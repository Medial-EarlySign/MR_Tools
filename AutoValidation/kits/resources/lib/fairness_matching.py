#!/usr/bin/env python
import os, sys, subprocess
from PY_Helper import *
import pandas as pd
from fairness_analysis import read_fairness_analysis, plot_graphs
from reformat_bt_filter import transform_from_bt_filter_to_cohrt

def run_cmd(cmd, file_to_check, override=False):
    if override or not(os.path.exists(file_to_check)):
        print('Will run:\n%s'%(cmd), flush=True)
        p_res=subprocess.run(cmd.split(), capture_output=True)
        output_res_err=p_res.stderr.decode('utf8')
        output_res=p_res.stdout.decode('utf8')
        succ=True
        if p_res.returncode != 0:
            print('Execution failed!!', flush=True)
            succ=False
        if len(output_res)>0:
            print(output_res, flush=True)
        if len(output_res_err)>0:
            print(output_res_err, flush=True)
        return succ
    return True

def prepare_matched(fairness_groups, filter_base_cohort, rep, samples, json_model, model_path, work_dir, match_params, override=False):
    #filter_base_cohort=filter_base.replace(',', ';').replace('-', ',').replace('Time,Window:', 'Time-Window:')
    filter_base=transform_from_bt_filter_to_cohrt(filter_base_cohort)
    os.makedirs(os.path.join(work_dir, 'fairness', 'matching'), exist_ok=True)
    os.makedirs(os.path.join(work_dir, 'tmp'),  exist_ok=True)
    for fairness_defs, fairness_names in fairness_groups:
        
        fname=None
        if len(fairness_defs)!=2:
            print('Can only compare and match with 2 groups, skips', flush=True)
            continue
    
        output_path_tmps=[]
        filters_str=[]
        print('Handling %s'%(fairness_names), flush=True)
        for i, fd in enumerate(fairness_defs):
            
            filter_name, ranges=fd.split(':')
            low_r, high_r = ranges.split(',')
            if fname is None:
                fname = filter_name
            if fname != filter_name:
                raise NameError('Has multiple filters on different fields - not allowed')
            filters_str.append(fname + ':' + '%2.3f'%(float(low_r)) + ',' + '%2.3f'%(float(high_r)))
            filter_cohorts = filter_base_cohort
            if len(filter_cohorts) > 0:
                filter_cohorts = filter_cohorts + ';'
            filter_cohorts = filter_cohorts + filters_str[-1]
            output_path_tmp=os.path.join(work_dir, 'tmp', '%d'%(i))
            filter_cohorts=filter_cohorts
            print('Will filter by: "%s"'%(filter_cohorts), flush=True)
            cmd_filter=f'FilterSamples --rep {rep} --samples {samples} --filter_train 0 --json_mat {json_model} --filter_by_bt_cohort {filter_cohorts} --output {output_path_tmp}'
            succ=run_cmd(cmd_filter, output_path_tmp, True)
            output_path_tmps.append(output_path_tmp)
            if not(succ):
                raise NameError('Failed')
        
        #Union samples:
        output_path=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.samples'%(fname, '_'.join(fairness_names)))
        samples_1=pd.read_csv(output_path_tmps[0], sep='\t')
        samples_2=pd.read_csv(output_path_tmps[1], sep='\t')
        samples_s=pd.concat([samples_1, samples_2], ignore_index=True)
        samples_s.to_csv(output_path, sep='\t', index=False)
        columns_order = list(samples_s.columns)
        
        #Now let's filter by outcome and do the matching separatley:
        cases_path=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.cases.samples'%(fname, '_'.join(fairness_names)))
        controls_path=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.controls.samples'%(fname, '_'.join(fairness_names)))
        filter_samples=pd.read_csv(output_path, sep='\t')
        cases_samples=filter_samples[filter_samples['outcome']>0].reset_index(drop=True).copy()
        controls_samlpes=filter_samples[filter_samples['outcome']==0].reset_index(drop=True).copy()
        cases_samples['outcome']=0
        controls_samlpes['outcome']=0
        #Join with samples_2 - and change to 1. The second is the target
        samples_2=samples_2[['id', 'time', 'outcome']].set_index(['id', 'time']).rename(columns={'outcome': 'is_samples_2'})
        cases_samples=cases_samples.set_index(['id', 'time']).join(samples_2, how='left').reset_index()
        cases_samples.loc[cases_samples['is_samples_2'].notnull() , 'outcome']=1
        cases_samples=cases_samples.drop(columns=['is_samples_2'])
        controls_samlpes=controls_samlpes.set_index(['id', 'time']).join(samples_2, how='left').reset_index()
        controls_samlpes.loc[controls_samlpes['is_samples_2'].notnull() , 'outcome']=1
        controls_samlpes=controls_samlpes.drop(columns=['is_samples_2'])
        
        cases_samples[columns_order].to_csv(cases_path, sep='\t', index=False)
        controls_samlpes[columns_order].to_csv(controls_path, sep='\t', index=False)
        
        output_cases_matched=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.cases.matched.samples'%(fname, '_'.join(fairness_names)))
        output_controls_matched=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.controls.matched.samples'%(fname, '_'.join(fairness_names)))
        
        cmd_match=f'Flow --rep {rep} --filter_and_match --in_samples {cases_path} --out_samples {output_cases_matched} --match_params "{match_params}"'
        succ=run_cmd(cmd_match, output_cases_matched, override)
        if not(succ):
            raise NameError('Failed')
        cmd_match_2=f'Flow --rep {rep} --filter_and_match --in_samples {controls_path} --out_samples {output_controls_matched} --match_params "{match_params}"'
        succ=run_cmd(cmd_match_2, output_controls_matched, override)
        if not(succ):
            raise NameError('Failed')
        #Now join samples after matching:
        matched_cases_sm=pd.read_csv(output_cases_matched, sep='\t')
        matched_controls_sm=pd.read_csv(output_controls_matched, sep='\t')
        matched_samples=pd.concat([matched_controls_sm,  matched_cases_sm], ignore_index=True)
        #Get outcome back from original samples!
        samples_s=samples_s.set_index(['id', 'time']).join(matched_samples[['id', 'time']].set_index(['id', 'time']), how='inner').reset_index()
        output_final_samples=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.final.samples'%(fname, '_'.join(fairness_names)))
        samples_s[columns_order].to_csv(output_final_samples, sep='\t', index=False)
        
        #Get preds:
        output_preds=os.path.join(work_dir, 'fairness', 'matching', '%s-%s.final.preds'%(fname, '_'.join(fairness_names)))
        cmd_pred=f'Flow --get_model_preds --rep {rep} --f_samples {output_final_samples} --f_preds {output_preds} --f_model {model_path}'
        succ=run_cmd(cmd_pred, output_preds, override)
        if not(succ):
            raise NameError('Failed')
        
        #Bootstrap:
        output_bt=os.path.join(work_dir, 'fairness', 'matching', 'bt.matched.%s-%s'%(fname, '_'.join(fairness_names)))
        graph_graph=os.path.join(work_dir, 'fairness', 'matching', 'graph.%s-%s'%(fname, '_'.join(fairness_names)))
        os.makedirs(graph_graph, exist_ok=True)
        cohort_params=os.path.join(work_dir, 'tmp', 'cohort_params')
        fw=open(cohort_params, 'w')
        fw.write(filter_base + '\t'+filter_base_cohort+'\n')
        
        #filter_base_clean='All'
        ff=filter_base_cohort
        if len(filter_base_cohort)>0:
            ff=ff+';'
        ff=ff+ filters_str[0]
        fw.write(filter_base + ',' + filters_str[0].replace(',', '-').replace(';', ',') + '\t' + ff  + '\n')
        #filter_base_clean + '|' + fairness_names[0]
        ff=filter_base_cohort
        if len(ff)>0:
            ff=ff+';'
        ff=ff+ filters_str[1]
        fw.write(filter_base + ',' +filters_str[1].replace(',', '-').replace(';', ',') + '\t' + ff  + '\n')
        fw.close()
        #filter_base_clean + '|' + fairness_names[1]
        #Generate cohort params:
        
        cmd_bt=f'bootstrap_app --use_censor 0 --sample_per_pid 1 --input {output_preds} --rep {rep}  --force_score_working_points 1 --score_resolution 0.005' + \
        f' --json_model {json_model} --output {output_bt} --cohorts_file {cohort_params} --print_graphs_path {graph_graph}'
        succ=run_cmd(cmd_bt, output_bt+ '.pivot_txt', override)
        if not(succ):
            raise NameError('Failed')
        
        graphs_output_pt=os.path.join(work_dir, 'fairness', 'graphs_matched')
        os.makedirs(graphs_output_pt, exist_ok=True)
        plot_graphs(output_bt+ '.pivot_txt', filter_base_cohort, fairness_groups, graphs_output_pt)

init_env(sys.argv, locals())

#Test for parameters
REQ_PARAMETERS=['CONFIG_DIR', 'WORK_DIR', 'REPOSITORY_PATH', 'MODEL_PATH', 'TEST_SAMPLES', 'BT_JSON_FAIRNESS', \
                'FAIRNESS_MATCHING_PARAMS', 'FAIRNESS_BT_PREFIX']
res=test_existence(locals(), REQ_PARAMETERS , TEST_NAME)
if not(res):
    sys.exit(1)
cfg_input=os.path.join(CONFIG_DIR,'fairness_groups.cfg')
cfg_fairness=read_fairness_analysis(cfg_input)

prepare_matched(cfg_fairness, FAIRNESS_BT_PREFIX, REPOSITORY_PATH, TEST_SAMPLES, BT_JSON_FAIRNESS, MODEL_PATH, WORK_DIR, FAIRNESS_MATCHING_PARAMS, OVERRIDE)