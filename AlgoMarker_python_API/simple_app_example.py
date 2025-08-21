#!/usr/bin/env python
from AlgoMarker_minimal import AlgoMarker
import json

ALGOMARKER_PATH='/nas1/Products/LungCancer/QA_Versions/LungFlag3.NEW.2023-07-01.With_ButWhy/lungflag.amconfig'
REQUEST_DATA='/nas1/Products/LungCancer/QA_Versions/LungFlag3.NEW.2023-07-01.With_ButWhy/examples/req.full.json'

def read_text_file(p):
    fr=open(p, 'r')
    res=fr.read()
    fr.close()
    return res

with AlgoMarker(ALGOMARKER_PATH) as algomarker:
    discovery_json=algomarker.discovery()
    print('$> discovery - first 100 characters:')
    print(json.dumps(discovery_json, indent=True)[:100])
    print('$> calculate - first 200 characters:')
    resp=algomarker.calculate(read_text_file(REQUEST_DATA))
    print(json.dumps(resp, indent=True)[:200])
    
print('All Done')