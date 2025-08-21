#include "diabetes.h"
#include <cmath>
#include <MedUtils/MedUtils/MedCohort.h>
#include <MedMat/MedMat/MedMat.h>


//=================================================================================================
int get_diabetes_range_reg(const string &rep_name, const string &f_dreg, const string &f_out)
{

	MLOG("In get_diabetes_range_reg , using registry %s , out to registry %s\n", f_dreg.c_str(), f_out.c_str());
	// read diabetes full registry
	Registry<DiabetesRegRec> DReg;
	if (DReg.read_from_file(f_dreg) < 0) {
		MERR("ERROR: failed reading full diabetes registry file %s\n", f_dreg.c_str());
		return -1;
	}
	
	// read repository signals startdata and enddate
	MedRepository rep;
	vector<string> sigs ={ "STARTDATE", "ENDDATE" };
	if (rep.read_all(rep_name, {}, sigs) < 0) {
		MERR("ERROR: failed reading repository %s\n", rep_name.c_str());
		return -1;
	}

	// open output file
	ofstream fout;
	fout.open(f_out);

	if (!fout.is_open()) {
		MERR("ERROR: Can't open output file %s\n", f_out.c_str());
		return -1;
	}

	// go over registry and create the DM_Registry ranges
	int start_date_sid = rep.sigs.sid("STARTDATE");
	int end_date_sid = rep.sigs.sid("ENDDATE");
	int slen;
	int elen;
	int n = 0;

	for (auto &dr : DReg.reg) {

		int pid = dr.pid;	

		SVal *start_sig = (SVal *)rep.get(pid, start_date_sid, slen);
		SVal *end_sig = (SVal *)rep.get(pid, end_date_sid, elen);
		//int start_date = (int)(((SVal *)rep.get(pid, start_date_sid,slen))[0].val);		
		//int end_date = (int)(((SVal *)rep.get(pid, end_date_sid, elen))[0].val);
		//cout << pid << " start_date " << start_date << " end_date " << end_date << "\n";
		if (1) { //dr.censor == 0) {
			if (dr.rc_healthy[0] > 0) {
				int from = dr.rc_healthy[0];
				int to = dr.rc_healthy[1];
				if (to < from) to = from;
				if (slen > 0) {
					int start_date = (int)(start_sig[0].val);
					if (start_date < from) from = start_date;
				}
				fout << pid << "\tDM_Registry\t" << from << "\t" << to << "\t0" << "\n";
			}

			if (dr.rc_pre[0] > 0) {
				int from = dr.rc_pre[0];
				int to = dr.rc_pre[1];
				if (to < from) to = from;
				fout << pid << "\tDM_Registry\t" << from << "\t" << to << "\t1" << "\n";
			}

			if (dr.rc_diabetic[0] > 0) {
				int from = dr.rc_diabetic[0];
				int to = dr.rc_diabetic[1];
				if (to < from) to = from;
				if (elen > 0) {
					int end_date = (int)(end_sig[0].val);
					if (end_date > to) to = end_date;
				}
				fout << pid << "\tDM_Registry\t" << from << "\t" << to << "\t2" << "\n";
			}
		}

		n++;
		if (n%100000 == 0) MLOG("Went through %d registry records\n", n);
	}

	fout.close();
	return 0;
}


//=================================================================================================
// Diabetes Registry
//=================================================================================================

string printVec(const vector<string> &node_header, const vector<float> &node_value) {
	string res = "";
	char bf[200];
	snprintf(bf, sizeof(bf), "%s=%2.2f", node_header[0].c_str(), node_value[0]);
	res += bf;
	for (size_t i = 1; i < node_value.size(); ++i)
	{
		snprintf(bf, sizeof(bf), ", %s=%2.2f", node_header[i].c_str(), node_value[i]);
		res += bf;
	}
	return res;
}


