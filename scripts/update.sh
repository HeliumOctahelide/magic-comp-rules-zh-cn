#!/bin/bash
date=$1
python plain2json.py $date
python json2md.py $date
python json2doku.py $date