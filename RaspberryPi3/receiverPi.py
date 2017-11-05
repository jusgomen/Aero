#!/usr/bin/python
# -*- coding: utf-8 -*-

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
from lib_nrf24 import NRF24
import time
import spidev
import requests
from datetime import datetime as date

def toGx(x):
    ixx=round(-1.214/100000000*x**3+1.844/100000*x**2-0.002251*x-2,2)
    return ixx

def toGy(y):
    iyy=round(-1.268/100000000*y**3+1.945/100000*y**2-0.002715*y-2.001,2)
    return iyy

def toGz(z):
    izz=round(-1.306/100000000*z**3+1.99/100000*z**2-0.002778*z-1.999,2)
    return izz

GPIO.setwarnings(False)

#Configure Radio
pipes = [[0xe7, 0xd3, 0xf0, 0x35, 0xff], [0xe7, 0xd3, 0xf0, 0x35, 0xc2]]

radio = NRF24(GPIO, spidev.SpiDev())
radio.begin(1, 17)

radio.setRetries(15,15)
radio.setPALevel(NRF24.PA_MAX)
radio.setAutoAck(True)
radio.enableDynamicPayloads()
radio.setCRCLength(16)
radio.enableAckPayload()
##radio.openReadingPipe(1, pipes[0])
radio.openReadingPipe(2, pipes[1])

radio.startListening()

#Open sending buffers
send=[]
sendBuffer1=[]
sendBuffer2=[]
sendBuffer3=[]
sendBuffer4=[]
internet=False

lenBufRPM=0
lenBufAcc=0

