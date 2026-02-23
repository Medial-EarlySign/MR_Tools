#!/usr/bin/env python
from plot import *
import argparse, os, re
#generate bootstrap graphs from bootstrap results

def fetch_number(s:str):
    number_fetcher = re.compile(r'_([0-9]+)_|_([0-9]+\.[0-9]+)_')
    res = number_fetcher.findall(s)
    if len(res)==1:
        res = res[0]
        if len(res[0])==0:
            res = str(float(res[1]))
        else:
            res = str(float(res[0]))
        return res
    return None

def merge_rows(filtered_rows: list[list], filtered_rows2: list[list], op_metric:bool) -> list[list]:
    # str, float, float in each list
    assert(len(filtered_rows)== len(filtered_rows2))
    for i in range(len(filtered_rows)):
        row1 = filtered_rows[i]
        row2 = filtered_rows2[i]
        assert(row1[0] == row2[0]) # same cohort
        assert(row1[1] == row2[1]) # same measre
        if op_metric:
            row2[2] = str(100 - float(row2[2]))
        filtered_rows[i][1] = row2[2] # override with value from filtered_rows2
    return filtered_rows

def perpare_bt_graph(input_path: str, measure: str, filter_cohorts, take_mean=True, show_ci = False, set_metric_x: str = '', op_metric: bool = False):
    #print('Reading %s'%(input_path))
    data_rows=read_data(input_path, '\t')
    data_rows = data_rows[1:]
    #removed header
    filtered_rows_main = list(filter(lambda x: x[1].split('_')[0] == measure ,data_rows))
    if (len(filtered_rows_main) == 0):
        filtered_rows_main = list(filter(lambda x: x[1].find(measure) >= 0 ,data_rows))
    if filter_cohorts is not None and len(filter_cohorts) > 0:
        filter_reg = re.compile(filter_cohorts)
        filtered_rows_main = list(filter(lambda x: len(filter_reg.findall(x[0])) > 0 ,filtered_rows_main))
        
    if take_mean:
        filtered_rows = list(filter(lambda x: x[1].endswith('_Mean') ,filtered_rows_main))
    else:
        filtered_rows = list(filter(lambda x: x[1].endswith('_Obs') ,filtered_rows_main))
    
    filtered_rows = list(map(lambda x : [x[0], fetch_number(x[1]), x[2]], filtered_rows))

    if set_metric_x != '':
        suffix_measure = measure.split('@')[1]
        filtered_rows_main2 = list(filter(lambda x: x[1].startswith(set_metric_x + '@' + suffix_measure) ,filtered_rows_main))
        if (len(filtered_rows_main2) == 0):
            filtered_rows_main2 = list(filter(lambda x: x[1].find(set_metric_x + '@' + suffix_measure) >= 0 ,data_rows))
        if filter_cohorts is not None and len(filter_cohorts) > 0:
            filter_reg = re.compile(filter_cohorts)
            filtered_rows_main2 = list(filter(lambda x: len(filter_reg.findall(x[0])) > 0 ,filtered_rows_main2))
        if take_mean:
            filtered_rows2 = list(filter(lambda x: x[1].endswith('_Mean') ,filtered_rows_main2))
        else:
            filtered_rows2 = list(filter(lambda x: x[1].endswith('_Obs') ,filtered_rows_main2))
        filtered_rows2 = list(map(lambda x : [x[0], fetch_number(x[1]), x[2]], filtered_rows2))
        # Update filtered_rows with filtered_rows2: replace 1 with this matching results:
        filtered_rows = merge_rows(filtered_rows, filtered_rows2, op_metric)

    if show_ci:
        ci_rows_low = list(filter(lambda x: x[1].endswith('_CI.Lower.95')  ,filtered_rows_main))
        ci_rows_high = list(filter(lambda x: x[1].endswith('_CI.Upper.95') ,filtered_rows_main))
        filtered_rows = list(map(lambda i: filtered_rows[i] + [ ci_rows_low[i][2], ci_rows_high[i][2] ] , range(len(filtered_rows))) )
        #filtered_rows = filtered_rows + list(map(lambda x : [ '%s_CI_Lower'%(x[0]), fetch_number(x[1]), x[2]], ci_rows_low))
        #filtered_rows = filtered_rows + list(map(lambda x : [ '%s_CI_Upper'%(x[0]), fetch_number(x[1]), x[2]], ci_rows_high))
        
    filtered_rows = sorted(filtered_rows, key = lambda x: [x[0], float(x[1])])
    tokens = measure.split('@')
    header = ['Cohort', measure, 'value']
    if len(tokens)==2:
        header = ['Cohort', tokens[1], tokens[0]]
    if show_ci:
        header.append('CI_lower')
        header.append('CI_upper')
    filtered_rows.insert(0, header)
    
    #print(filtered_rows[:3])
    
    return filtered_rows

