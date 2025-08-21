import requests
from lxml import html
import json
import pandas as pd
import os

# api-endpoint
URL = "https://nccd.cdc.gov/DHDSPAtlas/ThematicDataHandler.ashx"

# GET_URL = 'https://nccd.cdc.gov/DHDSPAtlas/ThematicDataHandler.ashx?{"ThemeId":29,"ThemeFilterOptions":[{"FilterId":9,"FilterOptionId":"1"},{"FilterId":2,"FilterOptionId":"1"},{"FilterId":3,"FilterOptionId":"1"},{"FilterId":4,"FilterOptionId":"5"},{"FilterId":7,"FilterOptionId":"1"}],"GeographyType":"county","ParentGeographyFilter":""}'

# location given here
location = "delhi technological university"
# Risk Factors: 62, 64,64
# Sosial and Economict: 39,40,38,55,56,34,57 | 36,37,32,41,35,,54,60,52, 33, | 73,61,74 | 59
# Helth Care Delivery 65 ("FilterId":18, "FilterOptionId" 1-6) 44 ("FilterId":19, "FilterOptionId" 1-4) 58, 49,48,50,51, 53, 42
# Costs: 80 ("FilterId":17, "FilterOptionId" 1-4) 76 ("FilterId":17, "FilterOptionId" 1-4), 75
# defining a params dict for the parameters to be sent to the API
PARAMS = {"ThemeId": 29,  # Indicator theme 29-31,
          "ThemeFilterOptions": [{"FilterId": 9, "FilterOptionId": "1"},  # Years 1-9
                                 {"FilterId": 2, "FilterOptionId": "1"},  # Races Ethnicities 1-6
                                 {"FilterId": 3, "FilterOptionId": "1"},  # Gender 1-3
                                 {"FilterId": 4, "FilterOptionId": "5"},  # Ages 1-5
                                 {"FilterId": 7, "FilterOptionId": "1"}],  # Smoothed / Not Smoothed 1-2
          "GeographyType": "county",
          "ParentGeographyFilter": ""}

GET_URL = URL + '?' + json.dumps(PARAMS)
r = requests.get(url=GET_URL, params=PARAMS)
print(r.url)

tree = html.fromstring(r.text)
page_header = tree.xpath('//h5/text()')[0]
file_name = page_header.strip().replace(' ', '_').replace(',', '').replace('/', '_') + '.txt'

parsed_cols = ['fips', 'County', 'State', 'Value']
table_rows = tree.xpath('//table[1][@class="tablesorter"]//tr')
header = table_rows.pop(0)
cols = {}
dict_list = []
for i, hd in zip(range(len(header)), header.xpath('./th[position()]/text()')):
    if hd in parsed_cols:
        cols[i] = hd.strip()
for row in table_rows:
    dict1 = {}
    cnt = 0
    for column in row.xpath(
            './td[position()]/text() | ./th//text()'):  # row.xpath('./th[position()>0]/text() | ./td[position()=1]/a/text() | ./td[position()>1]/text()'):
        if cnt in cols.keys():
            dict1[cols[cnt]] = column.strip()
        cnt += 1

    fips = row.xpath('./th/a/@href')[0].strip()

    dict1['fips'] = fips[45:50]
    dict_list.append(dict1)

df = pd.DataFrame(dict_list)
print(file_name)
df[parsed_cols].to_csv(os.path.join('output', file_name), sep='\t')
print(df[parsed_cols])