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

class ProgramArgs : public medial::io::ProgramArgs_base {
private:

	void post_process() {
		if (input.size() != date_app.size())
			HMTHROW_AND_ERR("Error - please pass same number of args to input(%zu) and date_app(%zu)\n",
				input.size(), date_app.size());
	}

public:
	vector<string> input; ///< the location to read input files
	vector<int> date_app; ///< applicable date for each file
	string output; ///< the location to write output file
	string delimeter; ///< the input file delimeter
	bool has_header; ///< True if the file has header
	int close_buffer_backward;
	int close_buffer_foreward;

	ProgramArgs()
	{
		po::options_description program_desc("Program Options");
		program_desc.add_options()
			("input", po::value<vector<string>>(&input)->multitoken(), "the location to read multiple input PID START_DATE END_DATE")
			("date_app", po::value<vector<int>>(&date_app)->multitoken(), "the max date of each file")
			("output", po::value<string>(&output)->required(), "the location to write output file")
			("delimeter", po::value<string>(&delimeter)->default_value("\t"), "the input file delimeter")
			("has_header", po::value<bool>(&has_header)->default_value(false), "True if the file has header")
			("close_buffer_backward", po::value<int>(&close_buffer_backward)->default_value(30), "the buffer size to close holes between files")
			("close_buffer_foreward", po::value<int>(&close_buffer_foreward)->default_value(30), "the buffer size to close holes between files")
			;

		init(program_desc);
	}

};
#endif
