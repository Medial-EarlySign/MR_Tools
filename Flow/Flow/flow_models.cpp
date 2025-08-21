#include "Flow.h"
#include "Logger/Logger/Logger.h"
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedAlgo/MedAlgo/BinSplitOptimizer.h>
#include <MedProcessTools/MedProcessTools/ExplainWrapper.h>
#include <MedStat/MedStat/MedBootstrap.h>
#include <unordered_set>
#include <cmath>
#include <algorithm>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

//=====================================================================================================
int flow_simple_train(string rep_fname, string f_model, string f_samples, string f_json, string f_matrix, bool no_matrix_retrain,
	int split, string predictor, string predictor_params, vector<string> &train_test_json_alt)
{
	MedModel model;

	if (no_matrix_retrain) {
		if (model.read_from_file(f_model) < 0) return -1;
		if (predictor != "") {
			MLOG("Deleting current predictor in model\n");
			if (model.predictor != NULL) { delete model.predictor; model.predictor = NULL; }
			MLOG("Setting a new untrained model: %s with params %s\n", predictor.c_str(), predictor_params.c_str());
			model.set_predictor(predictor, predictor_params);
		}
		else
			model.replace_predictor_with_json_predictor(f_json);
	}
	else {
		model.init_from_json_file_with_alterations(f_json, train_test_json_alt);
		if (!predictor.empty() && !predictor_params.empty()) {
			MLOG("Deleting current predictor in model\n");
			if (model.predictor != NULL) { delete model.predictor; model.predictor = NULL; }
			MLOG("Setting a new untrained model: %s with params %s\n", predictor.c_str(), predictor_params.c_str());
			model.set_predictor(predictor, predictor_params);
		}
	}


	MedSamples samples;

	if (samples.read_from_file(f_samples) < 0) return -1;
	vector<int> pids;

	if (split >= 0) {
		MedSamples in_s, out_s;
		samples.split_by_split(in_s, out_s, split);
		samples = out_s;
	}

	samples.get_ids(pids);


	MedPidRepository rep;
	model.load_repository(rep_fname, pids, rep, true);

	if (no_matrix_retrain) {
		if (model.learn_skip_matrix_train(rep, &samples, MED_MDL_END) < 0) return -1;
	}
	else {
		if (model.learn(rep, &samples) < 0) return -1;
	}

	if (model.write_to_file(f_model) < 0) return -1;

	if (f_matrix != "//you/need/to/fill/the/matrix_fname/parameter") {
		if (model.features.write_as_csv_mat(f_matrix) < 0)
			return -1;
	}


	return 0;

}

//=====================================================================================================
int flow_simple_test(string rep_fname, string f_model, string f_samples, string f_preds, string f_matrix, int split)
{
	MedModel model;

	if (model.read_from_file(f_model) < 0) return -1;

	MedSamples samples;

	if (samples.read_from_file(f_samples) < 0) return -1;

	if (split >= 0) {
		MedSamples in_s, out_s;
		samples.split_by_split(in_s, out_s, split);
		samples = in_s;
	}

	vector<int> pids;
	samples.get_ids(pids);

	MedPidRepository rep;
	model.load_repository(rep_fname, pids, rep, true);

	if (model.apply(rep, samples) < 0) return -1;

	// just a small auc print:
	vector<float> preds, y;
	samples.get_preds_channel(preds, 0);
	samples.get_y(y);
	flow_analyze(preds, y, "TEST");

	if (f_preds != "//you/need/to/fill/the/f_preds/parameter")
		samples.write_to_file(f_preds);
	else
		MLOG("No f_preds to write predictions was provided <<<<======\n");

	if (f_matrix != "//you/need/to/fill/the/matrix_fname/parameter") {
		if (model.features.write_as_csv_mat(f_matrix) < 0)
			return -1;
	}


	return 0;

}

void split_train_test(MedFeatures &train_mat, MedFeatures &test_mat, int split) {
	vector<int> train_ids, test_ids;
	for (int i = 0; i < train_mat.samples.size(); ++i)
		if (train_mat.samples[i].split == split)
			test_ids.push_back(i);
		else
			train_ids.push_back(i);
	test_mat = train_mat;
	medial::process::filter_row_indexes(test_mat, test_ids);
	medial::process::filter_row_indexes(train_mat, train_ids);
}

void train_test_predictor(const string &f_matrix_train, const string &f_matrix_test,
	int split, const string &predictor_type, const string &predictor_params, const string &f_preds) {
	if (f_matrix_train.empty())
		MTHROW_AND_ERR("Error = must provice f_matrix in this mode\n");
	if (predictor_type.empty())
		MTHROW_AND_ERR("Error = must provide predictor in this mode\n");
	if (f_preds.empty())
		MTHROW_AND_ERR("Error = must provide f_preds in this mode\n");
	//Learns MedPredictor on train and apply on test => store in f_preds
	//if split =-1 => will use all train and apply on test. if has a values and no "f_matrix_test" will do the split
	unique_ptr<MedPredictor> predictor = unique_ptr<MedPredictor>(MedPredictor::make_predictor(predictor_type, predictor_params));

	MedFeatures train_mat, test_mat;
	MedMat<float> train_labels;
	train_mat.read_from_csv_mat(f_matrix_train);
	if (f_matrix_test != "")
		test_mat.read_from_csv_mat(f_matrix_test);
	else {
		if (split < 0) {
			MWARN("WARN !! OVERFITTING\n");
			test_mat = train_mat; //overfitting
		}
		else {
			if (split >= 999) {
				//Full CV:
				set<int> split_set;
				for (size_t i = 0; i < train_mat.samples.size(); ++i)
					split_set.insert(train_mat.samples[i].split);
				MedFeatures full_copy = train_mat;
				vector<MedSample> all_splits_res;
				if (split_set.size() == 1)
					MTHROW_AND_ERR("Error - no splits in matrix, either set them or pass -1 to do overfitting\n");
				for (int _split : split_set)
				{
					train_mat = full_copy;
					split_train_test(train_mat, test_mat, _split);

					predictor->learn(train_mat);
					predictor->predict(test_mat);
					all_splits_res.insert(all_splits_res.end(), test_mat.samples.begin(), test_mat.samples.end());
				}

				MedSamples result_file;
				result_file.import_from_sample_vec(all_splits_res);

				result_file.write_to_file(f_preds);
				return;
			}
			else {
				//split to train/test:
				split_train_test(train_mat, test_mat, split);
			}
		}
	}
	predictor->learn(train_mat);
	predictor->predict(test_mat);

	MedSamples result_file;
	result_file.import_from_sample_vec(test_mat.samples);
	//save results in f_preds file:
	result_file.write_to_file(f_preds);
}

//=====================================================================================================
void filter_feats(MedModel &model, const string &select_features) {
	if (select_features != "") {
		vector<string> search_str;
		boost::split(search_str, select_features, boost::is_any_of(","));
		unordered_set<string> selected;

		model.features.prep_selected_list(search_str, selected);
		model.features.filter(selected);
	}
}
int apply_model_save(MedModel &model, MedSamples &samples, MedPidRepository &rep, MedModelStage stop_stage,
	const string &f_matrix, const string &select_features, bool string_attributes) {
	int batch_sz = model.get_apply_batch_count();
	if (samples.nSamples() > batch_sz) {
		vector<MedSample> flatt_sampels;
		samples.export_to_sample_vec(flatt_sampels);
		MedSamples batch_sampes;
		int tot_samples = (int)flatt_sampels.size();
		int batch_start = 0, curr_ser = 0;
		while (batch_start < tot_samples - 1) {
			int batch_end = batch_start + batch_sz;
			if (batch_end >= tot_samples)
				batch_end = tot_samples - 1;
			vector<MedSample> flat_batch(flatt_sampels.begin() + batch_start,
				flatt_sampels.begin() + batch_end);
			batch_sampes.import_from_sample_vec(flat_batch);

			if (model.apply(rep, batch_sampes, MED_MDL_APPLY_FTR_GENERATORS, stop_stage) < 0) {
				MERR("Flow: get_mat: could not apply model\n");
				return -1;
			}
			filter_feats(model, select_features);
			if (batch_start == 0) {
				if (model.features.write_as_csv_mat(f_matrix, string_attributes) < 0) {
					MERR("Flow: get_mat: could not write to matrix file %s\n", f_matrix.c_str());
					return -1;
				}
			}
			else {
				if (model.features.add_to_csv_mat(f_matrix, string_attributes, curr_ser) < 0) {
					MERR("Flow: get_mat: could not append to matrix file %s\n", f_matrix.c_str());
					return -1;
				}
			}
			curr_ser += (int)model.features.samples.size();
			batch_start = batch_end;
		}
	}
	else
	{
		if (model.apply(rep, samples, MED_MDL_APPLY_FTR_GENERATORS, stop_stage) < 0) {
			MERR("Flow: get_mat: could not apply model\n");
			return -1;
		}
		filter_feats(model, select_features);
		if (model.features.write_as_csv_mat(f_matrix, string_attributes) < 0) {
			MERR("Flow: get_mat: could not write to matrix file %s\n", f_matrix.c_str());
			return -1;
		}
	}
	return 0;
}
int flow_get_json_mat(string rep_fname, string f_model, string f_samples, string f_json, string f_matrix, int stop_step)
{
	MedModel model;

	model.init_from_json_file(f_json);

	MedSamples samples;
	if (samples.read_from_file(f_samples) < 0) return -1;
	vector<int> pids;
	samples.get_ids(pids);

	MedPidRepository rep;
	model.load_repository(rep_fname, pids, rep, true);
	MedModelStage stop_stage = MED_MDL_APPLY_PREDICTOR; //default
	if (stop_step > 0)
		stop_stage = (MedModelStage)stop_step;
	if (model.learn(rep, &samples, MED_MDL_LEARN_REP_PROCESSORS, stop_stage) < 0) return -1;

	if (model.features.write_as_csv_mat(f_matrix) < 0) return -1;

	return 0;

}


//=====================================================================================================
int flow_get_model_preds(string rep_fname, string f_model, string f_samples, string f_preds, string f_pre_json,
	bool only_apply_pp, bool print_attributes, const string &change_object_init, const string &change_model_file)
{
	MedModel model;
	if (!change_model_file.empty())
		model.read_from_file_with_changes(f_model, change_model_file);
	else {
		if (model.read_from_file(f_model) < 0) {
			MERR("Flow: get_model_preds: could not read model file %s\n", f_model.c_str());
			return -1;
		}
		if (!change_object_init.empty()) {
			ChangeModelInfo ch;
			ch.init_from_string(change_object_init);
			model.change_model(ch);
		}
	}

	MedPidRepository rep;
	MedSamples samples;
	if (samples.read_from_file(f_samples) < 0) {
		MERR("Flow: get_model_preds: could not read samples file %s\n", f_samples.c_str());
		return -1;
	}

	if (only_apply_pp) {
		//no need for rep:
		samples.export_to_sample_vec(model.features.samples);
		if (model.apply(rep, samples, MedModelStage::MED_MDL_APPLY_POST_PROCESSORS, MedModelStage::MED_MDL_END) < 0) {
			MERR("Flow: get_model_preds: could not apply model\n");
			return -1;
		}
		if (samples.write_to_file(f_preds, -1, print_attributes) < 0) {
			MERR("Flow: get_model_preds: could not write to file %s\n", f_preds.c_str());
			return -1;
		}
		return 0;
	}

	if (f_pre_json != "") {
		vector<string> dummy_arr;
		model.add_pre_processors_json_string_to_model("", f_pre_json, dummy_arr, true);
	}
	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_fname.c_str());
	model.fit_for_repository(rep);
	unordered_set<string> req_sigs;
	vector<string> rsigs;
	model.get_required_signal_names(req_sigs);
	for (auto &s : req_sigs) rsigs.push_back(s);


	vector<int> pids;
	samples.get_ids(pids);


	if (rep.read_all(rep_fname, pids, rsigs) < 0) {
		MERR("Flow: get_model_preds: could not read repository %s\n", rep_fname.c_str());
		return -1;
	}

	samples.export_to_sample_vec(model.features.samples);
	if (model.apply(rep, samples) < 0) {
		MERR("Flow: get_model_preds: could not apply model\n");
		return -1;
	}

	if (samples.write_to_file(f_preds, -1, print_attributes) < 0) {
		MERR("Flow: get_model_preds: could not write to file %s\n", f_preds.c_str());
		return -1;
	}

	return 0;
}

//=====================================================================================================
int flow_get_mat(string rep_fname, string f_model, string f_samples, string f_matrix, string select_features,
	bool string_attributes, string f_pre_json, int stop_step, const string &change_model_init, const string &change_model_file)
{
	MedModel model;
	if (!change_model_file.empty())
		model.read_from_file_with_changes(f_model, change_model_file);
	else {
		if (model.read_from_file(f_model) < 0) {
			MERR("Flow: get_mat: could not read model file %s\n", f_model.c_str());
			return -1;
		}
		if (!change_model_init.empty()) {
			ChangeModelInfo ch;
			ch.init_from_string(change_model_init);
			model.change_model(ch);
		}
	}
	if (f_pre_json != "") {
		vector<string> dummy_arr;
		model.add_pre_processors_json_string_to_model("", f_pre_json, dummy_arr, true);
		
	}


	unordered_set<string> req_sigs;
	vector<string> rsigs;
	MedPidRepository rep;
	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_fname.c_str());
	model.fit_for_repository(rep);
	model.get_required_signal_names(req_sigs);
	for (auto &s : req_sigs) rsigs.push_back(s);

	MedSamples samples;

	if (samples.read_from_file(f_samples) < 0) {
		MERR("Flow: get_mat: could not read samples file %s\n", f_samples.c_str());
		return -1;
	}

	vector<int> pids;

	samples.get_ids(pids);


	if (rep.read_all(rep_fname, pids, rsigs) < 0) {
		MERR("Flow: get_mat: could not read repository %s\n", rep_fname.c_str());
		return -1;
	}

	MedModelStage stop_stage = MED_MDL_END;
	if (stop_step > 0) {
		stop_stage = (MedModelStage)stop_step;
	}
	//If need to do batching?
	return apply_model_save(model, samples, rep, stop_stage, f_matrix, select_features, string_attributes);
}

//=====================================================================================================
int flow_train_test(FlowAppParams &ap)
{
	TrainTestV2 tt;

	tt.f_learning_samples = ap.train_test_learning_samples_fname;
	tt.f_validation_samples = ap.train_test_validation_samples_fname;
	tt.f_model_init = ap.train_test_model_init_fname;
	tt.f_rep = ap.rep_fname;
	tt.steps = ap.steps;
	tt.active_splits_str = ap.active_splits;
	tt.f_split = ap.split_fname;
	tt.wdir = ap.work_dir;
	tt.prefix = ap.train_test_prefix;
	tt.validation_prefix = ap.train_test_validation_prefix;
	tt.preds_format = ap.train_test_preds_format;
	tt.json_alt = ap.train_test_json_alt;
	tt.save_matrix_flag = ap.train_test_save_matrix;
	tt.save_contribs_flag = ap.train_test_save_contribs;
	tt.save_matrix_splits = ap.train_test_save_matrix_splits;
	tt.cv_on_train_str = ap.cv_on_train1;
	tt.conf_fname = ap.train_test_conf_fname;
	tt.pred_params_fname = ap.pred_params_fname;
	tt.runner();

	return 0;
}

//=========================================================================================================================
int flow_print_model_processors(string &f_model)
{
	MedModel model;

	MLOG("Reading model file %s\n", f_model.c_str());
	if (model.read_from_file(f_model) < 0) {
		MERR("FAILED reading model file %s\n", f_model.c_str());
		return -1;
	}

	int i = 0;
	for (auto &proc : model.rep_processors) {
		MLOG("Processor %d :: type %d :: ", i++, proc->processor_type);
		proc->print();
	}

	return 0;
}

