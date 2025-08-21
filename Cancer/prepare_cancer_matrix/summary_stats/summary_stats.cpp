// summary_stats.cpp : Defines the entry point for the console application.
//

#include "stdio.h"
#include <iostream>
#include "read_data.h"
#include "menu.h"
#include <assert.h>
#include "tools.h"
#include <signal.h>
#include "data_types.h"
#include <boost/program_options.hpp>
#include "xls.h"

namespace po = boost::program_options;

extern FILE* fflags = NULL;
//extern libxl::Book* book = NULL;

void signal_handler( int s ) {
	//book->release();   
	//::ShellExecute(NULL, "open", xls_output_filename, NULL, NULL, SW_SHOW);
	exit(0);
}

// Analyze Command Line
int read_run_params(int argc, char **argv, po::variables_map& vm) {

	po::options_description desc("Program options");
	
	try {
		desc.add_options()	
			("help", "produce help message")	
			// Input Files : 
			("path", po::value<string>()->required(), "files path")
			("source", po::value<string>()->required(), "source name")
			("in-ref", po::value<string>()->required(), "input reference name. if none given, use source name")
			("out-ref", po::value<string>(), "optional output reference name")
			("run-7", po::bool_switch(), "a flag indicating non-interactive mode runing mode-7")

        ;

		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
            cerr << desc << "\n";
            return -1;

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


int main(int argc, char * argv[])
{ 
	try {

		po::variables_map vm ;
		if (read_run_params(argc,argv,vm) < 0)
			return -1 ;

		const char *path = vm["path"].as<string>().c_str() ;
		const char *source = vm["source"].as<string>().c_str() ;
		const char *in_ref =vm["in-ref"].as<string>().c_str() ;

		// output filenames
		snprintf( output_last_full_filename, sizeof(output_last_full_filename), output_filename_patten, path, output_last_filename );
		snprintf( output_log_full_filename, sizeof(output_log_full_filename), output_filename_patten, path, output_log_filename );
		snprintf( output_full_comparison_filename, sizeof(output_full_comparison_filename), output_filename_patten, path, output_comparison_filename );

		data_set_t ds;

		int iret = read_data_set( path, source, ds, 0 );
		if ( iret != 0 ) return iret;

		if (vm.count("out-ref")) {
			const char *out_ref = vm["out-ref"].as<string>().c_str() ;
			char out_ref_path[MAX_STRING_LEN];
			snprintf( out_ref_path, sizeof(out_ref_path), refernece_filename_patten, path, out_ref);

			printf( "Notice: Writing summary data to %s for future use\n",out_ref_path );
			reference_data_set_t::save( out_ref_path, ds );
		}

		reference_data_set_t rds;
		
		char in_ref_path[MAX_STRING_LEN];
		snprintf( in_ref_path, sizeof(in_ref_path), refernece_filename_patten, path, in_ref);
		iret = rds.read( in_ref_path );
		if( iret != 0 ) return iret;

		fflags = fopen( output_full_comparison_filename, "wt" );
		if(fflags==NULL) {
			fprintf( stderr, "Error opening comparison output file %s\n", output_full_comparison_filename );	
			return -1;
		}

		xls_create(path);

		xls_add_params( ds );

		bool continue_running = true;
		
		if (vm["run-7"].as<bool>()) {
			write_xls( ds, rds ) ;
		} else {
			while( continue_running ) {
				int key = print_main_menu();
				continue_running = run_main_menu( key, ds, rds );
			} 

			fflush(stdout);
		}

		fclose(fflags);
	} 
	catch ( ... ) {
		fprintf( stderr, "Got exception. Program aborts!\n" );
	}
	return 0;
}


