// Get the score corresponding to a given probability of outcome

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);

void read_preds(string& rawFile, vector<pair<int, float>>& preds);
float get_score(vector<pair<int, float>>& preds, int minCases, int minSamples, int nBootstrap, float prob, vector<float>& score_ci);
void bootstrap_sample(int n, vector<int>& indices);
float get_score(vector<pair<int, float>>& preds, vector<int>& indices, int minCases, int minSamples, float prob);
float score2pr(vector<pair<int, float>>& preds, float score);