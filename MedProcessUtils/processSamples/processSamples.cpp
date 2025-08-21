// Process Samples

#include "processSamples.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#include <MedUtils/MedUtils/MedGlobalRNG.h>
#include "boost/range/algorithm/random_shuffle.hpp"

int main(int argc, char *argv[])
{

	global_logger.init_level(LOG_MEDALGO, 6);

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	if (vm.count("attr") + vm.count("str_attr")>1) 
		MTHROW_AND_ERR("Currently only one of attr and str_attr allowed")

	// Mode
	if (vm.count("split_p") + vm.count("nums") + vm.count("attr") != 1)
		MTHROW_AND_ERR("Don't know what to do. Quitting");

	//Read samples
	MedSamples samples;
	string inFile = vm["in"].as<string>();
	if (samples.read_from_file(inFile) != 0)
		MTHROW_AND_ERR("Reading samples from %s failed\n", inFile.c_str());

	if (vm.count("split_p")) {
		// Split
		float p = vm["split_p"].as<float>();
		MLOG("Splitting with P=%f\n", p);
		string outFile1 = vm["out1"].as<string>();
		string outFile2 = vm["out2"].as<string>();
		split_samples(samples, p, outFile1, outFile2);
	}
	else if (vm.count("nums")) {
		string nums_s = vm["nums"].as<string>();
		MLOG("Filterring with nums=%s\n", nums_s.c_str());

		vector<string> fields;
		boost::split(fields, nums_s, boost::is_any_of(","));
		vector<int> nums(fields.size());
		for (size_t i = 0; i < nums.size(); i++)
			nums[i] = stoi(fields[i]);
		string outFile = vm["out1"].as<string>();
		filter_samples(samples, nums, outFile);
	}
	else if (vm.count("attr") || vm.count("str_attr")) {

		MedFeatures ftrs;
		samples.export_to_sample_vec(ftrs.samples);
		vector<string> signatures(ftrs.samples.size());

		if (vm.count("attr")) {
			string attr = vm["attr"].as<string>();
			for (size_t i = 0; i < signatures.size(); i++)
				signatures[i] = to_string(ftrs.samples[i].attributes[attr]);
		}
		else {
			string attr = vm["str_attr"].as<string>();
			for (size_t i = 0; i < signatures.size(); i++)
				signatures[i] = ftrs.samples[i].str_attributes[attr];
		}

		float eventToControlPriceRatio = vm["matchPriceRatio"].as<float>();
		float maxControlToEventRatio = vm["matchMaxRatio"].as<float>();
		int min_group_size = vm["matchMinGroup"].as<int>();
		vector<int> filtered;

		medial::process::match_by_general(ftrs, signatures, filtered, eventToControlPriceRatio, maxControlToEventRatio, min_group_size, 0);
		
		MedSamples outSamples;
		outSamples.import_from_sample_vec(ftrs.samples);
		string outFile = vm["out1"].as<string>();
		outSamples.write_to_file(outFile);
	}

}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("in", po::value<string>()->required(), "input samples file")
			("out1", po::value<string>(), "first output sampels file")
			("out2", po::value<string>(), "second output sampels file")
			("split_p", po::value<float>(), "splitting probability")
			("nums", po::value<string>(), "comma-separated of number of samples to choose per id (outcome-dependent; <=0 = select all)")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
			("attr", po::value<string>(), "if given, perform matching by attribute")
			("str_attr", po::value<string>(), "if given, perform matching by attribute")
			("matchPriceRatio",po::value<float>()->default_value(100.0),"price ratio for matching")
			("matchMaxRatio",po::value<float>()->default_value(10.0), "max contorl/case ratio for matching")
			("matchMinGroup",po::value<int>()->default_value(100),"minimal group size for matching")
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

void split_samples(MedSamples& in, float& p, string& outFile1, string& outFile2) {

	vector<int> ids;
	in.get_ids(ids);

	unordered_set<int> ids_set;
	for (int id : ids) {
		if ((globalRNG::rand() / (globalRNG::max() + 0.0)) < p)
			ids_set.insert(id);
	}

	MedSamples out1, out2;
	for (MedIdSamples& idSample : in.idSamples) {
		if (ids_set.find(idSample.id) == ids_set.end())
			out1.idSamples.push_back(idSample);
		else
			out2.idSamples.push_back(idSample);
	}

	if (out1.write_to_file(outFile1) != 0 || out2.write_to_file(outFile2) != 0)
		MTHROW_AND_ERR("Failed writing to output files");
}

void filter_samples(MedSamples& samples, vector<int>& nums, string& outFile) {

	vector<MedSample> filtered;
	for (auto& idSample : samples.idSamples) {
		// Check that all samples have the sampe label ;
		for (int i = 1; i < idSample.samples.size(); i++) {
			if (idSample.samples[i].outcome != idSample.samples[0].outcome)
				MTHROW_AND_ERR("Cannot perform num_sampling when id=%d has different outcomes", idSample.samples[i].id);
		}

		int outcome = (int)(idSample.samples[0].outcome);
		if (outcome < 0 || outcome >= (int)nums.size())
			MTHROW_AND_ERR("Cannot filter outcome=%d", outcome);

		int targetN = nums[outcome];
		int origN = (int)idSample.samples.size();
		if (targetN <= 0 || targetN > origN)
			targetN = origN;

		// Randomly select
		vector<int> indices(origN);
		for (int j = 0; j < origN; j++)
			indices[j] = j;
		boost::random_shuffle(indices);
		for (int j = 0; j < targetN; j++)
			filtered.push_back(idSample.samples[indices[j]]);
	}

	// Write to file
	MedSamples outSamples;
	outSamples.import_from_sample_vec(filtered);
	outSamples.write_to_file(outFile);
}