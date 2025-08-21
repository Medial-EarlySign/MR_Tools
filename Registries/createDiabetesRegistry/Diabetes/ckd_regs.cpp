#include "diabetes.h"
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedUtils/MedUtils/MedCohort.h>
#include <cassert>

//................................................................................................................................
int read_RC_from_file(const string &fname, vector<string> &RC_list)
{
	ifstream inf(fname);

	if (!inf) {
		MERR("MedSignals: read: Can't open file %s\n", fname.c_str());
		return -1;
	}

	string curr_line;
	RC_list.clear();
	while (getline(inf, curr_line)) {
		//		MLOG("curr_line: %s\n", curr_line.c_str());
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {
			vector<string> fields;
			split(fields, curr_line, boost::is_any_of(" \t"));
			RC_list.push_back(fields[0]);
		}
	}

	inf.close();

	return 0;
}

// CKD_State :
// 4 levels : 0 , 1 , 2 , 3
// 0 : egfr > 60 && mA <30    ||  no egfr && mA <= 30         || no protein && egfr > 60
// 1 : egfr 45-60 && mA <30   ||   egfr > 60 && mA 30-300	  ||    no egfr && mA 30-300   || no proteinuria && egfr 45-60
// 2 : egfr 30-45 && mA <30   ||   egfr 45-60 && mA 30-300    ||    egfr > 60 &&  mA > 300 || no egfr && mA > 300 || no protein && egfr 30-45
// 3 : egfr < 30              ||   egfr 30-45 && mA > 30      ||    egfr 45-60 && mA > 300
// 4 : efgr < 15
//---------------------------------------------------------------------------------------------
pair<int, string> get_ckd_state(float last_egfr, int last_proteinuria)
{

	if (last_egfr < 0 && last_proteinuria < 0) return make_pair(-1, "last_egfr < 0 && last_proteinuria < 0");

	if (last_egfr < 15 && last_egfr >= 0) return make_pair(4, "last_egfr < 15 && last_egfr >= 0");

	if (last_egfr > 60 && last_proteinuria == 0) return make_pair(0, "last_egfr > 60 && last_proteinuria == 0");
	if (last_egfr < 0 && last_proteinuria == 0) return make_pair(0, "last_egfr < 0 && last_proteinuria == 0");
	if (last_egfr > 60 && last_proteinuria < 0) return make_pair(0, "last_egfr > 60 && last_proteinuria < 0");

	if (last_egfr > 45 && last_egfr <= 60 && last_proteinuria == 0) return make_pair(1, "last_egfr > 45 && last_egfr <= 60 && last_proteinuria == 0");
	if (last_egfr > 60 && last_proteinuria >= 1 && last_proteinuria <= 3) return make_pair(1, "last_egfr > 60 && last_proteinuria >= 1 && last_proteinuria <= 3");
	if (last_egfr < 0 && last_proteinuria >= 1 && last_proteinuria <= 3) return make_pair(1, "last_egfr < 0 && last_proteinuria >= 1 && last_proteinuria <= 3");
	if (last_egfr > 45 && last_egfr <= 60 && last_proteinuria < 0) return make_pair(1, "last_egfr > 45 && last_egfr <= 60 && last_proteinuria < 0");

	if (last_egfr > 30 && last_egfr <= 45 && last_proteinuria == 0) return make_pair(2, "last_egfr > 30 && last_egfr <= 45 && last_proteinuria == 0");
	if (last_egfr > 45 && last_egfr <= 60 && last_proteinuria >= 1 && last_proteinuria <= 3) return make_pair(2, "last_egfr > 45 && last_egfr <= 60 && last_proteinuria >= 1 && last_proteinuria <= 3");
	if (last_egfr > 60 && last_proteinuria >= 4) return make_pair(2, "last_egfr > 60 && last_proteinuria >= 4");
	if (last_egfr < 0 && last_proteinuria >= 4) return make_pair(2, "last_egfr < 0 && last_proteinuria >= 4");
	if (last_egfr > 30 && last_egfr <= 45 && last_proteinuria < 0) return make_pair(2, "last_egfr > 30 && last_egfr <= 45 && last_proteinuria < 0");

	if (last_egfr < 0) return make_pair(-1, "last_egfr < 0");
	if (last_egfr <= 30) return make_pair(3, "last_egfr <= 30");
	if (last_proteinuria < 0) return make_pair(-1, "last_proteinuria < 0");
	if (last_egfr > 30 && last_egfr <= 45 && last_proteinuria >= 1 && last_proteinuria <= 3) return make_pair(3, "last_egfr > 30 && last_egfr <= 45 && last_proteinuria >= 1 && last_proteinuria <= 3");
	if (last_egfr > 45 && last_egfr <= 60 && last_proteinuria >= 4) return make_pair(3, "last_egfr > 45 && last_egfr <= 60 && last_proteinuria >= 4");

	return make_pair(-1, "default");

}

