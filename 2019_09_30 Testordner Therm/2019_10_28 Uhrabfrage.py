import os, sys, time, random
global temp

path="/home/pi/LokaleErg/"
os.chdir(path) 


 
print (time.strftime("%H:%M:%S"))
help(rrdtool.update)


l=0


while l <= 10:

    TEMP = 10.2*l + l*0.1
    print (l, "  ", TEMP)
    rrdtool.update(
        "testtemp.rrd",
        "N:$TEMP")

    l = l+1
    print (time.strftime("%H:%M:%S"), "  Durchlauf:   ", l)
    time.sleep(5)




rrdtool.graph(
    "testtemp.png",
    "--start",
    "-1d", "--vertical-label=Bytes/s",
    "DEF:inoctets=test1.rrd:input:AVERAGE",
    "DEF:outoctets=test1.rrd:output:AVERAGE",
    "AREA:inoctets#00FF00:In traffic",
    "LINE1:outoctets#0000FF:Out traffic\\r",
    "CDEF:inbits=inoctets,8,*",
    "CDEF:outbits=outoctets,8,*",
    "COMMENT:\\n",
    "GPRINT:inbits:AVERAGE:Avg In traffic\: %6.2lf %Sbps",
    "COMMENT: ",
    "GPRINT:inbits:MAX:Max In traffic\: %6.2lf %Sbps\\r",
    "GPRINT:outbits:AVERAGE:Avg Out traffic\: %6.2lf %Sbps",
    "COMMENT: ",
    "GPRINT:outbits:MAX:Max Out traffic\: %6.2lf %Sbps\\r")
