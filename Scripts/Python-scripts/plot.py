#!/usr/bin/env python
import re, argparse, sys, os
import numpy as np
#Generate plotly graph from output of N columns - first 1 is X-axis, the others are different series of y label
#optional argument for template HTML path - the path should include arguments $DATA_CODE to generate JS code.  

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def _read_data(file_p, delimiter):
    if (file_p == '-'):
        lines=sys.stdin.readlines()
    else:
        fr=open(file_p, 'r')
        lines=fr.readlines()
        fr.close()
    lines = list(filter(lambda x: len(x.strip())>0,lines))
    return list(map(lambda line: list(map(lambda t: t.strip(), line.split(delimiter))),lines))

def read_data(file_p, delimiter = '\t'):
    if type(file_p) is list and len(file_p)==1:
        file_p=file_p[0]
        return _read_data(file_p, delimiter)
    elif type(file_p) is list:
        has_header=None
        all_data=[]
        for f in file_p:
            data=_read_data(f, delimiter)
            is_first_file=has_header is None
            if is_first_file:
                has_header=test_header(data[0], data[1:], False)
                #Add virtual col "FILE" to the data:
                if has_header:
                    data[0].append('FILE')
                    all_data.append(data[0])
            if has_header:
                data=data[1:]
            data = list(map(lambda row : row + [f] ,data))
            #aggregate
            all_data=all_data + data
        return all_data
    else:
        return _read_data(file_p, delimiter)
            

def read_template(template_path):
    fr=open(template_path, 'r')
    txt=fr.read()
    fr.close()
    return txt

numeric_regex=re.compile(r'^(-?)[0-9]+((\.)[0-9]+)?$')
def get_vals(data_rows, col):
    return list(map( lambda row: row[col] ,data_rows))

def get_vals_group(data_rows, col):
    return list(map( lambda row: '_'.join(np.array(row)[col]) ,data_rows))

def get_str(vec, missing_val):
    num_cnt=len(list(filter(lambda x: numeric_regex.match(x) is not None, vec)))
    all_numbers= num_cnt==len(vec)
    vec = list(map(lambda x: 'NaN' if x == str(missing_val) else x, vec))
    if all_numbers:
        return ', '.join( map(lambda x: '%s'%(x) ,vec) )
    else:
        return ', '.join( map(lambda x: '\'%s\''%(x) ,vec) )

def is_same_bool(a,b):
    return a==b

def test_header(header_tokens, data_tokens, pr=True):
    if len(data_tokens) == 0:
        raise NameError('Error - no data')
    number_re = re.compile(r'^([0-9]+|[0-9]*\.[0-9]+|[0-9]+\.[0-9]*)$')
    num_vec = list(map( lambda s : len(number_re.findall(s))>0 ,header_tokens))
    
    test_cnt=20
    #Test for first 20 rows if it is of the same types:
    no_header = None
    for i in range(0, min(test_cnt, len(data_tokens))):
        r_vec = list(map( lambda s : len(number_re.findall(s))>0 ,data_tokens[i]))
        #compare r_vec, num_vec - if same means header is like data - so no header:
        no_header = is_same_bool(r_vec, num_vec)
        if not(no_header):
            break
    
    #no_header = num_cnt == len(tokens)
    if pr:
        if not(no_header):
            sys.stderr.write('Found header\n')
        else:
            sys.stderr.write('No header\n')
    return not(no_header)
    #test if any is none numeric:

#filters apply_vec by matched indexes in filter_vec to filter_value
def filter_by_group(filter_vec, filter_value, apply_vec):
    f_idx=filter(lambda i: filter_vec[i]==filter_value ,range(0, len(apply_vec)))
    return list(map(lambda i : apply_vec[i] ,f_idx))

