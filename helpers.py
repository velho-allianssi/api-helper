import requests, json, ndjson
import csv
import os
import time, datetime
from datetime import datetime
import sys
import copy

# Tee oma funktio parts = target.split("_") 
# url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + ".json" 
# auth = 'Bearer ' + str(token())
# api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
# api_call_response = requests.get(url, headers=api_call_headers)
# Näille

# Finder ja apufunktiot omaan tiedostoon


# Hakee tokenin jota hyödynnetään muiden funktioiden get ja post pyyntöjen headerin auth osiossa
def get_token(): 
        token_url = "https://auth.stg.velho.vayla.fi/oauth2/token"

        test_api_url = "https://api-v2.stg.velho.vayla.fi"

        #hae env tiedostosta
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")

        data = {'grant_type': 'client_credentials'}

        access_token_response = requests.post(token_url, data=data, verify=False, allow_redirects=False, auth=(client_id, client_secret))
        tokens = json.loads(access_token_response.text)
        print(tokens['access_token'])
        return tokens['access_token']


def api_call_data(url, data, method): 
        url = url 
        url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
        auth = 'Bearer ' + str(get_token())

        data = '[ "' + data + '" ]' 
        api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        if method == 'post':
                return requests.post(url, headers=api_call_headers, data=data) 
        else: 
                return requests.get(url, headers=api_call_headers, data=data) 

def api_call_data_kohdeluokka(kohdeluokka, token): 
        parts = kohdeluokka.split("_") 
        url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + ".json"
        auth = 'Bearer ' + str(get_token()) if not token else 'Bearer ' + token
        api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        return requests.get(url, headers=api_call_headers), url


# Palauttaa listan tietyn kohdeluokan objecteista, sekä hakemiseen käytetyn url:n
# target tulee muodossa kohdeluokka_nimiavaruus_kohdeluokan_nimi
# esim. kohdeluokka_varusteet_aidat tai kohdeluokka_urakka_palvelusopimus 
def kohdeluokka_dict(kohdeluokka):
        api_call_response, url = api_call_data_kohdeluokka(kohdeluokka, None)
        try: 
                #purkaa ndjsonin python listaksi
                content = api_call_response.json(cls=ndjson.Decoder)
                #poistaa latauspalvelun ensimmäisen meta rivin
                content = content[1:]
        except: 
                #jos api ei palauta ndjson tiedostoa, näytetään pyynnön mukana tullut teksti
                content = api_call_response.text

        return content, url 

# Sama kuin kohdeluokka_dict mutta ei hae uutta tokenia
def kohdeluokka_dict_same_token(kohdeluokka, token):
        api_call_response, url = api_call_data_kohdeluokka(kohdeluokka, token)
        try: 
                content = api_call_response.json(cls=ndjson.Decoder)
                content = content[1:]
        except: 
                content = api_call_response.text

        return content, url 

# Hakee metatietopalvelusta kohdeluokkien nimet ja nimikkeistöt
def meta_tiedot(class_name): 
        url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"
        auth = 'Bearer ' + str(get_token())

        data = '[ "' + class_name + '" ]'
        api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        api_call_response = requests.post(url, headers=api_call_headers, data=data)
        vals = api_call_response.json().values()
        to_list = list(vals)
        schemas = to_list[1]
        s_vals = schemas["schemas"]
        s_list = list(s_vals)
        nimikkeistot = {}
        for s in s_vals: 
                if "kohdeluokka" not in s: 
                        nimikkeistot[s] = s_vals[s]
 
        return nimikkeistot

# Apu-funktio finder-funktiolle
# Tarkistaa ovatko ominaisuus ja tarkenne määriteltyjä, sekä kuuluvatko ne dict objectiin
# Palauttaa joko koko objectin, obj[ominaisuuden] tai obj[ominaisuus][tarkenne]
# split metodia käytetään siistimiseen, esim verkon-materiaali/mt01 otetaan vain mt01

def check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne):
        if ominaisuus and ominaisuus in obj:
                if tarkenne:
                        if type(obj[ominaisuus]) is dict:
                                try: 
                                        return obj[ominaisuus][tarkenne].split("/")[1]
                                except: 
                                        return obj[ominaisuus][tarkenne]
                        else: 
                                ominaisuudet = obj[ominaisuus]
                                for i in ominaisuudet: 
                                        if tarkenne in i: 
                                                try: 
                                                        return i[tarkenne].split("/")[1]
                                                except: 
                                                        return i[tarkenne]
                else: 
                        return obj[ominaisuus]
        else: 
                return obj


