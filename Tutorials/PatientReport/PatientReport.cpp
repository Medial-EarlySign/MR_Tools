//
// PatientReport
//
// This app tries to summarize a patient record at a given time
// The idea is to try and find the important stuff and summarize it.
//

#include <string>
#include <algorithm>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <boost/program_options.hpp>
#include <boost/algorithm/string/split.hpp>
#include <InfraMed/InfraMed/InfraMed.h>
#include <InfraMed/InfraMed/MedPidRepository.h>
#include <MedProcessTools/MedProcessTools/MedModel.h>
#include <MedUtils/MedUtils/MedGenUtils.h>
#include <MedPlotly/MedPlotly/MedPlotly.h>

#include <Logger/Logger/Logger.h>
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL
using namespace std;
namespace po = boost::program_options;


void get_drugs_heatmap(MedPidRepository &rep, int pid, const vector<vector<string>> &sets, vector<int> &_xdates, vector<string> &_sets_names, vector<vector<float>> &_hmap);


//=========================================================================================================
int read_run_params(int argc, char *argv[], po::variables_map& vm, unordered_set<string> &report_types, vector<string> &report_sigs) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value("/home/Repositories/THIN/thin_jun2017/thin.repository"), "repository file name")
			("config", po::value<string>()->default_value("//nas1/UsersData/avi/MR/Libs/Internal/MedPlotly/MedPlotly/BasicConfig.txt"), "java script directory")
			("pid", po::value<int>()->default_value(5000001), "pid to work with")
			("date", po::value<int>()->default_value(20160101), "date of report")
			("date_text", po::value<string>()->default_value(""), "text describing the date of report, optional")
			("types", po::value<string>()->default_value("all"), "report sections to print: all (all of them), or , separated (demographic, drugs, diabetes, etc...")
			("sigs", po::value<string>()->default_value(""), "when empty: auto mode. Otherwise: create a report with the asked for signals.")
			("js_to_load", po::value<string>()->default_value("file:///W:/Users/Avi/canvasjs/plotly/plotly-latest.min.js"), ", separated list of js files to load in header")
			("fout", po::value<string>()->default_value("patient.html"), "output html file")
			("width", po::value<int>()->default_value(1200), "width for graphs")
			("height", po::value<int>()->default_value(400), "height for graphs")
			("dwidth", po::value<int>()->default_value(1200), "width for drug heatmap")
			("dheight", po::value<int>()->default_value(150), "initial height for drug heatmap")
			("pwidth", po::value<int>()->default_value(800), "width for panels")
			("pheight", po::value<int>()->default_value(400), "height for panels")
			("block_mode", po::value<int>()->default_value(1), "side by side or one after the other")

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

	// parsing report_types and report_sigs
	vector<string> fields;
	boost::split(fields, vm["types"].as<string>(), boost::is_any_of(","));
	for (auto &f : fields) report_types.insert(f);
	boost::split(report_sigs, vm["sigs"].as<string>(), boost::is_any_of(","));


	return 0;
}

//----------------------------------------------------------------------------------------
int get_last_time(MedPidRepository &rep, int pid)
{
	int time = 0;
	int len;

	if (rep.sigs.sid("ENDDATE") > 0) {
		SVal *sv = (SVal *)rep.get(pid, "ENDDATE", len);
		time = (int)sv[0].val;
	}
	else if (rep.sigs.sid("RC") > 0) {
		SDateVal *sdv = (SDateVal *)rep.get(pid, "RC", len);
		if (len > 0)
			time = sdv[len-1].date;
	}
	else
		time = 20170101; // taking some last time

	return time;
}

//----------------------------------------------------------------------------------------
string date_to_string(int date)
{
	int y = date/10000;
	int m = (date % 10000)/100;
	int d = date % 100;

	string s = "'" + to_string(y) + "-" + to_string(m) + "-" + to_string(d) + "'";
	return s;
}

//----------------------------------------------------------------------------------------
void add_html_header(const string &js_to_load, string &shtml)
{
	vector<string> load_files;
	boost::split(load_files, js_to_load, boost::is_any_of(","));

	shtml += "<!DOCTYPE HTML>\n<html>\n<head>\n";
	for (auto &f : load_files)
		shtml += "\t<script type=\"text/javascript\" src=\"" + f + "\"></script>\n";
	shtml += "</head>\n";
}

//----------------------------------------------------------------------------------------
void add_basic_demographics(MedPidRepository &rep, int pid, int time, string date_text, string &shtml)
{
	float age;
	int len;

	if (time == 0) {
		time = get_last_time(rep, pid);
	}

	int byear = (int)(((SVal *)rep.get(pid, "BYEAR", len))[0].val);
	int gender = (int)(((SVal *)rep.get(pid, "GENDER", len))[0].val);

	age = get_age(time, byear);

	shtml += "<h1> Patient Report </h1>\n";

	shtml += "<h3> pid " + to_string(pid) + " , ";

	stringstream s;
	s << fixed << setprecision(2) << age;
	shtml += "age " + s.str() + " , ";

	if (gender == 1)
		shtml += "Male , ";
	else
		shtml += "Female , ";

	shtml += " date: " + to_string(time);
	
	if (date_text != "") shtml += " [" + date_text + "] ";

	shtml +="</h3>\n";


}