def get_plotly_js():
    import plotly.graph_objects as go
    fig = go.Figure()
    html = fig.to_html(include_plotlyjs=True)
    script_element = re.compile(r'<script [^>]*>(/\*.*?)< */script>', re.DOTALL)
    res = script_element.findall(html)
    if len(res)!=1:
        print('Error in fetching js')
        return ''
    js = res[0]
    return js

def fix_plotly_js(txt: str, output_path: str, force_create: bool = False) -> str:
    # Search in output path if has plotly.js, plotly.min.js etc and reference there. Otherwise create in parent folder
    valid_js_name = set(['plotly.js', 'plotly.min.js', 'plotly-latest.min.js'])
    if output_path == '-' or output_path == '':
        return txt
    dir_name = os.path.dirname(output_path)
    
    search_path = dir_name
    current_rel_path = ''
    i_try = 0
    has_js = False
    while not(has_js) and search_path != '' and search_path != '/' and i_try < 3:
        i_try += 1
        has_js = len(list(filter(lambda x: x in valid_js_name , os.listdir(search_path))))
        has_js_folder = len(list(filter(lambda x: x == 'js' , os.listdir(search_path))))
        if has_js_folder:
            current_rel_path += 'js/'
            search_path = os.path.join(search_path, 'js')
        else:
            if not(has_js):
                search_path = os.path.dirname(search_path)
                current_rel_path += '../'


    src_regex = re.compile(r'<script src *= *".*(?:plotly.js|plotly.min.js|plotly-latest.min.js)" *>')
    if has_js:
        # If we found match - change the reference to dir_name
        dir_name = search_path
        found_name = list(filter(lambda x: x in valid_js_name , os.listdir(dir_name)))[0]
        txt = src_regex.sub(f'<script src="{os.path.join(current_rel_path, found_name)}">', txt)
    else:
        # No match
        if force_create:
            js_content = get_plotly_js()
            
            # Store in current folder as plotly.js:
            found_name = 'plotly.js'
            with open(os.path.join(dir_name, found_name), 'w') as fw:
                fw.write(js_content)
            # Reference to this path:
            current_rel_path = ''
            txt = src_regex.sub(f'<script src="{os.path.join(current_rel_path, found_name)}">', txt)

    return txt

