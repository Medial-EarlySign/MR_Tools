//
// Parser for Rambam Data
//
//

#define AM_DLL_IMPORT

#include <string>
#include <iostream>
#include <boost/program_options.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/algorithm/string/replace.hpp>
#include <boost/algorithm/string/join.hpp>

#include <Logger/Logger/Logger.h>
#include <MedUtils/MedUtils/MedIO.h>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/xml_parser.hpp>
#include <boost/regex.hpp>
#include <RapidXML/rapidxml.hpp>

#include <unordered_map>


#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
using namespace std;
namespace po = boost::program_options;
namespace pt = boost::property_tree;
using namespace rapidxml;

int med_stoi(const string& _Str) {
	try {
		return stoi(_Str);
	}
	catch (exception e) {
		MTHROW_AND_ERR("invalid stoi argument [%s]\n", _Str.c_str());
	}
}

//=========================================================================================================
struct parser_params {
	map<int, long long> id2nr;
	map<long long, int> nr2id;
	vector<int> pids;
	string in_dir = ".";
	string out_dir = ".";
	string prefix = "";
	int outpatient_dept_code = 100000;

	// dictionaries created while passing through data
	unordered_map<string, int> units; // units names and counts
	unordered_map<string, string> code2testname; // codes to tests names map
	unordered_map<string, int> tests; // codes and counts
	unordered_map<string, map<string, int>> tests_units_hist; // code@unit with a map of all possible values and counts
	unordered_map<string, unordered_map<string, string>> all_dicts;
	unordered_map<string, int> outpatient_dept_to_code;

	// flags
	int get_demographics_flag = 0;
	int get_labs_flag = 0;
	int get_dicts = 0;
	int get_hists = 0;
	int get_procedures = 0;
	int get_drugs = 0;

	// output files
	ofstream f_demographics;
	ofstream f_labs;
	ofstream f_labs_units_dict;
	ofstream f_labs_tests_dict;
	ofstream f_labs_hists;
	map<string, ofstream*> f_tables;
	map<string, ofstream*> f_dicts;
	ofstream f_errors;

};

//=========================================================================================================
string hebrew_hibrish_converter(string &str)
{
	static vector<string> hibrish ={ "A","B","G","D","H","O","Z","CH","T","I","K","K","L","M","M","N","N","S","A","F","F","TS","TS","K","R","SH","T" };

	string out_s;

	//out_s = str;
	//boost::replace_all(out_s, "##", "&#");
	//return out_s;

	//MLOG("IN: %s\n", str.c_str());
	for (int i=0; i<str.size(); i++) {
		//MLOG("%d %c\n", i, str[i]);
		if (i < str.size()-6) {
			if (str[i] == '#' && str[i+1] == '#') {
				int n = med_stoi(str.substr(i+2, 4)) - 1488;
				if (n>=0 && n<hibrish.size()) out_s += hibrish[n];
				else out_s += str.substr(i, 7);
				i += 6;
			}
			else
				out_s += str[i];
		}
		else
			out_s += str[i];
	}

	return out_s;
}

//=========================================================================================================
int read_run_params(int argc, char *argv[], po::variables_map& vm) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("in_dir", po::value<string>()->default_value("/nas1/Data/RAMBAM/da_medial_patients"), "input xml files directory")
			("out_dir", po::value<string>()->default_value("."), "output directory")
			("id2nr", po::value<string>()->default_value("/nas1/UsersData/avi/MR/Tools/InPatientLoaders/Rambam/configs/rambam.id2nr"), "pid to rambam id table")
			("in_list", po::value<string>()->default_value(""), "list of input pids to work on")
			("id", po::value<int>()->default_value(-1), "working on a single id xml file")
			("create_tables", po::value<string>()->default_value("demographic,lab"), "list of tables to create : demographic , lab, transfers, drugs, diagnosis")
			("prefix", po::value<string>()->default_value("rambam_"), "prefix for files created")

			//("egfr_test", "split to a debug routine for the simple egfr algomarker")
			;


		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);

		MLOG("=========================================================================================\n");
		MLOG("Command Line:");
		for (int i=0; i<argc; i++) MLOG(" %s", argv[i]);
		MLOG("\n");
		MLOG("..........................................................................................\n");
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

