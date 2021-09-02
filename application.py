from typing import Dict
from functools import wraps
from flask import Flask, render_template, session, request, redirect, url_for
from flask.helpers import send_file
import requests, json, ndjson
from helpers import group_by_tie, meta_tiedot, api_call_data_kohdeluokka, login_token
from csv_homogenisoitu import CsvLinearReference
from collections import OrderedDict
from csv_json_functions import csv_write_kohdeluokka, convert_csv_to_json
import datetime, time
import pytz

app = Flask(__name__)
# vaihtuu
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'
dataset = [ ]
utc = pytz.UTC


def kohdeluokka_dict(kohdeluokka, token):
        api_call_response, url = api_call_data_kohdeluokka(kohdeluokka, token)
        if api_call_response.status_code == 401:
            session.pop('token')
            return redirect(url_for('login', message="Token expired"))
        
        #purkaa ndjsonin python listaksi
        #kutsuu json.loads(f.read()) mikä dumppaa koko jsonin muistiin 
        #Ehkä ijson parempi? 
        
        #data = api_call_response
        #jsonobjs = ijson.items(api_call_response.content, 'item')
        #jsons = (o for o in jsonobjs)


        try: 
            content = api_call_response.json(cls=ndjson.Decoder)
            #poistaa latauspalvelun ensimmäisen meta rivin
            content = content[1:]
        except:
            #jos api ei palauta ndjson tiedostoa, näytetään pyynnön mukana tullut teksti
            content = api_call_response.text

        return content, url 

def token_required(f): 
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try: 
            token = session['token']
            if utc.localize(datetime.datetime.now()) > session['max-length']:
                session.clear()
                return redirect(url_for('login', message="Token expired"))
        except: 
            return redirect(url_for('login', message="Valid token is required, please enter api information"))
        return f(*args, **kwargs)
    return decorated_function
        
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        api_id = request.form['id']
        api_secret = request.form['secret']
        token = login_token(api_id, api_secret)
        if token:
            # Tärkeä
            session.permanent = True
            app.permanent_session_lifetime = datetime.timedelta(hours=1)
            session['token'] = token
            session['max-length'] = utc.localize(datetime.datetime.now() + datetime.timedelta(hours=1))
            return render_template('index.html')
        else:
            return render_template('login.html', message="Invalid id or secret")
    else:
        try: 
            return render_template('login.html', message=request.args .get('message'))
        except:
            return render_template('login.html')



@app.route('/')
@token_required
def index():
    return render_template('index.html')

# Hakee kohdeluokkien nimet metatietopalvelusta
@app.route('/meta')
@token_required
def meta(): 
    token_url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/nimiavaruudet"
    try: 
        auth = 'Bearer ' + str(session['token'])
    except: 
        return redirect(url_for('login', message="Invalid login"))
    data = {'accept': 'application/json'}
    api_call_headers = {'Authorization': auth}
    api_call_response = requests.get(token_url, headers=api_call_headers, data=data)
    # Vaikka Tokenin pitäisi expirata itsekseen, tarkistetaan response_code varmuuden vuoksi
    if api_call_response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
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
    if api_call_response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
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
@token_required
def kohdeluokka_metatiedot(kohdeluokka):
    url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
    try: 
        auth = 'Bearer ' + str(session['token'])
    except: 
        return redirect(url_for('login', message="Your token has expired"))

    data = '[ "' + kohdeluokka + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)
    if api_call_response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
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
@token_required
def kohdeluokka_latauspalvelu(class_name, target):
    kohdeluokka = target
    parts = kohdeluokka.split("_") 
    try: 
        auth = 'Bearer ' + str(session['token'])
        token = session['token']
    except: 
        return redirect(url_for('login', message="Your token has expired"))

    # Osa kohdeluokista jakautuu useaan tiedostoon, koska yhtenä tiedostona niistä tulisi liian suuria. 
    # Tällöin kohdeluokan nimi toimii hakemistona, ja data on (yleensä tieosan ja kaistan perusteella) pilkottuina tiedostoina sen alaisuudessa.
    if "palvelutason-mittaus" in kohdeluokka: 
            url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + "/"
            auth = 'Bearer ' + token
            api_call_headers = {'Authorization': auth}
            api_call_response, url =  requests.get(url, headers=api_call_headers), url
            content = json.loads(api_call_response.text)
            print("here")
            return render_template("kohdeluokka_latauspalvelu_alt.html", data=content, target=target, path=None, filters=None)
    else:
        filters = {}
        if parts[0] == "kohdeluokka": 
            content, path = kohdeluokka_dict(target, token)
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
                        as_dict = {}
                        for d in content:
                            as_dict[d["oid"]] = d
                        return render_template('kohdeluokka_latauspalvelu.html', data=as_dict, target=target, path=path, filters=filters)
            else:
                if type(content) is str: 
                    return content
                else: 
                    first_ten = content[:25]
                    as_dict = {}
                    for d in first_ten:
                        as_dict[d["oid"]] = d
                    return render_template('kohdeluokka_latauspalvelu.html', data=as_dict, target=target, path=path, filters=filters)

        else:
            data = meta_tiedot(kohdeluokka, auth)
            try: 
                return render_template('kohdeluokka_latauspalvelu.html', data=data[target], target=target, filters=filters)
            except: 
                return render_template('kohdeluokka_latauspalvelu.html', data={"Error": "No data with this keyword"}, target=target, filters=filters)


