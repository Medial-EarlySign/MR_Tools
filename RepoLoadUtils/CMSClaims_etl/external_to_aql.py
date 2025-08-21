import os
import sys
import pandas as pd
import io
import time
from utils import fixOS
from sql_utils import get_sql_engine
from Configuration import Configuration
import itertools
import d6tstack
#SQL_SERVER = 'MSSQL'
SQL_SERVER = 'POSTGRESSQL'
#SQL_SERVER = 'D6_POSTGRESSQL'
DBNAME = 'RawCMS_syn'
username = 'postgres'
password= ''


def create_state_id_map(ext_folder, db_engine):
    tob_file = os.path.join(ext_folder, 'State', 'Behavioral_Risk_Factor_Data__Tobacco_Use__2011_to_present.csv')
    tob_df = pd.read_csv(tob_file, usecols=[1, 2], names=['StatePostalCode', 'StateName'], header=0)
    tob_df.drop_duplicates(inplace=True)
    tob_df['StateName'] = tob_df['StateName'].str.strip()
    tob_df = tob_df.append({'StateName': 'Dist. of Col.', 'StatePostalCode': 'DC'}, ignore_index=True)

    pov_file = os.path.join(ext_folder, 'County', 'est17all.txt')
    pov_df = pd.read_csv(pov_file, sep='\t', encoding='latin-1', skiprows=3,
                         dtype={'State FIPS Code': str},
                         usecols=[0, 2])
    pov_df.drop_duplicates(inplace=True)
    pov_df.rename(columns={'State FIPS Code': 'StateFIPSCode', 'Postal Code': 'StatePostalCode'}, inplace=True)
    pov_df = pov_df.append({'StatePostalCode': 'GU', 'StateFIPSCode': '66'}, ignore_index=True)
    pov_df = pov_df.append({'StatePostalCode': 'PR', 'StateFIPSCode': '72'}, ignore_index=True)

    tob_df = tob_df.merge(pov_df, how='left', on='StatePostalCode')
    cols = ['StatePostalCode', 'StateName', 'StateFIPSCode']
    tob_df[cols].to_csv(os.path.join(ext_folder, 'state_id_map.txt'), sep='\t', index=False)
    tob_df[cols].to_sql('state_id_map', db_engine, if_exists='replace', index=False)


def create_zipcode_county_map(ext_folder, db_engine):
    map_file = os.path.join(ext_folder, 'ZIP-COUNTY-FIPS_2017-06.csv')
    cols = ['zipcode','county', 'stateCode','FIPSCode']
    map_df = pd.read_csv(map_file, usecols=[0, 1, 2, 3], names=cols, header=0)
    map_df['county'] = map_df['county'].str.replace(' County', '')
    map_df[cols].to_csv(os.path.join(ext_folder, 'zip_county_map.txt'), sep='\t', index=False)
    map_df[cols].to_sql('zip_county_map', db_engine, if_exists='replace', index=False)


def tax_to_zip(ext_folder):
    #Source: https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics-zip-code-data-soi
    zip_path = os.path.join(ext_folder, 'Zip')
    tax_files = os.listdir(zip_path)
    tax_files = [x for x in tax_files if 'zpallagi' in x]

    for tf in tax_files:
        year = tf[0:2]
        tax_file = os.path.join(zip_path, tf)
        tax_df = pd.read_csv(tax_file, usecols=[0, 1, 2, 3, 4] ) #, dtype={'CPT_CODE': str})
        ren_cols = {x: x.upper() for x in tax_df.columns}
        tax_df.rename(columns=ren_cols, inplace=True)
        if 'STATEFIPS' not in tax_df.columns:  # in 2008 and down no 'STATEFIPS' in file
            sid = pd.read_csv(os.path.join(ext_folder, 'state_id_map.txt'), usecols=[0, 2],
                              names=['STATE', 'STATEFIPS'], sep='\t', header=0)
            tax_df = tax_df.merge(sid, how='left', on='STATE')
            tax_df.rename(columns={'AGI_CLASS': 'AGI_STUB'}, inplace=True)
        ind_cols = ['STATEFIPS', 'STATE', 'ZIPCODE']
        #tax_df.set_index(ind_cols, inplace=True)
        piv_df = tax_df.pivot_table(index=ind_cols, columns='AGI_STUB', values='N1').reset_index()
        piv_df.rename(columns={1: 'under25K', 2: 'over25K_under50K', 3: 'over50K_under75K',
                               4: 'over75K_under100K', 5: 'over100K_under100K', 6: 'over200K'}, inplace=True)
        piv_df.to_sql('tax_'+year, db_engine, if_exists='replace', index=False)
    return