# Enkoodaus 100 milj * tienum + pituus 
# Enkoodaus 300008782 = tie 3 etaisyys 8782
# loppu alun jälkeen, loppu ennen alkua
# alku inklusiivinen loppu ekslusiivinen

def encode(tie, etaisyys):
        return 100000000 * tie + etaisyys
        
# Palauttaa etaisyyden tien alusta/lopusta
def decode_to_length(enkoodattu, tie):
        return enkoodattu / tie / 10000000

# loppu alun jälkeen, loppu ennen alkua
# alku inklusiivinen loppu ekslusiivinen

def encoded_in_range(enkoodattu_alku, enkoodattu_loppu, vertailtava_alku, vertailtava_loppu):
        if enkoodattu_alku <= vertailtava_loppu and enkoodattu_loppu > vertailtava_alku:
                return True
        else: 
                return False


# Apufunktio finder_encoded funktiolle
# Kutsutaan jos käsiteltävä objecti sisältää "sijainnit"
def finder_encoded_sijannit(obj, results, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne):
        results = results
        for sijainti in obj["sijainnit"]:
                alkusijainti  = sijainti["alkusijainti"]
                loppusijainti = sijainti["loppusijainti"]
                if "enkoodattu" in alkusijainti:
                        obj_alku  = alkusijainti["enkoodattu"]
                        obj_loppu = loppusijainti["enkoodattu"]
                        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                                # Rivitä nämä
                                results.append({
                                        'tie': tie, 
                                        'aosa': alkusijainti['osa'], 
                                        'aet': alkusijainti['etaisyys'], 
                                        'enkoodattu_alku': obj_alku, 
                                        'losa': loppusijainti['osa'], 
                                        'let': loppusijainti['etaisyys'], 
                                        'enkoodattu_loppu': obj_loppu, 
                                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                        })
                else: 
                        obj_alku  = encode(alkusijainti["tie"], alkusijainti["osa"])
                        obj_loppu = encode(loppusijainti["tie"], loppusijainti["osa"])
                        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                                results.append({
                                        'tie': tie, 
                                        'aosa': alkusijainti['osa'], 
                                        'aet': alkusijainti['etaisyys'], 
                                        'enkoodattu_alku': obj_alku, 
                                        'losa': loppusijainti['osa'], 
                                        'let': loppusijainti['etaisyys'], 
                                        'enkoodattu_loppu': obj_loppu, 
                                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                        })
                return results

# Apufunktio finder_encoded funktiolle
# Kutsutaan jos käsiteltävä objecti sisältää "alkusijainti" tai "loppusijainti"

def finder_encoded_alku_ja_loppu_sijainti(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne):
        result = None
        obj_alku  = obj["alkusijainti"]["enkoodattu"]
        obj_loppu = obj["loppusijainti"]["enkoodattu"]
        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                result = {
                        'tie': tie, 
                        'aosa': obj["alkusijainti"]['osa'], 
                        'aet': obj['alkusijainti']['etaisyys'], 
                        'enkoodattu_alku': obj_alku, 
                        'losa': obj["loppusijainti"]['osa'], 
                        'let': obj['loppusijainti']['etaisyys'], 
                        'enkoodattu_loppu': obj_loppu, 
                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                        }
        return result

# Apufunktio finder_encoded funktiolle
# Kutsutaan jos käsiteltävä objecti sisältää "tie", eli käytännössä vain sijainti/tieosa kohdeluokalle

def finder_encoded_tieosat(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne):
        result = None
        obj_alku  = obj["enkoodattu-alku"]
        obj_loppu = obj["enkoodattu-loppu"]
        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                result = {
                        'tie': tie, 
                        'aosa': obj['osa'], 
                        'aet': 0, 
                        'enkoodattu_alku': obj_alku, 
                        'losa': obj['osa'], 
                        'let': obj_loppu - obj_alku, 
                        'enkoodattu_loppu': obj_loppu, 
                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                        }
        return result
        
# Etsii tietyn kohdeluokan objectit tietyllä enkoodatulla välillä 

