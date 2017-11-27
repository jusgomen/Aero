#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sun Nov  5 05:23:45 2017

@author: juangonzalez
"""

# -*- coding: utf-8 -*-

#Librería: Base de datos de PostgreSQL
import psycopg2

# Librería: Numpy, maneja matrices en Python
import numpy as np

# Librería: Datetime, obtiene la fecha actual y opera sobre ella
from datetime import datetime, timedelta

# Librería: Requests, hace peticiones HTTP
import requests

def queryData(minutesQ=25, limit="200"):
    
    success=False
    
    #Conexión con base de datos, se establecen parámetros de login
    conn = psycopg2.connect(host="138.197.104.91", port="5432",database="track_my_power_app_production", user="admin", password="mauro1234")
    cur = conn.cursor()
    
    dq= datetime.now() - timedelta(minutes = minutesQ)
    date_query=str(dq)[:19]
    
    #Query de datos de los últimos 25 minutos (approx 375 medidas, 15 por minuto)
    query="SELECT m_ejex, m_ejey, m_ejez FROM wind_turbine_vibration_measurements WHERE created_at > '"+date_query+"' ORDER BY created_at DESC LIMIT "+limit
    cur.execute(query)
    num = cur.rowcount;
    print("Numero de medidas halladas: ", num)
    
    #Construcción de Numpy Array con el resultado de la query
    row = cur.fetchone()
    if row==None:
        print("No se devolvió nada")
    else:
        #Creación del Array
        x_result=np.array([row[0]])
        y_result=np.array([row[1]])
        z_result=np.array([row[2]])
        count=1
        success=True
    
    while row is not None:
        row = cur.fetchone()
        if row is not None:
            x_result=np.append(x_result, [row[0]])
            y_result=np.append(y_result, [row[1]])
            z_result=np.append(z_result, [row[2]])
            count+=1
            if count>=2000:
                break
    if success:
        return (x_result, y_result, z_result, success)
    else:   
        return (0, 0, 0, success) 


def getFFT(BufferX, BufferY, BufferZ, Fs=200):
    
    #These are Python lists containing Buffered Data for Vibration
    #For example, if 2 measurements were saved, BufferX would be:
    #  BufferX=[min1, max1, min2, max2]
    xx=BufferX
    yy=BufferY
    zz=BufferZ
    
    num=len(xx)    
    x_result=np.array(xx)
    y_result=np.array(yy)
    z_result=np.array(zz)
    
    Fs = 200.0
    N = num
    T = 1.0 / Fs
    f = np.linspace(-1.0/(2.0*T), 1.0/(2.0*T), N)
    
    x = x_result
    xf = np.fft.fft(x,norm="ortho")
    xf = np.fft.fftshift(xf)
    
    
    y = y_result
    yf = np.fft.fft(y,norm="ortho")
    yf = np.fft.fftshift(yf)
    
    
    z = z_result
    zf = np.fft.fft(z,norm="ortho")
    zf = np.fft.fftshift(zf)
    
    return (f[f>0], abs(xf[f>0]), abs(yf[f>0]), abs(zf[f>0]))

def getRequest(freq, x_fft, y_fft, z_fft):
	
    n=len(freq)
    absX=x_fft.tolist()
    absY=y_fft.tolist()
    absZ=z_fft.tolist()
    
    success=True
    
    try:
        for i in range(n):
            requests.get('http://track-mypower.tk/measurements/wind_turbine_frequencies/new?mag='+str(absX[i])+'&mag_y='+str(absY[i])+'&mag_z='+str(absZ[i])+'&freq='+str(freq[i]),
				                auth=requests.auth.HTTPBasicAuth(
				                  'admin',
				                  'uninorte'))	
    except:
        success=False
        pass
    
    return success


############################################################
##                         MAIN                           ##
############################################################


#Obtains data from the Database
(x_result, y_result, z_result, success) =queryData(5000)

if success: 
    #Computes FFT
    (f, xf, yf, zf)=getFFT(x_result, y_result, z_result)
    
    #Uploads FFT result to Database
    uploaded=getRequest(f, xf, yf, zf)