def generate_graph_(data_rows, input_file, has_header, html_template, output_path, delim, x_cols, y_cols, group_col,
                    missing_value, error_bar_y_low=None, error_bar_y_high=None, txt_cols=None, mode='scatter',
                    additional_ly_str=''):
    additional_ly_str=additional_ly_str.strip()
    if len(additional_ly_str)>0:
        additional_ly_str=','+ additional_ly_str
    if len(data_rows) == 0:
        print('EMPTY')
        return
    first_row=data_rows[0]
    nfields=len(first_row)
    if has_header == 'auto':
        has_header=test_header(first_row, data_rows[1:])
    else:
        sys.stderr.write('has_header = %s\n'%(has_header))
        has_header = str2bool(has_header)
    if has_header:
        header=first_row
        data_rows=data_rows[1:]
    else:
        header=['Y_%d'%(i) if i>0 else 'X' for i in range(nfields)]
    if len(y_cols) == 0:
        y_cols = [i for i in range(1,nfields)]
    else:
        y_cols = list(map(lambda x: int(x) ,y_cols))
    if len(x_cols) == 0:
        x_cols = [ 0 for i in range(len(y_cols))]
    else:
        x_cols = list(map(lambda x: int(x) ,x_cols))
    if len(y_cols)!=len(x_cols):
        raise NameError('Error - input x_cols(%d) must be equal size to y_cols(%d)'%(len(x_cols),len(y_cols)))
    has_labels=False
    if txt_cols is not None and len(txt_cols) > 0:
        has_labels=True
        if len(txt_cols)!=len(x_cols):
            raise NameError('Error - input x_cols(%d) must be equal size to txt_cols(%d)'%(len(x_cols),len(txt_cols)))
        txt_cols=list(map(lambda x: int(x) ,txt_cols))
    
    
    data_js=''
    txt=read_template(html_template)
    txt = fix_plotly_js(txt, output_path)
    
    #use group_col to "split" x-y cols tuples by this column value
    series_vals = ['All' for i in range(0, len(data_rows))]
    if len(group_col) > 0:
        group_col = list(map(lambda x: int(x),group_col))
        series_vals = get_vals_group(data_rows, group_col)

    all_groups=list(set(series_vals))
    all_groups = sorted(all_groups)
    
    ser_id = 0
    lbl_vals=None
    lbl_vals_f=None
    lbl_vals_str=None
    for i in range(len(x_cols)):
        x_vals = get_vals(data_rows, x_cols[i])
        y_vals = get_vals(data_rows, y_cols[i])
        if has_labels:
            lbl_vals=get_vals(data_rows, txt_cols[i])
        y_vals_low_e = None
        if error_bar_y_low is not None and len(error_bar_y_low)>0:
            y_vals_low_e = get_vals(data_rows, int(error_bar_y_low[i]))
        y_vals_high_e = None
        if error_bar_y_high is not None and len(error_bar_y_high)>0:
            y_vals_high_e = get_vals(data_rows, int(error_bar_y_high[i]))
        
        #breakpoint()
        series_name = header[y_cols[i]]
        for grp in all_groups:
            #Filter values for group from x_vals, y_vals by series_vals:
            x_vals_f = filter_by_group(series_vals, grp, x_vals)
            y_vals_f = filter_by_group(series_vals, grp, y_vals)
            additional_txt_labels=''
            additional_txt_def=''
            if has_labels:
                lbl_vals_f=filter_by_group(series_vals, grp, lbl_vals)
                lbl_vals_str=get_str(lbl_vals_f, missing_value)
                additional_txt_labels+=',\n text: [%s],\n textposition:\'auto\'\n'%(lbl_vals_str)
                additional_txt_def='+text'
            y_vals_low_e_f = None
            if y_vals_low_e is not None:
                y_vals_low_e_f = filter_by_group(series_vals, grp, y_vals_low_e)
            y_vals_high_e_f = None
            if y_vals_high_e is not None:
                y_vals_high_e_f = filter_by_group(series_vals, grp, y_vals_high_e)
            
            x_vals_str= get_str(x_vals_f, missing_value)
            y_vals_str=get_str(y_vals_f, missing_value)
            additional_error_bar=''
            if y_vals_low_e_f is not None or y_vals_high_e_f is not None:
                additional_error_bar = ',\n  error_y: { type : \'data\', symmetric: false, visible: true, \n'
                if y_vals_high_e_f is not None:
                    additional_error_bar += 'array: [%s] \n'%( ', '.join( map(lambda i: str(float(y_vals_high_e_f[i]) - float(y_vals_f[i]))
                                                                              if (float(y_vals_high_e_f[i]) != missing_value and float(y_vals_f[i]) != missing_value) else 'NaN' , range(len(y_vals_f))) ) )
                if y_vals_low_e_f is not None and y_vals_high_e_f is not None:
                    additional_error_bar += ', '
                if y_vals_low_e_f is not None:
                    additional_error_bar += 'arrayminus: [%s] \n, opacity: 0.4}\n'%( ', '.join( map(lambda i: str(float(y_vals_f[i]) - float(y_vals_low_e_f[i]))
                                                                                   if (float(y_vals_low_e_f[i]) != missing_value and float(y_vals_f[i]) != missing_value) else 'NaN', range(len(y_vals_f))) ) )
                else:
                    additional_error_bar += '\n, opacity: 0.4 }\n'
            
            if len(group_col) > 0:
                if len(x_cols) > 1:
                    series_name='%s::%s'%(grp, header[y_cols[i]])
                else:
                    series_name=grp
            data_js += """
                var series%d = {
                type: '%s',
                mode: 'lines+markers%s',
                name: '%s',
                x: [%s],
                y: [%s]%s%s
                };\n"""%(ser_id, mode, additional_txt_def, series_name, x_vals_str, y_vals_str, additional_error_bar, additional_txt_labels)
            ser_id+=1
    
    
    x_tit = 'X'
    y_tit='Y'
    if has_header:
        x_tit = header[x_cols[0]]
        if len(x_cols) == 1:
            y_tit = header[y_cols[0]]
    data_js += 'var data = [%s];\n'%( ', '.join( map(lambda i: 'series%d'%(i) , range(ser_id) ) ) )
    data_js += """ 
    
    var layout = { 
      title: '%s',
      xaxis: { title : '%s'}, 
      yaxis: { title: '%s'},
      height: 800, 
      width: 1200
      %s
    };
    Plotly.newPlot('myDiv', data, layout);
    """%(input_file, x_tit, y_tit, additional_ly_str)
    txt=txt.replace('$DATA_CODE', data_js)
    
    if output_path == '-':
        print(txt)
    else:
        fw=open(output_path, 'w')
        fw.write(txt)
        fw.close()
        sys.stderr.write('Wrote html into %s\n'%(output_path))
        
