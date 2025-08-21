#!/bin/bash

BASE_INPUT_PATH=/data/MHS_Raw
BASE_OUTPUT_PATH=/data/MHS_loading/march2018
FINAL_REP_PATH=/data/Repositories/march2018
FIX_FIT_HEBREW=0

mkdir -p $BASE_OUTPUT_PATH
mkdir -p $BASE_OUTPUT_PATH/data
mkdir -p $BASE_OUTPUT_PATH/dicts
mkdir -p $BASE_OUTPUT_PATH/configs
mkdir -p $BASE_OUTPUT_PATH/logs

mkdir -p $FINAL_REP_PATH

echo "calcing demographic"
if [ -f $BASE_OUTPUT_PATH/data/DEMOGRAPHIC ]; then
  echo "skip DEMOGRAPHIC - already done"
else
  tail -n +2 ${BASE_INPUT_PATH}/DEMOG_DATA.csv | awk '{ if ($3=="M") { print $1"\tBYEAR\t"$2"\n"$1"\tGENDER\t1\n"$1"\tBDATE\t"$2"0101" } else { print $1"\tBYEAR\t"$2"\n"$1"\tGENDER\t2\n"$1"\tBDATE\t"$2"0101" }}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/DEMOGRAPHIC
fi

echo "calcing Urine..."
if [ -f $BASE_OUTPUT_PATH/data/LABS_URINE.final ]; then
  echo "skip LABS_URINE.final - already done"
else
  text_file_processor --input $BASE_INPUT_PATH/LABS_URAN.csv --delimeter="," --output - --config_parse="0;file:/data/MHS_Raw/dicts/dict.lab_tests.csv#0#1#1;2;3;4" | awk -F"," '{ gsub(" ","_",$2); gsub(/[\(\)]/,"",$2) ;print $1"\t"$2"\t" substr($3,1,4) substr($3,6,2) substr($3,9,2) "\t"$4"\t"$5}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/LABS_URINE.final
fi

echo "writing Diseases.."
text_file_processor --input $BASE_INPUT_PATH/Diseases/IBD.txt  --output - --config_parse "0;Diagnosis;2;1" | awk -F"," '{print $1"\t"$2"\t"$3"\t"$4}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/IBD.final
text_file_processor --input $BASE_INPUT_PATH/Diseases/sikle_anemia.txt --output - --config_parse "0;Diagnosis;1;sickle_anemia" | awk -F"," '{print $1"\t"$2"\t"$3"\t"$4}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/sikle_anemia.final
text_file_processor --input $BASE_INPUT_PATH/Diseases/ULCER.txt --output - --config_parse "0;Diagnosis;2;1" | awk -F"," '{print $1"\t"$2"\t"$3"\t"$4}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/ULCER.final
tail -n +2 $BASE_INPUT_PATH/Diseases/TALSEMIA.txt | awk '{print $1 "\t" "Diagnosis" "\t" substr($2,5,5)  "0101\t" "Talsemia"  }' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/TALSEMIA.final

echo "calcing medadim"
if [ -f $BASE_OUTPUT_PATH/data/MADADIM.final ]; then
  echo "skip MADADIM.final - already done"
else
  text_file_processor --input $BASE_INPUT_PATH/MADADIM.csv --config_parse "0;file:/data/MHS_Raw/dicts/dict.madadim.csv#0#2#1;1;3"  --output - --delimeter , | awk -F"," '{ gsub(" ","_",$2); gsub(/[\(\)]/,"",$2) ;print $1"\t"$2"\t" substr($3,1,4) substr($3,6,2) substr($3,9,2) "\t"$4}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/MADADIM.final
fi

echo "calcing FIT.."
if [ -f $BASE_OUTPUT_PATH/data/FIT.final ]; then
  echo "skip FIT - already done"
else
  text_file_processor --input $BASE_INPUT_PATH/FIT.csv --output - --delimeter , --config_parse "0;FIT;5;3" | awk -F"," '{ gsub(" ","_",$2); gsub(/[\(\)]/,"",$2) ;print $1"\t"$2"\t" substr($3,1,4) substr($3,6,2) substr($3,9,2) "\t"$4}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/FIT.final
fi

echo "calcing Drugs..."
if [ -f $BASE_OUTPUT_PATH/data/DRUGS.final ]; then
  echo "skip DRUGS.final - already done"
else
  text_file_processor --input  $BASE_INPUT_PATH/DRUGS.csv --delimeter , --output - --config_parse "0;Drug;1;file:/data/MHS_Raw/dicts/dict.drugs.csv#0#2#1;3;4;5" --treat_missings original | awk -F"," '{print $1"\t"$2"\t"$3"\t"$4"\t"$5"\t"$6"\t"$7}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/DRUGS.final
fi

echo "calcing Labs..."
if [ -f $BASE_OUTPUT_PATH/data/LABS_CBC.final ]; then
  echo "skip LABS_CBC.final - already done"
