
#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "InfraMed/InfraMed/Utils.h"
#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>

#include "MedStat/MedStat/MedStat.h"
#include "MedStat/MedStat/MedPerformance.h"
#include "MedAlgo/MedAlgo/MedAlgo.h"
#include "MedUtils/MedUtils/MedCohort.h"
#include "MedProcessTools/MedProcessTools/MedModel.h"
#include "MedProcessTools/MedProcessTools/SampleFilter.h"

#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>
#include <omp.h>

#include <Logger/Logger/Logger.h>
#include <MedIO/MedIO/MedIO.h>

#include <algorithm>
#include <time.h>
#include <string.h>

class CmdArgs : public medial::io::ProgramArgs_base
{
public:
	string file;
	CmdArgs();
};

class admin { 
public:
	int pid,start,end ;
	string type;

	admin() {}
	admin(vector<string>& fields) { pid = stoi(fields[0]); start = stoi(fields[2]); end = stoi(fields[3]); type = fields[4]; }
};


void read_admissions(string& file, vector<admin>& admissions);
void process_admissions(vector<admin>& admissions);
void write_admissions(string& file, vector<admin>& admissions);