//----------------------------------------------------------------------------------------
void get_usv_min_max(UniversalSigVec &usv, float &vmin, float &vmax)
{
	vmin = (float)1e10;
	vmax = -vmin;
	for (int chan=0; chan<usv.n_val_channels(); chan++)
		for (int i=0; i<usv.len; i++) {
			float v = usv.Val(i, chan);
			if (v < vmin) vmin = v;
			if (v > vmax) vmax = v;
		}
}

//----------------------------------------------------------------------------------------
void add_xy_js(UniversalSigVec &usv, int time_chan, int chan, int null_zeros_flag, string prefix, string &shtml)
{
	// dates
	shtml += prefix+"x: [";
	for (int i=0; i<usv.len; i++) {
		shtml += date_to_string(usv.Time(i, time_chan));
		if (i < usv.len - 1)	shtml += ",";
	}
	shtml += "],\n";

	// vals
	shtml += prefix + "y: [";
	for (int i=0; i<usv.len; i++) {
		float v = usv.Val(i, chan);
		if (null_zeros_flag == 0 || v > 0)
			shtml += to_string(v);
		else
			shtml += "null";
		if (i < usv.len - 1)	shtml += ",";
	}
	shtml += "],\n";

}

//----------------------------------------------------------------------------------------
void add_xy_js(vector<int> &dates, vector<float> &vals, int null_zeros_flag, string prefix, string &shtml)
{
	// dates
	shtml += prefix+"x: [";
	for (int i=0; i<dates.size(); i++) {
		shtml += date_to_string(dates[i]);
		if (i < dates.size() - 1)	shtml += ",";
	}
	shtml += "],\n";

	// vals
	shtml += prefix + "y: [";
	for (int i=0; i<vals.size(); i++) {
		float v = vals[i];
		if (null_zeros_flag == 0 || v > 0)
			shtml += to_string(v);
		else
			shtml += "null";
		if (i < vals.size() - 1)	shtml += ",";
	}
	shtml += "],\n";

}

//----------------------------------------------------------------------------------------
void add_dataset_js(UniversalSigVec &usv, int time_chan, int chan, int null_zeros_flag, string prefix, string sname, int yaxis, string sig, string &shtml)
{

	shtml += prefix + "var " + sname + " = {\n";
	add_xy_js(usv, time_chan, chan, null_zeros_flag, prefix + "\t", shtml);

	// types/general defs
	shtml += prefix + "\ttype: 'scatter',\n";
	shtml += prefix + "\tmode: 'lines+markers',\n";
	shtml += prefix + "\tline: {shape: 'spline', width: 2, smoothing: 0.75},\n";
	shtml += prefix + "\tyaxis: 'y" + to_string(yaxis) + "',\n";
	if (null_zeros_flag) shtml += prefix + "\tconnectgaps: true,\n";
	shtml += prefix + "\tname: '" + sig +"'\n";

	// close it
	shtml += prefix + "};\n";
}

//----------------------------------------------------------------------------------------
void add_bg_dataset_js(vector<int> &dates, vector<float> &vals, int null_zeros_flag, string color, string prefix, string sname, int yaxis, string name, string &shtml)
{

	shtml += prefix + "var " + sname + " = {\n";
	add_xy_js(dates, vals, null_zeros_flag, prefix + "\t", shtml);
/*
name: 'Statins',
	yaxis: 'y4',
	type: 'scatter',
	mode: 'none',
	fill: 'tozeroy',
	fillcolor: 'rgba(162, 217, 206,0.333)',
	line: {shape: 'hv'}
*/
	// types/general defs
	shtml += prefix + "\ttype: 'scatter',\n";
	shtml += prefix + "\tmode: 'none',\n";
	shtml += prefix + "\thoverinfo: 'none',\n";
	shtml += prefix + "\tfill: 'tozeroy',\n";
	shtml += prefix + "\tfillcolor: '"+color+"',\n";
	shtml += prefix + "\tline: {shape: 'hv'},\n";
	shtml += prefix + "\tyaxis: 'y" + to_string(yaxis) + "',\n";
	if (null_zeros_flag) shtml += prefix + "\tconnectgaps: true,\n";
	shtml += prefix + "\tname: '" + name +"'\n";

	// close it
	shtml += prefix + "};\n";
}

