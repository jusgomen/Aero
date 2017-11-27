#!/usr/bin/python
# -*- coding: utf-8 -*-

################################################################################
################################################################################
#                                  IMPORTS                                     #
################################################################################
################################################################################

#Python internal packages
import os
import sys
import RPi.GPIO as GPIO

import dht11

import http.client
import requests

import spidev
import minimalmodbus
import serial

import time
import datetime
from datetime import datetime as date

import random
import decimal
from decimal import Decimal

#Python external libraries
#These are *.py files containing method and classes definitions.
#They should be stored in the same folder of the present file.
from lib_nrf24 import NRF24

################################################################################
################################################################################
#                            METHOD DEFINITIONS                                #
################################################################################
################################################################################

def toGx(x):
    '''
    Function to obtain acceleration in g
    Takes in an unsigned integer between 0 and 1023 and returns an acceleration
    between -2g and +2g, with a formula derived from callibration for the x-axis.
    '''
    ixx=round(-1.214/100000000*x**3+1.844/100000*x**2-0.002251*x-2,2)
    return ixx

def toGy(y):
    '''
    Function to obtain acceleration in g
    Takes in an unsigned integer between 0 and 1023 and returns an acceleration
    between -2g and +2g, with a formula derived from callibration for the y-axis.
    '''
    iyy=round(-1.268/100000000*y**3+1.945/100000*y**2-0.002715*y-2.001,2)
    return iyy

def toGz(z):
    '''
    Function to obtain acceleration in g
    Takes in an unsigned integer between 0 and 1023 and returns an acceleration
    between -2g and +2g, with a formula derived from callibration for the z-axis.
    '''
    izz=round(-1.306/100000000*z**3+1.99/100000*z**2-0.002778*z-1.999,2)
    return izz

def ReadChannel(channel):
    '''
    Function to read SPI data from MCP3008 chip
    Channel must be an integer 0-7
    '''
    adc = spi.xfer2([1,(8+channel)<<4,0])
    data = ((adc[1]&3) << 8) + adc[2]
    return data


def ConvertVolts(data,places):
    '''
    Function to convert data to voltage level,
    rounded to specified number of decimal places.
    '''
    volts = (data * 3.3) / float(1023)
    volts = round(volts,places)*5
    return volts

################################################################################
################################################################################
#                     PANEL AND ENERGY VARIABLE DEFINITIONS                    #
################################################################################
################################################################################

# Define sensor channels
pot =0 #vbatt1
pot1=1 #vbatt2
pot2=2 #spektron1
pot3=3 #spektron2
pot4=4 #lm1
pot5=5 #lm2

# Define delay between readings
delay = 0.01

#Instantiate the SharkMeter
SharkMeter = minimalmodbus.Instrument('/dev/serial0', 1) # port name, slave add$
print(SharkMeter)

latitude=2341
longitude=2341
date_time=2421

#Initialize Buffers
Sent=[]
Buffer=[]
valid_measure=False
internet=False

# initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()
GPIO.setup(12,GPIO.OUT)

# read data using pin 14
instance = dht11.DHT11(pin=18)

# SPI bus for the MCP3008
spi = spidev.SpiDev()
spi.open(0,0)

#Timing
now = datetime.now()
then = now

################################################################################
################################################################################
#                        WIND TURBINE VARIABLE DEFINITIONS                     #
################################################################################
################################################################################

send=[]
sendBuffer1=[]
sendBuffer2=[]
sendBuffer3=[]
sendBuffer4=[]
internet=False

lenBufRPM=0
lenBufAcc=0

################################################################################
################################################################################
#                                      MAIN                                    #
################################################################################
################################################################################

