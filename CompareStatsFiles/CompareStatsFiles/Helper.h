#ifndef _HELPER_H__
#define _HELPER_H__
#include <string>
#include <vector>
#include <map>

using namespace std;

void compare_maps(const map<string, float> &a, const map<string, float> &b,
	const string &name1, const string &name2, float diff_allowed = 0);

void compare_bootstrap_maps(const string &test_name, const map<string, float> &a, const map<string, float> &b,
	const string &name1, const string &name2, float diff_allowed, float diff_allowed_ratio, 
	float diff_reject_abs, float diff_reject_ratio, const vector<string> &tests, const string &log_file = "");

#endif
