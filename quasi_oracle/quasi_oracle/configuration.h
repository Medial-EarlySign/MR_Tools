#ifndef __CONFIGURATION_H__
#define __CONFIGURATION_H__

#include "Logger/Logger/Logger.h"
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/join.hpp>
#include <boost/algorithm/string/split.hpp>
#include <boost/program_options.hpp>
#include "boost/date_time/posix_time/posix_time.hpp"

using namespace std;
namespace po = boost::program_options;
namespace pt = boost::posix_time;

class configuration {
public:

	string runDir; // Directory for input/output files

	string repFile; // Repository file
	string samplesFile; // File for sampels
	string featuresFile; // Input matrix (directly given);
	int nFolds = -1; // # of cross validation folds
	int read_e = 0; // Read e(X) from file
	int only_e = 0; // Perform only learning of e
	string eFile; // input/output e-File
	int read_m = 0; // Read m(X) from file
	int only_m = 0; // Perform only learning of m
	string mFile; // input/output m-File
	string out; // output file (predictor/model)
	string treatmentName = "Treatment"; // Name of treatment in samples (as attribute) or features (as data entry)
	string treatmentTimeName ; // Name of treatment-time attribute in samples
	map<string,string> predictorName, predictorParams, modelFile; // predictor/model specification
	map<string,vector<string>> modelAlts; // additional predictor/model specification
	map<string, string> performanceFile; // output performance files
	map<string, string> calibrationParams; // calibration parameters
	string iteFile; // Optional output ITE file

	string defaultCalibrationParams = "calibration_type=binning;min_preds_in_bin=150;min_score_res=0.0001;min_prob_res=0.02;bins_num=50;fix_pred_order=1";

	// Functions
	void read_from_file(const string& fileName);
	void write_to_file(const string& fileName);
	void write_to_file();

};



#endif