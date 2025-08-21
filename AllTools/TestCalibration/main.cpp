#include <string>
#include <boost/filesystem.hpp>
#include <boost/regex.hpp>
#include <iostream>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedUtils/MedUtils/MedRegistry.h>
#include <MedProcessTools/MedProcessTools/Calibration.h>
#include <MedUtils/MedUtils/MedPlot.h>
#include <MedAlgo/MedAlgo/BinSplitOptimizer.h>
#include <MedStat/MedStat/MedBootstrap.h>
#include "Cmd_Args.h"
#include <algorithm>
using namespace std;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void read_model_splits(const string &model_splits, vector<MedModel> &models, unordered_map<int, int> &pid_to_model_idx) {
	ifstream fr(model_splits);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't open %s file for reading\n", model_splits.c_str());
	//Fomat [PID] TAB_DELIMETER [MODEL_PATH]
	string line;
	unordered_set<string> model_seen;
	unordered_map<string, vector<int>> model_to_pids;
	while (getline(fr, line)) {
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Error bad format file %s expected 2 tokens of tab dilimeter. line:\n%s\n",
				model_splits.c_str(), line.c_str());
		int pid = med_stoi(tokens[0]);
		const string &mdl_path = tokens[1];
		if (model_seen.find(mdl_path) == model_seen.end()) {
			model_seen.insert(mdl_path);
		}
		model_to_pids[mdl_path].push_back(pid);
	}
	vector<string> all_mdls(model_seen.begin(), model_seen.end());
	sort(all_mdls.begin(), all_mdls.end());
	//read models
	models.resize(all_mdls.size());
	for (int i = 0; i < all_mdls.size(); ++i) {
		models[i].read_from_file(all_mdls[i]);
		const vector<int> &all_pids = model_to_pids[all_mdls[i]];
		for (int pid : all_pids) //connect all pids to current i
			pid_to_model_idx[pid] = i;
	}
}

void apply_model_splits_main(const unordered_map<int, int> &pid_to_model_idx, vector<MedModel> &models,
	const string &rep_path, MedSamples &samples, vector<MedSample> &samples_prob, bool throw_not_found) {
	if (models.empty())
		MTHROW_AND_ERR("Error - models is empty\n");

	//split MedSamples by splits:
	vector<MedSamples> samples_by_split(models.size());
	for (size_t i = 0; i < samples_by_split.size(); ++i)
		samples_by_split[i].time_unit = samples.time_unit;

	int not_fnd = 0;
	int exmaple_not_fnd = -1;
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
	{
		int pid = samples.idSamples[i].id;
		int sel_split;
		if (pid_to_model_idx.find(pid) == pid_to_model_idx.end()) {
			if (throw_not_found)
				MTHROW_AND_ERR("Error - can't find pid %d in model splits\n", pid);
			++not_fnd;
			exmaple_not_fnd = pid;
			sel_split = 0;
		}
		else
			sel_split = pid_to_model_idx.at(pid);

		samples_by_split[sel_split].idSamples.push_back(samples.idSamples[i]);
	}
	if (not_fnd > 0)
		MWARN("Warning: Has %d not found pid in splits. example_pid = %d\n", not_fnd, exmaple_not_fnd);

	MedPidRepository rep;
	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	vector<int> pids; //fetch all
	models.front().load_repository(rep_path, rep, true);
	//collect each split:
	samples_prob.clear();
	for (size_t i = 0; i < samples_by_split.size(); ++i) {
		models[i].fit_for_repository(rep);
		if (models[i].apply(rep, samples_by_split[i], MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_END) < 0)
			MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");

		samples_by_split[i].flatten(samples_prob);
	}
}

void fix_scores_probs(MedSamples &samples, vector<MedSample> &samples_probs,
	const string &rep_path, const string &medmodel_path, const string &pid_to_split_file) {
	MedFeatures train_matrix;
	unordered_set<string> selected_sigs;
	unordered_map<string, vector<float>> additional_bootstrap;

	if (!pid_to_split_file.empty()) {
		vector<MedModel> models_main;
		unordered_map<int, int> pid_to_mdl_idx;
		read_model_splits(pid_to_split_file, models_main, pid_to_mdl_idx);
		MLOG("Loaded %zu models from split file: %s\n", models_main.size(), pid_to_split_file.c_str());

		apply_model_splits_main(pid_to_mdl_idx, models_main, rep_path, samples, samples_probs, false);
		return;
	}

	//simple case - assume train & calibrated on diffrent set. otherwise, don't active both flags.
	if (!medmodel_path.empty()) {
		MedModel model_calibrated;
		model_calibrated.read_from_file(medmodel_path);
		model_calibrated.verbosity = 0;

		medial::medmodel::apply(model_calibrated, samples, rep_path, MED_MDL_END);
		samples_probs = move(model_calibrated.features.samples);
	}
	else {
		//samples has preds: Test and copy into samples_probs
		vector<MedSample> flat;
		samples.export_to_sample_vec(flat);
		bool has_preds = true;
		for (size_t i = 0; i < flat.size() && has_preds; ++i)
			has_preds = !flat[i].prediction.empty();
		if (!has_preds)
			MTHROW_AND_ERR("Error TestCalibration - fix_scores_probs - input samples without a model should have predictions\n");
		samples_probs = move(flat);
	}

}

