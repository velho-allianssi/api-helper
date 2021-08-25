import requests, json, ndjson
import os
import copy
import sys

# Finder ja apufunktiot omaan tiedostoon

# Hakee tokenin jota hyödynnetään muiden funktioiden get ja post pyyntöjen headerin auth osiossa


def login_token(client_id, client_secret): 
        token_url = "https://auth.stg.velho.vayla.fi/oauth2/token"
        test_api_url = "https://api-v2.stg.velho.vayla.fi"
        data = {'grant_type': 'client_credentials'}

        access_token_response = requests.post(token_url, data=data, verify=False, allow_redirects=False, auth=(client_id, client_secret))
        if access_token_response.status_code == 200: 
                tokens = json.loads(access_token_response.text)
                return tokens['access_token']
        else: 
                None

def api_call_data_kohdeluokka(kohdeluokka, token): 
        parts = kohdeluokka.split("_") 
        url = "https://api-v2.stg.velho.vayla.fi/latauspalvelu/viimeisin/" + parts[1] + "/" + parts[2] + ".json"
        auth = 'Bearer ' + token
        api_call_headers = {'Authorization': auth, 'accept': "application/json", 'Content-Type': "application/json"}
        return requests.get(url, headers=api_call_headers), url


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
def meta_tiedot(class_name, auth): 
        url = "https://api-v2.stg.velho.vayla.fi/metatietopalvelu/api/v2/metatiedot"

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
# Tarkistaa ovatko ominaisuus ja tarkenne määriteltyjä, sekä kuuluvatko ne dict objektiin
# Palauttaa joko koko objektin, obj[ominaisuuden] tai obj[ominaisuus][tarkenne]
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


# Vertailee kahden kohdeluokan objektin enkoodattuja sijainteja 
# |.......| = alkuperäinen objekti ja ------- = vertailtava objekti
# Jos vertailtava objekti kattaa alkuperäisen objektin sekä alkupisteen, että loppupisteen, palautetaan 0 
# Esim: |-------| tai --|----| tai |-----|--- tai ---|------|--
# Jos vertailtava objekti alkaa myöhemmin kuin alkuperäinen objekti, mutta loppuu alkuperäisen objektin jälkeen, palautetaan 1
# Esim: |...-----| tai |..----|---
# Jos vertailtava objekti loppuu ennen alkuperäistä objektiä, mutta alkaa ennen tai samaanaikaan kuin alkuperäinen objekti, palautetaan 2
# Esim: |------....| tai ---|---....|
# Jos vertailtava objektin alku ja loppu ovat alkuperäisen objektin sisällä, palautetaan 3
# Esim: |..-----....|
# Jos vertailtava objekti ei leikkaa millään tavalla alkuperäistä objektia, palautetaan -1 
def encoded_split_cases(enkoodattu_alku, enkoodattu_loppu, vertailtava_alku, vertailtava_loppu, tieosa, vertailtava_osa):
        if tieosa == vertailtava_osa: 
                if vertailtava_alku <= enkoodattu_alku:
                        if vertailtava_loppu < enkoodattu_alku:
                                return -1
                        else: 
                                if vertailtava_loppu >= enkoodattu_loppu:
                                        return 0 
                                else: 
                                        return 2
                elif vertailtava_alku > enkoodattu_alku:
                        if vertailtava_alku >= enkoodattu_loppu:
                                return -1
                        else: 
                                if vertailtava_loppu >= enkoodattu_loppu:
                                        return 1
                                else: 
                                        return 3
                else: 
                        return -1
        else: 
                return -1
        

# Apufunktio finder_encoded funktiolle
# Kutsutaan jos käsiteltävä objekti sisältää "sijainnit"
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
# Kutsutaan jos käsiteltävä objekti sisältää "alkusijainti" tai "loppusijainti"

def finder_encoded_alku_ja_loppu_sijainti(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, prev_result):
        obj_alku  = obj["alkusijainti"]["enkoodattu"]
        obj_loppu = obj["loppusijainti"]["enkoodattu"]
        osa = prev_result['aosa']
        vertailtava_osa = obj["alkusijainti"]["osa"]
        # Testaukseen vain yhdellä ajoradalla
        #if vertailtava_osa["alkusijainti"]["ajorata"] != 1: return None
        # -----
        rajat = encoded_split_cases(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu, osa, vertailtava_osa)
        if rajat == 0: 
                return {
                        'tie': tie, 
                        'aosa': prev_result['aosa'],
                        'aet': prev_result['aet'], 
                        'enkoodattu_alku': enkoodattu_alku, 
                        'losa': prev_result['aosa'], 
                        'let': prev_result['let'], 
                        'enkoodattu_loppu': enkoodattu_loppu, 
                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                        }
        elif rajat == 1:
                return {
                        'tie': tie, 
                        'aosa': obj["alkusijainti"]['osa'], 
                        'aet': obj['alkusijainti']['etaisyys'], 
                        'enkoodattu_alku': obj_alku, 
                        'losa': prev_result['aosa'], 
                        'let': prev_result['let'], 
                        'enkoodattu_loppu': enkoodattu_loppu, 
                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                }
        elif rajat == 2:
                return {
                        'tie': tie, 
                        'aosa': prev_result['aosa'],
                        'aet': prev_result['aet'], 
                        'enkoodattu_alku': enkoodattu_alku, 
                        'losa': obj["loppusijainti"]['osa'], 
                        'let': obj['loppusijainti']['etaisyys'], 
                        'enkoodattu_loppu': obj_loppu, 
                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                }
        elif rajat == 3: 
                return {
                        'tie': tie, 
                        'aosa': obj["alkusijainti"]['osa'], 
                        'aet': obj['alkusijainti']['etaisyys'], 
                        'enkoodattu_alku': obj_alku, 
                        'losa': obj["loppusijainti"]['osa'], 
                        'let': obj['loppusijainti']['etaisyys'], 
                        'enkoodattu_loppu': obj_loppu, 
                        'value': check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                }
        else: 
                return None


