#include <algorithm>
#include "Cmd_Args.h"
#include <InfraMed/InfraMed/InfraMed.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void read_pid_list(const string &pid_list, bool input_is_med_samples, unordered_map<int, vector<int>> &pid_to_times) {
	if (input_is_med_samples) {
		MedSamples smps;
		smps.read_from_file(pid_list);
		for (const MedIdSamples &s_id : smps.idSamples)
		{
			vector<int> &t = pid_to_times[s_id.id];
			t.reserve(s_id.samples.size());
			for (const MedSample &s : s_id.samples)
				t.push_back(s.time);
		}
		return;
	}
	ifstream fr(pid_list);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't read file %s\n", pid_list.c_str());
	string line;

	vector<string> tokens;
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty())
			continue;
		boost::split(tokens, line, boost::is_any_of(" \t,;"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("bad format in line:\n%s\n", line.c_str());

		int pid = med_stoi(tokens[0]);
		int time = med_stoi(tokens[1]);
		pid_to_times[pid].push_back(time);
	}

	fr.close();

	for (auto &it : pid_to_times)
		sort(it.second.begin(), it.second.end());
}

string print_signal(MedRepository &rep, int section_id, int sig_id, bool is_categ,
	int raw_val, int limit_count) {
	if (raw_val < 0)
		return "MISSING";

	stringstream buffer_str;
	buffer_str << raw_val;
	if (is_categ) {
		int printed_cnt = 0;
		if (rep.dict.dict(section_id)->Id2Names.find(raw_val) != rep.dict.dict(section_id)->Id2Names.end())
			for (int j = 0; j < rep.dict.dict(section_id)->Id2Names[raw_val].size()
				&& printed_cnt < limit_count; j++) {
				string st = rep.dict.dict(section_id)->Id2Names[raw_val][j];
				buffer_str << "|" << st;
				++printed_cnt;
			}

	}
	return buffer_str.str();
}

/**
* Searches for code list
*/
int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	vector<string> set;
	if (args.code_list_is_file)
		medial::io::read_codes_file(args.code_list, set);
	else
		boost::split(set, args.code_list, boost::is_any_of(",;"));
	unordered_map<int, vector<int>> pid_to_times;
	read_pid_list(args.pid_time_file, args.input_is_med_samples, pid_to_times);
	vector<int> pids;
	pids.reserve(pid_to_times.size());
	for (const auto &it : pid_to_times)
		pids.push_back(it.first);
	vector<string> sigs = { args.signal };

	ofstream fw;
	if (!args.output_file.empty()) {
		fw.open(args.output_file);
		if (!fw.good())
			MTHROW_AND_ERR("can't open %s for writing\n", args.output_file.c_str());
		fw << "pid" << "\t" << "req_time" << "\t" << "found_time" << "\t" << "value" << "\n";
	}

	MedRepository rep;
	if (rep.read_all(args.rep, pids, sigs) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", args.rep.c_str());
	int sig_id = rep.sigs.sid(args.signal);
	int section_id = rep.dict.section_id(args.signal);
	vector<char> lut;
	rep.dict.prep_sets_lookup_table(section_id, set, lut);
	bool is_categ = rep.sigs.is_categorical_channel(sig_id, args.val_channel);

	MedProgress progress("searching_codes", (int)rep.pids.size(), 15);
	map<int, map<int, vector<pair<int, int>>>> pid_to_time_to_foundtime_val;
#pragma omp parallel for
	for (int i = 0; i < rep.pids.size(); ++i)
	{
		UniversalSigVec usv;
		rep.uget(rep.pids[i], sig_id, usv);
		if (pid_to_times.find(rep.pids[i]) == pid_to_times.end())
			continue;
		const vector<int> &times = pid_to_times.at(rep.pids[i]);

		for (int tm : times) {
			//define time window:
			int start_tm = med_time_converter.convert_days(global_default_time_unit, med_time_converter.convert_times(global_default_time_unit, MedTime::Days, tm) - args.time_win_to);
			int end_tm = med_time_converter.convert_days(global_default_time_unit, med_time_converter.convert_times(global_default_time_unit, MedTime::Days, tm) - args.time_win_from);
			int j = 0;
			while (j < usv.len && usv.Time(j, args.time_channel) < start_tm)
				++j;
			bool added = false;
			while (j < usv.len && usv.Time(j, args.time_channel) <= end_tm) {
				int val = usv.Val(j, args.val_channel);
				int curr_tm = usv.Time(j, args.time_channel);
				if (lut[val] > 0) {
#pragma omp critical
					pid_to_time_to_foundtime_val[rep.pids[i]][tm].push_back(pair<int, int>(curr_tm, val));
					added = true;
				}
				++j;
			}
			if (!added)
#pragma omp critical
				pid_to_time_to_foundtime_val[rep.pids[i]][tm].push_back(pair<int, int>(-1, -1)); //mark as not added
		}
		progress.update();
	}

	for (const auto &it : pid_to_time_to_foundtime_val)
	{
		int pid = it.first;
		const map<int, vector<pair<int, int>>> &time_to_foundtime_val = it.second;
		for (const auto &jt : time_to_foundtime_val)
		{
			int req_time = jt.first;
			const vector<pair<int, int>> &time_val = jt.second;
			for (size_t i = 0; i < time_val.size(); ++i)
			{
				int time = time_val[i].first;
				int val = time_val[i].second;
				if (args.output_file.empty())
					MLOG("%d\t%d\t%d\t%s\n", pid, req_time, time,
						print_signal(rep, section_id, sig_id, is_categ, val, args.limit_count).c_str());
				else
					fw << pid << "\t" << req_time << "\t" << time << "\t"
					<< print_signal(rep, section_id, sig_id, is_categ, val, args.limit_count) << "\n";
			}
		}
	}

	if (!args.output_file.empty())
		fw.close();

	return 0;
}