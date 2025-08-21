// Calibrate scores using cross-validation

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "cv_calibration.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// Read data
	vector<MedSample> samples;
	string inFile = vm["input"].as<string>();
	
	string header;
	int nAttr = read_input_data(inFile, samples, header);

	// Split
	int nFolds = vm["nfolds"].as<int>();
	for (MedSample& sample : samples)
		sample.split = globalRNG::rand() % nFolds;

	// Loop - learn calibrator and apply
	string calInit = vm["calibrator"].as<string>();
	for (int iFold = 0; iFold < nFolds; iFold++) {
		MedSamples learningSamples, testSamples;
		split_samples(samples, learningSamples, testSamples, iFold);

		Calibrator cal;
		cal.init_from_string(calInit);
		cal.Learn(learningSamples);
		cal.Apply(testSamples);

		add_calibrated_scores(testSamples, samples, iFold);
	}

	// Write data
	string outFile = vm["output"].as<string>();
	write_output_data(outFile, samples, nAttr, header);

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("input", po::value<string>()->required(), "input file (col,col,col,....,score,outcome")
			("output", po::value<string>()->required(), "output file (col,col,col,....,score,outcome,calibrated-score")
			("nfolds", po::value<int>()->default_value(5), "number of folds for cross validation")
			("calibrator", po::value<string>()->default_value("calibration_type=isotonic_regression;n_top_controls=5;n_bottom_cases=2"), "calibrator initialization string")
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


// Split samples to learning and test set according to split
void split_samples(vector<MedSample>& samples, MedSamples& learningSamples, MedSamples& testSampels, int iFold) {

	vector<MedSample> learningSamplesVec, testSamplesVec;
	for (MedSample& sample : samples) {
		if (sample.split == iFold)
			testSamplesVec.push_back(sample);
		else
			learningSamplesVec.push_back(sample);
	}

	learningSamples.import_from_sample_vec(learningSamplesVec);
	testSampels.import_from_sample_vec(testSamplesVec);
}

// Add calibrated score as an extra prediction
void add_calibrated_scores(MedSamples& testSamples, vector<MedSample>& samples, int iFold) {

	vector<MedSample> testSamplesVec;
	testSamples.export_to_sample_vec(testSamplesVec);

	int idx = 0;
	for (MedSample& sample :  samples) {
		if (sample.split == iFold)
			sample.prediction.push_back(testSamplesVec[idx++].prediction[0]);
	}
}



