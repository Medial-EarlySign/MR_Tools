import os

class SignalInfo:
    def __init__(self, _name, t_channels_vec, v_channels_vec, value_categorical_bit, classes = []):
        self.name=_name
        self.t_ch = t_channels_vec
        self.v_ch= v_channels_vec
        self.v_categ= value_categorical_bit
        self.classes = classes
        self.units= []
    def has_cetgorical(self):
        for ch in self.v_categ:
            if ch !='0':
                return True
        return False
    def  __repr__(self):
        return '%s :: %s, %s, %s, %s'%(self.name, self.t_ch, self.v_ch, self.v_categ, self.classes)
    def print_help(self):
        print('Signal "%s"'%(self.name) , end =" ", flush=True)
        columns=['pid', 'signal']
        if len(self.t_ch) > 0:
            print('has %d time channels of types [%s]'%( len(self.t_ch), ','.join(self.t_ch)), end =" ", flush=True)
            columns = columns+ ['time_%d'%i for i in range(len(self.t_ch))]
        if len(self.v_ch) > 0:
            if len(self.t_ch) > 0:
                print('and', end =' ', flush=True)
            print('has %d value channels of types [%s], categrical bit vector: %s'%( len(self.v_ch), ','.join(self.v_ch), self.v_categ), flush=True)
            columns = columns+ ['value_%d'%i for i in range(len(self.v_ch))]
        print('DataFrame should have those columns: %s'%(columns), flush=True)
        #Now, lets print whats columns we expecte to see
        

def load_signals_map(FULL_SIGNALS_TYPES, workdir):
    sig_types = _read_signals_map(FULL_SIGNALS_TYPES)
    os.makedirs(os.path.join(workdir, 'configs'), exist_ok=True)
    if os.path.exists(os.path.join(workdir, 'configs', 'rep.signals')):
        sig_types_local = _read_signals_map(os.path.join(workdir, 'configs', 'rep.signals'))
        #merge with sig_types, override:
        for sig, vals in sig_types_local.items():
            #if sig not in sig_types:
            #    print('Adding signal %s'%(sig))
            if sig in sig_types:
                print('Overiding signal definition from local changes %s'%(sig), flush=True)
            sig_types[sig] = vals
    return sig_types

def _read_signals_map(cfg_file):
    #read signals config file
    fr=open(cfg_file, 'r')
    lines=fr.readlines()
    fr.close()
    
    lines = list(map(lambda x: x.strip(),lines))
    lines = list(filter(lambda x: not(x.startswith('#')) and len(x)>0,lines))
    type_d=dict()
    sig_to_type=dict()
    for line in lines:
        tokens=line.split('\t')
        if line.startswith('GENERIC_SIGNAL_TYPE'):
            if len(tokens)<3:
                raise NameError('Bad Format in line \n%s'%(line))
            #prase time, value channels:
            tt=tokens[2].strip()
            state=None
            t_ch=[]
            v_ch=[]
            legit_type=set(['i', 'l', 'f', 's', 'c', 'd', 'D'])
            legit_type=legit_type.union(set(map(lambda x: 'u'+x, legit_type)))
            for t in tt:
                if t=='T' or t=='V':
                    state=t
                elif t=='(' or t==',' or t==' ':
                    continue
                elif t==')':
                    state=None
                    continue
                elif t in legit_type:
                    if state is None:
                        raise NameError('Cant parse type %s'%(tt))
                    elif state=='T':
                        t_ch.append(t)
                    else:
                        v_ch.append(t)
                else:
                    raise NameError('Cant parse type %s'%(tt))
                    
            type_d[tokens[1].strip()]=[t_ch, v_ch]
            
        elif line.startswith('SIGNAL'):
            if len(tokens)<5:
                raise NameError('Bad Format in line(%d) \n%s'%(len(tokens), line))
            type_s=tokens[3].strip().split(':')[-1]
            if type_s not in type_d:
                raise NameError('Unknown type in line \n%s'%(line))
            type_s=type_d[type_s]
            numeric_categ=''
            if len(tokens)>5:
                numeric_categ = tokens[5].strip()
            signal_classes = tokens[4].strip().split(',')
            
            units=[]
            if len(tokens)>6:
                units=tokens[6].strip().split('|')
            #4 lists: time_channels, value_channeles, categorical_for each value, signal hierarchy
            si=SignalInfo(tokens[1].strip(), type_s[0], type_s[1], numeric_categ, signal_classes)
            si.units=units
            sig_to_type[tokens[1].strip()]= si
        else:
            raise NameError('Unknown line \n%s'%(line))
        
    return sig_to_type