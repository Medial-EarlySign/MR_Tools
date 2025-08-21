#include "Flow.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/MedPidRepository.h"
#include "MedFeat/MedFeat/MedOutcome.h"
#include <MedProcessTools/MedProcessTools/ExplainWrapper.h>

#include <vector>

#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
extern MedLogger global_logger;

using namespace std;

inline bool signal_type(const string &sig_name, MedRepository &rep) {
	return rep.sigs.has_any_categorical_channel(sig_name) && rep.dict.SectionName2Id.find(sig_name) != rep.dict.SectionName2Id.end();
	//return (sig_name == "Cancer_Location" || sig_name == "Drug" || sig_name == "RC" || sig_name.find("RC_") != string::npos);
}

//================================================================================================
// Repository Creation, Medical Records prints
//================================================================================================
int flow_pid_print_pid_sig(string &rep_fname, int pid, string &sig_name)
{
	MLOG("Flow: pid_print: pid %d sog %s rep %s\n", pid, sig_name.c_str(), rep_fname.c_str());

	MedPidRepository mpr;

	if (mpr.init(rep_fname) < 0) {
		MERR("Flow: pid_print: ERROR failed reading transposed repository.\n");
		return -1;
	}

	int sid = mpr.sigs.sid(sig_name);
	if (sid < 0) {
		MERR("Flow: pid_print: No such signal %s\n", sig_name.c_str());
		return -1;
	}

	int len;
	PidRec prec;
	prec.prealloc(MAX_PID_DATA_SIZE);
	mpr.get_pid_rec(pid, prec);

	void *data = prec.get(sid, len);
	if (len > 0)
		mpr.print_vec_dict(data, len, pid, sid);
	return 0;
}

//=============================================================================
int flow_print_pid_sig(string &rep_fname, int pid, string &sig_name)
{
	MLOG("Flow: print_pid_sig: pid %d sig %s rep %s\n", pid, sig_name.c_str(), rep_fname.c_str());
	MedRepository rep;

	vector<int> pids;
	pids.push_back(pid);

	vector<string> sigs;
	sigs.push_back(sig_name);

	if (rep.read_all(rep_fname, pids, sigs) < 0) {
		MERR("Flow: print_pid_sig: FAILED reading repository\n");
		return -1;
	}

	int sid = rep.sigs.sid(sig_name);
	if (sid < 0) {
		MERR("Flow: print_pid_sig: No such signal %s\n", sig_name.c_str());
		return -1;
	}

	rep.print_data_vec_dict(pid, sid);

	return 0;
}

int read_code_to_signal(const string &fname, map<string, string>& signal_to_code)
{
	ifstream inf(fname);
	if (!inf)
		MTHROW_AND_ERR("read_code_to_signal: Can't open file [%s]\n", fname.c_str());
	string curr_line;
	while (getline(inf, curr_line)) {
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {
			vector<string> fields;
			split(fields, curr_line, boost::is_any_of(" \t"));
			if (fields.size() >= 2) {
				signal_to_code[fields[1]] = fields[0];
			}
		}
	}
	MLOG("read_code_to_signal: read %d lines from [%s]\n", signal_to_code.size(), fname.c_str());
	inf.close();
	return 0;
}

//=====================================================================================================
string convert_val_to_string(MedPidRepository& mpr, int sid, int channel, float val) {
	string ret_val = to_string(val);
	if (mpr.sigs.is_categorical_channel(sid, channel)) {
		int section_id = mpr.dict.section_id(mpr.sigs.name(sid));
		if (mpr.dict.dict(section_id)->Id2Names.find(val) != mpr.dict.dict(section_id)->Id2Names.end()) {
			ret_val = mpr.dict.dict(section_id)->Id2Names[val][0];
		}
		else {
			MTHROW_AND_ERR("Could not find dictionary value for sid %d, val %f \n", sid, val);
		}
	}
	return ret_val;
}

