import pandas as pd
import numpy as np
import os


DB_PATH='/server/Work/Data/UMLS/Install/2020AA/META/MRCONSO.RRF'
DB_REL_PATH='/server/Work/Data/UMLS/Install/2020AA/META/MRREL.RRF'
DB_SNOMED_ICD10='/server/Work/Data/SnoMed/SnoMedCT_RF2_int_20200731/SnomedCT_InternationalRF2_PRODUCTION_20200731T120000Z/Full/Refset/Map/der2_iisssccRefset_ExtendedMapFull_INT_20200731.txt'
def generate_snomed_defs(store_path = None):
    df=pd.read_csv(DB_PATH, sep='|', low_memory=False,
                   names=['CONCEPT_ID','LANGUAGE','P','ID2','PF','ID3','Y','ID4','ID5','SNOMED_ID','EMPTY','ONTHOLOGY','SCD','RX_CUI2','DESC_NAME','0','N','256','EMPTY2'],
                   usecols=['CONCEPT_ID','P','ID2','PF','ID3','Y','ID4','ID5','SNOMED_ID','ONTHOLOGY','SCD','DESC_NAME','N','256'])
    print('Read DB')
    df=df[(df['ONTHOLOGY']=='SNOMEDCT_US')].reset_index(drop=True)
    
    df['DESC_N']=df['DESC_NAME'].astype(str).map(lambda x:x.lower())
    
    df=df.drop_duplicates(['SNOMED_ID', 'DESC_N', 'CONCEPT_ID']).reset_index(drop=True)
    print('Has %d SNOMED codes, duplicates %d'%(df.SNOMED_ID.nunique(), len(df)))
    df_f=df.drop_duplicates(['SNOMED_ID']).reset_index(drop=True)
    
    df_f['DEF']='DEF'
    df_f=df_f.sort_values('SNOMED_ID').reset_index(drop=True)
    df_f['code']=100000+np.asarray(range(len(df_f)))
    df_f['SNOMED_CD']='SNOMED_CODE:' + df_f['SNOMED_ID']
    df_f['SNOMED_DESC']='SNOMED_DESC:' + df_f['SNOMED_ID'] + ":" + df_f['DESC_NAME'].astype(str).apply(lambda x: x.strip().replace(' ', '_').replace(',', '_').replace('/', '_Over_'))
    if store_path is not None:
        df_final = df_f[['DEF', 'code', 'SNOMED_CD']].copy()
        df_final=pd.concat([df_final, df_f[['DEF', 'code', 'SNOMED_DESC']].rename(columns={'SNOMED_DESC': 'SNOMED_CD'})], ignore_index=True)
        df_final=df_final.sort_values(['code', 'SNOMED_CD']).reset_index(drop=True)
    
        df_final.to_csv(store_path, header=False, index=False, sep='\t')
        print('Wrote dict into %s'%(store_path))
    return df_f[['CONCEPT_ID', 'SNOMED_ID', 'DESC_NAME']]

