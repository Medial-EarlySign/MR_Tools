
drop table resolve_err;
create table resolve_err
(
pracid varchar(8),
status varchar(20),
source varchar(200),
cnt integer
)  
;


truncate table resolve_err;
LOAD DATA LOCAL INFILE 'W:\\Users\\Ido\\THIN_ETL\\ahd\\Resolved_ac\\all.resolve_err' INTO TABLE resolve_err
fields TERMINATED BY '\t'
lines TERMINATED BY '\n'
;

select distinct status from resolve_err
limit 20;

select status,source, count(*) cnti, sum(cnt) sumi
from resolve_err 
group by status, source 
order by sumi desc 
limit 10;
+----------------------+----------------------------------------------------------------------------------+------+------------+
| status               | source                                                                           | cnti | sumi       |
+----------------------+----------------------------------------------------------------------------------+------+------------+
| read                 | TOTAL                                                                            |  693 | 1487433725 |
| wrote                | TOTAL                                                                            |  693 |  758328651 |
| non_numeric_ahd_code | TOTAL                                                                            |  693 |  675903896 |
| empty_num_result     | Serum_lipids-44O..00_Blood_lipids-1001400069                                     |  683 |    5850739 |
| unknown_id           | TOTAL                                                                            |  693 |    4871795 |
| empty_num_result     | GFR_calculated_abbreviated_MDRD-451E.00_Glomerular_filtration_rate-1001400326    |  666 |    2059709 |
| empty_num_result     | Bone_profile-44Z2.00_Bone_studies-1001400071                                     |  681 |    1843258 |
| empty_num_result     | Laboratory_procedures-4....00_Other_Laboratory_tests-1001400153                  |  661 |    1615716 |
| empty_num_result     | Biochemical_test-44p..00_Other_Laboratory_tests-1001400153                       |  538 |    1491606 |
| empty_num_result     | International_normalised_ratio-42QE.00_International_normalised_ratio-1001400212 |  692 |     895731 |
+----------------------+----------------------------------------------------------------------------------+------+------------+

select *
from resolve_err
where status = 'unknown_id'
order by cnt desc
limit 5;

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'H:\\Medial\\Projects\\General\\thin_etl\\common-signals-count' INTO TABLE just_for_load;

drop table count_common_signals;
create table count_common_signals
(
cnt int,
source varchar(200)
);

INSERT
  INTO count_common_signals
SELECT 
		TRIM(SUBSTRING(l,1,10))
     , TRIM(SUBSTRING(l,11,200))
  FROM just_for_load
  ;

select IF(a2m.ahdcode is null, 0, 1) as has_translation, count(*), avg(cnt), max(cnt), min(cnt)
from count_common_signals c 
left join
ahd_to_medial a2m
on c.source = a2m.ahdcode 
group by has_translation
limit 20;
+-----------------+----------+-------------+----------+----------+
| has_translation | count(*) | avg(cnt)    | max(cnt) | min(cnt) |
+-----------------+----------+-------------+----------+----------+
|               0 |      283 |   3517.2580 |    56268 |      503 |
|               1 |      494 | 497177.2206 |  9250902 |      598 |
+-----------------+----------+-------------+----------+----------+


select * from 
ahd_to_medial a2m
left join
count_common_signals c 
on c.source = a2m.ahdcode 
where c.source is null
and a2m.medial_code not in ('NULL', 'TBD');
+-----------------------------------------------------------------------+-----------------+------+--------+
| ahdcode                                                               | medial_code     | cnt  | source |
+-----------------------------------------------------------------------+-----------------+------+--------+
| InFile                                                                | OutFile         | NULL | NULL   |
| Abnormal_monocytes-42N4.00_Monocyte_count-1001400050                  | MonNum          | NULL | NULL   |
| Full_blood_count_-_FBC-424..00_Haemoglobin-1001400027                 | Hemoglobin      | NULL | NULL   |
| Plasma_viscosity_normal-42B1.00_Other_Laboratory_tests-1001400153     | PlasmaViscosity | NULL | NULL   |
| Random_blood_sugar-44T1.00_Other_Laboratory_tests-1001400153          | RandomGlucose   | NULL | NULL   |
| Serum_zinc_protoporphyrin-44Z4.00_Other_Biochemistry_tests-1001400276 | Zinc            | NULL | NULL   |
| Urea_-_blood-44J..11_Other_Laboratory_tests-1001400153                | Urea            | NULL | NULL   |
+-----------------------------------------------------------------------+-----------------+------+--------+


