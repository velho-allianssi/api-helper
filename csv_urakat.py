import csv
import time, datetime
from datetime import datetime
from helpers import kohdeluokka_dict, grouped_by_tie, get_token,  finder_encoded

# Hyödyntää enkoodattuja sijainteja teiden ja tieosien sijaan.
# Jos enkoodattua sijaintia ei ole, oletetaan että kohdeluokka kattaa koko tien. 
def urakat_csv_encoded():
        data = kohdeluokka_dict("kohdeluokka_sijainti_tieosa")
        content = data[0]
        date = datetime.today().strftime('%d-%m-%Y')
        filename = date + "-urakat.csv"
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

                grouped_tieosat             = grouped_by_tie("kohdeluokka_sijainti_tieosa", auth_token)
                grouped_talvihoitoluokat    = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_talvihoitoluokka", auth_token)
                grouped_viherhoitoluokat    = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_viherhoitoluokka", auth_token)
                grouped_sidotut             = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sidotut-paallysrakenteet", auth_token)
                grouped_sitomattomat        = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_sitomattomat-pintarakenteet", auth_token)
                grouped_ladottavat          = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_ladottavat-pintarakenteet", auth_token)
                grouped_pintaukset          = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_pintaukset", auth_token)
                grouped_kasvillisuudet      = grouped_by_tie("kohdeluokka_paallyste-ja-pintarakenne_kasvillisuusrakenteet", auth_token)
                grouped_pohjavedet          = grouped_by_tie("kohdeluokka_alueet_pohjavesialueet", auth_token)
                grouped_soratiet            = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_soratieluokka", auth_token)
                grouped_korjausluokat       = grouped_by_tie("kohdeluokka_kunnossapitoluokitukset_paallysteen-korjausluokka", auth_token)
                grouped_urakat              = grouped_by_tie("kohdeluokka_urakka_maanteiden-hoitourakka", auth_token)
                grouped_palvelusopimukset   = grouped_by_tie("kohdeluokka_urakka_palvelusopimus", auth_token)
                grouped_toimluokitukset     = grouped_by_tie("kohdeluokka_kansalliset-luokitukset_toiminnallinen-luokka", auth_token)
                grouped_kaistat             = grouped_by_tie("kohdeluokka_tiealueen-poikkileikkaus_kaistat", auth_token)
                grouped_vaylanluonteet      = grouped_by_tie("kohdeluokka_liikennetekninen-luokitus_vaylan-luonne", auth_token)

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
                                        parts = sidotut_rakenteet["ominaisuudet"]["paallysteen-tyyppi"].split("/")
                                        sidotut_rakenteet_tyyppi = parts[1]
                                
                        #Haetaan kaista ennen kirjoittamista, sillä sen ominaisuustieto vaatii kolme avainta: obj[avain][avain][avain]
                        alev_rakenteelliset = finder_encoded(grouped_kaistat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "rakenteelliset-ominaisuudet")
                        alev = None
                        if alev_rakenteelliset: 
                                alev = alev_rakenteelliset["leveys"]

                        # Kaistapaallyste voidaan hakea useasta kohdeluokasta. Käydään kohdeluokat läpi yksikerrallaan, jotta ei tarvitse käyä niitä kaikkia läpi, jos haluttu tulos löytyy aiemmasta kohdeluokasta
                        kaistapaallyste = None
                        if sidotut_rakenteet:
                                kaistapaallyste = sidotut_rakenteet["ominaisuudet"]["paallysteen-tyyppi"].split("/")[1]
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
                        
                        # Haetaan myös urakat ennen kirjottamista, sillä niitä käytetään useaan kenttään
                        urakka = None
                        maantieurakka = finder_encoded(grouped_urakat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "urakkakoodi")
                        if maantieurakka: 
                            urakka = maantieurakka
                        else: 
                            urakka = finder_encoded(grouped_palvelusopimukset.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "urakkakoodi")

                        writer.writerow({
                                'tilannepvm'    : None,
                                'tie'           : tie,
                                'ajr'           : None,
                                'aosa'          : aosa,
                                'aet'           : aet,
                                'losa'          : losa,
                                'let'           : let,
                                'pituus'        : pituus,
                                'tiety'         : finder_encoded(grouped_tieosat.get(tie) or [], tie, e_alku, e_loppu, "hallinnolliset-luokat", "hallinnollinen-luokka"),
                                'kunta'         : None, #Ei ole?
                                'ualue'         : urakka,
                                'tualue'        : None,
                                'vluonne'       : finder_encoded(grouped_vaylanluonteet.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "vaylan-luonne"),
                                'toiml'         : finder_encoded(grouped_toimluokitukset.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "toiminnallinen-luokka"),
                                'kplk'          : finder_encoded(grouped_talvihoitoluokat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "talvihoitoluokka"),
                                'viherlk'       : finder_encoded(grouped_viherhoitoluokat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "viherhoitoluokka"),
                                'alev'          : alev, #confluence laske leveys
                                'kaistapa'      : kaistapaallyste, #Yhdistä tähän pt, spr ja pintaukset/pintaustyyppi ja ladottavat pintarakenteet/kivenmateriaali?
                                'pyplk'         : finder_encoded(grouped_korjausluokat.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "paallysteen-korjausluokka"),
                                'soratielk'     : finder_encoded(grouped_soratiet.get(tie) or [], tie, e_alku, e_loppu, "ominaisuudet", "soratieluokka")
                        })
