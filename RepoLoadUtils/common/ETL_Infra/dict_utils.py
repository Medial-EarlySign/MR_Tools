import os,re
import pandas as pd
import numpy as np
from .env import FULL_SIGNALS_TYPES,BASE_DICT_PATH
from .define_signals import load_signals_map
from .build_config_file import create_convert_config_file
from .env import *

#generate_dict_from_codes - to add client specific codes dicts - "DEF" foir signal
#add_hirarchy- to add client specific SET dicts for signal
#process_dicts - generate dicts from global dicts
#get_dicts_done_signals - done signals
#load_final_sig - laod specific signal from FinalSignals
#finish_prepare_dicts - prepare rest of dicts
#finish_prepare_load - finish dicts, generate signal+convert_config+flow

def fix_def_dict(dict_path, out_dict_path, signal):
    dict_header=['DEF', 'ID', 'VALUE']
    dict_df=pd.read_csv(dict_path, sep='\t', names=dict_header)
    #Add header SECTION and store file
    header='SECTION\t%s\n'%(signal)
    if os.path.exists(out_dict_path):
        if_file=open(out_dict_path, 'r')
        header=if_file.readline()
        if_file.close()
        sigs=header.split('\t')[1]
        ss=set(list(map(lambda x:x.strip(),sigs.split(','))))
        ss=ss.union(set(signal.split(',')))
        sigs=','.join(list(ss))
        header='SECTION\t%s\n'%(sigs)
    of_file=open(out_dict_path, 'w')
    of_file.write(header)
    dict_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()
    return dict_df

def fix_set_dict(dict_path, out_dict_path, signal):
    dict_header=['SET', 'PARENT', 'CHILD']
    dict_df=pd.read_csv(dict_path, sep='\t', names=dict_header)
    if os.path.exists(out_dict_path):
        if_file=open(out_dict_path, 'r')
        header=if_file.readline()
        if_file.close()
        sigs=header.split('\t')[1]
        ss=set(list(map(lambda x:x.strip(),sigs.split(','))))
        ss=ss.union(set(signal.split(',')))
        sigs=','.join(list(ss))
        header='SECTION\t%s\n'%(sigs)
    
    header='SECTION\t%s\n'%(signal)
    of_file=open(out_dict_path, 'w')
    of_file.write(header)
    dict_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()
    return dict_df

def sort_by_name(x):
    num_reg=re.compile('[0-9]+')
    arr=x.split('.')
    if len(arr)<2:
        return 0
    else:
        x=arr[1]
        if num_reg.match(x) is not None:
            return int(x)
        else:
            return 0

def get_dicts(desired_ontologies):
    ont_to_dict_path=dict()
    ont_to_set_path=dict()
    ont_to_dict_path['ICD9DX']=os.path.join(BASE_DICT_PATH, 'ICD9', 'dict.icd9dx')
    ont_to_set_path['ICD9DX']=os.path.join(BASE_DICT_PATH, 'ICD9', 'dict.set_icd9dx')
    ont_to_dict_path['ICD9PC']=os.path.join(BASE_DICT_PATH, 'ICD9', 'dict.icd9sg')
    ont_to_set_path['ICD9PC']=os.path.join(BASE_DICT_PATH, 'ICD9', 'dict.set_icd9sg')
    ont_to_dict_path['ICD10DX']=os.path.join(BASE_DICT_PATH, 'ICD10', 'dict.icd10')
    ont_to_set_path['ICD10DX']=os.path.join(BASE_DICT_PATH, 'ICD10', 'dict.set_icd10')
    ont_to_dict_path['ICD10PC']=os.path.join(BASE_DICT_PATH, 'ICD10', 'dict.icd10pcs')
    ont_to_set_path['ICD10PC']=os.path.join(BASE_DICT_PATH, 'ICD10', 'dict.set_icd10pcs')
    
    ont_to_set_path['ICD9DX_TO_ICD10DX']=os.path.join(BASE_DICT_PATH, 'ICD9_TO_ICD10', 'dict.set_icd9_2_icd10')
    ont_to_set_path['ICD10DX_TO_ICD9DX']=os.path.join(BASE_DICT_PATH, 'ICD10_TO_ICD9', 'dict.set_icd10_2_icd9')
    
    ont_to_dict_path['ATC']=os.path.join(BASE_DICT_PATH, 'ATC', 'dict.defs_atc')
    ont_to_set_path['ATC']=os.path.join(BASE_DICT_PATH, 'ATC', 'dict.sets_atc')
    ont_to_dict_path['ATC_SYN']=os.path.join(BASE_DICT_PATH, 'ATC', 'dict.defs_atc_syn')
    ont_to_dict_path['RX']=os.path.join(BASE_DICT_PATH, 'RX', 'dict.defs_rx')
    ont_to_set_path['RX']=os.path.join(BASE_DICT_PATH, 'RX', 'dict.sets_atc_rx')
    ont_to_dict_path['NDC']=os.path.join(BASE_DICT_PATH, 'NDC', 'dict.ndc_defs')
    ont_to_set_path['NDC']=os.path.join(BASE_DICT_PATH, 'NDC', 'dict.atc_ndc_set')
    
    def_dicts=[]
    set_dicts=[]
    for ont in desired_ontologies:
        if ont not in ont_to_dict_path and ont not in ont_to_set_path:
            print('please select one of:\n%s'%('\n'.join(list(ont_to_dict_path.keys()))), flush=True)
            raise NameError(f'Unknown ontology {ont}')
        if ont in ont_to_dict_path:
            def_dicts = def_dicts + [ont_to_dict_path[ont]]
        if ont in ont_to_set_path:
            set_dicts = set_dicts + [ont_to_set_path[ont]]
        
    return def_dicts, set_dicts

