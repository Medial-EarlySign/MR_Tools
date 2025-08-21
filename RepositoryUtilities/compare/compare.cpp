// Comparison of two MHS repositories, the new one is supposed to be an extension of the old one.

#define _CRT_SECURE_NO_WARNINGS

#include "compare.h"


int main(int argc, char *argv[])
{

	
	allInfo info ;

	// Read running parameters
	if (read_run_params(argc,argv,info) < 0) {
		fprintf(stderr,"Reading running parameters failed\n") ;
		return -1 ;
	}

	// Read repositories
	MedRepository origRep,newRep ;

	if (origRep.read_all(info.origRepName) < 0) {
		fprintf(stderr,"Cannot read all repository %s\n",info.origRepName.c_str()) ;
		return -1 ;
	}

	if (newRep.read_all(info.newRepName) < 0) {
		fprintf(stderr,"Cannot read all repository %s\n",info.newRepName.c_str()) ;
		return -1 ;
	}

	// Examine original repository
	examineOrig(origRep,info) ;

	// Do Comparison
	if (compareRep(origRep,newRep,info) < 0) {
		fprintf(stderr,"Caomparison of repositories failed\n") ;
		return -1 ;
	}

	// Examine new
	newRepTests(newRep,info) ;
}


// Read running parameters
int read_run_params(int argc,char **argv, allInfo& info) {

	po::options_description desc("Program options");
	po::variables_map vm ;

	try {
		desc.add_options()	
			("help", "produce help message")	
			("orig", po::value<string>()->required(), "original repository configuration file")
			("new", po::value<string>()->required(), "new repository configuration file")
			("skip_registry", po::bool_switch()->default_value(false), "skip registry comparison")
			("skip_signals", po::bool_switch()->default_value(false), "skip signals comparison")
			("skip_counts", po::bool_switch()->default_value(false), "skip comparison of monthly counts")
			("report_file", po::value<string>()->required(), "summary report file")
			("log_file", po::value<string>()->required(), "detailed log file")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
            cerr << desc << "\n";
            return 0;

        }
        po::notify(vm);    
	}
	catch(exception& e) {
        cerr << "error: " << e.what() << "; run with --help for usage information\n";
        return -1;
    }
    catch(...) {
        cerr << "Exception of unknown type!\n";
		return -1;
    }

	info.origRepName = vm["orig"].as<string>() ;
	info.newRepName = vm["new"].as<string>() ;
	info.skipRegistry = vm["skip_registry"].as<bool>() ;
	info.skipSignals = vm["skip_signals"].as<bool>() ;
	info.skipCounts = vm["skip_counts"].as<bool>() ;

	string fileName = vm["report_file"].as<string>() ;
	info.reportFile = fopen(fileName.c_str(),"w") ;
	if (info.reportFile == NULL) {
		fprintf(stderr,"Cannot open \'%s\' for writing",fileName.c_str()) ;
		return -1 ;
	}

	fileName = vm["log_file"].as<string>() ;
	info.logFile = fopen(fileName.c_str(),"w") ;
	if (info.logFile == NULL) {
		fprintf(stderr,"Cannot open \'%s\' for writing",fileName.c_str()) ;
		return -1 ;
	}

	return 0 ;
}

// Extract some information from original repository
void examineOrig(MedRepository& rep, allInfo& info) {

	int len ;

	// Maximal Birth year
	info.origMaxByear = -1 ;

	for (unsigned int j=0; j<rep.index.pids.size(); j++) {
		int id = rep.index.pids[j] ;
	
		SVal *_byear = (SVal *) rep.get(id,"BYEAR",len) ;
		int byear = (int) _byear[0].val ;

		if (byear > info.origMaxByear)
			info.origMaxByear = byear ;
	}

	fprintf(stderr,"Max Birth Year in original repository = %d\n",info.origMaxByear) ;

	// Range of CBCs (according to Hemoglobin)
	map<int,int> counts ;
	for (unsigned int j=0; j<rep.index.pids.size(); j++) {
		int id = rep.index.pids[j] ;
		SDateVal *hg = (SDateVal *) rep.get(id,"Hemoglobin",len) ;

		for (int i=0; i<len; i++)
			counts[hg[i].date] ++ ;

	}
	info.origHgFirstDate = 0 ;
	for (auto cnt:counts) {
		if (cnt.second > MIN_HGB_PER_DAY) {
			if (info.origHgFirstDate == 0)
				info.origHgFirstDate = cnt.first ;
			info.origHgLastDate = cnt.first ;
		}
	}

	fprintf(stderr,"Hg Time range in original repository = %d-%d\n",info.origHgFirstDate,info.origHgLastDate) ;
}

