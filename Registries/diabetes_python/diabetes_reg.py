import pandas as pd
import numpy as np
import os


def prep_ranges(event_df):
    event_df.loc[:, 'block'] = ((event_df['level'].shift(1) != event_df['level']) |
                              (event_df['pid'] != event_df['pid'].shift(1))).astype(int).cumsum()
    grp = event_df.groupby('block')
    level = grp['level'].first().rename('level')
    #cnt = grp['level'].count().rename('count')
    first = grp['date'].first().rename('start_date')
    last = grp['date'].last().rename('end_date')
    pid = grp['pid'].first()
    range_df = pd.concat([pid, first, last, level.astype(int)], axis=1)

    #res = range_df.groupby('pid').apply(lambda x: fix_end_date(x))
    #range_df['fixed_end'] = res.values
    #range_df.loc[range_df['fixed_end'].notnull(), 'end_date'] = range_df[range_df['fixed_end'].notnull()]['fixed_end'].astype(int)

    return range_df


def prep_sig_levels(sig_df, levels):
    for i in range(len(levels)):
        sig_df.loc[sig_df['val'] > levels[i], 'level'] = i
    sig_df.dropna(how='any', inplace=True)


def fix_end_date(g):
    return g['end_date'] if g.shape[0] == 1 else g.shift(-1)['start_date']


def win_max_roll(g):
    #tmp = g.copy()
    #if (g.name&1000) == 0:
    #print(g.name)
    res = g.set_index('real_date').rolling('730D')['level'].max().shift(1)
    g['max2y'] = res.values
    g.loc[(g['level'] == 2) &
          (g['level'].shift(1) != 2) &
          ((g['max2y'] < 2) | (g['max2y'].isnull())), 'level2mark'] = -1
    cond = (g['level2mark'] == -1) & (g['source'] == 'diag') & ((g['max2y'] < 2) | (g['max2y'].isnull()))
    g.loc[cond, 'level'] = 1
    g.loc[cond, 'level2mark'] = -2
    g = g[g['level2mark'] != -1]
    g.loc[g['level'] == 3, 'level'] = 2
    res = g.set_index('real_date').expanding()['level'].max()
    g['level'] = res.values
    return g


def get_all_diabetes_reg(glu_sig, hba1c_sig, drugs=None, diags=None):
    glu_levels = [0.01, 100-0.01, 126-0.01, 200-0.01]
    prep_sig_levels(glu_sig, glu_levels)
    glu_sig['source'] = 'glu'

    hba_levels = [0.01, 5.7-0.01, 6.5-0.01]
    prep_sig_levels(hba1c_sig, hba_levels)
    hba1c_sig['source'] = 'hba1c'

    cols = ['pid', 'date', 'val', 'level', 'source']
    con_dfs = [glu_sig[cols], hba1c_sig[cols]]

    if drugs is not None:
        drugs.loc[:, 'level'] = 3
        drugs['source'] = 'drug'
        con_dfs.append(drugs[cols])

    if diags is not None:
        diags.drop_duplicates(subset='pid', keep='first', inplace=True)
        diags.loc[:, 'level'] = 2
        diags['source'] = 'diag'
        con_dfs.append(diags[cols])

    print('prepare full list')
    all_events = pd.concat(con_dfs)
    all_events['real_date'] = pd.to_datetime(all_events['date'], format='%Y%m%d', errors='coerce')
    all_events = all_events[all_events['real_date'].notnull()]
    all_events.sort_values(by=['pid', 'date', 'level'], ascending=[True, True, False], inplace=True)
    all_events.drop_duplicates(subset=['pid', 'real_date'], inplace=True)
    #all_events = all_events[all_events['pid'] >= 5000029]
    # save the max in 2 years back window - to mark what can be removed
    print('proccess pids (groupby)')
    all_events = all_events.groupby('pid').apply(lambda x: win_max_roll(x))
    all_events['level'] = all_events['level'].astype(int)
    all_events.reset_index(drop=True, inplace=True)
    return all_events[['pid', 'date', 'val', 'level', 'source']]


def fix_start_end(ranges, starts, sdate_field, ends, edate_field):
    ranges = ranges.merge(starts, how='left', on='pid')
    cond1 = (ranges['level'] == 0) & (ranges[sdate_field].notnull()) & (ranges['start_date'] > ranges[sdate_field])
    ranges.loc[cond1, 'start_date'] = ranges[cond1][sdate_field].astype(int)
    ranges.drop(columns=sdate_field, inplace=True)
    ranges = ranges.merge(ends, how='left', on='pid')
    cond2 = (ranges['level'] == 2) & (ranges[edate_field].notnull()) & (ranges['end_date'] < ranges[edate_field])
    ranges.loc[cond2, 'end_date'] = ranges[cond2][edate_field].astype(int)
    ranges.drop(columns=edate_field, inplace=True)
    return ranges


if __name__ == '__main__':
    all_events_file = 'W:\\AlgoMarkers\\Pre2D\\pre2d_thin18\\pre2d.allevents'
    final_file = 'W:\\AlgoMarkers\\Pre2D\\pre2d_thin18\\diabetes.DM_Registry_python'
    cols = ['pid', 'sig', 'start_date', 'end_date', 'level']

    if os.path.exists(all_events_file):
        print('reading events file')
        events_df = pd.read_csv(all_events_file, sep='\t', nrows=10000)
    else:
        start_df = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_start_dates')
        glu = pd.read_csv('X:\\Thin_2018_Loading\\temp\\glucose_sig')
        #glu=None
        hba1c = pd.read_csv('X:\\Thin_2018_Loading\\temp\\hba1c_sig')
        #hba1c=None
        drugs = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_drug_diabetes.csv')
        #drugs=None
        rcs = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_rc_diabetes.csv')
        #rcs = None
        step = 1000000
        pids = start_df['pid'].unique().tolist()
        print(str(len(pids)) + ' pids')
        for i in range(0, len(pids), step):
            print(i, i + step)
            curr_pids = pids[i:i + step]
            curr_glu = glu[glu['pid'].isin(curr_pids)].copy()
            curr_hba1c = hba1c[hba1c['pid'].isin(curr_pids)].copy()
            curr_drugs = drugs[drugs['pid'].isin(curr_pids)].copy()
            curr_rcs = rcs[rcs['pid'].isin(curr_pids)].copy()
            events_df = get_all_diabetes_reg(curr_glu, curr_hba1c, curr_drugs, curr_rcs)
            if os.path.exists(all_events_file):
                events_df.to_csv(all_events_file, sep='\t', index=False, mode='a', header=False)
            else:
                events_df.to_csv(all_events_file, sep='\t', index=False, mode='a')

    ranges_df = prep_ranges(events_df)
    ranges_df['sig'] = 'DM_Registry'

    start_df = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_start_dates')
    end_df = pd.read_csv('X:\\Thin_2018_Loading\\temp\\thin_end_dates')
    ranges_df = fix_start_end(ranges_df, start_df, 'val', end_df, 'val')
    #ranges_df[cols].to_csv(final_file, sep='\t', index=False, header=False)


