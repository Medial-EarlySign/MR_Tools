call expand_one_level('5%', 1000);
+--------------+----------------------------------+------------+---------+--------------------------------+
| repr_medcode | source                           | total_freq | my_freq | description                    |
+--------------+----------------------------------+------------+---------+--------------------------------+
| 5....00      | MedicalReadcodeFrequencyEver1601 |     207663 |  207663 | X-rays                         |
| 5....00      | AHDReadcodeFrequencyEver1601     |     618397 |  618397 | X-rays                         |
| 51...00      | MedicalReadcodeFrequencyEver1601 |      83222 |      17 | Radiology/physics - general    |
| 51...00      | AHDReadcodeFrequencyEver1601     |     114826 |    3441 | Radiology/physics - general    |
| 52...00      | MedicalReadcodeFrequencyEver1601 |     407107 |   40305 | Plain X-rays                   |
| 52...00      | AHDReadcodeFrequencyEver1601     |    4593463 |  113732 | Plain X-rays                   |
| 53...00      | AHDReadcodeFrequencyEver1601     |    5598498 |    2104 | Soft tissue imaging - plain    |
| 53...00      | MedicalReadcodeFrequencyEver1601 |     631430 |    1860 | Soft tissue imaging - plain    |
| 54...00      | AHDReadcodeFrequencyEver1601     |     452448 |     676 | Contrast radiography excl.CVS  |
| 54...00      | MedicalReadcodeFrequencyEver1601 |     188008 |      15 | Contrast radiography excl.CVS  |
| 55...00      | AHDReadcodeFrequencyEver1601     |     162113 |  100733 | Cardiovascular sys.angiography |
| 55...00      | MedicalReadcodeFrequencyEver1601 |      68402 |   44591 | Cardiovascular sys.angiography |
| 56...00      | MedicalReadcodeFrequencyEver1601 |     241846 |      74 | Other X-ray diagn. procedures  |
| 56...00      | AHDReadcodeFrequencyEver1601     |    1599922 |    4089 | Other X-ray diagn. procedures  |
| 57...00      | MedicalReadcodeFrequencyEver1601 |      26501 |    3597 | Vitamin B12 isotope studies    |
| 57...00      | AHDReadcodeFrequencyEver1601     |      85539 |   21776 | Vitamin B12 isotope studies    |
| 58...00      | MedicalReadcodeFrequencyEver1601 |     894291 |       6 | Physics: other diagn. methods  |
| 58...00      | AHDReadcodeFrequencyEver1601     |    5257053 |     512 | Physics: other diagn. methods  |
| 59...00      | AHDReadcodeFrequencyEver1601     |      18607 |   17616 | X-ray therapy -external        |
| 59...00      | MedicalReadcodeFrequencyEver1601 |       5615 |    4600 | X-ray therapy -external        |
| 5A...00      | AHDReadcodeFrequencyEver1601     |       5475 |     225 | Radiotherapy - internal        |
| 5A...00      | MedicalReadcodeFrequencyEver1601 |       6002 |     115 | Radiotherapy - internal        |
| 5B...00      | AHDReadcodeFrequencyEver1601     |      20313 |      25 | Physics - other therapy        |
| 5B1..00      | MedicalReadcodeFrequencyEver1601 |      11485 |      14 | Visible light therapy          |
| 5C...00      | MedicalReadcodeFrequencyEver1601 |      12672 |      88 | Imaging interpretation         |
| 5C...00      | AHDReadcodeFrequencyEver1601     |      78920 |   25873 | Imaging interpretation         |
| 5Z...00      | AHDReadcodeFrequencyEver1601     |       1552 |    1552 | Radiology/physics NOS          |
+--------------+----------------------------------+------------+---------+--------------------------------+

DEF	40000	Imaging
SET	Imaging	5....00
SET	Imaging	G_51...
SET	Imaging	G_52...
SET	Imaging	G_53...
SET	Imaging	G_54...
SET	Imaging	G_55...
SET	Imaging	G_56...


/* *************************************************************************************** */
call expand_one_level('9N%', 1000000);
+--------------+------------+---------+-------------------------------+
| repr_medcode | total_freq | my_freq | description                   |
+--------------+------------+---------+-------------------------------+
| 9N0..00      |    7053975 |   52389 | Other site of encounter       |
| 9N1..00      |   66120944 |    4844 | Site of encounter             |
| 9N2..00      |    9466569 |   87069 | Seen by professional          |
| 9N3..00      |   75598023 | 2102839 | Indirect encounter            |
| 9N4..00      |   16088786 | 3813365 | Failed encounter              |
| 9N5..00      |    2214232 |  201794 | Reason for encounter-patient  |
| 9N7..00      |    3087414 | 1256434 | Provider initiated encounter  |
| 9Na..00      |    6492630 | 6331760 | Consultation                  |
| 9NC..00      |    3719563 |  832890 | Letter sent to outside agency |
| 9ND..00      |   13690287 | 2791011 | Incoming mail processing      |
| 9Nd..00      |    3031530 |   83829 | Obtaining consent             |
| 9NE..00      |    1888205 |  252666 | Outgoing mail processing      |
| 9NF..00      |    1802033 |  197066 | Home visit admin              |
| 9NL..00      |    1552161 | 1541695 | Letter from outside agency    |
| 9NN..00      |    2559770 |    4479 | Under care of person          |
| 9NZ..00      |    3001411 | 3001411 | Patient encounter data NOS    |
+--------------+------------+---------+-------------------------------+

