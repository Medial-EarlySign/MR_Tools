import json, sys
from datetime import datetime
from flask import Flask
from flask import request, url_for
import pandas as pd


class Contributer_Records_Info:
    def __init__(self, max_time, time_unit, max_count):
        self.max_time = max_time
        self.time_unit = time_unit
        self.max_count = max_count


class Explainer_output:
    def __init__(self):
        self.contributor_name = None
        self.contributor_level = None
        self.contributor_level_max = None
        self.contributor_records = []
        self.contributor_records_info = None
        self.contributor_value = None
        self.contributor_percentage = None
        self.contributor_elements = []

    def parse(self, js_element):
        self.contributor_name = js_element["contributor_name"]
        self.contributor_level = float(js_element["contributor_level"])
        self.contributor_level_max = float(js_element["contributor_level_max"])
        self.contributor_records = js_element["contributor_records"]
        self.contributor_value = float(js_element["contributor_value"])
        self.contributor_percentage = float(js_element["contributor_percentage"])
        if "contributor_records_info" in js_element:
            info_records = js_element["contributor_records_info"]
            self.contributor_records_info = Contributer_Records_Info(
                info_records["contributor_max_time"],
                info_records["contributor_max_time_unit"],
                info_records["contributor_max_count"],
            )

    def __repr__(self):
        return f"\tcontributor_name: {self.contributor_name}, contributor_level: {self.contributor_level}\n"


def parse_explainer(js_element) -> Explainer_output:
    res = Explainer_output()
    res.parse(js_element)
    return res


class static_info:
    def __init__(self, sig: str, val: float):
        self.signal = sig
        self.value = val

    def __repr__(self):
        return f"{self.signal} = {self.value}"


class patient_info:
    def __init__(self):
        self.patient_id = None
        self.time = None
        self.prediction = None
        self.explainer_output = []
        self.static_info = None

    def parse(self, js_element):
        self.patient_id = int(js_element["patient_id"])
        self.time = int(js_element["time"])
        self.prediction = float(js_element["prediction"])
        head_key = list(
            filter(
                lambda x: type(js_element[x]) == dict
                and "explainer_output" in js_element[x],
                js_element.keys(),
            )
        )

        if len(head_key) > 0:
            head_key = head_key[0]
            # print(f'Found in {head_key}')
            bt_js = js_element[head_key]["explainer_output"]
            if "static_info" in js_element[head_key]:
                self.static_info = list(
                    map(
                        lambda x: static_info(x["signal"], x["value"]),
                        js_element[head_key]["static_info"],
                    )
                )
            self.explainer_output = list(map(parse_explainer, bt_js))

    def __repr__(self):
        if len(self.explainer_output) > 0:
            return (
                "{"
                + f"patient_id: {self.patient_id}, time: {self.time}, prediction: {self.prediction}, but_why_output:\n{self.explainer_output[:3]}"
                + "}"
            )
        else:
            return (
                "{"
                + f"patient_id: {self.patient_id}, time: {self.time}, prediction: {self.prediction}"
                + "}"
            )

    def to_dict(self, max_reasons=3):
        res = {"pid": self.patient_id, "time": self.time, "prediction": self.prediction}
        for i, exp in enumerate(self.explainer_output[:max_reasons]):
            res[f"contrib_{i}.name"] = exp.contributor_name
            res[f"contrib_{i}.level"] = exp.contributor_level
            res[f"contrib_{i}.value"] = exp.contributor_value
            res[f"contrib_{i}.percentage"] = exp.contributor_percentage

        return res


def parse_patient(js_element) -> patient_info:
    res = patient_info()
    res.parse(js_element)
    return res


app = Flask(__name__)


def run_server():
    app.run(host="0.0.0.0", debug=True, threaded=True, port=5000)
    url_for("static", filename="bootstrap.min.css")
    url_for("static", filename="bootstrap.min.js")
    url_for("static", filename="jquery.min.js")
    url_for("static", filename="plotly-latest.min.js")


