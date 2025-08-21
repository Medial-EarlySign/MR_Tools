#include "diabetes.h"
#include <MedUtils/MedUtils/MedCohort.h>

//==================================================================================================================
int get_all_rc_reg(const string &rep_name, string read_codes_fname, vector<int> &pid_list, Registry<RCRegRec> &rcreg)
{
	MedRepository rep;

	MLOG("Creating thin rc registry from file %s\n", read_codes_fname.c_str());
	vector<string> signals ={ "RC_Demographic", "RC_History", "RC_Diagnostic_Procedures",
							  "RC_Radiology", "RC_Procedures", "RC_Admin", "RC_Diagnosis", "RC_Injuries" };

	if (rep.read_all(rep_name, pid_list, signals) < 0) {
		MERR("ERROR: Failed reading repository %s\n", rep_name.c_str());
		return -1;
	}

	// prep sids
	vector<int> sids;
	for (auto& sname : signals)
		sids.push_back(rep.sigs.sid(sname));

	// prep lookup tables
	int section_id = rep.dict.section_id("RC_Diagnosis");
	vector<string> rcs;
	vector<char> lut;
	MLOG("Reading lut from file %s\n", read_codes_fname.c_str());
	if (read_RC_from_file(read_codes_fname, rcs) < 0) return -1;
	rep.dict.prep_sets_lookup_table(section_id, rcs, lut);

	rcreg.reg.clear();
	for (auto pid : rep.pids) {

		RCRegRec rc;
		rc.pid = pid;

		int first_date = 0;
		int n_tests = 0;
		int len;
		for (auto sid : sids) {
			SDateVal *sdv = (SDateVal *)rep.get(pid, sid, len);
			n_tests += len;
			for (int i=0; i<len; i++) {
				if (first_date > 0 && sdv[i].date >= first_date) break;
				if (lut[(int)sdv[i].val]) { first_date = sdv[i].date; break; }
			}
		}

		rc.first_rc = first_date;
		rc.n_tests = n_tests;
		if (n_tests > 5)
			rc.censored = 0;
		else
			rc.censored = 1;

		if (rc.censored == 0) {
			rcreg.reg.push_back(rc);
			rc.print();
		}

	}

	MOUT("finished going over %d pids , got %d non censored records\n", rep.pids.size(), rcreg.reg.size());

	return 0;
}

//==================================================================================
// Diabetic + Retinopathy Or CVD
//==================================================================================
//....................................................................................................................................................
int create_diabetic_complication_cohort_file(const string name, const string &diab_reg_file, const string &rc_reg_file, const string &fcohort_out)
{

	MLOG("Creating Diabetic %s cohort with files %s , %s\n", name.c_str(), diab_reg_file.c_str(), rc_reg_file.c_str());

	MLOG("Reading Diabetes registry %s\n", diab_reg_file.c_str());
	Registry<DiabetesRegRec> d_reg;
	if (d_reg.read_from_file(diab_reg_file) < 0) return -1;
	MLOG("Read %d diabetes reg records\n", d_reg.reg.size());

	MLOG("Reading %s registry %s\n", name.c_str(), rc_reg_file.c_str());
	Registry<RCRegRec> rc_reg;
	if (rc_reg.read_from_file(rc_reg_file) < 0) return -1;
	MLOG("Read %d %s registry records\n", rc_reg.reg.size(), name.c_str());

	MedCohort dcomp_cohort;

	int i = 0, j = 0, n = 0;


	while (i<d_reg.reg.size() && j<rc_reg.reg.size()) {

		// skip diabetes censored records
		if (d_reg.reg[i].censor >= 3) { i++; continue; }

		// skip rc censored records
		if (rc_reg.reg[j].censored >= 1) { j++; continue; }

		// move diabetes up if its pid is below rc
		if (d_reg.reg[i].pid < rc_reg.reg[j].pid) { i++; continue; }

		// move rc up if its pid is below diabetes
		if (d_reg.reg[i].pid > rc_reg.reg[j].pid) { j++; continue; }

		// same pid - verifying
		assert(d_reg.reg[i].pid == rc_reg.reg[j].pid);

		int pid = d_reg.reg[i].pid;

		// check if diabetic and if so ... set starting date
		int start_diabetic = d_reg.reg[i].rc_diabetic[0];

		if (start_diabetic > 0) {

			int from_date = start_diabetic;
			int to_date = d_reg.reg[i].rc_diabetic[1];
			int outcome_date = 0;
			float outcome = -1;

			if (rc_reg.reg[j].first_rc > 0) {

				// had a complication BEFORE or AFTER start diabetic
				outcome_date = rc_reg.reg[j].first_rc;
				outcome = 1;
				if (outcome_date > to_date) to_date = outcome_date;

			}
			else {

				// had no complication AFTER start diabetic
				outcome_date = to_date;
				outcome = 0;

			}

			if (to_date > from_date &&			// sanity
				outcome_date > from_date &&		// outcome must be after diabetes started
				outcome_date <= to_date)		// outcome must be before last possible time

				dcomp_cohort.insert(pid, from_date, to_date, outcome_date, outcome);
		}

		i++;
		j++;
		n++;
		if (n%10000 == 0) MLOG("diabetic %s cohort creation: %d\n", name.c_str(), n);
	}


	if (dcomp_cohort.write_to_file(fcohort_out) < 0) {
		MERR("Failed writing file %s\n", fcohort_out.c_str());
		return -1;
	}

	MLOG("Wrote cohort file %s : %d records\n", fcohort_out.c_str(), dcomp_cohort.recs.size());
	return 0;
}
