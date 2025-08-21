#import xml.etree.cElementTree as et
import pandas as pd
import os
import lxml.etree as et
import time

rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'
rambam_events =


def create_schema_from_xml(rambam_xml_dir):
    evenets_dicst = {}
    xml_files = os.listdir(rambam_xml_dir)[60000:61000]  #sample 1000 patients from later years
    for file in xml_files:
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        tree = et.parse(xml_fd)
        root = tree.getroot()
        all_ev = root.findall('Ev')
        ev_set = set([ev.attrib['Type'] for ev in all_ev])
        events_types_set = set(evenets_dicst.keys())
        to_parse = list(ev_set - events_types_set)
        for evname in to_parse:
            ev = [ev for ev in all_ev if ev.attrib['Type'] == evname][0]
            field_list = ['Type','']





def parse_one_xml_for_values(xml_file_name):
    code_list = []
    try:
        tree = et.parse(xml_file_name)
        root = tree.getroot()
    except OSError:
        print('ERROR: !!!!!!!!!!!!!!!! '+str(xml_file_name)+'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    all_ev = root.findall('Ev')
    op_ev = [ev for ev in all_ev if ev.attrib['Type'] == 'ev_measurements_numeric']
    for ev in op_ev:
        attr = 'measurementcode'
        attr_name = ev.find(".//Pr[@Name='"+attr+"']")
        if attr_name is not None:
            cond_dict = {'code': attr_name.text, 'desc': attr_name.attrib['Hier']}
            code_list.append(cond_dict)
    return code_list


def parse_one_xml_lxml(xml_file_name):
    try:
        tree = et.parse(xml_file_name)
        root = tree.getroot()
    except OSError:
        print('ERROR: !!!!!!!!!!!!!!!! '+str(xml_file_name)+'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    all_ev = root.findall('Ev')
    ev_list = set([ev.attrib['Type'] for ev in all_ev])
    return list(ev_list)



def read_rambam_xmls(rambam_xml_dir, out_file):
    xml_files = os.listdir(rambam_xml_dir)[60000:61000]
    event_s = pd.Series()
    cnt = 0
    start_time = time.time()
    for file in xml_files:
        print(cnt)
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        cnt = cnt+1
        ret_list = parse_one_xml_lxml(xml_fd)
        if len(ret_list) > 0:
            event_s = event_s.append(pd.Series(ret_list),  ignore_index=False)
            event_s.drop_duplicates(inplace=True)
        xml_fd.close()

    print(event_s.shape)
    print(event_s)
    print(time.time() - start_time)
    return event_s


def read_rambam_xmls2(rambam_xml_dir, out_file):
    xml_files = os.listdir(rambam_xml_dir)
    event_df = pd.DataFrame()
    cnt = 0
    for file in xml_files:
        print(cnt)
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        cnt = cnt+1
        ret_list = parse_one_xml_for_values(xml_fd)
        if len(ret_list) > 0:
            event_df = event_df.append(ret_list)
            event_df.drop_duplicates(inplace=True)
        xml_fd.close()

    print(event_df)
    event_df.to_csv(out_file, index=False, sep='\t')
    return event_df


if __name__ == '__main__':
    events_df = read_rambam_xmls2(rambam_xml_dir, "measurement_types.csv")