else
  text_file_processor --delimeter , --input $BASE_INPUT_PATH/LABS_CBC.csv --output - --config_parse "1;file:/data/MHS_Raw/dicts/dict.lab_tests.csv#0#2#1;3;4" | awk -F"," '{ gsub(" ","_",$2); gsub(/[\(\)]/,"",$2) ;print $1"\t"$2"\t" substr($3,1,4) substr($3,6,2) substr($3,9,2) "\t"$4}' | sort -S 80% -g -k1 > $BASE_OUTPUT_PATH/data/LABS_CBC.final
fi

#ISHPUZIM
echo "calcing Hospitalizations..."
if [ -f $BASE_OUTPUT_PATH/data/ISHPUZIM.final ]; then
  echo "skip ISHPUZIM.final - already done"
else
  text_file_processor --treat_missings unknown --delimeter , --input $BASE_INPUT_PATH/ISHPUZIM.csv --output - --config_parse "0;Hospitalization_Dep;3;file:/data/MHS_Raw/dicts/dicts.hospitalization_dep.csv#0#5#1;4" | awk -F"," '{ gsub(" ","_",$4); gsub(/[\(\)]/,"",$4); print $1"\t"$2"\t"$3"\t"$4"\t" (mktime(substr( $5,1,4) " " substr($5,5,2) " " substr($5,7,2) " 00 00 00")- mktime( substr($3,1,4) " " substr($3,5,2) " " substr($3,7,2) " 00 00 00" ))/86400 }' | sort -S 80% -g -k1 >  $BASE_OUTPUT_PATH/data/ISHPUZIM.final
fi

#Create init maccabi.signals:
echo "Creating configs - signal file..."
if [ -f $BASE_OUTPUT_PATH/configs/maccabi.signals ]; then
  echo "skip create signals config - already done"