@app.route("/")
def index():
    # Use data:
    data_f = list(filter(lambda x: len(x.explainer_output) > 0, data))
    data_f = sorted(data_f, key=lambda x: x.prediction, reverse=True)

    table_body = "\n".join(
        list(
            map(
                lambda x: f"<tr><td>{x.patient_id}</td><td>{x.time}</td><td>{x.prediction}</td>"
                + f'<td><a href="/open?patient={x.patient_id}&time={x.time}">Open</a></td><td><a href="http://node-04:8196/pid,{x.patient_id},{x.time},prediction_time,Smoking_Status&Smoking_Duration&P_White&P_Red&Platelets&P_Diabetes&P_Cholesterol&P_Liver&P_Renal&ICD9_Diagnosis&Race&Lung_Cancer_Location">Open viewer</a></td></tr>',
                data_f,
            )
        )
    )
    return """
<html>
    <head>
         <script src="/static/jquery.min.js"></script>
         <script src="/static/bootstrap.min.js"></script>
         <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
        <title>Patients list</title>
    </head>
    <body>
    <p><a href="/stats">Data Stats</a>
    </p>
        <p>
            <table class="table">
                <thead>
                    <th>Patient id</th><th>prediction time</th><th>prediction score</th><th>Link</th><th>Link Viewer</th>
                </thead>
                <tbody>
                    %s
                </tbody>
            </table>
        </p>
    </body>
</html>
    """ % (
        table_body
    )


def conv_to_html_rec(js):
    if len(js["timestamp"]) > 0:
        return f'time: {js["timestamp"]}, value: {js["value"]}'
    else:
        return f'value: {js["value"]}'


def conv_to_html(js_records, records_info, idx):
    if len(js_records) > 0:
        signal_name = js_records[0]["signal"]
        if len(js_records[0]["timestamp"]) == 0:
            return f"{signal_name}:<br>" + "<br>".join(
                list(map(conv_to_html_rec, js_records))
            )
        x_data = list(
            map(
                lambda x: "%s" % (datetime.strptime(str(x["timestamp"][0]), "%Y%m%d")),
                js_records,
            )
        )
        y_data = list(
            map(
                lambda x: x["value"][0] if len(x["value"]) > 0 else "<None>", js_records
            )
        )
        if len(x_data) == 1:
            return (
                f"<p><b>Single measurement of {y_data[0]} at time {x_data[0]}</b></p>"
            )
        else:
            return f"""<div id="myDiv_{signal_name}_{idx}"></div><script>
var trace1 = {{
  x: {x_data}, 
  y: {y_data},
  type: 'scatter',
  mode: 'markers+lines',
  name: 'data'
}};

var layout = {{
  title: 'Last {records_info.max_count} most recent {signal_name} in last {records_info.max_time} {records_info.time_unit}',
  autosize: true,
  width: 800,
  height: 300,
  yaxis : {{title: '{signal_name}' }},
  xaxis : {{ title: 'Time' }}
  
}};

Plotly.newPlot('myDiv_{signal_name}_{idx}', [trace1], layout);
</script>
"""
    else:
        if records_info is None:
            return "<p><b>No records</b></p>"
        else:
            return f"<p><b>No records in last {records_info.max_time} {records_info.time_unit}</b></p>"