// Preparing a few needed calculated signals to help building registries and train/test
// Proteinuria_State : values 0,1,2,3,4
// 0: microalbumin level 0-30 , 1 : 30-100 , 2 : 100-200 , 3: 200-300 , 4: 300+
// several other urine tests are used as well. They were calibrated against urine microalbumin and split to matching levels.
// 
// eGFR_CKD_State :
// 0: eGFR 90+ , 1: 60-90 2: 45-60 3: 30-45 4: 15-30 5: <15
// 
// CKD_State :
// 4 levels : 0 , 1 , 2 , 3
// 0 : egfr > 60 && mA <30
// 1 : egfr 45-60 && mA <30   ||   egfr > 60 && mA 30-300
// 2 : egfr 30-45 && mA <30   ||   egfr 45-60 && mA 30-300    ||    egfr > 60 &&  mA > 300
// 3 : egfr < 30              ||   egfr 30-45 && mA > 30      ||    egfr 45-60 && mA > 300
//--------------------------------------------------------------------------------------------------------------------------------
int get_proteinuria_thin(const string &rep_fname, const string &f_out)
{

	MedRepository rep;

	vector<string> sig_names ={ "Urine_Microalbumin", "UrineTotalProtein", "UrineAlbumin", 
		"UrineAlbumin_over_Creatinine" , "eGFR_CKD_EPI", "STARTDATE" , "ENDDATE"};
	if (rep.read_all(rep_fname, {}, sig_names) < 0) {
		MERR("Can't read repository file %s\n", rep_fname.c_str());
		return -1;
	}

	int Urine_Microalbumin_sid = rep.sigs.sid("Urine_Microalbumin");
	int UrineTotalProtein_sid = rep.sigs.sid("UrineTotalProtein");
	int UrineAlbumin_sid = rep.sigs.sid("UrineAlbumin");
	int Urine_dipstick_for_protein_sid = rep.sigs.sid("Urine_dipstick_for_protein");
	int Urinalysis_Protein_sid = rep.sigs.sid("Urinalysis_Protein");
	int Urine_Protein_Creatinine_sid = rep.sigs.sid("Urine_Protein_Creatinine");
	int UrineAlbumin_over_Creatinine_sid = rep.sigs.sid("UrineAlbumin_over_Creatinine");
	int eGFR_sid = rep.sigs.sid("eGFR_CKD_EPI");
	int start_date_sid = rep.sigs.sid("STARTDATE");
	int end_date_sid = rep.sigs.sid("ENDDATE");

	
	// add if thin
	if (Urinalysis_Protein_sid > 0) 
		rep.load(Urinalysis_Protein_sid);
	else MWARN("Urinalysis_Protein signal is not available\n");
	if (Urine_Protein_Creatinine_sid > 0) 
		rep.load(Urine_Protein_Creatinine_sid);
	else MWARN("Urine_Protein_Creatinine signal is not available\n");
	if (Urine_dipstick_for_protein_sid > 0)
		rep.load(Urine_dipstick_for_protein_sid);
	else MWARN("Urine_dipstick_for_protein signal is not available\n");

	vector<char> Urine_dipstick_for_protein_normal, Urine_dipstick_for_protein_medium, Urine_dipstick_for_protein_severe;
	if (Urine_dipstick_for_protein_sid > 0) {
		int section_id = rep.dict.section_id("Urine_dipstick_for_protein");
		rep.dict.prep_sets_lookup_table(section_id, { "Urine_dipstick_for_protein_normal" }, Urine_dipstick_for_protein_normal);
		rep.dict.prep_sets_lookup_table(section_id, { "Urine_dipstick_for_protein_medium" }, Urine_dipstick_for_protein_medium);
		rep.dict.prep_sets_lookup_table(section_id, { "Urine_dipstick_for_protein_severe" }, Urine_dipstick_for_protein_severe);
	}
	
	vector<char> Urinalysis_Protein_normal, Urinalysis_Protein_medium, Urinalysis_Protein_severe;
	if (Urinalysis_Protein_sid > 0) {
		int section_id = rep.dict.section_id("Urinalysis_Protein");
		rep.dict.prep_sets_lookup_table(section_id, { "Urinalysis_Protein_normal" }, Urinalysis_Protein_normal);
		rep.dict.prep_sets_lookup_table(section_id, { "Urinalysis_Protein_medium" }, Urinalysis_Protein_medium);
		rep.dict.prep_sets_lookup_table(section_id, { "Urinalysis_Protein_severe" }, Urinalysis_Protein_severe);
	}
	

	int len;

	// open output file
	ofstream fout;
	fout.open(f_out);

	if (!fout.is_open()) {
		MERR("ERROR: Can't open output file %s\n", f_out.c_str());
		return -1;
	}

	for (auto pid : rep.pids) {
		map<int, pair<int, string>> date_state;
		
		// Urine_Microalbumin
		SDateVal *U_micro = (SDateVal *)rep.get(pid, Urine_Microalbumin_sid, len);
		for (int i=0; i<len; i++) {
			float uval = U_micro[i].val;
			int udate = U_micro[i].date;
			int state = 0;
			if (uval >= 30) state = 1;
			if (uval >= 100) state = 2;
			if (uval >= 200) state = 3;
			if (uval >= 300) state = 4;
			if (uval > 0) {
				// microalbumin tests are contaminated with a large number of 0 test .... we throw these - not a real result for this test
				if (date_state.find(udate) == date_state.end())
					date_state[udate] = make_pair(state, "Urine_Microalbumin");
				else {
					if (date_state[udate].first < state)
						date_state[udate] = make_pair(state, "Urine_Microalbumin");
				}
			}
		}

		// UrineTotalProtein
		SDateVal *U_TotalProtein = (SDateVal *)rep.get(pid, UrineTotalProtein_sid, len);
		for (int i=0; i<len; i++) {
			float uval = U_TotalProtein[i].val;
			int udate = U_TotalProtein[i].date;
			int state = 0;
			if (uval >= 0.15) state = 1;
			if (uval >= 0.30) state = 2;
			if (uval >= 0.45) state = 3;
			if (uval >= 0.60) state = 4;
			if (date_state.find(udate) == date_state.end())
				date_state[udate] = make_pair(state, "U_TotalProtein");
			else {
				if (date_state[udate].first < state)
					date_state[udate] = make_pair(state, "U_TotalProtein");
			}

		}

		// UrineAlbumin
		SDateVal *U_Albumin = (SDateVal *)rep.get(pid,UrineAlbumin_sid, len);
		for (int i=0; i<len; i++) {
			float uval = U_Albumin[i].val;
			int udate = U_Albumin[i].date;
			int state = 0;
			if (uval >= 30) state = 1;
			if (uval >= 80) state = 2;
			if (uval >= 180) state = 3;
			if (uval >= 300) state = 4;
			if (date_state.find(udate) == date_state.end())
				date_state[udate] = make_pair(state, "UrineAlbumin");
			else {
				if (date_state[udate].first < state)
					date_state[udate] = make_pair(state, "UrineAlbumin");
			}

		}

		if (Urine_Protein_Creatinine_sid > 0) {
			// Urine_Protein_Creatinine
			SDateVal *U_PC = (SDateVal *)rep.get(pid, Urine_Protein_Creatinine_sid, len);
			for (int i = 0; i < len; i++) {
				float uval = U_PC[i].val;
				int udate = U_PC[i].date;
				int state = 0;
				if (uval >= 15) state = 1;
				if (uval >= 30) state = 2;
				if (uval >= 60) state = 3;
				if (uval >= 100) state = 4;
				if (date_state.find(udate) == date_state.end())
					date_state[udate] = make_pair(state, "Urine_Protein_Creatinine");
				else {
					if (date_state[udate].first < state)
						date_state[udate] = make_pair(state, "Urine_Protein_Creatinine");
				}

			}
		}


		// UrineAlbumin_over_Creatinine
		SDateVal *U_ACR = (SDateVal *)rep.get(pid, UrineAlbumin_over_Creatinine_sid, len);
		for (int i=0; i<len; i++) {
			float uval = U_ACR[i].val;
			int udate = U_ACR[i].date;
			int state = 0;
			if (uval >= 3.5) state = 1;
			if (uval >= 12) state = 2;
			if (uval >= 20) state = 3;
			if (uval >= 27) state = 4;
			if (date_state.find(udate) == date_state.end())
				date_state[udate] = make_pair(state, "UrineAlbumin_over_Creatinine");
			else {
				if (date_state[udate].first < state)
					date_state[udate] = make_pair(state, "UrineAlbumin_over_Creatinine");
			}

		}
		
		if (Urine_dipstick_for_protein_sid > 0) {
			// Urine_dipstick_for_protein
			SDateVal *U_dipstick = (SDateVal *)rep.get(pid, Urine_dipstick_for_protein_sid, len);
			for (int i = 0; i < len; i++) {
				int uval = (int)U_dipstick[i].val;
				int udate = U_dipstick[i].date;
				int state = -1;
				// normal
				if (Urine_dipstick_for_protein_normal[uval]) state = 0; // normal
				if (Urine_dipstick_for_protein_medium[uval]) state = 1; // normal
				if (Urine_dipstick_for_protein_severe[uval]) state = 2; // normal
				if (state >= 0) {
					if (date_state.find(udate) == date_state.end())
						date_state[udate] = make_pair(state, "Urine_dipstick_for_protein");
					else {

						if (date_state[udate].first < state) {
							date_state[udate] = make_pair(state, "Urine_dipstick_for_protein");
							if (state == 2)
								date_state[udate] = make_pair(20, "Urine_dipstick_for_protein"); // signing it for a max pass
						}
					}
				}
			}
		}
		if (Urinalysis_Protein_sid > 0) {
			// Urinalysis_Protein 
			SDateVal *U_UP = (SDateVal *)rep.get(pid, Urinalysis_Protein_sid, len);
			for (int i = 0; i < len; i++) {
				int uval = (int)U_UP[i].val;
				int udate = U_UP[i].date;
				int state = -1;
				if (Urinalysis_Protein_normal[uval]) state = 0; // normal
				if (Urinalysis_Protein_medium[uval]) state = 1; // normal
				if (Urinalysis_Protein_severe[uval]) state = 2; // normal

				if (state >= 0) {
					if (date_state.find(udate) == date_state.end())
						date_state[udate] = make_pair(state, "Urinalysis_Protein");
					else {
						if (date_state[udate].first < state) {
							date_state[udate] = make_pair(state, "Urinalysis_Protein");
							if (state == 2)
								date_state[udate] = make_pair(20, "Urinalysis_Protein"); // signing it for a max pass
						}
					}
				}
			}
		}
		// max pass - fixing correctly the '20' values to either 2 or the last larger proteinuria based on the continous params.
		int last_prot = -1;
		for (auto &ds : date_state) {
			if (ds.second.first == 20) {
				// in this case last_prot changes to 2 only if it was below that
				if (last_prot >= 2)
					ds.second.first = last_prot;
				else {
					ds.second.first = 2;
					last_prot = 2;
				}

			} else
				last_prot = ds.second.first;
		}

		// print Proteinuria_State results for pid
		int last = -100;
		for (auto &ds : date_state) {
			//MOUT("%d Proteinuria_State %d %d\n", pid, ds.first, ds.second);
			fout << pid << "\tProteinuria_State\t" << ds.first << "\t" <<ds.second.first << "\t" << ds.second.second << "\n";
			if (ds.second.first != last) {
				//MOUT("%d Proteinuria_State_Changes %d %d\n", pid, ds.first, ds.second);
				fout << pid << "\tProteinuria_State_Changes\t" << ds.first << "\t" <<ds.second.first << "\t" << ds.second.second << "\n";
			}
			last = ds.second.first;
		}


		// get eGFR_CKD_State and CKD_State
		SDateVal *egfr = (SDateVal *)rep.get(pid, eGFR_sid, len);
		map<int, int> egfr_ckd_date_state;
		for (int i=0; i<len; i++) {
			float egfr_val = egfr[i].val;
			int egfr_date = egfr[i].date;
			int val = -1;
			if (egfr_val >= 90) val = 0;
			else if (egfr_val >= 60) val = 1;
			else if (egfr_val >= 45) val = 2;
			else if (egfr_val >= 30) val = 3;
			else if (egfr_val >= 15) val = 4;
			else val = 5;

			egfr_ckd_date_state[egfr_date] = val;
		}

		map<int, pair<float, int>> combined_vals;
		for (int i=0; i<len; i++) {
			pair<float, int> p;
			p.first = egfr[i].val;
			p.second = -1;
			combined_vals[egfr[i].date] = p;
		}

		for (auto &prot : date_state) {

			if (combined_vals.find(prot.first) != combined_vals.end()) {
				combined_vals[prot.first].second = prot.second.first;
			}
			else {
				pair<float, int> p;
				p.first = -1;
				p.second = prot.second.first;
				combined_vals[prot.first] = p;
			}

		}

		int last_p_val = -1;
		float last_e_val = -1;
		for (auto &c : combined_vals) {
			if (c.second.first < 0) c.second.first = last_e_val;
			if (c.second.second < 0) c.second.second = last_p_val;
			last_e_val = c.second.first;
			last_p_val = c.second.second;
		}

		map<int, pair<int, string>> ckd_date_state;
		for (auto &c : combined_vals) {
			pair<int, string> ckd_state = get_ckd_state(c.second.first, c.second.second);
			if (ckd_state.first >= 0)
				ckd_date_state[c.first] = ckd_state;
		}


		// print eGFR_CKD_State results for pid
		last = -100;
		for (auto &ecs : egfr_ckd_date_state) {
			//MOUT("%d eGFR_CKD_State %d %d\n", pid, ecs.first, ecs.second);
			fout << pid << "\teGFR_CKD_State\t" << ecs.first << "\t" << ecs.second << "\n";
			if (ecs.second != last) {
				//MOUT("%d eGFR_CKD_State_Changes %d %d\n", pid, ecs.first, ecs.second);
				fout << pid << "\teGFR_CKD_State_Changes\t" << ecs.first << "\t" << ecs.second << "\n";
			}
			last = ecs.second;
		}


		// print CKD_State results for pid
		last = -100;
		for (auto &cs : ckd_date_state) {
			//MOUT("%d CKD_State %d %d\n", pid, cs.first, cs.second);
			fout << pid << "\tCKD_State\t" << cs.first << "\t" << cs.second.first << "\t" << cs.second.second << "\n";
			if (cs.second.first != last) {
				//MOUT("%d CKD_State_Changes %d %d\n", pid, cs.first, cs.second);
				fout << pid << "\tCKD_State_Changes\t" << cs.first << "\t" << cs.second.first << "\t" << cs.second.second << "\n";
			}
			last = cs.second.first;
		}

		// calc and print CKD_Registry results
		int prev_state = -1;
		int start_date = (int)(((SVal *)rep.get(pid, start_date_sid, len))[0].val);
		int end_date = (int)(((SVal *)rep.get(pid, end_date_sid, len))[0].val);
		vector<int> from_d, to_d;
		vector<pair<int, string>> state_d;
		for (auto &cs : ckd_date_state) {
			if (prev_state != cs.second.first) {
				// start new range 
				from_d.push_back(cs.first);
				to_d.push_back(cs.first);
				state_d.push_back(cs.second);
				prev_state = cs.second.first;

			} else {
				// update current range
				to_d.back() = cs.first;
			}

		}

		int nd = (int)from_d.size();
		if (nd > 0) {
			if (state_d[0].first == 0 && start_date < from_d[0]) from_d[0] = start_date;
			if (state_d[nd-1].first > 0 && end_date > to_d[nd-1]) to_d[nd-1] = end_date;
		}

		for (int i=0; i<nd; i++)
			fout << pid << "\tCKD_Registry\t" << from_d[i] << "\t" << to_d[i] << "\t" << state_d[i].first << "\t" << state_d[i].second << "\n";

	}

	return 0;
}

