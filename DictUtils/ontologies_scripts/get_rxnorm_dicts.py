import pandas as pd
import numpy as np
import os


DB_PATH='/server/Work/Data/UMLS/Install/2020AA/META/MRCONSO.RRF'
DB_REL_PATH='/server/Work/Data/UMLS/Install/2020AA/META/MRREL.RRF'
def generate_rx_cui_defs(store_path = None):
    df=pd.read_csv(DB_PATH, sep='|', low_memory=False,
                   names=['CONCEPT_ID','LANGUAGE','P','ID2','PF','ID3','Y','ID4','ID5','RX_CUI','EMPTY','ONTHOLOGY','SCD','RX_CUI2','DRUG_NAME','0','N','256','EMPTY2'],
                   usecols=['CONCEPT_ID','P','ID2','PF','ID3','Y','ID4','ID5','RX_CUI','ONTHOLOGY','SCD','DRUG_NAME','N','256'])
    print('Read DB')
    df=df[(df['ONTHOLOGY']=='RXNORM') & ((df['P']=='P') | (df['PF']=='PF'))].reset_index(drop=True)
    rx_cnts=df[['P', 'RX_CUI']].groupby('RX_CUI').count().reset_index().rename(columns= {'P': 'cnt'})
    df=df.set_index('RX_CUI').join(rx_cnts.set_index('RX_CUI')).reset_index()
    
    df_f=df[(df['cnt']==1)].reset_index(drop=True)[['RX_CUI', 'DRUG_NAME', 'CONCEPT_ID']].copy()
    df=df[(df['cnt']>1)].reset_index(drop=True)
    df_f=df_f.append(df[(df['P']=='P') & (df['PF']=='PF')][['RX_CUI', 'DRUG_NAME', 'CONCEPT_ID']].drop_duplicates().reset_index(drop=True), ignore_index=True)
    df=df[~df.RX_CUI.isin(df_f.RX_CUI)].reset_index(drop=True).drop(columns=['cnt'])
    rx_cnts=df[df['P']=='P'][['P', 'RX_CUI']].groupby('RX_CUI').count().reset_index().rename(columns= {'P': 'cnt'})
    df=df.set_index('RX_CUI').join(rx_cnts.set_index('RX_CUI')).reset_index()
    df_f=df_f.append(df[(df['cnt']==1) & (df['P']=='P') ][['RX_CUI', 'DRUG_NAME', 'CONCEPT_ID']].drop_duplicates().reset_index(drop=True), ignore_index=True)
    df=df[~df.RX_CUI.isin(df_f.RX_CUI)].reset_index(drop=True)
    df['DRUG_N']=df['DRUG_NAME'].map(lambda x:x.lower())
    df=df.drop_duplicates(['RX_CUI', 'DRUG_N', 'CONCEPT_ID']).reset_index(drop=True).drop(columns=['cnt'])
    rx_cnts=df[['P', 'RX_CUI']].groupby('RX_CUI').count().reset_index().rename(columns= {'P': 'cnt'})
    df=df.set_index('RX_CUI').join(rx_cnts.set_index('RX_CUI')).reset_index()
    df_f=df_f.append(df[(df['cnt']==1)][['RX_CUI', 'DRUG_NAME', 'CONCEPT_ID']].drop_duplicates().reset_index(drop=True), ignore_index=True)
    df=df[~df.RX_CUI.isin(df_f.RX_CUI)].reset_index(drop=True).drop(columns=['cnt'])
    
    df_f=df_f.append(df.drop_duplicates(['RX_CUI'])[['RX_CUI', 'CONCEPT_ID', 'DRUG_NAME']].reset_index(drop=True), ignore_index=True)
    print('Has %d RX codes'%(len(df_f)))
    
    df_f['DEF']='DEF'
    df_f=df_f.sort_values('RX_CUI').reset_index(drop=True)
    df_f['code']=6000+np.asarray(range(len(df_f)))
    df_f['RX_CD']='RX_CODE:' + df_f['RX_CUI']
    df_f['RX_DESC']='RX_DESC:' + df_f['DRUG_NAME'].apply(lambda x: x.strip().replace(' ', '_').replace(',', '_').replace('/', '_Over_'))
    if store_path is not None:
        df_final = df_f[['DEF', 'code', 'RX_CD']].copy()
        df_final=df_final.append(df_f[['DEF', 'code', 'RX_DESC']].rename(columns={'RX_DESC': 'RX_CD'}), ignore_index=True)
        df_final=df_final.sort_values(['code', 'RX_CD']).reset_index(drop=True)
    
        df_final.to_csv(store_path, header=False, index=False, sep='\t')
        print('Wrote dict into %s'%(store_path))
    return df_f[['CONCEPT_ID', 'RX_CUI', 'DRUG_NAME']]


