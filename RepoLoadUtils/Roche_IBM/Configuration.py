import os


class Configuration:
    def __init__(self):
        #self.repo_folder = '/server/Work/CancerData/Repositories/THIN/thin_2021/'
        #self.repo = os.path.join(self.repo_folder, 'thin.repository')

        self.flow_app = '/medial/bin/Flow'

        self.data_dir='/mnt/s3mnt_pt'
        self.work_dir='/mnt/work/LGI/loading_files'
        self.code_dir='/mnt/work/LGI/etl'
        self.dict_folder=os.path.join(self.code_dir, 'configs', 'dicts')
        #self.data_folder = 'T:\THIN2101'
        #self.doc_source_path = self.data_folder + '\\IMRD Ancil TEXT\\text'
        #self.patient_source_path = self.data_folder + '\\IMRD Ancil TEXT\\Patient_Demography2101'
        #self.raw_source_path = self.data_folder + '\\THINDB2101'
        # self.raw_source_path = 'D:\\THINDB1801'
        #self.patient_demo = self.data_folder + '\\IMRD Ancil TEXT\\Patient_Demography2101\\patient_demography.csv'
        #self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\thin20_etl'
        #self.code_folder = os.path.join(os.environ['MR_ROOT'],'Tools','RepoLoadUtils','thin21_etl')
        self.output_path = os.path.join(self.work_dir,
                                        'outputs')  # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        #self.curr_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2021\\'
        #self.prev_repo = 'W:\\CancerData\\Repositories\THIN\\thin_2020\\'
        #self.prev_id2ind = self.prev_repo + 'ID2NR'
        self.repo_folder = '/mnt/work/Repositories/IBM'
