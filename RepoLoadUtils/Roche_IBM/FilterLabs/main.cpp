#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <dirent.h>
#include <unordered_set>
#include <unordered_map>
#include <algorithm>

using namespace std;

void replace_all(string& str, const string& from, const string& to) {
    if(from.empty())
        return;
    size_t start_pos = 0;
    while((start_pos = str.find(from, start_pos)) != string::npos) {
        str.replace(start_pos, from.length(), to);
        start_pos += to.length(); // In case 'to' contains 'from', like replacing 'x' with 'yx'
    }
}

void get_files(const string &dir_path, vector<string> &files) {
	DIR *dirp = opendir(dir_path.c_str());
	if (dirp == NULL)
		throw invalid_argument("can't open directory " + dir_path + "\n");
	dirent *dp=  NULL;
	files.clear();
	while ((dp = readdir(dirp)) != NULL)
        files.push_back(dp->d_name);
	(void)closedir(dirp);
}

void trim(string &str) {
	static unordered_set<char> space_chars= {' ', '\t', '\n', '\r'};
	
	size_t i=0, start_idx=0, end_idx=0;
	bool start_mode=true;
	while (i<str.size()) {
		if (start_mode) {
			if (space_chars.find(str.at(i))==space_chars.end())
				start_mode=false;
			else
				++start_idx;
		}
		
		if (space_chars.find(str.at(i))==space_chars.end()) 
			end_idx = i;
	
		++i;
		
	}
	++end_idx;
	str=str.substr(start_idx, end_idx-start_idx);
}

void read_file_codes(const string &file_path, vector<string> &tokens) {
	char msg_buffer[5000];
	tokens.clear();
	ifstream file;
	file.open(file_path);
	if (!file.is_open()) {
		snprintf(msg_buffer, sizeof(msg_buffer), "Unable to open file for reading:\n%s\n", file_path.c_str());
		printf("%s", msg_buffer);
		throw invalid_argument(msg_buffer);
	}

	string line;
	//getline(file, line); //ignore first line
	while (getline(file, line)) {
		trim(line);
		if (line.empty())
			continue;
		if (line.at(0) == '#')
			continue;
		if (line.find('\t') != string::npos)
			line = line.substr(0, line.find('\t'));
		tokens.push_back(line);
	}
	file.close();
}

void split_by_tab(const string &str, vector<string> &tokens) {
	size_t i =0, start_idx=0;
	tokens.clear();
	while (i<str.size()) {
		if (str.at(i)== '\t') {
			tokens.push_back(str.substr(start_idx, i-start_idx));
			start_idx=i+1;
		}
	
		++i;
		
	}
	//add last
	tokens.push_back(str.substr(start_idx));
}

class Admission_dates {
	public:
	int start_date;
	int end_date;
};

void read_admissions(unordered_map<int, vector<Admission_dates>> &patient_admissions, const string &admission_path, const unordered_set<string> &filter_codes) {
	ifstream file(admission_path);
	if (!file.is_open()) 
		throw invalid_argument("Unable to open file for reading " + admission_path);
	string line;
	vector<string> tokens;
	size_t line_num=0;
	while (getline(file, line)) {
		//trim(line);
		++line_num;
		if (line.empty())
			continue;
		if (line.at(0) == '#')
			continue;
			
		//patient, signal, start_date, end_date, type
		split_by_tab(line, tokens);
		if (tokens.size()<5)
			throw invalid_argument("Bad file format " + admission_path + " in line " + to_string(line_num) + " has " + to_string(tokens.size()));
		Admission_dates adm;
		int pid;
		replace_all(tokens[2], "-", "");
		replace_all(tokens[3], "-", "");
		try {
			pid = stoi(tokens[0]);
			adm.start_date= stoi(tokens[2]);
			adm.end_date= stoi(tokens[3]);
		}
		catch (...) {
			cerr << "Error can't convert \"" << tokens[0] << "\" or \"" << tokens[2] <<
			"\" or \"" << tokens[3] << "\" to number. in line " <<
			line_num << endl << line << endl;
			throw;
		}
		string type=tokens[4];
		//if (line_num < 5) {
		//	cout << "Read exampe. pid=" << pid << ", start=" << adm.start_date
		//	<< ", end=" << adm.end_date << ", type=" << type << endl;
		//}
		if (filter_codes.find(type) != filter_codes.end()) {
			//found - add to blacklist codes
			vector<Admission_dates> &pid_a = patient_admissions[pid];
			pid_a.push_back(adm);
		}
	}
	//sort admissions for each patient:
	for (auto &it : patient_admissions)
		sort(it.second.begin(), it.second.end(), [](const Admission_dates &a, const Admission_dates &b) { return a.start_date < b.start_date; });

	file.close();
	
}