//...................................................................................................
// gets a repository loaded with the relevant signals (glucose, hba1c, Drug, ReadCodes)
// and creates a diabetes registry entry for it
// preparations needed as well:
// lut for drugs
// lut for read codes
// fixed version:
// (1) hba1c >= 6.5 is Diabetic
// (2) when 2 tests are needed to make a decision (in a row, or in 2Y), the SECOND date is the diabetic date !!!!!!
//
// mode = 1 : take first test of the two ("biological" - can't be used for training)
// mode = 2 : take second test of the two ("real simulation" - only these can be used for training)
//
int get_diabetes_reg_for_pid_fixed(MedRepository &rep, int pid, DiabetesRegRec &d_rec, vector<char> &lut_drugs, vector<char> &lut_rc, string diag_signal, int mode, int diagnosis_importance)
{
	DiabetesRegRec dr;

	//MLOG("pid is %d\n", pid);
	dr.pid = pid;

	vector<pair<int, int>> events;

	// glucose data basics
	int glu_len;
	SDateVal *glu_sdv = (SDateVal *)rep.get(pid, "Glucose", glu_len);
	dr.glu_nvals = glu_len;
	if (glu_len > 0) {
		dr.glu_first_date = glu_sdv[0].date;
		dr.glu_last_date = glu_sdv[glu_len - 1].date;
		for (int i = 0; i < glu_len; i++) {
			if (dr.glu_first_date_above[0] == 0 && glu_sdv[i].val > 100 - 0.01) dr.glu_first_date_above[0] = glu_sdv[i].date;
			if (dr.glu_first_date_above[1] == 0 && glu_sdv[i].val > 126 - 0.01) dr.glu_first_date_above[1] = glu_sdv[i].date;
			if (dr.glu_first_date_above[2] == 0 && glu_sdv[i].val > 150 - 0.01) dr.glu_first_date_above[2] = glu_sdv[i].date;
			if (dr.glu_first_date_above[3] == 0 && glu_sdv[i].val > 200 - 0.01) dr.glu_first_date_above[3] = glu_sdv[i].date;
			pair<int, int> ev;
			ev.first = glu_sdv[i].date;
			if (glu_sdv[i].val > 200 - 0.01) ev.second = 4; // 4 means: 1 such result is enough for defining diabetes
			else if (glu_sdv[i].val > 126 - 0.01) ev.second = 3; // 3 means: 2 results are needed for defining diabetes
			else if (glu_sdv[i].val > 100 - 0.01) ev.second = 2; // 2 means: 1 result is enough for defining prediabetes
			else ev.second = 0;
			events.push_back(ev);
		}

	}

	// hba1c data basics
	int hba1c_len;
	SDateVal *hba1c_sdv = (SDateVal *)rep.get(pid, "HbA1C", hba1c_len);
	dr.hba1c_nvals = hba1c_len;
	if (hba1c_len > 0) {
		dr.hba1c_first_date = hba1c_sdv[0].date;
		dr.hba1c_last_date = hba1c_sdv[hba1c_len - 1].date;
		for (int i = 0; i < hba1c_len; i++) {
			if (dr.hba1c_first_date_above[0] == 0 && hba1c_sdv[i].val > (float)(5.7 - 0.01)) dr.hba1c_first_date_above[0] = hba1c_sdv[i].date;
			if (dr.hba1c_first_date_above[1] == 0 && hba1c_sdv[i].val > (float)(6.5 - 0.01)) dr.hba1c_first_date_above[1] = hba1c_sdv[i].date;
			if (dr.hba1c_first_date_above[2] == 0 && hba1c_sdv[i].val > (float)(7.0 - 0.01)) dr.hba1c_first_date_above[2] = hba1c_sdv[i].date;
			if (dr.hba1c_first_date_above[3] == 0 && hba1c_sdv[i].val > (float)(8.0 - 0.01)) dr.hba1c_first_date_above[3] = hba1c_sdv[i].date;
			pair<int, int> ev;
			ev.first = hba1c_sdv[i].date;
			if (hba1c_sdv[i].val > 8.5 - 0.01) ev.second = 4;
			else if (hba1c_sdv[i].val > 6.5 - 0.01) ev.second = 3;
			else if (hba1c_sdv[i].val > 5.7 - 0.01) ev.second = 2;
			else ev.second = 0;
			events.push_back(ev);
		}
	}


	// drug basics (using unified API)
	UniversalSigVec usv;
	rep.uget(pid, "Drug", usv);
	int section_id_drugs = rep.dict.section_id("Drug");
	if (usv.len > 0) {
		for (int i = 0; i < usv.len; i++) {
			if (lut_drugs[(int)usv.Val(i, 0)]) {
				if (dr.first_drugs_date == 0) {
					dr.first_drugs_date = usv.Time(i);
					dr.first_drugs_code = rep.dict.name(section_id_drugs, (int)usv.Val(i, 0));
				}
				dr.n_drug_records++;
				dr.n_drug_days += (int)usv.Val(i, 1);
			}
		}
	}

	if (dr.first_drugs_date > 0) {
		pair<int, int> ev;
		ev.first = dr.first_drugs_date;
		ev.second = 5;
		events.push_back(ev);
	}

	// read code basics
	/*
	if (lut_rc.size() > 0) {
		// means we're in THIN mode
		int section_id = rep.dict.section_id(diag_signal);
		int rc_len;
		SDateVal *rc_sdv = (SDateVal *)rep.get(pid, diag_signal, rc_len);
		if (rc_len) {
			int first_date = 0;
			string rc_name = "0";
			int n_rcs = 0;
			for (int i = 0; i < rc_len; i++) {
				if (lut_rc[(int)rc_sdv[i].val]) {
					if (first_date == 0) {
						first_date = rc_sdv[i].date;
						float val = rc_sdv[i].val;
						rc_name = "";
						int my_len = (int)(rep.dict.dict(section_id)->Id2Names[(int)val].size());
						for (int j = 0; j<my_len; j++) {
							string st = rep.dict.dict(section_id)->Id2Names[(int)val][j];
							if (st.compare(0, 3, "dc:") == 0 || my_len <= 3)
								rc_name.append(st + "|");
						}
					}
					n_rcs++;
					//MLOG("n_rcs %d date %d\n", n_rcs, rc_sdv[i].date);
				}
			}
			if (dr.first_read_code_date == 0) {
				dr.first_read_code_date = first_date;
				dr.first_read_code_name = rc_name;
			}
			else if (first_date > 0 && first_date < dr.first_read_code_date) {
				dr.first_read_code_date = first_date;
				dr.first_read_code_name = rc_name;
			}
			dr.n_rc_records += n_rcs;
		}
	}
	*/
	UniversalSigVec rc_usv;
	if (lut_rc.size() > 0) {
		// means we're in THIN mode
		int section_id = rep.dict.section_id(diag_signal);
		//int rc_len;
		rep.uget(pid, diag_signal, rc_usv);
		if (rc_usv.len > 0) {
			int first_date = 0;
			string rc_name = "0";
			int n_rcs = 0;
			for (int i = 0; i < rc_usv.len; i++) {
				if (lut_rc[(int)rc_usv.Val(i, 0)]) {
					if (pid == 2164238)
						cout << " In if  " << (int)lut_rc[(int)rc_usv.Val(i, 0)] << "\n";

					if (first_date == 0) {
						first_date = rc_usv.Time(i);
						int val = (int)rc_usv.Val(i, 0);
						rc_name = "";
						int my_len = (int)(rep.dict.dict(section_id)->Id2Names[val].size());
						for (int j = 0; j < my_len; j++) {
							string st = rep.dict.dict(section_id)->Id2Names[val][j];
							//if (st.compare(0, 3, "dc:") == 0 || my_len <= 3)
							rc_name.append(st + "|");
						}
					}
					n_rcs++;
					//MLOG("n_rcs %d date %d\n", n_rcs, rc_usv.Time(i));
				}
			}
			if (dr.first_read_code_date == 0) {
				dr.first_read_code_date = first_date;
				dr.first_read_code_name = rc_name;
			}
			else if (first_date > 0 && first_date < dr.first_read_code_date) {
				dr.first_read_code_date = first_date;
				dr.first_read_code_name = rc_name;
			}
			dr.n_rc_records += n_rcs;
		}
	}

	// Add event of type 3 (need 2 tests) when we see a read code (read code = one diabetic test in power)

	// !!! : Decided to get rid of this mess, and controling this from outside with default of 5 to importance (meaning a single diagnosis is enough)

	if (dr.first_read_code_date > 0) events.push_back({ dr.first_read_code_date, diagnosis_importance });

	// ghd decision
	sort(events.begin(), events.end());
	for (int i = 0; i < events.size(); i++) {

		if (events[i].second >= 4) {
			// an event that indicates diabetes on its own
			if (dr.ghd_diabetic[0] == 0) dr.ghd_diabetic[0] = events[i].first;
		}
		else if (events[i].second >= 3) {

			// check if there's an event >= 2 up to 2Y later
			int max_date = events[i].first + 20000; // added 2Y
			for (int j = i + 1; j < events.size(); j++) {
				if (events[j].first >= max_date) break;
				if (events[j].second >= 3) {
					// diabetes detected
					if (dr.ghd_diabetic[0] == 0) {
						if (mode > 1)
							dr.ghd_diabetic[0] = events[j].first;	// real
						else
							dr.ghd_diabetic[0] = events[i].first;	// biological
						break;
					}
				}
			}

			// check if immediately next event is >=3 ... we take that as enough to indicate a non random errored test
			if (i < events.size() - 1 && events[i + 1].second >= 3) {
				if (dr.ghd_diabetic[0] == 0) {
					if (mode > 1)
						dr.ghd_diabetic[0] = events[i + 1].first;		// real
					else
						dr.ghd_diabetic[0] = events[i].first;		// biological
				}
			}

		}

		if (events[i].second >= 2 && (dr.ghd_diabetic[0] == 0 || (dr.ghd_diabetic[0] > events[i].first))) {
			// an event that indicates pre-diabetes on its own
			if (dr.ghd_pre[0] == 0) dr.ghd_pre[0] = events[i].first;
		}
		else if (events[i].second >= 1 && (dr.ghd_diabetic[0] == 0 || (dr.ghd_diabetic[0] > events[i].first))) {
			// detecting pre diabetes
			// check if theres an event >= 1 up to 2Y later
			int max_date = events[i].first + 20000; // added 2Y
			for (int j = i + 1; j < events.size(); j++) {
				if (events[j].first >= max_date) break;
				if (events[j].second >= 1) {
					// pre diabetes detected
					if (dr.ghd_pre[0] == 0) {
						if (mode > 1)
							dr.ghd_pre[0] = events[j].first;		// real
						else
							dr.ghd_pre[0] = events[i].first;		// biological

						break;
					}
				}
			}

			// check if immediately next event is >=1 ... we take that as enough to indicate a non random errored test
			if (i < events.size() - 1 && events[i + 1].second >= 1) {
				if (dr.ghd_pre[0] == 0) {
					if (mode > 1)
						dr.ghd_pre[0] = events[i + 1].first;			// real
					else
						dr.ghd_pre[0] = events[i].first;			// biological
				}
			}


		}

		//MLOG("(*) i %d ev %d %d pre %d %d diab %d %d \n", i, events[i].first, events[i].second, dr.ghd_pre[0], dr.ghd_pre[1], dr.ghd_diabetic[0], dr.ghd_diabetic[1]);
	}

	// fix pre to be before diabetes if there's one
	if (dr.ghd_pre[0] > 0 && dr.ghd_diabetic[0] > 0 && dr.ghd_pre[0] >= dr.ghd_diabetic[0]) dr.ghd_pre[0] = 0;

	// set rest
	//MLOG("(*) pre %d %d diab %d %d \n", dr.ghd_pre[0], dr.ghd_pre[1], dr.ghd_diabetic[0], dr.ghd_diabetic[1]);
	for (int i = 0; i < events.size(); i++) {

		int curr_date = events[i].first;

		int before_pre = 1;
		if (dr.ghd_pre[0] > 0 && curr_date >= dr.ghd_pre[0]) before_pre = 0;

		int before_diab = 1;
		if (dr.ghd_diabetic[0] > 0 && curr_date >= dr.ghd_diabetic[0]) before_diab = 0;

		//MLOG("event i %d curr %d %d pre %d %d diab %d %d , bef_pre %d bef_diab %d\n", i, curr_date, events[i].second, dr.ghd_pre[0], dr.ghd_pre[1], dr.ghd_diabetic[0], dr.ghd_diabetic[1], before_pre, before_diab);
		// healthy dates
		if (before_pre && before_diab) {

			if (!((i == events.size() - 1 || i == 0) && events[i].second >= 1)) { // last event that's pre diabetic and up can not be considered for healthy period, same for first
				if (dr.ghd_healthy[0] == 0) dr.ghd_healthy[0] = curr_date; // first date we are sure of being healthy
				dr.ghd_healthy[1] = curr_date;							   // last date we are sure of being healthy
			}

		}

		// pre dates
		if (before_diab && dr.ghd_pre[0] > 0 && curr_date >= dr.ghd_pre[0]) {
			if (!(i == events.size() - 1 && events[i].second >= 3)) // if this is the last event AND it is DIABETIC we can't know for sure it is not a start of one
				dr.ghd_pre[1] = curr_date; // last date we are sure of being pre diabetic
		}

		// last diabetic
		if (dr.ghd_diabetic[0] > 0 && curr_date >= dr.ghd_diabetic[0])
			dr.ghd_diabetic[1] = curr_date; // last date we are sure of being diabetic
	}

	//MLOG("(*) pre %d %d diab %d %d \n", dr.ghd_pre[0], dr.ghd_pre[1], dr.ghd_diabetic[0], dr.ghd_diabetic[1]);
	// adding rc
	dr.rc_healthy = dr.ghd_healthy;
	dr.rc_pre = dr.ghd_pre;
	dr.rc_diabetic = dr.ghd_diabetic;

	if (dr.first_read_code_date > 0 && diagnosis_importance < 5) {

		//int pre_adjusted = 0;
		// case of rc before prediabetes period
		if (dr.rc_pre[0] > 0 && dr.first_read_code_date < dr.rc_pre[0]) {
			dr.rc_ignore_censor_bit = 1;
		}

		// case of moving the diabetic date
		if (dr.rc_diabetic[0] > 0) {

			if (dr.first_read_code_date < dr.rc_diabetic[0]) {

				// as long as we are before the LAST pre diabetic date we can move 
				// (our previous conditions make sure that the test before CAN NOT be in diabetic range.)
				if (dr.rc_pre[0] > 0) {
					if (dr.first_read_code_date > dr.rc_pre[1])
						dr.rc_diabetic[0] = dr.first_read_code_date;
					else
						dr.rc_ignore_censor_bit = 1;
				}
				else if (dr.rc_healthy[0] > 0) {
					if (dr.first_read_code_date > dr.rc_healthy[1])
						dr.rc_diabetic[0] = dr.first_read_code_date;
					else
						dr.rc_ignore_censor_bit = 1;
				}
				else {
					// rc code is before the first diabetic which spans all tests, hence we move date before
					dr.rc_diabetic[0] = dr.first_read_code_date;
				}

			}

		}

		// case of all normal
		if (dr.rc_diabetic[0] == 0 && dr.rc_pre[0] == 0) {
			if (dr.rc_healthy[0] > 0) {
				if (dr.first_read_code_date <= dr.rc_healthy[1])
					dr.rc_ignore_censor_bit = 1;
			}


		}
	}
		// censoring

		// censor = 1 : rc_ignore_censor bit is on
		if (dr.rc_ignore_censor_bit) dr.censor = 1;

		// censor = 2 : read code after last healthy when there are no pre/diabetic
		if (diagnosis_importance < 5 && dr.first_read_code_date > 0 && dr.rc_pre[0] == 0 && dr.rc_diabetic[0] == 0 && dr.rc_healthy[1] > 0 &&
			dr.first_read_code_date > dr.rc_healthy[1])
			dr.censor = 2;

		// censor = 3 : below 2 test of glucose or hba1c test
	//	if (dr.glu_nvals + dr.hba1c_nvals < 2)
	//		dr.censor = 3;

		d_rec = dr;
		return 0;
	
}

