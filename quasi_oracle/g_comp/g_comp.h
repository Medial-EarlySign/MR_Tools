// A tool for performing g-computation regression for estimation of individual effect

#include "../common/common.h"
#include "g_comp_configuration.h"

using namespace std;
namespace po = boost::program_options;

// Functions
void learn_initial_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& preds);
void two_models_learn_initial_from_features(MedFeatures& inFeatures, configuration& config, vector<float>& preds);

void learn_initial_from_samples(MedSamples& inSamples, configuration& config, vector<float>& preds);
void two_models_learn_initial_from_samples(MedSamples& inSamples, configuration& config, vector<float>& preds);


// Second layer learning
void learn_final_from_features(MedFeatures& inFeatures, vector<float>& preds, configuration& config);
void learn_final_from_samples(MedSamples& inSamples, vector<float>& preds, configuration& config);
void regression_cross_validation_on_samples(MedSamples& samples, MedPidRepository& rep, configuration& config, vector<float>& inPreds, vector<float>& outPreds,
	vector<float>& labels);
void get_regression_model(MedSamples& inSamples, MedPidRepository& rep, configuration& config, vector<float>& inPreds, MedModel& model, string& outFileName);

// Splitting by value of feature/attribute
void getSubMatrix(MedFeatures& matrix, const string& ftr, const float value, MedFeatures& outMatrix, vector<int>& indices);
void getSubSamples(MedSamples& inSamples, const string& attr, const float value, MedSamples& outSamples, vector<int>& indices);

// Generate counter-factual matrix
void generateMatrix(MedFeatures& inFeatures, vector<float>& preds, string treatName, bool include_original, MedFeatures& outFeatures);