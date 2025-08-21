#include "Helper.h"
#include <unordered_set>
#include <algorithm>
#include <Logger/Logger/Logger.h>
#include <MedUtils/MedUtils/MedUtils.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

#ifndef max
#define max(a,b)            (((a) > (b)) ? (a) : (b))
#endif

#ifndef min
#define min(a,b)            (((a) < (b)) ? (a) : (b))
#endif

string add_str(string &str, const string &add) {
	if (!str.empty())
		str += ";";
	str += add;
	return str;
}

bool find_substr(const vector<string> &tests, const string &search) {
	for (size_t i = 0; i < tests.size(); ++i)
		if (tests[i].find(search) != string::npos)
			return true;
	return false;
}

bool is_similar(float mean1, float lower1, float upper1,
	float mean2, float lower2, float upper2, const vector<string> &tests, string &comp, float similar_mean_ratio) {

	float mean_diff_ratio = 0;
	float min_mean = min(abs(mean1), abs(mean2));
	if (min_mean > 0)
		mean_diff_ratio = abs(mean1 - mean2) / min_mean;

	if (tests.empty() || find_substr(tests, "mean_diff_bigger_ratio"))
		if (!(mean_diff_ratio <= similar_mean_ratio))
			comp = add_str(comp, "mean_diff_bigger_ratio_" + medial::print::print_obj(100 * similar_mean_ratio, "%2.2f%%"));
	if (tests.empty() || find_substr(tests, "mean_not_in_ci"))
		if (!((mean1 >= lower2 && mean1 <= upper2) ||
			(mean2 >= lower1 && mean2 <= upper1) ||
			(lower1 == lower2 && upper1 == upper2))) //means are inside CI of 95. like 2 stds in normal
			comp = add_str(comp, "mean_not_in_ci");
	if (tests.empty() || find_substr(tests, "no_intersection_ci"))
		if (lower1 > upper2 || lower2 > upper1)
			comp = add_str(comp, "no_intersection_ci");
	return  comp.empty();
}

bool is_rejected(float mean1, float lower1, float upper1, float mean2, float lower2, float upper2, float reject_abs, float reject_ratio) {
	float mean_diff_ratio = -1;
	float min_mean = min(abs(mean1), abs(mean2));
	float mean_diff_abs = abs(mean1 - mean2);
	if (min_mean > 0)
		mean_diff_ratio = mean_diff_abs / min_mean;
	if (mean_diff_abs <= reject_abs)
		return true;
	if (mean_diff_ratio > -1)
		return mean_diff_ratio <= reject_ratio;
	return false;
}

void compare_maps(const map<string, float> &a, const map<string, float> &b,
	const string &name1, const string &name2, float diff_allowed) {
	for (auto it = b.begin(); it != b.end(); ++it)
		if (a.find(it->first) == a.end())
			MWARN("Measure %s wasn't found in %s\n", it->first.c_str(), name1.c_str());
	for (auto it = a.begin(); it != a.end(); ++it)
	{
		if (b.find(it->first) == b.end())
			MWARN("Measure %s wasn't found in %s\n", it->first.c_str(), name2.c_str());
		float df = abs(it->second - b.at(it->first));

		if (df > diff_allowed)
			MWARN("Diff in measure %s. in %s=%f, in %s=%f, diff=%f\n", it->first.c_str(), name1.c_str(),
				it->second, name2.c_str(), b.at(it->first), df);
	}
}

string clean_measure(const string &meas) {
	vector<string> endings = { "_Mean", "_Obs", "_Std", "_CI.Upper.95", "_CI.Lower.95" };
	string final_m = meas;
	for (size_t i = 0; i < endings.size(); ++i)
		if (boost::ends_with(meas, endings[i]))
			boost::replace_tail(final_m, (int)endings[i].length(), "");
	return final_m;
}