int get_diabetes_reg_for_pid_fixed_Geisinger(MedRepository &rep, int pid, DiabetesRegRec &d_rec, vector<char> &lut_drugs, vector<char> &lut_rc, int mode)
{

	DiabetesRegRec dr;

	dr.pid = pid;

	vector<pair<int, int>> events;

	// glucose data basics
	int glu_len;
	SDateVal *glu_sdv = (SDateVal *)rep.get(pid, "Glucose", glu_len);
	dr.glu_nvals = glu_len;
	if (glu_len > 0) {
		dr.glu_first_date = glu_sdv[0].date;
		dr.glu_last_date = glu_sdv[glu_len - 1].date;
		for (int i = 0; i < glu_len; i++) {
			if (dr.glu_first_date_above[0] == 0 && glu_sdv[i].val > 100 - 0.01) dr.glu_first_date_above[0] = glu_sdv[i].date;
			if (dr.glu_first_date_above[1] == 0 && glu_sdv[i].val > 126 - 0.01) dr.glu_first_date_above[1] = glu_sdv[i].date;
			if (dr.glu_first_date_above[2] == 0 && glu_sdv[i].val > 150 - 0.01) dr.glu_first_date_above[2] = glu_sdv[i].date;
			if (dr.glu_first_date_above[3] == 0 && glu_sdv[i].val > 200 - 0.01) dr.glu_first_date_above[3] = glu_sdv[i].date;
			pair<int, int> ev;
			ev.first = glu_sdv[i].date;
			if (glu_sdv[i].val > 200 - 0.01) ev.second = 4; // 4 means: 1 such result is enough for defining diabetes
			else if (glu_sdv[i].val > 126 - 0.01) ev.second = 3; // 3 means: 2 results are needed for defining diabetes
			else if (glu_sdv[i].val > 100 - 0.01) ev.second = 1; // 1 means - 2 results are enough for definining prediabetes,
																 // 2 means: 1 result is enough for defining prediabetes
			else ev.second = 0;
			events.push_back(ev);
		}

	}

	// hba1c data basics
	int hba1c_len;
	SDateVal *hba1c_sdv = (SDateVal *)rep.get(pid, "HbA1C", hba1c_len);
	dr.hba1c_nvals = hba1c_len;
	if (hba1c_len > 0) {
		dr.hba1c_first_date = hba1c_sdv[0].date;
		dr.hba1c_last_date = hba1c_sdv[hba1c_len - 1].date;
		for (int i = 0; i < hba1c_len; i++) {
			if (dr.hba1c_first_date_above[0] == 0 && hba1c_sdv[i].val >(float)(5.7 - 0.01)) dr.hba1c_first_date_above[0] = hba1c_sdv[i].date;
			if (dr.hba1c_first_date_above[1] == 0 && hba1c_sdv[i].val > (float)(6.5 - 0.01)) dr.hba1c_first_date_above[1] = hba1c_sdv[i].date;
			if (dr.hba1c_first_date_above[2] == 0 && hba1c_sdv[i].val > (float)(7.0 - 0.01)) dr.hba1c_first_date_above[2] = hba1c_sdv[i].date;
			if (dr.hba1c_first_date_above[3] == 0 && hba1c_sdv[i].val > (float)(8.0 - 0.01)) dr.hba1c_first_date_above[3] = hba1c_sdv[i].date;
			pair<int, int> ev;
			ev.first = hba1c_sdv[i].date;
			if (hba1c_sdv[i].val > 6.5 - 0.01) ev.second = 3;
			else if (hba1c_sdv[i].val > 5.7 - 0.01) ev.second = 2;
			else ev.second = 0;
			events.push_back(ev);
		}
	}

	// drug basics (using unified API)
	UniversalSigVec usv;
	rep.uget(pid, "Drug", usv);
	int section_id_drugs = rep.dict.section_id("Drug");
	if (usv.len > 0) {
		for (int i = 0; i < usv.len; i++)
			if (lut_drugs[(int)usv.Val(i, 0)]) {
				if (dr.first_drugs_date == 0) {
					dr.first_drugs_date = usv.Time(i);
					dr.first_drugs_code = rep.dict.name(section_id_drugs, (int)usv.Val(i, 0));
				}
				dr.n_drug_records++;
				dr.n_drug_days += (int)usv.Val(i, 1);
			}
	}

	if (dr.first_drugs_date > 0) {
		pair<int, int> ev;
		ev.first = dr.first_drugs_date;
		ev.second = 5;
		events.push_back(ev);
	}

	// read code basics
	if (lut_rc.size() > 0) {
		// means we're in THIN mode
		int section_id = rep.dict.section_id("RC");
		int rc_len;
		SDateVal *rc_sdv = (SDateVal *)rep.get(pid, "RC", rc_len);
		if (rc_len) {
			int first_date = 0;
			string rc_name = "0";
			int n_rcs = 0;
			for (int i = 0; i < rc_len; i++) {
				if (lut_rc[(int)rc_sdv[i].val]) {
					if (first_date == 0) {
						first_date = rc_sdv[i].date;
						float val = rc_sdv[i].val;
						rc_name = "";
						int my_len = (int)(rep.dict.dict(section_id)->Id2Names[(int)val].size());
						for (int j = 0; j<my_len; j++) {
							string st = rep.dict.dict(section_id)->Id2Names[(int)val][j];
							if (st.compare(0, 3, "dc:") == 0 || my_len <= 3)
								rc_name.append(st + "|");
						}
					}
					n_rcs++;
					//MLOG("n_rcs %d date %d\n", n_rcs, rc_sdv[i].date);
				}
			}
			if (dr.first_read_code_date == 0) {
				dr.first_read_code_date = first_date;
				dr.first_read_code_name = rc_name;
			}
			else if (first_date > 0 && first_date < dr.first_read_code_date) {
				dr.first_read_code_date = first_date;
				dr.first_read_code_name = rc_name;
			}
			dr.n_rc_records += n_rcs;
		}
	}

	// Add event of type 3 (need 2 tests) when we see a read code (read code = one diabetic test in power)
	if (dr.first_read_code_date > 0) events.push_back({ dr.first_read_code_date, 3 });

	// ghd decision
	sort(events.begin(), events.end());
	for (int i = 0; i < events.size(); i++) {

		if (events[i].second >= 4) {
			// an event that indicates diabetes on its own
			if (dr.ghd_diabetic[0] == 0) dr.ghd_diabetic[0] = events[i].first;
		}
		else if (events[i].second >= 3) {

			// check if there's an event >= 2 up to 2Y later
			int max_date = events[i].first + 20000; // added 2Y
			for (int j = i + 1; j < events.size(); j++) {
				if (events[j].first >= max_date) break;
				if (events[j].second >= 3) {
					// diabetes detected
					if (dr.ghd_diabetic[0] == 0) {
						if (mode > 1)
							dr.ghd_diabetic[0] = events[j].first;	// real
						else
							dr.ghd_diabetic[0] = events[i].first;	// biological
						break;
					}
				}
			}

			// check if immediately next event is >=3 ... we take that as enough to indicate a non random errored test
			if (i < events.size() - 1 && events[i + 1].second >= 3) {
				if (dr.ghd_diabetic[0] == 0) {
					if (mode > 1)
						dr.ghd_diabetic[0] = events[i + 1].first;		// real
					else
						dr.ghd_diabetic[0] = events[i].first;		// biological
				}
			}

		}

		if (events[i].second == 2 && dr.ghd_diabetic[0] == 0) {
			// an event that indicates pre-diabetes on its own
			if (dr.ghd_pre[0] == 0) dr.ghd_pre[0] = events[i].first;
		}
		else if (events[i].second >= 1 && dr.ghd_diabetic[0] == 0) {
			// detecting pre diabetes
			// check if theres an event >= 1 up to 3Y later
			int max_date = events[i].first + 30000; // added 2Y
			//for (int j = i + 1; j < events.size(); j++) {
				if (events[i+1].first >= max_date) break;
				if (events[i+1].second >= 1) {
					// pre diabetes detected
					if (dr.ghd_pre[0] == 0) {
						if (mode > 1)
							dr.ghd_pre[0] = events[i+1].first;		// real
						else
							dr.ghd_pre[0] = events[i].first;		// biological

						//break;
					}
				}
			//}

			// check if immediately next event is >=1 ... we take that as enough to indicate a non random errored test
			if (i < events.size() - 1 && events[i + 1].second >= 1) {
				if (dr.ghd_pre[0] == 0) {
					if (mode > 1)
						dr.ghd_pre[0] = events[i + 1].first;			// real
					else
						dr.ghd_pre[0] = events[i].first;			// biological
				}
			}


		}

	}

	// fix pre to be before diabetes if there's one
	if (dr.ghd_pre[0] > 0 && dr.ghd_diabetic[0] > 0 && dr.ghd_pre[0] >= dr.ghd_diabetic[0]) dr.ghd_pre[0] = 0;

	// set rest
	for (int i = 0; i < events.size(); i++) {

		int curr_date = events[i].first;

		int before_pre = 1;
		if (dr.ghd_pre[0] > 0 && curr_date >= dr.ghd_pre[0]) before_pre = 0;

		int before_diab = 1;
		if (dr.ghd_diabetic[0] > 0 && curr_date >= dr.ghd_diabetic[0]) before_diab = 0;

		//MLOG("event i %d curr %d %d pre %d diab %d , bef_pre %d bef_diab %d\n", i, curr_date, events[i].second, dr.ghd_pre[0], dr.ghd_diabetic[0], before_pre, before_diab);
		// healthy dates
		if (before_pre && before_diab) {

			if (!((i == events.size() - 1 || i == 0) && events[i].second >= 1)) { // last event that's pre diabetic and up can not be considered for healthy period, same for first
				if (dr.ghd_healthy[0] == 0) dr.ghd_healthy[0] = curr_date; // first date we are sure of being healthy
				dr.ghd_healthy[1] = curr_date;							   // last date we are sure of being healthy
			}

		}

		// pre dates
		if (before_diab && dr.ghd_pre[0] > 0 && curr_date >= dr.ghd_pre[0]) {
			if (!(i == events.size() - 1 && events[i].second >= 3)) // if this is the last event AND it is DIABETIC we can't know for sure it is not a start of one
				dr.ghd_pre[1] = curr_date; // last date we are sure of being pre diabetic
		}

		// last diabetic
		if (dr.ghd_diabetic[0] > 0 && curr_date >= dr.ghd_diabetic[0])
			dr.ghd_diabetic[1] = curr_date; // last date we are sure of being diabetic
	}

	// adding rc
	dr.rc_healthy = dr.ghd_healthy;
	dr.rc_pre = dr.ghd_pre;
	dr.rc_diabetic = dr.ghd_diabetic;

	if (dr.first_read_code_date > 0) {

		//int pre_adjusted = 0;
		// case of rc before prediabetes period
		if (dr.rc_pre[0] > 0 && dr.first_read_code_date < dr.rc_pre[0]) {
			dr.rc_ignore_censor_bit = 1;
		}

		// case of moving the diabetic date
		if (dr.rc_diabetic[0] > 0) {

			if (dr.first_read_code_date < dr.rc_diabetic[0]) {

				// as long as we are before the LAST pre diabetic date we can move 
				// (our previous conditions make sure that the test before CAN NOT be in diabetic range.)
				if (dr.rc_pre[0] > 0) {
					if (dr.first_read_code_date > dr.rc_pre[1])
						dr.rc_diabetic[0] = dr.first_read_code_date;
					else
						dr.rc_ignore_censor_bit = 1;
				}
				else if (dr.rc_healthy[0] > 0) {
					if (dr.first_read_code_date > dr.rc_healthy[1])
						dr.rc_diabetic[0] = dr.first_read_code_date;
					else
						dr.rc_ignore_censor_bit = 1;
				}
				else {
					// rc code is before the first diabetic which spans all tests, hence we move date before
					dr.rc_diabetic[0] = dr.first_read_code_date;
				}

			}

		}

		// case of all normal
		if (dr.rc_diabetic[0] == 0 && dr.rc_pre[0] == 0) {
			if (dr.rc_healthy[0] > 0) {
				if (dr.first_read_code_date <= dr.rc_healthy[1])
					dr.rc_ignore_censor_bit = 1;
			}
		}

	}

	// censoring

	// censor = 1 : rc_ignore_censor bit is on
	if (dr.rc_ignore_censor_bit) dr.censor = 1;

	// censor = 2 : read code after last healthy when there are no pre/diabetic
	if (dr.first_read_code_date > 0 && dr.rc_pre[0] == 0 && dr.rc_diabetic[0] == 0 && dr.rc_healthy[1] > 0 &&
		dr.first_read_code_date > dr.rc_healthy[1])
		dr.censor = 2;

	// censor = 3 : below 2 test of glucose or hba1c test
	if (dr.glu_nvals + dr.hba1c_nvals < 2)
		dr.censor = 3;

	d_rec = dr;
	return 0;
}


