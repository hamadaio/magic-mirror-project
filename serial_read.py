#!/usr/bin/env python3
 
import time
import serial
 
# voice command functions
def empty():
  print("nothing")
  #pass
 
def one():
  print('com1')
 
 
def two():
  print('com2')
 
 
def three():
  print('com3')
 
 
def four():
  print('com4')
 
 
def five():
  print('com5')

def error():
  print('error!!')
 
 
if __name__ == '__main__':
 
    # integers mapped to voice command functions
    commands = {0:empty, 11:one, 12:two, 13:three, 14:four, 15:five, 82:error}
 
    # serial settings
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
        int_val = (str(data_byte)[9:11])
        if len(int_val) == 0:
          continue
        #print(int(str(data_byte)[9:11]))
        #int_val = int.from_bytes(data_byte, byteorder='big') # convert to integer
        #print(type(data_byte))
        print(int_val)
        commands[int(int_val)]() # call voice command function
    except KeyboardInterrupt:
      print('Exiting Script')