int flow_pid_printall(MedPidRepository& mpr, int pid, const string& output_format = "text", const string& codes_to_signals_fname = "")
{
	MLOG("pid_printall for pid %d sig size %d\n", pid, mpr.index.signals.size());

	map<string, string> signal_to_code;
	if (output_format == "repo_load_format")
		read_code_to_signal(codes_to_signals_fname, signal_to_code);

	PidRec prec;
	prec.prealloc(MAX_PID_DATA_SIZE);
	mpr.get_pid_rec(pid, prec);
	if (output_format == "csv")
		MOUT("pid,sid,sname,stype,len,i,val,val2,date1,date2,val3,val4,desc1,desc2,extra1,extra2\n");
	int len;
	for (int s = 0; s <= 1; s++) {
		for (int i = 0; i < mpr.sigs.signals_ids.size(); i++) {
			int print_type = 0;
			int sid = mpr.sigs.signals_ids[i];
			string sname = mpr.sigs.name(sid);
			if (signal_type(sname, mpr))
				print_type = 1;

			if (print_type == s) {
				void *data = prec.get(mpr.sigs.signals_ids[i], len);

				if (len <= 0)
					continue;
				if (output_format == "csv")
					mpr.print_csv_vec(data, len, pid, mpr.sigs.signals_ids[i], (bool)(print_type != 0));
				else if (output_format == "repo_load_format") {
					string thin_sname = signal_to_code[sname];
					if (signal_to_code.find(sname) == signal_to_code.end() || thin_sname.length() == 0) {
						thin_sname = sname;
					}

					if (mpr.sigs.type(sid) == T_DateVal) {
						SDateVal *v = (SDateVal *)data;
						for (int j = 0; j < len; j++)
							printf("%d\t%s\t%d\t%s\n", pid, thin_sname.c_str(), v[j].date, convert_val_to_string(mpr, sid, 0, v[j].val).c_str());
					}
					if (mpr.sigs.type(sid) == T_DateRangeVal) {
						SDateRangeVal *v = (SDateRangeVal *)data;
						for (int j = 0; j < len; j++)
							printf("%d\t%s\t%d\t%d\t%s\n", pid, thin_sname.c_str(), v[j].date_start, v[j].date_end, convert_val_to_string(mpr, sid, 0, v[j].val).c_str());
					}
					if (mpr.sigs.type(sid) == T_Value) {
						SVal *v = (SVal*)data;
						for (int j = 0; j < len; j++)
							printf("%d\t%s\t%d\n", pid, thin_sname.c_str(), int(v[j].val));
					}
					if (mpr.sigs.type(sid) == T_ValShort4) {
						SValShort4 *v = (SValShort4*)data;
						for (int j = 0; j < len; j++)
							printf("%d\t%s\t%d\t%d\t%d\t%d\n", pid, thin_sname.c_str(), int(v[j].val1)
								, int(v[j].val2)
								, int(v[j].val3)
								, int(v[j].val4));
					}
					if (mpr.sigs.type(sid) == T_DateVal2) {
						SDateVal2 *v = (SDateVal2 *)data;
						for (int j = 0; j < len; j++)
							printf("%d\t%s\t%d\t%s\t%s\n", pid, thin_sname.c_str(), v[j].date, convert_val_to_string(mpr, sid, 0, v[j].val).c_str()
								, convert_val_to_string(mpr, sid, 1, v[j].val2).c_str());
					}
					if (mpr.sigs.type(sid) == T_DateShort2) {
						SDateShort2 *v = (SDateShort2 *)data;
						for (int j = 0; j < len; j++)
							printf("%d\t%s\t%d\t%s\t%s\n", pid, thin_sname.c_str(), v[j].date, convert_val_to_string(mpr, sid, 0, v[j].val1).c_str()
								, convert_val_to_string(mpr, sid, 1, v[j].val2).c_str());
					}
					if (mpr.sigs.type(sid) == T_Generic) {
						UniversalSigVec usv;
						prec.uget(mpr.sigs.signals_ids[i], usv);
						for (int j = 0; j < usv.len; ++j) {
							printf("%d\t%s", pid, thin_sname.c_str());
							for (int k = 0; k < usv.n_time_channels(); ++k)
								printf("\t%d", usv.Time(j, k));
							for (int k = 0; k < usv.n_val_channels(); ++k)
								printf("\t%s", convert_val_to_string(mpr, sid, k, usv.Val(j, k)).c_str());
							printf("\n");
						}
					}
				}
				else if (output_format == "text") {
					mpr.print_vec_dict(data, len, pid, mpr.sigs.signals_ids[i]);
				}
				else MTHROW_AND_ERR("unknown format [%s]", output_format.c_str());
			}
		}
	}
	return 0;
}
int flow_pid_printall(string &rep_fname, int pid, const string& output_format = "text", const string& codes_to_signals_fname = "") {
	MLOG("Flow: pid_printall: pid %d format [%s] rep [%s]\n", pid, output_format.c_str(), rep_fname.c_str());

	MedPidRepository mpr;

	if (mpr.init(rep_fname) < 0) {
		MERR("Flow: pid_printall: ERROR failed reading transposed repository.\n");
		return -1;
	}
	return flow_pid_printall(mpr, pid, output_format, codes_to_signals_fname);
}
int flow_pids_printall(string &rep_fname, const string& samples_file, const string &output_format, const string &codes_to_signals_fname) {
	MedSamples samples;
	if (samples.read_from_file(samples_file) < 0)
		return -1;

	MedPidRepository mpr;
	if (mpr.init(rep_fname) < 0) {
		MERR("Flow: pids_printall: ERROR failed reading transposed repository.\n");
		return -1;
	}

	for (auto patient : samples.idSamples)
		if (flow_pid_printall(mpr, patient.id, output_format, codes_to_signals_fname) < 0)
			return -1;

	return 0;
}