//....................................................................................................................................................
void DiabetesRegRec::print()
{
	MOUT("DRec:: id %d :: ", pid);
	MOUT("glu_above: %d %d %d %d glu_dates %d %d n_glu %d ", glu_first_date_above[0], glu_first_date_above[1], glu_first_date_above[2], glu_first_date_above[3], glu_first_date, glu_last_date, glu_nvals);
	MOUT(":: hba1c_above: %d %d %d %d hba1c_dates %d %d n_hba1c %d ", hba1c_first_date_above[0], hba1c_first_date_above[1], hba1c_first_date_above[2], hba1c_first_date_above[3], hba1c_first_date, hba1c_last_date, hba1c_nvals);
	MOUT(":: drugs %d %s %d %d", first_drugs_date, first_drugs_code.c_str(), n_drug_records, n_drug_days);
	MOUT(":: rc %d %s %d ", first_read_code_date,first_read_code_name.c_str(), n_rc_records);
	MOUT(":: ghd: H: %d - %d P: %d - %d D: %d - %d ", ghd_healthy[0], ghd_healthy[1], ghd_pre[0], ghd_pre[1], ghd_diabetic[0], ghd_diabetic[1]);
	MOUT(":: rc: H: %d - %d P: %d - %d D: %d - %d ", rc_healthy[0], rc_healthy[1], rc_pre[0], rc_pre[1], rc_diabetic[0], rc_diabetic[1]);
	MOUT(":: ignore %d censor %d\n", rc_ignore_censor_bit, censor);
}

