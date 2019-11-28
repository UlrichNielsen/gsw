# Ziel ist es ein einfaches Zählprogramm auf Interrupt-Basis
# erst einaml für den Gasverbrauch, dann Strom und Wasser
# Mess- und Speicherintervall == 6 min


# Um die Interrupts nutzen zu können,
# ist eine aktuelle Version des Moduls RPi.GPIO notwendig.

import RPi.GPIO as GPIO
import time, _thread
import os, sys, csv



def main():
    
# Peneral Purpose I/O behandeln
    global channel_in           #Eingang
    global channel_out_r        #Ausgang rote LED
    global channel_out_g        #Ausgang gelbe LED

    global Counter_min          # lfd. Zähler während der 6 min
    global Counter_up           # lfd. Zähler Flanke-up (Gas, Magnet-"Puls" bei 0 Durchgang)
    global Counter_down         # lfd. Zähler Flanke-down (Gas, Magnet-"Puls" bei 0 Durchgang)

    global Cnt_6m               # Zähler mit Ergebnis des jeweiligen 6 min-Takts
    global Cnt_h                # Zähler der Pulse i.d. Stunde (Summierung der angefallenen 6 min-Zähler
    global Cnt_d                # dasselbe für den Tag
    global Cnt_W                # dasselbe für die Woche
    global Cnt_M                # dasselbe für den Monat
    global Cnt_Y                # dasselbe für das Jahr

    global Jahr
    global lfdJahr
    global TdJ
    global lfdTdJ
    global MdJ
    global lfdMdJ
    global TdM
    global lfdTdM
    global WdJ
    global lfdWdJ
    global TdW
    global lfdTdW
    global Std
    global lfdStd
    global Min
    global Voll                 # Muster für den "Füllgrad" des Intervalls (1 = noch nicht "voll")
    global Filename
    global FileWoWe
    global f
    global d
    global Flag_up
    global Flag_down

