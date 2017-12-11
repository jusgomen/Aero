# Aero
This repo stores a solution for remote sensing using NRF24L01 and NRF24L01+ modules for communication. Speed and vibration are measured from a Wind turbine. Each variable is measured and proccesed independently using two Texas Instruments MSP430, conforming two kits. 

First the speed is sent to the other microcontroller, and that one sends vibration and speed data to a Raspberry Pi. This computer receives the data and store it into a relational database. A buffer is implemented,for the case internet connection is lost.
