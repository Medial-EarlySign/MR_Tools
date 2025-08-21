#ifndef __PROGRAM__ARGS__H__
#define __PROGRAM__ARGS__H__
#include "MedUtils/MedUtils/MedUtils.h"
#include "Logger/Logger/Logger.h"
#include <boost/algorithm/string.hpp>
#include <unordered_map>
#include <fstream>
#include <cctype>
#include <ctime>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;

enum CmdTypes {
	TakeColumn = 1,
	StaticString = 2,
	JoinFile = 3,
};

enum TreatMissings {
	EmptyField = 1,
	UnknownField = 2,
	KeepOriginal = 3
};

class ParseCmd {
public:
	string command;
	CmdTypes type;

	int column_index;
	vector<int> input_indexes;
	unordered_map<string, vector<string>> join_file_map;
	int max_input_indexes;
	int add_count;

	string file_name() {
		if (type == CmdTypes::JoinFile && command.find("#") != string::npos) {
			return command.substr(0, command.find_first_of("#"));
		}
		return "";
	}
};

bool is_number(const std::string& s)
{
	return !s.empty() && std::find_if(s.begin(),
		s.end(), [](char c) { return !std::isdigit(c); }) == s.end();
}

void parse_int_list(const string &token, vector<int> &res, const string &delim = "#") {
	vector<string> tokens;
	boost::split(tokens, token, boost::is_any_of(delim));
	res.resize(tokens.size());
	for (size_t i = 0; i < res.size(); ++i)
		res[i] = stoi(tokens[i]);
}

int max_vector(const vector<int> &v) {
	if (v.empty())
		MTHROW_AND_ERR("Empty\n");
	int m = v[0];
	for (size_t i = 1; i < v.size(); ++i)
		if (v[i] < m)
			m = v[i];
	return m;
}

