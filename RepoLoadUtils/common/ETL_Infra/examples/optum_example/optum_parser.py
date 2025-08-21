import os
from ETL_Infra.data_fetcher.db_fetcher import db_fetcher, postgres_connection_string, DB_Access

def get_db():
    user = ''
    password = ''
    host = ''
    port = 5439
    database =''
    
    conn_str = f"redshift+redshift_connector://{user}:{password}@{host}:{port}/{database}"
    db=DB_Access(conn_str, {"sslmode": "verify-ca"})
    return db

batch_mapper=dict()
def optum_parser_demographic(batch_size, start_batch):
    db=get_db()
    #GENDER, BDATE, BYEAR, RACE, ETHNICITY, DEATH, MEMBERSHIP
    query="""
SELECT substring(ptid,3) as pid, birth_yr as byear, gender as sex, race,ethnicity,
first_month_active, last_month_active, date_of_death from db_schema.patient
"""
    #db_fetcher(db, sql_query, batch_size, start_batch, batch_mapper)
    return db_fetcher(db, query, batch_size, start_batch, batch_mapper)