def calc_ontologies(df, selected_cols, signal, sig_classes):
    prefix_to_desire=dict()
    prefix_to_desire['ATC']=['ATC']
    if 'atc_syn' in sig_classes:
        prefix_to_desire['ATC']=['ATC', 'ATC_SYN']
    prefix_to_desire['RX_CODE']=['RX', 'ATC']
    prefix_to_desire['NDC_CODE']=['NDC', 'ATC']
    
    is_diagnostic = True
    if signal=='PROCEDURE' or ('procedure' in sig_classes):
        prefix_to_desire['ICD10_CODE']=['ICD10PC']
        prefix_to_desire['ICD9_CODE']=['ICD9PC']
        is_diagnostic = False
    else: #DX
        prefix_to_desire['ICD10_CODE']=['ICD10DX']
        prefix_to_desire['ICD9_CODE']=['ICD9DX' ]
        is_diagnostic = (signal.lower() == "diagnosis") or ('icd9' in sig_classes or 'icd10' in sig_classes)
        #if has both icd9,icd10 add:
    
    desired_ontologies=[]
    has_9=False
    has_10=False
    for col in selected_cols:
        #test all vals with prefix "prefix:"
        prefix_vals=set(df[(df[col].notnull()) & (df[col].str.contains(':'))].reset_index(drop=True)[col].apply(lambda x: x[:x.find(':')]).values)
        for code_sys in prefix_vals:
            if code_sys not in prefix_to_desire:
                print(f'WARNING: coding system prefix {code_sys} is not recognized in signal {signal}', flush=True)
                continue
            desired_ontologies = desired_ontologies + prefix_to_desire[code_sys]
            if code_sys =='ICD10_CODE':
                has_10=True
            if code_sys =='ICD9_CODE':
                has_9=True
    
    if is_diagnostic and (has_10 or has_9): 
        if 'icd10' in sig_classes:
            desired_ontologies.append('ICD10DX_TO_ICD9DX')
            desired_ontologies.append('ICD10DX')
            if 'ICD9DX' not in desired_ontologies:
                desired_ontologies.append('ICD9DX')
            if 'ICD10DX' not in desired_ontologies:
                desired_ontologies.append('ICD10DX')
        elif 'icd9' in sig_classes: #like in lung
            desired_ontologies.append('ICD9DX_TO_ICD10DX')
            if 'ICD9DX' not in desired_ontologies:
                desired_ontologies.append('ICD9DX')
            if 'ICD10DX' not in desired_ontologies:
                desired_ontologies.append('ICD10DX')
        else:
            print('Has ICD10 or ICD9 but choosed not to add maping from one to the other', flush=True)
            
    desired_ontologies=list(set(desired_ontologies))
        
    return desired_ontologies