//----------------------------------------------------------------------------------------
void add_sig_simple_chart(MedPidRepository &rep, po::variables_map& vm, string sig, int y_log_flag, string &shtml)
{
	int pid = vm["pid"].as<int>();
	int time = vm["date"].as<int>();
	int time_chan = 0;
	int width = vm["width"].as<int>();
	int height = vm["height"].as<int>();
	int block_mode = vm["block_mode"].as<int>();
	int null_zero_flag = 1;

	UniversalSigVec usv;
	rep.uget(pid, sig, usv);

	if (usv.len == 0) return;

	// case single value : we do not plot this one ...
	if (usv.len == 1) {
		shtml += "<h3> " + sig + " : ";
		shtml += to_string(usv.Time(0,time_chan)) + ",";
		for (int i=0; i<usv.n_val_channels(); i++) {
			shtml += to_string(usv.Val(0, i));
			if (i < usv.n_val_channels()-1) shtml += ":";
		}
		shtml += "</h3>\n";
		return;
	}

	// case of plotting
	string div_name = "div_" + sig + to_string(rand_N(10000));
	
	//<div id="chart" style="width:1200px;height:500px;"></div>
	shtml += "\t<div id=\"" + div_name + "\" style=\"width:" + to_string(width) + "px;height:" + to_string(height) + "px;";
	if (block_mode) shtml += "display: inline-block;";
	shtml+= "\"></div>\n";
	shtml += "\t<script>\n";

	// computing datasets

	for (int chan=0; chan<usv.n_val_channels(); chan++) {

		add_dataset_js(usv, time_chan, chan, null_zero_flag, "\t\t", "set" + to_string(chan+1), 1, sig, shtml);

	}

	// prep layout
	float vmin, vmax;
	get_usv_min_max(usv, vmin, vmax);
	shtml += "\t\tvar layout = {\n";
	shtml += "\t\t\ttitle: '" + sig + "',\n";
	if (y_log_flag && vmin > 0 && usv.n_val_channels() < 2) shtml += "\t\t\tyaxis: {type: 'log', autorange: true},\n";
	shtml += "\t\txaxis: {hoverformat: '%%Y/%%m/%%d'},";
	if (time > 0) shtml += "\t\t\tshapes: [{type: 'line', x0: " + date_to_string(time) + ", y0: " + to_string(vmin) + ", x1: " + date_to_string(time) + ", y1: " + to_string(vmax) + "}]\n";
	shtml += "\t\t};\n";

	// prep data
	shtml += "\t\tvar data = [";
	for (int chan=0; chan<usv.n_val_channels(); chan++) {
		string set_name = "set" + to_string(chan+1);
		shtml += set_name;
		if (chan < usv.n_val_channels()-1) shtml += ",";
	}
	shtml += "];\n";

	// actual plot
	shtml += "\t\tPlotly.plot('" + div_name + "', data, layout);\n";

	shtml += "\t</script>\n";

}

//----------------------------------------------------------------------------------------
void add_panel_chart(MedPidRepository &rep, po::variables_map& vm, const vector<string> &sigs, int null_zero_flag, int y_log_flag, string panel_name, 
	string drug_group, const vector<string> &drug_set, string &shtml)
{
	int pid = vm["pid"].as<int>();
	int time = vm["date"].as<int>();
	int time_chan = 0;
	int pwidth = vm["pwidth"].as<int>();
	int pheight = vm["pheight"].as<int>();
	int block_mode = vm["block_mode"].as<int>();

	vector<string> titles = sigs;

	// div_name
	string div_name = "div";
	for (auto &s : sigs) div_name += "_" + s;
	div_name += to_string(rand_N(10000));

	//<div id="chart" style="width:1200px;height:500px;"></div>
	shtml += "\t<div id=\"" + div_name + "\" style=\"width:" + to_string(pwidth) + "px;height:" + to_string(pheight) + "px;";
	if (block_mode) shtml += "display: inline-block;";
	shtml+= "\"></div>\n";
	shtml += "\t<script>\n";

	// computing datasets

	UniversalSigVec usv;
	int cnt = 0;
	int n_yaxis = (int)sigs.size();
	vector<float> vmin(sigs.size()), vmax(sigs.size());
	for (int i=0; i<sigs.size(); i++) {
		rep.uget(pid, sigs[i], usv);
		for (int chan=0; chan<usv.n_val_channels(); chan++) {
			add_dataset_js(usv, time_chan, chan, null_zero_flag, "\t\t", "set" + to_string((++cnt)), i+1, sigs[i], shtml);
		}
		get_usv_min_max(usv, vmin[i], vmax[i]);
	}

	if (drug_group != "") {
		vector<string> dname ={ drug_group };
		vector<int> xdates;
		vector<vector<float>> hmap;
		get_drugs_heatmap(rep, pid, { drug_set }, xdates, dname, hmap);
		if (xdates.size()>0 && hmap.size()>0) {
			add_bg_dataset_js(xdates, hmap[0], 0, "rgba(162, 217, 206,0.333)", "\t\t", "set" + to_string(++cnt), n_yaxis+1, drug_group, shtml);
			n_yaxis++;
			vmin.push_back(0);
			vmax.push_back(0);
			titles.push_back(drug_group);
		}

	}

	// prep layout
	
	shtml += "\t\tvar layout = {\n";
	shtml += "\t\t\ttitle: '" + panel_name + "',\n";
	float psize = (float)1.0 - n_yaxis*(float)0.02;
	// deal with multiple yaxis
	for (int i=0; i<n_yaxis; i++) {
		shtml += "\t\t\tyaxis" + to_string(i+1) +": {title: '" + titles[i] + "', showline: false";
		if (i > 0) {
			shtml += ", overlaying: 'y', side: 'right', position: " + to_string(psize+0.02*i) + ", tick: '', showticklabels: false";
		}
		if (y_log_flag && vmin[i] > 0 && usv.n_val_channels() < 2) shtml += ",type: 'log', autorange: true";
		shtml += "},\n";
	}
	// xaxis setup
	shtml += "\t\txaxis: {domain: [0," + to_string(psize) +"], hoverformat: '\%Y/\%m/\%d'},";
	if (time > 0) shtml += "\t\t\tshapes: [{type: 'line', x0: " + date_to_string(time) + ", y0: " + to_string(vmin[0]) + ", x1: " + date_to_string(time) + ", y1: " + to_string(vmax[0]) + "}]\n";
	shtml += "\t\t};\n";

	// prep data
	shtml += "\t\tvar data = [";
	for (int i=0; i<cnt; i++) {
		string set_name = "set" + to_string(i+1);
		shtml += set_name;
		if (i < cnt-1) shtml += ",";
	}
	shtml += "];\n";

	// actual plot
	shtml += "\t\tPlotly.plot('" + div_name + "', data, layout);\n";

	shtml += "\t</script>\n";
}

