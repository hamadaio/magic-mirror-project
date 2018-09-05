#!/usr/bin/env python3
'''
original code: https://www.piddlerintheroot.com/voice-recognition/
edited by MagicMirror group 2018-09-05

'''
import time
import serial
 
# voice command functions
def empty():
  print("Listening...")
  #pass
  
def one():
  print('command 1')
  
def two():
  print('command 2')
 
def three():
  print('command 3')
 
def four():
  print('command 4')
 
def five():
  print('command 5')
 
 
if __name__ == '__main__':
 
    # integers mapped to voice command functions
    commands = {0:empty, 11:one, 12:two, 13:three, 14:four, 15:five}
 
    # serial port settings for raspberry pi
    ser = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1
    )
    ser.flushInput()
 
    # run twice to make sure it's in the correct mode
    for i in range(2):
      ser.write(serial.to_bytes([0xAA])) # set speech module to waiting state
      time.sleep(0.5)
      ser.write(serial.to_bytes([0x21])) # import group 1 and await voice input
      time.sleep(0.5)
    print('init complete')
    
    try:
      while True:
        data_byte = ser.read(11) # read serial data (one byte)
        int_val = (str(data_byte)[9:11]) # convert incoming stream (bytes) to string
        if not int_val: # checking if the received stream it is an empty 'string'
          continue
        #print(int(str(data_byte)[9:11]))
        #int_val = int.from_bytes(data_byte, byteorder='big') # convert to integer
        #print(type(data_byte))
        print(int_val)
        commands[int(int_val)]() # call voice command function & convert to 'int'
    except KeyboardInterrupt:
      print('Exiting Script')
