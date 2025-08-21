// Learn a calibrator

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "learn_calibrator.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

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

	// Sanity
	if (! (vm.count("calibrator") || vm.count("table")))
		MTHROW_AND_ERR("No output mode given. quitting");

	cerr << "Reading Samples" << endl;
	MedSamples samples;
	string samplesFile = vm["samples"].as<string>();
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	// Get clibrator
	Calibrator cal;
	string init_string = vm["params"].as<string>();
	cal.init_from_string(init_string);
	cal.Learn(samples);

	// Output
	if (vm.count("calibrator")) {
		string outFile = vm["calibrator"].as<string>();
		cal.write_to_file(outFile);
	}

	if (vm.count("table")) {
		string outFile = vm["table"].as<string>();
		cal.write_calibration_table(outFile);
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("samples", po::value<string>()->required(), "input samples")
			("params", po::value<string>()->required(), "calibrator params")
			("calibrator", po::value<string>(), "output calibrator file")
			("table", po::value<string>(), "output calibrator table")
			("inpatient", "indicate that relevant data is in-patient data")
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
