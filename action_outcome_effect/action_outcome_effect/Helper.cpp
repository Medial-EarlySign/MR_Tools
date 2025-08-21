#include "Helper.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedProcessTools/MedProcessTools/Calibration.h"
#include "MedMat/MedMat/MedMatConstants.h"
#include "Logger/Logger/Logger.h"
#include <algorithm>
#include <cmath>
#include <omp.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

void test_independece(const vector<string> &groups_x, const vector<float> &groups_y,
	const vector<float> &labels, const vector<string> &groups_x_sorted,
	float &tot_chi, int &tot_dof, bool print, bool print_full,
	int smooth_chi, float at_least_diff) {
	unordered_map<string, map<float, vector<int>>> chi_stats;
	unordered_map<string, pair<int, int>> group_x_counts;
	for (size_t i = 0; i < groups_x.size(); ++i) { //for each our "matching" risk group
		float pos_group_y = groups_y[i];
		//Or fetch right Y value for grouping :)
		if (chi_stats[groups_x[i]].find(pos_group_y) == chi_stats[groups_x[i]].end())
			chi_stats[groups_x[i]][pos_group_y].resize(4);
		++chi_stats[groups_x[i]][pos_group_y][labels[i] > 0]; //update case or control count
		if (labels[i] > 0)
			++group_x_counts[groups_x[i]].second;
		else
			++group_x_counts[groups_x[i]].first;
	}
	map<string, float> all_chi_square_results;
	tot_chi = 0;
	tot_dof = 0;
	for (auto it = chi_stats.begin(); it != chi_stats.end(); ++it) {
		for (auto jt = it->second.begin(); jt != it->second.end(); ++jt)
		{
			chi_stats[it->first][jt->first][2 + 0] = group_x_counts[it->first].first;
			chi_stats[it->first][jt->first][2 + 1] = group_x_counts[it->first].second;
		}
		float chi_res = (float)medial::contingency_tables::calc_chi_square_dist(chi_stats[it->first], smooth_chi);
		all_chi_square_results[it->first] = chi_res;
		tot_chi += chi_res;
		tot_dof += (int)it->second.size() - 1;
	}
	//print all chi results:
	double tot_prob = medial::contingency_tables::chisqr(tot_dof, tot_chi);
	if (print) {
		MLOG("total chi_square=%2.3f, total_DOF=%d, prob=%2.3f\n",
			tot_chi, tot_dof, tot_prob);
		for (const string &grp_key : groups_x_sorted) {
			int dof = (int)chi_stats[grp_key].size() - 1;
			double prob = medial::contingency_tables::chisqr(dof, all_chi_square_results[grp_key]);
			if (dof > 0)
				MLOG("Reference Group: %s\tchi-square=%2.3f\tDOF=%d\tchi-prob=%2.3f\n",
					grp_key.c_str(), all_chi_square_results[grp_key], dof, prob);
			if (print_full && dof > 0) {
				for (auto ii = chi_stats[grp_key].begin(); ii != chi_stats[grp_key].end(); ++ii)
					MLOG("Val=%f\t%d\t%d\t%2.3f\n", ii->first, ii->second[0], ii->second[1],
						100.0*ii->second[1] / double(ii->second[1] + ii->second[0]));
			}
		}
	}
}

