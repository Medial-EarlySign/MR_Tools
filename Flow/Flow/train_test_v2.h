#pragma once
// Cross Validator = an object for performing cross validation = learning set filterer + model + test set filterer

#include <InfraMed/InfraMed/InfraMed.h>
#include <Logger/Logger/Logger.h>
#include <MedProcessTools/MedProcessTools/RepProcess.h>
#include <MedProcessTools/MedProcessTools/FeatureProcess.h>
#include <MedProcessTools/MedProcessTools/FeatureGenerator.h>
#include <MedAlgo/MedAlgo/MedAlgo.h>
#include <MedProcessTools/MedProcessTools/MedSamples.h>
#include <MedProcessTools/MedProcessTools/SampleFilter.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedSplit/MedSplit/MedSplit.h>


#define DEFAULT_CV_NTHREADS 8

//.......................................................................................
//.......................................................................................
// learns cross-validated on a set of train samples + a full model from all
// then applies correct models on a set of validation samples 
//.......................................................................................
//.......................................................................................

class TrainTestV2 {
public:

	// Threading
	int nthreads;

	// config for all input files
	string name;
	string wdir;
	string f_learning_samples;
	string f_learning_samples_for_cv;
	float learning_sampling_prob0 = 1.0;
	float learning_sampling_prob1 = 1.0;
	float validation_sampling_prob0 = 1.0;
	float validation_sampling_prob1 = 1.0;
	string f_validation_samples;
	string f_split;
	string f_rep;
	string f_model_init;
	string prefix;
	string validation_prefix;
	string steps;
	string active_splits_str;
	string cv_on_train_str;
	int train_flag, validate_flag, cv_on_train_flag, filter_train_cv;
	string save_matrix_flag;
	string save_contribs_flag;
	string save_matrix_splits;
	string conf_fname;
	string preds_format;
	string pred_params_fname;
	int time_unit_wins;
	int time_unit;
	vector<string> json_alt;
	vector<string> active_split_requests;
	map<int, bool> active_splits;
	vector <vector<string>> paramsList;
	vector<string> post_processors_sample_files;

	// data containers
	MedSamples full_learning_samples, full_validation_samples, full_learning_cv_samples;
	MedSamples learning_samples, validation_samples;
	vector<MedSamples> post_processors_samples;
	MedSplit sp;
	MedPidRepository *rep;
	vector<MedModel *> models;

	TrainTestV2() {
		nthreads = DEFAULT_CV_NTHREADS;
		train_flag = 0; validate_flag = 0; cv_on_train_flag = 0; save_matrix_flag = "none"; save_matrix_splits = "all";  conf_fname = "";
		name = ""; wdir = ""; f_learning_samples = ""; f_validation_samples = ""; pred_params_fname = "";
		f_split = ""; f_rep = ""; prefix = ""; f_model_init = ""; preds_format = "csv"; save_contribs_flag = "none";
		f_learning_samples_for_cv = ""; filter_train_cv = 0;
	}

	~TrainTestV2() {};

	// Run
	void runner();

private:
	void read_config(const string &config_name);
	void read_all_input_files();
	void set_parameters_from_cmd_line();
	void train();
	void split_validate_to_cv_and_full(unordered_set<int>& should_go_to_cv);
	void validate();
	void init_steps(const vector<string> &steps_params);
	int read_predictor_params(string &fname);
	void prepareGridSearch(vector<MedFeatures> &featuresVecLearn, vector<MedFeatures> &featuresVecApply, vector<MedSamples> &learnSamples, vector<MedSamples> &validSamples);
	void runGridSearch(vector<MedFeatures> &featuresVecLearn, vector<MedFeatures> &featuresVecApply, ofstream &perf_fstream, vector<vector<string>> &paramsList, vector<MedSamples> &validSamples);
};

