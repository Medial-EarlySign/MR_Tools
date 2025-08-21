import os
import pandas as pd
import traceback
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, add_fisrt_line, fixOS, read_tsv
from shutil import copy
from load_therapy import get_unit_dosage_map


# def days_dicts(therapy_folder):
#     files = os.listdir(therapy_folder)
#     files = [x for x in files if '_therapy' in x]
#     #files = ['a_therapy', 'b_therapy']
#     tot_cnt_df = pd.DataFrame()
#     for file in files:
#         print(file)
#         pref = file[0]
#         drug_df = read_tsv(file, therapy_folder, names=['pid', 'signals', 'eventdate', 'val', 'val2'])
#         countdf = drug_df.groupby('val2').count()
#         countdf.rename(columns={'pid': pref + '_count'}, inplace=True)
#         if tot_cnt_df.empty:
#             tot_cnt_df = countdf[[pref + '_count']]
#         else:
#             tot_cnt_df = tot_cnt_df.merge(countdf[[pref + '_count']], how='outer', left_index=True, right_index=True)
#
#     tot_cnt_df['sum'] = tot_cnt_df.sum(axis=1)
#     return tot_cnt_df[['sum']]

def detailed_drug_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    raw_path = fixOS(cfg.doc_source_path)
    doc_path = fixOS(cfg.doc_source_path)
    dict_path = os.path.join(out_folder, 'dicts')
    dict_file = 'dict.detailed_drugs_defs'
    set_file = 'dict.detailed_drugs_set'
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    if os.path.exists(os.path.join(dict_path, set_file)):
        os.remove(os.path.join(dict_path, set_file))
    dc_start = 50000

    detailed_map = get_unit_dosage_map(raw_path)

    # for med, grp in detailed_map.groupby('med'):
    #     if len(grp['units'].unique()) > 1:
    #         grp1 = grp[(grp['multi'] == 1) & (grp['dose']!=9999)]
    #         if len(grp1['units'].unique()) > 1:
    #             unts = grp1[grp1['med'] == med]['units'].unique()
    #             unts2 = list(unts.copy())
    #             tot_freq = grp['freq'].sum()
    #             if tot_freq < 1000:
    #                 continue
    #             print('medication: ' + med + ' total records: ' + str(tot_freq))
    #             prnt_str =''
    #             for un in unts:
    #                 un_freq = grp1[grp1['units'] == un]['freq'].sum()
    #                 prnt_str += 'unit: ' + un + ' records = ' + str((un_freq/tot_freq)*100) + '\n'
    #                 if un_freq/tot_freq <= 0.05:
    #                     unts2.remove(un)
    #             if len(unts2) > 1:
    #                 print(prnt_str)
    #                 print(grp[['atc', 'dose', 'med', 'units', 'multi']])

    med_names = detailed_map['med'].unique()
    med_units = detailed_map['units'].unique()
    def_df = pd.DataFrame(data=(list(med_names) + list(med_units)), columns=['code'])
    def_df['def'] = 'DEF'
    def_df = def_df.assign(defid=range(dc_start, dc_start + def_df.shape[0]))
    if os.path.exists(os.path.join(dict_path, dict_file)):
        os.remove(os.path.join(dict_path, dict_file))
    write_tsv(def_df[['def', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\tDrug_detailed\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    atc_codes_df = read_fwf('ATCTerms', doc_path)
    atc_codes_df['lower'] = atc_codes_df['Term'].str.lower()

    set_df = pd.DataFrame(data=med_names, columns=['inner'])
    set_df['short'] = set_df['inner'].apply(lambda x: x.split('_')[0])
    set_df = set_df.merge(atc_codes_df, how='left', left_on='short', right_on='lower')

    set_df['outer'] = atc_code_from_atc(set_df, 'ATC')

    set_df['set'] = 'SET'
    if os.path.exists(os.path.join(dict_path, set_file)):
        os.remove(os.path.join(dict_path, set_file))
    write_tsv(set_df[['set', 'outer', 'inner']], dict_path, set_file)
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))


def drug_dicts():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.drugs_defs'
    #days_start = 0
    dc_start = 1200

    drug_codes_df = read_fwf('Drugcodes', doc_path)

    to_drug_dict = drug_codes_df[['drugcode', 'genericname']].copy()
    to_drug_dict['drugcode'] = to_drug_dict['drugcode'].astype(int).astype(str)
    to_drug_dict['genericname'] = to_drug_dict['genericname'].str.lower().str.replace(' ', '_')
    lists = to_drug_dict[['genericname', 'drugcode']].groupby(['genericname']).agg(lambda x: list(set(x.tolist())))
    to_drug_dict.drop('drugcode', axis=1, inplace=True)
    to_drug_dict = to_drug_dict.groupby('genericname').first()
    to_drug_dict = to_drug_dict.merge(lists, left_index=True, right_index=True)
    to_drug_dict.reset_index(drop=False, inplace=True)
    to_drug_dict['list'] = to_drug_dict.apply(lambda x: [x['genericname']] + x['drugcode'], axis=1)
    to_drug_dict = to_drug_dict.assign(defid=range(dc_start, dc_start+to_drug_dict.shape[0]))

    to_stack = to_drug_dict[['defid', 'list']].set_index('defid', append=True)
    drug_dict = to_stack['list'].apply(pd.Series).stack().reset_index(level=[0, 2], drop=True).reset_index()
    drug_dict['code'] = 'dc:' + drug_dict[0].astype(str).str.strip()

    #drug_dict = pd.concat([days_df[['defid', 'code']], drug_dict[['defid', 'code']]], sort=False)
    drug_dict['type'] = 'DEF'
    write_tsv(drug_dict[['type', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION' + '\t' + 'Drug\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE drug_dicts')


def atc_code_from_atc(df, col):
    return 'ATC_' + df[col].str.replace(' ', '_').str.pad(width=8, side='right', fillchar='_')


def atc_dicts():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.atc_defs'
    set_file = 'dict.atc_sets'
    atc_start = 100000

    drug_codes_df = read_fwf('Drugcodes', doc_path)
    atc_codes_df = read_fwf('ATCTerms', doc_path)

    # SET from drug code
    set_dict = drug_codes_df[['drugcode', 'atc']].copy()
    set_dict['atc'] = atc_code_from_atc(set_dict, 'atc')
    set_dict['drugcode'] = 'dc:' + set_dict['drugcode'].astype(str).str.strip()
    set_dict.rename(columns={'drugcode': 'inner', 'atc': 'outter'}, inplace=True)
    set_dict.dropna(how='any', inplace=True)

    len_dicts = {1: 3, 2: 2, 3: 4, 4: 6, 6: 8, 8: 8}
    set_dict_hier = pd.DataFrame()
    # Set from ATC hierarchy
    for _, atc1 in atc_codes_df.iterrows():
        val = atc1['ATC']
        for inn in [s for s in atc_codes_df['ATC'].values if val in s and len(s) <= len_dicts[len(val)] and val != s]:
            set_dict_hier = set_dict_hier.append({'outter': val, 'inner': inn}, ignore_index=True)
    set_dict_hier['inner'] = atc_code_from_atc(set_dict_hier, 'inner')
    set_dict_hier['outter'] = atc_code_from_atc(set_dict_hier, 'outter')
    set_dict = pd.concat([set_dict, set_dict_hier], sort=False)
    set_dict['type'] = 'SET'
    write_tsv(set_dict[['type', 'outter', 'inner']], dict_path, set_file)

    # Crate ATC def files
    atc_codes_df = atc_codes_df.assign(defid=range(atc_start, atc_start + atc_codes_df.shape[0]))
    atc_codes_df['ATC'] = atc_code_from_atc(atc_codes_df, 'ATC')
    atc_codes_df['Term'] = atc_codes_df['ATC'] + ':' + atc_codes_df['Term'].str.strip()
    to_stack = atc_codes_df.set_index('defid', drop=True)
    atc_dict = to_stack.stack().to_frame()
    atc_dict['defid'] = atc_dict.index.get_level_values(0)
    atc_dict.rename({0: 'code'}, axis=1, inplace=True)
    atc_dict['type'] = 'DEF'
    write_tsv(atc_dict[['type', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION' + '\t' + 'Drug,Drug_detailed\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))
    print('DONE atc_dicts')


def bnf_dics():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.bnf_defs'
    set_file = 'dict.bnf_sets'
    bnf_start = 200000

    drug_codes_df = read_fwf('Drugcodes', doc_path)
    bnf_codes_df = read_fwf('BNFcode', doc_path)

    # SET from drug code
    set_dict = pd.DataFrame()
    for col in ['bnfcode1', 'bnfcode2', 'bnfcode3']:
        set_dict1 = drug_codes_df[['drugcode', col]].copy()
        set_dict1 = set_dict1[set_dict1[col] != '00.00.00.00']
        set_dict1['bnf'] = 'BNF_' + set_dict1[col]
        set_dict1['raw_bnf'] = set_dict1[col]
        set_dict1['drugcode'] = 'dc:' + set_dict1['drugcode'].astype(str).str.strip()
        set_dict = set_dict.append(set_dict1[['drugcode', 'bnf']], ignore_index=True)
    set_dict.rename(columns={'drugcode': 'inner', 'bnf': 'outter'}, inplace=True)
    all_bnfs = set_dict[['outter']].copy()
    all_bnfs['bnfcode'] = all_bnfs['outter'].str[4:]
    all_bnfs.drop_duplicates(inplace=True)

    # Not all BNF are in BNFcode file so adding it ti df manually....
    bnf_codes_df = bnf_codes_df.merge(all_bnfs, how='right', left_on='bnfcode', right_on='bnfcode')
    bnf_codes_df.drop(columns=['outter'], inplace=True)

    # Set from BNF hierarchy
    set_dict_hier = pd.DataFrame()
    for _, bnf in bnf_codes_df.iterrows():
        val = bnf['bnfcode']
        val1 = val[:9] + '00'
        if val1 != val:
            for out in [s for s in bnf_codes_df['bnfcode'].values if val1 == s]:
                set_dict_hier = set_dict_hier.append({'outter': out, 'inner': val}, ignore_index=True)
        else:
            val2 = val[:6] + '00.00'
            if val2 != val:
                for out in [s for s in bnf_codes_df['bnfcode'].values if val2 == s]:
                    set_dict_hier = set_dict_hier.append({'outter': out, 'inner': val}, ignore_index=True)
            else:
                val3 = val[:3] + '00.00.00'
                if val3 != val:
                    for out in [s for s in bnf_codes_df['bnfcode'].values if val3 == s]:
                        set_dict_hier = set_dict_hier.append({'outter': out, 'inner': val}, ignore_index=True)

    set_dict_hier['outter'] = 'BNF_' + set_dict_hier['outter']
    set_dict_hier['inner'] = 'BNF_' + set_dict_hier['inner']

    set_dict = pd.concat([set_dict, set_dict_hier], sort=False)
    set_dict['type'] = 'SET'
    write_tsv(set_dict[['type', 'outter', 'inner']], dict_path, set_file)

    # Crate BNF def files
    bnf_codes_df = bnf_codes_df.assign(defid=range(bnf_start, bnf_start + bnf_codes_df.shape[0]))
    bnf_codes_df['bnfcode'] = 'BNF_' + bnf_codes_df['bnfcode']
    bnf_codes_df['description'] = bnf_codes_df['bnfcode'] + ':' + bnf_codes_df['description'].str.strip()
    to_stack = bnf_codes_df.set_index('defid', drop=True)
    bnf_dict = to_stack.stack().to_frame()
    bnf_dict['defid'] = bnf_dict.index.get_level_values(0)
    bnf_dict.rename({0: 'code'}, axis=1, inplace=True)
    bnf_dict['type'] = 'DEF'
    write_tsv(bnf_dict[['type', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION' + '\t' + 'Drug\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    add_fisrt_line(first_line, os.path.join(dict_path, set_file))
    print('DONE bnf_dics')


def create_ahdlookup_dict():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    code_folder = fixOS(cfg.code_folder)
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.ahdlookups'
    ahd_start = 1000

    ahdlookup_df = read_fwf('AHDlookups', doc_path)
    ahdlookup_df.drop_duplicates(subset=['dataname', 'lookup', 'lookupdesc'], inplace=True)
    datatypes = ahdlookup_df['dataname'].unique()
    ahd_dict = pd.DataFrame()
    ahd_dict = ahd_dict.append({'defid': 0, 'code': 'EMPTY_THIN_FIELD'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 1, 'code': 'Y'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 2, 'code': 'N'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 3, 'code': '@Y'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 4, 'code': '@N'}, ignore_index=True)
    # Diet codes that not found in AHDlookup but found in the data
    ahd_dict = ahd_dict.append({'defid': 10, 'code': 'DIE003'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 11, 'code': 'DIE004'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 12, 'code': 'DIE005'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 13, 'code': 'DIE006'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 14, 'code': 'DIE007'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 15, 'code': 'DIE008'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 16, 'code': 'DIE009'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 17, 'code': 'DIE010'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 17, 'code': 'DIE011'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 19, 'code': 'DIE012'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 20, 'code': 'DIE013'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 21, 'code': 'DIE014'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 22, 'code': 'DIE015'}, ignore_index=True)

    ahd_dict = ahd_dict.append({'defid': 25, 'code': 'AMA005'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 26, 'code': 'AMA006'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 27, 'code': 'AMA007'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 28, 'code': 'AMA008'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 29, 'code': 'AMA009'}, ignore_index=True)

    ahd_dict = ahd_dict.append({'defid': 30, 'code': 'AAR007'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 31, 'code': 'AAR008'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 32, 'code': 'AAR009'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 33, 'code': 'AAR010'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 34, 'code': 'AAR011'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 35, 'code': 'AAR012'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 36, 'code': 'AAR013'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 37, 'code': 'AAR014'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 38, 'code': 'AAR015'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 39, 'code': 'AAR016'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 40, 'code': 'AAR017'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 41, 'code': 'AAR018'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 42, 'code': 'AAR019'}, ignore_index=True)

    ahd_dict = ahd_dict.append({'defid': 43, 'code': 'GMP005'}, ignore_index=True)

    ahd_dict = ahd_dict.append({'defid': 44, 'code': 'RES007'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 45, 'code': 'RES008'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 46, 'code': 'RES009'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 47, 'code': 'RES010'}, ignore_index=True)
    ahd_dict = ahd_dict.append({'defid': 48, 'code': 'RES011'}, ignore_index=True)

    for dt in datatypes:
        dt_df = ahdlookup_df[ahdlookup_df['dataname'] == dt].copy()
        if dt == 'CHS':
            descs = dt_df['lookupdesc'].unique()
            dt_dict = pd.DataFrame()
            for desc in descs:
                desc_df = dt_df[dt_df['lookupdesc'] == desc]
                for i, r in desc_df.iterrows():
                    code1 = dt+':' + r['lookup']
                    dt_dict = dt_dict.append({'defid': ahd_start, 'code': code1}, ignore_index=True)
                    dt_dict = dt_dict.append({'defid': ahd_start, 'code': code1 + ':' + r['lookupdesc'].strip()}, ignore_index=True)
                code = code1[-1]
                dt_dict = dt_dict.append({'defid': ahd_start, 'code': dt+str(code)}, ignore_index=True)
                ahd_start += 1
        else:
            dt_df = dt_df.assign(defid=range(ahd_start, ahd_start + dt_df.shape[0]))
            dt_df['lookup'] = dt+':' + dt_df['lookup']
            dt_df['lookupdesc'] = dt_df['lookup'] + ':' + dt_df['lookupdesc'].str.strip()
            ahd_start += dt_df.shape[0]
            to_stack = dt_df[['lookup', 'lookupdesc', 'defid']].set_index('defid', drop=True)
            dt_dict = to_stack.stack().to_frame()
            dt_dict['defid'] = dt_dict.index.get_level_values(0)
            dt_dict.rename({0: 'code'}, axis=1, inplace=True)
        ahd_dict = ahd_dict.append(dt_dict, ignore_index=True)

    ##
    missing_codes = [{'defid': 35000, 'code': '@A'},
                      {'defid': 35000, 'code': 'FECAL_AND_COLONOSCOPY_UNKNOWN_FLAGS_UNKNOWN'},
                      {'defid': 35001, 'code': '@H'},
                      {'defid': 35001, 'code': 'FECAL_AND_COLONOSCOPY_UNKNOWN_FLAGS_UNKNOWN_  # 2'},
                      {'defid': 35002, 'code': '@L'},
                      {'defid': 35002, 'code': 'FECAL_AND_COLONOSCOPY_UNKNOWN_FLAGS_UNKNOWN_  # 3'},
                      {'defid': 35003, 'code': '@PA'},
                      {'defid': 35003, 'code': 'FECAL_AND_COLONOSCOPY_UNKNOWN_FLAGS_UNKNOWN_  # 4'},
                      {'defid': 35004, 'code': 'Report Scope'},
                      {'defid': 35004, 'code': 'FECAL_AND_COLONOSCOPY_UNKNOWN_FLAGS_UNKNOWN_  # 5'},
                      {'defid': 35005, 'code': 'Return to the'},
                      {'defid': 35005, 'code': 'FECAL_AND_COLONOSCOPY_UNKNOWN_FLAGS_UNKNOWN_  # 6'},
                      {'defid': 35006, 'code': '@HH'},
                      {'defid': 35007, 'code': 'Hyperandrogen'}]

    ahd_dict = ahd_dict.append(missing_codes, ignore_index=True)
    ##
    ahd_dict['type'] = 'DEF'
    ahd_dict['defid'] = ahd_dict['defid'].astype(int)
    ### Manula sditional definitions for regisries
    reg_codes = [{'type': 'DEF', 'defid': 100000, 'code': 'Urine_dipstick_for_protein_normal'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_normal', 'code': 'EMPTY_THIN_FIELD'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_normal', 'code': 'QUA:QUA001'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_normal', 'code': 'QUA:QUA002'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_normal', 'code': 'QUA:QUA006'},
                 {'type': 'DEF', 'defid': 100001, 'code': 'Urine_dipstick_for_protein_medium'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_medium', 'code': 'QUA:QUA003'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_medium', 'code': 'QUA:QUA004'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_medium', 'code': 'QUA:QUA007'},
                 {'type': 'DEF', 'defid': 100002, 'code': 'Urine_dipstick_for_protein_severe'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_severe', 'code': 'QUA:QUA005'},
                 {'type': 'SET', 'defid': 'Urine_dipstick_for_protein_severe', 'code': 'QUA:QUA008'},
                 {'type': 'DEF', 'defid': 100010, 'code': 'Urinalysis_Protein_normal'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_normal', 'code': 'EMPTY_THIN_FIELD'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_normal', 'code': 'QUA:QUA001'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_normal', 'code': 'QUA:QUA002'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_normal', 'code': 'QUA:QUA006'},
                 {'type': 'DEF', 'defid': 100011, 'code': 'Urinalysis_Protein_medium'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_medium', 'code': 'QUA:QUA003'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_medium', 'code': 'QUA:QUA004'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_medium', 'code': 'QUA:QUA007'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_medium', 'code': 'QUA:QUA008'},
                 {'type': 'DEF', 'defid': 100012, 'code': 'Urinalysis_Protein_severe'},
                 {'type': 'SET', 'defid': 'Urinalysis_Protein_severe', 'code': 'QUA:QUA005'}]
    ahd_dict = ahd_dict.append(reg_codes, ignore_index=True)
    #####

    write_tsv(ahd_dict[['type', 'defid', 'code']], dict_path, dict_file)


    #non_numeric_path = os.path.join(out_folder, 'NonNumericSignals')
    #signals_files = os.listdir(non_numeric_path)
    thin_map = read_tsv('thin_signal_mapping.csv', code_folder, header=0)
    signals_files = thin_map[(thin_map['type'] == 'string') &
                             (thin_map['signal'] != 'Cancer_Location') &
                             (thin_map['signal'] != 'PRAC') &
                             (thin_map['signal'] != 'Drug')]['signal'].values


    first_line = 'SECTION' + '\t' + ",".join(signals_files) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE create_ahdlookup_dict')


def create_readcode_dict():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.read_codes'
    rc_start = 100000
    group_start = 250000

    readcode_df = read_fwf('Readcodes', doc_path)

    # Crate Readcodes def files
    rc_df_df = readcode_df.copy()
    rc_df_df = rc_df_df.assign(defid=range(rc_start, rc_start + rc_df_df.shape[0]))
    rc_df_df['description'] = rc_df_df['medcode'] + ':' + rc_df_df['description'].str.replace(' ', '_')
    to_stack = rc_df_df.set_index('defid', drop=True)
    rc_dict = to_stack.stack().to_frame()
    rc_dict['defid'] = rc_dict.index.get_level_values(0)
    rc_dict.rename({0: 'code'}, axis=1, inplace=True)


    # Create GROUP defs
    rc_gr_df = readcode_df.copy()
    rc_gr_df['description'] = 'GROUP:' + rc_gr_df['medcode'] + ':' +rc_gr_df['description'].str.replace(' ', '_').str.strip()
    rc_gr_df['medcode'] = 'G_' + rc_gr_df['medcode'].str[:5]

    lists = rc_gr_df.groupby(['medcode']).agg(lambda x: list(set(x.tolist())))
    rc_gr_df.drop('description', axis=1, inplace=True)
    rc_gr_df = rc_gr_df.groupby('medcode').first()
    to_gr_dict = rc_gr_df.merge(lists, left_index=True, right_index=True)
    to_gr_dict.reset_index(drop=False, inplace=True)
    to_gr_dict['list'] = to_gr_dict.apply(lambda x: [x['medcode']] + x['description'], axis=1)
    to_gr_dict = to_gr_dict.assign(defid=range(group_start, group_start + to_gr_dict.shape[0]))

    to_stack = to_gr_dict[['defid', 'list']].set_index('defid', append=True)
    def_dict = to_stack['list'].apply(pd.Series).stack().reset_index(level=[0, 2], drop=True).reset_index()
    def_dict.rename({0: 'code'}, axis=1, inplace=True)

    rc_dict = pd.concat([rc_dict, def_dict], sort=False)
    rc_dict['type'] = 'DEF'
    write_tsv(rc_dict[['type', 'defid', 'code']], dict_path, dict_file)

    # Set from Readcodes hierarchy
    set_dict_hier = pd.DataFrame()
    for _, rc in readcode_df.iterrows():
        val = rc['medcode'][:5]
        for inn in [s for s in readcode_df['medcode'].values if s.startswith(val)]:
            set_dict_hier = set_dict_hier.append({'outter': val, 'inner': inn}, ignore_index=True)
    set_dict_hier['outter'] = 'G_' + set_dict_hier['outter']

    set_build = to_gr_dict[['medcode']].copy()
    set_build['medcode_strip'] = set_build['medcode'].str.replace('.', '')
    set_build['medcode_strip_short'] = set_build['medcode_strip'].str[:-1]
    set_build['medcode_strip_short_dot'] = set_build['medcode_strip_short'].str.pad(width=7, side='right', fillchar='.')
    mc5 = set_build['medcode']
    set_build['set'] = set_build['medcode_strip_short_dot'].isin(mc5)
    set_build.rename(columns={'medcode_strip_short_dot': 'outter', 'medcode': 'inner'}, inplace=True)
    set_build = set_build[set_build['set'] == True][['outter', 'inner']]
    set_dict_hier = pd.concat([set_dict_hier, set_build])

    set_dict_hier['type'] = 'SET'
    write_tsv(set_dict_hier[['type', 'outter', 'inner']], dict_path, dict_file)

    #raedcodes_path = os.path.join(out_folder, 'Readcode')
    signals_files = ['Labs', 'RC', 'RC_Admin', 'RC_Demographic', 'RC_Diagnosis', 'RC_Diagnostic_Procedures', 'RC_History', 'RC_Injuries', 'RC_Procedures', 'RC_Radiology']
    first_line = 'SECTION' + '\t' + ",".join(signals_files) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))

    print('DONE create_readcode_dict')


def create_prac_dict():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.prac'
    det_file = 'dict.prac_set'
    # prac_start = 0

    prac_df = read_fwf('THINprac', doc_path)
    prac_df['def'] = 'DEF'
    prac_df['medialid'] = prac_df.index + 1
    prac_df['prac'] = 'PRAC_' + prac_df['prac']
    write_tsv(prac_df[['def', 'medialid', 'prac']], dict_path, dict_file)
    add_fisrt_line('DEF\t0\tPRAC\n', os.path.join(dict_path, dict_file))
    prac_df['set'] = 'SET'
    prac_df['const'] = 'PRAC'
    write_tsv(prac_df[['set', 'const', 'prac']], dict_path, det_file)
    first_line = 'SECTION' + '\t' + 'PRAC\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    add_fisrt_line(first_line, os.path.join(dict_path, det_file))
    print(' DONE create_prac_dict')


def craate_rc_icd10_map():
    cfg = Configuration()
    doc_path = fixOS(cfg.doc_source_path)
    out_folder = fixOS(cfg.work_path)
    mapping_folder = 'W:\\Data\\Mapping\\DMWB\\'
    code_folder = fixOS(cfg.code_folder)
    ontology_folder = os.path.join(code_folder, '..\\..\\DictUtils\\Ontologies\\')
    dict_path = os.path.join(out_folder, 'dicts')
    if not (os.path.exists(doc_path)):
        raise NameError('config error - doc_apth don''t exists')
    if not (os.path.exists(out_folder)):
        raise NameError('config error - out_path don''t exists')
    dict_file = 'dict.rc_icd_set'

    thin_readcode_df = read_fwf('Readcodes', doc_path)
    thin_readcode_df = thin_readcode_df[['medcode', 'description']]
    thin_readcode_df['RC5'] = thin_readcode_df['medcode'].str[0:5]  # Map file map 5 digit RC codes

    readcode_snomed_map = os.path.join(mapping_folder, 'CTV3SCTMAP.csv')
    readcode_snomed_df = pd.read_csv(readcode_snomed_map, names=['RCID', 'RCTERM', 'SMCODEID', 'SMDECID', 'MAPTYPE', 'ASSURED'], dtype={'SMCODEID': str})
    readcode_snomed_df = readcode_snomed_df[['RCID', 'SMCODEID']]

    icd_snomed_map = os.path.join(mapping_folder, 'ICDSCTMAP.csv')
    icd_snomed_df = pd.read_csv(icd_snomed_map, names=['ICDID', 'STUI', 'SMCODEID', 'SMDECID', 'MAPTYPE', 'ASSURED'], dtype={'SMCODEID': str})
    icd_snomed_df = icd_snomed_df[['ICDID', 'SMCODEID']]

    icd_file = os.path.join(mapping_folder, 'ICD.csv')
    icd_df = pd.read_csv(icd_file, names=['ICDID', 'ICDDESC'])
    icd_snomed_df = icd_snomed_df.merge(icd_df, on='ICDID')

    thin_rc_map_df = thin_readcode_df.merge(readcode_snomed_df, left_on='RC5', right_on='RCID')
    map_df = icd_snomed_df.merge(thin_rc_map_df, on='SMCODEID')

    map_df = map_df[['RCID', 'ICDID']].drop_duplicates()
    map_df['set'] = 'SET'
    map_df['ICDID'] = 'ICD10_CODE:' + map_df['ICDID']
    map_df['RCID'] = 'G_' + map_df['RCID']
    write_tsv(map_df[['set', 'ICDID', 'RCID']], dict_path, dict_file)
    signals_files = ['RC_Admin', 'RC_Demographic', 'RC_Diagnosis', 'RC_Diagnostic_Procedures', 'RC_History',
                     'RC_Injuries', 'RC_Procedures', 'RC_Radiology', 'RC']
    first_line = 'SECTION' + '\t' + ",".join(signals_files) + '\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    icd10_def = os.path.join(ontology_folder, 'ICD10\\dicts\\', 'dict.icd10')
    copy(icd10_def, dict_path)
    icd10_def = os.path.join(ontology_folder, 'ICD10\\dicts\\', 'dict.set_icd10')
    copy(icd10_def, dict_path)

    add_fisrt_line(first_line, os.path.join(dict_path, 'dict.icd10'))
    add_fisrt_line(first_line, os.path.join(dict_path, 'dict.set_icd10'))

    icds_in_map = map_df['ICDID'].unique()
    icd_dict = read_tsv('dict.icd10', dict_path, names=['def', 'num', 'code'])
    for icd in icds_in_map:
        if icd not in icd_dict['code'].values:
            print('Missing ICD Code ' + icd)


    #print(map_df)

def smoking_status_dict():
    cfg = Configuration()
    out_folder = fixOS(cfg.work_path)
    dict_path = os.path.join(out_folder, 'dicts')
    dict_file = 'dict.smoking_status'
    dict_list = [{'defid': 1, 'code': 1},
                 {'defid': 1, 'code': 'Current'},
                 {'defid': 2, 'code': 2},
                 {'defid': 2, 'code': 'Former'},
                 {'defid': 3, 'code': 3},
                 {'defid': 3, 'code': 'Never'},
                 {'defid': 4, 'code': 4},
                 {'defid': 4, 'code': 'Unknown'}]
    dict_df = pd.DataFrame(dict_list)
    dict_df['type'] = 'DEF'
    write_tsv(dict_df[['type', 'defid', 'code']], dict_path, dict_file)
    first_line = 'SECTION\tSmoking_Status\n'
    add_fisrt_line(first_line, os.path.join(dict_path, dict_file))
    print('DONE smoking_status dict')


def create_drug_dicts():
    drug_dicts()
    atc_dicts()
    bnf_dics()


if __name__ == '__main__':
    create_drug_dicts()
    create_ahdlookup_dict()
    create_readcode_dict()
    create_prac_dict()
    craate_rc_icd10_map()
    detailed_drug_dict()
    smoking_status_dict()