//----------------------------------------------------------------------------------------------------------------------
void get_drugs_heatmap(MedPidRepository &rep, int pid, const vector<vector<string>> &sets, vector<int> &_xdates, vector<string> &_sets_names, vector<vector<float>> &_hmap)
{
	int month_granularity = 1; // 1 , 2, 3, 4, 6, 12 (should divide 12)
	string drug_sig = "Drug";
	// read drug data
	UniversalSigVec usv;
	rep.uget(pid, drug_sig, usv);

	vector<int> xdates;
	vector<vector<float>> hmap;
	vector<string> sets_names = _sets_names;

	if (usv.len == 0) return;

	// calculate min/max cells dates, xdays and xdates
	int min_date = usv.Time(0, 0);
	if (min_date < 20000101) min_date = 20000101;
	int max_date = usv.Time(usv.len-1, 0);
	min_date = (min_date/10000)*10000+101;
	max_date = (max_date/10000)*10000+(12-month_granularity)*100 + 1;
	vector<int> xdays;
	xdates.clear();
	int t = min_date;
	while (t<=max_date) {
		int days = med_time_converter.convert_date(MedTime::Days, t);
		xdates.push_back(t);
		xdays.push_back(days);

		t += (month_granularity)*100;
		if (t % 10000 > 1231) t = (t/10000 + 1)*10000 + 101;
	}
	max_date = t;
	xdays.push_back(med_time_converter.convert_date(MedTime::Days, t));

	hmap.clear();
	hmap.resize(sets.size());
	
	vector<int> drug_days;
	for (int i=0; i<usv.len; i++)
		drug_days.push_back(med_time_converter.convert_date(MedTime::Days, usv.Time(i,0)));

	int section_id = rep.dict.section_id(drug_sig);
	vector<int> sets_sum(sets.size(), 0);
	int first_nonz = 99999999, last_nonz = 0;
	for (int s=0; s<sets.size(); s++) {
		vector<unsigned char> lut;
		rep.dict.prep_sets_indexed_lookup_table(section_id, sets[s], lut);
		hmap[s].resize(xdates.size(), (float)0);
		int last_day_counted = xdays[0]-1;
		int curr_cell = 0;
		for (int i=0; i<usv.len; i++) {
			if (lut[(int)usv.Val(i, 0)]) {
				//MLOG("Taking the drug at i=%d %d,%d\n", i, usv.Time(i,0), (int)usv.Val(i, 1));
				sets_sum[s] += (int)usv.Val(i, 1);
				if (usv.Time(i, 0) < first_nonz && usv.Time(i,0) >= min_date) first_nonz = usv.Time(i, 0);
				if (usv.Time(i, 0) > last_nonz && usv.Time(i,0) <= max_date) last_nonz = usv.Time(i, 0);
				int to_day = drug_days[i] + (int)usv.Val(i, 1);
				if (to_day > last_day_counted) {
					int from_day = max(last_day_counted+1, drug_days[i]);
					// get the curr_cell from_day is contained in
					while ((curr_cell < xdays.size()-1) && (xdays[curr_cell+1] <= from_day)) curr_cell++;
					if (curr_cell >= xdays.size()-1) break; // we finished this part
					int left = to_day - from_day;
					if (to_day < xdays[0]) left = 0;
					//MLOG("from %d , to %d , curr %d , left %d\n", from_day, to_day, curr_cell, left);
					while (left > 0) {
						if (from_day + left < xdays[curr_cell+1]) {
							// all contained in current
							//MLOG("add1: before : from %d , to %d , curr %d , left %d\n", from_day, to_day, curr_cell, left);
							hmap[s][curr_cell] += (float)(left+1);
							last_day_counted = to_day;
							left = 0;
							//MLOG("add1: after : from %d , to %d , curr %d , left %d\n", from_day, to_day, curr_cell, left);
						}
						else {
							// count to the end and advance to next 
							//MLOG("add2: before : from %d , to %d , curr %d , left %d add %d \n", from_day, to_day, curr_cell, left, xdays[curr_cell+1] - from_day);
							hmap[s][curr_cell] += (float)(xdays[curr_cell+1] - from_day);
							curr_cell++;
							if (curr_cell >= xdays.size()-1) break; // we finished this part
							from_day = xdays[curr_cell];
							left = to_day - from_day;
							last_day_counted = from_day - 1;
							//MLOG("add2: after : from %d , to %d , curr %d , left %d\n", from_day, to_day, curr_cell, left);
						}
					}
				}
			}
		}

		// hmap[s] needs to be normalized to coverage
		for (int i=0; i<hmap[s].size(); i++)
			hmap[s][i] /= (float)(xdays[i+1] - xdays[i]);
	}

	// Shrinkage
	// We leave at most 2 years of no drugs at start, and 1 at the end.
	// Also we get rid of drugs with 0 usage
	first_nonz = first_nonz - 20000;
	last_nonz = last_nonz + 10000;
	int start_cell = -1, end_cell = -1;
	for (int i=0; i<xdates.size(); i++) {
		if (first_nonz >= xdates[i]) start_cell++;
		if (last_nonz >= xdates[i]) end_cell++;
	}
	if (start_cell < 0) start_cell = 0;
	_xdates.clear();
	//MLOG("min_date %d max_date %d first_nonz %d last_nonz %d start_cell %d end_cell %d xdates.size %d\n", min_date, max_date, first_nonz, last_nonz, start_cell, end_cell, xdates.size());
	for (int i=start_cell; i<=end_cell; i++) _xdates.push_back(xdates[i]);
	_hmap.clear();
	_sets_names.clear();
	for (int s=0; s<sets_sum.size(); s++) {
		if (sets_sum[s] > 0) {
			_sets_names.push_back(sets_names[s]);
			_hmap.push_back({});
			for (int i=start_cell; i<=end_cell; i++) _hmap.back().push_back(hmap[s][i]);
		}
	}



	// debug

#if 0
	MLOG("xdates: ");
	for (int i=0; i<xdates.size(); i++) MLOG("[%d] %d:%d ", i, xdates[i], xdays[i]);
	MLOG("\n");
	for (int s=0; s<sets.size(); s++) {
		MLOG("%s : ", sets[s][0].c_str());
		for (int i=0; i<hmap[s].size(); i++) MLOG("[%d] %f ", i, hmap[s][i]);
		MLOG("\n");
	}
#endif

}

