#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>
#include "Helper.h"

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string train_cases_labels_s, train_control_labels_s, test_cases_labels_s, test_control_labels_s;
	string train_weights_method_s;

public:
	string rep;
	string train_samples_files;
	string test_samples_files;
	string splits_file; ///< splits file with id [space delimeted] split
	bool train_test_samples_single; ///< If true this is the samples for train/test. it's not reference file
	string json_model;
	string bt_json; ///< json to filter test sample for bootstrap cohort
	string bt_cohort; ///< bootstrap cohort
	//global
	string result_folder;
	string config_folder;
	int min_age_filter;
	int max_age_filter;
	int min_year_filter;
	int max_year_filter;

	//filter params:
	int train_till_time;
	vector<int> train_cases_labels;
	vector<int> train_control_labels;
	vector<int> test_cases_labels;
	vector<int> test_control_labels;

	//model selection:
	string ms_predictor_name;
	string  ms_configs_file;

	//train model args:
	string matching_strata; ///< matching strata arg
	string matching_json; ///< Json for matching
	float price_ratio; ///< if 0 - no matching, if <0- will give weights. otherwise mathcing
	double matching_change_to_prior; ///< control ratio of cases/controls in the samples matching/ override price_ratio

	int nfolds;
	int split_sel; ///< if has selects number of split to use in model selection
	vector<weights_params> train_weights_method; ///< if given will use it to give weights in train
	double change_to_prior; ///< control ratio of cases/controls in the samples
	int down_sample_train_count; ///< if given not zero, will down sample to this count
	int down_sample_test_count; ///< if given not zero, will down sample to this count

	string combine_with_report; ///< path to report with old results
	bool override_all_results; ///<  if true will override results that exists already and ignore them
	bool use_same_splits; ///< if true will use same random splits
	bool debug_mat_weights; ///< if true will output samples with weights
	bool exit_after_full_model; ///< if true will exit after FULL model is trained without calculating performance on CV splits
	double generelization_error_factor; ///< factor for generalization error overfit between train-test. Should be >1. 

	string bootstrap_args;
	string bootstrap_measure;

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("rep", po::value<string>(&rep)->default_value("/home/Repositories/THIN/thin_final/thin.repository"), "repository path")
			("train_samples_files", po::value<string>(&train_samples_files)->required(), "train files - a file with new line for each train samples opttion. Can have 2 additional tokens to define cases and controls values with comma")
			("test_samples_files", po::value<string>(&test_samples_files)->default_value(""), "test files - a file with new line for each train samples opttion. Can have 2 additional tokens to define cases and controls values with comma")
			("train_test_samples_single", po::value<bool>(&train_test_samples_single)->default_value(false), "If true this is the samples for train/test. it's not reference file")
			("splits_file", po::value<string>(&splits_file)->default_value(""), "splits file with id [space delimeted] split")
			("train_cases_labels", po::value<string>(&train_cases_labels_s)->default_value(""), "train definition for cases - Default is empty - do nothing. When given as comma separated values. It will transform outcome to case when the original value was part of the given list. When train train_test_samples_single is 0, you can provide the cases definition value within the file train_samples_files in 3rd column. If you have 3rd column it will override those instructions.")
			("train_control_labels", po::value<string>(&train_control_labels_s)->default_value(""), "train definition for controls - Default is empty - do nothing. When given as comma separated values. It will transform outcome to control when the original value was part of the given list. When train train_test_samples_single is 0, you can provide the control definition value within the file train_samples_files in 2rd column. If you have 2rd column it will override those instructions. If provided train_control_labels and train_cases_labels, outcomes that are not inside any of those lists will be excluded")
			("test_cases_labels", po::value<string>(&test_cases_labels_s)->default_value(""), "test definition for cases")
			("test_control_labels", po::value<string>(&test_control_labels_s)->default_value(""), "test definition for controls")
			("train_till_time", po::value<int>(&train_till_time)->default_value(-1), "if given will filter train till this time, and after used for test")
			("change_to_prior", po::value<double>(&change_to_prior)->default_value(-1), "if given bigger than zero, will sub sample randomly from cases/controls to reach this prior")
			("down_sample_train_count", po::value<int>(&down_sample_train_count)->default_value(0), "if given not zero, will down sample to this count")
			("down_sample_test_count", po::value<int>(&down_sample_test_count)->default_value(0), "if given not zero, will down sample to this count")

			("json_model", po::value<string>(&json_model)->required(), "the json for model")
			("matching_strata", po::value<string>(&matching_strata)->default_value("Time,year,1"), "The strata args")
			("matching_json", po::value<string>(&matching_json)->default_value(""), "Json for matching, if required")
			("matching_change_to_prior", po::value<double>(&matching_change_to_prior)->default_value(-1), "if >0, will match to this ratio.overrides price_ratio")
			("price_ratio", po::value<float>(&price_ratio)->default_value(0), "if 0 - no matching, if <0- will give weights. otherwise mathcing")
			("nfolds", po::value<int>(&nfolds)->default_value(6), "number of folds if need to split train")
			("split_sel", po::value<int>(&split_sel)->default_value(0), "number of splits to use in model selection.0 - means all")
			("train_weights_method_file", po::value<string>(&train_weights_method_s)->default_value(""), "If given will train with all weights options in file.each line is option")

			("ms_predictor_name", po::value<string>(&ms_predictor_name)->default_value("xgb"), "model selection - predictor name")
			("ms_configs_file", po::value<string>(&ms_configs_file), "model selection file. each parameter is assigned with =. If there are many options to search use ,")
			("generelization_error_factor", po::value<double>(&generelization_error_factor)->default_value(5), "factor for generalization error overfit between train-test. Should be >1")
			("result_folder", po::value<string>(&result_folder)->required(), "result folder")
			("config_folder", po::value<string>(&config_folder)->required(), "config folder")

			("min_age_filter", po::value<int>(&min_age_filter)->default_value(0), "filter for age")
			("max_age_filter", po::value<int>(&max_age_filter)->default_value(120), "filter for age")
			("min_year_filter", po::value<int>(&min_year_filter)->default_value(0), "filter for sample time years")
			("max_year_filter", po::value<int>(&max_year_filter)->default_value(3000), "filter for sample time years")
			("use_same_splits", po::value<bool>(&use_same_splits)->default_value(true), "If true will use same splits over different train sample - assume all has same samples")

			("combine_with_report", po::value<string>(&combine_with_report)->default_value(""), "path to report with old results to combine/continue from")
			("override_all_results", po::value<bool>(&override_all_results)->default_value(false), "If true will override results that already exists in folder and ignore them")
			("debug_mat_weights", po::value<bool>(&debug_mat_weights)->default_value(false), "if true will output samples with weights")
			("exit_after_full_model", po::value<bool>(&exit_after_full_model)->default_value(false), "if true will exit after FULL model is trained without calculating performance on CV splits")

			("bt_json", po::value<string>(&bt_json)->default_value(""), "json file to create features for bootstrap filtering of the cohort")
			("bt_cohort", po::value<string>(&bt_cohort)->default_value(""), "Cohort line for filtering. No support for Multi and name - only filter definition")
			("bootstrap_args", po::value<string>(&bootstrap_args)->default_value(""), "bootstrap params")
			("bootstrap_measure", po::value<string>(&bootstrap_measure)->default_value("AUC_Obs"), "measure for bootstrap")
			;

		init(options);
	}

	void post_process() {
		read_int_array(train_cases_labels_s, train_cases_labels, "train_cases_labels");
		read_int_array(train_control_labels_s, train_control_labels, "train_control_labels");
		read_int_array(test_cases_labels_s, test_cases_labels, "test_cases_labels");
		read_int_array(test_control_labels_s, test_control_labels, "test_control_labels");
		if (train_cases_labels.empty() != train_control_labels.empty())
			HMTHROW_AND_ERR("Error - when train_cases_labels is used, you should alos define train_control_labels\n");
		if (test_cases_labels.empty() != test_control_labels.empty())
			HMTHROW_AND_ERR("Error - when test_cases_labels is used, you should alos define test_control_labels\n");

		if (!train_weights_method_s.empty()) {
			ifstream fr(train_weights_method_s);
			if (!fr.good())
				HMTHROW_AND_ERR("Can't open file %s for reading\n", train_weights_method_s.c_str());
			string line;
			while (getline(fr, line)) {
				boost::trim(line);
				if (line.empty() || line[0] == '#')
					continue;
				weights_params wp;
				wp.init_from_string(line);
				train_weights_method.push_back(move(wp));
			}

			fr.close();
		}
		if (train_weights_method.empty())
			train_weights_method.resize(1);

		if (price_ratio < 0) {
			bool uses_weights = false;
			for (size_t i = 0; i < train_weights_method.size() && !uses_weights; ++i)
				uses_weights = train_weights_method[i].active();
			if (uses_weights)
				HMTHROW_AND_ERR("Error in arguments. can't use train_weights_method & price_ratio < 0 (to use weights)\n");
		}
	}

	bool has_filters() {
		return !vm["min_age_filter"].defaulted() || !vm["max_age_filter"].defaulted()
			|| !vm["min_year_filter"].defaulted() || !vm["max_year_filter"].defaulted();
	}
};
#endif