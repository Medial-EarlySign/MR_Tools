from __future__ import print_function
import sys, os, time
import pandas as pd
from pandas.parser import CParserError
import binascii
import sys, select
from sklearn.externals import joblib
from StringIO import StringIO
 
def print_crc32(fname, quiet=False):
	if not quiet:
		eprint('reading', fname, time.ctime(os.path.getmtime(fname)) , "crc32:", end = "")
	buf = open(fname,'rb').read()
	buf = (binascii.crc32(buf) & 0xFFFFFFFF)
	if not quiet:
		eprint('%08X' % buf)

def read_file(fname, **kwargs):
	attempts = 0
	quiet = "quiet" in kwargs and kwargs["quiet"]
	if "limit_records" in kwargs:
		limit_records = kwargs["limit_records"]
	else:
		limit_records = -1
	for word in ["quiet", "limit_records"]:
		if word in kwargs:
			del kwargs[word]
	while True:
		try:
			if limit_records != -1:
				with open(fname) as myfile:
					head = []
					try:
						for x in xrange(limit_records):
							head.append(next(myfile))
					except StopIteration as e:
						eprint("file contains only {0} records".format(len(head)))
					head = StringIO("\n".join(head))
					r = pd.read_csv(head, **kwargs)
			else:
				print_crc32(fname, quiet)
				r = pd.read_csv(fname, **kwargs)
			break
		except CParserError as e:
			if attempts >= 3:
				raise e
			eprint(e, "attempts", attempts)
			attempts += 1
	if not quiet:
		eprint('read', r.shape, 'rows from', fname)
	return r

def joblib_load(fname, **kwargs):
	attempts = 0
	quiet = "quiet" in kwargs and kwargs["quiet"]
	if "quiet" in kwargs:
		del kwargs["quiet"]
	while True:
		try:
			print_crc32(fname, quiet)
			r = joblib.load(fname, **kwargs)
			break
		except CParserError as e:
			if attempts >= 3:
				raise e
			eprint(e, "attempts", attempts)
			attempts += 1
	return r
	
def eprint(*args, **kwargs):
	print(*args, file=sys.stderr, **kwargs)

def write_for_sure(df, out_fname, **kwargs):
	eprint('writing ', df.shape, 'into', out_fname)
	if df.shape[0] == 0:
		raise Exception('refusing to write 0 records into ' + out_fname)
	wrote_it = False
	attempts = 0
	while (not wrote_it):
		try:
			attempts += 1
			df.to_csv(out_fname, **kwargs)
			wrote_it = True
		except IOError as e:
			if attempts >= 3:
				raise e
			eprint("failed writing", e)
			eprint("try again?")
			i, o, e = select.select( [sys.stdin], [], [], 10 )
			
