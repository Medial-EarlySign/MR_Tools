#!/bin/python
import sys, os, io
sys.path.append(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepoLoadUtils', 'thin_etl'))
from flow_api import getLines
from common import *
from Configuration import Configuration

def run_command_file(cmd, out_p):
    if os.path.exists(out_p):
        os.remove(out_p)
    p = subprocess.call(cmd, shell=True)
    if (p != 0 or not(os.path.exists(out_p))):
        print ('Error in running Command. CMD was:\n%s'%cmd)
        raise NameError('stop')

def load_hyper_reg():
    reg_creator_app = fixOS(os.path.join(os.environ['MR_ROOT'], 'Projects', 'Shared', 'CVA', 'checkThinData', 'Linux', 'Release', 'checkThinData'))
    reg_path_def = fixOS('/server/Work/Users/yaron/CVA/NewLists/hyper_tension.desc')
    cfg = Configuration()
    work_path =  fixOS(cfg.work_path)
    reg_path = os.path.join(work_path, 'registry')
    rep_path = os.path.join(work_path, 'repository_data_final/thin.repository')
    if not(os.path.exists(reg_path)):
        os.makedirs(reg_path)
    
    cmd = [reg_creator_app, '--mode', 'hyperTenstionRegistry', '--readCodesFile', reg_path_def, '--config', rep_path]
    full_cmd = ' '.join(cmd) + ' > %s 2> %s'%( os.path.join(reg_path, 'HT_Registry'), os.path.join(reg_path, 'hyperTenstionRegistry.stderr') )
    run_command_file(full_cmd, os.path.join(reg_path, 'HT_Registry'))
    
def load_diabetes_reg():
    print_app = fixOS(os.path.join(os.environ['MR_ROOT'], 'Tools', 'RepositoryUtilities', 'Linux', 'Release', 'print'))
    cfg = Configuration()
    work_path =  fixOS(cfg.work_path)
    out_path  = fixOS(cfg.output_path)
    reg_path = os.path.join(work_path, 'registry')
    diabetes_reg_path = fixOS('/nas1/Work/Users/Avi/Diabetes/canvas_pre2d/diabetes_fixed_part.txt') #TODO
    out_p = os.path.join(out_path, 'DM_Registry.init')
    p_script = os.path.join(os.environ['MR_ROOT'], 'Projects', 'Scripts', 'Perl-scripts', 'paste.pl')
    rep_path = os.path.join(work_path, 'repository_data_final/thin.repository')
    st_dates_path = os.path.join(out_path, 'all_start_dates')
    ed_dates_path = os.path.join(out_path, 'all_end_dates')
    if not(os.path.exists(st_dates_path)):
        cmd = '%s --config %s --signal STARTDATE > %s'%(print_app, rep_path, st_dates_path)
        run_command_file(cmd, st_dates_path)
    else:
        print('Skip creating Start_dates')
    if not(os.path.exists(ed_dates_path)):
        cmd = '%s --config %s --signal ENDDATE > %s'%(print_app, rep_path, ed_dates_path)
        run_command_file(cmd, ed_dates_path)
    else:
        print('Skip creating End_dates')
    
    cmd = """cat %s | perl -ne 'chomp; next unless (/^DRec/); """%(diabetes_reg_path) + \
    """/DRec:: id (\d+).*rc: H: (\d+) - (\d+) P: (\d+) - (\d+) D: (\d+) - (\d+) """ + \
    """:: ignore/ or die $_ ; my ($id,$hs,$he,$ps,$pe,$ds,$de)=($1,$2,$3,$4,$5,$6,$7);""" + \
    """ print "$id\tDM_Registry\t$hs\t$he\t0\n" if ($hs!=0); """ + \
    """ print "$id\tDM_Registry\t$ps\t$pe\t1\n" if ($ps!=0); """+ \
    """ print "$id\tDM_Registry\t$ds\t$de\t2\n" if ($ds!=0);' """ + \
    """ > %s"""%(out_p)

    run_command_file(cmd, out_p)
    step_1_path = os.path.join(out_path, 'DM_Registry.step1')
    cmd = """%s %s 0 %s 1 3 | sed 's/\.000000//' """%(p_script, out_p, st_dates_path) + \
          """ | perl -ne 'chomp; ($id,$n,$f,$t,$l,$s)=split; $f=$s if ($l==0 and $s<$f); """ + \
          """$o=join "\t",($id,$n,$f,$t,$l); print "$o\n"' > %s"""%(step_1_path)
    run_command_file(cmd, step_1_path)

    final_path = os.path.join(reg_path, 'DM_Registry')
    cmd = """%s %s 0 %s 1 3 | sed 's/\.000000//' """%(p_script, step_1_path, ed_dates_path) + \
          """| perl -ne 'chomp; ($id,$n,$f,$t,$l,$e)=split; $t=$e if ($l==2 and $e>$t); """ + \
          """ $o=join "\t",($id,$n,$f,$t,$l); print "$o\n"' > %s"""%(final_path)
    run_command_file(cmd, final_path)
    

if __name__ == "__main__":
    print('starting')
    load_hyper_reg()
    #load_diabetes_reg()
