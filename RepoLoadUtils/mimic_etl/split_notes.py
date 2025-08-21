from sqlalchemy import engine_from_config
import pandas as pd


class DB_shula:
    def __init__(self):
        self.host = '192.168.102.41'
        self.port = 1443
        self.username = 'postgres'
        self.password = ''
        self.default_batch_size = 5000000


    def get_url(self, dbname):
        uri_psql = 'postgresql+psycopg2://' + self.username + ':' + self.password + '@' + self.host + ':5432/' + dbname
        return uri_psql

    def get_engine(self, dbname):
        config = {
            "sqlalchemy.url": 'postgresql://' + self.username + ':' + self.password + '@' + self.host + ':5432/' + dbname,
            "sqlalchemy.echo": True,
            "sqlalchemy.server_side_cursors": True,
        }
        engine = engine_from_config(config)
        return engine


def note_to_sections(nt, sections):
    loc_dict = {}
    sec_dict = {}
    for sec in sections:
        sec_loc = nt.find(sec)
        loc_dict[sec] = sec_loc
    loc_dict['stop'] = len(nt)
    sorted_ser = pd.Series(loc_dict).sort_values()
    if sorted_ser[sorted_ser == 0].shape[0] !=1:
        sorted_ser = sorted_ser.append(pd.Series([0], index=['start']))
        sorted_ser.sort_values(inplace=True)
    for i in range(0, sorted_ser.shape[0]-1):
        col = sorted_ser.index[i]
        start = sorted_ser.iloc[i]
        end = sorted_ser.iloc[i+1]
        #print(col, start, end)
        if start == -1:
            sec_dict[col] = ''
        else:
            cont = nt[start: end]
            cont = cont.replace(col, '')
            cont = cont[1:]
            cont = cont.strip()
            cont = cont.replace('\n', '[NL]')
            sec_dict[col] = cont
    return sec_dict


def split_physician_notes(db_engine, outfile):
    sections = ['Chief Complaint', '24 Hour Events', 'Allergies', 'Last dose of Antibiotics', 'Other medications',
                'Infusions', 'Other ICU medications', 'Other medications', 'Vital signs', 'Respiratory support',
                'Physical Examination', 'Labs / Radiology', 'Assessment and Plan', 'ICU Care']

    note_sql = "SELECT subject_id, hadm_id, charttime, description, text FROM public.noteevents WHERE category='Physician '"
    note_df = pd.read_sql_query(note_sql, db_engine)

    all_notes = []
    for i, r in note_df.iterrows():
        nt = r['text']
        note_row = note_to_sections(nt, sections)
        note_row['subject_id'] = r['subject_id']
        note_row['hadm_id'] = r['hadm_id']
        note_row['charttime'] = r['charttime']
        all_notes.append(note_row)
    all_df = pd.DataFrame(all_notes)
    print(all_df.shape)
    all_df.to_csv(outfile, sep='\t', index=False)
    print('DONE - splited notes writen to ' + outfile)


if __name__ == "__main__":
    dbname = 'MimicRaw'
    db_conn = DB_shula()

    db_engine = db_conn.get_engine(dbname)
    split_physician_notes(db_engine, '/nas1/Work/Users/Tamar/NLP/mimic_physician_test.txt')

