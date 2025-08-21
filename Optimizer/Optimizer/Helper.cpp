#include "Helper.h"
#include <boost/filesystem.hpp>
#include <boost/regex.hpp>
#include <MedAlgo/MedAlgo/MedAlgo.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedStat/MedStat/MedBootstrap.h>
#include <cmath>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void read_int_array(const string &s, vector<int> &arr, const string &arg_name) {
	if (s.empty())
		return;
	vector<string> tokens;
	boost::split(tokens, s, boost::is_any_of(",;"));
	arr.resize(tokens.size());
	for (size_t i = 0; i < tokens.size(); ++i)
	{
		try {
			int val = stoi(tokens[i]);
			arr[i] = val;
		}
		catch (const exception &) {
			HMTHROW_AND_ERR("Error in reading int array for %s = got \"%s\". full string was\"%s\"\n",
				arg_name.c_str(), tokens[i].c_str(), s.c_str());
		}
	}
}

int weights_params::init(map<string, string>& map) {

	vector<string> tokens;
	for (auto it = map.begin(); it != map.end(); ++it)
	{
		if (it->first == "weight_function") {
			boost::to_lower(it->second);
			if (conversion_map.find(it->second) == conversion_map.end())
				MTHROW_AND_ERR("Error can't find weight_function %s\nOptions:\n%s\n", it->second.c_str(),
					medial::io::get_list(conversion_map, "\n").c_str());
			weight_function = weighting_method(conversion_map.at(it->second));
		}
		else if (it->first == "weight_function_params") {
			boost::split(tokens, it->second, boost::is_any_of(",;"));
			weight_function_params.resize(tokens.size());
			for (size_t i = 0; i < weight_function_params.size(); ++i)
				weight_function_params[i] = med_stof(tokens[i]);
		}
		else if (it->first == "json_matrix_model")
			json_matrix_model = it->second;
		else if (it->first == "weight_samples")
			weight_samples = it->second;
		else if (it->first == "weight_attr")
			weight_attr = it->second;
		else if (it->first == "weight_function_inputs") {
			boost::split(weight_function_inputs, it->second, boost::is_any_of(",;")); //:: to split type
		}
		else if (it->first == "rep")
			rep = it->second;
		else
			MTHROW_AND_ERR("Unknown param \"%s\"\n", it->first.c_str());
	}

	return 0;
}

/// has 3 parameters:v1,v1 anb m:. input is gap and outcome
double weights_params::hyperbolic_w(const vector<float> &x) const {
	double m = weight_function_params[2];
	double v1 = weight_function_params[0];
	double v2 = weight_function_params[1];
	double weight = 1;
	float gap = x[0];
	bool is_case = x[1] > 0;

	double middle = (v1 + v2) / 2;
	if (gap > v1 && gap < v2) {
		if ((gap <= middle && is_case) || (gap > middle && !is_case))
			weight = (4 * m / pow(v2 - v1, 2)) * pow(gap - middle, 2) + (1 - m);
		else
			weight = 1 - m;
	}

	if (weight < 0)
		weight = 0;
	return weight;
}

//has 3 parameters: T - for time gap importance . W- the width of time gap,  K - by how much to increase the weight in max. input is only gap, assume outcome changes over T from case to control
double weights_params::time_gap_importance_w(const vector<float> &x) const {
	double T = weight_function_params[0];
	double W = weight_function_params[1];
	double K = weight_function_params[2];
	double weight = 1;
	float gap = x[0];
	if (gap >= T - W && gap <= T + W) {
		float time_diff = abs(T - gap); //raises from 1 till K in gap==T
		weight = sqrt((1 - K * K) / W * time_diff + (K * K));
	}

	return weight;
}

float weights_params::parse_input(const MedFeatures &matrix, int i, const string &parse_input_string) const {
	if (boost::istarts_with(parse_input_string, "sample::")) {
		const MedSample &smp = matrix.samples[i];
		string type = parse_input_string.substr(8);
		if (type == "gap") {
			return med_time_converter.convert_times(matrix.time_unit, MedTime::Days, smp.outcomeTime) -
				med_time_converter.convert_times(matrix.time_unit, MedTime::Days, smp.time);
		}
		else if (type == "outcome" || type == "label") {
			return smp.outcome;
		}
		else
			MTHROW_AND_ERR("Unsupported pasring - %s\n", parse_input_string.c_str());
	}
	else if (boost::istarts_with(parse_input_string, "feature::")) {
		vector<string> names;
		matrix.get_feature_names(names);
		string feat_name = parse_input_string.substr(9);
		const string &full_name = names[find_in_feature_names(names, feat_name)];
		return matrix.data.at(full_name)[i];
	}
	else
		MTHROW_AND_ERR("Unsupported - looking for input starting with sample:: or feature::\nGot: %s\n",
			parse_input_string.c_str());
}

void weights_params::get_weights(const MedSamples &samples, vector<float> &weights) const
{
	vector<MedSample> samples_v;
	samples.export_to_sample_vec(samples_v);
	get_weights(samples_v, weights);
}

void weights_params::get_inputs(const vector<MedSample> &samples, vector<vector<float>> &x) const {
	x.resize(samples.size());
	MedFeatures matrix;
	if (!json_matrix_model.empty()) {
		MedModel model;
		model.init_from_json_file(json_matrix_model);
		MedSamples smps;
		smps.import_from_sample_vec(samples);
		medial::medmodel::apply(model, smps, rep);
		matrix = move(model.features);
	}
	else
		matrix.samples = samples;

	if (!weight_samples.empty() && !weight_attr.empty()
		&& weight_function == weighting_method::from_file) {
		unordered_map<int, vector<pair<int, float>>> pid_to_time_weight;
		MedSamples w_samples;
		w_samples.read_from_file(weight_samples);
		for (const MedIdSamples &pid_s : w_samples.idSamples)
		{
			for (const MedSample &s : pid_s.samples)
			{
				pair<int, float> r(s.time, s.outcome);
				if (weight_attr != "outcome") {
					if (s.attributes.find(weight_attr) == s.attributes.end())
						MTHROW_AND_ERR("Error can't find attribute %s\n", weight_attr.c_str());
					r.second = s.attributes.at(weight_attr);
				}
				pid_to_time_weight[s.id].push_back(move(r));
			}
		}

		int miss_cnt = 0;
		for (int i = 0; i < samples.size(); ++i)
		{
			vector<float> &input_line = x[i];
			input_line.resize(1);
			input_line[0] = 0; //by Default exclude if no match:

			if (pid_to_time_weight.find(samples[i].id) == pid_to_time_weight.end()) {
				++miss_cnt;
				continue;
			}
			const vector<pair<int, float>> &time_opt_search = pid_to_time_weight.at(samples[i].id);
			int found_idx = -1;
			for (int j = 0; j < time_opt_search.size() && found_idx < 0; ++j)
				if (time_opt_search[j].first == samples[i].time)
					found_idx = j;

			if (found_idx < 0) {
				++miss_cnt;
				continue;
			}
			//Write input weight
			input_line[0] = time_opt_search[found_idx].second;
		}
		return;
	}

	for (int i = 0; i < samples.size(); ++i)
	{
		vector<float> &input_line = x[i];
		input_line.resize(weight_function_inputs.size());
		for (int j = 0; j < weight_function_inputs.size(); ++j)
			input_line[j] = parse_input(matrix, i, weight_function_inputs[j]);
	}
}

void weights_params::get_weights(const vector<MedSample> &samples, vector<float> &weights) const {
	//retrieve inputs
	if (weight_function == weighting_method::none)
		MTHROW_AND_ERR("Error - weights_params::get_weights. weight function is none and request to get weights\n");
	vector<vector<float>> x;
	get_inputs(samples, x);

	//calculate functions:
	weights.resize(samples.size());
	switch (weight_function)
	{
	case weighting_method::hyperbolic:
		if (weight_function_params.size() < 3)
			MTHROW_AND_ERR("Error hyperbolic not support less than 3 params\n");
		if (!x.empty() && x.front().size() != 2)
			MTHROW_AND_ERR("Error hyperbolic supports only 2 input: gap,outcome\n");

		for (size_t i = 0; i < weights.size(); ++i)
			weights[i] = hyperbolic_w(x[i]);
		break;
	case weighting_method::time_gap_importance:
		if (weight_function_params.size() < 3)
			MTHROW_AND_ERR("Error time_gap_importance not support less than 3 params\n");
		if (!x.empty() && x.front().size() != 1)
			MTHROW_AND_ERR("Error time_gap_importance supports only 1 input: gap\n");
		if (weight_function_params[0] <= 0 || weight_function_params[1] <= 0)
			MTHROW_AND_ERR("Error time_gap_importance input paramaters T,W > 0\n");

		for (size_t i = 0; i < weights.size(); ++i)
			weights[i] = time_gap_importance_w(x[i]);
		break;
	case weighting_method::from_file:
		if (x.empty() || x.front().size() != 1)
			MTHROW_AND_ERR("Error from_file needs to have both weight_samples, weight_attr in order to work\n");
		for (size_t i = 0; i < weights.size(); ++i)
			weights[i] = x[i][0];
		break;
	default:
		MTHROW_AND_ERR("weights_params::get_weights - Unsupported method %d\n", int(weight_function));
	}
}

string weights_params::to_string() const {
	stringstream s;
	unordered_map<int, string> op_map;
	for (const auto &it : conversion_map)
		op_map[it.second] = it.first;
	string w_f = "none";
	if (active()) {
		if (op_map.find(weight_function) != op_map.end())
			w_f = op_map.at(weight_function);
		else
			w_f = "unknown";
	}

	s << "weight_function=" << w_f << ";";
	if (!rep.empty())
		s << "rep=" << rep << ";";
	if (!json_matrix_model.empty())
		s << "json_matrix_model=" << json_matrix_model << ";";
	if (!weight_function_inputs.empty())
		s << "weight_function_inputs=" << medial::io::get_list(weight_function_inputs, ",") << ";";
	if (!weight_function_params.empty())
		s << "weight_function_params=" << weight_function_params[0];
	for (size_t i = 1; i < weight_function_params.size(); ++i)
		s << "," << weight_function_params[i];
	if (!weight_function_params.empty())
		s << ";";
	if (!weight_samples.empty() && !weight_attr.empty() && weight_function == weighting_method::from_file)
		s << "weight_samples=" << weight_samples << ";" << "weight_attr=" << weight_attr;
	return s.str();
}

full_train_args::full_train_args() {
	samples_id = "";
	samples_path = "";
	predictor_type = "";
	predictor_args = "";
	auc_train = MED_MAT_MISSING_VALUE;
	auc = MED_MAT_MISSING_VALUE;
	price_ratio = 0;
	matching_strata = "";
	matching_json = "";
}

string full_train_args::to_string(bool skip_auc) const {
	stringstream s;

	if (samples_path.empty())
		s << "samples_id" << "=" << samples_id;
	else
		s << "samples_path" << "=" << samples_path;
	stringstream s_cases, s_controls;
	bool first_ = true;
	for (int c : cases_def)
	{
		if (!first_)
			s_cases << ",";
		s_cases << c;
		first_ = false;
	}
	first_ = true;
	for (int c : controls_def)
	{
		if (!first_)
			s_controls << ",";
		s_controls << c;
		first_ = false;
	}
	s << ";cases_def" << "=" << s_cases.str();
	s << ";controls_def" << "=" << s_controls.str();
	s << ";price_ratio" << "=" << price_ratio;
	s << ";matching_strata" << "=" << matching_strata;
	s << ";matching_json" << "=" << matching_json;
	s << ";predictor_type" << "=" << predictor_type;
	s << ";predictor_args" << "={" << predictor_args << "}";
	s << ";weights_params" << "={" << w_params.to_string() << "}";

	if (!skip_auc)
		s << "\t" << auc << "\t" << auc_train;

	return s.str();
}

void full_train_args::parse_only_args(const string &args_token, const string &f_path) {
	map<string, string> mapper;
	if (MedSerialize::init_map_from_string(args_token, mapper) < 0)
		MTHROW_AND_ERR("Error Init from String %s from file:\n%s\n", args_token.c_str(), f_path.c_str());

	if (mapper.find("samples_path") == mapper.end())
		MTHROW_AND_ERR("line must include samples_path in %s\n%s\n", f_path.c_str(), args_token.c_str());
	samples_path = mapper.at("samples_path");
	vector<int> cases_ls, controls_ls;
	if (mapper.find("cases_def") == mapper.end())
		MTHROW_AND_ERR("line must include cases_def in %s\n%s\n", f_path.c_str(), args_token.c_str());
	read_int_array(mapper.at("cases_def"), cases_ls, "cases_def");
	cases_def = move(unordered_set<int>(cases_ls.begin(), cases_ls.end()));
	if (mapper.find("controls_def") == mapper.end())
		MTHROW_AND_ERR("line must include controls_def in %s\n%s\n", f_path.c_str(), args_token.c_str());
	read_int_array(mapper.at("controls_def"), controls_ls, "controls_def");
	controls_def = move(unordered_set<int>(controls_ls.begin(), controls_ls.end()));

	if (mapper.find("price_ratio") == mapper.end())
		MTHROW_AND_ERR("line must include price_ratio in %s\n%s\n", f_path.c_str(), args_token.c_str());
	price_ratio = med_stof(mapper.at("price_ratio"));

	if (mapper.find("matching_strata") == mapper.end())
		MTHROW_AND_ERR("line must include matching_strata in %s\n%s\n", f_path.c_str(), args_token.c_str());
	matching_strata = mapper.at("matching_strata");
	if (mapper.find("matching_json") == mapper.end())
		MTHROW_AND_ERR("line must include matching_json in %s\n%s\n", f_path.c_str(), args_token.c_str());
	matching_json = mapper.at("matching_json");

	if (mapper.find("predictor_type") == mapper.end())
		MTHROW_AND_ERR("line must include predictor_type in %s\n%s\n", f_path.c_str(), args_token.c_str());
	predictor_type = mapper.at("predictor_type");
	if (mapper.find("predictor_args") == mapper.end())
		MTHROW_AND_ERR("line must include predictor_args in %s\n%s\n", f_path.c_str(), args_token.c_str());
	predictor_args = mapper.at("predictor_args");

	if (mapper.find("weights_params") == mapper.end())
		MTHROW_AND_ERR("line must include weights_params in %s\n%s\n", f_path.c_str(), args_token.c_str());
	w_params.init_from_string(mapper.at("weights_params"));
}

void full_train_args::parse_line(const string &line, const string &f_path) {
	vector<string> tokens;
	boost::split(tokens, line, boost::is_any_of("\t"));
	if (tokens.size() != 3)
		MTHROW_AND_ERR("Bad format (should have 3 tokens) String %s from file:\n%s\n", line.c_str(), f_path.c_str());

	parse_only_args(tokens[0], f_path);
	string auc_tokens = tokens[1];
	string auc_train_tokens = tokens[2];
	auc = med_stof(auc_tokens);
	auc_train = med_stof(auc_train_tokens);
}