string build_series_data(const vector<pair<float, float>> &dmap, int i,
	const string &chart_type, const string &mode, const string &name, const vector<float> &text_data,
	const string &addition_text, const vector<float> &ci_lower, const vector<float> &ci_upper) {
	stringstream s;
	if (!ci_lower.empty() && ci_lower.size() != dmap.size())
		MTHROW_AND_ERR("Error graph points number = %zu, ci_lower has %zu points\n",
			dmap.size(), ci_lower.size());
	if (!ci_upper.empty() && ci_upper.size() != dmap.size())
		MTHROW_AND_ERR("Error graph points number = %zu, ci_upper has %zu points\n",
			dmap.size(), ci_upper.size());

	s << "var y_data_" << i << " = [";
	auto it = dmap.begin();
	if (it != dmap.end()) {
		if (it->second != MED_MAT_MISSING_VALUE)
			s << it->second;
		else
			s << "NaN";
	}
	++it;
	for (; it != dmap.end(); ++it) {
		if (it->second != MED_MAT_MISSING_VALUE)
			s << ", " << it->second;
		else
			s << ", NaN";
	}
	s << "];\n";

	s << "var series" << i << " = {\n type: '" << chart_type << "'";
	if (!mode.empty())
		s << ",\n mode: '" << mode << "'";
	s << ",\n x: [";
	it = dmap.begin();
	if (it != dmap.end()) {
		if (it->first != MED_MAT_MISSING_VALUE)
			s << it->first;
		else
			s << "NaN";
	}
	++it;
	for (; it != dmap.end(); ++it) {
		if (it->first != MED_MAT_MISSING_VALUE)
			s << ", " << it->first;
		else
			s << ", NaN";
	}
	s << "], \n";

	s << "y: y_data_" << i << "\n";
	if (!text_data.empty()) {
		s << ", text: [";
		s << text_data[0];
		for (size_t i = 1; i < text_data.size(); ++i)
			s << ", " << text_data[i];
		s << "]\n";
	}

	if (!ci_lower.empty() || !ci_upper.empty()) {
		//add error bar:
		s << ", error_y: { type : 'data', symmetric: false, array: [";
		//add if needed:
		if (!ci_upper.empty()) {
			if (ci_upper[0] != MED_MAT_MISSING_VALUE)
				s << ci_upper[0];
			else
				s << "NaN";
			for (size_t i = 1; i < ci_upper.size(); ++i) {
				if (ci_upper[i] != MED_MAT_MISSING_VALUE)
					s << ", " << ci_upper[i];
				else
					s << ", NaN";
			}
		}
		s << "], arrayminus: [";
		//add if needed
		if (!ci_lower.empty()) {
			if (ci_lower[0] != MED_MAT_MISSING_VALUE)
				s << ci_lower[0];
			else
				s << "NaN";
			for (size_t i = 1; i < ci_lower.size(); ++i) {
				if (ci_lower[0] != MED_MAT_MISSING_VALUE)
					s << ", " << ci_lower[i];
				else
					s << ", NaN";
			}
		}
		s << "]";
		s << ", visible: false, opacity: 0.4 }\n";
	}

	if (!name.empty()) {
		s << ", name: '";
		s << name;
		s << "' \n";
	}
	if (!addition_text.empty())
		s << ", " << addition_text;

	s << "};\n";

	return s.str();
}

