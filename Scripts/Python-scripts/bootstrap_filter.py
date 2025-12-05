import re, os

cohort_col_name = 'Cohort'
end_names = ['_Mean', '_CI.Lower.95', '_CI.Upper.95']
missing_value = -65336
verbose_warning = False
numeric_regex = re.compile(r'[0-9]+(\.[0-9]+)?')

#already transposed format
def read_bootstrap_output2(file_path):
    delim_char = '\t'
    f = open(file_path, 'r')
    lines = f.readlines()
    f.close()
    header_measurements = lines[0]
    if not(header_measurements.startswith('Cohort\tMeasurement')):
        return read_bootstrap_output(file_path)
    lines = lines[1:] #skip header
    line_num = 1
    all_measures = dict()
    all_cohorts = set()
    for line in lines:
        tokens = line.split(delim_char)
        if len(tokens) != 3:
            raise NameError('wrong format in line %d. line was "%s"'%(line_num, line))
        cohort_name = tokens[0].strip()
        measure = tokens[1].strip()
        value = None
        if (measure != 'run_id'):
            value = float(tokens[2].strip())
        if measure not in all_measures:
            all_measures[measure] = dict()
        all_measures[measure][cohort_name] = value
        line_num += 1
        all_cohorts.add(cohort_name)
    all_measures[cohort_col_name] = dict()
    for cohort_name in all_cohorts:    
        all_measures[cohort_col_name][cohort_name] = cohort_name

    #check sanity:
    if verbose_warning:
        cohort_cnt = len(all_cohorts)
        for meas, meas_vals in all_measures.items():
            cm = len(meas_vals.keys())
            if (cm != cohort_cnt):
                print('Warning: file:%s measure %s has %d cohorts and should have %d'%(file_path, meas ,cm, cohort_cnt))
    return all_measures
    
#read bootstrap and do transpose
def read_bootstrap_output(file_path):
    delim_char = '\t'
    f = open(file_path, 'r')
    lines = f.readlines()
    f.close()
    header_measurements = lines[0]
    if header_measurements.startswith('Cohort\tMeasurement'):
        return read_bootstrap_output2(file_path)
    
    titles = list(map(lambda s: s.strip() ,header_measurements.split(delim_char)))
    all_measures = dict()
    for name in titles:
        all_measures[name] = dict()
    
    lines = lines[1:]
    line_num = 1
    all_cohorts = set()
    for line in lines:
        tokens = line.split(delim_char)
        if (len(tokens) != len(titles)):
            raise NameError('format error in file %s line %d. has tokens=%d, titles=%d'%(file_path, line_num, len(tokens), len(titles)))
        cohort_name = tokens[0]
        all_cohorts.add(cohort_name)
        tokens = list(map(lambda i: tokens[i] if i == 0 or titles[i] == 'run_id' else float(tokens[i]) ,range(len(tokens))))
        for i in range(0, len(tokens)):
            all_measures[titles[i]][cohort_name] = tokens[i]
        line_num += 1
    all_measures[cohort_col_name] = dict()
    for cohort_name in all_cohorts:    
        all_measures[cohort_col_name][cohort_name] = cohort_name
    return all_measures

def filter_bootstrap(all_measures, cohort_regex, pos_regex_list = [], neg_regex_list = []):
    to_remove = []
    for r in neg_regex_list:
        #remove all measures with reg:
        reg = re.complie(r)
        for k in all_measures.keys():
            if (k != cohort_col_name and len(reg.findall(k)) > 0):
                to_remove.append(k)

    need_checksum=len(list(filter(lambda x : x.find('Checksum')>=0,pos_regex_list)))>0
    for r in pos_regex_list:
        #keep only measures with reg that intersect all filters:
        reg = re.compile(r)
        for k in all_measures.keys():
            if (k != cohort_col_name and len(reg.findall(k)) == 0):
                if k != 'Checksum' or not(need_checksum):
                    to_remove.append(k)
    for k in to_remove:
        if k in all_measures:
            all_measures.pop(k)
    #keep only relevent cohorts:
    reg = re.compile(cohort_regex)
    all_cohorts = list(all_measures[cohort_col_name].values())
    cohorts_set = set(filter( lambda n: len(reg.findall(n)) > 0 ,all_cohorts))
    for k in all_measures.keys():
        cohorts_measures = all_measures[k]
        #remove irelevetn cohorts:
        key_list = list(cohorts_measures.keys())
        for cohort_name in key_list:
            if cohort_name not in cohorts_set:
                cohorts_measures.pop(cohort_name)
    
    return all_measures

