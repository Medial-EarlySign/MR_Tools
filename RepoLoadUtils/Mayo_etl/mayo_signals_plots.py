import pandas as pd
import os
import sys
sys.path.append(os.path.join('/nas1/UsersData/tamard/MR', 'Tools', 'RepoLoadUtils', 'common'))
from Configuration import Configuration
from utils import fixOS
from signals_plots import numeric_plots, category_plots
sys.path.append('/nas1/UsersData/tamard/MR/Libs/Internal/MedPyExport/generate_binding/CMakeBuild/Linux/Release/MedPython')
import medpython as med


if __name__ == '__main__':
    cfg = Configuration()
    #code_folder = fixOS(cfg.code_folder)
    code_folder = '/nas1/UsersData/tamard/MR/Tools/RepoLoadUtils/Mayo_etl'
    out_folder = os.path.join(fixOS(cfg.work_path), 'plots')
    kp_rep = fixOS(cfg.repo)
    full_map_file = os.path.join(code_folder, 'mayo_signal_map.csv')
    map_df = pd.read_csv(full_map_file, sep='\t')
    rep = med.PidRepository()

    map_numeric = map_df[(map_df['type'] == 'numeric') & (map_df['source'].str.contains('mayolabs'))]
    numeric_signals = map_numeric['signal'].unique().tolist()
    print(numeric_signals)
    rep.read_all(kp_rep, [], numeric_signals)
    print(med.cerr())
    numeric_plots(rep, numeric_signals, code_folder, out_folder)

    #kp_map_cat = map_df[(map_df['type'] == 'string')]
    #cat_signals = kp_map_cat['signal'].unique().tolist()
    #print(len(cat_signals))
    #rep.read_all(kp_rep, [], cat_signals)
    #rint(med.cerr())
    #category_plots(rep, cat_signals, out_folder)

    cat_signals2 = ['Colon_Cancer', 'GI_Bleed']
    rep.read_all(kp_rep, [], cat_signals2)
    print(med.cerr())
    category_plots(rep, cat_signals2, out_folder)
