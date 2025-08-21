#ifndef __UTILS____H_
#define __UTILS____H_
#include <string>
#include <boost/program_options.hpp>
using namespace std;

void MLOG(bool throw_exp, const char *fmt, ...);

namespace po = boost::program_options;

		class ProgramArgs_base {
		private:
			string base_config; ///< config file with all arguments - in CMD we override those settings
			bool init_called; ///< mark for calling init function

			po::options_description desc; ///< the program_options object
			/// converts string arguments to enums if the program has some. 
			/// keep the raw string params from the user input as private and keep
			/// the Enum result of the converted as public.
			virtual void post_process() {};
			/// finds module section help in full help message
			string get_section(const string &full_help, const string &search);

			/// list all help section names for search
			void list_sections(const string &full_help, vector<string> &all_sec);
		protected:
			/// an init function
			void init(po::options_description &prg_options, const string &app_l = "");
			/// the ctor of base class
			ProgramArgs_base() { init_called = false; debug = false; }
		public:
			bool debug; ///< a debug flag for verbose printing. will be init from command args
			po::variables_map vm;
			string app_logo = "\
##     ## ######## ########  ####    ###    ## \n\
###   ### ##       ##     ##  ##    ## ##   ##    \n\
#### #### ##       ##     ##  ##   ##   ##  ##       \n\
## ### ## ######   ##     ##  ##  ##     ## ##       \n\
##     ## ##       ##     ##  ##  ######### ##       \n\
##     ## ##       ##     ##  ##  ##     ## ##       \n\
##     ## ######## ########  #### ##     ## ######## "; ///< the application logo/name



			/// the main function to parse the command arguments
			virtual int parse_parameters(int argc, char *argv[]);

		};
#endif