//
// needed definitions for Flow.cpp
//

#ifndef __FLOW__H__
#define __FLOW__H__
#include <vector>
#include <string>

#include "InfraMed/InfraMed/InfraMed.h"
#include "train_test_v2.h"
#include <MedProcessTools/MedProcessTools/MedSamples.h>
#include <MedUtils/MedUtils/MedUtils.h>

#define OPTION_REP_CREATE			0
#define OPTION_REP_CREATE_PIDS		1
#define OPTION_PRINTALL				2
#define OPTION_PID_PRINTALL			3
#define OPTION_PRINT				4
#define OPTION_PID_PRINT			5
#define OPTION_DESCRIBE				6
#define OPTION_CREATE_SPLITS		7
//#define OPTION_CREATE_OUTCOME		8
//#define OPTION_MATCH_OUTCOME		9
//#define OPTION_FILTER_OUTCOME		10
#define OPTION_TRAIN_TEST			11
#define OPTION_SIG_PRINT			12
#define OPTION_LEARN_MATRIX			13
#define OPTION_PRINT_PIDS			14
#define OPTION_DESCRIBE_ALL			15
#define OPTION_EXTRACT_PIDS_IN_SET	16
#define OPTION_SCAN_SIGS_FOR_SAMPLES 17
#define OPTION_GENERATE_FEATURES 18
#define OPTION_FILTER_AND_MATCH		 19
//#define OPTION_GET_INCIDENCE		 20
#define OPTION_HOSPITAL_REP			 21
#define OPTION_COHORT_INCIDENCE		 22
#define OPTION_COHORT_SAMPLING		 23
#define OPTION_PIDS_PRINTALL		24
#define OPTION_SIG_PRINT_RAW		25
#define OPTION_GET_MODEL_PREDS		26
#define OPTION_PRINT_PROCESSORS		27
#define OPTION_MODEL_INFO			28
#define OPTION_GET_MAT				29
#define OPTION_REWRITE_OBJECT		30
#define OPTION_SIMPLE_TRAIN			31
#define OPTION_GET_JSON_MAT			32
#define OPTION_CALC_KAPLAN_MEIR     33
#define OPTION_EXPORT_PRODUCTION     34
#define OPTION_REP_PROCESSOR_PRINT	 35
#define OPTION_MODEL_DEP	 36
#define OPTION_RELABEL		37
#define OPTION_SHAP		38
#define OPTION_EXPORT_PREDICTOR 39
#define OPTION_PRINT_MDOEL_SIGNALS 40
#define OPTION_CLEAN_DICT 41
#define OPTION_SHOW_CATEGORY_INFO 42
#define OPTION_ADD_SPLITS_TO_SAMPLES 43
#define OPTION_SIMPLE_TEST 44
#define OPTION_GET_PROPENSITY_WEIGHTS 45
#define OPTION_GET_FEAT_GROUP 46
#define OPTION_SHOW_NAMES 47
#define OPTION_TT_PREDICTOR_ON_MAT 48
#define OPTION_AM_DICT 49
#define OPTION_CMP_MATRIX 50
#define OPTION_PREDICT_ON_MAT 51
#define OPTION_RENAME_MODEL_SIGNAL 52
#define OPTION_FLAT_CATEGORY_VALS 53
#define OPTION_FIT_MODEL_TO_REP 54

#define MAX_OPTION					100

using namespace std;

class FlowAppParams : public medial::io::ProgramArgs_base {
public:
	vector<int> options;

	string global_time_unit;
	string global_win_time_unit;

	string rep_fname;
	string convert_conf_fname;
	string load_args;
	string outcome_fname;
	string matched_outcome_fname;
	string filtered_outcome_fname;
	string split_fname;
	string pred_params_fname;
	string features_fname;
	string matrix_fname;
	string label_matrix_fname;
	string work_dir;
	string signals_fname;
	string model_init_fname;
	string f_pre_json;

	int	pid;
	string sig_name;
	string sig_section;
	string sig_val;
	string sig_set;
	int date_min, date_max;
	int age_min, age_max;
	string sigs, pids;

	int debug_level;
	int random_seed; // -1 means seed chosen from time will be used

	// creating splits
	string split_params;

	// creating outcome
	string outcome_params;
	string match_params;
	string filter_params;
	string in_samples_file;
	string out_samples_file;
	string samples_match_params;
	string samples_filter_params;

	// train_test example
	string train_test_conf_fname;
	string train_test_learning_samples_fname;	// overrides 
	string train_test_validation_samples_fname;
	string train_test_prefix;
	string train_test_validation_prefix;
	string train_test_preds_format;
	string train_test_save_matrix;
	string train_test_save_contribs;
	string train_test_save_matrix_splits;
	string train_test_model_init_fname;
	vector<string> train_test_json_alt;
	string steps;
	string active_splits;
	string cv_on_train1;



