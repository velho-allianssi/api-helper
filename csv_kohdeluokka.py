from helpers import kohdeluokka_dict
import csv
import os, sys, getopt
import pandas as pd
import json

def csv_write_kohdeluokka(kohdeluokka_nimi):
    content, url = kohdeluokka_dict(kohdeluokka_nimi)
    filename = kohdeluokka_nimi.split("_")[2] + ".csv"
    #jsonToCsv(json.load(content), filename)
    pass

'''
def jsonToCsv(json_data, outputfp):
    # Read data                    
    with open(inputfp, encoding='utf-8') as f:                                                                                                                                                                                                                                                                                                                                         
        # First line different ...
        f.readline()
        # Read JSON
        data = pd.read_json(f, lines=True)
        # Normalize
        data = pd.io.json.json_normalize(data.to_dict(orient="records"))
        # Sort columns alphabetically
        data = data.reindex(sorted(data.columns), axis=1)
        
    # Save as csv                                                                                                                                                                                                                                                                                                                                                           
    # If file already exists, don't copy it again:     
                                                                                                                                                                                                                                                                                                                     
    if os.path.isfile(outputfp) == True:
        print(outputfp, "already exists.")
        # If file doesn't already exist, create it                                                                                                                                                                                                                                                                                                                          
    else:
        # Save to csv                                                                                                                                                                                                                                                                                                                             
        data.to_csv(outputfp, encoding = 'utf-8-sig', sep = ";")
        
    return True
'''