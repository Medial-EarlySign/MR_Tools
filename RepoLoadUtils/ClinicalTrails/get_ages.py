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
    query = "SELECT * FROM " + table + " WHERE type != 'Exclusion' AND (LOWER(criteria) like '%%age%%' OR LOWER(criteria) like '%%adult%%')"
    one_id = ""
    #one_id = " AND nct_id = 'NCT00000493'"
    query = query + one_id
    ct_df = pd.read_sql_query(query, db_url)
    print(ct_df.shape)
    return ct_df  # ['criteria'].values.tolist()


def get_criterias_files(path):
    files = os.listdir(path)
    files = [x for x in files if x.startswith('eligibility_criterias')]
    all_age_crits = pd.DataFrame()
    for f in files:
        ff = os.path.join(path,f)
        crits = pd.read_csv(ff, sep='\t')
        crits = crits[(crits['criteria'].str.lower().str.contains('age')) |
                      (crits['criteria'].str.lower().str.contains('adult')) |
                      (crits['criteria'].str.lower().str.contains('years old')) |
                      (crits['criteria'].str.lower().str.contains(' y/o'))]
        crits = crits[crits['type'] != 'Exclusion']
        all_age_crits = all_age_crits.append(crits)
    print(all_age_crits.shape)
    #all_age_crits = all_age_crits[all_age_crits['nct_id'] == 'NCT00000152']
    return all_age_crits


add_spaces = ['≤', '<', '≥', '>']
if __name__ == "__main__":
    # ----
    # db = DB_shula()
    # db_url = db.get_url('ClinicalTrials')
    # crit_df = get_criterias(db_url)
    # -----
    path = fixOS('/nas1/Work/Users/Tamar/ClinicalTrials_load/')
    crit_df = get_criterias_files(path)
    # ----
    no_age = 0
    age = 0
    ages_list = []
    for i, r in crit_df.iterrows():
        sentence = r['criteria'].lower()
        sentence = re.sub('^\d\.', '', sentence)  # remove the traling numbering 1., 2.
        sentence = sentence.replace('-', ' ')  # to break age range to agss
        for sp in add_spaces:  # split the bigger then / smaller then fro the number
            sentence = sentence.replace(sp, ' ' + sp + ' ')

        tokens = nltk.word_tokenize(sentence)
        stem_tokens = stem_sentence(tokens)
        #if 'age' in stem_tokens or 'adult' in stem_tokens:
        if 'age' in sentence and not 'age' in stem_tokens:
            no_age += 1
            continue
        else:
            age_dict = {'nct_id': r['nct_id'], 'year': np.nan}
            if 'year' in stem_tokens or 'y/o' in stem_tokens:
                age_dict['year'] = 1
            ages = []
            #print(sentence)
            tagged = nltk.pos_tag(stem_tokens)
            #print(tagged)
            for tg in tagged:
                if tg[1] == 'CD':
                    num_tag = get_number_only(tg[0].replace(',', ''))
                    if 0 <= num_tag < 120:
                        ages.append(num_tag)
            if len(ages) >= 2:
                age_dict['min'] = ages[0]
                age_dict['max'] = ages[1]
            elif len(ages) == 1:
                if '≤' in stem_tokens or '<' in stem_tokens or 'under' in stem_tokens or 'less' in stem_tokens or \
                        'up to' in sentence or 'younger' in sentence or 'not more' in sentence:
                    age_dict['min'] = np.nan
                    age_dict['max'] = ages[0]
                else:
                    age_dict['min'] = ages[0]
                    age_dict['max'] = np.nan
            elif len(ages) == 0 and 'adult' in stem_tokens and 'age' not in stem_tokens:
            #else:
                age_dict['min'] = 18
                age_dict['max'] = np.nan
            ages_list.append(age_dict)
            age += 1
        #print(is_age)
        # tagged = nltk.pos_tag(tokens)
        # print(tagged)
        # sen_text = nltk.Text(w.lower() for w in stem_tokens)
        # print(sen_text.concordance("age"))

    print('No age sentences = ' + str(no_age))
    print('Age sentences = ' + str(age))

    ages_df = pd.DataFrame(ages_list)

    # Some clean ups

    ages_df.loc[:, 'max1'] = ages_df['max']
    ages_df.loc[:, 'min1'] = ages_df['min']
    ages_df.loc[ages_df['max1'] < ages_df['min1'], 'max'] = ages_df['min1']
    ages_df.loc[ages_df['max1'] < ages_df['min1'], 'min'] = ages_df['max1']

    #ages_df = ages_df[(ages_df['min'].notnull()) | (ages_df['max'].notnull())]

    ages_df.sort_values(by=['nct_id', 'year', 'min', 'max'], na_position='last', inplace=True)
    ages_df.drop_duplicates('nct_id', keep='first', inplace=True)
    print('CT with age sentences = ' + str(ages_df['nct_id'].nunique()))


    ages_df[['nct_id', 'min', 'max']].to_csv(fixOS('/nas1/Work/Users/Tamar/ClinicalTrials_load/ages_nlp.txt'), sep='\t', index=False)

