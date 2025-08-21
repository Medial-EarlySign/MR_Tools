// Learn a calibrator

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "apply_calibrator.h"
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
	if (vm.count("outSamples") + vm.count("outTable") != 1)
		MTHROW_AND_ERR("Exactly one output mode allowed");

	// Read samples
	cerr << "Reading Samples" << endl;
	MedSamples samples;
	string samplesFile = vm["inSamples"].as<string>();
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	// Readclibrator
	Calibrator cal;
	string calFile = vm["calibrator"].as<string>();
	cal.read_from_file(calFile);

	// Output
	if (vm.count("outSamples")) {
		cal.Apply(samples);
		string outSamplesFile = vm["outSamples"].as<string>();
		if (samples.write_to_file(outSamplesFile) != 0)
			MTHROW_AND_ERR("Cannot write samples to file %s", samplesFile.c_str());
	}

	// Comparison
	if (vm.count("outTable")) {
		string estimator_type = cal.estimator_type;
		cal.estimator_type = "bin";
		cal.Apply(samples);
		cal.estimator_type = estimator_type;

		string outTableFile = vm["outTable"].as<string>();
		if (cal.calibration_type == probability_time_window)
			compare_probability_time_window(cal, samples, outTableFile);
		else
			MTHROW_AND_ERR("compare not implemented for calibration type %d\n", cal.calibration_type);
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("inSamples", po::value<string>()->required(), "input samples")
			("outSamples", po::value<string>(), "output samples")
			("calibrator", po::value<string>(), "input calibrator file")
			("outTable", po::value<string>(), "output table file")
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

void compare_probability_time_window(Calibrator& cal, MedSamples& samples, string& outTableFile) {

	cal.binning_method = "unique_score_per_bin";
	cal.do_calibration_smoothing = 0;
	cal.Learn(samples);
	cal.write_calibration_table(outTableFile);
}
