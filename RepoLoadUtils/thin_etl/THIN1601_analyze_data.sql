create database THIN1601;

use THIN1601;

drop table just_for_load;
create table just_for_load
(
l varchar(1000)
)
;

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\Readcodes1601.txt' INTO TABLE just_for_load;

drop table readcodes;
create table readcodes
(
medcode varchar(7) COLLATE latin1_general_cs, -- medcodes are case sensitive!
description varchar(60))
;

INSERT
  INTO readcodes
SELECT TRIM(SUBSTRING(l,1,7)) AS medcode
     , TRIM(SUBSTRING(l,8,60)) AS description
  FROM just_for_load
  ;

select medcode, count(*) cnt
from readcodes
group by medcode
having cnt >= 2;

delete from readcodes where medcode in ('Rz...11', '9Z...11');

alter table readcodes add primary key (medcode);




truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\ThinPrac1601.txt' INTO TABLE just_for_load;

drop table thin_prac;
create table thin_prac
(
pracid varchar(15) COLLATE latin1_general_cs,
country varchar(1)
);

INSERT
  INTO thin_prac
SELECT TRIM(SUBSTRING(l,1,5)) AS pracid
     , TRIM(SUBSTRING(l,46,1)) AS country
  FROM just_for_load
  ;

select * from thin_prac limit 10;





truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\AHDlookups1601.txt' INTO TABLE just_for_load;

drop table ahdlookups;
create table ahdlookups
(
dataname varchar(8),
datadesc varchar(30),
lookup varchar(6),
lookupdesc varchar(100)
)
;

INSERT
  INTO ahdlookups
SELECT TRIM(SUBSTRING(l,1,7))
     , TRIM(SUBSTRING(l,9,30)) 
     , TRIM(SUBSTRING(l,39,6)) 
     , TRIM(SUBSTRING(l,45,100)) 
  FROM just_for_load
  ;

drop table ahdcodes;
create table ahdcodes
(
datafile varchar(8),
ahdcode varchar(10),
description varchar(100),
data1 varchar(30),
data2 varchar(30),
data3 varchar(30),
data4 varchar(30),
data5 varchar(30),
data6 varchar(30)
)  
;

alter table ahdcodes add primary key (ahdcode);


truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\AHDCodes1601.txt' INTO TABLE just_for_load;

INSERT
  INTO ahdcodes
SELECT TRIM(SUBSTRING(l,1,8)) 
     , TRIM(SUBSTRING(l,9,10)) 
     , TRIM(SUBSTRING(l,19,100)) 
     , TRIM(SUBSTRING(l,119,30)) 
     , TRIM(SUBSTRING(l,149,30)) 
     , TRIM(SUBSTRING(l,179,30)) 
     , TRIM(SUBSTRING(l,209,30)) 
     , TRIM(SUBSTRING(l,239,30)) 
     , TRIM(SUBSTRING(l,269,30)) 
  FROM just_for_load
  ;
  

drop table ahdfreq;
create table ahdfreq
(
ahdcode varchar(10),
description varchar(100),
freq integer
)  
;

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\AHDcodeFrequencyEver1601.txt' INTO TABLE just_for_load;

INSERT
  INTO ahdfreq
SELECT TRIM(SUBSTRING(l,1,10)) 
     , TRIM(SUBSTRING(l,11,100)) 
     , TRIM(SUBSTRING(l,111,10))
  FROM just_for_load
  ;


drop table readcodefreq;
create table readcodefreq
(
medcode varchar(7) COLLATE latin1_general_cs, 
description varchar(100),
freq integer,
source varchar(40)
)  
;

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\AHDReadcodeFrequencyEver1601.txt ' INTO TABLE just_for_load
lines TERMINATED BY '\r\n';

INSERT
  INTO readcodefreq
SELECT TRIM(SUBSTRING(l,1,7)) 
     , TRIM(SUBSTRING(l,8,60)) 
     , TRIM(SUBSTRING(l,68,10))
	 , 'AHDReadcodeFrequencyEver1601'
  FROM just_for_load
  ;

truncate table just_for_load;  
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\MedicalReadcodeFrequencyEver1601.txt ' INTO TABLE just_for_load
lines TERMINATED BY '\r\n';

INSERT
  INTO readcodefreq
SELECT TRIM(SUBSTRING(l,1,7)) 
     , TRIM(SUBSTRING(l,8,60)) 
     , TRIM(SUBSTRING(l,68,10))
	 , 'MedicalReadcodeFrequencyEver1601'
  FROM just_for_load
  ;
  

drop table ahd;
create table ahd
(
pracid varchar(15) COLLATE latin1_general_cs,
patid varchar(15) COLLATE latin1_general_cs,
eventdate varchar(15),
ahdcode varchar(15),
ahdflag varchar(15),
data1 varchar(15),
data2 varchar(15),
data3 varchar(15),
data4 varchar(15),
data5 varchar(15),
data6 varchar(15),
medcode varchar(15) COLLATE latin1_general_cs, -- medcodes are case sensitive!
source varchar(15),
nhsspec varchar(15),
locate varchar(15),
staffid varchar(15),
textid varchar(15),
category varchar(15),
ahdinfo varchar(15),
inprac varchar(15),
private_field varchar(15),
ahdid varchar(15),
consultid varchar(15) COLLATE latin1_general_cs,
sysdate_field varchar(15),
modified  varchar(15)
)
;

truncate table ahd;

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINDB1601\\ahd.a6641' INTO TABLE just_for_load;


INSERT
  INTO ahd
