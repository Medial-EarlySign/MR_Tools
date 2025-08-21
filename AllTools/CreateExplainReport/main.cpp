#include "Cmd_Args.h"
#include <boost/filesystem.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/regex.hpp>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedProcessTools/MedProcessTools/ExplainWrapper.h>
#include <MedProcessTools/MedProcessTools/MedFeatures.h>
#include <fstream>
#include <random>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;


#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

//pretty print number based on best resolution
string print_number(double number) {
	char buff[100];
	int max_res = 6; //find resolution till max_res:
	int res = 0;
	double diff = 1e-5;
	//double diff = 0;
	double multi = 1;

	while (abs(lround(number * multi) / multi - number) > diff && res < max_res) {
		++res;
		multi *= 10;
	}
	string res_text;
	snprintf(buff, sizeof(buff), "%%2.%df", res);
	res_text = string(buff);

	snprintf(buff, sizeof(buff), res_text.c_str(), number);
	return string(buff);
}

class Representative_Results {
public:
	string feature_name = "";
	float value = 0;
	float contribution = 0;
	float precentage_contribution = -1;
	int num_in_group = 0;

	string clean_name() const
	{
		if (boost::starts_with(feature_name, "FTR_") && feature_name.find(".") != string::npos)
			return feature_name.substr(feature_name.find(".") + 1);
		return feature_name;
	}

