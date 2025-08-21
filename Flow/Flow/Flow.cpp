//
// Flow -
// ---------------------------------------------------------------------------------------------------------
// The Flow App is intended to contain a complete tool set for creating a medical problem, build a model for it,
// create cross validation results for it and test its performace on cv results and test sets.
// It also contains some needed stat tools for parameters, and tools to create and change Repositories.
//
// In particular it has the following work modes:
// --rep_create			: to use for creating and changing a repository
// --rep_create_pids	: creating the transposed by-pid part of the repository
// --printall			: print all records for a specific pid (given in the --pid option)
// --pid_printall		: like --printall but using the faster by-pid API
// --describe			: print basic statistics on a signal (given in the --sig option)
// --convert_conf		: the .convert_config file for rep_create
// --rep				: repository to work with
// --pid				: pid to work with
// --sig				: sig name to work with
// --debug				: increase debug logs
// --output				: print csv results for signal
//
//==============================================================================================================
//==============================================================================================================


#include "Flow.h"
#include <InfraMed/InfraMed/InfraMed.h>
#include <InfraMed/InfraMed/MedConvert.h>
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedUtils/MedUtils/MedGenUtils.h>
#include <MedIO/MedIO/MedIO.h>
#include <boost/program_options.hpp>
#include <fenv.h>
#ifndef  __unix__
#pragma float_control( except, on )
#endif

#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
extern MedLogger global_logger;

namespace po = boost::program_options;
using namespace std;
using namespace boost;

void FlowAppParams::post_process() {
	options.resize(MAX_OPTION, 0);
	//switches:
	if (rep_create) options[OPTION_REP_CREATE] = 1;
	if (rep_create_pids) options[OPTION_REP_CREATE_PIDS] = 1;
	if (printall) options[OPTION_PRINTALL] = 1;
	if (pid_printall) options[OPTION_PID_PRINTALL] = 1;
	if (pids_printall) options[OPTION_PIDS_PRINTALL] = 1;
	if (print_pids) options[OPTION_PRINT_PIDS] = 1;
	if (print) options[OPTION_PRINT] = 1;
	if (pid_print) options[OPTION_PID_PRINT] = 1;
	if (describe) options[OPTION_DESCRIBE] = 1;
	if (describe_all) options[OPTION_DESCRIBE_ALL] = 1;
	if (sig_print) options[OPTION_SIG_PRINT] = 1;
	if (sig_print_raw) options[OPTION_SIG_PRINT_RAW] = 1;
	if (generate_features) options[OPTION_GENERATE_FEATURES] = 1;
	if (extract_pids_in_set) options[OPTION_EXTRACT_PIDS_IN_SET] = 1;
	if (learn_matrix) options[OPTION_LEARN_MATRIX] = 1;
	if (train_test) options[OPTION_TRAIN_TEST] = 1;
	if (samples_scan_sigs) options[OPTION_SCAN_SIGS_FOR_SAMPLES] = 1;
	if (filter_and_match) options[OPTION_FILTER_AND_MATCH] = 1;
	if (get_model_preds) options[OPTION_GET_MODEL_PREDS] = 1;
	if (simple_train) options[OPTION_SIMPLE_TRAIN] = 1;
	if (simple_test) options[OPTION_SIMPLE_TEST] = 1;
	if (get_json_mat) options[OPTION_GET_JSON_MAT] = 1;
	if (get_mat) options[OPTION_GET_MAT] = 1;
	if (print_processors) options[OPTION_PRINT_PROCESSORS] = 1;
	if (print_model_info) options[OPTION_MODEL_INFO] = 1;
	if (rewrite_object) options[OPTION_REWRITE_OBJECT] = 1;
	if (calc_kaplan_meir) options[OPTION_CALC_KAPLAN_MEIR] = 1;
	if (export_production_model) options[OPTION_EXPORT_PRODUCTION] = 1;
	if (rep_processor_print) options[OPTION_REP_PROCESSOR_PRINT] = 1;
	if (model_dep) options[OPTION_MODEL_DEP] = 1;
	if (relabel) options[OPTION_RELABEL] = 1;
	if (shap_val_request) options[OPTION_SHAP] = 1;
	if (export_predictor) options[OPTION_EXPORT_PREDICTOR] = 1;
	if (print_model_signals) options[OPTION_PRINT_MDOEL_SIGNALS] = 1;
	if (clean_dict) options[OPTION_CLEAN_DICT] = 1;
	if (show_category_info) options[OPTION_SHOW_CATEGORY_INFO] = 1;
	if (add_splits_to_samples) options[OPTION_ADD_SPLITS_TO_SAMPLES] = 1;
	if (get_propensity_weights) options[OPTION_GET_PROPENSITY_WEIGHTS] = 1;
	if (get_feature_group) options[OPTION_GET_FEAT_GROUP] = 1;
	if (show_names) options[OPTION_SHOW_NAMES] = 1;
	if (tt_predictor_on_matrix) options[OPTION_TT_PREDICTOR_ON_MAT] = 1;
	if (algomarker_dict) options[OPTION_AM_DICT] = 1;
	if (compare_mat) options[OPTION_CMP_MATRIX] = 1;
	if (predict_on_mat) options[OPTION_PREDICT_ON_MAT] = 1;
	if (rename_model_signal) options[OPTION_RENAME_MODEL_SIGNAL] = 1;
	if (flat_category_vals) options[OPTION_FLAT_CATEGORY_VALS] = 1;
	if (fit_model_to_rep) options[OPTION_FIT_MODEL_TO_REP] = 1;

	if (cohort_incidence != "") options[OPTION_COHORT_INCIDENCE] = 1;
	if (cohort_sampling != "") options[OPTION_COHORT_SAMPLING] = 1;
	//	if (outcome_params != "") options[OPTION_CREATE_OUTCOME] = 1;
	//	if (match_params != "") options[OPTION_MATCH_OUTCOME] = 1;
	//	if (filter_params != "") options[OPTION_FILTER_OUTCOME] = 1;
	if (split_params != "") options[OPTION_CREATE_SPLITS] = 1;

	//if (debug)
	//	global_logger.init_all_levels(0);
	if (debug) {
		global_logger.levels[LOG_MED_MODEL] = 0;
		global_logger.levels[LOG_REPCLEANER] = 0;
	}
	//global_logger.levels[LOG_DICT] = LOG_DEF_LEVEL;

	// adding work_dir to input/output files
	if (work_dir != "") {
		for (string* ps : { &outcome_fname , &matched_outcome_fname, &filtered_outcome_fname, &split_fname, &features_fname,
			&matrix_fname, &label_matrix_fname, &train_test_learning_samples_fname, &train_test_validation_samples_fname })
			if (ps->size() > 1 && (*ps)[0] != '/' && (*ps)[1] != ':') {
				MLOG("adding work_dir [%s] to [%s]\n", work_dir.c_str(), ps->c_str());
				*ps = (work_dir + "/" + *ps);
			}
	}
	set_rand_seed(random_seed);
}