def finder_encoded(obj_list, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne):
    results = []
    if not obj_list: 
            return None
    for obj in obj_list:
            if "sijainnit" in obj:
                    results = finder_encoded_sijannit(obj, results, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne)
            elif "alkusijainti" in obj and "loppusijainti" in obj:
                    find = finder_encoded_alku_ja_loppu_sijainti(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne)
                    if find: 
                            results.append(find)
            elif "tie" in obj: 
                    find = finder_encoded_tieosat(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne)
                    if find: 
                            results.append(find)

    return results
                        

# Etsii listasta objectin, joka täyttää vaatimukset ja palauttaa joko obj[ominaisuus] tai obj[ominaisuus][tarkenne]
# Esim. tieosan hallinnollisen luokan (tieosa/ominaisuudet/hallinnollinen-luokka) joka osuu tietylle tie/osa välille
# obj_list = kohdeluokan objectit listana
# tie = haettava tie
# aosa = alun osa, aet = alun etäisyys, losa = lopun osa (jos kaksi sijaintia), let = lopun etäisyys
# Objectit ovat dict muotoisia, jolloin ominaisuudella viitataan ensimmäiseen obj[__tahan__] hakuun (yleensä "ominaisuudet")
# Tarkenne on sitten obj[ominaisuus][tarkenne] jos obj[ominaisuus] on myös dict muotoa
# Jos tarkenne == None, palauttaa obj[ominaisuus]
# Jos ominaisuus == None, palauttaa objectin

def finder(obj_list, tie, aosa, losa, ominaisuus, tarkenne): 
        if not obj_list: 
                return None
        for obj in obj_list: 
                if "sijainti" in obj: 
                        sijainti = obj["sijainti"]
                        if sijainti["osa"] == aosa:
                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)   
                elif "sijainnit" in obj: 
                        for sijainti in obj["sijainnit"]:
                                alkusijainti  = sijainti["alkusijainti"]
                                loppusijainti = sijainti["loppusijainti"]
                                if alkusijainti["osa"] < aosa:
                                        if loppusijainti["osa"] > losa: 
                                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                        elif loppusijainti["osa"] == losa: # and loppusijainti["etaisyys"] >= let: 
                                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                elif alkusijainti["osa"] == aosa: # and alkusijainti["etaisyys"] <= aet:
                                        if loppusijainti["osa"] > losa: 
                                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                        elif loppusijainti["osa"] == losa: # and loppusijainti["etaisyys"] >= let: 
                                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)   

                elif "alkusijainti" in obj and "loppusijainti" in obj: 
                        alkusijainti = obj["alkusijainti"]
                        loppusijainti = obj["loppusijainti"]
                        if alkusijainti["osa"] < aosa:
                                if loppusijainti["osa"] > losa: 
                                        return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                elif loppusijainti["osa"] == losa: # and loppusijainti["etaisyys"] >= let: 
                                        return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                        elif alkusijainti["osa"] == aosa: #and alkusijainti["etaisyys"] <= aet:
                                if loppusijainti["osa"] > losa: 
                                        return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                elif loppusijainti["osa"] == losa: # and loppusijainti["etaisyys"] >= let: 
                                        return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)

                elif "tie" in obj: 
                        if obj["tie"] == tie and obj["osa"] == aosa:
                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
        return None


# group_by_tie ja split at parts omaan tiedostoon
# Ryhmittelee kohdeluokan objectit teiden perusteella
# Palauttaa dictionaryn jolla voi hakea dict_name[__tien numero__] objectit tietyllä tiellä
# Pilko kolmeen functioon
def group_by_tie_tie(grouped, obj):
        if obj["tie"] in grouped: 
                cur = grouped[obj["tie"]]
                cur.append(obj)
                grouped[obj["tie"]] = cur
        else: 
                grouped[obj["tie"]] = [obj]

def group_by_tie(obj_list):
        grouped = {}
        for obj in obj_list:
                if "tie" in obj: 
                        if obj["tie"] in grouped: 
                                cur = grouped[obj["tie"]]
                                cur.append(obj)
                                grouped[obj["tie"]] = cur
                        else: 
                                grouped[obj["tie"]] = [obj]
                elif "alkusijainti" in obj: 
                        alkusijainti = obj["alkusijainti"]
                        if alkusijainti["tie"] in grouped: 
                                cur = grouped[alkusijainti["tie"]]
                                cur.append(obj)
                                grouped[alkusijainti["tie"]] = cur
                        else: 
                                grouped[alkusijainti["tie"]] = [obj]
                else: 
                        for sijainti in obj["sijainnit"]:
                                alkusijainti = sijainti["alkusijainti"]
                                if alkusijainti["tie"] in grouped: 
                                        cur = grouped[alkusijainti["tie"]]
                                        cur.append(obj)
                                        grouped[alkusijainti["tie"]] = cur
                                else: 
                                        grouped[alkusijainti["tie"]] = [obj]
        return grouped 

