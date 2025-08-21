#!/usr/bin/python
import fnmatch
import os
import random
import sys
import re

rec_names = ["patid","prscdate","drugcode","therflag","doscode","prscqty","prscdays","private","staffid","prsctype","opno","bnf","seqnoiss","maxnoiss","packsize","dosgval","locate","drugsource","inprac","therid","consultid","sysdate","modified"]
rec_lens = [4,8,8,1,7,8,3,1,4,1,8,8,4,4,7,7,2,1,1,4,4,8,1]
rec_from_to = []

def write_tabbed_list(fname,in_list):
    f = open(fname,"w")
    for l in sorted(in_list, key= lambda x:x[1] if x[0].upper() != 'SECTION' else -1):
        s = "\t".join(l)+"\n"
        f.write(s)
    f.close()

def write_tabbed_list_num(fname,in_list):
    f = open(fname,"w")
    for l in sorted(in_list, key= lambda x:int(x[1]) if x[0].upper() != 'SECTION' else -1):
        s = "\t".join(l)+"\n"
        f.write(s)
    f.close()

def append_unique(mylist, in_mylist, item):
    s = " ".join(item)
    if s not in in_mylist:
        mylist.append(item)
        in_mylist[s] = 1
        return True
    return False

def sanity1():
    print('%d %d'%(len(rec_names),len(rec_lens)))
    for i in range(len(rec_names)):
        print('%d %d'%(rec_names[i],rec_lens[i]))

def prep_rec_from_to():
    from_pos = 0
    to_pos = 0
    for i in range(len(rec_lens)):
        from_pos = to_pos
        to_pos = to_pos + rec_lens[i]
        rec_from_to.append([from_pos, to_pos])

def parse_line(curr_line, from_to, parsed):
    for ft in from_to:
        #print ft[0], ft[1], curr_line[ft[0]:ft[1]]
        parsed.append(curr_line[ft[0]:ft[1]])

def print_parsed(prefix,parsed):
    x = prefix+": "
    for s in parsed:
        x = x + s +" | "
    print(x)

def parse_therapy_file(fname,all):
    fin = open(fname,"r")
    NR = len(rec_lens)
    for curr_l in fin:
        #print curr_l
        parsed = []
        parse_line(curr_l,rec_from_to,parsed)
        print_parsed("",parsed)
        all.append(parsed)

def get_days(date):
    dt = int(date)
    y = round(dt/10000)
    m = round((dt % 10000)/100)
    d = dt%100
    days = y*365 + (m-1)*30.5 + d
    return round(days)


def day_dist(ther,pres_quant):
    last_the = {}
    for th in ther:
        k = th[0]+th[2];
        days = get_days(th[1])
        diff = ""
        if k in last_the:
            if th[1] == last_the[k][3]:
                th[5] = str(float(th[5])+float(last_the[k][2]))
            else:
                d1 = float(last_the[k][2])
                d2 = days-last_the[k][0]
                r = ""
                if d1>0 and d2>0:
                    r = str(round(d1/d2)) #units/day
                    kk = last_the[k][1]+" "+r
                    if kk in pres_quant:
                        pres_quant[kk] = pres_quant[kk]+1
                    else:
                        pres_quant[kk] = 1
                diff = " "+last_the[k][1]+" "+last_the[k][2]+" "+str(d2)+" "+r
        last_the[k] = [days, th[4], th[5], th[1]]
        #print th[0],th[1],th[2],th[4],th[5],"::",diff


def print_pq(pq):
    for k in pq:
        print ("%8d %s"%(pq[k],str(k)))


def prep_pq():
    pq = {}
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, 'therapy.*'):
            if (random.random() < 0.5):
                print("working on file",file)
                sys.stdout.flush()
                a = []
                parse_therapy_file(path+file,a)
                day_dist(a,pq)
    print_pq(pq)

def read_dosage_rates(fname,drates):
    fin = open(fname,"r")
    for L in fin:
        Li = L.replace('\n','').replace('\r','').split(' ')
        drates[Li[1]] = float(Li[2])
    fin.close()

