import xml.etree.cElementTree as et
import pandas as pd
import os


def parse_one_xml(xml_file_name, event_list, attr_list):
    code_list = []
    try:
        tree = et.parse(xml_file_name)
        root = tree.getroot()
    except OSError:
        print('ERROR: !!!!!!!!!!!!!!!! '+str(xml_file_name)+'!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    attr_dict = {at: ".//Pr[@Name='"+at+"']" for at in attr_list}

    pid = xml_file_name.name[xml_file_name.name.rfind('\\')+1:xml_file_name.name.find('.')]
    all_ev = root.findall('Ev')
    op_ev = [ev for ev in all_ev if ev.attrib['Type'] in event_list]
    for ev in op_ev:
        info_dict = {'pid': pid, 'event_name': ev.attrib['Type'], 'date': ev.attrib['Time']}

        for key in attr_dict.keys():
            find_res = ev.find(attr_dict[key])
            info_dict[key] = find_res.text if find_res is not None else None
            info_dict[key+'hier'] = find_res.attrib['Hier'] if find_res is not None else None
        code_list.append(info_dict)
    return code_list


def read_rambam_xmls(rambam_xml_dir, section_type_list, att_list, out_file):
    xml_files = os.listdir(rambam_xml_dir)
    diag_df = pd.DataFrame()
    cnt = 0
    for file in xml_files:
        print(cnt)
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        cnt = cnt+1
        ret_list = parse_one_xml(xml_fd, section_type_list, att_list)
        if len(ret_list) > 0:
            diag_df = diag_df.append(ret_list)
        xml_fd.close()

    print(diag_df.shape)
    diag_df.to_csv(out_file, index=False, sep='\t')
    return diag_df
