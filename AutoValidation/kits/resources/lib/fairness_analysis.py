import os, sys, re, subprocess
from reformat_bt_filter import transform_from_bt_filter_to_cohrt

INFRA_PATH = os.path.dirname(subprocess.check_output(['which', 'plt_bt.py']).decode('UTF-8').rstrip())
sys.path.insert(0, INFRA_PATH)
from plt_bt import perpare_bt_graph
from plot import generate_graph_

def read_fairness_analysis(pt):
    fr=open(pt,'r')
    lines=fr.readlines()
    fr.close()
    
    lines = list( filter(lambda x: len(x)>0 and not(x.startswith('#')) ,map(lambda x: x.strip(), lines)))
    res=[]
    for line in lines:
        tokens=line.split('\t')
        if len(tokens)!=2:
            raise NameError('Error - must specify 1 tab to alias the groups')
        defs, aliases= tokens
        defs_grp= defs.split('|')
        aliases_grp= aliases.split('|')
        if len(defs_grp)!=len(aliases_grp):
            raise NameError('Error - must have the same number of groups in both token (definitions and aliasing). Group seperator is "|"')
        res.append( [defs_grp, aliases_grp] )
    return res

def rename_cohort(row, filter_cohort, fairness_defs, fairness_names):
    if row[0] == filter_cohort:
        row[0]= 'All'
        return row
    if row[0].startswith(filter_cohort):
        row[0]=row[0][len(filter_cohort)+1:]
    if row[0].endswith(filter_cohort):
        row[0]=row[0][:-len(filter_cohort)-1]
    # find index in fairness_defs
    for i, def_grp in enumerate(fairness_defs):
        feat, range_def = def_grp.split(':')
        low, high = range_def.split(',')
        low = float(low)
        high = float(high)
        def_grp_n = f'{feat}:{low:.3f}-{high:.3f}'
        if row[0].find(def_grp_n) >=0:
            row[0] = row[0].replace(def_grp_n, fairness_names[i])
            break
    return row

#Plot SENS@SCORE from bootstrap based on groups:
def plot_graphs(bt_input_path, filter_regex_cohort_filter, fairness_groups, output, html_template = None):
    if html_template is None:
        html_template =os.path.join(INFRA_PATH, 'templates', 'plotly_graph.html')
    filter_regex_cohort = transform_from_bt_filter_to_cohrt(filter_regex_cohort_filter)
    for fairness_defs, fairness_names in fairness_groups:
        #Build filter_cohorts from fairness_defs
        filter_cohorts=''
        fname=None
        for fd in fairness_defs:
            if len(filter_cohorts) > 0:
                filter_cohorts = filter_cohorts + '|'
            filter_name, ranges=fd.split(':')
            low_r, high_r = ranges.split(',')
            if fname is None:
                fname = filter_name
            if fname != filter_name:
                raise NameError('Has multiple filters on different fields - not allowed')
            
            filter_cohorts = filter_cohorts + filter_name + ':' + '%2.3f'%(float(low_r)) + '-' + '%2.3f'%(float(high_r))
        
        filter_cohorts = '(' + filter_cohorts + ')'
        
        filter_cohorts = filter_regex_cohort + ',' + filter_cohorts + '|' + filter_cohorts + ',' + filter_regex_cohort + '|(^' + filter_regex_cohort + '$)'
        data=perpare_bt_graph(bt_input_path, 'SENS@SCORE', filter_cohorts, True, True)
        #Rename cohorts:
        data=list(map( lambda x: rename_cohort(x, filter_regex_cohort, fairness_defs, fairness_names) ,data))
        all_datasets=data
            
        name = 'Comparing %s'%(','.join(fairness_names))
        
        os.makedirs(output, exist_ok=True)
        generate_graph_(all_datasets, name, 'true', html_template, os.path.join(output, '%s_%s.html'%(filter_name, '-'.join(fairness_names))), '\t', [1], [2], [0], -65336 , [3], [4])

if __name__ == '__main__':
    if len(sys.argv)<5:
        raise NameError('Please provide 4 inputs')
    bt_input_path=sys.argv[1]
    output=sys.argv[2]
    cfg_fairness=read_fairness_analysis(sys.argv[3])
    filter_regex_cohort=sys.argv[4]
    plot_graphs(bt_input_path, filter_regex_cohort, cfg_fairness, output)
