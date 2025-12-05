#!/usr/bin/env python
import zlib
import ctypes
import argparse

parser = argparse.ArgumentParser(description = "test crc32")
parser.add_argument("--input", default='/earlysign/AlgoMarkers/LGI/LGI-Flag-3.1.model',help="input file path")
parser.add_argument("--expected_in_c", type=int, default=0,help="if we have result")

args = parser.parse_args()
FILE_PATH=args.input

fr=open(FILE_PATH, 'rb')
binary=fr.read()
fr.close()
result = zlib.crc32(binary)

expected_in_c=ctypes.c_int(result).value
if args.expected_in_c != 0:
	if expected_in_c == args.expected_in_c:
		print(f'TESTED {FILE_PATH} SUCCESS - crc expected: {expected_in_c}')
	else:
		print(f'TESTED {FILE_PATH} Failed - crc expected: {args.expected_in_c}, got {expected_in_c}')
else:
	print(f'TESTED {FILE_PATH} crc expected: {expected_in_c}')
