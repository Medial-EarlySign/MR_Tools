//
// MedTimeTests
//
// test program for the MedTime Library
//

#include <iostream>
#include <string>
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string.hpp>
#include <vector>
#include <Logger/Logger/Logger.h>
#include <MedTime/MedTime/MedTime.h>

#define LOCAL_SECTION LOG_CONVERT
#define LOCAL_LEVEL	LOG_DEF_LEVEL

using namespace std;
using namespace boost;

int initialize_time_tests_string(string &tests)
{
	// format to add : from_type,to_type,input,expected_output + "\n";

	tests += "Date,Days,20170206,42770\n";
	tests += "Days,Date,42770,20170206\n";
	tests += "Date,Days,19000101,0\n";
	tests += "Days,Date,0,19000101\n";
	tests += "Days,Hours,10,240\n";
	tests += "Days,Minutes,5,7200\n";
	tests += "Hours,Days,252,10.5,D\n";
	tests += "Date,Years,20170206,117\n";
	tests += "Date,Hours,20170206,1026480\n";
	tests += "Date,Minutes,20170206,61588800\n";
	tests += "Years,Date,117,20170101\n";
	tests += "Hours,Date,1026480,20170206\n";
	tests += "Minutes,Date,61588800,20170206\n";
	tests += "Days,Years,42770,117\n";
	tests += "Days,Hours,42770,1026480\n";
	tests += "Days,Minutes,42770,61588800\n";
	tests += "Hours,Days,1026480,42770\n";
	tests += "Minutes,Days,61588800,42770\n";
	tests += "Hours,Minutes,1026480,61588800\n";
	tests += "Minutes,Hours,61588800,1026480\n";
	tests += "Date,Months,19020615,29.5,D\n";
	tests += "Years,Minutes,2,1051200\n";
	tests += "Date,Years,19020630,2.5,D\n";

	return 0;
}



int run_time_test(string &test)
{
	vector<string> fields;
	split(fields, test, boost::is_any_of(","));

	// integer
	if (fields.size() == 4) {
		MLOG("Running Test: %s ...\n",test.c_str());
		int from_type = med_time_converter.string_to_type(fields[0]);
		int to_type = med_time_converter.string_to_type(fields[1]);
		int in_time = stoi(fields[2]);
		int expected = stoi(fields[3]);

		int res = med_time_converter.convert_times(from_type, to_type, in_time);
		MLOG("res %d , expected %d .... ", res, expected);
		if (res == expected) {
			MLOG("PASSED\n");
			return 1;
		}
		else {
			MLOG("FAILED\n");
			return 0;
		}

	} else if (fields.size() == 5) {
		MLOG("Running Test: %s ...\n", test.c_str());
		int from_type = med_time_converter.string_to_type(fields[0]);
		int to_type = med_time_converter.string_to_type(fields[1]);
		int in_time = stoi(fields[2]);
		double expected = stod(fields[3]);

		double res = med_time_converter.convert_times_D(from_type, to_type, in_time);
		MLOG("res %f , expected %f .... ", res, expected);
		if (abs(res-expected) < 0.1) {
			MLOG("PASSED\n");
			return 1;
		}
		else {
			MLOG("FAILED\n");
			return 0;
		}

	} else {
		MERR("Can't run test %s\n", test.c_str());
	}

	return -1;
}

int run_all_time_tests(string &tests)
{
	vector<string> fields;
	split(fields, tests, boost::is_any_of("\n"));

	int n_tests=0, n_pos=0;
	MLOG("Running MedTime tests\n");
	for (auto &test : fields) {
		int rc = run_time_test(test);
		if (rc >= 0) n_tests++;
		if (rc >= 1) n_pos++;
	}

	MLOG("\n\nTotal Summary: passed %d/%d tests\n", n_pos, n_tests);
	return 0;
}

int main(int argc, char **argv)
{
	string tests;

	initialize_time_tests_string(tests);
	run_all_time_tests(tests);
}