while True:
    while radio.available():
        #print("Radio available")
        received = []
        radio.read(received, radio.getDynamicPayloadSize())

        if len(received)>0:
            string=""
            for n in received:
                if (n>=32 and n<=126):
                    string += chr(n)
            #print(string)
            if string[0]=='r':
                ind1=string.find('r')
                ind2=string.find('r',ind1+1)

                rpm=string[ind1+1:ind2]
                
                try:
                    irpm=int(rpm)
                    print("Speed = "+ rpm + " RPM")
                    
                    if irpm==0:
                        rpm="0.0"
                   
                    try:
                        response_speed=requests.get('http://track-mypower.tk/measurements/wind_turbine_speed/new?rpm='+rpm+'&created_at='+str(date.now()),
                        auth=requests.auth.HTTPBasicAuth(
                          'admin',
                          'uninorte'))
                        #f = urllib2.urlopen("http://sistelemetria-sistelemetria.rhcloud.com/save_aero.php?type=rpm&rpm="+rpm)
                        internet=True    
                    except:
                        internet=False
                        if len(sendBuffer3)>211680:
                            sendBuffer3=sendBuffer3[1:]
                            sendBuffer3.append(rpm)
                        else:
                            sendBuffer3.append(rpm)
                        sendBuffer4=sendBuffer3[:]
                        lenBufRPM=len(sendBuffer3)
                            
                except:
                    #print("There was an error in communication with the RPM sensor.")
                    pass
            
            if string[0]=='X'and len(string)>27:
                indX=string.find('X')
                indY=string.find('Y')
                indZ=string.find('Z')
                indF=string.find('F')
                
                mx=string[indX+1:indX+4]
                maxx=string[indX+4:indX+7]
                minx=string[indX+7:indX+10]
                
                my=string[indY+1:indY+4]
                maxy=string[indY+4:indY+7]
                miny=string[indY+7:indY+10]
                
                mz=string[indZ+1:indZ+4]
                maxz=string[indZ+4:indZ+7]
                minz=string[indZ+7:indZ+10]
            
                values=[maxx,mx,minx,maxy,my,miny,maxz,mz,minz]

                try:
                    ivalues= [int(x) for x in values]
                
                    sendG= [ toGx(x) for x in ivalues[0:3] ]
                    sendG+=[ toGy(x) for x in ivalues[3:6] ]
                    sendG+=[ toGz(x) for x in ivalues[6:]  ]
                
                    sendIter= [str(x) for x in sendG]
                    print(sendIter)

                    #GET aceleraciones a base de datos
                    try:
                        response_vibration = requests.get('http://track-mypower.tk/measurements/wind_turbine_vibration/new?max_ejex='+sendIter[0]+'&m_ejex='+sendIter[1]+'&min_ejex='+sendIter[2]+'&max_ejey='+sendIter[3]+'&m_ejey='+sendIter[4]+'&min_ejey='+sendIter[5]+'&max_ejez='+sendIter[6]+'&m_ejez='+sendIter[7]+'&min_ejez='+sendIter[8]+'&created_at='+str(date.now()),
                        auth=requests.auth.HTTPBasicAuth(
                          'admin',
                          'uninorte'))
                        #f=urllib2.urlopen("http://sistelemetria-sistelemetria.rhcloud.com/save_aero.php?type=acc&maxx="+sendIter[0]+"&mx="+sendIter[1]+"&minx="+sendIter[2]+"&maxy="+sendIter[3]+"&my="+sendIter[4]+"&miny="+sendIter[5]+"&maxz="+sendIter[6]+"&mz="+sendIter[7]+"&minz="+sendIter[8])
                        internet=True
                    except:
                        internet=False
                        if len(sendBuffer1)>211680:
                            sendBuffer1=sendBuffer1[1:]
                            sendBuffer1.append(sendIter)
                        else:
                            sendBuffer1.append(sendIter)
                        sendBuffer1.append(sendIter)
                        sendBuffer2=sendBuffer1[:]
                        lenBufAcc=len(sendBuffer1)
            
                except:
                    #print("There was an error in communication with Accelerometer")
                    pass
                
    #print("Radio unavailable")
    #time.sleep(0.01)
    if not internet:
        if len(sendBuffer3)==lenBufRPM:
            print("El buffer de RPM es: ")
            lenBufRPM+=1
            print(sendBuffer3)
        if len(sendBuffer1)==lenBufAcc:
            print("El buffer de Acc es: ")
            print(sendBuffer1)
            lenBufAcc+=1
    
    continueT=False
    while len(sendBuffer4)>0 and (not continueT):
        try:
            for sendRPM in sendBuffer3:
                response_speed=requests.get('http://track-mypower.tk/measurements/wt_speed/new?rpm='+sendRPM+'&t='+str(date.now()),
                        auth=requests.auth.HTTPBasicAuth(
                          'admin',
                          'uninorte'))
                #f = urllib2.urlopen("http://sistelemetria-sistelemetria.rhcloud.com/save_aero.php?type=rpm&rpm="+sendRPM)

                if sendRPM in sendBuffer4:
                    sendBuffer4.remove(sendRPM)

            sendBuffer3=sendBuffer4[:]

        except:
            #print("There is no internet connection")
            continueT=True

    continueB=False
    while len(sendBuffer2)>0 and (not continueB):
        try:
            for sendAcc in sendBuffer1:
                response_vibration = requests.get('http://track-mypower.tk/measurements/wt_vibration/new?max_ejex='+sendAcc[0]+'&m_ejex='+sendAcc[1]+'&min_ejex='+sendAcc[2]+'&max_ejey='+sendAcc[3]+'&m_ejey='+sendAcc[4]+'&min_ejey='+sendAcc[5]+'&max_ejez='+sendAcc[6]+'&m_ejez='+senAcc[7]+'&min_ejez='+sendAcc[8]+'&t='+str(date.now()),
                        auth=requests.auth.HTTPBasicAuth(
                          'admin',
                          'uninorte'))
                #f=urllib2.urlopen("http://sistelemetria-sistelemetria.rhcloud.com/save_aero.php?type=acc&maxx="+sendAcc[0]+"&mx="+sendAcc[1]+"&minx="+sendAcc[2]+"&maxy="+sendAcc[3]+"&my="+sendAcc[4]+"&miny="+sendAcc[5]+"&maxz="+senAcc[6]+"&mz="+sendAcc[7]+"&minz="+sendAcc[8])

                if sendAcc in sendBuffer2:
                    sendBuffer2.remove(sendAcc)

            sendBuffer1=sendBuffer2[:]

        except:
            #print("There is no internet connection")
            continueB=True

    time.sleep(0.01)
    
