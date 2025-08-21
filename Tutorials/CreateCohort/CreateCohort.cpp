//
// An example app to create .cohort files for tutorials
//
// The app can be handy to create a cohort with the following options:
// (1) Filter on Ages, Gender, No. of tests of each kind from a list
// (2) Future Value option (single measurement, or more: the last one) :
//     (a) patient starts at a signal X with values in range BASELINE=[base_min, base_max]
//     (b) patient either stays in BASELINE or evolves into the range OUTCOME=[out_min, out_max] at least K times (the K-th time is the outcome time)
// (3) ReadCodes signals and keys given in a file. This can be used to find the first time a readcode from a group appeared, 
//     or the first time a drug from a drug list appeared.
// (4) Option to start at the times of a category=C from a given cohort.
// (5) Option to create a regression problem cohort.
//

#include <string>
#include <iostream>
#include <boost/program_options.hpp>
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <InfraMed/InfraMed/InfraMed.h>
#include <MedUtils/MedUtils/MedCohort.h>
#include <MedTime/MedTime/MedTime.h>


#include <Logger/Logger/Logger.h>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
using namespace std;
namespace po = boost::program_options;

enum outcome_types {
	TYPE_DEATH = 0,
	TYPE_VAL = 1,
	TYPE_CATEG = 2
};

struct CreateCohortParams {
	string outcome_type;
	int type;
	string outcome_sig;
	vector<string> categs;
	float min_val, max_val;
	int min_date, max_date;
	int min_age, max_age;
	vector<string> forced_sigs;
	int min_count;
	int end_on_forced;
	float min_follow_up;

	vector<string> all_sigs; // all sigs to read to make a decision

	string rep_fname;
	string out_cohort;

	int time_ch = 0, val_ch = 0; // for outcome_sig

	int death_sid;
	int byear_sid;
	int startdate_sid;
	int enddate_sid;
	int outcome_sid = -1;
	vector<int> forced_sids;

	vector<char> categ_lut;
};

int get_codes_from_file(const string &fname, vector<string> &codes);

//=========================================================================================================
int read_run_params(int argc, char *argv[], po::variables_map& vm, CreateCohortParams &params) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value("/home/Repositories/THIN/thin_jun2017/thin.repository"), "repository file name")
			("outcome_type", po::value<string>()->default_value(""), "death, val, categ")
			("outcome_sig", po::value<string>()->default_value(""), "RC, DEATH, Drug, DM_Registry, etc...")
			("outcome_categs", po::value<string>()->default_value(""), "file with read_codes or Drugs (or other categories) defining cases")
			("min_val", po::value<float>()->default_value(0), "min range of values to define a case")
			("max_val", po::value<float>()->default_value(999999), "max range of values to define a case")
			("min_follow_up", po::value<float>()->default_value(0), "minimal followup in years to enter cohort")
			("forced_sigs", po::value<string>()->default_value(""), "list of signals forced to have at least min_count before entry to cohort")
			("min_count", po::value<int>()->default_value(0), "min count of signals to enter the cohort")
			("end_on_forced", po::value<int>()->default_value(0), "if 1 - cohort must end on the last of the forced_sigs")
			("min_date", po::value<int>()->default_value(0), "min date to enter the cohort")
			("max_date", po::value<int>()->default_value(99999999), "max date to leave the cohort")
			("min_age", po::value<int>()->default_value(0), "min age to enter the cohort")
			("max_age", po::value<int>()->default_value(999), "max age to leave the cohort")

			("out_cohort", po::value<string>()->default_value("out.cohort"), "output cohort")
			;


		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);

		MLOG("=========================================================================================\n");
		MLOG("Command Line:");
		for (int i=0; i<argc; i++) MLOG(" %s", argv[i]);
		MLOG("\n");
		MLOG("..........................................................................................\n");
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}

	// moving params to params
	params.rep_fname = vm["rep"].as<string>();
	params.out_cohort = vm["out_cohort"].as<string>();
	params.outcome_type = vm["outcome_type"].as<string>();
	if (params.outcome_type == "death") params.type = TYPE_DEATH;
	else if (params.outcome_type == "val") params.type = TYPE_VAL;
	else params.type = TYPE_CATEG;
	params.outcome_sig = vm["outcome_sig"].as<string>();
	params.min_val = vm["min_val"].as<float>();
	params.max_val = vm["max_val"].as<float>();
	params.min_follow_up = vm["min_follow_up"].as<float>();
	params.min_date = vm["min_date"].as<int>();
	params.max_date = vm["max_date"].as<int>();
	params.min_age = vm["min_age"].as<int>();
	params.max_age = vm["max_age"].as<int>();
	params.min_count = vm["min_count"].as<int>();
	params.end_on_forced = vm["end_on_forced"].as<int>();
	boost::split(params.forced_sigs, vm["forced_sigs"].as<string>(), boost::is_any_of(","));

	params.all_sigs = params.forced_sigs;
	vector<string> add_ons ={ "BYEAR", "STARTDATE", "ENDDATE", "DEATH" };
	if (params.outcome_sig != "") add_ons.push_back(params.outcome_sig);
	params.all_sigs.insert(params.all_sigs.end(), add_ons.begin(), add_ons.end());


	// read categs file
	vector<string> categs;
	if (vm["outcome_categs"].as<string>() != "") {
		if (get_codes_from_file(vm["outcome_categs"].as<string>(), params.categs) < 0)
			return -1;
	}

	return 0;
}