void createProbabiltyBins(const MedFeatures &feats, BinSettings probabilty_bin_settings
	, const map<string, BinSettings> &features_bin_settings, vector<float> &score_probabilty_bins) {
	vector<float> y(feats.samples.size());
	vector<int> empty_in;
	for (size_t i = 0; i < feats.samples.size(); ++i)
		y[i] = feats.samples[i].outcome;
	score_probabilty_bins.resize(y.size()); //starts that all in same cluster value - 0
											//vector<float> uniq_bin_values = { 0 };
	vector<vector<int>> bin_prob_values_indexes(1);
	bin_prob_values_indexes[0].resize(y.size());
	for (size_t i = 0; i < bin_prob_values_indexes[0].size(); ++i)
		bin_prob_values_indexes[0][i] = (int)i;

	for (auto it = feats.data.begin(); it != feats.data.end(); ++it)
	{
		if (features_bin_settings.find(it->first) == features_bin_settings.end())
			MTHROW_AND_ERR("Feature \"%s\" has no bin settings\n", it->first.c_str());
		const BinSettings &setting = features_bin_settings.at(it->first);
		//iterate on all current bins:

#pragma omp parallel for
		for (int i = 0; i < bin_prob_values_indexes.size(); ++i)
		{
			vector<float> feature(bin_prob_values_indexes[i].size());
			for (size_t j = 0; j < feature.size(); ++j)
				feature[j] = it->second[bin_prob_values_indexes[i][j]];
			vector<float> sel_y;

			try {
				medial::process::split_feature_to_bins(setting, feature,
					bin_prob_values_indexes[i], y);
			}
			catch (exception &exceptio) {
				MERR("Error %s in signal \"%s\"\n",
					exceptio.what(), it->first.c_str());
				throw;
			}

			//calc probabilty for each bin
			unordered_map<float, pair<double, int>> bin_prob_map;
			for (size_t k = 0; k < feature.size(); ++k)
			{
				bin_prob_map[feature[k]].first += y[bin_prob_values_indexes[i][k]]; //sum
				++bin_prob_map[feature[k]].second; //counters
			}
			for (auto jt = bin_prob_map.begin(); jt != bin_prob_map.end(); ++jt)
				bin_prob_map[jt->first].first = jt->second.first / jt->second.second; //now it's prob

																					  //flatten to new bins
#pragma omp critical
			for (size_t k = 0; k < bin_prob_values_indexes[i].size(); ++k)
				score_probabilty_bins[bin_prob_values_indexes[i][k]] = (float)
				bin_prob_map[feature[k]].first; //map to prob of this bin feature value
		}

		//merge into new bins - split bins again on score_probabilty_bins
		//need to update: score_probabilty_bins - done in upper loop, now merged and flattend again
		medial::process::split_feature_to_bins(probabilty_bin_settings, score_probabilty_bins,
			empty_in, y);

		//need to update bin_prob_values_indexes
		unordered_map<float, vector<int>> prob_val_to_ind;
		for (size_t k = 0; k < score_probabilty_bins.size(); ++k)
			prob_val_to_ind[score_probabilty_bins[k]].push_back((int)k);
		bin_prob_values_indexes.resize(prob_val_to_ind.size()); //not erasing ols values
		int index_i = 0;
		for (auto jt = prob_val_to_ind.begin(); jt != prob_val_to_ind.end(); ++jt)
		{
			bin_prob_values_indexes[index_i] = jt->second; //rewrite indexes for value
			++index_i;
		}
		MLOG("Done Feature \"%s\"\n", it->first.c_str());
	}

}

template<class T> string get_name(const map<string, T> &mapper, const string &col_name) {
	string all_options = "";
	for (auto i = mapper.begin(); i != mapper.end(); ++i) {
		if (i->first.find(col_name) != string::npos) //finds exact name
			return i->first;
		all_options += i->first + "\n";
	}
	MERR("All Options:\n%s\n", all_options.c_str());
	MTHROW_AND_ERR("Not found \"%s\" in above options\n", col_name.c_str());
}
template string get_name<vector<float>>(const map<string, vector<float>> &mapper, const string &col_name);

void read_strings(const string &file_path, vector<string> &groups) {
	ifstream fr(file_path);
	string line;
	while (getline(fr, line)) {
		boost::trim(line);
		groups.push_back(line);
	}
	fr.close();
	MLOG("Done reading %d lines from [%s]\n", (int)groups.size(), file_path.c_str());
}

void read_confounders(const string &file_path, unordered_set<string> &confounders) {
	ifstream fr(file_path);
	string line;
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		string &confounder_feature_search_name = line;
		confounders.insert(confounder_feature_search_name);
	}
	fr.close();
	MLOG("Done reading %d Confounders in [%s]\n", (int)confounders.size(), file_path.c_str());
}

