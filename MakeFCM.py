
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
import numpy as np
import io
import datetime
import time
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *






#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

cleanupfolders=[]

defaults={}
defaults['tile']=None #(delivery tile name)
defaults['lazfile']=None #(input file name)
defaults['outpath']=None #location to process and store results
defaults['aoi']=None #clip polygon
defaults['xmin']=None
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None
defaults['step']=None
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
    #python \\10.10.10.142\projects\PythonScripts\MakeFCM.py --tile=#name# --lazfile=w:\data\#name#.laz --outpath=W:\temp2\working\working --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --step=2

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

    #create variables from settings
    tile=settings['tile']
    if not tile==None:
        pass
    else:
        PrintMsg('tile not set')
        return

    outpath=settings['outpath']
    if not outpath==None:
        outpath=AtlassGen.makedir(outpath.replace('\\','/'))
        working=AtlassGen.makedir(os.path.join(outpath,'working'))
    else:
        PrintMsg('outpath not set')
        return

    lazfile=settings['lazfile']
    if not lazfile==None:
        lazfile=lazfile.replace('\\','/')
        pass
    else:
        PrintMsg('lazfile not set')
        return

    xmin=settings['xmin']
    if not xmin==None:
        xmin=float(xmin)
        pass
    else:
        PrintMsg('xmin not set')
        return

    ymin=settings['ymin']
    if not ymin==None:
        ymin=float(ymin)
        pass
    else:
        PrintMsg('ymin not set')
        return

    xmax=settings['xmax']
    if not xmax==None:
        xmax=float(xmax)
        pass
    else:
        PrintMsg('xmax not set')
        return

    ymax=settings['ymax']
    if not ymax==None:
        ymax=float(ymax)
        pass
    else:
        PrintMsg('ymax not set')
        return

    step=settings['step']
    if not step==None:
        step=float(step)
        pass
    else:
        PrintMsg('step not set')
        return

    __keepfiles=settings['__keepfiles']
    
    #make FCM
    # get total valid points per cell
    FCMTotal=os.path.join(working,'{0}_{1}_FCM_TOTAL.asc'.format(int(xmin),int(ymin)))
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',lazfile,'-oasc','-o',FCMTotal,'-step',step,'-counter_32bit','-nodata',0 ]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',int((ymax-ymin)/step),'-ncols',int((xmax-xmin)/step)]
    subprocessargs=subprocessargs+['-keep_class',0,1,2,3,4,5,6,8,9,10,11,13,14,15,16,17,18,19,20]
    
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs) 

    # get total vegation points per cell
    FCMVeg=os.path.join(working,'{0}_{1}_FCM_VEG.asc'.format(int(xmin),int(ymin)))
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',lazfile,'-oasc','-o',FCMVeg,'-step',step,'-counter_32bit','-nodata',0 ]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',int((ymax-ymin)/step),'-ncols',int((xmax-xmin)/step)]
    subprocessargs=subprocessargs+['-keep_class',3,4,5]
    
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs) 

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
    anodata=azero*9999

    a.grid = np.where(a.grid>0,a.grid,azero)
    c=AsciiGrid()
    c.header=b.header
    c.grid=np.divide(b.grid,a.grid)
    c.grid = np.where(c.grid>0,c.grid,zeros)
    c.grid = np.where(anodata==-9999,anodata,c.grid)


    FCM=os.path.join(outpath,'{0}_{1}_FCM_{2}m.asc'.format(int(xmin),int(ymin),step))
    c.nodata_value=-9999
    c.savetofile(FCM)

    
if __name__ == "__main__":
    main(sys.argv[1:])     