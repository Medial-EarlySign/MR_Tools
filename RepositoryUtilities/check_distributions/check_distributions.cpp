#define _CRT_SECURE_NO_WARNINGS
// Check signal distributions.

#include "check_distributions.h"

int main(int argc, char *argv[])
{

	// Command Line
	assert(argc == 2);
	string configFile = argv[1];

	// Read Repository
	MedPidRepository rep;
	int rc = rep.init(configFile);
//	int rc = rep.read_all(configFile);
	assert(rc == 0);

	// Take up to ~1M ids
	size_t nIds = rep.all_pids_list.size();
	vector<int> pIds;
	if (nIds <= 1000000)
		pIds = rep.all_pids_list;
	else {
		float p = 1000000.0 / nIds;
		for (unsigned int i = 0; i < nIds; i++) {
			if (rand() / (RAND_MAX + 1.0) < p)
				pIds.push_back(rep.all_pids_list[i]);
		}
	}
	cerr << "NUMBER OF IDS = " << pIds.size() << endl;

	// Identify relevant signal
	vector<int> signalsToCheck;
	vector<int>& signalIds = rep.sigs.signals_ids;

	for (int i = 0; i < signalIds.size(); i++) {
		string signalName = rep.dict.name(signalIds[i]);
		if (signalName == "eGFR_MDRD") continue;

		// Check Type
		if (rep.sigs.type(signalIds[i]) != T_DateVal)
			cerr << "Signal " + signalName + " is not DateVal" << endl;
		else
			signalsToCheck.push_back(signalIds[i]);
	}

	// load
	cerr << "Loading " << signalsToCheck.size() << " signals\n";
	rc = rep.load(signalsToCheck,pIds);
	cerr << "DONE\n";
	assert(rc == 0);

	// Check Signals
	map<int, string> info;
	
#pragma omp parallel for
	for (int i = 0; i < signalsToCheck.size(); i++)
		info[signalsToCheck[i]] = checkSignalDistribution(rep, signalsToCheck[i], pIds);
//		info[signalsToCheck[i]] = checkSignal(rep, signalsToCheck[i],pIds);

	for (auto& rec : info)
		cout << rec.second << endl;

	return 0;
}

// Check Signal Distribution
string checkSignal(MedPidRepository& rep, int signalId, vector<int>& pIds) {

	string signalName = rep.dict.name(signalId); 

	// Check Type
	if (rep.sigs.type(signalId) != T_DateVal)
		return ("Signal " + signalName + "is not DateVal");

	// Extract Values
	vector<float> values;
	int len;

	for (int pid :pIds) {

		SDateVal *signal = (SDateVal *)rep.get(pid, signalId, len);
		for (int i = 0; i < len; i++)
			values.push_back(signal[i].val);

	}

	// How many values are there
	unordered_set<float> valuesSet;
	for (float value : values)
		valuesSet.insert(value);

	int nValues = valuesSet.size();
	if (nValues < 10) 
		return ("Signal " + signalName + " has only " + to_string(nValues) + " values");

	// Take Log
	vector<float> logValues(values.size());
	for (unsigned int i = 0; i < values.size(); i++) {
		if (values[i] <= 0)
			logValues[i] = log(0.001);
		else
			logValues[i] = log(values[i]);
	}

	// Measure correlation
	float r2 = correlateToGaussian(values); 
	float r2Log = correlateToGaussian(logValues); 
	char info[256];
	sprintf(info,"%s: Normal = %.3f\tLogNormal = %.3f", signalName.c_str(), r2, r2Log);
	return (string(info));
}

