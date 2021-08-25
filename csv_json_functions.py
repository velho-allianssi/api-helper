from application import kohdeluokka_dict
from copy import deepcopy
import csv
import os, sys, getopt
import pandas as pd
import json

# pandas group by googleta

def csv_write_kohdeluokka(kohdeluokka_nimi, token):
    content, url = kohdeluokka_dict(kohdeluokka_nimi, token)
    filename = kohdeluokka_nimi.split("_")[2] + ".csv"
    data = pd.json_normalize(content)
    #data = json_to_dataframe(content)
    data = data.reindex(sorted(data.columns), axis=1)
    data.to_csv(filename, encoding = 'utf-8-sig', sep = ";", index=False)
    return filename
   

def convert_csv_to_json(file):
    csv_content = pd.read_csv(file, sep=';', encoding="utf-8-sig", dtype='unicode')
    data = csv_content.where(pd.notnull(csv_content), None)
    reverse_normalization = df_to_formatted_json(data)
    return reverse_normalization


# https://stackoverflow.com/questions/54776916/inverse-of-pandas-json-normalize
def df_to_formatted_json(df, sep="."):
    """
    The opposite of json_normalize
    """
    result = []
    for idx, row in df.iterrows():
        parsed_row = {}
        for col_label,v in row.items():
            keys = col_label.split(".")

            current = parsed_row
            for i, k in enumerate(keys):
                if i==len(keys)-1:
                    current[k] = v
                else:
                    if k not in current.keys():
                        current[k] = {}
                    current = current[k]

        # save
        result.append(parsed_row)
    return result

def to_formatted_json(df, sep="."):
    result = []
    for _, row in df.iterrows():
        parsed_row = {}
        for idx, val in row.iteritems():
            if val == val:
                keys = idx.split(sep)
                parsed_row = set_for_keys(parsed_row, keys, val)

        result.append(parsed_row)
    return result

def set_for_keys(my_dict, key_arr, val):
    """
    Set val at path in my_dict defined by the string (or serializable object) array key_arr
    """
    current = my_dict
    for i in range(len(key_arr)):
        key = key_arr[i]
        if key not in current:
            if i==len(key_arr)-1:
                current[key] = val
            else:
                current[key] = {}
        else:
            if type(current[key]) is not dict:
                print("Given dictionary is not compatible with key structure requested")
                raise ValueError("Dictionary key already occupied")

        current = current[key]

#---------------------

def cross_join(left, right):
    new_rows = [] if right else left
    for left_row in left:
        for right_row in right:
            temp_row = deepcopy(left_row)
            for key, value in right_row.items():
                temp_row[key] = value
            new_rows.append(deepcopy(temp_row))
    return new_rows


def flatten_list(data):
    for elem in data:
        if isinstance(elem, list):
            yield from flatten_list(elem)
        else:
            yield elem


def json_to_dataframe(data_in):
    def flatten_json(data, prev_heading=''):
        if isinstance(data, dict):
            rows = [{}]
            for key, value in data.items():
                rows = cross_join(rows, flatten_json(value, prev_heading + '.' + key))
        elif isinstance(data, list):
            rows = []
            for i in range(len(data)):
                [rows.append(elem) for elem in flatten_list(flatten_json(data[i], prev_heading))]
        else:
            rows = [{prev_heading[1:]: data}]
        return rows

    return pd.DataFrame(flatten_json(data_in))