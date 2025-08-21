
#include "InfraMedTests.h"
#include <MedProcessTools/MedProcessTools/FeatureGenerator.h>

#include "Catch-master/single_include/catch.hpp"
#include <boost/filesystem.hpp>
#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL


extern MedLogger global_logger;

unsigned int Factorial(unsigned int number) {
	return number <= 1 ? number : Factorial(number - 1)*number;
}

TEST_CASE("Factorials are computed", "[factorial]") {
	REQUIRE(Factorial(1) == 1);
	REQUIRE(Factorial(2) == 2);
	REQUIRE(Factorial(3) == 6);
	REQUIRE(Factorial(10) == 3628800);
}

int read_repository(string config_file, vector<int>& ids, vector<string>& signals, MedPidRepository& rep) {

	vector<string> sigs = signals;
	sigs.push_back("GENDER");
	sigs.push_back("BYEAR");
	sigs.push_back("TRAIN");
	MLOG("Before reading config file %s\n", config_file.c_str());


	if (rep.read_all(config_file,ids,sigs) < 0) {
		MLOG("Cannot init repository %s\n", config_file.c_str());
		return -1;
	}

	size_t nids = rep.index.pids.size();
	size_t nsigs = rep.index.signals.size();
	MLOG("Read %d Ids and %d signals\n", (int)nids, (int)nsigs);

	return 0;
}

TEST_CASE("Test binned lm estimates", "[binnedLM]") {

	// Read Signals
	MLOG("Reading signals\n");
	vector<string> signals = { "Hemoglobin", "BMI", "Platelets" };

	// Read Samples
	MLOG("Reading samples\n");
	MedSamples allSamples;
	for (int i = 5000300; i < 5000300 + 500000; i++) {
		MedIdSamples idSamples;
		idSamples.id = i;
		MedSample sample;
		sample.id = i;
		idSamples.samples.push_back(sample);
		allSamples.idSamples.push_back(idSamples);
	}	

	vector<int> ids;
	allSamples.get_ids(ids);

	// Read Repository
	string config_file;
	for (string s : {"/server/Work/CancerData/Repositories/THIN/build_jan2017/thin.repository", "W:\\CancerData\\Repositories\\THIN\\build_nov2016\\thin.repository"})
		if (boost::filesystem::exists(s)) {
			MLOG("[%s] exists, let's use it\n", s.c_str());
			config_file = s;
			break;
		}
	REQUIRE(config_file.size() > 0);

	MLOG("Initializing repository\n");
	return;
	MedPidRepository rep;
	int rc = read_repository(config_file, ids, signals, rep);
	REQUIRE(rc >= 0);
	string in = "fg_type = binnedLM; estimation_points = -180,0,180; signal = Hemoglobin";
	FeatureGenerator *feat_gen = FeatureGenerator::create_generator(in);
	BinnedLmEstimates* blm_gen = dynamic_cast<BinnedLmEstimates*>(feat_gen);
	REQUIRE(blm_gen != NULL);
	for (int i: blm_gen->params.bin_bounds)
		MLOG("bound: %d\n", i);
	for (int i : blm_gen->params.estimation_points)
		MLOG("estimation point: %d\n", i);
	blm_gen->set_signal_ids(rep.dict);
	MLOG("rep.pids: %d\n", rep.pids.size());
	rc = blm_gen->learn(rep);
	MLOG("returned from learn\n");
	REQUIRE(rc >= 0);
	REQUIRE(blm_gen->models.size() == 256);
	for (int model_type : {100, 255}) {
		MLOG("b0[%d] = %f\n", model_type, blm_gen->models[model_type].b0);
		for (size_t i = 0; i < blm_gen->models[model_type].b.size(); i++)
			MLOG("b[%d,%d] = %f\n", model_type, i, blm_gen->models[model_type].b[i]);
	}
	for (auto m : blm_gen->means) {
		MLOG("m = [%f, %f]\n", m[0], m[1]);
	}

}