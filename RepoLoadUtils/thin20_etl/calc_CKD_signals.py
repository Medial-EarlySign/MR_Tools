import os
import sys
import pandas as pd
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from utils import write_tsv, fixOS
from unit_converts import round_ser
from Configuration import Configuration
import medpython as med


Urine_Microalbumin_levels = {'A1': (0, 30), 'A2': (30, 300), 'A3': (300, 100000)}
UrineAlbumin_levels = {'A1': (0, 30), 'A2': (30, 300), 'A3': (300, 100000)}
UrineTotalProtein_levels = {'A1': (0, 0.15), 'A2': (0.15, 0.6), 'A3': (0.6, 100000)}
Urine_Protein_Creatinine_levels = {'A1': (0, 17), 'A2': (17, 57), 'A3': (57, 100000)}
UrineAlbumin_over_Creatinine_levels = {'A1': (0, 3.5), 'A2': (3.5, 30), 'A3': (30, 100000)}
dipstick_for_protein_levels = {'A1': ['QUA:QUA000', 'QUA:QUA001', 'QUA:QUA002', 'QUA:QUA006'],
                               'A2':  ['QUA:QUA003', 'QUA:QUA004', 'QUA:QUA007'],
                               'A3': ['QUA:QUA005', 'QUA:QUA008']}

'''
Urine_Microalbumin_levels = {'0': (0, 30), '1': (30, 100), '2': (100, 200), '3': (200,300), '4': (300, 100000)}
UrineAlbumin_levels = {'0': (0, 30), '1': (30, 100), '2': (100, 200), '3': (200,300), '4': (300, 100000)}
UrineTotalProtein_levels = {'0': (0, 0.15), '1': (0.15, 0.3), '2': (0.3, 0.45), '3': (0.45, 0.6), '4': (0.6, 100000)}
Urine_Protein_Creatinine_levels = {'0': (0, 17), '1': (17, 34), '2': (34, 68), '3': (68, 113), '4': (113, 100000)}
#Urine_Protein_Creatinine_levels = {'0': (0, 15), '1': (15, 30), '2': (30, 60), '3': (60, 100), '4': (100, 100000)}
UrineAlbumin_over_Creatinine_levels = {'0': (0, 3.5), '1': (3.5, 12), '2': (12, 20), '3': (20, 27), '4': (27, 100000)}
dipstick_for_protein_levels = {'0': ['QUA:QUA000', 'QUA:QUA001', 'QUA:QUA006', 'QUA:QUA002'],
                               '1': ['QUA:QUA003', 'QUA:QUA007'],
                               '2': ['QUA:QUA004'],
                               '4': ['QUA:QUA005', 'QUA:QUA008']}
'''
# protein adjust to albu
#UrineTotalProtein_levels = {'0': (0, 0.16), '1': (0.16, 0.31), '2': (0.31, 0.45), '3': (0.45, 0.6), '4': (0.6, 100000)}

def get_numeric_sig_with_level(rep, sig, levels):
    sig_df = rep.get_sig(sig)
    sig_df.rename(columns={'val0': sig}, inplace=True)
    for lvl, limits in levels.items():
        print(lvl, limits)
        sig_df.loc[(sig_df[sig] >= limits[0]) & (sig_df[sig] < limits[1]), 'level'] = lvl
    return sig_df


def get_category_sig_with_level(rep, sig, levels):
    sig_df = rep.get_sig(sig)
    sig_df.rename(columns={'val0': sig}, inplace=True)
    for lvl, limits in levels.items():
        print(lvl, limits)
        for lm in limits:
            sig_df.loc[sig_df[sig].str.contains(lm), 'level'] = lvl
    return sig_df