def education_to_county(ext_folder):
    edu_file = os.path.join(ext_folder, 'County', 'Education.csv')
    cols = ["FIPS Code",
            "State",
            "Area name",
            "Less than a high school diploma, 2013-17",
            "High school diploma only, 2013-17",
            "Some college or associate's degree, 2013-17",
            "Bachelor's degree or higher, 2013-17",
            "Percent of adults with less than a high school diploma, 2013-17",
            "Percent of adults with a high school diploma only, 2013-17",
            "Percent of adults completing some college or associate's degree, 2013-17",
            "Percent of adults with a bachelor's degree or higher, 2013-17"]
    edu_df = pd.read_csv(edu_file, encoding='latin-1', skip_blank_lines=True, usecols=cols)
    edu_df.dropna(how='all', inplace=True)
    edu_df['FIPS Code'] = edu_df['FIPS Code'].astype(int)
    ren_dict = {x: x.replace(', 2013-17', '') for x in edu_df.columns}
    edu_df.rename(columns=ren_dict, inplace=True)
    edu_df.to_sql('Education_2013-2017', db_engine, if_exists='replace', index=False)
    return edu_df


def poverty_to_county(ext_folder):
    pov_file = os.path.join(ext_folder, 'County', 'est17all.txt')
    pov_df = pd.read_csv(pov_file, sep='\t', encoding='latin-1',skiprows=3,
                         dtype={'State FIPS Code':str, 'County FIPS Code':str},
                         usecols=[0, 1, 2, 3, 4, 7, 22])

    pov_df['FIPS Code'] = (pov_df['State FIPS Code'] + pov_df['County FIPS Code']).astype(int)
    pov_df.drop(['State FIPS Code', 'County FIPS Code'], inplace=True, axis=1)
    # ren = {'Postal Code': 'State',
    #        'Name': 'Area name',
    #        'Poverty Estimate, All Ages': 'Poverty Estimate All Ages',
    #        '90% CI Lower Bound': 'Poverty Estimate All Ages 90 CI Lower Bound',
    #        '90% CI Upper Bound': 'Poverty Estimate All Ages 90 CI Upper Bound' ,
    #        'Poverty Percent, All Ages': 'Poverty Percent All Ages',
    #        '90% CI Lower Bound.1': 'Poverty Percent All Ages 90 CI Lower Bound',
    #        '90% CI Upper Bound.1': 'Poverty Percent All Ages 90 CI Upper Bound',
    #        'Median Household Income': 'Median Household Income',
    #        '90% CI Lower Bound.6': 'Median Household Income 90 CI Lower Bound',
    #        '90% CI Upper Bound.6': 'Median Household Income 90 CI Upper Bound'}
    ren = {'Postal Code': 'State',
           'Name': 'Area name'}
    pov_df.rename(columns=ren, inplace=True)
    pov_df.to_sql('Poverty_2017', db_engine, if_exists='replace', index=False)
    return pov_df


