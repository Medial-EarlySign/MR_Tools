#include <random>
#include <string>
#include "Logger/Logger/Logger.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "MedUtils/MedUtils/MedRegistry.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include <boost/filesystem.hpp>
#include "Cmd_Args.h"
#include "Helper.h"

#include <fenv.h>
#ifndef  __unix__
#pragma float_control( except, on )
#endif

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

using namespace std;

float get_action_value(float val, float val_near, float val_far, float val_con, const ProgramArgs &args) {
	float res = MED_MAT_MISSING_VALUE;
	if (args.action_type == 0) {
		//pos
		if (val >= args.threshold_drug_prec_case_min && val <= args.threshold_drug_prec_case_max) {
			res = 1; //case
		}
		//neg
		else if (val >= args.threshold_drug_prec_control_min && val <= args.threshold_drug_prec_control_max) {
			res = 0;
		}
	}
	else if (args.action_type == 1) {
		//pos
		if (val >= args.threshold_drug_prec_case_min && val <= args.threshold_drug_prec_case_max) {
			res = 1; //case
		}
		//neg
		if (val_near >= args.threshold_drug_prec_control_min && val_near <= args.threshold_drug_prec_control_max && val_far <= 0.02) {
			res = 0;
		}
	}
	else if (args.action_type == 2) {
		//pos
		if (val >= args.threshold_drug_prec_case_min && val <= args.threshold_drug_prec_case_max && val_con <= 0) {
			res = 1; //case
		}
		//neg
		else if (val_con >= args.threshold_drug_prec_control_min && val_con <= args.threshold_drug_prec_control_max && val <= 0) {
			res = 0;
		}
	}

	//fprintf(stderr, "action_type:%i val:%f val_near:%f , val_far:%f val_con:%f res:%f \n", args.action_type, val, val_near, val_far, val_con, res);
	//getchar();

	return res;
}

void read_active_periods(const string &complete_reg, const string &complete_reg_sig, const string &complete_reg_type,
	const string &complete_reg_args, const string &rep_path, MedPidRepository &rep,
	medial::repository::fix_method registry_fix_method,
	MedRegistry *&active_reg) {
	//three options:
	//1. from file complete_reg
	//2. from signal complete_reg_sig
	//3. from init line: complete_reg_type, complete_reg_args => stores to save_censor_path

	if (!complete_reg.empty()) {
		MLOG("Complete Active periods using %s\n", complete_reg.c_str());
		active_reg = MedRegistry::make_registry("keep_alive");
		active_reg->read_text_file(complete_reg);
		active_reg->clear_create_variables();
	}
	else {
		if (!complete_reg_sig.empty()) {
			active_reg = MedRegistry::make_registry("keep_alive");
			MLOG("Complete Active periods using Signal %s\n", complete_reg_sig.c_str());
			MedRepository rep2;
			vector<int> all_pids;
			vector<string> sigs_read = { complete_reg_sig };
			if (rep2.read_all(rep_path, all_pids, sigs_read) < 0)
				MTHROW_AND_ERR("Error reading repository %s\n", rep_path.c_str());
			int sid = rep2.sigs.sid(complete_reg_sig);
			if (rep2.sigs.Sid2Info[sid].n_time_channels != 2)
				MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
					complete_reg_sig.c_str(), rep2.sigs.Sid2Info[sid].n_time_channels);
			for (size_t i = 0; i < rep2.pids.size(); ++i)
			{
				MedRegistryRecord rec;
				rec.pid = rep2.pids[i];
				rec.registry_value = 1;

				UniversalSigVec usv;
				rep2.uget(rec.pid, sid, usv);
				for (int k = 0; k < usv.len; ++k)
				{
					rec.start_date = usv.Time(k, 0);
					rec.end_date = usv.Time(k, 1);
					active_reg->registry_records.push_back(rec);
				}
			}
			active_reg->clear_create_variables();
		}
		else {
			//try with init arg
			if (!complete_reg_args.empty() && !complete_reg_type.empty()) {
				vector<int> pids = {};
				MLOG("Loading censor registry\n");
				if (rep.signal_fnames.empty())
					if (rep.init(rep_path) < 0)
						MTHROW_AND_ERR("can't read repository %s\n", rep_path.c_str());
				MedModel empty_model;
				active_reg = create_registry_full_with_rep(complete_reg_type, complete_reg_args, rep_path,
					empty_model, medial::repository::fix_method::none, rep);
			}
		}
	}
}

