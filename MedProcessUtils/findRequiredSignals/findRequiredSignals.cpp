#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "findRequiredSignals.h"

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	// Initialize
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return 0; //print exit

	// get vector of performance measurements 
	MedBootstrapResult bootstrapper;
	IterativeFeatureSelector dummyIterativeFtrSelector; // Used only for bootstrap init
	
	// init bootstrapper
	string bootstrap_init = args.bootstrap_params;
	boost::replace_all(bootstrap_init, "/", ";");
	boost::replace_all(bootstrap_init, ":", "=");
	bootstrapper.bootstrap_params.init_from_string(bootstrap_init);
	string lower_bootstrap_init = boost::to_lower_copy(bootstrap_init);
	if (!boost::icontains(bootstrap_init, "loopcnt"))
		bootstrapper.bootstrap_params.loopCnt = 1;
	bootstrapper.bootstrap_params.sample_ratio = 1;

	dummyIterativeFtrSelector.init_bootstrap_cohort(bootstrapper, args.cohort_params);
	dummyIterativeFtrSelector.init_bootstrap_params(bootstrapper, args.msr_params);
	//

	MedSamples samples;
	samples.read_from_file(args.samples_file);
	MedModel model, bootstrapModel;
	model.read_from_file(args.model_file);

	MedPidRepository rep;
	vector<string> sig_names, sig_names_bootstrap, total_req_signals;

	vector<int> ids;
	model.get_required_signal_names(sig_names);
	unordered_set<string> sig_names_set(sig_names.begin(), sig_names.end());
	total_req_signals = sig_names;

	// init bootstrap model
	if (args.bootstrap_json != "")
	{
		bootstrapModel.init_from_json_file(args.bootstrap_json);
	}

	bootstrapModel.add_age();
	bootstrapModel.add_gender();

	samples.get_ids(ids);
	// get also bootstrap required signals
	bootstrapModel.get_required_signal_names(sig_names_bootstrap);
	for (string &req_sig_bs : sig_names_bootstrap)
	{
		if (sig_names_set.find(req_sig_bs) == sig_names_set.end())
			total_req_signals.push_back(req_sig_bs);
	}

	if (rep.read_all(args.rep_file, ids, total_req_signals) < 0)
	{
		MERR(" read_all_input_files(): ERROR could not read repository %s\n", args.rep_file.c_str());
		throw exception();
	}

	// Prepare bootstarp features matrix
	bootstrapModel.apply(rep, samples, MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_GENERATORS);

	// Filter features Matrix according to cohort extracy labels and pids
	vector<int> pids;
	vector<float> labels;
	map<string, vector<float>> additional_info;
	filterFeatureMatrix(bootstrapModel.features, args.cohort_params, bootstrapper.bootstrap_params, labels, pids, additional_info);
	int n_pids = pids.size();

	// update samples to relvant samples according to cohort filtering
	samples.import_from_sample_vec(bootstrapModel.features.samples);

	// Get Required Signals
	unordered_set<string> required;
	if (args.req_signals.size() > 0) {
		for (string req : args.req_signals)
			if (sig_names_set.find(req) == sig_names_set.end())
			{
				MWARN("required signal %s isn't used in the model \n", req.c_str());
			}
			else
				required.insert(req);
	}
	
	// if required ratio exists, run full model for reference.
	float requiredAbsPerf;
	if (args.requiredRatioPerf > 0)
	{
		model.apply(rep, samples);
		for (size_t ind = 0; ind < model.features.samples.size(); ind++)
		{
			bootstrapModel.features.samples[ind].prediction[0] = model.features.samples[ind].prediction[0];
		}
		bootstrapper.bootstrap(bootstrapModel.features);
		MLOG("Reference Run has perfomance of %f \n", bootstrapper.bootstrap_results["bs"][dummyIterativeFtrSelector.measurement_name]);
		requiredAbsPerf = bootstrapper.bootstrap_results["bs"][dummyIterativeFtrSelector.measurement_name] * args.requiredRatioPerf;
	}
	else
		requiredAbsPerf = args.requiredAbsPerf;

	// Write header + required performance  to file
	ofstream of(args.outFile);
	if (!of.is_open())
		MTHROW_AND_ERR("Cannot open %s for writing\n", args.outFile.c_str());
	of << "Required Performance\t" << requiredAbsPerf << endl;
	of << "Signals" << "\t" << "Performance" <<  "% samples containing the comb." << endl;

	bool loop_done = false;
	int curr_num_signals = 0;

	vector<pair<float, unordered_set<string>>> performanceSignals; // contains signals sets and their perfomance
	
	// init performanceSignals all the signals (required signals are removed, they are not counted).
	vector<string> signalsSorted, prevSignalsSorted;
	
	for (string sig_name : sig_names)
	{
		if ((required.find(sig_name) == required.end()) && (args.delete_signals.find(sig_name) == args.delete_signals.end()))
		{
			unordered_set<string> tmp = {};
			tmp.insert(sig_name);
			signalsSorted.push_back(sig_name);
			performanceSignals.push_back(make_pair((float)0 , tmp));
		}
	}
	
	size_t maximalNumSignals = min(args.maximalNumSignals, signalsSorted.size());
	vector<RepProcessor*> origRepProcessors(model.rep_processors);
	unordered_set<string> best_comb;
	MedTimer timer;
	vector<unordered_set<string>> acceptableCombinations;

	while (!loop_done)
	{
		curr_num_signals++;

		int num_signals_to_choose = min(find_num_signals(args.numTestsPerIter, curr_num_signals), (int)signalsSorted.size());
		MLOG("current signals to select is %d, total number of signals to select from is %d, maximum number of evaluations allowed %d chosen number of signals is %d \n",
			curr_num_signals, (int)performanceSignals.size(), args.numTestsPerIter, num_signals_to_choose);

		// pick first num_signals_to_choose elements
		prevSignalsSorted = signalsSorted;
		signalsSorted.erase(signalsSorted.begin() + num_signals_to_choose, signalsSorted.end());
	
		// create permutations:
		vector<unordered_set<string>> combsOut;
		combinations(signalsSorted, curr_num_signals, combsOut);

		// initialize performance vec
		performanceSignals.clear();
		
		// run over permutations
		int cntr = 0;
		
		unordered_map <string, vector<float>> ci_dict;
		unordered_map <string, int> cnt_dict;
		
		for (unordered_set<string> comb : combsOut)
		{
			timer.start();
			cntr++;

			// Check whether current combination is a superset of a previous accepted combinations
			if (args.skip_supersets)
			{
				unordered_set<string> acceptableCombOut;
				if (combinationsIsSupersetOfAcceptableSet(acceptableCombinations, comb, acceptableCombOut))
				{
					MLOG("SKIPPING - Signal Combination: %s, is a superset of acceptable combination %s - \n", set2string(comb).c_str(), set2string(acceptableCombOut).c_str());
					continue;
				}
			}
			
			// get Signals to delete and take from the current combination
			unordered_set<string> sigsToDelete(sig_names_set);
			unordered_set<string> sigsToTake = {};

			getSigsFromCombination(comb, required, sig_names, sigsToDelete, sigsToTake);


			// generate Deleting rep processors
			vector<RepProcessor*> cleaningRepProcess;
			for (auto & sig : sigsToDelete)
			{
				string params;
				params = string("delete_sig=1;signal=") + sig;
				RepProcessor* deleteRepProcess = RepProcessor::make_processor("history_limit",params);
				cleaningRepProcess.push_back(deleteRepProcess);
			}

			model.rep_processors = cleaningRepProcess;
			model.rep_processors.insert(model.rep_processors.end(), origRepProcessors.begin(), origRepProcessors.end());

			model.apply(rep, samples);
			
			// Performance
			vector<float> preds(model.features.samples.size());
			for (size_t ind = 0; ind < model.features.samples.size(); ind++)
			{
				preds[ind] = model.features.samples[ind].prediction[0];
				bootstrapModel.features.samples[ind].prediction[0] = model.features.samples[ind].prediction[0];
			}

			// Run Bootstap performance
			vector<MeasurementFunctions> meas_function = { bootstrapper.bootstrap_params.measurements_with_params[0].first };
			vector<Measurement_Params *> function_params = { bootstrapper.bootstrap_params.measurements_with_params[0].second };
			vector<int> filter_indexes;
			int warn_cnt = 0;
		
			vector<int> preds_order;
			map<string, float> res = booststrap_analyze_cohort(preds, preds_order, labels, pids, bootstrapper.bootstrap_params.sample_ratio, bootstrapper.bootstrap_params.sample_per_pid, bootstrapper.bootstrap_params.loopCnt,
				meas_function, function_params, NULL, additional_info, labels, pids, NULL, filter_indexes, filter_range_params, NULL, warn_cnt, "bootstrap");

			performanceSignals.push_back({ res[dummyIterativeFtrSelector.measurement_name], comb });
			MLOG("Signal Combination: %s, has %s: %f. Required performance is %f \n", set2string(comb).c_str(), dummyIterativeFtrSelector.measurement_name.c_str(), res[dummyIterativeFtrSelector.measurement_name], requiredAbsPerf);
			ci_dict[set2string(comb)].push_back(res["AUC_CI.Lower.95"]);
			ci_dict[set2string(comb)].push_back(res["AUC_CI.Upper.95"]);
			cnt_dict[set2string(comb)] = countEligible(pids, sigsToTake, rep);
			
			if (res[dummyIterativeFtrSelector.measurement_name] > requiredAbsPerf)
				acceptableCombinations.push_back(comb);

			// delete preprocessors
			for(int k = 0 ; k < cleaningRepProcess.size(); k++)
			{
				delete(model.rep_processors[k]);
				model.rep_processors[k] = NULL;
			}
			timer.take_curr_time();
			double diff = timer.diff_sec() / 60.0;
			
			MLOG("Total time of a single test is %f minutes. %d done out of %d. Estimated remaining time for current setting: %f minutes\n", diff, cntr, combsOut.size(), (combsOut.size() - cntr)*diff);
		}

		// rank signals according to previous run.
		getSortedSignals(performanceSignals, prevSignalsSorted, signalsSorted);
		float currBestPerform = performanceSignals[0].first;

		writeResultsToFile(of, sig_names, performanceSignals, args.evaluationsToPrint, requiredAbsPerf, ci_dict, cnt_dict, n_pids);
		loop_done = calcStoppingCriteria(requiredAbsPerf, maximalNumSignals, args.numIterationsToContinue, currBestPerform, curr_num_signals);
	}	
	of.close();
	return 0;
}
int nchoosek(int n, int k)
{
	if (k == 0)
		return 1;
	return (n * nchoosek(n - 1, k - 1)) / k;
}


