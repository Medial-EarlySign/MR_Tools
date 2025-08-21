#define _CRT_SECURE_NO_WARNINGS

#include "PanelCompleter.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
extern MedLogger global_logger;


float my_round(float value, float res, float factor) {

	char svalue[STRING_LEN];
	value /= factor;
	if (res == (float) 1.0)
		sprintf(svalue, "%.0f", value);
	else if (res == (float) 0.1)
		sprintf(svalue, "%.1f", value);
	else if (res == (float) 0.01)
		sprintf(svalue, "%.2f", value);
	else if (res == (float) 10.0)
		sprintf(svalue, "%.0f", float(int(value / 10) * 10));
	else {
		fprintf(stderr, "Cannot handle resolution %f\n", res);
		exit(-1);
	}

	value = (float)atof(svalue)*factor;
	sprintf(svalue, "%.2f", value);
	return (float)atof(svalue);

}


int read_thin_to_medial(string file_name, map<string, string>& trans) {

	fprintf(stderr, "Reading %s\n", file_name.c_str());

	FILE *fp = fopen(file_name.c_str(), "r");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", file_name.c_str());
		return -1;
	}

	char thin[STRING_LEN];
	char medial[STRING_LEN];

	fscanf(fp, "%*[^\n]\n"); // skip header
	char line[1024];
	while (fgets(line, sizeof line, fp)) {
		int rc = sscanf(line, "%s\t%s\n", thin, medial);

		if (rc != 2)
			fprintf(stderr, "skipping line [%s], rc = %d\n", line, rc);
		else if (string(thin).compare(medial) != 0) {
			fprintf(stderr, "[%s]\t[%s]\n", thin, medial);
			trans[thin] = medial;
		}
	}

	fclose(fp);
	return 0;
}
int main(int argc, char *argv[])
{
	// Running parameters
	po::variables_map vm;
	assert(read_run_params(argc, argv, vm) != -1);

	map<string, string> thin_to_medial;
	if (vm["codes_to_signals_file"].as<string>() != "")
		assert(read_thin_to_medial(vm["codes_to_signals_file"].as<string>(), thin_to_medial) != -1);
	else MWARN("codes_to_signals_file not specified\n");

	// Resolutions
	map<string, float> res;
	map<string, float> fac;
	assert(read_resolutions_new(vm["instructions_file"].as<string>(), res, fac) != -1);
	//assert(read_resolutions(vm["instructions_file"].as<string>(), thin_to_medial, res, fac) != -1);

	// Read repository
	MedRepository rep;
	string config_file = vm["repository_file"].as<string>();

	vector<string> vpanel(std::begin(panel), std::end(panel));
	vpanel.push_back("GENDER");
	vpanel.push_back("BYEAR");
	if (rep.read_all(config_file, vector<int>(), vpanel) < 0) {
		fprintf(stderr, "Cannot read all repository %s\n", config_file.c_str());
		return -1;
	}

	// Files
	string out_file = vm["out_folder"].as<string>() + "/" + vm["out_prefix"].as<string>() + "_completed.csv";
	string err_file = vm["out_folder"].as<string>() + "/" + vm["out_prefix"].as<string>() + "_mismatched.csv";
	string matched_file = vm["out_folder"].as<string>() + "/" + vm["out_prefix"].as<string>() + "_matched.csv";
	string exist_file = vm["out_folder"].as<string>() + "/" + vm["out_prefix"].as<string>() + "_exist.csv";


	FILE *out_fp = fopen(out_file.c_str(), "w");
	FILE *err_fp = fopen(err_file.c_str(), "w");
	FILE *matched_fp = fopen(matched_file.c_str(), "w");
	if (out_fp == NULL || err_fp == NULL) {
		fprintf(stderr, "Cannot open %s for writing\n", out_file.c_str());
		return -1;
	}
	FILE *exist_fp = NULL;
	if (vm["show_existing_signals"].as<int>() == 1)
		exist_fp = fopen(exist_file.c_str(), "w");

	// Loop 
	int size = (int)rep.index.pids.size();
	//size = 100000;
	fprintf(stderr, "Working on %d ids\n", size);

	map<string, int> completions;
	map<string, int> mismatches;
	map<string, int> matches;
	for (int i = 0; i < size; i++) {
		int id = rep.index.pids[i];
		if (process_id(rep, id, res, fac, out_fp, err_fp, exist_fp, completions, mismatches, matches) == -1) {
			fprintf(stderr, "Failed in processing id %d\n", id);
			return -1;
		}
		if (i % 250000 == 250000 - 1) {
			fprintf(stderr, "Processed id #%d ... ", i);
		}
	}
	fprintf(stderr, "\n");

	for (auto it = completions.begin(); it != completions.end(); it++)
		fprintf(matched_fp, "%s,completed,%d\n", it->first.c_str(), it->second);

	for (auto it = mismatches.begin(); it != mismatches.end(); it++)
		fprintf(matched_fp, "%s,mismatched,%d\n", it->first.c_str(), it->second);

	for (auto it = matches.begin(); it != matches.end(); it++)
		fprintf(matched_fp, "%s,matched,%d\n", it->first.c_str(), it->second);

	fclose(out_fp);
	fclose(err_fp);
	fclose(matched_fp);
	if (exist_fp != NULL) {
		fclose(exist_fp);
		fprintf(stderr, "wrote %s\n", exist_file.c_str());
	}

	fprintf(stderr, "wrote %s\n", out_file.c_str());
	fprintf(stderr, "wrote %s\n", err_file.c_str());
	fprintf(stderr, "wrote %s\n", matched_file.c_str());
	return 0;
}