//=====================================================================================================
int flow_print_pids_with_sig(string &rep_fname, string &sig_name)
{
	MLOG("Flow: flow_print_pids_with_sig: rep %s sig %s\n", rep_fname.c_str(), sig_name.c_str());
	MedRepository rep;

	if (rep.read_all(rep_fname, {}, { sig_name }) < 0) {
		MERR("Flow: flow_print_pids_with_sig: ERROR: Failed reading repository\n");
		return -1;
	}

	int sid = rep.sigs.sid(sig_name);
	int len;
	for (auto pid : rep.pids) {
		if (rep.get(pid, sid, len) != NULL)
			MOUT("%d\n", pid);
	}

	return 0;
}

//=====================================================================================================
int flow_printall(string &rep_fname, int pid, string output_format, const vector<string>& ignore_signals)
{
	MLOG("Flow: printall: pid %d rep %s\n", pid, rep_fname.c_str());
	MedRepository rep;

	vector<int> pids;
	pids.push_back(pid);

	vector<string> sigs;

	if (rep.read_all(rep_fname, pids, sigs) < 0) {
		MERR("Flow: printall: ERROR: Failed reading repository\n");
		return -1;
	}
	MLOG("printall for pid %d sig size %d output_format [%s]\n", pid, rep.sigs.signals_ids.size(), output_format.c_str());
	int len;
	for (int j = 0; j <= 1; j++) {
		for (int i = 0; i < rep.sigs.signals_ids.size(); i++) {
			int sid = rep.sigs.signals_ids[i];
			string sname = rep.sigs.name(sid);
			if (find(ignore_signals.begin(), ignore_signals.end(), sname) != ignore_signals.end())
				continue;
			int print_type = 0;
			if (signal_type(sname, rep))
				print_type = 1;

			if (print_type == j) {
				rep.get(pid, sid, len);

				if (len <= 0)
					continue;
				if (output_format == "csv") {
					int len = 0;
					void *data = rep.get(pid, sid, len);
					rep.print_csv_vec(data, len, pid, sid, (bool)(print_type != 0));
				}
				else {
					rep.print_data_vec_dict(pid, sid);
				}
			}
		}
	}

	return 0;

}

//=====================================================================================================
int flow_rep_create_pids(string &rep_fname)
{
	MLOG("Flow: rep_create_pids: Attemping to create a transpose pid repository for rep %s ...\n", rep_fname.c_str());

	// first reading all_pids
	MedPidRepository mpr;

	if (mpr.read_config(rep_fname) < 0) return -1;
	if (mpr.read_pid_list() < 0) return -1;

	if (mpr.all_pids_list.size() == 0) {
		MERR("Flow: rep_create_pids: ERROR: got 0 pids in repository...., maybe pids list file was not created?...\n");
		return -1;
	}

	int jump = 1000000;
	int first = mpr.all_pids_list[0] - 1;
	int last = mpr.all_pids_list.back() + 1;
	if (((last - first) / 10) > jump)
		jump = (last - first) / 10;

	if (mpr.create(rep_fname, first, last, jump) < 0) {
		MERR("Flow: rep_create_pids: ERROR: Failed creating pid transpose rep.\n");
		return -1;
	}

	MLOG("Flow: rep_create_pids: Succeeded\n");
	return 0;
}