//..................................................................................................................
int get_codes_from_file(const string &fname, vector<string> &codes)
{
	codes.clear();
	if (fname == "") return 0;

	ifstream inf(fname);

	if (!inf) {
		MERR("ERROR: Can't open file %s for read\n", fname.c_str());
		return -1;
	}

	string curr_line;
	while (getline(inf, curr_line)) {
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {

			if (curr_line[curr_line.size() - 1] == '\r')
				curr_line.erase(curr_line.size() - 1);

			vector<string> fields;
			boost::split(fields, curr_line, boost::is_any_of(" \t"));

			if (fields.size() > 0)
				codes.push_back(fields[0]);
		}
	}

	inf.close();
	MLOG("Read %d codes from file %s\n", codes.size(), fname.c_str());

	return 0;
}

//=========================================================================================================
int get_cohort_rec(MedRepository &rep, CreateCohortParams &params, int pid, CohortRec &crec)
{
	//MLOG("get_cohort_rec:: Working on pid %d\n", pid);
	crec.from = 0; // signaling no valid record for this pid

	// check for outcome
	int outcome = 0;
	int outcome_date = 0;
	int len;
	if (params.type == TYPE_DEATH) {
		SVal *sdv = (SVal *)rep.get(pid, params.death_sid, len);
		if (len > 0) {
			outcome = 1;
			outcome_date = (int)(sdv[0].val);
			//MLOG("DEATH pid %d : %d\n", pid, outcome_date);
		}
	}
	else if (params.type == TYPE_VAL) {
		UniversalSigVec usv;
		rep.uget(pid, params.outcome_sid, usv);
		for (int i=0; i<usv.len; i++) {
			float i_val = usv.Val(i, params.val_ch);
			if (i_val >= params.min_val && i_val <= params.max_val) {
				outcome = 1;
				outcome_date = usv.Time(i, params.time_ch);
				break;
			}
		}
	}
	else if (params.type == TYPE_CATEG && params.categs.size() > 0) {
		UniversalSigVec usv;
		rep.uget(pid, params.outcome_sid, usv);
		for (int i=0; i<usv.len; i++) {
			int i_val = (int)usv.Val(i, params.val_ch);
			if (params.categ_lut[i_val]) {
				outcome = 1;
				outcome_date = usv.Time(i, params.time_ch);
				break;
			}
		}
	}

	// now starting to calculate the times for start and end of this cohort rec
	//MLOG("after outcome : pid is %d\n", pid);

	// initializing with start-end dates
	int dstart, dend;
	SVal *sdv_s = (SVal *)rep.get(pid, params.startdate_sid, len);
	if (len > 0)
		dstart = (int)(sdv_s[0].val);
	else
		return 0; // NO STARTDATE FOR PID

	SVal *sdv_e = (SVal *)rep.get(pid, params.enddate_sid, len);
	if (len > 0)
		dend = (int)(sdv_e[0].val);
	else
		return 0; // NO ENDDATE FOR PID

	if (dend < dstart) return 0; // NO Valid Period

	//MLOG("Before death : pid is %d\n", pid);
	// check death
	SVal *sdv_d = (SVal *)rep.get(pid, params.death_sid, len);
	if (len > 0) {
		int d = (int)(sdv_d[0].val);
		if (d < dend)
			dend = d;
		if (dend < dstart) return 0; // NO Valid Period
	}


	//MLOG("Before follow_up : pid is %d\n", pid);
	// check minimal follow_up
	if (params.min_follow_up > 0) {
		int days = (int)(params.min_follow_up * 365);
		int dstart_days = med_time_converter.convert_times(MedTime::Date, MedTime::Days, dstart);
		dstart_days += days;
		dstart = med_time_converter.convert_times(MedTime::Days, MedTime::Date, dstart_days);
		if (dend < dstart) return 0; // NO Valid Period
	}


	//MLOG("Before min/max dates : pid is %d , dstart %d dend %d , min_date %d max_date %d\n", pid, dstart, dend, params.min_date, params.max_date);
	// check min/max dates
	if (params.min_date > dstart) dstart = params.min_date;
	if (params.max_date < dend) dend = params.max_date;
	if (dend < dstart) return 0; // NO Valid Period



	//MLOG("Before forced_sigs : pid is %d\n", pid);
	// check forced_sigs
	if (params.forced_sids.size() > 0) {
		vector<int> all_dates;
		UniversalSigVec usv;
		//MLOG("%d forced sigs\n", params.forced_sids.size());
		for (auto sid : params.forced_sids) {
			rep.uget(pid, sid, usv);
			for (int i=0; i<usv.len; i++)
				all_dates.push_back(usv.Time(i));
		}
		//MLOG("%d dates min_count %d\n", all_dates.size(), params.min_count);
		sort(all_dates.begin(), all_dates.end());
		if (all_dates.size() >= params.min_count) {
			if (all_dates[params.min_count-1] > dstart)
				dstart = all_dates[params.min_count-1];

			if (params.end_on_forced) {
				if (all_dates.back() < dend)
					dend = all_dates.back();
			}
		}
		else {
			return 0; // not enough forced sigs
		}

		if (dend < dstart) return 0; // NO Valid Period
	}


	//MLOG("Before ages : pid is %d\n", pid);
	// check ages
	SVal *sdv_y = (SVal *)rep.get(pid, params.byear_sid, len);
	if (len > 0) {

		int byear = (int)(sdv_y[0].val);
		int min_d = (byear + params.min_age)*10000 + 101;
		int max_d = (byear + params.max_age)*10000 + 1230;

		if (min_d > dstart) dstart = min_d;
		if (max_d < dend) dend = max_d;
		if (dend < dstart) return 0; // NO Valid Period
	}

	//MLOG("After all : pid is %d : dstart %d dend %d outcome %d outcome_date %d\n", pid);

	// finally - we got to a state in which we have the outcome , and dstart - dend period.
	// we pack it now into a record.

	if (outcome == 1 && outcome_date < dstart) return 0; // whole period is already after outcome

	if (outcome == 1 && outcome_date > dend) outcome = 0; // outcome not in cohort range

	if (outcome == 0) outcome_date = dend;

	crec.from = dstart;
	crec.to = dend;
	crec.outcome = (float)outcome;
	crec.outcome_date = outcome_date;
	crec.pid = pid;

	return 1;
}