bool weights_params::compare(const weights_params &other) const {
	bool res = active() == other.active();
	if (active() && res)
		res = other.json_matrix_model == json_matrix_model
		&& other.rep == rep && other.weight_function == weight_function;
	if (active() && res) {
		//compare parameters:
		int i = 0;
		res = other.weight_function_params.size() == weight_function_params.size();
		while (res && i < other.weight_function_params.size() && abs(other.weight_function_params[i] - weight_function_params[i]) < 1e-5)
			++i;
		if (i < other.weight_function_params.size())
			res = false;
		//check inputs:
		i = 0;
		res = res && other.weight_function_inputs.size() == weight_function_inputs.size();
		while (res && i < other.weight_function_inputs.size() &&
			other.weight_function_inputs[i] == weight_function_inputs[i])
			++i;
		if (i < other.weight_function_inputs.size())
			res = false;
	}

	return res;
}

void read_old_results(const string &path, const vector<string> &train_path_order, vector<full_train_args> &results) {

	ifstream fr(path);
	if (!fr.good())
		MTHROW_AND_ERR("Error can;t open for reading %s\n", path.c_str());
	string line;
	int cnt = 0;
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		full_train_args f;
		f.parse_line(line, path);
		//find id:
		int id = -1;
		for (int i = 0; i < train_path_order.size() && id < 0; ++i)
			if (train_path_order[i] == f.samples_path)
				id = i;
		if (id < 0)
			MTHROW_AND_ERR("Error read_old_results - can't find sample_id\n");
		f.samples_id = to_string(id);
		if (!already_did(results, train_path_order, f))
			results.push_back(f);
		++cnt;
	}
	fr.close();
	MLOG("read [%d] rows in old results from %s\n", cnt, path.c_str());
}

bool same_lists(const unordered_set<int> &a, const unordered_set<int> &b) {
	bool res = a.size() == b.size();
	auto it_a = a.begin();
	while (res && it_a != a.end()) {
		res = b.find(*it_a) != b.end();
		++it_a;
	}
	return res;
}

bool full_train_args::compare(const full_train_args &o) const {
	bool res = samples_path == o.samples_path &&
		same_lists(cases_def, o.cases_def) &&
		same_lists(controls_def, o.controls_def) &&
		price_ratio == o.price_ratio &&
		matching_strata == o.matching_strata &&
		matching_json == o.matching_json &&
		predictor_type == o.predictor_type &&
		w_params.compare(o.w_params);
	return res;
}

bool already_did(const vector<full_train_args> &process_results, const vector<string> &train_path_order, full_train_args &candidante) {
	//search if exists, samples, price_ratio, weights_params
	string f_path = candidante.samples_path;
	if (f_path.empty()) {
		int ind = med_stoi(candidante.samples_id);
		f_path = train_path_order[ind];
	}
	bool res_found = false;
	full_train_args candi_test = candidante;
	candi_test.samples_path = f_path;
	for (size_t i = 0; i < process_results.size() && !res_found; ++i)
		res_found = process_results[i].compare(candi_test);
	return res_found;
}

void get_train_paths(const string &samples_paths, const vector<int> &cases_labels, const vector<int> &control_labels,
	vector<string> &train_paths_orders, vector<unordered_set<int>> &train_cases_orders,
	vector<unordered_set<int>> &train_controls_orders) {
	ifstream fr(samples_paths);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't read samples file %s\n", samples_paths.c_str());
	string line;
	unordered_set<int> train_case_default_set(cases_labels.begin(), cases_labels.end());
	unordered_set<int> train_cntl_default_set(control_labels.begin(), control_labels.end());

	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 1 && tokens.size() != 3)
			MTHROW_AND_ERR("Error unsupported defintion. Should be wither 1 or 3 tokens (last 2 are optional). File_path, cases_def_by_comma, controls_def_by_comma");
		train_paths_orders.push_back(tokens[0]);
		if (tokens.size() > 1) {
			vector<int> cases_def;
			read_int_array(tokens[1], cases_def, "samples_def_cases(within_file:" + samples_paths + ")");
			unordered_set<int> train_def_set(cases_def.begin(), cases_def.end());
			train_cases_orders.push_back(move(train_def_set));
		}
		else
			train_cases_orders.push_back(train_case_default_set);

		if (tokens.size() > 2) {
			vector<int> controls_def;
			read_int_array(tokens[2], controls_def, "samples_def_controls(within_file:" + samples_paths + ")");
			unordered_set<int> train_def_set(controls_def.begin(), controls_def.end());
			train_controls_orders.push_back(move(train_def_set));
		}
		else
			train_controls_orders.push_back(train_cntl_default_set);
	}
	fr.close();

	MLOG("reading from %s, got %zu files\n", samples_paths.c_str(), train_paths_orders.size());
}

void read_splits_file(const string &split_file, unordered_map<int, int> &pid_to_split) {
	if (split_file.empty())
		return;
	MLOG("Read split from %s\n", split_file.c_str());
	ifstream f_reader(split_file);
	if (!f_reader.good())
		MTHROW_AND_ERR("Error can't open %s for reading\n", split_file.c_str());
	string line;
	while (getline(f_reader, line)) {
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of(" \t,"));
		if (tokens.size() != 2) {
			f_reader.close();
			MTHROW_AND_ERR("Error - Bad format in file %s, expecting 2 tokens, got line:\n%s\n",
				split_file.c_str(), line.c_str());
		}
		if (tokens[0] == "NSPLITS")
			continue; //skip first row
		int pid = med_stoi(tokens[0]);
		int split = med_stoi(tokens[1]);
		if (pid_to_split.find(pid) != pid_to_split.end()) {
			f_reader.close();
			MTHROW_AND_ERR("Error in split_file %s, pid %d appeared more than once\n",
				split_file.c_str(), pid);
		}
		pid_to_split[pid] = split;
	}

	f_reader.close();
}
//samples_prefix is file with lines to samples
void read_samples(const vector<string> &train_paths_orders, unordered_map<string, MedSamples> &group_samples,
	const vector<unordered_set<int>> &cases_labels, const vector<unordered_set<int>> &control_labels,
	const unordered_map<int, int> &pid_to_split) {

	int file_id = 0;
	for (const string &file_full_path : train_paths_orders) {

		string samples_option = to_string(file_id);
		group_samples[samples_option].read_from_file(file_full_path);
		MedSamples &samples = group_samples.at(samples_option);
		MedSamples manipulated; manipulated.time_unit = samples.time_unit;
		manipulated.idSamples.reserve(samples.idSamples.size());

		int excluded_cnt = 0;
		for (size_t i = 0; i < samples.idSamples.size(); ++i) {
			MedIdSamples smp_id(samples.idSamples[i].id);
			if (pid_to_split.find(smp_id.id) == pid_to_split.end())
				smp_id.split = samples.idSamples[i].split;
			else
				smp_id.split = pid_to_split.at(smp_id.id);

			smp_id.samples.reserve(samples.idSamples[i].samples.size());
			for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j)
			{
				int label = (int)samples.idSamples[i].samples[j].outcome;
				if (!cases_labels[file_id].empty() && !control_labels[file_id].empty()) { //manipulate only if not empty both
					if (cases_labels[file_id].find(label) != cases_labels[file_id].end())
						label = 1;
					else if (control_labels[file_id].find(label) != control_labels[file_id].end())
						label = 0;
					else
						label = -1;
					samples.idSamples[i].samples[j].outcome = label;
				}
				if (pid_to_split.find(samples.idSamples[i].samples[j].id) != pid_to_split.end())
					samples.idSamples[i].samples[j].split = pid_to_split.at(samples.idSamples[i].samples[j].id);

				if (label != -1)
					smp_id.samples.push_back(samples.idSamples[i].samples[j]);
				else
					++excluded_cnt;
			}
			if (!smp_id.samples.empty()) {
				smp_id.samples.shrink_to_fit();
				manipulated.idSamples.push_back(smp_id);
			}
		}

		manipulated.idSamples.shrink_to_fit();
		samples = move(manipulated);
		++file_id;
		if (excluded_cnt > 0)
			MLOG("Excluded %d samples from %s due to cases/controls rules\n",
				excluded_cnt, file_full_path.c_str());
	}
}

void validate_train_test(const unordered_map<string, MedSamples> &a, const unordered_map<string, MedSamples> &b) {
	if (a.size() != b.size())
		MTHROW_AND_ERR("Input Error - train(%zu) and test(%zu) are not same sizes\n", a.size(), b.size());
	for (const auto &it : a)
		if (b.find(it.first) == b.end())
			MTHROW_AND_ERR("Input Error - %s was not found in test\n", it.first.c_str());
}

void filter_samples(MedSamples &samples, int till_time, bool before) {
	//filter samples till time if before is true, otherwise filters after
	vector<int> idx;
	MedFeatures flat;
	samples.export_to_sample_vec(flat.samples);
	idx.reserve(flat.samples.size());
	for (int i = 0; i < flat.samples.size(); ++i)
		if ((before && flat.samples[i].time <= till_time) || (!before && flat.samples[i].time >= till_time))
			idx.push_back(i);
	medial::process::filter_row_indexes(flat, idx);

	samples.import_from_sample_vec(flat.samples);
}

void split_train_test_till_year(unordered_map<string, MedSamples> &train, unordered_map<string, MedSamples> &test,
	int till_time) {
	if (till_time < 0)
		return;
	for (auto &train_it : train)
	{
		MedSamples &train_batch = train_it.second;
		MedSamples &test_batch = test.at(train_it.first);

		filter_samples(train_batch, till_time, true);
		filter_samples(test_batch, till_time, false);
	}
}

void commit_matching_general(MedSamples &train, float price_matching, double match_to_prior, vector<float> &sample_weights,
	MedPidRepository &rep, const string &strata_str, const string& matching_json, bool verbose = false) {
	if (price_matching == 0)
		return;

	// If matching json is given, create feautres matrix.
	MedModel matching_model;
	FeatureProcessor dummy;
	if (!matching_json.empty()) {
		matching_model.init_from_json_file(matching_json);
		matching_model.learn(rep, train, MED_MDL_LEARN_REP_PROCESSORS, MED_MDL_APPLY_FTR_PROCESSORS);
	}


	vector<string> strata_vec;
	boost::split(strata_vec, strata_str, boost::is_any_of(":"));
	vector<featureStrata> stratas(strata_vec.size());

	string stratas_str_names = "";
	bool need_gender = false;
	int age_ind_sett = -1;
	int time_res = -1;
	int time_unit = MedTime::Undefined;
	vector<string> featureNames(stratas.size());

	for (int i = 0; i < stratas.size(); ++i)
	{
		vector<string> fields;
		boost::split(fields, strata_vec[i], boost::is_any_of(","));
		if (fields.size() < 3)
			MTHROW_AND_ERR("Cannot initialize strata from \'%s\'. Ignoring\n", strata_vec[i].c_str());

		string lc_st = fields[0];
		boost::to_lower(lc_st);

		// Time
		if (lc_st == "time") {
			stratas[i].name = fields[0] + ":" + fields[1];
			stratas[i].resolution = med_stof(fields[2]);
			time_res = stratas[i].resolution;
			time_unit = med_time_converter.string_to_type(fields[1]);
		}
		// Others
		else {
			if (fields.size() != 4)
				MTHROW_AND_ERR("Cannot initialize strata from \'%s\'. Ignoring\n", strata_vec[i].c_str());
			stratas[i] = featureStrata(fields[0], stof(fields[3]), stof(fields[1]), stof(fields[2]));

			// Gender
			if (lc_st == "gender")
				need_gender = 1;
			// Age
			else if (lc_st == "age") {
				if (age_ind_sett != -1)
					MTHROW_AND_ERR("More than one age strata given. Please check\n");
				age_ind_sett = i;
			}
			// Check matching matrix
			else {
				if (matching_model.features.data.empty())
					MTHROW_AND_ERR("tryping to match by \'%s\' without giving Json. Quitting\n", fields[0].c_str());
				featureNames[i] = dummy.resolve_feature_name(matching_model.features, fields[0]);
			}
		}

		if (!stratas_str_names.empty())
			stratas_str_names += "_";
		stratas_str_names += fields[0];

	}
	MLOG("Match by %s\n", stratas_str_names.c_str());

	int bdate_sid = -1;
	int gender_sid = -1;

	MedFeatures flat_samples;
	train.export_to_sample_vec(flat_samples.samples);
	//Matching: match by matching_groups
	vector<string> filtered_groups(flat_samples.samples.size());

	if (age_ind_sett >= 0) {
		bdate_sid = rep.sigs.sid("BDATE");
		if (bdate_sid < 0)
			MTHROW_AND_ERR("Error, can't find BDATE in rep\n");
	}
	if (need_gender) {
		gender_sid = rep.sigs.sid("GENDER");
		if (gender_sid < 0)
			MTHROW_AND_ERR("Error, can't find GENDER in rep\n");
	}

	// Generate groups
	int byear, gender, age, bin_age;
	for (size_t i = 0; i < filtered_groups.size(); ++i) {
		if (need_gender) {
			gender = medial::repository::get_value(rep, flat_samples.samples[i].id, gender_sid);
			if (gender == GENDER_MALE)
				filtered_groups[i] = "MALE";
			else
				filtered_groups[i] = "FEMALE";
		}

		if (age_ind_sett >= 0) {
			byear = int(medial::repository::get_value(rep, flat_samples.samples[i].id, bdate_sid) / 10000);
			age = int(med_time_converter.convert_times(train.time_unit, MedTime::Date,
				flat_samples.samples[i].time) / 10000) - byear;
			if (age < stratas[age_ind_sett].min)
				age = stratas[age_ind_sett].min;
			else if (age > stratas[age_ind_sett].max)
				age = stratas[age_ind_sett].max;

			bin_age = stratas[age_ind_sett].resolution * int(age / stratas[age_ind_sett].resolution);

			if (filtered_groups[i].empty())
				filtered_groups[i] += "_";
			filtered_groups[i] += medial::print::print_obj(bin_age, "% 3d");
		}

		//check if has TIME:
		if (time_res > 0) {
			//format since 1900.
			int sample_tm = med_time_converter.convert_times(global_default_time_unit, time_unit,
				flat_samples.samples[i].time);
			int time_bin = time_res * int(sample_tm / time_res);
			//pretty bin string:
			int pretty_time = med_time_converter.convert_times(time_unit, MedTime::Date, time_bin);

			if (filtered_groups[i].empty())
				filtered_groups[i] += "_";
			filtered_groups[i] += medial::print::print_obj(pretty_time, "%d");
		}

		// From matching matrix
		for (size_t iStrata = 0; iStrata < featureNames.size(); iStrata++) {
			if (!featureNames[iStrata].empty()) {
				float value = matching_model.features.data[featureNames[iStrata]][i];

				if (value < stratas[iStrata].min)
					value = stratas[iStrata].min;
				else if (value > stratas[iStrata].max)
					value = stratas[iStrata].max;

				int bin = stratas[iStrata].resolution * int(value / stratas[iStrata].resolution);

				if (filtered_groups[i].empty())
					filtered_groups[i] += "_";
				filtered_groups[i] += medial::print::print_obj(bin, "% 3d");
			}
		}

	}

	if (price_matching > 0 || match_to_prior > 0) {
		vector<int> seleced_filt;
		if (match_to_prior > 0) {
			vector<float> y_ex(flat_samples.samples.size());
			for (size_t j = 0; j < y_ex.size(); ++j)
				y_ex[j] = flat_samples.samples[j].outcome;
			unordered_map<string, float> map_dict_grps;

			int curr_idx = 1;
			for (size_t j = 0; j < filtered_groups.size(); ++j)
				if (map_dict_grps.find(filtered_groups[j]) == map_dict_grps.end()) {
					map_dict_grps[filtered_groups[j]] = curr_idx;
					++curr_idx;
				}
			vector<float> filtered_groups_f(filtered_groups.size()); // populate each string to float:
			for (size_t j = 0; j < filtered_groups.size(); ++j)
				filtered_groups_f[j] = map_dict_grps.at(filtered_groups[j]);

			medial::process::match_to_prior(y_ex, filtered_groups_f, match_to_prior, seleced_filt);
			medial::process::filter_row_indexes(flat_samples, seleced_filt);
		}
		else
			medial::process::match_by_general(flat_samples, filtered_groups, seleced_filt, price_matching,
				5, verbose);
		//save in MedSamples:
		train.import_from_sample_vec(flat_samples.samples);
		//sample_weights.resize(flat_samples.samples.size(), 1);
	}
	else {
		//reweight:
		medial::process::reweight_by_general(flat_samples, filtered_groups, sample_weights, verbose);
	}

	double tot_cases = 0, tot_cont = 0;
	for (size_t i = 0; i < flat_samples.samples.size(); ++i)
		if (flat_samples.samples[i].outcome > 0)
			tot_cases += (!sample_weights.empty() ? sample_weights[i] : 1);
		else
			tot_cont += (!sample_weights.empty() ? sample_weights[i] : 1);

	if (verbose) {
		MLOG("After Matching has %2.1f controls and %2.1f cases with %2.3f%% percentage\n",
			tot_cont, tot_cases, 100.0*tot_cases / (tot_cases + tot_cont));
		//print by each group:
		unordered_map<string, pair<double, double>> grp_stats;
		unordered_map<string, pair<int, int>> grp_cnts;
		for (size_t i = 0; i < flat_samples.samples.size(); ++i) {
			if (flat_samples.samples[i].outcome > 0) {
				grp_stats[filtered_groups[i]].second += (!sample_weights.empty() ? sample_weights[i] : 1);
				++grp_cnts[filtered_groups[i]].second;
			}
			else {
				grp_stats[filtered_groups[i]].first += (!sample_weights.empty() ? sample_weights[i] : 1);
				++grp_cnts[filtered_groups[i]].first;
			}
		}
		MLOG("%s\tcntrl\tcases\tcntrl_weighted\tcases_weighted\tpercentage\n", stratas_str_names.c_str());
		for (const auto &it : grp_stats)
		{
			MLOG("%s\t%d\t%d\t%2.1f\t%2.1f\t%2.2f\n",
				it.first.c_str(), grp_cnts.at(it.first).first, grp_cnts.at(it.first).second,
				grp_stats.at(it.first).first, grp_stats.at(it.first).second,
				grp_stats.at(it.first).second / (grp_stats.at(it.first).second + grp_stats.at(it.first).first));
		}
	}
}

