import csv
import time, datetime
from datetime import datetime
from helpers import grouped_by_tie, get_token,  finder_encoded, split_at_parts
import sys
import copy

# Muuttujien nimet selkeämmäksi esim enkoodattu_alku => enkoodattu_alku

class CsvLinearReference:
        def __init__(self):
                auth_token = str(get_token())
                self.kohdeluokat = {
                                'tieosat'       : grouped_by_tie("kohdeluokka_sijainti_tieosa", auth_token),
                                'kplk'          : grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_talvihoitoluokka", auth_token),
                                'viherlk'       : grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_viherhoitoluokka", auth_token),
                                # ---
                                
                                'kaistapa'      : {
                                        'sidotut'          : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sidotut-paallysrakenteet", auth_token),
                                        'sitomattomat'     : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sitomattomat-pintarakenteet", auth_token),
                                        'ladottavat'       : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_ladottavat-pintarakenteet", auth_token),
                                        'pintaukset'       : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_pintaukset", auth_token),
                                #        'kasvillisuudet '  : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_kasvillisuusrakenteet", auth_token)
                                },
                                
                                # ---
                                'toiml'         : grouped_by_tie("kohdeluokka_alueet_pohjavesialueet", auth_token),
                                'soratielk'     : grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_soratieluokka", auth_token),
                                'pyplk'         : grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_paallysteen-korjausluokka", auth_token),
                                #'urakat'       : grouped_by_tie("kohdeluokka_urakka_maanteiden-hoitourakka", auth_token),
                                'toiml'         : grouped_by_tie("kohdeluokka_kansalliset-luokitukset_toiminnallinen-luokka", auth_token),
                                'vluonne'       : grouped_by_tie("kohdeluokka_liikennetekninen-luokitus_vaylan-luonne", auth_token),
                        }

                self.paths = {
                        'kplk'          : ["ominaisuudet", "talvihoitoluokka"],
                        'viherlk'       : ["ominaisuudet", "viherhoitoluokka"],
                        # ---
                        
                        'kaistapa'      : {
                                'sidotut'          : ["ominaisuudet", "paallysteen-tyyppi"],
                                'sitomattomat'     : ["ominaisuudet", "runkomateriaali"],
                                'ladottavat'       : ["ominaisuudet", "materiaali"],
                                'pintaukset'       : ["ominaisuudet", "pintauksen-tyyppi"],
                        #        'kasvillisuudet '  : ["ominaisuudet", "materiaali"],
                        },
                        # --- 
                        'toiml'         : ["ominaisuudet", "toiminnallinen-luokka"],
                        'soratielk'     : ["ominaisuudet", "soratieluokka"],
                        'pyplk'         : ["ominaisuudet", "paallysteen-korjausluokka"],
                        #'urakat'       : grouped_by_tie("kohdeluokka_urakka_maanteiden-hoitourakka", auth_token),
                        'toiml'         : ["ominaisuudet", "toiminnallinen-luokka"],
                        'vluonne'       : ["ominaisuudet", "vaylan-luonne"],
                }

        def to_roadparts(self):
                for key,value in self.kohdeluokat.items(): 
                        if key != 'tieosat':
                                for tie, object in value.items(): 
                                        for obj in object:
                                                if tie in self.kohdeluokat['tieosat']:
                                                        new_parts = split_at_parts(self.kohdeluokat['tieosat'][tie], obj)
                                                        if len(new_parts) > 1:
                                                                object.remove(obj)
                                                                for b in new_parts: 
                                                                        object.append(b)



        
        def find_kaistapaallyste(self, prev_result, enkoodattu_alku, enkoodattu_loppu):
                kaistapaallyste = None
                try: 
                        sidotut_rakenteet = finder_encoded(
                                                self.kohdeluokat['kaistapa']['sidotut'].get(prev_result['tie']) or [], 
                                                prev_result['tie'],
                                                enkoodattu_alku, 
                                                enkoodattu_loppu, 
                                                self.paths['kaistapa']['sidotut'][0], 
                                                self.paths['kaistapa']['sidotut'][1], 
                                                prev_result
                                                )
                        if sidotut_rakenteet:
                                kaistapaallyste = sidotut_rakenteet
                        else:
                                sitomattomat_rakenteet = finder_encoded(self.kohdeluokat['kaistapa']['sitomattomat'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['sitomattomat'][0], self.paths['kaistapa']['sitomattomat'][1], prev_result)
                                if sitomattomat_rakenteet:
                                        kaistapaallyste = sitomattomat_rakenteet
                                else: 
                                        ladottavat_rakenteet = finder_encoded(self.kohdeluokat['kaistapa']['ladottavat'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['ladottavat'][0], self.paths['kaistapa']['ladottavat'][1], prev_result)
                                        if ladottavat_rakenteet:
                                                kaistapaallyste = ladottavat_rakenteet
                                        else:
                                                pintaukset = finder_encoded(self.kohdeluokat['kaistapa']['pintaukset'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['pintaukset'][0], self.paths['kaistapa']['pintaukset'][1], prev_result)
                                                if pintaukset:
                                                        kaistapaallyste = pintaukset
                                                #else: 
                                                #        kasvillisuudet = finder_encoded(self.kohdeluokat['kaistapa']['kasvillisuudet'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['kasvillisuudet'][0], self.paths['kaistapa']['kasvillisuudet'][1])
                                                #        if kasvillisuudet:
                                                #                kaistapaallyste = kasvillisuudet
                        return kaistapaallyste
                except: 
                        return None

        def next_key(self, temp, key): 
                try:
                        temp = list(temp.keys())
                        i = 0 
                        while i < len(temp):
                                if temp[i] == key:
                                        return temp[i+1] 
                                i += 1
                        return None
                except: 
                        return None
                        
        # Finder encoded saataa suurentaa vanhoja aet ja let välejä jos uuden kohdaluokan pituus on suurempi kuin aikasemman
        # Rivien määrä : n. 5433
        def generate_rows(self, prev_result, obj_type, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, rows):
                #result_list = []
                try: 
                        if obj_type != 'kaistapa':
                                # Haetaan kohdeluokan objecti lista
                                cur = self.kohdeluokat[obj_type]
                                # Etsitään kohdeluokan objecti listasta objectit jotka ovat tietyllä enkoodatulla välillä
                                #print("here")
                                found_objects_on_span = []
                                cur_result = copy.deepcopy(prev_result)
                                #print("Alkuperäinen: Osa: " + str(cur_result['aosa']) + " Aet: " + str(cur_result['aet']) + " Let: " + str(cur_result['let']) + " Enka: " + str(enkoodattu_alku) + " Enkl: " + str(enkoodattu_loppu))
                                found_objects_on_span = finder_encoded(cur.get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, cur_result)
                                # Jos objectejä löytyy
                                if found_objects_on_span:
     

                                        #print("-------------------ennen------------------")
                                        # Käydään objectit läpi
                                        for kohdeluokka in found_objects_on_span:
                                                #print(kohdeluokka)
                                                if kohdeluokka["enkoodattu_alku"] != kohdeluokka["enkoodattu_loppu"]:
                                                        # Kopioidaan kohdeluokka objecti ettei se muutu
                                                        obj = copy.deepcopy(kohdeluokka)
                                                        # Kopioidaan vanha result jottei se muutu
                                                        new_result = copy.deepcopy(prev_result)
                                                        # Täytetään kohdeluokan objectin tiedot uuteen resulttiin
                                                        new_result['aet'] = obj['aet']
                                                        new_result['let'] = obj['let']
                                                        new_result['pituus'] = obj['enkoodattu_loppu'] - obj['enkoodattu_alku']
                                                        new_result[obj_type] = obj['value']
                                                        # Haetaan seuraavan kohdeluokan avain
                                                        next_type = copy.deepcopy(self.next_key(prev_result, obj_type))
                                                        #print(next_type)
                                                        #time.sleep(1)
                                                        # Kutsutaan uudestaan generate_rows funktiota, uudella resultilla sekä uudella kohdeluokalla
                                                        if next_type and next_type != 'kaistapa': 
                                                                self.generate_rows(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], self.paths[next_type][0], self.paths[next_type][1], rows)
                                                        elif next_type and next_type == 'kaistapa':
                                                                self.generate_rows(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], None, None, rows)
                                                        # Jos seuraavaa kohdeluokkaa ei ole, lisätään tulos listaan 
                                                        else:
                                                                print("------------------------tyhjä-------------------------------")
                                                                rows.append(new_result)

                                        #print("-------------------jälkeen-------------------")
                                else: 
                                        next_type = self.next_key(prev_result, obj_type)
                                        #print("Alempana: ")
                                        #print(next_type)
                                        if next_type and next_type != 'kaistapa': 
                                                self.generate_rows(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, self.paths[next_type][0], self.paths[next_type][1], rows)
                                        elif next_type and next_type == 'kaistapa':
                                                self.generate_rows(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, None, None, rows)
                                        else:   

                                                #print("here")
                                                rows.append(prev_result)
                        
                        else: 
                                kaistapaallyste = self.find_kaistapaallyste(prev_result, enkoodattu_alku, enkoodattu_loppu)
                                if kaistapaallyste: 
                                        for kohdeluokka in kaistapaallyste:
                                                new_result = copy.deepcopy(prev_result)
                                                obj = copy.deepcopy(kohdeluokka)
                                                new_result['aet'] = obj['aet']
                                                new_result['let'] = obj['let']
                                                new_result['pituus'] = obj['enkoodattu_loppu'] - obj['enkoodattu_alku']
                                                new_result[obj_type] = obj['value']

                                                next_type = self.next_key(prev_result, obj_type)
                                                if next_type: 
                                                        self.generate_rows(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], self.paths[next_type][0], self.paths[next_type][1], rows)
                                                else:
                                                        rows.append(new_result)
                                else:
                                        next_type = self.next_key(prev_result, obj_type)
                                        if next_type: 
                                                self.generate_rows(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, self.paths[next_type][0], self.paths[next_type][1], rows)
                                        else:
                                                rows.append(prev_result)
                except Exception as e: 
                        print('In CSV Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)


        def writable_objects(self):
                # Initialize results list to store writable objects
                results = []

                # Use "tieosat" class as starting class
                all_roads = self.kohdeluokat["tieosat"] 
                #for road in obj_list.values():
                for number, road in all_roads.items():
                        for part in road: 
                                obj     = copy.deepcopy(part) 
                                tie     = obj["tie"]
                                aosa    = obj["osa"]
                                losa    = obj["osa"]
                                e_alku  = obj["enkoodattu-alku"]

                                hal_luokat = obj["hallinnolliset-luokat"]
                                # It is possible to have multiple "hallinnollinen-luokka" in one part of road so iterate over those
                                for hal_luokka in hal_luokat:
                                        aet = hal_luokka["alku-m"]
                                        let = hal_luokka["loppu-m"]
                                        pituus  = let-aet
                                        enkoodattu_alku = e_alku + aet
                                        enkoodattu_loppu = e_alku + let
                                        result = {
                                                'tie'           : tie,
                                                'aosa'          : aosa,
                                                'aet'           : aet,
                                                'losa'          : losa,
                                                'let'           : let,
                                                'pituus'        : pituus,
                                                'tiety'         : hal_luokka["hallinnollinen-luokka"].split('/')[1],
                                                'vluonne'       : None,
                                                'toiml'         : None,
                                                'kplk'          : None,
                                                'viherlk'       : None,
                                                'kaistapa'      : None,
                                                'pyplk'         : None,
                                                'soratielk'     : None
                                        }

                                        # Call recursive function to fill missing classes 
                                        self.generate_rows(copy.deepcopy(result), 'vluonne', enkoodattu_alku, enkoodattu_loppu, self.paths['vluonne'][0], self.paths['vluonne'][1], results)
                        
                return results

        def write_and_run(self):
                self.to_roadparts()
                writables = self.writable_objects()
                date = datetime.today().strftime('%d-%m-%Y')
                filename = date + "-tieosat.csv"
                with open(filename, 'w', newline='') as csvfile:
                        fieldnames = [
                                'tie',
                                'aosa',
                                'aet',
                                'losa',
                                'let',
                                'pituus',
                                'tiety',
                                'vluonne',
                                'toiml',
                                'kplk',
                                'viherlk',
                                'kaistapa',
                                'pyplk',
                                'soratielk'
                        ]

                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                        writer.writeheader()
                        for record in writables:
                                writer.writerow(record)

                return filename

                
        

