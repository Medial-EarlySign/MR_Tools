#include "Flow.h"

#include "Logger/Logger/Logger.h"
#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL	LOG_DEF_LEVEL

int flow_create_operations(FlowAppParams &ap)
{
	if (ap.options[OPTION_REP_CREATE])
		flow_rep_create(ap.convert_conf_fname, ap.load_args, ap.load_err_file);

	if (ap.options[OPTION_REP_CREATE_PIDS])
		flow_rep_create_pids(ap.rep_fname);

	if (ap.options[OPTION_CLEAN_DICT])
		flow_clean_dict(ap.vm["rep"].defaulted() ? "" : ap.rep_fname, 
			ap.output_dict_path, ap.output_fname);

	return 0;
}