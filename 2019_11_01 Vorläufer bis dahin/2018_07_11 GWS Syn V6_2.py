# Ziel ist es ein einfaches Zählprogramm auf Interrupt-Basis
# für den Gas-,Strom- und Wasserverbrauch
# Mess- und Speicherintervall == 6 min
# Die Daten werden auf den NAS-Server (Synology) gespeichert
# jeweils unter Tages-Datum von 6:00 bis 5:54 des Folgetages


# Um die Interrupts nutzen zu können,
# ist eine aktuelle Version des Moduls RPi.GPIO notwendig.

import RPi.GPIO as GPIO
import time, _thread
import os, sys, csv

#datapath=/home/pi/shareSynol/IR-Lese/
#cp -v /dev/ttyUSB0 ${datapath}serialin.txt 
def main():
    
# Peneral Purpose I/O behandeln
    global channel_in           # Eingang (Gas)
    global LS_in                # Line sense modul als Input-geber (Wasser)
    global channel_out_r        # Ausgang rote LED (Gas)
    global channel_out_gr       # Ausgang grüne LED (Gas)
    global channel_out_b        # Ausgang blaue LED (Wasser)
    global channel_out_ge       # Ausgang gelbe LED (Wasser)
   

    global Counter_min          # lfd. Zähler während der 6 min
    global Counter_up           # lfd. Zähler Flanke-up (Gas, Magnet-"Puls" bei 0 Durchgang)
    global Counter_down         # lfd. Zähler Flanke-down (Gas, Magnet-"Puls" bei 0 Durchgang)

    global Cnt_6m               # Zähler mit Ergebnis des jeweiligen 6 min-Takts
    global Cnt_h                # Zähler der Pulse i.d. Stunde (Summierung der angefallenen 6 min-Zähler
    global Cnt_d                # dasselbe für den Tag
    global Cnt_W                # dasselbe für die Woche
    global Cnt_M                # dasselbe für den Monat
    global Cnt_Y                # dasselbe für das Jahr
    # Strom
    global Strom_6m             # Strom aus IR-Zähler
    global Strom_6m_diff
    global Strom_6m_vor
    # Wasser
    global Counter_W
    global Counter_W_minus
    global Cnt_W_6m
    global Cnt_W_h
    global Cnt_W_d
    global Cnt_W_W
    global Cnt_W_M
    global Cnt_W_Y
    
    global LfdDir, TagWe, Quelle
    global Jahr, lfdJahr
    global TdJ, lfdTdJ
    global MdJ, lfdMdJ
    global TdM, lfdTdM
    global WdJ, lfdWdJ
    global TdW, lfdTdW
    global Std, lfdStd
    global Min
    global Voll                 # Muster für den "Füllgrad" des Intervalls (1 = noch nicht "voll")
    global Filename
    global FileWoWe
    global File6bis554
    global Flag_Anf6            # Flag für 6:00 Anfang
    global d, f,  l,  s,  f6		# fileidentifier
    global Flag_up, Flag_down, Flanke_w_up, Flanke_w_down
   
   
