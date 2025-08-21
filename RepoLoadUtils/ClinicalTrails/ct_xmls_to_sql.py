import pandas as pd
import os
import xml.etree.ElementTree as etree
from utils import fixOS
from db_connect import DB_shula
import time
import sqlalchemy



'''
for child in root:
    child_tag = child.tag
    child_list = [x.tag for x in root.findall(child.tag+"/*")]
    print(child_tag)
    print([x.tag for x in root.findall(child.tag+"/*")])
    for tag in child_list:

columns = [e.tag for e in root.iter()]
cnt=0
for node in root:
    print(cnt)
    cnt+=1
    print(node.tag)
    node_list = [x.tag for x in root.findall(node.tag + "/*")]
    print(node_list)
    for
    #for c in columns:
    #    c_val = node.find(c) #.text
    #    if c_val is not None:
    #        cnt+=1
    #        print(str(cnt) + ':' + c + '=' + c_val.text)
'''


def node_to_val(node, parent, dict1):
    # print('%s: %s' % (node.tag.title(), node.attrib.get('name', node.text)))
    #print(parent.tag)
    #print(node.tag + ' = ' + node.text)
    if node.tag == 'textblock':
        key1 = parent.tag
    else:
        key1 = parent.tag+'_'+node.tag
    if key1 in dict1.keys():
        dict1[key1] = dict1[key1] + '|' + node.text
    else:
        dict1[key1] = node.text


def get_node(n, dict1):
    skips = ['pending_results','clinical_results']
    for m in n:
        #print(n.tag, m.tag)
        if m.tag in skips:
            continue
        if m.text.strip() != '':
            node_to_val(m,n, dict1)
        yield from get_node(m, dict1)


def group_to_sql(dict_name, db_url):
    table = 'alltrials'
    all_xmls = os.listdir(dict_name)
    ll_xmls = [x for x in all_xmls if x.endswith('.xml')]
    #all_xmls = ['NCT00000125.xml']
    dict_list = []
    for xml_f in all_xmls:
        #print(xml_f)
        dict1 = {}
        tree = etree.parse(os.path.join(dict_name, xml_f))
        root = tree.getroot()
        list(get_node(root, dict1))
        dict_list.append(dict1)
        #break
    ct_df = pd.DataFrame(dict_list)
    #print(ct_df)
    try:
        query = 'SELECT * FROM ' + table
        exist_cols = pd.read_sql_query(query, db_url, params={'limit':1})
        miss = list(set(ct_df.columns) - set(exist_cols.columns))
        cols = set(ct_df.columns) - set(miss)
        print('Additionals cols = ' + str(miss))
    except sqlalchemy.exc.ProgrammingError:
        cols = ct_df.columns
        pass
    time1 = time.time()
    cols = [x.strip() for x in cols]
    ct_df[cols].to_sql(table, db_url, if_exists='append', index=False)
    print('    saved ' + str(ct_df.shape[0]) + ' trials to sql in ' + str(time.time() - time1))


#def eligibility_to_sql()


if __name__ == "__main__":
    db = DB_shula()
    db_url = db.get_url('ClinicalTrials')

    files_path = fixOS('/nas1/Work/Users/Tamar/ClinicalTrials')
    groups = os.listdir(files_path)
    groups = [x for x in groups if x.startswith('NCT')]
    for gr in groups:
        print(gr)
        full_dict = os.path.join(files_path, gr)
        group_to_sql(full_dict, db_url)

    #list(get_node(root))
    #dict_list.append(dict1)
    #print(dict_list)