//=========================================================================================================================
int flow_print_model_info(const string &f_model, const string &model_predictor_path, const string &predcitor_type,
	const string &general_importance_param, string f_features, string rep, string f_samples, int max_samples,
	bool print_in_json, const string &f_output_json)
{
	MedModel model;

	MLOG("Reading model file %s\n", f_model.c_str());
	if (model.read_from_file(f_model) < 0) {
		MERR("FAILED reading model file %s\n", f_model.c_str());
		return -1;
	}
	if (model.version_info.empty())
		MLOG("Model is old and doesn't contain version info...\n");
	else
		MLOG("Read Model version:\n%s\n", model.version_info.c_str());
	string current_v = medial::get_git_version();
	if (model.version_info != current_v)
		MLOG("It's differnt from crrent code version:\n%s\n", current_v.c_str());
	if (!predcitor_type.empty() && !model_predictor_path.empty()) {
		delete model.predictor;
		MLOG("Reloading predictor type %s from %s\n", predcitor_type.c_str(), model_predictor_path.c_str());
		model.predictor = MedPredictor::make_predictor(predcitor_type);
		model.predictor->read_from_file(model_predictor_path);
	}

	if (!print_in_json)
		model.dprint_process("MODEL_INFO:", 2, 2, 2, 2, 2);
	else {
		if (!f_output_json.empty()) {
			string json_cont = model.object_json();
			ofstream fw_json(f_output_json);
			if (!fw_json.good())
				MTHROW_AND_ERR("Error can't open file %s for writing\n", f_output_json.c_str());
			fw_json << json_cont;
			fw_json.flush();
			fw_json.close();
			MLOG("Wrote Model in json format into %s\n", f_output_json.c_str());
			FILE * pFile;
			string precditor_path = f_output_json + ".predictor";
			pFile = fopen(precditor_path.c_str(), "w");
			model.predictor->print(pFile, "", 2);
			fclose(pFile);
			MLOG("Wrote Predictor into %s\n", precditor_path.c_str());
		}
	}

	if (model.predictor == NULL) {
		MLOG("Model has no predictor\n");
		return 0;
	}

	MedFeatures allocated_mat;
	MedFeatures *features = NULL;
	if (rep != "" && f_samples != "") {
		MedSamples samples_test;
		samples_test.read_from_file(f_samples);
		int nsamlpes = samples_test.nSamples();
		if (max_samples > 0 && max_samples < nsamlpes)
			medial::process::down_sample(samples_test, float(max_samples) / nsamlpes);
		medial::medmodel::apply(model, samples_test, rep);
		features = &model.features;
	}
	else if (f_features != "")
	{
		features = &allocated_mat;
		MedMat<float> x;
		int titles_line_flag = 1;
		x.read_from_csv_file(f_features, titles_line_flag);
		features->set_as_matrix(x);
		if (max_samples > 0 && max_samples < features->samples.size())
			medial::process::down_sample(*features, float(max_samples) / features->samples.size());
	}



	// feature importance print
	vector<float> features_scores;

	model.predictor->calc_feature_importance(features_scores, general_importance_param, features);
	//sort and print features
	vector<string> feat_names;
	if (features != NULL)
		features->get_feature_names(feat_names);
	else {
		feat_names = model.predictor->model_features;
	}

	if (feat_names.size() != features_scores.size()) {
		if (feat_names.size() + 1 == features_scores.size())
			feat_names.push_back("b0_const");
		else {
			MLOG("Got %zu features and %zu scores in predictor to used features.. giving names by order\n",
				feat_names.size(), features_scores.size());
			feat_names.resize(features_scores.size());
			for (size_t i = 0; i < feat_names.size(); ++i)
				feat_names[i] = "FTR_" + to_string(i + 1);
		}
	}
	else
		MLOG("Got %zu features in predictor\n", feat_names.size());

	sort(feat_names.begin(), feat_names.end());
	vector<pair<string, float>> ranked((int)features_scores.size());
	for (size_t i = 0; i < features_scores.size(); ++i)
		ranked[i] = pair<string, float>(feat_names[i], features_scores[i]);
	sort(ranked.begin(), ranked.end(), [](const pair<string, float> &c1, const pair<string, float> &c2)
	{
		return c1.second > c2.second;
	});
	for (size_t i = 0; i < ranked.size(); ++i)
	{
		printf("FEATURE IMPORTANCE %s : %2.3f\n", ranked[i].first.c_str(), ranked[i].second);
	}


	return 0;
}

bool get_real_sigs(MedModel &model, const string &sig, vector<string> &real) {
	unordered_set<string> signalNames;
	signalNames.insert(sig);
	for (int i = (int)model.rep_processors.size() - 1; i > 0; --i)
		model.rep_processors[i]->get_required_signal_names(signalNames, signalNames);
	//filter to keep only physical signals:
	real.clear();
	for (const string &sig_name : signalNames)
	{
		if (model.virtual_signals.find(sig_name) == model.virtual_signals.end() &&
			model.virtual_signals_generic.find(sig_name) == model.virtual_signals_generic.end())
			real.push_back(sig_name);
	}

	return model.virtual_signals.find(sig) != model.virtual_signals.end() ||
		model.virtual_signals_generic.find(sig) != model.virtual_signals_generic.end();
}

bool flat_all_sons(MedDictionarySections &dict,
	const string &signalName, const string &code, vector<int> &flat_parents,
	vector<int> &flat_leafs, int max_depth = 0) {
	int sectionId = dict.section_id(signalName);
	//includes the code itself!

	int code_id = dict.id(sectionId, code);
	if (code_id < 0) {
		if (signalName == "Smoking_Status") {

			return false;
		}
		MTHROW_AND_ERR("Error in flat_all_sons - can't find code %s in signal %s\n",
			code.c_str(), signalName.c_str());
	}

	vector<int> last_layer_new_ids;
	unordered_set<int> full_list, full_parents, full_leaves;
	full_list.insert(code_id);
	last_layer_new_ids.push_back(code_id);
	int depth_cnt = 0;
	while (!last_layer_new_ids.empty()) {
		vector<int> new_ids;
		for (int id_in : last_layer_new_ids)
		{
			vector<int> fetch_ids;
			dict.get_set_members(sectionId, id_in, fetch_ids);
			if (fetch_ids.size() > 0)
				full_parents.insert(id_in);
			else
				full_leaves.insert(id_in);

			for (int fetch_id : fetch_ids)
			{
				//not seen id - new one
				if (full_list.find(fetch_id) == full_list.end()) {
					full_list.insert(fetch_id);
					new_ids.push_back(fetch_id);
					//insert to leave or parent - depend on result
				}
			}
		}
		last_layer_new_ids = move(new_ids);
		++depth_cnt;
		if (max_depth > 0 && depth_cnt >= max_depth)
			break;
	}

	//return all ids in full_list
	flat_parents.clear();
	flat_leafs.clear();
	flat_parents.insert(flat_parents.end(), full_parents.begin(), full_parents.end());
	flat_leafs.insert(flat_leafs.end(), full_leaves.begin(), full_leaves.end());
	return full_list.size() > 1;
}

void flow_print_model_signals(const string &f_model, const string &rep_path, const string &dict_path,
	bool is_source_rep)
{
	bool filter_rep_uneeded = false;
	bool use_same_rep_numbers = true;
	MedModel model;

	MLOG("Reading model file %s\n", f_model.c_str());
	if (model.read_from_file(f_model) < 0)
		MTHROW_AND_ERR("FAILED reading model file %s\n", f_model.c_str());
	//get feature names
	MedPidRepository rep;
	if (!rep_path.empty()) {
		if (rep.init(rep_path) < 0)
			MTHROW_AND_ERR("Error can't read rep %s\n", rep_path.c_str());

		model.fit_for_repository(rep);
		model.collect_and_add_virtual_signals(rep);
		if (filter_rep_uneeded)
			model.filter_rep_processors();
	}
	vector<string> req_sigs;
	model.get_required_signal_names(req_sigs);
	vector<vector<string>> depend_feats(req_sigs.size());
	vector<vector<int>> depend_feats_idx(req_sigs.size());
	unordered_set<string> all_virt_signals;
	for (size_t i = 0; i < req_sigs.size(); ++i)
	{
		const string &sig = req_sigs[i];
		vector<string> &used_sigs = depend_feats[i];

		//feat_processors + generator
		int feat_i = 0;
		for (FeatureGenerator *feat_gen : model.generators) {
			unordered_set<string> gen_req_sigs_virt, gen_req_sigs;
			feat_gen->get_required_signal_names(gen_req_sigs_virt);
			for (const string &s_name : gen_req_sigs_virt)
			{
				vector<string> physical_names;
				bool has_virt = get_real_sigs(model, s_name, physical_names);
				if (has_virt)
					all_virt_signals.insert(s_name);
				gen_req_sigs.insert(physical_names.begin(), physical_names.end());
			}

			if (gen_req_sigs.find(sig) != gen_req_sigs.end() && !feat_gen->names.empty()) {
				used_sigs.insert(used_sigs.end(), feat_gen->names.begin(), feat_gen->names.end());
				depend_feats_idx[i].push_back(feat_i);
			}
			++feat_i;
		}

	}

	//those are the required signals:
	if (!rep_path.empty())
		MLOG("model needs %zu signals:\n", req_sigs.size());
	else
		MLOG("model needs %zu signals (no repository is given, so can't break full deps):\n", req_sigs.size());
	for (size_t i = 0; i < req_sigs.size(); ++i)
		MLOG("%zu :: %s\n", i + 1, req_sigs[i].c_str());
	vector<string> virt_sigs(all_virt_signals.begin(), all_virt_signals.end());
	sort(virt_sigs.begin(), virt_sigs.end());
	MLOG("####################################################\n\nmodel has %zu virtual signals:\n",
		all_virt_signals.size());

	for (size_t i = 0; i < virt_sigs.size(); ++i) {
		vector<string> map_to;
		get_real_sigs(model, virt_sigs[i], map_to);
		MLOG("%zu :: %s => [%s]\n", i + 1, virt_sigs[i].c_str(), medial::io::get_list(map_to, ", ").c_str());
	}

	//depenedency:
	MLOG("####################################################\n\nMORE DETAILS:\n");
	for (size_t i = 0; i < req_sigs.size(); ++i) {
		//handle long strings

		if (!depend_feats_idx[i].empty()) {
			MLOG("%zu :: %s :: (%zu) [", i + 1, req_sigs[i].c_str(), depend_feats_idx[i].size());
			for (size_t j = 0; j < depend_feats[i].size(); ++j)
				MLOG("\n\t%s", depend_feats[i][j].c_str());
			MLOG("\n]\n");
		}
		else
			MLOG("Signal %s is not used\n", req_sigs[i].c_str());
	}

	//print categorical used values in generators and rep_processors:
	unordered_map<string, vector<string>> signal_to_ls_categories; // map from signal name to used categories in the model
	model.get_required_signal_categories(signal_to_ls_categories);
	//print categories in used in the model:
	MLOG("####################################################\n\nWriting original lists:\n");
	for (const auto &it : signal_to_ls_categories) {
		string full_path_list = dict_path + path_sep() + it.first + ".list"; //defs and sets of hirarchy
		ofstream dict_fw;
		if (!dict_path.empty()) {
			dict_fw.open(full_path_list);
			if (!dict_fw.good())
				MTHROW_AND_ERR("can't open %s for write\n", full_path_list.c_str());
		}
		if (!dict_path.empty()) {
			if (rep_path.empty()) {
				for (size_t i = 0; i < it.second.size(); ++i)
					dict_fw << it.second[i] << "\n";
			}
			else {
				//use rep to fetch all names:
				int sec_id = rep.dict.section_id(it.first);
				for (size_t i = 0; i < it.second.size(); ++i) {
					string nm = it.second[i];
					dict_fw << nm;
					int id_nm = rep.dict.id(sec_id, nm);
					if (id_nm < 0) {
						MWARN("WARN can't find in SIGNAL %s - %s\n",
							it.first.c_str(), nm.c_str());
						dict_fw << "\n";
						continue;
					}
					for (const string &cand_nm : rep.dict.dict(sec_id)->Id2Names.at(id_nm))
						if (cand_nm != nm) //print more names (don't repeat original name apeared in the model)
							dict_fw << "\t" << cand_nm;
					dict_fw << "\n";
				}
			}
		}
		else {
			MLOG("categories in signal %s (%zu): [", it.first.c_str(), it.second.size());
			for (size_t i = 0; i < it.second.size(); ++i)
				MLOG("\n\t%s", it.second[i].c_str());
			MLOG("\n]\n");
		}

		if (!dict_path.empty())
			dict_fw.close();
		MLOG("Wrote %s lists\n", it.first.c_str());
	}
	if (!rep_path.empty() && !dict_path.empty() && is_source_rep) {
		unordered_map<int, unordered_set<string>> wrote_str;
		unordered_map<int, unordered_set<int>> wrote_def;
		MLOG("####################################################\n\nWriting dicts:\n");
		for (const auto &it : signal_to_ls_categories) {
			string full_path_def = dict_path + path_sep() + "dict.defs_" + it.first; //leaves
			string full_path_set = dict_path + path_sep() + "dict.sets_" + it.first; //defs and sets of hirarchy
			ofstream dict_fw_defs(full_path_def);
			ofstream dict_fw_sets(full_path_set);
			if (!dict_fw_defs.good())
				MTHROW_AND_ERR("can't open %s for write\n", full_path_def.c_str());
			if (!dict_fw_sets.good())
				MTHROW_AND_ERR("can't open %s for write\n", full_path_set.c_str());
			dict_fw_defs << "SECTION" << "\t" << it.first << "\n";
			dict_fw_defs << "#" << "Minimal set with " << it.second.size() <<
				" items to run model " << f_model << "\n\n";
			dict_fw_sets << "SECTION" << "\t" << it.first << "\n";
			dict_fw_sets << "#" << "Minimal set with " << it.second.size() <<
				" items to run model " << f_model << "\n\n";

			//define and use start_id for each signal with config file.
			//decied if def or set:
			int signal_start_id = 100000; //or same id as in current rep?
			int section_id = rep.dict.section_id(it.first);
			for (size_t j = 0; j < it.second.size(); ++j) {
				vector<int> all_sons_parents, all_sons_leaves;
				bool is_set = flat_all_sons(rep.dict, it.first, it.second[j], all_sons_parents, all_sons_leaves);
				//has more than one element (the first one is itself)
				if (is_set) {
					//fetch all hierarchy - save leavse in dict_fw_defs and paretns in dict_fw_sets:
					vector<vector<string>> all_sons_par_names(all_sons_parents.size());
					vector<vector<string>> all_sons_leaves_names(all_sons_leaves.size());
					for (size_t k = 0; k < all_sons_parents.size(); ++k)
						all_sons_par_names[k] = rep.dict.dict(section_id)->Id2Names.at(all_sons_parents[k]);
					for (size_t k = 0; k < all_sons_leaves.size(); ++k)
						all_sons_leaves_names[k] = rep.dict.dict(section_id)->Id2Names.at(all_sons_leaves[k]);

					//write parents
					for (size_t k = 0; k < all_sons_par_names.size(); ++k)
					{
						dict_fw_sets << "#DEF" << "\t" << all_sons_par_names[k].front() << "\n";

						if (!use_same_rep_numbers) {
							bool advance_sig = false;
							for (size_t kk = 0; kk < all_sons_par_names[k].size(); ++kk)
								if (wrote_str[section_id].find(all_sons_par_names[k][kk]) == wrote_str[section_id].end()) {
									dict_fw_defs << "DEF" << "\t" << signal_start_id << "\t" <<
										all_sons_par_names[k][kk] << "\n";
									wrote_str[section_id].insert(all_sons_par_names[k][kk]);
									advance_sig = true;
								}
							if (advance_sig)
								++signal_start_id;
						}
						else {
							for (size_t kk = 0; kk < all_sons_par_names[k].size(); ++kk)
								if (wrote_str[section_id].find(all_sons_par_names[k][kk]) ==
									wrote_str[section_id].end() &&
									wrote_def[section_id].find(all_sons_parents[k]) == wrote_def[section_id].end()) {
									dict_fw_defs << "DEF" << "\t" << all_sons_parents[k] << "\t" <<
										all_sons_par_names[k][kk] << "\n";
									wrote_str[section_id].insert(all_sons_par_names[k][kk]);
								}
							wrote_def[section_id].insert(all_sons_parents[k]);
						}

						//write parent sets rules:
						vector<int> direct_childs;
						rep.dict.get_set_members(section_id, all_sons_parents[k], direct_childs);
						//write SET:
						for (int child_code : direct_childs)
						{
							if (child_code == all_sons_parents[k])
								continue;
							string code_name = rep.dict.name(section_id, child_code);
							dict_fw_sets << "SET" << "\t" << all_sons_par_names[k].front()
								<< "\t" << code_name << "\n";
						}
						dict_fw_sets << "\n"; //end set definition
					}


					//write leaves:
					for (size_t k = 0; k < all_sons_leaves_names.size(); ++k)
					{
						if (!use_same_rep_numbers) {
							bool advance_sig = false;
							for (size_t kk = 0; kk < all_sons_leaves_names[k].size(); ++kk)
								if (wrote_str[section_id].find(all_sons_leaves_names[k][kk]) == wrote_str[section_id].end()) {
									dict_fw_defs << "DEF" << "\t" << signal_start_id << "\t" <<
										all_sons_leaves_names[k][kk] << "\n";
									wrote_str[section_id].insert(all_sons_leaves_names[k][kk]);
									advance_sig = true;
								}
							if (advance_sig)
								++signal_start_id;
						}
						else {
							for (size_t kk = 0; kk < all_sons_leaves_names[k].size(); ++kk)
								if (wrote_str[section_id].find(all_sons_leaves_names[k][kk]) ==
									wrote_str[section_id].end() &&
									wrote_def[section_id].find(all_sons_leaves[k]) == wrote_def[section_id].end()) {
									dict_fw_defs << "DEF" << "\t" << all_sons_leaves[k] << "\t" <<
										all_sons_leaves_names[k][kk] << "\n";
									wrote_str[section_id].insert(all_sons_leaves_names[k][kk]);
								}
							wrote_def[section_id].insert(all_sons_leaves[k]);
						}
					}

				}
				else {
					//direct leaf
					if (!use_same_rep_numbers) {
						//get all names to write - for sets to work as needed!
						int sig_id = rep.dict.id(section_id, it.second[j]);
						const vector<string> &name_aliasing = rep.dict.dict(section_id)->Id2Names.at(sig_id);
						bool advance_sig = false;
						for (size_t kk = 0; kk < name_aliasing.size(); ++kk)
						{
							if (wrote_str[section_id].find(name_aliasing[kk]) == wrote_str[section_id].end()) {
								dict_fw_defs << "DEF" << "\t" << signal_start_id <<
									"\t" << name_aliasing[kk] << "\n";
								wrote_str[section_id].insert(name_aliasing[kk]);
								advance_sig = true;
							}
						}
						if (advance_sig)
							++signal_start_id;
					}
					else {
						int sig_code = rep.dict.id(section_id, it.second[j]);
						if (sig_code < 0 && it.first == "Smoking_Status") {
							//Can skip missings:
							continue;
						}
						if (sig_code < 0)
							MTHROW_AND_ERR("Error can't find code %s in siganl %s\n",
								it.second[j].c_str(), it.first.c_str());

						const vector<string> &name_aliasing = rep.dict.dict(section_id)->Id2Names.at(sig_code);
						for (size_t kk = 0; kk < name_aliasing.size(); ++kk)
						{
							if (wrote_str[section_id].find(name_aliasing[kk]) ==
								wrote_str[section_id].end() &&
								wrote_def[section_id].find(sig_code) == wrote_def[section_id].end()) {

								dict_fw_defs << "DEF" << "\t" << sig_code <<
									"\t" << name_aliasing[kk] << "\n";
								wrote_str[section_id].insert(name_aliasing[kk]);
							}
						}
						wrote_def[section_id].insert(sig_code);
					}
				}
			}

			dict_fw_defs.close();
			dict_fw_sets.close();
			MLOG("Wrote %s dicts\n", it.first.c_str());
		}
	}

	//transform to new rep:
	if (!is_source_rep && !rep_path.empty() && !dict_path.empty()) {
		MLOG("####################################################\n\nTranformation needed on rep:\n");
		for (size_t i = 0; i < req_sigs.size(); ++i)
			if (rep.sigs.sid(req_sigs[i]) < 0)
				MWARN("repository is missing signal %s\n", req_sigs[i].c_str());

		//scan categories:
		for (const auto &it : signal_to_ls_categories) {
			string signal_name = it.first;
			int sid = rep.sigs.sid(signal_name);
			if (sid < 0) {
				MWARN("repository is missing a categorical signal %s - skiped list of all categories!\n",
					signal_name.c_str());
				continue;
			}
			int section_id = rep.dict.section_id(signal_name);
			//max code
			int max_code_id = 1;
			if (!rep.dict.dicts[section_id].Id2Name.empty())
				max_code_id = rep.dict.dicts[section_id].Id2Name.rbegin()->first;
			max_code_id += 100;

			string file_path_categ = dict_path + path_sep() + "dict.transform_" + signal_name;
			ofstream fw_categ;

			for (size_t i = 0; i < it.second.size(); ++i) {
				int test_code = rep.dict.id(section_id, it.second[i]);
				if (test_code < 0) {
					//missing signal! - write in new text file to define later set map:
					if (!fw_categ.is_open()) {
						fw_categ.open(file_path_categ);
						if (!fw_categ.good())
							MTHROW_AND_ERR("Error can't open %s for writing\n", file_path_categ.c_str());
						fw_categ << "SECTION" << "\t" << signal_name << "\n\n";
					}
					//write to file the missing code:
					fw_categ << "DEF" << "\t" << max_code_id << "\t"
						<< it.second[i] << "\n";
					++max_code_id;
				}
			}

			if (fw_categ.is_open())
				fw_categ.close();
			else
				MLOG("catgorical signal %s is OK\n", signal_name.c_str());
		}
	}
}

