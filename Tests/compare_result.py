import numpy as np
import pandas as pd
import med
from sklearn.metrics import roc_auc_score
import subprocess


def run_bt_app(df: pd.DataFrame) -> float:
    df2 = df.copy()
    df2["EVENT_FIELDS"] = "SAMPLE"
    df2["id"] = df2.index + 1
    df2["time"] = 20251201
    df2["outcomeTime"] = 20251201
    df2["split"] = 1
    df2 = df2.rename(columns={"label": "outcome", "score": "pred_0"})
    df2 = df2[
        ["EVENT_FIELDS", "id", "time", "outcome", "outcomeTime", "split", "pred_0"]
    ]
    df2.to_csv("/tmp/test.preds", sep="\t", index=False)
    # Run Bootstrap app
    subprocess.run(
        ["bootstrap_app --input /tmp/test.preds --output /tmp/bt"],
        shell=True,
        check=True,
    )
    df_res = pd.read_csv("/tmp/bt.pivot_txt", sep="\t")
    auc_obs = float(df_res[df_res["Measurement"] == "AUC_Obs"].iloc[0]["Value"])
    return auc_obs


def med_python(df: pd.DataFrame) -> float:
    bt = med.Bootstrap()
    res = bt.bootstrap(df["score"], df["label"]).to_df()
    res[res["Measurement"] == "AUC_Obs"]
    mes_value = res[res["Measurement"] == "AUC_Obs"].iloc[0]["Value"]
    return mes_value


def run_exp(N: int = 1000):
    df = pd.DataFrame(
        {
            "score": np.random.uniform(size=[N]),
            "label": np.random.randint(low=0, high=2, size=[N]),
        }
    )
    auc_app = run_bt_app(df)
    mes_value = med_python(df)
    scikit_val = roc_auc_score(df["label"], df["score"])
    return auc_app, mes_value, scikit_val


def repeat_exp(N: int = 1000, bootstrap: int = 10):
    all_res = []
    for i in range(bootstrap):
        auc_app, mes_value, scikit_val = run_exp(10000)
        all_res.append([auc_app, mes_value, scikit_val])
    res = pd.DataFrame(all_res)
    res.columns = ["bootstrap_app", "med_python", "scikit_learn"]
    res["diff_python"] = abs(res["med_python"] - res["scikit_learn"])
    res["diff_mes"] = abs(res["med_python"] - res["bootstrap_app"])
    return res


df = repeat_exp(N=1000, bootstrap=10)
print(df)
