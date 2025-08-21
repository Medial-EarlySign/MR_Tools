#include "utils.h"
#include <boost/algorithm/string.hpp>
#include <iostream>
#include <fstream>
#include <stdarg.h>

#ifndef GIT_HEAD_VERSION
#define GIT_HEAD_VERSION "not built using scripts - please define GIT_HEAD_VERSION in compilation or use smake_rel.sh"
#endif

using namespace std;

template<class ContainerType> string get_list(const ContainerType &ls, const string &delimeter) {
	string res = "";
	for (auto it = ls.begin(); it != ls.end(); ++it)
		if (it == ls.begin())
			res += *it;
		else
			res += delimeter + *it;
	return res;
}

string get_git_version() {
    return GIT_HEAD_VERSION;
}

string print_any(po::variable_value &a) {
	if (a.value().type() == typeid(string)) {
		return a.as<string>();
	}
	else if (a.value().type() == typeid(int)) {
		return to_string(a.as<int>());
	}
	else if (a.value().type() == typeid(unsigned short)) {
		return to_string(a.as<unsigned short>());
	}
	else if (a.value().type() == typeid(float)) {
		return to_string(a.as<float>());
	}
	else if (a.value().type() == typeid(double)) {
		return to_string(a.as<double>());
	}
	else if (a.value().type() == typeid(bool)) {
		return to_string(a.as<bool>());
	}

	return "";
}


void MLOG(bool throw_exp, const char *fmt, ...) {
    char buff[5000];
    va_list args;
    
    va_start(args, fmt);
	vsnprintf(buff, sizeof(buff), fmt, args);
	va_end(args);

    printf("%s", buff);
	fflush(stdout);
    if (throw_exp)
        throw std::runtime_error(buff);
}

void ProgramArgs_base::init(po::options_description &prg_options, const string &app_l) {
	po::options_description general_options("Program General Options",
		(unsigned int)po::options_description::m_default_line_length * 2);
	general_options.add_options()
		("help,h", "help & exit")
		("help_module", po::value<string>(), "help on specific module")
		("base_config", po::value<string>(&base_config), "config file with all arguments - in CMD we override those settings")
		("debug", po::bool_switch(&debug), "set debuging verbose")
		("version", "prints version information of the program")
		;
	desc.add(general_options);
	desc.add(prg_options);
	if (!app_l.empty())
		app_logo = app_l;
	debug = false;
	init_called = true;
}

//finds module section help in full help message
string ProgramArgs_base::get_section(const string &full_help, const string &search) {
	stringstream res;
	vector<string> lines;
	boost::split(lines, full_help, boost::is_any_of("\n"));
	bool in_section = false;
	for (size_t i = 0; i < lines.size(); ++i) {
		string ln = boost::trim_copy(lines[i]);
		if (!ln.empty() && ln.at(ln.length() - 1) == ':' && ln.substr(0, 2) != "--") {
			if (lines[i].find(search) != string::npos)
				in_section = true;
			else
				in_section = false;
		}
		if (in_section)
			res << lines[i] << "\n";
	}
	return res.str();
}

void ProgramArgs_base::list_sections(const string &full_help, vector<string> &all_sec) {
	vector<string> lines;
	boost::split(lines, full_help, boost::is_any_of("\n"));
	for (size_t i = 0; i < lines.size(); ++i) {
		boost::trim(lines[i]);
		if (!lines[i].empty() && lines[i].at(lines[i].length() - 1) == ':' && lines[i].substr(0, 2) != "--")
			all_sec.push_back(lines[i].substr(0, lines[i].length() - 1));
	}
}

int ProgramArgs_base::parse_parameters(int argc, char *argv[]) {
	if (!init_called)
		MLOG(true, "ProgramArgs_base::init function wasn't called\n");

	po::options_description desc_file(desc);
	po::variables_map vm_config;

	auto parsed_args = po::parse_command_line(argc, argv, desc,
		po::command_line_style::style_t::default_style);

	po::store(parsed_args, vm);
	if (vm.count("help_module")) {
		string help_search = vm["help_module"].as<string>();
		stringstream help_stream;
		help_stream << desc;
		string full_help = help_stream.str();
		string module_help = get_section(full_help, help_search);
		if (module_help.empty()) {
			vector<string> all_sections;
			list_sections(full_help, all_sections);
			string section_msg = get_list(all_sections, "\n");
			cout << "No help on search for module \"" << help_search << "\", Available Sections(" << all_sections.size() << "):\n" << section_msg << endl;
		}
		else
			cout << module_help << endl;

		return -1;
	}

	if (vm.count("help") || vm.count("h")) {
		MLOG(false, "%s\n", app_logo.c_str());
		cout << desc << endl;
		return -1;
	}

	if (vm.count("version")) {
		MLOG(false, "%s\n", app_logo.c_str());
		cout << "Version Info:\n" << get_git_version() << endl;
		return -1;
	}

	if (vm.count("base_config") > 0) {
		std::ifstream ifs(vm["base_config"].as<string>(), std::ifstream::in);
		if (!ifs.good())
			MLOG(true, "IO Error: can't read \"%s\"\n", vm["base_config"].as<string>().c_str());
		auto parsed = po::parse_config_file(ifs, desc_file, true);
		po::store(parsed, vm_config);
		ifs.close();
	}
	//iterate on all values and override defaults in desc:
	for (auto it = vm_config.begin(); it != vm_config.end(); ++it)
	{
		if (it->second.defaulted()) {
			continue;
		}
		if (vm.find(it->first) == vm.end() || vm[it->first].defaulted()) {
			//should not happended

			if (vm.find(it->first) == vm.end()) {
				vm.insert(pair<string, po::variable_value>(it->first, it->second));
			}
			vm.at(it->first) = it->second;

		}
	}

	po::notify(vm);

	post_process();

	if (debug) {
		string full_log_format = "$time\t$level\t$section\t%s";
		
		MLOG(false, "Version Info:\n%s\n", get_git_version().c_str());
		MLOG(false, "Debug Running With:\n");
		string full_params = string(argv[0]);
		char buffer[1000];
		for (auto it = vm.begin(); it != vm.end(); ++it) {
			MLOG(false, "%s = %s\n", it->first.c_str(),print_any(it->second).c_str());
			string val = print_any(it->second);
			//gets deafult value when defaulted
			//desc.find(it->first, true).semantic()
			if (it->second.value().type() == typeid(string))
				val = "\"" + val + "\"";
			snprintf(buffer, sizeof(buffer), " --%s %s", it->first.c_str(), val.c_str());
			full_params += string(buffer);
		}
		MLOG(false, "######################################\n\n%s\n", app_logo.c_str());
		MLOG(false, "######################################\n");
		MLOG(false, "Full Running Command:\n%s\n", full_params.c_str());
		MLOG(false, "######################################\n");
	}

	return 0;
}