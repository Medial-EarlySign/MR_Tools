#!/usr/bin/env python
import sys, os, re
#sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Projects', 'Scripts', 'Python-scripts'))
import bootstrap_filter as bootstrap_filter
import argparse
from io import StringIO
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

def break_mes(df):
    cols = [x for x in df.columns if 'Cohort' not in x and 'Measurements' not in x]
    for col in cols:
        df[col] = df[col].map(lambda x: x.replace('[',' ').replace(' - ',' ').replace(']',' ').split(' '))
        df[col + '_Mean'] = df[col].map(lambda x: x[0])
        df[col + '_Min'] = df[col].map(lambda x: x[1])
        df[col + '_Max'] = df[col].map(lambda x: x[2])
        df.drop(columns=[col], inplace=True)
    return df

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
        pass
        #print('Ignored 1st token %s'%(tokens[0]))
    if col1.find('$')>0:
        if tokens[1].strip() == 'Cohort':
            cohort_idx = 1
        elif tokens[1].strip() == 'Report':
            report_idx = 1
        else:
            pass
            #print('Ignored 2nd token %s'%(tokens[1]))
    if report_idx < 0 and cohort_idx  <0:
        return df
    
    
    #Split "$"f exists:
    cols_order=list(df.columns)
    if col1.find('$')>0:
        c1_name=tokens[0].strip()
        c2_name=tokens[1].strip()
        df[c1_name] = df[col1].astype(str).map(lambda x: x.split('$')[0])
        df[c2_name] = df[col1].astype(str).map(lambda x: x.split('$')[1])
        df=df.drop(columns=[col1])
        cols_order.insert(0,c2_name)
        cols_order.insert(0,c1_name)
        cols_order.remove(col1)
    
    df = df[cols_order]
    if report_idx >= 0 and cohort_idx  <0:
        return df
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
            tokens= vals.split(':')
            if len(tokens)==2:
                param_name, param_value =vals.split(':')
                #breakpoint()
                df.iloc[i, df.columns.get_loc(param_name) ] = clean_param_val(param_value)
            else:
                df.iloc[i, df.columns.get_loc(vals) ] = 1
    
    final_order=sorted(props) + cols_ord_before
    if 'Cohort' in final_order:
        final_order.remove('Cohort')
        final_order.insert(0, 'Cohort')
    df=df[final_order]
    return df

if __name__ == '__main__':
    #def_cohorts=  ['Age:65.000-120.000,Got_Flu_Vaccination:0.000-0.000,Got_Guideline_Condition:0.000-100.000']
    def_cohorts=  ['All']
    def_regex = [r'(AUC|POS|NEG|SENS@FPR_10\.0|SENS@FPR_01\.0|SENS@FPR_03\.0|SENS@FPR_05\.0)|SENS@FPR']
    
    parser = argparse.ArgumentParser(description = "Analyze Multiple bootstrap files")
    parser.add_argument("--report_path",nargs='+',help="the full path to bootstrap report",default=[])
    parser.add_argument("--report_name",help="if single report, control the names",nargs='+',default=[])
    parser.add_argument("--cohorts_list",nargs='+',help="the cohort list in bootstrap",default=def_cohorts)
    parser.add_argument("--measure_regex",nargs='+',help="the measurements regex",default=def_regex)
    parser.add_argument("--format_number",help="the number format",default='auto')
    parser.add_argument("--break_cols", type=str2bool,help="break columns if possible",default=True)
    parser.add_argument("--break_mes", type=str2bool,help="break mes columns",default=False)
    parser.add_argument("--table_format",help="config output table format rows,cols. m - measurment, c - cohort and r - report. comma to seprate. example default m,rc",default='m,rc')
    parser.add_argument("--take_obs",help="If true will use Obs instead of mean", type=str2bool,default=False)
    parser.add_argument("--show_cohorts",help="show info about cohorts", type=str2bool,default=False)
    parser.add_argument("--show_measures",help="show info about measures", type=str2bool,default=False)
    parser.add_argument("--output_path",help="output file", default='')
        

    args = parser.parse_args() 

    format_number = args.format_number
    cohorts_list = args.cohorts_list
    if len(args.report_path) == 0:
        raise NameError('Please provide at least 1 argument of report_path')
    if len(args.report_name) > 0 and len(args.report_path) != len(args.report_name):
        raise NameError('Please provide the same amount of report_name to match report_path')

    bootstrap_filter.verbose_warning = False
    file_dict = dict()
    idx = 0
    report_ord=[]
    if len(args.report_path) == len(args.report_name):
        report_ord=args.report_name
    for fn in args.report_path:
        pretty_name = os.path.splitext(os.path.basename(fn))[0]
        if len(args.report_path) == len(args.report_name):
            pretty_name = args.report_name[idx]
        else:
            report_ord.append(pretty_name)
        file_dict[fn] = pretty_name
        idx += 1
   
    if type(args.measure_regex) == str:
        measure_regex = [ args.measure_regex ]
    else:
        measure_regex = args.measure_regex
    measure_neg = []
    
    #END PARAMS - Running
    if (args.show_cohorts):
        print('Available cohorts for (cohorts_list):')
        bootstrap_filter.show_cohorts(file_dict)
    elif (args.show_measures):
        print('Available Measurements for (measure_regex):')
        bootstrap_filter.show_measures(file_dict)
    else:
        all_res = bootstrap_filter.filter_all_files_ci(file_dict, cohorts_list, measure_regex, measure_neg, format_number, args.take_obs)
        measure_flat, rows, cols, all_lines = bootstrap_filter.print_result(all_res, report_ord, delim_char= '\t', reformat = format_number, format_table=args.table_format)
        full_output_txt='\n'.join(all_lines)
        df=pd.read_csv(StringIO(full_output_txt), sep='\t')
        
        if args.break_mes:
            df = break_mes(df)
        if args.break_cols:
            df = break_columns(df)
        
        full_output_txt=df.to_csv(sep='\t', index=False)
        if args.output_path != '':
            df.to_csv(args.output_path, index=False)
        
        print(full_output_txt)
