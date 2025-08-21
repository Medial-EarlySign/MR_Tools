#include "common.h"

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

// Read input data
// Comma separated val1,val2....,val#,score,outcome
// Allow first line to be a header
int read_input_data(const string& inFileName, vector<MedSample>& samples, string& header) {

	// Open
	ifstream infile;
	infile.open(inFileName.c_str(), ifstream::in);
	if (!infile.is_open())
		MTHROW_AND_ERR("Cannot open %s for reading\n", inFileName.c_str());

	// Read
	string line;
	int nFields = -1;
	int idx = 0;
	while (getline(infile, line)) {
		vector<string> fields;
		boost::split(fields, line, boost::is_any_of(","));
		int nCurrFields = (int)fields.size();

		// Check for header
		try {
			int outcome = stof(fields[nCurrFields - 1]);
			float score = stof(fields[nCurrFields - 2]);
			MedSample sample;
			sample.id = idx++;
			sample.outcome = outcome;
			sample.prediction.push_back(score);
			for (int i = 0; i < nCurrFields - 2; i++)
				sample.str_attributes[to_string(i)] = fields[i];
			samples.push_back(sample);
		}
		catch (const std::invalid_argument& ia) {
			if (nFields == -1) {
				MLOG("First line is \'%s\' - Considered as header\n", line.c_str());
				header = line;
			}
			else
				MTHROW_AND_ERR("Cannot parse line %d : \'%s\'\n", idx + 1, line.c_str());
		}

		if (nFields == -1)
			nFields = nCurrFields;
		else if (nFields != nCurrFields)
			MTHROW_AND_ERR("Field number inconsistency - line %d has %d fields compared to %d so far\n", idx + 1, nCurrFields, nFields);
	}

	return nFields - 2;
}


// Print output
void write_output_data(const string& outFileName, vector<MedSample>& samples, int nAttr, string& header) {

	// Open
	ofstream outfile;
	outfile.open(outFileName.c_str(), ifstream::out);
	if (!outfile.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", outFileName.c_str());

	if (!header.empty())
		outfile << header << ",calibrated_score\n";

	for (MedSample& sample : samples) {
		// Attributes
		for (int i = 0; i < nAttr; i++)
			outfile << sample.str_attributes[to_string(i)] << ",";

		// Original prediction
		outfile << sample.prediction[0] << ",";

		// Outcome
		outfile << sample.outcome << ",";

		// Calibrated prediction
		outfile << sample.prediction[1] << "\n";
	}
	outfile.close();
}