@app.route("/open")
def open_patient():
    patient_id = request.args.get("patient", "")
    time = request.args.get("time", "")
    if len(patient_id) == 0 or len(time) == 0:
        raise NameError("please pass arguments")
    patient_id = int(patient_id)
    time = int(time)
    res_index = list(
        filter(
            lambda i: data[i].patient_id == patient_id and data[i].time == time,
            range(len(data)),
        )
    )
    if len(res_index) == 0:
        raise NameError("patient not found")
    assert len(res_index) == 1
    res_index = res_index[0]
    pid_data = data[res_index]
    next_pid = None
    prev_pid = None
    if res_index + 1 < len(data):
        next_pid = [data[res_index + 1].patient_id, data[res_index + 1].time]
    if res_index > 0:
        prev_pid = [data[res_index - 1].patient_id, data[res_index - 1].time]

    pid_html = '<a id="top"></a>'
    pid_html += f"<h1>Patient: {pid_data.patient_id}, Time: {pid_data.time}, Prediction: {pid_data.prediction}, Order:{res_index}</h1><br>"
    # Print static info:
    pid_html += "<h2>"
    first_print = True
    for info in pid_data.static_info:
        if not (first_print):
            pid_html += ", "
        pid_html += f'{info.signal}: {",".join(map(str,info.value)) if type(info.value) is list else info.value}'
        first_print = False
    pid_html += "</h2><br>"

    # pid_html+='<table class="table"><thead><th>Contributor Name</th><th>Contributor Importance</th><th>Contributor Data</th></thead></table>'
    graph = ""
    for idx, exp in enumerate(pid_data.explainer_output):
        direction = "=>"
        if idx > 0:
            graph += "<hr>\n"
        graph += f"Contributer #{idx+1}: Raw_Importance: {exp.contributor_value:.2f} ({exp.contributor_percentage:.2f}%)"
        bar_size = exp.contributor_level / exp.contributor_level_max * 100.0
        if exp.contributor_value < 0:
            direction = "<="
            graph += f'<div class="chart-wrap vertical"><div class="bar" style="--bar-value:{bar_size}%;background-color: #F16335;" data-name="{direction} {exp.contributor_name} ({exp.contributor_level})" title="{exp.contributor_name}"></div></div>'
        else:
            graph += f'<div class="chart-wrap vertical"><div class="bar" style="--bar-value:{bar_size}%;" data-name="{direction} {exp.contributor_name} ({exp.contributor_level} out of {exp.contributor_level_max})" title="{exp.contributor_name}"></div></div>'
        graph += f"\n{conv_to_html(exp.contributor_records, exp.contributor_records_info, idx)}"
    pid_html += graph

    res_page = """
<html>
    <head>
         <script src="/static/jquery.min.js"></script>
         <script src="/static/bootstrap.min.js"></script>
         <script src="/static/plotly-latest.min.js"></script>
         <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
         <style>
 .chart-wrap {
  margin-left: 50px;
  font-family: sans-serif;
  height: 100px;
  width: 300px;
}
.chart-wrap .title {
  font-weight: bold;
  font-size: 1.62em;
  padding: 0.5em 0 1.8em 0;
  text-align: center;
  white-space: nowrap;
}
.chart-wrap.vertical .grid {
  transform: translateY(-175px) translateX(175px) rotate(-90deg);
}
.chart-wrap.vertical .grid .bar::after {
  transform: translateY(-50%%) rotate(45deg);
  display: block;
}
.chart-wrap.vertical .grid::before,
.chart-wrap.vertical .grid::after {
  transform: translateX(-0.2em) rotate(90deg);
}
.chart-wrap .grid {
  position: relative;
  padding: 5px 0 5px 0;
  height: 100%%;
  width: 100%%;
  border-left: 2px solid #aaa;
  background: repeating-linear-gradient(90deg, transparent, transparent 19.5%%, rgba(170, 170, 170, 0.7) 20%%);
}
.chart-wrap .grid::before {
  font-size: 0.8em;
  font-weight: bold;
  content: '0%%';
  position: absolute;
  left: -0.5em;
  top: -1.5em;
}
.chart-wrap .grid::after {
  font-size: 0.8em;
  font-weight: bold;
  content: '100%%';
  position: absolute;
  right: -1.5em;
  top: -1.5em;
}
.chart-wrap .bar {
  width: var(--bar-value);
  height: 50px;
  margin: 30px 0;
  background-color: green;
  border-radius: 0 3px 3px 0;
}
.chart-wrap .bar:hover {
  opacity: 0.7;
}
.chart-wrap .bar::after {
  content: attr(data-name);
  margin-left: 100%%;
  padding: 10px;
  display: inline-block;
  white-space: nowrap;
}

hr {
  border: 0;
  clear:both;
  display:block;
  width: 96%%;               
  background-color:black;
  height: 1px;
}
         </style>
        <title>Patient %d at time %d</title>
    </head>
    <body>
        <p>
            %s
        </p>
        <a href="#top" style="position:fixed; width:60px;height:60px;bottom:340px;right:40px;background-color:#0C9;color:#FFF;border-radius:50px;box-shadow: 2px 2px 3px #999;text-align:center;">
<i><br>^ Up</i>
</a>
""" % (
        patient_id,
        time,
        pid_html,
    )
    if prev_pid:
        res_page += """
            <a href="/open?patient=%s&time=%s" style="position:fixed; width:60px;height:60px;bottom:240px;right:40px;background-color:#0C9;color:#FFF;border-radius:50px;box-shadow: 2px 2px 3px #999;text-align:center;">
    <i><br>&#8249; Back</i>
    </a> """ % (
            prev_pid[0],
            prev_pid[1],
        )
    if next_pid:
        res_page += """
<a href="/open?patient=%s&time=%s" style="position:fixed; width:60px;height:60px;bottom:140px;right:40px;background-color:#0C9;color:#FFF;border-radius:50px;box-shadow: 2px 2px 3px #999;text-align:center;">
<i><br>Next &gt;</i>
</a>
""" % (
            next_pid[0],
            next_pid[1],
        )
    res_page += """
    <a href="/" style="position:fixed; width:60px;height:60px;bottom:40px;right:40px;background-color:#0C9;color:#FFF;border-radius:50px;box-shadow: 2px 2px 3px #999;text-align:center;">
<i><br>Home</i>
</a>
    </body>
</html>
"""
    return res_page


def get_df_table(df: pd.DataFrame, title: str) -> str:
    s = f'<p><h1>{title}</h1><table class="table"><thead>'
    cols = list(df.columns)
    for col in cols:
        s += f"<th>{col}</th>"
    s += "</thead><tbody>"  # <tr><td>
    for i, d_row in df.iterrows():
        s += "<tr>"
        for col in cols:
            s += f"<td>{d_row[col]}</td>"
        s += "</tr>"
    s += "</tbody></table></p>"
    return s


