import os
import pandas as pd
import re

elix_defs = {
    'Congestive heart failure': ['398.91', '402.01', '402.11', '402.91', '404.01', '404.03', '404.11', '404.13',
                                 '404.91', '404.93', '425.4 - 425.9', '428.x'],
    'Cardiac arrhythmias': ['426.0', '426.13', '426.7', '426.9', '426.10', '426.12', '427.0 - 427.4', '427.6 - 427.9',
                            '785.0', '996.01', '996.04', 'V45.0', 'V53.3'],
    'Valvular disease': ['093.2', '394.x - 397.x', '424.x', '746.3 - 746.6', 'V42.2', 'V43.3'],
    'Pulmonary circulation disorders': ['415.0', '415.1', '416.x', '417.0', '417.8', '417.9'],
    'Peripheral vascular disorders': ['093.0', '437.3', '440.x', '441.x', '443.1 - 443.9', '447.1', '557.1', '557.9',
                                      'V43.4'],
    'Hypertension uncomplicated': ['401.x'],
    'Hypertension complicated': ['402.x - 405.x'],
    'Paralysis': ['334.1', '342.x', '343.x', '344.0 - 344.6', '344.9'],
    'Other neurological disorders': ['331.9', '332.0', '332.1', '333.4', '333.5', '333.92', '334.x - 335.x', '336.2',
                                     '340.x', '341.x', '345.x', '348.1', '348.3', '780.3', '784.3'],
    'Chronic pulmonary disease': ['416.8', '416.9', '490.x - 505.x', '506.4', '508.1', '508.8'],
    'Diabetes uncomplicated': ['250.0 - 250.3'],
    'Diabetes complicated': ['250.4 - 250.9'],
    'Hypothyroidism': ['240.9', '243.x', '244.x', '246.1', '246.8'],
    'Renal failure': ['403.01', '403.11', '403.91', '404.02', '404.03', '404.12', '404.13', '404.92', '404.93', '585.x',
                      '586.x', '588.0', 'V42.0', 'V45.1', 'V56.x'],
    'Liver disease': ['070.22', '070.23', '070.32', '070.33', '070.44', '070.54', '070.6', '070.9', '456.0 - 456.2',
                      '570.x', '571.x', '572.2 - 572.8', '573.3', '573.4', '573.8', '573.9', 'V42.7'],
    'Peptic ulcer disease excluding bleeding': ['531.7', '531.9', '532.7', '532.9', '533.7', '533.9', '534.7', '534.9'],
    'AIDS/HIV': ['042.x - 044.x'],
    'Lymphoma': ['200.x - 202.x', '203.0', '238.6'],
    'Metastatic cancer': ['196.x - 199.x'],
    'Solid tumour without metastasis': ['140.x - 172.x', '174.x - 195.x'],
    'Rheumatoid arthritis/collagen vascular diseases': ['446.x', '701.0', '710.0 - 710.4', '710.8', '710.9', '711.2',
                                                        '714.x', '719.3', '720.x', '725.x', '728.5', '728.89',
                                                        '729.30'],
    'Coagulopathy': ['286.x', '287.1', '287.3 - 287.5'],
    'Obesity': ['278.0'],
    'Weight loss': ['260.x - 263.x', '783.2', '799.4'],
    'Fluid and electrolyte disorders': ['253.6', '276.x'],
    'Blood loss anaemia': ['280.0'],
    'Deficiency anaemia': ['280.1 - 280.9', '281.x'],
    'Alcohol abuse': ['265.2', '291.1 - 291.3', '291.5 - 291.9', '303.0', '303.9', '305.0', '357.5', '425.5', '535.3',
                      '571.0 - 571.3', '980.x', 'V11.3'],
    'Drug abuse': ['292.x', '304.x', '305.2 - 305.9', 'V65.42'],
    'Psychoses': ['293.8', '295.x', '296.04', '296.14', '296.44', '296.54', '297.x', '298.x'],
    'Depression': ['296.2', '296.3', '296.5', '300.4', '309.x', '311']
    }