//=====================================================================================================
void flow_rep_create(string &conf_fname, const string &load_args, const string &err_log_path)
{
	std::ios::sync_with_stdio(false);
	std::ios_base::sync_with_stdio(false);


	MedConvert mc;
	mc.init_load_params(load_args);
	MLOG("Flow: rep_create: Attemping to create repository using convert config file %s ...\n", conf_fname.c_str());
	if (!err_log_path.empty())
		mc.full_error_file = err_log_path;

	if (mc.create_rep(conf_fname) < 0) {
		MTHROW_AND_ERR("Flow ERROR: Creating repository failed with convert config file %s.\n", conf_fname.c_str());
		return;
	}

	MLOG("Flow: rep_create: Succeeded\n");
}

//================================================================================================
// Creating Splits
//================================================================================================
struct FlowSplitParams {
	int nsplits;
	int gender_mask;
	int train_mask;
	int balance_flag;

	FlowSplitParams() { nsplits = 1; gender_mask = 3; train_mask = 7; balance_flag = 0; }

	void init_from_string(const string &in_params);
};
//================================================================================================
void FlowSplitParams::init_from_string(const string &in_params)
{
	vector<string> fields;
	split(fields, in_params, boost::is_any_of(",;:="));

	for (int i = 0; i < fields.size(); i++) {
		if (fields[i] == "gender") { i++; gender_mask = stoi(fields[i]); }
		if (fields[i] == "train") { i++; train_mask = stoi(fields[i]); }
		if (fields[i] == "nsplits") { i++; nsplits = stoi(fields[i]); }
		if (fields[i] == "balance") { balance_flag = 1; }
	}

}

//================================================================================================
int flow_create_split(string &split_fname, string &split_params, string &rep_fname)
{
	MLOG("flow: create_split: creating split file %s (params %s)\n", split_fname.c_str(), split_params.c_str());
	vector<int> pids_to_split;

	FlowSplitParams sp;
	sp.init_from_string(split_params);

	// first reading all_pids
	MedPidRepository mpr;
	vector<string> sigs = { "GENDER", "TRAIN" };
	vector<int> pids;
	if (mpr.read_all(rep_fname, pids, sigs) < 0) return -1;
	int t_sid = mpr.sigs.sid("TRAIN");
	int g_sid = mpr.sigs.sid("GENDER");

	MLOG("Reading %d,%d\n", t_sid, g_sid);
	int cnt = 0;
	for (int pid : mpr.all_pids_list) {
		int train = medial::repository::get_value(mpr, pid, t_sid);
		int gender = medial::repository::get_value(mpr, pid, g_sid);
		if (gender < 0 || train < 0) continue;

		if (cnt++ < 5)
			MLOG("%d Read pid [%d] train=%d gender=%d\n", cnt, pid, train, gender);
		if (((1 << (train - 1)) & sp.train_mask) && (gender & sp.gender_mask))
			pids_to_split.push_back(pid);

	}
	MLOG("Read %d pids\n", pids_to_split.size());

	if (!sp.balance_flag) {
		MedSplit spl;
		spl.create_random(pids_to_split, sp.nsplits);
		return (spl.write_to_file(split_fname));
	}

	// balance case
	MLOG("ERROR: balanced splits creation not supported yet\n");
	return -1;
}

//====================================================================
int flow_add_splits_to_samples(string &f_split, string &f_samples)
{
	MedSamples samples;

	if (samples.read_from_file(f_samples) < 0)
		MTHROW_AND_ERR("flow_add_splits_to_samples() failed reading samples file %s\n", f_samples.c_str());

	samples.add_splits_from_file(f_split);

	if (samples.write_to_file(f_samples) < 0)
		MTHROW_AND_ERR("flow_add_splits_to_samples() failes writing samples to %s\n", f_samples.c_str());

	return 0;
}

