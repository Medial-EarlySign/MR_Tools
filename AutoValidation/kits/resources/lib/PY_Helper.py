import os, sys, re, math, traceback, subprocess
import pandas as pd
import numpy as np

try:
    import med
    NO_MED=False
except:
    NO_MED=True
    print('Can\'t import med - some of the functionalities will be limited', flush=True)

try:
    import plotly.graph_objs as go
    NO_PLOTLY=False
except:
    NO_PLOTLY=True
    print('Can\'t import plotly - some of the functionalities will be limited', flush=True)

def __get_plotly_js():
    fig = go.Figure()
    html = fig.to_html(include_plotlyjs=True)
    script_element = re.compile(r'<script [^>]*>(/\*.*?)< */script>', re.DOTALL)
    res = script_element.findall(html)
    if len(res)!=1:
        print('Error in fetching js')
        return ''
    js = res[0]
    return js

def __setup_plotly_js(workdir):
    js_path = os.path.join(workdir, 'js')
    os.makedirs(js_path, exist_ok=True)
    file_path = os.path.join(js_path, 'plotly.js')
    if os.path.exists(file_path):
        return
    #Create file
    js = __get_plotly_js()
    fw=open(file_path, 'w')
    fw.write(js)
    fw.close()

def init_env(argv, py_vars, addition_back=False):
    py_vars['CURR_PT']=os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    #if addition_back:
    #    py_vars['CURR_PT']=os.path.abspath(os.path.dirname(py_vars['CURR_PT']))
    py_vars['TEST_NAME_']=os.path.basename(argv[0])
    py_vars['TEST_NAME']='.'.join(py_vars['TEST_NAME_'].split('.')[:-1])
    py_vars['CONFIG_DIR']=argv[1]
    py_vars['OVERRIDE']=int(argv[3])>0 if len(argv) > 3 else False
    #bugfix PROJECT_DIR
    SPECIFC_FOLDER=os.path.dirname(argv[1])
    BASE_DIR_CURRENT=os.path.dirname(os.path.dirname(argv[0]))
    py_vars['PROJECT_DIR'] = os.path.basename(BASE_DIR_CURRENT)
    if SPECIFC_FOLDER == BASE_DIR_CURRENT:
        with open(os.path.join(BASE_DIR_CURRENT, 'run.sh'),'r') as fr:
            lines = fr.readlines()
        lines = list(filter(lambda x:x.find('AUTOTEST_LIB')>=0, lines))
        py_vars['PROJECT_DIR'] = lines[0].split()[1]
        #py_vars['PROJECT_DIR'] = "Development"
    #Read other ENV From env.sh
    read_env(py_vars['CONFIG_DIR'], py_vars)
    test_existence(py_vars, ['WORK_DIR'], py_vars['TEST_NAME'])
    py_vars['LOG_FILE']=os.path.join(py_vars['WORK_DIR'], py_vars['TEST_NAME'] + '.log')
    fw=open(py_vars['LOG_FILE'], 'w')
    fw.close()
    __setup_plotly_js(py_vars['WORK_DIR'])

def parse_vars(p_res):
    output_res=list(filter(lambda x: len(x.strip())>0, p_res.stdout.decode('utf8').split('\n')))
    output_res=list(filter(lambda x: len(x.split('='))>=2  ,output_res))
    output_res=list(map(lambda x: [x.split('=')[0],  '='.join(x.split('=')[1:])] ,output_res))
    res=dict()
    for k,v in output_res:
        res[k]=v
    return res

def read_env(pt, py_vars):
    script_pt=os.path.join(pt, 'env.sh')
    p_res=subprocess.run(['/bin/bash', '-c', 'set -o posix ; set'], capture_output=True)
    output_res=parse_vars(p_res)
    
    ignore_keys=set(output_res.keys())
    p_res=subprocess.run(['/bin/bash', '-c', f'source {script_pt};set -o posix ; set'], capture_output=True)
    output_res_after=parse_vars(p_res)
    
    for env_var in output_res_after.keys():
        if env_var not in ignore_keys:
            env_val=output_res_after[env_var]
            py_vars[env_var] = env_val.strip('"').strip("'")
            #print(f'ADDED {env_var}={env_val}')
    return py_vars

def run_command(command, CONFIG_DIR):
    # Start the process
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True, shell=True, cwd=CONFIG_DIR)

    # Print the output line by line as it's being produced
    all_output = []
    while True:
        output = process.stdout.readline()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip(), flush=True)
            all_output.append(output.strip())

    # Get the return code
    rc = process.poll()
    return all_output, rc