charl_defs = {'Myocardial infarction': ['410.x', '412.x'],
              'Congestive heart failure': ['398.91', '402.01', '402.11', '402.91', '404.01', '404.03', '404.11',
                                           '404.13', '404.91', '404.93', '425.4 - 425.9', '428.x'],
              'Peripheral vascular disease': ['093.0', '437.3', '440.x', '441.x', '443.1 - 443.9', '447.1', '557.1',
                                              '557.9', 'V43.4'],
              'Cerebrovascular disease': ['362.34', '430.x - 438.x'],
              'Dementia': ['290.x', '294.1', '331.2'],
              'Chronic pulmonary disease': ['416.8', '416.9', '490.x - 505.x', '506.4', '508.1', '508.8'],
              'Rheumatic disease': ['446.5', '710.0 - 710.4', '714.0 - 714.2', '714.8', '725.x'],
              'Peptic ulcer disease': ['531.x - 534.x'],
              'Mild liver disease': ['070.22', '070.23', '070.32', '070.33', '070.44', '070.54', '070.6', '070.9',
                                     '570.x', '571.x', '573.3', '573.4', '573.8', '573.9', 'V42.7'],
              'Diabetes without chronic complication': ['250.0 - 250.3', '250.8', '250.9'],
              'Diabetes with chronic complication': ['250.4 - 250.7'],
              'Hemiplegia or paraplegia': ['334.1', '342.x', '343.x', '344.0 - 344.6', '344.9'],
              'Renal disease': ['403.01', '403.11', '403.91', '404.02', '404.03', '404.12', '404.13', '404.92',
                                '404.93', '582.x', '583.0 - 583.7', '585.x', '586.x', '588.0', 'V42.0', 'V45.1',
                                'V56.x'],
              'Any malignancy including lymphoma and leukaemia except malignant neoplasm of skin': ['140.x - 172.x',
                                                                                                    '174.x - 195.8',
                                                                                                    '200.x - 208.x',
                                                                                                    '238.6'],
              'Moderate or severe liver disease': ['456.0 - 456.2', '572.2- 572.8'],
              'Metastatic solid tumour': ['196.x - 199.x'],
              'AIDS/HIV': ['042.x - 044.x']
              }


def range_to_lists(score_dict):
    fill_defs = {}
    for cmb, cmb_icds in score_dict.items():
        # print(cmb)
        full_list = []
        for x in cmb_icds:
            pref = None
            if '-' in x:
                # print('range with -' + x)
                rng = x.split('-')
                if 'x' in x:
                    lowr = rng[0].replace('.', '').replace('x', '0')
                    upr = rng[1].replace('.', '').replace('x', '9')
                else:
                    lowr = rng[0].replace('.', '').strip()
                    upr = rng[1].replace('.', '').strip()
                if x[0] == '0' or not x[0].isdigit():
                    pref = x[0]
                    lowr = re.findall('\d+', lowr)[0]
                    upr = re.findall('\d+', upr)[0]
                for i in range(int(lowr), int(upr) + 1):
                    if pref:
                        full_list.append('ICD9_CODE:' + pref + str(i))
                    else:
                        full_list.append('ICD9_CODE:' + str(i))
            elif 'x' in x:
                # print('range with x ' + x)
                lowr = x.replace('.', '').replace('x', '0')
                upr = x.replace('.', '').replace('x', '9')
                if x[0] == '0' or not x[0].isdigit():
                    pref = x[0]
                    lowr = re.findall('\d+', lowr)[0]
                    upr = re.findall('\d+', upr)[0]
                for i in range(int(lowr), int(upr) + 1):
                    if pref:
                        full_list.append('ICD9_CODE:' + pref + str(i))
                    else:
                        full_list.append('ICD9_CODE:' + str(i))
                # print(lowr, upr)
            else:
                icd = x.replace('.', '')
                full_list.append('ICD9_CODE:' + icd)
        fill_defs[cmb] = full_list
    return fill_defs


def read_icd_dict(icd_dict_file):
    icd_dict_df = pd.read_csv(icd_dict_file, sep='\t', skiprows=1, names=['def', 'defid', 'code'])
    icds = icd_dict_df[icd_dict_df['code'].str.contains('ICD9_CODE:')]['code']
    return icds


def filter_legal_icds(elix_lists, icds_list):
    set_list = []
    for cmb, cmb_icds in elix_lists.items():
        for x in cmb_icds:
            if x in icds_list.values:
                set_list.append({'def': 'SET', 'outer': cmb, 'inner': x})
    return pd.DataFrame(set_list)


def get_elixhauser_sets(dict_file):
    icds = read_icd_dict(dict_file)
    elix_lists = range_to_lists(elix_defs)
    return filter_legal_icds(elix_lists, icds)


def get_charlson_sets(dict_file):
    icds = read_icd_dict(dict_file)
    charl_lists = range_to_lists(charl_defs)
    return filter_legal_icds(charl_lists, icds)
