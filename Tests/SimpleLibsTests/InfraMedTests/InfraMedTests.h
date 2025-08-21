//===================================================================================================
// InfraMedTests.h
//===================================================================================================

#ifndef __INFRA_MED_TESTS_H__
#define __INFRA_MED_TESTS_H__

#define OPTION_TEST_UNIFIED_API			0
#define OPTION_API_PERFORMANCE			1

#define MAX_OPTION					100

#include <vector>
#include <string>
using namespace std;

struct IMTestAppParams {

	vector<int> options;

	string rep_fname;

	int	pid;
	string sig_name;

	int random_seed;
};


#endif
