import Atlass
import os
import io
import sys
import glob
from subprocess import Popen, PIPE
from multiprocessing import Process, Queue
import time
import datetime
from contextlib import redirect_stderr, redirect_stdout
import geojson
from collections import defaultdict , OrderedDict
import json
import objectpath
import logging
from time import strftime

import linecache
import scipy
from scipy import misc
from scipy.interpolate import griddata
from scipy.ndimage import morphology
from scipy.ndimage import filters


class GMScript():
    pass


class AsciiGridHeader(object):
    def __init__(self):
        self._ncols=None
        self._nrows=None
        self._xllcorner=None
        self._yllcorner=None
        self._cellsize=None
        self._nodata_value=None
    def __repr__(self):
        return 'ncols {0}\nnrows {1}\nxllcorner {2}\nyllcorner {3}\ncellsize {4}\nnodata_value {5}\n'.format(
        self.ncols,self.nrows,self.xllcorner,self.yllcorner,self.cellsize,self.nodata_value)
    @property
    def ncols(self):
        return self._ncols
    @ncols.setter
    def ncols(self,value):
        self._ncols=int(value) 
    @property
    def nrows(self):
        return self._nrows
    @nrows.setter
    def nrows(self,value):
        self._nrows=int(value) 
    @property
    def xllcorner(self):
        return self._xllcorner
    @xllcorner.setter
    def xllcorner(self,value):
        self._xllcorner=float(value)         
    @property
    def yllcorner(self):
        return self._yllcorner
    @yllcorner.setter
    def yllcorner(self,value):
        self._yllcorner=float(value)         
    @property
    def cellsize(self):
        return self._cellsize
    @cellsize.setter
    def cellsize(self,value):
        self._cellsize=float(value)      
    @property
    def nodata_value(self):
        return self._nodata_value
    @nodata_value.setter
    def nodata_value(self,value):
        self._nodata_value=float(value)      
    def set(self,values):
        self._ncols=values.ncols
        self._nrows=values.nrows
        self._xllcorner=values.xllcorner
        self._yllcorner=values.yllcorner
        self._cellsize=values.cellsize
        self._nodata_value=values.nodata_value
        
class AsciiGridGrid(object):
    def __init__(self):
        self._data=None
    def __repr__(self):
        return self._data
    @property
    def data(self):
        return self._data
    @data.setter
    def data(self,data):
        self._data=data
    @property
    def points(self):
        points=[]
        for j in range(0,self._data.shape[0]):
            for i in range(0,self._data.shape[1]):
                points.append((i,j,self._data[j,i]))
        return points   
    
class AsciiGrid(object):
    def __init__(self):
        self._header=AsciiGridHeader()
        self._grid=AsciiGridGrid()
    def __repr__(self):
        return self.header,self.grid
    @property
    def header(self):
        return self._header
    @header.setter
    def header(self,headervalues):
        self._header.set(headervalues)
    @property
    def grid(self):
        return self._grid.data
    @grid.setter
    def grid(self,gridvalues):
        self._grid.data=gridvalues 
    @property
    def ncols(self):
        return self.header.ncols
    @ncols.setter
    def ncols(self,value):
        self.header.ncols=int(value) 
    @property
    def nrows(self):
        return self.header.nrows
    @nrows.setter
    def nrows(self,value):
        self.header.nrows=int(value) 
    @property
    def xllcorner(self):
        return self.header._xllcorner
    @xllcorner.setter
    def xllcorner(self,value):
        self.header.xllcorner=float(value)         
    @property
    def yllcorner(self):
        return self.header.yllcorner
    @yllcorner.setter
    def yllcorner(self,value):
        self.header.yllcorner=float(value)         
    @property
    def cellsize(self):
        return self.header.cellsize
    @cellsize.setter
    def cellsize(self,value):
        self.header.cellsize=float(value)      
    @property
    def nodata_value(self):
        return self.header.nodata_value
    @nodata_value.setter
    def nodata_value(self,value):
        self.header.nodata_value=float(value)           
    @property
    def points(self):
        return[(self.pointfromcell((x,y))) for x in range(self.grid.shape[1]) for y in range(self.grid.shape[0]) if self.grid[y,x] != self.nodata_value] 
    def pointfromcell(self,cell):
        return self.xllcorner+cell[0]*self.cellsize,self.yllcorner+self.cellsize*(self.nrows-cell[1]),self.grid[cell[1],cell[0]]
    def readfromfile(self,file):
        #returns grid as numpy float array and library of header values
        header={}
        self.ncols=int(linecache.getline(file, 1).split()[1])
        self.nrows=int(linecache.getline(file, 2).split()[1])
        self.xllcorner=float(linecache.getline(file, 3).split()[1])
        self.yllcorner=float(linecache.getline(file, 4).split()[1])
        self.cellsize=float(linecache.getline(file, 5).split()[1])
        self.nodata_value=float(linecache.getline(file, 6).split()[1])
        self.grid=np.array(np.loadtxt(file, skiprows=6),dtype=float)
    def savetofile(self,file):
        np.set_printoptions(formatter={'float': '{: 0.3f}'.format})
        with open(file, "w") as f:
            f.write('ncols {0}\nnrows {1}\nxllcorner {2}\nyllcorner {3}\ncellsize {4}\nnodata_value {5}\n'.format(self.ncols,self.nrows,self.xllcorner
            ,self.yllcorner,self.cellsize,self.nodata_value))
            for y in self.grid:
                f.write('{0}\n'.format(" ".join(str(x) for x in y)))
            f.close()
    def erode(self,iterations=1):
        ones=np.array(np.ones((self.grid.shape[0],self.grid.shape[1])), ndmin=2, dtype=int)
        nodatagrid=ones*self.nodata_value
        unoccupied=ones*(self.grid==self.nodata_value)
        unoccupied=morphology.binary_dilation(unoccupied,iterations=iterations).astype(unoccupied.dtype)
        self.grid=np.where(unoccupied==0,self.grid,nodatagrid)
        return
    def applymask(self,mask):
        nodatagrid=np.array(np.ones((self.grid.shape[0],self.grid.shape[1])), ndmin=2, dtype=int)*self.nodata_value
        self.grid=np.where(mask==1,self.grid,nodatagrid)
        pass
  

