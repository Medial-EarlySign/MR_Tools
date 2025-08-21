#define _CRT_SECURE_NO_WARNINGS
#include "ValidationFunctions.h"

// Do your stuff
int validate_bounds(input_data& indata, work_space& work, FILE *fout, int nbootstrap, quick_random& qrand) {

	// Header
	fprintf(fout, "Time-Window\tAge-Range\tCheckSum\tNBootStrap\tBound\t");
	fprintf(fout, "Target-Sens\tSens-Obs\tSens-Mean\tSens-CI-Lower\tSens-CI-Upper\tIs-Sens-Inside\t");
	fprintf(fout, "Target-Spec\tSpec-Obs\tSpec-Mean\tSpec-CI-Lower\tSpec-CI-Upper\tIs-Spec-Inside\t");
	fprintf(fout, "OR-Obs\tOR-Mean\tOR-CI-Lower\tOR-CI-Upper\n");

	// Loop on time-windows x age-ranges
	int idx = 0;
	for (unsigned int i = 0; i<indata.time_windows.size(); i++) {
		for (unsigned int j = 0; j<indata.age_ranges.size(); j++) {
			fprintf(stderr, "Working on Time Window %d - %d and Age Range %d - %d\n", indata.time_windows[i].first, indata.time_windows[i].second, indata.age_ranges[j].first,
				indata.age_ranges[j].second);

			cross_section entry(indata.age_ranges[j], indata.time_windows[i]);
			if (indata.bnds.find(entry) == indata.bnds.end())
				continue;

			vector<target_bound> cs_bnd = indata.bnds[entry];

			// Collect Scores
			int nids, checksum;
			if (collect_all_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.time_windows[i], indata.age_ranges[j], indata.byears, indata.censor,
				work.idstrs, work.dates, work.days, work.years, work.scores, work.ages, work.id_starts, work.id_nums, work.types, &nids, &checksum) == -1) {
				fprintf(stderr, "Score Collection failed\n");
				return -1;
			}

			// Observed parameters
			int size = 2 * ((int)cs_bnd.size());

			vector<double> observables;
			all_stats istats;
			vector<double> pos_scores;
			vector<double> neg_scores;
			observables.resize(size, -1.0);

			if (get_bootstrap_scores(work.scores, work.types, work.id_starts, work.id_nums, nids, pos_scores, neg_scores, qrand, 1) == 0)
				get_bootstrap_performance(pos_scores, neg_scores, cs_bnd, observables);

			// Bootstraping estimate of parameters ....

			vector<vector<double> > estimates(nbootstrap);

			clock_t start = clock();
			for (int ibs = 0; ibs<nbootstrap; ibs++) {
				if (ibs % 20 == 0)
					fprintf(stderr, "Bootstrap #%d ... ", ibs);

				all_stats istats;
				vector<double> pos_scores;
				vector<double> neg_scores;
				estimates[ibs].resize(size, -1.0);
				if (get_bootstrap_scores(work.scores, work.types, work.id_starts, work.id_nums, nids, pos_scores, neg_scores, qrand, 0) == 0) {
					get_bootstrap_performance(pos_scores, neg_scores, cs_bnd, estimates[ibs]);
				}
			}
			fprintf(stderr, "\n");

			for (unsigned ibnd = 0; ibnd<cs_bnd.size(); ibnd++) {
				double sens_sum = 0, spec_sum = 0;
				vector<double> sens_values;
				vector<double> spec_values;
				int actual_nbootstrap = 0;


				for (int ibs = 0; ibs<nbootstrap; ibs++) {
					if (estimates[ibs][2 * ibnd] != -1) {
						sens_sum += estimates[ibs][2 * ibnd];
						sens_values.push_back(estimates[ibs][2 * ibnd]);
						spec_sum += estimates[ibs][2 * ibnd + 1];
						spec_values.push_back(estimates[ibs][2 * ibnd + 1]);
						actual_nbootstrap++;
					}
				}


				fprintf(fout, "%d-%d\t%d-%d\t%d\t%d\t%f\t", indata.time_windows[i].first, indata.time_windows[i].second, indata.age_ranges[j].first, indata.age_ranges[j].second, checksum,
					actual_nbootstrap, cs_bnd[ibnd].score);

				if (actual_nbootstrap) {
					double obs_sens = 100 * observables[2 * ibnd];
					double obs_spec = 100 * observables[2 * ibnd + 1];
					double obs_or = (obs_sens == 100 || obs_sens == 0 || obs_spec == 100 || obs_spec == 0) ? -1 : (obs_sens / (100 - obs_sens))*(obs_spec / (100 - obs_spec));

					double sens_mean = 100 * sens_sum / actual_nbootstrap;
					double spec_mean = 100 * spec_sum / actual_nbootstrap;
					double or_mean = (spec_mean == 100 || spec_mean == 0 || sens_mean == 100 || sens_mean == 0) ? -1 : (sens_mean / (100 - sens_mean))*(spec_mean / (100 - spec_mean));

					sort(sens_values.begin(), sens_values.end());
					double sens_lower = 100 * sens_values[(int)(0.025*actual_nbootstrap)];
					double sens_upper = 100 * sens_values[(int)(0.975*actual_nbootstrap)];

					sort(spec_values.begin(), spec_values.end());
					double spec_lower = 100 * spec_values[(int)(0.025*actual_nbootstrap)];
					double spec_upper = 100 * spec_values[(int)(0.975*actual_nbootstrap)];

					double or_lower = (spec_lower == 100 || spec_lower == 0 || sens_lower == 100 || sens_lower == 0) ? -1 : (sens_lower / (100 - sens_lower))*(spec_lower / (100 - spec_lower));
					double or_upper = (spec_upper == 100 || spec_upper == 0 || sens_upper == 100 || sens_upper == 0) ? -1 : (sens_upper / (100 - sens_upper))*(spec_upper / (100 - spec_upper));

					char sens_flag = (cs_bnd[ibnd].sens >= sens_lower && cs_bnd[ibnd].sens <= sens_upper) ? '+' : '-';
					char spec_flag = (cs_bnd[ibnd].spec >= spec_lower && cs_bnd[ibnd].spec <= spec_upper) ? '+' : '-';

					fprintf(fout, "%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%c\t", cs_bnd[ibnd].sens, obs_sens, sens_mean, sens_lower, sens_upper, sens_flag);
					fprintf(fout, "%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%c\t", cs_bnd[ibnd].spec, obs_spec, spec_mean, spec_lower, spec_upper, spec_flag);
					fprintf(fout, "%.2f\t%.2f\t%.2f\t%.2f\n", obs_or, or_mean, or_lower, or_upper);
				}
				else
					fprintf(fout, "-\t-\t-\t-\t-\t-\t-\t-\t-\n");
			}
		}
	}

	return 0;
}


