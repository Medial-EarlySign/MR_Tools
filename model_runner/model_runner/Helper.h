#ifndef __HELPER_H_
#define __HELPER_H_
#include <vector>
#include <string>
#include <unordered_set>
#include <unordered_map>
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedStat/MedStat/MedBootstrap.h"
#include "MedAlgo/MedAlgo/BinSplitOptimizer.h"
#include "Logger/Logger/Logger.h"

using namespace std;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void read_selected_model(const string &selected_mode_path,
	string &predictor_name, string &predictor_params);

enum weighting_method {
	propensity = 0,
	propensity_controls = 1,
	outcome_event = 2
};

enum loss_metric {
	auc = 0,
	kendall_tau = 1,
	accurarcy = 2,
	RMSE = 3
};
loss_metric get_loss_metric(const string &s);
string get_loss_metric_name(loss_metric metric);
bool loss_function_order(loss_metric metric);

class weights_params : public SerializableObject {
private:
	string base_folder_path;
public:
	bool active;
	string medmodel_path;
	string predictor_type;
	string predictor_path;
	string feature_selection_path;
	string registry_path;
	string censor_registry_path;
	string censor_registry_signal;
	string sampler_type;
	string sampler_params;
	weighting_method method;
	LabelParams labeling_params;
	string train_samples; ///< get train samples directly
	int nfolds;
	string norm_weight_condition;
	bool norm_all;
	int down_sample_to;
	bool medmodel_has_predictor;
	bool medmodel_has_calibrator;
	string secondery_medmodel_path; //secondery medmodel with calibration just to multiply by

	float change_action_prior;
	string calibration_init;

	weights_params() {
		base_folder_path = ""; medmodel_path = ""; predictor_path = "";
		feature_selection_path = ""; registry_path = ""; predictor_type = "";
		censor_registry_path = "";
		censor_registry_signal = "";
		sampler_type = "yearly";
		sampler_params = "start_year=2007;end_year=2014;day_jump=365;"
			"prediction_month_day=101;back_random_duration=0;";
		calibration_init = "";
		method = propensity;
		active = false;
		change_action_prior = 0;
		norm_weight_condition = "";
		nfolds = 5;
		down_sample_to = 0;
		labeling_params.init_from_string("conflict_method=drop;label_interaction_mode=0:all,before_end|1:before_start,after_start;censor_interaction_mode=all:within,within;time_from=30;time_to=365");
		medmodel_has_predictor = false;
		medmodel_has_calibrator = false;
		secondery_medmodel_path = "";
		train_samples = "";
		norm_all = true;
	}

	int init(map<string, string>& map);
};

enum class stat_test {
	chi_square = 1,
	fisher = 2,
	mcnemar = 3,
	cmh = 4
};

class signal_dep_filters : public SerializableObject {
public:
	int minimal_count;
	float fdr;
	float lift_below;
	float lift_above;
	stat_test stat_metric;
	float chi_square_at_least;
	int minimal_chi_cnt;
	vector<string> regex_filters;
	float filter_child_pval_diff; ///< below this threshold of pvalue diff change to remove child category (with AND condition on average lift change)
	float filter_child_lift_ratio; ///< below this threshold of lift change to remove child category
	float filter_child_count_ratio; ///< If child ratio count is too similar, small change from parent code - keep only paretn code
	float filter_child_removed_ratio; ///< If child removed ratio is beyond this and has other child taken - remove parent

	signal_dep_filters();

	int init(map<string, string>& map);
};

/**
* An object for comparing models parameters
*/
class compare_model_params : public SerializableObject {
public:
	string model_path; ///< must has value. the path to the json file
	bool need_learn; ///< if binary already trained or json file to train
	string selected_features_file; ///< the list of selection params
	string final_score_calc; ///< if predictor will use the predcitor otherwise will use the name
	string predictor_type; ///< the predictor type if binary model
	string predictor_path; ///< the predictor path for binary model

	compare_model_params() {
		need_learn = true;
		model_path = "";
		selected_features_file = "";
		final_score_calc = "predictor";
		predictor_type = "";
		predictor_path = "";
	}

	int init(map<string, string>& map);
};

void write_string_file(const unordered_set<string> &ls, const string &f_out);
void read_string_file(const string &f_in, unordered_set<string> &ls);

void update_selected_sigs(unordered_set<string> &selected_sigs,
	const vector<pair<float, string>> &all_scores, float ref, int take_top,
	const string &out_path, const string &log_path = "", loss_metric metric = loss_metric::auc, 
	bool use_counts = true);

void shrink_med_model(MedModel &mod, const unordered_set<string> &feature_selection_set);
///loads MedFeatures from MedSamples using json format for MedModel
double load_matrix_from_json(MedSamples &samples,
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat, double change_prior = 0);
void load_additional_featuress(MedModel &mod, const string &signalName,
	const string &selection_list, int win_from = 0, int win_to = 1825);

void read_ms_config(const string &file_path, const string &base_model,
	vector<MedPredictor *> &all_configs);

///prepare and init MedRepository based on MedModel and MedSamples
double prepare_model_from_json(MedSamples &samples,
	const string &RepositoryPath,
	MedModel &mod, MedPidRepository &dataManager, double change_prior = 0);

void write_model_selection(const unordered_map<string, float> &model_loss,
	const unordered_map<string, float> &model_loss_train, const string &save_path);

