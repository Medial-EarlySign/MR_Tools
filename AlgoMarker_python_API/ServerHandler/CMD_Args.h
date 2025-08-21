#ifndef __CMD_ARGS___H__
#define __CMD_ARGS___H__

#include <string>
#include "utils.h"

using namespace std;
namespace po = boost::program_options;

#define LOCAL_SECTION LOG_APP
class ProgramArgs : public ProgramArgs_base
{
private:
	void post_process() {}
public:
	string algomarker_path;
    string library_path;
	
    string address;
    unsigned short port;
	bool no_prints;
	int num_of_threads;

	ProgramArgs() {
		po::options_description pr_opts("AlgoMarker_Server Options");
		pr_opts.add_options()
			("algomarker_path", po::value<string>(&algomarker_path)->required(), "algomarker amconfig file path")
			("library_path", po::value<string>(&library_path)->default_value(""), "shared library path")
            ("address", po::value<string>(&address)->default_value("0.0.0.0"), "server ip address")
            ("port", po::value<unsigned short>(&port)->default_value(88), "server port")
			("no_prints", po::value<bool>(&no_prints)->default_value(false), "if true will no print each requets to stdout")
			("num_of_threads", po::value<int>(&num_of_threads)->default_value(1), "Number of allwo threads. 0 will use system")
			;

		init(pr_opts);
	}

};

#endif
