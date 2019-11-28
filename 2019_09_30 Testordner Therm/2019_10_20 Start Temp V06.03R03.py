#!/usr/bin/python
# coding=utf-8
# messprogramm.py
#------------------------------------------------------------
 
import RPi.GPIO as GPIO
import os, sys, time, csv
 
# Global für vorhandene Temperatursensoren
tempSensorBezeichnung = [] #Liste mit den einzelnen Sensoren-Kennungen
tempSensorAnzahl = 0 #INT für die Anzahl der gelesenen Sensoren
tempSensorWert = [] #Liste mit den einzelnen Sensor-Werten
realSensorBezeichnung = []
realSensorBezeichnung = ["Vorlauf  ","Dach/Garten ",
                         "Dach/ Mitte ","Wz/Mitte    ",
                         "Bad         ","Wz/Fenster  ",
                         "Wz/Küche    ","Schlafzimmer",
                         "Dach/Strasse","Aussen  ",
                         "Windfang/WC ","Arbeitsz.   "]  # Liste der zug. Sensorbezeichnungen
 
 
# Global für Programmstatus / 
programmStatus = 1 
 
def ds1820einlesen():
    global tempSensorBezeichnung, tempSensorAnzahl, programmStatus, realSensorBezeichnung
    #Verzeichnisinhalt auslesen mit allen vorhandenen Sensorbezeichnungen 28-xxxx
    try:
        for x in os.listdir("/sys/bus/w1/devices"):
            if (x.split("-")[0] == "28") or (x.split("-")[0] == "10"):
                tempSensorBezeichnung.append(x)
                tempSensorAnzahl = tempSensorAnzahl + 1
    except:
        # Auslesefehler
        print (time.strftime("%H:%M:%S") , "Der Verzeichnisinhalt konnte nicht ausgelesen werden.")
        programmStatus = 0

def ds1820auslesen():
    global tempSensorBezeichnung, tempSensorAnzahl, tempSensorWert, programmStatus, realSensorBezeichnung
    x = 0
    try:
        # 1-wire Slave Dateien gem. der ermittelten Anzahl auslesen 
        while x < tempSensorAnzahl:
            dateiName = "/sys/bus/w1/devices/" + tempSensorBezeichnung[x] + "/w1_slave"
            file = open(dateiName)
            filecontent = file.read()
            file.close()
            # Temperaturwerte auslesen und konvertieren
            stringvalue = filecontent.split("\n")[1].split(" ")[9]
            sensorwert = float(stringvalue[2:]) / 1000
            temperatur = '%6.2f' % sensorwert #Sensor- bzw. Temperaturwert auf 2 Dezimalstellen formatiert
            tempSensorWert.insert(x,temperatur) #Wert in Liste aktualisieren
            x = x + 1
    except:
        # Fehler bei Auslesung der Sensoren
        print (time.strftime("%H:%M:%S"), "Die Auslesung der DS1820 Sensoren war nicht möglich.")
        programmStatus = 0
 
#Programminitialisierung
global channel_out_r        # Ausgang rote LED: Werte lesen
global channel_out_we       # Ausgang weisse LED: Ruhephase
global Flag_Anf6, DLauf


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)     # Keine Ausgabe von Warnungen
channel_out_r = 16          # GPIO-PIN 16 als Ausgang rote LED
channel_out_we = 20         # GPIO-PIN 20 als Ausgang weisse LED
GPIO.cleanup()

GPIO.setup(channel_out_r, GPIO.OUT)     # Definition Output PIN rote LED
GPIO.setup(channel_out_we, GPIO.OUT)    # Definition Output PIN weisse LED

# initial Rot ausschalten (Messung)
GPIO.output(channel_out_r, GPIO.LOW)
# initial Weiss einschalten (Ruhepause)
GPIO.output(channel_out_we, GPIO.HIGH)


# Datenbank aufbauen

path="/home/pi/LokaleErg/"
os.chdir(path) 

# Öffnen einer "neuen" DB (Löschen alter Inhalte und Überschriften schreiben)
# Name : Jahr und Tag des laufenden Jahres und Heizungs-Temperatur
      
LfdDir = str ("lfdProgrammErg/")        # Ergebnis-Folder
LfdY = str (time.strftime("%Y_"))       # Lfd Jahr
lfdM = str (time.strftime("%m_"))       # Monat des Jahres
lfdT = str (time.strftime("%d"))        # Tag des Monats, hier für die nicht-Tagesfiles
lfdStd =   time.strftime("%H")
Quelle = str (" Hzg.csv")
TagWe = str ("_ab 6h")