//----------------------------------------------------------------------------------------
int read_id2nr(string fname, map<int, long long> &id2nr, map<long long, int> &nr2id)
{
	vector<string> s_pids, s_nrs;
	if (read_text_file_col(fname, "#", " ,\t", 0, s_pids) < 0) return -1;
	if (read_text_file_col(fname, "#", " ,\t", 1, s_nrs) < 0) return -1;
	if (s_pids.size() != s_nrs.size()) return -1;
	for (int i=0; i<s_pids.size(); i++) {
		//MLOG("%s %s\n", s_pids[i].c_str(), s_nrs[i].c_str());
		id2nr[med_stoi(s_pids[i])] = stoll(s_nrs[i]);
		nr2id[stoll(s_nrs[i])] = med_stoi(s_pids[i]);
	}
	return 0;
}


//----------------------------------------------------------------------------------------
int read_pids_list(string fname, vector<int> &pids)
{
	vector<string> s_pids;
	if (read_text_file_col(fname, "#", " ,\t", 0, s_pids) < 0) return -1;
	for (auto &s : s_pids)
		pids.push_back(med_stoi(s));
		
	return 0;
}

//========================================================================================
void arrange_date_time(string &in_t, string &out_t)
{
	out_t = in_t;
	// will arrange later when loading the repo
	/*
	boost::replace_all(out_t, " ", "");
	boost::replace_all(out_t, "-", "");
	boost::replace_all(out_t, ":", "");
	out_t = out_t.substr(0, 12);*/

}

//========================================================================================
int append_demographics_data_rapid(parser_params &prm, xml_document<> &xmldoc, int pid)
{
	string out_s;
	if (!prm.get_demographics_flag) return 0;
	string spid = to_string(pid);

	xml_node<> *node = xmldoc.first_node("Patient");
	for (xml_attribute<> *attr = node->first_attribute(); attr; attr = attr->next_attribute()) {
		string name = attr->name();
		string val = attr->value();
		if (boost::contains(name, "date")) arrange_date_time(val, val);
		if (0) MLOG("%s %s %s %s\n", spid.c_str(), node->name(), name.c_str(), val.c_str());

		out_s += spid + "\t" + name + "\t" + val + "\n";
	}

#pragma omp critical
	prm.f_demographics << out_s;
	return 0;
}

