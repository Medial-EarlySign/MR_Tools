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
	}

public:
	string input; ///< the location to read input files
	string output; ///< the location to write output file


	ProgramArgs()
	{
		po::options_description program_desc("Program Options");
		program_desc.add_options()
			("input", po::value<string>(&input)->required(), "the location of input")
			("output", po::value<string>(&output)->default_value(""), "the location to write output file. If not given, will store next to input")
			;

		init(program_desc);
	}

};
#endif