void plotCalibrationGraph(const string &outPath, const vector<pair<float, float>> &data_expected_predicted,
	const vector<pair<float, float>> &data_observed_prob, const vector<pair<float, float>> &bin_sizes,
	const string &title, const string &additional_text, float std_factor, const vector<float> &lower_ci,
	const vector<float> &upper_ci, bool lower_up_from_observed) {

	//data is : real, predictor, bin_size
	stringstream s;

	string xName = "Predicted Score in Percents";
	string yName = "Observed Validation Cases in Percents";

	string content = "<html>\n<head>\n  <!-- Plotly.js -->\n   <script src=\"plotly-latest.min.js\"></script>\n</head>\n\n<body>\n  <div id=\"myDiv\" align=\"center\"><!-- Plotly chart will be drawn inside this DIV --></div>\n  <script>\n    <!-- JAVASCRIPT CODE GOES HERE -->\n\n\t{0}\n\nPlotly.newPlot(\'myDiv\', data, layout);\n\t\n\tfunction searchXY() {\n\t\tsNum = parseInt(document.getElementById(\'seriesNum\').value);\n\t\tx = parseFloat(document.getElementById(\'xVal\').value);\n\t\ty = parseFloat(document.getElementById(\'yVal\').value);\n\t\tvar ser = data[sNum];\n\t\t\n\t\tif (\'z\' in ser) { //search in 3D Graph\n\t\t\tvar ind = ser.x.indexOf(x) + (ser.y.indexOf(y) % ser.x.length);\n\t\t\tdocument.getElementById(\'res\').innerHTML = ser.z[ind];\n\t\t\treturn ser.z[ind];\n\t\t}\n\t\telse {\n\t\tvar minDistance = NaN;\n\t\tvar minDistanceInd = NaN;\n\t\t\tif (!isNaN(x)) {\n\t\t\t\tfor (i=0; i< ser.x.length; ++i) {\n\t\t\t\t\tif (isNaN(minDistance) || Math.abs(ser.x[i] - x) < minDistance) {\n\t\t\t\t\t\tminDistance = Math.abs(ser.x[i] - x);\n\t\t\t\t\t\tminDistanceInd = i;\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\tdocument.getElementById(\'xVal\').value = ser.x[minDistanceInd];\n\t\t\t\tdocument.getElementById(\'yVal\').value = ser.y[minDistanceInd];\n\t\t\t}\n\t\t\telse if(!isNaN(y)) {\n\t\t\t\tfor (i=0; i< ser.y.length; ++i) {\n\t\t\t\t\tif (isNaN(minDistance) || Math.abs(ser.y[i] - y) < minDistance) {\n\t\t\t\t\t\tminDistance = Math.abs(ser.y[i] - y);\n\t\t\t\t\t\tminDistanceInd = i;\n\t\t\t\t\t}\n\t\t\t\t}\n\t\t\t\tdocument.getElementById(\'xVal\').value = ser.x[minDistanceInd];\n\t\t\t\tdocument.getElementById(\'yVal\').value = ser.y[minDistanceInd];\n\t\t\t}\n\t\t\t\n\t\t}\n\t}\n\t\n  </script>\n  \n  <h3 align=\"center\">Search for values in graph (leave x or y empty to search for the other value)</h3>\n   <p align=\"center\"> \n   <label for \"seriesNum\">series number (top is 0)</label>\n   <input type=\"number\" name=\"seriesNum\" id=\"seriesNum\" value=\"0\"></input>\n  <label for=\"xVal\">x</label>\n  <input type=\"number\" name=\"xVal\" id=\"xVal\"></input>\n  <label for=\"xVal\">y</label>\n  <input type=\"number\" name=\"yVal\" id=\"yVal\"></input>\n  <input type=\"button\" value=\"search\" onclick=\"searchXY();\"></input>\n  </p>\n  <span id=\"res\"></span>\n <h2>{1}</h2> \n<button id=\"tgl_msn\" onclick=\"toggle_view()\">Switch to Mode_2</button></body>\n</html>";

	size_t ind = content.find("{0}");
	if (ind == string::npos)
		MTHROW_AND_ERR("Not Found in template. need to contain string {0}\n");

	size_t ind2 = content.find("{1}");
	if (ind2 == string::npos)
		MTHROW_AND_ERR("Not Found in template. need to contain string {1}\n");

	string rep = "";
	vector<string> chart_type = { "scatter", "scatter", "bar" };
	vector<float> empty_text_data, bin_cnt_vec(bin_sizes.size());
	vector<float> empty_ci_data;
	for (size_t i = 0; i < bin_cnt_vec.size(); ++i)
		bin_cnt_vec[i] = bin_sizes[i].second;

	vector<float> ci_data_std_low = lower_ci;
	vector<float>  ci_data_std_up = upper_ci;
	if (lower_ci.empty()) {
		ci_data_std_low.resize(data_observed_prob.size());
		for (size_t i = 0; i < ci_data_std_low.size(); ++i)
		{
			double std = 100 * sqrt((data_observed_prob[i].first / 100 * (1 - data_observed_prob[i].first / 100)) / bin_sizes[i].second);
			ci_data_std_low[i] = std_factor * std;
		}
	}
	if (upper_ci.empty()) {
		ci_data_std_up.resize(data_observed_prob.size());
		for (size_t i = 0; i < ci_data_std_up.size(); ++i)
		{
			double std = 100 * sqrt((data_observed_prob[i].first / 100 * (1 - data_observed_prob[i].first / 100)) / bin_sizes[i].second);
			ci_data_std_up[i] = std_factor * std;
		}
	}
	string real_txt = build_series_data(data_expected_predicted, 1, "scatter", "lines+markers", "Expected Predicted Percentage",
		empty_text_data, "marker: {size : 10, color: '#1f77b4', line: { color: '#1f77b4'}}", empty_ci_data, empty_ci_data);
	s << real_txt << "\n";

	string predictor_txt = build_series_data(data_observed_prob, 2, "scatter", "lines+markers+text",
		"Validation Observed Percentage",
		bin_cnt_vec, "textposition: 'top center',\n marker: {size : 10, color: '#ff7f0e', line: { color: '#ff7f0e'}} ", ci_data_std_low, ci_data_std_up);
	s << predictor_txt << "\n";

	string bining_txt = build_series_data(bin_sizes, 3, "bar", "", "Bin Size",
		empty_text_data, "yaxis: 'y2', \n width : 0.5, marker: { line: { color: 'black', width: 0.5 } } ", empty_ci_data, empty_ci_data);
	s << bining_txt << "\n";

	//add lower and upper graphs:
	vector<pair<float, float>> lower_nums(data_observed_prob.size()), upper_nums(data_observed_prob.size());
	for (size_t i = 0; i < data_observed_prob.size(); ++i)
	{
		lower_nums[i].first = data_observed_prob[i].first;
		upper_nums[i].first = data_observed_prob[i].first;
		if (lower_up_from_observed) {
			lower_nums[i].second = data_observed_prob[i].second - ci_data_std_low[i];
			upper_nums[i].second = data_observed_prob[i].second + ci_data_std_up[i];
		}
		else {
			lower_nums[i].second = data_observed_prob[i].first - ci_data_std_low[i];
			upper_nums[i].second = data_observed_prob[i].first + ci_data_std_up[i];
		}
	}
	string lower_obs_exp = build_series_data(lower_nums, 4, "scatter", "lines+markers",
		"Lower Expected Observation Percentage",
		empty_text_data, "marker: {size : 3}, line: { shape : 'spline'} ", empty_ci_data, empty_ci_data);
	s << lower_obs_exp << "\n";
	string upper_obs_exp = build_series_data(upper_nums, 5, "scatter", "lines+markers",
		"Upper Expected Observation Percentage",
		empty_text_data, "marker: {size : 3}, line: { shape : 'spline'} ", empty_ci_data, empty_ci_data);
	s << upper_obs_exp << "\n";

	s << "var data = [ series1, series2, series3, series4, series5 ];\n";


	s << "var layout = { \n  title:'";
	s << title + "',\n ";


	s << "xaxis: { title : '" << xName << "'},\n ";
	s << "yaxis: { title: '" << yName << "', overlaying : 'y2', side : 'left'},\n ";
	s << "yaxis2: { title: '" << "Observation Count Size" << "', side : 'right'},\n ";


	s << "height: 800, \n width: 1200,\n ";
	s << "updatemenus : [ {\n";

	s << "\ty: 1, x: 1, yanchor: 'bottom', type: 'dropdown',\n";
	s << "\tbuttons: [ \n";
	s << "\t{  method: 'restyle', label: 'Markers+Line+Text', args: ['mode', 'markers+lines+text']},\n";
	s << "\t{  method: 'restyle', label: 'Markers+Line', args: ['mode', 'markers+lines']},\n";
	s << "\t{  method: 'restyle', label: 'Markers', args: ['mode', 'markers']}\n";
	s << "\t]\n}";

	s << "\t]";
	s << " \n }; ";

	s << "\n function toggle_view() {\n "
		<< "var btn = document.getElementById('tgl_msn');\n"
		<< "var change_view_mode_1=btn.innerText.indexOf('Mode_1') >= 0;\n"
		<< "if (change_view_mode_1) {\n"
		<< "series2.error_y.visible = false;\n"
		<< "data = [ series1, series2, series3, series4, series5 ];\n btn.innerText='Switch to Mode_2';"
		<< "}\n"
		<< "else {\n"
		<< "series2.error_y.visible = true;\n"
		<< "data = [ series2, series1 ];\n btn.innerText='Switch to Mode_1';"
		<< "}\n"
		<< "Plotly.purge('myDiv'); \n Plotly.newPlot('myDiv', data, layout);\n"
		<< " }";

	///replace from end to begin
	content.replace(ind2, 3, additional_text);

	content.replace(ind, 3, s.str());
	content.replace(content.find("\"plotly-latest.min.js\""), 22, "\"/nas1/Work/Graph_Infra/plotly-latest.min.js\"");

	ofstream myfile;
	cerr << "writing: [" << outPath << "]\n";
	myfile.open(outPath);
	if (!myfile.good())
		cerr << "IO Error: can't write " << outPath << endl;
	myfile << content;
	myfile.close();

}