def population_unemploymentn_to_county(ext_folder, filename, table_pref):
    pop_file = os.path.join(ext_folder, 'County', filename)
    pop_df = pd.read_csv(pop_file, encoding='latin-1')
    pop_df.rename(columns={'FIPS': 'FIPS Code', 'Area_name': 'Area_Name'}, inplace=True)
    for yr in range(2010, 2019):
        table_name = table_pref + '_' + str(yr)
        cols = [x for x in pop_df.columns if str(yr) in x]
        cols = ['FIPS Code', 'State', 'Area_Name'] + cols
        yr_df = pop_df[cols].copy()
        ren_dict = {x: x.replace('_'+str(yr), '').strip() for x in cols}
        yr_df.rename(columns=ren_dict, inplace=True)
        yr_df.to_sql(table_name, db_engine, if_exists='replace', index=False)
    return pop_df[cols]


def county_level_to_sql(ext_folder, db_engine):
    # county level source: https://www.ers.usda.gov/data-products/county-level-data-sets/download-data/
    edu_df = education_to_county(ext_folder)
    pov_df = poverty_to_county(ext_folder)
    pop_df = population_unemploymentn_to_county(ext_folder, 'PopulationEstimates.csv', 'Population')
    une_df = population_unemploymentn_to_county(ext_folder, 'Unemployment.csv', 'Unemployment')
    #county = pd.merge(edu_df, pov_df, on=['FIPS Code', 'State', 'Area name'], how='outer')
    #county = pd.merge(county, pop_df, on=['FIPS Code', 'State'], how='outer')
    #county = pd.merge(county, une_df, on=['FIPS Code', 'State'], how='outer')
    #county.to_sql('county', db_engine, if_exists='replace', index=False)
    #print(county.columns)


def tobacco_use_state(ext_folder, db_engine, youth=False):
    if youth:
        tob_file = os.path.join(ext_folder, 'State', 'Youth_Tobacco_Survey__YTS__Data.csv')
    else:
        tob_file = os.path.join(ext_folder, 'State', 'Behavioral_Risk_Factor_Data__Tobacco_Use__2011_to_present.csv')
    inds = ['LocationAbbr', 'LocationDesc']
    split_cols = ['YEAR']
    cols = ['TopicDesc', 'MeasureDesc', 'Response', 'Gender', 'Race', 'Age', 'Education']
    vals = ['Data_Value', 'Sample_Size']  # 'Data_Value_Std_Err', 'Low_Confidence_Limit',	'High_Confidence_Limit',
    tob_df = pd.read_csv(tob_file, usecols=inds+split_cols+cols+vals)
    tob_df['YEAR'] = tob_df['YEAR'].apply(lambda x: str(x).split('-')[-1])  # if 2 years range. take the second
    tob_df = tob_df[tob_df['YEAR'] > '2010']

    # For files wide tables column for each data type
    for gi, table_df in tob_df.groupby(split_cols):
        # ------ For SQL long tables per year (too long columns names
        if youth:
            table_name = 'Tobacco_Use_Youth' + gi
        else:
            table_name = 'Tobacco_Use_' + gi
        table_df.to_sql(table_name, db_engine, if_exists='replace', index=False)
        file_name = table_name + '.txt'
        #file_name = '_'.join(gi) + '.txt'
        #file_name = file_name.replace(' ', '_')

        all_df = pd.DataFrame()
        for vl, df in table_df.groupby(cols):
            pref_col_name = '_'.join(vl)
            pref_col_name = pref_col_name.replace(' ', '-')
            one_df = df[inds+vals].copy()
            ren_dict = {x: pref_col_name + x for x in vals}
            one_df.rename(columns=ren_dict, inplace=True)
            one_df.set_index(inds, inplace=True)
            if all_df.empty:
                all_df = one_df
            else:
                all_df = all_df.merge(one_df, how='outer', left_index=True, right_index=True)
        print(file_name)
        if all_df.shape[0] == 0:
            print('   Empty')
            continue
        print(all_df.shape)
        #print(all_df.columns)
        all_df.reset_index(inplace=True)
        all_df.to_csv(os.path.join('output', file_name), sep='\t', index=False)


