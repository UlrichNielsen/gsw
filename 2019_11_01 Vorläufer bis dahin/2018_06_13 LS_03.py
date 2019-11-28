#!/usr/bin/env python
import RPi.GPIO as GPIO
import time, _thread
import os, sys, csv

def main():
    global LS_in                # Line sense modul als Input-geber
    global Counter_W            # lfd. Wasser Zähler während der 6 min
    global channel_out_b        # Ausgang blaue LED
    global channel_out_gr       # Ausgang grüne LED
    global Counter_W            # lfd. Wasser Zähler während der 6 min
    global Counter_W_minus
    global Flanke_w_up
    global Flanke_w_down
    
    # print ("Start")
    Counter_W = 0               # lfd. Wasser Zähler während der 6 min,
                                # muss wahrscheinlich halbiert werden

    Flanke_w_up = 0
    Flanke_w_down = 0
    Counter_W_minus = 0
    print ("Start1", Counter_W, Counter_W_minus)
    
    GPIO.setmode(GPIO.BCM)      #Set pin-layout to BCM     
    GPIO.setwarnings(False)     # keine Ausgabe von Warnungen
    LS_in = 17                  # GPIO-PIN 17 als Eingang LS-Sonde Wasser 
    channel_out_b = 27          # GPIO-PIN 27 als Ausgang blaue LED
    channel_out_gr = 22         # GPIO-PIN 22 als Ausgang grüne LED
    GPIO.cleanup()
    
    GPIO.setup(channel_out_b, GPIO.OUT)    # Definition Output PIN blaue LED
    GPIO.setup(channel_out_gr, GPIO.OUT)    # Definition Output PIN grüne LED
    
    #Set LS-pin to input, use internal pull-up-resistor
    GPIO.setup(LS_in,GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    
    # Erkennen einer Flankenänderung
   
    GPIO.add_event_detect(LS_in, GPIO.BOTH, Wasser_Interr, bouncetime=25)
    # 10 msec Prellzeit


    id = _thread.get_ident()

    # initial Blau ausschalten (kein Magnet Durchgang)
    GPIO.output(channel_out_b, GPIO.LOW)
    # initial Grün einschalten (warten auf Magnet Durchgang)
    GPIO.output(channel_out_gr, GPIO.HIGH)


#***************************************************************   
    _thread.start_new_thread(Zeitfenster6min,())


    for i in range(500):
        time.sleep(12500) # beliebig




# die ISR für Wasser-LS-Sensor deklarieren

def Wasser_Interr(LS_in):
    global Counter_W                # lfd. Wasser Zähler während der 6 min
                                    # muss wahrscheinlich halbiert werden
    global Flanke_w_up
    global Flanke_w_down
    global Counter_W_minus
    
    if GPIO.input(LS_in) == 1:                          # steigende  Flanke (0 → 1)
        # print ("Optisch Hell/Dunkel detected: blaue-LED on, grün aus")
        if Flanke_w_up == 0:
            Flanke_w_down = 0
            Flanke_w_up = 1
            Counter_W = Counter_W + 1
            print ("WZ= ", time.strftime("%H:%M:%S"), time.time(), Counter_W)
            GPIO.output(channel_out_b, GPIO.HIGH)           # blaue LED an
            GPIO.output(channel_out_gr, GPIO.LOW)           # grüne LED aus
        else:
            Flanke_w_up = Flanke_w_up + 1
            print ("                              Flanke_w_up = ", Flanke_w_up)
    else:
        if Flanke_w_down == 0:
            Flanke_w_up = 0
            Flanke_w_down = 1 
            # print ("Optisch Dunkel/Hell: blaue-LED off, grün an")
            GPIO.output(channel_out_b, GPIO.LOW)            # blaue LED aus
            GPIO.output(channel_out_gr, GPIO.HIGH)          # grüne LED an 
            Counter_W_minus = Counter_W_minus - 1
            print ("WZ-minus= ", time.strftime("%H:%M:%S"), time.time(), Counter_W_minus)
        else:
            Flanke_w_down = Flanke_w_down + 1
            print ("                      Flanke_w_down = ", Flanke_w_down)


    # Timer via Threads setzen

def Zeitfenster6min():
    id = _thread.get_ident()
    print ("WZ+++= ",  time.strftime("%H:%M:%S"), Counter_W)
    print ("WZ-minus++++= ", time.strftime("%H:%M:%S"), Counter_W_minus) 




    return


# Hauptprogramm

main()                           # Invoke the main function
# The main-loop does nothing. All is done by the event-listener
try:
    while True:
        pass

# Quit on Ctrl-c
except KeyboardInterrupt:
    print ("Ctrl-C - quit")

# Cleanup GPIO
finally:
    GPIO.cleanup() 
