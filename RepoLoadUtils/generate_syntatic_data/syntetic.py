import pandas as pd
import numpy as np
import med, random, os, pickle
import plotly.express as px
import plotly.graph_objs as go

class Gen_Params:
    def __init__(self):
        self.start_year=2010
        self.end_year=2020
        self.trim_age=90
        self.min_age=18
        self.gender_rate=0.5
        #get age density
        self.age_params = None
        #hgb params for function as age,gender - mean,std for each bin:
        self.hgb_params = None
        #CRP fully syntetic - different resolution - jumps of 8 or something like that
        self.crp_params = None
        
    def save(self, pt):
        with open(pt, 'wb') as handle:
            pickle.dump(self, handle)
            
    def load(self,pt):
        with open(pt, 'rb') as handle:
            data = pickle.load(handle)
            self.start_year = data.start_year
            self.end_year = data.end_year
            self.trim_age = data.trim_age
            self.min_age = data.min_age
            self.gender_rate = data.gender_rate
            self.age_params = data.age_params
            self.hgb_params = data.hgb_params
            self.crp_params = data.crp_params

def get_params(params, rep_path, current_year=2021):
    rep=med.PidRepository()
    rep.read_all(rep_path, [], ['BYEAR', 'GENDER', 'Hemoglobin', 'CRP'])
    byear = rep.get_sig('BYEAR').rename(columns={'val0': 'val'}).rename(columns={'val': 'byear'})
    gender = rep.get_sig('GENDER').rename(columns={'val0': 'val'}).rename(columns={'val': 'sex'})
    #estimate age for current_year
    
    age = current_year - byear['byear']
    age = age[age>=params.min_age]
    age[age>=params.trim_age] = params.trim_age
    age_hist=pd.DataFrame({'age':age, 'cnt':1}).groupby('age').count().reset_index()
    age_hist['prob']=age_hist.cnt/len(age)
    params.age_params = age_hist[['age', 'prob']]
    #calc hgb dependence:
    hgb = rep.get_sig('Hemoglobin').rename(columns={'val0': 'val'}).rename(columns={'time0': 'time'}).rename(columns={'date': 'time'})
    hgb=hgb[(hgb.val> 0) & (hgb.val<50)].reset_index(drop=True)
    hgb=hgb.set_index('pid').join(byear.set_index('pid')).reset_index()
    hgb['age'] = hgb.time//10000 - hgb['byear']
    hgb=hgb.set_index('pid').join(gender.set_index('pid'), on=['pid']).reset_index()
    hgb = hgb[hgb.age>=params.min_age].reset_index(drop=True)
    hgb.loc[hgb.age >=  params.trim_age ,'age'] = params.trim_age
    params.hgb_params = hgb.groupby(['age', 'sex']).val.agg(['mean', 'std']).reset_index()[['age', 'sex', 'mean', 'std']]
    params.hgb_params.loc[params.hgb_params['std'].isnull(), 'std'] = np.random.rand(sum(params.hgb_params['std'].isnull()))*3
    params.hgb_params.loc[params.hgb_params['mean']<=2, 'mean'] = 12 + np.random.rand(sum(params.hgb_params['mean']<=2))
    
    #get CRP params - get probs:
    crp = rep.get_sig('CRP').rename(columns={'val0': 'val'}).rename(columns={'time0': 'time'}).rename(columns={'date': 'time'})
    crp_hist=crp.groupby('val').pid.count().reset_index().rename(columns={'pid': 'cnt'})
    crp_hist['prob'] = crp_hist.cnt/ len(crp)
    params.crp_params = crp_hist[['val', 'prob']]
    
    return params

