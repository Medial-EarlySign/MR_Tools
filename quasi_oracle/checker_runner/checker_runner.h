// An envelope for preparing quasi-oracle runs

#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedUtils/MedUtils/MedGlobalRNG.h"
#include "boost/filesystem.hpp"   // includes all needed Boost.Filesystem declarations

#include <algorithm>
#include <time.h>
#include <stdio.h>

using namespace std;
namespace po = boost::program_options;
namespace fs = boost::filesystem;


// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void read_condor_runner(string& fileName, vector<string>& condor_runner);
void write_file(string& fileName, vector<string>& condor_runner);
void get_directories(const string& dir, const string& prefix, vector<string>& directories);