def fetch_all_rel(df_snomed, df_icd9,df_rel, store_path=None):
    direct_icd_rel = ['mapped_to'] #mapped_from
    #
    df_direct=df_rel[(df_rel.RELATION.isin(direct_icd_rel)) & (df_rel.RELATED_HOLDER_ID.isin(df_snomed.CONCEPT_ID))][['CONCEPT_ID', 'RELATION','RELATED_HOLDER_ID']].drop_duplicates().reset_index(drop=True).rename(columns={'CONCEPT_ID':'CHILD_ID', 'RELATED_HOLDER_ID':'CONCEPT_ID'})
    breakpoint()
    df_direct_all=df_direct.set_index('CONCEPT_ID').join( df_snomed.set_index('CONCEPT_ID'), how='inner').reset_index().drop_duplicates().reset_index(drop=True)
    df_direct_all_icd=df_direct_all.set_index('CHILD_ID').join(df_icd9.rename(columns={'CONCEPT_ID': 'CHILD_ID', 'DESC_NAME':'ICD9_DESC'}).set_index('CHILD_ID'), how='inner').reset_index()
    df_direct_all_icd=df_direct_all_icd[['SNOMED_ID', 'ICD9_CODE', 'ICD9_DESC', 'DESC_NAME']].drop_duplicates().reset_index(drop=True)
    
    if store_path is not None:
        dict_map=df_direct_all_icd[['SNOMED_ID', 'ICD9_CODE']].drop_duplicates().reset_index(drop=True)
        dict_map['SNOMED_ID']='SNOMED_CODE:' + dict_map['SNOMED_ID']
        dict_map['ICD9_CODE']='ICD9_CODE:' + dict_map['ICD9_CODE'].astype(str).map(lambda x: x.replace('.',''))
        dict_map['set']='SET'
        dict_map=dict_map[['set', 'ICD9_CODE', 'SNOMED_ID']].sort_values('ICD9_CODE').reset_index(drop=True)
        
        dict_map.to_csv(store_path, header=False, index=False, sep='\t')
        print('Wrote dict into %s'%(store_path))
        
    return df_all_flat
    #query df_direct_all by CHILD_ID => RX_CUI2 is the ATC

def generate_snomed_icd10_map(store_path, op=False):
    df_map=pd.read_csv(DB_SNOMED_ICD10, sep='\t', low_memory=False,
                   usecols=['referencedComponentId', 'mapRule', 'mapPriority','mapAdvice', 'mapTarget'])
    df_map=df_map[df_map['mapTarget'].notnull()].reset_index(drop=True)
    df_map=df_map[~df_map.mapRule.str.startswith('IFA')]
    df_map=df_map[['referencedComponentId', 'mapTarget']].rename(columns = {'referencedComponentId':'SNOMED_ID', 'mapTarget':'ICD10'}).drop_duplicates().reset_index(drop=True)
    df_map['set']='SET'
    df_map['SNOMED_ID'] =df_map['SNOMED_ID'].astype(str)
    df_map['ICD10'] =df_map['ICD10'].astype(str).map(lambda x:x.upper().replace('.',''))
    df_map['SNOMED_ID'] = 'SNOMED_CODE:' + df_map['SNOMED_ID']
    df_map['ICD10'] = 'ICD10_CODE:' + df_map['ICD10']
    if not(op):
        df_map=df_map[['set', 'SNOMED_ID', 'ICD10']]
    else:
        df_map=df_map[['set', 'ICD10', 'SNOMED_ID']]
    df_map.to_csv(store_path, header=False, index=False, sep='\t')
    print('Wrote dict into %s'%(store_path))
    #Store op_path

def generate_snomed_icd9_map(store_path):
    black_list= ['contraindicated_with_disease', 'clinically_similar']
    df_snomed=generate_snomed_defs()
    df_icd9=pd.read_csv(DB_PATH, sep='|', low_memory=False,
                   names=['CONCEPT_ID','LANGUAGE','P','ID2','PF','ID3','Y','ID4','ID5','RX_CUI','EMPTY','ONTHOLOGY','SCD','ICD9_CODE','DESC_NAME','0','N','256','EMPTY2'],
                   usecols=['CONCEPT_ID','P','PF','ONTHOLOGY','SCD','DESC_NAME','ICD9_CODE'])
    df_icd9=df_icd9[df_icd9['ONTHOLOGY']=='ICD9CM'].reset_index(drop=True)
    
    print('Read ICD9')
    df_rel=pd.read_csv(DB_REL_PATH, low_memory=False,sep='|',
                   names=['CONCEPT_ID','ID2','CD_TYPE','R_TYPE','RELATED_HOLDER_ID', 'ID3','CD_TYPE2','RELATION','ID4','ID5','ONTHOLOGY','ONTHOLOGY2','ID6','FLAG1','ID7','EMPTY1','EMPTY2'],
                       usecols=['CONCEPT_ID','CD_TYPE','R_TYPE','RELATED_HOLDER_ID','CD_TYPE2','RELATION','ONTHOLOGY'])
    print('Read Rel DB')
    df_icd9= df_icd9[['CONCEPT_ID', 'ICD9_CODE', 'DESC_NAME']].drop_duplicates()
    df_icd9['sz']=df_icd9['DESC_NAME'].astype(str).map(lambda x: len(x))
    df_icd9=df_icd9.sort_values(['CONCEPT_ID', 'sz'], ascending=[True, False]).drop_duplicates(['CONCEPT_ID']).drop(columns=['sz'])
    
    df_rel=df_rel[df_rel.CONCEPT_ID!=df_rel.RELATED_HOLDER_ID].reset_index(drop=True)
    df_rel=df_rel[~df_rel.RELATION.isin(black_list)].reset_index(drop=True)
    fetch_all_rel(df_snomed, df_icd9,df_rel, store_path)

