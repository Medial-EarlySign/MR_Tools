import pandas as pd
import os
import sys

fwf_formats = {
    'AHDCodes': {'datafile': (1, 8),
                 'ahdcode': (9, 18),
                 'description': (19, 118),
                 'data1': (119, 148),
                 'data2': (149, 178),
                 'data3': (179, 208),
                 'data4': (209, 238),
                 'data5': (239, 268),
                 'data6': (269, 298)},
    'Readcodes': {'medcode': (1, 7),
                  'description': (8, 67)},
    'THINprac': {'prac': (1, 5),
                 'compdate': (6, 15),
                 'visiondate': (16, 25),
                 'amr': (26, 35),
                 'collectdate': (36, 45),
                 'country': (46, 46),
                 'dataflag': (47, 48),
                 'description': (49, 303),
                 'status': (304, 304)},
    'AHDlookups': {'dataname': (1, 8),
                   'datadesc': (9, 38),
                   'lookup': (39, 44),
                   'lookupdesc': (45, 144)},
    'Drugcodes': {'drugcode': (1, 8),
                  'bnfcode1': (9, 19),
                  'bnfcode2': (20, 30),
                  'bnfcode3': (31, 41),
                  'genericname': (42, 161),
                  'formulation': (162, 211),
                  'strength': (212, 261),
                  'units': (262, 311),
                  'status': (312, 312),
                  'hospitalonly': (313, 313),
                  'nhsflag': (314, 314),
                  'atc': (315, 322)},
    'ATCTerms': {'ATC': (1, 8),
                 'Term': (9, 264)},
    'BNFcode': {'bnfcode': (1, 11),
                'description': (12, 111)},
    'Pack': {'drugcode': (1, 8),
             'genericname': (9, 128),
             'pack': (129, 131),
             'packunit': (132, 151),
             'packsize': (152, 158),
             'status': (159, 159),
             'legaltext': (160, 189),
             'divisible': (190, 190)},
    'Packsize': {'packsize': (1, 7),
                 'description': (8, 107)},
    'Dosage': {'doscode': (1, 7),
               'dosgval': (8, 14),
               'description': (15, 269)},
    'NHSspeciality': {'nhsspec': (1, 3),
                     'speciality': (4, 33),
                     'subspec': (34, 83)},
    'patient': {'patid': (1, 4),
                'patflag': (5, 5),
                'yob': (6, 13),
                'famnum': (14, 19),
                'sex': (20, 20),
                'regdate': (21, 28),
                'regstat': (29, 30),
                'xferdate': (31, 38),
                'regrea': (39, 40),
                'deathdate': (41, 48),
                'deathinfo': (49, 49),
                'accept': (50, 50),
                'institute': (51, 51),
                'marital': (52, 53),
                'dispensing': (54, 54),
                'prscexempt': (55, 56),
                'sysdate': (57, 65)},
    'ahd': {'patid': (1, 4),
            'eventdate': (5, 12),
            'ahdcode': (13, 22),
            'ahdflag': (23, 23),
            'data1': (24, 36),
            'data2': (37, 49),
            'data3': (50, 62),
            'data4': (63, 75),
            'data5': (76, 88),
            'data6': (89, 101),
            'medcode': (102, 108),
            'source': (109, 109),
            'nhsspec': (110, 112),
            'locate': (113, 114),
            'staffid': (115, 118),
            'textid': (119, 125),
            'category': (126, 126),
            'ahdinfo': (127, 127),
            'inprac': (128, 128),
            'private': (129, 129),
            'ahdid': (130, 133),
            'consultid': (134, 137),
            'sysdate': (138, 145),
            'modified': (146, 146)},
    'medical': {'patid': (1, 4),
                'eventdate': (5, 12),
                'enddate': (13, 20),
                'datatype': (21, 22),
                'medcode': (23, 29),
                'medflag': (30, 30),
                'staffid': (31, 34),
                'source': (35, 35),
                'episode': (36, 36),
                'nhsspec': (37, 39),
                'locate': (40, 41),
                'textid': (42, 48),
                'category': (49, 49),
                'priority': (50, 50),
                'medinfo': (51, 51),
                'inprac': (52, 52),
                'private': (53, 53),
                'medid': (54, 57),
                'consultid': (58, 61),
                'sysdate': (62, 69),
                'modified': (70, 70)},
    'therapy': {'patid': (1, 4),
                'prscdate': (5, 12),
                'drugcode': (13, 20),
                'therflag': (21, 21),
                'doscode': (22, 28),
                'prscqty': (29, 36),
                'prscdays': (37, 39),
                'private': (40, 40),
                'staffid': (41, 44),
                'prsctype': (45, 45),
                'opno': (46, 53),
                'bnf': (54, 61),
                'seqnoiss': (62, 65),
                'maxnoiss': (66, 69),
                'packsize': (70, 76),
                'dosgval': (77, 83),
                'locate': (84, 85),
                'drugsource': (86, 86),
                'inprac': (87, 87),
                'therid': (88, 91),
                'consultid': (92, 95),
                'sysdate': (96, 103),
                'modified': (104, 104)},
    'MedicalReadcodeFrequency': {'medcode': (1, 7),
                                     'description':	(8, 67),
                                     'freq': (68, 77)},
    'AHDReadcodeFrequency': {'medcode': (1, 7),
                             'description':	(8, 67),
                             'freq': (68, 77)},
    'DrugcodeFrequency': {'drugcode': (1, 8),
                          'description':	(9, 128),
                          'freq': (129, 138)}
}

