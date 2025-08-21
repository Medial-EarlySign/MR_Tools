# -*- coding: utf-8 -*-
"""
Created on Mon Apr  9 16:07:55 2018

@author: Ron
"""
import numpy as np
import pandas as pd
import re
import icd9dict
import random
import collections
import os



outputDir = 'D:/KP_LAB_26092018/'
#outputDir = '/home/Work/Users/Ron/KP_temp'
charsToRemove = "[,'/]"

def correctComponent2(df,correctMap):
    for correction in correctMap.items():
        ind = [True] * len(df)
        for element in correction[0]:
            colname = element.split('=')[0]
            value =element.split('=')[1]
            ind = ind & (df[colname] == value)
        
        print(df[ind].head()) 
        print('changed component2 to ' + correction[1])
        df.loc[ind,'component2'] = correction[1]
   
##################################################################################################
# Read Files to data frames
##################################################################################################
sourceDir = 'D:/Databases/kpsc'

#sourceDir = '/nas1/Data/kpsc'

filenameThinSignals = r'W:\CancerData\Repositories\THIN\thin_jun2017\thin.signals'
#filenameThinSignals = '/nas1/Work/CancerData/Repositories/THIN/thin_jun2017/thin.signals'

fileControlCbc =  '/15-07-2018/controls_cbc.txt'
fileControlDemo = '/03-05-2018/controls_demo.txt'
fileControlLabList = ['/20-08-2018/controls_lab1.txt','/20-08-2018/controls_lab2.txt','/20-08-2018/controls_lab3.txt']
fileControlDxList = ['/controls_dx1.txt','/controls_dx2.txt','/controls_dx3.txt']
fileControlHosp = '/controls_hosp.txt'
fileControlAlcohol = '/03-05-2018/controls_alcohol.txt'
fileControlPft = '/03-05-2018/controls_pft.txt'
fileControlSmoking = '/03-05-2018/controls_smoking.txt'
fileControlBmi = '/03-05-2018/controls_bmi.txt'
fileControlAdditionalDx = '/03-05-2018/controls_dx_lung_ca.txt'

dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t',dtype = str) 
dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfControlLabList = []
for fileControlLab in fileControlLabList:
    dfControlLabList.append(pd.read_csv(sourceDir + fileControlLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfControlLab = pd.concat(dfControlLabList)    

dfControlDxList = []
for fileControlDx in fileControlDxList:
    dfControlDxList.append(pd.read_csv(sourceDir + fileControlDx, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfControlDx = pd.concat(dfControlDxList)    
dfControlHosp =  pd.read_csv(sourceDir + fileControlHosp, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfControlAlcohol =pd.read_csv(sourceDir + fileControlAlcohol, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfControlPft = pd.read_csv(sourceDir + fileControlPft, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfControlSmoking = pd.read_csv(sourceDir + fileControlSmoking, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfControlBmi = pd.read_csv(sourceDir + fileControlBmi, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 

fileCaseCbc =  '/15-07-2018/cases_cbc.txt'
fileCaseDemo = '/03-05-2018/cases_demo.txt'
fileCaseLab = '/20-08-2018/cases_lab.txt'
fileCaseDxList = ['/cases_dx.txt', '/03-05-2018/cases_dx_lung_ca.txt']
fileCaseHosp = '/cases_hosp.txt'
fileCaseTumor = '/cases_tumor.txt'
fileCaseAlcohol = '/03-05-2018/cases_alcohol.txt'
fileCasePft = '/03-05-2018/cases_pft.txt'
fileCaseSmoking = '/03-05-2018/cases_smoking.txt'
fileCaseBmi = '/03-05-2018/cases_bmi.txt'

dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t',dtype = str)
dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseLab =  pd.read_csv(sourceDir + fileCaseLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseHosp =  pd.read_csv(sourceDir + fileCaseHosp, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseTumor =  pd.read_csv(sourceDir + fileCaseTumor, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseAlcohol =pd.read_csv(sourceDir + fileCaseAlcohol, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCasePft = pd.read_csv(sourceDir + fileCasePft, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseSmoking = pd.read_csv(sourceDir + fileCaseSmoking, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseBmi = pd.read_csv(sourceDir + fileCaseBmi, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfCaseDxList = []

for fileCaseDx in fileCaseDxList:
    dfCaseDxList.append(pd.read_csv(sourceDir + fileCaseDx, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
    
dfCaseDx = pd.concat(dfCaseDxList) 

#fileCaseAdditionalDx

# List to Run
dfDemo = pd.concat([dfCaseDemo,dfControlDemo]).sort_values(by = 'id')
dfCbc = pd.concat([dfCaseCbc,dfControlCbc]).sort_values(by = 'id')

# Apply corrections to raw data
correctMap = dict()
correctMap['component2=EOSINOPHILS','rrange=0-10%']  = 'EOSINOPHILS %'
correctMap['component2=BASOPHILS','rrange=0-1%']  = 'BASOPHILS %'
correctComponent2(dfCbc,correctMap)

dfLab = pd.concat([dfCaseLab,dfControlLab]).sort_values(by = 'id')
dfDx = pd.concat([dfCaseDx,dfControlDx]).sort_values(by = 'id')
dfHosp = pd.concat([dfCaseHosp,dfControlHosp]).sort_values(by = 'id')
dfAlcohol = pd.concat([dfCaseAlcohol,dfControlAlcohol]).sort_values(by = 'id')
dfPft = pd.concat([dfCasePft,dfControlPft]).sort_values(by = 'id')
dfSmoking = pd.concat([dfCaseSmoking,dfControlSmoking]).sort_values(by = 'id')
dfBmi = pd.concat([dfCaseBmi,dfControlBmi]).sort_values(by = 'id')
del dfCaseDemo, dfControlDemo , dfCaseCbc,dfControlCbc , dfCaseLab,dfControlLab, dfCaseDx,dfControlDx, dfCaseHosp,dfControlHosp,dfCaseAlcohol,dfControlAlcohol,dfCasePft,dfControlPft,dfCaseSmoking,dfControlSmoking,dfCaseBmi,dfControlBmi

#dfList = [dfCaseDemo , dfCaseCbc, dfCaseLab, dfCaseDx, dfCaseHosp]
dfCaseTumor['Lung_Cancer'] = '1'
dfList = [dfDemo , dfCbc, dfLab, dfDx, dfHosp, dfCaseTumor,dfAlcohol,dfPft,dfSmoking,dfBmi]
del dfCbc, dfLab, dfDx, dfHosp, dfCaseTumor,dfAlcohol,dfPft,dfSmoking,dfBmi

#print("REMOVE BEFORE REAL Run!!!")
#for k in range(len(dfList)):
#    dfList[k] = dfList[k].iloc[0:1000,:]

kp2FinalNameDict = dict()
kpSecDict = dict()
finalName2KpDict = dict()
kpName2Desc = dict()
kpName2transDict = dict()

##################################################################################################
# Demogarphic Maps
##################################################################################################

kp2FinalNameDict['dob'] = 'BDATE'
kp2FinalNameDict['GENDER'] = 'GENDER'
kp2FinalNameDict['race'] = 'Race'    
kp2FinalNameDict['marital'] = 'Marital'
kp2FinalNameDict['H_MED_INCOME'] = 'Income'
kp2FinalNameDict['education'] = 'Education'
kp2FinalNameDict['dod'] = 'DEATH'
kp2FinalNameDict['mem_start'] = 'STARTDATE'
kp2FinalNameDict['mem_stop'] = 'ENDDATE'
kp2FinalNameDict['index_date'] = 'INDEXDATE'


kpName2Desc['GENDER'] = 'Male=1,Female=2'
kpName2Desc['race'] = 'Asian=1,Black=2,Hispanic=3,White=4,Other=5'
kpName2Desc['marital'] = 'Never married=0,Married or living as married=1, Widowed=2,Separated=3,Divorced=4,Other=5'
kpName2Desc['education'] = "Less than high school=1,Some high school=2,High school graduate=3,Some college, no degree=4,Associate's degree=5,Bachelor's degree=6,Graduate degree=7"
# 

##################################################################################################
# CBC Maps
##################################################################################################

# Create CBC Map:
kp2FinalNameDict['HCT'] = 'Hematocrit'
kp2FinalNameDict['HGB'] = 'Hemoglobin'
kp2FinalNameDict['MCH'] = 'MCH'
kp2FinalNameDict['MCHC'] = 'MCHC-M'
kp2FinalNameDict['MCV'] = 'MCV'
kp2FinalNameDict['MPV'] = 'MPV'
kp2FinalNameDict['PLATELETS'] = 'Platelets'
kp2FinalNameDict['RBC'] = 'RBC'
kp2FinalNameDict['RDW'] = 'RDW'
kp2FinalNameDict['WBC'] = 'WBC'
kp2FinalNameDict['BASOPHILS %'] = 'Basophils%' 
kp2FinalNameDict['EOSINOPHILS %'] = 'Eosinophils%' 
kp2FinalNameDict['LYMPHOCYTES %'] = 'Lymphocytes%'
kp2FinalNameDict['NEUTROPHILS %'] = 'Neutrophils%'
kp2FinalNameDict['MONOCYTES %'] = 'Monocytes%'
kp2FinalNameDict['RBC NUCLEATED'] = 'nRBC'
kp2FinalNameDict['BANDS %'] = 'Bands%' 
kp2FinalNameDict['NEUTROPHILS'] = 'Neutrophils#'
kp2FinalNameDict['BASOPHILS'] = 'Basophils#'
kp2FinalNameDict['EOSINOPHILS'] = 'Eosinophils#'
kp2FinalNameDict['LYMPHOCYTES'] = 'Lymphocytes#'
kp2FinalNameDict['MONOCYTES'] = 'Monocytes#'

##################################################################################################
# Lab Mapping exists in THIN
##################################################################################################

kp2FinalNameDict['CHLORIDE'] = 'Cl'
kp2FinalNameDict['CO2'] = 'CO2'
kp2FinalNameDict['POTASSIUM'] = 'K+'
kp2FinalNameDict['SODIUM'] = 'Na'
kp2FinalNameDict['BUN'] = 'Urea'
kp2FinalNameDict['CREATININE'] = 'Creatinine'
kp2FinalNameDict['CHOLESTEROL'] = 'Cholesterol'
kp2FinalNameDict['HDL'] = 'HDL'
kp2FinalNameDict['LDL CALCULATED'] = 'LDL'
kp2FinalNameDict['TRIGLYCERIDE'] = 'Triglycerides'
kp2FinalNameDict['ALT'] = 'ALT'
kp2FinalNameDict['LDL'] = 'LDL'
kp2FinalNameDict['CALCIUM'] = 'Ca'
kp2FinalNameDict['FERRITIN'] = 'Ferritin'
kp2FinalNameDict['GLUCOSE, RANDOM'] = 'RandomGlucose'
kp2FinalNameDict['BILIRUBIN, TOTAL'] = 'Bilirubin'
kp2FinalNameDict['CK'] = 'CK'
kp2FinalNameDict['ALKALINE PHOSPHATASE'] = 'ALKP'
kp2FinalNameDict['PHOSPHORUS'] = 'Phosphore'
kp2FinalNameDict['ALBUMIN'] = 'Albumin'
kp2FinalNameDict['GLOBULIN'] = 'Globulin'
kp2FinalNameDict['TOTAL PROTEIN'] = 'Protein_Total'
kp2FinalNameDict['AST'] = 'AST'
kp2FinalNameDict['INR'] = 'INR'
kp2FinalNameDict['PT INR'] = 'INR'
kp2FinalNameDict['PT-INR'] = 'INR'
kp2FinalNameDict['AMYLASE'] = 'Amylase'
kp2FinalNameDict['BILIRUBIN, DIRECT'] = 'DirectBilirubin'
kp2FinalNameDict['URIC ACID'] = 'Uric_Acid'
kp2FinalNameDict['25-HYDROXYVITAMIN D'] = 'VitaminD_25'
kp2FinalNameDict['VITAMIN D, 25-HYDROXY, D2'] = 'VitaminD_25'
kp2FinalNameDict['VITAMIN D, 25-HYDROXY, D3'] = 'VitaminD_25'
kp2FinalNameDict['VIT B12'] = 'B12'
kp2FinalNameDict['FOLATE'] = 'Follic_Acid'
kp2FinalNameDict['TRIGLYCERIDE, NONFASTING'] = 'Triglycerides'
kp2FinalNameDict['GGT'] = 'GGT'
kp2FinalNameDict['LDH'] = 'LDH'
kp2FinalNameDict['PT'] = 'PT'
kp2FinalNameDict['Vitamin D, 25-OH, D2'] = 'VitaminD_25'
kp2FinalNameDict['Vitamin D, 25-OH, D3'] = 'VitaminD_25'
kp2FinalNameDict['Vitamin D, 25-OH, Total'] = 'VitaminD_25'
kp2FinalNameDict['IRON'] = 'Iron_Fe'
kp2FinalNameDict['TRANSFERRIN'] = 'Transferrin'
#['SERUM SPECIMEN'] # Remove - 1 value
#['APTT IMMEDIATELY AFTER ADDITION OF NORMAL PLASMA']  Remove - 1 value
kp2FinalNameDict['CHOLESTEROL, NON-HDL'] = 'NonHDLCholesterol'
kp2FinalNameDict['INR, BLOOD, POCT'] = 'INR'
kp2FinalNameDict['GLUCOSE, BLOOD, POCT'] = 'Glucose'
kp2FinalNameDict['HGB A1C, EXTERNAL RESULT.'] = 'HbA1C' 
kp2FinalNameDict['GLUCOSE, BLOOD'] = 'Glucose'
kp2FinalNameDict['CALCIUM, PRE DIALYSIS'] = 'Ca'
kp2FinalNameDict['PHOSPHORUS, PRE DIALYSIS'] = 'Phosphore'
kp2FinalNameDict['CREATININE PRE DIALYSIS,SER/PLAS'] = 'Creatinine'
kp2FinalNameDict['BUN, PRE DIALYSIS'] = 'Urea'
kp2FinalNameDict['GLUCOSE POST FAST'] = 'Glucose'
kp2FinalNameDict['INR, EXTERNAL REPORT'] = 'INR'
kp2FinalNameDict['INR, PATIENT PERFORMED'] = 'INR'
kp2FinalNameDict['APTT'] = 'PTT'
kp2FinalNameDict['APTT IMMEDIATELY AFTER ADDITION OF NORMAL PLASMA'] = 'PTT'
kp2FinalNameDict['TOTAL IRON BINDING CAPACITY, UNSATURATED'] = 'TIBC'
kp2FinalNameDict['TOTAL IRON BINDING CAPACITY'] = 'TIBC'
kp2FinalNameDict['TOTAL IRON BINDING CAPACITY, UNSATURATED'] = 'TIBC'
kp2FinalNameDict['GLOMERULAR FILTRATION RATE'] = 'GFR'
kp2FinalNameDict['GLUCOSE, FASTING'] = 'Glucose'
kp2FinalNameDict['HGBA1C%'] = 'HbA1C'
kp2FinalNameDict['ALBUMIN DIALYSIS, BROMCRESOL GREEN'] = 'Albumin'
kp2FinalNameDict['component2'] = 'Repo'
kp2FinalNameDict['GFR EST'] = 'eGFR'
kp2FinalNameDict['SGPT (ALT)'] = 'ALT'
kp2FinalNameDict['CALCULATED LDL'] = 'LDL'
kp2FinalNameDict['CHOL/HDL RATIO'] = 'Cholesterol_over_HDL'
kp2FinalNameDict['DIRECT HDL'] = 'HDL'
kp2FinalNameDict['TRIGLYCERIDES'] = 'Triglycerides'
kp2FinalNameDict['GLUC-FAST'] = 'Glucose'
kp2FinalNameDict['TOTAL CALCIUM'] = 'Ca'
kp2FinalNameDict['HEMOGLOBIN A1C'] = 'HbA1C'
kp2FinalNameDict['SGOT (AST)'] = 'AST'
kp2FinalNameDict['VITAMIN B12'] = 'B12'
kp2FinalNameDict['TIBC'] = 'TIBC'
kp2FinalNameDict['GLUC-RAND'] = 'RandomGlucose'
kp2FinalNameDict['CHOL/HDL RATIO'] = 'Cholesterol_over_HDL'
kp2FinalNameDict['ALK PHOS'] = 'ALKP'
kp2FinalNameDict['CK-TOTAL'] = 'CK'
kp2FinalNameDict['FASTING GLUCOSE'] = 'Glucose'
kp2FinalNameDict['ALK PHOS'] = 'ALKP'
kp2FinalNameDict['TOTAL BILIRUBIN'] = 'Bilirubin'
kp2FinalNameDict['DIRECT LDL'] = 'LDL'
kp2FinalNameDict['VITAMIN B12'] = 'B12'
kp2FinalNameDict['GAMMA GT'] = 'GGT'
kp2FinalNameDict['CO2 TOTAL'] = 'CO2'
kp2FinalNameDict['DIRECT LDL'] = 'LDL'
kp2FinalNameDict['BILI TOTAL'] = 'Bilirubin'
kp2FinalNameDict['SGPT (ALT)'] = 'ALT'
kp2FinalNameDict['DIRECT HDL'] = 'HDL'
kp2FinalNameDict['BILI 1 MIN DIRECT'] = 'DirectBilirubin'
kp2FinalNameDict['TIBC'] = 'TIBC'
kp2FinalNameDict['Total Amylase'] = 'Amylase'
kp2FinalNameDict['BILI DIRECT'] = 'DirectBilirubin'
kp2FinalNameDict['FOLATE (FOLIC ACID)'] = 'Follic_Acid'
kp2FinalNameDict['BLOOD AMYLASE'] = 'Amylase'
kp2FinalNameDict['TRIGLYCERIDES'] = 'Triglycerides'
kp2FinalNameDict['VITAMIN B12'] = 'B12'
kp2FinalNameDict['BILI TOTAL'] = 'Bilirubin'
kp2FinalNameDict['HEMOGLOBIN A1C'] = 'HbA1C'
kp2FinalNameDict['GLUCOSE'] = 'RandomGlucose'
kp2FinalNameDict['SERUM CALCIUM'] = 'Ca'
kp2FinalNameDict['FBS'] = 'Glucose'
kp2FinalNameDict['ALK PHOS'] = 'ALKP'
kp2FinalNameDict['TOTAL BILIRUBIN'] = 'Bilirubin'
kp2FinalNameDict['TIBC'] = 'TIBC'
kp2FinalNameDict['CALCULATED LDL'] = 'LDL'
kp2FinalNameDict['CHOL/HDL RATIO'] = 'Cholesterol_over_HDL'
kp2FinalNameDict['DIRECT HDL'] = 'HDL'
kp2FinalNameDict['TRIGLYCERIDES'] = 'Triglycerides'
kp2FinalNameDict['DIRECT HDL'] = 'HDL'
kp2FinalNameDict['DIRECT LDL'] = 'LDL'
kp2FinalNameDict['ALT/SGPT'] = 'ALT'
kp2FinalNameDict['DIRECT BILIRUBIN'] = 'DirectBilirubin'
kp2FinalNameDict['AST/SGOT'] = 'AST'
kp2FinalNameDict['VITAMIN D, 25-OH D2'] = 'VitaminD_25'
kp2FinalNameDict['VITAMIN D, 25-OH D3'] = 'VitaminD_25'
kp2FinalNameDict['VITAMIN D, 25-OH TOT'] = 'VitaminD_25'
kp2FinalNameDict['FASTING GLUCOSE'] = 'Glucose'
kp2FinalNameDict['TOTAL CK'] = 'CK'
kp2FinalNameDict['TIBC'] = 'TIBC'
kp2FinalNameDict['TRIGLYCERIDES'] = 'Triglycerides'


kp2FinalNameDict['ICD9_Diagnosis'] = 'ICD9_Diagnosis'
kp2FinalNameDict['ICD9_Hospitalization'] = 'ICD9_Hospitalization'
kp2FinalNameDict['Lung_Cancer'] = 'Lung_Cancer' # Added Manually
kp2FinalNameDict['site_desc'] = 'Lung_Cancer_Location'
kp2FinalNameDict['TUMOR_SIZE'] = 'Lung_Cancer_Size'
kp2FinalNameDict['stage'] = 'Lung_Cancer_Stage'
kp2FinalNameDict['t_value'] = 'Lung_Cancer_T_Value'
kp2FinalNameDict['n_value'] = 'Lung_Cancer_N_Value'
kp2FinalNameDict['m_value'] = 'Lung_Cancer_M_Value'
kp2FinalNameDict['histology'] = 'Lung_Cancer_Type'
kp2FinalNameDict['SEQUENCE_NUMBER'] = 'Lung_Sequence_Number'

kp2FinalNameDict['BMI'] = 'BMI'
kp2FinalNameDict['TOBACCO_USER'] = 'Smoking_Status'
kp2FinalNameDict['smoking_quit_date'] = 'Smoking_Quit_Date'
kp2FinalNameDict['pkyr'] = 'Pack_Years'
kp2FinalNameDict['ALCOHOL_USER'] = 'Alcohol_Status'
kp2FinalNameDict['FEV1_PERCENT_PREDICTED'] = 'Fev1'
kp2FinalNameDict['FEV1_FVC'] = 'Fev1/Fvc'


#kp2FinalNameDict['NA'] = 'ICD9_Diagnosis'
#kp2FinalNameDict['NA'] 

# 'IRON SAT' 1 Occur
# 'SERUM SPECIMEN' 1 Occur 
#ttt = dfControlLab['component2']
#tt = ttt.value_counts()
#tt['APTT']

# Create oppsoite dict
for k,v in kp2FinalNameDict.items():
    if v in finalName2KpDict:
        finalName2KpDict[v].append(k)
    else:
        finalName2KpDict[v] = [k]

generatedFinalNames = {'BYEAR','TRAIN'}       

##################################################################################################
# Signals Taken from THIN
##################################################################################################

kpSecDict['Demographic'] = {'GENDER','BYEAR','BDATE','STARTDATE','ENDDATE','DEATH','TRAIN','PRAC','Censor'}
kpSecDict['Weight related'] = {'Weight','Height','BMI'}
kpSecDict['Rock & Roll'] = {'ALCOHOL','SMOKING','STOPPED_SMOKING','SMOKING_ENRICHED'}
kpSecDict['BP'] = {'BP','PULSE'}
kpSecDict['Lab Tests - Blood counts (CBC)'] = {'Hemoglobin','RBC','Hematocrit','Platelets','WBC',
            'MCH','MCHC-M','MCV','Eosinophils#','Monocytes#','Basophils#','Lymphocytes#','Neutrophils#',		
            'Eosinophils%','Monocytes%','Basophils%','Lymphocytes%','Neutrophils%','MPV','PDW','PlasmaViscosity',
            'Platelets_Hematocrit','INR','RDW'}

kpSecDict['Lab Tests - Biochem - Urine'] = {'UrineTotalProtein','UrineAlbumin','UrineCreatinine','UrineAlbumin_over_Creatinine'}
kpSecDict['Lab tests - Biochem - Iron and Vitamins related'] = {'Iron_Fe','Ferritin','B12',
         'VitaminD_25','Transferrin'}
kpSecDict['Lab Tests - Biochem - Cholesterol and cardio related'] = {'Cholesterol','Triglycerides','LDL','HDL',
         'NonHDLCholesterol','HDL_over_nonHDL','HDL_over_Cholesterol','HDL_over_LDL',
         'Cholesterol_over_HDL','CK','LDL_over_HDL'}

kpSecDict['Lab Tests - Biochem - Renal Related'] = {'Creatinine','Urea','eGFR','Uric_Acid	','eGFR_MDRD','eGFR_CKD_EPI','GFR'}
kpSecDict['Lab Tests - Biochem - Diabetic related'] = {'Glucose','HbA1C','RandomGlucose','Fructosamine'}
kpSecDict['Lab Tests - Biochem - Hepatic'] = {'ALT','AST','GGT','LDH','ALKP','Bilirubin','Albumin',
         'Protein_Total'}

kpSecDict['Lab Tests - Biochem - ions'] = {'Na','K+','Ca','CorrectedCa','Cl','Lithium','Mg','Phosphore',
                                             'Bicarbonate','SerumAnionGap','PlasmaAnionGap'}

kpSecDict['Lab Tests - Biochem - others'] = {'FreeT3','FreeT4','T4','CO2','Digoxin','Globulin','Amylase','Testosterone',
                                             'Fibrinogen','Prolactin','LuteinisingHormone	','PSA',
                                             'Follic_Acid','PFR','CRP','TSH','CA125','FSH',
                                             'Progesterone'}
kpSecDict['Indications'] = set()
kpSecDict['Lung Cancer'] = set()
kpSecDict['Other']= set()

##################################################################################################
# Adding Additional Signals in KP 
##################################################################################################

kpSecDict['Demographic'] = kpSecDict['Demographic'].union({'Race','Marital','Income','Education','INDEXDATE'})
kpSecDict['Lab Tests - Biochem - Hepatic'] = kpSecDict['Lab Tests - Biochem - Hepatic'].union({'DirectBilirubin'})
kpSecDict['Indications'] = kpSecDict['Indications'].union({'ICD9_Diagnosis', 'ICD9_Hospitalization'})
kpSecDict['Lung Cancer'] = kpSecDict['Lung Cancer'].union({'Lung_Cancer','Lung_Cancer_Location', 'Lung_Cancer_Size','Lung_Cancer_Stage','Lung_Sequence_Number','Lung_Cancer_T_Value','Lung_Cancer_N_Value','Lung_Cancer_M_Value','Lung_Cancer_Type'})
kpSecDict['Other'] = kpSecDict['Other'].union({'Fev1','Fev1/Fvc'})
kpSecDict['Rock & Roll'] = kpSecDict['Rock & Roll'].union({'Smoking_Quit_Date','Alcohol_Status','Smoking_Status','Pack_Years'})
##################################################################################################
# Create Numbering Dict
##################################################################################################

# Create Map For THIN :
sections = ['Demographic', 'Weight related','Rock & Roll', 'BP','Lab Tests - Blood counts (CBC)','Lab Tests - Biochem - Urine','Lab tests - Biochem - Iron and Vitamins related',
            'Lab Tests - Biochem - Cholesterol and cardio related','Lab Tests - Biochem - Renal Related','Lab Tests - Biochem - Diabetic related','Lab Tests - Biochem - Hepatic',
            'Lab Tests - Biochem - ions','Lab Tests - Biochem - others','Indications','Lung Cancer','Other']

startDict = {'Demographic': 100, 'Weight related': 900, 'Rock & Roll': 910, 
             'BP':920, 'Lab Tests - Blood counts (CBC)' : 1000, 'Lab Tests - Biochem - Urine': 1030,
             'Lab tests - Biochem - Iron and Vitamins related':1050,  'Lab Tests - Biochem - Cholesterol and cardio related':1060,
             'Lab Tests - Biochem - Renal Related':1080,'Lab Tests - Biochem - Diabetic related':1090, 'Lab Tests - Biochem - Hepatic':1100,
             'Lab Tests - Biochem - ions': 1110, 'Lab Tests - Biochem - others': 1200, 'Indications': 2300 ,'Lung Cancer': 2400,'Other' : 3000}            

##################################################################################################
# Create Numbering Dict (could be dobe automaically)
##################################################################################################
finalName2Type = dict()
kpSec2defaultType = {'Demographic': '0', 'Weight related': '1', 'Rock & Roll': '1', 
             'BP':'8', 'Lab Tests - Blood counts (CBC)' : '1', 'Lab Tests - Biochem - Urine': '1',
             'Lab tests - Biochem - Iron and Vitamins related': '1',  'Lab Tests - Biochem - Cholesterol and cardio related': '1',
             'Lab Tests - Biochem - Renal Related': '1','Lab Tests - Biochem - Diabetic related': '1', 'Lab Tests - Biochem - Hepatic': '1',
             'Lab Tests - Biochem - ions': '1', 'Lab Tests - Biochem - others': '1', 'Indications': '1' ,'Lung Cancer': '1' ,'Other' : '1'}            

for section in sections:
    for finalName in kpSecDict[section]:
        finalName2Type[finalName] = kpSec2defaultType[section]
    
# Overrides:
finalName2Type['ICD9_Hospitalization'] = '3' # range
#finalName2Type['Smoking_Quit_Date'] = '4' # Time stamp
 
##################################################################################################
# Create KP values Dict for categorial (could be dobe automaically?)
##################################################################################################

kpName2transDict['GENDER'] = collections.OrderedDict([('M','1'), ('F', '2')])
kpName2transDict['race'] = collections.OrderedDict([('Asian','1'), ('Black', '2'), ('Hispanic','3'), ('White', '4'),('Other', '5')])
kpName2transDict['ALCOHOL_USER'] = collections.OrderedDict([('No', '0'), ('Yes', '1')])
kpName2transDict['TOBACCO_USER'] = collections.OrderedDict([('Never','0'), ('Passive','1'), ('Quit','2'), ('Yes','3')])
kpName2transDict['marital'] = collections.OrderedDict([('Never married' , '0'),('Married or living as married' , '1'), ('Widowed', '2'), ('Separated','3'), ('Divorced','4'), ('Other','5')])
kpName2transDict['education'] =  collections.OrderedDict([('Less than high school' , '1'),('Some high school' , '2'), ('High school graduate', '3'), ('Some college, no degree','4'), ("Associate's degree",'5'), ("Bachelor's degree",'6'), ("Graduate degree",'7')])

# 
##################################################################################################
# Define values considered to be unknown
##################################################################################################

ignoredValuesSet = {'Lung_Cancer_Location' : {'Lung, NOS'}, 'Lung_Cancer_Stage' : {'Stage Unknown','Not Applicable'},
                    'Lung_Cancer_Size' : {'960','990','991','992','993','994','995','996','997','998','999'},
                    'Lung_Cancer_N_Value' : {'NA'}, 'Lung_Cancer_T_Value' : {'NA'}, 'Lung_Cancer_M_Value' : {'NA'} }

##################################################################################################
# Define Sets
##################################################################################################


finalName = 'Lung_Cancer_Location'
kpSecDict['Lung Cancer']

final2SetsDict = dict()
final2SetsDict['Lung_Cancer_Stage'] = {'Stage I Set' : {'Stage I' ,'Stage IA',  'Stage IB'}, 'Stage II  Set' : {'Stage II','Stage IIA',  'Stage IIB'}, 'Stage III Set' : {'Stage III','Stage IIIA', 'Stage IIIB', 'Stage IIIC'}}
final2SetsDict['Lung_Cancer_T_Value'] = {'T1_Set' : {'T1','T1a',  'T1b', 'T1 NOS'}, 'T2 Set' : {'T2', 'T2a','T2b','T2 NOS'}}
final2SetsDict['Lung_Cancer_M_Value'] = {'M1_Set' : {'M1', 'M1 NOS', 'M1a', 'M1b'}}


##################################################################################################
# Create KP convertion function dictionary
##################################################################################################
kpName2ConvFuncDict = dict()   
kpName2ConvFuncDict['race'] = int
kpName2ConvFuncDict['education'] = int
kpName2ConvFuncDict['Marital'] = int


##################################################################################################
# Final Name to creation function
##################################################################################################
finalName2func = dict()
finalName2func['Demo'] ={'GENDER','BYEAR','BDATE' , 'STARTDATE' ,'ENDDATE','DEATH','TRAIN','Income','INDEXDATE' }
finalName2func['Categorial'] = {'Education','Marital','Race','Alcohol_Status','Smoking_Status','Lung_Cancer_N_Value','Lung_Cancer_Stage','Lung_Cancer_M_Value','Lung_Cancer_Type',
 'Lung_Cancer_Location','Lung_Cancer_T_Value' }
finalName2func['CategorialNoDict'] = {'BMI', 'Lung_Sequence_Number','Lung_Cancer', 'Lung_Cancer_Size','Pack_Years', 'Smoking_Quit_Date', 'Fev1', 'Fev1/Fvc'}
finalName2func['DxFile'] = {'ICD9_Diagnosis'}
finalName2func['HospFile'] = {'ICD9_Hospitalization'}

##################################################################################################
# Gen Number for final signal name
##################################################################################################

# Parse THIN Signals Map : Sig -> Number:

with open(filenameThinSignals, 'r') as f:
   # Read the file contents and generate a list with each line
   lines = f.readlines()

thinName2Num = dict()
num2FinalNames = dict()

for line in lines:
    linesplit = line.strip().split('\t')
    if len(linesplit) > 3:
        name  = linesplit[1]
        num = linesplit[2]
        sigType = linesplit[3]
        thinName2Num[name] = num
        
finalName2num = dict()
for section in sections:
    currNum = startDict[section]
    usedNums = set()
    
    if section in kpSecDict:
        # locate fixed signals first
        for finalName in kpSecDict[section]:
            if (finalName in (set(kp2FinalNameDict.values()).union(generatedFinalNames))) and (finalName in thinName2Num):
                # pick only existing signals in KP and generated:
                finalName2num[finalName] = thinName2Num[finalName]                
                usedNums.add(finalName2num[finalName])
        
        # locate new signals
        for finalName in kpSecDict[section]:
            if (finalName in (set(kp2FinalNameDict.values()).union(generatedFinalNames))) and not(finalName in thinName2Num):
                while str(currNum) in usedNums:
                    currNum += 1
                # pick only existing signals in KP:
                finalName2num[finalName] = str(currNum)                
                usedNums.add(finalName2num[finalName])
        
            
            
num2FinalNames = {v:k for k,v in finalName2num.items()}

 

def genSecSignals(finalNames,finalName2num,finalName2Type,kpName2Desc,generatedFinalNames):
    numsPerSec = [int(finalName2num[finalName]) for finalName in finalNames]
    sortedNumsPerSec = np.sort(numsPerSec)
    outStr = ""   
    for num in sortedNumsPerSec:
        finalName = num2FinalNames[str(num)]
        outStr += "SIGNAL\t"+ finalName + "\t"  + str(num) + "\t" + finalName2Type[finalName] + "\t"
        if not(finalName in generatedFinalNames):
            kpName = finalName2KpDict[finalName][0] # assuming no more than 1.
            if kpName in kpName2Desc:
                print(kpName)
                outStr += kpName2Desc[kpName]
#        
        outStr += "\n"
    return outStr

def genSignalsFilePreamble():
    outStr = ""
    outStr += "#===============================================================================\n"
    outStr += "\n"
    outStr += "# Signal Types \n"
    outStr += "# 0 - Value (32bit) \n"
    outStr += "# 1 - Date (32bit) + Value (32bit) \n"
    outStr += "# 2 - Time (64bit) + Value (32bit) \n"
    outStr += "# 4 - 64 bits of data (mainly for time stamps) \n"
    outStr += "# 3 - RangeDate (32bit + 32bit) + Value (32bit) \n"
    outStr += "# 8 - DateShort2 (32 bit int + 16bit short + 16 bit short) \n"
    outStr += "#10 - ValShort4 : 4 x short values \n"
    return outStr

def genSecHeadline(sectionName):
    outStr = ""
    outStr += "#===============================================================================\n"
    outStr += "# " + sectionName + "\n" 
    outStr += "#===============================================================================\n"
    return outStr

def isDate(string):   
    pattern = '[0-9][0-9]/[0-9][0-9]/[0-9][0-9][0-9][0-9]'
    if re.match(pattern,string):
        return True
    else:
        return False

def convertDateToIntDate(string):
    return string[6:] + string[0:2] + string[3:5]

def genTrainNum():
    prob_1 = 0.6
    prob_2 = 0.2
    prob_3 = 1- (prob_2 + prob_1)
    r = random.random()
    if (r <= prob_1):
        return 1
    if (r <= prob_1 + prob_2):
        return 2
    return 3    

def genDemoSignalFile(finalNames, filename, df):
    # Generate Demo File
    outStr = ""  
    kpNames = [finalName2KpDict[name][0] for name in finalNames if name in finalName2KpDict]
    for index, row in df.iterrows():
        for name in kpNames:
            if (row[name] == row[name]): # check if exists
                if name in kpName2transDict:
                    if (row[name] in kpName2transDict[name]):
                        value = kpName2transDict[name][row[name]]
                    else: 
                        print(row[name] + ' value not written for ' + name)
                else:
                    value = row[name]
                    
                if name in kpName2ConvFuncDict:
                    value = kpName2ConvFuncDict[name](value)
                
                if isDate(str(value)):
                    value = convertDateToIntDate(str(value))
                
                outStr += str(row['id']) + "\t" + kp2FinalNameDict[name] + "\t" + str(value) + "\n"
        # Gen BYEAR signal
        outStr += str(row['id']) + "\t" +'BYEAR' + "\t" + str(int(int(convertDateToIntDate(str(row[finalName2KpDict['BDATE'][0]])))/10000)) + "\n"
        # Gen TRAIN signal
        outStr += str(row['id']) + "\t" +'TRAIN' + "\t" + str(genTrainNum()) + "\n"
    with open(outputDir + filename, "wb") as text_file:
        text_file.write(str.encode(outStr))

def is_number(s):    
    try:
        x= float(s)
        return (x == x) # check that it's non NaN
    except:
        return False
    
def genNumSignalFile(finalName,finalName2KpDict,dfList):
    # quit if exists
    filename = re.sub('[^\w_#%]','',finalName) + '.txt'  
    if os.path.isfile(outputDir + filename):
        if (os.stat(outputDir + filename).st_size > 0):
            return
    
    outStr = ""
    # search in datarames
    badCntr = 0
    for df in dfList:
        if ("component2" not in df):
            continue
        gbComp = df.groupby('component2')
        kpNames = set(finalName2KpDict[finalName]).intersection(set(df.component2.unique()))   
        print(kpNames)
        #zz  = pd.concat( [gbComp.get_group(group[0]) for group in gbComp if group[0] in kpNames]).sort_index()
        
        if len(kpNames) > 0:
            new_gb = pd.concat( [gbComp.get_group(group[0]) for group in gbComp if group[0] in kpNames]).sort_values(by = 'id')
            
            for index, row in new_gb.iterrows():
                kpName = row['component2']
                date = convertDateToIntDate(row['order_date'])
                value = str(row['value2'])
                if is_number(value):
                    unit = str(row['unit2'])
                    outStr += str(row['id']) + "\t" + finalName + "\t" + date + "\t" + value + "\t" + kpName + "\t" + unit + "\n"
                else:
                    badCntr += 1
                    print("Removed not a number: " + str(badCntr) + " " + row['id'] + " " + kpName + " " + value)
                    
                    
 
    with open(outputDir + filename, "wb") as text_file:
        text_file.write(str.encode(outStr))

def genNumSignalFileByCol(finalName,finalName2KpDict,dfList):
    # Extract filename:
    filename = re.sub('[^\w_#%]','',finalName) + '.txt'  
    if os.path.isfile(outputDir + filename):
        if (os.stat(outputDir + filename).st_size > 0):
            return
                    
    outStr = ""
    # search in datarames
    badCntr = 0
    for df in dfList:
        kpName = finalName2KpDict[finalName][0]
        if (kpName not in df):
            continue
        
        print('hi')
        for index, row in df.iterrows():
            kpNameStr = kpName
            date = convertDateToIntDate(row['measure_date'])
            value = str(row[kpName])
            if is_number(value):
                outStr += str(row['id']) + "\t" + finalName + "\t" + date + "\t" + value + "\t" + kpNameStr + "\n"
            else:
                badCntr += 1
                print("Removed not a number: " + str(badCntr) + " " + row['id'] + " " + kpName + " " + value)
                

    with open(outputDir + filename, "wb") as text_file:
        text_file.write(str.encode(outStr))


def genDxSignalFile(finalName,dfList,ignore_dict,code_map,icd102icd9Dict):
    # Extract filename:
    filename = re.sub('[^\w_#%]','',finalName) + '.txt'   
    if os.path.isfile(outputDir + filename):
        if (os.stat(outputDir + filename).st_size > 0):
            return
    
    outStr = ""
    # search in datarames
    for df in dfList:
        # Check The DxFile by exists adate col but not ddate ()
        if ('adate' in df.columns) and (not('ddate' in df.columns)):       
            for index, row in df.iterrows():
                date = convertDateToIntDate(row['adate'])
                
                KP_code_decr = str(row['CODE_DESC'])
                value = str(row['CODE'])
                if value in ignore_dict:
                    print('Code : ' + value + ' Description : ' + ignore_dict[value] + ' ignored' ) 
                    continue
                if  row['CODE_SUBTYPE'] == 'ICD10':                
                    value = icd102icd9Dict[value]
                
                my_code_descr = str(code_map[value])
                
                outStr += str(row['id']) + "\t" + finalName + "\t" + date + "\t" + value + "\t" + KP_code_decr + "\t" + my_code_descr + "\n"
                
            
    
    with open(outputDir + filename, "wb") as text_file:
        text_file.write(str.encode(outStr))

def genHospSignalFile(finalName,dfList,ignore_dict,code_map,icd102icd9Dict):
    # Extract filename:
    filename = re.sub('[^\w_#%]','',finalName) + '.txt'   
    if os.path.isfile(outputDir + filename):
        if (os.stat(outputDir + filename).st_size > 0):
            return
    outStr = ""
    # search in datarames
    for df in dfList:
        # Check The HospFile by exists adate col and ddate col()
        if (('adate' in df.columns) and ('ddate' in df.columns)):       
            for index, row in df.iterrows():
                try:
                    date_start = convertDateToIntDate(row['adate'])
                    date_end = convertDateToIntDate(row['ddate'])
                    KP_code_decr = str(row['CODE_DESC'])
                    value = str(row['CODE'])           
        
                    if value in ignore_dict:
                        print('Code : ' + value + ' Description : ' + ignore_dict[value] + ' ignored' ) 
                        continue
                    if  row['CODE_SUBTYPE'] == 'ICD10':                
                        value = icd102icd9Dict[value]
                    
                    my_code_descr = str(code_map[value])
                    
                    outStr += str(row['id']) + "\t" + finalName + "\t" + date_start + "\t" + date_end + "\t"  + value + "\t" + KP_code_decr + "\t" + my_code_descr + "\n"
                except:
                    print(finalName + ' Bad Row: ' + ' '.join(row.to_string().split()))
                    
            
 
    with open(outputDir + filename, "wb") as text_file:
        text_file.write(str.encode(outStr))
        
def convertName(value,charsToRemove):
    if value == value: #  check that it non nan
        convertedValue = "_".join(value.split())
        convertedValue = re.sub(charsToRemove,'',convertedValue)
        return convertedValue
    else:
        return value
  
def genCategorialFiles(finalName, outputDir, charsToRemove, timeColName, kpName2transDict, ignoredValuesSet, final2SetsDict, printDictFile, dfList): 
    # Generate Dictionary
    value2numDict = dict()
    num2valueDict = dict()
    fileNameDict = outputDir + 'dict.' + finalName
    fileNameData = outputDir +  convertName(finalName,charsToRemove) + '.txt'
    #fileNameDict = 'temp.txt'
    #fileNameData = 'temp2.txt'
 
    if os.path.isfile(fileNameData):
        if (os.stat(fileNameData).st_size > 0):
            return
    
    # Generate File 
    outStr = ""  
    kpName = finalName2KpDict[finalName][0]
    for df in dfList:
        if not (kpName in df.columns):
            continue
        
        genDict(df,finalName, kpName2transDict, ignoredValuesSet, final2SetsDict, fileNameDict, charsToRemove, value2numDict, num2valueDict, printDictFile) 
        for index, row in df.iterrows():
            origValue = row[kpName]
            value = convertName(origValue,charsToRemove) 
            
            if value in value2numDict: # Check that value in dicionary
                valueToPrint = value
            elif value in num2valueDict:
                valueToPrint = num2valueDict[value]
            else:
                print(kpName + ': not found ' + str(value))
                continue
            # if value is date, convert to repo format
            if isDate(origValue):
                valueToPrint = convertDateToIntDate(origValue)
                
            if (finalName2Type[finalName] == '1'):
                outStr += str(row['id']) + "\t" + finalName + "\t" + convertDateToIntDate(row[timeColName]) + '\t' + str(valueToPrint) + "\n"
            elif (finalName2Type[finalName] == '0'):
                outStr += str(row['id']) + "\t" + finalName + "\t" + str(valueToPrint) + "\n"
            elif  (finalName2Type[finalName] == '4'):
                outStr += str(row['id']) + "\t" + finalName + "\t" + convertDateToIntDate(row[kpName]) + "\n"
            else:
                print('Error in ' + str(row))
            
        with open(fileNameData, "wb") as text_file:
            text_file.write(str.encode(outStr))
            
#def checkIfCategorial():
    

     
def genDict(df, finalName, kpName2transDict, ignoredValuesSet, final2SetsDict, fileNameDict, charsToRemove, value2numDict, num2valueDict, printDictFile):       
    kpName = finalName2KpDict[finalName][0]
    uniqueVals = df[kpName].unique()      
    outStr = ""
    outStr = "SECTION"+"\t" + finalName + "\n"
    
    uniqueValsCleanedSet = set(uniqueVals) - {np.nan}
    # Remove Ignored Values (like unknown, etc.)
    if finalName in ignoredValuesSet:
        uniqueValsCleanedSet = uniqueValsCleanedSet - ignoredValuesSet[finalName]
        
    uniqueValsSorted = sorted(list(uniqueValsCleanedSet))
        
    # add sets in the end
    if finalName in final2SetsDict:
        uniqueValsSorted = uniqueValsSorted + sorted(list(final2SetsDict[finalName].keys()))
    
    if (kpName not in kpName2transDict):    
        currNum = 1
        for value in uniqueValsSorted:            
            convertedValue = convertName(value,charsToRemove)
            outStr += "DEF" + "\t" + str(currNum) + "\t" + convertedValue + "\n"
            value2numDict[convertedValue] = str(currNum)
            num2valueDict[str(currNum)] = convertedValue
            
            currNum += 1
    else:
        for key,value in kpName2transDict[kpName].items():
            convertedValue = convertName(key,charsToRemove)
            currNum = value
            outStr += "DEF" + "\t" + str(currNum) + "\t" + convertedValue + "\n"
            value2numDict[convertedValue] = str(currNum)
            num2valueDict[str(currNum)] = convertedValue
            
    # Add Sets:
    if finalName in final2SetsDict:    
        for dictSetParent in final2SetsDict[finalName]:
            sorted_children = sorted(final2SetsDict[finalName][dictSetParent])
            for child in sorted_children:
                outStr += "SET" + "\t" + convertName(dictSetParent, charsToRemove) + "\t" + convertName(child,charsToRemove) + "\n"
    if printDictFile:     
        with open(fileNameDict, "wb") as text_file:
            text_file.write(str.encode(outStr))
        
# Run Main 
ignore_dict = dict()
code_map = dict()        
icd92icd10Dict = dict()
icd102icd9Dict = dict()

icd9dict.genIcd9Map(ignore_dict, code_map, outputDir + 'dict.icd9')
icd9dict.icd9icd10conversion3(icd92icd10Dict, icd102icd9Dict)
    
outStr = genSignalsFilePreamble()

secCnt = 0
# TEMP!!!
#kpSecDict['Lab Tests - Blood counts (CBC)'] = {'Eosinophils#','Basophils#',		
#            'Eosinophils%','Basophils%'}
#
#kpSecDict = {'Lab Tests - Blood counts (CBC)' : kpSecDict['Lab Tests - Blood counts (CBC)'] }
#kpSecDict.pop('Lab Tests - Blood counts (CBC)')

for section in kpSecDict:
     print('Done: ' + str(secCnt) + ' out of ' + str(len(kpSecDict)) )
     outStr =  outStr + genSecHeadline(section)
     finalNames = set(kpSecDict[section]).intersection(set(kp2FinalNameDict.values())) # Files that are taken from Databaste
     finalNamesToSigFile = set(kpSecDict[section]).intersection(set(kp2FinalNameDict.values()).union(generatedFinalNames))# Signal names for .signal file
     outStr = outStr + genSecSignals(finalNamesToSigFile,finalName2num,finalName2Type,kpName2Desc,generatedFinalNames)
     
     if (section == 'Demographic'):
         #genDemoSignalFile(finalName2func['Demo'],'kp_demographic.txt',dfDemo) Don't gen demogrphic because of TRAIN flag.
         finalNames = finalNames - finalName2func['Demo']
     
     for finalName in finalNames:
         if finalName in finalName2func['Categorial']:
             if (section == 'Lung Cancer'):
                 timeColName = 'index_date' 
             else:
                 timeColName = 'measure_date'        
             if finalName2Type[finalName] == '0': # No Time stamp
                timeColName = None
             printDictFile = True      
             genCategorialFiles(finalName, outputDir, charsToRemove, timeColName, kpName2transDict, ignoredValuesSet, final2SetsDict,printDictFile,  dfList)
             pass
         
         elif finalName in finalName2func['CategorialNoDict']:
             if (section == 'Lung Cancer'):
                 timeColName = 'index_date' 
             else:
                 timeColName = 'measure_date'
             printDictFile = False
             genCategorialFiles(finalName, outputDir, charsToRemove, timeColName, kpName2transDict, ignoredValuesSet, final2SetsDict,printDictFile,  dfList)
             pass
         
         elif finalName in finalName2func['DxFile']:
#             genDxSignalFile(finalName,dfList,ignore_dict,code_map,icd102icd9Dict)
             pass
         elif finalName in finalName2func['HospFile']:
#             genHospSignalFile(finalName,dfList,ignore_dict,code_map,icd102icd9Dict) 
             pass
         else:
             genNumSignalFile(finalName,finalName2KpDict,dfList)
             pass
        
     secCnt += 1                 
             
 # write string to file:
with open(outputDir + "kp.signals", "wb") as text_file:
    text_file.write(str.encode(outStr))       

                
         
        
         
        
        

## run over sections
#for section in kpSecDict:
#   outStr =  outStr + genSecHeadline(section)
#   finalNames = set(kpSecDict[section]).intersection(set(kp2FinalNameDict.values())) # Files that are taken from Databaste
#   finalNamesToSigFile = set(kpSecDict[section]).intersection(set(kp2FinalNameDict.values()).union(generatedFinalNames))# Signal names for .signal file
#   outStr = outStr + genSecSignals(finalNamesToSigFile,finalName2num,finalName2Type,kpName2Desc,generatedFinalNames)
#   
#   if (section == 'Demographic'):
#       # This is Temp until vectors are received:
#       finalNames = finalNames.union(set(kpSecDict['Rock & Roll']).intersection(set(kp2FinalNameDict.values())))
#       finalNames = finalNames.union(set(kpSecDict['Other']).intersection(set(kp2FinalNameDict.values())))
##      genDemoSignalFile(finalNames,'kp_demographic.txt',dfDemo)
##       
#       pass
#   elif (section == 'Indications'):
##       for finalName in finalNames:
##           if (finalName == 'ICD9_Diagnosis'):
##               genDxSignalFile(finalName,dfList,ignore_dict,code_map,icd102icd9Dict)
##           if (finalName == 'ICD9_Hospitalization'):
##               genHospSignalFile(finalName,dfList,ignore_dict,code_map,icd102icd9Dict)  
##          
#       pass                
#   elif (section == 'Weight related'):
#       finalNames = finalNames.union(set(kpSecDict['Weight related']).intersection(set(kp2FinalNameDict.values())))
#       for finalName in finalNames:
#           genNumSignalFileByCol(finalName,finalName2KpDict,dfList)
#       pass
#   
#   elif (section == 'Lung Cancer'):
##       dfCaseTumorLungCancerSig = dfCaseTumor.copy()
##       dfCaseTumorLungCancerSig['Lung_Cancer'] = '1'
##       for finalName in finalNames:
##            timeColName = 'index_date'
##            genCategorialFiles(finalName, outputDir, charsToRemove, timeColName, ignoredValuesSet, final2SetsDict, dfCaseTumorLungCancerSig)
#           pass
#               
#   elif (section == 'Rock & Roll'):   
#       pass
#   
#   else: # All numreic tests
#       for finalName in finalNames:
#           if (finalName == 'Fev1/Fvc') or (finalName == 'Fev1'):
#               genNumSignalFileByCol(finalName,finalName2KpDict,dfList)
#           else:
##               genNumSignalFile(finalName,finalName2KpDict,dfList)
#               pass
#           
#          


        

     
                
                
                
    
    
    
    


















    