SELECT 
		'a6641'
	 ,TRIM(SUBSTRING(l,1,4))
     , TRIM(SUBSTRING(l,5,8))
     , TRIM(SUBSTRING(l,13,10)) 
     , TRIM(SUBSTRING(l,23,1))
     , TRIM(SUBSTRING(l,24,13)) 
     , TRIM(SUBSTRING(l,37,13)) 
     , TRIM(SUBSTRING(l,50,13)) 
     , TRIM(SUBSTRING(l,63,13)) 
     , TRIM(SUBSTRING(l,76,13)) 
     , TRIM(SUBSTRING(l,89,13)) 
     , TRIM(SUBSTRING(l,102,7)) 
     , TRIM(SUBSTRING(l,109,1)) 
     , TRIM(SUBSTRING(l,110,3)) 
     , TRIM(SUBSTRING(l,113,2)) 
     , TRIM(SUBSTRING(l,115,4)) 
     , TRIM(SUBSTRING(l,119,7)) 
     , TRIM(SUBSTRING(l,126,1)) 
     , TRIM(SUBSTRING(l,127,1)) 
     , TRIM(SUBSTRING(l,128,1)) 
     , TRIM(SUBSTRING(l,129,1)) 
     , TRIM(SUBSTRING(l,130,4)) 
     , TRIM(SUBSTRING(l,134,4)) 
     , TRIM(SUBSTRING(l,138,8)) 
     , TRIM(SUBSTRING(l,146,1)) 
  FROM just_for_load
  ;

alter table ahd add index(medcode);
alter table ahd add index(ahdcode);
alter table ahd add index(patid);




drop table patient;
create table patient
(
pracid varchar(15),
patid varchar(15) COLLATE latin1_general_cs,
patflag varchar(15),
yob int,
famnum int,
sex int,
regdate int,
regstat int,
xferdate int,
regrea int,
deathdate int,
deathinfo varchar(15),
accept int,
institute varchar(15),
marital int,
dispensing varchar(15),
prscexempt int,
sysdat int
)
;

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINDB1601\\patient.a6641' INTO TABLE just_for_load;

truncate table patient;

INSERT
  INTO patient
SELECT 
		'a6641'
	 ,TRIM(SUBSTRING(l,1,4))
     , TRIM(SUBSTRING(l,5,1))
     , TRIM(SUBSTRING(l,6,8)) 
     , TRIM(SUBSTRING(l,14,6))
     , TRIM(SUBSTRING(l,20,1)) 
     , TRIM(SUBSTRING(l,21,8)) 
     , TRIM(SUBSTRING(l,29,2)) 
     , TRIM(SUBSTRING(l,31,8)) 
     , TRIM(SUBSTRING(l,39,2)) 
     , TRIM(SUBSTRING(l,41,8)) 
     , TRIM(SUBSTRING(l,49,1)) 
     , TRIM(SUBSTRING(l,50,1)) 
     , TRIM(SUBSTRING(l,51,1)) 
     , TRIM(SUBSTRING(l,52,2)) 
     , TRIM(SUBSTRING(l,54,1)) 
     , TRIM(SUBSTRING(l,55,2)) 
     , TRIM(SUBSTRING(l,57,8)) 
  FROM just_for_load
  ;

alter table patient add index(patid)
;

drop table medical;
create table medical
(
pracid varchar(5),
patid varchar(4) COLLATE latin1_general_cs,
eventdate varchar(8),
enddate varchar(8),
datatype int,
medcode varchar(7) COLLATE latin1_general_cs, -- medcodes are case sensitive!
medflag varchar(1),
staffid varchar(4),
source varchar(1),
episode varchar(1),
nhsspec varchar(3),
locate varchar(2),
textid varchar(7),
category varchar(7),
priority varchar(7),
medinfo varchar(1),
inprac varchar(1),
private_field varchar(1),
medid varchar(4),
consultid varchar(4) COLLATE latin1_general_cs,
sysdate_field varchar(8),
modified varchar(1)
)  
;


truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINDB1601\\medical.a6641' INTO TABLE just_for_load;

INSERT
  INTO medical
SELECT 
	'a6641'
	 , TRIM(SUBSTRING(l,1,4)) 
     , TRIM(SUBSTRING(l,5,8)) 
     , TRIM(SUBSTRING(l,13,8)) 
     , TRIM(SUBSTRING(l,21,2)) 
     , TRIM(SUBSTRING(l,23,7)) 
     , TRIM(SUBSTRING(l,30,1)) 
     , TRIM(SUBSTRING(l,31,4)) 
     , TRIM(SUBSTRING(l,35,1)) 
     , TRIM(SUBSTRING(l,36,1)) 
     , TRIM(SUBSTRING(l,37,3)) 
     , TRIM(SUBSTRING(l,40,2)) 
     , TRIM(SUBSTRING(l,42,7)) 
     , TRIM(SUBSTRING(l,49,1)) 
     , TRIM(SUBSTRING(l,50,1)) 
     , TRIM(SUBSTRING(l,51,1)) 
     , TRIM(SUBSTRING(l,52,1)) 
     , TRIM(SUBSTRING(l,53,1)) 
     , TRIM(SUBSTRING(l,54,4)) 
     , TRIM(SUBSTRING(l,58,4)) 
     , TRIM(SUBSTRING(l,62,8)) 
     , TRIM(SUBSTRING(l,70,1)) 
  FROM just_for_load
  ;

  
  

drop table consult;
create table consult
(
pracid varchar(5),
consultid varchar(4)  COLLATE latin1_general_cs,
patid varchar(4)  COLLATE latin1_general_cs,
staffid varchar(4),
eventdate varchar(8),
sysdate_field varchar(8),
systime_field varchar(8),
constype varchar(3),
duration varchar(6)
)  
;

alter table consult add primary key (pracid, patid, consultid);


truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINDB1601\\consult.a6641' INTO TABLE just_for_load;

INSERT
  INTO consult
SELECT 
	'a6641'
	 , TRIM(SUBSTRING(l,1,4)) 
     , TRIM(SUBSTRING(l,5,4)) 
     , TRIM(SUBSTRING(l,9,4)) 
     , TRIM(SUBSTRING(l,13,8)) 
     , TRIM(SUBSTRING(l,21,8)) 
     , TRIM(SUBSTRING(l,29,6)) 
     , TRIM(SUBSTRING(l,35,3)) 
     , TRIM(SUBSTRING(l,38,6)) 
  FROM just_for_load
  ;  
  

drop table nhs;
create table nhs
(
nhsspec varchar(3),
specialty varchar(30),
subspec varchar(50)
);

