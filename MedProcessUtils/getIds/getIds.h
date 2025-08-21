// Get list of ids according to signal + sets

#include "CommonLib/CommonLib/commonHeader.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void getValidIds(MedPidRepository& rep, int signalId, VEC_CATEGORIES setsLUT, int channel, vector<int>& ids, vector<int>&lastDates, vector<int>& validFlags, string& reasonsFile);
