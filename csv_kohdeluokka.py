from helpers import kohdeluokka_dict
import csv
import os, sys, getopt
import pandas as pd
import json

def csv_write_kohdeluokka(kohdeluokka_nimi):
    content, url = kohdeluokka_dict(kohdeluokka_nimi)
    filename = kohdeluokka_nimi.split("_")[2] + ".csv"
    data = pd.json_normalize(content)
    data = data.reindex(sorted(data.columns), axis=1)
    data.to_csv(filename, encoding = 'utf-8-sig', sep = ";")
    return filename
   