def plot_graph(x_data, y_data, mode='markers+lines', save_path='/tmp/1.html', order_names=None):
    fig=go.Figure()
    amode=mode
    if type(x_data) == dict:
        if order_names is None:
            for g_name, x_d in x_data.items():
                if mode=='bar':
                    fig.add_trace(go.Bar(x=x_d, y=y_data[g_name], name=g_name))
                else:
                    fig.add_trace(go.Scatter(x=x_d, y=y_data[g_name], mode=amode, name=g_name))
        else:
            for g_name in order_names:
                if mode=='bar':
                    fig.add_trace(go.Bar(x=x_data[g_name], y=y_data[g_name], name=g_name))
                else:
                    fig.add_trace(go.Scatter(x=x_data[g_name], y=y_data[g_name], mode=amode, name=g_name))
    else:
        if mode=='bar':
            fig.add_trace(go.Bar(x=x_data, y=y_data, name='trace_1'))
        else:
            fig.add_trace(go.Scatter(x=x_data, y=y_data, mode=amode, name='trace_1'))
    tmp=fig.update_xaxes(showgrid=False, zeroline=False, title='X')
    tmp=fig.update_yaxes(showgrid=False, zeroline=False, title='Y')
    fig.layout.plot_bgcolor='white'
    fig.layout.title='Plot'
    fig.write_html(save_path, include_plotlyjs=r'W:\Graph_Infra\plotly-latest.min.js')
    print('Wrote %s'%(save_path))

def generate_patient_data(count, params, current_year=2021):
    #Generate Gender data (indipendent):
    all_sexes=(np.random.rand(count)>=params.gender_rate).astype(int)+1
    all_ids=np.asarray(range(count))+1
    gender_data = pd.DataFrame({'sex':all_sexes, 'pid':all_ids})
    #save gender
    
    #Generate Byear data based on params
    min_year=current_year-params.trim_age
    max_year=current_year-params.min_age
    age=current_year - np.asarray(range(min_year,max_year))
    year_age=pd.DataFrame({'age':age, 'year': np.asarray(range(min_year,max_year))})
    year_prob=params.age_params.set_index('age').join(year_age.set_index('age'), on='age').reset_index()[['age','year','prob']]
    year_prob = year_prob.sort_values('age')[['year', 'prob']]
    byear_data=np.random.choice(year_prob.year, count, p=year_prob.prob)
    byear_df = pd.DataFrame({'birth_year':byear_data, 'pid':all_ids})
    #save byear_df
    
    #Now generate hgb:
    hgb_years= np.random.randint(params.start_year, params.end_year+1, count)
    full_date= hgb_years*10000 + np.random.randint(1, 13, count)*100 + np.random.randint(1, 29, count)
    pid_data = pd.DataFrame({'byear': byear_data, 'sex': all_sexes, 'date_year':hgb_years, 'full_date':full_date})
    pid_data['age']=pid_data.date_year-pid_data.byear
    pid_data.loc[pid_data['age']<params.min_age,'age'] = params.min_age
    pid_data.loc[pid_data['age']>params.trim_age,'age'] = params.trim_age
    pid_data['hgb']=0
    #randomly set values for each params.hgb_params['age', 'sex']:
    for i in range(len(params.hgb_params)):
        age=params.hgb_params.iloc[i].age
        sex=params.hgb_params.iloc[i].sex
        filt=(pid_data.age==age) & (pid_data.sex==sex)
        raw_vals = np.random.normal(params.hgb_params.iloc[i]['mean'],params.hgb_params.iloc[i]['std'],sum(filt))
        raw_vals[raw_vals<2]=4+np.random.rand(sum(raw_vals<2))
        pid_data.loc[filt ,'hgb'] = raw_vals
    
    hgb_data=pid_data[['full_date', 'hgb']].rename(columns={'hgb':'val'})
    hgb_data['val'] = np.round(hgb_data['val']*10)/10.0
    hgb_data['pid'] = all_ids
    #save hgb_data
    #generate crp:
    crp_years= np.random.randint(params.start_year, params.end_year+1, count)
    full_date= crp_years*10000 + np.random.randint(1, 13, count)*100 + np.random.randint(1, 29, count)
    crp_arr=np.random.choice(params.crp_params.val, count, p=params.crp_params.prob)
    crp_data = pd.DataFrame({'full_date':full_date, 'pid': all_ids, 'val': crp_arr})
    #save crp_data
    return gender_data, byear_df, hgb_data, crp_data
    
    
