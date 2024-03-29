import os
import io
import sys
import glob
import statistics
import math
from subprocess import Popen, PIPE
from multiprocessing import Process, Queue, pool
import time
import datetime
from contextlib import redirect_stderr, redirect_stdout
import geojson
from collections import defaultdict , OrderedDict
import json
import objectpath
import logging
from time import strftime
import numpy as np
import linecache
import scipy
from scipy import misc
from scipy.interpolate import griddata
from scipy.ndimage import morphology
from scipy.ndimage import filters
import subprocess

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
        self._params['modtime']=None   
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
    def modtime(self):
        return self._params['modtime']

    @modtime.setter    
    def modtime(self, value): 
        if isinstance(value, str):
            self._params['modtime']=value
        else:
            raise TypeError('only accepts strings') 

    @property
    def params(self):
        return self._params

    @params.setter  
    def params(self,data):
        #data can be of type dictionary
        print("in param setter")
        if isinstance(data,dict) or isinstance(data,OrderedDict): 
            for stdkey in ['name','xmin','ymin','xmax','ymax','modtime']:
                if not stdkey in data.keys():
                    print('Warning: {0} not in keys'.format(stdkey))
                    print('Current value of {0}'.format(self._params[stdkey])) 

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
                if key =='modtime':
                    self.modtime=value        
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
            if key =='modtime':
                self.modtime=value          
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
                     #print('\n\n',key,val)
                     key=key.lower()
                     if(key == 'tilename'):
                         key = 'name'
                     if(key == 'name'):
                         key = 'name'
                     if(key == 'tile_name'):
                         key = 'name'                         
                     if(key == 'xmin'):
                         val = float(val)
                     if(key == 'ymin'):
                         val = float(val)
                     if(key == 'xmax'):
                         val = float(val)
                     if(key == 'ymax'):
                         val = float(val)
                     if(key == 'modtime'):
                         val = str(val)
                     tile[key] = val
                 name = tile['name']           
                 tiles[name] = tile
            self.fromdict(tiles)
        #print(len(self.tiles.keys()))
        return 

    def gettilesfrombounds(self,xmin,ymin,xmax,ymax):
        neighbours=[]
        for key,tile in self.tiles.items():
            if tile.xmin<xmin<tile.xmax or tile.xmin<xmax<tile.xmax or xmin<tile.xmin<xmax or xmin<tile.xmax<xmax:
                if tile.ymin<ymin<tile.ymax or tile.ymin<ymax<tile.ymax or ymin<tile.ymin<ymax or ymin<tile.ymax<ymax:
                    neighbours.append(tile.name)
        return neighbours


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
        self.jlogpath = os.path.join(outpath,'log.json').replace('\\','/')
        self.logpath = os.path.join(outpath,'log.txt').replace('\\','/')
        if os.path.exists(self.jlogpath):
            if os.stat(self.jlogpath).st_size !=0:
                with open(self.jlogpath) as fr:
                    data = json.load(fr)
                    for tasks in data['Tasks']:
                        Atlasslogger.loginfo.append(tasks)
                
    
            print(Atlasslogger.loginfo)
            self.jlog = open(self.jlogpath,"w")
        else:
            self.jlog = open(self.jlogpath,"w")
                
        if os.path.exists(self.logpath):
            os.remove(self.logpath)
            self.log = open(self.logpath, 'w')
            self.log.write("-------------------------------------\nStart Time : {} \n-----------------------------------------------".format(str(datetime.datetime.now())))
        else:
            self.log = open(self.logpath, 'w')

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
class AtlassTask():
    '''
    Stores task related data that is used during multiprocessing
    '''
    def __init__(self,name,func,*args,**kwargs):
        self.name=name
        self.func=func
        self.success=False
        self.log=None
        self.result=None
        self.args=args
        self.kwargs=kwargs

    def __repr__(self):
        return 'Task object:\n\n\nTask({0},{1},{2})\n\nStatus: {3} {4}\n\nLog:{5}'.format(self.name,self.args,self.kwargs,self.success, self.result,self.log)

class AtlassTaskRunner():

    def __init__(self):
        pass


    def taskmanager(task):
        '''
        Runs the function specified in the task
        Functions need to return (sucess, result, log)
        '''
        log='\n------------------------------------------------------------------------------------------------------\n'
        log=log+ '{0}: {1}({2},{3})\n'.format(task.name,task.func.__name__,task.args,task.kwargs)
        log=log+'Process started: {0}\n'.format(time.ctime( time.time()))

        #run the task
        task.success,task.result,task.log=task.func(*task.args,**task.kwargs)

        log=log+ task.log +'\n\n'
        log=log+'Success:{0}\n'.format(task.success)
        log=log+'Process ended: {0}\n'.format(time.ctime( time.time()))
        log=log + '------------------------------------------------------------------------------------------------------\n'

        task.log=log

        return task