int find_num_signals(int num_required_iterations, int curr_num_signals)
{
	int num_signals_to_take = curr_num_signals;

	while (nchoosek(num_signals_to_take + 1, curr_num_signals) < num_required_iterations)
		num_signals_to_take++;

	return num_signals_to_take;
}

void combinations_recursive(vector<string> &elems, unsigned long req_len,
	vector<unsigned long> &pos, unsigned long depth,
	unsigned long margin, vector<unordered_set<string>> &out)
{
	// Have we selected the number of required elements?
	if (depth >= req_len) {
		unordered_set<string> tmpVec;
		for (unsigned long ii = 0; ii < pos.size(); ++ii)
			tmpVec.insert(elems[pos[ii]]);
		out.push_back(tmpVec);
		return;
	}

	// Are there enough remaining elements to be selected?
	// This test isn't required for the function to be correct, but
	// it can save a good amount of futile function calls.
	if ((elems.size() - margin) < (req_len - depth))
		return;

	// Try to select new elements to the right of the last selected one.
	for (unsigned long ii = margin; ii < elems.size(); ++ii) {
		pos[depth] = ii;
		combinations_recursive(elems, req_len, pos, depth + 1, ii + 1, out);
	}
	return;
}

void combinations(vector<string>&elems, unsigned long req_len, vector<unordered_set<string>> &out)
{
	assert(req_len > 0 && req_len <= elems.size());
	vector<unsigned long> positions(req_len, 0);
	combinations_recursive(elems, req_len, positions, 0, 0, out);
}

