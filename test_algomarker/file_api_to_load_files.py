#!/nas1/Work/python-env/python38/bin/python
import pandas as pd
import argparse, os, shutil

def get_translation_dict():
    translation_dict = {}
    translation_dict['JAN'] = 1
    translation_dict['FEB'] = 2
    translation_dict['MAR'] = 3
    translation_dict['APR'] = 4
    translation_dict['MAY'] = 5
    translation_dict['JUN'] = 6
    translation_dict['JUL'] = 7
    translation_dict['AUG'] = 8
    translation_dict['SEP'] = 9
    translation_dict['OCT'] = 10
    translation_dict['NOV'] = 11
    translation_dict['DEC'] = 12
    return translation_dict
translation_dict=get_translation_dict()

def fix_date(s):
    tokens=s.split('-')
    month='%02d'%(translation_dict[tokens[1]])
    return int(tokens[0]+month+tokens[2])

def unified_signals(df, configuration_file, Calculator):
    #join loinc to unified into signals
    cfg=pd.read_csv(configuration_file, sep='\t')
    cfg=cfg[cfg['Calculator']==Calculator].reset_index(drop=True)
    cfg=cfg[['Code', 'Signal']].drop_duplicates().reset_index(drop=True)
    df=df.rename(columns={'Signal':'Code'}).set_index('Code').join(cfg.set_index('Code'), how='left').reset_index()
    allowed_codes=set(['Diagnosis', 'Drug', 'PROCEDURES', 'DIAGNOSIS', 'Procedures'])
    
    unmapped=df[(df['Signal'].isnull()) & (~df['Code'].isin(allowed_codes))].Code.value_counts()
    if len(unmapped)>0:
        print('Unmapping codes\n')
        print(unmapped)
        raise NameError('Error - please fix')
    df.loc[df['Signal'].isnull(),'Signal']=df.loc[df['Signal'].isnull(),'Code']
    return df

def fix_units(df):
    #Actual fix using equation:
    df['addition']=None
    df['multiply']=None
    df.loc[~df['equation'].isnull(),'addition']=df.loc[~df['equation'].isnull(),'equation'].apply(lambda x: float(x.split('+')[1].strip()))
    df.loc[~df['equation'].isnull(),'multiply']=df.loc[~df['equation'].isnull(),'equation'].apply(lambda x: float(x.split('+')[0].strip().strip('*')))
    #For each value channel:
    #breakpoint()
    for val_col in list(filter(lambda x:x.startswith('Value'), df.columns)):
        df.loc[~df.equation.isnull(),val_col] = df.loc[~df.equation.isnull(),val_col].astype(float)*df.loc[~df.equation.isnull(),'multiply'].astype(float)+df.loc[~df.equation.isnull(),'addition'].astype(float)
    return df

def unit_conversion(df, configuration_file, Calculator, confirm_ok=False):
    #unit conversion
    cfg=pd.read_csv(configuration_file, sep='\t')
    cfg=cfg[cfg['Calculator']==Calculator].reset_index(drop=True)
    cfg=cfg[['Signal', 'Code', 'Unit', 'Unit conversion']].rename(columns={'Unit conversion':'conversion'})
    test_cfg=cfg[['Signal', 'Unit']].drop_duplicates().groupby('Signal').count().reset_index().rename(columns={'Unit':'Cnt'})
    if len(test_cfg[test_cfg.Cnt>1]):
        raise NameError('Bad config - Signal has multiple main units')
    if len(cfg[['Signal', 'conversion']].drop_duplicates())!=len(cfg['Signal'].drop_duplicates()):
        raise NameError('Bad config - Signal has multiple conversion rules')
    #Convert using Signal, Code, Unit => Unit conversion
    cfg=cfg[['Signal', 'conversion']].drop_duplicates().reset_index(drop=True)
    cfg.loc[cfg['conversion'].isnull(), 'conversion']='(*1 +0)'
    cfg['conversion']=cfg['conversion'].apply(lambda x:x.split(','))
    #break down this table
    cfg=cfg.explode('conversion')
    cfg['Unit']=cfg['conversion'].apply(lambda x: x[:x.find('(')].strip() )
    cfg['equation']=cfg['conversion'].apply(lambda x: x[x.find('('):].strip('(').strip(')') )
    cfg=cfg[['Signal', 'Unit', 'equation']]
    cfg.loc[cfg['Unit']=='','Unit']=None
    cfg.loc[cfg['Unit'].isnull(),'equation']=None
    cfg.loc[cfg['Unit']=='NULL','Unit']=None #Keep equation in this case
    
    df=df.set_index(['Signal', 'Unit']).join(cfg.set_index(['Signal', 'Unit']), how='left').reset_index()
    
    allowed_codes=set(['Diagnosis', 'Drug', 'PROCEDURES', 'DIAGNOSIS', 'Procedures', 'BDATE', 'GENDER', 'Race', 'Smoking_Quit_Date',
                       'Smoking_Status', 'BYEAR'])
    bad_codes=df[(df.equation.isnull()) & (~df.Signal.isin(allowed_codes))]
    if len(df[(df.equation.isnull()) & (~df.Signal.isin(allowed_codes))])>0:
        print('###################')
        print(df[(df.equation.isnull()) & (~df.Signal.isin(allowed_codes))].Signal.value_counts())
        print('###################')
        if not(confirm_ok):
            print('Has missing conversions, will not convert those, please confirm (Y/N)')
            user=input()
            if not(user.upper()=='Y' or user.upper()=='YES'):
                raise NameError('User canceled - please fix and rerun')
    #Actual fix:
    df=fix_units(df)
    
    return df

