#include <algorithm>
#include <typeinfo>
#include <fstream>
#include "Cmd_Args.h"
#include <MedProcessTools/MedProcessTools/MedModel.h>


#define LOCAL_SECTION LOG_APP
#define LOCAL_LEVEL LOG_DEF_LEVEL

void print_help(const string &section) {
	if (section.empty() || section == "print")
		MLOG("command print $1 {$1 might by one of rep_processors,generators,feature_processors,predictor,post_processors}\n");
	if (section.empty() || section == "change")
		MLOG("command change $1 {$1 might by one of rep_processors,generators,feature_processors,predictor,post_processors}\n");
	if (section.empty())
		MLOG("enter quit/exit to wirte and exit app\n");
}

int print_model_part(const MedModel &model, const string &print_part) {
	if (print_part == "rep_processors") {
		for (size_t i = 0; i < model.rep_processors.size(); ++i)
			model.rep_processors[i]->dprint("RP[" + to_string(i) + "]", 2);
		return (int)model.rep_processors.size();
	}
	if (print_part == "generators") {
		for (size_t i = 0; i < model.generators.size(); ++i)
			model.generators[i]->dprint("GEN[" + to_string(i) + "]", 2);
		return (int)model.generators.size();
	}
	if (print_part == "feature_processors") {
		for (size_t i = 0; i < model.feature_processors.size(); ++i)
			model.feature_processors[i]->dprint("FP[" + to_string(i) + "]", 2);
		return (int)model.feature_processors.size();
	}
	if (print_part == "post_processors") {
		for (size_t i = 0; i < model.post_processors.size(); ++i)
			model.post_processors[i]->dprint("PP[" + to_string(i) + "]");
		return (int)model.post_processors.size();
	}
	if (print_part == "predictor") {
		//model.predictor->print(stderr, "predictor", 2);
		MLOG("MedPredcitor (%s)\n", model.predictor->my_class_name().c_str());
		return 1;
	}
	return -1;
}

int select_num_from_user_input(const string &arg1, int opt_cnt) {
	int selected_parsed = -1;
	if (opt_cnt == 0)
		return selected_parsed;
	if (opt_cnt > 1) {
		string selected_num = "";
		getline(cin, selected_num);

		if (selected_num == "*") {
			return -2; ///mark to select all!!
		}

		try {
			selected_parsed = stoi(selected_num);
		}
		catch (...) {
			MERR("Waited for a number\n");
		}
	}
	else
		selected_parsed = 0;

	if (selected_parsed >= 0 && opt_cnt == 0) {
		MLOG("%s is Empty\n", arg1.c_str());
		selected_parsed = -1;
	}
	if (selected_parsed >= 0 && selected_parsed >= opt_cnt) {
		MLOG("options for %s should be between 0-%d. got %d\n",
			arg1.c_str(), opt_cnt - 1, selected_parsed);
		selected_parsed = -1;
	}

	return selected_parsed;
}

void clear_model(MedModel &model) {
	vector<RepProcessor *> final_res;
	for (size_t i = 0; i < model.rep_processors.size(); ++i)
	{
		if (model.rep_processors[i] != NULL) {
			if (model.rep_processors[i]->processor_type == REP_PROCESS_MULTI) {
				RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(model.rep_processors[i]);
				vector<RepProcessor *> final_res_internal;
				for (size_t j = 0; j < multi->processors.size(); ++j)
					if (multi->processors[j] != NULL)
						final_res_internal.push_back(multi->processors[j]);
				multi->processors = move(final_res_internal);
			}
			final_res.push_back(model.rep_processors[i]);
		}
	}
	model.rep_processors = move(final_res);

	vector<FeatureGenerator *> final_res_g;
	for (size_t i = 0; i < model.generators.size(); ++i)
		if (model.generators[i] != NULL)
			final_res_g.push_back(model.generators[i]);
	model.generators = move(final_res_g);

	vector<FeatureProcessor *> final_res_fp;
	for (size_t i = 0; i < model.feature_processors.size(); ++i)
	{
		if (model.feature_processors[i] != NULL) {
			if (model.feature_processors[i]->processor_type == FTR_PROCESS_MULTI) {
				MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(model.feature_processors[i]);
				vector<FeatureProcessor *> final_res_internal;
				for (size_t j = 0; j < multi->processors.size(); ++j)
					if (multi->processors[j] != NULL)
						final_res_internal.push_back(multi->processors[j]);
				multi->processors = move(final_res_internal);
			}
			final_res_fp.push_back(model.feature_processors[i]);
		}
	}
	model.feature_processors = move(final_res_fp);

	vector<PostProcessor *> final_res_pp;
	for (size_t i = 0; i < model.post_processors.size(); ++i)
	{
		if (model.post_processors[i] != NULL) {
			if (model.post_processors[i]->processor_type == FTR_POSTPROCESS_MULTI) {
				MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(model.post_processors[i]);
				vector<PostProcessor *> final_res_internal;
				for (size_t j = 0; j < multi->post_processors.size(); ++j)
					if (multi->post_processors[j] != NULL)
						final_res_internal.push_back(multi->post_processors[j]);
				multi->post_processors = move(final_res_internal);
			}
			final_res_pp.push_back(model.post_processors[i]);
		}
	}
	model.post_processors = move(final_res_pp);
}