//....................................................................................................................................................
void DiabetesRegRec::print_short()
{
	MOUT("pid %d H %d P %d D %d C %d\n", pid, rc_healthy[0], rc_pre[0], rc_diabetic[0], censor);
}

//....................................................................................................................................................
int get_all_diabetes_reg(const string &rep_name, vector<string> drugs_names, vector<string> read_codes, vector<int> &pid_list, string diag_sig, string params, Registry<DiabetesRegRec> &dr)
{
	map<string, string> reg_params;
	MedSerialize::initialization_text_to_map(params, reg_params);
	int reg_mode = 2;
	if (reg_params.find("reg_mode") != reg_params.end()) reg_mode = stoi(reg_params["reg_mode"]);
	int do_print = 1;
	if (reg_params.find("print") != reg_params.end()) do_print = stoi(reg_params["print"]);
	int diagnosis_importance = 5;
	if (reg_params.find("diagnosis_importance") != reg_params.end()) diagnosis_importance = stoi(reg_params["diagnosis_importance"]);


	MLOG("reg_mode %d do_print %d\n", reg_mode, do_print);
	MedRepository rep;

	if (rep.read_all(rep_name, pid_list, { "TRAIN", "Glucose","HbA1C","Drug"}) < 0) {
		MERR("ERROR: Failed reading repository %s\n", rep_name.c_str());
		return -1;
	}

	// add diagnosis 
	if (rep.sigs.sid(diag_sig) > 0) {
		rep.load(diag_sig, pid_list);
	}

	// prep lookup table for drugs
	vector<char> lut_drugs;
	rep.dict.prep_sets_lookup_table(rep.dict.section_id("Drug"), drugs_names, lut_drugs);
	// prep lookup table for read_codes
	vector<char> lut_rc;
	MLOG("Working with diag_sig=%s got %d read_codes\n", diag_sig.c_str(), read_codes.size());

	if (rep.sigs.sid(diag_sig) > 0) {
		rep.dict.prep_sets_lookup_table(rep.dict.section_id(diag_sig), read_codes, lut_rc);
		MLOG("Got lut_rc of size %d\n", lut_rc.size());
		int n = 0;
		for (auto l : lut_rc) n += l;
		MLOG("lut_rc sum is %d\n", n);
	}

	dr.reg.clear();
	MLOG("pid_list size %d , rep.pids %d\n", pid_list.size(), rep.pids.size());

	int n = 0, n1 = 0, n2 = 0, n3 = 0;

	vector<DiabetesRegRec> records(rep.pids.size());

#pragma omp parallel for
	for (int i=0; i<rep.pids.size(); i++) {
		int pid = rep.pids[i];

		get_diabetes_reg_for_pid_fixed(rep, pid, records[i], lut_drugs, lut_rc, diag_sig ,reg_mode, diagnosis_importance);
		//get_diabetes_reg_for_pid_fixed_Geisinger(rep, pid, drr, lut_drugs, lut_rc, reg_mode);

#pragma omp critical
		{
			n++;
			if (n % 1000000 == 0) {
				MLOG("done %d/%d records\n", n, rep.pids.size());
			}
		}


	}

	MLOG("Finished 1st stage now writing to output file");
	for (auto &drr : records) {
		if (drr.censor != 3) {
			if (do_print == 1) drr.print();
			if (do_print == 2) drr.print_short();
			if (drr.censor == 2) n2++;
			if (drr.censor == 1) n1++;
			dr.reg.push_back(drr);
		}
		else
			n3++;
	}

	MLOG("censor 1 records - %d \n", n1);
	MLOG("censor 2 records - %d \n", n2);
	MLOG("censor 3 records - %d (not saved)\n", n3);
	return 0;
	
}

