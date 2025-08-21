import os
import pandas as pd
import numpy as np
from Configuration import Configuration
import re
from shutil import copyfile

def collect_values(in_path,files,names):
    print(files)
    values = np.array([])
    for idx,file in enumerate(files):
        print(f'Collecing values from file {idx+1}/{len(files)} : {file}')
        full_path = os.path.join(in_path,file)
        df = pd.read_csv(full_path,sep='\t',header=None,index_col=False,names=names)
        _values = df.value.unique()
        values = np.unique(np.concatenate([values,_values]))

    return values

def create_admissions_dict(in_path,dict_path):
    file_name = 'dict.ADMISSION'
    sigs = ['ADMISSION']

    # Read data
    files = [file for file in os.listdir(in_path) if re.search("^ADMISSION(\d*)$",file)]
    names = ['pid','signal','start_date','end_date','value','enc_id']
    values = collect_values(in_path, files, names)
    defs = zip(values.T, np.arange(len(values)))
    sets = []

    write_dict(dict_path, file_name, sigs, defs, sets)

def create_cancer_location_dict(onto_path,in_path,dict_path,addendum_file,sets_file,err_file):
    file_name = 'dict.Cancer_Location'
    sigs = ['Cancer_Location']

    # Read ICD-10 codes
    inFile = os.path.join(onto_path,'ICD10','dicts','dict.icd10')
    icd10 = pd.read_csv(inFile,sep='\t',header=None,names=['def','key','val'])
    max_key = icd10.key.max() + 1

    # Read Addendum and add to dictionary
    addendum = pd.read_csv(addendum_file,sep='\t',header=None,index_col=False,names=['code','set'])
    addendum_defs = pd.DataFrame({'val':addendum.code,'key':np.arange(max_key,max_key+len(addendum))})
    addendum_defs['def'] = 'DEF'
    icd10 = pd.concat([icd10,addendum_defs],axis=0)

    # Collect Values
    files = [file for file in os.listdir(in_path) if re.search("^Cancer_Location(\d*)$",file)]
    names = ['pid','signal','date','value']
    values = collect_values(in_path,files,names)

    subset = icd10.loc[icd10.val.isin(values)]
    icd10 = icd10.loc[icd10.key.isin(subset.key.values)]

    # Write
    outFile = os.path.join(dict_path,file_name)
    with open(outFile, 'w') as file:
        sigs_v = ','.join(sigs)
        file.write(f'SECTION\t{sigs_v}\n')

    # Check for missing
    missing = pd.DataFrame({'MISSING':[value for value in values if value not in icd10.val.values]})
    missing.to_csv(err_file,index=False)

    icd10.to_csv(outFile, sep='\t', header=False, index=False, mode='a')

    create_cancer_sets_file(icd10,dict_path,onto_path,sets_file,err_file)


def create_cancer_sets_file(icd10,dict_path,onto_path,sets_file,err_file):

    file_name = 'dict.Cancer_Location_sets'
    sigs = ['Cancer_Location']

    #Read Sets file
    defs = []
    sets = []
    max_key = icd10.key.max() + 1
    values = icd10.val.values

    with open(sets_file,'r') as file:
        for line in file:
            set,members = line.rstrip('\r\n').split('\t')
            members = members.split(',')

            defs.append([set,max_key])
            values = np.append(values,set)
            max_key += 1

            for member in members:
                regex = re.compile('.*({}).*'.format(member))
                vmatch = np.vectorize(lambda x:bool(regex.match(x)))
                matches = vmatch(values)
                match_values = values[matches]
                sets.extend(zip(match_values,[set]*len(match_values)))

    write_dict(dict_path, file_name, sigs, defs, sets)

