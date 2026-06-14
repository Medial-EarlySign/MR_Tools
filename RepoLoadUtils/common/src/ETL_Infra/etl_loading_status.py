import os
from datetime import datetime

def get_load_status(workdir):
    load_status=os.path.join(workdir, 'loading_status.state')
    completed=[]
    if os.path.exists(load_status):
        fr=open(load_status, 'r')
        completed=fr.readlines()
        fr.close()
    completed=list(map(lambda x:x.strip(),completed))
    sig_to_status = dict()
    #datetime, sig, status
    for s in completed:
        tokens=s.split('\t')
        if len(tokens)!=3:
            raise NameError('Error bad file format %s, expected 3 token and got line:\n%s'%(load_status, s))
        sig_to_status[tokens[1].strip()]=[tokens[0].strip(), tokens[2].strip()]
    return sig_to_status

def update_load_status(workdir, signal, status='Completed'):
    load_status=os.path.join(workdir, 'loading_status.state')
    sig_to_status = get_load_status(workdir)
    sig_to_status[signal]=['%s'%(datetime.now()), status]
    sorted_list=sorted(sig_to_status.items(), key= lambda x :x[0])
    fw=open(load_status, 'w')
    for sig,st in sorted_list:
        fw.write('%s\t%s\t%s\n'%(st[0],sig, st[1]))
    fw.close()

def get_load_batch_status(workdir):
    load_status=os.path.join(workdir, 'loading_batch_status.state')
    completed=[]
    if os.path.exists(load_status):
        fr=open(load_status, 'r')
        completed=fr.readlines()
        fr.close()
    completed=list(map(lambda x:x.strip(),completed))
    sig_to_status = dict()
    #datetime, sig, status
    for s in completed:
        tokens=s.split('\t')
        if len(tokens)!=3:
            raise NameError('Error bad file format %s, expected 3 token and got line:\n%s'%(load_status, s))
        sig_to_status[tokens[1].strip()]=[tokens[0].strip(), int(tokens[2].strip())]
    return sig_to_status

def update_batch_load_status(workdir, signal, batch_num, is_override=False):
    load_status=os.path.join(workdir, 'loading_batch_status.state')
    sig_to_status = get_load_batch_status(workdir)
    if signal in sig_to_status:
        update_date, last_batch= sig_to_status[signal]
        if not(is_override) and batch_num!=last_batch+1:
            raise NameError('Last batch was %d, trying to update status to batch %d'%(last_batch, batch_num))
    sig_to_status[signal]=['%s'%(datetime.now()), batch_num]
    sorted_list=sorted(sig_to_status.items(), key= lambda x :x[0])
    fw=open(load_status, 'w')
    for sig,st in sorted_list:
        fw.write('%s\t%s\t%s\n'%(st[0],sig, st[1]))
    fw.close()