# Apufunktio finder_encoded funktiolle
# Kutsutaan jos käsiteltävä objekti sisältää "tie", eli käytännössä vain sijainti/tieosa kohdeluokalle

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
        
# Etsii tietyn kohdeluokan objektit tietyllä enkoodatulla välillä 

def finder_encoded(obj_list, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, prev_result):
        results = []
        if not obj_list: 
                return None
  
        for obj in obj_list:
                        if "sijainnit" in obj:
                                results = finder_encoded_sijannit(obj, results, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne)
                        elif "alkusijainti" in obj and "loppusijainti" in obj:
                                find = finder_encoded_alku_ja_loppu_sijainti(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, prev_result)

                                # Tarkistaa onko objektia olemassa jo listassa
                                # Jos objekti onjo listassa, sitä ei lisätä listaan
                                if find:
                                        duplicate = False
                                        for x in results: 
                                                if x == find:
                                                        duplicate == True
                                        if duplicate == False:
                                                results.append(find)
                        elif "tie" in obj: 
                                find = finder_encoded_tieosat(obj, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne)
                                if find: 
                                        results.append(find)

        return results
                        

# Etsii listasta objektin, joka täyttää vaatimukset ja palauttaa joko obj[ominaisuus] tai obj[ominaisuus][tarkenne]
# Esim. tieosan hallinnollisen luokan (tieosa/ominaisuudet/hallinnollinen-luokka) joka osuu tietylle tie/osa välille
# obj_list = kohdeluokan objektit listana
# tie = haettava tie
# aosa = alun osa, aet = alun etäisyys, losa = lopun osa (jos kaksi sijaintia), let = lopun etäisyys
# objektit ovat dict muotoisia, jolloin ominaisuudella viitataan ensimmäiseen obj[__tahan__] hakuun (yleensä "ominaisuudet")
# Tarkenne on sitten obj[ominaisuus][tarkenne] jos obj[ominaisuus] on myös dict muotoa
# Jos tarkenne == None, palauttaa obj[ominaisuus]
# Jos ominaisuus == None, palauttaa objektin

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
# Ryhmittelee kohdeluokan objektit teiden perusteella
# Palauttaa dictionaryn jolla voi hakea dict_name[__tien numero__] objektit tietyllä tiellä
# Pilko kolmeen functioon

def group_by_tie(obj_list):
        grouped = {}
        try:
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
        except Exception as e: 
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

        
        return grouped 

# Jos kohdeluokan sijainti ylittää tieosan, pilkotaan se osiin
# tieosat on lista tieosia jollain tiellä, obj on pilkottavan kohdeluokan objekti 

# Tuplaa tulosten määrän, ongelma täällä??

def split_at_parts(tieosat, kohdeluokka):
        result = []
        try:    
                if "alkusijainti" in kohdeluokka:
                        alku  = kohdeluokka["alkusijainti"] 
                        loppu = kohdeluokka["loppusijainti"]

                        if alku["osa"] != loppu["osa"]:

                                tieosa_alku = finder(tieosat, alku["tie"], alku["osa"], alku["osa"], None, None)

                                new_kohdeluokka = copy.deepcopy(kohdeluokka)
                                new_kohdeluokka["loppusijainti"]["osa"]      = alku["osa"]
                                new_kohdeluokka["loppusijainti"]["etaisyys"] = tieosa_alku["pituus"]
                                new_kohdeluokka["loppusijainti"]["etaisyys-tien-alusta"] = tieosa_alku["lopun-etaisyys-tien-alusta"]
                                new_kohdeluokka["loppusijainti"]["enkoodattu"] = tieosa_alku["enkoodattu-loppu"]
                                result.append(new_kohdeluokka)
                                i = alku["osa"] + 1

                                while i < loppu["osa"]:
                                        tieosa_cur = finder(tieosat, alku["tie"], i, i, None, None)
                                        if tieosa_cur:
                                                cur_kohdeluokka = copy.deepcopy(kohdeluokka)
                                                cur_alku = {
                                                        'osa': i,
                                                        'tie': tieosa_cur["tie"],
                                                        'etaisyys': 0,
                                                        'etaisyys-tien-alusta': tieosa_cur["alun-etaisyys-tien-alusta"],
                                                        'enkoodattu': tieosa_cur["enkoodattu-alku"],
                                                        'ajorata': alku["ajorata"]
                                                }
                                                cur_loppu = {
                                                        'osa': i,
                                                        'tie': tieosa_cur["tie"],
                                                        'etaisyys': tieosa_cur["pituus"],
                                                        'etaisyys-tien-alusta': tieosa_cur["lopun-etaisyys-tien-alusta"],
                                                        'enkoodattu': tieosa_cur["enkoodattu-loppu"],
                                                        'ajorata': alku["ajorata"]
                                                }
                                                cur_kohdeluokka["alkusijainti"] = cur_alku
                                                cur_kohdeluokka["loppusijainti"] = cur_loppu
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

