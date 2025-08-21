#define _CRT_SECURE_NO_WARNINGS
#include "binary_bootstrap.h"

/*			Main			*/

int main(int argc, char *argv[]) {


	// Read Running Parameters
	po::variables_map vm ;  
	running_flags flags ; 

	assert(read_run_params(argc,argv,vm,flags) != -1) ;

	// Init output param names
	char *param_names,*autosim_param_names ;
	int nestimates,autosim_nestimates ;
	assert(init_binary_param_names(&nestimates,&param_names,&autosim_nestimates,&autosim_param_names) != -1) ;

	// Initialize random numbers
	srand(vm["seed"].as<int>());
	quick_random qrand;

	// Read data
	input_data indata ;
	assert(read_all_input_data(vm,flags.inc_from_pred, flags.mhs_reg_format,flags.simple_reg_format, flags.read_reg_from_scores, indata) != -1) ;

	// Open output files 
	const char *out_file = vm["out"].as<string>().c_str();
	
	out_fps fouts ;
	fouts.info_fout = NULL ;
	flags.auto_sim_raw = false ;

	assert(open_output_files(out_file,flags,param_names,nestimates,autosim_param_names,autosim_nestimates,fouts)!= -1) ;

	// Allocate.
	work_space work ;
	assert (allocate_data(indata, work) != -1) ;

	// Auto-simulation
	assert(do_binary_autosim(indata,work,fouts,flags,autosim_nestimates,qrand, vm) != -1) ;

	// Time Windows: Loop on time-windows x age-ranges
	assert(do_binary_time_windows(indata,work,fouts,flags,nestimates,qrand, vm) != -1) ;

	return 0;
}

// Functions
/////////////

