#include "Cmd_Args.h"
#include <string>
#include <unordered_set>
#include <algorithm>
#include <fstream>
#include <random>
#include <omp.h>
#include <boost/filesystem.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/regex.hpp>
#include <regex>
#include <MedAlgo/MedAlgo/BinSplitOptimizer.h>
#include <MedIO/MedIO/MedIO.h>
#include <InfraMed/InfraMed/InfraMed.h>

using namespace std;

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void test_res(const vector<float> &data, ofstream &log_file, const string &signal_nm, double threshold = 0.001, double factor_threshold = 0.3,
	double tails_ignore = 0.05, int max_allowed_peaks = 5, int min_diff = 100) {
	map<float, int> hist;
	for (float n : data)
		++hist[n];
	if (hist.size() < 3)
		return;

	int total_sz = (int)data.size();
	auto it = hist.begin();
	int prev[2];
	prev[0] = it->second; ++it;
	prev[1] = it->second;
	float prev_val = it->first;
	++it;
	double tot_sum = prev[0] + prev[1];

	vector<float> peak_vals;
	for (; it != hist.end(); ++it)
	{
		if (tot_sum / total_sz > 1 - tails_ignore)
			break; //don't search peaks in tails - end tail stop
		if (tot_sum / total_sz < tails_ignore) {
			tot_sum += it->second;
			continue; //don't search peaks in tails - start of tail - skip
		}

		//check for prev[1] > prev[0] && prev[1] > current (it's a local peak)
		int cnt1 = prev[1] - prev[0];
		int cnt2 = prev[1] - it->second;
		double diff1 = (prev[1] - prev[0]) / double(total_sz);
		double diff2 = (prev[1] - it->second) / double(total_sz);
		double f1 = (prev[1] / prev[0]) - 1;
		double f2 = (prev[1] / it->second) - 1;

		if ((cnt1 > min_diff && cnt2 > min_diff)
			&& ((diff1 > threshold && diff2 > threshold) || (f1 > factor_threshold && f2 > factor_threshold)))
			peak_vals.push_back(prev_val);
		//update prevs
		prev[0] = prev[1];
		prev[1] = it->second;
		prev_val = it->first;
		tot_sum += it->second;
	}
	stringstream ls_vals;
	if (!peak_vals.empty())
		ls_vals << peak_vals[0];
	for (size_t i = 1; i < peak_vals.size(); ++i)
		ls_vals << ", " << peak_vals[i];

	if (peak_vals.size() > max_allowed_peaks)
		medial::print::log_with_file(log_file, "Warning: %s data has %zu local peaks - may be resolution problem.\nLook At peaks in [%s]\n",
			signal_nm.c_str(), peak_vals.size(), ls_vals.str().c_str());
}

