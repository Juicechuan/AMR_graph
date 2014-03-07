#!/usr/bin/python
# -*- coding:utf-8 -*- 

import sys,codecs
from optparse import OptionParser
from amr_graph import *
from util import trim_concepts

if __name__ == "__main__":
    usage = "Usage: %prog [options] amr_file"
    opt = OptionParser(usage)
    opt.add_option("-v",action="store_true",dest="verbose",
                   default=False,help="verbose option")
    opt.add_option("-s",action="store",type="int",dest ="start",default=0,help="where to start check the sentence")
    
    (options, args) = opt.parse_args()
    if len(args) != 1:
        opt.error("incorrect number of arguments")
    if options.verbose:
        print "formatting file %s..."% args[0]
        
    f = codecs.open(args[0],'r',encoding='utf-8')
    
    start = options.start
    i = start + 1
    for line in f.readlines()[start:]:
        amr_string = line.strip()
        amr_string = trim_concepts(amr_string)
        print str(i)+":" + amr_string
        amr_ch = AMR.parse_string(amr_string)
        print amr_ch.to_amr_string()
        i += 1
        raw_input("Presss ENTER to continue")
        
    
