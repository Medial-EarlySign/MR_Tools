#!/bin/python

def print_stats(dict_cnt, name, top_k, bigger_cond = 0):
    ls = []
    tot = 0
    for k,cnt in dict_cnt.items():
        ls.append([k, cnt])
        tot += cnt
    ls = sorted(ls, key = lambda x: x[1], reverse=True)
    print('%s has %d records of total %d'%(name, len(ls), tot))
    ls = ls[:top_k]
    for k, cnt in ls:
        if cnt > bigger_cond:
            print('%s:: %s => %d'%(name, k, cnt))

def read_mapper_simple(mapping_file):
    fr = open(mapping_file, 'r')
    lines = fr.readlines()
    fr.close()
    lines = lines[1:]
    lines = list(filter(lambda x: x.split('\t')[0]!='O',lines))
    mapper = dict()
    for line in lines:
        tokens = line.split('\t')
        if len(tokens) != 3:
            raise NameError('Bad Format - mapping')
        val = tokens[1].strip()
        k = tokens[2].strip()
        if (k not in mapper):
            mapper[k] = []
        mapper[k].append(val)
    return mapper

#better mapping file (Rons file) ICD9 => ICD10. first col to second
def read_mapper_full(mapping_file):
    fr = open(mapping_file, 'r')
    lines = fr.readlines()
    fr.close()
    lines = lines[1:]
    mapper = dict()
    for line in lines:
        tokens = line.split(',')
        if len(tokens) < 3:
            raise NameError('Bad Format - mapping_full')
        k = tokens[0].strip().strip('"')
        val = tokens[1].strip().strip('"')
        if val == "NoDx":
            continue
        if (k not in mapper):
            mapper[k] = []
        mapper[k].append(val)
    return mapper


