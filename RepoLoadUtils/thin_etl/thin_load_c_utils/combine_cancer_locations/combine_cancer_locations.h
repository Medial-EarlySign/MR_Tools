// Perform cross-validation

#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>


#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>
#include <boost/filesystem.hpp>
#include <omp.h>

#include <algorithm>
#include <time.h>
#include <string.h>

#include <iostream>
#include <MedTime/MedTime/MedTime.h>

using namespace std;
namespace po = boost::program_options;
namespace fs = boost::filesystem;

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void get_files(string dir, string prefix, vector<string>& files);
void read_translation_table(string file, vector<vector<string>>& table);
void handle_file(string& inFile, ofstream& outf, vector<vector<string>>& table);
void handle_id(vector<vector<string>>& idLines, ofstream& outf, vector<vector<string>>& table);