class AtlassTile():
    def __init__(self,parent,**kwargs):
        self.parent=parent
        self._params=OrderedDict()
        self._params['name']=''
        self._params['xmin']=None
        self._params['ymin']=None
        self._params['xmax']=None
        self._params['ymax']=None        
        self.addparams(**kwargs)

    def getneighbours(self,buffer):
        neighbours=[]
        if isinstance(buffer, float) or isinstance(buffer, int):
            xmin=self.xmin-buffer
            xmax=self.xmax+buffer
            ymin=self.ymin-buffer
            ymax=self.ymax+buffer
            
            for key,tile in self.parent.tiles.items():
                if tile.xmin<xmin<tile.xmax or tile.xmin<xmax<tile.xmax or xmin<tile.xmin<xmax or xmin<tile.xmax<xmax:
                    if tile.ymin<ymin<tile.ymax or tile.ymin<ymax<tile.ymax or ymin<tile.ymin<ymax or ymin<tile.ymax<ymax:
                        neighbours.append(tile.name)
        else:
            raise TypeError('only accepts floats or integers for buffer')  


        return neighbours
    @property
    def name(self):
        return self._params['name']

    @name.setter    
    def name(self, value): 
        if isinstance(value, str):
            self._params['name']=str(value)
        else:
            raise TypeError('only accepts strings') 


    @property
    def xmin(self):
        return self._params['xmin']

    @xmin.setter    
    def xmin(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['xmin']=float(value)
        else:
            raise TypeError('only accepts floats or integers') 


    @property
    def ymin(self):
        return self._params['ymin']

    @ymin.setter    
    def ymin(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['ymin']=float(value)
        else:
            raise TypeError('only accepts floats or integers')    


    @property
    def xmax(self):
        return self._params['xmax']

    @xmax.setter    
    def xmax(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['xmax']=float(value)
        else:
            raise TypeError('only accepts floats or integers') 


    @property
    def ymax(self):
        return self._params['ymax']

    @ymax.setter    
    def ymax(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['ymax']=float(value)
        else:
            raise TypeError('only accepts floats or integers') 

    @property
    def params(self):
        return self._params

    @params.setter  
    def params(self,data):
        #data can be of type dictionary
        print("in param setter")
        if isinstance(data,dict) or isinstance(data,OrderedDict): 
            for stdkey in ['name','xmin','ymin','xmax','ymax']:
                if not stdkey in data.keys():
                    print('Warning: {0} not in keys'.format(stdkey))
                    print('Current value of {0}'.format(stdkey,self._params[stdkey])) 

            for key,value in data.items():
                if key =='name':
                    self.name=value
                if key =='xmin':
                    self.xmin=value
                if key =='ymin':
                    self.ymin=value
                if key =='xmax':
                    self.xmax=value
                if key =='ymax':
                    self.ymax=value                
                else:
                    if isinstance(value,str) or isinstance(value,float) or isinstance(value,int):
                        self._params[key]=value
                    else:
                        raise TypeError('only accepts strings, float and integers "{0}" is type: {1}'.format(key,type(value))) 

                
        else:
            raise TypeError('only accepts dictionary type, data is of type: {0}'.format(type(value))) 

  
    def addparams(self,**kwargs):
        for key,value in kwargs.items():
            if key =='name':
                self.name=value
            if key =='xmin':
                self.xmin=value
            if key =='ymin':
                self.ymin=value
            if key =='xmax':
                self.xmax=value
            if key =='ymax':
                self.ymax=value                
            else:
                if isinstance(value,str) or isinstance(value,float) or isinstance(value,int):
                    self._params[key]=value
                else:
                    raise TypeError('only accepts strings, float and integers "{0}" is type: {1}'.format(key,type(value)))

    def __repr__(self):
        return str(self._params)

    def __str__(self):
        txt='{"type": "Feature",'
        txt=txt+ '"properties": {'
        for key,value in self.params.items():
            if isinstance(value,int) or isinstance(value,float):
                txt=txt+'"{0}":{1},'.format(key,value)
            else:
                txt=txt+'"{0}":"{1}",'.format(key,value)

        txt=txt[:-1]+'},'+'"geometry":{"type": "Polygon","coordinates":'+'[[[{0},{1}],[{2},{1}],[{2},{3}],[{0},{3}],[{0},{1}]]]'.format(self.xmin,self.ymin,self.xmax,self.ymax)+'}}'

        return txt


class AtlassTileLayout():
    fileNo = 0
    def __init__(self):
        self.tiles=OrderedDict()
        pass

    def __iter__(self):
        for key,item in self.tiles.items():
            yield item

    def addtile(self,**kwargs):
        
        for stdkey in ['name','xmin','ymin','xmax','ymax']:
            if not stdkey in kwargs.keys():
                print('Warning: {0} not in keys. Tile not added'.format(stdkey))
                return
        self.tiles[kwargs['name']]=AtlassTile(self,**kwargs)

    def gettile(self,tilename):
        print(tilename)
        if isinstance(tilename,str):
            if tilename in self.tiles.keys():
                #return tile object
                return self.tiles[tilename]
        else:
            raise TypeError('only accepts strings as tilename')  
      

    def fromdict(self,data):    
       for key, value in data.items():
            if not key in self.tiles:
                self.tiles[key]=AtlassTile(self, **value)
            else:
                pass


    def fromjson(self, jsonfile):
        with open(jsonfile) as fr:
            data = json.load(fr)
            tiles = {}
            for value in data['features']:
                 #print(value)
                 tile = {}
                 for key, val in value['properties'].items():
                     if(key == 'tilename'):
                         key = 'name'
                     tile[key] = val

                 name = tile['name']           
                 tiles[name] = tile

            self.fromdict(tiles)
        return 


    def createGeojsonFile(self, outputfile):
        '''
        while True:
            try:
                os.path.exists(outputfile)

            except:
                outputfile, ex = outputfile.split('.')
                outputfile = outputfile+ str(AtlassTileLayout.fileNo)+'.json'
                AtlassTileLayout.fileNo += 1
                continue

            else:
                outputfile, ex = outputfile.split('.')
                outputfile = outputfile+ str(AtlassTileLayout.fileNo+1)+'.json'
                AtlassTileLayout.fileNo += 1
                break
        '''

        with open(outputfile, 'w') as f:
             f.write('')
        
        with open(outputfile, 'a') as f:
            tilestr = '{ "type": "FeatureCollection", "features": ['
            for key, value in self.tiles.items():
                 tilestr = tilestr + str(value)+','
            tilestr = tilestr[:-1]+']}'
            f.write(tilestr)

        return outputfile
                
    def __repr__(self):
        return 'tilelayout()'

    def __str__(self):
        return 'tilelayout with tiles:({0})'.format(self.len())    

    def __len__(self):
        return len(self.tiles.keys())


class Atlasslogger(list):
    loginfo = []
    def __init__(self, outpath):
        self.logpath = os.path.join(outpath,'log.json').replace('\\','/')
        self.jlog = open(outpath+"\\log.json","w")
                
        if os.path.exists(outpath+"\\log.txt"):
            os.remove(outpath+"\\log.txt")
            self.log = open(outpath+"\\log.txt", 'w')
            self.log.write("-------------------------------------\nStart Time : {} \n-----------------------------------------------".format(str(datetime.datetime.now())))
        else:
            self.log = open(outpath+"\\log.txt", 'w')

    def write(self, msg = None):
        self.log.write("\n\n{}".format(msg)) 

    def flush(self):
        self.log.close()
        self.jlog.close()

    def PrintMsg(self, Message,Heading=None):
        if Heading==None:
            msgstring='\t{0}'.format(Message)
            self.log.write(msgstring) 
            print(msgstring)
        else:
            msgstring='\n'
            msgstring=msgstring+'----------------------------------------------------------------------------\n'
            msgstring=msgstring+'{0}: {1}\n'.format(time.ctime(time.time()),Heading)
            msgstring=msgstring+'----------------------------------------------------------------------------\n'
            msgstring=msgstring+'\t{0}'.format(Message)
            self.log.write(msgstring) 
            print(msgstring)
        
        return msgstring + '\n'

    def CreateLog(self, proccess=None, args = None,time=None, sucess=None, fail=None, results=None):
        if not results==None or Process==None:
            args = args.replace("\\\\", "/")
            print(Atlasslogger.loginfo)
            Atlasslogger.loginfo.append({'scope':proccess, 'time':time,'success':sucess, 'fail':fail, 'results':results})

    def DumpLog(self):
        dumps = {}
        dumps['Tasks']=(Atlasslogger.loginfo)
        json.dump(dumps, self.jlog, indent=4)


class AtlassWorkerProcess():
    def __init__(self, input, output):
        self.inputQ = input
        self.outputQ = output
        self.run()
   
    def run(self): 
        try:
            for func, args in iter(self.inputQ.get,'STOP'):
                result = func(*args)
                self.outputQ.put(result)
        except:
            print( "Worker Process: Unable to process \n",)

        return self.outputQ

class AtlassTaskRunner():

    failedscript = False

    def __init__(self,cores, tasks, name, logger, args):
        self.cores = cores
        self.tasks = tasks
        self.name = name
        self.results = []
        self.logger = logger
        self.args = args
        self.resultpertask = []
        self.success = 0
        self.fail = 0

        self.run()

    def resultsCalc(self, result):
        pass

    def run(self):
        self.time = strftime("%Y-%m-%dT%H:%M:%S")
        if self.tasks==None:
            return -1
        self.logger.PrintMsg("Running AtlassTaskRunner\n", "Task Runner")
        number_of_processes=min(self.cores, len(self.tasks))  
        
        # Create queues
        task_queue = Queue()
        done_queue = Queue()

        # Submit tasks
        for task in self.tasks:
            task_queue.put(task)

        # Start worker processes
        self.logger.PrintMsg('Setting up {0} tasks in {1} parallel processes\n'.format(len(self.tasks),number_of_processes))
        
        for i in range(number_of_processes):
            try:
                Process(target=AtlassWorkerProcess, args=(task_queue, done_queue)).start()
            except:
                self.logger.PrintMsg('Exception on start\n')
                pass
            
            
        # Get and print results

        self.logger.PrintMsg("Unordered results:{0}\n".format(self.name))
        for i in range(len(self.tasks)):
            try:
                result =done_queue.get()
                if not result==None:
                    #self.logger.write('{}'.format(result))
                    self.results.append(result)
            except:
                self.logger.PrintMsg('Exception on get results')
                pass
       
        #result_list = [x.recv() for x in  done_queue]
        #Tell child processes to stop  
        self.logger.PrintMsg('Closing {0} parallel processes\n'.format(number_of_processes))
        for i in range(number_of_processes):
            try:
                task_queue.put('STOP')
            except:
                print('Exception on stop')
        self.logger.PrintMsg("Printing Results at the end TaskRunner.\n\n")

        for result in self.results:
            if result['state'] == "Success":
                self.success += 1
            else:
                self.fail += 1
                AtlassTaskRunner.failedscript = True

            self.resultpertask.append({'Tile':result['file'],'state':result['state'],'output':result['output'] })


        self.logger.CreateLog(self.name, self.args, self.time, self.success, self.fail, self.resultpertask)
        self.logger.flush
        return self.results

class AtlassGen():

    def makedir(path):
        if not os.path.exists('{0}'.format(path)):
            try:
                os.makedirs('{0}'.format(path))
            except:
                pass
        return path

    def FILELIST (Pattern):
        filedetails = []
        for infile in glob.glob( Pattern ):
            filedetails.append(infile.replace("\\","/"))
        return filedetails

    def FILESPEC(filename):
        # splits file into components
        path,name=os.path.split(filename)
        name,ext=name.split(".")
    
        return path, name, ext    


