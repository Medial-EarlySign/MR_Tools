#include "Flow.h"
#include <MedUtils/MedUtils/MedCohort.h>
#include <MedUtils/MedUtils/MedRegistry.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

void load_censor_from_sig(const string &rep_fname, const string &censor_sig, MedRegistry &censor_r) {
	MLOG("Loading censor registry from signal %s\n", censor_sig.c_str());
	MedRepository rep;
	vector<int> all_pids;
	vector<string> sigs_read = { censor_sig };
	if (rep.read_all(rep_fname, all_pids, sigs_read) < 0)
		MTHROW_AND_ERR("Error reading repository %s\n", rep_fname.c_str());
	int sid = rep.sigs.sid(censor_sig);
	if (rep.sigs.Sid2Info[sid].n_time_channels != 2)
		MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
			censor_sig.c_str(), rep.sigs.Sid2Info[sid].n_time_channels);
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
			censor_r.registry_records.push_back(rec);
		}
	}
}

//--------------------------------------------------------------------------------------------------------------------------
int flow_get_cohort_incidence(const string &cohort_fname, const string &incidence_params, const string &rep_fname,
	const string &out_incidence_fname, bool is_med_registry, bool use_kaplan_meir, const string &sampler_params,
	const string &labeling_params, const string &censor_reg, const string &censor_sig)
{
	IncidenceParams i_params;

	i_params.init_from_string(incidence_params);
	if (i_params.rep_fname == "") i_params.rep_fname = rep_fname;

	if (!is_med_registry) {
		MedCohort cohort;

		if (cohort.read_from_file(cohort_fname) < 0) return -1;

		return cohort.create_incidence_file(i_params, out_incidence_fname, out_incidence_fname + ".debug");
	}
	else {
		MedRegistry registry, censor_r;
		registry.read_text_file(cohort_fname);
		vector<MedRegistryRecord > *censoring = NULL;
		if (!censor_reg.empty()) {
			censor_r.read_text_file(censor_reg);
			censoring = &censor_r.registry_records;
		}
		else if (!censor_sig.empty()) {
			load_censor_from_sig(rep_fname, censor_sig, censor_r);
			censoring = &censor_r.registry_records;
		}

		string labeling_pr = labeling_params;
		int time_period = i_params.incidence_days_win > 0 ? i_params.incidence_days_win :
			365 * i_params.incidence_years_window;
		if (labeling_pr.empty()) {
			if (use_kaplan_meir)
				labeling_pr = "conflict_method=max;label_interaction_mode=0:within,all|1:before_start,after_start;censor_interaction_mode=all:within,all";
			else
				labeling_pr = "conflict_method=all;label_interaction_mode=0:within,within|1:before_start,after_start;censor_interaction_mode=all:within,all";
		}
		LabelParams pr; pr.init_from_string(labeling_pr);
		pr.time_from = 0;
		pr.time_to = time_period;
		MedLabels labeler(pr);
		labeler.prepare_from_registry(registry.registry_records, censoring);

		string sampler_p = sampler_params;
		if (sampler_params.empty()) {
			sampler_p = "day_jump=365";
			char buffer[500];
			snprintf(buffer, sizeof(buffer), ";start_year=%d;end_year=%d;prediction_month_day=%d",
				i_params.from_year, i_params.to_year, i_params.start_date);
			sampler_p += string(buffer);
		}
		labeler.create_incidence_file(out_incidence_fname, i_params.rep_fname,
			i_params.age_bin, i_params.from_age, i_params.to_age, use_kaplan_meir,
			"yearly", sampler_p, out_incidence_fname + ".debug");
		return 0;
	}
}

//--------------------------------------------------------------------------------------------------------------------------
int flow_get_cohort_sampling(string cohort_fname, string sampling_params, string rep_fname, string out_samples_fname)
{
	SamplingParams s_params;
	s_params.init_from_string(sampling_params);
	if (s_params.rep_fname == "") s_params.rep_fname = rep_fname;

	MedCohort cohort;

	if (cohort.read_from_file(cohort_fname) < 0) return -1;

	return cohort.create_sampling_file(s_params, out_samples_fname);

}

int flow_get_km(const string &samples_path, int time_period) {
	MedSamples samples;
	samples.read_from_file(samples_path);

	medial::print::print_samples_stats(samples);

	double prb = medial::stats::kaplan_meir_on_samples(samples, time_period);
	MLOG("Kaplan Meir for %d - %2.2f%%\n", time_period, 100 * prb);
	return 0;
}

void flow_relabel_samples(const string &in_samples, const string &output_samples,
	const string &registry_path, const string &censor_reg_path,
	const string &rep, const string &censor_sig, const string &labeling_params) {
	MedSamples samples;
	if (in_samples.empty())
		MTHROW_AND_ERR("Error flow_relabel_samples - must provide in_samples");
	if (output_samples.empty())
		MTHROW_AND_ERR("Error flow_relabel_samples - must provide out_samples");
	if (registry_path.empty())
		MTHROW_AND_ERR("Error flow_relabel_samples - must provide cohort_fname for MedRegistry");
	if (labeling_params.empty())
		MTHROW_AND_ERR("Error flow_relabel_samples - must provide labeling_param for labeling");
	samples.read_from_file(in_samples);
	MedRegistry registry, censor_reg;
	registry.read_text_file(registry_path);
	MedRegistry *censor_final = &censor_reg;
	if (!censor_reg_path.empty())
		censor_reg.read_text_file(censor_reg_path);
	else if (!censor_sig.empty())
		load_censor_from_sig(rep, censor_sig, censor_reg);
	else
		censor_final = NULL;
	MedLabels labeler(labeling_params);
	labeler.prepare_from_registry(registry.registry_records, 
		censor_final == NULL ? NULL : &censor_final->registry_records);

	labeler.relabel_samples(samples);

	samples.write_to_file(output_samples);
}