import pandas as pd
import numpy as np
import json
import os
from utils import fixOS

crit_id_text_map = {}
query_id_to_crit_id = {}


def get_type_queries(typ):
    crits = [k for k, val in crit_id_text_map.items() if val['criteria_type'] == typ]
    cols = [q for q, v in query_id_to_crit_id.items() if v in crits]
    return cols


def read_json_with_comments(json_file):
    file1 = open(json_file, 'r')
    lines = file1.readlines()
    str = ''
    for ln in lines:
        if not ln.strip().startswith('//') and not ln.strip() == '':
            str += ln
    data = json.loads(str)
    return data


def get_short_names(mat_json_file):
    short_list = []
    mat_dict = read_json_with_comments(mat_json_file)
    actions = mat_dict['model_actions']
    for act in actions:
        if 'in_set_name' in act.keys():
            short_list.append(act['in_set_name'])
        elif 'signal' in act.keys():
            short_list.append(act['signal'])
    return short_list


def build_rename_dict(list_shorts, columns):
    ren_dict = {}
    for sh in list_shorts:
        full = [col for col in columns if sh in col]
        if len(full) != 1:
            continue
        ren_dict[full[0]] = sh
    return ren_dict


def check_crit_json(crit_json):
    print(' ====== cretiria json validity report ' + crit_json['trial_id'] + ' ===== ')
    # Check for duplicate criteria_id and build dict for easy access\
    global crit_id_text_map
    global query_id_to_crit_id
    crit_id_text_map = {}
    for crt in crit_json['criteria']:
        cid = crt.pop('criteria_id')
        if cid in crit_id_text_map.keys():
            print('Duplicate Criteria ID: ' + cid)
        crit_id_text_map[cid] = crt

    # Check for missing query - check if all criteria have queries
    for cid in crit_id_text_map.keys():
        if cid not in [crt['criteria_id'] for crt in crit_json['criteria_queries']]:
            print('Criteria with no query: ' + cid + ' (' + crit_id_text_map[cid]['criteria_type'] + ') ' + crit_id_text_map[cid]['original_text'])


    # Check for duplicate query IDs
    q1 = {cq["criteria_id"]: cq["query_list"] for cq in crit_json['criteria_queries']}
    # Save global map from query id to crit id for easy future use
    query_id_to_crit_id = {q['query_id']: k for k, val in q1.items() for q in val}
    quey_id_list = [q['query_id'] for sublist in q1.values() for q in sublist]
    if len(quey_id_list) != len(set(quey_id_list)):
        dupes = [x for n, x in enumerate(quey_id_list) if x in quey_id_list[:n]]
        print('Duplicated Query IDs: ' + str(dupes))
    print(' ====== ' + crit_json['trial_id'] + ' ===== ')


def by_query_matrix(matrix_df, criteria_queries):
    res_df = matrix_df[['id', 'time', 'Age']].copy()
    for cq in criteria_queries:
        for qr in cq['query_list']:
            q = qr['query']
            ukn = q['unknown'] if 'unknown' in q.keys() else 1
            if q['qtype'] == 'range':
                res_df.loc[:, qr['query_id']] = ((matrix_df[q['qcol']] >= q['qcond1']) & (matrix_df[q['qcol']] <= q['qcond2'])).astype(int)
                if ukn == 1:
                    res_df.loc[matrix_df[q['qcol']] == -65336, qr['query_id']] = -1
            elif q['qtype'] == 'event':
                res_df.loc[:, qr['query_id']] = ((matrix_df[q['qcol']] >= q['qcond1'])).astype(int)
    return res_df


def get_col_stat(query_id, ser1, is_include):
    ren_dict = {1: 'match', 0: 'non_match', -1: 'Unknown'}
    if is_include == 1:
        vc = ser1.value_counts(dropna=False)
        vcn = ser1.value_counts(dropna=False, normalize=True)
    else:
        ser2 = ser1.copy()
        ser2.replace(0, -2, inplace=True)
        ser2.replace(1, 0, inplace=True)
        ser2.replace(-2, 1, inplace=True)
        vc = ser2.value_counts(dropna=False)
        vcn = ser2.value_counts(dropna=False, normalize=True)
    vc = vc.rename(index=ren_dict).to_dict()
    vcn = vcn.rename(index={k: v + '_%' for k, v in ren_dict.items()}).to_dict()
    vc.update(vcn)
    vc['Query id'] = query_id
    vc['Creteria'] = crit_id_text_map[query_id_to_crit_id[query_id]]['original_text']
    return vc


