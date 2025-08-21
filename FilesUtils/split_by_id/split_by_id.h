// Split file by id


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
#include <boost/algorithm/string.hpp>
#include <omp.h>

#include <set>
#include <fstream>
#include <algorithm>
#include <time.h>
#include <unordered_map>
#include <iostream>
#include <string>

#include <Logger/Logger/Logger.h>

using namespace std;
namespace po = boost::program_options;

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
