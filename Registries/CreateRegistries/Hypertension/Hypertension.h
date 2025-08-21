
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
#include <Logger/Logger/Logger.h>

#include <algorithm>
#include <time.h>
#include <queue>
#include <omp.h>

using namespace std;
namespace po = boost::program_options;

#define MIN_AGE 30
#define MAX_AGE 85
#define CHUNK 1000000

// Functions

int read_run_params(int argc, char **argv, po::variables_map& vm); // Read running parameters
int readReadCodes(string& fname, vector<pair<string, string> >& rcs); // Read ReadCodes file
int generateHyperTenstionRegistry(MedPidRepository& rep, po::variables_map& vm); // Generate a registry for hypertension
void buildLookupTableForHTDrugs(MedDictionary& dict, vector<char>& lut); // Build a look up table for HT drugs
void fillLookupTableForHTDrugs(MedDictionary& dict, vector<char>& lut, vector<string>& sets, char val);// Build a look up table for HT drugs