void test_unit(const vector<float> &data, ofstream &log_file, const string &signal_nm, double diff_threshold = 5, double factor_threshold = 0.3) {
	map<float, int> hist;
	for (float n : data)
		++hist[n];
	if (hist.size() < 3)
		return;

	vector<pair<int, float>> ordered_counts(hist.size());
	int ind = 0;
	double res_val = 0;
	float prev = hist.begin()->first;
	for (const auto &it : hist)
	{
		ordered_counts[ind] = pair<int, float>(it.second, it.first);
		++ind;
		res_val += it.first - prev;
		prev = it.first;
	}
	res_val /= hist.size() - 1;
	sort(ordered_counts.begin(), ordered_counts.end(), [](const pair<int, float> &a, const pair<int, float> &b) {
		return a.first > b.first; //from big to small
	});


	//find first 2 peaks that are not adj to each other - than check diff between peaks:
	pair<int, float> &max_peak = ordered_counts[0];
	float prev_after = max_peak.second, prev_before = max_peak.second;
	pair<int, float> second_peak = pair<int, float>(0, (float)0);

	for (size_t i = 1; i < ordered_counts.size(); ++i)
	{
		if (ordered_counts[i].second > max_peak.second) {
			//check diffs - and if new peak in other region:
			if (ordered_counts[i].second > prev_after) {
				float diff = (ordered_counts[i].second - prev_after) / res_val;
				float f = (max_peak.first - ordered_counts[i].first) / double(ordered_counts[i].first);
				if (diff > diff_threshold && f < factor_threshold) {
					second_peak = ordered_counts[i];
					break;
				}

				prev_after = ordered_counts[i].second;
			}
		}
		else {
			if (ordered_counts[i].second < prev_before) {
				float diff = (prev_before - ordered_counts[i].second) / res_val;
				float f = (max_peak.first - ordered_counts[i].first) / double(ordered_counts[i].first);
				if (diff > diff_threshold && f < factor_threshold) {
					second_peak = ordered_counts[i];
					break;
				}

				prev_before = ordered_counts[i].second;
			}
		}
	}

	//if has second peak which is far away and big enough show it
	if (second_peak.first > 0) {
		float f = (max_peak.first - second_peak.first) / double(second_peak.first);
		medial::print::log_with_file(log_file, "Warning: %s has second peak - maybe mixture of signals/units. "
			"first peak at %2.4f(%d), second at %2.4f(%d), res=%f, second_down_factor=%2.3f\n",
			signal_nm.c_str(), max_peak.second, max_peak.first, second_peak.second, second_peak.first, res_val, f);
	}
}

void test_problems(const vector<float> &data, const test_params &pr, const string &log_path, const string &signal_nm) {
	ofstream log_file(log_path, ios::app);
	//test resolution problems - count peaks num:
	test_res(data, log_file, signal_nm, pr.res_threshold, pr.res_factor_threshold, pr.res_tails_ignore, pr.res_max_allowed_peaks,
		pr.res_min_diff_num);
	//test if has unit problem? - if has more than 1 "global" peak
	test_unit(data, log_file, signal_nm, pr.unit_diff_threshold, pr.unit_factor_threshold);
	//test for not similar dist
	log_file.close();
}

void print_options(const string &pt, const string &rep_path) {
	boost::filesystem::path p(pt);
	MLOG("Options are:\n");
	if (!pt.empty()) {
		boost::regex re("[0-9]+$");
		unordered_set<string> names;
		for (auto& entry : boost::make_iterator_range(boost::filesystem::directory_iterator(p), {})) {
			string cand = entry.path().filename().generic_string();
			cand = boost::regex_replace(cand, re, "");
			names.insert(cand);
		}
		vector<string> sorted(names.begin(), names.end());
		sort(sorted.begin(), sorted.end());

		for (int i = (int)sorted.size() - 1; i >= 0; --i)
			MLOG("%s\n", sorted[i].c_str());
	}
	else {
		MedRepository rep;
		if (rep.init(rep_path) < 0)
			MTHROW_AND_ERR("Error can't read repository %s\n", rep_path.c_str());
		vector<string> sorted(rep.sigs.signals_names.begin(), rep.sigs.signals_names.end());
		sort(sorted.begin(), sorted.end());

		for (int i = 0; i < sorted.size(); ++i)
			MLOG("%s\n", sorted[i].c_str());
	}
}

void fetch_line(const char *buff, int size, string &line) {
	static vector<bool> new_line_map(256);
	new_line_map['\n'] = true;
	new_line_map['\r'] = true;

	int start_pos = -1, end_pos = -1;
	for (int i = 0; i < size; ++i)
	{
		if (new_line_map[buff[i]]) {
			if (start_pos < 0) {
				while (new_line_map[buff[i]])
					++i;
				start_pos = i;
			}
			else
			{
				end_pos = i;
				break;
			}
		}
	}

	if (start_pos > 0 && end_pos > 0)
		line = string(buff + start_pos, end_pos - start_pos);
	else
		line = "";
}

