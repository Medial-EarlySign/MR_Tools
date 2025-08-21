#ifndef __CMD_ARGS_H_
#define __CMD_ARGS_H_
#include <string>
#include <ctime>
#include <boost/program_options.hpp>
#include <boost/spirit/home/support/detail/hold_any.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/filesystem.hpp>
#include "MedUtils/MedUtils/MedUtils.h"
#include "MedUtils/MedUtils/MedEnums.h"
#include "Logger/Logger/Logger.h"
#include "SerializableObject/SerializableObject/SerializableObject_imp.h"
#include "Helper.h"
#include <MedUtils/MedUtils/FilterParams.h>


namespace po = boost::program_options;
using namespace std;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

string get_time_str() {
	time_t theTime = time(NULL);
	struct tm now;

#if defined(__unix__)
	localtime_r(&theTime, &now);
#elif defined(_MSC_VER)
	localtime_s(&now, &theTime);
#endif
	char buffer[500];
	snprintf(buffer, sizeof(buffer), "%d_%02d_%02d.%02d_%02d_%02d",
		now.tm_year + 1900, 1 + now.tm_mon, now.tm_mday,
		now.tm_hour, now.tm_min, now.tm_sec);
	string date_format = string(buffer);
	return date_format;
}
void set_logging(const string &base_path, bool debug) {
	boost::filesystem::create_directories(base_path.data());
	string log_dir = base_path + path_sep() + "run_logs";
	boost::filesystem::create_directories(log_dir.data());

	string time_str = get_time_str();
	FILE *inf;
	string fname = log_dir + path_sep() + time_str + ".log";
	inf = fopen(fname.c_str(), "w");
	if (inf == NULL)
		MWARN("MedLogger: init_file: Can't open file %s\n", fname.c_str());

	global_logger.init_file(LOG_APP, inf);
	//global_logger.init_out(args.output_folder + separator() + "last_run.log");
	if (debug) {
		global_logger.levels[LOG_APP] = MIN_LOG_LEVEL;
		global_logger.levels[LOG_MED_MODEL] = MIN_LOG_LEVEL;
		global_logger.fds[LOG_MED_UTILS].push_back(inf);
	}
	global_logger.log(LOG_MED_MODEL, LOG_DEF_LEVEL, "Started @ %s\n", time_str.c_str());
}

class programArgs : public medial::io::ProgramArgs_base {
private:
	unordered_map<string, int> convert_map = {
		{ "none", medial::repository::fix_method::none },
		{ "drop", medial::repository::fix_method::drop },
		{ "first", medial::repository::fix_method::take_first },
		{ "last", medial::repository::fix_method::take_last },
		{ "mean", medial::repository::fix_method::take_mean },
		{ "max", medial::repository::fix_method::take_max },
		{ "min", medial::repository::fix_method::take_min }
	};

	string example_init_reg;
	string fg_create_signals;
	string assign_weights;
	string bootstrap_outcome_correction_s;
	string registry_fix_method_s; ///< fix contradictions if exists
	string bootstrap_weights_s;
	string labeling_params_s;
	string fg_sampler_age_labeling_s;
	string fg_filters_s;
	string train_filtering_params_s;
	string test_filtering_params_s;
	void split_signals() {
		vector<string> tokens;
		if (!fg_create_signals.empty()) {
			boost::split(tokens, fg_create_signals, boost::is_any_of(","));
			fg_signals.reserve(tokens.size());
			for (const string &token : tokens)
				fg_signals.push_back(boost::trim_copy(token));
		}
	}