	// learn from prepared matrix
	string xtrain_fname, ytrain_fname;
	string xtest_fname, ytest_fname;
	string learn_model, learn_model_params;

	// working with cohorts
	string cohort_fname;
	string cohort_incidence;
	string incidence_fname;
	string cohort_sampling;
	bool cohort_medregistry;
	bool use_kaplan_meir;
	string sampler_params;
	string labeling_param;
	string censor_reg;
	string censor_sig;

	//output params
	string codes_to_signals_fname;
	string outputFormat;
	string output_fname;
	int sampleCnt;
	int maxPids;
	int gender;
	float filterCnt;
	int normalize;
	string bin_method;
	vector<string> ignore_signals;
	string model_rep_processors;

	// get_model_preds params
	string f_model;
	string f_samples;
	string f_preds;
	string model_predictor_path; ///< If given with predictor_type override predictor in f_model
	string predictor_type;
	string object_type;
	bool only_post_processors;
	int stop_step;

	string f_json;
	bool no_matrix_retrain;
	int split;
	string predictor;
	string predictor_params;

	string select_features;

	int time_period;
	int limit_count;
	string importance_param;

	string cleaner_path_before;
	string cleaner_path;
	int max_examples;
	bool show_all_changes;
	bool print_attr;
	int max_samples;
	float group_ratio;
	int group_cnt;
	string group_names;
	bool bin_uniq;
	bool normalize_after;
	bool remove_b0;
	bool relearn_predictor;
	string group_signals;
	string output_dict_path;
	bool transform_rep;
	bool keep_imputers;
	string cohort_filter;
	bool zero_missing_contrib;

	double max_propensity_weight;
	bool trim_propensity_weight;
	string prop_attr_weight_name;
	int override_outcome;
	bool propensity_sampling; ///< If true will sample by the propenstity weights (will dividide all by max weight and sample)
	string propensity_feature_name; ///< If json is given will select this feature instead of outcome
	bool do_conversion;
	
	bool print_json_format;
	string change_model_init;
	string change_model_file;
	bool minimize_model;

	string f_test_matrix;
	string dict_path;
	bool add_empty;
	bool skip_missings;

	int time;
	bool shrink_code_list;

	string load_err_file;
	bool catch_fe_exceptions;

	string signal_rename;
	bool apply_feat_processors;
	int cleaner_verbose;

	string log_action_file_path;
	string log_missing_categories_path;
	bool allow_virtual_rep;
	bool remove_explainability;

	FlowAppParams();
private:
	bool rep_create, rep_create_pids, printall, pid_printall, pids_printall,
		print_pids, print, pid_print, describe, describe_all, sig_print,
		sig_print_raw, generate_features, extract_pids_in_set, learn_matrix, train_test,
		samples_scan_sigs, filter_and_match, get_model_preds, get_mat, print_processors,
		print_model_info, rewrite_object, simple_train, get_json_mat, calc_kaplan_meir, export_production_model, 
		rep_processor_print, model_dep, relabel, shap_val_request, export_predictor, print_model_signals, clean_dict,
		show_category_info, add_splits_to_samples, simple_test, get_propensity_weights, get_feature_group, show_names,
		tt_predictor_on_matrix, algomarker_dict, compare_mat, predict_on_mat, rename_model_signal,
		flat_category_vals, fit_model_to_rep;
	void post_process();
};

// basic_ops
int flow_pid_print_pid_sig(string &rep_fname, int pid, string &sig_name);
int flow_print_pid_sig(string &rep_fname, int pid, string &sig_name);
int flow_pid_printall(string &rep_fname, int pid, const string &output_format, const string &codes_to_signals_fname);
int flow_pids_printall(string &rep_fname, const string& samples_file, const string &output_format, const string &codes_to_signals_fname);
int flow_printall(string &rep_fname, int pid, string output_format, const vector<string>& ignore_signals);
int flow_print_pids_with_sig(string &rep_fname, string &sig_name);
int flow_rep_create_pids(string &rep_fname);
void flow_rep_create(string &conf_fname, const string &load_args, const string &err_log_path);
void flow_extract_pids_in_set(const string &rep_fname, const string& section,
	const string& sig_name, const string& sig_set, const string& sig_val, const string& out_file);
void test_rep_processors(const string &rep_fname, const string &before_cleaners_path, const string &cleaners_path,
	const vector<string> &all_sigs, const string &output_example_file, int seed, int max_examples, const vector<int> &given_pids, bool show_all_changes);