int read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("repository_file", po::value<string>()->required(), "repository file")
			("instructions_file", po::value<string>()->required(), "Instructions file per signal with resolutions")
			("codes_to_signals_file", po::value<string>()->default_value(""), "thin to medial signal names translation table file")
			("show_existing_signals", po::value<int>()->default_value(0), "output existing signals for debug")
			("out_folder", po::value<string>()->required(), "output file")
			("out_prefix", po::value<string>()->default_value("thin"), "output prefix")
			;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			return 0;

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


int egfr_complete(int id, int date, int age, int gender, map<string, float>& cur_panel,
	map<string, float>& res, map<string, float>& fac, map<string, int>& completions, map<string, int>& mismatches,
	map<string, int>& matches, map<string, int>& attempted, FILE *out_fp, FILE *err_fp) {

	vector<string> names = { "eGFR_CKD_EPI", "eGFR_MDRD" };
	return 0;

	if (cur_panel.find("Creatinine") != cur_panel.end() && cur_panel["Creatinine"] != 0.0) {
		map<string, float> egfrs;
		egfrs["eGFR_CKD_EPI"] = get_eGFR_CKD_EPI(age, cur_panel["Creatinine"], gender);
		egfrs["eGFR_MDRD"] = get_eGFR_MDRD(age, cur_panel["Creatinine"], gender);
		if (!isfinite(egfrs["eGFR_CKD_EPI"]) || !isfinite(egfrs["eGFR_MDRD"]))
			MTHROW_AND_ERR("ERROR - infinite eGFR was completed:\npid: [%d] age: [%d] gender: [%d] creatinine: [%f]\n", id, age, gender, cur_panel["Creatinine"]);

		for (string xname : names) {
			if (attempted.find(xname) != attempted.end())
				continue;
			attempted[xname] = 1;
			if (cur_panel.find(xname) == cur_panel.end() || cur_panel[xname] == 0.0) {
				cur_panel[xname] = my_round(egfrs[xname], res[xname], fac[xname]);
				fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, xname.c_str(), date, cur_panel[xname], xname.c_str());
				completions[xname]++;
				return 1;
			}
			else {
				float maxi = cur_panel[xname] + res[xname];
				float mini = cur_panel[xname] - res[xname];
				if (egfrs[xname] > maxi || egfrs[xname] < mini) {
					fprintf(err_fp, "%d\t%s\t%d\t%f\t%f\t%f\n", id, xname.c_str(), date, my_round(egfrs[xname], res[xname], fac[xname]), mini, maxi);
					mismatches[xname] ++;
				}
				else
					matches[xname]++;
			}
		}
	}

	return 0;
}


