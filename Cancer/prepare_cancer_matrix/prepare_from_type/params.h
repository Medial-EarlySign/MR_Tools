#ifndef __PARAMS_H__
#define __PARAMS_H__
#pragma once

#define STT_FILE "W:/CRC/AllDataSets/Censor"
#define REG_FILE "W:/CRC/AllDataSets/Registry"
#define DEM_FILE "W:/CRC/AllDataSets/Demographics" 
#define GRP_FILE "W:/CRC/AllDataSets/Groups" 

int file_nos[] = {7,7,9,9} ; // Regular/Full/Complete//Validation runs

char men_labfiles[][256] = {
	"T:/macabi4/men_cbc/men_CBC_2003_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2004_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2005_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2006_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2007_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2008_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2009_filtered_22-6-11.txt",
	"T:/macabi4/men_cbc/men_CBC_2010_filtered_22-6-11.txt", // Complete Run
	"T:/macabi4/men_cbc/men_CBC_2011_filtered_22-6-11.txt", // Complete Run
} ;

char men_extra_labfiles[][256] = {
	"T:/macabi5/men_training_2003",
	"T:/macabi5/men_training_2004",	
	"T:/macabi5/men_training_2005",
	"T:/macabi5/men_training_2006",
	"T:/macabi5/men_training_2007",
	"T:/macabi5/men_training_2008",
	"T:/macabi5/men_training_2009",
	"T:/macabi5/men_training_2010", // Complete Run
	"T:/macabi5/men_training_2011", // Complete Run
} ;

char women_labfiles[][256] = {
	"T:/macabi4/women_cbc/women_CBC_2003_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2004_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2005_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2006_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2007_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2008_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2009_filtered_22-6-11.txt",
	"T:/macabi4/women_cbc/women_CBC_2010_filtered_22-6-11.txt", // Complete Run
	"T:/macabi4/women_cbc/women_CBC_2011_filtered_22-6-11.txt", // Complete Run
} ;

char women_extra_labfiles[][256] = {
	"T:/macabi5/women_training_2003",
	"T:/macabi5/women_training_2004",	
	"T:/macabi5/women_training_2005",
	"T:/macabi5/women_training_2006",
	"T:/macabi5/women_training_2007",
	"T:/macabi5/women_training_2008",
	"T:/macabi5/women_training_2009",
	"T:/macabi5/women_training_2010", // Complete Run
	"T:/macabi5/women_training_2011", // Complete Run
} ;

// Validation Data:
char men_validation_labfiles[][256] = {
	"T:/macabi4/Validation/validation_cbc_men_2003_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2004_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2005_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2006_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2007_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2008_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2009_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2010_27-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_men_2011_31-7-11.txt"
} ;

char men_validation_extra_labfiles[][256] = {
	"T:/macabi5/men_validation_2003",
	"T:/macabi5/men_validation_2004",	
	"T:/macabi5/men_validation_2005",
	"T:/macabi5/men_validation_2006",
	"T:/macabi5/men_validation_2007",
	"T:/macabi5/men_validation_2008",
	"T:/macabi5/men_validation_2009",
	"T:/macabi5/men_validation_2010",
	"T:/macabi5/men_validation_2011",
} ;

char women_validation_labfiles[][256] = {
	"T:/macabi4/Validation/validation_cbc_women_2003_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2004_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2005_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2006_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2007_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2008_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2009_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2010_25-7-11.txt",
	"T:/macabi4/Validation/validation_cbc_women_2011_25-7-11.txt"
} ;

char women_validation_extra_labfiles[][256] = {
	"T:/macabi5/women_validation_2003",
	"T:/macabi5/women_validation_2004",	
	"T:/macabi5/women_validation_2005",
	"T:/macabi5/women_validation_2006",
	"T:/macabi5/women_validation_2007",
	"T:/macabi5/women_validation_2008",
	"T:/macabi5/women_validation_2009",
	"T:/macabi5/women_validation_2010",
	"T:/macabi5/women_validation_2011",
} ;

char biochem_files[][256] = {
	"T:/macabi4/biochemistry_14-2-12/biochem_2003",
	"T:/macabi4/biochemistry_14-2-12/biochem_2004",
	"T:/macabi4/biochemistry_14-2-12/biochem_2005",
	"T:/macabi4/biochemistry_14-2-12/biochem_2006",
	"T:/macabi4/biochemistry_14-2-12/biochem_2007",
	"T:/macabi4/biochemistry_14-2-12/biochem_2008",
	"T:/macabi4/biochemistry_14-2-12/biochem_2009",
	"T:/macabi4/biochemistry_14-2-12/biochem_2010",  // Complete Run
	"T:/macabi4/biochemistry_14-2-12/biochem_2011",  // Complete Run
} ;

char ferritin_files[][256] = {
	"T:/macabi5/ferritin_2003",
	"T:/macabi5/ferritin_2004",
	"T:/macabi5/ferritin_2005",
	"T:/macabi5/ferritin_2006",
	"T:/macabi5/ferritin_2007",
	"T:/macabi5/ferritin_2008",
	"T:/macabi5/ferritin_2009",
	"T:/macabi5/ferritin_2010", // Complete Run
	"T:/macabi5/ferritin_2011", // Complete Run
//	"T:/macabi5/ferritin_2012"
} ;


#define MEN_BMI_FILENO 1
#define WOMEN_BMI_FILENO 2
char bmifiles[2][2][256] = {{
	"T:/macabi4/men BMI/BMI_men_29-5-2011.csv",
	},{
	"T:/macabi4/women BMI/BMI_women_part1_25-5-2011.csv",
	"T:/macabi4/women BMI/BMI_women_part2_25-5-2011.csv",
}} ;

char validation_bmifiles[2][256] = {"T:/macabi4/Validation/BMI_men/bmi_men_validation_31-7-11.csv",
									"T:/macabi4/Validation/BMI_women/bmi_women_validation_31-7-11.csv",
} ;

#define MEN_SMX_FILENO 2
#define WOMEN_SMX_FILENO 3
char smxfiles[2][3][256] = {{
	"T:/macabi4/men smoking/smoking_stat_men_part1.csv",
	"T:/macabi4/men smoking/smoking_stat_men_part2.csv",
	},{
	"T:/macabi4/women smoking/smoking_stat_women_part1.csv",
	"T:/macabi4/women smoking/smoking_stat_women_part2.csv",
	"T:/macabi4/women smoking/smoking_stat_women_part3.csv",
}} ;

char validation_smxfiles[2][256] = {"T:/macabi4/Validation/SMOKING_STAT_men/SMOKING_STAT_men_validation_31-7-11.csv",
									"T:/macabi4/Validation/SMOKING_STAT_women/SMOKING_STAT_women_validation_31-7-11.csv",
} ;

char thin_smx_file[256] = "W:/LUCA/THIN_7Nov2013/Smoking/Smoking.csv" ;
char thin_qty_smx_file[256] = "W:/LUCA/THIN_MAR2014/Smoking/qtySmx.txt" ;

#endif