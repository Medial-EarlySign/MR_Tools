class StageConfig(object):
    DBTYPE = 'D6_POSTGRESSQL'
    username = 'postgres'
    password=''


class StageLabs(StageConfig):
    COLUMNS = ['orig_pid', 'code', 'description', 'value', 'value2', 'unit', 'date1', 'date2', 'source']
    COL_TYPES = ['INT', 'VARCHAR(100)', 'VARCHAR(500)', 'VARCHAR(200)', 'VARCHAR(200)', 'VARCHAR(200)', 'TIMESTAMP(0)', 'TIMESTAMP(0)', 'VARCHAR(50)']


class StageDemographic(StageConfig):
    COLUMNS = ['orig_pid', 'code', 'description', 'value', 'date1', 'source']
    COL_TYPES = ['INT', 'VARCHAR(50)', 'VARCHAR(500)', 'VARCHAR(500)', 'TIMESTAMP(0)', 'VARCHAR(50)']


class MimicLabs(StageLabs):
    DBTYPE = 'D6_POSTGRESSQL_SHULA'
    DBNAME = 'MimicStage'
    TABLE = 'mimiclabs'
    SPECIAL_CASES = ['I_E_Ratio']


class MimicDemographic(StageDemographic):
    DBTYPE = 'D6_POSTGRESSQL_SHULA'
    DBNAME = 'MimicStage'
    TABLE = 'mimicdemographic'
    SPECIAL_CASES = ['BYEAR', 'BDATE']


class ThinLabs(StageLabs):
    #DBTYPE = 'D6_POSTGRESSQL_SHULA'
    DBTYPE = 'D6_POSTGRESSQL'
    COL_TYPES = ['VARCHAR(20)', 'VARCHAR(20)', 'VARCHAR(500)', 'VARCHAR(200)', 'VARCHAR(200)', 'VARCHAR(200)', 'TIMESTAMP(0)',
                 'TIMESTAMP(0)', 'VARCHAR(50)']
    DBNAME = 'Thin21Stage'
    TABLE = 'thinlabs'
    SPECIAL_CASES = ['BP', 'Alcohol_quantity', 'Smoking_quantity', 'SMOKING', 'ALCOHOL', 'STOPPED_SMOKING', 'Labs', 'Child_development']


class ThinLabsCat(ThinLabs):
    TABLE = 'thinlabscats'


class ThinReadcodes(ThinLabs):
    TABLE = 'thinreadcodes'


class ThinDemographic(StageDemographic):
    #DBTYPE = 'D6_POSTGRESSQL_SHULA'
    DBTYPE = 'D6_POSTGRESSQL'
    COL_TYPES = ['VARCHAR(20)', 'VARCHAR(50)', 'VARCHAR(500)', 'VARCHAR(500)', 'TIMESTAMP(0)', 'VARCHAR(50)']
    DBNAME = 'Thin21Stage'
    TABLE = 'thindemographic'
    SPECIAL_CASES = ['Censor', 'PRAC', 'BYEAR', 'STARTDATE', 'ENDDATE', 'DEATH']


class JilinLabs(StageLabs):
    DBNAME = 'JilinStage'
    TABLE = 'jilinlabs'
    SPECIAL_CASES = []


class JilinDemographic(StageDemographic):
    DBNAME = 'JilinStage'
    TABLE = 'jilindemographic'
    SPECIAL_CASES = ['GENDER', 'BYEAR']


class KPNWLabs(StageLabs):
    DBTYPE = 'POSTGRESSQL'
    DBNAME = 'KPNWStage'
    TABLE = 'kpnwlabs'
    SPECIAL_CASES = []


class KPNWLabs2(KPNWLabs):
    TABLE = 'kpnwlabs2'


class KPNWVitals(KPNWLabs):
    TABLE = 'kpnwvitals'
    SPECIAL_CASES = ['BP', 'Height']


class KPNWDemographic(StageDemographic):
    DBTYPE = 'POSTGRESSQL'
    DBNAME = 'KPNWStage'
    TABLE = 'kpnwdemographic'
    SPECIAL_CASES = ['GENDER', 'DEATH']


class MayoLabs(StageLabs):
    DBTYPE = 'POSTGRESSQL'
    DBNAME = 'MayoStage'
    TABLE = 'mayolabs'
    SPECIAL_CASES = []


class MayoDemographic(StageDemographic):
    DBTYPE = 'POSTGRESSQL'
    DBNAME = 'MayoStage'
    TABLE = 'mayodemographic'
    SPECIAL_CASES = ['BYEAR', 'BDATE', 'GENDER']
