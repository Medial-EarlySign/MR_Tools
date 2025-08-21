// Perform hyper-parameters tuning

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "Optimize_HyperParams.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

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

	// Read Model json
	cerr << "Reading model" << endl;
	MedModel model;
	model.init_from_json_file(inModel);

	// Read Samples
	cerr << "Reading samples" << endl;
	MedSamples samples;
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	// Test samples
	MedSamples testSamples;
	if (vm.count("test_samples")) {
		string testSamplesFile = vm["test_samples"].as<string>();
		if (testSamples.read_from_file(testSamplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from file %s", testSamplesFile.c_str());
	}
	else
		testSamples = samples;

	// Override splits
	if (vm.count("nfolds")) {
		int nfolds = vm["nfolds"].as<int>();
		for (int idx = 0; idx < samples.idSamples.size(); idx++) {
			samples.idSamples[idx].split = idx % nfolds;
			for (MedSample& sample : samples.idSamples[idx].samples)
				sample.split = samples.idSamples[idx].split;
		}
	}

	// Folds to take
	int nSplits = samples.nSplits();
	cerr << "Working with " << nSplits << " splits\n";
	vector<int> folds;
	get_folds(vm, folds, nSplits);
	int nOutSplit = (int) folds.size();

	// Take care of test-samples splits
	map<int, int> id2Split;
	for (auto& idSamples : samples.idSamples)
		id2Split[idSamples.id] = idSamples.split;

	for (auto& idSamples : testSamples.idSamples) {
		int id = idSamples.id;
		if (id2Split.find(id) == id2Split.end())
			id2Split[id] = folds[0];

		idSamples.split = id2Split[id];
		for (auto& sample : idSamples.samples)
			sample.split = idSamples.split;
	}

	cerr << "Getting ids" << endl;
	vector<int> ids;
	samples.get_ids(ids);

	// Read Repository
	MedPidRepository rep;
	model.load_repository(configFile, ids, rep, true);

	// Matching info
	SampleFilter *matcher = NULL;
	if (vm.count("matching")) {
		string matchingParams = vm["matching"].as<string>();
		matcher = SampleFilter::make_filter("match", matchingParams);
	}

	// get vector of performance measurements 
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
	MedSamples allTestSamples;
	for (int idx = 0; idx < nOutSplit; idx++) {
		int iFold = folds[idx];
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

		// Partial learning and application
		model.learn(rep, &iTrainSamples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
		MedFeatures trainFeatures = model.features;
		model.apply(rep, iTestSamples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_PROCESSORS);
		MedFeatures testFeatures = model.features;

		// Loop on options, complete learning and apply
		for (int iOption = 0; iOption < predictorOptions.size(); iOption++) {
			model.predictor->set_params(predictorOptions[iOption]);

			model.features = trainFeatures;
			model.learn(rep, &iTrainSamples, MED_MDL_LEARN_PREDICTOR, MED_MDL_END);

			model.features = testFeatures;
			model.apply(rep, iTestSamples, MED_MDL_APPLY_PREDICTOR, MED_MDL_END);


			// Performance
			vector<vector<float> > tmp_prfs;
			get_performance(iTestSamples, msrs, tmp_prfs);
			for (int iMsr = 0; iMsr < msrs.size(); iMsr++) {
				all_prfs[idx][iOption][iMsr] = tmp_prfs[iMsr][1];

				// Debug print
				cerr << "PERFOFMANCE\t" << iOption << "\t" << iFold << "\t" << iMsr << "\t";
				for (auto& rec : predictorOptions[iOption]) cerr << rec.first << "=" << rec.second << "\t";
				cerr << tmp_prfs[iMsr][1] << "\n";
			}

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
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("samples", po::value<string>()->required(), "training samples")
			("test_samples", po::value<string>(), "optional parallel test samples (use training samples if not given)")
			("inModel", po::value<string>()->required(), "model json file")
			("predictorParamsFile", po::value<string>()->required(), "file with possible options for parameters")
			("nPredictorRuns", po::value<int>(), "optional number of parameters combinations to check")
			("matching", po::value<string>(), "optional matching parameters")
			("out", po::value<string>(), "performance output file")
			("inpatient", "indicate that relevant data is in-patient data")
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
