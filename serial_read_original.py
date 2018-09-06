 #!/usr/bin/env python3
 
import time
import serial
 
# voice command functions
def empty():
  pass
 
 
def one():
  print('17')
 
 
def two():
  print('18')
 
 
def three():
  print('19')
 
 
def four():
  print('20')
 
 
def five():
  print('21')
 
 
if __name__ == '__main__':
 
    # integers mapped to voice command functions
    commands = {0:empty, 17:one, 18:two, 19:three, 20:four, 21:five}
 
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
        data_byte = ser.read() # read serial data (one byte)
        int_val = int.from_bytes(data_byte, byteorder='big') # convert to integer
        print(int_val)
        commands[int_val]() # call voice command function
    except KeyboardInterrupt:
      print('Exiting Script')