static map<int, int> pid_to_bdate;
static map<int, bool> pid_to_gender; //true male
static int AGE_BIN;

//=========================================================================================================
// YEARLY STATS
//=========================================================================================================
int get_diabetes_stats(const string &f_dreg,
	const fieldValueFunction &fieldValue, const vector<string> &headers, bool(*filterRec)(const vector<float> &) = NULL)
{
	Registry<DiabetesRegRec> DReg;
	if (DReg.read_from_file(f_dreg) < 0) return -1;

	map<vector<float>, DiabetesStat> stats;

	for (auto &dr : DReg.reg) {

		if (dr.censor != 3) {
			map<vector<float>, vector<StatType>> valToState;
			fieldValue(dr, valToState);

			for (auto it = valToState.begin(); it != valToState.end(); ++it)
			{
				if (stats.find(it->first) == stats.end()) {
					DiabetesStat dstat;
					dstat.node_value = it->first;
					dstat.node_header = headers;
					stats[it->first] = dstat;
				}
				for (StatType s : it->second) {
					if (s == StatType::n_healthy)
						++stats[it->first].n_healthy;
					else if (s == StatType::n_pre)
						++stats[it->first].n_pre;
					else if (s == StatType::n_diab)
						++stats[it->first].n_diab;
					else if (s == StatType::n_h2d)
						++stats[it->first].n_h2d;
					else if (s == StatType::n_h2p)
						++stats[it->first].n_h2p;
					else if (s == StatType::n_pre2d)
						++stats[it->first].n_pre2d;
				}
			}
		}
	}

	auto s_b = stats.begin();
	if (filterRec != NULL)
		while (s_b != stats.end())
			if (!filterRec(s_b->first)) s_b = stats.erase(s_b);
			else ++s_b;

			for (auto &stat : stats)
				stat.second.print();

			stats.begin()->second.print_csv_header();

			for (auto &stat : stats)
				stat.second.print_csv();

			return 0;
}

