#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import itertools

import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import os, glob



import time
import datetime
from contextlib import redirect_stderr, redirect_stdout
import geojson
from collections import defaultdict , OrderedDict
import json

import numpy as np
import linecache
import scipy
from scipy import misc
from scipy.interpolate import griddata
from scipy.ndimage import morphology
from scipy.ndimage import filters


#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# Original coding: Alex Rixon 05/06/2019
# Produces vegetation modelling grids from a tiled dataset of classified LAZ and DEMS in LAZ format
# Assumes south west corner naming convention files will need to be renamed to match this convention
#
# requires a tilelayout in json format.
# tilelayout class below can be used to create this file.
#
# requires licensed version of lastools to be installed
#
# requires python 3.7
#
# requires the following python extensions:
#   scipy (use pip install scipy)
#   numpy (use pip install numpy)
#   geojson (use pip install geojson)


#-----------------------------------------------------------------------------------------------------------------
#Scheduled additions:
# no further additions
# 
# 
#-----------------------------------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------------------
#Notes on running command
#-----------------------------------------------------------------------------------------------------------------
# Process is designed to be single threaded and can be managed by external multithread tool
#
# command pattern:
# python W:\Lockyer\Script\VegModelling.py --tile=#name# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --inputlazpath=#inputlazpath# --inputdempath=#inputlazpath# --workingpath=#workingpath# --extn=laz --tilelayout=#tilelayout# --restart=True --makefcmlayers=True
#
# python W:\Lockyer\Script\VegModelling.py --tile=417000_6927000 --xmin=417000.0 --ymin=6927000.0 --xmax=418000.0 --ymax=6928000.0 --inputlazpath=F:/Processing/Lockyer/LiDAR_DEM/2018/01_LAS_AHD --inputdempath=F:/Processing/Lockyer/LiDAR_DEM/2018/31a_DEM_1m_ESRI_ASCII_tiles --workingpath=F:/Processing/Lockyer/LiDAR_DEM/2018/FCM99 --extn=laz --tilelayout=F:/Processing/Lockyer/LiDAR_DEM/2018/01_LAS_AHD/TileLayout.json --restart=True --makefcmlayers=True
#
# Input file preparation was required which included converting DEM ascii grids to laz and re-naming any tiled data to south west corner naming convention == <xmin>_<ymin>.laz


#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants

defaults={}
defaults['tile']=None
defaults['tilelayout']=None
defaults['xmin']=None 
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None

defaults['inputlazpath']=None
defaults['inputdempath']=None
defaults['extn']=None
defaults['tilelayout']=None
defaults['workingpath']=None

#data handling allows for keeping processing files and restarting process
defaults['keepfiles']=None
defaults['restart']=None

# stuff for DEM
defaults['hydropoints']=None
defaults['step']=None
defaults['buffer']=50
defaults['kill']=500

defaults['makefcmlayers']=None

#-----------------------------------------------------------------------------------------------------------------
#Class definitions
#-----------------------------------------------------------------------------------------------------------------
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

class Tile():
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

class TileLayout():
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
        self.tiles[kwargs['name']]=Tile(self,**kwargs)

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
                self.tiles[key]=Tile(self, **value)
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
                outputfile = outputfile+ str(TileLayout.fileNo)+'.json'
                TileLayout.fileNo += 1
                continue

            else:
                outputfile, ex = outputfile.split('.')
                outputfile = outputfile+ str(TileLayout.fileNo+1)+'.json'
                TileLayout.fileNo += 1
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

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def PrintMsg(Message,Heading=False):
    if not Heading:
        msgstring='\t{0}'.format(Message)
        print(msgstring)
    else:
        msgstring='\n'
        msgstring=msgstring+'----------------------------------------------------------------------------\n'
        msgstring=msgstring+'{0}: {1}\n'.format(time.ctime(time.time()),Message)
        msgstring=msgstring+'----------------------------------------------------------------------------\n'
        print(msgstring)
        
    return msgstring + '\n'

def PrintHelp(defaults):
    PrintMsg('Below is an example of acceptable options and arguments:','Print help.')
    for arg in list(defaults.keys()):
        PrintMsg('\t--{0}={1}'.format(arg,defaults[arg]))
    print('----------------------------------------------------------------------------')

def makedir(path):
    if not os.path.exists('{0}'.format(path)):
        try:
            os.makedirs('{0}'.format(path))
        except:
            pass
    return path

def filelist (filepattern, inputfolder):
    filelist = []
    if len(filepattern) >=2:
        #print('Number of patterns found : {0}'.format(len(filepattern)))
        pass
    for pattern in filepattern:
        pattern = pattern.strip()
        #print ('Selecting files with pattern {0}'.format(pattern))
        files = glob.glob(inputfolder+"\\"+pattern)
        for file in files:
            if not file.strip() == '': 
                filelist.append(file)
    #print('Number of Files founds : {0} '.format(len(filelist)))
    return filelist

