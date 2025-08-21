import os
import socket
import re
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import json, sys

# from langchain_community.vectorstores import Chroma
# from langchain_community.embeddings import LlamaCppEmbeddings
from sentence_transformers import SentenceTransformer
import torch
from similarity import fetch_conf_data, search
import html2text

# from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import TextIteratorStreamer, AutoTokenizer
from ctransformers import AutoModelForCausalLM, AutoConfig


def fix_txt(txt: str, title: str | None = None) -> str:
    data_regex = re.compile(r"(<!\[CDATA\[)(.*?)(]]>)", re.DOTALL)
    modified_text = txt
    has_change = True
    while has_change:
        before = modified_text
        modified_text = re.sub(data_regex, lambda m: m.group(2), modified_text)
        has_change = len(before) != len(modified_text)
    modified_text = (
        modified_text.replace("<ac:structured-macro", "<pre")
        .replace(
            '<ac:parameter ac:name="language">py</ac:parameter>',
            '<code class="language-python">',
        )
        .replace(
            '<ac:parameter ac:name="language">bash</ac:parameter>',
            '<code class="language-bash">',
        )
        .replace("</ac:structured-macro>", "</code></pre>")
        .replace("</ac:parameter>", "</ac:parameter>\n")
        .replace("<ac:plain-text-body>", "")
        .replace("</ac:plain-text-body>", "")
    )

    modified_text = re.sub(
        '<ac:parameter ac:name="collapse">[^<]*</ac:parameter>', "", modified_text
    )
    modified_text = re.sub(
        '<ac:parameter ac:name="theme">[^<]*</ac:parameter>', "", modified_text
    )

    modified_text = (
        """
    <html>
    <head>

    <script src="/resources/marked.min.js"></script>
    
    """
        + (f"<title>{title}</title><h1>{title}</h1>" if title else "")
        + """</head>
    <body><div id="content"></div>
   <script>
   var txt = '""" + '\\\n\\n'.join(modified_text.replace("'", "\\'").splitlines()) + """';
    document.getElementById('content').innerHTML =
      marked.parse(txt);
  </script>
    
    </body>

    </html>
    """
    )
    return modified_text


@asynccontextmanager
async def startup_event(app: FastAPI):
    # llama_model_path = '/nas1/Work/python-resources/common/llama/7B/llama-2-7b-chat/ggml-model-q4_0.gguf'
    # llama_model_path = '/nas1/Work/python-resources/common/llama/7B/llama-2-7b-chat/ggml-model-f32.gguf'
    # embeddings = LlamaCppEmbeddings(model_path=llama_model_path)
    # app.vectordb = Chroma(persist_directory=app.db_path, embedding_function=embeddings)
    res = fetch_conf_data()
    # h = html2text.HTML2Text()
    # res['clear_text'] = res['BODY'].apply(lambda txt: h.handle(fix_txt(txt)))
    print(f"There are {len(res)} confluence pages")
    app.full_data = res
    app.docs = list(res["clear_text"].values)
    app.ids = list(res["CONTENTID"].values)
    app.titles = list(res["TITLE"].values)
    app.paths = list(res["PATH"].values)
    app.model = SentenceTransformer(
        "/nas1/Work/LLM/all-MiniLM-L6-v2",
        local_files_only=True,
        tokenizer_kwargs={"clean_up_tokenization_spaces": True},
    )
    config = AutoConfig.from_pretrained("/nas1/Work/LLM/mistral_chat")
    # Explicitly set the max_seq_len
    config.max_seq_len = 8192
    config.max_answer_len = 8192
    config.config.max_new_tokens = 8192
    config.config.context_length = 4096
    app.llm_model = AutoModelForCausalLM.from_pretrained(
        "/nas1/Work/LLM/mistral_chat",
        model_file="mistral-7b-claude-chat.Q5_K_S.gguf",
        model_type="mistral",
        config=config,
        gpu_layers=0,
    )
    app.tokenizer = AutoTokenizer.from_pretrained(
        "/nas1/Work/LLM/mistral_chat", hf=True
    )
    # app.llm_device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    app.max_query_len = 1000  # Default
    app.max_answer_len = 1024  # Default
    app.doc_emb = app.model.encode(app.docs)
    app.SYS_PROMPT = "You are a helpful, respectful and honest assistant. Always answer as helpfully as possible, while being safe. If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information. Please answer using markup language"
    print("DB loaded!")
    yield
    print("END")


app = FastAPI(lifespan=startup_event)
app.mount("/resources", StaticFiles(directory="resources"), name="resources")


