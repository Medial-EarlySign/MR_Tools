//
// InfraMedTests
//
// Tools to test and measure performance of the InfraMed library
//
#include "Catch-master/single_include/catch.hpp"

#include "InfraMedTests.h"
#include <boost/program_options.hpp>
#include <InfraMed/InfraMed/InfraMed.h>
#include <InfraMed/InfraMed/MedConvert.h>
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedTime/MedTime/MedTime.h>
#include <Logger/Logger/Logger.h>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;
using namespace boost;


//=============================================================================
int parse_parameters(int argc, char *argv[], IMTestAppParams &ap)
{
	po::options_description desc("Program options");
	po::variables_map vm;

	desc.add_options()
		("help", "help & exit")
		("h", "help & continue")

		// repository creation and printing
		("test_unified_API", "get and print records using old and new API's and verify the results")
		("API_performance", "test API performance on some task")

		// general params
		("rep", po::value<string>(&ap.rep_fname)->default_value("/server/Work/CancerData/Repositories/THIN/build_jan2017/thin.repository"), "repository file name")

		("pid", po::value<int>(&ap.pid)->default_value(5000300), "pid number")
		("sig", po::value<string>(&ap.sig_name)->default_value("Hemoglobin"), "signal name")

		("seed", po::value<int>(&ap.random_seed)->default_value(1948), "pid number")
		("debug", "add to get full debug logs");

	po::store(po::command_line_parser(argc, argv).options(desc).run(), vm);
	po::notify(vm);

	if (vm.count("help")) {
		cerr << desc << "\n";
		return -1;
	}

	if (vm.count("h")) {
		cerr << desc << "\n";
	}


	ap.options.resize(MAX_OPTION, 0);

	if (vm.count("test_unified_API")) ap.options[OPTION_TEST_UNIFIED_API] = 1;
	if (vm.count("API_performance")) ap.options[OPTION_API_PERFORMANCE] = 1;

	if (vm.count("debug")) global_logger.init_all_levels(0);

	//set_rand_seed(ap.random_seed);

	return 0;
}

//=====================================================================================================
int print_rep_pig_sig_unified(string &rep_fname, int pid, string &sig_name)
{
	MedRepository rep;

	if (rep.read_all(rep_fname, { pid }, { sig_name }) < 0) {
		MERR("Error reading repository file %s\n", rep_fname.c_str());
		return -1;
	}

	int len;
	void *sdata = rep.get(pid, sig_name, len);


	int sid = rep.sigs.sid(sig_name);
	int stype = rep.sigs.type(sig_name);


	UniversalSigVec usv;
	rep.uget(pid, sid, usv);

	MLOG("pid %d sig_name %s sid %d stype %d n_time_channels %d n_val_channels %d time_unit %d\n", 
		pid, sig_name.c_str(), sid, stype, usv.n_time_channels(), usv.n_val_channels(), usv.time_unit());

	MLOG("-------------------------------------------------------------------------------------------------------------\n");
	for (int i=0; i<len; i++)
		MLOG("[%d] date %d minutes %d val %f\n", i, usv.Date(i), usv.Minutes(i), usv.Val(i));

	MLOG("-------------------------------------------------------------------------------------------------------------\n");
	for (int i=0; i<len; i++) {
		MLOG("[%d]",i);
		for (int j=0; j<usv.n_time_channels(); j++) MLOG(" (%d) date %d minutes %d", j, usv.Date(i, j), usv.Minutes(i, j));
		for (int j=0; j<usv.n_val_channels(); j++) MLOG(" (%d) val %f", j, usv.Val(i, j));
		MLOG("\n");
	}

	MLOG("-------------------------------------------------------------------------------------------------------------\n");
	if (stype == (int)T_Value) {
		SVal *sv = (SVal *)sdata;
		for (int i=0; i<len; i++)
			MLOG("[%d] val %f :: val %f\n", i, usv.Val(i), sv[i].val);
	}

	if (stype == (int)T_DateVal) {
		SDateVal *sdv = (SDateVal *)sdata;
		for (int i=0; i<len; i++)
			MLOG("[%d] date %d minutes %d val %f :: date %d val %f\n", i, usv.Date(i), usv.Minutes(i), usv.Val(i), sdv[i].date, sdv[i].val);
	}

	if (stype == (int)T_TimeVal) {
		STimeVal *stv = (STimeVal *)sdata;
		for (int i=0; i<len; i++)
			MLOG("[%d] date %d minutes %d val %f :: time %d val %f\n", i, usv.Date(i), usv.Minutes(i), usv.Val(i), stv[i].time, stv[i].val);
	}

	if (stype == (int)T_DateVal2) {
		SDateVal2 *sdv = (SDateVal2 *)sdata;
		for (int i=0; i<len; i++)
			MLOG("[%d] date %d minutes %d val %f,%f :: date %d val %f,%d\n", 
				i, usv.Date(i), usv.Minutes(i), usv.Val(i,0), usv.Val(i,1), sdv[i].date, sdv[i].val, sdv[i].val2);
	}

	return 0;
}