void commit_selection(MedFeatures &data, const unordered_set<string> &final_list);
void filter_conflicts(MedFeatures &data);
void filter_matrix_ages_years(MedFeatures &data, int min_age, int max_age, int min_year, int max_year);

void get_signal_stats(string &base_stats_path,
	const string &signal_expend_stats, MedLabels &train_labeler, const string &type_sampler, const string &init_sampler,
	const LabelParams &lbl_pr, MedRepository &rep, const string &RepositoryPath, const string &out_path, int top_take, const signal_dep_filters &filters, 
	int signal_idx);

/// the json model is binary serialized. populating MedFeatures from MedSamples using the modelFile
double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, unordered_map<string, vector<float>> &additional_bootstrap,
	const string &modelFile, const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior = 0);

///A load from model
double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, unordered_map<string, vector<float>> &additional_bootstrap,
	const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior);

void split_registry_train_test(const string &rep_path, MedRegistry &regRecords
	, vector<MedRegistryRecord> &only_train,
	vector<MedRegistryRecord> &only_test, MedRepository &rep);

void simple_uni_feature_sel(const MedFeatures &data, const vector<string> &signalNames,
	const string &output_path, const BinSettings &bin_sett, loss_metric metric = loss_metric::auc);

vector<pair<float, string>> runFeatureSelectionModel(MedPredictor *model, const MedFeatures &data_records, const vector<string> &signalNames, float &refScore,
	const vector<string> &baseSigs, int find_addition, int loopIter, loss_metric metric = loss_metric::auc);

string runOptimizerModel(MedFeatures &dataMat, bool filterTrainPid, float price_ratio
	, vector<int> &selectedInd, const vector<MedPredictor *> &all_models_config,
	unordered_map<string, float> &model_loss, unordered_map<string, float> &model_loss_train,
	int nFold = 4, loss_metric metric = loss_metric::auc);

map<string, map<string, float>> runExperiment(MedFeatures &dataMat, string f_name
	, bool(*filterTestCondition)(const MedFeatures &, int)
	, bool(*filterTrainCondition)(const MedFeatures &, int), bool filterTrainPid,
	MedPredictor *&model, vector<int> &selectedInd, float price_ratio, int kFold,
	const map<string, FilterCohortFunc> &cohort_defs,
	const vector<MeasurementFunctions> &measurement_functions, bool onTrain, bool returnOnlyAuc, loss_metric metric);

void backward_selection(const string &output_folder, const string &log_file,
	MedFeatures &data, float price_ratio, int kfold, float max_auc_change, float min_diff_th,
	int max_count, const vector<string> &signal_names, unordered_set<string> &final_list, void *model,
	loss_metric metric, double change_prior = 0);

void assign_weights(const string &rep_path, MedFeatures &dataMat, const weights_params &params, bool do_norm = true,
	double change_prior = 0);

void get_probs_weights(MedSamples &samples, const string &rep_path, const weights_params &params,
	vector<float> &weights, vector<int> &sel_idx, double change_prior = 0);

void run_bootstrap(const string &rep, MedFeatures &validation_data,
	const unordered_map<string, vector<float>> &additional_bootstrap,
	const string &bootstrap_params, const string &cohort_file, const weights_params &weights_args,
	const string &output_path, const string &model_name, vector<float> &compare_preds,
	vector<float> *ret_weights = NULL, loss_metric metric = loss_metric::auc
	, with_registry_args *bootstrap_reg_args = NULL);

void read_compare_models(const string &file_path, vector<pair<string, compare_model_params>> &model_name_json);

void run_compare_model(const pair<string, compare_model_params> &param,
	MedSamples &train_samples, MedSamples &validation_samples, const vector<float> *bootstrap_weights,
	const unordered_map<string, vector<float>> &additional_feature_bootstrap,
	const string &rep_path, const string &bootstrap_params,
	const string &cohort_file, const weights_params &weights_args, const string &bootstrap_output_path,
	vector<float> &compare_preds, vector<float> *ret_weights, loss_metric metric, double change_prior = 0
	, with_registry_args *bootstrap_reg_args = NULL);

void plotAUC_graphs(const vector<float> &yFixed, const map<string, vector<float>> &dataMat,
	const vector<vector<float>> &all_model_preds, const vector<float> *weights, const vector<string> &model_names,
	const string &cohort_file, const string &bootstrap_output_base);

template<class T> string list_signals(const map<string, T> &f, const string &delimeter = "\n");

template<class T> string get_name(const map<string, T> &mapper, const string &col_name, bool throw_error = true);

void clean_ftr_name(string &name);

float loss_function_metric(loss_metric metric, const vector<float> &preds, const vector<float> &labels,
	const vector<float> *weights = NULL, bool make_smaller_better = false);

typedef double(*loss_fun_sig)(const vector<float> &, const vector<float> &, const vector<float> *);
loss_fun_sig get_loss_function(loss_metric metric, bool make_smaller_better = false);
MeasurementFunctions get_loss_function_bootstrap(loss_metric metric);
void fix_samples(MedSamples &samples, const MedFeatures &feats, bool print_warn = true);

void complete_control_active_periods(MedRegistry &reg, const string &complete_reg,
	const string &complete_reg_sig, const string &rep_path);

void read_active_periods(string &complete_reg, const string &complete_reg_sig, const string &complete_reg_type,
	const string &complete_reg_args, const string &rep_path, MedPidRepository &rep,
	medial::repository::fix_method registry_fix_method, const string &save_censor_path,
	MedRegistry *&active_reg);

#endif