double loss_target_AUC(const vector<float> &preds,
	const vector<float> &y, vector<float> &preds_validation, void *params) {
	loss_confounders_params *loss_params = (loss_confounders_params *)params;
	MedFeatures *all_matrix = loss_params->all_matrix;

	MedPredictor *validation_predictor = MedPredictor::make_predictor(loss_params->validator_type,
		loss_params->validator_init);
	medial::models::get_pids_cv(validation_predictor, *all_matrix, loss_params->validation_nFolds,
		*loss_params->random_generator, preds_validation);
	delete validation_predictor;

	//try learn CV on weighted MedFeatures
	double res = medial::performance::auc_q(preds_validation, y, &all_matrix->weights); //try to minimize over 0.5
	return res;
}

double loss_target_confounders_AUC(const vector<float> &preds,
	const vector<float> &y, void *params) {

	vector<float> preds_validation;
	return loss_target_AUC(preds, y, preds_validation, params);
}



void write_model_selection(const vector<pair<string, unordered_map<string, float>>> &measures,
	const string &save_path) {
	if (measures.empty())
		return;
	ofstream fw(save_path);
	if (!fw.good())
		MTHROW_AND_ERR("IOError: can't write model_selection file\n");
	fw << "model_name";
	for (size_t i = 0; i < measures.size(); ++i)
		fw << "\t" << measures[i].first;
	fw << endl;
	vector<string> model_names;
	model_names.reserve(measures.front().second.size());
	for (auto it = measures.front().second.begin(); it != measures.front().second.end(); ++it)
		model_names.push_back(it->first);

	//print in sorted way by desc model_loss values and than by model_loss_train asc values:
	vector<pair<string, vector<double>>> sorted(model_names.size()); //model name, values to sort
	for (size_t i = 0; i < sorted.size(); ++i) {
		sorted[i].first = model_names[i];
		sorted[i].second.resize(measures.size());
		for (size_t j = 0; j < measures.size(); ++j)
			sorted[i].second[j] = measures[j].second.at(model_names[i]);
	}
	sort(sorted.begin(), sorted.end(), [](pair<string, vector<double>> a, pair<string, vector<double>> b) {
		int pos = 0;
		while (pos < a.second.size() &&
			a.second[pos] == b.second[pos])
			++pos;
		if (pos >= a.second.size())
			return false;
		return b.second[pos] > a.second[pos];
	});
	for (size_t i = 0; i < sorted.size(); ++i)
	{
		fw << sorted[i].first;
		for (size_t m = 0; m < measures.size(); ++m)
			fw << "\t" << sorted[i].second[m];
		fw << "\n";
	}
	fw.close();
}

float get_weight(float prob, float outcome, float min_prob) {
	float res = 0;
	if (prob >= min_prob && prob <= 1 - min_prob) {
		if (outcome > 0)
			res = float(1.0 / prob);
		else
			res = float(1.0 / (1 - prob));
	}
	return res;
}

