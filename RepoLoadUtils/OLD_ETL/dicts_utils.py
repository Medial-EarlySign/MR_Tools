import os,re
import pandas as pd
import numpy as np

def fix_def_dict(dict_path, prefix_orig, prefix_in_data, out_dict_path, signal='DIAGNOSIS'):
    dict_header=['DEF', 'ID', 'VALUE']
    dict_df=pd.read_csv(dict_path, sep='\t', names=dict_header)
    #transform prefix. for example ICD10_CODE: to ICD10:
    if prefix_orig is not None and len(prefix_orig)>0:
        dict_df.loc[ dict_df['VALUE'].str.startswith(prefix_orig) ,'VALUE']= dict_df.loc[ dict_df['VALUE'].str.startswith(prefix_orig) ,'VALUE'].apply(lambda x: prefix_in_data+x[len(prefix_orig):])

    #Add header SECTION and store file
    of_file=open(out_dict_path, 'w')
    of_file.write('SECTION\t%s\n'%(signal))
    dict_df.to_csv(of_file, sep='\t', index=False, header=False)
    of_file.close()
    return dict_df

def fix_set_dict(dict_path, prefix_orig, prefix_in_data, out_dict_path, signal='DIAGNOSIS', child_prefix_orig=None, child_prefix_in_data=None):
    dict_header=['SET', 'PARENT', 'CHILD']
    dict_df=pd.read_csv(dict_path, sep='\t', names=dict_header)
    #transform PARENT
    if prefix_orig is not None and len(prefix_orig)>0:
        dict_df.loc[ dict_df['PARENT'].str.startswith(prefix_orig) ,'PARENT']= dict_df.loc[ dict_df['PARENT'].str.startswith(prefix_orig) ,'PARENT'].apply(lambda x: prefix_in_data+x[len(prefix_orig):])
    if child_prefix_orig is None:
        child_prefix_orig=prefix_orig
    if child_prefix_in_data is None:
        child_prefix_in_data=prefix_in_data
    if child_prefix_orig is not None and len(child_prefix_orig)>0:
        dict_df.loc[ dict_df['CHILD'].str.startswith(child_prefix_orig) ,'CHILD']= dict_df.loc[ dict_df['CHILD'].str.startswith(child_prefix_orig) ,'CHILD'].apply(lambda x: child_prefix_in_data+x[len(child_prefix_orig):])
    
    of_file=open(out_dict_path, 'w')
    of_file.write('SECTION\t%s\n'%(signal))
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

#def_dicts -is list of list. each list is: dictionary name and params for loading (from => to conversions of prefix string to match data. default is None when given not list)
#set_dicts - is list oif list. each list is: dictionary name and params for loading (from => to conversions of prefix string to match data. default is None when given not list)
#signal, data_files_prefix - name of signal (to create section), and name of data file prefix
#header - the header row of input data files
#to_use_list - column to create dicts for
def create_dict_generic(work_dir, def_dicts, set_dicts, signal, data_files_prefix, header, to_use_list):
    final_sig_folder=os.path.join(work_dir, 'FinalSignals')
    os.makedirs(os.path.join(work_dir, 'rep_configs'), exist_ok=True)
    out_dict=os.path.join(work_dir, 'rep_configs' ,'dicts')
    os.makedirs(out_dict, exist_ok=True)
    existing_dict_folder=cfg.dict_folder
    set_col_name='INTERNAL_MES_code_system'
    
    if set_col_name in to_use_list:
        raise NameError('Error in create_dict_generic - can\'t use name "%s" inside to_use_list argument'%(set_col_name))

    #Load dict defs:
    dict_arr=[]
    for def_d in def_dicts:
        params=[None, None]
        if type(def_d) is list:
            params=def_d[1:]
            def_d=def_d[0]
        dict_arr.append( fix_def_dict(os.path.join(existing_dict_folder, def_d), params[0], params[1], os.path.join(out_dict, def_d), signal) )

    for set_d in set_dicts:
        params=[None, None]
        if type(set_d) is list:
            params=set_d[1:]
            set_d=set_d[0]
        fix_set_dict(os.path.join(existing_dict_folder, set_d), params[0], params[1] , os.path.join(out_dict, set_d), signal)

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
            existing_cd=existing_cd.append(df_d[['VALUE']].copy().drop_duplicates().reset_index(drop=True), ignore_index=True)
            curr_m=df_d['ID'].max()
            if max_code is None or curr_m>max_code:
                max_code=curr_m
    if existing_cd is not None:
        existing_cd=existing_cd.drop_duplicates().reset_index(drop=True)
    else:
        existing_cd=pd.DataFrame({'VALUE':[]})

    data_files=sorted(list(filter(lambda x: x.startswith(data_files_prefix), os.listdir(final_sig_folder))), key = lambda x: sort_by_name(x))
    all_codes=[None for i in range(len(to_use_list))]
    for file_name in data_files:
        print('Reading %s'%(file_name),flush=True)
        df=pd.read_csv(os.path.join(final_sig_folder, file_name), sep='\t', names=header, usecols=to_use_list).drop_duplicates().reset_index(drop=True)
        if all_codes[0] is None:
            for i in range(len(all_codes)):
                col_name=to_use_list[i]
                all_codes[i]=df[[col_name]].drop_duplicates().reset_index(drop=True)
        else:
            for i in range(len(all_codes)):
                col_name=to_use_list[i]
                all_codes[i]=all_codes[i].append(df[[col_name]], ignore_index=True).drop_duplicates().reset_index(drop=True)

    if max_code is None:
        max_code=0
    for i in range(len(all_codes)):
        col_name=to_use_list[i]
        all_cd_df=all_codes[i]
        all_cd_df[col_name]=all_cd_df[col_name].astype(str)
        missing_codes=all_cd_df[~all_cd_df[col_name].isin(existing_cd['VALUE'])].copy()
        missing_codes['def']='DEF'
        missing_codes=missing_codes.sort_values(col_name).reset_index(drop=True)
        missing_codes[set_col_name]=np.asarray(range(len(missing_codes)))+10000+max_code
        max_code=missing_codes[set_col_name].max()    
        missing_codes=missing_codes[['def', set_col_name, col_name]]

        print('Have %d %s codes (%s), out of them %d is missing (%2.4f%%)'%( len(all_cd_df), data_files_prefix, col_name , len(missing_codes), float(100.0*len(missing_codes))/len(all_cd_df) ), flush=True)
        if len(missing_codes) > 0:
            add_s=''
            if len(all_codes)>1:
                add_s='_%s'%(col_name)
            of_file=open(os.path.join(out_dict, 'dict.def_%s%s'%(data_files_prefix, add_s)), 'w')
            of_file.write('SECTION\t%s\n'%(signal))
            missing_codes.to_csv(of_file, sep='\t', index=False, header=False)
            of_file.close()