def generate_THIN(count, save_path, extract_year=2015):
    params = Gen_Params()
    params.trim_age=150
    params.min_age=0
    params.start_year=2008
    params.end_year=2015
    params.gender_rate = 0.5
    params=get_params(params,'/home/Repositories/THIN/thin_2018/thin.repository', current_year=extract_year)
    gender_data, byear_df, hgb_data, crp_data = generate_patient_data(count, params, current_year=extract_year)
    
    os.makedirs(save_path, exist_ok=True)
    os.makedirs(os.path.join(save_path, 'Tests'), exist_ok=True)
    gender_data.to_csv(os.path.join(save_path, 'gender.csv'), sep=',', header=True, index=False)
    byear_df.to_csv(os.path.join(save_path, 'byear.csv'), sep=',', header=True, index=False)
    hgb_data.to_csv(os.path.join(save_path, 'hgb.csv'), sep=',', header=True, index=False)
    crp_data.to_csv(os.path.join(save_path, 'crp.csv'), sep=',', header=True, index=False)
    
    xx=hgb_data.groupby('val').pid.count().reset_index()
    plot_graph(xx.val, xx.pid, save_path=os.path.join(save_path, 'Tests', 'hgb.html'))
    xx=crp_data.groupby('val').pid.count().reset_index()
    plot_graph(xx.val, xx.pid, save_path=os.path.join(save_path, 'Tests', 'crp.html'))
    xx=byear_df.groupby('birth_year').pid.count().reset_index()
    plot_graph(xx.birth_year, xx.pid, save_path=os.path.join(save_path, 'Tests', 'byear.html'))
    
    return gender_data, byear_df, hgb_data, crp_data, params
    
#Change years, age triming, crp - resolution. THIN,IBM

def gen_ibm(count, save_path):
    params=Gen_Params()
    params.load('/nas1/Temp/Data3/ibm_params')
    params.hgb_params.sex=params.hgb_params.sex.astype('string')
    params.hgb_params.loc[params.hgb_params.sex=='Male|1', 'sex']='1'
    params.hgb_params.loc[params.hgb_params.sex=='Female|2', 'sex']='2'
    params.hgb_params=params.hgb_params[params.hgb_params.sex!='Undefined Category'].reset_index(drop=True)
    params.hgb_params.sex=params.hgb_params.sex.astype(int)
    #fetch CRP from MHS:
    rep=med.PidRepository()
    rep.read_all('/home/Repositories/MHS/build_Feb2016_Mode_3/maccabi.repository', [], ['CRP'])
    crp = rep.get_sig('CRP').rename(columns={'val0': 'val'}).rename(columns={'time0': 'time'}).rename(columns={'date': 'time'})
    crp_hist=crp.groupby('val').pid.count().reset_index().rename(columns={'pid': 'cnt'})
    crp_hist['prob'] = crp_hist.cnt/ len(crp)
    params.crp_params = crp_hist[['val', 'prob']]
    
    gender_data, byear_df, hgb_data, crp_data = generate_patient_data(count, params, current_year=2021)
    
    os.makedirs(save_path, exist_ok=True)
    os.makedirs(os.path.join(save_path, 'Tests'), exist_ok=True)
    gender_data.to_csv(os.path.join(save_path, 'gender.csv'), sep=',', header=True, index=False)
    byear_df.to_csv(os.path.join(save_path, 'byear.csv'), sep=',', header=True, index=False)
    hgb_data.to_csv(os.path.join(save_path, 'hgb.csv'), sep=',', header=True, index=False)
    crp_data.to_csv(os.path.join(save_path, 'crp.csv'), sep=',', header=True, index=False)
    
    xx=hgb_data.groupby('val').pid.count().reset_index()
    xx.pid=xx.pid/len(hgb_data)*100
    plot_graph(xx.val, xx.pid, save_path=os.path.join(save_path, 'Tests', 'hgb.html'))
    xx=crp_data.groupby('val').pid.count().reset_index()
    xx.pid=xx.pid/len(hgb_data)*100
    plot_graph(xx.val, xx.pid, save_path=os.path.join(save_path, 'Tests', 'crp.html'))
    xx=byear_df.groupby('birth_year').pid.count().reset_index()
    xx.pid=xx.pid/len(hgb_data)*100
    plot_graph(xx.birth_year, xx.pid, save_path=os.path.join(save_path, 'Tests', 'byear.html'))
    
    return gender_data, byear_df, hgb_data, crp_data, params
gender_data, byear_df, hgb_data, crp_data, params = gen_ibm(3263742, '/nas1/Temp/Data3')