//----------------------------------------------------------------------------------------------------------------------
void add_drugs_heatmap(MedPidRepository &rep, po::variables_map& vm, string &shtml)
{
	vector<int> xdates;
	vector<vector<float>> hmap;
	vector<vector<string>> sets ={ { "ATC_A10_____" } ,{"ATC_A10A____"}, {"ATC_A10B____"}, {"ATC_A10B_A__", "ATC_A10B_G__" },{ "ATC_A10B_B__", "ATC_A10B_C__", "ATC_A10B_H__"},
			{ "ATC_A10B_F__" } , {"ATC_A10B_J__"},{ "ATC_A10B_K__" }, { "ATC_C10A_A__" }, { "ATC_B01_____" },{ "ATC_B01A_C__" },{ "ATC_B01A_A03" },{ "ATC_B01A_B__" },
			{ "ATC_B02_____" }, { "ATC_C03_____" },{ "ATC_C07_____" }, { "ATC_C08_____" },{ "ATC_C09_____" },{ "ATC_H03_____" },{ "ATC_L02_____" },{ "ATC_L04_____" },
			{ "ATC_N06A____" },{ "ATC_J01_____" },{ "ATC_N02A____" } ,{ "ATC_N02B____" } ,{ "ATC_G03_____" },{ "ATC_G03A____" },{ "ATC_A02_____" },{ "ATC_R03_____" },
			{ "ATC_B03_____"} };
	vector<string> sets_names ={ "Diabetes", "Insulin", "Non-Insulin", "Metformin", "Sulphinil Urea",
								 "alphaGlucosidaseI", "glp1", "sglt2I", "Statins", "Antithrombotic", "Aspirin", "Warfarin", "Heparin",
								 "Antihemorrhagics", "Diuretics", "Beta blockers", "Calcium channels", "AceI", "Thyroid", "Endoctrine", "Immunosuppresors",
								 "Antidepressants", "Antibiotics", "Opioids", "Antipyretics", "Hormonal", "H. Contraceptives", "AntiAcid", "Obstructive airway", "AntiAnemic" };

	for (int i=0; i<sets_names.size(); i++) {
		MLOG("DRUG_GROUP\t%s\t", sets_names[i].c_str());
		for (int j=0; j<sets[i].size(); j++) {
			MLOG("%s", sets[i][j].c_str());
			if (j < sets[i].size() - 1)
				MLOG(",");
		}
		MLOG("\n");
	}


	get_drugs_heatmap(rep, vm["pid"].as<int>(), sets, xdates, sets_names, hmap);

	//int pid = vm["pid"].as<int>();
	//int time = vm["date"].as<int>();
	//int time_chan = 0;
	int dwidth = vm["dwidth"].as<int>();
	int dheight = vm["dheight"].as<int>()+30*(int)sets_names.size();
	int block_mode = 0;

	string div_name = "div_drug_heatmap" + to_string(rand_N(10000));

	//<div id="chart" style="width:1200px;height:500px;"></div>
	shtml += "\t<div id=\"" + div_name + "\" style=\"width:" + to_string(dwidth) + "px;height:" + to_string(dheight) + "px;";
	if (block_mode) shtml += "display: inline-block;";
	shtml+= "\"></div>\n";
	shtml += "\t<script>\n";

	// xValues is xdates
	shtml += "\t\tvar xValues = [";
	for (int i=0; i<xdates.size(); i++) {
		//MLOG("====> xValues %d : %d\n", i, xdates[i]);
		shtml += date_to_string(xdates[i]); if (i<xdates.size()-1) shtml += ",";
	}
	shtml += "];\n";

	// yValues is the sets names
	shtml += "\t\tvar yValues = [";
	for (int i=0; i<sets_names.size(); i++) {
		shtml += "'" + sets_names[i] + "'"; if (i<sets_names.size()-1) shtml += ",";
	}
	shtml += "];\n";

	// zValues is tje actual heatmap
	shtml += "\t\tvar zValues = [";
	for (int i=0; i<sets_names.size(); i++) {
		shtml += "[";
		for (int j=0; j<xdates.size(); j++) {
			shtml += to_string(hmap[i][j]);
			if (j<xdates.size()-1) shtml += ",";
		}
		shtml += "]";
		if (i<sets_names.size()-1) shtml += ",";
	}
	shtml += "];\n";

	// color scales
	//shtml += "\t\tvar colorscaleValue = [ [0, '#3D9970'], [1, '#001f3f']];\n";
	shtml += "\t\tvar colorscaleValue = [ [0, '#001f3f'], [1, '#2ecc71']];\n";

	// data
	shtml += "\t\tvar data = [{ x: xValues,	y: yValues,	z: zValues,	type: 'heatmap', colorscale: colorscaleValue, showscale: false}];\n";

	// layout
	shtml += "\t\tvar layout = { title: 'Drugs HeatMap', margin: {l: 200}};\n";

	// actual plot
	shtml += "\t\tPlotly.plot('" + div_name + "', data, layout);\n";

	shtml += "\t</script>\n";

}

