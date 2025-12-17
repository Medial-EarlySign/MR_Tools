import json
from datetime import datetime
from collections import defaultdict

# --- 1. SETUP: Load your Mapping File ---
def load_mapping():
    mapping = {}
    # For this demo, we'll manually simulate the loaded dict from loinc codes to medpython names - your model input names
    # Please refer to ../RepoLoadUtils/Roche_IBM/configs/map.tsv map example of loinc codes
    mapping = {
        "718-7": "Hemoglobin",
        "4544-3": "Hematocrit",
        "30522-7": "CRP"
    }
    return mapping

def to_medial_date(fhir_date_str):
    """Converts ISO '2023-12-25' to Integer 20231225"""
    if not fhir_date_str: return None
    try:
        # Take first 10 chars to handle both '2023-01-01' and '2023-01-01T10:00:00'
        dt = datetime.strptime(fhir_date_str[:10], "%Y-%m-%d")
        return int(dt.strftime("%Y%m%d"))
    except ValueError:
        return None

def fhir_to_medpython(fhir_bundle: dict) -> str:
    code_map = load_mapping()
    
    # Dictionary to hold signals per patient
    # Structure: patients[pid][signal_name] = [ {val, date}, {val, date} ]
    patient_signals = defaultdict(lambda: defaultdict(list))
    
    entries = fhir_bundle.get("entry", [])
    
    for entry in entries:
        resource = entry.get("resource", {})
        
        if resource.get("resourceType") == "Observation":
            # A. Extract Patient ID
            subject = resource.get("subject", {}).get("reference", "")
            pid = subject.split("/")[-1] if "/" in subject else subject
            if not pid: continue

            # B. Find the Medial Name using your Map
            codings = resource.get("code", {}).get("coding", [])
            medial_name = None
            
            for coding in codings:
                system_code = coding.get("code")
                if system_code in code_map:
                    medial_name = code_map[system_code]
                    break
            
            # C. Extract Value and Date
            if medial_name:
                val = resource.get("valueQuantity", {}).get("value")
                unit = resource.get("valueQuantity", {}).get("unit")
                date_int = to_medial_date(resource.get("effectiveDateTime"))

                if val is not None and date_int:
                    # D. Add to intermediate list
                    patient_signals[pid][medial_name].append({
                        "value": [str(val)],     # Medial format expects lists
                        "timestamp": [date_int], # Medial format expects lists
                        "unit": unit
                    })

    # --- 4. CONSTRUCT FINAL JSON ---
    request_list = []
    
    for pid, signals_dict in patient_signals.items():
        medial_signals = []
        
        for sig_name, data_points in signals_dict.items():
            # Create the signal object
            sig_obj = {
                "code": sig_name,
                "data": data_points
            }
            # Optional: Add unit from the first data point if available
            if data_points and data_points[0].get("unit"):
                sig_obj["unit"] = data_points[0]["unit"]
                
            medial_signals.append(sig_obj)

        request_list.append({
            "patient_id": pid,
            "time": datetime.now().strftime("%Y%m%d"), 
            "data": { "signals": medial_signals }
        })

    final_output = {
        "type": "request",
        "request_id": "req_generated_001",
        "export": {"prediction": "pred_0"},
        "load": 1,
        "requests": request_list
    }
    
    return json.dumps(final_output, indent=2)

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    pass
    # fhir_data = json.load(open('my_fhir.json'))
    # print(fhir_to_medpython(fhir_data))