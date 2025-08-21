import sys
import os
import re
import pandas as pd
import numpy as np
import time
import traceback
from Configuration import Configuration
from const_and_utils import read_fwf, fixOS, is_nan
from utils import to_float

if __name__ == '__main__':
    rem_terms = ['other', 'equipment', 'products', 'non-therapeutic', 'stomi', 'all', 'auxiliary', 'plasters', 'and',
                 'nutrients', 'incontinence', 'acid', 'combinations', 'general', 'preparations',
                 'with', 'for', 'cosmetics', 'protectives', 'inhibitor', 'indifferent', '(human)', 'oral',
                 'agents', 'artificial', 'tears', 'topical', 'use', 'formulations',
                 'vitamin', 'various', 'incl.', 'of',  'agents,', 'excl.', 'in', '-', 'blood', 'normal',
                 'human,', 'adm.', 'whole', 'against', 'virus', 'salt', 'tests,', 'surgical',
                 'drugs', 'diluting', 'beta', 'treatment', 'seeds)', '(psylla', 'cough', 'live', 'etc.)',
                 'cold', 'plain', 'soft', 'b,', 'b', 'e)', 'd', 'B', '', 'silicone', 'x', 'c', 'alfa', 'liquid', 'wounds', 'nasal',
                 'plastic', 'vaccines', 'vaccine', 'medicated', 'gum', 'yellow', 'B', 'system', 'without', 'urine',
                 'milk', 'mineral', 'or', 'dressing', 'fixed', 'i', 'ii', 'iii','ix', 'vii', 'viii', 'a', 'acne',
                 'bandage', 'silver', 'female', 'male']

    cfg = Configuration()
    code_folder = fixOS(cfg.code_folder)
    data_path = fixOS(cfg.raw_source_path)
    raw_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)

    drugcodes = read_fwf('Drugcodes', raw_path)
    drugcodes['drugcode'] = drugcodes['drugcode'].astype(str)
    atc = read_fwf('ATCTerms', raw_path)
    freq = read_fwf('DrugcodeFrequency', raw_path)
    mrg = drugcodes.merge(atc, how='left', left_on='atc', right_on='ATC')
    mrg = mrg.merge(freq, how='left', on='drugcode')

    mrg['genericname'] = mrg['genericname'].str.replace(',', '')
    name_split = mrg['genericname'].str.split(' ', expand=True)
    name_split = mrg[['drugcode', 'genericname', 'atc', 'freq']].join(name_split)
    name_split.drop_duplicates(subset='drugcode', inplace=True)
    #all_terms = mrg[mrg['Term'].notnull()]['Term'].str.split(' ', expand=False)
    all_atc_terms = [x.lower() for x in atc['Term']]
    all_terms = atc[atc['Term'].notnull()]['Term'].str.split(' ', expand=False)
    all_terms = [x.lower() for term in all_terms for x in term]
    all_terms = list(set(all_terms) - set(rem_terms))  # + ['solution', 'solutions']
    atc_cols = []
    for col in range(0, 8):
        name_split[str(col) + '_atc'] = name_split[col].str.lower().isin(all_terms)
        atc_cols.append(str(col) + '_atc')
        # name_split[str(col)+'_dose'] = name_split[col].str.extract('(^\d*)')
        name_split[str(col) + '_unit'] = name_split[col].str.split('([0-9\.]+)([A-z%/]+)', expand=False)

    name_split.set_index('drugcode', inplace=True)
    new_row_list = []
    for gn, splt in name_split.iterrows():
        new_row = {'drugcode': gn, 'genericname': splt['genericname'], 'atc': splt['atc'], 'freq': splt['freq']}
        print(gn, splt['genericname'])
        new_row['meds'] = []
        new_row['dose'] = []
        new_row['units'] = []
        prev_word = 'aaa'
        for st in range(0, 8):
            ucol = str(st) + '_unit'
            atc_col = str(st) + '_atc'
            if splt[atc_col]:
                curr_word = splt[ucol][0].lower()
                words_meds = prev_word + ' ' + curr_word
                if words_meds in all_atc_terms:
                    if prev_word in new_row['meds']:
                        new_row['meds'][-1] = words_meds
                    else:
                        new_row['meds'].append(words_meds)
                elif curr_word in all_atc_terms:
                    new_row['meds'].append(curr_word)
                prev_word = curr_word
            if splt[ucol] and len(splt[ucol]) > 1:  # It is a dose+unit
                for u in splt[ucol]:
                    if u == '':
                        continue
                    flt = to_float(u)
                    if is_nan(flt):
                        new_row['units'].append(u)
                    else:
                        new_row['dose'].append(flt)
        new_row_list.append(new_row)
    new_df = pd.DataFrame(new_row_list)

    print(new_df)
    final_map_list = []
    med_fit_df = new_df[(new_df['meds'].str.len() > 0) &
                    (new_df['units'].str.len() == new_df['meds'].str.len()) &
                    (new_df['dose'].str.len() == new_df['meds'].str.len())]
    for i, dc_info in med_fit_df.iterrows():
        new_row = {'drugcode': dc_info['drugcode'], 'genericname': dc_info['genericname'],
                   'atc': dc_info['atc'], 'freq': dc_info['freq']}
        for med_ind in range(0, len(dc_info['meds'])):
            new_row['med'] = dc_info['meds'][med_ind]
            new_row['dose'] = dc_info['dose'][med_ind]
            new_row['units'] = dc_info['units'][med_ind]
            final_map_list.append(new_row)

    # When meds >  units/dose check without the word sodium
    med_2words = new_df[(new_df['meds'].str.len() > 1) &
                        (new_df['units'].str.len() < new_df['meds'].str.len()) & (new_df['units'].str.len() > 0) &
                        (new_df['dose'].str.len() < new_df['meds'].str.len()) & (new_df['dose'].str.len() > 0)]
    for i, dc_info in med_2words.iterrows():
        new_row = {'drugcode': dc_info['drugcode'], 'genericname': dc_info['genericname'],
                   'atc': dc_info['atc'], 'freq': dc_info['freq']}
        if 'sodium' in dc_info['meds']:
            dc_info['meds'].remove('sodium')
            for med_ind in range(0, len(dc_info['meds'])):
                if dc_info['meds'][med_ind] in all_atc_terms:
                    new_row['med'] = dc_info['meds'][med_ind]
                    new_row['dose'] = dc_info['dose'][med_ind]
                    new_row['units'] = dc_info['units'][med_ind]
                    final_map_list.append(new_row)

    # When meds <  units/dose check without the word sodium --> if second unit is ml take the fisrt dose unit
    med_ml = new_df[(new_df['meds'].str.len() == 1) &
                    (new_df['units'].str.len() > new_df['meds'].str.len()) &
                    (new_df['dose'].str.len() > new_df['meds'].str.len())]
    for i, dc_info in med_ml.iterrows():
        new_row = {'drugcode': dc_info['drugcode'], 'genericname': dc_info['genericname'],
                   'atc': dc_info['atc'], 'freq': dc_info['freq']}
        if dc_info['units'][1] == 'ml' and dc_info['units'][0][-1] == '/':
            new_row['med'] = dc_info['meds'][0]
            new_row['dose'] = dc_info['dose'][0]
            new_row['units'] = dc_info['units'][0][:-1]
            final_map_list.append(new_row)

    final_map_df = pd.DataFrame(final_map_list)
    print(final_map_df)
