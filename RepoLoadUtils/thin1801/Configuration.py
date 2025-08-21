import os


class Configuration:
    def __init__(self):
        self.html_data_path = '\\\\nas3\\Work\\Graph_Infra'
        self.repo_folder = '/server/Work/CancerData/Repositories/THIN/thin_2018_2/'
        self.repo = self.repo_folder + 'thin.repository'
        self.fix_mean_threshold = 0.1
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\alon\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/alon/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\THIN1801\\'
        self.doc_source_path = self.data_folder + 'THINAncil1801\\text'
        self.raw_source_path = self.data_folder + 'THINDB1801'
        #self.raw_source_path = 'D:\\THINDB1801'
        self.patient_demo = self.data_folder + 'THINAncil1801\\Patient_Demography1801\\patient_demography.csv'
        self.work_path = 'X:\\Thin_2018_Loading'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\thin1801'

        self.output_path = 'X:\\Thin_2018_Loading\\outputs' # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.reg_list_path = 'H:\\MR\\Tools\\Registries\\Lists'
        self.curr_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2018\\'
        self.prev_repo = 'W:\\CancerData\\Repositories\THIN\\thin_jun2017\\'
        self.prev_id2ind = self.prev_repo + 'ID2NR'