class SurfacePoint(object):
    def __init__(self,index,x,y,z, dz, accepted ):
        self.index=index
        self.x=x 
        self.y=y
        self.z=z
        self.dz = dz
        self.accepted = accepted


    def __repr__(self):
        return (str(self.index),str(self.x), str(self.y), str(self.z), str(self.dz))
    
        
class SurfacePatch:
    tcaltime = 0
    def __init__(self):
        self.points=OrderedDict()
        self.initalaverage = None
        self.initalstddev = None
        self.finalaverage = None
        self.finalstddev = None

        pass    

    def addSurfacePoint(self, *args):
        self.points[args[0]]=SurfacePoint(args[0], args[1], args[2], args[3], args[4], args[5])

    def calc_sum(self, attr):
        sm = sum(float(getattr(point, attr)) for key, point in self.points.items())
        return sm

    def calc_average(self, attr):
        data = []
        for key, point in self.points.items():
            if point.accepted:
                data.append(getattr(point, attr))
        av = round(statistics.mean(data), 3)

        if SurfacePatch.tcaltime<1:
            print('\n\n')
            self.initalaverage = av
        else:
            self.finalaverage = av
        return av

    def calc_stdev(self, attr):
        data = []
        for key, point in self.points.items():
            if point.accepted:
                data.append(getattr(point, attr))
        std = round(statistics.stdev(data), 4)
        if SurfacePatch.tcaltime<1:
            self.initalstddev = std
        else:
            self.finalstddev = std
        SurfacePatch.tcaltime += 1
        return std

    def filter_data(self, tsigma , initavg):
        rejected = 0
        accepted = 0
        if initavg:
            filterval_upper = initavg + tsigma
            filterval_lower = initavg - tsigma
            print('Data range : {0} - {1}'.format(filterval_lower,filterval_upper))
            for point in self.points.values():

                if (  filterval_lower < point.z < filterval_upper):
                    point.accepted = True
                    accepted +=1
                else:
                    point.accepted = False
                    rejected +=1
        else:
            print("Inital average not calculated !")
            exit()

        self.calc_average('z')
        print("Final average : {0}".format(self.finalaverage))
        self.calc_stdev('z')
        print("Final Std Deviation : {0}".format(self.finalstddev))



        return (accepted, rejected)

    def __len__(self):
        return len(self.points.keys())

    def __iter__(self):
        for key,item in self.points.items():
            yield item

class Point(object):
    def __init__(self,index,x,y,lidarz,controlz, dz, patchstddev,  accepted=True, dzshifted=None, dzshiftedsq=None ):
        self.index=index
        self.x=x 
        self.y=y
        self.lidarz = lidarz
        self.controlz=controlz
        self.dz = dz
        self.patchstddev = patchstddev
        self.accepted = accepted
        self.dzshifted = dzshifted
        self.dzshiftedsq = dzshiftedsq

    def __repr__(self):
        return (str(self.index),str(self.x), str(self.y), str(self.lidarz), str(self.controlz), str(self.dz))
    
        