def get_parent(x):
    #Structure: ICD10_CODE:XXXX
    return x[:-1]

def add_missing_icd10_sets():
     df_icd=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD10', 'dicts', 'dict.icd10'), sep='\t', names=['DEF', 'code', 'icd'])
     max_icd_id=df_icd.code.max()
     df_icd= df_icd[['icd']]
     df_icd['icd']=df_icd['icd'].astype('str').map(lambda x:x.replace('.', ''))
     
     df_snmd=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'SNOMED', 'dicts', 'dict.defs_snomed'), sep='\t', names=['def','code', 'snomed_id'])
     max_snmd_id=df_snmd.code.max()
     df_snmd=df_snmd[['snomed_id']]
     
     df_map=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'SNOMED', 'dicts', 'dict.set_snomed_icd10'), sep='\t', names=['SET', 'SNOMED_ID', 'ICD10_ID'])
     df_map['ICD10_ID']=df_map['ICD10_ID'].astype('str').map(lambda x:x.replace('.', ''))
     #Add missing snomed:
     miss_ids = list(set(df_map[~df_map['SNOMED_ID'].isin(df_snmd.snomed_id)].SNOMED_ID))
     add_snomed = pd.DataFrame({'SNOMED_ID': miss_ids})
     add_snomed['def']= 'DEF'
     add_snomed['code']=max_snmd_id+1+np.asarray(range(len(miss_ids)))
     add_snomed=add_snomed[['def', 'code', 'SNOMED_ID']]
     print('Adding %d rows'%(len(add_snomed)))
     breakpoint()
     print(add_snomed.head())
     
     if len(add_snomed)>0:
         add_snomed.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'SNOMED', 'dicts', 'dict.defs_snomed')
                   ,sep='\t', header=False, index=False, mode = 'a')
     
     #Add missing ICD10:
     miss_ids= list(set(df_map[~df_map['ICD10_ID'].isin(df_icd.icd)].ICD10_ID))
     add_icd = pd.DataFrame({'ICD10_ID': miss_ids})
     add_icd['def']= 'DEF'
     add_icd['code']=max_icd_id+1+np.asarray(range(len(miss_ids)))
     add_icd=add_icd[['def', 'code', 'ICD10_ID']]
     print('Adding %d rows'%(len(add_icd)))
     print(add_icd.head())
     if len(add_icd)>0:
         add_icd.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD10', 'dicts', 'dict.icd10')
                   ,sep='\t', header=False, index=False, mode = 'a')
     
     add_icd['parent']=add_icd.ICD10_ID.apply(get_parent)
     add_icd['set']= 'SET'
     add_icd=add_icd[['set', 'parent', 'ICD10_ID']]
     missing_parents=add_icd[~add_icd.parent.isin(df_icd.icd)][['parent', 'ICD10_ID']].drop_duplicates().reset_index(drop=True).copy()
     missing_parents['set']='SET'
     missing_parents=missing_parents[['set', 'parent', 'ICD10_ID']]
     if len(missing_parents)>0:
         missing_parents.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD10', 'dicts', 'dict.set_icd10')
                   ,sep='\t', header=False, index=False, mode='a')
     print('missing parents %d'%(len(missing_parents)))
     while len(missing_parents)>0:
         print('need to do for parents')
         df_icd=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD10', 'dicts', 'dict.icd10'), sep='\t', names=['DEF', 'code', 'icd'])
         max_icd_id=df_icd.code.max()
         df_icd= df_icd[['icd']]
         df_icd['icd']=df_icd['icd'].astype('str').map(lambda x:x.replace('.', ''))
         miss_ids= list(set(missing_parents.parent) - set(df_icd.icd))
         if len(miss_ids)==0:
             break
         add_icd = pd.DataFrame({'ICD10_ID': miss_ids})
         add_icd['def']= 'DEF'
         add_icd['code']=max_icd_id+1+np.asarray(range(len(miss_ids)))
         add_icd=add_icd[['def', 'code', 'ICD10_ID']]
         print('Adding %d rows'%(len(add_icd)))
         print(add_icd.head())
         add_icd.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD10', 'dicts', 'dict.icd10')
                       ,sep='\t', header=False, index=False, mode = 'a')
         missing_parents=miss_ids
         
