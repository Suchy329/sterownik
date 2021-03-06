#!/usr/bin/python
# -*- coding: utf-8 -*-

#==================================================================================
# Algorytm proporcjonalnej korekcji pracy (auto) w trybie retortowym-recznym
# z zalozenia nalezy dobrac tak parametry aby nie wychodzic w podtrzymanie
#
# pomysl algorytmu kol. janusz z forum http://esterownik.pl/forum
# pomysl z korekcjami kol. mark3k
#==================================================================================

# PARAMETRY w pliku konf_retortowy_p.py

# PROGRAM GLOWNY
from sterownik import *
import signal, os, sys, time
if sys.version_info[0] == 3:
  import importlib

rozped = True
try:
  import konf_polaczenie
except ImportError:
  raise ImportError('brak pliku konfiguracji polaczenia ze sterownikiem: konf_polaczenie.py')

c = sterownik(konf_polaczenie.ip, konf_polaczenie.login, konf_polaczenie.haslo);
c.getStatus()

try:
  import konf_retortowy_p as konf
except ImportError:
  raise ImportError('brak pliku konfiguracji parametrow pracy retortowy-P: konf_retortowy_p.py')

from timer import *

def sprawdz_dane():
  global pod_min,pod_max,pos_min,pos_max,dmu_min,dmu_max

  if (konf.praca_ciagla == True):
    c.setZadanaCO(konf.zadana_co+5)
  else:
    c.setZadanaCO(konf.zadana_co)

  if (c.version == "BRULI"):
    pod_min = 2
    pod_max = 180
  else:
    pod_min = 3
    pod_max = 20

  pos_min = 1
  pos_max = 600
  dmu_min = 25
  dmu_max = 100

  if (konf.podawanie_min > 0 and konf.podawanie_min > pod_min): pod_min = konf.podawanie_min
  if (konf.podawanie_max > 0 and konf.podawanie_max < pod_max): pod_max = konf.podawanie_max
  if (konf.postoj_min > 0    and konf.postoj_min > pos_min):    pos_min = konf.postoj_min
  if (konf.postoj_max > 0    and konf.postoj_max < pos_max):    pos_max = konf.postoj_max
  if (konf.dmuchanie_min > 0 and konf.dmuchanie_min > dmu_min): dmu_min = konf.dmuchanie_min
  if (konf.dmuchanie_max > 0 and konf.dmuchanie_max < dmu_max): dmu_max = konf.dmuchanie_max

global kold,knew,nowakonfiguracja
nowakonfiguracja = False

def files_to_timestamp(path):
    files = [os.path.join(path, f) for f in os.listdir(path)]
    return dict ([(f, os.path.getmtime(f)) for f in files])

def konfig():
    wkonf.stop()
    global kold,knew,nowakonfiguracja
    knew = files_to_timestamp(os.path.abspath(os.path.dirname(sys.argv[0])))
    added = [f for f in knew.keys() if not f in kold.keys()]
    removed = [f for f in kold.keys() if not f in knew.keys()]
    modified = []

    for f in kold.keys():
        if not f in removed:
           if os.path.getmtime(f) != kold.get(f):
              modified.append(f)
       
    kold = knew
    for f in modified:
        print modified
        if os.path.isfile(f) and os.path.basename(f) == 'konf_retortowy_p.py':
           nowakonfiguracja = True

    for f in added:
        print added
        if os.path.isfile(f) and os.path.basename(f) == 'konf_retortowy_p.py':
           nowakonfiguracja = True
    
    wkonf.start()


c.setRetRecznyDmuchawa(konf.rozped_dmuchawa)
c.setRetRecznyPostoj(konf.rozped_postoj)
c.setRetRecznyPodawanie(konf.rozped_podawanie)

global pod_min,pod_max,pos_min,pos_max,dmu_min,dmu_max
pod_min=pod_max=pos_min=pos_max=dmu_min=dmu_max=0
sprawdz_dane()