def clear_str(s):
    return s.strip().replace('"', '_').replace(',', '_').replace(' ', '_')

#map_df has 2 columns from (first col),to(2nd col). generate dict that each code value has mapping to those 2 columns
def generate_dict_from_codes(map_df, outpath, _sep = '\t', min_code=1, dup_separator='_'):
    NOT_USED_COL_NAME='mes_internal_counter_46437'
    CODE_COL_NOT_USED= 'CODE_COL_MES_476523'
    if type(map_df) is str:
        df = pd.read_csv(map_df, sep= _sep)
    else:
        df=map_df
    from_col=df.columns[0]
    to_col=df.columns[1]
    df[from_col] = df[from_col].astype(str).map(clear_str)
    sz=len(df)
    df=df[(df[from_col].notnull())& (df[from_col]!='')].reset_index(drop=True)
    if (len(df)< sz):
        print('Filtered nulls in %s map from %d => %d'%(from_col, len(df), sz))
    sz=len(df)
    df=df.drop_duplicates(subset=[from_col]).reset_index(drop=True)
    if (len(df)< sz):
        print('Filtered duplicated map from %d => %d'%(len(df), sz))
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
        print('Filtered nulls in %s map from %d => %d'%(to_col, len(df), sz))
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
        print('Filtered duplicated in target map from %d => %d'%(len(df_jn), sz))
    sz=len(df_jn)
    #concat
    dict_df=  pd.concat([dict_df, df_jn], ignore_index=True).sort_values(CODE_COL_NOT_USED).reset_index(drop=True)
    #store:
    dict_df.to_csv(outpath, sep='\t', index=False, header=False)
    print('Wrote %s'%(outpath))

def hir_up(s, replace_token):
    if replace_token=='':
        return s[:-1]
    l=len(s)
    while l>0 and s[l]==replace_token:
        l=l-1
    if l>0:
        s[l]=replace_token
    return s

def is_empty_hir(s, replace_token):
    if replace_token=='':
        return len(s)>0
    return len(s.strip(replace_token))>0

def _rec_fix_hirarchial_codes(existing_codes, new_codes, prefix='ICD10_CODE:', replace_token=''):
    new_codes=new_codes[~new_codes.isin(existing_codes)]
    
    #no_prefix = list(map(lambda x: x[len(prefix):] if x.startswith(prefix) else x, new_codes))
    no_prefix = new_codes.map(lambda x: x[len(prefix):] if x.startswith(prefix) else x) 
    #parents_no_prefix=list(map(lambda x: hir_up(x,replace_token), no_prefix))
    parents_no_prefix=no_prefix.map(lambda x: hir_up(x,replace_token))
    df=pd.DataFrame()
    df['parents_no_prefix']=parents_no_prefix
    df['child']=new_codes
    df['filter_empty']=parents_no_prefix.map(lambda x: is_empty_hir(x, replace_token))
    
    df=df[df['filter_empty']>0].reset_index(drop=True)
    df['parent']= df['parents_no_prefix'].map(lambda x: prefix + x)
    df=df[['parent', 'child']]
    df['parent_exists']=df['parent'].isin(existing_codes)
    return df

