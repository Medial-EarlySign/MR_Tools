import os
import sys
work_dir = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(work_dir), '..','RepoLoadUtils/thin_etl')))

class Configuration:
    def __init__(self):
        #self.doc_source_path = '/server/Data/THIN1701/THINAncil1701/text'
        self.doc_source_path = '/server/Data/THIN1601/THINAncil1601/text'        
        #self.raw_source_path = '/server/Data/THIN1701/THINDB1701'
        self.raw_source_path = '/server/Temp/Thin_2017_Loading/missing_pids_from_2016/data'
        
        #self.work_path = '/server/Temp/Thin_2017_Loading'      
        self.work_path = '/server/Temp/Thin_2017_Loading/missing_pids_from_2016'
        
        self.config_lists_folder = os.path.join(os.path.dirname(work_dir), 'Lists/')
        
        
        
        