int reciprocal_complete(int id, int date, map<string, float>& cur_panel, float factor, const string& xname, const string& yname, const string& type,
	map<string, float>& res, map<string, float>& fac, map<string, int>& completions, map<string, int>& mismatches, map<string, int>& matches, map<string, int>& attempted, FILE *out_fp, FILE *err_fp) {

	// Do we have both ?

	if (cur_panel.find(yname) != cur_panel.end() && cur_panel.find(xname) != cur_panel.end()) {
		if (attempted.find(type) == attempted.end()) {
			attempted[type] = 1;
			float maxi = factor / (cur_panel[yname] - res[yname]) + res[xname];
			float mini = factor / (cur_panel[yname] + res[yname]) - res[xname];
			if (cur_panel[xname] > maxi || cur_panel[xname] < mini)
			{
				fprintf(err_fp, "%d\t%s\t%d\t%f\t%f\t%f\n", id, xname.c_str(), date, my_round(cur_panel[xname], res[xname], fac[xname]), mini, maxi);
				mismatches[type] ++;
			}
			else
				matches[type] ++;
		}
		return 0;
	}


	// Can We complete ?
	if (cur_panel.find(yname) != cur_panel.end() && cur_panel[yname] != 0.0) {
		cur_panel[xname] = my_round(factor / cur_panel[yname], res[xname], fac[xname]);
		fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, xname.c_str(), date, cur_panel[xname], type.c_str());
		completions[xname]++;
		attempted[type] = 1;
		return 1;
	}
	else if (cur_panel.find(xname) != cur_panel.end() && cur_panel[xname] != 0.0) {
		cur_panel[yname] = my_round(factor / cur_panel[xname], res[yname], fac[yname]);
		fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, yname.c_str(), date, cur_panel[yname], type.c_str());
		completions[yname]++;
		attempted[type] = 1;
		return 1;
	}

	return 0;
}



// Complete X = factor*Y/Z ; Y = X*Z/factor ; Z = factor*Y/X
int triplet_complete(int id, int date, map<string, float>& cur_panel, float factor, const string& xname, const string& yname, const string& zname, const string& type,
	map<string, float>& res, map<string, float>& fac, map<string, int>& completions, map<string, int>& mismatches, map<string, int>& matches, map<string, int>& attempted, FILE *out_fp, FILE *err_fp) {

	// Do we have all three ?

	if (cur_panel.find(zname) != cur_panel.end() && cur_panel.find(yname) != cur_panel.end() && cur_panel.find(xname) != cur_panel.end()) {
		if (attempted.find(type) == attempted.end()) {
			attempted[type] = 1;
			if (cur_panel[zname] != 0) {
				float maxi = factor * (cur_panel[yname] + res[yname]) / (cur_panel[zname] - res[zname]) + res[xname];
				float mini = factor * (cur_panel[yname] - res[yname]) / (cur_panel[zname] + res[zname]) - res[xname];
				if (cur_panel[xname] > maxi || cur_panel[xname] < mini)
				{
					fprintf(err_fp, "%d\t%s\t%d\t%f\t%f\t%f\n", id, xname.c_str(), date, my_round(cur_panel[xname], res[xname], fac[xname]), mini, maxi);
					mismatches[type] ++;
				}
				else
					matches[type] ++;
			}
		}

		return 0;
	}


	// Can We complete ?
	if (cur_panel.find(yname) != cur_panel.end() && cur_panel.find(zname) != cur_panel.end()) {
		if (cur_panel[zname] != 0) {
			cur_panel[xname] = my_round(factor * cur_panel[yname] / cur_panel[zname], res[xname], fac[xname]);
			fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, xname.c_str(), date, cur_panel[xname], type.c_str());
			completions[xname]++;
			attempted[type] = 1;
			return 1;
		}
	}
	else if (cur_panel.find(xname) != cur_panel.end() && cur_panel.find(zname) != cur_panel.end()) {
		cur_panel[yname] = my_round(cur_panel[xname] * cur_panel[zname] / factor, res[yname], fac[yname]);
		fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, yname.c_str(), date, cur_panel[yname], type.c_str());
		completions[yname]++;
		attempted[type] = 1;
		return 1;
	}
	else if (cur_panel.find(yname) != cur_panel.end() && cur_panel.find(xname) != cur_panel.end()) {
		if (cur_panel[xname] != 0) {
			if (zname.compare("HeightMetersSquared") == 0) {
				cur_panel[zname] = factor * cur_panel[yname] / cur_panel[xname];
				cur_panel["Height"] = my_round(sqrt(cur_panel[zname]) * 100, res["Height"], fac["Height"]);
				fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, "Height", date, cur_panel["Height"], type.c_str());
			}
			else {
				cur_panel[zname] = my_round(factor * cur_panel[yname] / cur_panel[xname], res[zname], fac[zname]);
				fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, zname.c_str(), date, cur_panel[zname], type.c_str());
			}
			completions[zname]++;
			attempted[type] = 1;
			return 1;
		}
	}

	return 0;
}

