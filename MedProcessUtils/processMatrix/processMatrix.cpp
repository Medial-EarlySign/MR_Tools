// process a MedFeatures matrix

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "processMatrix.h"
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

	int seed = vm["seed"].as<int>();
	globalRNG::srand(seed);


	// Read Features
	cerr << "Reading Features" << endl;
	MedFeatures features;
	readMatrix(features, vm);

	MedFeatures trainFeatures, testFeatures;

	// Process
	cerr << "Processing" << endl;
	string process = vm["process"].as<string>();
	if (process == "existing") {
		// Add an "existing" feature per each input feature
		addExisting(features);
	}
	else if (process == "sample") {
		// Randomly sample by ratios
		if (vm.count("processParams") == 0)
			MTHROW_AND_ERR("processParams (comma-separated sampling ratios) required for sample");
		string params = vm["processParams"].as<string>();
		sample(features, params);
	}
	else if (process == "nsample") {
		// Randomly sample by # of samples per id (n>0 - take up to n. n==0 - take all)
		if (vm.count("processParams") == 0)
			MTHROW_AND_ERR("processParams (comma-separated sampling numbers) required for sample");
		string params = vm["processParams"].as<string>();
		num_sample(features, params);
	}
	else if (process == "split") {
		// Split to Test + Train
		if (vm.count("processParams") == 0)
			MTHROW_AND_ERR("processParams (splitting ratios) required for split");
		string params = vm["processParams"].as<string>();
		split(features, params, trainFeatures, testFeatures);
	}
	else if (process == "normalize") {
		string inParamsFile = vm.count("inParamsFile") ? vm["inParamsFile"].as<string>() : "";
		string outParamsFile = vm.count("outParamsFile") ? vm["outParamsFile"].as<string>() : "";
		normalize(features, inParamsFile, outParamsFile);
	}
	else if (process == "denormalize") {
		if (vm.count("inParamsFile") == 0)
			MTHROW_AND_ERR("inParamsFile (normalization parameters file) required for denormalize");
		string inParamsFile = vm["inParamsFile"].as<string>();
		denormalize(features, inParamsFile);
	}
	else if (process == "combine") {
		if (vm.count("processParams") == 0)
			MTHROW_AND_ERR("processParams (comma-separated sampling ratios) required for combine");
		float priceRatio = stof(vm["processParams"].as<string>());

		cerr << "Reading Additional Features" << endl;
		MedFeatures features2;
		readMatrix(features2, vm, "inCsv2", "inBin2");

		combine(features, features2, priceRatio);
	} else if (process == "getSamples") {
		if (vm.count("outSamples") == 0)
			MTHROW_AND_ERR("outSamples required for getSamples");

		string outFile = vm["outSamples"].as<string>();
		MedSamples samples;
		samples.import_from_sample_vec(features.samples);
		samples.write_to_file(outFile);
		return 0;
	}
	else {
		// Apply a Feature Processor
		string params = vm.count("processParams") ? vm["processParams"].as<string>() : "";
		FeatureProcessor *processor = FeatureProcessor::make_processor(process, params);
		if (processor == NULL)
			MTHROW_AND_ERR("Unknown process %s\n", process.c_str());

		// Learn Feature Processor and apply it in 'learning' mode
		processor->learn(features);
		processor->apply(features);
	}

	// Write to file
	cerr << "Saving" << endl;
	if (vm.count("outCsv")) {
		if (process == "split") {
			string trainFileName = "train_" + vm["outCsv"].as<string>();
			if (trainFeatures.write_as_csv_mat(trainFileName) != 0)
				MTHROW_AND_ERR("Cannot write features to %s\n", trainFileName.c_str());
			string testFileName = "test_" + vm["outCsv"].as<string>();
			if (testFeatures.write_as_csv_mat(testFileName) != 0)
				MTHROW_AND_ERR("Cannot write features to %s\n", testFileName.c_str());
		}
		else {
			string fileName = vm["outCsv"].as<string>();
			if (features.write_as_csv_mat(fileName) != 0)
				MTHROW_AND_ERR("Cannot write features to %s\n", fileName.c_str());
		}
	}

	if (vm.count("outBin")) {
		if (process == "split") {
			string trainFileName = "train_" + vm["outBin"].as<string>();
			trainFeatures.write_to_file(trainFileName);
			string testFileName = "test_" + vm["outBin"].as<string>();
			testFeatures.write_to_file(testFileName);
		} 
		else {
			string fileName = vm["outBin"].as<string>();
			features.write_to_file(fileName);
		}
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("inCsv", po::value<string>(), "input matrix as a csv file")
			("inBin", po::value<string>(), "input matrix as a bin file")
			("inCsv2", po::value<string>(), "second input matrix as a csv file")
			("inBin2", po::value<string>(), "second input matrix as a bin file")
			("outCsv", po::value<string>(), "output matrix as a csv file")
			("outBin", po::value<string>(), "output matrix as a bin file")
			("process",po::value<string>()->required(), "process to perform")
			("processParams", po::value<string>(), "parameters of process to perform")
			("inParamsFile", po::value<string>(), "input file of process parameters")
			("outParamsFile", po::value<string>(), "output file of process parameters")
			("seed", po::value<int>()->default_value(123456), "random number generator seed")
			("outSamples",po::value<string>(), "output file for getSampels")
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

// Add "Existing" information
void addExisting(MedFeatures& features) {

	float missing_value = MED_MAT_MISSING_VALUE;

	vector<string> names;
	features.get_feature_names(names);
	int serial_id = features.get_max_serial_id_cnt();

	for (string& name : names) {
		string rawName;
		if (name.substr(0, 4) == "FTR_")
			rawName = name.substr(4, name.length() - 4);
		else
			rawName = name;

		string newName = "FTR_" + int_to_string_digits(++serial_id, 6) + rawName + ".Exist";

		FeatureAttr attr; attr.imputed = true; attr.normalized = false;
		features.attributes[newName] = attr;

		features.data[newName] = vector<float>(features.data[name].size(), 0);
		for (unsigned int i = 0; i < features.data[name].size(); i++) {
			if (features.data[name][i] == missing_value)
				features.data[newName][i] = 1;
		}
	}
}

// Sample matrix
void sample(MedFeatures& features, string& params) {

	vector<string> fields;
	boost::split(fields, params, boost::is_any_of(","));

	vector<float> ratios(fields.size());
	for (int i = 0; i < fields.size(); i++)
		ratios[i] = stof(fields[i]);

	map<int, int> tot, sampled;
	vector<string> names;
	features.get_feature_names(names);

	int outIdx = 0;
	for (int i = 0; i < features.samples.size(); i++) {
		int outcome = features.samples[i].outcome;
		if (outcome < 0 || outcome >= ratios.size())
			MTHROW_AND_ERR("No Ratio Found for outcome = %d\n", outcome);

		tot[outcome] ++;
		if ((globalRNG::rand() / (globalRNG::max() + 0.0)) <= ratios[outcome]) {
			if (outIdx != i) {
				features.samples[outIdx] = features.samples[i];
				for (string name : names)
					features.data[name][outIdx] = features.data[name][i];
				if (features.weights.size() > 0)
					features.weights[outIdx] = features.weights[i];
			}
			sampled[outcome] ++;
			outIdx++;
		}
	}

	features.samples.resize(outIdx);
	if (features.weights.size()>0)
		features.weights.resize(outIdx);
	for (string& name : names)
		features.data[name].resize(outIdx);

	features.init_pid_pos_len();
	for (auto& rec : tot)
		cerr << "outcome=" << rec.first << " : sampled " << sampled[rec.first] << " out of " << rec.second << "\n";
}

void num_sample(MedFeatures& features, string& params) {

	vector<string> fields;
	boost::split(fields, params, boost::is_any_of(","));

	vector<int> nums(fields.size());
	for (int i = 0; i < fields.size(); i++)
		nums[i] = stoi(fields[i]);

	MedSamples samples; 
	samples.import_from_sample_vec(features.samples);
	vector<int> index(features.samples.size(), 0);

	// Select
	int idx = 0;
	for (auto& idSample : samples.idSamples) {
		// Check that all samples have the sampe label ;
		for (int i = 1; i < idSample.samples.size(); i++) {
			if (idSample.samples[i].outcome != idSample.samples[0].outcome)
				MTHROW_AND_ERR("Cannot perform num_sampling when id=%d has different outcomes", idSample.samples[i].id);
			int targetN = nums[(int)(idSample.samples[0].outcome)];
			int origN = (int)idSample.samples.size();
			if (targetN <= 0 || targetN > origN)
				targetN = origN;

			// Randomly select
			vector<int> indices(origN);
			for (int j = 0; j < origN; j++)
				indices[j] = j;
			boost::random_shuffle(indices);
			for (int j = 0; j < targetN; j++)
				index[idx + indices[j]] = 1;
			idx += origN;
		}
	}

	// Recreate features
	map<int, int> tot, sampled;
	vector<string> names;
	features.get_feature_names(names);

	int outIdx = 0;
	for (int i = 0; i < features.samples.size(); i++) {
		if (index[i]) {
			if (outIdx != i) {
				features.samples[outIdx] = features.samples[i];
				for (string name : names)
					features.data[name][outIdx] = features.data[name][i];
				if (features.weights.size() > 0)
					features.weights[outIdx] = features.weights[i];
			}
			outIdx++;
		}
	}

	features.samples.resize(outIdx);
	if (features.weights.size()>0)
		features.weights.resize(outIdx);
	for (string& name : names)
		features.data[name].resize(outIdx);

	features.init_pid_pos_len();
	for (auto& rec : tot)
		cerr << "outcome=" << rec.first << " : sampled " << sampled[rec.first] << " out of " << rec.second << "\n";
}

// Train-test Splitting
void split(MedFeatures& features, string& params, MedFeatures& trainFeatures, MedFeatures& testFeatures) {

	float ratio = stof(params);

	map<int,int> trainIds;
	vector<string> names;
	features.get_feature_names(names);
	vector<MedFeatures *> out = { &trainFeatures,&testFeatures };

	for (int i = 0; i < features.samples.size(); i++) {
		int id = features.samples[i].id;
		if (trainIds.find(id) == trainIds.end())
			trainIds[id] = ((globalRNG::rand() / (globalRNG::max() + 0.0)) <= ratio) ? 0 : 1;

		int idx = trainIds[id];
		out[idx]->samples.push_back(features.samples[i]);
		for (string name : names)
			out[idx]->data[name].push_back(features.data[name][i]);
		if (features.weights.size() > 0)
			out[idx]->weights.push_back(features.weights[i]);
	}

	for (auto attr : features.attributes) {
		trainFeatures.attributes[attr.first] = attr.second;
		testFeatures.attributes[attr.first] = attr.second;
	}

	for (auto tag : features.tags) {
		trainFeatures.tags[tag.first] = tag.second;
		testFeatures.tags[tag.first] = tag.second;
	}

	trainFeatures.init_pid_pos_len();
	testFeatures.init_pid_pos_len();
}

// (de)normalization
void normalize(MedFeatures& features, string& inParamsFile, string& outParamsFile) {

	normParams params;

	if (inParamsFile != "") {
		// Read
		params.read_from_file(inParamsFile);
		for (auto& rec : params.avg) {
			string name = rec.first;
			MLOG("NormParams: %s :: %f\t%f\n", name.c_str(), rec.second, params.std[name]);
		}
	}
	else {
		// Calculate
		for (auto& data_rec : features.data) {
			string ftr = data_rec.first;
			double sum = 0, sum2 = 0;
			size_t n = data_rec.second.size();
			for (float v : data_rec.second) {
				sum += v;
				sum2 += v * v;
			}

			params.avg[ftr] = sum / n;
			params.std[ftr] = sqrt((sum2 - params.avg[data_rec.first] * sum) / (n - 1));
			if (params.std[ftr] == 0.0)
				params.std[ftr] = 1.0;
		}
	}
	
	// Noramlzie
	for (auto& data_rec : features.data) {
		string ftr = data_rec.first;
		for (size_t i = 0; i < data_rec.second.size(); i++)
			data_rec.second[i] = (data_rec.second[i] - params.avg[ftr]) / params.std[ftr];
	}

	// Save
	if (outParamsFile != "")
		params.write_to_file(outParamsFile);
}

void denormalize(MedFeatures& features, string& paramsFile) {

	normParams params;

	// Read
	params.read_from_file(paramsFile);

	// deNoramlzie
	for (auto& data_rec : features.data) {
		string ftr = data_rec.first;
		for (size_t i = 0; i < data_rec.second.size(); i++)
			data_rec.second[i] = data_rec.second[i] * params.std[ftr] + params.avg[ftr];
	}

}

// Combine two matrices with matching. Assuming binary outcome
void combine(MedFeatures& features, MedFeatures& features2, float priceRatio) {

	// Sanity - check names are identical
	vector<string> names1, names2;
	features.get_feature_names(names1);
	features2.get_feature_names(names2);

	string all_names1 = boost::join(names1, ",");
	string all_names2 = boost::join(names2, ",");
	if (all_names1 != all_names2)
		MTHROW_AND_ERR("Names mismatch: %s VS %s\n", all_names1.c_str(), all_names2.c_str());


	int n1 = (int)features.samples.size();
	int s1 = 0;
	for (int i = 0; i < n1; i++)
		s1 += (int)features.samples[i].outcome;
	float r1 = (s1 + 0.0) / n1;

	int n2 = (int)features2.samples.size();
	int s2 = 0;
	for (int i = 0; i < n2; i++)
		s2 += (int)features2.samples[i].outcome;
	float r2 = (s2 + 0.0) / n2;
	MLOG("R1 = %f R2 = %f\n", r1, r2);

	// Choose ratio
	float price1 = 0, price2 = 0; // Price1 = price if choosing r1, Price2 = price if choosing r2
	if (r1 > r2) {
		price1 = 1.0*((n2 - s2) - n2 * (1 - r1)); // Removing controls from r2
		price2 = priceRatio * (s1 - n1 * r2); // Removing cases from r1
	}
	else {
		price1 = priceRatio * (s2 - n2 * r1); // Removing cases from r2
		price2 = 1.0*((n1 - s1) - n1 * (1 - r2)); // Removing controls from r1
	}
	MLOG("Price1 = %f Price2 = %f\n", price1, price2);

	vector<float> p1 = { 1.0,1.0 }, p2 = { 1.0,1.0 };
	if (price1 > price2) {
		// Ratio = r2
		if (r1 > r2)
			p1 = { 1.0, r2 / r1 };
		else
			p1 = { r1 / r2,1.0 };
	}
	else {
		if (r2 > r1)
			p2 = { 1.0,r1 / r2 };
		else
			p2 = { r2 / r1,1.0 };
	}
	MLOG("p1 = %f,%f p2 = %f,%f\n", p1[0],p1[1],p2[0],p2[1]);


	// Indices Vectors
	vector<int> indices1, indices2;
	for (int i = 0; i < n1; i++) {
		int outcome = (int)features.samples[i].outcome;
		if ((globalRNG::rand() / (globalRNG::max() + 0.0)) <= p1[outcome])
			indices1.push_back(i);
	}
	for (int i = 0; i < n2; i++) {
		int outcome = (int)features2.samples[i].outcome;
		if ((globalRNG::rand() / (globalRNG::max() + 0.0)) <= p2[outcome])
			indices2.push_back(i);
	}
	MLOG("N1 = %d N2 = %d\n", (int)indices1.size(), (int)indices2.size());

	// ReFill Features
	for (string& name : names1) {
		features.data[name].resize(indices1.size() + indices2.size());

		int idx = 0;
		for (int i : indices1)
			features.data[name][idx++] = features.data[name][i];
		for (int i : indices2)
			features.data[name][idx++] = features2.data[name][i];
	}

	features.samples.resize(indices1.size() + indices2.size());
	int idx = 0;
	for (int i : indices1)
		features.samples[idx++] = features.samples[i];
	for (int i : indices2)
		features.samples[idx++] = features2.samples[i];

}