def filter_all_files(file_list, cohorts_list, measure_regex_list, measure_neg_list):
    cohorts_reg = '|'.join(cohorts_list)
    all = dict()
    for file_path, file_name in file_list.items():
        m = read_bootstrap_output(file_path)
        m = filter_bootstrap(m, cohorts_reg, measure_regex_list, measure_neg_list)
        all[file_name] = m
    return all

def auto_format(reformat : str, measure : str) -> str:
    if reformat != 'auto':
        return reformat
    #if type(measure) == tuple:
    #    breakpoint()
    #    measure = measure[1]
    format_3_set=set(['AUC', 'PART_AUC', 'Harrell-C-Statistic', 'Kendall-Tau', 'R2', 'RMSE', 'LOGLOSS'])
    format_1_set=set(['NPOS', 'NNEG', 'Checksum'])
    if measure in format_3_set or measure.find('PART_AUC')>=0:
        return '%2.3f'
    elif measure in format_1_set:
        return '%d'
    elif measure.startswith('SCORE@'):
        return '%2.5f'
    else:
        return '%2.1f'

def filter_bootstrap_ci(all_measures,  cohort_regex, pos_regex_list = [], neg_regex_list = [], reformat = None, take_obs=False):
    end_filter_nm = end_names
    if take_obs:
        end_filter_nm[0] = '_Obs'
    end_reg = '.*'
    end_reg = end_reg  + '(' + '|'.join(end_filter_nm) + ')'
    pos_regex_list.append(end_reg)
    res = filter_bootstrap(all_measures,  cohort_regex, pos_regex_list, neg_regex_list)
    if (reformat is None):
        reformat = '%s'
    #print(res)
    #format: measurement_name, cohort_name => aggregate endings
    center, lower, upper = end_filter_nm
    regs = list(map(lambda r: re.compile(r+'$'),end_filter_nm))
    all_new_meas = dict()
    for measure_name, cohort_name_vals in res.items():
        cln_name = measure_name
        for r in regs:
            cln_name = r.sub('',cln_name)
        if all_new_meas.get(cln_name) is None:
            all_new_meas[cln_name] = dict()
        for cohort_name, cohort_val in cohort_name_vals.items():
            if measure_name == cohort_col_name:
                all_new_meas[cln_name][cohort_name] = [cohort_val]
                continue
            try:
                cohort_va = float(cohort_val)
                cohort_val = cohort_va
            except:
                if verbose_warning:
                    print('Warning: can\'t read %s in measure %s'%(cohort_val, measure_name))
                pass
            if all_new_meas[cln_name].get(cohort_name) is None:
                all_new_meas[cln_name][cohort_name] = [None, None, None]
            if measure_name.endswith(center):
                all_new_meas[cln_name][cohort_name][0] = cohort_val
            elif measure_name.endswith(lower):
                all_new_meas[cln_name][cohort_name][1] = cohort_val
            elif measure_name.endswith(upper):
                all_new_meas[cln_name][cohort_name][2] = cohort_val
            else:
                all_new_meas[cln_name][cohort_name] = [cohort_val]
    #make list to string:
    for measure_name,cohort_name_vals in all_new_meas.items():
        for cohort_name, cohort_val in cohort_name_vals.items():
            if len(cohort_val) > 2:
                format_final = auto_format(reformat, measure_name)
                full_desc = (format_final + '[' + format_final + ' - ' + format_final + ']')%(cohort_val[0], cohort_val[1], cohort_val[2])
            else:
                full_desc = cohort_val[0]
            all_new_meas[measure_name][cohort_name] = full_desc
     
    return all_new_meas

def filter_all_files_ci(file_list, cohorts_list, measure_regex_list, measure_neg_list, reformat = None, take_obs=False):
    cohorts_reg = '|'.join(cohorts_list)
    all = dict()
    for file_path, file_name in file_list.items():
        m = read_bootstrap_output(file_path)
        m = filter_bootstrap_ci(m, cohorts_reg, measure_regex_list, measure_neg_list, reformat, take_obs)
        all[file_name] = m
    return all

def is_num(a):
    return type(a) == float

def clean_measure_name(s):
    tokens = s.split('_')
    
    num_part=tokens[-1]
    m = numeric_regex.match(num_part)
    if m and m.span()[1] == len(num_part) and num_part.find('.')>=0:
        num_part = num_part.strip('0')
        if num_part.startswith('.'):
            num_part = '0' + num_part
        if num_part.endswith('.'):
            num_part = num_part[:-1]
        to_join=tokens[:-1]
        to_join.append(num_part)
        return '_'.join(to_join)
        
    return s

def sort_measurements(s):
    tokens = s.split('_')
    
    num_part=tokens[-1]
    m = numeric_regex.match(num_part)
    if m and m.span()[1] == len(num_part):
        num_parsed = float(num_part)
        return tokens[0] + '_' +  '%015.6f'%(num_parsed)
    
    return s

