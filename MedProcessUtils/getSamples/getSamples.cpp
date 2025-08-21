// Generate a samples set

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "getSamples.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	global_logger.init_level(LOG_MEDALGO, 6);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// Signals : 
	vector<string> signalNames = { "Cancer_Location","BYEAR", "GENDER", "STARTDATE", "ENDDATE", "TRAIN" };
	vector<string> anchorSignals;
	string anchorsFile = vm["anchors"].as<string>();
	if (readList(anchorsFile, anchorSignals) != 0)
		MTHROW_AND_ERR("Cannot read anchor signals frmo %s\n", anchorsFile.c_str());
	signalNames.insert(signalNames.end(), anchorSignals.begin(), anchorSignals.end());

	// Read Repository
	string configFile = vm["rep"].as<string>();

	cerr << "Reading Repository" << endl;
	MedPidRepository rep;
	vector<int> ids;
	if (rep.read_all(configFile, ids, signalNames) != 0)
		MTHROW_AND_ERR("Read repository from %s failed\n", configFile.c_str());

	// Generate Samples
	int minAge = vm["minAge"].as<int>();
	int maxAge = vm["maxAge"].as<int>();
	int history = vm["history"].as<int>();
	int followUp = vm["follow"].as<int>();
	int winStart = vm["winStart"].as<int>();
	int winEnd = vm["winEnd"].as<int>();
	int minYear = vm["minYear"].as<int>();
	int maxYear = vm["maxYear"].as<int>();
	int jump = vm["jump"].as<int>();
	int trainBitMap = vm["train"].as<int>();
	string cancerSet = vm["cancerSet"].as<string>();

	MedSamples samples;
	getSamples(rep, anchorSignals, minAge, maxAge, history, followUp, cancerSet, winStart, winEnd, jump, minYear, maxYear, trainBitMap, samples);

	// Write Samples
	string outFile = vm["outFile"].as<string>();
	samples.write_to_file(outFile);

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("anchors", po::value<string>()->required(), "file of signals to use as potential anchors for samples")
			("minAge", po::value<int>()->default_value(40), "minimal age")
			("maxAge", po::value<int>()->default_value(90), "maximal age")
			("minYear", po::value<int>()->default_value(1990), "minimal year")
			("maxYear", po::value<int>()->default_value(2100), "maximal year")
			("history", po::value<int>()->default_value(365), "required history (in days)")
			("follow", po::value<int>()->default_value(730), "required history (in days)")
			("winStart", po::value<int>()->default_value(30), "start of time-windows for cases")
			("winEnd", po::value<int>()->default_value(730), "end of time-windows for cases")
			("jump", po::value<int>()->default_value(180), "jump between samples (in days)")
			("cancerSet", po::value<string>()->default_value(""), "Cancer set to consider")
			("train", po::value<int>()->default_value(1), "bitmap of TRAIN values to take")
			("outFile", po::value<string>()->required(), "output file")
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

// Get Samples
void getSamples(MedPidRepository& rep, vector<string>& anchorSignals, int minAge, int maxAge, int history, int followUp, string& cancerSet, int winStart, int winEnd, int jump, int minYear, int maxYear,
	int trainBitMap, MedSamples& samples) {


	// Lookup table for cancer-set
	bool cancer = false;
	vector<char> lut;
	if (cancerSet != "") {
		cancer = true;
		int section_id = rep.dict.section_id("Cancer_Location");
		vector<string> sets = { cancerSet };
		rep.dict.prep_sets_lookup_table(section_id, sets, lut);
	}

	// Generate cohort
	int startSigId = rep.dict.id("STARTDATE");
	int endSigId = rep.dict.id("ENDDATE");
	int regSigId = rep.dict.id("Cancer_Location");

	MedCohort cohort;
	for (int id : rep.index.pids) {

		// START and END Dates
		int startDate = medial::repository::get_value(rep, id, startSigId);
		int endDate = medial::repository::get_value(rep, id, endSigId);
		// Case/Control
		UniversalSigVec locations;
		rep.uget(id, regSigId, locations);

		if (cancer && (locations.len > 0 && lut[locations.Val(0)] == 0))
			continue;

		float outcome = (cancer && locations.len > 0) ? 1.0 : 0.0;
		int outcomeTime = (cancer && locations.len > 0) ? locations.Time(0) : endDate;

		cohort.recs.push_back(CohortRec(id, startDate, endDate, outcomeTime, outcome));
	}

	cerr << "Generated cohort with " << cohort.recs.size() << " records\n";

	// Generate smples from cohort
	SamplingParams params;
	params.min_control_years = followUp / 365.0;
	params.max_case_years = winEnd / 365.0;
	params.is_continous = 0;
	params.min_days_from_outcome = winStart;
	params.min_age = minAge;
	params.max_age = maxAge;
	params.train_mask = trainBitMap;
	params.jump_days = jump;
	params.stick_to_sigs = anchorSignals;
	params.min_year  = minYear;
	params.max_year = maxYear ;

	cohort.create_samples_sticked(rep, params, samples);

	cerr << "Generated " << samples.nSamples() << " samples\n";
}
