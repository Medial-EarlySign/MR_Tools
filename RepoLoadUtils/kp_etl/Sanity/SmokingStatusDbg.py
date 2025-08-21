# -*- coding: utf-8 -*-
"""
Created on Thu May 10 09:14:01 2018

@author: Ron
"""

fileControlSmoking = '/03-05-2018/controls_smoking.txt'
dfControlSmoking = pd.read_csv(sourceDir + fileControlSmoking, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
fileCaseSmoking = '/03-05-2018/cases_smoking.txt'
dfCaseSmoking = pd.read_csv(sourceDir + fileCaseSmoking, delimiter = '\t',encoding = "ISO-8859-1",dtype = str) 
dfSmoking = pd.concat([dfCaseSmoking,dfControlSmoking]).sort_values(by = 'id')
dfSmoking['measure_date_int'] = dfSmoking.apply(lambda row: int(row.measure_date[6:] + row.measure_date[0:2] + row.measure_date[3:5]),axis = 1)
dfSmoking['smoking_quit_date_int'] = dfSmoking.apply(lambda row: int(row.smoking_quit_date[6:] + row.smoking_quit_date[0:2] + row.smoking_quit_date[3:5]) if (row.smoking_quit_date == row.smoking_quit_date) else "",axis = 1)
dfSmoking = dfSmoking.groupby('id').apply(lambda x: x.sort_values('measure_date_int',ascending=True))
dfSmoking = dfSmoking.reset_index(drop=True)

# More than 1 smoking quit Date
tt = dfSmoking.groupby('id')['smoking_quit_date'].nunique()
ttt = tt[tt  > 1]

# Smokers with more than 1 pack year
tt = dfCaseSmoking.groupby('id')['pkyr'].nunique()
ttt = tt[tt  > 1]
len(ttt)

# Never Smokers with quit date or pkyears
tt = dfSmoking[(dfSmoking['TOBACCO_USER']=='Never') & (dfSmoking['pkyr'] == dfSmoking['pkyr'])]
tt = dfSmoking[(dfSmoking['TOBACCO_USER']=='Never') & (dfSmoking['smoking_quit_date'] == dfSmoking['smoking_quit_date'])]

dfSmoking['TOBACCO_USER'].unique()

# Smokers with more than 1 status
tt = dfCaseSmoking.groupby('id')['TOBACCO_USER'].nunique()
ttt = tt[tt > 1]
tttt = dfCaseSmoking.loc[dfCaseSmoking['id'].isin(ttt.index)]

# Passive
idPassive = dfCaseSmoking[dfCaseSmoking['TOBACCO_USER'] == 'Passive']['id'].unique()
tt =  dfCaseSmoking.loc[dfCaseSmoking['id'].isin(idPassive)]

pid = '100192'
date = 20120101
window = [0 , 365]
patientDf = (dfSmoking[dfSmoking['id'] == pid]).sort_values('measure_date_int').reset_index()


 # Quit + Yes smokers
tt = dfSmoking.groupby('id')
idList = []
for gr in tt:
    if ('Yes' in gr[1]['TOBACCO_USER'].unique()) and ('Quit' in gr[1]['TOBACCO_USER'].unique()):
        idList.append(gr[0])
ttt =  dfSmoking.loc[dfSmoking['id'].isin(idList)]

# Quit + Never smokers
tt = dfSmoking.groupby('id')
idList = []
for gr in tt:
    if ('Quit' in gr[1]['TOBACCO_USER'].unique()) and ('Never' in gr[1]['TOBACCO_USER'].unique()):
        idList.append(gr[0])
ttt =  dfSmoking.loc[dfSmoking['id'].isin(idList)] 
len(idList)

# Check feature generation 
new_gb = pd.concat( [ tt.get_group(group) for i,group in enumerate( tt.groups) if i < 1000 ] ).groupby('id')    
#resDf = new_gb.apply(smokingFeatGenerator)
#resDfNew = resDf.apply(pd.Series)
#resDfNew.columns = ['Smoking Status','NeverSmoker','PassiveSmoker','FormerSmoker','CurrentSmoker','last pkyears','max pkyears','quitTime']

resDfShort = new_gb.apply(smokingFeatGeneratorShort)
resDfShortNew = resDfShort.apply(pd.Series)
resDfShortNew.columns = ['Smoking Status','NeverSmoker','PassiveSmoker','FormerSmoker','CurrentSmoker','last pkyears','max pkyears','quitTime']

for name,gr in new_gb:
    smokingFeatGenerator(gr)
    smokingFeatGeneratorShort(gr)
    
# Binary features = NeverSmoker, PassiveSmoker, FormerSmoker , CurrentSmoker
# time Since Quitting 

patientDf = new_gb.get_group('100147')

SmokingStatusVal = patientDf['TOBACCO_USER'][patientDf['TOBACCO_USER']== patientDf['TOBACCO_USER']].reset_index(drop=True)
SmokingStatusTime = patientDf['measure_date_int'][patientDf['TOBACCO_USER']== patientDf['TOBACCO_USER']].reset_index(drop=True)
SmokingQuitVal = patientDf['smoking_quit_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
SmokingQuitTime = patientDf['measure_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
SmokingPkyrVal = patientDf['pkyr'][patientDf['pkyr']== patientDf['pkyr']].reset_index(drop=True)
SmokingPkyrTime = patientDf['measure_date_int'][(patientDf['pkyr']== patientDf['pkyr']) & (patientDf['pkyr'] != '0') ].reset_index(drop=True)


###################################################################
# Feature Generation
###################################################################



def smokingFeatGeneratorShort(patientDf):
    SmokingStatusVal = patientDf['TOBACCO_USER'][patientDf['TOBACCO_USER']== patientDf['TOBACCO_USER']].reset_index(drop=True)
    SmokingStatusTime = patientDf['measure_date_int'][patientDf['TOBACCO_USER']== patientDf['TOBACCO_USER']].reset_index(drop=True)
    SmokingQuitVal = patientDf['smoking_quit_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
    SmokingQuitTime = patientDf['measure_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
    SmokingPkyrVal = patientDf['pkyr'][patientDf['pkyr']== patientDf['pkyr']].reset_index(drop=True)
    SmokingPkyrTime = patientDf['measure_date_int'][(patientDf['pkyr']== patientDf['pkyr']) & (patientDf['pkyr'] != '0') ].reset_index(drop=True)
    
    ## Set time as index date!
    indexdate = patientDf['index_date'].iloc[0]
    date = int(indexdate[6:] + indexdate[0:2] + indexdate[3:5])
    ##
    MISSING_VAL = -pow(2,16)
    
    # Never Smoker 
    # Only if all values are never smoker and no quit date before
    NeverSmoker = MISSING_VAL
    CurrentSmoker = MISSING_VAL
    PassiveSmoker = MISSING_VAL
    FormerSmoker = MISSING_VAL
    lastPackYears = MISSING_VAL
    maxPackYears = MISSING_VAL
    quitTime = MISSING_VAL
    
    # Calculate get last quit time before date. 
    if len(SmokingQuitVal > 0):
        for timeInd in range(0,len(SmokingQuitTime)-1):
            if SmokingQuitTime[timeInd] > date:
                break;
            quitTime = SmokingQuitVal[timeInd]
    
    # overdie values when never smoker or current smoker.

    # calculate smoking status    
    if len(SmokingStatusVal) > 0:
        NeverSmoker = 1
        CurrentSmoker = 0
        PassiveSmoker = 0
        FormerSmoker = 0
        prevStatus = 'Quit'
        prevStatusDate = '01011900'
        for timeInd in range(0,len(SmokingStatusTime)):
            if SmokingStatusTime[timeInd] > date:
                break;
            if (SmokingStatusVal[timeInd] == 'Quit' or SmokingStatusVal[timeInd] == 'Yes'):
                NeverSmoker = 0
                FormerSmoker = 1
            
            if (SmokingStatusVal[timeInd] == 'Passive'):
                PassiveSmoker = 1
            
            # search for Yes -> Quit transitions (if yes after quitTime, take the quit date)
            if (SmokingStatusVal[timeInd] == 'Quit') and  (prevStatus == 'Yes'):
                    if (int(prevStatusDate) > quitTime):
                        quitTime = SmokingStatusTime[timeInd]
                        
            prevStatus = SmokingStatusVal[timeInd]
            prevStatusDate = SmokingStatusTime[timeInd]
            
            # Keep ;ast value for current smokers
            lastVal = SmokingStatusVal[timeInd]
            
        if lastVal == 'Yes':
            FormerSmoker = 0
            CurrentSmoker = 1
            quitTime = date
        
        # Chck whther necassary
        if ( ((len(SmokingPkyrVal) > 0) or (len(SmokingQuitVal)>0)) and (CurrentSmoker != 1)):
            FormerSmoker = 1
            NeverSmoker = 0
             
        if NeverSmoker:
            quitTime = '01011900'           
        #
        # Pack Years:
        if (NeverSmoker == 1):
            maxPackYears = 0
            lastPackYears = 0
        else:
            if len(SmokingPkyrVal) > 0:
                for timeInd in range(0,len(SmokingPkyrTime)):
                    if SmokingPkyrTime[timeInd] > date:
                        break;
                    if float(SmokingPkyrVal[timeInd]) > 0 :
                        lastPackYears = SmokingPkyrVal[timeInd]
                        if float(SmokingPkyrVal[timeInd]) > maxPackYears:
                            maxPackYears = float(SmokingPkyrVal[timeInd])
                         
         # PSmoking Status:
    SmokingStatus = MISSING_VAL
    if  NeverSmoker == 1:
        SmokingStatus = 0
    if PassiveSmoker == 1:
        SmokingStatus = 1
    if FormerSmoker == 1:
        SmokingStatus = 2
    if CurrentSmoker == 1:
        SmokingStatus = 3
        
        
    
    return SmokingStatus,NeverSmoker,PassiveSmoker,FormerSmoker,CurrentSmoker,lastPackYears,maxPackYears,quitTime
    

def smokingFeatGenerator(patientDf):
    SmokingStatusVal = patientDf['TOBACCO_USER'][patientDf['TOBACCO_USER']== patientDf['TOBACCO_USER']].reset_index(drop=True)
    SmokingStatusTime = patientDf['measure_date_int'][patientDf['TOBACCO_USER']== patientDf['TOBACCO_USER']].reset_index(drop=True)
    SmokingQuitVal = patientDf['smoking_quit_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
    SmokingQuitTime = patientDf['measure_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
    SmokingPkyrVal = patientDf['pkyr'][patientDf['pkyr']== patientDf['pkyr']].reset_index(drop=True)
    SmokingPkyrTime = patientDf['measure_date_int'][(patientDf['pkyr']== patientDf['pkyr']) & (patientDf['pkyr'] != '0') ].reset_index(drop=True)
    
    ## Set time as index date!
    indexdate = patientDf['index_date'].iloc[0]
    date = int(indexdate[6:] + indexdate[0:2] + indexdate[3:5])
    ##
    MISSING_VAL = -pow(2,16)
    
    # Never Smoker 
    # Only if all values are never smoker and no quit date before
    NeverSmoker = MISSING_VAL
    CurrentSmoker = MISSING_VAL
    PassiveSmoker = MISSING_VAL
    FormerSmoker = MISSING_VAL
    lastPackYears = MISSING_VAL
    maxPackYears = MISSING_VAL
    quitTime = MISSING_VAL
    
    if len(SmokingStatusVal) > 0:
        NeverSmoker = 0 
        
        if len(SmokingStatusVal) > 0:
            NeverSmoker = 1
            # Only if all values are never
            for timeInd in range(0,len(SmokingStatusTime)):
                if SmokingStatusTime[timeInd] > date:
                    break;
                if (SmokingStatusVal[timeInd] != 'Never'):
                        NeverSmoker = 0
                        break
                    
        if len(SmokingQuitTime > 0):
            # Check that there is no quit year
            for timeInd in range(0,len(SmokingQuitTime)):
                if SmokingQuitVal[timeInd] > date:
                    break;
                NeverSmoker = 0
                
        # Current Smoker:
        # check last value of 
        #if (SmokingStatusVal[SmokingStatusTime < (date)][len(SmokingStatusVal)-1] == 'Yes'):
        CurrentSmoker = 0
        if len(SmokingStatusTime) > 0:
            for timeInd in range(0,len(SmokingStatusTime)):
                if SmokingStatusTime[timeInd] > date:
                    break;
                if (SmokingStatusVal[timeInd] == 'Yes'):
                    CurrentSmoker = 1
                    
        # Passive:
        # Check if one value is Passive:
        if len(SmokingStatusVal) > 0:
            PassiveSmoker = 0
            # Only if all values are never
            for timeInd in range(0,len(SmokingStatusTime)):
                if SmokingStatusTime[timeInd] > date:
                    break;
                if (SmokingStatusVal[timeInd] == 'Passive'):
                        PassiveSmoker = 1
                        break
                    
        # Quit:
        # 1. If There is value which is not Passive or never, and not smoker -> then quit
        FormerSmoker = 0
        if len(SmokingStatusVal) > 0 and (CurrentSmoker != 1):
             for timeInd in range(0,len(SmokingStatusTime)-1):
                if SmokingStatusTime[timeInd] > date:
                    break;
                if (SmokingStatusVal[timeInd] != 'Passive' and SmokingStatusVal[timeInd] != 'Never'):
                        FormerSmoker = 1
                        break
        
        # 2. if there are pack years and not current smoker:
        if len(SmokingPkyrVal) > 0 and (CurrentSmoker != 1):
            FormerSmoker = 1
            
        #        
        # Calculate get last quit time before date. 
        SmokingQuitVal = patientDf['smoking_quit_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
        SmokingQuitTime = patientDf['measure_date_int'][patientDf['smoking_quit_date']== patientDf['smoking_quit_date']].reset_index(drop=True)
        
        quitTime = MISSING_VAL
        if len(SmokingQuitVal > 0):
            for timeInd in range(0,len(SmokingQuitTime)):
                if SmokingQuitTime[timeInd] > date:
                    break;
                quitTime = SmokingQuitVal[timeInd]
        
        # overdie values when never smoker or current smoker.
        if CurrentSmoker:
            quitTime = date
        
        if NeverSmoker:
            quitTime = '01011900'
            
        
        # Search for last Yes-> quit transition, if "yes" after quittime, take the quit date after the transition 
        if len(SmokingStatusVal) > 0:
            prevStatus = 'Quit'
            prevStatusDate = '01011900'
            # Only if all values are never
            for timeInd in range(0,len(SmokingStatusTime)):
                if SmokingStatusTime[timeInd] > date:
                    break;
                if (SmokingStatusVal[timeInd] == 'Quit') and  (prevStatus == 'Yes'):
                    if (int(prevStatusDate) > int(quitTime)):
                        quitTime = SmokingStatusTime[timeInd]
                        
                prevStatus = SmokingStatusVal[timeInd]
                prevStatusDate = SmokingStatusTime[timeInd]
                
        # Pack Years:
        if (NeverSmoker == 1):
            maxPackYears = 0
            lastPackYears = 0
        else:
            if len(SmokingPkyrVal) > 0:
                for timeInd in range(0,len(SmokingPkyrTime)):
                    if SmokingPkyrTime[timeInd] > date:
                        break;
                    lastPackYears = SmokingPkyrVal[timeInd]
                    if float(SmokingPkyrVal[timeInd]) > maxPackYears:
                        maxPackYears = float(SmokingPkyrVal[timeInd])
                         
         # PSmoking Status:
    SmokingStatus = MISSING_VAL
    if  NeverSmoker == 1:
        SmokingStatus = 0
    if PassiveSmoker == 1:
        SmokingStatus = 1
    if FormerSmoker == 1:
        SmokingStatus = 2
    if CurrentSmoker == 1:
        SmokingStatus = 3
        
        
    
    return SmokingStatus,NeverSmoker,PassiveSmoker,FormerSmoker,CurrentSmoker,lastPackYears,maxPackYears,quitTime


            
    


    
    
    
       
    


    
    
    
    
    
    



