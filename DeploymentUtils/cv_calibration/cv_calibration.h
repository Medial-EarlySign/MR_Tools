// Calibrate scores using cross-validation

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S
#define _SCL_SECURE_NO_WARNINGS

#include "../common/common.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void split_samples(vector<MedSample>& samples, MedSamples& learningSamples, MedSamples& testSampels, int iFold);
void add_calibrated_scores(MedSamples& testSamples, vector<MedSample>& samples, int iFold);
