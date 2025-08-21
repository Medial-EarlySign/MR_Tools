#ifndef __PROGRAM__ARGS__H__
#define __PROGRAM__ARGS__H__

#include <boost/program_options.hpp>
#include <boost/spirit/home/support/detail/hold_any.hpp>
#include <boost/algorithm/string.hpp>
#include <string>
#include <vector>
#include <map>
#include <unordered_map>
#include <fstream>
#include <iostream>
#include <algorithm>
#include "MedUtils/MedUtils/MedUtils.h"
#include "Logger/Logger/Logger.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;

enum Input_types {
	Samples = 1,
	Features = 2,
	Samples_Bin = 3,
	Features_Csv = 4,
	MedMat_Csv = 5
};

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	unordered_map<string, int> conv_map = {
		{ "samples", Samples }
		,{ "samples_bin", Samples_Bin }
		,{ "features", Features }
		,{ "features_csv", Features_Csv }
		,{ "medmat_csv", MedMat_Csv }
	};
	string input_type; //may be "samples, features, samples_bin"

	void convert_type() {
		if (conv_map.find(input_type) == conv_map.end())
			HMTHROW_AND_ERR("couldn't find \"%s\" type. legal types are: %s\n", input_type.c_str(),
				medial::io::get_list(conv_map).c_str());
		inp_type = Input_types(conv_map[input_type]);
	}

	void post_process() {
		convert_type();
	}

