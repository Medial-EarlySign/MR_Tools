#ifndef __CMD_ARGS_H__
#define __CMD_ARGS_H__

#include <MedUtils/MedUtils/MedUtils.h>

class Program_Args : public medial::io::ProgramArgs_base {
private:
	string sigs_s;
	void post_process() {
		if (sigs_s.empty() && model_path.empty())
			HMTHROW_AND_ERR("Error - please provide either model_path or list of signals\n");
		if (!sigs_s.empty() && !model_path.empty())
			HMTHROW_AND_ERR("Error - please provide either model_path or list of signals - not both\n");

		if (!sigs_s.empty()) {
			if (boost::starts_with(sigs_s, "file:")) 
				medial::io::read_codes_file(sigs_s.substr(5), sigs);
			else
				boost::split(sigs, sigs_s, boost::is_any_of(","));
		}
	}
public:

	string rep;
	vector<string> sigs;
	string output_path;
	string model_path;
	int till_date;

	Program_Args() {
		po::options_description prg_options("Global Options");

		prg_options.add_options()
			("rep", po::value<string>(&rep)->required(), "repository")
			("sigs", po::value<string>(&sigs_s)->default_value(""), "signal names list")
			("model_path", po::value<string>(&model_path)->default_value(""), "optional model path to retrieve signal list")
			("till_date", po::value<int>(&till_date)->default_value(20300101), "default sample date to limit")
			("output_path", po::value<string>(&output_path)->required(), "the output path")
			;

		init(prg_options);
	}
};


#endif // !__CMD_ARGS_H__