string runOptimizerModel(MedFeatures &dataMat, const vector<MedPredictor *> &all_models_config,
	int nFolds, mt19937 &random_generator, const string &calibrator_init, float min_prob,
	double(*loss_func)(const vector<float> &, const vector<float> &, void *), void *params,
	vector<pair<string, unordered_map<string, float>>> &measures) {

	string bestParams = "";
	if (all_models_config.size() == 1)
	{
		bestParams = medial::models::getParamsInfraModel(all_models_config[0]);
		if (bestParams.find(":") != string::npos)
			bestParams = bestParams.substr(bestParams.find(":") + 1);
		return bestParams;
	}

	vector<float> yData(dataMat.samples.size());
	for (size_t i = 0; i < dataMat.samples.size(); ++i)
		yData[i] = dataMat.samples[i].outcome;
	//vector<float> empty_w(dataMat.samples.size(), 1);

	if (loss_func == NULL)
		loss_func = [](const vector<float> &preds, const vector<float> &y, void *p) {
		return (double)-medial::performance::auc_q(preds, y);
	};

	float minVal = (float)INT32_MAX;
	int tot_done = 0;
	time_t start = time(NULL);
	time_t curr = time(NULL);
	int duration;
	for (size_t k = 0; k < dataMat.samples.size(); ++k)
		dataMat.samples[k].prediction.resize(1);

	measures.resize(2); //has 2 measures
	measures[0].first = "SECOND_WEIGHTED_AUC"; //need to be lower
	measures[1].first = "CV_AUC"; //need to be lower - more samples\stable

	for (int i = 0; i < all_models_config.size(); ++i) {
		vector<float> empty_w;
		vector<float> preds;
		dataMat.weights.clear();
		medial::models::get_pids_cv(all_models_config[i], dataMat, nFolds, random_generator, preds);
		for (size_t k = 0; k < preds.size(); ++k)
			dataMat.samples[k].prediction[0] = preds[k];
		Calibrator cl;
		cl.init_from_string(calibrator_init);
		cl.Learn(dataMat.samples);
		cl.Apply(dataMat.samples);
		//set weights:
		dataMat.weights.resize(dataMat.samples.size(), 1);
		for (size_t k = 0; k < dataMat.samples.size(); ++k)
			dataMat.weights[k] = get_weight(dataMat.samples[k].prediction[0], dataMat.samples[k].outcome, min_prob);

		//delete (MedPredictor *)model;
		float res = (float)loss_func(preds, yData, params);

		float auc_cv = medial::performance::auc_q(preds, yData);
		string model_name = medial::models::getParamsInfraModel(all_models_config[i]);
		MLOG("%s, auc_cv=%2.3f, loss=%2.3f\n", model_name.c_str(), auc_cv, res);
#pragma omp critical
		{
			measures[0].second[model_name] = res;
			measures[1].second[model_name] = auc_cv;
		}
#pragma omp critical
		if (res < minVal || bestParams.empty()) {
			minVal = res;
			bestParams = model_name;
		}
#pragma omp atomic 
		++tot_done;
		duration = (int)difftime(time(NULL), curr);
		if (duration >= 60) {
			int time_from_start = (int)difftime(time(NULL), start);
			double estimate = ((double)(all_models_config.size() - tot_done) / tot_done) * time_from_start / 60.0;
			MLOG("Done %d out of %d(%2.2f%%). minutes_elapsed=%2.1f, estimate_minutes=%2.1f\n",
				tot_done, (int)all_models_config.size(),
				100.0* double(tot_done) / all_models_config.size(),
				time_from_start / 60.0, estimate);
			curr = time(NULL);
		}
	}

	MLOG("Done! best score = %2.4f with \"%s\"\n", minVal, bestParams.c_str());
	if (bestParams.find(":") != string::npos)
		bestParams = bestParams.substr(bestParams.find(":") + 1);
	return bestParams;
}

void read_ms_config(const string &file_path, const string &base_model,
	vector<MedPredictor *> &all_configs) {
	ifstream fr(file_path);
	if (!fr.good())
		MTHROW_AND_ERR("IOError: can't read model selection file\n");
	string line;
	vector<string> all_init = { "" };
	all_configs.clear();
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("="));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Bad Format in line \"%s\"\n", line.c_str());
		string param_name = boost::trim_copy(tokens[0]);
		string params_options = boost::trim_copy(tokens[1]);
		vector<string> opts;
		boost::split(opts, params_options, boost::is_any_of(","));
		int base_sz = (int)all_init.size();
		all_init.resize(base_sz * opts.size()); //cartezian multiply of options. copy the current options:
		for (size_t i = 1; i < opts.size(); ++i) //the first is already OK:
			for (size_t j = 0; j < base_sz; ++j)
				all_init[i*base_sz + j] = all_init[j];
		for (size_t i = 0; i < opts.size(); ++i) //the first is already OK:
			for (size_t j = 0; j < base_sz; ++j)
				all_init[i*base_sz + j] += param_name + "=" + opts[i] + ";";
	}
	fr.close();
	//I have string line to init all models:
	MLOG("I have %d models in model selection.\n", (int)all_init.size());

	int curr_lev = global_logger.levels[LOG_MEDALGO];
	global_logger.levels[LOG_MEDALGO] = MAX_LOG_LEVEL;
	all_configs.resize(all_init.size());
	for (size_t i = 0; i < all_init.size(); ++i)
		all_configs[i] = MedPredictor::make_predictor(base_model, all_init[i]);
	global_logger.levels[LOG_MEDALGO] = curr_lev;
}

