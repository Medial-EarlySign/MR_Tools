// Generate a matrix given samples and a model (either as JSON or as bin)

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "getMatrix.h"
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

	string configFile = vm["rep"].as<string>();
	
	if (vm.count("samples") + vm.count("inCsv") + vm.count("inBin") != 1)
		MTHROW_AND_ERR("Exactly one of samples, inCsv and inBin should be given\n");

	if (vm.count("outCsv") + vm.count("outBin") == 0)
		MTHROW_AND_ERR("At least one of outCsv and outBin should be given\n");

	if (vm.count("modelJson") + vm.count("modelBin") != 1)
		MTHROW_AND_ERR("Exactly one of modelJson and modelBin should be given\n");

	// Threading
	if (vm.count("nthreads")) {
		int nThreads = vm["nthreads"].as<int>();
		omp_set_num_threads(nThreads);
	}

	// Read Samples/Features
	cerr << "Reading samples/features" << endl;

	MedSamples samples;
	MedFeatures inFeatures;
	inFeatures.time_unit = global_default_time_unit;

	if (vm.count("samples")) {
		string samplesFile = vm["samples"].as<string>();
		if (samples.read_from_file(samplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from %s", samplesFile.c_str());
	}
	else {
		readMatrix(inFeatures, vm);
		inFeatures.get_samples(samples);

		if (vm.count("only_samples_from_matrix"))
			strip_matrix(inFeatures);

		MedFeatures::global_serial_id_cnt = inFeatures.get_max_serial_id_cnt();
	}

	// Read Model
	cerr << "Reading model" << endl;
	int learn;
	MedModel model;
	if (vm.count("modelJson")) {
		string modelFile = vm["modelJson"].as<string>();
		vector<string> jsonAlts;
		if (vm.count("jsonAlt"))
			for (string alt : vm["jsonAlt"].as<vector<string>>())
				jsonAlts.push_back(alt);
		model.init_from_json_file_with_alterations(modelFile, jsonAlts);
		learn = 1;
	}
	else {
		string modelFile = vm["modelBin"].as<string>();
		string changesJson = vm["modelChanges"].as<string>();
		model.read_from_file_with_changes(modelFile,changesJson);
		learn = 0;
	}

	cerr << "Getting ids" << endl;
	vector<int> ids;
	samples.get_ids(ids);

	// Read Repository
	bool allow_fitting = (vm.count("allow_fitting") > 0);
	MedPidRepository rep;
	model.load_repository(configFile, ids, rep, (learn == 1 || allow_fitting));

	// Match
	if (vm.count("matching")) {
		if (!vm.count("samples"))
			MTHROW_AND_ERR("Matching on features input is not implemented yet\n");

		string matchingParams = vm["matching"].as<string>();
		SampleFilter *matcher = SampleFilter::make_filter("match", matchingParams);
		matcher->filter(rep, samples);
		MLOG("Matching results in %d samples\n", samples.nSamples());
	}

	if (vm.count("samples"))
		inFeatures.init_all_samples(samples.idSamples);


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

	if (sizes.size()>1 && vm.count("outBin"))
		MTHROW_AND_ERR("Currently cannot write to bin file in multiple batches. Try increasing batch size to %d\n", samples.nSamples())

	MLOG("Will work on %d batches:", sizes.size());
	for (size_t i = 0; i < sizes.size(); i++)
		MLOG(" ids %d-%d (%d samples)", batches[i], batches[i + 1], sizes[i]);
	MLOG("\n");

	// Loop on batches
	int iSamples = 0;
	MedModelStage endStage = (vm.count("noProcess")) ? MED_MDL_APPLY_FTR_GENERATORS : MED_MDL_APPLY_FTR_PROCESSORS;
	for (size_t i = 0; i < sizes.size(); i++) {
		MedSamples batchSamples;
		batchSamples.time_unit = samples.time_unit;
		batchSamples.idSamples.insert(batchSamples.idSamples.end(), samples.idSamples.begin() + batches[i], samples.idSamples.begin() + batches[i + 1]);

		// Get matrix
		cerr << "Getting Matrix for batch" << i << endl;

		if (learn)
			model.learn(rep, &batchSamples, MED_MDL_LEARN_REP_PROCESSORS, endStage);
		else
			model.apply(rep, batchSamples, MED_MDL_APPLY_FTR_GENERATORS, endStage);

		// Add data + attributes from inFeatures
		for (auto& rec : inFeatures.data) {
			string name = rec.first;
			if (inFeatures.attributes.find(name) != inFeatures.attributes.end())
				model.features.attributes[name] = inFeatures.attributes[name];
			if (inFeatures.tags.find(name) != inFeatures.tags.end())
				model.features.tags[name] = inFeatures.tags[name];
			model.features.data[name].assign(inFeatures.data[name].begin() + batches[i], inFeatures.data[name].begin() + batches[i + 1]);
		}

		// Write to file
		cerr << "Saving" << endl;
		if (vm.count("outCsv")) {
			string fileName = vm["outCsv"].as<string>();
			bool attr_flag = !(vm.count("no_attr"));
			if (i == 0) {
				if (model.features.write_as_csv_mat(fileName, attr_flag) != 0)
					MTHROW_AND_ERR("Cannot write features to %s\n", fileName.c_str());
			}
			else {
				if (model.features.add_to_csv_mat(fileName,attr_flag, iSamples)!=0)
					MTHROW_AND_ERR("Cannot write features to %s\n", fileName.c_str());
			}
			iSamples += model.features.samples.size();
		}

		if (vm.count("outBin")) {
			string fileName = vm["outBin"].as<string>();
			model.features.write_to_file(fileName);
		}
	}
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value(DEFAULT_REP), "repository config file")
			("matching", po::value<string>(), "optional matching parameters")
			("samples", po::value<string>(), "training samples")
			("inCsv", po::value<string>(), "input csv matrix file")
			("inBin", po::value<string>(), "input bin matrix file")
			("modelJson", po::value<string>(), "model json file")
			("jsonAlt", po::value<vector<string>>()->composing(), "(multiple) alterations to model json file")
			("modelBin", po::value<string>(), "model bin file")
			("modelChanges", po::value<string>()->default_value(""), "optional changes to binary model (json file)")
			("outCsv", po::value<string>(), "csv matrix file")
			("outBin", po::value<string>(), "bin matrix file")
			("noProcess",  "do not apply feature-processing")
			("nthreads", po::value<int>(), "optional max # of trheads")
			("inpatient", "indicate that relevant data is in-patient data")
			("no_attr", "do not write attributes to csv")
			("only_samples_from_matrix", "if input is matrix (inCsv or inBin), ues it only for sampels")
			("allow_fitting", "allow replacing input signals with virtual ones if not available")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
			("batch_size", po::value<int>(), "batch size for predictions (no.of samples, rounded to ids)")
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

// Keep only samples in matrix
void strip_matrix(MedFeatures& features) {

	vector<string> names;
	features.get_feature_names(names);

	for (string& name : names) {
		features.data.erase(name);
		features.attributes.erase(name);
		features.global_serial_id_cnt = 0;
		features.tags.erase(name);
	}
}