def print_result(all_res, report_ord, delim_char = '\t', reformat = None, format_table = 'm,rc'):
    format_tokens=format_table.split(',')
    legal_chars=set(['m','r', 'c'])
    if len(format_tokens)!=2:
        raise NameError('Wrong format_table argument. should contain comma to seperate row and cols. got "%s"'%(format_table))
    rows_format=format_tokens[0].strip().lower()
    cols_format=format_tokens[1].strip().lower()
    #check correctness:
    if len(rows_format) != 1 and len(rows_format)!=2:
        raise NameError('Wrong format_table argument. rows argument should be 1-2 letters. got "%s". row part "%s"'%(format_table, rows_format))
    if len(cols_format) != 1 and len(cols_format)!=2:
        raise NameError('Wrong format_table argument. cols argument should be 1-2 letters. got "%s". col part "%s"'%(format_table, cols_format))
    if (len(cols_format) + len(rows_format))!=3:
        raise NameError('Wrong format_table argument. rows+cols argument should be exactly 3 letters. got "%s"'%(format_table))
    if not((rows_format[0] in legal_chars) and ((len(rows_format)==1) or ((rows_format[1] in legal_chars) and rows_format[0]!=rows_format[1] ))):
        raise NameError('Wrong format_table argument. rows argument should contain letters [m,r,c] only and different letters. got "%s". row part "%s"'%(format_table, rows_format))
    if not((cols_format[0] in legal_chars) and ((len(cols_format)==1) or ((cols_format[1] in legal_chars) and cols_format[0]!=cols_format[1] ))):
        raise NameError('Wrong format_table argument. cols argument should contain letters [m,r,c] only and different letters. got "%s". col part "%s"'%(format_table, cols_format))
    #Check alldifferent letters:
    diff_letters=set()
    for c in rows_format:
        diff_letters.add(c)
    for c in cols_format:
        diff_letters.add(c)
    if (len(diff_letters)!=3):
        raise NameError('Wrong format_table argument. rows+cols argument should be different letters. got "%s"'%(format_table))
    if (reformat is None):
        reformat = '%s'

    #Fetch cohorts - C
    #order cohorts: All is first if exists
    cohorts = set()
    for fname in report_ord:
        for c in all_res[fname][cohort_col_name].values():
            cohorts.add(c)
    cohorts = list(cohorts)
    all_name = list(filter(lambda x: x.lower()=='all',cohorts))
    if (len(all_name) > 0):
        cohorts.remove(all_name[0])
    cohorts = sorted(cohorts)
    if (len(all_name) > 0):
        cohorts.insert(0, all_name[0])
    #Fetch measurement - M
    measurements = set()
    for fname in report_ord:
        for c in all_res[fname].keys():
            measurements.add(clean_measure_name(c))
    measurements = list(measurements)
    #order Cohort_desription first, than by name:
    measurements.remove(cohort_col_name)
    measurements = sorted(measurements, key = sort_measurements)
    
    all_names = report_ord
    #report_ord - for r letter
    #all_res - set of c,m. set by: cohorts, measurements

    map_letter_lists = { 'm':measurements, 'r':report_ord, 'c':cohorts }
    map_letter_Names = { 'm':'Measurements', 'r':'Report', 'c':'Cohort' }
    st_cols=[]
    #construct "rows"
    rows = map_letter_lists[rows_format[0]]
    st_cols=[map_letter_Names[rows_format[0]]]
    if (len(rows_format)>1):
        #cartezian multiple by map_letter_lists[rows_format[1]]
        new_grp=[]
        for a_val in map_letter_lists[rows_format[0]]:
            for b_val in map_letter_lists[rows_format[1]]:
                grp=(a_val, b_val)
                new_grp.append(grp)
        rows = new_grp
        st_cols[0] += '$' + map_letter_Names[rows_format[1]]
        
    cols = map_letter_lists[cols_format[0]]
    if (len(cols_format)>1):
        #cartezian multiple by map_letter_lists[rows_format[1]]
        new_grp=[]
        for a_val in map_letter_lists[cols_format[0]]:
            for b_val in map_letter_lists[cols_format[1]]:
                grp=(a_val, b_val)
                new_grp.append(grp)
        cols = new_grp
    
    measure_flat = dict()
    for r in rows:
        measure_flat[r] = dict()

    for r_name in all_names: #Iterate Reports - r
        m = all_res[r_name]
        for m_name in m.keys(): # iterate Measurements - m
            if m_name == cohort_col_name:
                continue
            cohorts_res = m[m_name]
            m_name= clean_measure_name(m_name)
            for c_name in cohorts_res.keys(): #Iterate Cohort - c
                #Construct row key, col key and store:
                val_num = cohorts_res[c_name]
                access_dict = { 'm': m_name, 'c': c_name, 'r':r_name }
                row_key = access_dict[rows_format[0]]
                col_key = access_dict[cols_format[0]]
                if len(rows_format) > 1:
                    row_key = (access_dict[rows_format[0]], access_dict[rows_format[1]])
                if len(cols_format) > 1:
                    col_key = (access_dict[cols_format[0]], access_dict[cols_format[1]])                
                measure_flat[row_key][col_key] = val_num

    all_lines = []
    full_cols = st_cols + list(map(lambda x: x if type(x) is str else '%s$%s'%(x[0],x[1]) , cols))
    header = delim_char.join(full_cols)
    all_lines.append(header)
    #print(header)
    format_final = '%d'
    col_idxx=0
    row_idxx=-1
    if 'm' in cols_format:
        if len(cols_format) > 1:
            if cols_format.startswith('m'):
                col_idxx=0
            else:
                col_idxx=1
        else:
            col_idxx = -1
    else:
        col_idxx=-1
        if len(rows_format) > 1:
            if rows_format.startswith('m'):
                row_idxx=0
            else:
                row_idxx=1
        else:
            row_idxx=-1
        
    null_str = (format_final + '[' + format_final + ' - ' + format_final + ']')%(missing_value,missing_value,missing_value)
    for row in rows:
        m = measure_flat[row]
        if row_idxx==-1 and col_idxx==-1:
            if 'm' in cols_format:
                vals = list(map(lambda col : ((auto_format(reformat, col))%(m[col]) if is_num(m[col]) else m[col]) if col in m and m[col]!=missing_value and m[col] != null_str else 'EMPTY' ,cols))
            else:
                vals = list(map(lambda col : ((auto_format(reformat, row))%(m[col]) if is_num(m[col]) else m[col]) if col in m and m[col]!=missing_value and m[col] != null_str else 'EMPTY' ,cols))
        elif row_idxx==-1 and col_idxx>=0:
            vals = list(map(lambda col : ((auto_format(reformat, col[col_idxx]))%(m[col]) if is_num(m[col]) else m[col]) if col in m and m[col]!=missing_value and m[col] != null_str else 'EMPTY' ,cols))
        elif col_idxx==-1 and row_idxx>=0:
            vals = list(map(lambda col : ((auto_format(reformat, row[row_idxx]))%(m[col]) if is_num(m[col]) else m[col]) if col in m and m[col]!=missing_value and m[col] != null_str else 'EMPTY' ,cols))
        else:
            raise NameError('Bug')
        if type(row) is str:
            vals.insert(0, row)
        else:
            vals.insert(0, '%s$%s'%(row[0], row[1]))
        line =  delim_char.join(vals)
        all_lines.append(line)
        
    return measure_flat, rows, cols, all_lines

