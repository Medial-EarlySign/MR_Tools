#include "Cmd_Args.h"
#include <boost/filesystem.hpp>
#include <MedUtils/MedUtils/MedPlot.h>
#include <MedIO/MedIO/MedIO.h>
#include <MedAlgo/MedAlgo/BinSplitOptimizer.h>
#include <MedProcessTools/MedProcessTools/MedFeatures.h>

#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

float NormalizeData(map<float, float> &data) {
	float totSum = 0;
	for (auto it = data.begin(); it != data.end(); ++it)
		totSum += it->second;
	for (auto it = data.begin(); it != data.end(); ++it)
		data[it->first] = it->second / totSum;
	return totSum;
}


int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;
	boost::filesystem::create_directories(args.output);
	MedSamples samples;
	MedFeatures matrix;
	if (args.feature_name.empty())
		samples.read_from_file(args.input);
	else {
		MLOG("Reading MedFeatures\n");
		matrix.read_from_csv_mat(args.input);
		samples.import_from_sample_vec(matrix.samples);
		if (args.feature_name == "pred_0")
			args.feature_name = "";
	}

	unordered_set<float> outcome_opt;
	for (size_t i = 0; i < samples.idSamples.size(); ++i)
		for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j)
			outcome_opt.insert(samples.idSamples[i].samples[j].outcome);
	string res = "%1.0f";
	for (float a : outcome_opt)
		if (abs(a - int(a)) > 0.0001) {
			res = "%1.3f";
			break;
		}

	//create outcome graphs for preds: TODO: for each pred
	unordered_map<float, vector<float>> outcome_preds;
	string feat_name = args.feature_name;
	if (args.feature_name.empty()) {
		for (size_t i = 0; i < samples.idSamples.size(); ++i)
			for (size_t j = 0; j < samples.idSamples[i].samples.size(); ++j) {
				if (samples.idSamples[i].samples[j].prediction.empty())
					MTHROW_AND_ERR("Error samples has no pred\n");
				outcome_preds[samples.idSamples[i].samples[j].outcome].push_back(samples.idSamples[i].samples[j].prediction[0]);
			}
	}
	else {
		vector<string> fnames;
		matrix.get_feature_names(fnames);
		feat_name = fnames[find_in_feature_names(fnames, args.feature_name)];
		const vector<float> &data_vec = matrix.data.at(feat_name);
		if (data_vec.size() != matrix.samples.size())
			MTHROW_AND_ERR("Error samples doesn't match feature name\n");
		for (size_t i = 0; i < matrix.samples.size(); ++i) {
			outcome_preds[matrix.samples[i].outcome].push_back(data_vec[i]);
		}
	}
	map<float, vector<pair<float, float>>> scores_dist;
	string y_label = "Percent";
	for (auto &it : outcome_preds)
	{
		vector<pair<float, float>> &graph = scores_dist[it.first];
		vector<float> &data = it.second;
		//bin values:
		if (!args.binning.empty()) {
			BinSettings bin_s;
			bin_s.init_from_string(args.binning);
			if (!args.binning.empty())
				medial::process::split_feature_to_bins(bin_s, data, {}, data);
		}
		map<float, float> hist = BuildHist(data);

		if (args.normalize)
			NormalizeData(hist);
		else
			y_label = "Count";

		//populate graph data
		for (const auto &it : hist) {
			if (!args.normalize)
				graph.push_back(pair<float, float>(it.first, it.second));
			else
				graph.push_back(pair<float, float>(it.first, 100 * it.second));
		}
	}

	vector<string> ser_names = { "controls", "cases" };
	vector<vector<pair<float, float>>> scores_dist_graphs;
	scores_dist_graphs.reserve(scores_dist.size());
	for (auto &it : scores_dist)
		scores_dist_graphs.push_back(it.second);

	if (outcome_opt.size() != 2) {
		ser_names.clear();
		ser_names.reserve(scores_dist.size());
		for (auto &it : scores_dist)
			ser_names.push_back("outcome=" + medial::print::print_obj(it.first, res));
	}

	string cap = "score";
	string fnmae_cap = "score";
	if (!args.feature_name.empty()) {
		cap = feat_name;
		fnmae_cap = args.feature_name;
	}
	fix_filename_chars(&fnmae_cap);
	string content_html = "";
	if (!args.html_template.empty()) {
		ifstream fr(args.html_template);
		if (!fr.good())
			MTHROW_AND_ERR("Error - can't open %s for reading\n", args.html_template.c_str());
		std::stringstream strStream;
		strStream << fr.rdbuf(); //read the file
		content_html = strStream.str(); //str holds the content of the file
		fr.close();
	}
	createScatterHtmlGraph(args.output + path_sep() + fnmae_cap + "_dist.html", scores_dist_graphs, cap + "_dist",
		cap, y_label, ser_names, 0, "scatter", "markers", content_html);

	return 0;
}