	string to_string() const {
		stringstream s;
		s << clean_name() << "(" << print_number(value) << ")" << ":=" << print_number(contribution);
		if (precentage_contribution >= 0)
			s << "(" << medial::print::print_obj(precentage_contribution, "%2.2f%%") << ")";

		return s.str();
	}
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

string format_row(const string &grp_name, const vector<Representative_Results> &rep_name,
	double contrib, double norm_contrib, MedPidRepository &repo, bool expend_vals, bool expend_feat_vals) {
	char buff[5000];
	string clean_grp_name = grp_name;
	if (boost::starts_with(grp_name, "FTR_") && grp_name.find(".") != string::npos)
		clean_grp_name = grp_name.substr(grp_name.find(".") + 1);
	if (rep_name.empty())
		MTHROW_AND_ERR("Error format_row:: rep_name - can't be empty\n");
	//clear FTR and eliminate if no groups
	if (rep_name[0].num_in_group != 1) {
		snprintf(buff, sizeof(buff), "%s:=%s(%2.2f%%)",
			clean_grp_name.c_str(), print_number(contrib).c_str(), norm_contrib);
		stringstream ss;
		ss << string(buff);
		if (expend_vals) {
			string aliases = get_aliases(repo, clean_grp_name);
			ss << "\t" << aliases;
		}
		for (size_t i = 0; i < rep_name.size(); ++i) {
			ss << "\t" << rep_name[i].to_string();
			if (expend_feat_vals) {
				string aliases = get_aliases(repo, rep_name[i].clean_name(), true);
				ss << "\t" << aliases;
			}
		}
		return ss.str();
	}
	else { //group is single feature 
		const Representative_Results &r = rep_name[0]; //has only 1
		snprintf(buff, sizeof(buff), "%s(%s):=%s(%2.2f%%)",
			clean_grp_name.c_str(), print_number(r.value).c_str(), print_number(contrib).c_str(), norm_contrib);
		stringstream ss;
		ss << string(buff);
		if (expend_vals || expend_feat_vals) {
			string aliases = get_aliases(repo, clean_grp_name, true);
			ss << "\t" << aliases;
		}
		return ss.str();
	}

}

bool same_sign(float n1, float n2) {
	return n1 * n2 > 0;
}

double contrib_match(float group, float v) {
	if (same_sign(group, v))
		return abs(v); //wants to maximize
	else //wants to minimize abs value, closest to zero. so maximize minus
		return -abs(v);
}

//based on single contrib mat - finds in a specific row the best single feature
void find_representative(const MedMat<float> &single_contrib, const map<string, vector<float>> &unorm_features,
	int obs_num, const vector<string> &features_names, const ExplainProcessings &processings,
	const string &group_search_first, float grp_contirb,
	const Representative_Group_Settings &sett, vector<Representative_Results> &res) {

	int feat_cnt = 0;
	for (const vector<int> &inds : processings.group2Inds)
		for (int ind : inds)
			if (feat_cnt < ind)
				feat_cnt = ind;
	++feat_cnt; //features indexes start from 0
	//if (feat_cnt < features_names.size())
	//	++feat_cnt; //for b0 const

	if (feat_cnt != features_names.size())
		MTHROW_AND_ERR("Error mismatch in number of features. processing has %d, matrix has %zu\n",
			feat_cnt, features_names.size());
	if (single_contrib.ncols != features_names.size())
		if (single_contrib.ncols - 1 != features_names.size())
			MTHROW_AND_ERR("Error sizes mismatch. single_contrib(%d), features_names(%zu)\n",
			(int)single_contrib.ncols, features_names.size());

	//create sorted_features for this row:
	vector<pair<int, float>> feat_contrib(features_names.size());
	for (int i = 0; i < feat_contrib.size(); ++i)
	{
		feat_contrib[i].first = i;
		feat_contrib[i].second = single_contrib(obs_num, i);
	}
	sort(feat_contrib.begin(), feat_contrib.end(), [](const pair<int, float> &c1, const pair<int, float> &c2)
	{
		return abs(c1.second) > abs(c2.second);
	});
	vector<int> sorted_features(features_names.size()); //contains index from "features_names"
	for (size_t i = 0; i < sorted_features.size(); ++i)
		sorted_features[i] = feat_contrib[i].first;

	//use groups:
	if (processings.groupName2Inds.find(group_search_first) == processings.groupName2Inds.end())
		MTHROW_AND_ERR("Error, can't find group %s in ModelExplainer processings\n", group_search_first.c_str());
	const vector<int> &ind_opts = processings.groupName2Inds.at(group_search_first);
	vector<bool> ind_mask(sorted_features.size());
	for (size_t i = 0; i < ind_opts.size(); ++i)
		ind_mask[ind_opts[i]] = true;

	float tot_sum = 0, curr_sum = 0;
	int num_in_grp = (int)ind_opts.size();
	for (int i = 0; i < sorted_features.size(); ++i)
		if (ind_mask[sorted_features[i]]) {
			float c = single_contrib(obs_num, sorted_features[i]);
			if (!sett.only_same_direction || same_sign(grp_contirb, c))
				tot_sum += abs(c);
		}

	double best_contrib_val = 0;
	int best_contrib_idx = -1;
	for (int i = 0; i < sorted_features.size(); ++i)
		if (ind_mask[sorted_features[i]]) {
			Representative_Results r;
			r.num_in_group = num_in_grp;
			r.feature_name = features_names[sorted_features[i]];
			r.contribution = single_contrib(obs_num, sorted_features[i]);
			//if forced to use only_same_direction and not same direction - skip
			if (!sett.only_same_direction || same_sign(grp_contirb, r.contribution)) {
				float curr_sum_before = 0;
				if (tot_sum > 0) {
					r.precentage_contribution = 100 * abs(r.contribution) / tot_sum;
					curr_sum_before = curr_sum / tot_sum;
				}
				curr_sum += abs(r.contribution);
				if (res.size() < sett.min_count || (tot_sum > 0 && curr_sum_before < sett.sum_ratio)) {
					//find value:
					if (unorm_features.find(r.feature_name) == unorm_features.end()) {
						MWARN("Error can't find feature %s in unorm_mat, options:\n",
							r.feature_name.c_str());
						int feat_cnt = 1;
						for (const auto &it : unorm_features) {
							MWARN("(%d) %s\n", feat_cnt, it.first.c_str());
							++feat_cnt;
						}
						MTHROW_AND_ERR("Error can't find feature %s in unorm_mat.\n",
							r.feature_name.c_str());
					}
					r.value = unorm_features.at(r.feature_name)[obs_num];
					res.push_back(move(r));
				}
			}

			// To avoid empty selection:
			if (sett.only_same_direction) {
				if (best_contrib_idx < 0 || contrib_match(grp_contirb, r.contribution) > best_contrib_val) {
					best_contrib_idx = sorted_features[i];
					best_contrib_val = contrib_match(grp_contirb, r.contribution);
				}
			}
		}

	if (res.empty() && sett.only_same_direction && best_contrib_idx > 0) {
		//take best candidate when no same direction exists:
		Representative_Results r;
		r.num_in_group = num_in_grp;
		r.feature_name = features_names[best_contrib_idx];
		r.contribution = 0;
		r.precentage_contribution = 0;

		if (unorm_features.find(r.feature_name) == unorm_features.end()) {
			MWARN("Error can't find feature %s in unorm_mat, options:\n",
				r.feature_name.c_str());
			int feat_cnt = 1;
			for (const auto &it : unorm_features) {
				MWARN("(%d) %s\n", feat_cnt, it.first.c_str());
				++feat_cnt;
			}
			MTHROW_AND_ERR("Error can't find feature %s in unorm_mat.\n",
				r.feature_name.c_str());
		}
		r.value = unorm_features.at(r.feature_name)[obs_num];
		res.push_back(move(r));

	}

	if (res.empty())
		MTHROW_AND_ERR("Error feature or group %s not found\n", group_search_first.c_str());
}

float transform_contrib(float b0, float contrib) {
	//return contrib;
	return (1 + exp(b0)) / (1 + exp(b0 - contrib));
}

void prepare_rep_for_apply(MedPidRepository &rep, const string &rep_fname,
	MedModel &model, const MedSamples &samples) {
	unordered_set<string> req_sigs;
	vector<string> rsigs;

	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_fname.c_str());
	model.fit_for_repository(rep);
	model.get_required_signal_names(req_sigs);
	for (auto &s : req_sigs) rsigs.push_back(s);