void gether_stats(const vector<unordered_map<string, float>> &raw
	, map<string, float> &summerized) {
	vector<double> prc_vals = { 0.05, 0.95 };
	int n_clean;
	for (auto it = raw[0].begin(); it != raw[0].end(); ++it)
	{
		vector<float> vals(raw.size());
		for (size_t i = 0; i < raw.size(); ++i)
			vals[i] = raw[i].at(it->first);
		float mean_value = medial::stats::mean(vals, (float)MED_MAT_MISSING_VALUE, n_clean);
		float std_value = medial::stats::std(vals, mean_value, (float)MED_MAT_MISSING_VALUE, n_clean);
		vector<float> prs;
		medial::process::prctils(vals, prc_vals, prs);

		summerized[it->first + "_Mean"] = mean_value;
		summerized[it->first + "_Std"] = std_value;
		summerized[it->first + "_CI.Lower.95"] = prs[0];
		summerized[it->first + "_CI.Upper.95"] = prs[1];
	}
}

template<class T> void commit_selection(vector<T> &vec, const vector<int> &idx) {
	vector<T> filt(idx.size());
	for (size_t i = 0; i < idx.size(); ++i)
		filt[i] = vec[idx[i]];
	vec.swap(filt);
}
template void commit_selection<string>(vector<string> &vec, const vector<int> &idx);

inline double distance_metric(const vector<float> &a, const vector<float> &b) {
	double res = 0;
	for (size_t i = 0; i < a.size(); ++i)
		res += (a[i] - b[i])*(a[i] - b[i]);
	res = sqrt(res);
	return res;
}

// Match according to similarity matrix (it can also have one score - propensity to match by it)
void match_samples_pairwise(vector<MedSample>& samples, vector<float>& matchedValue,
	const vector<const vector<float> *> &metric_data, float caliper, vector<int>& matchedSamples, bool quiet) {
	matchedSamples.clear();
	vector<pair<int, const vector<float> *>> propScores[2];
	for (int i = 0; i < samples.size(); i++) {
		int treatment = (int)matchedValue[i];
		propScores[treatment].push_back({ i, metric_data[i] });
	}

	float ratioTreated = float(1.0 * propScores[1].size() / (propScores[1].size() + propScores[0].size()));
	if (!quiet)
		fprintf(stderr, "Before matching : Ratio of treated = %.2f%% (%d vs %d)\n", ratioTreated*100.0, (int)propScores[1].size(), (int)propScores[0].size());

	//euclidain metric:
	int sample_cnt = 1;
	double totVar = 0;
	random_device rd;
	mt19937 gen(rd());
	vector<float> ref_scores(metric_data[0]->size(), 0);
	bool use_ref_score = false;
	vector<double> var_type(2);
	for (int type = 0; type < 2; ++type) {
		double sum = 0, sum2 = 0;
		uniform_int_distribution<> smp_gen(0, (int)propScores[type].size() - 1);
		for (int i = 0; i < propScores[type].size(); i++) {
			//sample random x distances
			float dist;
			if (use_ref_score) {
				dist = (float)distance_metric(*propScores[type][i].second, ref_scores);
				sum += dist;
				sum2 += dist * dist;
			}
			else {
				vector<bool> seen(propScores[type].size());
				for (int j = 0; j < sample_cnt && j < propScores[type].size() - 1; ++j)
				{
					seen[i] = true;
					int p = smp_gen(gen);
					while (seen[p])
						p = smp_gen(gen);
					seen[p] = true;
					dist = (float)distance_metric(*propScores[type][i].second, *propScores[type][p].second);
					sum += dist;
					sum2 += dist * dist;
				}
			}
		}
		int num = (int)propScores[type].size();
		if (!use_ref_score)
			num *= sample_cnt;
		double mean = sum / num;
		double var = (sum2 - mean * sum) / (num - 1);
		if (!quiet)
			fprintf(stderr, "Type %d : N = %d Mean = %f Var = %f\n", type, num, mean, var);
		totVar += var;
		var_type[type] = var;
	}

	double sdv = sqrt(totVar / 2);
	double maxDiff = sdv * caliper;

	// match
	int type = 0; //choose less common
	if (propScores[1].size() < propScores[0].size())
		type = 1;
	maxDiff = sqrt(var_type[type]) * caliper;
	if (!quiet)
		MLOG("matching to type %d\n", type);
	int nSamples = (int)propScores[type].size();
	MedProgress progress("", nSamples, 10, 1);
#pragma omp parallel for
	for (int l = 0; l < nSamples; ++l)
	{
		const vector<float> *target_candidate = propScores[type][l].second;

		int matchedIndx = 0;
		double minDiff = distance_metric(*propScores[1 - type][0].second, *target_candidate);
		for (int i = 1; i < propScores[1 - type].size(); i++) {
			double diff = distance_metric(*propScores[1 - type][i].second, *target_candidate);
			if (diff < minDiff) {
				matchedIndx = i;
				minDiff = diff;
			}
		}

		if (minDiff < maxDiff) {
#pragma omp critical
			{
				matchedSamples.push_back(propScores[type][l].first);
				matchedSamples.push_back(propScores[1 - type][matchedIndx].first);
			}
		}

		//#pragma omp critical
		//propScores[type].pop_back();
		if (minDiff < maxDiff) {
#pragma omp critical
			{
				//earasing "matchedIndx" => save last in matched_index and remove last
				propScores[1 - type][matchedIndx] = propScores[1 - type].back();
				propScores[1 - type].pop_back();
			}
		}

		if (!quiet)
			progress.update();
	}

	sort(matchedSamples.begin(), matchedSamples.end());
	if (!quiet)
		fprintf(stderr, "After matching , left with %d samples\n", (int)matchedSamples.size());
}

