#!/usr/bin/env python
import os,sys, argparse, json
from AlgoMarker import AlgoMarker

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def read_text_file(p):
    fr=open(p, 'r')
    res=fr.read()
    fr.close()
    return res

#Default arguments
#algomarker_dir = '/nas1/Products/LungCancer/QA_Versions/LungFlag3.NEW.2023-07-01.With_ButWhy'
#js_data_path='/nas1/Products/LungCancer/QA_Versions/LungFlag3.NEW.2023-07-01.With_ButWhy/examples/data.single.backup.json'
#req_js_path='/nas1/Products/LungCancer/QA_Versions/LungFlag3.NEW.2023-07-01.With_ButWhy/examples/req.single.json'
#output_path='/tmp/results.txt'

parser = argparse.ArgumentParser(description = "Run AlgoMarker Test")
parser.add_argument("--amconfig",help="algomarker config", required=True)
parser.add_argument("--amlib",help="algomarker lib", default='')
parser.add_argument("--add_data_json_path",help="add_data_json_path", default='')
parser.add_argument("--request_json_path",help="request_json_path",default='')
parser.add_argument("--run_discovery",help="if true will run discovery", type=str2bool, default=False)
parser.add_argument("--output",help="output path", required=True)
args = parser.parse_args() 

#Excute
libpath=None
if args.amlib!='':
    libpath=args.amlib

with open(args.output, 'w') as output_f:
    with AlgoMarker(args.amconfig, libpath) as algomarker:
        if args.run_discovery:
            print('Call Discovery')
            discovery_output = algomarker.discovery()
            output_f.write('###########DISCOVERY OUTPUT#############\n')
            output_f.write(json.dumps(discovery_output, indent=True)+'\n')

        #AddData:
        if len(args.add_data_json_path):
            js_data = read_text_file(args.add_data_json_path)
            print('Call ClearData')
            algomarker.clear_data()
            print('Call AddData')
            msgs=algomarker.add_data(js_data)
            if msgs is not None:
                output_f.write('###########AddData Messages#############\n')
                output_f.write(msgs+'\n')
        #Calculate:
        if len(args.request_json_path):
            req_js = read_text_file(args.request_json_path)
            print('Call Calculate')
            resp=algomarker.calculate(req_js)
            output_f.write('###########Calculate OUTPUT#############\n')
            output_f.write(json.dumps(resp, indent=True)+'\n')

print(f'output can be found in {args.output}')