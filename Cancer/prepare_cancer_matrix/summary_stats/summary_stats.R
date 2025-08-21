reg_file <- "\\\\server\\Data\\macabi5\\medialpopulationcancerstages.csv"
cen_file <- "\\\\server\\Data\\macabi5\\id.status"
dem_file <- "\\\\server\\Temp\\get_statistics_files\\Maccabi.Demographics.txt"
cbc_file <- "\\\\server\\Temp\\get_statistics_files\\InternalMaccabi.Data.txt"

reg = read.csv( reg_file )
dem = read.table( dem_file, header=FALSE, col.names=c("NUMERATOR", "BIRTH_YEAR", "GENDER") )

reg_crc = subset(reg, cancer.type1_first=="Digestive Organs" &
            cancer.type2_first=="Digestive Organs" & 
            cancer.type3_first=="Colon" | cancer.type3_first=="Rectum" )

sick = merge( reg_crc, dem )
sick = cbind( sick, AGE = 2011 - ds$BIRTH_YEAR )
sick = cbind( sick, AGE_AT_ONESET = sick$YEAR - sick$BIRTH_YEAR )

population = cbind( dem, AGE = 2011 - dem$BIRTH_YEAR)

c <- as.data.frame(with(sick, table(sick$YEAR, sick$AGE_AT_ONESET)))