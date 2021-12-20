#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
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

import scipy
from scipy import misc
from scipy.interpolate import griddata
from scipy.ndimage import morphology
from scipy.ndimage import filters

sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 08/05/2019 -Alex Rixon - Original development Alex Rixon
# 
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#Tool is designed to copy data to local drive, process products and prepare delivery and achive datasets for DPIPWE


#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings


defaults={}
defaults['tile']=None
defaults['aoi']=None
defaults['workingpath']=None
defaults['chmgridfile']=None
defaults['demfile']=None
defaults['__keepfiles']=None


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

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------
    
    #python C:\AtlassTools\MakeHYDRO_GRIDS_AB.py --tile=#name# --workingpath=W:\temp2\working\working --chmgridfile= --demfile= --aoi=


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
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintHelp(longargs,defaults)
            sys.exit()
        elif opt.replace('-','') in list(defaults.keys()):
            PrintMsg('{0}={1}'.format(opt, arg))
            settings[opt.replace('-','')]=arg
        else:
            PrintHelp(defaults)
            sys.exit()
            #raise Exception('Unknown input type')

    #create variables from settings
    tile=settings['tile']
    if not tile==None:
        pass
    else:
        PrintMsg('tile not set')
        return

    aoi=settings['aoi']
    if not aoi==None:
        aoi=aoi.replace('\\','/')
    else: 
        PrintMsg('aoi not set')
        #return              

    chmgridfile=settings['chmgridfile']
    if not chmgridfile==None:
        chmgridfile=chmgridfile.replace('\\','/')
    else: 
        PrintMsg('chmgridfile not set')
        return       

    demfile=settings['demfile']
    if not demfile==None:
        demfile=demfile.replace('\\','/')
    else: 
        PrintMsg('demfile not set')
        return   

    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
        chmfile=os.path.join(workingpath,'{0}_CHM.asc'.format(tile)).replace('\\','/')
        cleanupfiles=[]
        #cleanupfiles.append(chmfile)
    else: 
        PrintMsg('workingpath not set')
        return                 
            

    a=AsciiGrid()
    b=AsciiGrid()   

    #chmgrid File
    a.readfromfile(chmgridfile) 
    #DEM file    
    b.readfromfile(demfile)     

    ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
    zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
    nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

    #if canopy height = 0 then 0
    #if dem = no data then no data
    c=AsciiGrid()  
    c.header=a.header
    c.grid=np.subtract(a.grid,b.grid)
    c.grid=np.where(c.grid>=0,c.grid,zeros)
    c.grid=np.where(b.grid==b.nodata_value,nodata,c.grid)
    c.savetofile(chmfile) 

    # clean up workspace
    PrintMsg('Cleanup',Heading=True)
    for file in cleanupfiles:
        if os.path.isfile(file):
            os.remove(file)
            PrintMsg('file: {0} removed.'.format(file))
            pass
        else:
            PrintMsg('file: {0} not found.'.format(file))
    '''
    for folder in cleanupfolders:
        if os.path.isdir(folder):
            #shutil.rmtree(folder, ignore_errors=True)
            pass
    '''
if __name__ == "__main__":
    main(sys.argv[1:])            