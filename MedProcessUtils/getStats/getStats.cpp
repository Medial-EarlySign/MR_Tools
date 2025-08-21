// Read an object from a binary file and print

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "getStats.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{
	// Statistics
	unordered_set<string> all_stats = { "auc","pearson","spearman","explained","l2", "rmse", "r2" };

	//stats that creates 3 values statistical value, degree of freedom and p value
	unordered_set<string> all_stat_test = { "t_test","t_test_unequal_size","welch_t_test",
		"mann-whitney", "mann-whitney_with-missing" };
	all_stats.insert(all_stat_test.begin(), all_stat_test.end());

	// stats that create 2 values
	unordered_set<string> all_stats2 = { "accuracy" };
	all_stats.insert(all_stats2.begin(), all_stats2.end());

	// Initialize
	po::variables_map vm;
	read_run_params(argc, argv, vm, all_stats);

	// Read Data
	vector<float> v1, v2, w;
	read_data(vm, v1, v2, w);

	// Statistics
	string stat = vm["stat"].as<string>();
	boost::to_lower(stat);
	int nBootstrap = vm["nbootstrap"].as<int>();

	vector<string> stats;
	vector<string> types;
	boost::split(stats, stat, boost::is_any_of(","));

	for (const string &_stat : stats)
	{
		if (all_stats.find(_stat) == all_stats.end())
			MTHROW_AND_ERR("Unknown stat \'%s\' requested\n", _stat.c_str());

		if (all_stat_test.find(_stat) != all_stat_test.end()) {
			if (!w.empty())
				MTHROW_AND_ERR("Error - weights are not supported for %s\n", _stat.c_str());

			types.push_back(_stat + ".STATISIC_VALUE");
			types.push_back(_stat + ".DEGREE_OF_FREEDOM");
			types.push_back(_stat + ".P_VALUE");
			types.push_back(_stat + ".V1_MEAN");
			types.push_back(_stat + ".V2_MEAN");
		}
		else if (all_stats2.find(_stat) != all_stats2.end()) {
			if (!w.empty())
				MTHROW_AND_ERR("Error - weights are not supported for for %s\n", _stat.c_str());

			types.push_back(_stat + ".VALUE");
			types.push_back(_stat + ".PARAM");
		}
		else {
			if (w.empty())
				types.push_back(_stat);
			else
				types.push_back("weighted_" + _stat);
		}
	}

	// Calculate
	vector<vector<float>> bootstrap_v1(nBootstrap, vector<float>(v1.size())), bootstrap_v2(nBootstrap, vector<float>(v2.size())), bootstrap_w(nBootstrap, vector<float>(v1.size()));
	vector<vector<float>> values(types.size(), vector<float>(nBootstrap));
	vector<float> obs_values(types.size());
	if (w.empty())
		w.assign(v1.size(), 1.0);

	//calc obs:
	int val_ind_obs = 0;
	for (int j = 0; j < stats.size(); j++) {
		vector<float> res;
		get_stat_val(stats[j], v1, v2, w, res);
		for (size_t k = 0; k < res.size(); ++k) {
			obs_values[val_ind_obs] = res[k];
			++val_ind_obs;
		}
	}

