// Learn a model starting from a matrix

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "predict_on_matrix.h"
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
	if (vm.count("model") + vm.count("predictor") != 1)
		MTHROW_AND_ERR("Either model or predictor must be given");

	// Input options
	if (vm.count("model")) {
		string changesJson = vm["modelChanges"].as<string>();

		// Read Model
		cerr << "Reading Model " << endl;
		MedModel model;
		string modelFile = vm["model"].as<string>();
		model.read_from_file_with_changes(modelFile, changesJson);

		// Read Features
		cerr << "Reading Features" << endl;
		readMatrix(model.features, vm);

		// Apply
		cerr << "Applying" << endl;
		MedPidRepository dummyRep;
		MedSamples samples;

		string end_stage_s = vm["end_stage"].as<string>();
		MedModelStage start_stage = (vm.count("no_process") > 0) ? MED_MDL_APPLY_PREDICTOR : MED_MDL_APPLY_FTR_PROCESSORS;
		MedModelStage end_stage = MedModel::get_med_model_stage(end_stage_s);

		model.features.get_samples(samples);
		model.apply(dummyRep, samples, start_stage, end_stage);

		// Write to samples file
		cerr << "Writing" << endl;
		writePredictions(model.features, vm);
	
	}
	else {

		// Read predictor
		cerr << "Reading Predictor" << endl;
		string predictorFile = vm["predictor"].as<string>();
		MedPredictor *pred;
		read_predictor_from_file(pred, predictorFile);

		// Read Features
		cerr << "Reading Features" << endl;
		MedFeatures features;
		readMatrix(features, vm);

		// Apply
		cerr << "Predicting" << endl;
		pred->predict(features);
		// Write to samples file
		cerr << "Writing" << endl;
		writePredictions(features, vm);
	}



	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("predictor", po::value<string>(), "predictor file")
			("model", po::value<string>(), "model file")
			("modelChanges", po::value<string>()->default_value(""), "optional changes to binary model (json file)")
			("inCsv", po::value<string>(), "input matrix as csv file")
			("inBin", po::value<string>(), "input matrix as bin file")
			("outSamples", po::value<string>(), "predictions output file as samples")
			("outCsv", po::value<string>(), "predictions output file as csv matrix")
			("outBin", po::value<string>(), "predictions output file as binary matrix")
			("end_stage", po::value<string>()->default_value("end"), "end stage of apply")
			("no_process", "skeep processing stage and apply predictor on matrix as is")
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