// Do Comparison
int compareRep(MedRepository& origRep,MedRepository& newRep, allInfo& info) {

	// List of ids
	compareIdsList(origRep,newRep,info) ;

	// Demographics
	compareDemographics(origRep,newRep,info) ;

	// Registry
	if (! info.skipRegistry)
		compareRegistry(origRep,newRep,info) ;

	// Lab Results
	if (! info.skipSignals)
		compareSignals(origRep,newRep,info) ;
	

	// Counts
	if (! info.skipCounts)
		compareCounts(origRep,newRep,info) ;

	return 0 ;
}

// List of ids
void compareIdsList(MedRepository& origRep,MedRepository& newRep, allInfo& info) {

	int len ;

	// any ids only in original dataset ?
	int countOrig = 0 ;
	for (unsigned int j=0; j<origRep.index.pids.size(); j++) {
		int id = origRep.index.pids[j] ;
		if (! newRep.contains_pid(id)) {
			countOrig ++ ;
			fprintf(info.logFile,"CompareIdList: id %d only in origRep\n",id) ;
		}
	}
	fprintf(info.reportFile,"CompareIdsList: Found %d ids only in original repository\n",countOrig) ;

	// check ids only in new dataset
	vector<int> countNew(3) ;
	for (unsigned int j=0; j<newRep.index.pids.size(); j++) {
		int id = newRep.index.pids[j] ;
		if (! origRep.contains_pid(id))
			countNew[checkNewId(newRep,id,info)] ++ ;
	}
	fprintf(info.reportFile,"CompareIdsList: Found %d ids only in new repository beacuase of age\n",countNew[0]) ;
	fprintf(info.reportFile,"CompareIdsList: Found %d idsonly in new repository because of no Hgb in [%d,%d]\n",countNew[1],info.origHgFirstDate,info.origHgLastDate) ;
	fprintf(info.reportFile,"CompareIdsList: Found %d idsonly in new repository but with Hgb in [%d,%d]\n",countNew[2],info.origHgFirstDate,info.origHgLastDate) ;

	// Create list of common ids
	for (unsigned int j=0; j<newRep.index.pids.size(); j++) {
		int id = newRep.index.pids[j] ;
		if (origRep.contains_pid(id))
			info.commonIds.push_back(id) ;
	}

	// Check division to Train/Test/Internal
	int counter = 0 ;
	for (auto id:info.commonIds) {
		SVal *_origTrain = (SVal *) origRep.get(id,"TRAIN",len) ;
		int origTrain = (int) _origTrain[0].val ;


		SVal *_newTrain = (SVal *) newRep.get(id,"TRAIN",len) ;
		int newTrain = (int) _newTrain[0].val ;

		if (origTrain != newTrain) {
			counter ++ ;
			fprintf(info.logFile,"CompareIdsList: id %d changed TrainStatus from %d to %d\n",id,origTrain,newTrain) ;
		}
	}
	fprintf(info.reportFile,"CompareIdsList : Found %d contradiction in TrainStatus\n",counter) ;
}

