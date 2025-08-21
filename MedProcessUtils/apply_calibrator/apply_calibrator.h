// Apply a calibrator

#include "CommonLib/CommonLib/commonHeader.h"
#include "MedProcessTools/MedProcessTools/Calibration.h"

// Functions
void read_run_params(int argc, char **argv, po::variables_map& vm);
void compare_probability_time_window(Calibrator& cal, MedSamples& samples, string& outTableFile);