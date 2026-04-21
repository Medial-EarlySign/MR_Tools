# python 3.10

from fastapi import FastAPI, Request, Response
from llm_api4 import LLM_Model, simple_predict
from contextlib import asynccontextmanager
import json
import os
import glob
import numpy as np
from sentence_transformers import SentenceTransformer, util


def fetch_data() -> list[str]:
    root_base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    wiki_home = os.path.join(root_base, "MR_WIKI")
    path_pattern = f"{wiki_home}/**/*.md"
    files = glob.glob(path_pattern, recursive=True)
    res = []
    for file in files:
        with open(file, "r") as f:
            res.append(f.read())
    return res


def search(
    model: SentenceTransformer,
    corpus_embeddings,
    query: str,
    docs: list[str],
    k: int = 10,
) -> list[str]:
    query_embedding = model.encode(query, convert_to_tensor=True)
    hits = util.cos_sim(query_embedding, corpus_embeddings)[0]
    top_results = np.argpartition(-hits.cpu(), range(k))[:k]
    res = [docs[idx] for idx in top_results]
    return res


@asynccontextmanager
async def startup_event(app: FastAPI):
    print("Starting up...", flush=True)
    SYSTEM_PROMPT = "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information."
    app.state.model = LLM_Model(sys_prompt=SYSTEM_PROMPT)
    print("Model loaded!")
    app.state.docs = fetch_data()
    app.state.search_model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )
    app.state.embd = app.state.search_model.encode(
        app.state.docs, convert_to_tensor=True
    )
    yield


app = FastAPI(lifespan=startup_event)


def get_result(js_data_str, response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    try:
        js_data = json.loads(js_data_str)
    except:
        print(js_data_str)
        return {"error": "please pass valid json"}
    if "query" not in js_data:
        print(js_data)
        return {"error": "please pass query element in request"}
    temperature = 0.2
    if "temperature" in js_data:
        temperature = float(js_data["temperature"])
    max_new_tokens = 512
    if "max_new_tokens" in js_data:
        max_new_tokens = int(js_data["max_new_tokens"])
    _k = 3
    if "k" in js_data:
        _k = int(js_data["k"])
    max_length = 128_000
    if "max_length" in js_data:
        max_length = int(js_data["max_length"])
    print(js_data)
    prompt = js_data["query"]

    # sys.setrecursionlimit(100000)
    docs = search(app.state.search_model, app.state.embd, prompt, app.state.docs, _k)
    backgroud_info = ""
    for doc in docs[:_k]:
        backgroud_info += doc + "\n"
    if len(backgroud_info) > max_length:
        print(
            f"Query is too long - truncating from {len(backgroud_info)} to {max_length} "
        )
        backgroud_info = backgroud_info[:max_length]

    messages = [
        {
            "role": "system",
            "content": app.state.model.sys_prompt
            + "\n\nUse This background information:\n"
            + backgroud_info,
        }
    ]
    answer, messages = simple_predict(app.state.model, prompt, messages)
    res = {"response": answer}
    # print (res)
    return res


@app.post("/")
async def index_root(request: Request, response: Response):
    js_body = await request.body()
    js_body = js_body.decode("utf-8")
    return get_result(js_body, response)
