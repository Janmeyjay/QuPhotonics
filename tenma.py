from socket import timeout
import serial
import time
class powerControl:
    """Tenma Power Control Class"""
    def __init__(self,port):
        self.rm = serial.Serial(port=port,baudrate=115200,timeout=0.1,write_timeout=0.1)
        self.inst = None
        pass

    def connect(self):
        try:
            self.rm.write(b'*IDN?\n')
            # print(self.rm.readline())
            if self.rm.readline().decode("utf-8")=='':
                return False
            else:
                return True
        except serial.serialutil.SerialTimeoutException:
            return False
        pass

    def setCurrent(self,value):
        self.rm.write(bytes(f'ISET1:{value}\n', 'utf-8'))
        self.rm.write(b'ISET?\n')
        return self.rm.readline().decode("utf-8")


    def setVoltage(self,value):
        self.rm.write(bytes(f'VSET:{value}\n', 'utf-8'))
        self.rm.write(b'VSET?\n')
        return self.rm.readline().decode("utf-8")
        pass
    def setOCP(self):
        self.rm.write(b'*IDN?\n')
        pass

    def setOCV(self):
        self.rm.write(b'*IDN?\n')
        pass

    def getCurrent(self):
        self.rm.write(b'ISET?\n')
        return self.rm.readline().decode("utf-8")
        pass

    def getVoltage(self):
        self.rm.write(b'VSET?\n')
        return self.rm.readline().decode("utf-8")
        pass

    def output(self,state):
        self.rm.write(bytes(f'OUT{state}\n','utf-8'))
        return True
        pass
    
    def output_state(self):
        self.rm.write(b'OUT?\n')
        if self.rm.readline() == b'0\n':
            return True
        else:
            return False
        pass
    