def work():
 wwork.stop();

 tryb_info = False
 delta_ujemna = False
 za_mala_moc = False
 nowa_moc = 0
 poprzednia_co = c.getTempCO()
 poprzednie_dmuchanie = nowe_dmuchanie = konf.rozped_dmuchawa
 poprzednie_postoj = nowe_postoj = konf.rozped_postoj
 poprzednie_podawanie = nowe_podawanie = konf.rozped_podawanie
 poprzednie_opoznienie = 0
 start_czas_podajnika = c.getCzasPodajnika()
 start_czas = time.time()

 while (True):
  c.getStatus()
  if (c.getTrybAuto() and c.getTypKotla() == "RETORTOWY-RECZNY"):
    tryb_info = False
    delta = int(konf.zadana_co - c.getTempCO() +0.5)
    delta_poprzednia = int(poprzednia_co - c.getTempCO() +0.5)
    
    if (delta > 0 or konf.praca_ciagla == True):
      if (delta_ujemna == True and konf.praca_ciagla == True):
        c.setZadanaCO(konf.zadana_co+5)
      delta_ujemna = False
      nowe_podawanie = delta * konf.korekcja_podawania + konf.start_podawanie
      nowe_postoj    = delta * konf.korekcja_postoju   + konf.start_postoj
      nowe_dmuchanie = delta * konf.korekcja_dmuchania + konf.start_dmuchawa
      
      if (nowe_podawanie < 1):
        x = 1-nowe_podawanie
        nowe_podawanie = 1
        nowe_postoj = nowe_postoj + x
      
      nowe_moc = float(nowe_postoj)/float(nowe_podawanie)
      
      if (nowe_podawanie < pod_min):
        nowe_podawanie = pod_min
        nowe_postoj = int(nowe_moc*pod_min)
      if (nowe_podawanie > pod_max):
        nowe_podawanie = pod_max
        nowe_postoj = int(nowe_moc*pod_max)
      if (nowe_postoj    < pos_min): nowe_postoj = pos_min
      if (nowe_postoj    > pos_max): nowe_postoj = pos_max
      if (nowe_dmuchanie < dmu_min): nowe_dmuchanie = dmu_min
      if (nowe_dmuchanie > dmu_max): nowe_dmuchanie = dmu_max
      rozped = True
      rozped = False
    elif (delta < 0 and konf.praca_ciagla == False):
      if (delta_ujemna == False):
        c.setZadanaCO(konf.zadana_co)
        delta_ujemna = True
        
    #  nowe_dmuchanie = konf.rozped_dmuchawa
    #  nowe_postoj = konf.rozped_postoj
    #  nowe_podawanie =konf.rozped_podawanie
    #  rozped = False
    #  print("ROZPED Delta:"+ str(delta)+" dmuchanie:" + str(konf.rozped_dmuchawa) + " podawanie:" + str(konf.rozped_podawanie) + " postoj:" + str(konf.rozped_postoj))
    #else:
    #  print("Delta:"+ str(delta)+" Poprzednia:" + str(delta_poprzednia))

    nowa_moc = 100*(float(nowe_podawanie)/float(nowe_postoj))
    if konf.moc_100 > 0:
      nowa_moc /= konf.moc_100

    if (delta < 0 and konf.praca_ciagla == True):
      if (nowa_moc < konf.moc_min and za_mala_moc == False):
        za_mala_moc = True
        c.setZadanaCO(konf.zadana_co)

    if (nowa_moc >= konf.moc_min and za_mala_moc == True and konf.praca_ciagla == True):
      za_mala_moc = False
      c.setZadanaCO(konf.zadana_co+5)

  else:
    if (tryb_info == False):
      tryb_info = True
      print("Sterownik nie jest w trybie auto lub nie ma wlaczonego trybu RETORTOWY-RECZNY")

  nowe_dane = False
  if (nowe_dmuchanie != poprzednie_dmuchanie):
    c.setRetRecznyDmuchawa(nowe_dmuchanie)
    print(" dmuchanie:" + str(poprzednie_dmuchanie)+"->" + str(nowe_dmuchanie))
    poprzednie_dmuchanie = nowe_dmuchanie
    nowe_dane = True

  if (nowe_postoj != poprzednie_postoj):
    c.setRetRecznyPostoj(nowe_postoj)
    print(" postoj:" + str(poprzednie_postoj)+"->" + str(nowe_postoj))
    poprzednie_postoj = nowe_postoj
    nowe_dane = True

  if (nowe_podawanie != poprzednie_podawanie):
    c.setRetRecznyPodawanie(nowe_podawanie)
    print(" podawanie: " + str(poprzednie_podawanie)+"->" + str(nowe_podawanie))
    poprzednie_podawanie = nowe_podawanie
    nowe_dane = True

  if (nowe_dane == True):
    ile_min = (time.time() - start_czas)/60
    ile_kg = (c.getCzasPodajnika()-start_czas_podajnika)*konf.kg_na_minute
    ile_kg_min = ile_kg / ile_min
    print("Nowa moc: " +str(int(nowa_moc))+"% "\
      + "%0.3f kg " % (ile_kg) + "%0.3f kg/min" % (ile_kg_min) + " %0.3f kg/24h" % (ile_kg_min*60*24))
    print("Delta:"+ str(delta)+" dmuchanie:" + str(nowe_dmuchanie) + " podawanie:" + str(nowe_podawanie) + " postoj:" + str(nowe_postoj))
    nowe_dane = False
  
  poprzednia_co = c.getTempCO()
  opoznienie = int(nowe_postoj+nowe_podawanie)/4
  if (opoznienie <= 0):
    opoznienie = 1
  if (poprzednie_opoznienie != opoznienie):
    print(" opoznienie: " + str(poprzednie_opoznienie) + "->" + str(opoznienie))
    poprzednie_opoznienie = opoznienie

  time.sleep(opoznienie)

wwork = RTimer(work)
wwork.startInterval(2)
kold = files_to_timestamp(os.path.abspath(os.path.dirname(sys.argv[0])))
wkonf = RTimer(konfig)
wkonf.startInterval(10)

try:
  while True:
    if nowakonfiguracja == True:
        print time.strftime("Data: %Y.%m.%d  Czas: %H.%M:%S")
        print ('== Konfiguracja: Wczytywanie ...')
        if sys.version_info[0] == 3:
          importlib.reload(sys.modules["konf_retortowy_p"])
        else:
          reload(sys.modules["konf_retortowy_p"])
        sprawdz_dane()
        nowakonfiguracja = False
    time.sleep(0.2);

finally:
    print ("Kończę działanie ...")
    os.kill(os.getpid(), signal.SIGTERM)