special_codes = {'BP': '1005010500',
                 'Weight': '1005010200',
                 'BMI': '1005010200',
                 'Height': '1005010100',
                 'SMOKING': '1003040000',
                 'STOPPED_SMOKING': '1003040000',
                 'ALCOHOL': '1003050000',
                 'PULSE': '1009300000'}

rc_map = {"RC_Demographic": "0",
          "RC_History": "12R",
          "RC_Diagnostic_Procedures": "34",
          "RC_Radiology": "5",
          "RC_Procedures": "678Z",
          "RC_Admin": "9",
          "RC_Diagnosis": "ABCDEFGHJKLMNPQ",
          "RC_Injuries": "STU"}


cat_to_name = {
    'INPATIENT': 'gaZVSGHAD',
    'OUTPATIENT': 'CERIKPY1',
    'DAY_CASE': 'BWbkp'
}


def read_fwf(file_type, raw_path, file_name_pref=None):
    if not file_name_pref:
        file_name_pref = file_type
    file_name = list(filter(lambda f: f.upper().startswith(file_name_pref.upper()), os.listdir(raw_path)))
    if len(file_name) != 1:
        raise NameError('coudn''t find ' + file_name_pref)
    file_name = file_name[0]
    file_full_name = os.path.join(raw_path, file_name)

    field_dict = fwf_formats[file_type]
    colspecs = [(x[0]-1, x[1]) for x in field_dict.values()]
    names = field_dict.keys()
    df = pd.read_fwf(file_full_name, colspecs=colspecs, names=names) # , dtype=str)
    return df


def read_tsv(file_name, path, names=None, header=1, dtype=None):
    full_file = os.path.join(path, file_name)
    df = pd.read_csv(full_file, sep='\t', names=names, header=header, dtype=dtype)
    return df


def write_tsv(df, path, file_name, headers=False):
    if not(os.path.exists(path)):
        os.makedirs(path)
    full_file = os.path.join(path, file_name)
    df.to_csv(full_file, sep='\t', index=False, header=headers, mode='a', line_terminator='\n')


def write_tsv_fd(fd, df, path, file_name, headers=False):
    if not(os.path.exists(path)):
        os.makedirs(path)
    full_file = os.path.join(path, file_name)
    if fd is None:
        fd = open(full_file, mode='a', newline='\n')
    df.to_csv(fd, sep='\t', index=False, header=headers, mode='a', line_terminator='\n')
    return fd


def add_fisrt_line(first_line, file):
    with open(file, "r+", encoding="utf8", newline='\n') as f:
        a = f.read()
    with open(file, "w+", encoding="utf8", newline='\n') as f:
        f.write(first_line + a)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


# def get_user():
#     userName = os.environ.get('USERNAME')
#     if userName is None:
#         userName = os.environ.get('USER')
#     return userName

def get_user():
    user_name = os.environ.get('USERNAME')
    if user_name is None:
        user_name = os.environ.get('USER')
        if 'internal' in user_name:
            user_name = user_name.split('-')[0]
    return user_name

def fixOS(pt):
    isUnixPath = pt.find('\\') == -1
    if ((os.name != 'nt' and isUnixPath) or (os.name == 'nt' and not(isUnixPath))):
        return pt
    elif (os.name == 'nt'):
        res = 'C:\\USERS\\' + get_user()
        if (pt.startswith('/nas1') or pt.startswith('/server')):
            res = '\\\\nas3'
            pt = pt.replace('/nas1', '').replace('/server', '')
        pt = pt.replace('/', '\\')
        res= res + pt
        return res
    else:
        res = ''
        if pt.startswith('\\\\nas1') or pt.startswith('\\\\nas3') :
            res = '/nas1'
            pt = pt.replace('\\\\nas1', '')
            pt = pt.replace('\\\\nas3', '')
        elif pt.startswith('C:\\Users\\') :
            res = os.environ['HOME']
            pt = pt.replace('C:\\Users\\', '')
            pt = pt[ pt.find('\\'):]
        elif pt.startswith('H:\\'):
            res = os.path.join('/nas1/UsersData', get_user().lower() )
            pt = pt.replace('H:', '')
        elif pt.startswith('W:\\'):
            res = '/nas1/Work'
            pt = pt.replace('W:', '')
        elif pt.startswith('T:\\'):
            res = '/nas1/Data'
            pt = pt.replace('T:', '')
        elif pt.startswith('U:\\'):
            res = '/nas1/UserData'
            pt = pt.replace('U:', '')
        elif pt.startswith('X:\\'):
            res = '/nas1/Temp'
            pt = pt.replace('X:', '')
        else:
            eprint('not support convertion "%s"'%pt)
            raise NameError('not supported')
        pt = pt.replace('\\', '/')
        res= res + pt
        return res


def is_nan(num):
    return num != num
