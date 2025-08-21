import pandas as pd
import numpy as np
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS, write_tsv
sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
#barWidth = 0.15
plt.rcParams['figure.figsize'] = [15, 5]

new_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
              '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
              '#bcbd22', '#17becf']


groups = [0, 5,18,65,150]
age_group_map = {}
for j in range(1, len(groups)):
    for i in range(groups[j-1], groups[j]):
        age_group_map[i] = str(groups[j-1])+'-'+str(groups[j])
age_group_map = pd.Series(age_group_map)
age_group_map.replace({'65-150': '65+'}, inplace=True)
month_name_map = pd.Series({0: 'Aug', 1: 'Sep', 2: 'Oct', 3: 'Nov', 4: 'Dec', 5: 'Jan', 6: 'Feb', 7: 'Mar', 8: 'Apr', 9: 'May', 10: 'Jun', 11: 'Jul'})


def check_membership1(pid, vac_date, mem_df):
    if pid not in mem_df.index:
        return 2
    pid_mem = mem_df.loc[pid]
    aug1 = int(str(vac_date)[0:4] + '0801')
    for dts in zip(pid_mem['date_start'], pid_mem['date_end']):
        if dts[0] <= vac_date <= dts[1]:
            if dts[0] <= aug1 <= dts[1]:
                return 1
            else:
                return 4
    return 0


def get_membership(reg_df, mem_df):
    reg_df = reg_df.merge(mem_df[['pid', 'date_start', 'date_end']], on='pid', how='left')
    reg_df['year'] = (reg_df['date'] / 10000).astype(int)
    reg_df.loc[reg_df['date'] % 10000 < 801, 'year'] = reg_df['year'] - 1  # fix year to start at Aug1
    reg_df['aug1'] = reg_df['year'] .astype(str) + '0801'
    reg_df['aug1'] = reg_df['aug1'].astype(int)
    reg_df['member'] = 0
    # print(vacc_df)
    print(len(reg_df['pid'].unique()))
    reg_df.loc[(reg_df['date_start'] <= reg_df['date']) & (reg_df['date'] <= reg_df['date_end']) &
               (reg_df['date_start'] <= reg_df['aug1']) & (reg_df['aug1'] <= reg_df['date_end']), 'member'] = 1
    reg_df.loc[reg_df['date_start'].isnull(), 'member'] = 2
    print(reg_df['member'].value_counts())
    reg_df = reg_df[reg_df['member'] == 1]
    return reg_df[['pid', 'date', 'val']]


def membership_totals(member_df, yob_df):
    membership_df = member_df.merge(yob_df, how='left', on='pid')
    yr_list = []
    for yr in range(2008, 2020):
        aug1 = yr * 10000 + 801
        df_yr = membership_df[(membership_df['date_start'] < aug1) & (membership_df['date_end'] >= aug1)]
        df_yr['age'] = yr - df_yr['byear']
        df_yr['age_group'] = df_yr['age'].map(age_group_map)
        dict1 = df_yr.groupby('age_group')['pid'].count().to_dict()
        dict1['All'] = sum(dict1.values())
        dict1['year'] = yr
        yr_list.append(dict1)
    tot_count = pd.DataFrame(yr_list)
    tot_count.fillna(0, inplace=True)
    tot_count.set_index('year', inplace=True)
    print(tot_count)
    return tot_count


# def polt_by_year_age(df, cnt_field, title, save_file):
#     bars0_5 = df[df['age_group'] == '0-5'].set_index('year')[cnt_field]
#     bars5_18 = df[df['age_group'] == '5-18'].set_index('year')[cnt_field]
#     bars18_65 = df[df['age_group'] == '18-65'].set_index('year')[cnt_field]
#     bars65up = df[df['age_group'] == '65-150'].set_index('year')[cnt_field]
#     barall = df[df['age_group'] == 'All'].set_index('year')[cnt_field]
#
#     r1 = np.arange(len(bars0_5))
#     r2 = [x + barWidth for x in r1]
#     r3 = [x + barWidth for x in r2]
#     r4 = [x + barWidth for x in r3]
#     r5 = [x + barWidth for x in r4]
#
#     # Make the plot
#     plt.bar(r1, bars0_5,  width=barWidth, label='0-5')
#     plt.bar(r2, bars5_18, width=barWidth, edgecolor='white', label='5-18')
#     plt.bar(r3, bars18_65, width=barWidth, edgecolor='white', label='18-65')
#     plt.bar(r4, bars65up, width=barWidth, edgecolor='white', label='65+')
#     plt.bar(r5, barall, width=barWidth, edgecolor='white', label='All')
#
#     plt.title(title)
#
#     plt.xlabel('Years', fontweight='bold')
#     plt.xticks([r + barWidth for r in range(len(bars0_5))], df['year'].unique().tolist())
#
#     plt.legend()
#     print(save_file)
#     plt.savefig(save_file)
#     plt.close()
#     #plt.show()