def score_patients(res_df, full_query):
    and_cond = full_query['AND']
    all_cols = query_id_to_crit_id.keys()
    inc_cols = get_type_queries('Inclusion')
    exc_cols = get_type_queries('Exclusion')
    stat_list = []
    #cond = None
    res_df.loc[:, 'score'] = 0
    res_df.loc[:, 'inclusion_score'] = 0
    res_df.loc[:, 'exclusion_score'] = 0
    for c in and_cond:
        col = c['query_id']
        local_cond = (res_df[col] == c['include'])
        stat_dict = get_col_stat(col, res_df[col], c['include'])
        stat_list.append(stat_dict)
        #if cond is None:
        #    cond = local_cond
        #else:
        #    cond = cond & local_cond
        res_df.loc[local_cond, 'score'] = res_df[local_cond]['score'] + local_cond.astype(int)
        if col in inc_cols:
            res_df.loc[local_cond, 'inclusion_score'] = res_df[local_cond]['inclusion_score'] + local_cond.astype(int)
        elif col in exc_cols:
            res_df.loc[local_cond, 'exclusion_score'] = res_df[local_cond]['exclusion_score'] + local_cond.astype(int)
    res_df.loc[:, 'score'] = res_df['score']/len(all_cols)
    res_df.loc[:, 'inclusion_score'] = res_df['inclusion_score'] / len(inc_cols)
    res_df.loc[:, 'exclusion_score'] = res_df['exclusion_score'] / len(exc_cols)
    #fit_df = res_df[cond]
    fit_df = res_df[res_df['inclusion_score'] == 1]
    # Add summary to stat
    stat_list.append({'Query id': 'All Criteria',
                      'match': res_df[res_df['score'] == 1].shape[0],
                      'match_%': res_df[res_df['score'] == 1].shape[0]/res_df.shape[0],
                      'non_match': res_df[res_df['score'] != 1].shape[0],
                      'non_match_%':res_df[res_df['score'] != 1].shape[0]/res_df.shape[0]})
    stat_list.append({'Query id': 'Inclusion Criteria',
                      'match': res_df[res_df['inclusion_score'] == 1].shape[0],
                      'match_%': res_df[res_df['inclusion_score'] == 1].shape[0] / res_df.shape[0],
                      'non_match': res_df[res_df['inclusion_score'] != 1].shape[0],
                      'non_match_%': res_df[res_df['inclusion_score'] != 1].shape[0] / res_df.shape[0]})
    stat_list.append({'Query id': 'Exclusion Criteria',
                      'match': res_df[res_df['exclusion_score'] == 1].shape[0],
                      'match_%': res_df[res_df['exclusion_score'] == 1].shape[0] / res_df.shape[0],
                      'non_match': res_df[res_df['exclusion_score'] != 1].shape[0],
                      'non_match_%': res_df[res_df['exclusion_score'] != 1].shape[0] / res_df.shape[0]})
    stat_df = pd.DataFrame(stat_list)
    if 'Unknown' not in stat_df.columns:
        stat_df['Unknown'] = np.nan
        stat_df['Unknown_%'] = np.nan
    return stat_df, fit_df


if __name__ == '__main__':
    # Read the matrix from file and rename columns to short names (signal/in_set_name from model json)
    workdir = fixOS('/nas1/Work/Users/Tamar/ClinicalTrials/query/trial3')
    trial_alias = 'trial3'
    matrix = pd.read_csv(os.path.join(workdir, trial_alias + '.csv'))
    short_col_names = get_short_names(os.path.join(workdir, trial_alias + '.json'))
    rename_dict = build_rename_dict(short_col_names, matrix.columns.tolist())
    matrix.rename(columns=rename_dict, inplace=True)

    # Read the eligibility json
    crit_json = read_json_with_comments(os.path.join(workdir, 'criteria.json'))
    check_crit_json(crit_json)
    res_mat = by_query_matrix(matrix, crit_json['criteria_queries'])

    q_stat_df, final_df = score_patients(res_mat, crit_json['full_query'])

    stat_cols = ['Query id', 'match', 'match_%', 'non_match', 'non_match_%', 'Unknown', 'Unknown_%', 'Creteria']
    q_stat_df[stat_cols].to_csv(os.path.join(workdir, 'criteria_stat.csv'), index=False)
    final_df.to_csv(os.path.join(workdir, trial_alias + '_fit.csv'), index=False)
