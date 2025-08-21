import os
import pandas as pd
from Configuration import Configuration
from const_and_utils import read_fwf, write_tsv, eprint, fixOS, read_tsv, cat_to_name, special_codes, is_nan


def comp_from_demographic_file():
    cfg = Configuration()
    new_rep = fixOS(cfg.curr_repo)
    old_rep = fixOS(cfg.prev_repo)
    new_id2inr = os.path.join(new_rep, 'ID2NR')
    old_id2inr = os.path.join(old_rep, 'ID2NR')

    old_id2nr = pd.read_csv(old_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
    old_id2nr['prac'] = old_id2nr['combid'].str[:5]
    old_ids_by_file = old_id2nr['combid'].unique()
    old_prac_by_file = old_id2nr['prac'].unique()

    new_id2nr = pd.read_csv(new_id2inr, sep='\t', names=['combid', 'medialid'], dtype={'combid': str, 'medialid': int})
    new_id2nr['prac'] = new_id2nr['combid'].str[:5]
    new_ids_by_file = new_id2nr['combid'].unique()
    new_prac_by_file = new_id2nr['prac'].unique()

    new_pracs = list(set(new_prac_by_file) - set(old_prac_by_file))
    removed_pracs = list(set(old_prac_by_file) - set(new_prac_by_file))
    print(removed_pracs)
    both_pracs = list(set(old_prac_by_file) & set(new_prac_by_file))

    new_patients = list(set(new_ids_by_file) - set(old_ids_by_file))
    removed_patients = list(set(old_ids_by_file) - set(new_ids_by_file))

    new_patients_in_new_pracs = new_id2nr[new_id2nr['prac'].isin(new_pracs)]
    new_patients_in_old_pracs = new_id2nr[~new_id2nr['prac'].isin(new_pracs)]
    new_patients_in_old_pracs = new_patients_in_old_pracs[new_patients_in_old_pracs['combid'].isin(new_patients)]

    patients_in_removed_pracs = old_id2nr[old_id2nr['prac'].isin(removed_pracs)]
    removed_patients_in_old_pracs = old_id2nr[old_id2nr['prac'].isin(both_pracs)]
    removed_patients_in_old_pracs = removed_patients_in_old_pracs[removed_patients_in_old_pracs['combid'].isin(removed_patients)]

    print('Counts by demographic file:')
    print('===========================')
    print('Total patients 17: ' + str(len(old_ids_by_file)))
    print('Total patients 18: ' + str(len(new_ids_by_file)))

    print('Total practices 17: ' + str(len(old_prac_by_file)))
    print('Total practices 18 ' + str(len(new_prac_by_file)))

    print('Patients only 17: ' + str(len(removed_patients)))
    print('Patients only 18: ' + str(len(new_patients)))

    print('Practices only in 17: ' + str(len(removed_pracs)))
    print('Practices only in 18: ' + str(len(new_pracs)))

    print('New patients from new practices: ' + str(new_patients_in_new_pracs.shape[0]))
    print('New patients in old practices: ' + str(new_patients_in_old_pracs.shape[0]))
    print('Removed patients in removed practices ' + str(patients_in_removed_pracs.shape[0]))
    print('Removed patients in exist practices ' + str(removed_patients_in_old_pracs.shape[0]))

    index = ['Total patients', 'Total practices', 'Patients only in', 'Practices only',
             'patients in practices only in', 'patients only in (from practices in both)']
    comp_list = [{'17': len(old_ids_by_file), '18': len(new_ids_by_file)},
                 {'17': len(old_prac_by_file), '18': len(new_prac_by_file)},
                 {'17': len(removed_patients), '18': len(new_patients)},
                 {'17': len(removed_pracs), '18': len(new_pracs)},
                 {'17': patients_in_removed_pracs.shape[0], '18': new_patients_in_new_pracs.shape[0]},
                 {'17': removed_patients_in_old_pracs.shape[0], '18': new_patients_in_old_pracs.shape[0]}]

    comp_df = pd.DataFrame(data=comp_list, index=index)
    comp_df.to_csv('patients_and_prac_comp.csv')


if __name__ == '__main__':
    comp_from_demographic_file()


    cfg = Configuration()
    new_rep = fixOS(cfg.curr_repo)
    old_rep = fixOS(cfg.prev_repo)
    new_id2inr = os.path.join(new_rep, 'ID2NR')
    old_id2inr = os.path.join(old_rep, 'ID2NR')
    raw_new = fixOS(cfg.raw_source_path)
    raw_old = raw_new.replace('8', '7')

    old_file_names = list(filter(lambda f: f.startswith('patient.'), os.listdir(raw_old)))
    old_prac_by_raw = [x[-5:] for x in old_file_names]
    new_file_names = list(filter(lambda f: f.startswith('patient.'), os.listdir(raw_new)))
    new_prac_by_raw = [x[-5:] for x in new_file_names]

    print('prac only in 17: ' + str(len(set(old_prac_by_raw) - set(new_prac_by_raw))))
    print('prac only in 18: ' + str(len(set(new_prac_by_raw) - set(old_prac_by_raw))))

    print(set(old_prac_by_raw) - set(new_prac_by_raw))