while True:
    ############################################################################################
    ############################################################################################
    #                                     WIND TURBINE RECEIVER                                #
    ############################################################################################
    ############################################################################################

    #This condition is True when there are bytes available to be read.
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
            if len(string)>0:

                if string[0]=='r':
                    ind1=string.find('r')
                    ind2=string.find('r',ind1+1)

                    rpm=string[ind1+1:ind2]

                    try:
                        irpm=int(rpm)*2//10
                        rpm=str(irpm)

                        if irpm==0:
                            rpm="0.0"

                        if irpm>=400:
                            rpm="400"

                        print("Speed = "+ rpm + " RPM")

                        try:
                            response_speed=requests.get('http://track-mypower.tk/measurements/wind_turbine_speed/new?rpm='+rpm+'&created_at='+str(date.now()),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
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
                            response_vibration = requests.get('http://track-mypower.tk/measurements/wind_turbine_vibration/new?m_ejex='+sendIter[0]+'&m_ejey='+sendIter[3]+'&m_ejez='+sendIter[6]+'&created_at='+str(date.now()),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
                            response_vibration = requests.get('http://track-mypower.tk/measurements/wind_turbine_vibration/new?m_ejex='+sendIter[2]+'&m_ejey='+sendIter[5]+'&m_ejez='+sendIter[8]+'&created_at='+str(date.now()),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
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

    if not internet:
        if len(sendBuffer3)==lenBufRPM:
            print("RPM Buffer is: ")
            lenBufRPM+=1
            print(sendBuffer3)
        if len(sendBuffer1)==lenBufAcc:
            print("Vibration Buffer is: ")
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
                response_vibration = requests.get('http://track-mypower.tk/measurements/wind_turbine_vibration/new?m_ejex='+sendAcc[0]+'&m_ejey='+sendAcc[3]+'&m_ejez='+sendAcc[6]+'&created_at='+str(date.now()),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
                response_vibration = requests.get('http://track-mypower.tk/measurements/wind_turbine_vibration/new?m_ejex='+sendAcc[2]+'&m_ejey='+sendAcc[5]+'&m_ejez='+sendAcc[8]+'&created_at='+str(date.now()),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
                if sendAcc in sendBuffer2:
                    sendBuffer2.remove(sendAcc)

            sendBuffer1=sendBuffer2[:]

        except:
            #print("There is no internet connection")
            continueB=True

    ############################################################################################
    ############################################################################################
    #                                     PANEL TURBINE RECEIVER                               #
    ############################################################################################
    ############################################################################################
    now = datetime.now()
    panelTime = now -then
    if panelTime.seconds > 180 :
        then = now
        try:
           Whour=SharkMeter.read_long(1099,3,True)
           Whour=Whour/100
           energy=Whour
           print("Whour: " + str(Whour))
        except IOError:
          print("Not Shark100 measurements available")
          Whour=0
          energy=Whour
          print("Whour: " + str(Whour))
        try:
          Voltage1=SharkMeter.read_float(999,3,2)
          Voltage2=Decimal(Voltage1)
          Voltage=round(Voltage2, 2)
          print("Voltage: " + str(Voltage))
        except IOError:
          Voltage=0
          print("Voltage: " + str(Voltage))
        try:
          AmpA1 = SharkMeter.read_float(1011,3,2)
          AmpA2 = Decimal(AmpA1)
          AmpA = round(AmpA2, 2)
          current=AmpA
          print("Current: " + str(AmpA))
        except IOError:
          AmpA = 0
          current=AmpA
          print("Current: " + str(AmpA))
        try:
          WTP1 = SharkMeter.read_float(1017,3,2)
          WTP2 = Decimal(WTP1)
          WTP = round(WTP2, 2)
          power=WTP
          print("Power: " + str(power))
        except IOError:
          WTP = 0
          power=WTP
          print("Power: " + str(power))
        try:
          PFTP1 = SharkMeter.read_float(1023,3,2)
          PFTP2 = Decimal(PFTP1)
          PFTP = round(PFTP2, 2)
          pf=PFTP
          print("PF: " + str(pf))
        except IOError:
          PFTP = 0
          pf=PFTP
          print("PF: " + str(pf))

        result=instance.read()
        adc = ReadChannel(pot)
        adc1=ReadChannel(pot1)
        adc2=ReadChannel(pot2)
        adc3=ReadChannel(pot3)
        adc4=ReadChannel(pot4)
        adc5=ReadChannel(pot5)
        #conversion a voltaje
        pot_volts= ConvertVolts(adc,2)
        pot_volts1= ConvertVolts(adc1,2)
        pot_volts2= ConvertVolts(adc2,2)
        pot_volts3=ConvertVolts(adc3,2)
        pot_volts4=ConvertVolts(adc4,2)
        pot_volts5=ConvertVolts(adc5,2)
        #conversion sensores de radiacion
        rad1=454.5454*pot_volts2+0.018
        rad2=454.5454*pot_volts3+0.018
        print("Radiacion 1: "+str(rad1)+"W/m^2")
        print("Radiacion 2: "+str(rad2)+"W/m^2")
        #radiacion promedio
        rad=(rad1+rad2)/2
        print("Radiacion promedio: "+str(rad)+"W/m^2")
        #conversion sensores de temperatura
        temp1=pot_volts4*100
        temp2=pot_volts5*100
        print("Temperatura del panel: "+str(temp1)+"°C")
        print("Temperatura ambiente: "+str(temp2)+"°C")
        flag = False
        # Print out results
        print ("--------------------------------------------")
        print ("Lectura ADC: ", adc)
        print ("Lectura ADC: ", adc1)
        print("Voltaje Baterias 1: {}V".format(pot_volts))
        print("Voltaje Baterias 2: {}V".format(pot_volts1))

        while flag != True:
          result=instance.read()
          if result.is_valid():
            # Read the light sensor data
            # Print out results
            t= result.temperature
            h= result.humidity
            print("Temperatura:  "+str(t)+"°C")
            print("Humedad: "+str(h)+"%")
            flag = True

        Sent.append(voltage)
        Sent.append(current)
        Sent.append(energy)
        Sent.append(power)
        Sent.append(latitude)
        Sent.append(longitude)
        Sent.append(date_time)
        Sent.append(t)
        Sent.append(h)
        Sent.append(pf)
        Sent.append(pot_volts)
        Sent.append(pot_volts1)
        Sent.append(rad)
        Sent.append(temp1)
        Sent.append(temp2)
          #Post variables in database
        try:
          conn = http.client.HTTPSConnection("track-mypower.rhcloud.com")
          conn.request("GET","/mysql/dataToDB.php?user=mpardo&pssd=pardo1234&voltage=%s&current=%s&energy=%s&power=%s&latitude=%s&longitude=%s&date_time=%s&temperature=%s&humidity=%s&pf=%s&vbatt1=%s&vbatt2=%s" % (Sent[0], Sent[1], Sent[2], Sent[3], Sent[4], Sent[5], Sent[6], Sent[7], Sent[8], Sent[9], Sent[10], Sent[11]))
          res = conn.getresponse()


          #Post variables in track.tk

          response = requests.get('http://track-mypower.tk/measurements/internal_conditions/new?temperature_int=%s&humidity_int=%s'%(Sent[7], Sent[8]),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))


          response2 = requests.get('http://track-mypower.tk/measurements/electrical/new?voltage_med1=%s&current_med1=%s&energy_med1=%s&power_med1=%s&pf_med1=%s&voltage_batt1=%s&voltage_batt2=%s'%(Sent[0], Sent[1], Sent[2], Sent[3],Sent[9], Sent[10], Sent[11]),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
          response3 = requests.get('http://track-mypower.tk/measurements/panel_conditions/new?temp_ext=%s&temp_panel=%s&radiation=%s'%(Sent[14],Sent[15],Sent[13]),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))

          del Sent[0:15]
          print(res.reason)
          print("Variables have been updated")
          internet=True
          # Xantrex Control
        except:
          Buffer.append(voltage)
          Buffer.append(current)
          Buffer.append(energy)
          Buffer.append(power)
          Buffer.append(latitude)
          Buffer.append(longitude)
          Buffer.append(date_time)
          Buffer.append(t)
          Buffer.append(h)
          Buffer.append(pf)
          Buffer.append(pot_volts)
          Buffer.append(pot_volts1)
          Buffer.append(rad)
          Buffer.append(temp1)
          Buffer.append(temp2)

       # GPIO.setmode(GPIO.BCM)
        if internet==True and len(Buffer)>0:
          while len(Buffer)%15 == 0:
            #Post variables in database
            try:
              conn = http.client.HTTPSConnection("track-mypower.rhcloud.com")
              conn.request("GET","/mysql/dataToDB.php?user=mpardo&pssd=pardo1234&voltage=%s&current=%s&energy=%s&power=%s&latitude=%s&longitude=%s&date_time=%s&temperature=%s&humidity=%s&pf=%s&vbatt1=%s&vbatt2=%s" % (Buffer[0], Buffer[1], Buffer[2], Buffer[3], Buffer[4], Buffer[5], Buffer[6], Buffer[7], Buffer[8], Buffer[9], Buffer[10], Buffer[11]))
              res = conn.getresponse()


              #Post variables in track.tk

              response = requests.get('http://track-mypower.tk/measurements/internal_conditions/new?temperature_int=%s&humidity_int=%s'%(Buffer[7], Buffer[8]),
                              auth=requests.auth.HTTPBasicAuth(
                                'admin',
                                'uninorte'))


              response2 = requests.get('http://track-mypower.tk/measurements/electrical/new?voltage_med1=%s&current_med1=%s&energy_med1=%s&power_med1=%s&pf_med1=%s&voltage_batt1=%s&voltage_batt2=%s'%(Buffer[0], Buffer[1], Buffer[2],Buffer[3], Buffer[9], Buffer[10], Buffer[11]),
                              auth=requests.auth.HTTPBasicAuth(
                                'admin',
                                'uninorte'))
              response3 = requests.get('http://track-mypower.tk/measurements/panel_conditions/new?temp_ext=%s&temp_panel=%s&radiation=%s'%(Buffer[14],Buffer[15],Buffer[13]),
                            auth=requests.auth.HTTPBasicAuth(
                              'admin',
                              'uninorte'))
              print(res.reason)
              print("Variables have been updated")
              del Buffer[0:15]
            except:
              internet = False

    ############################################################################################
    ############################################################################################
    #                                             NOP                                          #
    ############################################################################################
    ############################################################################################
    time.sleep(0.01)