	void post_process() {
		if (!assign_weights.empty())
			weights_args.init_from_string(assign_weights);
		if (!bootstrap_weights_s.empty())
			bootstrap_weights.init_from_string(bootstrap_weights_s);
		if (!bootstrap_outcome_correction_s.empty())
			bootstrap_outcome_correction.init_from_string(bootstrap_outcome_correction_s);
		split_signals();
		if (load_train_samples.empty() || load_test_samples.empty())
			if (registry_path.empty() &&
				(registry_init_cfg.empty() || registry_init_cfg == example_init_reg))
				MTHROW_AND_ERR("please provide registry_path or registry_init_cfg\n");
		if (!registry_init_cfg.empty() && !rep.empty()) {
			//check if has rep, if not, add it:
			map<string, string> reg_init;
			MedSerialize::initialization_text_to_map(registry_init_cfg, reg_init);
			if (reg_init.find("rep") == reg_init.end())
				registry_init_cfg += ";rep=" + rep;
		}
		if (convert_map.find(registry_fix_method_s) == convert_map.end())
			MTHROW_AND_ERR("Error: wrong fix method, please choose one of: %s\n",
				medial::io::get_list(convert_map).c_str());
		registry_fix_method = medial::repository::fix_method(convert_map.at(registry_fix_method_s));
		if (!labeling_params_s.empty())
			labeling_params.init_from_string(labeling_params_s);
		if (!train_filtering_params_s.empty())
			train_filtering_params.init_from_string(train_filtering_params_s);
		if (!test_filtering_params_s.empty())
			test_filtering_params.init_from_string(test_filtering_params_s);
		if (!fg_sampler_age_labeling_s.empty())
			fg_sampler_age_labeling.init_from_string(fg_sampler_age_labeling_s);
		if (!fg_filters_s.empty())
			fg_filters.init_from_string(fg_filters_s);
		if (fg_sampler_age_labeling_s.find("time_from") != string::npos || fg_sampler_age_labeling_s.find("time_to") != string::npos)
			MWARN("Warning: got time_from|time_to in fg_sampler_age_labeling - overriding value by age_bin arg\n");
		fg_sampler_age_labeling.time_from = 0;
		fg_sampler_age_labeling.time_to = 365 * fg_sampler_age_bin;

		set_logging(output_folder, debug);
	};
public:

	//General settings:
	string rep;
	string output_folder;

	//reg settings
	string registry_name;
	string registry_path;
	string registry_type;
	medial::repository::fix_method registry_fix_method;
	string registry_init_cfg;
	string registry_rep_processors; ///< json config file to MedModel with rep_processors for running on Repository
	string censor_registry_type;
	string censor_registry_init;
	string registry_active_periods; ///< if given active periods registry of patient to complete reg as controls
	string registry_active_periods_sig; ///< if given active periods registry of patient to complete reg as controls from signal
	bool use_active_for_reg_outcome; ///< if true will use active period to complete outcome registry
	LabelParams labeling_params; ///< how to label from registry, please reffer to LabelParams type
	FilterParams train_filtering_params; ///< filter params for sampling
	FilterParams test_filtering_params; ///< filter params for sampling

	//sampling:
	string sampler_train_name;
	string sampler_train_params;
	string sampler_validation_name;
	string sampler_validation_params;
	int min_age, max_age;
	int min_year, max_year;
	string json_mat_filter;
	string filter_feat_name;
	float filter_low;
	float filter_high;
	weights_params weights_args;
	string metric;
	string load_train_samples;
	string load_test_samples;
	string config_folder_name;
	string bootstrap_folder_name;

	//feature selection:
	int fg_take_top;
	int fg_sampler_age_bin;
	int fg_win_from;
	int fg_win_to;
	int fg_win_from_test;
	int fg_win_to_test;
	LabelParams fg_sampler_age_labeling;
	vector<string> fg_signals;
	signal_dep_filters fg_filters;
	int fs_take_top;
	int fs_deep_size; //2
	string fs_base_signal; //file with "Age"
	string fs_predictor_name; //qrf
	string fs_predictor_params;
	int fs_f_max_count; // 500000
	int fs_loop_count; //20000
	bool fs_sort_by_count; ///
	bool fs_skip_backward; // 500000
	float price_ratio;
	bool sample_per_pid;
	bool sample_conflict_pids;
	float change_prior;
	int fs_max_count;
	int ms_max_count;
	int ms_nfolds;
	float fs_max_change;
	float fs_min_remove;
	int fs_nfolds;
	string fs_uni_bin_init;

	string ms_predictor_name;
	string ms_configs_file;

	//run model:
	int kfold;

