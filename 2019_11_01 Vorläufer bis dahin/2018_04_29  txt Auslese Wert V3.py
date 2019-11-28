import sys
import csv

# cat /home/pi/shared02/IR-Lese/serialin_20180424155542.txt | od -tx1


# Öffnen csv-Quelle
lese_pfad = str ("/home/pi/sharedSynol/IR-Lese/")
lfile = str ("serialin.txt")
lquelle = lese_pfad + lfile
l = open(lquelle,"rb")

# Öffnen Ziel csv
schreib_pfad = str ("/home/pi/shared02/IR-Strom/")
sfile = str ("csvout_424155857.csv")
ssenke = schreib_pfad + sfile
s = open(ssenke,"a+")


# Test-Ausdruck 
allezeilen = l.read()
#print(allezeilen)


# Stop-Pattern bei Suche auf Stromwert (entspr.b'52 ff 59')
byte_patter = b"\x1eR\xffY"
print("byte_patter: ", byte_patter)



seek_index = 260
byte_index = 4      #ist der richtige Wert

erg_index = 8

while seek_index < 400:
    l.seek(seek_index)
    bytesuch=l.read(byte_index)
    if bytesuch == byte_patter:
        print("Treffer", seek_index)
        seek_index= seek_index + byte_index
        l.seek(seek_index)
        print ("Pointer auf Wert: ", seek_index)
        byte_erg = l.read(erg_index)
        print("Wert: ", byte_erg)
        Strom_6m =(int.from_bytes(byte_erg, byteorder='big'))
# einfügen in DB 
        print(Strom_6m)
        if Strom_6m > 0:
            break
    seek_index = seek_index + 1    


# Schliessen der Datei
l.close ()
s.close()
