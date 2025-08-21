// Perform analyses on model

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "analyze_model.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	global_logger.init_level(LOG_MEDALGO, 6);

	// Initialize  
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// Analyze
	string analysis = vm["analysis"].as<string>();
	if (analysis == "contribs") {
		analyze_contributions(vm);
	}
	else
		MTHROW_AND_ERR("Unknown analysis: %s\n", analysis.c_str());

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("model", po::value<string>()->required(), "model to analyze")
			("samples", po::value<string>(), "sampels to use in analysis")
			("rep", po::value<string>(), "repository to use in analysis")
			("analysis", po::value<string>()->required(), "analysis to perform (option: contribs)")
			("features", po::value<string>(), "comma-separated list of features to analyze in analysis=contribs")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
			("contribs", po::value<string>(), "optional contributions matrix input/output file")
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

// Analyze Contributions
void analyze_contributions(po::variables_map& vm) {

	// Get Predictions
	// Check required paramters
	string samplesFile, repFile;
	if (vm.count("samples"))
		samplesFile = vm["samples"].as<string>();
	else
		MTHROW_AND_ERR("Samples required for analysis=contrib\n");

	if (vm.count("rep"))
		repFile = vm["rep"].as<string>();
	else
		MTHROW_AND_ERR("Rep required for analysis=contrib\n");

	// Read
	string modelFile = vm["model"].as<string>();
	MedModel model;
	if (model.read_from_file(modelFile) != 0)
		MTHROW_AND_ERR("Cannot read model from file \'%s\'\n", modelFile.c_str());

	MedPidRepository rep;
	model.load_repository(repFile, rep);

	MedSamples samples;
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file \'%s\'\n", samplesFile.c_str());

	// Get Matrix + predictions
	model.apply(rep, samples);
	MedMat<float> matrix;
	model.features.get_as_matrix(matrix);

	// Data
	MedMat<float> contributions;
	vector<string> features_v;

	// Read/Calculate contributions
	string contribsFile = (vm.count("contribs") > 0) ? vm["contribs"].as<string>() : "";
	struct stat buffer;
	if (contribsFile != "" && stat(contribsFile.c_str(), &buffer) == 0) {
		if (contributions.read_from_bin_file(contribsFile) != 0)
			MTHROW_AND_ERR("Cannot read binary file \'%s\'\n", contribsFile.c_str());
		features_v = contributions.signals;
	}
	else {
		// Get contributions matrix
		model.predictor->calc_feature_contribs(matrix, contributions);
		model.features.get_feature_names(features_v);

		// Write to file if required
		if (contribsFile != "") {
			contributions.signals = features_v;
			contributions.write_to_bin_file(contribsFile);
		}
	}

	// Select subset, if required	
	vector<int> features;

	if (vm.count("features")) {
		vector<string> in_features;
		boost::split(in_features, vm["features"].as<string>(), boost::is_any_of(","));
		for (string ftr : in_features)
			features.push_back(find_in_feature_names(features_v, ftr));
	}
	else {
		for (int i = 0; i < (int)features_v.size(); i++)
			features.push_back(i);
	}

	// Print contributions + values + predictions
	cout << "irow\tfeature\tvalue\tcontrib\tsum\tpred\n";
	for (int irow = 0; irow < contributions.nrows; irow++) {
		double pred = model.features.samples[irow].prediction[0];
		double sum = 0.0;
		for (int icol = 0; icol < contributions.ncols; icol++)
			sum += contributions(irow, icol);
		for (int icol : features) {
			double value = model.features.data[features_v[icol]][irow];
			double contrib = contributions(irow, icol);
			cout << irow << "\t" << features_v[icol] << "\t" << value << "\t" << contrib << "\t" << sum << "\t" <<  pred << "\n";
		}
	}

	

}
