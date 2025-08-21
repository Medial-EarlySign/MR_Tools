// Get list of ids according to signal + sets

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "getIds.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	global_logger.init_level(LOG_MEDALGO, 6);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	string repFile = vm["rep"].as<string>();
	string signal = vm["signal"].as<string>();
	string setsFile = vm["sets"].as<string>();
	int channel = vm["channel"].as<int>();
	int lastDate = vm["last_date"].as<int>();
	string outFile = vm["output"].as<string>();

	// Read Samples
	vector<int> ids;
	MedSamples samples;

	if (vm.count("samples")) {
		string samplesFile = vm["samples"].as<string>();
		if (samples.read_from_file(samplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from %s\n", samplesFile.c_str());
		samples.get_ids(ids);
	}

	// Read Repository
	MedPidRepository rep;
	vector<string> signals = { signal };
	if (rep.read_all(repFile, ids, signals) != 0)
		MTHROW_AND_ERR("Cannot read repository from %s\n", repFile.c_str());

	// Read sets
	vector<string> sets;
	medial::io::read_codes_file(setsFile, sets);
	MLOG("Read %d sets from file\n", (int)sets.size());

	VEC_CATEGORIES setsLUT;
	int sectionId = rep.dict.section_id(signal);
	int signalId = rep.sigs.sid(signal);
	rep.dict.prep_sets_lookup_table(sectionId, sets, setsLUT);

	// Filter
	string reasonsFile = (vm.count("reasons") == 0) ? "" : vm["reasons"].as<string>();

	if (samples.idSamples.empty()) {
		vector<int> lastDates(rep.index.pids.size(), lastDate);
		vector<int> validFlags(rep.index.pids.size(), 0);
		getValidIds(rep, signalId, setsLUT, channel, rep.index.pids, lastDates, validFlags, reasonsFile);

		ofstream of(outFile);
		if (!of)
			MTHROW_AND_ERR("Cannot open %s for writing\n", outFile.c_str());
		for (size_t i = 0; i <  rep.index.pids.size(); i++) {
			if (validFlags[i])
				of << rep.index.pids[i] << "\n";
		}
	}
	else {
		vector<MedSample> samples_v;
		samples.export_to_sample_vec(samples_v);
		vector<int> ids(samples_v.size());
		vector<int> lastDates(samples_v.size());
		for (size_t i = 0; i < samples_v.size(); i++) {
			ids[i] = samples_v[i].id;
			lastDates[i] = samples_v[i].time;
		}

		vector<int> validFlags(ids.size(), 0);
		getValidIds(rep, signalId, setsLUT, channel,ids, lastDates, validFlags, reasonsFile);

		vector<MedSample> validSamples_v;
		for (size_t i = 0; i < ids.size(); i++) {
			if (validFlags[i])
				validSamples_v.push_back(samples_v[i]);
		}

		MedSamples validSamples;
		validSamples.import_from_sample_vec(validSamples_v);
		if (validSamples.write_to_file(outFile) != 0)
			MTHROW_AND_ERR("Failed writing to %s\n", outFile.c_str());

	}

}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("signal", po::value<string>()->required(), "signal to check")
			("sets", po::value<string>()->required(), "file with sets to requrie")
			("channel", po::value<int>()->default_value(0), "value channel")
			("samples", po::value<string>(), "optional samples file for ids and last-dates to check")
			("last_date", po::value<int>()->default_value(20990101), "last date to check")
			("output", po::value<string>()->required(), "output file")
			("reasons",po::value<string>(), "file with inclusion reasons")
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


void getValidIds(MedPidRepository& rep, int signalId, VEC_CATEGORIES setsLUT, int channel, vector<int>& ids, vector<int>&lastDates, vector<int>& validFlags, string& reasonsFile) {

	ofstream rf;
	if (reasonsFile != "") {
		cerr << "Writing reasons to " << reasonsFile << "\n";
		rf.open(reasonsFile.c_str(), ofstream::out);
		if (!rf)
			MTHROW_AND_ERR("Cannot open reasons file %s\n", reasonsFile.c_str());
	}

	UniversalSigVec sig;
	for (size_t i=0; i<ids.size(); i++) {
		rep.uget(ids[i], signalId, sig);

		for (int j = 0; j < sig.len; j++) {

			if (sig.Time(j) > lastDates[i])
				break;

			if (setsLUT[sig.Val(j,channel)]) {
				if (rf) {
					string out = to_string(ids[i]) + "\t" + to_string(signalId) + "\t" + rep.dict.name(signalId) + "\t" + to_string(sig.Time(j)) + "\t" + 
						rep.get_channel_info(signalId, channel, sig.Val(j, channel));
					rf << out << "\n";
				}
				validFlags[i] = 1;
				break;
			}
		}
	}
}

