// Perform cross-validation

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "cv.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#include <MedUtils/MedUtils/MedGlobalRNG.h>

int main(int argc, char *argv[])
{
	
	global_logger.init_level(LOG_MEDALGO, 6);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// In/Out patients
	if (vm.count("inpatient")) {
		MLOG("Working on in-patient data\n");
		global_default_time_unit = global_default_windows_time_unit = MedTime::Minutes;
	}

	string configFile = vm["rep"].as<string>();
	string samplesFile = vm["samples"].as<string>();
	string inModel = vm["inModel"].as<string>();

	// Read Model json
	cerr << "Reading model" << endl;
	MedModel model;
	vector<string> jsonAlts;
	if (vm.count("jsonAlt"))
		for (string alt : vm["jsonAlt"].as<vector<string>>())
			jsonAlts.push_back(alt);
	model.init_from_json_file_with_alterations(inModel, jsonAlts);

	// Read training Samples
	cerr << "Reading samples" << endl;
	MedSamples samples;
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	// Override splits
	if (vm.count("nfolds")) {
		int nfolds = vm["nfolds"].as<int>();
		for (int idx = 0; idx < samples.idSamples.size(); idx++) {
			samples.idSamples[idx].split = idx%nfolds;
			for (auto& sample : samples.idSamples[idx].samples)
				sample.split = idx%nfolds;
		}
	}

	int nSplits = samples.nSplits();

	// Test samples
	MedSamples testSamples;
	if (vm.count("test_samples")) {
		string testSamplesFile = vm["test_samples"].as<string>();
		if (testSamples.read_from_file(testSamplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from file %s", testSamplesFile.c_str());
	}
	else
		testSamples = samples;

	// Take care of test-samples splits
	map<int, int> id2Split;
	for (auto& idSamples : samples.idSamples)
		id2Split[idSamples.id] = idSamples.split;

	int nAssigned = 0;
	for (auto& idSamples : testSamples.idSamples) {
		int id = idSamples.id;
		if (id2Split.find(id) == id2Split.end())
			id2Split[id] = (nAssigned++) % nSplits;
			//MTHROW_AND_ERR("Cannot find test-samples id %d in train-samples\n", id);
	
		idSamples.split = id2Split[id];
		for (auto& sample : idSamples.samples)
			sample.split = idSamples.split;
	}
	MLOG("Assigned folds to %d ids not in training set\n", nAssigned);


	// Folds to take
	vector<int> folds;
	get_folds(vm, folds, nSplits);

	cerr << "Getting ids" << endl;
	vector<int> ids;
	set<int> ids_set;

	samples.get_ids(ids);
	for (int id : ids)
		ids_set.insert(id);
	MLOG("Found %d ids in training samples\n", (int)ids.size());

	testSamples.get_ids(ids);
	for (int id : ids)
		ids_set.insert(id);
	MLOG("Found %d ids in test samples\n", (int)ids.size());

	ids.clear();
	for (int id : ids_set)
		ids.push_back(id);
	MLOG("Found %d ids in all samples\n", (int)ids.size());


	// Read Repository
	MedPidRepository rep;
	model.load_repository(configFile, ids, rep, true);

	// Matching info
	SampleFilter *matcher = NULL;
	if (vm.count("matching")) {
		string matchingParams = vm["matching"].as<string>();
		matcher = SampleFilter::make_filter("match", matchingParams);
	}

	// end stages
	string end_stage_s = vm["learn_end_stage"].as<string>();
	MedModelStage learn_end_stage = MedModel::get_med_model_stage(end_stage_s);
	end_stage_s = vm["apply_end_stage"].as<string>();
	MedModelStage apply_end_stage = MedModel::get_med_model_stage(end_stage_s);

	// Cross Validation
	MedSamples allTestSamples;
	for (int iFold : folds) {
		cerr << "Working on split " << iFold + 1 << "/" << nSplits << endl;

		// Split
		MedSamples iTrainSamples, iTestSamples;
		for (MedIdSamples& idSamples : samples.idSamples) {
			if (idSamples.split != iFold)
				iTrainSamples.idSamples.push_back(idSamples);
		}
		for (MedIdSamples& idSamples : testSamples.idSamples) {
			if (idSamples.split == iFold)
				iTestSamples.idSamples.push_back(idSamples);
		}

		// Match
		if (matcher != NULL)
			matcher->filter(rep, iTrainSamples);

		// Learn
		model.clear();
		model.init_from_json_file_with_alterations(inModel, jsonAlts);
		model.learn(rep, &iTrainSamples,MED_MDL_LEARN_REP_PROCESSORS,learn_end_stage);

		// Add pre-processors ?
		if (vm.count("preProcessors")) {
			string preProcessorsFile = vm["preProcessors"].as<string>();
			model.add_pre_processors_json_string_to_model("", preProcessorsFile);
		}

		// Apply
		model.apply(rep, iTestSamples, MED_MDL_APPLY_FTR_GENERATORS, apply_end_stage);

		// Append to allTestSamples
		for (MedIdSamples& idSamples : iTestSamples.idSamples)
			allTestSamples.idSamples.push_back(idSamples);

	}

	// Perfomance
	if (vm.count("outPerformance")) {
		string perforamcenFile = vm["outPerformance"].as<string>();
		print_auc_performance(allTestSamples, folds, perforamcenFile);
	}

	// Write Samples
	if (vm.count("outSamples")) {
		// Remove attributes if required
		if (vm.count("no_attr")) {
			for (MedIdSamples& idSamples : allTestSamples.idSamples) {
				for (MedSample& sample : idSamples.samples)
					sample.attributes.clear();
			}
		}
		string outSamplesFile = vm["outSamples"].as<string>();
		if (allTestSamples.write_to_file(outSamplesFile) != 0)
			MTHROW_AND_ERR("Cannot write predictinos to %s\n", outSamplesFile.c_str());
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("samples", po::value<string>()->required(), "training samples")
			("test_samples", po::value<string>(), "optional test samples, using training samples if not given")
			("inModel", po::value<string>()->required(), "model json file")
			("jsonAlt", po::value<vector<string>>()->composing(), "(multiple) alterations to model json file")
			("matching", po::value<string>(), "optional matching parameters")
			("outPerformance", po::value<string>(), "performance output file")
			("outSamples", po::value<string>(), "samples output file")  
			("inpatient", "indicate that relevant data is in-patient data")
			("nfolds", po::value<int>(), "if given, replace given splits with id-index%nfolds")
			("folds", po::value<string>(), "comma-separated list of folds to actually take for test. If not given - take all")
			("learn_end_stage", po::value<string>()->default_value("end"), "end stage of learning")
			("apply_end_stage", po::value<string>()->default_value("end"), "end stage of applying")
			("preProcessors", po::value<string>(), "optional (learning-less) pre-processors json file to add for application stage (e.g. history limit)")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
			("no_attr", "do not write attributes")

			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);
	}
	catch (exception& e) {
		string err = "error: " + string(e.what()) + "; run with --help for usage information\n";
		throw runtime_error(err);
	}
	catch (...) {
		throw runtime_error("Exception of unknown type!\n");
	}
}

