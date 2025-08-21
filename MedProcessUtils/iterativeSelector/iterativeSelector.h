// Wrapper (iterative) feature selection

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void adjusted_univariate_slection(MedFeatures& features, set<string>& required, string& initializer);
void runSelection(MedFeatures& features, po::variables_map& vm);
void add_features_from_file(unordered_set<string>& list, string file);
void read_retrace_info(string& fileName, string& mode, vector<string>& families);