truncate table just_for_load;
LOAD DATA LOCAL INFILE 'T:\\THIN1601\\THINAncil1601\\text\\NHSspeciality1601.txt' INTO TABLE just_for_load;

INSERT
  INTO nhs
SELECT 
	   TRIM(SUBSTRING(l,1,3)) 
     , TRIM(SUBSTRING(l,4,30)) 
     , TRIM(SUBSTRING(l,34,50)) 
  FROM just_for_load
  ;

alter table nhs add primary key (nhsspec);
  
select m.private_field, m.nhsspec, max(specialty), max(subspec), count(distinct m.pracid, m.patid) cnt_patients, count(*) cnt_records,
count(distinct r.medcode) codes_handled, avg(duration), std(duration),
max(r.description) example_for_code
from medical m 
join 
readcodes r
on m.medcode = r.medcode
left join nhs n
on m.nhsspec = n.nhsspec
left join consult c
on m.pracid = c.pracid and m.patid = c.patid and m.consultid = c.consultid
group by m.private_field, m.nhsspec
having cnt_patients > 50
order by cnt_patients desc 
;
+---------+------------------+--------------------------+--------------+-------------+---------------+-------------------------------------------------+
| nhsspec | max(specialty)   | max(subspec)             | cnt_patients | cnt_records | codes_handled | example_for_code                                |
+---------+------------------+--------------------------+--------------+-------------+---------------+-------------------------------------------------+
| 000     | NULL             | NULL                     |        25097 |     7438061 |         27911 | _Converted code                                 |
|         | NULL             | NULL                     |         3320 |        4897 |           251 | [X]Depression NOS                               |
| AGG     | Orthopaedic      | Trauma and Orthopaedics  |          841 |        1059 |            24 | Sprain wrist ligament                           |
| CDX     |                  | Accident and Emergency   |          800 |        1068 |            81 | [D]Retention of urine                           |
| AYU     | Ophthalmology    | Ophthalmology            |          798 |         981 |            17 | Retinal detachments and defects                 |
| CDN     |                  | ENT                      |          745 |         870 |            23 | Sore throat symptom                             |
| CDK     |                  | General Surgical         |          518 |         589 |            41 | Swelling                                        |
| CEW     |                  | Paediatrics              |          494 |         645 |            26 | Referral to respiratory physician               |
| CEL     |                  | Cardiology               |          474 |         553 |            22 | [D]Syncope                                      |
| CEA     |                  | Gastroenterology         |          469 |         541 |            18 | Referred to hepatology service                  |
| ARB     | Gynaecology      | Gynaecology              |          465 |         598 |            20 | Vaginal discharge symptom                       |
| CDL     |                  | Urology                  |          438 |         516 |            27 | [D]Groin pain                                   |
| CGI     |                  | Physiotherapy            |          432 |         519 |            25 | Wrist joint pain                                |
| CHQ     | Obstetrics       | Obstetrics & Gynaecology |          416 |         495 |             6 | Serum pregnancy test (B-HCG)                    |
| CEV     |                  | Rheumatology             |          373 |         440 |            15 | Shoulder pain                                   |
| CEM     |                  | Dermatology              |          326 |         368 |            20 | Urgent referral                                 |
| CET     |                  | Neurology                |          294 |         338 |            21 | [D]Seizure NOS                                  |
| CDZ     |                  | General Medicine         |          281 |         303 |            45 | [D]Haemoptysis                                  |
| CDM     |                  | Trauma and Orthopaedics  |          280 |         306 |            32 | [D]Gait abnormality                             |
| BIY     | Dermatology      | Dermatology              |          277 |         337 |            21 | [M]Melanoma NOS                                 |
| CGB     |                  | Adult Psychiatry         |          225 |         263 |            29 | Transurethral prostatectomy                     |
| CDO     |                  | Ophthalmology            |          203 |         227 |            19 | Visual symptoms                                 |
| BZJ     | Other            | Radiology                |          181 |         196 |             4 | Referral for echocardiography                   |
| CFB     |                  | Gynaecology              |          152 |         164 |            30 | Vaginal bleeding                                |
| CDU     |                  | Plastic Surgery          |          149 |         179 |            17 | Skin lesion                                     |
| CEF     |                  | Audiological Medicine    |          146 |         154 |            10 | Urinalysis - general                            |
| CFR     |                  | Haematology              |          131 |         146 |             6 | Referred to hepatology service                  |
| CEN     |                  | Thoracic Medicine        |          119 |         125 |            19 | Referred to chest physician                     |
| CMG     |                  | Vascular Surgeons        |          117 |         126 |             9 | Vascular surgery                                |
| SUR     | General Surgical |                          |          109 |         113 |             7 | Referral to general surgery special interest GP |
| CEB     |                  | Endocrinology            |          109 |         120 |            20 | Type 2 diabetes mellitus                        |
+---------+------------------+--------------------------+--------------+-------------+---------------+-------------------------------------------------+


select m.consultid, m.pracid, m.patid, specialty, 
cast(c.duration as unsigned),
subspec, m.medcode, a.medcode, r1.description, r2.description 
from 
medical m 
left join 
ahd a
on m.pracid = a.pracid and m.patid = a.patid and m.consultid = a.consultid
left join readcodes r1 
on m.medcode = r1.medcode
left join readcodes r2
on a.medcode = r2.medcode
left join nhs n
on m.nhsspec = n.nhsspec
left join consult c
on m.pracid = c.pracid and m.patid = c.patid and m.consultid = c.consultid
where m.nhsspec is not null and m.nhsspec not in ('', '000')
limit 40;

select * from 
(
	select medcode, count(distinct pracid, patid) as cnt_patients, count(*) as cnt
	from medical m 
	group by medcode
) m 
left join
readcodes r
on m.medcode = r.medcode
order by cnt_patients desc
limit 300;



select * from readcodes
where description like '%hospital%'
limit 100;

select count(distinct patid) from ahd
where pracid = 'f6648';
+-----------------------+
| count(distinct patid) |
+-----------------------+
|                 47671 |
+-----------------------+

select count(distinct patid) from patient
where pracid = 'f6648';
+-----------------------+
| count(distinct patid) |
+-----------------------+
|                 53369 |
+-----------------------+

