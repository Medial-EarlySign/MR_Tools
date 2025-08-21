from typing import Any, Dict, List

import pandas as pd
from sentence_transformers import SentenceTransformer, util
import urllib
import os

# from fetch_conf import DB_Access


def fetch_title(txt: str) -> str:
    lines = txt.splitlines()
    state = 0
    header = None
    for ii, ln in enumerate(lines):
        if ln.strip() == "" and state == 0:
            continue
        else:
            state = 1
        if state > 0:
            if not (ln.startswith("#")):
                break
            header = ln[2:]
            break
    return header


def convert_df(data: Dict[str, str]) -> pd.DataFrame:
    df = pd.DataFrame({"PATH": data.keys(), "CONTENT": data.values()})
    df["TITLE"] = df["CONTENT"].astype(str).apply(fetch_title)
    df = df[~df["PATH"].str.startswith("Archive")].reset_index(drop=True)
    df["clear_text"] = df["CONTENT"]
    df["CONTENTID"] = df.index
    return df


def fetch_data(wiki_path: str, full_pt: str, args: Dict[str, Any]):
    relative_name = full_pt[len(wiki_path) + 1 :]
    if "data" not in args:
        args["data"] = {}
    with open(full_pt, "r") as fr:
        txt = fr.read()
    args["data"][relative_name] = txt


def analyze_folder_wiki(wiki_path: str, full_pt: str, args: Dict[str, Any]):
    all_files = os.listdir(full_pt)
    for f in all_files:
        ff = os.path.join(full_pt, f)
        if os.path.isfile(ff) and ff.endswith(".md"):
            fetch_data(wiki_path, ff, args)
        if os.path.isdir(ff):
            analyze_folder_wiki(wiki_path, ff, args)


def fetch_conf_data():
    base_script_folder = os.path.dirname(os.path.abspath(__file__))
    wiki_path = os.path.join(
        os.path.dirname(os.path.dirname(base_script_folder)), "Wiki"
    )
    skip_list_root = [
        "attachments",
        ".git",
        "gitlab",
        ".gitlab-ci.yml",
        "images",
        "styles",
        "index.md",
    ]
    args = {}
    for dirn in os.listdir(wiki_path):
        if dirn in skip_list_root:
            continue
        analyze_folder_wiki(wiki_path, os.path.join(wiki_path, dirn), args)
    # args["data"] contains the dict of page_name to content
    pages_data = args["data"]
    res = convert_df(pages_data)

    IGNORE_TITLES = [
        "Influenza Complications",
        "THIN Signals",
        "Signals map",
        "Signals",
        "Signal",
        "NWP",
        "Readmission",
        "Prostate",
        "THIN - 1601",
        "Archive",
    ]
    res_size = len(res)
    res = res[~res["TITLE"].isin(IGNORE_TITLES)].reset_index(drop=True)

    return res


def search(
    model: SentenceTransformer,
    docs: List[str],
    titles: List[str],
    ids: List[int],
    paths: List[str],
    doc_emb: List[List[float]],
    query: str,
):
    # Encode query
    query_emb = model.encode(query)
    # Compute dot score between query and all document embeddings
    scores = util.dot_score(query_emb, doc_emb)[0].cpu().tolist()
    # Combine docs & scores
    doc_score_pairs = list(zip(docs, scores, titles, ids, paths))
    # Sort by decreasing score
    doc_score_pairs = sorted(doc_score_pairs, key=lambda x: x[1], reverse=True)
    return doc_score_pairs


def print_top(doc_score_pairs, top=5):
    # Output passages & scores
    for doc, score, title in doc_score_pairs[:top]:
        print(f"{title} - score: {score}\n{doc[:100]}\n###################")


if __name__ == "__main__":
    query = "How many people live in London?"
    # docs = ["Around 9 Million people live in London", "London is known for its financial district"]
    res = fetch_conf_data()
    print(f"There are {len(res)} confluence pages")
    docs = list(res["CONTENT"].values)
    titles = list(res["TITLE"].values)

    # Load the model
    model = SentenceTransformer(
        "/nas1/Work/python-resources/common/models/msmarco-MiniLM-L12-cos-v5",
        local_files_only=True,
    )

    # Encode documents
    doc_emb = model.encode(docs)

    doc_score_pairs = search(model, docs, titles, doc_emb, query)

    print_top(doc_score_pairs, 5)
