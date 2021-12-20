import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

def makeBufferedFiles(tilename,neighbourlasfiles, outputpath, xmin, ymin,xmax,ymax,buffer,filetype):

    if isinstance(neighbourlasfiles, str):
        neighbourlasfiles = [neighbourlasfiles]

  
    bufflasfile = os.path.join(outputpath,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(xmin-buffer), ymin-buffer, xmax+buffer, ymax+buffer)
    keep=keep.split()
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + neighbourlasfiles + ['-olaz','-o', bufflasfile,'-merged'] + keep 
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)      
        

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making Buffered for {0} /nException {1}".format(bufflasfile, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufflasfile):
            log = "Making Buffered for {0} Success".format(bufflasfile)
            return (True,bufflasfile, log)

        else: 
            log = "Making Buffered for {0} Failed".format(bufflasfile)
            return (False,None, log)
   
   

if __name__ == '__main__':
    #python C:/AtlassTools/MakeBufferedTilesLib.py #name# #xmin# #ymin# #xmax# #ymax# inputdir outputdir "D:\temp\Test_TL\TileLayout_18.json" "laz" #name# 200

    tilename, xmin,ymin,xmax,ymax,inputdir,outputdir,inputgeojsonfile,filetype,outputfilename,buffer= sys.argv[1:12]

    xmin = float(xmin)
    xmax = float(xmax)
    ymin = float(ymin)
    ymax = float(ymax)

    #Making the neighbourhood files
    print('Creating tile neighbourhood for : {0}'.format(tilename))
    buffdir = outputdir
    neighbourlasfiles = []
    neighbours = []
    makebuff_results = []


    #read tilelayout into library
    tl_in = AtlassTileLayout()
    tl_in.fromjson(inputgeojsonfile)



    try:
        neighbours =  tl_in.gettilesfrombounds(int(xmin)-int(buffer),int(ymin)-int(buffer),int(xmax)+int(buffer),int(ymax)+int(buffer))

    except:
        print("tile: {0} does not exist in geojson file".format(tilename))

    print('Neighbours : {0}'.format(neighbours))
    
    #files
    for neighbour in neighbours:
        neighbour = os.path.join(inputdir, '{0}.{1}'.format(neighbour, filetype))
        if os.path.isfile(neighbour):
            print('\n{0}'.format(neighbour))
            neighbourlasfiles.append(neighbour)
        else:
            print('\nFile {0} could not be found in {1}'.format(neighbour, inputdir))

    makebuff_results = makeBufferedFiles(tilename,neighbourlasfiles, outputdir, int(xmin), int(ymin),int(xmax),int(ymax),int(buffer),filetype)

    print(makebuff_results)
   