void create_feature_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out,
	vector<float>(*getFeat)(map<float, vector<float>> &, int, int)) {
	int min_year = 1995;
	int max_year = 2016;
	map<float, vector<float>> singleton_years;

	if (dr.rc_healthy[0] > 0) {

		int y_from = dr.rc_healthy[0] / 10000;
		int y_to = 0;
		int to_pre = 0;
		int to_d = 0;

		if (dr.rc_pre[0] > 0) { y_to = dr.rc_pre[0] / 10000; to_pre = 1; }
		else if (dr.rc_diabetic[0] > 0) { y_to = dr.rc_diabetic[0] / 10000; to_d = 1; }
		else y_to = dr.rc_healthy[1] / 10000;

		for (int y = max(y_from, min_year); y <= min(y_to, max_year); y++)
			out[getFeat(singleton_years, y, dr.pid)].push_back(StatType::n_healthy);
		if (to_pre && y_to >= min_year && y_to <= max_year)
			out[getFeat(singleton_years, y_to, dr.pid)].push_back(StatType::n_h2p);
		if (to_d && y_to >= min_year && y_to <= max_year)
			out[getFeat(singleton_years, y_to, dr.pid)].push_back(StatType::n_h2d);
	}

	if (dr.rc_pre[0] > 0) {

		int y_from = dr.rc_pre[0] / 10000;
		int y_to = 0;
		int to_d = 0;

		if (dr.rc_diabetic[0] > 0) { y_to = dr.rc_diabetic[0] / 10000; to_d = 1; }
		else y_to = dr.rc_pre[1] / 10000;

		for (int y = max(y_from, min_year); y <= min(y_to, max_year); y++)
			out[getFeat(singleton_years, y, dr.pid)].push_back(StatType::n_pre);
		if (to_d && y_to >= min_year && y_to <= max_year)
			out[getFeat(singleton_years, y_to, dr.pid)].push_back(StatType::n_pre2d);
	}

	if (dr.rc_diabetic[0] > 0) {

		int y_from = dr.rc_diabetic[0] / 10000;
		int y_to = dr.rc_diabetic[1] / 10000;

		for (int y = max(y_from, min_year); y <= min(y_to, max_year); y++)
			out[getFeat(singleton_years, y, dr.pid)].push_back(StatType::n_diab);
	}
}

vector<float> fetch_year(map<float, vector<float>> &singleton_years, int year, int pid) {
	if (singleton_years.find((float)year) == singleton_years.end()) {
		singleton_years[(float)year] = { (float)year };
	}
	return singleton_years[(float)year];
}
vector<float> fetch_yearage(map<float, vector<float>> &singleton_years, int year, int pid) {
	if (singleton_years.find((float)year) == singleton_years.end()) {
		singleton_years[(float)year] = { (float)year, (float)(AGE_BIN * round((year - pid_to_bdate[pid] / 10000) / AGE_BIN)) };
	}
	return singleton_years[(float)year];
}
vector<float> fetch_age(map<float, vector<float>> &singleton_years, int year, int pid) {
	if (singleton_years.find((float)year) == singleton_years.end()) {
		singleton_years[(float)year] = { (float)(AGE_BIN * round((year - pid_to_bdate[pid] / 10000) / AGE_BIN)) };
	}
	return singleton_years[(float)year];
}
vector<float> fetch_yeargender(map<float, vector<float>> &singleton_years, int year, int pid) {
	if (singleton_years.find((float)year) == singleton_years.end()) {
		singleton_years[(float)year] = { (float)year,  2 - (float)pid_to_gender[pid] }; //2 is female, 1 is male
	}
	return singleton_years[(float)year];
}
vector<float> fetch_gender(map<float, vector<float>> &singleton_years, int year, int pid) {
	float gender = 2 - (float)pid_to_gender[pid];
	if (singleton_years.find(gender) == singleton_years.end()) {
		singleton_years[gender] = { gender }; //2 is female, 1 is male
	}
	return singleton_years[gender];
}
vector<float> fetch_agegender(map<float, vector<float>> &singleton_years, int year, int pid) {
	if (singleton_years.find((float)year) == singleton_years.end()) {
		singleton_years[(float)year] = { (float)(AGE_BIN * round((year - pid_to_bdate[pid] / 10000) / AGE_BIN)), 2 - (float)pid_to_gender[pid] }; //2 is female, 1 is male
	}
	return singleton_years[(float)year];
}
vector<float> fetch_yearagegender(map<float, vector<float>> &singleton_years, int year, int pid) {
	if (singleton_years.find((float)year) == singleton_years.end()) {
		singleton_years[(float)year] = { (float)year, (float)(AGE_BIN * round((year - pid_to_bdate[pid] / 10000) / AGE_BIN)), 2 - (float)pid_to_gender[pid] }; //2 is female, 1 is male
	}
	return singleton_years[(float)year];
}

