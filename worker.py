from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

import time

import subprocess as sp

import pickle

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self,main):
        QObject.__init__(self)
        self.Mainwindow = main
        self.run_state = True

        self.Mainwindow.progress_cancel_button.clicked.connect(self.run_state_check)


    def run_state_check(self):
        if self.run_state:
            self.run_state=False

    def calculate(self):

        self.Mainwindow.progress_cancel_button.show()

        data_array = []
        self.file_name_array=[]

        self.shel_counter = 0
        self.moke_counter = 0
        self.wave_counter = 0

        self.shel_value = 0
        self.moke_value = 0
        self.wave_value = 0

        # self.moke_loop = 0

        self.data_dict = {}
        self.data_dict['capture_data']={}
        # np.savetxt(f"{self.Mainwindow.save_folder[0]}/data_analyser_pos.csv",np.linspace(self.Mainwindow.initial_position,self.Mainwindow.final_position,self.Mainwindow.steps+1), delimiter=",")

        self.field_dir=0


        for i in self.Mainwindow.run_list:
            if i['run']==True:
                self.data_dict[i['name']]=i['data']
                if i['name']=='SHEL': self.data_dict['analyser positions']=np.linspace(self.Mainwindow.initial_position,self.Mainwindow.final_position,self.Mainwindow.steps+1)
                if i['name']=='MOKE': 
                    self.data_dict['field strength']=np.linspace(self.Mainwindow.initial_current,self.Mainwindow.final_current,self.Mainwindow.steps_current,endpoint=False)
                    self.data_dict['field strength']=np.hstack((self.data_dict['field strength'],np.linspace(self.Mainwindow.final_current,self.Mainwindow.initial_current,self.Mainwindow.steps_current,endpoint=False)))
                    self.data_dict['field strength']=np.hstack((self.data_dict['field strength'],np.linspace(self.Mainwindow.initial_current,-self.Mainwindow.final_current,self.Mainwindow.steps_current,endpoint=False)))
                    self.data_dict['field strength']=np.hstack((self.data_dict['field strength'],np.linspace(-self.Mainwindow.final_current,self.Mainwindow.initial_current,self.Mainwindow.steps_current,endpoint=False)))
                    self.data_dict['field strength']=np.hstack((self.data_dict['field strength'],np.linspace(self.Mainwindow.initial_current,self.Mainwindow.final_current,self.Mainwindow.steps_current+1)))

        self.data_dict['ISO']= self.Mainwindow.iso
        self.data_dict['Shutter Speed']= self.Mainwindow.ss
        pickle.dump(self.data_dict,open(f'{self.Mainwindow.save_folder[0]}/data.sav','wb'))
        self.run(self.Mainwindow.run_list)

        # self.data_dict['File Name']= self.file_name_array
        pickle.dump(self.data_dict,open(f'{self.Mainwindow.save_folder[0]}/data.sav','wb'))


        self.run_state=True
        self.finished.emit()

    
    def run(self,list):
        if list[0]['run']:
            for j in range(5):
                try:
                    for i in np.linspace(list[0]['data'][j][0],list[0]['data'][j][1],int(list[0]['data'][j][2]),bool(list[0]['data'][j][3])):
                        if self.run_state==False:
                            break

                        if list[0]['name']=='SHEL':
                            i = np.round(i, decimals = 4)
                            self.SHEL(i)

                            if self.shel_counter==list[0]['data'][0][2]:
                                self.shel_counter=0
                            self.shel_counter+=1
                            
                        elif list[0]['name']=='MOKE':
                            if(i>=0):
                                self.field_switch(1)
                            if(i<0):
                                self.field_switch(2)
                            # if self.moke_counter==list[0]['data'][0][2]:
                            #     self.moke_counter=0
                            # self.moke_counter=np.round(i, decimals = 3)
                            i=abs(np.round(i, decimals = 3))
                            self.MOKE(i)
                            # self.moke_loop=j
                            if ((self.moke_counter==list[0]['data'][4][2]) and (j==4)):
                                self.moke_counter=0
                            self.moke_counter+=1

                        elif list[0]['name']=='wave':
                            i = np.round(i)
                            self.wave(i)
                            if self.wave_counter==list[0]['data'][j][2]:
                                self.wave_counter=0
                            self.wave_counter+=1
                        
                        # print(len(list))
                        if len(list)==1:
                            self.capture()
                            # pass

                        else:
                            
                            self.run(list[1:])
                except:
                    pass
                    # try:
                    #     self.turnoff()
                    # except:
                    #     pass
                                    
        else:
            if len(list)==1:
                self.capture()
                # pass

            else:
                self.run(list[1:])

    def SHEL(self,value):
        self.shel_value=value
        # print('reached')
        self.Mainwindow.rs.moveabs(value)
        self.Mainwindow.rs.wait_for_stop()
        # time.sleep(0.5)
        pass

    def MOKE(self,value):
        self.moke_value = value
        self.Mainwindow.rm.setCurrent(value)
        time.sleep(0.1)
        # while float(self.Mainwindow.rm.getCurrent().strip('\n'))!=value:
        #     pass
        pass

    def wave(self,value):
        self.wave_value=value
        self.Mainwindow.nkt.set_wavelength(value)

    def field_switch(self,field_dir):
        self.Mainwindow.ard.switchfield(field_dir)

    def capture(self):
        self.data_dict['capture_data'][f'img{self.moke_counter}_{self.wave_counter}_{self.shel_counter}.png']={"shel":self.shel_value,'moke':self.moke_value,'wave':self.wave_value}
        self.StillCmd = f"raspistill -ISO {self.Mainwindow.iso} -ss {self.Mainwindow.ss} -ex off --timeout 1  --output {self.Mainwindow.save_folder[0]}/img{self.moke_counter}_{self.wave_counter}_{self.shel_counter}.png --nopreview"
        sp.run(self.StillCmd,shell=True)
        self.file_name_array.append(f'img{self.moke_counter}_{self.shel_counter}.png')