def show_cohorts(file_list):
    all_s = set()
    for file_path, file_name in file_list.items():
        m = read_bootstrap_output(file_path)
        for c in m[cohort_col_name].values():
            all_s.add(c)
    all_s = sorted(list(all_s))
    for c in all_s:
        print(c)
    return all_s

def show_measures(file_list):
    all_s = set()
    for file_path, file_name in file_list.items():
        m = read_bootstrap_output(file_path)
        for c in m.keys():
            all_s.add(c)
    all_s = sorted(list(all_s))
    for c in all_s:
        print(c)
    return all_s

if __name__ == '__main__':
    #base_path = r'W:\Users\Alon\Influenza\outputs\models_bootstrap'
    base_path = '/server/Work/Users/Alon/Influenza/outputs/models_bootstrap'
    cohorts_list = ['All']
    file_dict = {os.path.join(base_path, 'validation' ,'qrf_validation_test.csv') : 'QRF',
                 os.path.join(base_path, 'validation' ,'age_validation_test.csv') : 'Age_Model',
                 os.path.join(base_path, 'validation' ,'linear_validation_test.csv') : 'Linear_Model',
                 os.path.join(base_path, 'validation' ,'guidline_eldery_validation_test.csv') : 'Binary_Age'
                 }
    measure_regex = ['_Mean', 'AUC|PPV@FPR|SENS@(FPR|PR)|^PR@SENS|SENS@SCORE_1.000|^PR@SCORE_1.000']
    measure_neg = []
    
    all = filter_all_files(file_dict, cohorts_list, measure_regex, measure_neg)
    measure_flat = print_result(all)
    #all_cohorts = list(all_measures['Cohort_Description'].values())