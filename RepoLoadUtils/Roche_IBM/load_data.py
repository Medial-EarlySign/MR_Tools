#!/usr/bin/python
from basic_loader import read_table_united
from Configuration import Configuration
import os,sys, random
import pandas as pd
from datetime import datetime

sys.path.insert(0, '/mnt/work/Infra/tools/common')
from stage_to_signals import handle_batch

def load_drugs(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'record_id_hash', 'data_grid_date_updated', 'std_dosage', 'std_drug_desc', 'ndc_code', 'all_ndc_codes', 'std_quantity', 'std_refills', 'std_route', 'rxnorm_concept_id', 'encounter_date', 'encounter_record_id_hash', 'encounter_join_id', 'start_date', 'end_date', 'prescription_date', 'display_ndc', 'rx_cui', 'target_concept_type', 'concept_id', 'concept_description', 'std_ordering_mode', 'std_order_status', 'claim_type', 'ingredient_rx_cui_join_id', 'ingredient_descriptions', 'generic_package_join_id', 'generic_drug_package_descriptions', 'snomed_join_id', 'snomed_drug_descriptions', 'brand_name_join_id', 'brand_name_descriptions', 'sigs']
    batch_size=int(5e7)
    #minimal_take_cols=['pid', 'start_date', 'end_date', 'prescription_date', 'rx_cui', 'std_drug_desc', 'std_order_status', 'std_quantity', 'std_dosage', 'std_ordering_mode']
    minimal_take_cols=['pid', 'start_date', 'end_date', 'prescription_date', 'rx_cui', 'std_order_status', 'std_quantity', 'std_ordering_mode']
    data=read_table_united(cfg.data_dir, 'v_drug', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'Drug'), process_function=lambda data:  proc_drug(data), sort_by=['pid', 'start_date'] )
    return data

def load_procedures(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid',  'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'procedure_code', 'std_procedure_modifiers', 'procedure_date', 'std_order_status', 'encounter_record_id_hash', 'encounter_join_id', 'snomed_id', 'snomed_join_id', 'cpt_concept', 'icd_code', 'icd_version', 'is_principal', 'claim_type', 'line_charge']
    batch_size=int(5e7)
    minimal_take_cols=['pid', 'procedure_date', 'cpt_concept', 'icd_version', 'icd_code', 'std_order_status', 'is_principal']
    data=read_table_united(cfg.data_dir, 'v_procedure', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'PROCEDURES'), process_function=lambda data:  proc_procedures(data), sort_by=['pid', 'procedure_date'] )
    return data


def load_problem_list(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid',  'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'diagnosis_code', 'icd_code', 'icd_version', 'chronicity', 'std_disorer_status', 'std_diagnosis_status', 'encounter_record_id_hash', 'encounter_join_id', 'diagnosis_start_date', 'diagnosis_end_date', 'snomed_join_id']
    batch_size=int(5e7)
    minimal_take_cols=['pid', 'diagnosis_start_date', 'icd_version', 'icd_code']
    data=read_table_united(cfg.data_dir, 'v_problem_list', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'DIAGNOSIS_problem_list'), process_function=lambda data:  proc_problem_list(data), sort_by=['pid', 'diagnosis_start_date'] )
    return data

#Diagnosis and treatments reported by the patient
def load_medial_hostory(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid',  'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'encounter_record_join_id', 'encounter_join_id', 'icd_code', 'icd_version', 'std_medial_history_date', 'contact_date', 'snomed_join_id']
    batch_size=int(5e7)
    minimal_take_cols=['pid', 'std_medial_history_date', 'icd_version', 'icd_code', 'contact_date']
    data=read_table_united(cfg.data_dir, 'v_medical_history', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'DIAGNOSIS_history'), process_function=lambda data:  proc_medical_history(data), sort_by=['pid', 'std_medial_history_date'] )

def load_admissions(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid',  'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'std_admission_source', 'std_admission_type', 'std_discharge_disposition', 'encounter_join_hash', 'encounter_join_id', 'admission_date', 'discharge_date', 'contact_date']
    batch_size=int(5e7)
    minimal_take_cols=['pid', 'admission_date', 'discharge_date', 'std_admission_type']
    data=read_table_united(cfg.data_dir, 'v_admission', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'ADMISSION'),
            process_function=lambda data:  proc_admission(data), sort_by=['pid', 'admission_date'] )

    return data

def load_encounters(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'encounter_join_id', 'encounter_canceled', 'encounter_closed', 'std_encounter_type', 'std_encounter_status', 'appt_made_date', 'check_in_time', 'encounter_date']
    batch_size=int(5e7)
    minimal_take_cols=['pid', 'encounter_date', 'std_encounter_type']
    data=read_table_united(cfg.data_dir, 'v_encounter.csv', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'ENCOUNTER'),
            process_function=lambda data:  proc_encounter(data), sort_by=['pid', 'encounter_date'] )

    return data


