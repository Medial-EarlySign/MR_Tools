import requests
import itertools
from lxml import html
import json
import pandas as pd
import os


def get_theme_filter_list(jsn, theme_filre):
    theme_filters = jsn['ThemeConfiguration']['ThemeFilters']
    curr_filer = [x for x in theme_filters if x['ThemeFilterId'] == theme_filre]
    filter_dicts = curr_filer[0]['ThemeFilterOptions']
    if theme_filre == 7 or theme_filre == 9:  # "Spatial Smoothing", Yers
        filter_list = [2]  # "Not Smoothed"
    else:
        filter_list = [x['FilterOptionId'] for x in filter_dicts]
    return filter_list


def create_params(jsn):
    # print(jsn)
    theme_classes = jsn['ThemeConfiguration']['ThemeClasses']
    for tc in theme_classes:
        print(tc['ThemeClassName'])
        theme_subclasses = tc['ThemeSubClasses']
        for tsc in theme_subclasses:
            print('\t' + tsc['ThemeSubClassName'])
            themes = tsc['Themes']
            th_dict = {"GeographyType": "county", "ParentGeographyFilter": ""}
            for th in themes:
                print('\t\t' + th['Name'])
                th_dict['ThemeId'] = th['ThemeId']
                theme_filter_ids = []
                theme_filter_lists = []
                for tfid in th['ThemeFilterIds']:
                    # print('\t\t\t' + str(tfid))
                    theme_filter_ids.append(tfid)
                    theme_filter_lists.append(get_theme_filter_list(jsn, tfid))
                options = list(itertools.product(*theme_filter_lists))
                for op in options:
                    theme_filter_dicts = []
                    for i in range(len(op)):
                        theme_filter_dicts.append({"FilterId": theme_filter_ids[i], "FilterOptionId": str(op[i])})
                    th_dict['ThemeFilterOptions'] = theme_filter_dicts
                    yield th_dict


def get_and_parse(url, param):
    GET_URL = url + '?' + json.dumps(param)
    #r = requests.get(url=GET_URL)  # , params=PARAMS)
    filename = 'response.html'
    with open(filename, 'r', encoding="utf-8") as f:
        r = f.read()
    #print(r.url)

    #tree = html.fromstring(r.text)
    tree = html.fromstring(r)
    page_header = tree.xpath('//h5/text()')[0]
    file_name = page_header.strip().replace(' ', '_').replace(',', '').replace('/', '_') + '.txt'

    parsed_cols = ['fips', 'County', 'State', 'Value']
    table_rows = tree.xpath('//table[1][@class="tablesorter"]//tr')
    table_rows2 = tree.xpath('//table[2][@class="tablesorter"]//tr')
    header = table_rows.pop(0)
    table_rows2.pop(0)
    cols = {}
    dict_list = []
    for i, hd in zip(range(len(header)), header.xpath('./th[position()]/text()')):
        if hd in parsed_cols:
            cols[i] = hd.strip()

    for row in table_rows+table_rows2:
        dict1 = {}
        cnt = 0
        for column in row.xpath(
                './td[position()]/text() | ./th//text()'):  # row.xpath('./th[position()>0]/text() | ./td[position()=1]/a/text() | ./td[position()>1]/text()'):
            if cnt in cols.keys():
                dict1[cols[cnt]] = column.strip()
            cnt += 1
        if dict1['Value'] == 'Insufficient Data':
            continue

        fips = row.xpath('./th/a/@href')[0].strip()
        dict1['fips'] = fips[45:50]
        dict_list.append(dict1)

    df = pd.DataFrame(dict_list)
    print(file_name)
    df[parsed_cols].to_csv(os.path.join('output', file_name), sep='\t')
    print(df[parsed_cols])


if __name__ == '__main__':
    config_url = 'https://nccd.cdc.gov/DHDSPAtlas/proxy.ashx?https://proxy/api/config'
    get_url = "https://nccd.cdc.gov/DHDSPAtlas/ThematicDataHandler.ashx"
    #config_r = requests.get(url=config_url)  # , params=PARAMS)
    #all_parmam = create_params(json.loads(config_r.text))
    # ----
    filename = 'config.json'
    with open(filename, 'r', encoding="utf-8") as f:
        jsn = json.load(f)
    all_parmam = create_params(jsn)
    # ----
    cnt = 0
    for prm in all_parmam:
        #print(prm)
        get_and_parse(get_url, prm)
        cnt += 1
    print(cnt)

