#include "Helper.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "Logger/Logger/Logger.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

void prepare_model_from_json(MedSamples &samples,
	const string &RepositoryPath,
	MedModel &mod, MedPidRepository &dataManager) {
	medial::repository::prepare_repository(samples, RepositoryPath, mod, dataManager);

	int sz = 0, feat_cnt = mod.get_nfeatures();
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		sz += (int)samples.idSamples[i].samples.size();
	MLOG("Generating features for %d samples with %d features...\n", sz, feat_cnt);
	//dont pass 2 Billion records:
	int max_smp = int((INT_MAX / feat_cnt) * 0.99) - 1;
	if (max_smp < sz) {
		double down_factor = max_smp / double(sz);
		MWARN("WARN:: Too Many samples (%d) - down sampling by %2.3f...\n", sz, down_factor);
		//medial::process::down_sample_by_pid(samples, down_factor);
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
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat) {
	MLOG("Reading repo file [%s]\n", RepositoryPath.c_str());
	unordered_set<string> req_names;
	//mod.get_required_signal_names(req_names);
	MedModel mod;
	MedPidRepository dataManager;
	mod.init_from_json_file(jsonPath);
	mod.verbosity = 0;
	//medial::repository::prepare_repository(dataManager, "", )
	prepare_model_from_json(samples, RepositoryPath, mod, dataManager);

	mod.learn(dataManager, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	dataMat = mod.features;
}

void match_by_year(MedFeatures &data_records, float price_ratio, int year_bin_size, bool print_verbose,
	vector<int> *filter_inds_res) {
	vector<string> groups((int)data_records.samples.size());
	for (size_t i = 0; i < data_records.samples.size(); ++i) {
		int prediction_year = int(year_bin_size*round(data_records.samples[i].time / 10000 / year_bin_size));
		groups[i] = to_string(prediction_year);
	}
	vector<int> filter_inds;
	if (filter_inds_res == NULL)
		filter_inds_res = &filter_inds;
	medial::process::match_by_general(data_records, groups, *filter_inds_res, price_ratio, 5, print_verbose);
}

MedRegistry *create_registry_full_with_rep(const string &registry_type, const string &init_str,
	const string &repository_path, MedModel &model_with_rep_processor, medial::repository::fix_method method,
	MedPidRepository &rep) {
	if (rep.sigs.sid("BDATE") < 0)
		rep.init(repository_path);
	model_with_rep_processor.collect_and_add_virtual_signals(rep);

	MedRegistry *registry = MedRegistry::make_registry(registry_type, rep, init_str);

	vector<int> pids;
	vector<string> sig_codes;
	registry->get_pids(pids);
	registry->get_registry_creation_codes(sig_codes);
	vector<string> physical_signal;
	medial::repository::prepare_repository(rep, sig_codes, physical_signal, &model_with_rep_processor.rep_processors);

	if (rep.read_all(repository_path, pids, physical_signal) < 0)
		MTHROW_AND_ERR("Can't read repo\n");
	registry->create_registry(rep, method, &model_with_rep_processor.rep_processors);
	registry->clear_create_variables();

	return registry;
}