#!/bin/bash
source /nas1/Work/python-env/python310/bin/activate
uvicorn server:app --reload --host 0.0.0.0 --port 8001
