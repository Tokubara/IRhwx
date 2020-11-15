#!/usr/bin/env bash
tr -d ' ' < Sogou0012.txt > tmp_.txt
sed -i '.txt' 's_<N>_0_' tmp_.txt
/Users/quebec/Downloads/THULAC-master/thulac -model_dir /Users/quebec/Downloads/THULAC-master/models  -deli '/' -input tmp_.txt -output tmp_output.txt
/usr/local/bin/python3 build_index.py
