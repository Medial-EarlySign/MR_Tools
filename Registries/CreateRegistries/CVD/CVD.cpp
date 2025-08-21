// CVD.cpp : Defines the entry point for the console application.
//

#include "CVD.h"


#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[]) {

	fprintf(stderr, "create registries for cvd \n");

	int QA_YEAR = 2005;
	int EVENT_GAP = 30;
	int ADDMISION_GAP = 60;

	// Running parameters

	po::variables_map vm;
	if (read_run_params(argc, argv, vm) == -1) {
		fprintf(stderr, "read_run_params failed\n");
		return -1;
	}

	assert(vm.count("FileOut")); 
	string outFile = vm["FileOut"].as<string>();
	FILE *fout = fopen(outFile.c_str(), "w");

	// Init Repository
	string configFile = vm["config"].as<string>();

	MedPidRepository rep;
	vector<string> signals = { "BYEAR", "GENDER" , "STARTDATE" , "ENDDATE" , "TRAIN" };
	vector<int> ids;

	rep.read_all(configFile, vector<int>(), signals);

	string run_type = vm["Runtype"].as<string>();
	string signalname = vm["SignalName"].as<string>();


	int rc, len;
	string fname;

	vector<pair<string, string> >  disease_readcodes;
	fname = vm["DiseaseReadCodesFile"].as<string>();
	rc = readReadCodes(fname, disease_readcodes);
	assert(rc == 0);


	int past_ind = 0;
	vector<pair<string, string> >  disease_past_readcodes;
	if (vm.count("PastReadCodesFile") > 0) {
		fname = vm["PastReadCodesFile"].as<string>();
		rc = readReadCodes(fname, disease_past_readcodes);
		assert(rc == 0);
		past_ind = 1;
	}

	int admission_ind = 0;
	vector<pair<string, string> >  admission_readcodes;
	if (vm.count("AdmissionReadCodesFile") > 0) {
		MLOG("AdmissionReadCodesFile specified, requiring hospital admission within %d days as a proof of real event\n", ADDMISION_GAP);
		fname = vm["AdmissionReadCodesFile"].as<string>();
		rc = readReadCodes(fname, admission_readcodes);
		assert(rc == 0);
		admission_ind = 1;
	}
	else MLOG("AdmissionReadCodesFile not specified, not requiring hospital admission as a proof of real event\n");


	vector<string> dxSignals = { "RC" };
	rep.load(dxSignals);
	vector<int> dxSignalIds;
	for (string& signal : dxSignals) dxSignalIds.push_back(rep.dict.id(signal));


	vector<unsigned char> diseaseLut;
	buildLookUpTable(rep, dxSignals, disease_readcodes, diseaseLut);

	vector<unsigned char> admissionpLut;
	if (admission_ind == 1)
		buildLookUpTable(rep, dxSignals, admission_readcodes, admissionpLut);


	vector<unsigned char> diseasePastLut;
	if (past_ind == 1)
		buildLookUpTable(rep, dxSignals, disease_past_readcodes, diseasePastLut);

	int sectionId = rep.dict.section_id(dxSignals[0]);

	
	int count_1 = 0;
	int count_2 = 0;
	int count_3 = 0;

	int count = 0;
	for (int jj = 0; jj < rep.index.pids.size(); jj++) {
		count += 1;
		if (count % 100000 == 0) fprintf(stderr, "%i ",count);

		int pid = rep.index.pids[jj];

		//admission
		vector<int> admission_dates;
		if (admission_ind == 1) {
			for (int signalId : dxSignalIds) {
				SDateVal *signalData = (SDateVal *)rep.get(pid, signalId, len);
				for (int i = 0; i < len; i++) {
					if (admissionpLut[(int)signalData[i].val]) {
						int my_date = (int)signalData[i].date;
						admission_dates.push_back(my_date);
					}
				}
			}
		}

		//past 
		int min_hist = -1;
		if (past_ind == 1) {
			for (int signalId : dxSignalIds) {
				SDateVal *signalData = (SDateVal *)rep.get(pid, signalId, len);
				for (int i = 0; i < len; i++) {
					if (diseasePastLut[(int)signalData[i].val]) {
						int my_date = (int)signalData[i].date;
						//past type 3
						min_hist = my_date;
						//fprintf(fout , "%d\t%s\t%d\t%d\n", pid, signalname.c_str(), my_date, 3);
						if ((int)my_date/10000>= QA_YEAR) count_3++;
						break;
					}
				}
			}
		}

		//disease
		int min_event = -1;
		for (int signalId : dxSignalIds) {
			SDateVal *signalData = (SDateVal *)rep.get(pid, signalId, len);
			int prev_date = -1;
			for (int i = 0; i < len; i++) {
				if (diseaseLut[(int)signalData[i].val]) {
					int my_date = (int)signalData[i].date;
					int my_val = (int)signalData[i].val;

					if (run_type == "event") {
						if (prev_date == -1 || get_day(my_date) - get_day(prev_date)>EVENT_GAP) {

							if (admission_ind == 1) {
								//look for admission
								int id_admission_flag = 0;
								for (int kk = 0; kk < admission_dates.size(); kk++) {
									int admission_dates_n = get_day(admission_dates[kk]);
									int my_date_n = get_day(my_date);
									int diff = my_date_n - admission_dates_n;
									int diff_abs = abs(diff);

									if (diff_abs < ADDMISION_GAP) id_admission_flag = 1;
								}


								if (id_admission_flag == 1) {
									if ((int)my_date / 10000>= QA_YEAR) count_1++;
									if (min_event != -1) min_event = my_date;
									//type 1 event with addmition
									fprintf(fout, "%d\t%s\t%d\t%d\n", pid, signalname.c_str(), my_date, 1);
								}
								else {
									if ((int)my_date / 10000>= QA_YEAR) count_2++;
									if (min_event != -1) min_event = my_date;
									//type 2 event no addmision
									fprintf(fout, "%d\t%s\t%d\t%d\n", pid, signalname.c_str(), my_date, 2);
								}
							}
							else {
								//type 1 event no need for addmision
								if ((int)my_date / 10000>= QA_YEAR) count_1++;
								if (min_event != -1) min_event = my_date;
								fprintf(fout, "%d\t%s\t%d\t%d\n", pid, signalname.c_str(), my_date, 1);
							}
						}
						prev_date = my_date;
					}
					else {
						//type 1 first
						if ((int)my_date / 10000>= QA_YEAR) count_1++;
						if (min_event != -1) min_event = my_date;
						fprintf(fout, "%d\t%s\t%d\t%d\n", pid, signalname.c_str(), my_date, 1);
						break;
					}
				}
			}
		}

		if (min_hist != -1 && (min_event == -1 || min_hist < min_event)) {
			//print history event
			fprintf(fout, "%d\t%s\t%d\t%d\n", pid, signalname.c_str(), min_hist, 3);
		}
	}


	fprintf(stderr, "\ncount_1: %i\n", count_1);
	fprintf(stderr, "count_2: %i\n", count_2);
	fprintf(stderr, "count_3: %i\n", count_3);

	fclose(fout);
	MLOG("wrote [%s]\n", outFile.c_str());
}