def load_diagnosis(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'diagnosis_code', 'icd_code', 'icd_version', 'encounter_join_id', 'encounter_join_hash', 'diagnosis_date', 
            'is_principal', 'is_admitting', 'is_reason_for_visit', 'status', 'claim_type', 'snomed_join_id']
    batch_size=int(5e7)
    minimal_take_cols=['pid', 'diagnosis_date', 'icd_code', 'icd_version']
    data=read_table_united(cfg.data_dir, 'v_diagnosis', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'DIAGNOSIS'),
            process_function=lambda data:  proc_diagnosis(data) )

    return data

def load_single_lab_from_mem(cfg, all_df, sig, unit_mult, sig_map, min_th=0, batch=None):
    all_errors=pd.DataFrame()
    out_folder=os.path.join(cfg.work_dir, 'FinalSignals', 'BeforeFilter')
    os.makedirs(out_folder, exist_ok=True)

    print('%s :: Preparing signal %s from mem'%(datetime.now(), sig), flush=True)
    unit_mult_sig=unit_mult[((unit_mult['signal']==sig) & (unit_mult['remap'].isnull())) | (unit_mult['remap']==sig)].reset_index(drop=True)
    #Filter only relevent signal (using the units)
    all_df_sig=all_df.set_index(['signal', 'unit']).join(unit_mult_sig.set_index(['signal', 'unit']), how='inner').reset_index()
    sig_map_s=sig_map[sig_map['Map_to']==sig].reset_index(drop=True).rename(columns={'loinc_num': 'source', 'Optional_val_channel':'val_channel'})[['source','val_channel']]
    #all_df_sig: ['pid', 'signal', 'date', 'val', 'val_txt', 'unit', 'source'])

    all_df_sig = process_sig(all_df_sig)
    print('%s :: Filtered %d due to non numeric text results, size was %d'%(datetime.now(), len(all_df_sig[all_df_sig['val']!=all_df_sig['val_conv']]), len(all_df_sig)), flush=True)
    all_df_sig=all_df_sig[all_df_sig['val']==all_df_sig['val_conv']][['pid', 'signal', 'date', 'val', 'unit', 'source']].reset_index(drop=True)
    out_range=len(all_df_sig[all_df_sig['val']<min_th])
    print('%s :: has %d(%2.4f%%) records below %f - removing for %s'%(datetime.now(), out_range, out_range/(len(all_df_sig)*100.0), min_th, sig), flush=True)
    all_df_sig=all_df_sig[all_df_sig['val']>=min_th].reset_index(drop=True)
    #keep only relevant signals and units for signal:
    all_df_sig.loc[all_df_sig['signal']!=sig, 'unit'] = all_df_sig.loc[all_df_sig['signal']!=sig, 'signal'] + ':' + all_df_sig.loc[all_df_sig['signal']!=sig, 'unit']
    all_df_sig['signal']=sig #overwrite - all are this signal
    #fix unit_multi:
    unit_mult_sig.loc[unit_mult_sig['signal']!=sig,'unit']= unit_mult_sig.loc[unit_mult_sig['signal']!=sig,'signal'] + ':' + unit_mult_sig.loc[unit_mult_sig['signal']!=sig,'unit']
    unit_mult_sig['signal']=sig
    #Handle multi channle
    if len(sig_map_s[sig_map_s['val_channel'].notnull()])>0:
        print('Signal has multiple channels based on source data code', flush=True)
        all_df_sig = all_df_sig.set_index('source').join(sig_map_s.set_index('source'), how='left').reset_index()
        all_df_sig.loc[ all_df_sig['val_channel'].isnull() ,'val_channel']=0
        max_ch=int(all_df_sig['val_channel'].max())
        print('Has %d channels'%(max_ch+1), flush=True)
        for i in range(1, max_ch+1):
            #all_df_sig['value%d'%(i+1)]=-1
            new_ch=all_df_sig[all_df_sig['val_channel']==i][['pid', 'date', 'val', 'unit', 'source']].reset_index(drop=True).copy().rename(columns={ 'unit': 'unit_%d'%(i+1), 'source': 'source_%d'%(i+1), 'val': 'value%d'%(i+1) })
            all_df_sig=all_df_sig[all_df_sig['val_channel']!=i].reset_index(drop=True)
            all_df_sig=all_df_sig.set_index(['pid', 'date']).join(new_ch.set_index(['pid', 'date']), how='left').reset_index()
            all_df_sig.loc[ all_df_sig['value%d'%(i+1)].isnull() ,'value%d'%(i+1)]=-1
            print('Added %s'%('value%d'%(i+1)), flush=True)

        vals = all_df_sig[['pid', 'date', 'val', 'value2', 'unit', 'source']].rename(columns={'pid': 'orig_pid', 'date':'date1', 'val': 'value'}).drop_duplicates().reset_index(drop=True).sort_values(['orig_pid', 'date1'])
    else:
    
    #vals with cols:['orig_pid', 'date1', 'value', 'source', 'unit'] //'value2' if has more value channel
    
        vals = all_df_sig[['pid', 'date', 'val', 'unit', 'source']].rename(columns={'pid': 'orig_pid', 'date':'date1', 'val': 'value'}).drop_duplicates().reset_index(drop=True).sort_values(['orig_pid', 'date1'])
    handle_batch(vals, None, sig, '', None, unit_mult_sig, [], batch, all_errors, out_folder, None)


