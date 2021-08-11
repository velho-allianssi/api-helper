import csv
import time, datetime
from datetime import datetime
from helpers import grouped_by_tie, get_token,  finder_encoded, split_at_parts
import sys
import copy
import pandas as pd
from iteration_utilities import unique_everseen
# Muuttujien nimet selkeämmäksi esim enkoodattu_alku => enkoodattu_alku

class CsvLinearReference:
        def __init__(self, options):
                auth_token = str(get_token())
                self.kohdeluokat = {
                                'tieosat'       : grouped_by_tie("kohdeluokka_sijainti_tieosa", auth_token),
                                'kplk'          : grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_talvihoitoluokka", auth_token),
                                'viherlk'       : grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_viherhoitoluokka", auth_token),
                                'kaistapa'      : {
                                        'sidotut'          : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sidotut-paallysrakenteet", auth_token),
                                        'sitomattomat'     : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sitomattomat-pintarakenteet", auth_token),
                                        'ladottavat'       : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_ladottavat-pintarakenteet", auth_token),
                                        'pintaukset'       : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_pintaukset", auth_token),
                                #        'kasvillisuudet '  : grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_kasvillisuusrakenteet", auth_token)
                                },
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
                        'kaistapa'      : {
                                'sidotut'          : ["ominaisuudet", "paallysteen-tyyppi"],
                                'sitomattomat'     : ["ominaisuudet", "runkomateriaali"],
                                'ladottavat'       : ["ominaisuudet", "materiaali"],
                                'pintaukset'       : ["ominaisuudet", "pintauksen-tyyppi"],
                        #        'kasvillisuudet '  : ["ominaisuudet", "materiaali"],
                        },
                        'toiml'         : ["ominaisuudet", "toiminnallinen-luokka"],
                        'soratielk'     : ["ominaisuudet", "soratieluokka"],
                        'pyplk'         : ["ominaisuudet", "paallysteen-korjausluokka"],
                        #'urakat'        : ["ominaisuudet", "urakka-koodi"],
                        'toiml'         : ["ominaisuudet", "toiminnallinen-luokka"],
                        'vluonne'       : ["ominaisuudet", "vaylan-luonne"],
                }
                
                self.options = options

        def to_roadparts(self):
                for key,value in self.kohdeluokat.items(): 
                        if key != 'tieosat' and key != 'kaistapa':
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
                        
        def generate_rows(self, prev_result, obj_type, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, rows):
                try: 
                        if obj_type != 'kaistapa':
                                # Haetaan kohdeluokan objecti lista
                                cur = self.kohdeluokat[obj_type]
                                # Etsitään kohdeluokan objecti listasta objectit jotka ovat tietyllä enkoodatulla välillä
                                found_objects_on_span = []
                                cur_result = copy.deepcopy(prev_result)
                                found_objects_on_span = finder_encoded(cur.get(prev_result['tie']) or [], prev_result['tie'], enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne, cur_result)
                                # Jos objectejä löytyy
                                if found_objects_on_span:
                                        # Käydään objectit läpi
                                        for kohdeluokka in found_objects_on_span:
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
                                                        # Kutsutaan uudestaan generate_rows funktiota, uudella resultilla sekä uudella kohdeluokalla
                                                        if next_type and next_type != 'kaistapa': 
                                                                self.generate_rows(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], self.paths[next_type][0], self.paths[next_type][1], rows)
                                                        elif next_type and next_type == 'kaistapa':
                                                                self.generate_rows(new_result, next_type, obj['enkoodattu_alku'], obj['enkoodattu_loppu'], None, None, rows)
                                                        # Jos seuraavaa kohdeluokkaa ei ole, lisätään tulos listaan 
                                                        else:
                                                                rows.append(new_result)
                                else: 
                                        next_type = self.next_key(prev_result, obj_type)
                                        if next_type and next_type != 'kaistapa': 
                                                self.generate_rows(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, self.paths[next_type][0], self.paths[next_type][1], rows)
                                        elif next_type and next_type == 'kaistapa':
                                                self.generate_rows(prev_result, next_type, enkoodattu_alku, enkoodattu_loppu, None, None, rows)
                                        else:   
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
                                                #'vluonne'       : None,
                                                #'toiml'         : None,
                                                #'kplk'          : None,
                                                #'viherlk'       : None,
                                                #'kaistapa'      : None,
                                                #'pyplk'         : None,
                                                #'soratielk'     : None
                                        }
                                        for option in self.options: 
                                                result[option] = None
              
                                        # Call recursive function to fill missing classes
                                        start_type = self.next_key(result, 'tiety') 
                                        self.generate_rows(copy.deepcopy(result), start_type, enkoodattu_alku, enkoodattu_loppu, self.paths[start_type][0], self.paths[start_type][1], results)
                                        #self.generate_rows(copy.deepcopy(result), 'vluonne', enkoodattu_alku, enkoodattu_loppu, self.paths['vluonne'][0], self.paths['vluonne'][1], results)
                        
                return results

        def combine_two_rows(self,row1, row2):
                row1 = copy.deepcopy(row1)
                row2 = copy.deepcopy(row2)
                keys = [
                        'tiety',
                        'vluonne',
                        'toiml',
                        'kplk',
                        'viherlk',
                        'kaistapa',
                        'pyplk',
                        'soratielk'
                ]
                if row1['tie'] == row2['tie'] and row1['aosa'] == row2['aosa']:
                        '''
                        if row1['aet'] == row2['aet']:
                                if row1['let'] < row2['let']:
                                        for key in keys:
                                                if row1[key] != row2[key]:
                                                        return None
                                        new_row = row1
                                        new_row['let'] = row2['let']
                                else: 
                                        for key in keys:
                                                if row1[key] != row2[key]:
                                                        return None
                                        new_row = row1
                                        new_row['let'] = row1['let']
                                return new_row
                        '''
                        if row1['let'] <= row2['let']:
                                for key in keys:
                                        if row1[key] != row2[key]:
                                                return None
                                new_row = row1
                                new_row['let'] = row2['let']
                                new_row['pituus'] = new_row['let'] - new_row['aet']
                                return new_row
                        elif row1['let'] > row2['let']:
                                for key in keys:
                                        if row1[key] != row2[key]:
                                                return None
                                new_row = row1
                                return new_row
                        else: 
                                return None

                return None

        def combine_rows_loop(self,rows):
                new_rows = []
                i = 1 
                cur_row = rows[0]
                while i < len(rows):

                        row2 = rows[i]
                        combined = self.combine_two_rows(cur_row,row2)
                        if combined:
                                cur_row = combined
                        else: 
                                new_rows.append(cur_row)
                                cur_row = copy.deepcopy(row2)

                        i += 1
                return new_rows
                        
        #Etsi kaikki uniikit merkitsevät tiedot eli tie,aosa,pituus,tiety jne / ei aet, let, pituus
        #Palautettava set sisältää listoja (dictejä ei voi käyttää koska ne eivät ole "hashable")
        #Listat ovat muotoa [tie, aosa, tiety, vluonne, toiml, kplk, viherlk, kaistapa, pyplk, soratielk]
        #---------------------------------
        def to_meaningful_sets(self, rows):
                unique_data = set()
                for row in rows:
                        '''
                        current_data = (
                                row['tie'],
                                row['aosa'],
                                row['tiety'],
                                row['vluonne'],
                                row['toiml'],
                                row['kplk'],
                                row['viherlk'],
                                row['kaistapa'],
                                row['pyplk'],
                                row['soratielk']
                        )  
                        '''
                        base_data = [
                                row['tie'],
                                row['aosa'],
                                row['tiety']
                        ]
                        for opt in self.options:
                                base_data.append(row[opt])
                        current_data = tuple(base_data)

                        unique_data.add(current_data)

                return unique_data

        def filter_check_meaningful_data(self, row, data):
                base_data = [
                        row['tie'],
                        row['aosa'],
                        row['tiety']
                ]
                for opt in self.options:
                        base_data.append(row[opt])
                row_data = tuple(base_data)
                '''
                row_data = (
                        row['tie'],
                        row['aosa'],
                        row['tiety'],
                        row['vluonne'],
                        row['toiml'],
                        row['kplk'],
                        row['viherlk'],
                        row['kaistapa'],
                        row['pyplk'],
                        row['soratielk']
                )
                '''
                return row_data == data


        def group_meaningful_data(self, rows):
                grouped_rows = {}
                for row in rows: 
                        if row['tie'] in grouped_rows:
                                cur = grouped_rows[row['tie']]
                                cur.append(row)
                                grouped_rows[row['tie']] = cur
                        else: 
                                grouped_rows[row['tie']] = []
                                grouped_rows[row['tie']].append(row)

                return grouped_rows


        def combine_meaningful_data(self, row_list):

                # rekursiivinen sisäfunktio
                # palauttaa rivin jos sille ei löydy enää yhdisteltäviä rivejä
                def inner_combiner(aet_row, row_list):
                        let = aet_row['let']
                        next_row = next((row for row in row_list if row['aet'] == let), None)
                        if next_row: 
                                aet_row['let'] = next_row['let']
                                row_list.remove(next_row)
                                aet_row = inner_combiner(aet_row, row_list)
                        else: 
                                return aet_row

                # ensin käydään läpi aet 0 
                aet_zero: list = list(filter(lambda row: row['aet'] == 0, row_list))
                row_list: list = row_list
                for aet_row in aet_zero:
                        row_list.remove(aet_row) 
                        aet_row = inner_combiner(aet_row, row_list)

        
                for row_left in row_list:
                        row_list.remove(row_left)
                        row_left = inner_combiner(row_left, row_list)
                        aet_zero.append(row_left)
                
                return aet_zero


                        
        #----------------------------------

        def write_and_run(self):
                self.to_roadparts()
                print("writables aika")
                w_start = time.time()
                writables = self.writable_objects()
                w_end = time.time()
                print(w_end-w_start)
                print("-------------------")
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
                                #'vluonne',
                                #'toiml',
                                #'kplk',
                                #'viherlk',
                                #'kaistapa',
                                #'pyplk',
                                #'soratielk'
                        ]
                        fieldnames.extend(self.options)
                        
                        
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                        writer.writeheader()
                        #Poistaa duplikaattii rivit
                        without_duplicates = pd.DataFrame(writables).drop_duplicates().to_dict('records')
                        #Järjestää rivit ensin teiden perusteella, sitten alkuosan ja vielä alun etäisyyden perusteella
                        print("Sorttauksen aika")
                        start_sort = time.time()
                        lista_riveistä = sorted(without_duplicates, key=lambda k: (k['tie'], k['aosa'], k['aet']))
                        sort_end = time.time()
                        print(sort_end - start_sort)
                        print("------------")
                        grouped_rivit = self.group_meaningful_data(lista_riveistä)
                        #combined_writables = self.combine_rows_loop(sorted_writables)
                        #Muodostaa setin joka sisältää uniikit merkitsevät tiedot
                        unique_data = self.to_meaningful_sets(lista_riveistä)
                        
                        #start = time.time()
                        #x = list(filter(lambda row: self.filter_check_meaningful_data(row, (1,3,'t1','valu02', 'toiml01', 'kplk01', None, 'pt02', 'pklk08', None)), lista_riveistä))
                        #print(x)
                        #       
                        #end = time.time()
                        #print(end - start)
  
                        #lista_rivestä ovat muotoa [tie, aosa, tiety, vluonne, toiml, kplk, viherlk, kaistapa, pyplk, soratielk]
                        start = time.time()
                        y = list(map(lambda meaningful_data: list(filter(lambda row: self.filter_check_meaningful_data(row, meaningful_data), grouped_rivit[meaningful_data[0]])),unique_data))
                        sorted_y = sorted(y, key=lambda k: k[0]['tie'])
                        for x in sorted_y:
                                if len(x) > 1: 
                                        x = self.combine_meaningful_data(x)

                        end = time.time()
                        print(end - start)
                        print(sorted_y[0])

                        for record in sorted_y:
                                for record2 in record:
                                        writer.writerow(record2)

                        #Mahdollisesti lista_rivestä (sorted_writables) voisi ryhmitellä teiden mukaan ajon nopeuttamiseksi.
                        #Mapin sisällä olevan filterin voi korvata ns. apu_filterillä, eli toisella functiolla joka kutsuu mahdolisesti filteriä + muuta roskaa.

                return filename

                
        

