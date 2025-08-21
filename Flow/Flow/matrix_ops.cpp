//
// matrix_ops - 
//
// basic matrix operations: mainly creating new feature matrices, writing/reading matrices 
//

#include "Flow.h"
#include "Logger/Logger/Logger.h"
#include "MedUtils/MedUtils/MedUtils.h"
#include "MedFeat/MedFeat/MedOutcome.h"
#include "MedStat/MedStat/MedPerformance.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
extern MedLogger global_logger;
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string.hpp>

#include <random>
#include <algorithm>

using namespace std;
using namespace boost;


void flow_print_distribution(vector<float> & y, const string& pref);


//================================================================================================================
// creating a new feature matrix
//================================================================================================================
int flow_create_feature_matrix(string &matrix_fname, string &mat_fmt, string &rep_fname, string &outcome_fname, string &split_fname, string &feat_fname);


//================================================================================================================
// learn a model on prepared matrix
//================================================================================================================
int flow_learn_matrix(string f_xtrain, string f_ytrain, string f_xtest, string f_ytest, string learn_model, string learn_params)
{

	MedMat<float> xtrain, ytrain, xtest, ytest;

	if (f_xtrain.find(".csv") == string::npos) {

		if (xtrain.read_from_bin_file(f_xtrain) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_xtrain.c_str()); return -1; }
		if (ytrain.read_from_bin_file(f_ytrain) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_ytrain.c_str()); return -1; }

		MLOG("Flow Learn Matrix: Read xtrain: %d x %d , ytrain: %d x %d\n", xtrain.nrows, xtrain.ncols, ytrain.nrows, ytrain.ncols);

		if (f_xtest != "" && f_ytest != "") {
			if (xtest.read_from_bin_file(f_xtest) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_xtest.c_str()); return -1; }
			if (ytest.read_from_bin_file(f_ytest) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_ytest.c_str()); return -1; }
			MLOG("Flow Learn Matrix: Read xtest: %d x %d , ytest: %d x %d\n", xtest.nrows, xtest.ncols, ytest.nrows, ytest.ncols);
		}
	}
	else {
		// read csv

		MLOG("Reading matrices as CSV files with no titles line\n");

		if (xtrain.read_from_csv_file(f_xtrain, 0) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_xtrain.c_str()); return -1; }
		if (ytrain.read_from_csv_file(f_ytrain, 0) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_ytrain.c_str()); return -1; }

		MLOG("Flow Learn Matrix: Read xtrain: %d x %d , ytrain: %d x %d\n", xtrain.nrows, xtrain.ncols, ytrain.nrows, ytrain.ncols);

		if (f_xtest != "" && f_ytest != "") {
			if (xtest.read_from_csv_file(f_xtest, 0) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_xtest.c_str()); return -1; }
			if (ytest.read_from_csv_file(f_ytest, 0) < 0) { MERR("Flow Learn Matrix: Failed reading %s\n", f_ytest.c_str()); return -1; }
			MLOG("Flow Learn Matrix: Read xtest: %d x %d , ytest: %d x %d\n", xtest.nrows, xtest.ncols, ytest.nrows, ytest.ncols);
		}
	}

	// learn the model
	MLOG("Flow Learn Matrix: initializing model: %s :: params: %s\n", learn_model.c_str(), learn_params.c_str());
	MedPredictor *model = MedPredictor::make_predictor(learn_model);
	if (model == NULL) {
		MERR("Flow Learn Matrix: Cannot initialize a model of type \'%s\'\n", learn_model.c_str());
		return -1;
	}
	model->init_from_string(learn_params);
	xtrain.normalized_flag = 1;
	xtest.normalized_flag = 1;

	if (model->learn(xtrain, ytrain) < 0) {
		MERR("Flow Learn Matrix: Error while running learn %s(%s)\n", learn_model.c_str(), learn_params.c_str());
		return -1;
	}

	// performance on train
	vector<float> pred_train;
	model->predict(xtrain, pred_train);
	flow_analyze(pred_train, ytrain.get_vec(), "TRAIN:");


	// performance on test
	if (xtest.nrows > 0) {
		vector<float> pred_test;
		model->predict(xtest, pred_test);
		flow_analyze(pred_test, ytest.get_vec(), "TEST:");
	}

	return 0;
}


//=====================================================================================================
int flow_analyze(vector<float> &preds, vector<float> &y, const string pref)
{
	double auc = medial::performance::auc(preds, y);
	int direction = 1; if (auc < 0.5) direction = -1;
	if (auc < 0.5) auc = 1.0 - auc;
	float corr = medial::performance::pearson_corr_without_cleaning(preds, y);

	vector<float> sizes = { (float)0.01 , (float)0.05, (float)0.1, (float)0.2, (float)0.5 };
	vector<vector<int>> cnts;
	medial::performance::get_preds_perf_cnts(preds, y, sizes, direction, cnts);
	flow_print_distribution(y, pref);
	MLOG("Flow: analyze: %s: AUC: %6.3f    corr: %6.3f\n", pref.c_str(), auc, corr);

	for (int i = 0; i < sizes.size(); i++) {
		float sens, spec, ppv, rr;
		medial::performance::cnts_to_perf(cnts[i], sens, spec, ppv, rr);
		MLOG("TT: analyze: %s: size: %6.3f sens: %6.3f spec: %6.3f ppv: %6.3f rr: %6.3f\n", pref.c_str(), sizes[i], sens, spec, ppv, rr);
	}

	return 0;
}

void flow_print_distribution(vector<float> &y, const string &pref)
{
	int zeros = 0, non_zeros = 1;
	for (int i = 0; i < y.size(); i++) {
		if (y[i] == 0.0)
			zeros++;
		else
			non_zeros++;
	}
	MLOG("TT: %s: label distribution = %d non-zeros, %d zeros\n", pref.c_str(), non_zeros, zeros);
}