//----------------------------------------------------------------------------------------------------------------------
void add_RCs_to_js(MedPidRepository &rep, po::variables_map& vm, string &shtml)
{
	int pid = vm["pid"].as<int>();
	int time = vm["date"].as<int>();
	//int time_chan = 0;
	int pwidth = 1200; //vm["pwidth"].as<int>();
	int pheight = 600; //vm["pheight"].as<int>();
	int block_mode = 0; //vm["block_mode"].as<int>();
	int rc_acc_days = 60;
	unordered_map<string, double> code2wgt = { {"0", 0.1}, { "1", 0.1 }, { "2", 0.1 }, { "3", 0.1 }, { "4", 0.1 }, { "5", 0.5 }, { "6", 0.1 }, { "7", 1.0 }, { "8", 0.1 }, { "9", 0.1 },
	{ "A", 2.0 }, { "B", 5.0 }, { "C", 2.5 }, { "D", 1.5 }, { "E", 1.5 }, { "F", 2.0 }, { "G", 3.0 }, { "H", 3.0 }, { "J", 2.0 }, { "K", 1.0 }, 
	{ "L", 2.5 }, { "M", 0.8 }, { "N", 1.0 }, { "P", 1.0 }, { "Q", 2.0 }, { "R", 0.9 }, { "S", 1.0 }, { "T", 1.0 }, { "U", 2.0 }, { "Z", 0.1 } 
	};
	double p_decay = 0.5, q_decay = 0.2;
	double alpha;

	alpha = -log(q_decay/p_decay)/(double)rc_acc_days;

	// plan:
	// calculate some accumulator in a time window and add a point of (x=time,y=accumulator,text=drugs in day x)

	vector<string> xdates;
	vector<float> yvals;
	vector<int> days;
	vector<float> days_cnt;
	vector<string> hovertext;

	UniversalSigVec usv;
	rep.uget(pid, "RC", usv);
	int curr_date = 0;
	//int curr_days = 0;
	int section_id = rep.dict.section_id("RC");
	for (int i=0; i<usv.len; i++) {
		int i_date = usv.Time(i, 0);
		int i_val = (int)usv.Val(i, 0);
		int d = med_time_converter.convert_date(MedTime::Days, i_date);
		if (d != curr_date) {
			days.push_back(d); days_cnt.push_back(0);
			xdates.push_back(date_to_string(i_date));
			float y = 0;
			int j = (int)days_cnt.size() - 1;
			while (j >= 0) {
				int ddays = d - days[j];
				if (ddays > rc_acc_days) break;
				double factor = p_decay * exp(-alpha*(double)ddays);
				y += (float)factor*days_cnt[j];
				j--;
			}
			yvals.push_back(y);
			hovertext.push_back("");
		}
		curr_date = d;
		//days_cnt.back()++;
		//yvals.back()++;

		// recover curr text
		string curr_text = "";
		if (rep.dict.dict(section_id)->Id2Names.find(i_val) != rep.dict.dict(section_id)->Id2Names.end())
			for (int j = 0; j < rep.dict.dict(section_id)->Id2Names[i_val].size(); j++) {
				string sname = rep.dict.dict(section_id)->Id2Names[i_val][j];
				string scode = sname.substr(0, 1);

				curr_text += "|" + sname;

				if (j == 0) { // assumes the first name is the READCODE !!!!!!!!
					float wgt = (float)code2wgt[scode];
					days_cnt.back() += wgt;
					yvals.back() += wgt;
					//MLOG("date %d sname= %s :: scode = %s :: weight = %f :: acc %f\n", i_date, sname.c_str(), scode.c_str(), code2wgt[scode], days_cnt.back());
				}
			}
		replace(curr_text.begin(), curr_text.end(), '\"', '@');
		replace(curr_text.begin(), curr_text.end(), '\'', '@');

		if (hovertext.back() != "") hovertext.back() += "<br>";
		hovertext.back() += curr_text;
	}

	// prep x , y, text arrays
	string ax, ay, atext;
	float ymax = 0, ymin = 9999999;
	for (int i=0; i<xdates.size(); i++) {
		ax += xdates[i];
		ay += to_string(yvals[i]);
		atext += "\"" + hovertext[i] + "\"";
		if (yvals[i] > ymax) ymax = yvals[i];
		if (yvals[i] < ymin) ymin = yvals[i];
		//atext += "\"TTT" + to_string(i) + "\"";
		if (i < xdates.size()-1) {
			ax += ",";
			ay += ",";
			atext += ",";
		}
		//MLOG("i %d :: days %d,%d :: xdate %s :: yval %d :: %s\n", i, days[i], days_cnt[i], xdates[i].c_str(), yvals[i], hovertext[i].c_str());
	}

	// write RC div
	// div_name
	string div_name = "div_RC_";
	div_name += to_string(rand_N(10000));

	//<div id="chart" style="width:1200px;height:500px;"></div>
	shtml += "\t<div id=\"" + div_name + "\" style=\"width:" + to_string(pwidth) + "px;height:" + to_string(pheight) + "px;";
	if (block_mode) shtml += "display: inline-block;";
	shtml+= "\"></div>\n";
	shtml += "\t<script>\n";

	shtml += "\t\tvar set1 = {\n";
	shtml += "\t\t\tx: [" + ax + "],\n";
	shtml += "\t\t\ty: [" + ay + "],\n";
	shtml += "\t\t\ttext: [" + atext + "],\n";
	shtml += "\t\t\tyaxis: 'y1',\n";
	shtml += "\t\t\ttype: 'scatter',\n";
	shtml += "\t\t\tname: 'ReadCodes',\n";
	shtml += "\t\t\tmode: 'lines+markers',\n";
	shtml += "\t\t\tline: {shape: 'spline', width: 2, smoothing: 0.75},\n";
	shtml += "\t\t\thoverinfo: 'x+text'\n";
	shtml += "\t\t};\n";

	shtml += "\t\tvar layout ={\n";
	shtml += "\t\t\ttitle: 'ReadCodes',\n";
	shtml += "\t\t\tyaxis: {autorange: true},\n";
	if (time > 0) shtml += "\t\t\tshapes: [{type: 'line', x0: " + date_to_string(time) + ", y0: " + to_string(ymin) + ", x1: " + date_to_string(time) + ", y1: " + to_string(ymax) + "}]\n";
	shtml += "\t\t};\n";

	shtml += "\t\tPlotly.plot('" + div_name+"', [set1], layout);\n";

	shtml += "\t</script>\n";

}

