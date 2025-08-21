import os
import sys
import pandas as pd
import numpy as np
import io
import time
from utils import fixOS, add_fisrt_line
from Configuration import Configuration


MIN_COUNTY_COUNT = 1500


def calc_tot(row, mid_dct):
    tot = 0
    for i in range(1,7):
        tot += row[i]*mid_dct[i]
    return tot


def merge_with_zip(cnt_df, mrg_val, zip_map, values, more_key_cols=[]):
    mrg_df = zip_map.merge(cnt_df, left_on='FIPSCODE', right_on=mrg_val)
    key_cols = ['ZIPCODE', 'FIPSCODE', 'STATECODE'] + more_key_cols
    cols = key_cols + values
    return mrg_df[cols], key_cols


def cdc_aditional_parse(files_cols_dict, source_folder, zip_map):
    files_path = os.path.join(source_folder, 'County', 'cdc_reports')
    inds = ['fips', 'County', 'State']
    val_cols = []
    topic_df = pd.DataFrame()
    for fl, colname in files_cols_dict.items():
        df = pd.read_csv(os.path.join(files_path, fl), sep='\t', usecols=[1, 2, 3, 4])
        if df.shape[0] < MIN_COUNTY_COUNT:
            print('Not enough counties ' + fl + '(' + str(df.shape[0]) + ')')
            continue
        val_cols.append(colname)
        df.set_index(inds, inplace=True)
        df.rename(columns={'Value': colname}, inplace=True)
        topic_df = pd.concat([topic_df, df], axis=1)
    topic_df.reset_index(inplace=True)
    topic_df, key_cols = merge_with_zip(topic_df, 'fips', zip_map, val_cols)
    topic_df['SEP'] = ''
    cols = key_cols + ['SEP'] + val_cols
    return topic_df[cols]


def tax_to_features(year, source_folder, out_folder, zip_map):
    zip_path = os.path.join(source_folder, 'Zip')
    tax_files = os.listdir(zip_path)
    short_yaer = str(year)[2:4]
    tax_file = [x for x in tax_files if short_yaer in x][0]
    tax_df = pd.read_csv(os.path.join(zip_path, tax_file), usecols=[0, 1, 2, 3, 4])  # , dtype={'CPT_CODE': str})
    ren_cols = {x: x.upper() for x in tax_df.columns}
    tax_df.rename(columns=ren_cols, inplace=True)
    #tax_df.rename(columns={'STATE': 'STATECODE'}, inplace=True)

    ind_cols = ['STATEFIPS', 'STATE', 'ZIPCODE']
    cat_dict = {1: 'under25K', 2: 'over25K_under50K', 3: 'over50K_under75K',
                4: 'over75K_under100K', 5: 'over100K_under200K', 6: 'over200K'}
    mid_dict = {1: 0, 2: 37500, 3: 62500, 4: 87500, 5: 150000, 6: 200000}
    # tax_df.set_index(ind_cols, inplace=True)
    piv_df = tax_df.pivot_table(index=ind_cols, columns='AGI_STUB', values='N1').reset_index()
    piv_df['total'] = piv_df.apply(lambda c: calc_tot(c, mid_dict), axis=1)
    piv_df['sum'] = piv_df[[1, 2, 3, 4, 5, 6]].sum(axis=1)
    for c in range(1, 7):
        piv_df[c] = round(piv_df[c]/piv_df['sum'], 3)
    piv_df['AVG'] = round(piv_df['total'] / piv_df['sum'], 2)
    piv_df.rename(columns=cat_dict, inplace=True)
    piv_df = piv_df.merge(zip_map, on='ZIPCODE')
    piv_df['SEP'] = ''
    cols = ['ZIPCODE', 'FIPSCODE', 'STATECODE', 'SEP', 'AVG'] + list(cat_dict.values())
    piv_df[cols].to_csv(os.path.join(out_folder, 'tax'+str(year)+'.txt'), sep='\t', index=False)