	//bootstrap settings:
	string cohort_file;
	string bootstrap_params;
	string bootstrap_json_model; ///< json model to add features to validation matrix for filtering
	string compare_models_file; ///< a file where each line is: model name [TAB] config init line. Look for Tools code documentition for compare_model_params
	weights_params bootstrap_weights; ///< weighting model for bootstrap results
	weights_params bootstrap_outcome_correction; ///< outcome shift/correction
	string bootstrap_sampler_args; ///< for registry args in incidence calc

	//outputs settings:
	string dictonary_folder_name; //relative to output_folder. default "dicts". can give full path also

	string json_model;

	bool skip_to_compare; ///< if true will skip to compare models

	programArgs() {
		example_init_reg = "start_buffer_duration=365;end_buffer_duration=365;max_repo_date=20160101;config_signals_rules=$RULES_PATH";
		unsigned int row_size = (unsigned int)po::options_description::m_default_line_length;
		string optionList = "fix contradictions method if exists. options are: " + medial::io::get_list(convert_map);
		string conflict_optionList = "Conflict method options are: " + medial::io::get_list(ConflictMode_to_name);

		po::options_description desc("Global Options", row_size * 2, row_size);
		desc.add_options()
			("rep", po::value<string>(&rep)->required(), "the repository path")
			("output_folder", po::value<string>(&output_folder)->required(), "the location to save data")
			("config_folder_name", po::value<string>(&config_folder_name)->default_value("config_params"), "config folder name")
			("bootstrap_folder_name", po::value<string>(&bootstrap_folder_name)->default_value("bootstrap_pref"), "bootstrap folder name")
			("dictonary_folder_name", po::value<string>(&dictonary_folder_name)->required()->default_value("dicts"), "directory name for the dictionaries in calc_stats")
			("json_model", po::value<string>(&json_model)->required(), "the path to the json to create model")
			("metric", po::value<string>(&metric)->default_value("auc"), "metric to use in whole program. for example: \"auc\" or \"rmse\"")
			("skip_to_compare", po::value<bool>(&skip_to_compare)->default_value(0), "If True will skip all and go to compare bootstrap")
			;

		po::options_description desc2("Registry Options", row_size * 2, row_size);
		desc2.add_options()
			("registry_name", po::value<string>(&registry_name)->required(), "the name of the registry")
			("registry_path", po::value<string>(&registry_path)->default_value(""), "the location to save or read registry")
			("registry_type", po::value<string>(&registry_type)->default_value("binary"), "binary or categories type")
			("registry_init_cfg", po::value<string>(&registry_init_cfg)->default_value(example_init_reg), "the registry init line. reffer to MedRegistry init for more details")
			("registry_fix_method", po::value<string>(&registry_fix_method_s)->default_value("none"), optionList.c_str())
			("registry_rep_processors", po::value<string>(&registry_rep_processors)->default_value(""), "json config file to MedModel with rep_processors for running on Repository")
			("censor_registry_type", po::value<string>(&censor_registry_type)->default_value("keep_alive"), "registry type for cnesoring")
			("censor_registry_init", po::value<string>(&censor_registry_init)->default_value(""), "the censoring init line. reffer to MedRegistry init for more details")
			("registry_active_periods", po::value<string>(&registry_active_periods)->default_value(""), "if given active periods registry of patient to complete reg as controls")
			("registry_active_periods_sig", po::value<string>(&registry_active_periods_sig)->default_value(""), "if given active periods registry of patient to complete reg as controls from rep signal")
			("use_active_for_reg_outcome", po::value<bool>(&use_active_for_reg_outcome)->default_value(0), "If true will also use active_period to complete controls period in outcome registry")
			("labeling_params", po::value<string>(&labeling_params_s)->default_value("conflict_method=drop;label_interaction_mode=0:all,before_end|1:before_start,after_start;censor_interaction_mode=all:within,within;time_from=0;time_to=365"), "how to label from registry, please reffer to LabelParams type")
			;


		po::options_description desc3("Sampling Options", row_size * 2, row_size);
		desc3.add_options()
			("sampler_train_name", po::value<string>(&sampler_train_name)->default_value("time_window"), "the train sampler name")
			("sampler_train_params", po::value<string>(&sampler_train_params)->default_value("minimal_times=30,720;maximal_times_control=365,1825"), "the train sampler params")
			("sampler_validation_name", po::value<string>(&sampler_validation_name)->default_value("yearly"), "validation sampler name")
			("sampler_validation_params", po::value<string>(&sampler_validation_params)->default_value("start_year=2007;end_year=2011;day_jump=365;prediction_month_day=601;back_random_duration=0"), "the validation sampler params")
			("train_filtering_params", po::value<string>(&train_filtering_params_s)->default_value(""), "filtering of sampling prior to sampling, please reffer to FilterParams type")
			("test_filtering_params", po::value<string>(&test_filtering_params_s)->default_value(""), "filtering of sampling prior to sampling, please reffer to FilterParams type")
			("assign_weights", po::value<string>(&assign_weights)->default_value(""), "If empty will do no weighting, otherwise will use weights_params to assign_weights")
			("min_age", po::value<int>(&min_age)->default_value(0), "minimal age for filtering train")
			("max_age", po::value<int>(&max_age)->default_value(100), "maximal age for filtering train")
			("min_year", po::value<int>(&min_year)->default_value(1990), "minimal year for filtering train")
			("max_year", po::value<int>(&max_year)->default_value(2016), "maximal year for filtering train")
			("json_mat_filter", po::value<string>(&json_mat_filter)->default_value(""), "A path to json for creatine matrix to filter train samples")
			("filter_feat_name", po::value<string>(&filter_feat_name)->default_value(""), "the name of feature from created matrix to filter by the train samples")
			("filter_low", po::value<float>(&filter_low)->default_value(0), "the low filter value for the selected feature for training samples")
			("filter_high", po::value<float>(&filter_high)->default_value(0), "the low filter value for the selected feature for training samples")
			("price_ratio", po::value<float>(&price_ratio)->default_value(30), "price ratio for matching by year. 0 -means no matching")
			("sample_per_pid", po::value<bool>(&sample_per_pid)->default_value(false), "sample per patient in train")
			("sample_conflict_pids", po::value<bool>(&sample_conflict_pids)->default_value(false), "sample patient with both case and control")
			("change_prior", po::value<float>(&change_prior)->default_value(0), "If given(value > 0) will subsample controls or cases to match this prior")
			("load_train_samples", po::value<string>(&load_train_samples)->default_value(""), "train samples to load and skip all registry and sampling")
			("load_test_samples", po::value<string>(&load_test_samples)->default_value(""), "train samples to load and skip all registry and sampling")
			;

		po::options_description desc4("Feature Generation Options(SignalsDependencies)", row_size * 2, row_size);
		desc4.add_options()
			("fg_take_top", po::value<int>(&fg_take_top)->default_value(100), "how much RC,Drug to add for features")
			("fg_create_signals", po::value<string>(&fg_create_signals)->default_value(""), "the list of signals with , between each name to run signal_dependencies.")
			("fg_sampler_age_bin", po::value<int>(&fg_sampler_age_bin)->default_value(5), "sampler params for age sampling in signal dependencies")
			("fg_win_from", po::value<int>(&fg_win_from)->default_value(0), "the from time window for signal to create")
			("fg_win_to", po::value<int>(&fg_win_to)->default_value(1095), "the to time window for signal to create")
			("fg_win_from_test", po::value<int>(&fg_win_from_test)->default_value(30), "the from time window for signal to test outcome")
			("fg_win_to_test", po::value<int>(&fg_win_to_test)->default_value(1095), "the to time window for signal to test outcome")
			("fg_sampler_age_labeling", po::value<string>(&fg_sampler_age_labeling_s)->default_value("label_interaction_mode=all:before_end,after_start;conflict_method=all"), "the interaction rule with the age bin")
			("fg_filters", po::value<string>(&fg_filters_s)->default_value("minimal_count=500;fdr=0.05;lift_below=0.8;lift_above=1.25;chi_square_at_least=0.1;minimal_chi_cnt=10;stat_metric=mcnemar"), "filters for signal dependency app")
			;

		po::options_description desc5("Forward Feature Selection Options", row_size * 2, row_size);
		desc5.add_options()
			("fs_uni_bin_init", po::value<string>(&fs_uni_bin_init)->default_value(""), "Univariate feature ranking - If provided will use those binning to rank features univariate. reffer to BinSettings for init string")
			("fs_take_top", po::value<int>(&fs_take_top)->default_value(100), "forward selection top features")
			("fs_deep_size", po::value<int>(&fs_deep_size)->default_value(2), "forward selection deep size")
			("fs_base_signal", po::value<string>(&fs_base_signal), "forward selection must signals")
			("fs_predictor_name", po::value<string>(&fs_predictor_name)->default_value("qrf"), "forward selection model")
			("fs_predictor_params", po::value<string>(&fs_predictor_params)->default_value("ntrees=10;spread=0.01;maxq=1000;ntry=0;min_node=500"), "forward selection params")
			("fs_f_max_count", po::value<int>(&fs_f_max_count)->default_value(500000), "forward selection max count for down sampling")
			("fs_loop_count", po::value<int>(&fs_loop_count)->default_value(20000), "forward selection iter count")
			("fs_sort_by_count", po::value<bool>(&fs_sort_by_count)->default_value(true), "If true will use counts to sort features selection list of forward list")
			;

		po::options_description desc6("Backward Feature Selection Options", row_size * 2, row_size);
		desc6.add_options()
			("fs_skip_backward", po::value<bool>(&fs_skip_backward)->default_value(false), "skip backward feature selection")
			("fs_max_count", po::value<int>(&fs_max_count)->default_value(500000), "maximum count for down sampling matrix in backward selection")
			("fs_max_change", po::value<float>(&fs_max_change)->default_value((float)0.01), "maximal change in AUC to stop in backward selection")
			("fs_min_remove", po::value<float>(&fs_min_remove)->default_value((float)0.001), "minmal change for the best in AUC to remove feature immediately in backward selection")
			("fs_nfolds", po::value<int>(&fs_nfolds)->default_value(4), "number of folds in each backward feature selection")
			;

		po::options_description desc7("Model Selection Options", row_size * 2, row_size);
		desc7.add_options()
			("ms_max_count", po::value<int>(&ms_max_count)->default_value(500000), "maximum count for down sampling matrix in model selection")
			("ms_predictor_name", po::value<string>(&ms_predictor_name)->default_value("xgb"), "model selection - predictor name")
			("ms_configs_file", po::value<string>(&ms_configs_file), "model selection file. each parameter is assigned with =. If there are many options to search use ,")
			("ms_nfolds", po::value<int>(&ms_nfolds)->default_value(3), "number of folds in each model selection")
			("kfold", po::value<int>(&kfold)->default_value(4), "kFold number in training final model after selection");

		po::options_description desc8("Bootstrap Options", row_size * 2, row_size);
		desc8.add_options()
			("cohort_file", po::value<string>(&cohort_file), "the cohort file for bootstrap")
			("bootstrap_params", po::value<string>(&bootstrap_params)->default_value("loopCnt=500;sample_per_pid=0;roc_params={score_resolution=0.0001}"), "the bootstrap params init string")
			("bootstrap_json_model", po::value<string>(&bootstrap_json_model)->default_value(""), "json model to add features to validation matrix for filtering")
			("compare_models_file", po::value<string>(&compare_models_file)->default_value(""), "a file where each line is: model name [TAB] config init line. Look for Tools code documentition for compare_model_params")
			("bootstrap_weights", po::value<string>(&bootstrap_weights_s)->default_value(""), "weighting model for bootstrap results")
			("bootstrap_outcome_correction", po::value<string>(&bootstrap_outcome_correction_s)->default_value(""), "outcome shift/correction parameters")
			("bootstrap_sampler_args", po::value<string>(&bootstrap_sampler_args)->default_value(""), "the bootstrap parameter to init sampler for registry incidence calc")
			;

		string logo = app_logo; //change logo here
		desc.add(desc2);
		desc.add(desc3);
		desc.add(desc4);
		desc.add(desc5);
		desc.add(desc6);
		desc.add(desc7);
		desc.add(desc8);

		init(desc, logo);
	}

};

#endif