DEF	40001	Gp_Encounter
SET	Gp_Encounter	G_9N0..
SET	Gp_Encounter	G_9N1..
SET	Gp_Encounter	G_9N2..

/* *************************************************************************************** */

select * from readcodefreq
where description like '%renal%'
and freq > 100
order by freq desc
limit 50;

call expand_one_level('K0%', 1000);
+--------------+------------+---------+-------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                     |
+--------------+------------+---------+-------------------------------------------------+
| K0...00      |       1110 |    1109 | Nephritis, nephrosis and nephrotic syndrome     |
| K00..00      |       7604 |    4272 | Acute glomerulonephritis                        |
| K01..00      |      15346 |   12763 | Nephrotic syndrome                              |
| K02..00      |       3693 |    1800 | Chronic glomerulonephritis                      |
| K03..00      |       8056 |     495 | Nephritis and nephropathy unspecified           |
| K04..00      |      45107 |   22956 | Acute renal failure                             |
| K05..00      |      75047 |   55191 | Chronic renal failure                           |
| K06..00      |      56278 |   30134 | Renal failure unspecified                       |
| K07..00      |       1899 |      51 | Renal sclerosis unspecified                     |
| K08..00      |       8927 |    4637 | Impaired renal function disorder                |
| K09..00      |       1325 |     867 | Small kidney of unknown cause                   |
| K0A..00      |       4823 |     244 | Glomerular disease                              |
| K0z..00      |       2494 |    2491 | Nephritis, nephrosis and nephrotic syndrome NOS |
+--------------+------------+---------+-------------------------------------------------+

call expand('K04%', 1000);
+---------+---------------------+-------+----------------------------------+
| medcode | description         | freq  | source                           |
+---------+---------------------+-------+----------------------------------+
| K04..00 | Acute renal failure | 22956 | MedicalReadcodeFrequencyEver1601 |
| K04..12 | Acute kidney injury | 18873 | MedicalReadcodeFrequencyEver1601 |
| K04..00 | Acute renal failure |  1038 | AHDReadcodeFrequencyEver1601     |
+---------+---------------------+-------+----------------------------------+
call expand('K05%', 1000);
+---------+--------------------------------+-------+----------------------------------+
| medcode | description                    | freq  | source                           |
+---------+--------------------------------+-------+----------------------------------+
| K05..00 | Chronic renal failure          | 55191 | MedicalReadcodeFrequencyEver1601 |
| K053.00 | Chronic kidney disease stage 3 | 12825 | MedicalReadcodeFrequencyEver1601 |
| K050.00 | End stage renal failure        |  3225 | MedicalReadcodeFrequencyEver1601 |
| K05..00 | Chronic renal failure          |  1359 | AHDReadcodeFrequencyEver1601     |
| K054.00 | Chronic kidney disease stage 4 |  1151 | MedicalReadcodeFrequencyEver1601 |
+---------+--------------------------------+-------+----------------------------------+
call expand('K06%', 1000);
+---------+---------------------------+-------+----------------------------------+
| medcode | description               | freq  | source                           |
+---------+---------------------------+-------+----------------------------------+
| K06..00 | Renal failure unspecified | 30134 | MedicalReadcodeFrequencyEver1601 |
| K060.00 | Renal impairment          | 15931 | MedicalReadcodeFrequencyEver1601 |
| K060.11 | Impaired renal function   |  7567 | MedicalReadcodeFrequencyEver1601 |
| K06..11 | Uraemia NOS               |  1774 | MedicalReadcodeFrequencyEver1601 |
+---------+---------------------------+-------+----------------------------------+

DEF	40002	Acute_Renal_Failure
DEF	40003	Chronic_Renal_Failure
DEF	40004	Other_Renal_Condition
SET	Acute_Renal_Failure	G_K04..
SET	Chronic_Renal_Failure	G_K05..
SET	Other_Renal_Condition	G_K00..
SET	Other_Renal_Condition	G_K01..
SET	Other_Renal_Condition	G_K02..
SET	Other_Renal_Condition	G_K03..
SET	Other_Renal_Condition	G_K06..
SET	Other_Renal_Condition	G_K07..
SET	Other_Renal_Condition	G_K08..
SET	Other_Renal_Condition	G_K09..
SET	Other_Renal_Condition	G_K0A..
SET	Other_Renal_Condition	G_K0z..

/* *************************************************************************************** */

select * from readcodefreq
where description like '%diabet%'
and freq > 100
order by freq desc
limit 50;