void filter_file(const string &full_path, const unordered_map<int, vector<Admission_dates>> &patient_admissions, const string &out_path) {
	ifstream file_reader(full_path);
	if (!file_reader.is_open()) 
		throw invalid_argument("Unable to open file for reading " + full_path);
	ofstream file_out(out_path);
	if (!file_out.is_open()) {
		file_reader.close();
		throw invalid_argument("Unable to open file for writing " + out_path);
	}
	string line;
	vector<string> tokens;
	int line_num = 0, count_rows=0;
	while (getline(file_reader, line)) {
		++line_num;
		trim(line);
		if (line.empty())
			continue;
		split_by_tab(line, tokens);
		if (tokens.size() < 4) {
			file_out.close();
			file_reader.close();
			throw invalid_argument("Bad file format " + full_path);
		}
		
		
		int pid, date;
		replace_all(tokens[2], "-", "");
		try {
			pid= stoi(tokens[0]);
			date=stoi(tokens[2]);
		}
		catch (...) {
			cerr << "can't convert \"" << tokens[0] << "\" or \"" << tokens[2] << "\""		<< endl;
			throw;
		}
		if (patient_admissions.find(pid) == patient_admissions.end()) {
			file_out << line << "\n";
			//if (line_num<5) {
			//	cout << pid << ", date=" << date << ", empty" <<  endl;
			//}
			++count_rows;
		}
		else {
			
			const vector<Admission_dates> &adm_dates = patient_admissions.at(pid);
			//if (line_num<5) {
			//	cout << pid << ", date=" << date << " has " << adm_dates.size() << " cand" << endl;
			//}
			//Test if date is inside one of those date range:
			bool is_inside=false;
			size_t i = 0;
			//stops when reacheds end, already found intersection or passed start_date is after date (no chance for intersectin).
			while (i < adm_dates.size() && !is_inside && adm_dates[i].start_date <= date) {
				is_inside = (date <= adm_dates[i].end_date); //already known that (date >= start_date)
				++i;
			}
			
			if (!is_inside) {
				file_out << line << "\n";
				++count_rows;
			}
		}
	}

	file_out.close();
	file_reader.close();
	cout << full_path  << " had " << line_num << " row, filtered " << count_rows << " out of them" << endl;
}

bool file_selection(const string &file) {
	//return file == "Hemoglobin1";
	return file!="." && file !="..";
}

int main(int argc, char *argv[]) {
	string labs_path="/mnt/work/LGI/loading_files/FinalSignals/BeforeFilter";
	string inpaitient_list = "/mnt/work/LGI/etl/configs/admissions_inpatient.list";
	string out_path="/mnt/work/LGI/loading_files/FinalSignals";
	if (argc > 1) 
		labs_path= string(argv[1]);
	if (argc > 2)
		inpaitient_list=string(argv[2]);
	if (argc > 3)
		out_path=string(argv[3]);

	cout << "labs_path=" << labs_path << "\n" << "inpaitient_list=" << inpaitient_list << "\n"
		<< "out_path="  << out_path << endl;
	
	unordered_map<int, vector<Admission_dates>> patient_admissions;
	vector<string> files, admission_codes;
	get_files(out_path, files);
	read_file_codes(inpaitient_list, admission_codes);
	cout << "Read " << admission_codes.size() << " codes" << endl;
	unordered_set<string> filter_codes(admission_codes.begin(), admission_codes.end());
	
	for (const string &file : files) 
		if (file.substr(0,9)=="ADMISSION") {
			string full_path = out_path + "/" + file;
			cout << "Reading admissions from " << full_path << endl;
			
			read_admissions(patient_admissions, full_path, filter_codes);
			
	    }
	cout << "Has " << patient_admissions.size() << " patients with admissions" << endl;
	files.clear();
	get_files(labs_path, files);
	//Now read labs and filter by patient_admissions object:
	for (const string &file : files) 
		if (file_selection(file))	{
			string full_path = labs_path + "/" + file;
			string out_file_path = out_path + "/" + file;
			cout << "filtering " << full_path << " to " << out_file_path << endl;
			filter_file(full_path, patient_admissions, out_file_path);
		}

	return 0;
}

