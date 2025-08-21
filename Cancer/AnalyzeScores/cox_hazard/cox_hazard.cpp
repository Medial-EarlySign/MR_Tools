#define _CRT_SECURE_NO_WARNINGS
#include "CommonLib/AnalyzeScores.h"
#include "CommonLib/BootstrappingFunctions.h"

namespace po = boost::program_options;

/*			Main			*/

int main(int argc, char *argv[]) {

		// Read Parameters
	po::options_description desc("Program options");
	po::variables_map vm;     
	try {
		desc.add_options()	
			("help", "produce help message")	
			("in", po::value<string>()->required(), "scores file")
			("dir", po::value<string>()->required(), "cancer registry directions file")
			("params", po::value<string>()->required(), "file specifying time windows, age groups, and last date")				
			("out", po::value<string>()->required(), "output directory")
			("nbin_types", po::value<int>()->default_value(2)->notifier(&check_nbin_types_value), "number of bin types")
			("reg", po::value<string>()->default_value("W:/CancerData/AncillaryFiles/Registry"), "cancer registry file")
			("byear", po::value<string>()->default_value("W:/CancerData/AncillaryFiles/Byears"), "years of birth file")
			("censor", po::value<string>()->default_value("W:/CancerData/AncillaryFiles/Censor"), "censoring file")
			("rem", po::value<string>(), "removal file")
			("inc", po::value<string>(), "inclusion file")
			("seed", po::value<int>()->default_value(1234), "seed for randomizations")
        ;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
            cerr << desc << "\n";
            exit(-1);

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

	globalRNG::srand(vm["seed"].as<int>());

	// Read removal file
	map<string, periods> remove_list ;
	if (vm.count("rem") == 1 && read_list(vm["rem"].as<string>().c_str(), remove_list) == -1) {
		fprintf(stderr,"Could not read removal list from file \'%s\'\n", vm["rem"].as<string>().c_str()) ;
		return -1 ;
	}

	// Read inclsion file
	map<string, periods> include_list ;
	if (vm.count("inc") == 1 && read_list(vm["inc"].as<string>().c_str(), include_list) == -1) {
		fprintf(stderr,"Could not read inclusion list from file \'%s\'\n", vm["inc"].as<string>().c_str()) ;
		return -1 ;
	}

	// Read Scores File
	map<string,vector<score_entry> > all_scores ;
	string run_id ;
	map<string, vector<pair<int, int> > > registry;
	map<string, status> censor;
	int nscores = read_scores(vm["in"].as<string>().c_str(), all_scores, run_id, vm["nbin_types"].as<int>(),
							  include_list, remove_list, false, registry, censor, string("")) ;
	if (nscores == -1) {
		fprintf(stderr, "Could not read scores from file \'%s\'\n", vm["in"].as<string>().c_str()) ;
		return -1 ;
	}

	// Read Cancer Directions File
	map<string,int> cancer_directions ;
	if (read_cancer_directions(vm["dir"].as<string>().c_str(), cancer_directions) == -1) {
		fprintf(stderr,"Could not read cancer directions from file \'%s\'\n", vm["dir"].as<string>().c_str()) ;
		return -1 ;
	}

	// Read Extra Params
	vector<pair<int,int> > age_ranges ;
	vector<pair<int,int> > initiation_dates ;
	int last_date ;
	int max_status_year ;

	if (read_extra_params(vm["params"].as<string>().c_str(), initiation_dates, age_ranges, &last_date, &max_status_year) == -1) {
		fprintf(stderr,"Could not read extra parameters from file \'%s\'\n", vm["params"].as<string>().c_str()) ;
		return -1 ;
	}

	// Read Cancer Registry
	if (read_cancer_registry(vm["reg"].as<string>().c_str(), cancer_directions, registry) == -1) {
		fprintf(stderr,"Could not read cancer registry from file \'%s\'\n", vm["reg"].as<string>().c_str()) ;
		return -1 ;
	}

	// Read birth-years
	map<string, int> byears ;
	if (read_byears(vm["byear"].as<string>().c_str(), byears) == -1) {
		fprintf(stderr, "Could not read birth years from file \'%s\'\n", vm["byear"].as<string>().c_str()) ;
		return -1 ;
	}
	
	// Read censoring data
	if (read_censor(vm["censor"].as<string>().c_str(), censor) == -1) {
		fprintf(stderr,"Could not read censoring status from file \'%s\'\n", vm["censor"].as<string>().c_str()) ;
		return -1 ;
	}

	char matrix_file[MAX_STRING_LEN] ;
	sprintf(matrix_file,"%s/%s", vm["out"].as<string>().c_str(), COX_MATRIX_NAME) ;

	char r_matrix_file[MAX_STRING_LEN] ;
	sprintf(r_matrix_file,"%s/%s", vm["out"].as<string>().c_str(), COX_MATRIX_NAME) ;

	// Loop on initiation dates and age ranges
	for (unsigned int i=0; i<initiation_dates.size(); i++) {
		for (unsigned int j=0; j<age_ranges.size(); j++) {
			fprintf(stderr,"Working on Initiation dates %d - %d and Age Range %d - %d\n",initiation_dates[i].first,initiation_dates[i].second,
				age_ranges[j].first, age_ranges[j].second); 
				
			if (create_matrix_for_cox(all_scores, registry, last_date, initiation_dates[i], age_ranges[j], byears, censor, matrix_file) == -1) {
				fprintf(stderr,"COX-Analysis Matrix Creation failed\n") ;
				return -1 ;
			}

			if (perform_cox_analysis(r_matrix_file, vm["out"].as<string>().c_str()) == -1) {
				fprintf(stderr,"COX-Analysis failed\n") ;
				return -1 ;
			}
		}
	}

	return 0 ;
}