def plot_bar(arr, title, xticks, save_file):
    plt.rcParams['figure.figsize'] = [7, 2]
    index = np.arange(len(xticks))
    plt.bar(index, arr)
    plt.xlabel('Months', fontweight='bold')
    plt.xticks(index, xticks)
    plt.title(title)
    print(save_file)
    plt.savefig(save_file)
    plt.close()
    #plt.show()


def plot_bar_fixed(arr, title, xlabel, save_file, print_vals=False):
    labels = [str(round(x)) + '%' for x in arr.values.tolist()]
    #arr.rename(index={'65-150': '65+'}, inplace=True)
    arr = arr.reindex(['0-5', '5-18', '18-65', '65+', 'All'])
    plt.rcParams['figure.figsize'] = [7, 2]
    index = np.arange(arr.shape[0])
    plt.bar(index, arr)
    plt.xlabel(xlabel, fontweight='bold')
    plt.xticks(index, arr.index)
    plt.title(title)
    if print_vals:
        for i in range(arr.shape[0]):
            plt.text(x=index[i] - 0.2, y=arr.values[i] - 15, s=labels[i], size=12, color='w', fontweight='bold')
    print(save_file)
    plt.savefig(save_file)
    plt.close()



def polt_by_month_level(df, cnt_field, title, ofile, grph_bars=['1', '2', '3']):
    plt.rcParams['figure.figsize'] = [5, 3]
    bars = {}
    for k in grph_bars:
        bars[k] = df[df['val'] == k].set_index('month')[cnt_field]
    #bars['1'] = df[df['val'] == '1'].set_index('month')[cnt_field]
    #bars['2'] = df[df['val'] == '2'].set_index('month')[cnt_field]
    #bars['3'] = df[df['val'] == '3'].set_index('month')[cnt_field]
    plot_by_year_plus(bars, title, df[df['val'] == grph_bars[0]]['month'].map(month_name_map).tolist(), ofile)


def polt_by_year_level(df, cnt_field, title, ofile, grph_bars=['1', '2', '3']):
    bars = {}
    for k in grph_bars:
        bars[k] = df[df['val'] == k].set_index('year')[cnt_field]
    plot_by_year_plus(bars, title, df['year'].unique().tolist(), ofile)


def polt_by_year_age(df, cnt_field, title, ofile):
    bars = {}
    bars['0-5'] = df[df['age_group'] == '0-5'].set_index('year')[cnt_field]
    bars['5-18'] = df[df['age_group'] == '5-18'].set_index('year')[cnt_field]
    bars['18-65'] = df[df['age_group'] == '18-65'].set_index('year')[cnt_field]
    bars['65+'] = df[df['age_group'] == '65+'].set_index('year')[cnt_field]
    bars['All'] = df[df['age_group'] == 'All'].set_index('year')[cnt_field]
    plot_by_year_plus(bars, title, df['year'].unique().tolist(), ofile)