void read_sample_file(const string &fpath, bool has_header, int rand_lines, const string &delimeter, int column_num,
	mt19937 &gen, int buffer_size, vector<float> &data) {
	if (rand_lines == 0) {
		ifstream in(fpath);
		if (!in.good())
			MTHROW_AND_ERR("Error can't open file %s\n", fpath.c_str());
		//no random:
		string line;
		if (has_header)
			getline(in, line);
		while (getline(in, line)) {
			vector<string> tokens;
			boost::split(tokens, line, boost::is_any_of(delimeter));
			if (tokens.size() <= column_num)
				MTHROW_AND_ERR("Error in line:\n%s\nHas only %zu tokens, request %d\n",
					line.c_str(), tokens.size(), column_num);
			float num = stof(tokens[column_num]);
			data.push_back(num);
		}
		return;
	}

	ifstream in(fpath, ios::in | ios::binary | ios::ate);
	if (!in.good())
		MTHROW_AND_ERR("Error can't open file %s\n", fpath.c_str());
	unsigned long long size = in.tellg();
	in.clear();
	in.seekg(0, ios::beg);
	//uniform_int_distribution<unsigned long long> rnd_num((unsigned long long) 0, size - 1);
	uniform_real_distribution<> rnd_num(0, 1);
	vector<unsigned long long> poses(rand_lines);
	for (size_t i = 0; i < rand_lines; ++i)
		poses[i] = rnd_num(gen) * (size - 1);
	sort(poses.begin(), poses.end());

	//string to store the line
	vector<char> buffer_readed(buffer_size);
	string line = "";
	data.reserve(rand_lines);
	bool print_skip = false;
	for (int i = 0; i < poses.size(); ++i) {
		//in.clear();
		in.seekg(poses[i]);
		in.read(buffer_readed.data(), buffer_size);
		fetch_line(buffer_readed.data(), buffer_size, line);
		//read till line and than next line:

		//getline(in, line); //read till end line if in the middle
		//getline(in, line);
		if (line.empty()) {
			if (!print_skip) {
				print_skip = true;
				MLOG("First skip=%d, pos=%llu, file_size-=%llu\n", i, poses[i], size);
			}
			continue;
		}
		//process line
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of(delimeter));
		if (tokens.size() <= column_num)
			MTHROW_AND_ERR("Error in line:\n{%s}\nHas only %zu tokens, request %d\n",
				line.c_str(), tokens.size(), column_num);
		float num = stof(tokens[column_num]);
		data.push_back(num);
	}
	if (data.size() != rand_lines)
		MWARN("Skipped %d lines\n", rand_lines - (int)data.size());
	in.close();
}

float NormalizeData(map<float, float> &data) {
	float totSum = 0;
	for (auto it = data.begin(); it != data.end(); ++it)
	{
		totSum += it->second;
	}
	for (auto it = data.begin(); it != data.end(); ++it)
	{
		data[it->first] = it->second / totSum;
	}
	return totSum;
}

void get_list(const string &signal_name_arg, vector<string> &res, vector<int> &val_channels, 
	const string &rep_path) {
	//If file read file, otherwise use as tokens:
	if (signal_name_arg == "ALL") {
		//take all numeric from repo:
		MedRepository rep;
		if (rep.init(rep_path) < 0)
			MTHROW_AND_ERR("Error can't read repository %s\n", rep_path.c_str());
		for (const string &sig : rep.sigs.signals_names) {
			int sid = rep.sigs.sid(sig);
			if (sid < 0)
				MTHROW_AND_ERR("Error can't find signal %s\n", sig.c_str());
			const SignalInfo &si = rep.sigs.Sid2Info.at(sid);
			for (int val_channel = 0; val_channel < si.n_val_channels; ++val_channel)
				if (!si.is_categorical_per_val_channel[val_channel]) {
					res.push_back(sig); 
					val_channels.push_back(val_channel);
				}
		}
		MLOG("Has %zu numeric signals to test\n", res.size());
		return;
	}
	vector<string> tokens;
	boost::split(tokens, signal_name_arg, boost::is_any_of(",;"));
	if (tokens.size() > 1) {
		res = move(tokens);
		val_channels.resize(res.size());
	}
	else {
		ifstream fp(signal_name_arg);
		if (!fp.good()) {
			res = { signal_name_arg };
			val_channels.resize(res.size());
		}
		else {
			medial::io::read_codes_file(signal_name_arg, tokens);
			res = move(tokens);
			val_channels.resize(res.size());
		}
	}
}