#generate combination of new_codes + thier parents, connections to existing codes.
#existing_codes - is array of all existing strings
#new_codes -  is array of all new strings not in existing_codes
#min_code_value - integer, the numeric value to add defs
#replace_token - when going to parent and removing letter, what to add instead
#returns dict with def,set commands
def fix_hirarchial_codes(existing_codes, new_codes, min_code_value, prefix='ICD10_CODE:', replace_token='', def_new_code=True):
    dict_result = pd.DataFrame({'cmd':[], 'val1':[], 'val2':[]})
 
    df=_rec_fix_hirarchial_codes(existing_codes, new_codes, prefix, replace_token) #returns: parent,child,parent_exists
    #Let's find the parents in existing_codes:
    parents_existing_df=df[df['parent_exists']>0].reset_index(drop=True)[['parent', 'child']]
    parents_non_existing_df=df[df['parent_exists']==0].reset_index(drop=True)[['parent', 'child']]
    #Let's add mapping to parents_existing:
    mp_df = pd.DataFrame({'val1':parents_existing_df['parent'], 'val2':parents_existing_df['child']})
    mp_df['cmd']='SET'
    mp_df=mp_df[['cmd', 'val1', 'val2']]
    
    #def codes:
    if def_new_code:
        df_codes = pd.DataFrame({'val2':parents_existing_df['child']})
        df_codes['cmd']='DEF'
        df_codes['val1']=list(range(min_code_value, min_code_value+len(df_codes)))
        min_code_value = min_code_value+len(df_codes)
        df_codes=df_codes[['cmd', 'val1', 'val2']]
        dict_result=pd.concat([dict_result, df_codes, mp_df], ignore_index=True)
    else:
        dict_result=pd.concat([dict_result, mp_df], ignore_index=True)
    
    if len(parents_non_existing_df)==0:
        return dict_result
    #Now let's handle parents_non_existing_df - need to define parents and connect with child! - Try do again for those!
    df_p=_rec_fix_hirarchial_codes(existing_codes, parents_non_existing_df['parent'], prefix, replace_token)
    #Let's add those who are mapped only:
    df=parents_non_existing_df.set_index('parent').join(df_p.rename(columns={'parent':'parent_2', 'child': 'parent'}).set_index('parent'), how='left').reset_index()
    #Will have child,parent,parent_2,parent_exists
    df.loc[df['parent_exists'].isnull(), 'parent_exists']=0 #when no merged, filtered since there is no parent
    
    #now let's only add child,parent,parent_2 when parent_exists and define parent!
    df_to_add=df[df['parent_exists']>0].reset_index(drop=True)[['parent_2', 'parent', 'child']]
    
    #Add codes
    codes_df=pd.DataFrame({'val2': list(set(df_to_add['parent']) )})
    codes_df['cmd']='DEF'
    codes_df['val1'] = list(range(min_code_value, min_code_value+len(codes_df)))
    codes_df=codes_df[['cmd', 'val1', 'val2']]
    min_code_value = min_code_value+len(codes_df)
    
    if def_new_code:
        df_codes = pd.DataFrame({'val2':df_to_add['child']})
        df_codes['cmd']='DEF'
        df_codes['val1']=list(range(min_code_value, min_code_value+len(df_codes)))
        min_code_value = min_code_value+len(df_codes)
        df_codes=df_codes[['cmd', 'val1', 'val2']]
        codes_df = pd.concat([codes_df, df_codes], ignore_index=True)
    
    #Add mapping parent =>  child, parent_2 => parent
    mp_df_2 = pd.DataFrame({'val1':df_to_add['parent_2'], 'val2':df_to_add['parent']})
    mp_df_2['cmd']='SET'
    mp_df_2=mp_df_2[['cmd', 'val1', 'val2']]
    
    mp_df = pd.DataFrame({'val1':df_to_add['parent'], 'val2':df_to_add['child']})
    mp_df['cmd']='SET'
    mp_df=mp_df[['cmd', 'val1', 'val2']]
    
    #concat
    dict_result=pd.concat([dict_result, codes_df, mp_df_2, mp_df], ignore_index=True)
    
    #what we are left with - no mapping from child to parent!
    df=df[df['parent_exists']==0].reset_index(drop=True)[['parent_2', 'parent', 'child']].drop_duplicates(subset=['child']).reset_index(drop=True)
    #print as warning!
    if len(df)>0:
        print('There are %d not mapped codes'%(len(df)))
        print(df.head(20))
    
    return dict_result