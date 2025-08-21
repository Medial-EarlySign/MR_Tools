#include "diabetes.h"
#include <MedUtils/MedUtils/MedGenUtils.h>
#include <MedMat/MedMat/MedMat.h>

//================================================================================================================
// Command Line Params:
//================================================================================================================
int read_run_params(int argc, char *argv[], po::variables_map& vm) {
	po::options_description desc("Program options");

	try {
		desc.add_options()
			("help", "produce help message")
			("rep", po::value<string>()->default_value("/home/Repositories/THIN/thin_mar2017/thin.repository"), "repository file name")
			("rep_type", po::value<string>()->default_value("thin"), "repository type: thin or mhs")
			("reg_type", po::value<string>()->default_value("diabetes"), "registry type to create: diabetes , ckd , pre2d , dneph, rc")
			("reg_params", po::value<string>()->default_value("reg_mode=2;print=1;diagnosis_importance=5"), "reg_mode: 2:real 1: biological")
			("pids_list", po::value<string>()->default_value(""), "list of pids to work with")
			("dist2", po::value<string>()->default_value(""), "run mutual distribution test")
			("create_registry", "create registries for diabetes and its complications, registry type in reg_type")
			("print_registry",  "create registries for diabetes and its complications, registry type in reg_type")
			("drugs", po::value<string>()->default_value(""), "file name for drugs to use in registry")
			("read_codes", po::value<string>()->default_value(""), "file name for read codes to use in registry")
			("diags", po::value<string>()->default_value(""), "file name for diagnosis codes to use in registry (as read read_code for thin")
			("diag_signal", po::value<string>()->default_value("RC"), "Name of the diagnosis signal - default for this")
			("out_reg", po::value<string>()->default_value(""), "output file name for registry")
			("in_reg", po::value<string>()->default_value(""), "input file name for registry")
			("sampler", po::value<string>()->default_value(""), "sampler params")
			("out_samples", po::value<string>()->default_value(""), "output file name for samples")
			("out_cohort", po::value<string>()->default_value(""), "output file name for cohort")
			("seed", po::value<int>()->default_value(1234), "random seed")
			("ystat", po::value<string>()->default_value(""), "registry for yearly stat")
			("rc_file", po::value<string>()->default_value(""), "read codes for a registry based on read codes only ")
			("renal_rc_file", po::value<string>()->default_value("/nas1/Work/Users/Avi/Diabetes/registries/renal_read_codes_registry.full"), "read codes for renal registry ")
			("dialysis_rc_file", po::value<string>()->default_value("/nas1/Work/Users/Avi/Diabetes/registries/dialysis_read_codes_registry.full"), "read codes for dialysis ")
			("transplant_rc_file", po::value<string>()->default_value("/nas1/Work/Users/Avi/Diabetes/registries/transplant_read_codes_registry.full"), "read codes for transplant ")
			("diabetes_reg", po::value<string>()->default_value("/nas1/Work/Users/Avi/Diabetes/registries/diabetes_part.reg"), "input file name for registry")
			("ckd_reg", po::value<string>()->default_value("/nas1/Work/Users/Avi/Diabetes/registries/ckd2.reg"), "input file name for registry")
			("rc_reg", po::value<string>()->default_value(""), "input file name for a read code based registry")
			("stat_args", po::value<string>()->default_value("year"), "stats param for aggregation. exmaple: year,age,gender")
			("age_bin", po::value<int>()->default_value(5), "age_bin size for stats")
			("ckd_state_level", po::value<int>()->default_value(0), "state for creating nephropathy cohorts")
			("proteinuria", "create the Proteinuria_State , eGFR_CKD_State and CKD_State signals to be loaded to the repository")

			;


		po::store(po::parse_command_line(argc, argv, desc), vm);
		if (vm.count("help")) {
			cerr << desc << "\n";
			exit(-1);

		}
		po::notify(vm);

		set_rand_seed(vm["seed"].as<int>());

		MLOG("=========================================================================================\n");
		MLOG("Command Line:");
		for (int i=0; i<argc; i++) MLOG(" %s", argv[i]);
		MLOG("\n");
		MLOG("..........................................................................................\n");
	}
	catch (exception& e) {
		cerr << "error: " << e.what() << "; run with --help for usage information\n";
		return -1;
	}
	catch (...) {
		cerr << "Exception of unknown type!\n";
		return -1;
	}

	return 0;
}

