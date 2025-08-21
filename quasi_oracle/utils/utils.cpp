// utilities

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "utils.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

	int rc = 0;
	globalRNG::srand(12131415);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	// Do it
	string mode = vm["mode"].as<string>();
	if (mode == "attr2ftr")
		attr2ftr(vm);
	else
		MTHROW_AND_ERR("Unknown mode: \'%s\'\n", mode.c_str());

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	char* pPath;
	pPath = getenv("MR_ROOT");
	if (pPath == NULL)
		MTHROW_AND_ERR("The current MR_ROOT is not available ");

	try {
		desc.add_options()
			("help", "produce help message")
			("mode", po::value<string>()->required(), "mode: attr2ftr")
			("in", po::value<string>(), "input bin matrix file")
			("out", po::value<string>(), "output bin matrix file")
			("name", po::value<string>(), "attr/feature name");

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

// Create a feature from an attribute
void attr2ftr(po::variables_map& vm) {

	if (!(vm.count("in") && vm.count("out") && vm.count("name")))
		MTHROW_AND_ERR("Required parameters for mode attr2ftr: in,out,name\n");

	string inFile = vm["in"].as<string>();
	string outFile = vm["out"].as<string>();
	string name = vm["name"].as<string>();


	MedFeatures matrix;
	if (matrix.read_from_file(inFile) < 0)
		MTHROW_AND_ERR("Cannot read matrix from %s\n", inFile.c_str());

	if (matrix.data.find(name) != matrix.data.end())
		MTHROW_AND_ERR("Feature named \'%s\' already exists in matrix\n", name.c_str());

	int nSamples = (int) matrix.samples.size();
	matrix.data[name].resize(nSamples);
	for (int i = 0; i < nSamples; i++) {
		if (matrix.samples[i].attributes.find(name) == matrix.samples[i].attributes.end())
			MTHROW_AND_ERR("Cannot find attribute \'%s\' for sample #%d\n", name.c_str(), i);
		matrix.data[name][i] = matrix.samples[i].attributes[name];
		matrix.samples[i].attributes.erase(name);
	}

	if (matrix.write_to_file(outFile) < 0)
		MTHROW_AND_ERR("Cannot write matrix to %s\n", outFile.c_str());

	return;
}