int read_run_params(int argc,char **argv, po::variables_map& vm, running_flags& flags) {

	po::options_description desc("Program options");
	
	try {
		desc.add_options()	
			("help", "produce help message")	
			("in", po::value<string>()->required(), "scores file")
			("dir", po::value<string>()->default_value("directions_file_not_set"), "cancer registry directions file")
			("params", po::value<string>()->required(), "file specifying time windows, age groups, and last date")				
			("out", po::value<string>()->required(), "prefix of output file names")
			("nbin_types", po::value<int>()->default_value(2)->notifier(&check_nbin_types_value), "number of bin types")
			("reg", po::value<string>()->default_value("W:/CancerData/AncillaryFiles/Registry"), "cancer registry file")
			("byear", po::value<string>()->default_value("W:/CancerData/AncillaryFiles/Byears"), "years of birth file")
			("censor", po::value<string>()->default_value("W:/CancerData/AncillaryFiles/Censor"), "censoring file")
			("prbs", po::value<string>(), "incidence per age file")
			("rem", po::value<string>(), "removal file")
			("inc", po::value<string>(), "inclusion file")
			("seed", po::value<int>()->default_value(1234), "seed for randomizations")
			("raw_only", po::bool_switch(&(flags.raw_only)), "print .Raw and .Info files and exit")
			("inc_from_pred", po::bool_switch(&(flags.inc_from_pred)), "use predcition file as include file")
			("mhs_reg_format", po::bool_switch(&(flags.mhs_reg_format)), "use historical MHS registry format")
			("simple_reg_format", po::bool_switch(&(flags.simple_reg_format)), "use pid,event_date format")
			("read_reg_from_scores", po::bool_switch(&(flags.read_reg_from_scores)), "scores file was created with flow train_test, it contains the registry as well!")
			("nbootstrap", po::value<int>()->default_value(500), " bootstrap rounds")
			("pred_col", po::value<string>()->default_value(""), "name of prediction column")
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

	return 0 ;
}

#define NBOOTSTRAP 500
// Auto-simulation
int do_binary_autosim(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int autosim_nestimates, quick_random& qrand, po::variables_map& vm) {
		
	for (unsigned int j=0; j<indata.age_ranges.size(); j++) {
		fprintf(stderr,"Working on AutoSim on Age Range %d - %d\n",indata.age_ranges[j].first,indata.age_ranges[j].second); 

		// Collect Scores
		int nids,checksum ;
		if (collect_all_binary_autosim_scores(indata.all_scores, indata.registry, indata.last_date, indata.age_ranges[j], indata.byears, indata.censor, work.idstrs, work.types, work.gaps, 
											   &nids, &checksum) == -1) {
			fprintf(stderr,"Score Collection for AutoSim failed\n") ;
			return -1 ;
		}
		fprintf(fouts.autosim_fout,"%d-%d\t%d", indata.age_ranges[j].first, indata.age_ranges[j].second, checksum); 

		if (! flags.raw_only) {

			// Bootstraping estimate of parameters 
			int *sampled_ids = (int *) malloc(nids*sizeof(int)) ;
			if (sampled_ids==NULL) {
				fprintf(stderr,"Allocation failed\n") ;
				return -1 ;
			}

			vector<vector<double> > autosim_bootstrap_estimates(vm["nbootstrap"].as<int>()) ;
			vector<vector<bool> > valid_bootstrap (vm["nbootstrap"].as<int>()) ;

			vector<double> autosim_observables ;
			vector<bool> valid_obeservables ;

			// Observed parameters
			autosim_observables.resize(autosim_nestimates) ;		
			for (int i=0; i<nids; i++)
				sampled_ids[i] = i ;

			if (get_binary_autosim_parameters(sampled_ids,work.types,nids,work.gaps,autosim_observables) != -1) {
				for (int j=0; j<autosim_nestimates; j++)
					valid_obeservables.push_back(true) ;
			} else {
				for (int j=0; j<autosim_nestimates; j++)
					valid_obeservables.push_back(true) ;
			}

			// Bootstrap Estimates

			int nbootstrap = 0 ;

			clock_t start = clock();
			for (int ibs = 0; ibs<vm["nbootstrap"].as<int>(); ibs++) {
				if (ibs % 20 == 0)
					fprintf(stderr,"Bootstrap #%d ... ",ibs) ;

				autosim_bootstrap_estimates[ibs].resize(autosim_nestimates) ;		
				sample_ids(sampled_ids, nids, qrand) ;
				if (get_binary_autosim_parameters(sampled_ids,work.types,nids,work.gaps,autosim_bootstrap_estimates[ibs]) != -1) {
					for (int j=0; j<autosim_nestimates; j++)
						valid_bootstrap[ibs].push_back(true) ;
					nbootstrap ++ ;
				} else {
					for (int j=0; j<autosim_nestimates; j++)
						valid_bootstrap[ibs].push_back(true) ;
				}
			}

			fprintf(stderr,"\n") ;
			fprintf(stderr,"Bootstraping took %f secs\n",(0.0+clock()-start)/CLOCKS_PER_SEC) ;
			free(sampled_ids) ;

			// Print output
			fprintf(fouts.autosim_fout,"\t%d",nbootstrap) ;
			if (nbootstrap > 1)
				print_bootstrap_output(autosim_bootstrap_estimates,autosim_observables,autosim_nestimates,vm["nbootstrap"].as<int>(),valid_bootstrap,valid_obeservables,fouts.autosim_fout) ;
			fprintf(fouts.autosim_fout,"\n") ;

		} //raw only
	}

	fclose(fouts.autosim_fout) ;

	return 0 ;
}

// Initialize names of output parameters
int init_binary_param_names(int *nestimates, char **param_names, int *autosim_nestimates, char **autosim_param_names) {
	
	char _param_names[12][MAX_STRING_LEN] = {"NPOS","NNEG","SPEC", "SENS","OR","NPV","PPV","PR","LIFT","PLR","NLR", "RR"} ;
	char _autosim_param_names[8][MAX_STRING_LEN] = {"TP","FP","PPV","SPEC","SENS","EarlySens1","EarlySens2","EarlySens3" };

	*nestimates = sizeof(_param_names)/MAX_STRING_LEN ;
	*autosim_nestimates = sizeof(_autosim_param_names)/MAX_STRING_LEN ;

	(*param_names) = (char *) malloc((*nestimates)*MAX_STRING_LEN) ;
	(*autosim_param_names) = (char *) malloc((*autosim_nestimates)*MAX_STRING_LEN) ;
	if ((*param_names)==NULL || (*autosim_param_names)==NULL) {
		fprintf(stderr,"Allocation Failed\n") ;
		return -1 ;
	}

	for (int i=0; i<(*nestimates); i++)
		strcpy(*param_names+i*MAX_STRING_LEN,_param_names[i]) ;

	for (int i=0; i<(*autosim_nestimates); i++)
		strcpy(*autosim_param_names+i*MAX_STRING_LEN,_autosim_param_names[i]) ;

	return 0 ;
}

// Time Windows: Loop on time-windows x age-ranges
int do_binary_time_windows(input_data& indata, work_space& work, out_fps& fouts, running_flags& flags, int nestimates, quick_random& qrand, po::variables_map& vm) {
	
	double incidence ; 
	int idx = 0 ;
	for (unsigned int i=0; i<indata.time_windows.size(); i++) {
		for (unsigned int j=0; j<indata.age_ranges.size(); j++) {
			fprintf(stderr,"Working on Time Window %d - %d and Age Range %d - %d\n",indata.time_windows[i].first,indata.time_windows[i].second,indata.age_ranges[j].first, 
				indata.age_ranges[j].second);

			// Collect Scores
			int nids,checksum ;
			if (collect_all_scores(indata.all_scores, indata.registry, indata.last_date, indata.first_date, indata.time_windows[i], indata.age_ranges[j], indata.byears, indata.censor,
									work.idstrs, work.dates, work.days, work.years, work.scores, work.ages, work.id_starts, work.id_nums, work.types, &nids, &checksum) == -1) {
				fprintf(stderr,"Score Collection failed\n") ;
				return -1 ;
			}
	
			if (! flags.raw_only) {
				fprintf(fouts.fout,"%d-%d\t%d-%d\t%d",indata.time_windows[i].first,indata.time_windows[i].second,indata.age_ranges[j].first, indata.age_ranges[j].second, checksum); 
	

				// Observed parameters
				vector<double> observables ;
				vector<bool> valid_observables ;

				observables.resize(nestimates) ;		
				int istats[2][2] ;
				if (get_binary_bootstrap_stats(work.scores, work.ages, work.types, work.id_starts, work.id_nums, nids, istats, indata.incidence_rate, &incidence, flags.use_last, qrand,1) == 0) {
					get_binary_bootstrap_estimate(istats,observables,incidence) ;
					for (int j=0; j<nestimates; j++)
						valid_observables.push_back(true) ;
				} else {
					for (int j=0; j<nestimates; j++)
						valid_observables.push_back(true) ;
				}

				// Bootstraping estimate of parameters ....
				vector<vector<double> > bootstrap_estimates(vm["nbootstrap"].as<int>()) ;
				vector<vector<bool> > valid_bootstrap (vm["nbootstrap"].as<int>()) ;

				clock_t start = clock() ;
				int nbootstrap = 0 ;
				for (int ibs = 0; ibs<vm["nbootstrap"].as<int>(); ibs++) {
					if (ibs % 20 == 0)
						fprintf(stderr,"Bootstrap #%d ... ",ibs) ;

					bootstrap_estimates[ibs].resize(nestimates) ;		
					int istats[2][2] ;
					if (get_binary_bootstrap_stats(work.scores, work.ages, work.types, work.id_starts, work.id_nums, nids, istats, indata.incidence_rate, &incidence, flags.use_last, qrand,0) == 0) {
						get_binary_bootstrap_estimate(istats,bootstrap_estimates[ibs],incidence) ;
						for (int j=0; j<nestimates; j++)
							valid_bootstrap[ibs].push_back(true) ;
						nbootstrap ++ ;
					} else {
						for (int j=0; j<nestimates; j++)
							valid_bootstrap[ibs].push_back(true) ;
					}
				}
				fprintf(stderr,"\n") ;
				fprintf(stderr,"Bootstraping took %f secs\n",(0.0+clock()-start)/CLOCKS_PER_SEC) ;
		
				fprintf(fouts.fout,"\t%d",nbootstrap) ;
			
				if (nbootstrap > 1)
					print_bootstrap_output(bootstrap_estimates,observables,nestimates,vm["nbootstrap"].as<int>(),valid_bootstrap,valid_observables,fouts.fout) ;
				fprintf(fouts.fout,"\n") ;

			} // raw_only

			// Raw and Info files
			char prefix[MAX_STRING_LEN] ;
			sprintf(prefix,"%d-%d-%d-%d",indata.time_windows[i].first,indata.time_windows[i].second,indata.age_ranges[j].first,indata.age_ranges[j].second);		
			print_raw_and_info(work.idstrs, work.dates, work.scores, work.types, work.id_starts, work.id_nums, nids, qrand, fouts.raw_fout, fouts.info_fout, prefix, flags.use_last) ;
		}
	}

	fclose(fouts.fout) ;

	return 0 ;
}