class Collected_stats
{
public:
	float contrib_val;
	float outcome;
	float score;

	Collected_stats() : contrib_val(0), outcome(0), score(0) {}
	Collected_stats(float a, float b, float c) :contrib_val(a), outcome(b), score(c) {}
};

string get_aliases(MedPidRepository &repo, const string &grp_name, bool feature_clean = false) {
	string grp_name_ = grp_name;
	if (feature_clean) {
		vector<string> group_names;
		vector<vector<int>> group2index;
		string &feature_val_with_prefix = grp_name_;
		vector<string> to_process = { grp_name };
		ExplainProcessings::read_feature_grouping("BY_SIGNAL_CATEG", to_process, group2index, group_names, false);
		//MLOG("Request %s => %s\n", to_process.front().c_str(), group_names.front().c_str());
		///try to clean feature_val_with_prefix
		feature_val_with_prefix = group_names[0];

	}
	vector<string> tokens;
	boost::split(tokens, grp_name_, boost::is_any_of("."));
	if (tokens.size() < 2)
		return "";
	int section_id = repo.dict.section_id(tokens[0]);

	stringstream ss_val;
	ss_val << tokens[1];
	for (size_t i = 2; i < tokens.size(); ++i) //if has more than 1 dot, as part of the code
		ss_val << "." << tokens[i];
	string curr_name = ss_val.str();

	int sig_val = repo.dict.id(section_id, curr_name);
	if (repo.dict.name(section_id, sig_val).empty())
		return "";
	const vector<string> &names = repo.dict.dicts[section_id].Id2Names.at(sig_val);
	if (names.size() <= 1)
		return "";
	stringstream ss;
	bool is_empty = true;
	for (size_t i = 0; i < names.size(); ++i)
	{
		if (names[i] == curr_name)
			continue;
		if (!is_empty)
			ss << "|";
		ss << names[i];
		is_empty = false;
	}
	return ss.str();
}


