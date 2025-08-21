// An envelope for preparing quasi-oracle runs

#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "boost/filesystem.hpp"   // includes all needed Boost.Filesystem declarations

#include <algorithm>
#include <time.h>
#include <stdio.h>

using namespace std;
namespace po = boost::program_options;
namespace fs = boost::filesystem;

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void get_directories(const string& dir, const string& prefix, vector<string>& directories);
void get_params(vector<string>& directories, const string& config, const string& inField, vector<set<string>>& params);
void get_performance(vector<string>& directories, const string& perf,  vector<float>& performance);
void get_mean_performance(vector<set<string>>& params, vector<float>& performance, map<string, pair<int, float>>& performanceMean);

