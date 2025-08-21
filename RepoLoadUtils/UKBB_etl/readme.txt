data sources
============
after downloading, and unpack using biobank utilities

/nas1/Data/UKBB/ukbb_db/

1st request:
	- data: ukb49235_c.csv
	- descriptions: ukb49235.html
	- gp_clinic.txt (primary care)
	
2nd request (first_occurance):
	- data: ukb51583.csv
	- descriptions: first_occurance_data_fields.txt

preperations
============
Scripts and code for etl and repo generation under source control
/nas1/users-data/Eitan/MR/tools/RepoLoadUtils/UKBB_etl

Midterm outputs = place to hold etl results files 
/nas1/Work/users/Eitan/UKBB_loading

Useful link
eitan-internal@node-03:/nas1/Work/users/Eitan/UKBB_loading$ ln -s /nas1/users-data/Eitan/MR/tools/RepoLoadUtils/UKBB_etl etl

NMR
---
Only for portion of the popullation

Use biobank visit dates to date the samples

blood test from primary care (gp)
---------------------------------
Data is in gp_clinic.txt, only for portion of the popullation

- use okbb resource to replace read code ver3 with ver2:
	- try READV3_CODE => READV2_CODE
	- else TERMV3_CODE => READV2_CODE
	- else IGNORE (local codes? about 1% of the rows)

- when relevant, use thin_signal_mapping.csv to convert read-codes to signals
	- not for 'Alcohol_quantity' 'Smoking_quantity'
	- "Unit mix" correction for:
		- Hemoglobin (mix g/L and g/dL)

- all the rest keep - see next

other measurments from primary care (gp)
----------------------------------------
if has value ...
- for now we keep only BP, Height, Weight, BMI
- and drop all the rest

if no value
- keep all in one general gp signal (and connect it to readcodes dict)

first_occurance
---------------
It combines self-reported, primary_care (when available) and hospital
all combine together to one RC signal


prepare load_config_file
========================
Put the load_config_file (tab delimited) in UKBB_loading/rep_config

Necessary dicts:
- Put in UKBB_loading/dict
- Bring the resource from /nas1/users-data/Eitan/MR/tools/DictUtils/Ontologies
- Add title tab delimited with "SECTION	signal_name,signal_name"

Prepare rep.signals based on recent example 
(if a signal is categorical - it must have a dictionary)

run
===

Flow --rep_create --convert_conf /nas1/Work/users/Eitan/UKBB_loading/outputs/rep_configs/load_config_file.config --load_err_file /nas1/Work/users/Eitan/UKBB_loading/errors.txt

(make sure all paths in load_config_file are right, and that outdir exists)