def cdi_state(ext_folder, db_engine):
    cdi_file = os.path.join(ext_folder, 'State', 'U.S._Chronic_Disease_Indicators__CDI_.csv')

    inds = ['LocationAbbr', 'LocationDesc']
    split_cols = ['YearStart', 'Topic']
    cols = ['QuestionID', 'Stratification1']
    vals = ['DataValue', 'DataValueType']  # 'LowConfidenceLimit', 'HighConfidenceLimit']
    cdi_df = pd.read_csv(cdi_file, usecols=inds + split_cols + cols + vals + ['Question'])
    qid_df = cdi_df[['QuestionID', 'Question']].drop_duplicates()
    qid_df.to_sql('QuestionMap', db_engine, if_exists='replace', index=False)
    cdi_df = cdi_df[cdi_df['YearStart'] > 2010]
    #cdi_df = cdi_df[cdi_df['YearStart'] == 2012]

    for gi, table_df in cdi_df.groupby('YearStart'):
        table_name = 'CDI_' + str(gi)
        #table_df.to_sql(table_name, db_engine, if_exists='replace', index=False)
        all_df = pd.DataFrame()
        for vl, df in table_df.groupby(cols):
            if df['DataValueType'].nunique() > 1:
                data_type = [x for x in df['DataValueType'].unique() if 'age' in x.lower()][0]
                df = df[df['DataValueType'] == data_type]
            all_df = all_df.append(df)
        all_df.to_sql(table_name, db_engine, if_exists='replace', index=False)

    return

    cdi_df = cdi_df[cdi_df['YearStart'] == 2015]
    for gi, table_df in cdi_df.groupby(split_cols):
        #table_name = 'CDI_' + str(gi[0]) + '_' + str(gi[1])
        #table_df.to_sql(table_name, db_engine, if_exists='replace', index=False)
        file_name = 'CDI_' + str(gi[0]) + '_' + str(gi[1]) + '.txt'
        file_name = file_name.replace(' ', '_').replace(',', '')
        print(file_name)
        all_df = pd.DataFrame()
        for vl, df in table_df.groupby(cols):
            pref_col_name = '_'.join(vl) + '_'
            pref_col_name = pref_col_name.replace(',', '-')
            if df['DataValueType'].nunique() > 1:
                data_type = [x for x in df['DataValueType'].unique() if 'age' in x.lower()][0]
                df = df[df['DataValueType'] == data_type]

            one_df = df[inds+vals] #.copy()
            ren_dict = {x: pref_col_name + x for x in vals}
            one_df.rename(columns=ren_dict, inplace=True)
            one_df.set_index(inds, inplace=True)
            if all_df.empty:
                all_df = one_df
            else:
                all_df = all_df.merge(one_df, how='outer', left_index=True, right_index=True)

        print(all_df.shape)
        #print(all_df.columns)
        all_df.reset_index(inplace=True)
        all_df.to_csv(os.path.join('output', file_name), sep='\t', index=False)