class PointList:
    caltime = 0
    def __init__(self):
        self.points=OrderedDict()
        self.initalaverage = None
        self.initalstddev = None
        self.finalaverage = None
        self.finalstddev = None
        self.rmse = None
        self.ci95 = None
        pass    

    def addPoint(self, *args):
        self.points[args[0]]=Point(args[0], args[1], args[2], args[3], args[4], args[5], args[6])

    def calc_sum(self, attr):
        sm = sum(float(getattr(point, attr)) for key, point in self.points.items())
        return sm

    def calc_average(self, attr):
        data = []
        for key, point in self.points.items():
            if point.accepted:
                data.append(getattr(point, attr))

        av = round(statistics.mean(data), 4)
        if PointList.caltime<1:
            self.initalaverage = av
        else:
            self.finalaverage = av
        return av

    def calc_stdev(self, attr):
        data = []
        for key, point in self.points.items():
            if point.accepted:
                data.append(getattr(point, attr))
        std = round(statistics.stdev(data), 4)
        if PointList.caltime<1:
            self.initalstddev = std
        else:
            self.finalstddev = std
        PointList.caltime += 1
        return std
        
    def createOutputFiles(self,outputpath):

        txtfile = os.path.join(outputpath,'GCP_accepted.txt').replace('\\','/')
        txtf =  open(txtfile, 'w') 
           
        rejtxtfile = os.path.join(outputpath,'GCP_rejected.txt').replace('\\','/')
        rejtf = open(rejtxtfile, 'w')

        for key,point in self.points.items():
            if point.accepted:
                txtf.write('{0} {1} {2} {3}\n'.format(point.index, point.x, point.y, point.controlz))
            else:
                rejtf.write('{0} {1} {2} {3}\n'.format(point.index, point.x, point.y, point.controlz))

        txtf.close()
        rejtf.close()

        return 

    def filter_data(self, tsigma):
        rejected = 0
        accepted = 0
        if self.initalaverage:
            filterval_upper = self.initalaverage + tsigma
            filterval_lower = self.initalaverage - tsigma
            print('Data range : {0} - {1}'.format(filterval_lower,filterval_upper))
            for point in self.points.values():

                if (  filterval_lower < point.dz < filterval_upper):
                    point.accepted = True
                    accepted +=1
                else:
                    point.accepted = False
                    rejected +=1
        else:
            print("Inital average not calculated !")
            exit()

        self.calc_average('dz')
        print("Final average : {0}".format(self.finalaverage))
        self.calc_stdev('dz')
        print("Final Std Deviation : {0}".format(self.finalstddev))

        if self.finalaverage:
            dzsqsum = []
            for point in self.points.values():
                if point.accepted:
                    shiftval = (point.dz - self.finalaverage)
                    point.dzshifted = round(shiftval, 4)
                    point.dzshiftedsq = round(shiftval*shiftval, 4)
                    dzsqsum.append(point.dzshiftedsq)
                else:
                    point.dzshifted = 'Rejected'

            dsqmean = round(statistics.mean(dzsqsum), 4)
            self.rmse = round(math.sqrt(dsqmean), 4)
            self.ci95 = round(1.96*self.rmse, 4)

        return (accepted, rejected)

    def __len__(self):
        return len(self.points.keys())

    def __iter__(self):
        for key,item in self.points.items():
            yield item