float correlateToGaussian(vector<float>& inValues) {

	// Remove VERY CLEAR outliers
	MedValueCleaner cleaner;
	ValueCleanerParams& cleanerParams = cleaner.params;
	cleanerParams.take_log = false; cleanerParams.missing_value = MED_MAT_MISSING_VALUE; cleanerParams.doTrim = false; cleanerParams.doRemove = true; cleanerParams.trimming_sd_num = 15; cleanerParams.removing_sd_num = 15;
	
	cleaner.get_iterative_min_max(inValues);
	if (fabs(cleaner.removeMax - cleaner.removeMin) < 0.0001)
		return -2.0;
 
	vector<float> values;
	for (float value : inValues) {
		if (value > cleaner.removeMin && value < cleaner.removeMax)
			values.push_back(value);
	}

	if (values.size() == 0)
		return -2.0;

	// Get Mean + Standard Deviation again
	double sum = 0;
	int n = (int)values.size();
	for (float value : values)
		sum += value;
	float mean = sum / n;

	sum = 0;
	for (float value : values)
		sum += (value - mean)*(value - mean);
	float sdv = sqrt(sum / n);

	// Get Min/Max
	float min = values[0], max = values[0];
	for (float value : values) {
		if (value < min) 
			min = value;
		else if (value > max) 
			max = value;
	}

	// How many values are there
	unordered_set<float> valuesSet;
	for (float value : values)
		valuesSet.insert(value);
	int nValues = valuesSet.size();

	// Binning
	int nBins = 100;
	if (nValues < nBins)
		nBins = nValues;
	float binSize = (max - min) / nBins;

	vector<float> hist(nBins, 0.0);
	for (float value : values) {
		int bin = (int)((value - min) / binSize);
		if (bin == nBins) bin = nBins - 1;
		hist[bin] ++;
	}

	// Normal Distribution
	normal gaussian(mean, sdv);
	vector<float> normHist(nBins);
	for (int i = 0; i < nBins; i++) {
		float lowerBound = boost::math::cdf(gaussian, min + i*binSize);
		float upperBound = boost::math::cdf(gaussian, min + (i+1)*binSize);
		normHist[i] = upperBound - lowerBound;
	}

	// Return correlation
	double r2;
	int nCorr;
	r2 = medial::performance::pearson_corr(hist, normHist, (float) MED_MAT_MISSING_VALUE, nCorr);
	assert(nCorr > 0);

//	for (int i = 0; i < nBins; i++)
//		cerr << i << "\t" << mean << "\t" << sdv << "\t" << min + i*binSize << "\t" << hist[i] << "\t" << normHist[i] << endl;
//	cerr << "\n";

	return (float) r2;
}

string checkSignalDistribution(MedPidRepository& rep, int signalId, vector<int>& pIds) {

	string signalName = rep.dict.name(signalId);
	string info;
	char c_info[256];

	// Check Type
	if (rep.sigs.type(signalId) != T_DateVal)
		return ("Signal " + signalName + "is not DateVal");

	// Extract Values
	vector<float> values;
	int len;

	for (int pid : pIds) {

		SDateVal *signal = (SDateVal *)rep.get(pid, signalId, len);
		for (int i = 0; i < len; i++)
			values.push_back(signal[i].val);

	}

	// Build Histogram
	map<float,int> valuesSet;
	for (float value : values)
		valuesSet[value]++;

	int nValues = valuesSet.size();
	if (nValues < 10)
		return ("Signal " + signalName + " has only " + to_string(nValues) + " values");

	// Check consecutive values
	vector<float> diffValues;
	for (auto& rec : valuesSet)
		diffValues.push_back(rec.first);

	sort(diffValues.begin(), diffValues.end());
	for (unsigned int i = 1; i < diffValues.size(); i++) {

		// more than X5 change
		float r = (1.0*valuesSet[diffValues[i]]) / valuesSet[diffValues[i - 1]];
		if ((r < 0.2 || r > 5.0) && (valuesSet[diffValues[i]]>100 || valuesSet[diffValues[i - 1]] > 100)) {
			sprintf(c_info, "%s\t%f: %d vs %f: %d\n", signalName.c_str(),diffValues[i], valuesSet[diffValues[i]], diffValues[i - 1], valuesSet[diffValues[i - 1]]);
			info += c_info;
		}
		/*
		else if (i < diffValues.size() - 1) {
			float r2 = (1.0*valuesSet[diffValues[i]]) / valuesSet[diffValues[i + 1]];
			if (((r < 0.75 && r2 < 0.75) || (r > 1.333 && r2 > 1.3333)) && (valuesSet[diffValues[i]]>100 || valuesSet[diffValues[i - 1]] > 100 || valuesSet[diffValues[i+1]] > 100)) {
				sprintf(c_info, "%s\t%f: %d vs %f: %d and %f: %d\n", signalName.c_str(),diffValues[i], valuesSet[diffValues[i]], diffValues[i - 1], valuesSet[diffValues[i - 1]], diffValues[i + 1], valuesSet[diffValues[i + 1]]);
				info += c_info;
			}
		}
		*/
	}

	return info;
}
