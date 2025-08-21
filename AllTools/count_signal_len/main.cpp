#include "Cmd_Args.h"
#include <MedProcessTools/MedProcessTools/MedModel.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void get_quantiles(const map<int, int> &cnts, vector<int> &res) {
	res.clear();
	res.resize(100 + 1); //1-100 for each percentage + 99.9% last one:

	long long tot_cnt_pids = 0;
	for (auto &it : cnts)
		tot_cnt_pids += it.second;

	double last_q = 0.999;
	bool has_last = false;
	long long current_q = 0;
	double current_q_f;
	int ind = 0; //quantile ind+1
	for (auto &it : cnts) {
		current_q += it.second;
		current_q_f = current_q / (double)tot_cnt_pids; //current quantile

		if (current_q_f >= last_q && !has_last) {
			has_last = true;
			res[res.size() - 1] = it.first;
		}

		while (ind < res.size() && current_q_f >= (ind + 1) / 100.0) {
			//passed current quantile
			//update counts:
			res[ind] = it.first;
			++ind;
		}
		if (ind >= res.size()) {
			ind = res.size() - 1;
			res[ind] = it.first;
			break;
		}
	}
}

int main(int argc, char * argv[]) {
	Program_Args args;
	int exit_code = args.parse_parameters(argc, argv);
	if (exit_code == -1)
		return 0;
	if (exit_code < 0)
		MTHROW_AND_ERR("unable to parse arguments\n");

	MedPidRepository rep;
	if (rep.init(args.rep) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());

	if (!args.model_path.empty()) {
		//fetch signal list from model:
		MedModel model;
		model.read_from_file(args.model_path);
		model.fit_for_repository(rep);
		model.collect_and_add_virtual_signals(rep);
		model.filter_rep_processors();
		args.sigs.clear();
		model.get_required_signal_names(args.sigs);
	}

	vector<int> empty;
	if (rep.read_all(args.rep, empty, args.sigs) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());
	vector<int> sids(args.sigs.size());
	for (size_t i = 0; i < sids.size(); ++i)
	{
		sids[i] = rep.sigs.sid(args.sigs[i]);
		if (sids[i] < 0)
			MTHROW_AND_ERR("Error - unknown signal %s\n", args.sigs[i].c_str());
	}

	ofstream fw(args.output_path);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open file %s for write\n", args.output_path.c_str());
	//Let's iterate over "args.sigs" - for each one fetch stats: signal, length, count. 
	MedProgress progress("calc lengths", args.sigs.size(), 30, 1);
	vector<map<int, int>> sig_to_counts(args.sigs.size()); //count is map from length to count
	for (int i = 0; i < args.sigs.size(); ++i)
	{
		int sid = sids[i];
		map<int, int> &cnts = sig_to_counts[i]; //length to count
		UniversalSigVec usv;
		for (int j = 0; j < rep.pids.size(); ++j)
		{
			int pid = rep.pids[j];
			rep.uget(pid, sid, usv);
			//count till date:
			int cnt = 0;
			for (int k = 0; k < usv.len; ++k)
			{
				if (usv.Time(k) >= args.till_date)
					break;
				++cnt;
			}
			//#pragma omp critical
			++cnts[cnt];
		}
		progress.update();
	}
	fw << "signal\t" << "length\t" << "count" << "\n";
	//write to file signal length count
	for (size_t i = 0; i < args.sigs.size(); ++i)
	{
		const string &sig = args.sigs[i];
		const map<int, int> &cnts = sig_to_counts[i]; //length to count
		for (auto &it : cnts)
			fw << sig << "\t" << it.first << "\t" << it.second << "\n";
	}
	fw.close();
	//Then final 1-100% quantiles of total signal lengths for this list (call this signal All, lengths 1-100, and the counts)
	//calculate percentiles from cnts!
	vector<vector<int>> sig_quantiles(args.sigs.size());
	for (size_t i = 0; i < args.sigs.size(); ++i)
	{
		const map<int, int> &cnts = sig_to_counts[i]; //length to count
		vector<int> &res_q = sig_quantiles[i]; //1-100, 99.9 (as last)
		get_quantiles(cnts, res_q);
	}

	//Print element length for 99%, 99.9%, 100% quantiles + count!
	int tot_res_99 = 0;
	int tot_res_100 = 0;
	int tot_res_99_9 = 0;
	for (size_t i = 0; i < args.sigs.size(); ++i)
	{
		const string &sig = args.sigs[i];
		const vector<int> &res_q = sig_quantiles[i];
		int res_99 = res_q[98];
		int res_100 = res_q[99];
		int res_99_9 = res_q[100];
		MLOG("signal %s :: [99%% = %d, 99.9%% = %d, 100%% = %d]\n", 
			sig.c_str(), res_99, res_99_9, res_100);
		tot_res_99 += res_99;
		tot_res_100 += res_100;
		tot_res_99_9 += res_99_9;
	}

	MLOG("##############################################\n");
	MLOG("To reach 99% you need %d, to reach 99.9% you need %d and to reach 100% you need %d\n",
		tot_res_99, tot_res_99_9, tot_res_100);
	MLOG("##############################################\n");

	return 0;
}