call expand_one_level('9OL%', 1000);
+--------------+------------+---------+-------------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                                 |
+--------------+------------+---------+-------------------------------------------------------------+
| 9OL..00      |    1856953 | 1836126 | Diabetes monitoring admin.                                  |
| 9OL1.00      |     134143 |  132164 | Attends diabetes monitoring                                 |
| 9OL2.00      |       1539 |    1535 | Refuses diabetes monitoring                                 |
| 9OL3.00      |      13707 |   13705 | Diabetes monitoring default                                 |
| 9OL4.00      |     822979 |  822680 | Diabetes monitoring 1st letter                              |
| 9OL5.00      |     194418 |  194352 | Diabetes monitoring 2nd letter                              |
| 9OL6.00      |      91457 |   91440 | Diabetes monitoring 3rd letter                              |
| 9OL7.00      |      23586 |   23533 | Diabetes monitor.verbal invite                              |
| 9OL8.00      |      34116 |   34035 | Diabetes monitor.phone invite                               |
| 9OLA.00      |      88766 |   69369 | Diabetes monitor. check done                                |
| 9OLB.00      |       1703 |    1703 | Attended diabetes structured education programme            |
| 9OLD.00      |      15203 |   15162 | Diabetic patient unsuitable for digital retinal photography |
| 9OLE.00      |       1807 |    1807 | Attended DESMOND structured programme                       |
| 9OLK.00      |       1484 |    1484 | DESMOND diabetes structured education programme completed   |
| 9OLL.00      |       1233 |    1233 | XPERT diabetes structured education programme completed     |
| 9OLM.00      |      24049 |   24047 | Diabetes structured education programme declined            |
| 9OLN.00      |       1163 |    1163 | Diabetes monitor invitation by SMS (short message service)  |
| 9OLZ.00      |      23164 |   23092 | Diabetes monitoring admin.NOS                               |
+--------------+------------+---------+-------------------------------------------------------------+

call expand_one_level('42W%', 1000);
+--------------+------------+---------+--------------------------------+
| repr_medcode | total_freq | my_freq | description                    |
+--------------+------------+---------+--------------------------------+
| 42W..00      |    1788991 | 1473610 | Hb. A1C - diabetic control     |
| 42W1.00      |      33567 |   31250 | Hb. A1C < 7% - good control    |
| 42W2.00      |      38960 |   37374 | Hb. A1C 7-10% - borderline     |
| 42W3.00      |      19438 |   17967 | Hb. A1C > 10% - bad control    |
| 42W4.00      |    2609705 | 2604614 | HbA1c level (DCCT aligned)     |
| 42W5.00      |    3673073 | 3671845 | HbA1c levl - IFCC standardised |
| 42WZ.00      |      18342 |   18263 | Hb. A1C - diabetic control NOS |
+--------------+------------+---------+--------------------------------+

call expand_one_level('66A%', 100000);
+--------------+------------+---------+------------------------------------------+
| repr_medcode | total_freq | my_freq | description                              |
+--------------+------------+---------+------------------------------------------+
| 66A..00      |    1831984 | 1067900 | Diabetic monitoring                      |
| 66A2.00      |     407615 |  371630 | Follow-up diabetic assessment            |
| 66A3.00      |     104693 |   67667 | Diabetic on diet only                    |
| 66A4.00      |     223080 |  139968 | Diabetic on oral treatment               |
| 66Ac.00      |     154901 |  140392 | Diabetic peripheral neuropathy screening |
| 66AE.00      |     431955 |  431762 | Feet examination                         |
| 66AJ.00      |     127925 |   98561 | Diabetic - poor control                  |
| 66AP.00      |     351185 |  250451 | Diabetes: practice programme             |
| 66Aq.00      |     166330 |  161193 | Diabetic foot screen                     |
| 66AR.00      |     136745 |  111780 | Diabetes management plan given           |
| 66AS.00      |    1621463 | 1407732 | Diabetic annual review                   |
| 66At.00      |     383009 |  200538 | Diabetic dietary review                  |
| 66AZ.00      |     139549 |  127762 | Diabetic monitoring NOS                  |
+--------------+------------+---------+------------------------------------------+

call expand_one_level('9N1Q%', 1000);
+--------------+------------+---------+-------------------------+
| repr_medcode | total_freq | my_freq | description             |
+--------------+------------+---------+-------------------------+
| 9N1Q.00      |    1123087 | 1122955 | Seen in diabetic clinic |
+--------------+------------+---------+-------------------------+

call expand_one_level('68A7%', 1000);
+--------------+------------+---------+--------------------------------+
| repr_medcode | total_freq | my_freq | description                    |
+--------------+------------+---------+--------------------------------+
| 68A7.00      |     957055 |  832047 | Diabetic retinopathy screening |
+--------------+------------+---------+--------------------------------+

call expand_one_level('C10%', 1000);
+--------------+------------+---------+--------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                            |
+--------------+------------+---------+--------------------------------------------------------+
| C10..00      |     718274 |  716232 | Diabetes mellitus                                      |
| C100.00      |     145841 |    3218 | Diabetes mellitus with no mention of complication      |
| C101.00      |      11835 |   11367 | Diabetes mellitus with ketoacidosis                    |
| C104.00      |       4709 |    1219 | Diabetes mellitus with renal manifestation             |
| C105.00      |       2397 |    2018 | Diabetes mellitus with ophthalmic manifestation        |
| C106.00      |      21573 |   12079 | Diabetes mellitus with neurological manifestation      |
| C107.00      |       4333 |    3603 | Diabetes mellitus with peripheral circulatory disorder |
| C108.00      |      42272 |   24599 | Insulin dependent diabetes mellitus                    |
| C109.00      |     164578 |   97696 | Non-insulin dependent diabetes mellitus                |
| C10B.00      |       1344 |    1215 | Diabetes mellitus induced by steroids                  |
| C10E.00      |      96753 |   86464 | Type 1 diabetes mellitus                               |
| C10F.00      |     872299 |  831562 | Type 2 diabetes mellitus                               |
+--------------+------------+---------+--------------------------------------------------------+

