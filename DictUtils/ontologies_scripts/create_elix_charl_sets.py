import os
from elix_charl_defs import get_charlson_sets, get_elixhauser_sets
from utils import fixOS, replace_spaces, write_tsv

onto_path ='..\\Ontologies\\'
out_path = onto_path+'ELIX_CHARL\\dicts'

if __name__ == '__main__':
    icd9_dict_file = 'dict.icd9dx'
    como_set_file = 'dict.comorbidity_scores'
    icd9_dict_file = os.path.join(onto_path, 'ICD9', 'dicts', icd9_dict_file)

    elix_ind = 940000
    elix_set_df = get_elixhauser_sets(icd9_dict_file)
    elix_set_df['outer'] = 'ELIXHAUSER:' + replace_spaces(elix_set_df['outer'])
    elix_def_df = elix_set_df.drop_duplicates('outer')[['outer']].copy()
    elix_def_df['def'] = 'DEF'
    elix_def_df = elix_def_df.assign(defid=range(elix_ind, elix_ind+elix_def_df.shape[0]))
    write_tsv(elix_def_df[['def', 'defid', 'outer']], out_path, como_set_file, mode='w')

    charl_ind = 950000
    charl_set_df = get_charlson_sets(icd9_dict_file)
    charl_set_df['outer'] = 'CHARLSON:' + replace_spaces(charl_set_df['outer'])
    charl_def_df = charl_set_df.drop_duplicates('outer')[['outer']].copy()
    charl_def_df['def'] = 'DEF'
    charl_def_df = charl_def_df.assign(defid=range(charl_ind, charl_ind + charl_def_df.shape[0]))
    write_tsv(charl_def_df[['def', 'defid', 'outer']], out_path, como_set_file, mode='a')
    elix_set_df = elix_set_df.append(charl_set_df, ignore_index=True, sort=False)
    write_tsv(elix_set_df[['def', 'outer', 'inner']], out_path, como_set_file, mode='a')