else
  awk -F"\t" '{print $2}' $BASE_OUTPUT_PATH/data/* | sort -S 80% | uniq | awk '{print "SIGNAL\t"$1"\t"NR"\t1"}' > $BASE_OUTPUT_PATH/configs/maccabi.signals
  echo "please change signal types in $BASE_OUTPUT_PATH/configs/maccabi.signals"
  vi $BASE_OUTPUT_PATH/configs/maccabi.signals
fi

#create dicts:
if [ -f $BASE_OUTPUT_PATH/dicts/dict.FIT ]; then
  echo "skip create dict.FIT - already done"
else
  echo -e "SECTION\tFIT,FECAL_TEST" > $BASE_OUTPUT_PATH/dicts/dict.FIT
  awk -F"\t" '{d[$NF]+=1} END {for (i in d) print i"\t"d[i]}' $BASE_OUTPUT_PATH/data/FIT.final | sort -S 80% -g -r -k2 -t$'\t' | awk -F"\t" '{print "DEF\t"NR"\t"$1}' >> $BASE_OUTPUT_PATH/dicts/dict.FIT
  echo "Done creating dict.FIT"
  vi $BASE_OUTPUT_PATH/dicts/dict.FIT
fi
if [ -f $BASE_OUTPUT_PATH/dicts/dict.Diagnosis ]; then
  echo "skip create dict.Diagnosis - already done"
else
  echo -e "SECTION\tDiagnosis" > $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  awk '{print $NF}' $BASE_OUTPUT_PATH/data/IBD.final | sort -S 80% | uniq | awk '{print "DEF\t" 100+NR "\t" $1}' >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  awk '{print $NF}' $BASE_OUTPUT_PATH/data/ULCER.final | sort -S 80% | uniq | awk '{print "DEF\t" 200+NR "\t" $1}' >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  echo -e "DEF\t5001\tIBD" >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  echo -e "DEF\t5002\tsickle_anemia" >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  echo -e "DEF\t5003\tTalsemia" >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  echo -e "DEF\t5004\tULCER" >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis

  awk '{print $NF}' $BASE_OUTPUT_PATH/data/IBD.final | sort -S 80% | uniq | awk '{print "SET\t" "IBD" "\t" $1}' >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis
  awk '{print $NF}' $BASE_OUTPUT_PATH/data/ULCER.final | sort -S 80% | uniq | awk '{print "SET\t" "ULCER" "\t" $1}' >> $BASE_OUTPUT_PATH/dicts/dict.Diagnosis 
  echo "done creating dict.Diagnosis"
fi
if [ -f $BASE_OUTPUT_PATH/dicts/dict.Drug ]; then
  echo "skip create dict.Drug - already done"
else
  echo -e "SECTION\tDrug" > $BASE_OUTPUT_PATH/dicts/dict.Drug
  awk '{print $4}' $BASE_OUTPUT_PATH/data/DRUGS.final | sort -S 80% | uniq | awk '{print "DEF\t" 1000+NR "\t" $1}' >> $BASE_OUTPUT_PATH/dicts/dict.Drug
  #add ATC sets and code
  vi $BASE_OUTPUT_PATH/dicts/dict.Drug
  echo "done creating dict.Drug"
fi
if [ -f $BASE_OUTPUT_PATH/dicts/dict.Hospitalization ]; then
  echo "skip create dict.Hospitalization - already done"
else
  awk -F"," '{print $6"\t"$7}' $BASE_INPUT_PATH/ISHPUZIM.csv  | sort -S 80% | uniq -c | sort -g -r -k1 > $BASE_OUTPUT_PATH/configs/convert_hosp
  echo -e "SECTION\tHospitalization,Hospitalization_Dep" > $BASE_OUTPUT_PATH/dicts/dict.Hospitalization
  awk '{print $4}' $BASE_OUTPUT_PATH/data/ISHPUZIM.final | sort -S 80% | uniq | awk '{print "DEF\t" 1000+NR "\t" $1}' >> $BASE_OUTPUT_PATH/dicts/dict.Hospitalization
  grep "DEF" $BASE_OUTPUT_PATH/dicts/dict.Hospitalization | text_file_processor --input - --output - --config_parse ""
  vi $BASE_OUTPUT_PATH/dicts/dict.Hospitalization
  echo "done creating dict.Hospitalization"
fi

#FIX FIT hebrew:
if [ $FIX_FIT_HEBREW -eq 1 ]; then
  echo "Fixing FIr Hebrew"
  tail -n +2 $BASE_OUTPUT_PATH/dicts/dict.FIT > $BASE_OUTPUT_PATH/configs/convert_fit
  text_file_processor --input $BASE_OUTPUT_PATH/data/FIT.final --output $BASE_OUTPUT_PATH/data/FIT.final2 --config_parse "0;1;2;file:$BASE_OUTPUT_PATH/configs/convert_fit#2#3#1" 
  rm $BASE_OUTPUT_PATH/data/FIT.final
  mv $BASE_OUTPUT_PATH/data/FIT.final2 $BASE_OUTPUT_PATH/data/FIT.final
  echo -e "DEF\t1001\t0\nDEF\t1001\tNegative" >>  $BASE_OUTPUT_PATH/dicts/dict.FIT
  echo -e "DEF\t1002\t1\nDEF\t1002\tPositive" >>  $BASE_OUTPUT_PATH/dicts/dict.FIT
  echo -e "DEF\t1003\t2\nDEF\t1003\tUnknown" >>  $BASE_OUTPUT_PATH/dicts/dict.FIT
fi


#create init load file:
shopt -s nullglob
echo "Creating config load file..."
ln -s -f $BASE_OUTPUT_PATH/dicts/* $BASE_OUTPUT_PATH/configs
if [ -f $BASE_OUTPUT_PATH/configs/maccabi.load_config ]; then
  echo "skip creating load_config - already done"
else
  echo -e "DESCRIPTION\tMACCABI" > $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "RELATIVE\t1" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "SAFE_MODE\t1" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "MODE\t3" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "PREFIX\trepo_" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "CONFIG\tmaccabi.repository" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "CODES\tcodes_to_signals" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "SIGNAL\tmaccabi.signals" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "FORCE_SIGNAL\tGENDER,BYEAR" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "OUTDIR\t$FINAL_REP_PATH" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "DIR\t$BASE_OUTPUT_PATH/configs" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  for f in $BASE_OUTPUT_PATH/dicts/*; do
    echo -e "DICTIONARY\t$f" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  done
  ls -1 $BASE_OUTPUT_PATH/data/ | awk '{print "DATA\t../data/"$1}' >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo -e "#LOAD_ONLY\t" >> $BASE_OUTPUT_PATH/configs/maccabi.load_config
  echo "please change load_config DATA\\DATA_S load type. you may edit LOAD_ONLY"
  vi $BASE_OUTPUT_PATH/configs/maccabi.load_config
fi

echo "dont forget to edit codes_to_signals and update signals files respectively"
#text_file_processor --input $BASE_OUTPUT_PATH/configs/maccabi.signals --output - --has_header 0 --treat_missings "original" --config_parse "0;file:$BASE_OUTPUT_PATH/configs/codes_to_signals#0#1#1;3" | sort | uniq | sort -g -k3 | awk '{print $1 "\t" $2 "\t" NR "\t" $3}' > $BASE_OUTPUT_PATH/configs/maccabi.signals2
read -p "Press any key to continue " confirm

echo "Run Create Rep with Flow" 
read -p "Continue? (Y/N): " confirm 
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
	Flow --rep_create --convert_conf $BASE_OUTPUT_PATH/configs/maccabi.load_config 2>&1 | tee  $BASE_OUTPUT_PATH/logs/rep_create.log
else
	echo "Skip running Flow:\n"
	echo "Flow --rep_create --convert_conf $BASE_OUTPUT_PATH/configs/maccabi.load_config 2>&1 | tee  $BASE_OUTPUT_PATH/logs/rep_create.log"
fi
#echo "no need to create op index. and cp_to_home"

#LABS_CBC - delete CUSTOMER_ID. change column numbers

#todo: cancer registry
#todo: dicts: drugs, also for conversion
#todo: COLONO