void init_medmodel(MedModel &model, MedPidRepository &rep, const string &json_path) {
	model.clear();
	model.virtual_signals.clear();
	model.required_signal_ids.clear();
	model.required_signal_names.clear();
	model.init_from_json_file(json_path);
	model.fit_for_repository(rep);
	model.filter_rep_processors();

	unordered_set<string> req_names;
	model.get_required_signal_names(req_names);
}

void prepare_rep_from_model(MedModel &mod, MedPidRepository &rep, const string &RepositoryPath) {
	MedSamples empty;
	medial::repository::prepare_repository(empty, RepositoryPath, mod, rep);
}

void prepare_rep_from_model(
	MedModel &mod, 
	MedPidRepository &rep, 
	const string &RepositoryPath,
	const unordered_map<string, MedSamples> &train, 
	const unordered_map<string, MedSamples> &test) {

	unordered_set<int> pids_s;
	for (const auto & it : train)
		for (size_t i = 0; i < it.second.idSamples.size(); ++i)
			pids_s.insert(it.second.idSamples[i].id);
	for (const auto & it : test)
		for (size_t i = 0; i < it.second.idSamples.size(); ++i)
			pids_s.insert(it.second.idSamples[i].id);

	vector<int> pids(pids_s.begin(), pids_s.end());
	medial::repository::prepare_repository(pids, RepositoryPath, mod, rep);
}

void enrich_rep_from_model(MedModel& model, MedPidRepository& rep, const string &RepositoryPath) {

	// Do we need additional signals ?
	vector<string> signals;
	model.get_required_signal_names(signals);

	vector<string> unloaded;
	for (string& signal : signals) {
		if (rep.index.index_table[rep.dict.id(signal)].is_loaded != 1)
			unloaded.push_back(signal);
	}

	if (!unloaded.empty()) {
		MLOG("Adding following signals to repository for matching:");
		for (string& signal : unloaded)
			MLOG(" %s", signal.c_str());
		MLOG("\n");
		rep.load(signals);
	}

}

void prepare_rep_for_signals(MedPidRepository &rep, const string &RepositoryPath, const vector<string> &signals,
	const unordered_map<string, MedSamples> &train, const unordered_map<string, MedSamples> &test) {
	unordered_set<int> pids_s;
	for (const auto & it : train)
		for (size_t i = 0; i < it.second.idSamples.size(); ++i)
			pids_s.insert(it.second.idSamples[i].id);
	for (const auto & it : test)
		for (size_t i = 0; i < it.second.idSamples.size(); ++i)
			pids_s.insert(it.second.idSamples[i].id);

	vector<int> pids(pids_s.begin(), pids_s.end());
	if (rep.read_all(RepositoryPath, pids, signals) < 0)
		MTHROW_AND_ERR("Error can't read repo %s\n", RepositoryPath.c_str());
}

float auc_samples(const vector<MedSample> &samples, const vector<float> &weights, const string &bootstrap_params, const string &measure) {
	if (samples.empty())
		MTHROW_AND_ERR("Error in auc_samples - samples is empty\n");
	if (!weights.empty() && weights.size() != samples.size())
		MTHROW_AND_ERR("Error in auc_samples - samples(%zu) and weights(%zu) not in same size\n",
			samples.size(), weights.size());
	if (samples.front().prediction.empty())
		MTHROW_AND_ERR("Error in auc_samples - no predictions\n");

	vector<float> y(samples.size()), preds(samples.size());
	bool has_0 = false, has_1 = false;
	bool has_measurement_params = bootstrap_params.find("measurement") != string::npos;
	for (size_t i = 0; i < samples.size(); ++i)
	{
		y[i] = samples[i].outcome;
		preds[i] = samples[i].prediction[0];
		has_0 |= y[i] <= 0;
		has_1 |= y[i] > 0;
	}
	if (!has_measurement_params && (!has_0 || !has_1)) {
		if (has_0)
			MLOG("No AUC - got only controls\n");
		else
			MLOG("No AUC - got only cases\n");
		return -1;
	}
	else {
		MedBootstrap bt;
		bt.loopCnt = 0;

		bt.init_from_string(bootstrap_params);
		MedFeatures bootstrap_feats;
		bootstrap_feats.samples = samples;
		if (!weights.empty())
			bootstrap_feats.weights = weights;
		map<string, map<string, float>> res = bt.bootstrap(bootstrap_feats);
		if (!res.empty()) {
			map<string, float> &all_res = res.begin()->second;
			if (all_res.find(measure) == all_res.end())
				MTHROW_AND_ERR("Error can't find %s in bootstrap\n", measure.c_str());
			return all_res.at(measure);
		}
		else {
			MWARN("MedBootstrap failed\n");
			return medial::performance::auc_q(preds, y, &weights);
		}
	}
}

void update_mat_weights(MedFeatures &features, float matching_price_ratio,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights) {
	if (pid_time_weights != NULL && !pid_time_weights->empty()) {
		MLOG("using Weights in learn predictor:\n");
		int miss_weights = 0; //default is zero
		features.weights.resize(features.samples.size(), 0);
		for (size_t i = 0; i < features.samples.size(); ++i)
		{
			if (pid_time_weights->find(features.samples[i].id) == pid_time_weights->end()) {
				++miss_weights;
				continue;
			}
			const unordered_map<int, float> &time_weights = pid_time_weights->at(features.samples[i].id);
			if (time_weights.find(features.samples[i].time) == time_weights.end()) {
				++miss_weights;
				continue;
			}
			float weight = time_weights.at(features.samples[i].time);
			features.weights[i] = weight;
		}
		if (miss_weights > 0)
			MWARN("Warning: skipped %d samples (gave weight 0) because no match in match object\n", miss_weights);
		medial::print::print_hist_vec(features.weights, "weights_in_train", "%2.3f");
	}
	else {
		//clear existing weights if has:
		if (matching_price_ratio > 0) //if < 0 the mathcing uses weights - so can't clear it up!
			features.weights.clear();
	}
}

void load_weights(MedModel &model_feat_generator,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights) {
	if (pid_time_weights != NULL && !pid_time_weights->empty()) {
		MLOG("using Weights in learn predictor:\n");
		//populate model_feat_generator.features.weights
		int miss_weights = 0; //default is zero
		model_feat_generator.features.weights.resize(model_feat_generator.features.samples.size(), 0);
		for (size_t i = 0; i < model_feat_generator.features.samples.size(); ++i)
		{
			if (pid_time_weights->find(model_feat_generator.features.samples[i].id) == pid_time_weights->end()) {
				++miss_weights;
				continue;
			}
			const unordered_map<int, float> &time_weights = pid_time_weights->at(model_feat_generator.features.samples[i].id);
			if (time_weights.find(model_feat_generator.features.samples[i].time) == time_weights.end()) {
				++miss_weights;
				continue;
			}
			float weight = time_weights.at(model_feat_generator.features.samples[i].time);
			model_feat_generator.features.weights[i] = weight;
		}
		if (miss_weights > 0)
			MWARN("Warning: skipped %d samples (gave weight 0) because no match in match object\n", miss_weights);
		medial::print::print_hist_vec(model_feat_generator.features.weights, "weights_in_train", "%2.3f");
	}
}

void fit_to_mem_size(MedModel &model, MedSamples &samples) {
	int max_smp = model.get_apply_batch_count();
	int sz = samples.nSamples();
	if (sz > max_smp) {
		MWARN("WARN:: Too Many samples (%d) - down sampling to %d...\n", sz, max_smp);
		medial::process::down_sample_by_pid(samples, max_smp);
		MLOG("Done Down sampling\n");
	}
}