def filespec(filename):
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



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------

    try:
        longargs=list('{0}='.format(key) for key in list(defaults.keys()))
        settings=defaults
        opts, args = getopt.getopt(argv,"h",["help"] + longargs)
    except getopt.GetoptError as err:
        # print help information and exit:
        PrintMsg(str(err),Heading=True)
        PrintHelp(defaults)
        sys.exit(2)
        
    PrintMsg('Setting arguments:',Heading=True)

    #Get options
    syslog=''
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintHelp(longargs,defaults)
            sys.exit()
        elif opt.replace('-','') in list(defaults.keys()):
            syslog=syslog+PrintMsg('{0}={1}'.format(opt, arg))
            settings[opt.replace('-','')]=arg.replace('\\','/')
        else:
            PrintHelp(defaults)
            sys.exit()

    #create variables from settings
    tile=settings['tile']
    if not tile==None:
        pass
    else:
        PrintMsg('tile not set')
        return

    tilelayout=settings['tilelayout']
    if not tilelayout==None:
        tilelayout=TileLayout()
        tilelayout.fromjson(settings['tilelayout'].replace('\\','/'))
    else: 
        PrintMsg('tilelayout not set')
        return    


    xmin=settings['xmin']
    if not xmin==None:
        xmin=float(xmin)
    else:
        PrintMsg('xmin not set')
        return

    ymin=settings['ymin']
    if not ymin==None:
        ymin=float(ymin)
    else:
        PrintMsg('ymin not set')
        return

    xmax=settings['xmax']
    if not xmax==None:
        xmax=float(xmax)
    else:
        PrintMsg('xmax not set')
        return

    ymax=settings['ymax']
    if not ymax==None:
        ymax=float(ymax)
    else:
        PrintMsg('ymax not set')
        return

    buffer=settings['buffer']
    if not buffer==None:
        buffer=float(buffer)
    else:
        PrintMsg('buffer not set')
        return

    inputlazpath=settings['inputlazpath']
    if not inputlazpath==None:
        inputlazpath=inputlazpath.replace('\\','/')
        
    else: 
        PrintMsg('inputlazpath not set')
        return

    inputdempath=settings['inputdempath']
    if not inputdempath==None:
        inputdempath=inputdempath.replace('\\','/')
    else: 
        PrintMsg('inputdempath not set')
        return

    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=makedir(workingpath.replace('\\','/'))
        logfile=os.path.join(workingpath,'{0}.log'.format(tile))
        outpath=makedir(os.path.join(workingpath,'output'))
        CHM1path=makedir(os.path.join(workingpath,'output/CHM_1m'))
        CHM5path=makedir(os.path.join(workingpath,'output/CHM_5m'))
        FCM5path=makedir(os.path.join(workingpath,'output/FCM_5m'))
        laznorm=makedir(os.path.join(workingpath,'output/Normalised_LAZ'))
        workingpath=makedir(os.path.join(workingpath,'working'))
        temppath=makedir(os.path.join(workingpath,tile))
        tempinputdempath=makedir(os.path.join(temppath,'demsrc'))

    else: 
        PrintMsg('workingpath not set')
        return
    extn=settings['extn']


    if not extn==None:
        pass
    else: 
        PrintMsg('extn not set')
        return

    buffer=settings['buffer']
    if not buffer==None:
        buffer=float(buffer)
    else:
        PrintMsg('buffer not set')
        return     

    restart=settings['restart']
    if not restart==None:
        restart=True
    else:
        restart=False


    makefcmlayers=settings['makefcmlayers']
    if not makefcmlayers==None:
        makefcmlayers=True
    else:
        makefcmlayers=False


    keepfiles=settings['keepfiles']
    if not keepfiles==None:
        keepfiles=True
    else:
        keepfiles=False

    #Process recovery
    #Test for the log file to see if the process has been completed before.
    #Skips processing if log and all outputs are found, and restart is not False
    if os.path.isfile(logfile) and restart:
        return 

    try:
        #write log header
        log='\n'
        log=log +PrintMsg(Message="Processing tile:{0}".format(tile),Heading=True)
        log=log+ syslog + '\n'

        with open(logfile, 'w') as f:
            for line in log:
                f.write(line)
            f.close()
        
        #restart the log
        log='\n'

        lazfile=os.path.join(inputlazpath,'{0}.{1}'.format(tile,extn))

        # Get overlapping tiles in buffer
        log=log +PrintMsg(Message="Getting Neighbours",Heading=True)
        neighbours=tilelayout.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

        log=log +PrintMsg('{0} Neighbours detected'.format(len(neighbours)))
        log=log +PrintMsg('Copying to workspace')

        # Copy dem tiles to workspace
        for neighbour in neighbours:
            source=os.path.join(inputdempath,'{0}.{1}'.format(neighbour,extn))
            dest=tempinputdempath
            shutil.copy2(source,dest)
            neighbour=os.path.join(dest,'{0}.{1}'.format(neighbour,extn))

            log=log + PrintMsg('File copied:{1}\t{0}'.format(neighbour,os.path.isfile(neighbour)))

        #merge DEM from buffer.
        log=log +PrintMsg(Message='Merge DEM from buffer.',Heading=True)
        mergeddemfile=os.path.join(temppath,'{0}_dem.laz'.format(tile))
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',os.path.join(tempinputdempath,'*.laz'),'-olaz','-merged','-o',mergeddemfile]
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
        subprocessargs=subprocessargs+['-set_classification', 2]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(mergeddemfile,os.path.isfile(mergeddemfile)))

        #normalise data to DEM
        log=log +PrintMsg(Message='Normalise data to DEM.',Heading=True)
        normalisedlas=os.path.join(temppath,'{0}_norm.laz'.format(tile))
        subprocessargs=['C:/LAStools/bin/lasheight.exe','-i',lazfile,'-ground_points',mergeddemfile,'-all_ground_points','-olaz','-merged','-o',normalisedlas,'-replace_z']
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
        subprocessargs=subprocessargs+['-keep_class',1,2,3,4,5,6,8,9,10,11,13,14,15,16,17,18,19]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(normalisedlas,os.path.isfile(normalisedlas)))

        #Fix near ground classification
        log=log +PrintMsg(Message='Fix near ground classification.',Heading=True)
        normalisedlas2=os.path.join(laznorm,'{0}_normalised.laz'.format(tile))
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',normalisedlas,'-olaz','-merged','-o',normalisedlas2]
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
        subprocessargs=subprocessargs+['-classify_z_between_as', -0.1, 0.1, 2]
        subprocessargs=subprocessargs+['-classify_z_between_as', 0.1, 0.3, 3]
        subprocessargs=subprocessargs+['-classify_z_between_as', 0.3, 2.0, 4]
        subprocessargs=subprocessargs+['-clamp_z',0.0,75.0]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(normalisedlas2,os.path.isfile(normalisedlas2)))

        #make CHM1
        log=log +PrintMsg(Message='Make 1m CHM.',Heading=True)
        CHM1=os.path.join(CHM1path,'SW_{0}_{1}_1km_1m_ESRI_CHM.asc'.format(int(xmin),int(ymin)))
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',normalisedlas2,'-oasc','-o',CHM1,'-step', 1,'-elevation_highest']
        subprocessargs=subprocessargs+['-keep_class',2,3,4,5]
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',1000,'-ncols',1000]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(CHM1,os.path.isfile(CHM1)))


        #make CHM5
        log=log +PrintMsg(Message='Make 5m CHM.',Heading=True)
        CHM5=os.path.join(CHM5path,'SW_{0}_{1}_1km_5m_ESRI_CHM.asc'.format(int(xmin),int(ymin)))
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',normalisedlas2,'-oasc','-o',CHM5,'-step', 5,'-elevation_highest']
        subprocessargs=subprocessargs+['-keep_class',2,3,4,5]
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',200,'-ncols',200]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(CHM5,os.path.isfile(CHM5)))

        #make FCM5 
        log=log +PrintMsg(Message='Make 5m FCM.',Heading=True)
        # get total valid points per cell
        FCMTotal=os.path.join(temppath,'{0}_{1}_FCM_TOTAL.asc'.format(int(xmin),int(ymin)))
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',normalisedlas2,'-oasc','-o',FCMTotal,'-step',5,'-counter_32bit']
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',200,'-ncols',200]
        subprocessargs=subprocessargs+['-keep_class',1,2,3,4,5,6,8,9,10,11,13,14,15,16,17,18,19]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(FCMTotal,os.path.isfile(FCMTotal)))

        # get total vegation points per cell
        FCMVeg=os.path.join(temppath,'{0}_{1}_FCM_VEG.asc'.format(int(xmin),int(ymin)))
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',normalisedlas2,'-oasc','-o',FCMVeg,'-step',5,'-counter_32bit']
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',200,'-ncols',200]
        subprocessargs=subprocessargs+['-keep_class',3,4,5]
        log=log +'\n{0}\n'.format(subprocessargs)  
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs) 
        log=log + PrintMsg('File created:{1}\t{0}'.format(FCMVeg,os.path.isfile(FCMVeg)))

        #load ascii grids and calculate fraction
        a=AsciiGrid()
        a.readfromfile(FCMTotal)

        b=AsciiGrid()
        b.readfromfile(FCMVeg)

        ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
        ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
        zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
        nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

        azero=ones*(a.grid==0)
        azero=azero*-1

        a.grid = np.where(a.grid>0,a.grid,azero)
        c=AsciiGrid()
        c.header=b.header
        c.grid=np.divide( b.grid,a.grid)
        c.grid = np.where(c.grid>0,c.grid,zeros)


        FCM5=os.path.join(FCM5path,'SW_{0}_{1}_1km_5m_ESRI_FCM.asc'.format(int(xmin),int(ymin)))
        c.savetofile(FCM5)
        log=log + '\n'
        log=log + PrintMsg('File created:{1}\t{0}'.format(FCM5,os.path.isfile(FCM5)))

        if makefcmlayers:
            log=log + PrintMsg('Making FCM layers',True)
            FCM5layerspath=makedir(os.path.join(FCM5path,'layered'))

            for i in range(0,26,1):
                

                if i==25:
                    low=float(i)+0.001
                    high=75
                else:
                    low=float(i)+0.001
                    high=i+1

                log=log +'\n'+ PrintMsg('FCM layer {0}m_to_{1}m'.format(int(i),int(high)))

                #make FCM5 output height filtered layer of laz for gridding
                FCMVeglaz=os.path.join(FCM5layerspath,'{0}_{1}_FCMVeg_{2}.laz'.format(int(xmin),int(ymin),'{0}m_to_{1}m'.format(int(i),int(high))))
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i',normalisedlas2,'-olaz','-o',FCMVeglaz]
                subprocessargs=subprocessargs+['-keep_class',3,4,5]
                subprocessargs=subprocessargs+['-keep_z',low,high]
                log=log +'\n\t\t{0}\n'.format(subprocessargs)  
                subprocessargs=map(str,subprocessargs)        
                subprocess.call(subprocessargs) 
                log=log + PrintMsg('\t\tFile created:{1}\t{0}'.format(FCMVeglaz,os.path.isfile(FCMVeglaz)))

                #make FCM5 for layer
                FCMVeg=os.path.join(FCM5layerspath,'{0}_{1}_FCMVeg_{2}.asc'.format(int(xmin),int(ymin),'{0}m_to_{1}m'.format(int(i),int(high))))
                subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',FCMVeglaz,'-oasc','-o',FCMVeg,'-step',5,'-counter_32bit']
                subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',200,'-ncols',200]
                log=log +'\n\t\t{0}\n'.format(subprocessargs)  
                subprocessargs=map(str,subprocessargs)        
                subprocess.call(subprocessargs) 
                log=log + PrintMsg('\t\tFile created:{1}\t{0}'.format(FCMVeg,os.path.isfile(FCMVeg)))

                #load ascii grids and calculate fraction
                a=AsciiGrid()
                a.readfromfile(FCMTotal)

                ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
                ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
                zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
                nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

                #file may not exist if there is not data in that band
                if os.path.isfile(FCMVeg):
                    b=AsciiGrid()
                    b.readfromfile(FCMVeg)


                    azero=ones*(a.grid==0)
                    azero=azero*-1

                    a.grid = np.where(a.grid>0,a.grid,azero)
                    c=AsciiGrid()
                    c.header=b.header
                    c.grid=np.divide( b.grid,a.grid)
                    c.grid = np.where(c.grid>0,c.grid,nodata)
                else:
                    c=AsciiGrid()
                    c.header=b.header
                    c.grid=nodata

                FCM5=os.path.join(FCM5layerspath,'SW_{0}_{1}_1km_5m_ESRI_FCM_{2}.asc'.format(int(xmin),int(ymin),'{0}m_to_{1}m'.format(int(i),int(high))))
                c.savetofile(FCM5)
                log=log + PrintMsg('\t\tFile created:{1}\t{0}'.format(FCM5,os.path.isfile(FCM5)))

        
    finally:
        if not keepfiles:
            log=log + PrintMsg(Message='Removing temporary files and folders',Heading=True)
            for folder in [tempinputdempath,temppath]:
                cleanupfiles=filelist('*.*',folder)
                for file in cleanupfiles:
                    if os.path.isfile(file):
                        os.remove(file)
                    else:
                        pass
                    log=log + PrintMsg('File removed:{1}\t{0}'.format(file,os.path.isfile(file)==False))

                if os.path.isdir(folder):
                    shutil.rmtree(folder, ignore_errors=False)
                    
                    log=log + PrintMsg('Folder removed:{1}\t{0}'.format(folder,os.path.isdir(folder)==False))
                    log=log +'\n'

        log=log + PrintMsg(Message='Processing completed',Heading=True)

        with open(logfile, 'a') as f:
            for line in log:
                f.write(line)
            f.close()
        
    

if __name__ == "__main__":
    main(sys.argv[1:])            