void print_stats(const MedFeatures &feats, const vector<string> &action,
	const unordered_map<string, int> &action_to_val) {
	vector<vector<int>> stats(2); //outcome, than action
	stats[0].resize(2); stats[1].resize(2);
	for (size_t i = 0; i < feats.samples.size(); ++i)
		++stats[feats.samples[i].outcome > 0][action_to_val.at(action[i])];
	int yes_outcome = stats[1][0] + stats[1][1];
	int no_outcome = stats[0][0] + stats[0][1];
	int yes_action = stats[0][1] + stats[1][1];
	int no_action = stats[0][0] + stats[1][0];

	MLOG("no_outcome_no_action: %d, no_outcome_yes_action: %d"
		", yes_outcome_no_action:%d, yes_outcome_yes_action:%d\n",
		stats[0][0], stats[0][1], stats[1][0], stats[1][1]);

	MLOG("outcome_prior=%2.2f%%(%d / %d). action_prior=%2.2f%%(%d / %d).\n",
		100.0* yes_outcome / double(yes_outcome + no_outcome), yes_outcome,
		yes_outcome + no_outcome, 100.0*yes_action / double(yes_action + no_action),
		yes_action, yes_action + no_action);

	MLOG("no_action_prob_outcome=%2.3f%%, yes_action_prob_outcome=%2.3f%%\n",
		(100.0* stats[1][0]) / no_action, (100.0* stats[1][1]) / yes_action);

	medial::print::print_by_year(feats.samples, 1);
}

class conv_mat {
public:
	vector<vector<int>> s;
	conv_mat() {
		s.resize(2);
		for (size_t i = 0; i < s.size(); ++i)
			s[i].resize(2);
	}

	vector<int>& operator[](std::size_t idx) { return s[idx]; }
	const vector<int>& operator[](std::size_t idx) const { return s[idx]; }
};

