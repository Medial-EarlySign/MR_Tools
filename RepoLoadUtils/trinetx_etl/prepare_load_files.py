import pandas as pd
import os
import sys
import time
from Configuration import Configuration
import numpy as np
sys.path.append(os.path.join(f'/nas1/UsersData/{os.environ["USER"]}/MR', 'Tools', 'RepoLoadUtils', 'common'))
from unit_converts import round_ser
import subprocess
import datetime as dt

chunksize=10000000

large_chunksize=20000000

def get_id2nr(cfg):
    id2nrFile = os.path.join(cfg.work_path,'ID2NR')
    id2nrDf = pd.read_csv(id2nrFile,sep='\t',header=None)
    zit = zip(id2nrDf[0].values,id2nrDf[1].values)
    id2nr = dict(zit)

    return id2nr

def get_demographic_files(cfg,id2nr):
    inFile = os.path.join(cfg.data_path,'patient.csv')
    pat = pd.read_csv(inFile)
    print(f'Read {len(pat)} demographics entries')
    pat['pid'] = pat.patient_id.map(id2nr)

    path = os.path.join(cfg.work_path,'FinalSignals')

    # GENDER
    print('Doing GENDER')
    pat['signal'] = 'GENDER'
    outFile = os.path.join(path,'GENDER')
    pat[['pid','signal','sex']].to_csv(outFile, sep='\t', index=False, header=False)

    # BYEAR + BDATE
    print('Doing BYEAR/BDATE')
    pat['signal'] = 'BYEAR'
    pat['BYEAR'] = 0
    pat.loc[~pat.year_of_birth.isnull(), 'BYEAR'] = pat.loc[~pat.year_of_birth.isnull(), 'year_of_birth'].astype(int)
    outFile = os.path.join(path,'BYEAR')
    pat.loc[~pat.year_of_birth.isnull(),['pid', 'signal', 'BYEAR']].to_csv(outFile, sep='\t', index=False, header=False)

    pat['signal'] = 'BDATE'
    pat['date_of_birth'] = 0
    pat.loc[~pat.year_of_birth.isnull(),'date_of_birth'] = 10000* pat.loc[~pat.year_of_birth.isnull(),'year_of_birth'].astype(int) + 701
    outFile = os.path.join(path,'BDATE')
    pat.loc[~pat.year_of_birth.isnull(), ['pid', 'signal', 'date_of_birth']].to_csv(outFile, sep='\t', index=False, header=False)

    # DEATH
    print('Doing DEATH')
    pat['signal'] = 'DEATH'
    pat['date_of_death'] = 0
    pat.loc[~pat.month_year_death.isnull(),'date_of_death'] = 100 * pat.loc[~pat.month_year_death.isnull(),'month_year_death'].astype(int) + 15
    outFile = os.path.join(path,'DEATH')
    pat.loc[~pat.month_year_death.isnull(), ['pid', 'signal', 'date_of_death']].to_csv(outFile, sep='\t', index=False, header=False)


def get_lab_result_files(cfg,id2nr):
    # Read tests
    testsFile = os.path.join(cfg.code_path,'lab_tests.csv')
    tests = pd.read_csv(testsFile)

    # Read resolutions
    resFile = os.path.join(cfg.code_path,'lab_res.csv')
    res = pd.read_csv(resFile)
    resDict = dict(zip(res.signal,res.res))

    path = os.path.join(cfg.work_path, 'FinalSignals')

    use_existing = False
    if not use_existing:
        # Read Admissions for filtering
        adFile = os.path.join(path,'ADMISSION')
        admissions = pd.read_csv(adFile,sep='\t',header=None,names=['pid','signal','start','end','type'])
        print(f'Read {len(admissions)} admissions')

        # Read
        inFile = os.path.join(cfg.data_path, 'lab_result.csv')
        for idx, lab in enumerate(pd.read_csv(inFile, chunksize=chunksize)):
            # For writing
            mode = 'w' if (idx == 0) else 'a'

            print(f'Read {len(lab)} lab-results entries')
            lab['pid'] = lab.patient_id.map(id2nr)

            # Loop on tests
            for signal in tests.Signal.unique():
                testDf = tests.loc[tests.Signal == signal]
                testLabs = pd.DataFrame()
                for index, row in testDf.iterrows():
                    code_system = row['code_system']
                    code = row['code']
                    print(f'{idx}\tWorking on {signal} : {code_system} - {code}')
                    testLabs = pd.concat([testLabs, lab.loc[(lab.code_system == code_system) & (lab.code == code)]],
                                         axis=0)
                    print(f'{idx}\t\tCollected {len(testLabs)} labs results')

                testLabs['signal'] = signal

                # Remove tests that are within admissions
                testLabs['idx'] = np.arange(len(testLabs))
                testLabs = testLabs.merge(admissions, on='pid', how='left',suffixes=('','_admin'))
                testLabs['inside'] = (testLabs.date >= testLabs.start) & (testLabs.date <= testLabs.end)
                testLabs['inside_any'] = testLabs.groupby('idx').inside.transform(any)
                testLabs = testLabs.loc[~testLabs.inside_any]

                # Write to file
                outFile = os.path.join(path, signal)
                testLabs[['pid', 'signal', 'date', 'lab_result_num_val', 'code']].drop_duplicates().to_csv(outFile, sep='\t', index=False,header=False, mode=mode)

    # Read, Sort, Write
    for signal in tests.Signal.unique():
        print(f'sorting and filtering {signal}')
        outFile = os.path.join(path, signal)
        labs = pd.read_csv(outFile,sep='\t',header=None, names=['pid','signal','date','value','code'])
        norig = len(labs)
        labs = labs.loc[~labs['value'].isnull()]
        print(f'filtered from {norig} to {len(labs)}')

        # Round
        labs['rnd'] = resDict[signal]
        labs.value = round_ser(labs.value, labs.rnd)
        del labs['rnd']

        labs = labs.sort_values(by=['pid', 'date'])
        labs.to_csv(outFile, sep='\t', index=False, header=False)

