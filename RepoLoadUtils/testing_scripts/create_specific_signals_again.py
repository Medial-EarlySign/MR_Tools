#!/nas1/Work/python-env/python38/bin/python
import os, sys
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'common'))

from utils import fixOS, read_tsv
from staging_config import ThinLabs
from stage_to_signals import numeric_to_files

import pandas as pd

def recalc_values(sigs):
    cfg=Configuration()
    db_cfg=ThinLabs()

    special_cases = ['CHADS2', 'CHADS2_VASC']
    code_folder = fixOS(cfg.code_folder)
    work_folder = fixOS(cfg.work_path)
    print('config folder : %s'%(code_folder))
    out_folder = os.path.join(work_folder, 'FinalSignals')
    all_files=os.listdir(out_folder)
    all_sigs_files=[]
    for sig in sigs:
        all_sigs_files += list(filter(lambda x: x.startswith('%s_thinlabs_'%(sig)) ,all_files))
    for f in all_sigs_files:
        full_f = os.path.join(out_folder,f)
        print('Remove %s to rewrite it'%(full_f))
        os.remove(full_f)

    th_map = pd.read_csv(os.path.join(code_folder, 'thin_signal_mapping.csv'), sep='\t')
    lab_chart_cond = (th_map['source'] == db_cfg.TABLE)
    th_map_numeric = th_map[(th_map['type'] == 'numeric') & lab_chart_cond & ~(th_map['signal'].isin(special_cases))]
    th_map_numeric = th_map_numeric[th_map_numeric['signal'] != 'STOPPED_SMOKING']
    unit_mult = read_tsv('unitTranslator.txt', code_folder,
                    names=['signal', 'unit', 'mult', 'add', 'rnd', 'rndf'], header=0)
    id2nr = get_id2nr_map()
    th_map_numeric= th_map_numeric[th_map_numeric['signal'].isin(sigs)]
    special_factors_signals = pd.read_csv(os.path.join(code_folder, 'mixture_units_cfg.txt'), sep='\t')
    numeric_to_files(db_cfg, th_map_numeric, unit_mult, special_factors_signals, id2nr, out_folder, suff='_'+db_cfg.TABLE+'_', main_cond = 'code')

if __name__ == '__main__':
    config_path=os.path.join(os.environ['MR_ROOT'],'Tools', 'RepoLoadUtils', 'thin21_etl')
    sys.path.append(config_path)
    from Configuration import Configuration
    from generate_id2nr import get_id2nr_map
    
    print('Ran from folder %s'%(config_path))
    sigs=[ 'VitaminD2', 'PFR','Uric_Acid', 'Cortisol','TroponinI','Testosterone','VitaminD_25','Cholesterol','Triglycerides','TIBC']
    #Recalc again
    recalc_values(sigs)