vector<pair<float, float>> convert_map(const map<float, float> &m, bool multiply_percent) {
	vector<pair<float, float>> res;
	res.resize(m.size());
	int i = 0;
	for (auto it = m.begin(); it != m.end(); ++it) {
		res[i].first = 100 * it->first;
		if (!multiply_percent)
			res[i].second = it->second;
		else
			res[i].second = 100 * it->second;
		++i;
	}
	return res;
}

class Calibration_Args : public Measurement_Params {
public:
	int min_bin_size = 0;
	float cases_weight = 1;
	float controls_weight = 1;
	string bin_settings = "";
	bool calc_bins_once = true;
};

map<string, float> bootstrap_calibration(Lazy_Iterator *iterator, int thread_num, Measurement_Params *function_params) {
	map<string, float> res;
	Calibration_Args *params = static_cast<Calibration_Args *>(function_params);

	vector<float> preds, outcome_vec, weights;
	float y, w, pred;
	bool has_weights = false;
	while (iterator->fetch_next_external(thread_num, y, pred, w))
	{
		preds.push_back(pred);
		outcome_vec.push_back(y);
		weights.push_back(w);
		has_weights = has_weights || w >= 0;
	}
	if (!has_weights)
		weights.clear();

	map<float, float> prob_final;
	if ((params->min_bin_size > 0 || !params->bin_settings.empty())) {
		//use iterative:
		BinSettings sett;
		if (!params->bin_settings.empty())
			sett.init_from_string(params->bin_settings);
		else {
			sett.binCnt = 0;
			sett.split_method = BinSplitMethod::IterativeMerge;
		}
		sett.min_bin_count = params->min_bin_size;

		vector<int> empt;
		medial::process::split_feature_to_bins(sett, preds, empt, preds);
	}


	map<float, pair<int, int>> prob_stats; //totCnt,posCnt
	for (size_t i = 0; i < preds.size(); ++i)
	{
		++prob_stats[preds[i]].first;
		prob_stats[preds[i]].second += int(outcome_vec[i] > 0);
	}

	for (auto &it : prob_stats) {
		float n0 = (float)it.second.first - (float)it.second.second;
		float n1 = (float)it.second.second;
		it.second.first = (int)(params->controls_weight * n0 + params->cases_weight * n1);
		it.second.second = (int)(params->cases_weight * n1);
	}
	for (auto &it : prob_stats)
		prob_final[it.first] = (float)it.second.second / float(it.second.first);

	double tot_loss = 0, tot_pos = 0, tot_count = 0;

	map<float, float> graph_observed_calibration, perfect_ref, bin_sizes;
	for (auto it = prob_stats.begin(); it != prob_stats.end(); ++it)
	{
		double real_prob = prob_final[it->first];
		double diff = abs(it->first - real_prob);

		res["OBSERVED_PROB@PREDICTED_PROB_" + medial::print::print_obj(100 * it->first, "%06.3f")] = 100.0 * real_prob;
		res["NPOS@PREDICTED_PROB_" + medial::print::print_obj(100 * it->first, "%06.3f")] = it->second.second;
		res["NNEG@PREDICTED_PROB_" + medial::print::print_obj(100 * it->first, "%06.3f")] = it->second.first - it->second.second;
		res["DIFF@PREDICTED_PROB_" + medial::print::print_obj(100 * it->first, "%06.3f")] = 100 * diff;

		tot_loss += diff * diff * it->second.first;
		tot_pos += it->second.second;
		tot_count += it->second.first;
		graph_observed_calibration[it->first] = real_prob;
		perfect_ref[it->first] = it->first;
		bin_sizes[it->first] = it->second.first;
	}
	tot_loss /= tot_count;
	tot_loss = sqrt(tot_loss);
	double prior = tot_pos / tot_count;
	double loss_prior = 0;
	for (auto it = prob_stats.begin(); it != prob_stats.end(); ++it)
		loss_prior += (it->first - prior)*(it->first - prior) * it->second.first;
	loss_prior /= tot_count;
	loss_prior = sqrt(loss_prior);
	float R2 = 1 - (tot_loss / loss_prior);

	//calc calibration index

	if (params->controls_weight != 1 || params->cases_weight != 1) {
		weights.resize(preds.size(), 1);
		for (size_t i = 0; i < weights.size(); ++i)
			weights[i] = (outcome_vec[i] > 0) ? params->cases_weight : params->controls_weight;
	}
	double ici_res = medial::performance::integrated_calibration_index(preds, outcome_vec, &weights);

	res["CalibrationIndex"] = ici_res;
	res["RMSE"] = tot_loss;
	res["R2"] = R2;

	return res;
}

