#!/nas1/Work/python-env/python38/bin/python
import os, sys, argparse
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'common'))

from utils import fixOS, read_tsv
from staging_config import ThinLabs
from stage_to_signals import numeric_to_files

import pandas as pd
import plotly.express as px
import plotly.graph_objs as go

def plot_graph(df, mode='markers+lines', save_path='/server/Linux/alon/1.html'):
    fig=go.Figure()
    df = df[['value', 'signal']].groupby('value').count().reset_index()
    amode=mode
    fig.add_trace(go.Scatter(x=df['value'], y=df['signal'] ,mode=amode, name='histogram'))
    tmp=fig.update_xaxes(showgrid=False, zeroline=False, title='Value')
    tmp=fig.update_yaxes(showgrid=False, zeroline=False, title='Count')
    fig.layout.plot_bgcolor='white'
    fig.layout.title='Plot'
    fig.write_html(save_path)
    print('Wrote html into %s'%(save_path))

def get_signal_graph(bs_path, sig, out_path): 
    all_files=os.listdir(bs_path)
    all_sigs_files=list(filter(lambda x: x.startswith('%s_thinlabs_'%(sig)) ,all_files))
    #read vals:
    all_x=None
    for f in all_sigs_files:
        print('Read %s'%(os.path.join(bs_path,f)))
        df=pd.read_csv(os.path.join(bs_path, f), sep='\t', names=['pid', 'signal', 'date', 'value', 'ignore', 'unit', 'source'])
        if all_x is None:
            all_x=df
        else:
            all_x=all_x.append(df, ignore_index=True)
    #This is before
    plot_graph(all_x, 'markers+lines', out_path)
    return all_x

def recalc_values(sig):
    cfg=Configuration()
    db_cfg=ThinLabs()

    special_cases = ['CHADS2', 'CHADS2_VASC']
    code_folder = fixOS(cfg.code_folder)
    print('config folder : %s'%(code_folder))
    out_folder = '/tmp'
    out_folder_dbg='/tmp/debug'
    os.makedirs(out_folder_dbg, exist_ok=True)
    all_files=os.listdir(out_folder)
    all_sigs_files=list(filter(lambda x: x.startswith('%s_thinlabs_'%(sig)) ,all_files))
    for f in all_sigs_files:
        full_f = os.path.join(out_folder,f)
        print('Remove %s to rewrite it'%(full_f))
        os.remove(full_f)

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == db_cfg.TABLE)
    th_map_numeric = th_map[(th_map['type'] == 'numeric') & lab_chart_cond & ~(th_map['signal'].isin(special_cases))]
    th_map_numeric = th_map_numeric[th_map_numeric['signal'] != 'STOPPED_SMOKING']
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                    names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    th_map_numeric= th_map_numeric[th_map_numeric['signal']==sig]
    special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    #print(unit_mult[unit_mult['signal']==sig])
    numeric_to_files(db_cfg, th_map_numeric, unit_mult, special_factors_signals, id2nr, out_folder, suff='_'+db_cfg.TABLE+'_', main_cond = 'code', debug_input=out_folder_dbg)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Recalc signal with UnitTranslator")
    parser.add_argument("--sig",help="signal name", required=True)
    parser.add_argument("--config_path",help="Configuration path", default=os.path.join(os.environ['MR_ROOT'],'Tools', 'RepoLoadUtils', 'thin21_etl'))
    parser.add_argument("--output",help="Outout html folder", default='/server/Linux/alon')
    args = parser.parse_args()
    
    sys.path.append(args.config_path)
    from Configuration import Configuration
    from generate_id2nr import get_id2nr_map
    
    print('Ran from folder %s'%(args.config_path))
    cfg=Configuration()
    bs_path =os.path.join( fixOS( cfg.work_path), 'FinalSignals')

    b_val = get_signal_graph(bs_path, args.sig, os.path.join(args.output, 'before.html'))
    #Recalc again
    recalc_values(args.sig)
    #read values again:
    a_val = get_signal_graph('/tmp', args.sig, os.path.join(args.output, 'after.html'))
