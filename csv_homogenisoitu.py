import csv
import time, datetime
from datetime import datetime
from helpers import grouped_by_tie, get_token,  finder_encoded, split_at_parts
import sys

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
                                        'kasvillisuudet '  : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_kasvillisuusrakenteet", auth_token)
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
                                'kasvillisuudet '  : ["ominaisuudet", "materiaali"],
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
                                                        obj = split_at_parts(self.kohdeluokat['tieosat'][tie], obj)

        def find_kaistapaallyste(self, prev_result, enkoodattu_alku, enkoodattu_loppu):
                kaistapaallyste = None
                try: 
                        sidotut_rakenteet = finder_encoded(self.kohdeluokat['kaistapa']['sidotut'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['sidotut'][0], self.paths['kaistapa']['sidotut'][1])
                        if sidotut_rakenteet:
                                kaistapaallyste = sidotut_rakenteet
                        else:
                                sitomattomat_rakenteet = finder_encoded(self.kohdeluokat['kaistapa']['sitomattomat'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['sitomattomat'][0], self.paths['kaistapa']['sitomattomat'][1])
                                if sitomattomat_rakenteet:
                                        kaistapaallyste = sitomattomat_rakenteet
                                else: 
                                        ladottavat_rakenteet = finder_encoded(self.kohdeluokat['kaistapa']['ladottavat'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['ladottavat'][0], self.paths['kaistapa']['ladottavat'][1])
                                        if ladottavat_rakenteet:
                                                kaistapaallyste = ladottavat_rakenteet
                                        else:
                                                pintaukset = finder_encoded(self.kohdeluokat['kaistapa']['pintaukset'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['pintaukset'][0], self.paths['kaistapa']['pintaukset'][1])
                                                if pintaukset:
                                                        kaistapaallyste = pintaukset
                                                else: 
                                                        kasvillisuudet = finder_encoded(self.kohdeluokat['kaistapa']['kasvillisuudet'].get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, self.paths['kaistapa']['kasvillisuudet'][0], self.paths['kaistapa']['kasvillisuudet'][1])
                                                        if kasvillisuudet:
                                                                kaistapaallyste = kasvillisuudet
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
        

        def current_object(self, prev_result, obj_type, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne):
                result = []
                try: 
                        if obj_type != 'kaistapa':
                                cur = self.kohdeluokat[obj_type]
                                class_obj = finder_encoded(cur.get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne)
                                if class_obj:
                                        print(len(class_obj))
                                        for obj in class_obj:
                                                #print(str(prev_result['aosa']) + " and aet " + str(obj['aet']) + " and let " + str(obj['let']))
                                                new_result = prev_result
                                                new_result['aet'] = obj['aet']
                                                new_result['let'] = obj['let']
                                                new_result['pituus'] = obj['enkoodattu_loppu'] - obj['enkoodattu_alku']
                                                new_result[obj_type] = obj['value']

                                                next_type = self.next_key(prev_result, obj_type)
                                                
                                                if next_type and next_type != 'kaistapa': 
                                                        self.current_object(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], self.paths[next_type][0], self.paths[next_type][1])
                                                elif next_type and next_type == 'kaistapa':
                                                        self.current_object(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], None, None)
                                                else:
                                                        result.append(new_result)
                                else: 
                                        next_type = self.next_key(prev_result, obj_type)
                                        if next_type and next_type != 'kaistapa': 
                                                self.current_object(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, self.paths[next_type][0], self.paths[next_type][1])
                                        elif next_type and next_type == 'kaistapa':
                                                self.current_object(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, None, None)
                                        else:
                                                result.append(prev_result)
                        
                        else: 

                                kaistapaallyste = self.find_kaistapaallyste(prev_result, enkoodattu_alku, enkoodattu_loppu)
                                if kaistapaallyste: 
                                        for obj in kaistapaallyste:
                                                new_result = prev_result

                                                new_result['aet'] = obj['aet']
                                                new_result['let'] = obj['let']
                                                new_result['pituus'] = obj['enkoodattu_loppu'] - obj['enkoodattu_alku']
                                                new_result[obj_type] = obj['value']

                                                next_type = self.next_key(prev_result, obj_type)
                                                if next_type: 
                                                        self.current_object(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], self.paths[next_type][0], self.paths[next_type][1])
                                                else:
                                                        result.append(new_result)
                except Exception as e: 
                        print('In CSV Error on line {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

                if not result: 
                        result.append(prev_result)

                return result        



        def writable_objects(self):
                # Initialize results list to store writable objects
                results = []

                # Use "tieosat" class as starting class
                obj_list = self.kohdeluokat["tieosat"] 
                #for road in obj_list.values():
                road = obj_list[1]
                for obj in road:  
                        tie     = obj["tie"]
                        aosa    = obj["osa"]
                        losa    = obj["osa"]
                        e_alku  = obj["enkoodattu-alku"]
                        e_loppu = obj["enkoodattu-loppu"]
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
                                recursion = self.current_object(result, 'vluonne', enkoodattu_alku, enkoodattu_loppu, self.paths['vluonne'][0], self.paths['vluonne'][1])

                                # current_object is recursive function that might return more than one result so iterate over returned values and add them to list
                                for r in recursion:
                                        if r:
                                                results.append(r)
                
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
                                if type(record) == type([]):
                                        for r in record:
                                                writer.writerow(record)
                                else: 
                                        writer.writerow(record)

                
        

