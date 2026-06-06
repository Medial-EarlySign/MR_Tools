import pandas as pd
from utils import fixOS

alcohol_status_map = pd.Series({"N": 0, "D": 0, "Y": 1})
smoke_status_map = pd.Series({"N": 0, "D": 1, "Y": 2})
readcode_100_map = pd.Series({"N": 0, "D": 1, "Y": 2})
Censor_stst = {'regular': '1001', 'dead': '2008', 'transferred': '2002', 'unknown': '2009'}
qunt_map_file = fixOS('/nas1/UsersData/tamard/MR/Tools/RepoLoadUtils/thin19_etl/quantity_map.csv')
year = 2019


def handle_thin_special(sig, vals, table):
    if sig == 'PRAC':
        vals['value'] = 'PRAC_' + vals['value']
    if sig == 'BYEAR':
        vals['value'] = vals['value'].str[6:10]
    if sig == 'STARTDATE' or sig == 'ENDDATE' or sig == 'DEATH' or sig == 'BDATE':
        vals['value'] = vals['value'].str[6:10] + vals['value'].str[3:5] + vals['value'].str[0:2]
    if sig == 'Censor':
        vals.drop_duplicates('orig_pid', inplace=True)
        censor_df = vals[['orig_pid', 'code', 'value']].pivot(values='value', columns='code', index='orig_pid')

        censor_df['value'] = Censor_stst['unknown']
        censor_df['endyear'] = censor_df['enddate'].str[-4:].astype(int)
        #censor_df['startdate'] = censor_df['startdate'].str[-4:] + censor_df['startdate'].str[3:5] + censor_df['startdate'].str[0:2]
        #censor_df['eventdate'] = censor_df['enddate'].str[-4:] + censor_df['enddate'].str[3:5] + censor_df['enddate'].str[0:2]
        censor_df['date1'] = censor_df['enddate']
        # When start year is now its regular
        censor_df.loc[censor_df['endyear'] >= year, 'value'] = Censor_stst['regular']
        censor_df.loc[censor_df['endyear'] >= year, 'date1'] = censor_df[censor_df['endyear'] >= year]['startdate']

        censor_df.loc[(censor_df['value'] == Censor_stst['unknown']) & (censor_df['deathdte'].notnull()), 'value'] = Censor_stst['dead']
        censor_df.loc[(censor_df['value'] == Censor_stst['unknown']) & (censor_df['xferdate'].notnull()), 'value'] = Censor_stst['transferred']
        return censor_df.reset_index()

    if sig == 'BP':
        bps = vals[vals['code'].str.contains('data1')]
        bpd = vals[vals['code'].str.contains('data2')]
        vals = pd.merge(bps, bpd, on=['orig_pid', 'date1'])
        vals.rename(
            columns={'value_x': 'value', 'value_y': 'value2', 'code_x': 'code', 'unit_x': 'unit', 'source_x': 'source'},
            inplace=True)
    if sig == 'SMOKING':
        vals['value'] = vals['value'].map(smoke_status_map)
    if sig == 'ALCOHOL':
        vals['value'] = vals['value'].map(alcohol_status_map)
    if sig == 'STOPPED_SMOKING':
        vals['value'] = pd.to_numeric(vals['value'], errors='coarse')
        vals = vals[vals['value'].notnull()]
        vals['value'] = vals['value'].astype(int).astype(str).str.pad(8, side='right', fillchar='1')
    if sig == 'Alcohol_quantity' or sig == 'Smoking_quantity':
        q_map = pd.read_csv(qunt_map_file, sep='\t')
        q_map.set_index('readcode', inplace=True)

        if table == 'thinlabs':
            print('Removing ' + str(vals[vals['source'].isnull()].shape[0]) + ' records with null source')
            vals = vals[vals['source'].notnull()]
            v1 = vals[vals['code'].str.contains('data1')]
            v2 = vals[vals['code'].str.contains('data2')]
            vals = pd.merge(v1, v2, how='left', on=['orig_pid', 'date1', 'source'])
            vals.rename(
                columns={'value_x': 'value', 'value_y': 'value2', 'code_x': 'code', 'unit_x': 'unit'},
                inplace=True)
            vals['RC'] = vals['source'].apply(lambda x: x.split('|')[1])
            vals['v1'] = vals['RC'].map(q_map['value1'])
            vals['v2'] = vals['RC'].map(q_map['value2'])
            rc100 = vals[vals['v1'] == 100].copy()
            rc100['value'] = rc100['value'].map(readcode_100_map)
            rc100['value2'] = pd.to_numeric(rc100['value2'], errors='coerce')
            #cond1 = (rc100['value'] == '1') | (rc100['value'] == '2')  # Smoker
            #cond2 = (rc100['value2'].notnull() & (rc100['value2'] > 0))  # quantity exists
            #rc100.loc[cond1 & cond2, 'value2'] = rc100[(cond1 & cond2)]['data2']

            no100 = vals[vals['v1'] != 100][['orig_pid', 'date1', 'v1', 'v2', 'code', 'unit', 'source']].copy()
            no100.rename(columns={'v1': 'value', 'v2': 'value2'}, inplace=True)
            cols = ['orig_pid', 'date1', 'value', 'value2', 'code', 'unit', 'source']
            vals = pd.concat([no100[cols], rc100[cols]], axis=0)
            vals['value2'].fillna(-9, inplace=True)
        else:
            vals['value'] = vals['code'].map(q_map['value1'])
            vals['value2'] = vals['code'].map(q_map['value2'])
        vals = vals[vals['value'].notnull()]
        if 'value2' in vals.columns:
            vals = vals[vals['value2'].notnull()]
    if sig == 'Labs':
        vals['numeric'] = pd.to_numeric(vals['value'], errors='coerce')
        vals['isdate'] = pd.to_datetime(vals['value'].astype(str), format='%Y%m%d', errors='coerce')
        labs_df = vals[(vals['numeric'].notnull()) & (vals['isdate'].isnull())]
        labs_df.rename(columns={'value': 'value2'}, inplace=True)
        labs_df['value'] = labs_df['source'].str[11:18]
        return labs_df[['orig_pid', 'date1', 'value', 'value2', 'code', 'unit', 'source']]
    if sig == 'Child_development':
        vals.loc[vals['value'].str.len() == 1, 'value'] = 'CHS00' + vals['value'].astype(str)
        vals.loc[vals['value'].str.replace('CHS', '').str.len() == 1, 'value'] = 'CHS00' + vals['value'].str.replace('CHS', '')
    #else:
    #    vals = pd.DataFrame()
    return vals
