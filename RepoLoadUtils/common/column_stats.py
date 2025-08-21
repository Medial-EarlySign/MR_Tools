#!/home/Work/python-env/python38/bin/python
"""
A helper library to analyze and get stats from dataframe on each column
"""

import pandas as pd
from pandas.api.types import is_numeric_dtype

def analyze_col(df, col, analyze_by_id_cols=['pid', 'id'], additional_skip_list= ['time', 'date']):
    
    skip_list=analyze_by_id_cols + additional_skip_list
    
    ss=set(skip_list)
    if col in ss:
        return
    diff_vals=df[col].nunique()
    has_val_count = len(df[df[col].notnull()])
    if diff_vals < 2:
        print('Column "%s" has only one value %s'%(col, df[col][0]))
        return
    #analyze per individual:
    res_sub = df[analyze_by_id_cols + [col]].groupby(analyze_by_id_cols).agg(['nunique']).sort_values((col, 'nunique'), ascending=False)
    max_val_per_subject=res_sub.iloc(0)[0].values[0]
    res = df[analyze_by_id_cols  + [col]].groupby(col).agg(['count','nunique']).sort_values([tuple(analyze_by_id_cols + ['nunique']), tuple(analyze_by_id_cols + ['count'])], ascending=[False, False])
    max_sub_per_col=res.iloc(0)[0].values[1]
    if max_val_per_subject < 2 and max_sub_per_col < 2:
        print('column "%s" is fixed for subject and each value is mapped to 1 subject'%(col))
        return
    if max_val_per_subject < 2:
        print('column "%s" is fixed for subject. Always the same value for subject'%(col))
    else:
        print('column "%s" changes for subject. maximal change: %d'%(col, max_val_per_subject))
    #analyze for all:
    add_msg=''
    if is_numeric_dtype(df[col]):
        add_msg=', min=%f, mean=%f, max=%f'%( df[col].min(), df[col].mean(), df[col].max() )
    if max_sub_per_col < 2:
        print('column "%s" has always the same subject'%(col))
    most_common_val=res.sort_values(tuple(analyze_by_id_cols + ['count']), ascending=False).iloc(0)[0]
    print('column "%s" has %d values in %d records(%2.1f%%)%s, most common value "%s" with %d count(%2.1f%%):'%(col, len(res), has_val_count,100* has_val_count/float(len(df)),
                                                                                                                add_msg, most_common_val.name, most_common_val.values[0],
                                                                                       100.0*most_common_val.values[0] / float(has_val_count)))
    print(res.head())
    
    

def analyze_file(file_path, analyze_by_id_cols=['pid', 'id'], additional_skip_list= ['time', 'date'], _sep='\t'):
    print('Reading %s...'%(file_path))
    df=pd.read_csv(file_path, sep=_sep low_memory=False)
    print('Read file')
    cols=list(df.columns)
    for col in cols[1:]:
        print('####################################')
        analyze_col(df, col, analyze_by_id_cols, additional_skip_list)
        print('####################################')

def analyze_file_big(file_paths, analyze_by_id_cols=['pid', 'id'], additional_skip_list= ['time', 'date'], _sep='\t'):
    header=pd.read_csv(file_paths[0], sep=_sep, nrows=3)
    cols=list(header.columns)
    skip_list=analyze_by_id_col + additional_skip_list
    ss=set(skip_list)
    for col in cols[1:]:
        if col in ss:
            continue
        print('####################################')
        
        df=None
        for fp in file_paths:
            print('Read column %s for file %s'%(col, fp))
            x=pd.read_csv(fp, sep=_sep, usecols=[col] + analyze_by_id_col, low_memory=True)
            if df is None:
                df=x
            else:
                df=df.append(x, ignore_index=True)
        
        analyze_col(df, col, analyze_by_id_cols, additional_skip_list)
        print('####################################')