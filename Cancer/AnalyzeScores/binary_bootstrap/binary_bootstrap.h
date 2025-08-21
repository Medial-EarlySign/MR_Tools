#include <assert.h>
#include "CommonLib/AnalyzeScores.h"
#include "CommonLib/BootstrappingFunctions.h"

int read_run_params(int argc,char **argv, po::variables_map& vm, running_flags& flags) ;
int do_binary_autosim(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, quick_random& qrand, po::variables_map& vm) ;
int do_binary_time_windows(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int nestimates, quick_random& qrand, po::variables_map& vm) ;
int init_binary_param_names(int *nestimates, char **param_names, int *autosim_nestimates, char **autosim_param_names) ;