//========================================================================================
int append_labs_data_rapid(parser_params &prm, xml_document<> &xmldoc, int pid)
{
	if (!prm.get_labs_flag) return 0;
	string out_s;
	xml_node<> *root = xmldoc.first_node("Patient");
	for (xml_node<> *ev_node = root->first_node("Ev"); ev_node; ev_node = ev_node->next_sibling("Ev")) {
		string ev_type = ev_node->first_attribute("Type")->value();
		if (ev_type == "ev_lab_results_numeric" || ev_type == "ev_measurements_numeric") {

			string resultdate = "####";
			string collectiondate = "####";
			string testcode = "####";
			string testname = "####";
			string value = "####";
			string value_text = "####";
			string unit= "####";

			for (xml_node<> *pr_node = ev_node->first_node("Pr"); pr_node; pr_node = pr_node->next_sibling("Pr")) {

				string name = pr_node->first_attribute("Name")->value();
				string hier = pr_node->first_attribute("Hier")->value();
				string val = pr_node->value();

				if (name == "resultdate") arrange_date_time(val, resultdate);
				else if (name == "collectiondate") arrange_date_time(val, collectiondate);
				else if (name == "testcode") { testcode = val; testname = hier; }
				else if (name == "valueconversion") value = val;
				else if (name == "valueconversion_textual") value_text = val;
				else if (name == "measurementdate") { arrange_date_time(val, resultdate); collectiondate = resultdate; }
				else if (name == "measurementcode") { testcode = val; testname = hier; }
				else if (name == "result") value = val;
				else if (name == "result_textual") value_text = val;
				else if (name == "resultunits" || name == "valueunitcode") unit = val;

				//MLOG("####### %s %s %s %s\n", pr_node->name(), name.c_str(), hier.c_str(), val.c_str());

			}

			//value_text = hebrew_hibrish_converter(value_text);
			if (value == "Null") value = value_text;
			if (0) {
				MLOG("###### %d || %s || %s || %s || %s || %s || %s\n",
					pid, resultdate.c_str(), collectiondate.c_str(), testcode.c_str(),
					hebrew_hibrish_converter(testname).c_str(), hebrew_hibrish_converter(value).c_str(), hebrew_hibrish_converter(unit).c_str());
			}

			float v = -9999;
			try {
				v = stof(value);
				if (value.size() > 12 || ((float)((int)(100*v)))/(float)100 != v) {
					v = roundf(1000 * v)/1000;
					stringstream s;
					s << std::fixed << std::setprecision(3) << v;
					value = s.str();
				}
			}
			catch (...) {};

			for (int i=0; i<unit.size(); i++) {
				unit[i] = toupper(unit[i]);
				if (unit[i] == '\\') unit[i] = '/';
			}
			out_s += to_string(pid) + "\t" + resultdate + "\t" + collectiondate + "\t" + testcode + "\t" + unit + "\t" + value + "\n";
			//out_s += to_string(pid) + "\t" + resultdate + "\t" + collectiondate + "\t" + testcode + "\t" + hebrew_hibrish_converter(unit) + "\t" + value + "\n";

			if (prm.get_dicts) {
#pragma omp critical 
			{
				if (prm.code2testname.find(testcode) == prm.code2testname.end()) {
					prm.code2testname[testcode] = testname;
					prm.tests[testcode] = 0;
				}
				if (prm.units.find(unit) == prm.units.end()) {
					prm.units[unit] = 0;
				}
				prm.tests[testcode]++;
				prm.units[unit]++;
			}
			}

			if (prm.get_dicts) {
#pragma omp critical
			{
				string test_unit = testcode + "@" + unit;
				if (prm.tests_units_hist.find(test_unit) == prm.tests_units_hist.end()) {
					prm.tests_units_hist[test_unit] = map<string, int>();
				}
				if (prm.tests_units_hist[test_unit].find(value) == prm.tests_units_hist[test_unit].end()) {
					prm.tests_units_hist[test_unit][value] = 0;
				}
				prm.tests_units_hist[test_unit][value]++;
			}
			}
		}
	}

#pragma omp critical
	prm.f_labs << out_s;

	return 0;
}

const boost::regex e("0:.(\\d+)~1.+");
// Hier contains a leading-zeros version of val, e.g. 0: 00774~ for val 774
// which is important to save as-is as 00774 can be a different code than 774 :(
void fix_code_according_to_hier(const string& name, const string& hier, string& val) {
	boost::smatch what;
	bool match_found = boost::regex_match(hier, what, e);
	if (match_found  && what.size() > 1) {
		if (med_stoi(val) != med_stoi(what[1]))
			MTHROW_AND_ERR("name [%s] mismatch between val [%s] and hier [%s]\n", name.c_str(), val.c_str(), what[1].str().c_str());
		val = what[1];
	}

}
void extract_ev(parser_params &prm, string& ev_type, xml_node<> *pr_node, string& name, map<string, string>& name_to_hier, map<string, string>& name_to_val) {
	name = pr_node->first_attribute("Name")->value();
	string hier = pr_node->first_attribute("Hier")->value();
	string val = pr_node->value();

	fix_code_according_to_hier(name, hier, val);

	if (ev_type == "ev_outpatient_visits" && name == "departmentcode") {
#pragma omp critical 
		{
			if (prm.outpatient_dept_to_code.find(val) == prm.outpatient_dept_to_code.end())
				prm.outpatient_dept_to_code[val] = prm.outpatient_dept_code++;
			val = to_string(prm.outpatient_dept_to_code[val]);
		}
	}

	if (name.length() > 4 && (name.substr(name.length() - 4, 4) == "date" || name.substr(0, 4) == "date") )
		arrange_date_time(val, val);

	name_to_hier[name] = hier;
	name_to_val[name] = val;
}

