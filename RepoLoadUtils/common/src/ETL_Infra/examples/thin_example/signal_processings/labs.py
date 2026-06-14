from signal_processings.process_helper import *

thin_signal_mapping = pd.read_csv('configs/thin_signal_mapping.csv', sep='\t')

print('total removed bad row: ' + str(len(df[df['ahdflag']!='Y'])))
df = df[df['ahdflag']=='Y'].reset_index(drop=True)

# just medcodes with numeric signal
data=df
data.drop(columns='signal', inplace=True)
data = data.merge(thin_signal_mapping[['signal', 'code', 'description', 'type']].rename(columns={'code':'medcode'}), on='medcode', how='left')
data = data[data['type']=='numeric']

## tmp - load just Urine_Microalbumin
data = data[data.signal.isin(['Uric_Acid', 'T4', 'Bicarbonate'])]

# remove eGFR (we will calculate independently) smoking statistics, to make statistice meaningful
data = data[data.signal!='eGFR']
data = data[data.medcode.map(lambda x: x[0:3]!='137')]
print('total candidat numeric rows (without smoking and without eGFR): ' + str(len(data)))

# just numeric values in data field
data['data2'] = pd.to_numeric(data.data2, errors='coerce')
data = data[data.data2.notna()]
print('after removing no data: ' + str(len(data)))

# just signals we have in general.signals
signals_to_drop = ['ALCOHOL',
 'Maternity_pregnancy_LMP_EDD',
 'Albumin_over_Creatinine',
 'Alcohol_quantity',
 'C3',
 'CA125',
 'CA153',
 'CA199',
 'CHADS2',
 'CHADS2_VASC',
 'HDL_over_Cholesterol',
 'Cholesterol_over_HDL',
 'CorrectedCa',
 'Erythrocyte',
 'FSH',
 'Fev1_over_Fvc',
 'Fructosamine',
 'Fvc',
 'GtanNum',
 'HCG',
 'HDL_over_LDL',
 'HDL_over_nonHDL',
 'LDL_over_HDL',
 'LUC',
 'LuteinisingHormone',
 'PDW',
 'PT',
 'PTH',
 'APTT',
 'APTT_r',
 'PTT',
 'PlasmaAnionGap',
 'PlasmaViscosity',
 'PlasmaVolume',
 'Progesterone',
 'RandomGlucose',
 'RandomHDL',
 'RandomLDL',
 'RandomTriglyceride',
 'Reticulocyte',
 'Serum_Oestradiol',
 'Sex_Hormone_Binding_Globulin',
 'T3',
 'Teophylline',
 'Transferrin_Saturation_Index',
 'TroponinI',
 'TroponinT',
 'Urine_Dipstick_pH',
 'Urine_Epithelial_Cell',
 #'Urine_Microalbumin',
 'Urine_Protein_Creatinine',
 'VLDL',
 'VitaminD2',
 'VitaminLevel',
 'Zinc',
 'eGFR',
 'GFR']

to_drop = data.signal.isin(signals_to_drop)
if to_drop.sum() > 0:
    print('Drop ' + str(to_drop.sum()) + ' lab records because signal is not in allowed list. Most common drop are:')
    print(data[to_drop].signal.value_counts().head(10))
    data = data[~to_drop]
    
# must have code for unit
data = data[data.data3.map(lambda x: x[0:3]=='MEA')] 
print('After removing no unit: ' + str(len(data)))

# Basophils# with unit % are actually Basophils%
to_change = (data.signal=='Basophils#') & (data.data3=='MEA001')
data.loc[to_change, 'signal'] = 'Basophils%'

# translate to unit

def get_translate_to_unit():
    f_MEA = '/nas1/Data/THIN2101/IMRD Ancil TEXT/text/AHDlookups2101.txt'
    mea = pd.read_csv(f_MEA, names = ['input'])
    mea = mea[mea.input.map(lambda x: x[0:3]=='MEA')]
    mea[mea.input.map(lambda s: s[:16]=='MEA MEASURE_UNIT ')].shape
    mea['data3'] = mea.input.map(lambda s: s[38:44])
    mea['unit'] = mea.input.map(lambda s: s[44:].strip())
    return mea

