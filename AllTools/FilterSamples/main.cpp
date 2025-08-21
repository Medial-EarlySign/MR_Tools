#include <string>
#include "Cmd_Args.h"
#include <InfraMed/InfraMed/InfraMed.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedStat/MedStat/MedBootstrap.h>
using namespace std;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void prepare_model_from_json(MedSamples &samples,
	const string &RepositoryPath,
	MedModel &mod, MedPidRepository &dataManager, double change_prior) {
	medial::repository::prepare_repository(samples, RepositoryPath, mod, dataManager);

	int sz = 0, feat_cnt = 0;
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		sz += (int)samples.idSamples[i].samples.size();
	for (size_t i = 0; i < mod.generators.size(); ++i)
		feat_cnt += (int)mod.generators[i]->names.size();
	MLOG("Generating features for %d samples with %d features...\n", sz, feat_cnt);
	//dont pass 2 Billion records:
	int max_smp = int((INT_MAX / feat_cnt) * 0.99) - 1;
	if (max_smp < sz && change_prior > 0) {
		vector<int> sel_idx;
		medial::process::match_to_prior(samples, change_prior, sel_idx);
		if (!sel_idx.empty()) //did something
			sz = (int)sel_idx.size();
	}
	if (max_smp < sz) {
		double down_factor = max_smp / double(sz);
		MWARN("WARN:: Too Many samples - down sampling by %2.3f...\n", down_factor);
		//down_sample_by_pid(samples, down_factor);
		medial::process::down_sample(samples, down_factor);
		MLOG("Done Down sampling\n");
	}
	mod.serialize_learning_set = 0;
	if (mod.predictor == NULL) {
		MLOG("set default predictor for serialization\n");
		mod.set_predictor("gdlm");
	}
}

void load_matrix_from_json(MedSamples &samples,
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat, double change_prior,
	MedModel &mod) {
	MLOG("Reading repo file [%s]\n", RepositoryPath.c_str());
	MedPidRepository dataManager;
	mod.init_from_json_file(jsonPath);
	mod.verbosity = 0;
	prepare_model_from_json(samples, RepositoryPath, mod, dataManager, change_prior);

	mod.learn(dataManager, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	dataMat = move(mod.features);
}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 1;

	MedSamples samples;
	samples.read_from_file(args.samples);
	MedRepository rep;
	if (args.filter_train != 0) {
		vector<string> sigs = { "TRAIN" };
		vector<int> pids;
		samples.get_ids(pids);
		if (rep.read_all(args.rep.c_str(), pids, sigs) < 0)
			MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());

		int tr_sid = rep.sigs.sid(sigs.front());
		MedSamples filtered;
		for (size_t i = 0; i < samples.idSamples.size(); ++i)
		{
			int pid = samples.idSamples[i].id;
			int tr = medial::repository::get_value(rep, pid, tr_sid);
			if (tr == args.filter_train)
				filtered.idSamples.push_back(samples.idSamples[i]);
		}
		samples = move(filtered);
	}
	//filter json mat
	if (!args.json_mat.empty() && (!args.filter_feat.empty() || !args.filter_by_bt_cohort.empty())) {
		MedFeatures mat;
		MedModel m;
		load_matrix_from_json(samples, args.rep, args.json_mat, mat, 0, m);
		vector<int> sel;

		if (!args.filter_feat.empty()) {
			vector<string> filter_feature_names;
			mat.get_feature_names(filter_feature_names);
			int pos_name = find_in_feature_names(filter_feature_names, args.filter_feat);
			const string &full_filt_name = filter_feature_names[pos_name];
			vector<int> after_filt_idxs;
			int before_size = (int)mat.samples.size();
			for (size_t i = 0; i < mat.samples.size(); ++i)
				if (mat.data[full_filt_name][i] >= args.low_val &&
					mat.data[full_filt_name][i] <= args.high_val)
					after_filt_idxs.push_back((int)i);

			medial::process::filter_row_indexes(mat, after_filt_idxs);
			MLOG("Filter condition on %s[%2.4f , %2.4f], before was %d after filtering %zu\n",
				full_filt_name.c_str(), args.low_val, args.high_val, before_size, mat.samples.size());
			samples.import_from_sample_vec(mat.samples);
		}

		if (!args.filter_by_bt_cohort.empty()) {
			int before_size = (int)mat.samples.size();
			string cohort_name = args.filter_by_bt_cohort.substr(0, args.filter_by_bt_cohort.find('\t'));
			string cohort_definition = "";
			if (args.filter_by_bt_cohort.find('\t') != string::npos)
				cohort_definition = args.filter_by_bt_cohort.substr(args.filter_by_bt_cohort.find('\t') + 1);
			else
				cohort_definition = args.filter_by_bt_cohort;

			vector<string> param_use;
			boost::split(param_use, cohort_definition, boost::is_any_of(";"));
			for (size_t i = 0; i < param_use.size(); ++i)
			{
				vector<string> tokens;
				boost::split(tokens, param_use[i], boost::is_any_of(":"));
				param_use[i] = tokens[0];
			}

			unordered_set<string> valid_params;
			valid_params.insert("Time-Window");
			valid_params.insert("Label");
			MedBootstrap bt_tmp;
			bt_tmp.clean_feature_name_prefix(mat.data);
			for (auto it = mat.data.begin(); it != mat.data.end(); ++it)
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
						boost::replace_all(cohort_definition, param_name, found_nm);
					}
				}

			if (!all_valid) {
				if (!args.debug) {
					MLOG("Feature Names availible for cohort filtering:\n");
					for (auto it = mat.data.begin(); it != mat.data.end(); ++it)
						MLOG("%s\n", it->first.c_str());
					MLOG("Time-Window\n");
					MLOG("\n");
				}
				MTHROW_AND_ERR("Cohort file has wrong paramter names. look above for all avaible params\n");
			}

			MedBootstrap::filter_bootstrap_cohort(mat, cohort_definition);
			samples.import_from_sample_vec(mat.samples);
			MLOG("Filter BT condition  before was %d after filtering %zu\n",
				 before_size, mat.samples.size());
		}
		medial::print::print_samples_stats(samples);
	}
	samples.write_to_file(args.output);
	return 0;
}