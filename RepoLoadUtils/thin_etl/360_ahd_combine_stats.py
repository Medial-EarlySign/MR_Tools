from __future__ import print_function
from collections import defaultdict
import sys

def clean_and_strip(x):
    return x.strip()

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

stats = {"processed": 0}

counts = dict()
counts_non_zero = dict()

fp = open('temp.all', 'r')
lines = fp.readlines()
fp.close()

#sk = 0
for l in lines:
    ahdcode, count, count_non_zero = map(clean_and_strip, l.split('\t'))
    #if ahdcode == "ahdcode": #header
    #    sk = sk + 1
    #    continue
    if ahdcode is None or count is None or count_non_zero is None:
        raise NameError('parse error')
    stats["processed"] += 1
    if counts.get(ahdcode) is None:
        counts[ahdcode] = 0
    if counts_non_zero.get(ahdcode) is None:
        counts_non_zero[ahdcode] = 0
    counts[ahdcode] = counts[ahdcode] + int(count)
    counts_non_zero[ahdcode] =counts_non_zero[ahdcode] + int(count_non_zero)
        
eprint("processed", stats["processed"], "records")
#eprint("skipped %d"%sk)
        
for k, v in counts.items():
    print("\t".join([k, str(v), str(counts_non_zero[k])]))