translate_to_unit = get_translate_to_unit()
data = data.merge(translate_to_unit[['data3', 'unit']], on='data3', how='left')
        
# merge with formula
unitTranslator = pd.read_csv('configs/unitTranslator.txt', sep='\t')
unitTranslator.loc[unitTranslator.unit=='None', 'unit'] = 'null value'
data = data.merge(unitTranslator, on=['signal', 'unit'], how='left')

# print missing formula statistics
print('Most common missing unit translation:')
one = pd.DataFrame(data[data.addition.isna()][['signal', 'unit']].value_counts()).rename(columns={0:'missing'})
two = pd.DataFrame(data[['signal']].value_counts()).rename(columns={0:'total_for_signal'})
print(one.join(two).sort_values(by='missing').tail(20))

data = data[data.addition.notna()]
print('after removing rows without unit translation: ' + str(len(data)))

# calculate value
data['value_0'] = data.muliplier.astype(float) * data.data2 + data.addition.astype(float)
data['value_0'] = data['value_0'] / data.Round
data['value_0'] = round(data['value_0'], 0) * data.Round

# remove 0's
data = data[data.value_0 >= 0]
zero_allowed = pd.read_csv('../../rep_signals/lab_zero_value_allowed.txt', names=['signal'])          
to_remove = (data.value_0 == 0) & (~data.signal.isin(zero_allowed.signal.tolist())) & (data.unit == 'null value')
data = data[~to_remove]
print('after removing negative values and rows with 0 as value and null unit: ' + str(len(data)))

# fix (later - might be better to use config file)
data.loc[(data.signal == 'Hematocrit') & (data.value_0 < 1),     'value_0'] *= 100
data.loc[(data.signal == 'Hematocrit') & (data.value_0 > 1000),  'value_0'] *= 0.01
data.loc[(data.signal == 'HbA1C')      & (data.value_0 > 30),    'value_0'] *= 0.1
data.loc[(data.signal == 'MCHC-M')     & (data.value_0 < 10),    'value_0'] *= 10
data.loc[(data.signal == 'MCHC-M')     & (data.value_0 > 100),   'value_0'] *= 0.1
data.loc[(data.signal == 'MCV')        & (data.value_0 < 20),    'value_0'] *= 10
data.loc[(data.signal == 'Uric_Acid')  & (data.value_0 > 100),   'value_0'] *= 0.01
data.loc[(data.signal == 'Hemoglobin') & (data.value_0 > 25),    'value_0'] *= 0.1
data.loc[(data.signal == 'B12')        & (data.value_0 < 50),    'value_0'] *= 10
data.loc[(data.signal == 'Fibrinogen') & (data.value_0 > 10000), 'value_0'] *= 0.01
data.loc[(data.signal == 'RBC')        & (data.value_0 > 2000),  'value_0'] *= 0.001
data.loc[(data.signal == 'T4')         & (data.value_0 > 40),    'value_0'] *= 0.1
data.loc[(data.signal == 'Uric_Acid')  & (data.value_0 > 20),    'value_0'] *= 0.1

# fix by drop, possible mix between % and #
before = len(data)
data = data[(data.signal != 'Neutrophils#') | (data.value_0 < 36) ] # 36  is 1% of Neutrophils%
data = data[(data.signal != 'Lymphocytes%') | (data.value_0 > 4.6)] # 4.6 is 1% of Lymphocytes#
data = data[(data.signal != 'Monocytes%')   | (data.value_0 > 1.4)] # 1.4 is 1% of Monocytes#
after = len(data)
if before > after:
    print('Drop ' + str(before-after) + ' lab records because of potential mix between count signal and % signal')

# time cleaning
return_df = check_and_fix_date(data, col='time_0')

before = len(return_df)
return_df = return_df[return_df.time_0.between(MIN_REPO_DATE, MAX_REPO_DATE)]
after = len(return_df)
if before > after:
    print('Drop ' + str(before-after) + ' lab records because date of signal out of repo range')

df = return_df[['pid', 'signal', 'time_0', 'value_0', 'medcode', 'data3', 'unit', 'muliplier', 'addition']]