void print_age_stats(const MedFeatures &feats, const vector<string> &action,
	const unordered_map<string, int> &action_to_val, int age_bin) {
	vector<conv_mat> stats; //Age_Bin, outcome, action
	if (feats.data.find("Age") == feats.data.end() || feats.data.at("Age").empty()) {
		MWARN("Warning: matrix doesn't have Age Feature - skip printing by age");
		return;
	}

	int min_age = feats.data.at("Age")[0];
	int max_age = min_age;
	for (size_t i = 0; i < feats.samples.size(); ++i) {
		if (feats.data.at("Age")[i] > max_age)
			max_age = feats.data.at("Age")[i];
		if (feats.data.at("Age")[i] < min_age)
			min_age = feats.data.at("Age")[i];
	}
	if (min_age == max_age) {
		MLOG("All Samples are from the same age %d\n", min_age);
		return;
	}
	if (max_age > 120) {
		int before = max_age;
		max_age = 120;
		MLOG("max_age was %d, truncate to %d\n", before, max_age);
	}
	stats.resize((max_age - min_age) / age_bin + 1);
	for (size_t i = 0; i < feats.samples.size(); ++i) {
		int age = feats.data.at("Age")[i];
		if (age > max_age)
			age = max_age;
		int age_idx = (age - min_age) / age_bin;
		++stats[age_idx][feats.samples[i].outcome > 0][action_to_val.at(action[i])];
	}


	MLOG(" no_outcome_no_action  |  no_outcome_yes_action | yes_outcome_no_action  | yes_outcome_yes_action | "
		"outcome_prior | action_prior | no_action_prob_outcome | yes_action_prob_outcome\n");
	for (int age_idx = 0; age_idx < stats.size(); ++age_idx)
	{
		int from_age = age_idx * age_bin;
		int to_age = (age_idx + 1) *age_bin - 1;

		int yes_outcome = stats[age_idx][1][0] + stats[age_idx][1][1];
		int no_outcome = stats[age_idx][0][0] + stats[age_idx][0][1];
		int yes_action = stats[age_idx][0][1] + stats[age_idx][1][1];
		int no_action = stats[age_idx][0][0] + stats[age_idx][1][0];
		if (no_outcome == 0 || yes_outcome == 0 || no_action == 0 || yes_action == 0) {
			MLOG("Age:%03d-%03d: Skipped - not enought samples\n", from_age, to_age);
			continue;
		}

		MLOG("Age:%03d-%03d: %8s %8s %8s %8s %8s(%8s / %8s) %8s(%8s / %8s) %8s %8s\n", from_age, to_age,
			to_string(stats[age_idx][0][0]).c_str(), to_string(stats[age_idx][0][1]).c_str()
			, to_string(stats[age_idx][1][0]).c_str(), to_string(stats[age_idx][1][1]).c_str(),
			medial::print::print_obj(100.0* yes_outcome / double(yes_outcome + no_outcome), "%2.4f%%").c_str(), to_string(yes_outcome).c_str(),
			to_string(yes_outcome + no_outcome).c_str(), medial::print::print_obj(100.0*yes_action / double(yes_action + no_action), "%2.4f%%").c_str(),
			to_string(yes_action).c_str(), to_string(yes_action + no_action).c_str(),
			medial::print::print_obj((100.0* stats[age_idx][1][0]) / no_action, "%2.4f%%").c_str(),
			medial::print::print_obj((100.0* stats[age_idx][1][1]) / yes_action, "%2.4f%%").c_str());
	}
}

void read_attr_from_samples(const string &attr, const vector<MedSample> &samples, vector<float> &vals,
	float missing_val) {
	int has_miss = 0, found = 0;
	vals.resize(samples.size(), missing_val); //give 1 weights to all
	for (size_t i = 0; i < samples.size(); ++i) {
		if (samples[i].attributes.find(attr) == samples[i].attributes.end())
			++has_miss;
		else {
			vals[i] = samples[i].attributes.at(attr);
			++found;
		}
	}
	if (has_miss > 0 && found > 0)
		MWARN("Warning read_attr_from_samples: has attr::%s for some of the samples (%d / %d)%2.2f%%\n",
			attr.c_str(), found, (int)samples.size(), ((100.0*found) / (float)samples.size()));
	else if (found)
		MLOG("Read attr::%s from samples\n", attr.c_str());
}

void read_attr_from_samples(const string &attr, const vector<MedSample> &samples, vector<string> &vals,
	const string &missing_val) {
	int has_miss = 0, found = 0;
	vals.resize(samples.size(), missing_val); //give 1 weights to all
	for (size_t i = 0; i < samples.size(); ++i) {
		if (samples[i].str_attributes.find(attr) == samples[i].str_attributes.end())
			++has_miss;
		else {
			vals[i] = samples[i].str_attributes.at(attr);
			++found;
		}
	}
	if (has_miss > 0 && found > 0)
		MWARN("Warning read_attr_from_samples: has attr::%s for some of the samples (%d / %d)%2.2f%%\n",
			attr.c_str(), found, (int)samples.size(), ((100.0*found) / (float)samples.size()));
	else if (found)
		MLOG("Read attr::%s from samples\n", attr.c_str());
}