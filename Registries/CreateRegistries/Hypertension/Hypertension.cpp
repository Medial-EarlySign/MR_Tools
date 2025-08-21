#include "Hypertension.h"

int main(int argc, char *argv[])
{


	// Running parameters

	po::variables_map vm;
	if (read_run_params(argc, argv, vm) == -1) {
		fprintf(stderr, "read_run_params failed\n");
		return -1;
	}

	// Init Repository
	string configFile = vm["config"].as<string>();

	MedPidRepository rep;
	vector<string> signals = { "BYEAR", "GENDER" , "STARTDATE" , "ENDDATE" , "TRAIN" };
	rep.read_all(configFile, vector<int>(), signals);


	// Run
	return generateHyperTenstionRegistry(rep, vm);

}

// Read run-params
int read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	char* pPath;
	pPath = getenv("MR_ROOT");
	if (pPath == NULL) {
		fprintf(stderr, "The current MR_ROOT is not available ");
		return -1;
	}
	try {
		desc.add_options()
			("help", "produce help message")
			("config", po::value<string>()->default_value("/home/Repositories/THIN/thin_jun2017/thin.repository"), "repository file name")
			("readCodesFile", po::value<string>()->default_value(string(pPath)+"/Tools/Registries/Lists/hyper_tension.desc"), " file of readcodes to count")
			("CHF_ReadCodes", po::value<string>()->default_value(string(pPath) +"/Tools/Registries/Lists/heart_failure_events.desc"),"ReadCodes for CHF")
			("MI_ReadCodes", po::value<string>()->default_value(string(pPath) + "/Tools/Registries/Lists/mi.desc"), "ReadCodes for MI")
			("AF_ReadCodes", po::value<string>()->default_value(string(pPath) + "/Tools/Registries/Lists/AtrialFibrilatioReadCodes.desc"), "ReadCodes for AF")
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


// Read ReadCodes file
int readReadCodes(string& fname, vector<pair<string, string> >& rcs) {

	ifstream inf(fname);
	if (!inf) {
		cerr << "Cannot open " << fname << " for reading\n";
		return -1;
	}

	string line;
	while (getline(inf, line)) {
		
		vector<string> fields;
		split(fields, line, boost::is_any_of("\t"));
		if (fields.size() != 2) {
			cerr << "Cannot parse " << line << endl;
			return -1;
		}

		fields[0].erase(remove_if(fields[0].begin(), fields[0].end(), ::isspace), fields[0].end());
		rcs.push_back({ fields[0],fields[1] });
	}

	return 0;
}

// Generate a registry for hypertension
int generateHyperTenstionRegistry(MedPidRepository& rep, po::variables_map& vm) {

	int rc;

	// Required Signals : 
	vector<string> rcSignals = { "RC" };

	// SignalIds
	vector<int> rcSignalIds;
	for (string& signal : rcSignals) { rcSignalIds.push_back(rep.dict.id(signal)); assert(rcSignalIds.back() >= 0); }
	int bpId = rep.dict.id("BP"); assert(bpId >= 0);
	int drugId = rep.dict.id("Drug"); assert(drugId >= 0);
	int genderId = rep.dict.id("GENDER"); assert(genderId >= 0);
	int byearId = rep.dict.id("BYEAR"); assert(byearId >= 0);
	int startId = rep.dict.id("STARTDATE"); int endId = rep.dict.id("ENDDATE"); assert(startId >= 0 && endId >= 0);
	int dmRegId = rep.dict.id("DM_Registry"); assert(dmRegId >= 0);

	// Load
	vector<string> signals = rcSignals;
	signals.push_back("BP"); signals.push_back("Drug"); signals.push_back("DM_Reg");


	MedTimer timer; timer.start();
	rep.load(signals);
	timer.take_curr_time(); fprintf(stderr, "Reading extra data time: %f sec\n", timer.diff_sec());




	// Read Files : ReadCodes (Hyper-Tension, CHF, MI, AF)
	assert(vm.count("readCodesFile"));
	string htFile = vm["readCodesFile"].as<string>();

	assert(vm.count("CHF_ReadCodes"));
	string chfFile = vm["CHF_ReadCodes"].as<string>();

	assert(vm.count("MI_ReadCodes"));
	string miFile = vm["MI_ReadCodes"].as<string>();

	assert(vm.count("AF_ReadCodes"));
	string afFile = vm["AF_ReadCodes"].as<string>();

	vector<pair<string, string> > htReadCodes, chfReadCodes, miReadCodes, afReadCodes;
	rc = readReadCodes(htFile, htReadCodes);assert(rc == 0);
	rc = readReadCodes(chfFile, chfReadCodes); assert(rc == 0);
	rc = readReadCodes(miFile, miReadCodes); assert(rc == 0);
	rc = readReadCodes(afFile, afReadCodes); assert(rc == 0);

	// Build Lookup Tables
	vector<char> htLut, chfLut, miLut, afLut; 
	int section_id = rep.dict.section_id("RC");
	for (string& rcSignal : rcSignals)
		assert(rep.dict.section_id(rcSignal) == section_id);

	vector<string> htSets(htReadCodes.size()), chfSets(chfReadCodes.size()), miSets(miReadCodes.size()), afSets(afReadCodes.size());
	for (unsigned int i = 0; i < htSets.size(); i++)
		htSets[i] = htReadCodes[i].first;
	rc = rep.dict.prep_sets_lookup_table(section_id, htSets, htLut); assert(rc == 0);

	for (unsigned int i = 0; i < chfSets.size(); i++)
		chfSets[i] = chfReadCodes[i].first; 
	rc = rep.dict.prep_sets_lookup_table(section_id, chfSets, chfLut); assert(rc == 0);

	for (unsigned int i = 0; i < miSets.size(); i++)
		miSets[i] = miReadCodes[i].first;
	rc = rep.dict.prep_sets_lookup_table(section_id, miSets, miLut); assert(rc == 0);

	for (unsigned int i = 0; i < afSets.size(); i++)
		afSets[i] = afReadCodes[i].first;
	rc = rep.dict.prep_sets_lookup_table(section_id, afSets, afLut); assert(rc == 0);

	// build drug-specific look : 0 = not relevant to HT. 1 = inidcative of HT. 2 = indicative of HT unless CHF. 3 = indicative of HT unless diabetes. 4 = indicative of HT unless CHF/MI/AF.
	vector<char> drugLut;
	section_id = rep.dict.section_id("Drug");
	buildLookupTableForHTDrugs(rep.dict.dicts[section_id], drugLut);

	// Build a BP cleaner
	vector<RepBasicOutlierCleaner> bpCleaners(2);
	bpCleaners[0].init_from_string("range_min = 0.001; range_max = 100000; val_channel = 0; signal = BP");
	bpCleaners[1].init_from_string("range_min = 0.001; range_max = 100000; val_channel = 1; signal = BP");
	for (int i = 0; i < 2; i++) {
		bpCleaners[i].set_signal_ids(rep.dict) ;
		bpCleaners[i].learn(rep);
	}

	// Loop on ids and create registry

	fprintf(stderr, "count ids : %i \n", (int) rep.pids.size());
	//int chunk = CHUNK;
	int n_chunk = round(rep.pids.size() / CHUNK + 0.5);
	for (int kk = 0; kk < n_chunk; kk++) {
	//for (int kk = 0; kk < 1; kk++) {
		int start = kk*CHUNK;
		int end = (kk + 1)*CHUNK;
		if (end > rep.pids.size())  end = (int) rep.pids.size();

		int n_threads = omp_get_max_threads();
		vector<vector<string>> stderr_vec(n_threads);
		vector<vector<string>> stdout_vec(n_threads);

#pragma omp parallel for
		for (int ii = start; ii < end; ++ii) {
			int len;
			int pid = rep.pids[ii];
			int i_thread = omp_get_thread_num();

			vector<pair<int, string> > data_s;
			vector<pair<int, int> > data; // 0 = Normal BP ; 1 = High BP ; 20 + X = HT Drug ; 3 = HT Read Code (4/5/6 = CHF/MI/AF Read Codes ; 7 = DM)

			// Gender + BYEAR
			int gender = (int)((SVal *)rep.get(pid, genderId, len))[0].val; assert(len == 1);
			int bYear = (int)((SVal *)rep.get(pid, byearId, len))[0].val; assert(len == 1);
			int startDate = (int)((SVal *)rep.get(pid, startId, len))[0].val; assert(len == 1);
			int endDate = (int)((SVal *)rep.get(pid, endId, len))[0].val; assert(len == 1);

			// Blood Pressure
			SDateShort2 *bp = (SDateShort2 *)rep.get(pid, bpId, len);
			vector<int> dates;
			vector<pair<short, short> > bps;
			for (int i = 0; i < len; i++) {

				if (bp[i].val2 < bpCleaners[1].removeMin || bp[i].val1 < bpCleaners[0].removeMin || bp[i].val2 > bpCleaners[1].removeMax || bp[i].val1 > bpCleaners[0].removeMax) {
					stderr_vec[i_thread].push_back( "Outliers Removal : " + to_string(pid)+ " " +  to_string(bp[i].date) + " " + to_string(bp[i].val2)+ " "+ to_string(bp[i].val1) );
					continue;
				}

				if (dates.size() == 0 || bp[i].date != dates.back()) {
					dates.push_back(bp[i].date);
					bps.push_back({ bp[i].val1,bp[i].val2 });
				}
				else {
					// Take minimum per day ....
					if (bp[i].val1 < bps.back().first)
						bps.back().first = bp[i].val1;
					if (bp[i].val2 < bps.back().second)
						bps.back().second = bp[i].val2;
				}
			}

			for (unsigned int i = 0; i < dates.size(); i++) {

				int age = dates[i] / 10000 - bYear;
				int bpFlag = 0;

				if ((age >= 60 && bps[i].second > 150) || (age < 60 && bps[i].second > 140) || bps[i].first > 90)
					bpFlag = 1;
				data.push_back({ dates[i],bpFlag });
				data_s.push_back({ dates[i],to_string(bps[i].second) + "/" + to_string(bps[i].first) });
			}

			// Drugs
			SDateShort2 *drug = (SDateShort2 *)rep.get(pid, drugId, len);
			for (int i = 0; i < len; i++) {
				if (drugLut[drug[i].val1]) {
					data.push_back({ drug[i].date, 20 + drugLut[drug[i].val1] });
					data_s.push_back({ drug[i].date,"HT Drug [" + to_string(drugLut[drug[i].val1]) + "]" });
				}
			}

			// Read Codes
			for (int sid : rcSignalIds) {
				SDateVal *signal = (SDateVal *)rep.get(pid, sid, len);
				for (int i = 0; i < len; i++) {
					if (htLut[(int)signal[i].val]) {
						data.push_back({ signal[i].date, 3 });
						data_s.push_back({ signal[i].date,"HT ReadCode" });
					}

					if (chfLut[(int)signal[i].val]) {
						data.push_back({ signal[i].date, 4 });
						data_s.push_back({ signal[i].date,"CHF ReadCode" });
					}

					if (miLut[(int)signal[i].val]) {
						data.push_back({ signal[i].date, 5 });
						data_s.push_back({ signal[i].date,"MI ReadCode" });
					}

					if (afLut[(int)signal[i].val]) {
						data.push_back({ signal[i].date, 6 });
						data_s.push_back({ signal[i].date,"AF ReadCode" });
					}
				}
			}

			// Diabetes
			SDateRangeVal *dm = (SDateRangeVal *)rep.get(pid, dmRegId, len);
			for (int i = 0; i < len; i++) {
				if (dm[i].val == 2) {
					data.push_back({ dm[i].date_start,7 });
					data_s.push_back({ dm[i].date_start, "DM" });
				}
			}

			// Sort and analyze
			stable_sort(data.begin(), data.end(), [](const pair<int, int> &v1, const pair<int, int> &v2) {return (v1.first < v2.first); });

			int bpStatus = -1;
			vector<int> bpStatusVec;
			int lastBP = -1;
			int lastDrugDays = -1;
			int chfStatus = 0, miStatus = 0, afStatus = 0, dmStatus = 0;

			int drugs_gap = 90; // Gap from drugs to following indication

			for (auto& rec : data) {
				int date = rec.first;
				int days = med_time_converter.convert_date(MedTime::Days, date);
				int info = rec.second;

				int bpStatusToPush = -1;
				// Background : CHF/MI/AF/DM
				if (info == 4) 
					chfStatus = 1;
				else if (info == 5)
					miStatus = 1;
				else if (info == 6)
					afStatus = 1;
				else if (info == 7)
					dmStatus = 1;
				else { // HT Indications 
					if (bpStatus <= 0) { // Non HyperTensinve (or no info yet)
						if (info == 0) { // Normal BP , still non hypertensive
							lastBP = 0;
							bpStatus = 0;
						}
						else if (info == 1) { // High BP, move to HT given previous indication
							if (lastBP == 1 || (lastDrugDays != -1 && days - lastDrugDays < drugs_gap))
								bpStatus = 2;
							lastBP = 1;
						}
						else if (info > 20) { // HT Drug, move to unclear (depending on background)
							// build drug-specific look : 1 = inidcative of HT. 2 = indicative of HT unless CHF. 3 = indicative of HT unless diabetes. 4 = indicative of HT unless CHF/MI/AF.
							if (info == 21 || (info == 22 && !chfStatus) || (info == 23 && !dmStatus) || (info == 24 && !chfStatus && !miStatus && !afStatus)) {
								bpStatus = 1;
								lastDrugDays = days;
							}
						}
						else if (info == 3) { // Read Code. if last bp is normal, mark as unclear, otherwise, mark as HT
							if (lastBP == 0)
								bpStatus = 1;
							else
								bpStatus = 2;
						}
					}
					else if (bpStatus == 1) { // Unclear.
						if (info == 0)  // Normal BP, still unclear
							lastBP = 0;
						else if (info == 1) { // High BP. move to HT if previous BP was also high
							if (lastBP == 1)
								bpStatus = 2;
							lastBP = 1;
						}
						else if (info > 20) { // HT Drug. move to HT if last BP was high or HT Drug was taken within the last 6 months
							if (info == 21 || (info == 22 && !chfStatus) || (info == 23 && !dmStatus) || (info == 24 && !chfStatus && !miStatus && !afStatus)) {
								if (lastBP == 1 || (lastDrugDays != -1 && days - lastDrugDays < drugs_gap && days - lastDrugDays > 0))
									bpStatus = 2;
								lastDrugDays = days;
							}
						}
						else if (info == 3) // ReadCode. Move to HT
							bpStatus = 2;
					}
					
					bpStatusToPush = bpStatus;
				}
				bpStatusVec.push_back(bpStatusToPush);
			}

			// Print
			stable_sort(data_s.begin(), data_s.end(), [](const pair<int, string> &v1, const pair<int, string> &v2) {return (v1.first < v2.first); });
			if (data_s.size() == 0)
				stderr_vec[i_thread].push_back( to_string(pid) +  " No Info" );
			else {
				for (unsigned int i = 0; i < data_s.size(); i++)
					stderr_vec[i_thread].push_back( to_string(pid)+" "+to_string(data_s[i].first)+" "+data_s[i].second+" "+to_string(data[i].second)+" "+ 
						(bpStatusVec[i] == -1 ? "no change in BP" : to_string(bpStatusVec[i])) );

				int firstNorm = -1, lastNorm = -1, firstHT = -1;

				int status = 0;
				for (unsigned int i = 0; i < bpStatusVec.size(); i++) {
					if (bpStatusVec[i] == 2) {
						firstHT = data[i].first;
						break;
					}
					else if (bpStatusVec[i] == 0) {
						lastNorm = data[i].first;
						if (firstNorm == -1)
							firstNorm = lastNorm;
					}
				}

				if (lastNorm > 0) {
					if (lastNorm < startDate) startDate = firstNorm;
					stdout_vec[i_thread].push_back( to_string(pid) +"\tHT_Registry\t" +  to_string(startDate)  + "\t" + to_string(lastNorm) +"\t0" );
				}
				if (firstHT > 0) {
					stdout_vec[i_thread].push_back(to_string(pid) + "\tHT_Registry\t"+ to_string(firstHT)+"\t"+to_string(endDate) +"\t1" );
				}


			}
		}

		for (int ithread = 0; ithread < n_threads; ithread++) {
			for (string& line : stderr_vec[ithread])
				cerr << line << "\n";
			for (string& line : stdout_vec[ithread])
				cout << line << "\n";
		}

	}

	return 0;
}

// Build a look up table for HT drugs
void fillLookupTableForHTDrugs(MedDictionary& dict, vector<char>& lut, vector<string>& sets, char val) {

	// convert names to ids
	vector<int> sig_ids;
	for (auto &name : sets) {
		int myid = dict.id(name);
		if (myid > 0)
			sig_ids.push_back(myid);
		else
			fprintf(stderr, "prep_sets_lookup_table() : Found bad name %s :: not found in dictionary()\n", name.c_str());
	}

	for (int j = 0; j<sig_ids.size(); j++) {
		queue<int> q;
		q.push(sig_ids[j]);

		while (q.size() > 0) {
			int s = q.front();
			q.pop();
			lut[s] = val;
			for (auto elem : dict.Set2Members[s])
				if (lut[elem] == 0)
					q.push(elem);

		}

	}
	return;
}

void buildLookupTableForHTDrugs(MedDictionary& dict, vector<char>& lut) {

	int maxId = dict.Id2Name.rbegin()->first;
	lut.assign(maxId + 1, 0);

	// 1 = inidcative of HT. 
	vector<string> sets1 = { "ATC_C08C____","ATC_C07B____","ATC_C07C____","ATC_C07D____","ATC_C07F____","ATC_C07A_G__","ATC_C09B____","ATC_C09D____", "ATC_C02D_A01" };
	fillLookupTableForHTDrugs(dict, lut, sets1, (char) 1);

	// 2 = indicative of HT unless CHF.
	vector<string> sets2 = { "ATC_C03_____"};
	fillLookupTableForHTDrugs(dict, lut, sets2, (char)2); 
		
	// 3 = indicative of HT unless diabetes.
	vector<string> sets3 = { "ATC_C09A____", "ATC_C09C____" };
	fillLookupTableForHTDrugs(dict, lut, sets3, (char)3);

	// 4 = indicative of HT unless CHF / MI / AF.
	vector<string> sets4 = { "ATC_C07A_A__", "ATC_C07A_B__" };
	fillLookupTableForHTDrugs(dict, lut, sets4, (char)4);

}