def get_result(js_data_str, response: Response):
    try:
        js_data = json.loads(js_data_str)
    except:
        print(js_data_str)
        return {"error": "please pass valid json"}
    if "query" not in js_data:
        print(js_data)
        return {"error": "please pass query element in request"}
    _k = 3
    if "k" in js_data:
        _k = int(js_data["k"])
    query = js_data["query"]

    # titles = list(map(lambda x:x.metadata['source'], docs))
    docs = search(
        app.model, app.docs, app.titles, app.ids, app.paths, app.doc_emb, query
    )
    full_res = []
    for doc, score, title, id, doc_path in docs[:_k]:
        if doc_path.endswith("index.md"):
            doc_path = doc_path[: -len("index.md") - 1]
        if doc_path.endswith('.md'):
            doc_path = doc_path[:-3]
        full_res.append(
            {
                "title": title,
                "score": score,
                "text": doc,
                "id": str(id),
                "path": doc_path,
            }
        )

    res = {"response": full_res}
    # print (res)
    return res


def summerize_res(js_data_str: str):
    try:
        js_data = json.loads(js_data_str)
    except:
        print(js_data_str)
        return {"error": "please pass valid json"}
    if "query" not in js_data:
        print(js_data)
        return {"error": "please pass query element in request"}
    _k = 3
    if "k" in js_data:
        _k = int(js_data["k"])
    query = js_data["query"]
    max_length = app.max_query_len
    max_answer_len = app.max_answer_len
    if "max_length" in js_data:
        max_length = int(js_data["max_length"])
    if "max_len_answer" in js_data:
        max_answer_len = int(js_data["max_len_answer"])

    # titles = list(map(lambda x:x.metadata['source'], docs))
    docs = search(
        app.model, app.docs, app.titles, app.ids, app.paths, app.doc_emb, query
    )

    backgroud_info = ""
    for doc, score, title, ids, paths in docs[:_k]:
        backgroud_info += doc + "\n"
    if len(backgroud_info) > max_length:
        print(
            f"Query is too long - truncating from {len(backgroud_info)} to {max_length} "
        )
        backgroud_info = backgroud_info[:max_length]

    prefix_query = "Please use this background information to answer a question:\n"
    # and answer the question in the end using Markup language.
    # print(full_query)
    # full_query = prefix_query + backgroud_info + "\n\nAnswer this question using Markup language: \n" + query
    # <human>:
    # <bot>:
    # USER: {prompt} ASSISTANT:
    full_query = ""
    full_query_conv = [
        {"role": "user", "content": app.SYS_PROMPT},
        {"role": "user", "content": "Background information: " + backgroud_info},
        {"role": "user", "content": query},
    ]
    for token in full_query_conv:
        tag = "USER: "
        if token["role"] == "system":
            tag = "ASSISTANT: "
        full_query += tag + token["content"] + "\n\n"

    with torch.no_grad():
        gen_res = app.llm_model(
            full_query, max_new_tokens=max_answer_len, stream=True, stop=["USER: "]
        )
    with open("/tmp/debug_query.txt", "w") as fw:
        fw.write(app.SYS_PROMPT + "\n\n" + backgroud_info + "\n\n" + query)

    for token in gen_res:
        print(token, end="", flush=True)
        yield token


@app.get("/page/{page_id}", response_class=HTMLResponse)
async def see_page(page_id: str):
    res = app.full_data[app.full_data["CONTENTID"] == int(page_id)]
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    html_txt = fix_txt(res.iloc[0].CONTENT, res.iloc[0].TITLE)
    return html_txt


@app.get("/page_text/{page_id}", response_class=PlainTextResponse)
async def see_page(page_id: str):
    res = app.full_data[app.full_data["CONTENTID"] == int(page_id)]
    if len(res) == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    html_txt = res.iloc[0]["clear_text"]
    return html_txt


@app.post("/query")
async def query(request: Request, response: Response):
    js_body = await request.body()
    js_body = js_body.decode("utf-8")
    response.headers["Access-Control-Allow-Origin"] = "*"
    return get_result(js_body, response)


@app.post("/summerize")
async def summerize(request: Request, response: Response):
    js_body = await request.body()
    js_body = js_body.decode("utf-8")
    response.headers["Access-Control-Allow-Origin"] = "*"
    res = summerize_res(js_body)
    return StreamingResponse(
        res, media_type="text/plain", headers={"Access-Control-Allow-Origin": "*"}
    )


@app.get("/", response_class=HTMLResponse)
async def get_index_html(request: Request, response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    html_template_path = os.path.join(
        os.path.dirname(__file__), "index_similarity.html"
    )
    with open(html_template_path, "r") as file_reader:
        content = file_reader.read()

    hostname = socket.gethostname()
    # var url='http://localhost:8001';
    content = content.replace("http://localhost:8001", f"http://{hostname}:8001")
    return content
