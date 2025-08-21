import nltk
from nltk.stem import PorterStemmer
from nltk.stem.snowball import SnowballStemmer
from db_connect import DB_shula
import pandas as pd
import numpy as np
import re
import os
from utils import fixOS, is_nan
from word2number import w2n

# from nltk.book import *
# from nltk.corpus import treebank

porter = PorterStemmer()
#porter = SnowballStemmer("english")


def stem_sentence(token_words):
    stem_sentence = []
    for word in token_words:
        try:
            word1 = str(w2n.word_to_num(word))
            if word == 'one':
                word1 = word
        except ValueError:
            word1 = word
        stem_sentence.append(porter.stem(word1))
    return stem_sentence


def get_number_only(a):
    if is_nan(a):
        return a
    m = re.findall(r'\d+', a)
    if m:
        return int(m[0])
    else:
        return np.nan


def get_criterias(db_url):
    table = 'eligibility_criterias_nlp'
    query = "SELECT * FROM " + table + " WHERE type == 'Inclusion'"
    one_id = ""
    #one_id = " AND nct_id = 'NCT00000493'"
    query = query + one_id
    ct_df = pd.read_sql_query(query, db_url)
    print(ct_df.shape)
    return ct_df  # ['criteria'].values.tolist()


def get_inclusion_criterias_files(path):
    files = os.listdir(path)
    files = [x for x in files if x.startswith('eligibility_criterias')]
    all_inclusion = pd.DataFrame()
    for f in files:
        ff = os.path.join(path, f)
        crits = pd.read_csv(ff, sep='\t')
        crits = crits[crits['type'] == 'Inclusion']
        all_inclusion = all_inclusion.append(crits)
        break
    print(all_inclusion.shape)
    # all_inclusion = all_inclusion[all_inclusion['nct_id'] == 'NCT00000152']
    return all_inclusion


if __name__ == "__main__":
    # ----
    # db = DB_shula()
    # db_url = db.get_url('ClinicalTrials')
    # crit_df = get_criterias(db_url)
    # -----
    path = fixOS('/nas1/Work/Users/Tamar/ClinicalTrials_load/')
    crit_df = get_inclusion_criterias_files(path)
    # ----
    crit_list = []
    for i, r in crit_df.iterrows():
        sentence = r['criteria'].lower()

        tokens = nltk.word_tokenize(sentence)
        stem_tokens = stem_sentence(tokens)
        #if 'age' in stem_tokens or 'adult' in stem_tokens:
        tagged = nltk.pos_tag(stem_tokens)
        #print(tagged)
        for tg in tagged:
            if tg[1] == 'CD':
                num_tag = get_number_only(tg[0].replace(',', ''))


    crit_df_df = pd.DataFrame(crit_list)

    #crit_df_df.to_csv(fixOS('/nas1/Work/Users/Tamar/ClinicalTrials_load/crits.txt'), sep='\t', index=False)

