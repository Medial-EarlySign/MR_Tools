library(data.table)

data = fread('H:\\MR\\Tools\\RepoLoadUtils\\thin_etl\\medcode.final.stats')
#data = fread('H:\\MR\\Tools\\RepoLoadUtils\\thin_etl\\ahdcode.final.stats')

fdata <- data[type!= 'SINGLE_VALUE']

colStats <- fdata[ total_cnt > 100 , .(cnt=.N) ,by=column_description][order(-cnt)]

emptyVals <- data[ type != 'SINGLE_VALUE' & column_description == '<empty string>']
#we can ignore <empty string> because it's not intersting
fdata <- fdata[column_description != '<empty string>']

#analyze column
fdata[column_description == 'OPERATOR', .N , by=type]
fdata[column_description == 'OPERATOR', .N , by=unique_cnt][order(unique_cnt)]

temp <- fdata[column_description == 'OPERATOR', .(ahd_name, data_file, top5Vals, unique_cnt, total_cnt)]
temp <- temp[,  .(ahd_name, data_file, top5Vals, unique_cnt, total_cnt, first_element = substr(top5Vals, 2 , lapply(gregexpr(',', top5Vals), function(x) x[1] - 1))  ,tst = as.numeric(substr(top5Vals, lapply(gregexpr('[(]', top5Vals), function(x) x[1]+1) , lapply(gregexpr(',', top5Vals), function(x) x[1] - 2)))   ) ][order(-tst)]

#end analyze

numeric_signal_codes<-data[type != 'SINGLE_VALUE' & column_description == 'NUM_RESULT' & data_file== 'TEST' & total_cnt >= 10000, code]

#filter not important
fdata <- fdata[column_description != 'OPERATOR']
fdata <- fdata[column_description != 'START_RNGE' & column_description!= 'END_RNGE' & column_description != 'MEASURE_UNIT']
fdata <- fdata[column_description != 'IN_PRAC'] #not important from which practice if or not idf in this pracitce - not important
fdata <- fdata[column_description != 'METHOD'] # where the IMMS was done - which method
fdata <- fdata[column_description != 'IMMS_STATUS'] # does the imms taken or stopped
fdata <- fdata[column_description != 'REASON'] #only in imms why it was taken - risk group, travller...
fdata <- fdata[column_description != 'STAGE'] #only in imms why stage of imms - there are several stages for giving imms - after each period of time..
fdata <- fdata[data_file != 'IMMS'] #the rest of imms  - only COMPOUND column
fdata <- fdata[column_description != 'SEEN_BY'] #who saw the pid - only 4


temp<- fdata[ (code %in% ('1005010500')) ] #Blood presuure
temp<- fdata[ (code %in% ('1005010200')) ] #Weight
temp<- fdata[ (code %in% ('1005010100')) ] #Height
temp<- fdata[ (code %in% ('1003040000')) ] #Smoking
temp<- fdata[ (code %in% ('1003050000')) ][order(-column_name)] #Alcohol
temp<- fdata[ (code %in% ('1009300000')) ][order(-column_name)] #Pulse
temp<- fdata[ (code %in% ('1001400080')) ][order(-column_name)] #Faecal Occult Blood
temp<- fdata[ (code %in% ('1001400169')) ][order(-column_name)] #Colonscopy

temp<- fdata[type == 'numeric'] 

#filter already handled NUM_RESULT and in clinical:
fdata <- fdata[column_description != 'NUM_RESULT' | data_file != 'TEST']
fdata <- fdata[ !(code %in% c('1005010500', '1005010200', '1005010100', '1003040000', '1003050000', '1009300000', '1001400080', '1001400169', '1001400323')) ]
fdata <- fdata[data_file != 'IMMS'] #the rest of imms  - only COMPOUND column
fdata <- fdata[type != 'numeric'] #Written to take care [asthma test in clinical demographic info like parity status, some newborn tests in clinical].
fdata<- fdata[column_description != 'READ_CODE']  #Written to take care[ diseases and allergies, familiy history diseases]
fdata<- fdata[column_description != 'FIT_FREQ']  #Written to take care[ eppilipsia]
fdata <- fdata[!code %in% c('1095000000', '1065000000', '1055201001', '1015000000', '1016000000', '1084000000', '1002337002')] #remove stuiped test
fdata <- fdata[!column_description %in% c('ADVICE_GIVEN', 'ADVICE_TYPE', 'EXCLUDE_TARGET(Y/N)', 
                                          'CERVICAL_EXCLUSION_REASON', 'CONTRACEPTIVE_SERVICE_TYPE', 'TEST_METHOD', 'PARENTAL_CONSENT',
                                          'CONSULTANT', 'HOSPITAL', 'MIDWIFE', 'NOTES_REQUESTBY', 'MATERNITY_BOOKING_TYPE', 'MOBILITY_LEVELS'
                                          , 'SEX', 'OUTCOME', 'AGENCY_TYPE', 'INTERVAL', 'BABY_OUTCOME', 'REFERRALS')] #filter not intersting tests
fdata <- fdata[! code %in% numeric_signal_codes] #filter categories when we have thier numeric value by code

fdata <- fdata[total_cnt >= 50000 | column_description %in% c('QUALIFIER', 'QUALIFIER(LEFT)','QUALIFIER(RIGHT)') ]
fdata <- fdata[ total_cnt >= 10000 | !column_description %in% c('QUALIFIER', 'QUALIFIER(LEFT)','QUALIFIER(RIGHT)') ]
#num_names <- data[ type == 'numeric' & total_cnt > 100 , .(cnt=.N, total_cnt=max(total_cnt) ) ,by=column_description][order(-cnt)]





temp<- fdata[data_file == 'IMMS']
special <- fdata[column_description != 'QUALIFIER' & column_description != 'QUALIFIER(LEFT)' & column_description != 'QUALIFIER(RIGHT)']
qualifier_signals <- fdata[column_description %in% c('QUALIFIER' ,'QUALIFIER(LEFT)' ,'QUALIFIER(RIGHT)')]

fdata[ , .(unique_cnt, ucnt = ifelse(unique_cnt > 50, 100 , ifelse(unique_cnt > 10 , 5*round(unique_cnt/ 5) ,unique_cnt) ) ) ][ , .(cnt=   .N) , by=ucnt][order(ucnt)]