int sum_complete(int id, int date, map<string, float>& cur_panel, string the_sum, vector<string> summands, const string& type,
	map<string, int>& attempted, map<string, float>& res, map<string, float>& fac, map<string, int>& completions, map<string, int>& mismatches, map<string, int>& matches,
	FILE *out_fp, FILE *err_fp) {

	int npresent = 0;
	float sum = 0, maxi = 0, mini = 0;
	for (int i = 0; i < summands.size(); i++) {
		string num = summands[i];
		if (cur_panel.find(num) != cur_panel.end()) {
			npresent++;
			maxi += cur_panel[num] + res[num];
			mini += cur_panel[num] - res[num];
			sum += cur_panel[num];
		}
	}

	// Do we have all values ?
	if (npresent == summands.size() && cur_panel.find(the_sum) != cur_panel.end()) {
		if (attempted.find(type) == attempted.end()) {
			attempted[type] = 1;
			mini -= res[the_sum];
			maxi += res[the_sum];
			float sum_final = my_round(sum, res[the_sum], fac[the_sum]);
			if (sum_final < mini || sum_final > maxi) {
				fprintf(err_fp, "%d\t%s\t%d\t%f\t%f\t%f\n", id, the_sum.c_str(), date, sum_final, mini, maxi);
				mismatches[type] ++;
			}
			else
				matches[type] ++;
		}
		return 0;
	}

	// Can we complete ?
	if (npresent == summands.size() && cur_panel.find(the_sum) == cur_panel.end()) {
		float sum_final = my_round(sum, res[the_sum], fac[the_sum]);
		fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, the_sum.c_str(), date, sum_final, type.c_str());
		cur_panel[the_sum] = sum_final;
		completions[type] ++;
		return 1;

	}
	else if (npresent == summands.size() - 1 && cur_panel.find(the_sum) != cur_panel.end()) {
		for (int i = 0; i < summands.size(); i++) {
			string num = summands[i];
			if (cur_panel.find(num) == cur_panel.end() && attempted.find(num) == attempted.end()) {
				float val = cur_panel[the_sum] - sum;
				if (val > 0) {
					if (num.compare("VLDL") == 0) {
						val = my_round(val, res["Triglycerides"], fac["Triglycerides"]);
						fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, "Triglycerides", date, val*5.0, type.c_str());
						cur_panel["Triglycerides"] = val;
						completions["Triglycerides"] ++;
					}
					else {
						val = my_round(val, res[num], fac[num]);
						fprintf(out_fp, "%d\t%s\t%d\t%.2f\tcompleted_%s\n", id, num.c_str(), date, val, type.c_str());
					}
					cur_panel[num] = val;
					completions[num] ++;
					return 1;
				}
				else
					attempted[num] = 1;
			}
		}
	}

	return 0;

}