map<string, vector<string>> table_columns;
map<string, string> events_to_table_names;

//========================================================================================
int append_all_other_tables_rapid(parser_params &prm, xml_document<> &xmldoc, int pid)
{
	string out_s;
	xml_node<> *root = xmldoc.first_node("Patient");
	string orig_pid = root->first_attribute("ID")->value();
	for (xml_node<> *ev_node = root->first_node("Ev"); ev_node; ev_node = ev_node->next_sibling("Ev")) {
		string ev_type = ev_node->first_attribute("Type")->value();
		string ev_date = ev_node->first_attribute("Time")->value();
		arrange_date_time(ev_date, ev_date);
		if (events_to_table_names.find(ev_type) != events_to_table_names.end()) {
			string table_name = events_to_table_names[ev_type];
			vector<string>& my_columns = table_columns[table_name];
			map<string, string> name_to_hier;
			map<string, string> name_to_val;
			for (xml_node<> *pr_node = ev_node->first_node("Pr"); pr_node; pr_node = pr_node->next_sibling("Pr")) {
				string name;
				extract_ev(prm, ev_type, pr_node, name, name_to_hier, name_to_val);
			}
			out_s = to_string(pid) + "\t" + orig_pid + "\t" + ev_type + "\t" + ev_date;
			for (string name : my_columns) {
				out_s += "\t" + name_to_val[name];
			}
			out_s += "\n";

#pragma omp critical 
			{
				if (prm.get_dicts) {
					for (string name : my_columns) {
						string dict_name = name;
						if (name == "surgerydepartmentcode" || name == "consultingdepartment")
							dict_name = "departmentcode";
						if (prm.all_dicts.find(dict_name) == prm.all_dicts.end())
							continue;
						auto& dict = prm.all_dicts[dict_name];
						string code = name_to_val[name];
						string hier = name_to_hier[name];
						if (code == "")
							continue;
						if (hier == "None" || hier.size() == 0) {
							if (dict.find(code) == dict.end())
								dict[code] = code;
						}
						else {
							if (dict.find(code) != dict.end() && dict[code] != code) {
								if (hier != dict[code]) {
									MERR("ERROR: !! %s code %s has 2 different names: %s AND %s\n", name.c_str(),
										code.c_str(), hier.c_str(), dict[code].c_str());
									prm.f_errors << "pid " << pid << " nr " << prm.id2nr[pid] << "ERROR: !! %s code %s has 2 different names: %s AND %s\n", name.c_str(),
										code.c_str(), hier.c_str(), dict[code].c_str();
								}
							}
							else
								dict[code] = hier;
						}
					}
				}
				*prm.f_tables[table_name] << out_s;
			}
		}
	}

	return 0;
}


//========================================================================================
void write_dict_hist_files(parser_params &prm)
{
	if (prm.get_dicts) {

		// write tests
		for (auto &s : prm.tests) {
			prm.f_labs_tests_dict << s.second << "\t" << s.first << "\t" << prm.code2testname[s.first] << "\n";
		}

		// write units
		for (auto &s : prm.units) {
			prm.f_labs_units_dict << s.second << "\t" << s.first << "\n";
		}
	}

	if (prm.get_hists) {
		for (auto &t : prm.tests_units_hist) {
			string tcode_unit = t.first;
			vector<string> f;
			boost::split(f, tcode_unit, boost::is_any_of("@"));
			string tcode = f[0];
			string tunit = f[1];
			string tname = prm.code2testname[tcode];
			for (auto &s : t.second) {
				prm.f_labs_hists << tcode_unit << "\t" << tcode << "\t" << tname << "\t" << tunit << "\t" << s.first << "\t" << s.second << "\n";
			}
		}
	}

	if (prm.get_dicts) {
		for (auto& d : prm.all_dicts) {
			string dict_name = d.first;
			for (auto &s : d.second)
				*prm.f_dicts[dict_name] << s.first << "\t" << s.second << "\n";
		}
	}
}