# Initialisieren
    # Gas
    Counter_up = 0
    Counter_down = 0
    Counter_min = 0

    # Wasser
    Counter_W = 0               # lfd. Wasser-Zähler während der 6 min
    # Strom
    Strom_6m_vor = 0
    # Maske für h, W, Monat, Jahr usw.
    Voll = 11111
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)     # Keine Ausgabe von Warnungen
    channel_in = 24             # GPIO-PIN 24 als Eingang Hall-Sonde (Gas)
    LS_in = 17                  # GPIO-PIN 17 als Eingang LS-Sonde (Wasser)
    channel_out_r = 23          # GPIO-PIN 23 als Ausgang rote LED (Gas)
    channel_out_gr = 18         # GPIO-PIN 12 als Ausgang grüne LED (Gas)
    channel_out_b = 27          # GPIO-PIN 27 als Ausgang blaue LED (Wasser)
    channel_out_ge = 22         # GPIO-PIN 22 als Ausgang gelbe LED (Wasser)
    GPIO.cleanup()

    GPIO.setup(channel_out_r, GPIO.OUT)     # Definition Output PIN rote LED (Gas)
    GPIO.setup(channel_out_gr, GPIO.OUT)     # Definition Output PIN grüne LED (Gas)
    GPIO.setup(channel_out_b, GPIO.OUT)     # Definition Output PIN blaue LED (Wasser)
    GPIO.setup(channel_out_ge, GPIO.OUT)    # Definition Output PIN gelbe LED (Wasser)
    
    # Gas-Input: Pull-Down Widerstand aktivieren, um einen festen Pegel zu definieren
    # Aussenwiderstand und 0,1 µF über Eingang
    # (Widerstand gegen 3,3 V funktioniert nicht)
    GPIO.setup(channel_in, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
 
    # Wasser LS-pin to input, use internal pull-up-resistor
    GPIO.setup(LS_in,GPIO.IN, pull_up_down=GPIO.PUD_UP) 

    # Erkennen einer Flankenänderung bei Gas
    GPIO.add_event_detect(channel_in, GPIO.BOTH, Interrupt_H_L, bouncetime = 100)
    # 100 msec Prellzeit

    # Erkennen einer Flankenänderung bei Wasser   
    GPIO.add_event_detect(LS_in, GPIO.BOTH, Wasser_Interr, bouncetime=25)
    # 25 msec Prellzeit
    
    # Flanken Flip-Flops für Prell-Unterdrückung in ISR
    Flag_up =0
    Flag_down =0 
    Flanke_w_up =0
    Flanke_w_down =0
    
    id = _thread.get_ident()
    # Gas
    # initial Rot ausschalten (kein 8er Durchgang)
    GPIO.output(channel_out_r, GPIO.LOW)
    # initial Grün einschalten (warten auf 8er Durchgang)
    GPIO.output(channel_out_gr, GPIO.HIGH)

    # Wasser
    # initial Blau ausschalten (kein Durchgang)
    GPIO.output(channel_out_b, GPIO.LOW)
    # initial Gelb einschalten (warten auf Durchgang)
    GPIO.output(channel_out_ge, GPIO.HIGH)


#*********************************************************************
#
# Datenbank erzeugen bzw. öffnen in eigenem Folder
# Daten-Struktur (3.te Version)
#            auch für csv-DB mit Strom
#
# 1. Zeitangaben  
#   - weitere Zeitangaben für die Darstellung aus time.strftime("%Y.%j.%m.%d.%H.%M.%V.%u")
#       - Jahr Monat Tag            time.strftime("%x")
#       - Stunde Min Sec            time.strftime("%X")
#
# 2. Werte in m³(jedesmal)
#   - Durchläufe (Counter_min) in den 6 min, d.h. counter_min*0,01 m³ Gasverbrauch
#   - zugehöriger saldierter h-Wert (auf 0 gesetzt bei Beginn einer h)
#   - Strom-Zählerwert alle 6 min, 4 Stellen hinter dem Komma und als Differenzwert
#   - Wasserwerte
#   - zugehöriges Pattern für Vollständigkeit (Voll in Reihenfolge 0, sonst 1)
#
#---------------------------------------------------------------------------
#   Zeiten und Intervallwerte initialisieren

    Ticks = time.time()

    ### 
    #  Werte und Zeiten initialisieren
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

    
    # Gas
    Cnt_6m = 0
    Cnt_h = 0
    Cnt_d = 0
    Cnt_W = 0
    Cnt_M = 0
    Cnt_Y = 0
    # Strom
    Strom_6m = 0
    # Wasser
    Counter_W = 0
    Cnt_W_6m = 0
    Cnt_W_h = 0
    Cnt_W_d = 0
    Cnt_W_W = 0
    Cnt_W_M = 0
    Cnt_W_Y = 0

    Voll = 11111
    
    # Path setzen
    
    path="/home/pi/shareSynol/"
    os.chdir(path) 

    # Öffnen einer "neuen" DB (Löschen alter Inhalte und Überschriften schreiben)
    # Name : Jahr und Tag des laufenden Jahres und Gas&Strom
      
    LfdDir = str ("lfd Programm Erg/")      # Ergebnis-Folder
    LfdY = str (time.strftime("%Y_"))       # Lfd Jahr
    lfdM = str (time.strftime("%m_"))       # Monat des Jahres
    lfdT = str (time.strftime("%d"))        # Tag des Monats, hier für die nicht-Tagesfiles
    Quelle = str (" GSW.csv")
    WoWe = str (" Wochenwerte.csv")
    TagWe = str ("_ab 6h")

    # Filenamen nach üblicher-Konvention z.B. 2018_03_12 Gas etc.)
    Filename = LfdDir + LfdY + lfdM + lfdT + Quelle
    d = open(Filename,"w")
    writer = csv.writer(d, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
    # Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"
    writer.writerow(["Datum", "Zeit", "Strom_6m_dif", "Gas_6m", "Cnt_W_6m", "G_Cnt_h", "G_Cnt_d", "g_Cnt_W", "G_Cnt_M", "G_Cnt_Y", "Strom_6m","Cnt_W_h", "Cnt_W_d", "Cnt_W_W", "Cnt_W_M", "Voll"])

    # und schliessen
    d.close ()

    # und dasselbe für die Tageswerte von 6:00 bis 5:54 initial, wird nicht vollständig sein da belieber Start des Programms
    File6bis554 = LfdDir + LfdY + lfdM + lfdT + TagWe + Quelle
    f6 = open(File6bis554,"w")
    f6riter = csv.writer(f6, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
    # Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"
    f6riter.writerow(["Datum", "Zeit", "Strom_6m_dif", "Gas_6m", "Cnt_W_6m", "G_Cnt_h", "Strom_6m", "Cnt_W_h", "Voll"])

    # und schliessen
    #
    f6.close ()
    Flag_Anf6 = 1            # Flag für 6:00 Anfang setzen

    # und dasselbe für den Wochenwert So 16:00
    FileWoWe = LfdDir + LfdY + lfdM + lfdT + WoWe
    f = open(FileWoWe,"w")
    friter = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
    # Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"
    friter.writerow(["Datum", "Gas", "Strom", "Wasser"])
    f.close
    
    
  
#***************************************************************   
    _thread.start_new_thread(Zeitfenster6min,())


    for i in range(50000):
        time.sleep(125000) # beliebig

        


# die ISR deklarieren

def Interrupt_H_L(channel_in):
    global Counter_min, Counter_up, Counter_down
    global Flag_up, Flag_down
    
    if GPIO.input(channel_in) == 1:             # steigende  Flanke (0 → 1)
        GPIO.output(channel_out_r, GPIO.HIGH)   # rote LED an
        GPIO.output(channel_out_gr, GPIO.LOW)   # grüne LED aus
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
            # print("        Steigende Flanke 3.(Neg): Flag_up, Flag_down, Counter_up" ,Flag_up, Flag_down, Counter_up) 
            # print("        um: ", time.strftime("%H.%M.%S"))
        
    else:                                       #  fallende Flanke (1 → 0)
        GPIO.output(channel_out_r, GPIO.LOW)    # rote LED aus
        GPIO.output(channel_out_gr, GPIO.HIGH)  # grüne LED an
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
            # print("3. (Neg) Fallende Flanke: Flag_down, Flag_up, Counter_min" ,Flag_down, Flag_up, Counter_min)
            # print(" um: ", time.strftime("%H.%M.%S"))


def Wasser_Interr(LS_in):
    global Counter_W                # lfd. Wasser Zähler während der 6 min
                                    
    global Flanke_w_up, Flanke_w_down, Counter_W_minus
    
    if GPIO.input(LS_in) == 1:                          # steigende  Flanke (0 → 1)
        # print ("Optisch Hell/Dunkel detected: blaue-LED on, grün aus")
        if Flanke_w_up == 0:
            Flanke_w_down = 0
            Flanke_w_up = 1
            Counter_W = Counter_W + 1
            # print ("WZ= ", time.strftime("%H:%M:%S"), time.time(), Counter_W)
            GPIO.output(channel_out_b, GPIO.HIGH)           # blaue LED an
            GPIO.output(channel_out_ge, GPIO.LOW)           # gelbe LED aus
        else:
            Flanke_w_up = Flanke_w_up + 1
            # print ("                              Flanke_w_up = ", Flanke_w_up)
    else:
        if Flanke_w_down == 0:
            Flanke_w_up = 0
            Flanke_w_down = 1 
            # print ("Optisch Dunkel/Hell: blaue-LED off, grün an")
            GPIO.output(channel_out_b, GPIO.LOW)            # blaue LED aus
            GPIO.output(channel_out_ge, GPIO.HIGH)          # gelbe LED an 
            # Counter_W_minus = Counter_W_minus-1
            # print ("WZ-minus= ", time.strftime("%H:%M:%S"), time.time(), Counter_W_minus)
        else:
            Flanke_w_down = Flanke_w_down + 1



# Timer via Threads setzen

def Zeitfenster6min():
    id = _thread.get_ident()
   
    # Gas
    global Counter_up, Counter_min, Cnt_6m, Cnt_h, Cnt_d, Cnt_W, Cnt_M, Cnt_Y
   
    # Strom
    global Strom_6m, Strom_6m_diff, Strom_6m_vor
    
    # Wasser
    global Counter_W, Counter_W_minus, Cnt_W_6m, Cnt_W_h, Cnt_W_d, Cnt_W_W, Cnt_W_M, Cnt_W_Y
    
    global LfdDir, TagWe, Quelle
    global Jahr, lfdJahr
    global TdJ, lfdTdJ
    global MdJ, lfdMdJ
    global TdM, lfdTdM
    global WdJ, lfdWdJ
    global TdW, lfdTdW
    global Std, lfdStd
    global Min
    global Voll
    global Filename
    global FileWoWe
    global File6bis554
    global Flag_Anf6            # Flag für 6:00 Anfang
    global d, f, l, s, f6
    

    # Wochenwert zu Sonntag 15:00 setzen
    WoWert_Gas = 0
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
    Counter_W = 0
    Durchl = 0
    


# Zeiten setzen
    zeitAktuell = int(time.strftime("%d"))      # Test für Tagelang
    zeitEnde = zeitAktuell + 365                  #erst einnmal 365d

       # Ende erreicht?
    while zeitAktuell < zeitEnde: 
        # Datenbank aufmachen zum Schreiben
        d = open(Filename,"a+")
        f6 = open(File6bis554,"a+")

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

        
        # Werte ermitteln
        #
        # laufenden 6 min umspeichern: Counter_min zu Cnt_6m
        Cnt_6m = Counter_min
        Cnt_W_6m = Counter_W
        # 6 min Zähler anschließend auf 0 setzen für neues Intervall
        Counter_min = 0
        Counter_W = 0

        # laufenden h-Wert bearbeiten
        Cnt_h = Cnt_h + Cnt_6m
        Cnt_W_h = Cnt_W_h + Cnt_W_6m
        # laufenden d-Wert bearbeiten
        Cnt_d = Cnt_d + Cnt_6m
        Cnt_W_d = Cnt_W_d + Cnt_W_6m
        # laufenden Wochen-Wert bearbeiten
        Cnt_W = Cnt_W + Cnt_6m
        Cnt_W_W = Cnt_W_W + Cnt_W_6m
        # laufenden Monats-Wert bearbeiten
        Cnt_M = Cnt_M + Cnt_6m
        Cnt_W_M = Cnt_W_M + Cnt_W_6m
        # laufenden Jahres-Wert bearbeiten
        Cnt_Y = Cnt_Y + Cnt_6m
        # Wochenwert für Gas setzen bis alles stimmt
        WoWert_Gas = WoWert_Gas +Cnt_6m 

        # Stromwert ermitteln aus Zählerauslesung


        # Öffnen csv-Quelle
        lese_pfad = str ("/home/pi/shareSynol/IR-Lese/")
        lfile = str ("serialin.txt")
        lquelle = lese_pfad + lfile
        l = open(lquelle,"rb")

        # Test-Ausdruck 
        allezeilen = l.read()
        #print(allezeilen)

        # Stop-Pattern bei Suche auf Stromwert (entspr.b'52 ff 59')
        byte_patter = b"\x1eR\xffY"
        # print("byte_patter: ", byte_patter)



        seek_index = 10
        byte_index = 4      #ist der richtige Wert

        erg_index = 8

        while seek_index < 400:         # sollte reichen
            l.seek(seek_index)
            bytesuch=l.read(byte_index)
            if bytesuch == byte_patter:
                # Testausdruck
                #print("Treffer", seek_index)
                seek_index= seek_index + byte_index
                l.seek(seek_index)
                # Testausdruck
                #print ("Pointer auf Wert: ", seek_index)
                byte_erg = l.read(erg_index)
                # Testausdruck
                #print("Wert: ", byte_erg)
                Strom_6m =(int.from_bytes(byte_erg, byteorder='big'))
        # einfügen in DB 
                # Testausdruck
                # print(Strom_6m)
                if Strom_6m > 0:
                    Strom_6m_diff = Strom_6m - Strom_6m_vor
                    # print(Strom_6m_diff, Strom_6m_vor)
                    if Strom_6m_diff > 5999:     # erster Wert vor Diff-Bildung
                        Strom_6m_diff = 0    
                    Strom_6m_vor = Strom_6m
                    break
            seek_index = seek_index + 1    


        # Schliessen der Strom-Dateien
        l.close ()

 
        # Datensatz erzeugen
        lfdDatum = time.strftime("%x")
        lfdUhr =   time.strftime("%X") 
        d.write (str (lfdDatum) + ";"
                 + str (lfdUhr) + ";"
                 + str (Strom_6m_diff) + ";" 
                 + str (Cnt_6m) + ";"
                 + str (Cnt_W_6m) + ";"
                 + str (Cnt_h) + ";"
                 + str (Cnt_d) + ";"
                 + str (Cnt_W) + ";"
                 + str (Cnt_M) + ";"
                 + str (Cnt_Y) + ";"
                 + str (Strom_6m) + ";"
                 + str (Cnt_W_h) + ";"
                 + str (Cnt_W_d) + ";"
                 + str (Cnt_W_W) + ";"
                 + str (Cnt_W_M) + ";"
                 + str (Voll) + ";"
                 + "\n")

        # Datensatz für 6-5:54 erzeugen
        lfdDatum = time.strftime("%x")
        lfdUhr =   time.strftime("%X") 
        if Flag_Anf6 >= 0:            
            f6.write (str (lfdDatum) + ";"
                     + str (lfdUhr) + ";"
                     + str (Strom_6m_diff) + ";" 
                     + str (Cnt_6m) + ";"
                     + str (Cnt_W_6m) + ";"
                     + str (Cnt_h) + ";"
                     + str (Strom_6m) + ";"
                     + str (Cnt_W_h) + ";"
                     + str (Voll) + ";"
                     + "\n")

        

        Counter_up = 0
        #
        # Zeitübergänge berücksichtigen

        # Wochenwert Sonntag 16:00 setzen
        #
        if lfdTdW == 7:
            if lfdStd ==16:
                if lfdMin < 6:
                    lfdDatum = time.strftime("%c")
                    f = open(FileWoWe,"a+")
                    f.write(str(lfdDatum) + ";"
                            + str (WoWert_Gas) + ";"
                            + str (Strom_6m) + ";"
                            + str (WoWert_Wasser) + ";"
                            + "\n")
                    f.close ()
                    WoWert_Gas = 0
                    WoWert_Wasser = 0
                    
        #
        if lfdStd != Std:       # Volle Stunde
            Std = lfdStd
            if Voll == 11111:
                Voll = 1111

            if lfdStd == 5:
                if lfdMin > 52:
                    Flag_Anf6 = 0
                    # altes Tagesfile schliessen
                    f6.close()
                    # und neues File für die Tageswerte von 6:00 bis 5:54 aufmachen
                    LfdY = str (time.strftime("%Y_"))       # Lfd Jahr, hier für die Tagesfiles
                    lfdM = str (time.strftime("%m_"))       # Monat des Jahres, hier für die Tagesfiles
                    lfdT = str (time.strftime("%d"))        # Tag des Monats, hier für die Tagesfiles
                    File6bis554 = LfdDir + LfdY + lfdM + lfdT + TagWe + Quelle
                    f6 = open(File6bis554,"w")
                    f6riter = csv.writer(f6, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
                    # Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"
                    f6riter.writerow(["Datum", "Zeit", "Strom_6m_dif", "Gas_6m", "Cnt_W_6m", "G_Cnt_h", "Strom_6m", "Cnt_W_h", "Voll"])
                    # und schliessen "Überschrift"
                    f6.close()
                    # und neu aufmachen
                    f6 = open(File6bis554,"a+")
                    
            Cnt_h = 0
            Cnt_W_h = 0
         #   print("--6min-- Std, Cnt_h, Voll:" ,Std, Cnt_h, Voll)
        if lfdTdW != TdW:      # voller Tag Mitternacht 24h 
            TdW = lfdTdW
            if Voll == 1111:
                Voll = 111
            Cnt_d = 0
            Cnt_W_d = 0
          #  print("--6min-- TdW, Cnt_d, Voll:" ,TdW, Cnt_d, Voll)
        if lfdWdJ != WdJ:      # volle Woche
            WdJ = lfdWdJ
            if Voll == 111:
                Voll = 11
            Cnt_W = 0
            Cnt_W_W = 0
          #  print("--6min-- WdJ, Cnt_W, Voll:" ,WdJ, Cnt_W, Voll)
        if lfdMdJ != MdJ:      # voller Monat
            MdJ = lfdMdJ
            if Voll == 11:
                Voll = 1
            Cnt_M = 0
            Cnt_W_M = 0
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
       #
        # f6.close () 
        # Zeit fuer Schleife ermitteln
        zeitAktuell = int(time.strftime("%d"))
        
    
#######################################
    
    return



# Hauptprogramm

main()                           # Invoke the main function

try:
    while True:
        pass

# Quit on Ctrl-c
except KeyboardInterrupt:
    print ("Ctrl-C - quit")
    # Alle ausschalten
    GPIO.output(channel_out_r, GPIO.LOW)       # Rot aus 
    GPIO.output(channel_out_ge, GPIO.LOW)      # Gelb aus 
    GPIO.output(channel_out_b, GPIO.LOW)       # Blau aus      
    GPIO.output(channel_out_gr, GPIO.LOW)      # Grün aus
# Cleanup GPIO
finally:
    GPIO.cleanup() 