void flow_print_shap(MedModel &model, MedFeatures *features, MedFeatures *non_norm_features,
	float group_ratio, int group_cnt, vector<string> &names, bool normalize, bool normalize_after,
	bool remove_b0, const string &group_features, bool bin_uniqu_vals, const string &binning_method,
	const string &output_file, bool retrain_predictor, const string &rep_path, bool zero_missing_contribs)
{
	MedPidRepository rep_dict;
	if (!rep_path.empty()) {
		if (rep_dict.init(rep_path) < 0)
			MTHROW_AND_ERR("Error can't init rep %s\n", rep_path.c_str());
	}

	const string feature_val_catption = "FEAT_VAL";
	const string shap_catption = "SHAP";
	const string score_catption = "SCORE";
	const string outcome_catption = "OUTCOME";
	float top_pr = group_ratio;
	vector<float> req = { (float)0.1, (float)0.5, (float)0.9 };
	vector<float> req_feature = { 0, (float)0.1, (float)0.5, (float)0.9, 1 };
	vector<float> req_outcome = { (float)0.1, (float)0.5, (float)0.9 };
	vector<float> req_score = { 0,(float)0.1, (float)0.5, (float)0.9, 1 };

	ofstream fw;
	if (!output_file.empty())
	{
		fw.open(output_file);
		if (!fw.good())
			MTHROW_AND_ERR("Can't open output file %s for write\n", output_file.c_str());
	}
	if (group_ratio > 0.5)
		MTHROW_AND_ERR("group_ratio > 0.5 not supported\n");
	vector<float> low_rng(group_cnt), high_rng(group_cnt);
	//the groups definitions in percentiles
	if (names.empty()) {
		names.resize(group_cnt);
		if (group_cnt == 1) {
			names[0] = "MedianGroup";
		}
		else {
			for (int i = 0; i < group_cnt; ++i)
				names[i] = "Group" + to_string(i + 1);
		}
	}
	if (group_cnt == 1) {
		low_rng[0] = 0.5 - group_ratio / 2;
		if (low_rng[0] < 0)
			low_rng[0] = 0;
		high_rng[0] = 0.5 + group_ratio / 2;
		if (high_rng[0] > 1)
			high_rng[0] = 1;
	}
	else {
		low_rng[0] = 0;
		high_rng[0] = group_ratio;
		low_rng[group_cnt - 1] = 1 - group_ratio;
		high_rng[group_cnt - 1] = 1;
		if (group_cnt == 3) {
			low_rng[1] = 0.5 - group_ratio / 2;
			high_rng[1] = 0.5 + group_ratio / 2;
		}
		else {
			double bin_space = (1.0 - (2 * group_ratio)) / (double(group_cnt) - 1.0);
			for (int i = 1; i < group_cnt - 1; ++i)
			{
				float center = i * bin_space;
				low_rng[i] = center - group_ratio / 2;
				if (low_rng[i] < 0)
					low_rng[i] = 0;
				high_rng[i] = center + group_ratio / 2;
				if (high_rng[i] > 1)
					high_rng[i] = 1;
			}
		}
	}
	if (names.size() != group_cnt)
		MTHROW_AND_ERR("names should be same size as group_cnt\n");

	BinSettings bin_setts;
	if (!binning_method.empty())
		bin_setts.init_from_string(binning_method);

	if (retrain_predictor) {
		if (model.predictor->learn(*features) < 0)
			MTHROW_AND_ERR("Error in relrean\n");
	}

	// feature importance print
	MedMat<float> mat, mat_contrib, mat_non_norm;
	features->get_as_matrix(mat);
	non_norm_features->get_as_matrix(mat_non_norm);

	model.verbosity = 1;
	model.predictor->calc_feature_contribs(mat, mat_contrib);
	MLOG("Done calc\n");
	if (zero_missing_contribs) {
		vector<const vector< unsigned char> *>_mask;
		_mask.reserve(features->masks.size());
		for (const auto &it : features->masks)
			_mask.push_back(&it.second);
		for (size_t i = 0; i < features->samples.size(); ++i)
		{
			for (size_t j = 0; j < _mask.size(); ++j)
				if (_mask[j]->at(i) & MedFeatures::imputed_mask)
					mat_contrib(i, j) = 0;
		}
	}
	//sort and print features
	vector<string> feat_names;
	features->get_feature_names(feat_names);
	bool add_b0 = false;
	if (mat.ncols != mat_contrib.ncols) {
		MLOG("mat.ncols=%d mat_contrib.ncols=%d feat_names.size()=%zu\n",
			mat.ncols, mat_contrib.ncols, feat_names.size());
		if (!remove_b0) {
			feat_names.push_back("b0_const");
			add_b0 = true;
		}
		else {
			vector<int> all_row, cols(mat.ncols);
			for (int i = 0; i < mat.ncols; ++i)
				cols[i] = i;
			mat_contrib.get_sub_mat(all_row, cols);
		}
	}

	if (!group_features.empty()) {
		vector<vector<int>> group2Inds;
		vector<string> groupNames;
		ExplainProcessings::read_feature_grouping(group_features, feat_names, group2Inds, groupNames);
		MedMat<float> tranformed(mat_contrib.nrows, (int)groupNames.size());
		tranformed.set_signals(groupNames);
		MedMat<float> representative_mat(mat_non_norm.nrows, (int)groupNames.size());
		representative_mat.signals.resize(group2Inds.size());
		//convert into groups if needed

		for (int i = 0; i < group2Inds.size(); ++i)
		{
			for (int j = 0; j < mat_contrib.nrows; ++j) {
				double contrib = 0.0f;
				for (int ind : group2Inds[i])
					contrib += mat_contrib(j, ind);
				tranformed(j, i) = contrib;
			}

			double max_average_con = 0;
			int sel_idx_r = -1;
			//find represenative in current group
			for (int ind : group2Inds[i]) {
				double avg_contrib = 0;
				for (int j = 0; j < mat_contrib.nrows; ++j)
					avg_contrib += abs(mat_contrib(j, ind));
				if (sel_idx_r < 0 || avg_contrib > max_average_con) {
					sel_idx_r = ind;
					max_average_con = avg_contrib;
				}
			}
			//use represntative sel_idx_r as value:
			for (int j = 0; j < mat_non_norm.nrows; ++j)
				representative_mat(j, i) = mat_non_norm(j, sel_idx_r);
			representative_mat.signals[i] = feat_names[sel_idx_r];
		}

		mat_contrib = move(tranformed);
		feat_names = mat_contrib.signals;
		mat_non_norm = move(representative_mat);
	}

	if (normalize) {
		if (!normalize_after) {
			int interate_till = mat_contrib.ncols;
			if (add_b0) //iterate and norm without b0 - last cell
				--interate_till;
			for (int i = 0; i < mat_contrib.nrows; ++i)
			{
				double sm = 0;
				for (int j = 0; j < interate_till; ++j)
					sm += abs(mat_contrib(i, j));
				sm /= 100; //to be in percents.
				if (sm > 0)
					for (int j = 0; j < interate_till; ++j)
						mat_contrib(i, j) /= sm;
			}
		}
		else {
			int interate_till = mat_contrib.ncols;
			if (add_b0) //iterate and norm without b0 - last cell
				--interate_till;
			double sm = 0;
			for (int i = 0; i < interate_till; ++i) {
				double contrib = 0;
				for (int j = 0; j < mat_contrib.nrows; ++j)
					contrib += abs(mat_contrib(j, i));
				contrib /= mat_contrib.nrows;
				sm += contrib;
			}
			sm /= 100; //to be in percents.
			if (sm > 0)
				for (int i = 0; i < mat_contrib.nrows; ++i)
					for (int j = 0; j < mat_contrib.ncols; ++j)
						mat_contrib(i, j) /= sm;
		}
	}

	//sort(feat_names.begin(), feat_names.end());
	vector<pair<string, float>> ranked(mat_contrib.ncols);
	unordered_map<string, map<string, float>> feat_to_measures_vals;
	//for top 20%, and low 20% calc prctile, average contrib no abs
	unordered_map<string, string> rep_names;
	int max_group_sz = group_cnt;
	MedProgress progress_("Feature_Contribution", (int)mat_contrib.ncols, 15, 10);
#pragma omp parallel for
	for (int i = 0; i < mat_contrib.ncols; ++i) {
		const string &feat_name = feat_names[i];
#pragma omp critical
		{
			rep_names[feat_name] = feat_name;
			if (!group_features.empty())
				rep_names[feat_name] = mat_non_norm.signals[i];
		}
		//map<string, float> &measures = feat_to_measures_vals[feat_name];
		map<string, float> measures;
		float contrib = 0;
		vector<pair<Collected_stats, float>> collected(mat_contrib.nrows);
		for (int j = 0; j < mat_contrib.nrows; ++j) {
			contrib += abs(mat_contrib(j, i));
			collected[j].first.contrib_val = mat_contrib(j, i);
			collected[j].first.outcome = features->samples[j].outcome;
			collected[j].first.score = features->samples[j].prediction[0];
			collected[j].second = mat_non_norm(j, i);
		}
		int feature_grp_count = group_cnt;
		contrib /= mat_contrib.nrows;
		sort(collected.begin(), collected.end(), [](const pair<Collected_stats, float> &a, const pair<Collected_stats, float> &b)
		{  return a.second < b.second;
		});

		int count = int((float)collected.size() * top_pr);
		vector<vector<float>> grp_vals, grp_feature_vals, grp_outcome, grp_score;

		//update: grp_vals (contribution), grp_feature_vals(feature value) - to processed stats. used collected!
		if (!binning_method.empty()) {
			vector<float> curr_feature;
			curr_feature.resize(collected.size());
			for (int j = 0; j < collected.size(); ++j)
				curr_feature[j] = collected[j].second;
			vector<int> empty_sel;
			medial::process::split_feature_to_bins(bin_setts, curr_feature, empty_sel, curr_feature);
			unordered_map<float, vector<int>> index_bins;
			vector<float> sorted_vals;
			for (size_t k = 0; k < curr_feature.size(); ++k) {
				if (index_bins.find(curr_feature[k]) == index_bins.end())
					sorted_vals.push_back(curr_feature[k]);
				index_bins[curr_feature[k]].push_back((int)k);
			}
			sort(sorted_vals.begin(), sorted_vals.end());

			feature_grp_count = (int)index_bins.size();

			grp_vals.resize(feature_grp_count); //for each bin - collect values
			grp_feature_vals.resize(feature_grp_count);
			grp_outcome.resize(feature_grp_count);
			grp_score.resize(feature_grp_count);
			for (size_t k = 0; k < feature_grp_count; ++k) {
				float bin_val = sorted_vals[k];
				const vector<int> &inds = index_bins.at(bin_val);
				grp_vals[k].resize(inds.size());
				grp_feature_vals[k].resize(inds.size());
				grp_outcome[k].resize(inds.size());
				grp_score[k].resize(inds.size());
				for (size_t j = 0; j < inds.size(); ++j)
				{
					grp_vals[k][j] = collected[inds[j]].first.contrib_val;
					grp_outcome[k][j] = collected[inds[j]].first.outcome;
					grp_score[k][j] = collected[inds[j]].first.score;
					grp_feature_vals[k][j] = collected[inds[j]].second;
				}
			}
		}
		else {
			grp_vals.resize(feature_grp_count);
			grp_feature_vals.resize(feature_grp_count);
			grp_outcome.resize(feature_grp_count);
			grp_score.resize(feature_grp_count);
			for (size_t j = 0; j < feature_grp_count; ++j) {
				grp_vals[j].resize(count);
				grp_feature_vals[j].resize(count);
				grp_outcome[j].resize(count);
				grp_score[j].resize(count);
			}
			vector<float> uniq_vals;
			unordered_set<float> seen_val;
			for (size_t j = 0; j < collected.size(); ++j)
				if (seen_val.find(collected[j].second) == seen_val.end())
					seen_val.insert(collected[j].second);
			uniq_vals.insert(uniq_vals.end(), seen_val.begin(), seen_val.end());
			sort(uniq_vals.begin(), uniq_vals.end());

			for (size_t k = 0; k < feature_grp_count; ++k) {
				int start_from = int(low_rng[k] * mat_contrib.nrows);
				int end_index = int(high_rng[k] * mat_contrib.nrows);
				if (end_index - start_from > count) //dont pass count - for error in fractions of +-1 in calc
					end_index = start_from + count;
				if (end_index > collected.size()) //dont pass end
					end_index = (int)collected.size();

				if (feat_name.find(".nsamples") != string::npos || feat_name.find("category_set_") != string::npos
					|| feat_name.find("category_dep_set_") != string::npos
					|| feat_name.find("category_dep_count_") != string::npos) {
					//diffrent binning for binary, nsamples. 0 is low, the rest split 1-2, 3+ and repeat
					if (k == 0) {
						grp_vals[k].clear();
						grp_feature_vals[k].clear();
						grp_outcome[k].clear();
						grp_score[k].clear();
						for (size_t j = 0; j < collected.size() && collected[j].second <= 0; ++j) {
							grp_vals[k].push_back(collected[j].first.contrib_val);
							grp_outcome[k].push_back(collected[j].first.outcome);
							grp_score[k].push_back(collected[j].first.score);
							grp_feature_vals[k].push_back(collected[j].second);
						}
					}
					else if (k == 1) {
						grp_vals[k].clear();
						grp_feature_vals[k].clear();
						grp_outcome[k].clear();
						grp_score[k].clear();
						for (size_t j = 0; j < collected.size() && collected[j].second <= 2; ++j) {
							if (collected[j].second <= 0)
								continue;
							grp_vals[k].push_back(collected[j].first.contrib_val);
							grp_outcome[k].push_back(collected[j].first.outcome);
							grp_score[k].push_back(collected[j].first.score);
							grp_feature_vals[k].push_back(collected[j].second);
						}
					}
					else {
						grp_vals[k].clear();
						grp_feature_vals[k].clear();
						grp_outcome[k].clear();
						grp_score[k].clear();
						for (size_t j = 0; j < collected.size(); ++j) {
							if (collected[j].second <= 2)
								continue;
							grp_vals[k].push_back(collected[j].first.contrib_val);
							grp_outcome[k].push_back(collected[j].first.outcome);
							grp_score[k].push_back(collected[j].first.score);
							grp_feature_vals[k].push_back(collected[j].second);
						}
						if (grp_vals[k].empty()) {
							for (size_t j = 0; j < collected.size() && collected[j].second <= 2; ++j) {
								if (collected[j].second <= 0)
									continue;
								grp_vals[k].push_back(collected[j].first.contrib_val);
								grp_outcome[k].push_back(collected[j].first.outcome);
								grp_score[k].push_back(collected[j].first.score);
								grp_feature_vals[k].push_back(collected[j].second);
							}
						}
					}

				}
				else {
					if (bin_uniqu_vals) {
						int pos_min = int(low_rng[k] * uniq_vals.size());
						float min_val = uniq_vals[pos_min];
						int pos_max = int(high_rng[k] * uniq_vals.size());
						if (pos_max >= uniq_vals.size())
							pos_max = (int)uniq_vals.size() - 1;
						float max_val = uniq_vals[pos_max];
						grp_vals[k].clear();
						grp_feature_vals[k].clear();
						grp_outcome[k].clear();
						grp_score[k].clear();
						for (size_t j = 0; j < collected.size() && collected[j].second <= max_val; ++j) {
							if (collected[j].second < min_val)
								continue;
							grp_vals[k].push_back(collected[j].first.contrib_val);
							grp_outcome[k].push_back(collected[j].first.outcome);
							grp_score[k].push_back(collected[j].first.score);
							grp_feature_vals[k].push_back(collected[j].second);
						}
					}
					else {
						for (size_t j = start_from; j < end_index; ++j) {
							grp_vals[k][j - start_from] = collected[j].first.contrib_val;
							grp_outcome[k].push_back(collected[j].first.outcome);
							grp_score[k].push_back(collected[j].first.score);
							grp_feature_vals[k][j - start_from] = collected[j].second;
						}
						grp_vals[k].resize(end_index - start_from);
						grp_feature_vals[k].resize(end_index - start_from);
						grp_outcome[k].resize(end_index - start_from);
						grp_score[k].resize(end_index - start_from);
					}
				}

			}
		}

		for (size_t k = 0; k < feature_grp_count; ++k) {
			float mean_v, std_v;
			float mean_v_feat, std_v_feat;
			float mean_v_outcome, std_v_outcome;
			float mean_v_score, std_v_score;
			vector<float> prctile_res, prctile_feat_res, prctile_outcome_res, prctile_score_res;
			string grp_name;
			if (binning_method.empty())
				grp_name = names[k];
			else
				grp_name = to_string(k);
			vector<float> &curr_grp_shap_vals = grp_vals[k];
			vector<float> &curr_grp_feat_vals = grp_feature_vals[k];
			vector<float> &curr_scores = grp_score[k];
			vector<float> &curr_outcomes = grp_outcome[k];
			if (curr_grp_shap_vals.empty()) {
				measures[shap_catption + "::" + grp_name + "_Mean"] = MED_MAT_MISSING_VALUE;
				measures[shap_catption + "::" + grp_name + "_Std"] = MED_MAT_MISSING_VALUE;
				for (size_t j = 0; j < req.size(); ++j)
					measures[shap_catption + "::" + grp_name + "_Prctile" + to_string(int(req[j] * 100))] = MED_MAT_MISSING_VALUE;
				measures[feature_val_catption + "::" + grp_name + "_Mean"] = MED_MAT_MISSING_VALUE;
				measures[feature_val_catption + "::" + grp_name + "_Std"] = MED_MAT_MISSING_VALUE;
				measures[feature_val_catption + "::" + grp_name + "_Cnt"] = 0;
				for (size_t j = 0; j < req_feature.size(); ++j)
					measures[feature_val_catption + "::" + grp_name + "_Prctile" + to_string(int(req_feature[j] * 100))] = MED_MAT_MISSING_VALUE;

				measures[score_catption + "::" + grp_name + "_Mean"] = MED_MAT_MISSING_VALUE;
				measures[score_catption + "::" + grp_name + "_Std"] = MED_MAT_MISSING_VALUE;
				for (size_t j = 0; j < req.size(); ++j)
					measures[score_catption + "::" + grp_name + "_Prctile" + to_string(int(req[j] * 100))] = MED_MAT_MISSING_VALUE;
				measures[outcome_catption + "::" + grp_name + "_Mean"] = MED_MAT_MISSING_VALUE;
				measures[outcome_catption + "::" + grp_name + "_Std"] = MED_MAT_MISSING_VALUE;
				for (size_t j = 0; j < req.size(); ++j)
					measures[outcome_catption + "::" + grp_name + "_Prctile" + to_string(int(req[j] * 100))] = MED_MAT_MISSING_VALUE;

				continue;
			}

			medial::stats::get_mean_and_std_without_cleaning(curr_grp_shap_vals, mean_v, std_v);
			medial::stats::get_percentiles(curr_grp_shap_vals, req, prctile_res);

			medial::stats::get_mean_and_std_without_cleaning(curr_grp_feat_vals, mean_v_feat, std_v_feat);
			medial::stats::get_percentiles(curr_grp_feat_vals, req_feature, prctile_feat_res);

			medial::stats::get_mean_and_std_without_cleaning(curr_outcomes, mean_v_outcome, std_v_outcome);
			medial::stats::get_percentiles(curr_outcomes, req_outcome, prctile_outcome_res);

			medial::stats::get_mean_and_std_without_cleaning(curr_scores, mean_v_score, std_v_score);
			medial::stats::get_percentiles(curr_scores, req_score, prctile_score_res);

			measures[shap_catption + "::" + grp_name + "_Mean"] = mean_v;
			measures[shap_catption + "::" + grp_name + "_Std"] = std_v;
			for (size_t j = 0; j < req.size(); ++j)
				measures[shap_catption + "::" + grp_name + "_Prctile" + to_string(int(req[j] * 100))] = prctile_res[j];

			measures[feature_val_catption + "::" + grp_name + "_Mean"] = mean_v_feat;
			measures[feature_val_catption + "::" + grp_name + "_Std"] = std_v_feat;
			measures[feature_val_catption + "::" + grp_name + "_Cnt"] = (float)curr_grp_feat_vals.size();
			for (size_t j = 0; j < req_feature.size(); ++j)
				measures[feature_val_catption + "::" + grp_name + "_Prctile" + to_string(int(req_feature[j] * 100))] = prctile_feat_res[j];

			measures[outcome_catption + "::" + grp_name + "_Mean"] = mean_v_outcome;
			measures[outcome_catption + "::" + grp_name + "_Std"] = std_v_outcome;
			for (size_t j = 0; j < req_outcome.size(); ++j)
				measures[outcome_catption + "::" + grp_name + "_Prctile" + to_string(int(req_outcome[j] * 100))] = prctile_outcome_res[j];

			measures[score_catption + "::" + grp_name + "_Mean"] = mean_v_score;
			measures[score_catption + "::" + grp_name + "_Std"] = std_v_score;
			for (size_t j = 0; j < req_score.size(); ++j)
				measures[score_catption + "::" + grp_name + "_Prctile" + to_string(int(req_score[j] * 100))] = prctile_score_res[j];

		}

#pragma omp critical
		feat_to_measures_vals[feat_name] = move(measures);

		ranked[i] = pair<string, float>(feat_name, contrib);
		if (feature_grp_count > max_group_sz)
			max_group_sz = feature_grp_count;
		progress_.update();
	}
	sort(ranked.begin(), ranked.end(), [](const pair<string, float> &c1, const pair<string, float> &c2)
	{
		return c1.second > c2.second;
	});
	vector<string> print_order;
	for (size_t k = 0; k < max_group_sz; ++k) {
		string grp_name;
		if (binning_method.empty())
			grp_name = names[k];
		else
			grp_name = to_string(k);
		print_order.push_back(shap_catption + "::" + grp_name + "_Mean");
		print_order.push_back(shap_catption + "::" + grp_name + "_Std");
		for (size_t j = 0; j < req.size(); ++j)
			print_order.push_back(shap_catption + "::" + grp_name + "_Prctile" + to_string(int(req[j] * 100)));
		print_order.push_back(feature_val_catption + "::" + grp_name + "_Mean");
		print_order.push_back(feature_val_catption + "::" + grp_name + "_Std");
		print_order.push_back(feature_val_catption + "::" + grp_name + "_Cnt");
		for (size_t j = 0; j < req_feature.size(); ++j)
			print_order.push_back(feature_val_catption + "::" + grp_name + "_Prctile" + to_string(int(req_feature[j] * 100)));

		print_order.push_back(outcome_catption + "::" + grp_name + "_Mean");
		print_order.push_back(outcome_catption + "::" + grp_name + "_Std");
		for (size_t j = 0; j < req_outcome.size(); ++j)
			print_order.push_back(outcome_catption + "::" + grp_name + "_Prctile" + to_string(int(req_outcome[j] * 100)));

		print_order.push_back(score_catption + "::" + grp_name + "_Mean");
		print_order.push_back(score_catption + "::" + grp_name + "_Std");
		for (size_t j = 0; j < req_score.size(); ++j)
			print_order.push_back(score_catption + "::" + grp_name + "_Prctile" + to_string(int(req_score[j] * 100)));
	}

	//TITLE:
	ostream *outp = &cout;
	if (!output_file.empty())
		outp = &fw;

	(*outp) << "Feature";

	if (!rep_path.empty())
		(*outp) << "\t" << "Category_Alias_Lookup";
	if (!group_features.empty())
		(*outp) << "\t" << "Representative";

	(*outp) << "\t" << "Importance";
	for (const string &m_name : print_order)
		(*outp) << "\t" << m_name;
	(*outp) << "\n";
	//Data:
	for (size_t i = 0; i < ranked.size(); ++i)
	{
		const map<string, float> &measures = feat_to_measures_vals.at(ranked[i].first);
		stringstream res_stream;
		res_stream << ranked[i].first;
		if (!rep_path.empty()) {
			string alias_names = get_aliases(rep_dict, ranked[i].first, group_features.empty());
			res_stream << "\t" << alias_names;
		}
		if (!group_features.empty())
			res_stream << "\t" << rep_names[ranked[i].first];
		res_stream << "\t" << ranked[i].second;
		for (const string &m_name : print_order) {
			if (measures.find(m_name) != measures.end())
				res_stream << "\t" << medial::print::print_obj(measures.at(m_name), "%2.5f");
			else
				res_stream << "\t";
		}
		(*outp) << res_stream.str() << "\n";
		//printf("%s\n", res_stream.str().c_str());
	}

	if (!output_file.empty()) {
		fw.close();
		MLOG("Wrote output to file %s\n", output_file.c_str());
	}
}