void get_split_mat(
	MedSamples &train_samples, 
	MedSamples &test_samples, 
	const string &model_json, 
	MedPidRepository &rep, 
	float price_mathcing, 
	double match_to_prior,
	MedFeatures &train_mat, 
	MedFeatures &test_mat, 
	MedModel &model_feat_generator,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights, 
	const string &strata_str, 
	const string& matching_json, 
	bool verbose
) 
{
	global_logger.levels[LOG_MED_MODEL] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = MAX_LOG_LEVEL;

	// Perform matching on the train samples
	vector<float> sample_weights;
	commit_matching_general(
		train_samples, 
		price_mathcing, 
		match_to_prior, 
		sample_weights, 
		rep, 
		strata_str, 
		matching_json, 
		verbose
	);

	// Create MedModel
	init_medmodel(model_feat_generator, rep, model_json);
	fit_to_mem_size(model_feat_generator, train_samples);
	
	// Train MedModel on matched samples (after read from json) 
	model_feat_generator.learn(
		rep, 
		&train_samples, 
		MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, 
		MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS
	);

	if (!sample_weights.empty())
		model_feat_generator.features.weights = sample_weights;
	else
		load_weights(model_feat_generator, pid_time_weights);
	
	// Prepare train feature matrix
	train_mat = move(model_feat_generator.features);

	// Apply feature generator to the test matrix
	fit_to_mem_size(model_feat_generator, test_samples);
	model_feat_generator.apply(rep, test_samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	test_mat = move(model_feat_generator.features);
	model_feat_generator.features.clear(); //validate empty to clean memory

	global_logger.levels[LOG_MED_MODEL] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = LOG_DEF_LEVEL;
}


// For each split, take (train,test) samples and convert to (train_mat_for_split,test_mat_for_split) feature matrices
void run_all_splits_mat(
	const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test,
	const string &model_json, 
	MedPidRepository &rep, 
	float price_mathcing, 
	double match_to_prior, 
	const string &strata_str, 
	const string& matching_json, 
	bool verbose,
	unordered_map<string, MedFeatures> &train_mat_for_split, 
	unordered_map<string, MedFeatures> &test_mat_for_split,
	unordered_map<string, MedModel> &model_for_split,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights, 
	bool store_models
) 
{
	/*
	For each split, take (train,test) samples
	and convert to (train_mat_for_split,test_mat_for_split) feature matrices
	*/

	for (const auto &it : train)
	{
		MLOG("Create Mats for %s\n", it.first.c_str());
		MedSamples train_sampels = it.second; //creates copy
		MedSamples test_samples = test.at(it.first);
		MedModel &model_feat_generator = model_for_split[it.first];

		get_split_mat(
			train_sampels, 
			test_samples, 
			model_json, 
			rep, 
			price_mathcing, 
			match_to_prior, 
			train_mat_for_split[it.first], 
			test_mat_for_split[it.first], 
			model_feat_generator, 
			pid_time_weights, 
			strata_str, 
			matching_json, 
			verbose
		);

		if (!store_models)
			model_feat_generator.clear();
	}
	if (!store_models)
		model_for_split.clear();
}

void run_all_splits(
	const unordered_map<string, MedSamples> &train, // maps split_name into a set of train samples
	const unordered_map<string, MedSamples> &test,  // maps split_name into a set of test samples
	const string &model_json,
	MedPidRepository &rep,
	const string &pred_type,                        // 
	const string &pred_args,                        //
	float price_mathcing,
	double match_to_prior,
	const string &strata_str,
	const string& matching_json,
	bool verbose,
	float &auc_test,
	float &auc_train,
	vector<MedSample> &all_samples_collected,
	unordered_map<string, MedModel> &model_for_split,
	const string &bootstrap_params,
	const string &measure,
	bool verbose_summary, 
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights,
	const string &save_pattern
) 
{
	/*

		Loop over all train splits, train separate predictor for each split
		*   Get train/test feature matrices
		*   Perform matching on train
		*   Train feature generator on (matched) train
		*   Prepare train/test feature matrices
		*   Export (matched) train and test samples for split:
		*   Train predictor on the matched train feature matrix
		*   Train predictor on the matched train feature matrix
		*   Apply predictor to the (matched) train matrix
		*   Compute AUC on the predictionsr for(matched) training samples
		*   Apply predictor to the (matched) test matrix
		*   Compute AUC on predictions over test samples using bootstrap
		*   Append AUC for this split to the list of AUCs
			(separately for train and test)
		*   Append a list of test samples for _this_split_ to
		*   Print out AUC for (matched) train and (unmatched) test samples
		*   Compute AUC on union of test samples from all participating splits
		*   Print AUC statistics:
		*		Print AUC computed on union of test samples from all participating splits
		*		Print AUC for each participating split separately
		*		Print average of AUC values (over the splits)
		*   Output AUC computed over a union of test splits as "auc_test"
		*   Output mean AUC computed over (matched) train sets

	*/
	global_logger.levels[LOG_MED_MODEL] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = MAX_LOG_LEVEL;

	all_samples_collected.clear(); // will contain a union of test samples for all participating splits
	vector<float> auc_each_split, auc_train_each;
	vector<float> empty_weight_test;
	
	// Loop over all train splits, train separate predictor for each split
	for (auto &it : train)
	{
		MLOG("Run on %s\n", it.first.c_str());
		MedPredictor *predictor = MedPredictor::make_predictor(pred_type, pred_args);

		// Get train/test feature matrices
		MedSamples train_samples = it.second;	// creates copy
		MedSamples test_samples = test.at(it.first);
		MedFeatures train_mat, test_mat;		// creates copy

		MedModel &curr_model = model_for_split[it.first];

		// Perform matching on train, train feature generator on (matched)train, 
		// prepare train/test feature matrices
		// output feature generator to "curr_model"
		get_split_mat(
			train_samples, 
			test_samples, 
			model_json, 
			rep, 
			price_mathcing, 
			match_to_prior,
			train_mat, 
			test_mat, 
			curr_model, 
			pid_time_weights, 
			strata_str, 
			matching_json, 
			verbose
		);
		
		if (save_pattern.empty())
			curr_model.clear();
		else {
			// export (matched)train and (unmatched)test samples for split:
			char buffer_nm[5000];
			snprintf(buffer_nm, sizeof(buffer_nm), save_pattern.c_str(), it.first.c_str());
			string save_path = string(buffer_nm) + ".train_samples";
			MedSamples tr_save;
			tr_save.import_from_sample_vec(train_mat.samples);
			tr_save.write_to_file(save_path);
			save_path = string(buffer_nm) + ".test_samples";
			MedSamples test_save;
			test_save.import_from_sample_vec(test_mat.samples);
			test_save.write_to_file(save_path);
		}

		// train predictor on the matched train feature matrix 
		predictor->learn(train_mat);

		// Apply predictor to the (matched) train matrix
		predictor->predict(train_mat);
		
		// Compute AUC on the predictionsr for(matched) training samples using bootstrap
		float auc_train = auc_samples(train_mat.samples, train_mat.weights, bootstrap_params, measure);

		// Apply predictor to the (matched) test matrix
		predictor->predict(test_mat);

		// Compute AUC on predictions over test samples using bootstrap
		float auc = auc_samples(test_mat.samples, empty_weight_test, bootstrap_params, measure);

		// Append AUC for this split to the list of AUCs (separately for train and test)
		auc_each_split.push_back(auc);
		auc_train_each.push_back(auc_train);

		// Append a list of test samples for _this_split_ to "all_samples_collected"
		all_samples_collected.insert(all_samples_collected.end(), test_mat.samples.begin(), test_mat.samples.end());

		// Print out AUC for (matched) train and (unmatched) test samples
		if (verbose)
			MLOG("AUC in %s:: train %2.3f, test %2.3f\n", it.first.c_str(), auc_train, auc);

		if (!save_pattern.empty()) { 
			// insert predictor into the model and export the resulting model to file
			if (curr_model.predictor != NULL)
				delete curr_model.predictor;
			curr_model.set_predictor(predictor);
			char buffer_nm[5000];
			snprintf(buffer_nm, sizeof(buffer_nm), save_pattern.c_str(), it.first.c_str());
			string save_path = string(buffer_nm);
			curr_model.write_to_file(save_path);
			curr_model.clear();
		}
		else
			delete predictor; //clear memory
	}

	// Compute AUC on union of test samples from all participating splits 
	float auc_all = auc_samples(all_samples_collected, empty_weight_test, bootstrap_params, measure);

	// Print AUC statistics
	if (verbose_summary) {
		// Print AUC computed on union of test samples from all participating splits
		string all_aucs = "all_auc::" + medial::print::print_obj(auc_all, "%2.3f");
		
		// Print AUC for each participating split separately
		float avg = 0;
		for (size_t i = 0; i < auc_each_split.size(); ++i) {
			all_aucs += " | split_" + to_string(i) + "::" + medial::print::print_obj(auc_each_split[i], "%2.3f");
			avg += auc_each_split[i];
		}

		// Print average of AUC values (over the splits)
		if (auc_each_split.size() > 0)
			avg /= auc_each_split.size();
		all_aucs += " | average::" + medial::print::print_obj(avg, "%2.3f");
		MLOG("%s\n", all_aucs.c_str());
	}

	// output AUC computed over a union of test splits as "auc_test"
	auc_test = auc_all;
	// output mean AUC computed over (matched) train sets
	auc_train = (float)medial::stats::mean_without_cleaning(auc_train_each);

	// Set logger levels to what they were
	global_logger.levels[LOG_MED_MODEL] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = LOG_DEF_LEVEL;
	//global_logger.levels[LOG_MEDALGO] = LOG_DEF_LEVEL;
}

void run_all_splits(
	const unordered_map<string, MedFeatures> &train_mat,
	const unordered_map<string, MedFeatures> &test_mat, 
	const string &pred_type, 
	const string &pred_args,
	float &auc_test, 
	float &auc_train, 
	vector<MedSample> &all_samples_collected,
	const string &bootstrap_params, 
	const string &measure, 
	bool verbose, 
	bool verbose_summary
) 
{
	/*
		Loop over splits
		*   Load (matched)train and test feature matrices for current split
		*   Train predictor on the matched train feature matrix
		*   Apply predictor to the (matched) train matrix
		*   Compute AUC on the predictionsr for(matched) training samples
		*   Apply predictor to the test matrix
		*   Compute AUC on predictions over test samples using bootstrap
		*   Append AUC for this split to the list of AUCs
		(separately for train and test)
		*   Append a list of test samples for _this_split_ to
		*   Print out AUC for (matched) train and (unmatched) test samples
		*   Compute AUC on union of test samples from all participating splits
		*   Print AUC statistics
		*   	Print AUC computed on union of test samples from all participating splits
		*   	Print AUC for each participating split separately
		*   	Print average of AUC values (over the splits)

		*   output AUC computed over a union of test splits as "auc_test"
		*   output mean AUC computed over (matched) train sets
	*/

	global_logger.levels[LOG_MED_MODEL] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = MAX_LOG_LEVEL;
	//global_logger.levels[LOG_MEDALGO] = MAX_LOG_LEVEL;

	all_samples_collected.clear();
	vector<float> auc_each_split, auc_train_each;
	vector<float> empty_weight_test;

	// Loop over splits
	for (auto &it : train_mat)
	{
		MLOG("Run on %s\n", it.first.c_str());
		
		// Initialize predictor
		MedPredictor *predictor = MedPredictor::make_predictor(pred_type, pred_args);

		// Load (matched)train and test feature matrices
		const MedFeatures &train_sampels = it.second; //creates copy
		const MedFeatures &test_sampels = test_mat.at(it.first);

		// Train predictor on (matched) train feature matrix
		predictor->learn(train_sampels);
		

		MedMat<float> train_m, test_m;
		train_sampels.get_as_matrix(train_m);

		test_sampels.get_as_matrix(test_m);
		vector<float> train_preds, test_preds;

		// Apply predictor to the (matched) train matrix
		predictor->predict(train_m, train_preds);

		//populate train_sampels with preds:
		vector<MedSample> train_col = train_sampels.samples;
		for (size_t i = 0; i < train_col.size(); ++i)
			train_col[i].prediction = { train_preds[i] };
		
		// Compute AUC on the predictionsr for(matched) training samples
		float auc_train = auc_samples(train_col, empty_weight_test, bootstrap_params, measure);


		// Apply predictor to the (matched) test matrix
		predictor->predict(test_m, test_preds);
		
		delete predictor; //clear memory
		
		vector<MedSample> test_col = test_sampels.samples;
		for (size_t i = 0; i < test_col.size(); ++i)
			test_col[i].prediction = { test_preds[i] };

		// Compute AUC on the predictionsr for test samples
		float auc = auc_samples(test_col, empty_weight_test, bootstrap_params, measure);
		
		//  Append AUC for this split to the list of AUCs (separately for train and test)
		auc_each_split.push_back(auc);
		auc_train_each.push_back(auc_train);
		
		for (size_t i = 0; i < test_sampels.samples.size(); ++i)
		{
			all_samples_collected.push_back(test_sampels.samples[i]);
			all_samples_collected.back().prediction = { test_preds[i] };
		}
		
		if (verbose)
			MLOG("AUC in %s:: train %2.3f, test %2.3f\n", it.first.c_str(), auc_train, auc);
	}

	// Compute AUC on union of test samples from all participating splits
	float auc_all = auc_samples(all_samples_collected, empty_weight_test, bootstrap_params, measure);

	// Print AUC statistics
	if (verbose_summary) {
		// Print AUC computed on union of test samples from all participating splits
		string all_aucs = "all_auc(bootstrap)::" + medial::print::print_obj(auc_all, "%2.3f");
		float avg = 0;
		for (size_t i = 0; i < auc_each_split.size(); ++i) {
			//Print AUC for each participating split separately
			all_aucs += " | split_" + to_string(i) + "::" + medial::print::print_obj(auc_each_split[i], "%2.3f");
			avg += auc_each_split[i];
		}

		if (auc_each_split.size() > 0)
			avg /= auc_each_split.size();

		// Print average of AUC values (over the splits)
		all_aucs += " | average::" + medial::print::print_obj(avg, "%2.3f");
		MLOG("%s\n", all_aucs.c_str());
	}

	auc_test = auc_all;
	auc_train = (float)medial::stats::mean_without_cleaning(auc_train_each);
	global_logger.levels[LOG_MED_MODEL] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = LOG_DEF_LEVEL;
	//global_logger.levels[LOG_MEDALGO] = LOG_DEF_LEVEL;
}

void write_model_selection(const unordered_map<string, float> &model_loss,
	const unordered_map<string, float> &model_loss_train, const string &save_path,
	const string &measure_name, double generelization_error_factor) {
	ofstream fw(save_path);
	if (!fw.good())
		MTHROW_AND_ERR("IOError: can't write model_selection file\n");
	char buffer[5000];
	fw << "model_name" << "\t" << measure_name << "_test" << "\t" << measure_name << "_on_train" << endl;
	//print in sorted way by desc model_loss values and than by model_loss_train asc values:
	vector<pair<string, vector<double>>> sorted(model_loss.size());
	int i = 0;
	for (auto it = model_loss.begin(); it != model_loss.end(); ++it) {
		sorted[i].first = it->first;
		float test_pref = it->second;
		float generalization_error = model_loss_train.at(it->first) - it->second;
		if (generalization_error < 0)
			generalization_error = 0;
		if (generelization_error_factor != 0)
			test_pref = test_pref - (generalization_error / generelization_error_factor);
		sorted[i].second = { -test_pref , -it->second, -model_loss_train.at(it->first) };
		++i;
	}
	sort(sorted.begin(), sorted.end(), [](pair<string, vector<double>> a, pair<string, vector<double>> b) {
		int pos = 0;
		while (pos < a.second.size() &&
			a.second[pos] == b.second[pos])
			++pos;
		if (pos >= a.second.size())
			return false;
		return b.second[pos] > a.second[pos];
	});
	for (size_t ii = 0; ii < sorted.size(); ++ii)
	{
		snprintf(buffer, sizeof(buffer), "%s\t%2.4f\t%2.4f\n",
			sorted[ii].first.c_str(), sorted[ii].second[1], sorted[ii].second[2]);
		string line = string(buffer);
		fw << line;
	}
	fw.close();
}

void read_ms_config(const string &file_path, const string &base_model,
	vector<MedPredictor *> &all_configs) {
	ifstream fr(file_path);
	if (!fr.good())
		MTHROW_AND_ERR("IOError: can't read model selection file %s\n", file_path.c_str());
	string line;
	vector<string> all_init = { "" };
	all_configs.clear();
	while (getline(fr, line)) {
		boost::trim(line);
		if (line.empty() || line[0] == '#')
			continue;
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("="));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Bad Format in line \"%s\"\n", line.c_str());
		string param_name = boost::trim_copy(tokens[0]);
		string params_options = boost::trim_copy(tokens[1]);
		vector<string> opts;
		boost::split(opts, params_options, boost::is_any_of(","));
		int base_sz = (int)all_init.size();
		all_init.resize(base_sz * opts.size()); //cartezian multiply of options. copy the current options:
		for (size_t i = 1; i < opts.size(); ++i) //the first is already OK:
			for (size_t j = 0; j < base_sz; ++j)
				all_init[i*base_sz + j] = all_init[j];
		for (size_t i = 0; i < opts.size(); ++i) //the first is already OK:
			for (size_t j = 0; j < base_sz; ++j)
				all_init[i*base_sz + j] += param_name + "=" + opts[i] + ";";
	}
	fr.close();
	//I have string line to init all models:
	MLOG("I have %d models in model selection.\n", (int)all_init.size());

	int curr_lev = global_logger.levels[LOG_MEDALGO];
	global_logger.levels[LOG_MEDALGO] = MAX_LOG_LEVEL;
	all_configs.resize(all_init.size());
	for (size_t i = 0; i < all_init.size(); ++i)
		all_configs[i] = MedPredictor::make_predictor(base_model, all_init[i]);
	global_logger.levels[LOG_MEDALGO] = curr_lev;
}

void read_selected_model(const string &selected_mode_path,
	string &predictor_name, string &predictor_params) {
	if (file_exists(selected_mode_path)) {
		ifstream fr(selected_mode_path);
		if (!fr.good())
			MTHROW_AND_ERR("IOError: can't read selected model\n");
		string line;
		predictor_name = "";
		predictor_params = "";
		while (getline(fr, line)) {
			boost::trim(line);
			if (line.empty() || line[0] == '#')
				continue;
			vector<string> tokens;
			boost::split(tokens, line, boost::is_any_of("\t"));
			if (tokens.size() != 2)
				MTHROW_AND_ERR("wrong format in line \"%s\". searching for \"TAB\"", line.c_str());
			boost::trim(tokens[0]);
			boost::trim(tokens[1]);
			if (tokens[0] == "predictor_params")
				predictor_params += tokens[1];
			else if (tokens[0] == "predictor_name")
				predictor_name = tokens[1];
			else
				MTHROW_AND_ERR("wrong format in line \"%s\"\n"
					". command was \"%s\" and should be predictor_name|predictor_params",
					line.c_str(), tokens[0].c_str());
		}
		fr.close();
		if (predictor_name.empty() || predictor_params.empty())
			MTHROW_AND_ERR("missing predictor_params or predictor lines in file");
	}
	else
		MTHROW_AND_ERR("IOError: can't read selected model in %s\n",
			selected_mode_path.c_str());
}

string clean_model_prefix(const string &s) {
	if (s.find(":") == string::npos)
		return s;
	string text = boost::trim_copy(s.substr(s.find(":") + 1));
	text.erase(remove_if(text.begin(), text.end(), ::isspace), text.end());
	return text;
}

bool can_skip_already_done(const vector<full_train_args> &already_done, const string &modelName,
	float &avg_auc_test, float &avg_auc_train) {
	bool found = false;
	avg_auc_test = -1;
	avg_auc_train = -1;
	if (!already_done.empty()) {
		string predictor_args = clean_model_prefix(modelName);

		for (int i = 0; i < already_done.size() && !found; ++i)
			if (boost::trim_copy(already_done[i].predictor_args) == predictor_args) {
				found = true;
				avg_auc_test = already_done[i].auc;
				avg_auc_train = already_done[i].auc_train;
			}
	}
	return found;
}