//==================================================================================================================
// CKD
//==================================================================================================================
////	// CKD definitions:
////
////	// Normal Creatinine levels for Males:    0 - 1.2 , > 1.4 Start CKD
////	// Normal Creatinine levels for Females:  0 - 1.0 , > 1.2 Start CKD
////	// eGFR_CKD_EPI : >90 Normal , 60-90 Low, 30-60 : low kidney damage, 15-30: severe damage, 0-15: Failure
////	// Urine_Microalbumin: <30 Normal , 30-300: medium damage, >300 damage
////	// Urine_Protein (we have it only in maccabi) : <30 normal 30-300 medium , >300 severe
////	// Several Replacements for Urine_Protein in THIN: (calibrated vs. Urine_Microalbumin samples)
////	// (1) UrineTotalProtein : < 0.15 Normal , 0.15 - 0.60 medium, >0.60 Severe
////	// (2) UrineAlbumin: <30 Normal, 30-300 medium, >300 Severe
////	// (3) Urine_dipstick_for_protein: 70001,70002,70006: Normal , 70003,70004,70005,70007: Medium, 70008: Severe (70006 is like 70001, 70007 is abit above 70003)
////	// (4) Urinalysis_Protein: 70001,70002,70006: Normal , 70003,70004,70005,70007: Medium, 70008: Severe (70006 is like 70001, 70007 is abit above 70003)
////	//
////
////
////	// Starting point for CKD :
////	// One of:
////	// (1) 2 consecutive or within 2Y of Creatinine >= 1.4 for Males (and we will take the first ever >=1.4)
////	// (2) 2 consecutive or within 2Y of Creatinine >= 1.2 for Females (and we will take the first ever >= 1.2)
////	// (3) A single creatinine >= 2.0 for either male or female
////	// (4) Urine_Microalbumin >=30 first time
////	// (5) One of UrineTotalProtein,UrineAlbumin,Urine_dipstick_for_protein,Urinalysis_Protein reaching Medium level first time
////	//
////	// Level of CKD once started:
////	// if there is eGFR and one of the Urine tests
////	// (CKD-1) eGFR 45-60 + Urine_test Normal || eGFR > 60 + Urine_test Medium
////	// (CKD-2) eGFR 30-45 + Urine_test Normal || eGFR 45-60 + Urine_test Medium || eGFR > 60 + Urine_test Severe
////	// (CKD-3) eGFR 15-30 || eGFR 30-45 + Urine_test Medium,Severe || eGFR 45-60 + Urine_test Severe
////	// (CKD-4) eGFR 0-15
////	// if there is no Urine_test:
////	// (CKD-1) eGFR 45-60
////	// (CKD-2) eGFR 30-45
////	// (CKD-3) eGFR 15-30
////	// (CKD-4) eGFR <15
////	//if there is no eGFR
////	// (CKD-1) Urine_test Medium
////	// (CKD-2) Urine_test Severe
////	//
////	// For each patient the CKD level at time T is the maximal CKD level for all t <= T.
////	//
////
////	// Additional Considerations:
////	// (1) Detect points in time where Dialysis/Transplant were done (using Creatinine levels drop, and/or ReadCodes?)
////	// (2) Use relevant readcodes (ckd, dialysis, translant):
////	//	   - consider moving date of CKD first onset to the readcode date (if it is up to X days earlier) X =~ 2 years.
////	//     - consider censoring a patient that has ONLY readcode indication
////	//
int get_ckd_reg_fixed_thin(PidRec &rec, CKDRegRec2 &cr, vector<vector<char>> &luts, vector<int> &sids, int reg_mode, int eGFR_mode)
{
	int creatinine_sid = sids[0];
//	int eGFR_CKD_EPI_sid = sids[1];
	int Proteinuria_State_sid = sids[2];
	int eGFR_CKD_State_sid = sids[3];
	int CKD_State_sid = sids[4];
	int gender_sid = sids[5];
//	int RC_History_sid = sids[6];
//	int RC_Diagnostic_Procedures_sid = sids[7];
//	int RC_Radiology_sid = sids[8];
//	int RC_Procedures_sid = sids[9];
//	int RC_Admin_sid = sids[10];
//	int RC_Diagnosis_sid = sids[11];
//	int RC_Injuries_sid = sids[12];

	// CKD definitions:

	// Normal Creatinine levels for Males:    0 - 1.2 , > 1.4 Start CKD
	// Normal Creatinine levels for Females:  0 - 1.0 , > 1.2 Start CKD
	// eGFR_CKD_EPI : >90 Normal , 60-90 Low, 30-60 : low kidney damage, 15-30: severe damage, 0-15: Failure
	// Urine_Microalbumin: <30 Normal , 30-300: medium damage, >300 damage
	// Urine_Protein (we have it only in maccabi) : <30 normal 30-300 medium , >300 severe
	// Several Replacements for Urine_Protein in THIN: (calibrated vs. Urine_Microalbumin samples)
	// (1) UrineTotalProtein : < 0.15 Normal , 0.15 - 0.60 medium, >0.60 Severe
	// (2) UrineAlbumin: <30 Normal, 30-300 medium, >300 Severe
	// (3) Urine_dipstick_for_protein: 70001,70002,70006: Normal , 70003,70004,70005,70007: Medium, 70008: Severe (70006 is like 70001, 70007 is abit above 70003)
	// (4) Urinalysis_Protein: 70001,70002,70006: Normal , 70003,70004,70005,70007: Medium, 70008: Severe (70006 is like 70001, 70007 is abit above 70003)
	//


	// Starting point for CKD :
	// One of:
	// (1) 2 consecutive or within 2Y of Creatinine >= 1.4 for Males (and we will take the first ever >=1.4)
	// (2) 2 consecutive or within 2Y of Creatinine >= 1.2 for Females (and we will take the first ever >= 1.2)
	// (3) A single creatinine >= 2.0 for either male or female
	// (4) Urine_Microalbumin >=30 first time
	// (5) One of UrineTotalProtein,UrineAlbumin,Urine_dipstick_for_protein,Urinalysis_Protein reaching Medium level first time
	//
	// Level of CKD once started:
	// if there is eGFR and one of the Urine tests
	// (CKD-1) eGFR 45-60 + Urine_test Normal || eGFR > 60 + Urine_test Medium
	// (CKD-2) eGFR 30-45 + Urine_test Normal || eGFR 45-60 + Urine_test Medium || eGFR > 60 + Urine_test Severe
	// (CKD-3) eGFR 15-30 || eGFR 30-45 + Urine_test Medium,Severe || eGFR 45-60 + Urine_test Severe
	// (CKD-4) eGFR 0-15
	// if there is no Urine_test:
	// (CKD-1) eGFR 45-60
	// (CKD-2) eGFR 30-45
	// (CKD-3) eGFR 15-30
	// (CKD-4) eGFR <15
	//if there is no eGFR
	// (CKD-1) Urine_test Medium
	// (CKD-2) Urine_test Severe
	//
	// For each patient the CKD level at time T is the maximal CKD level for all t <= T.
	//

	// Additional Considerations:
	// (1) Detect points in time where Dialysis/Transplant were done (using Creatinine levels drop, and/or ReadCodes?)
	// (2) Use relevant readcodes (ckd, dialysis, translant):
	//	   - consider moving date of CKD first onset to the readcode date (if it is up to X days earlier) X =~ 2 years.
	//     - consider censoring a patient that has ONLY readcode indication
	//

	int len;
	int gender = (int)(((SVal *)rec.get(gender_sid, len))[0].val);
	int is_male = (int)(gender == 1);
	int is_female = (int)(gender == 2);

	vector<pair<int, int>> events;

	CKDRegRec2 reg;

	// creatinine
	SDateVal *creatinine_sdv = (SDateVal *)rec.get(creatinine_sid, len);
	reg.n_tests += len;

//	int last_large_creatinine = 0;
//	int last_was_large = 0;

	if (len > 0) {
		reg.creatinine_from_to[0] = creatinine_sdv[0].date;
		reg.creatinine_from_to[1] = creatinine_sdv[len-1].date;
	}

	for (int i=0; i<len; i++) {
		float cval = creatinine_sdv[i].val;
		int cdate = creatinine_sdv[i].date;

		if (is_male && cval >= (float)1.2 && reg.creatinine_first_above[0] == 0) reg.creatinine_first_above[0] = cdate;
		if (is_female && cval >= (float)1.0 && reg.creatinine_first_above[0] == 0) reg.creatinine_first_above[0] = cdate;
		if (is_male && cval >= (float)1.4 && reg.creatinine_first_above[1] == 0) reg.creatinine_first_above[1] = cdate;
		if (is_female && cval >= (float)1.2 && reg.creatinine_first_above[1] == 0) reg.creatinine_first_above[1] = cdate;
		if (cval >= (float)2.0 && reg.creatinine_first_above[2] == 0) reg.creatinine_first_above[2] = cdate;
		if (cval >= (float)3.0 && reg.creatinine_first_above[3] == 0) reg.creatinine_first_above[3] = cdate;

		if (cval < 1.5 && reg.creatinine_first_above[3] != 0 && reg.suspected_dt == 0)
			reg.suspected_dt = cdate;

		if (eGFR_mode == 0) {
			// taking registry decisions based on eGFR
			pair<int, int> ev;
			ev.first = cdate;
			ev.second = 0;
			if ((is_male && cval>=(float)1.4) || (is_female && cval >=(float)1.2)) ev.second = 1;
			if ((is_male && cval>=(float)1.7) || (is_female && cval >=(float)1.4)) ev.second = 2;
			events.push_back(ev);
		}
	}

	// eGFR_State decision
	SDateVal *egfr_state_sdv = (SDateVal *)rec.get(eGFR_CKD_State_sid, len);

	for (int i=0; i<len; i++) {
		int egval = (int)egfr_state_sdv[i].val;
		int egdate = egfr_state_sdv[i].date;

		if (egval>0 && egval <=5) {
			if (reg.egfr_state_first[egval-1] == 0) reg.egfr_state_first[egval-1] = egdate;
		}

		if (eGFR_mode != 0) {
			// taking registry decisions based on eGFR
			pair<int, int> ev;
			ev.first = egdate;
			ev.second = 0;
			if (egval == 2) ev.second = 1;
			if (egval >= 3) ev.second = 2;
			events.push_back(ev);
		}
	}

	// CKD_State collection
	SDateVal *ckd_state_sdv = (SDateVal *)rec.get(CKD_State_sid, len);
	//MLOG("pid , ckd_state len %d\n", len);
	for (int i=0; i<len; i++) {
		int ckval = (int)ckd_state_sdv[i].val;
		int ckdate = ckd_state_sdv[i].date;

		if (ckval>=0 && ckval <=4) {
			if (reg.ckd_state_first[ckval] == 0) reg.ckd_state_first[ckval] = ckdate;
		}

	}

	// urine tests

	// using Proteinuria signal
	SDateVal *U_PS = (SDateVal *)rec.get(Proteinuria_State_sid, len);
	reg.n_tests += len;

	if (len > 0) {
		reg.urine_from_to[0] = U_PS[0].date;
		reg.urine_from_to[1] = U_PS[len-1].date;

		for (int i=0; i<len; i++) {
			int uval = (int)U_PS[i].val;
			int udate = U_PS[i].date;
			if (uval >= 1) {
				pair<int, int> ev;
				ev.first = udate;
				if (uval >= 4)
					ev.second = 2;
				else
					ev.second = 1; // below 300 microalbumin
				events.push_back(ev);
			}
			if (uval >= 1 && reg.urine_first_above[0] == 0) reg.urine_first_above[0] = udate;
			if (uval >= 4 && reg.urine_first_above[1] == 0) reg.urine_first_above[1] = udate;
		}
	}


	// going over read_codes
	for (int j=5; j<sids.size(); j++) {
		int rc_sid = sids[j];
		SDateVal *rc_sdv = (SDateVal *)rec.get(rc_sid, len);

		for (int i=0; i<len; i++) {
			int rcode = (int)rc_sdv[i].val;
			int rdate = rc_sdv[i].date;

			if (luts[0][rcode]) {
				if (reg.first_rc[0] == 0 || rdate < reg.first_rc[0]) reg.first_rc[0] = rdate;
				if (luts[1][rcode] && (reg.first_rc[1] == 0 || rdate < reg.first_rc[1]))
					reg.first_rc[1] = rdate;
				if (luts[2][rcode] && (reg.first_rc[2] == 0 || rdate < reg.first_rc[2]))
					reg.first_rc[2] = rdate;

			}
		}
	}

	// ckd_date
	sort(events.begin(), events.end());
	for (int i=0; i<events.size(); i++) {

		int val = events[i].second;
		int date = events[i].first;

		if (val >= 2) { reg.ckd_date = date; break; }

		if (val >=1) {

			if (i < events.size()-1 && events[i+1].second >= 1) { 
				if (reg_mode > 1)
					reg.ckd_date = events[i+1].first;		// real
				else
					reg.ckd_date = events[i].first;			// biological

				break; 
			}

			// 2Y condition
			for (int j=i+1; j<events.size(); j++) {
				if (events[j].first > date + 20000) break;
				if (events[j].second >= 1) { 
					if (reg_mode > 1)
						reg.ckd_date = events[j].first;		// real
					else
						reg.ckd_date = events[i].first;		// biological
					break; 
				}
			}

			if (reg.ckd_date) break;
		}

	}

	if (reg.suspected_dt > 0 && (reg.ckd_date == 0 || reg.suspected_dt < reg.ckd_date))
		reg.ckd_date = reg.suspected_dt;

	reg.rc_ckd_date = reg.ckd_date;
	if (reg.first_rc[0] > 0 && (reg.rc_ckd_date == 0 || reg.first_rc[0] < reg.rc_ckd_date))
		reg.rc_ckd_date = reg.first_rc[0];


	if (reg.n_tests < 2) reg.censor = 3;

	cr = reg;
	return 0;
}