# Jos kohdeluokan sijainti ylittää tieosan, pilkotaan se osiin
# tieosat on lista tieosia jollain tiellä, obj on pilkottavan kohdeluokan objecti 

# Tuplaa tulosten määrän, ongelma täällä??

def split_at_parts(tieosat, kohdeluokka):
        result = []
        try: 
                alku  = kohdeluokka["alkusijainti"] 
                loppu = kohdeluokka["loppusijainti"]

                if alku["osa"] != loppu["osa"]:

                        tieosa_alku = finder(tieosat, alku["tie"], alku["osa"], alku["osa"], None, None)

                        new_kohdeluokka = copy.deepcopy(kohdeluokka)
                        new_kohdeluokka["loppusijainti"]["osa"]      = alku["osa"]
                        new_kohdeluokka["loppusijainti"]["etaisyys"] = tieosa_alku["pituus"]
                        new_kohdeluokka["loppusijainti"]["etaisyys-tien-alusta"] = alku["etaisyys-tien-alusta"] + tieosa_alku["pituus"]
                        new_kohdeluokka["loppusijainti"]["enkoodattu"] = alku["enkoodattu"] + tieosa_alku["pituus"]
                        result.append(new_kohdeluokka)
                        i = alku["osa"] + 1

                        while i < loppu["osa"]:
                                tieosa_cur = finder(tieosat, alku["tie"], i, i, None, None)
                                cur_kohdeluokka = copy.deepcopy(kohdeluokka)
                                alku = {
                                        'osa': tieosa_cur["osa"],
                                        'tie': tieosa_cur["tie"],
                                        'etaisyys': 0,
                                        'etaisyys-tien-alusta': tieosa_cur["alun-etaisyys-tien-alusta"],
                                        'enkoodattu': tieosa_cur["enkoodattu-alku"],
                                        'ajorata': alku["ajorata"]
                                }
                                loppu = {
                                        'osa': tieosa_cur["osa"],
                                        'tie': tieosa_cur["tie"],
                                        'etaisyys': tieosa_cur["pituus"],
                                        'etaisyys-tien-alusta': tieosa_cur["lopun-etaisyys-tien-alusta"],
                                        'enkoodattu': tieosa_cur["enkoodattu-loppu"],
                                        'ajorata': alku["ajorata"]
                                }
                                cur_kohdeluokka["alkusijainti"] = alku
                                cur_kohdeluokka["loppusijainti"] = loppu
                                result.append(cur_kohdeluokka)
                                i = i + 1 

                        second_last_kohdeluokka = copy.deepcopy(result[-1])

                        last_kohdeluokka = copy.deepcopy(kohdeluokka)
                        last_kohdeluokka["alkusijainti"]["osa"]         = loppu["osa"]
                        last_kohdeluokka["alkusijainti"]["etaisyys"]    = 0
                        last_kohdeluokka["alkusijainti"]["etaisyys-tien-alusta"] = second_last_kohdeluokka["loppusijainti"]["etaisyys-tien-alusta"]
                        last_kohdeluokka["alkusijainti"]["enkoodattu"]           = second_last_kohdeluokka["loppusijainti"]["enkoodattu"]

                        result.append(last_kohdeluokka)
        
        except Exception as e: 
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

        if not result: 
                result.append(kohdeluokka)
        return result       



# Käytännössä vain kutsuu group_by_tie ja kohdeluokka_dict_same_token functiota siistimmän koodin takia
def grouped_by_tie(target, auth_token): 
        as_dict = kohdeluokka_dict_same_token(target, auth_token)
        data = as_dict[0]
        return group_by_tie(data)


