#include "Cmd_Args.h"
#include <algorithm>
#include "MedStat/MedStat/MedBootstrap.h"
#include <omp.h>
#include <random>

//Assume samples has calibrated predictions (Uses only the prediction)
void get_roc_from_calibrated_preds(MedSamples &samples, map<string, float> &res) {
	//Let's calc distribution (key is score, value is frequency in fraction):
	map<float, double> score_dist;
	vector<float> sorted_preds;
	double tot_samples = 0;
	double tot_cases = 0;
	for (auto& idSample : samples.idSamples)
		for (auto& sample : idSample.samples) {
			if (sample.prediction.empty())
				MTHROW_AND_ERR("Error no predictions in samples\n");
			if (score_dist.find(sample.prediction[0]) == score_dist.end()) {
				sorted_preds.push_back(sample.prediction[0]);
				score_dist[sample.prediction[0]] = 0;
			}
			++score_dist[sample.prediction[0]];
			++tot_samples;
			tot_cases += sample.prediction[0];
		}
	if (tot_samples == 0)
		MTHROW_AND_ERR("Error samples is empty\n");
	for (auto &it : score_dist)
		it.second /= tot_samples;
	sort(sorted_preds.begin(), sorted_preds.end());

	MLOG("There are %zu score bins for %d predictions\n", sorted_preds.size(), (int)tot_samples);
	//MedProgress progress("AUC_CALC", (sorted_preds.size()*sorted_preds.size() + sorted_preds.size()) / 2, 30, 1000);
	MedProgress progress("Performance_From_Calibration", 1, 30, 1);
	progress.alway_print_total = true;
	//double auc_sum = 0, tot_weight = 0;
	int NTH = omp_get_max_threads();
	vector<double> auc_sum_t(NTH);
	vector<double> tot_weight_t(NTH);
#pragma omp parallel for
	for (int i = 0; i < sorted_preds.size(); ++i) {
		int th_num = omp_get_thread_num();

		double freq_i = score_dist.at(sorted_preds[i]);
		double pred_i = sorted_preds[i];
		for (int j = i; j < sorted_preds.size(); ++j) {
			double &tot_weight = tot_weight_t[th_num];
			double &auc_sum = auc_sum_t[th_num];

			double freq_j = score_dist.at(sorted_preds[j]);
			double pred_j = sorted_preds[j];
			double weight_selection = freq_i * freq_j;
			// probability that we took case for i and control from j when pred_* is calibrated probablity for outcome
			double compare_prb = pred_j * (1 - pred_i);
			float succ_rate = 0.5;
			if (i != j) {
				succ_rate = 1;
				//add weight again of j<i where succ_rate is 0, but need to increase weight
				tot_weight += weight_selection * pred_i * (1 - pred_j);
			}

			auc_sum += succ_rate * weight_selection * compare_prb;
			tot_weight += weight_selection * compare_prb;
			//progress.update();
		}
	}
	progress.update();

	//map reduce:
	double auc_sum = 0, tot_weight = 0;
	for (size_t i = 0; i < auc_sum_t.size(); ++i)
	{
		auc_sum += auc_sum_t[i];
		tot_weight += tot_weight_t[i];
	}
	if (tot_weight > 0)
		auc_sum /= tot_weight;
	else
		auc_sum = MED_MAT_MISSING_VALUE;
	res["AUC"] = auc_sum;

	//Add calculation os SENS @ PR _ 1,3,5,10
	//Add calculation os PPV @ PR _ 1,3,5,10
	//Add calculation os LIFT @ PR _ 1,3,5,10
	//Add calculation os SPEC @ PR _ 1,3,5,10
	vector<double> pr_cutoffs = { 0.01,0.03,0.05,0.1,0.99 };
	double max_allowed_diff = 0.05;

	int score_th_i = 0, pr_i = 0;
	double curr_pr = 0, prev_pr = 0;
	bool update_pr_cutoff = false;

	double tot_controls = tot_samples - tot_cases;
	double tot_sens = 0, tot_fpr = 0;
	double prev_tot_sens = 0, prev_tot_fpr = 0;
	int last_idx_bin = (int)sorted_preds.size() - 1;
	while (score_th_i < sorted_preds.size() && pr_i < pr_cutoffs.size()) {
		//update prev_pr, curr_pr - add frequency of bin, if not updated cutoff last time
		int real_score_idx = last_idx_bin - score_th_i;
		double freq = score_dist.at(sorted_preds[real_score_idx]);
		if (!update_pr_cutoff) {
			prev_pr = curr_pr;
			curr_pr += freq;
			//update metrices:
			prev_tot_sens = tot_sens;
			prev_tot_fpr = tot_fpr;
			tot_sens += sorted_preds[real_score_idx] * freq* tot_samples;
			tot_fpr += (1 - sorted_preds[real_score_idx])*freq* tot_samples;
		}
		//test if passed required cutoff
		if (curr_pr >= pr_cutoffs[pr_i]) {
			//collect measurements in this cutoff based on linear interpolation from prev_pr,curr_pr:
			double diff_prev = pr_cutoffs[pr_i] - prev_pr;
			double diff_curr = curr_pr - pr_cutoffs[pr_i];
			double tot_diff = diff_prev + diff_curr;
			double weight_curr = 0.5, weight_prev = 0.5;
			if (tot_diff > 0) {
				weight_curr = diff_prev / tot_diff;
				weight_prev = diff_curr / tot_diff;
			}
			res[format_working_point("SENS@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
			res[format_working_point("SPEC@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
			res[format_working_point("PPV@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
			res[format_working_point("LIFT@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;

			if (diff_prev <= max_allowed_diff || diff_curr <= max_allowed_diff) {
				res[format_working_point("SENS@PR", pr_cutoffs[pr_i])] =
					(((tot_sens*weight_curr) + (prev_tot_sens*weight_prev)) / tot_cases) * 100;
				res[format_working_point("SPEC@PR", pr_cutoffs[pr_i])] =
					(1 - (((tot_fpr*weight_curr) + (prev_tot_fpr*weight_prev)) / tot_controls)) * 100;
				double ppv = (weight_curr*(tot_sens / (curr_pr * tot_samples))
					+ weight_prev * (prev_tot_sens / (prev_pr * tot_samples)));
				res[format_working_point("PPV@PR", pr_cutoffs[pr_i])] = ppv * 100;
				double lift = ppv / (tot_cases / tot_samples);
				res[format_working_point("LIFT@PR", pr_cutoffs[pr_i])] = lift;
			}

			//end collection
			++pr_i; //advance to next cutoff
			update_pr_cutoff = true;
			continue; //no need to advance score_th_i, wait. Don't update prev_pr,curr_pr and other metrices either
		}

		update_pr_cutoff = false;
		++score_th_i;
	}

	//Add missing values to the rest if needed and reached end of sorted_preds before
	while (pr_i < pr_cutoffs.size()) {
		res[format_working_point("SENS@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
		res[format_working_point("SPEC@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
		res[format_working_point("PPV@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
		res[format_working_point("LIFT@PR", pr_cutoffs[pr_i])] = MED_MAT_MISSING_VALUE;
		++pr_i;
	}
}

map<string, float> bt_calc_roc_measures(Lazy_Iterator *iterator, int thread_num,
	Measurement_Params *function_params) {
	random_device rd;
	mt19937 rnd_gen(rd());
	uniform_real_distribution<> rand_real(0, 1);

	int sample_per_pid = 0;
	int loopCnt = 500;
	int seed = 0;
	//Generate new Lazy_Iterator that points to the static edited arrays. and call calc_roc_measures_with_inc
	
	vector<int> pids, preds_order;
	vector<float> preds, labels, weights;
	float y, pred, weight;
	int pid_id = 0;
	iterator->sample_all_no_sampling = true;
	iterator->restart_iterator(thread_num);
	iterator->set_thread_sample_all(thread_num);
	while (iterator->fetch_next_external(thread_num, y, pred, weight)) {
		double p = rand_real(rnd_gen);
		y = (p < pred);
		++pid_id;
		//Allocate pred,y,weight
		pids.push_back(pid_id);
		preds.push_back(pred);
		labels.push_back(y);
		weights.push_back(weight);
	}
	preds_order.resize(preds.size());
	if (preds_order.empty())
		MTHROW_AND_ERR("Error - samples is empty\n");
	Lazy_Iterator static_iterator(&pids, &preds, &labels, &weights, 1.0, sample_per_pid,
		loopCnt + 1, seed, &preds_order);
	
	return calc_roc_measures_with_inc(&static_iterator, thread_num, function_params);
}
//Assume samples has calibrated predictions (Uses only the prediction)
void fetch_bootstrap_from_calibration(MedSamples &samples, const string &save_path) {
	//In each bootstrap run will randomize outcome according to prediction.
	//Use "bt_calc_roc_measures" with bootstrap on samples
	string bt_params = "loopcnt=500;sample_per_pid=0";
	MedBootstrapResult bt;
	bt.bootstrap_params.init_from_string(bt_params);
	bt.bootstrap_params.is_binary_outcome = false;

	vector<pair<MeasurementFunctions, Measurement_Params *>> &cl_m = bt.bootstrap_params.measurements_with_params;
	cl_m.clear(); //clear and remove the default
	cl_m.push_back(pair<MeasurementFunctions, Measurement_Params *>(bt_calc_roc_measures, &bt.bootstrap_params.roc_Params));

	map<string, vector<float>> empty;
	bt.bootstrap(samples, empty);
	bt.write_results_to_text_file(save_path);
	MLOG("Wrote bootstrap in %s\n", save_path.c_str());
}

int main(int argc, char *argv[]) {
	// Parse the command-line parameters
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;
	MedSamples samples;
	samples.read_from_file(args.preds);
	//Current version no support for rep,json_model and cohorts_file
	ofstream fw(args.output);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open file %s for write\n", args.output.c_str());
	fw << "Measurement" << "\t" << "Value" << "\n";
	map<string, float> res;
	get_roc_from_calibrated_preds(samples, res);
	for (auto &it : res)
		fw << it.first << "\t" << it.second << "\n";
	fw.close();

	fetch_bootstrap_from_calibration(samples, args.output + ".bootstrap.pivot_txt");

	return 0;
}