#!/bin/python
from convertor import read_objects_declarations, deserialize, serialize, convert_version, set_debug
from convertor import Result_Object, ls_vars, get_var, get_vars
from convertor import bcolors
import argparse, code, os

parser = argparse.ArgumentParser(description='Serialization Program')
parser.add_argument('--input', help = 'Path to input', required = True)
parser.add_argument('--type','--object_type', help = 'Object Class Name to Serialize In C. For Example MedModel', default = 'MedModel')
parser.add_argument('--version', help = 'Path to version folder', required = True)
#add arguments for ouput version - another version folder, change actions?
parser.add_argument('--out_ver_num', help = 'output version number', required = True, type= int)
parser.add_argument('--output_version', help = 'Path to version folder of output', required = True)
parser.add_argument('--output', help = 'Path to output', required = True)
parser.add_argument('--debug', help = 'active Debug - 0 - none, 1-little, 2-full', type=int ,default = 0)
parser.add_argument('--skip_convert', help = 'If 1 will not do convert', type=int ,default = 0)
parser.add_argument('--edit', help = 'edit flag - 0 - none, 1-use code before writing object', type=int ,default = 0)

args = parser.parse_args()

set_debug(args.debug>1)
    
print('Input = %s, of Type=%s, Version_path=%s'%(args.input, args.type, args.version))
input_obj_decl = read_objects_declarations(args.version)
output_obj_decl = read_objects_declarations(args.output_version)
obj = deserialize(args.input, input_obj_decl, args.type, not(args.debug > 0))
#Convert
if args.skip_convert == 0:
    obj_conv = convert_version(obj, output_obj_decl, not(args.debug > 0))
obj.version = args.out_ver_num
#edit
if args.edit>0:
    print(bcolors.WARNING + 'use "obj" to edit the new object.' + bcolors.ENDC)
    print(bcolors.WARNING + 'use "input_obj_decl" for input version dictionary' + bcolors.ENDC)
    print(bcolors.WARNING + 'use "output_obj_decl" is for output version dictionary' + bcolors.ENDC)
    if os.name == 'nt':
        print(bcolors.OKBLUE + 'Press <CTRL-Z> + enter when done.' + bcolors.ENDC)
    else:
        print(bcolors.OKBLUE + 'Press <CTRL-D> when done.' + bcolors.ENDC)
    code.interact(local=locals())
#Serialize
serialize(args.output, obj, not(args.debug > 0))