void create_year_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	return create_feature_stats(dr, out, fetch_year);
}
void create_yearage_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	if (pid_to_bdate.find(dr.pid) == pid_to_bdate.end()) {
		throw logic_error("patient bdate not found");
	}
	return create_feature_stats(dr, out, fetch_yearage);
}
void create_yeargender_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	if (pid_to_gender.find(dr.pid) == pid_to_gender.end()) {
		throw logic_error("patient gender not found");
	}
	return create_feature_stats(dr, out, fetch_yeargender);
}
void create_age_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	if (pid_to_bdate.find(dr.pid) == pid_to_bdate.end()) {
		throw logic_error("patient bdate not found");
	}
	return create_feature_stats(dr, out, fetch_age);
}
void create_gender_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	if (pid_to_gender.find(dr.pid) == pid_to_gender.end()) {
		throw logic_error("patient gender not found");
	}
	return create_feature_stats(dr, out, fetch_gender);
}
void create_agegender_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	if (pid_to_gender.find(dr.pid) == pid_to_gender.end()) {
		throw logic_error("patient gender not found");
	}
	return create_feature_stats(dr, out, fetch_agegender);
}
void create_yearagegender_stats(const DiabetesRegRec &dr, map<vector<float>, vector<StatType>> &out) {
	if (pid_to_gender.find(dr.pid) == pid_to_gender.end()) {
		throw logic_error("patient gender not found");
	}
	return create_feature_stats(dr, out, fetch_yearagegender);
}

vector<string> splitStr(string str, char delimeter) {
	vector<string> res;
	size_t i = 0;
	string buff = "";
	while (i < str.size())
	{
		if (str.at(i) == delimeter) {
			res.push_back(buff);
			buff = "";
		}
		else if (str.at(i) != ' ') {
			buff += str.at(i);
		}
		++i;
	}
	if (buff.size() > 0) {
		res.push_back(buff);
	}
	return res;
}

int get_full_diabetes_stats(const string &f_dreg, const string &stat_args, const string &rep, int age_bin)
{
	AGE_BIN = age_bin;
	MOUT("Set Age_bin to %d\n", AGE_BIN);
	//supports for "year" "age" "gender" and thier combination with ",". exmaple "year,age"
	if (stat_args.find("age") != string::npos || stat_args.find("gender") != string::npos)
		if (rep.empty())
			throw invalid_argument("you supply age or gender params without repository path to complete those signals");

	//populate byear:
	if (stat_args.find("age") != string::npos) {
		MedRepository mr;
		if (mr.read_all(rep, {}, { "BDATE" }) < 0)
			throw logic_error("error reading repository");

		for (int i = 0; i < mr.pids.size(); ++i)
		{
			int len;
			SVal *data = (SVal *)mr.get(mr.pids[i], "BDATE", len);
			if (len == 0) {
				continue;
			}
			pid_to_bdate[mr.pids[i]] = (int)data[len - 1].val;
		}
	}
	//populate gender:
	if (stat_args.find("gender") != string::npos) {
		MedRepository mr;
		if (mr.read_all(rep, {}, { "GENDER" }) < 0)
			throw logic_error("error reading repository");

		for (int i = 0; i < mr.pids.size(); ++i)
		{
			int len;
			SVal *data = (SVal *)mr.get(mr.pids[i], "GENDER", len);
			if (len == 0) {
				continue;
			}
			pid_to_gender[mr.pids[i]] = (int)data[len - 1].val == 1;
		}
	}

	vector<string> aggs = splitStr(stat_args, ',');
	bool has_age = false, has_year = false, has_gender = false;
	for (string agg : aggs)
	{
		if (agg == "age")
			has_age = true;
		else if (agg == "year")
			has_year = true;
		else if (agg == "gender")
			has_gender = true;
		else
			throw invalid_argument("not supported " + agg);
	}

	//for now onlt age and year:
	if (has_year && !has_age && !has_gender)
	{
		MOUT("Running On \"Year\"\n");
		return get_diabetes_stats(f_dreg, create_year_stats, aggs);
	}
	else if (has_year && has_age && !has_gender) {
		MOUT("Running On \"Year,Age\"\n");
		return get_diabetes_stats(f_dreg, create_yearage_stats, aggs, [](const vector<float> &v) { return v[1] >= 20 && v[1] <= 90 && v[0] >= 1995 && v[0] <= 2016; });
	}
	else if (!has_year && has_age && !has_gender) {
		MOUT("Running On \"Age\"\n");
		return get_diabetes_stats(f_dreg, create_age_stats, aggs, [](const vector<float> &v) { return v[0] >= 20 && v[0] <= 90; }); //filter age_range
	}
	else if (has_year && !has_age  && has_gender) {
		MOUT("Running On \"Year,Gender\"\n");
		return get_diabetes_stats(f_dreg, create_yeargender_stats, aggs, [](const vector<float> &v) { return v[0] >= 1995 && v[0] <= 2016; });
	}
	else if (has_year && has_age  && has_gender) {
		MOUT("Running On \"Year,Age,Gender\"\n");
		return get_diabetes_stats(f_dreg, create_yearagegender_stats, aggs, [](const vector<float> &v) { return v[1] >= 20 && v[1] <= 90 && v[0] >= 1995 && v[0] <= 2016; });
	}
	else if (!has_year && has_age  && has_gender) {
		MOUT("Running On \"Age,Gender\"\n");
		return get_diabetes_stats(f_dreg, create_agegender_stats, aggs, [](const vector<float> &v) { return v[0] >= 20 && v[0] <= 90; });
	}
	else if (!has_year && !has_age  && has_gender) {
		MOUT("Running On \"Gender\"\n");
		return get_diabetes_stats(f_dreg, create_gender_stats, aggs);
	}
	else {
		throw logic_error("not supported for now");
	}

}