//========================================================================================
int create_tables_rapid(parser_params &prm) {

	// first step : open needed output files for writing
	if (prm.get_demographics_flag) prm.f_demographics.open(prm.out_dir+"/"+prm.prefix+"demographics");
	if (prm.get_labs_flag) prm.f_labs.open(prm.out_dir+"/"+prm.prefix+"labs");
	if (prm.get_dicts) prm.f_labs_units_dict.open(prm.out_dir+"/dict.labs_units");
	if (prm.get_dicts) prm.f_labs_tests_dict.open(prm.out_dir+"/dict.labs_tests");
	if (prm.get_hists) prm.f_labs_hists.open(prm.out_dir+"/hist.labs_test_unit");

	table_columns["procedures"] = { "dateperformed", "servicecode", "servicegroup", "serviceclassindicator",
		"prefix", "conditiontype", "departmentcode", "quantitydispensed", "dispanseddate", 
		"protocol", "administereddate", "surgerydepartmentcode", "performedprocedurecode", "executiondate", "surgerytype"};
	table_columns["drugs"] = { 
		"departmentcode", "quantity_value", "quantitiy_unitcode", "medicationcode",
		"formcode", "frequencycode", "routecode", "administeredflag", "administeredcount" };
	table_columns["diagnoses"] = { "conditionclassindicator", "conditioncode", "conditiontype", "suspected",
		"sequencenumber", "deceaseddate" };
	table_columns["visits"] = { "lengthofstayvalue", "departmentcode", "consultdate", "orderedconsulttype", "consultingdepartment",
		"admissionsourcecode"};

	for (auto& tc: table_columns){
		string table_name = tc.first;
		ofstream* f = new ofstream(prm.out_dir + "/" + prm.prefix + table_name);
		vector<string> com = { "admissionstartdate", "admissionenddate", "transferstartdate", "transferenddate", 
			"internalcasenum", "startdate", "enddate", };
		tc.second.insert(tc.second.end(), com.begin(), com.end());
		*f << "pid\torig_pid\tev_type\tev_time\t" << boost::algorithm::join(tc.second, "\t") << "\n";
		prm.f_tables[table_name] = f;
	}
	events_to_table_names["ev_procedures"] = "procedures";
	events_to_table_names["ev_institutes"] = "procedures";
	events_to_table_names["ev_blood_bank"] = "procedures";
	events_to_table_names["ev_medications_oncology_treatments"] = "procedures";
	events_to_table_names["ev_surgeries"] = "procedures";

	events_to_table_names["ev_medications_administered"] = "drugs";
	events_to_table_names["ev_medications_adm"] = "drugs";
	events_to_table_names["ev_medications_orders"] = "drugs";
	events_to_table_names["ev_medications_recom"] = "drugs";

	events_to_table_names["ev_diagnoses"] = "diagnoses";
	events_to_table_names["ev_deceased"] = "diagnoses";

	events_to_table_names["ev_outpatient_visits"] = "visits";
	events_to_table_names["ev_consultations"] = "visits";
	events_to_table_names["ev_transfers"] = "visits";
	events_to_table_names["ev_ed_visit"] = "visits";
	events_to_table_names["ev_admissions"] = "visits";

	if (prm.get_dicts) {
		for (string dict_name : {"departmentcode", "servicecode", "servicegroup", "conditioncode", "performedprocedurecode",
				"protocol", "sequencenumber", "conditiontype", "prefix", "conditionclassindicator", 
				"serviceclassindicator", "quantitiy_unitcode", "medicationcode",
			"formcode", "frequencycode", "routecode", "admissionsourcecode", "surgerytype"}) {
			prm.f_dicts[dict_name] = new ofstream(prm.out_dir + "/dict." + dict_name);
			unordered_map<string, string> d;
			prm.all_dicts[dict_name] = d;
		}
	}

	MedTimer timer;
	timer.start();

	int n_proccessed = 0;
	long long psize = 0;
#pragma omp parallel for
	for (int i = 0; i<prm.pids.size(); i++) {
		//for (auto pid : prm.pids) {
		int pid = prm.pids[i];
		long long nr = prm.id2nr[pid];
		string fname = prm.in_dir + "/" + to_string(nr) + ".xml";

		string data;
		if (read_file_into_string(fname, data) < 0) {
			MERR("Failed reading from file %s\n", fname.c_str());
			continue;
		}

		xml_document<> doc;
		doc.parse<0>(&data[0]);
		
		append_demographics_data_rapid(prm, doc, pid);
		append_labs_data_rapid(prm, doc, pid);
		append_all_other_tables_rapid(prm, doc, pid);

#pragma omp critical
		{
			psize += (long long)data.size();
			n_proccessed++;
			if (n_proccessed % 100 == 0) {
				timer.take_curr_time();
				double t = timer.diff_sec();
				double dt = (double)n_proccessed/t;
				double mb = ((double)psize/(1024.0*1024.0))/t;
				MLOG("######>>>>> processed %d records so far :: %f sec :: %f records/sec :: %f MB/sec\n", n_proccessed, t, dt, mb);
			}
		}
	}

	// writing dict and hist files if needed
	write_dict_hist_files(prm);

	if (prm.get_demographics_flag) prm.f_demographics.close();
	if (prm.get_labs_flag) prm.f_labs.close();
	if (prm.get_dicts) prm.f_labs_units_dict.close();
	if (prm.get_dicts) prm.f_labs_tests_dict.close();
	if (prm.get_hists) prm.f_labs_hists.close();
	if (prm.get_dicts) 
		for (auto f: prm.f_dicts)
			f.second->close();
	for (auto f : prm.f_tables)
		f.second->close();

}


