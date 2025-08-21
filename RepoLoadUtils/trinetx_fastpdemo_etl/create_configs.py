import os
import pandas as pd
import numpy as np
from Configuration import Configuration
import re
from shutil import copyfile


if __name__ == '__main__':

    """
       *    Copy trinetX.signals 
            from 
            /nas1/UsersData/Ilya/MR/Tools/RepoLoadUtils/trinetx_fastpdemo_etl/trinetX.signals
            to 
            /nas1/Work/Users/ilya/Trinetx/rep_config/trinetX.signals 
            
    *       Load a configuration template 
            from 
            /nas1/UsersData/Ilya/MR/Tools/RepoLoadUtils/trinetx_fastpdemo_etl/trinetX.convert_config
            
            add
            
            DIR /nas1/Work/Users/ilya/Trinetx/rep_config/
            OUTDIR  /server/Work/Repositories/TrinetX_fastpdemo/ 
            
    *       Dictionaries
    
            For each dictionary 
            from /nas1/Work/Users/ilya/Trinetx/rep_config/dicts
            create a line
            DICTIONARY full_path 
    
    *       DATA FILES
    
                    
    """

    # load configuration, set paths
    cfg = Configuration()
    final_signals_path  = os.path.join(cfg.work_path,'FinalSignals')
    rep_config_path     = os.path.join(cfg.work_path,'rep_config')
    dict_path           = os.path.join(rep_config_path,'dicts')

    # Copy signals file
    src = os.path.join(cfg.code_path,'trinetX.signals')
    dst = os.path.join(rep_config_path,'trinetX.signals')
    print(f'Copying signals file from {src} to {dst}')
    copyfile(src,dst)

    # Read signals
    signals = []
    with open(dst,'r') as file:
        for line in file:
            fields = line.rstrip('\r\n').split('\t')
            if (fields[0] == 'SIGNAL'):
                signals.append(fields[1])
    print(f'Read {len(signals)} signal from {dst}')

    # Load the template configuration
    in_config_file = os.path.join(cfg.code_path, 'trinetX.convert_config')
    lines = []
    with open(in_config_file,'r') as file:
        for line in file:
            lines.append(line)
    print(f'Loading template configuration from {in_config_file}')

    # Create convert config

    config_file = os.path.join(rep_config_path,'trinetX.convert_config')
    print(f'Creating configuration at {config_file}')
    with open(config_file,'w') as file:

        # Initialize with rows from a template
        for line in lines:
            file.write(line)
        file.write(f'DIR\t{rep_config_path}\n')
        file.write(f'OUTDIR\t{cfg.repo_folder}\n')

        # COPY DICTIONARIES
        dicts = [file for file in os.listdir(dict_path) if re.search("^dict\.", file)]
        for dict in dicts:
            full_path = os.path.join(dict_path,dict)
            file.write(f'DICTIONARY\t{full_path}\n')

        # COPY DATA FILES
        data_files = os.listdir(final_signals_path)
        for signal in signals:
            signal = signal.replace('+', '\+')
            regex = re.compile('^({})(\d*)$'.format(signal))
            signal_files = [file for file in data_files if re.match(regex,file)]
            if (len(signal_files)==0):
                raise ValueError(f'Cannot find files for {signal} in {final_signals_path}')
            for signal_file in signal_files:
                full_path = os.path.join(final_signals_path, signal_file)
                file.write(f'DATA\t{full_path}\n')
