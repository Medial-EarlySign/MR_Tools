#include "Helper.h"
#include <fenv.h>
#include "Cmd_Args.h"
#include <MedStat/MedStat/MedBootstrap.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
#if defined(__unix__)
	feenableexcept(FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW);
#endif
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;
	map<string, map<string, float>> bt, bt2;

	read_pivot_bootstrap_results(args.file1, bt);
	read_pivot_bootstrap_results(args.file2, bt2);
	unordered_set<string> sel(args.cohort_list.begin(), args.cohort_list.end());

	for (auto it = bt.begin(); it != bt.end(); ++it)
		if ((sel.empty() || sel.find(it->first) != sel.end()) && bt2.find(it->first) == bt2.end())
			MWARN("Missing Cohort %s in %s\n", it->first.c_str(), args.file2.c_str());
	for (auto it = bt2.begin(); it != bt2.end(); ++it)
		if ((sel.empty() || sel.find(it->first) != sel.end()) && bt.find(it->first) == bt.end())
			MWARN("Missing Cohort %s in %s\n", it->first.c_str(), args.file1.c_str());

	vector<string> to_compare;
	for (auto it = bt.begin(); it != bt.end(); ++it)
		if (sel.empty() || sel.find(it->first) != sel.end())
			to_compare.push_back(it->first);
	MLOG("Comparing %zu cohorts\n", to_compare.size());
	if (to_compare.size() != args.cohort_list.size())
		MWARN("Request cohort list size was %zu, found %zu\n", args.cohort_list.size(), to_compare.size());

	if (!args.output.empty())
	{
		ofstream fw(args.output);
		if (!fw.good())
			MTHROW_AND_ERR("Can't open file %s for writing\n", args.output.c_str());
		fw.close(); //flush and write empty file
	}

	for (const string &cohort : to_compare)
	{
		MLOG("Comparing %s\n", cohort.c_str());
		compare_bootstrap_maps(cohort, bt.at(cohort), bt2.at(cohort), "file1", "file2",
			args.diff_allowed_abs, args.diff_allowed_ratio, args.diff_reject_abs, args.diff_reject_ratio,
			args.tests_list, args.output);
	}


	return 0;
}