if __name__ == '__main__':
    #generate_graph(input_file, has_header, html_template, output_path, delim, x_cols, y_cols, group_col)
    par=os.path.dirname(__file__)
    if (par==''):
        par='.'
    def_template=os.path.join( par, 'templates', 'plotly_graph.html')
    parser = argparse.ArgumentParser(description = "Plot HTML Graph from Bootstrap results")
    parser.add_argument("--input",nargs='+',help="input file path",required=True)
    parser.add_argument("--names",nargs='+',help="names for input files. same size as input",required=False,default=[])
    parser.add_argument("--output",help="output path",required=True)
    parser.add_argument("--measure",help="output path",default='SENS@FPR')
    parser.add_argument("--filter_cohorts",help="regex filter of cohorts",default='')
    parser.add_argument("--html_template",help="html template path",default=def_template)
    parser.add_argument("--take_mean",help="If true will print Mean, otherwise Obs", type=str2bool,default=True)
    parser.add_argument("--show_ci",help="If true will also output CI", type=str2bool,default=False)
    parser.add_argument("--add_y_eq_x",help="If true will add y=x graph", type=str2bool,default=False)
    parser.add_argument("--set_metric_x",help="Control metric to fetch from X@ pattern to set as X input", default='')
    parser.add_argument("--op_metric_x",help="if ttue will do 100-X in x axis", type=str2bool, default=False)
    args = parser.parse_args()

    all_datasets=[]
    for i, inp in enumerate(args.input):
        data=perpare_bt_graph(inp, args.measure, args.filter_cohorts, args.take_mean, args.show_ci, args.set_metric_x, args.op_metric_x)
        if len(args.input) > 1:
            inp_name=os.path.basename(inp)
            if len(args.names) != len(args.input):
                func_naming= lambda x: [inp_name + "::" + x[0]] + x[1:]
            else:
                func_naming= lambda x: [args.names[i] + "::" + x[0]] + x[1:]
            if i == 0:
                data = [data[0]] + list(map(func_naming  ,data[1:]))
            else:
                data = list(map(func_naming ,data[1:]))
            
                
        all_datasets = all_datasets + data
        
    if args.add_y_eq_x:
        print('Add y==x graph')
        x_vals = sorted(set(map(lambda x: float(x[1]) ,all_datasets[1:])))
        if args.show_ci:
            add_d = list(map(lambda x: ['Y=X', str(x), str(x),str(x) , str(x)] ,x_vals))
        else:
            add_d = list(map(lambda x: ['Y=X', str(x), str(x)] ,x_vals))
        all_datasets = all_datasets + add_d

    name = args.input[0]
    if len(args.input) > 1:
        name = 'multiple'
    additional_ly_s='showlegend: true, legend: {x: 0.5, y: 1 }'
    if not(args.show_ci):
        generate_graph_(all_datasets, name, 'true', args.html_template, args.output, '\t', [1], [2], [0], -65336, additional_ly_str=additional_ly_s)
    else:
        generate_graph_(all_datasets, name, 'true', args.html_template, args.output, '\t', [1], [2], [0], -65336 , [3], [4], additional_ly_str=additional_ly_s)
