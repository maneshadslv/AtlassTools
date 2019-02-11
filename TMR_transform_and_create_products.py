#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import math
import shutil
import subprocess
import os, glob
import numpy as np
import urllib
from gooey import Gooey, GooeyParser
import time
import datetime
from time import strftime
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make TMR products", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Make TMR products")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("geojsonfile", metavar="TileLayout file", widget="FileChooser", help="Select TileLayout file (.json)", default='')
    main_parser.add_argument("poly", metavar="AOI file", widget="FileChooser", help="polygon shapefile (.shp)", default='')
    main_parser.add_argument('name', metavar="AreaName", help="Project Area Name eg : MR101502 ", default="")
    main_parser.add_argument("epsg", metavar="EPSG", type=int)
    main_parser.add_argument("dx", metavar="dx", type=float)
    main_parser.add_argument("dy", metavar="dy", type=float)
    main_parser.add_argument("dz", metavar="dz", type=float)
    main_parser.add_argument("intensity_min", metavar="Intensity min", type=float, default=100)
    main_parser.add_argument("intensity_max", metavar="Intensity max", type=float, default=2500)    
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    main_parser.add_argument("-tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    main_parser.add_argument("-k", "--kill",metavar="Kill", help="Large triangle size (m)", type=int, default=250)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    
    return main_parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
class TMR_AtlassTile():
    def __init__(self,parent,**kwargs):
        self.parent=parent
        self._params=OrderedDict()
        self._params['TILE_NAME']=''
        self._params['XMIN']=None
        self._params['YMIN']=None
        self._params['XMAX']=None
        self._params['YMAX']=None     
        self._params['TILENUM']=''   
        self.addparams(**kwargs)

    def getneighbours(self,buffer):
        neighbours=[]
        if isinstance(buffer, float) or isinstance(buffer, int):
            XMIN=self.XMIN-buffer
            XMAX=self.XMAX+buffer
            YMIN=self.YMIN-buffer
            YMAX=self.YMAX+buffer
            
            for key,tile in self.parent.tiles.items():
                if tile.XMIN<XMIN<tile.XMAX or tile.XMIN<XMAX<tile.XMAX or XMIN<tile.XMIN<XMAX or XMIN<tile.XMAX<XMAX:
                    if tile.YMIN<YMIN<tile.YMAX or tile.YMIN<YMAX<tile.YMAX or YMIN<tile.YMIN<YMAX or YMIN<tile.YMAX<YMAX:
                        neighbours.append(tile.TILENUM)
        else:
            raise TypeError('only accepts floats or integers for buffer')  


        return neighbours
    
    @property
    def TILE_NAME(self):
        return self._params['TILE_NAME']

    @TILE_NAME.setter    
    def TILE_NAME(self, value): 
        if isinstance(value, str):
            self._params['TILE_NAME']=str(value)
        else:
            raise TypeError('only accepts strings') 
    
    @property
    def TILENUM(self):
        return self._params['TILENUM']

    @TILENUM.setter    
    def TILENUM(self, value): 
        if isinstance(value, str):
            self._params['TILENUM']=str(value)
        else:
            raise TypeError('only accepts strings') 

    @property
    def XMIN(self):
        return self._params['XMIN']

    @XMIN.setter    
    def XMIN(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['XMIN']=float(value)
        else:
            raise TypeError('only accepts floats or integers') 
    @property
    def YMIN(self):
        return self._params['YMIN']

    @YMIN.setter    
    def YMIN(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['YMIN']=float(value)
        else:
            raise TypeError('only accepts floats or integers')    


    @property
    def XMAX(self):
        return self._params['XMAX']

    @XMAX.setter    
    def XMAX(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['XMAX']=float(value)
        else:
            raise TypeError('only accepts floats or integers') 


    @property
    def YMAX(self):
        return self._params['YMAX']

    @YMAX.setter    
    def YMAX(self, value): 
        if isinstance(value, float) or isinstance(value, int):
            self._params['YMAX']=float(value)
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
            for stdkey in ['TILE_NAME','XMIN','YMIN','XMAX','YMAX', 'TILENUM']:
                if not stdkey in data.keys():
                    print('Warning: {0} not in keys'.format(stdkey))
                    print('Current value of {0}'.format(stdkey,self._params[stdkey])) 

            for key,value in data.items():
                if key =='TILE_NAME':
                    self.TILE_NAME=value
                if key =='XMIN':
                    self.XMIN=value
                if key =='YMIN':
                    self.YMIN=value
                if key =='XMAX':
                    self.XMAX=value
                if key =='YMAX':
                    self.YMAX=value   
                if key =='TILENUM':
                    self.TILENUM=value             
                else:
                    if isinstance(value,str) or isinstance(value,float) or isinstance(value,int):
                        self._params[key]=value
                    else:
                        raise TypeError('only accepts strings, float and integers "{0}" is type: {1}'.format(key,type(value))) 

                
        else:
            raise TypeError('only accepts dictionary type, data is of type: {0}'.format(type(value))) 

  
    def addparams(self,**kwargs):
        for key,value in kwargs.items():
            if key =='TILE_NAME':
                self.TILE_NAME=value
            if key =='XMIN':
                self.XMIN=value
            if key =='YMIN':
                self.YMIN=value
            if key =='XMAX':
                self.XMAX=value
            if key =='YMAX':
                self.YMAX=value   
            if key =='TILENUM':
                self.TILENUM=value             
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

        txt=txt[:-1]+'},'+'"geometry":{"type": "Polygon","coordinates":'+'[[[{0},{1}],[{2},{1}],[{2},{3}],[{0},{3}],[{0},{1}]]]'.format(self.XMIN,self.YMIN,self.XMAX,self.YMAX)+'}}'

        return txt

class TMR_AtlassTileLayout():
    fileNo = 0
    def __init__(self):
        self.tiles=OrderedDict()
        pass

    def __iter__(self):
        for key,item in self.tiles.items():
            yield item

    def addtile(self,**kwargs):
        
        for stdkey in ['TILE_NAME','XMIN','YMIN','XMAX','YMAX', 'TILENUM']:
            if not stdkey in kwargs.keys():
                print('Warning: {0} not in keys. Tile not added'.format(stdkey))
                return
        self.tiles[kwargs['TILENUM']]=TMR_AtlassTile(self,**kwargs)

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
                self.tiles[key]=TMR_AtlassTile(self, **value)
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
                     if(key == 'TILENUM'):
                         key = 'TILENUM'
                     tile[key] = val

                 name = tile['TILENUM']           
                 tiles[name] = tile

            self.fromdict(tiles)
        return 


    def createGeojsonFile(self, outputfile):

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

def asciigridtolas(input, output , filetype):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''

    log = ''
    try:
       #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-o{0}'.format(filetype), '-o', output, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
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

def lastoasciigrid(x,y,input, output, tilesize, step):
    '''
    Converts a las/laz file to ascii and retains the milimetre precision.
    '''

    log = ''
    try:
       #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', input, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
        subprocessargs=list(map(str,subprocessargs))       
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting las to asc Failed at exception for : {0}'.format(input)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting las to asc success for : {0}'.format(input)
            return (True, output, log)
        else:
            log ='Converting las to asc Failed for {0}'.format(input)
            return (False, output, log)

def clipandmergelas(filelist,clipshape,lasfile,outformat='las'):
    '''
    clips and merges several lasfiles usinf an ESRI shapefile.
    '''
    try:
        subprocessargs=['C:/LAStools/bin/clip.exe','-i'] +filelist + ['-o{0}'.format(outformat),'-merged', '-o', lasfile, '-poly',clipshape] 
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs) 
    except:
        pass
    finally:
        if os.path.isfile(lasfile):
            return lasfile
        else:
            return None

def transformlas(infile,outfile,x=0,y=0,z=0,outformat='las'):
    #
    #clips and merges several lasfiles usinf an ESRI shapefile.
    #

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] +filelist + ['-o{0}'.format(outformat),'-merged', '-o', lasfile, '-poly',clipshape] 
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs) 
    except:
        pass
    finally:
        if os.path.isfile(lasfile):
            return lasfile
        else:
            return None

def makeDEM(xmin, ymin, xmax, ymax, gndfile, workdir, dtmfile, buffer, kill, step, gndclasses, hydropoints, filetype, poly,areaname):
    #need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
    #use this file for MKP, just remember to remove buffer
    #This will need clipping to AOI
    log = ''
    #Prep RAW DTM
    
    #set up clipping    
    keep='-keep_xy {0} {1} {2} {3}'.format(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)
    keep=keep.split()

    
    try:

        #not changing the classifciation, just creating a buffered unfiltered temp file.
        gndfile2 = gndfile
        gndfile=os.path.join(workdir,'{0}_{1}_dem_gnd.{2}'.format(xmin, ymin,filetype)).replace('\\','/')
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',gndfile2,'-merged','-o{0}'.format(filetype),'-o',gndfile, '-keep_class'] + gndclasses
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    

        #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
        print("Checking for Hydro files")
        if not hydropoints==None:

            
            hydfile=os.path.join(workdir,'{0}_{1}_hydro.{2}'.format(xmin, ymin,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + hydropoints + ['-merged','-o{0}'.format(filetype),'-o',hydfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("clipped Hydro points")

            gndfile2 = gndfile
            gndfile=os.path.join(workdir,'{0}_{1}_dem_hydro.{2}'.format(xmin, ymin,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile2,hydfile,'-merged','-o{0}'.format(filetype),'-o',gndfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("added Hydro points")

        else:
            print("No Hydro files")
        
        print("DEM starting")
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o', dtmfile,'-nbits',32,'-kill',kill,'-step',step] 
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]    
        #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}_{1}: DEM output FAILED.'.format(xmin, ymin))
        log = 'DEM creation Failed for {0}_{1} at Subprocess.'.format(xmin, ymin)
        return(False, None, log)


    finally:
        if os.path.isfile(dtmfile):
            
            log = 'DEM output Success for: {0}_{1}.'.format(xmin, ymin)
            return(True, dtmfile, log)
        else:
            log = 'DEM creation Failed for: {0}_{1}.'.format(xmin, ymin)
            return(False, None, log)

def adjust(input, output, dx, dy, dz, epsg, filetype):
    #las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las
    
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i' , input ,'-o{0}'.format(filetype), '-translate_xyz', dx, dy, dz, '-epsg', epsg ,'-set_version', 1.2,  '-o', output]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(output):
            log = "Adjusting {0} output : {1}".format(str(input), str(output))
            return (True,output, log)

        else:
            log = "Could not adjust : {0}".format(str(input))
            return (False,None,log)
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Could not adjust {0}. Failed at Subprocess".format(str(input))
        return (False,None,log)

def makeXYZ(input, output, filetype):
    #las2las -i <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc -otxt -o <inputpath>/Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz -rescale 0.001 0.001 0.001

    #Prep RAW DTM
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-otxt','-o', output, '-rescale', 0.001, 0.001, 0.001]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make xyz {0}. Failed at Subprocess'.format(str(input))
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'xyz file created for {0}'.format(str(input))
            return (True,output, log)

        else:
            log = 'Could not make xyz {0}'.format(str(input))           
            return (False,None, log)

def index(input):
   
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        return(True, None, "Success")

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        return(False, None, "Error")

def buffertiles(input, bufffile, filetype, buffer, tile):
    log=''
    
    if isinstance(input,str):
        input = [input]
    try:

        #not changing the classifciation, just creating a buffered unfiltered temp file.
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+input+['-merged','-o{0}'.format(filetype),'-o',bufffile]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making buffered file for {0} /nException {1}".format(tile.name, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufffile):
            log = "Making buffered file for {0} Success".format(tile.name)
            return (True,bufffile, log)

        else: 
            log = "Making buffered file for {} Failed".format(tile.name)
            return (False,None, log)

def makeMKP(bufffile, tempfile, output, filetype, gndclasses, hz, vt, buffer, xmin, ymin, tilesize):
    log=''
    cleanup=[tempfile]

    try:

        subprocessargs=['C:/LAStools/bin/lasthin.exe','-i',bufffile,'-o{0}'.format(filetype),'-o',tempfile,'-adaptive',vt,hz,'-classify_as',8,'-ignore_class'] + [0,1,3,4,5,6,7,9,10,11,12,13,14,15,16,17,18,19,20]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

       
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile,'-o{0}'.format(filetype),'-o',output]
        subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmin+tilesize,ymin+tilesize]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
        
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making MKP for {0} /nException {1}".format(bufffile, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = "Making MKP for {0} Success".format(bufffile)
            for file in cleanup:
                if os.path.isfile(file):
                    os.remove(file)
                    pass
            #file contains all original points. Original Ground class (2) has been split into ground (2) and MKP (8)
            return (True,output, log)

        else: 
            log = "Making MKP for {} Failed".format(bufffile)
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
            log = "Clipping failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Clipping failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)

def makegrid(input, output, intensityMin,intensityMax, xmin, ymin):

    
    log = ''

    try:
        '''
        This function needs -ll <xmin> <ymin>
        '''
        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-step', 0.5, '-fill' ,2 ,'-keep_first', '-intensity_average', '-otif', '-nbits', 8 ,'-set_min_max', intensityMin , intensityMax, '-o', output, '-ll', xmin , ymin, '-nrows', 2000, '-ncols', 2000]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make grid {0}, Failed at Subprocess'.format(str(input))  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'Make Grid successful for {0}'.format(str(input))
            return (True,output, log)

        else:
            log = 'Could not make grid {0}'.format(str(input))           
            return (False,None, log)




#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()
    filetype=args.filetype

    inputfolder = args.inputfolder
    areaname = args.name

    buffer=float(args.buffer)
    tilesize=int(args.tile_size)
    dx = args.dx
    dy = args.dy
    dz = args.dz
    epsg = args.epsg
    zone = (int(epsg) - 28300)
    hydropointsfiles=None
    vt = 0.1 
    hz = 20
    poly = args.poly.replace('\\','/')
    geojsonfile = args.geojsonfile.replace('\\','/')
    intensityMin = args.intensity_min
    intensityMax = args.intensity_max
    

    if not args.hydropointsfiles==None:
        hydropointsfiles=args.hydropointsfiles
        hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')
    step=float(args.step)
    kill=float(args.kill)
    gndclasses=[2 ,8]    
    cores = args.cores
    
    tl = AtlassTileLayout()
    tl.fromjson(geojsonfile)
    
    outputpath=args.outputpath.replace('\\','/')
    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_{1}'.format(areaname,strftime("%y%m%d_%H%M"))))
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')

    adjdir = AtlassGen.makedir(os.path.join(outputpath, 'Adjusted')).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(adjdir, 'Buffered')).replace('\\','/')
    mkpdir = AtlassGen.makedir(os.path.join(adjdir, 'MKP_working')).replace('\\','/')
    adjdemworkingdir = AtlassGen.makedir(os.path.join(adjdir, 'DEM_working')).replace('\\','/')
    prodsdir = AtlassGen.makedir(os.path.join(outputpath, 'Products')).replace('\\','/')

    dem1dir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_DEM_1m'.format(areaname))).replace('\\','/')
    dem1esridir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_DEM_1m_ESRI'.format(areaname))).replace('\\','/')
    intensitydir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_Intensity_50cm'.format(areaname))).replace('\\','/')
    lasahddir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_LAS_AHD'.format(areaname))).replace('\\','/')

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(geojsonfile)

 

    print("Reading {0} files \n".format(filetype))
    
    filepattern = args.filepattern.split(';')
    files = AtlassGen.FILELIST(filepattern, inputfolder)
  


    ###########################################################################################################################
    #Adjust las
    adj_tasks = {}

    print("Applying x,y,z adjustments")
    for file in files:

        path, filename, ext = AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        #finalnames[filename]={}
        #finalnames[filename]['CLIPPED_LAS']='{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.las'.format()
        #finalnames[filename]['ESRI_GRID']='{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.las'.format()
        
        output = os.path.join(adjdir, '{0}.{1}'.format(filename, ext)).replace("\\", "/")
     
        adj_tasks[filename] = AtlassTask(filename, adjust, file, output, dx, dy, dz, epsg, filetype)



    p=Pool(processes=cores)      
    adjust_results=p.map(AtlassTaskRunner.taskmanager,adj_tasks.values())
    
    ###########################################################################################################################
    #Create buffered file



    print('\n\n Making buffered files')
    buffer_tasks = {}
    for result in adjust_results:
        #tasklist={'ProcessName':'Run some tasks','fn'=func,'Tasks':{'tile/filename':{'args':args,'kwargs':kwargs,'status':False,'output':None,'log':'blah blah blah\n blah blah blah'}}}
        log.write(result.log)  
        if result.success:
            
            tilename=result.name
            
            #files
            input = os.path.join(adjdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')  #adjusted las
            bufferedfile=os.path.join(workingdir,'{0}_buff.{1}'.format(tilename, filetype)).replace('\\','/')
      

            #Get Neigbouring las files
            print('Creating tile neighbourhood for : {0}'.format(tilename))
            tile = tl.gettile(tilename)
            neighbourlasfiles = []

            try:
                neighbours = tile.getneighbours(buffer)
            except:
                print("tile: {0} does not exist in geojson file".format(tilename))

            #print('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,tilename))

            for neighbour in neighbours:
                neighbour = os.path.join(adjdir,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

                if os.path.isfile(neighbour):
                    neighbourlasfiles.append(neighbour)

            buffer_tasks[tilename] = AtlassTask(tilename, buffertiles, input, bufferedfile, filetype, buffer, tile)
  

    buffer_results=p.map(AtlassTaskRunner.taskmanager,buffer_tasks.values())

    ###########################################################################################################################
    #MKP process
    #use names from clipped las to decide which tiles to generate mkp from unclipped adjusted las.


    #Revision: remove the check against clipped file list. Clipping will be done after this step.

    
    print("Starting MKP")
    mkp_tasks = {}
    for result in buffer_results:
        log.write(result.log)
        if result.success:
  
            tilename = result.name
           
            x,y=tilename.split('_') 
            input = os.path.join(workingdir,'{0}_buff.{1}'.format(tilename, filetype)).replace('\\','/')
            output=os.path.join(mkpdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            tempfile=os.path.join(mkpdir,'{0}_temp.{1}'.format(tilename, filetype)).replace('\\','/')
            
            mkp_tasks[tilename] = AtlassTask(tilename, makeMKP, input, tempfile, output, filetype, gndclasses, hz, vt, buffer, int(x), int(y), int(tilesize))
    
   
    mkp_results=p.map(AtlassTaskRunner.taskmanager,mkp_tasks.values())

    
    ###########################################################################################################################
    #las index mkp las files

    print("Starting MKP file Indexing")
    mkp_index_tasks = {}
    for result in mkp_results:
        log.write(result.log)
        if result.success:
            file = result.result
            path, filename, ext = AtlassGen.FILESPEC(file)
            x,y=filename.split('_') 

            mkp_index_tasks[filename] = AtlassTask(filename, index, file)
            
    
   
    mkp_index_results=p.map(AtlassTaskRunner.taskmanager,mkp_index_tasks.values())

    

    ###########################################################################################################################
    #Clipping the MKP files and the adjusted files to the AOI
    #Making product ADH

    print('Clipping MKP files to the AOI')
    clip_mkp_tasks = {}

    for result in mkp_index_results:
        log.write(result.log)        
        if result.success:
            tilename=result.name
            x,y = tilename.split('_')
            #files 
            input = os.path.join(mkpdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') # mkp
            output = os.path.join(lasahddir, '{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, x, y, zone, 'las')).replace("\\", "/") #<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las
         

            clip_mkp_tasks[tilename] = AtlassTask(tilename, clip, input, output, poly, 'las')


    clip_mkp_results=p.map(AtlassTaskRunner.taskmanager,clip_mkp_tasks.values())   
    



    ###########################################################################################################################
    #Make DEM with the adjusted las in the working directory
    #input buffered las file ?????

    print('Making DEM')
    dem_tasks = {}
    dem_results = []
    #for result in clip_mkp_results:
    for result in buffer_results:
        log.write(result.log)
        if result.success:
            
            tilename=result.name
            x,y = tilename.split('_')
            #files
            input=os.path.join(workingdir,'{0}_buff.{1}'.format(tilename, filetype)).replace('\\','/') # adjusted buffered las files
            output=os.path.join(adjdemworkingdir,'{0}_dem.asc'.format(tilename)).replace('\\','/')

            dem_tasks[tilename] = AtlassTask(tilename, makeDEM, int(x), int(y), int(x)+tilesize, int(y)+tilesize, input, workingdir, output, buffer, kill, step, gndclasses, hydropointsfiles, filetype, poly,areaname)
            
    
            #dem_results.append(makeDEM(int(x), int(y), int(x)+tilesize, int(y)+tilesize, input, workingdir, output, buffer, kill, step, gndclasses, hydropointsfiles, filetype, poly,areaname))

    dem_results=p.map(AtlassTaskRunner.taskmanager,dem_tasks.values())

    ###########################################################################################################################
    #Convert asci to laz
    #asciigridtolas(dtmlazfile)

    print('Converting ASC to LAZ')
    asciigridtolas_tasks={}
    for result in dem_results:
        log.write(result.log)
        if result.success:
            tilename = result.name
            
            
            x,y=tilename.split('_') 


            #files
            input=os.path.join(adjdemworkingdir,'{0}_dem.asc'.format(tilename)).replace('\\','/')
            output=os.path.join(adjdemworkingdir,'{0}_dem.{1}'.format(tilename, filetype)).replace('\\','/')

            asciigridtolas_tasks[tilename] = AtlassTask(tilename, asciigridtolas, input, output, filetype)
    

    asciigridtolas_results=p.map(AtlassTaskRunner.taskmanager,asciigridtolas_tasks.values())


    ###########################################################################################################################
    #Index the DEM laz files
    #index(demlazfile)

    print('Indexing DEM files')
    index_dem_tasks={}
    for result in asciigridtolas_results:
        log.write(result.log)
        if result.success:
            tilename = result.name
            file = os.path.join(adjdemworkingdir,'{0}_dem.{1}'.format(tilename, filetype)).replace('\\','/')
            x,y=tilename.split('_') 

            index_dem_tasks[tilename] = AtlassTask(tilename, index, file)
    
 
    index_dem_results=p.map(AtlassTaskRunner.taskmanager,index_dem_tasks.values())



    ###########################################################################################################################
    #Clipping the DEM las files to the AOI
    #lasclip demlazfile

    print('Clipping the DEM las files to AOI')
    clip_demlaz_tasks = {}

    for result in index_dem_results:
        log.write(result.log)
        if result.success:
            
            tilename=result.name

            #files 
            input=os.path.join(adjdemworkingdir,'{0}_dem.{1}'.format(tilename, filetype)).replace('\\','/') #dtmlaz
            output = os.path.join(adjdemworkingdir,'{0}_dem_clipped.{1}'.format(tilename, filetype)).replace('\\','/')

            clip_demlaz_tasks[tilename] = AtlassTask(tilename, clip, input, output, poly, filetype)

    clip_demlaz_results=p.map(AtlassTaskRunner.taskmanager,clip_demlaz_tasks.values())   


    #############################################################################################################################
    #Convert the laz files to asci
    #lasgrid
    #TODo

    print('Converting Clipped {0} to asc'.format(filetype))
    lastoasciigrid_tasks={}
    for result in  clip_demlaz_results:
        log.write(result.log)
        if result.success:
            tilename = result.name

            x,y=tilename.split('_') 

            #files
            input=os.path.join(adjdemworkingdir,'{0}_dem_clipped.{1}'.format(tilename, filetype)).replace('\\','/')
            output=os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, x, y)).replace('\\','/')

            lastoasciigrid_tasks[tilename] = AtlassTask(tilename, lastoasciigrid,int(x), int(y), input, output, int(tilesize), step)
    

    lastoasciigrid_results=p.map(AtlassTaskRunner.taskmanager,lastoasciigrid_tasks.values())



    ##########################################################################################################################
    #Download prj file for the requied zone

    link = "http://spatialreference.org/ref/epsg/gda94-mga-zone-{0}/prj/".format(zone)
    projfile = os.path.join(prodsdir, '{0}_tile_layout_shapefile.prj'.format(areaname)).replace("\\", "/")
    prjfile = urllib.request.urlretrieve(link, projfile)
    

    ###########################################################################################################################
    #MAKE XYZ from the dtm asci file, output xyz file in Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz
    #makexyz

    print('Making XYZ files')
    xyz_tasks = {}
    for result in lastoasciigrid_results:
        log.write(result.log)
        if result.success:
            
            tilename = result.name
            x,y=tilename.split('_') 

            #files 
            input=os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, x, y)).replace('\\','/') #dtm asci file
            prjfile1 = os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.prj'.format(areaname, x, y)).replace('\\','/')
            shutil.copyfile(projfile, prjfile1) 
            output = os.path.join(dem1dir,'{0}_2018_SW_{1}_{2}_1k_1m.xyz'.format(areaname, x, y)).replace('\\','/')

            xyz_tasks[tilename] = AtlassTask(tilename, makeXYZ, input, output, filetype)


    xyz_results=p.map(AtlassTaskRunner.taskmanager,xyz_tasks.values())   

    for result in xyz_results:
        log.write(result.log)


    ###########################################################################################################################
    #MAKE GRID from the AHD las files, output tif file
    #makexyz

    print('Making Intensity Image')
    grid_tasks = {}
    for result in clip_demlaz_results:
        log.write(result.log)
        if result.success:
            
            tilename = result.name
            x,y=tilename.split('_') 

            #files 
            input = os.path.join(lasahddir, '{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, x, y, zone, 'las')).replace("\\", "/") #<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las
            output = os.path.join(intensitydir,'{0}_2018_SW_{1}_{2}_1k_50cm_INT.tif'.format(areaname, x, y)).replace("\\", "/")   #<inputpath>/Products/<Area_Name>_Intensity_50cm/<Name>_2018_SW_<X>_<Y>_1k_50cm_INT.tif

            grid_tasks[tilename] = AtlassTask(tilename, makegrid, input, output, intensityMin,intensityMax, int(x), int(y))


    grid_results=p.map(AtlassTaskRunner.taskmanager,grid_tasks.values())   
    
    for result in grid_results:
        log.write(result.log)
    print('Making Poducts Completed')

    '''
    print('Making TileLayout for processed files')

    tilelayout2 = TMR_AtlassTileLayout()
    jsonfile = os.path.join(prodsdir, 'tilelayout.json')


    for file in files:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilename = '{0}_SW_{1}_{2}_1k'.format(areaname, x, y)
        tilelayout2.addtile(TILE_NAME=tilename, XMIN=float(x), YMIN=float(y), XMAX=float(x)+tilesize, YMAX=float(y)+tilesize, TILENUM=filename)
         
    jsonfile = tilelayout2.createGeojsonFile(jsonfile)

    print("Making geojson file : Completed\n")
    '''
    prjfile = os.path.join(prodsdir, '{0}_tile_layout.prj'.format(areaname)).replace("\\", "/")
    prjfilespec=AtlassGen.FILESPEC(prjfile)
    if not os.path.exists(prjfilespec[0]):
        os.makedirs(prjfilespec[0])
    
    w = shapefile.Writer(shapefile.POLYGON)
    w.autoBalance = 1
    w.field('TILE_NAME','C','255')
    w.field('XMIN','N',12,3)
    w.field('YMIN','N',12,3)
    w.field('XMAX','N',12,3)
    w.field('YMAX','N',12,3)
    w.field('TILENUM','C','16')



    print("Making prj file : Started\n")
    with open(prjfile,"w") as f:

        
        #write the header to the file.
        f.write('[TerraScan project]\n')
        f.write('Scanner=Airborne\n')
        f.write('Storage={0}1.2\n'.format(filetype))
        f.write('StoreTime=2\n')
        f.write('StoreColor=0\n')
        f.write('RequireLock=0\n')
        f.write('Description=Created using Compass\n')
        f.write('FirstPointId=1\n')
        f.write('Directory={0}\n'.format(inputfolder))
        f.write('PointClasses=\n')
        f.write('Trajectories=\n')
        f.write('BlockSize={0}\n'.format(str(tilesize)))
        f.write('BlockNaming=0\n')
        f.write('BlockPrefix=\n')   
        
        
        #make a prj fille

        for file in files:
            filepath,filename,extn=AtlassGen.FILESPEC(file)
            x,y=filename.split('_')
            boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
            f.write( '\nBlock {0}.{1}\n'.format(filename,extn))
            for i in boxcoords:
                f.write(  ' {0} {1}\n'.format(i[0],i[1]))

        f.close
        print("Making prj file : Completed\n")
        

    print("Making shp file : Started\n")

    for file in files:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilename = '{0}_SW_{1}_{2}_1k'.format(areaname, x, y)
        boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
        w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
        w.record(TILE_NAME='{0}'.format(tilename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='{0}_{1}'.format(x,y))
    
    w.save(prjfile.replace('.prj','_shapefile'))           
    print("Making shp file : Completed\n")
    

    print('Data available at : {0}'.format(outputpath))
    print('---------------------------------------------------------------------------------------------------------\nProcess Completed')
    log.close()
    return


if __name__ == "__main__":
    main()         

'''
Make def for each of the bolow functions;


kwargs;
    <input path>
    <input extn>
    <Area name> eg <MR101502>
    <poly>
    <dx>
    <dy>
    <dz>
    <epsg> or <Zone>   EPSG= 28300 + <Zone>
    <cores>
    <intensity Min>
    <intensity max>


1.
make output folder structure based on
<inputpath>/Adjusted/
<inputpath>/Adjusted/Working
<inputpath>/Adjusted/MKP

<inputpath>/Products/<Area_Name>_DEM_1m
<inputpath>/Products/<Area_Name>_DEM_1m_ESRI
<inputpath>/Products/<Area_Name>_Intensity_50cm
<inputpath>/Products/<Area_Name>_LAS_AHD

2. 
#las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las

3.
#need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
use this file for MKP, just remember to remove buffer
MakeGrids Just DEM in <inputpath>/Adjusted/<name>.las  ... to <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc    
This will need clipping to AOI

4. 
las2las -i <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc     -otxt -o <inputpath>/Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz -rescale 0.001 0.001 0.001

5.
lasindex <inputpath>/Adjusted/<name>.las

6.
Make MKP vt=0.1 hz=20 -input=<inputpath>/Adjusted/Working/<name>.las output=<inputpath>/Adjusted/MKP/<name>.las --set_classification 8  (remove buffer)

7.
lasindex <inputpath>/Adjusted/MKP/<name>.las


8.
lasclip -i -use_lax <inputpath>/Adjusted/<name>.las <inputpath>/Adjusted/MKP/<name>.las -merged -poly <poly> -o <inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las -olas


9.
lasgrid -i<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las -step 0.5 -fill 2 -keep_first -intensity_average -otif -nbits 8 -set_min_max <intensity Min> <intensity Max> -o <inputpath>/Products/<Area_Name>_Intensity_50cm/<Name>_2018_SW_<X>_<Y>_1k_50cm_INT.tif -nrows 2000 -ncols 2000



set up multi thread process for each
'''


#



#lasgrid -i W:\TMR_Mackaybeesck_VQ780_180923\20181012\dz\clipped\*.las -step 0.5 -fill 2 -keep_first -intensity_average -otif -nbits 8 -set_min_max 100 2500 -cores 18 -odir W:\TMR_Mackaybeesck_VQ780_180923\20181012\clipped_intensity -nrows 2000 -ncols 2000

#C:\LASTools\bin\lasgrid -i *.laz -cores 18 -keep_last -step 5 -point_density -otif -odir point_density

