import pandas as pd
import numpy as np


def prep_sig_ranges_OLD(sig_df, levels, suff):
    sig_df = sig_df[sig_df['val'] > 0]
    sig_df.loc[:, 'level'] = 0
    for i in range(len(levels)):
        sig_df.loc[sig_df['val'] > levels[i], 'level'] = i+1

    cond_lvl = (sig_df['level'] <= sig_df['level'].shift(1))
    cond_pid = (sig_df['pid'] == sig_df['pid'].shift(1))
    while sig_df[cond_lvl & cond_pid].shape[0] > 0:
        # glu_sig.loc[cond_lvl & cond_pid, 'level'] = np.nan
        # glu_sig['level'].ffill(inplace=True)
        sig_df.loc[cond_lvl & cond_pid, 'level'] = sig_df['level'].shift(1)
        cond_lvl = (sig_df['level'] < sig_df['level'].shift(1))
        cond_pid = (sig_df['pid'] == sig_df['pid'].shift(1))
        print(sig_df[cond_lvl & cond_pid].shape[0])

    sig_df.loc[:, 'block'] = ((sig_df['level'].shift(1) != sig_df['level']) |
                              (sig_df['pid'] != sig_df['pid'].shift(1))).astype(int).cumsum()
    grp = sig_df.groupby('block')
    level = grp['level'].first().rename('level')
    cnt = grp['level'].count().rename('count_'+suff)
    first = grp['date'].first().rename('start_date_'+suff)
    last = grp['date'].last().rename('end_date+'+suff)
    pid = grp['pid'].first()
    range_df = pd.concat([pid, first, last, level, cnt], axis=1)
    return range_df


def prep_ranges(event_df):
    cond_lvl = (event_df['level'] <= event_df['level'].shift(1))
    cond_pid = (event_df['pid'] == event_df['pid'].shift(1))
    while event_df[cond_lvl & cond_pid].shape[0] > 0:
        # glu_sig.loc[cond_lvl & cond_pid, 'level'] = np.nan
        # glu_sig['level'].ffill(inplace=True)
        event_df.loc[cond_lvl & cond_pid, 'level'] = event_df['level'].shift(1)
        cond_lvl = (event_df['level'] < event_df['level'].shift(1))
        cond_pid = (event_df['pid'] == event_df['pid'].shift(1))
        print(event_df[cond_lvl & cond_pid].shape[0])

    event_df.loc[:, 'block'] = ((event_df['level'].shift(1) != event_df['level']) |
                              (event_df['pid'] != event_df['pid'].shift(1))).astype(int).cumsum()
    grp = event_df.groupby('block')
    level = grp['level'].first().rename('level')
    #cnt = grp['level'].count().rename('count')
    first = grp['date'].first().rename('start_date')
    last = grp['date'].last().rename('end_date')
    pid = grp['pid'].first()
    range_df = pd.concat([pid, first, last, level.astype(int)], axis=1)
    return range_df


def prep_sig_levels(sig_df, levels):
    for i in range(len(levels)):
        sig_df.loc[sig_df['val'] > levels[i], 'level'] = i
    sig_df.dropna(how='any', inplace=True)


def fix_end_date(g):
    return g['end_date'] if g.shape[0] == 1 else g.shift(-1)['start_date']

def win_max(g):
    return g.apply(lambda r: g[(g['date'] >= r['date'] - 20000) & (g['date'] < r['date'])]['level'].max(), axis=1)
    #print(g)


def get_all_diabetes_reg(glu_sig, hba1c_sig, drugs=None, diags=None):
    glu_levels = [0.01, 100-0.01, 126-0.01, 200-0.01]
    prep_sig_levels(glu_sig, glu_levels)

    #glu_ranges = prep_sig_ranges(glu_sig, glu_levels, 'glu')

    hba_levels = [0.01, 5.7-0.01, 6.5-0.01]
    prep_sig_levels(hba1c_sig, hba_levels)
    #hba_ranges = prep_sig_ranges(hba1c_sig, hba_levels, 'hba')

    cols = ['pid', 'date', 'val', 'level']
    con_dfs = [glu_sig[cols], hba1c_sig[cols]]

    if drugs is not None:
        drugs.loc[:, 'level'] = 3
        con_dfs.append(drugs[cols])

    if diags is not None:
        diags.drop_duplicates(subset='pid', keep='first', inplace=True)
        diags.loc[:, 'level'] = 2
        con_dfs.append(diags[cols])

    print('call to merge signals')
    all_events = pd.concat(con_dfs)
    all_events.sort_values(by=['pid', 'date'], inplace=True)
    # save the max in 2 years back window - to mark what can be removed
    res = all_events.groupby('pid').apply(lambda x: win_max(x))
    all_events['max2y'] = res.values
    #all_events['max2y'] = all_events.apply(lambda r: all_events[(all_events['pid'] == r['pid']) & (all_events['date'] >= r['date']-20000) & (all_events['date'] < r['date'])]['level'].max(), axis=1)
    # all_events['max2y'] = all_events.apply(lambda r: all_events[(all_events['pid'] == r['pid']) & (all_events['date'] > r['date']) & (all_events['date'] <= r['date']+20000)]['level'].max(), axis=1)

    # Mark with -1 all the fisrt level2 that has level 2 immidetly after - to be remove later
    all_events.loc[(all_events['level'] == 2) &
                   ((all_events['level'].shift(1) != 2) &
                   (all_events['max2y'] < 2) | (all_events['max2y'].isnull())) &
                   (all_events['pid'] == all_events['pid'].shift(1)) &
                   (all_events['pid'] == all_events['pid'].shift(-1)), 'level2mark'] = -1
    # for pid with first test as 2
    all_events.loc[(all_events['level'] == 2) &
                   (all_events['max2y'].isnull()) &
                   (all_events['pid'] != all_events['pid'].shift(1)) &
                   (all_events['pid'] == all_events['pid'].shift(-1)), 'level2mark'] = -1

    all_events = all_events[all_events['level2mark'] != -1]
    all_events.loc[all_events['level'] == 3, 'level'] = 2
    all_events.reset_index(drop=True, inplace=True)
    print('prepare ranges')
    ranges = prep_ranges(all_events)
    res = ranges.groupby('pid').apply(lambda x: fix_end_date(x))

    ranges['fixed_end'] = res.values
    ranges.loc[ranges['fixed_end'].notnull(), 'end_date'] = ranges[ranges['fixed_end'].notnull()]['fixed_end'].astype(int)

    return ranges


if __name__ == '__main__':
    glu = pd.read_csv('X:\\Thin_2018_Loading\\temp\\glucose_sig')
    #glu=None
    hba1c = pd.read_csv('X:\\Thin_2018_Loading\\temp\\hba1c_sig')
    #hba1c=None
    drugs = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_drug_diabetes.csv')
    #drugs=None
    rcs = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_rc_diabetes.csv')
    #rcs = None
    ranges_df = get_all_diabetes_reg(glu, hba1c, drugs, rcs)
    ranges_df['sig'] = 'DM_Registry'
    ranges_df[['pid', 'sig', 'start_date', 'end_date', 'level']].to_csv('W:\\AlgoMarkers\\Pre2D\\pre2d_thin18\\diabetes.DM_Registry_python', sep='\t', index=False, header=False)




