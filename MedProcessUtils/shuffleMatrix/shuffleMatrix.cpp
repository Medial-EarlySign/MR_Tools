// Shuffle a matrix (csv/bin -> csv/bin)

#include "shuffleMatrix.h"
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

	if (vm.count("outCsv") + vm.count("outBin") == 0)
		MTHROW_AND_ERR("At least one of OutCsv and OutBin should be given\n");

	// Read 
	MedFeatures matrix;
	readMatrix(matrix, vm);

	// Shuffle
	cerr << "Shuffling" << endl;
	shuffleMatrix(matrix);


	// Write to file
	cerr << "Saving" << endl;
	if (vm.count("outCsv")) {
		string fileName = vm["outCsv"].as<string>();
		if (matrix.write_as_csv_mat(fileName) != 0)
			MTHROW_AND_ERR("Cannot write matrix to csv file %s\n", fileName.c_str());
	}

	if (vm.count("outBin")) {
		string fileName = vm["outBin"].as<string>();
		if (matrix.write_to_file(fileName) != 0)
			MTHROW_AND_ERR("Cannot write matrix to bin file %s\n", fileName.c_str());
	}
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("inCsv", po::value<string>(), "input csv matrix file")
			("inBin", po::value<string>(), "input bin matrix file")
			("outCsv", po::value<string>(), "output csv matrix file")
			("outBin", po::value<string>(), "output bin matrix file")
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

