from db_connect import DB_shula
import pandas as pd
import time

if __name__ == "__main__":
    db = DB_shula()
    db_url = db.get_url('ClinicalTrials')
    from_table = 'alltrials'
    to_table = 'eligibility_criterias'
    #query = 'SELECT id_info_nct_id,clinical_study_overall_status, eligibility_gender, eligibility_healthy_volunteers, eligibility_maximum_age, eligibility_minimum_age, eligibility_sampling_method, criteria FROM ' + table
    query = 'SELECT id_info_nct_id,clinical_study_overall_status, criteria FROM ' + from_table

    ct_df = pd.read_sql_query(query, db_url) #, params={'limit': 1000})
    types = ['Inclusion', 'Exclusion', 'DISEASE CHARACTERISTICS', 'PATIENT CHARACTERISTICS', 'PRIOR CONCURRENT THERAPY',
             'Affected patients', 'Unaffected Patients', 'Eligibility', 'considerations']
    no_types = []

    cnt=0

    for ct_df in pd.read_sql_query(query, db_url, chunksize=50000):
        print(cnt)
        cnt += 1
        criterias_list = []
        for i, r in ct_df.iterrows():

            #rint(r['id_info_nct_id'])
            if not r['criteria']:
                continue
            criterias = r['criteria'].split('\n\n')
            # print(criterias)
            crit_list = [x.strip().lstrip('-').strip() for x in criterias if x.strip() != '']
            curr_type = 'Unknown'
            id_list = []
            for st in crit_list:
                crit_dict = {'nct_id': r['id_info_nct_id']}
                new_type = [x for x in types if st.lower().startswith(x.lower())]
                # print(curr_type)
                if len(new_type) != 0:
                    curr_type = new_type[0]
                else:
                    crit_dict['type'] = curr_type
                    crit_dict['criteria'] = st.replace('\n', ' ')
                    criterias_list.append(crit_dict)
            # print(crit_list)
            if curr_type == 'Unknown':
                no_types.append({'nct_id': r['id_info_nct_id'], 'full_critiria': r['criteria']})
                #print(r['id_info_nct_id'] + ' !!!!  NO TYPES FOUNDS !!!!')
            # print('--------------------')
        time1 = time.time()
        eligibility_df = pd.DataFrame(criterias_list)
        eligibility_df.to_sql(to_table, db_url, if_exists='append', index=False)
        print('    saved ' + str(eligibility_df.shape[0]) + ' criteria to sql in ' + str(time.time() - time1))
        print('!!!!  NO TYPES !!!! for chunk ' + str(cnt) + '- ' + str(len(no_types)))

    print('!!!!  NO TYPES !!!!' + str(len(no_types)))
