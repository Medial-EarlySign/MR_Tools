#include "train_test_v2.h"
#include "MedStat/MedStat/MedPerformance.h"
#include "Logger/Logger/Logger.h"
#include "MedAlgo/MedAlgo/MedXGB.h"

#define LOCAL_SECTION LOG_DEF
#define LOCAL_LEVEL	LOG_DEF_LEVEL

//===========================================================================================================================
void TrainTestV2::runner()
{
	set_parameters_from_cmd_line();
	if (!conf_fname.empty()) {
		read_config(conf_fname);
	}
	read_all_input_files();
	if (train_flag) {
		train();
	}
	if (validate_flag) {
		validate();
	}
}

//===========================================================================================================================
int TrainTestV2::read_predictor_params(string &fname)
{
	if (fname == "") {
		paramsList = {};
		return 0;
	}

	ifstream inf(fname);
	string curr_line;

	if (!inf) {
		MERR("Predictor Parameters File: can't open file %s for read\n", fname.c_str());
		return -1;
	}

	while (getline(inf, curr_line)) {
		if (curr_line[0] != '#') {
			vector<string> fields;
			boost::trim(curr_line);
			boost::split(fields, curr_line, boost::is_any_of("\t"));

			if (fields.size() == 2) {
				paramsList.push_back(fields);
			}
			else {
				MERR("Predictor Parameters File:: file [%s] does not contain 2 parameters per line\n", fname.c_str());
				return -1;
			}
		}
	}

	inf.close();
	return 0;
}



//===========================================================================================================================
void TrainTestV2::init_steps(const vector<string> &steps_params) {
	for (auto &s : steps_params) {
		if (s == "Train" || s == "TRAIN" || s == "train") {
			MLOG("TT: will train\n");
			train_flag = 1;
		}
		if (s == "Validate" || s == "VALIDATE" || s == "validate") {
			MLOG("TT: will validate\n");
			validate_flag = 1;
		}
	}
}

//===========================================================================================================================
void TrainTestV2::set_parameters_from_cmd_line() {

	if (!steps.empty()) {
		vector<string> steps_params;
		boost::split(steps_params, steps, boost::is_any_of(" \t,;:"));
		MLOG("Setting Steps from Command line\n");
		init_steps(steps_params);
	}
	if (!active_splits_str.empty()) {
		boost::split(active_split_requests, active_splits_str, boost::is_any_of(" \t,;:"));
		MLOG("Setting active_splits from Command line\n");
	}
	if (!cv_on_train_str.empty()) {
		MLOG("Setting cv_on_train1 from Command line\n");
		cv_on_train_flag = stoi(cv_on_train_str);
	}

}


//===========================================================================================================================
void TrainTestV2::read_config(const string &config_name)
{
	MLOG("TT: ********* read_config() from file %s *********\n", config_name.c_str());

	ifstream inf(config_name);

	if (!inf) {
		MERR("TT: read_config() can't open file %s for read\n", config_name.c_str());
		throw exception();
	}

	string curr_line;
	vector<int> explicit_splits;
	while (getline(inf, curr_line)) {
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {

			if (curr_line[curr_line.size() - 1] == '\r')
				curr_line.erase(curr_line.size() - 1);

			vector<string> fields;
			boost::split(fields, curr_line, boost::is_any_of(" \t"));

			if (fields.size() >= 2) {
				vector<string> fields2;
				boost::split(fields2, fields[1], boost::is_any_of(" \t,;:"));

				if (fields[0] == "NAME") name = fields[1];
				else if (fields[0] == "REPOSITORY" && (f_rep.size() == 0 || f_rep.find("you/need/to/fill") != std::string::npos))
					f_rep = fields[1];
				else if (fields[0] == "WORK_DIR" && wdir.size() == 0) wdir = fields[1];
				else if (fields[0] == "SPLITS" && f_split.size() == 0)	f_split = fields[1];
				else if (fields[0] == "VALIDATION_SAMPLES" && f_validation_samples.size() == 0) f_validation_samples = fields[1];
				else if (fields[0] == "LEARNING_SAMPLES" && f_learning_samples.size() == 0) f_learning_samples = fields[1];
				else if (fields[0] == "LEARNING_SAMPLES_FOR_CV" && f_learning_samples_for_cv.size() == 0) f_learning_samples_for_cv = fields[1];
				else if (fields[0] == "MODEL_INIT_FILE" && f_model_init.size() == 0) { f_model_init = fields[1]; }
				else if (fields[0] == "PREFIX" && prefix.size() == 0)  prefix = fields[1];
				else if (fields[0] == "FILTER_TRAIN_CV")  filter_train_cv = med_stoi(fields[1]);
				else if (fields[0] == "VALIDATION_PREFIX" && validation_prefix.size() == 0) validation_prefix = fields[1];
				else if (fields[0] == "SAVE_MATRIX" && save_matrix_flag.size() == 0) { save_matrix_flag = fields[1]; MLOG("TT: save_matrix = [%s]\n", save_matrix_flag.c_str()); }
				else if (fields[0] == "SAVE_CONTRIBS" && save_contribs_flag.size() == 0) { save_contribs_flag = fields[1]; MLOG("TT: save_contribs = [%s]\n", save_contribs_flag.c_str()); }
				else if (fields[0] == "CV_ON_TRAIN1" && cv_on_train_str.size() == 0) { cv_on_train_flag = stoi(fields[1]); MLOG("Setting from config file: cv_on_train = [%d]\n", cv_on_train_flag); }
				else if (fields[0] == "PREDS_FORMAT" && preds_format.size() == 0) preds_format = fields[1];
				else if (fields[0] == "PREDECITOR_PARAMS_FILE" && pred_params_fname.size() == 0) pred_params_fname = fields[1];
				else if (fields[0] == "LEARNING_SAMPLES_PROB") {
					learning_sampling_prob0 = stof(fields[1]);
					learning_sampling_prob1 = learning_sampling_prob0;
					if (fields.size() >= 3)	learning_sampling_prob1 = stof(fields[2]);
				}
				else if (fields[0] == "VALIDATION_SAMPLES_PROB") {
					validation_sampling_prob0 = stof(fields[1]);
					validation_sampling_prob1 = validation_sampling_prob0;
					if (fields.size() >= 3)	validation_sampling_prob1 = stof(fields[2]);
				}
				else if (fields[0] == "TIME_UNIT") {
					time_unit = med_time_converter.string_to_type(fields[1]);
					MLOG("#######>>>>>>> setting global time unit to %s (%d)\n", fields[1].c_str(), time_unit);
					global_default_time_unit = time_unit;
				}
				else if (fields[0] == "TIME_UNIT_WINS") {
					time_unit_wins = med_time_converter.string_to_type(fields[1]);
					MLOG("#######>>>>>>> setting global wins time unit to %s (%d)\n", fields[1].c_str(), time_unit_wins);
					global_default_windows_time_unit = time_unit_wins;
				}
				else if (fields[0] == "STEPS" && steps.size() == 0) {
					init_steps(fields2);
				}
				else if (fields[0] == "ACTIVE_SPLITS" && active_splits_str.empty()) {
					active_split_requests = fields2;
				}
				else if (fields[0] == "POST_PROCESSORS_SAMPLES") {
					vector<string> names;
					boost::split(names, fields[1], boost::is_any_of(","));
					for (auto s : names) post_processors_sample_files.push_back(s);
				}
				else {
					MWARN("TT: ignoring [%s]\n", curr_line.c_str());
				}
			}

		}
	}
	inf.close();
	MLOG("TT: read_config:: read config %s succesfully\n", config_name.c_str());
}

