import requests, json, ndjson
import csv
import itertools
import os
import time, datetime
from datetime import datetime

# Hakee tokenin jota hyödynnetään muiden funktioiden get ja post pyyntöjen headerin auth osiossa
def token(): 
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


# Palauttaa listan tietyn kohdeluokan objecteista, sekä hakemiseen käytetyn url:n
# target tulee muodossa kohdeluokka_nimiavaruus_kohdeluokan_nimi
# esim. kohdeluokka_varusteet_aidat tai kohdeluokka_urakka_palvelusopimus 
def kohdeluokka_dict(target):
        parts = target.split("_") 
        url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + ".json" 
        auth = 'Bearer ' + str(token())
        api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        api_call_response = requests.get(url, headers=api_call_headers)
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
def kohdeluokka_dict_same_token(target, token):
        parts = target.split("_") 
        url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + ".json" 
        auth = 'Bearer ' + token
        api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        api_call_response = requests.get(url, headers=api_call_headers)
        try: 
                content = api_call_response.json(cls=ndjson.Decoder)
                content = content[1:]
        except: 
                content = api_call_response.text

        return content, url 

# Hakee metatietopalvelusta kohdeluokkien nimet ja nimikkeistöt
def meta_tiedot(class_name): 
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
                                ominaisuudet = obj[ominaisuus]
                                try: 
                                        parts = ominaisuudet[tarkenne].split("/")
                                        return parts[1] 
                                except: 
                                        return ominaisuudet[tarkenne]
                        else: 
                                ominaisuudet = obj[ominaisuus]
                                for i in ominaisuudet: 
                                        if tarkenne in i: 
                                                try: 
                                                        parts = i[tarkenne].split("/")
                                                        return parts[1] 
                                                except: 
                                                        return i[tarkenne]
                else: 
                        return obj[ominaisuus]
        else: 
                return obj

# Etsii listasta objectin, joka täyttää vaatimukset ja palauttaa joko obj[ominaisuus] tai obj[ominaisuus][tarkenne]
# Esim. tieosan hallinnollisen luokan (tieosa/ominaisuudet/hallinnollinen-luokka) joka osuu tietylle tie/osa välille
# obj_list = kohdeluokan objectit listana
# tie = haettava tie
# aosa = alun osa, aet = alun etäisyys, losa = lopun osa (jos kaksi sijaintia), let = lopun etäisyys
# Objectit ovat dict muotoisia, jolloin ominaisuudella viitataan ensimmäiseen obj[__tahan__] hakuun (yleensä "ominaisuudet")
# Tarkenne on sitten obj[ominaisuus][tarkenne] jos obj[ominaisuus] on myös dict muotoa
# Jos tarkenetta == None, palauttaa obj[ominaisuus]
# Jos ominaisuus == None, palauttaa objectin

def finder(obj_list, tie, aosa, aet, losa, let, ominaisuus, tarkenne): 
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

# Ryhmittelee kohdeluokan objectit teiden perusteella
# Palauttaa dictionaryn jolla voi hakea dict_name[__tien numero__] objectit tietyllä tiellä
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

# Käytännössä vain kutsuu group_by_tie ja kohdeluokka_dict_same_token functiota siistimmän koodin takia
def grouped_by_tie(target, auth_token): 
        as_dict = kohdeluokka_dict_same_token(target, auth_token)
        data = as_dict[0]
        return group_by_tie(data)

def etaisyys_laskin(aosa, aet, losa, let): 
        if aosa == losa: 
                return let-aet
        else: 
                diff = losa - aosa
                # TODO
                return None

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

                auth_token = str(token())

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

