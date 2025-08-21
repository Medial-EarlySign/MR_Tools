#include "InfraMed/InfraMed/MedConvert.h"
#include "InfraMed/InfraMed/InfraMed.h"
#include "Logger/Logger/Logger.h"
#include "InfraMed/InfraMed/Utils.h"
#include <stdio.h>

#include <stdlib.h>
#include <stdarg.h>

#include <boost/program_options.hpp>

#define PI 3.1415

int main(int argc, char *argv[])
{
	assert(argc == 2);
	string configFile(argv[1]);

	MedRepository rep;

	int rc = rep.read_all(configFile, vector<int>(), vector<int>());
	assert(rc >= 0);

	string setName = "dischargeDestination";
	int setId = rep.dict.id(setName);
	vector<int> memberIds;
	rep.dict.get_set_members(setId, memberIds);
	for (int member : memberIds) {
		cout << rep.dict.name(member) << " (" << member <<  ") is a member of " << setName << endl;
	}
	return -1;

	int drugId = rep.dict.id("Drug");
	assert(drugId != -1);

	int inrId = rep.dict.id("INR");
	assert(inrId != -1);

	int warfarinSetId = rep.dict.id("ATC_B01A_A03");
	assert(warfarinSetId != -1);


	int inrLen,drugLen;
	int idCount;
	for (int id : rep.pids) {
		if (idCount > 10000) return 0;
		idCount++;

		map<int, vector<float> > inrValues;
		SDateVal *inrSignal = (SDateVal *)rep.get(id, inrId, inrLen);
		if (inrLen) {

			for (int i = 0; i < inrLen; i++) {
				int unit = inrSignal[i].date / 10000;
				float value = int(inrSignal[i].val * 10 + 0.5) / 10.0;
				inrValues[unit].push_back(value);
			}

			SDateVal2 *drugSignal = (SDateVal2 *)rep.get(id, drugId, drugLen);

			set<int> warfarinTimes;
			for (int i = 0; i < drugLen; i++) {
				int drugCode = (int)drugSignal[i].val;
				if (rep.dict.is_in_set(drugCode, warfarinSetId))
					warfarinTimes.insert(inrSignal[0].date / 10000);
			}

			for (int unit : warfarinTimes) {
//			for (auto rec : inrValues) {
//				int year = rec.first;
				for (float value : inrValues[unit])
					printf("%f\n", value);
			}
		}
	}
}

/*
	assert (argc == 3) ;
	string configFile(argv[1]) ;
	string signalName(argv[2]) ;

	MedRepository rep;
	vector<string> signalNames;
	signalNames.push_back(signalName) ;
	int rc = rep.read_all(configFile, vector<int>(), signalNames);
	assert(rc >= 0);

	int signalId = rep.dict.id(signalName);
	assert(signalId != -1);

	// Normal/Log-Normal moments
	double s = 0, s2 = 0, sLog = 0, sLog2 = 0;
	int len, n=0, n0=0 ;
	for (int id : rep.index.pids) {
		SDateVal *signal = (SDateVal *) rep.get(id, signalId, len);
		for (int i = 0; i < len; i++) {
			float val = signal[i].val;
			if (val > 0) {
				s += val;
				s2 += val * val;
				sLog += log(val);
				sLog2 += log(val) * log(val);
				n++;
			}
			else
				n0++;
		}
	}
	float mean = s / n; 
	float var = (s2 - mean*s) / (n - 1);
	float meanLog = sLog / n;
	float varLog = (sLog2 - meanLog*sLog) / (n - 1);
	printf("N = %d N0 = %d ; Normal = %f +- %f ; LogNormal = %f +- %f\n", n, n0, mean, sqrt(var), meanLog, sqrt(varLog));

	// LL for normal
	double ll = 0;
	for (int id : rep.index.pids) {
		SDateVal *signal = (SDateVal *)rep.get(id, signalId, len);
		for (int i = 0; i < len; i++) {
			float val = signal[i].val;
			if (val > 0) 
				ll += -(val - mean)*(val - mean) / (2 * var);
		}
	}
	float meanLL = ll / n - 0.5 * log(2 * PI*var);
	printf("Normal mean LL = %f\n", meanLL);

	// LL for log-normal
	// LL for normal
	double llLog = 0;
	float valLog;
	for (int id : rep.index.pids) {
		SDateVal *signal = (SDateVal *)rep.get(id, signalId, len);
		for (int i = 0; i < len; i++) {
			float val = signal[i].val;
			if (val > 0) {
				valLog = log(val);
				llLog += -(valLog - meanLog)*(valLog - meanLog) / (2 * varLog) - valLog; // dp = p(log)dLog => log(dp) = log(p(log)) + log(1/v)
			}
		}
	}

	float meanLlLog = llLog / n - 0.5 * log(2 * PI*varLog);
	printf("LogNormal mean LL = %f\n", meanLlLog);
}

*/