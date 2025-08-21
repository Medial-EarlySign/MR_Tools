// Print Repository data

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "printData.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	if (vm.count("modelJson") + vm.count("modelBin") > 1)
		MTHROW_AND_ERR("At most one model input allowed\n");

	string repFile = vm["rep"].as<string>();
	medial::repository::set_global_time_unit(repFile);

	// Get Signals
	vector<string> signals;
	if (vm.count("signals"))
		boost::split(signals, vm["signals"].as<string>(), boost::is_any_of(","));

	if (vm.count("signals_file")) {
		vector<string> _signals;
		medial::io::read_codes_file(vm["signals_file"].as<string>(), _signals);
		signals.insert(signals.end(), _signals.begin(), _signals.end());
	}

	// Get Ids
	vector<string> ids_s;
	if (vm.count("ids"))
		boost::split(ids_s, vm["ids"].as<string>(), boost::is_any_of(","));

	if (vm.count("ids_file")) {
		vector<string> _ids;
		medial::io::read_codes_file(vm["ids_file"].as<string>(), _ids);
		ids_s.insert(ids_s.end(), _ids.begin(), _ids.end());
	}

	vector<int> ids(ids_s.size());
	for (size_t i = 0; i < ids.size(); i++)
		ids[i] = stoi(ids_s[i]);

	MLOG("Reading %zd signals for %zd ids\n", signals.size(), ids.size());

	MedPidRepository rep; 
	if (vm.count("modelJson") + vm.count("modelBin") == 0) {
		// Simple mode - no model given
		get_rep(vm, ids, signals, NULL, rep);
		print_without_processing(rep, ids, signals);
	}
	else {
		// Read model and apply rep-processing before printing 
		MedModel model;
		int learn;
		get_model(vm, model, learn);

		get_rep(vm, ids, signals, &model, rep);
		print_with_processing(rep, model, ids, signals);
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
		("help", "produce help message")
		("rep", po::value<string>()->default_value(DEFAULT_REP), "repository configuration file")
		("signals_file", po::value<string>(), "file of signals to extract ")
		("signals", po::value<string>(), "comma-separated signals to extract")
		("ids_file", po::value<string>(), "file of ids to extract")
		("ids", po::value<string>(), "comma-separated ids to extract")
		("modelJson", po::value<string>(), "json for Rep-Processors to apply")
		("modelBin", po::value<string>(), "binary model for Rep-Processors to apply")
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

// printing without any rep-processing
void print_without_processing(MedPidRepository& rep, vector<int>& ids, vector<string>& signals) {

	// Get signal-ids
	vector<int> signal_ids;
	if (signals.empty()) {
		signal_ids = rep.index.signals;
		for (int id : signal_ids)
			signals.push_back(rep.sigs.name(id));
	}
	else {
		for (unsigned int i = 0; i < signals.size(); i++) {
			int sid = rep.sigs.sid(signals[i]);
			assert(sid >= 0);
			signal_ids.push_back(sid);
		}
	}

	MLOG("NIDS = %zd. NSIGS = %zd\n", rep.index.pids.size(), signal_ids.size());

	for (unsigned int i = 0; i < signal_ids.size(); i++) {
		for (unsigned j = 0; j < rep.index.pids.size(); j++) {
			UniversalSigVec usv;
			rep.uget(rep.index.pids[j], signal_ids[i], usv);
			vector<pair<vector<string>, vector<string>>> prtintable_usv;
			rep.convert_pid_sigs(usv, prtintable_usv, signals[i], signal_ids[i], 3);
			rep.print_pid_sig(rep.index.pids[j], signals[i], prtintable_usv);
		}
	}
}

void print_with_processing(MedPidRepository& rep, MedModel& model, vector<int>& ids, vector<string>& signals) {

	// init virtual signals
	if (model.collect_and_add_virtual_signals(rep) < 0)
		MTHROW_AND_ERR("FAILED collect_and_add_virtual_signals\n");

	// Initialize
	model.init_all(rep.dict, rep.sigs);

	// Required signals
	model.required_signal_names.clear();
	model.required_signal_ids.clear();
	vector<int> req_signals;

	unordered_set<string> signals_set;
	for (string& signal : signals)
		signals_set.insert(signal);
	model.get_required_signal_names_for_processed_values(signals_set, model.required_signal_names);

	// Signal ids
	for (string signal : model.required_signal_names) {
		req_signals.push_back(rep.dict.id(signal));
		model.required_signal_ids.insert(req_signals.back());
	}

	// Get Required signals per processor (set)
	unordered_set<int> signalIds;
	vector<int> signalIds_v;
	for (string signal : signals) {
		int signalId = rep.dict.id(signal);
		signalIds.insert(signalId);
		signalIds_v.push_back(signalId);
	}

	vector<unordered_set<int> > current_req_signal_ids(model.rep_processors.size());
	for (unsigned int i = 0; i < model.rep_processors.size(); i++) {
		current_req_signal_ids[i] = signalIds;
		for (int j = (int)model.rep_processors.size() - 1; j > i; j--)
			model.rep_processors[i]->get_required_signal_ids(current_req_signal_ids[i], current_req_signal_ids[i]);
	}

	PidDynamicRec idRec;
	MedIdSamples emptySamples;

	// Learning is sometimes required (e.g. for panel-completer)
	MedSamples emptyLearningSet;
	if (model.learn_all_rep_processors(rep, emptyLearningSet) < 0) 
		MTHROW_AND_ERR("MedModel learn() : ERROR: Failed learn_rep_processors()\n");

	for (int id : rep.index.pids) {
		emptySamples.id = id;

		// Generate DynamicRec with all relevant signals
		if (idRec.init_from_rep(std::addressof(rep), id, req_signals, 1) < 0)
			MTHROW_AND_ERR("Dynamic Rec initialization for pid=%d failed\n",id);

		// Apply rep-processing
		for (unsigned int i = 0; i < model.rep_processors.size(); i++) {
			if (model.rep_processors[i]->conditional_apply(idRec, emptySamples, current_req_signal_ids[i]) < 0)
				MTHROW_AND_ERR("Application of RepProcessor #%d for pid=%d failed\n", i, id);
		}

		// Print
		for (unsigned int ii=0; ii<signalIds_v.size(); ii++) {
			int signalId = signalIds_v[ii];
			string signalName = signals[ii];

			UniversalSigVec usv;
			rep.uget(id, signalId, usv);
			vector<pair<vector<string>, vector<string>>> prtintable_usv;
			rep.convert_pid_sigs(usv, prtintable_usv, signalName, signalId, 3);
			rep.print_pid_sig(id, signalName, prtintable_usv);
		}
	}

}

void get_model(po::variables_map& vm, MedModel& model, int& learn) {

	if (vm.count("modelJson")) {
		string modelFile = vm["modelJson"].as<string>();
		model.init_from_json_file(modelFile);
		learn = 1;
	}
	else {
		string modelFile = vm["modelBin"].as<string>();
		model.read_from_file(modelFile);
		learn = 0;
	}
}

void get_rep(po::variables_map& vm, vector<int>& ids, vector<string>& signals, MedModel *model, MedPidRepository& rep) {

	string config_file = vm["rep"].as<string>();

	// Add signals according to model.
	vector<string> all_signals;
	if (model != NULL) {
		unordered_set<string> signals_set;
		for (string& signal : signals)
			signals_set.insert(signal);

		model->get_required_signal_names_for_processed_values(signals_set, all_signals);

	}
	else
		all_signals = signals;

	if (ids.empty() && all_signals.empty()) {
		if (rep.read_all(config_file) < 0)
			MTHROW_AND_ERR("Cannot read all repository %s\n", config_file.c_str());
	}
	else {
		if (rep.read_all(config_file, ids, all_signals) < 0)
			MTHROW_AND_ERR("Cannot read all repository %s\n", config_file.c_str());
	}
}

