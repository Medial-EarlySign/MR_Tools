#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "Logger/Logger/Logger.h"
#include "InfraMed/InfraMed/Utils.h"
#include "InfraMed/InfraMed/MedPidRepository.h"

#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>

using namespace std;
namespace po = boost::program_options;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

// Functions
int read_run_params(int argc, char **argv, po::variables_map& vm);
void get_members(po::variables_map& vm, string& configFile);
void get_read_code_cases(po::variables_map& vm, string& configFile);
void get_drug_cases(po::variables_map& vm, string& configFile);
int read_list(const string& fname, vector<string>& members);
int read_ids_list(const string& fname, vector<int>& ids);