call expand_one_level('2G5%', 10000);
mysql> call expand_one_level('2G5%', 10000);
+--------------+------------+---------+--------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                |
+--------------+------------+---------+--------------------------------------------+
| 2G5..00      |     606805 |  606558 | O/E - foot                                 |
| 2G54.00      |      11042 |   11042 | O/E - Right foot ulcer                     |
| 2G58.00      |      12659 |   12659 | O/E - Right foot deformity                 |
| 2G59.00      |      12550 |   12550 | O/E - Left foot deformity                  |
| 2G5E.00      |     775978 |  773892 | O/E - Right diabetic foot at low risk      |
| 2G5F.00      |     175052 |  174340 | O/E - Right diabetic foot at moderate risk |
| 2G5G.00      |      48762 |   48400 | O/E - Right diabetic foot at high risk     |
| 2G5I.00      |     769908 |  767823 | O/E - Left diabetic foot at low risk       |
| 2G5J.00      |     173232 |  172527 | O/E - Left diabetic foot at moderate risk  |
| 2G5K.00      |      48414 |   48056 | O/E - Left diabetic foot at high risk      |
+--------------+------------+---------+--------------------------------------------+

call expand_one_level('9NND%', 1000);
+--------------+------------+---------+--------------------------------------+
| repr_medcode | total_freq | my_freq | description                          |
+--------------+------------+---------+--------------------------------------+
| 9NND.00      |     340937 |  333574 | Under care of diabetic foot screener |
+--------------+------------+---------+--------------------------------------+

call expand_one_level('8B3l%', 1000);
+--------------+------------+---------+----------------------------+
| repr_medcode | total_freq | my_freq | description                |
+--------------+------------+---------+----------------------------+
| 8B3l.00      |     248289 |  220952 | Diabetes medication review |
+--------------+------------+---------+----------------------------+

call expand_one_level('42c%', 1000);
+--------------+------------+---------+-----------------------------------+
| repr_medcode | total_freq | my_freq | description                       |
+--------------+------------+---------+-----------------------------------+
| 42c..00      |     162958 |  156924 | HbA1 - diabetic control           |
| 42c0.00      |       3959 |    3357 | HbA1 < 7% - good control          |
| 42c1.00      |       7620 |    5000 | HbA1 7 - 10% - borderline control |
| 42c2.00      |       1821 |    1281 | HbA1 > 10% - bad control          |
| 42c3.00      |      14689 |   13914 | HbA1 level (DCCT aligned)         |
+--------------+------------+---------+-----------------------------------+

call expand_one_level('8BL2%', 1000);
+--------------+------------+---------+---------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                       |
+--------------+------------+---------+---------------------------------------------------+
| 8BL2.00      |      88699 |   88698 | Patient on maximal tolerated therapy for diabetes |
+--------------+------------+---------+---------------------------------------------------+

call expand_one_level('F420%', 1000);
+--------------+------------+---------+----------------------------------------+
| repr_medcode | total_freq | my_freq | description                            |
+--------------+------------+---------+----------------------------------------+
| F420.00      |      82437 |   81930 | Diabetic retinopathy                   |
| F420000      |      73198 |   73082 | Background diabetic retinopathy        |
| F420100      |       8347 |    8331 | Proliferative diabetic retinopathy     |
| F420200      |       4133 |    4107 | Preproliferative diabetic retinopathy  |
| F420400      |      19898 |   19822 | Diabetic maculopathy                   |
| F420600      |      11394 |   11393 | Non proliferative diabetic retinopathy |
| F420z00      |       2285 |    2285 | Diabetic retinopathy NOS               |
+--------------+------------+---------+----------------------------------------+

DEF	40005	Diabetes
SET	Diabetes	G_9OL..
SET	Diabetes	G_42W..
SET	Diabetes	G_66A..
SET	Diabetes	G_9N1Q.
SET	Diabetes	G_68A7.
SET	Diabetes	G_C10..
SET	Diabetes	G_2G5E.
SET	Diabetes	G_2G5F.
SET	Diabetes	G_2G5G.
SET	Diabetes	G_2G5I.
SET	Diabetes	G_2G5J.
SET	Diabetes	G_2G5K.
SET	Diabetes	G_9NND.
SET	Diabetes	G_8B3l.
SET	Diabetes	G_42c..
SET	Diabetes	G_8BL2.
SET	Diabetes	G_F420.


/* *************************************************************************************** */

select * from readcodefreq
where description like '%hyper%tension%'
and freq > 100
order by freq desc
limit 50;

call expand_one_level('G20%', 1000);
+--------------+------------+---------+----------------------------------+
| repr_medcode | total_freq | my_freq | description                      |
+--------------+------------+---------+----------------------------------+
| G20..00      |    2714335 | 2543355 | Essential hypertension           |
| G200.00      |       2722 |    2717 | Malignant essential hypertension |
| G201.00      |      49954 |   49949 | Benign essential hypertension    |
| G202.00      |      13119 |   13117 | Systolic hypertension            |
| G20z.00      |     216565 |  144005 | Essential hypertension NOS       |
+--------------+------------+---------+----------------------------------+

call expand('662..12%', 1000);
+---------+-------------------------+---------+----------------------------------+
| medcode | description             | freq    | source                           |
+---------+-------------------------+---------+----------------------------------+
| 662..12 | Hypertension monitoring | 2300665 | MedicalReadcodeFrequencyEver1601 |
+---------+-------------------------+---------+----------------------------------+

DEF	40100	Hypertension
SET	Hypertension	G_G20..

/* *************************************************************************************** */

select * from readcodefreq
where description like '%ischaemic%'
and freq > 100
order by freq desc
limit 50;