	vector<int> pids;

	samples.get_ids(pids);

	if (rep.read_all(rep_fname, pids, rsigs) < 0)
		MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not read repository %s\n", rep_fname.c_str());
}

void apply_without_imputer_normalizer(MedModel &model, MedSamples &sample_to_apply, MedPidRepository &repo,
	MedFeatures &non_norm_features) {
	vector<FeatureProcessor *> keep_p;
	vector<bool> filter_mask(FTR_PROCESS_LAST);
	filter_mask[FTR_PROCESS_NORMALIZER] = true;
	filter_mask[FTR_PROCESS_IMPUTER] = true;
	filter_mask[FTR_PROCESS_ITERATIVE_IMPUTER] = true;
	filter_mask[FTR_PROCESS_PREDICTOR_IMPUTER] = true;

	for (size_t i = 0; i < model.feature_processors.size(); ++i)
	{
		if (model.feature_processors[i]->processor_type == FTR_PROCESS_MULTI) {
			MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(model.feature_processors[i]);
			vector<FeatureProcessor *> keep_internal_p;
			for (size_t j = 0; j < multi->processors.size(); ++j) {
				if (!filter_mask[multi->processors[j]->processor_type])
					keep_internal_p.push_back(multi->processors[j]);
				else {
					delete multi->processors[j];
					multi->processors[j] = NULL;
				}
			}
			if (!keep_internal_p.empty()) {
				MultiFeatureProcessor *multi_new = new MultiFeatureProcessor;
				multi_new->duplicate = multi->duplicate;
				multi_new->processors = move(keep_internal_p);
				keep_p.push_back(multi_new);
			}

			//clear mem
			multi->processors.clear(); //already cleared what's neede inside
			delete multi;
			model.feature_processors[i] = NULL;
		}
		else {
			if (!filter_mask[model.feature_processors[i]->processor_type])
				keep_p.push_back(model.feature_processors[i]);
			else {
				delete model.feature_processors[i];
				model.feature_processors[i] = NULL;
			}

		}
	}
	model.feature_processors = keep_p;
	if (model.apply(repo, sample_to_apply, MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS) < 0)
		MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");
	non_norm_features = move(model.features);
}

