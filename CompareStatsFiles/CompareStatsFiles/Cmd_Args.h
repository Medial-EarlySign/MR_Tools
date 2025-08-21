#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string cohort_list_s;
	string tests_list_s;
public:
	string file1;
	string file2;
	float diff_allowed_abs, diff_allowed_ratio;
	float diff_reject_abs, diff_reject_ratio;
	vector<string> cohort_list;
	vector<string> tests_list;
	string output;

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("file1", po::value<string>(&file1)->required(), "file1 path")
			("file2", po::value<string>(&file2)->required(), "file2 path")
			("diff_allowed_abs", po::value<float>(&diff_allowed_abs)->default_value(0), "max diff allowed to report OK")
			("diff_allowed_ratio", po::value<float>(&diff_allowed_ratio)->default_value((float)0.05), "max diff allowed in ratio report OK")
			("diff_reject_abs", po::value<float>(&diff_reject_abs)->default_value(0), "max diff that below it report OK")
			("diff_reject_ratio", po::value<float>(&diff_reject_ratio)->default_value((float)0.01), "max diff that below it in ratio report OK")
			("cohort_list", po::value<string>(&cohort_list_s)->default_value(""), "cohort list to test. if empty will take all")
			("tests_list", po::value<string>(&tests_list_s)->default_value(""), "test list to test if empty will take all. options: mean_diff_bigger_ratio,mean_not_in_ci,no_intersection_ci,diff_mean_bigger")
			("output", po::value<string>(&output)->default_value(""), "output to write results. empty to skip")
			;

		init(options);
	}

	void post_process() {
		if (!cohort_list_s.empty())
			boost::split(cohort_list, cohort_list_s, boost::is_any_of(",;"));
		if (!tests_list_s.empty())
			boost::split(tests_list, tests_list_s, boost::is_any_of(",;"));
	}
};
#endif