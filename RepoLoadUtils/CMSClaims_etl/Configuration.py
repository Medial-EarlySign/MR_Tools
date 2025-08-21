import os


class Configuration:
    def __init__(self):
        self.repo_folder = '/server/Work/CancerData/Repositories/CMS/cms_synthetic/'
        self.repo = os.path.join(self.repo_folder, 'cms.repository')

        self.cms_folder = 'W:\\Data\\CMSClaims\\'
        self.data_folder = os.path.join(self.cms_folder, 'data')
        self.data_external = os.path.join(self.cms_folder, 'External')
        self.work_path = 'W:\\Users\\Tamar\\cms_load\\'
        self.code_folder = 'H:\\MR\\Tools\\RepoLoadUtils\\CMSClaims_etl'

        self.output_path = os.path.join(self.work_path, 'outputs') # path to output graphs and information abput signals. in linux it's mapped automaticaly "C:\\Users\\Alon" is replaced by "~\"
        self.ontology_folder = 'H:\\MR\\Tools\\DictUtils\\Ontologies'