//===========================================================================================================================
void TrainTestV2::read_all_input_files() {
	MLOG("TT: ********* read_all_input_files *********\n", f_learning_samples.c_str());
	if (wdir != "")
		for (string* ps : { &f_learning_samples , &f_validation_samples, &f_split, &f_learning_samples_for_cv })
			if (ps->length() > 2 && (*ps)[0] != '/' && (*ps)[1] != ':') {
				MLOG("adding work_dir [%s] to [%s]\n", wdir.c_str(), ps->c_str());
				*ps = (wdir + "/" + *ps);
			}

	// try reading model
	MedModel m;
	vector<string> my_json_alt = json_alt;
	my_json_alt.push_back("_SPLIT_::0");
	my_json_alt.push_back("_WORK_FOLDER_::" + wdir);
	m.init_from_json_file_with_alterations(f_model_init, my_json_alt);

	// read learning samples
//	learning_samples.time_unit = global_default_time_unit;
	if (learning_samples.read_from_file(f_learning_samples) < 0) {
		MERR("TT: read_all_input_files(): ERROR could not read samples file %s\n", f_learning_samples.c_str());
		throw exception();
	}
	full_learning_samples = learning_samples;
	MLOG("TT: before samples dilution got %d learning ids, %d samples\n", learning_samples.idSamples.size(), learning_samples.nSamples());
	learning_samples.binary_dilute(learning_sampling_prob0, learning_sampling_prob1);
	MLOG("TT: after samples dilution %f,%f got %d learning ids, %d samples\n", learning_sampling_prob0, learning_sampling_prob1, learning_samples.idSamples.size(), learning_samples.nSamples());

	MLOG("TT: Read learning samples file [%s] assuming time_unit is [%d]\n", f_learning_samples.c_str(),
		learning_samples.time_unit);

	// read post_processors samples
	post_processors_samples.resize(post_processors_sample_files.size());
	for (int i = 0; i < post_processors_sample_files.size(); i++) {
		if (post_processors_samples[i].read_from_file(post_processors_sample_files[i]) < 0) {
			MTHROW_AND_ERR("TT: read_all_input_files(): Failed reading post processors samples file %s\n", post_processors_sample_files[i].c_str());
		}
		post_processors_samples[i].time_unit = learning_samples.time_unit;
		MLOG("TT: Read post processors samples file %d/%d [%s] with %d samples\n", i, post_processors_sample_files.size(), post_processors_sample_files[i].c_str(), post_processors_samples[i].get_size());
	}

	if (f_learning_samples_for_cv != "" && full_learning_cv_samples.read_from_file(f_learning_samples_for_cv) < 0) {
		MERR("TT: read_all_input_files(): ERROR could not read samples file %s\n", f_learning_samples_for_cv.c_str());
		throw exception();
	}
	//Filter only ids from full_learning_samples
	if (filter_train_cv > 0) {
		vector<MedIdSamples> filtered_samples;
		unordered_set<int> learn_ids;
		for (size_t i = 0; i < full_learning_samples.idSamples.size(); ++i)
			learn_ids.insert(full_learning_samples.idSamples[i].id);
		size_t before_sz = full_learning_cv_samples.idSamples.size();
		for (size_t i = 0; i < full_learning_cv_samples.idSamples.size(); ++i)
			if (learn_ids.find(full_learning_cv_samples.idSamples[i].id) != learn_ids.end())
				filtered_samples.push_back(full_learning_cv_samples.idSamples[i]);
		full_learning_cv_samples.idSamples = move(filtered_samples);
		if (before_sz != full_learning_cv_samples.idSamples.size())
			MWARN("WARN :: full_learning_cv_samples has ids not in training. size was %zu, now %zu\n",
				before_sz, full_learning_cv_samples.idSamples.size());
	}
	// read validation samples
//	validation_samples.time_unit = global_default_time_unit;
	if (f_validation_samples != "" && validation_samples.read_from_file(f_validation_samples) < 0) {
		MERR("TT: read_all_input_files(): ERROR could not read validation samples file %s\n", f_validation_samples.c_str());
		throw exception();
	}
	full_validation_samples = validation_samples;
	MLOG("TT: before samples dilution got %d validation ids, %d samples\n", validation_samples.idSamples.size(), validation_samples.nSamples());
	validation_samples.binary_dilute(validation_sampling_prob0, validation_sampling_prob1);
	MLOG("TT: after samples dilution %f,%f got %d validation ids, %d samples\n", learning_sampling_prob0, learning_sampling_prob1, validation_samples.idSamples.size(), validation_samples.nSamples());
	MLOG("TT: Read validation samples file [%s] assuming time_unit is [%d]\n", f_validation_samples.c_str(),
		validation_samples.time_unit);

	// read split
	if (f_split.length() <= 2) {
		MLOG("TT: using splits from samples file, number of splits given in splits parameter = [%s] \n", f_split.c_str());
		sp.nsplits = stoi(f_split);
		// entering splits from learning samples
		for (auto & s : learning_samples.idSamples) {
			if (s.split < 0 || s.split >= sp.nsplits)
				MTHROW_AND_ERR("TT: ERROR: Got invalid split (%d) for pid %d\n", s.split, s.id);
			if (sp.pid2split.find(s.id) == sp.pid2split.end())
				sp.pid2split[s.id] = s.split;
			if (sp.pid2split[s.id] != s.split)
				MTHROW_AND_ERR("TT: ERROR: splits from sample file mode: Non matching splits for pid %d\n", s.id);
		}
		// entering splits from validation samples
		for (auto & s : validation_samples.idSamples) {
			if (s.split < 0 || s.split >= sp.nsplits)
				MTHROW_AND_ERR("TT: ERROR: Got invalid split (%d) for pid %d\n", s.split, s.id);
			if (sp.pid2split.find(s.id) == sp.pid2split.end())
				sp.pid2split[s.id] = s.split;
			if (sp.pid2split[s.id] != s.split)
				MTHROW_AND_ERR("TT: ERROR: splits from sample file mode: Non matching splits for pid %d\n", s.id);
		}
		MLOG("TT: Read %d splits for pids from learning and validation samples\n", sp.pid2split.size());

		for (auto & s : full_learning_cv_samples.idSamples) {
			if (s.split < 0 || s.split >= sp.nsplits)
				MTHROW_AND_ERR("TT: ERROR: Got invalid split (%d) for pid %d\n", s.split, s.id);
			if (sp.pid2split.find(s.id) == sp.pid2split.end())
				sp.pid2split[s.id] = s.split;
			if (sp.pid2split[s.id] != s.split)
				MTHROW_AND_ERR("TT: ERROR: splits from sample file mode: Non matching splits for pid %d\n", s.id);
		}
	}
	else {
		MLOG("TT: reading split file %s\n", f_split.c_str());
		if (sp.read_from_file(f_split) < 0) {
			MERR("TT: read_all_input_files(): ERROR could not read split file %s\n", f_split.c_str());
			throw exception();
		}
		MLOG("TT: Read split file %s\n", f_split.c_str());
	}

	bool do_full_model = false, do_cv_for_all_splits = false;
	vector<int> do_explicit_splits;
	for (auto &s : active_split_requests) {
		if (s == "full") { MLOG("TT: full model is active\n"); do_full_model = true; }
		else if (s == "cv" || s == "CV") { MLOG("TT: cv specified - all splits are active\n"); do_cv_for_all_splits = true; }
		else { MLOG("TT: split [%d] is active\n", stoi(s)); do_explicit_splits.push_back(stoi(s)); }
	}

	for (int split = 0; split < sp.nsplits; split++)
		active_splits[split] = do_cv_for_all_splits;
	active_splits[sp.nsplits] = do_full_model;
	for (int split : do_explicit_splits)
		active_splits[split] = true;
	for (int split = 0; split <= sp.nsplits; split++)
		MLOG("TT: split [%d] active = %d\n", split, active_splits[split]);

	unordered_set<string> req_names;
	rep = new MedPidRepository;
	if (rep->init(f_rep) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", f_rep.c_str());
	m.fit_for_repository(*rep);
	m.get_required_signal_names(req_names);

	// read rep
	vector<string> sigs;
	sigs.push_back("TRAIN");
	for (string s : req_names)
		sigs.push_back(s);
	sort(sigs.begin(), sigs.end());
	auto it = unique(sigs.begin(), sigs.end());
	sigs.resize(std::distance(sigs.begin(), it));

	vector<int> pids;

	learning_samples.get_ids(pids); //always get pids from learning - will use to validate TRAIN==1 on them so need them
	vector<int> more_pids;
	if (validate_flag) {
		validation_samples.get_ids(more_pids);
		pids.insert(pids.end(), more_pids.begin(), more_pids.end());
	}

	for (auto &pp : post_processors_samples) {
		vector<int> more_ids;
		pp.get_ids(more_ids);
		pids.insert(pids.end(), more_ids.begin(), more_ids.end());
	}



	if (rep->read_all(f_rep, pids, sigs) < 0) {
		MERR("TT: read_all_input_files(): ERROR could not read repository %s\n", f_rep.c_str());
		throw exception();
	}
	MLOG("TT: Read repo file %s\n", f_rep.c_str());

	// read Predictor parameters file for grid search:
	read_predictor_params(pred_params_fname);

}

//===========================================================================================================================
void print_distrib(MedSamples& s) {
	vector<float> y;
	s.get_y(y);
	map <float, int> freq;
	for (int i = 0; i < y.size(); i++)
		if (freq.find(y[i]) == freq.end())
			freq[y[i]] = 1;
		else
			freq[y[i]]++;
	vector<pair<float, int>> top_5(5);
	partial_sort_copy(freq.begin(), freq.end(),
		top_5.begin(), top_5.end(),
		[](const pair<float, int> &a, const pair<float, int> &b)
	{
		return !(a.second < b.second);
	});

	MLOG("TT: patients size: %d y size: %d distribution: ", s.idSamples.size(), y.size());
	for (auto e : top_5)
		if (e.second > 0)
			MLOG("%6.3f: %d ", e.first, e.second);
	MLOG("\n");
}

//===========================================================================================================================
void print_performance(MedSamples& s_before_filter, string dataset, int split, ofstream& perf_fstream) {
	print_distrib(s_before_filter);
	vector<float> preds, y;
	s_before_filter.get_preds(preds);
	s_before_filter.get_y(y);
	float corr = 0;
	bool multicateg = preds.size() > y.size();
	if (multicateg) {
		// multicateg case we take the 1- 0channel as prediction
		MLOG("TT: AUC for multicateg predictions: take only predictions for the first class\n");
		int jump = (int)(preds.size() / y.size());
		for (int i = 0; i < y.size(); i++)
			preds[i] = (float)1 - preds[i*jump];
		preds.resize(y.size());
	}
	corr = medial::performance::pearson_corr_without_cleaning(preds, y);
	if (y.size() == 0) {
		MLOG("TT: 0 samples found, not calculating performance\n");
		return;
	}

	float AUC = medial::performance::auc(preds, y);
	int cnt_ctrl_case[] = { 0, 0 };
	for (size_t i = 0; i < y.size(); i++)
		if (int(y[i]) == 0 || int(y[i]) == 1)
			cnt_ctrl_case[int(y[i])]++;
	MLOG("TT: y size: %d , preds size: %d , ctrls size: %d, cases size: %d, AUC is : %6.3f  CORR is: %6.3f\n", y.size(), preds.size(), cnt_ctrl_case[0],
		cnt_ctrl_case[1], AUC, corr);

	vector<float> sizes = { (float)0.01 , (float)0.05, (float)0.1, (float)0.2, (float)0.5 };
	vector<vector<int>> cnts;
	int direction = 1; if (AUC < 0.5) direction = -1;
	medial::performance::get_preds_perf_cnts(preds, y, sizes, direction, cnts);

	for (int i = 0; i < sizes.size(); i++) {
		float sens, spec, ppv, rr;

		if (i < cnts.size()) {
			medial::performance::cnts_to_perf(cnts[i], sens, spec, ppv, rr);
			MLOG("TT: size: %6.3f sens: %6.3f spec: %6.3f ppv: %6.3f rr: %6.3f\n", sizes[i], sens, spec, ppv, rr);
		}
	}
	perf_fstream << dataset << ',' << split << ',' << AUC << "," << cnt_ctrl_case[0] << "," << cnt_ctrl_case[1] << "," << preds.size() << "," << corr << endl;
}
//===========================================================================================================================
void TrainTestV2::train()
{
	MLOG("TT: ********* train *********\n");
	for (MedModel* p : models)
		if (p != NULL) { delete p; }
	models.resize(sp.nsplits + 1);
	MedSamples learningCVPredictions;
	learningCVPredictions.clear();

	ofstream perf_fstream;
	string perf_file = wdir + "/" + prefix + "_perf.csv";
	perf_fstream.open(perf_file, ios::out);
	if (!perf_fstream)
		MTHROW_AND_ERR("can't open file %s for write\n", perf_file.c_str())
	else
		MLOG("opening file %s for write\n", perf_file.c_str());
	perf_fstream << "prefix,split,auc,ctrls,cases,total,corr" << endl;

	vector<MedSamples> l(sp.nsplits + 1), v(sp.nsplits + 1);
	vector<vector<MedSamples>> pp(sp.nsplits + 1, vector<MedSamples>(post_processors_samples.size()));
	vector<MedFeatures> featuresVecLearn, featuresVecApply;

	for (int split = 0; split <= sp.nsplits; split++) {
		if (split == sp.nsplits)
			MLOG("TT: full model (denoted as split %d)\n", split);
		else
			MLOG("TT: split %d (out of %d)\n", split, sp.nsplits);
		if (!active_splits[split]) {
			MLOG("TT: skipping split %d as it was not specified\n", split);
			continue;
		}
		// important - make sure the feature IDs would be the same between splits!
		MedFeatures::global_serial_id_cnt = 0;

		MLOG("learning_samples.idSamples.size() = %d\n", learning_samples.idSamples.size());
		for (auto& sample : learning_samples.idSamples) {
			int mysplit = sp.pid2split[sample.id];
			if (mysplit != split) {
				if (l[split].idSamples.size() < 3)
					MLOG("TT: pid: %d belongs to split: %d = learning\n", sample.id, mysplit);
				l[split].idSamples.push_back(sample);
			}
			else {
				if (full_learning_cv_samples.idSamples.empty()) {
					if (v[split].idSamples.size() < 3)
						MLOG("TT: pid: %d belongs to split: %d = validating\n", sample.id, mysplit);
					v[split].idSamples.push_back(sample);
				}
			}
		}
		for (auto& sample : full_learning_cv_samples.idSamples) {
			int mysplit = sp.pid2split[sample.id];
			if (mysplit == split) {
				if (v[split].idSamples.size() < 3)
					MLOG("TT: pid: %d belongs to split: %d = validating\n", sample.id, mysplit);
				v[split].idSamples.push_back(sample);
			}
		}

		for (int i_pp = 0; i_pp < post_processors_samples.size(); i_pp++) {
			for (auto &sample : post_processors_samples[i_pp].idSamples) {
				int mysplit = sp.pid2split[sample.id];
				if (mysplit != split)
					pp[split][i_pp].idSamples.push_back(sample);
			}
		}

		models[split] = new MedModel;
		vector<string> my_json_alt = json_alt;
		my_json_alt.push_back("_SPLIT_::" + to_string(split));
		my_json_alt.push_back("_WORK_FOLDER_::" + wdir);
		models[split]->init_from_json_file_with_alterations(this->f_model_init, my_json_alt);

		MLOG("TT: learning split %d on learning samples with distribution:\n", split);
		print_distrib(l[split]);
		// learn
		if (models[split]->learn(*rep, l[split], pp[split]) < 0) {
			MERR("TT: Learning model for split %d failed\n", split);
			throw exception();
		}

		if (save_matrix_flag == "1" || save_matrix_flag == "all" || save_matrix_flag == "train") {
			if (save_matrix_splits.empty() || save_matrix_splits.find("all") != string::npos ||
				save_matrix_splits.find(to_string(split)) != string::npos) {
				MedMat<float> x;
				models[split]->features.get_as_matrix(x);
				x.write_to_csv_file(wdir + "/" + prefix + "_x_" + to_string(split) + ".csv");
			}
		}

		// cv apply on learning set itself
		if (split < sp.nsplits) {

			if (models[split]->apply(*rep, v[split]) < 0) {
				MERR("TT: Applying model for split %d failed\n", split);
				throw exception();
			}

			if (save_matrix_flag == "1" || save_matrix_flag == "all" || save_matrix_flag == "train") {
				if (save_matrix_splits.empty() || save_matrix_splits.find("all") != string::npos ||
					save_matrix_splits.find(to_string(split)) != string::npos) {
					MedMat<float> x;
					models[split]->features.get_as_matrix(x);
					x.write_to_csv_file(wdir + "/" + prefix + "_x_v_" + to_string(split) + ".csv");
				}
			}

			for (auto& pat : v[split].idSamples)
				pat.set_split(split);

			MLOG("TT: split %d : predictions CV performance on learning samples\n", split);
			print_performance(v[split], prefix, split, perf_fstream);

			learningCVPredictions.append(v[split]);
		}
		MLOG("TT: Collected CV predictions for [%d] patients on the learning samples\n", learningCVPredictions.idSamples.size());

		string model_f = wdir + "/" + prefix + "_S" + to_string(split) + ".model";
		MLOG("TT: split %d : writing model file %s\n", split, model_f.c_str());
		if (models[split]->write_to_file(model_f) < 0) {
			MERR("TT: split %d : FAILED writing model file %s\n", model_f.c_str());
			throw exception();
		}
		delete models[split];
		models[split] = NULL;
	}
	vector<float> preds, y;
	if (learningCVPredictions.idSamples.size() > 0) {
		MLOG("TT: cross validated predictions performance on learning samples\n");

		print_performance(learningCVPredictions, prefix, sp.nsplits, perf_fstream);

		if (preds_format == "csv") {
			string f_pl = wdir + "/" + prefix + ".preds";
			learningCVPredictions.write_to_file(f_pl);
		}
		else if (preds_format == "bin") {
			string f_pl = wdir + "/" + prefix + ".bin_preds";
			MLOG("TT: writing binary file [%s]\n", f_pl.c_str());
			learningCVPredictions.write_to_bin_file(f_pl);
		}
		else if (preds_format == "none")
			MLOG("TT: preds_format == [none], not writing predictions\n");
		else
			MTHROW_AND_ERR("TT: unknown preds_format [%s]\n", preds_format.c_str());
	}

	if (paramsList.size() > 0)
	{
		// run Grid search.
		// Build features matrices.
		prepareGridSearch(featuresVecLearn, featuresVecApply, l, v);

		// Run Grid search models.
		runGridSearch(featuresVecLearn, featuresVecApply, perf_fstream, paramsList, v);
	}

	perf_fstream.close();
	MLOG("TT: wrote [%s]\n", perf_file.c_str());
}

//===========================================================================================================================
void TrainTestV2::prepareGridSearch(vector<MedFeatures> &featuresVecLearn, vector<MedFeatures> &featuresVecApply, vector<MedSamples> &learnSamples, vector<MedSamples> &validSamples)
{
	unique_ptr<MedModel> genFeaturesModel = unique_ptr<MedModel>(new MedModel);
	for (int split = 0; split < sp.nsplits; split++) {
		vector<string> my_json_alt = json_alt;
		my_json_alt.push_back("_SPLIT_::" + to_string(split));
		my_json_alt.push_back("_WORK_FOLDER_::" + wdir);
		genFeaturesModel->init_from_json_file_with_alterations(this->f_model_init, my_json_alt);

		// Generate Matrix for Learning
		if (genFeaturesModel->learn(*rep, &learnSamples[split], MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS) < 0) {
			MERR("TT: Grid Search Learning model for split %d failed\n", split);
			throw exception();
		}
		featuresVecLearn.push_back(genFeaturesModel->features);

		// Generate Matrix for Validation
		if (genFeaturesModel->apply(*rep, validSamples[split], MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_APPLY_FTR_PROCESSORS) < 0) {
			MERR("TT: Grid Search Applying model for split %d failed\n", split);
			throw exception();
		}
		featuresVecApply.push_back(genFeaturesModel->features);
	}

}


//===========================================================================================================================
void TrainTestV2::runGridSearch(vector<MedFeatures> &featuresVecLearn, vector<MedFeatures> &featuresVecApply, ofstream &perf_fstream, vector<vector<string>> &paramsList, vector<MedSamples> &validSamples)
{

#pragma omp parallel for
	for (int paramInd = 0; paramInd < paramsList.size(); paramInd++) {
		MedPredictor *predictor;
		MedSamples learningCVPredictions;
		learningCVPredictions.clear();

		string currPredictorType = paramsList[paramInd][0];
		string currPredictorParams = paramsList[paramInd][1];

		for (int split = 0; split < sp.nsplits; split++) {
			// Set Model Parameters according to grid search file
			MLOG("Grid Search Model #[%d]: [%s]. Model parameters: [%s] \n", paramInd, currPredictorType.c_str(), currPredictorParams.c_str());

			predictor = predictor->make_predictor(currPredictorType, currPredictorParams);

			// Learn predictor
			if (predictor->learn(featuresVecLearn[split]) < 0) {
				MERR("TT: Learning model (predictor) for split %d failed\n", split);
				throw exception();
			}

			// cv apply on learning set itself
			if (split < sp.nsplits) {
				// predict 
				predictor->predict((featuresVecApply[split]));
				if (validSamples[split].insert_preds((featuresVecApply[split])) != 0) {
					MERR("Insertion of predictions to samples failed\n");
					throw exception();
				}

				MLOG("TT: split %d : predictions CV performance on learning samples\n", split);

				learningCVPredictions.append(validSamples[split]);
				delete predictor;
			}

			MLOG("TT: Collected CV predictions for [%d] patients on the learning samples\n", learningCVPredictions.idSamples.size());
		}

#pragma omp critical 
		{
			// Write results in atomic manner
			perf_fstream << currPredictorType << ',' << currPredictorParams << endl;
			for (int split = 0; split < sp.nsplits; split++) {
				print_performance(validSamples[split], prefix, split, perf_fstream);
			}
			if (learningCVPredictions.idSamples.size() > 0) {
				MLOG("TT: cross validated predictions performance on learning samples\n");
				print_performance(learningCVPredictions, prefix, sp.nsplits, perf_fstream);
			}
		}

	}
}


//===========================================================================================================================
void make_weighted_matrix(MedLM* lm, MedMat<float>& x, MedMat<float>& wx)
{
	wx.resize(x.get_nrows() + 1, x.get_ncols() + 1);
	wx(0, 0) = lm->b0;
	for (int j = 0; j < x.get_ncols(); j++)
		wx(0, j + 1) = lm->b[j];

	for (int i = 0; i < x.get_nrows(); i++) {
		wx(i, 0) = lm->b0;
		for (int j = 0; j < x.get_ncols(); j++)
			wx(i + 1, j + 1) = lm->b[j] * x(i, j);
	}
	wx.signals.push_back("b0");
	wx.signals.insert(wx.signals.end(), x.signals.begin(), x.signals.end());
	wx.recordsMetadata.push_back(RecordData(1, 19000000, 0, -1, 0, 0, 0.0));
	wx.recordsMetadata.insert(wx.recordsMetadata.end(), x.recordsMetadata.begin(), x.recordsMetadata.end());
}

//===========================================================================================================================
template <typename T> vector<size_t> sort_indexes(const vector<T> &v)
{

	// initialize original index locations
	vector<size_t> idx(v.size());
	iota(idx.begin(), idx.end(), 0);

	// sort indexes based on comparing values in v
	sort(idx.begin(), idx.end(),
		[&v](size_t i1, size_t i2) {return v[i1] < v[i2]; });

	return idx;
}

//===========================================================================================================================
void get_pivoted_contribs(MedMat<float> contribs, MedMat<float> features, MedSamples& pivoted)
{
	int n_contribs = min(3, (int)contribs.ncols - 1);
	for (int i = 0; i < contribs.nrows; i++) {
		vector<float> my_row;
		// importance is contribution relative to the sum of all (pos or neg)
		float sum_pos = 0.0f, sum_neg = 0.0f;
		for (int j = 0; j < contribs.ncols - 1; j++) {
			float f = contribs(i, j);
			if (f >= 0)
				sum_pos += f;
			else
				sum_neg += f;
			my_row.push_back(f);
		}
		vector<size_t> sorted_indexes = sort_indexes<float>(my_row);
		MedIdSamples pat;
		pat.id = contribs.recordsMetadata[i].id;
		for (int direction = 0; direction < 2; direction++) {
			for (int k = 0; k < n_contribs; k++) {
				int j = direction == 0 ? k : (int)my_row.size() - 1 - k;
				MedSample s;
				s.id = contribs.recordsMetadata[i].id;
				s.time = contribs.recordsMetadata[i].date;
				s.outcome = contribs.recordsMetadata[i].label;
				s.outcomeTime = contribs.recordsMetadata[i].outcomeTime;
				s.attributes["b0"] = contribs(i, contribs.ncols - 1);
				float c = my_row[sorted_indexes[j]];
				s.attributes["contribution"] = c;
				float divider = c > 0.0 ? sum_pos : sum_neg;
				s.attributes["importance"] = divider == 0.0f ? 0.0f : c / divider;
				s.attributes["feat_rank"] = (float)k;
				s.attributes["val"] = features(i, sorted_indexes[j]);
				s.prediction.push_back(contribs.recordsMetadata[i].pred);
				s.str_attributes["direction"] = direction == 0 ? "but_why_negative" : "but_why_positive";
				s.str_attributes["feature"] = contribs.signals[sorted_indexes[j]];
				pat.samples.push_back(s);
			}
		}
		pivoted.idSamples.push_back(pat);
	}
}


//===========================================================================================================================
void TrainTestV2::validate()
{
	MLOG("TT: ********* validate *********\n");
	unordered_set<int> should_go_in_cv;
	split_validate_to_cv_and_full(should_go_in_cv);
	for (MedModel* p : models)
		if (p != NULL) { delete p; p = NULL; }
	models.resize(sp.nsplits + 1);
	MedSamples validationCVPredictions;
	MedSamples validationFullModelPredictions;

	ofstream perf_fstream;
	string perf_file = wdir + "/" + validation_prefix + "_perf.csv";
	perf_fstream.open(perf_file, ios::out);
	if (!perf_fstream)
		MTHROW_AND_ERR("can't open file %s for write\n", perf_file.c_str())
	else
		MLOG("opening file %s for write\n", perf_file.c_str());
	perf_fstream << "prefix,split,auc,ctrls,cases,total,corr" << endl;

	for (int split = 0; split <= sp.nsplits; split++) {
		if (split == sp.nsplits)
			MLOG("TT: Applying full model (denoted as split %d) on all validation samples that were not in the learning set\n",
				split, sp.nsplits);
		else
			MLOG("TT: Applying split %d model (out of %d) on validation samples that were in the learning set\n", split, sp.nsplits);
		if (!active_splits[split]) {
			MLOG("TT: skipping %d as it was not specified\n", split);
			continue;
		}
		MedSamples v;
		for (auto& sample : validation_samples.idSamples) {
			//MLOG("TT: debug : split %d pid %d (%d) should %d nsplits %d\n", split, sample.id, sp.pid2split[sample.id], (should_go_in_cv.find(sample.id) != should_go_in_cv.end()), sp.nsplits);
			if (split == sp.nsplits && should_go_in_cv.find(sample.id) == should_go_in_cv.end())
				v.idSamples.push_back(sample);
			if (split < sp.nsplits && should_go_in_cv.find(sample.id) != should_go_in_cv.end() && sp.pid2split[sample.id] == split)
				v.idSamples.push_back(sample);
		}
		if (v.idSamples.size() == 0) {
			MLOG("TT: no samples were found for split %d, continuing...\n", split, sp.nsplits);
			continue;
		}
		MLOG("TT: split %d has [%d] patients \n", split, v.idSamples.size());


		models[split] = new MedModel;
		string model_f = wdir + "/" + prefix + "_S" + to_string(split) + ".model";
		MLOG("TT: before reading model file %s\n", model_f.c_str());
		if (models[split]->read_from_file(model_f) < 0) {
			MERR("TT: Validation: split %d : FAILED reading models file %s\n", split, model_f.c_str());
			throw exception();
		}
		MLOG("TT: completed reading model file %s\n", model_f.c_str());
		if (models[split]->apply(*rep, v) < 0) {
			MERR("TT: Applying model for split %d failed\n", split);
			throw exception();
		}
		MLOG("TT: After apply of split %d from file %s\n", split, model_f.c_str());

		MedMat<float> x;
		models[split]->features.get_as_matrix(x);
		if (save_matrix_flag == "1" || save_matrix_flag == "all" || save_matrix_flag == "validate") {
			if (save_matrix_splits.empty() || save_matrix_splits.find("all") != string::npos ||
				save_matrix_splits.find(to_string(split)) != string::npos) {
				x.write_to_csv_file(wdir + "/" + validation_prefix + "_x_" + to_string(split) + ".csv");
				if (dynamic_cast<MedLM*> (models[split]->predictor) != NULL) {
					MedLM* lm = dynamic_cast<MedLM*> (models[split]->predictor);
					MedMat<float> wx;
					make_weighted_matrix(lm, x, wx);
					wx.write_to_csv_file(wdir + "/" + validation_prefix + "_weighted_x_" + to_string(split) + ".csv");
				}
			}
		}
		if (dynamic_cast<MedXGB*> (models[split]->predictor) != NULL && save_contribs_flag != "none") {
			if (save_matrix_splits.empty() || save_matrix_splits.find("all") != string::npos ||
				save_matrix_splits.find(to_string(split)) != string::npos) {
				MedMat<float> contribs;
				models[split]->predictor->calc_feature_contribs(x, contribs);
				if (save_contribs_flag == "full")
					contribs.write_to_csv_file(wdir + "/" + validation_prefix + "_contribs_" + to_string(split) + ".csv");
				MedSamples samples;
				get_pivoted_contribs(contribs, x, samples);
				samples.write_to_file(wdir + "/" + validation_prefix + "_top_contribs_" + to_string(split) + ".csv");
			}
		}
		for (auto& pat : v.idSamples)
			pat.set_split(split);


		if (split < sp.nsplits) {
			MLOG("TT: split %d : predictions CV performance on validation samples that were used in train\n", split);
			print_performance(v, validation_prefix, split, perf_fstream);
			validationCVPredictions.append(v);
		}
		else
			validationFullModelPredictions.append(v);

		delete models[split];
		models[split] = NULL;
	}

	vector<float> preds, y;
	if (validationCVPredictions.idSamples.size() > 0) {
		int split = 999;
		MLOG("TT: split %d : combined cross validated predictions performance on validation samples that were used in train\n", split);
		print_performance(validationCVPredictions, validation_prefix, split, perf_fstream);
	}
	if (validationFullModelPredictions.idSamples.size() > 0) {
		int split = sp.nsplits;
		MLOG("TT: split %d : full model predictions performance on validation samples outside of train\n", split);
		print_performance(validationFullModelPredictions, validation_prefix, split, perf_fstream);
	}

	MedSamples validationCombinedPredictions;
	validationCombinedPredictions.append(validationCVPredictions);
	validationCombinedPredictions.append(validationFullModelPredictions);

	// combined performance - print only if both are not empty(otherwise it has no difference from previous output)
	if (validationCombinedPredictions.idSamples.size() > 0
		&& validationCVPredictions.idSamples.size() > 0
		&& validationFullModelPredictions.idSamples.size() > 0) {
		int split = 999999;
		MLOG("TT: split %d : combined cross validated + full model predictions performance on all samples (cv prediction for samples used in train, full model for samples not in train)\n", split);
		print_performance(validationCombinedPredictions, validation_prefix, split, perf_fstream);
	}
	if (preds_format == "csv") {
		string f_pl = wdir + "/" + validation_prefix + ".preds";
		validationCombinedPredictions.write_to_file(f_pl);
	}
	else if (preds_format == "bin") {
		string f_pl = wdir + "/" + validation_prefix + ".bin_preds";
		MLOG("TT: writing binary file [%s]\n", f_pl.c_str());
		validationCombinedPredictions.write_to_bin_file(f_pl);
	}
	else if (preds_format == "none")
		MLOG("TT: preds_format == [none], not writing predictions\n");
	else
		MTHROW_AND_ERR("TT: unknown preds_format [%s]\n", preds_format.c_str());

	perf_fstream.close();
	MLOG("TT: wrote [%s]\n", perf_file.c_str());
}

//===========================================================================================================================
// the goal is create a list of ALL the samples that will be counted as cross validation samples
// those are the samples from the full learning set
// either all of them, or just train=1 if the cv_on_train_flag is on.
void TrainTestV2::split_validate_to_cv_and_full(unordered_set<int>& should_go_to_cv)
{
	// prepare a hash for pids in mout
	int t_sid = rep->sigs.sid("TRAIN");
	UniversalSigVec usv;
	if (t_sid < 0) {
		MTHROW_AND_ERR("Ilegal repository, TRAIN not found in %s\n", rep->config_fname.c_str())
	}
	if (!rep->index.index_table[t_sid].is_loaded) {
		MTHROW_AND_ERR("Bug - TRAIN wasn't loaded\n")
	}
	if (cv_on_train_flag) {
		MLOG("TT: cv_on_train_flag=[1], validating that all learning_sampels have TRAIN=1\n");
		for (auto &orec : full_learning_samples.idSamples) {
			rep->uget(orec.id, t_sid, usv);
			if (usv.len <= 0 || usv.Val<int>(0) != 1) {
				if (usv.len > 0)
					MTHROW_AND_ERR("TT ERROR: cv_on_train_flag on but found pid %d in learning_samples with TRAIN=%d!=1\n", orec.id, usv.Val<int>(0))
				else
					MTHROW_AND_ERR("TT ERROR: cv_on_train_flag on but found pid %d in learning_samples without TRAIN signal on rep=%s! ilegal pid\n", orec.id, rep->config_fname.c_str())
			}
		}

		// and now inserting all TRAIN==1 pids in validation_samples to should_go_to_cv
		for (auto &orec : validation_samples.idSamples) {
			rep->uget(orec.id, t_sid, usv);
			if (usv.len > 0 && usv.Val<int>(0) == 1)
				should_go_to_cv.insert(orec.id);
		}

	}
	else {
		// if cv_on_train_flag is off simply put all learning_samples in should_go_to_cv
		for (auto &orec : full_learning_samples.idSamples)
			should_go_to_cv.insert(orec.id);
	}
	MERR("TT: cv_on_train_flag=[%d], found [%d]/[%d] pids in validation_samples that will go into CV instead of full model\n",
		cv_on_train_flag, should_go_to_cv.size(), validation_samples.idSamples.size());
}
