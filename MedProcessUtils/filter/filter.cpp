// Filter a samples set

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "filter.h"
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
		global_default_time_unit = global_default_windows_time_unit = MedTime::Minutes;
	}

	// Sanity
	if (vm.count("filterModel") && (vm.count("filter") || vm.count("filterParams")))
		MTHROW_AND_ERR("Either filterModel or filter+filterParams must be given");

	// Input options
	MedSamples samples;

	if (!(vm.count("filter") && vm.count("filterParams")))
		MTHROW_AND_ERR("Both filter and filterParams must be given");


	// Initialize filter
	cerr << "Initializing filter" << endl;
	string filterType = vm["filter"].as<string>();
	string filterParams = vm["filterParams"].as<string>();
	SampleFilter *filter = SampleFilter::make_filter(filterType, filterParams);

	// Read Samples
	cerr << "Reading Samples" << endl;
	string samplesFile = vm["inSamples"].as<string>();
	if (samples.read_from_file(samplesFile) != 0)
		MTHROW_AND_ERR("Cannot read samples from file %s", samplesFile.c_str());

	if (vm.count("json") == 0) {
		//	Mode without model

		// Read repository
		MedPidRepository rep;
		if (vm.count("rep")) {
			cerr << "Reading Repository" << endl;
			vector<string> signalNames;
			filter->get_required_signals(signalNames);

			if (signalNames.empty())
				MLOG("No signals required from repository\n");
			else {
				vector<int> ids;
				samples.get_ids(ids);

				string configFile = vm["rep"].as<string>();
				if (rep.read_all(configFile, ids, signalNames) != 0)
					MTHROW_AND_ERR("Read repository from %s failed\n", configFile.c_str());
			}
		}

		// Learn filter (possibly doing nothing)
		cerr << "Learning filter" << endl;
		filter->learn(rep, samples);

		// Apply filter
		cerr << "Applying filter" << endl;
		filter->filter(rep, samples);
	} 
	else {
		// Mode with model (only matcher)		
		if (!vm.count("rep"))
			MTHROW_AND_ERR("Repository needed when model given\n");

		if (filter->filter_type != SMPL_FILTER_MATCH)
			MTHROW_AND_ERR("Model applicable only for matching\n");

		// Read repository
		vector<string> signalNames;
		filter->get_required_signals(signalNames);
		
		string modelJson = vm["json"].as<string>();
		MedModel model;
		model.init_from_json_file(modelJson);

		vector<string> modelSignalNames;
		model.get_required_signal_names(modelSignalNames);

		unordered_set<string> allReqSignals_set;
		for (string& s : signalNames)
			allReqSignals_set.insert(s);
		for (string& s : modelSignalNames)
			allReqSignals_set.insert(s);
		vector<string> allReqSingals_vec(allReqSignals_set.begin(), allReqSignals_set.end());

		vector<int> ids;
		samples.get_ids(ids);

		MedPidRepository rep;
		string configFile = vm["rep"].as<string>();
		if (rep.read_all(configFile, ids, allReqSingals_vec) != 0)
			MTHROW_AND_ERR("Read repository from %s failed\n", configFile.c_str());

		// Learn Model
		model.learn(rep, samples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);

		// Match
		cerr << "Applying matcher" << endl;
		MatchingSampleFilter *matcher = dynamic_cast<MatchingSampleFilter*>(filter);
		MedSamples filtered;
		matcher->_filter(model.features, rep, samples, filtered);
		samples = filtered;

	}

	// Write to file  
	cerr << "Saving" << endl;
	string outSamplesFile = vm["outSamples"].as<string>();
	if (samples.write_to_file(outSamplesFile) != 0)
		MTHROW_AND_ERR("Cannot write model to bin file %s\n", outSamplesFile.c_str());


	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>(), "repository config file")
			("inSamples", po::value<string>()->required(), "input samples")
			("outSamples", po::value<string>()->required(), "output samples")
			("json", po::value<string>(), "json for generating feature for filtering")
			("filter", po::value<string>(), "filter type")
			("filterParams", po::value<string>(), "filter parameters string")
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
