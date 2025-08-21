#include <assert.h>
#include "CommonLib/AnalyzeScores.h"
#include "CommonLib/ValidationFunctions.h"

namespace po = boost::program_options;

int read_run_params(int argc,char **argv, po::variables_map& vm) ;
int read_all_validation_input_data(po::variables_map& vm, input_data& indata) ;