def convert_load_files(source_file, outpath, configuration_file, Calculator, confirm_ok=False):
    df=pd.read_csv(source_file, sep='\t')
    df=df[['ID', 'Signal', 'Date', 'Value', 'Unit']]
    #currently doens't handle multiple date signals
    df.loc[df['Date'].notnull(),'Date']=df.loc[df['Date'].notnull(),'Date'].apply(fix_date)
    df=unified_signals(df, configuration_file, Calculator)
    
    #Handle MULTIPLE CHANNELS
    multi_channel_vals = df[df['Value'].str.contains(',')].reset_index(drop=True).copy()
    df=df[~df['Value'].str.contains(',')].reset_index(drop=True).copy()
    multi_channel_vals['val_ch_count']=multi_channel_vals.Value.apply(lambda x: len(x.split(',')))
    signal_types=multi_channel_vals[['val_ch_count', 'ID']].groupby('val_ch_count').count().reset_index()
    output_files=[]
    for i,ch_count in enumerate(signal_types.val_ch_count):
        df2=multi_channel_vals.copy()
        new_cols=[]
        for add_ch in range(ch_count):
            new_cols.append('Value_%d'%(add_ch+1))
            df2['Value_%d'%(add_ch+1)]=df2.Value.apply(lambda x: float(x.split(',')[add_ch]))
        cols=['ID', 'Signal', 'Date']
        cols+=new_cols
        cols+=['Unit', 'Code']
        df2=df2[cols]
        df2=unit_conversion(df2, configuration_file, Calculator, confirm_ok)
        df2=df2[cols].sort_values(['ID', 'Signal', 'Date']).reset_index(drop=True)
        out_file=outpath + '.' + str(ch_count)
        df2.to_csv(out_file, index=False, header=False, sep='\t')
        output_files.append(out_file)
        print('Wrote %s'%(out_file))
        #Store those to disk
            
    #Convert units
    df = unit_conversion(df, configuration_file, Calculator, confirm_ok)
    #Store files without Date differently!
    no_dates=df[(df.Date.isnull())].reset_index(drop=True).copy()
    df=df[(df.Date.notnull())].reset_index(drop=True).copy()
    df=df[['ID', 'Signal', 'Date', 'Value', 'Unit', 'Code']].sort_values(['ID', 'Signal', 'Date']).reset_index(drop=True)
    df.to_csv(outpath, index=False, header=False, sep='\t')
    output_files.append(outpath)
    print('Wrote %s'%(outpath))
    no_dates=no_dates[['ID', 'Signal', 'Value', 'Unit', 'Code']].sort_values(['ID', 'Signal']).reset_index(drop=True)
    no_dates.to_csv(outpath + '.no_dates', index=False, header=False, sep='\t')
    output_files.append(outpath+ '.no_dates')
    print('Wrote %s'%(outpath+ '.no_dates'))
    return output_files

