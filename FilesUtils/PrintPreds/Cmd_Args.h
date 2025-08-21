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
	string input; ///< the location to read input file
	string output; ///< the location to write output file
	string binning;
	bool normalize;
	string feature_name; ///< if given, the input is MedFeatures. will use this feature instead of score to analyze. Use pred_0 to use prediction and just read for MedFeatures
	string html_template; ///< html template

	ProgramArgs()
	{
		po::options_description program_desc("Program Options");
		program_desc.add_options()
			("input", po::value<string>(&input)->required(), "the location for input MedSamples")
			("output", po::value<string>(&output)->required(), "the location to write output files - html,csv")
			("binning", po::value<string>(&binning)->default_value(""), "binning of signal values")
			("normalize", po::value<bool>(&normalize)->default_value(false), "True if need to normalize histogram")
			("feature_name", po::value<string>(&feature_name)->default_value(""), "if given, the input is MedFeatures. will use this feature instead of score to analyze. Use pred_0 to use prediction and just read for MedFeatures")
			("html_template", po::value<string>(&html_template)->default_value(""), "HTML template")
			;

		init(program_desc);
	}

};
#endif
