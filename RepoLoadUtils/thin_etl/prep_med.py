#!/usr/bin/python

#
# preparing dictionary and input files to med read codes in thin
#

def write_tabbed_list(fname,in_list, mode = 'w'):
    f = open(fname, mode)
    for l in in_list:
        s = "\t".join(l)+"\n"
        f.write(s)
    f.close()

def append_unique(mylist, in_mylist, item):
    s = " ".join(item)
    if s not in in_mylist:
        mylist.append(item)
        in_mylist[s] = 1

def prep_dict_file(in_f, out_f):
    fin = open(in_f,"r")
    data = fin.read().replace('\n',' ').replace('\r','').split(' ')
    fin.close()
    codes = data[::2]
    names = data[1::2]

    a = []
    myset = {}
    ind = 100000
    indset = {}
    seen = {}

    # adding DEF parts (several names per item)
    for n in names:
        if n[:5] in indset:
            s = indset[n[:5]]
        else:
            s = str(ind)
            indset[n[:5]] = s
            ind = ind + 1
        append_unique(a,seen,["DEF",s,n[:5]])
        append_unique(a,seen,["DEF",s,n[:7]])
        append_unique(a,seen,["DEF",s,n[7:]])

    for c in codes:
        cc = c[:5].replace('.','')
        myset[cc] = c[:5]

    seen = {}
    for c in codes:
        cc = c[:5].replace('.','')
        for l in range(len(cc)-1,0,-1):
            sc = cc[:l]
            if sc in myset:
                curr = ["SET",myset[sc],c[:5]]
                append_unique(a,seen,curr)
#            print "SET",c[:5],myset[sc]
                break

    write_tabbed_list(out_f,a)
#for i in range(len(a)):
#    print "%s\t%s\t%s" % ("SET",a[i][1],a[i][0])

def prep_dict_file2(text_in, out_f):
    #fin = open(in_f,"r")
    #data = fin.read().replace('\n',' ').replace('\r','').split(' ')
    data = text_in.replace('\n',' ').replace('\r','').split(' ')
    #fin.close()
    codes = data[::2]
    names = data[1::2]

    a = []
    myset = {}
    ind = 100000
    indset = {}
    seen = {}
    append_unique(a, seen, ['SECTION'	,'RC_Demographic,RC_History,RC_Diagnostic_Procedures,RC_Radiology,RC_Procedures,RC_Admin,RC_Diagnosis,RC_Injuries,RC'])
    append_unique(a, seen, ['DEF'	,'100000', '0000000']) #add empty key

    # adding 7 letters DEF parts (several names per item)
    for n in names:
        d7 = n[:7]
        if d7 in indset:
            s = indset[d7]
        else:
            s = str(ind)
            indset[d7] = s
            ind = ind + 1
        append_unique(a,seen,["DEF",s,d7])
        append_unique(a,seen,["DEF",s,n[7:]])

    print("ind after 7 letter defs: ",ind)

    # adding 5 letters DEF parts (several names per item)
    ind = 250000
    b = []
    for n in names:
        d5 = n[:5]
        if d5 in indset:
            s = indset[d5]
        else:
            s = str(ind)
            indset[d5] = s
            ind = ind + 1
        d5 = "G_"+d5
        append_unique(a,seen,["DEF",s,d5])
        append_unique(a,seen,["DEF",s,"GROUP_"+n[7:]])
        b.append(["SET",d5,n[:7]])

    for c in codes:
        cc = c[:5].replace('.','')
        myset[cc] = c[:5]

    seen = {}
    for c in codes:
        cc = c[:5].replace('.','')
        for l in range(len(cc)-1,0,-1):
            sc = cc[:l]
            if sc in myset:
                curr = ["SET","G_"+myset[sc],"G_"+c[:5]]
                append_unique(b,seen,curr)
                #print "set->",c[:5],myset[sc],sc
                break

    a.extend(b)
    write_tabbed_list(out_f,a)
#for i in range(len(a)):
#    print "%s\t%s\t%s" % ("SET",a[i][1],a[i][0])

def prep_L2G(groups,L2G):
    for g in groups:
        for i in range(len(g[1])):
            L2G[g[1][i:i+1]] = g[0]


def prep_med_signal_file(f_in,f_out,L2G):
    a = []
    fin = open(f_in,"r")
    nl = 0
    buffer_size = 100000000
    fw = open(f_out, 'w') #erase file
    fw.close()
    for curr_line in fin:
#        print curr_line
        ci = curr_line.replace('\n','').replace('\r','').split('\t')
        cl = ci[3][0:1]
        if cl in L2G:
            ca = [str(ci[0]),L2G[cl],str(ci[2]),ci[3]]
            a.append(ca)
        nl = nl + 1
        if nl%1000000 == 0:
            print(nl/1000000,"million lines....\n")
        if nl >= buffer_size:
            write_tabbed_list(f_out,a, 'a')
            a = [] # clear buffer
            nl = 0
            print('Buffer flush')

 #       print ci
 #       print ca
    if len(a) > 0:
        write_tabbed_list(f_out,a, 'a')
    fin.close()


if __name__ == "__main__":
    path1 = "/server/Work/Users/Avi/thin/new/"
    #path = "/server/Work/Users/Ido/THIN_ETL/medical/"
    path = "/server/Work/Users/Ido/THIN_ETL/ahd/NonNumeric/"
    #prep_dict_file2(path1+"code2read2",path1+"dict.read_codes")

    groups = [["RC_Demographic","0"], ["RC_History","12R"], ["RC_Diagnostic_Procedures","34"], ["RC_Radiology","5"], ["RC_Procedures","678Z"], ["RC_Admin","9"], ["RC_Diagnosis","ABCDEFGHJKLMNPQ"],["RC_Injuries","STU"]]
    L2G = {}
    prep_L2G(groups,L2G)

    alls = "abcdefghij"
    #seyfa = "_MEDCODE"
    seyfa = "_AHDCODE"
    #seyfa2 = "_medsigs"
    seyfa2 = "_ahdsigs"
    for i in range(len(alls)):
        l = alls[i:i+1]
        print("working on "+path+l+seyfa)
        prep_med_signal_file(path+l+seyfa,path1+l+seyfa2,L2G)
