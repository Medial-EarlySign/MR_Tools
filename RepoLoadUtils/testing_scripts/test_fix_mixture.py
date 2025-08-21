import os, sys, argparse
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'common'))
import pandas as pd

import plotly.express as px
import plotly.graph_objs as go

from fix_factors import fixFactorsMixtureGaussian

def plot_graph(y, mode='markers+lines', save_path='/server/Linux/alon/1.html'):
    fig=go.Figure()
    df=pd.DataFrame(y, columns=['value'])
    df['signal']=1
    
    df = df[['value', 'signal']].groupby('value').count().reset_index()
    amode=mode
    fig.add_trace(go.Scatter(x=df['value'], y=df['signal'] ,mode=amode, name='histogram'))
    tmp=fig.update_xaxes(showgrid=False, zeroline=False, title='Value')
    tmp=fig.update_yaxes(showgrid=False, zeroline=False, title='Count')
    fig.layout.plot_bgcolor='white'
    fig.layout.title='Plot'
    fig.write_html(save_path)
    print('Wrote html into %s'%(save_path))

data=pd.read_csv('/tmp/debug.txt', names=['value'])

new_vals=fixFactorsMixtureGaussian(data['value'].to_numpy(), [10], 0.1, 2000, None, True)