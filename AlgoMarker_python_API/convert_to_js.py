import pandas as pd
import json
import os
DATA_FILE = '/nas1/Work/Users/Alon/LGI/outputs.MHS/test_data/data.tsv'
df=pd.read_csv(DATA_FILE, sep='\t')
df=df.rename(columns={'Signal':'code', 'Time':'timestamp', 'Value':'value'})

js= df.to_json(orient='records')
js=json.loads(js)

def tranf(x):
  xx=dict()
  xx['code'] = x['code'].strip()
  xx['data']=[dict()]
  xx['data'][0]['timestamp'] =[]
  xx['data'][0]['value'] =[]
  if x['timestamp'] is not None:
    xx['data'][0]['timestamp'] = [int(x['timestamp'])]
  xx['data'][0]['value'] = [x['value']]
  return xx

js = list(map(lambda x: tranf(x) ,js))


js_see=dict()
for ele in js:
  if ele['code'] not in js_see:
    js_see[ele['code']] = []
  js_see[ele['code']].append(ele)

js_combine = []  
for  sig,data in js_see.items():
  e = dict()
  e['code'] = sig
  e['data'] = list(map(lambda x:x['data'][0] , data))
  js_combine.append(e)
  
final_dict=dict()
final_dict['request_id'] = 'test'
final_dict['load'] = 1
final_dict["type"] = "request"
final_dict['export'] = {'prediction':'pred_0'}
final_dict['requests'] = []
final_dict['requests'].append({'patient_id':"1", 'time':'20240630', 'data': {'signals': js_combine} })
result_js_string = json.dumps(final_dict, indent=True)

#print(result_js_string)
OUTPUT = os.path.join(os.path.dirname(DATA_FILE), 'result.json')
fw = open(OUTPUT, 'w')
fw.write(result_js_string)
fw.close()
print(f'Wrote {OUTPUT}')