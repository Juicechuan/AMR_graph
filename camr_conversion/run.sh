#!/bin/sh


#SRC=/nfs/guest/yaqiny/Dropbox/Code/OntonotesUtil/ontonotes-db-tool-v0.999b/src
SRC=/home/j/llc/cwang24/R_D/AMR/camr_conversion

#ONTONOTES=/nfs/nlg/semmt/data/ontonotes/ontonotes-release-4.0/data/files/data
ONTONOTES=~clp/chinese/corpora/ontonotes-release-4.0/data
SAMPLE_DATA=/home/j/llc/cwang24/R_D/AMR/onto-100-sample-data/data

#MYCONFIG=/nfs/guest/yaqiny/Dropbox/Code/OntonotesUtil/ontonotes-db-tool-v0.999b/myconfig
MYCONFIG=/home/j/llc/cwang24/R_D/AMR/camr_conversion/myconfig

#HEADRULES=/nfs/guest/yaqiny/Dropbox/Code/OntonotesUtil/ontonotes-db-tool-v0.999b/data/headrules.txt
HEADRULES=/home/j/llc/cwang24/R_D/AMR/camr_conversion/chn_headrules.txt
HEADTREES=/home/j/llc/cwang24/R_D/AMR/camr_conversion/e2c_0003.parse.head

CORPORA="parse coref sense name parallel prop speaker"
#GENRE="english-nw-wsj"
GENRE="chinese-wb-e2c"
PREFIX="00"
SUFFIX="00 01"
GRAN=source


python $SRC/camr_conversion.py $HEADTREES -c $MYCONFIG corpus.data_in=$SAMPLE_DATA corpus.load=$GENRE corpus.prefix=$PREFIX corpus.suffix="03" corpus.banks="parse prop name coref"