//run on matrixes
string runOptimizerModel(const unordered_map<string, MedFeatures> &train_mat,
	const unordered_map<string, MedFeatures> &test_mat, MedModel &model_feat_generator, const string &model_json, MedPidRepository &rep,
	const string &model_type, const vector<MedPredictor *> &all_models_config,
	unordered_map<string, float> &model_loss, unordered_map<string, float> &model_loss_train, const string &log_file, const unordered_map<int, unordered_map<int, float>> *pid_time_weights,
	const vector<full_train_args> &already_done, const string &bootstrap_params, const string &measure,
	double generelization_error_factor, bool debug) {

	ofstream log_f(log_file, ios::app);
	if (!log_f.good())
		MTHROW_AND_ERR("Error can't write log file %s\n", log_file.c_str());

	float maxVal = 0;
	string bestParams = "";
	MedProgress tot_done("OptimizerModel", (int)all_models_config.size(), 30, 1);

	//#pragma	omp parallel for
	for (int i = 0; i < all_models_config.size(); ++i) {
		string modelName = medial::models::getParamsInfraModel(all_models_config[i]);
		modelName.erase(remove_if(modelName.begin(), modelName.end(), ::isspace), modelName.end());
		//check if can skip:
		float avg_auc_test, avg_auc_train;
		bool skipped = false;
		if (!can_skip_already_done(already_done, modelName, avg_auc_test, avg_auc_train)) {
			//fill model_loss, model_loss_train - goto mutex section
			vector<MedSample> all_col_samples;
			string model_args = clean_model_prefix(modelName);
			unordered_map<string, MedModel> model_for_split;
			run_all_splits(train_mat, test_mat, model_type, model_args, avg_auc_test, avg_auc_train, all_col_samples,
				bootstrap_params, measure, debug, true);

		}
		else
			skipped = true;
		delete all_models_config[i]; //clear memory
		MLOG("%s has auc_test=%2.4f on train %2.4f\n", modelName.c_str(), avg_auc_test, avg_auc_train);
		log_f << modelName.c_str() << "\t" << avg_auc_test << "\t" << avg_auc_train << endl;

#pragma omp critical
		{
			model_loss[modelName] = avg_auc_test;
			model_loss_train[modelName] = avg_auc_train;
			float general_err_bound = avg_auc_train - avg_auc_test;
			if (general_err_bound < 0)
				general_err_bound = 0;
			float best_metric_calc = avg_auc_test;
			if (generelization_error_factor != 0)
				best_metric_calc = avg_auc_test - (general_err_bound / generelization_error_factor);
			if (best_metric_calc > maxVal || bestParams.empty()) {
				maxVal = best_metric_calc;
				bestParams = modelName;
			}
		}
		if (!skipped)
			tot_done.update();
		else
			tot_done.skip_update();
	}
	MLOG("Done! best score = %2.4f with %s\n", maxVal, bestParams.c_str());
	log_f.close();
	return bestParams;
}

string runOptimizerModel(
	const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test, 
	MedModel &model_feat_generator, 
	const string &model_json, 
	MedPidRepository &rep,
	const string &model_type, 
	const vector<MedPredictor *> &all_models_config,
	unordered_map<string, float> &model_loss, 
	unordered_map<string, float> &model_loss_train, 
	float price_mathcing, 
	double match_to_prior,
	const string &strata_str, 
	const string& matching_json, 
	const string &log_file, 
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights,
	const string &bootstrap_params, 
	const string &measure, 
	double generelization_error_factor, 
	bool debug
) 
{

	/*

		Input:
		======

		all_models_config keeps all configurations to test

		Description:
		============

		*	For each split, take(train, test) samples
		and convert to (train_mat_for_split, test_mat_for_split)
		feature matrices

		*	Loop over all configurations
		*	Loop over all splits, train separate predictor for each split
		*	Compute AVERAGE train AUC over all splits
		*	Compute AVERAGE test AUC over all splits

		*	Select best model based on AVERAGE test AUC

		*	Return parameters of the best model
		    (that is, the best configuration )

	*/
	ofstream log_f(log_file);
	if (!log_f.good())
		MTHROW_AND_ERR("Error can't write log file %s\n", log_file.c_str());

	unordered_map<string, MedFeatures> train_mat, test_mat;
	unordered_map<string, MedModel> models;

	// For each split, take(train, test) samples
	// and convert to(train_mat_for_split, test_mat_for_split) feature matrices
	run_all_splits_mat(
		train, 
		test, 
		model_json, 
		rep,
		price_mathcing, 
		match_to_prior, 
		strata_str, 
		matching_json, 
		false, 
		train_mat, 
		test_mat, 
		models, 
		pid_time_weights, 
		false
	);

	float maxVal = 0;
	string bestParams = "";
	MedProgress tot_done("OptimizerModel", (int)all_models_config.size(), 30, 1);

	//#pragma	omp parallel for

	// Loop over all configurations
	for (int i = 0; i < all_models_config.size(); ++i) {

		string modelName = medial::models::getParamsInfraModel(all_models_config[i]);
		modelName.erase(remove_if(modelName.begin(), modelName.end(), ::isspace), modelName.end());
		float avg_auc_test, avg_auc_train;
		vector<MedSample> all_col_samples;
		string model_args = clean_model_prefix(modelName);
		unordered_map<string, MedModel> model_for_split;

		// Loop over all splits, train separate predictor for each split
		run_all_splits(
			train_mat, 
			test_mat, 
			model_type, 
			model_args, 
			avg_auc_test, 
			avg_auc_train, 
			all_col_samples,
			bootstrap_params, 
			measure, 
			debug, 
			true
		);

		delete all_models_config[i]; //clear memory

		MLOG("%s has auc_test=%2.4f on train %2.4f\n", modelName.c_str(), avg_auc_test, avg_auc_train);
		log_f << modelName.c_str() << "\t" << avg_auc_test << "\t" << avg_auc_train << endl;

		// If current model is the best so far, update "bestParams" and "maxVal"
#pragma omp critical
		{
			model_loss[modelName] = avg_auc_test;
			model_loss_train[modelName] = avg_auc_train;
			float general_err_bound = avg_auc_train - avg_auc_test;
			if (general_err_bound < 0)
				general_err_bound = 0;
			float best_metric_calc = avg_auc_test;
			if (generelization_error_factor != 0)
				best_metric_calc = avg_auc_test - (general_err_bound / generelization_error_factor);
			if (best_metric_calc > maxVal || bestParams.empty()) {
				maxVal = best_metric_calc;
				bestParams = modelName;
			}
		}
		tot_done.update();
	}
	MLOG("Done! best score = %2.4f with %s\n", maxVal, bestParams.c_str());
	log_f.close();

	// Return best model parameters
	return bestParams;
}

void write_progress_header(const string &folder, const string &fname, const full_train_args &train_args) {
	string progress_file_path = folder + path_sep() + "model_selection." + fname + ".progress.log";
	ofstream fw(progress_file_path);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open %s for writing\n", progress_file_path.c_str());

	full_train_args copy_params = train_args;
	copy_params.predictor_args = "";
	fw << "HEADER" << "\t" << copy_params.to_string(true) << endl;
	fw.close();
}

void load_all_progress_files(const string &folder, vector<full_train_args> &already_done) {
	boost::filesystem::path p(folder);
	boost::regex selection_model_pattern("model_selection\\..+\\.progress\\.log"); //no need to read "full" - if has one will skip externally.

	for (auto& entry : boost::make_iterator_range(boost::filesystem::directory_iterator(p), {})) {
		string file_full_path = entry.path().string();
		string file_name = entry.path().filename().string();
		bool is_prog_file = boost::regex_match(file_name, selection_model_pattern);
		if (!is_prog_file)
			continue;
		string line;
		ifstream fr(file_full_path);
		if (!fr.good())
			MTHROW_AND_ERR("Error can't open file %s for reading\n", file_full_path.c_str());
		getline(fr, line);
		if (!boost::starts_with(line, "HEADER")) {
			fr.close();
			MLOG("skip file %s - old format - no header\n", file_full_path.c_str());
			continue;
		}
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Error - bad header format in %s\n%s\n",
				file_full_path.c_str(), line.c_str());
		const string &t_args = tokens[1];
		full_train_args r;
		r.parse_only_args(t_args, file_full_path);
		//lets's continue reading and update predictor_args:
		while (getline(fr, line)) {
			tokens.clear();
			boost::split(tokens, line, boost::is_any_of("\t"));
			if (tokens.size() != 3)
				MTHROW_AND_ERR("Error bad file format (%s). expecting 3 tokens. got:\n%s\n",
					file_full_path.c_str(), line.c_str());
			string predictor_str = clean_model_prefix(tokens[0]);
			r.predictor_args = predictor_str;
			r.auc = med_stof(tokens[1]);
			r.auc_train = med_stof(tokens[2]);
			//read AUC
			already_done.push_back(r);
		}

		fr.close();
	}
}

void write_existings(const string &folder, const string &fname, const full_train_args &train_arg,
	const vector<full_train_args> &all_done_non_filter, vector<full_train_args> &relevent_filtered) {
	string progress_file_path = folder + path_sep() + "model_selection." + fname + ".progress.log";
	//filter releveant and write them:

	for (size_t i = 0; i < all_done_non_filter.size(); ++i)
		if (train_arg.compare(all_done_non_filter[i]))
			relevent_filtered.push_back(all_done_non_filter[i]);

	/* 	no need to write it here
	ofstream fw(progress_file_path, ios::app);
	if (!fw.good())
		MTHROW_AND_ERR("Error can't open %s for writing\n", progress_file_path.c_str());

	//format: predictor TAB test_AUC TAB train_AUC

	string predictor_prefix = "";
	if (!relevent_filtered.empty()) {
		MedPredictor *tmp = MedPredictor::make_predictor(relevent_filtered.front().predictor_type);
		predictor_prefix = predictor_type_to_name[tmp->classifier_type];
		delete tmp;
	}


	for (size_t i = 0; i < relevent_filtered.size(); ++i)
	{
		string predictor_token = predictor_prefix + ": " + relevent_filtered[i].predictor_args;
		fw << predictor_token << "\t" << relevent_filtered[i].auc << "\t" << relevent_filtered[i].auc_train << "\n";
	}

	fw.close();
	*/
}

//but on matrix
float load_selected_model(
	MedPredictor *&model, 
	const unordered_map<string, MedFeatures> &train,
	const unordered_map<string, MedFeatures> &test, 
	MedModel &model_feat_generator, const string &model_json, 
	MedPidRepository &rep, 
	const string &ms_configs_file, 
	const string &ms_predictor_name,
	const string &results_folder_name, 
	const string &config_folder_path, 
	float price_mathcing, 
	const string &strata_str, 
	const string& matching_json,
	const string &fname, 
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights,
	bool override_existing_results, 
	const full_train_args &train_args, 
	const string &bootstrap_params, 
	const string &measure,
	double generelization_error_factor, 
	bool debug
) 
{
	float res = MED_MAT_MISSING_VALUE;
	if (config_folder_path != "/dev/null" && file_exists(config_folder_path + path_sep() + "selected_model." + fname + ".params")) {
		string predictor_name, predictor_params;
		read_selected_model(config_folder_path + path_sep() + "selected_model." + fname + ".params", predictor_name, predictor_params);
		model = MedPredictor::make_predictor(predictor_name, predictor_params);
	}
	else {
		vector<MedPredictor *> all_configs;
		read_ms_config(ms_configs_file, ms_predictor_name, all_configs);

		unordered_map<string, float> model_loss, model_loss_train;
		string progress_file_path = results_folder_name + path_sep() + "model_selection." + fname + ".progress.log";

		vector<full_train_args> already_done;
		if (!override_existing_results) {
			vector<full_train_args> all_done_non_filter;
			load_all_progress_files(results_folder_name, all_done_non_filter);
			write_progress_header(results_folder_name, fname, train_args);
			write_existings(results_folder_name, fname, train_args, all_done_non_filter, already_done);
			MLOG("found %zu runs in total before filter, can use %zu runs after filter\n",
				all_done_non_filter.size(), already_done.size());
		}
		else
			write_progress_header(results_folder_name, fname, train_args);

		//TODO: see when we can skip experiment from already_done:
		string bestConfig = runOptimizerModel(train, test, model_feat_generator, model_json, rep, ms_predictor_name,
			all_configs, model_loss, model_loss_train, progress_file_path,
			pid_time_weights, already_done, bootstrap_params, measure, generelization_error_factor, debug);
		write_model_selection(model_loss, model_loss_train,
			results_folder_name + path_sep() + "model_selection." + fname + ".full.log",
			measure, generelization_error_factor);

		float best_loss_test = model_loss.at(bestConfig);
		float best_loss_train = model_loss_train.at(bestConfig);
		res = best_loss_test;
		bestConfig = clean_model_prefix(bestConfig);
		//write selection to file
		if (config_folder_path != "/dev/null") {
			ofstream fw(config_folder_path + path_sep() + "selected_model." + fname + ".params");
			if (!fw.good())
				MTHROW_AND_ERR("IOError: can't write selected model\n");
			fw << "predictor_name" << "\t" << ms_predictor_name << endl;
			fw << "predictor_params" << "\t" << bestConfig << endl;
			fw.close();
		}
		MLOG("Found best model for \"%s\" with loss_val=%2.4f, loss_val_train=%2.4f with those params:\n%s\n",
			ms_predictor_name.c_str(), best_loss_test, best_loss_train, bestConfig.c_str());

		model = MedPredictor::make_predictor(ms_predictor_name, bestConfig);
	}
	return res;
}

