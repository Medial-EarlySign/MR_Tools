#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "InfraMed/InfraMed/MedPidRepository.h"
#include "Logger/Logger/Logger.h"
#include "InfraMed/InfraMed/Utils.h"
#include "MedUtils/MedUtils/MedUtils.h"
#include "MedProcessTools/MedProcessTools/MedValueCleaner.h"
#include "MedStat/MedStat/MedStat.h"
#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>
#include <unordered_set>
#include <string.h>

#include <boost/program_options.hpp>
#include <boost/math/distributions/normal.hpp>

using namespace std;
namespace po = boost::program_options;
using boost::math::normal;


#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

// Functions
string checkSignal(MedPidRepository& rep, int signalId, vector<int>& pIds);
string checkSignalDistribution(MedPidRepository& rep, int signalId, vector<int>& pIds);
float correlateToGaussian(vector<float>& values);