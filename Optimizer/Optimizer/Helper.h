#ifndef __HELPER_LIB_H__
#define __HELPER_LIB_H__
#include <MedAlgo/MedAlgo/MedAlgo.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedUtils/MedUtils/MedRegistry.h>
#include <MedProcessTools/MedProcessTools/Calibration.h>

enum weighting_method {
	none = 0,
	hyperbolic = 1, ///< has 3 parameter: v1,v2: 1-2 time/x values for parabola to reach 1 (for example 30,90 for readmission). m - parabola depth (m >= 0. 0 - weight is constant 1, 1-weight is 0 in middle, bigger, creates gap). output := sqrt( (1-m^2)/((v2-v1)/2) * (x-(v1+v2)/2) + m^2)
	time_gap_importance = 2, ///< has 3 parameters: T - for time gap importance . W- the width of time gap,  K - by how much to increase the weight in max. input is only gap, assume outcome changes over T from case to control
	from_file = 3 ///< read weights from MedSamples files by pid,time - has 2 string args file path and name of attribute
};

static unordered_map<string, int> conversion_map = {
	{ "none", weighting_method::none },
	{ "hyperbolic", weighting_method::hyperbolic },
	{"time_gap_importance", weighting_method::time_gap_importance },
    { "from_file", weighting_method::from_file }
};

class weights_params : public SerializableObject {
private:
	float parse_input(const MedFeatures &matrix, int i, const string &parse_input_string) const;
	void get_inputs(const vector<MedSample> &samples, vector<vector<float>> &x) const; ///< row is for sample

	double hyperbolic_w(const vector<float> &x) const;
	double time_gap_importance_w(const vector<float> &x) const;
public:
	weighting_method weight_function;
	vector<double> weight_function_params; ///< function parameter
	vector<string> weight_function_inputs; ///< names to fetch input to weight function. can decode MedFeature using json or something from samples
	string json_matrix_model; ///< json to create MedModel if needed
	string weight_samples; ///< samples with weights path
	string weight_attr; ///< the attr name for weights. outcome to take the weight from outcome
	string rep; ///< repository

	/// if true, weights are active and used
	bool active() const { return weight_function != weighting_method::none; };

	weights_params() {
		weight_function = weighting_method::none;
	}

	int init(map<string, string>& map);

	void get_weights(const MedSamples &samples, vector<float> &weights) const;

	void get_weights(const vector<MedSample> &samples, vector<float> &weights) const;

	bool compare(const weights_params &other) const;

	///output weight method param, init line
	string to_string() const;
};

class full_train_args {
public:
	string samples_id; ///< the samples number - later replace with path
	string samples_path; ///< the path
	unordered_set<int> cases_def; ///< cases def list. if not provided, no manipulation
	unordered_set<int> controls_def; ///< controls def list. if not provided, no manipulation
	weights_params w_params; ///< the weights params
	float price_ratio; ///< for matching to time
	string matching_strata; ///< strata for matching
	string matching_json; ///< Json for matching (optional);
	string predictor_type; ///< the predictor type
	string predictor_args; ///< the predictor args

	float auc; ///< the auc pref
	float auc_train; ///< can be empty

	full_train_args();

	string to_string(bool skip_auc = false) const;

	void parse_line(const string &line, const string &f_path);
	void parse_only_args(const string &args_token, const string &f_path);

	bool compare(const full_train_args &o) const;
};

void read_old_results(const string &path, const vector<string> &train_path_order, vector<full_train_args> &results);

bool already_did(const vector<full_train_args> &process_results, const vector<string> &train_path_order, full_train_args &candidante);

//retrive file with list of paths to med samples
void get_train_paths(const string &samples_paths, const vector<int> &cases_labels, const vector<int> &control_labels,
	vector<string> &train_paths_orders, vector<unordered_set<int>> &train_cases_orders,
	vector<unordered_set<int>> &train_controls_orders);

void read_splits_file(const string &split_file, unordered_map<int, int> &pid_to_split);

void read_samples(const vector<string> &train_paths_orders, unordered_map<string, MedSamples> &group_samples,
	const vector<unordered_set<int>> &cases_labels, const vector<unordered_set<int>> &control_labels,
	const unordered_map<int, int> &pid_to_split);

