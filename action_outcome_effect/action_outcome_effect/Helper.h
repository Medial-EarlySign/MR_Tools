#ifndef __HELPER_H__
#define __HELPER_H__
#include <string>
#include <random>
#include <vector>
#include <unordered_map>
#include <map>
#include "MedIO/MedIO/MedIO.h"
#include "Logger/Logger/Logger.h"
#include "MedAlgo/MedAlgo/BinSplitOptimizer.h"
#include "MedProcessTools/MedProcessTools/MedFeatures.h"
#include "MedAlgo/MedAlgo/MedAlgo.h"

using namespace std;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

inline void fix_path_wrap(string &path) {
	string fixed;
	fix_path(path, fixed);
	path.swap(fixed);
}

float get_weight(float prob, float outcome, float min_prob);

void test_independece(const vector<string> &groups_x, const vector<float> &groups_y,
	const vector<float> &labels, const vector<string> &groups_x_sorted,
	float &tot_chi, int &tot_dof, bool print, bool print_full,
	int smooth_chi, float at_least_diff);

void createProbabiltyBins(const MedFeatures &feats, BinSettings probabilty_bin_settings
	, const map<string, BinSettings> &features_bin_settings, vector<float> &score_probabilty_bins);

struct loss_confounders_params {
	string validator_type;
	string validator_init;
	MedFeatures *all_matrix;
	int validation_nFolds;
	mt19937 *random_generator;
};

template<class T> string get_name(const map<string, T> &mapper, const string &col_name);
void read_strings(const string &file_path, vector<string> &groups);
void read_confounders(const string &file_path, unordered_set<string> &confounders);
double loss_target_AUC(const vector<float> &preds, const vector<float> &y, vector<float> &preds_validation, void *params);
double loss_target_confounders_AUC(const vector<float> &preds, const vector<float> &y, void *params);
void write_model_selection(const vector<pair<string, unordered_map<string, float>>> &measures, const string &save_path);
void read_ms_config(const string &file_path, const string &base_model, vector<MedPredictor *> &all_configs);
void gether_stats(const vector<unordered_map<string, float>> &raw, map<string, float> &summerized);
template<class T> void commit_selection(vector<T> &vec, const vector<int> &idx);
void print_stats(const MedFeatures &feats, const vector<string> &action, const unordered_map<string, int> &action_to_val);
void match_samples_pairwise(vector<MedSample>& samples, vector<float>& matchedValue,
	const vector<const vector<float> *> &metric_data, float caliper, vector<int>& matchedSamples, bool quiet = true);
string runOptimizerModel(MedFeatures &dataMat, const vector<MedPredictor *> &all_models_config,
	int nFolds, mt19937 &random_generator, const string &calibrator_init, float min_prob,
	double(*loss_func)(const vector<float> &, const vector<float> &, void *), void *params,
	vector<pair<string, unordered_map<string, float>>> &measures);
void print_age_stats(const MedFeatures &feats, const vector<string> &action,
	const unordered_map<string, int> &action_to_val, int age_bin);
void read_attr_from_samples(const string &attr, const vector<MedSample> &samples, vector<float> &vals,
	float missing_val);
void read_attr_from_samples(const string &attr, const vector<MedSample> &samples, vector<string> &vals,
	const string &missing_val);

#endif // !__HELPER_H__

