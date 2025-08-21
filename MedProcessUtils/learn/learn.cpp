// Learn a model

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "learn.h"
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

	// In/Out patients
	if (vm.count("inpatient")) {
		MLOG("Working on in-patient data\n");
		global_default_time_unit = global_default_windows_time_unit =  MedTime::Minutes;
	}

	string configFile = vm["rep"].as<string>();
	string samplesFile = vm["samples"].as<string>();
	string inModel = vm["inModel"].as<string>();
	string outModel = vm["outModel"].as<string>();
	
	// Read Model json
	cerr << "Reading model" << endl;
	MedModel model;
	vector<string> jsonAlts;
	if (vm.count("json_alt"))
		for (string alt : vm["json_alt"].as<vector<string>>())
			jsonAlts.push_back(alt);
	model.init_from_json_file_with_alterations(inModel, jsonAlts);

	// Read Samples
	cerr << "Reading samples" << endl;
	MedSamples samples;
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	// Additional post-processors samples ?
	vector<MedSamples> pp_samples;
	if (vm.count("pp_samples")) {
		vector<string> files;
		string list = vm["pp_samples"].as<string>();
		boost::split(files, list, boost::is_any_of(","));

		pp_samples.resize(files.size());
		for (unsigned int i = 0; i < files.size(); i++) {
			if (pp_samples[i].read_from_file(files[i]) != 0)
				MTHROW_AND_ERR("Cannot read samples from file %s", files[i].c_str());
		}
	}

	cerr << "Getting ids" << endl;
	vector<int> ids;
	samples.get_ids(ids);

	// Add ids from pp_samples. Check lists are not overlapping
	if (pp_samples.size() > 0) {
		for (MedSamples& _samples : pp_samples) {
			vector<int> _ids;
			_samples.get_ids(_ids);
			ids.insert(ids.end(), _ids.begin(), _ids.end());
		}

		// Sort
		sort(ids.begin(), ids.end());

		// Check non-overlap
		for (unsigned int i = 1; i < ids.size(); i++) {
			if (ids[i] == ids[i - 1])
				MTHROW_AND_ERR("id %d found in more than one sampels file. Quitting", ids[i]);
		}
	}
	
	// Read Repository
	MedPidRepository rep;
	model.load_repository(configFile, ids, rep, true);

	// Match model learning set
	if (vm.count("matching")) {
		string matchingParams = vm["matching"].as<string>();
		SampleFilter *matcher = SampleFilter::make_filter("match", matchingParams);
		matcher->filter(rep, samples);
	}

	// Learn
	string end_stage_s = vm["end_stage"].as<string>();
	MedModelStage end_stage = MedModel::get_med_model_stage(end_stage_s);
	cerr << "Learning" << endl;
	model.learn(rep, samples, pp_samples, MED_MDL_LEARN_REP_PROCESSORS, end_stage);

	// Write to file
	cerr << "Saving" << endl;
	if (model.write_to_file(outModel) != 0)
		MTHROW_AND_ERR("Cannot write model to bin file %s\n", outModel.c_str());

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("matching",po::value<string>(),"optional matching parameters")
			("samples",po::value<string>()->required(),"training samples")
			("pp_samples", po::value<string>(), "optional comma-separated list of sample files for post-processors learning")
			("inModel", po::value<string>()->required(), "model json file")
			("json_alt", po::value<vector<string>>()->composing(), "(multiple) alterations to model json file")
			("outModel", po::value<string>()->required(), "model output file")
			("end_stage", po::value<string>()->default_value("end"), "end stage of learning")
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
