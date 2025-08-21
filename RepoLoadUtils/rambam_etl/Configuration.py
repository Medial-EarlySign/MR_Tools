import os


class Configuration:
    def __init__(self):
        self.repo = '/server/Work/CancerData/Repositories/THIN/rambam_nov2018_fixed/rambam.repository'
        
        if os.name =='nt':
            self.flow_app = r'\\nas1\UsersData\tamar\MR\Tools\Flow\x64\Release\Flow.exe'
        else:
            self.flow_app = '/server/UsersData/tamar/MR/Tools/Flow/Linux/Release/Flow'

        self.data_folder = 'T:\\RAMBAM\\'
        self.raw_source_path = self.data_folder + 'da_medial_patients'
        self.raw_source_path_add = 'T:\\Rambam19\\'
        self.work_path = 'W:\\Users\\Tamar\\rambam_load\\'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\rambam_etl'

        #self.output_path = 'X:\\Thin_2018_Loading\\outputs' # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.reg_list_path = 'H:\\MR\\Tools\\Registries\\Lists'
        self.prev_id2ind = 'W:\\CancerData\\Repositories\\Rambam\\rambam_nov2018_fixed\\ID2NR'