def get_ambulatory_lab_result_files(cfg,id2nr):

    # Read tests
    testsFile = os.path.join(cfg.code_path,'lab_tests.csv')
    tests = pd.read_csv(testsFile)

    # Read resolutions
    resFile = os.path.join(cfg.code_path,'lab_res.csv')
    res = pd.read_csv(resFile)
    resDict = dict(zip(res.signal,res.res))

    path = os.path.join(cfg.work_path, 'FinalSignals')

    # find ambulatory encounters
    inFile = os.path.join(cfg.data_path,'encounter.csv')
    amb = pd.DataFrame()
    for idx,enc in enumerate(pd.read_csv(inFile,usecols=['encounter_id','patient_id','type'],chunksize=chunksize)):
        print(f'{idx}:Read {len(enc)} encounters entries')
        enc = enc.loc[enc.type=='AMB']
        amb = pd.concat([amb,enc],axis=0)
    amb['pid'] = amb.patient_id.map(id2nr)
    print(f'Read {len(amb)} ambulatory encounters')

    path = os.path.join(cfg.work_path,'FinalSignals')

    use_existing = False
    if not use_existing:
        # Read Admissions for filtering
        adFile = os.path.join(path,'ADMISSION')
        admissions = pd.read_csv(adFile,sep='\t',header=None,names=['pid','signal','start','end','type'])
        admissions['start_dt'] = pd.to_datetime(admissions.start, format='%Y%m%d')
        admissions['end_dt'] = pd.to_datetime(admissions.end, format='%Y%m%d')
        print(f'Read {len(admissions)} admissions')

        # Read
        inFile = os.path.join(cfg.data_path, 'lab_result.csv')
        for idx, lab in enumerate(pd.read_csv(inFile, chunksize=chunksize)):
            # For writing
            mode = 'w' if (idx == 0) else 'a'

            print(f'Read {len(lab)} lab-results entries')
            lab['pid'] = lab.patient_id.map(id2nr)

            # Filter to ambulatory encounters
            lab = lab.merge(amb,on=['pid','encounter_id'],how='inner')
            print(f'Filtered to {len(lab)} lab-results entries in ambulatory encounters')

            # Further filtering : 180 days after admission !
            gap = 180
            lab['idx'] = np.arange(len(lab))
            lab['date_dt'] = pd.to_datetime(lab.date, format='%Y%m%d')
            lab = lab.merge(admissions, on='pid', how='left')
            adm_lab = lab.loc[(lab.date_dt >= lab.start_dt) & (lab.date_dt <= lab.end_dt + dt.timedelta(days=gap))]
            lab = lab.loc[~lab.idx.isin(adm_lab.idx.values)].drop_duplicates(subset=['pid', 'date', 'lab_result_num_val','code']).copy()
            print(f'Filtered to {len(lab)} results not within {gap} days from admission')

            # Loop on tests
            for signal in tests.Signal.unique():
                testDf = tests.loc[tests.Signal == signal]
                testLabs = pd.DataFrame()
                for index, row in testDf.iterrows():
                    code_system = row['code_system']
                    code = row['code']
                    print(f'{idx}\tWorking on {signal} : {code_system} - {code}')
                    testLabs = pd.concat([testLabs, lab.loc[(lab.code_system == code_system) & (lab.code == code)]],axis=0)
                    print(f'{idx}\t\tCollected {len(testLabs)} labs results')

                # Write to file
                testLabs['signal'] = signal
                outFile = os.path.join(path, signal)
                testLabs[['pid', 'signal', 'date', 'lab_result_num_val', 'code']].drop_duplicates().to_csv(outFile, sep='\t', index=False,header=False, mode=mode)

    # Read, Sort, Write
    for signal in tests.Signal.unique():
        print(f'sorting and filtering {signal}')
        outFile = os.path.join(path, signal)
        labs = pd.read_csv(outFile,sep='\t',header=None, names=['pid','signal','date','value','code'])
        norig = len(labs)
        labs = labs.loc[~labs['value'].isnull()]
        print(f'filtered from {norig} to {len(labs)}')

        # Round
        labs['rnd'] = resDict[signal]
        labs.value = round_ser(labs.value, labs.rnd)
        del labs['rnd']

        labs = labs.sort_values(by=['pid', 'date'])
        labs.to_csv(outFile, sep='\t', index=False, header=False)