def load_labs_categorical(cfg):
    categ_df=pd.read_csv(os.path.join(cfg.code_dir, 'configs', 'categorical_signals.list'), names=['signal']).drop_duplicates().reset_index(drop=True)
    sigs=list(categ_df['signal'])
    all_df = read_sig_from_pre(cfg, sigs[0], sigs)
    out_folder=os.path.join(cfg.work_dir, 'FinalSignals', 'BeforeFilter')
    for sig in sigs:
        df=all_df[(all_df['signal']==sig) & (all_df['val_txt'].notnull())].reset_index(drop=True).copy()
        df['val_conv']=pd.to_numeric(df['val_txt'], errors='coerce')
        #Remove numeric values!
        df=df[df['val_conv']!=df['val']].reset_index(drop=True)
        #change name
        new_name='%s.Categorical'%(sig)
        df['signal']=new_name
        #['pid', 'signal', 'date', 'val', 'val_txt', 'unit', 'source']) => use pid, signal, date, val_txt - store
        df[['pid', 'signal', 'date', 'val_txt']].drop_duplicates().sort_values(['pid', 'date']).reset_index(drop=True).to_csv(os.path.join(out_folder, '%s'%(new_name)) , sep='\t', header=False, index=False)
        print('Wrote %s file'%(new_name), flush=True)

def get_comp_labs(cfg):
    log_f=os.path.join(cfg.work_dir, 'outputs', 'completed_labs.txt')
    if not(os.path.exists(log_f)):
        return set()
    fr=open(log_f, 'r')
    lines=fr.readlines()
    fr.close()
    done=list(filter(lambda x: len(x)>0 ,list(map(lambda x: x.strip(),lines))))
    return set(done)

def add_comp_lab(cfg, sig):
    log_f=os.path.join(cfg.work_dir, 'outputs', 'completed_labs.txt')
    fw=open(log_f,'a')
    fw.write(sig+'\n')
    fw.close()