def create_diagnosis_dict(onto_path,in_path,dict_path,err_file):
    sigs = ['Diagnosis','Procedure']

    # Copy dictionaries
    dicts = (
        ('ICD9','dict.icd9dx'), 
        ('ICD9','dict.set_icd9dx'), 
        ('ICD9','dict.icd9sg'), 
        ('ICD9','dict.set_icd9sg'), 
        ('ICD10','dict.icd10'), 
        ('ICD10','dict.set_icd10'), 
        ('ICD10_TO_ICD9','dict.set_icd10_2_icd9'),
        ('CPT','dict.cpt'),
        ('HCPCS','dict.hcpcs')
        )
    allDefs = pd.DataFrame()

    idx=0
    for dict in dicts:
        inFile = os.path.join(onto_path,dict[0],'dicts',dict[1])
        outFile = os.path.join(dict_path,dict[1])
        print(f'copy {inFile} to {outFile}')
        with open(outFile,'w') as file:
            sigs_v = ','.join(sigs)
            file.write(f'SECTION\t{sigs_v}\n')

        dict = pd.read_csv(inFile,sep='\t',header=None)
        if (idx>0):
            dict = dict.loc[(dict[0]=='SET') | (~dict[2].isin(allDefs[2].values))]
        isNewDef = ((dict[0] == 'DEF') & (dict[1] != dict.shift(1)[1])).astype(int)
        defCnt = idx + isNewDef.cumsum()
        dict.loc[dict[0]=='DEF',1] = defCnt.loc[dict[0]=='DEF']
        if (len(dict.loc[dict[0]=='DEF'])>0):
            idx = dict.loc[dict[0]=='DEF'][1].max() + 1

        dict.to_csv(outFile,sep='\t',header=False,index=False,mode='a')
        allDefs = pd.concat([allDefs,dict.loc[dict[0]=='DEF']],axis=0)

    # Collect Values
    dx_files = [file for file in os.listdir(in_path) if re.search("^Diagnosis(\d*)$",file)]
    names = ['pid','signal','date','value','principal_diagnosis_indicator','admitting_diagnosis','reason_for_visit','enc_id']
    dx_values = collect_values(in_path,dx_files,names)
    print(f'size of dx-values = {len(dx_values)}')

    prc_files = [file for file in os.listdir(in_path) if re.search("^Procedure(\d*)$", file)]
    names = ['pid','signal','date','value','principal_procedure_indicator','enc_id']
    prc_values = collect_values(in_path,prc_files,names)
    print(f'size of prc-values = {len(prc_values)}')

    values = np.unique(np.concatenate((prc_values,dx_values),axis=0))
    print(f'size of values = {len(values)}')

    # Check for missing values
    def_values = allDefs[2].unique()
    missing_values = [value for value in values if value not in def_values]

    file_name = 'dict.Diagnosis'
    defs = zip(missing_values,np.arange(idx,idx+len(missing_values)))
    sets = []

    write_dict(dict_path, file_name, sigs, defs, sets)

def create_gender_dict(dict_path):
    file_name = 'dict.GENDER'
    sigs = ['GENDER']
    defs = [['M',1],['F',2]]
    sets =[]

    write_dict(dict_path,file_name,sigs,defs,sets)

def write_dict(dir,file,sigs,defs,sets):

    full_path = os.path.join(dir,file)
    sigs = ','.join(sigs)
    with open(full_path,'w') as file:
        file.write(f'SECTION\t{sigs}\n')
        for entry in defs:
            file.write(f'DEF\t{entry[1]}\t{entry[0]}\n')
        for entry in sets:
            file.write(f'SET\t{entry[1]}\t{entry[0]}\n')


if __name__ == '__main__':

    cfg = Configuration()
    final_signals_path = os.path.join(cfg.work_path,'FinalSignals')
    dict_path = os.path.join(cfg.work_path,'rep_config','dicts')

    # Dictionaries
    # Demographics
    create_gender_dict(dict_path)

    # Admissions
    create_admissions_dict(final_signals_path,dict_path)

    # Diagnosis + Procedure
    err_file = os.path.join(cfg.work_path, 'create_dict.missing_diagnosis')
    create_diagnosis_dict(cfg.onto_path,final_signals_path,dict_path,err_file)

    # Cancer Locations
    #err_file = os.path.join(cfg.work_path, 'create_dict.missing_cancer_locations')
    #addendum_file = os.path.join(cfg.code_path,'ICD-O.addendum')
    #sets_file = os.path.join(cfg.code_path,'Cancer_Location_Sets')
    #create_cancer_location_dict(cfg.onto_path,final_signals_path,dict_path,addendum_file,sets_file,err_file)