def query_rx_cui(df_drug, df_atc,df_rel, rx_cui):
    direct_atc_rel = ['active_ingredient_of', 'active_moiety_of', 'ingredient_of']
    undirect_rel=  ['contained_in']
    
    concept_id=df_drug[df_drug.RX_CUI==rx_cui].CONCEPT_ID.iloc[0]
    print('Query for %s which is %s'%(rx_cui, concept_id))
    
    cn_df = df_rel[(df_rel.CONCEPT_ID==concept_id)].reset_index(drop=True).copy()
    res=set(cn_df[(cn_df.RELATION.isin(direct_atc_rel)) & (cn_df.RELATED_HOLDER_ID.isin(df_atc.CONCEPT_ID))].RELATED_HOLDER_ID)
    print('Direct Access: %s'%(','.join(res)))
    undirect_acc=cn_df[(cn_df.RELATION.isin(undirect_rel))][['RELATED_HOLDER_ID', 'RELATION']].drop_duplicates().reset_index(drop=True)
    print('Undirect codes')
    print(df_drug.set_index('CONCEPT_ID').join( undirect_acc.rename(columns={'RELATED_HOLDER_ID':'CONCEPT_ID'}).set_index('CONCEPT_ID'), how='inner').reset_index())
    
    res2=df_rel[(df_rel.CONCEPT_ID.isin(undirect_acc.RELATED_HOLDER_ID)) & (df_rel.RELATION.isin(direct_atc_rel)) & (df_rel.RELATED_HOLDER_ID.isin(df_atc.CONCEPT_ID))][['RELATED_HOLDER_ID', 'RELATION']].drop_duplicates().sort_values(['RELATED_HOLDER_ID', 'RELATION']).reset_index(drop=True)
    print('Undirect ATC components:')
    print(df_drug.set_index('CONCEPT_ID').join( res2.rename(columns={'RELATED_HOLDER_ID':'CONCEPT_ID'}).set_index('CONCEPT_ID'), how='inner').reset_index())
    res=res.union(set(res2.RELATED_HOLDER_ID))
    res=set(df_atc[(df_atc.CONCEPT_ID.isin(res))].RX_CUI2)
    return list(sorted(list(res)))

#G03C_A03
def reformat_atc(s):
    l=len(s)
    if len(s)<=4:
        return 'ATC_'+s+'_'*(8-l)
    else:
        return 'ATC_'+s[:4]+ '_' + s[4:] + (7-l)*'_'