# Initialisieren
    Counter_up = 0
    Counter_down = 0
    Counter_min = 0
    Voll = 11111
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)     # Keine Ausgabe von Warnungen
    channel_in = 24             #GPIO-PIN 24 als Eingang
    channel_out_r = 23          #GPIO-PIN 23 als Ausgang rote LED
    channel_out_g = 18          #GPIO-PIN 12 als Ausgang gelbe LED
    GPIO.cleanup()

    GPIO.setup(channel_out_r, GPIO.OUT)    # Definition Output PIN rote LED
    GPIO.setup(channel_out_g, GPIO.OUT)    # Definition Output PIN gelbe LED

    # seinen Pull-Down Widerstand aktivieren, um einen festen Pegel zu definieren
    # Aussenwiderstand und 0,1 µF über Eingang
    # (Widerstand gegen 3,3 V funktioniert nicht)
    GPIO.setup(channel_in, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

    # Erkennen einer Flankenänderung

    GPIO.add_event_detect(channel_in, GPIO.BOTH, callback = Interrupt_H_L, bouncetime = 100)
    # 100 msec Prellzeit

    # Flanken Flip-Flops für Prell-Unterdrückung in ISR
    Flag_up =0
    Flag_down =0 
    
    id = _thread.get_ident()

    # initial Rot ausschalten (kein 8er Durchgang)
    GPIO.output(channel_out_r, GPIO.LOW)
    # initial Gelb einschalten (warten auf 8er Durchgang)
    GPIO.output(channel_out_g, GPIO.HIGH)


#*********************************************************************
#
# Datenbank erzeugen bzw. öffnen
# Daten-Struktur (2.te Version)
#            auch für csv-DB
#
# 1. Zeitangaben  
#   - 6min-Zeit nach Abschluss des 6min-Fensters Ticks aus time.time()
#   - weitere Zeitangaben für die Darstellung aus time.strftime("%Y.%j.%m.%d.%H.%M.%V.%u")
#       - Jahr (vierstellig)        time.strftime("%Y")
#       - Tag des Jahres (001-366)  time.strftime("%j")
#       - Monat (01-12)             time.strftime("%m")
#       - Tag des Monats (01-31)    time.strftime("%d.")
#       - Stunde (00-23)            time.strftime("%H")
#       - Minute                    time.strftime("%M")
#       - Wochennummer des Jahres   time.strftime("%V")
#       - Wochentag (1(Montag)-7)   time.strftime("%u")
#       -
#
# 2. Werte in m³(jedesmal)
#   - Durchläufe (Counter_min) in den 6 min, d.h. counter_min*0,01 m³ Gasverbrauch
#   - zugehöriger saldierter h-Wert (auf 0 gesetzt bei Beginn einer h)
#   - zugehöriger saldierter d-Wert (auf 0 gesetzt bei Beginn eines d)
#   - zugehöriger saldierter Wochen-Wert (auf 0 gesetzt bei Beginn einer Woche)
#   - zugehöriger saldierter Monats-Wert (auf 0 gesetzt bei Beginn eines Monats)
#   - zugehöriger saldierter Jahres-Wert (auf 0 gesetzt bei Beginn eines Jahres)
#   - zugehöriges Pattern für Vollständigkeit (Voll in Reihenfolge 0, sonst 1)
#
#---------------------------------------------------------------------------
#   Zeiten und Intervallwerte initialisieren

    Ticks = time.time()

    ### 
    #  Werte und Zeiten initialisieren")
    ### 
    
    Jahr = int(time.strftime("%Y"))
    lfdJahr = Jahr
    TdJ = int(time.strftime("%j"))  # Tag des Jahres
    lfdTdJ = TdJ
    MdJ = int(time.strftime("%m"))  # Monat des Jahres
    lfdMdJ = MdJ
    TdM = int(time.strftime("%d"))  # Tag des Monats
    lfdTdM = TdM
    WdJ = int(time.strftime("%V"))  # Woche des Jahres
    lfdWdJ = WdJ
    TdW = int(time.strftime("%u"))  # Tag der Woche
    lfdTdW = TdW
    Std = int(time.strftime("%H"))  # Stunde des Tages
    lfdStd = Std
    Min = int(time.strftime("%M"))  # Minute der Stunde

    ListeDatum = [Jahr, TdJ, MdJ, TdM, WdJ, TdW, Std, Min]

    
    Cnt_6m = 0
    Cnt_h = 0
    Cnt_d = 0
    Cnt_W = 0
    Cnt_M = 0
    Cnt_Y = 0
    Voll = 11111
    
    ListeWerte = [Cnt_6m, Cnt_h, Cnt_d, Cnt_W, Cnt_M, Cnt_Y, Voll]
    
    

    # Öffnen einer "neuen" DB (Löschen alter Inhalte und Überschriften schreiben)
    # Name : Jahr und Tag des laufenden Jahres und Gas
      

    LfdY = str (time.strftime("%Y_"))       # Lfd Jahr
    lfdM = str (time.strftime("%m_"))       # Monat des Jahres
    lfdT = str (time.strftime("%d"))       # Tag des Monats
    Quelle = str (" Gas.csv")
    WoWe = str (" Wochenwerte.csv")

    # Filenamen nach üblicher-Konvention z.B. 2018_03_12 Gas)
    Filename = LfdY + lfdM + lfdT + Quelle
    FileWoWe = LfdY + lfdM + lfdT + WoWe
    
    d = open(Filename,"w")
    writer = csv.writer(d, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)

    # Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"

    writer.writerow(["Counter_up", "Jahr", "TdJahres", "Monat", "TdMonats", "WochedJ", "TagdW", "Std", "Min", "Cnt_6m", "Cnt_h", "Cnt_d", "Cnt_W", "Cnt_M", "Cnt_Y", "Voll"])

    # und schliessen
    #
    d.close ()
    # und dasselbe für den Wochenwert So 15:00

    f = open(FileWoWe,"w")
    friter = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
   
    friter.writerow(["Datum", "Gas", "Strom", "Wasser"])
    f.close

    
 
    
  
#***************************************************************   
    _thread.start_new_thread(Zeitfenster6min,())


    for i in range(500):
        time.sleep(12500) # beliebig

        


# die ISR deklarieren

def Interrupt_H_L(channel_in):
    global Counter_min
    global Counter_up
    global Counter_down
    global Flag_up
    global Flag_down
    if GPIO.input(channel_in) == 1:             # steigende  Flanke (0 → 1)
        GPIO.output(channel_out_r, GPIO.HIGH)   # rote LED an
        GPIO.output(channel_out_g, GPIO.LOW)    # gelbe LED aus
        # print("            Steigende Flanke 1.: Flag_up, Flag_down, Counter_up" ,Flag_up, Flag_down, Counter_up)
        # print("            um: ", time.strftime("%H.%M.%S"))
        if Flag_up == 0:
            Flag_up = 1
            Flag_down = 0
            Counter_up = Counter_up + 1
            # print("        Steigende Flanke 2.: Flag_up, Flag_down, Counter_up" ,Flag_up, Flag_down, Counter_up) 
            # print("        um: ", time.strftime("%H.%M.%S"))
        else:
            Flag_up = Flag_up + 1
            print("        Steigende Flanke 3.(Neg): Flag_up, Flag_down, Counter_up" ,Flag_up, Flag_down, Counter_up) 
            print("        um: ", time.strftime("%H.%M.%S"))
        
    else:                                       #  fallende Flanke (1 → 0)
        GPIO.output(channel_out_r, GPIO.LOW)    # rote LED aus
        GPIO.output(channel_out_g, GPIO.HIGH)   # gelbe LED an
        # print("1. Fallende Flanke: Flag_down, Flag_up, Counter_min" ,Flag_down, Flag_up, Counter_min)
        # print(" um: ", time.strftime("%H.%M.%S"))
        if Flag_down == 0:
            Flag_down = 1
            Flag_up = 0
            Counter_min = Counter_min + 1
            # print("2. Fallende Flanke: Flag_down, Flag_up, Counter_min" ,Flag_down, Flag_up, Counter_min)
            # print(" um: ", time.strftime("%H.%M.%S"))
        else:
            Flag_down = Flag_down + 1
            print("3. (Neg) Fallende Flanke: Flag_down, Flag_up, Counter_min" ,Flag_down, Flag_up, Counter_min)
            print(" um: ", time.strftime("%H.%M.%S"))
# Timer via Threads setzen

def Zeitfenster6min():
    id = _thread.get_ident()
   
    global Counter_up
    global Counter_min
    global Cnt_6m
    global Cnt_h
    global Cnt_d
    global Cnt_W
    global Cnt_M
    global Cnt_Y

    global Jahr
    global lfdJahr
    global TdJ
    global lfdTdJ
    global MdJ
    global lfdMdJ
    global TdM
    global lfdTdM
    global WdJ
    global lfdWdJ
    global TdW
    global lfdTdW
    global Std
    global lfdStd
    global Min
    global Voll
    global Filename
    global FileWoWe
    global f
    global d
    

    # Wochenwert zu Sonntag 15:00 setzen
    WoWert_Gas = 0
    WoWert_Strom = 0
    WoWert_Wasser = 0
    
    # 6 min Intervalle
    min_interv = 6                      #6 min
    min_interv_sec = min_interv * 60    #6 min in sec
    jetztmin = int(time.strftime("%M"))
    zuviel_sec = int(time.strftime("%S"))


    # Wartezeitberechnung
    rest_zeit = min_interv - (jetztmin % min_interv)    # in min
    rest_zeit_sec = rest_zeit * 60 - zuviel_sec         # als sec korrigiert
    
    time.sleep(rest_zeit_sec)
    # Durchlaufzähler
    

    # 6 min- und Durchlauf- Zähler auf  0 setzen vor erstem vollen Intervall, Flanken up für Test auf Richtig
    Counter_up = 0
    Counter_min = 0
    Durchl = 0
    


# Zeiten setzen
    zeitAktuell = int(time.strftime("%d"))      # Test für Tagelang
    zeitEnde = zeitAktuell + 13                  #erst einnmal 13d

       # Ende erreicht?
    while zeitAktuell < zeitEnde: 
        # Datenbank aufmachen zum Schreiben
        d = open(Filename,"a+")

        # Zeit genau auf min-Anfang der 6-min Periode setzen, Schlupf durch CPU-Leistung
        zuviel_sec = int(time.strftime("%S"))
        time.sleep((min_interv_sec-zuviel_sec))


        ### test  incl. ausdruck #########################################
        # Zeit innerhalb der Stunde als Minute und wievieltes Intervall
        jetztmin = int(time.strftime("%M"))
        jetzt_intv = int(jetztmin/min_interv)
        # print("--6min-- jetztmin", jetztmin, jetzt_intv)
      
        #================================================================
        # Zeit und Impulsanzahl in Datenbank speichern
        #------------------------------------------------------------------------
        # laufende Zeitwerte gewinnen
        #
        Ticks = time.time()        
        lfdJahr = int(time.strftime("%Y"))
        lfdTdJ = int(time.strftime("%j"))   # Tag des Jahres
        lfdMdJ = int(time.strftime("%m"))   # Monat des Jahres
        lfdTdM = int(time.strftime("%d"))   # Tag des Monats
        lfdWdJ = int(time.strftime("%V"))   # Woche des Jahres
        lfdTdW = int(time.strftime("%u"))   # Tag der Woche
        lfdStd = int(time.strftime("%H"))   # Stunde des Tages
        lfdMin = int(time.strftime("%M"))   # Minute der Stunde

        
        lfdListeDatum = [lfdJahr, lfdTdJ, lfdMdJ, lfdTdM, lfdWdJ, lfdTdW, lfdStd, lfdMin]
        
        # Werte ermitteln
        #
        # laufenden 6 min umspeichern: Counter_min zu Cnt_6m
        Cnt_6m = Counter_min
        # 6 min Zähler anschließend auf 0 setzen für neues Intervall
        Counter_min = 0

        # laufenden h-Wert bearbeiten
        Cnt_h = Cnt_h + Cnt_6m     
        # laufenden d-Wert bearbeiten
        Cnt_d = Cnt_d + Cnt_6m 
        # laufenden Wochen-Wert bearbeiten
        Cnt_W = Cnt_W + Cnt_6m
        # laufenden Monats-Wert bearbeiten
        Cnt_M = Cnt_M + Cnt_6m
        # laufenden Jahres-Wert bearbeiten
        Cnt_Y = Cnt_Y + Cnt_6m
        # Wochenwert für Gas setzen bis alles stimmt
        WoWert_Gas = WoWert_Gas +Cnt_6m 
        
        ListeWerte = [Cnt_6m, Cnt_h, Cnt_d, Cnt_W, Cnt_M, Cnt_Y, Voll]
 
        # Datensatz erzeugen
        TLi = [Ticks, lfdJahr, lfdTdJ, lfdMdJ, lfdTdM, lfdWdJ, lfdTdW, lfdStd, lfdMin]
        WLi = [Cnt_6m, Cnt_h, Cnt_d, Cnt_W, Cnt_M, Cnt_Y, Voll]
        d.write (str (Counter_up) + ";"
                 + str (lfdJahr) + ";"
                 + str (lfdTdJ) + ";"
                 + str (lfdMdJ) + ";"
                 + str (lfdTdM) + ";"
                 + str (lfdWdJ) + ";"
                 + str (lfdTdW) + ";"
                 + str (lfdStd) + ";"
                 + str (lfdMin) + ";"
                 + str ( Cnt_6m) + ";"
                 + str (Cnt_h) + ";"
                 + str (Cnt_d) + ";"
                 + str (Cnt_W) + ";"
                 + str (Cnt_M) + ";"
                 + str (Cnt_Y) + ";"
                 + str (Voll) + ";"
                 + "\n")

        Counter_up = 0
        #
        # Zeitübergänge berücksichtigen

        # Wochenwert Sonntag 15:00 setzen
        #
        if lfdTdW == 7:
            if lfdStd ==16:
                if lfdMin < 6:
                    lfdDatum = time.strftime("%c")
                    f = open(FileWoWe,"a+")
                    f.write(str(lfdDatum) + ";"
                            + str (WoWert_Gas) + ";"
                            + str (WoWert_Strom) + ";"
                            + str (WoWert_Wasser) + ";"
                            + "\n")
                    f.close ()
                    WoWert_Gas = 0
                    WoWert_Strom = 0
                    WoWert_Wasser = 0
                    
        #
        if lfdStd != Std:       # Volle Stunde
            Std = lfdStd
            if Voll == 11111:
                Voll = 1111
            Cnt_h = 0
         #   print("--6min-- Std, Cnt_h, Voll:" ,Std, Cnt_h, Voll)
        if lfdTdW != TdW:      # voller Tag Mitternacht 24h 
            TdW = lfdTdW
            if Voll == 1111:
                Voll = 111
            Cnt_d = 0
          #  print("--6min-- TdW, Cnt_d, Voll:" ,TdW, Cnt_d, Voll)
        if lfdWdJ != WdJ:      # volle Woche
            WdJ = lfdWdJ
            if Voll == 111:
                Voll = 11
            Cnt_W = 0
          #  print("--6min-- WdJ, Cnt_W, Voll:" ,WdJ, Cnt_W, Voll)
        if lfdMdJ != MdJ:      # voller Monat
            MdJ = lfdMdJ
            if Voll == 11:
                Voll = 1
            Cnt_M = 0
          #  print("--6min-- MdJ, Cnt_M, Voll:" ,MdJ, Cnt_M, Voll)
        if lfdJahr != Jahr:      # volles Jahr
            Jahr = lfdJahr
            Voll = 00000
            Cnt_Y = 0
          #  print("--6min-- Jahr, Cnt_Y, Voll:" ,Jahr, Cnt_Y, Voll)      

        #================================================================
        

        Durchl = Durchl + 1
        ### test ausdruck ###############################################
        # print("--6min-- Durchlauf Nr.:", Durchl)
        ### test ausdruck ###############################################

        d.close ()
        # Zeit fuer Schleife ermitteln
        zeitAktuell = int(time.strftime("%d"))
        
    
#######################################
    
    return



# Hauptprogramm

main()                           # Invoke the main function


#except KeyBoardInterrupt:
        #print ("CTRL+C, Alles aus")
        # Rot ausschalten
        #GPIO.output(channel_out_r, GPIO.LOW)
        #  Gelb ausschalten
        #GPIO.output(channel_out_g, GPIO.LOW)
        #GPIO.cleanup()
    


    
    