unordered_map<string, int> treat_enum_map = {
	{"empty", EmptyField } ,
	{ "unknown", UnknownField },
	{ "original", KeepOriginal }
};

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	/// the config command to parse line. ";" for each command\n
	/// Command options: \n
	/// number - to take column number
	/// string - to print static string
	/// file:*# - starts with "file:" to intersect with file path till "#" than taking 2 list numbers with "#". each list is seperated by ",".
	/// it join columns value from second file
	string config_parse;
	string treat_missings;

	void convert_treat_enum() {
		if (treat_enum_map.find(treat_missings) == treat_enum_map.end())
			MTHROW_AND_ERR("Conversion Error for treat_missings value \"%s\""
				". options are:\n%s\n", treat_missings.c_str(),
				medial::io::get_list(treat_enum_map).c_str());
		missing_method = TreatMissings(treat_enum_map.at(treat_missings));
	}

	void post_process() {
		has_dict_param = false;
		//get command:
		if (config_parse.empty() && !has_header)
			MTHROW_AND_ERR("unable to parse new file without header and config_parse\n");
		convert_treat_enum();
		if (config_parse.empty())
		{
			//interactive mode:
			ifstream fr(input);
			string line;
			getline(fr, line);
			fr.close();
			vector<string> tokens;
			boost::split(tokens, line, boost::is_any_of(delimeter));
			MLOG("Header for input file \"%s\" is\n", input.c_str());
			for (size_t i = 0; i < tokens.size(); ++i)
				MLOG("%03d:\t%s\n", (int)i, tokens[i].c_str());
			MLOG("Please write config_prase command:\n");
			cin >> config_parse;
		}
		//process command
		vector<string> parsed;
		boost::split(parsed, config_parse, boost::is_any_of(";"));
		parsed_commands.resize(parsed.size());
		for (size_t i = 0; i < parsed.size(); ++i)
		{
			if (boost::starts_with(parsed[i], "file:")) {
				parsed_commands[i].type = JoinFile;
				parsed_commands[i].command = parsed[i].substr(5);

				vector<string> cmd_params;
				boost::split(cmd_params, parsed_commands[i].command, boost::is_any_of("#"));
				if (cmd_params.size() != 4)
					MTHROW_AND_ERR("JoinFile Command must has 4 tokens splited by \"#\"\nGot:%s\n",
						parsed_commands[i].command.c_str());
				string &file_name = cmd_params[0];
				vector<int> source_indexes, use_indexes;
				parse_int_list(cmd_params[1], source_indexes, ",");
				parse_int_list(cmd_params[2], parsed_commands[i].input_indexes, ","); //in input_file
				parse_int_list(cmd_params[3], use_indexes, ",");
				int max_index = max(max_vector(source_indexes), max_vector(use_indexes));

				time_t start = time(NULL);
				ifstream fr(file_name);
				string dict_line;
				int dict_line_num = 1;
				string string_buffer;
				string_buffer.reserve(5000);
				while (getline(fr, dict_line)) {
					boost::trim(dict_line);
					if (dict_line.empty()) {
						++dict_line_num;
						continue;
					}
					vector<string> dict_tokens;
					boost::split(dict_tokens, dict_line, boost::is_any_of(delimeter));
					if (max_index >= dict_tokens.size()) {
						if (dict_line_num == 1) {
							MWARN("Bad Format in dict_line %d which has %d tokens\n%s\n"
								"Requested Column %d\n", dict_line_num, (int)dict_tokens.size(),
								dict_line.c_str(), max_index);
							++dict_line_num;
							continue;
						}
						else {
							HMTHROW_AND_ERR("Bad Format in dict_line %d which has %d tokens\n%s\n"
								"Requested Column %d\n", dict_line_num, (int)dict_tokens.size(),
								dict_line.c_str(), max_index);
						}
					}
					string_buffer.clear();
					for (int col_index : source_indexes)
						string_buffer.append(dict_tokens[col_index]);
					string source_key = string(string_buffer);
					string_buffer.clear();
					for (int ind = 0; ind < use_indexes.size(); ++ind) {
						if (ind == (int)use_indexes.size() - 1) //last
							string_buffer.append(dict_tokens[use_indexes[ind]]);
						else {
							string_buffer.append(dict_tokens[use_indexes[ind]]);
							string_buffer.append(delimeter);
						}
					}
					string &target_key = string_buffer;
					parsed_commands[i].join_file_map[source_key].push_back(target_key);
					++dict_line_num;
				}
				fr.close();
				//check for warning duplicate matchings:
				int has_dupl = 0;
				for (auto it = parsed_commands[i].join_file_map.begin(); it !=
					parsed_commands[i].join_file_map.end(); ++it)
					if (it->second.size() > 1)
						++has_dupl;
				if (has_dupl > 0)
					MWARN("Warning: has %d keys that are duplicated\n", has_dupl);
				parsed_commands[i].max_input_indexes = max_vector(parsed_commands[i].input_indexes);
				parsed_commands[i].add_count = (int)use_indexes.size();
				int durration = (int)difftime(time(NULL), start);
				MLOG("Read %d keys for dictionary %s in %d seconds\n",
					(int)parsed_commands[i].join_file_map.size(), file_name.c_str(), durration);
				has_dict_param = true;
			}
			else if (is_number(parsed[i])) {
				parsed_commands[i].type = TakeColumn;
				parsed_commands[i].command = parsed[i];
				parsed_commands[i].column_index = stoi(parsed[i]);
			}
			else {
				parsed_commands[i].type = StaticString;
				parsed_commands[i].command = parsed[i];
			}
		}
	}

public:
	string input; ///< the location to read input file
	string output; ///< the location to write output file
	string delimeter; ///< the input file delimeter
	bool has_header; ///< True if the file has header
	int output_buffer; ///< the line number buffer for write
	TreatMissings missing_method; ///< how to treat missings in join

	vector<ParseCmd> parsed_commands;
	bool has_dict_param;

	ProgramArgs()
	{
		string treat_options = "the treatment options are:" + medial::io::get_list(treat_enum_map);
		po::options_description program_desc("Program Options");
		program_desc.add_options()
			("input", po::value<string>(&input)->required(), "the location to read input (\"-\" for stdin)")
			("output", po::value<string>(&output)->required(), "the location to write output file  (\"-\" for stdout)")
			("delimeter", po::value<string>(&delimeter)->default_value("\t"), "the input file delimeter")
			("has_header", po::value<bool>(&has_header)->default_value(true), "True if the file has header")
			("config_parse", po::value<string>(&config_parse)->default_value(""), "the config command to parse line")
			("output_buffer", po::value<int>(&output_buffer)->default_value(0), "the line number buffer for write. 0 means no buffer - write all")
			("treat_missings", po::value<string>(&treat_missings)->default_value("unknown"), treat_options.c_str())
			;

		init(program_desc);
	}

};
#endif
