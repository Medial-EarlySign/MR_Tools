from typing import Any, Dict
import urllib.parse
import multiprocess
import multiprocess.pool
import requests
import asyncio
import urllib
import json
import random
import multiprocessing as mp
from tqdm import tqdm
import time
import os
from datetime import datetime

def get_input_json(json_path:str) -> str:
    with open(json_path, 'r') as fr:
        txt = fr.read()
    js = json.loads(txt)
    return js

async def call_api(base_url:str, json_req:Dict[Any,Any], call_clear:bool = False) -> Dict[Any,Any]:
    #json_req['requests'][0]['patient_id']= str(random.randint(1, 2**31-1))
    js_data = json.dumps(json_req)
    if call_clear:
        resp_clear = requests.request('POST', urllib.parse.urljoin(base_url, 'clear_data'))
        resp_clear.raise_for_status()
    resp = requests.request('POST', urllib.parse.urljoin(base_url, 'calculate'), data=js_data)
    resp_js = resp.json()
    #resp_clear = requests.request('POST', urllib.parse.urljoin(base_url, 'clear_data'), data=json_req)
    #resp_clear.raise_for_status()
    return resp_js

def call_sync(base_url:str, json_req:Dict[Any,Any], output_dir:str, call_clear:bool = False, sleep = 0):
    res = asyncio.run(call_api(base_url, json_req, call_clear))
    if 'responses' not in res or 'prediction' not in res['responses'][0] or res['responses'][0]['prediction']!='0.053654':
        full_path = os.path.join(output_dir, f'rep_{datetime.now()}')
        with open(full_path, 'w') as fw:
            fw.write(json.dumps(res))
        print(f'Wrote {full_path}')
    if sleep > 0 :
        time.sleep(sleep)

async def call_async(base_url:str, json_req:Dict[Any,Any], output_dir:str, call_clear:bool = False, sleep = 0):
    res = await call_api(base_url, json_req, call_clear)
    if 'responses' not in res or 'prediction' not in res['responses'][0] or res['responses'][0]['prediction']!='0.053654':
        full_path = os.path.join(output_dir, f'rep_{datetime.now()}')
        with open(full_path, 'w') as fw:
            fw.write(json.dumps(res))
        print(f'Wrote {full_path}')
    #else:
        #print('Done OK')
    if sleep > 0 :
        time.sleep(sleep)

def call_sync_add_data(base_url:str, json_req_data:Dict[Any,Any], json_req:Dict[Any,Any], output_dir:str, sleep = 0):
    resp_clear = requests.request('POST', urllib.parse.urljoin(base_url, 'clear_data'))
    resp_clear.raise_for_status()
    resp_data = add_data(base_url, json_req_data)
    if 'messages' not in resp_data or len(resp_data['messages'])>0:
        print(f'Error in add data: {resp_data}')
        return
    js_data = json.dumps(json_req)
    resp = requests.request('POST', urllib.parse.urljoin(base_url, 'calculate'), data=js_data)
    res = resp.json()
    if 'responses' not in res or 'prediction' not in res['responses'][0] or res['responses'][0]['prediction']!='0.053654':
        full_path = os.path.join(output_dir, f'rep_{datetime.now()}')
        with open(full_path, 'w') as fw:
            fw.write(json.dumps(res))
        print(f'Wrote {full_path}')
    if sleep > 0 :
        time.sleep(sleep)

def add_data(base_url:str, json_req:Dict[Any,Any]):
    js_data = json.dumps(json_req)
    resp = requests.request('POST', urllib.parse.urljoin(base_url, 'add_data'), data=js_data)
    resp_js = resp.json()
    return resp_js

def calulate_req(base_url:str, json_req:Dict[Any,Any]):
    js_data = json.dumps(json_req)
    resp = requests.request('POST', urllib.parse.urljoin(base_url, 'calculate'), data=js_data)
    resp_js = resp.json()
    return resp_js

def call_async_join(base_url:str, json_req:Dict[Any,Any], output_dir:str, call_clear:bool = False, sleep = 0):
    start_time = datetime.now()
    #print(f'Starting {start_time}')
    res = asyncio.run(call_async(base_url, json_req, output_dir, call_clear, sleep))
    end_time = datetime.now()
    #print(f'Done {start_time} @ {end_time}, took: {(end_time-start_time).total_seconds()}')
    return res

def call_async_join_map(args: Dict[Any,Any]):
    call_async_join(**args)

random.seed()
base_url = 'http://localhost:8001'
js_data = get_input_json('/nas1/Products/LungCancer/QA_Versions/LungFlag4.NEW.2024-05-08.With_Calibration.With_ButWhy/examples/req.full.json')
output_dir = '/tmp/res'
MAX_REQUESTS_CNT = 1000
async_allowed = True

js_data_single = get_input_json('/nas1/Products/LungCancer/QA_Versions/LungFlag4.NEW.2024-05-08.With_Calibration.With_ButWhy/examples/data.single.json')
js_req_single = get_input_json('/nas1/Products/LungCancer/QA_Versions/LungFlag4.NEW.2024-05-08.With_Calibration.With_ButWhy/examples/req.single.json')
os.makedirs(output_dir, exist_ok=True)

st_time = datetime.now()
for i in tqdm(range(MAX_REQUESTS_CNT)):
    if async_allowed:
        call_sync(base_url, js_data, output_dir, False, 0)
    else:
        call_sync_add_data(base_url, js_data_single, js_req_single, output_dir, 0)
sync_time = ( datetime.now()- st_time).total_seconds()
print(f'Took {sync_time} for sync calls')

#msgs = add_data(base_url, js_data_single)
#resp_clear = requests.request('POST', urllib.parse.urljoin(base_url, 'clear_data'))
#resp = calulate_req(base_url, js_req_single)
#async_call = call_api(base_url, js_data)
#resp_full = asyncio.run(async_call)

#Async:
if async_allowed:
    NUM_THREADS=5
    st_time = datetime.now()
    with mp.Pool(processes=NUM_THREADS) as pool:
        res = pool.imap(call_async_join_map, [{'base_url':base_url, 'json_req': js_data, 'output_dir': output_dir, 
                                              'call_clear':False, 'sleep': 0}for i in range(MAX_REQUESTS_CNT)])
        list(tqdm(res, total=MAX_REQUESTS_CNT, desc='Update status'))
    print(f'Took {( datetime.now()- st_time).total_seconds()} for async calls vs {sync_time}')