float load_selected_model(
	MedPredictor *&model, 
	const unordered_map<string, MedSamples> &train,
	const unordered_map<string, MedSamples> &test, 
	MedModel &model_feat_generator, 
	const string &model_json, 
	MedPidRepository &rep, 
	const string &ms_configs_file, 
	const string &ms_predictor_name,
	const string &results_folder_name, 
	const string &config_folder_path, 
	float price_mathcing, 
	double match_to_prior, 
	const string &strata_str,
	const string& matching_json,
	const string &fname, 
	const string &bootstrap_params, 
	const string &measure,
	double generelization_error_factor,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights, 
	bool debug
) {
	/*
	*	Load model parameters from "fname", if the file exists
	*	Otherwise load parameters form "ms_configs_file" (e.g. depth=3,4,5)
	*	Select optimal model via call to "runOptimizerModel()"
	*	Export optimal model performance to a logfile
	*	Return predictor initialized with the best parameter configuration
	*/

	float res = MED_MAT_MISSING_VALUE;
	// Load model parameters from "fname", if the file exists
	if (config_folder_path != "/dev/null" && file_exists(config_folder_path + path_sep() + "selected_model." + fname + ".params")) {
		string predictor_name, predictor_params;
		read_selected_model(config_folder_path + path_sep() + "selected_model." + fname + ".params", predictor_name, predictor_params);
		model = MedPredictor::make_predictor(predictor_name, predictor_params);
	}
	else {
		// otherwise load parameters form "ms_configs_file" (e.g. depth=3,4,5)
		vector<MedPredictor *> all_configs;
		read_ms_config(ms_configs_file, ms_predictor_name, all_configs);

		// select optimal model via a call to runOptimizerModel()
		unordered_map<string, float> model_loss, model_loss_train;
		string bestConfig = runOptimizerModel(
			train, 
			test, 
			model_feat_generator, 
			model_json, 
			rep, 
			ms_predictor_name,
			all_configs, 
			model_loss, 
			model_loss_train, 
			price_mathcing, 
			match_to_prior, 
			strata_str, 
			matching_json, 
			results_folder_name + path_sep() + "model_selection." + fname + ".progress.log",
			pid_time_weights, 
			bootstrap_params,
			measure, 
			generelization_error_factor, 
			debug
		);

		// export optimal model performance to a logfile
		write_model_selection(
			model_loss, 
			model_loss_train,
			results_folder_name + path_sep() + "model_selection." + fname + ".full.log", 
			measure,
			generelization_error_factor);

		float best_loss_test = model_loss.at(bestConfig);
		float best_loss_train = model_loss_train.at(bestConfig);
		res = best_loss_test;
		bestConfig = clean_model_prefix(bestConfig);
		//write selection to file
		if (config_folder_path != "/dev/null") {
			ofstream fw(config_folder_path + path_sep() + "selected_model." + fname + ".params");
			if (!fw.good())
				MTHROW_AND_ERR("IOError: can't write selected model\n");
			fw << "predictor_name" << "\t" << ms_predictor_name << endl;
			fw << "predictor_params" << "\t" << bestConfig << endl;
			fw.close();
		}
		MLOG("Found best model for \"%s\" with loss_val=%2.4f, loss_val_train=%2.4f with those params:\n%s\n",
			ms_predictor_name.c_str(), best_loss_test, best_loss_train, bestConfig.c_str());

		// initialize model with the best configuration
		model = MedPredictor::make_predictor(ms_predictor_name, bestConfig);
	}
	return res;
}

void flat_samples(const unordered_map<string, MedSamples> &train, MedSamples &flat) {
	unordered_set<int> seen_pids;
	flat.clear();
	for (const auto &it : train)
	{
		const MedSamples &bucket = it.second;
		for (size_t i = 0; i < bucket.idSamples.size(); ++i)
			if (seen_pids.find(bucket.idSamples[i].id) == seen_pids.end()) {
				seen_pids.insert(bucket.idSamples[i].id);
				flat.idSamples.push_back(bucket.idSamples[i]);
			}
	}
	flat.sort_by_id_date();
}

void train_model(
	MedPredictor &model, 
	MedSamples &flat_train,
	const unordered_map<string, MedSamples> &train,
	MedModel &model_feat_generator, 
	const string &model_json, 
	MedPidRepository &rep,
	float matching_ratio, 
	double match_to_prior, 
	const string &strata_str, 
	const string& matching_json,
	const unordered_map<int, unordered_map<int, float>> *pid_time_weights
) 
{
	/*
		*	Merge training samples from all the splits
		*	Perform matching on all the training samples
		*	Train the feature generator
		*	 Set samples weights according to "matching"
		*   Train the model

	*/

	// Merge training samples from all the splits
	flat_samples(train, flat_train);

	// Perform matching on all the training samples
	vector<float> sample_weights;
	commit_matching_general(flat_train, matching_ratio, match_to_prior, sample_weights, rep, strata_str, matching_json, true);

	// Train the feature generator
	fit_to_mem_size(model_feat_generator, flat_train);
	init_medmodel(model_feat_generator, rep, model_json);
	model_feat_generator.learn(
		rep, 
		&flat_train,
		MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, 
		MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS
	);

	// set samples weights according to matching 
	if (!sample_weights.empty())
		model_feat_generator.features.weights = sample_weights;
	else
		load_weights(model_feat_generator, pid_time_weights);
	
	// train the model
	model.learn(
		model_feat_generator.features
	);
}

bool need_fp(FeatureProcessor *fp, const unordered_set<string> &selected_sigs, string &needed_exm) {
	vector<string> all_names;
	fp->get_feature_names(all_names);
	bool needed_pr = false;
	needed_exm = "";
	for (size_t i = 0; i < all_names.size() && !needed_pr; ++i)
	{
		string strip_name = all_names[i];
		if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
			strip_name = strip_name.substr(strip_name.find(".") + 1);
		if (selected_sigs.find(strip_name) != selected_sigs.end()) {
			needed_pr = true;
			needed_exm = all_names[i];
		}
	}
	return needed_pr;
}

void shrink_med_model(MedModel &mod, const unordered_set<string> &feature_selection_set) {
	if (feature_selection_set.empty())
		return;
	unordered_set<string> selected_sigs; //apply feature selection on model
	for (auto it = feature_selection_set.begin(); it != feature_selection_set.end(); ++it)
	{
		string strip_name = *it;
		if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
			strip_name = strip_name.substr(strip_name.find(".") + 1);
		selected_sigs.insert(strip_name);
	}
	bool add_age = selected_sigs.find("Age") == selected_sigs.end();
	if (add_age)
		selected_sigs.insert("Age");
	bool add_gender = selected_sigs.find("Gender") == selected_sigs.end();
	if (add_gender)
		selected_sigs.insert("Gender");

	//remove processors
	for (auto it = mod.feature_processors.begin(); it != mod.feature_processors.end();)
	{
		string needed_exm;
		bool needed_pr = need_fp(*it, selected_sigs, needed_exm);

		if (!needed_pr) {
			delete *it; //release memory
			it = mod.feature_processors.erase(it);
			continue;
		}
		else {
			//check if multi - if multi - check inside:
			if ((*it)->processor_type != FeatureProcessorTypes::FTR_PROCESS_MULTI) {
				unordered_set<string> out_req, in_req;
				out_req.insert(needed_exm);
				(*it)->update_req_features_vec(out_req, in_req);
				for (const string &s_name : in_req)
				{
					string strip_name = s_name;
					if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
						strip_name = strip_name.substr(strip_name.find(".") + 1);
					selected_sigs.insert(strip_name);
				}
			}
			else {
				MultiFeatureProcessor *multi_p = ((MultiFeatureProcessor *)(*it));
				vector<int> selected_idxs;
				for (size_t i = 0; i < multi_p->processors.size(); ++i)
				{
					string needed_exm_i;
					bool needed_pr_i = need_fp(multi_p->processors[i], selected_sigs, needed_exm_i);
					if (needed_pr_i)
						selected_idxs.push_back((int)i);
					else {
						delete multi_p->processors[i];
						multi_p->processors[i] = NULL;
					}
				}
				//remove all - shouldn't happen
				if (selected_idxs.empty()) {
					delete *it; //release memory
					it = mod.feature_processors.erase(it);
					continue;
				}
				else {
					vector<FeatureProcessor *> _int_list(selected_idxs.size());
					for (size_t i = 0; i < selected_idxs.size(); ++i)
						_int_list[i] = multi_p->processors[selected_idxs[i]];
					multi_p->processors = move(_int_list);

					//run again:
					need_fp(*it, selected_sigs, needed_exm);
					unordered_set<string> out_req, in_req;
					out_req.insert(needed_exm);
					(*it)->update_req_features_vec(out_req, in_req);
					for (const string &s_name : in_req)
					{
						string strip_name = s_name;
						if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
							strip_name = strip_name.substr(strip_name.find(".") + 1);
						selected_sigs.insert(strip_name);
					}
				}
			}
		}
		++it;
	}

	unordered_set<string> needed_sigs;
	//original names:
	vector<FeatureGenerator *> filterd_gen;
	for (size_t i = 0; i < mod.generators.size(); ++i) {
		bool keep_generator = false;
		for (const string &nm : mod.generators[i]->names)
		{
			string strip_name = nm;
			if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
				strip_name = strip_name.substr(strip_name.find(".") + 1);
			if (selected_sigs.find(strip_name) != selected_sigs.end())
				keep_generator = true;
		}
		if (keep_generator) {
			filterd_gen.push_back(mod.generators[i]);
			mod.generators[i]->get_required_signal_names(needed_sigs);
		}
	}
	vector<string> needed_sigs_vec(needed_sigs.begin(), needed_sigs.end());
	filter_rep_processors(needed_sigs_vec, &mod.rep_processors);
	//remove generators:
	mod.generators.swap(filterd_gen);


	MLOG("generators %d fp %d\n", (int)mod.generators.size(), (int)mod.feature_processors.size());
}

void commit_selection(MedFeatures &data, const unordered_set<string> &final_list) {
	unordered_set<string> clean_set_names;
	vector<string> origianl_names;
	data.get_feature_names(origianl_names);
	for (auto it = final_list.begin(); it != final_list.end(); ++it)
	{
		string clean_name = *it;
		if (boost::starts_with(clean_name, "FTR_"))
			clean_name = clean_name.substr(clean_name.find(".") + 1);
		clean_set_names.insert(clean_name);
	}
	for (auto it = data.data.begin(); it != data.data.end();) {
		string clean_name = it->first;
		if (boost::starts_with(clean_name, "FTR_"))
			clean_name = clean_name.substr(clean_name.find(".") + 1);
		if (clean_set_names.find(clean_name) == clean_set_names.end())   //not found - remove
			it = data.data.erase(it);
		else
			++it;
	}
	//check final_list size is same same of data:
	if (data.data.size() != final_list.size()) {
		unordered_set<string> data_names;
		for (auto it = data.data.begin(); it != data.data.end(); ++it) {
			string clean_name = it->first;
			if (boost::starts_with(clean_name, "FTR_"))
				clean_name = clean_name.substr(clean_name.find(".") + 1);
			data_names.insert(clean_name);
		}
		//print diff between lists:
		for (const string &ftr : clean_set_names)
			if (data_names.find(ftr) == data_names.end()) {

				MWARN("Warning: Matrix is missing feature %s\n", ftr.c_str());
				int idx = find_in_feature_names(origianl_names, ftr, false);
				if (idx > 0)
					MWARN("Maybe you meant feature %s\n", origianl_names[idx].c_str());
			}
		for (const string &ftr : data_names)
			if (clean_set_names.find(ftr) == clean_set_names.end())
				MWARN("Warning: Matrix has additional feature %s\n", ftr.c_str());
		MTHROW_AND_ERR("Error in commit_selection - after commit selection request size was %zu(%zu unique), result size = %zu(%zu unique)\n",
			final_list.size(), clean_set_names.size(), data.data.size(), data_names.size());
	}
}

