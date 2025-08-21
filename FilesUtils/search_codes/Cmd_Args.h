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
	string rep; ///< repository instead of input base_path
	string pid_time_file; ///< file to pid_time
	bool input_is_med_samples; ///< if true input is MedSamples
	string signal; ///< the signal
	int val_channel; ///< signal channel
	int time_channel; ///< signal channel
	string code_list; /// code list file or list
	bool code_list_is_file; ///< if true code_list is file
	int limit_count; ///< limit print count of each code name
	string output_file;
	int time_win_from, time_win_to; ///< backward time window definition to search 

	ProgramArgs()
	{
		po::options_description program_desc("Program Options - Inspect categories values and sets. helps debug dicts");
		program_desc.add_options()
			("rep", po::value<string>(&rep)->required(), "the location repository")
			("pid_time_file", po::value<string>(&pid_time_file)->required(), "file to pid_time")
			("input_is_med_samples", po::value<bool>(&input_is_med_samples)->default_value(true), "If true pid_time_file is MedSamples otherwise it's tsv with 2 cols of pid,time")
			("signal", po::value<string>(&signal)->required(), "the signal")
			("val_channel", po::value<int>(&val_channel)->default_value(0), "the signal channel")
			("time_channel", po::value<int>(&time_channel)->default_value(0), "the signal channel")
			("code_list", po::value<string>(&code_list)->required(), "code list file or list")
			("code_list_is_file", po::value<bool>(&code_list_is_file)->default_value(false), "If true code_list is file")
			("time_win_from", po::value<int>(&time_win_from)->default_value(0), "backward time window from to search for code")
			("time_win_to", po::value<int>(&time_win_to)->default_value(0), "backward time window to to search for code (should be bigger than from)")

			("limit_count", po::value<int>(&limit_count)->default_value(3), "the signal channel")
			("output_file", po::value<string>(&output_file)->required(), "the output_file")

			;

		init(program_desc);
	}

};
#endif