//................................................................................................................................
int get_all_ckd_reg_fixed_thin(const string &rep_name, vector<string> read_codes_fnames, vector<int> &pid_list, string params, Registry<CKDRegRec2> &creg)
{
	map<string, string> reg_params;
	MedSerialize::initialization_text_to_map(params, reg_params);
	int reg_mode = 2;
	if (reg_params.find("reg_mode") != reg_params.end()) reg_mode = stoi(reg_params["reg_mode"]);
	int do_print = 1;
	if (reg_params.find("print") != reg_params.end()) do_print = stoi(reg_params["print"]);
	int egfr_mode = 1;
	if (reg_params.find("egfr_mode") != reg_params.end()) egfr_mode = stoi(reg_params["egfr_mode"]);


	MLOG("reg_mode %d do_print %d egfr_mode %d\n", reg_mode, do_print, egfr_mode);

	MedRepository rep;

	MLOG("Creating thin ckd registry\n");
	vector<string> signals ={ "Creatinine", "eGFR_CKD_EPI", "Proteinuria_State", "eGFR_CKD_State", "CKD_State", "GENDER", 
							  "RC_Demographic", "RC_History", "RC_Diagnostic_Procedures", 
							  "RC_Radiology", "RC_Procedures", "RC_Admin", "RC_Diagnosis", "RC_Injuries" };

	if (rep.read_all(rep_name, pid_list, signals) < 0) {
		MERR("ERROR: Failed reading repository %s\n", rep_name.c_str());
		return -1;
	}

	// prep sids
	vector<int> sids;
	for (auto& sname : signals)
		sids.push_back(rep.sigs.sid(sname));

	MLOG("signals.size %d sids.size %d\n", signals.size(), sids.size());
	// prep lookup tables
	int section_id = rep.dict.section_id("RC_Diagnosis");
	vector<vector<char>> luts;
	for (auto fname : read_codes_fnames) {
		vector<string> rcs;
		vector<char> lut;
		MLOG("Reading lut from file %s\n", fname.c_str());
		if (read_RC_from_file(fname, rcs) < 0) {
			return -1;
		}
		rep.dict.prep_sets_lookup_table(section_id, rcs, lut);
		luts.push_back(lut);
	}

	MLOG("prepared %d luts\n", luts.size());
	creg.reg.clear();
	PidRec rec;
	for (auto pid : rep.pids) {

		rec.init_from_rep(&rep, pid, sids);
		CKDRegRec2 ckdr;

		get_ckd_reg_fixed_thin(rec, ckdr, luts, sids, reg_mode, egfr_mode);
		ckdr.pid = pid;

		if (ckdr.censor < 2) {
			if (do_print)
				ckdr.print();
			creg.reg.push_back(ckdr);
		}
	}

	MLOG("finished going over %d pids\n", rep.pids.size());

	return 0;
}

