// Perform predictor hyper-parameters tuning (start from matrix)

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "Optimize_HyperParams_on_matrix.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	string outFile = vm["out"].as<string>();
	ofstream of(outFile);
	if (!of)
		MTHROW_AND_ERR("Cannot open %s for writing\n", outFile.c_str());


	// Read and select parameters options
	vector<map<string, string> > predictorOptions;
	string predictorParamsFile = vm["predictorParamsFile"].as<string>();
	int nPredictorRuns = vm.count("nPredictorRuns") ? vm["nPredictorRuns"].as<int>() : -1;
	get_options(predictorParamsFile, nPredictorRuns, predictorOptions);

	vector<string> predictorParams;
	if (predictorOptions.size() == 0)
		return 0;
	else {
		for (auto& rec : predictorOptions[0])
			predictorParams.push_back(rec.first);
	}

	// Read Features
	MLOG("Reading Features\n");
	MedFeatures features;
	readMatrix(features, vm);
	features.samples_sort();

	// Test Features
	MedFeatures validationFeatures;
	if (vm.count("test_inCsv") + vm.count("test_inBin")) {
		readMatrix(validationFeatures, vm, "test_inCsv", "test_inBin");
		validationFeatures.samples_sort();
	}
	else
		validationFeatures = features;

	// Override splits
	MLOG("Handlnig Folds\n");
	map<int, int> id_folds;
	if (vm.count("nfolds")) {
		int idx = 0;
		int nfolds = vm["nfolds"].as<int>();
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

	// Folds to take
	int nSplits = medial::process::nSplits(features.samples);
	vector<int> folds;
	get_folds(vm, folds, nSplits);
	int nOutSplit = (int)folds.size();

	// Set test splits according to learning splits
	for (auto& sample : validationFeatures.samples) {
		int id = sample.id;
		if (id_folds.find(id) == id_folds.end())
			id_folds[id] = folds[0];
		sample.split = id_folds[id];
	}

	// get vector of performance measurements 
	MLOG("Reading measures\n");
	vector<Measurement> msrs;
	string msrFileName = vm["msrFile"].as<string>();
	Measurement::read_from_file(msrFileName, msrs);

	vector<vector<vector<float>>> all_prfs(nOutSplit);
	for (int i = 0; i < nOutSplit; i++) {
		all_prfs[i].resize(predictorOptions.size());
		for (int j = 0; j < predictorOptions.size(); j++)
			all_prfs[i][j].resize(msrs.size());
	}

	// Cross Validation
	MLOG("Going at it\n");
	MedPidRepository dummyRep;
	MedSamples dummySamples, applySamples;
	vector<MedSample> allTestSamples, testSamples;


	MedTimer timer;
	float tot_time = 0;
	string predictor_type = vm["predictor"].as<string>();
	MedFeatures learnFeatures, testFeatures;

	for (int idx = 0; idx < nOutSplit; idx++) {
		int iFold = folds[idx];
		
		// Split
		get_features(features, learnFeatures, iFold, true);
		get_features(validationFeatures, testFeatures, iFold, false);
		
		// Loop on options, learn & apply
		for (int iOption = 0; iOption < predictorOptions.size(); iOption++) {
			timer.start();
			MLOG("Working on split %d (%d/%d) Option %d/%d\n", iFold, idx + 1, nOutSplit, iOption + 1, (int)predictorOptions.size());
			MLOG("Params:");
			for (auto& rec : predictorOptions[iOption])
				MLOG("\t%s:%s", rec.first.c_str(), rec.second.c_str());
			MLOG("\n");

			MedPredictor *predictor = MedPredictor::make_predictor(predictor_type);
			predictor->set_params(predictorOptions[iOption]);
			predictor->learn(learnFeatures);
			predictor->predict(testFeatures);
			applySamples.import_from_sample_vec(testFeatures.samples);
			delete predictor;

			// Performance
			vector<vector<float> > tmp_prfs;
			get_performance(applySamples, msrs, tmp_prfs);
			for (int iMsr = 0; iMsr < msrs.size(); iMsr++)
				all_prfs[idx][iOption][iMsr] = tmp_prfs[iMsr][1];

			timer.take_curr_time();
			float time_diff = timer.diff_sec();
			tot_time += time_diff;
			MLOG("\tOption time = %.2fsec . Total time so far = %.2fsec\n", time_diff, tot_time);

		}
	}

	// Print
	print_performance(of, predictorParams, msrs, predictorOptions, folds, all_prfs);

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("inCsv", po::value<string>(), "input matrix as csv file")
			("inBin", po::value<string>(), "input matrix as bin file")
			("test_inCsv", po::value<string>(), "optional test matrix as csv file")
			("test_inBin", po::value<string>(), "optional test matrix as bin file")
			("predictor", po::value<string>()->required(), "predictor type")
			("predictorParamsFile", po::value<string>()->required(), "file with possible options for parameters")
			("nPredictorRuns", po::value<int>(), "optional number of parameters combinations to check")
			("out", po::value<string>()->required(), "performance output file")
			("nfolds", po::value<int>(), "if given, replace given splits with id-index%nfolds")
			("folds", po::value<string>(), "comma-separated list of folds to actually take for test. If not given - take all")
			("msrFile", po::value<string>()->required(), "file with performance measurements")
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