// Demographics
void compareDemographics(MedRepository& origRep,MedRepository& newRep, allInfo& info) {

	int len ;

	// Birth year
	int counter = 0 ;
	for (auto id:info.commonIds) {
		SVal *_origByear = (SVal *) origRep.get(id,"BYEAR",len) ;
		int origByear = (int) _origByear[0].val ;


		SVal *_newByear = (SVal *) newRep.get(id,"BYEAR",len) ;
		int newByear = (int) _newByear[0].val ;

		if (origByear != newByear) {
			counter ++ ;
			fprintf(info.logFile,"CompareDemographics: id %d changed BYear from %d to %d\n",id,origByear,newByear) ;
		}
	}
	fprintf(info.reportFile,"CompareDemographics : Found %d contradiction in BYear\n",counter) ;

	// Gender
	counter = 0 ;
	for (auto id:info.commonIds) {
		SVal *_origGender = (SVal *) origRep.get(id,"GENDER",len) ;
		int origGender = (int) _origGender[0].val ;


		SVal *_newGender = (SVal *) newRep.get(id,"GENDER",len) ;
		int newGender = (int) _newGender[0].val ;

		if (origGender != newGender) {
			counter ++ ;
			fprintf(info.logFile,"CompareDemographics: id %d changed Gender from %d to %d\n",id,origGender,newGender) ;
		}
	}
	fprintf(info.reportFile,"CompareDemographics : Found %d contradiction in Gender\n",counter) ;

	// Censor
	vector<int> counters(2) ;
	for (auto id:info.commonIds) {
		SDateVal *origCensor = (SDateVal *) origRep.get(id,"Censor",len) ;
		int origCensorDate = origCensor[0].date ;

		SDateVal *newCensor = (SDateVal *) newRep.get(id,"Censor",len) ;
		int newCensorDate = newCensor[0].date ;

		if (newCensorDate < origCensorDate) {
			counters[0] ++ ;
			fprintf(info.logFile,"CompareDemographics : id %d censoring is earlier in newRep [%d] than in origRep [%d]\n",id,newCensorDate,origCensorDate) ;
		} else if (origCensor[0].val == 2008 && (newCensorDate > origCensorDate || newCensor[0].val != 2008)) {
			counters[1] ++ ;
			fprintf(info.logFile,"CompareDemographics : id %d died in %d in origRep but has [%d:%d] in newRep\n",id,origCensorDate,newCensorDate, (int) newCensor[0].val) ;
		}
	}
	fprintf(info.reportFile,"CompareDemographics : Found %d contradiction in Censoring\n",counters[0]) ;
	fprintf(info.reportFile,"CompareDemographics : Found %d revivals in Censoring\n",counters[1]) ;
}