//==================================================================================
// Diabetic Nephropathy
//==================================================================================
//....................................................................................................................................................
int create_diabetic_nephropathy_cohort_file(const string &diab_reg_file, const string &ckd_reg_file, const string &fcohort_out, int ckd_state_level)
{

	MLOG("Creating Diabetic Nephropathy cohort with files %s , %s\n", diab_reg_file.c_str(), ckd_reg_file.c_str());

	MLOG("Reading Diabetes registry %s\n", diab_reg_file.c_str());
	Registry<DiabetesRegRec> d_reg;
	if (d_reg.read_from_file(diab_reg_file) < 0) return -1;
	MLOG("Read %d diabetes reg records\n", d_reg.reg.size());

	MLOG("Reading ckd registry %s\n", ckd_reg_file.c_str());
	Registry<CKDRegRec2> ckd_reg;
	if (ckd_reg.read_from_file(ckd_reg_file) < 0) return -1;
	MLOG("Read %d ckd registry records\n", ckd_reg.reg.size());

	MedCohort dneph_cohort;

	int i = 0, j = 0, n = 0;

	while (i<d_reg.reg.size() && j<ckd_reg.reg.size()) {

		// skip diabetes censored records
		if (d_reg.reg[i].censor >= 3) { i++; continue; }

		// skip ckd censored records
		if (ckd_reg.reg[j].censor >= 2) { j++; continue; }

		// move diabetes up if its pid is below ckd
		if (d_reg.reg[i].pid < ckd_reg.reg[j].pid) { i++; continue; }

		// move ckd up if its pid is below diabetes
		if (d_reg.reg[i].pid > ckd_reg.reg[j].pid) { j++; continue; }

		// same pid - verifying
		assert(d_reg.reg[i].pid == ckd_reg.reg[j].pid);

		int pid = d_reg.reg[i].pid;

		// check if diabetic and if so ... set starting date
		int start_diabetic = d_reg.reg[i].rc_diabetic[0];

		if (start_diabetic > 0) {
			// check if has renal information after start_diabetic date
			int max_renal_date = max(ckd_reg.reg[j].creatinine_from_to[1], ckd_reg.reg[j].urine_from_to[1]);
			int min_renal_date = ckd_reg.reg[j].creatinine_from_to[0];
			if (min_renal_date == 0 || (ckd_reg.reg[j].urine_from_to[0] > 0 && ckd_reg.reg[j].urine_from_to[0] < min_renal_date))
				min_renal_date = ckd_reg.reg[j].urine_from_to[0];

			// there are several cases here

			// case1: start_d -> before_ckd -> ckd  :: t_ckd
			// case2: start_d -> before_ckd :: t_max_renal

			// other cases do not participate.

			// in case1 (1) the maximal range for samples is [start_d, ckd]
			// in case2 (0) the maximal range for samples is [start_d, max_renal]

			// for each we add the conditions of min_case, max_case, min_ctrl, max_ctrl

			int ckd_date = ckd_reg.reg[j].ckd_date; // not using rc_ckd_date at the moment as it seems too early
			if (ckd_state_level > 0) {
				ckd_date = ckd_reg.reg[j].ckd_state_first[ckd_state_level];
				for (int k=ckd_state_level; k<=4; k++) 
					if (ckd_date==0 || (ckd_reg.reg[j].ckd_state_first[k] > 0 && ckd_reg.reg[j].ckd_state_first[k] < ckd_date)) ckd_date = ckd_reg.reg[j].ckd_state_first[k];
			}

			if (max_renal_date > start_diabetic) {

				int from_date = 0, to_date = 0;
				int outcome_date = 0;
				float outcome = -1;

				from_date = max(start_diabetic, min_renal_date);
				to_date = max_renal_date;
				

				if (ckd_date > 0) {
					// case
					outcome_date = ckd_date;
					outcome = 1;

				}
				else {

					// control
					outcome_date = max_renal_date;
					outcome = 0;

				}

				if (to_date > from_date &&			// sanity
					outcome_date > from_date &&		// outcome must be after at least one single evidence
					outcome_date <= to_date)		// outcome must be before last possible time

					dneph_cohort.insert(pid, from_date, to_date, outcome_date, outcome);
			}

		}
		i++;
		j++;
		n++;
		if (n%10000 == 0) MLOG("diabetic nephropathy cohort creation: %d\n", n);
	}

	if (dneph_cohort.write_to_file(fcohort_out) < 0) {
		MERR("Failed writing file %s\n", fcohort_out.c_str());
		return -1;
	}

	MLOG("Wrote cohort file %s : %d records\n", fcohort_out.c_str(), dneph_cohort.recs.size());
	return 0;
}