//----------------------------------------------------------------------------------------------------------------------
int get_sigs_simple_html_report(MedPidRepository &rep, po::variables_map& vm, unordered_set<string> &report_types, vector<string> &report_sigs)
{
	string shtml = "";

	add_html_header(vm["js_to_load"].as<string>(), shtml);

	add_basic_demographics(rep, vm["pid"].as<int>(), vm["date"].as<int>(), vm["date_text"].as<string>(), shtml);

	shtml += "<body>\n";

	for (auto s : report_sigs) {
		if (s == "Drug")
			add_drugs_heatmap(rep, vm, shtml);
		else
			add_sig_simple_chart(rep, vm, s, 1, shtml);
	}

	//add_panel_chart(rep, vm, { "Glucose" }, 1, 1, "Single Panel", "", {}, shtml);
	add_panel_chart(rep, vm, { "Glucose", "HbA1C", "BMI" }, 1, 1, "Diabetes View", "Diabetes Drugs", { "ATC_A10_____" }, shtml);
	add_panel_chart(rep, vm, { "LDL", "HDL", "Triglycerides", "Cholesterol" }, 1, 1, "Cholesterol View", "Statins", { "ATC_C10A_A__" }, shtml);
	add_panel_chart(rep, vm, { "BP", "BMI" }, 1, 1, "BP View", "BP Drugs", { "ATC_C03_____","ATC_C07_____","ATC_C08_____","ATC_C09_____" }, shtml);
	add_panel_chart(rep, vm, { "Creatinine", "eGFR_CKD_EPI", "Urea", "UrineAlbumin", "UrineCreatinine", "Urine_Microalbumin" }, 1, 1, "Renal View", "", { "" }, shtml);
	add_panel_chart(rep, vm, { "Hemoglobin", "RBC", "MCV", "MCH" }, 1, 1, "Red Panel View", "AntiAnemic", { "ATC_B03_____" }, shtml);
	add_panel_chart(rep, vm, { "ALT", "GGT", "AST" }, 1, 1, "Liver Panel View", "", { "" }, shtml);
	add_panel_chart(rep, vm, { "K+", "Cl", "Ca", "Na" }, 1, 1, "Ions Panel View", "", { "" }, shtml);
	//add_panel_chart(rep, vm, { "WBC", "Eosinophils%", "Monocytes%", "Basophils%" , "Lymphocytes%" , "Neutrophils%" }, 1, "White Panel View", shtml);
	add_panel_chart(rep, vm, { "Eosinophils#", "Monocytes#", "Basophils#" , "Lymphocytes#" , "Neutrophils#" }, 0, 1, "White Panel View", "", { "" }, shtml);

	add_RCs_to_js(rep, vm, shtml);


	shtml += "</body>\n";



	int rc = write_string(vm["fout"].as<string>(), shtml);



	return rc;
}

