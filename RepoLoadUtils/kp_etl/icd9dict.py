# -*- coding: utf-8 -*-
"""
Created on Thu Apr 12 08:13:38 2018

@author: Ron
"""

import sys
#import numpy as np
import os.path
sys.path.append('H:\\MR\\Tools\\RepoLoadUtils\\kp_etl\\icd9')
sys.path.append('/nas1/UsersData/ron/MR/Tools/RepoLoadUtils/kp_etl/icd9')
from icd9 import ICD9
import re
import numpy as np
import pandas as pd

tree = ICD9('icd9/codes.json')
#
#node = tree.find('003')
#for c in node.parents:
#    print('- {}: {}'.format(c.code, c.description)) 
#    

###########################################################################################
# Get All Codes
###########################################################################################
charsToRemove = '[,]'

def dfs(start, code_map , visited=None,visited_code=None, children_map = None):
    if visited is None:
        visited = set()
        visited_code = set()
        children_map = dict()
    
    if not(start in visited):
        if len(start.children) > 0:
            children_map[start.code] = [child.code for child in start.children]
        code_map[start.code] = "_".join(start.descr.split()) 
        
    visited.add(start)
    visited_code.add(start.code)
    
    for next in set(start.children) - visited:
        dfs(next, code_map , visited,visited_code,children_map)
    return visited,visited_code,children_map, code_map

# 
#node = tree.find('162.9')
#tree.find('162.9').descr

def short_to_decimal_icd9(code):
    """
    Convert an ICD9 code from short format to decimal format.
    """
    if (code[0] == 'E'):
        tempCode = code[1:]
        if len(tempCode) <= 3:
            return 'E' + tempCode
        else:
            return 'E' + tempCode[:3] + "." + tempCode[3:]
    
    if len(code) <= 3:
        return code
    else:
        return code[:3] + "." + code[3:]

def short_to_decimal_icd10(code):
    """
    Convert an ICD9 code from short format to decimal format.
    """
    if len(code) <= 3:
        return code
    else:
        return code[:3] + "." + code[3:]


# Overide with long descr + missing codes
def icd9codeEnhance(children_map,code_map,ignore_dict,charsToRemove):
    descrFileName = 'icd9/CMS30_DESC_LONG_DX080612.txt'
    my_path = os.path.dirname(os.path.realpath('__file__'))
    path = os.path.join(my_path, descrFileName)
    
    with open(path) as f:
        lines = f.readlines()
        
    for line in lines:
        lstrip = line.split()
        code = short_to_decimal_icd9(lstrip[0])
        code_map[code] = "_".join(lstrip[1:])
    
    code_map_set = set(code_map.keys())
    cnt = 0
    # Fill Values from files:
    newCodesHistDict = dict()
    
    dataFilesDir = r'D:\Databases\kpsc'
    #dataFilesDir = '/nas1/Data/kpsc'
    
    fileList = ['/cases_dx.txt','/controls_dx1.txt','/controls_dx2.txt','/controls_dx3.txt']
    for file in fileList:
        with open(dataFilesDir + file) as f:
            lines = f.readlines()
        
        for line in lines:
            lineSplit = line.strip().split('\t')
            code_type = lineSplit[8]
            if code_type == 'ICD9':
                code = lineSplit[6]
                code_descr = lineSplit[7] 
                       
            if code not in code_map_set:
                print(code + ' ' + code_descr + " Doesn't exist")
                newCodesHistDict[code][code_descr] = newCodesHistDict.setdefault(code, dict()).setdefault(code_descr,0) + 1
                
    #ignore below th
    ignoreTh = 5

    for code in newCodesHistDict:
        code_descr = list(newCodesHistDict[code])[np.argmax(newCodesHistDict[code].values())]
        if (code_descr != '') & (newCodesHistDict[code][code_descr] > ignoreTh):
            code_map[code] = code_descr   
            
            code_children = [k for k in code_map.keys() if (k.find(code) == 0) and (code != k)] 
            if len(code_children) >= 2:
                children_map[code] = code_children
            print('code: ' + code + ' ' + code_descr + ' Added')
        else:
            print('code: ' + code + ' ' + code_descr +  ' Ignored')
            ignore_dict[code] = code_descr
          

###########################################################################################
# Main
###########################################################################################

def genIcd9Map(ignore_dict, code_map, filename = 'dict.icd9'):
    print(type(code_map))
    visited,visited_code,children_map, code_map = dfs(tree,code_map);
    icd9codeEnhance(children_map,code_map,ignore_dict,charsToRemove)
     # remove unwanted characters
    code_map = {k : re.sub(charsToRemove,'',v) for k,v in code_map.items()}    
    
    # fixed cuplicated names
    correctDuplicatedNames(code_map,children_map)
    
    ## Gen String
    outStr = "SECTION"+"\t" + "ICD9_Diagnosis,ICD9_Hospitalization" + "\n"
    sorted_codes = sorted(code_map.keys())
    #filename = 'dict.icd9'
    currNum = 100000
    for code in sorted_codes:
        outStr += "DEF" + "\t" + str(currNum) + "\t" + code + "\n"
        outStr += "DEF" + "\t" + str(currNum) + "\t" + code_map[code] + "\n"
        currNum += 1
    
    ### debug 
