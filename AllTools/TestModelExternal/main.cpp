#include <string>
#include <iostream>
#include <algorithm>
#include <random>
#include <cmath>
#include <boost/filesystem.hpp>
#include <boost/algorithm/string.hpp>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedStat/MedStat/MedBootstrap.h>
#include <MedAlgo/MedAlgo/BinSplitOptimizer.h>
#include <MedProcessTools/MedProcessTools/ExplainWrapper.h>
#include "Cmd_Args.h"
using namespace std;

void read_features_binning_config(const string &file_path,
	const vector<string> &all_feat_names, unordered_map<string, BinSettings> &res) {
	res.clear();
	if (file_path.empty())
		return;
	ifstream of(file_path);
	if (!of.good())
		MTHROW_AND_ERR("Error can't find file %s\n", file_path.c_str());
	string line;
	while (getline(of, line)) {
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Error bad file format in file %s in line:\n%s\n",
				file_path.c_str(), line.c_str());
		BinSettings bs;
		bs.init_from_string(boost::trim_copy(tokens[1]));
		//find in regex:
		boost::regex reg_pat = boost::regex(boost::trim_copy(tokens[0]));
		for (const string &feat_name : all_feat_names)
		{
			if (boost::regex_search(feat_name, reg_pat)) {
				if (res.find(feat_name) != res.end())
					MWARN("WARNING : Error feature %s has more than 1 matching regex\n",
						feat_name.c_str());
				res[feat_name] = bs;
			}
		}
	}
	MLOG("Read feature bin config from %s and has %zu features\n",
		file_path.c_str(), res.size());

	of.close();
}

void apply_binning_on_features(const unordered_map<string, BinSettings> &feature_bin_settings,
	MedFeatures &features) {
	vector<int> empty_for_all;
	for (auto &it : features.data)
	{
		if (feature_bin_settings.find(it.first) == feature_bin_settings.end())
			continue;
		const BinSettings &bs = feature_bin_settings.at(it.first);
		medial::process::split_feature_to_bins(bs, it.second, empty_for_all,
			it.second);
	}
}

float find_closest(const vector<float> &sorted_vals, float val) {
	int pos = medial::process::binary_search_position(sorted_vals, val);
	//pos is in range [0, v.size()] - position in sorted_vals where it's is smaller equals to sorted_vals[pos] but bigger than pos-1 
	if (pos >= sorted_vals.size())
		pos = (int)sorted_vals.size() - 1;

	if (sorted_vals[pos] == val)
		return val;
	//not equal - means sorted_vals[pos] > val
	if (pos == 0)
		return sorted_vals[0];
	//pos > 0  - mean val is not lower than lowest value in sorted_vals:
	float diff_lower = val - sorted_vals[pos - 1];
	float diff_upper = sorted_vals[pos] - val;
	if (diff_lower < diff_upper)
		return  sorted_vals[pos - 1];
	else
		return sorted_vals[pos];
}

void fix_res_between_mat(const MedFeatures &source, MedFeatures &target) {
	vector<string> feat_names;
	source.get_feature_names(feat_names);
	vector<vector<float> *> features_p(feat_names.size());
	vector<const vector<float> *> src_feature_p(feat_names.size());
	for (size_t i = 0; i < feat_names.size(); ++i) {
		if (target.data.find(feat_names[i]) == target.data.end())
			MTHROW_AND_ERR("Error: source has feature %s which is missing in target\n", feat_names[i].c_str());
		features_p[i] = &target.data.at(feat_names[i]);
		src_feature_p[i] = &source.data.at(feat_names[i]);
	}

	MedProgress progress("fix_resolution", (int)feat_names.size(), 30, 1);
#pragma omp parallel for
	for (int i = 0; i < feat_names.size(); ++i)
	{
		unordered_set<float> uniq_vals(src_feature_p[i]->begin(), src_feature_p[i]->end());
		vector<float> sorted_source_bins(uniq_vals.begin(), uniq_vals.end());
		sort(sorted_source_bins.begin(), sorted_source_bins.end());

		vector<float> &to_change = *features_p[i];
		//choose clooset value for each to_change in option values sorted_source_bins
		for (size_t i = 0; i < to_change.size(); ++i)
			to_change[i] = find_closest(sorted_source_bins, to_change[i]);

		progress.update();
	}
}

void get_model_imputers(const MedModel &model, vector<FeatureProcessor *> &keep_p,
	vector<MultiFeatureProcessor *> &to_clear, bool use_imputer) {
	vector<bool> filter_mask(FTR_PROCESS_LAST);
	filter_mask[FTR_PROCESS_NORMALIZER] = true;
	if (!use_imputer) {
		filter_mask[FTR_PROCESS_IMPUTER] = true;
		filter_mask[FTR_PROCESS_ITERATIVE_IMPUTER] = true;
		filter_mask[FTR_PROCESS_PREDICTOR_IMPUTER] = true;
	}

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
					/*delete multi->processors[j];
					multi->processors[j] = NULL;*/
				}
			}
			if (!keep_internal_p.empty()) {
				MultiFeatureProcessor *multi_new = new MultiFeatureProcessor;
				multi_new->duplicate = multi->duplicate;
				multi_new->processors = move(keep_internal_p);
				keep_p.insert(keep_p.begin(), multi_new);
				to_clear.push_back(multi_new);
				//turn true if contains fp that is not selector:
				for (size_t j = 0; j < keep_internal_p.size() && !kept_fp; ++j)
					kept_fp = !keep_internal_p[j]->is_selector();
			}

			//clear mem
			//multi->processors.clear(); //already cleared what's neede inside
			//delete multi;
			//model.feature_processors[i] = NULL;
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
				/*delete model.feature_processors[i];
				model.feature_processors[i] = NULL;*/
			}

		}
	}
}