//..................................................................................................................
int get_pid_list(const string &fname, vector<int> &pids_list)
{
	//MedMat<int> pids;
	pids_list.clear();
	if (fname == "") return 0;

	vector<string> s_pids;
	if (read_text_file_col(fname, "#", ", \t", 0, s_pids) < 0) {
		MERR("Can't open file %s\n", fname.c_str());
		return -1;
	}
	pids_list.clear();
	for (auto &sp : s_pids)
		pids_list.push_back(stoi(sp));
/*
	if (pids.read_from_csv_file(fname, 0) < 0) {
		MERR("Can't open file %s\n", fname.c_str());
		return -1;
	}
	MLOG("read pids mat %d x %d\n", pids.nrows, pids.ncols);
	pids.get_col(0, pids_list);
*/
	return 0;
}

//..................................................................................................................
int get_codes_from_file(const string &fname, vector<string> &codes)
{
	codes.clear();
	if (fname == "") return -1;

	ifstream inf(fname);

	if (!inf) {
		MERR("ERROR: Can't open file %s for read\n", fname.c_str());
		return -1;
	}

	string curr_line;
	while (getline(inf, curr_line)) {
		if ((curr_line.size() > 1) && (curr_line[0] != '#')) {

			if (curr_line[curr_line.size() - 1] == '\r')
				curr_line.erase(curr_line.size() - 1);

			vector<string> fields;
			boost::split(fields, curr_line, boost::is_any_of(" \t"));

			if (fields.size() > 0)
				codes.push_back(fields[0]);
		}
	}

	inf.close();
	MLOG("Read %d codes from file %s\n", codes.size(), fname.c_str());

	return 0;
}

//========================================================================================
// MAIN
//========================================================================================

