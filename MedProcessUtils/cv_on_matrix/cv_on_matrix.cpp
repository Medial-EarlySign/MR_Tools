// Perform cross-validation

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "cv_on_matrix.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	global_logger.init_level(LOG_MEDALGO, 6);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// Sanity
	if (vm.count("model") && (vm.count("predictor") || vm.count("params")))
		MTHROW_AND_ERR("Either model or predictor+params must be given");

	// Read Features
	MLOG("Reading Features\n");
	MedFeatures features;
	readMatrix(features, vm);
	features.samples_sort();

	// Test Features
	MedFeatures testFeatures;
	if (vm.count("test_inCsv") + vm.count("test_inBin")) {
		readMatrix(testFeatures, vm, "test_inCsv", "test_inBin");
		testFeatures.samples_sort();
	} else
		testFeatures = features;

	// Input options
	MedModel model;
	if (vm.count("inModel")) {
		// Initialize predictor
		MLOG("Initializing\n");
		string modelFile = vm["inModel"].as<string>();

		// Read Model json
		vector<string> jsonAlts;
		if (vm.count("json_alt"))
			for (string alt : vm["json_alt"].as<vector<string>>())
				jsonAlts.push_back(alt);
		model.init_from_json_file_with_alterations(modelFile, jsonAlts);
	}
	else {
		if (!(vm.count("predictor") && vm.count("params")))
			MTHROW_AND_ERR("Both predictor and params must be given");

		// Initialize predictor
		MLOG("Initializing Predictor\n");
		string predictorType = vm["predictor"].as<string>();
		string predictorParams = vm["params"].as<string>();
		model.predictor = MedPredictor::make_predictor(predictorType, predictorParams);
	}
	
	// Override splits
	map<int, int> id_folds;
	int nfolds = (vm.count("nfolds")) ? vm["nfolds"].as<int>() : 0;
	if (nfolds > 0) {
		int idx = 0;
		for (auto& sample : features.samples) {
			int id = sample.id;
			if (id_folds.find(id) == id_folds.end()) {
				id_folds[id] = idx % nfolds;
				idx++;
			}
			sample.split = id_folds[id];
		}
	}
	else {
		for (auto& sample : features.samples) {
			int id = sample.id;
			if (sample.split == -1 || (id_folds.find(id) != id_folds.end() && sample.split != id_folds[id]))
				MTHROW_AND_ERR("Split problem for id %d in training features", id);
			id_folds[id] = sample.split;
		}
	}

	// Set test splits according to learning splits
	int idx = 0;
	for (auto& sample : testFeatures.samples) {
		int id = sample.id;
		if (id_folds.find(id) == id_folds.end()) {
			if (nfolds)
				id_folds[id] = idx % nfolds;
			else
				id_folds[id] = 0;
		}
		sample.split = id_folds[id];
	}

	// Folds to take
	int nSplits = medial::process::nSplits(features.samples);
	vector<int> folds;
	get_folds(vm, folds, nSplits);

	// end stages
	string end_stage_s = vm["learn_end_stage"].as<string>();
	MedModelStage learn_end_stage = MedModel::get_med_model_stage(end_stage_s);
	end_stage_s = vm["apply_end_stage"].as<string>();
	MedModelStage apply_end_stage = MedModel::get_med_model_stage(end_stage_s);

	// Cross Validation
	MedPidRepository dummyRep;
	MedSamples dummySamples, applySamples;
	vector<MedSample> allTestSamples, testSamples;

	for (int iFold : folds) {
		cerr << "Working on split " << iFold + 1 << "/" << nSplits << endl;

		// Learn
		get_features(features, model.features, iFold, true);
		cerr << model.features.data.size() << " X " << model.features.samples.size() << "\n";
		model.learn(dummyRep, &dummySamples, MED_MDL_LEARN_FTR_PROCESSORS, learn_end_stage);

		// Apply
		get_features(testFeatures, model.features, iFold, false);
		applySamples.import_from_sample_vec(model.features.samples);

		cerr << model.features.data.size() << " X " << model.features.samples.size() << "\n";
		model.apply(dummyRep, applySamples, MED_MDL_APPLY_FTR_PROCESSORS,apply_end_stage);

		// Append to allTestSamples
		applySamples.export_to_sample_vec(testSamples);
		for (MedSample& sample : testSamples)
			allTestSamples.push_back(sample);
	}

	// Perfomance
	MedSamples samples;
	samples.import_from_sample_vec(allTestSamples);
	if (vm.count("outPerformance")) {
		string perforamcenFile = vm["outPerformance"].as<string>();
		print_auc_performance(samples, folds, perforamcenFile);
	}

	// Write Samples
	if (vm.count("outSamples")) {
		string outSamplesFile = vm["outSamples"].as<string>();
		if (samples.write_to_file(outSamplesFile) != 0)
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
			("predictor", po::value<string>(), "predictor type")
			("params", po::value<string>(), "predictor parameters")
			("inModel", po::value<string>(), "model json file")
			("json_alt", po::value<vector<string>>()->composing(), "(multiple) alterations to model json file")
			("inCsv", po::value<string>(), "input matrix as csv file")
			("inBin", po::value<string>(), "input matrix as bin file")
			("test_inCsv", po::value<string>(), "optional test matrix as csv file")
			("test_inBin", po::value<string>(), "optional test matrix as bin file")
			("outPerformance", po::value<string>(), "performance output file")
			("outSamples", po::value<string>(), "samples output file")
			("nfolds", po::value<int>(), "if given, replace given splits with id-index%nfolds")
			("folds", po::value<string>(), "comma-separated list of folds to actually take for test. If not given - take all")
			("learn_end_stage", po::value<string>()->default_value("end"), "end stage of learning")
			("apply_end_stage", po::value<string>()->default_value("end"), "end stage of applying")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
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