def risk_factors_to_features(source_folder, out_folder, zip_map):
    risk_factors_files = {'Diagnosed_Diabetes_Age-Adjusted_Percentage_20+_2015.txt': 'Diagnosed_Diabetes',
                          'Obesity_Age-Adjusted_Percentage_20+._2015.txt': 'Obesity',
                          'Leisure-Time_Physical_Inactivity_Age_Adjusted_Percentage_20+_2015.txt': 'Leisure_Time_Physical_Inactivity'}
    feat_df = cdc_aditional_parse(risk_factors_files, source_folder, zip_map)
    out_file = os.path.join(out_folder, 'risk_factors.txt')
    feat_df.to_csv(out_file, sep='\t', index=False)
    add_fisrt_line('# Year: 2015\n', out_file)
    add_fisrt_line('# Values as Age-Adjusted Percentage 20+\n', out_file)


def healthcare_delivery_insurance(source_folder, out_folder, zip_map):
    hospitals_physicians_files = {'Hospitals_2016.txt': 'Hospitals',
                                  'Hospitals_with_Cardiac_Intensive_Care_2016.txt': 'Hospitals_with_Cardiac_Intensive',
                                  'Hospitals_with_Cardiac_Rehabilitation_2016.txt': 'Hospitals_with_Cardiac_Rehabilitation',
                                  'Hospitals_with_Emergency_Department_2016.txt': 'Hospitals_with_ED',
                                  'Hospitals_with_Neurological_Services_2016.txt': 'Hospitals_with_Neurological_Services',
                                  'Number_of_Pharmacies_and_Drug_Stores_per_100000_population_2016.txt': 'Number_of_Pharmacies_per_100K',
                                  'Population_per_Primary_Care_Physician_(in_thousands)_2016.txt': 'Population_per_Primary_Care_Physician',
                                  'Population_per_Cardiovascular_Disease_Physician_(in_thousands)_2016.txt': 'Population_per_Cardiovascular_Disease_Physician',
                                  'Population_per_Neurologist_(in_thousands)_2016.txt': 'Population_per_Neurologist',
                                  'Population_per_Neurosurgeon_(in_thousands)_2016.txt': 'Population_per_Neurosurgeon',
                                  'Percentage_without_Health_Insurance_Under_Age_65_2016.txt': 'Percentage_without_Health_Insurance_Under_Age_65',
                                  'Percentage_Eligible_for_Medicaid_All_Ages_2012.txt':'Percentage_Eligible_for_Medicaid'}
    feat_df = cdc_aditional_parse(hospitals_physicians_files, source_folder, zip_map)
    out_file = os.path.join(out_folder, 'hospitals_physicians_insurance.txt')
    feat_df.to_csv(out_file, sep='\t', index=False)
    add_fisrt_line('# Year: 2016\n', out_file)
    add_fisrt_line('# Values for Population per Physician are in thousands\n', out_file)


def demographics_to_features(source_folder, out_folder, zip_map):
    demographics_files = {'American_Indian_Alaska_Native_Population_(%)_All_Ages_2013-2017_(5-year).txt': 'Native',
                          'Asian_Population_(%)_or_Native_Hawaiian_or_Other_Pacific_Islander_Population_(%)_All_Ages_2013-2017_(5-year).txt': 'Asian',
                          'Black_or_African_American_Population_(%)_All_Ages_2013-2017_(5-year).txt': 'African_American',
                          'White_Population_(%)_2013-2017_(5-year).txt': 'White',
                          'Hispanic_Latino_Population_(%)_2013-2017_(5-year).txt': 'Hispanic_Latino',
                          'Population_Aged_65_and_Older_(%)_2013-2017_(5-year).txt': '65_and_Older',
                          'Total_Population_2013-2017_(5-year).txt': 'Total_Population'}
    feat_df = cdc_aditional_parse(demographics_files, source_folder, zip_map)
    out_file = os.path.join(out_folder, 'demographics.txt')
    feat_df.to_csv(out_file, sep='\t', index=False)
    add_fisrt_line('# Values are % of Population (except Total_Population)\n', out_file)
    add_fisrt_line('# Years: 2013-2017_(5-year)\n', out_file)
    for k, v in demographics_files.items():
        add_fisrt_line('# ' + v + ': ' + k + '\n', out_file)


