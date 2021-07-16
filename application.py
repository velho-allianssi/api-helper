from flask import Flask, render_template, session, request
from flask.helpers import send_file
import requests, json, ndjson
from helpers import get_token, group_by_tie, kohdeluokka_dict, meta_tiedot, api_call_data_kohdeluokka, finder, grouped_by_tie, split_at_parts
from csv_urakat import urakat_csv_encoded
from csv_homogenisoitu import CsvLinearReference
from collections import OrderedDict
from csv_kohdeluokka import csv_write_kohdeluokka


# targetit -> kohdeluokaksi

app = Flask(__name__)

dataset = [ ]

@app.route('/')
def index():
    return render_template('index.html', data="API Helper")


# Hakee kohdeluokkien nimet metatietopalvelusta
@app.route('/meta')
def meta(): 
    token_url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/nimiavaruudet"
    auth = 'Bearer ' + str(get_token())
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
    auth = 'Bearer ' + str(get_token())

    data = '[ "' + class_name + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)

    schemas = api_call_response.json()["components"]["schemas"]
    schema_list = list(schemas)
    filtered_list = []
    for s in schema_list: 
        parts = s.split("_")
        if parts[1] == class_name and "muokkaus" not in parts[2] and "luonti" not in parts[2] and "nimikkeisto" not in parts[0]: 
            filtered_list.append(s)

    # Haetaan nimikkeistot
    # Kokeile muuttaa for loop --> map
    nimikkeistot_dict = {}
    nimikkeistot = api_call_response.json()["info"]["x-velho-nimikkeistot"]
    for key, value in nimikkeistot.items():
        otsikot = value["nimikkeistoversiot"]["1"]
        nimikkeistot_dict[key] = []
        for nimike, otsikko in otsikot.items():
            nimikkeistot_dict[key].append({nimike: otsikko["otsikko"]})

    return render_template('details.html', data = sorted(filtered_list), nimikkeistot=OrderedDict(sorted(nimikkeistot_dict.items())), class_name=class_name)

# Hakee latauspalvelusta tietyn kohdeluokan objectit
@app.route('/<class_name>/<target>', methods = ['GET', 'POST'])
def get_class(class_name, target):
    parts = target.split("_")
    filters = {}
    if parts[0] == "kohdeluokka": 
        content, path = kohdeluokka_dict(target)
        if request.method == 'POST':
            tie = request.form['road']
            grouped = group_by_tie(content)
            if int(tie) in grouped: 
                content = grouped[int(tie)]
                aosa = request.form['aosa']
                losa = request.form['losa']

                if aosa and losa:
                    aosa = int(aosa)
                    losa = int(losa)
                    finds = tieosa_haku(content, aosa, losa)
                    content = finds

                    filters = {
                        'tie'  : tie,
                        'aosa' : aosa,
                        'losa' : losa
                    }

        if type(content) is str: 
            return content
        else: 
            as_dict = {}
            for d in content:
                as_dict[d["oid"]] = d
            return render_template('target.html', data=as_dict, target=target, path=path, filters=filters)

    else:
        data = meta_tiedot(class_name)
        try: 
            return render_template('target.html', data=data[target], target=target, filters=filters)
        except: 
            return render_template('target.html', data={"Error": "No data with this keyword"}, target=target, filters=filters)

# Etsii kohdeluokan objectit joiden osat ovat tietyllä välillä
# Kutsuttaessa oletetaan että tieosat ovat kohdeluokan objectit tietyllä tiellä (yleensä siis group_by_tie(__jokin tie__))
def tieosa_haku(tieosat, aosa, losa):
    results = []
    if not tieosat: 
                return None
    for tieosa in tieosat: 
            if "sijainti" in tieosa: 
                    sijainti = tieosa["sijainti"]
                    if sijainti["osa"] >= aosa and sijainti["osa"] <= losa:
                            results.append(tieosa)
            elif "sijainnit" in tieosa: 
                    for sijainti in tieosa["sijainnit"]:
                            alkusijainti  = sijainti["alkusijainti"]
                            loppusijainti = sijainti["loppusijainti"]
                            if alkusijainti["osa"] >= aosa and loppusijainti["osa"] <= losa:
                                results.append(tieosa)

            elif "alkusijainti" in tieosa and "loppusijainti" in tieosa: 
                    alkusijainti  = tieosa["alkusijainti"]
                    loppusijainti = tieosa["loppusijainti"]
                    if alkusijainti["osa"] >= aosa and loppusijainti["osa"] <= losa:
                                results.append(tieosa)

            elif "tie" in tieosa: 
                    if tieosa["osa"] >= aosa and tieosa["osa"] <= losa:
                            results.append(tieosa)
    return results

# Lataa latauspalvelusta tietyn kohdeluokan ndjsonin
@app.route('/download/<kohdeluokka>')
def download_ndjson(kohdeluokka):
    api_response, url = api_call_data_kohdeluokka(kohdeluokka, None)
    content = api_response.json(cls=ndjson.Decoder)
    filename = kohdeluokka.split("_")[2] + ".json"
    #open(filename, 'wb').write(content)
    with open(filename, 'w') as f:
        json.dump(content, f)

    return send_file(filename, as_attachment=True)

@app.route('/lahetykset')
def lahetykset():
    auth = 'Bearer ' + str(get_token())
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tunnisteet" 
    response = requests.get(url, headers=headers)
    
    lahetys_lista = response.json()
    as_dict = {}
    for lahetys in lahetys_lista: 
        cur_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + lahetys
        response = requests.get(cur_url, headers=headers)
        as_dict[lahetys] = response.json()
    
    return render_template('upload_check.html', data=as_dict)

@app.route('/check_status/<tunniste>')
def check_status(tunniste):
    auth = 'Bearer ' + str(get_token())
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + tunniste
    response = requests.get(url, headers=headers)
    return render_template('upload_check.html', data=response.json(), lahetystunniste=tunniste)

@app.route('/put', methods = ['POST'])
def curl_put():
    if request.method == 'POST':
        target = request.form['target'] 
        parts = target.split("_") 

        url     = 'https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/laheta'
        auth    = 'Bearer ' + str(get_token())
        headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        data    = {"kohdeluokka": parts[1] + "/" + parts[2]}

        response = requests.post(url, headers=headers, data=json.dumps(data))
        print(response)

        response_json = response.json()
        upload_url = response_json["url"]
        print(upload_url)
        files = request.files['file']
        
        upload = requests.put(upload_url, files=files, verify=False)
        print("here")
        print(upload)
        #status_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + response_json["lahetystunniste"]
        #return render_template("upload_check.html", data=requests.get(status_url, headers=headers).json(), lahetystunniste=response_json["lahetystunniste"])

        lahetykset()

@app.route('/csv/tieosat')
def tieosat_csv():
    obj = CsvLinearReference()
    filename = obj.write_and_run()
    return send_file(filename, as_attachment=True)

@app.route('/<class_name>/csv')
def kohdeluokka_csv(class_name):
    file = csv_write_kohdeluokka(class_name)
    return send_file(file, as_attachment=True)

@app.route('/nappi')
def nappi():
    auth_token = get_token()
    kohdeluokka = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_viherhoitoluokka", auth_token)
    tieosat = grouped_by_tie("kohdeluokka_sijainti_tieosa", auth_token)
    tieosat = tieosat[1]
    kohdeluokka = kohdeluokka[1]
    result = []
    for x in kohdeluokka:
        result = split_at_parts(tieosat, x)
        if result:
            return render_template('testi.html', data=result)
    return render_template('testi.html', data=result)

