#include <json/json.hpp>
#include <MedProcessTools/MedProcessTools/StripComments.h>
#include "Cmd_Args.h"
#include <cctype>
#include <boost/filesystem.hpp>
#include <MedIO/MedIO/MedIO.h>

void store_comments_position(const string &str, map<int, string> &comments_pos) {
	int pos = 0;

	char currentChar, nextChar;
	bool insideString = false;
	int commentType = 0; //;no commnet, 1 - single, 2- double
	stringstream current_token;
	for (int i = 0; i < str.length(); ++i) {
		currentChar = str[i];
		if (i < str.length() - 1)
			nextChar = str[i + 1];
		else
			nextChar = '\0';


		// If we're not in a comment, check for a quote.
		if (commentType == 0 && currentChar == '"') { //start double
			bool escaped = false;
			// If the previous character was a single slash, and the one before
			// that was not (i.e. the previous character is escaping this quote
			// and is not itself escaped), then the quote is escaped.
			if (i >= 2 && str[i - 1] == '\\' && str[i - 2] != '\\')
				escaped = true;
			if (!escaped)
				insideString = !insideString;
		}

		if (insideString) {
			++pos;
			continue;
		}

		//skip spaces if not in string. Can also be in comment
		if (commentType == 0 && isspace(str[i]))
			continue; //skip spaces
		//not inside string (and not comment)
		if (commentType == 0 && currentChar == '/' && nextChar == '/') {
			commentType = 1;

			// Skip second '/'
			++i;
			current_token << "//";
			continue;
		}
		else if (commentType == 1 && currentChar == '\n') {
			commentType = 0;
			current_token << "\n";
			if (comments_pos.find(pos) == comments_pos.end())
				comments_pos[pos] = "";
			else
				comments_pos[pos] = comments_pos[pos] + "\n";
			comments_pos[pos] = comments_pos[pos] + current_token.str();
			current_token.str("");
			//no advance in pos - stop comment
			continue;
		}
		else if (commentType == 0 && currentChar == '/' && nextChar == '*') {
			commentType = 2;

			// Skip the '*'
			i++;
			current_token << "/*";
			continue;
		}
		else if (commentType == 2 && currentChar == '*' && nextChar == '/') {
			commentType = 0;

			current_token << "*/";
			if (comments_pos.find(pos) == comments_pos.end())
				comments_pos[pos] = "";
			else
				comments_pos[pos] = comments_pos[pos] + "\n";
			comments_pos[pos] = comments_pos[pos] + current_token.str();
			current_token.str("");
			// Skip '*'
			i++;
			continue;
		}

		if (commentType > 0)
			current_token << currentChar;
		else //no inside comment:
			++pos;
	}
}

void restore_comments(string &str, const map<int, string>  &comments_pos) {
	//no comments in str:

	int pos = 0;
	bool insideString = false;
	auto comments_iter = comments_pos.begin();
	stringstream s, last_indent;
	for (int i = 0; i < str.length(); ++i) {

		// If we're not in a comment, check for a quote.
		if (str[i] == '"')  //start/end double 
			insideString = !insideString;

		if (insideString) {
			if (comments_iter != comments_pos.end()) {
				int c_pos = comments_iter->first;
				if (pos == c_pos) {
					string comment = comments_iter->second;
					s << comment << last_indent.str();
					++comments_iter;
				}
			}
			++pos;
			s << str[i];
			continue;
		}

		//skip spaces if not in string. Can also be in comment
		if (isspace(str[i])) {
			s << str[i];
			last_indent << str[i];
			if (str[i] == '\n')
				last_indent.str(""); //clear buffer
			continue; //skip spaces
		}

		//check if need to insert comment
		if (comments_iter != comments_pos.end()) {
			int c_pos = comments_iter->first;
			if (pos == c_pos) {
				string comment = comments_iter->second;
				s << comment << last_indent.str();
				++comments_iter;
			}
		}

		

		s << str[i];
		++pos;
	}

	//if last is comment:
	if (comments_iter != comments_pos.end()) {
		int c_pos = comments_iter->first;
		if (pos == c_pos) {
			string comment = comments_iter->second;
			s << comment << last_indent.str();
			++comments_iter;
		}
	}

	str = s.str();
}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	//parse json without comments:
	ifstream inf(args.input);
	if (!inf)
		MTHROW_AND_ERR("can't open json file [%s] for read\n", args.input.c_str());
	stringstream sstr;
	sstr << inf.rdbuf();
	inf.close();
	//mark comments positions
	map<int, string> comments_loc;
	MLOG("Read %s\n", args.input.c_str());
	store_comments_position(sstr.str(), comments_loc);
	MLOG("strip comments\n");
	//remove comments
	string orig = stripComments(sstr.str());

	nlohmann::ordered_json parsed_json = nlohmann::ordered_json::parse(orig);

	//dump to text:
	string res = parsed_json.dump(1, '\t');

	//add comment
	MLOG("Adding comments back\n");
	restore_comments(res, comments_loc);

	//save
	string output_path = args.output;
	if (output_path.empty()) {
		string pdir = boost::filesystem::path(args.input.c_str()).parent_path().string();
		string file_name = boost::filesystem::path(args.input.c_str()).filename().string();
		file_name = file_name.substr(0, file_name.rfind('.'))+".pretify.json";
		output_path = pdir + path_sep() + file_name;
	}
	MLOG("Saving file in %s\n", output_path.c_str());
	ofstream fw(output_path);
	if (!fw)
		MTHROW_AND_ERR("can't open json file [%s] for write\n", output_path.c_str());
	fw << res << endl;
	fw.close();

	return 0;
}