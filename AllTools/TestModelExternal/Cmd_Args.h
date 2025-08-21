#ifndef __CMD_ARGS__
#define __CMD_ARGS__
#include <MedUtils/MedUtils/MedUtils.h>
#include <fstream>
#include <MedProcessTools/MedProcessTools/MedSamples.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

enum SHAPLEY_FLAG
{
	CALC_UNORM = 1,
	CALC_FINAL = 2,
	CALC_ALL = 3
};

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	void post_process() {
		if (train_ratio > 1)
			HMTHROW_AND_ERR("Error train_ratio should be lower than 1\n");
		if (model_path.empty() && model_json_additional_path.empty())
			HMTHROW_AND_ERR("Error either model_path,model_json_additional_path must be provided\n");
	}
public:

	string rep_trained;
	string rep_test;

	string model_path;
	string model_json_additional_path;
	string samples_train;
	string samples_test;
	string strata_train_features_moments;
	string train_matrix_csv;
	string features_subset_file;
	string feature_binning_config;
	string name_for_train;
	string name_for_test;

	string strata_json_model;
	string strata_settings;

	bool fix_train_res, fix_test_res;
	unsigned char calc_shapley_mask;

	string predictor_type;
	string predictor_args;
	string calibration_init_str;

	int sub_sample_train;
	int sub_sample_test;
	int sub_sample_but_why; //maximal number of samples to use to calc but why - to boost up performance. 0 no limit
	double train_ratio;
	bool print_mat;

	string bt_params;
	string binning_shap_params;
	string group_shap_params;
	double shap_auc_threshold;

	string output;
	int smaller_model_feat_size;
	string additional_importance_to_rank;
	bool match_also_outcome;
	string feature_html_template;

	ProgramArgs() {
		po::options_description options("Required options");
		options.add_options()
			("model_path", po::value<string>(&model_path)->default_value(""), "model path - either model_json_additional_path,model_path are required")
			("model_json_additional_path", po::value<string>(&model_json_additional_path)->default_value(""), "model json path - either model_json_additional_path,model_path are required")
			("rep_test", po::value<string>(&rep_test)->required(), "Repository path to test")
			("samples_test", po::value<string>(&samples_test)->required(), "samples path to be calculated on rep_test")
			("name_for_test", po::value<string>(&name_for_test)->default_value("TEST"), "name for those test samples")


			("output", po::value<string>(&output)->default_value(""), "output file path")
			("smaller_model_feat_size", po::value<int>(&smaller_model_feat_size)->default_value(0), "If > 0 will create additional smaller model with top X group of features")
			("additional_importance_to_rank", po::value<string>(&additional_importance_to_rank)->default_value(""), "If given will read additional shapley report to rank with propensity rank")
			("match_also_outcome", po::value<bool>(&match_also_outcome)->default_value(false), "If true will add outcome as a feature and will try to match into")
			;

		po::options_description options2("Compare input options");
		options2.add_options()
			("rep_trained", po::value<string>(&rep_trained)->default_value(""), "trained repository path")
			("samples_train", po::value<string>(&samples_train)->default_value(""), "samples path to be calculated on rep_train")
			("name_for_train", po::value<string>(&name_for_train)->default_value("TRAIN"), "name for those test samples")
			("strata_train_features_moments", po::value<string>(&strata_train_features_moments)->default_value(""), "If given and no rep_trained and samples_train - will use this path as input for train stratas. If empty no compare will be made")
			("train_matrix_csv", po::value<string>(&train_matrix_csv)->default_value(""), "If given and no rep_trained and samples_train - will use this path as input for train feature matrix. If empty no compare will be made")
			;

		po::options_description options3("Usage of full train repository and samples to compare mode args");
		options3.add_options()
			("features_subset_file", po::value<string>(&features_subset_file)->default_value(""), "Optional file where each line is name of feature to lookup - to filter features that are less important to the model or outcome and so not confounder to better focus the model")
			("fix_train_res", po::value<bool>(&fix_train_res)->default_value(false), "if true will also fix train res by test")
			("fix_test_res", po::value<bool>(&fix_test_res)->default_value(true), "if true will also fix test res by train")
			("feature_binning_config", po::value<string>(&feature_binning_config)->default_value(""), "Optional file path to configuration of binning of features.Tab delimeted with 2 cols. 1st col regex for feature. 2nd cols - binning config string BinSettings")

			("predictor_type", po::value<string>(&predictor_type)->default_value("lightgbm"), "predictor type")
			("predictor_args", po::value<string>(&predictor_args)->default_value("num_threads=15;num_trees=500;learning_rate=0.03;lambda_l2=0;metric_freq=10;verbose=1"), "predictor args")
			("calibration_init_str", po::value<string>(&calibration_init_str)->default_value("calibration_type=isotonic_regression"), "calibration init string for model trained on rest of train_ratio")

			("sub_sample_train", po::value<int>(&sub_sample_train)->default_value(0), "subsampling of train samples. 0 - means no subsampling")
			("sub_sample_test", po::value<int>(&sub_sample_test)->default_value(0), "subsampling of test samples. 0 - means no subsampling")
			("sub_sample_but_why", po::value<int>(&sub_sample_but_why)->default_value(0), "maximal number of samples to use to calc but why - to boost up performance. 0 no limit")
			("train_ratio", po::value<double>(&train_ratio)->default_value(-1), "train-test ratio. number between [0, 1). 0 or negative number means overfitting and no train/test split. Good value can be 0.7 if want to split")

			("bt_params", po::value<string>(&bt_params)->default_value(""), "bootstrap params")

			("binning_shap_params", po::value<string>(&binning_shap_params)->default_value("split_method=iterative_merge;binCnt=50;min_bin_count=100;min_res_value=0.1"), "binning params for shap")
			("group_shap_params", po::value<string>(&group_shap_params)->default_value(""), "grouping shap params")
			("shap_auc_threshold", po::value<double>(&shap_auc_threshold)->default_value(0.52), "Threshold that belows it, it will skip Shap value calculations")

			("print_mat", po::value<bool>(&print_mat)->default_value(true), "if true will print mat")
			("calc_shapley_mask", po::value<unsigned char>(&calc_shapley_mask)->default_value(3), "Mask to calculate shapley: 1 - Unorm features, 2 - norm features")
			("feature_html_template", po::value<string>(&feature_html_template)->default_value(""), "HTML template for plotting graphs for cases/controls in train, test samples and train with weights")
			;

		po::options_description options4("Usage of stratified matrix as input to compare with");
		options4.add_options()
			("strata_json_model", po::value<string>(&strata_json_model)->default_value(""), "the medmodel json path to calc the stratas")
			("strata_settings", po::value<string>(&strata_settings)->default_value("Age,0,100,10"), "strata settings - \":\" is delimeter for next feature strata. strata settings in this format by \",\" delimeter:FEATURE_NAME,MIN_VALUE,MAX_VALUE,BIN_SIZE")
			;

		options.add(options2);
		options.add(options3);
		options.add(options4);

		init(options);
	}
};


#endif