void prepare_features_from_samples(MedModel &model, const string &rep, MedSamples &samples_test, int max_samples, bool use_imputer,
	MedFeatures &static_mem, MedFeatures *&features, MedFeatures *&non_norm_features) {
	int nsamlpes = samples_test.nSamples();
	int max_mode_batch = model.get_apply_batch_count();
	if (max_samples > 0 && min(max_mode_batch, max_samples) < nsamlpes)
		medial::process::down_sample(samples_test, min(max_mode_batch, max_samples));
	else {
		if (max_mode_batch < nsamlpes)
			medial::process::down_sample(samples_test, max_mode_batch);
	}
	medial::medmodel::apply(model, samples_test, rep, MedModelStage::MED_MDL_END);
	static_mem = move(model.features);
	features = &static_mem;
	//remove imputer, normalizer from Feature Processors:
	vector<FeatureProcessor *> keep_p;
	vector<bool> filter_mask(FTR_PROCESS_LAST);
	filter_mask[FTR_PROCESS_NORMALIZER] = true;
	if (!use_imputer) {
		filter_mask[FTR_PROCESS_IMPUTER] = true;
		filter_mask[FTR_PROCESS_ITERATIVE_IMPUTER] = true;
		filter_mask[FTR_PROCESS_PREDICTOR_IMPUTER] = true;
	}

	vector<MultiFeatureProcessor *> managed_mem;
	bool kept_fp = false, warn_show = false;
	for (int i = (int)model.feature_processors.size() - 1; i >= 0; --i)
	{
		if (model.feature_processors[i]->processor_type == FTR_PROCESS_MULTI) {
			MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(model.feature_processors[i]);
			vector<FeatureProcessor *> keep_internal_p;
			for (size_t j = 0; j < multi->processors.size(); ++j) {
				if (!filter_mask[multi->processors[j]->processor_type] || kept_fp) {
					keep_internal_p.push_back(multi->processors[j]);
					if (filter_mask[multi->processors[j]->processor_type] && !warn_show) {
						MWARN("WARN: can't remove imputers, it used by other FPs\n");
						warn_show = true;
					}
				}
				else {
					//Dont change model - keep as is!
					/*delete multi->processors[j];
					multi->processors[j] = NULL;*/
				}
			}
			if (!keep_internal_p.empty()) {
				MultiFeatureProcessor *multi_new = new MultiFeatureProcessor;
				multi_new->duplicate = multi->duplicate;
				multi_new->processors = move(keep_internal_p);
				keep_p.insert(keep_p.begin(), multi_new);
				managed_mem.push_back(multi_new);
				//turn true if contains fp that is not selector:
				for (size_t j = 0; j < keep_internal_p.size() && !kept_fp; ++j)
					kept_fp = !keep_internal_p[j]->is_selector();
			}

			//DONT CHANGE original model - keep as is
			//clear mem
			/*
			multi->processors.clear(); //already cleared what's neede inside
			delete multi;
			model.feature_processors[i] = NULL;
			*/
		}
		else {
			if (!filter_mask[model.feature_processors[i]->processor_type] || kept_fp) {
				keep_p.insert(keep_p.begin(), model.feature_processors[i]);
				kept_fp = !model.feature_processors[i]->is_selector();
				if (filter_mask[model.feature_processors[i]->processor_type] && !warn_show) {
					MWARN("WARN: can't remove imputers, it used by other FPs\n");
					warn_show = true;
				}
			}
			else {
				//DONT CHANGE original model - keep as is
				/*delete model.feature_processors[i];
				model.feature_processors[i] = NULL;*/
			}

		}
	}
	vector<FeatureProcessor *> backup = model.feature_processors;
	model.feature_processors = keep_p;
	medial::medmodel::apply(model, samples_test, rep, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	model.feature_processors = backup;
	non_norm_features = &model.features;
	for (size_t i = 0; i < managed_mem.size(); ++i) {
		managed_mem[i]->processors.clear(); //that won't clear FP memory
		delete managed_mem[i];
		managed_mem[i] = NULL;
	}
}

void flow_print_shap(const string &f_model, const string &f_features, const string &rep,
	const string &f_samples, int max_samples, float group_ratio, int group_cnt, vector<string> &names,
	bool normalize, bool normalize_after, bool remove_b0, const string &group_features, bool bin_uniqu_vals,
	const string &binning_method, const string &output_file, bool retrain_predictor,
	bool use_imputer, const string &json_filter, const string &cohort_filter, bool zero_missing_contrib)
{
	MedModel model;
	MLOG("Reading model file %s\n", f_model.c_str());
	if (model.read_from_file(f_model) < 0)
		MTHROW_AND_ERR("FAILED reading model file %s\n", f_model.c_str());
	if (zero_missing_contrib) {
		MLOG("Info: zere missing contrib on features\n");
		model.generate_masks_for_features = 1;
	}

	MedFeatures allocated_mat;
	MedFeatures *features = NULL, *non_norm_features = NULL;
	MedFeatures static_mem, non_norm_static;

	if (rep != "" && f_samples != "") {
		MedSamples samples_test;
		samples_test.read_from_file(f_samples);
		MedBootstrap bt_filters;
		bool has_fiters = false;
		if (!cohort_filter.empty()) {
			MLOG("Filtering samples...\n");
			has_fiters = true;
			bt_filters.filter_cohort.clear();
			if (!file_exists(cohort_filter))
				bt_filters.get_cohort_from_arg(cohort_filter);
			else
				bt_filters.parse_cohort_file(cohort_filter);
		}

		if (!has_fiters) {
			//prepare MedFeatures from each sample:
			prepare_features_from_samples(model, rep, samples_test, max_samples, use_imputer,
				static_mem, features, non_norm_features);
		}
		else {
			//filter by bootstrap
			MedFeatures filter_mat;
			MedModel filter_model;
			if (!json_filter.empty())
				filter_model.init_from_json_file(json_filter);
			bool need_age = true, need_gender = true;
			for (FeatureGenerator *generator : filter_model.generators) {
				if (generator->generator_type == FTR_GEN_AGE)
					need_age = false;
				if (generator->generator_type == FTR_GEN_GENDER)
					need_gender = false;
			}
			if (need_age)
				filter_model.add_age();
			if (need_gender)
				filter_model.add_gender();
			MedSamples copy_samples = samples_test;
			vector<int> pids_in_bt;
			copy_samples.get_ids(pids_in_bt);

			MedPidRepository rep_bt;
			filter_model.load_repository(rep, pids_in_bt, rep_bt, true);
			if (filter_model.learn(rep_bt, &copy_samples, MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("Can't generate bootstrap filter matrix\n");
			//medial::medmodel::apply(filter_model, copy_samples, rep, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);

			filter_mat = move(filter_model.features);
			//MedBootstrap::prepare_bootstrap(filter_mat.data);
			vector<float> preds, labelsOrig;
			vector<int> preds_order, pidsOrig;
			// Create Dummy predictions (needed for prepare)
			for (MedSample &sample : filter_mat.samples)
				sample.prediction = { 0.0 };

			map<string, vector<float>> bt_data;
			bt_filters.prepare_bootstrap(filter_mat, preds, labelsOrig, pidsOrig, bt_data, preds_order);
			filter_mat.data = move(bt_data);
			//find names:
			vector<string> param_use;
			unordered_set<string> con_set;
			for (auto ii = bt_filters.filter_cohort.begin(); ii != bt_filters.filter_cohort.end(); ++ii)
				for (size_t i = 0; i < ii->second.size(); ++i)
					con_set.insert(ii->second[i].param_name);
			param_use.insert(param_use.end(), con_set.begin(), con_set.end());

			unordered_set<string> valid_params;
			valid_params.insert("Time-Window");
			valid_params.insert("Label");
			for (auto it = filter_mat.data.begin(); it != filter_mat.data.end(); ++it)
				valid_params.insert(it->first);
			vector<string> all_names_ls(valid_params.begin(), valid_params.end());

			bool all_valid = true;
			for (string param_name : param_use)
				if (valid_params.find(param_name) == valid_params.end()) {
					//try and fix first:
					int fn_pos = find_in_feature_names(all_names_ls, param_name, false);
					if (fn_pos < 0) {
						all_valid = false;
						MERR("ERROR:: Wrong use in \"%s\" as filter params. the parameter is missing\n", param_name.c_str());
					}
					else {
						//fix name:
						string found_nm = all_names_ls[fn_pos];
						MLOG("Mapped %s => %s\n", param_name.c_str(), found_nm.c_str());
						for (auto &it_cohort : bt_filters.filter_cohort)
						{
							vector<Filter_Param> &vec = it_cohort.second;
							for (Filter_Param &pp : vec)
								if (pp.param_name == param_name)
									pp.param_name = found_nm;
						}
					}
				}

			if (!all_valid) {

				MLOG("Feature Names availible for cohort filtering:\n");
				for (auto it = filter_mat.data.begin(); it != filter_mat.data.end(); ++it)
					MLOG("%s\n", it->first.c_str());
				MLOG("Time-Window\n");
				MLOG("\n");

				MTHROW_AND_ERR("Cohort file has wrong paramter names. look above for all avaible params\n");
			}

			MedProgress progress("Shapley_Cohorts", (int)bt_filters.filter_cohort.size(), 30, 1);
			int smp_size = samples_test.nSamples();
			for (auto &it : bt_filters.filter_cohort)
			{
				vector<Filter_Param> &filter_args = it.second;
				//void *params = &filter_args;
				vector<MedSample> flat_filtered;
				//filter samples_test by filter_args into cohort_samples
				for (size_t i = 0; i < smp_size; ++i)
					if (filter_range_params(filter_mat.data, (int)i, &filter_args))
						flat_filtered.push_back(filter_mat.samples[i]);
				MedSamples cohort_samples;
				cohort_samples.import_from_sample_vec(flat_filtered);
				MLOG("%s :: After filter has %zu rows for %zu pids\n",
					it.first.c_str(),
					flat_filtered.size(), cohort_samples.idSamples.size());
				//prepare MedFeatures from each sample:
				prepare_features_from_samples(model, rep, cohort_samples, max_samples, use_imputer,
					static_mem, features, non_norm_features);
				//run shap:
				string addition = it.first;
				fix_filename_chars(&addition);
				string new_output_files = output_file + "." + addition;
				flow_print_shap(model, features, non_norm_features, group_ratio, group_cnt, names, normalize, normalize_after, remove_b0,
					group_features, bin_uniqu_vals, binning_method, new_output_files, retrain_predictor, rep, zero_missing_contrib);
				progress.update();
			}
			return;
		}
	}
	else if (f_features != "")
	{
		features = &allocated_mat;
		MedMat<float> x;
		int titles_line_flag = 1;
		x.read_from_csv_file(f_features, titles_line_flag);
		features = &static_mem;
		features->set_as_matrix(x);
		if (max_samples > 0 && max_samples < features->samples.size())
			medial::process::down_sample(*features, float(max_samples) / features->samples.size());
		non_norm_features = &static_mem;
		if (zero_missing_contrib)
			MWARN("WARN: not supported zero_missing_contrib when starting from matrix csv\n");
		zero_missing_contrib = false;
	}

	// feature importance print
	flow_print_shap(model, features, non_norm_features, group_ratio, group_cnt, names, normalize, normalize_after, remove_b0,
		group_features, bin_uniqu_vals, binning_method, output_file, retrain_predictor, rep, zero_missing_contrib);
}

void flow_rewrite_object(const string &f_model, const string &object_type, const string &output_fname) {
	string obj_name = boost::to_lower_copy(object_type);
	boost::trim(obj_name);
	if (obj_name == "medmodel") {
		MedModel model;
		model.read_from_file_unsafe(f_model);
		model.version_info = medial::get_git_version();
		model.write_to_file(output_fname);
	}
	else if (obj_name == "medfeatures") {
		MedFeatures feats;
		feats.read_from_file_unsafe(f_model);
		feats.write_to_file(output_fname);
	}
	else
		MTHROW_AND_ERR("Error unsupported object_type = %s\n", object_type.c_str());
}

void flow_export_predictor(const string &f_model, const string &output_fname)
{
	MedModel model;
	if (model.read_from_file(f_model) < 0)
		MTHROW_AND_ERR("FAILED reading model file %s\n", f_model.c_str());

	if (model.predictor != NULL)
		model.predictor->export_predictor(output_fname);
	else
		MTHROW_AND_ERR("Model doesn't have predictor \n");
}

void activate_cleaners_logging(vector<RepProcessor *> &rep_processors, bool acticvate = true) {
	vector<RepProcessor *> flatten;
	for (size_t i = 0; i < rep_processors.size(); ++i)
	{
		if (rep_processors[i]->processor_type == REP_PROCESS_MULTI)
			flatten.insert(flatten.end(), ((RepMultiProcessor *)rep_processors[i])->processors.begin()
				, ((RepMultiProcessor *)rep_processors[i])->processors.end());
		else
			flatten.push_back(rep_processors[i]);
	}
	string nRem = "nRem";
	string nTrim = "nTrim";
	if (!acticvate) {
		nRem = "";
		nTrim = "";
	}
	for (RepProcessor *p : flatten)
	{
		if (p->processor_type == REP_PROCESS_BASIC_OUTLIER_CLEANER || p->processor_type == REP_PROCESS_CONFIGURED_OUTLIER_CLEANER) {
			((RepBasicOutlierCleaner *)p)->nRem_attr_suffix = nRem;
			((RepBasicOutlierCleaner *)p)->nTrim_attr_suffix = nTrim;
		}
		if (p->processor_type == REP_PROCESS_NBRS_OUTLIER_CLEANER) {
			((RepNbrsOutlierCleaner *)p)->nRem_attr_suffix = nRem;
			((RepNbrsOutlierCleaner *)p)->nTrim_attr_suffix = nTrim;
		}
		if (p->processor_type == REP_PROCESS_RULEBASED_OUTLIER_CLEANER) {
			((RepRuleBasedOutlierCleaner *)p)->nRem_attr_suffix = "";
			if (acticvate)
				((RepRuleBasedOutlierCleaner *)p)->nRem_attr = "nRem_rule_" + to_string(((RepRuleBasedOutlierCleaner *)p)->rulesToApply.front());
			else
				((RepRuleBasedOutlierCleaner *)p)->nRem_attr = "";
		}

	}
}

void flow_export_production_model(const string &f_model, const string &output_fname,
	const string &predcitor_type, const string &model_predictor_path,
	int activate_cleaners, const string &rep_path, bool minimize_model) {
	MedModel model;
	MLOG("Reading model file %s\n", f_model.c_str());
	if (model.read_from_file(f_model) < 0)
		MTHROW_AND_ERR("FAILED reading model file %s\n", f_model.c_str());

	if (!predcitor_type.empty() && !model_predictor_path.empty()) {
		delete model.predictor;
		MLOG("Reloading predictor type %s from %s\n", predcitor_type.c_str(), model_predictor_path.c_str());
		model.predictor = MedPredictor::make_predictor(predcitor_type);
		model.predictor->read_from_file(model_predictor_path);
	}

	//prepare for production:
	if (activate_cleaners != 0)
		activate_cleaners_logging(model.rep_processors, activate_cleaners > 0);

	//minimize if needed:
	if (minimize_model) {
		if (rep_path.empty())
			MLOG("Warn - in order to fully minimize model, you must provide repository\n");
		else {
			MedPidRepository rep;
			if (rep.init(rep_path) < 0)
				MTHROW_AND_ERR("Error can't read rep %s\n", rep_path.c_str());
			model.fit_for_repository(rep);
			model.collect_and_add_virtual_signals(rep);
			model.filter_rep_processors();
		}
		//Filter generators:
		vector<string> req_sigs;
		model.get_required_signal_names(req_sigs);
		vector<bool> need_feature_gen(model.generators.size(), false);
		for (size_t i = 0; i < req_sigs.size(); ++i)
		{
			const string &sig = req_sigs[i];

			//feat_processors + generator
			int feat_i = 0;
			for (FeatureGenerator *feat_gen : model.generators) {
				unordered_set<string> gen_req_sigs_virt, gen_req_sigs;
				feat_gen->get_required_signal_names(gen_req_sigs_virt);
				for (const string &s_name : gen_req_sigs_virt)
				{
					vector<string> physical_names;
					get_real_sigs(model, s_name, physical_names);
					gen_req_sigs.insert(physical_names.begin(), physical_names.end());
				}

				if (!need_feature_gen[feat_i]) //calculate if not already marked as needed:
					need_feature_gen[feat_i] = (gen_req_sigs.find(sig) != gen_req_sigs.end() && !feat_gen->names.empty());
				++feat_i;
			}

		}

		//clear uneeded feature generators:
		vector<FeatureGenerator *> fitlered_gen;
		fitlered_gen.reserve(model.generators.size());
		for (size_t i = 0; i < model.generators.size(); ++i)
		{
			if (need_feature_gen[i]) {
				fitlered_gen.push_back(model.generators[i]);
			}
			else {
				MLOG("Remove generator %s\n", model.generators[i]->my_class_name().c_str());
				delete model.generators[i];
				model.generators[i] = NULL;
			}
		}
		model.generators = move(fitlered_gen);
	}

	//write model
	model.write_to_file(output_fname);
}

void flow_check_deps(const string &f_model, const string &f_json, const string &sig) {
	MedModel mdl;
	if (!f_model.empty())
		mdl.read_from_file(f_model);
	else {
		if (f_json.empty())
			MTHROW_AND_ERR("Error - must provide f_model or f_json\n");
		mdl.init_from_json_file(f_json);
	}

	vector<FeatureGenerator *> applied_generators;
	for (auto& generator : mdl.generators) {
		unordered_set<string> req_names;
		generator->get_required_signal_names(req_names);
		if (req_names.find(sig) != req_names.end())
			applied_generators.push_back(generator);
	}

	vector<RepProcessor *> filtered_processors;
	for (unsigned int i = 0; i < mdl.rep_processors.size(); i++) {
		unordered_set<string> current_req_signal_names;
		if (applied_generators.empty())
			current_req_signal_names.insert(sig);
		get_all_required_signal_names(current_req_signal_names, mdl.rep_processors, i, applied_generators);
		if (!mdl.rep_processors[i]->filter(current_req_signal_names))
			filtered_processors.push_back(mdl.rep_processors[i]);
	}
	// Identify required signals
	MLOG("Left with %zu generators out of %zu\n", applied_generators.size(), mdl.generators.size());
	int pos = 1;
	for (auto& generator : applied_generators) {
		generator->dprint("FeatureGenerator_" + to_string(pos), 2);
		++pos;
	}

	MLOG("Left with %zu rep_processors out of %zu\n", filtered_processors.size(), mdl.rep_processors.size());
	pos = 1;
	for (auto& rep_processor : filtered_processors) {
		rep_processor->dprint("RepProcessor_" + to_string(pos), 2);
		++pos;
	}

}

void apply_on_matrix(MedModel &model, MedSamples &samples) {
	//Predict
	if (!model.predictor->model_features.empty()) {
		//filter features from matrix:
		unordered_set<string> feature_list(model.predictor->model_features.begin(), model.predictor->model_features.end());
		model.features.filter(feature_list);
	}
	if (model.predictor->predict(model.features) < 0)
		MTHROW_AND_ERR("Predictor failed\n");
	//do also PP for calibration
	for (size_t i = 0; i < model.post_processors.size(); ++i)
		model.post_processors[i]->Apply(model.features);

	if (samples.insert_preds(model.features) != 0)
		MTHROW_AND_ERR("Insertion of predictions to samples failed\n");

	if (samples.copy_attributes(model.features.samples) != 0)
		MTHROW_AND_ERR("Insertion of post_process to samples failed\n");
}

void get_propensity_weights(const string &rep_fname, const string &f_model, const string &f_samples, const string &f_matrix,
	const string &f_preds, double max_propensity_weight, bool trim_propensity_weight, const string &prop_attr_weight_name,
	int override_outcome, bool do_conversion, const string &f_json, const string &feat_name, bool do_sampling) {
	MLOG("Calculating propensity weights...\n");
	double propensity_cutoff = 0;
	if (max_propensity_weight > 0) {
		//has some cutof limit - calculate it:
		propensity_cutoff = (1 / max_propensity_weight);
		MLOG("Using propensity probability cutoff (based on max_propensity_weight) of: [%f, %f].\n",
			propensity_cutoff, 1 - propensity_cutoff);
	}
	MedModel model;
	model.read_from_file(f_model);
	MedSamples samples;
	if (f_matrix.empty())
		samples.read_from_file(f_samples);
	else {
		MedFeatures samples_features;
		samples_features.read_from_csv_mat(f_matrix);
		samples.import_from_sample_vec(samples_features.samples);
		model.features = move(samples_features);
	}
	vector<float> original_preds;
	if (!samples.idSamples.empty() && !samples.idSamples[0].samples[0].prediction.empty()) {
		MLOG("input has preds inside\n");
		samples.get_preds_channel(original_preds, 0);
	}

	vector<float> outcome_override;
	bool override_outome_from_json = !f_json.empty() && !feat_name.empty();
	if (override_outome_from_json) {
		MedModel feat_model;
		feat_model.init_from_json_file(f_json);

		vector<int> pids;
		samples.get_ids(pids);

		MedPidRepository rep;
		feat_model.load_repository(rep_fname, pids, rep, true);

		if (feat_model.learn(rep, &samples, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_PREDICTOR) < 0)
			MTHROW_AND_ERR("Error - Failed learning model\n");

		vector<string> all_feat_names;
		feat_model.features.get_feature_names(all_feat_names);
		string full_feat_name = all_feat_names[find_in_feature_names(all_feat_names, feat_name)];
		outcome_override = move(feat_model.features.data.at(full_feat_name));
	}

	//Check if model has Outcome feature and than add it:
	bool has_outcome = false;
	for (const string & s_name : model.predictor->model_features)
		if (s_name == "Outcome") {
			has_outcome = true;
			break;
		}
	if (!has_outcome) {
		if (f_matrix.empty())
			medial::medmodel::apply(model, samples, rep_fname, MedModelStage::MED_MDL_END); //do also PP for calibration
		else
			apply_on_matrix(model, samples); //matrix was loaded into model, just apply from there
	}
	else {
		//Add Outcomme feature
		MLOG("Has Outcome feature - adding...\n");
		if (f_matrix.empty()) //need to apply when not loaded by matrix directly
			medial::medmodel::apply(model, samples, rep_fname, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);

		vector<float> &outcome_f = model.features.data["Outcome"];
		model.features.attributes["Outcome"].imputed = false;
		outcome_f.resize(model.features.samples.size());
		for (size_t i = 0; i < outcome_f.size(); ++i)
			outcome_f[i] = model.features.samples[i].outcome;

		apply_on_matrix(model, samples);
	}
	vector<MedSample> flat_samples;
	samples.export_to_sample_vec(flat_samples);
	//clear preds from samples and return old preds:
	int idx = 0;
	for (MedIdSamples &sample_pid : samples.idSamples)
		for (MedSample &s : sample_pid.samples) {
			s.prediction.clear();
			if (!original_preds.empty()) {
				s.prediction.push_back(original_preds[idx]);
				++idx;
			}
		}
	//use model.features.samples.predictions to weight the samples
	vector<float> weights(flat_samples.size());
	int case_cutoff = 0, controls_cutoff = 0;

	for (size_t i = 0; i < flat_samples.size(); ++i)
	{
		float prob = flat_samples[i].prediction[0];
		bool is_case = flat_samples[i].outcome > 0;
		if (override_outome_from_json)
			is_case = outcome_override[i] > 0;
		else {
			if (override_outcome == 0)
				is_case = false;
			if (override_outcome > 0)
				is_case = true;
		}

		if (is_case) {
			if (prob > 0 && prob >= propensity_cutoff)
				weights[i] = 1 / prob;
			else {
				if (trim_propensity_weight)
					weights[i] = max_propensity_weight;
				else
					weights[i] = 0; //drop
				++case_cutoff;
			}
		}
		else {
			if (prob < 1 && prob <= 1 - propensity_cutoff)
				weights[i] = 1 / (1 - prob);
			else {
				if (trim_propensity_weight)
					weights[i] = max_propensity_weight;
				else
					weights[i] = 0; //drop
				++controls_cutoff;
			}
		}

		if (do_conversion) {
			if (is_case)
				weights[i] *= (1 - prob);
			else
				weights[i] *= prob;
		}
	}

	if (!do_sampling) {
		//store weights:
		idx = 0;
		for (MedIdSamples &sample_pid : samples.idSamples)
			for (MedSample &s : sample_pid.samples) {
				s.attributes[prop_attr_weight_name] = weights[idx];
				++idx;
			}
	}
	else {
		random_device rd;
		mt19937 gen(rd());
		uniform_real_distribution<> rnd_real(0, 1);
		if (weights.empty()) {
			MWARN("WARN :: no weights, no samples?\n");
			return;
		}
		//do sampling:
		float max_w = weights.front();
		for (size_t i = 1; i < weights.size(); ++i)
			if (max_w < weights[i])
				max_w = weights[i];
		vector<MedSample> filt_samples;
		idx = 0;
		for (MedIdSamples &sample_pid : samples.idSamples)
			for (MedSample &s : sample_pid.samples) {
				double pr = weights[idx] / max_w;
				bool keep_sample = rnd_real(gen) <= pr;
				++idx;
				if (keep_sample)
					filt_samples.push_back(s);
			}
		samples.import_from_sample_vec(filt_samples);
	}
	//write samples:
	samples.write_to_file(f_preds);

	MLOG("Has %d samples in high cutoff and %d samples in low cutoff\n",
		controls_cutoff, case_cutoff);
}

void apply_predictor_on_mat(const string &f_matrix, const string &f_model,
	const string &f_preds, const string &rep_path, bool apply_feat_processors) {
	if (f_matrix.empty())
		MTHROW_AND_ERR("Error please provide f_matrix in this mode\n");
	if (f_model.empty())
		MTHROW_AND_ERR("Error please provide f_model in this mode\n");
	if (f_preds.empty())
		MTHROW_AND_ERR("Error please provide f_preds in this mode\n");

	MedModel model;
	if (model.read_from_file(f_model) < 0)
		MTHROW_AND_ERR("Error unable to read model %s\n", f_model.c_str());
	MedFeatures x;
	if (x.read_from_csv_mat(f_matrix) < 0)
		MTHROW_AND_ERR("Error unable to read matrix %s\n", f_matrix.c_str());

	if (apply_feat_processors) {
		MedPidRepository dummy;
		dummy.init(rep_path);
		MedSamples dummy_s;
		model.features = move(x);
		model.apply(dummy, dummy_s, MED_MDL_APPLY_FTR_PROCESSORS, MED_MDL_APPLY_PREDICTOR);
		x = move(model.features);
	}
	else {
		if (model.predictor->predict(x) < 0)
			MTHROW_AND_ERR("Error unable to predict\n");
	}
	MedSamples res;
	res.import_from_sample_vec(x.samples);

	if (res.write_to_file(f_preds) < 0)
		MTHROW_AND_ERR("Error unable to write preds %s\n", f_preds.c_str());
}

void try_change_name(const vector<vector<string>> &all_names_before, const vector<vector<string>> &all_names_after
	, const string &signal, const string &signal_new_name, string &f_name) {
	//need to find the mathcing map:
	//first find bucket:
	int bucket_idx = -1;
	for (int i = 0; i < all_names_before.size() && bucket_idx < 0; ++i)
	{
		unordered_set<string> snames(all_names_before[i].begin(), all_names_before[i].end());
		if (snames.find(f_name) != snames.end())
			bucket_idx = i;
	}
	if (bucket_idx < 0)
		MTHROW_AND_ERR("Error can't find feature bucket in model\n");
	//try search and replace of ".%s." and see if that worked?
	string cp_f = f_name;
	boost::regex reg_start("^" + signal + "\\.");
	f_name = move(boost::regex_replace(f_name, reg_start, signal_new_name + "."));
	boost::replace_first(f_name, "." + signal + ".", "." + signal_new_name + ".");
	unordered_set<string> snames(all_names_after[bucket_idx].begin(), all_names_after[bucket_idx].end());
	if (snames.find(f_name) == snames.end())
		MTHROW_AND_ERR("Error - couldn't map feature %s, tried %s\n", cp_f.c_str(), f_name.c_str());
}


void update_selector(FeatureProcessor *feat_proc, const unordered_set<string> &aff_names,
	const vector<vector<string>> &all_names_before, const vector<vector<string>> &all_names_after
	, const string &signal, const string &signal_new_name) {
	FeatureSelector *f_selector = static_cast<FeatureSelector *>(feat_proc);
	unordered_set<string> new_s;
	for (const string &required_feature : f_selector->required)
	{
		if (aff_names.find(required_feature) == aff_names.end()) {
			new_s.insert(required_feature);
			continue;
		}
		//need to change:
		string editable_f = required_feature;
		try_change_name(all_names_before, all_names_after, signal, signal_new_name, editable_f);
		new_s.insert(editable_f);
	}
	f_selector->required = move(new_s);
	//Let's change selector result: selected
	for (string &selected_feature : f_selector->selected)
	{
		if (aff_names.find(selected_feature) == aff_names.end())
			continue;
		//need to change:
		try_change_name(all_names_before, all_names_after, signal, signal_new_name, selected_feature);
	}
}

void rename_model_signal(const string &f_model, const string &f_output,
	const string &signal, const string &signal_new_name) {
	if (f_model.empty() || f_output.empty() || signal_new_name.empty())
		MTHROW_AND_ERR("Error - must provide f_model, f_output,signal_rename in this mode\n");

	MedModel model;
	if (model.read_from_file(f_model) < 0)
		MTHROW_AND_ERR("Error can't read model %s\n", f_model.c_str());
	//calc feature needed to update:
	vector<int> depend_feats_idx;
	int feat_i = 0;
	for (FeatureGenerator *feat_gen : model.generators) {
		unordered_set<string> gen_req_sigs_virt, gen_req_sigs;
		feat_gen->get_required_signal_names(gen_req_sigs_virt);
		for (const string &s_name : gen_req_sigs_virt)
		{
			vector<string> physical_names;
			get_real_sigs(model, s_name, physical_names);
			gen_req_sigs.insert(physical_names.begin(), physical_names.end());
		}

		if (gen_req_sigs.find(signal) != gen_req_sigs.end())
			depend_feats_idx.push_back(feat_i);
		++feat_i;
	}
	//change signal name in features depend_feats and all depend_feats_idx:
	vector<vector<string>> all_names_before, all_names_after;
	unordered_set<string> aff_names;
	for (int gen_idx : depend_feats_idx)
	{
		FeatureGenerator *feat_gen = model.generators[gen_idx];
		//change req_signals and call set_names
		MLOG("CHANGING:\n###############################\n");
		string s = feat_gen->object_json();
		MLOG("Before:\n%s\n", s.c_str());
		vector<string> names_before = feat_gen->names;
		all_names_before.push_back(names_before);
		aff_names.insert(names_before.begin(), names_before.end());
		if (feat_gen->generator_type == FTR_GEN_CATEGORY_DEPEND) {
			feat_gen->names.clear();
			feat_gen->req_signals = { "BDATE", "GENDER" };
		}
		feat_gen->init_from_string("signal=" + signal_new_name);
		if (feat_gen->generator_type == FTR_GEN_CATEGORY_DEPEND)
			feat_gen->set_names();

		s = feat_gen->object_json();
		MLOG("After:\n%s\n", s.c_str());
		vector<string> names_after = feat_gen->names;
		all_names_after.push_back(names_after);
	}

	//TODO: Change FP that depend on those previous feature names AND output names in here (if output name is input name)
	for (FeatureProcessor *feat_proc : model.feature_processors) {
		if (feat_proc->is_selector())
			update_selector(feat_proc, aff_names, all_names_before, all_names_after, signal, signal_new_name);
		if (feat_proc->processor_type == FeatureProcessorTypes::FTR_PROCESS_MULTI) {
			MultiFeatureProcessor *multi_f = static_cast<MultiFeatureProcessor *>(feat_proc);
			for (FeatureProcessor *int_f_proc : multi_f->processors)
				if (int_f_proc->is_selector())
					update_selector(int_f_proc, aff_names, all_names_before, all_names_after, signal, signal_new_name);
		}
	}

	//Change model that depend on those previous feature names:
	vector<string> &mdl_f = model.predictor->model_features;
	for (string &f_name : mdl_f)
	{
		if (aff_names.find(f_name) == aff_names.end())
			continue;
		try_change_name(all_names_before, all_names_after, signal, signal_new_name, f_name);
	}

	if (model.write_to_file(f_output) < 0)
		MTHROW_AND_ERR("Error can't write model %s\n", f_model.c_str());
}

bool is_rename_processor(RepProcessor *rp, const string &signal,
	const string &rep_signal) {
	if (rp->virtual_signals_generic.size() <= 1) {
		if (rp->aff_signals.find(rep_signal) == rp->aff_signals.end())
			return false;
		//this creates the "needed" virtual signal
		//let's make sure input signal is rep_signal
		if (rp->req_signals.find(rep_signal) != rp->req_signals.end())
			return false; //uses itself
		if (rp->req_signals.find(signal) == rp->req_signals.end()) {
			MWARN("WARN: found fp that uses %s, to create something else from %s\n",
				signal.c_str(), rep_signal.c_str());
			MWARN("%s\n", rp->object_json().c_str());
			return false;
		}

		return true;
	}
	return false;
}

bool adjust_sig_rename(MedModel &model, const string &signal, const string &rep_signal,
	const string &sig_type) {
	char buffer[5000];
	snprintf(buffer, sizeof(buffer), "signal_type=%s;signal=%s;output_name=%s",
		sig_type.c_str(), rep_signal.c_str(), signal.c_str());
	//check if model contain opposite rename and remove it
	bool found_fp = false;
	int new_size = (int)model.rep_processors.size();
	for (size_t i = 0; i < model.rep_processors.size(); ++i)
	{
		RepProcessor *rp = model.rep_processors[i];
		if (rp == NULL)
			continue;
		if (rp->processor_type == REP_PROCESS_MULTI) {
			RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(rp);
			int new_fp_size = (int)multi->processors.size();
			for (size_t j = 0; j < multi->processors.size(); ++j)
			{
				if (multi->processors[j] == NULL)
					continue;
				//check in multi->processors[j]
				if (is_rename_processor(multi->processors[j], signal, rep_signal)) {
					//remove
					found_fp = true;
					delete multi->processors[j];
					for (size_t k = j + 1; k < multi->processors.size(); ++k)
						multi->processors[k - 1] = multi->processors[k];
					multi->processors[new_fp_size - 1] = NULL;
					--new_fp_size;
				}
			}
			if (multi->processors.size() > new_fp_size)
				multi->processors.resize(new_fp_size);
		}
		else {
			//check rp
			if (is_rename_processor(rp, signal, rep_signal)) {
				//remove
				delete model.rep_processors[i];
				//model.rep_processors[i] = NULL;
				//move all the rest to i:
				for (size_t j = i + 1; j < model.rep_processors.size(); ++j)
					model.rep_processors[j - 1] = model.rep_processors[j];
				model.rep_processors[new_size - 1] = NULL;
				--new_size;
				found_fp = true;
			}
		}
	}
	if (found_fp) {
		model.rep_processors.resize(new_size);
		return false;
	}


	RepProcessor *rep = RepProcessor::make_processor("filter_channels", buffer);
	model.rep_processors.insert(model.rep_processors.begin(), rep);
	return true;

}
void adjust_empty_sig(MedModel &model, const string &signal) {
	char buffer[5000];
	snprintf(buffer, sizeof(buffer),
		"calculator=empty;output_signal_type=T(i),V(f);max_time_search_range=0;signals_time_unit=Days;signals=BDATE;names=%s",
		signal.c_str());
	//check if model contain opposite rename and remove it

	RepProcessor *rep = RepProcessor::make_processor("calc_signals", buffer);
	model.rep_processors.insert(model.rep_processors.begin(), rep);
}

float fetch_sig_median(MedPidRepository &rep, int sid) {
	UniversalSigVec usv;
	vector<int> pids;
	MedPidRepository rep2;
	vector<int> sig_ids = { sid };
	if (rep2.read_all(rep.config_fname, pids, sig_ids) < 0)
		MTHROW_AND_ERR("Error can't read rep %s", rep.config_fname.c_str());
	map<float, int> cnts;
	long long tot_cnt = 0;
	for (int i = 0; i < rep2.pids.size(); ++i)
	{
		rep2.uget(rep2.pids[0], sid, usv);
		for (int j = 0; j < usv.len; ++j)
		{
			++tot_cnt;
			++cnts[usv.Val(j)];
		}
	}
	//find median:
	double curr_p = 0;
	float res = MED_MAT_MISSING_VALUE;
	for (auto &it : cnts)
	{
		curr_p += it.second / (double)tot_cnt;
		if (curr_p >= 0.5) {
			res = it.first;
			break;
		}
	}
	return res;
}

enum Convert_Res {
	SUCC = 0,
	MIGHT_FIND_BETTER = 1,
	FAILED = 2
};

Convert_Res try_adjust_model(MedModel &model, MedPidRepository &rep, const string &signal,
	ofstream &log_file, bool use_log_file) {
	//Maybe read from configuration later. current version is hardcoded:
	char buffer[5000];
	unordered_map<string, vector<string>> name_conversions; //can have multiple options to same target
	name_conversions["SEX"].push_back("GENDER");
	name_conversions["DIAGNOSIS"].push_back("RC");
	name_conversions["DIAGNOSIS"].push_back("ICD9_Diagnosis");

	name_conversions["GENDER"].push_back("SEX");
	name_conversions["RC"].push_back("DIAGNOSIS");
	name_conversions["ICD9_Diagnosis"].push_back("DIAGNOSIS");
	name_conversions["ICD9_Diagnosis"].push_back("RC");
	//Check for conversion BUN <=> Urea:
	if (signal == "BUN" || signal == "Urea") {
		//our range is around "5-20" Urea mg/dl
		//(assumes never "mg/l" or "g/dl")

		//BUN = 2.14*Urea(both mg/dL)
		//BUN(mmol/l = > mg/dL multiply by 6)
		//Urea(mmol/l = > mg/dL multiply by 6.01)
		//factors (or 1/factor): 1, 2.14, 2.8, 6, 12.84 
		//check how to fit repo medial value to 16 -25 

		string rep_signal = "Urea";
		int sid = rep.sigs.sid("Urea");
		if (sid < 0) {
			sid = rep.sigs.sid("BUN");
			rep_signal = "BUN";
		}

		if (sid < 0) {
			//can only fix be empty signal:
			adjust_empty_sig(model, signal);
			snprintf(buffer, sizeof(buffer), "EMPTY_SIGNAL\t%s\n", signal.c_str());
			if (use_log_file)
				log_file << buffer;
			else
				MWARN("%s", buffer);
			return MIGHT_FIND_BETTER;
		}
		else {
			float med_val = fetch_sig_median(rep, sid);
			float calc_factor = 1;
			//find calc_factor-   1, 2.14, 2.8, 6, 12.84 (or 1/)
			if (med_val >= 13 && med_val <= 27)
				calc_factor = 1;
			else if (med_val > 27 && med_val <= 40)
				calc_factor = float(1.0 / 2.14);
			else if (med_val > 40 && med_val <= 70)
				calc_factor = float(1.0 / 2.8);
			else if (med_val > 70 && med_val <= 150)
				calc_factor = float(1.0 / 6.0);
			else if (med_val > 150 && med_val <= 330)
				calc_factor = float(1.0 / 12.84);
			else if (med_val > 330)
				calc_factor = -1; //mark as not found!
			//now test 1/factor:
			else if (med_val >= 7.5 && med_val < 13)
				calc_factor = float(2.14);
			else if (med_val >= 4.6 && med_val < 7.5)
				calc_factor = float(2.8);
			else if (med_val >= 2 && med_val < 4.6)
				calc_factor = float(6);
			else if (med_val >= 1 && med_val < 2)
				calc_factor = float(12.84);
			else
				calc_factor = -1;

			MLOG("Signal %s, medial value is %f in repository\n", rep_signal.c_str(), med_val);
			if (calc_factor == -1) {
				MWARN("Couldn't determine factor: repository medial value for signal %s is %f, range should be 13-25\n",
					rep_signal.c_str(), med_val);

				adjust_empty_sig(model, signal);
				snprintf(buffer, sizeof(buffer), "EMPTY_SIGNAL\t%s\n", signal.c_str());
				if (use_log_file)
					log_file << buffer;
				else
					MWARN("%s", buffer);
				return MIGHT_FIND_BETTER;
			}

			//add conversion from "rep_signal" => "model_sig"
			snprintf(buffer, sizeof(buffer),
				"calculator=sum;output_signal_type=T(i),V(f);max_time_search_range=0;signals_time_unit=Days;signals=%s;names=%s;calculator_init_params={factors=%f}",
				rep_signal.c_str(), signal.c_str(), calc_factor);
			RepProcessor *convertion_rp = RepProcessor::make_processor("calc_signals", buffer);
			//add at the beggining (model will handle memory)
			model.rep_processors.insert(model.rep_processors.begin(), convertion_rp);

			//model_signal, rep_signal, factor
			snprintf(buffer, sizeof(buffer), "CONVERT_SIGNAL_TO_FROM_FACTOR\t%s\t%s\t%f\n",
				signal.c_str(), rep_signal.c_str(), calc_factor);
			if (use_log_file)
				log_file << buffer;
			else
				MWARN("%s", buffer);
			return SUCC;
		}

	}
	else if (name_conversions.find(signal) != name_conversions.end()) {
		//Suggest conversions: renames: GENDER:SEX, DIAGNOSIS:ICD9_Diagnosis, DIAGNOSIS:RC

		//model target signal is one of the "keys" in name_conversions. SEX, Diagnosis
		vector<string> &opts = name_conversions.at(signal);
		string found_opt = "";
		for (const string &opt : opts)
			if (rep.sigs.sid(opt) >= 0)
			{
				found_opt = opt;
				break;
			}

		if (found_opt.empty()) {
			//failed to find - not adding empty i want this to fail completely - mark as not run
			snprintf(buffer, sizeof(buffer), "MISSING_IMPORTANT_SIGNAL\t%s\n", signal.c_str());
			if (use_log_file)
				log_file << buffer;
			else
				MWARN("%s", buffer);
			return FAILED;
		}
		//found map! need to convert from found_opt => signal
		//if model contain op conversion - remove it instead of adding 

		int sid = rep.sigs.sid(found_opt);
		const SignalInfo &si = rep.sigs.Sid2Info[sid];
		UniversalSigVec usv;
		usv.init(si);
		string sig_type = usv.get_signal_generic_spec();
		bool added_rename = adjust_sig_rename(model, signal, found_opt, sig_type);
		if (added_rename)
			snprintf(buffer, sizeof(buffer), "RENAME_TO_FROM\t%s\t%s\n", signal.c_str(), found_opt.c_str());
		else
			snprintf(buffer, sizeof(buffer), "REMOVED_RENAME_FROM_TO\t%s\t%s\n", signal.c_str(), found_opt.c_str());
		if (use_log_file)
			log_file << buffer;
		else
			MWARN("%s", buffer);
		return SUCC;
	}
	else if (signal == "Race" || signal == "RACE") {
		//Add all are "White"

		snprintf(buffer, sizeof(buffer),
			"calculator=constant;output_signal_type=V(i);max_time_search_range=0;signals_time_unit=Days;signals=BDATE;names=%s;calculator_init_params={value=White;additional_dict_vals=Black,Asian,Hispanic,Other}",
			signal.c_str());
		RepProcessor *convertion_rp = RepProcessor::make_processor("calc_signals", buffer);
		//add at the beggining (model will handle memory)
		model.rep_processors.insert(model.rep_processors.begin(), convertion_rp);

		//model_signal, rep_signal, factor
		snprintf(buffer, sizeof(buffer), "ADD_CONSTANT_VALUE\t%s\tWhite\n",
			signal.c_str());
		if (use_log_file)
			log_file << buffer;
		else
			MWARN("%s", buffer);
		return SUCC;

	}
	else {
		//add empty signal:
		adjust_empty_sig(model, signal);
		snprintf(buffer, sizeof(buffer), "EMPTY_SIGNAL\t%s\n", signal.c_str());
		if (use_log_file)
			log_file << buffer;
		else
			MWARN("%s", buffer);
		return MIGHT_FIND_BETTER;
	}

	return SUCC;
}

void fit_model_to_repository(const string &rep_path, const string &model_path,
	const string &adjusted_model_output_path, const string &log_adjusted_actions,
	const string &log_missing_categories, int cleaner_verbose, bool is_virtual_rep,
	bool remove_explainability) {
	if (rep_path.empty())
		MTHROW_AND_ERR("Error rep must be given in fit_model_to rep\n");
	if (model_path.empty())
		MTHROW_AND_ERR("Error f_model must be given in fit_model_to rep\n");
	if (adjusted_model_output_path.empty())
		MTHROW_AND_ERR("Error f_output must be given in fit_model_to rep\n");

	//store log of actions to adjust model (and/or) unresolved ones
	char msg_buffer[5000];
	ofstream log_actions;
	if (!log_adjusted_actions.empty()) {
		log_actions.open(log_adjusted_actions);
		if (!log_actions.good())
			MTHROW_AND_ERR("Error can't write to file %s\n", log_adjusted_actions.c_str());
	}
	//store log of missing categories
	ofstream log_categ;
	if (!log_missing_categories.empty()) {
		log_categ.open(log_missing_categories);
		if (!log_categ.good())
			MTHROW_AND_ERR("Error can't write to file %s\n", log_missing_categories.c_str());
	}

	MedModel model;
	model.read_from_file(model_path);
	if (remove_explainability) {
		int new_sz = (int)model.post_processors.size();
		for (size_t i = 0; i < model.post_processors.size(); ++i)
		{
			if (model.post_processors[i]->processor_type == PostProcessorTypes::FTR_POSTPROCESS_MULTI) {
				MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(model.post_processors[i]);
				int new_pp_size = int(multi->post_processors.size());
				for (size_t j = 0; j < multi->post_processors.size(); ++j)
				{
					if (dynamic_cast<ModelExplainer *>(multi->post_processors[j]) != NULL) {
						delete multi->post_processors[j];
						for (size_t k = j + 1; k < multi->post_processors.size(); ++k)
							multi->post_processors[k - 1] = multi->post_processors[k];
						multi->post_processors[new_pp_size - 1] = NULL;
						--new_pp_size;
					}
				}
				if (new_pp_size != multi->post_processors.size()) {
					multi->post_processors.resize(new_pp_size);
					snprintf(msg_buffer, sizeof(msg_buffer), "REMOVED\tModelExplainer\n");
					if (log_adjusted_actions.empty())
						MLOG("%s", msg_buffer);
					else
						log_actions << msg_buffer;
				}

			}
			else
			{
				if (dynamic_cast<ModelExplainer *>(model.post_processors[i]) != NULL) {
					delete model.post_processors[i];
					for (size_t k = i + 1; k < model.post_processors.size(); ++k)
						model.post_processors[k - 1] = model.post_processors[k];
					model.post_processors[new_sz - 1] = NULL;
					--new_sz;
				}
			}
		}
		if (model.post_processors.size() != new_sz) {
			model.post_processors.resize(new_sz);
			snprintf(msg_buffer, sizeof(msg_buffer), "REMOVED\tModelExplainer\n");
			if (log_adjusted_actions.empty())
				MLOG("%s", msg_buffer);
			else
				log_actions << msg_buffer;
		}
	}
	//Remove RepCheckReq if exists in model:
	int new_rep_size = (int)model.rep_processors.size();
	for (size_t i = 0; i < model.rep_processors.size(); ++i)
	{
		if (model.rep_processors[i]->processor_type == RepProcessorTypes::REP_PROCESS_MULTI) {
			RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(model.rep_processors[i]);

			int new_rp_size = int(multi->processors.size());
			for (size_t j = 0; j < multi->processors.size(); ++j)
			{
				if (multi->processors[j]->processor_type == RepProcessorTypes::REP_PROCESS_CHECK_REQ) {
					delete multi->processors[j];
					for (size_t k = j + 1; k < multi->processors.size(); ++k)
						multi->processors[k - 1] = multi->processors[k];
					multi->processors[new_rp_size - 1] = NULL;
					--new_rp_size;
				}
			}
			bool removed_rep_check = new_rp_size != multi->processors.size();
			if (removed_rep_check)
				multi->processors.resize(new_rp_size);

			if (new_rp_size == 0) {
				delete model.rep_processors[i];
				for (size_t k = i + 1; k < model.rep_processors.size(); ++k)
					model.rep_processors[k - 1] = model.rep_processors[k];
				model.rep_processors[new_rep_size - 1] = NULL;
				--new_rep_size;
			}
			else if (removed_rep_check) {
				snprintf(msg_buffer, sizeof(msg_buffer), "REMOVED\tRepCheckReq\n");
				if (log_adjusted_actions.empty())
					MLOG("%s", msg_buffer);
				else
					log_actions << msg_buffer;
			}
		}
		else {
			if (model.rep_processors[i]->processor_type == RepProcessorTypes::REP_PROCESS_CHECK_REQ) {
				//remove:
				delete model.rep_processors[i];
				for (size_t k = i + 1; k < model.rep_processors.size(); ++k)
					model.rep_processors[k - 1] = model.rep_processors[k];
				model.rep_processors[new_rep_size - 1] = NULL;
				--new_rep_size;
			}
		}
		if (model.rep_processors.size() != new_rep_size) {
			model.rep_processors.resize(new_rep_size);
			snprintf(msg_buffer, sizeof(msg_buffer), "REMOVED\tRepCheckReq\n");
			if (log_adjusted_actions.empty())
				MLOG("%s", msg_buffer);
			else
				log_actions << msg_buffer;
		}
	}
	MedPidRepository rep;
	if (is_virtual_rep)
		rep.switch_to_in_mem_mode();
	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", rep_path.c_str());

	//1. list all signals needed by model
	vector<string> req_signals;
	model.fit_for_repository(rep);
	model.collect_and_add_virtual_signals(rep);
	model.get_required_signal_names(req_signals);
	//2. collect signals that not exists in rep
	vector<string> missing_signals;
	for (size_t i = 0; i < req_signals.size(); ++i)
		if (rep.sigs.sid(req_signals[i]) < 0)
			missing_signals.push_back(req_signals[i]);
	//3. try to resolve missing signals with this priority: conversion, rename, empty signal:
	bool all_model_ok = true;
	for (const string &signal : missing_signals)
	{
		Convert_Res succ_res = try_adjust_model(model, rep, signal, log_actions, !log_missing_categories.empty());
		if (succ_res == FAILED)
			all_model_ok = false;
	}

	//3.1. store adjusted model and reread model and see now only if no completly failor:
	if (all_model_ok) {
		if (cleaner_verbose != 0)
			activate_cleaners_logging(model.rep_processors, cleaner_verbose > 0);

		model.write_to_file(adjusted_model_output_path);
		model.read_from_file(adjusted_model_output_path);
		//rea repo again
		rep.clear();
		if (rep.init(rep_path) < 0)
			MTHROW_AND_ERR("Error can't read repo %s\n", rep_path.c_str());
		req_signals.clear();
		model.fit_for_repository(rep);
		model.collect_and_add_virtual_signals(rep);
		model.get_required_signal_names(req_signals);
		for (size_t i = 0; i < req_signals.size(); ++i)
			if (rep.sigs.sid(req_signals[i]) < 0) {
				MLOG("Error - still unknown signal %s in rep and model uses it\n", req_signals[i].c_str());
				all_model_ok = false;
			}

		//4. Iterate over categorical signals and check all codes exists in repository!
		unordered_map<string, vector<string>> signal_to_ls_categories; // map from signal name to used categories in the model
		model.get_required_signal_categories(signal_to_ls_categories);

		bool all_categ_ok = true;

		//Register virtual signals categories:
		model.init_all(rep.dict, rep.sigs);

		for (const auto &it : signal_to_ls_categories) {
			const string &signal_name = it.first;
			int sid = rep.sigs.sid(signal_name);
			if (sid < 0) {
				snprintf(msg_buffer, sizeof(msg_buffer), "MISSING_CATEGORICAL_SIGNAL\t%s\n",
					signal_name.c_str());
				if (log_missing_categories.empty())
					MWARN("%s", msg_buffer);
				else
					log_categ << msg_buffer;

				all_categ_ok = false;
				all_model_ok = false;
				continue;
			}
			int section_id = rep.dict.section_id(signal_name);

			bool all_ok = true;
			for (size_t i = 0; i < it.second.size(); ++i) {
				int test_code = rep.dict.id(section_id, it.second[i]);
				if (test_code < 0) {
					string status = "MISSING_CODE_VALUE";
					if (signal_name == "Smoking_Status")
						status = "MISSING_OPTIONAL_CODE_VALUE";
					snprintf(msg_buffer, sizeof(msg_buffer), "%s\t%s\t%s\n",
						status.c_str(), signal_name.c_str(), it.second[i].c_str());
					//missing code it.second[i] in signal signal_name! 
					if (log_missing_categories.empty())
						MWARN("%s", msg_buffer);
					else
						log_categ << msg_buffer;
					if (signal_name != "Smoking_Status") {
						all_ok = false;
						all_categ_ok = false;
						all_model_ok = false;
					}
				}
			}
			if (all_ok)
				MLOG("catgorical signal %s is OK\n", signal_name.c_str());
			else
				MLOG("catgorical signal %s is BAD\n", signal_name.c_str());
		}
		if (all_categ_ok)
			MLOG("All categorical signals are OK!\n");
		else
			MLOG("Some of the categorical signals are NOT OK!\n");
		if (all_model_ok)
			MLOG("All OK - Model can be applied on repository\n");
		else
			MLOG("There are some problems\n");
	}
}

//=========================================================================================================================
int flow_models_operations(FlowAppParams &ap)
{
	if (ap.options[OPTION_TRAIN_TEST]) {
		if (flow_train_test(ap) < 0) {
			MERR("Flow: train_test : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_LEARN_MATRIX]) {
		if (flow_learn_matrix(ap.xtrain_fname, ap.ytrain_fname, ap.xtest_fname, ap.ytest_fname, ap.learn_model, ap.learn_model_params) < 0) {
			MERR("Flow: learn_matrix : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_GENERATE_FEATURES])
		flow_generate_features(ap.rep_fname, ap.outcome_fname, ap.model_init_fname, ap.matrix_fname,
			ap.train_test_json_alt, ap.f_model, ap.change_model_init, ap.change_model_file);


	if (ap.options[OPTION_GET_MODEL_PREDS]) {
		if (flow_get_model_preds(ap.rep_fname, ap.f_model, ap.f_samples, ap.f_preds, ap.f_pre_json,
			ap.only_post_processors, ap.print_attr, ap.change_model_init, ap.change_model_file) < 0) {
			MERR("Flow: get_model_preds : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_SIMPLE_TRAIN]) {

		if (flow_simple_train(ap.rep_fname, ap.f_model, ap.f_samples, ap.f_json, ap.matrix_fname, ap.no_matrix_retrain, ap.split, ap.predictor,
			ap.predictor_params, ap.train_test_json_alt) < 0) {
			MERR("Flow: simple_train : FAILED\n");
			return -1;
		}

	}

	if (ap.options[OPTION_SIMPLE_TEST]) {

		if (flow_simple_test(ap.rep_fname, ap.f_model, ap.f_samples, ap.f_preds, ap.matrix_fname, ap.split) < 0) {
			MERR("Flow: simple_train : FAILED\n");
			return -1;
		}

	}

	if (ap.options[OPTION_GET_JSON_MAT]) {
		if (flow_get_json_mat(ap.rep_fname, ap.f_model, ap.f_samples, ap.f_json, ap.matrix_fname, ap.stop_step) < 0) {
			MERR("Flow: get_json_mat : FAILED\n");
			return -1;
		}
	}


	if (ap.options[OPTION_GET_MAT]) {
		if (flow_get_mat(ap.rep_fname, ap.f_model, ap.f_samples, ap.matrix_fname, ap.select_features,
			ap.print_attr, ap.f_pre_json, ap.stop_step, ap.change_model_init, ap.change_model_file) < 0) {
			MERR("Flow: get_mat : FAILED\n");
			return -1;
		}
	}


	if (ap.options[OPTION_PRINT_PROCESSORS]) {
		if (flow_print_model_processors(ap.f_model) < 0) {
			MERR("Flow: print model processors: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_MODEL_INFO]) {

		if (flow_print_model_info(ap.f_model, ap.model_predictor_path, ap.predictor_type, ap.importance_param,
			ap.vm["f_matrix"].defaulted() ? "" : ap.vm["f_matrix"].as<string>(),
			ap.vm["rep"].defaulted() ? "" : ap.vm["rep"].as<string>(),
			ap.vm["f_samples"].defaulted() ? "" : ap.vm["f_samples"].as<string>(), ap.max_samples,
			ap.print_json_format, ap.vm["f_output"].defaulted() ? "" : ap.vm["f_output"].as<string>()) < 0) {
			MERR("Flow: print model info: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_EXPORT_PREDICTOR])
	{
		flow_export_predictor(ap.f_model, ap.output_fname);
	}

	if (ap.options[OPTION_REWRITE_OBJECT]) {
		flow_rewrite_object(ap.f_model, ap.object_type, ap.output_fname);
	}

	if (ap.options[OPTION_EXPORT_PRODUCTION]) {
		flow_export_production_model(ap.f_model, ap.output_fname, ap.predictor_type, ap.model_predictor_path, ap.cleaner_verbose,
			ap.vm["rep"].defaulted() ? "" : ap.vm["rep"].as<string>(), ap.minimize_model);
	}

	if (ap.options[OPTION_MODEL_DEP]) {
		flow_check_deps(ap.vm["f_model"].defaulted() ? "" : ap.f_model,
			ap.vm["f_json"].defaulted() ? "" : ap.f_json, ap.sig_name);
	}

	if (ap.options[OPTION_SHAP]) {
		vector<string> grp_names;
		if (!ap.group_names.empty())
			boost::split(grp_names, ap.group_names, boost::is_any_of(",;"));
		flow_print_shap(ap.f_model, ap.vm["f_matrix"].defaulted() ? "" : ap.vm["f_matrix"].as<string>(),
			ap.rep_fname, ap.vm["f_samples"].defaulted() ? "" : ap.vm["f_samples"].as<string>(),
			ap.max_samples, ap.group_ratio, ap.group_cnt, grp_names, ap.normalize, ap.normalize_after, ap.remove_b0, ap.group_signals, ap.bin_uniq,
			ap.vm["bin_method"].defaulted() ? "" : ap.bin_method, ap.vm["f_output"].defaulted() ? "" : ap.output_fname,
			ap.relearn_predictor, ap.keep_imputers, ap.vm["f_json"].defaulted() ? "" : ap.f_json, ap.cohort_filter, ap.zero_missing_contrib);
	}

	if (ap.options[OPTION_PRINT_MDOEL_SIGNALS]) {
		flow_print_model_signals(ap.f_model, ap.vm["rep"].defaulted() ? "" : ap.rep_fname,
			ap.output_dict_path, !ap.transform_rep);
	}

	if (ap.options[OPTION_GET_PROPENSITY_WEIGHTS]) {
		get_propensity_weights(ap.rep_fname, ap.f_model, ap.f_samples,
			ap.vm["f_matrix"].defaulted() ? "" : ap.matrix_fname, ap.f_preds,
			ap.max_propensity_weight, ap.trim_propensity_weight, ap.prop_attr_weight_name,
			ap.override_outcome, ap.do_conversion, ap.vm["f_json"].defaulted() ? "" : ap.f_json,
			ap.propensity_feature_name, ap.propensity_sampling);
	}

	if (ap.options[OPTION_TT_PREDICTOR_ON_MAT]) {

		train_test_predictor(ap.vm["f_matrix"].defaulted() ? "" : ap.matrix_fname, ap.f_test_matrix,
			ap.split, ap.predictor_type, ap.predictor_params, ap.vm["f_preds"].defaulted() ? "" : ap.f_preds);
	}

	if (ap.options[OPTION_PREDICT_ON_MAT]) {
		apply_predictor_on_mat(ap.vm["f_matrix"].defaulted() ? "" : ap.matrix_fname,
			ap.vm["f_model"].defaulted() ? "" : ap.f_model, ap.vm["f_preds"].defaulted() ? "" : ap.f_preds,
			ap.rep_fname, ap.apply_feat_processors);
	}

	if (ap.options[OPTION_RENAME_MODEL_SIGNAL]) {
		rename_model_signal(ap.vm["f_model"].defaulted() ? "" : ap.f_model,
			ap.vm["f_output"].defaulted() ? "" : ap.output_fname, ap.sig_name, ap.signal_rename);
	}

	if (ap.options[OPTION_FIT_MODEL_TO_REP]) {
		fit_model_to_repository(ap.vm["rep"].defaulted() ? "" : ap.rep_fname,
			ap.vm["f_model"].defaulted() ? "" : ap.f_model,
			ap.vm["f_output"].defaulted() ? "" : ap.output_fname,
			ap.log_action_file_path, ap.log_missing_categories_path, ap.cleaner_verbose,
			ap.allow_virtual_rep, ap.remove_explainability);
	}
	return 0;
}