# Osa kohdeluokista jakautuu useaan tiedostoon, koska yhtenä tiedostona niistä tulisi liian suuria. 
# Tällöin kohdeluokan nimi toimii hakemistona, ja data on (yleensä tieosan ja kaistan perusteella) pilkottuina tiedostoina sen alaisuudessa.

@app.route('/mittaustiedot_alt/<key>')
@token_required
def mittaustiedot(key):
    parts = key.split("_")
    url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + "/" + parts[3]
    print(url)
    token = session['token']
    auth = 'Bearer ' + token
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response =  requests.get(url, headers=api_call_headers)
    content = api_call_response.json(cls=ndjson.Decoder)
    #poistaa latauspalvelun ensimmäisen meta rivin
    content = content[1:]
    first_ten = content[:25]
    as_dict = {}
    for d in first_ten:
        as_dict[d["oid"]] = d
    return render_template('kohdeluokka_latauspalvelu.html', data=as_dict, target=key, path=url, filters={})


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
@token_required
def download_ndjson(kohdeluokka):
    try: 
        token = session['token']
    except: 
        return redirect(url_for('login', message="Your token has expired"))
    api_response, url = api_call_data_kohdeluokka(kohdeluokka, token)
    if api_response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
    content = api_response.json(cls=ndjson.Decoder)
    content = content[1:]
    filename = kohdeluokka.split("_")[2] + ".json"
    #open(filename, 'wb').write(content)
    with open(filename, 'w') as f:
        ndjson.dump(content, f)

    return send_file(filename, as_attachment=True)


# Lataa metatieto palvelusta tietyn kohdeluokan metatiedot
@app.route('/download/meta/<kohdeluokka>')
@token_required
def download_meta_json(kohdeluokka):
    url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
    try: 
        auth = 'Bearer ' + str(session['token'])
    except: 
        return redirect(url_for('login', message="Your token has expired"))

    data = '[ "' + kohdeluokka + '" ]'
    api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    api_call_response = requests.post(url, headers=api_call_headers, data=data)
    if api_call_response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
    content = ndjson.loads(api_call_response.text)
    filename = filename = "meta_" + kohdeluokka + ".ndjson"
    with open(filename, 'w') as f:
        ndjson.dump(content, f)

    return send_file(filename, as_attachment=True)

@app.route('/laheta')
@token_required
def laheta():
    try: 
        auth = 'Bearer ' + str(session['token'])
    except: 
        return redirect(url_for('login', message="Your token has expired"))
    vaihtoehdot = {}
    token_url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/nimiavaruudet"
    data = {'accept': 'application/json'}
    api_call_headers = {'Authorization': auth}
    api_call_response = requests.get(token_url, headers=api_call_headers, data=data)
    if api_call_response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
    nimiavaruudet = api_call_response.json()
    for nimi in nimiavaruudet: 
        kohdeluokat = kohdeluokka_metatiedot_schemat(auth, nimi)
        vaihtoehdot[nimi] = kohdeluokat
    vaihtoehdot.popitem()
    return render_template('laheta.html', data=vaihtoehdot)


