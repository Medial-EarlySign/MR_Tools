#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedProcessTools/MedProcessTools/Calibration.h"

#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>

#include <algorithm>
#include <time.h>
#include <stdio.h>

using namespace std;
namespace po = boost::program_options;

// Functions
// Setting folds
void set_folds(int nFolds, MedSamples& samples, MedFeatures& inFeatures);
void set_folds(int nFolds, MedFeatures& inFeatures);
void set_folds(int nFolds, MedSamples& samples);

// Read/Write text vectors
void read_vec(vector<float>& d, const string& fileName);
void write_vec(vector<float>& d, const string& fileName);

// Utilities for learn_from_features
int getNumFolds(MedFeatures& inFeatures);
void split_matrix(MedFeatures& inFeatures, int iFold, MedFeatures& trainMatrix, MedFeatures& testMatrix);

// Utilities for learn_from_samples
int getNumFolds(MedSamples& samples);
void split_samples(MedSamples& samples, int iFold, MedSamples& trainSamples, MedSamples& testSamples);
void split_samples(MedSamples& samples, int iFold, MedSamples& trainSamples, MedSamples& testSamples, vector<float>& weights, vector<float>& trainWeights, vector<float>& testWeights);
void g_comp_split_samples(MedSamples& samples, int iFold, MedSamples& trainSamples, MedSamples& testSamples, vector<float>& preds, vector<float>& trainPreds, vector<float>& testPreds);


// Calibration
void recalibrate(vector<float>& preds, vector<float>& labels, const string& params, vector<float>* outPreds = NULL);

// Cross Validation learning of a classification model
void learn_from_features(MedFeatures& inFeatures, vector<float>& preds, string& predictor, string& params, string& performanceFile, string& calParams, const string& name);
void learn_from_samples(MedSamples& samples, vector<float>& preds, string& modelFile, vector<string>& modelAlts, string& repFile, string& performanceFile, string& calParams, const string& name);

// Cross validation of a regression model
void regression_cross_validation_on_matrix(MedFeatures& inFeatures, int nFolds, string& predictorName, string& predictorParams, string& runDir, string& outFileName,
	vector<float>& preds, vector<float>& labels);
void regression_cross_validation_on_samples(MedSamples& inSamples, vector<float>& weights, MedModel& model, MedPidRepository& rep, int nFolds, string& predictorName, string& predictorParams,
	string& runDir, string& outFileName, vector<float>& preds, vector<float>& labels);

// Run Python scripts for ite (NN)
void prepare_for_nn_model(MedFeatures &inFeatures, string& in_params, string& dir, string& out_params, string suffix);
void learn_nn_model(MedFeatures &inFeatures, string& scriptName, string& params, string& dir, string& predictorFileName);
void apply_nn_model(MedFeatures &inFeatures, string& scriptName, string& params, string& dir, string& predictorFileName);
void my_run(string& command);

// Write Predictor to File
void write_predictor_to_file(MedPredictor *pred, const string& outFile);

// Performance
void write_performance(vector<float>& preds, vector<float>& labels, const string& performanceFile);
void write_regression_performance(vector<float>& v1, vector<float>& v2, const string& performanceFile);