int process_id(MedRepository& rep, int id, map<string, float>& res, map<string, float>& fac, FILE *out_fp, FILE *err_fp, FILE *exist_fp, map<string, int>& completions, map<string, int>& mismatches, map<string, int>& matches) {

	// Build panels
	map<int, map<string, float> > panels;
	for (int i = 0; i < panel_size; i++) {
		UniversalSigVec signal;
		rep.uget(id, panel[i], signal);
		for (int j = 0; j < signal.len; j++) {
			if (string(panel[i]).compare("Triglycerides") == 0)
				panels[signal.Time(j)]["VLDL"] = signal.Val(j) / 5.0;
			else if (string(panel[i]).compare("Height") == 0)
				panels[signal.Time(j)]["HeightMetersSquared"] = (signal.Val(j) / 100.0)*(signal.Val(j) / 100.0);
			panels[signal.Time(j)][panel[i]] = signal.Val(j);
		}
	}

	if (exist_fp != NULL)
		for (auto p : panels) {
			for (auto s : p.second) {
				fprintf(exist_fp, "%d\t%s\t%d\t%f\n", id, s.first.c_str(), p.first, s.second);
			}
		}
	int gender_sid = rep.sigs.sid("GENDER");
	int byear_sid = rep.sigs.sid("BYEAR");
	int gender = medial::repository::get_value(rep, id, gender_sid);
	assert(gender > 0);
	int byear = medial::repository::get_value(rep, id, byear_sid);
	assert(byear > 0);

	// Copmlete panels
	for (auto it = panels.begin(); it != panels.end(); it++) {
		map<string, float>& cur_panel = it->second;
		int date = it->first;
		int age = int(date) / 10000 - byear;

		int try_again = 1;
		map<string, int> attempted;

		while (try_again) {
			try_again = 0;

			try_again += egfr_complete(id, date, age, gender, cur_panel, res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

			// MCV = 10*HCT/RBC
			try_again += triplet_complete(id, date, cur_panel, 10, "MCV", "Hematocrit", "RBC", "MCV=10*HCT/RBC", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

			// MCH = 10 * HGB / RBC
			try_again += triplet_complete(id, date, cur_panel, 10, "MCH", "Hemoglobin", "RBC", "MCH=10*HGB/RBC", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

			// MCHC = 100 * HGB / HCT
			try_again += triplet_complete(id, date, cur_panel, 100, "MCHC-M", "Hemoglobin", "Hematocrit", "MCHC=100*HGB/HCT", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

			vector<string> white_nums{ "Eosinophils#","Neutrophils#","Lymphocytes#","Monocytes#","Basophils#" };
			vector<string> white_percs{ "Eosinophils%","Neutrophils%","Lymphocytes%","Monocytes%","Basophils%" };

			// WBC = SUM(#s)
			try_again += sum_complete(id, date, cur_panel, "WBC", white_nums, "WBC=sum(whites)", attempted, res, fac, completions, mismatches, matches, out_fp, err_fp);

			// White subtypes - 
			for (int j = 0; j < white_nums.size(); j++) {
				string num = white_nums[j];
				string perc = white_percs[j];

				// Perc = 100 * Num/WBC ;
				try_again += triplet_complete(id, date, cur_panel, 100, perc, num, "WBC", num, res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			}
		}

		triplet_complete(id, date, cur_panel, 100, "MPV", "Platelets_Hematocrit", "Platelets", "MPV=100*PH/P", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

		try_again = 1;
		while (try_again) {
			try_again = 0;
			try_again += triplet_complete(id, date, cur_panel, 1, "HDL_over_Cholesterol", "HDL", "Cholesterol", "HC=HDL/Chol", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			try_again += triplet_complete(id, date, cur_panel, 1, "Cholesterol_over_HDL", "Cholesterol", "HDL", "CH=Cholesterol/HDL", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			try_again += triplet_complete(id, date, cur_panel, 1, "HDL_over_LDL", "HDL", "LDL", "HL=HDL/LDL", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			try_again += triplet_complete(id, date, cur_panel, 1, "LDL_over_HDL", "LDL", "HDL", "LH=LDL/HDL", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			try_again += triplet_complete(id, date, cur_panel, 1, "HDL_over_nonHDL", "HDL", "NonHDLCholesterol", "HN=HDL/NHDL", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			try_again += reciprocal_complete(id, date, cur_panel, 1, "HDL_over_LDL", "LDL_over_HDL", "HL=1/LH", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);
			try_again += reciprocal_complete(id, date, cur_panel, 1, "HDL_over_Cholesterol", "Cholesterol_over_HDL", "HC=1/CH", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

			vector<string> bad_good = { "NonHDLCholesterol", "HDL" };
			try_again += sum_complete(id, date, cur_panel, "Cholesterol", bad_good, "Chol=NH+HDL", attempted, res, fac, completions, mismatches, matches, out_fp, err_fp);

			vector<string> chol_parts = { "LDL", "HDL", "VLDL" };
			try_again += sum_complete(id, date, cur_panel, "Cholesterol", chol_parts, "Chol=LDL+HDL+VLDL", attempted, res, fac, completions, mismatches, matches, out_fp, err_fp);

		}
		try_again += triplet_complete(id, date, cur_panel, 1, "BMI", "Weight", "HeightMetersSquared", "BMI=Weight/(Height/100)^2", res, fac, completions, mismatches, matches, attempted, out_fp, err_fp);

		vector<string> sodium_parts = { "Bicarbonate", "AnionGap", "Cl" };
		//ido 20170315 - removing AnionGap completion, because it generated a Gaussian with mean 10.0, instead of the expected 13.0
		//sum_complete(id, date, cur_panel, "Na", sodium_parts, "Na=AnionGap+Cl+Bicarbonate", attempted, res, completions, mismatches, matches, out_fp, err_fp);
	}

	return 0;
}


int read_resolutions(string file_name, map<string, string>& thin_to_medial, map<string, float>& res, map<string, float>& fac) {

	fprintf(stderr, "Reading %s\n", file_name.c_str());

	FILE *fp = fopen(file_name.c_str(), "r");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", file_name.c_str());
		return -1;
	}

	string signal;
	float resolution;
	float final_factor;

	fscanf(fp, "%*[^\n]\n"); // skip header
	char line[1024];
	while (fgets(line, sizeof line, fp)) {
		//Name	Unit	Resolution	Ignore	Factors	FinalFactor	SupposeMean	TrimMax
		vector<string> strs;
		boost::split(strs, line, boost::is_any_of("\t"));

		if (strs.size() < 3) {
			fprintf(stderr, "Failed reading [%s], line [%s] has length [%zu]\n", file_name.c_str(), line, strs.size());
			return -1;
		}
		else {
			signal = strs[0]; resolution = atof(strs[2].c_str());
			//fprintf(stderr, "[%s]\t[%f]\n", signal.c_str(), resolution);
		}
		final_factor = 1.0;
		if (strs.size() >= 6 && strs[5].size() > 0) {
			final_factor = atof(strs[5].c_str());
			if (final_factor == 0.0)
				final_factor = 1.0;
		}

		if (thin_to_medial.find(signal) != thin_to_medial.end()) {
			fprintf(stderr, "renaming [%s] to [%s]\n", signal.c_str(), thin_to_medial[signal].c_str());
			res[thin_to_medial[signal]] = resolution;
			fac[thin_to_medial[signal]] = final_factor;
		}
		else {
			res[signal] = resolution;
			fac[signal] = final_factor;
		}
	}

	for (int i = 0; i < panel_size; i++) {
		if (res.find(panel[i]) == res.end()) {
			fprintf(stderr, "Cannot find resolution for %s\n", panel[i]);
			return -1;
		}
		else {
			float n = (float)123.456;
			fprintf(stderr, "[%s] with res [%f, %f] will round [%f] to [%.2f]\n", panel[i], res[panel[i]], fac[panel[i]], n, my_round(n, res[panel[i]], fac[panel[i]]));
		}
	}
	fprintf(stderr, "Found resolutions for the entire panel\n");
	fclose(fp);
	return 0;
}

int read_resolutions_new(string file_name, map<string, float>& res, map<string, float>& fac) {

	fprintf(stderr, "Reading %s\n", file_name.c_str());

	FILE *fp = fopen(file_name.c_str(), "r");
	if (fp == NULL) {
		fprintf(stderr, "Cannot open %s for reading\n", file_name.c_str());
		return -1;
	}

	string signal;
	int round;
	float resolution;
	float final_factor;

	fscanf(fp, "%*[^\n]\n"); // skip header
	char line[1024];
	while (fgets(line, sizeof line, fp)) {
		//Name	Unit	Round
		vector<string> strs;
		boost::split(strs, line, boost::is_any_of("\t"));

		if (strs.size() < 3) {
			fprintf(stderr, "Failed reading [%s], line [%s] has length [%zu]\n", file_name.c_str(), line, strs.size());
			return -1;
		}
		else {
			signal = strs[0]; round = stoi(strs[2]);
			//fprintf(stderr, "[%s]\t[%d]\n", signal.c_str(), round);
		}
		final_factor = 1.0;
		resolution = 1 / pow(10, round);
		//fprintf(stderr, "[%s]\t[%f]\n", signal.c_str(), resolution);
		res[signal] = resolution;
		fac[signal] = final_factor;
	}

	for (int i = 0; i < panel_size; i++) {
		if (res.find(panel[i]) == res.end()) {
			fprintf(stderr, "Cannot find resolution for %s\n", panel[i]);
			return -1;
		}
		else {
			float n = (float)123.456;
			fprintf(stderr, "[%s] with res [%f, %f] will round [%f] to [%.2f]\n", panel[i], res[panel[i]], fac[panel[i]], n, my_round(n, res[panel[i]], fac[panel[i]]));
		}
	}
	fprintf(stderr, "Found resolutions for the entire panel\n");
	fclose(fp);
	return 0;
}