def blood_pressure_medication_nonadherence(source_folder, out_folder, zip_map):
    plood_pressure_files = {
        'Blood_Pressure_Medication_Nonadherence_Percentage_All_Races_Ethnicities_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt':'Blood_Pressure_Medication_Nonadherence-All_Races',
        'Blood_Pressure_Medication_Nonadherence_Percentage_Black_(Non-Hispanic)_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Blood_Pressure_Medication_Nonadherence-Black',
        'Blood_Pressure_Medication_Nonadherence_Percentage_White_(Non-Hispanic)_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Blood_Pressure_Medication_Nonadherence-White',
        'Blood_Pressure_Medication_Nonadherence_Percentage_Hispanic_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Blood_Pressure_Medication_Nonadherence-Hispanic',
        'Blood_Pressure_Medication_Nonadherence_Percentage_American_Indian_and_Alaskan_Native_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Blood_Pressure_Medication_Nonadherence-Native',
        'Blood_Pressure_Medication_Nonadherence_Percentage_Asian_and_Pacific_Islander_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Blood_Pressure_Medication_Nonadherence-Asian',
        'Diuretic_Nonadherence_Percentage_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Diuretic_Nonadherence-All_Races',
        'Renin-Angiotensin_System_Antagonist_Nonadherence_Percentage_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt': 'Renin_Angiotensin_System_Antagonist_Nonadherence-All_Races'}
    feat_df = cdc_aditional_parse(plood_pressure_files, source_folder, zip_map)

    val_cols = [v for v in plood_pressure_files.values() if v in feat_df.columns]
    key_cols = ['ZIPCODE', 'FIPSCODE', 'STATECODE']
    final_df = pd.DataFrame()
    for col in val_cols:
        colname = col.split('-')[0]
        race = col.split('-')[-1]
        sub_df = feat_df[key_cols+[col]].copy()
        sub_df.rename(columns={col: colname}, inplace=True)
        sub_df['RACE'] = race
        sub_df.set_index(key_cols+['RACE'], inplace=True)
        if final_df.empty:
            final_df = sub_df
        else:
            final_df = final_df.merge(sub_df, how='outer', left_index=True, right_index=True)
            same_cols = [x for x in final_df.columns if colname in x]
            if len(same_cols) > 1:
                final_df[colname] = final_df[same_cols].sum(axis=1)
                final_df.loc[final_df[colname] == 0, colname] = np.nan
    final_df.reset_index(inplace=True)
    final_df['SEP'] = ''
    out_file = os.path.join(out_folder, 'blood_pressure_medication_nonadherence.txt')
    cols = key_cols + ['RACE', 'SEP'] + list(set([x.split('-')[0] for x in val_cols]))
    final_df[cols].to_csv(out_file, sep='\t', index=False)
    add_fisrt_line('# Values are in % from Medicare Part D Beneficiaries\n', out_file)
    add_fisrt_line('# Age 65+ \n', out_file)
    add_fisrt_line('# Year: 2015\n', out_file)


