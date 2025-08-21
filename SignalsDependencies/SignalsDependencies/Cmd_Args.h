#ifndef __PROGRAM__ARGS__H__
#define __PROGRAM__ARGS__H__

#include <boost/program_options.hpp>
#include <boost/spirit/home/support/detail/hold_any.hpp>
#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <iostream>
#include "MedUtils/MedUtils/MedUtils.h"
#include "Logger/Logger/Logger.h"
#include "MedUtils/MedUtils/MedEnums.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;

enum class stat_test {
	chi_square = 1,
	fisher = 2,
	mcnemar = 3,
	cmh = 4
};


class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	unordered_map<string, int> conv_map = {
		{ "chi-square", (int)stat_test::chi_square },
		{ "fisher", (int)stat_test::fisher },
		{ "mcnemar", (int)stat_test::mcnemar },
		{ "cmh", (int)stat_test::cmh}
	};
	void convert_type() {
		if (conv_map.find(stat_test_type) == conv_map.end())
			MTHROW_AND_ERR("couldn't find \"%s\" type. legal types are: %s\n", stat_test_type.c_str(),
				medial::io::get_list(conv_map).c_str());
		filter_stats_test = stat_test(conv_map[stat_test_type]);
	}
	string labeling_params_s;
	string inc_labeling_params_s;

	void post_process() {
		convert_type();
		if (output_debug && (output_value <= 0 || output_full_path == ""))
			MTHROW_AND_ERR("please provide output_value and output_full_path for debugging\n");
		if (output_debug)
			global_override = true;
		if (registry_path.empty() && registry_init_cmd.empty())
			MTHROW_AND_ERR("Please provide registry_path or registry_init_cmd to load registry");

		if (!labeling_params_s.empty())
			labeling_params.init_from_string(labeling_params_s);

		labeling_params.time_from = test_from_window;
		labeling_params.time_to = test_to_window;
		if (labeling_params_s.find("time_from") != string::npos)
			MWARN("Warning: got time_from in labeling_params - overriding value by test_from_window arg\n");
		if (labeling_params_s.find("time_to") != string::npos)
			MWARN("Warning: got time_to in labeling_params - overriding value by test_to_window arg\n");

		if (!inc_labeling_params_s.empty())
			inc_labeling_params.init_from_string(inc_labeling_params_s);
		if (inc_labeling_params_s.find("time_from") == string::npos)
			inc_labeling_params.time_from = 0;
		if (inc_labeling_params_s.find("time_to") == string::npos)
			inc_labeling_params.time_to = 365 * global_age_bin;

	}