//....................................................................................................................................................
int create_nephropathy_cohort_file(const string &ckd_reg_file, const string &fcohort_out, int ckd_state_level)
{

	MLOG("Creating General Nephropathy cohort with file %s\n", ckd_reg_file.c_str());

	MLOG("Reading ckd registry %s\n", ckd_reg_file.c_str());
	Registry<CKDRegRec2> ckd_reg;
	if (ckd_reg.read_from_file(ckd_reg_file) < 0) return -1;
	MLOG("Read %d ckd registry records\n", ckd_reg.reg.size());

	MedCohort neph_cohort;

	int j = 0, n = 0;

	while (j<ckd_reg.reg.size()) {

		// skip ckd censored records
		if (ckd_reg.reg[j].censor >= 2) { j++; continue; }

		int pid = ckd_reg.reg[j].pid;

		// check if has renal information after start_diabetic date
		int max_renal_date = max(ckd_reg.reg[j].creatinine_from_to[1], ckd_reg.reg[j].urine_from_to[1]);
		int min_renal_date = ckd_reg.reg[j].creatinine_from_to[0];
		if (min_renal_date == 0 || (ckd_reg.reg[j].urine_from_to[0] > 0 && ckd_reg.reg[j].urine_from_to[0] < min_renal_date))
				min_renal_date = ckd_reg.reg[j].urine_from_to[0];

		int ckd_date = ckd_reg.reg[j].ckd_date; // not using rc_ckd_date at the moment as it seems too early
		if (ckd_state_level > 0) {
			ckd_date = ckd_reg.reg[j].ckd_state_first[ckd_state_level];
			for (int k=ckd_state_level; k<=4; k++)
				if (ckd_date==0 || (ckd_reg.reg[j].ckd_state_first[k] > 0 && ckd_reg.reg[j].ckd_state_first[k] < ckd_date)) ckd_date = ckd_reg.reg[j].ckd_state_first[k];
		}

		int from_date = min_renal_date;
		int to_date = max_renal_date;
		int outcome_date = 0;
		float outcome = -1;

		if (ckd_date > 0) {
			// case
			outcome_date = ckd_date;
			outcome = 1;
		}
		else {
			// control
			outcome_date = max_renal_date;
			outcome = 0;
		}

		neph_cohort.insert(pid, from_date, to_date, outcome_date, outcome);
		j++;
		n++;
		if (n%10000 == 0) MLOG("nephropathy cohort creation: %d\n", n);
	}

	if (neph_cohort.write_to_file(fcohort_out) < 0) {
		MERR("Failed writing file %s\n", fcohort_out.c_str());
		return -1;
	}

	MLOG("Wrote cohort file %s : %d records\n", fcohort_out.c_str(), neph_cohort.recs.size());
	return 0;
}