// Registry
void compareRegistry(MedRepository& origRep,MedRepository& newRep, allInfo& info) {

	int len ;

	// Time range of registry in origRep
	int minDate = 99999999 ;
	int maxDate = -1 ;

	for (unsigned int j=0; j<origRep.index.pids.size(); j++) {
		int id = origRep.index.pids[j] ; 

		SDateVal *cancerLocation = (SDateVal *) origRep.get(id,"Cancer_Location",len) ;
		for (int i=0; i<len; i++) {
			if (cancerLocation[i].date > maxDate)
				maxDate = cancerLocation[i].date ;
			if (cancerLocation[i].date < minDate)
				minDate = cancerLocation[i].date ;
		}
	}

	fprintf(stderr,"Original registry cover: %d - %d\n",minDate,maxDate) ;

	map<string,int> diffCounter ;
	char buffer[32] ;
	int locationMatches = 0, stageMatches = 0 ;

	for (auto id:info.commonIds) {
		map<int,unordered_set<string>> origLocations,newLocations ;
		map<int,unordered_set<int>> origStages,newStages ;

		SDateVal *cancerLocation = (SDateVal *) origRep.get(id,"Cancer_Location",len) ;
		for (int i=0; i<len; i++) {
//			fprintf(info.logFile,"OrigLocation %d %d %d %s\n",id,cancerLocation[i].date,(int)cancerLocation[i].val,origRep.dict.name((int) cancerLocation[i].val).c_str()) ;
			string location = origRep.dict.name((int)cancerLocation[i].val);
			boost::algorithm::replace_all(location, "_", " ");
			origLocations[cancerLocation[i].date].insert(location) ;
		}

		SDateVal *cancerStage = (SDateVal *) origRep.get(id,"Cancer_Stage",len) ;
		for (int i=0; i<len; i++) {
//			fprintf(info.logFile,"OrigStage %d %d %d\n",id,cancerStage[i].date,(int)cancerStage[i].val) ;
			origStages[cancerStage[i].date].insert((int) cancerStage[i].val) ;	
		}

		cancerLocation = (SDateVal *) newRep.get(id,"Cancer_Location",len) ;
		for (int i=0; i<len; i++) {
//			fprintf(info.logFile,"NewLocation %d %d %d %s\n",id,cancerLocation[i].date,(int)cancerLocation[i].val,newRep.dict.name((int) cancerLocation[i].val).c_str()) ;
			string location = newRep.dict.name((int)cancerLocation[i].val);
			boost::algorithm::replace_all(location, "_", " ");
			newLocations[cancerLocation[i].date].insert(location) ;
		}

		cancerStage = (SDateVal *) newRep.get(id,"Cancer_Stage",len) ;
		for (int i=0; i<len; i++) {
//			fprintf(info.logFile,"NewStage %d %d %d\n",id,cancerStage[i].date,(int)cancerStage[i].val) ;
			newStages[cancerStage[i].date].insert((int) cancerStage[i].val) ;	
		}

		// Cancer Location of original repository
		for (auto incident:origLocations) {
			if (newLocations.find(incident.first) == newLocations.end()) {
				fprintf(info.logFile,"CompareRegistry: Cannot find any location at newRep for %d/%d\n",id,incident.first) ;
				diffCounter["MissingLocationAtNew"] ++ ;
				string name = "MissingLocationAtNew" ;
				for (auto location:incident.second)
					name += ":" + location ;
				diffCounter[name] ++ ;
			} else {
				for (auto location:incident.second) {
					if (newLocations[incident.first].find(location) == newLocations[incident.first].end()) {
						fprintf(info.logFile,"CompareRegistry: Cannot find %s at newRep for %d/%d\n",location.c_str(),id,incident.first) ;
						diffCounter["LocationMismatch"] ++ ;
						diffCounter["LocationMismatch:"+location] ++ ;
					} else 
						locationMatches ++ ;
				}
			} 
		}

		// Cancer Stages of original repository
		for (auto incident:origStages) {
			if (newStages.find(incident.first) == newStages.end()) {
				fprintf(info.logFile,"CompareRegistry: Cannot find any stage at newRep for %d/%d\n",id,incident.first) ;
				diffCounter["MissingStageAtNew"] ++ ;
			} else {
				for (auto stage:incident.second) {
					if (newStages[incident.first].find(stage) == newStages[incident.first].end()) {
						fprintf(info.logFile,"CompareRegistry: Cannot find stage %d at newRep for %d/%d\n",stage,id,incident.first) ;
						diffCounter["StageMismatch"] ++ ;
						sprintf(buffer,"StageMismatch:%d",stage) ;
						diffCounter[buffer] ++ ;
					} else
						stageMatches ++ ;
				} 
			}
		}

		// Cancer Location of new repository
		for (auto incident:newLocations) {
			if (incident.first < minDate || incident.first> maxDate)
				continue ;

			if (origLocations.find(incident.first) == origLocations.end()) {
				fprintf(info.logFile,"CompareRegistry: Cannot find any location at origRep for %d/%d\n",id,incident.first) ;
				diffCounter["MissingLocationAtOrig"] ++ ;
				string name = "MissingLocationAtOrig" ;
				for (auto location:incident.second)
					name += ":" + location;
				diffCounter[name] ++ ;
			} 
		}

		// Cancer Stages of original repository
		for (auto incident:newStages) {
			if (incident.first < minDate || incident.first> maxDate)
				continue ;

			if (origStages.find(incident.first) == origStages.end()) {
				fprintf(info.logFile,"CompareRegistry: Cannot find any stage at origRep for %d/%d\n",id,incident.first) ;
				diffCounter["MissingStageAtOrig"] ++ ;
			} 
		}
	}

	// Print
	for (auto cnt:diffCounter) 
		fprintf(info.reportFile,"CompareRegistry: Count of %s : %d  [Location Matches %d : Stage Matches %d]\n",cnt.first.c_str(),cnt.second,locationMatches,stageMatches) ;

	return ;
}