def run_test(CURR_PT, PROJECT_DIR, CONFIG_DIR, test_num, override):
    #print(f'In directory {CONFIG_DIR}')
    print(f'Running: {CURR_PT}/autotest.specific_test {PROJECT_DIR} {test_num} {1 if override else 0}', flush=True)
    output, ret_code = run_command(f'{CURR_PT}/autotest.specific_test {PROJECT_DIR} {test_num} {1 if override else 0}', CONFIG_DIR)
    if ret_code != 0:
        raise Exception(f'Error in execution, return code {ret_code}')
    return output, ret_code

def test_existence(py_vars, requirements, test_name):
    all_ok=True
    for env_req in requirements:
        if env_req not in py_vars:
            print('Missing variable %s in env.sh for executing: %s'%(env_req, test_name), flush=True)
            all_ok=False
    if 'DEPENDS' in py_vars:
        dep_tests = py_vars['DEPENDS']
        if len(dep_tests)>0:
            print('Has dependent tests - running...', flush=True)
            for test_num in dep_tests:
                try:
                    res, ret_code = run_test(py_vars['CURR_PT'], py_vars['PROJECT_DIR'], os.path.dirname(py_vars['CONFIG_DIR'])
                                         ,test_num, py_vars['OVERRIDE'])
                    #print(f'Finished with ret_code: {ret_code}')
                except:
                    all_ok = False
                    raise
                #print(res, res_err)
    if not(all_ok):
        raise Exception('Error in running dependencies and testing parameters existence')
    return all_ok

def print_(log_path, *args, **kwargs):
    #Print to file:
    kwargs['flush']=True
    print(*args, **kwargs)
    fa=open(log_path, 'a')
    kwargs['file']=fa
    print(*args, **kwargs)
    fa.close()
    
def getcol(df, col, throw_error=True):
  feat=list(filter(lambda x: x.find(col)>0, df.columns))
  if len(feat)==1:
    feat=feat[0]
  elif len(feat) > 1:
    if throw_error:
      raise NameError('Found more than 1 feature correspond to %s:\n%s'%(col, '\n'.join(feat)))
    return None
  else:
    fw=os.open('/tmp/feat_list', flags=( os.O_WRONLY | os.O_CREAT | os.O_TRUNC), mode=0o777)
    os.write(fw,'\n'.join(df.columns).encode('utf-8'))
    os.close(fw)
    if throw_error:
      raise NameError('Not Found columns matching %s. please refer to /tmp/feat_list to see all options'%(col))
    return None
  return feat

def get_matrix(rep_path, model_file, samples_file, max_size=1000000):
    if NO_MED:
        print('Failed to import med - please fix and rerun to use "get_matrix"', flush=True)
        raise NameError('Failed')
    print("Reading basic Repository structure for fitting model", flush=True)
    rep = med.PidRepository()
    rep.init(rep_path)
    
    print("Reading Model", flush=True)
    model = med.Model()
    model.read_from_file(model_file)
    model.fit_for_repository(rep)
    signalNamesSet = model.get_required_signal_names() #Get list of relevant signals the model needed to fetch from repository
    
    print("Reading Samples", flush=True)
    samples = med.Samples()
    samples.read_from_file(samples_file)
    ids = samples.get_ids() #Fetch relevant ids from samples to read from repository
    
    print("Reading Repository", flush=True)
    rep.read_all(rep_path, ids, signalNamesSet) #read needed repository data
    
    #Apply model:
    nsamples=samples.nSamples()
    if nsamples> max_size:
        print('Sample size is too big, dilute to %d!!'%(max_size), flush=True)
        samples.dilute(float(max_size-1)/nsamples)
    model.apply(rep, samples)
    matrix=model.features.to_df()
    return matrix

def get_json_matrix(rep_path, model_json, samples_file, max_size=1000000):
    if NO_MED:
        print('Failed to import med - please fix and rerun to use "get_matrix"', flush=True)
        raise NameError('Failed')
    print("Reading basic Repository structure for fitting model", flush=True)
    rep = med.PidRepository()
    rep.init(rep_path)
    
    print("Reading Model", flush=True)
    model = med.Model()
    model.init_from_json_file(model_json)
    model.fit_for_repository(rep)
    signalNamesSet = model.get_required_signal_names() #Get list of relevant signals the model needed to fetch from repository
    
    print("Reading Samples", flush=True)
    samples = med.Samples()
    samples.read_from_file(samples_file)
    ids = samples.get_ids() #Fetch relevant ids from samples to read from repository
    
    print("Reading Repository", flush=True)
    rep.read_all(rep_path, ids, signalNamesSet) #read needed repository data
    
    #Apply model:
    nsamples=samples.nSamples()
    if nsamples> max_size:
        print('Sample size is too big, dilute to %d!!'%(max_size), flush=True)
        samples.dilute(float(max_size-1)/nsamples)
    model.learn(rep, samples)
    matrix=model.features.to_df()
    return matrix