select pracid, patflag, count(distinct patid) cnt from patient
group by pracid, patflag
order by pracid, cnt desc;

select * from ahd a
left join
patient p
on a.pracid = p.pracid and a.patid = p.patid
where a.pracid = 'f6648'
and p.patid is null
limit 10;

select count(distinct patid), count(*)   from patient;

select patid, count(*) cnt
from patient
group by patid
having cnt > 1
limit 10;


  
select count(*) from ahdcodes where datafile = "TEST" and data2 = "NUM_RESULT";
--151


select count(*), count(distinct patid) from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode;
+----------+-----------------------+
| count(*) | count(distinct patid) |
+----------+-----------------------+
|  2187774 |                  6251 |
+----------+-----------------------+
1 row in set (1 min 30.40 sec)

select count(*), count(distinct patid) from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode
where codes.datafile = "TEST" and codes.data2 = "NUM_RESULT";
+----------+-----------------------+
| count(*) | count(distinct patid) |
+----------+-----------------------+
|  1249326 |                  4920 |
+----------+-----------------------+
1 row in set (32.32 sec)

select codes.description, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode
where codes.datafile = "TEST" and codes.data2 = "NUM_RESULT"
group by codes.description
having cnt > 50
order by cnt desc
limit 15
;
+-------------------------------+-------+---------+
| description                   | cnt   | cnt_dis |
+-------------------------------+-------+---------+
| Other Laboratory tests        | 65796 |    4104 |
| Serum creatinine              | 46024 |    4048 |
| Glomerular filtration rate    | 42539 |    4002 |
| Serum cholesterol             | 42010 |    4039 |
| Urea - blood                  | 41613 |    4018 |
| Potassium                     | 41287 |    4008 |
| Sodium                        | 41207 |    4008 |
| Albumin                       | 40591 |    4018 |
| Alkaline Phosphatase          | 40437 |    4018 |
| Gamma Glutamyl Transpeptidase | 39716 |    4006 |
| Bilirubin                     | 39304 |    4009 |
| Aspartate Aminotransferase    | 39156 |    3997 |
| Red blood cell count          | 31665 |    4046 |
| Calcium                       | 29740 |    3947 |
| Calcium adjusted              | 29497 |    3939 |
+-------------------------------+-------+---------+
15 rows in set (2.26 sec)

select pracid, count(distinct patid), count(*) cnt 
from 
ahd a
group by pracid
;
+--------+-----------------------+---------+
| pracid | count(distinct patid) | cnt     |
+--------+-----------------------+---------+
| a6641  |                 15915 | 2187774 |
| a6658  |                  9346 |  664126 |
+--------+-----------------------+---------+

select pracid, count(distinct patid), count(*) cnt 
from 
medical a
group by pracid
;

select sum(cnt_cnt) from 
(
	select cnt_proc, count(*) cnt_cnt from (
		select pracid, patid, count(distinct codes.ahdcode) as cnt_proc
		from 
		ahd a
		left join
		ahdcodes codes
		on a.ahdcode = codes.ahdcode
		group by pracid, patid)aaa
	group by cnt_proc
	order by cnt_proc
)bbb



select r.medcode, r.description, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
join
readcodes r
on a.medcode = r.medcode
join
ahdcodes c
on a.ahdcode = c.ahdcode
where (c.datafile != "TEST" and c.data2 != "NUM_RESULT") and c.
group by r.medcode, r.description
having cnt_dis > 50
order by cnt_dis desc
limit 222
;



select codes.medcode, codes.description, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
medical a
join
readcodes codes
on a.medcode = codes.medcode
group by codes.medcode, codes.description
having cnt_dis > 50
order by cnt_dis desc
limit 222
;


select ahdcode, ahddesc, count(distinct patid) as cnt_dis, count(patid) as cnt_bad, round(avg(cnt), 2) avgi, round(std(cnt), 2) stdi
from (
	select patid, codes.ahdcode as ahdcode, codes.description as ahddesc, count(*) cnt 
	from 
	ahd a
	join
	ahdcodes codes
	on a.ahdcode = codes.ahdcode
	/*where codes.datafile = "TEST" and codes.data2 = "NUM_RESULT"
	and eventdate > '20100000'*/
	group by patid, ahdcode, ahddesc

)aa
group by ahdcode, ahddesc
having cnt_dis > 500
order by cnt_dis desc, avgi desc
;

