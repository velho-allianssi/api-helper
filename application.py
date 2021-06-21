from flask import Flask, render_template, session
import requests, json, ndjson
from helpers import token, kohdeluokka_dict, meta_tiedot
from csv_functions import tieosat_csv_encoded
import csv
import collections


app = Flask(__name__)

dataset = [ ]

@app.route('/')
def index():
    return render_template('index.html', data="API Helper")


# Hakee kohdeluokkien nimet metatietopalvelusta
@app.route('/meta')
def meta(): 
    token_url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/nimiavaruudet"
    auth = 'Bearer ' + str(token())
    data = {'accept': 'application/json'}
    api_call_headers = {'Authorization': auth}
    api_call_response = requests.get(token_url, headers=api_call_headers, data=data)
    try: 
        return render_template('classes.html', data=sorted(api_call_response.json()))
    except: 
        return api_call_response.text

# Hakee kohdeluokan jsonin metatietopalvelusta
# Hakee jsonista schemat
@app.route('/meta/<class_name>')
def get_specs(class_name):

    url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
    auth = 'Bearer ' + str(token())

    data = '[ "' + class_name + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)
    vals = api_call_response.json().values()
    to_list = list(vals)
    schemas = to_list[1]
    s_vals = schemas["schemas"]
    s_list = list(s_vals)
    filtered_list = []
    for s in s_list: 
        parts = s.split("_")
        if parts[1] == class_name and "muokkaus" not in parts[2] and "luonti" not in parts[2]: 
            filtered_list.append(s)

    return render_template('details.html', data = sorted(filtered_list), class_name=class_name)

# Hakee latauspalvelusta tietyn kohdeluokan objectit
@app.route('/<class_name>/<target>')
def get_class(class_name, target):
    parts = target.split("_")
    if parts[0] == "kohdeluokka": 
        content, path = kohdeluokka_dict(target)
        if type(content) is str: 
            return content
        else: 
            as_dict = {}
            for d in content:
                as_dict[d["oid"]] = d
            return render_template('target.html', data=as_dict, target=target, path=path)

    else:
        data = meta_tiedot(class_name)
        try: 
            return render_template('target.html', data=data[target], target=target)
        except: 
            return render_template('target.html', data={"Error": "No data with this keyword"}, target=target)

# Lataa latauspalvelusta tietyn kohdeluokan ndjsonin
@app.route('/download/<target>')
def download_ndjson(target):
    parts = target.split("_") 
    url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + ".json" 
    auth = 'Bearer ' + str(token())
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.get(url, headers=api_call_headers)

    open(parts[2] + ".json", 'wb').write(api_call_response.content)

    return '', 204

@app.route('/lahetykset')
def lahetykset():
    auth = 'Bearer ' + str(token())
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tunnisteet" 
    response = requests.get(url, headers=headers)
    '''
    lahetys_lista = response.json()
    as_dict = {}
    for lahetys in lahetys_lista: 
        cur_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + lahetys
        response = requests.get(cur_url, headers=headers)
        as_dict[lahetys] = response.json()
    '''
    return render_template('lahtykset.html', data=response.json())

@app.route('/check_status/<tunniste>')
def check_status(tunniste):
    auth = 'Bearer ' + str(token())
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + tunniste
    response = requests.get(url, headers=headers)
    return render_template('upload_check.html', data=response.json(), target=tunniste)

@app.route('/put/<target>')
def curl_put(target): 
    parts = target.split("_") 
    url = 'https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/laheta'
    auth = 'Bearer ' + str(token())
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    data = {"kohdeluokka": parts[1] + "/" + parts[2]}
    response = requests.post('https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/laheta', headers=headers, data=json.dumps(data))
    response_json = response.json()
    upload_url = response_json["url"]

    payload, request_url = kohdeluokka_dict(target)
    files = {'file': open('testi_toimenpide.json', 'rb')}

    requests.put(url, files=files, verify=False)
    status_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + response_json["lahetystunniste"]
    
    return render_template("upload_check.html", data=requests.get(status_url, headers=headers).json(), target=response_json["lahetystunniste"])
 
@app.route('/class/<target>/<oid>')
def get_oid(target, oid):
    pass
'''
@app.route('/csv/tatu/<target>')
def tatu_csv(target):
    to_tatu_csv(target)

    return "success"
@app.route('/csv/full/<target>')
def full_csv(target): 

    urakat_csv(target)
    return "success"
'''
@app.route('/csv/tieosat')
def tieosat_csv():
    tieosat_csv_encoded()
    return "success"