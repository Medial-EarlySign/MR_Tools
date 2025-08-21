import pandas as pd
import plotly.graph_objs as go
from typing import Dict
import re


def get_plotly_js():
    fig = go.Figure()
    html = fig.to_html(include_plotlyjs=True)
    script_element = re.compile(r"<script [^>]*>(/\*.*?)< */script>", re.DOTALL)
    res = script_element.findall(html)
    if len(res) != 1:
        print("Error in fetching js")
        return ""
    js = res[0]
    return js


def plot_graph(
    obj: Dict[str, pd.DataFrame] | pd.DataFrame,
    save_path: str,
    title: str = "Test",
    mode: str = "markers+lines",
    javascript_path: str = r"W:\Graph_Infra\plotly-latest.min.js",
) -> None:
    """
    Method to plot graph using plotly

    :param obj: dictioanry from the name of the series into Dataframe with the data. The first column is x, 2nd is y axis data
    :param save_path: path to store the html file
    :param title: The graph title
    :param mode: controls the graph type: "bar" or options for scatter
    :param javascript_path: controls the path to javascript
    """
    fig = go.Figure()
    amode = mode
    col_x_name = None
    col_y_name = None
    if type(obj) == dict:
        for ser_name, df in obj.items():
            x_col = df.columns[0]
            y_col = df.columns[1]
            if col_x_name is None:
                col_x_name = x_col
                col_y_name = y_col
            if mode != "bar":
                fig.add_trace(
                    go.Scatter(x=df[x_col], y=df[y_col], mode=amode, name=ser_name)
                )
            else:
                fig.add_trace(go.Bar(x=df[x_col], y=df[y_col], name=ser_name))
    elif (isinstance(obj, pd.DataFrame)):  # dataframe
        df: pd.DataFrame = obj
        col_x_name = df.columns[0]
        col_y_name = df.columns[1]
        if mode != "bar":
            fig.add_trace(
                go.Scatter(x=df[col_x_name], y=df[col_y_name], mode=amode, name="Test")
            )
        else:
            fig.add_trace(go.Bar(x=df[col_x_name], y=df[col_y_name], name="Test"))
    else:
        raise ValueError("obj must be a dictionary or a DataFrame")
    tmp = fig.update_xaxes(showgrid=False, zeroline=False, title=col_x_name)
    tmp = fig.update_yaxes(showgrid=False, zeroline=False, title=col_y_name)
    fig.layout.plot_bgcolor = "white"
    fig.layout.title = title
    fig.write_html(save_path, include_plotlyjs=javascript_path)
    return fig