def converge_dict(dict_path, mapping_file, output_dict):
    #mapper = read_mapper_simple(mapping_file)
    mapper = read_mapper_full(mapping_file)

    fr =open(dict_path, 'r')
    lines = fr.readlines()
    fr.close()
    out_lines = [lines[0]]
    lines = lines[1:]
    no_matches = dict()
    icd10_ids = dict()
    only_icd9 = dict()
    id_to_code = dict()
    max_id = 0
    #prepare map from ICD10 to id code in dict
    for line in lines:
        tokens = line.split('\t')
        if len(tokens) != 3:
            raise NameError('Bad Format - dict')
        nm = tokens[2].strip()
        id_code = int(tokens[1])
        if (nm.startswith('ICD-10-CM:')):
            icd10_cd = nm[10:].replace('.', '')
            icd10_ids[icd10_cd] = id_code
        if (id_code > max_id):
            max_id = id_code

    #prepare dictionary - save id's need to be converted in final_ids_mapper
    final_ids_mapper = dict()
    addtional_for_ids = dict()
    for line in lines:
        tokens = line.split('\t')
        nm = tokens[2].strip()
        icd9_cd = None
        icd9_id = None
        if (nm.startswith('ICD-9-CM:')):
            icd9_cd = nm[9:].replace('.', '')
            icd9_id = int(tokens[1])
            #find match in ICD10:
            if icd9_cd not in mapper:
                icd9_cd += '0'
            if icd9_cd not in mapper:
                if icd9_cd[:-1] not in no_matches:
                    no_matches[icd9_cd[:-1]] = 0
                no_matches[icd9_cd[:-1]] += 1
            else:
                match_icd10_list = mapper[icd9_cd]
                has_match = False
                for match_icd10 in match_icd10_list:
                    if match_icd10 in icd10_ids:
                        has_match = True
                        break
                if not(has_match):
                    if icd9_cd not in only_icd9:
                        only_icd9[icd9_cd] = 0
                    only_icd9[icd9_cd]+=1
                    if icd9_id not in final_ids_mapper:
                        final_ids_mapper[icd9_id] = set()
                    final_ids_mapper[icd9_id].add(max_id + 1)
                    if max_id + 1 not in addtional_for_ids:
                        addtional_for_ids[max_id + 1] = []
                    for match_icd10 in match_icd10_list:
                        addtional_for_ids[max_id + 1].append('ICD-10-CM:%s'%(match_icd10))
                    max_id += 1
    
                    
                else:
                    for match_icd10 in match_icd10_list:
                        if match_icd10 in icd10_ids:
                            icd10_id = icd10_ids[match_icd10]
                            if icd9_id not in final_ids_mapper:
                                final_ids_mapper[icd9_id] = set()
                            final_ids_mapper[icd9_id].add(icd10_id)

    uniq_nm = dict() #dict from id => set of names
    #create uniq lines - for dictionary
    for line in lines:
        tokens = line.split('\t')
        idd = int(tokens[1].strip())
        nm = tokens[2].strip()
        ids_set = [idd]
        if idd in final_ids_mapper:
            ids_set = final_ids_mapper[idd]
        for id in ids_set:
            if id not in uniq_nm:
                uniq_nm[id] = set()
            if nm not in uniq_nm[id]:
                uniq_nm[id].add(nm)
                out_lines.append('DEF\t%d\t%s\n'%(id, nm))
            if id in addtional_for_ids:
                more_opts = addtional_for_ids[id]
                for opt in more_opts:
                    if opt not in uniq_nm[id]:
                        uniq_nm[id].add(opt)
                        out_lines.append('DEF\t%d\t%s\n'%(id, opt))
            
    #print stats: only_icd9, no_matches
    print_stats(only_icd9 , 'has_icd10 not in use', 10)
    print_stats(no_matches , 'no_matches', 10)
    print('Added aditional %d'%(len(addtional_for_ids)))
    print('mapped %d keys from icd9 to icd10'%(len(final_ids_mapper)))
    #check duplicate text to diffrent ids - can't be - If ICD-something than change to SET:
    text_to_id = dict()
    text_stats = dict()
    text2_to_stats = dict()
    for line in out_lines[1:]:
        tokens = line.split('\t')
        text = tokens[2].strip()
        if not(text.startswith('ICD-')):
            if text not in text2_to_stats:
                text2_to_stats[text] = 0
            text2_to_stats[text]+=1
            continue
        if text not in text_to_id:
            text_to_id[text] = []
            text_stats[text] = 0
        text_to_id[text].append(int(tokens[1]))
        text_stats[text] +=1
    print_stats(text_stats , 'text_stats', 10, 1)

    for line in out_lines[1:]:
        tokens = line.split('\t')
        nm = tokens[2].strip()
        id_code = int(tokens[1])
        if nm in text_stats and text_stats[nm] > 1:
            continue
        if id_code not in id_to_code:
            id_to_code[id_code] = nm
        elif not(id_to_code[id_code].startswith('ICD-')) and nm.startswith('ICD-'):
            id_to_code[id_code] = nm

    additional_lines = ['\n#DEFs for SET defined by ICD9 mapped to multiple ICD10 codes\n']
    uniq_def_sets = set()
    set_lines = ['\n#Sets for ICD9 mapped to multiple ICD10 codes\n']
    for i in range(1, len(out_lines)):
        line = out_lines[i]
        #manipulate:
        tokens = line.split('\t')
        text = tokens[2].strip()
        if not(text.startswith('ICD-')):
            if text2_to_stats[text] > 1:
                cd = id_to_code[int(tokens[1].strip())]
                line = 'DEF\t%d\t%s::%s\n'%(int(tokens[1].strip()),cd, text)
                out_lines[i] = line
            continue
        if (text_stats[text] > 1):
            #change to set:
            line = 'SET\t%s\t%s\n'%(text, id_to_code[int(tokens[1].strip())])
            if text not in uniq_def_sets:
                additional_lines.append('DEF\t%d\t%s\n'%(max_id + 1, text))
                max_id += 1
                uniq_def_sets.add(text)
            set_lines.append(line)
            line = ''
        out_lines[i] = line
    if len(additional_lines) == 1:
        additional_lines = []
    if len(set_lines) == 1:
        set_lines = []
    out_lines = list(filter(lambda x:len(x) > 0,out_lines))
    out_lines = out_lines + additional_lines + set_lines
    
    fw = open(output_dict ,'w')
    fw.writelines(out_lines)
    fw.close()
    

#mapping_file = '/server/Work/Data/Mapping/ICD10_ICD9/ICD10_ICD9.tsv'
mapping_file = '/server/Work/Data/Mapping/ICD10_ICD9/icd9toicd10gem.csv'
dict_path = '/server/Work/Users/Alon/NWP/dicts/dict.before.DIAGNOSIS'
output_dict = '/server/Work/Users/Alon/NWP/dicts/dict.DIAGNOSIS'
converge_dict(dict_path, mapping_file, output_dict)