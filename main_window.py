# import system module
from re import M, search
from shelve import Shelf
import sys
import atexit

import faulthandler

# import pickle to save data for loading later
import pickle
from tempfile import tempdir
from traceback import print_tb

# import some PyQt5 modules
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore
from PyQt5.QtGui import QImage
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import QTimer, QThread
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtWidgets import QFileDialog
from PyQt5.uic import loadUi


import numpy as np


# import Opencv module
import cv2

# import some system library
import time # for calculating the fps
import subprocess as sp # for running 'raspividyuv' and 'raspistill' in shell
import os

# import MatPlotLib module for plotting 
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

#import Rotation stage library
try:
    from k10cr1 import K10CR1 as rs
    
except ModuleNotFoundError or ImportError:
    print("No Thorlabs library")
    pass

# improt TENMA
from tenma import powerControl

# import NKT
from filter import NKT

#import arduino_fieldsweep
from fieldsweep import arduino_fieldSwitch as ard


# import serial communication library
import serial 

#import library for acquiring images
from worker import Worker

class MainWindow(QMainWindow):

    # class constructor
    def __init__(self):
        # call QWidget constructor
        QMainWindow.__init__(self)

        self.ui = loadUi("ui_main_window.ui",self) # load the UI from ui file made using Qt Designer

        self.log = "" # variable called by log button


        # create a timer
        self.timer = QTimer() # Timer defined to refresh frames

        # set timer timeout callback function
        self.timer.timeout.connect(self.viewCam)
        (self.true_width,self.true_height) = (640,640)
        self.bytesPerFrame = self.true_width * self.true_height
        self.videoCmd = "raspividyuv -w "+str(self.true_width)+" -h "+str(self.true_height)+" --output - --timeout 0 --framerate "+str(24)+" --luma --nopreview"
        self.videoCmd = self.videoCmd.split()

        # set connect_button callback clicked  function 
        self.ui.connect_button.clicked.connect(self.controlTimer)
        
        self.ui.test_button.clicked.connect(self.test_raspistill) # test button for checking ISO and Shutterspeed

        self.start_time = time.time()

        # Circle crop of image
        self.dot_loc= (0,0) # all variables set to zero if crop not required
        self.x = 0
        self.y = 0
        self.radius = 0
        self.ui.image_label.mousePressEvent = self.getPos # to get the mouse click location
        self.ui.circlecenter_button.clicked.connect(self.centerDot) # manually set the center
        self.ui.circleradius_button.clicked.connect(self.setRadius) # manually set the radius
        

        # initiate all the progress bar as class variables for use of Worker class
        MainWindow.progress_bar_1 = self.ui.progress_bar_1
        MainWindow.progress_bar_1.hide()
        MainWindow.progress_bar_1.setValue(0)
        
        MainWindow.progress_bar_2 = self.ui.progress_bar_2
        MainWindow.progress_bar_2.hide()
        MainWindow.progress_bar_2.setValue(0)

        MainWindow.progress_bar_3 = self.ui.progress_bar_3
        MainWindow.progress_bar_3.hide()
        MainWindow.progress_bar_3.setValue(0)


        # initiate all the progress labels as class variables for use of Worker class
        MainWindow.progress_label_1 = self.ui.progress_label_1
        MainWindow.progress_label_1.hide()

        MainWindow.progress_label_2 = self.ui.progress_label_2
        MainWindow.progress_label_2.hide()

        MainWindow.progress_label_3 = self.ui.progress_label_3
        MainWindow.progress_label_3.hide()


        # initiate all the cancel button as class variables for use of Worker class
        MainWindow.run_state = True # variable checked but cancel button during calculation
        MainWindow.progress_cancel_button = self.ui.progress_cancel_button
        MainWindow.progress_cancel_button.hide()
        MainWindow.progress_cancel_button.clicked.connect(MainWindow.run_state_check)


        #  ANALYSER
        # initiate the variables
        self.position = 0
        self.initial_position = 0
        self.centre_position = 0
        self.final_position = 0
        self.rs_connected = False # initially the analyser isnt connected
        self.ui.search_analyser_button.clicked.connect(lambda: self.search_port(self.ui.analyser_combo))
        self.ui.connect_analyser_button.clicked.connect(self.connect_analyser)
        self.ui.home_button.clicked.connect(self.home_analyser)
        self.ui.initial_button.clicked.connect(lambda: self.positionSet(self.ui.initial_text))
        self.ui.centre_button.clicked.connect(lambda: self.positionSet(self.ui.centre_text))
        self.ui.final_button.clicked.connect(lambda: self.positionSet(self.ui.final_text))


        #Arduino
        self.ard_connected = False
        self.ui.search_power_button.clicked.connect(lambda: self.search_port(self.ui.arduino_combo))
        self.ui.connect_ard_pushButton.clicked.connect(self.ard_connect)
        # self.ui.ard_


        # POWER CONTROL
        self.is_connected_power = False # initially the controller isnt connected
        self.ui.search_power_button.clicked.connect(lambda: self.search_port(self.ui.power_combo))
        self.ui.connect_power_button.clicked.connect(self.connect_power)
        self.ui.get_current_button.clicked.connect(self.get_current_power)
        self.ui.get_voltage_button.clicked.connect(self.get_voltage_power)  
        self.ui.set_voltage_button.clicked.connect(lambda: self.set_voltage_power(self.ui.set_voltage_text))
        self.ui.set_initial_current_button.clicked.connect(lambda: self.set_current_power(self.ui.set_initial_current_text))
        self.ui.set_final_current_button.clicked.connect(lambda: self.set_current_power(self.ui.set_final_current_text))
        self.ui.power_on_Button.clicked.connect(self.power_output)

        # LLTF
        self.is_connected_nkt=False # initially the nkt controller isnt connected
        self.ui.search_nktlltf_button.clicked.connect(lambda: self.search_port(self.ui.nktlltf_combo))
        self.ui.connect_nktlltf_button.clicked.connect(self.connect_lltf)
        self.ui.set_wavelength_button.clicked.connect(lambda: self.set_wavelength_lltf(self.ui.set_wavelength_text))
        self.ui.home_nktlltf_button.clicked.connect(self.home_lltf)
        self.ui.set_initial_wavelength_button.clicked.connect(lambda: self.set_wavelength_lltf(self.ui.set_initial_wavelength_text))
        self.ui.set_final_wavelength_button.clicked.connect(lambda: self.set_wavelength_lltf(self.ui.set_final_wavelength_text))


        self.ui.log_button.clicked.connect(lambda: self.show_log()) # shows the log ##REQUIRES UPDATE

        self.ui.calculate_button.clicked.connect(self.calculate) # the final calculate button



    def search_port(self,elem):
        self.ports = sorted(serial.tools.list_ports.comports())
        elem.clear()
        elem.addItem(" ")
        for port, desc, hwid in self.ports:
            elem.addItem(desc)

    def ard_connect(self):
        if self.ard_connected == False:
            try:
                MainWindow.ard = ard(self.ports[self.ui.arduino_combo.currentIndex()-1][0])
                self.log += 'arduino connected \n'
                MainWindow.ard.switchfield(0)
                self.ui.connect_ard_pushButton.setText("Off")
                self.ard_connected = True
            except NameError or AttributeError:
                self.show_warning("No Arduino Connected")
                self.ard_connected = False
        else:
            MainWindow.ard.disconnect()
            self.ui.connect_ard_pushButton.setText("On")
            self.ard_connected = False
            pass

    def connect_lltf(self):
        self.nkt = NKT(self.ports[self.ui.nktlltf_combo.currentIndex()-1][0])
        self.is_connected_nkt =  self.nkt.connect()
        if self.is_connected_nkt==False:
            self.show_warning("NKT Controller not Connected!")
        pass
    
    def set_wavelength_lltf(self,wave):
        try:
            if self.is_connected_nkt == True:
                nm = int(wave.text())
                self.nkt.set_wavelength(nm)

            else: 
                self.show_warning("NKT Controller not Connected!")
        except AttributeError:
            self.show_warning("NKT Controller not Connected!")
        pass

    def home_lltf(self):
        try:
            if self.is_connected_nkt == True:
                self.nkt.start()
            else: 
                self.show_warning("NKT Controller not Connected!")
        except AttributeError:
            self.show_warning("NKT Controller not Connected!")
        pass
    def connect_power(self):
        self.rm = powerControl(self.ports[self.ui.power_combo.currentIndex()-1][0])
        self.is_connected_power =  self.rm.connect()
        if self.is_connected_power==False:
            self.show_warning("Power Controller not Connected!")
        pass

    def get_current_power(self):
        try:
            if self.is_connected_power == True:
                current = self.rm.getCurrent().strip('\n')
                self.ui.current_label.setText(f"{current} A")
            else: 
                self.show_warning("Power Controller not Connected!")
        except AttributeError:
            self.show_warning("Power Controller not Connected!")
        pass

    def get_voltage_power(self):
        try:
            if self.is_connected_power == True:
                voltage = self.rm.getVoltage().strip('\n')
                self.ui.voltage_label.setText(f"{voltage} V")
            else: 
                self.show_warning("Power Controller not Connected!")
        except AttributeError:
            self.show_warning("Power Controller not Connected!")
        pass

    def set_voltage_power(self,box):
        try:
            if self.is_connected_power == True:
                voltage = self.rm.setVoltage(box.text()).strip('\n')
                self.ui.voltage_label.setText(f"{voltage} V")
            else: 
                self.show_warning("Power Controller not Connected!")
        except AttributeError:
            self.show_warning("Power Controller not Connected!")
    
    def set_current_power(self,box):
        try:
            if self.is_connected_power == True:
                current = self.rm.setCurrent(box.text()).strip('\n')
                self.ui.current_label.setText(f"{current} A")
            else: 
                self.show_warning("Power Controller not Connected!")
        except AttributeError:
            self.show_warning("Power Controller not Connected!")

    def power_output(self):
        try:
            if self.is_connected_power == True:
                status= self.rm.output_state()
                if status == True:
                    self.rm.output(1)
                    self.ui.power_on_Button.setText("On")
                else:
                    self.rm.output(0)
                    self.ui.power_on_Button.setText("Off")
            else:
                self.show_warning("Power Controller not Connected!")
        except AttributeError:
            self.show_warning("Power Controller not Connected!")

    def connect_analyser(self):
        if self.rs_connected == False:
            try:
                MainWindow.rs = rs(self.ports[self.ui.analyser_combo.currentIndex()-1][0])

                self.log += 'Homing... \n'
                MainWindow.rs.home() # reseting the analyser position to zero
                self.position = MainWindow.rs.getpos()
                MainWindow.rs.wait_for_stop()
                self.ui.connect_analyser_button.setText("Disconnect")
                self.rs_connected = True
            except NameError or AttributeError:
                self.show_warning("No Analyzer Connected")
                self.rs_connected = False
        else:
            MainWindow.rs.disconnect()
            self.ui.connect_analyser_button.setText("Connect")
            self.rs_connected = False
            pass

    def home_analyser(self):
        if self.rs_connected == True:
            self.log += 'Homing... \n'
            MainWindow.rs.home() # reseting the analyser position to zero
            self.position = MainWindow.rs.getpos()
            # MainWindow.rs.wait_for_stop()
        else:
            self.show_warning("No Analyzer Connected")



    def test_raspistill(self):
        if self.timer.isActive():
            self.controlTimer()
        StillCmd = f"raspistill  -ISO {int(self.ui.iso_text.text())} -ss {int(self.ui.ss_text.text())} -ex off --output /home/pi/Documents/try/tmp.png -t 1 --nopreview"
        sp.call(StillCmd, shell=True) # start the camera  
        image = cv2.imread('/home/pi/Documents/try/tmp.png')
        cv2.imshow("Image",image)

        if not self.timer.isActive():
            self.controlTimer()

    def run_state_check(self):
        if MainWindow.run_state:
            MainWindow.run_state=False
        else:
            MainWindow.run_state=True


    def setRadius(self):
        self.radius = int(self.ui.circleradius_text.text())
    def getPos(self , event):
        if self.timer.isActive():
            # get the x and y position of mouse click w.r.t image_label
            self.x = event.pos().x()
            self.y = event.pos().y() 
            
            # convert x and y to be w.r.t image
            if self.c < self.C:
                self.x = int((self.x - (self.W-self.w*(self.H/self.h))/2)*self.h/self.H)
                self.y = int(self.y*self.h/self.H)
                if event.button()==QtCore.Qt.LeftButton:
                    self.dot_loc = (self.x,self.y)
                    self.ui.circlecenter_text.setText(str(self.dot_loc))
                elif event.button()==QtCore.Qt.RightButton:
                    self.radius = int(np.sqrt((self.dot_loc[0]-self.x)**2+(self.dot_loc[1]-self.y)**2))
                    self.ui.circleradius_text.setText(str(self.radius))
            elif self.c > self.C:
                self.y = int((self.y - (self.H-self.h*(self.W/self.w))/2)*self.w/self.W)
                self.x = int(self.x*self.w/self.W)
                if event.button()==QtCore.Qt.LeftButton:
                    self.dot_loc = (self.x,self.y)
                    self.ui.circlecenter_text.setText(str(self.dot_loc))
                elif event.button()==QtCore.Qt.RightButton:
                    self.radius = int(np.sqrt((self.dot_loc[0]-self.x)**2+(self.dot_loc[1]-self.y)**2))
                    self.ui.circleradius_text.setText(str(self.radius))

            # TO DO
            elif event.key()=='q':
                print('check')


    def centerDot(self):
        text = str(self.ui.circlecenter_text.text())
        text = text.split(',')
        self.dot_loc = (int(text[0][1:]),int(text[1][:-1]))

    def viewCam(self):

        # read image in BGR format
        self.cameraProcess.stdout.flush() # discard any frames that we were not able to process in time
        # Parse the raw stream into a numpy array
        image = np.frombuffer(self.cameraProcess.stdout.read(self.bytesPerFrame), dtype=np.uint8)
        image.shape = (self.true_height,self.true_width)

        # print(image.shape)
        dim = (self.ui.image_label.width(), self.ui.image_label.height())
        self.C = dim[0]/dim[1]
        # image = cv2.resize(image, (640,480))
        # get image infos
        height, width = image.shape
        
        step =  width
        
        # print(dim)
        
        self.c = width/height
        # print(self.c,self.C)
        self.w = width
        self.h = height
        self.W = dim[0]
        self.H = dim[1]
        if self.ui.tabWidget_2.currentIndex()==0:
            self.resolution = f'{width}x{height}'
            if self.dot_loc[0]>0 and self.dot_loc[1]>0 and self.radius>0:

                mask = np.zeros(image.shape[:2], dtype="uint8")
                cv2.circle(mask,self.dot_loc,self.radius,255,-1)
                image = cv2.circle(image, self.dot_loc, radius=0, color=(50, 50,50), thickness=2)
                image = cv2.bitwise_and(image,image,mask=mask)


            self.log += f"Resolution: {self.resolution}\n"
            img = cv2.cvtColor( image, cv2.COLOR_GRAY2BGR )
            
            
            self.end_time = time.time()
            self.elapsed_time = self.end_time-self.start_time
            self.fps = 1/self.elapsed_time
            self.start_time = time.time()
            self.ui.imagedata_label.setText(f"Resolution: {self.resolution} \t FPS : {int(self.fps)} Position : {self.position}")

            # create QImage from image
            qImg = QPixmap.fromImage(QImage(img.data, width,height , width*3, QImage.Format_RGB888))
            qImg = qImg.scaled(dim[0]-1,dim[1]-1, QtCore.Qt.KeepAspectRatio)

            # show image in img_label
            self.ui.image_label.setPixmap(qImg)
        elif self.ui.tabWidget_2.currentIndex()==1:
            intensity_profile_row = np.mean(image,axis=1)
            length_row = np.arange(height)
            # print('test 1')
            self.ui.MplWidget_row.canvas.axes.clear()
            self.ui.MplWidget_row.canvas.axes.xaxis.set_minor_locator(MultipleLocator(50))
            self.ui.MplWidget_row.canvas.axes.grid(which='minor', color='r', linestyle='--')
            self.ui.MplWidget_row.canvas.axes.grid(which='major', color='r', linestyle='--')
            self.ui.MplWidget_row.canvas.axes.plot(length_row, intensity_profile_row)
            self.ui.MplWidget_row.canvas.draw()

            intensity_profile_column = np.mean(image,axis=0)
            length_column = np.arange(width)
            # print('test 1')
            self.ui.MplWidget_column.canvas.axes.clear()            
            self.ui.MplWidget_column.canvas.axes.xaxis.set_minor_locator(MultipleLocator(50))
            self.ui.MplWidget_column.canvas.axes.grid(which='minor', color='r', linestyle='--')
            self.ui.MplWidget_column.canvas.axes.grid(which='major', color='r', linestyle='--')
            self.ui.MplWidget_column.canvas.axes.plot(length_column, intensity_profile_column)
            self.ui.MplWidget_column.canvas.draw()
        return None

    
    def positionSet(self,box):
        try:
            self.position = float(box.text())
            MainWindow.rs.moveabs(self.position)
            self.log += f"Position set to {self.position}\n"
        except ValueError:
            self.show_warning("Please input positive floats!")
        return None

    # start/stop timer
    def controlTimer(self):
        # if timer is stopped
        if not self.timer.isActive():
            # create video capture
            self.cameraProcess = sp.Popen(self.videoCmd, stdout=sp.PIPE, bufsize=1) # start the camera
            atexit.register(self.cameraProcess.terminate) # this closes the camera process in case the python scripts exits unexpectedly
            self.log += f'Camera Initiated\n'

            # start timer
            self.timer.start(20)

            # update connect_button text
            self.ui.connect_button.setText("Stop")


        # if timer is started
        else:
            # stop timer
            self.timer.stop()

            # release video capture
            self.cameraProcess.terminate()

            # update connect_button text
            self.ui.connect_button.setText("Connect")
            self.ui.imagedata_label.setText("Disconnected!")

    def show_log(self):
        QMessageBox.about(self, "Log", self.log)

    def show_warning(self,warning):
        QMessageBox.warning(self, "Warning", warning)


    def calculate(self):
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setAcceptMode(QFileDialog.AcceptOpen)
        dialog.setLabelText(QFileDialog.FileName,"Folder Name")
        dialog.setLabelText(QFileDialog.Accept,"Save")
        if dialog.exec():
            MainWindow.save_folder = dialog.selectedFiles()
            os.mkdir(MainWindow.save_folder[0])

        MainWindow.ss =int(self.ui.ss_text.text())
        MainWindow.iso =int(self.ui.iso_text.text())
        
        MainWindow.dot_loc_ratio_x = self.dot_loc[0]/self.true_width  
        MainWindow.dot_loc_ratio_y = self.dot_loc[1]/self.true_height 

        (MainWindow.true_width,MainWindow.true_height) = (3040,3040)
        MainWindow.bytesPerFrame = MainWindow.true_width * MainWindow.true_height
        if self.timer.isActive():
            self.controlTimer()

        self.log += f'Calculation Initiated\n'

        MainWindow.shel_check = self.ui.shel_check.isChecked()
        MainWindow.moke_check = self.ui.moke_check.isChecked()
        MainWindow.temp_check = self.ui.temp_check.isChecked()

        MainWindow.run_list = []


        if self.ui.moke_check.isChecked(): 
            MainWindow.rm = self.rm
            print("done")
            if not self.is_connected_power:
                self.show_warning("Power not connected")
                return None
            MainWindow.initial_current = float(self.ui.set_initial_current_text.text())
            MainWindow.final_current = float(self.ui.set_final_current_text.text())
            MainWindow.steps_current = int(self.ui.step_current_text.text())
            MainWindow.MOKE_list = {'run':True,'name':'MOKE','data':[MainWindow.initial_current,MainWindow.final_current,MainWindow.steps_current,False],'object':MainWindow.rm}
            MainWindow.MOKE_list['data']=np.stack((MainWindow.MOKE_list['data'],[MainWindow.final_current,MainWindow.initial_current,MainWindow.steps_current,False],[MainWindow.initial_current,-MainWindow.final_current,MainWindow.steps_current,False],[-MainWindow.final_current,-MainWindow.initial_current,MainWindow.steps_current,False],[-MainWindow.initial_current,MainWindow.final_current,MainWindow.steps_current+1,True]))
            
        else:
            MainWindow.MOKE_list = {'run':False}
        MainWindow.run_list.append(MainWindow.MOKE_list)

        if self.ui.wave_check.isChecked(): 
            MainWindow.nkt = self.nkt
            print("done")
            if not self.is_connected_nkt:
                self.show_warning("NKT not connected")
                return None
            MainWindow.initial_wavelength = int(self.ui.set_initial_wavelength_text.text())
            MainWindow.final_wavelength = int(self.ui.set_final_wavelength_text.text())
            MainWindow.steps_wavelength = int(self.ui.step_wavelength_text.text())
            MainWindow.wave_list = {'run':True,'name':'wave','data':[[MainWindow.initial_wavelength,MainWindow.final_wavelength,MainWindow.steps_wavelength+1,True]],'object':MainWindow.nkt}
        else:
            MainWindow.wave_list = {'run':False}
        MainWindow.run_list.append(MainWindow.wave_list)

        if self.ui.shel_check.isChecked():
            MainWindow.initial_position = float(self.ui.initial_text.text())
            # self.centre_position = float(self.ui.centre_text.text())
            MainWindow.final_position = float(self.ui.final_text.text())
            MainWindow.steps = int(self.ui.steps_text.text())
            MainWindow.SHEL_list = {'run':True,'name':'SHEL','data':[[MainWindow.initial_position,MainWindow.final_position,MainWindow.steps+1,True]],'object':MainWindow.rs}
        else :
            MainWindow.SHEL_list = {'run':False}
        MainWindow.run_list.append(MainWindow.SHEL_list)

        # Step 2: Create a QThread object
        self.thread = QThread()
        # Step 3: Create a worker object
        self.worker = Worker(MainWindow)
        # Step 4: Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Step 5: Connect signals and slots
        self.thread.started.connect(self.worker.calculate)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        # self.worker.progress.connect(self.reportProgress)
        # Step 6: Start the thread
        self.thread.start()

        # Final resets

        self.thread.finished.connect(MainWindow.thread_finished
        )
        self.thread.finished.connect(
            lambda: MainWindow.progress_cancel_button.hide()
        )

    def thread_finished():
        MainWindow.progress_bar_1.hide()
        MainWindow.progress_bar_2.hide()
        MainWindow.progress_bar_3.hide()

        MainWindow.progress_label_1.hide()
        MainWindow.progress_label_2.hide()
        MainWindow.progress_label_3.hide()





if __name__ == '__main__':
    app = QApplication(sys.argv)
    faulthandler.enable()
    # create and show mainWindow
    mainWindow = MainWindow()
    mainWindow.show()

    sys.exit(app.exec_())