+--------------------------------+---------+-------+--------------------+
| ahddesc                        | cnt_dis | avgi  | stdi               |
+--------------------------------+---------+-------+--------------------+
| Other Laboratory tests         |    3610 | 11.83 |              13.82 |
| Serum creatinine               |    3592 |  7.98 |              10.04 |
| Glomerular filtration rate     |    3586 |  7.84 |               9.86 |
| Red blood cell count           |    3585 |  5.90 |               9.01 |
| Urea - blood                   |    3573 |  7.45 |               9.39 |
| Albumin                        |    3573 |  7.23 |               9.06 |
| Alkaline Phosphatase           |    3571 |  7.22 |               9.05 |
| Sodium                         |    3570 |  7.43 |               9.36 |
| Potassium                      |    3569 |  7.43 |               9.37 |
| Bilirubin                      |    3560 |  6.99 |               8.89 |
| Serum cholesterol              |    3560 |  6.85 |               6.48 |
| Gamma Glutamyl Transpeptidase  |    3553 |  7.03 |               8.94 |
| Aspartate Aminotransferase     |    3553 |  6.98 |               8.90 |
| Calcium                        |    3514 |  5.49 |               4.95 |
| Calcium adjusted               |    3513 |  5.49 |               4.94 |
| Total protein                  |    3478 |  5.21 |               4.61 |
| Haemoglobin                    |    3357 |  5.49 |               8.80 |
| White blood count              |    3355 |  5.43 |               8.71 |
| Platelets                      |    3354 |  5.42 |               8.67 |
| Mean corpuscular haemoglobin   |    3353 |  5.41 |               8.66 |
| Packed Cell Volume             |    3353 |  5.41 |               8.66 |
| Mean corpuscular volume        |    3353 |  5.41 |               8.67 |
| MCH Hb Concentration           |    3353 |  5.41 |               8.66 |
| Neutrophil count               |    3289 |  5.14 |               8.16 |
| Basophil count                 |    3289 |  5.13 |               8.15 |
| Lymphocyte count               |    3288 |  5.13 |               8.15 |
| Eosinophil count               |    3287 |  5.12 |               8.12 |
| Monocyte count                 |    3287 |  5.12 |               8.12 |
| Blood glucose                  |    2925 |  3.51 |               3.02 |
| Thyroid Stimulating Hormone    |    2704 |  3.30 |               3.67 |
| Free Thyroxine                 |    2701 |  3.25 |               3.55 |
| Low Density Lipoprotein        |    2273 |  3.76 |               3.28 |
| High Density Lipoprotein       |    2273 |  3.13 |               2.73 |
| Triglycerides                  |    2270 |  3.13 |               2.73 |
| Hb A1C - Diabetic control      |    2251 |  4.04 |               5.16 |
| Erythrocyte sedimentation rate |    2140 |  3.84 |               7.92 |
| Blood lipid ratios             |    2059 |  2.74 |               2.26 |
| C Reactive protein             |    2013 |  3.77 |               7.73 |
| Serum chloride                 |    1837 |  5.00 |               9.51 |
| Serum bicarbonate              |    1837 |  4.98 |               9.51 |
| Alanine Aminotransferase       |    1778 |  4.45 |               9.76 |
| Serum ferritin                 |    1603 |  2.38 |               2.16 |
| Serum iron tests               |    1492 |  2.26 |               2.00 |
| Total iron binding capacity    |    1487 |  3.35 |               3.16 |
| Urine Biochemistry             |    1119 |  7.69 |               6.34 |
| Enzymes/Specific proteins      |    1116 |  1.85 |               1.44 |
| Albumin Creatinine Ratio       |    1077 |  5.29 |               4.12 |
| Folate level                   |    1010 |  1.85 |               1.53 |
| Serum Inorganic Phosphate      |     922 |  1.93 |               2.01 |
| B12 Levels                     |     812 |  1.65 |               1.31 |
| Temperature                    |     657 |  1.28 |               0.74 |
| PF current                     |     613 |  3.61 |               3.14 |
| Blood trace elements/vitamins  |     600 |  2.17 |               2.51 |
| B12 & Folate level             |     575 |  2.49 |               1.78 |
| Follicle Stimulating Hormone   |     564 |  1.53 |               1.05 |
| Oestradiol level               |     550 |  1.58 |               1.12 |
+--------------------------------+---------+-------+--------------------+

select r.description, count(*) cnt, count(distinct patid) cnt_dis from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode
join readcodes r
on a.medcode = r.medcode
where codes.datafile = "TEST" and codes.data2 = "NUM_RESULT" and codes.description = "Other Laboratory tests"
and eventdate > '20100000'
group by r.description
having cnt > 50
order by cnt desc
;
+--------------------------------------------+-------+---------+
| description                                | cnt   | cnt_dis |
+--------------------------------------------+-------+---------+
| Laboratory procedures                      | 34751 |    3290 |
| Epithelial cell count                      |  3941 |    1611 |
| Lipid fractionation                        |  3689 |    1671 |
| Plasma pro-brain natriuretic peptide level |   147 |     128 |
+--------------------------------------------+-------+---------+
4 rows in set (0.16 sec)


drop table ahd_to_medial;
create table ahd_to_medial
(
ahdcode varchar(120),
medial_code varchar(50)
)
;

truncate table ahd_to_medial;
LOAD DATA LOCAL INFILE 'H:\\Medial\\Projects\\General\\thin_etl\\thin_signals_to_united.txt' INTO TABLE ahd_to_medial
fields TERMINATED BY '\t'
lines TERMINATED BY '\r\n'
;


select * from ahdcodes  a
where a.ahdcode = 1005010500 /*blood pressure*/
;
+----------+------------+----------------+-----------+----------+-----------+------------+------------+---------+
| datafile | ahdcode    | description    | data1     | data2    | data3     | data4      | data5      | data6   |
+----------+------------+----------------+-----------+----------+-----------+------------+------------+---------+
| CLINICAL | 1005010500 | Blood pressure | DIASTOLIC | SYSTOLIC | KOROTKOFF | EVENT_TIME | LATERALITY | POSTURE |
+----------+------------+----------------+-----------+----------+-----------+------------+------------+---------+


