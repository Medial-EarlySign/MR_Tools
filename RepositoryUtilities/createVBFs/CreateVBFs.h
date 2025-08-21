#pragma once
#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "Logger/Logger/Logger.h"
#include "InfraMed/InfraMed/Utils.h"
#include "medial_utilities/medial_utilities/globalRNG.h"
#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>
#include <boost/random/mersenne_twister.hpp>
#include <boost/random/uniform_int.hpp>
#include <boost/random/variate_generator.hpp>
#include <algorithm>

using namespace std ;
namespace po = boost::program_options;

struct randomGen : unary_function<unsigned, unsigned> {
	boost::mt19937 &_state;
	unsigned operator()(unsigned i) {
		boost::uniform_int<> rng(0, i - 1);
		return rng(_state);
	}
	randomGen(boost::mt19937 &state) : _state(state) {}
};


#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

// Functions
int readRunParams(int argc, char **argv, po::variables_map& vm);
int createIdLists(const string& configFile, const string& outDir, int nfolds, bool skipInternal, bool skipExternal);
int createVBFs(string& config, string& group, string& outDir, string& name, int nfolds, bool skipInternal, bool skipExternal);
int createVBF(const string& fileName, const string& configFileName, const string& group, const string& idsFileName);
int writeIdsToFile(const string& fileName, vector<int>& ids);