void flat_list(const string &rep_fname, const string &signal, const string &signal_codes, int limit_depth, bool shrink, bool allow_diff_lut);
void show_category_info(const string &rep_fname, const string &signal, const string &signal_value);
void flow_clean_dict(const string &rep_fname, const string &input_dict, const string &output_dict);
void flow_get_features_groups(const string &grouping, const string &feature_name_list);

// create outcomes & splits
int flow_create_sig_outcome_SDateVal(string &rep_fname, string &outcome_fname, string &in_params);
int flow_create_split(string &split_fname, string &split_params, string &rep_fname);
int flow_add_splits_to_samples(string &f_split, string &f_samples);
int flow_match_outcome(string &rep_fname, string &outcome_fname, string &matched_outcome_fname, string &match_params);
int flow_filter_outcome(string &rep_fname, string &outcome_fname, string &filtered_outcome_fname, string &filter_params);
int flow_scan_sigs_for_samples(const string &rep_fname, const string &samples_file);
void flow_generate_features(const string &rep_fname, const string &samples_file, const string& model_init_fname,
	const string& matrix_fname, vector<string> alterations, const string& f_model, const string &change_model_init, const string &change_model_file);
int flow_samples_filter_and_match(string rep_fname, string in_samples_file, string out_samples_file, string filter_params, string match_params);

// learn a model on prepared matrices
int flow_learn_matrix(string f_xtrain, string f_ytrain, string f_xtest, string f_ytest, string learn_model, string learn_params);


// basic stat
int flow_describe_sig(string &rep_fname, string &sig_name, int age_min, int age_max, int date_min, int date_max);
int flow_describe_all(string &rep_fname, string signals_fname, int age_min, int age_max, int date_min, int date_max);
int flow_output_sig(string &rep_fname, string &sig_name, string &outputFrmt, int age_min, int age_max, int gender_filt,
	int maxPids, int sampleCnt, bool normalize, float filterRate, const string &bin_method, string& output_fname);
int flow_output_pids_sigs_print_raw(const string &rep_fname, const string &pids_args, const string &sigs_args, int limit_count, const string &model_rep_processors, const int time, const string &f_samples);
void flow_create_dict_for_am(const string &rep_fname, const string &sig, const string &dict_path,
	bool add_empty, bool skip_missings, const string &output_fname);

struct FlowBasicStat {
	int n_diff_values;
	int n_zeros;
	double mean;
	double std;
	double median;
	vector<float> percentiles_vals;
	vector<pair<float, int>> val_counts;
};

struct FlowSigStat {
	int sid;
	string sname;
	vector<FlowBasicStat> Gender;
	vector<FlowBasicStat> Gender_Age;
	vector<FlowBasicStat> Gender_Years;

	// defining slices to work on
	int gender_to_take; // 3 bits, <all><female><male> (values 0 to 7)
	int min_age, max_age, jump_age;
	int min_year, max_year;

	// defining which stats to get
	int get_median_flag;
	int count_zeros_flag;
	int count_diff_values_flag;
	int get_percentiles_flag;
	vector<double> percentiles;
	int show_categs_below;

	// stats that are done only on all data
	vector<pair<float, int>> rounding_counts;

	FlowSigStat() {
		gender_to_take = 0x7; min_age = -1; min_year = -1; count_zeros_flag = 1;  get_median_flag = 1; count_diff_values_flag = 1;
		show_categs_below = 0; get_percentiles_flag = 1;
		percentiles = { 0.001, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975, 0.99, 0.999 };
	}

	int get_stats_mhs(MedRepository &rep, string &sig_name); // get stats for mhs/thin like repositories (have GENDER, BYEAR, global time, and SDateVal signals)
};



// get incidence information
struct LocalCohortRec {
	int pid;
	int from;
	int to;
	int outcome;
};

int flow_get_incidence(const string &inc_params, const string &rep_fname);

// cohort operations
int flow_get_cohort_incidence(const string &cohort_fname, const string &incidence_params, const string &rep_fname,
	const string &out_incidence_fname, bool is_med_registry, bool use_kaplan_meir, const string &sampler_params = "",
	const string &labeling_params = "", const string &censor_reg = "", const string &censor_sig = "");
int flow_get_cohort_sampling(string cohort_fname, string sampling_params, string rep_fname, string out_samples_fname);
int flow_get_km(const string &samples_path, int time_period);
void flow_relabel_samples(const string &in_samples, const string &output_samples,
	const string &registry_path, const string &censor_reg_path, const string &rep, const string &censor_sig,
	const string &labeling_params);

// general split into files to help compilation...
int flow_create_operations(FlowAppParams &ap);
int flow_print_operations(FlowAppParams &ap);
int flow_models_operations(FlowAppParams &ap);
int flow_cohort_samples_operations(FlowAppParams &ap);

int flow_analyze(vector<float> &preds, vector<float> &y, const string pref);


#endif