double load_train_test_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, unordered_map<string, vector<float>> &additional_bootstrap,
	const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior, bool is_train) {
	double prev_prior = -1;
	vector<int> pids_to_take;
	samples.get_ids(pids_to_take);

	unordered_set<string> req_names;
	MedPidRepository dataManager;
	if (dataManager.init(RepositoryPath))
		MTHROW_AND_ERR("ERROR could not read repository %s\n", RepositoryPath.c_str());
	mod.fit_for_repository(dataManager);
	mod.get_required_signal_names(req_names);
	vector<string> sigs = { "BDATE", "GENDER", "TRAIN" };
	for (string s : req_names)
		sigs.push_back(s);
	sort(sigs.begin(), sigs.end());
	auto it = unique(sigs.begin(), sigs.end());
	sigs.resize(std::distance(sigs.begin(), it));


	if (dataManager.read_all(RepositoryPath, pids_to_take, sigs) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", RepositoryPath.c_str());

	shrink_med_model(mod, feature_selection_set);

	int sz = 0, feat_cnt = mod.get_nfeatures();
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		sz += (int)samples.idSamples[i].samples.size();
	MLOG("Generating features for %d samples with %d features...\n", sz, feat_cnt);
	//dont pass 2 Billion records:
	int max_smp = int((INT_MAX / feat_cnt) * 0.9) - 1;
	if (max_smp < sz && change_prior > 0) {
		vector<int> sel_idx;
		int prev_sz = samples.nSamples();
		prev_prior = medial::process::match_to_prior(samples, change_prior, sel_idx);
		if (!sel_idx.empty()) {//did something
			sz = (int)sel_idx.size();
			MLOG("Match to prior. size was %d, now %zu\n", prev_sz, sel_idx.size());
		}
		else
			prev_prior = -1; //didn't change
	}
	if (max_smp < sz) {
		double down_factor = max_smp / double(sz);
		MWARN("WARN:: Too Many samples (%d) - down sampling by %2.3f...\n", sz, down_factor);
		medial::process::down_sample_by_pid(samples, down_factor);
		MLOG("Done Down sampling\n");
	}

	if (is_train)
		mod.learn(dataManager, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	else
		mod.apply(dataManager, samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);

	dataMat = mod.features;
	if (!feature_selection_set.empty()) {
		unordered_set<string> selected_sigs, loaded_sigs; //apply feature selection on model
		for (auto it = feature_selection_set.begin(); it != feature_selection_set.end(); ++it)
		{
			string strip_name = *it;
			if (boost::starts_with(strip_name, "FTR_") && strip_name.find(".") != string::npos)
				strip_name = strip_name.substr(strip_name.find(".") + 1);
			selected_sigs.insert(strip_name);
		}
		bool add_age = selected_sigs.find("Age") == selected_sigs.end();
		if (!is_train && add_age) {
			additional_bootstrap["Age"].swap(dataMat.data["Age"]);
			dataMat.data.erase("Age");
		}
		bool add_gender = selected_sigs.find("Gender") == selected_sigs.end();
		if (!is_train && add_gender) {
			additional_bootstrap["Gender"].swap(dataMat.data["Gender"]);
			dataMat.data.erase("Gender");
		}

		commit_selection(dataMat, selected_sigs);
		for (auto it = dataMat.data.begin(); it != dataMat.data.end(); ++it) {
			string clean_name_stripped = it->first;
			if (boost::starts_with(clean_name_stripped, "FTR_") && clean_name_stripped.find(".") != string::npos)
				clean_name_stripped = clean_name_stripped.substr(clean_name_stripped.find(".") + 1);
			loaded_sigs.insert(clean_name_stripped);
		}
		if (loaded_sigs.size() != selected_sigs.size())
		{
			MWARN("Warning: Has missing feature in creation:\n");
			for (auto it = selected_sigs.begin(); it != selected_sigs.end(); ++it)
				if (loaded_sigs.find(*it) == loaded_sigs.end())
					MWARN("MISSING %s\n", it->c_str());
			for (auto it = loaded_sigs.begin(); it != loaded_sigs.end(); ++it)
				if (selected_sigs.find(*it) == selected_sigs.end())
					MWARN("Additional %s\n", it->c_str());
		}
	}
	return prev_prior;
}

double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, unordered_map<string, vector<float>> &additional_bootstrap,
	const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior) {

	return load_train_test_matrix(samples, dataMat, mod, additional_bootstrap, feature_selection_set, RepositoryPath,
		change_prior, false);
}

double load_test_matrix(MedSamples &samples, MedFeatures &dataMat, unordered_map<string, vector<float>> &additional_bootstrap
	, const string &modelFile, const unordered_set<string> &feature_selection_set, const string &RepositoryPath, double change_prior) {
	//use MedModel - if want to use my code feature creator than need serialization support
	//TODO: support other feature creation

	ifstream mdl_file(modelFile);
	if (mdl_file.good()) {
		mdl_file.close();
		MedModel mod;
		mod.read_from_file(modelFile);
		mod.verbosity = 0;
		double pr = load_test_matrix(samples, dataMat, mod, additional_bootstrap, feature_selection_set, RepositoryPath, change_prior);
		if (mod.LearningSet != NULL) {//when reading model from disk need to clean LearningSet before exit - valgrind
			delete mod.LearningSet;
			mod.LearningSet = 0;
			mod.serialize_learning_set = false;
		}
		return pr;
	}

	MTHROW_AND_ERR("Unsupported initialization without MedModel\n");
}

double load_train_matrix(MedSamples &samples, MedFeatures &dataMat, MedModel &mod, const string &rep_path,
	const unordered_set<string> &feature_selection_set, float change_prior) {
	unordered_map<string, vector<float>> additional_bootstrap;
	return load_train_test_matrix(samples, dataMat, mod, additional_bootstrap, feature_selection_set, rep_path,
		change_prior, true);
}

void prepare_model_from_json(MedSamples &samples,
	const string &RepositoryPath,
	MedModel &mod, MedPidRepository &dataManager, double change_prior) {
	medial::repository::prepare_repository(samples, RepositoryPath, mod, dataManager);

	int sz = 0, feat_cnt = 0;
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		sz += (int)samples.idSamples[i].samples.size();
	for (size_t i = 0; i < mod.generators.size(); ++i)
		feat_cnt += (int)mod.generators[i]->names.size();
	MLOG("Generating features for %d samples with %d features...\n", sz, feat_cnt);
	//dont pass 2 Billion records:
	int max_smp = int((INT_MAX / feat_cnt) * 0.99) - 1;
	if (max_smp < sz && change_prior > 0) {
		vector<int> sel_idx;
		medial::process::match_to_prior(samples, change_prior, sel_idx);
		if (!sel_idx.empty()) //did something
			sz = (int)sel_idx.size();
	}
	if (max_smp < sz) {
		double down_factor = max_smp / double(sz);
		MWARN("WARN:: Too Many samples (%d) - down sampling by %2.3f...\n", sz, down_factor);
		//down_sample_by_pid(samples, down_factor);
		medial::process::down_sample(samples, down_factor);
		MLOG("Done Down sampling\n");
	}
	mod.serialize_learning_set = 0;
	if (mod.predictor == NULL) {
		MLOG("set default predictor for serialization\n");
		mod.set_predictor("gdlm");
	}
}

void load_matrix_from_json(MedSamples &samples,
	const string &RepositoryPath, const string &jsonPath, MedFeatures &dataMat, double change_prior,
	MedModel &mod) {
	MLOG("Reading repo file [%s]\n", RepositoryPath.c_str());
	MedPidRepository dataManager;
	mod.init_from_json_file(jsonPath);
	mod.verbosity = 0;
	prepare_model_from_json(samples, RepositoryPath, mod, dataManager, change_prior);

	mod.learn(dataManager, &samples, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	dataMat = move(mod.features);
}

void split_registry_train_test(const string &rep_path, MedRegistry &regRecords
	, vector<MedRegistryRecord> &only_train,
	vector<MedRegistryRecord> &only_test, MedRepository &rep) {
	vector<int> reg_pids;
	regRecords.get_pids(reg_pids);
	vector<string> signal_names = { "TRAIN", "BDATE" };
	if (rep.read_all(rep_path, reg_pids, signal_names) < 0)
		MTHROW_AND_ERR("Unable to read repository.\n");
	MedDictionarySections rep_dict = rep.dict;
	int trn_code = rep.sigs.sid("TRAIN");
	only_train.reserve(int(regRecords.registry_records.size() * 0.71));
	only_test.reserve(int(regRecords.registry_records.size() * 0.21));
	for (size_t i = 0; i < regRecords.registry_records.size(); ++i) {
		int trn_val = medial::repository::get_value(rep, regRecords.registry_records[i].pid, trn_code);
		if (trn_val == 1)
			only_train.push_back(regRecords.registry_records[i]);
		else if (trn_val == 2)
			only_test.push_back(regRecords.registry_records[i]);
		//skip external validation trn_code==3
	}
}

void read_from_rep(const string &complete_reg_sig, const string &rep_path, MedRegistry &active_reg) {
	MLOG("Complete Active periods using Signal %s\n", complete_reg_sig.c_str());
	MedRepository rep2;
	vector<int> all_pids;
	vector<string> sigs_read = { complete_reg_sig };
	if (rep2.read_all(rep_path, all_pids, sigs_read) < 0)
		MTHROW_AND_ERR("Error reading repository %s\n", rep_path.c_str());
	int sid = rep2.sigs.sid(complete_reg_sig);
	if (rep2.sigs.Sid2Info[sid].n_time_channels != 2)
		MTHROW_AND_ERR("Error signal %s should have 2 time channels, has %d\n",
			complete_reg_sig.c_str(), rep2.sigs.Sid2Info[sid].n_time_channels);
	for (size_t i = 0; i < rep2.pids.size(); ++i)
	{
		MedRegistryRecord rec;
		rec.pid = rep2.pids[i];
		rec.registry_value = 1;

		UniversalSigVec usv;
		rep2.uget(rec.pid, sid, usv);
		for (int k = 0; k < usv.len; ++k)
		{
			rec.start_date = usv.Time(k, 0);
			rec.end_date = usv.Time(k, 1);
			active_reg.registry_records.push_back(rec);
		}
	}
}

void read_string_file(const string &f_in, unordered_set<string> &ls) {
	vector<string> ls_t;
	medial::io::read_codes_file(f_in, ls_t);
	ls.insert(ls_t.begin(), ls_t.end());
}

void get_learn_calibration(const string &med_model_json, MedPidRepository &rep,
	const string &rep_path, const string &calibration_init,
	MedSamples &train_samples, MedSamples &req_samples, int nfolds,
	float price_matching, double match_to_prior, const string &strata_str, const string& matching_json, MedPredictor *predictor, Calibrator &cl,
	const string &bootstrap_params, const string &measure, bool cal_need_learn) {
	//req samples are requested samples to get results on - train_samples is all_train samples! 
	//Will divide to distinct sets in train for the whole process than in CV will collect scores, learn calibrate
	// Apply on req_samples - store preds in req_samples prediction
	vector<int> req_ids;
	req_samples.get_ids(req_ids);
	unordered_set<int> seen_pid(req_ids.begin(), req_ids.end());
	MedSamples train_distict; train_distict.time_unit = train_samples.time_unit;
	for (size_t i = 0; i < train_samples.idSamples.size(); ++i)
		if (seen_pid.find(train_samples.idSamples[i].id) == seen_pid.end())
			train_distict.idSamples.push_back(train_samples.idSamples[i]);

	global_logger.levels[LOG_MED_MODEL] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = MAX_LOG_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = MAX_LOG_LEVEL;
	MedModel feature_model_full;
	feature_model_full.init_from_json_file(med_model_json);
	//prepare_rep_from_model(feature_model_full, rep, rep_path);
	//Relearn model with cv on train_distict:
	vector<MedSample> all_samples_collected; //from train_distict - to train calibrator
	vector<float> empty_test_w;
	if (cal_need_learn) {
		vector<int> folds;
		get_folds(train_distict, nfolds, folds, rep_path, false);
		vector<float> empty_weight_test;
		//Do IN CV manner:
		vector<float> cv_auc_col(nfolds);
		for (int split = 0; split < nfolds; ++split) {
			MedSamples train_sampels, test_samples;
			get_train_test(train_distict, folds, split, nfolds, train_sampels, test_samples);
			vector<float> sample_weights;
			commit_matching_general(train_sampels, price_matching, match_to_prior, sample_weights, rep, strata_str, matching_json, false);
			MedModel model_feat_generator;
			init_medmodel(model_feat_generator, rep, med_model_json);
			//Learn MedModel (after read from json) 
			model_feat_generator.learn(rep, &train_sampels, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
			if (!sample_weights.empty())
				model_feat_generator.features.weights = sample_weights;
			predictor->learn(model_feat_generator.features);
			//predictor->predict(model_feat_generator.features);
			//float auc_train = auc_samples(model_feat_generator.features.samples, sample_weights);

			model_feat_generator.apply(rep, test_samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
			predictor->predict(model_feat_generator.features);
			//float auc = auc_samples(model_feat_generator.features.samples, empty_weight_test);
			//auc_each_split.push_back(auc);
			//auc_train_each.push_back(auc_train);
			all_samples_collected.insert(all_samples_collected.end(), model_feat_generator.features.samples.begin(), model_feat_generator.features.samples.end());
			cv_auc_col[split] = auc_samples(model_feat_generator.features.samples, empty_test_w, bootstrap_params, measure);
		}
		float auc_cv = auc_samples(all_samples_collected, empty_test_w, bootstrap_params, measure);
		string all_aucs = "all_auc::" + medial::print::print_obj(auc_cv, "%2.3f");
		float avg = 0;
		for (size_t i = 0; i < cv_auc_col.size(); ++i) {
			all_aucs += " | split_" + to_string(i) + "::" + medial::print::print_obj(cv_auc_col[i], "%2.3f");
			avg += cv_auc_col[i];
		}
		if (cv_auc_col.size() > 0)
			avg /= cv_auc_col.size();
		all_aucs += " | average::" + medial::print::print_obj(avg, "%2.3f");
		MLOG("##Propensity model## %s\n", all_aucs.c_str());
	}

	//Learn All:
	vector<float> train_weights;
	commit_matching_general(train_distict, price_matching, match_to_prior, train_weights, rep, strata_str, matching_json, false);
	feature_model_full.learn(rep, &train_distict, MedModelStage::MED_MDL_LEARN_REP_PROCESSORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	if (!train_weights.empty())
		feature_model_full.features.weights = train_weights;
	predictor->learn(feature_model_full.features);
	//Learn Calibrator for all in CV
	if (cal_need_learn) {
		cl.init_from_string(calibration_init);
		cl.Learn(all_samples_collected);
	}
	//Apply on req_samples
	feature_model_full.apply(rep, req_samples, MedModelStage::MED_MDL_APPLY_FTR_GENERATORS, MedModelStage::MED_MDL_APPLY_FTR_PROCESSORS);
	predictor->predict(feature_model_full.features);
	//Apply calibrator
	cl.Apply(feature_model_full.features.samples);
	//Collect back to req_samples:
	req_samples.import_from_sample_vec(feature_model_full.features.samples);
	global_logger.levels[LOG_MED_MODEL] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEATCLEANER] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_REPCLEANER] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FEAT_SELECTOR] = LOG_DEF_LEVEL;
	global_logger.levels[LOG_FTRGNRTR] = LOG_DEF_LEVEL;
}

void read_model_splits(const string &model_splits, vector<MedModel> &models, unordered_map<int, int> &pid_to_model_idx) {
	ifstream fr(model_splits);
	if (!fr.good())
		MTHROW_AND_ERR("Error can't open %s file for reading\n", model_splits.c_str());
	//Fomat [PID] TAB_DELIMETER [MODEL_PATH]
	string line;
	unordered_set<string> model_seen;
	unordered_map<string, vector<int>> model_to_pids;
	while (getline(fr, line)) {
		vector<string> tokens;
		boost::split(tokens, line, boost::is_any_of("\t"));
		if (tokens.size() != 2)
			MTHROW_AND_ERR("Error bad format file %s expected 2 tokens of tab dilimeter. line:\n%s\n",
				model_splits.c_str(), line.c_str());
		int pid = med_stoi(tokens[0]);
		const string &mdl_path = tokens[1];
		if (model_seen.find(mdl_path) == model_seen.end()) {
			model_seen.insert(mdl_path);
		}
		model_to_pids[mdl_path].push_back(pid);
	}
	vector<string> all_mdls(model_seen.begin(), model_seen.end());
	sort(all_mdls.begin(), all_mdls.end());
	//read models
	models.resize(all_mdls.size());
	for (int i = 0; i < all_mdls.size(); ++i) {
		models[i].read_from_file(all_mdls[i]);
		const vector<int> &all_pids = model_to_pids[all_mdls[i]];
		for (int pid : all_pids) //connect all pids to current i
			pid_to_model_idx[pid] = i;
	}
}

void apply_model_splits(const unordered_map<int, int> &pid_to_model_idx, vector<MedModel> &models,
	const string &rep_path, MedSamples &samples, bool throw_not_found) {
	if (models.empty())
		MTHROW_AND_ERR("Error - models is empty\n");

	//split MedSamples by splits:
	vector<MedSamples> samples_by_split(models.size());
	for (size_t i = 0; i < samples_by_split.size(); ++i)
		samples_by_split[i].time_unit = samples.time_unit;

	int not_fnd = 0;
	int exmaple_not_fnd = -1;
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
	{
		int pid = samples.idSamples[i].id;
		int sel_split;
		if (pid_to_model_idx.find(pid) == pid_to_model_idx.end()) {
			if (throw_not_found)
				MTHROW_AND_ERR("Error - can't find pid %d in model splits\n", pid);
			++not_fnd;
			exmaple_not_fnd = pid;
			sel_split = 0;
		}
		else
			sel_split = pid_to_model_idx.at(pid);

		samples_by_split[sel_split].idSamples.push_back(samples.idSamples[i]);
	}
	if (not_fnd > 0)
		MWARN("Warning: Has %d not found pid in splits. example_pid = %d\n", not_fnd, exmaple_not_fnd);

	MedPidRepository rep;
	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	vector<int> pids; //fetch all
	models.front().load_repository(rep_path, rep, true);
	//collect each split:
	for (size_t i = 0; i < samples_by_split.size(); ++i) {
		models[i].fit_for_repository(rep);
		if (models[i].apply(rep, samples_by_split[i], MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_END) < 0)
			MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");
	}

	//copy results to samples:
	samples.idSamples.clear();
	for (size_t i = 0; i < samples_by_split.size(); ++i) {
		samples.idSamples.insert(samples.idSamples.end(),
			samples_by_split[i].idSamples.begin(), samples_by_split[i].idSamples.end());
	}
	samples.sort_by_id_date();
}

void apply_model_splits_main(const unordered_map<int, int> &pid_to_model_idx, vector<MedModel> &models,
	const string &rep_path, MedSamples &samples, MedFeatures &features, bool throw_not_found) {
	if (models.empty())
		MTHROW_AND_ERR("Error - models is empty\n");

	//split MedSamples by splits:
	vector<MedSamples> samples_by_split(models.size());
	for (size_t i = 0; i < samples_by_split.size(); ++i)
		samples_by_split[i].time_unit = samples.time_unit;

	int not_fnd = 0;
	int exmaple_not_fnd = -1;
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
	{
		int pid = samples.idSamples[i].id;
		int sel_split;
		if (pid_to_model_idx.find(pid) == pid_to_model_idx.end()) {
			if (throw_not_found)
				MTHROW_AND_ERR("Error - can't find pid %d in model splits\n", pid);
			++not_fnd;
			exmaple_not_fnd = pid;
			sel_split = 0;
		}
		else
			sel_split = pid_to_model_idx.at(pid);

		samples_by_split[sel_split].idSamples.push_back(samples.idSamples[i]);
	}
	if (not_fnd > 0)
		MWARN("Warning: Has %d not found pid in splits. example_pid = %d\n", not_fnd, exmaple_not_fnd);

	MedPidRepository rep;
	if (rep.init(rep_path) < 0)
		MTHROW_AND_ERR("ERROR could not read repository %s\n", rep_path.c_str());
	vector<int> pids; //fetch all
	models.front().load_repository(rep_path, rep, true);
	//collect each split:
	features.samples.clear();
	features.data.clear();
	for (size_t i = 0; i < samples_by_split.size(); ++i) {
		models[i].fit_for_repository(rep);
		if (models[i].apply(rep, samples_by_split[i], MED_MDL_APPLY_FTR_GENERATORS, MED_MDL_END) < 0)
			MTHROW_AND_ERR("medial::medmodel::apply() ERROR :: could not apply model\n");

		samples_by_split[i].flatten(features.samples);
		for (const auto &it : models[i].features.data)
			features.data[it.first].insert(features.data[it.first].end(), it.second.begin(), it.second.end());
	}

	features.init_pid_pos_len();
}

void assign_weights(const string &rep_path, MedFeatures &dataMat, const weights_params &params,
	double change_prior) {
	//create MedSamples from dataMat
	MedSamples train_samples;
	unordered_map<int, int> pid_to_index;
	for (size_t i = 0; i < dataMat.samples.size(); ++i)
	{
		MedSample sample = dataMat.samples[i];
		if (pid_to_index.find(dataMat.samples[i].id) == pid_to_index.end()) {
			MedIdSamples sample_id(dataMat.samples[i].id);
			pid_to_index[dataMat.samples[i].id] = (int)train_samples.idSamples.size();
			sample_id.samples.push_back(sample);
			train_samples.idSamples.push_back(sample_id);
		}
		else
			train_samples.idSamples[pid_to_index[dataMat.samples[i].id]].samples.push_back(sample);
	}

	MLOG("Assigning Weights..\n");
	//use other model for risk score:
	params.get_weights(dataMat.samples, dataMat.weights);

	//Print prob hist:
	medial::print::print_hist_vec(dataMat.weights, "probability hist", "%2.5f");
	MLOG("Done Weights\n");
}

void get_folds(const MedSamples &samples, int nfold, vector<int> &folds, const string &rep_path, bool use_in_samples) {
	if (use_in_samples) {
		for (size_t i = 0; i < samples.idSamples.size(); ++i)
			for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j)
				folds.push_back(samples.idSamples[i].samples[j].split);
		return;
	}
	if (nfold < 2)
		MTHROW_AND_ERR("Error nfolds should be bigger than 1\n");
	MedRepository rep;
	vector<int> pids;
	//samples.get_ids(pids);
	vector<string> sigs = { "TRAIN" };
	if (rep.read_all(rep_path, pids, sigs) < 0)
		MTHROW_AND_ERR("Errorr can't read repo %s\n", rep_path.c_str());
	int train_sig = rep.sigs.sid(sigs.front());
	//Last split is Train == 2, split Train==1 to folds

	int pid_cnt = (int)samples.idSamples.size();
	folds.resize(pid_cnt);
	random_device rd;
	mt19937 gen(rd());
	uniform_int_distribution<> dist_r(0, nfold - 1); //each id is once in this sample:

	for (size_t i = 0; i < folds.size(); ++i) {
		int pid = samples.idSamples[i].id;
		int train_val = (int)medial::repository::get_value(rep, pid, train_sig);
		if (train_val == 1)
			folds[i] = dist_r(gen);
		else if (train_val == 2)
			folds[i] = nfold;
		else
			folds[i] = -1; //to remove - external validation!!
	}
}

void get_train_test(const MedSamples &samples, const vector<int> &folds, int choose_fold, int limit,
	MedSamples &train, MedSamples &test) {

	vector<MedSamples *> smps = { &train, &test };
	for (size_t i = 0; i < folds.size(); ++i)
		if (folds[i] != -1) //skip Train == 3
			if (folds[i] < limit || choose_fold == limit) //If Not last split(choose_fold == limit which mean train==2) skip folds from train==2 for training
				smps[folds[i] == choose_fold]->idSamples.push_back(samples.idSamples[i]);
	MLOG("Train has %zu patient, Test has %zu patients\n", smps[0]->idSamples.size(), smps[1]->idSamples.size());
}

void split_train_test(const MedSamples &samples, int nfold, const string &rep_path,
	unordered_map<string, MedSamples> &train_samples, unordered_map<string, MedSamples> &test_samples, bool use_in_samples) {
	vector<int> folds;
	get_folds(samples, nfold, folds, rep_path, use_in_samples);
	if (use_in_samples) {//update nfold to max split
		nfold = 0;
		for (int fl : folds)
			if (fl > nfold)
				nfold = fl;
	}

	for (int i = 0; i < nfold; ++i)
	{
		string split_name = "split" + to_string(i);
		MedSamples &train = train_samples[split_name];
		MedSamples &test = test_samples[split_name];
		get_train_test(samples, folds, i, nfold, train, test);
	}
}


void get_train_test(const MedSamples &samples, const MedSamples &t_samples,
	const vector<int> &folds, int choose_fold, int limit, MedSamples &train, MedSamples &test) {

	//by train pids set:
	unordered_set<int> train_pids;
	//add train from samples that are not in fold
	for (size_t i = 0; i < folds.size(); ++i)
		if (folds[i] != -1) //skip Train == 3
			if ((folds[i] < limit && folds[i] != choose_fold) || choose_fold == limit) { //If Not last split(choose_fold == limit which mean train==2) skip folds from train==2 for training
				train.idSamples.push_back(samples.idSamples[i]);
				train_pids.insert(samples.idSamples[i].id);
			}
	//add test samples that are not in train_pids:
	for (size_t i = 0; i < t_samples.idSamples.size(); ++i)
		if (train_pids.find(t_samples.idSamples[i].id) == train_pids.end())
			test.idSamples.push_back(t_samples.idSamples[i]);

	MLOG("Train has %zu patient, Test has %zu patients\n", train.idSamples.size(), test.idSamples.size());
}
//has also test samples to sample from
void split_train_test(const MedSamples &samples, const MedSamples &t_samples, int nfold, const string &rep_path,
	unordered_map<string, MedSamples> &train_samples, unordered_map<string, MedSamples> &test_samples, bool use_in_samples) {
	vector<int> folds;
	get_folds(samples, nfold, folds, rep_path, use_in_samples);
	if (use_in_samples) {//update nfold to max split
		nfold = 0;
		for (int fl : folds)
			if (fl > nfold)
				nfold = fl;
	}

	for (int i = 0; i < nfold; ++i)
	{
		string split_name = "split" + to_string(i);
		MedSamples &train = train_samples[split_name];
		MedSamples &test = test_samples[split_name];
		get_train_test(samples, t_samples, folds, i, nfold, train, test);
	}
}

void collect_ids_from_samples(const vector<MedSample> &all, const MedSamples &ids_samples, vector<MedSample> &collected) {
	vector<int> ids;
	ids_samples.get_ids(ids);
	unordered_set<int> seen_ids(ids.begin(), ids.end());
	for (size_t i = 0; i < all.size(); ++i)
		if (seen_ids.find(all[i].id) != seen_ids.end())
			collected.push_back(all[i]);

	sort(collected.begin(), collected.end(), comp_sample_id_time);
}

void index_pid_time_prob(const vector<MedSample> &all_train_flat,
	unordered_map<int, unordered_map<int, float>> &pid_time_prob) {
	for (const auto &it : all_train_flat)
		pid_time_prob[it.id][it.time] = it.attributes.at("weight");
}

void filter_age_years(MedSamples &samples, MedPidRepository &rep, int min_age, int max_age, int min_year, int  max_year) {
	vector<MedSample> selected;

	int bdate_sid = rep.sigs.sid("BDATE");
	if (bdate_sid < 0)
		MTHROW_AND_ERR("can't find BDATE or rep not initialized\n");
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
	{
		for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j)
		{
			int byear = int(medial::repository::get_value(rep, samples.idSamples[i].samples[j].id, bdate_sid) / 10000);
			int sample_year = int(samples.idSamples[i].samples[j].time / 10000);
			int age = sample_year - byear;
			if (age >= min_age && age <= max_age && sample_year >= min_year && sample_year <= max_year)
				selected.push_back(samples.idSamples[i].samples[j]);
		}
	}

	samples.clear();
	samples.import_from_sample_vec(selected);
}