int main(int argc, char *argv[])
{
	int rc = 0;
	po::variables_map vm;

	// Running Parameters
	MLOG("Reading params\n");
	rc = read_run_params(argc, argv, vm);
	assert(rc >= 0);

	// reading pid_list
	vector<int> pid_list;
	get_pid_list(vm["pids_list"].as<string>(), pid_list);

	// read drugs and read_codes 
	vector<string> drugs;
	if (get_codes_from_file(vm["drugs"].as<string>(), drugs) < 0) MLOG("ERROR !!! No Drug data given !!!!!!!\n");
	vector<string> diags;
	if (get_codes_from_file(vm["diags"].as<string>(), diags) < 0)
		//if diag not found look for read_codes - for backward competability
		if (get_codes_from_file(vm["read_codes"].as<string>(), diags) < 0) MLOG("ERROR !!!!! No diagnoses data given\n");
	MLOG("Got %d drugs, and %d diagnoses to work with\n", drugs.size(), diags.size());

	if (vm.count("create_registry") > 0) {

		//=============================================================================================
		// Creating a Diabetes Registry
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "diabetes") {
			Registry<DiabetesRegRec> DReg;
			get_all_diabetes_reg(vm["rep"].as<string>(), drugs, diags, pid_list, vm["diag_signal"].as<string>(), vm["reg_params"].as<string>(), DReg);
			MLOG("%d records in diabetes registry\n", DReg.reg.size());
			if (vm["out_reg"].as<string>() != "") {
				if (DReg.write_to_file(vm["out_reg"].as<string>()) < 0) {
					MERR("FAILED writing registry file %s\n", vm["out_reg"].as<string>().c_str());
					return -1;
				}
			}
		}

		//=============================================================================================
		// Creating a DM_Registry (collapsing registry to ranges)
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "DM_Registry") {
			if (get_diabetes_range_reg(vm["rep"].as<string>(), vm["diabetes_reg"].as<string>(), vm["out_reg"].as<string>()) < 0) {
				MERR("Failed preparing DM_Registry file %s\n", vm["out_reg"].as<string>().c_str());
				return -1;
			}
			MLOG("Succesfuly created DM_Registry file %s\n", vm["out_reg"].as<string>().c_str());
		}

		//=============================================================================================
		// Creating a CKD registry (just for thin at the moment)
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "ckd" && vm["rep_type"].as<string>() == "thin") {
			Registry<CKDRegRec2> ckd_reg;
			vector<string> rc_files ={ vm["renal_rc_file"].as<string>(), vm["dialysis_rc_file"].as<string>(), vm["transplant_rc_file"].as<string>() };
			get_all_ckd_reg_fixed_thin(vm["rep"].as<string>(), rc_files, pid_list, vm["reg_params"].as<string>(), ckd_reg);
			MLOG("Serializing CKD registry to file %s\n", vm["out_reg"].as<string>().c_str());
			ckd_reg.write_to_file(vm["out_reg"].as<string>());
		}


		//=============================================================================================
		// Creating a read code registry (just for thin at the moment)
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "rc" && vm["rep_type"].as<string>() == "thin") {
			Registry<RCRegRec> rc_reg;
			get_all_rc_reg(vm["rep"].as<string>(), vm["rc_file"].as<string>(), pid_list, rc_reg);
			MLOG("Serializing RC registry (for file %s) to file %s\n", vm["rc_file"].as<string>().c_str(), vm["out_reg"].as<string>().c_str());
			rc_reg.write_to_file(vm["out_reg"].as<string>());
		}

		//=============================================================================================
		// diabetic nephropathy - creating cohort file
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "diabetic_nephropathy" || vm["reg_type"].as<string>() == "dneph") {
			if (create_diabetic_nephropathy_cohort_file(vm["diabetes_reg"].as<string>(), vm["ckd_reg"].as<string>(), vm["out_cohort"].as<string>(), vm["ckd_state_level"].as<int>()) < 0) {
				MERR("FAILED Creating dneph cohort file %s\n", vm["out_cohort"].as<string>().c_str());
				return -1;
			}
		}

		//=============================================================================================
		// general nephropathy - creating cohort file
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "nephropathy" || vm["reg_type"].as<string>() == "neph") {
			if (create_nephropathy_cohort_file(vm["ckd_reg"].as<string>(), vm["out_cohort"].as<string>(), vm["ckd_state_level"].as<int>()) < 0) {
				MERR("FAILED Creating neph cohort file %s\n", vm["out_cohort"].as<string>().c_str());
				return -1;
			}
		}

		//=============================================================================================
		// diabetic retinopathy - creating cohort file
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "diabetic_cvd" || vm["reg_type"].as<string>() == "dret") {
			if (create_diabetic_complication_cohort_file("retinopathy", vm["diabetes_reg"].as<string>(), vm["rc_reg"].as<string>(), vm["out_cohort"].as<string>()) < 0) {
				MERR("FAILED Creating dret cohort file %s\n", vm["out_cohort"].as<string>().c_str());
				return -1;
			}
		}

		//=============================================================================================
		// diabetic cvd occlusive - creating cohort file
		//=============================================================================================
		if (vm["reg_type"].as<string>() == "diabetic_cvd" || vm["reg_type"].as<string>() == "dcvd") {
			if (create_diabetic_complication_cohort_file("cvd occlusive", vm["diabetes_reg"].as<string>(), vm["rc_reg"].as<string>(), vm["out_cohort"].as<string>()) < 0) {
				MERR("FAILED Creating dret cohort file %s\n", vm["out_cohort"].as<string>().c_str());
				return -1;
			}
		}

	}

	//=============================================================================================
	// print a registry
	//=============================================================================================
	if (vm.count("print_registry") > 0) {

		if (vm["in_reg"].as<string>() != "") {
			if (vm["reg_type"].as<string>() == "diabetes" && print_reg<DiabetesRegRec>(vm["in_reg"].as<string>(), vm["print_registry"].as<string>()) < 0) return -1;
			if (vm["reg_type"].as<string>() == "ckd" && print_reg<CKDRegRec2>(vm["in_reg"].as<string>(), vm["print_registry"].as<string>()) < 0) return -1;
		}

	}


	//=============================================================================================
	// annual stats 
	//=============================================================================================
	if (vm["ystat"].as<string>() != "") {
		if (vm["reg_type"].as<string>() == "diabetes") {
			if (vm["stat_args"].as<string>() == "") {
				MERR("please provide aggregation params");
				return -1;
			}
			else
				return get_full_diabetes_stats(vm["ystat"].as<string>(), vm["stat_args"].as<string>(),
					vm["rep"].as<string>(), vm["age_bin"].as<int>());
		}
		if (vm["reg_type"].as<string>() == "diabetic_nephropathy") {
			return get_annual_dneph_stats(vm["diabetes_reg"].as<string>(), vm["ckd_reg"].as<string>());
		}
	}


	//=============================================================================================
	// Running a dist2 session (used mainly to calibrate urine protein signals)
	//=============================================================================================
/*
	if (vm["dist2"].as<string>() != "") {
		MedMutualDist mmd;

		mmd.pids_to_check = pid_list;
		mmd.init_from_string(vm["dist2"].as<string>());
		mmd.collect_values(vm["rep"].as<string>());
		//MLOG("Values Collected!!!!!\n");
		VecMoments vecm;
		for (auto& d : mmd.values) {
			MLOG("%s[%f] :: %s :: %d vals :: ", mmd.sig1.c_str(), d.first, mmd.sig2.c_str(), d.second.size());
			vecm.get_for_vec(d.second);
			MLOG("mean %f std %f median %f\n", vecm.mean, vecm.std, vecm.median);
			//MLOG("%s[%f] :: %s :: %d vals\n", mmd.sig1.c_str(), d.first, mmd.sig2.c_str(), mmd.values[d.first].size());
		}
	}
*/
	//=============================================================================================
	// Create Proteinuria_State signal
	//=============================================================================================
	if (vm.count("proteinuria") > 0) {
		return get_proteinuria_thin(vm["rep"].as<string>(), vm["out_reg"].as<string>());
	}
}