# Tuottaa minimikentät täyttävän csv tiedoston tatulle
def to_tatu_csv(target):
        data = kohdeluokka_dict(target)
        content = data[0]
        

        with open('tatulle.csv', 'w', newline='') as csvfile: 
                fieldnames = ['TIE', 'AJR', 'AOSA', 'AET', 'LOSA', 'LET']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
 
                for record in content:
                        if "sijainnit" in record:
                                sijainnit = record['sijainnit']
                                for sijainti in sijainnit:
                                        if "alkusijainti" in sijainti:
                                                alkusijainti = sijainti['alkusijainti']
                                                if "loppusijainti" in sijainti:
                                                        loppusijainti = sijainti['loppusijainti']
                                                        writer.writerow({
                                                                'TIE'   : alkusijainti['tie']           or None, 
                                                                'AJR'   : alkusijainti['ajorata']       or None, 
                                                                'AOSA'  : alkusijainti['osa']           or None, 
                                                                'AET'   : alkusijainti['etaisyys']      or None,
                                                                'LOSA'  : loppusijainti['osa']          or None,
                                                                'LET'   : loppusijainti['etaisyys']     or None,
                                                        })
                                                else: 
                                                        writer.writerow({
                                                                'TIE'   : alkusijainti['tie']           or None, 
                                                                'AJR'   : alkusijainti['ajorata']       or None, 
                                                                'AOSA'  : alkusijainti['osa']           or None,
                                                                'AET'   : alkusijainti['etaisyys']      or None
                                                        })
                        elif "alkusijainti" in record:
                                alkusijainti = record['alkusijainti']
                                if "loppusijainti" in record:
                                        loppusijainti = record['loppusijainti']
                                        writer.writerow({
                                                'TIE'   : alkusijainti['tie']           or None, 
                                                'AJR'   : alkusijainti['ajorata']       or None, 
                                                'AOSA'  : alkusijainti['osa']           or None, 
                                                'AET'   : alkusijainti['etaisyys']      or None,
                                                'LOSA'  : loppusijainti['osa']          or None,
                                                'LET'   : loppusijainti['etaisyys']     or None
                                        })
                                else: 
                                        writer.writerow({
                                                'TIE'   : alkusijainti['tie']           or None, 
                                                'AJR'   : alkusijainti['ajorata']       or None, 
                                                'AOSA'  : alkusijainti['osa']           or None, 
                                                'AET'   : alkusijainti['etaisyys']      or None,
                                        })

# Yhdistelee kohdeluokkia tieosa kohdeluokkaan käyttämällä tie / tieosa / etaisyyksiä ja kirjoittaa tulokset csv tiedostoon