def level_dict1(df1, df2):
    cfg = Configuration()
    sig1 = df1.columns[2]
    sig2 = df2.columns[2]
    if sig1==sig2:
        return
    print(sig1, sig2)
    mrg = pd.merge(df1, df2, how='outer', on=['pid', 'time0'])
    match = mrg[(mrg[sig1].notnull()) & (mrg[sig2].notnull())]
    #print(match['level_x'].value_counts(normalize=True))
    #print(match['level_y'].value_counts(normalize=True))
    conflicts = match[match['level_x'] != match['level_y']]
    #print('total')
    #print(match.shape[0], conflicts.shape[0], (conflicts.shape[0]/match.shape[0])*100)
    exw = pd.ExcelWriter(os.path.join(fixOS(cfg.work_path), 'CKD_FinalSignals', sig1 + '_' + sig2 + '.xlsx'))
    exw2 = pd.ExcelWriter(os.path.join(fixOS(cfg.work_path), 'CKD_FinalSignals', 'conf'+sig1 + '_' + sig2 + '.xlsx'))
    for i in range(1, 4):
        lvl = 'A' + str(i)
        #match_lvl = match[match['level_x'] == lvl]
        #print(match_lvl.shape)
        #match_lvl.to_excel(exw, sheet_name='level '+lvl, index=False)

        conflicts_lvl = conflicts[conflicts['level_x'] == lvl]
        conflicts_lvl.to_excel(exw2, sheet_name='level ' + lvl, index=False)
        print('level ' + lvl)
        #print(match_lvl.shape[0], conflicts_lvl.shape[0], (conflicts_lvl.shape[0] / match_lvl.shape[0]) * 100)
    exw.save()
    exw.close()
    exw2.save()
    exw2.close()


def level_dist_excel(sigs_list):
    cfg = Configuration()
    print(os.path.join(fixOS(cfg.work_path), 'CKD_FinalSignals', 'signals_level_comp.xlsx'))
    exw = pd.ExcelWriter(os.path.join(fixOS(cfg.work_path), 'CKD_FinalSignals', 'signals_level_comp.xlsx'))
    ex_df = pd.DataFrame()
    for i in range(0, len(sigs_list)):
        for j in range(0, len(sigs_list)):
            dct1 = level_dist_to_dict(sigs_list[i], sigs_list[j])
            ex_df = ex_df.append(dct1, ignore_index=True)
    print(ex_df)
    ex_df[['signal1','signal2', 'sig1_count', 'sig2_count', 'match_count', 'sig1_match', 'sig2_match', 'conflicts', 'conflicts_vc']].to_excel(exw, index=False)
    exw.save()
    exw.close()

def level_dist_to_dict(df1, df2):

    sig1 = df1.columns[2]
    sig2 = df2.columns[2]
    if sig1==sig2:
        return
    dict1 = {'signal1': sig1, 'signal2': sig2}
    mrg = pd.merge(df1, df2, how='outer', on=['pid', 'time0'])
    match = mrg[(mrg[sig1].notnull()) & (mrg[sig2].notnull())]
    match_vals = match[match['level_x'] == match['level_y']]
    conflicts = match[match['level_x'] != match['level_y']]
    dict1['sig1_count'] = df1.shape[0]
    dict1['sig2_count'] = df2.shape[0]
    dict1['match_count'] = match.shape[0]

    dict1['sig1_match'] = round((match.shape[0] / df1.shape[0]) * 100, 2)
    dict1['sig2_match'] = round((match.shape[0] / df2.shape[0]) * 100, 2)
    dict1['conflicts'] = round((conflicts.shape[0] / match.shape[0]) * 100, 2)

    conflicts.loc[:, 'conf_pair'] = conflicts['level_x'] + '_' + conflicts['level_y']
    dict1['conflicts_vc'] = str(conflicts['conf_pair'].value_counts(normalize=True))
    return dict1


def level_dict(df1, df2):
    sig1 = df1.columns[2]
    sig2 = df2.columns[2]
    if sig1==sig2:
        return
    print(sig1, sig2)
    print('================')
    mrg = pd.merge(df1, df2, how='outer', on=['pid', 'time0'])
    match = mrg[(mrg[sig1].notnull()) & (mrg[sig2].notnull())]
    match_vals = match[match['level_x'] == match['level_y']]
    conflicts = match[match['level_x'] != match['level_y']]
    print('Match count ' + str(match.shape[0]))

    df1_match = round((match.shape[0] / df1.shape[0]) * 100, 2)
    print(sig1 + ' total: ' + str(df1.shape[0]) + ' match dates ' + str(df1_match) + '%')

    df2_match = round((match.shape[0] / df2.shape[0]) * 100, 2)
    print(sig2 + ' total: ' + str(df2.shape[0]) + ' match dates ' + str(df2_match) + '%')
    print('Match values and date from match '+ str(round((match_vals.shape[0] / match.shape[0]) * 100, 2)) + '%')
    print('conflicts values on date from match ' + str(round((conflicts.shape[0] / match.shape[0]) * 100, 2)) + '%')

    #print(conflicts['level_x'].value_counts(normalize=True))
    #print(conflicts['level_y'].value_counts(normalize=True))
    conflicts.loc[:, 'conf_pair'] = conflicts['level_x'] + '_' + conflicts['level_y']
    print(conflicts['conf_pair'].value_counts(normalize=True))
    print()
    print()


