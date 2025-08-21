from pharmpy.atc import ATCEngine
import json
ae = ATCEngine(root_url="https://rxnav.nlm.nih.gov/REST")
print(ae.root_url)
res = ae.get_atc("50090347201")

print(json.dumps(res, indent=2))