#!/usr/bin/env python
from AlgoMarker import AlgoMarker
from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
import os

description = """
AlgoMarker API helps you do awesome stuff. 🚀

## Methods

You will be able to:

* **discovery** .
* **calculate**.
"""
tags_metadata = [
    {
        "name": "methods",
        "description": "**discovery** to see AlgoMarker details and **calculate** to run calculation",
    }
]

ALGOMARKER_PATH = os.getenv("AM_CONFIG", "")
if ALGOMARKER_PATH == "":
    raise Exception("Environment variable AM_CONFIG is not set. Please set it to the path of AlgoMarker configuration file.")
AM_LIB_PATH = os.getenv("AM_LIB", "")
if AM_LIB_PATH == "":
    AM_LIB_PATH = os.path.join(os.path.dirname(ALGOMARKER_PATH), "lib", "libdyn_AlgoMarker.so")




@asynccontextmanager
async def startup_event(app: FastAPI):
    print("Starting up AlgoMarker API...", flush=True)
    app.algomarker = AlgoMarker(ALGOMARKER_PATH, AM_LIB_PATH)
    yield
    # Shutdown code
    app.algomarker.dispose()

app = FastAPI(
    description=description, openapi_tags=tags_metadata, docs_url=None, redoc_url=None,
    lifespan=startup_event
)
app.algomarker = None
app.mount("/swagger", StaticFiles(directory="swagger"), name="swagger")


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/swagger/swagger-ui-bundle.js",
        swagger_css_url="/swagger/swagger-ui.css",
    )


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/swagger/redoc.standalone.js",
    )


@app.get("/")
async def index():
    return {
        "Help": {
            "/discovery": {"input": "", "output": "returns discovery json"},
            "/calculate": {
                "input": "json request with patient data",
                "output": "returns responde json with results",
            },
        }
    }


@app.get("/discovery", tags=["methods"])
async def discovery():
    return app.algomarker.discovery()


@app.post("/calculate", tags=["methods"])
async def calculate(request: Request):
    js_data_str = await request.body()
    js_data_str = js_data_str.decode("utf-8")
    # print(f"Recieved {js_data_str}", flush=True)
    resp = app.algomarker.calculate(js_data_str)
    app.algomarker.clear_data()
    return resp