call expand_one_level('G3%', 1000);
+--------------+------------+---------+--------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                      |
+--------------+------------+---------+--------------------------------------------------+
| G3...00      |     646926 |  510272 | Ischaemic heart disease                          |
| G30..00      |     448283 |  201219 | Acute myocardial infarction                      |
| G31..00      |      89737 |     199 | Other acute and subacute ischaemic heart disease |
| G32..00      |      10132 |    8839 | Old myocardial infarction                        |
| G33..00      |     709326 |  673168 | Angina pectoris                                  |
| G34..00      |      62581 |     609 | Other chronic ischaemic heart disease            |
| G37..00      |       2016 |    2016 | Cardiac syndrome X                               |
| G3z..00      |      43214 |   43070 | Ischaemic heart disease NOS                      |
+--------------+------------+---------+--------------------------------------------------+

DEF	40006	Heart_Disease
SET	Heart_Disease	G_G3...

/* *************************************************************************************** */

select * from readcodefreq
where description like '%stroke%'
and freq > 1000
order by freq desc
limit 50;

call expand_one_level('G66%', 1000);
+--------------+------------+---------+----------------------------+
| repr_medcode | total_freq | my_freq | description                |
+--------------+------------+---------+----------------------------+
| G66..00      |     317386 |  317386 | Stroke unspecified         |
| G663.00      |       1057 |    1057 | Brain stem stroke syndrome |
| G664.00      |       1252 |    1252 | Cerebellar stroke syndrome |
| G667.00      |       4939 |    4939 | Left sided CVA             |
| G668.00      |       4352 |    4352 | Right sided CVA            |
+--------------+------------+---------+----------------------------+

call expand_one_level('662e%', 1000);
+--------------+------------+---------+--------------------------+
| repr_medcode | total_freq | my_freq | description              |
+--------------+------------+---------+--------------------------+
| 662e.00      |      98637 |   98637 | Stroke/CVA annual review |
+--------------+------------+---------+--------------------------+

call expand_one_level('662M%', 1000);
+--------------+------------+---------+-------------------+
| repr_medcode | total_freq | my_freq | description       |
+--------------+------------+---------+-------------------+
| 662M.00      |      84377 |   84377 | Stroke monitoring |
+--------------+------------+---------+-------------------+

call expand_one_level('9Om%', 1000);
+--------------+------------+---------+--------------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                                  |
+--------------+------------+---------+--------------------------------------------------------------+
| 9Om..00      |       4073 |    4073 | Stroke/transient ischaemic attack monitoring administration  |
| 9Om0.00      |      95722 |   95722 | Stroke/transient ischaemic attack monitoring first letter    |
| 9Om1.00      |      25466 |   25466 | Stroke/transient ischaemic attack monitoring second letter   |
| 9Om2.00      |      11118 |   11118 | Stroke/transient ischaemic attack monitoring third letter    |
| 9Om3.00      |       1406 |    1406 | Stroke/transient ischaemic attack monitoring verbal invitati |
| 9Om4.00      |       2043 |    2043 | Stroke/transient ischaemic attack monitoring telephone invte |
+--------------+------------+---------+--------------------------------------------------------------+

call expand_one_level('8HBJ%', 1000);
+--------------+------------+---------+----------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                  |
+--------------+------------+---------+----------------------------------------------+
| 8HBJ.00      |      23609 |   23609 | Stroke / transient ischaemic attack referral |
+--------------+------------+---------+----------------------------------------------+

call expand_one_level('8HTQ%', 1000);
+--------------+------------+---------+---------------------------+
| repr_medcode | total_freq | my_freq | description               |
+--------------+------------+---------+---------------------------+
| 8HTQ.00      |      17991 |   17991 | Referral to stroke clinic |
+--------------+------------+---------+---------------------------+

call expand_one_level('9N0p%', 1000);
+--------------+------------+---------+-----------------------+
| repr_medcode | total_freq | my_freq | description           |
+--------------+------------+---------+-----------------------+
| 9N0p.00      |      16167 |   16167 | Seen in stroke clinic |
+--------------+------------+---------+-----------------------+

DEF	40007	CVA
SET	CVA	G_G66..
SET	CVA	G_662e.
SET	CVA	G_662M.
SET	CVA	G_9Om..
SET	CVA	G_8HBJ.
SET	CVA	G_8HTQ.
SET	CVA	G_9N0p.


/* *************************************************************************************** */


call expand('14B3%', 1000);
+---------+--------------------------------------------------+------+----------------------------------+
| medcode | description                                      | freq | source                           |
+---------+--------------------------------------------------+------+----------------------------------+
| 14B3.00 | H/O: chr.obstr. airway disease                   | 8269 | MedicalReadcodeFrequencyEver1601 |
| 14B3.11 | H/O: bronchitis                                  | 5642 | MedicalReadcodeFrequencyEver1601 |
| 14B3.12 | History of chronic obstructive pulmonary disease | 1220 | MedicalReadcodeFrequencyEver1601 |
+---------+--------------------------------------------------+------+----------------------------------+

call expand_one_level('3376%', 1000);
+--------------+------------+---------+--------------------------------+
| repr_medcode | total_freq | my_freq | description                    |
+--------------+------------+---------+--------------------------------+
| 3376.00      |       3229 |    3229 | Lung function signific. obstr. |
+--------------+------------+---------+--------------------------------+

