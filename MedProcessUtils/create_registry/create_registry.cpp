#include "Cmd_Arg.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedUtils/MedUtils/MedRegistry.h"

// A utility for creating a registry and/or samples
// -- Read/Create registry == (multiple) time-periods + correspoding labels per id indicating when the individual is healthy/sick
// -- Read/Create censor == (multiple) time-periods per id
// -- Create a labler from registry + censor == (multiple) time-periods when the we can choose the samples + correspoding label (e.g. the period BEFORE the disease-period in the registry)
// -- Create samples from labeler + sampling strategy

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

void read_active_periods(const string &complete_reg_sig, const string &rep_path,
	MedRegistry &active_reg) {
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

int main(int argc, char *argv[]) {

	// Init params
	ProgramArgs args;
	int ret_code = args.parse_parameters(argc, argv);
	if (ret_code == -1)
		return -1;
	if (ret_code != 0)
		MTHROW_AND_ERR("Wrong parameters\n");
	medial::repository::set_global_time_unit(args.rep);

	// Read Registry or create from init-string + json
	MedRegistry loaded_reg;
	MedRegistry *registry = &loaded_reg;
	if (!args.registry_load.empty()) {
		registry->read_text_file(args.registry_load);
		//complete control periods if needed
		if ((!args.registry_active_periods_complete_controls.empty() || !args.registry_active_periods_complete_controls_sig.empty()) && args.use_active_for_reg_outcome) {
			complete_control_active_periods(*registry, args.registry_active_periods_complete_controls, args.registry_active_periods_complete_controls_sig, args.rep);
			if (!args.registry_save.empty())
				registry->write_text_file(args.registry_save);
		}
	}
	else {
		MedModel model_rep_proc;
		if (!args.model_rep_proc_json.empty())
			model_rep_proc.init_from_json_file(args.model_rep_proc_json);
		registry = MedRegistry::create_registry_full(args.registry_type, args.registry_init, args.rep,
			model_rep_proc, args.conflicts_method);

		if ((!args.registry_active_periods_complete_controls.empty() || !args.registry_active_periods_complete_controls_sig.empty()) && args.use_active_for_reg_outcome)
			complete_control_active_periods(*registry, args.registry_active_periods_complete_controls, args.registry_active_periods_complete_controls_sig, args.rep);

		if (!args.registry_save.empty())
			registry->write_text_file(args.registry_save);
	}


	// Read censoring or create from init-string + json
	medial::print::print_reg_stats(registry->registry_records);
	MedRegistry *censor_reg = NULL;
	vector<MedRegistryRecord> censor_recs;
	if (!args.censor_load.empty()) {
		MLOG("Loading censor registry from file %s\n", args.censor_load.c_str());
		MedRegistry censor_external;
		censor_external.read_text_file(args.censor_load);
		censor_recs.swap(censor_external.registry_records);
	}
	else if (!args.registry_censor_init.empty()) {
		MedModel model_rep_proc;
		MLOG("Loading censor registry\n");
		censor_reg = MedRegistry::create_registry_full(args.registry_censor_type, args.registry_censor_init,
			args.rep, model_rep_proc, medial::repository::fix_method::none);
		censor_recs.swap(censor_reg->registry_records);
		delete censor_reg;
		censor_reg = NULL;
	}
	else if (!args.registry_active_periods_complete_controls_sig.empty()) {
		MedRegistry censor_external;
		read_active_periods(args.registry_active_periods_complete_controls_sig, args.rep, censor_external);
		censor_recs.swap(censor_external.registry_records);
	}

	// Create a labeler : Periods of times to sample from with corresponding labels 
	MedLabels labeler(args.labeling_params);
	labeler.prepare_from_registry(registry->registry_records, censor_recs.empty() ? NULL : &censor_recs);
	if (!args.reg_print_incidence.empty())
		labeler.create_incidence_file(args.reg_print_incidence, args.rep, 5, 30, 90, true, "yearly",
			args.reg_params_incidence);

	// Create samples from labeler according to sampling strategy
	if (!args.sampler_type.empty() && !args.sampler_args.empty() && !args.samples_save.empty()) {
		MedSamples samples;
		MedSamplingStrategy *sampler = MedSamplingStrategy::make_sampler(args.sampler_type, args.sampler_args);
		sampler->filtering_params = args.filtering_params;

		// Get birth-dates of all relevant ids for sampler initialization
		MedRepository rep;
		vector<int> r_pids;
		registry->get_pids(r_pids);
		vector<string> sig_names = { "BDATE" };
		if (rep.read_all(args.rep, r_pids, sig_names) < 0)
			MTHROW_AND_ERR("Can't read repo %s\n", args.rep.c_str());
		sampler->init_sampler(rep);

		// Create the samples and write to file
		labeler.create_samples(sampler, samples);
		samples.write_to_file(args.samples_save);

		delete sampler;
		MLOG("Done Sampling has %d samples on %zu patients...\n",
			samples.nSamples(), samples.idSamples.size());
		medial::print::print_samples_stats(samples);
		if (samples.time_unit == MedTime::Date)
			medial::print::print_by_year(samples, 1, false, true);
	}

	if (args.registry_load.empty()) //need to clear registry
		delete registry;

	return 0;
}