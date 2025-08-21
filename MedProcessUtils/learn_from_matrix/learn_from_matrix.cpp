// Learn a model starting from a matrix

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "learn_from_matrix.h"
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

	// Sanity
	if (vm.count("model") && (vm.count("predictor") || vm.count("params")))
		MTHROW_AND_ERR("Either model or predictor+params must be given");

	// Input options
	if (vm.count("inModel")) {
		// Initialize predictor
		cerr << "Initializing" << endl;
		string modelFile = vm["inModel"].as<string>();
		
		// Read Model json
		MedModel model;
		vector<string> jsonAlts;
		if (vm.count("json_alt"))
			for (string alt : vm["json_alt"].as<vector<string>>())
				jsonAlts.push_back(alt);
		model.init_from_json_file_with_alterations(modelFile, jsonAlts);

		// Read Features
		cerr << "Reading" << endl;
		readMatrix(model.features, vm);

		// Learn
		cerr << "Learning" << endl;
		MedPidRepository dummyRep;
		MedSamples samples;

		string end_stage_s = vm["end_stage"].as<string>();
		MedModelStage end_stage = MedModel::get_med_model_stage(end_stage_s);
		model.features.get_samples(samples);
		model.learn(dummyRep, &samples, MED_MDL_LEARN_FTR_PROCESSORS, end_stage);

		// Write to file
		cerr << "Saving" << endl;
		string outFile = vm["out"].as<string>();
		if (model.write_to_file(outFile) != 0)
			MTHROW_AND_ERR("Cannot write model to binary file %s\n", outFile.c_str());
	}
	else {
		if (!(vm.count("predictor") && vm.count("params")))
			MTHROW_AND_ERR("Both predictor and params must be given");


		// Initialize predictor
		cerr << "Initializing Predictor" << endl;
		string predictorType = vm["predictor"].as<string>();
		string predictorParams = vm["params"].as<string>();
		MedPredictor *pred = MedPredictor::make_predictor(predictorType, predictorParams);

		// Read Features
		cerr << "Reading Features" << endl;
		MedFeatures features;
		readMatrix(features, vm);

		// Learn
		cerr << "Learning" << endl;
		pred->learn(features);

		// Write to file
		cerr << "Saving" << endl;
		string outFile = vm["out"].as<string>();
		write_predictor_to_file(pred, outFile);
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("predictor", po::value<string>(), "predictor type")
			("params", po::value<string>(), "predictor parameters")
			("inModel", po::value<string>(), "model json file")
			("json_alt", po::value<vector<string>>()->composing(), "(multiple) alterations to model json file")
			("inCsv", po::value<string>(), "input matrix as csv file")
			("inBin", po::value<string>(), "input matrix as bin file")
			("out", po::value<string>()->required(), "predictor/model output file")
			("end_stage", po::value<string>()->default_value("end"), "end stage of learning")
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

// Write Predictor to File
void write_predictor_to_file(MedPredictor *pred, string& outFile) {
	size_t predictor_size = pred->get_predictor_size();
	vector<unsigned char> buffer(predictor_size);
	pred->predictor_serialize(&(buffer[0]));

	if (write_binary_data(outFile, &(buffer[0]), predictor_size) != 0)
		MTHROW_AND_ERR("Error writing model to file %s\n", outFile.c_str());
}