int main(int argc, char *argv[]) {
	Program_Args args;
	int exit_code = args.parse_parameters(argc, argv);
	if (exit_code == -1)
		return 0;
	if (exit_code < 0)
		MTHROW_AND_ERR("unable to parse arguments\n");
	random_device rd;
	mt19937 gen(rd());

	MedSamples samples;
	samples.read_from_file(args.samples_path);

	MedModel full_med;
	if (!args.change_model_file.empty())
		full_med.read_from_file_with_changes(args.model_path, args.change_model_file);
	else {
		if (full_med.read_from_file(args.model_path) < 0) {
			MERR("Flow: get_model_preds: could not read model file %s\n", args.model_path.c_str());
			return -1;
		}
		if (!args.change_model_init.empty()) {
			ChangeModelInfo ch;
			ch.init_from_string(args.change_model_init);
			full_med.change_model(ch);
		}
	}


	PostProcessor *exp_p = NULL;
	for (PostProcessor *pp : full_med.post_processors)
	{
		if (pp->processor_type != PostProcessorTypes::FTR_POSTPROCESS_MULTI) {
			if (ModelExplainer* explainer_pointer = dynamic_cast<ModelExplainer*>(pp))
			{
				if (exp_p != NULL)
					MTHROW_AND_ERR("Error has multiple explainers\n");
				exp_p = explainer_pointer;
			}
		}
		else {
			for (PostProcessor *internel_pp : static_cast<MultiPostProcessor *>(pp)->post_processors)
			{
				if (ModelExplainer* explainer_pointer = dynamic_cast<ModelExplainer*>(internel_pp))
				{
					if (exp_p != NULL)
						MTHROW_AND_ERR("Error has multiple explainers\n");
					exp_p = explainer_pointer;
				}
			}
		}
	}
	if (exp_p == NULL)
		MTHROW_AND_ERR("Please provide model with PostProcessor of ModelExplainer\n");
	ModelExplainer *explainer_pointer = static_cast<ModelExplainer *>(exp_p);
	//force to print not in json:
	explainer_pointer->global_explain_params.store_as_json = false;

	if (args.transform_contribution)
		explainer_pointer->filters.max_count = 0; // force to get all results

	MedPidRepository repo;
	prepare_rep_for_apply(repo, args.rep, full_med, samples);

	if (full_med.apply(repo, samples, MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_END) < 0)
		MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");

	MedFeatures final_mat = move(full_med.features);

	// feature importance print
	//vector<float> features_scores;
	MedMat<float> mat_vals, single_contrib_vals;
	final_mat.get_as_matrix(mat_vals);
	//for single - to handle groups
	full_med.predictor->calc_feature_contribs(mat_vals, single_contrib_vals);

	//sort and print features
	vector<string> feat_names;
	final_mat.get_feature_names(feat_names);
	if (feat_names.size() != single_contrib_vals.ncols) {
		if (feat_names.size() + 1 == single_contrib_vals.ncols) {
			//feat_names.push_back("b0_const"); //don't add bias
		}
		else
			MTHROW_AND_ERR("Got %zu features and %d scores in predictor to used features.. giving names by order\n",
				feat_names.size(), (int)single_contrib_vals.ncols);
		//print report - for each row:

		ofstream fw_report(args.output_path);
		if (!fw_report.good())
			MTHROW_AND_ERR("Error can't open %s report file for writing\n", args.output_path.c_str());

		fw_report << "pid" << "\t" << "time" << "\t" << "outcome" << "\t" << "pred_0";
		fw_report << "\t" << explainer_pointer->global_explain_params.attr_name;
		if (args.expend_dict_names)
			fw_report << "\t" << "Code_Description";
		fw_report << "\t" << "Specific_Feature_Inside_Group(optional)..." << "\n";

		int nSamples = (int)final_mat.samples.size();
		unordered_set<string> skip_bias_names = { "b0", "Prior_Score", "b0_const" };
		const vector<MedSample> &samples_vec = final_mat.samples;

		MedFeatures unorm_features;
		MedSamples sample_to_apply;
		sample_to_apply.import_from_sample_vec(samples_vec);
		apply_without_imputer_normalizer(full_med, sample_to_apply, repo, unorm_features);
		string url_template = args.viewer_url_base;
		//find prior:
		float prior_b0 = MED_MAT_MISSING_VALUE;
		if (args.transform_contribution) {
			bool found_b0 = false;
			for (const auto &it : final_mat.samples.front().attributes)
			{
				string clean_name = it.first;
				if (clean_name.find("::") != string::npos) {
					clean_name = clean_name.substr(clean_name.find("::") + 2);
					if (skip_bias_names.find(clean_name) != skip_bias_names.end()) {
						prior_b0 = it.second;
						found_b0 = true;
						break;
					}
				}
			}
			if (!found_b0)
				MTHROW_AND_ERR("Error can't find prior b0 in explaining features\n");
			MLOG("FOUND b0=%f\n", prior_b0);
		}

		for (size_t i = 0; i < nSamples; ++i)
		{
			//select order of mats:
			int pid = samples_vec[i].id;
			//first idx  is explain, second is result num


			MedFeatures &mat = final_mat;
			vector<pair<string, float>> curr_a;
			for (const auto &it : mat.samples[i].attributes)
			{
				string clean_name = it.first;
				if (clean_name.find("::") != string::npos) {
					clean_name = clean_name.substr(clean_name.find("::") + 2);
					if (skip_bias_names.find(clean_name) != skip_bias_names.end())
						continue;
					float cont = it.second;
					curr_a.push_back(pair<string, float>(clean_name, cont)); //feature name / group => contrib
				}
			}
			sort(curr_a.begin(), curr_a.end(), [](const pair<string, float> &a, const pair<string, float>&b) {
				return abs(a.second) > abs(b.second);
			});
			//save also normalized contribution: 
			vector<string> explain_feat_name(curr_a.size());
			vector<vector<Representative_Results>> rep_name(curr_a.size());
			vector<double> explain_contribs(curr_a.size()), explain_norm_contribs(curr_a.size());
			double tot_sum = 0;

			for (size_t k = 0; k < curr_a.size(); ++k)
				if (skip_bias_names.find(curr_a[k].first) == skip_bias_names.end())
					tot_sum += abs(curr_a[k].second);
			if (tot_sum > 0)
				for (size_t k = 0; k < curr_a.size(); ++k)
					explain_norm_contribs[k] = double(100.0 * abs(curr_a[k].second) / tot_sum); //in percentage - sum to 100

			if (curr_a.size() > args.take_max) {
				curr_a.resize(args.take_max);
				explain_norm_contribs.resize(args.take_max);
				rep_name.resize(curr_a.size());
				explain_feat_name.resize(curr_a.size());
				explain_contribs.resize(curr_a.size());
			}
			//find_representative

			for (int k = 0; k < curr_a.size(); ++k)
			{
				vector<Representative_Results> repr_res;
				find_representative(single_contrib_vals, unorm_features.data, (int)i, feat_names,
					explainer_pointer->processing, curr_a[k].first, curr_a[k].second, args.rep_settings, repr_res);

				rep_name[k] = move(repr_res);
			}

			//collect values:	
			for (size_t k = 0; k < curr_a.size(); ++k) {
				explain_feat_name[k] = curr_a[k].first;
				explain_contribs[k] = (double)curr_a[k].second;
				if (args.transform_contribution)
					explain_contribs[k] = (double)transform_contrib(prior_b0, curr_a[k].second);
			}

			//print in each row: curr_a[k].first, curr_a[k].second, norm_contribs[k], rep_feats[k], rep_vals[k]
			//print each explain row:
			int explain_cnt = (int)explain_feat_name.size();

			for (size_t k = 0; k < explain_cnt; ++k)
			{
				fw_report << pid << "\t" << samples_vec[i].time
					<< "\t" << samples_vec[i].outcome << "\t" << samples_vec[i].prediction[0];
				//print for row k
				const vector<Representative_Results> &rep_res = rep_name[k];

				fw_report << "\t" << format_row(explain_feat_name[k],
					rep_res, explain_contribs[k],
					explain_norm_contribs[k], repo, args.expend_dict_names, args.expend_feature_names);

				fw_report << "\n";
			}
			fw_report << "SCORES" << "\t" << pid << "\t" << samples_vec[i].time << "\t" << "###" << "\n";
			if (!url_template.empty()) {
				char buff_temp[5000];
				snprintf(buff_temp, sizeof(buff_temp), url_template.c_str(),
					pid, samples_vec[i].time);
				string url_pid = string(buff_temp);
				fw_report << "PID_VIEWER_URL" << "\t" << url_pid << "\n";
			}
			fw_report << "\n";
		}
		fw_report.close();
		MLOG("Wrote %s\n", args.output_path.c_str());
		return 0;
	}

	return 0;
}