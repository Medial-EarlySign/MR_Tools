#!/bin/bash
uvicorn server_similarity:app --reload --host 0.0.0.0 --port 8001
