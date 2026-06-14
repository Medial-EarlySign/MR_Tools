import pandas as pd
import os, subprocess
from .env import *
from .define_signals import load_signals_map

def _handle_mapping(df, sig_types, workdir, editor=None):
    #TODO: In the future might support use comma to specify to fetch the same source multiple time for different signals for processings.
    if 'signal' not in df.columns:
        print(df.head(), flush=True)
        print(list(df.columns), flush=True)
        raise NameError('Error, df has no column "signal", should also have "pid"')
    if 'pid' not in df.columns:
        print(df.head(), flush=True)
        print(list(df.columns), flush=True)
        print('Warning, df has no column "pid", it will be required in the next steps, please rename the right column in the input', flush=True)
    
    cfg_file=os.path.join(workdir, 'configs', 'map.tsv')
    mapper_file=None
    df['WAS_MAPPED']=0
    if os.path.exists(cfg_file):
        mapper_file=pd.read_csv(cfg_file, sep='\t')
        mapper_file=mapper_file[(mapper_file['destination'].notnull()) & (mapper_file['destination']!='')].reset_index(drop=True) #filter empty, non-mapped rows
        #do the join and rename signals:
        df=df.rename(columns={'signal':'source'}).set_index('source').join(mapper_file[['source', 'destination']].rename(columns={'destination':'signal'}).set_index('source'), how='left').reset_index()
        df.loc[ df['signal'].notnull(),'WAS_MAPPED']=1
        df.loc[df['signal'].isnull(), 'signal']= df.loc[df['signal'].isnull(), 'source']
        #df=df.drop(columns=['source'])
        df=df.rename(columns={'source' : 'original_signal_source'})
        
    df_test=df[df['signal'].notnull()].reset_index(drop=True)[['signal', 'WAS_MAPPED']].copy()
    if len(df_test)==0:
        return df, False
    sigs=pd.DataFrame({'signal':list(sig_types.keys())} )
    sigs['exists']=1
    df_test=df_test.set_index('signal').join(sigs.set_index('signal'), how='left').reset_index()
    df_test.loc[df_test['exists'].isnull(), 'exists'] = 0
    
    global_stats=df_test.drop_duplicates().copy()
    unmmapped=len(global_stats[global_stats['exists']<1])
    mapped=len(global_stats[global_stats['exists']>0])
    os.makedirs(os.path.join(workdir, 'configs'), exist_ok=True)
    
    have_missings=False
    if unmmapped>0:
        tot_miss=len(df_test[df_test['exists']<1])
        print('There are %d unmapped signals with total %s missings records and %d mapped/recognized signals.'%(unmmapped, tot_miss, mapped), flush=True)
        #Test if there are unkown mapped signals!
        bad_maps_maybe=list(global_stats[(global_stats['exists']<1) & (global_stats['WAS_MAPPED']>0)]['signal'].values)
        if len(bad_maps_maybe)>0:
            print('There are not existing mapping in your file, please define more signals in %s, or change those mappings'%(os.path.join(workdir,'configs' ,'rep.signals')), flush=True)
            rank_missings=df_test[(df_test['exists']<1) & (df_test['WAS_MAPPED']>0)][['signal', 'exists']].groupby('signal').count().reset_index().rename(columns={'exists': 'count'}).sort_values(['count'],ascending=False).reset_index(drop=True)
            print('Missing maps:\n%s'%(rank_missings), flush=True)
        #Generate mapper config file with counts, 3 columns "source", "destination", "count" to be completed by user (only for unmpapped items):
        stats=df_test[df_test['WAS_MAPPED']<1][['signal', 'exists']].groupby('signal').count().reset_index().rename(columns={'exists': 'count', 'signal': 'source'}).sort_values('count', ascending=False).reset_index(drop=True)
        
        #fix and merge with mapper_file.
        stats['destination']='' #Default is empty
        if mapper_file is not None: #merge with existing config:
            stats = pd.concat([mapper_file, stats], ignore_index=True).sort_values('count', ascending=False).reset_index(drop=True)
        
        stats.to_csv(cfg_file, sep='\t', index=False)
        #Now let's edit:
        #print('Please edit map file in %s'%(cfg_file))
        if editor is not None:
            proc=subprocess.Popen([editor, cfg_file], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc.wait()
        have_missings=True
        
    df=df.drop(columns=['WAS_MAPPED'])
    return df, have_missings

def handle_mapping(df, sig_types, workdir, interactive=True, editor=None):
    signal_defs=os.path.join(workdir,'configs' ,'rep.signals')
    signal_maps=os.path.join(workdir, 'configs', 'map.tsv')
    os.makedirs(workdir, exist_ok=True)
    os.makedirs(os.path.join(workdir, 'configs'), exist_ok=True)
    if not(interactive):
        editor=None
    
    if not(os.path.exists(signal_defs)):
        fr=open(FULL_SIGNALS_TYPES, 'r')
        lines=fr.readlines()
        fr.close()
        lines=list(map(lambda x: x.strip(),lines))
        lines=list(filter(lambda x: x.startswith('GENERIC_SIGNAL_TYPE'),lines))
        #Generare template from generic: - add comments
        lines.append('\n# This file was created based on generic file %s'%(FULL_SIGNALS_TYPES))
        lines.append('# This files adds definitions to specific signals that you only want to use in this repository, otherwise please define the signals in the generic file path above')
        lines.append('# File format is the same as repository signals files - can be used later to create repository after join with generic file\n')
        lines.append('# SIGNAL [TAB] $SIGNAL_NAME [TAB] $UNIQUE_NUMERIC_IDENTIFIER_FOR_YOUR_CHOISE [TAB] 16:$SIGNAL_TYPE [TAB] $SIGNAL_HIRARCHY [TAB] $IS_VALUE_CHANNELS_CATEGORICAL [TAB] $UNIT_IF_HAS')
        lines.append('# $SIGNAL_HIRARCHY - is comma seperated to define hirarchy for the signal processing, $IS_VALUE_CHANNELS_CATEGORICAL - is string with 0/1 chars for each value channel, $UNIT_IF_HAS - for each channel separated by |')
        lines.append('\n# Example:')
        lines.append('#SIGNAL\tHemoglobin\t1000\t16:my_SDateVal\tlabs,cbc\t0\tmg/dL')
        
        fw=open(signal_defs, 'w')
        fw.writelines(map(lambda x:x + '\n',lines))
        fw.close()
    print('File location for adding and defining more signals: %s'%(signal_defs), flush=True)
    signals_cnt=len(set(df[df['signal'].notnull()]['signal'].values))
    if signals_cnt==0:
        return df
    print('File location for mapping signals: %s'%(signal_maps), flush=True)
    df, have_missings = _handle_mapping(df, sig_types, workdir, editor)
    if interactive:
        legit_res=set({'N', 'NO', 'Y', 'YES'})
        while have_missings:
            print('File location for adding and defining more signals: %s'%(signal_defs), flush=True)
            print('File location for mapping signals: %s'%(signal_maps), flush=True)
            res=input('We have missings mappings, do you want to rerun after editing the 2 files above? Y/N? ').upper()
            while res not in legit_res:
                res=input('We have missings mappings, do you want to rerun after editing the 2 files above? Y/N? ').upper()
            if res=='N' or res=='NO':
                break
            elif res =='Y' or res == 'YES':
                sig_types = load_signals_map(FULL_SIGNALS_TYPES, workdir) #reread again
                df, have_missings = _handle_mapping(df, sig_types, workdir, editor)
    return df
