# -*- coding: utf-8 -*-
"""
Created on Wed Jul  4 12:32:05 2018

@author: Ron
"""

import testGroupingDicts
import pandas as pd
import numpy as np
from datetime import datetime, date, time,timedelta
import matplotlib.pyplot as plt

def numberOfRelPatients(df,caseControlType,years, plotFigs = False):
    fiveYears = timedelta(days = 5*365)
    df['year'] = df.apply(lambda row: row.index_date[6:], axis = 1)
    #df['mem_start_int'] =  df.apply(lambda row: int(row.index_date[6:] + row.index_date[0:2] +row.index_date[3:5] ), axis = 1)
    df['mem_start_date'] =  df.apply(lambda row: date(int(row.mem_start[6:]),int(row.mem_start[0:2]),int(row.mem_start[3:5])  ), axis = 1)
    df['start_index_date'] =  df.apply(lambda row: date(int(row.index_date[6:]),int(row.index_date[0:2]),int(row.index_date[3:5])  )- fiveYears, axis = 1)
    df['maxStartDate'] = df.apply(lambda row: row['start_index_date'] if row['mem_start_date'] < row['start_index_date'] else  row['mem_start_date'] ,axis = 1)
    
    for year in years:
        df[year] = 0.0
    
    for ind,row in df.iterrows():
        for year in range(row['maxStartDate'].year+1,int(row['year'])):
            df.at[ind,str(year)] = 1
        
        daysInYearLast = 30*(int(row.index_date[0:2])-1) + int(row.index_date[3:5] )
        partialLast = daysInYearLast/365
        df.at[ind,row.year] =  partialLast
        
        daysInYearFirst = (row['maxStartDate'].month - 1)*30 + row['maxStartDate'].day
        df.at[ind,str(row['maxStartDate'].year)] = 1 - daysInYearFirst/365
        
    patInYear = dict()
    for year in years:
        patInYear[year] = df[year].sum()
    if plotFigs:  
        plt.figure()
        pd.Series(patInYear).sort_index().plot(kind='bar')
        plt.title(caseControlType + "s -Rel. Patients per year ")
    return pd.Series(patInYear)

def numTestsPerYear(df,patInYear, caseControlType , plotFigs = False):
    df['year'] = df.apply(lambda row: row.order_date[6:], axis = 1)
    df['testsGroup'] = df['component2'] 
    df['testsGroup'] =  df['testsGroup'].map(testGroupingDicts.testGroupDict)
    years = [str(year) for year in range(2003,2016)]
    
    # remove duplicates tests if on the same test group (for example - don't count Lymphocytes% and Lymphocytes# twice if on the samw test)
    order_proc_id_name = 'order_proc_id' if 'order_proc_id' in df.columns else 'ORDER_PROC_ID'
    dfOnePerTestGroup = df.groupby([order_proc_id_name,'testsGroup'], as_index = False).first()
    
    gbTestGroupYear = dfOnePerTestGroup.groupby(['testsGroup','year']).size()
    
    dfOut = pd.DataFrame([['Patients Per Year','-' ] + np.ndarray.tolist(patInYear.values)], columns = ['Test Group','Type'] + years)
    var = gbTestGroupYear.index.get_level_values('testsGroup').unique()
    testsList = sorted(var, key=lambda v: (v.upper(), v[0].islower()))
    for test in testsList:
            x = gbTestGroupYear[test].index
            y = gbTestGroupYear[test].values
            if plotFigs:
                plt.figure()
                plt.plot(x,y/patInYear[x].values,label = test)
                plt.legend()
                plt.grid()
                plt.title('# of tests per patients per year. '+ caseControlType  +  '. ' + test)
                      
            # write to dataframe
            yStr = [gbTestGroupYear[test][year] if year in gbTestGroupYear[test] else '0' for year in years]
            dfOut = dfOut.append(pd.DataFrame([[test, 'Raw' ] + yStr], columns = dfOut.columns))
            yStr = [float(gbTestGroupYear[test][year])/patInYear[year] if year in gbTestGroupYear[test] else '0' for year in years]
            dfOut = dfOut.append(pd.DataFrame([[test, 'Noralized By Pat.' ] + yStr], columns = dfOut.columns))        
            dfOut = dfOut.append(pd.DataFrame([[test, 'Num tests per pat. - Curr. Year / Prev year ' ] + ['-'] + np.ndarray.tolist(np.array(yStr[1:],dtype=float)/np.array(yStr[0:-1],dtype=float))], columns = dfOut.columns))
     
    return dfOut
    
    
