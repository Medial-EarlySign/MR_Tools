#!/opt/medial/dist/usr/bin/python

from __future__ import print_function
import sys
import numpy as np
import pandas as pd
import med
import argparse

def main():

    if ((FLAGS.inCsv and FLAGS.inBin) or not (FLAGS.inCsv or FLAGS.inBin)):
        raise ValueError("Exactly one of inCsv and inBin should be given")

    features = med.Features()
    if (FLAGS.inCsv):
        features.read_from_csv_mat(FLAGS.inCsv)
    else:
        features.read_from_bin_file(FLAGS.inBin)

    samples = med.Samples()
    samples.import_from_sample_vec(features.samples)

    if (FLAGS.outTxt):
        samples.write_to_file(FLAGS.outTxt)
    if (FLAGS.outBin):
        samples.write_to_bin_file(FLAGS.outBin)


####################################################

if __name__ == "__main__":

    # configuration file
    #
    #  Read command arguments
    parser = argparse.ArgumentParser(description="Get Samples (Bin and/or txt) file from Matrix (Bin or Csv)")
    parser.add_argument("--inCsv", type=str, help="input csv file")
    parser.add_argument("--inBin", type=str, help="input bin file")
    parser.add_argument("--outTxt", type=str, help="output text file")
    parser.add_argument("--outBin", type=str, help="output bin file")

    args = parser.parse_args()

    FLAGS, unparsed = parser.parse_known_args()

    if (unparsed):
        eprint("Left with unparsed arguments:")
        eprint(unparsed)
        exit(0)

    main()