def tieosat_csv():
        data = kohdeluokka_dict("kohdeluokka_sijainti_tieosa")
        content = data[0]
        date = datetime.today().strftime('%d-%m-%Y')
        filename = date + "-tieosat.csv"
        with open(filename, 'w', newline='') as csvfile:
                fieldnames = [
                        'tilannepvm',
                        'tie',
                        'ajr',
                        'aosa',
                        'aet',
                        'losa',
                        'let',
                        'pituus',
                        'tiety',
                        'kunta',
                        'ualue',
                        'tualue',
                        'vluonne',
                        'toiml',
                        'kplk',
                        'viherlk',
                        'alev',
                        'kaistapa',
                        'paallev',
                        'pyplk',
                        'soratielk'
                ]

                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                
                # Haetaan token

                auth_token = str(get_token())

                grouped_tieosat          = grouped_by_tie("kohdeluokka_sijainti_tieosa", auth_token)
                grouped_talvihoitoluokat = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_talvihoitoluokka", auth_token)
                grouped_viherhoitoluokat = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_viherhoitoluokka", auth_token)
                grouped_sidotut          = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sidotut-paallysrakenteet", auth_token)
                grouped_sitomattomat     = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sitomattomat-pintarakenteet", auth_token)
                grouped_ladottavat       = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_ladottavat-pintarakenteet", auth_token)
                grouped_pintaukset       = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_pintaukset", auth_token)
                grouped_kasvillisuudet   = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_kasvillisuusrakenteet", auth_token)
                grouped_pohjavedet       = grouped_by_tie("kohdeluokka_alueet_pohjavesialueet", auth_token)
                grouped_soratiet         = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_soratieluokka", auth_token)
                grouped_korjausluokat    = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_paallysteen-korjausluokka", auth_token)
                grouped_urakat           = grouped_by_tie("kohdeluokka_urakka_maanteiden-hoitourakka", auth_token)
                grouped_toimluokitukset  = grouped_by_tie("kohdeluokka_kansalliset-luokitukset_toiminnallinen-luokka", auth_token)
                grouped_kaistat          = grouped_by_tie("kohdeluokka_tiealueen-poikkileikkaus_kaistat", auth_token)
                grouped_vaylanluonteet   = grouped_by_tie("kohdeluokka_liikennetekninen-luokitus_vaylan-luonne", auth_token)

                for record in content:
                        tie     = record["tie"]
                        aosa    = record["osa"]
                        losa    = record["osa"]
                        aet     = record["alun-etaisyys-tien-alusta"]
                        let     = record["lopun-etaisyys-tien-alusta"]
                        pituus  = record["pituus"]

                        # Haetaan pohjavesi ennen kirjoittamista, sillä sitä käytetään useaan kenttään
                        pohjavesi = finder(grouped_pohjavedet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", None)

                        # Haetaan sidotut päällysrakenteet ennen kirjoittamista, sillä objectin kaistan vertailulle pitää muodostaa if lause
                        sidotut_rakenteet = finder(grouped_sidotut.get(tie) or [], tie, aosa, aet, losa, let, None, None)
                        sidotut_rakenteet_tyyppi = None 
                        if sidotut_rakenteet and "sijaintitarkenne" in sidotut_rakenteet:
                                if sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 11 or sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 21: 
                                        parts = sidotut_rakenteet["ominaisuudet"]["paallysteen-tyyppi"].split("/")
                                        sidotut_rakenteet_tyyppi = parts[1]
                                
                        #Haetaan kaista ennen kirjoittamista, sillä sen ominaisuustieto vaatii kolme avainta: obj[avain][avain][avain]
                        alev_rakenteelliset = finder(grouped_kaistat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "rakenteelliset-ominaisuudet")
                        alev = None
                        if alev_rakenteelliset: 
                                alev = alev_rakenteelliset["leveys"]

                        # Kaistapaallyste voidaan hakea useasta kohdeluokasta. Käydään kohdeluokat läpi yksikerrallaan, jotta ei tarvitse käyä niitä kaikkia läpi, jos haluttu tulos löytyy aiemmasta kohdeluokasta
                        kaistapaallyste = None
                        if sidotut_rakenteet:
                                kaistapaallyste = sidotut_rakenteet["ominaisuudet"]["paallysteen-tyyppi"].split("/")[1]
                        else:
                                sitomattomat_rakenteet = finder(grouped_sitomattomat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "runkomateriaali")
                                if sitomattomat_rakenteet:
                                        kaistapaallyste = sitomattomat_rakenteet
                                else: 
                                        ladottavat_rakenteet = finder(grouped_ladottavat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "materiaali")
                                        if ladottavat_rakenteet:
                                                kaistapaallyste = ladottavat_rakenteet
                                        else:
                                                pintaukset = finder(grouped_pintaukset.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "pintauksen-tyyppi")
                                                if pintaukset:
                                                        kaistapaallyste = pintaukset
                                                else: 
                                                        kasvillisuudet = finder(grouped_kasvillisuudet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "materiaali")
                                                        if kasvillisuudet:
                                                                kaistapaallyste = kasvillisuudet


                        writer.writerow({
                                'tilannepvm'    : None,
                                'tie'           : tie,
                                'ajr'           : None,
                                'aosa'          : aosa,
                                'aet'           : aet,
                                'losa'          : losa,
                                'let'           : let,
                                'pituus'        : pituus,
                                'tiety'         : finder(grouped_tieosat.get(tie) or [], tie, aosa, aet, losa, let, "hallinnolliset-luokat", "hallinnollinen-luokka"),
                                'kunta'         : None, #Ei ole?
                                'ualue'         : finder(grouped_urakat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "urakkakoodi"),
                                'tualue'        : None,
                                'vluonne'       : finder(grouped_vaylanluonteet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "vaylan-luonne"),
                                'toiml'         : finder(grouped_toimluokitukset.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "toiminnallinen-luokka"),
                                'kplk'          : finder(grouped_talvihoitoluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "talvihoitoluokka"),
                                'viherlk'       : finder(grouped_viherhoitoluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "viherhoitoluokka"),
                                'alev'          : alev, #confluence laske leveys
                                'kaistapa'      : kaistapaallyste, #Yhdistä tähän pt, spr ja pintaukset/pintaustyyppi ja ladottavat pintarakenteet/kivenmateriaali?
                                'pyplk'         : finder(grouped_korjausluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "paallysteen-korjausluokka"),
                                'soratielk'     : finder(grouped_soratiet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "soratieluokka")
                        })
                
#NIMIKKEISTÖ SELITYKSET METATIETO JSONISSA INFON ALLA                                            