# Membership - naive approach (first encounter to last encounter, not considering gaps)
def get_membership_files(cfg,id2nr):
    inFile = os.path.join(cfg.data_path, 'encounter.csv')
    membership = pd.DataFrame(columns = ['pid','from','to'])

    for idx,enc in enumerate(pd.read_csv(inFile,usecols=['patient_id','start_date','end_date'],chunksize=chunksize)):
        print(f'{idx}:Read {len(enc)} encounters entries')
        enc = enc.loc[(~enc.start_date.isnull()) | (~enc.end_date.isnull())]
        enc.loc[enc.start_date.isnull(),'start_date'] = enc.loc[enc.start_date.isnull(),'end_date']
        enc.loc[enc.end_date.isnull(),'end_date'] = enc.loc[enc.end_date.isnull(),'start_date']
        enc['pid'] = enc.patient_id.map(id2nr)

        enc['max_date'] = enc.groupby('pid').end_date.transform(max)
        enc['min_date'] = enc.groupby('pid').start_date.transform(min)
        enc = enc[['pid','min_date','max_date']].drop_duplicates()

        membership = membership.merge(enc,on='pid',how='outer')
        membership.loc[(membership['from'].isnull()) | (membership['from'] > membership.min_date),'from'] = membership.min_date
        membership.loc[(membership['to'].isnull()) | (membership['to'] < membership.max_date),'to'] = membership.max_date
        membership = membership[['pid','from','to']]
        print(f'collected membership info for {len(membership)} ids')

    membership.sort_values(by='pid',inplace=True)
    membership['sig'] = 'Membership'

    # Write
    print('Writing Membership')
    path = os.path.join(cfg.work_path, 'FinalSignals')
    outFile = os.path.join(path,'Membership')
    membership[['pid','sig','from','to']].to_csv(outFile, sep='\t', index=False, header=False)


def get_admissions_file(cfg,id2nr):
    typesFile = os.path.join(cfg.code_path,'encounter_types.csv')
    types = pd.read_csv(typesFile)

    inFile = os.path.join(cfg.data_path,'encounter.csv')
    admissions = pd.DataFrame()

    for idx,enc in enumerate(pd.read_csv(inFile,chunksize=chunksize)):
        print(f'{idx}:Read {len(enc)} encounters entries')
        enc['pid'] = enc.patient_id.map(id2nr)

        enc = enc.merge(types,on='type',how='left')
        enc['signal'] = 'ADMISSION'

        # Filter outptatient encounters
        admissions = pd.concat([admissions,enc.loc[(enc.inpatient==1) | (enc.inpatient==-1)]],axis=0)
        print(f'{idx}:identified {len(admissions)} admissions')

    path = os.path.join(cfg.work_path,'FinalSignals')

    # Unite Admissions
    admissions.loc[admissions.end_date.isnull(),'end_date'] = admissions.loc[admissions.end_date.isnull(),'start_date']
    admissions.end_date = admissions.end_date.astype(int)

    admissions['start_date'] = admissions.groupby('encounter_id')['start_date'].transform(min)
    admissions['end_date'] = admissions.groupby('encounter_id')['end_date'].transform(max)

    # Filter single-day unknowns
    admissions = admissions.loc[(admissions.inpatient == 1) | ((admissions.inpatient == -1) & (admissions.start_date != admissions.end_date))]
    print(f'Filtered to {len(admissions)} admissions')

    # Remove duplicates
    admissions = admissions.drop_duplicates(subset=['pid', 'signal', 'start_date', 'end_date'])
    admissions = admissions.sort_values(by=['pid','start_date'])
    print(f'Found {len(admissions)} different admissions')

    # Write (I)
    print('Writing ADMISSION')
    outFile = os.path.join(path,'ADMISSION')
    admissions[['pid', 'signal', 'start_date', 'end_date','type']].to_csv(outFile, sep='\t', index=False, header=False)

    # Handle overlaps
    exe = f'/nas1/UsersData/{os.environ["USER"]}/MR/Tools/RepoLoadUtils/trinetx_etl/unite_admissions/Linux/Release/unite_admissions'
    cmd = [exe, '--file', outFile]
    unite_cmd = subprocess.run(cmd)
    print(f'{exe} exit code: {unite_cmd.returncode}')
    if (unite_cmd.returncode!=0):
        quit()