call expand_one_level('663K%', 1000);
+--------------+------------+---------+--------------------------------+
| repr_medcode | total_freq | my_freq | description                    |
+--------------+------------+---------+--------------------------------+
| 663K.00      |      25157 |   25157 | Airways obstructn irreversible |
+--------------+------------+---------+--------------------------------+

call expand_one_level('66Y%', 5000);
+--------------+------------+---------+--------------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                                  |
+--------------+------------+---------+--------------------------------------------------------------+
| 66Y0.00      |      19712 |   19712 | Number of times bronchodilator used in 24 hours              |
| 66Y3.00      |       7017 |    7017 | Peak expiratory flow rate - technique good                   |
| 66Y4.00      |      88866 |   88866 | Inhaler technique - moderate                                 |
| 66Y5.00      |       5707 |    5707 | Change in asthma management plan                             |
| 66Y9.00      |      23133 |   23133 | Step up change in asthma management plan                     |
| 66YA.00      |      12060 |   12060 | Step down change in asthma management plan                   |
| 66Ya.00      |       8729 |    8729 | Reversibility trial by bronchodilator                        |
| 66YB.00      |     219593 |  209262 | Chronic obstructive pulmonary disease monitoring             |
| 66YC.00      |       5402 |    5402 | Absent from work or school due to asthma                     |
| 66Yd.00      |      13552 |   13552 | COPD accident and emergency attendance since last visit      |
| 66YE.00      |      26245 |   26245 | Asthma monitoring due                                        |
| 66Ye.00      |      11894 |   11894 | Emergency COPD admission since last appointment              |
| 66Yf.00      |     158588 |  158588 | Number of COPD exacerbations in past year                    |
| 66YI.00      |     138848 |  138848 | COPD self-management plan given                              |
| 66YJ.00      |    2498352 | 2498352 | Asthma annual review                                         |
| 66YK.00      |     747306 |  747306 | Asthma follow-up                                             |
| 66YL.00      |      80664 |   80664 | COPD follow-up                                               |
| 66YM.00      |     580668 |  580668 | Chronic obstructive pulmonary disease annual review          |
| 66YP.00      |      19963 |   19963 | Asthma night-time symptoms                                   |
| 66Yp.00      |      35507 |   35507 | Asthma review using Roy Colleg of Physicians three questions |
| 66YQ.00      |      67272 |   67272 | Asthma monitoring by nurse                                   |
| 66Yq.00      |      18550 |   18550 | Asthma causes night time symptoms 1 to 2 times per week      |
| 66YR.00      |      18596 |   18596 | Asthma monitoring by doctor                                  |
| 66Yr.00      |      16691 |   16691 | Asthma causes symptoms most nights                           |
| 66Ys.00      |       8491 |    8491 | Asthma never causes night symptoms                           |
| 66YX.00      |      41831 |   41831 | Peak expiratory flow rate monitoring                         |
| 66YY.00      |      15631 |   15631 | PEFR monitoring using diary                                  |
+--------------+------------+---------+--------------------------------------------------------------+


call expand_one_level('679V%', 5000);
+--------------+------------+---------+----------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                              |
+--------------+------------+---------+----------------------------------------------------------+
| 679V.00      |      19496 |   19496 | Health education - chronic obstructive pulmonary disease |
+--------------+------------+---------+----------------------------------------------------------+


call expand_one_level('8CE6%', 500);
+--------------+------------+---------+-----------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                         |
+--------------+------------+---------+-----------------------------------------------------+
| 8CE6.00      |       3718 |    3718 | Chronic obstructive pulmonary disease leaflet given |
+--------------+------------+---------+-----------------------------------------------------+

 call expand_one_level('8CR1%', 500);
+--------------+------------+---------+-------------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                                 |
+--------------+------------+---------+-------------------------------------------------------------+
| 8CR1.00      |       9327 |    9327 | Chronic obstructive pulmonary disease clini management plan |
+--------------+------------+---------+-------------------------------------------------------------+

call expand_one_level('8H2R%', 500);
+--------------+------------+---------+----------------------+
| repr_medcode | total_freq | my_freq | description          |
+--------------+------------+---------+----------------------+
| 8H2R.00      |      16369 |   16369 | Admit COPD emergency |
+--------------+------------+---------+----------------------+

 call expand_one_level('9Oi%', 500);
+--------------+------------+---------+--------------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                                  |
+--------------+------------+---------+--------------------------------------------------------------+
| 9Oi..00      |      16530 |   16530 | Chronic obstructive pulmonary disease monitoring admin       |
| 9Oi0.00      |     226091 |  226091 | Chronic obstructive pulmonary disease monitoring 1st letter  |
| 9Oi1.00      |      71596 |   71596 | Chronic obstructive pulmonary disease monitoring 2nd letter  |
| 9Oi2.00      |      34255 |   34255 | Chronic obstructive pulmonary disease monitoring 3rd letter  |
| 9Oi3.00      |       5328 |    5328 | Chronic obstructive pulmonary disease monitoring verb invite |
| 9Oi4.00      |      12182 |   12182 | Chronic obstructive pulmonary disease monitor phone invite   |
+--------------+------------+---------+--------------------------------------------------------------+

