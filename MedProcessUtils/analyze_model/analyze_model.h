// Analyze a model

#include "CommonLib/CommonLib/commonHeader.h"
#include "MedProcessTools/MedProcessTools/Calibration.h"
#include <sys/stat.h>

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void analyze_contributions(po::variables_map& vm);