#df of data
#signal, data_files_prefix - name of signal (to create section), and name of data file prefix
#workdir - outputpath
def process_dicts(df, signal_types, signal, workdir, set_dict, add_missing_hir=True):
    existing_dict_folder=os.path.join(os.path.dirname(__file__), 'dicts')
    final_sig_folder=os.path.join(workdir, 'FinalSignals')
    os.makedirs(os.path.join(workdir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(workdir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    signal_ls=signal.split(',')
    if signal_ls[0] not in signal_types:
        raise NameError(f'signal {signal_ls[0]} is not defined signal')
    specific_client_dicts=os.path.join(out_dict, f'dict.defs_{signal_ls[0]}_Fromclient')
    
    
    set_col_name='INTERNAL_MES_code_system'
    #calc desired_ontologies:
    si = signal_types[signal_ls[0]]
    selected_cols=[]
    for i,ch in enumerate(si.v_categ):
        if ch == '1':
            selected_cols.append(f'value_{i}')
            
    desired_ontologies=calc_ontologies(df, selected_cols, signal_ls[0], si.classes)
    if set_dict is not None:
        desired_ontologies_target=calc_ontologies(set_dict, [set_dict.columns[0]], signal_ls[0], si.classes)
        desired_ontologies=list(set(desired_ontologies+desired_ontologies_target))
    def_dicts, set_dicts=get_dicts(desired_ontologies)
    #Load dict defs:
    dict_arr=[]
    for def_d in def_dicts:
        dname=os.path.basename(def_d)
        dict_arr.append( fix_def_dict(def_d, os.path.join(out_dict, dname), signal))

    for set_d in set_dicts:
        dname=os.path.basename(set_d)
        fix_set_dict(os.path.join(existing_dict_folder, set_d), os.path.join(out_dict, dname), signal)
    
    if os.path.exists(specific_client_dicts):
        additional_codes=pd.read_csv(specific_client_dicts, sep='\t', names=['DEF', 'ID', 'VALUE'], skiprows=1)
        dict_arr.append(additional_codes)

    #Create existing set:
    existing_cd=None
    max_code=None
    for df_d in dict_arr:
        if existing_cd is None:
            existing_cd=df_d[['VALUE']].copy().drop_duplicates().reset_index(drop=True)
            curr_m=df_d['ID'].max()
            if max_code is None or curr_m>max_code:
                max_code=curr_m
        else:
            existing_cd=pd.concat([existing_cd, df_d[['VALUE']].copy().drop_duplicates().reset_index(drop=True)], ignore_index=True)
            curr_m=df_d['ID'].max()
            if max_code is None or curr_m>max_code:
                max_code=curr_m
    if existing_cd is not None:
        existing_cd=existing_cd.drop_duplicates().reset_index(drop=True)
    else:
        existing_cd=pd.DataFrame({'VALUE':[]})

    #Iterate over categorical columns in df:
    
    all_codes=[]
    for i, col in enumerate(selected_cols):
        codes_in_col = df[df[col].notnull()][[col]].drop_duplicates().reset_index(drop=True)
        if set_dict is not None and i ==0: 
            codes_in_col = pd.concat([codes_in_col, set_dict.rename(columns={set_dict.columns[0]: col})[[col]] , 
            set_dict.rename(columns={set_dict.columns[1]: col})[[col]]],
             ignore_index=True).drop_duplicates(ignore_index=True)
        all_codes.append(codes_in_col)

    if max_code is None:
        max_code=0
    seen_set = set()
    for i, col_name in enumerate(selected_cols):
        all_cd_df=all_codes[i]
        all_cd_df[col_name]=all_cd_df[col_name].astype(str)
        missing_codes=all_cd_df[(~all_cd_df[col_name].isin(existing_cd['VALUE'])) & (~all_cd_df[col_name].isin(seen_set)) ].reset_index(drop=True).copy()
        missing_codes['def']='DEF'
        missing_codes=missing_codes.sort_values(col_name).reset_index(drop=True)
        missing_codes[set_col_name]=np.asarray(range(len(missing_codes)))+10000+max_code
        max_code=missing_codes[set_col_name].max()    
        missing_codes=missing_codes[['def', set_col_name, col_name]]
        seen_set = seen_set.union(set(all_cd_df[col_name].values))

        print('Have %d %s codes (%s), out of them %d is missing (%2.4f%%)'%( len(all_cd_df), signal_ls[0], col_name , len(missing_codes), float(100.0*len(missing_codes))/len(all_cd_df) ), flush=True)
        if len(missing_codes) > 0:
            add_s=''
            if len(all_codes)>1:
                add_s='_%s'%(col_name)
            of_file=open(os.path.join(out_dict, 'dict.def_%s%s'%(signal_ls[0], add_s)), 'w')
            of_file.write('SECTION\t%s\n'%(signal))
            missing_codes.to_csv(of_file, sep='\t', index=False, header=False)
            of_file.close()
        if len(missing_codes) and add_missing_hir:
            add_set_to_missing_parents(workdir, signal_types, signal)

def clear_str(s):
    return s.strip().replace('"', '_').replace(',', '_').replace(' ', '_')
#df has 2 columns from (first col),to(2nd col). generate dict that each code value has mapping to those 2 columns
def generate_dict_from_codes(df, workdir, signal_types, signal, sig_df, set_dict, dup_separator='_'):
    os.makedirs(os.path.join(workdir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(workdir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    
    #Use final signal - to see if it has some ontologies!
    signal_ls=signal.split(',')
    selected_cols=[]
    si = signal_types[signal_ls[0]]
    for i,ch in enumerate(si.v_categ):
        if ch =='1': #Categorial
            selected_cols.append(f'value_{i}')
    
    desired_ontologies=calc_ontologies(sig_df, selected_cols, signal_ls[0], si.classes)
    if set_dict is not None:
        desired_ontologies_target=calc_ontologies(set_dict, [set_dict.columns[0]], signal_ls[0], si.classes)
        desired_ontologies=list(set(desired_ontologies+desired_ontologies_target))
    def_dicts, set_dicts=get_dicts(desired_ontologies)
    
    max_code=None
    for df_d in def_dicts:
        df_d=pd.read_csv(df_d, sep='\t', names=['def', 'ID', 'code'], usecols=['ID'])
        curr_m=df_d['ID'].astype(int).max()
        if max_code is None or curr_m>max_code:
            max_code=curr_m
    if max_code is None:
        max_code=0
    min_code=max_code+10000
    
    NOT_USED_COL_NAME='mes_internal_counter_46437'
    CODE_COL_NOT_USED= 'CODE_COL_MES_476523'
    
    from_col=df.columns[0]
    to_col=df.columns[1]
    df[from_col] = df[from_col].astype(str).map(clear_str)
    sz=len(df)
    df=df[(df[from_col].notnull())& (df[from_col]!='')].reset_index(drop=True)
    if (len(df)< sz):
        print('Filtered nulls in %s map from %d => %d'%(from_col, len(df), sz), flush=True)
    sz=len(df)
    df=df.drop_duplicates(subset=[from_col]).reset_index(drop=True)
    if (len(df)< sz):
        print('Filtered duplicated map from %d => %d'%(len(df), sz), flush=True)
    sz=len(df)
    
    dict_df=pd.DataFrame({'value':df[from_col]})
    dict_df['def']='DEF'
    dict_df[CODE_COL_NOT_USED] = min_code + np.asarray(range(sz))
    dict_df=dict_df[['def', CODE_COL_NOT_USED, 'value']]
    #Now let's add aliases
    
    #Generate DEF with map of "codes" from and thier alias to_codes:
    df[to_col] = df[to_col].astype(str).map(clear_str)
    df=df[(df[to_col].notnull()) & (df[to_col]!='')].reset_index(drop=True)
    if (len(df)< sz):
        print('Filtered nulls in %s map from %d => %d'%(to_col, len(df), sz), flush=True)
    sz=len(df)
    #Let's transform the values to be uniq:
    df[NOT_USED_COL_NAME]= df.groupby(to_col).cumcount()
    df.loc[ df[NOT_USED_COL_NAME]>0 ,to_col] = df.loc[ df[NOT_USED_COL_NAME]>0 ,to_col] + dup_separator + (df.loc[ df[NOT_USED_COL_NAME]>0 , NOT_USED_COL_NAME]+1).astype(str)
    #For each duplication add counter in the end:
    df_jn=df.set_index(from_col).join(dict_df[[CODE_COL_NOT_USED, 'value']].rename(columns= {'value': from_col}).set_index(from_col), how= 'inner').reset_index()
    df_jn = df_jn[[CODE_COL_NOT_USED, to_col]]
    df_jn['def']= 'DEF'
    df_jn=df_jn[['def', CODE_COL_NOT_USED, to_col]].rename(columns={to_col : 'value'})
    sz=len(df_jn)
    df_jn=df_jn.drop_duplicates().reset_index(drop=True)
    if (len(df)< sz):
        print('Filtered duplicated in target map from %d => %d'%(len(df_jn), sz), flush=True)
    sz=len(df_jn)
    #concat
    dict_df=  pd.concat([dict_df, df_jn], ignore_index=True).sort_values(CODE_COL_NOT_USED).reset_index(drop=True)
    #store:
    outpath=os.path.join(out_dict, f'dict.defs_{signal_ls[0]}_Fromclient')
    of_file=open(outpath, 'w')
    of_file.write('SECTION\t%s\n'%(signal))
    dict_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()    
    print('Wrote %s'%(outpath), flush=True)

#add hirarchy dict using 2 columns dataframe from => to
def add_hirarchy(map_df, workdir, signal):
    os.makedirs(os.path.join(workdir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(workdir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    signal_ls=signal.split(',')
    
    from_col=map_df.columns[0]
    to_col=map_df.columns[1]
    map_df['SET']='SET'
    map_df=map_df[['SET', from_col, to_col]].drop_duplicates().reset_index(drop=True)
    
    output_full=os.path.join(out_dict, f'dict.sets_{signal_ls[0]}_Fromclient')
    of_file=open(output_full, 'w')
    of_file.write('SECTION\t%s\n'%(signal))
    map_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()
    
def get_dicts_done_signals(workdir):
    out_dict=os.path.join(workdir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    all_sigs=set()
    for f in os.listdir(out_dict):
        if f == '.ipynb_checkpoints':
            continue
        full_f=os.path.join(out_dict, f)
        fr=open(full_f,'r')
        header=fr.readline()
        fr.close()
        tmp, signals = header.split('\t')
        all_sigs=all_sigs.union(set(map(lambda x: x.strip(), signals.split(','))))
    return list(all_sigs)

def get_final_sig_list(workdir):
    final_sig=os.path.join(workdir, 'FinalSignals')
    load_files=list(filter(lambda x: x!='ID2NR' and x != '.ipynb_checkpoints', os.listdir(final_sig)))
    batch_re=re.compile(r'\.[0-9]+$')
    return list(set(map(lambda x: batch_re.sub('',x) ,load_files)))

def generate_static_dict(workdir, signal):
    static_dicts=['GENDER', 'Smoking_Status']
    if 'SEX' in FORCED_SIGNALS:
        static_dicts=['SEX', 'Smoking_Status']
    if signal not in static_dicts:
        return False

    os.makedirs(os.path.join(workdir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(workdir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    if signal=='Smoking_Status':
        dict_path=os.path.join(out_dict, 'dict.Smoking_Status')
        fw=open(dict_path, 'w')
        fw.write('SECTION\tSmoking_Status\n')
        fw.write('DEF\t0\tNever\n')
        fw.write('DEF\t1\tPassive\n')
        fw.write('DEF\t2\tFormer\n')
        fw.write('DEF\t3\tCurrent\n')
        fw.write('DEF\t4\tNever_or_Former\n')
        fw.write('DEF\t5\tUnknown\n')
        fw.close()
    if signal=='GENDER' or signal == 'SEX':
        dict_path=os.path.join(out_dict, 'dict.gender')
        fw=open(dict_path, 'w')
        fw.write('SECTION\t%s\n'%(signal))
        fw.write('DEF\t1\t1\n')
        fw.write('DEF\t2\t2\n')
        fw.write('DEF\t1\tMale\n')
        fw.write('DEF\t2\tFemale\n')
        fw.write('DEF\t1\tM\n')
        fw.write('DEF\t2\tF\n')
        fw.close()   
    
    return True

def load_categ_sig(workdir, sig_types, signal):
    categorical_stats=os.path.join(workdir, 'outputs', 'signal_categorical_stats')
    if not(os.path.exists(categorical_stats)):
        raise NameError('no stats for signal %s'%(signal))
    good_f=list(filter(lambda x: x.startswith(signal) ,os.listdir(categorical_stats)))
    
    by_col=dict()
    cols=set()
    for fn in good_f:
        full_f=os.path.join(categorical_stats, fn)
        df=pd.read_csv(full_f, sep='\t')
        col_n=df.columns[0]
        cols.add(col_n)
        df=df[[col_n]].astype(str)
        if col_n not in by_col:
            by_col[col_n]=[]
        by_col[col_n].append(df)       
    for col in cols:
        by_col[col]=pd.concat(by_col[col], ignore_index=True).drop_duplicates().reset_index(drop=True)[col]
    
    df=pd.DataFrame(by_col)
    
    return df

def load_final_sig(workdir, sig_types, signal):
    if signal not in sig_types:
        print(f'Error - can\'t locate signal {signal} in signal_types', flush=True)
        return None
    final_sig_dir=os.path.join(workdir, 'FinalSignals')
    all_files=os.listdir(final_sig_dir)
    relevant_files=list(filter(lambda x: x==signal or x.startswith(signal+'.') ,all_files))
    all_df=[]
    for f in relevant_files:
        all_df.append(pd.read_csv(os.path.join(final_sig_dir,f), sep='\t', header=None))
    df=pd.concat(all_df, ignore_index=True)
    col_names = ['pid', 'signal']
    
    si=sig_types[signal]
    for i in range(len(si.t_ch)):
        col_name='time_%d'%(i)
        col_names.append(col_name)
    for i in range(len(si.v_ch)):
        col_name='value_%d'%(i)
        col_names.append(col_name)
    if len(col_names) > len(df.columns):
        print(f'Error - bad format - expecting at least {len(col_names)} columns and has {len(df.columns)}', flush=True)
        return None
    mss_col=1
    while len(col_names) < len(df.columns):
        col_names.append('additional_%d'%(mss_col))
        mss_col=mss_col+1
    
    df.columns=col_names
    return df

def finish_signal_dict(workdir, signal_types, signal:str, set_dict=None):
    if signal not in signal_types:
            raise NameError(f'Error - signal {signal} is unknown type')
    si=signal_types[signal]
    if not(si.has_cetgorical()):
        return
    #prepare dict- check static
    if generate_static_dict(workdir, signal):
        return
    #prepare dict - assume no special dict - no static:
    df = load_categ_sig(workdir, signal_types, signal)
    process_dicts(df, signal_types, signal, workdir, set_dict)

def finish_prepare_dicts(workdir, signal_types, set_dict=None, override=False):
    done_sigs = []
    if not(override):
        done_sigs=get_dicts_done_signals(workdir)
    sigs=get_final_sig_list(workdir)
    
    for signal in sigs:
        if signal in done_sigs:
            continue
        finish_signal_dict(workdir, signal_types, signal, set_dict)

def parse_signals(lines, group_sigs, source_file):
    seen_name=set()
    seen_id=set()
    for line in lines:
        tokens=line.split('\t')
        if len(tokens)<5:
            raise NameError('Bad format in %s - not enough tokens in line:\n%s'%(source_file, line))
        sig_name=tokens[1].strip()
        sig_id=tokens[2].strip()
        sig_type=tokens[3].strip()
        sig_tags=tokens[4].strip()
        sig_categorical=''
        if len(tokens)>5:
            sig_categorical=tokens[5].strip()
        sig_units=''
        if len(tokens)>6:
            sig_units=tokens[6].strip()
        sig_time_unit=''
        if len(tokens)>7:
            sig_time_unit=tokens[7].strip()
        if sig_name in seen_name:
            raise NameError('Bad format in %s - signal %s was defined more than once'%(source_file, sig_name))
        if sig_id in seen_id:
            raise NameError('Bad format in %s - signal_id %s was defined more than once'%(source_file, sig_id))
        #Print by sig_tags
        if sig_tags not in group_sigs:
            group_sigs[sig_tags]=[]
        #Build dict from signal name to "tags" from group_sigs
        sig_name_to_tags=dict()
        for tags,data in group_sigs.items():
            all_names=list(map(lambda x: x[0],data))
            for nm in all_names:
                sig_name_to_tags[nm] =tags
        
        if sig_name in sig_name_to_tags:
            in_tag_group = sig_name_to_tags[sig_name]
            group_sigs[in_tag_group] = list(filter(lambda x: x[0]!=sig_name,group_sigs[in_tag_group])) #remove and next append (override)
        
        group_sigs[sig_tags].append([sig_name, sig_id, sig_type, sig_tags, sig_categorical, sig_units, sig_time_unit])
        seen_name.add(sig_name)
        seen_id.add(sig_id)

def generate_signals_file(codedir, workdir, final_name):
    sigs=get_final_sig_list(workdir)
    for forced_sig in FORCED_SIGNALS:
        if forced_sig not in sigs:
            raise NameError(f'Missing forced signal {forced_sig} in ETL')
    private_sigs_file=os.path.join(codedir, 'configs', 'rep.signals')
    os.makedirs(os.path.join(workdir, 'rep_configs'), exist_ok=True)
    final_signals_file=os.path.join(workdir, 'rep_configs' ,f'{final_name}.signals')
    
    #Genreate signals files from merge of both files:
    if_file=open(FULL_SIGNALS_TYPES, 'r')
    lines=if_file.readlines()
    if_file.close()
    lines=list(map(lambda x: x.strip(), lines))
    lines=list(filter(lambda x: len(x)>0 and not(x.startswith('#')), lines))
    
    lines2=[]
    if os.path.exists(private_sigs_file):
        if_file=open(private_sigs_file, 'r')
        lines2=if_file.readlines()
        if_file.close()
        lines2=list(map(lambda x: x.strip(), lines2))
        lines2=list(filter(lambda x: len(x)>0 and not(x.startswith('#')), lines2))
    #Merge types:
    typ_lines=list(filter(lambda x: x.startswith('GENERIC_SIGNAL_TYPE'),lines))
    typ_lines2=list(filter(lambda x: x.startswith('GENERIC_SIGNAL_TYPE'),lines2))
    lines=list(filter(lambda x: not(x.startswith('GENERIC_SIGNAL_TYPE')),lines))
    lines2=list(filter(lambda x: not(x.startswith('GENERIC_SIGNAL_TYPE')),lines2))
    #add typ_lines2 to typ_lines:
    exist_names=set(map(lambda x: x.split('\t')[1] ,typ_lines))
    for tp_ln in typ_lines2:
        nm=tp_ln.split('\t')[1]
        if nm not in exist_names:
            typ_lines.append(tp_ln)
    typ_lines.append("# SIGNAL <name> <signal id> <signal type num> <description> <is_categorical_per_val_channel> <unit_per_val_channel separated by '|' char>")
    typ_lines.append('#===============================================================================')
    typ_lines=list(map(lambda x: x+'\n',typ_lines))
    
    #Merge signals:
    
    group_sigs=dict()
    parse_signals(lines, group_sigs, FULL_SIGNALS_TYPES)
    parse_signals(lines2, group_sigs, private_sigs_file) #Will override
    #keep only used singals in sigs
    
    #Now add to file for each group:
    sig_lines=[]
    #add lines:
    for grp, data in sorted(group_sigs.items(), key=lambda x: 'AAA' if x[0].startswith('demographic') else x[0]):
        #Check we have singals in header
        using_sigs=False
        for signal_line in data:
            sig_name = signal_line[0]
            if sig_name in sigs:
                using_sigs=True
                break
        if not(using_sigs):
            continue
        #print header:
        sig_lines.append('')
        sig_lines.append('#===============================================================================')
        sig_lines.append('# %s'%(' => '.join(grp.split(','))))
        sig_lines.append('#===============================================================================')
        for signal_line in data:
            sig_name = signal_line[0]
            if sig_name not in sigs:
                continue
            sig_lines.append('SIGNAL\t%s'%('\t'.join(signal_line)))
    
    sig_lines=list(map(lambda x: x+'\n',sig_lines))
    #write all:
    fw=open(final_signals_file, 'w')
    fw.writelines(typ_lines+sig_lines)
    fw.close()

def generate_flow_script(workdir, dest_folder, dest_rep):
    os.makedirs(os.path.join(workdir, 'rep_configs'), exist_ok=True)
    convert_cfg_path = os.path.join(workdir, 'rep_configs', dest_rep+'.convert_config')
    flow_script=os.path.join(workdir, 'rep_configs', 'load_with_flow.sh')
    err_file=os.path.join(workdir, 'outputs', 'flow_loading_err.log')
    log_file=os.path.join(workdir, 'outputs', 'flow_loading.log')
    load_args='check_for_error_pid_cnt=500000;allowed_missing_pids_from_forced_ratio=0.1;max_bad_line_ratio=0.05;allowed_unknown_catgory_cnt=1000;run_parallel=0;run_parallel_files=0;allowed_missing_pids_from_forced_cnt=0;read_lines_buffer=100000'
    repository_final_dest=os.path.join(dest_folder, dest_rep+'.repository')
    os.makedirs(dest_folder, exist_ok=True)
    
    fr=open(convert_cfg_path, 'r')
    lines=fr.readlines()
    fr.close()
    lines=list(filter(lambda x: x.startswith('DATA'), lines))
    load_data_files_cnt=len(lines)
    
    fw=open(flow_script, 'w')
    fw.write('#!/bin/bash\n\n')
    fw.write('set -e\n')
    fw.write('export OMP_NUM_THREADS=1\n')
    if load_data_files_cnt > 1000:
        print(f'There are many input files ({load_data_files_cnt}) - you will need to increase system limit of open files',flush=True)
        fw.write('ulimit -Sn 9999\n')
    fw.write(f'Flow --rep_create --convert_conf {convert_cfg_path} --load_err_file {err_file} --load_args "{load_args}" 2>&1 | tee {log_file}\n')
    fw.write('\n')
    fw.write(f'Flow --rep_create_pids --rep {repository_final_dest}\n')
    fw.write('\n')
    fw.close()
    os.chmod(flow_script, 0o777)
    print('Target Repository: %s'%(repository_final_dest), flush=True)
    print('Full script to execute :\n%s'%(flow_script), flush=True)

def get_parent(x):
    if len(x)<=1 or x.find('_CODE:')<0:
        return None
    return x[:-1].strip('.')
    
def add_set_to_missing_parents(workdir, signal_types, signal):
    out_dict=os.path.join(workdir, 'rep_configs' ,'dicts')
    
    
    signal_ls=signal.split(',')
    selected_cols=[]
    si = signal_types[signal_ls[0]]
    for i,ch in enumerate(si.v_categ):
        if ch =='1': #Categorial
            selected_cols.append(f'value_{i}')
    
    dict_fname=list(filter(lambda x: x.startswith('dict.def_' + signal_ls[0]) ,os.listdir(out_dict)))
    if len(dict_fname) ==0:
        print(f'No missing codes for {signal_ls[0]}', flush=True)
        return
    alld=[]
    for di_p in dict_fname:
        alld.append(pd.read_csv(os.path.join(out_dict, di_p), sep='\t', skiprows=1, names=['def', 'code', 'value']))
    alld=pd.concat(alld, ignore_index=True)
    first_def_dict = alld.copy()
    
    max_cd=alld['code'].max()
    alld=alld[['value']].astype(str)
    alld['set']='SET'
    
    #sig_df = load_categ_sig(workdir, signal_types, signal)
    desired_ontologies=calc_ontologies(alld, ['value'], signal_ls[0], si.classes)
    
    def_dicts, set_dicts=get_dicts(desired_ontologies)
    if len(def_dicts)==0:
        print(f'Unknown mappings to {signal}', flush=True)
        return
    def_d=[]
    for dict_p in def_dicts:
        def_d.append(pd.read_csv(dict_p, sep='\t', skiprows=1, names=['def', 'code', 'value']))
    def_d=pd.concat(def_d, ignore_index=True)
    
    #Use search in alld missing codes in def_d:
    all_legal_values=set(def_d['value'])
    all_legal_values_extended = all_legal_values.union(set(first_def_dict['value']))
    max_id=max(max_cd,def_d['code'].max())+1000
    #alld['parent'] = alld['value'].apply(lambda x: get_parent(x))
    missing_codes=[]
    final_dict=[]
    final_chains=[]
    final_def_dicts=[]
    for i in range(len(alld)):
        val=alld.iloc[i]['value']
        parent = val
        full_chain=[val]
        while parent is not None:
            parent = get_parent(parent)
            if parent is None:
                missing_codes.append(val)
                final_chains.append([full_chain[0]])
                break
            full_chain.append(parent)
            if parent in all_legal_values: #Done, reached final
                final_chains.append(full_chain)
                for j in range(len(full_chain)-1):
                    final_dict.append([full_chain[j+1], full_chain[j]])
                    if full_chain[j+1] not in all_legal_values_extended:
                        final_def_dicts.append(full_chain[j+1])
                break
        
    #construct  final_dict dataframe:
    additional_defs=pd.DataFrame({'child':final_def_dicts})
    additional_defs=additional_defs.drop_duplicates().reset_index(drop=True)
    additional_defs['set']= 'DEF'
    additional_defs['parent']=list(range(max_id, max_id+len(additional_defs)))
    additional_defs=additional_defs[['set', 'parent', 'child']]
    final_dict= pd.DataFrame ({'parent': list(map(lambda x: x[0], final_dict)), 'child': list(map(lambda x: x[1], final_dict))})
    #print stats by final_chains:
    resolve_list=list(map(lambda x: len(x)-1, final_chains))
    codes_list=list(map(lambda x: x[0], final_chains))
    df_resolve=pd.DataFrame({'level': resolve_list, 'code': codes_list})
    df_resolve['p']=1
    print('Distribution of codes found by level up (0 means not found)', flush=True)
    print(df_resolve.groupby('level').count().reset_index(), flush=True) #0 means not found
    #print some examples for each level:
    for val_level in sorted(set(df_resolve['level'])):
        if val_level > 0:
            print(f'Example of matched codes by level = {val_level}', flush=True)
        else:
            print('Example of unmatched codes', flush=True)
        df_exm = df_resolve[df_resolve['level']==val_level].reset_index(drop=True)
        print(df_exm[['code']].head(5), flush=True)
    
    final_dict['set']='SET'
    final_dict=final_dict[['set', 'parent', 'child']]
    final_dict=final_dict.drop_duplicates().reset_index(drop=True)
    final_dict=pd.concat([additional_defs, final_dict], ignore_index=True)
    fw_path=os.path.join(out_dict,'dict.set_' + signal_ls[0])
    fw=open(fw_path, 'w')
    fw.write('SECTION\t%s\n'%(signal))
    final_dict.to_csv(fw, sep='\t', index=False, header=False)
    fw.close()
    print(f'Wrote additional dict in [{fw_path}]', flush=True)