call expand_one_level('H3%', 500);
+--------------+------------+---------+-------------------------------------------------------+
| repr_medcode | total_freq | my_freq | description                                           |
+--------------+------------+---------+-------------------------------------------------------+
| H3...00      |     511795 |  511795 | Chronic obstructive pulmonary disease                 |
| H30..00      |     431467 |  342414 | Recurrent wheezy bronchitis                           |
| H31..00      |     206207 |   22096 | Chronic bronchitis                                    |
| H32..00      |      44909 |   42867 | Emphysema                                             |
| H33..00      |    4443963 | 3667696 | Bronchial asthma                                      |
| H34..00      |      80425 |   77912 | Bronchiectasis                                        |
| H35..00      |       4205 |    2190 | Hypersensitivity pneumonitis                          |
| H36..00      |      62191 |   62191 | Mild chronic obstructive pulmonary disease            |
| H37..00      |      60068 |   60068 | Moderate chronic obstructive pulmonary disease        |
| H38..00      |      25910 |   25910 | Severe chronic obstructive pulmonary disease          |
| H39..00      |       2384 |    2384 | Very severe chronic obstructive pulmonary disease     |
| H3y..00      |      62885 |    1870 | Other specified chronic obstructive pulmonary disease |
| H3z..00      |      64297 |   64297 | Chronic obstructive pulmonary disease NOS             |
+--------------+------------+---------+-------------------------------------------------------+

DEF	40008	Chronic_Lung_Disease
SET	Chronic_Lung_Disease	G_14B3.
SET	Chronic_Lung_Disease	G_3376.
SET	Chronic_Lung_Disease	G_66YB.
SET	Chronic_Lung_Disease	G_66Yd.
SET	Chronic_Lung_Disease	G_66Ye.
SET	Chronic_Lung_Disease	G_66Yf.
SET	Chronic_Lung_Disease	G_66YI.
SET	Chronic_Lung_Disease	G_66YL.
SET	Chronic_Lung_Disease	G_66YM.
SET	Chronic_Lung_Disease	G_679V.
SET	Chronic_Lung_Disease	G_8CE6.
SET	Chronic_Lung_Disease	G_8CR1.
SET	Chronic_Lung_Disease	G_8H2R.
SET	Chronic_Lung_Disease	G_9Oi..
SET	Chronic_Lung_Disease	G_H3...


/* *************************************************************************************** */

select * from readcodefreq
where description like '%asthma%'
and freq > 1000
order by freq desc
limit 50;

call expand_one_level('H33%', 1000);
call expand_one_level('H33%', 1000);
+--------------+------------+---------+-------------------------------+
| repr_medcode | total_freq | my_freq | description                   |
+--------------+------------+---------+-------------------------------+
| H33..00      |    3667696 | 3667696 | Bronchial asthma              |
| H330.00      |      75311 |   64134 | Pollen asthma                 |
| H331.00      |      17594 |   15491 | Late onset asthma             |
| H333.00      |     353700 |  353700 | Acute exacerbation of asthma  |
| H33z.00      |     327966 |   49106 | Hyperreactive airways disease |
+--------------+------------+---------+-------------------------------+

call expand_one_level('66YJ%', 1000);
+--------------+------------+---------+----------------------+
| repr_medcode | total_freq | my_freq | description          |
+--------------+------------+---------+----------------------+
| 66YJ.00      |    2498352 | 2498352 | Asthma annual review |
+--------------+------------+---------+----------------------+

call expand_one_level('663.%', 1000);
+--------------+------------+---------+--------------------------------+
| repr_medcode | total_freq | my_freq | description                    |
+--------------+------------+---------+--------------------------------+
| 663..00      |    2125298 | 2125298 | Respiratory disease monitoring |
+--------------+------------+---------+--------------------------------+

call expand_one_level('8B3j%', 1000);
+--------------+------------+---------+--------------------------+
| repr_medcode | total_freq | my_freq | description              |
+--------------+------------+---------+--------------------------+
| 8B3j.00      |    1291655 | 1291655 | Asthma medication review |
+--------------+------------+---------+--------------------------+

call expand_one_level('663O%', 1000);
+--------------+------------+---------+-----------------------------+
| repr_medcode | total_freq | my_freq | description                 |
+--------------+------------+---------+-----------------------------+
| 663O.00      |    1223327 | 1223327 | Asthma not disturbing sleep |
| 663O000      |     149979 |  149979 | Asthma never disturbs sleep |
+--------------+------------+---------+-----------------------------+

call expand_one_level('663Q%', 1000);
+--------------+------------+---------+--------------------------------+
| repr_medcode | total_freq | my_freq | description                    |
+--------------+------------+---------+--------------------------------+
| 663Q.00      |    1184464 | 1184464 | Asthma not limiting activities |
+--------------+------------+---------+--------------------------------+

DEF	40009	Asthma
SET	Asthma	G_66Y5.
SET	Asthma	G_66Y9.
SET	Asthma	G_66YA.
SET	Asthma	G_66YC.
SET	Asthma	G_66YE.
SET	Asthma	G_66YJ.
SET	Asthma	G_66YK.
SET	Asthma	G_66YP.
SET	Asthma	G_66Yp.
SET	Asthma	G_66YQ.
SET	Asthma	G_66Yq.
SET	Asthma	G_66YR.
SET	Asthma	G_66Yr.
SET	Asthma	G_66Ys.
SET	Asthma	G_H33..
SET	Asthma	G_66YJ.
SET	Asthma	663..00
SET	Asthma	G_8B3j.
SET	Asthma	G_663O.
SET	Asthma	G_663Q.

/* *************************************************************************************** */

select * from readcodefreq
where description like '%fat%liver%'
and freq > 1000
order by freq desc
limit 50;