def generate_graph(input_file, has_header, html_template, output_path, delim, x_cols, y_cols, txt_cols_data, group_col, missing_value, graph_md, layout_str,
                   err_y_cols_low, err_y_cols_high):
    data_rows=read_data(input_file, delim)
    if len(input_file)==1:
        input_file=input_file[0]
    else:
        input_file='Multiple Files'
    generate_graph_(data_rows, input_file, has_header, html_template, output_path, delim, x_cols, y_cols, group_col, missing_value, txt_cols=txt_cols_data,
                    mode=graph_md, additional_ly_str=layout_str, error_bar_y_low=err_y_cols_low, error_bar_y_high= err_y_cols_high)

if __name__ == '__main__':
    par=os.path.dirname(__file__)
    if (par==''):
        par='.'
    def_template=os.path.join( par, 'templates', 'plotly_graph.html')
    parser = argparse.ArgumentParser(description = "Plot HTML Graph")
    parser.add_argument("--input",help="input file path - for stdin",default=['-'], nargs='+')
    parser.add_argument("--output",help="output path - for stdout",default='-')
    parser.add_argument("--html_template",help="html template path",default=def_template)
    parser.add_argument("--has_header",help="True if input has header",default='auto')
    parser.add_argument("--delim",help="delimeter",default='\t')
    parser.add_argument("--x_cols",help="comma delimeted of x cols (default is first columns). starts from 0", nargs='+',default=[])
    parser.add_argument("--y_cols",help="comma delimeted of y cols (default is rest of the columns except 0). starts from 0", nargs='+',default=[])
    parser.add_argument("--err_y_cols_low",help="comma delimeted of error y cols (default is empty). suppose to be same size as y cols", nargs='+',default=[])
    parser.add_argument("--err_y_cols_high",help="comma delimeted of error y cols (default is empty). suppose to be same size as y cols", nargs='+',default=[])
    parser.add_argument("--txt_cols",help="comma delimeted of label cols. default is no labels. otherwise same size as x nd y", nargs='+',default=[])
    parser.add_argument("--graph_mode",help="default is scatter, can be [scatter, bar]",default='scatter')
    parser.add_argument("--layout_str",help="additional_str to layout",default='')
    parser.add_argument("--group_col",help="column to seperate into groups - if < 0 no such a column",default=[], nargs='+')
    parser.add_argument("--missing_value",help="missing value number", type=float,default=-65336)
    args = parser.parse_args()
    generate_graph(args.input, args.has_header, args.html_template, args.output, args.delim,
                   args.x_cols, args.y_cols, args.txt_cols, args.group_col, args.missing_value, args.graph_mode,
                   args.layout_str, args.err_y_cols_low, args.err_y_cols_high)
    