#
# get an input file and output file
# parsing lines in input, and calculating a line of <patient> DRUG <date> <drugcode> <days>
# <days> is calculated by dividing quantity with dosage rate whenever possible (rate of 1 is default if not given)
# in case quantity is 0
def prep_drug_sig(fname,fout_name,drates,id2nr):
    fin = open(fname,"r")
    fout = open(fout_name,"a")
    fpref = re.sub(r"^.*\.","",fname)
    prev = {}
    piddate = []
    dcode_days={}
    for curr_l in fin:
        #print curr_l
        parsed = []
        parse_line(curr_l,rec_from_to,parsed)
        if parsed[3] != "Y":
            continue

        #print_parsed("",parsed)
        quantity = float(parsed[5]) 
        dos_code = parsed[4] #how much to take (caliberated to daily). you can multiply with drug strength later (it's fixed per drugcode)
        drug_code = parsed[2]

        rate = drates.get(dos_code,0)
        if quantity<=0:
            quantity = prev.get(drug_code,[7,1])[0]
        if rate<=0:
            rate = prev.get(drug_code,[7,1])[1]

        pid = fpref+parsed[0]
        date = parsed[1]

        if piddate==[]:
            piddate = [pid, date]
            dcode_days = {}

        days = quantity/rate

        if piddate == [pid, date]:
            v = dcode_days.get(drug_code, 0)
            dcode_days[drug_code] = v + days
        else:
            for dc in sorted(dcode_days):
                d = round(dcode_days[dc])
                if d <= 1:
                    d = 7.0
                if d>360:
                    d = 360
                if piddate[0] in id2nr:
                    #print piddate[0],id2nr[piddate[0]],"Drug",piddate[1],dc,d
                    s = str(id2nr[piddate[0]])+"\tDrug\t"+piddate[1]+"\tdc"+str(dc)+"\tDays:"+str(int(d))+"\t"+str(rate)+"\n"
                    fout.write(s)

            dcode_days.clear()
            dcode_days[drug_code] = days

        piddate = [pid, date]

        #print_parsed("",parsed)
        #print pid, "Drug", date, drug_code, days

    for dc in sorted(dcode_days):
        d = round(dcode_days[dc])
        if d <= 1:
            d = 7.0
        if d>360:
            d = 360
        if piddate[0] in id2nr:
            #print piddate[0],id2nr[piddate[0]],"Drug",piddate[1],dc,d
            s = str(id2nr[piddate[0]])+"\tDrug\t"+piddate[1]+"\tdc"+str(dc)+"\tDays:"+str(int(d))+"\t"+str(rate)+"\n"
            fout.write(s)


    fin.close()
    fout.close()

def read_id2nr(fname,id2nr):
    fin = open(fname,"r")
    for f in fin:
        #print f
        fi = f.replace('\n','').replace('\r','').split('\t')
        #print fi[0],fi[1]
        id2nr[fi[0]] = fi[1]
    fin.close()

def prep_drug_sig_looper(data_path, out_path, prefix, drates, id2nr):

    fout_name = out_path + prefix + "_" + "therapy"
    fout = open(fout_name,"w")
    fout.close()
    pat = "therapy."+prefix+"*"
    for file in os.listdir(data_path):
        if fnmatch.fnmatch(file, pat):
            print("Working on file ", file)

            prep_drug_sig(data_path+file,fout_name,drates, id2nr)