def load_labs(cfg, batch_size=1):
    sig_map=pd.read_csv(os.path.join(cfg.code_dir, 'configs', 'map.tsv'), sep='\t')
    unit_mult = pd.read_csv(os.path.join(cfg.code_dir, 'configs', 'unitTranslator.txt'),
                names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf', 'remap'], header=0, sep='\t')
    unit_mult['unit'] = unit_mult['unit'].str.lower().str.strip()
    unit_mult.drop_duplicates(inplace=True)
    unit_mult.loc[unit_mult['rndf'].isnull(), 'rndf'] = unit_mult[unit_mult['rndf'].isnull()]['rnd']
    out_folder=os.path.join(cfg.work_dir, 'FinalSignals', 'BeforeFilter')
    #filter signals without unit_mult
    sig_map=sig_map[sig_map['Map_to'].isin(unit_mult['signal'])].reset_index(drop=True)
    #filter loaded sigs
    loaded=get_comp_labs(cfg)
    before_cnt=sig_map['Map_to'].nunique()
    sig_map=sig_map[~sig_map['Map_to'].isin(loaded)].reset_index(drop=True)
    lab_sigs=list(sig_map['Map_to'].copy().drop_duplicates())
    print('Has %d signals, prepared %d, remained %d'%(before_cnt, len(loaded), len(lab_sigs)),flush=True)
    if batch_size <=0:
        batch_size=len(lab_sigs)
    file_bt_size=10
    tot_files=100
    for batch_idx in range(0,len(lab_sigs), batch_size):
        fetch_sigs=lab_sigs[batch_idx:batch_idx+batch_size]
        sig=fetch_sigs[0]
        input_sigs=unit_mult[(unit_mult['remap'].isin(fetch_sigs)) | ((unit_mult['signal'].isin(fetch_sigs)) & (unit_mult['remap'].isnull()))]['signal'].copy().drop_duplicates()
        #First time
        load_batch=1
        if sig=='BP':
            file_bt_size=10
        else:
            file_bt_size=100
            load_batch=None
        for batch_start_index in range(0, tot_files ,file_bt_size):
            all_df = read_sig_from_pre(cfg, sig, input_sigs, 0, [batch_start_index ,batch_start_index+file_bt_size])
            all_df.loc[all_df['unit'].isnull(), 'unit']='<NULL>'
            all_df['unit'] = all_df['unit'].str.lower().str.strip()
            for sig in fetch_sigs:
                load_single_lab_from_mem(cfg, all_df, sig, unit_mult, sig_map, 0 ,load_batch)
            if load_batch is not None:
                load_batch=load_batch+1
            del all_df
        
        for s in fetch_sigs:
            add_comp_lab(cfg,s)

def process_sig(all_df):
    #when no value at all - filter
    all_df=all_df[(all_df['val_txt'].notnull()) | (all_df['val'].notnull())].reset_index(drop=True)
    #if val_txt is null but has value in val => copy from val to val_txt. Now val_txt is never null
    all_df.loc[all_df['val_txt'].isnull(), 'val_txt']=all_df.loc[all_df['val_txt'].isnull(), 'val']
    all_df['val_conv']=pd.to_numeric(all_df['val_txt'], errors='coerce')
    #if val is null but has value in val_conv => copy from val_conv to val before compare - to use more values
    all_df.loc[all_df['val'].isnull(), 'val']=all_df.loc[all_df['val'].isnull(), 'val_conv']
    all_df.loc[all_df['unit'].isnull(), 'unit']='<null>'
    if len(all_df) > 0:
        signal=all_df['signal'].iloc[0]
        if signal.endswith('%'):
            print('Process - try to convert %',flush=True)
            all_df.loc[(all_df['val_conv'].isnull()) & (all_df['val_txt'].str.endswith('%')), 'unit']='%'
            all_df.loc[(all_df['val_conv'].isnull()) & (all_df['val_txt'].str.endswith('%')), 'val_conv']=pd.to_numeric( all_df.loc[(all_df['val_conv'].isnull()) & (all_df['val_txt'].str.endswith('%')), 'val_txt'].apply(lambda s: s.rstrip('%')) , errors='coerce')
        if signal=='BP':
            print('Special case of BP!!')
            #Convert 'val_txt' patterns of Num1/Num1 
            potential_data=all_df[all_df['val_txt'].str.match('^[0-9]+/[0-9]+$')].reset_index(drop=True).copy()
            all_df=all_df[~all_df['val_txt'].str.match('^[0-9]+/[0-9]+$')].reset_index(drop=True)
            potential_data['signal']='BP'
            potential_data['unit']='mmHg'
            #split potential_data into 2 for each channel and stack into all_df:
            ch_1 = potential_data['val_txt'].apply(lambda x: int(x.split('/')[0]))
            ch_2 = potential_data['val_txt'].apply(lambda x: int(x.split('/')[1]))
            potential_data=potential_data[['pid', 'signal', 'date', 'unit']]
            potential_data['val']=ch_1
            potential_data['val_conv']=ch_1
            potential_data['source']='8480-6'
            all_df=all_df.append(potential_data, ignore_index=True)
            potential_data=potential_data[['pid', 'signal', 'date', 'unit']].copy()
            potential_data['val']=ch_2
            potential_data['val_conv']=ch_2
            potential_data['source']='8462-4'
            all_df=all_df.append(potential_data, ignore_index=True)


    return all_df

def read_sig_from_pre(cfg, sig, input_sigs=None, random_sample=0, partial_pos=None):
    bs = os.path.join(cfg.work_dir, 'PreSignals')
    files=sorted(filter(lambda x: x.startswith('LABS.'),os.listdir(bs)), key=lambda x: int(x.split('.')[1]))
    if random_sample > 0:
        random.shuffle(files)
        files=files[:random_sample]
    if partial_pos is not None:
        if partial_pos[1] is not None:
            files=files[partial_pos[0]:partial_pos[1]]
        else:
            files=files[partial_pos[0]:]

    all_df=None
    filter_set=None
    if input_sigs is not None and len(input_sigs) > 0:
        filter_set=set(input_sigs)
        filter_set.add(sig)
    for file in files:
        full_path=os.path.join(bs, file)
        print('%s :: Reading %s'%(datetime.now(),full_path), flush=True)
        df=pd.read_csv(full_path, sep='\t', header=None, names=['pid', 'signal', 'date', 'val', 'val_txt', 'unit', 'source'])
        if sig is not None or filter_set is not None:
            if filter_set is not None:
                df=df[df['signal'].isin(filter_set)].reset_index(drop=True)
            else:
                df=df[df['signal']==sig].reset_index(drop=True)
        if all_df is None:
            all_df=df
        else:
            all_df=all_df.append(df, ignore_index=True)
    del df
    return all_df


def preprocess_labs(cfg):
    sig_map=pd.read_csv(os.path.join(cfg.code_dir, 'configs', 'map.tsv'), sep='\t')
    used_codes=sig_map['loinc_num'].copy().drop_duplicates()
    final_sig_folder=os.path.join(cfg.work_dir, 'PreSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'loinc_test_id', 'loinc_category_id', 'std_uom', 'std_value', 'std_value_txt', 'std_report_status', 'std_value_status', 'encounter_record_id_hash', 'encounter_join_id', 'observation_date', 'std_observation_high_ref', 'std_observation_low_ref']
    sig_map.rename(columns={'loinc_num': 'loinc_test_id', 'Map_to': 'signal'}, inplace=True)
    batch_size=int(5e7)
    #minimal_take_cols=['pid', 'observation_date', 'update_date', 'loinc_test_id', 'loinc_category_id', 'std_uom', 'std_value', 'std_value_txt', 'std_report_status']
    minimal_take_cols=['pid', 'observation_date', 'loinc_test_id', 'std_uom', 'std_value', 'std_value_txt']
    data=read_table_united(cfg.data_dir, 'v_observation', columns = data_headers, write_batch=batch_size, _use_cols=minimal_take_cols, output_path_prefix= os.path.join(final_sig_folder, 'LABS'),
            process_function=lambda data:  proc_labs(data, sig_map, used_codes) )
    #data=data.set_index('loinc_test_id').join(sig_map.set_index('loinc_test_id'), on='loinc_test_id').reset_index()
    #data=data[['pid', 'signal', 'observation_date', 'std_value', 'std_value_txt', 'std_uom', 'loinc_test_id']].drop_duplicates()
    #all_sigs =data['signal'].copy().drop_duplicates()
    #for sig in all_sigs:
    #    data[data['signal']==sig].reset_index(drop=True).sort_values(['signal', 'pid', 'observation_date'], inplace=True).to_csv(os.path.join(final_sig_folder, sig), sep ='\t', index=False, header=False)
    return data

def strip_dict_code(s):
    s=s.replace(' ', '_').replace("'",'').replace('"','')
    return s

def proc_encounter(data):
    data=data.drop_duplicates().reset_index(drop=True)
    data['encounter_date']=data['encounter_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='ENCOUNTER'
    data.loc[(data['std_encounter_type'].isnull()) | (data['std_encounter_type']==''), 'std_encounter_type'] = 'UNKNOWN_EMPTY'
    data=data[['pid', 'signal', 'encounter_date', 'std_encounter_type']].drop_duplicates().reset_index(drop=True)
    data=data.sort_values(['pid', 'encounter_date'])
    return data

def proc_drug(data):
    data=data.drop_duplicates().reset_index(drop=True)
    data=data[data['std_order_status']!='ERRONEOUS'].reset_index(drop=True)
    data.loc[(data['start_date'].isnull()) | (data['start_date']==''), 'start_date'] = data.loc[(data['start_date'].isnull()) | (data['start_date']==''), 'prescription_date']
    data=data[(data['start_date'].notnull()) & (data['start_date']!='')].reset_index(drop=True)
    data.loc[(data['end_date'].isnull()) | (data['end_date']==''), 'end_date'] = data.loc[(data['end_date'].isnull()) | (data['end_date']==''), 'start_date']
    data['start_date']=data['start_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['end_date']=data['end_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='Drug'
    data.loc[(data['std_ordering_mode'].isnull()) | (data['std_ordering_mode']==''),'std_ordering_mode']='UNKNOWN:ORDERING_MODE'
    data.loc[(data['std_order_status'].isnull()) | (data['std_order_status']==''),'std_order_status']='UNKNOWN:ORDER_STATUS'
    #data.loc[(data['std_dosage'].isnull()) | (data['std_dosage']==''),'std_dosage']='UNKNOWN:DOSAGE'
    #data['std_dosage']=data['std_dosage'].apply(lambda x: x.strip().replace(' ','_').replace(',','_'))
    data.loc[(data['std_quantity'].isnull()),'std_quantity']=0
    #has info in std_drug_desc, but most of it, is junk, like "unkowon", "multi-vatimins", "override in admission"
    data=data[data['rx_cui'].notnull()].reset_index(drop=True)
    data['rx_cui']=data['rx_cui'].astype(int).astype('str').apply(lambda x: 'RX_CODE:' + x)
    #breakpoint()
    data=data[['pid', 'signal', 'start_date', 'end_date', 'rx_cui', 'std_ordering_mode', 'std_order_status', 'std_quantity']].drop_duplicates().sort_values(['pid', 'start_date']).reset_index(drop=True)
    return data

def proc_procedures(data):
    data=data.drop_duplicates().reset_index(drop=True)
    data=data[data['std_order_status']!='ERRONEOUS'].reset_index(drop=True)
    data['procedure_date']=data['procedure_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='PROCEDURE'
    data.loc[(data['icd_code'].isnull()) | (data['icd_code']==''), 'icd_code'] = 'ICD_UNKNOWN_EMPTY'
    data.icd_code=data.icd_code.astype(str)
    #breakpoint()
    data.loc[data['icd_code']!='ICD_UNKNOWN_EMPTY' ,'icd_code']=data.loc[ data['icd_code']!='ICD_UNKNOWN_EMPTY','icd_version'] + ':' + data.loc[data['icd_code']!='ICD_UNKNOWN_EMPTY', 'icd_code'].apply(lambda x: x.strip().replace('.','').replace(' ', '_').replace(',', '_'))
    data.loc[(data['cpt_concept'].isnull()) | (data['cpt_concept']==''), 'cpt_concept'] = 'CPT_UNKNOWN_EMPTY'
    data.loc[data['cpt_concept']!='CPT_UNKNOWN_EMPTY' ,'cpt_concept']= 'CPT_CODE:' + data.loc[data['cpt_concept']!='CPT_UNKNOWN_EMPTY' ,'cpt_concept']
    data.loc[(data['std_order_status'].isnull()) | (data['std_order_status']==''), 'std_order_status']= 'STATUS_UNKNOWN_EMPTY'

    data_primary=data[data['is_principal']=='t'][['pid', 'signal', 'procedure_date', 'icd_code', 'cpt_concept', 'std_order_status']].drop_duplicates().reset_index(drop=True).copy()
    data_primary['signal']='PROCEDURE_PRIMARY'
    data_icd=data[data['icd_code']!='ICD_UNKNOWN_EMPTY'][['pid', 'signal', 'procedure_date', 'icd_code', 'std_order_status']].drop_duplicates().reset_index(drop=True).copy().rename(columns={'icd_code': 'procedure_code'})
    data_cpt=data[data['cpt_concept']!='CPT_UNKNOWN_EMPTY'][['pid', 'signal', 'procedure_date', 'cpt_concept', 'std_order_status']].drop_duplicates().reset_index(drop=True).copy().rename(columns={'cpt_concept': 'procedure_code'})
    data=data_icd.append(data_cpt, ignore_index=True)
    data_primary_icd=data_primary[data_primary['icd_code']!='ICD_UNKNOWN_EMPTY'][['pid', 'signal', 'procedure_date', 'icd_code', 'std_order_status']].drop_duplicates().reset_index(drop=True).copy().rename(columns={'icd_code': 'procedure_code'})
    data_primary_cpt=data_primary[data_primary['cpt_concept']!='CPT_UNKNOWN_EMPTY'][['pid', 'signal', 'procedure_date', 'cpt_concept', 'std_order_status']].drop_duplicates().reset_index(drop=True).copy().rename(columns={'cpt_concept': 'procedure_code'})
    data_primary=data_primary_icd.append(data_primary_cpt, ignore_index=True)

    data=data.sort_values(['pid', 'procedure_date'])
    data_primary=data_primary.sort_values(['pid', 'procedure_date'])
    #Add PRIMARY_DIAGNOSIS by querying is_principal column
    data=data.append(data_primary, ignore_index=True)
    return data

def proc_problem_list(data):
    data=data.drop_duplicates().reset_index(drop=True)
    data.loc[data['diagnosis_start_date'].isnull(), 'diagnosis_start_date']= '1900-01-01 00:00:00'
    #breakpoint()
    data['diagnosis_start_date']=data['diagnosis_start_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='DIAGNOSIS'
    data['source']='PROBLEM_LIST'
    data['icd_code']=data['icd_version'] + ':' + data['icd_code'].apply(lambda x: x.strip().replace('.','').replace(' ', '_').replace(',', '_'))
    data=data[['pid', 'signal', 'diagnosis_start_date', 'icd_code', 'source']].drop_duplicates().reset_index(drop=True)
    data=data.sort_values(['pid', 'diagnosis_start_date'])
    return data

def proc_medical_history(data):
    data=data.drop_duplicates().reset_index(drop=True)
    data['std_medial_history_date']=data['std_medial_history_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='DIAGNOSIS'
    data['icd_code']=data['icd_version'] + ':' + data['icd_code'].apply(lambda x: x.strip().replace('.','').replace(' ', '_').replace(',', '_'))
    data['source']='MEDICAL_HISTORY'
    data=data[['pid', 'signal', 'std_medial_history_date', 'icd_code', 'source']].drop_duplicates().reset_index(drop=True)
    data=data.sort_values(['pid', 'std_medial_history_date'])

    return data

def proc_admission(data):
    data=data.drop_duplicates().reset_index(drop=True)
    #print(data.head())
    data['admission_date']=data['admission_date'].apply(lambda x: x.split()[0].replace('-',''))
    data.loc[data['discharge_date'].isnull(), 'discharge_date']= data.loc[data['discharge_date'].isnull(), 'admission_date']
    data['discharge_date']=data['discharge_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='ADMISSION'
    data.loc[(data['std_admission_type'].isnull()) | (data['std_admission_type']==''), 'std_admission_type'] = 'UNKNOWN_EMPTY'
    data['std_admission_type']=data['std_admission_type'].apply(strip_dict_code)
    data=data[['pid', 'signal', 'admission_date', 'discharge_date', 'std_admission_type']].drop_duplicates().reset_index(drop=True)
    #data['admission_date']= = pd.to_numeric(data['admission_date'], errors='coerce')
    #data=data[~data['admission_date'].isnull()].reset_index(drop=True)
    data=data.sort_values(['pid', 'admission_date'])
    return data

def proc_diagnosis(data):
    data=data.drop_duplicates().reset_index(drop=True)
    data['diagnosis_date']=data['diagnosis_date'].apply(lambda x: x.split()[0].replace('-',''))
    data['signal']='DIAGNOSIS'
    data['icd_code']=data['icd_version'] + ':' + data['icd_code'].apply(lambda x: x.strip().replace('.','').replace(' ', '_').replace(',', '_'))
    data['source']='DIAGNOSIS'
    data=data[['pid', 'signal', 'diagnosis_date', 'icd_code', 'source']].drop_duplicates().reset_index(drop=True)
    data=data.sort_values(['pid', 'diagnosis_date'])
    return data

def proc_labs(data, sig_map, used_codes):
    data=data[data['loinc_test_id'].isin(used_codes)].drop_duplicates()
    data=data.set_index('loinc_test_id').join(sig_map.set_index('loinc_test_id'), on='loinc_test_id').reset_index().reset_index(drop=True)
    data['observation_date']=data['observation_date'].apply(lambda x: x.split()[0].replace('-',''))
    data=data[['pid', 'signal', 'observation_date', 'std_value', 'std_value_txt', 'std_uom', 'loinc_test_id']].drop_duplicates()
    data=data.reset_index(drop=True).sort_values(['signal', 'pid', 'observation_date'])
    #all_sigs =data['signal'].copy().drop_duplicates()
    return data


def load_habit(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    os.makedirs(final_sig_folder, exist_ok=True)
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'update_date', 'answer', 'encounter_hash_id', 'encounter_join_id', 'date']
    batch_size=0
    res=read_table_united(cfg.data_dir, 'v_habit', columns = data_headers, write_batch=batch_size, process_function=lambda data: data[['pid', 'id2', 'id3', 'rowid', 'source', 'status', 'answer', 'date', 'update_date']].drop_duplicates())

    print('Remove empty answers', flush=True)
    res=res[res['answer'].notnull()].reset_index(drop=True)
    print('rename passive value', flush=True)
    res.answer = res.answer.map(lambda x: 'tobacco_passive:no' if x=='tobacco_passive_no' else x )
    print('split column', flush=True)
    res[['signal','value']] = res.answer.str.split("_", expand=True)

    print('change name of signal', flush=True)
    res.signal = res.signal.map( {'tobacco': 'SMOKING_STATUS', 'alcohol': 'ALCOHOL_STATUS'} )
    print('convert date', flush=True)
    res.date = res.date.apply(lambda x : int(x.split()[0].replace('-','')))
    print('sorting', flush=True)
    res.sort_values(['signal', 'pid', 'date'], inplace=True)

    res[res['signal']=='SMOKING_STATUS'][['pid', 'signal', 'date', 'value']].drop_duplicates().reset_index(drop=True).to_csv(os.path.join(final_sig_folder, 'SMOKING_STATUS'), sep ='\t', index=False, header=False)
    print('Wrote SMOKING_STATUS', flush=True)
    res[res['signal']=='ALCOHOL_STATUS'][['pid', 'signal', 'date', 'value']].drop_duplicates().reset_index(drop=True).to_csv(os.path.join(final_sig_folder, 'ALCOHOL_STATUS'), sep ='\t', index=False, header=False)
    print('Wrote ALCOHOL_STATUS', flush=True)

    return res


def load_demographic(cfg):
    final_sig_folder=os.path.join(cfg.work_dir, 'FinalSignals')
    data_headers=['pid', 'source_system_type', 'source_connection_type', 'rowid', 'data_grid_date_updated', 'sex', 'byear', 'is_deceased', 'patient_state', 'std_insurance_type', 'std_race', 'age_in_weeks_for_age_under_2_years', 'age_in_months_for_age_under_8_years']
    #batch_size=int(1e7)
    batch_size=0
    #byear, gender, payer
    #skip: membership, state
    res=read_table_united(cfg.data_dir, 'v_demographic', columns = data_headers, write_batch=batch_size, process_function=flat_demo)
    res=process_demo(res)
    res[res['signal']=='GENDER'].reset_index(drop=True).to_csv(os.path.join(final_sig_folder, 'GENDER'), sep ='\t', index=False, header=False)
    res[res['signal']=='BYEAR'].reset_index(drop=True).to_csv(os.path.join(final_sig_folder, 'BYEAR'), sep ='\t', index=False, header=False)
    res[res['signal']=='BDATE'].reset_index(drop=True).to_csv(os.path.join(final_sig_folder, 'BDATE'), sep ='\t', index=False, header=False)

    return res
   
def flat_demo(data):
    data=data[['pid', 'byear', 'sex']][data['byear'].notnull()].reset_index(drop=True).drop_duplicates()
    return data

    #process demographic dataframe into load dataframe
def process_demo(data):
    res=data[data['byear'].notnull()][['pid', 'byear']].groupby('pid').agg(['min', 'max']).reset_index()
    inconsistent_byear=res[res[('byear', 'min')]!= res[('byear', 'max')]]['pid']
    print('Has %d mismatch byears'%(len(inconsistent_byear)), flush=True)
    data = data[~data['pid'].isin(inconsistent_byear)].reset_index(drop=True)
    res=data[['pid', 'sex']].groupby('pid').nunique().reset_index()
    inconsistent_sex=res[res['sex']>1]
    print('Has %d mismatch sex'%(len(inconsistent_sex)), flush=True)
    data = data[~data['pid'].isin(inconsistent_sex)].reset_index(drop=True)
    print('Remove unknown gender %d'%(len(data[data['sex']<=0])), flush=True)
    data=data[data['sex']>0].reset_index(drop=True)
    #print(data.head())
    #preprocess data
    #end preprocess
    gender_df=data[['pid', 'sex']].copy()
    gender_df['signal'] = 'GENDER'
    gender_df= gender_df[['pid', 'signal', 'sex']]
    gender_df.rename(columns= {'sex': 'value'}, inplace=True)
    gender_df['value']=gender_df['value'].astype(int)
    #payer_df=data[['pid', 'payer']].copy()
    #payer_df['signal'] = 'PAYER'
    #payer_df= payer_df[['pid', 'signal', 'payer']]
    #payer_df.rename(columns= {'payer': 'value'}, inplace=True)
    byear_df=data[['pid', 'byear']].copy()
    byear_df['signal'] = 'BYEAR'
    byear_df= byear_df[['pid', 'signal', 'byear']]
    byear_df.rename(columns= {'byear': 'value'}, inplace=True)
    byear_df['value'] = pd.to_numeric(byear_df['value'], errors='coerce')
    byear_df=byear_df[byear_df['value'].notnull()]
    byear_df['value']=byear_df['value'].astype(int)

    bdate_df=byear_df.copy()
    bdate_df['signal'] ='BDATE'
    bdate_df['value'] = pd.to_numeric(bdate_df['value'], errors='coerce')
    bdate_df=bdate_df[bdate_df['value'].notnull()]
    bdate_df['value'] = bdate_df['value']*10000+101
    final_df=gender_df
    #final_df=final_df.append(payer_df, ignore_index=True)
    final_df=final_df.append(byear_df, ignore_index=True)
    final_df=final_df.append(bdate_df, ignore_index=True)
    final_df.sort_values(['signal', 'pid'], inplace=True)
    #print(byear_df['value'].head())
    #print (final_df[final_df['signal']=='BYEAR'].head())
    return final_df
       
if __name__ == '__main__':
    cfg=Configuration()
    #load_demographic(cfg)
    #load_habit(cfg)
    #preprocess_labs(cfg)
    #load_diagnosis(cfg)
    #load_admissions(cfg)
    #load_encounters(cfg)
    #load_medial_hostory(cfg)
    #load_problem_list(cfg)
    #load_procedures(cfg)
    load_labs_categorical(cfg)