//....................................................................................................................................................
int get_annual_dneph_stats(const string &diab_reg_fname, const string &ckd_reg_fname)
{
	MLOG("Reading Diabetes registry %s\n", diab_reg_fname.c_str());
	Registry<DiabetesRegRec> d_reg;
	if (d_reg.read_from_file(diab_reg_fname) < 0) return -1;
	MLOG("Read %d diabetes reg records\n", d_reg.reg.size());

	MLOG("Reading ckd registry %s\n", ckd_reg_fname.c_str());
	Registry<CKDRegRec2> ckd_reg;
	if (ckd_reg.read_from_file(ckd_reg_fname) < 0) return -1;
	MLOG("Read %d ckd registry records\n", ckd_reg.reg.size());

	int i = 0, j = 0, n = 0;
	map<int, DiabNephStat> stats;
	for (int y=1900; y<=2100; y++) {
		DiabNephStat dns;
		stats[y] = dns;
	}

	while (i<d_reg.reg.size() && j<ckd_reg.reg.size()) {

		if (d_reg.reg[i].censor >= 3) { i++; continue; }
		if (ckd_reg.reg[j].censor >= 2) { j++; continue; }

		if (d_reg.reg[i].pid < ckd_reg.reg[j].pid) { i++; continue; }
		if (d_reg.reg[i].pid > ckd_reg.reg[j].pid) { j++; continue; }

		// same pid
		assert(d_reg.reg[i].pid == ckd_reg.reg[j].pid);

		// check if diabetic and if so ... set starting date
		int start_diabetic = d_reg.reg[i].rc_diabetic[0];


		if (start_diabetic > 0) {
			// check if has renal information after start_diabetic date
			int max_renal_date = max(ckd_reg.reg[j].creatinine_from_to[1], ckd_reg.reg[j].urine_from_to[1]);
			int ckd_date = ckd_reg.reg[j].ckd_date; // not using rc_ckd_date at the moment as it seems too early

			int to_no_ckd_date = max_renal_date;
			if (ckd_date > 0) {
				to_no_ckd_date = ckd_date;
				if (ckd_date > start_diabetic)
					stats[ckd_date/10000].n_new_ckd++;
				// counting ckd years
				for (int y=max(start_diabetic,ckd_date); y<=max_renal_date; y+=10000)
					stats[y/10000].n_ckd++;
			}

			for (int y=start_diabetic; y<=to_no_ckd_date; y+=10000)
				stats[y/10000].n_no_ckd++;

		}
		i++;
		j++;
		n++;
		if (n%10000 == 0) MLOG("diabetic nephropathy reg creation: %d\n", n);
	}

	for (int y=2000; y<=2016; y++) {
		int total = stats[y].n_ckd + stats[y].n_no_ckd - stats[y].n_new_ckd;
		MLOG("Diabetic Nephropathy : year %4d : total %d no_ckd %6d %5.3f ckd %6d %5.3f new_ckd %6d %5.3f %5.3f\n",
			y, total,
			stats[y].n_no_ckd, (float)stats[y].n_no_ckd/(float)total,
			stats[y].n_ckd, (float)stats[y].n_ckd/(float)total,
			stats[y].n_new_ckd, (float)stats[y].n_new_ckd/(float)total, (float)stats[y].n_new_ckd/(float)stats[y].n_no_ckd);
	}

	return 0;
}