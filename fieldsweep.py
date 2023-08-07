from socket import timeout
import serial
class arduino_fieldSwitch:
    """arduino field switch Class"""
    def __init__(self,port):
        self.arduino = serial.Serial(port=port,baudrate=115200,timeout=0.1,write_timeout=0.1)
        self.inst = None
        pass
    def switchfield(self,field_dir):
            try:
                self.arduino.write("{}\n".format(field_dir).encode(encoding="ascii")) 
                if self.arduino.readline().decode("utf-8")=='':
                    return False
                else:
                    return True
            except serial.serialutil.SerialTimeoutException:
                return False
            pass
    def disconnect(self):
        self.switchfield(0)
        self.arduino.close()