//========================================================================================
// MAIN
//========================================================================================

int main(int argc, char *argv[])
{
	int rc = 0;
	po::variables_map vm;
	parser_params prm;

	// Running Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm);
	assert(rc >= 0);

	// read id2nr
	if (read_id2nr(vm["id2nr"].as<string>(), prm.id2nr, prm.nr2id) < 0) {
		MERR("ERROR: Reading id2nr file %s failed", vm["id2nr"].as<string>().c_str());
		return -1;
	}

	// prepare list of pids to work on
	if (vm["in_list"].as<string>() != "") {
		if (read_pids_list(vm["in_list"].as<string>(), prm.pids) < 0) {
			MERR("ERROR: Reading pids file %s failed", vm["in_list"].as<string>().c_str());
			return -1;
		}
	}
	else {
		if (vm["id"].as<int>() > 0)
			prm.pids.push_back(vm["id"].as<int>());
	}

	// get needed flags
	if (boost::contains(vm["create_tables"].as<string>(), "demographic")) prm.get_demographics_flag = 1;
	if (boost::contains(vm["create_tables"].as<string>(), "lab")) prm.get_labs_flag = 1;
	if (boost::contains(vm["create_tables"].as<string>(), "dict")) prm.get_dicts = 1;
	if (boost::contains(vm["create_tables"].as<string>(), "hist")) prm.get_hists = 1;
	if (boost::contains(vm["create_tables"].as<string>(), "procedures")) prm.get_procedures = 1;
	if (boost::contains(vm["create_tables"].as<string>(), "drugs")) prm.get_drugs = 1;

	prm.in_dir = vm["in_dir"].as<string>();
	prm.out_dir = vm["out_dir"].as<string>();
	prm.prefix = vm["prefix"].as<string>();

	// all is ready , go for it
	if (create_tables_rapid(prm) < 0) {
		MERR("FAILED Creating tables\n");
		return -1;
	}

	MLOG("Tables created\n");
	return 0;

}