//=====================================================================================================
int UnifiedSigTimeMeasure(string &rep_fname, string &sig_name)
{
	MedPidRepository rep;

	if (rep.read_all(rep_fname, {}, { sig_name }) < 0) {
		MERR("Error: FAILED reading repository %s\n", rep_fname.c_str());
		return -1;
	}

	MedTimer timer;
	double sum_all_vals;
	double sum_all_times;
	int sid = rep.sigs.sid(sig_name);
	int stype = rep.sigs.type(sig_name);

	for (int round=0; round<10; round++) {
		// use universal API
		timer.start();
		UniversalSigVec usv;
		sum_all_vals = 0;
		sum_all_times = 0;
		for (auto pid : rep.pids) {
			//usv.init(stype);
			if (rep.uget(pid, sid, usv) != NULL) {
				for (int i=0; i<usv.len; i++) {
					sum_all_vals += usv.Val(i);
					sum_all_times += (double)usv.Time(i);
				}
			}
		}
		timer.take_curr_time();
		MLOG("Universal API: sum %g %g time %g\n", sum_all_vals, sum_all_times, timer.diff_milisec());

#if 1
		// use regular API
		if (rep.sigs.type(sid) == T_DateVal) {
			timer.start();
			SDateVal *sdv;
			sum_all_vals = 0;
			sum_all_times = 0;
			int len;
			for (auto pid : rep.pids) {
				if ((sdv = (SDateVal *)rep.get(pid, sid, len)) != NULL) {
					for (int i=0; i<len; i++) {
						sum_all_vals += sdv[i].val;
						sum_all_times += sdv[i].date;
					}
				}
			}
			timer.take_curr_time();
			MLOG("Regular SDateVal API: sum %g %g time %g\n", sum_all_vals, sum_all_times, timer.diff_milisec());
		}
#endif
	}

	return 0;

}

string rep = "/server/Work/CancerData/Repositories/THIN/build_jan2017/thin.repository";
string sig = "Hemoglobin";

TEST_CASE("Just load a repo with some signals", "[repo1]") {
	MedPidRepository r;
	vector<int> ids;
	int rc = r.read_all(rep, ids, { sig });
	REQUIRE(rc == 0);
}

TEST_CASE("Test print_rep_pig_sig_unified", "[repo2]") {
	int rc = print_rep_pig_sig_unified(rep, 5000300, sig);
	REQUIRE(rc == 0);
}

TEST_CASE("Test UnifiedSigTimeMeasure", "[repo3]") {
	int rc = UnifiedSigTimeMeasure(rep, sig);
	REQUIRE(rc == 0);
}

//=====================================================================================================
//========== M A I N                   ================================================================
//=====================================================================================================
int old_main(int argc, char *argv[])
{
	IMTestAppParams ap;

	if (parse_parameters(argc, argv, ap) < 0)
		return -1;

	if (ap.options[OPTION_TEST_UNIFIED_API]) {
		return print_rep_pig_sig_unified(ap.rep_fname, ap.pid, ap.sig_name);
	}

	if (ap.options[OPTION_API_PERFORMANCE]) {
		return UnifiedSigTimeMeasure(ap.rep_fname, ap.sig_name);
	}
	return 0;
}