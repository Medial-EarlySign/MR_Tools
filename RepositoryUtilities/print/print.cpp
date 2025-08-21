// Printing utility for signals 

#include "print.h"
#include "MedUtils/MedUtils/MedUtils.h"

int main(int argc, char *argv[])
{
	int rc = 0;

	// Running parameters
	po::variables_map vm ;
	assert(read_run_params(argc,argv,vm) != -1) ;

	MLOG("Before reading config file %s\n",vm["config"].as<string>().c_str()) ;
	string config_file = vm["config"].as<string>() ;

	vector<string> signals ;
	if (vm.count("signal"))
		signals.push_back(vm["signal"].as<string>()) ;

	if (vm.count("signals_file")) {
		if (read_signals_list(vm["signals_file"].as<string>(),signals) < 0)
			return -1 ;
	}

	if (vm.count("signals")) {
		vector<string> _signals;
		boost::split(_signals, vm["signals"].as<string>(), boost::is_any_of(","));
		signals.insert(signals.end(), _signals.begin(), _signals.end());
	}

	vector<int> ids ;
	if (vm.count("id"))
		ids.push_back(vm["id"].as<int>()) ;

	if (vm.count("ids_file")) {
		if (read_ids_list(vm["ids_file"].as<string>(),ids) < 0)
			return -1 ;
	}

	fprintf(stderr,"Reading %zd signals for %zd ids\n",signals.size(),ids.size()) ;

	MedRepository rep;
	vector<int> dummy ;
	if (ids.empty() && signals.empty()) {
		if (rep.read_all(config_file) < 0) {
			MERR("Cannot read all repository %s\n", config_file.c_str());
			return -1;
		}
	}
	else {
		if (rep.read_all(config_file, ids, signals) < 0) {
			MERR("Cannot read all repository %s\n", config_file.c_str());
			return -1;
		}
	}

	vector<int> signal_ids;
	if (signals.empty()) {
		signal_ids = rep.index.signals ;
	} else {
		for (unsigned int i=0; i<signals.size(); i++) {
			int sid = rep.sigs.sid(signals[i]);
			assert(sid >= 0) ;
			signal_ids.push_back(sid) ;
		}
	}

	fprintf(stderr,"NIDS = %zd. NSIGS = %zd\n",rep.index.pids.size(),signal_ids.size()) ;

	UniversalSigVec usv;

	int from = med_time_converter.convert_date(MedTime::Minutes, 20131001);
	int to = med_time_converter.convert_date(MedTime::Minutes, 20131010);
	for (unsigned int i = 0; i < signal_ids.size(); i++) {
		for (unsigned j = 0; j < rep.index.pids.size(); j++)
//			rep.long_print_data_vec_dict(rep.index.pids[j], signal_ids[i],from,to);
			rep.long_print_data_vec_dict(rep.index.pids[j], signal_ids[i]);
	}

	return rc;
}

int read_ids_list(const string& fname, vector<int>& ids) {

	vector<string> list;
	medial::io::read_codes_file(fname, list);
	for (string& el : list) {
		if (!el.empty()) {
			if (el.find_first_not_of("0123456789") == std::string::npos)
				ids.push_back(stoi(el));
		}
		else
			MWARN("Cannot get an id from %s. Ignoring\n", el.c_str());
	}
}

int read_signals_list(const string& fname, vector<string>& signals) {

	medial::io::read_codes_file(fname, signals);
}


int read_run_params(int argc,char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");
	
	try {
		desc.add_options()	
			("help", "produce help message")	
			("config", po::value<string>()->required(), "conversion confifuration file")
			("signals_file", po::value<string>(), "file of signals to extract ")
			("signal", po::value<string>(), "signal to extract")
			("signals", po::value<string>(), "comma-separated signals to extract")
			("ids_file", po::value<string>(), "file of ids to extract")
			("id", po::value<int>(), "id to extract")
        ;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
            cerr << desc << "\n";
            exit(0);

        }
        po::notify(vm);    
	}
	catch(exception& e) {
        cerr << "error: " << e.what() << "; run with --help for usage information\n";
        return -1;
    }
    catch(...) {
        cerr << "Exception of unknown type!\n";
		return -1;
    }

	return 0 ;
}
