#!/usr/bin/env python
import requests
import os
import json


def test_calculate(req_json_path: str) -> dict:
    with open(req_json_path, "r") as f:
        req_json = f.read()
    URL = "http://localhost:8001/calculate"
    res = requests.post(URL, data=req_json).json()
    return res


if __name__ == "__main__":
    base_path = os.path.dirname(os.path.abspath(__file__))
    requests_dir = os.path.join(base_path, "Resources", "Requests")
    responses_dir = os.path.join(base_path, "Resources", "Responses")
    responses_dir_failed = os.path.join(base_path, "Resources", "Responses.errors")
    os.makedirs(responses_dir_failed, exist_ok=True)
    # Clear dir
    for req in os.listdir(responses_dir_failed):
        os.remove(os.path.join(responses_dir_failed, req))
    
    CREATE_TEST = False

    collected_errors = []
    for req in os.listdir(requests_dir):
        full_req_path = os.path.join(requests_dir, req)
        # Corresponding resp:
        full_resp_path = os.path.join(responses_dir, req)
        resp_json = None
        if os.path.exists(full_resp_path):
            with open(full_resp_path, "r") as f:
                resp_json = f.read()
        else:
            if not (CREATE_TEST):
                raise Exception(
                    f"No expected results exists for test. Please populate {responses_dir} or run with CREATE_TEST=True if you trust those results as expected to fix the test results"
                )

        res = test_calculate(full_req_path)
        if CREATE_TEST:
            with open(full_resp_path, "w") as f:
                f.write(json.dumps(res, indent=True))
        else:
            if resp_json is not None and res != json.loads(resp_json):
                collected_errors.append(f"## Error in Requests {req}, please compare folders")
                # Write this in now folder for compare:
                with open(os.path.join(responses_dir_failed, req), "w") as f:
                    f.write(json.dumps(res, indent=True))

    for error in collected_errors:
        print(error)
    if len(collected_errors) ==0:
        print("All Tests are OK")