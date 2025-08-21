import sys, ctypes, struct, os, re, __builtin__

__builtin__.GLOBAL_DEBUG_FLAG = False

def set_debug(flg):
    __builtin__.GLOBAL_DEBUG_FLAG = flg

number_ptr = re.compile('[0-9]+')
def is_int(st):
    return number_ptr.match(st) is not None
 
def read_primitive(type, fr, cnt = 1 ,quiet = None):
    convert_types_dict = {'int':'i', 'float':'f', 'char':'c', 'size_t':'N', 'double':'d', 'long':'l', 'unsigned long':'L',
                          'unsigned int':'I', 'short':'h', 'unsigned short':'H', 'bool':'?', 'longlong': 'q', 'unsigned long long': 'Q',
                          'unsigned char':'B', 'signed char':'b'}
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #if (sys.maxsize < 2**32 and (type == 'size_t')): #if32bit and certain type
    if (type == 'size_t'): #always do
        type = 'longlong'
    name = 'c_' + type
    sz = eval('ctypes.sizeof(ctypes.%s)'%(name))
   
    prev = fr.tell()
    binary = fr.read(sz * cnt)
    after = fr.tell()
    if (prev == after):
        raise NameError('Reached EOF')
    #print('%s'%(binary))
    #val = eval('ctypes.%s(binary).value'%(name))
    if cnt == 1:
        val = struct.unpack(convert_types_dict[type] ,binary)[0]
    else:
        val = list(struct.unpack('%d%s'%(cnt,convert_types_dict[type]) ,binary))
    if not(quiet):
        print('reading primitive %s with value = %s'%(type, val))
    return val