def plot_by_year_plus(bars, title, xticks, save_file):
    barWidth = 0.15
    bar0 = list(bars.values())[0]
    num_bars = len(bars)
    if num_bars <= 3:
        barWidth = 0.30
    if num_bars == 1:
        barWidth = 0.40
    xlabel = 'Years'
    if 'Aug' in xticks:
        xlabel = 'Months'
    prev_bar = np.arange(len(bar0))
    r_list = [prev_bar]
    for i in range(1, num_bars):
        r = [x + barWidth for x in prev_bar]
        r_list.append(r)
        prev_bar = r

    # Make the plot
    for k, r in zip(bars.keys(), r_list):
        plt.bar(r, bars[k],  width=barWidth, edgecolor='white', label=k)



    plt.title(title)
    plt.xticks([r + barWidth for r in range(len(bar0))], xticks)
    plt.xlabel(xlabel, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    print(save_file)
    plt.savefig(save_file)
    plt.close()
    #plt.show()


def plot_by_ages_plus(bars, title, xticks, save_file):
    barWidth = 0.15
    bar0 = list(bars.values())[0]
    num_bars = len(bars)
    xlabel = 'Age Groups'
    prev_bar = np.arange(len(bar0))
    r_list = [prev_bar]
    for i in range(1, num_bars):
        r = [x + barWidth for x in prev_bar]
        r_list.append(r)
        prev_bar = r

    # Make the plot
    for k, r in zip(bars.keys(), r_list):
        plt.bar(r, bars[k],  width=barWidth, edgecolor='white', label=k)

    plt.title(title)
    plt.xticks([r + barWidth for r in range(len(bar0))], bar0.index)
    plt.xlabel(xlabel, fontweight='bold')
    plt.legend()
    plt.tight_layout()
    print(save_file)
    plt.savefig(save_file)
    plt.close()
    #plt.show()



def plot_level_graph(p_df, typ, level, tot_count, ofile_cnt, ofile_per):
    all_df1 = p_df.groupby('year').sum()['pid'].reset_index()
    all_df1['age_group'] = 'All'
    p_df = pd.concat([p_df, all_df1], axis=0, sort=False)
    p_df['all_count'] = p_df.apply(lambda x: tot_count.loc[x['year'], x['age_group']], axis=1)
    p_df['%'] = p_df.apply(lambda x: (x['pid'] / x['all_count'])*100 if x['all_count'] != 0 else 0, axis=1)

    polt_by_year_age(p_df, 'pid', typ + ' Tier: ' + str(level) + '. over years by age groups - Counts', ofile_cnt)
    polt_by_year_age(p_df, '%', typ + ' Tier: ' + str(level) + '. over years by age groups - % of members on Aug1', ofile_per)


def vacc_year_age(rep):
    cfg = Configuration()
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')

    yob_df = rep.get_sig('BYEAR')
    yob_df.rename(columns={'val': 'byear'}, inplace=True)
    vacc_df = rep.get_sig('Vaccination_flu')
    member_df = rep.get_sig('MEMBERSHIP')
    #mem_df = pd.concat([member_df.groupby('pid')['date_start'].apply(list), member_df.groupby('pid')['date_end'].apply(list)],
    #                   axis=1)

    tot_count = membership_totals(member_df, yob_df)

    vacc_df = get_membership(vacc_df, member_df)
    vacc_df1 = vacc_df.merge(yob_df, how='left', on='pid')
    vacc_df1['year'] = (vacc_df1['date'] / 10000).astype(int)
    vacc_df1.loc[vacc_df1['date'] % 10000 < 801, 'year'] = vacc_df1['year'] - 1  # fix yaer to start at Aug1
    vacc_df1['month'] = vacc_df1['date'].astype(str).str[4:6].astype(int) + 4
    vacc_df1['month'] = vacc_df1['month'] % 12
    vacc_df1['age'] = vacc_df1['year'] - vacc_df1['byear']

    vacc_df1['age_group'] = vacc_df1['age'].map(age_group_map)
    print(vacc_df1)

    df = vacc_df1[['pid', 'age_group', 'year']].groupby(['year', 'age_group'])['pid'].count()
    df = df.reset_index()

    all_df = df.groupby('year').sum()['pid'].reset_index()
    all_df['age_group'] = 'All'
    df = pd.concat([df, all_df], axis=0, sort=False)

    age_df = df.groupby('age_group').sum()['pid'].reset_index()

    plot_bar_fixed(age_df.set_index('age_group')['pid'], 'Vacctination by age groups', 'age groups', os.path.join(out_folder, 'vacc_by_age_group_count.jpg'))
    age_df['%'] = age_df.apply(lambda x: (x['pid'] / tot_count[x['age_group']].sum()) * 100, axis=1)
    plot_bar_fixed(age_df.set_index('age_group')['%'], 'Vacctination by age groups -  % of members on Aug1',
                   'age groups', os.path.join(out_folder, 'vacc_by_age_group_%.jpg'), print_vals=True)


    polt_by_year_age(df, 'pid', 'Vaccinations over years by age groups - Counts',
                     os.path.join(out_folder,'vacc_year_age_count.jpg'))
    df['all_count'] = df.apply(lambda x: tot_count.loc[x['year'], x['age_group']], axis=1)
    df['%'] = df.apply(lambda x: (x['pid'] / tot_count.loc[x['year'], x['age_group']])*100 if tot_count.loc[x['year'], x[
        'age_group']] != 0 else 0, axis=1)
    polt_by_year_age(df, '%', 'Vaccinations over years by age groups - % of members on Aug1',
                     os.path.join(out_folder, 'vacc_year_age_%.jpg'))


    ## By month
    for yr in range(2009, 2019):
        yr_df = vacc_df1[vacc_df1['year'] == yr]
        df_month = yr_df[['pid', 'month', 'val']].groupby(['month', 'val'])['pid'].count()
        df_month = df_month.reset_index()

        ##### fill missing entries
        for m in range(0, 12):
            if df_month[(df_month['month'] == m)].empty:
                df_month = df_month.append({'month': m, 'pid': 0}, ignore_index=True)
        df_month.sort_values(by='month', inplace=True)
        #####
        plot_bar(df_month.set_index('month')['pid'], 'Vacctination for year Aug' + str(yr) + '-Jul' + str(yr + 1),
                 df_month['month'].map(month_name_map), os.path.join(out_folder, 'vacc_by_month_'+str(yr)+'.jpg'))

    df_all = vacc_df1[['pid', 'month']].groupby(['month'])['pid'].count()
    df_all = df_all.reset_index()
    plot_bar(df_all.set_index('month')['pid'], 'Vacctination for all years', df_all['month'].map(month_name_map),
             os.path.join(out_folder, 'vacc_by_month_all.jpg'))


def flu_year_age(rep):
    cfg = Configuration()
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')
    yob_df = rep.get_sig('BYEAR')
    yob_df.rename(columns={'val': 'byear'}, inplace=True)
    flu_df = rep.get_sig('FLU_REG2')
    member_df = rep.get_sig('MEMBERSHIP')

    tot_count = membership_totals(member_df, yob_df)

    flu_df1 = get_membership(flu_df, member_df)
    flu_df1 = flu_df1.merge(yob_df, how='left', on='pid')
    flu_df1['year'] = (flu_df1['date'] / 10000).astype(int)
    flu_df1.loc[flu_df1['date'] % 10000 < 801, 'year'] = flu_df1['year'] - 1  # fix year to start at Aug1
    flu_df1['month'] = flu_df1['date'].astype(str).str[4:6].astype(int) + 4
    flu_df1['month'] = flu_df1['month'] % 12
    flu_df1['age'] = flu_df1['year'] - flu_df1['byear']
    flu_df1.drop_duplicates(subset=['pid', 'year'], keep='first', inplace=True)

    flu_df1['age_group'] = flu_df1['age'].map(age_group_map)
    # print(flu_df1)

    df = flu_df1[['pid', 'age_group', 'year']].groupby(['year', 'age_group'])['pid'].count()
    df = df.reset_index()
    plot_level_graph(df, 'Flu', 'all', tot_count, os.path.join(out_folder, 'flu_level_all_year_age_cnt.jpg'),
                     os.path.join(out_folder, 'flu_level_all_year_age_%.jpg'))

    df_lvl = flu_df1[['pid', 'age_group', 'year', 'val']].groupby(['year', 'age_group', 'val'])['pid'].count()
    df_lvl = df_lvl.reset_index()
    plot_level_graph(df_lvl[df_lvl['val'] == '1'], 'Flu', '1', tot_count, os.path.join(out_folder, 'flu_level_1_year_age_cnt.jpg'), os.path.join(out_folder, 'flu_level_1_year_age_%.jpg'))
    plot_level_graph(df_lvl[df_lvl['val'] == '2'], 'Flu', '2',  tot_count, os.path.join(out_folder, 'flu_level_2_year_age_cnt.jpg'), os.path.join(out_folder, 'flu_level_2_year_age_%.jpg'))
    plot_level_graph(df_lvl[df_lvl['val'] == '3'], 'Flu', '3', tot_count, os.path.join(out_folder, 'flu_level_3_year_age_cnt.jpg'), os.path.join(out_folder, 'flu_level_3_year_age_%.jpg'))

    flu_df2 = flu_df1.copy()
    flu_df2.loc[flu_df2['val'] == '1', 'val'] = '2'
    flu_df2 = flu_df2[['pid', 'age_group', 'year', 'val']].groupby(['year', 'age_group', 'val'])['pid'].count()
    flu_df2 = flu_df2.reset_index()
    plot_level_graph(flu_df2[flu_df2['val'] == '2'], 'Flu', '<=2', tot_count, os.path.join(out_folder, 'flu_level_less2_year_age_cnt.jpg'), os.path.join(out_folder, 'flu_level_less2_year_age_%.jpg'))

    df_val = flu_df1[['pid', 'val', 'year']].groupby(['year', 'val'])['pid'].count()
    df_val = df_val.reset_index()
    polt_by_year_level(df_val, 'pid', 'Flu over years by tiers - Counts', os.path.join(out_folder, 'flu_year_level.jpg'))

    ## By month
    for yr in range(2009, 2019):
        yr_df = flu_df1[flu_df1['year'] == yr]
        df_month = yr_df[['pid', 'month', 'val']].groupby(['month', 'val'])['pid'].count()
        df_month = df_month.reset_index()
        ##### fill missing entries
        for m in range(0, 12):
            for v in range(1, 4):
                if df_month[(df_month['month'] == m) & (df_month['val'] == str(v))].empty:
                    # print('missing entry!!!!', m, v)
                    df_month = df_month.append({'month': m, 'val': str(v), 'pid': 0}, ignore_index=True)
        df_month.sort_values(by='month', inplace=True)
        ####
        polt_by_month_level(df_month, 'pid', 'Flu for year Aug' + str(yr) + '-Jul' + str(yr + 1),
                            os.path.join(out_folder, 'flu_by_month_'+str(yr)+'.jpg'))

    df_all = flu_df1[flu_df1['year']!=2009][['pid', 'month', 'val']].groupby(['month', 'val'])['pid'].count()
    df_all = df_all.reset_index()
    polt_by_month_level(df_all, 'pid', 'Flu all years', os.path.join(out_folder, 'flu_by_month_all.jpg'))
    polt_by_month_level(df_all, 'pid', 'Flu all years - tiers 1&2', os.path.join(out_folder,'flu_1&2_by_month_all.jpg'), grph_bars=['1', '2'])
    polt_by_month_level(df_all, 'pid', 'Flu all years - tier 3', os.path.join(out_folder,'flu_3_by_month_all.jpg'), grph_bars=['3'])


def comp_year_age(rep):
    cfg = Configuration()
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')
    yob_df = rep.get_sig('BYEAR')
    yob_df.rename(columns={'val': 'byear'}, inplace=True)
    comp_df = rep.get_sig('Complications')
    member_df = rep.get_sig('MEMBERSHIP')

    tot_count = membership_totals(member_df, yob_df)

    comp_df1 = get_membership(comp_df, member_df)
    comp_df1 = comp_df1.merge(yob_df, how='left', on='pid')
    comp_df1['year'] = (comp_df1['date'] / 10000).astype(int)
    comp_df1.loc[comp_df1['date'] % 10000 < 801, 'year'] = comp_df1['year'] - 1  # fix year to start at Aug1
    comp_df1['month'] = comp_df1['date'].astype(str).str[4:6].astype(int) + 5
    comp_df1['month'] = comp_df1['month'] % 12
    comp_df1['age'] = comp_df1['year'] - comp_df1['byear']

    comp_df1['age_group'] = comp_df1['age'].map(age_group_map)
    # print(comp_df1)

    df = comp_df1[['pid', 'age_group', 'year']].groupby(['year', 'age_group'])['pid'].count()
    df = df.reset_index()
    plot_level_graph(df, 'Complications', 'all', tot_count, os.path.join(out_folder, 'comp_level_all_year_age_cnt.jpg'),
                     os.path.join(out_folder, 'comp_level_all_year_age_%.jpg'))


    df_lvl = comp_df1[['pid', 'age_group', 'year', 'val']].groupby(['year', 'age_group', 'val'])['pid'].count()
    df_lvl = df_lvl.reset_index()

    ##### fill missing entries
    for yr in df_lvl['year'].unique():
        for ag in df_lvl['age_group'].unique():
            for v in df_lvl['val'].unique():
                if df_lvl[(df_lvl['year'] == yr) & (df_lvl['age_group'] == ag) & (df_lvl['val'] == v)].empty:
                    print('missing entry', yr, ag, v)
                    df_lvl = df_lvl.append({'year': yr, 'age_group': ag, 'val': v, 'pid': 0}, ignore_index=True)
                    #####

    plot_level_graph(df_lvl[df_lvl['val'] == '1'], 'Complications', '1', tot_count,
                     os.path.join(out_folder, 'comp_level_1_year_age_cnt.jpg'),
                     os.path.join(out_folder, 'comp_level_1_year_age_%.jpg'))
    plot_level_graph(df_lvl[df_lvl['val'] == '2'], 'Complications', '2', tot_count,
                     os.path.join(out_folder, 'comp_level_2_year_age_cnt.jpg'),
                     os.path.join(out_folder, 'comp_level_2_year_age_%.jpg'))
    plot_level_graph(df_lvl[df_lvl['val'] == '3'], 'Complications', '3', tot_count,
                     os.path.join(out_folder, 'comp_level_3_year_age_cnt.jpg'),
                     os.path.join(out_folder, 'comp_level_3_year_age_%.jpg'))

    comp_df2 = comp_df1.copy()
    comp_df2.loc[comp_df2['val'] == '1', 'val'] = '2'
    comp_df2 = comp_df2[['pid', 'age_group', 'year', 'val']].groupby(['year', 'age_group', 'val'])['pid'].count()
    comp_df2 = comp_df2.reset_index()
    plot_level_graph(comp_df2[comp_df2['val'] == '2'], 'Complications', '<=2', tot_count,
                     os.path.join(out_folder, 'comp_level_less2_year_age_cnt.jpg'),
                     os.path.join(out_folder, 'comp_level_less2_year_age_%.jpg'))

    df_val = comp_df1[['pid', 'val', 'year']].groupby(['year', 'val'])['pid'].count()
    df_val = df_val.reset_index()
    polt_by_year_level(df_val, 'pid', 'Complications over years by teirs - Counts',
                       os.path.join(out_folder, 'comp_year_level.jpg'))

    ## By month
    for yr in range(2009, 2019):
        yr_df = comp_df1[comp_df1['year'] == yr]
        df_month = yr_df[['pid', 'month', 'val']].groupby(['month', 'val'])['pid'].count()
        df_month = df_month.reset_index()
        ##### fill missing entries
        for m in range(0, 12):
            for v in range(1, 4):
                if df_month[(df_month['month'] == m) & (df_month['val'] == str(v))].empty:
                    # print('missing entry!!!!', m, v)
                    df_month = df_month.append({'month': m, 'val': str(v), 'pid': 0}, ignore_index=True)
        df_month.sort_values(by='month', inplace=True)
        ####
        polt_by_month_level(df_month, 'pid', 'Complications for year Aug' + str(yr) + '-Jul' + str(yr + 1),
                            os.path.join(out_folder, 'comp_by_month_'+str(yr)+'.jpg'))

    df_all = comp_df1[['pid', 'month', 'val']].groupby(['month', 'val'])['pid'].count()
    df_all = df_all.reset_index()
    polt_by_month_level(df_all, 'pid', 'Complications  all years', os.path.join(out_folder, 'comp_by_month_all.jpg'))


def print_graph_comp_by_age(flu, comp, title):
    days_grps = ['0-1 Month', '1-3 Months', '3-9 Months', '9-18 Months']  # , 'no complications']
    ages = ['0-5', '5-18', '18-65', '65+']
    tot_dict = {}
    for ag in ages:
        tot_dict[ag] = flu[flu['age_group'] == ag].shape[0]
    print(tot_dict)
    months = [1, 2, 6, 9]  # , 1]
    cfg = Configuration()
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')
    mrg_df = flu.merge(comp, on='pid')
    mrg_df.sort_values(by=['pid', 'date_flu', 'date_comp'], inplace=True)
    mrg_df = mrg_df[mrg_df['date_flu'] <= mrg_df['date_comp']]
    mrg_df.drop_duplicates(subset=['pid', 'date_flu'], keep='first', inplace=True)
    mrg_df['days'] = (mrg_df['date_comp'] - mrg_df['date_flu']).dt.days
    mrg_df.sort_values(by=['pid', 'days'])
    mrg_df.drop_duplicates(subset=['pid', 'date_comp'], inplace=True)

    mrg_df.loc[(mrg_df['days'] >= 0) & (mrg_df['days'] <= 30), 'days_group'] = '0-1 Month'
    mrg_df.loc[(mrg_df['days'] >= 30) & (mrg_df['days'] <= 90), 'days_group'] = '1-3 Months'
    mrg_df.loc[(mrg_df['days'] > 90) & (mrg_df['days'] <= 270), 'days_group'] = '3-9 Months'
    mrg_df.loc[(mrg_df['days'] > 270) & (mrg_df['days'] <= 540), 'days_group'] = '9-18 Months'

    df_dys = mrg_df[['pid', 'days_group', 'age_group']].groupby(['age_group', 'days_group'])['pid'].count()
    df_dys = df_dys.reset_index()

    for ag in ages:
        for dy, m in zip(days_grps, months):
            cond = (df_dys['age_group'] == ag) & (df_dys['days_group'] == dy)
            df_dys.loc[cond, 'pid'] = (df_dys[cond]['pid'] / tot_dict[ag]) * 100
            df_dys.loc[cond, 'pid'] = df_dys[cond]['pid']/m


    bars = {}
    cnt_field = 'pid'
    for dy in days_grps:
        bars[dy] = df_dys[df_dys['days_group'] == dy].set_index('age_group')[cnt_field]
        #bars[dy].rename(index={'65-150': '65+'}, inplace=True)
        bars[dy] = bars[dy].reindex(['0-5', '5-18', '18-65', '65+'])


    # if 'All' in title:
    #    bars['no complications'] = df_dys[df_dys['days_group'] == 'no complications'].set_index('year_comp')[cnt_field]
    #df_dys['year_comp'] = df_dys['year_comp'].astype(int)
    file_name = title.replace(' ', '_') + '.jpg'
    full_file = os.path.join(out_folder, file_name)
    plot_by_ages_plus(bars, title, df_dys['age_group'].unique().tolist(), full_file)


def print_graph_comp(flu, comp, title, vacc=pd.DataFrame(), norm=False, with_vacc=False):
    days_grps = ['0-1 Month', '1-3 Months', '3-9 Months', '9-18 Months']#, 'no complications']
    months = [1, 2, 6, 9]#, 1]
    cfg = Configuration()
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')
    # mrg_df = pd.merge(flu, comp, left_on=['pid', 'year_flu'], right_on=['pid', 'year_comp'], how='outer')
    # mrg_df['days'] = (mrg_df['date_comp'] - mrg_df['date_flu']).dt.days
    # # print(mrg_df)
    # mrg_df.sort_values(by=['pid', 'date_flu', 'days'], inplace=True)
    # mrg_df = mrg_df.drop_duplicates(subset=['pid', 'date_flu'], keep='first')
    # mrg_df = mrg_df.drop_duplicates(subset=['pid', 'date_comp'], keep='first')


    mrg_df = flu.merge(comp, on='pid')
    mrg_df.sort_values(by=['pid', 'date_flu', 'date_comp'], inplace=True)
    mrg_df = mrg_df[mrg_df['date_flu'] <= mrg_df['date_comp']]
    mrg_df.drop_duplicates(subset=['pid', 'date_flu'], keep='first', inplace=True)
    mrg_df['days'] = (mrg_df['date_comp'] - mrg_df['date_flu']).dt.days
    mrg_df.sort_values(by=['pid', 'days'])
    mrg_df.drop_duplicates(subset=['pid', 'date_comp'], inplace=True)

    mrg_df.loc[(mrg_df['days'] >= 0) & (mrg_df['days'] <= 30), 'days_group'] = '0-1 Month'
    mrg_df.loc[(mrg_df['days'] >= 30) & (mrg_df['days'] <= 90), 'days_group'] = '1-3 Months'
    mrg_df.loc[(mrg_df['days'] > 90) & (mrg_df['days'] <= 270), 'days_group'] = '3-9 Months'
    mrg_df.loc[(mrg_df['days'] > 270) & (mrg_df['days'] <= 540), 'days_group'] = '9-18 Months'
    #mrg_df.loc[(mrg_df['days'].isnull()) | (mrg_df['days'] < 0), 'days_group'] = 'no complications'

    if not vacc.empty:
        mrg_df = pd.merge(mrg_df, vacc, how='left', left_on=['pid', 'year_flu'], right_on=['pid', 'year_vacc'])
        if with_vacc:
            mrg_df = mrg_df[(mrg_df['vacc'].notnull()) & (mrg_df['date_vacc'] < mrg_df['date_flu'])]
        else:
            mrg_df = mrg_df[(mrg_df['vacc'].isnull()) | (mrg_df['date_vacc'] >= mrg_df['date_flu'])]
        mrg_df.drop_duplicates(subset=['pid', 'year_flu'], keep='first', inplace=True)
        # print(mrg_df)

    df_dys = mrg_df[['pid', 'days_group', 'year_comp']].groupby(['year_comp', 'days_group'])['pid'].count()
    df_dys = df_dys.reset_index()

    ##### fill missing entries and devide by months
    for yr in range(2009, 2019):
        for dy, m in zip(days_grps, months):
            cond = (df_dys['year_comp'] == yr) & (df_dys['days_group'] == dy)
            if df_dys[cond].empty:
                print('missing entry!!!!', yr, dy)
                df_dys = df_dys.append({'year_comp': yr, 'days_group': dy, 'pid': 0}, ignore_index=True)
                cond = (df_dys['year_comp'] == yr) & (df_dys['days_group'] == dy)
            if norm:
                df_dys.loc[cond, 'pid'] = df_dys[cond]['pid']/m
    df_dys.sort_values(by='year_comp', inplace=True)
    ####
    # print(df_dys)
    bars = {}
    cnt_field = 'pid'
    for dy in days_grps:
        bars[dy] = df_dys[df_dys['days_group'] == dy].set_index('year_comp')[cnt_field]
    #if 'All' in title:
    #    bars['no complications'] = df_dys[df_dys['days_group'] == 'no complications'].set_index('year_comp')[cnt_field]
    df_dys['year_comp'] = df_dys['year_comp'].astype(int)
    file_name = title.replace(' ', '_') + '.jpg'
    full_file = os.path.join(out_folder, file_name)
    plot_by_year_plus(bars, title, df_dys['year_comp'].unique().tolist(), full_file)


def vacc_flu_comp(rep):
    vacc_df = rep.get_sig('Vaccination_flu')
    mem_df = rep.get_sig('MEMBERSHIP')
    flu_df = rep.get_sig('FLU_REG2')
    comp_df = rep.get_sig('Complications')
    yob_df = rep.get_sig('BYEAR')
    yob_df.rename(columns={'val': 'byear'}, inplace=True)

    vacc_df = get_membership(vacc_df, mem_df)
    flu_df = get_membership(flu_df, mem_df)
    comp_df = get_membership(comp_df, mem_df)

    plt.rcParams['figure.figsize'] = [15, 5]
    # Create graphs
    comp_df1 = comp_df.rename(columns={'val': 'comp', 'date': 'date_comp'})
    comp_df1['date_comp'] = pd.to_datetime(comp_df1['date_comp'], format='%Y%m%d')
    comp_df1['year_comp'] = comp_df1['date_comp'].dt.year
    comp_df1.loc[comp_df1['date_comp'].dt.month < 8, 'year_comp'] = comp_df1['year_comp'] - 1

    flu_df1 = flu_df.rename(columns={'val': 'flu', 'date': 'date_flu'})
    flu_df1['date_flu'] = pd.to_datetime(flu_df1['date_flu'], format='%Y%m%d')
    flu_df1['year_flu'] = flu_df1['date_flu'].dt.year
    flu_df1.loc[flu_df1['date_flu'].dt.month < 8, 'year_flu'] = flu_df1['year_flu'] - 1
    flu_df1.sort_values(by=['pid', 'date_flu'], inplace=True)
    flu_df1.drop_duplicates(subset=['pid', 'year_flu'], keep='first', inplace=True)
    #add the age_groups
    flu_df1 = flu_df1.merge(yob_df, on='pid', how='left')
    flu_df1['age'] = flu_df1['year_flu'] - flu_df1['byear']
    flu_df1['age_group'] = flu_df1['age'].map(age_group_map)
    print_graph_comp_by_age(flu_df1, comp_df1, 'Flu followed by all complication by age - Normalized by months - % of flu patients')
    cond1 = (comp_df1['comp'] == '1')
    print_graph_comp_by_age(flu_df1, comp_df1[cond1], 'Flu followed by Death by age - Normalized by months - % of flu patients')
    cond2 = (comp_df1['comp'] == '1') | (comp_df1['comp'] == '2')
    print_graph_comp_by_age(flu_df1, comp_df1[cond2], 'Flu followed by Death & Hospitalization  by age - Normalized by months - % of flu patients')
    return

    print_graph_comp(flu_df1, comp_df1, 'All Flu followed by All complications by year')
    print_graph_comp(flu_df1, comp_df1, 'All Flu followed by All complications by year - Normalized by months', norm=True)
    plt.rcParams['figure.figsize'] = [20, 4]
    cond1 = (comp_df1['comp'] == '1') | (comp_df1['comp'] == '2')
    print_graph_comp(flu_df1, comp_df1[cond1],
                     'Flu followed by complication complication 1-2 (Death&hospitalization) by year')
    print_graph_comp(flu_df1, comp_df1[cond1],
                     'Flu followed by complication complication 1-2 (Death&hospitalization) by year - Normalized by months', norm=True)
    cond2 = (comp_df1['comp'] == '1')
    print_graph_comp(flu_df1, comp_df1[cond2], 'Flu followed by complication 1 (Death) by year')
    print_graph_comp(flu_df1, comp_df1[cond2], 'Flu followed by complication 1 (Death) by year - Normalized by months', norm=True)

    cond3 = (flu_df1['flu'] == '1') | (flu_df1['flu'] == '2')
    print_graph_comp(flu_df1[cond3], comp_df1, 'Flu tier 1&2 followed by complication by year')
    print_graph_comp(flu_df1[cond3], comp_df1, 'Flu tier 1&2 followed by complication by year - Normalized by months', norm=True)
    cond4 = (flu_df1['flu'] == '1')
    print_graph_comp(flu_df1[cond4], comp_df1, 'Flu tier 1 followed by complication by year')
    print_graph_comp(flu_df1[cond4], comp_df1, 'Flu tier 1 followed by complication by year - Normalized by months', norm=True)

    vacc_df1 = vacc_df.rename(columns={'val': 'vacc', 'date': 'date_vacc'})
    vacc_df1['date_vacc'] = pd.to_datetime(vacc_df1['date_vacc'], format='%Y%m%d')
    vacc_df1['year_vacc'] = vacc_df1['date_vacc'].dt.year
    vacc_df1.loc[vacc_df1['date_vacc'].dt.month < 8, 'year_vacc'] = vacc_df1['year_vacc'] - 1
    vacc_df1.sort_values(by=['pid', 'date_vacc'], inplace=True)
    vacc_df1.drop_duplicates(subset=['pid', 'year_vacc'], keep='first', inplace=True)
    print_graph_comp(flu_df1, comp_df1, 'Flu followed by complication without pre vaccination', vacc_df1, norm=False, with_vacc=False)
    print_graph_comp(flu_df1, comp_df1, 'Flu followed by complication without pre vaccination - - Normalized by months', vacc_df1, norm=True, with_vacc=False)
    print_graph_comp(flu_df1, comp_df1, 'Flu followed by complication with pre vaccination', vacc_df1, False, with_vacc=True)
    print_graph_comp(flu_df1, comp_df1, 'Flu followed by complication with pre vaccination - Normalized by months', vacc_df1, norm=True, with_vacc=True)


if __name__ == '__main__':
    cfg = Configuration()
    rep_folder = fixOS(cfg.repo_folder)
    #sigs = pd.read_csv(os.path.join(rep_folder, 'kpnw.signals'), sep='\t', usecols=[1], names=['signal'])
    #sigs = [s for s in sigs['signal'].values if s not in ['DIAGNOSIS', 'Drug']]
    sigs = ['BYEAR', 'Vaccination_flu', 'MEMBERSHIP', 'FLU_REG2', 'Complications']
    rep = med.PidRepository()
    rep.read_all(fixOS(cfg.repo), [], sigs)
    print(med.cerr())

    #vacc_year_age(rep)
    #flu_year_age(rep)
    #comp_year_age(rep)
    vacc_flu_comp(rep)
