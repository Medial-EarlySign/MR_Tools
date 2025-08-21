// A tool for performing quasi-oracle estimation of individual effect

#include "../common/common.h"
#include "configuration.h"

#define MIN_ABS_WGT 0.01

using namespace std;
namespace po = boost::program_options;

// Cross validation learning
void learn_e_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& e);
void learn_e_from_samples(MedSamples& samples, configuration& config, vector<float>& e);
void learn_m_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& m);
void learn_m_from_samples(MedSamples& samples, configuration& config, vector<float>& m);

// Performance
void write_regression_performance(vector<float>& preds, vector<float>& y, vector<float>& t, vector<float>& m, vector<float>& e, const string& performanceFile);
float get_weighted_pearson_corr(vector<float>& preds, vector<float>& labels, vector<float>& weights);

// Learning ite
void learn_ite_from_features(MedFeatures &inFeatures, vector<float>& e, vector<float>& m, configuration& config);
void learn_ite_from_samples(MedSamples& samples, vector<float>& e, vector<float>& m, configuration& config);


