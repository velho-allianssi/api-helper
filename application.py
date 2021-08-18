from typing import Dict
from flask import Flask, render_template, session, request, redirect, url_for, flash
from flask.helpers import send_file
import requests, json, ndjson
from helpers import get_token, group_by_tie, kohdeluokka_dict, meta_tiedot, api_call_data_kohdeluokka, login_token
from csv_homogenisoitu import CsvLinearReference
from collections import OrderedDict
from csv_kohdeluokka import csv_write_kohdeluokka, convert_csv_to_json


# targetit -> kohdeluokaksi

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
dataset = [ ]

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        api_id = request.form['id']
        api_secret = request.form['secret']
        token = login_token(api_id, api_secret)
        if token:
            # Tärkeä
            session['token'] = token      
            return render_template('index.html')
        else:
            return render_template('login.html', message="Invalid id or secret")
    else: 
        return render_template('login.html')



@app.route('/')
def index():
    return render_template('index.html')

# Hakee kohdeluokkien nimet metatietopalvelusta
@app.route('/meta')
def meta(): 
    print(request.cookies.get('id'))
    token_url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/nimiavaruudet"
    #auth = 'Bearer ' + str(get_token(request.cookies.get('id'), request.cookies.get('secret')))
    auth = 'Bearer ' + str(get_token())
    data = {'accept': 'application/json'}
    api_call_headers = {'Authorization': auth}
    api_call_response = requests.get(token_url, headers=api_call_headers, data=data)
    try: 
        return render_template('nimiavaruudet.html', data=sorted(api_call_response.json()))
    except: 
        return api_call_response.text

# Apufunktio metatietojen hakemiseen, sillä niitä käytetään enemmän kuin yhdessä funktiossa
def kohdeluokka_metatiedot_schemat(auth, kohdeluokka):
    url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
    data = '[ "' + kohdeluokka + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)

    schemas = api_call_response.json()["components"]["schemas"]
    schema_list = list(schemas)
    filtered_list = []
    for s in schema_list: 
        parts = s.split("_")
        if parts[1] == kohdeluokka and "muokkaus" not in parts[2] and "luonti" not in parts[2] and "kohdeluokka" in parts[0] and "1" not in parts[2]: 
            filtered_list.append(s)

    return filtered_list

# Hakee kohdeluokan jsonin metatietopalvelusta
# Hakee jsonista schemat
@app.route('/meta/<kohdeluokka>')
def kohdeluokka_metatiedot(kohdeluokka):
    url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
    auth = 'Bearer ' + str(get_token())

    data = '[ "' + kohdeluokka + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)

    schemas = api_call_response.json()["components"]["schemas"]
    schema_list = list(schemas)
    filtered_list = []
    for s in schema_list: 
        parts = s.split("_")
        if parts[1] == kohdeluokka and "muokkaus" not in parts[2] and "luonti" not in parts[2] and "kohdeluokka" in parts[0] and parts[2][-1] != '1': 
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

    return render_template('kohdeluokka_metatiedot.html', data = sorted(filtered_list), nimikkeistot=OrderedDict(sorted(nimikkeistot_dict.items())), class_name=kohdeluokka)

# Hakee latauspalvelusta tietyn kohdeluokan objectit
@app.route('/<class_name>/<target>', methods = ['GET', 'POST'])
def kohdeluokka_latauspalvelu(class_name, target):
    kohdeluokka = class_name
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
            return render_template('kohdeluokka_latauspalvelu.html', data=as_dict, target=target, path=path, filters=filters)

    else:
        data = meta_tiedot(kohdeluokka)
        try: 
            return render_template('kohdeluokka_latauspalvelu.html', data=data[target], target=target, filters=filters)
        except: 
            return render_template('kohdeluokka_latauspalvelu.html', data={"Error": "No data with this keyword"}, target=target, filters=filters)

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


# Lataa metatieto palvelusta tietyn kohdeluokan metatiedot
@app.route('/download/meta/<kohdeluokka>')
def download_meta_json(kohdeluokka):
    url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
    auth = 'Bearer ' + str(get_token())

    data = '[ "' + kohdeluokka + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)
    content = api_call_response.json(cls=ndjson.Decoder)
    filename = filename = "meta_" + kohdeluokka + ".json"
    with open(filename, 'w') as f:
        json.dump(content, f)

    return send_file(filename, as_attachment=True)

@app.route('/laheta')
def laheta():
    auth = 'Bearer ' + str(get_token())
    vaihtoehdot = {}
    token_url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/nimiavaruudet"
    data = {'accept': 'application/json'}
    api_call_headers = {'Authorization': auth}
    api_call_response = requests.get(token_url, headers=api_call_headers, data=data)
    nimiavaruudet = api_call_response.json()
    for nimi in nimiavaruudet: 
        kohdeluokat = kohdeluokka_metatiedot_schemat(auth, nimi)
        vaihtoehdot[nimi] = kohdeluokat
    vaihtoehdot.popitem()
    return render_template('laheta.html', data=vaihtoehdot)


# Hakee kaikki meneillään olevat lähetykset
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
    
    return render_template('upload_check.html', data=as_dict, lahetystunniste=None)

# Tarkistaa tietyn lähetyksen statuksen
@app.route('/check_status/<tunniste>')
def check_status(tunniste):
    auth = 'Bearer ' + str(get_token())
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + tunniste
    response = requests.get(url, headers=headers)
    return render_template('upload_check.html', data=response.json(), lahetystunniste=tunniste)

# Lähettää tiedoston lähetyspalveluun
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
        response_json = response.json()
        upload_url = response_json["url"]

        file = request.files['file']
        #if filename.split('.')[1] == 'csv':
        #   converted = convert_csv_to_json(file)
        upload = requests.put(upload_url, files={'file': file}, verify=False)

        status_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + response_json["lahetystunniste"]
        return render_template("upload_check.html", data=requests.get(status_url, headers=headers).json(), lahetystunniste=response_json["lahetystunniste"])

        #return redirect(url_for('lahetykset'))

# Yhdistelee useiden kohdeluokkien tietoja yhdeksi csv:ksi
@app.route('/csv/tieosat', methods = ['POST'])
def tieosat_csv():
    if request.method == 'POST':
        options_json = request.form['selected_options']
        options = json.loads(options_json)
        options.reverse()
        obj = CsvLinearReference(options)
        filename = obj.write_and_run()
        return send_file(filename, as_attachment=True)

@app.route('/<kohdeluokka>/csv')
def kohdeluokka_csv(kohdeluokka):
    file = csv_write_kohdeluokka(kohdeluokka)
    return send_file(file, as_attachment=True)

@app.route("/csv")
def csv_options():
    options = {
        'vluonne'       : 'Väylän-luonne',
        'toiml'         : 'Toiminnallinen-luokka',
        'kplk'          : 'Talvihoitoluokka',
        'viherlk'       : 'Viherhoitoluokka',
        'kaistapa'      : 'Kaistapäällyste',
        'pyplk'         : 'Päällysteen-korjausluokka',
        'soratielk'     : 'Soratieluokka'
    }
    return render_template('csv.html', options=options)


@app.route('/convert', methods = ['POST'])
def csv_to_json():
    if request.method == 'POST':
        files = request.files['file']
        filename = files.filename.split(".")[0] + ".json"
        print(filename.split(".")[0])
        try: 
            converted = convert_csv_to_json(files)

            with open(filename, 'w') as f:
                json.dump(converted, f)
            return send_file(filename, as_attachment=True, attachment_filename=filename)
        except: 
            return "Ongelma muunnoksessa"


@app.route('/info')
def info():
    return render_template('info.html')