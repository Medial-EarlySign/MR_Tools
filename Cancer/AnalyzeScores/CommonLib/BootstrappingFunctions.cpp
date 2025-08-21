#define _CRT_SECURE_NO_WARNINGS
#include "BootstrappingFunctions.h"

// Initialize names of output parameters
int init_param_names(double extra_fpr, double extra_sim_fpr, double extra_sens, bool all_fpr, int *nestimates, char **param_names, int *autosim_nestimates, char **autosim_param_names) {
	// Time Windows parameters
	// Initial
	char field[MAX_STRING_LEN];

	char initial_param_names[5][MAX_STRING_LEN] = { "NPOS","NNEG","AUC","WAUC","AUC-PR" };
	int ninit = sizeof(initial_param_names) / MAX_STRING_LEN;

	char prefix1[10][MAX_STRING_LEN] = { "SENS","OR","NPV","PPV","PR","LIFT","PLR","NLR","SCORE","RR" };
	int nprefix1 = sizeof(prefix1) / MAX_STRING_LEN;

	char prefix2[10][MAX_STRING_LEN] = { "SPEC","OR","NPV","PPV","PR","LIFT","PLR","NLR","SCORE","RR" };
	int nprefix2 = sizeof(prefix2) / MAX_STRING_LEN;

	char prefix3[10][MAX_STRING_LEN] = { "SENS","OR","NPV","PPV","PR","LIFT","PLR","NLR","SPEC","RR" };
	int nprefix3 = sizeof(prefix3) / MAX_STRING_LEN;

	double *fpr_points = get_fpr_points(all_fpr);
	int nfpr_points = get_fpr_points_num(all_fpr);

	double *sens_points = get_sens_points();
	int nsens_points = get_sens_points_num();

	double *score_points = get_score_points();
	int nscore_points = get_score_points_num();

	// Allocate
	*nestimates = ninit + nprefix1 * nfpr_points + nprefix2 * nsens_points + nprefix3 * nscore_points;
	if (extra_fpr != -1)
		(*nestimates) += nprefix1;
	if (extra_sens != -1)
		(*nestimates) += nprefix2;

	(*param_names) = (char *)malloc((*nestimates)*MAX_STRING_LEN);
	if ((*param_names) == NULL) {
		fprintf(stderr, "Allocation Failed\n");
		return -1;
	}

	// Fill
	int idx = 0;
	for (int i = 0; i < ninit; i++) {
		strcpy(*param_names + idx*MAX_STRING_LEN, initial_param_names[i]);
		idx++;
	}

	for (int ifpr = 0; ifpr < nfpr_points; ifpr++) {
		for (int ipref = 0; ipref < nprefix1; ipref++) {
			sprintf(field, "%s@FP%.1f", prefix1[ipref], fpr_points[ifpr]);
			strcpy(*param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	for (int isens = 0; isens < nsens_points; isens++) {
		for (int ipref = 0; ipref < nprefix2; ipref++) {
			sprintf(field, "%s@%.1f", prefix2[ipref], sens_points[isens]);
			strcpy(*param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	for (int i = 0; i < nscore_points; i++) {
		for (int ipref = 0; ipref < nprefix3; ipref++) {
			sprintf(field, "%s@SCORE%.1f", prefix3[ipref], score_points[i]);
			strcpy(*param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	// Extra FPR
	if (extra_fpr != -1) {
		for (int ipref = 0; ipref < nprefix1; ipref++) {
			sprintf(field, "%s@FP%f", prefix1[ipref], extra_fpr);
			strcpy(*param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	// Extra Sens
	if (extra_sens != -1) {
		for (int ipref = 0; ipref < nprefix1; ipref++) {
			sprintf(field, "%s@%f", prefix2[ipref], extra_sens);
			strcpy(*param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	// AutoSim parameters
	// Initial
	char sim_prefix[9][MAX_STRING_LEN] = { "TP","FP","PPV","SPEC","SENS","SCORE","EarlySens1","EarlySens2","EarlySens3" };
	int nsim_prefix = sizeof(sim_prefix) / MAX_STRING_LEN;

	double *sim_fpr_points = get_sim_fpr_points();
	int nsim_fpr_points = get_sim_fpr_points_num();

	// Allocate
	*autosim_nestimates = nsim_prefix * nsim_fpr_points;
	if (extra_sim_fpr != -1)
		(*autosim_nestimates) += nsim_prefix;

	(*autosim_param_names) = (char *)malloc((*autosim_nestimates)*MAX_STRING_LEN);
	if ((*autosim_param_names) == NULL) {
		fprintf(stderr, "Allocation Failed\n");
		return -1;
	}

	idx = 0;
	for (int ifpr = 0; ifpr < nsim_fpr_points; ifpr++) {
		for (int ipref = 0; ipref < nsim_prefix; ipref++) {
			sprintf(field, "%s@FP%.1f", sim_prefix[ipref], sim_fpr_points[ifpr]);
			strcpy(*autosim_param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	// Extra FPR
	if (extra_sim_fpr != -1) {
		for (int ipref = 0; ipref < nsim_prefix; ipref++) {
			sprintf(field, "%s@FP%.1f", sim_prefix[ipref], extra_sim_fpr);
			strcpy(*autosim_param_names + idx*MAX_STRING_LEN, field);
			idx++;
		}
	}

	return 0;
}

// Handle output files
int open_all_output_files(const char *out_file, running_flags& flags, int period, char *param_names, int nestimates, char *autosim_param_names, int autosim_nestimates, out_fps& fouts) {

	if (open_output_files(out_file, flags, param_names, nestimates, autosim_param_names, autosim_nestimates, fouts) == -1)
		return -1;

	if (period > 0) {
		char periodic_cuts_file_name[MAX_STRING_LEN];
		sprintf(periodic_cuts_file_name, "%s.PeriodicCuts", out_file);
		fouts.periodic_cuts_fout = fopen(periodic_cuts_file_name, "w");
		if (fouts.periodic_cuts_fout == NULL) {
			fprintf(stderr, "Could not open periodic autosim outuput file \'%s\' for writing\n", periodic_cuts_file_name);
			return -1;
		}
		fprintf(stderr, "Opened periodic autosim outuput file \'%s\' for writing\n", periodic_cuts_file_name);

		char periodic_autosim_file_name[MAX_STRING_LEN];
		sprintf(periodic_autosim_file_name, "%s.PeriodicAutoSim", out_file);
		fouts.periodic_autosim_fout = fopen(periodic_autosim_file_name, "w");
		if (fouts.periodic_autosim_fout == NULL) {
			fprintf(stderr, "Could not open periodic autosim outuput file \'%s\' for writing\n", periodic_autosim_file_name);
			return -1;
		}
		fprintf(stderr, "Opened periodic autosim outuput file \'%s\' for writing\n", periodic_autosim_file_name);
	}

	return 0;
}

// Autosim
int do_autosim(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, double extra_fpr, vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP) {

	for (unsigned int j = 0; j < indata.age_ranges.size(); j++) {
		fprintf(stderr, "Working on AutoSim on Age Range %d - %d\n", indata.age_ranges[j].first, indata.age_ranges[j].second); fflush(stderr);

		// Collect Scores
		int nids, checksum;
		if (collect_all_autosim_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.age_ranges[j], indata.byears, indata.censor,
			work.idstrs, work.dates, work.days, work.years, work.scores, work.gaps, work.id_starts, work.id_nums, work.types, &nids, &checksum) == -1) {
			fprintf(stderr, "Score Collection for AutoSim failed\n");
			return -1;
		}
		if (!flags.raw_only) {
			fprintf(fouts.autosim_fout, "%d-%d\t%d", indata.age_ranges[j].first, indata.age_ranges[j].second, checksum);
		}

		if (flags.auto_sim_raw) {
			for (int i = 0; i < nids; i++) {
				if (work.types[i] == 0)
					fprintf(fouts.sim_raw_fout, "%d-%d %i %s %i\n", indata.age_ranges[j].first, indata.age_ranges[j].second, work.types[i], work.idstrs[work.id_starts[i]].c_str(),
						work.dates[work.id_starts[i]]);
			}
			fclose(fouts.sim_raw_fout);
		}
		fprintf(stderr, "Finsihed AutoSim score collection on Age Range %d - %d\n", indata.age_ranges[j].first, indata.age_ranges[j].second); fflush(stderr);

		if (!flags.raw_only) {

			// Observed parameters
			vector<double> autosim_observables;
			vector<bool> valid_observable;

			// Bootstraping estimate of parameters 
			vector<vector<double> > autosim_bootstrap_estimates(NBOOTSTRAP);
			vector<vector<bool> > valid_bootstrap(NBOOTSTRAP);

			time_t start = time(NULL);

			autosim_params gen_params;
			gen_params.nestimates = autosim_nestimates;
			gen_params.nids = nids;
			gen_params.estimates = (vector<vector<double> > *)& autosim_bootstrap_estimates;
			gen_params.validity = (vector<vector<bool> > *)& valid_bootstrap;
			gen_params.work = (work_space *)& work;
			gen_params.extra_fpr = extra_fpr;

			// Observed values
			int *all_ids = (int *)malloc(nids*sizeof(int));
			assert(all_ids != NULL);

			for (int i = 0; i < nids; i++)
				all_ids[i] = i;

			autosim_observables.resize(autosim_nestimates, -1.0);
			valid_observable.resize(autosim_nestimates, false);
			get_autosim_parameters(all_ids, work.types, work.id_starts, work.id_nums, nids, work.scores, work.gaps, autosim_observables, valid_observable, threaded_qrand[0], extra_fpr);

			free(all_ids);

			// Bootstrap estimtes
			vector<autosim_thread_params> threads(nthreads);
			int k = 0;
			int jump = NBOOTSTRAP / nthreads;
			for (k = 0; k < nthreads; k++) {
				threads[k].from = k*jump;
				threads[k].to = (k + 1)*jump - 1;
				threads[k].general_params = &gen_params;
				threads[k].qrand = &(threaded_qrand[k]);
				threads[k].state = 0;
				threads[k].nbootstraps = 0;
			}

			threads[nthreads - 1].to = NBOOTSTRAP - 1;

			vector<thread> th_handle(nthreads);
			for (int i = 0; i < nthreads; i++) {
				th_handle[i] = thread(autosim_thread, (void *)&threads[i]);
			}

			int n_state = 0;
			while (n_state < nthreads) {
				this_thread::sleep_for(chrono::milliseconds(10));
				n_state = 0;
				for (int i = 0; i < nthreads; i++)
					n_state += threads[i].state;
			}
			for (int i = 0; i < nthreads; i++)
				th_handle[i].join();

			fprintf(stderr, "Bootstraping took %2.1f secs\n", (float)difftime(time(NULL), start));

			// Print output
			int nbootstrap = 0;
			for (int k = 0; k < nthreads; k++)
				nbootstrap += threads[k].nbootstraps;

			fprintf(fouts.autosim_fout, "\t%d", nbootstrap);
			if (nbootstrap > 1)
				print_bootstrap_output(autosim_bootstrap_estimates, autosim_observables, autosim_nestimates, NBOOTSTRAP, valid_bootstrap, valid_observable, fouts.autosim_fout);

			fprintf(fouts.autosim_fout, "\n");

		} //raw only

	}

	if (!flags.raw_only) {
		fclose(fouts.autosim_fout);
	}
	return 0;
}

// Time Windows
int do_time_windows(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int nestimates, double extra_fpr, double extra_sens, quick_random& qrand, vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP) {

	int idx = 0;

	for (unsigned int i = 0; i < indata.time_windows.size(); i++) {
		for (unsigned int j = 0; j < indata.age_ranges.size(); j++) {
			fprintf(stderr, "Working on Time Window %d - %d and Age Range %d - %d\n", indata.time_windows[i].first, indata.time_windows[i].second, indata.age_ranges[j].first,
				indata.age_ranges[j].second);

			// Collect Scores
			int nids, checksum;
			if (collect_all_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.time_windows[i], indata.age_ranges[j], indata.byears, indata.censor,
				work.idstrs, work.dates, work.days, work.years, work.scores, work.ages, work.id_starts, work.id_nums, work.types, &nids, &checksum) == -1) {
				fprintf(stderr, "Score Collection failed\n");
				return -1;
			}

			if (!flags.raw_only) {
				fprintf(fouts.fout, "%d-%d\t%d-%d\t%d", indata.time_windows[i].first, indata.time_windows[i].second, indata.age_ranges[j].first, indata.age_ranges[j].second, checksum);


				vector<vector<bool> > valid_bootstrap(NBOOTSTRAP);
				vector<vector<double> > bootstrap_estimates(NBOOTSTRAP);
				vector<double> observed_incidence(NBOOTSTRAP, -1.0);

				vector<bool> valid_observables;
				vector<double> observables;
				double observable_incidence = -1.0;

				time_t start = time(NULL);

				// Observed Parameters

				observables.resize(nestimates);
				all_stats istats;

				double temp_incidence;
				if (get_bootstrap_stats(work.scores, work.ages, work.types, work.id_starts, work.id_nums, nids, istats, indata.incidence_rate, &temp_incidence, flags.use_last, threaded_qrand[0], 1) == 0) {
					valid_observables.resize(nestimates, true);
					get_bootstrap_estimate(istats, observables, temp_incidence, extra_fpr, extra_sens, flags.all_fpr, valid_observables);
					observable_incidence = temp_incidence;
				}
				else
					valid_observables.resize(nestimates, false);

				// Bootstraping estimate of parameters ....
				time_windows_params gen_params;
				gen_params.nestimates = nestimates;
				gen_params.nids = nids;
				gen_params.bootstrap_estimates = (vector<vector<double> > *)& bootstrap_estimates;
				gen_params.valid_bootstrap = (vector<vector<bool> > *)& valid_bootstrap;
				gen_params.work = (work_space *)& work;
				gen_params.extra_fpr = extra_fpr;
				gen_params.extra_sens = extra_sens;
				gen_params.all_fpr = flags.all_fpr;
				gen_params.incidence_rate = (map<int, double> *) &(indata.incidence_rate);
				gen_params.use_last = flags.use_last;
				gen_params.observed_incidence = (vector<double> *)& observed_incidence;

				vector<time_windows_thread_params> threads(nthreads);
				int k = 0;
				int jump = NBOOTSTRAP / nthreads;
				for (k = 0; k < nthreads; k++) {
					threads[k].from = k*jump;
					threads[k].to = (k + 1)*jump - 1;
					threads[k].general_params = &gen_params;
					threads[k].qrand = &(threaded_qrand[k]);
					threads[k].state = 0;
					threads[k].nbootstraps = 0;
				}

				threads[nthreads - 1].to = NBOOTSTRAP - 1;

				vector<thread> th_handle(nthreads);
				for (int i = 0; i < nthreads; i++) {
					th_handle[i] = thread(time_windows_thread, (void *)&threads[i]);
				}

				int n_state = 0;
				while (n_state < nthreads) {
					this_thread::sleep_for(chrono::milliseconds(10));
					n_state = 0;
					for (int i = 0; i < nthreads; i++)
						n_state += threads[i].state;
				}
				for (int i = 0; i < nthreads; i++)
					th_handle[i].join();

				fprintf(stderr, "Bootstraping took %f secs\n", difftime(time(NULL), start));

				// Print output
				int nbootstrap = 0;
				for (int k = 0; k < nthreads; k++)
					nbootstrap += threads[k].nbootstraps;

				fprintf(fouts.fout, "\t%d", nbootstrap);

				if (nbootstrap > 1)
					print_bootstrap_output(bootstrap_estimates, observables, nestimates, nbootstrap, valid_bootstrap, valid_observables, fouts.fout);

				fprintf(fouts.fout, "\n");

				// Average incidence
				if (nbootstrap > 0) {

					int num = 0;
					double sum = 0;
					for (int ibs = 0; ibs < nbootstrap; ibs++) {
						if (observed_incidence[ibs] != -1.0) {
							num++;
							sum += observed_incidence[ibs];
						}
					}
					fprintf(stderr, "Mean observed incidence = %f\n", sum / num);
				}

			} // raw_only

			  // Raw and Info files
			char prefix[MAX_STRING_LEN];
			sprintf(prefix, "%d-%d-%d-%d", indata.time_windows[i].first, indata.time_windows[i].second, indata.age_ranges[j].first, indata.age_ranges[j].second);
			print_raw_and_info(work.idstrs, work.dates, work.scores, work.types, work.id_starts, work.id_nums, nids, qrand, fouts.raw_fout, fouts.info_fout, prefix, flags.use_last);
		}
	}
	fprintf(stderr, "bootstrap_analysis run has finished.\n");

	return 0;
}

// Periodict AutoSim - Considering each period on it's own, taking all scores in the period
int do_periodic_autosim(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, char *autosim_param_names, double extra_fpr, int period,
	vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP) {

	int max_autosim_nperiods = 0;
	int first_days = get_day(indata.first_date);
	vector<int> all_autosim_nperiods(indata.age_ranges.size());
	vector<vector<double> > all_autosim_values(indata.age_ranges.size());
	vector<vector<bool> > all_autosim_flags(indata.age_ranges.size());

	for (unsigned int j = 0; j < indata.age_ranges.size(); j++) {
		fprintf(stderr, "Working on Periodic AutoSim on Age Range %d - %d\n", indata.age_ranges[j].first, indata.age_ranges[j].second);

		// AutoSim
		// Collect Scores
		int nids, nperiods, checksum;

		if (collect_periodic_autosim_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.age_ranges[j], indata.byears, indata.censor,
			work.idstrs, work.dates, work.days, work.years, work.scores, work.gaps, work.id_starts, work.id_nums, work.types, &nids,
			period, &nperiods, &checksum) == -1) {
			fprintf(stderr, "Score Collection for AutoSim failed\n");
			return -1;
		}

		all_autosim_nperiods[j] = nperiods;
		if (nperiods > max_autosim_nperiods)
			max_autosim_nperiods = nperiods;

		int periodic_autosim_nestimates = autosim_nestimates * nperiods;

		// Periodict AutoSim - Considering each period on it's own, taking all scores in the period
		vector<vector<double> > periodic_autosim_bootstrap_estimates(NBOOTSTRAP);
		vector<double> periodic_autosim_observables;

		vector<vector<bool> > valid_bootstrap(NBOOTSTRAP);
		vector<bool> valid_observables;

		time_t start = time(NULL);

		autosim_params gen_params;
		gen_params.tot_nestimates = periodic_autosim_nestimates;
		gen_params.nestimates = autosim_nestimates;
		gen_params.nids = nids;
		gen_params.estimates = (vector<vector<double> > *)& periodic_autosim_bootstrap_estimates;
		gen_params.validity = (vector<vector<bool> > *)& valid_bootstrap;
		gen_params.work = (work_space *)& work;
		gen_params.extra_fpr = extra_fpr;
		gen_params.period = period;
		gen_params.nperiods = nperiods;
		gen_params.first_days = first_days;

		// Observed values
		int *all_ids = (int *)malloc(nids*sizeof(int));
		assert(all_ids != NULL);

		for (int i = 0; i < nids; i++)
			all_ids[i] = i;

		periodic_autosim_observables.resize(periodic_autosim_nestimates);
		valid_observables.clear();
		get_periodic_autosim_parameters(all_ids, work.types, work.id_starts, work.id_nums, nids, work.scores, work.gaps, work.days, periodic_autosim_observables, threaded_qrand[0], extra_fpr, first_days, period, nperiods,
			periodic_autosim_nestimates, autosim_nestimates, valid_observables);
		free(all_ids);

		vector<autosim_thread_params> threads(nthreads);
		int k = 0;
		int jump = NBOOTSTRAP / nthreads;
		for (k = 0; k < nthreads; k++) {
			threads[k].from = k*jump;
			threads[k].to = (k + 1)*jump - 1;
			threads[k].general_params = &gen_params;
			threads[k].qrand = &(threaded_qrand[k]);
			threads[k].state = 0;
		}

		threads[nthreads - 1].to = NBOOTSTRAP - 1;

		vector<thread> th_handle(nthreads);
		for (int i = 0; i < nthreads; i++) {
			th_handle[i] = thread(periodic_autosim_thread, (void *)&threads[i]);
		}

		int n_state = 0;
		while (n_state < nthreads) {
			this_thread::sleep_for(chrono::milliseconds(10));
			n_state = 0;
			for (int i = 0; i < nthreads; i++)
				n_state += threads[i].state;
		}
		for (int i = 0; i < nthreads; i++)
			th_handle[i].join();


		fprintf(stderr, "Bootstraping took %2.1f secs\n", difftime(time(NULL), start));

		collect_periodic_estimates(periodic_autosim_bootstrap_estimates, periodic_autosim_observables, valid_bootstrap, valid_observables,
			indata.age_ranges[j], periodic_autosim_nestimates, checksum, all_autosim_values[j], all_autosim_flags[j], NBOOTSTRAP);
	}

	// Print

	// Header
	fprintf(fouts.periodic_autosim_fout, "Age-Range\tCheckSum\tNBootStrap");
	for (int iperiod = 0; iperiod < max_autosim_nperiods; iperiod++) {
		int start_date = get_date(first_days + period * iperiod);
		int end_date = get_date(first_days + period * (iperiod + 1));
		for (int i = 0; i < autosim_nestimates; i++)
			fprintf(fouts.periodic_autosim_fout, "\tPeriod-%d-%d-%s-Obs\tPeriod-%d-%d-%s-Mean\tPeriod-%d-%d-%s-Sdv\tPeriod-%d-%d-%s-CI-Lower\tPeriod-%d-%d-%s-CI-Upper",
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN);
	}
	fprintf(fouts.periodic_autosim_fout, "\n");

	for (unsigned int j = 0; j < indata.age_ranges.size(); j++) {

		fprintf(fouts.periodic_autosim_fout, "%d-%d\t%d\t%d", (int)all_autosim_values[j][0], (int)all_autosim_values[j][1], (int)all_autosim_values[j][2], (int)all_autosim_values[j][3]);
		int n_base = 5 * autosim_nestimates * all_autosim_nperiods[j];
		int n_full = 5 * autosim_nestimates * max_autosim_nperiods;

		for (int i = 0; i < n_base; i++) {
			if (all_autosim_flags[j][i + 4])
				fprintf(fouts.periodic_autosim_fout, "\t%.3f", all_autosim_values[j][i + 4]);
			else
				fprintf(fouts.periodic_autosim_fout, "\tNA");
		}

		for (int i = n_base; i < n_full; i++)
			fprintf(fouts.periodic_autosim_fout, "\tNA");
		fprintf(fouts.periodic_autosim_fout, "\n");
	}

	fclose(fouts.periodic_autosim_fout);
	return 0;
}

// Periodic Cuts - Considering given dates (periodic) and taking the last score in the period before as the relevant score
int do_periodic_cuts(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, char *autosim_param_names, double extra_fpr, int period, int gap,
	vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP) {

	int max_cuts_nperiods = 0;
	int first_days = get_day(indata.first_date);
	vector<int> all_cuts_nperiods(indata.age_ranges.size());
	vector<vector<double> > all_cuts_values(indata.age_ranges.size());
	vector<vector<bool> > all_cuts_flags(indata.age_ranges.size());

	for (unsigned int j = 0; j < indata.age_ranges.size(); j++) {
		// Collect Scores
		fprintf(stderr, "Working on Periodic Cuts on Age Range %d - %d\n", indata.age_ranges[j].first, indata.age_ranges[j].second);

		int nids, nperiods, checksum;

		if (collect_periodic_cuts_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.age_ranges[j], indata.byears, indata.censor,
			work.idstrs, work.dates, work.days, work.years, work.scores, work.time_to_cancer, work.id_starts, work.id_nums, work.types, &nids, period, gap,
			&nperiods, &checksum) == -1) {
			fprintf(stderr, "Score Collection for Periodic Cuts failed\n");
			return -1;
		}

		all_cuts_nperiods[j] = nperiods;
		if (nperiods > max_cuts_nperiods)
			max_cuts_nperiods = nperiods;

		int periodic_cuts_nestimates = autosim_nestimates * nperiods;

		vector<vector<double> > periodic_cuts_bootstrap_estimates(NBOOTSTRAP);
		vector<vector<bool> > valid_bootstrap(NBOOTSTRAP);

		vector<double> periodic_cuts_observables;
		vector<bool> valid_observables;

		time_t start = time(NULL);

		autosim_params gen_params;
		gen_params.tot_nestimates = periodic_cuts_nestimates;
		gen_params.nestimates = autosim_nestimates;
		gen_params.nids = nids;
		gen_params.estimates = (vector<vector<double> > *)& periodic_cuts_bootstrap_estimates;
		gen_params.validity = (vector<vector<bool> > *)& valid_bootstrap;
		gen_params.work = (work_space *)& work;
		gen_params.extra_fpr = extra_fpr;
		gen_params.period = period;
		gen_params.nperiods = nperiods;
		gen_params.first_days = first_days;

		// Observed values
		int *all_ids = (int *)malloc(nids*sizeof(int));
		assert(all_ids != NULL);

		for (int i = 0; i < nids; i++)
			all_ids[i] = i;

		periodic_cuts_observables.resize(periodic_cuts_nestimates);
		valid_observables.clear();
		get_periodic_cuts_parameters(all_ids, work.types, work.id_starts, work.id_nums, nids, work.scores, work.time_to_cancer, work.days, periodic_cuts_observables, threaded_qrand[0], extra_fpr, first_days, period, nperiods,
			periodic_cuts_nestimates, autosim_nestimates, valid_observables);
		free(all_ids);

		// Bootstrap Estimates
		vector<autosim_thread_params> threads(nthreads);
		int k = 0;
		int jump = NBOOTSTRAP / nthreads;
		for (k = 0; k < nthreads; k++) {
			threads[k].from = k*jump;
			threads[k].to = (k + 1)*jump - 1;
			threads[k].general_params = &gen_params;
			threads[k].qrand = &(threaded_qrand[k]);
			threads[k].state = 0;
		}

		threads[nthreads - 1].to = NBOOTSTRAP - 1;

		vector<thread> th_handle(nthreads);
		for (int i = 0; i < nthreads; i++) {
			th_handle[i] = thread(periodic_cuts_thread, (void *)&threads[i]);
		}

		int n_state = 0;
		while (n_state < nthreads) {
			this_thread::sleep_for(chrono::milliseconds(10));
			n_state = 0;
			for (int i = 0; i < nthreads; i++)
				n_state += threads[i].state;
		}
		for (int i = 0; i < nthreads; i++)
			th_handle[i].join();

		fprintf(stderr, "Bootstraping took %2.1f secs\n", difftime(time(NULL), start));

		collect_periodic_estimates(periodic_cuts_bootstrap_estimates, periodic_cuts_observables, valid_bootstrap, valid_observables, indata.age_ranges[j], periodic_cuts_nestimates, checksum, all_cuts_values[j], all_cuts_flags[j], NBOOTSTRAP);
	}

	// Print Periodic Cuts	
	// Header
	fprintf(fouts.periodic_cuts_fout, "Age-Range\tCheckSum\tNBootStrap");
	for (int iperiod = 0; iperiod < max_cuts_nperiods; iperiod++) {
		int start_date = get_date(first_days + period * iperiod);
		int end_date = get_date(first_days + period * (iperiod + 1));
		for (int i = 0; i < autosim_nestimates; i++)
			fprintf(fouts.periodic_cuts_fout, "\tPeriod-%d-%d-%s-Obs\tPeriod-%d-%d-%s-Mean\tPeriod-%d-%d-%s-Sdv\tPeriod-%d-%d-%s-CI-Lower\tPeriod-%d-%d-%s-CI-Upper",
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN,
				start_date, end_date, autosim_param_names + i*MAX_STRING_LEN);
	}
	fprintf(fouts.periodic_cuts_fout, "\n");

	for (unsigned int j = 0; j < indata.age_ranges.size(); j++) {

		fprintf(fouts.periodic_cuts_fout, "%d-%d\t%d\t%d", (int)all_cuts_values[j][0], (int)all_cuts_values[j][1], (int)all_cuts_values[j][2], (int)all_cuts_values[j][3]);
		int n_base = 5 * autosim_nestimates * all_cuts_nperiods[j];
		int n_full = 5 * autosim_nestimates * max_cuts_nperiods;

		for (int i = 0; i < n_base; i++) {
			if (all_cuts_flags[j][i + 4])
				fprintf(fouts.periodic_cuts_fout, "\t%.3f", all_cuts_values[j][i + 4]);
			else
				fprintf(fouts.periodic_cuts_fout, "\tNA");
		}

		for (int i = n_base; i < n_full; i++)
			fprintf(fouts.periodic_cuts_fout, "\tNA");
		fprintf(fouts.periodic_cuts_fout, "\n");
	}

	return 0;
}

void collect_periodic_estimates(vector<vector<double> >& periodic_autosim_bootstrap_estimates, vector<double>& observables, vector<vector<bool> >& valid, vector<bool>& valid_obs, pair<int, int>& age_range,
	int nestimates, int checksum, vector<double>& all_autosim_values, vector<bool>& all_autosim_flags, int NBOOTSTRAP) {

	// Print output
	all_autosim_values.push_back(age_range.first);
	all_autosim_flags.push_back(true);

	all_autosim_values.push_back(age_range.second);
	all_autosim_flags.push_back(true);

	all_autosim_values.push_back(checksum);
	all_autosim_flags.push_back(true);

	all_autosim_values.push_back(NBOOTSTRAP);
	all_autosim_flags.push_back(true);

	for (int l = 0; l < nestimates; l++) {

		if (valid_obs[l]) {
			all_autosim_values.push_back(observables[l]);
			all_autosim_flags.push_back(true);
		}
		else {
			all_autosim_values.push_back(-1.0);
			all_autosim_flags.push_back(false);
		}

		vector<double> values;
		int num = 0;
		double sum = 0, sum2 = 0;
		for (int k = 0; k < NBOOTSTRAP; k++) {
			if (valid[k][l]) {
				double value = periodic_autosim_bootstrap_estimates[k][l];
				sum += value;
				sum2 += value * value;
				values.push_back(value);
				num++;
			}
		}

		if (num) {
			sort(values.begin(), values.end());
			double mean = sum / num;
			double sdv = sqrt((sum2 - sum*mean) / (num - 1));
			double ci_lower = values[(int)(0.025*num)];
			double ci_upper = values[(int)(0.975*num)];

			all_autosim_values.push_back(mean); all_autosim_flags.push_back(true);
			all_autosim_values.push_back(sdv); all_autosim_flags.push_back(true);
			all_autosim_values.push_back(ci_lower); all_autosim_flags.push_back(true);
			all_autosim_values.push_back(ci_upper); all_autosim_flags.push_back(true);

		}
		else {
			all_autosim_values.push_back(-1.0); all_autosim_flags.push_back(false);
			all_autosim_values.push_back(-1.0); all_autosim_flags.push_back(false);
			all_autosim_values.push_back(-1.0); all_autosim_flags.push_back(false);
			all_autosim_values.push_back(-1.0); all_autosim_flags.push_back(false);
		}
	}
}

// Threading functions
void autosim_thread(void *p)
{
	autosim_thread_params *tp = (autosim_thread_params *)p;
	autosim_params *gp = tp->general_params;

	int *sampled_ids = (int *)malloc(gp->nids*sizeof(int));
	assert(sampled_ids != NULL);

	for (int ibs = tp->from; ibs <= tp->to; ibs++) {
		(*(gp->estimates))[ibs].resize(gp->nestimates, -1.0);
		(*(gp->validity))[ibs].resize(gp->nestimates, false);
		sample_ids(sampled_ids, gp->nids, *(tp->qrand));
		get_autosim_parameters(sampled_ids, (gp->work)->types, (gp->work)->id_starts, (gp->work)->id_nums, gp->nids, (gp->work)->scores, (gp->work)->gaps, (*(gp->estimates))[ibs], (*(gp->validity))[ibs], *(tp->qrand), gp->extra_fpr);

		for (int i = 0; i < gp->nestimates; i++) {
			if ((*(gp->validity))[ibs][i]) {
				tp->nbootstraps++;
				break;
			}
		}

	}

	free(sampled_ids);
	tp->state = 1;

}

void  periodic_autosim_thread(void *p)
{
	autosim_thread_params *tp = (autosim_thread_params *)p;
	autosim_params *gp = tp->general_params;

	int *sampled_ids = (int *)malloc(gp->nids*sizeof(int));
	assert(sampled_ids != NULL);


	for (int ibs = tp->from; ibs <= tp->to; ibs++) {

		(*(gp->estimates))[ibs].resize(gp->tot_nestimates);
		sample_ids(sampled_ids, gp->nids, *(tp->qrand));
		get_periodic_autosim_parameters(sampled_ids, (gp->work)->types, (gp->work)->id_starts, (gp->work)->id_nums, gp->nids, (gp->work)->scores, (gp->work)->gaps, (gp->work)->days,
			(*(gp->estimates))[ibs], *(tp->qrand), gp->extra_fpr, gp->first_days, gp->period, gp->nperiods, gp->tot_nestimates, gp->nestimates, (*(gp->validity))[ibs]);
	}


	free(sampled_ids);
	tp->state = 1;

}

void  periodic_cuts_thread(void *p)
{
	autosim_thread_params *tp = (autosim_thread_params *)p;
	autosim_params *gp = tp->general_params;

	int *sampled_ids = (int *)malloc(gp->nids*sizeof(int));
	assert(sampled_ids != NULL);


	for (int ibs = tp->from; ibs <= tp->to; ibs++) {

		(*(gp->estimates))[ibs].resize(gp->tot_nestimates);
		sample_ids(sampled_ids, gp->nids, *(tp->qrand));
		(*(gp->validity))[ibs].clear();
		get_periodic_cuts_parameters(sampled_ids, (gp->work)->types, (gp->work)->id_starts, (gp->work)->id_nums, gp->nids, (gp->work)->scores, (gp->work)->time_to_cancer, (gp->work)->days,
			(*(gp->estimates))[ibs], *(tp->qrand), gp->extra_fpr, gp->first_days, gp->period, gp->nperiods, gp->tot_nestimates, gp->nestimates, (*(gp->validity))[ibs]);
	}


	free(sampled_ids);
	tp->state = 1;

}

void time_windows_thread(void *p)
{
	time_windows_thread_params *tp = (time_windows_thread_params *)p;
	time_windows_params *gp = tp->general_params;

	double incidence;
	for (int ibs = tp->from; ibs <= tp->to; ibs++) {

		(*(gp->bootstrap_estimates))[ibs].resize(gp->nestimates);
		all_stats istats;

		if (get_bootstrap_stats((gp->work)->scores, (gp->work)->ages, (gp->work)->types, (gp->work)->id_starts, (gp->work)->id_nums, gp->nids, istats, *(gp->incidence_rate), &incidence, gp->use_last, *(tp->qrand), 0) == 0) {
			(*(gp->valid_bootstrap))[ibs].resize(gp->nestimates, true);
			get_bootstrap_estimate(istats, (*(gp->bootstrap_estimates))[ibs], incidence, gp->extra_fpr, gp->extra_sens, gp->all_fpr, (*(gp->valid_bootstrap))[ibs]);
			tp->nbootstraps++;
			(*(gp->observed_incidence))[ibs] = incidence;
		}
		else
			(*(gp->valid_bootstrap))[ibs].resize(gp->nestimates, false);

	}

	tp->state = 1;
}
