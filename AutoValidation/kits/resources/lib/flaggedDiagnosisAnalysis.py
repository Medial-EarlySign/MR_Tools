# This program analyzes the diagnosis frequencies in flagged patients of a model or in false positive  patients of a model.
import pandas as pd
import medpython as med
import numpy as np
import datetime as dt 

import argparse
from scipy.stats import chi2_contingency 
from statsmodels.stats.multitest import multipletests

parser = argparse.ArgumentParser()
parser.add_argument('--rep', type=str, help="path to repository",required=True)
parser.add_argument('--f_preds', type=str, required=True, help="path to  predictions file")
parser.add_argument('--pr', type=float, default=0.03, help="Positive rate for flag threshold")
parser.add_argument('--pMax', type=float , default=0.05, help="p value threshold")
parser.add_argument('--minAge', type=float, default=40, help="min age of patients to condiser")
parser.add_argument('--maxAge', type=float, default=99, help="max age of patients to condiser")
parser.add_argument('--startTime', type=float, default=-99999, help="start of diagnosis time window ( in days) relative to prediction time (negative for time before prediction)")
parser.add_argument('--endTime', type=float, default=99999, help="start of diagnosis time window (in days) relative to prediction time (negative for time before prediction)")
parser.add_argument('--firstDiagnosis', action='store_true', help="when set diagnosis time is only on its first appearance (and not every appearance)")
parser.add_argument('--includeCases', action='store_true', help="should cases be included in the flagged population or if false only false positives")
parser.add_argument('--diagnosisSignal', type=str, default='RC_Diagnosis', help="name of diagnosis signal in repo.")
parser.add_argument('--f_output', type=str, required=True, help="path to output report file")

def fixTime(timeColumn):
    tc=timeColumn.copy() # copy to avoid slice warning
    tc.loc[tc/10000<1]=tc[tc/10000<1]+18000000
    tc.loc[tc%100==0]=tc[tc%100==0]+1;
    tc.loc[tc%10000<100]= tc[tc%10000<100]+100
    return(tc)

args = parser.parse_args()
# get the predictions
preds=pd.read_csv(args.f_preds,sep='\t')
preds.time=fixTime(preds.time)
preds.outcomeTime=fixTime(preds.outcomeTime)

# get bdate and diagnosis signals from repository 
rep=med.PidRepository()
rep.read_all(args.rep,[],[args.diagnosisSignal,'BDATE','GENDER'])
bdate=rep.get_sig('BDATE')
gender=rep.get_sig('GENDER')

# cut preds by age
preds=preds.merge(bdate,how='left',left_on='id',right_on='pid').rename(columns={'val':'bdate'}).merge(gender,how='left',left_on='id',right_on='pid').rename(columns={'val':'gender'})
preds['age']=(preds.time/10000).astype(int)-(preds.bdate/10000).astype(int)
preds=preds[preds.age.between(args.minAge,args.maxAge)]

#
#get one random pred for id if marked case in some preds consider as case 
preds=preds.sample(frac=1).sort_values(by=['id','outcome']).drop_duplicates(subset='id',keep='last')
flagged=preds[preds.pred_0>=preds.pred_0.quantile(1-args.pr)]

if not args.includeCases:
	flagged=flagged[flagged.outcome==0]

#Get the unflagged:
unFlagged=preds[preds.pred_0<preds.pred_0.quantile(1-args.pr)]
	
#age weighting
ageFlagged=flagged[['age','gender']].value_counts()
ageUnFlagged=unFlagged[['age','gender']].value_counts()

#merge the counts in each age and gender and calculate the weight for the unFlagged to age match to the flagged
allM=unFlagged.merge(ageFlagged,left_on=['age','gender'],right_index=True,how='left')
allM=allM.merge(ageUnFlagged,left_on=['age','gender'],right_index=True,how='left')
print(allM)              
#allM=allM.rename(columns={'age_x':'age','age_y':'countFlagged','age':'countUnFlagged'}) old pandas vrsion
allM=allM.rename(columns={'count_x':'countFlagged','count_y':'countUnFlagged'}) # new pandas use different column names
allM['weight']=allM.countFlagged/allM.countUnFlagged