public:
	string rep; ///<the repository if needed for age\gender cohorts
	string input; ///< the location to read input
	Input_types inp_type; ///< the input typeplease reffer to Input_types enum for options
	string output; ///< the location to write output
	string json_model; ///< json model for creating features for the confounders
	string bin_learned_model; ///< binary MedModel for creating features for the confounders
	string confounders_file; ///< the list of confounders
	string patient_groups_file; ///< the list of patient group with same order as samples
	string patient_action; ///< the list of patient group with same order as samples

	// bin spliting:
	string probabilty_bin_init; ///< the init line for probabilty binning (only in bin squezzing method)
	string features_bin_init; ///< the init line for features. if not empty and probabilty_bin_init not empty will so bin splitting(only in bin squezzing method)
	string model_type; ///< the model type
	string models_selection_file; ///< the model selection file with all params
	float method_price_ratio; ///< if -1 will do reweight. if 0 - no matching. otherwise matching with this price ratio.

	int nFolds_train; ///< the nFolds in training
	int nFolds_validation; ///< the nFolds in validation
	float min_probablity_cutoff; ///the minimal probabilty cutoff in reweighting
	string model_prob_clibrator; ///the init string for Calibration of model scores to prob
	string model_validation_type; ///the predictor type of the validation
	string model_validation_init; ///the predictor init line of the validation predictor
	float bootstrap_subsample; ///< bootstrap subsample param in each loop if nbotstrap>1
	int nbootstrap; ///< the number of bootstrap rounds
	int down_sample_max_cnt; ///< the maximal size of input to downsample to. if 0 won't do
	float change_action_prior; ///< If > 0 will change prior of action in the sample to be the given number
	float pairwise_matching_caliper; ///< If > 0 will do pairwise matching using caliper for std on prctile
	bool do_validation_outcome; ///< If True will do validation on outcome 
	int select_year; ///< if privided will filter to given year
	int age_bin; ///< If Provided will print stats by age bin

	ProgramArgs() {
		unsigned int row_size = (unsigned int)po::options_description::m_default_line_length;
		po::options_description desc("Basic options(input/output)", row_size * 2, row_size);
		string option_ls = "the input type (" + medial::io::get_list(conv_map) + ")";

		desc.add_options()

			("rep", po::value<string>(&rep)->required(), "the repository if needed for age\\gender cohorts")
			("input", po::value<string>(&input)->required(), "the location to read input")
			("input_type", po::value<string>(&input_type)->default_value("samples"), option_ls.c_str())
			("json_model", po::value<string>(&json_model)->default_value(""), "json model for creating features from samples to the matching process")
			("bin_learned_model", po::value<string>(&bin_learned_model)->default_value(""), "binary MedModel for creating features for the confounders")
			("confounders_file", po::value<string>(&confounders_file)->default_value(""), "the file with the list of confounders [TAB] binSettings init line")
			("patient_groups_file", po::value<string>(&patient_groups_file)->required(), "each sample and belongness - same order as input. use attr: to fetch from samples attrinute name")
			("patient_action", po::value<string>(&patient_action)->required(), "each sample and belongness - same order as input. use attr: to fetch from samples attrinute name")
			("output", po::value<string>(&output)->required(), "the location to write output");

		po::options_description desc2("Analyze options", row_size * 2, row_size);
		desc2.add_options()
			("down_sample_max_cnt", po::value<int>(&down_sample_max_cnt)->default_value(0), "the maximal size of input to downsample to. if 0 won't do")
			("change_action_prior", po::value<float>(&change_action_prior)->default_value(-1), "If > 0 will change prior of action in the sample to be the given number")
			("probabilty_bin_init", po::value<string>(&probabilty_bin_init)->default_value(""), "the init line for probabilty binning (only in bin squezzing method)")
			("features_bin_init", po::value<string>(&features_bin_init)->default_value(""), "the init line for features. if not empty and probabilty_bin_init not empty will so bin splitting(only in bin squezzing method)")
			("model_type", po::value<string>(&model_type)->default_value("xgb"), "the model type to learn")
			("models_selection_file", po::value<string>(&models_selection_file)->default_value(""), "the model selection file with all params")
			("method_price_ratio", po::value<float>(&method_price_ratio)->default_value(-1), "if -1 will do reweight. if 0 - no matching. otherwise matching with this price ratio")
			("pairwise_matching_caliper", po::value<float>(&pairwise_matching_caliper)->default_value(-1), "If > 0 will do pairwise matching using caliper for std on prctiles")
			("nFolds_train", po::value<int>(&nFolds_train)->default_value(5), "0 means use all. no train\\test. other number splits the matrix")
			("nFolds_validation", po::value<int>(&nFolds_validation)->default_value(5), "0 means use all. no train\\test. other number splits the matrix")
			("min_probablity_cutoff", po::value<float>(&min_probablity_cutoff)->default_value((float)0.005), "the minimal probabilty cutoff in reweighting")
			("model_validation_type", po::value<string>(&model_validation_type)->default_value("qrf"), "the predictor type of the validation")
			("model_validation_init", po::value<string>(&model_validation_init)->default_value("ntrees=100;maxq=500;spread=0.0001;min_node=50;ntry=4;get_only_this_categ=1;n_categ=2;type=categorical_entropy;learn_nthreads=1;predict_nthreads=1"), "the predictor init line of the validation predictor")
			("model_prob_clibrator", po::value<string>(&model_prob_clibrator)->default_value("calibration_type=isotonic_regression;min_preds_in_bin=200;min_prob_res=0.005"), "the init line for model probability calibrator")
			("bootstrap_subsample", po::value<float>(&bootstrap_subsample)->default_value(1), "bootstrap subsample param in each loop if nbotstrap>1")
			("nbootstrap", po::value<int>(&nbootstrap)->default_value(1), "bootstrap loop count")
			("do_validation_outcome", po::value<bool>(&do_validation_outcome)->default_value(false), "If True will do validation on outcome")
			("select_year", po::value<int>(&select_year)->default_value(0), "If given will filter samples only from specific year")
			("age_bin", po::value<int>(&age_bin)->default_value(0), "If Provided will print stats by age bin")
			;

		desc.add(desc2);

		string logo = "\
##     ## ######## ########  ####    ###    ## \n\
###   ### ##       ##     ##  ##    ## ##   ##    \n\
#### #### ##       ##     ##  ##   ##   ##  ##       \n\
## ### ## ######   ##     ##  ##  ##     ## ##       \n\
##     ## ##       ##     ##  ##  ######### ##       \n\
##     ## ##       ##     ##  ##  ##     ## ##       \n\
##     ## ######## ########  #### ##     ## ######## ";

		init(desc, logo);
	}

};
#endif
