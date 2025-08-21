#ifndef __CMD_ARGS_H__
#define __CMD_ARGS_H__

#include <MedUtils/MedUtils/MedUtils.h>

class Program_Args : public medial::io::ProgramArgs_base {
private:
	void post_process() {}
public:
	
	string rep;
	string sig;
	string regex_target; ///< takes all codes not from this regex and see if they are mapped to a code with this regex (has father of this type)
	string output_path;
	
	Program_Args() {
		po::options_description prg_options("Global Options");

		prg_options.add_options()
			("rep", po::value<string>(&rep)->required(), "repository")
			("sig", po::value<string>(&sig)->required(), "signal name")
			("regex_target", po::value<string>(&regex_target)->required(), "regex to filter codes to exclude, test all other codes to this group")
			("output_path", po::value<string>(&output_path)->required(), "the output path")
			;

		init(prg_options);
	}
};


#endif // !__CMD_ARGS_H__