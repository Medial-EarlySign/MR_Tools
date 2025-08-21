import json, argparse
import pandas as pd

class pred_data:
    def __init__(self):
        self.pid=None
        self.time=None
        self.score=None
    
    def __repr__(self):
        return "pid: %d, time: %d, score: %f"%(self.pid, self.time, self.score)
    def __str__(self):
        return "pid: %d, time: %d, score: %f"%(self.pid, self.time, self.score)
    
    def parse_js(self, js, score_field_name = 'prediction'):
        if 'patient_id' in js:
            self.pid= int(js['patient_id'])
        elif 'pid' in js:
            self.pid= int(js['pid'])
        else:
            raise NameError('Can\'t find patient id')
        self.time= int(js['time'])
        self.score= float(js[score_field_name])
    
    def parse_med_samples_line(self, line):
        tokens=line.split('\t')
        self.pid= int(tokens[1].strip())
        self.time= int(tokens[2].strip())
        self.score=float(tokens[6].strip())
        

def parse_js_obj(js, score_field_name = 'prediction'):
    x=pred_data()
    x.parse_js(js,score_field_name)
    return x

def parse_sample_obj(line):
    x=pred_data()
    x.parse_med_samples_line(line)
    return x

def read_resp_json(path):
    print('Reading %s'%(path))
    fr=open(path, 'r')
    data=fr.read()
    fr.close()
    x=json.loads(data)
    x=x['responses']
    n=len(x)
    x=list(map(parse_js_obj ,x))
    print('Done')
    x=convert_df(x)
    return x
    
def read_med_samples(path):
    print('Reading %s'%(path))
    fr=open(path, 'r')
    data=fr.readlines()
    fr.close()
    data=data[1:]
    data=list(map(parse_sample_obj,data))
    print('Done')
    data=convert_df(data)
    return data

def convert_df(ls_preds):
    df=pd.DataFrame(columns= {'pid': [], 'time': [], 'score': []})
    df['pid']= list(map(lambda x: x.pid ,ls_preds))
    df['time']= list(map(lambda x: x.time ,ls_preds))
    df['score']= list(map(lambda x: x.score ,ls_preds))
    return df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = "Compare json results to am")
    parser.add_argument("--json_resp_path",help="the input path of algomarker response json",required=True)
    parser.add_argument("--preds_path",help="the input path of preds file",required=True)
    
    args = parser.parse_args() 
    json_data=read_resp_json(args.json_resp_path)
    samples_data=read_med_samples(args.preds_path)
    res=json_data.set_index(['pid', 'time']).join(samples_data.set_index(['pid', 'time']), how='inner', lsuffix='_json').reset_index()
    if len(res)!=len(json_data):
        print('Not same size %d, %d'%(len(res),len(json_data)))
    res=res[res['score_json']>-9999].reset_index(drop=True)
    print('Can compare %d'%(len(res)))
    res['diff'] = abs(res.score-res.score_json)
    print('max diff %f'%(res['diff'].max()))
    cnt=len(res[res['diff'] > 1e-6])
    print('has %d above 1e-6'%(cnt))
    bad=res[res['diff'] > 1e-6].sort_values('diff', ascending=False).reset_index(drop=True)
    print(bad.head())
    if cnt > 0:
        print('Failed!')
    else:
        print('Good!')

