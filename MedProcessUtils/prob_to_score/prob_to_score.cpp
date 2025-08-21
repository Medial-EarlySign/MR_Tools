// Learn a calibrator

#define _CRT_SECURE_NO_WARNINGS
#define _CRT_RAND_S

#include "prob_to_score.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int main(int argc, char *argv[])
{

	// Initialize  
	po::variables_map vm;
	read_run_params(argc, argv, vm);
	globalRNG::srand(vm["seed"].as<int>());

	// Paramters 
	int minCases = vm["min_case_in_win"].as<int>();
	int minSamples = vm["min_samples_in_win"].as<int>();
	int nBootstrap = vm["nbootstrap"].as<int>();
	int nSamplesPerId = vm["n_samples_per_id"].as<int>();

	if (nSamplesPerId != 1 && nSamplesPerId != 0)
		MTHROW_AND_ERR("Currently, n_samples_per_id can be 1 or 0\n");
	if (vm.count("prob") + vm.count("lift") != 1)
		MTHROW_AND_ERR("Exactly one of prob and lift must be given\n");
	if (vm.count("raw") + vm.count("samples") != 1)
		MTHROW_AND_ERR("Exactly one of raw and samples required\n");

	// Get Score
	vector<pair<int, float>> preds;

	if (vm.count("samples")) {
		string samplesFile = vm["samples"].as<string>();
		MedSamples samples;
		if (samples.read_from_file(samplesFile) != 0)
			MTHROW_AND_ERR("Cannot read samples from \'%s\'\n", samplesFile.c_str());

		// Get Preds
		// Read cohort file and get preds
	}
	else {
		string rawFile = vm["raw"].as<string>();
		read_preds(rawFile, preds);
	}

	// Get target prob
	float prob;
	if (vm.count("prob"))
		prob = vm["prob"].as<float>();
	else {
		float lift = vm["lift"].as<float>();
		int n = preds.size();
		int nPos = 0;
		for (size_t i = 0; i < preds.size(); i++) {
			if (preds[i].first == 1)
				nPos++;
		}
		prob = lift * (nPos + 0.0) / n;
	}

	// Get Score
	float score;
	vector<float> score_ci(2);
	score = get_score(preds, minCases, minSamples, nBootstrap, prob, score_ci);

	float pr = score2pr(preds, score);
	vector<float> pr_ci = { score2pr(preds,score_ci[0]), score2pr(preds,score_ci[1]) };

	cout << "Score for Prob = " << prob << " : Score = " << score << "[" << score_ci[0] << "," << score_ci[1] << "]\tPR = " << pr << "[" << pr_ci[1] << "," << pr_ci[0] << "]\n";
	return 0;
}

// Analyze Command Line
void read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("samples", po::value<string>(), "file of samples with predictions")
			("raw", po::value<string>(), "Raw output of bootstrap_app")
			("nbootstrap", po::value<int>()->default_value(500), "number of bootstrap runs")
			("prob", po::value<float>(), "target probability")
			("lift", po::value<float>(), "target lift")
			("min_case_in_win", po::value<int>()->default_value(50), "minimal number of cases in window")
			("min_samples_in_win", po::value<int>()->default_value(500), "minimal number of samples in window")
			("n_samples_per_id", po::value<int>()->default_value(1), "number of samples to take per id in bootstraping. currently 1 or 0 for all")
			("seed", po::value<int>()->default_value(123456), "seed for globalRNG")
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

// Read raw predictions
void read_preds(string& rawFile, vector<pair<int, float>>& preds) {
	
	ifstream inf(rawFile);
	if (!inf.is_open())
		MTHROW_AND_ERR("Cannot open \'%s\' for reading\n", rawFile.c_str());

	vector<string> fields;
	string line;

	preds.clear();
	while (getline(inf, line)) {
		boost::split(fields, line, boost::is_any_of(" \t"));
		preds.push_back({ stoi(fields[2]),stof(fields[1]) });
	}

	sort(preds.begin(), preds.end(), [](const pair<int, float> &c1, const pair<int, float> &c2) {return c1.second > c2.second;});
}

float get_score(vector<pair<int, float>>& preds, int minCases, int minSamples, int nBootstrap, float prob, vector<float>& score_ci) {

	vector<float> scores;
	int nScores = (int)preds.size();
	scores.resize(nBootstrap);

#pragma omp parallel for
	for (int i = 0; i < nBootstrap; i++) {
		vector<int> indices;
		bootstrap_sample(nScores,indices);
		scores[i] = get_score(preds,indices, minCases, minSamples, prob);
	}

	// Get mean and CI
	sort(scores.begin(), scores.end());
	float sum = 0;
	for (int i = 0; i < nBootstrap; i++)
		sum += scores[i];

	score_ci[0] = scores[(int)(0.025 * nBootstrap)];
	score_ci[1] = scores[(int)(0.975 * nBootstrap)];

	return sum / nBootstrap;
}

void bootstrap_sample(int n, vector<int>& indices) {

	indices.resize(n);
	for (int i = 0; i < n; i++)
		indices[i] = (int)(n * ((globalRNG::rand() / (globalRNG::max() + 0.0))));
	sort(indices.begin(), indices.end());
}

# define QUIT_FACTOR 0.1
float get_score(vector<pair<int, float>>& preds, vector<int>& indices, int minCases, int minSamples, float prob) {

	int start = 0, end = 0;
	int nCases = 0, nSamples = 0;
	int n = (int)indices.size();

	// Initial window
	while (end < n && (nCases < minCases || nSamples < minSamples)) {
		nSamples++;
		if (preds[indices[end]].first == 1)
			nCases++;
		end++;
	}

	if (nCases < minCases || nSamples < minSamples)
		MTHROW_AND_ERR("Cannot find enough cases/samples for calculating score\n");

	float optP = (nCases + 0.0) / nSamples;
	float dist = fabs(optP - prob);
	float score = 0.5 * (preds[indices[start]].second + preds[indices[end]].second);

	float p= optP;
	while (1) {

		// Try to move windows start
		while (nSamples > minSamples) {
			nSamples--;
			if (preds[indices[start]].first == 1)
				nCases--;
			start++;

			if (nCases < minCases)
				break;

			p = (nCases + 0.0) / nSamples;
			if (fabs(p - prob) < dist) {
				optP = p;
				dist = fabs(p - prob);
				score = 0.5 * (preds[indices[start]].second + preds[indices[end]].second);
			}
		}

		// Are we done ?
		if (end == n - 1 || p <= QUIT_FACTOR * prob)
			break;

		// Try to move windows end
		while (end < n - 1) {
			nSamples++;
			if (preds[indices[end]].first == 1)
				nCases++;
			end++;

			if (nCases >= minCases && nSamples >= minSamples) {
				float p = (nCases + 0.0) / nSamples;
				if (fabs(p - prob) < dist) {
					optP = p;
					dist = fabs(p - prob);
					score = 0.5 * (preds[indices[start]].second + preds[indices[end]].second);
				}
				break;
			}
		}
	}

	return score;
}

float score2pr(vector<pair<int, float>>& preds, float score) {

	int n = (int)preds.size();
	int nPos = 0;
	while (preds[nPos].second >= score)
		nPos++;
	return ((int)(10000.0*(nPos + 0.0) / n)) / 100.0;
}