void print_long(const SerializableObject &obj, ofstream &log_file) {
	string all_res = obj.object_json();
	int sz = 5000;
	//print in 50000 tokens:
	while (!all_res.empty()) {
		if (all_res.length() < sz) {
			medial::print::log_with_file(log_file, "%s", all_res.c_str());
			all_res = "";
		}
		else {
			medial::print::log_with_file(log_file, "%s", all_res.substr(0, sz).c_str());
			all_res = all_res.substr(sz);
		}
	}
	medial::print::log_with_file(log_file, "\n");
}

void exit(const vector<string> &record_changes_msg, MedModel &model, const string &output_path) {
	int ch_num = 1;
	for (const string &msg : record_changes_msg)
	{
		MLOG("CHANGE %d :: %s\n", ch_num, msg.c_str());
		++ch_num;
	}
	model.write_to_file(output_path);
	MLOG("Finished\n");
}

int main(int argc, char *argv[]) {
	ProgramArgs args;
	if (args.parse_parameters(argc, argv) < 0)
		return -1;

	MedModel model;
	if (args.change_model_file.empty())
		model.read_from_file(args.model_path);
	else
		model.read_from_file_with_changes(args.model_path, args.change_model_file);
	if (!args.change_model_init.empty()) {
		ChangeModelInfo ch;
		ch.init_from_string(args.change_model_init);
		model.change_model(ch);
	}

	vector<string> record_changes_msg;
	//start manipulation model
	if (args.interactive_change) {
		ofstream log_path;
		if (!args.output_log_file.empty()) {
			log_path.open(args.output_log_file);
			if (!log_path.good())
				MTHROW_AND_ERR("Error can't open %s file for loging\n", args.output_log_file.c_str());
		}

		unordered_set<string> legal_inps = { "rep_processors","generators","feature_processors","predictor","post_processors" };
		vector<string> cmd_tokens;
		string with_input = "", cmd_up = "";
		while (cmd_up != "QUIT" && cmd_up != "EXIT") {
			if (!with_input.empty()) {
				if (cmd_up == "HELP") {
					print_help("");
				}
				else if (boost::starts_with(with_input, "print")) {
					boost::split(cmd_tokens, with_input, boost::is_any_of(" "));
					if (cmd_tokens.size() != 2) {
						MERR("print must provide 1 argument\n");
						print_help("print");
					}
					else {
						string &arg1 = cmd_tokens[1];
						if (legal_inps.find(arg1) == legal_inps.end()) {
							MERR("print has ilegal 1 argument\n");
							print_help("print");
						}
						else {
							int cnt = print_model_part(model, arg1);
							if (cnt == 0)
								MLOG("no %s Empty\n", arg1.c_str());
						}
					}
				}
				else if (boost::starts_with(with_input, "change")) {
					boost::split(cmd_tokens, with_input, boost::is_any_of(" "));
					if (cmd_tokens.size() != 2) {
						MERR("change must provide 1 argument\n");
						print_help("change");
					}
					else {
						string &arg1 = cmd_tokens[1];
						if (legal_inps.find(arg1) == legal_inps.end()) {
							MERR("change has ilegal 1 argument\n");
							print_help("change");
						}
						else {
							//do change inside arg1 - print and ask to choose one to drill down:
							int opt_cnt = print_model_part(model, arg1);
							if (opt_cnt > 1)
								MLOG("Please select one of [0, %d] or * for All: ", opt_cnt - 1);
							int selected_opt = select_num_from_user_input(arg1, opt_cnt);
							string navigation = "";
							char buffer[8000];
							if (opt_cnt == 0)
								MLOG("no %s Empty\n", arg1.c_str());
							if (selected_opt == -2) {
								//selected All:
								//get input:
								snprintf(buffer, sizeof(buffer), "model.%s[*]", arg1.c_str());
								navigation = string(buffer);
								MLOG("Enter new init string or DELETE: ");
								string input_init = "";
								getline(cin, input_init);
								boost::trim(input_init);

								//use input_init
								if (arg1 == "rep_processors") {
									if (input_init == "DELETE") {
										for (size_t i = 0; i < model.rep_processors.size(); ++i) {
											delete model.rep_processors[i];
											model.rep_processors[i] = NULL;
										}
										model.rep_processors.clear();
									}
									else {
										int fail_cnt = 0;
										int succ_cnt = 0;
										for (auto &sel : model.rep_processors)
										{
											if (sel->processor_type == REP_PROCESS_MULTI) {
												RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(sel);
												for (auto &internal_p : multi->processors)
												{
													try {
														internal_p->init_from_string(input_init);
														++succ_cnt;
													}
													catch (const exception &exp) {
														MERR("Failed Exception:\n%s\n", exp.what());
														++fail_cnt;
													}
												}
											}
											else
											{
												try {
													sel->init_from_string(input_init);
													++succ_cnt;
												}
												catch (const exception &exp) {
													MERR("Failed Exception:\n%s\n", exp.what());
													++fail_cnt;
												}
											}
										}
										if (succ_cnt > 0)
											record_changes_msg.push_back(navigation + "\t=>\t{" + input_init + "}\tFailed: " +
												to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
									}
								}
								if (arg1 == "generators") {
									if (input_init == "DELETE") {
										for (size_t i = 0; i < model.generators.size(); ++i) {
											delete model.generators[i];
											model.generators[i] = NULL;
										}
										model.generators.clear();
									}
									else {
										int fail_cnt = 0;
										int succ_cnt = 0;
										for (auto &sel : model.generators)
										{
											try {
												sel->init_from_string(input_init);
												++succ_cnt;
											}
											catch (const exception &exp) {
												MERR("Failed Exception:\n%s\n", exp.what());
												++fail_cnt;
											}
										}
										if (succ_cnt > 0)
											record_changes_msg.push_back(navigation + "\t=>\t{" + input_init + "}\tFailed: " +
												to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
									}
								}
								if (arg1 == "feature_processors") {
									if (input_init == "DELETE") {
										for (size_t i = 0; i < model.feature_processors.size(); ++i) {
											delete model.feature_processors[i];
											model.feature_processors[i] = NULL;
										}
										model.feature_processors.clear();
									}
									else {
										int fail_cnt = 0;
										int succ_cnt = 0;
										for (auto &sel : model.feature_processors)
										{
											if (sel->processor_type == FTR_PROCESS_MULTI) {
												MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(sel);
												for (auto &internal_p : multi->processors)
												{
													try {
														internal_p->init_from_string(input_init);
														++succ_cnt;
													}
													catch (const exception &exp) {
														MERR("Failed Exception:\n%s\n", exp.what());
														++fail_cnt;
													}
												}
											}
											else
											{
												try {
													sel->init_from_string(input_init);
													++succ_cnt;
												}
												catch (const exception &exp) {
													MERR("Failed Exception:\n%s\n", exp.what());
													++fail_cnt;
												}
											}
										}
										if (succ_cnt > 0)
											record_changes_msg.push_back(navigation + "\t=>\t{" + input_init + "}\tFailed: " +
												to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
									}
								}
								if (arg1 == "post_processors") {
									if (input_init == "DELETE") {
										for (size_t i = 0; i < model.post_processors.size(); ++i) {
											delete model.post_processors[i];
											model.post_processors[i] = NULL;
										}
										model.post_processors.clear();
									}
									else {
										int fail_cnt = 0;
										int succ_cnt = 0;
										for (auto &sel : model.post_processors)
										{
											if (sel->processor_type == FTR_POSTPROCESS_MULTI) {
												MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(sel);
												for (auto &internal_p : multi->post_processors)
												{
													try {
														internal_p->init_from_string(input_init);
														++succ_cnt;
													}
													catch (const exception &exp) {
														MERR("Failed Exception:\n%s\n", exp.what());
														++fail_cnt;
													}
												}
											}
											else
											{
												try {
													sel->init_from_string(input_init);
													++succ_cnt;
												}
												catch (const exception &exp) {
													MERR("Failed Exception:\n%s\n", exp.what());
													++fail_cnt;
												}
											}
										}
										if (succ_cnt > 0)
											record_changes_msg.push_back(navigation + "\t=>\t{" + input_init + "}\tFailed: " +
												to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
									}
								}

							}
							else if (selected_opt >= 0) {
								//If multi => choose inside:
								//print med_serialized names of object:
								//get init_string to alter the object
								bool do_all = false;
								int selected_opt_internal = -1;
								if (arg1 == "rep_processors") {
									RepProcessor *sel = model.rep_processors[selected_opt];
									snprintf(buffer, sizeof(buffer), "model.rep_processors[%d]", selected_opt);
									navigation = string(buffer);
									if (sel->processor_type == REP_PROCESS_MULTI) {
										//choose inside again:
										RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(sel);
										MedModel prt_mdl;
										for (size_t j = 0; j < multi->processors.size(); ++j)
											prt_mdl.rep_processors.push_back(multi->processors[j]); //flat internal

										int opt_cnt_multi = print_model_part(prt_mdl, arg1);
										MLOG("Multi Rep Processor - Please select one of [0, %d] or * for All: ",
											opt_cnt_multi - 1);
										for (size_t j = 0; j < multi->processors.size(); ++j)
											prt_mdl.rep_processors[j] = NULL;
										prt_mdl.rep_processors.clear(); //for memory. will be handled by original model
										selected_opt_internal = select_num_from_user_input("RepMultiProcessor",
											opt_cnt_multi);
										do_all = selected_opt_internal == -2;
										if (selected_opt_internal >= 0) {
											sel = multi->processors[selected_opt_internal];
											snprintf(buffer, sizeof(buffer), "model.rep_processors[%d]->processors[%d]",
												selected_opt, selected_opt_internal);
											navigation = string(buffer);
										}
										else
											sel = NULL;
									}
									if (sel != NULL) {
										RepProcessor *&sel_real = model.rep_processors[selected_opt];
										RepProcessor **sel_real_final = &sel_real;
										if (selected_opt_internal >= 0) {
											RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(sel_real);
											sel_real_final = &multi->processors[selected_opt_internal];
										}
										(*sel_real_final)->dprint(navigation, 2);

										MLOG("Enter new init string or DELETE or PRINT: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);
										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tRepProcessor(" + (*sel_real_final)->my_class_name() + ") => \t" + input_init + "\n");
											delete (*sel_real_final);
											*sel_real_final = NULL;

											//clear all nulls from model:
											clear_model(model);
										}
										else if (input_init == "PRINT") {
											print_long(*(*sel_real_final), log_path);
										}
										else {
											try {
												sel->init_from_string(input_init);
												record_changes_msg.push_back(navigation + "\tRepProcessor(" + sel->my_class_name() + ") => \t{" + input_init + "}\n");
											}
											catch (const exception &exp) {
												MERR("Failed Exception:\n%s\n", exp.what());
											}
										}
									}
									if (do_all) {
										//do all inside 
										RepProcessor *&sel_full = model.rep_processors[selected_opt];

										MLOG("Enter new init string or DELETE: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);

										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tRepProcessor(*) => \t" + input_init + "\n");
											delete sel_full;
											sel_full = NULL;

											//clear all nulls from model:
											clear_model(model);
										}
										else {
											RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(sel_full);
											int fail_cnt = 0;
											int succ_cnt = 0;
											for (auto &it_pr : multi->processors)
											{
												try {
													it_pr->init_from_string(input_init);
													++succ_cnt;
												}
												catch (const exception &exp) {
													MERR("Failed Exception:\n%s\n", exp.what());
													++fail_cnt;
												}
											}
											if (succ_cnt > 0)
												record_changes_msg.push_back(navigation + "\tRepProcessor(*) => \t{" + input_init + "}\t" + "Failed: "
													+ to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
										}
									}

								}
								if (arg1 == "generators") {
									FeatureGenerator *&sel = model.generators[selected_opt];
									snprintf(buffer, sizeof(buffer), "model.generators[%d]", selected_opt);
									navigation = string(buffer);
									if (sel != NULL) {
										sel->dprint(navigation, 2);
										MLOG("Enter new init string or DELETE or PRINT: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);
										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tFeatureGenerator(" + sel->my_class_name() + ") => \t" + input_init + "\n");
											delete sel;
											sel = NULL;
											clear_model(model);
										}
										else if (input_init == "PRINT") {
											print_long(*sel, log_path);
										}
										else
										{
											try {
												sel->init_from_string(input_init);
												record_changes_msg.push_back(navigation + "\tFeatureGenerator(" + sel->my_class_name() + ") => \t{" + input_init + "}\n");
											}
											catch (const exception &exp) {
												MERR("Failed Exception:\n%s\n", exp.what());
											}
										}
									}
								}
								if (arg1 == "feature_processors") {
									FeatureProcessor *sel = model.feature_processors[selected_opt];
									snprintf(buffer, sizeof(buffer), "model.feature_processors[%d]", selected_opt);
									navigation = string(buffer);
									if (sel->processor_type == FTR_PROCESS_MULTI) {
										//choose inside again:
										MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(sel);
										MedModel prt_mdl;

										for (size_t j = 0; j < multi->processors.size(); ++j)
											prt_mdl.feature_processors.push_back(multi->processors[j]); //flat internal

										int opt_cnt_multi = print_model_part(prt_mdl, arg1);
										MLOG("Multi Feature Processor - Please select one of [0, %d] or * for All: ",
											opt_cnt_multi - 1);
										for (size_t j = 0; j < multi->processors.size(); ++j)
											prt_mdl.feature_processors[j] = NULL;
										prt_mdl.feature_processors.clear(); //for memory. will be handled by original model
										selected_opt_internal = select_num_from_user_input("MultiFeatureProcessor",
											opt_cnt_multi);
										do_all = selected_opt_internal == -2;
										if (selected_opt_internal >= 0) {
											sel = multi->processors[selected_opt_internal];
											snprintf(buffer, sizeof(buffer), "model.feature_processors[%d]->processors[%d]",
												selected_opt, selected_opt_internal);
											navigation = string(buffer);
										}
										else
											sel = NULL;
									}
									if (sel != NULL) {
										FeatureProcessor *&sel_real = model.feature_processors[selected_opt];
										FeatureProcessor **sel_real_final = &sel_real;
										if (selected_opt_internal >= 0) {
											MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(sel_real);
											sel_real_final = &multi->processors[selected_opt_internal];
										}
										(*sel_real_final)->dprint(navigation, 2);

										MLOG("Enter new init string or DELETE or PRINT: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);
										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tFeatureProcessor(" + (*sel_real_final)->my_class_name() + ") => \t" + input_init + "\n");
											delete (*sel_real_final);
											*sel_real_final = NULL;
											clear_model(model);
										}
										else if (input_init == "PRINT") {
											print_long(*(*sel_real_final), log_path);
										}
										else {
											try {
												sel->init_from_string(input_init);
												record_changes_msg.push_back(navigation + "\tFeatureProcessor(" + sel->my_class_name() + ") => \t{" + input_init + "}\n");
											}
											catch (const exception &exp) {
												MERR("Failed Exception:\n%s\n", exp.what());
											}
										}
									}
									if (do_all) {
										//do all inside 
										FeatureProcessor *&sel_full = model.feature_processors[selected_opt];

										MLOG("Enter new init string or DELETE: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);

										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tFeatureProcessor(*) => \t" + input_init + "\n");
											delete sel_full;
											sel_full = NULL;

											//clear all nulls from model:
											clear_model(model);
										}
										else {
											MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(sel_full);
											int fail_cnt = 0;
											int succ_cnt = 0;
											for (auto &it_pr : multi->processors)
											{
												try {
													it_pr->init_from_string(input_init);
													++succ_cnt;
												}
												catch (const exception &exp) {
													MERR("Failed Exception:\n%s\n", exp.what());
													++fail_cnt;
												}
											}
											if (succ_cnt > 0)
												record_changes_msg.push_back(navigation + "\tFeatureProcessor(*) => \t{" + input_init + "}\t" + "Failed: "
													+ to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
										}
									}
								}
								if (arg1 == "post_processors") {
									PostProcessor *sel = model.post_processors[selected_opt];
									snprintf(buffer, sizeof(buffer), "model.post_processors[%d]", selected_opt);
									navigation = string(buffer);
									if (sel->processor_type == FTR_POSTPROCESS_MULTI) {
										//choose inside again:
										MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(sel);
										MedModel prt_mdl;

										for (size_t j = 0; j < multi->post_processors.size(); ++j)
											prt_mdl.post_processors.push_back(multi->post_processors[j]); //flat internal

										int opt_cnt_multi = print_model_part(prt_mdl, arg1);
										MLOG("Multi Post Processor - Please select one of [0, %d] or * for All: ",
											opt_cnt_multi - 1);
										for (size_t j = 0; j < multi->post_processors.size(); ++j)
											prt_mdl.post_processors[j] = NULL;
										prt_mdl.post_processors.clear(); //for memory. will be handled by original model
										selected_opt_internal = select_num_from_user_input("MultiPostProcessor",
											opt_cnt_multi);
										do_all = selected_opt_internal == -2;
										if (selected_opt_internal >= 0) {
											sel = multi->post_processors[selected_opt_internal];
											snprintf(buffer, sizeof(buffer), "model.post_processors[%d]->post_processors[%d]",
												selected_opt, selected_opt_internal);
											navigation = string(buffer);
										}
										else
											sel = NULL;
									}
									if (sel != NULL) {
										PostProcessor *&sel_real = model.post_processors[selected_opt];
										PostProcessor **sel_real_final = &sel_real;
										if (selected_opt_internal >= 0) {
											MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(sel_real);
											sel_real_final = &multi->post_processors[selected_opt_internal];
										}

										(*sel_real_final)->dprint(navigation);
										MLOG("Enter new init string or DELETE or PRINT: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);
										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tPostProcessor(" + (*sel_real_final)->my_class_name() + ") => \t" + input_init + "\n");
											delete (*sel_real_final);
											*sel_real_final = NULL;
											clear_model(model);
										}
										else if (input_init == "PRINT") {
											print_long(*(*sel_real_final), log_path);
										}
										else {
											try {
												sel->init_from_string(input_init);
												record_changes_msg.push_back(navigation + "\tPostProcessor(" + sel->my_class_name() + ") => \t{" + input_init + "}\n");
											}
											catch (const exception &exp) {
												MERR("Failed Exception:\n%s\n", exp.what());
											}
										}
									}
									if (do_all) {
										//do all inside 
										PostProcessor *&sel_full = model.post_processors[selected_opt];

										MLOG("Enter new init string or DELETE: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);

										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tPostProcessor(*) => \t" + input_init + "\n");
											delete sel_full;
											sel_full = NULL;

											//clear all nulls from model:
											clear_model(model);
										}
										else {
											MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(sel_full);
											int fail_cnt = 0;
											int succ_cnt = 0;
											for (auto &it_pr : multi->post_processors)
											{
												try {
													it_pr->init_from_string(input_init);
													++succ_cnt;
												}
												catch (const exception &exp) {
													MERR("Failed Exception:\n%s\n", exp.what());
													++fail_cnt;
												}
											}
											if (succ_cnt > 0)
												record_changes_msg.push_back(navigation + "\tPostProcessor(*) => \t{" + input_init + "}\t" + "Failed: "
													+ to_string(fail_cnt) + ", Succ: " + to_string(succ_cnt) + "\n");
										}
									}
								}
								if (arg1 == "predictor") {
									MedPredictor *sel = model.predictor;
									snprintf(buffer, sizeof(buffer), "model.predictor");
									navigation = string(buffer);
									if (sel != NULL) {
										MLOG("Enter new init string or DELETE or PRINT: ");
										string input_init = "";
										getline(cin, input_init);
										boost::trim(input_init);
										if (input_init == "DELETE") {
											//delete:
											record_changes_msg.push_back(navigation + "\tMedPredictor(" + sel->my_class_name() + ") => \t" + input_init + "\n");
											delete sel;
											model.predictor = NULL;
										}
										else if (input_init == "PRINT") {
											print_long(*model.predictor, log_path);
										}
										else {
											try {
												sel->init_from_string(input_init);
												record_changes_msg.push_back(navigation + "\tMedPredictor(" + sel->my_class_name() + ") => \t{" + input_init + "}\n");
											}
											catch (const exception &exp) {
												MERR("Failed Exception:\n%s\n", exp.what());
											}
										}
									}
								}
							}
						}
					}
				}
				else {
					MLOG("Unknown Command\n");
					print_help("");
				}
				//parse command with_input:
				//print %1 - can be rep, generators, processors, post_processors

			}
			MLOG("$> "); //read next command
			getline(cin, with_input);
			cmd_up = boost::trim_copy(with_input);
			boost::to_upper(cmd_up);
		}
		MLOG("Done recording changes\n");

		if (!args.output_log_file.empty())
			log_path.close();
	}
	else {
		//non interactive:
		RepProcessor test_rep;
		FeatureGenerator test_gen;
		FeatureProcessor ftr_processor; //needs try catch
		PostProcessor pp_processor;
		MedPredictor predictor;

		global_logger.levels[LOG_REPCLEANER] = MAX_LOG_LEVEL + 1;
		void *obj = test_rep.new_polymorphic(args.search_object_name);
		global_logger.levels[LOG_REPCLEANER] = LOG_DEF_LEVEL;
		int did_cnt = 0, succ_cnt = 0;
		if (obj != NULL) {
			MLOG("Found object as RepProcessor\n");
			RepProcessor *c = static_cast<RepProcessor *>(obj);
			//search for all in rep_processor to send command:
			for (size_t i = 0; i < model.rep_processors.size(); ++i)
			{
				if (typeid(*model.rep_processors[i]) == typeid(*c)) {
					++did_cnt;
					if (args.object_command == "DELETE") {
						delete model.rep_processors[i];
						model.rep_processors[i] = NULL;
						++succ_cnt;
					}
					else {
						try {
							model.rep_processors[i]->init_from_string(args.object_command);
							++succ_cnt;
						}
						catch (exception &exp) {
							MWARN("Error in sending init, got %s\n", exp.what());
						}
					}
				}
				if (model.rep_processors[i]->processor_type == REP_PROCESS_MULTI) {
					RepMultiProcessor *multi = static_cast<RepMultiProcessor *>(model.rep_processors[i]);
					for (size_t j = 0; j < multi->processors.size(); ++j) {
						if (typeid(*multi->processors[j]) == typeid(*c)) {
							++did_cnt;
							if (args.object_command == "DELETE") {
								delete multi->processors[j];
								multi->processors[j] = NULL;
								++succ_cnt;
							}
							else {
								try {
									multi->processors[j]->init_from_string(args.object_command);
									++succ_cnt;
								}
								catch (exception &exp) {
									MWARN("Error in sending init, got %s\n", exp.what());
								}
							}
						}
					}
				}
			}
			if (args.object_command == "DELETE")
				clear_model(model);
			MLOG("Found object as RepProcessor - touched %d objects - succesed in %d\n", did_cnt, succ_cnt);
			delete c;
			exit(record_changes_msg, model, args.output_path);
			return 0;
		}

		global_logger.levels[LOG_FTRGNRTR] = MAX_LOG_LEVEL + 1;
		void *obj_gen = test_gen.new_polymorphic(args.search_object_name);
		global_logger.levels[LOG_FTRGNRTR] = LOG_DEF_LEVEL;
		if (obj_gen != NULL) {
			MLOG("Found object as FeatureGenerator\n");
			FeatureGenerator *c = static_cast<FeatureGenerator *>(obj_gen);
			//search for all in rep_processor to send command:
			for (size_t i = 0; i < model.generators.size(); ++i)
			{
				if (typeid(*model.generators[i]) == typeid(*c)) {
					++did_cnt;
					if (args.object_command == "DELETE") {
						delete model.generators[i];
						model.generators[i] = NULL;
						++succ_cnt;
					}
					else {
						try {
							model.generators[i]->init_from_string(args.object_command);
							++succ_cnt;
						}
						catch (exception &exp) {
							MWARN("Error in sending init, got %s\n", exp.what());
						}
					}
				}
			}
			if (args.object_command == "DELETE")
				clear_model(model);
			MLOG("Found object as FeatureGenerator - touched %d objects - succesed in %d\n", did_cnt, succ_cnt);
			delete c;
			exit(record_changes_msg, model, args.output_path);
			return 0;
		}

		void *obj_ftr_processor = NULL;
		global_logger.levels[LOG_FEATCLEANER] = MAX_LOG_LEVEL + 1;
		try {
			obj_ftr_processor = ftr_processor.new_polymorphic(args.search_object_name);
		}
		catch (...) {
			obj_ftr_processor = NULL;
		}
		global_logger.levels[LOG_FEATCLEANER] = LOG_DEF_LEVEL;
		if (obj_ftr_processor != NULL) {
			MLOG("Found object as FeatureProcessor\n");
			FeatureProcessor *c = static_cast<FeatureProcessor *>(obj_ftr_processor);
			//search for all in rep_processor to send command:
			for (size_t i = 0; i < model.feature_processors.size(); ++i)
			{
				if (typeid(*model.feature_processors[i]) == typeid(*c)) {
					++did_cnt;
					if (args.object_command == "DELETE") {
						delete model.feature_processors[i];
						model.feature_processors[i] = NULL;
						++succ_cnt;
					}
					else {
						try {
							model.feature_processors[i]->init_from_string(args.object_command);
							++succ_cnt;
						}
						catch (exception &exp) {
							MWARN("Error in sending init, got %s\n", exp.what());
						}
					}
				}
				if (model.feature_processors[i]->processor_type == FTR_PROCESS_MULTI) {
					MultiFeatureProcessor *multi = static_cast<MultiFeatureProcessor *>(model.feature_processors[i]);
					for (size_t j = 0; j < multi->processors.size(); ++j) {
						if (typeid(*multi->processors[j]) == typeid(*c)) {
							++did_cnt;
							if (args.object_command == "DELETE") {
								delete multi->processors[j];
								multi->processors[j] = NULL;
								++succ_cnt;
							}
							else {
								try {
									multi->processors[j]->init_from_string(args.object_command);
									++succ_cnt;
								}
								catch (exception &exp) {
									MWARN("Error in sending init, got %s\n", exp.what());
								}
							}
						}
					}
				}
			}
			if (args.object_command == "DELETE")
				clear_model(model);
			MLOG("Found object as FeatureProcessor - touched %d objects - succesed in %d\n", did_cnt, succ_cnt);
			delete c;
			exit(record_changes_msg, model, args.output_path);
			return 0;
		}

		global_logger.levels[LOG_MED_MODEL] = MAX_LOG_LEVEL + 1;
		void *obj_post_processor = pp_processor.new_polymorphic(args.search_object_name);
		global_logger.levels[LOG_MED_MODEL] = LOG_DEF_LEVEL;
		if (obj_post_processor != NULL) {
			MLOG("Found object as PostProcessor\n");
			PostProcessor *c = static_cast<PostProcessor *>(obj_post_processor);
			//search for all in rep_processor to send command:
			for (size_t i = 0; i < model.post_processors.size(); ++i)
			{
				if (typeid(*model.post_processors[i]) == typeid(*c)) {
					++did_cnt;
					if (args.object_command == "DELETE") {
						delete model.post_processors[i];
						model.post_processors[i] = NULL;
						++succ_cnt;
					}
					else {
						try {
							model.post_processors[i]->init_from_string(args.object_command);
							++succ_cnt;
						}
						catch (exception &exp) {
							MWARN("Error in sending init, got %s\n", exp.what());
						}
					}
				}
				if (model.post_processors[i]->processor_type == FTR_POSTPROCESS_MULTI) {
					MultiPostProcessor *multi = static_cast<MultiPostProcessor *>(model.post_processors[i]);
					for (size_t j = 0; j < multi->post_processors.size(); ++j) {
						if (typeid(*multi->post_processors[j]) == typeid(*c)) {
							++did_cnt;
							if (args.object_command == "DELETE") {
								delete multi->post_processors[j];
								multi->post_processors[j] = NULL;
								++succ_cnt;
							}
							else {
								try {
									multi->post_processors[j]->init_from_string(args.object_command);
									++succ_cnt;
								}
								catch (exception &exp) {
									MWARN("Error in sending init, got %s\n", exp.what());
								}
							}
						}
					}
				}
			}
			if (args.object_command == "DELETE")
				clear_model(model);
			MLOG("Found object as PostProcessor - touched %d objects - succesed in %d\n", did_cnt, succ_cnt);
			delete c;
			exit(record_changes_msg, model, args.output_path);
			return 0;
		}

		global_logger.levels[LOG_MEDALGO] = MAX_LOG_LEVEL + 1;
		void *obj_predictor = predictor.new_polymorphic(args.search_object_name);
		global_logger.levels[LOG_MEDALGO] = LOG_DEF_LEVEL;
		if (obj_predictor != NULL) {
			MLOG("Found object as MedPredictor\n");
			MedPredictor *c = static_cast<MedPredictor *>(obj_predictor);

			if (typeid(*model.predictor) == typeid(*c)) {
				++did_cnt;
				if (args.object_command == "DELETE") {
					delete model.predictor;
					model.predictor = NULL;
					++succ_cnt;
				}
				else {
					try {
						model.predictor->init_from_string(args.object_command);
						++succ_cnt;
					}
					catch (exception &exp) {
						MWARN("Error in sending init, got %s\n", exp.what());
					}
				}


			}

			MLOG("Found object as MedPredictor - touched %d objects - succesed in %d\n", did_cnt, succ_cnt);
			delete c;
			exit(record_changes_msg, model, args.output_path);
			return 0;
		}

		if (!args.change_model_init.empty() || !args.change_model_file.empty()) {
			MLOG("Has change_model_init,change_model_file - storing after changes\n");
			exit(record_changes_msg, model, args.output_path);
			return 0;
		}

		MLOG("Warn - can't find object %s - exits without save\n", args.search_object_name.c_str());
		return 0;
	}

	exit(record_changes_msg, model, args.output_path);
	return 0;
}