#pragma omp parallel for
	for (int i = 0; i < nBootstrap; i++) {
		//not sure it's thread safe
		sample(v1, v2, w, bootstrap_v1[i], bootstrap_v2[i], bootstrap_w[i]);
		int val_ind = 0;
		for (int j = 0; j < stats.size(); j++) {
			vector<float> res;
			get_stat_val(stats[j], bootstrap_v1[i], bootstrap_v2[i], bootstrap_w[i], res);
			for (size_t k = 0; k < res.size(); ++k)
			{
				values[val_ind][i] = res[k];
				++val_ind;
			}
		}
	}

	// Moments
	for (int j = 0; j < types.size(); j++) {
		sort(values[j].begin(), values[j].end());

		double s = 0, s2 = 0;
		for (float& v : values[j]) {
			s += v;
			s2 += v * v;
		}

		float mean = s / nBootstrap;

		float sdv;
		if (nBootstrap > 1) {
			float var = (s2 - s * mean) / (nBootstrap - 1);
			if (fabs(var) < 1e-7)
				var = 0;
			sdv = sqrt(var);
		}
		else
			sdv = -1.0;

		float ci[2] = { values[j][(int)(nBootstrap*0.025)], values[j][(int)(nBootstrap*0.975)] };

		MLOG("%s : %d bootstrap runs - Mean = %f Sdv = %f CI = ( %f , %f ) Obs = %f\n",
			types[j].c_str(), nBootstrap, mean, sdv, ci[0], ci[1], obs_values[j]);
	}

	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm, const unordered_set<string> &all_stats) {

	po::options_description desc("Program options");
	string options_str = medial::io::get_list(all_stats);
	string full_text = "statistics to calculate (options: " + options_str + ") - comma separated if more than one";

	try {
		desc.add_options()
			("help", "produce help message")
			("stat", po::value<string>()->default_value("pearson,spearman"), full_text.c_str())
			("input", po::value<string>()->default_value("-"), "input file (default is stdin)")
			("no_header", "indicating that input file is without a header")
			("allow_empty", "indicating that column might be empty and skip it when empty - won't be in equal size")
			("sep", po::value<string>()->default_value("white"), "input file separator (white/tab/space/comma")
			("cols", po::value<string>()->default_value("1,2"), "comma seperated 0-based (2 or 3) columns to take (v1,v2,weights)")
			("nbootstrap", po::value<int>()->default_value(1), "# of bootstrap runs")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);
	}
	catch (exception& e) {
		string err = "error: " + string(e.what()) + "; run with --help for usage information\n";
		throw runtime_error(err);
	}
	catch (...) {
		throw runtime_error("Exception of unknown type!\n");
	}
}

int read_data(po::variables_map& vm, vector<float>& v1, vector<float>& v2, vector<float>& w) {

	string inFile = vm["input"].as<string>();

	// Read
	int rc;
	if (inFile != "-") {
		ifstream inf(inFile);
		if (!inf)
			MTHROW_AND_ERR("Cannot open %s for reading\n", inFile.c_str());
		rc = read_data_from_stream(vm, inf, v1, v2, w);
	}
	else {
		rc = read_data_from_stream(vm, std::cin, v1, v2, w);
	}

	return rc;
}

int read_data_from_stream(po::variables_map& vm, istream& inf, vector<float>& v1, vector<float>& v2, vector<float>& w) {
	string sep = vm["sep"].as<string>();

	if (sep == "white")
		sep = " \t";
	else if (sep == "tab")
		sep = "\t";
	else if (sep == "space" || sep == " ")
		sep = " ";
	else if (sep == "comma" || sep == ",")
		sep = ",";
	else
		MTHROW_AND_ERR("Unknown separator option \'%s\'\n", sep.c_str());

	// Columns
	string cols = vm["cols"].as<string>();
	vector<string> cols_v;
	boost::split(cols_v, cols, boost::is_any_of(","));
	if (cols_v.size() != 2 && cols_v.size() != 3)
		MTHROW_AND_ERR("Two or Three columns allowed. Given \'%s\'\n", cols.c_str());
	vector<int> cols_i;
	int max_col = 0;
	for (string& col : cols_v) {
		int col_i = stoi(col);
		cols_i.push_back(col_i);
		if (col_i > max_col)
			max_col = col_i;
	}

	string line;
	vector<string> fields;

	bool header = (vm.count("no_header") == 0);
	int line_num = 1;
	while (getline(inf, line)) {
		if (!header) {
			boost::split(fields, line, boost::is_any_of(sep));
			if (fields.size() - 1 < max_col)
				MTHROW_AND_ERR("Not enough fields in \'%s\' (%d) to extract col #%d\n", line.c_str(), (int)fields.size(), max_col);
			string s1 = fields[cols_i[0]], s2 = fields[cols_i[1]];
			boost::trim(s1); boost::trim(s2);
			if (!s1.empty())
				v1.push_back(stof(s1));
			else {
				if (vm.count("allow_empty") == 0)
					MTHROW_AND_ERR("Got empty value in row %d for column %d. it's not allowed\n", line_num, cols_i[0]);
			}
			if (!s2.empty())
				v2.push_back(stof(s2));
			else {
				if (vm.count("allow_empty") == 0)
					MTHROW_AND_ERR("Got empty value in row %d for column %d. it's not allowed\n", line_num, cols_i[1]);
			}
			if (cols_i.size() == 3) {
				if (vm.count("allow_empty") > 0)
					MTHROW_AND_ERR("Can't get weights when allow_empty is on\n");
				w.push_back(stof(fields[cols_i[2]]));
			}
		}
		header = false;
		++line_num;
	}

	MLOG("Read %d cols for %d,%d lines\n", (int)cols_i.size(), (int)v1.size(), (int)v2.size());
	return (int)v1.size();
}

