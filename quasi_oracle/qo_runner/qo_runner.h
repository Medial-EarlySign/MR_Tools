// An envelope for preparing quasi-oracle runs

#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedUtils/MedUtils/MedGlobalRNG.h"

#include <algorithm>
#include <time.h>
#include <stdio.h>

using namespace std;
namespace po = boost::program_options;

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void get_options(string& paramsFile, int nRuns, vector<map<string, string> >& options);
int read_optimization_ranges(string& optFile, map<string, vector<string> >& optimizationOptions);
void create_directory(string& name);
void create_config_file(string& configName, string& subDirName, map<string,string>& runOption);
void read_condor_runner(string& fileName, vector<string>& condor_runner);
void write_file(string& fileName, vector<string>& condor_runner);

