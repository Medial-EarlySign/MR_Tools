// Generate a samples set

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm, const unordered_set<string> &all_stats);

float get_auc(const vector<float>& v1, const  vector<float>& v2);
float get_explained(const vector<float>& v1, const  vector<float>& v2, const  vector<float>& w);
float get_l2_err(const vector<float>& v1, const  vector<float>& v2, const  vector<float>& w);
int read_data(po::variables_map& vm, vector<float>& v1, vector<float>& v2, vector<float>& w);
void get_optimal_accuracy(const vector<float>& labels, const vector<float> &preds, float& acc, float& bnd);
int read_data_from_stream(po::variables_map& vm, istream& inf, vector<float>& v1, vector<float>& v2, vector<float>& w);

void sample(const vector<float>& v1, const  vector<float>& v2, const  vector<float>& w, vector<float>& bootstrap_v1, vector<float>& bootstrap_v2, vector<float>& bootstrap_w);
void get_stat_val(const string &stat_test, const vector<float>& v1, const vector<float>& v2, const vector<float> &w,
	vector<float> &values);