def add_drug_codes(fname,defs,sets, seen, seen_names, seen_drug,n = 1000, n_atc = 100000, n_bnf = 200000):
    fin = open(fname,"r")
    #seen = {}
    #seen_names = {}
    for L in fin:
        L = L.replace('\n','').replace('\r','')
        dc = L[0:8]
        bnf1 = L[8:19]
        bnf2 = L[19:30]
        bnf3 = L[30:41]
        gname_full = L[41:161]
        atc = L[-8:-1]+L[-1]
        atc = atc.replace(' ','_')

        gname = "dc: "+gname_full.strip().lower()
        

        if "dc"+dc in seen_drug: #exits - ignore "new name" gname
            id = seen_drug["dc"+dc]
            seen_names[gname] = id
            append_unique(defs,seen,["DEF",id,gname])
        elif gname in seen_names:
            id = seen_names[gname]
            seen_drug["dc"+dc] = id
            append_unique(defs,seen,["DEF",id,"dc"+dc])
        else:
            id = str(n)
            seen_names[gname] = id
            seen_drug["dc"+dc] = id
            #print ("DEF",n,gname)
            append_unique(defs,seen,["DEF",id,gname])    
            append_unique(defs,seen,["DEF",id,"dc"+dc])
            n += 1
        #print L
        #print "====>",len(L)
        #print "dc=",dc
        #print dc,bnf1,bnf2,bnf3,atc,gname
        atc = atc.replace(' ','_')
        #print ("DEF",n,"dc"+dc)
        if bnf1 != "00.00.00.00":
            #print ("SET","BNF_"+bnf1,"dc"+dc)
            if "BNF_"+bnf1 not in seen_names:
                append_unique(defs, seen, ["DEF", str(n_bnf),"BNF_"+bnf1])
                seen_names["BNF_"+bnf1] = str(n_bnf)
                n_bnf += 1
            append_unique(sets, seen, ["SET","BNF_"+bnf1,"dc"+dc])

        if bnf2 != "00.00.00.00":
            #print ("SET","BNF_"+bnf2,"dc"+dc)
            if "BNF_"+bnf2 not in seen_names:
                append_unique(defs, seen, ["DEF", str(n_bnf),"BNF_"+bnf2])
                seen_names["BNF_"+bnf2] = str(n_bnf)
                n_bnf += 1
            append_unique(sets, seen, ["SET","BNF_"+bnf2,"dc"+dc])

        if bnf3 != "00.00.00.00":
            #print ("SET","BNF_"+bnf3,"dc"+dc)
            if "BNF_"+bnf3 not in seen_names:
                append_unique(defs, seen, ["DEF", str(n_bnf),"BNF_"+bnf3])
                seen_names["BNF_"+bnf3] = str(n_bnf)
                n_bnf += 1
            append_unique(sets, seen, ["SET","BNF_"+bnf3,"dc"+dc])

        if atc != "________":
            #print ("SET","ATC_"+atc,"dc"+dc)
            if "ATC_" + atc not in seen_names:
                append_unique(defs, seen, ["DEF", str(n_atc) ,"ATC_"+atc])
                seen_names["ATC_"+atc] = str(n_atc)
                n_atc += 1
            append_unique(sets, seen, ["SET", "ATC_"+atc,"dc"+dc])

    fin.close()
    return n,n_atc,n_bnf

def add_atc_codes(fname,defs,sets, seen, seen_names, start_n):
    fin = open(fname,"r")
    n = start_n
    #seen = {}
    for L in fin:
        L = L.replace('\n','').replace('\r','')
        atc = L[0:8]
        atc = atc.replace(' ','_')
        name = "ATC_"+atc+": "+re.sub(r"  *$","",L[8:])

        if "ATC_" + atc  not in seen_names:
            #print ("DEF",n,"ATC_"+atc)
            append_unique(defs,seen,["DEF",str(n),"ATC_"+atc])
            #print ("DEF",n,name)
            seen_names["ATC_"+atc] = n
            n = n+1
        id = seen_names["ATC_"+atc]
        append_unique(defs,seen,["DEF",str(id),name])

        atc1 = atc[:6]+"__"
        if atc != atc1:
            #print ("SET","ATC_"+atc1,"ATC_"+atc)
            append_unique(sets, seen, ["SET","ATC_"+atc1,"ATC_"+atc])

        atc2 = atc1[:5]+"___"
        if atc2!=atc1:
            #print ("SET","ATC_"+atc2,"ATC_"+atc)
            append_unique(sets, seen, ["SET","ATC_"+atc2,"ATC_"+atc1])

        atc3 = atc2[:3]+"_____"
        if atc3 != atc2:
            #print ("SET","ATC_"+atc3,"ATC_"+atc)
            append_unique(sets, seen, ["SET","ATC_"+atc3,"ATC_"+atc2])

        atc4 = atc3[:1]+"_______"
        if atc4 != atc3:
            #print ("SET","ATC_"+atc4,"ATC_"+atc)
            append_unique(sets, seen, ["SET","ATC_"+atc4,"ATC_"+atc3])

    fin.close()
    return n