void complete_control_active_periods(MedRegistry &reg, const string &complete_reg,
	const string &complete_reg_sig, const string &rep_path) {
	if (complete_reg.empty() && complete_reg_sig.empty())
		return;
	MedRegistry active_reg;
	if (!complete_reg.empty()) {
		MLOG("Complete Active periods using %s\n", complete_reg.c_str());
		active_reg.read_text_file(complete_reg);
	}
	else {
		MLOG("Complete Active periods using Signal %s\n", complete_reg_sig.c_str());
		MedRepository rep;
		vector<int> all_pids;
		vector<string> sigs_read = { complete_reg_sig };
		if (rep.read_all(rep_path, all_pids, sigs_read) < 0)
			MTHROW_AND_ERR("Error reading repository %s\n", rep_path.c_str());
		int sid = rep.sigs.sid(complete_reg_sig);
		if (rep.sigs.Sid2Info[sid].n_time_channels != 2)
			MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
				complete_reg_sig.c_str(), rep.sigs.Sid2Info[sid].n_time_channels);
		for (size_t i = 0; i < rep.pids.size(); ++i)
		{
			MedRegistryRecord rec;
			rec.pid = rep.pids[i];
			rec.registry_value = 1;

			UniversalSigVec usv;
			rep.uget(rec.pid, sid, usv);
			for (int k = 0; k < usv.len; ++k)
			{
				rec.start_date = usv.Time(k, 0);
				rec.end_date = usv.Time(k, 1);
				active_reg.registry_records.push_back(rec);
			}
		}

	}
	medial::registry::complete_active_period_as_controls(reg.registry_records, active_reg.registry_records);
}

