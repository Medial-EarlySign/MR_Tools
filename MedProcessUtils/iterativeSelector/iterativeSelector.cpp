// Wrapper (iterative) feature selection

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "iterativeSelector.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

void fit_to_mem_size(MedModel &model, MedSamples &samples) {
	int max_smp = model.get_apply_batch_count();
	int sz = samples.nSamples();
	if (sz > max_smp) {
		MWARN("WARN:: Too Many samples (%d) - down sampling to %d...\n", sz, max_smp);
		medial::process::down_sample_by_pid(samples, max_smp);
		MLOG("Done Down sampling\n");
	}
}

int main(int argc, char *argv[])
{

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	int seed = vm["seed"].as<int>();
	globalRNG::srand(seed);
	srand(seed);

	// In/Out patients
	if (vm.count("inpatient")) {
		MLOG("Working on in-patient data\n");
		global_default_time_unit = global_default_windows_time_unit = MedTime::Minutes;
	}

	// Sanity
	if (vm.count("inSamples") + vm.count("inCsv") + vm.count("inBin") != 1)
		MTHROW_AND_ERR("Either samples, csv or bin input must be given");

	string mode = vm["mode"].as<string>();
	if (mode != "top2bottom" && mode != "bottom2top")
		MTHROW_AND_ERR("Illegal mode - \'%s\'\n", mode.c_str());

	// Read and Run
	if (!vm.count("inSamples")) {
		MLOG("Reading Features\n");

		MedFeatures inFeatures;
		readMatrix(inFeatures, vm);
		runSelection(inFeatures, vm);
	}
	else {
		if (vm.count("inModel") + vm.count("inJson") != 1)
			MTHROW_AND_ERR("Either inModel or inJson must be given with inSamples\n");
		if (!vm.count("rep"))
			MTHROW_AND_ERR("rep must be given with inSamples\n");

		MedModel model;

		// Read Model (json)
		MLOG("Reading model\n'");

		bool doLearning;
		if (vm.count("inModel")) {
			string modelFile = vm["inModel"].as<string>();
			if (model.read_from_file(modelFile) != 0)
				MTHROW_AND_ERR("Reading model from \'%s\' failed\n", modelFile.c_str());
			doLearning = false;
		}
		else {
			string modelFile = vm["inJson"].as<string>();
			model.init_from_json_file(modelFile);
			doLearning = true;
		}

		// Read Sampels
		cerr << "Reading samples" << endl;
		string samplesFile = vm["inSamples"].as<string>();
		MedSamples samples;
		if (samples.read_from_file(samplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

		MLOG("Getting ids\n");
		vector<int> ids;
		samples.get_ids(ids);

		// Read Repository
		MedPidRepository rep;
		string configFile = vm["rep"].as<string>();
		bool allow_rep_change = vm["rep_change"].as<bool>();
		model.load_repository(configFile, ids, rep, doLearning || allow_rep_change);

		fit_to_mem_size(model, samples);
		// Get Features
		if (doLearning)
			model.learn(rep, &samples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
		else
			model.apply(rep, samples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_PROCESSORS);

		MLOG("Done preparing matrix from model\n");
		runSelection(model.features, vm);
	}

	return 0;
}

void runSelection(MedFeatures& features, po::variables_map& vm) {

	// Required
	set<string> required;
	if (vm.count("required")) {
		string req = vm["required"].as<string>();
		boost::split(required, req, boost::is_any_of(","));
	}
	int numToSelect = (int)required.size() + vm["numToSelect"].as<int>();


	// Perform initial univariate selection
	if (vm.count("univariate_nfeatures")) {
		string initializer = vm["univariate_params"].as<string>() + ";numToSelect=" + to_string(vm["univariate_nfeatures"].as<int>()) + ";required=" + vm["req"].as<string>();
		adjusted_univariate_slection(features, required, initializer);
	}

	// define iterative slector
	IterativeFeatureSelector selector;
	string init_string;
	if (vm.count("selector_params"))
		init_string = vm["selector_params"].as<string>();
	else {
		// Predictor
		init_string = "predictor=" + vm["predictor"].as<string>();
		if (vm.count("predictor_params"))
			init_string += ";predictor_params={" + vm["predictor_params"].as<string>() + "}";
		// Key -> Values
		for (string field : {"predictor_params_file", "do_internal_cv", "nfolds", "folds", "mode", "rates", "msr_params", "bootstrap_params", "cohort_params"}) {
			if (vm.count(field))
				init_string += ";" + field + "=" + vm[field].as<string>();
		}

		// Required + Ignored
		unordered_set<string> required, ignored;
		if (vm.count("required"))
			boost::split(required, vm["required"].as<string>(), boost::is_any_of(","));
		if (vm.count("ignored"))
			boost::split(ignored, vm["ignored"].as<string>(), boost::is_any_of(","));
		if (vm.count("required_file"))
			add_features_from_file(required, vm["required_file"].as<string>());
		if (vm.count("ignored_file"))
			add_features_from_file(ignored, vm["ignored_file"].as<string>());

		if (!required.empty())
			init_string += ";required=" + boost::join(required, ",");
		if (!ignored.empty())
			init_string += ";ignored=" + boost::join(ignored, ",");

		// Additional
		init_string += ";work_on_sets=" + to_string(vm["work_on_ftrs"].as<bool>() ? 0 : 1);
		init_string += ";verbose=" + to_string(vm["verbose"].as<bool>() ? 1 : 0);
		init_string += ";numToSelect=" + to_string(numToSelect);
		if (vm.count("ungrouped") > 0)
			init_string += ";ungrouped=" + vm["ungrouped"].as<string>();
		if (vm.count("group_to_sigs") > 0)
			init_string += ";group_to_sigs=" + to_string(vm["group_to_sigs"].as<bool>() ? 1 : 0);
		if (vm.count("group_mode") > 0)
			init_string += ";grouping_mode=" + vm["group_mode"].as<string>();
		if (vm.count("progress_file_path") > 0)
			init_string += ";progress_file_path=" + vm["progress_file_path"].as<string>();

		MLOG("init_string : %s\n", init_string.c_str());
	}

	selector.init_from_string(init_string);

	if ((vm.count("retrace_in") == 0) && ((vm.count("retrace_string") == 0))) {
		// Select
		selector.learn(features);
	}
	else {
		// Retrace
		vector<string> retracedFamilies;
		if (vm.count("retrace_in") > 0)
		{
			string retraceFile = vm["retrace_in"].as<string>();
			string mode = vm["mode"].as<string>();
			read_retrace_info(retraceFile, mode, retracedFamilies);
		}
		if (vm.count("retrace_string") > 0)
		{
			boost::split(retracedFamilies, vm["retrace_string"].as<string>(), boost::is_any_of(","));
		}
		int start = (vm.count("retrace_start")) ? vm["retrace_start"].as<int>() : 0;
		int end = (vm.count("retrace_end")) ? vm["retrace_end"].as<int>() : (int)retracedFamilies.size() - 1;
		if (start < 0 || end >= retracedFamilies.size())
			MTHROW_AND_ERR("Illegal tracing range [%d,%d] for %d families \n", start, end, (int)retracedFamilies.size());

		selector.retrace(features, retracedFamilies, start, end);
	}
	// print
	string outFile = vm["out"].as<string>();
	selector.print_report(outFile);
	MLOG("Saved: %s\n", outFile.c_str());
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("inCsv", po::value<string>(), "input matrix as csv file")
			("inBin", po::value<string>(), "input matrix as bin file")
			("inSamples", po::value<string>(), "input samples")
			("inModel", po::value<string>(), "bin model for generating matrix from samples")
			("inJson", po::value<string>(), "json model for generating matrix from samples")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("out", po::value<string>()->required(), "output file")

			("predictor", po::value<string>()->required(), "predictor type")
			("predictor_params", po::value<string>(), "predictor parameters")
			("predictor_params_file", po::value<string>(), "input predictor parameters file - if exists, override predictor parameters")
			("nfolds", po::value<string>(), "if given, replace given splits with rand()%nfolds")
			("folds", po::value<string>(), "comma-separated list of folds to actually take for test. If not given - take all")
			("mode", po::value<string>()->default_value("top2bottom"), "directions of selection (top2bottom/bottom2top)")
			("rates", po::value<string>()->default_value("50:1,100:2,500:5,5000:10"), "instruction on rate of selection - comma separated pairs : #-bound:step")
			("msr_params", po::value<string>()->required(), "performance measurement (AUC, or SENS,FPR,0.2 for SENS@FPR=20%, etc.")
			("bootstrap_params", po::value<string>(), "bootstrap parameters")
			("cohort_params", po::value<string>(), "bootstrap cohort parameters")
			("univariate_nfeatures", po::value<int>(), "number of features to select in an initial univariate selector stage")
			("univariate_params", po::value<string>()->default_value("method=mi"), "univariate selector parameters")
			("required", po::value<string>(), "comma-separated list of required features")
			("required_file", po::value<string>(), "file with list of required features")
			("ignored", po::value<string>(), "comma-separated list of ignored features")
			("ignored_file", po::value<string>(), "file with list of ignored features")
			("work_on_ftrs", po::value<bool>()->default_value(false), "if true - work on features, if false, work on signals")
			("verbose", po::value<bool>()->default_value(true), "verbosity flag")
			("selector_params", po::value<string>(), "if given, overwrite all other parmeters to iterative selector")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
			("rep_change", po::value<bool>()->default_value(false), "If true will allow adjustment to rep in apply")
			("ungrouped", po::value<string>()->default_value("RC,Drug,ICD9,ADMISSION,VISIT"), "name of ungrouped features")
			("group_to_sigs", po::value<bool>()->default_value(false), "If true will group into sigs like RC and not just thier specific categories")
			("group_mode", po::value<string>()->default_value("BY_SIGNAL_CATEG"), "The grouping of feature parameter.can be a file or keyword like BY_SIGNAL_CATEG")
			("inpatient", "indicate that relevant data is in-patient data")
			("do_internal_cv", po::value<string>(), "if true - the iterative selector creates new splits. If false uses original splits")
			("progress_file_path", po::value<string>(), "file path to log progress")
			("numToSelect", po::value<int>()->default_value(0), "stop criteria of number of additional groups beyond required")

			// Read output file of another run and range of indices and rerun the cross-validations 
			("retrace_in", po::value<string>(), "output file of previous run to be used as input for retun")
			("retrace_string", po::value<string>(), "comma delimited features or signals for retrace")
			("retrace_start", po::value<int>(), "index to start retracing")
			("retrace_end", po::value<int>(), "index to start retracing")
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

// Linearly adjusted univariate selection
void adjusted_univariate_slection(MedFeatures& features, set<string>& required, string& initializer) {

	cerr << "Performing adjusted univariate feature selector ...";

	// Linear model based on required signals only
	MedPredictor *lm = MedPredictor::make_predictor("linear_model", "rfactor=0.99");

	MedMat<float> matrix;
	vector<string> required_v;
	for (string req : required)
		required_v.push_back(req);
	features.get_as_matrix(matrix, required_v);

	vector<float> labels(features.samples.size());
	for (int i = 0; i < labels.size(); i++)
		labels[i] = features.samples[i].outcome;

	lm->learn(matrix, labels);

	vector<float> preds;
	features.get_as_matrix(matrix, required_v);
	lm->predict(matrix, preds);

	// Univariate selector based on residual labels
	for (int i = 0; i < labels.size(); i++)
		features.samples[i].outcome -= preds[i];

	FeatureProcessor *selector = FeatureProcessor::make_processor("univariate_selector", initializer);

	selector->learn(features);
	selector->apply(features);

	for (int i = 0; i < labels.size(); i++)
		features.samples[i].outcome = labels[i];

	cerr << " left with " << features.data.size() << " features\n";
}

// Add features from file
void add_features_from_file(unordered_set<string>& list, string file) {

	vector<string> tokens;
	medial::io::read_codes_file(file, tokens);
	for (string& token : tokens)
		list.insert(token);
}

// Read families from output file
void read_retrace_info(string& fileName, string& mode, vector<string>& families) {

	ifstream inf(fileName);
	if (!inf.is_open())
		MTHROW_AND_ERR("Cannot open %s for reading\n", fileName.c_str());

	string line;
	string word = (mode == "top2bottom") ? "Removing" : "Adding";

	while (getline(inf, line)) {
		boost::trim(line);
		if (line.empty())
			continue;
		vector<string> words;
		boost::split(words, line, boost::is_any_of(","));
		if (words[0] == "word" && words[2] == "family")
			families.push_back(words[3]);
	}

	inf.close();
}