@app.route("/stats")
def get_stats():
    df = pd.DataFrame(map(lambda x: x.to_dict(), data))
    dff = []
    for i in range(3):
        df_i = df[
            [
                f"contrib_{i}.name",
                f"contrib_{i}.level",
                f"contrib_{i}.value",
                f"contrib_{i}.percentage",
            ]
        ].copy()
        df_i.columns = ["name", "level", "value", "percentage"]
        df_i["prediction"] = df["prediction"]
        df_i["order"] = i
        dff.append(df_i)
    dff = pd.concat(dff, ignore_index=True)
    top_selection = 5

    percentage_stats = (
        (5 * (dff["percentage"] // 5))
        .value_counts()
        .reset_index()
        .sort_values("percentage")
    )
    percentage_stats["per"] = (100 * (
        percentage_stats["count"] / percentage_stats["count"].sum()
    )).round(1)

    level_stats = dff["level"].value_counts().reset_index().sort_values("level")
    level_stats["percentage"] = (level_stats["count"] / level_stats["count"].sum() * 100).round(1)
    level_stats_0 = (
        dff[dff["order"] == 0]["level"]
        .value_counts()
        .reset_index()
        .sort_values("level")
    )
    level_stats_0["percentage"] = (level_stats_0["count"] / level_stats_0["count"].sum() * 100).round(1)

    name_stats = dff["name"].value_counts().reset_index()
    name_stats["percentage"] = (name_stats["count"] / name_stats["count"].sum() * 100).round(1)
    name_stats_top = (
        dff.sort_values("prediction", ascending=False)
        .iloc[: len(dff) * top_selection // 100]["name"]
        .value_counts()
        .reset_index()
    )
    name_stats_top["percentage"] = (name_stats_top["count"] / name_stats_top["count"].sum() * 100).round(1)
    name_stats_ord_0 = dff[dff["order"] == 0]["name"].value_counts().reset_index()
    name_stats_ord_0["percentage"] = (name_stats_ord_0["count"] / name_stats_ord_0["count"].sum() * 100).round(1)

    val_distrib = (
        abs(dff["value"].round(1)).value_counts().reset_index().sort_values("value")
    )
    val_distrib['percentage'] = (val_distrib["count"] / val_distrib["count"].sum() * 100).round(1)
    val_q_0 = (
        dff[dff["order"] == 0]["value"].abs().quantile([0.5, 0.9, 0.99, 0.999]).reset_index()
    )
    val_q_0.columns = ["quantile", "value"]
    
    val_q_1 = (
        dff[dff["order"] == 1]["value"].abs().quantile([0.5, 0.9, 0.99, 0.999]).reset_index()
    )
    val_q_1.columns = ["quantile", "value"]

    # Print: percentage_stats, level_stats, level_stats_0, name_stats, name_stats_top,name_stats_ord_0 , val_distrib, val_q_0, val_q_1
    full_html = """
<html>
    <head>
         <script src="/static/jquery.min.js"></script>
         <script src="/static/bootstrap.min.js"></script>
         <link rel="stylesheet" href="/static/bootstrap.min.css"></link>
        <title>Data stats</title>
    </head>
    <body>"""

    full_html += get_df_table(percentage_stats, "Percentage Distribution")
    full_html += get_df_table(level_stats, "Level Distribution")
    full_html += get_df_table(
        level_stats_0, "Level Distribution of most important contributer"
    )
    full_html += get_df_table(name_stats, "Name Distribution")
    full_html += get_df_table(
        name_stats_top, f"Name Distribution of top {top_selection}%"
    )
    full_html += get_df_table(name_stats_ord_0 ,"Name Distribution of most important contributer",
    )
    full_html += get_df_table(val_distrib, "Value distribution")
    full_html += get_df_table(val_q_0, "Quantile top contributer value")
    full_html += get_df_table(val_q_1, "Quantile second top contributer value")

    full_html += "</body></html>"
    return full_html


if __name__ == "__main__":
    FILE_PATH = (
        "/server/Products/LGI-ColonFlag-3.0/scripts_butwhy/examples.NEW/resp.json"
    )
    if len(sys.argv) > 1:
        FILE_PATH = sys.argv[1]
    fr = open(FILE_PATH, "r")
    txt = fr.read()
    fr.close()
    js = json.loads(txt)
    js = js["responses"]
    data = list(map(parse_patient, js))
    data = list(filter(lambda x: len(x.explainer_output) > 0, data))
    data = sorted(data, key=lambda x: x.prediction, reverse=True)
    run_server()
