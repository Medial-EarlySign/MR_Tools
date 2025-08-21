#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>
#include <fstream>
#include <MedProcessTools/MedProcessTools/MedSamples.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

class Calibration_Test : public SerializableObject {
public:
	string model_path = "";
	string validation_samples_path = "";
	int filter_split = -1;

	MedSamples stored_samples;

	int init(map<string, string>& mapper) {
		for (auto &it : mapper)
		{
			if (it.first == "model_path")
				model_path = it.second;
			else if (it.first == "validation_samples_path")
				validation_samples_path = it.second;
			else if (it.first == "filter_split")
				filter_split = med_stoi(it.second);
			else
				HMTHROW_AND_ERR("Error unsupported arg %s\n", it.first.c_str());
		}
		return 0;
	}

	ADD_SERIALIZATION_FUNCS(model_path, validation_samples_path, filter_split)
		ADD_CLASS_NAME(Calibration_Test)
};

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string tests_file;

	void post_process() {
		if (cases_weight <= 0)
			HMTHROW_AND_ERR("Error - cases_weight should be bigger than 0. got %f\n", cases_weight);
		if (controls_weight <= 0)
			HMTHROW_AND_ERR("Error - controls_weight should be bigger than 0. got %f\n", controls_weight);

		ifstream fr(tests_file);
		if (!fr.good())
			HMTHROW_AND_ERR("Error can't read %s file - excpeting format is line for each test with TAB delimeted of modle_path,samples_path,split_to_filter(keep -1 to select all)\n",
				tests_file.c_str());
		string line;
		while (getline(fr, line)) {
			boost::trim(line);
			if (line.empty() || line[0] == '#')
				continue;
			vector<string> tokens;
			boost::split(tokens, line, boost::is_any_of("\t"));
			Calibration_Test test_obj;
			test_obj.validation_samples_path = tokens[0];
			if (tokens.size() > 1)
				test_obj.model_path = tokens[1];
			if (tokens.size() > 2)
				test_obj.filter_split = med_stoi(tokens[2]);
			tests.push_back(move(test_obj));
		}
		fr.close();
		if (tests.empty())
			HMTHROW_AND_ERR("Error - no tests in file %s\n- excpeting format is line for each test with TAB delimeted of modle_path,samples_path,split_to_filter(keep -1 to select all)\n",
				tests_file.c_str());
		MLOG("Read %zu tests\n", tests.size());
	}
public:
	string rep;
	vector<Calibration_Test> tests; ///can have multiple tests for each split - will produce results for each split and all

	string output;
	bool test_kaplan_meier;
	int kaplan_meier_time;
	string pid_splits_to_model_file; ///< to specify splits with file
	int min_bin_size; ///< minimal bin size to enforce
	string pred_binning_arg; ///< Full argument to initialize BinSettings. For example: "split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0.1" methods:iterative_merge,same_width,partition_mover,dynamic_split
	float cases_weight, controls_weight;
	float std_factor; ///< the std factor for confidence interval without bootstrap

	string bt_params; ///< bootstrap params - if not empty will do bootstraping of MedBootstrap
	string json_model; ///< json to create features for cohorts
	string cohorts_file; ///< cohorts - like in bootstrap
	bool calc_bins_once; ///< If true will calculate bins once in bootstrap (faster)
	string bootstrap_graphs; ///< if given, the path to plot bootstrap graphs

	ProgramArgs() {
		po::options_description options("Program Options");
		options.add_options()
			("rep", po::value<string>(&rep)->required(), "repository path")
			("tests_file", po::value<string>(&tests_file)->required(), "A test file with 3 TAB tokens in each line: samples_path, optional model_path to apply on samples and optional split to filter from samples")
			("pid_splits_to_model_file", po::value<string>(&pid_splits_to_model_file)->default_value(""), "Optional - If given will use this to choose model for each each split based on patient id")
			("test_kaplan_meier", po::value<bool>(&test_kaplan_meier)->default_value(false), "If true will test kaplan meier")
			("kaplan_meier_time", po::value<int>(&kaplan_meier_time)->default_value(365), "The time for kaplan meier")
			("min_bin_size", po::value<int>(&min_bin_size)->default_value(0), "minimal bin size to enforce")
			("cases_weight", po::value<float>(&cases_weight)->default_value(1.0), "weight of cases")
			("controls_weight", po::value<float>(&controls_weight)->default_value(1.0), "weight of controls")
			("pred_binning_arg", po::value<string>(&pred_binning_arg)->default_value(""), "Full argument to initialize BinSettings. For example: \"split_method = iterative_merge; binCnt = 50; min_bin_count = 100; min_res_value = 0.1\" methods:iterative_merge,same_width,partition_mover,dynamic_split")
			("std_factor", po::value<float>(&std_factor)->default_value(2.0), "the std factor for confidence interval without bootstrap")
			("output", po::value<string>(&output)->default_value(""), "output file path")

			("bt_params", po::value<string>(&bt_params)->default_value(""), "bootstrap params - if not empty will do bootstraping of MedBootstrap")
			("json_model", po::value<string>(&json_model)->default_value(""), "json to create features for cohorts")
			("cohorts_file", po::value<string>(&cohorts_file)->default_value(""), "cohorts - like in bootstrap. If empty will just analyze all samples")
			("calc_bins_once", po::value<bool>(&calc_bins_once)->default_value(true), "If true will calculate bins once in bootstrap (faster)")
			("bootstrap_graphs", po::value<string>(&bootstrap_graphs)->default_value(""), "if given, the path to plot bootstrap graphs")
			;

		init(options);
	}
};


#endif
