// utilities sprogram

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
void attr2ftr(po::variables_map& vm);
