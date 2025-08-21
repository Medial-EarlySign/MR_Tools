from db_connect import DB_shula
import pandas as pd
import os


def sites_enroll_counts(ct_df,output_file):

    site_vc = ct_df['sites'].value_counts().sort_index()
    sites_agg = {}
    grps = [1] + list(range(10,300, 10)) + [1000000]
    prev = 1
    for g in grps:
        if g > 300:
            sites_agg['300+'] = site_vc[prev:g].sum()
        else:
            sites_agg[g] = site_vc[prev:g].sum()
        prev = g+1

    ew = pd.ExcelWriter(output_file)
    pd.Series(sites_agg).to_excel(ew, sheet_name='No. sites', index=True)

    enrrol_vc = ct_df['num_enroll_round'].value_counts().sort_index()
    enrrol_vc.to_excel(ew, sheet_name='No. enrollment', index=True)

    e_per_s_vc = ct_df['enroll_per_site'].value_counts().sort_index()
    e_per_s_vc.to_excel(ew, sheet_name='enrollment per site', index=True)

    ew.save()


def per_cond_counts(ct_df, output_file):
    group_map_file = '/nas1/Work/Users/Tamar/ClinicalTrials_load/condition_map_new.csv'
    group_map = pd.read_csv(group_map_file)
    group_map['group'].fillna('Unmapped', inplace=True)
    group_map = group_map.set_index('condition')['group']

    ew = pd.ExcelWriter(output_file)
    ct_df['group'] = ct_df['clinical_study_condition'].map(group_map)
    cond_grp = ct_df.groupby('group')

    enroll_per_cond = cond_grp['num_enroll'].sum().sort_values(ascending=False)
    trials_per_cond = cond_grp['id_info_nct_id'].count().sort_values(ascending=False)
    avg_per_site = cond_grp['enroll_per_site'].mean().sort_values(ascending=False)
    meadian_per_site = cond_grp['enroll_per_site'].median().sort_values(ascending=False)
    avg_site = cond_grp['sites'].mean().sort_values(ascending=False)
    median_site = cond_grp['sites'].median().sort_values(ascending=False)
    cond_df = pd.concat([enroll_per_cond.rename('enrollments'),
                         trials_per_cond.rename('# trials'),
                         avg_per_site.rename('Avg enroll per sites'),
                         meadian_per_site.rename('medain enroll per sites'),
                         avg_site.rename('Avg # of sites'),
                         median_site.rename('Median # of sites')],
                        axis=1, sort=False)
    cond_df.to_excel(ew, sheet_name='by condition', index=True)
    ew.save()


def per_cond_sites(ct_df, output_file):
    group_map_file = '/nas1/Work/Users/Tamar/ClinicalTrials_load/condition_map_new.csv'
    group_map = pd.read_csv(group_map_file)
    group_map['group'].fillna('Unmapped', inplace=True)
    group_map = group_map.set_index('condition')['group']

    ew = pd.ExcelWriter(output_file)
    dict_list = []
    ct_df['group'] = ct_df['clinical_study_condition'].map(group_map)
    cond_grp = ct_df.groupby('group')
    for name, g in cond_grp:
        dict1 = {'cond': name}
        vc = g['sites'].value_counts().sort_index()
        more10 = 0
        for i, s in vc.iteritems():
            if i <=10:
                dict1[i] = s
            else:
                more10 += s
        dict1['10+'] = more10
        dict_list.append(dict1)
    cols = ['cond'] + list(range(1, 11)) + ['10+']
    cond_df = pd.DataFrame(dict_list)[cols]
    cond_df.to_excel(ew, sheet_name='by condition', index=False)
    ew.save()


def custom_round(x, base=5):
    if x and x == x:
        return int(base * round((x+base/2)/base))
    else:
        return 0


def get_calcs(df):
    df = df[df['num_enroll'].astype(float) < 1000000].copy()
    df.loc[:, 'cities'] = df['address_city'].str.split('|').str.len()  # apply(lambda x:  len(x.split('|')))
    df.loc[:, 'zips'] = df['address_zip'].str.split('|').str.len()
    df.loc[:, 'sites'] = df[['cities', 'zips']].max(axis=1)
    df.loc[:, 'sites_round'] = df.loc[:, 'sites'].apply(lambda x: custom_round(x, base=10))

    df.loc[:, 'num_enroll_round'] = df['num_enroll'].apply(lambda x: custom_round(x, base=100))

    df.loc[:, 'enroll_per_site'] = df['num_enroll'] / df['sites']
    df.loc[:, 'enroll_per_site'] = df['enroll_per_site'].apply(lambda x: custom_round(x, base=10))
    return df


def calculate_and_save(query, db_engine, out_path, file_pref):

    df = pd.read_sql_query(query, db_engine)
    df = get_calcs(df)

    out_file = os.path.join(out_path, file_pref+'_site_enroll.xlsx')
    sites_enroll_counts(df, out_file)

    out_file = os.path.join(out_path, file_pref + '_by_condition_group.xlsx')
    per_cond_counts(df, out_file)

    out_file = os.path.join(out_path, file_pref + '_by_condition_sites.xlsx')
    per_cond_sites(df, out_file)

if __name__ == "__main__":
    db = DB_shula()
    db_engine = db.get_engine('ClinicalTrials')

    files_path = '/nas1/Work/Users/Tamar/ClinicalTrials_load'

    update_year_calc = "DATE_PART('year', TO_DATE(clinical_study_last_update_posted,'Month DD,YYYY'))"
    select_sql = "SELECT id_info_nct_id, address_city, address_country, address_state, address_zip, \
    clinical_study_phase, clinical_study_condition, CAST(clinical_study_enrollment as float) as num_enroll, " + update_year_calc + " as update_year \
    FROM alltrials WHERE CAST(clinical_study_enrollment as float) <100000 "

    ##### all from update year
    from_year = 2015
    where_sql = "  AND " + update_year_calc + " >= " + str(from_year)
    query = select_sql + where_sql
    calculate_and_save(query, db_engine, files_path, 'all_'+str(from_year))


    where_sql = "  AND " + update_year_calc + " >= " + str(from_year) +" AND clinical_study_study_type='Interventional' \
     AND location_countries_country ='United States' AND clinical_study_phase like '%%Phase 3%%'"
    query = select_sql + where_sql
    calculate_and_save(query, db_engine, files_path, 'Interventional_US_PH3_'+str(from_year))


    where_sql = " AND  clinical_study_overall_status = 'Recruiting' AND clinical_study_study_type='Interventional' \
    AND clinical_study_phase like '%%Phase 3%%' AND location_countries_country ='United States'"
    query = select_sql + where_sql
    calculate_and_save(query, db_engine, files_path, 'RecrutingUS')