// Read run-params
int read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			//("config", po::value<string>()->default_value("/home/Repositories/THIN/thin_jun2017/thin.repository"), "repository file name")
			("config", po::value<string>(), "repository file name")
			("DiseaseReadCodesFile", po::value<string>(), "DiseaseReadCodesFile")
			("PastReadCodesFile", po::value<string>(), "PastReadCodesFile")
			("AdmissionReadCodesFile", po::value<string>(), "AdmissionReadCodesFile")
			("Runtype", po::value<string>()->default_value("event"), "event")
			("SignalName", po::value<string>(), "SignalName")
			("FileOut", po::value<string>(), "FileOut")

			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}
	return 0;
}

int readReadCodes(string& fname, vector<pair<string, string> >& rcs) {

	fprintf(stderr, "%s\n", fname.c_str());

	ifstream inf(fname);
	if (!inf) {
		cerr << "Cannot open " << fname << " for reading\n";
		return -1;
	}

	string line;
	while (getline(inf, line)) {

		vector<string> fields;
		split(fields, line, boost::is_any_of("\t"));
		if (fields.size() == 1) {
			string my_name = fields[0];
			string my_readcode = my_name.substr(0, 7);
			string my_desc = my_name.substr(7);
			rcs.push_back({ my_readcode,my_desc });
		}
		else {
			string my_readcode = fields[0];
			string my_desc = fields[1];
			rcs.push_back({ my_readcode,my_desc });
		}
	}

	return 0;
}

// Build a look-up table
void buildLookUpTable(MedPidRepository& rep, vector<string>& signals, vector<pair<string, string> >& readCodes, vector<unsigned char>& lut) {

	assert(readCodes.size() < 255); // to fit in a char.

	int sectionId = rep.dict.section_id(signals[0]);
	for (string& signal : signals) assert(rep.dict.section_id(signal) == sectionId);

	int maxId = rep.dict.dicts[sectionId].Id2Name.rbegin()->first;
	lut.assign(maxId + 1, 0);

	for (unsigned int j = 0; j < readCodes.size(); j++) {
		if (rep.dict.id(sectionId, readCodes[j].first) != -1)
			lut[rep.dict.id(sectionId, readCodes[j].first)] = j + 1;
		else fprintf(stderr, "prep_sets_lookup_table() : Found bad name %s :: not found in dictionary()\n", readCodes[j].first.c_str());
	}
}


