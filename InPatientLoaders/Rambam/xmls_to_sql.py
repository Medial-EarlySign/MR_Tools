import pandas as pd
import os
import lxml.etree as et
import pymssql
import time

rambam_xml_dir = 'T:\\RAMBAM\\da_medial_patients'


def create_schema_from_xml(rambam_xml_dir):
    evenets_dicst = {}
    xml_files = os.listdir(rambam_xml_dir)[60000:61000]  #sample 1000 patients from later years
    for file in xml_files:
        file_name = rambam_xml_dir+'\\'+file
        xml_fd = open(file_name)
        tree = et.parse(xml_fd)
        root = tree.getroot()
        evenets_dicst['demographics'] = list(root.attrib.keys())
        all_ev = root.findall('Ev')
        ev_set = set([ev.attrib['Type'] for ev in all_ev])
        events_types_set = set(evenets_dicst.keys())
        to_parse = list(ev_set - events_types_set)
        for evname in to_parse:
            ev = [ev for ev in all_ev if ev.attrib['Type'] == evname][0]
            field_list = ['pid'] + ev.keys()
            for attr in list(ev):
                field_list.extend([attr.attrib['Name'], attr.attrib['Name']+'Hier'])
            evenets_dicst[evname] = field_list
        if len(evenets_dicst.keys()) >= 23:
            break

    return evenets_dicst


def create_tables(curr, tables_fields):
    curr = conn.cursor()
    for table, fields in tables_fields.items():
        sql_command = "IF OBJECT_ID('" + table + "', 'U') IS NOT NULL DROP TABLE " + table +" CREATE TABLE "+table+" ("
        for fld in fields:
            if 'medicationcodeHier' in fld or 'servicecodeHier' in fld or 'conditioncode' in fld:
                sql_command = sql_command + fld + " NVARCHAR(1024),"
            else:
                sql_command = sql_command + fld + " NVARCHAR(256),"
        sql_command = sql_command[:-1]
        sql_command = sql_command + ')'
        print(sql_command)
        ret = curr.execute(""+sql_command+"")
        print(ret)
    conn.commit()



def xmls_to_lists(xml_files, tables):
    #xml_files = os.listdir(rambam_xml_dir)[60000:60010]  # sample 1000 patients from later years
    tables_values = {}
    for tb, flds in tables.items():
        tables_values[tb] = []
    cnt = 0
    for file in xml_files:
        file_start_time = time.time()
        cnt=cnt+1
        file_name = rambam_xml_dir + '\\' + file
        xml_fd = open(file_name)
        tree = et.parse(xml_fd)
        root = tree.getroot()
        dem_dict = {fld: root.attrib[fld] for fld in tables['demographics']}
        tables_values['demographics'].append(dem_dict)
        pid = root.attrib['ID']
        all_ev = root.findall('Ev')
        print(str(cnt) + ') ' + pid + ' events num:' + str(len(all_ev)))
        if len(all_ev) > 10000:
            continue
        ev_loop_start_time = time.time()
        for ev in all_ev:
            row = {'pid': pid}
            row.update(dict(ev.attrib))
            row.update({attr.attrib['Name']: attr.text for attr in list(ev)})
            row.update({attr.attrib['Name'] + 'Hier': attr.attrib['Hier'] for attr in list(ev)})
            tables_values[ev.attrib['Type']].append(row)
        xml_fd.close()
        end_time = time.time()
        print('file process time=' + str(end_time-file_start_time) + " ev loop time=" + str(end_time-ev_loop_start_time))
    return tables_values


def lists_to_sql_tables(conn, val_list, tables_fields):
    curr = conn.cursor()
    for tbl in tables_fields.keys():
        if len(tables_fields[tbl]) == 0 or tbl == 'ev_lab_result_vector':
            continue
        print(' insert to table ' + tbl)
        vals_s = '('
        for i in range(len(tables_fields[tbl])):
            vals_s = vals_s + '%s,'

        vals_s = vals_s[:-1] + ')'
        start_time = time.time()
        sql_command = "INSERT INTO " + tbl + " VALUES " + vals_s
        recs = [tuple(vals[key] for key in tables_fields[tbl]) for vals in val_list[tbl]]
        ret = curr.executemany(sql_command, recs)
        print('Inserted ' + str(len(recs)) + ' in '+str(time.time()-start_time))
    conn.commit()


def lists_to_sql_tables_bulk(conn, val_list, tables_fields):
    bulk_file_name = 'temp1.txt'
    curr = conn.cursor()
    for tbl in tables_fields.keys():
        if len(tables_fields[tbl]) == 0:
            continue
        print(' insert to table ' + tbl)
        '''
        vals_s = '('
        for i in range(len(tables_fields[tbl])):
            vals_s = vals_s + '%s,'

        vals_s = vals_s[:-1] + ')'
        '''
        sql_command = "BULK INSERT " + tbl + " FROM '" + bulk_file_name + "'"
        recs =[tuple(vals[key] for key in tables_fields[tbl]) for vals in val_list[tbl]]
        f = open(bulk_file_name, "w+")
        f.write(str(recs))
        f.close()
        ret = curr.execute(sql_command)
    conn.commit()


if __name__ == '__main__':
    events_dc = create_schema_from_xml(rambam_xml_dir)
    conn = pymssql.connect(server='server', database='RawRambam')
    create_tables(conn, events_dc)
    chunk_size = 200
    chunk_start = 9300
    xml_files = os.listdir(rambam_xml_dir)
    while chunk_start < len(xml_files):
        print('parsing chunk start in ' + str(chunk_start))
        xmls = xml_files[chunk_start: chunk_start+chunk_size]
        tables_lists = xmls_to_lists(xmls, events_dc)
        lists_to_sql_tables(conn, tables_lists, events_dc)
        del tables_lists
        chunk_start = chunk_start + chunk_size
    #print(insert_to_tables)