//=============================================================================
FlowAppParams::FlowAppParams()
{
	unsigned int row_size = (unsigned int)po::options_description::m_default_line_length;
	po::options_description desc("Main Program Options - General switches", row_size * 2, row_size);
	desc.add_options()
		// repository creation
		("rep_create", po::bool_switch(&rep_create), "create a new repository")
		// create transposed pids repository 
		("rep_create_pids", po::bool_switch(&rep_create_pids), "create a transpose by-pid index and data for an exisiting repository (no additional args, only rep)")
		// print all data for a pid using a regular repository
		("printall", po::bool_switch(&printall), "print all pid records (give pid and rep)")
		// print all data for a pid using a transposed repository (faster in theory)
		("pid_printall", po::bool_switch(&pid_printall), "print all pid records using by-pid API (give pid and rep)")
		// ??
		("pids_printall", po::bool_switch(&pids_printall), "print all records for all pids using by-PID API")
		("print_pids", po::bool_switch(&print_pids), "print pid list of all pids that have a certain signal")
		("print", po::bool_switch(&print), "print records for a pid,sig")
		("pid_print", po::bool_switch(&pid_print), "print records for a pid,sig using by-PID API")
		("describe", po::bool_switch(&describe), "get basic overall statistics for a sig")
		("describe_all", po::bool_switch(&describe_all), "get basic overall statistics for all signals")
		("sig_print", po::bool_switch(&sig_print), "print signal")
		("pids_sigs_print_raw", po::bool_switch(&sig_print_raw), "print raw signal for all pids in repo in csv format")
		("generate_features", po::bool_switch(&generate_features), "generate the features from json(do learn&apply) or binary learned model(only apply) for the samples f_outcome and writes csv matrix")
		("extract_pids_in_set", po::bool_switch(&extract_pids_in_set), "extract all pid, min(date) that have a value in this set in the specified signals")
		("train_test", po::bool_switch(&train_test), "run in train-test mode")
		("learn_matrix", po::bool_switch(&learn_matrix), "mode of learning of a given set of matrices")
		("samples_scan_sigs", po::bool_switch(&samples_scan_sigs), "counting which sigs appear in data for a given sample (use rep and f_outcome)")
		("filter_and_match", po::bool_switch(&filter_and_match), "samples filter and match")
		("get_model_preds", po::bool_switch(&get_model_preds), "get prediction for a model file (in f_model) on a given samples file (in f_samples) and write it to preds file (in f_preds) , optional: add f_pre_json for pre_processors json file")
		("simple_train", po::bool_switch(&simple_train), "train a model given rep , a samples file (in_samples) , a json file (f_json) , and writes model to a file (f_model), can do it on a split (split)")
		("simple_test", po::bool_switch(&simple_test), "test a model given rep , a samples file (in_samples) , writes preds to a file (f_pred), can do it on a split(split)")
		("get_json_mat", po::bool_switch(&get_json_mat), "get matrix for a model defined as json (in f_json) on a given samples file (in f_samples) and write it to a mat file (in f_matrix)")
		("get_mat", po::bool_switch(&get_mat), "get matrix for a model file (in f_model) on a given samples file (in f_samples) and write it to a mat file (in f_matrix)")
		("print_processors", po::bool_switch(&print_processors), "print the processors (in particular: cleaners) information of the model given in f_model")
		("print_model_info", po::bool_switch(&print_model_info), "print general info on the given model (signals, rep processors, features, etc...). The model is given in f_model")
		("rewrite_object", po::bool_switch(&rewrite_object), "rewrites binary object (reads unsafe, without checking version and writing it down again)")
		("calc_kaplan_meir", po::bool_switch(&calc_kaplan_meir), "calc kaplan_meir on MedSamples")
		("export_production_model", po::bool_switch(&export_production_model), "If true will read and write MedModel for production")
		("rep_processor_print", po::bool_switch(&rep_processor_print), "If true will print compare of signals with 2 rep processors (one can be none\\empty)")
		("model_dep", po::bool_switch(&model_dep), "If true will check dependency for sig and model(json or binary) - who requires it")
		("relabel", po::bool_switch(&relabel), "If true will relabel MedSamples using registries and labeling params")
		("shap_val_request", po::bool_switch(&shap_val_request), "If true will print shapley values on model")
		("export_predictor", po::bool_switch(&export_predictor), "convert predictor from MedModel to python readable")
		("print_model_signals", po::bool_switch(&print_model_signals), "prints model signals in used")
		("clean_dict", po::bool_switch(&clean_dict), "take a new set dict file and clear undefined sets from it")
		("show_category_info", po::bool_switch(&show_category_info), "When on will use rep , sig and categorical value and print hirerachy - up and down all codes in the tree")
		("add_splits_to_samples", po::bool_switch(&add_splits_to_samples), "add splits to a sample file from a splits file, use f_split and f_samples")
		("get_propensity_weights", po::bool_switch(&get_propensity_weights), "calculate propensity weights for rep,samples,calibrated model and stores in sample weights field")
		("get_feature_group", po::bool_switch(&get_feature_group), "get the name of the group for a feature - same logic in explainers")
		("show_names", po::bool_switch(&show_names), "get the all names for a specific value for signal")
		("tt_predictor_on_matrix", po::bool_switch(&tt_predictor_on_matrix), "train test MedPredictor when we have feature matrix")
		("algomarker_dict", po::bool_switch(&algomarker_dict), "Creates Json dict for AlgoMarker testing. Additionl load value on rep")
		("compare_mat", po::bool_switch(&compare_mat), "Compares 2 matrices")
		("predict_on_mat", po::bool_switch(&predict_on_mat), "Apply MedPredictor on matrix")
		("rename_model_signal", po::bool_switch(&rename_model_signal), "Rename model signal")
		("flat_category_vals", po::bool_switch(&flat_category_vals), "Get flat list of codes from list of codes")
		("fit_model_to_rep", po::bool_switch(&fit_model_to_rep), "Will recieve rep and f_model, and will make adjustment in model to be applied for rep if possible and will check for errors, output modle will be store in f_output")
		;

	po::options_description desc_global("global options", row_size * 2, row_size);
	desc_global.add_options()
		("rep", po::value<string>(&rep_fname)->default_value("//you/need/to/fill/the/rep/parameter"), "repository file name")
		("work_dir", po::value<string>(&work_dir)->default_value(""), "work dir for all files besides repository and convert_conf, used only when not empty")
		("f_label_matrix", po::value<string>(&label_matrix_fname)->default_value("//you/need/to/fill/the/matrix_fname/parameter"), "matrix file name")
		("f_features", po::value<string>(&features_fname)->default_value("//you/need/to/fill/the/features_fname/parameter"), "features file name")
		("global_time_unit", po::value<string>(&global_time_unit)->default_value(""), "if not empty will set global_time_unit first thing")
		("global_win_time_unit", po::value<string>(&global_win_time_unit)->default_value(""), "if not empty will set global_win_time_unit first thing")
		("seed", po::value<int>(&random_seed)->default_value(1948), "random generator seed")
		("catch_fe_exceptions", po::value<bool>(&catch_fe_exceptions)->default_value(false), "If true will not crash in arithmetic exceptions")
		;

	po::options_description desc2("describe_all options(switch)", row_size * 2, row_size);
	desc2.add_options()
		("signals_fname", po::value<string>(&signals_fname)->default_value(""), "file with list of signals")
		("date_min", po::value<int>(&date_min)->default_value(20000101), "date_min")
		("date_max", po::value<int>(&date_max)->default_value(20170101), "date_max")
		("age_min", po::value<int>(&age_min)->default_value(40), "age_min")
		("age_max", po::value<int>(&age_max)->default_value(100), "age_max");

	po::options_description desc6("pids_printall options(switch)", row_size * 2, row_size);
	desc6.add_options()
		("codes_to_signals_fname", po::value<string>(&codes_to_signals_fname)->default_value(""), "codes_to_signals file, used to map the signal name to its original name in the repo load files format")
		("output", po::value<string>(&outputFormat)->default_value("text"), "output format to print out signal/patient (csv/html/text/repo_load_format)")
		("in_samples", po::value<string>(&in_samples_file)->default_value("//you/need/to/fill/the/in_samples/parameter"), "in samples file name");

	po::options_description desc7("pid_printall options(switch)", row_size * 2, row_size);
	desc7.add_options()
		("GLOBAL7.codes_to_signals_fname", "codes_to_signals file, used to map the signal name to its original name in the repo load files format")
		("GLOBAL7.output", "output format to print out signal/patient (csv/html/text/repo_load_format)")
		("pid", po::value<int>(&pid)->default_value(2), "pid number");

	// creating pid splits
	// train is a bit mask 1=70%, 2=20%, 4=10% (so entire population = 7)
	// example: nsplits=6,train=7,gender=3
	po::options_description desc8("create_splits options(to active fill create_splits)", row_size * 2, row_size);
	desc8.add_options()
		("create_splits", po::value<string>(&split_params)->default_value(""), "create a split for a repository/outcome with given params  example: nsplits=6,train=7,gender=3")
		("f_split", po::value<string>(&split_fname)->default_value(""), "split file name - or simply number of splits to use splits from samples file!")
		;

	// create , read and write matrices
	po::options_description desc9("generate_features options(switch)", row_size * 2, row_size);
	desc9.add_options()
		("f_matrix", po::value<string>(&matrix_fname)->default_value("//you/need/to/fill/the/matrix_fname/parameter"), "matrix file name")
		("model_init_fname", po::value<string>(&model_init_fname)->default_value("//you/need/to/fill/the/model_init_fname/parameter"), "model json file ")
		("train_test_json_alt", po::value<vector<string>>(&train_test_json_alt)->composing(), "(multiple) alterations to model json file")
		("f_model", po::value<string>(&f_model)->default_value("//you/need/to/fill/the/f_model/parameter"), "model file name")
		("f_outcome", po::value<string>(&outcome_fname)->default_value("//you/need/to/fill/the/f_outcome/parameter"), "f_outcome - outcome file name");

	// train_test example cycle from a config file to get quick results
	po::options_description desc10("train_test options(switch)", row_size * 2, row_size);
	desc10.add_options()
		("train_test_conf", po::value<string>(&train_test_conf_fname)->default_value(""), "train_test config file (optional)")
		("train_test_learning_samples_fname", po::value<string>(&train_test_learning_samples_fname)->default_value(""), "overrides LEARNING_SAMPLES in train_test config")
		("train_test_validation_samples_fname", po::value<string>(&train_test_validation_samples_fname)->default_value(""), "overrides VALIDATION_SAMPLES in train_test config")
		("train_test_model_init_fname", po::value<string>(&train_test_model_init_fname)->default_value(""), "overrides MODEL_INIT_FILE in train_test config")
		("train_test_prefix", po::value<string>(&train_test_prefix)->default_value(""), "overrides PREFIX in train_test config")
		("train_test_validation_prefix", po::value<string>(&train_test_validation_prefix)->default_value(""), "overrides VALIDATION_PREFIX in train_test config")
		("train_test_preds_format", po::value<string>(&train_test_preds_format)->default_value("csv"), "overrides PREDS_FORMAT in train_test config")
		("train_test_save_matrix", po::value<string>(&train_test_save_matrix)->default_value(""), "overrides SAVE_MATRIX in train_test config")
		("train_test_save_contribs", po::value<string>(&train_test_save_contribs)->default_value("none"), "overrides SAVE_CONTRIBS in train_test config")
		("train_test_save_matrix_splits", po::value<string>(&train_test_save_matrix_splits)->default_value("all"))
		("cv_on_train1", po::value<string>(&cv_on_train1)->default_value(""), "overrides CV_ON_TRAIN1 in train_test config")
		("steps", po::value<string>(&steps)->default_value(""), "overrides STEPS in train_test config")
		("active_splits", po::value<string>(&active_splits)->default_value(""), "overrides ACTIVE_SPLITS in train_test config")
		("pred_params_fname", po::value<string>(&pred_params_fname)->default_value(""), "Optional - Grid search parameters file. Overrides PREDECITOR_PARAMS_FILE in train_test config");


	po::options_description desc11("extract_pids_in_set options(switch)", row_size * 2, row_size);
	desc11.add_options()
		("f_output", po::value<string>(&output_fname)->default_value("output.html"), "output filename to print out signal (default is output.html)")
		("sig", po::value<string>(&sig_name)->default_value("Hemoglobin"), "signal name")
		("sig_section", po::value<string>(&sig_section)->default_value("RC_Diagnosis"), "repo section for dictionaries")
		("sig_val", po::value<string>(&sig_val)->default_value(""), "signal value")
		("sig_set", po::value<string>(&sig_set)->default_value(""), "set with signal values");

	po::options_description desc12("sig_print options(switch)", row_size * 2, row_size);
	desc12.add_options()
		("bin_method", po::value<string>(&bin_method)->default_value("split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0.1"), "bin method to use. split_method=[same_width|partition_mover|iterative_merge|dynamic_split]")
		("sampleCnt", po::value<int>(&sampleCnt)->default_value(0), "sampleCnt - how much samples to take from each patient. (0=no sampling take all)")
		("maxPids", po::value<int>(&maxPids)->default_value(0), "maxPids - how many patients to take (0=take all pids in repository)")
		("gender", po::value<int>(&gender)->default_value(0), "gender filter (0-none,1-male,2-female)")
		("filterCnt", po::value<float>(&filterCnt)->default_value((float)0.00005), "filterCnt - threshold filter bin frequency")
		("normalize", po::value<int>(&normalize)->default_value(1), "normalize histogram - make probability")
		("GLOBAL12.age_min", "age_min")
		("GLOBAL12.age_max", "age_max")
		("GLOBAL12.sig", "signal name")
		("GLOBAL12.output", "can be csv,html")
		("GLOBAL12.f_output", "output filename to print out signal (default is output.html)")
		;

	po::options_description desc13("printall options(switch)", row_size * 2, row_size);
	desc13.add_options()
		("ignore_signals", po::value<vector<string>>(&ignore_signals)->composing(), "(multiple) signals to ignore when printing")
		("GLOBAL13.pid", "pid number")
		("GLOBAL13.output", "output format to print out signal/patient (csv/html/text/repo_load_format)");

	// running a model on prepared matrices
	po::options_description desc14("learn_matrix options(switch)", row_size * 2, row_size);
	desc14.add_options()
		("f_xtrain", po::value<string>(&xtrain_fname)->default_value(""), "xtrain file name, learn_matrix mode")
		("f_ytrain", po::value<string>(&ytrain_fname)->default_value(""), "ytrain file name, learn_matrix mode")
		("f_xtest", po::value<string>(&xtest_fname)->default_value(""), "xtest file name, learn_matrix mode")
		("f_ytest", po::value<string>(&ytest_fname)->default_value(""), "ytest file name, learn_matrix mode")
		("learn_model", po::value<string>(&learn_model)->default_value(""), "model to learn: linear_model, xgb, qrf, etc...")
		("learn_model_params", po::value<string>(&learn_model_params)->default_value(""), "ytest file name, learn_matrix mode");

	// general params
	po::options_description desc15("print_pids options(switch)", row_size * 2, row_size);
	desc15.add_options()
		("GLOBAL15.sig", "signal name"); //second use;

	po::options_description desc16("rep_create options(switch)", row_size * 2, row_size);
	desc16.add_options()
		("convert_conf", po::value<string>(&convert_conf_fname)->default_value("//you/need/to/fill/the/convert_conf/parameter"), "convert config file name")
		("load_err_file", po::value<string>(&load_err_file)->default_value(""), "Error log path file to document all loading process errors")
		("load_args", po::value<string>(&load_args)->default_value("check_for_error_pid_cnt=0;allowed_missing_pids_from_forced_ratio=0.05;max_bad_line_ratio=0.05;allowed_unknown_catgory_cnt=50"), "Additional arguments for loading process")
		;

	// samples filter and match
	po::options_description desc17("filter_and_match options(switch)", row_size * 2, row_size);
	desc17.add_options()
		("GLOBAL17.in_samples", "input samples file path")
		("out_samples", po::value<string>(&out_samples_file)->default_value("//you/need/to/fill/the/out_samples/parameter"), "out samples file name")
		("filter_params", po::value<string>(&samples_filter_params)->default_value(""), "samples filter params")
		("match_params", po::value<string>(&samples_match_params)->default_value(""), "match filter params");

	po::options_description desc18("cohort_sampling options (to active fill cohort_sampling arg)", row_size * 2, row_size);
	desc18.add_options()
		("cohort_sampling", po::value<string>(&cohort_sampling)->default_value(""), "cohort sampling parameters (rep taken from --rep if not given)")
		("cohort_fname", po::value<string>(&cohort_fname)->default_value(""), "cohort file name")
		("GLOBAL18.out_samples", "out samples file name");

	// working with cohort files
	po::options_description desc20("cohort_incidence option(to active fill cohort_incidence)", row_size * 2, row_size);
	desc20.add_options()
		("cohort_incidence", po::value<string>(&cohort_incidence)->default_value(""), "cohort incidence parameters (rep taken from --rep if not given)")
		("out_incidence", po::value<string>(&incidence_fname)->default_value(""), "cohort incidence output file")
		("GLOBAL20.cohort_fname", "cohort_fname - cohort file name")
		("cohort_medregistry", po::value<bool>(&cohort_medregistry)->default_value(true), "it true input is MedRegistry and not MedCohort")
		("use_kaplan_meir", po::value<bool>(&use_kaplan_meir)->default_value(true), "if true will use kaplan meir calc - works on MedRegistry only")
		("sampler_params", po::value<string>(&sampler_params)->default_value(""), "sampler params to override")
		("labeling_param", po::value<string>(&labeling_param)->default_value(""), "labeler params")
		("censor_reg", po::value<string>(&censor_reg)->default_value(""), "censor reg")
		("censor_sig", po::value<string>(&censor_sig)->default_value(""), "censor signal - like MEMBERSHIP in KP")
		;


	// a direct option to get prediction of a model on a given samples file
	// Does not check anything (such as splits and such) simply gives predictions. Good for when checking model from one database on another
	// usage --get_model_preds --f_model <serialized model file> --f_samples <samples file> --f_preds <output preds>
	po::options_description desc21("get_model_preds option(switch)", row_size * 2, row_size);
	desc21.add_options()
		("GLOBAL21.f_model", "model file name")
		("f_samples", po::value<string>(&f_samples)->default_value("//you/need/to/fill/the/f_samples/parameter"), "samples file name")
		("f_preds", po::value<string>(&f_preds)->default_value("//you/need/to/fill/the/f_preds/parameter"), "preds file name")
		("f_pre_json", po::value<string>(&f_pre_json)->default_value(""), "if not empty: will add pre_processors to model from this json file")
		("only_post_processors", po::value<bool>(&only_post_processors)->default_value(false), "If true will get samples with preds and only apply post processors")
		("GLOBAL21.print_attr", "If 1 will output attributes (default is 0)")
		("change_model_init", po::value<string>(&change_model_init)->default_value(""), "init argument to change the model in runtime")
		("change_model_file", po::value<string>(&change_model_file)->default_value(""), "json file to read multiple changes to the model in runtime - should have \"changes\" element with array of change requests")
		;

	// a direct option to train a model on a given samples file
	// Does not check anything (such as splits and such) simply trains.
	// usage --simple_train --rep <repository> --f_samples <samples to train on> --f_json <model json file> --f_model <output model file>  --f_matrix <optional: write train matrix as csv>
	po::options_description desc22("simple_train(switch) or simple_test(switch) or get_json_mat (just generating the matrix) or no_matrix_retrain (switch) option added", row_size * 2, row_size);
	desc22.add_options()
		("GLOBAL22.f_model", "output model file name")
		("GLOBAL22.f_samples", "samples to train on file name")
		("f_json", po::value<string>(&f_json)->default_value("//you/need/to/fill/the/f_json/parameter"), "json file name")
		("GLOBAL22.f_matrix", "csv train matrix output")
		("no_matrix_retrain", po::bool_switch(&no_matrix_retrain), "use only with simple_train, if on you must provide both f_model (will be in and out !) and f_json (to define the new predictor)")
		("split", po::value<int>(&split)->default_value(-1), "split to train(test) on: if -1 will use all samples.")
		("predictor", po::value<string>(&predictor)->default_value(""), "predictor can be given directly in --no_matrix_retrain option")
		("predictor_params", po::value<string>(&predictor_params)->default_value(""), "predictor_params can be given directly in --no_matrix_retrain option")
		("GLOBAL22.stop_step", "Where to stop the apply. default 0 to run till the end")
		("GLOBAL22.train_test_json_alt", "(multiple) alterations to model json file")

		;

	// a direct option to get the matrix of a model of some samples
	po::options_description desc23("get_mat option(switch)", row_size * 2, row_size);
	desc23.add_options()
		("GLOBAL23.f_model", "model file name")
		("GLOBAL23.f_samples", "samples file name")
		("GLOBAL23.f_matrix", "output matrix file name")
		("GLOBAL23.f_pre_json", "if not empty: will add pre_processors to model from this json file")
		("select_features", po::value<string>(&select_features)->default_value(""), "select_features : list of strings to select features for the matrix (optional)")
		("print_attr", po::value<bool>(&print_attr)->default_value(false), "If True will output attributes")
		("stop_step", po::value<int>(&stop_step)->default_value(0), "Where to stop the apply. default 0 to run till the end")
		("GLOBAL23.change_model_init", "init argument to change the model in runtime")
		("GLOBAL23.change_model_file", "json file to read multiple changes to the model in runtime - should have \"changes\" element with array of change requests")
		;

	po::options_description desc24("print|pid_print option(switch)", row_size * 2, row_size);
	desc24.add_options()
		("GLOBAL24.pid", "pid number")
		("GLOBAL24.sig", "signal name");

	po::options_description desc25("describe option(switch)", row_size * 2, row_size);
	desc25.add_options()
		("GLOBAL25.sig", "signal name") //second use
		("GLOBAL25.date_min", "date_min") //second use
		("GLOBAL25.date_max", "date_max") //second use
		("GLOBAL25.age_min", "age_min") //second use
		("GLOBAL25.age_max", "age_max") //second use
		;

	po::options_description desc26("pids_sigs_print_raw option(switch)", row_size * 2, row_size);
	desc26.add_options()
		("pids", po::value<string>(&pids)->default_value(""), "pids list with \",\" or \";\" of not given will take all")
		("sigs", po::value<string>(&sigs)->default_value("Hemoglobin"), "signal names with \",\" or \";\"")
		("limit_count", po::value<int>(&limit_count)->default_value(3), "the maximal number to print names in dictionary")
		("time", po::value<int>(&time)->default_value(20990101), "the time point to apply model_rep_processors at")
		("model_rep_processors", po::value<string>(&model_rep_processors)->default_value(""), "If given will load rep_processors to manipulate repository before printing")
		("GLOBAL26.f_samples", "if given will use this file to choose patient ids")
		; 

	po::options_description desc27("samples_scan_sigs option(switch)", row_size * 2, row_size);
	desc27.add_options()
		("GLOBAL27.f_outcome", "outcome file name");

	po::options_description desc28("print_processors option(switch)", row_size * 2, row_size);
	desc28.add_options()
		("GLOBAL28.f_model", "model file name")
		;

	po::options_description desc29("print_model_info option(switch)", row_size * 2, row_size);
	desc29.add_options()
		("GLOBAL29.f_model", "model file name")
		("predictor_type", po::value<string>(&predictor_type)->default_value(""), "predictor type - for overriding predictor if given with model_predcitor_path")
		("model_predictor_path", po::value<string>(&model_predictor_path)->default_value(""), "predictor path - for overriding predictor if given with model_predcitor_path")
		("importance_param", po::value<string>(&importance_param)->default_value(""), "params to pass the importance")
		("GLOBAL29.f_matrix", "features mat (for SHAP values feature importance) - in MedMat csv format.")
		("GLOBAL29.f_samples", "samples file name for SHAP values")
		("GLOBAL29.rep", "rep - repository. Used when samples file is given for calculating SHAP feature importance")
		("GLOBAL29.max_samples", "if > 0 : how many samples to subsample if matrix is large - to speedup")
		("print_json_format", po::value<bool>(&print_json_format)->default_value(false), "If true will print json format into f_output")
		("GLOBAL29.f_output", "path to store json object of model")
		;

	po::options_description desc30("rewrite_object option(switch)", row_size * 2, row_size);
	desc30.add_options()
		("GLOBAL30.f_model", "model file name")
		("object_type", po::value<string>(&object_type)->default_value("MedModel"), "The object Type to serialize")
		("GLOBAL30.f_output", "output filename to print out new model")
		;

	po::options_description desc31("calc_kaplan_meir option(switch)", row_size * 2, row_size);
	desc31.add_options()
		("GLOBAL31.in_samples", "input samples file name")
		("time_period", po::value<int>(&time_period)->default_value(365), "time period for kaplan meir")
		;

	po::options_description desc32("export_production_model option(switch)", row_size * 2, row_size);
	desc32.add_options()
		("GLOBAL32.f_model", "model file path")
		("GLOBAL32.f_output", "output model path")
		("GLOBAL32.predictor_type", "for overriding predictor if given with model_predcitor_path")
		("GLOBAL32.model_predictor_path", "for overriding predictor if given with model_predcitor_path")
		("minimize_model", po::value<bool>(&minimize_model)->default_value(true), "If true will remove uneeded rep_processors and feature generators")
		("cleaner_verbose", po::value<int>(&cleaner_verbose)->default_value(1), "activates/deactivates logging (-1 - deactivates, 0 - no change, 1- activate logging)")
		;

	po::options_description desc33("rep_processor_print option(switch)", row_size * 2, row_size);
	desc33.add_options()
		("GLOBAL33.pids", "optional list of pids")
		("GLOBAL33.sigs", "list of sigs (Required)")
		("GLOBAL33.seed", "random seed")
		("GLOBAL33.f_output", "output file location")
		("cleaner_path_before", po::value<string>(&cleaner_path_before)->default_value(""), "the cleaners path before to compare")
		("cleaner_path", po::value<string>(&cleaner_path)->default_value("/server/Work/Users/Alon/UnitTesting/examples/general_config_files/Cleaner/full_cleaners.json"), "the cleaners path")
		("max_examples", po::value<int>(&max_examples)->default_value(0), "maximum number of examples to print for each signal with filtered records - 0 (prints all)")
		("show_all_changes", po::value<bool>(&show_all_changes)->default_value(false), "If true will print all changes. default is to skip cleaning of zeros.")
		;

	po::options_description desc34("model_dep option(switch)", row_size * 2, row_size);
	desc34.add_options()
		("GLOBAL34.sig", "the signal to search")
		("GLOBAL34.f_model", "the binary model")
		("GLOBAL34.f_json", "the json model")
		;

	po::options_description desc35("relabel option(switch)", row_size * 2, row_size);
	desc35.add_options()
		("GLOBAL35.in_samples", "the MedSamples to relabel")
		("GLOBAL35.out_samples", "output file location for the new MedSamples")
		("GLOBAL35.cohort_fname", " - the registry")
		("GLOBAL35.censor_reg", "the censor registry")
		("GLOBAL35.labeling_param", "the labeling parameters")
		("GLOBAL35.censor_sig", "the censor registry in signal (if given, rep is also needed)")
		;

	po::options_description desc36("shap_val_request option(switch)", row_size * 2, row_size);
	desc36.add_options()
		("GLOBAL36.f_model", "model file name")
		("GLOBAL36.f_matrix", "features mat (for SHAP values feature importance) - in MedMat csv format.")
		("GLOBAL36.f_samples", "samples file name for SHAP values")
		("GLOBAL36.rep", "repository. Used when samples file is given for calculating SHAP feature importance")
		("max_samples", po::value<int>(&max_samples)->default_value(0), "if > 0 : how many samples to subsample if matrix is large - to speedup")
		("group_ratio", po::value<float>(&group_ratio)->default_value((float)0.2), "group size aroung prctile")
		("group_cnt", po::value<int>(&group_cnt)->default_value(3), "how many groups")
		("group_names", po::value<string>(&group_names)->default_value(""), "names groups with ,")
		("GLOBAL36.normalize", "to normalize each prediction to sum score")
		("bin_uniq", po::value<bool>(&bin_uniq)->default_value(true), "whether to bin groups without respect to the distribution - only by values")
		("normalize_after", po::value<bool>(&normalize_after)->default_value(true), "If true, will do the normalization to percentage after sum of all contribs from all data - The global feature importance will sum to 100")
		("remove_b0", po::value<bool>(&remove_b0)->default_value(true), "If true, will remove b0 contrib if exists")
		("group_signals", po::value<string>(&group_signals)->default_value(""), "a file to signals to group by or BY_SIGNAL or BY_SIGNAL_CATEG to group by signals or group by signal and support diffrent categ values")
		("relearn_predictor", po::value<bool>(&relearn_predictor)->default_value(false), "If true will retrain predictor on samples")
		("keep_imputers", po::value<bool>(&keep_imputers)->default_value(false), "If True will use the model imputer if exists in the shapley report")
		("zero_missing_contrib", po::value<bool>(&zero_missing_contrib)->default_value(false), "If true will zero the contribution of missing values")
		("GLOBAL36.f_json", "json model to filter the samples")
		("cohort_filter", po::value<string>(&cohort_filter)->default_value(""), "Parameter to control filtering of the samples in a bootstrap format settings")
		("GLOBAL36.bin_method", "bining method to bin each feature")
		("GLOBAL36.f_output", "the output file location to write")
		;

	po::options_description desc37("export_predictor option(switch)", row_size * 2, row_size);
	desc37.add_options()
		("GLOBAL37.f_model", "MedModel file")
		("GLOBAL37.f_output", "Output model")
		;

	po::options_description desc38("print_model_signals option(switch)", row_size * 2, row_size);
	desc38.add_options()
		("GLOBAL38.f_model", "MedModel file")
		("GLOBAL38.rep", "the repository path")
		("output_dict_path", po::value<string>(&output_dict_path)->default_value(""), "Output path for dict. defintions used in the model")
		("transform_rep", po::value<bool>(&transform_rep)->default_value(false), "It true will be ran on target rep to create init dicts to transform")
		;

	po::options_description desc39("clean_dict option(switch)", row_size * 2, row_size);
	desc39.add_options()
		("GLOBAL39.rep", "the repository path")
		("GLOBAL39.output_dict_path", "full input path for dictionary to clean")
		("GLOBAL39.f_output", "full output path for cleaned dictionary")
		;

	po::options_description desc40("show_category_info option(switch)", row_size * 2, row_size);
	desc40.add_options()
		("GLOBAL40.rep", "rep - the repository path")
		("GLOBAL40.sig", "the signal to search for category")
		("GLOBAL40.sig_val", "the signal value")
		;

	po::options_description desc41("get_propensity_weights option(switch)", row_size * 2, row_size);
	desc41.add_options()
		("GLOBAL41.rep", "the repository path")
		("GLOBAL41.f_model", "the calibrated propensity model")
		("GLOBAL41.f_samples", "the input samples (can also have preds inside)")
		("GLOBAL41.f_matrix", "the input MedFeatures (will not use samples and repository in this mode)")
		("GLOBAL41.f_preds", "the output samples with the weights")
		("max_propensity_weight", po::value<double>(&max_propensity_weight)->default_value(0), "the maximal weight cutoff to give sample. If 0 no limit")
		("trim_propensity_weight", po::value<bool>(&trim_propensity_weight)->default_value(false), "Used when max_propensity_weight>0. If true will trim the weight to max_propensity_weight, otherwise will exclude by giving zero weight")
		("prop_attr_weight_name", po::value<string>(&prop_attr_weight_name)->default_value("weight"), "attribute name to store in the final samples")
		("override_outcome", po::value<int>(&override_outcome)->default_value(-1), "If 0 - will treat all samples as control. If 1 will treat all as cases. if -1 - will use outcome in samples")
		("GLOBAL41.f_json", "[Optional] json model to calculate feature and take it instead of sample outcome for propensity calculation")
		("propensity_feature_name", po::value<string>(&propensity_feature_name)->default_value(""), "If f_json is given will select this feature instead of outcome")
		("propensity_sampling", po::value<bool>(&propensity_sampling)->default_value(false), "If true will sample by the propenstity weights (will dividide all by max weight and sample)")
		("do_conversion", po::value<bool>(&do_conversion)->default_value(false), "If true will match each population to the second one. Not regular propensity calc - dividing in the population probability, but also multiply by the opposite population prob")
		;

	po::options_description desc42("get_feature_group option(switch)", row_size * 2, row_size);
	desc42.add_options()
		("GLOBAL42.group_signals", "the grouping argument, file path or BY_SIGNAL, BY_SIGNAL_CATEG, BY_SIGNAL_CATEG_TREND")
		("GLOBAL42.select_features", "the feature names to resolve, can be prefixed with \"file:\" to list many features, one in each line")
		;

	po::options_description desc43("show_names option(switch)", row_size * 2, row_size);
	desc43.add_options()
		("GLOBAL43.rep", "the repository")
		("GLOBAL43.sig", "the signal name")
		("GLOBAL43.sig_val", "the signal value.  can be prefixed with \"file:\" to list many values, one in each line. Can have 2 tokens for signal and signal_val with tab-delimeted")
		;

	po::options_description desc44("tt_predictor_on_matrix option(switch)", row_size * 2, row_size);
	desc44.add_options()
		("GLOBAL44.f_matrix", "the matrix to train and might also test on certain split")
		("f_test_matrix", po::value<string>(&f_test_matrix)->default_value(""), "the matrix to test on. Will not use train matrix splits")
		("GLOBAL44.split", "if given will choose a split.is >=999 will do full CV")
		("GLOBAL44.predictor_type", "type of predictor")
		("GLOBAL44.predictor_params", "params for predictor")
		("GLOBAL44.f_preds", "the path to store results")
		;

	po::options_description desc45("algomarker_dict option(switch)", row_size * 2, row_size);
	desc45.add_options()
		("GLOBAL45.rep", "the repository")
		("GLOBAL45.sig", "the signal name")
		("dict_path", po::value<string>(&dict_path)->default_value(""), "dictionary_path to define sets for")
		("add_empty", po::value<bool>(&add_empty)->default_value(false), "If true will also add values without mapping")
		("skip_missings", po::value<bool>(&skip_missings)->default_value(false), "If true will also skip missing values")
		("GLOBAL45.f_output", "the output path")
		;

	po::options_description desc46("compare_mat option(switch)", row_size * 2, row_size);
	desc46.add_options()
		("GLOBAL46.f_matrix", "the first matrix")
		("GLOBAL46.f_test_matrix", "the second matrix")
		("GLOBAL46.predictor_type", "type of predictor (optional) to try discriminate")
		("GLOBAL46.predictor_params", "params for predictor (optional) to try discriminate")
		("GLOBAL46.max_samples", "if > 0 : how many samples to subsample if matrix is large - to speedup")
		("GLOBAL46.f_output", "the output path (optional) or writes to screen")
		;

	po::options_description desc47("add_splits_to_samples option(switch)", row_size * 2, row_size);
	desc47.add_options()
		("GLOBAL47.f_split", "the splits definition file")
		("GLOBAL47.f_samples", "the input and output samples to rewrite the splits")
		;

	po::options_description desc48("predict_on_mat option(switch)", row_size * 2, row_size);
	desc48.add_options()
		("GLOBAL48.f_model", "The model to load MedPredictor from")
		("GLOBAL48.f_matrix", "the input to be applied on")
		("GLOBAL48.f_preds", "The preds with the output")
		("apply_feat_processors", po::value<bool>(&apply_feat_processors)->default_value(false), "if true will apply feature processors")
		;

	po::options_description desc49("rename_model_signal option(switch)", row_size * 2, row_size);
	desc49.add_options()
		("GLOBAL49.f_model", "The model")
		("GLOBAL49.f_output", "the output model")
		("GLOBAL49.sig", "the signal name in the model to be renamed")
		("signal_rename", po::value<string>(&signal_rename)->default_value(""), "new name for signal")
		;

	po::options_description desc50("flat_category_vals option(switch)", row_size * 2, row_size);
	desc50.add_options()
		("GLOBAL50.rep", "the repository path")
		("GLOBAL50.sig", "the signal to search for category")
		("GLOBAL50.sig_val", "file to code list")
		("shrink_code_list", po::value<bool>(&shrink_code_list)->default_value(false), "If true will shrink code list by keeping only the parents when all childs exists")
		;

	po::options_description desc51("fit_model_to_rep option(switch)", row_size * 2, row_size);
	desc51.add_options()
		("GLOBAL51.rep", "the repository path")
		("GLOBAL51.f_model", "the model path")
		("GLOBAL51.f_output", "the output model path after adjustments")
		("log_action_file_path", po::value<string>(&log_action_file_path)->default_value(""), "Optional file path to store all adjustment actions made to the model to fit rep")
		("log_missing_categories_path", po::value<string>(&log_missing_categories_path)->default_value(""), "Optional file path to store all missing categories in rep if there are ones")
		("GLOBAL51.cleaner_verbose", "1 to activate cleaner verbose, 0 keep as is, -1 - turn of")
		("remove_explainability", po::value<bool>(&remove_explainability)->default_value(false), "If true will remove Explainability is exists")
		("allow_virtual_rep", po::value<bool>(&allow_virtual_rep)->default_value(false), "If true will allow to recieve repository from AlgoMarker directory without data, will not support all conversions. In some cases, repository with data is needed for example in BUN-Urea")
		;
	//skip_missings

	desc.add(desc_global);
	desc.add(desc2);
	desc.add(desc6); desc.add(desc7); desc.add(desc8); desc.add(desc9);
	desc.add(desc10); desc.add(desc11); desc.add(desc12); desc.add(desc13);
	desc.add(desc14); desc.add(desc15); desc.add(desc16); desc.add(desc17);
	desc.add(desc18); desc.add(desc20); desc.add(desc21);
	desc.add(desc22); desc.add(desc23); desc.add(desc24); desc.add(desc25);
	desc.add(desc26); desc.add(desc27); desc.add(desc28); desc.add(desc29);
	desc.add(desc30); desc.add(desc31); desc.add(desc32);  desc.add(desc33);
	desc.add(desc34); desc.add(desc35); desc.add(desc36); desc.add(desc37);
	desc.add(desc38); desc.add(desc39); desc.add(desc40); desc.add(desc41);
	desc.add(desc42); desc.add(desc43); desc.add(desc44); desc.add(desc45);
	desc.add(desc46); desc.add(desc47); desc.add(desc48); desc.add(desc49);
	desc.add(desc50); desc.add(desc51);

	app_logo = "\n\
#######                      \n\
#       #       ####  #    # \n\
#       #      #    # #    # \n\
#####   #      #    # #    # \n\
#       #      #    # # ## # \n\
#       #      #    # ##  ## \n\
#       ######  ####  #    # \n\
		";

	init(desc);
}


