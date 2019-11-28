#!/usr/bin/python
# coding=utf-8
# messprogramm.py
#------------------------------------------------------------
 
import RPi.GPIO as GPIO
import os, sys, time
#- import rrdtool
 
# Global für vorhandene Temperatursensoren
tempSensorBezeichnung = [] #Liste mit den einzelnen Sensoren-Kennungen
tempSensorAnzahl = 0 #INT für die Anzahl der gelesenen Sensoren
tempSensorWert = [] #Liste mit den einzelnen Sensor-Werten
realSensorBezeichnung = ["Sensor #11  ","Dach/Garten ",
                         "Dach/ Mitte ","Wz/Mitte    ",
                         "Bad         ","Wz/Fenster  ",
                         "Wz/Küche    ","Schlafzimmer",
                         "Dach/Strasse","Sensor #12  ",
                         "Windfang/WC ","Arbeitsz.   "]  # Liste der zug. Sensorbezeichnungen
 
# Global für Programmstatus / 
programmStatus = 1 
 
def ds1820einlesen():
    global tempSensorBezeichnung, tempSensorAnzahl, programmStatus,realSensorBezeichnung 
    #Verzeichnisinhalt auslesen mit allen vorhandenen Sensorbezeichnungen 28-xxxx
    try:
        for x in os.listdir("/sys/bus/w1/devices"):
            if (x.split("-")[0] == "28") or (x.split("-")[0] == "10"):
                tempSensorBezeichnung.append(x)
                tempSensorAnzahl = tempSensorAnzahl + 1
    except:
        # Auslesefehler
        print ("Der Verzeichnisinhalt konnte nicht ausgelesen werden.")
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
        print ("Die Auslesung der DS1820 Sensoren war nicht möglich.")
        programmStatus = 0
 
#Programminitialisierung
global channel_out_r        # Ausgang rote LED: Werte lesen
global channel_out_we       # Ausgang weisse LED: Ruhephase

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

# rrd aufsetzen


#- ret = rrdtool.create("example1.rrd", "--step", "1800", "--start", '0',
#- "DS:metric1:GAUGE:2000:U:U",
#- "DS:metric2:GAUGE:2000:U:U",
#- "RRA:AVERAGE:0.5:1:600",
#- "RRA:AVERAGE:0.5:6:700",
#- "RRA:AVERAGE:0.5:24:775",
#- "RRA:AVERAGE:0.5:288:797",
#- "RRA:MAX:0.5:1:600",
#- "RRA:MAX:0.5:6:700",
#- "RRA:MAX:0.5:24:775",
#- "RRA:MAX:0.5:444:797")

#   Name der Datenbank: Example1
#   step of parameters checking (30 minutes in sec= 1800)
#   start point (0 or N means ‘now’)
#   ‘DS’ beide Zeilen)means Data Source with two metrics
#       ‘2000’ means that RRD can wait for 2000 sec to get new values
#          until it considers them as unknown (that’s is why we use 2000, 200 sec
#           more of the 30 min interval
#       'U:U' stands for min and max values of each metric (here 'unknown'
#   'RRA....' describes what types of gained values RRD should store in
#       its database  


ds1820einlesen() #Anzahl und Bezeichnungen der vorhandenen Temperatursensoren einlesen
 
# Temperaturausgabe in Schleife
while programmStatus == 1:
    x = 0
    ds1820auslesen()

    GPIO.output(channel_out_r, GPIO.HIGH)   # rote LED an
    GPIO.output(channel_out_we, GPIO.LOW)   # weisse LED aus

    print ("Zeit und Sensorbezeichnung und Temperaturwert:")
    while x < tempSensorAnzahl:
        print (time.strftime("%H:%M:%S") , "     " ,"     " ,realSensorBezeichnung[x] , "   "  ,tempSensorBezeichnung[x] , " " , tempSensorWert[x] , " °C")
        x = x + 1

    GPIO.output(channel_out_r, GPIO.LOW)    # rote LED aus
    GPIO.output(channel_out_we, GPIO.HIGH)  # weisse LED an

    time.sleep(1)
    print ("\n")
#-    programmStatus = 1      # nur ein Durchlauf
   
# Programmende durch Veränderung des programmStatus
print ("Programm wurde beendet.")

        