def fetch_all_rel(df_drug, df_atc,df_rel, store_path=None):
    direct_atc_rel = ['active_ingredient_of', 'active_moiety_of', 'ingredient_of']
    undirect_rel=  ['contained_in']
    
    df_direct=df_rel[(df_rel.RELATION.isin(direct_atc_rel)) & (df_rel.RELATED_HOLDER_ID.isin(df_atc.CONCEPT_ID))][['CONCEPT_ID', 'RELATION','RELATED_HOLDER_ID']].drop_duplicates().reset_index(drop=True).rename(columns={'CONCEPT_ID':'CHILD_ID', 'RELATED_HOLDER_ID':'CONCEPT_ID'})
    df_direct_all=df_direct.set_index('CONCEPT_ID').join( df_atc.set_index('CONCEPT_ID'), how='inner').reset_index()[['CONCEPT_ID', 'RX_CUI2', 'DRUG_NAME', 'RELATION', 'CHILD_ID']].drop_duplicates().reset_index(drop=True).rename(columns={'RX_CUI2': 'ATC_SET', 'DRUG_NAME':'ATC_DESC_NAME'})
    df_direct_all_rx=df_direct_all.set_index('CHILD_ID').join(df_drug.rename(columns={'CONCEPT_ID': 'CHILD_ID'}).set_index('CHILD_ID'), how='inner').reset_index()
    #query df_direct_all_rx by CHILD_ID or RX_CUI
    
    df_undirect=df_rel[df_rel.RELATION.isin(undirect_rel)][['CONCEPT_ID', 'RELATION','RELATED_HOLDER_ID']].drop_duplicates().reset_index(drop=True).rename(columns={'RELATED_HOLDER_ID':'CHILD_ID', 'CONCEPT_ID':'PARENT_ID', 'RELATION':'RELATION_UNDIRECT'})
    df_undirect_linked=df_direct.set_index('CHILD_ID').join(df_undirect.set_index('CHILD_ID'), how='inner').reset_index()[['CONCEPT_ID','CHILD_ID', 'RELATION', 'PARENT_ID', 'RELATION_UNDIRECT']].drop_duplicates().reset_index(drop=True)
    df_undirect_linked_all=df_undirect_linked.set_index('CONCEPT_ID').join(df_atc.set_index('CONCEPT_ID') ,how='inner').reset_index()[['CONCEPT_ID', 'RX_CUI2', 'DRUG_NAME', 'RELATION', 'PARENT_ID']].drop_duplicates().reset_index(drop=True).rename(columns={'RX_CUI2': 'ATC_SET', 'DRUG_NAME':'ATC_DESC_NAME', 'PARENT_ID':'CHILD_ID'})
    df_undirect_linked_all_rx=df_undirect_linked_all.set_index('CHILD_ID').join(df_drug.rename(columns={'CONCEPT_ID': 'CHILD_ID'}).set_index('CHILD_ID'), how='inner').reset_index()
    
    df_all_flat=df_direct_all_rx.append(df_undirect_linked_all_rx,ignore_index=True).reset_index(drop=True)
    df_all_flat=df_all_flat[['RX_CUI', 'CHILD_ID', 'ATC_SET','ATC_DESC_NAME', 'DRUG_NAME']].drop_duplicates().reset_index(drop=True)
    if store_path is not None:
        dict_map=df_all_flat[['RX_CUI', 'ATC_SET']].drop_duplicates().reset_index(drop=True)
        dict_map['RX_CUI']=dict_map['RX_CUI'].apply(lambda x: 'RX_CODE:%s'%(x))
        dict_map['set']='SET'
        dict_map['ATC_SET']=dict_map['ATC_SET'].apply(reformat_atc)
        dict_map=dict_map[['set', 'ATC_SET', 'RX_CUI']].sort_values('RX_CUI').reset_index(drop=True)
        
        dict_map.to_csv(store_path, header=False, index=False, sep='\t')
        print('Wrote dict into %s'%(store_path))
        
    return df_all_flat
    #query df_direct_all by CHILD_ID => RX_CUI2 is the ATC

def generate_rx_cui_atc_map(store_path):
    black_list= ['contains', 'dose_form_of', 'inactive_ingredient_of', 'tradename_of', 'use']
    df_drug=generate_rx_cui_defs()
    df_atc=pd.read_csv(DB_PATH, sep='|', low_memory=False,
                   names=['CONCEPT_ID','LANGUAGE','P','ID2','PF','ID3','Y','ID4','ID5','RX_CUI','EMPTY','ONTHOLOGY','SCD','RX_CUI2','DRUG_NAME','0','N','256','EMPTY2'],
                   usecols=['CONCEPT_ID','P','PF','RX_CUI','ONTHOLOGY','SCD','DRUG_NAME','RX_CUI2'])
    print('Read atc')
    df_rel=pd.read_csv(DB_REL_PATH, low_memory=False,sep='|',
                   names=['CONCEPT_ID','ID2','CD_TYPE','R_TYPE','RELATED_HOLDER_ID', 'ID3','CD_TYPE2','RELATION','ID4','ID5','ONTHOLOGY','ONTHOLOGY2','ID6','FLAG1','ID7','EMPTY1','EMPTY2'],
                       usecols=['CONCEPT_ID','CD_TYPE','R_TYPE','RELATED_HOLDER_ID','CD_TYPE2','RELATION','ONTHOLOGY'])
    print('Read Rel DB')
    df_atc=df_atc[df_atc['ONTHOLOGY']=='ATC'].reset_index(drop=True)
    df_rel=df_rel[df_rel.CONCEPT_ID!=df_rel.RELATED_HOLDER_ID].reset_index(drop=True)
    df_rel=df_rel[~df_rel.RELATION.isin(black_list)].reset_index(drop=True)
    fetch_all_rel(df_drug, df_atc,df_rel, store_path)
    
    
