#include "Flow.h"

#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL


int flow_cohort_samples_operations(FlowAppParams &ap)
{
	if (ap.options[OPTION_FILTER_AND_MATCH]) {
		if (flow_samples_filter_and_match(ap.rep_fname, ap.in_samples_file, ap.out_samples_file, ap.samples_filter_params, ap.samples_match_params) < 0) {
			MERR("Flow: filter_and_match : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_COHORT_INCIDENCE]) {
		if (flow_get_cohort_incidence(ap.cohort_fname, ap.cohort_incidence, ap.rep_fname, ap.incidence_fname,
			ap.cohort_medregistry, ap.use_kaplan_meir, ap.sampler_params, ap.labeling_param, ap.censor_reg, ap.censor_sig) < 0) {
			MERR("Flow: get_cohort_incidence : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_COHORT_SAMPLING]) {
		if (flow_get_cohort_sampling(ap.cohort_fname, ap.cohort_sampling, ap.rep_fname, ap.out_samples_file) < 0) {
			MERR("Flow: get_cohort_incidence : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_CALC_KAPLAN_MEIR]) {
		if (flow_get_km(ap.in_samples_file, ap.time_period) < 0) {
			MERR("Flow: calc_kaplan_meir : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_RELABEL]) {
		flow_relabel_samples(ap.in_samples_file, ap.out_samples_file, ap.cohort_fname, ap.censor_reg, 
			ap.rep_fname, ap.censor_sig ,ap.labeling_param);
	}

	return 0;
}
