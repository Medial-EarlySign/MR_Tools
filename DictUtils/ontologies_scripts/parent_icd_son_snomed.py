import pandas as pd
import numpy as np
import os, sys

BASE_PATH='/nas1/Work/Data/Mapping/SNOMED'

def process():
    concept, concept_relationship=fetch_maps()
    SNOMED=concept[concept['vocabulary_id'].isin(['SNOMED Veterinary', 'SNOMED'])].reset_index(drop=True).copy()
    direct_map, full_join=get_hop(SNOMED,concept, concept_relationship,1)
    direct_map2, full_join2=get_hop(full_join,concept, concept_relationship,2)
    #No more then 2 hops:
    final_df=pd.concat([direct_map, direct_map2], ignore_index=True).drop_duplicates(subset=['PARENT', 'SON']).reset_index(drop=True)
    final_df['set']='SET'
    final_df=final_df[['set', 'PARENT', 'SON']]
    SNOMED['SNOMED']='SNOMED_CODE:'+SNOMED['concept_code']
    return final_df, SNOMED

def get_hop(df, concept, concept_relationship, i):
    if 'concept_id_2' in df.columns:
        df=df.drop(columns=['vocabulary_id_hope', 'domain_id_hope', 'concept_class_id_hope', 'concept_code_hope']).rename(columns={'relationship_id': 'relationship_id_prev'})
        snomed_rel=df.rename(columns={'concept_id_2':'concept_id_last'}).set_index('concept_id_last').join(concept_relationship[['concept_id_1', 'concept_id_2', 'relationship_id']].rename(columns={'concept_id_1':'concept_id_last'}).set_index('concept_id_last'), how='inner', rsuffix=f'_rel{i}').reset_index()
    else:
        snomed_rel=df.set_index('concept_id').join(concept_relationship[['concept_id_1', 'concept_id_2', 'relationship_id']].rename(columns={'concept_id_1':'concept_id'}).set_index('concept_id'), how='inner', rsuffix=f'_rel{i}').reset_index()
    full_join=snomed_rel.set_index('concept_id_2').join(concept.rename(columns={'concept_id': 'concept_id_2'}).set_index('concept_id_2'), how='inner', rsuffix='_hope').reset_index()
    #REMOVES ICD9
    full_join=full_join[full_join['vocabulary_id_hope']!='ICD9CM'].reset_index(drop=True)

    full_join=full_join[~full_join['domain_id_hope'].isin(['Spec Anatomic Site', 'Procedure', 'Meas Value', 'Drug', 'Device'])].reset_index(drop=True)
    full_join=full_join[~full_join['concept_class_id_hope'].isin(['Procedure', 'Model Comp', 'Qualifier Value'])].reset_index(drop=True)
    full_join=full_join[~full_join['relationship_id'].isin(['Has due to', 'Has causative agent', 'Due to of', 'Occurs before'])].reset_index(drop=True)
    #full_join=full_join[full_join['relationship_id'].isin(['Concept same_as to', 'Concept was_a to', 'Maps to', 'Concept alt_to to', 'Concept poss_eq to', 'Concept replaces', 'Subsumes'])].reset_index(drop=True)
    
    cols=['concept_code', 'concept_code_hope', 'relationship_id']
    if 'relationship_id_prev' in full_join.columns:
        cols.append('relationship_id_prev')
    direct_map=full_join[full_join['vocabulary_id_hope'].isin(['ICD10', 'ICD10CM'])][cols].reset_index(drop=True).copy()
    full_join=full_join[full_join['relationship_id'].isin(['Concept same_as to', 'Concept was_a to', 'Maps to', 'Concept alt_to to', 'Concept poss_eq to', 'Concept replaces', 'Subsumes'])].reset_index(drop=True).copy()
    direct_map['PARENT']='ICD10_CODE:' + direct_map['concept_code_hope'].astype(str).apply(lambda x: x.replace('.',''))
    direct_map['SON']='SNOMED_CODE:' + direct_map['concept_code']
    if len(cols) == 3:
        direct_map['relationship_id_prev']=None
    direct_map=direct_map[['PARENT', 'SON', 'relationship_id', 'relationship_id_prev']]
    full_join=full_join[~full_join['vocabulary_id_hope'].isin(['ICD10', 'ICD10CM'])].reset_index(drop=True)
    return direct_map, full_join


def fetch_maps():
    concept_path=os.path.join(BASE_PATH, 'CONCEPT.csv')
    rel_path=os.path.join(BASE_PATH, 'CONCEPT_RELATIONSHIP.csv')
    #syn_path=os.path.join(base_path, 'CONCEPT_SYNONYM.csv')

    #Filter concepts
    print(f'read {concept_path}')
    concept=pd.read_csv(concept_path, sep='\t', low_memory=False)
    print(f'read {rel_path}')
    concept_relationship=pd.read_csv(rel_path, sep='\t', low_memory=False)
    print('CONCEPT size:%d - start'%(len(concept)))
    concept=concept[concept['vocabulary_id'].isin(['SNOMED', 'ICD10CM', 'SNOMED Veterinary', 'ICD9CM', 'ICD10'])].reset_index(drop=True)
    print('CONCEPT size:%d - after filter relevant vocabularies'%(len(concept)))
    concept=concept[(concept['vocabulary_id'].isin(['ICD10CM', 'ICD10'])) | ( (concept['vocabulary_id'].isin(['SNOMED Veterinary', 'SNOMED'])) & (concept['domain_id'].isin(['Condition'])))]
    print('CONCEPT size:%d - filter condition in SNOMED'%(len(concept)))
    #Filter jung from rel:
    print('CONCEPT_RELATIONSHIP size:%d - start'%(len(concept_relationship)))
    concept_relationship=concept_relationship[(concept_relationship['concept_id_1'].isin(concept.concept_id)) & (concept_relationship['concept_id_2'].isin(concept.concept_id))].reset_index(drop=True)
    print('CONCEPT_RELATIONSHIP size:%d - filter known concept'%(len(concept_relationship)))
    concept_relationship=concept_relationship[~concept_relationship['relationship_id'].isin(['Has due to', 'Has causative agent', 'Due to of', 'Occurs before'])].reset_index(drop=True)
    print('CONCEPT_RELATIONSHIP size:%d - filter non relevant realtions'%(len(concept_relationship)))
    concept_relationship=concept_relationship[concept_relationship['concept_id_1']!=concept_relationship['concept_id_2']]
    print('CONCEPT_RELATIONSHIP size:%d - filter different concept_id_1<>concept_id_2'%(len(concept_relationship)))
    return concept, concept_relationship

def clear_str(s):
    return s.strip().replace('"', '_').replace(',', '_').replace(' ', '_')

def generate_dict_from_codes(df, dup_separator='_'):    
    min_code=2000000
    
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
    return dict_df

final_df, SNOMED=process()
final_df.to_csv(os.path.join(BASE_PATH,'dict.sets_icd10_snomed'), sep='\t', index=False, header=False)
#print SNOMED codes!
min_code=2000000
dict_df=generate_dict_from_codes(SNOMED[['SNOMED', 'concept_name']])
dict_df.to_csv(os.path.join(BASE_PATH,'dict.defs_snomed'), sep='\t', index=False, header=False)