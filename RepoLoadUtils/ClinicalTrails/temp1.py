import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from db_connect import DB_shula
import pandas as pd
import re
from utils import fixOS, is_nan
from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktParameters
punkt_param = PunktParameters()
#punkt_param.abbrev_types = set(['dr', 'vs', 'mr', 'mrs', 'prof', 'inc'])
sentence_splitter = PunktSentenceTokenizer(punkt_param)



text1 = '\n        Inclusion Criteria:\n\n        1-Patient with breast cancer proved by histology and treated surgically 2. Relevant of\n        adjuvant radiotherapy after partial or total mastectomy with or without lymph node\n        irradiation 3- Age ≥ 18 years 4- Information and no opposition to the patient\n\n        Exclusion Criteria:\n\n          1. - Metastatic disease\n\n          2. - Patient having another severe disease or uncontrolled which could jeopardize the\n             trial participation\n\n          3. - pregnant or breastfeeding woman 4-inability to do follow-up medical care of clinical\n             trial for geographical, social or psychological reasons\n      '
text2 = '\n        Inclusion Criteria:\n\n          -  Patients between 5 and 12 years.\n\n          -  Meet DSM-IV criteria for autism spectrum disorder.\n\n          -  Patients who have been diagnosed at least 2 years before inclusion in the study.\n\n        Exclusion Criteria:\n\n          -  Acute visual or hearing loss.\n\n          -  Traumatic brain injury.\n\n          -  Other neurological disorders: migraine, epilepsy, tuberous sclerosis ...\n\n          -  Trauma at birth.\n\n          -  Mental retardation.\n\n          -  Pregnancy.\n      '
text3 = 'patient has received one line of chemotherapy prior to enrolment in the adjuvant or in the metastatic setting (including chemoradiotherapy) and progressed after this line of chemotherapy'
txt = text1 .replace('\n\n', ' .\n')
words_tokens = nltk.word_tokenize(text3)
pos_tag = nltk.pos_tag(words_tokens)

words = [w.lower() for w in words_tokens]
words = [w for w in words if not w in stopwords.words("english")]
text = nltk.Text(words)
#fdist = nltk.FreqDist(text)

#stem_tokens = stem_sentence(tokens)
tokens = nltk.sent_tokenize(text3)
sentences = sentence_splitter.tokenize(txt)

tokens = [x.strip().lstrip('-').strip() for x in tokens if x.strip() != '']
i=0
for s in tokens:
    i+=1

    print(str(i) + ')' + s)
    print('----')

sentences = [x.strip().lstrip('-').strip() for x in sentences if x.strip() != '']
i=0
for s in sentences:
    i+=1

    print(str(i) + ')' + s)
    print('----')