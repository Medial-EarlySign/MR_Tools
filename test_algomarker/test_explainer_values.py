import json
import sys
import pandas as pd
from show_explainer_output import parse_patient

FILE_PATH='/nas1/Products/GastroFlag/QA_Versions/GastroFlag_20250210_15:23:08/minimal_score_compare/resp.butwhy.json'
if len(sys.argv)>1:
    FILE_PATH=sys.argv[1]
fr=open(FILE_PATH, 'r')
txt=fr.read()
fr.close()
js=json.loads(txt)
js=js['responses']
data=list(map(parse_patient, js))

data_f=list(filter(lambda x: len(x.explainer_output) >0 ,data))
df=pd.DataFrame(map(lambda x: x.to_dict(),data_f))
dff = []
for i in range(3):
    df_i =df[[f'contrib_{i}.name', f'contrib_{i}.level', f'contrib_{i}.value', f'contrib_{i}.percentage']].copy()
    df_i.columns = ['name', 'level', 'value', 'percentage']
    df_i['order'] = i
    dff.append(df_i)
dff = pd.concat(dff, ignore_index=True)

(5*(dff['percentage']//5)).value_counts()
dff['level'].value_counts()
dff['name'].value_counts()

print(abs(dff['value'].round(1)).value_counts().reset_index().sort_values('value'))
NUM_GRPS=4
MAX_TH=2.5

dff['level_recalc']=(dff['value'].abs()/(MAX_TH/NUM_GRPS))//1+1
dff.loc[dff['level_recalc'] > NUM_GRPS, 'level_recalc'] = NUM_GRPS
print((dff['level']-dff['level_recalc']).abs().sum())

# Suggest different MAX_TH:
print(dff[dff['order']==0]['value'].quantile(0.999))

MAX_TH=2.5
dff['level_recalc']=(dff['value'].abs()/(MAX_TH/NUM_GRPS))//1+1
dff.loc[dff['level_recalc'] > NUM_GRPS, 'level_recalc'] = NUM_GRPS

dff['level_recalc'].value_counts()
d=dff[dff['order']==0]['level_recalc'].value_counts().reset_index().sort_values('level_recalc')
d['p']=d['count']/d['count'].sum()*100