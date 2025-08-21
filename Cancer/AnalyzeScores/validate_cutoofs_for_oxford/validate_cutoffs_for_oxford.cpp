#define _CRT_SECURE_NO_WARNINGS
#include "validate_cutoffs_for_oxford.h"

/*			Main			*/

int main(int argc, char *argv[]) {

	// Read Parameters
	po::variables_map vm;

	assert(read_run_params_for_oxford(argc, argv, vm) != -1);

	// Initialize random numbers
	globalRNG::srand(vm["seed"].as<int>());
	quick_random qrand;

	// Read data
	input_data indata;
	assert(read_all_validation_input_data_for_oxford(vm, indata) != -1);


	// Open output file
	FILE *fout = fopen(vm["out"].as<string>().c_str(), "w");
	if (fout == NULL) {
		fprintf(stderr, "Could not open outuput file \'%s\' for writing\n", vm["out"].as<string>().c_str());
		return -1;
	}

	string auto_name = vm["out"].as<string>() + ".Autosim";
	FILE *fout_sim = fopen(auto_name.c_str(), "w");
	if (fout_sim == NULL) {
		fprintf(stderr, "Could not open outuput file \'%s\' for writing\n", auto_name.c_str());
		return -1;
	}


	// Allocate.
	work_space work;
	assert(allocate_data(indata, work) != -1);

	// Check performance
	int nbootstrap = vm["nbootstrap"].as<int>();
	assert(validate_bounds(indata, work, fout, nbootstrap, qrand) != -1);
	assert(validate_bounds_autosim(indata, work, fout_sim, nbootstrap, qrand) != -1);

	return 0;
}

// Functions
int read_run_params_for_oxford(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("in", po::value<string>()->required(), "input file")
			("params", po::value<string>()->required(), "file specifying time windows, age groups, and last date")
			("out", po::value<string>()->required(), "output file name")
			("bnds", po::value<string>()->required(), "bounds file")
			("seed", po::value<int>()->default_value(1234), "seed for randomizations")
			("nbootstrap", po::value<int>()->default_value(500), "number of bootstrap samples")
			("first_date", po::value<int>()->required(), "first date for which cancer data is reliable")
			("last_date", po::value<int>()->required(), "last date for which cancer/censor data is available")
			("gender", po::value<string>()->required(), "Gender: M/F/C")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}

	return 0;
}

int read_all_validation_input_data_for_oxford(po::variables_map& vm, input_data& indata) {

	// Read bounds file
	if (read_bnds(vm["bnds"].as<string>().c_str(), indata.bnds, indata.bnds_autosim) == -1) {
		fprintf(stderr, "Could not read bounds from file \'%s\'\n", vm["bnds"].as<string>().c_str());
		return -1;
	}

	return read_all_input_data_for_oxford(vm, indata);
}