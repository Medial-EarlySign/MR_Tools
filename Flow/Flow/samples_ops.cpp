//
// containing several useful actions needed when working with MedSamples files
//
// -> scan signals distribution before the samples: to help choose only dense enough features
// -> filter and match samples
// -> convert samples to bin
//

#include "Flow.h"
#include "Logger/Logger/Logger.h"
#include "MedUtils/MedUtils/MedUtils.h"
#include "MedFeat/MedFeat/MedOutcome.h"
#include <MedStat/MedStat/MedPerformance.h>
#include <MedProcessTools/MedProcessTools/SampleFilter.h>
#include <MedUtils/MedUtils/MedCohort.h>
#include <MedUtils/MedUtils/MedRegistry.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
#include <boost/algorithm/string/split.hpp>
#include <boost/algorithm/string.hpp>


#include <random>
#include <algorithm>
#include <map>
#include <unordered_set>

using namespace std;
using namespace boost;

//================================================================================================
// Given a sample file and a repository we do the following:
// (1) detect for each id the last date in the samples (if small number of categories, then for each category)
// (2) go over all signals in the repository and for each signal
//     - count how many ids have the signal BEFORE the given date (also by category)
//     - give a score for the difference betweeen categories (if there are any)
//
// Goal is to help choose signals that have enough representation when working on a problem
//
int flow_scan_sigs_for_samples(const string &rep_fname, const string &samples_file)
{
	MedSamples samples;

	if (samples.read_from_file(samples_file) < 0)
		return -1;

	MedPidRepository rep;
	if (rep.init(rep_fname) < 0)
		return -1;

	// get list of id,date,category
	vector<float> categs;
	samples.get_categs(categs);
	int n_categs = (int)categs.size();

	vector<int> ids;
	samples.get_ids(ids);

	int max_categs_to_count = 10;
	if (n_categs > max_categs_to_count) {
		n_categs = 0; categs.clear();
	}

	map<pair<int, int>, int> id_categ2date;
	float c;
	vector<int> n_per_categ(n_categs + 1, 0);
	for (auto &id : samples.idSamples)
		for (auto &rec : id.samples) {
			if (n_categs == 0)
				c = 0;
			else
				c = rec.outcome;
			pair<int, int> key(rec.id, (int)c);
			if (id_categ2date.find(key) == id_categ2date.end()) {
				id_categ2date[key] = rec.time;
				n_per_categ[(int)c]++;
			}
			else {
				if (rec.time > id_categ2date[key])
					id_categ2date[key] = rec.time;
			}
		}

	map<string, vector<int>> counts;
	MLOG("Scanning %d ids , %d signals, %d categories , %d id x categ cases\n", ids.size(), rep.sigs.signals_ids.size(), n_categs, id_categ2date.size());
	for (int sid : rep.sigs.signals_ids) {

		vector<float> vals;
		vector<float> outcome;

		MLOG("sid %d %s\n", sid, rep.sigs.name(sid).c_str());

		if (rep.load(sid, ids) < 0) return -1;

		MLOG("Scanning sig %d %s\n", sid, rep.sigs.name(sid).c_str());
		vector<int> sig_counts(n_categs + 1, 0);
		UniversalSigVec usv;

		for (auto &it : id_categ2date) {
			float last_val = -999;
			float last_out = -1;
			rep.uget(it.first.first, sid, usv);
			if (usv.len > 0 && usv.Time(0) < it.second) {
				sig_counts[it.first.second]++;
				if (n_categs)
					sig_counts[n_categs]++;
				last_val = usv.Val(0);
				last_out = (float)it.first.second;
			}
			if (last_val != -999) {
				vals.push_back(last_val);
				outcome.push_back(last_out);
			}
		}

		double corr = medial::performance::pearson_corr_without_cleaning(vals, outcome);
		counts[rep.sigs.name(sid)] = sig_counts;
		MLOG("## sig %d type %d %s counts ::", sid, rep.sigs.Sid2Info[sid].type, rep.sigs.name(sid).c_str());
		if (n_categs) {
			MLOG(" Categories:");
			vector<int> chi_counts(n_categs * 2, 0);
			for (int i = 0; i < n_categs; i++) {
				MLOG(" [%d] %d / %d : %f ", i, sig_counts[i], n_per_categ[i], (float)sig_counts[i] / (float)n_per_categ[i]);
				chi_counts[2 * i] = sig_counts[i];
				chi_counts[2 * i + 1] = n_per_categ[i] - sig_counts[i];
			}
			MLOG(" :: bias %f ", medial::stats::chi2_n_x_m(chi_counts, n_categs, 2));
		}
		MLOG(" :: corr %f", corr);
		MLOG(" :: total %d / %d :: %f\n", sig_counts[n_categs], id_categ2date.size(), (float)sig_counts[n_categs] / (float)id_categ2date.size());

		if (rep.free(sid) < 0) return -1;
	}

	return 0;
}