select c.*, f.freq, bbb.d1, bbb.d2, bbb.d3, bbb.d4, bbb.d5, bbb.d6
from 
ahdcodes c
join 
ahdfreq f 
on c.ahdcode = f.ahdcode
join 
(
	select ahdcode,
	COUNT(NULLIF(TRIM(data1), '')) as d1,
	COUNT(NULLIF(TRIM(data2), '')) as d2,
	COUNT(NULLIF(TRIM(data3), '')) as d3,
	COUNT(NULLIF(TRIM(data4), '')) as d4,
	COUNT(NULLIF(TRIM(data5), '')) as d5,
	COUNT(NULLIF(TRIM(data6), '')) as d6
	from ahd a
	group by  a.ahdcode
)bbb
on c.ahdcode = bbb.ahdcode
where datafile = 'TEST'
and data2 != 'NUM_RESULT'
order by freq desc
limit 30;
+----------+------------+-------------------+----------------------------+-----------------+------------------+---------------------+---------------------------+-----------------+--------+--------+-------+-------+------+-------+
| datafile | ahdcode    | description       | data1                      | data2           | data3            | data4               | data5                     | data6           | d1     | d2     | d3    | d4    | d5   | d6    |
+----------+------------+-------------------+----------------------------+-----------------+------------------+---------------------+---------------------------+-----------------+--------+--------+-------+-------+------+-------+
| CLINICAL | 1005010500 | Blood pressure    | DIASTOLIC                  | SYSTOLIC        | KOROTKOFF        | EVENT_TIME          | LATERALITY                | POSTURE         | 109441 | 109441 |     2 | 22812 | 6260 | 22824 |
| CLINICAL | 1003040000 | Smoking           | SMOKER                     | CIGARETTES(DAY) | CIGARS(DAY)      | TOBACCO_OUNCES(DAY) | STARTSMOKE(DATE)          | STOPSMOKE(DATE) |  63282 |  54346 |    34 |    43 |   48 |  1855 |
| CLINICAL | 1005010200 | Weight            | WEIGHT(KG)                 | CENTILE         | BMI              |                     |                           |                 |  61657 |     16 | 56789 |     0 |    0 |     0 |
| CLINICAL | 1066000000 | Medication review | DUE(DATE)                  | REVIEW(DATE)    | NEXT(REVIEW)     |                     |                           |                 |  35091 |  28854 | 28481 |     0 |    0 |     0 |
| CLINICAL | 1064100000 | Advice given      | ADVICE_GIVEN               | ADVICE_TYPE     |                  |                     |                           |                 |  23125 |  13548 |     0 |     0 |    0 |     0 |
| CLINICAL | 1008050000 | Cervical          | READ_CODE                  | IN_PRAC         | REPORT(DATE)     | EXCLUDE_TARGET(Y/N) | CERVICAL_EXCLUSION_REASON | ADEQUATE(Y/N)   |    210 |  15820 |    37 | 15820 |    7 | 15562 |
| CLINICAL | 1003050000 | Alcohol           | DRINKER                    | UNITS(WEEK)     | STARTDRINK(DATE) | STOPDRINK(DATE)     |                           |                 |  23531 |  20614 |     1 |   202 |    0 |     0 |
| CLINICAL | 1005010100 | Height            | HEIGHT(M)                  | CENTILE         |                  |                     |                           |                 |  50651 |     13 |     0 |     0 |    0 |     0 |
| CLINICAL | 1090000000 | Family History    | READ_CODE                  |                 |                  |                     |                           |                 |   1477 |      0 |     0 |     0 |    0 |     0 |
| CLINICAL | 1002550000 | Contraception     | CONTRACEPTIVE_SERVICE_TYPE | IUCDDATE        | DRUG_CODE        | CLAIM_EXPIRY(DATE)  |                           |                 |    577 |     12 |     0 |   545 |    0 |     0 |
+----------+------------+-------------------+----------------------------+-----------------+------------------+---------------------+---------------------------+-----------------+--------+--------+-------+-------+------+-------+



select *
from 
ahdcodes c
join 
ahdfreq f 
on c.ahdcode = f.ahdcode
left join 
(
	select ahdcode,
	count(distinct pracid, patid) as cnt_dis,
	count(*) as cnt,
	COUNT(NULLIF(TRIM(data1), '')) as d1,
	COUNT(NULLIF(TRIM(data2), '')) as d2,
	COUNT(NULLIF(TRIM(data3), '')) as d3,
	COUNT(NULLIF(TRIM(data4), '')) as d4,
	COUNT(NULLIF(TRIM(data5), '')) as d5,
	COUNT(NULLIF(TRIM(data6), '')) as d6
	from ahd a
	group by  a.ahdcode
)bbb
on c.ahdcode = bbb.ahdcode
order by freq desc
INTO OUTFILE 'ahdcodes_freq_and_desc.csv'
;




/* Smoking */

select data1, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
where ahdcode = 1003040000 
and data6 != ''
group by data1
limit 50;
+-------+-------+---------+
| data1 | cnt   | cnt_dis |
+-------+-------+---------+
| D     | 38450 |   10117 |
| N     | 79000 |   22507 |
| Y     | 63799 |   15906 |
+-------+-------+---------+

select data1, avg(data2), std(data2), COUNT(NULLIF(TRIM(data2), '')) as d2
from ahd a
where ahdcode = 1003040000 
and data2 != '' and data2 < 100 and data2 > 0
group by data1
limit 50;
+-------+--------------------+--------------------+-------+
| data1 | avg(data2)         | std(data2)         | d2    |
+-------+--------------------+--------------------+-------+
| D     | 16.197655334114888 | 13.054618570255167 |  4265 |
| N     |              18.75 |  8.926785535678562 |     4 |
| Y     | 14.435873975654388 |   9.17903260391144 | 25138 |
+-------+--------------------+--------------------+-------+

select r.medcode, r.description, count(*) cnt from 
ahd a
join readcodes r
on a.medcode = r.medcode
where ahdcode = 1003040000 
and data1 = 'D'
group by r.medcode, r.description
having cnt > 200
order by cnt desc
limit 10;
+---------+--------------------------------+-------+
| medcode | description                    | cnt   |
+---------+--------------------------------+-------+
| 137S.00 | Ex smoker                      | 31970 |
| 137K.00 | Stopped smoking                |  3580 |
| 137F.00 | Ex-smoker - amount unknown     |  1109 |
| 1379.00 | Ex-moderate smoker (10-19/day) |   700 |
| 137A.00 | Ex-heavy smoker (20-39/day)    |   558 |
| 1378.00 | Ex-light smoker (1-9/day)      |   284 |
+---------+--------------------------------+-------+

select r.medcode, r.description, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode
join readcodes r
on a.medcode = r.medcode
where codes.ahdcode = 1003040000 
group by r.medcode, r.description
having count(*) > 150
order by cnt desc
;
+---------+--------------------------------+-------+---------+
| medcode | description                    | cnt   | cnt_dis |
+---------+--------------------------------+-------+---------+
| 1371.00 | Never smoked tobacco           | 54867 |   18961 |
| 137R.00 | Current smoker                 | 44162 |   12470 |
| 137S.00 | Ex smoker                      | 31970 |    8628 |
| 1371.11 | Non-smoker                     | 14065 |    5549 |
| 137L.00 | Current non-smoker             | 10154 |    5924 |
| 137P.00 | Cigarette smoker               |  7354 |    4089 |
| 137K.00 | Stopped smoking                |  3580 |    2399 |
| 1374.00 | Moderate smoker - 10-19 cigs/d |  3543 |    2861 |
| 1375.00 | Heavy smoker - 20-39 cigs/day  |  2269 |    1787 |
| 1373.00 | Light smoker - 1-9 cigs/day    |  1732 |    1467 |
| 8CAL.00 | Smoking cessation advice       |  1447 |    1031 |
| 137F.00 | Ex-smoker - amount unknown     |  1109 |     996 |
| 137..00 | Tobacco consumption            |   957 |     697 |
| 1372.11 | Occasional smoker              |   919 |     628 |
| 1379.00 | Ex-moderate smoker (10-19/day) |   700 |     625 |
| 137A.00 | Ex-heavy smoker (20-39/day)    |   558 |     504 |
| 1378.00 | Ex-light smoker (1-9/day)      |   284 |     272 |
| 1372.00 | Trivial smoker - < 1 cig/day   |   261 |     255 |
| 137Z.00 | Tobacco consumption NOS        |   190 |     190 |
| 137E.00 | Tobacco consumption unknown    |   181 |     176 |
| 1376.00 | Very heavy smoker - 40+cigs/d  |   164 |     143 |
| 137P.11 | Smoker                         |   151 |     149 |
+---------+--------------------------------+-------+---------+