# Hakee kaikki meneillään olevat lähetykset
@app.route('/lahetykset')
@token_required
def lahetykset():
    try: 
        auth = 'Bearer ' + str(session['token'])
    except: 
        return redirect(url_for('login', message="Your token has expired"))
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tunnisteet" 
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
    lahetys_lista = response.json()
    as_dict = {}
    for lahetys in lahetys_lista: 
        cur_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + lahetys
        response = requests.get(cur_url, headers=headers)
        as_dict[lahetys] = response.json()
    
    return render_template('upload_check.html', data=as_dict, lahetystunniste=None)

# Tarkistaa tietyn lähetyksen statuksen
@app.route('/check_status/<tunniste>')
@token_required
def check_status(tunniste):
    try: 
        auth = 'Bearer ' + str(session['token'])
    except: 
        return redirect(url_for('login', message="Your token has expired"))
    headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
    url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + tunniste
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        session.pop('token')
        return redirect(url_for('login', message="Token expired"))
    return render_template('upload_check.html', data=response.json(), lahetystunniste=tunniste)

# Lähettää tiedoston lähetyspalveluun
@app.route('/put', methods = ['POST'])
@token_required
def curl_put():
    if request.method == 'POST':
        target = request.form['target'] 
        parts = target.split("_") 

        url     = 'https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/laheta'
        try: 
            auth = 'Bearer ' + str(session['token'])
        except: 
            return redirect(url_for('login', message="Your token has expired"))
        headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        data    = {"kohdeluokka": parts[1] + "/" + parts[2]}

        response = requests.post(url, headers=headers, data=json.dumps(data))
        if response.status_code == 401:
            session.pop('token')
            return redirect(url_for('login', message="Token expired"))

        response_json = response.json()
        upload_url = response_json["url"]

        file_form = request.files['file']
        filename = file_form.filename
        #if filename.split('.')[1] == 'csv':
        #   converted = convert_csv_to_json(file)
        upload = requests.put(upload_url, files={'file': file_form.read()}, verify=False)

        status_url = "https://api-v2.stg.velho.vayla.fi/lahetyspalvelu/api/v1/tila/" + response_json["lahetystunniste"]
        return render_template("upload_check.html", data=requests.get(status_url, headers=headers).json(), lahetystunniste=response_json["lahetystunniste"])

        #return redirect(url_for('lahetykset'))

# Yhdistelee useiden kohdeluokkien tietoja yhdeksi csv:ksi
@app.route('/csv/tieosat', methods = ['POST'])
@token_required
def tieosat_csv():
    if request.method == 'POST':
        options_json = request.form['selected_options']
        options = json.loads(options_json)
        options.reverse()
        try: 
            token = session['token']
        except: 
            return redirect(url_for('login', message="Your token has expired"))
        obj = CsvLinearReference(options, token)
        filename = obj.write_and_run()
        return send_file(filename, as_attachment=True)

@app.route('/<kohdeluokka>/csv')
@token_required
def kohdeluokka_csv(kohdeluokka):
    try: 
        token = session['token']
    except: 
        return redirect(url_for('login', message="Valid token is required, please enter api information"))
    content, url = kohdeluokka_dict(kohdeluokka, token)
    file = csv_write_kohdeluokka(content, kohdeluokka)
    return send_file(file, as_attachment=True)

@app.route("/csv")
@token_required
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
@token_required
def csv_to_json():
    if request.method == 'POST':
        files = request.files['file']
        filename = files.filename.split(".")[0] + ".ndjson"
        converted = convert_csv_to_json(files)
        try: 
            with open(filename, 'w') as f:
                ndjson.dump(converted, f)
            return send_file(filename, as_attachment=True, attachment_filename=filename)
        except: 
            return "Virhe muunnoksessa. Lähettävä tiedosto ei saa olla avattuna"



@app.route('/info')
@token_required
def info():
    return render_template('info.html')