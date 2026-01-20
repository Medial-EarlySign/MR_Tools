#ifndef __CMD_ARGS___H__
#define __CMD_ARGS___H__

#include <string>
#include <getopt.h>
#include "utils.h"

using namespace std;

#define LOCAL_SECTION LOG_APP
class ProgramArgs
{
public:
	string algomarker_path = "";
	string library_path = "";

	string address = "0.0.0.0";
	unsigned short port = 88;
	bool no_prints = false;
	int num_of_threads = 1;

	bool debug;											///< a debug flag for verbose printing. will be init from command args
	string app_logo = "\
##     ## ######## ########  ####    ###    ## \n\
###   ### ##       ##     ##  ##    ## ##   ##    \n\
#### #### ##       ##     ##  ##   ##   ##  ##       \n\
## ### ## ######   ##     ##  ##  ##     ## ##       \n\
##     ## ##       ##     ##  ##  ######### ##       \n\
##     ## ##       ##     ##  ##  ##     ## ##       \n\
##     ## ######## ########  #### ##     ## ######## "; ///< the application logo/name

	/// the main function to parse the command arguments
	bool parse_parameters(int argc, char *argv[])
	{
		int c;
		static struct option long_options[] = {
			{"help", no_argument, 0, 'h'},
			{"debug", no_argument, 0, 'd'},
			{"version", no_argument, 0, 'v'},
			{"algomarker_path", required_argument, 0, 'a'},
			{"library_path", required_argument, 0, 'l'},
			{"address", required_argument, 0, 'i'},
			{"port", required_argument, 0, 'p'},
			{"no_prints", no_argument, 0, 'n'},
			{"num_of_threads", required_argument, 0, 't'},
			{0, 0, 0, 0} // Terminator
		};
		string full_params;
		bool stop_proc = false;
		while (1)
		{
			int option_index = 0;

			c = getopt_long(argc, argv, "hdvo:a:l:i:p:nt:", long_options, &option_index);

			if (c == -1)
				break; // End of options

			switch (c)
			{
			case 'h':
				std::cout << "Those are the argument names: " << std::endl;
				for (size_t i = 0; i < sizeof(long_options) / sizeof(long_options[0]); ++i)
					std::cout << long_options[i].name << std::endl;
				stop_proc = true;
				break;
			case 'd':
				debug = true;

				MLOG(false, "Version Info:\n%s\n", get_git_version().c_str());
				MLOG(false, "Debug Running With:\n");
				full_params = string(argv[0]);
				char buffer[1000];
				snprintf(buffer, sizeof(buffer), "%s", argv[0]);
				for (size_t i = 1; i < argc; ++i)
				{
					MLOG(false, " %s", argv[i]);

					// gets deafult value when defaulted
					// desc.find(it->first, true).semantic()

					snprintf(buffer, sizeof(buffer), " %s", argv[i]);
					full_params += string(buffer);
				}
				MLOG(false, "######################################\n\n%s\n", app_logo.c_str());
				MLOG(false, "######################################\n");
				MLOG(false, "Full Running Command:\n%s\n", full_params.c_str());
				MLOG(false, "######################################\n");
				break;
			case 'v':
				std::cout << app_logo << "\n"
						  << "Version Info:\n"
						  << get_git_version() << std::endl;
				stop_proc = true;
				break;
			case 'a':
				algomarker_path = string(optarg);
				break;
			case 'l':
				library_path = string(optarg);
				break;
			case 'i':
				address = string(optarg);
				break;
			case 'p':
				port = atoi(optarg);
				break;
			case 'n':
				no_prints = true;
				break;
			case 't':
				num_of_threads = atoi(optarg);
				break;
			case '?':
				throw invalid_argument("Unknown option : " + string(optarg) + "\n");
				// Unknown option or missing required argument
			default:
				std::cout << "Unknown error" << std::endl;
				break;
			}
			if (stop_proc)
				break;
		}

		// Process any remaining non-option arguments
		if (optind < argc)
		{
			std::cout << "Non-option arguments: ";
			while (optind < argc)
				std::cout << argv[optind++] << " ";
			std::cout << std::endl;
		}

		// Check required:
		if (!stop_proc && algomarker_path.empty())
			throw logic_error("Must provide algomarker_path");
		return stop_proc;
	}
};

#endif
