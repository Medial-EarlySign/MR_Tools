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

class test_params : public SerializableObject {
public:
	double unit_diff_threshold = 5;
	double unit_factor_threshold = 0.3;
	double res_threshold = 0.001;
	double res_factor_threshold = 0.3;
	double  res_tails_ignore = 0.05;
	int res_min_diff_num = 100; ///< minimal num for diff in peaks
	int res_max_allowed_peaks = 5;

	int init(map<string, string>& map) {
		for (const auto &it : map)
		{
			if (it.first == "unit_diff_threshold")
				unit_diff_threshold = stof(it.second);
			else if (it.first == "unit_factor_threshold")
				unit_factor_threshold = stof(it.second);
			else if (it.first == "res_threshold")
				res_threshold = stof(it.second);
			else if (it.first == "res_factor_threshold")
				res_factor_threshold = stof(it.second);
			else if (it.first == "res_tails_ignore")
				res_tails_ignore = stof(it.second);
			else if (it.first == "res_max_allowed_peaks")
				res_max_allowed_peaks = stoi(it.second);
			else if (it.first == "res_min_diff_num")
				res_min_diff_num = stoi(it.second);
			else
				HMTHROW_AND_ERR("Error in test_params::init - Unsupported param %s\n", it.first.c_str());
		}
		return 0;
	}
};

class ProgramArgs : public medial::io::ProgramArgs_base {
private:
	string test_args_s;
	void post_process() {
		if (!test_args_s.empty())
			test_args.init_from_string(test_args_s);
		if (rep.empty() && base_path.empty())
			HMTHROW_AND_ERR("Error must provide rep or base_path\n");
	}

public:
	string base_path; ///< the location to read input file
	string rep; ///< repository instead of input base_path
	string output; ///< the location to write output file
	string delimeter; ///< the input file delimeter
	int column_num;
	bool has_header; ///< True if the file has header
	int sample_each_file; ///< 
	string signal_name;
	bool use_threads;
	string binning;
	bool normalize;
	int buffer_size;
	bool test_categorical; ///< if true will test all categorical signals

	test_params test_args;

	ProgramArgs()
	{
		po::options_description program_desc("Program Options");
		program_desc.add_options()
			("base_path", po::value<string>(&base_path)->default_value(""), "the location for inputs signals directory")
			("rep", po::value<string>(&rep)->default_value(""), "the location repository")
			("output", po::value<string>(&output)->default_value(""), "the location to write output files - html,csv")
			("signal_name", po::value<string>(&signal_name)->default_value(""), "the signal name to look for in base_path. ALL - means all numeric signals")
			("binning", po::value<string>(&binning)->default_value(""), "binning of signal values")
			("delimeter", po::value<string>(&delimeter)->default_value("\t"), "the input file delimeter")
			("has_header", po::value<bool>(&has_header)->default_value(false), "True if the file has header")
			("normalize", po::value<bool>(&normalize)->default_value(false), "True if need to normalize histogram")
			("use_threads", po::value<bool>(&use_threads)->default_value(false), "True if to use threads")
			("column_num", po::value<int>(&column_num)->default_value(4), "the column number to take from each line in file")
			("buffer_size", po::value<int>(&buffer_size)->default_value(5000), "the buffer size for reading")
			("sample_each_file", po::value<int>(&sample_each_file)->default_value(0), "the line number buffer for write. 0 means no buffer - write all")
			("test_args", po::value<string>(&test_args_s)->default_value("unit_diff_threshold=5;unit_factor_threshold=3;res_threshold=0.001;res_factor_threshold=0.3;res_tails_ignore=0.05;res_min_diff_num=100;res_max_allowed_peaks=5"), "params for testing signal")
			("test_categorical", po::value<bool>(&test_categorical)->default_value(false), "if true will test all categorical signals - all values in dict")
			;

		init(program_desc);
	}

};
#endif