void flat_samples(const unordered_map<string, MedSamples> &train, MedSamples &flat);

void validate_train_test(const unordered_map<string, MedSamples> &a, const unordered_map<string, MedSamples> &b);

void split_train_test_till_year(unordered_map<string, MedSamples> &train, unordered_map<string, MedSamples> &test,
	int till_time);

double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, unordered_map<string, vector<float>> &additional_bootstrap
	, const string &modelFile, const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior);

double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, unordered_map<string, vector<float>> &additional_bootstrap,
	const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior);

double load_train_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, const string &rep_path,
	const unordered_set<string> &feature_selection_set, float change_prior);

void commit_selection(MedFeatures &data, const unordered_set<string> &final_list);

void prepare_rep_from_model(MedModel &mod, MedPidRepository &rep, const string &RepositoryPath);

void prepare_rep_from_model(MedModel &mod, MedPidRepository &rep, const string &RepositoryPath,
	const unordered_map<string, MedSamples> &train, const unordered_map<string, MedSamples> &test);

void enrich_rep_from_model(MedModel& model, MedPidRepository& rep, const string &RepositoryPath);

void prepare_rep_for_signals(MedPidRepository &rep, const string &RepositoryPath, const vector<string> &signals,
	const unordered_map<string, MedSamples> &train, const unordered_map<string, MedSamples> &test);

void run_all_splits(const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test, const string &model_json, MedPidRepository &rep,
	const string &pred_type, const string &pred_args, float price_mathcing, double match_to_prior, const string &strata_str, const string& matching_json, bool verbose,
	float &auc_test, float &auc_train, vector<MedSample> &all_samples_collected, unordered_map<string, MedModel> &model_for_split, const string &bootstrap_params, const string &measure,
	bool verbose_summary = true, const unordered_map<int, unordered_map<int, float>> *pid_time_weights = NULL, const string &save_pattern = "");

void run_all_splits_mat(const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test,
	const string &model_json, MedPidRepository &rep, float price_mathcing, double match_to_prior, const string &strata_str, const string& matching_json, bool verbose,
	unordered_map<string, MedFeatures> &train_mat_for_split, unordered_map<string, MedFeatures> &test_mat_for_split,
	unordered_map<string, MedModel> &model_for_split,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights, bool store_models);

void update_mat_weights(MedFeatures &features, float matching_price_ratio,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights);

void read_ms_config(const string &file_path, const string &base_model,
	vector<MedPredictor *> &all_configs);

void read_selected_model(const string &selected_mode_path,
	string &predictor_name, string &predictor_params);

string clean_model_prefix(const string &s);

string runOptimizerModel(const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test, MedModel &model_feat_generator, const string &model_json, MedPidRepository &rep,
	const string &model_type, const vector<MedPredictor *> &all_models_config,
	unordered_map<string, float> &model_loss, unordered_map<string, float> &model_loss_train, float price_mathcing, double match_to_prior,
	const string &strata_str, const string& matching_json, const string &log_file, const unordered_map<int, unordered_map<int, float>> *pid_time_weights
	, const string &bootstrap_params, const string &measure, double generelization_error_factor, bool debug);

float load_selected_model(MedPredictor *&model, const unordered_map<string, MedFeatures> &train,
	const unordered_map<string, MedFeatures> &test, MedModel &model_feat_generator, const string &model_json, MedPidRepository &rep
	, const string &ms_configs_file, const string &ms_predictor_name,
	const string &results_folder_name, const string &config_folder_path, float price_mathcing, const string &strata_str, const string& matching_json,
	const string &fname, const unordered_map<int, unordered_map<int, float>> *pid_time_weights,
	bool override_existing_results, const full_train_args &train_args, const string &bootstrap_params, 
	const string &measure, double generelization_error_factor, bool debug);

