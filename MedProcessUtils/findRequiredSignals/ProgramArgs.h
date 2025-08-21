#pragma once

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

#include "CommonLib/CommonLib/commonHeader.h"
#include <MedUtils/MedUtils/MedUtils.h>

class ProgramArgs : public medial::io::ProgramArgs_base
{
private:
	string req_signals_s;
	string delete_signals_s;
public:
	string samples_file;
	string model_file;
	string rep_file;
	int evaluationsToPrint;
	string msrName;
	int numTestsPerIter;
	string outFile;
	vector<string> req_signals;
	unordered_set<string> delete_signals;
	size_t maximalNumSignals;
	int numIterationsToContinue;
	float requiredRatioPerf;
	float requiredAbsPerf;
	string cohort_params;  ///< cohort parameters for bootstrap performance evaluation (type:from,to/type:from,to/....)
	string bootstrap_params; ///< parameters for bootstrapping ('/' separaters)
	string msr_params;
	string bootstrap_json;
	bool skip_supersets;

	ProgramArgs();

	void post_process();
};