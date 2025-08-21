// Apply a model

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "predict.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#include <MedUtils/MedUtils/MedGlobalRNG.h>

int main(int argc, char *argv[])
{

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// In/Out patients
	if (vm.count("inpatient")) {
		MLOG("Working on in-patient data\n");
		global_default_time_unit = global_default_windows_time_unit = MedTime::Minutes;
	}

	string configFile = vm["rep"].as<string>();
	string samplesFile = vm["samples"].as<string>();
	string inModel = vm["inModel"].as<string>();
	string outSamples = vm["outSamples"].as<string>();
	string changesJson = vm["modelChanges"].as<string>();

	// Read Model 
	cerr << "Reading model" << endl;
	MedModel model;
	model.read_from_file_with_changes(inModel, changesJson);
	if (vm.count("verbosity"))
		model.verbosity = vm["verbosity"].as<int>();

	// Add pre-processors
	if (vm.count("preProcessors")) {
		string jsonFile = vm["preProcessors"].as<string>();
		model.add_pre_processors_json_string_to_model("", jsonFile);
	}

	// Read Samples
	cerr << "Reading samples" << endl;
	MedSamples samples;
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	cerr << "Getting ids" << endl;
	vector<int> ids;
	samples.get_ids(ids);

	// Batches
	int batch_size = (vm.count("batch_size") > 0) ? vm["batch_size"].as<int>() : samples.nSamples();
	vector<int> batches = { 0 }, sizes;
	int count = 0;
	for (size_t i = 0; i < samples.idSamples.size(); i++) {
		count += (int)samples.idSamples[i].samples.size();
		if (count > batch_size) {
			sizes.push_back(count);
			batches.push_back(i);
			count = 0;
		}
	}
	if (count > 0) {
		sizes.push_back(count);
		batches.push_back((int)samples.idSamples.size());
	}

	MLOG("Will work on %d batches:", sizes.size());
	for (size_t i = 0; i < sizes.size(); i++)
		MLOG(" ids %d-%d (%d samples)", batches[i], batches[i + 1], sizes[i]);
	MLOG("\n");


	// Read Repository
	bool allow_fitting = (vm.count("allow_fitting") > 0);
	MedPidRepository rep;
	model.load_repository(configFile, ids, rep, allow_fitting);

	// Predict
	string end_stage_s = vm["end_stage"].as<string>();
	MedModelStage end_stage = MedModel::get_med_model_stage(end_stage_s);

	cerr << "Predicting" << endl;
	MedSamples predSamples;
	predSamples.time_unit = samples.time_unit;
	for (size_t i = 0; i < sizes.size(); i++) {
		MedSamples batchSamples;
		batchSamples.time_unit = samples.time_unit;
		batchSamples.idSamples.insert(batchSamples.idSamples.end(), samples.idSamples.begin() + batches[i], samples.idSamples.begin() + batches[i + 1]);
		model.apply(rep, batchSamples, MED_MDL_APPLY_FTR_GENERATORS, end_stage);
		predSamples.idSamples.insert(predSamples.idSamples.end(),batchSamples.idSamples.begin(), batchSamples.idSamples.end());
	}

	// Write to file
	cerr << "Saving" << endl;
	// Remove attributes if required
	if (vm.count("no_attr")) {
		for (MedIdSamples& idSamples : predSamples.idSamples) {
			for (MedSample& sample : idSamples.samples)
				sample.attributes.clear();
		}
	}
	if (predSamples.write_to_file(outSamples) != 0)
		MTHROW_AND_ERR("Cannot write predictinos to %s\n", outSamples.c_str());

	// Perfomance
	if (vm.count("outPerformance")) {
		string perforamcenFile = vm["outPerformance"].as<string>();
		int nSplits = predSamples.nSplits();
		print_auc_performance(predSamples, nSplits, perforamcenFile);
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("samples", po::value<string>()->required(), "test samples")
			("inModel", po::value<string>()->required(), "model file")
			("modelChanges", po::value<string>()->default_value(""), "optional changes to binary model (json file)")
			("outSamples", po::value<string>()->required(), "samples output file")
			("outPerformance", po::value<string>(), "optional performance file")
			("preProcessors", po::value<string>(), "optional pre-processors json file")
			("inpatient",  "indicate that relevant data is in-patient data")
			("end_stage", po::value<string>()->default_value("end"), "end stage of apply")
			("verbosity", po::value<int>(), "verbosity level")
			("batch_size", po::value<int>(), "batch size for predictions (no.of samples, rounded to ids)")
			("no_attr", "do not write attributes")
			("allow_fitting", "allow replacing input signals with virtual ones if not available")
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