void flow_extract_pids_in_set(const string &rep_fname, const string& section,
	const string& sig_name, const string& sig_set, const string& sig_val, const string& out_file)
{
	MLOG("Flow: flow_extract_pids_in_set: rep [%s]\n", rep_fname.c_str());
	MedRepository rep;

	vector<int> pids;

	vector<string> sigs;
	split(sigs, sig_name, boost::is_any_of(","), boost::token_compress_on);

	if (rep.read_all(rep_fname, pids, sigs) < 0)
		MTHROW_AND_ERR("Flow: flow_extract_pids_in_set: ERROR: Failed reading repository");

	int section_id = rep.dict.section_id(section);
	MLOG("section [%s] = [%d]\n", section.c_str(), section_id);

	vector<char> lut;
	int sig_val_code = -1;
	if (sig_val.size() > 0) {
		sig_val_code = rep.dict.dict(section_id)->Name2Id[sig_val];
		if (sig_val_code <= 0) {
			MTHROW_AND_ERR("could not find definition for [%s]", sig_val.c_str());
		}
		else
			cerr << "looking for [" << sig_val << "] = [" << sig_val_code << "]\n";
	}
	else if (sig_set.size() > 0) {
		vector<string> sets;
		split(sets, sig_set, boost::is_any_of(","), boost::token_compress_on);

		rep.dict.prep_sets_lookup_table(section_id, sets, lut);
		int cnt = 0;
		for (auto& c : lut)
			if (c > 0)
				cnt++;
		MLOG("looking for sets [%s] with [%d/%d] items\n", sig_set.c_str(), cnt, lut.size());
		if (cnt <= 0)
			MTHROW_AND_ERR("sig_set must contain at least 1 item");
	}
	else
		MTHROW_AND_ERR("sig_val or sig_set must be set");

	struct o {
		o(int _pid, int _date, int _val) { pid = _pid; date = _date; val = _val; }
		int pid; int date; int val;
	};
	vector<o> result;

	UniversalSigVec usv;
	for (string s : sigs) {
		MLOG("scanning [%s]\n", s.c_str());
		for (int i = 0; i < rep.index.pids.size(); i++) {
			//int len;
			int pid = rep.index.pids[i];
			rep.uget(pid, s, usv);
			//SDateVal *sdv = (SDateVal *)rep.get(pid, s, len);
			if (i % 1000000 == 0)
				MLOG("%d: %d, %d\n", i, pid, usv.len);
			for (int j = 0; j < usv.len; j++) {
				int v = int(usv.Val(j));
				if ((sig_val_code <= 0 && v < lut.size() && lut[v]) || (v == sig_val_code)) {
					result.push_back(o(pid, usv.Date(j), v));
					break;
				}
			}
		}
	}
	cerr << "found [" << result.size() << "] patients, writing them to [" + out_file + "]\n";

	ofstream of;
	of.open(out_file, ios::out);
	if (!of)
		MTHROW_AND_ERR("can't open file: %s", out_file.c_str());
	of << "pid,date,val" << "\n";
	for (auto& r : result)
		of << r.pid << "," << r.date << "," << r.val << "\n";
	of.close();
}

void flow_clean_dict(const string &rep_fname, const string &input_dict, const string &output_dict) {
	if (rep_fname.empty())
		MTHROW_AND_ERR("Please provide repository path with rep param\n");

	MedPidRepository rep;
	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("Error can't read repository %s\n", rep_fname.c_str());
	ifstream fr(input_dict);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't open %s for reading\n", input_dict.c_str());
	//read input dict
	int max_examples = 10;
	vector<string> lines;
	string line;
	int section_id = 0;
	int skip_cnt = 0;
	vector<string> example_col;
	example_col.reserve(max_examples);
	while (getline(fr, line)) {
		boost::trim(line);
		if (!boost::algorithm::starts_with(line, "SET")) {
			lines.push_back(line);
			if (boost::algorithm::starts_with(line, "SECTION")) {
				vector<string> tokens;
				boost::split(tokens, line, boost::is_any_of("\t"));
				if (tokens.size() < 2)
					MTHROW_AND_ERR("format error in line:\n%s\n", line.c_str());
				string names = tokens[1];
				boost::split(tokens, names, boost::is_any_of(","));
				string sig_search = tokens[0];
				section_id = rep.dict.section_id(sig_search);
				MLOG("Found section %d for signal %s\n", section_id, sig_search.c_str());
			}
		}
		else {
			vector<string> tokens;
			boost::split(tokens, line, boost::is_any_of("\t"));
			if (tokens.size() < 2)
				MTHROW_AND_ERR("format error in line:\n%s\n", line.c_str());
			string set_name = tokens[1];
			boost::trim(set_name);
			int code_id = rep.dict.id(section_id, set_name);
			if (code_id >= 0)
				lines.push_back(line);
			else {
				++skip_cnt;
				if (example_col.size() < max_examples)
					example_col.push_back(set_name);
			}

		}
	}
	fr.close();
	if (skip_cnt == 0) {
		MLOG("All dict is OK. no conversion is needed\n");
		return;
	}

	MLOG("Has %d misses, examples:\n%s\n", skip_cnt,
		medial::io::get_list(example_col, "\n").c_str());

	ofstream fw(output_dict);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open %s for write\n", output_dict.c_str());
	//write clean file with lines:
	for (const string &line : lines) {
		fw << line << "\n";
	}

	fw.close();
}

