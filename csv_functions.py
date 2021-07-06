import csv
import time, datetime
from datetime import datetime
from helpers import kohdeluokka_dict, grouped_by_tie, get_token,  finder_encoded, check_ominaisuus_tarkenne_in_obj


# Enkoodaus 100 milj * tienum + pituus 
# Enkoodaus 300008782 = tie 3 etaisyys 8782
# loppu alun jälkeen, loppu ennen alkua
# alku inklusiivinen loppu ekslusiivinen

def encode(tie, etaisyys):
        return 100000000 * tie + etaisyys


# loppu alun jälkeen, loppu ennen alkua
# alku inklusiivinen loppu ekslusiivinen

def encoded_in_range(obj_alku, obj_loppu, vertailtava_alku, vertailtava_loppu):
        if obj_alku <= vertailtava_loppu and obj_loppu > vertailtava_alku:
                return True
        else: 
                return False

# Etsii listasta objectin, joka täyttää vaatimukset ja palauttaa joko obj[ominaisuus] tai obj[ominaisuus][tarkenne]
# Esim. tieosan hallinnollisen luokan (tieosa/ominaisuudet/hallinnollinen-luokka) joka osuu tietylle tie/osa välille
# obj_list = kohdeluokan objectit listana
# tie = haettava tie
# aosa = alun osa, aet = alun etäisyys, losa = lopun osa (jos kaksi sijaintia), let = lopun etäisyys
# Objectit ovat dict muotoisia, jolloin ominaisuudella viitataan ensimmäiseen obj[__tahan__] hakuun (yleensä "ominaisuudet")
# Tarkenne on sitten obj[ominaisuus][tarkenne] jos obj[ominaisuus] on myös dict muotoa
# Jos tarkenne == None, palauttaa obj[ominaisuus]
# Jos ominaisuus == None, palauttaa objectin

# Hyödyntää teiden ja tieosien sijaan enkoodattuja sijainteja, muuten sama kuin finder

def finder_encoded(obj_list, tie, enkoodattu_alku, enkoodattu_loppu, ominaisuus, tarkenne):
        if not obj_list: 
                return None
        for obj in obj_list:
                if "sijainnit" in obj:
                        for sijainti in obj["sijainnit"]:
                                alkusijainti  = sijainti["alkusijainti"]
                                loppusijainti = sijainti["loppusijainti"]
                                if "enkoodattu" in alkusijainti:
                                        obj_alku  = alkusijainti["enkoodattu"]
                                        obj_loppu = loppusijainti["enkoodattu"]
                                        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                else: 
                                        obj_alku  = encode(alkusijainti["tie"], alkusijainti["osa"])
                                        obj_loppu = encode(loppusijainti["tie"], loppusijainti["osa"])
                                        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                '''
                                if alkusijainti["tie"] == tie and loppusijainti["tie"] == tie:
                                        return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                                '''

                elif "alkusijainti" in obj and "loppusijainti" in obj:
                        obj_alku  = obj["alkusijainti"]["enkoodattu"]
                        obj_loppu = obj["loppusijainti"]["enkoodattu"]
                        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)
                
                elif "tie" in obj: 
                        obj_alku  = obj["enkoodattu-alku"]
                        obj_loppu = obj["enkoodattu-loppu"]
                        if encoded_in_range(enkoodattu_alku, enkoodattu_loppu, obj_alku, obj_loppu):
                                return check_ominaisuus_tarkenne_in_obj(obj, ominaisuus, tarkenne)

# Hyödyntää enkoodattuja sijainteja teiden ja tieosien sijaan.
# Jos enkoodattua sijaintia ei ole, oletetaan että kohdeluokka kattaa koko tien. 
def tieosat_csv_encoded():
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
                        e_alku  = record["enkoodattu-alku"]
                        e_loppu = record["enkoodattu-loppu"]
                        aet     = record["alun-etaisyys-tien-alusta"]
                        let     = record["lopun-etaisyys-tien-alusta"]
                        pituus  = record["pituus"]

                        # Haetaan pohjavesi ennen kirjoittamista, sillä sitä käytetään useaan kenttään
                        pohjavesi = finder_encoded(grouped_pohjavedet.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", None)

                        # Haetaan sidotut päällysrakenteet ennen kirjoittamista, sillä objectin kaistan vertailulle pitää muodostaa if lause
                        sidotut_rakenteet = finder_encoded(grouped_sidotut.get(tie) or [], tie, e_alku, e_loppu, None, None)
                        sidotut_rakenteet_tyyppi = None 
                        if sidotut_rakenteet and "sijaintitarkenne" in sidotut_rakenteet:
                                if sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 11 or sidotut_rakenteet["sijaintitarkenne"]["kaista"] == 21: 
                                        sidotut_rakenteet_tyyppi = sidotut_rakenteet["ominaisuudet"]["paallysteen-tyyppi"].split("/")[1]
                                
                        #Haetaan kaista ennen kirjoittamista, sillä sen ominaisuustieto vaatii kolme avainta: obj[avain][avain][avain]
                        alev_rakenteelliset = finder_encoded(grouped_kaistat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "rakenteelliset-ominaisuudet")
                        alev = None
                        if alev_rakenteelliset: 
                                alev = alev_rakenteelliset["leveys"]

                        # Kaistapaallyste voidaan hakea useasta kohdeluokasta. Käydään kohdeluokat läpi yksikerrallaan, jotta ei tarvitse käyä niitä kaikkia läpi, jos haluttu tulos löytyy aiemmasta kohdeluokasta
                        kaistapaallyste = None
                        if sidotut_rakenteet_tyyppi:
                                kaistapaallyste = sidotut_rakenteet_tyyppi
                        else:
                                sitomattomat_rakenteet = finder_encoded(grouped_sitomattomat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "runkomateriaali")
                                if sitomattomat_rakenteet:
                                        kaistapaallyste = sitomattomat_rakenteet
                                else: 
                                        ladottavat_rakenteet = finder_encoded(grouped_ladottavat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "materiaali")
                                        if ladottavat_rakenteet:
                                                kaistapaallyste = ladottavat_rakenteet
                                        else:
                                                pintaukset = finder_encoded(grouped_pintaukset.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "pintauksen-tyyppi")
                                                if pintaukset:
                                                        kaistapaallyste = pintaukset
                                                else: 
                                                        kasvillisuudet = finder_encoded(grouped_kasvillisuudet.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "materiaali")
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
                                'tiety'         :  finder_encoded(grouped_tieosat.get(tie) or [], tie, e_alku, e_loppu, "hallinnolliset-luokat", "hallinnollinen-luokka"),
                                'kunta'         : None, #Ei ole?
                                'ualue'         :  finder_encoded(grouped_urakat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "urakkakoodi"),
                                'tualue'        : None,
                                'vluonne'       :  finder_encoded(grouped_vaylanluonteet.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "vaylan-luonne"),
                                'toiml'         :  finder_encoded(grouped_toimluokitukset.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "toiminnallinen-luokka"),
                                'kplk'          :  finder_encoded(grouped_talvihoitoluokat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "talvihoitoluokka"),
                                'viherlk'       :  finder_encoded(grouped_viherhoitoluokat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "viherhoitoluokka"),
                                'alev'          : alev, #confluence laske leveys
                                'kaistapa'      : kaistapaallyste, #Yhdistä tähän pt, spr ja pintaukset/pintaustyyppi ja ladottavat pintarakenteet/kivenmateriaali?
                                'pyplk'         :  finder_encoded(grouped_korjausluokat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "paallysteen-korjausluokka"),
                                'soratielk'     :  finder_encoded(grouped_soratiet.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "soratieluokka")
                        })
