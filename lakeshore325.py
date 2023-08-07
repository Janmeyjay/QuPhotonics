from socket import timeout
import serial

class temp_Control:
    "lakeshore control class"
    def __init__(self,port):
        self.rm = serial.Serial(port='port',timeout=0.1,write_timeout=0.1,parity=serial.PARITY_ODD,)
        self.inst = None
        pass
    def connect(self):
        try:
            self.rm.write(b'*IDN?\r\n')
            # print(self.rm.readline())
            if self.rm.readline().decode("utf-8")=='':
                return False
            else:
                return True
        except serial.serialutil.SerialTimeoutException:
            return False
        pass