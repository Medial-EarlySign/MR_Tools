#ifndef __VALIDATION_FUNCS__H__
#define __VALIDATION_FUNCS__H__

#include "AnalyzeScores.h"

int validate_bounds(input_data& indata, work_space& work, FILE *fout, int nbootstrap, quick_random& qrand);
int validate_bounds_autosim(input_data& indata, work_space& work, FILE *fout, int nbootstrap, quick_random& qrand);

#endif