public:
	// Global Section:
	string global_rep; ///< the repository path
	string global_stats_path; ///< the location to save or load stats file if exists
	bool global_override; ///< to override global_stats_path even if exists
	int global_age_bin; ///< age bin resolution for statsitics matching

	// Section 1 - Registry Loading
	string registry_path; ///< A path to registry file to load
	string registry_save; ///< to export reigstry created by this tool
	bool registry_filter_train; ///< filtering TRAIN==1 if true
	string registry_init_cmd; ///< An init command for registry creation on the fly.
	LabelParams labeling_params; ///< the labeling params
	LabelParams inc_labeling_params; ///< the labeling params for incidence by age
	int sub_sample_pids; ///< down-sample pids till this number to speedup calculation

	//Censoring reg:
	string censoring_registry_path; ///< A path to registry file to load
	string censoring_registry_type; ///< A path to registry type to calc on the fly
	string censoring_registry_args; ///< A path to registry args when calculating

	// Section 2 - Signal Loading
	string test_main_signal; ///< main signal for labeling new signal
	int test_from_window; ///< the minimal time in days before the registry. if negative so minimal time after registry
	int test_to_window; ///< the maximal time in days before the registry. if negative the maximal time after the registry
	string test_hierarchy; ///< supports for regex hierarchy filtering

	// Section 3 - Filtering
	float filter_min_age; ///< minimal age filter
	float filter_max_age; ///< maximal age filter
	int filter_gender; ///< filter by gender - 1 for male, 2 - for female, 3 - take both
	int filter_positive_cnt; ///< min positive count filter
	int filter_total_cnt; ///< min total count filter
	float filter_pval_fdr; ///< p value fdr to filter
	float filter_min_ppv; ///< min PPV in signal existence. how many cases are out of cases+controls when signal exists
	float filter_positive_lift; ///< filtering of lift > 1. from which value? for example at least lift of 1.5
	float filter_negative_lift; ///< filtering of lift < 1. from which value? for example at tops lift of 0.8
	float filter_child_pval_diff; ///< below this threshold of pvalue diff change to remove child category (with AND condition on average lift change)
	float filter_child_lift_ratio; ///< below this threshold of lift change to remove child category
	float filter_child_count_ratio; ///< If child ratio count is too similar, small change from parent code - keep only paretn code
	float filter_child_removed_ratio; ///< If child removed ratio is beyond this and has other child taken - remove parent
	stat_test filter_stats_test; ///< which statistical test to use: 
	int filter_chi_smooth; ///< number of "balls" to add and smooth each window
	float filter_chi_at_least; ///< diff in ratio for bin to cancel
	int filter_chi_minimal; ///< the minimal number of observations in bin to keep row
	float filter_fisher_smooth; ///< fisher bandwith for division to happend. in ratio change from total_count of no_sig to with_sig [0-1]

	// Section 4 - Output
	float output_value; ///< if not exist will do filter and run print_top. if exist will skip filter and run RegistryRecord::print_stats
	string output_full_path; ///< will only treat if output_value <> NULL. if exist will use to run all and print out all pids data with corersponding signal in output_value.
	bool output_debug;

	//for conversion - not for direct use
	string stat_test_type; //may be the statistical test - chi-square for example

	ProgramArgs() {
		string conflict_optionList = "param to control conflicting parameter of signal with reg. options are: " + medial::io::get_list(ConflictMode_to_name);
		string option_ls = "which statistical test to use: (" + medial::io::get_list(conv_map) + ")";
		unsigned int row_size = (unsigned int)po::options_description::m_default_line_length;
		po::options_description desc("Global Options", row_size * 2, row_size);
		desc.add_options()
			("global_rep", po::value<string>(&global_rep)->required(), "repository path to fetch signal\\registry")
			("global_stats_path", po::value<string>(&global_stats_path)->required(), "location to save or load stats dictionary for fast load in the second time for more filtering")
			("global_override", po::value<bool>(&global_override)->default_value(false), "whather or not override stats file if already exists")
			("global_age_bin", po::value<int>(&global_age_bin)->default_value(5), "age bin size (default is 5 years)");

		po::options_description desc2("Registry Options", row_size * 2, row_size);
		desc2.add_options()
			("registry_path", po::value<string>(&registry_path), "location to load registry txt file")
			("registry_init_cmd", po::value<string>(&registry_init_cmd), "An init command for registry creation on the fly")
			("registry_save", po::value<string>(&registry_save), "location to export registry txt file created by this tool on the fly")
			("registry_filter_train", po::value<bool>(&registry_filter_train)->default_value(true), "if True will filter TRAIN==1")
			("labeling_params", po::value<string>(&labeling_params_s)->default_value("conflict_method=max;label_interaction_mode=0:after_start,before_end|1:before_start,after_start;censor_interaction_mode=all:within,all"), " the labeling params")
			("sub_sample_pids", po::value<int>(&sub_sample_pids)->default_value(0), " down-sample pids till this number to speedup calculation. If 0 no sub sampling")
			;

		po::options_description desc3("Censoring Registry Options", row_size * 2, row_size);
		desc3.add_options()
			("censoring_registry_path", po::value<string>(&censoring_registry_path)->default_value(""), "location to load registry txt file for censoring")
			("censoring_registry_type", po::value<string>(&censoring_registry_type)->default_value("keep_alive"), "censoring registry default path")
			("censoring_registry_args", po::value<string>(&censoring_registry_args)->default_value(""), "An init command for registry creation on the fly")
			;

		po::options_description desc4("Test Signal Options", row_size * 2, row_size);
		desc4.add_options()
			("test_main_signal", po::value<string>(&test_main_signal)->required(), "main signal to look for it's values when creating test signal")
			("test_from_window", po::value<int>(&test_from_window)->default_value(0), "min time after the registry to look for signal (if negative means search forward)")
			("test_to_window", po::value<int>(&test_to_window)->default_value(365), "max time after the registry to look for signal (if negative means search forward)")
			("test_hierarchy", po::value<string>(&test_hierarchy)->default_value(""), "Hierarchy type for test signal. free string to filter regex on parents to propage up. to cancel pass \"None\"")
			("inc_labeling_params", po::value<string>(&inc_labeling_params_s)->default_value("conflict_method=all;label_interaction_mode=all:before_end,after_start;censor_interaction_mode=all:all,all"), "params for outcome registry interaction with age bin")
			;

		po::options_description desc5("Filtering Options", row_size * 2, row_size);
		desc5.add_options()
			("filter_min_age", po::value<float>(&filter_min_age)->default_value(20), "minimal age for filtering population in stats table nodes")
			("filter_max_age", po::value<float>(&filter_max_age)->default_value(90), "maximal age for filtering population in stats table nodes")
			("filter_gender", po::value<int>(&filter_gender)->default_value(3), "filter by gender - 1 for male, 2 - for female, 3 - take both")
			("filter_positive_cnt", po::value<int>(&filter_positive_cnt)->default_value(0), "minimal positive count in registry for signal value to keep signal value from filering out")
			("filter_total_cnt", po::value<int>(&filter_total_cnt)->default_value(100), "minimal count for signal value to keep signal value from filering out to remove small redandent signal values")
			("filter_pval_fdr", po::value<float>(&filter_pval_fdr)->default_value((float)0.05), "filter p value in FDR to filter signal values")
			("filter_min_ppv", po::value<float>(&filter_min_ppv)->default_value((float)0), "filter minimal PPV for signal value and registry values")
			("filter_positive_lift", po::value<float>(&filter_positive_lift)->default_value((float)1), "should be >= 1. filtering of lift > 1. from which value? for example at least lift of 1.5")
			("filter_negative_lift", po::value<float>(&filter_negative_lift)->default_value((float)1), "should be <= 1. filtering of lift < 1. from which value? for example at tops lift of 0.8")
			("filter_child_pval_diff", po::value<float>(&filter_child_pval_diff)->default_value((float)1e-10), "p value diff to consider similar in hirarchy filters")
			("filter_child_lift_ratio", po::value<float>(&filter_child_lift_ratio)->default_value((float)0.05), "lift change ratio in child comapred to parent to consider similar")
			("filter_child_count_ratio", po::value<float>(&filter_child_count_ratio)->default_value((float)0.05), "count similarty to consider similar in hirarchy filters")
			("filter_child_removed_ratio", po::value<float>(&filter_child_removed_ratio)->default_value(1), "If child removed ratio is beyond this and has other child taken - remove parent")
			("filter_stats_test", po::value<string>(&stat_test_type)->default_value("mcnemar"), option_ls.c_str())
			("filter_chi_smooth", po::value<int>(&filter_chi_smooth)->default_value(0), "number of balls to add and smooth each window")
			("filter_chi_at_least", po::value<float>(&filter_chi_at_least)->default_value(0), "diff in ratio for bin to cancel - will get change of at least greater than")
			("filter_chi_minimal", po::value<int>(&filter_chi_minimal)->default_value(0), "the minimal number of observations in bin to keep row")
			("filter_fisher_smooth", po::value<float>(&filter_fisher_smooth)->default_value(0), "fisher bandwith for division to happend. in ratio change from total_count of no_sig to with_sig [0-1]");

		po::options_description desc6("Output Options", row_size * 2, row_size);
		desc6.add_options()
			("output_value", po::value<float>(&output_value)->default_value(-1), "if exists will print stats table for only selected signal value else will print all sorted list")
			("output_full_path", po::value<string>(&output_full_path), "will only treat if output_value <> NULL. if exist will use to run all and print out all pids data with corersponding signal in output_value")
			("output_debug", po::value<bool>(&output_debug)->default_value(false), "If true & output_value!=-1 will output intersetions into file for debuging")
			;
		desc.add(desc2);
		desc.add(desc3);
		desc.add(desc4);
		desc.add(desc5);
		desc.add(desc6);

		init(desc);
	}
};
#endif
