# supress deprecated warnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import pandas as pd
import os
import matplotlib.pyplot as plt
import argparse
from sqlalchemy import engine_from_config
from datetime import datetime


class DB_shula:
    def __init__(self):
        self.host = 'localhost'
        self.port = '5433'
        self.username = 'postgres'
        self.password = 'aaa'

    def get_url(self, dbname):
        uri_psql = 'postgresql+psycopg2://' + self.username + ':' + self.password + '@' + self.host + ':' + self.port+' /' + dbname
        return uri_psql

    def get_engine(self, dbname):
        config = {
            "sqlalchemy.url": 'postgresql://' + self.username + ':' + self.password + '@' + self.host + ':' + self.port+' /' + dbname,
            "sqlalchemy.echo": False,
            "sqlalchemy.server_side_cursors": True,
        }
        engine = engine_from_config(config)
        return engine



def input_dist_figures(request_df, threshold, out_dir):
    for sig in request_df.columns:
        if sig == 'correlation_id':
            continue
        sig_s = request_df[request_df[sig].notnull()][sig].copy()
        if sig_s.shape[0] == 0:
            print('  ' + sig + ' skipped (no datapoints)')
            continue

        if pd.api.types.is_numeric_dtype(sig_s):
            ax1 = sig_s.plot.hist(title=sig + ' Distribution')
            if sig == 'score':
                ax1.axvline(x=threshold, color='r', linewidth=3)
        else:
            ax1 = sig_s.value_counts().plot.bar(title=sig + ' Distribution')
        fig2 = ax1.get_figure()
        fig2.savefig(os.path.join(out_dir, sig + '_dist'))
        plt.cla()
        plt.clf()
        print('  ' + sig)
    return


def parse_request(request_df):
    dict_list = []
    for i, r in request_df.iterrows():
        s = r['content']['Signals']
        dict1 = {x['Code']: x['Data'][0]['Value'][0] for x in s if len(x['Data'][0]['Value']) > 0}
        dict1['correlation_id'] = r['correlation_id']
        dict_list.append(dict1)
    df = pd.DataFrame(dict_list)
    # convert to numeric if needed
    for sig in df.columns:
        if sig == 'correlation_id':
            continue
        if df[df[sig].notnull()].shape[0] > 0:
            num_ser = pd.to_numeric(df[sig], errors='coerce')
            # if more then 80% of the values can be converted to numeric it is numeric column
            if num_ser[num_ser.notnull()].shape[0]/df[df[sig].notnull()].shape[0]:
                df.loc[:, sig] = num_ser
    return df


def signals_summary(all_df, out_dir):
    sig_list = []
    for sig in all_df.columns:
        if sig == 'correlation_id':
            continue
        desc_dict = all_df[all_df[sig].notnull()][sig].describe()
        sig_list.append(desc_dict)
    summ_df = pd.DataFrame(sig_list)
    summ_df.to_csv(os.path.join(out_dir, 'signal_summary.csv'))


def score_to_float(x):
    if str(x).startswith("{'Signals'"):
        return float(x['Signals'][0]['Value'][0])
    return -1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--f_output', help="The output path")
    parser.add_argument('--f_marker', help="The AlgoMarker", default='LGI-Flag')
    parser.add_argument('--f_threshold', help="The score threshold", default=3)
    parser.add_argument('--f_from_date', help="Requests from date", default='19000101')
    parser.add_argument('--f_to_date', help="Requests to date", default='30000101')

    args = parser.parse_args()
    if not args.f_output:
        raise Exception('no output path supplied. Please supply one using --f_output')

    outdir = args.f_output
    calc = args.f_marker
    threshold = args.f_threshold
    from_date = args.f_from_date
    to_date = args.f_to_date

    #calc = 'LGI-Flag'
    #outdir = 'W:\\Users\\Tamar\\log_analyzer'

    print('\nExecuting with')
    print('  Output Dir: ' + outdir)
    print('  AlgoMarker: ' + calc)
    print('  Threshold:  ' + str(threshold) + '%')
    print('  From date:  ' + str(from_date))
    print('  To date:    ' + str(to_date))

    if not os.path.exists(outdir):
        os.makedirs(outdir)

    dbname = 'AlgoAnalyzer.Log'
    db_conn = DB_shula()
    db_engine = db_conn.get_engine(dbname)

    print('')

    print('Parsing responses...', end =" ")
    query = "SELECT timestamp_utc, content, correlation_id FROM public.log_entry WHERE log_type = 'ScorerResponse' and content is not NULL and timestamp_utc >= '" + from_date + "' and timestamp_utc <= '" + to_date + "' order by timestamp_utc"
    resp_df = pd.read_sql_query(query, db_engine)
    #resp_df['score'] = resp_df['content'].apply(lambda x: float(x['Signals'][0]['Value'][0]))
    resp_df['score'] = resp_df['content'].apply(lambda x: score_to_float(x))
    resp_df = resp_df[(resp_df['score'] > 0) & (resp_df['score'] <= 1)]
    resp_df['calculator'] = resp_df['content'].apply(lambda x: x['Calculator'])
    resp_df = resp_df[(resp_df['calculator'] == calc)]
    th = resp_df['score'].quantile((100-threshold)/100)
    print('done')

    print('  ' + str(threshold) + '% threshold value: ' + str(th))

    print('Parsing requests...', end =" ")
    query = "SELECT timestamp_utc, content, correlation_id FROM public.log_entry WHERE log_type = 'ScorerRequest' and content is not NULL and timestamp_utc >= '" + from_date + "' and timestamp_utc <= '" + to_date + "' order by timestamp_utc"
    req_df = pd.read_sql_query(query, db_engine)
    req_df['calculator'] = req_df['content'].apply(lambda x: x['Calculator'])
    req_df = req_df[(req_df['calculator'].str.contains(calc))]
    parsed_req = parse_request(req_df)
    print('done')

    print('Generating analysis...', end =" ")
    #print(parsed_df)
    out_df = resp_df[['correlation_id', 'score']].merge(parsed_req, on='correlation_id', how='left')
    print('done')

    print('Generating distribution images...')
    input_dist_figures(out_df, th, outdir)

    print('Generating ''signal_summary.csv''...', end =" ")
    signals_summary(out_df, outdir)
    print('done')

    print('Generating ''full_table.csv''...', end =" ")
    out_df.to_csv(os.path.join(outdir, 'full_table.csv'), index=False)
    print('done')

    print('')


