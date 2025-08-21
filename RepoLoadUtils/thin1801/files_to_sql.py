import os
import pandas as pd
import pymssql
import time

if os.name =='nt':
    this1801_dir = 'T:\\THIN1801\\THINDB1801\\'
else:
    this1801_dir = '/server/Data/THIN1801/THINDB1801/'


tables_fields = {
    'patient': [('patid', 1, 4),
                ('patflag', 5, 5),
                ('yob', 6, 13),
                ('famnum', 14, 19),
                ('sex', 20, 20),
                ('regdate', 21, 28),
                ('regstat', 29, 30),
                ('xferdate', 31, 38),
                ('regrea', 39, 40),
                ('deathdate', 41, 48),
                ('deathinfo', 49, 49),
                ('accept', 50, 50),
                ('institute', 51, 51),
                ('marital', 52, 53),
                ('dispensing', 54, 54),
                ('prscexempt', 55, 56),
                ('sysdate', 57, 65)]
    ,
    'medical': [('patid', 1, 4),
                ('eventdate', 5, 12),
                ('enddate', 13, 20),
                ('datatype', 21, 22),
                ('medcode', 23, 29),
                ('medflag', 30, 30),
                ('staffid', 31, 34),
                ('source', 35, 35),
                ('episode', 36, 36),
                ('nhsspec', 37, 39),
                ('locate', 40, 41),
                ('textid', 42, 48),
                ('category', 49, 49),
                ('priority', 50, 50),
                ('medinfo', 51, 51),
                ('inprac', 52, 52),
                ('private', 53, 53),
                ('medid', 54, 57),
                ('consultid', 58, 61),
                ('sysdate', 62, 69),
                ('modified', 70, 70)],

    'therapy': [('patid', 1, 4),
                ('prscdate', 5, 12),
                ('drugcode', 13, 20),
                ('therflag', 21, 21),
                ('doscode', 22, 28),
                ('prscqty', 29, 36),
                ('prscdays', 37, 39),
                ('private', 40, 40),
                ('staffid', 41, 44),
                ('prsctype', 45, 45),
                ('opno', 46, 53),
                ('bnf', 54, 61),
                ('seqnoiss', 62, 65),
                ('maxnoiss', 66, 69),
                ('packsize', 70, 76),
                ('dosgval', 77, 83),
                ('locate', 84, 85),
                ('drugsource', 86, 86),
                ('inprac', 87, 87),
                ('therid', 88, 91),
                ('consultid', 92, 95),
                ('sysdate', 96, 103),
                ('modified', 104, 104)],
    'ahd': [('atid', 1, 4),
            ('eventdate', 5, 12),
            ('ahdcode', 13, 22),
            ('ahdflag', 23, 23),
            ('data1', 24, 36),
            ('data2', 37, 49),
            ('data3', 50, 62),
            ('data4', 63, 75),
            ('data5', 76, 88),
            ('data6', 89, 101),
            ('medcode', 102, 108),
            ('source', 109, 109),
            ('nhsspec', 110, 112),
            ('locate', 113, 114),
            ('staffid', 115, 118),
            ('textid', 119, 125),
            ('category', 126, 126),
            ('ahdinfo', 127, 127),
            ('inprac', 128, 128),
            ('private', 129, 129),
            ('ahdid', 130, 133),
            ('consultid', 134, 137),
            ('sysdate', 138, 145),
            ('modified', 146, 146)],
    'consult': [('consultid', 1, 4),
                ('patid', 5, 8),
                ('staffid', 9, 12),
                ('eventdate', 13, 20),
                ('sysdate', 21, 28),
                ('systime', 29, 34),
                ('constype', 35, 37),
                ('duration', 38, 43)],
}


def ascii_to_df(file_name, colspec, cols):
    full_file_name = this1801_dir + file_name
    fd = open(full_file_name)
    fdf = pd.read_fwf(fd, colspecs=colspec, names=cols)
    fd.close()
    return fdf


def create_table(conn, table):
    curr = conn.cursor()
    sql_command = "IF OBJECT_ID('" + table + "', 'U') IS NOT NULL DROP TABLE " + table + " CREATE TABLE " + table + " ("
    fields = [x[0] for x in tables_fields[table]]
    for fld in fields:
        sql_command = sql_command + fld + " VARCHAR(20),"
    sql_command = sql_command[:-1] + ')'
    print(sql_command)
    ret = curr.execute("" + sql_command + "")
    conn.commit()


def insert_to_table(conn, table, data):
    curr = conn.cursor()
    vals_s = '('
    for i in data.columns:
        vals_s = vals_s + '%s,'
    vals_s = vals_s[:-1] + ')'
    start_time = time.time()
    sql_command = "INSERT INTO " + table + " VALUES " + vals_s
    print(sql_command)
    data = data.astype(str)
    recs = data.to_records(index=False)
    recs = [tuple(x for x in rec) for rec in recs]
    ret = curr.executemany(sql_command, recs)
    print(' Inserted '+str(len(recs)) + ' recordes in ' + str(time.time() - start_time))
    conn.commit()


def load_one_type(conn, data_type, all_files):
    print('Loading ' + data_type)
    create_table(conn, data_type)
    files = [fl for fl in all_files if data_type in fl]
    fields = tables_fields[data_type]
    #files = files[2:3]
    locs = [(x[1] - 1, x[2]) for x in fields]
    headers = [x[0] for x in fields]
    cnt = 1
    for fl in files:
        print(str(cnt) + ') ' + fl)
        cnt = cnt+1
        data_df = ascii_to_df(fl, locs, headers)
        insert_to_table(conn, data_type, data_df)
        del data_df


def load_lookup_file(conn):
    curr = conn.cursor()
    full_file_name = this1801_dir + '\\..\\THINAncil1801\\text\\THINlookups1801.txt'
    fd = open(full_file_name)
    cols = ['field', 'code', 'description']
    fdf = pd.read_fwf(fd, colspecs=[(0, 10), (10, 11), (11,200)], names=cols)
    fd.close()
    sql_command = "IF OBJECT_ID('THINlookups', 'U') IS NOT NULL DROP TABLE THINlookups CREATE TABLE THINlookups (field VARCHAR(10), code CHAR, descriptions VARCHAR(200))"
    curr.execute("" + sql_command + "")
    conn.commit()
    sql_command = "INSERT INTO THINlookups VALUES (%s, %s, %s)"
    fdf = fdf.astype(str)
    recs = fdf.to_records(index=False)
    recs = [tuple(x for x in rec) for rec in recs]
    curr.executemany(sql_command, recs)
    conn.commit()


if __name__ == '__main__':
    conn = pymssql.connect(server='', user=r'', password='', database='')
    thin_files = os.listdir(this1801_dir)

    #load_one_type(conn, 'patient', thin_files)
    load_one_type(conn, 'medical', thin_files)
    load_one_type(conn, 'therapy', thin_files)
    load_one_type(conn, 'ahd', thin_files)
    load_one_type(conn, 'consult', thin_files)

    #load_lookup_file(conn)

    print('DONE')
