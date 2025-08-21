import pandas as pd
import os, sys

sys.path.insert(0, os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'common'))
from dicts_utils import *

RX_NORM_PATH='/nas1/Work/Data/Mapping/Medications'

def generate_rx_codes():
    df=pd.read_csv(os.path.join(RX_NORM_PATH, 'CONCEPT.csv'), sep='\t', low_memory=False )
    df=df[df['domain_id']=='Drug'].reset_index(drop=True)
    atc_df=df[(df['vocabulary_id']=='ATC')].reset_index(drop=True).copy()
    rx_df=df[(df['vocabulary_id']!='ATC')].reset_index(drop=True).copy()
    del df
    
    rx_df = rx_df[['concept_code', 'concept_name']]
    rx_df['concept_code'] = rx_df['concept_code'].astype(str).map(lambda x: 'RX_CODE:' + x)
    rx_df['concept_name'] = rx_df['concept_name'].astype(str).map(lambda x: 'RX_DESC:' + x.strip().replace(' ', '_').replace(',', '_').replace('/', '_Over_'))
    
    atc_df= atc_df[['concept_code', 'concept_name']]
    atc_df['concept_code']= 'ATC:' + atc_df['concept_code'].astype(str)
    atc_df['concept_name']= 'ATC:' + atc_df['concept_code'].astype(str) + ':' + atc_df['concept_name'].astype(str).map(lambda x: x.strip().replace(' ', '_').replace(',', '_').replace('/', '_Over_'))
    
    generate_dict_from_codes(atc_df, os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','ATC', 'dicts', 'dict.defs_atc'), min_code=100)
    generate_dict_from_codes(rx_df, os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','RX', 'dicts', 'dict.defs_rx'), min_code=10000)
    
    
def generate_rx_maps():
    df=pd.read_csv(os.path.join(RX_NORM_PATH, 'CONCEPT.csv'), sep='\t', low_memory=False )
    df=df[df['domain_id']=='Drug'].reset_index(drop=True)
    atc_df=df[(df['vocabulary_id']=='ATC')].reset_index(drop=True).copy()
    rx_df=df[(df['vocabulary_id']!='ATC')].reset_index(drop=True).copy()
    del df
    
    rx_df=rx_df.rename(columns={'concept_id': 'concept_id_1'})
    atc_df=atc_df.rename(columns={'concept_id': 'concept_id_2'})
    df_rel=pd.read_csv(os.path.join(RX_NORM_PATH, 'CONCEPT_RELATIONSHIP.csv'), sep='\t')
    df_rel=df_rel[df_rel.concept_id_1!=df_rel.concept_id_2].reset_index(drop=True)
    df_rel=df_rel.drop_duplicates(subset=['concept_id_1', 'concept_id_2']).reset_index(drop=True)
    df_rel=df_rel[df_rel['relationship_id']!='RxNorm dose form of'].reset_index(drop=True)
    df_rel_rx = df_rel[['concept_id_1', 'concept_id_2', 'relationship_id']].set_index('concept_id_1').join(rx_df.set_index('concept_id_1'), how='inner').reset_index()
    df_rel_atc = df_rel[['concept_id_1', 'concept_id_2', 'relationship_id']].set_index('concept_id_2').join(atc_df.set_index('concept_id_2'), how='inner').reset_index()
    
    #First step map directly:
    df_rel_direct = df_rel_rx.set_index('concept_id_2').join(atc_df.set_index('concept_id_2'), how='inner', rsuffix='.atc' ).reset_index()
    df_rel_direct=df_rel_direct[['concept_code', 'concept_code.atc', 'relationship_id', 'concept_name', 'concept_name.atc']].rename(columns=
                                                                                                                                {'concept_code': 'rx_code', 'concept_code.atc':'atc_code','concept_name':'rx_desc', 'concept_name.atc': 'atc_desc'})
    df_rel_direct['rx_code'] = 'RX_CODE:' + df_rel_direct['rx_code']
    df_rel_direct['atc_code'] = 'ATC:' + df_rel_direct['atc_code']
    
    #Map maybe with more than 1 step:
    df_rel_rx2 = df_rel_rx.set_index('concept_id_2').join(df_rel_atc.rename(columns={'concept_id_2': 'concept_id_3', 'concept_id_1': 'concept_id_2'}).set_index('concept_id_2'), how='inner', rsuffix='.atc' ).reset_index()
    df_rel_rx2 = df_rel_rx2.drop_duplicates(subset=['concept_id_1', 'concept_id_3']).reset_index(drop=True)

    #df_rel_rx2 = df_rel_rx2[df_rel_rx2['concept_id_2']!=df_rel_rx2['concept_id_1']]
    df_rel_rx2 = df_rel_rx2.drop_duplicates(subset=['concept_id_1', 'concept_id_2']).reset_index(drop=True)
    df_rel_rx2 = df_rel_rx2[['concept_code', 'concept_code.atc', 'relationship_id', 'concept_name', 'concept_name.atc']].rename(columns=
                                                                                                                                {'concept_code': 'rx_code', 'concept_code.atc':'atc_code','concept_name':'rx_desc', 'concept_name.atc': 'atc_desc'})
    df_rel_rx2['rx_code'] = 'RX_CODE:' + df_rel_rx2['rx_code']
    df_rel_rx2['atc_code'] = 'ATC:' + df_rel_rx2['atc_code']
    df_rel_rx2=df_rel_rx2.drop_duplicates(subset=['rx_code', 'atc_code']).reset_index(drop=True)
    
    #Let's combine:
    df_final=pd.concat([df_rel_direct, df_rel_rx2]).drop_duplicates().reset_index(drop=True)
    df_final['cmd']='SET'
    df_final=df_final[['cmd', 'atc_code','rx_code']]
    
    df_final.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies','RX', 'dicts', 'dict.sets_atc_rx'), sep='\t', index=False, header=False)
    print('Wrote %s'%(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'RX', 'dicts', 'dict.sets_atc_rx')))

def get_atc_parent(x):
    #Structure: 1223455
    if len(x)>=7 or len(x)==3:
        return x[:-2]
    else:
        return x[:-1]

def add_atc_hir():
     existing_codes=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.defs_atc'), sep='\t', names=['DEF', 'code', 'atc'])
     existing_codes['len'] = existing_codes['atc'].map(lambda x: len(x))
     existing_codes=existing_codes.sort_values(['len']).drop_duplicates(subset=['code']).reset_index(drop=True)
     existing_codes= existing_codes[['atc']]
     #Let's "calc" ATC sets:
     prefix='ATC:'
     no_prefix = existing_codes.atc.map(lambda x: x[len(prefix):] if x.startswith(prefix) else x)
     parents_no_prefix=no_prefix.map(get_atc_parent)
     
     df=pd.DataFrame()
     df['parents_no_prefix']=parents_no_prefix
     df['child']=existing_codes.atc
     df['filter_empty']=parents_no_prefix.map(lambda x: len(x)>0)
    
     df=df[df['filter_empty']>0].reset_index(drop=True)
    
     df['parent']= prefix + df['parents_no_prefix']
     df=df[['parent', 'child']]
    
     #Check parent exists:
     df=df[df['parent'].isin(existing_codes['atc'])]
     df['cmd']='SET'
     df=df[['cmd', 'parent', 'child']].drop_duplicates().sort_values(['parent', 'child']).reset_index(drop=True)
     df.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.sets_atc'), sep='\t', index=False, header=False)
     print('Wrote %s'%(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.sets_atc')))

def reformat_atc(s):
    l=len(s)
    if len(s)<=4:
        return 'ATC_'+s+'_'*(8-l)
    else:
        return 'ATC_'+s[:4]+ '_' + s[4:] + (7-l)*'_'

def create_atc_syn():
    df=pd.read_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.defs_atc'), sep='\t', names=['DEF', 'code', 'atc'])
    df['len'] = df['atc'].map(lambda x: len(x))
    df=df.sort_values(['len']).drop_duplicates(subset=['code']).reset_index(drop=True)
    df['syn']=df['atc'].map(lambda x: reformat_atc(x.replace('ATC:','')) )
    df=df[['DEF', 'code', 'syn']].sort_values(['code']).reset_index(drop=True)
    df.to_csv(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.defs_atc_syn'), sep='\t', index=False, header=False)
    print('Wrote %s'%(os.path.join(os.environ['MR_ROOT'], 'Tools', 'DictUtils', 'Ontologies', 'ATC', 'dicts', 'dict.defs_atc_syn')))
#generate_rx_codes()
#generate_rx_maps()
#add_atc_hir()
create_atc_syn()