#from asyncio.windows_events import _BaseWaitHandleFuture

from PyQt5.QtGui import QBrush
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QIcon
from PyQt5.QtGui import QPixmap
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import time
import traceback, sys
from random import random
import time
from datetime import datetime
import os, glob
import collections
import csv
import shlex, subprocess
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

class Editor(QPlainTextEdit):
    def __init__(self, parent=None):
        super(Editor, self).__init__(parent)
        self.zoomValue = 0

    def zoom(self, delta):
        zoomIncrement = 3

        if delta < 0:
            zoomIncrement = 0 - zoomIncrement

        self.zoomIn(zoomIncrement)
        self.zoomValue = self.zoomValue + zoomIncrement

    def wheelEvent(self, event):
        if (event.modifiers() & Qt.ControlModifier):
            self.zoom(event.angleDelta().y())


class FileDetails(object):

    def __init__(self, file):
        path,name=os.path.split(file)
        name,extension=name.split(".")
        self.file=file
        self.path=path
        self.name=name
        self.extension=extension

    def __repr__(self):
        return self.file

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` data returned from processing, anything

    progress
        `int` indicating % progress
    '''

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    cancelled = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(tuple)


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.canrun=True

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress
    def stepover(self):
        self.canrun=False

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        if self.canrun:
            try:
                result = self.fn(*self.args, **self.kwargs)
            except:
                traceback.print_exc()
                exctype, value = sys.exc_info()[:2]
                self.signals.error.emit((exctype, value, traceback.format_exc()))
            else:
                self.signals.result.emit(result)  # Return the result of the processing
            finally:
                self.signals.finished.emit()  # Done
        else:
            self.signals.cancelled.emit((self.args, self.kwargs)) #cancelled

class TaskQTreeWidget(QTreeWidget):
    model=QStandardItemModel() 
    
    def __init__(self):
        super(TaskQTreeWidget, self).__init__()
        self.addlabels()
        
    def addlabels(self,labels=[]):
        #set column order and labels
        self.FIELDS=collections.OrderedDict()
        self.FIELDS['ID']=len(self.FIELDS.keys())
        self.FIELDS['Status']=len(self.FIELDS.keys())
        self.FIELDS['Start']=len(self.FIELDS.keys())
        self.FIELDS['End']=len(self.FIELDS.keys())
        self.FIELDS['Duration']=len(self.FIELDS.keys())
        self.LABELS=self.FIELDS.keys()
        for label in labels:
            self.FIELDS[label]=len(self.FIELDS.keys())
        self.LABELS=self.FIELDS.keys()
        self.setColumnCount(len(self.LABELS))
        self.header=QHeaderView(Qt.Horizontal, parent = None)
        self.model.clear()
        self.model.setHorizontalHeaderLabels(self.LABELS)
        self.header.setModel(self.model)
        self.setSortingEnabled(True)
        self.setHeader(self.header) # add labels   
        self.setHeaderHidden (False)
        self.sortItems(0,Qt.AscendingOrder) #sort by ID column        
    def sort(self):
        self.sortItems(0,Qt.AscendingOrder) #sort by ID column      
        
class TaskSignal(QObject):
    state = pyqtSignal(int)

class Task(QTreeWidgetItem):
    #Set task states
    NEWTASK,READY,CANCELLED,RUNNING,COMPLETED,FAILED=range(6)
    
    #Set up styles to match states
    STYLES=[]
    STYLES.append(QBrush(QColor(125,125,125)))
    STYLES.append(QBrush(QColor(255,200,65)))
    STYLES.append(QBrush(QColor(255,205,255)))
    STYLES.append(QBrush(QColor(0,255,255)))
    STYLES.append(QBrush(QColor(0,255,0)))
    STYLES.append(QBrush(QColor(255,0,0)))
    
    VALUES=[]
    VALUES.append('New task')
    VALUES.append('Ready')
    VALUES.append('Cancelled')
    VALUES.append('Running')
    VALUES.append('Completed')
    VALUES.append('Failed')
    
    def __init__(self, parent, id, data):
        '''
        parent (QTreeWidget) : Item's QTreeWidget parent.
        data is in the form of a dict: 
        '''
        super(Task, self).__init__(parent)
        
        self.parent=parent
        self.signal = TaskSignal()
        self.signal.state.connect(self.setstate)

        self.signal.state.emit(self.NEWTASK)

        self.id=id
        self.setText(self.parent.FIELDS['ID'], '{0}'.format(self.id))
        self.data=collections.OrderedDict()
        self.data['ID']='{0}'.format(id)
        for key,value in data.items():
            self.data[key]='{0}'.format(value)
            self.setText(self.parent.FIELDS[key],self.data[key])

    def setstate(self,state):
        self.state=state
        for field in self.parent.LABELS:
            self.setBackground(self.parent.FIELDS[field],self.STYLES[self.state])
        self.setText(self.parent.FIELDS['Status'], self.VALUES[self.state])
        
        if self.state==self.READY:
            self.starttime=time.time()
            self.setText(self.parent.FIELDS['Start'],'')
            self.setText(self.parent.FIELDS['End'],'')
            self.setText(self.parent.FIELDS['Duration'],'')        
        
        if self.state==self.RUNNING:
            self.starttime=time.time()
            self.setText(self.parent.FIELDS['Start'],'{0}'.format(time.ctime(self.starttime)))
            self.setText(self.parent.FIELDS['End'],'')
            self.setText(self.parent.FIELDS['Duration'],'')
            
        if self.state==self.COMPLETED or self.state==self.FAILED:
            self.endtime=time.time()
            self.setText(self.parent.FIELDS['End'],'{0}'.format(time.ctime(self.endtime)))
            self.setText(self.parent.FIELDS['Duration'],'{0} seconds'.format(round(self.endtime-self.starttime,1)))
            
        return
        


class MainWindow(QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.errors=0
        self.remaining=0
        self.completed=0
        self.threadpool = QThreadPool()
        #self.worker = Worker(self.recurring_timer)
        self.counter = 0
        self.tasks=[]
        self.activetasks=[]

        layout = QVBoxLayout()

        self.l = QLabel('')
        self.recurring_timer()
        layout.addWidget(self.l)
        
        self.coreslabel = QLabel('')
        self.coreslabel.setText('Processing cores:')
        layout.addWidget(self.coreslabel)
        

        self.cores=QSpinBox()
        self.cores.setMinimum(1)
        self.cores.setMaximum(1000)
        self.cores.valueChanged.connect(self.coresvaluechange)
        self.cores.setValue(self.threadpool.maxThreadCount())
        layout.addWidget(self.cores)

        self.btnaddtasks = QPushButton("Add tasks")
        self.btnaddtasks.pressed.connect(self.add_tasks)
        layout.addWidget(self.btnaddtasks)

        self.btncleartasks = QPushButton("Clear tasks")
        self.btncleartasks.pressed.connect(self.clear_tasks)
        layout.addWidget(self.btncleartasks)
        
        self.tasktree = TaskQTreeWidget()
        layout.addWidget(self.tasktree)


        self.globalslabel = QLabel('')
        self.globalslabel.setText('Globals:')
        layout.addWidget(self.globalslabel)

        self.globals=Editor()
        self.globals.setLineWrapMode(Editor.NoWrap)
        self.globals.setMaximumHeight(80)
        note='This tool now supports global variables.'
        note=note+'\n\nexample:'
        note=note+ '\nmypath=W:/processing/'
        note=note+ '\nThis will result in a variable #mypath# being set to W:/processing/'
        self.globals.setPlaceholderText(note)
        layout.addWidget(self.globals)



        self.commandlabel = QLabel('')
        self.commandlabel.setText('Command pattern:')
        layout.addWidget(self.commandlabel)

        self.commandpattern=Editor()
        self.commandpattern.setLineWrapMode(Editor.NoWrap)
        self.commandpattern.setMaximumHeight(180)
        note='This tool now supports multi-line commands.'
        note=note+'\nAll command lines will run for each task before moving to the next tasks in the queue.'
        note=note+'\nThe output from one command can be the input to the next.'
        note=note+'\n(Use ctrl+<mouse scroll> to zoom command text window)'
        note=note+'\n\nexample:'
        note=note+ '\nlasgrid -i W:/processing/Onkaparinga_1804/2018_2019_merged/#name#.laz -step 1 -ll #xmin# #ymin# -nrows 500 -ncols 500 -o W:/processing/Onkaparinga_1804/2018_2019_merged/dem/#name#.asc -nbits 32 -elevation_lowest -keep_class 2'
        note=note+ '\nlasgrid -i W:/processing/Onkaparinga_1804/2018_2019_merged/#name#.laz -step 1 -ll #xmin# #ymin# -nrows 500 -ncols 500 -o W:/processing/Onkaparinga_1804/2018_2019_merged/dsm/#name#.asc -nbits 32 -elevation_highest -keep_class 0 1 2 3 4 5 6 8 9 10' 
        note=note+ '\nlasgrid -i W:/processing/Onkaparinga_1804/2018_2019_merged/#name#.laz -step 1 -ll #xmin# #ymin# -nrows 500 -ncols 500 -o W:/processing/Onkaparinga_1804/2018_2019_merged/chm/#name#.asc -nbits 32 -elevation_highest -keep_class 3 4 5'        
        self.commandpattern.setPlaceholderText(note)

        layout.addWidget(self.commandpattern)

        self.btnrun = QPushButton("Run")
        self.btnrun.pressed.connect(self.run)
        layout.addWidget(self.btnrun)   


        w = QWidget()
        
        w.setLayout(layout)
        self.setCentralWidget(w)

        self.showMaximized()

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()

    def coresvaluechange(self):
        if self.cores.value()>0:
            cores=int(self.cores.value())
        else:
            cores=1
        self.threadpool.setMaxThreadCount(cores)
      
    def progress_fn(self, data):
        try:
            index,value=data
            task=self.tasks[index]
            task.setstate(task.RUNNING)
        except IndexError:
            #items removed to clear tasks
            pass            
        except Exception as e:
            print(e)
    def requeue_ignore(self):
        return
    def requeue_fn(self,progress_callback, index):
        task=self.tasks[index]
        task.setstate(task.READY)
        return  

    def cancelled(self,data):
         args, kwargs=data
         index=kwargs['index']
         task=self.tasks[index]
         task.setstate(task.CANCELLED)


    def execute_command(self,progress_callback, index ):
        data=5
        log=''
        try:
            progress_callback.emit((index,'Initialising...'))
            task=self.tasks[index]
            
            commandlist=self.commandpattern.toPlainText()
            commandlist=commandlist.replace('\\','/')
            commandlist=commandlist.split('\n')

            globalvars=self.globals.toPlainText()
            globalvars=globalvars.replace('\\','/')
            globalvars=globalvars.split('\n')

            for command in commandlist:    
                command=command.strip()
                if command=='':
                    pass
                else:

                    for globalvar in globalvars:
                        globalvar=globalvar.strip()
                        if globalvar=='' or (not '=' in globalvar):
                            pass
                        else:
                            globalvar=globalvar.split('=')
                            command=command.replace('#{0}#'.format(globalvar[0]),'{0}'.format(globalvar[1].replace('\\','/')))

                    for key,value in task.data.items():
                        command=command.replace('#{0}#'.format(key),'{0}'.format(value.replace('\\','/')))

                    log=log+'\nStarted: {0}\n'.format(time.ctime(time.time())) 
                    log=log+'Command: {0}\n'.format(command)
                    command.replace('=','|EQUALS|')
                    command=shlex.split(command)
                    
                    for i,var in enumerate(command):
                        command[i].replace('|EQUALS|','=')
                
                    p = subprocess.run(command,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
                    
                    log=log +'\n'+p.stdout
                    log=log +'Success: {0}\n'.format(time.ctime(time.time()))

            data=task.COMPLETED

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout.decode('utf-8'))
            log=log +'Failed: {0}\n'.format(time.ctime(time.time()))
            self.errors_fn((index,'Error...'))
        except Exception as e:
            data=task.FAILED
            print(command)
            print(e)
            self.errors_fn((index,'Error...'))
        finally:
            if not log =='': print(log)
            return (index,data)


    def print_output(self, data):
        try:
            index,state=data
            task=self.tasks[index]
            task.setstate(state)
        except IndexError:
            #items removed to clear tasks
            pass
        except Exception as e:
            print(e)

    def thread_complete(self):
        self.remaining-=1
        self.completed+=1
        pass


    def add_tasks(self):
        
        self.clear_tasks()
        

        filter = "csv (*.csv);;json (*.json);;geojson (*.geojson);;*.* (*.*)"
        file_name = QFileDialog()
        file_name.setFileMode(QFileDialog.ExistingFile)
        fileopen = file_name.getOpenFileName(self, "Open file", "C:\\temp\\", filter)
        
        #print(fileopen)
        if not fileopen[0]=='':
            if fileopen[1]=='csv (*.csv)':
                self.opencsv(fileopen)
            if fileopen[1]=='json (*.json)' or fileopen[1]=='geojson (*.geojson)':
                self.openjson(fileopen)
            window.setWindowTitle("One Tool:  {0}".format(fileopen[0]))

    def openjson(self,fileopen):   
        self.errors=0
        self.remaining=0
        self.completed=0
        filepath=fileopen[0].replace('/','\\') 
        tilelayout=AtlassTileLayout()
        tilelayout.fromjson(filepath)
        count=0
        for tile in tilelayout.tiles:
            if count==0:
                fieldnames=tilelayout.tiles[tile].params.keys()
                self.tasktree.addlabels(fieldnames)
            count+=1
            task=Task(self.tasktree,'{0}'.format(len(self.tasks)).rjust(6, '0'),tilelayout.tiles[tile].params)
            task.setstate(task.READY)
            self.tasks.append(task)
            self.remaining+=1

    def opencsv(self,fileopen):
        self.errors=0
        self.remaining=0
        self.completed=0
        filepath=fileopen[0].replace('/','\\')
        with open(filepath, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            self.tasktree.addlabels(reader.fieldnames)
            for row in reader:
                task=Task(self.tasktree,'{0}'.format(len(self.tasks)).rjust(6, '0'),row)
                task.setstate(task.READY)
                self.tasks.append(task)
                self.remaining+=1

    def clear_tasks(self):
        #self.tasks=[]
        #self.tasktree.addlabels()
        #self.tasktree.clear()
        
        if self.threadpool.activeThreadCount() > 0 or self.threadpool.globalInstance().activeThreadCount()>0:
            for i,worker in enumerate(self.workers ):
                self.workers[i].stepover()

        self.errors=0
        self.remaining=0
        self.completed=0



    def errors_fn(self, data):
        self.errors+=1

    def run(self):         
        self.commandpattern.setEnabled(False)
        self.globals.setEnabled(False)
        self.btnrun.setEnabled(False)

        self.errors=0
        self.remaining=len(self.tasks)
        self.completed=0
        threadpool = QThreadPool()
        for i,task in enumerate(self.tasks):
            worker = Worker(self.requeue_fn,index=i)
            worker.signals.result.connect(self.requeue_ignore)
            worker.signals.finished.connect(self.requeue_ignore)
            #worker.signals.progress.connect(self.requeue_ignore)
            #worker.signals.error.connect(self.requeue_ignore)            
            threadpool.start(worker)

        while not threadpool.activeThreadCount() == 0:
            time.sleep(2) 
            
        self.tasktree.sort()

        print('--------------------------------------------------------------------------------------------------------')
        print('{0} - Threading {1} tasks.'.format(time.ctime(time.time()),len(self.tasks)))  
        print('--------------------------------------------------------------------------------------------------------')
        self.errors=0
        self.remaining=len(self.tasks)
        self.completed=0
        self.workers=[]

        for i,task in enumerate(self.tasks):
            # Pass the function to execute
            worker = Worker(self.execute_command,index=i)  # Any other args, kwargs are passed to the run function
            worker.signals.result.connect(self.print_output)
            worker.signals.finished.connect(self.thread_complete)
            worker.signals.progress.connect(self.progress_fn)
            worker.signals.error.connect(self.errors_fn)
            worker.signals.cancelled.connect(self.cancelled)
            self.workers.append(worker)
            self.threadpool.start(self.workers[-1])
        

    def recurring_timer(self):
        try:
            if self.threadpool.activeThreadCount() ==0 and self.btnrun.isEnabled()==False  :
                print('--------------------------------------------------------------------------------------------------------')
                print('{0} - Process ended.'.format(time.ctime(time.time()),len(self.tasks)))  
                print('--------------------------------------------------------------------------------------------------------\n')
                self.commandpattern.setEnabled(True)  
                self.globals.setEnabled(True)  
                self.btnrun.setEnabled(True)
            else:
                self.l.setText('{0}: Remaining: {1} Completed:{2} Errors: {3}'.format(time.ctime(time.time()),self.remaining, self.completed,self.errors))
        except:
            #self.l.setText('{0}'.format(time.ctime(time.time())))
            self.l.setText('{0}: Remaining: {1} Completed:{2} Errors: {3}'.format(time.ctime(time.time()),self.remaining, self.completed,self.errors))
            pass
        #print(self.threadpool.globalInstance().activeThreadCount() )


app = QApplication([])

# set app icon    
app_icon = QIcon()
app_icon.addFile(os.path.join(sys.path[0],'icons/16x16.png'), QSize(16,16))
app_icon.addFile(os.path.join(sys.path[0],'icons/24x24.png'), QSize(24,24))
app_icon.addFile(os.path.join(sys.path[0],'icons/32x32.png'), QSize(32,32))
app_icon.addFile(os.path.join(sys.path[0],'icons/48x48.png'), QSize(48,48))
app_icon.addFile(os.path.join(sys.path[0],'icons/256x256.png'), QSize(256,256))
app.setWindowIcon(app_icon)

window = MainWindow()
window.setWindowTitle("One Tool")
window.setWindowIcon(app_icon)

app.exec_()
