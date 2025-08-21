#include "Cmd_Args.h"
#include <algorithm>
#include <boost/algorithm/string.hpp>
#include <fstream>
#include <string>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

class data_f {
public:
	int start;
	int end;
};

void read_file(const string &f, const string &delimter, bool has_header, unordered_map<int, vector<data_f>> &recs) {
	ifstream fr(f);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't read file %s\n", f.c_str());
	MLOG("Read input %s\n", f.c_str());
	string line;
	if (has_header)
		getline(fr, line);

	while (getline(fr, line)) {
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of(delimter));
		if (tokens.size() < 3)
			MTHROW_AND_ERR("Error - bad file format %s:\n%s\n", f.c_str(), line.c_str());
		data_f r;
		int pid = stoi(tokens[0]);
		r.start = stoi(boost::replace_all_copy( tokens[1], "-", ""));
		r.end = stoi(boost::replace_all_copy(tokens[2], "-", ""));
		recs[pid].push_back(move(r));
	}
	fr.close();
}

void write_file(const string &f, const string &delimter, const unordered_map<int, vector<data_f>> &recs) {
	ofstream fw(f);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't write file %s\n", f.c_str());
	for (const auto &it : recs) {
		for (const data_f & dt : it.second)
			fw << it.first << delimter << dt.start << delimter << dt.end << "\n";
	}
	fw.close();
	MLOG("Wrote %s\n", f.c_str());
}

void merge(vector<data_f> &f, const data_f &curr) {
	if (curr.start >= curr.end)
		return;
	//Search intersection in last f (sorted by start):
	if (!f.empty() && curr.start <= f.back().end) {
		if (curr.end > f.back().end)
			f.back().end = curr.end;
	}
	else //f is empty (first) or no intersection - add and start new section
		f.push_back(curr);
}

void flat_periods(vector<data_f> &r) {
	sort(r.begin(), r.end(), [](const data_f &a, const data_f &b) { return a.start < b.start; });

	vector<data_f> f;
	for (int i = 0; i < r.size(); ++i)
	{
		data_f &curr = r[i];
		merge(f, curr);
	}
	r = move(f);
}

void get_merge(const vector<unordered_map<int, vector<data_f>>> &files_rec, const vector<int> &snap_dates,
	unordered_map<int, vector<data_f>> &final_merge, int hole_backward_th, int hole_forward_th) {
	//get list of all pids - iterate pid, pid:
	unordered_set<int> pid_list;
	for (const unordered_map<int, vector<data_f>> &f : files_rec)
		for (const auto &it : f)
			pid_list.insert(it.first);

	//Iterate over pids:
	for (int pid : pid_list)
	{
		int updated_till = 0;
		vector<data_f> &final_pid_rec = final_merge[pid]; //< the object that will be updated

		for (int i = 0; i < files_rec.size(); ++i) {
			const unordered_map<int, vector<data_f>> &curr_f = files_rec[i];
			if (curr_f.find(pid) == curr_f.end())
				continue;
			int max_date = snap_dates[i];
			vector<data_f> pid_recs = curr_f.at(pid);
			flat_periods(pid_recs);
			//Union pid_recs if needed:
			for (int j = 0; j < pid_recs.size(); ++j)
			{
				data_f curr = pid_recs[j];
				if (curr.end < updated_till)
					continue; //skip - period has update on already stored dates (less accurate and ignore)
				//Merge final_pid_rec with curr
				if (final_pid_rec.empty()) {
					//Trim dates:
					if (updated_till > 0 && curr.start < updated_till)
						curr.start = updated_till; //MAYBE add negative buffer? or variable to cancel this?
					if (curr.end > max_date)
						curr.end = max_date;

					final_pid_rec.push_back(curr);
					continue;
				}
				//final_pid_rec is not empty - not trivial:
				if (curr.start <= updated_till && curr.start <= final_pid_rec.back().end) {
					int hole_size = med_time_converter.diff_times(final_pid_rec.back().end, updated_till,
						MedTime::Date, MedTime::Days);
					if (hole_size <= hole_backward_th) {
						curr.start = final_pid_rec.back().end;
						if (curr.end > max_date)
							curr.end = max_date;
						merge(final_pid_rec, curr);
					}
					else {
						curr.start = updated_till; //MAYBE add negative buffer? or variable to cancel this?
						if (curr.end > max_date)
							curr.end = max_date;
						merge(final_pid_rec, curr);
					}

					continue;
				}
				if (final_pid_rec.back().end >= updated_till && curr.start > updated_till) {
					int hole_size = med_time_converter.diff_times(curr.start, updated_till,
						MedTime::Date, MedTime::Days);
					if (hole_size <= hole_forward_th) {
						curr.start = updated_till;
						if (curr.end > max_date)
							curr.end = max_date;
						merge(final_pid_rec, curr);
					}
					else {
						if (curr.end > max_date)
							curr.end = max_date;
						merge(final_pid_rec, curr);
					}

					continue;
				}

				if (updated_till > 0 && curr.start < updated_till)
					curr.start = updated_till; //MAYBE add negative buffer? or variable to cancel this?
				if (curr.end > max_date)
					curr.end = max_date;
				merge(final_pid_rec, curr);
			}

			updated_till = max_date;
		}
	}

}

int main(int argc, char *argv[])
{
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;
	vector<unordered_map<int, vector<data_f>>> files_rec(args.input.size());
	for (size_t i = 0; i < files_rec.size(); ++i)
		read_file(args.input[i], args.delimeter, args.has_header, files_rec[i]);
	//files were read and sorted!
	unordered_map<int, vector<data_f>> final_merge;

	get_merge(files_rec, args.date_app, final_merge, args.close_buffer_backward, args.close_buffer_foreward);

	write_file(args.output, args.delimeter, final_merge);
	return 0;
}