def generate_loadind_config(am_directory, output_path, data_load_files):
    wp=os.path.join(output_path, 'rep_configs')
    os.makedirs(wp, exist_ok=True)
    res=list(filter(lambda x:x.endswith('.repository'),os.listdir(am_directory)))
    if len(res)!=1:
        raise NameError('Can\'t find repository file in %s'%(am_directory))
    am_name='.'.join(res[0].split('.')[:-1])
    res=list(filter(lambda x:x.endswith('.signals'),os.listdir(am_directory)))
    if len(res)!=1:
        raise NameError('Can\'t find signals file in %s'%(am_directory))
    print('copy file from %s to %s'%(os.path.join(am_directory, '%s.signals'%(am_name)), wp))
    shutil.copy(os.path.join(am_directory, '%s.signals'%(am_name)), wp)
    
    #Read dicts from am:
    fr=open(os.path.join(am_directory, '%s.repository'%(am_name)), 'r')
    lines=fr.readlines()
    fr.close()
    dict_lines=list(filter(lambda x:x.startswith('DICTIONARY'), lines))
    dicts_rep=list(map(lambda x:x.split('\t')[1].strip(),dict_lines))
    #print(dicts_rep)
    #copy files:
    for d_f in dicts_rep:
        if len(os.path.dirname(d_f))>0:
            os.makedirs(os.path.join(wp, os.path.dirname(d_f)), exist_ok=True)
        print('copy file from %s to %s'%(os.path.join(am_directory,d_f), os.path.join(wp, os.path.dirname(d_f))))
        shutil.copy(os.path.join(am_directory,d_f), os.path.join(wp, os.path.dirname(d_f)))
    
    full_o=os.path.join(wp, am_name + '.convert_config')
    
    fw=open(full_o, 'w')
    fw.write('#Loading config file for %s auto generated)\n\n'%(am_name))
    fw.write('DESCRIPTION\t%s\n'%(am_name))
    fw.write('RELATIVE\t1\n')
    fw.write('SAFE_MODE\t1\n')
    fw.write('MODE\t3\n')
    fw.write('PREFIX\t%s_rep\n'%(am_name))
    fw.write('CONFIG\t%s.repository\n'%(am_name))
    fw.write('SIGNAL\t%s.signals\n'%(am_name))
    fw.write('FORCE_SIGNALS\tBDATE,GENDER\n')
    fw.write('DIR\t%s\n'%(os.path.abspath(wp)))
    fw.write('OUTDIR\t%s\n'%(os.path.abspath(output_path)))
    fw.writelines(dict_lines)
    fw.write('\n')
    #Now add DATA rows:
    fw.writelines(list(map(lambda x: 'DATA\t%s\n'%x ,data_load_files)))
    
    fw.close()
    print('Wrote %s'%(full_o))
    return full_o
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Generate loading files to load repository")
    parser.add_argument("--file_api_input_path",help="the input path of file api data",required=True)
    parser.add_argument("--output_path",help="the output path for loading files. directory and filename prefix",required=True)
    parser.add_argument("--signals_mapping_unit_config",help="path to config file", default='/nas1/Work/Users/Alon/UnitTesting/data/AlgoMarker/Signals_mapping_codes_units.tsv')
    parser.add_argument("--signals_mapping_calculator_name",help="name of calculator to fetch", default='AAA-Flag')
    parser.add_argument("--confirm_ok",help="if true will confirm OK", default=0)
    
    parser.add_argument("--data_files_path",help="if exists will skip generation of data files to generate config", default='')
    parser.add_argument("--am_path",help="the algomarker directory(optional to generate loading config file)",default='')
    parser.add_argument("--out_rep_path",help="the output repository path",default='')
    
    args = parser.parse_args()
    output_files=[]
    if len(args.data_files_path)>0:
        wp=os.path.dirname(args.data_files_path)
        prefix_nm=os.path.basename(args.data_files_path)
        output_files=list(map(lambda x:os.path.join(wp, x),filter(lambda x: x.startswith(prefix_nm) ,os.listdir(wp))))
    if len(output_files)==0:
        output_files = convert_load_files(args.file_api_input_path, args.output_path, args.signals_mapping_unit_config, args.signals_mapping_calculator_name, args.confirm_ok)
    else:
        print('Skipped generation of data files')
    if len(args.am_path)>0 and len(args.out_rep_path)>0:
        convert_cfg_file = generate_loadind_config(args.am_path, args.out_rep_path, output_files)
        print('Now load with Flow:\nFlow --rep_create --convert_conf %s --load_err_file /tmp/load_errors'%(convert_cfg_file))