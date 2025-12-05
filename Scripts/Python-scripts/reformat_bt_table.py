#!/usr/bin/env python
#NOT  NEEDED ANYMORE - PART OF bootstrpa_format.py

import sys, os, argparse, re
import pandas as pd

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def format_num(val):
    num_re=re.compile(r'[0-9]+(\.[0-9]+)?')
    if len(num_re.findall(val)):
        return str(float(val)).rstrip('0').rstrip('.')
    return val

def clean_param_val(val):
    tokens=val.split('-')
    if len(tokens)==2:
        if tokens[0].strip()==tokens[1].strip():
            return format_num(tokens[0])
        else:
            return format_num(tokens[0]) + '-' + format_num(tokens[1])
    return val

def break_columns(df):
    col1=df.columns[0]
    
    cohort_idx = -1
    report_idx = -1
    tokens = col1.split('$')
    if tokens[0].strip() == 'Cohort':
        cohort_idx = 0
    elif tokens[0].strip() == 'Report':
        report_idx = 0
    else:
        print('Ignored 1st token %s'%(tokens[0]))
    if col1.find('$')>0:
        if tokens[1].strip() == 'Cohort':
            cohort_idx = 1
        elif tokens[1].strip() == 'Report':
            report_idx = 1
        else:
            print('Ignored 2nd token %s'%(tokens[1]))
    if report_idx < 0 and cohort_idx  <0:
        raise NameError('Not found')
    if report_idx >= 0 and cohort_idx  <0:
        sys.exit(0)#Already done
    
    #Split "$"f exists:
    if col1.find('$')>0:
        c1_name=tokens[0].strip()
        c2_name=tokens[1].strip()
        df[c1_name] = df[col1].astype(str).map(lambda x: x.split('$')[0])
        df[c2_name] = df[col1].astype(str).map(lambda x: x.split('$')[1])
        df=df.drop(columns=[col1])
    
    #now let's handle df['Cohort']:
    props=set()
    for i in range(len(df)):
        ch=df.iloc[i]['Cohort']
        param_names = list(map(lambda x: x.split(':')[0],ch.split(',')))
        props = props.union(param_names)
    
    #Add columns:
    cols_ord_before = list(df.columns)
    for col in props:
        df[col] = None
    
    for i in range(len(df)):
        ch=df.iloc[i]['Cohort']
        for vals in ch.split(','):
            param_name, param_value =vals.split(':')
            #breakpoint()
            df.iloc[i, df.columns.get_loc(param_name) ] = clean_param_val(param_value)
    
    df=df[sorted(props) + cols_ord_before]
    return df

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Reformat bootstrap cohort,report with comma as first token")
    parser.add_argument("--input", help="the full path to input",default='-')
    parser.add_argument("--output", help="the full path to output",required=True)
    
    args = parser.parse_args()
    if args.input != '-':
        df=pd.read_csv(args.input, sep='\t')
    else:
        df=pd.read_csv(sys.stdin, sep='\t')
    
    df= break_columns(df)
    if args.output != '-':
        df.to_csv(args.output, sep='\t', index=False)
    else:
        df.to_csv(sys.stdout, sep='\t', index=False)
                
    