// Do your stuff
int validate_bounds_autosim(input_data& indata, work_space& work, FILE *fout, int nbootstrap, quick_random& qrand) {

	// Header
	fprintf(fout, "Age-Range\tCheckSum\tNBootStrap\tBound\t");
	fprintf(fout, "Target-Sens\tSens-Obs\tSens-Mean\tSens-CI-Lower\tSens-CI-Upper\tIs-Sens-Inside\t");
	fprintf(fout, "Target-Spec\tSpec-Obs\tSpec-Mean\tSpec-CI-Lower\tSpec-CI-Upper\tIs-Spec-Inside\t");
	fprintf(fout, "Target-EarlySens1\tEarlySens1-Obs\tEarlySens1-Mean\tEarlySens1-CI-Lower\tEarlySens1-CI-Upper\tIs-EarlySens1-Inside\t");
	fprintf(fout, "Target-EarlySens2\tEarlySens2-Obs\tEarlySens2-Mean\tEarlySens2-CI-Lower\tEarlySens2-CI-Upper\tIs-EarlySens2-Inside\t");
	fprintf(fout, "Target-EarlySens3\tEarlySens3-Obs\tEarlySens3-Mean\tEarlySens3-CI-Lower\tEarlySens3-CI-Upper\tIs-EarlySens3-Inside\n");

	// Loop on age-ranges
	int idx = 0;
	for (unsigned int j = 0; j<indata.age_ranges.size(); j++) {
		fprintf(stderr, "Working on  Age Range %d - %d\n", indata.age_ranges[j].first, indata.age_ranges[j].second);

		if (indata.bnds_autosim.find(indata.age_ranges[j]) == indata.bnds_autosim.end())
			continue;

		vector<target_bound_autosim> cs_bnd = indata.bnds_autosim[indata.age_ranges[j]];

		// Collect Scores
		int nids, checksum;
		if (collect_all_autosim_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.age_ranges[j], indata.byears, indata.censor,
			work.idstrs, work.dates, work.days, work.years, work.scores, work.gaps, work.id_starts, work.id_nums, work.types, &nids, &checksum) == -1) {
			fprintf(stderr, "Score Collection for AutoSim failed\n");
			return -1;
		}

		int size = 5 * ((int)cs_bnd.size());
		// Observed parameters
		vector<double> observables;

		all_stats istats;
		vector<double> pos_scores;
		vector<double> earlysens1pos_scores;
		vector<double> earlysens2pos_scores;
		vector<double> earlysens3pos_scores;
		vector<double> neg_scores;
		observables.resize(size, -1.0);
		if (get_autosim_scores(work.gaps, work.scores, work.types, work.id_starts, work.id_nums, nids, pos_scores, neg_scores, qrand, earlysens1pos_scores, earlysens2pos_scores, earlysens3pos_scores, 1) == 0) {
			get_bootstrap_performance_autosim(pos_scores, earlysens1pos_scores, earlysens2pos_scores, earlysens3pos_scores, neg_scores, cs_bnd, observables);
		}

		// Bootstraping estimate of parameters ....

		vector<vector<double> > estimates(nbootstrap);

		clock_t start = clock();
		for (int ibs = 0; ibs<nbootstrap; ibs++) {
			if (ibs % 20 == 0)
				fprintf(stderr, "Bootstrap #%d ... ", ibs);

			all_stats istats;
			vector<double> pos_scores;
			vector<double> earlysens1pos_scores;
			vector<double> earlysens2pos_scores;
			vector<double> earlysens3pos_scores;
			vector<double> neg_scores;
			estimates[ibs].resize(size, -1.0);
			if (get_autosim_scores(work.gaps, work.scores, work.types, work.id_starts, work.id_nums, nids, pos_scores, neg_scores, qrand, earlysens1pos_scores, earlysens2pos_scores, earlysens3pos_scores, 0) == 0) {
				get_bootstrap_performance_autosim(pos_scores, earlysens1pos_scores, earlysens2pos_scores, earlysens3pos_scores, neg_scores, cs_bnd, estimates[ibs]);
			}
		}
		fprintf(stderr, "\n");


		// Print
		for (unsigned ibnd = 0; ibnd<cs_bnd.size(); ibnd++) {
			double sens_sum = 0, spec_sum = 0, early1_sum = 0, early2_sum = 0, early3_sum = 0;
			vector<double> sens_values;
			vector<double> spec_values;
			vector<double> sens_early1_values;
			vector<double> sens_early2_values;
			vector<double> sens_early3_values;

			int actual_nbootstrap = 0;

			for (int ibs = 0; ibs<nbootstrap; ibs++) {
				if (estimates[ibs][5 * ibnd] != -1) {
					sens_sum += estimates[ibs][5 * ibnd];
					sens_values.push_back(estimates[ibs][5 * ibnd]);
					spec_sum += estimates[ibs][5 * ibnd + 1];
					spec_values.push_back(estimates[ibs][5 * ibnd + 1]);

					early1_sum += estimates[ibs][5 * ibnd + 2];
					sens_early1_values.push_back(estimates[ibs][5 * ibnd + 2]);

					early2_sum += estimates[ibs][5 * ibnd + 3];
					sens_early2_values.push_back(estimates[ibs][5 * ibnd + 3]);

					early3_sum += estimates[ibs][5 * ibnd + 4];
					sens_early3_values.push_back(estimates[ibs][5 * ibnd + 4]);

					actual_nbootstrap++;
				}
			}


			fprintf(fout, "%d-%d\t%d\t%d\t%f\t", indata.age_ranges[j].first, indata.age_ranges[j].second, checksum,
				actual_nbootstrap, cs_bnd[ibnd].score);


			if (actual_nbootstrap) {
				double sens_obs = 100 * observables[5 * ibnd];
				double spec_obs = 100 * observables[5 * ibnd + 1];
				double early1_obs = 100 * observables[5 * ibnd + 2];
				double early2_obs = 100 * observables[5 * ibnd + 3];
				double early3_obs = 100 * observables[5 * ibnd + 4];

				double sens_mean = 100 * sens_sum / actual_nbootstrap;
				double spec_mean = 100 * spec_sum / actual_nbootstrap;
				double early1_mean = 100 * early1_sum / actual_nbootstrap;
				double early2_mean = 100 * early2_sum / actual_nbootstrap;
				double early3_mean = 100 * early3_sum / actual_nbootstrap;

				sort(sens_values.begin(), sens_values.end());
				double sens_lower = 100 * sens_values[(int)(0.025*actual_nbootstrap)];
				double sens_upper = 100 * sens_values[(int)(0.975*actual_nbootstrap)];

				sort(spec_values.begin(), spec_values.end());
				double spec_lower = 100 * spec_values[(int)(0.025*actual_nbootstrap)];
				double spec_upper = 100 * spec_values[(int)(0.975*actual_nbootstrap)];

				sort(sens_early1_values.begin(), sens_early1_values.end());
				double sens_early1_lower = 100 * sens_early1_values[(int)(0.025*actual_nbootstrap)];
				double sens_early1_upper = 100 * sens_early1_values[(int)(0.975*actual_nbootstrap)];

				sort(sens_early2_values.begin(), sens_early2_values.end());
				double sens_early2_lower = 100 * sens_early2_values[(int)(0.025*actual_nbootstrap)];
				double sens_early2_upper = 100 * sens_early2_values[(int)(0.975*actual_nbootstrap)];

				sort(sens_early3_values.begin(), sens_early3_values.end());
				double sens_early3_lower = 100 * sens_early3_values[(int)(0.025*actual_nbootstrap)];
				double sens_early3_upper = 100 * sens_early3_values[(int)(0.975*actual_nbootstrap)];

				char sens_flag = (cs_bnd[ibnd].sens >= sens_lower && cs_bnd[ibnd].sens <= sens_upper) ? '+' : '-';
				char spec_flag = (cs_bnd[ibnd].spec >= spec_lower && cs_bnd[ibnd].spec <= spec_upper) ? '+' : '-';

				char early1_flag = (cs_bnd[ibnd].earlysens1 >= sens_early1_lower && cs_bnd[ibnd].earlysens1 <= sens_early1_upper) ? '+' : '-';
				char early2_flag = (cs_bnd[ibnd].earlysens2 >= sens_early2_lower && cs_bnd[ibnd].earlysens2 <= sens_early2_upper) ? '+' : '-';
				char early3_flag = (cs_bnd[ibnd].earlysens3 >= sens_early3_lower && cs_bnd[ibnd].earlysens3 <= sens_early3_upper) ? '+' : '-';



				fprintf(fout, "%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%c\t", cs_bnd[ibnd].sens, sens_obs, sens_mean, sens_lower, sens_upper, sens_flag);
				fprintf(fout, "%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%c\t", cs_bnd[ibnd].spec, spec_obs, spec_mean, spec_lower, spec_upper, spec_flag);

				fprintf(fout, "%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%c\t", cs_bnd[ibnd].earlysens1, early1_obs, early1_mean, sens_early1_lower, sens_early1_upper, early1_flag);
				fprintf(fout, "%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%c\t", cs_bnd[ibnd].earlysens2, early2_obs, early2_mean, sens_early2_lower, sens_early2_upper, early2_flag);
				fprintf(fout, "%.3f\t%.3f\t%.3f\t%.3f\t%.3f\t%c\n", cs_bnd[ibnd].earlysens3, early3_obs, early3_mean, sens_early3_lower, sens_early3_upper, early3_flag);


			}
			else
				fprintf(fout, "-\t-\t-\t-\t-\t-\t-\t-\n");
		}
	}

	return 0;
}