void get_mat(const string &json_model, const string &rep_path,
	MedSamples &samples, MedModel &mdl) {
	MedPidRepository rep;
	if (!json_model.empty())
		mdl.init_from_json_file(json_model);
	else
		MLOG("No json for bootstrap - can only use Time-Window,Age,Gender filters\n");

	bool need_age = true, need_gender = true;
	for (FeatureGenerator *generator : mdl.generators) {
		if (generator->generator_type == FTR_GEN_AGE)
			need_age = false;
		if (generator->generator_type == FTR_GEN_GENDER)
			need_gender = false;
	}
	if (need_age)
		mdl.add_age();
	if (need_gender)
		mdl.add_gender();


	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	mdl.fit_for_repository(rep);
	unordered_set<string> req_names;
	mdl.get_required_signal_names(req_names);

	vector<string> sigs(req_names.begin(), req_names.end());
	mdl.filter_rep_processors();

	int curr_level = global_logger.levels.front();
	global_logger.init_all_levels(LOG_DEF_LEVEL);
	vector<int> pids_to_take;
	samples.get_ids(pids_to_take);
	if (rep.read_all(rep_path, pids_to_take, sigs) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	global_logger.init_all_levels(curr_level);

	if (mdl.learn(rep, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS,
		MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
		MTHROW_AND_ERR("Error creating features for filtering\n");
}

void bootstrap_cl_main(const MedSamples &calibrated_preds,
	const string &rep_path, const string &json_model, const string &bt_params,
	const string &cohorts_file, Calibration_Args &cl_args, MedBootstrapResult &bt) {
	bt.bootstrap_params.init_from_string(bt_params);
	if (!cohorts_file.empty())
		bt.bootstrap_params.parse_cohort_file(cohorts_file);

	vector<pair<MeasurementFunctions, Measurement_Params *>> &cl_m = bt.bootstrap_params.measurements_with_params;
	cl_m.clear();
	cl_m.push_back(pair<MeasurementFunctions, Measurement_Params *>(bootstrap_calibration, &cl_args));

	MedSamples smps_preds = calibrated_preds;

	if (cl_args.calc_bins_once) {
		vector<float> preds;
		smps_preds.get_preds(preds);
		if (preds.size() != calibrated_preds.nSamples())
			MTHROW_AND_ERR("Error mismatch sizes nsampels=%d, preds=%zu\n",
				calibrated_preds.nSamples(), preds.size());

		//binning if has:
		if ((cl_args.min_bin_size > 0 || !cl_args.bin_settings.empty())) {
			//use iterative:
			BinSettings sett;
			if (!cl_args.bin_settings.empty())
				sett.init_from_string(cl_args.bin_settings);
			else {
				sett.binCnt = 0;
				sett.split_method = BinSplitMethod::IterativeMerge;
			}
			sett.min_bin_count = cl_args.min_bin_size;

			vector<int> empt;
			medial::process::split_feature_to_bins(sett, preds, empt, preds);
		}
		cl_args.min_bin_size = 0;
		cl_args.bin_settings = "";

		//return preds to smps_preds:
		int pred_idx = 0;
		for (size_t i = 0; i < smps_preds.idSamples.size(); ++i)
			for (size_t j = 0; j < smps_preds.idSamples[i].samples.size(); ++j) {
				smps_preds.idSamples[i].samples[j].prediction[0] = preds[pred_idx];
				++pred_idx;
			}
	}

	//create matrix for json, and rep
	MedModel mdl;
	get_mat(json_model, rep_path, smps_preds, mdl);
	MedFeatures matrix = move(mdl.features);
	bt.bootstrap_params.clean_feature_name_prefix(matrix.data);
	bt.bootstrap(matrix);
}

void test_preformace(const vector<MedSample> &model_result, bool test_kaplan_meier, int kaplan_meier_time,
	ofstream &log_fw, const string &output, int min_bin_size, float cases_weight, float controls_weight
	, const string &bin_settings, float std_factor) {
	map<float, float> prob_final; //pred to measured pred
								  //count on each prob group in risk_model - the diff from that group:

	//update model_result.prediction to inforce min_bin_size:
	vector<float> preds(model_result.size());
	for (size_t i = 0; i < model_result.size(); ++i)
		preds[i] = model_result[i].prediction[0];

	if ((min_bin_size > 0 || !bin_settings.empty()) && !test_kaplan_meier) {
		//use iterative:
		MLOG("Enforcing minimal bin size of %d\n", min_bin_size);
		BinSettings sett;
		if (!bin_settings.empty())
			sett.init_from_string(bin_settings);
		else {
			sett.binCnt = 0;
			sett.split_method = BinSplitMethod::IterativeMerge;
		}
		sett.min_bin_count = min_bin_size;

		vector<int> empt;
		medial::process::split_feature_to_bins(sett, preds, empt, preds);
	}

	map<float, pair<int, int>> prob_stats; //totCnt,posCnt
	for (size_t i = 0; i < preds.size(); ++i)
	{
		++prob_stats[preds[i]].first;
		prob_stats[preds[i]].second += int(model_result[i].outcome > 0);
	}

	for (auto &it : prob_stats) {
		float n0 = (float)it.second.first - (float)it.second.second;
		float n1 = (float)it.second.second;
		it.second.first = (int)(controls_weight * n0 + cases_weight * n1);
		it.second.second = (int)(cases_weight * n1);
	}

	if (!test_kaplan_meier) {
		for (auto &it : prob_stats) {
			prob_final[it.first] = (float)it.second.second / float(it.second.first);
			//prob_final[it.first] = cases_weight * (float)it.second.second / (controls_weight * float(it.second.first));
		}
	}
	else {
		//need to calc kaplan meier for each prediction bin
		unordered_map<float, vector<MedSample>> kp_samples_for_score_flat;
		for (size_t i = 0; i < model_result.size(); ++i) {
			vector<MedSample> &curr = kp_samples_for_score_flat[model_result[i].prediction[0]];
			curr.push_back(model_result[i]);
		}
		global_logger.levels[MED_SAMPLES_CV] = MAX_LOG_LEVEL;
		for (auto &it : kp_samples_for_score_flat) {
			MedSamples kp_samples;
			kp_samples.import_from_sample_vec(it.second);
			double prob = medial::stats::kaplan_meir_on_samples(kp_samples, kaplan_meier_time);
			prob_final[it.first] = prob;
		}
		global_logger.levels[MED_SAMPLES_CV] = LOG_DEF_LEVEL;
	}


	double tot_loss = 0, tot_pos = 0, tot_count = 0;
	string additional_tit = "";
	if (test_kaplan_meier)
		additional_tit = "\t Validation_simple_probabilty";
	medial::print::log_with_file(log_fw, "probabilty_of_model \t Validation_probabilty %s \t cases \t total_observations \t Diff\n", additional_tit.c_str());
	map<float, float> graph_observed_calibration, perfect_ref, bin_sizes;
	for (auto it = prob_stats.begin(); it != prob_stats.end(); ++it)
	{
		double real_prob = prob_final[it->first];
		double simple_prb = it->second.second / float(it->second.first);;
		double diff = abs(it->first - real_prob);
		string addi = "";
		if (test_kaplan_meier)
			addi = medial::print::print_obj(100.0 * simple_prb, "\t %2.4f%% ");
		medial::print::log_with_file(log_fw, "%2.4f%% \t %2.4f%% %s\t %d \t %d \t %2.4f%%\n", 100 * it->first,
			100.0 * real_prob, addi.c_str(), it->second.second, it->second.first, 100 * diff);
		tot_loss += diff * diff * it->second.first;
		tot_pos += it->second.second;
		tot_count += it->second.first;
		graph_observed_calibration[it->first] = real_prob;
		perfect_ref[it->first] = it->first;
		bin_sizes[it->first] = it->second.first;
	}
	tot_loss /= tot_count;
	tot_loss = sqrt(tot_loss);
	double prior = tot_pos / tot_count;
	double loss_prior = 0;
	for (auto it = prob_stats.begin(); it != prob_stats.end(); ++it)
		loss_prior += (it->first - prior)*(it->first - prior) * it->second.first;
	loss_prior /= tot_count;
	loss_prior = sqrt(loss_prior);
	float R2 = 1 - (tot_loss / loss_prior);

	//calc calibration index
	vector<float> outcome_vec(model_result.size());
	for (size_t i = 0; i < model_result.size(); ++i)
		outcome_vec[i] = model_result[i].outcome;
	vector<float> weights;
	if (controls_weight != 1 || cases_weight != 1) {
		weights.resize(preds.size(), 1);
		for (size_t i = 0; i < weights.size(); ++i)
			weights[i] = (outcome_vec[i] > 0) ? cases_weight : controls_weight;
	}
	double ici_res = medial::performance::integrated_calibration_index(preds, outcome_vec, &weights);

	char buffer[5000];
	snprintf(buffer, sizeof(buffer), "tot_diff(L2)=%f prior=%f prior_loss(L2)=%f R2=%f Num_Bins=%zu Calibration_Index=%f",
		tot_loss, prior, loss_prior, R2, prob_stats.size(), ici_res);
	string pref_txt = string(buffer);
	medial::print::log_with_file(log_fw, "%s\n",
		pref_txt.c_str());

	//document the size in each bin!!
	if (!output.empty()) {
		vector<float> empt_vec;
		plotCalibrationGraph(output + ".graph.html", convert_map(perfect_ref, true), convert_map(graph_observed_calibration, true)
			, convert_map(bin_sizes, false), "Calibration graph", pref_txt, std_factor, empt_vec, empt_vec, false);
	}
}

string get_filename_no_ext(const string &fp) {
	boost::filesystem::path file_p(fp);
	string fname = file_p.filename().string();

	if (fname.find(".") != string::npos)
		return fname.substr(0, fname.find_last_of('.'));
	else
		return fname;
}

float fetch_ref(const string &s) {
	float res = MED_MAT_MISSING_VALUE;
	string truncated = s.substr(s.find("@") + 16);
	size_t pos = truncated.find("_");
	if (pos == string::npos)
		MTHROW_AND_ERR("Error bad format %s\n", s.c_str());
	string to_conv = truncated.substr(0, pos);
	res = med_stof(to_conv);
	return res;
}

bool comp_nums_graph(const pair<float, float> &pr1, const pair<float, float> &pr2) {
	return pr1.first < pr2.first;
}

void test_calibration(const string &rep_path, const vector<Calibration_Test> &tests, const string &output
	, bool test_kaplan_meier, int kaplan_meier_time, const string &pid_to_split_file, int min_bin_size,
	float cases_weight, float controls_weight, const string &bin_settings,
	const string &json_model, const string &bt_params, const string &cohorts_file,
	bool calc_bins_once, const string &bootstrap_graphs_path, float std_factor) {
	ofstream fw;
	if (!output.empty())
	{
		fw.open(output);
		if (!fw.good())
			MTHROW_AND_ERR("Can't open %s for writing\n", output.c_str());
	}
	//medial::print::log_with_file()

	string kp_str = "";
	if (test_kaplan_meier)
		kp_str = medial::print::print_obj(kaplan_meier_time, "\tkaplan_meir_time=%d\n");
	///merge all tests into one:
	vector<Calibration_Test> tests_final = tests;
	if (!pid_to_split_file.empty()) {
		Calibration_Test merged_test;
		MedSamples samples_merged;
		merged_test.model_path = ""; //will use pid_to_split_file
		merged_test.filter_split = -1;
		for (int i = 0; i < tests_final.size(); ++i) {
			MedSamples batch;
			batch.read_from_file(tests_final[i].validation_samples_path);
			samples_merged.append(batch);
		}
		samples_merged.sort_by_id_date();

		tests_final.clear();
		merged_test.stored_samples = move(samples_merged);
		tests_final.push_back(move(merged_test));
		medial::print::log_with_file(fw, "#####################BEGIN_TEST###################\n");
		medial::print::log_with_file(fw, "Test %d\tUsing_pids_medmodel_path:%s%s\n",
			1, pid_to_split_file.c_str(), kp_str.c_str());
	}


	vector<MedSample> all_tests;
	for (int i = 0; i < tests_final.size(); ++i) {
		vector<MedSample> model_result;
		//run on each test and also aggregate results:
		if (pid_to_split_file.empty()) {
			medial::print::log_with_file(fw, "#####################BEGIN_TEST###################\n");
			medial::print::log_with_file(fw, "Test %d\tModel_Path:%s\tTest_Samples:%s\tFilter_Split:%d%s\n",
				i + 1, tests_final[i].model_path.c_str(), tests_final[i].validation_samples_path.c_str(), tests_final[i].filter_split,
				kp_str.c_str());

		}

		MedSamples &samples = tests_final[i].stored_samples;
		if (samples.idSamples.empty()) {
			MLOG("Loading validtaion samples from %s\n", tests_final[i].validation_samples_path.c_str());
			samples.read_from_file(tests_final[i].validation_samples_path);
			//check if need to filter
			if (tests_final[i].filter_split >= 0) {
				vector<MedIdSamples> sel_splt;
				for (size_t j = 0; j < samples.idSamples.size(); ++j)
					if (samples.idSamples[j].split == tests_final[i].filter_split)
						sel_splt.push_back(samples.idSamples[j]);
				samples.idSamples = move(sel_splt);
			}
		}
		fix_scores_probs(samples, model_result, rep_path, tests_final[i].model_path, pid_to_split_file);
		//has results in model_result
		string addition_split_info = "";
		if (tests_final.size() > 1) {
			string addition_name = get_filename_no_ext(tests_final[i].validation_samples_path);
			if (!tests_final[i].model_path.empty())
				addition_name += "." + get_filename_no_ext(tests_final[i].model_path);
			if (tests_final[i].filter_split >= 0)
				addition_name += ".split_" + to_string(tests_final[i].filter_split);
			addition_split_info = "." + addition_name;
		}
		test_preformace(model_result, test_kaplan_meier, kaplan_meier_time, fw, output + addition_split_info, min_bin_size, cases_weight, controls_weight, bin_settings, std_factor);
		all_tests.insert(all_tests.end(), model_result.begin(), model_result.end());
		if (!bt_params.empty()) {
			Calibration_Args cl_args;
			cl_args.bin_settings = bin_settings;
			cl_args.min_bin_size = min_bin_size;
			cl_args.cases_weight = cases_weight;
			cl_args.controls_weight = controls_weight;
			cl_args.calc_bins_once = calc_bins_once;
			MedSamples test_smpls;
			test_smpls.import_from_sample_vec(model_result);
			MedBootstrapResult res;
			bootstrap_cl_main(test_smpls, rep_path, json_model, bt_params, cohorts_file, cl_args, res);
			res.write_results_to_text_file(output + addition_split_info + ".bootstrap.pivot_txt");
			MLOG("Wrote file [%s]\n", (output + addition_split_info + ".bootstrap.pivot_txt").c_str());
			//Print graph for each cohort:
			if (!bootstrap_graphs_path.empty()) {
				boost::regex bt_points("^OBSERVED_PROB@PREDICTED_PROB_");
				boost::filesystem::create_directories(bootstrap_graphs_path);
				for (const auto &cohort_res : res.bootstrap_results)
				{
					string file_name = addition_split_info + "." + cohort_res.first + ".html";
					if (addition_split_info.empty())
						file_name = cohort_res.first + ".html";
					fix_filename_chars(&file_name, '_');
					string full_filename = bootstrap_graphs_path + path_sep() + file_name;
					const map<string, float> &c_res = cohort_res.second;
					stringstream ss;

					if (c_res.find("RMSE_Mean") != c_res.end()) {
						ss << "RMSE=" << c_res.at("RMSE_Mean") << " [" << c_res.at("RMSE_CI.Lower.95")
							<< " - " << c_res.at("RMSE_CI.Upper.95") << "]<br>";
					}
					if (c_res.find("R2_Mean") != c_res.end()) {
						ss << "R2=" << c_res.at("R2_Mean") << " [" << c_res.at("R2_CI.Lower.95")
							<< " - " << c_res.at("R2_CI.Upper.95") << "]<br>";
					}
					if (c_res.find("CalibrationIndex_Mean") != c_res.end()) {
						ss << "CalibrationIndex=" << c_res.at("CalibrationIndex_Mean") << " [" << c_res.at("CalibrationIndex_CI.Lower.95")
							<< " - " << c_res.at("CalibrationIndex_CI.Upper.95") << "]<br>";
					}


					vector<pair<float, float>> perfect_ref, graph_observed_calibration,
						ci_lower, ci_upper;
					boost::regex bt_neg("^NNEG@PREDICTED_PROB_");
					boost::regex bt_pos("^NPOS@PREDICTED_PROB_");
					map<float, float> bin_sizes;
					//scan c_res to build graph:
					for (const auto &it : c_res)
					{
						const string &m_name = it.first;
						if (boost::regex_search(m_name, bt_points)) {
							//fetch ref from name:
							float ref_val = fetch_ref(m_name);

							//fetch endswith _Mean, _CI.Lower.95, _CI.Upper.95
							if (boost::ends_with(m_name, "_Mean")) {
								//Also add ref
								perfect_ref.push_back(pair<float, float>(ref_val, ref_val));
								graph_observed_calibration.push_back(pair<float, float>(ref_val, it.second));
							}
							else if (boost::ends_with(m_name, "_CI.Lower.95")) {
								ci_lower.push_back(pair<float, float>(ref_val, it.second));
							}
							else if (boost::ends_with(m_name, "_CI.Upper.95")) {
								ci_upper.push_back(pair<float, float>(ref_val, it.second));
							}
						}
						//NNEG, NPOS - count bin size
						if (boost::regex_search(m_name, bt_neg) || boost::regex_search(m_name, bt_pos)) {
							if (boost::ends_with(m_name, "_Obs")) {
								float ref_val = fetch_ref(m_name);
								bin_sizes[ref_val] += it.second;
							}
						}
					}

					if (graph_observed_calibration.size() != bin_sizes.size()) {
						//Add missing info to obs if missing in the random sampling:
						for (size_t jj = 0; jj < graph_observed_calibration.size(); ++jj)
						{
							float val = graph_observed_calibration[i].first;
							if (bin_sizes.find(val) == bin_sizes.end())
								bin_sizes[val] = MED_MAT_MISSING_VALUE;
						}
					}
					vector<pair<float, float>> bin_s_vec;
					bin_s_vec.resize(bin_sizes.size());
					int ii = 0;
					for (auto it = bin_sizes.begin(); it != bin_sizes.end(); ++it) {
						bin_s_vec[ii].first = it->first;
						bin_s_vec[ii].second = it->second;
						++ii;
					}
					//sort by first num:
					sort(graph_observed_calibration.begin(), graph_observed_calibration.end(), comp_nums_graph);
					sort(perfect_ref.begin(), perfect_ref.end(), comp_nums_graph);
					sort(ci_lower.begin(), ci_lower.end(), comp_nums_graph);
					sort(ci_upper.begin(), ci_upper.end(), comp_nums_graph);
					sort(bin_s_vec.begin(), bin_s_vec.end(), comp_nums_graph);

					if (graph_observed_calibration.size() != ci_lower.size())
						MTHROW_AND_ERR("Error mismatch sizes in %s of observed and CI lower [%zu, %zu]\n",
							cohort_res.first.c_str(), graph_observed_calibration.size(), ci_lower.size());
					if (graph_observed_calibration.size() != ci_upper.size())
						MTHROW_AND_ERR("Error mismatch sizes in %s of observed and CI upper [%zu, %zu]\n",
							cohort_res.first.c_str(), graph_observed_calibration.size(), ci_upper.size());
					if (graph_observed_calibration.size() != bin_s_vec.size())
						MTHROW_AND_ERR("Error mismatch sizes in %s of observed and bin sizes [%zu, %zu]\n",
							cohort_res.first.c_str(), graph_observed_calibration.size(), bin_s_vec.size());
					if (graph_observed_calibration.size() != perfect_ref.size())
						MTHROW_AND_ERR("Error mismatch sizes in %s of observed and reference [%zu, %zu]\n",
							cohort_res.first.c_str(), graph_observed_calibration.size(), perfect_ref.size());
					vector<float> lower_ci_v(graph_observed_calibration.size()), upper_ci_v(graph_observed_calibration.size());
					for (size_t i = 0; i < lower_ci_v.size(); ++i)
						if (graph_observed_calibration[i].second == MED_MAT_MISSING_VALUE ||
							ci_lower[i].second == MED_MAT_MISSING_VALUE)
							lower_ci_v[i] = MED_MAT_MISSING_VALUE;
						else
							lower_ci_v[i] = graph_observed_calibration[i].second - ci_lower[i].second;
					for (size_t i = 0; i < upper_ci_v.size(); ++i)
						if (graph_observed_calibration[i].second == MED_MAT_MISSING_VALUE ||
							ci_upper[i].second == MED_MAT_MISSING_VALUE)
							upper_ci_v[i] = MED_MAT_MISSING_VALUE;
						else
							upper_ci_v[i] = ci_upper[i].second - graph_observed_calibration[i].second;

					ss << "Num_Bins=" << perfect_ref.size();
					string pref_txt = ss.str();

					plotCalibrationGraph(full_filename,
						perfect_ref, graph_observed_calibration, bin_s_vec,
						"Calibration graph", ss.str(), std_factor, lower_ci_v, upper_ci_v, true);
				}
			}
		}
	}
	//run again on aggregated if has multiple tests:
	if (tests_final.size() > 1) {
		medial::print::log_with_file(fw, "#####################BEGIN_TEST_ALL###################\n");
		medial::print::log_with_file(fw, "Test For all splits together\n");
		test_preformace(all_tests, test_kaplan_meier, kaplan_meier_time, fw, output + ".all", min_bin_size, cases_weight, controls_weight, bin_settings, std_factor);
		medial::print::log_with_file(fw, "#####################END_TEST_ALL#######################\n");
	}

}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;

	test_calibration(args.rep, args.tests, args.output, args.test_kaplan_meier, args.kaplan_meier_time,
		args.pid_splits_to_model_file, args.min_bin_size, args.cases_weight, args.controls_weight,
		args.pred_binning_arg, args.json_model, args.bt_params, args.cohorts_file, args.calc_bins_once,
		args.bootstrap_graphs, args.std_factor);
	return 0;
}