// Get AUC
float get_auc(const vector<float>& v1, const vector<float> &v2) {

	const vector<float>& labels = v1;
	const vector<float>& preds = v2;

	// Transform labels to 0/1
	set<float> labels_set;
	for (float label : labels)
		labels_set.insert(label);
	if (labels_set.size() != 2)
		MTHROW_AND_ERR("Labels must be of size 2 for AUC\n");

	return  medial::performance::auc_q(preds, labels);
}

// Get Proportion of explained variance
float get_explained(const vector<float>& v1, const vector<float>& v2, const vector<float>& w) {

	// Variance
	float mean, std;
	medial::stats::get_mean_and_std_without_cleaning(v1, mean, std, &w);
	float var = std * std;

	// Unexplained
	double unExplainedVar = 0;
	double sum = 0;
	for (size_t i = 0; i < v1.size(); i++) {
		unExplainedVar += w[i] * (v1[i] - v2[i])*(v1[i] - v2[i]);
		sum += w[i];
	}
	unExplainedVar /= sum;
	float explainedP = 100.0*(var - unExplainedVar) / var;
	//MLOG("Outcome Mean = %.3g ; Variance = %.3g ; UnExpalined Var = %.3g ; Percentage of variance explained = %.2f\n", mean, var, unExplainedVar, explainedP);

	return explainedP;
}

// Get L2 Error
float get_l2_err(const vector<float>& v1, const vector<float>& v2, const vector<float>& w) {

	double sum_w = 0;
	double sum_err = 0;
	for (size_t i = 0; i < v1.size(); i++) {
		sum_w += w[i];
		sum_err += w[i] * (v1[i] - v2[i])*(v1[i] - v2[i]);
	}

	return sum_err / sum_w;
}

// Bootstrap sampling
void sample(const vector<float>& v1, const  vector<float>& v2, const  vector<float>& w,
	vector<float>& bootstrap_v1, vector<float>& bootstrap_v2, vector<float>& bootstrap_w) {
	size_t n = v1.size();
	bool equal_size = v1.size() == v2.size();
	if (equal_size) {
		for (size_t i = 0; i < n; i++) {
			int j = (int)(n * (globalRNG::rand() / (globalRNG::max() + 0.0)));

			bootstrap_v1[i] = v1[j];
			bootstrap_v2[i] = v2[j];
			bootstrap_w[i] = w[j];
		}
	}
	else {
		for (size_t i = 0; i < n; i++) {
			int j = (int)(n * (globalRNG::rand() / (globalRNG::max() + 0.0)));
			bootstrap_v1[i] = v1[j];
		}
		for (size_t i = 0; i < v2.size(); i++) {
			int j = (int)(v2.size() * (globalRNG::rand() / (globalRNG::max() + 0.0)));
			bootstrap_v2[i] = v2[j];
		}
		bootstrap_w.clear();
	}
}

void get_optimal_accuracy(const vector<float>& labels, const vector<float> &preds, float& acc, float& bnd) {

	// Check labels
	set<float> labels_set;
	for (float label : labels)
		labels_set.insert(label);
	if (labels_set.size() != 2 || labels_set.find(0.0) == labels_set.end())
		MTHROW_AND_ERR("Labels must be 0 + other for accuracy\n");

	int n = (int)preds.size();
	vector<pair<float, int>> data(n);
	for (int i = 0; i < n; i++)
		data[i] = { preds[i], (labels[i] > 0) ? 1 : 0 };
	sort(data.begin(), data.end(), [](const pair<float, int>& left, const pair<float, int>& right) { return (left.first < right.first); });

	int tpos = 0, tneg = 0;
	for (int i = 0; i < n; i++)
		tpos += data[i].second;

	bnd = data[0].first;
	acc = (tpos + 0.0) / n;
	for (int i = 0; i < n; i++) {
		if (data[i].second)
			tpos--;
		else
			tneg++;

		float _acc = (tpos + tneg + 0.0) / n;
		if (_acc > acc) {
			acc = _acc;
			bnd = data[i].first;
		}
	}
}

