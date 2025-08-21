// File of common functions

#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string/classification.hpp>
#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "InfraMed/InfraMed/Utils.h"
#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>

#include "MedProcessTools/MedProcessTools/Calibration.h"

#include <boost/serialization/map.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/serialization/utility.hpp>
#include <boost/algorithm/string/classification.hpp>
#include <boost/algorithm/string/split.hpp>
#include <omp.h>

#include <Logger/Logger/Logger.h>
#include <SerializableObject/SerializableObject/SerializableObject.h>
#include <MedIO/MedIO/MedIO.h>

#include <algorithm>
#include <time.h>
#include <string.h>

#include <MedUtils/MedUtils/MedGlobalRNG.h>

int read_input_data(const string& inFileName, vector<MedSample>& samples, string& header);
void write_output_data(const string& outFileName, vector<MedSample>& samples, int nAttr, string& header);