//=========================================================================================================
int main(int argc, char *argv[])
{
	int rc = 0;
	po::variables_map vm;
	CreateCohortParams params;

	// Reading run Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm, params);
	assert(rc >= 0);

	// read rep for all signals
	MedRepository rep;
	if (rep.read_all(params.rep_fname, {}, params.all_sigs) < 0) {
		return -1;
	}

	// initializing some sids
	params.death_sid = rep.sigs.sid("DEATH");
	params.byear_sid = rep.sigs.sid("BYEAR");
	params.startdate_sid = rep.sigs.sid("STARTDATE");
	params.enddate_sid = rep.sigs.sid("ENDDATE");
	if (params.outcome_sig != "") params.outcome_sid = rep.sigs.sid(params.outcome_sig);
	for (auto s : params.forced_sigs)
		params.forced_sids.push_back(rep.sigs.sid(s));


	// get categ if needed
	if (params.categs.size() > 0) {
		rep.dict.prep_sets_lookup_table(rep.dict.section_id(params.outcome_sig), params.categs, params.categ_lut);
	}

	vector<CohortRec> crecs(rep.pids.size()); // working like this to allow easy parallelization later

	// going over pids one by one and entering cohort
	for (int i=0; i<rep.pids.size(); i++) {
		if (get_cohort_rec(rep, params, rep.pids[i], crecs[i]) < 0) {
			MERR("ERROR: Failed get cohort for pid %d\n", rep.pids[i]);
			return -1;
		}
	}

	MedCohort cohort;
	for (auto &crec : crecs)
		if (crec.from > 0)
			cohort.recs.push_back(crec);

	cohort.write_to_file(params.out_cohort);

	return 0;
}