void print_graph(const ProgramArgs &args) {
	if (args.output.empty())
		MTHROW_AND_ERR("Error - please provide output argument in this mode\n");
	string bp_path = args.base_path;
	boost::filesystem::path p(bp_path);
	random_device rd;

	boost::filesystem::create_directories(args.output);
	string f_log_file = args.output + path_sep() + "all_tests.log";
	ofstream fw(f_log_file);
	if (!fw.good())
		MTHROW_AND_ERR("Can't open file for logging %s\n", f_log_file.c_str());
	fw.close();

	vector<string> all_sigs;
	vector<int> val_channels;
	get_list(args.signal_name, all_sigs, val_channels, args.rep);
	MedRepository rep;
	vector<int> sids(all_sigs.size());
	if (bp_path.empty()) {
		vector<int> pids;
		if (rep.read_all(args.rep, pids, all_sigs) < 0)
			MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());
		for (size_t i = 0; i < sids.size(); ++i)
			sids[i] = rep.sigs.sid(all_sigs[i]);
	}
	int sig_id = 0;
	for (const string &signal_nm : all_sigs)
	{
		string clean_name = signal_nm;
		int chan = val_channels[sig_id];
		fix_filename_chars(&clean_name, '_');

		vector<string> fnames;
		regex match_nm(signal_nm);
		if (!bp_path.empty())
			for (auto& entry : boost::make_iterator_range(boost::filesystem::directory_iterator(p), {})) {
				string cand = entry.path().filename().generic_string();
				if (regex_match(cand, match_nm))
					fnames.push_back(entry.path().generic_string());
			}

		int THREADS_NUM = omp_get_max_threads();
		vector<mt19937> gens(THREADS_NUM);
		for (size_t i = 0; i < THREADS_NUM; ++i)
			gens[i] = mt19937(rd());

		vector<float> full_data;
		if (args.sample_each_file > 0)
			full_data.reserve(args.sample_each_file * fnames.size());

		if (!bp_path.empty()) {
			MedProgress progress("Input Reading", (int)fnames.size(), 30, 1);
#pragma omp parallel for if (args.use_threads)
			for (int i = 0; i < fnames.size(); ++i)
			{
				int n_th = omp_get_thread_num();
				const string fname = fnames[i];
				vector<float> data;
				read_sample_file(fname, args.has_header, args.sample_each_file, args.delimeter, args.column_num, gens[n_th], args.buffer_size,
					data);

#pragma omp critical
				full_data.insert(full_data.end(), data.begin(), data.end());

				progress.update();
			}
		}
		else {
			//use rep:
			MedProgress progress("Repository Reading", (int)rep.pids.size(), 30, 50);
			for (int i = 0; i < rep.pids.size(); ++i)
			{
				UniversalSigVec usv;
				rep.uget(rep.pids[i], sids[sig_id], usv);

#pragma omp critical
				for (int j = 0; j < usv.len; ++j)
					full_data.push_back(usv.Val(j, chan));

				progress.update();
			}
		}

		//test data:
		//1. test for problems
		test_problems(full_data, args.test_args, f_log_file, signal_nm);

		//plot graph:
		BinSettings bin_s;
		bin_s.init_from_string(args.binning);
		if (!args.binning.empty())
			medial::process::split_feature_to_bins(bin_s, full_data, {}, full_data);

		map<float, float> hist = BuildHist(full_data);
		string y_label = "Prob";
		if (args.normalize)
			NormalizeData(hist);
		else
			y_label = "Count";

		vector<map<float, float>> graphData = { hist };
		string signalName = args.signal_name;
		replace(signalName.begin(), signalName.end(), '#', 'H');
		replace(signalName.begin(), signalName.end(), '%', 'P');
		if (chan > 0) {
			clean_name += "_chan_" + to_string(chan);
			signalName += "_chan_" + to_string(chan);
		}

		createHtmlGraph(args.output + path_sep() + clean_name + ".html", graphData, signalName, args.signal_name, y_label, { "data" });
		//print also csv
		string fContent = createCsvFile(hist);
		ofstream fw(args.output + path_sep() + clean_name + ".csv");
		if (!fw.good())
			MTHROW_AND_ERR("can't write cvs\n");
		fw << fContent << endl;
		fw.close();

		++sig_id;
	}
}

