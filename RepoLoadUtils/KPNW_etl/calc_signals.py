import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, write_tsv
from signals_plots import numeric_plots, category_plots
sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med


def read_signal_file(sig_file):
    f = open(sig_file)
    lines = f.readlines()
    sigs = []
    for ln in lines:
        cells = ln.split('\t')
        if cells[0] != 'SIGNAL':
            continue
        if len(cells) >= 6:
            sigs.append({'signal': cells[1], 'sigid': cells[2]})
    sigs_df = pd.DataFrame(sigs)
    return sigs_df


def bmi(h, w):
    h_m2 = pow(h/100, 2)
    return round(w/h_m2, 1)


def get_sig_temp(sig):
    filename = sig+'_get_sig.txt'
    path = '/nas1/Work/Users/Tamar/kpnw_load/temp/'
    sig_df = pd.read_csv(fixOS(os.path.join(path, filename)), sep='\t')
    return sig_df


def calc_BMI(cfg, rep):
    #
    # Eeach time there is a Weight find the last Height and calc BMI
    #
    kp_rep = fixOS(cfg.repo)
    work_folder = fixOS(cfg.work_path)
    out_folder = os.path.join(work_folder, 'FinalSignals')
    rep.read_all(kp_rep, [], ['Height', 'Weight'])
    print(med.cerr())

    h_df = rep.get_sig('Height')
    #h_df = get_sig_temp('Height')
    h_df.rename(columns={'val0': 'Height'}, inplace=True)

    w_df = rep.get_sig('Weight')
    #w_df = get_sig_temp('Weight')
    w_df.rename(columns={'val0': 'Weight'}, inplace=True)

    y_df = rep.get_sig('BYEAR')
    #y_df = get_sig_temp('BYEAR')
    y_df.rename(columns={'val0': 'BYEAR'}, inplace=True)

    mrg_df = pd.merge(w_df, h_df, on=['pid', 'time0'], how='outer')
    mrg_df = mrg_df.merge(y_df, on='pid')
    mrg_df.loc[:, 'age'] = (mrg_df['time0']/10000).astype(int) - mrg_df['BYEAR']

    # If less then 18 - Weight and Height on the same day
    mrg_df = mrg_df[~((mrg_df['Height'].isnull()) & (mrg_df['age'] < 18))]

    #take the last exsiting height for each pid
    mrg_df['Height'] = mrg_df.groupby('pid')['Height'].apply(lambda x: x.ffill())
    mrg_df = mrg_df[(mrg_df['Height'].notnull()) & (mrg_df['Height'] > 0) &
                    (mrg_df['Weight'].notnull()) & (mrg_df['Weight'] > 0)]
    '''
    all_df = pd.DataFrame()
    for pid, pid_df in mrg_df.groupby('pid'):
        pid_df = pid_df[~((pid_df['Height'].isnull()) & (pid_df['age'] < 19))]
        pid_df['Height'].fillna(method='ffill', inplace=True)
        pid_df = pid_df[(pid_df['Height'].notnull()) & (pid_df['Height'] > 0) &
                        (pid_df['Weight'].notnull()) & (pid_df['Weight'] > 0)]
        all_df = all_df.append(pid_df)
    '''
    mrg_df['Height'] = pow(mrg_df['Height']/100, 2)
    #mrg_df['BMI'] = mrg_df.apply(lambda x: bmi(x['Height'], x['Weight']), axis=1)
    mrg_df['BMI'] = round(mrg_df['Weight']/mrg_df['Height'], 1)
    print(mrg_df)
    sig = 'BMI'
    mrg_df['signal'] = sig
    mrg_df.sort_values(by=['pid', 'time0'], inplace=True)

    print('Saving to file ' + sig)
    write_tsv(mrg_df[['pid', 'signal', 'time0', 'BMI']], out_folder, sig, mode='w')


def calc_missing_death(cfg, rep):
    # Find pids with no death date
    kp_rep = fixOS(cfg.repo)
    rep.read_all(kp_rep, [], ['DEATH', 'DEAD', 'MEMBERSHIP'])
    print(med.cerr())
    d_df = rep.get_sig('DEAD')
    d_df = d_df[d_df['val0'] == 1]
    print('Daeth len ' + str(d_df.shape))
    dod_df = rep.get_sig('DEATH')
    print(dod_df.shape)
    print('1) Death of 1014618: ' + str(dod_df[dod_df['pid'] == 1014618]))
    mem_df = rep.get_sig('MEMBERSHIP')
    messing = d_df.merge(dod_df, on='pid', how='left')
    print(messing.shape)
    messing = messing.merge(mem_df, on='pid', how='left')

    print(messing[messing['time0_x'].isnull()].shape)
    missing_pids = messing[(messing['time0_x'].isnull()) & messing['val0_y'].notnull()]['pid'].values.tolist()
    print(len(missing_pids))
    ####
    work_folder = fixOS(cfg.work_path)
    signals = read_signal_file(os.path.join(work_folder, 'rep_configs', 'kpnw.signals'))
    #signals = sigs_df['signal'].values
    #print(signals)
    rep.read_all(kp_rep, missing_pids, [])
    print(med.cerr())

    max_date = 19000101
    max_date_dict = {x: max_date for x in missing_pids}
    for sig in signals['signal'].values:
        print(sig)
        sig_df = rep.get_sig(sig, pids=missing_pids)
        date_field = 'time0'
        #if sig == 'MEMBERSHIP' or sig =='ADMISSION':
        #    date_field = 'date_end'
        if date_field in sig_df.columns:
            for pid in missing_pids:
                loc_max = sig_df[sig_df['pid'] == pid][date_field].max()
                if loc_max > max_date_dict[pid]:
                    max_date_dict[pid] = loc_max
        else:
            print('Signal ' + sig + 'does not have "time0" filed ' + str(sig_df.columns.tolist()))
    data = [{'pid': k, 'date': v} for k, v in max_date_dict.items()]
    max_date_df = pd.DataFrame(data=data)
    print('No date found date for ' + str(max_date_df[max_date_df['date'] == max_date].shape[0]))
    print('Date in the future for ' + str(max_date_df[max_date_df['date'] > 20210101].shape[0]))
    max_date_df = max_date_df[(max_date_df['date'] > 20080101) & (max_date_df['date'] < 20210101)]
    dod_df.rename(columns={'time0': 'date'}, inplace=True)
    print('2) Death of 1014618: ' + str(dod_df[dod_df['pid'] == 1014618]))
    dod_df = pd.concat([dod_df, max_date_df], sort=True)
    dod_df = dod_df[dod_df['date'].notnull()]
    out_folder = os.path.join(work_folder, 'FinalSignals')
    sig = 'DEATH'
    dod_df['signal'] = sig
    dod_df.sort_values(by=['pid', 'date'], inplace=True)
    print('Saving to file ' + sig)
    if os.path.exists(os.path.join(out_folder, sig)):
        os.remove(os.path.join(out_folder, sig))
    print('3) Death of 1014618: ' + str(dod_df[dod_df['pid'] == 1014618]))
    write_tsv(dod_df[['pid', 'signal', 'date']], out_folder, sig)


if __name__ == '__main__':
    cfg = Configuration()
    rep = med.PidRepository()

    #calc_BMI(cfg, rep)
    calc_missing_death(cfg, rep)