int main(int argc, char *argv[]) {
#if defined(__unix__)
	feenableexcept(FE_DIVBYZERO | FE_INVALID | FE_OVERFLOW);
#endif
	random_device rd;
	mt19937 gen(rd());
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;
	if (!args.repo_path.empty())
		medial::repository::set_global_time_unit(args.repo_path);
	MLOG("running on %s\n", args.output_folder.c_str());

	string RepositoryPath = args.repo_path;
	//params:
	char buff[5000];
	//int rep_max_year = args.repo_max_date;
	string sampler_type = args.sampler_type;
	string sampler_init = args.sampler_init;

	string output_folder = args.output_folder; //put_test_name
	string json_model = args.json_model;
	string feature_action_name_search = args.action_name_search;
	string feature_action_name_search_con = args.action_name_search_con;
	//float threshold_drug_prec = args.threshold_drug_prec;
	//float threshold_drug_untreat = args.threshold_drug_prec_con;
	string confounders_name_list_path = args.confounders_file;

	//Let's create Cancer registry
	//string registry_cfg_init = string(buff);
	string registry_cfg_init = args.registry_cfg_init;
	MedRegistry loaded_reg;
	MedRegistry *registry = &loaded_reg;
	MedPidRepository repo;
	if (!args.registry_path.empty()) {
		registry->read_text_file(args.registry_path);
		if (args.use_active_for_reg_outcome && (!args.registry_active_periods.empty() || !args.registry_active_periods_sig.empty()))
			complete_control_active_periods(*registry, args.registry_active_periods, args.registry_active_periods_sig, args.repo_path);
	}
	else {
		MedModel model_rep_proc;
		if (!args.registry_processors.empty())
			model_rep_proc.init_from_json_file(args.registry_processors);
		registry = create_registry_full_with_rep(args.registry_type, args.registry_cfg_init, args.repo_path,
			model_rep_proc, args.registry_conflicts_method, repo);

		if (!args.registry_active_periods.empty() || !args.registry_active_periods_sig.empty())
			complete_control_active_periods(*registry, args.registry_active_periods, args.registry_active_periods_sig, args.repo_path);
	}

	medial::print::print_reg_stats(registry->registry_records);
	boost::filesystem::create_directories(output_folder.c_str());
	MedRegistry *censor_reg = NULL;
	read_active_periods(args.registry_active_periods, args.registry_active_periods_sig, args.censor_registry_type,
		args.censor_registry_init, args.repo_path, repo, medial::repository::fix_method::none, censor_reg);
	//reg_outcome.write_text_file(args.output_folder + path_sep() + "registry.reg");
	//Let's sample from Cancer registry in years 2007-2015 random date in each year
	MedSamples samples;
	MedSamplingStrategy *sampler = MedSamplingStrategy::make_sampler(sampler_type, sampler_init);
	sampler->filtering_params = args.filtering_params;
	vector<int> pids_for_samplers;
	registry->get_pids(pids_for_samplers);
	vector<string> sigs = { "BDATE" };
	MedRepository rep_sampler;
	if (rep_sampler.read_all(args.repo_path, pids_for_samplers, sigs) < 0)
		MTHROW_AND_ERR("Can't read repo %s for init sampler\n", args.repo_path.c_str());
	sampler->init_sampler(rep_sampler);
	MedLabels labeler(args.labeling_args);
	labeler.prepare_from_registry(registry->registry_records, censor_reg == NULL ? NULL : &censor_reg->registry_records);
	labeler.create_samples(sampler, samples);
	delete sampler;
	MLOG("Done Sampling has %d samples on %d patients...\n", samples.nSamples(), samples.idSamples.size());

	//filter years:
	if (args.min_year_filter > 0 || args.max_year_filter < 3000) {
		MLOG("filtering by prediction year\n");
		MedSamples after_filt;
		after_filt.time_unit = samples.time_unit;
		for (size_t i = 0; i < samples.idSamples.size(); ++i)
		{
			vector<MedSample> filt_smps;
			for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j)
				if (int(samples.idSamples[i].samples[j].time / 10000) >= args.min_year_filter
					&& int(samples.idSamples[i].samples[j].time / 10000) <= args.max_year_filter)
					filt_smps.push_back(samples.idSamples[i].samples[j]);

			if (!filt_smps.empty()) {
				MedIdSamples smp_id(samples.idSamples[i].id);
				smp_id.samples.swap(filt_smps);
				after_filt.idSamples.push_back(smp_id);
			}
		}

		samples.idSamples.swap(after_filt.idSamples);
	}

	medial::print::print_samples_stats(samples);
	medial::print::print_by_year(samples, 1, false, true);
	//Let's prepare files for the tool to run:

	MedFeatures dataMat;

	load_matrix_from_json(samples, RepositoryPath, json_model, dataMat);
	vector<string> feature_names;
	dataMat.get_feature_names(feature_names);

	int pos;
	string full_action_name_con, full_action_name_far, full_action_name_near;
	pos = find_in_feature_names(feature_names, feature_action_name_search);	if (pos < 0) { medial::print::print_vec(feature_names, "All Feature Names", "\n"); MTHROW_AND_ERR("Unable to find \"%s\" in features\n", feature_action_name_search.c_str()); }
	string &full_action_name = feature_names[pos];

	if (args.action_type == 1) {
		pos = find_in_feature_names(feature_names, args.action_name_search_far); if (pos < 0) { medial::print::print_vec(feature_names, "All Feature Names", "\n"); MTHROW_AND_ERR("Unable to find \"%s\" in features\n", args.action_name_search_far.c_str()); }
		full_action_name_far = feature_names[pos];

		pos = find_in_feature_names(feature_names, args.action_name_search_near); if (pos < 0) { medial::print::print_vec(feature_names, "All Feature Names", "\n"); MTHROW_AND_ERR("Unable to find \"%s\" in features\n", args.action_name_search_near.c_str()); }
		full_action_name_near = feature_names[pos];
	}


	if (args.action_type == 2) {
		if (args.action_name_search_con.empty())
			MTHROW_AND_ERR("action_type =2 need action_name_search_con");

		pos = find_in_feature_names(feature_names, args.action_name_search_con); if (pos < 0) { medial::print::print_vec(feature_names, "All Feature Names", "\n"); MTHROW_AND_ERR("Unable to find \"%s\" in features\n", args.action_name_search_con.c_str()); }
		full_action_name_con = feature_names[pos];
	}


	vector<int> sel_idx;
	if (!args.filter_by_column.empty()) {

		vector<string> fields;
		split(fields, args.filter_by_column, boost::is_any_of(";"));
		for (int kk = 0; kk < fields.size(); kk++) {
			fprintf(stderr, "****filter: %s **** \n", fields[kk].c_str());
			vector<string> filter_cond;
			split(filter_cond, fields[kk], boost::is_any_of(","));
			if (fields.size() != 3)
				MTHROW_AND_ERR("Error in filter_by_column - expecting 3 token seperated by \",\" feature_name,operator,cutoff");
			string my_feature = filter_cond[0];
			string my_operator = filter_cond[1];
			string my_cutoff = filter_cond[2];

			pos = find_in_feature_names(feature_names, my_feature); if (pos < 0) { medial::print::print_vec(feature_names, "All Feature Names", "\n"); MTHROW_AND_ERR("Unable to find filter in features\n"); }
			string &filter_name = feature_names[pos];
			sel_idx.clear();
			MLOG("before filtering population %zu  %s \n", dataMat.samples.size(), fields[kk].c_str());
			for (size_t i = 0; i < dataMat.samples.size(); ++i) {
				if (my_operator == "<") {
					if (dataMat.data[filter_name][i] < stof(my_cutoff))
						sel_idx.push_back((int)i);
				}
				else if (my_operator == "=") {
					if (dataMat.data[filter_name][i] == stof(my_cutoff))
						sel_idx.push_back((int)i);
				}
				else if (my_operator == ">") {
					if (dataMat.data[filter_name][i] > stof(my_cutoff))
						sel_idx.push_back((int)i);
				}
			}
			medial::process::filter_row_indexes(dataMat, sel_idx);
			MLOG("after filtering population %zu\n", dataMat.samples.size());
		}
	}
	fprintf(stderr, "after filter column .... \n");



	//Let's filter samples that took the drug in the history:
	if (args.filter_took_drug_before) {
		sel_idx.clear();
		int pos_hist = find_in_feature_names(feature_names, args.action_name_search_his);
		if (pos_hist < 0) {
			//print_str_vec(feature_names, "All Feature Names");
			medial::print::print_vec(feature_names, "All Feature Names", "\n");
			MTHROW_AND_ERR("Unable to find \"%s\" in features\n",
				args.action_name_search_his.c_str());
		}
		string &history_action_name = feature_names[pos_hist];
		int before_sz = (int)dataMat.samples.size();

		for (size_t i = 0; i < dataMat.samples.size(); ++i)
			if (dataMat.data[history_action_name][i] <= 0)
				sel_idx.push_back((int)i);
		medial::process::filter_row_indexes(dataMat, sel_idx);
		MLOG("filtering samples of drug tooked in history. sample_size was %d and now %zu\n",
			before_sz, dataMat.samples.size());
	}
	fprintf(stderr, "after filter filter_took_drug_before .... \n");

	if (args.filter_took_drug_after) {
		sel_idx.clear();
		int pos_fut = find_in_feature_names(feature_names, args.action_name_search_fut);
		if (pos_fut < 0) { medial::print::print_vec(feature_names, "All Feature Names", "\n"); MTHROW_AND_ERR("Unable to find \"%s\" in features\n", args.action_name_search_his.c_str()); }
		string &future_action_name = feature_names[pos_fut];
		MLOG("before filtering samples of drug tooked in future. sample_size was %zu\n", dataMat.samples.size());
		for (size_t i = 0; i < dataMat.samples.size(); ++i)
			if (dataMat.data[future_action_name][i] <= 0)
				sel_idx.push_back((int)i);
		medial::process::filter_row_indexes(dataMat, sel_idx);
		MLOG("after filtering samples of drug tooked in future. sample_size was %zu\n", dataMat.samples.size());
	}

	fprintf(stderr, "after filter filter_took_drug_after .... \n");



	//filter middle treatment:
	MLOG("before filtering unconsensus treated no treatment, sample_size was %zu\n", dataMat.samples.size());
	sel_idx.clear();
	float val, val_near, val_far, val_con;
	for (size_t i = 0; i < dataMat.samples.size(); ++i) {
		val = dataMat.data[full_action_name][i];
		val_near = val; if (args.action_type == 1) val_near = dataMat.data[full_action_name_near][i];
		val_far = val; if (args.action_type == 1) val_far = dataMat.data[full_action_name_far][i];
		val_con = val; if (args.action_type == 2) val_con = dataMat.data[full_action_name_con][i];
		if (get_action_value(val, val_near, val_far, val_con, args) != MED_MAT_MISSING_VALUE)  sel_idx.push_back((int)i);
	}
	medial::process::filter_row_indexes(dataMat, sel_idx);
	MLOG("after filtering unconsensus treated no treatment, sample_size is  %zu\n", dataMat.samples.size());

	int before_sz;
	//filter once for patient,outcome:
	if (args.filter_pid_outcome) {
		before_sz = (int)dataMat.samples.size();

		sel_idx.clear();
		unordered_map<string, vector<int>> grp_to_idx;
		for (size_t i = 0; i < dataMat.samples.size(); ++i)
			grp_to_idx[to_string(dataMat.samples[i].id) + "_" +
			to_string(int(dataMat.samples[i].outcome > 0))].push_back((int)i);

		for (auto it = grp_to_idx.begin(); it != grp_to_idx.end(); ++it) {
			uniform_int_distribution<> select_ind(0, (int)it->second.size() - 1);
			sel_idx.push_back(it->second[select_ind(gen)]);
		}
		medial::process::filter_row_indexes(dataMat, sel_idx);
		MLOG("filtering one sample for each patient,outcome. sample_size was %d, now %zu\n",
			before_sz, dataMat.samples.size());
	}
	//match by year:
	if (args.match_year_price_ratio > 0)
		match_by_year(dataMat, args.match_year_price_ratio, 1, true);

	MLOG("finished with %zu samples\n", dataMat.samples.size());
	dataMat.write_to_file(output_folder + path_sep() + "test_matrix.bin");



	MLOG("Creating action with %s feature\n", full_action_name.c_str());
	ofstream fw(output_folder + "/patient.action");
	if (!fw.good())
		MTHROW_AND_ERR("unable to open file %s for writing",
		(output_folder + "/patient.action").c_str());


	for (size_t i = 0; i < dataMat.samples.size(); ++i) {
		val = dataMat.data[full_action_name][i];
		val_near = val; if (args.action_type == 1) val_near = dataMat.data[full_action_name_near][i];
		val_far = val; if (args.action_type == 1) val_far = dataMat.data[full_action_name_far][i];
		val_con = val; if (args.action_type == 2) val_con = dataMat.data[full_action_name_con][i];
		if (get_action_value(val, val_near, val_far, val_con, args) == 1) {
			fw << "1\n";
		}
		else {
			fw << "0\n";
		}
	}
	fw.close();


	fw.open(output_folder + "/patient.groups");
	if (!fw.good())
		MTHROW_AND_ERR("unable to open file %s for writing",
		(output_folder + "/patient.groups").c_str());
	for (size_t i = 0; i < dataMat.samples.size(); ++i) {
		val = dataMat.data[full_action_name][i];
		val_near = val; if (args.action_type == 1) val_near = dataMat.data[full_action_name_near][i];
		val_far = val; if (args.action_type == 1) val_far = dataMat.data[full_action_name_far][i];
		val_con = val; if (args.action_type == 2) val_con = dataMat.data[full_action_name_con][i];
		if (get_action_value(val, val_near, val_far, val_con, args) == 1)
			fw << "Treated\n";
		else
			fw << "Untreated\n";
	}
	fw.close();

	string fname_qa = output_folder + "/patient.action_outcome";
	FILE *fw_qa = fopen(fname_qa.c_str(), "w");
	fprintf(fw_qa, "%s\t%s\t%s\t%s\n", "id", "time", "out", "treat");
	int treat_pos = 0;
	int treat_neg = 0;
	int no_treat_pos = 0;
	int no_treat_neg = 0;
	for (size_t i = 0; i < dataMat.samples.size(); ++i) {
		int treat = 0;
		val = dataMat.data[full_action_name][i];
		val_near = val; if (args.action_type == 1) val_near = dataMat.data[full_action_name_near][i];
		val_far = val; if (args.action_type == 1) val_far = dataMat.data[full_action_name_far][i];
		val_con = val; if (args.action_type == 2) val_con = dataMat.data[full_action_name_con][i];
		if (get_action_value(val, val_near, val_far, val_con, args) == 1) {
			fprintf(fw_qa, "%i\t%i\t%f\t%s\n", dataMat.samples[i].id, dataMat.samples[i].time, dataMat.samples[i].outcome, "treat");
			treat = 1;
		}
		else {
			fprintf(fw_qa, "%i\t%i\t%f\t%s\n", dataMat.samples[i].id, dataMat.samples[i].time, dataMat.samples[i].outcome, "untreat");
			treat = 0;
		}

		float outcome = dataMat.samples[i].outcome;
		if (treat == 1 && outcome == 1) treat_pos++;
		else if (treat == 1 && outcome == 0) treat_neg++;
		else if (treat == 0 && outcome == 0) no_treat_neg++;
		else no_treat_pos++;
	}
	fclose(fw_qa);

	fprintf(stderr, "******** summary *********\n");
	fprintf(stderr, "treat_pos : %i %f\n", treat_pos, 100 * (float)treat_pos / (float)dataMat.samples.size());
	fprintf(stderr, "treat_neg : %i %f\n", treat_neg, 100 * (float)treat_neg / (float)dataMat.samples.size());
	fprintf(stderr, "no_treat_pos : %i %f\n", no_treat_pos, 100 * (float)no_treat_pos / (float)dataMat.samples.size());
	fprintf(stderr, "no_treat_neg : %i %f\n", no_treat_neg, 100 * (float)no_treat_neg / (float)dataMat.samples.size());

	fprintf(stderr, "\n");

	fprintf(stderr, "pos : %f\n", (float)(treat_pos + no_treat_pos));
	fprintf(stderr, "neg : %f\n", (float)(treat_neg + no_treat_neg));
	fprintf(stderr, "treat : %f\n", (float)(treat_pos + treat_neg));
	fprintf(stderr, "no_treat : %f\n", (float)(no_treat_pos + no_treat_neg));
	fprintf(stderr, "******** summary *********");



	vector<string> read_con_names;
	medial::io::read_codes_file(confounders_name_list_path, read_con_names);
	unordered_set<string> con_names(read_con_names.begin(), read_con_names.end());
	for (string con_name : con_names)
	{
		pos = find_in_feature_names(feature_names, con_name);
		if (pos < 0) {
			//print_str_vec(feature_names, "All Feature Names");
			medial::print::print_vec(feature_names, "All Feature Names", "\n");
			MTHROW_AND_ERR("Unable to find \"%s\" in features\n",
				con_name.c_str());
		}
	}

	MedSamples final_samples;
	dataMat.get_samples(final_samples);
	final_samples.write_to_file(output_folder + path_sep() + "test.samples");

	if (args.print_to_csv)
		dataMat.write_as_csv_mat(output_folder + path_sep() + "test.samples.matrix");

	//TODO: check for drug treatment generation time range same as outcome time range
	MLOG("Processing of all files is done!!\n################################\n\n");

	//Now we can run our tool for the drug effect on cancer
	string validation_pred_init = "ntrees=100;maxq=500;spread=0.0001;min_node=50;ntry=4;get_only_this_categ=1;n_categ=2;type=categorical_entropy;learn_nthreads=40;predict_nthreads=40";
	string default_calib_init = args.default_calib_init;
	string default_mdl = args.model_template; //can be "qrf" for example
	string model_select_path = args.model_select_path;

	snprintf(buff, sizeof(buff), "action_outcome_effect --rep %s --input_type features --input %s"
		" --output %s --patient_action %s --patient_groups_file %s --model_type %s"
		" --models_selection_file %s --nFolds_train 5 --nFolds_validation 5 --method_price_ratio -1"
		" --min_probablity_cutoff %f --model_validation_type qrf --model_validation_init \"%s\""
		" --model_prob_clibrator \"%s\" --confounders_file %s --bootstrap_subsample %f --nbootstrap %d"
		" --down_sample_max_cnt 0 --change_action_prior %f --debug 2>&1 | tee %s",
		RepositoryPath.c_str(), (output_folder + path_sep() + "test_matrix.bin").c_str(),
		(output_folder + path_sep() + "results.log").c_str(),// json_model.c_str(),
		(output_folder + path_sep() + "patient.action").c_str(), (output_folder + path_sep() + "patient.groups").c_str(),
		default_mdl.c_str(), model_select_path.c_str(), args.min_probablity_cutoff, validation_pred_init.c_str(), default_calib_init.c_str(),
		confounders_name_list_path.c_str(), args.bootstrap_subsample, args.nbootstrap, args.change_action_prior,
		(output_folder + path_sep() + "run_log.log").c_str());
	string run_command = string(buff);

	fw.open(output_folder + path_sep() + "run_command.sh");
	fw << "#!/bin/bash" << endl;
	fw << run_command << endl;
	fw.close();

	fw.open(output_folder + path_sep() + "base_config.cfg");
	fw << "rep = " << RepositoryPath << endl
		<< "input_type = features" << endl
		<< "input = " << (output_folder + path_sep() + "test_matrix.bin") << endl
		<< "output = " << (output_folder + path_sep() + "results.log") << endl
		<< "patient_action = " << (output_folder + path_sep() + "patient.action") << endl
		<< "patient_groups_file = " << (output_folder + path_sep() + "patient.groups") << endl
		<< "model_type = " << default_mdl << endl
		<< "models_selection_file = " << model_select_path << endl
		<< "nFolds_train = 5" << endl
		<< "nFolds_validation = 5" << endl
		<< "method_price_ratio = -1" << endl
		<< "min_probablity_cutoff = " << args.min_probablity_cutoff << endl
		<< "model_validation_type = qrf" << endl
		<< "model_validation_init = " << validation_pred_init << endl
		<< "model_prob_clibrator = " << default_calib_init << endl
		<< "confounders_file = " << confounders_name_list_path << endl
		<< "bootstrap_subsample = " << args.bootstrap_subsample << endl
		<< "nbootstrap = " << args.nbootstrap << endl
		<< "down_sample_max_cnt = 0" << endl
		<< "change_action_prior = " << args.change_action_prior << endl
		;
	fw.close();

	MLOG("To Run action_outcome_effect please run:\n%s\n\nDone!\n", run_command.c_str());

	if (args.registry_path.empty()) //need to clear registry
		delete registry;

	return 0;
}