//=====================================================================================================
//========== M A I N                   ================================================================
//=====================================================================================================
int main(int argc, char *argv[])
{

	FlowAppParams ap;
	if (ap.parse_parameters(argc, argv) < 0)
		return -1;

#if defined(__unix__)
	int arithmetic_flags = FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW;
	if (ap.options[OPTION_REP_CREATE])
		arithmetic_flags = FE_DIVBYZERO | FE_INVALID;
	if (!ap.catch_fe_exceptions)
		feenableexcept(arithmetic_flags);
#endif

	//Global setting:
	if (file_exists(ap.rep_fname))
		medial::repository::set_global_time_unit(ap.rep_fname);

	if (ap.global_time_unit != "")	global_default_time_unit = med_time_converter.string_to_type(ap.global_time_unit);
	if (ap.global_win_time_unit != "")	global_default_windows_time_unit = med_time_converter.string_to_type(ap.global_time_unit);


	// OPTION_HOSPITAL_REP , OPTION_REP_CREATE , OPTION_REP_CREATE_PIDS, OPTION_CLEAN_DICT
	if (flow_create_operations(ap) < 0) return -1;

	// OPTION_PRINTALL , OPTION_PID_PRINTALL , OPTION_PRINT , OPTION_PID_PRINT , OPTION_PRINT_PIDS , OPTION_SIG_PRINT, OPTION_SHOW_CATEGORY_INFO
	if (flow_print_operations(ap) < 0) return -1;

	// OPTION_TRAIN_TEST , OPTION_LEARN_MATRIX , OPTION_GENERATE_FEATURES , OPTION_PRINT_CLEANERS, OPTION_REWRITE_OBJECT, OPTION_MODEL_DEP
	if (flow_models_operations(ap) < 0) return -1;

	// OPTION_CREATE_OUTCOME , OPTION_MATCH_OUTCOME , OPTION_FILTER_OUTCOME , OPTION_FILTER_AND_MATCH , OPTION_GET_INCIDENCE
	// COHORT_INCIDENCE , COHORT_SAMPLING, OPTION_RELABEL options
	if (flow_cohort_samples_operations(ap) < 0) return -1;

	if (ap.options[OPTION_PIDS_PRINTALL]) {
		if (flow_pids_printall(ap.rep_fname, ap.in_samples_file, ap.outputFormat, ap.codes_to_signals_fname) < 0) {
			MERR("Flow: pids_printall: FAILED\n");
			return -1;
		}
	}



	// uncategorized atm

	if (ap.options[OPTION_DESCRIBE]) {
		if (flow_describe_sig(ap.rep_fname, ap.sig_name, ap.age_min, ap.age_max, ap.date_min, ap.date_max) < 0) {
			MERR("Flow: describe: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_DESCRIBE_ALL]) {
		if (flow_describe_all(ap.rep_fname, ap.signals_fname, ap.age_min, ap.age_max, ap.date_min, ap.date_max) < 0) {
			MERR("Flow: describe_all: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_CREATE_SPLITS]) {
		if (flow_create_split(ap.split_fname, ap.split_params, ap.rep_fname) < 0) {
			MERR("Flow: create_outcome : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_EXTRACT_PIDS_IN_SET])
		flow_extract_pids_in_set(ap.rep_fname, ap.sig_section, ap.sig_name, ap.sig_set, ap.sig_val, ap.output_fname);

	if (ap.options[OPTION_SCAN_SIGS_FOR_SAMPLES]) {
		if (flow_scan_sigs_for_samples(ap.rep_fname, ap.outcome_fname) < 0) {
			MERR("Flow: samples_scan_sigs : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_ADD_SPLITS_TO_SAMPLES])
		flow_add_splits_to_samples(ap.split_fname, ap.f_samples);

	if (ap.options[OPTION_AM_DICT])
		flow_create_dict_for_am(ap.rep_fname, ap.sig_name, ap.dict_path, ap.add_empty,
			ap.skip_missings, ap.output_fname);

	if (ap.options[OPTION_CMP_MATRIX]) {
		MedFeatures mat1, mat2;
		mat1.read_from_csv_mat(ap.matrix_fname);
		if (ap.f_test_matrix.empty())
			MTHROW_AND_ERR("Must provide f_test_matrix in this mode\n");
		mat2.read_from_csv_mat(ap.f_test_matrix);
		medial::process::compare_populations(mat1, mat2, "f_matrix", "f_test_matrix",
			ap.output_fname, ap.predictor_type, ap.predictor_params, 3, ap.max_samples);
	}

}
