#include "Flow.h"
#include "Logger/Logger/Logger.h"
#include <boost/algorithm/string.hpp>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL


int flow_print_operations(FlowAppParams &ap)
{
	if (ap.options[OPTION_PRINTALL]) {
		if (flow_printall(ap.rep_fname, ap.pid, ap.outputFormat, ap.ignore_signals) < 0) {
			MERR("Flow: printall: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_PID_PRINTALL]) {
		if (flow_pid_printall(ap.rep_fname, ap.pid, ap.outputFormat, ap.codes_to_signals_fname) < 0) {
			MERR("Flow: pid_printall: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_PRINT]) {
		if (flow_print_pid_sig(ap.rep_fname, ap.pid, ap.sig_name) < 0) {
			MERR("Flow: print: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_PID_PRINT]) {
		if (flow_print_pid_sig(ap.rep_fname, ap.pid, ap.sig_name) < 0) {
			MERR("Flow: print: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_PRINT_PIDS]) {
		if (flow_print_pids_with_sig(ap.rep_fname, ap.sig_name) < 0) {
			MERR("Flow: print_pids_with_sig: FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_SIG_PRINT]) {
		if (flow_output_sig(ap.rep_fname, ap.sig_name, ap.outputFormat, ap.age_min, ap.age_max, ap.gender, ap.maxPids, ap.sampleCnt,
			ap.normalize > 0, ap.filterCnt, ap.bin_method, ap.output_fname) < 0) {
			MERR("Flow: csv : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_SIG_PRINT_RAW]) {
		if (ap.vm["time"].defaulted() && global_default_windows_time_unit == MedTime::Minutes) {
			//it's ICU:
			ap.time = INT_MAX;
		}
		if (ap.vm["f_samples"].defaulted())
			ap.f_samples = "";
		if (flow_output_pids_sigs_print_raw(ap.rep_fname, ap.pids, ap.sigs, ap.limit_count, ap.model_rep_processors, ap.time, ap.f_samples) < 0) {
			MERR("Flow: pids_sigs_print_raw : FAILED\n");
			return -1;
		}
	}

	if (ap.options[OPTION_REP_PROCESSOR_PRINT]) {

		vector<string> tokens;
		if (!ap.pids.empty())
			boost::split(tokens, ap.pids, boost::is_any_of(","));
		vector<int> pids_int(tokens.size());
		for (size_t i = 0; i < tokens.size(); ++i)
			pids_int[i] = med_stoi(tokens[i]);
		if (ap.sigs.empty())
			MTHROW_AND_ERR("sigs in rep_processor_print must not be empty\n");
		vector<string> sigs_parsed;
		if (file_exists(ap.sigs)) {
			MLOG("Sigs is file - openning %s\n", ap.sigs.c_str());
			medial::io::read_codes_file(ap.sigs, sigs_parsed);
		}
		else
			boost::split(sigs_parsed, ap.sigs, boost::is_any_of(","));

		test_rep_processors(ap.rep_fname, ap.cleaner_path_before, ap.cleaner_path, sigs_parsed, ap.output_fname,
			ap.random_seed, ap.max_examples, pids_int, ap.show_all_changes);

	}

	if (ap.options[OPTION_SHOW_CATEGORY_INFO]) {
		string rep = ap.vm["rep"].defaulted() ? "" : ap.rep_fname;
		show_category_info(rep, ap.sig_name, ap.sig_val);
	}

	if (ap.options[OPTION_FLAT_CATEGORY_VALS]) {
		string rep = ap.vm["rep"].defaulted() ? "" : ap.rep_fname;
		flat_list(rep, ap.sig_name, ap.sig_val, 0, ap.shrink_code_list, true);
	}

	if (ap.options[OPTION_GET_FEAT_GROUP]) {
		flow_get_features_groups(ap.group_signals, ap.select_features);
	}

	if (ap.options[OPTION_SHOW_NAMES]) {
		string rep = ap.vm["rep"].defaulted() ? "" : ap.rep_fname;
		string sig = ap.sig_name;
		string sig_val = ap.sig_val;
		if (rep.empty())
			MTHROW_AND_ERR("Error - must provide rep\n");
		if (sig_val.empty())
			MTHROW_AND_ERR("Error - must provide sig_val\n");
		vector<string> input_vals, sig_vals;
		if (boost::starts_with(sig_val, "file:")) {
			ifstream fr(sig_val.substr(5));
			if (!fr.good())
				MTHROW_AND_ERR("Error - can't read file %s\n", sig_val.substr(5).c_str());
			string line;
			vector<string> tokens;
			while (getline(fr, line)) {
				boost::trim(line);
				if (line.empty())
					continue;
				if (line.at(0) == '#')
					continue;
				boost::split(tokens, line, boost::is_any_of("\t"));
				if (tokens.size() == 1) {
					sig_vals.push_back(sig);
					input_vals.push_back(line);
				}
				else if (tokens.size() == 2) {
					sig_vals.push_back(tokens[0]);
					input_vals.push_back(tokens[1]);
				}
				else {
					fr.close();
					MTHROW_AND_ERR("Error - bad file format (%s) line:\n%s\n",
						sig_val.substr(5).c_str(), line.c_str());
				}
			}
			fr.close();
		}
		else {
			sig_vals.push_back(sig);
			input_vals.push_back(sig_val);
		}

		MedPidRepository repository;
		repository.read_config(rep);
		repository.read_dictionary();

		for (size_t i = 0; i < input_vals.size(); ++i)
		{
			fprintf(stdout, "%s\t%s\t", sig_vals[i].c_str(), input_vals[i].c_str());
			int section_id = repository.dict.section_id(sig_vals[i]);
			int sig_val_id = repository.dict.id(section_id, input_vals[i]);
			if (sig_val_id < 0) {
				//Search substr:
				vector<int>ids;
				for (auto &e : repository.dict.dict(section_id)->Id2Names) {
					for (const string &v : e.second) {
						if (v.find(input_vals[i]) != string::npos) {
							ids.push_back(e.first);
							break;
						}
					}
				}
				if (ids.size() == 1) {
					MWARN("WARN:: found as substring %s\n", input_vals[i].c_str());
					sig_val_id = ids[0];
				}
				else {
					MWARN("WARN:: not found %s\n", input_vals[i].c_str());
					fprintf(stdout, "\n");
					continue;
				}
			}
			const vector<string> &names = repository.dict.dicts[section_id].Id2Names.at(sig_val_id);

			if (!names.empty())
				fprintf(stdout, "%s", names.front().c_str());
			for (size_t i = 1; i < names.size(); ++i)
				fprintf(stdout, "|%s", names[i].c_str());
			fprintf(stdout, "\n");
		}

	}

	return 0;
}