bool sortbyfirstinv(const pair<float, unordered_set<string>> &a, const pair<float, unordered_set<string>> &b)
{
	return (a.first > b.first);
}

void getSortedSignals(vector<pair<float, unordered_set<string>>> &performanceSignals, vector<string> &prevSignalsSorted, vector<string> &signalsSorted)
{
	sort(performanceSignals.begin(), performanceSignals.end(), sortbyfirstinv);

	unordered_set<string> insertedSignals = {};
	signalsSorted = {};
	for (pair<float, unordered_set<string>>& elem : performanceSignals)
	{
		for (string currSig : elem.second)
		{
			if (insertedSignals.find(currSig) == insertedSignals.end())
			{
				insertedSignals.insert(currSig);
				signalsSorted.push_back(currSig);
			}
		}
	}
	// fill by previous signal sorted
	for (string &currSig : prevSignalsSorted)
	{
		if (signalsSorted.size() == prevSignalsSorted.size())
			break;
		if (insertedSignals.find(currSig) == insertedSignals.end())
		{
			insertedSignals.insert(currSig);
			signalsSorted.push_back(currSig);
		}

	}
}

string set2string(unordered_set<string> stringSet)
{
	vector<string> stringVec(stringSet.begin(), stringSet.end());
	sort(stringVec.begin(), stringVec.end());
	string out;
	for (string str : stringVec)
	{
		out += str + ",";	
	}
	out.erase(out.end() - 1, out.end());
	return out;
}