drop table analyzed_signals;
create table analyzed_signals
(
sig varchar(50),
unit varchar(20),
source varchar(100),
max_cnt int,
cnt int,
cnt_nz int,
uniq int,
c1 varchar(50),
q1 float,
q2 float,
q3 float,
q4 float,
c2 varchar(50),
n_orig_above int,
c3 varchar(50),
skew_clean float,
c4 varchar(50),
std_clean float,
c5 varchar(50),
mean_clean float,
c6 varchar(50),
n_orig_below int,
c7 varchar(50),
n_clean int,
c8 varchar(50),
n_orig int,
c9 varchar(50),
qnz1 float,
qnz2 float,
qnz3 float,
qnz4 float,
max1 varchar(50),
max2 varchar(50),
max3 varchar(50)
)
;

truncate table analyzed_signals;
LOAD DATA LOCAL INFILE 'H:\\Medial\\Projects\\General\\thin_etl\\\all_analyse_units' INTO TABLE analyzed_signals
fields TERMINATED BY '\t'
lines TERMINATED BY '\n'
;

select * from analyzed_signals limit 10;


drop table fixed_signals;
create table fixed_signals
(
sig varchar(50),
unit varchar(20),
cnt int,
status varchar(50),
c1 varchar(50),
q1 float,
q2 float,
q3 float,
q4 float,
c2 varchar(50),
n_orig_above int,
c3 varchar(50),
skew_clean float,
c4 varchar(50),
std_clean float,
c5 varchar(50),
mean_clean float,
c6 varchar(50),
n_orig_below int,
c7 varchar(50),
n_clean int,
c8 varchar(50),
n_orig int,
c9 varchar(50),
qnz1 float,
qnz2 float,
qnz3 float,
qnz4 float
)
;
truncate table fixed_signals;
LOAD DATA LOCAL INFILE 'H:\\Medial\\Projects\\General\\thin_etl\\\all_fix_stats' INTO TABLE fixed_signals
fields TERMINATED BY '\t'
lines TERMINATED BY '\n'
;

select * from fixed_signals limit 10;

select fff.sig, fff.ncl / aaa.ncl as rat from 
	(
	select sig, sum(n_clean) ncl, sum(n_orig) nor
	from fixed_signals
	where status = 'OK'
	group by sig
	)fff
join 
	(
	select sig, sum(n_clean) ncl, sum(n_orig) nor
	from analyzed_signals
	group by sig
	)aaa
on fff.sig = aaa.sig
order by rat asc
limit 22;


select * from (
select sig,unit, max(pct_non_zero)- min(pct_non_zero) as del_pct_non_zero from (
select sig, unit, source, max_cnt, cnt_nz, q1, q2, q3, q4, 1.0*cnt_nz/cnt as pct_non_zero, 1.0*cnt_nz/max_cnt as pct_of_max from analyzed_signals) aaa 
where pct_of_max > 0.02
group by sig, unit )bbb
order by del_pct_non_zero desc
limit 30;

select CONCAT_WS(',',sig, unit, source, 'NA')
from 
(
select sig, unit, source, max_cnt, cnt_nz, q1, q2, q3, q4, 1.0*cnt_nz/cnt as pct_non_zero, 1.0*cnt_nz/max_cnt as pct_of_max from analyzed_signals) aaa 
where pct_of_max > 0.02
and unit = 'null value'
and pct_non_zero > 0.9
order by pct_of_max desc;





drop table thin_demo_stats;
create table thin_demo_stats
(
status varchar(50),
pracid varchar(15) COLLATE latin1_general_cs,
cnt int
)
;

truncate table thin_demo_stats;
LOAD DATA LOCAL INFILE 'W:\\Users\\Ido\\THIN_ETL\\demo\\thin_demo_stats' INTO TABLE thin_demo_stats
fields TERMINATED BY ' '
lines TERMINATED BY '\n'
;