// Signals
void compareSignals(MedRepository& origRep,MedRepository& newRep, allInfo& info) {

	int len ;

	// Full check
	medCounter counter ;
	map<string,medCounter> counterBySignal ;
	map<int,medCounter> counterByYear ;

	// Lab Signals
	for (auto id:info.commonIds) {
		for (auto signalName:signalsToCheck) {

			map<int,pair<float,float> > allMeasures ;
			
			SDateVal *signal = (SDateVal *) origRep.get(id,signalName,len) ;
			for (int i=0; i<len; i++)
				allMeasures[signal[i].date] = pair<float,float>(signal[i].val,(float) MISSING_VAL) ;

			signal = (SDateVal *) newRep.get(id,signalName,len) ;
			for (int i=0; i<len; i++) {
				int date = signal[i].date ;
				if (date >= info.origHgFirstDate && date <= info.origHgLastDate) {
					if (allMeasures.find(date) == allMeasures.end())
						allMeasures[date] = pair<float,float>((float) MISSING_VAL,signal[i].val) ;
					else
						allMeasures[date].second = signal[i].val ;
				}
			}

			for (auto measure:allMeasures) {
				int year = measure.first/10000 ;
				counter.total ++ ;
				counterBySignal[signalName].total ++ ;
				counterByYear[year].total ++ ;

				if (fabs(measure.second.first-measure.second.second)>EPSILON) {
					fprintf(info.logFile,"CompareSignals: Contradiction at %d/%s/%d : %f || %f\n",id,signalName,measure.first,measure.second.first,measure.second.second) ;

					string type1="NonZero",type2="NonZero," ;
					if (fabs(measure.second.first)<EPSILON)
						type1 = "Zero" ;
					else if (fabs(measure.second.first - MISSING_VAL)<EPSILON)
						type1 = "Missing" ;

					if (fabs(measure.second.second)<EPSILON)
						type2 = "Zero" ;
					else if (fabs(measure.second.second - MISSING_VAL)<EPSILON)
						type2 = "Missing" ;

					pair<string,string> type(type1,type2) ;
					counter.counts[type] ++ ;
					counterBySignal[signalName].counts[type] ++ ;
					counterByYear[year].counts[type] ++ ;
				}
			}
		}
	}

	for (auto cnt:counter.counts)
		fprintf(info.reportFile,"CompareSignals: Difference %s -> %s : # = %lld %% = %.1f\n",cnt.first.first.c_str(), cnt.first.second.c_str(),cnt.second,(100.0*cnt.second)/counter.total) ;

	for (auto sig:counterBySignal) {
		for (auto cnt:sig.second.counts)
			fprintf(info.reportFile,"CompareSignals: Signal %s Difference %s -> %s : # = %lld %% = %.1f\n",sig.first.c_str(),cnt.first.first.c_str(), cnt.first.second.c_str(),cnt.second,(100.0*cnt.second)/sig.second.total) ;
	}

	for (auto year:counterByYear) {
		for (auto cnt:year.second.counts)
			fprintf(info.reportFile,"CompareSignals: Year %d Difference %s -> %s : # = %lld %% = %.1f\n",year.first,cnt.first.first.c_str(), cnt.first.second.c_str(),cnt.second,(100.0*cnt.second)/year.second.total) ;
	}

	// Smoking - detailed check
	int totalCount = 0 ;
	map<pair<int,int>,int> diffCount ;

	for (auto id:info.commonIds) {

		map<int,pair<int,int> > allMeasures ;
			
		SDateVal *signal = (SDateVal *) origRep.get(id,"SMOKING",len) ;
		for (int i=0; i<len; i++)
			allMeasures[signal[i].date] = pair<int,int>((int)signal[i].val,-1) ;

		signal = (SDateVal *) newRep.get(id,"SMOKING",len) ;
		for (int i=0; i<len; i++) {
			int date = signal[i].date ;
			if (date >= info.origHgFirstDate && date <= info.origHgLastDate) {
				if (allMeasures.find(date) == allMeasures.end())
					allMeasures[date] = pair<int,int>(-1,(int) signal[i].val) ;
				else
					allMeasures[date].second = (int) signal[i].val ;
			}
		}

		for (auto measure:allMeasures) {
			totalCount ++ ;

			if (measure.second.first != measure.second.second) {
				diffCount[pair<int,int>(measure.second.first,measure.second.second)] ++ ;				
				fprintf(info.logFile,"CompareSignals: smoking Contradiction at %d/%d : %d || %d\n",id,measure.first,measure.second.first,measure.second.second) ;
			}
		}
	}

	for (auto cnt:diffCount)
		fprintf(info.reportFile,"CompareSignals: Smoking %d -> %d : # = %d %% = %.1f\n",cnt.first.first,cnt.first.second,cnt.second,(100.0*cnt.second)/totalCount) ;


}

// Counts
void compareCounts(MedRepository& origRep,MedRepository& newRep, allInfo& info) {

	int len ;

	vector<string> signals ;
	signals.push_back("Hemoglobin") ;
	signals.push_back("Cancer_Location") ;

	for (auto signal:signals) {
		map<int,pair<int,int> > counter ;
		for (unsigned int j=0; j<origRep.index.pids.size(); j++) {
			int id = origRep.index.pids[j] ;

			SDateVal *sig = (SDateVal *) origRep.get(id,signal,len) ;
			for (int i=0; i<len; i++) {
				int month = sig[i].date/100 ;
				counter[month].first ++ ;
			}
		}

		for (unsigned int j=0; j<newRep.index.pids.size(); j++) {
			int id = newRep.index.pids[j] ;

			SDateVal *sig = (SDateVal *) newRep.get(id,signal,len) ;
			for (int i=0; i<len; i++) {
				int month = sig[i].date/100 ;
				counter[month].second ++ ;
			}
		}

		for (auto cnt:counter)  {
			if (cnt.second.first)
				fprintf(info.reportFile,"CompareCounts: %s at %d : %d || %d || %.2f\n",signal.c_str(),cnt.first,cnt.second.first,cnt.second.second,(1.0*cnt.second.second)/cnt.second.first) ;
			else
				fprintf(info.reportFile,"CompareCounts: %s at %d : %d || %d || --\n",signal.c_str(),cnt.first,cnt.second.first,cnt.second.second) ;
		}
	}
}