def vehicle_registration_state(ext_folder, db_engine):
    #https://www.fhwa.dot.gov/policyinformation/statistics/2017/mv1.cfm
    #https://www.fhwa.dot.gov/policyinformation/statistics/2008/mv1.cfm
    #https://www.fhwa.dot.gov/policyinformation/statistics/2009/mv1.cfm
    #https://www.fhwa.dot.gov/policyinformation/statistics/2010/mv1.cfm
    #ttps://www.fhwa.dot.gov/policyinformation/statistics/2011/mv1.cfm
    #https://www.fhwa.dot.gov/policyinformation/statistics/2012/mv1.cfm
    veh_path = os.path.join(ext_folder, 'State', 'vehicles')
    veh_files = os.listdir(veh_path)
    for veh_file in veh_files:
        veh_full_file = os.path.join(veh_path, veh_file)
        yr = int(veh_file[4:8])
        print(yr)
        if (yr !=2010):
            continue
        if yr <= 2010:
            veh_df = pd.read_excel(veh_full_file, usecols=list(range(7))+list(range(8,14))+[15, 16],
                                   names=['STATE',
                                          'AUTOMOBILES_PRIVATE', 'AUTOMOBILES_PUBLICLY', 'AUTOMOBILES_TOTAL',
                                          'BUSES__PRIVATE', 'BUSES_PUBLICLY', 'BUSES_TOTAL',
                                          'TRUCKS_PRIVATE', 'TRUCKS_PUBLICLY', 'TRUCKS_TOTAL',
                                          'ALL_PRIVATE', 'ALL_PUBLICLY', 'ALL_TOTAL',
                                          'MOTORCYCLES_PRIVATE', 'MOTORCYCLES_PUBLICLY'],
                                   skiprows=12, skipfooter=8)
        else:
            veh_df = pd.read_excel(veh_full_file,
                                   names=['STATE',
                                          'AUTOMOBILES_PRIVATE', 'AUTOMOBILES_PUBLICLY', 'AUTOMOBILES_TOTAL',
                                          'BUSES__PRIVATE', 'BUSES_PUBLICLY', 'BUSES_TOTAL',
                                          'TRUCKS_PRIVATE', 'TRUCKS_PUBLICLY', 'TRUCKS_TOTAL',
                                          'MOTORCYCLES_PRIVATE', 'MOTORCYCLES_PUBLICLY', 'MOTORCYCLES_TOTAL',
                                          'ALL_PRIVATE', 'ALL_PUBLICLY', 'ALL_TOTAL'],
                                   skiprows=12, skipfooter=2)
        veh_df.dropna(how='all', inplace=True)
        veh_df['MOTORCYCLES_PUBLICLY'] = pd.to_numeric(veh_df['MOTORCYCLES_PUBLICLY'], errors='coerce', downcast='integer')
        veh_df['MOTORCYCLES_PUBLICLY'].fillna(0, inplace=True)
        veh_df['MOTORCYCLES_PRIVATE'] = veh_df['MOTORCYCLES_PRIVATE'].astype(int)
        veh_df['MOTORCYCLES_TOTAL'] = veh_df['MOTORCYCLES_PRIVATE'] + veh_df['MOTORCYCLES_PUBLICLY']

        veh_df['STATE'] = veh_df['STATE'].apply(lambda x: x.split('  ')[0])
        veh_df['STATE'] = veh_df['STATE'].apply(lambda x: x.split('\(')[0])
        veh_df['STATE'] = veh_df['STATE'].str.strip()
        #Read state id map
        sid = pd.read_csv(os.path.join(ext_folder, 'state_id_map.txt'),sep='\t')

        #veh_df['MOTORCYCLES_PUBLICLY'] = veh_df['MOTORCYCLES_PUBLICLY'].replace('— ', '')
        veh_df = veh_df.merge(sid, how='left', left_on='STATE', right_on='StateName')
        veh_df.drop(columns=['StateName', 'StateFIPSCode'], inplace=True)
        veh_df.to_csv(os.path.join('output', 'State_Vehicle_Registration'+str(yr)+'.txt'), sep='\t', index=False)
        veh_df.to_sql('Vehicles_'+str(yr), db_engine, if_exists='replace', index=False)


def drug_poisoning_state(ext_folder, db_engine):
    #https: // data.cdc.gov / NCHS / NCHS - Drug - Poisoning - Mortality - by - County - United - Sta / p56q - jrxg
    drg_file = os.path.join(ext_folder, 'State', 'NCHS_-_Drug_Poisoning_Mortality_by_State__United_States.csv')
    inds = ['State']
    split_cols = ['Year']
    cols_drops = ['Sex', 'Age Group', 'Race and Hispanic Origin']

    drg_df = pd.read_csv(drg_file)
    drg_df = drg_df[(drg_df['Year'] > 2010) & (drg_df['State'] != 'United States')]

    # Read state id map
    sid = pd.read_csv(os.path.join(ext_folder, 'state_id_map.txt'), names=['StatePostalCode', 'StateName'], sep='\t')
    drg_df = drg_df.merge(sid, how='left', left_on='State', right_on='StateName')
    drg_df.drop(columns=cols_drops+['StateName'], inplace=True)
    for gi, table_df in drg_df.groupby(split_cols):
        table_name = 'Drug_Poisoning_Mortality_states_' + str(gi)
        table_df.to_sql(table_name, db_engine, if_exists='replace', index=False)

        file_name = 'Drug_Poisoning_Mortality_states_' + str(gi) + '.txt'
        table_df.to_csv(os.path.join('output', file_name), sep='\t', index=False)