bool test_categ_signal(MedRepository &rep, const string &sig, int channel) {
	int sid = rep.sigs.sid(sig);
	int section_id = rep.dict.section_id(sig);

	MedProgress progress("Test::" + sig + "_" + to_string(channel), (int)rep.pids.size(), 30, 50);

	volatile bool flag = false;
	int example_pid, example_time, example_val;
#pragma omp parallel for shared(flag)
	for (int i = 0; i < rep.pids.size(); ++i)
	{
		if (flag) { progress.skip_update(); continue; }
		int pid = rep.pids[i];
		UniversalSigVec usv;
		rep.uget(pid, sid, usv);

		for (int j = 0; j < usv.len; ++j)
		{
			int v = usv.Val<int>(j, channel);
			//check defined in dict
			bool exists = !rep.dict.name(section_id, v).empty();
			if (!exists) {
#pragma omp critical 
				{
					flag = true;
					example_pid = pid;
					example_time = usv.Time(j, 0);
					example_val = v;
				}
			}
		}
		progress.update();
	}

	if (flag)
		MERR("Error found undefined value for signal %s, channel %d. Value was %d, for pid %d in time %d\n",
			sig.c_str(), channel, example_val, example_pid, example_time);
	return !flag;
}

void test_categ(const ProgramArgs &args) {
	if (args.rep.empty())
		MTHROW_AND_ERR("Error must provide rep when running in mode test_categorical True\n");
	MedRepository rep;
	if (rep.init(args.rep) < 0)
		MTHROW_AND_ERR("Error can't read repository %s\n", args.rep.c_str());
	vector<string> sorted(rep.sigs.signals_names.begin(), rep.sigs.signals_names.end());
	sort(sorted.begin(), sorted.end());
	//test which is categorical and on each channel and run test:
	vector<pair<string, int>> signal_channel;
	unordered_set<string> signals_to_read;
	for (const string &sig : sorted)
	{
		int sid = rep.sigs.sid(sig);
		const SignalInfo &info = rep.sigs.Sid2Info[sid];
		int nvals = info.n_val_channels;
		for (int i = 0; i < nvals; ++i)
			if (info.is_categorical_per_val_channel[i]) {
				signal_channel.push_back(pair<string, int>(sig, i));
				signals_to_read.insert(sig);
			}
	}
	vector<string> uniq_sigs(signals_to_read.begin(), signals_to_read.end());
	vector<int> empt_pids;
	if (rep.read_all(args.rep, empt_pids, uniq_sigs) < 0)
		MTHROW_AND_ERR("Error can't read repository %s\n", args.rep.c_str());

	//run test
	MLOG("Has %zu test in %zu signals\n", signal_channel.size(), uniq_sigs.size());
	bool all_res = true;
	MedProgress progress("Test Categorical Signals", (int)signal_channel.size(), 30, 1);
	for (const pair<string, int> &tp : signal_channel) {
		bool res = test_categ_signal(rep, tp.first, tp.second);
		all_res = all_res && res;
		progress.update();
	}
	if (all_res)
		MLOG("All signals are OK\n");
	else
		MERR("Found some problems, look ahead\n");
}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	if (args.test_categorical) {
		test_categ(args);
		return 0;
	}

	if (args.signal_name.empty()) {
		print_options(args.base_path, args.rep);
		return 0;
	}

	print_graph(args);

	return 0;
}