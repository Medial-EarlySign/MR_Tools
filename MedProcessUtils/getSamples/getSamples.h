// Generate a samples set

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void getSamples(MedPidRepository& rep, vector<string>& anchorSignals, int minAge, int maxAge, int history, int followUp, string& cancerSet, int winStart, int winEnd, int jump, int minYear, int maxYear,
	int trainBitMap, MedSamples& samples);