call expand_one_level('J61%', 1000);
+--------------+------------+---------+-------------------------------------------+
| repr_medcode | total_freq | my_freq | description                               |
+--------------+------------+---------+-------------------------------------------+
| J61..00      |       6771 |    6771 | Cirrhosis and chronic liver disease       |
| J610.00      |       4587 |    4587 | Alcoholic fatty liver                     |
| J611.00      |       3329 |    3329 | Acute alcoholic hepatitis                 |
| J612.00      |       9721 |    9626 | Laennec's cirrhosis                       |'
| J613.00      |       9751 |    9372 | Alcoholic liver damage unspecified        |
| J614.00      |       8648 |    4817 | Chronic hepatitis                         |
| J615.00      |       8999 |    1015 | Portal cirrhosis                          |
| J616.00      |       7649 |    1928 | Biliary cirrhosis                         |
| J617.00      |       2774 |    2647 | Alcoholic hepatitis                       |
| J61y.00      |      39186 |     132 | Other non-alcoholic chronic liver disease |
| J61z.00      |       1621 |    1621 | Chronic liver disease NOS                 |
+--------------+------------+---------+-------------------------------------------+

DEF	40010	Cirrhosis
DEF	40011	Alcoholic_Fatty_liver
DEF	40012	Alcoholic_Hepatitis
DEF	40013	Alcoholic_Cirrhosis
DEF	40014	Chronic_Cirrhosis
DEF	40015	Portal_Cirrhosis
DEF	40016	Biliary_Cirrhosis
DEF	40017	Other_Chronic_Liver_Disease

SET	Cirrhosis	J61..00
SET	Cirrhosis	G_J615.

SET	Alcoholic_Fatty_liver	G_J610.
SET	Alcoholic_Fatty_liver	G_J613.
SET	Alcoholic_Fatty_liver	G_J61y.

SET	Alcoholic_Hepatitis	G_J611.
SET	Alcoholic_Hepatitis	G_J617.

SET	Alcoholic_Cirrhosis	G_J612.

SET	Chronic_Cirrhosis	G_J614.

SET	Portal_Cirrhosis	G_J615.

SET	Biliary_Cirrhosis	G_J616.

SET	Other_Chronic_Liver_Disease	G_J61z.

/* *************************************************************************************** */

select * from readcodefreq
where description like '%hepa%'
and freq > 1000
order by freq desc
limit 50;



/* *************************************************************************************** */

select * from readcodefreq
where description like '%parki%'
and freq > 1000
order by freq desc
limit 50;
+---------+------------------------------------+-------+----------------------------------+
| medcode | description                        | freq  | source                           |
+---------+------------------------------------+-------+----------------------------------+
| F12..00 | Parkinson's disease                | 91201 | MedicalReadcodeFrequencyEver1601 |
| F12z.00 | Parkinson's disease NOS            |  6829 | MedicalReadcodeFrequencyEver1601 |
| G567400 | Wolff-Parkinson-White syndrome     |  6571 | MedicalReadcodeFrequencyEver1601 |
| 129Z.11 | FH: Parkinsonism                   |  4168 | AHDReadcodeFrequencyEver1601     |
| 297A.00 | O/E - Parkinsonian tremor          |  3843 | MedicalReadcodeFrequencyEver1601 |
| F121.11 | Drug induced parkinsonism          |  2036 | MedicalReadcodeFrequencyEver1601 |
| Eu02300 | [X]Dementia in Parkinson's disease |  1652 | MedicalReadcodeFrequencyEver1601 |
| 147F.00 | History of Parkinson's disease     |  1022 | MedicalReadcodeFrequencyEver1601 |
| F12..00 | Parkinson's disease                |  1006 | AHDReadcodeFrequencyEver1601     |'
+---------+------------------------------------+-------+----------------------------------+

DEF	40018	Parkinson
SET	Parkinson	G_F12..
SET	Parkinson	G567400
SET	Parkinson	G_297A.
SET	Parkinson	G_F121.
SET	Parkinson	Eu02300
SET	Parkinson	G_147F.

/* *************************************************************************************** */

select * from readcodefreq
where description like '%alzheimer%'
and freq > 1000
order by freq desc
limit 50;
+---------+--------------------------------------------------------+-------+----------------------------------+
| medcode | description                                            | freq  | source                           |
+---------+--------------------------------------------------------+-------+----------------------------------+
| F110.00 | Alzheimer's disease                                    | 49623 | MedicalReadcodeFrequencyEver1601 |
| Eu00.00 | [X]Dementia in Alzheimer's disease                     | 19326 | MedicalReadcodeFrequencyEver1601 |
| Eu00z11 | [X]Alzheimer's dementia unspec                         |  6310 | MedicalReadcodeFrequencyEver1601 |
| 129B.00 | FH: Alzheimer's disease                                |  4666 | AHDReadcodeFrequencyEver1601     |
| Eu00200 | [X]Dementia in Alzheimer's dis, atypical or mixed type |  1694 | MedicalReadcodeFrequencyEver1601 |
| F110.00 | Alzheimer's disease                                    |  1236 | AHDReadcodeFrequencyEver1601     |
+---------+--------------------------------------------------------+-------+----------------------------------+

DEF	40019	Alzheimer
SET	Alzheimer	G_F110.
SET	Alzheimer	G_Eu00.
SET	Alzheimer	Eu00200

/* *************************************************************************************** */

select * from readcodefreq
where description like '%irish%'
and freq > 1000
order by freq desc
limit 50;