def get_diagnosis_files(cfg,id2nr):

    inFile = os.path.join(cfg.data_path,'diagnosis.csv')
    path = os.path.join(cfg.work_path, 'FinalSignals')

    for idx,diag in enumerate(pd.read_csv(inFile,chunksize=large_chunksize)):
        print(f'{idx}:Read {len(diag)} diagnosis entries')
        diag['pid'] = diag.patient_id.map(id2nr)
        diag = diag.sort_values(by=['pid', 'date'])
        diag['diagnosis'] = diag.code_system.str.replace('ICD-10-CM','ICD10_CODE').replace('ICD-9-CM','ICD9_CODE') + ':' + diag.code.str.replace('.','',regex=False)
        diag['signal'] = 'Diagnosis'

        # Handle missing values
        diag = diag.loc[~diag.diagnosis.isnull()]
        diag.loc[diag.principal_diagnosis_indicator.isnull(),'principal_diagnosis_indicator'] = 'Unknown'
        diag.loc[diag.reason_for_visit.isnull(),'reason_for_visit'] = 'Unknown'
        diag.loc[diag.admitting_diagnosis.isnull(),'admitting_diagnosis'] = 'Unknown'

        diag = diag[['pid','signal','date','diagnosis','principal_diagnosis_indicator','admitting_diagnosis','reason_for_visit','encounter_id']].sort_values(by=['pid','date'])
        outFile = os.path.join(path, f'Diagnosis{idx+1}')
        diag.to_csv(outFile, sep='\t', index=False, header=False)

def get_procedures_files(cfg,id2nr):

    inFile = os.path.join(cfg.data_path,'procedure.csv')
    path = os.path.join(cfg.work_path, 'FinalSignals')

    for idx,proc in enumerate(pd.read_csv(inFile,chunksize=large_chunksize)):
        print(f'{idx}:Read {len(proc)} procedures entries')
        proc['pid'] = proc.patient_id.map(id2nr)
        proc = proc.sort_values(by=['pid', 'date'])
        proc['procedure'] = proc.code_system.str.replace('CPT','CPT_CODE').replace('HCPCS','HCPCS_CODE').replace('ICD-9-CM','ICD9_CODE').replace('ICD-10-PCS','ICD10_CODE') + ':' + proc.code.str.replace('.','',regex=False)
        proc['signal'] = 'Procedure'

        # Handle missing values
        proc = proc.loc[~proc.procedure.isnull()]
        proc.loc[proc.principal_procedure_indicator.isnull(),'principal_procedure_indicator'] = 'Unknown'

        proc = proc[['pid','signal','date','procedure','principal_procedure_indicator','encounter_id']].sort_values(by=['pid','date'])
        outFile = os.path.join(path, f'Procedure{idx+1}')
        proc.to_csv(outFile, sep='\t', index=False, header=False)