void compare_bootstrap_maps(const string &test_name, const map<string, float> &a, const map<string, float> &b,
	const string &name1, const string &name2, float diff_allowed, float diff_allowed_ratio,
	float diff_reject_abs, float diff_reject_ratio, const vector<string> &tests, const string &log_file) {
	//let's list all test without _Mean, _CI.Lower.95, _CI.Upper.95, _Obs, _Std, Checksum
	vector<string> simple_compare = { "Checksum" };
	vector<string> ignore_list = { "run_id" };
	unordered_set<string> ignore_set(ignore_list.begin(), ignore_list.end());
	ofstream fw_log;
	if (!log_file.empty()) {
		fw_log.open(log_file, ofstream::app);
		if (!fw_log.good())
			MTHROW_AND_ERR("Error can't open %s for writing", log_file.c_str());
	}

	//compare simple checksum:
	for (const string &m : simple_compare)
	{
		ignore_set.insert(m);
		if (a.find(m) == a.end() && b.find(m) == b.end())
			continue;
		if (a.find(m) != a.end() && b.find(m) != b.end()) {
			if (a.at(m) != b.at(m))
				medial::print::log_with_file(fw_log, "%s\tDiff in Measure\t%s\tin\t%s=%f\tin\t%s=%f\n",
					test_name.c_str(), m.c_str(), name1.c_str(), a.at(m), name2.c_str(), b.at(m));
		}
		if (a.find(m) == a.end())
			medial::print::log_with_file(fw_log, "%s\tMissing Measure\t%s\tin\t%s\n", test_name.c_str(), m.c_str(), name1.c_str());
		if (b.find(m) == b.end())
			medial::print::log_with_file(fw_log, "%s\tMissing Measure\t%s\tin\t%s\n", test_name.c_str(), m.c_str(), name2.c_str());
	}
	for (auto it = b.begin(); it != b.end(); ++it)
		if (ignore_set.find(it->first) == ignore_set.end() && a.find(it->first) == a.end())
			medial::print::log_with_file(fw_log, "%s\tMissing Measure\t%s\tin\t%s\n", test_name.c_str(), it->first.c_str(), name1.c_str());
	for (auto it = a.begin(); it != a.end(); ++it)
		if (ignore_set.find(it->first) == ignore_set.end() && b.find(it->first) == b.end())
			medial::print::log_with_file(fw_log, "%s\tMissing Measure\t%s\tin\t%s\n", test_name.c_str(), it->first.c_str(), name2.c_str());

	//let's list all measure simple names:
	unordered_set<string> base_names;
	for (auto it = a.begin(); it != a.end(); ++it)
	{
		if (b.find(it->first) == b.end() || ignore_set.find(it->first) != ignore_set.end())
			continue;
		string base_m = clean_measure(it->first);
		base_names.insert(base_m);
	}
	vector<string> all_compare_ls(base_names.begin(), base_names.end());
	sort(all_compare_ls.begin(), all_compare_ls.end());

	int c = 0;
	for (const string &m : all_compare_ls)
	{
		string mean_val = m + "_Mean";
		string l_val = m + "_CI.Lower.95";
		string u_val = m + "_CI.Upper.95";
		if (a.find(mean_val) == a.end()) {
			medial::print::log_with_file(fw_log, "%s\tRebase Missing Measure\t%s\tin\t%s\n", test_name.c_str(), mean_val.c_str(), name1.c_str());
			continue;
		}
		if (a.find(l_val) == a.end()) {
			medial::print::log_with_file(fw_log, "%s\tRebase Missing Measure\t%s\tin\t%s\n", test_name.c_str(), l_val.c_str(), name1.c_str());
			continue;
		}
		if (a.find(u_val) == a.end()) {
			medial::print::log_with_file(fw_log, "%s\tRebase Missing Measure\t%s\tin\t%s\n", test_name.c_str(), u_val.c_str(), name1.c_str());
			continue;
		}
		if (b.find(mean_val) == b.end()) {
			medial::print::log_with_file(fw_log, "%s\tRebase Missing Measure\t%s\tin\t%s\n", test_name.c_str(), mean_val.c_str(), name2.c_str());
			continue;
		}
		if (b.find(l_val) == b.end()) {
			medial::print::log_with_file(fw_log, "%s\tRebase Missing Measure\t%s\tin\t%s\n", test_name.c_str(), l_val.c_str(), name2.c_str());
			continue;
		}
		if (b.find(u_val) == b.end()) {
			medial::print::log_with_file(fw_log, "%s\tRebase Missing Measure\t%s\tin\t%s\n", test_name.c_str(), u_val.c_str(), name2.c_str());
			continue;
		}

		float df = abs(a.at(mean_val) - b.at(mean_val));
		string problems = "";
		if (tests.empty() || find_substr(tests, "diff_mean_bigger"))
			if (df > diff_allowed)
				problems = add_str(problems, "diff_mean_bigger_" + medial::print::print_obj(diff_allowed, "%2.3f"));
		is_similar(a.at(mean_val), a.at(l_val), a.at(u_val), b.at(mean_val), b.at(l_val), b.at(u_val), tests, problems, diff_allowed_ratio);
		if (is_rejected(a.at(mean_val), a.at(l_val), a.at(u_val), b.at(mean_val), b.at(l_val), b.at(u_val), diff_reject_abs, diff_reject_ratio)) {
			problems = "";
			++c;
		}

		if (!problems.empty())
			medial::print::log_with_file(fw_log, "%s\tDiff in Measure %s\tin\t%s=%f[%f, %f]\tin\t%s=%f[%f, %f]\tdiff=\t%f\t, problems=\t%s\n", 
				test_name.c_str(), m.c_str(), name1.c_str(),
				a.at(mean_val), a.at(l_val), a.at(u_val), name2.c_str(),
				b.at(mean_val), b.at(l_val), b.at(u_val), df, problems.c_str());
	}
	if (c > 0)
		MLOG("Rejected count %d\n", c);
	if (!log_file.empty())
		fw_log.close();
}