select count(*), count(distinct pracid, patid) cnt_dis from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode
where codes.ahdcode = 1003040000 
+----------+---------+
| count(*) | cnt_dis |
+----------+---------+
|   181249 |   38232 |
+----------+---------+

select cnt, count(*)as cnt_cnt from 
(
select pracid, patid, count(distinct eventdate) cnt from 
ahd a
where a.ahdcode = 1003040000 
group by pracid, patid
) smokes
group by cnt
order by cnt 
;
+-----+---------+
| cnt | cnt_cnt |
+-----+---------+
|   1 |   11479 |
|   2 |    6266 |
|   3 |    3940 |
|   4 |    2867 |
|   5 |    2224 |
|   6 |    1864 |
|   7 |    1600 |
|   8 |    1292 |
|   9 |    1161 |
|  10 |     939 |
|  11 |     822 |
|  12 |     683 |
|  13 |     593 |
|  14 |     499 |
|  15 |     386 |
|  16 |     286 |
|  17 |     266 |
|  18 |     221 |
|  19 |     150 |


select cnt, mind1, maxd1, count(*) cnt_cnt 
from 
(
	select pracid, patid, eventdate, count(*) as cnt, min(data1) mind1, max(data1) maxd1
	from 
	ahd a
	where a.ahdcode = 1003040000 
	group by pracid, patid, eventdate
	having cnt >= 2 
)aaa
group by cnt, mind1, maxd1
having cnt_cnt > 50
order by cnt_cnt desc 
;
+-----+-------+-------+---------+
| cnt | mind1 | maxd1 | cnt_cnt |
+-----+-------+-------+---------+
|   2 | N     | N     |    3457 |
|   2 | Y     | Y     |    2309 |
|   2 | D     | D     |     733 |
|   2 | D     | Y     |     346 |
|   2 | D     | N     |     192 |
|   2 | N     | Y     |      61 |
|   3 | Y     | Y     |      61 |
+-----+-------+-------+---------+


select distinct a.pracid, a.patid, a.eventdate, a.data1, a.data2, b.eventdate, b.data1, b.data2, c.eventdate, c.data1, c.data2
from 
ahd a
left join 
ahd b
on a.pracid = b.pracid and a.patid = b.patid and a.eventdate < b.eventdate and b.ahdcode = 1003040000
left join 
ahd c
on a.pracid = c.pracid and a.patid = c.patid and b.eventdate < c.eventdate and c.ahdcode = 1003040000
join 
(
select pracid, patid, min(eventdate) as eventdate, count(distinct eventdate) cnt from 
ahd a
where a.ahdcode = 1003040000 
group by pracid, patid
) smokes
on smokes.pracid = a.pracid and smokes.patid = a.patid and smokes.eventdate = a.eventdate
where 
a.ahdcode = 1003040000 
and cnt = 3
limit 130;


select data1, data2, count(distinct patid) cnt, count(*) cnt_events from 
ahd a
where a.ahdcode = 1003040000 
and data1 != 'N'
group by data1, data2
order by cnt desc
limit 50;


select cnt_stop_dates, count(*) from 
(
	select pracid, patid, count(distinct substring(data6,1,4)) cnt_stop_dates from 
	ahd a
	where a.ahdcode = 1003040000 
	and data6 != ''
	group by pracid, patid
)aaa
group by cnt_stop_dates
order by cnt_stop_dates 
limit 50;
+----------------+----------+
| cnt_stop_dates | count(*) |
+----------------+----------+
|              1 |     1274 |
|              2 |      202 |
|              3 |       21 |
|              4 |        3 |
+----------------+----------+

select pracid, patid, count(distinct substring(data6,1,4)) cnt_stop_dates, min(substring(data6,1,4)), max(substring(data6,1,4)) from 
ahd a
where a.ahdcode = 1003040000 
and data6 != ''
group by pracid, patid
having cnt_stop_dates = 2
limit 30;

select avg(quit_age), std(quit_age), count(*) cnt from (
select distinct a.pracid, a.patid, cast(substring(data6,1,4) as unsigned) - cast(substring(yob,1,4) as unsigned) as quit_age
from 
ahd a
join
patient p 
on a.pracid = p.pracid and a.patid = p.patid
where a.ahdcode = 1003040000 
and data6 != ''
)aaa
+---------------+-------------------+------+
| avg(quit_age) | std(quit_age)     | cnt  |
+---------------+-------------------+------+
|       42.5738 | 15.48496419125167 | 1403 |
+---------------+-------------------+------+


/* Alcohol */