# für die Tageswerte von 6:00 bis 5:54 initial
File6bis554 = LfdDir + LfdY + lfdM + lfdT + lfdStd + TagWe + Quelle
f6 = open(File6bis554,"w")
f6riter = csv.writer(f6, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
# Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"
f6riter.writerow(["Datum", "Zeit", "Windfang", "Wz/Fenster", "Wz/Mitte", "Wz/Kueche", "ArbZi", "Bad", "Schlaf", "Dh/Gart", "Dh/Mitte", "Dh/Str", "Vorlauf", "Aussen"])
# und schliessen
#
f6.close ()
# Datenbank aufmachen zum Schreiben
       ## d = open(Filename,"a+")
f6 = open(File6bis554,"a+")

Flag_Anf6 = 1
DLauf = 1

ds1820einlesen() #Anzahl und Bezeichnungen der vorhandenen Temperatursensoren einlesen
 
# Temperaturausgabe in Schleife
programmStatus = 1
while programmStatus == 1:
    x = 0
    ds1820auslesen()

    GPIO.output(channel_out_r, GPIO.HIGH)   # rote LED an
    GPIO.output(channel_out_we, GPIO.LOW)   # weisse LED aus

#+    print ("Zeit und Sensorbezeichnung und Temperaturwert:")
    while x < tempSensorAnzahl:
        
#*        print (time.strftime("%H:%M:%S") , "     " ,realSensorBezeichnung[x] , "   " , tempSensorBezeichnung[x] , " " , tempSensorWert[x] , " °C")
        x = x + 1

    GPIO.output(channel_out_r, GPIO.LOW)    # rote LED aus
    GPIO.output(channel_out_we, GPIO.HIGH)  # weisse LED an

 # Datensatz für 6-5:54 erzeugen
    lfdDatum = time.strftime("%x")
    lfdUhr =   time.strftime("%X") 
    lfdStd =   time.strftime("%H")
    lfdMin =   time.strftime("%M")
    IlfdStd =  int(lfdStd)
    IlfdMin =  int(lfdMin)    

                
    f6.write (str (lfdDatum) + ";"
                + str (lfdUhr) + ";"                      
                + str (tempSensorWert[10]).replace(".",",") + ";"
                + str (tempSensorWert[5]).replace(".",",") + ";"
                + str (tempSensorWert[3]).replace(".",",") + ";"
                + str (tempSensorWert[6]).replace(".",",") + ";"
                + str (tempSensorWert[11].replace(".",",")) + ";"
                + str (tempSensorWert[4]).replace(".",",") + ";"
                + str (tempSensorWert[7]).replace(".",",") + ";"
                + str (tempSensorWert[1]).replace(".",",") + ";"
                + str (tempSensorWert[2]).replace(".",",") + ";"
                + str (tempSensorWert[8]).replace(".",",") + ";"
                + str (tempSensorWert[0]).replace(".",",") + ";" 
                + str (tempSensorWert[9]).replace(".",",") + ";" 
                + "\n")
#+       print (DLauf, "    ", time.strftime("%H:%M:%S"))
    if IlfdStd == 6:
        if IlfdMin > 0 and IlfdMin < 9:
                    # altes Tagesfile schliessen
            print ("Verirrt")
            f6.close()
                    # und neues File für die Tageswerte von 6:00 bis 5:54 aufmachen
            LfdY = str (time.strftime("%Y_"))       # Lfd Jahr, hier für die Tagesfiles
            lfdM = str (time.strftime("%m_"))       # Monat des Jahres, hier für die Tagesfiles
            lfdT = str (time.strftime("%d"))        # Tag des Monats, hier für die Tagesfiles
            File6bis554 = LfdDir + LfdY + lfdM + lfdT + TagWe + Quelle
            f6 = open(File6bis554,"w")
            f6riter = csv.writer(f6, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
                    # Schreiben der Liste als CSV-Datensatz ergibt "Überschrift"
            f6riter.writerow(["Datum", "Zeit", "Windfang", "Wz/Fenster", "Wz/Mitte", "Wz/Kueche", "ArbZi", "Bad", "Schlaf", "Dh/Gart", "Dh/Mitte", "Dh/Str", "Vorlauf", "Aussen"])
                    # und schliessen "Überschrift"
            f6.close() 
            DLauf = 0
                    # und neu aufmachen
            f6 = open(File6bis554,"a+") 


    DLauf = DLauf + 1
    time.sleep(360)
#+    print ("\n")
   
# Programmende durch Veränderung des programmStatus
f6.close()
print ("Programm wurde beendet.")

        