select * from thin_demo_stats limit 10;


select country, sum(cnt)
from 
thin_demo_stats d join thin_prac p 
on d.pracid = p.pracid 
where status = 'processed'
group by country;

+---------+----------+
| country | sum(cnt) |
+---------+----------+
	 E       	 11012318 	
	 I       	   427540 	
	 S       	  1839209 	
	 W       	  1167625 	
+---------+----------+

drop table all_reg;
create table all_reg
(
pid int,
cancer_date int,
cancer_sto varchar(100),
i1 varchar(100),
i2 varchar(100),
i3 varchar(100),
icdo varchar(100),
readcode varchar(100) COLLATE latin1_general_cs -- medcodes are case sensitive!
)
;

truncate table all_reg;
LOAD DATA LOCAL INFILE 'W:\\Users\\Ido\\THIN_ETL\\reg\\all_reg' INTO TABLE all_reg
fields TERMINATED BY '\t'
lines TERMINATED BY '\n'
;

select cancer_sto, count(distinct pid) unique_patients from all_reg 
where cancer_date > 20070101
group by cancer_sto ;

+-----------------------------------------------------------+-----------------+
| cancer_sto                                                | unique_patients |
+-----------------------------------------------------------+-----------------+
| anc,na,na                                                 |           13148 |
| cancer,blood,ALL                                          |             438 |
| cancer,blood,AML                                          |            1496 |
| cancer,blood,CLL                                          |            3499 |
| cancer,blood,CML                                          |             844 |
| cancer,blood,HCL                                          |             185 |
| cancer,blood,HHL                                          |              88 |
| cancer,blood,HODG                                         |            1281 |
| cancer,blood,LEU                                          |            1071 |
| cancer,blood,MDS                                          |            2736 |
| cancer,blood,ML                                           |             270 |
| cancer,blood,MM                                           |            3581 |
| cancer,blood,NHL                                          |            9249 |
| cancer,blood,PCV                                          |             553 |
| cancer,blood,PV                                           |              28 |
| cancer,blood,SID                                          |              32 |
| cancer,blood,THR                                          |            1093 |
| cancer,blood,UNS                                          |            1443 |
| cancer,blood,WAL                                          |             332 |
| cancer,breast,breast                                      |           39202 |
| cancer,kidney,kidney                                      |            4732 |
| cancer,kidney,meta                                        |              75 |
| cancer,na,na                                              |           91185 |
| cancer,uterus,uterus                                      |            4635 |
| ca_bg,crc,colon                                           |              27 |
| ca_bg,crc,rectum                                          |              19 |
| ca_bg,lung,lung                                           |              11 |
| ca_bg,na,na                                               |            9891 |
| ca_bg,oeso,oeso                                           |              19 |
| ca_bg,stom,stom                                           |             327 |
| Digestive Organs,Digestive Organs,Colon                   |           18641 |
| Digestive Organs,Digestive Organs,Esophagus               |            6225 |
| Digestive Organs,Digestive Organs,Liver+intrahepatic bile |            1928 |
| Digestive Organs,Digestive Organs,Pancreas                |            4658 |
| Digestive Organs,Digestive Organs,Rectum                  |            7829 |
| Digestive Organs,Digestive Organs,Stomach                 |            3267 |
| Female genital organs,Ovary,Ovary                         |            4438 |
| Male genital organs,Prostate,Prostate                     |           30615 |
| Metastases To,Digestive System,Colon and Rectum           |              18 |
| Metastases To,Digestive System,Large Intestine and Rectum |              11 |
| Metastases To,Digestive System,Liver                      |            5874 |
| Metastases To,Digestive System,Small Intestine and Rectum |               3 |
| Metastases To,Respiratory System,Lung and Bronchus        |            1698 |
| morph,na,na                                               |           93647 |
| Respiratory system,Lung and Bronchus,Unspecified          |           23294 |
| Urinary Organs,Urinary Organs,Bladder                     |            9992 |
+-----------------------------------------------------------+-----------------+