def generate_percentile_vals(x_series, nticks = 4):
    x_min = x_series.min()
    x_dif = (x_series.max()-x_min)/nticks
    new_tickvals = [x_min+t*x_dif for t in range(nticks +1)]
    new_ticktext = [f' {t*100/nticks:2.1f}% <br> {new_tickvals[t]}' for t in range(nticks + 1)]
    return new_tickvals, new_ticktext

#obj is single dataframe with 2 columns, or dict of dataaframes with 2 cols each
def plot_graph(obj, save_path, title='Test', mode='markers+lines', plotly_js_path = r'W:\Graph_Infra\plotly-latest.min.js', percentile_nticks = 0):

    if NO_PLOTLY:
        raise NameError('Please setup plotly to use this feature')
    fig=go.Figure()
    amode=mode
    col_x_name=None
    col_y_name=None
    if type(obj) == dict:
        for ser_name, df in obj.items():
            x_col=df.columns[0]
            y_col=df.columns[1]
            if col_x_name is None:
                col_x_name=x_col
                col_y_name=y_col
            if mode!='bar':
                fig.add_trace(go.Scatter(x=df[x_col], y=df[y_col], mode=amode, name=ser_name))
            else:
                fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=ser_name))
            
            if percentile_nticks>0:
                new_tickvals, new_ticktext = generate_percentile_vals(df[x_col], nticks= percentile_nticks)
                fig.update_layout(
                xaxis = dict(
                tickmode = 'array',
                tickvals = new_tickvals,
                ticktext = new_ticktext
                    )
                )
    else: #dataframe
        df=obj
        col_x_name=df.columns[0]
        col_y_name=df.columns[1]
        if mode!='bar':
            fig.add_trace(go.Scatter(x=df[col_x_name], y=df[col_y_name], mode=amode, name='Test'))
        else:
            fig.add_trace(go.Bar(x=df[x_col], y=df[v_col], name='Test'))
        
        if percentile_nticks>0:
            new_tickvals, new_ticktext = generate_percentile_vals(df[x_col], nticks= percentile_nticks)
            fig.update_layout(
            xaxis = dict(
            tickmode = 'array',
            tickvals = new_tickvals,
            ticktext = new_ticktext
                )
            )   

    tmp=fig.update_xaxes(showgrid=False, zeroline=False, title=col_x_name)
    tmp=fig.update_yaxes(showgrid=False, zeroline=False, title=col_y_name)
    fig.layout.plot_bgcolor='white'
    fig.layout.title=title

    # Use __setup_plotly_js with plotly_js_path
    if not(plotly_js_path.startswith('/')): #relateive path
        base_file = os.path.realpath(os.path.join(os.path.dirname(save_path), plotly_js_path))
        base_dir = os.path.dirname(base_file)
        if base_dir.endswith('js'):
            base_dir = os.path.dirname(base_dir)
        __setup_plotly_js(base_dir)
    fig.write_html(save_path, include_plotlyjs=plotly_js_path)
    print('Wrote %s'%(save_path), flush=True)
    
def calc_kld(df1, df2, bin_by, p_name, eps=1e-4):
  x=df1.set_index(bin_by).join(df2.set_index(bin_by), how='outer', rsuffix='_r').reset_index()
  x.loc[(x[p_name].isnull()) | (x[p_name]<eps), p_name] = eps
  x.loc[ (x['%s_r'%(p_name)].isnull()) | (x['%s_r'%(p_name)]<eps) , '%s_r'%(p_name)] = eps

  kld_res=0
  entropy_p=0
  for i in range(len(x)):
    p=x.iloc[i][p_name]
    q=x.iloc[i]['%s_r'%(p_name)]
    entropy_p = entropy_p + p*math.log(p)
    kld_res = kld_res + p*(math.log(p) - math.log(q))

  entropy_p=-entropy_p
  #Compare to uniform dist:
  kld_res_d=0
  for i in range(len(x)):
    p=x.iloc[i][p_name]
    q=1.0/len(x)
    kld_res_d = kld_res_d + p*(math.log(p) - math.log(q))

  return len(x), kld_res, kld_res_d, entropy_p