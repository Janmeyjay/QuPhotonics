import serial as ser
import numpy as np
import time

class NKT():
    """ NKT class """
    def __init__(self,port):
        self.nkt = ser.Serial(port=port,baudrate=230400)
        pass

    def readline(self):
        a = self.nkt.read().decode('utf-8')
        ret = a
        while a!='\r':
            a = self.nkt.read().decode('utf-8')
            ret=ret+a
        return ret
 
    def write(self,fun):
        fun = bytes(fun,'utf-8')
        self.nkt.write(fun)
        return self.readline()


    def connect(self):
        try:
            self.nkt.write(b':rsern\r')
            self.readline()
            return True
        except:
            return False
            
    def start(self):
        self.nkt.write(b':rsern\r')
        print(self.readline())
        self.nkt.write(b':wmbren 0 1\r')
        print(self.readline())
        self.nkt.write(b':wmphase 0\r')
        print(self.readline())
        self.nkt.write(b':wmhome 0\r')
        print(self.readline())

    def get_status(self):
        return self.write(':rmstate \r')

    def set_wavelength(self,nm,side='right'):
        if side=='right':
            stageoffset = -126.403
            offset = -2.155992912594084
            factor = 1.001359996536545
            period = 690
            angle = -180-stageoffset-offset+np.round(np.rad2deg(np.arcsin(nm/(2*factor*period))),decimals=4)

            a = 360
            b = 6553600

            position = angle*(b/a)
            value = bytes(f':wmpos 0 {position}\r','utf-8')
            self.nkt.write(value)
            self.readline()
            status = self.get_status()[2:]
            while 'F' not in status:
                status = self.get_status()[2:]
                pass
            return position

        elif side=='left':
            stageoffset = 125.372
            offset = -2.457149873032229
            factor = 0.9993838650157658
            period = 1140

            angle = 180-stageoffset-offset+np.round(np.rad2deg(np.arcsin(nm/(2*factor*period))),decimals=4)
            a = 360
            b = 6553600

            position = angle*(b/a)
            return position

    def get_wavelength(self,side ='right'):
        if side=='right':
            self.nkt.write(b':rmpos 0\r')

            # print(self.readline()[2:])
            position = float(self.readline()[2:])

            a = 360
            b = 6553600
            angle = position *(a/b)

            stageoffset = -126.403
            offset = -2.155992912594084
            factor = 1.001359996536545
            period = 690
            nm = 2*factor*period*np.round(np.sin(np.deg2rad(angle+stageoffset+offset-180)),decimals=4)

            return nm

        elif side=='left':
            self.nkt.write(b':rmpos 0\r')

            # print(self.readline()[2:])
            position = float(self.readline()[2:])

            a = 360
            b = 6553600
            angle = position *(a/b)

            stageoffset = 125.372
            offset = -2.457149873032229
            factor = 0.9993838650157658
            period = 1140
            nm = 2*factor*period*np.round(np.sin(np.deg2rad(-angle-stageoffset-offset+180)),decimals=4)

            return nm


if __name__=='__main__':
    print("hello")