def add_missing_icd9_sets():
     df_icd=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD9', 'dicts', 'dict.icd9dx'), sep='\t', names=['DEF', 'code', 'icd'])
     max_icd_id=df_icd.code.max()
     df_icd= df_icd[['icd']]
     df_icd['icd']=df_icd['icd'].astype('str').map(lambda x:x.replace('.', ''))
     
     df_snmd=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'SNOMED', 'dicts', 'dict.defs_snomed'), sep='\t', names=['def','code', 'snomed_id'])
     max_snmd_id=df_snmd.code.max()
     df_snmd=df_snmd[['snomed_id']]
     
     df_map=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'SNOMED', 'dicts', 'dict.set_icd9_snomed'), sep='\t', names=['SET',  'ICD9_ID', 'SNOMED_ID',])
     df_map['ICD9_ID']=df_map['ICD9_ID'].astype('str').map(lambda x:x.replace('.', ''))
     #Add missing snomed:
     miss_ids = list(set(df_map[~df_map['SNOMED_ID'].isin(df_snmd.snomed_id)].SNOMED_ID))
     add_snomed = pd.DataFrame({'SNOMED_ID': miss_ids})
     add_snomed['def']= 'DEF'
     add_snomed['code']=max_snmd_id+1+np.asarray(range(len(miss_ids)))
     add_snomed=add_snomed[['def', 'code', 'SNOMED_ID']]
     print('Adding %d rows'%(len(add_snomed)))
     print(add_snomed.head())
     if len(add_snomed)>0:
         add_snomed.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'SNOMED', 'dicts', 'dict.defs_snomed')
                   ,sep='\t', header=False, index=False, mode = 'a')
     
     #Add missing ICD10:
     miss_ids= list(set(df_map[~df_map['ICD9_ID'].isin(df_icd.icd)].ICD9_ID))
     add_icd = pd.DataFrame({'ICD9_ID': miss_ids})
     add_icd['def']= 'DEF'
     add_icd['code']=max_icd_id+1+np.asarray(range(len(miss_ids)))
     add_icd=add_icd[['def', 'code', 'ICD9_ID']]
     print('Adding %d rows'%(len(add_icd)))
     print(add_icd.head())
     breakpoint()
     if len(add_icd)>0:
         add_icd.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ICD9', 'dicts', 'dict.icd9dx')
                   ,sep='\t', header=False, index=False, mode = 'a')
     
       

os.makedirs(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','SNOMED'), exist_ok=True)
os.makedirs(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','SNOMED', 'dicts'), exist_ok=True)
#generate_snomed_defs(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','SNOMED', 'dicts', 'dict.defs_snomed'))
generate_snomed_icd10_map(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','SNOMED', 'dicts', 'dict.set_snomed_icd10'))
generate_snomed_icd10_map(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','SNOMED', 'dicts', 'dict.set_icd10_snomed'), True)
#add_missing_icd10_sets()
#generate_snomed_icd9_map(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','SNOMED', 'dicts', 'dict.set_icd9_snomed'))
#add_missing_icd9_sets()