class AtlassGen():

    def makedir(path):
        if not os.path.exists('{0}'.format(path)):
            try:
                os.makedirs('{0}'.format(path))
            except:
                pass
        return path

    def FILELIST (filepattern, inputfolder):
        filelist = []
        if len(filepattern) >=2:
            #print('Number of patterns found : {0}'.format(len(filepattern)))
            pass
        for pattern in filepattern:
            pattern = pattern.strip()
            #print ('Selecting files with pattern {0}'.format(pattern))
            files = glob.glob(inputfolder+"\\"+pattern)
            for file in files:
                filelist.append(file)
        #print('Number of Files founds : {0} '.format(len(filelist)))
        return filelist

    def DIRLIST (inputfolder):
        dirlist = []

        folders = glob.glob(inputfolder+"\\*\\")
        for folder in folders:
            dirlist.append(folder)
        print('Number of Folders founds : {0} '.format(len(dirlist)))
        return dirlist
        
    def FILESPEC(filename):
        # splits file into components
        path,name=os.path.split(filename)
        pattern=name.split(".")
        if len(pattern) == 2:
            name = pattern[0]
            ext = pattern[1]
        else:
            name = pattern[0]
            ext = pattern[len(pattern)-1]
    
        return path, name, ext    

    def GETCOORDS(coords,size):
        #recieves tile name without extn or path
        #use FILESPEC to split file name
        #x and y coords must be the the first 2 portions of the file name an must be able to be separated by _
        boxcoords=[]
        coordsf=[]
        for coord in coords:
            coordsf.append(float(coord))
            
        boxcoords.append([coordsf[0],coordsf[1]])
        boxcoords.append([coordsf[0],coordsf[1]+size])
        boxcoords.append([coordsf[0]+size,coordsf[1]+size])
        boxcoords.append([coordsf[0]+size,coordsf[1]])
        boxcoords.append([coordsf[0],coordsf[1]])
        
        return boxcoords

    
    
    def bufferTile(tile,tilelayout,outputfile,buffer,gndclasses,inputfolder, filetype):
        print(gndclasses)
        print('buffering {0} - out {1}'.format(tile.name, outputfile))
        neighbourlasfiles = []
        try:
            neighbours =  tilelayout.gettilesfrombounds(tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
        
    
        except:
            print("tile: {0} does not exist in geojson file".format(tile.name))
    
        print('Neighbours : {0}'.format(neighbours))
       

        if isinstance(neighbours, str):
            neighbours = [neighbours]

        #Get the neighbouring files
        for neighbour in neighbours:
            neighbour = os.path.join(inputfolder, '{0}.{1}'.format(neighbour, filetype))
            if os.path.isfile(neighbour):
                print('\n{0}'.format(neighbour))
                neighbourlasfiles.append(neighbour)
            else:
                print('\nFile {0} could not be found in {1}'.format(neighbour, inputfolder))

        print(neighbourlasfiles)
        keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin-buffer, tile.ymin-buffer, tile.xmax+buffer, tile.ymax+buffer)
        keep=keep.split()
        log = ''
    
        try:
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + neighbourlasfiles + ['-olaz','-o', outputfile,'-merged','-keep_class']+ gndclasses + keep
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  


        except subprocess.CalledProcessError as suberror:
                log=log +"{0}\n".format(suberror.stdout)
                print(log)
                return (False,None,log)

        except Exception as e:
            log = "Making Buffered for {0} Exception - {1}".format(outputfile, e)
            print(log)
            return(False,None, log)

        finally:
            if os.path.isfile(outputfile):
                log = "Making Buffered for {0} Success".format(outputfile)
                print(log)
                return (True,outputfile, log)

            else: 
                log = "Making Buffered for {0} Failed".format(outputfile)
                print(log)
                return (False,None, log)



    def mergeFiles(inputfolder,outputfile,filetype):

        try:
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(inputfolder,filetype),'-o{0}'.format(filetype),'-o', outputfile,'-merged' ]
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  


        except subprocess.CalledProcessError as suberror:
                log=log +"{0}\n".format(suberror.stdout)
                print(log)
                return (False,None,log)

        except Exception as e:
            log = "Making merged file for {0} Exception - {1}".format(outputfile, e)
            print(log)
            return(False,None, log)

        finally:
            if os.path.isfile(outputfile):
                log = "Making merged for {0} Success".format(outputfile)
                print(log)
                return (True,outputfile, log)

            else: 
                log = "Making merged for {0} Failed".format(outputfile)
                print(log)
                return (False,None, log)

    def clip(input, output, poly, filetype):

        if isinstance(input,str):
            input = [input]


        log=''
        try:
            subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' ] + input + [ '-merged', '-poly', poly, '-o', output, '-o{0}'.format(filetype)]
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            if os.path.isfile(output):
                log = "Clipping {0} output : {1}".format(str(input), str(output)) 
                return (True,output, log)

            else:
                log = "Clipping failed for {0}. May be outside AOI ".format(str(input)) 
                print(log)
                return (False,None,log)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log = "Clipping failed for {0}. Failed at Subprocess ".format(str(input)) 
            print(log)
            return(False, None, log)   
    
        
    def index(input):
    
        log = ''
        try:
            subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            return(True, input, "Success")

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            return(False, None, "Error")

    def asciigridtolas(input, output , filetype):
        '''
        Converts an ascii file to a las/laz file and retains the milimetre precision.
        '''

        log = ''
        if os.path.isfile(input):
            print('Converting {0} to {1}'.format(input,filetype))
            try:
                #las2las -i <dtmfile> -olas -o <dtmlazfile>
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-o{0}'.format(filetype), '-o', output, '-rescale', 0.001, 0.001, 0.001] 
                subprocessargs=list(map(str,subprocessargs)) 
                #print(subprocessargs)
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
                    
            except subprocess.CalledProcessError as suberror:
                log=log +'\n'+ "{0}\n".format(suberror.stdout)
                print(log)
                return (False,None,log)

            except:
                log ='Converting {0} file  to {1} Failed at exception'.format(input, filetype)
                return (False, output, log)
            finally:
                if os.path.isfile(output):
                    log ='Converting {0} file  to {1} success'.format(input, filetype)
                    return (True, output, log)
                else:
                    log ='Converting {0} file  to {1} Failed'.format(input, filetype)
                    return (False, output, log)
            
            
    def lastoasciigrid(x,y,inputF, output, tilesize, step):
        '''
        Converts a las/laz file to ascii and retains the milimetre precision.
        '''

        if os.path.isfile(inputF):
            log = ''
            try:
                #las2las -i <dtmfile> -olas -o <dtmlazfile>
                subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', inputF, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
                subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
                subprocessargs=list(map(str,subprocessargs))       
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            
            except subprocess.CalledProcessError as suberror:
                log=log +'\n'+ "{0}\n".format(suberror.stdout)
                print(log)
                return (False,None,log)

            except:
                log ='Converting las to asc Failed at exception for : {0}'.format(inputF)
                return (False, output, log)
            finally:
                if os.path.isfile(output):
                    log ='Converting las to asc success for : {0}'.format(inputF)
                    return (True, output, log)
                else:
                    log ='Converting las to asc Failed for {0}'.format(inputF)
                    return (False, output, log)
            
        else:
            return(True,None,'Not input File')           