def get_cancer_location_files(cfg,id2nr):

    # Tumor File
    inFile = os.path.join(cfg.data_path,'tumor.csv')
    tumors = pd.read_csv(inFile).rename(columns={'observation_date':'date'})
    print(f'Read {len(tumors)} tumor entries')
    tumors['pid'] = tumors.patient_id.map(id2nr)

    tumors['sig'] = 'Cancer_Location'
    tumors['value'] = tumors.tumor_site_code_system + ':' + tumors.tumor_site_code.str.replace('.','',regex=False)
    tumors = tumors[['pid', 'sig', 'date', 'value']].copy()

    #ICD-O -> ICD10
    tumor_codes = tumors.value.unique()
    dict0 = pd.DataFrame({'orig':tumor_codes})
    dict0['set'] = 'SET'
    dict0['new'] = dict0.orig.str.replace('ICD-O','ICD10_CODE')

    # Read ICD9->ICD10 map
    inFile1 = os.path.join(cfg.onto_path,'ICD10_TO_ICD9','dicts','dict.set_icd10_2_icd9')
    dict1 = pd.read_csv(inFile1,sep='\t',header=None,names=['set','new','orig'])
    inFile2 = os.path.join(cfg.code_path,'ICD10_2_ICD9.addenudm')
    dict2 = pd.read_csv(inFile2, sep='\t', header=None,names=['set','new','orig'])

    # Diagnosis File
    codes_file = os.path.join(cfg.code_path, 'cancer_icds')
    cancer_codes = pd.read_csv(codes_file, sep='\t', header=None, index_col=False, names=['code'])['code'].values

    inFile = os.path.join(cfg.data_path, 'diagnosis.csv')
    path = os.path.join(cfg.work_path, 'FinalSignals')

    for idx, diag in enumerate(pd.read_csv(inFile, chunksize=large_chunksize)):
        print(f'{idx}:Read {len(diag)} diagnosis entries')
        diag['pid'] = diag.patient_id.map(id2nr)
        diag = diag.sort_values(by=['pid', 'date'])
        diag['diagnosis'] = diag.code_system.str.replace('ICD-10-CM', 'ICD10_CODE').replace('ICD-9-CM','ICD9_CODE') + ':' + diag.code.str.replace('.', '', regex=False)
        tumors_from_diag = diag.loc[diag.diagnosis.isin(cancer_codes)].copy().rename(columns={'diagnosis':'value'})
        tumors_from_diag['sig'] = 'Cancer_Location'
        tumors = pd.concat([tumors,tumors_from_diag[['pid', 'sig', 'date', 'value']].copy()],axis=0)

    # Add ICD10->ICD10 mapping
    icd10_codes =tumors.loc[tumors.value.str.startswith('ICD10')].value.unique()
    dict3 = pd.DataFrame({'orig':icd10_codes,'new':icd10_codes})
    dict3['set'] = 'SET'
    dict_df = pd.concat([dict0,dict1,dict2,dict3],axis=0)
    icd_mapper = dict(zip(dict_df['orig'],dict_df['new']))

    path = os.path.join(cfg.work_path, 'FinalSignals')
    outFile = os.path.join(path,'Cancer_Location')

#    tumors[['pid', 'sig', 'date', 'value']].to_csv(f'{outFile}.nomap', sep='\t', index=False, header=False)
    tumors.value= tumors.value.map(icd_mapper)
    tumors = tumors.sort_values(by=['pid', 'date']).drop_duplicates(subset=['pid','value'])

    tumors[['pid','sig','date','value']].to_csv(outFile,sep='\t', index=False, header=False)

def get_train_files(cfg,id2nr):
    train = pd.DataFrame({'pid':list(id2nr.values())})
    train['p'] = np.random.uniform(size=len(train))
    train['value'] = 1
    train.loc[train.p > 0.7,'value'] = 2
    train.loc[train.p > 0.9,'value'] = 3
    train['sig'] = 'TRAIN'
    train.sort_values(by='pid',inplace=True)

    path = os.path.join(cfg.work_path, 'FinalSignals')
    outFile = os.path.join(path, 'TRAIN')
    train[['pid','sig','value']].to_csv(outFile,sep='\t',index=False,header=False)

#"patient_id","diagnosis_date","observation_date","tumor_site_code_system","tumor_site_code","morphology_code_system","morphology_code","stage_code_system","stage_code","tumor_size","number_of_lymph_nodes","metastatic","derived_by_TriNetX","source_id"

if __name__ == '__main__':
    cfg = Configuration()

    # Read ID2NR
    id2nr = get_id2nr(cfg)

    # Demographics
    #get_demographic_files(cfg,id2nr)

    # Admissions
    #get_admissions_file(cfg,id2nr)

    # Lab Results
    #get_lab_result_files(cfg,id2nr)
    #get_ambulatory_lab_result_files(cfg,id2nr)

    # Diagnosis
    #get_diagnosis_files(cfg,id2nr)

    # Procedures
    #get_procedures_files(cfg,id2nr)

    # Cancer
    get_cancer_location_files(cfg,id2nr)

    # TRAIN
    #get_train_files(cfg,id2nr)

    # Membership
    #get_membership_files(cfg,id2nr)