select data1, data2, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
where ahdcode = 1003050000 
group by data1, data2
having cnt_dis > 50
order by cnt_dis desc 
limit 50;
+-------+-------+-------+---------+
| data1 | data2 | cnt   | cnt_dis |
+-------+-------+-------+---------+
| Y     | 0     | 30703 |   15564 |
| N     | 0     | 12490 |    7384 |
| Y     |       |  6948 |    4762 |
| N     |       |  4035 |    2789 |
| Y     | 3     |  2068 |    1868 |
| Y     | 5     |  1366 |    1261 |
| Y     | 2     |  1387 |    1124 |
| Y     | 1     |  1346 |    1012 |
|       | 0     |  2537 |    1001 |
| Y     | 4     |  1089 |     897 |
| Y     | 10    |  1004 |     845 |
| Y     | 6     |   854 |     713 |
| Y     | 9     |   704 |     645 |
| D     |       |   757 |     609 |
| Y     | 8     |   689 |     589 |
| Y     | 20    |   675 |     569 |
| Y     | 12    |   474 |     429 |
| D     | 0     |   527 |     416 |
| Y     | 14    |   439 |     384 |
| Y     | 30    |   336 |     276 |
| Y     | 16    |   253 |     230 |
| Y     | 18    |   194 |     172 |
| Y     | 40    |   186 |     161 |
| Y     | 15    |   169 |     158 |
| Y     | 24    |   177 |     152 |
| Y     | 7     |   149 |     141 |
| Y     | 28    |   142 |     131 |
| Y     | 50    |    87 |      79 |
| Y     | 25    |    85 |      78 |
| Y     | 56    |    81 |      72 |
| Y     | 60    |    70 |      67 |
| Y     | 70    |    77 |      67 |
| Y     | 21    |    66 |      63 |
| Y     | 100   |    67 |      59 |
+-------+-------+-------+---------+

select data1, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
where ahdcode = 1009300000
group by data1
having cnt_dis > 50
order by cnt_dis desc 
limit 50;

/* Immunizations */

select * from 
ahd a
where ahdcode = 1002090000
limit 10;

/* Rare tests */

select codes.description, a.data4, a.data5, count(*) cnt, count(distinct pracid, patid) cnt_dis from 
ahd a
join
ahdcodes codes
on a.ahdcode = codes.ahdcode
where a.ahdcode in (1001400081, 1001400106, 1001400075,1001400112, 1001400086, 1001400085,
1001400278,
1001400172,
1001400241,
1001400080,
1001400152,
1001400256,
1001400164,
1001400169,
1001400076,
1001400134
)
group by codes.description, a.data4, a.data5
having cnt_dis > 50
limit 100;
+--------------------------+--------+-----------+-------+---------+
| description              | data4  | data5     | cnt   | cnt_dis |
+--------------------------+--------+-----------+-------+---------+
| CAT scan                 |        |           |  2012 |    1520 |
| CAT scan                 | N/A001 |           |    59 |      59 |
| Clotting tests           |        |           |  3348 |     800 |
| Clotting tests           |        | 0.010000  |   138 |     126 |
| Clotting tests           |        | 23.400000 |   194 |     173 |
| Clotting tests           |        | 26.000000 |    58 |      54 |
| Clotting tests           | TST006 |           |   316 |     210 |
| Colonoscopy              |        |           |  1328 |     954 |
| Colonoscopy              | N/A001 |           |    60 |      57 |
| Echocardiogram           |        |           |  1470 |    1058 |
| Echocardiogram           | N/A001 |           |    66 |      64 |
| Echocardiogram           | N/A002 |           |    52 |      51 |
| Faecal Occult Blood      |        |           |  3689 |     972 |
| Faecal Occult Blood      | P/N001 |           |   342 |     342 |
| Full blood count         |        |           | 10698 |    4633 |
| Full blood count         | TST006 |           | 15298 |    3692 |
| General ultra sound scan |        |           |  1765 |    1434 |
| Iron studies             |        |           |  1727 |    1134 |
| Iron studies             | TST006 |           |  1806 |     941 |
| Liver Function tests     |        |           | 10356 |    3617 |
| Liver Function tests     | TST006 |           |  3933 |    1186 |
| Mammogram                |        |           |  3446 |    1824 |
| Mammogram                | N/A001 |           |   330 |     320 |
| MRI scan                 |        |           |  1233 |    1016 |
| MRI scan                 | N/A002 |           |    91 |      82 |
| Other autoantibodies     |        |           |  2937 |    1165 |
| Other autoantibodies     |        | 0.000000  |  1028 |     656 |
| Other autoantibodies     | TST006 |           |   105 |      77 |
| Rubella Test             |        |           |   957 |     883 |
| Rubella Test             |        | 10.000000 |    76 |      73 |
| Thyroid function         |        |           | 12560 |    4908 |
| Thyroid function         | TST006 |           |  2150 |     625 |
| Urea and Electrolytes    |        |           |  9645 |    3578 |
| Urea and Electrolytes    | TST006 |           |  4523 |    1176 |
| Urinalysis - Protein     |        |           |  4003 |    1280 |
+--------------------------+--------+-----------+-------+---------+

select medcode, max(description) as description, max(freq) as f 
from readcodefreq 
where description like '%RENAL%'
group by medcode
order by f desc
limit 30;


drop PROCEDURE expand;
drop PROCEDURE expand_one_level;
DELIMITER //
CREATE PROCEDURE expand_one_level
(IN wildcard CHAR(20), IN lim int)
BEGIN
	select gm.repr_medcode, gm.source, gm.total_freq, r.my_freq, r.description from 
		( select substring(medcode, 1, length(wildcard)) as g, source, min(medcode) as repr_medcode, sum(freq) as total_freq
		from readcodefreq where medcode like CONVERT(wildcard USING 'latin1') COLLATE 'latin1_general_cs'
		group by g,source ) gm
	join
		(select substring(medcode,1,5) as m, source, sum(freq) as my_freq, max(description) as description 
		from readcodefreq 
		group by m, source) r
	on substring(gm.repr_medcode,1,5) = r.m and gm.source = r.source
	where total_freq > lim 
	order by gm.repr_medcode
	limit 50;
END //

CREATE PROCEDURE expand
(IN wildcard CHAR(20), IN lim int)
BEGIN
	select * from readcodefreq
	where medcode like CONVERT(wildcard USING 'latin1') COLLATE 'latin1_general_cs'
	and freq > lim
	order by freq desc
	limit 50;
END //
DELIMITER ;

select locate, count(distinct pracid, patid, eventdate) cnt_dis 
from medical
group by locate
order by cnt_dis desc
limit 30;
