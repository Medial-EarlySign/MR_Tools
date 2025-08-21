 #obsolete. Replaced by python code (in jupiter)
 cat /server/Work/TrinetX/Labs/medication_drug.csv|awk -F ',' '{print $1,sprintf("\t%s:%s\t",$4,$5),$6}'|sed -r 's/\"//g'|sed -r 's/RxNorm:/RX_CODE:/g'|sed -r 's/NDC:/NDC_CODE:/g'>mergedDrug.1 &
 cat /server/Work/TrinetX/Labs/medication_ingredient.csv|awk -F ',' '{print $1,sprintf("\t%s:%s\t",$4,$5),$6}'|sed -r 's/\"//g'|sed -r 's/RxNorm:/RX_CODE:/g'|sed -r 's/NDC:/NDC_CODE:/g'>mergedDrug.2 &
 wait
 