void flow_get_features_groups(const string &grouping, const string &feature_name_list) {
	if (feature_name_list.empty())
		MTHROW_AND_ERR("Error select_features must be given in this mode\n");
	vector<string> features;
	if (boost::starts_with(feature_name_list, "file:"))
		medial::io::read_codes_file(feature_name_list.substr(5), features);
	else
		boost::split(features, feature_name_list, boost::is_any_of(","));
	if (grouping.empty())
		MTHROW_AND_ERR("Error group_signals must be given in this mode\n");
	vector<vector<int>> grp_idx;
	vector<string> group_names;
	ExplainProcessings::read_feature_grouping(grouping, features, grp_idx, group_names);
	//reverse from signal to group name:
	vector<string> resolve_grp_name(features.size());
	for (int group_id = 0; group_id < group_names.size(); ++group_id)
	{
		const string &curr_grp_name = group_names[group_id];
		for (int idx : grp_idx[group_id])
			resolve_grp_name[idx] = curr_grp_name;
	}

	MLOG("Feature to group mapping:\n");
	//print to screen:
	for (size_t i = 0; i < resolve_grp_name.size(); ++i)
		printf("%s => %s\n", features[i].c_str(), resolve_grp_name[i].c_str());
}

void flow_create_dict_for_am(const string &rep_fname, const string &sig,
	const string &dict_path, bool add_empty, bool skip_missings, const string &output_fname) {
	json js_writter, js_mappings;

	ifstream fr(dict_path);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't read file %s\n", dict_path.c_str());
	string line;
	unordered_set<string> all_vals;
	while (getline(fr, line))
	{
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 3 || tokens[0] != "DEF")
			continue;
		string val = tokens[2];
		all_vals.insert(val);
	}
	fr.close();

	MedRepository rep;
	if (rep.init(rep_fname) < 0)
		MTHROW_AND_ERR("Error can't read rep %s\n", rep_fname.c_str());
	int section_id = rep.dict.section_id(sig);
	const MedDictionary *dict = rep.dict.dict(section_id);
	//Add mappings for each value:
	unordered_map<string, unordered_set<string>> final_mapping; //from son to set holder
	int miss_cnt = 0;
	for (const string &target_set : all_vals)
	{
		int id = dict->id(target_set);
		if (id < 0) {
			if (skip_missings) {
				++miss_cnt;
				continue;
			}
			MTHROW_AND_ERR("Error cant find %s\n", target_set.c_str());
		}
		vector<int> sons;
		sons = medial::signal_hierarchy::sons_code_hierarchy(rep.dict, target_set, sig);
		for (int code : sons)
		{
			for (const string &nm : dict->Id2Names.at(code))
				if (all_vals.find(nm) == all_vals.end()) {
					unordered_set<string> &arr = final_mapping[nm];
					//add parent:
					arr.insert(target_set);
				}
		}
	}

	int add_empty_cnt = 0;
	if (add_empty) {
		for (const auto &it : dict->Id2Name)
		{
			int code_id = it.first;
			//exclude names that exists in all_vals:
			const vector<string> &all_names = dict->Id2Names.at(code_id);
			bool skip = false;
			for (size_t i = 0; i < all_names.size() && !skip; ++i)
				//skip if taken care of as ascender, or already a defined set.
				skip = all_vals.find(all_names[i]) != all_vals.end() ||
				final_mapping.find(all_names[i]) != final_mapping.end();
			if (skip)
				continue;

			// add empty
			++add_empty_cnt;
			for (const string &nm : all_names)
				final_mapping[nm].clear();
		}
	}

	//write to Json final_mapping:
	for (const auto &it : final_mapping)
	{
		vector<string> all_childs(it.second.begin(), it.second.end());
		js_mappings[it.first] = all_childs;
	}

	MLOG("Had %d codes in dict that aren't in rep and added %d codes that are not in the given dict\n",
		miss_cnt, add_empty_cnt);

	//js_writter
	js_writter[sig] = js_mappings;
	string full_text = js_writter.dump(2, ' ', true, json::error_handler_t::replace);
	write_string(output_fname, full_text);
	MLOG("Done writing to %s\n", output_fname.c_str());
}