void get_stat_val(const string &stat_test, const vector<float>& v1, const vector<float>& v2, const vector<float> &w,
	vector<float> &values) {
	values.resize(1);
	if (stat_test == "auc")
		values[0] = get_auc(v1, v2);
	else if (stat_test == "pearson")
		values[0] = medial::performance::pearson_corr_without_cleaning(v1, v2, &w);
	else if (stat_test == "spearman")
		values[0] = medial::performance::spearman_corr_without_cleaning(v1, v2, &w);
	else if (stat_test == "explained")
		values[0] = get_explained(v1, v2, w);
	else if (stat_test == "l2")
		values[0] = get_l2_err(v1, v2, w);
	else if (stat_test == "accuracy") {
		float acc, bnd;
		get_optimal_accuracy(v1, v2, acc, bnd);
		values.resize(2);
		values[0] = acc;
		values[1] = bnd;
	}
	else if (stat_test == "rmse")
		values[0] = sqrt(get_l2_err(v1, v2, w));
	else if (stat_test == "r2") {
		double l2_1 = sqrt(get_l2_err(v1, v2, w));
		float mean_val = medial::stats::mean_without_cleaning(v1, &w);
		vector<float> v_static(v2.size(), mean_val);
		double l2_base = sqrt(get_l2_err(v1, v_static, w));
		values[0] = 1 - (l2_1 / l2_base);
	}
	else if (stat_test == "t_test") {
		double t_test, dof, p_val;
		medial::stats::t_test(v1, v2, t_test, dof, p_val);
		values.resize(5);
		values[0] = t_test;
		values[1] = dof;
		values[2] = p_val;
		values[3] = medial::stats::mean_without_cleaning(v1);
		values[4] = medial::stats::mean_without_cleaning(v2);
	}
	else if (stat_test == "t_test_unequal_size") {
		double t_test, dof, p_val;
		medial::stats::t_test_unequal_sample_size(v1, v2, t_test, dof, p_val);
		values.resize(5);
		values[0] = t_test;
		values[1] = dof;
		values[2] = p_val;
		values[3] = medial::stats::mean_without_cleaning(v1);
		values[4] = medial::stats::mean_without_cleaning(v2);
	}
	else if (stat_test == "welch_t_test") {
		double t_test, dof, p_val;
		medial::stats::welch_t_test(v1, v2, t_test, dof, p_val);
		values.resize(5);
		values[0] = t_test;
		values[1] = dof;
		values[2] = p_val;
		values[3] = medial::stats::mean_without_cleaning(v1);
		values[4] = medial::stats::mean_without_cleaning(v2);
	}
	else if (stat_test == "mann-whitney_with-missing") {
		//Without clear of missing data
		values.resize(5);
		vector<float> test_auc(v1.size(), 0), data_vec;
		test_auc.resize(v1.size() + v2.size(), 1);
		data_vec.reserve(v1.size() + v2.size());
		data_vec.insert(data_vec.end(), v1.begin(), v1.end());
		data_vec.insert(data_vec.end(), v2.begin(), v2.end());

		float auc = medial::performance::auc_q(data_vec, test_auc);
		//float u_stat = auc * v1.size()*v2.size();
		values[0] = auc;
		values[1] = 1;
		values[2] = 1 - 2 * abs(auc - 0.5);
		int n_tmp;
		values[3] = medial::stats::mean<float>(v1, MED_MAT_MISSING_VALUE, n_tmp);
		values[4] = medial::stats::mean<float>(v2, MED_MAT_MISSING_VALUE, n_tmp);
	}
	else if (stat_test == "mann-whitney") {
		//Without clear of missing data
		values.resize(5);
		vector<float> test_auc, data_vec;
		test_auc.reserve(v1.size() + v2.size());
		data_vec.reserve(v1.size() + v2.size());
		for (size_t i = 0; i < v1.size(); ++i)
			if (v1[i] != MED_MAT_MISSING_VALUE) {
				data_vec.push_back(v1[i]);
				test_auc.push_back(0);
			}
		for (size_t i = 0; i < v2.size(); ++i)
			if (v2[i] != MED_MAT_MISSING_VALUE) {
				data_vec.push_back(v2[i]);
				test_auc.push_back(1);
			}

		float auc = medial::performance::auc_q(data_vec, test_auc);
		//float u_stat = auc * v1.size()*v2.size();
		values[0] = auc;
		values[1] = 1;
		values[2] = 1 - 2 * abs(auc - 0.5);
		int n_tmp;
		values[3] = medial::stats::mean<float>(v1, MED_MAT_MISSING_VALUE, n_tmp);
		values[4] = medial::stats::mean<float>(v2, MED_MAT_MISSING_VALUE, n_tmp);
	}
	else
		MTHROW_AND_ERR("method %s is not implemented\n", stat_test.c_str());
}