def urakat_csv(target):
        data = kohdeluokka_dict(target)
        content = data[0]
        date = datetime.today().strftime('%d-%m-%Y')
        filename = date + "-" + target + ".csv"
        with open(filename, 'w', newline='') as csvfile:
                #Valmistellaan käytettävät nimikkeet headeriin 
                fieldnames = [
                        'tilannepvm', 
                        'piiri', 
                        'tie', 
                        'ajr', 
                        'aosa', 
                        'aet', 
                        'ej', 
                        'losa', 
                        'let', 
                        'pituus', 
                        'tiety', 
                        'kplk', 
                        'alev', 
                        'pt',   #muutettu paalluok -> pt(sidotut) ja spr(sitomattomat) 
                        'spr',
                        'pvty', 
                        'pvalue',
                        'pvnro',
                        'pvsuoja',
                        'pvsuola',
                        'pvtaso',
                        'pvteksti',
                        'soratielk',
                        'pyplk',
                        'katyyppi',
                        'kkvl',
                        'ualue',
                        'tualue',
                        'viherlk']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                
                # Haetaan token

                auth_token = str(token())

                # Haetaan käytettävät kohdeluokat, ja ryhmitellään ne teiden mukaan nopeampaa hakua varten

                grouped_tieosat          = grouped_by_tie("kohdeluokka_sijainti_tieosa", auth_token)
                grouped_talvihoitoluokat = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_talvihoitoluokka", auth_token)
                grouped_viherhoitoluokat = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_viherhoitoluokka", auth_token)
                grouped_sidotut         = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sidotut-paallysrakenteet", auth_token)
                grouped_sitomattomat    = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sitomattomat-pintarakenteet", auth_token)
                grouped_pohjavedet      = grouped_by_tie("kohdeluokka_alueet_pohjavesialueet", auth_token)
                grouped_soratiet        = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_soratieluokka", auth_token)
                grouped_korjausluokat   = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_paallysteen-korjausluokka", auth_token)


                # Käydään läpi kohdeluokan objectit
                for record in content:
                        if "sijainnit" in record:
                                sijainnit = record['sijainnit']
                                for sijainti in sijainnit: 
                                        if "alkusijainti" in sijainti and "loppusijainti" in sijainti:
                                                alkusijainti  = sijainti['alkusijainti']
                                                loppusijainti = sijainti['loppusijainti']
                                                tie = alkusijainti["tie"]
                                                aosa = alkusijainti["osa"]
                                                losa = loppusijainti["osa"]
                                                aet = alkusijainti["etaisyys"]
                                                let = loppusijainti["etaisyys"]

                                                # Haetaan pohjavesi ennen kirjoittamista, sillä sitä käytetään useaan kenttään
                                                pohjavesi = finder(grouped_pohjavedet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", None)

                                                # Haetaan sidotut päällysrakenteet ennen kirjoittamista, sillä objectin kaistan vertailulle pitää muodostaa if lause
                                                sidotut_rakenteet = finder(grouped_sidotut.get(tie) or [], tie, aosa, aet, losa, let, None, None)
                                                sidotut_rakenteet_tyyppi = None 
                                                if sidotut_rakenteet and "sijaintitarkenne" in sidotut_rakenteet:
                                                        if sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 11 or sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 21: 
                                                                parts = sidotut_rakenteet["ominaisuudet"]["paallysteen-tyyppi"].split("/")
                                                                sidotut_rakenteet_tyyppi = parts[1]
                                             
                                                writer.writerow({
                                                        'tilannepvm'    : record['alkaen'] or None,
                                                        'piiri'         : None, 
                                                        'tie'           : tie or 0,
                                                        'ajr'           : alkusijainti['ajorata'] or None,
                                                        'aosa'          : aosa or 0,
                                                        'aet'           : aet or 0,
                                                        'ej'            : None,
                                                        'losa'          : losa or 0,
                                                        'let'           : let or 0,
                                                        'pituus'        : int(let or 0) - int(aet or 0),
                                                        'tiety'         : finder(grouped_tieosat.get(tie) or [], tie, aosa, aet, losa, let, "hallinnolliset-luokat", "hallinnollinen-luokka"), #Hallinnollinen luokka -> tieosa -> hallinnollisetluokat -> hallinnollinenluokka
                                                        'kplk'          : finder(grouped_talvihoitoluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "talvihoitoluokka"), #Talvihoitoluokka
                                                        'alev'          : None, #Ajoradanleveys hae tieosa/etäisyydet -> topologia -> hae kaistojen määrä -> laske kaistojen yhteenlaskettu leveys !!!topologia ei vielä latauspalvelussa
                                                        'pt'            : sidotut_rakenteet_tyyppi, #sidotut päällysrakenteet paallystetyyppi ||  Päällysteet/pintarakenteet/  sijantitarkenne/kaista oltava 11 tai 21 huom tee kaksi kentää sidotutpäällysrakenteet päällysteentyyppi ja sitomattomat runkomateriaali
                                                        'spr'           : finder(grouped_sitomattomat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "runkomateriaali"), #sitomattoman-pintarakenteen-runkomateriaali
                                                        'pvty'          : pohjavesi["tyyppi"].split("/")[1] if pohjavesi else None, #Pohjavesialueen tyyppi
                                                        'pvalue'        : pohjavesi["rakenteelliset-ominaisuudet"]["nimi"] if pohjavesi else None, #Pohjavesialue
                                                        'pvnro'         : pohjavesi["toiminnalliset-ominaisuudet"]["tunnus"] if pohjavesi else None, #SYKE:n alueesta käyttämätunnus
                                                        'pvsuoja'       : None, 
                                                        'pvsuola'       : None,  
                                                        'pvtaso'        : None, 
                                                        'pvteksti'      : None, 
                                                        'soratielk'     : finder(grouped_soratiet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "soratieluokka"), 
                                                        'pyplk'         : finder(grouped_korjausluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "paallysteen-korjausluokka"), #Päällysteiden ylläpitoluokka
                                                        'katyyppi'      : None,  #Kaistan tyyppi
                                                        'kkvl'          : None,  #Kesän keskimääräinen vuorokausiliikenne
                                                        'ualue'         : record['ominaisuudet']['urakkakoodi'],  #Urakka-alue / urakan koodi
                                                        'tualue'        : None,  #Tulevan alueurakan numero
                                                        'viherlk'       : finder(grouped_viherhoitoluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "viherhoitoluokka") #hae viherhoitoluokka ei viheralue
                                                })

                        elif "alkusijainti" in record and "loppusijainti" in record:
                                alkusijainti  = record['alkusijainti']
                                loppusijainti = record['loppusijainti']
                                tie = alkusijainti["tie"]
                                aosa = alkusijainti["osa"]
                                losa = loppusijainti["osa"]
                                aet = alkusijainti["etaisyys"]
                                let = loppusijainti["etaisyys"]

                                #Haetaan pohjavesi ennen kirjoittamista, sillä sitä käytetään useaan kenttään
                                pohjavesi = finder(grouped_pohjavedet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", None)

                                #Haetaan sidotut päällysrakenteet ennen kirjoittamista, sillä objectin kaistan vertailulle pitää muodostaa if else lause
                                sidotut_rakenteet = finder(grouped_sidotut.get(tie) or [], tie, aosa, aet, losa, let, None, None)
                                sidotut_rakenteet_tyyppi = None 
                                if sidotut_rakenteet and "sijaintitarkenne" in sidotut_rakenteet:
                                        if sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 11 or sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 21: 
                                                parts = sidotut_rakenteet["ominaisuudet"]["tyyppi"].split("/")
                                                sidotut_rakenteet_tyyppi = parts[1]
                                
                                writer.writerow({
                                        'tilannepvm'    : record['alkaen'] or None,
                                        'piiri'         : None, 
                                        'tie'           : tie or 0,
                                        'ajr'           : alkusijainti['ajorata'] or None,
                                        'aosa'          : aosa or 0,
                                        'aet'           : aet or 0,
                                        'ej'            : None,
                                        'losa'          : losa or 0,
                                        'let'           : let or 0,
                                        'pituus'        : int(let or 0) - int(aet or 0),
                                        'tiety'         : finder(grouped_tieosat.get(tie) or [], tie, aosa, aet, losa, let, "hallinnolliset-luokat", "hallinnollinen-luokka"), #Hallinnollinen luokka -> tieosa -> hallinnollisetluokat -> hallinnollinenluokka
                                        'kplk'          : finder(grouped_talvihoitoluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "talvihoitoluokka"), #Talvihoitoluokka
                                        'alev'          : None, #Ajoradanleveys hae tieosa/etäisyydet -> topologia -> hae kaistojen määrä -> laske kaistojen yhteenlaskettu leveys !!!topologia ei vielä latauspalvelussa
                                        'pt'            : sidotut_rakenteet_tyyppi, #sidotut päällysrakenteet paallystetyyppi ||  Päällysteet/pintarakenteet/  sijantitarkenne/kaista oltava 11 tai 21 huom tee kaksi kentää sidotutpäällysrakenteet päällysteentyyppi ja sitomattomat runkomateriaali
                                        'spr'           : finder(grouped_sitomattomat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "runkomateriaali"), #sitomattoman-pintarakenteen-runkomateriaali
                                        'pvty'          : pohjavesi["tyyppi"].split("/")[1] if pohjavesi else None, #Pohjavesialueen tyyppi
                                        'pvalue'        : pohjavesi["rakenteelliset-ominaisuudet"]["nimi"] if pohjavesi else None, #Pohjavesialue
                                        'pvnro'         : pohjavesi["toiminnalliset-ominaisuudet"]["tunnus"] if pohjavesi else None, #SYKE:n alueesta käyttämätunnus
                                        'pvsuoja'       : None, 
                                        'pvsuola'       : None,  
                                        'pvtaso'        : None, 
                                        'pvteksti'      : None, 
                                        'soratielk'     : finder(grouped_soratiet.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "soratieluokka"), 
                                        'pyplk'         : finder(grouped_korjausluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "paallysteen-korjausluokka"), #Päällysteiden ylläpitoluokka
                                        'katyyppi'      : None,  #Kaistan tyyppi
                                        'kkvl'          : None,  #Kesän keskimääräinen vuorokausiliikenne
                                        'ualue'         : record['ominaisuudet']['urakkakoodi'],  #Urakka-alue / urakan koodi
                                        'tualue'        : None,  #Tulevan alueurakan numero
                                        'viherlk'       : finder(grouped_viherhoitoluokat.get(tie) or [], tie, aosa, aet, losa, let, "ominaisuudet", "viherhoitoluokka") #hae viherhoitoluokka ei viheralue
                                })
        

                        else: 
                                pass
                



#NIMIKKEISTÖ SELITYKSET METATIETO JSONISSA INFON ALLA                                            