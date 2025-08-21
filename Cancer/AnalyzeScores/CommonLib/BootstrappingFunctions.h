#include "AnalyzeScores.h"


struct autosim_params {
	int nestimates, tot_nestimates;
	int nids;
	vector<vector<double> > *estimates;
	vector<vector<bool> > *validity;
	work_space *work;
	double extra_fpr;

	// For Periodic Autosim
	int period, nperiods;
	int first_days;
};

struct autosim_thread_params {
	int from;
	int to;
	autosim_params *general_params;
	quick_random *qrand;
	int state;
	int nbootstraps;
};


struct time_windows_params {
	int nestimates;
	int nids;
	vector<vector<double> > *bootstrap_estimates;
	vector<vector<bool> > *valid_bootstrap;
	map<int, double> *incidence_rate;
	work_space *work;
	double extra_fpr;
	double extra_sens;
	bool all_fpr;
	bool use_last;
	vector<double> *observed_incidence;
};

struct time_windows_thread_params {
	int from;
	int to;
	time_windows_params *general_params;
	quick_random *qrand;
	int state;
	int nbootstraps;
};

void autosim_thread(void *p);
void periodic_autosim_thread(void *p);
void periodic_cuts_thread(void *p);
void time_windows_thread(void *p);


int init_param_names(double extra_fpr, double extra_sim_fpr, double extra_sens, bool all_fpr, int *nestimates, char **param_names, int *nautosim_estimates, char **autosim_param_names);
int open_all_output_files(const char *out_file, running_flags& flags, int period, char *param_names, int nestimates, char *autosim_param_names, int autosim_nestimates, out_fps& fouts);

int do_autosim(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, double extra_fpr, vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP);
int do_time_windows(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int nestimates, double extra_fpr, double extra_sens, quick_random& qrand, vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP);
int do_periodic_autosim(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, char *autosim_param_names, double extra_fpr, int period,
	vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP);
int do_periodic_cuts(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, char *autosim_param_names, double extra_fpr, int period, int gap,
	vector<quick_random>& threaded_qrand, int nthreads, int NBOOTSTRAP);
void collect_periodic_estimates(vector<vector<double> >& periodic_autosim_bootstrap_estimates, vector<double>& observables, vector<vector<bool> >& valid, vector<bool>& valid_obs, pair<int, int>& age_range,
	int nestimates, int checksum, vector<double>& all_autosim_values, vector<bool>& all_autosim_flags, int NBOOTSTRAP);