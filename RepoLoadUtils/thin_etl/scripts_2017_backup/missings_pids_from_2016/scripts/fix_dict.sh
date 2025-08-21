#!/bin/bash

#last_p=`tail -n 1 /server/Temp/Thin_2017_Loading/dicts/dict.prac | awk '{print $2}'`
#echo "last_p=${last_p}"
#echo "fixing dict.prac"
#cat /server/Temp/Thin_2017_Loading/outputs/missing_2017.txt | awk -v i=${last_p} '{i+=1; print "DEF\t"i"\tPRAC_"$1}' >> /server/Temp/Thin_2017_Loading/dicts/dict.prac

#last_p=`tail -n 1 /server/Temp/Thin_2017_Loading/dicts/dict.pvi | awk '{print $2}'`
#echo "fix pvi. last_p=${last_p}" #empty haven't completed
#subtract.pl /server/Temp/Thin_2017_Loading/missing_pids_from_2016/dicts/dict.pvi 2 /server/Temp/Thin_2017_Loading/dicts/dict.pvi 2 | awk -v i=${last_p} '{i+=1; print "DEF\t"i"\t"$3}' >> /server/Temp/Thin_2017_Loading/dicts/dict.pvi

#did - similar think with read_code, and ahdlookup
#cat /server/Temp/Thin_2017_Loading/missing_pids_from_2016/dicts/dict.drugs_defs | egrep "^DEF" | awk 'BEGIN {FS="\t"} {print $3}' | sort > outputs/drugs_def.new
#cat /server/Temp/Thin_2017_Loading/dicts/dict.drugs_defs | egrep "^DEF" | awk 'BEGIN {FS="\t"} {print $3}' | sort > outputs/drugs_def.old

#this is smaller size complete list:
#last_drug=`egrep "^DEF" /server/Temp/Thin_2017_Loading/dicts/dict.drugs_defs | tail -n 1 | awk '{print $2}'`
#echo "last_d=${last_drug}"
#subtract.pl outputs/drugs_def.new 0 outputs/drugs_def.old 0 | awk -v i=${last_drug} '{i+=1; print "DEF\t"i"\t"$1 }' >> /server/Temp/Thin_2017_Loading/dicts/dict.drugs_defs

#cat /server/Temp/Thin_2017_Loading/missing_pids_from_2016/dicts/dict.drugs_sets | egrep "^SET" | awk 'BEGIN {FS="\t"} {print $2}' | uniq | sort > outputs/drugs_sets.new
#cat /server/Temp/Thin_2017_Loading/dicts/dict.drugs_sets | egrep "^SET" | awk 'BEGIN {FS="\t"} {print $2}' | uniq | sort > outputs/drugs_sets.old

#subtract.pl outputs/drugs_sets.new 0 outputs/drugs_sets.old 0
#subtract.pl outputs/drugs_sets.new 0 outputs/drugs_sets.old 0 | while read line ; do
   #echo Fixing $line
   #cat dicts/dict.drugs_sets | awk -v atc_code=$line '$2==atc_code' >> /server/Temp/Thin_2017_Loading/dicts/dict.drugs_sets
#done

#cat /server/Temp/Thin_2017_Loading/missing_pids_from_2016/dicts/dict.drugs_sets | egrep "^SET" | awk 'BEGIN {FS="\t"} {print $3}' | uniq | sort > outputs/drugs_sets.new
#cat /server/Temp/Thin_2017_Loading/dicts/dict.drugs_sets | egrep "^SET" | awk 'BEGIN {FS="\t"} {print $3}' | uniq | sort > outputs/drugs_sets.old

#subtract.pl outputs/drugs_sets.new 0 outputs/drugs_sets.old 0 | while read line; do
   #echo Fixing $line
   #cat dicts/dict.drugs_sets | awk -v drug_code=$line '$3==drug_code' >> /server/Temp/Thin_2017_Loading/dicts/dict.drugs_sets
#done

cat /server/Temp/Thin_2017_Loading/missing_pids_from_2016/dicts/dict.hospitalizations | egrep "^DEF" | awk 'BEGIN {FS="\t"} {print $3}' | uniq | sort >  outputs/hosp_def.new
cat /server/Temp/Thin_2017_Loading/dicts/dict.hospitalizations | egrep "^DEF" | awk 'BEGIN {FS="\t"} {print $3}' | uniq | sort >  outputs/hosp_def.old

cat /server/Temp/Thin_2017_Loading/missing_pids_from_2016/dicts/dict.hospitalizations | egrep "^SET" | awk 'BEGIN {FS="\t"} {print $2"\t"$3}' | uniq | sort >  outputs/hosp_set.new
cat /server/Temp/Thin_2017_Loading/dicts/dict.hospitalizations | egrep "^SET" | awk 'BEGIN {FS="\t"} {print $2"\t"$3}' | uniq | sort >  outputs/hosp_set.old