void select_splits_numbers(int num_of_splits, int active_splits,
	unordered_set<int> &sel) {
	sel.clear();
	if (active_splits <= 0 || active_splits >= num_of_splits) {
		for (int i = 0; i < num_of_splits; ++i)
			sel.insert(i);
		return;
	}
	random_device rd;
	mt19937 gen(rd());

	uniform_int_distribution<> int_dict(0, num_of_splits - 1);
	for (size_t i = 0; i < active_splits; ++i)
	{
		int split = int_dict(gen);
		while (sel.find(split) != sel.end())
			split = int_dict(gen);
		sel.insert(split);
	}
}

void commit_select_splits(const unordered_map<string, MedSamples> &train_samples,
	const unordered_map<string, MedSamples> &test_samples, int active_splits, const unordered_set<int> &sel,
	unordered_map<string, MedSamples> &train_samples_sel,
	unordered_map<string, MedSamples> &test_samples_sel) {
	if (active_splits <= 0 || active_splits >= test_samples.size()) {
		train_samples_sel = train_samples;
		test_samples_sel = test_samples;
		return;
	}
	vector<string> all_splits;
	all_splits.reserve(test_samples.size());
	for (const auto &it : test_samples)
		all_splits.push_back(it.first);
	sort(all_splits.begin(), all_splits.end());

	for (int id : sel)
	{
		string &split = all_splits[id];
		test_samples_sel[split] = test_samples.at(split);
		train_samples_sel[split] = train_samples.at(split);
	}
}

void select_splits(const unordered_map<string, MedSamples> &train_samples,
	const unordered_map<string, MedSamples> &test_samples, int active_splits,
	unordered_map<string, MedSamples> &train_samples_sel,
	unordered_map<string, MedSamples> &test_samples_sel) {
	if (active_splits <= 0 || active_splits >= test_samples.size()) {
		train_samples_sel = train_samples;
		test_samples_sel = test_samples;
		return;
	}
	unordered_set<int> sel;
	random_device rd;
	mt19937 gen(rd());
	vector<string> all_splits;
	all_splits.reserve(test_samples.size());
	for (const auto &it : test_samples)
		all_splits.push_back(it.first);
	sort(all_splits.begin(), all_splits.end());

	uniform_int_distribution<> int_dict(0, (int)all_splits.size() - 1);

	for (size_t i = 0; i < active_splits; ++i)
	{
		int split = int_dict(gen);
		while (sel.find(split) != sel.end())
			split = int_dict(gen);
		sel.insert(split);
	}

	for (int id : sel)
	{
		string &split = all_splits[id];
		test_samples_sel[split] = test_samples.at(split);
		train_samples_sel[split] = train_samples.at(split);
	}
}

void samples_to_splits_train_test(
	const MedSamples &curr_train, 
	const MedSamples &curr_test,
	unordered_map<string, MedSamples> &split_to_samples_train, 
	unordered_map<string, MedSamples> &split_to_samples_test
) {
	/*
		Prepare split_to_samples_train[] and split_to_samples_test[]
		which map split_name into the set of samples
	*/
	unordered_set<int> all_splits;
	for (size_t i = 0; i < curr_test.idSamples.size(); ++i)
		all_splits.insert(curr_test.idSamples[i].split);
	for (size_t i = 0; i < curr_test.idSamples.size(); ++i)
	{
		const MedIdSamples &smp_id_test = curr_test.idSamples[i];
		string split = to_string(smp_id_test.split);
		split_to_samples_test[split].idSamples.push_back(smp_id_test);
	}

	for (size_t i = 0; i < curr_train.idSamples.size(); ++i)
	{
		const MedIdSamples &smp_id = curr_train.idSamples[i];
		for (int opt_split : all_splits)
			if (opt_split != smp_id.split) { //add sample to train on all rest of splits
				string split_name = to_string(opt_split);
				split_to_samples_train[split_name].idSamples.push_back(smp_id);
			}
	}
}

void assign_splits_if_needed(unordered_map<string, MedSamples> &train_samples,
	unordered_map<string, MedSamples> &test_samples, int nfolds) {
	if (nfolds <= 0)
		return; //cancel try 

	random_device rd;
	mt19937 gen(rd());
	uniform_int_distribution<> rand_split(0, nfolds - 1);

	unordered_map<int, int> pids_to_split; //use same splits for all
	for (auto &it_train : train_samples)
	{
		MedSamples &train_smps = it_train.second;
		MedSamples &test_smps = test_samples.at(it_train.first);

		//get folds from train if has:
		int split = -1;
		if (!train_smps.idSamples.empty())
			split = train_smps.idSamples.front().split;
		bool found_split = false;
		for (size_t i = 1; i < train_smps.idSamples.size() && !found_split; ++i)
			found_split = split != train_smps.idSamples[i].split;
		if (!found_split) {
			//has no splits - need to set splits - validate train\test are differetn pids:
			for (size_t i = 0; i < train_smps.idSamples.size(); ++i)
				if (pids_to_split.find(train_smps.idSamples[i].id) == pids_to_split.end())
					pids_to_split[train_smps.idSamples[i].id] = rand_split(gen);
			bool is_distinct_test = true;
			for (size_t i = 0; i < test_smps.idSamples.size() && is_distinct_test; ++i)
				is_distinct_test = pids_to_split.find(test_smps.idSamples[i].id) == pids_to_split.end();
			//maybe create 1 test set which split nfold? - skip for now and randomly split it also:
			if (!is_distinct_test)
				MLOG("samples %s - has no splits - assigning randomly\n", it_train.first.c_str());
			else
				MLOG("samples %s - has no splits - assigning randomly. test is completly different from train\n", it_train.first.c_str());

			for (size_t i = 0; i < test_smps.idSamples.size(); ++i)
				if (pids_to_split.find(test_smps.idSamples[i].id) == pids_to_split.end())
					pids_to_split[test_smps.idSamples[i].id] = rand_split(gen);
			//now assign the new splits:
			for (size_t i = 0; i < train_smps.idSamples.size(); ++i)
				train_smps.idSamples[i].set_split(pids_to_split.at(train_smps.idSamples[i].id));
			for (size_t i = 0; i < test_smps.idSamples.size(); ++i)
				test_smps.idSamples[i].set_split(pids_to_split.at(test_smps.idSamples[i].id));
		}
	}
}

void filter_test_bootstrap_cohort(const string &rep, unordered_map<string, MedSamples> &test_samples,
	const string &bt_json, const string &bt_cohort) {
	MedModel bt_filters;
	if (!bt_json.empty())
		bt_filters.init_from_json_file(bt_json);
	//check if has Age:
	bool fnd_age = false, fnd_gender = false;
	for (const FeatureGenerator *f : bt_filters.generators) {
		if (f->generator_type == FTR_GEN_AGE)
			fnd_age = true;
		if (f->generator_type == FTR_GEN_GENDER)
			fnd_gender = true;
		if (fnd_age && fnd_gender)
			break;
	}
	if (!fnd_age)
		bt_filters.add_age();
	if (!fnd_gender)
		bt_filters.add_gender();

	MedPidRepository bt_repository;
	bt_filters.load_repository(rep, bt_repository, true);

	for (auto &it : test_samples) {
		MedSamples &curr_samples = it.second;
		MedBootstrap::filter_bootstrap_cohort(bt_repository, bt_filters, curr_samples, bt_cohort);
	}
}