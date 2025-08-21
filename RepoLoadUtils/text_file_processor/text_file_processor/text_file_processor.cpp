#include "Cmd_Args.h"
#include <unordered_set>
#include <ctime>

int main(int argc, char *argv[])
{
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	time_t start = time(NULL);
	ostream *output_stream = &std::cout;
	ofstream fw;
	if (args.output != "-") {
		fw.open(args.output);
		output_stream = &fw;
	}
	if (!fw.good())
		MTHROW_AND_ERR("IOError: can't write output \"%s\"\n", args.output.c_str());
	istream *input_stream = &std::cin;
	ifstream fr;
	if (args.input != "-") {
		fr.open(args.input);
		input_stream = &fr;
	}

	string line;
	int line_num = 1;
	if (args.has_header) {
		getline(*input_stream, line);// skip header
		++line_num;
	}

	string string_buffer;
	string_buffer.reserve(5000);
	vector<string> curr_line_buffers;
	vector<int> print_warn(args.parsed_commands.size(), 0);
	vector<unordered_set<string>>not_found_keys(args.parsed_commands.size());
	string unknown_token = "unknown";
	MedProgress progress("text_file_processor", 1, 15, 50);
	while (getline(*input_stream, line)) {
		boost::trim(line);
		if (line.empty()) {
			++line_num;
			continue;
		}
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of(args.delimeter));
		//process each column
		if (args.has_dict_param) {
			curr_line_buffers.resize(1, "");
			curr_line_buffers[0].clear();
		}
		string search_key;
		int prev_size = 0;
		for (size_t i = 0; i < args.parsed_commands.size(); ++i)
		{
			ParseCmd &cmd = args.parsed_commands[i];
			switch (cmd.type)
			{
			case CmdTypes::StaticString:
				if (args.has_dict_param)
					for (string &curr_line_buffer : curr_line_buffers)
						curr_line_buffer.append(cmd.command);
				else
					*output_stream << cmd.command;
				break;
			case CmdTypes::TakeColumn:
				if (cmd.column_index >= tokens.size())
					MTHROW_AND_ERR("Bad Format in line %d which has %d tokens:\n%s\n"
						"searched for column %d\n", line_num, (int)tokens.size(),
						line.c_str(), cmd.column_index);
				if (args.has_dict_param)
					for (string &curr_line_buffer : curr_line_buffers)
						curr_line_buffer.append(tokens[cmd.column_index]);
				else
					*output_stream << tokens[cmd.column_index];
				break;
			case CmdTypes::JoinFile:
				//Join dictionary file:
				if (cmd.max_input_indexes >= tokens.size())
					MTHROW_AND_ERR("Bad Format in line %d which has %d tokens:\n%s\n"
						"searched for column %d\n", line_num, (int)tokens.size(),
						line.c_str(), cmd.max_input_indexes);
				string_buffer.clear();
				for (int index : cmd.input_indexes)
					string_buffer.append(tokens[index]);
				if (cmd.join_file_map.find(string_buffer) == cmd.join_file_map.end()) {
					not_found_keys[i].insert(string_buffer);
					++print_warn[i];
					for (string &curr_line_buffer : curr_line_buffers)
						for (size_t k = 0; k < cmd.add_count; ++k)
							if (args.missing_method == EmptyField)
								curr_line_buffer.append(args.delimeter);
							else if (args.missing_method == UnknownField)
								curr_line_buffer.append(unknown_token);
							else
								curr_line_buffer.append(string_buffer);
				}
				else
				{
					prev_size = (int)curr_line_buffers.size();
					curr_line_buffers.resize(prev_size * cmd.join_file_map.at(string_buffer).size());
					for (size_t k = prev_size; k < curr_line_buffers.size(); ++k)
						curr_line_buffers[k] = string(curr_line_buffers[k % prev_size]);
					for (size_t k = 0; k < curr_line_buffers.size(); ++k)
						curr_line_buffers[k].append(cmd.join_file_map.at(string_buffer)[int(k % cmd.join_file_map.at(string_buffer).size())]);
				}
				break;
			default:
				MTHROW_AND_ERR("Unsupported command %d\n%s\n",
					int(cmd.type), cmd.command.c_str());
			}
			//not last add delimeter
			if (!args.has_dict_param)
				if (int(i) != (int)args.parsed_commands.size() - 1)
					*output_stream << args.delimeter;
				else {
					*output_stream << "\n";
					if (args.output_buffer > 0 && line_num % args.output_buffer == 0)
						output_stream->flush();
				}
			else {
				if (int(i) != (int)args.parsed_commands.size() - 1)
					for (string &curr_line_buffer : curr_line_buffers)
						curr_line_buffer.append(args.delimeter);
				else {
					for (string &curr_line_buffer : curr_line_buffers)
						*output_stream << curr_line_buffer << "\n";
					if (args.output_buffer > 0 && line_num % args.output_buffer == 0)
						output_stream->flush();
				}
			}
		}
		++line_num;
		progress.max_loop = line_num - int(args.has_header);
		progress.update();
	}
	output_stream->flush();
	progress.update();
	if (args.output != "-")
		fw.close();
	if (args.input != "-")
		fr.close();
	for (size_t i = 0; i < print_warn.size(); ++i)
		if (!not_found_keys[i].empty())
			MWARN("Warning: has %d not found keys within %d rows in %s\n\tExample:\"%s\"\n",
				(int)not_found_keys[i].size(), print_warn[i], args.parsed_commands[i].file_name().c_str(),
				not_found_keys[i].begin()->c_str());


	int durr = (int)difftime(time(NULL), start);
	MLOG("Done Processing %d lines in %d seconds\n",
		line_num, durr);

	return 0;
}