float load_selected_model(MedPredictor *&model, const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test, MedModel &model_feat_generator, const string &model_json, MedPidRepository &rep
	, const string &ms_configs_file, const string &ms_predictor_name,
	const string &results_folder_name, const string &config_folder_path, float price_mathcing, double match_to_prior, const string &strata_str, const string& matching_json,
	const string &fname, const string &bootstrap_params, const string &measure, double generelization_error_factor
	, const unordered_map<int, unordered_map<int, float>> *pid_time_weights = NULL, bool debug = false);

void load_matrix_from_json(MedSamples &samples,
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat, double change_prior, MedModel &mod);

void train_model(MedPredictor &model, MedSamples &flat_train, const unordered_map<string, MedSamples> &train,
	MedModel &model_feat_generator, const string &model_json, MedPidRepository &rep, float matching_ratio, double match_to_prior,
	const string &strata_str, const string& matching_json, const unordered_map<int, unordered_map<int, float>> *pid_time_weights = NULL);

void init_medmodel(MedModel &model, MedPidRepository &rep, const string &json_path);

void split_registry_train_test(const string &rep_path, MedRegistry &regRecords
	, vector<MedRegistryRecord> &only_train,
	vector<MedRegistryRecord> &only_test, MedRepository &rep);

void assign_weights(const string &rep_path, MedFeatures &dataMat, const weights_params &params,
	double change_prior = 0);

void get_folds(const MedSamples &samples, int nfold, vector<int> &folds, const string &rep_path, bool use_in_samples = false);

void get_train_test(const MedSamples &samples, const vector<int> &folds, int choose_fold, int limit,
	MedSamples &train, MedSamples &test);

void split_train_test(const MedSamples &samples, int nfold, const string &rep_path,
	unordered_map<string, MedSamples> &train_samples, unordered_map<string, MedSamples> &test_samples, bool use_in_samples);

void split_train_test(const MedSamples &samples, const MedSamples &t_samples, int nfold, const string &rep_path,
	unordered_map<string, MedSamples> &train_samples, unordered_map<string, MedSamples> &test_samples, bool use_in_samples);

void get_learn_calibration(const string &med_model_json, MedPidRepository &rep, const string &rep_path, const string &calibration_init,
	MedSamples &train_samples, MedSamples &req_samples, int nfolds,
	float price_matching, double match_to_prior, const string &strata_str, const string& matching_json, MedPredictor *predictor, Calibrator &cl,
	const string &bootstrap_params, const string &measure, bool cal_need_learn = true);

void collect_ids_from_samples(const vector<MedSample> &all, const MedSamples &ids_samples, vector<MedSample> &collected);

float auc_samples(const vector<MedSample> &samples, const vector<float> &weights, const string &bootstrap_params, const string &measure);

void index_pid_time_prob(const vector<MedSample> &all_train_flat,
	unordered_map<int, unordered_map<int, float>> &pid_time_prob);

void filter_age_years(MedSamples &samples, MedPidRepository &rep, int min_age, int max_age, int min_year, int  max_year);

void select_splits_numbers(int num_of_splits, int active_splits,
	unordered_set<int> &sel);

void commit_select_splits(const unordered_map<string, MedSamples> &train_samples,
	const unordered_map<string, MedSamples> &test_samples, int active_splits, const unordered_set<int> &sel,
	unordered_map<string, MedSamples> &train_samples_sel,
	unordered_map<string, MedSamples> &test_samples_sel);

void select_splits(const unordered_map<string, MedSamples> &train_samples,
	const unordered_map<string, MedSamples> &test_samples, int active_splits,
	unordered_map<string, MedSamples> &train_samples_sel,
	unordered_map<string, MedSamples> &test_samples_sel);

void samples_to_splits_train_test(const MedSamples &curr_train, const MedSamples &curr_test,
	unordered_map<string, MedSamples> &split_to_samples_train, unordered_map<string, MedSamples> &split_to_samples_test);

void assign_splits_if_needed(unordered_map<string, MedSamples> &train_samples,
	unordered_map<string, MedSamples> &test_samples, int nfolds);

void read_int_array(const string &s, vector<int> &arr, const string &arg_name = "");

void filter_test_bootstrap_cohort(const string &rep, unordered_map<string, MedSamples> &test_samples,
	const string &bt_json, const string &bt_cohort);

#endif