def get_missing_atc(store_path):
    df_atc=pd.read_csv(DB_PATH, sep='|', low_memory=False,
                   names=['CONCEPT_ID','LANGUAGE','P','ID2','PF','ID3','Y','ID4','ID5','RX_CUI','EMPTY','ONTHOLOGY','SCD','RX_CUI2','DRUG_NAME','0','N','256','EMPTY2'],
                   usecols=['CONCEPT_ID','P','PF','RX_CUI','ONTHOLOGY','SCD','DRUG_NAME','RX_CUI2'])
    df_atc=df_atc[df_atc['ONTHOLOGY']=='ATC'].reset_index(drop=True)
    df_atc=df_atc[['RX_CUI2', 'DRUG_NAME']].rename(columns={'RX_CUI2':'atc', 'DRUG_NAME':'atc_desc'}).drop_duplicates(subset=['atc']).reset_index(drop=True)
    df_atc['atc']=df_atc['atc'].apply(reformat_atc)
    df_atc['atc_desc']=df_atc['atc_desc'].apply(lambda x: x.replace(', ', '_').replace(',', '_').replace(' ', '_'))
    existing_codes=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.atc_defs'), sep='\t', names=['DEF', 'code', 'atc'])
    
    existing_codes= existing_codes[['atc']]
    existing_codes=existing_codes[existing_codes.atc.str.find(':')<0].reset_index(drop=True)
    missing=df_atc[~df_atc.atc.isin(existing_codes.atc)].reset_index(drop=True)
    missing.to_csv(store_path,sep='\t', header=False, index=False)
 
def get_parent(x):
    #Structure: ATC_1223_455
    if not(x.endswith('_')):
        return x[:-2]+ '__'
    elif x[-3]!='_':
        return x[:-3]+ '___'
    elif x[-5]!='_':
        return x[:-5]+ '_____'
    elif x[-6]!='_':
        return x[:-7]+ '_______'
    return None
    
 
 def add_missing_atc_sets(store_path):
     existing_codes=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.atc_defs'), sep='\t', names=['DEF', 'code', 'atc'])
     existing_codes= existing_codes[['atc']]
     existing_codes=existing_codes[existing_codes.atc.str.find(':')<0].reset_index(drop=True)
     
     df_atc=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'RX', 'missing_atc_codes'), sep='\t', names=['atc', 'atc_desc'])
     df_atc=df_atc[['atc']]
     df_atc['parent']=df_atc.atc.apply(get_parent)
     df_atc['set']= 'SET'
     df_atc=df_atc[['set', 'parent', 'atc']]
     missing_parents=df_atc[~df_atc.parent.isin(existing_codes.atc)][['parent']].drop_duplicates().reset_index(drop=True).copy()
     print('missing parents %d'%(len(missing_parents)))
     if len(missing_parents):
         print('need to do again')
     df_atc.to_csv(store_path,sep='\t', header=False, index=False)
    
    
#generate_rx_cui_defs(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','RX', 'dicts', 'dict.defs_rx'))
#generate_rx_cui_atc_map(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','RX', 'dicts', 'dict.set_atc_rx'))
#get_missing_atc(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'RX', 'missing_atc_codes'))