# get diagnosis signal and merge withflagged and unFlagged
diag = rep.get_sig(args.diagnosisSignal).rename(columns={'val':'diagnosis'})
diag.date=fixTime(diag.date)
if args.firstDiagnosis :
    diag=diag.drop_duplicates(subset=['pid','diagnosis'],keep='first') 
unFlaggedDiag=pd.merge(allM,diag,how='inner',left_on='id',right_on='pid')
flaggedDiag=pd.merge(flagged,diag,how='inner',left_on='id',right_on='pid')



# cut diags according to time window
print(flaggedDiag.head())
print(unFlaggedDiag.head())
preds['window']=pd.to_datetime(preds.outcomeTime, format='%Y%m%d')-pd.to_datetime(preds.time, format='%Y%m%d')
flaggedDiag=flaggedDiag[pd.to_datetime(flaggedDiag.date, format='%Y%m%d')-pd.to_datetime(flaggedDiag.time, format='%Y%m%d')>=dt.timedelta(days=args.startTime)]
flaggedDiag=flaggedDiag[pd.to_datetime(flaggedDiag.date, format='%Y%m%d')-pd.to_datetime(flaggedDiag.time, format='%Y%m%d')<=dt.timedelta(days=args.endTime)]
unFlaggedDiag=unFlaggedDiag[pd.to_datetime(unFlaggedDiag.date, format='%Y%m%d')-pd.to_datetime(unFlaggedDiag.time, format='%Y%m%d')>=dt.timedelta(days=args.startTime)]
unFlaggedDiag=unFlaggedDiag[pd.to_datetime(unFlaggedDiag.date, format='%Y%m%d')-pd.to_datetime(unFlaggedDiag.time, format='%Y%m%d')<=dt.timedelta(days=args.endTime)]

# remove repeating diagnosis
flaggedDiag=flaggedDiag.drop_duplicates(subset=['id','diagnosis']) 
unFlaggedDiag=unFlaggedDiag.drop_duplicates(subset=['id','diagnosis']) 
# translate to frequencies
flaggedFreq=flaggedDiag.diagnosis.value_counts()
unFlaggedFreq=unFlaggedDiag.diagnosis.value_counts()
unFlaggedFreqMatched=unFlaggedDiag.groupby(by='diagnosis',observed=True)['weight'].sum()

freqMatrix=pd.concat([flaggedFreq,unFlaggedFreq,unFlaggedFreqMatched],axis=1)
freqMatrix.columns=['countFlagged','countUnFlagged','countUnFlaggedWeighted']

#calculate lift
freqMatrix['lift']=freqMatrix.countFlagged/(freqMatrix.countUnFlaggedWeighted+0.00001)

# function to calculate p value according to chi square
def xipval(x1,x0,y1,y0):
    chi2,p,dd,dddd=chi2_contingency(np.array([[x1+0.1,x0+0.1],[y1+0.1,y0+0.1]]))
    return(p)

# get the p value by chi square
freqMatrix['pVal']=freqMatrix.apply(lambda row: xipval(row['countFlagged'],flagged.shape[0]-row['countFlagged'],row['countUnFlagged'],unFlagged.shape[0]-row['countUnFlagged']),axis=1)

# make the FDR correction
freqMatrix['rejected'], freqMatrix['p_adjusted'], _, _=multipletests(freqMatrix.pVal, alpha=0.05, method='fdr_bh')

#output dropping the unsignificants and sort by lift
print(freqMatrix[freqMatrix.rejected &(freqMatrix.countFlagged>3)].sort_values(by='lift',ascending=False))
freqMatrix[freqMatrix.rejected &(freqMatrix.countFlagged>3)].sort_values(by='lift',ascending=False).to_csv(args.f_output,sep='\t')