def add_bnf_codes(fname,defs,sets, seen, seen_names, start_n):
    fin = open(fname,"r")
    n = start_n
    #seen = {}
    #bnf_dict = set(map(lambda x: x[2],defs))
    for L in fin:
        L = L.replace('\n','').replace('\r','')
        bnf = L[0:11].strip()
        if bnf == 'None' or len(bnf) != 11:
            print('ERROR in BNF=%s. Line:\n%s'%(bnf, L))
            continue
        name = "BNF_"+bnf+": "+re.sub(r"  *$","",L[11:])
        bnf_full = "BNF_" + bnf

        #print ("DEF",n,"BNF_"+bnf)
        if bnf_full not in seen_names:
            append_unique(defs,seen,["DEF",str(n),"BNF_"+bnf])
            #print ("DEF",n,name)
            seen_names[bnf_full] = n
            n += 1
        id = seen_names[bnf_full]
        append_unique(defs,seen,["DEF",str(id),name])
        #if bnf not in bnf_dict:
        #    bnf_dict.add(bnf)
        #else:
        #    print('Duplicate %s'%bnf)

        bnf1 = bnf[0:9]+"00"
        bnf1_full = "BNF_" + bnf1
        if bnf != bnf1:
            #print ("SET","BNF_"+bnf1,"BNF_"+bnf)
            if bnf1_full not in seen_names:
                print('MISSING %s'%bnf1)
                append_unique(defs, seen, ["DEF",str(n),"BNF_"+bnf1])
                seen_names[bnf1_full] = n
                n += 1
            append_unique(sets, seen, ["SET","BNF_"+bnf1,"BNF_"+bnf])

        bnf2 = bnf1[0:6]+"00.00"
        bnf2_full = "BNF_" + bnf2
        if bnf2 != bnf1:
            #print ("SET","BNF_"+bnf2,"BNF_"+bnf)
            if bnf2_full not in seen_names:
                print('MISSING %s'%bnf2)
                append_unique(defs, seen, ["DEF",str(n),"BNF_"+bnf2])
                seen_names[bnf2_full] = n
                n += 1
            append_unique(sets, seen, ["SET","BNF_"+bnf2,"BNF_"+bnf1])
            continue

        bnf3 = bnf2[0:3]+"00.00.00"
        bnf3_full = "BNF_" + bnf3
        if bnf3 != bnf2:
            #print ("SET","BNF_"+bnf3,"BNF_"+bnf)
            if bnf3_full not in seen_names:
                print('MISSING %s'%bnf3)
                append_unique(defs, seen, ["DEF",str(n),"BNF_"+bnf3])
                seen_names[bnf3_full] = n
                n += 1
            append_unique(sets, seen, ["SET","BNF_"+bnf3,"BNF_"+bnf2])

    fin.close()
    return n



###################################################################################
#sanity1()
if __name__ == "__main__":
    prep_rec_from_to()
    path = "/server/Data/THIN1601/THINDB1601/"
    path2 = "/server/Work/Users/Avi/thin/new/"
    path3 = "/server/Work/Users/Ido/THIN_ETL/"

    # prepare the dictionaries for drugs
    if 0:
        defs = []
        sets = []
        seen = {}
        seen_names = {}
        seen_drug = {}
        for i in range(500):
            defs.append(["DEF",str(i),"Days:"+str(i)])
        n,start_atc, start_bnf=add_drug_codes(path2+"DrugCodes1601.txt",defs,sets, seen, seen_names, seen_drug)
        add_atc_codes(path2+"ATCTerms1601.txt",defs,sets, seen, seen_names, start_atc)
        add_bnf_codes(path2+"BNFCode1601.txt",defs,sets, seen, seen_names, start_bnf)

        write_tabbed_list_num(path2+"dict.drugs_defs",defs)
        write_tabbed_list(path2+"dict.drugs_sets",sets)

    # prepare the actual therapy files
    if 0:
        drates = {}
        id2nr = {}
        read_dosage_rates(path2+"dosage_rate",drates)
        read_id2nr(path3+"ID2NR",id2nr)
        #s = "abcdefghij"
        s = "fghij"
        for i in range(len(s)):
            prep_drug_sig_looper(path,path2,s[i:i+1],drates,id2nr)


    #prep_drug_sig(path+"therapy.a6641", drates)
    #a = []
    #parse_therapy_file(path+"therapy.a6641",a)