//================================================================================================
int flow_samples_filter_and_match(string rep_fname, string in_samples_file, string out_samples_file, string filter_params, string match_params)
{
	MedSamples in_samples;
	MedSamples filtered_samples;
	MedSamples out_samples;

	// read in_samples
	if (in_samples.read_from_file(in_samples_file) < 0) {
		MERR("ERROR: Can't read samples file %s\n", in_samples_file.c_str());
		return -1;
	}

	// defininf filters and getting required signals
	vector<string> req_sigs_filter, req_sigs_match, req_sigs;

	BasicSampleFilter bsf;
	bsf.init_from_string(filter_params);
	bsf.get_required_signals(req_sigs_filter);
	MatchingSampleFilter msf;
	msf.init_from_string(match_params);
	msf.get_required_signals(req_sigs_match);

	// pid list
	vector<int> pid_list;
	in_samples.get_ids(pid_list);

	// init rep
	req_sigs = req_sigs_filter;
	req_sigs.insert(req_sigs.end(), req_sigs_match.begin(), req_sigs_match.end());
	MedRepository rep;
	if (req_sigs.size() > 0)
		if (rep.read_all(rep_fname, pid_list, req_sigs) < 0) {
			MERR("Can't read repository %s\n", rep_fname.c_str());
			return -1;
		}

	// filter if needed
	if (filter_params != "") {
		MLOG("Filter & Match : file %s filtered with %s\n", in_samples_file.c_str(), filter_params.c_str());
		bsf.filter(rep, in_samples, filtered_samples);
	}
	else
		filtered_samples = in_samples;

	if (rep.dict.read_state == 0 && match_params != "") {
		msf.get_required_signals(req_sigs);
		if (req_sigs.size() > 0) {
			if (rep.read_all(rep_fname, {}, req_sigs) < 0) {
				MERR("Cann't read repository");
				return -1;
			}
		}
	}
	// second .. we match
	if (match_params != "") {
		MLOG("Filter & Match : file %s matched with %s\n", in_samples_file.c_str(), match_params.c_str());
		msf.filter(rep, filtered_samples, out_samples);
	}
	else
		out_samples = filtered_samples;


	// write results
	if (out_samples.write_to_file(out_samples_file) < 0) {
		MERR("Can't write output samples file %s\n", out_samples_file.c_str());
		return -1;
	}

	MLOG("Filter & Match : wrote output file %s\n", out_samples_file.c_str());

	return 0;
}

