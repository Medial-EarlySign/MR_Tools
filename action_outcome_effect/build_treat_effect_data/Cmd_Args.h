#ifndef __PROGRAM__ARGS__H__
#define __PROGRAM__ARGS__H__


#include <boost/program_options.hpp>
#include <boost/spirit/home/support/detail/hold_any.hpp>
#include <boost/algorithm/string.hpp>
#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <fstream>
#include <iostream>
#include <algorithm>
#include "MedUtils/MedUtils/MedUtils.h"
#include <MedUtils/MedUtils/FilterParams.h>
#include "Logger/Logger/Logger.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;


class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string labeling_args_s;
	string filtering_params_s;
public:
	string repo_path;
	string registry_path;
	string registry_type;
	string registry_processors;
	string censor_registry_type;
	string censor_registry_init;
	string registry_active_periods; ///< if given active periods registry of patient to complete reg as controls
	string registry_active_periods_sig; ///< if given active periods registry of patient to complete reg as controls from signal
	bool use_active_for_reg_outcome; ///< If true will use active period for outcome reg
	medial::repository::fix_method registry_conflicts_method;
	string registry_cfg_init;
	string output_folder;
	string sampler_type;
	string sampler_init;
	LabelParams labeling_args;
	FilterParams filtering_params; ///< filter params for sampling
	int min_year_filter;
	int max_year_filter;
	string filter_by_column;
	string json_model;
	string confounders_file;
	string action_name_search;
	string action_name_search_his;
	string model_template;
	string model_select_path;
	string default_calib_init;


	bool filter_took_drug_before;
	bool filter_took_drug_after;
	bool filter_pid_outcome;
	float match_year_price_ratio;
	float min_probablity_cutoff;
	float bootstrap_subsample;
	float change_action_prior;
	int nbootstrap;


	int action_type;
	string action_name_search_near;
	string action_name_search_far;
	string action_name_search_fut;
	string action_name_search_con;

	float threshold_drug_prec_case_min;
	float threshold_drug_prec_case_max;
	float threshold_drug_prec_control_min;
	float threshold_drug_prec_control_max;

	int print_to_csv;


	void post_process() {
		if (convert_map.find(conflicts_method_s) == convert_map.end())
			HMTHROW_AND_ERR("Wrong conflict method - please choose one of: %s\n",
				medial::io::get_list(convert_map).c_str());
		registry_conflicts_method = medial::repository::fix_method(convert_map.at(conflicts_method_s));
		if (!labeling_args_s.empty())
			labeling_args.init_from_string(labeling_args_s);
		if (!filtering_params_s.empty())
			filtering_params.init_from_string(filtering_params_s);
		if (registry_path.empty() && registry_cfg_init.empty())
			HMTHROW_AND_ERR("ERROR in ProgramArgs - Must provide registry_path path or registry_cfg_init to create registry\n");
	}

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("repo_path,rep", po::value<string>(&repo_path)->required(), "repository path")
			("output_folder", po::value<string>(&output_folder)->required(), "where to save all data")

			("json_model", po::value<string>(&json_model)->required(), "the json model file path")
			("action_name_search_his", po::value<string>(&action_name_search_his)->default_value("Drug.category_set_Treatment.History"), "the feature history action name to search in matrix")
			("action_name_search", po::value<string>(&action_name_search)->default_value("Drug.Treatment.Future"), "the feature action name to search in matrix")

			("action_type", po::value<int>(&action_type)->default_value(0), "action_type")

			("action_name_search_fut", po::value<string>(&action_name_search_fut)->default_value("Drug.category_set_Treatment.Future"), "the feature: future druge to search in matrix")
			("action_name_search_near", po::value<string>(&action_name_search_near)->default_value("Drug.near_Treatment.Future"), "the feature: future near druge to search in matrix")
			("action_name_search_far", po::value<string>(&action_name_search_far)->default_value("Drug.far_Treatment.Future"), "the feature: future far druge to search in matrix")
			("action_name_search_con", po::value<string>(&action_name_search_con)->default_value(""), "the feature : action name for untreat to search in matrix")


			("threshold_drug_prec_case_min", po::value<float>(&threshold_drug_prec_case_min)->default_value((float)0.5), "minimal coverage percentage to treat as treated")
			("threshold_drug_prec_case_max", po::value<float>(&threshold_drug_prec_case_max)->default_value((float)1.0), "maximal coverage percentage to treat as treated")
			("threshold_drug_prec_control_min", po::value<float>(&threshold_drug_prec_control_min)->default_value((float)0.0), "minimal coverage percentage to treat as untreated")
			("threshold_drug_prec_control_max", po::value<float>(&threshold_drug_prec_control_max)->default_value((float)0.05), "maximal coverage percentage to treat as untreated")

			("print_to_csv", po::value<int>(&print_to_csv)->default_value(0), "print_to_csv")

			;

		po::options_description options_reg("Registry Options");
		options_reg.add_options()
			("registry_path", po::value<string>(&registry_path)->default_value(""), "If Given will use this path as registry")
			("registry_type", po::value<string>(&registry_type)->default_value("binary"), "default registry type - reffer to doxygen to see all types")
			("registry_processors", po::value<string>(&registry_processors)->default_value(""), "If Given will use this path to create processors")
			("registry_conflicts_method", po::value<string>(&conflicts_method_s)->default_value("drop"), "the methos to solve conlict")
			("registry_cfg_init", po::value<string>(&registry_cfg_init)->required(), "the config init line for registry")
			("censor_registry_type", po::value<string>(&censor_registry_type)->default_value("keep_alive"), "default registry type for censoring - reffer to doxygen to see all types")
			("censor_registry_init", po::value<string>(&censor_registry_init)->default_value(""), "censor registry init line")
			("registry_active_periods", po::value<string>(&registry_active_periods)->default_value(""), "if given active periods registry of patient to complete reg as controls")
			("registry_active_periods_sig", po::value<string>(&registry_active_periods_sig)->default_value(""), "if given active periods registry of patient to complete reg as controls from rep signal")
			("use_active_for_reg_outcome", po::value<bool>(&use_active_for_reg_outcome)->default_value(0), "If true will also use active_period to complete controls period in outcome registry")
			;

		po::options_description options_smp("Sampling Options");
		options_smp.add_options()
			("sampler_type", po::value<string>(&sampler_type)->default_value("yearly"), "sampler type to create from registry")
			("sampler_init", po::value<string>(&sampler_init)->default_value("start_year=2007;end_year=2015;prediction_month_day=1231;"
				"back_random_duration=365;day_jump=365"), "sampler init command")
			("labeling_args", po::value<string>(&labeling_args_s)->default_value("label_interaction_mode=0:all,before_end|1:before_start,after_start;"
				"censor_interaction_mode=all:within,within;conflict_method=max;time_from=0;time_to=1095"), "labeling params, type LabelParams")
			("filtering_params", po::value<string>(&filtering_params_s)->default_value(""), "filtering of sampling prior to sampling, please reffer to FilterParams type")
			("min_year_filter", po::value<int>(&min_year_filter)->default_value(0), "registry minimla year to filter")
			("max_year_filter", po::value<int>(&max_year_filter)->default_value(3000), "registry maximal year to filter")
			("match_year_price_ratio", po::value<float>(&match_year_price_ratio)->default_value(0), "If 0 no matching")
			("filter_took_drug_before", po::value<bool>(&filter_took_drug_before)->default_value(false), "if true will filter elements who took the drug before time")
			("filter_pid_outcome", po::value<bool>(&filter_pid_outcome)->default_value(false), "if true will sample once for each pid, outcome")
			("filter_by_column", po::value<string>(&filter_by_column)->default_value(""), "If Provide will use this columnn and remove all records with value > 0")
			;

		po::options_description options_template("Command Template Options");
		options_template.add_options()
			("model_template", po::value<string>(&model_template)->default_value("xgb"), "the template for creating run command which model to use")
			("model_select_path", po::value<string>(&model_select_path)->required(), "the default path for outputing command")
			("default_calib_init", po::value<string>(&default_calib_init)->default_value("calibration_type=binning;min_preds_in_bin=200;min_prob_res=0"), "the default caliberation init for outputing command")
			("min_probablity_cutoff", po::value<float>(&min_probablity_cutoff)->default_value((float)0.001), "default value for command in min_probablity_cutoff")
			("bootstrap_subsample", po::value<float>(&bootstrap_subsample)->default_value(1), "default value for command in bootstrap_subsample")
			("change_action_prior", po::value<float>(&change_action_prior)->default_value(-1), "default value for command in change_action_prior")
			("nbootstrap", po::value<int>(&nbootstrap)->default_value(50), "default value for command in nbootstrap")
			("confounders_file", po::value<string>(&confounders_file)->required(), "the confounder list")
			;

		options.add(options_reg);
		options.add(options_smp);
		options.add(options_template);

		init(options);
	}
private:
	string conflicts_method_s;
	unordered_map<string, int> convert_map = {
		{ "none", medial::repository::fix_method::none },
		{ "drop", medial::repository::fix_method::drop },
		{ "first", medial::repository::fix_method::take_first },
		{ "last", medial::repository::fix_method::take_last },
		{ "mean", medial::repository::fix_method::take_mean },
		{ "min", medial::repository::fix_method::take_min },
		{ "max", medial::repository::fix_method::take_max }

	};
};


#endif