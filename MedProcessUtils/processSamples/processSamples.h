// process Sampels

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void split_samples(MedSamples& in, float& p, string& outFile1, string& outFile2);
void filter_samples(MedSamples& samples, vector<int>& nums, string& outFile);