// Check if a new id should have appeared. 0 : too young ; 1 : No Hgb in period ; 2 : Should appear
int checkNewId(MedRepository& rep, int id, allInfo& info) {

	int len ;

	// too young ?
	SVal *byear = (SVal *) rep.get(id,"BYEAR",len) ;
	if ((int)(byear[0].val) > info.origMaxByear)
		return 0 ;

	// Any Hemoglobin in origRep period
	int withHgb = 1 ;
	STimeVal *hg = (STimeVal *) rep.get(id,"Hemoglobin",len) ;
	for (int i=0; i<len; i++) {
		if (hg[i].time >= info.origHgFirstDate && hg[i].time <= info.origHgLastDate) {
			withHgb = 2;
			break ;
		}
	}

	return withHgb ;
}

// Check phenomenon in new repository
void newRepTests(MedRepository& rep, allInfo& info) {

	int len ;
	// Check 0-panels
	long long nZeroPanels = 0 ;
	long long nPanels = 0 ;

	for (unsigned int j=0; j<rep.index.pids.size(); j++) {
		int id = rep.index.pids[j] ;

		map <int,pair<int,int> > counter ;
		for (int iSignal=0; iSignal < 20; iSignal ++) {
			SDateVal *sig = (SDateVal *) rep.get(id,signalsToCheck[iSignal],len) ;
			for (int i=0; i<len; i++) {
				if (sig[i].val > 0)
					counter[sig[i].date].first ++ ;
				else if (sig[i].val == 0)
					counter[sig[i].date].second ++ ;
			}
		}

		for (auto cnt:counter) {
			nPanels ++ ;
			if (cnt.second.second > MAX_ZEROS_IN_PANEL) {
				fprintf(info.logFile,"CheckZeroPanels: %d at %d : [Zero/NonZero] = %d %d\n",id,cnt.first,cnt.second.second,cnt.second.first) ;
				nZeroPanels ++ ;
			}
		}
	}

	fprintf(info.reportFile,"CheckZeroPanels: # of panels with more than %d zeros = %lld of %lld panels %% = %.2f\n",MAX_ZEROS_IN_PANEL,nZeroPanels,nPanels,(100.0*nZeroPanels)/nPanels) ;

	// Count Train/Internal/External + Check for registry on external validation
	int nExternalInRegistry = 0;
	int counters[3];
	memset(counters, 0, sizeof(counters));

	for (unsigned int j = 0; j < rep.index.pids.size(); j++) {
		int id = rep.index.pids[j];

		SVal *train = (SVal *)rep.get(id, "TRAIN", len);
		assert(len == 1);

		counters[(int)train[0].val - 1] ++;
		if (train[0].val == 3) {
			SDateVal *cancerLocation = (SDateVal *)rep.get(id, "Cancer_Location", len);
			if (len > 0) {
				nExternalInRegistry++;
				for (int i = 0; i < len; i++)
					fprintf(info.logFile, "CheckExternal: id %d in external validation had cancer registry entry %d/%d\n", id, cancerLocation[i].date, (int)cancerLocation[i].val);
			}
		}
	}


	int total = counters[0] + counters[1] + counters[2];
	fprintf(info.reportFile, "CheckExternal: Train (1) : # = %d %% = %.1f\n", counters[0], (100.0*counters[0]) / total);
	fprintf(info.reportFile, "CheckExternal:Internal (2) : # = %d %% = %.1f\n", counters[1], (100.0*counters[1]) / total);
	fprintf(info.reportFile, "CheckExternal :External (3) : # = %d %% = %.1f\n", counters[2], (100.0*counters[2]) / total);
	fprintf(info.reportFile, "CheckExternal: Found %d external validation ids with cancer registry entries\n", nExternalInRegistry);
}