void writeResultsToFile(ofstream &out_file, vector<string> &sig_names, vector<pair<float, unordered_set<string>>> &performanceSignals, int evaluationsToPrint, float requiredAbsPerf, unordered_map<string, vector<float>> &ci_dict, unordered_map<string, int> &cnt_dict, int n_pids )
{
	// Print only combinations that pass the performance
	if (evaluationsToPrint == 0)
	{
		for (auto & sig : performanceSignals)
		{	
			if (sig.first >= requiredAbsPerf)
				out_file << set2string(sig.second) << "\t" << sig.first << "\t" << "[" << ci_dict[set2string(sig.second)][0] << "," << ci_dict[set2string(sig.second)][1] << "]" << "\t" << float(cnt_dict[set2string(sig.second)])/float(n_pids) << endl;
			else
				// performanceSignals are ordered byt performance, hence we can break 
				break;
		}
	}
	else
	{
		int sigCntr = 0;
		for (auto & sig : performanceSignals)
		{
			sigCntr++;
			//out_file << set2string(sig.second) << "\t" << sig.first << endl;
			out_file << set2string(sig.second) << "\t" << sig.first << "\t" << "[" << ci_dict[set2string(sig.second)][0] << "," << ci_dict[set2string(sig.second)][1] << "]" << "\t" << float(cnt_dict[set2string(sig.second)]) / float(n_pids) << endl;
			if ((evaluationsToPrint != -1) && (sigCntr == evaluationsToPrint))
				break;
		}
	}

}

void getSigsFromCombination(unordered_set<string> &comb, unordered_set<string> &required, vector<string> &sig_names, unordered_set<string> &sigsToDelete, unordered_set<string> &sigsToTake)
{
	for (auto sig : comb)
	{
		sigsToDelete.erase(sig);
		sigsToTake.insert(sig);
	}
	for (auto & req_sig : required)
	{
		sigsToDelete.erase(req_sig);
		sigsToTake.insert(req_sig);
	}
}

// Check whether stopping criteria are met
bool calcStoppingCriteria(float requiredAbsPerf, size_t maximalNumSignals, int numIterationsToContinue, float currBestPerform, int numSignals)
{
	static int cntrFromPassingReqPerformance = -1;
	if (cntrFromPassingReqPerformance > 0) {
		cntrFromPassingReqPerformance--;
	}
	if (cntrFromPassingReqPerformance == -1) {
		// If performance is not met yey. check criteria
		if (currBestPerform >= requiredAbsPerf) {
			cntrFromPassingReqPerformance = numIterationsToContinue;
		}
	}

	if ((cntrFromPassingReqPerformance == 0) || (numSignals == maximalNumSignals)) {
		return true;
	}
	return false;
}

void filterFeatureMatrix(MedFeatures &matrix, string &cohort_params, MedBootstrap &bootstrapper, vector<float> &labels, vector<int> &pids, map<string, vector<float>> &additional_info)
{
	vector<float> preds, labelsOrig;
	vector<int> pidsOrig;

	// Create Dummy predictions (needed for prepare)
	for (MedSample &sample : matrix.samples)
	{
		sample.prediction.push_back(0.0);
	}
	vector<int> preds_order;
	bootstrapper.prepare_bootstrap(matrix, preds, labelsOrig, pidsOrig, additional_info, preds_order);

	vector<int> sel;
	for (int i = 0; i < matrix.samples.size(); ++i)
		if (filter_range_params(additional_info, i, &bootstrapper.filter_cohort["bs"])) {
			sel.push_back(i);
			labels.push_back(labelsOrig[i]);
			pids.push_back(pidsOrig[i]);
		}
			
	medial::process::filter_row_indexes(matrix, sel);
	bootstrapper.filter_cohort.erase("All");
}

bool combinationsIsSupersetOfAcceptableSet(vector<unordered_set<string>> acceptableCombinations, unordered_set<string> &comb, unordered_set<string> & acceptableCombOut)
{
	// Check Whether a combination exits in previous combinations above 
	bool isSubsetOfAcceptableSet = false;
	for (auto acceptableComb : acceptableCombinations)
	{
		isSubsetOfAcceptableSet = true;
		for (string sig : acceptableComb)
		{
			if (comb.find(sig) == comb.end()) {
				isSubsetOfAcceptableSet = false;
				break;
			}
		}
		if (isSubsetOfAcceptableSet)
		{
			acceptableCombOut = acceptableComb;
			break;
		}
	}
	return isSubsetOfAcceptableSet;
}

int countEligible(vector <int> &pids, unordered_set<string> &sigsToTake, MedPidRepository &rep)
{
	UniversalSigVec usv;
	int cnt = 0;
	for (int pid : pids)
	{
		bool allExists = true;
		for (auto &sig : sigsToTake)
		{
			int sid = rep.sigs.sid(sig);
			rep.uget(pid, sid, usv);
			if (usv.len == 0)
			{
				allExists = false;
				break;
			}
		} 
		if (allExists)
			cnt++;
	}
	return cnt;
}