def calc_proteinuria_state(rep, out_folder, save_sig = False):

    sig = 'Proteinuria_State_micro_albu'
    micrro_albu_sig = get_numeric_sig_with_level(rep, 'Urine_Microalbumin', Urine_Microalbumin_levels)
    print(micrro_albu_sig.shape[0])
    micrro_albu_sig = micrro_albu_sig[micrro_albu_sig['Urine_Microalbumin'] > 0]
    print(micrro_albu_sig.shape[0])
    if save_sig:
        micrro_albu_sig['sig'] = sig
        micrro_albu_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(micrro_albu_sig[['pid', 'sig', 'time0', 'level', 'Urine_Microalbumin']], out_folder,sig, mode='w')

    sig = 'Proteinuria_State_albu'
    albu_sig = get_numeric_sig_with_level(rep, 'UrineAlbumin', UrineAlbumin_levels)
    print(albu_sig.shape[0])
    albu_sig = albu_sig[albu_sig['UrineAlbumin'] > 0]
    print(albu_sig.shape[0])
    if save_sig:
        albu_sig['sig'] = sig
        albu_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(albu_sig[['pid', 'sig', 'time0', 'level', 'UrineAlbumin']], out_folder, sig, mode='w')


    sig = 'Proteinuria_State_prot'
    prot_sig = get_numeric_sig_with_level(rep, 'UrineTotalProtein', UrineTotalProtein_levels)
    prot_sig = prot_sig[prot_sig['UrineTotalProtein'] > 0]
    if save_sig:
        prot_sig['sig'] = sig
        prot_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(prot_sig[['pid', 'sig', 'time0', 'level', 'UrineTotalProtein']], out_folder, sig, mode='w')



    sig = 'Proteinuria_State_PCR'
    pcr_sig = get_numeric_sig_with_level(rep, 'Urine_Protein_Creatinine', Urine_Protein_Creatinine_levels)
    pcr_sig = pcr_sig[pcr_sig['Urine_Protein_Creatinine'] > 0]
    if save_sig:
        pcr_sig['sig'] = sig
        pcr_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(pcr_sig[['pid', 'sig', 'time0', 'level', 'Urine_Protein_Creatinine']], out_folder, sig, mode='w')



    sig = 'Proteinuria_State_ACR'
    acr_sig = get_numeric_sig_with_level(rep, 'UrineAlbumin_over_Creatinine', UrineAlbumin_over_Creatinine_levels)
    acr_sig = acr_sig[acr_sig['UrineAlbumin_over_Creatinine'] > 0]
    if save_sig:
        acr_sig['sig'] = sig
        acr_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(acr_sig[['pid', 'sig', 'time0', 'level', 'UrineAlbumin_over_Creatinine']], out_folder, sig, mode='w')

    sig = 'Proteinuria_State_dipstick_protein'
    stick_sig = get_category_sig_with_level(rep, 'Urine_dipstick_for_protein', dipstick_for_protein_levels)
    if save_sig:
        stick_sig['sig'] = sig
        stick_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(stick_sig[['pid', 'sig', 'time0', 'level', 'Urine_dipstick_for_protein']], out_folder, sig, mode='w')

    sig = 'Proteinuria_State_urinalysis_protein'
    urin_sig = get_category_sig_with_level(rep, 'Urinalysis_Protein', dipstick_for_protein_levels)
    if save_sig:
        urin_sig['sig'] = sig
        urin_sig.sort_values(['pid', 'time0'], inplace=True)
        write_tsv(urin_sig[['pid', 'sig', 'time0', 'level', 'Urinalysis_Protein']], out_folder, sig, mode='w')

    sigs = [albu_sig, micrro_albu_sig, prot_sig, pcr_sig, acr_sig, stick_sig, urin_sig]
    level_dist_excel(sigs)
    #s2 = urin_sig
    #for s1 in sigs:
    #    level_dict(s1, s2)

    for i in range(0, len(sigs)):
        for j in range(i+1, len(sigs)):
            level_dict1(sigs[i], sigs[j])


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()
    rep.read_all(cfg.repo, [], ['GENDER'])
    out_folder = os.path.join(fixOS(cfg.work_path), 'CKD_FinalSignals')

    calc_proteinuria_state(rep, out_folder)
