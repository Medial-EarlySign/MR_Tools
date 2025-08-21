import pandas as pd
from dict_from_bioportal import code_bioportal_df, build_def_dict, build_set_dict, def_wo_chars

ONTO_NAME = 'SNMI'
snmi_codes_csv = '..\\Ontologies\\' + ONTO_NAME + '\\SNMI.csv'
snmi_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.snmi'
snmi_set_dict_file = '..\\Ontologies\\' + ONTO_NAME + '\\dicts\\dict.set_snmi'

snmi_med_index_start = 700000


if __name__ == '__main__':
    #  Build the SNMI DEF dict
    snmi_df = code_bioportal_df(snmi_codes_csv)
    snmi_dict = build_def_dict('SNMI', snmi_df, 'code', 'Preferred Label', snmi_med_index_start)
    snmi_dict_no_char = def_wo_chars('SNMI', snmi_dict, '-')
    snmi_dict = pd.concat([snmi_dict, snmi_dict_no_char]).sort_values(['mediald', 'desc'])

    snmi_dict.to_csv(snmi_dict_file, sep='\t', index=False, header=False)

    #  Build the SNMI SET dict

    #sets2_df = build_set_dict(snmi_dict, snmi_df, '-')
    sets2_df = build_set_dict(snmi_dict, snmi_df)
    sets2_df[['typ', 'outer_desc', 'inner_desc']].to_csv(snmi_set_dict_file, sep='\t', index=False, header=False)
