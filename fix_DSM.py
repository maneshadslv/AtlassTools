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
defaults['dsmfile']=None
defaults['demfile']=None
defaults['outfile']=None


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
    
    #c:\python35-64\python \\10.10.10.100\projects\PythonScripts\MakeDPIPWE.py --tile=461000_7170000 --xmin=461000 --ymin=7170000 --xmax=462000 --ymax=7171000 --areaname=Bishopbourne --laspath=F:\Processing\Area01_Mary_GDA94MGA56\origtiles --tilelayout=F:\Processing\Area01_Mary_GDA94MGA56\origtiles\TileLayout.json --storagepath=W:\temp2\working\storage\NorthMidlands --workingpath=W:\temp2\working\working --deliverypath=W:\temp2\working\delivery\NorthMidlands --step=1.0 --extn=laz --buffer=250


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

    dsmfile=settings['dsmfile']
    if not dsmfile==None:
        dsmfile=dsmfile.replace('\\','/')
        pass
    else:
        PrintMsg('dsmfile not set')
        return

    demfile=settings['demfile']
    if not demfile==None:
        demfile=demfile.replace('\\','/')
        pass
    else:
        PrintMsg('demfile not set')
        return

    outfile=settings['outfile']
    if not outfile==None:
        outfile=outfile.replace('\\','/')
        pass
    else:
        PrintMsg('outfile not set')
        return

    a=AsciiGrid()
    b=AsciiGrid()   
    c=AsciiGrid()
    a.readfromfile(dsmfile)     
    b.readfromfile(demfile)     

    c.header=a.header

    ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
    zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
    nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

    # extract DSM void areas
    voids=ones*(a.grid==a.nodata_value)
    c.grid=np.where(voids==1,b.grid,a.grid)

    c.savetofile(outfile)

    
if __name__ == "__main__":
    main(sys.argv[1:])            