if __name__ == "__main__":
    # Read Files
    sourceDir = 'D:/Databases/kpsc'
    #sourceDir = '/server/Data/kpsc'
    
    fileCaseCbc =  '/15-07-2018/cases_cbc.txt'
    fileControlCbc =  '/15-07-2018/controls_cbc.txt'
    fileControlDemo = '/controls_demo.txt'
    fileCaseDemo = '/cases_demo.txt'
    #fileControlLabList = ['/17-06-2018/controls_lab1.txt','/17-06-2018/controls_lab2.txt','/controls_lab3.txt']
    #fileCaseLab = '/17-06-2018/cases_lab.txt'
    fileControlLabList = ['/20-08-2018/controls_lab1.txt','/20-08-2018/controls_lab2.txt','/20-08-2018/controls_lab3.txt']
    fileCaseLab = '/20-08-2018/cases_lab.txt'


    dfCaseCbc =  pd.read_csv(sourceDir + fileCaseCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
    dfControlCbc =  pd.read_csv(sourceDir + fileControlCbc, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
    dfCaseDemo = pd.read_csv(sourceDir + fileCaseDemo, delimiter = '\t')
    dfControlDemo = pd.read_csv(sourceDir + fileControlDemo, delimiter = '\t') 
    dfControlLabList = []
    for fileControlLab in fileControlLabList:
        dfControlLabList.append(pd.read_csv(sourceDir + fileControlLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)) 
        
    dfControlLab = pd.concat(dfControlLabList)  
    dfCaseLab = pd.read_csv(sourceDir + fileCaseLab, delimiter = '\t',encoding = "ISO-8859-1",dtype = str)

    
    # Generate Active Patients per year
    years = [str(year) for year in range(2003,2016)]
    patInYearCase = numberOfRelPatients(df = dfCaseDemo,caseControlType = 'Case' ,years = years)
    patInYearControl = numberOfRelPatients(df = dfControlDemo,caseControlType = 'Control' ,years = years)
    
    # Check number of tests per year
    writer = pd.ExcelWriter('output_20_08_2018_2.xlsx')
    # CBC:
#    df1 = numTestsPerYear(df = dfCaseCbc,patInYear = patInYearCase, caseControlType = 'Cases')
#    df2 = numTestsPerYear(df = dfControlCbc ,patInYear = patInYearControl, caseControlType = 'Controls')
    df3 = numTestsPerYear(df = dfCaseLab,patInYear = patInYearCase, caseControlType = 'Cases')
    df4 = numTestsPerYear(df = dfControlLab ,patInYear = patInYearControl, caseControlType = 'Controls')
    
     #write to excel:
#    df1.to_excel(writer,'Cases CBC',index = False)
#    df2.to_excel(writer,'Controls CBC',index = False)
    df3.to_excel(writer,'Cases lab',index = False)
    df4.to_excel(writer,'Controls lab',index = False)
    
    # conditional 
    writer.save()
    
#    
#    worksheetCasesLab  = writer.sheets['Cases lab']
#    worksheetCasesLab.conditional_format('D5:O5', {'type':     'cell',
#                                       'criteria': 'between',
#                                       'minimum':  0.5,
#                                       'maximum':  1.5,
#                                       'format':   green_format})
#    
#    worksheetCasesLab.conditional_format('D5:O5', {'type':     'cell',
#                                       'criteria': 'not between',
#                                       'minimum':  0.5,
#                                       'maximum':  1.5,
#                                       'format':   red_format})
#    
#    


        