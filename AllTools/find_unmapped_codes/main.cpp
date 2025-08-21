#include "Cmd_Args.h"
#include <InfraMed/InfraMed/InfraMed.h>
#include <boost/regex.hpp>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

bool is_target_regex(int code_id, int section_id, MedRepository &rep, boost::regex &regex_code) {
	const vector<string> &names = rep.dict.dicts[section_id].Id2Names.at(code_id);
	bool is_target = false;
	for (const string &nm : names)
		if (boost::regex_search(nm, regex_code)) {
			is_target = true;
			break;
		}
	return is_target;
}

int main(int argc, char * argv[]) {
	Program_Args args;
	int exit_code = args.parse_parameters(argc, argv);
	if (exit_code == -1)
		return 0;
	if (exit_code < 0)
		MTHROW_AND_ERR("unable to parse arguments\n");

	MedRepository rep;
	if (rep.init(args.rep) < 0)
		MTHROW_AND_ERR("Error unable to read repository %s\n", args.rep.c_str());
	int sid = rep.sigs.sid(args.sig);
	if (sid < 0)
		MTHROW_AND_ERR("Error unable to find signal %s\n", args.sig.c_str());
	int section_id = rep.dict.section_id(args.sig);
	boost::regex regex_code(args.regex_target);


	ofstream fw_out(args.output_path);
	if (!fw_out.good())
		MTHROW_AND_ERR("Error unable to open file %s for writing\n", args.output_path.c_str());
	//iterate over all codes from dict:
	for (const auto &it : rep.dict.dicts[section_id].Id2Names) {
		int code_id = it.first;
		const vector<string> &names = it.second;
		//see if we want to code or not by regex:
		bool is_target = is_target_regex(code_id, section_id, rep, regex_code);
		if (is_target)
			continue;
		//Not target - now, let's check if one of the parents is regex_code:
		vector<int> all_par = medial::signal_hierarchy::parents_code_hierarchy(rep.dict, names[0], args.sig, 1000, 100000);
		//Let's see if one of them is target_regex:
		bool has_target = false;
		for (int cd : all_par)
			if (is_target_regex(cd, section_id, rep, regex_code)) {
				has_target = true;
				break;
			}

		if (has_target)
			continue;
		//use has_target to detemine if mapped or not - no target. So not mapped!
		//find longest description from names as alias:
		string alias = names.front();
		string official_name = names.back();
		for (const string &nm : names)
			if (nm != official_name && nm.size() > alias.size())
				alias = nm;


		fw_out << code_id << "\t" << names.back() << "\t" << alias << "\n";
	}

	fw_out.close();
	MLOG("Done writing unmapped code to file %s\n", args.output_path.c_str());
	return 0;
}