def health_indicators(year, source_folder, out_folder, zip_map):
    themas = ['Total_Cardiovascular_Disease',
              'Total_CVD',
              'Heart_Disease',
              'Coronary_Heart_Disease',
              'Acute_Myocardial_Infarction',
              'Cardiac_Dysrhythmia',
              'Heart_Failure',
              'Hypertension',
              'Stroke',
              'Ischemic_Stroke',
              'Hemorrhagic_Stroke',
              'Avoidable_Heart_Disease_and_Stroke']
    gender_dict = {'Men': 'M', 'Women': 'F', 'Both_Genders': 'Both'}
    race_dict = {'All_Races_Ethnicities': 'All', 'Black_(Non-Hispanic)': 'Black', 'White_(Non-Hispanic)': 'White',
                 'American_Indian_and_Alaskan_Native': 'Native', 'Asian_and_Pacific_Islander': 'Asian',
                 'Black': 'Black', 'White': 'White', 'Hispanic': 'Hispanic'}
    age_dict = {'All_Ages': 'All', '35+': '35+', '45_to_64': '45-64', '65+': '65+', 'Under_75': '-75'}
    indicators = ['Death_Rate_per_100000', 'Hospitalization_Rate_per_1000_Medicare_Beneficiaries']
    files_path = os.path.join(ext_folder, 'County', 'cdc_reports')
    files = os.listdir(files_path)
    inds = ['fips', 'County', 'State', 'RACE', 'AGE', 'GENDER']
    years = str(year) + '-' + str(year+2)
    for ind in indicators:
        inds_df = pd.DataFrame()
        indicator_files = [f for f in files if ind in f and str(year)+'-' in f]
        full_thems = []
        for thm in themas:
            thm_df = pd.DataFrame()
            thm_files = [f for f in indicator_files if f.startswith(thm)]
            for fl in thm_files:
                df = pd.read_csv(os.path.join(files_path, fl), sep='\t', usecols=[1, 2, 3, 4])
                if df.shape[0] < MIN_COUNTY_COUNT:
                    print('Not enough counties ' + fl + '(' + str(df.shape[0]) + ')')
                    continue
                colname = fl.split('_'+ind+'_')[0]
                filters = fl.split('_'+ind+'_')[1].replace('_'+years+'.txt', '')
                print(filters)
                df['RACE'] = [v for k, v in race_dict.items() if k in filters][0]
                ages = [v for k, v in age_dict.items() if k in filters]
                if len(ages) == 0:
                    df['AGE'] = '-75'
                else:
                    df['AGE'] = ages[0]
                df['GENDER'] = [v for k, v in gender_dict.items() if k in filters][0]
                print(df['RACE'].iloc[0], df['AGE'].iloc[0], df['GENDER'].iloc[0])
                thm_df = thm_df.append(df)
            if thm_df.empty:
                continue
            full_thems.append(thm)
            thm_df.rename(columns={'Value': thm}, inplace=True)
            thm_df.set_index(inds, inplace=True)
            if inds_df.empty:
                inds_df = thm_df
            else:
                inds_df = inds_df.merge(thm_df, how='outer', left_index=True, right_index=True)

        #cols = inds + ['SEP'] + list(set([x.split('-')[0] for x in val_cols]))
        #inds_df[cols].to_csv(out_file, sep='\t', index=False)
        inds_df.reset_index(inplace=True)
        zip_inds_df, key_cols = merge_with_zip(inds_df, 'fips', zip_map, full_thems, ['RACE', 'AGE', 'GENDER'])
        zip_inds_df['SEP'] = ''
        cols = key_cols + ['SEP'] + full_thems
        out_file = os.path.join(out_folder, ind + '.txt')
        zip_inds_df[cols].to_csv(out_file, sep='\t', index=False)
        print()
        add_fisrt_line('# Values for ' + ind + '\n', out_file)
        #add_fisrt_line('# Age 65+ \n', out_file)
        add_fisrt_line('# Year: '+ str(year) + '\n', out_file)


if __name__ == '__main__':
    cfg = Configuration()
    ext_folder = fixOS(cfg.data_external)
    output_folder = os.path.join(fixOS(cfg.work_path), 'public')
    #load zip code map
    map_df = pd.read_csv(os.path.join(ext_folder, 'zip_county_map.txt'), sep='\t')
    ren_cols = {x: x.upper() for x in map_df.columns}
    map_df.rename(columns=ren_cols, inplace=True)

    #tax_to_features(2009, ext_folder, output_folder, map_df)
    #risk_factors_to_features(ext_folder, output_folder, map_df)
    #demographics_to_features(ext_folder, output_folder, map_df)
    #healthcare_delivery_insurance(ext_folder, output_folder, map_df)
    #blood_pressure_medication_nonadherence(ext_folder, output_folder, map_df)
    health_indicators(2009, ext_folder, output_folder, map_df)