void flow_generate_features(const string &rep_fname, const string &samples_file, const string& model_init_fname, const string& matrix_fname,
	vector<string> alterations, const string& f_model, const string &change_model_init, const string &change_model_file) {

	MLOG("Reading learning samples file [%s]\n", samples_file.c_str());
	MedSamples samples;
	if (samples.read_from_file(samples_file) < 0)
		MTHROW_AND_ERR("TT: read_all_input_files(): ERROR could not read samples file %s\n", samples_file.c_str());

	MedModel m;
	if (!change_model_file.empty())
		m.read_from_file_with_changes(f_model, change_model_file);
	else {
		if (f_model.size() > 0 && f_model.find("you/need/to/fill") == string::npos) {
			MLOG("f_model specified, reading model from [%s]\n", f_model.c_str());
			m.read_from_file(f_model);
		}
		else {
			MLOG("model_init_fname specified, reading model from [%s]\n", model_init_fname.c_str());
			m.init_from_json_file_with_alterations(model_init_fname, alterations);
		}
		if (!change_model_init.empty()) {
			ChangeModelInfo ch;
			ch.init_from_string(change_model_init);
			m.change_model(ch);
		}
	}

	vector<int> pids;
	samples.get_ids(pids);


	MLOG("Reading repo file [%s]\n", rep_fname.c_str());

	MedPidRepository rep;
	m.load_repository(rep_fname, pids, rep);

	if (f_model.size() > 0 && f_model.find("you/need/to/fill") == string::npos) {
		MLOG("Applying model + generating features...\n");
		m.apply(rep, samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	}
	else {
		MLOG("Learning model + generating features...\n");
		m.learn(rep, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	}
	MedMat<float> x;
	m.features.get_as_matrix(x);

	int i = 0;
	for (auto &ids : samples.idSamples)
		for (auto &s : ids.samples) {
			x.recordsMetadata[i].label = s.outcome;
			if (s.prediction.size() == 1)
				x.recordsMetadata[i].pred = s.prediction[0];
			assert(x.recordsMetadata[i].id == s.id);
			assert(x.recordsMetadata[i].date == s.time);
			x.recordsMetadata[i].outcomeTime = s.outcomeTime;

			i++;
		}

	x.write_to_csv_file(matrix_fname);

	MLOG("Wrote matrix file [%s]\n", matrix_fname.c_str());
	return;
}


//=====================================================================================================================
int read_cohort_recs(const string &fname, vector<LocalCohortRec> &cr)
{
	cr.clear();

	ifstream inf(fname);

	if (!inf) {
		MERR("read_cohort_recs(): read: Can't open file %s\n", fname.c_str());
		return -1;
	}

	string curr_line;
	while (getline(inf, curr_line)) {
		//		MLOG("curr_line: %s\n", curr_line.c_str());
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {
			vector<string> fields;
			split(fields, curr_line, boost::is_any_of(" \t"));
			LocalCohortRec c;
			if (fields.size() >= 4) {
				c.pid = stoi(fields[0]);
				c.from = stoi(fields[1]);
				c.to = stoi(fields[2]);
				c.outcome = stoi(fields[3]);
				cr.push_back(c);
			}
		}
	}

	inf.close();

	return 0;
}


//================================================================================================
int read_pid_list(const string &fname, vector<int> &pids)
{
	pids.clear();

	ifstream inf(fname);

	if (!inf) {
		MERR("read_pid_list(): read: Can't open file %s\n", fname.c_str());
		return -1;
	}

	string curr_line;
	while (getline(inf, curr_line)) {
		//		MLOG("curr_line: %s\n", curr_line.c_str());
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {
			vector<string> fields;
			split(fields, curr_line, boost::is_any_of(" \t"));
			int pid;
			if (fields.size() >= 1) {
				pid = stoi(fields[0]);
				pids.push_back(pid);
			}
		}
	}

	inf.close();

	return 0;
}

//================================================================================================
int flow_get_incidence(const string &inc_params, const string &rep_fname)
{
	//string inc_params; // from_to_fname,pids_to_use_fname,from_year,to_year,min_age,max_age,bin_size,inc_file

	vector<string> fields;
	boost::split(fields, inc_params, boost::is_any_of(","));

	string from_to_fname = fields[0];
	string inc_file = fields[7];
	bool med_registry_format = false;
	string sampler_type = "yearly", sampler_params = "day_jump=365;";
	string labeling_params = "conflict_method=max;time_from=0;time_to=";
	string pids_to_use_fname = fields[1];

	IncidenceParams i_params;
	i_params.rep_fname = rep_fname;
	i_params.from_year = stoi(fields[2]);
	i_params.to_year = stoi(fields[3]);
	i_params.from_age = stoi(fields[4]);
	i_params.to_age = stoi(fields[5]);
	i_params.age_bin = stoi(fields[6]);
	i_params.incidence_years_window = 1; // how many years ahead do we consider an outcome?
	i_params.min_samples_in_bin = 20;
	i_params.gender_mask = 0x3;
	i_params.train_mask = 0x7;
	int time_period = i_params.incidence_days_win > 0 ? i_params.incidence_days_win :
		365 * i_params.incidence_years_window;
	labeling_params += to_string(time_period);

	char buffer[500];
	snprintf(buffer, sizeof(buffer), ";start_year=%d;end_year=%d",
		i_params.from_year, i_params.to_year);
	sampler_params += string(buffer);
	if (fields.size() > 8)
		med_registry_format = stoi(fields[8]) > 0;
	if (fields.size() > 9)
		sampler_type = fields[9];
	if (fields.size() > 10) {
		sampler_params = fields[10];
		MLOG("Sampling params: %s\n", sampler_params.c_str());
	}
	if (fields.size() > 11) {
		labeling_params = fields[11];
		MLOG("Labeling params: %s\n", labeling_params.c_str());
	}

	vector<int> pids;
	if (pids_to_use_fname != "" && pids_to_use_fname != "NONE" && read_pid_list(pids_to_use_fname, pids) < 0) return -1;
	unordered_set<int> pids_set;
	for (auto pid : pids) pids_set.insert(pid);

	// read from_to data
	if (!med_registry_format) {
		MedCohort cohort;
		if (cohort.read_from_file(from_to_fname) < 0) return -1;
		if (pids_to_use_fname != "" && pids_to_use_fname != "NONE") {
			vector<CohortRec> recs_filtered;
			recs_filtered.reserve((int)cohort.recs.size());
			for (size_t i = 0; i < cohort.recs.size(); ++i)
				if (pids_set.find(cohort.recs[i].pid) != pids_set.end())
					recs_filtered.push_back(cohort.recs[i]);
			cohort.recs.swap(recs_filtered);
		}

		return cohort.create_incidence_file(i_params, inc_file);
	}
	else {
		MedRegistry registry;
		registry.read_text_file(from_to_fname);
		if (pids_to_use_fname != "" && pids_to_use_fname != "NONE") {
			vector<MedRegistryRecord> recs_filtered;
			recs_filtered.reserve((int)registry.registry_records.size());
			for (size_t i = 0; i < registry.registry_records.size(); ++i)
				if (pids_set.find(registry.registry_records[i].pid) != pids_set.end())
					recs_filtered.push_back(registry.registry_records[i]);
			registry.registry_records.swap(recs_filtered);
		}
		LabelParams pr; pr.init_from_string(labeling_params);
		MedLabels labeler(pr); labeler.prepare_from_registry(registry.registry_records);

		bool use_kaplan_meier = false;
		labeler.create_incidence_file(inc_file, i_params.rep_fname, i_params.age_bin,
			i_params.from_age, i_params.to_age, use_kaplan_meier, sampler_type, sampler_params);
		return 0;
	}

}

