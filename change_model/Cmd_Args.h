#ifndef __PROGRAM__ARGS__H__
#define __PROGRAM__ARGS__H__
#include "MedUtils/MedUtils/MedUtils.h"
#include "Logger/Logger/Logger.h"
#include <SerializableObject/SerializableObject/SerializableObject.h>
#include <boost/algorithm/string.hpp>
#include <unordered_map>
#include <fstream>
#include <cctype>
#include <ctime>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

namespace po = boost::program_options;
using namespace std;

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	void post_process() {
	}

public:
	string model_path; ///< the medmodel path
	string change_model_init;
	string change_model_file;
	bool interactive_change = true; ///< currently no other controls
	string output_path; ///< where to store the changed model

	//non interactive command:
	string search_object_name; ///< the object name to search
	string object_command; ///< can be DELETE or init_string to pass the object
	string output_log_file; ///< additional file to output/store object jsons in PRINT command

	ProgramArgs()
	{
		po::options_description program_desc("Program Options");
		program_desc.add_options()
			("model_path", po::value<string>(&model_path)->required(), "the location of medmodel")
			("change_model_init", po::value<string>(&change_model_init)->default_value(""), "init argument to change the model in runtime")
			("change_model_file", po::value<string>(&change_model_file)->default_value(""), "json file to read multiple changes to the model in runtime - should have \"changes\" element with array of change requests")
			("output_path", po::value<string>(&output_path)->required(), "where to store the changed model")
			("interactive_change", po::value<bool>(&interactive_change)->default_value(true), "If true will run on interactive mode to change model")

			("search_object_name", po::value<string>(&search_object_name)->default_value(""), "When non interactive mode: the object name to search")
			("object_command", po::value<string>(&object_command)->default_value(""), "When non interactive mode: can be DELETE or init_string to pass the object")
			("output_log_file", po::value<string>(&output_log_file)->default_value(""), "additional file to output/store object jsons in PRINT command")
			;

		init(program_desc);
	}

};
#endif