def drug_poisoning_county(ext_folder, db_engine):
    #https://data.cdc.gov/NCHS/NCHS-Drug-Poisoning-Mortality-by-County-United-Sta/p56q-jrxg
    drg_file = os.path.join(ext_folder, 'County', 'NCHS_-_Drug_Poisoning_Mortality_by_County__United_States.csv')
    drg_df = pd.read_csv(drg_file, usecols=range(10))

    split_cols = ['Year']
    drg_df = drg_df[(drg_df['Year'] >= 2008)]
    drg_df['County'] = drg_df['County'].apply(lambda x: x.split(',')[0])
    drg_df['County'] = drg_df['County'].str.replace(' County', '')

    for gi, table_df in drg_df.groupby(split_cols):
        table_name = 'Drug_Poisoning_Mortality_county_' + str(gi)
        table_df.to_sql(table_name, db_engine, if_exists='replace', index=False)

        file_name = 'Drug_Poisoning_Mortality_county_' + str(gi) + '.txt'
        table_df.to_csv(os.path.join('output', file_name), sep='\t', index=False)


def cdc_heart_disease_stroke_county(ext_folder, db_engine):
    themas = ['Total_Cardiovascular_Disease',
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
              # 'Total_CVD_Hospitalization_Medicare_Beneficiaries']
    years = ['2008-2010', '2009-2011', '2010-2012', '2011-2013', '2012-2014', '2013-2015', '2014-2016']
    ignore_yers = ['2005-2007', '2006-2008', '2007-2009', '2008-2010']
    shorts ={'Death_Rate_per_100000': 'Death_100K',
             'American_Indian_and_Alaskan_Native': 'Native',
             'All_Races_Ethnicities': 'All_Races',
             'Hospitalization_Medicare_Beneficiaries_Percentage': 'Hospital%',
             'Other_Health_Care_Facility': 'Other_Facility',
             'Hospitalization_Rate_per_1000_Medicare_Beneficiaries': 'Hosp_per_1000',
             '(any_mention)_': '',
             'Discharged_to_Acute_Care_Facility': 'Discharged_to_AC'}
    themas = [x.strip().replace(' ', '_').replace(',', '') for x in themas]
    files_path = os.path.join(ext_folder, 'County', 'cdc_reports')
    files = os.listdir(files_path)
    for yr in ignore_yers:
        files = [x for x in files if yr not in x]
    inds = ['fips', 'County', 'State']
    for thm in themas:
        for yr in years:
            thm_table = thm + '_' + yr
            thm_df = pd.DataFrame()
            if thm == 'Total_Cardiovascular_Disease':
                thm_files = [f for f in files if (f.startswith(thm) or f.startswith('Total_CVD')) and yr in f]
            else:
                thm_files = [f for f in files if f.startswith(thm) and yr in f]
            files = [f for f in files if f not in thm_files]
            for fl in thm_files:
                df = pd.read_csv(os.path.join(files_path, fl), sep='\t', usecols=[1, 2, 3, 4])
                if (df.shape[0] == 0) or df['Value'].isnull().all():
                    print('Empty file ' + fl)
                colname = fl.replace(thm+'_', '').replace('_'+yr+'.txt', '')
                if thm == 'Total_Cardiovascular_Disease':
                    colname = colname.replace('Total_CVD_Hospitalization_Medicare_Beneficiaries' + '_', '')
                for long, short in shorts.items():
                    colname = colname.replace(long, short)
                df.set_index(inds, inplace=True)
                df.rename(columns={'Value': colname}, inplace=True)
                thm_df = pd.concat([thm_df, df], axis=1)
            print(thm_table)
            print(thm_df.shape)
            thm_df.reset_index(inplace=True)
            #thm_df.to_sql(thm_table, db_engine, if_exists='replace', index=False)

            thm_df.to_csv(os.path.join('output', thm_table+'.txt'), sep='\t', index=False)
            #print(df)
    print(files)


def cdc_additional_data_count(ext_folder, db_engine):
    topic_file_map = {'Risk_Factors': ['Diagnosed_Diabetes_Age-Adjusted_Percentage_20+_2015.txt',
                                       'Obesity_Age-Adjusted_Percentage_20+._2015.txt',
                                       'Leisure-Time_Physical_Inactivity_Age_Adjusted_Percentage_20+_2015.txt'],

                      'Social_Environment': ['Percentage_without_High_School_Diploma_Ages_25+_2013-2017_(5-year).txt',
                                           'Percentage_without_4+_Years_College_Ages_25+_2013-2017_(5-year).txt',
                                           'Families_with_Female_Head_of_Household_(%)_2013-2017_(5-year).txt',
                                           'Percentage_Food_Stamp_Supplemental_Nutrition_Assistance_Program_Recipients_2015.txt',
                                           'Median_Home_Value_(in_thousands_of_$)_2013-2017_(5-year).txt',
                                           'Median_Household_Income_(in_thousands_of_$)_2016.txt',
                                           'Income_Inequality_(Gini_Index)_2013-2017_(5-year).txt',
                                           'Percentage_Living_in_Poverty_All_Ages_2016.txt',
                                           'Unemployment_Rate_Ages_16+_2017.txt'],
                      'Demographics': ['American_Indian_Alaska_Native_Population_(%)_All_Ages_2013-2017_(5-year).txt',
                                       'Asian_Population_(%)_or_Native_Hawaiian_or_Other_Pacific_Islander_Population_(%)_All_Ages_2013-2017_(5-year).txt',
                                       'Black_or_African_American_Population_(%)_All_Ages_2013-2017_(5-year).txt',
                                       'White_Population_(%)_2013-2017_(5-year).txt',
                                       'Hispanic_Latino_Population_(%)_2013-2017_(5-year).txt',
                                       'Population_Aged_65_and_Older_(%)_2013-2017_(5-year).txt'],

                      'Physical_Environment': [
                          'Annual_Average_Ambient_Concentrations_of_PM2.5_2014.txt',
                          'Percentage_of_Population_Living_Within_Half_a_Mile_of_a_Park_2010.txt',
                          'Percentage_of_Households_Living_with_Severe_Housing_Problems_2010-2014_(5_year).txt',
                          'Urban-Rural_Status_2013.txt'],

                      'Blood_Pressure': [
                          'Blood_Pressure_Medication_Nonadherence_Percentage_All_Races_Ethnicities_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Blood_Pressure_Medication_Nonadherence_Percentage_Black_(Non-Hispanic)_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Blood_Pressure_Medication_Nonadherence_Percentage_White_(Non-Hispanic)_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Blood_Pressure_Medication_Nonadherence_Percentage_Hispanic_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Blood_Pressure_Medication_Nonadherence_Percentage_American_Indian_and_Alaskan_Native_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Blood_Pressure_Medication_Nonadherence_Percentage_Asian_and_Pacific_Islander_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Diuretic_Nonadherence_Percentage_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt',
                          'Renin-Angiotensin_System_Antagonist_Nonadherence_Percentage_Medicare_Part_D_Beneficiaries_Aged_65+_2015.txt'],

                      'Hospitals': ['Hospitals_2016.txt', 'Total_Population_2013-2017_(5-year).txt',
                                    'Hospitals_with_Cardiac_Intensive_Care_2016.txt',
                                    'Hospitals_with_Cardiac_Rehabilitation_2016.txt',
                                    'Hospitals_with_Emergency_Department_2016.txt',
                                    'Hospitals_with_Neurological_Services_2016.txt',
                                    'Number_of_Pharmacies_and_Drug_Stores_per_100000_population_2016.txt'],

                      'Physicians': ['Population_per_Primary_Care_Physician_(in_thousands)_2016.txt',
                                     'Population_per_Cardiovascular_Disease_Physician_(in_thousands)_2016.txt',
                                     'Population_per_Neurologist_(in_thousands)_2016.txt',
                                     'Population_per_Neurosurgeon_(in_thousands)_2016.txt'],

                      'Insurance': ['Percentage_without_Health_Insurance_Under_Age_65_2016.txt',
                                    'Percentage_Eligible_for_Medicaid_All_Ages_2012.txt'],

                      'Health_cost': [
                          'Cost_of_Care_per_Capita_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Total_2016.txt',
                          'Cost_of_Care_per_Capita_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Inpatient_2016.txt',
                          'Cost_of_Care_per_Capita_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Outpatient_2016.txt',
                          'Cost_of_Care_per_Capita_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Post-Acute_Care_2016.txt',
                          'Incremental_Cost_of_Care_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Total_2016.txt',
                          'Incremental_Cost_of_Care_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Inpatient_2016.txt',
                          'Incremental_Cost_of_Care_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Outpatient_2016.txt',
                          'Incremental_Cost_of_Care_for_Medicare_Beneficiaries_Diagnosed_with_Heart_Disease_Post-Acute_Care_2016.txt',
                          'Prevalence_of_Diagnosed_Heart_Disease_Among_Medicare_Beneficiaries_2016.txt'],
                      }
    files_path = os.path.join(ext_folder, 'County', 'cdc_reports')
    inds = ['fips', 'County', 'State']
    #topics = topic_file_map.keys()
    for tp, files in topic_file_map.items():
        topic_df = pd.DataFrame()
        for fl in files:
            df = pd.read_csv(os.path.join(files_path, fl), sep='\t', usecols=[1, 2, 3, 4])
            if (df.shape[0] == 0) or df['Value'].isnull().all():
                print('Empty file ' + fl)
            colname = fl.replace('.txt', '')
            df.set_index(inds, inplace=True)
            df.rename(columns={'Value': colname}, inplace=True)
            topic_df = pd.concat([topic_df, df], axis=1)
        topic_df.reset_index(inplace=True)
        print(tp)
        print(topic_df.shape)
        # thm_df.to_sql(thm_table, db_engine, if_exists='replace', index=False)
        topic_df.to_csv(os.path.join('output', tp + '.txt'), sep='\t', index=False)


if __name__ == '__main__':
    cfg = Configuration()
    ext_folder = fixOS(cfg.data_external)
    db_engine = get_sql_engine(SQL_SERVER, DBNAME, username, password)
    #create_state_id_map(ext_folder, db_engine)
    create_zipcode_county_map(ext_folder, db_engine)
    #tax_to_zip(ext_folder)

    #county_level_to_sql(ext_folder, db_engine)

    #tobacco_use_state(ext_folder, db_engine)
    #tobacco_use_state(ext_folder, db_engine, youth=True)

    #cdi_state(ext_folder, db_engine)

    #vehicle_registration_state(ext_folder, db_engine)


    #drug_poisoning_state(ext_folder, db_engine)
    #drug_poisoning_county(ext_folder, db_engine)

    #cdc_heart_disease_stroke_county(ext_folder, db_engine)
    #cdc_additional_data_count(ext_folder, db_engine)


# Influenza/Pneumonia Mortality by State
#source: https://www.cdc.gov/nchs/pressroom/sosmap/flu_pneumonia_mortality/flu_pneumonia.htm