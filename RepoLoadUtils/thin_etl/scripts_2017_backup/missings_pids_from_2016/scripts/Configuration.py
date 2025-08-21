import os

class Configuration:
    def __init__(self):
        self.html_data_path = '\\\\nas3\\Work\\Graph_Infra'
        #self.maccabi_repo = '/server/Work/CancerData/Repositories/Mode3/Maccabi_feb2016/maccabi.repository'
        self.maccabi_repo = '/home/Repositories/THIN/thin_mar2017/thin.repository'
        self.fix_mean_threshold = 0.11
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\alon\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/alon/MR/Tools/Flow/Linux/Release/Flow'

        self.doc_source_path = '/server/Data/THIN1601/THINAncil1601/text'
        self.raw_source_path = '/server/Temp/Thin_2017_Loading/missing_pids_from_2016/data'
        self.patient_demo = '/server/Data/THIN1601/PatientDemography1601/patient_demography.csv'
        self.work_path = '/server/Temp/Thin_2017_Loading/missing_pids_from_2016'
        #self.work_path = r'W:\Users\Alon'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\thin_etl\\configs\\config_2017'

        self.output_path = '/server/Temp/Thin_2017_Loading/missing_pids_from_2016/outputs' # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
