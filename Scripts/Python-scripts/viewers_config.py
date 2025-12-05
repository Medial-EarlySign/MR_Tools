#!/usr/bin/env python
import os

class ViewerCfg:
    def __init__(self, rep_path, port, log_error_file, config_path = None, index_page = None, java_script_dir = None):
        self.rep_path = rep_path
        self.port = port
        self.config_path= config_path
        self.index_page = index_page
        self.java_script_dir = java_script_dir
        self.log_error_file = log_error_file
        if self.java_script_dir is None:
            if 'MR_ROOT' not in os.environ:
                raise NameError('MR_ROOT is not defined in the environment')
            self.java_script_dir = os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'JavaScript')
        if self.config_path is None:
            if 'MR_ROOT' not in os.environ:
                raise NameError('MR_ROOT is not defined in the environment')
            self.config_path = os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'BasicConfig.txt')
        self.up_time = None
        self.start_cnt=0
        self.process=None
        self.last_error = None

class FullCfg:
    def __init__(self):
        self.sleep_interval = 30
        self.server_app = None #Default None - path to run SimpleHttpViewer from AllTools
        self.server_address = None #Default - checks server IP address
        self.html_index_template = None #Defualt None - gets from templates
        self.javascript_dir = None #Default None - gets from MR_ROOT
        self.log_error_folder='/nas1/Work/CancerData/Repositories/viewers_log'
        self.server_name = None #Default - fetch server name from socket
        self.index_port=8000
        
        self.all_viewers = []
        #############################################VIEWERS DEFINITIONS#####################################
        #THIN
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/THIN/thin_2021/thin.repository', 8194, os.path.join(self.log_error_folder, 'thin.log'), os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'BasicConfig.no_eGFR.txt')))
        #THIN2017
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/THIN/thin_jun2017/thin.repository', 8222, os.path.join(self.log_error_folder, 'thin_2017.log')))
        #self.all_viewers.append(ViewerCfg('/home/Repositories/THIN/thin_2020/thin.repository', 8206, os.path.join(self.log_error_folder, 'thin.log')))
        #self.all_viewers.append(ViewerCfg('/home/Repositories/THIN/thin_2018/thin.repository', 8204, os.path.join(self.log_error_folder, 'thin.2018.log')))
        #MHS:
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/Mode3/Maccabi_feb2016/maccabi.repository', 8195, os.path.join(self.log_error_folder, 'mhs.log'),
            os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'MHSConfig.txt'), 'formMHS.html'))
        #KPNW:
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/KPNW/kpnw_nov20/kpnw.repository', 8200, os.path.join(self.log_error_folder, 'kpnw.log'),
            os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'KPNWConfig.txt'), 'formKPNW.html'))
        #KPNW_DIABETES:
        #self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/KPNW/kpnw_diabetes/kpnw.repository', 8201, os.path.join(self.log_error_folder, 'kpnw_dm.log'),
        #    os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'KPNWConfig_DM.txt'), 'formKPNW_D.html'))
        #KP:
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/KP/kp.repository', 8196, os.path.join(self.log_error_folder, 'kp.log'),
            os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'KPConfig.txt')))
        #RAMBAM
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/Rambam/rambam_nov2018_fixed/rambam.repository', 8198, 
            os.path.join(self.log_error_folder, 'rambam.log'), os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'RambamConfig.txt')))
        #MIMIC
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/MIMIC/Mimic3/mimic3.repository', 8199, os.path.join(self.log_error_folder, 'mimic.log'),
            os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'MimicConfig.txt')))
        #SLU
        self.all_viewers.append(ViewerCfg('/nas1/Work/Users/Avi/SLU/repository3/slu.repository', 8193, os.path.join(self.log_error_folder, 'SLU.log'),
            os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'SLUConfig.txt')))
        #KPNW jun:
        self.all_viewers.append(ViewerCfg('/nas1/Work/CancerData/Repositories/KPNW/kpnw_jun19/kpnw.repository', 8202, os.path.join(self.log_error_folder, 'kpnw.jun.log'),
            os.path.join(os.environ['MR_ROOT'], 'Libs', 'Internal', 'MedPlotly', 'MedPlotly', 'KPNWConfig.txt'), 'formKPNW.html'))
        ##############################################END####################################################
    

    
    
        
        
