//#pragma once

#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>

#include <SerializableObject/SerializableObject/SerializableObject.h>
#include <InfraMed/InfraMed/InfraMed.h>
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedUtils/MedUtils/MedGenUtils.h>
#include <Logger/Logger/Logger.h>

#include <algorithm>
#include <time.h>
#include <queue>
#include <omp.h>


using namespace std;
namespace po = boost::program_options;

#define MIN_AGE 30
#define MAX_AGE 85



int read_run_params(int argc, char **argv, po::variables_map& vm);
void buildLookUpTable(MedPidRepository& rep, vector<string>& signals, vector<pair<string, string> >& readCodes, vector<unsigned char>& lut);
int readReadCodes(string& fname, vector<pair<string, string> >& rcs);