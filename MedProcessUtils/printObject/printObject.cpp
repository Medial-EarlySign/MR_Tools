// Read an object from a binary file and print

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "printObject.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{


	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm);

	if (vm.count("predictor") + vm.count("features") + vm.count("model") != 1)
		MTHROW_AND_ERR("Exactly one of predictor/features/model must be given");

	int level = vm["level"].as<int>();
	if (vm.count("predictor")) { // Predictor
		cerr << "Reading Predictor" << endl;
		string predictorFile = vm["predictor"].as<string>();
		MedPredictor *pred;
		read_predictor_from_file(pred, predictorFile);

		FILE *fp;
		if (vm.count("out")) {
			string fileName = vm["out"].as<string>();
			fp = fopen(fileName.c_str(), "w");
			if (fp == NULL)
				MTHROW_AND_ERR("Cannot open %s for writing\n", fileName.c_str());
		}
		else
			fp = stdout;

		print_predictor(pred, fp,level);
	}
	else if (vm.count("features")) { // Features
		MedFeatures matrix;
		string inFileName = vm["features"].as<string>();
		matrix.read_from_file(inFileName);

		if (vm.count("out")) {
			string outFileName = vm["out"].as<string>();
			matrix.write_as_csv_mat(outFileName);
		}
		else
			MTHROW_AND_ERR("Writing of MedFeatures to stdout is not implemented\n")
	}
	else if (vm.count("model")) { // Model
		MedModel model; 
		string inFileName = vm["model"].as<string>();
		model.read_from_file(inFileName);

		if (vm.count("out")) {
			// Set all logging files to out-file
			string outFileName = vm["out"].as<string>();
			global_logger.init_all_files(outFileName);
			model.dprint_process(inFileName, level, level, level, level, level);
			FILE *fp = fopen(outFileName.c_str(), "a");
			print_feature_importance(model.predictor, fp);
		}
		else {
			model.dprint_process(inFileName, level, level, level, level, level);
			print_feature_importance(model.predictor, stderr);
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
			("predictor", po::value<string>(), "predictor")
			("features", po::value<string>(), "features")
			("model", po::value<string>(), "model")
			("out", po::value<string>(), "output file")
			("level", po::value<int>()->default_value(0), "printout level, when applicable (e.g. model)")
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

// Print a predictor
void print_predictor(MedPredictor *predictor, FILE *fp, int level) {

	// Print info
	predictor->print(fp, "", level);

	// feature importance print
	if (level > 1)	
		print_feature_importance(predictor, fp);
}

void print_feature_importance(MedPredictor *predictor, FILE *fp) {

	vector<float> features_scores;
	predictor->calc_feature_importance(features_scores, "");

	//sort and print features
	vector<string> feat_names = predictor->model_features;
	if (predictor->classifier_type == MODEL_GD_LINEAR)
		feat_names.push_back("b0_const");

	if (feat_names.size() != features_scores.size()) {
		MLOG("Got %zu features and %zu scores in predictor to used features.. giving names by order\n",
			feat_names.size(), features_scores.size());
		feat_names.resize(features_scores.size());
		for (size_t i = 0; i < feat_names.size(); ++i)
			feat_names[i] = "FTR_" + to_string(i + 1);
	}
	else
		MLOG("Got %zu features in predictor\n", feat_names.size());

	sort(feat_names.begin(), feat_names.end());
	vector<pair<string, float>> ranked((int)features_scores.size());
	for (size_t i = 0; i < features_scores.size(); ++i)
		ranked[i] = pair<string, float>(feat_names[i], features_scores[i]);
	sort(ranked.begin(), ranked.end(), [](const pair<string, float> &c1, const pair<string, float> &c2) {return c1.second > c2.second;});

	for (size_t i = 0; i < ranked.size(); ++i)
		fprintf(fp, "FEATURE IMPORTANCE %s : %2.3f\n", ranked[i].first.c_str(), ranked[i].second);
}