void prepare_features_from_samples(MedModel &model, const string &rep, MedSamples &samples_test,
	int max_samples, bool use_imputer, MedFeatures &features, MedFeatures &non_norm_features,
	bool add_outcome, const string &model_json_additional_path, MedModel &additional_feats) {
	int nsamlpes = samples_test.nSamples();
	if (max_samples > 0 && max_samples < nsamlpes)
		medial::process::down_sample(samples_test, float(max_samples) / nsamlpes);
	MedPidRepository repo;
	vector<int> pid_ids;
	samples_test.get_ids(pid_ids);
	if (!model.generators.empty()) {
		model.load_repository(rep, pid_ids, repo, true);

		if (model.apply(repo, samples_test, MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_END) < 0)
			MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");
		features = move(model.features);
	}
	MedPidRepository additional_rep;
	if (!model_json_additional_path.empty()) {
		//load additional features:
		if (additional_feats.version_info.empty()) { //not trained model
			if (!model.generators.empty()) {
				//update additional_feats serial_num to match model serial_num
				int max_serial_id = 0;
				for (FeatureGenerator *fg : model.generators)
					if (fg->serial_id > max_serial_id)
						max_serial_id = fg->serial_id;

				MedFeatures::global_serial_id_cnt = max_serial_id;
				//init before loading model from json
			}
			additional_feats.init_from_json_file(model_json_additional_path);
		}

		additional_feats.load_repository(rep, pid_ids, additional_rep, true);
		if (additional_feats.version_info.empty()) { //not trained model
			if (additional_feats.learn(additional_rep, samples_test, MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("medial::medmodel::learn() ERROR :: could not learn model\n");
		}
		else {
			if (additional_feats.apply(additional_rep, samples_test, MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
				MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");
		}

		if (model.generators.empty())
			features = move(additional_feats.features);
		else {//add features
			for (auto &it : additional_feats.features.data)
				if (features.data.find(it.first) != features.data.end())
					MWARN("Feature %s is defined by model - skipped\n", it.first.c_str());
				else
					features.data[it.first] = move(it.second);
		}
	}

	if (add_outcome) {
		vector<float> &out_feat = features.data["Outcome"];
		out_feat.resize(features.samples.size());
		for (size_t i = 0; i < features.samples.size(); ++i)
			out_feat[i] = features.samples[i].outcome;
		features.attributes["Outcome"].imputed = false;
	}
	//remove imputer, normalizer from Feature Processors:
	vector<bool> filter_mask(FTR_PROCESS_LAST);
	filter_mask[FTR_PROCESS_NORMALIZER] = true;
	if (!use_imputer) {
		filter_mask[FTR_PROCESS_IMPUTER] = true;
		filter_mask[FTR_PROCESS_ITERATIVE_IMPUTER] = true;
		filter_mask[FTR_PROCESS_PREDICTOR_IMPUTER] = true;
	}

	vector<FeatureProcessor *> keep_p;
	vector<MultiFeatureProcessor *> to_clear;
	if (!model.generators.empty()) {
		vector<FeatureProcessor *> backup = model.feature_processors;

		get_model_imputers(model, keep_p, to_clear, use_imputer);
		model.feature_processors = keep_p;

		if (model.apply(repo, samples_test, MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
			MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");
		model.feature_processors = backup;
		non_norm_features = move(model.features);

		for (size_t i = 0; i < to_clear.size(); ++i) {
			to_clear[i]->processors.clear(); //that won't clear FP memory
			delete to_clear[i];
			to_clear[i] = NULL;
		}
		to_clear.clear();
		keep_p.clear();
	}
	if (!model_json_additional_path.empty()) {
		//add additional features:
		vector<FeatureProcessor *> backup = additional_feats.feature_processors;
		get_model_imputers(additional_feats, keep_p, to_clear, use_imputer);
		additional_feats.feature_processors = keep_p;

		if (additional_feats.apply(additional_rep, samples_test, MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
			MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");
		additional_feats.feature_processors = backup;
		if (model.generators.empty())
			non_norm_features = move(additional_feats.features);
		else {//add features
			for (auto &it : additional_feats.features.data)
				if (non_norm_features.data.find(it.first) != non_norm_features.data.end())
					MWARN("Feature %s is defined by model - skipped\n", it.first.c_str());
				else
					non_norm_features.data[it.first] = move(it.second);
		}

		for (size_t i = 0; i < to_clear.size(); ++i) {
			to_clear[i]->processors.clear(); //that won't clear FP memory
			delete to_clear[i];
			to_clear[i] = NULL;
		}

	}
	if (add_outcome) {
		vector<float> &out_feat = non_norm_features.data["Outcome"];
		out_feat.resize(non_norm_features.samples.size());
		for (size_t i = 0; i < non_norm_features.samples.size(); ++i)
			out_feat[i] = non_norm_features.samples[i].outcome;
		non_norm_features.attributes["Outcome"].imputed = false;
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

void flow_print_shap(MedPredictor &predictor, MedFeatures *features, MedFeatures *non_norm_features,
	bool normalize, bool normalize_after, bool remove_b0, const string &group_features,
	const string &binning_method, const string &output_file, vector<pair<string, float>> &ranked)
{
	const string feature_val_catption = "FEAT_VAL";
	const string shap_catption = "SHAP";
	const string score_catption = "SCORE";
	const string outcome_catption = "OUTCOME";
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

	BinSettings bin_setts;
	if (!binning_method.empty())
		bin_setts.init_from_string(binning_method);

	// feature importance print
	MedMat<float> mat, mat_contrib, mat_non_norm;
	features->get_as_matrix(mat);
	non_norm_features->get_as_matrix(mat_non_norm);

	try {
		predictor.calc_feature_contribs(mat, mat_contrib);
		MLOG("Done calc\n");
	}
	catch (...) {
		MLOG("Unsupported\n");
		if (!output_file.empty())
			fw.close();
		return;
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
	ranked.resize(mat_contrib.ncols);
	unordered_map<string, map<string, float>> feat_to_measures_vals;
	//for top 20%, and low 20% calc prctile, average contrib no abs
	unordered_map<string, string> rep_names;
	MedProgress progress_("Feature_Contribution", (int)mat_contrib.ncols, 15, 10);
	int max_group_sz = 0;
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
		contrib /= mat_contrib.nrows;
		sort(collected.begin(), collected.end(), [](const pair<Collected_stats, float> &a, const pair<Collected_stats, float> &b)
		{  return a.second < b.second;
		});

		vector<vector<float>> grp_vals, grp_feature_vals, grp_outcome, grp_score;

		//update: grp_vals (contribution), grp_feature_vals(feature value) - to processed stats. used collected!
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

		int feature_grp_count = (int)index_bins.size();

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


		for (size_t k = 0; k < feature_grp_count; ++k) {
			float mean_v, std_v;
			float mean_v_feat, std_v_feat;
			float mean_v_outcome, std_v_outcome;
			float mean_v_score, std_v_score;
			vector<float> prctile_res, prctile_feat_res, prctile_outcome_res, prctile_score_res;
			string grp_name = to_string(k);
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
		string grp_name = to_string(k);
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

void filter_features(const unordered_set<string> &selected_features, map<string, vector<float>> &mat) {
	map<string, vector<float>> filtered;
	for (const auto &it : mat)
		if (selected_features.find(it.first) != selected_features.end())
			filtered[it.first] = move(it.second);
	mat = move(filtered);
}

void load_additional_rank(const string &additional_importance_to_rank,
	vector<pair<string, float>> &ranked) {
	MLOG("Reading additional rank %s\n", additional_importance_to_rank.c_str());
	ifstream rank_fr(additional_importance_to_rank);
	string header, line;
	getline(rank_fr, header); // Feature, Representative(optional), Importance
	vector<string> tokens;
	boost::split(tokens, header, boost::is_any_of("\t"));
	int importance_idx = 1;
	if (tokens[importance_idx] != "Importance")
		importance_idx = 2;
	if (tokens[importance_idx] != "Importance") {
		rank_fr.close();
		MTHROW_AND_ERR("Error Can't find importance index\n");
	}
	unordered_map<string, double> additional_rank;
	double avg_importance = 0;
	while (getline(rank_fr, line)) {
		boost::split(tokens, line, boost::is_any_of("\t"));
		string group_feature = tokens[0];
		double importance = med_stof(tokens[importance_idx]);
		additional_rank[group_feature] = importance;
		avg_importance += importance;
	}
	rank_fr.close();
	if (!additional_rank.empty())
		avg_importance /= additional_rank.size();
	//manipulate ranked with additional by multiplying
	//Assume group to group or feature to feature, act directly wiht same names
	if (additional_rank.size() != ranked.size())
		MWARN("WARN - not same sizes (%zu, %zu) of ranked and additioanl\n",
			ranked.size(), additional_rank.size());
	for (size_t i = 0; i < ranked.size(); ++i)
	{
		if (additional_rank.find(ranked[i].first) != additional_rank.end())
			ranked[i].second *= additional_rank.at(ranked[i].first);
		else {
			//take average
			ranked[i].second *= avg_importance;
			MWARN("WARN missed group/feature %s in additional rank\n", ranked[i].first.c_str());
		}
	}

	//sort again:
	sort(ranked.begin(), ranked.end(), [](const pair<string, float> &c1, const pair<string, float> &c2)
	{
		return c1.second > c2.second;
	});
}

void plot_graph(MedFeatures &test_prop_mat, MedPredictor* propensity_predictor, const string &calibration_init_str
	, const string &feat_name, const string &out_folder, const string &html_template,
	const string &name_for_train, const string &name_for_test) {
	string full_html = out_folder + path_sep() + feat_name + ".html";
	//use attribute "original_outcome" and outcome
	//divide into cases(TEST)/controls(TRAIN) and controls weighted()

	vector<string> seriesNames = { name_for_train + ":Controls", name_for_train + ":Cases",
		name_for_test + ":Controls", name_for_test + ":Cases",
		name_for_train + ".weigthed:Controls", name_for_train + ".weigthed:Cases",
		name_for_train + ":Controls:marked_imputations", name_for_train + ":Cases:marked_imputations",
		name_for_test + ":Controls:marked_imputations", name_for_test + ":Cases:marked_imputations" };
	int num_of_graphs = seriesNames.size();
	vector<vector<pair<float, float>>> graph_to_feature_hist(num_of_graphs);
	vector<unordered_map<float, float>> graph_to_features_map(num_of_graphs);
	vector<double> cohort_sz(num_of_graphs);

	const vector<float> &vals = test_prop_mat.data.at(feat_name);
	const vector<unsigned char> &masks = test_prop_mat.masks[feat_name];
	for (size_t i = 0; i < test_prop_mat.samples.size(); ++i)
	{
		int idx = 0;
		if (test_prop_mat.samples[i].outcome > 0)
			idx = 2;
		int internal_idx = 0;
		if (feat_name != "Outcome")
			internal_idx = int(stoi(test_prop_mat.samples[i].str_attributes["original_outcome"]) > 0);
		idx += internal_idx;
		bool mark_imputed = (i < masks.size() && (masks[i] & MedFeatures::imputed_mask));
		float val = vals[i];

		unordered_map<float, float> &curr_g = graph_to_features_map[idx];
		//populate
		++curr_g[val];
		++cohort_sz[idx];

		//with imutations marked!
		idx += 6;
		if (mark_imputed) 
			val = MED_MAT_MISSING_VALUE;
		++graph_to_features_map[idx][val];
		++cohort_sz[idx];
	}
	//Add graphs 4,5 (score is the predicted score before calibarion.):
	test_prop_mat.weights.resize(test_prop_mat.samples.size());
	double propensity_cutoff = 1e-5;
	bool trim_propensity_weight = false;
	double max_propensity_weight = 1 / propensity_cutoff;
	for (size_t i = 0; i < test_prop_mat.samples.size(); ++i)
	{
		if (test_prop_mat.samples[i].outcome > 0)
			continue; //This is test sample - skip

		float prob = test_prop_mat.samples[i].prediction[0];
		//Always control
		if (prob < 1 && prob <= 1 - propensity_cutoff)
			test_prop_mat.weights[i] = 1 / (1 - prob);
		else {
			if (trim_propensity_weight)
				test_prop_mat.weights[i] = max_propensity_weight;
			else
				test_prop_mat.weights[i] = 0; //drop
		}
		test_prop_mat.weights[i] *= prob;
	}
	for (size_t i = 0; i < test_prop_mat.samples.size(); ++i)
	{
		if (test_prop_mat.samples[i].outcome > 0)
			continue; //This is test sample - skip
		int idx = 4;
		if (feat_name != "Outcome")
			idx += int(stoi(test_prop_mat.samples[i].str_attributes["original_outcome"]) > 0);
		unordered_map<float, float> &curr_g = graph_to_features_map[idx];
		//populate
		curr_g[vals[i]] += test_prop_mat.weights[i];
		cohort_sz[idx] += test_prop_mat.weights[i];
	}

	//convert graph_to_features_map into graph_to_feature_hist with normalization - Handle missing values
	for (size_t i = 0; i < graph_to_feature_hist.size(); ++i)
	{
		double curr_size = cohort_sz[i];
		for (const auto &it : graph_to_features_map[i])
			if (curr_size > 0)
				graph_to_feature_hist[i].push_back(pair<float, float>(it.first, float(100 * it.second / curr_size)));
		sort(graph_to_feature_hist[i].begin(), graph_to_feature_hist[i].end(), [](const pair<float, float> &a, const pair<float, float> &b)
		{ return a.first < b.first; });
	}

	if (feat_name == "Outcome") {
		graph_to_feature_hist = { graph_to_feature_hist[0],graph_to_feature_hist[2],graph_to_feature_hist[4] };
		seriesNames = { name_for_train, name_for_test, name_for_train + ".weighted" };
	}
	createScatterHtmlGraph(full_html, graph_to_feature_hist, feat_name + " Histogram",
		feat_name, "Percentage(%)", seriesNames, 0, "scatter", "markers+lines", html_template);
}

void compare_model_by_repositories(const ProgramArgs &args) {
	if ((args.rep_trained.empty() || args.samples_train.empty()) && args.train_matrix_csv.empty())
		return;
	MLOG("Compare using another repository\n");
	MedModel model;
	if (!args.model_path.empty())
		model.read_from_file(args.model_path);
	model.generate_masks_for_features = 1;

	MedSamples train_rep_samples;
	MedFeatures train_feats, unnorm_train;
	MedModel additional_feature_model;
	if (!args.train_matrix_csv.empty()) {
		train_feats.read_from_csv_mat(args.train_matrix_csv);
		if (args.sub_sample_train > 0 && args.sub_sample_train < train_feats.samples.size())
			medial::process::down_sample(train_feats, float(args.sub_sample_train) / train_feats.samples.size());
		if (args.match_also_outcome) {
			vector<float> &outcome_vec = train_feats.data["Outcome"];
			outcome_vec.resize(train_feats.samples.size());
			for (size_t i = 0; i < outcome_vec.size(); ++i)
				outcome_vec[i] = train_feats.samples[i].outcome;
			train_feats.attributes["Outcome"].imputed = false;
		}
		unnorm_train = train_feats;
	}
	else {
		train_rep_samples.read_from_file(args.samples_train);
		prepare_features_from_samples(model, args.rep_trained, train_rep_samples, args.sub_sample_train,
			false, train_feats, unnorm_train, args.match_also_outcome, args.model_json_additional_path, additional_feature_model);
	}

	MedSamples test_rep_samples;
	MedFeatures test_feats, unnorm_test;
	test_rep_samples.read_from_file(args.samples_test);
	prepare_features_from_samples(model, args.rep_test, test_rep_samples, args.sub_sample_test,
		false, test_feats, unnorm_test, args.match_also_outcome, args.model_json_additional_path, additional_feature_model);
	//filter features if needed:

	if (!args.features_subset_file.empty()) {
		MLOG("Filtering features to subset by %s\n", args.features_subset_file.c_str());
		vector<string> selected_features, all_mat_names;
		medial::io::read_codes_file(args.features_subset_file, selected_features);
		train_feats.get_feature_names(all_mat_names);
		for (size_t i = 0; i < selected_features.size(); ++i)
			selected_features[i] = all_mat_names[find_in_feature_names(all_mat_names, selected_features[i])];
		unordered_set<string> feat_set(selected_features.begin(), selected_features.end());
		if (args.match_also_outcome)
			feat_set.insert("Outcome");

		filter_features(feat_set, test_feats.data);
		filter_features(feat_set, train_feats.data);
		filter_features(feat_set, unnorm_test.data);
		filter_features(feat_set, unnorm_train.data);
		MLOG("Done filtering\n");
	}

	//test matrices:
	bool not_full_match = false;
	for (auto &it : train_feats.data)
		if (test_feats.data.find(it.first) == test_feats.data.end()) {
			MERR("ERR :: Missing feature %s in test\n", it.first.c_str());
			not_full_match = true;
		}
	for (auto &it : test_feats.data)
		if (train_feats.data.find(it.first) == train_feats.data.end()) {
			MERR("ERR :: Missing feature %s in train\n", it.first.c_str());
			not_full_match = true;
		}

	if (test_feats.data.size() != train_feats.data.size())
		MTHROW_AND_ERR("Error train and test matrices are not same size [%zu, %zu]\n", train_feats.data.size()
			, test_feats.data.size());
	if (not_full_match)
		MTHROW_AND_ERR("Error train and test matrices differ\n");


	if (!args.feature_binning_config.empty()) {
		unordered_map<string, BinSettings> feat_bin_settings;
		vector<string> all_names;
		test_feats.get_feature_names(all_names);
		read_features_binning_config(args.feature_binning_config, all_names, feat_bin_settings);

		//Apply binning on features - train_feats/test_feats:
		apply_binning_on_features(feat_bin_settings, train_feats);
		apply_binning_on_features(feat_bin_settings, test_feats);
	}

	// bin to feature values - since some of the seperation power is due to reslulotion
	if (args.fix_test_res)
		fix_res_between_mat(train_feats, test_feats);
	if (args.fix_train_res)
		fix_res_between_mat(test_feats, train_feats); //do opposite - use test resolution to fix train resolution

													  //create MedFeatures for predictor
	MedFeatures propensity_features; //data,masks, samples, weights - leave empty
	propensity_features.attributes = train_feats.attributes;
	propensity_features.tags = train_feats.tags;
	propensity_features.time_unit = train_feats.time_unit;
	propensity_features.medf_missing_value = train_feats.medf_missing_value;
	//samples:
	for (size_t i = 0; i < train_feats.samples.size(); ++i)
	{
		MedSample s = train_feats.samples[i];
		int original_id = s.id;
		s.id = (int)i;
		s.prediction.clear();
		s.attributes.clear();
		s.str_attributes.clear();
		s.str_attributes["original_outcome"] = to_string(int(s.outcome));
		s.outcome = 0;
		s.str_attributes["original_id"] = to_string(int(original_id));
		propensity_features.samples.push_back(s);
	}
	for (size_t i = 0; i < test_feats.samples.size(); ++i)
	{
		MedSample s = test_feats.samples[i];
		int original_id = s.id;
		s.id = (int)train_feats.samples.size() + (int)i;
		s.prediction.clear();
		s.attributes.clear();
		s.str_attributes.clear();
		s.str_attributes["original_outcome"] = to_string(int(s.outcome));
		s.outcome = 1;
		s.str_attributes["original_id"] = to_string(int(original_id));
		propensity_features.samples.push_back(s);
	}
	//data:
	MedFeatures non_norm_features = propensity_features;
	for (const auto &it : train_feats.data)
	{
		const vector<unsigned char> &source_masks = train_feats.masks[it.first];
		vector<float> &v = propensity_features.data[it.first];
		vector<unsigned char> &mask_imp = propensity_features.masks[it.first];
		if (v.empty())
			v.resize(train_feats.samples.size() + test_feats.samples.size());
		if (mask_imp.empty())
			mask_imp.resize(train_feats.samples.size() + test_feats.samples.size());

		for (size_t i = 0; i < it.second.size(); ++i)
			v[i] = it.second[i];
		if (source_masks.empty()) {
			for (size_t i = 0; i < source_masks.size(); ++i)
				mask_imp[i] = 8; //mark unknown - for example if loaded from matrix!
		}
		else {
			for (size_t i = 0; i < source_masks.size(); ++i)
				mask_imp[i] = source_masks[i];
		}
	}
	for (const auto &it : test_feats.data)
	{
		const vector<unsigned char> &source_masks = test_feats.masks.at(it.first);
		vector<float> &v = propensity_features.data.at(it.first);
		vector<unsigned char> &mask_imp = propensity_features.masks[it.first];
		for (size_t i = 0; i < it.second.size(); ++i)
			v[train_feats.samples.size() + i] = it.second[i];
		for (size_t i = 0; i < source_masks.size(); ++i)
			mask_imp[train_feats.samples.size() + i] = source_masks[i];
	}

	for (const auto &it : unnorm_train.data)
	{
		vector<float> &v = non_norm_features.data[it.first];
		if (v.empty())
			v.resize(unnorm_train.samples.size() + unnorm_test.samples.size());
		for (size_t i = 0; i < it.second.size(); ++i)
			v[i] = it.second[i];
	}
	for (const auto &it : unnorm_test.data)
	{
		vector<float> &v = non_norm_features.data.at(it.first);
		for (size_t i = 0; i < it.second.size(); ++i)
			v[unnorm_train.samples.size() + i] = it.second[i];
	}
	propensity_features.init_pid_pos_len();
	non_norm_features.init_pid_pos_len();

	if (args.output != "/dev/null" && args.print_mat) {
		propensity_features.write_as_csv_mat(args.output + path_sep() + "rep_propensity.matrix", true);
		non_norm_features.write_as_csv_mat(args.output + path_sep() + "rep_propensity_non_norm.matrix");
		MedMat<unsigned char> imputed_masks;
		propensity_features.get_masks_as_mat(imputed_masks);
		imputed_masks.write_to_csv_file(args.output + path_sep() + "imputation_masts.medmat");
	}
	//split to train\test
	MedFeatures train_prop_copy = propensity_features;
	if (args.train_ratio > 0 && args.train_ratio < 1) {
		MLOG("Split train test...\n");
		vector<int> train_idx(propensity_features.samples.size() * args.train_ratio);
		uniform_int_distribution<> sel_gen(0, (int)propensity_features.samples.size() - 1);
		random_device rd;
		mt19937 gen(rd());
		vector<bool> seen(propensity_features.samples.size());
		for (size_t i = 0; i < train_idx.size(); ++i)
		{
			int sel_i = sel_gen(gen);
			while (seen[sel_i])
				sel_i = sel_gen(gen);
			seen[sel_i] = true;
			train_idx[i] = sel_i;
		}
		sort(train_idx.begin(), train_idx.end());

		MLOG("Filtering train test\n");
		//Loop for parallel
#pragma omp parallel for
		for (int i = 0; i < 3; ++i) {
			if (i == 0)
				medial::process::filter_row_indexes_safe(train_prop_copy, train_idx);
			else if (i == 1)
				medial::process::filter_row_indexes_safe(propensity_features, train_idx, true);
			else if (i == 2)
				medial::process::filter_row_indexes_safe(non_norm_features, train_idx, true);
		}
		MLOG("Done train test\n");
	}
	else
		MLOG("OVERFITING!!! - OK for most scenarios in this case\n");

	//Build propensity model to seperate between both reps - between train_feats and test_feats
	unique_ptr<MedPredictor> propensity_predictor = unique_ptr<MedPredictor>(MedPredictor::make_predictor(args.predictor_type, args.predictor_args));
	propensity_predictor->learn(train_prop_copy);

	//Apply on test:
	propensity_predictor->predict(propensity_features);
	if (args.output != "/dev/null") {
		boost::filesystem::create_directories(args.output);
		MedSamples pred_samples;
		pred_samples.import_from_sample_vec(propensity_features.samples);
		pred_samples.write_to_file(args.output + path_sep() + "test_propensity.preds");

		//save model:
		//read again a second model copy
		MedModel full_prop_model;
		full_prop_model.read_from_file(args.model_path);

		//Add additional features from other model if needed
		vector<string> full_names;
		train_prop_copy.get_feature_names(full_names);

		if (!args.model_json_additional_path.empty()) {
			//check that we use some of the features?
			bool using_f = false;
			unordered_set<string> f_set_names(full_names.begin(), full_names.end());
			for (const auto &it : additional_feature_model.features.data)
				if (f_set_names.find(it.first) != f_set_names.end()) {
					using_f = true;
					break;
				}

			if (using_f) {
				full_prop_model.rep_processors.insert(full_prop_model.rep_processors.end(),
					additional_feature_model.rep_processors.begin(), additional_feature_model.rep_processors.end());

				full_prop_model.generators.insert(full_prop_model.generators.end(),
					additional_feature_model.generators.begin(), additional_feature_model.generators.end());

				full_prop_model.feature_processors.insert(full_prop_model.feature_processors.end(),
					additional_feature_model.feature_processors.begin(), additional_feature_model.feature_processors.end());

				//prevent multipl clear of memory:
				additional_feature_model.rep_processors.clear();
				additional_feature_model.generators.clear();
				additional_feature_model.feature_processors.clear();
			}

		}
		//Add filters to features if needed:
		if (!args.features_subset_file.empty()) {
			//If has additional selector - remove - not needed
			vector<FeatureProcessor *> fp_clean_list;
			fp_clean_list.reserve(full_prop_model.feature_processors.size());
			for (size_t i = 0; i < full_prop_model.feature_processors.size(); ++i)
			{
				if (full_prop_model.feature_processors[i]->processor_type == FTR_PROCESS_MULTI) {
					MultiFeatureProcessor *multi_fp = static_cast<MultiFeatureProcessor *>(full_prop_model.feature_processors[i]);
					vector<FeatureProcessor *> multi_clean_list;
					multi_clean_list.reserve(multi_fp->processors.size());
					for (size_t j = 0; j < multi_fp->processors.size(); ++j)
						if (multi_fp->processors[j]->is_selector()) {
							delete multi_fp->processors[j];
							multi_fp->processors[j] = NULL;
						}
						else
							multi_clean_list.push_back(multi_fp->processors[j]);

					if (!multi_clean_list.empty()) {
						multi_fp->processors = move(multi_clean_list);
						fp_clean_list.push_back(multi_fp);
					}
					else
					{
						delete full_prop_model.feature_processors[i];
						full_prop_model.feature_processors[i] = NULL;
					}
				}
				else {
					if (full_prop_model.feature_processors[i]->is_selector()) {
						delete full_prop_model.feature_processors[i];
						full_prop_model.feature_processors[i] = NULL;
					}
					else
						fp_clean_list.push_back(full_prop_model.feature_processors[i]);
				}
			}
			full_prop_model.feature_processors = move(fp_clean_list);

			FeatureProcessor *tag_sel = FeatureProcessor::make_processor("tags_selector", "verbose=0");

			((TagFeatureSelector *)tag_sel)->selected_tags.insert(((TagFeatureSelector *)tag_sel)->selected_tags.end(), full_names.begin(), full_names.end());
			((FeatureSelector *)tag_sel)->selected.insert(((FeatureSelector *)tag_sel)->selected.end(), full_names.begin(), full_names.end());
			full_prop_model.add_feature_processor(tag_sel);
		}

		//TODO: add resolution fix to the model - or do it externally? not that important for giveing weights

		//set predictor:
		if (full_prop_model.predictor != NULL)
			delete full_prop_model.predictor;
		full_prop_model.set_predictor(propensity_predictor.get());
		//TODO: filter unneeded components
		full_prop_model.write_to_file(args.output + path_sep() + "rep_propensity.model");
		//Add calibration to a second model:
		PostProcessor *pp_cal = PostProcessor::make_processor("calibrator", args.calibration_init_str);
		pp_cal->Learn(propensity_features);

		full_prop_model.add_post_processor(pp_cal);
		full_prop_model.write_to_file(args.output + path_sep() + "rep_propensity.calibrated.model");
		full_prop_model.predictor = NULL; //that won't clear the memory - already handled
	}

	//bootstrap propensity_features:
	MedBootstrapResult bt;
	bt.bootstrap_params.init_from_string(args.bt_params);
	bt.bootstrap(propensity_features);
	if (args.output != "/dev/null")
		bt.write_results_to_text_file(args.output + path_sep() + "test_propensity.bootstrap.pivot_txt");
	double found_auc = 1.1;
	for (const auto &bt_cohort : bt.bootstrap_results)
		if (bt_cohort.second.find("AUC_Mean") != bt_cohort.second.end()) {
			found_auc = (double)bt_cohort.second.at("AUC_Mean");
			MLOG("%s :: AUC_Mean :: %f\n", bt_cohort.first.c_str(), bt_cohort.second.at("AUC_Mean"));
		}

	//shap analysis:
	vector<pair<string, float>> ranked, ranked_norm;
	if (found_auc >= args.shap_auc_threshold) {
		if (args.sub_sample_but_why > 0 && args.calc_shapley_mask > 0) {
			if (propensity_features.samples.size() > args.sub_sample_but_why)
				medial::process::down_sample(propensity_features, args.sub_sample_but_why / double(propensity_features.samples.size()));
			if (non_norm_features.samples.size() > args.sub_sample_but_why && args.calc_shapley_mask & SHAPLEY_FLAG::CALC_UNORM)
				medial::process::down_sample(non_norm_features, args.sub_sample_but_why / double(non_norm_features.samples.size()));
		}
		if (args.calc_shapley_mask & SHAPLEY_FLAG::CALC_UNORM) {
			MLOG("#### => Start Shapley Values Analysis on no-norm and imputed features\n");
			flow_print_shap(*propensity_predictor, &propensity_features, &non_norm_features, true, true, true,
				args.group_shap_params, args.binning_shap_params, args.output + path_sep() + "shapley_report.tsv", ranked);
		}

		if (args.calc_shapley_mask & SHAPLEY_FLAG::CALC_FINAL) {
			MLOG("#### => Start Shapley Values Analysis on final features\n");
			flow_print_shap(*propensity_predictor, &propensity_features, &propensity_features, true, true, true,
				args.group_shap_params, args.binning_shap_params, args.output + path_sep() + "shapley_report.norm_features.tsv", ranked_norm);
		}
	}
	else
		MLOG("Skip Shapely value analysis\n");

	//Stats anaylsis:
	medial::process::compare_populations(train_feats, test_feats, args.name_for_train, args.name_for_test,
		args.output + path_sep() + "compare_rep.txt");

	bool reranked = false;
	if (args.smaller_model_feat_size > 0 && ranked.size() > args.smaller_model_feat_size) {
		MLOG("Creating smaller model, has %zu features/groups and requested %d\n",
			ranked.size(), args.smaller_model_feat_size);
		if (!args.additional_importance_to_rank.empty()) {
			load_additional_rank(args.additional_importance_to_rank, ranked);
			reranked = true;
		}
		ranked.resize(args.smaller_model_feat_size);
		//List all features in those group of ranked:
		vector<string> selected_names;
		vector<string> all_feat_names;
		train_prop_copy.get_feature_names(all_feat_names);
		if (args.group_shap_params.empty()) {
			//No groups - fetch names:
			for (size_t i = 0; i < ranked.size(); ++i)
			{
				string exact_name = all_feat_names[find_in_feature_names(all_feat_names, ranked[i].first)];
				selected_names.push_back(exact_name);
			}
		}
		else {
			//Handle groups:
			vector<vector<int>> group2Inds;
			vector<string> groupNames;
			ExplainProcessings::read_feature_grouping(args.group_shap_params, all_feat_names, group2Inds, groupNames);

			for (size_t i = 0; i < ranked.size(); ++i)
			{
				string group_name = ranked[i].first;
				//find group index:
				int grp_idx = -1;
				for (int k = 0; k < groupNames.size() && grp_idx < 0; ++k)
					if (groupNames[k] == group_name)
						grp_idx = k;
				if (grp_idx < 0)
					MTHROW_AND_ERR("Error - can't find group %s in groups. Grouping param was %s\n",
						group_name.c_str(), args.group_shap_params.c_str());
				const vector<int> &sel_idx = group2Inds[grp_idx];
				for (int feature_idx : sel_idx)
				{
					const string &exact_name = all_feat_names[feature_idx];
					selected_names.push_back(exact_name);
				}
			}
		}

		//Train smaller model
		MedFeatures small_prop_features = train_prop_copy;
		unordered_set<string> feat_sets(selected_names.begin(), selected_names.end());
		small_prop_features.filter(feat_sets);
		MedFeatures small_calibrate_train = propensity_features;
		small_calibrate_train.filter(feat_sets);

		MedModel small_prop_model;
		small_prop_model.read_from_file(args.model_path);

		unique_ptr<MedPredictor> small_propensity_predictor = unique_ptr<MedPredictor>(MedPredictor::make_predictor(args.predictor_type, args.predictor_args));
		small_propensity_predictor->learn(small_prop_features);
		small_propensity_predictor->predict(small_calibrate_train);

		//Add feature selection to the model:
		FeatureProcessor *tag_sel = FeatureProcessor::make_processor("tags_selector", "verbose=0");
		((TagFeatureSelector *)tag_sel)->selected_tags.insert(((TagFeatureSelector *)tag_sel)->selected_tags.end(), selected_names.begin(), selected_names.end());
		((FeatureSelector *)tag_sel)->selected.insert(((FeatureSelector *)tag_sel)->selected.end(), selected_names.begin(), selected_names.end());
		small_prop_model.add_feature_processor(tag_sel);

		if (small_prop_model.predictor != NULL)
			delete small_prop_model.predictor;
		small_prop_model.set_predictor(small_propensity_predictor.get());

		PostProcessor *pp_cal = PostProcessor::make_processor("calibrator", args.calibration_init_str);
		pp_cal->Learn(small_calibrate_train);

		small_prop_model.add_post_processor(pp_cal);
		small_prop_model.write_to_file(args.output + path_sep() + "rep_propensity_small.calibrated.model");
		small_prop_model.predictor = NULL; //that won't clear the memory - already handled

		MedBootstrapResult bt_small;
		bt_small.bootstrap_params.init_from_string(args.bt_params);
		bt_small.bootstrap(small_calibrate_train);
		for (const auto &bt_cohort : bt_small.bootstrap_results)
			if (bt_cohort.second.find("AUC_Mean") != bt_cohort.second.end())
				MLOG("(Small propensity model) %s :: AUC_Mean :: %f\n", bt_cohort.first.c_str(), bt_cohort.second.at("AUC_Mean"));
	}

	//Top 10 features in rank to print graph of train\test\train after weighting to test:
	if (ranked.empty() && !ranked_norm.empty())
		ranked = ranked_norm;

	//Add fictive if small model
	if (ranked.empty() && propensity_features.data.size() <= 10) {
		ranked.resize(propensity_features.data.size());
		vector<string> all_feat_names;
		propensity_features.get_feature_names(all_feat_names);
		for (size_t i = 0; i < ranked.size(); ++i)
		{
			ranked[i].second = 1;
			ranked[i].first = all_feat_names[i];
		}
	}

	if (!ranked.empty() && args.group_shap_params.empty())
	{
		if (!args.additional_importance_to_rank.empty() && !reranked)
			load_additional_rank(args.additional_importance_to_rank, ranked);
		string folder_feat = args.output + path_sep() + "features_diff";
		boost::filesystem::create_directories(folder_feat);

		//Calibrate scores to probs
		unique_ptr<PostProcessor> pp_cal = unique_ptr<PostProcessor>(PostProcessor::make_processor("calibrator", args.calibration_init_str));
		pp_cal->Learn(propensity_features);
		pp_cal->Apply(propensity_features);

		//Print graph for top 10:
		string content_html_temp = "";
		if (!args.feature_html_template.empty()) {
			ifstream fr(args.feature_html_template);
			if (!fr.good())
				MTHROW_AND_ERR("Error can't open %s for reading\n", args.feature_html_template.c_str());
			string line;
			stringstream str_;
			while (getline(fr, line)) {
				str_ << line << "\n";
			}
			fr.close();
			content_html_temp = str_.str();
		}
		for (size_t i = 0; i < ranked.size() && i < 10; ++i)
			plot_graph(propensity_features, propensity_predictor.get(), args.calibration_init_str, ranked[i].first,
				folder_feat, content_html_temp, args.name_for_train, args.name_for_test);

	}

}

void store_strata_matrix(const string &file_path, const vector<string> &feature_names,
	const vector<string> &moments_names, const vector<vector<float>> &data) {
	if (data.empty()) {
		MWARN("WARN - store_strata_matrix - data is empty\n");
		return;
	}

	ofstream fw(file_path);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open %s for writing\n", file_path.c_str());
	//write header
	fw << "STRATA_MOMENT";
	for (size_t i = 0; i < feature_names.size(); ++i)
		fw << "\t" << feature_names[i];
	fw << "\n";
	//write data:
	int strata_moments = (int)data.front().size();
	for (int i = 0; i < strata_moments; ++i) {
		int strata_idx = i / (int)moments_names.size();
		int moment_idx = (i % (int)moments_names.size());

		fw << "STRATA_" << strata_idx << "_" << moments_names[moment_idx];
		for (size_t feat_index = 0; feat_index < data.size(); ++feat_index)
		{
			const vector<float> &feat_data = data[feat_index];
			float val = feat_data[i];
			fw << "\t" << val;
		}
		fw << "\n";

	}

	fw.close();
}

int get_index(const vector<string> &v, const string &search) {
	for (int i = 0; i < v.size(); ++i)
		if (v[i] == search)
			return i;
	MTHROW_AND_ERR("Error not found %s in array\n", search.c_str());
}

void load_strata_matrix(const string &file_path, vector<string> &read_feature_names,
	vector<string> &read_moments_names, int moment_size, vector<vector<float>> &data) {
	ifstream fr(file_path);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't open %s for reading\n", file_path.c_str());
	string header, line;
	getline(fr, header);
	//parse header:
	vector<string> header_tokens, tokens;
	boost::split(header_tokens, header, boost::is_any_of("\t"));
	read_feature_names.resize(header_tokens.size() - 1);
	for (size_t i = 1; i < header_tokens.size(); ++i)
		read_feature_names[i - 1] = header_tokens[i];

	data.resize(read_feature_names.size());
	unordered_set<string> seen_txt, seen_moment;
	int line_num = 1;
	while (getline(fr, line)) {
		++line_num;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != read_feature_names.size() + 1)
			MTHROW_AND_ERR("Error - format error in line %d:\n%s\n", line_num, line.c_str());
		string strata_moment_str = tokens[0];
		string part_num = strata_moment_str.substr(7);
		size_t pos = part_num.find_first_of('_');
		if (pos == string::npos)
			MTHROW_AND_ERR("Error bad format in start line token: %s\n", strata_moment_str.c_str());

		string moment_part = part_num.substr(pos + 1);
		if (seen_txt.find(strata_moment_str) == seen_txt.end()) {
			//parse and update read_moments_names: FORMAT: "STRATA_" << strata_idx << "_" << moments_names[moment_idx]

			if (seen_moment.find(moment_part) == seen_moment.end()) {
				read_moments_names.push_back(moment_part);
				seen_moment.insert(moment_part);
			}
			seen_txt.insert(strata_moment_str);
		}
		int strata_idx = med_stoi(part_num.substr(0, pos));
		int moment_idx = get_index(read_moments_names, moment_part); //find moment_part index in read_moments_names
		int final_idx = strata_idx * moment_size + moment_idx;
		//parse rest of line:
		for (size_t i = 1; i < tokens.size(); ++i)
		{
			vector<float> &feat_update = data[i - 1];
			float num = med_stof(tokens[i]);
			if (feat_update.size() <= final_idx)
				feat_update.resize(final_idx + 1);
			feat_update[final_idx] = num;
		}
	}

	fr.close();
	if (data.empty())
		MTHROW_AND_ERR("Error file %s is empty\n", file_path.c_str());
	MLOG("Read %s with (%zu, %zu) features\n", file_path.c_str(), data.size(), data[0].size());
}

void test_equal(const vector<string> &a, const vector<string> &b, const string &msg) {
	if (a.size() != b.size())
		MTHROW_AND_ERR("Error - unequal sizes [%zu, %zu] - %s\n", a.size(), b.size(), msg.c_str());
	for (size_t i = 0; i < a.size(); ++i)
		if (a[i] != b[i])
			MTHROW_AND_ERR("Error - found unequal element at %zu [%s != %s] - %s\n",
				i, a[i].c_str(), b[i].c_str(), msg.c_str());
}

string get_sig(featureSetStrata &strata_settings, int idx) {
	stringstream s;
	vector<string> tokens(strata_settings.nStratas());
	for (int i = (int)strata_settings.nStratas() - 1; i >= 0; --i)
	{
		string strata_nm = strata_settings.stratas[i].name;
		int bin_idx = idx / strata_settings.factors[i];

		//calc min,max range from bin_idx
		float min_rng = strata_settings.stratas[i].min + (bin_idx * strata_settings.stratas[i].resolution);
		float max_rng = strata_settings.stratas[i].min + ((bin_idx + 1) * strata_settings.stratas[i].resolution);;
		if (max_rng > strata_settings.stratas[i].max)
			max_rng = strata_settings.stratas[i].max;
		stringstream ss;
		ss << strata_nm << ":[";
		ss << min_rng << "," << max_rng;
		ss << "]";
		tokens[i] = ss.str();
		idx = idx % strata_settings.factors[i];
	}

	if (!tokens.empty())
		s << tokens[0];
	for (size_t i = 1; i < tokens.size(); ++i)
		s << "_" << tokens[i];

	return s.str();
}

bool is_similar(float s1, float s2, double similar_ratio = 0.05) {
	if (s1 == MED_MAT_MISSING_VALUE || s2 == MED_MAT_MISSING_VALUE) {
		if (!(s1 == MED_MAT_MISSING_VALUE && s2 == MED_MAT_MISSING_VALUE)) {
			//only one of them is null;

			return true;
		}
	}
	double diff = abs(s1 - s2);
	double diff_ratio = diff / (abs(s1) + abs(s2));

	return (diff_ratio <= similar_ratio);
}

void compare_stats(const vector<float> &A, const vector<float> &B, const string &feat_name,
	const vector<string> &moment_names, featureSetStrata &strata_settings, ofstream &fw, double similar_ratio = 0.05) {
	if (A.size() != B.size())
		MTHROW_AND_ERR("Error row matrix has no same row sizes [%zu, %zu]\n",
			A.size(), B.size());

	for (int i = 0; i < A.size(); ++i)
	{
		float a = A[i];
		float b = B[i];
		int moment_type_idx = i % moment_names.size();
		string moment_nm = moment_names[moment_type_idx];
		int strata_idx = i / (int)moment_names.size();
		string strata_name = get_sig(strata_settings, strata_idx);

		//compare number - use feat_name, strata_name, moment_nm to print:
		bool res = is_similar(a, b, similar_ratio);
		fw << feat_name << "\t" << strata_name << "\t" << moment_nm;
		float diff = abs(a - b);
		if ((a == MED_MAT_MISSING_VALUE || b == MED_MAT_MISSING_VALUE) &&
			(!(a == MED_MAT_MISSING_VALUE && b == MED_MAT_MISSING_VALUE))) {
			//only one of them is NULL:
			diff = -1;
		}
		fw << "\t" << a << "\t" << b << "\t" << diff << "\t";
		if (res)
			fw << "Good";
		else
			fw << "Bad";

		fw << "\n";
	}
}

void compare_stats(const vector<vector<float>> &A, const vector<vector<float>> &B,
	const vector<string> &feature_names, const vector<string> &moment_names, featureSetStrata &strata_settings, const string &output_file) {
	if (A.size() != B.size())
		MTHROW_AND_ERR("Error matrix has no same row sizes [%zu, %zu]\n",
			A.size(), B.size());
	if (A.size() != feature_names.size())
		MTHROW_AND_ERR("Error feature_names(%zu) no same size %zu\n",
			feature_names.size(), A.size());

	ofstream fw(output_file);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open %s for writing\n", output_file.c_str());
	//Go over feature-feature:
	for (size_t i = 0; i < A.size(); ++i)
		compare_stats(A[i], B[i], feature_names[i], moment_names, strata_settings, fw);

	fw.close();
	MLOG("Wrote Compare file %s\n", output_file.c_str());
}

void compare_model_by_stats(const ProgramArgs &args) {
	if (!args.rep_trained.empty() && !args.samples_train.empty())
		return;
	MedModel model;
	model.read_from_file(args.model_path);

	featureSetStrata strata_settings;
	vector<string> strata_tokens;
	boost::split(strata_tokens, args.strata_settings, boost::is_any_of(":"));
	for (string& stratum : strata_tokens) {
		vector<string> fields;
		boost::split(fields, stratum, boost::is_any_of(","));
		if (fields.size() != 4)
			MLOG("Cannot initialize strata from \'%s\'. Ignoring\n", stratum.c_str());
		else
			strata_settings.stratas.push_back(featureStrata(fields[0], stof(fields[3]), stof(fields[1]), stof(fields[2])));
	}
	strata_settings.getFactors();

	int min_size = 5;
	//moments: Mean,STD, Prctile-10,30,50,70,90
	vector<string> moments_names = { "Mean", "Std" };
	int additional_moments = (int)moments_names.size(); //the additional moments are: Mean,Std
	vector<double> prctile_moments = { 0.1, 0.3, 0.5, 0.7, 0.9 };
	for (size_t i = 0; i < prctile_moments.size(); ++i)
		moments_names.push_back("Prctile_" + to_string(prctile_moments[i]));
	int moments_count = (int)moments_names.size(); // hte additional 2 are mean and std

	//generate strata feats for test
	//* generate strata feats data
	MedFeatures strata_feats;
	MedSamples test_rep_samples;
	test_rep_samples.read_from_file(args.samples_test);
	MedModel strata_feat_creation_mdl;
	if (!args.strata_json_model.empty())
		strata_feat_creation_mdl.init_from_json_file(args.strata_json_model);
	else {
		MLOG("No json model - adding Age,Gender features\n");
		strata_feat_creation_mdl.add_age();
		strata_feat_creation_mdl.add_gender();
	}
	medial::medmodel::apply(strata_feat_creation_mdl, test_rep_samples, args.rep_test, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	strata_feats = move(strata_feat_creation_mdl.features);
	vector<const vector<float> *> strataData(strata_settings.nStratas());
	vector<string> strata_feat_names;
	strata_feats.get_feature_names(strata_feat_names);
	for (int j = 0; j < strata_settings.nStratas(); j++) {
		string resolved_strata_name = strata_feat_names[find_in_feature_names(strata_feat_names, strata_settings.stratas[j].name)];
		strataData[j] = &strata_feats.data.at(resolved_strata_name);
	}
	MLOG("INFO:: compare_model_by_stats - has %zu stratas with %d bins\n",
		strata_settings.nStratas(), strata_settings.nValues());

	//* generate those values for test:
	MedFeatures test_feats;
	int nsamlpes = test_rep_samples.nSamples();
	if (args.sub_sample_test > 0 && args.sub_sample_test < nsamlpes)
		medial::process::down_sample(test_rep_samples, float(args.sub_sample_test) / nsamlpes);
	medial::medmodel::apply(model, test_rep_samples, args.rep_test, MedModelStage::MED_MDL_END);
	test_feats = move(model.features);

	int feature_sz = (int)test_feats.data.size();
	vector<vector<float>> test_strata_vals(feature_sz); //first index is feature, secon index is strata*moment_type
	for (size_t i = 0; i < test_strata_vals.size(); ++i)
		test_strata_vals[i].resize(strata_settings.nValues() * moments_count);
	vector<string> feat_names;
	test_feats.get_feature_names(feat_names);

	vector<vector<vector<float>>> test_strata_raw(feat_names.size()); //feature, strata => vector of values
	for (size_t i = 0; i < test_strata_raw.size(); ++i)
		test_strata_raw[i].resize(strata_settings.nValues());
	for (size_t i = 0; i < feat_names.size(); ++i)
	{
		const vector<float> &feat_vals = test_feats.data.at(feat_names[i]);
		vector<vector<float>> &feat_st_raw_vals = test_strata_raw[i];
		for (size_t j = 0; j < feat_vals.size(); ++j)
		{
			int st_idx = strata_settings.getIndex(MED_MAT_MISSING_VALUE, strataData, (int)j);
			vector<float> &raw_vals = feat_st_raw_vals[st_idx];
			raw_vals.push_back(feat_vals[j]); //stores  feature value for that strata
		}

	}

	//* calc moments from test_strata_raw into test_strata_vals
	for (int i = 0; i < test_strata_raw.size(); ++i)
	{
		vector<float> &feature_stats = test_strata_vals[i];

		for (int j = 0; j < test_strata_raw[i].size(); ++j)
		{
			const vector<float> &feature_strata_r = test_strata_raw[i][j];
			int target_idx_start = j * moments_count; //now add all moments from here:
			if (feature_strata_r.size() <= min_size) {
				for (size_t k = 0; k < moments_count; ++k)
					feature_stats[target_idx_start + k] = MED_MAT_MISSING_VALUE;
				continue;
			}
			float mean, std;
			vector<float> prctile_vals;
			medial::stats::get_mean_and_std_without_cleaning(feature_strata_r, mean, std);
			medial::process::prctils(feature_strata_r, prctile_moments, prctile_vals);
			feature_stats[target_idx_start + 0] = mean;
			feature_stats[target_idx_start + 1] = std;
			for (size_t k = 0; k < prctile_vals.size(); ++k)
				feature_stats[target_idx_start + additional_moments + k] = prctile_vals[k];
		}
	}

	//* store in output file
	store_strata_matrix(args.output + path_sep() + "test_stats.strata.tsv", feat_names, moments_names, test_strata_vals);
	MLOG("Wrote Stats file %s\n", (args.output + path_sep() + "test_stats.strata.tsv").c_str());

	//load from train if has into train_strata_vals
	vector<vector<float>> train_strata_vals;
	if (!args.strata_train_features_moments.empty()) {
		vector<string> read_feat_names, read_moments;
		load_strata_matrix(args.strata_train_features_moments, read_feat_names, read_moments,
			(int)moments_names.size(), train_strata_vals);
		//check it's OK:
		test_equal(read_feat_names, feat_names, "model feature names (read VS created)");
		test_equal(read_moments, moments_names, "moments names (read VS created)");
	}

	//compare if train was loaded
	if (!train_strata_vals.empty())
		compare_stats(test_strata_vals, train_strata_vals, feat_names, moments_names, strata_settings,
			args.output + path_sep() + "compare_stats.tsv");
}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;

	compare_model_by_repositories(args);
	compare_model_by_stats(args);

	return 0;
}