def read_string(fr, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    sz = read_primitive('size_t', fr) #64bit python
    #sz2 = read_primitive('size_t', fr)
    #print('DEBUG: %s'%sz2)
    val = ''
    if (sz > 0):
        prev = fr.tell()
        try:
            bin_data = fr.read(sz)
        except:
            print('Tried reading string of size %d'%(sz))
            raise
        after = fr.tell()
        if (prev == after):
            raise NameError('Reached EOF')
        try:
            val = struct.unpack('%ds'%(sz), bin_data)[0].decode('ascii')
        except:
            print(sz, bin_data)
            raise
    prev = fr.tell()
    check = fr.read(1) #read 0 terminate
    after = fr.tell()
    if (prev == after):
        raise NameError('Reached EOF')
    if (check != b'\x00'):
        raise NameError('read string(%d) %s that doesn\'t end with 0. got %s'%(sz, val, check))
    if not(quiet):
        print('read string "%s"'%val)
    return val

def read_string_raw(fr, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    sz = read_primitive('int', fr) #64bit python
    #sz2 = read_primitive('size_t', fr)
    #print('DEBUG: %s'%sz2)
    val = ''
    if (sz > 0):
        prev = fr.tell()
        try:
            bin_data = fr.read(sz)
        except:
            print('Tried reading string of size %d'%(sz))
            raise
        after = fr.tell()
        if (prev == after):
            raise NameError('Reached EOF')
        try:
            val = struct.unpack('%ds'%(sz), bin_data)[0]
        except:
            print(sz, bin_data)
            raise
    if not(quiet):
        print('read string "%s"'%val)
    return val

def read_list(object_decl, typ, fr, use_32 = False, quiet = None):
    supported_primitives = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short'] 
    set_pr = set(supported_primitives)
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #read int:
    val = []
    sz_type = 'size_t'
    if (use_32):
        sz_type = 'int'
    sz = read_primitive(sz_type, fr) #64bit python
    if (sz > 10000000):
        print('Array > 10000000 - got %d'%sz)
    #print('List Size = %d'%sz)
    if sz <= 1 or typ not in set_pr:
        for i in range(sz):
            v = read_next(object_decl, typ, fr)
            val.append(v)
    else:
        #print('Test read list of primitives size=%d'%sz)
        v = read_primitive(typ, fr, sz)
        #print(len(v))
        val = v
    if not(quiet):
        print('read list<%s> %s'%(typ,val))
    return val

def read_map(object_decl, type_key,type_val, fr, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    sz = read_primitive('size_t', fr) #64bit python
        
    val = dict()
    for i in range(sz):
        key = read_next(object_decl,type_key, fr)
        value = read_next(object_decl,type_val, fr)
        val[key] = value
    if not(quiet):
        print('read map<%s, %s> %s'%(type_key,type_val, val))
    return val

def read_pair(object_decl, type_key,type_val, fr, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    key = read_next(object_decl,type_key, fr)
    value = read_next(object_decl,type_val, fr)
    if not(quiet):
        print('read pair<%s, %s> (%s, %s)'%(type_key,type_val, key, value))
    return (key, value)

def read_fixed_list(object_decl, type, fr, sz, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #read int:
    val = []
    for i in range(sz):
        v = read_next(object_decl, type, fr)
        val.append(v)
    if not(quiet):
        print('read list<%s> %s'%(type,val))
    return val

def read_complex(object_decl, type, fr, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #print('reading %s'%(type))
    #check if complex type in object_decl:
    #if not(quiet):
    #    print('Try Read Complex %s'%(type))
    inner_type = type[type.find('<')+1:-1]
    if (type.startswith('vector') or type.startswith('set') or type.startswith('unordered_set') or type.startswith('vector_32') ):
        return read_list(object_decl, inner_type, fr, type.startswith('vector_32'), quiet)
    elif (type.startswith('map') or type.startswith('unordered_map')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        return read_map(object_decl, key_type,val_type, fr, quiet)
    elif (type.startswith('pair')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        return read_pair(object_decl, key_type,val_type, fr, quiet)
    elif type.endswith(']'):
        #fixed array:
        inner_type = type[:type.find('[')]
        sz = int(type[type.find('[') + 1:-1])
        return read_fixed_list(object_decl, inner_type, fr, sz, quiet)
    else:
        raise NameError('Unsupported type %s'%type)
        

def read_inner_type(object_decl, obj_dcl, fr, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #if not(quiet):
    #    print('Try Read inner %s'%(obj_dcl.class_name))
    val = []
    types = list(map(lambda x: x[1],obj_dcl.vars))
    names = list(map(lambda x: x[0],obj_dcl.vars))
    next_ser = None 
    for i in range(len(types)):
        
        #check if has array type using size of variable:
        if (types[i].endswith(']')):
            inner_tp = types[i][types[i].find('[')+1:-1]
            type_ext = types[i][:types[i].find('[')]
            if not(is_int(inner_tp)):
                ind = -1
                for j in range(len(val)):
                    if val[j][0] == inner_tp:
                        ind = j
                        break
                if ind == -1:
                    raise NameError('Couldn\'t find in variable %s %s. defination for %s which is not integer'%(types[i], names[i], inner_tp))
                if (types[ind] != 'int'):
                    raise NameError('found wrong reference in variable %s %s. defination for %s is not integer. it\'s %s'%(types[i], names[i], inner_tp, types[ind]))
                inner_tp = val[ind][1]
                types[i] = '%s[%s]'%(type_ext, inner_tp)

        tp_nm = (names[i], types[i])        
        v = read_next(object_decl, tp_nm, fr, quiet)
        val.append(v)
        if obj_dcl.abstract_field is not None and  names[i] == obj_dcl.abstract_field: #read
            next_ser = v[1]
    if obj_dcl.abstract_field is not None and next_ser is None:
        raise NameError('Got Abstract class %s but haven\'t found abstract field %s'%(obj_dcl.class_name ,obj_dcl.abstract_field))
    if obj_dcl.abstract_field is not None and next_ser not in obj_dcl.abstract_map:
        raise NameError('Got Abstract class %s but haven\'t mapping value for %d in object :\n%s'%(obj_dcl.class_name, next_ser, obj_dcl))
    
    if obj_dcl.abstract_field is not None:
        son_type = obj_dcl.abstract_map[next_ser]
        if (son_type.endswith(']')):
            inner_tp = son_type[son_type.find('[')+1:-1]
            type_ext = son_type[:son_type.find('[')]
            if not(is_int(inner_tp)):
                ind = -1
                for j in range(len(val)):
                    if val[j][0] == inner_tp:
                        ind = j
                        break
                if ind == -1:
                    raise NameError('Couldn\'t find in variable %s %s. defination for %s which is not integer'%(types[i], names[i], inner_tp))
                if (types[ind] != 'int'):
                    raise NameError('found wrong reference in variable %s %s. defination for %s is not integer. it\'s %s'%(types[i], names[i], inner_tp, types[ind]))
                inner_tp = val[ind][1]
                son_type = '%s[%s]'%(type_ext, inner_tp)
        #continue reading type - add support for variables for array reference:
        son_val = read_next(object_decl, son_type, fr, quiet) #append fields to class:
        val = val + son_val
    if not(quiet):
        print('Read object type %s, value = %s'%(obj_dcl.class_name, val))
                
    return val
    

def read_next(object_decl, type_name, fr, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    supported_primitives = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short'] 
    set_pr = set(supported_primitives)
    typ = type_name
    var_name = ''
    if type(type_name) == list or type(type_name) == tuple:
        var_name,typ = type_name
    #if not(quiet):
    #    print('Try Read type %s for %s'%(typ, var_name))

    try:    
        if (typ in set_pr):
            val = read_primitive(typ, fr, 1, quiet)
        elif (typ =='string'):
            val = read_string(fr, quiet)
        elif (typ =='string_raw'):
            val = read_string_raw(fr, quiet)
        elif (typ in object_decl):
            obj_dcl = object_decl[typ]
            val = read_inner_type(object_decl, obj_dcl, fr, quiet)
        else:
            val = read_complex(object_decl, typ, fr, quiet)
    except:
        if (typ in object_decl):
            obj_dcl = object_decl[typ]
            print('Failed Converting object "%s". Type %s'%(var_name, obj_dcl))
        else:
            print('Failed Converting object (%s %s)'%(typ,var_name))
        raise

    res = val
    if (var_name != ''):
        res = (var_name, val)
    if not(quiet):
        print('Read type %s - got value = %s'%(type_name, val))
    return res

#example for c_types_names:  ADD_SERIALIZATION_FUNCS(int processor_type, string signalName, int time_channel,int val_channel,vector<string> req_signals,
#         vector<string> aff_signals, int params.take_log,float params.missing_value,bool params.doTrim,bool params.doRemove,
#         float trimMax,float trimMin,float removeMax,float removeMin,string nRem_attr,string nTrim_attr,string nRem_attr_suffix,string nTrim_attr_suffix)
def deserialize(bin_path, object_decl, type_name, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #types = list(map(lambda x: x.strip(), c_types_names.split(',')))
    #types.insert(0, 'int') # add version reading
    #types = list(map(lambda x: x.replace('string', 'vector<char>'), types))
    
    fr = open(bin_path, 'rb')
    version = read_primitive('int', fr)
    print('Deserializing %s of Type %s version %d'%(bin_path, type_name, version))
    #print('Object Version %d'%(version))
    #obj = [('version', version)]
    obj = []
    
    val = read_next(object_decl, type_name, fr, quiet)
    obj = Result_Object(object_decl, type_name,val)
    obj.version = version

    fr.close()
    #print(types)
    print('Done reading %s of Type %s'%(bin_path, type_name))
    return obj

def write_primitive(typ, fw, val, cnt = 1 ,quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    convert_types_dict = {'int':'i', 'float':'f', 'char':'c', 'size_t':'N', 'double':'d', 'long':'l', 'unsigned long':'L',
                          'unsigned int':'I', 'short':'h', 'unsigned short':'H', 'bool':'?', 'longlong': 'q', 'unsigned long long': 'Q',
                          'unsigned char':'B', 'signed char':'b'}
    if not(quiet):
        print('Try Write primitive %s - %s'%(typ, val))
    #if (sys.maxsize < 2**32 and (typ == 'size_t')): #if32bit and certain type
    if (typ == 'size_t'): #always do
        typ = 'longlong'
    if cnt == 1:
        fw.write(struct.pack(convert_types_dict[typ] ,val))
    else:
        #print('cnt = %d, len_type=%d'%(cnt, len(val)))
        fw.write(struct.pack('%d%s'%(cnt,convert_types_dict[typ]) ,*val))
    if not(quiet):
        print('write primitive %s with value = %s'%(typ, val))
    return val

def write_string(fw, val, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    write_primitive('size_t', fw, len(val))
    if (len(val) > 0):
        fw.write(struct.pack('%ds'%(len(val)),val.encode('ascii')))
    fw.write(b'\0') #write 0 terminate
    if not(quiet):
        print('write string "%s"'%val)

def write_string_raw(fw, val, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    write_primitive('int', fw, len(val))
    if (len(val) > 0):
        fw.write(struct.pack('%ds'%(len(val)),val))
    if not(quiet):
        print('write string "%s"'%val)

def write_list(object_decl,typ, fw, val, is_32 ,quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    supported_primitives = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short'] 
    set_pr = set(supported_primitives)
    sz_type = 'size_t'
    if is_32:
        sz_type = 'int'
    if not(quiet):
        print('Try Write List<%s> '%(typ), val)
    write_primitive(sz_type, fw, len(val))
    #for i in range(len(val)):
    #    write_next(object_decl,typ, fw, val[i])
    if len(val) <= 1 or typ not in set_pr:
        for i in range(len(val)):
            write_next(object_decl,typ, fw, val[i])
    else:
        write_primitive(typ, fw, val, len(val))
    if not(quiet):
        print('write list<%s>'%(typ))

def write_map(object_decl,type_key,type_val, fw, val, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    write_primitive('size_t', fw, len(val))
    
    for key,value in sorted(val.items()):
        write_next(object_decl,type_key, fw, key)
        write_next(object_decl,type_val, fw, value)
    if not(quiet):
        print('write map<%s, %s>'%(type_key,type_val))
    
def write_pair(object_decl, type_key,type_val, fw,val, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    write_next(object_decl,type_key, fw, val[0])
    write_next(object_decl,type_val, fw, val[1])
    if not(quiet):
        print('write pair<%s, %s> (%s, %s)'%(type_key,type_val, val[0], val[1]))

def write_fixed_list(object_decl,typ, fw, val ,quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    for i in range(len(val)):
        write_next(object_decl,typ, fw, val[i])
    if not(quiet):
        print('write %s[%d]:'%(typ, len(val)))

def write_complex(object_decl, typ, fw, val, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    #print('reading %s'%(type))
    inner_type = typ[typ.find('<')+1:-1]
    if (typ.startswith('vector') or typ.startswith('set') or typ.startswith('unordered_set')):
        write_list(object_decl,inner_type, fw, val, typ.startswith('vector_32'), quiet)
    elif (typ.startswith('map') or typ.startswith('unordered_map')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        write_map(object_decl,key_type,val_type, fw,val, quiet)
    elif (typ.startswith('pair')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        write_pair(object_decl,key_type,val_type, fw, val,quiet)
    elif typ.endswith(']'):
        #fixed array:
        inner_type = typ[:typ.find('[')]
        #sz = int(typ[typ.find('[') + 1:-1])
        write_fixed_list(object_decl, inner_type, fw, val, quiet)
    else:
        raise NameError('Unsupported type %s'%typ)
        
def write_inner_type(object_decl, obj_dcl, fw, obj, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    if not(quiet):
        print('Try Write inner %s'%(obj_dcl.class_name))
    types = list(map(lambda x: x[1],obj_dcl.vars))
    names = list(map(lambda x: x[0],obj_dcl.vars))
    next_ser = None
    val = obj
    #val = obj[0]
    old_decl = object_decl #TODO: fix and get old declartion
    #get object declartion in old:
    if obj_dcl.class_name not in old_decl:
        raise NameError('Couldn\'t find class %s in old decaltion - fix that'%(obj_dcl.class_name))
    old_obj_dcl = old_decl[obj_dcl.class_name]

    abs_fld_val = None
    for i in range(len(types)):
        v= val[i]
        if obj_dcl.abstract_field is not None and obj_dcl.abstract_field == v[0]:
            #print('In ABSTRACT FIELD i=%d, names[i]=%s, v=%s'%(i, names[i], v))
            abs_fld_val = v[1]
            if abs_fld_val not in old_obj_dcl.abstract_map:
                raise NameError('Got Abstract class %s but haven\'t found for %d mapping value for it :\n%s'%(obj_dcl.class_name, abs_fld_val, obj_dcl))
            search_name = old_obj_dcl.abstract_map[abs_fld_val]
            #look backward
            if search_name not in obj_dcl.reverse_map:
                raise NameError('Got Abstract class %s but haven\'t mapping value for %s'%(obj_dcl.class_name, search_name))
            abs_fld_val = obj_dcl.reverse_map[search_name]
            v = ('ABSTRACT', abs_fld_val)
        write_next(object_decl, types[i], fw, v[1], quiet)

    if obj_dcl.abstract_field is not None and abs_fld_val is None:
        raise NameError('Got Abstract class %s but haven\'t found abstract field %s'%(obj_dcl.class_name ,obj_dcl.abstract_field))
    if obj_dcl.abstract_field is not None and abs_fld_val not in obj_dcl.abstract_map:
        raise NameError('Got Abstract class %s but haven\'t mapping value for %d in object :\n%s'%(obj_dcl.class_name, abs_fld_val, obj_dcl))
    
    if obj_dcl.abstract_field is not None:
        son_type = obj_dcl.abstract_map[abs_fld_val]
        write_next(object_decl, son_type, fw, val[len(types):], quiet) #append fields to class:
    if not(quiet):
        print('Write object type %s, value'%(obj_dcl.class_name))

def write_next(object_decl, type, fw, val, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    supported_primitives = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short'] 
    set_pr = set(supported_primitives)
    #if not(quiet):
    #    print('Try Write type %s with val=%s'%(type, val))
    if (type in set_pr):
        write_primitive(type, fw, val, 1, quiet)
    elif (type =='string'):
        write_string(fw, val, quiet)
    elif (type =='string_raw'):
        write_string_raw(fw, val, quiet)
    elif (type in object_decl):
        obj_dcl = object_decl[type]
        write_inner_type(object_decl, obj_dcl, fw, val, quiet)
    else:
        write_complex(object_decl, type, fw,val, quiet)


def serialize(bin_path, obj, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    print('Serializing %s of Type %s'%(bin_path, obj.object_type))
    if not(quiet):
        print('Write Object Version %d'%(obj.version))
    fw = open(bin_path, 'wb')
    write_primitive('int', fw, obj.version)
    
    write_next(obj.object_decl_version,obj.object_type , fw ,obj.obj, quiet)
    fw.close()
    print('Done Serializing %s of Type %s'%(bin_path, obj.object_type))
    
def fetch_all_files_rec(path, all_files =[]):
    #read recursively all files
    all_sons = os.listdir(path)
    all_sons = list(map(lambda x: os.path.join(path, x) ,all_sons))
    all_dirs  = list(filter(lambda x: os.path.isdir(x) ,all_sons))
    all_files2 = list(filter(lambda x: os.path.isfile(x) ,all_sons))
    all_files = all_files + all_files2
    for d in all_dirs:
        all_files2 = fetch_all_files_rec(d)
        all_files = all_files + all_files2
    return all_files

class VariableStruct:
    def __init__(self, cl_name):
        self.class_name = cl_name
        self.vars = []
        self.abstract_field = None
        self.abstract_map = dict()
        self.reverse_map = dict()
        
    def __repr__(self):
        res = 'Class_%s'%(self.class_name)
        if (self.abstract_field is not None):
            res += ', ABSTRACT_FIELD=%s, mapping=%s'%(self.abstract_field, self.abstract_map)
        res += ', Vars:\n'
        res += '\n'.join(map(lambda x: '%s %s'%(x[1], x[0]),self.vars))
        return res

def read_declaration(path):
    obj_name = os.path.basename(path)
    var = VariableStruct(obj_name)
    #var.vars = []
    fr = open(path, 'r')
    lines = fr.readlines()
    fr.close()
    lines = list(filter(lambda x: len(x) > 0,map(lambda x: x.strip(),lines)))
    var_names = set()
    for line in lines:
        line = line.strip()
        if len(line) == 0 or line.startswith('#'):
            continue
        tokens = list(map(lambda x: x.strip(),line.split('\t')))
        if len(tokens) < 2:
            raise NameError('BadFileFormat in %s - got line:\n%s\nSHOULD CONTAIN AT LEAST 1 TAB'%(path, line))
        var_name, var_type = tokens[:2]
        if (var_type == 'ABSTRACT'):
            var_type = 'int' #Serialize this field and it will be used to decied which serialization to activate
            if (var.abstract_field is not None):
                raise NameError('Got already Abstract Field in type %s - abstract field:%s'%(var.class_name, var.abstract_field))
            var.abstract_field = var_name
        if (var_name != 'ABSTRACT'):
            var.vars.append((var_name, var_type))
            if (var_name in var_names):
                raise NameError('Got Already Variable Name in type %s - variablr name:%s'%(var.class_name, var_name))
            var_names.add(var_name)
        else:
            if len(tokens) != 3:
                raise NameError('BadFileFormat in %s - got line:\n%s\nSHOULD CONTAIN Excatly 2 TAB in ABSTRACT to map value to class'%(path, line))
            map_val_key, obj_map_val = tokens[1:]
            var.abstract_map[int(map_val_key)] = obj_map_val
            var.reverse_map[obj_map_val] = int(map_val_key)
    return var

def read_objects_declarations(path):
    decalrations = dict()
    all_files = fetch_all_files_rec(path)
    for file in all_files:
        obj_name = os.path.basename(file)
        var = read_declaration(file)
        decalrations[obj_name] = var
    return decalrations

def ls_vars(v):
    if type(v) != list:
        raise NameError('input should be list of tuples')
    return list(map(lambda x: x[0],v))

def get_var(v, k):
    if type(v) != list:
        raise NameError('input should be list of tuples')
    res = list(filter(lambda x: x[0] == k,v))
    if len(res) == 0:
        raise NameError('Couldn\'t find %s in object. option list is : %s'%(k, ls_vars(v)))
    if len(res) > 1:
        print('More than 1 option for %s in object.'%(k))
        return list(map(lambda x: x[1],res))
    return res[0][1]

#search recursivly in obj for key==k and value ==v
def get_vars(objects_decl, obj_name, obj ,k, v):
    skip_ls = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short', 'string'] 
    set_skip = set(skip_ls)
    if obj_name in set_skip:
        return []
    poses = []
    if obj_name not in objects_decl: #it's complex:
        inner_type = obj_name[obj_name.find('<')+1:-1]
        if obj_name.startswith('pair'):
            key_type = inner_type[ :inner_type.find(',') ].strip()
            val_type = inner_type[ inner_type.find(',')+1: ].strip()
            p_inner = get_vars(objects_decl,key_type , obj[0], k, v)
            p_inner2 = get_vars(objects_decl,val_type , obj[1], k, v)
            return list(map(lambda ls: [0] + ls ,p_inner)) + list(map(lambda ls: [1] + ls ,p_inner2))
        elif obj_name.startswith('map') or obj_name.startswith('unordered_map'): #map
            for i in range(len(obj)):
                inner_obj = obj[i]
                key_type = inner_type[ :inner_type.find(',') ].strip()
                val_type = inner_type[ inner_type.find(',')+1: ].strip()
                p_inner = get_vars(objects_decl,key_type , inner_obj[0] , k, v)
                p_inner2 = get_vars(objects_decl,val_type , inner_obj[1] , k, v)
                return list(map(lambda ls: [i, 0] + ls ,p_inner)) + list(map(lambda ls: [i, 1] + ls ,p_inner2))
        elif obj_name.startswith('vector') or obj_name.startswith('unordered_set') or obj_name.startswith('set') or obj_name.endswith(']'): #vector
            for i in range(len(obj)):
                inner_obj = obj[i]
                p_inner = get_vars(objects_decl,inner_type , inner_obj , k, v)
                return list(map(lambda ls: [i] + ls ,p_inner))
        else:
            raise NameError('Unsupported type %s'%(obj_name))
        
    if len(obj) == 0:
        return []
    if obj_name not in objects_decl:
        raise NameError('Unsupported type %s'%(obj_name))
    obj_dcl = objects_decl[obj_name]
    types = list(map(lambda x:x[1],obj_dcl.vars))

    next_ser = None
    #inner object:
    full_types = types
    for i in range(len(obj)):
        if obj_dcl.abstract_field is not None and  obj[i][0] == obj_dcl.abstract_field: #read
            next_ser = obj[i][1]
        if (obj[i][0] == k and (v is None or obj[i][1] == v)):
            poses.append([i, -1]) #reached end
            continue
        if i >= len(types):
            if obj_dcl.abstract_field is None:
                raise NameError('Object is not abstract and has more field than defined - check version. class_name=%s'%(obj_name))
            if next_ser is None:
                raise NameError('Object is abstract and has no abstract field value - check version. class_name=%s'%(obj_name))
            if next_ser not in obj_dcl.abstract_map:
                raise NameError('Object is abstract and has no mapping for field value - check version. class_name=%s, map_value=%d'%(obj_name, next_ser))
            son_type = obj_dcl.abstract_map[next_ser]
            if son_type not in objects_decl:
                raise NameError('Couldn\'t Find object type %s - check version'%(son_type))
            son_dcl = objects_decl[son_type]
            full_types = types + list(map(lambda x: x[1], son_dcl.vars))
        if i >= len(full_types):
            raise NameError('Object has more field than defined - check version. class_name=%s'%(obj_name))
        #try search down:
        inner_obj = obj[i][1]
        p_inner = get_vars(objects_decl, full_types[i], inner_obj, k, v)
        if len(p_inner) > 0:
            poses = poses + list(map(lambda ls: [i,1] + ls ,p_inner))
        
    return poses

def get_names_types(objects_decl, obj_name, obj):
    if obj_name not in objects_decl:
        raise NameError('Couldn\'t find %s type in version'%(obj_name))
    obj_d = objects_decl[obj_name]
    name_types_res = obj_d.vars
    types = list(map(lambda x:x[1],obj_d.vars))
    names = list(map(lambda x:x[0],obj_d.vars))
    #fetch abstract:
    next_ser = None
    if obj_d.abstract_field is not None:
        for i in range(len(names)):
            if obj[i][0] == obj_d.abstract_field: #read
                next_ser = obj[i][1]
                break
        if next_ser is None:
            print(obj_name)
            print(obj)
            #print(','.join(map(lambda x: x[0],obj)))
            raise NameError('Warning: In Abstract Class %s - no son class found'%(obj_name))
        if next_ser not in obj_d.abstract_map:
            raise NameError('Object is abstract and has no mapping for field value - check version. class_name=%s, map_value=%d'%(obj_name, next_ser))
        son_type = obj_d.abstract_map[next_ser]
        #print('Son_type=%s'%(son_type))
        son_vars = get_names_types(objects_decl, son_type, obj[len(names):])
        name_types_res = name_types_res + son_vars
        
    return name_types_res
    

def convert_list(old_decl, object_decl,typ, val, is_32 ,quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    if not(quiet):
        print('Try Convert List<%s> '%(typ), val)
    obj = []
    for i in range(len(val)):
        v = convert_next(old_decl, object_decl,typ, val[i])
        obj.append(v)
    if not(quiet):
        print('write list<%s>'%(typ))
    return obj

def convert_map(old_decl, object_decl,type_key,type_val, val, quiet=None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    obj = dict()
    for key,value in val.items():
        k = convert_next(old_decl, object_decl,type_key, key)
        v = convert_next(old_decl, object_decl,type_val, value)
        obj[k] = v
    if not(quiet):
        print('Convert map<%s, %s>'%(type_key,type_val))
    return obj
    
def convert_pair(old_decl, object_decl, type_key,type_val,val, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    v1 = convert_next(old_decl, object_decl,type_key, val[0])
    v2 = convert_next(old_decl, object_decl,type_val, val[1])
    if not(quiet):
        print('Convert pair<%s, %s> (%s, %s)'%(type_key,type_val, val[0], val[1]))
    return (v1, v2)

def convert_fixed_list(old_decl, object_decl,typ, val ,quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    obj = []
    for i in range(len(val)):
        v = convert_next(old_decl, object_decl,typ, val[i])
        obj.append(v)
    if not(quiet):
        print('Convert %s[%d]:'%(typ, len(val)))
    return obj

def convert_complex(old_decl, object_decl, typ, val, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    if not(quiet):
        print('Try Convert complex %s, value.type=%s'%(typ, type(val)))
    #print('reading %s'%(type))
    inner_type = typ[typ.find('<')+1:-1]
    if (typ.startswith('vector') or typ.startswith('set') or typ.startswith('unordered_set')):
        return convert_list(old_decl, object_decl,inner_type, val, typ.startswith('vector_32'), quiet)
    elif (typ.startswith('map') or typ.startswith('unordered_map')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        return convert_map(old_decl, object_decl,key_type,val_type,val, quiet)
    elif (typ.startswith('pair')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        return convert_pair(old_decl, object_decl,key_type,val_type, val,quiet)
    elif typ.endswith(']'):
        #fixed array:
        inner_type = typ[:typ.find('[')]
        #sz = int(typ[typ.find('[') + 1:-1])
        return convert_fixed_list(old_decl, object_decl, inner_type, val, quiet)
    else:
        raise NameError('Unsupported type %s'%typ)

def find_name_idx(obj, nm, tp, old_obj_dcl):
    for i in range(len(obj)):
        if obj[i][0] == nm and old_obj_dcl.vars[i][1] == tp:
            return i
    #print('search=%s, type=%s, object_fields = %s, types=%s'%(nm, tp, ','.join(map(lambda x: x[0],obj)), ','.join(map(lambda x: x[1], old_obj_dcl.vars))))
    return -1

def get_default_in_val(object_decl, obj_dcl):
    types = list(map(lambda x: x[1],obj_dcl.vars))
    names = list(map(lambda x: x[0],obj_dcl.vars))
    val = []
    for i in range(len(types)):
        #find in obj same name:
        v = (names[i], get_default_val(object_decl, types[i]))  
        val.append(v)
    if obj_dcl.abstract_field is not None:
        print('Warning - Using Deafult value for abstract on field %s of class %s'%(obj_dcl.abstract_field, obj_dcl.class_name))
        son_type = obj_dcl.abstract_map[0]
        v_s = get_default_val(object_decl, son_type) #append fields to class:
        val = val + v_s
    return val

def get_default_comp_val(object_decl, typ):
    inner_type = typ[typ.find('<')+1:-1]
    if (typ.startswith('vector') or typ.startswith('set') or typ.startswith('unordered_set')):
        return []
    elif (typ.startswith('map') or typ.startswith('unordered_map')):
        return []
    elif (typ.startswith('pair')):
        key_type = inner_type[ :inner_type.find(',') ].strip()
        val_type = inner_type[ inner_type.find(',')+1: ].strip()
        k = get_default_val(object_decl, key_type)
        v = get_default_val(object_decl, val_type)
        return (k, v)
    elif typ.endswith(']'):
        #fixed array:
        inner_type = typ[:typ.find('[')]
        sz = int(typ[typ.find('[') + 1:-1])
        val = []
        for i in range(sz):
            v = get_default_val(object_decl, inner_type)
            val.append(v)
        return val
    else:
        raise NameError('Unsupported type %s'%typ)

def get_default_val(object_decl, typ):
    supported_primitives = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short'] 
    set_pr = set(supported_primitives)
    #if not(quiet):
    #    print('Try Write type %s with val=%s'%(type, val))
    if (typ in set_pr):
        if typ =='char':
            return ''
        elif typ =='bool':
            return False
        else:
            return 0
    elif (typ =='string' or typ =='string_raw'):
        return ''
    elif (typ in object_decl):
        val = []
        obj_dcl = object_decl[typ]
        return get_default_in_val(object_decl, obj_dcl)
        
    else:
        return get_default_comp_val(object_decl, typ)

def convert_inner_type(old_decl, object_decl, obj_dcl, obj, quiet = None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    if not(quiet):
        print('Try Convert inner %s'%(obj_dcl.class_name))
    types = list(map(lambda x: x[1],obj_dcl.vars))
    names = list(map(lambda x: x[0],obj_dcl.vars))
    if (obj_dcl.class_name == 'MedGDLMParams'):
        print('IN MedGDLMParams - names=%s'%(','.join(names)))
    next_ser = None
    #get object declartion in old:
    if obj_dcl.class_name not in old_decl:
        raise NameError('Couldn\'t find class %s in old decaltion - fix that'%(obj_dcl.class_name))
    old_obj_dcl = old_decl[obj_dcl.class_name]

    abs_fld_val = None
    val = []
    for i in range(len(types)):
        #find in obj same name:
        idx = find_name_idx(obj, names[i], types[i], old_obj_dcl)
        if idx < 0:
            print('Couldn\'t find field %s in object %s - Adding it'%(names[i], obj_dcl.class_name))
            #print(len(obj))
            v = (names[i], get_default_val(object_decl, types[i]))
        else:
            if not(quiet):
                print('Found %s(%d) in %d'%(names[i], i, idx))
            v = obj[idx]
        if obj_dcl.abstract_field is not None and obj_dcl.abstract_field == v[0]:
            #print('In ABSTRACT FIELD i=%d, names[i]=%s, v=%s'%(i, names[i], v))
            abs_fld_val = v[1]
            if abs_fld_val not in old_obj_dcl.abstract_map:
                raise NameError('Got Abstract class %s but haven\'t found for %d mapping value for it :\n%s'%(obj_dcl.class_name, abs_fld_val, obj_dcl))
            search_name = old_obj_dcl.abstract_map[abs_fld_val]
            #look backward
            if search_name not in obj_dcl.reverse_map:
                raise NameError('Got Abstract class %s but haven\'t mapping value for %s'%(obj_dcl.class_name, search_name))
            abs_fld_val = obj_dcl.reverse_map[search_name]
            v = (obj_dcl.abstract_field, abs_fld_val)
        #check if type is another inner/complex - If so - need to open it in recursive manner:
        v_conv = (names[i], convert_next(old_decl, object_decl, types[i], v[1]))
        val.append(v_conv)

    if obj_dcl.abstract_field is not None and abs_fld_val is None:
        raise NameError('Got Abstract class %s but haven\'t found abstract field %s'%(obj_dcl.class_name ,obj_dcl.abstract_field))
    if obj_dcl.abstract_field is not None and abs_fld_val not in obj_dcl.abstract_map:
        raise NameError('Got Abstract class %s but haven\'t mapping value for %d in object :\n%s'%(obj_dcl.class_name, abs_fld_val, obj_dcl))
    
    if obj_dcl.abstract_field is not None:
        son_type = obj_dcl.abstract_map[abs_fld_val]
        v_s = convert_next(old_decl, object_decl, son_type, obj[len(types):], quiet) #append fields to class:
        val = val + v_s
        additional_name = list(map(lambda x: x[0],v_s))
        if son_type.find('[') >=0 and len(v_s) > 0:
            additional_name = list(map(lambda x: x[0],v_s[0]))
        if len(additional_name) >0 and type(additional_name[0])!= str:
            raise NameError('Bug got additional_name = additional_name=%s'%( ('%s'%v_s)[:200]))
        names = names + additional_name
    if not(quiet):
        print('Write object type %s, value'%(obj_dcl.class_name))
    #print what have being removed from object:
    new_used_fields = set(names)
    
    obj_fields = list(map(lambda x: x[0], filter(lambda x : type(x) == tuple ,obj)))
    obj_fields = obj_fields + list(map( lambda d: d[0],map(lambda x : x[0],filter(lambda x : type(x) == list and len(x) > 0 ,obj))))

    missing_flds = list(filter(lambda x: x not in new_used_fields,obj_fields))
    if len(missing_flds) > 0:
        print('Removed Those Fields from object %s: %s'%(obj_dcl.class_name, '\n'.join(missing_flds)))
    
    return val

def convert_next(old_object_decl, object_decl, typ, val, quiet= None):
    if quiet is None:
        quiet = not(__builtin__.GLOBAL_DEBUG_FLAG)
    supported_primitives = ['int','float','bool','size_t','short','double', 'char', 'long', 'unsigned int', 'unsigned short'] 
    set_pr = set(supported_primitives)
    if not(quiet):
        print('Try Convert type %s, value.type=%s'%(typ, type(val)))
    obj = None
    if (typ in set_pr or typ =='string' or typ =='string_raw'):
        v = val
    elif (typ in object_decl):
        obj_dcl = object_decl[typ]
        v = convert_inner_type(old_object_decl, object_decl, obj_dcl, val, quiet)
    else:
        v = convert_complex(old_object_decl, object_decl, typ,val, quiet)
    obj = v
    return obj

def convert_version(obj ,new_version, quiet = True):
    if obj.object_type not in new_version:
        raise NameError('Object type %s isn\'t supported in requested version'%(obj.object_type))
    #Try "write" all fields if not exist remove from object, if new ones - add default values with warning.
    print('Converting Type %s'%(obj.object_type))
    res = convert_next(obj.object_decl_version, new_version, obj.object_type, obj.obj, quiet)
    obj.obj = res
    obj.object_decl_version = new_version
    print('Done Converting Type %s'%(obj.object_type))
    return res

#wrapper for result serilized object object
class Result_Object:
    def __init__(self, object_decl_version, object_type, obj):
        self.object_decl_version = object_decl_version
        self.object_type = object_type
        self.obj = obj
        self.version = None

    def ls(self):
        return ls_vars(self.obj)

    def ls_types(self):
        full_var_list = get_names_types(self.object_decl_version, self.object_type, self.obj)
        return list(map(lambda x:x[1],full_var_list))

    def get(self, k):
        if type(k) == str:
            return get_var(self.obj, k)
        elif type(k) == list:
            v = self.obj
            for i in range(len(k)):
                v = get_var(v, k[i])
            return v
        else: 
            raise NameError('Wrong format - should by string or list')

    def uget(self, k):
        if type(k) == str:
            v = get_var(self.obj, k)
            full_var_list = get_names_types(self.object_decl_version, self.object_type, self.obj)
            pos = None
            for i in range(len(self.obj)):
                if self.obj[i][0] == k:
                    pos = i
                    break
            if pos is None:
                raise NameError('Bug couldn\'t find pos')
            return Result_Object(self.object_decl_version, full_var_list[pos][1], v)
        elif type(k) == list:
            if len(k) == 0:
                return self
            v = self.uget(k[0])
            return v.uget(k[1:])
        else: 
            raise NameError('Wrong format - should by string or list')

    def search(self, k , v = None):
        return get_vars(self.object_decl_version, self.object_type ,self.obj, k, v)

    def change(self, indexes, func):
        for index in indexes:
            curr_obj = self.obj
            obj_ls = []
            for i in range(len(index)):
                if index[i] != -1 and (i+1 >= len(index) or index[i+1] != -1):
                    curr_obj= curr_obj[index[i]]
                    obj_ls.append([index[i], curr_obj])
                else:
                    if index[i] == -1:
                        raise NameError('Bug')
                    break
            func(curr_obj)
    def get_path(self, path):
        curr_obj = self.obj
        for i in range(len(path)):
            if path[i] != -1 and (i+1 >= len(path) or path[i+1] != -1):
                curr_obj= curr_obj[path[i]]
            else:
                if path[i] == -1:
                    raise NameError('Bug')
                break
        return curr_obj
    
    def uget_path(self, path):
        curr_obj = self.obj
        curr_type = self.object_type
        for i in range(len(path)):
            if path[i] != -1 and (i+1 >= len(path) or path[i+1] != -1):
                is_obj = type(curr_obj) == list
                if is_obj:
                    #print(ls_vars(curr_obj))
                    full_var_list = get_names_types(self.object_decl_version, curr_type, curr_obj)
                    #print('before Type=%s, after=%s'%(curr_type, full_var_list[path[i]][1]), type(curr_obj), type(curr_obj[path[i]]))
                    curr_type = full_var_list[path[i]][1]
                curr_obj= curr_obj[path[i]]
            else:
                if path[i] == -1:
                    raise NameError('Bug')
                break
        if (type(curr_obj) != list):
            raise NameError('path should point to object not tuple')
        return Result_Object(self.object_decl_version, curr_type, curr_obj)
    
    def __repr__(self):
        return '%s : %s'%(self.object_type, self.ls())

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

if __name__ == '__main__':
    set_debug(False)
    input_version_path = os.path.join(os.environ['MR_ROOT'], 'Tools', 'SerializeConvertor', 'versions', 'ver4_2018_10_03')
    output_version_path = os.path.join(os.environ['MR_ROOT'], 'Tools', 'SerializeConvertor', 'versions', 'ver5_2018_10_14')
    object_decl_version4 = read_objects_declarations(input_version_path)
    object_decl_version5 = read_objects_declarations(output_version_path)

    #obj_path = r'W:\Users\Alon\UnitTesting\outputs\cln.bin'
    #obj_path = r'W:\Users\Alon\UnitTesting\outputs\multi_processor.bin'
    #obj_path = r'/server/Work/Users/Alon/UnitTesting/outputs/cln.bin'
    obj_path = r'W:\Users\Alon\ICU\outputs\models\sofa_kidney\config_params\full_model.medmdl'

    obj = deserialize(obj_path, object_decl_version4, 'MedModel', True)
    obj_conv = convert_version(obj, object_decl_version5, True)
    serialize(obj_path+ '.new', obj, True)

    #obj = deserialize(obj_path, object_decl_version4, ('test','RepBasicOutlierCleaner'), True)
    #obj = deserialize(obj_path, object_decl_version4, 'RepBasicOutlierCleaner', True)
    #serialize(obj_path + '.new',object_decl_version4, 'RepBasicOutlierCleaner', obj, 2, True)
    #obj = deserialize(obj_path, object_decl_version4, 'RepMultiProcessor', True)
    #serialize(obj_path + '.new',object_decl_version4, 'RepMultiProcessor', obj, 0, True)