//=========================================================================================
void generate_via_plotly_lib(po::variables_map &vm)
{
	MedPatientPlotlyDate mplot;

	MLOG("1\n");
	if (mplot.read_config(vm["config"].as<string>()) < 0) return;

	MedPidRepository rep;

	MLOG("2\n");
	if (rep.init(vm["rep"].as<string>()) < 0) return;

	MLOG("3\n");
	PidDataRec rec;
	rec.use_dynamic = false;

	rep.get_pid_rec(vm["pid"].as<int>(), rec.rec_static);
	MLOG("4\n");

	string shtml;

	LocalViewsParams lvp(rec.pid(), 0, 0);
	
	mplot.get_rec_html(shtml, lvp, rec, "file", { ChartTimeSign(vm["date"].as<int>(), vm["date_text"].as<string>(), "'black'") });
	MLOG("5\n");

	write_string(vm["fout"].as<string>(), shtml);
	MLOG("6\n");

	return;
}


//========================================================================================
// MAIN
//========================================================================================

int main(int argc, char *argv[])
{
	int rc = 0;
	po::variables_map vm;
	unordered_set<string> report_types;
	vector<string> report_sigs;

	// Reading run Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm, report_types, report_sigs);
	assert(rc >= 0);


	if (1) {
		generate_via_plotly_lib(vm);
		return 0;
	}


	// load rep
	vector<int> pids;
	pids.push_back(vm["pid"].as<int>());
	MedPidRepository rep;
	vector<string> sigs ={}; // all
	if (rep.read_all(vm["rep"].as<string>(), pids, sigs) < 0) {
		MERR("ERROR: failed reading repository %s\n", vm["rep"].as<string>().c_str());
		return -1;
	}
	MLOG("Finished reading signals\n");

	if (vm["sigs"].as<string>() != "")
		return get_sigs_simple_html_report(rep, vm, report_types, report_sigs);

	return 0;
}


