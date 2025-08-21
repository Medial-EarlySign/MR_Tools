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
#include <boost/algorithm/string/join.hpp>
#include <omp.h>

#include <set>
#include <fstream>
#include <algorithm>
#include <time.h>
#include <unordered_map>


using namespace std;
namespace po = boost::program_options;

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void get_fields(po::variables_map& vm, set<string>& names1, set<string>&names2);
void cross(string& file1, string&file2, char separator, string &common, set<string>& names1, set<string>& names2);
string get_cols(ifstream& inf, string& file, char sep, string& common, set<string>& names, vector<int>& common_cols, vector<int>& names_cols, int first);
inline string get_string(vector<string> fields, char sep, vector<int> cols);
void mySplit(vector<string>& fields, string line, char sep);
char get_sep(string code);