#    for k,v in code_map.items():
#        cntr[v] = cntr.setdefault(v,0) + 1
    
    
    ###
    sorted_set_codes = sorted(children_map.keys())
    # Add Sets:
    for code in sorted_set_codes:
        sorted_children = sorted(children_map[code])
        for child in sorted_children:
            outStr += "SET" + "\t" + code + "\t" + child + "\n"
     
    with open(filename, "wb") as text_file:
        text_file.write(str.encode(outStr))

def icd9icd10conversion(icd92icd10Dict,icd102icd9Dict):
    descrFileName = 'icd9\\icd9to10dictionary.txt'
    my_path = os.path.dirname(os.path.realpath('__file__'))
    path = os.path.join(my_path, descrFileName)
    with open(path) as f:
        lines = f.readlines()

    for line in lines:
        linesSplit = line.split("|")    
        icd92icd10Dict[linesSplit[0]] = linesSplit[1] 
        icd102icd9Dict[linesSplit[1]] = linesSplit[0] 

def icd9icd10conversion2(icd92icd10Dict,icd102icd9Dict):
    descrFileName = 'icd9\\icd9icd10.xls'
    my_path = os.path.dirname(os.path.realpath('__file__'))
    path = os.path.join(my_path, descrFileName)
    dfConver = pd.read_excel(path,dtype = 'str')
    
    for index,row in dfConver.iterrows():  
        icd92icd10Dict[short_to_decimal_icd9(row['Pure Victorian Logical'])] = short_to_decimal_icd10(row['ICD10'])
        icd102icd9Dict[short_to_decimal_icd10(row['ICD10'])] = short_to_decimal_icd9(row['Pure Victorian Logical']) 

def icd9icd10conversion3(icd92icd10Dict,icd102icd9Dict):
    descrFileName = 'icd9\\icd10toicd9gem.csv'
    my_path = os.path.dirname(os.path.realpath('__file__'))
    path = os.path.join(my_path, descrFileName)
    dfConver = pd.read_csv(path,dtype = 'str')
    
    for index,row in dfConver.iterrows():  
        icd92icd10Dict[short_to_decimal_icd9(row['icd9cm'])] = short_to_decimal_icd10(row['icd10cm'])
        icd102icd9Dict[short_to_decimal_icd10(row['icd10cm'])] = short_to_decimal_icd9(row['icd9cm']) 

def correctDuplicatedNames(code_map,children_map):
     from collections import Counter
     import re
     cvalues = Counter(v for k,v in code_map.items())
     # Create oppsoite dict
     name2codesDict = dict()
     for k,v in code_map.items():
        if v in name2codesDict:
            name2codesDict[v].append(k)
        else:
            name2codesDict[v] = [k]

     code2parentDict = {v[i] : k for k,v in children_map.items() for i in range(len(v))}
     for value in cvalues:
         if cvalues[value] > 1:
             
             # Check if parent - children case:
             childParentFlag = False
             if name2codesDict[value][1] in children_map.get(name2codesDict[value][0],[]) or (code2parentDict.get(name2codesDict[value][0],'1') ==  code2parentDict.get(name2codesDict[value][1],'2')):
                 childParentFlag = True
            
             currInd = 1
             if childParentFlag: 
                 sortedInd = np.argsort([float(re.sub("\D", "", code)) for code in name2codesDict[value]])
                 for ind in sortedInd[1:]:
                     code_map[name2codesDict[value][ind]] = code_map[name2codesDict[value][ind]] + '_' + str(currInd)
                     currInd += 1                    
             else: 
                 for code in name2codesDict[value]:
                     if code in code2parentDict:
                         code_map[code] = code_map[code] + '_' + code_map[code2parentDict[code]]
                    
     # add _ind to remainig codes:
     cvalues = Counter(v for k,v in code_map.items())
     for value in cvalues:
         if cvalues[value] > 1:
             currInd = 1
             for code in name2codesDict[value]:
                 code_map[code] = code_map[code] + '_' + str(currInd)                
                 currInd += 1 
                         
                     
                
            
     
#     
#     for value in cvalues:
#         if cvalues[value] > 1:
#             currInd = 1
#             # clean children with same name as parent
#             for code in name2codesDict[value]:
#                 code_children = []
#                 if code in  children_map:
#                     code_children = [code_map[child_code] for child_code in children_map[code]]
#                            
#                 if not value in code_children:
#                     
#                     if (value ==  code_map.get(code2parentDict.get(code,''),'')) or (not code in code2parentDict): 
#                         # equal to parents name
#                         newName = value + '_' + str(currInd)
#                         currInd += 1
#                     else:
#                         # Added parent name
#                         newName = value + '_' + code_map[code2parentDict[code]]
#                
#                
#                     code_map[code] = newName 
                     
                     
     # there are still resdiuals - probably 2 levels diffs:
#     cvalues = Counter(v for k,v in code_map.items())
#     for value in cvalues:
#         if cvalues[value] > 1:
#             codes_float = [float(code) for code in name2codesDict[value]]:
#             
            
             
             
             
      
# temp
ignore_dict = dict()
code_map = dict()

genIcd9Map(ignore_dict, code_map, filename = 'dict.icd9')
         