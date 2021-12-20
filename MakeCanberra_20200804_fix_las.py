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
from os.path import basename
import numpy as np
import io
import datetime
import time
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

import zipfile

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

cleanupfolders=[]

defaults={}
defaults['fullpath']=None 
defaults['drive']=None 
defaults['las']=None 
defaults['working']='W:/act_working' 
defaults['folder']=None 
defaults['xmin']=None
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None
defaults['__keepfiles']=None

#masterVLR="//10.10.10.142/projects/PythonScripts/VLR_Headers/GDA2020/55/AHD/GDA2020_55_AHD.vlr"

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
    #load and run using 1km tilelayout in the one tool
    #python \\10.10.10.142\projects\PythonScripts\MakeCanberra_20200804_fix_las.py --fullpath=#fullpath# --drive=#drive# --las=#las# --folder=#folder# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax#



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

    fullpath=settings['fullpath']
    if not fullpath==None:
        fullpath=fullpath.replace('\\','/')
        pass
    else:
        PrintMsg('fullpath path not set')
        exit(1)

    las=settings['las']
    if not las==None:
        las=las.replace('\\','/')
        pass
    else:
        PrintMsg('las path not set')
        exit(1)

    drive=settings['drive']
    if not drive==None:
        drive=AtlassGen.makedir(drive.replace('\\','/'))
        pass
    else:
        PrintMsg('drive path not set')
        exit(1)
        
    folder=settings['folder']
    if not folder==None:
        folder=folder.replace('\\','/')
        pass
    else:
        PrintMsg('drive path not set')
        exit(1)

    working=settings['working']
    if not working==None:
        working=AtlassGen.makedir(working.replace('\\','/'))
        output=AtlassGen.makedir(os.path.join(working,'output').replace('\\','/'))
        pass
    else:
        PrintMsg('working path not set')
        exit(1)

    __keepfiles=settings['__keepfiles']


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


    '''
    ----------------------------------------------------------------------------------------------
    preparation
    ----------------------------------------------------------------------------------------------
    '''

    #copy zip to temp workspace
    zipin=shutil.copy2(fullpath,working)

    #extract zip
    zzz=zipfile.ZipFile(zipin, mode='r')
    zzz.extract(las,working)

    lasin=os.path.join(working,las)
    lasout=os.path.join(output,las)
    pngout=os.path.join(output,las.replace('.las','.png'))


    #subprocessargs=['C:/LAStools/bin/lasinfo.exe','-i',lasin, '-otxt']  
    #subprocessargs=map(str,subprocessargs) 
    #subprocess.call(subprocessargs)  


    #apply vlr
    #change to active directory
    os.chdir(working)

    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',lasin, '-load_vlrs', '-o',lasout,'-olas']  
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)

    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',lasout, '-opng','-o',pngout,'-intensity_average','-step',0.25,'-subcircle',0.1,'-fill',1,'-set_min_max', 50,2500,'-ll',xmin,ymin,'-nrows',4000,'-ncols',4000]  
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    #zip new copy of file
    zipout=lasout.replace('.las','.zip')
    zzz=zipfile.ZipFile(zipout, mode='w', compression=zipfile.ZIP_DEFLATED)
    zzz.write(lasout,basename(lasout))
    zzz.close()
    PrintMsg('zipped',Heading=True)

    productspath='//10.10.10.142/processed_data/BR02096_Canberra_and_ACT_Tender-ACT_Government/01_LiDAR/05_Product_generation/GDA_2020_Z55_Canberra_2020_Submission_200804'.replace('\\','/')

    #copy zip to server
    dest=AtlassGen.makedir(os.path.join(productspath,folder)).replace('\\','/')
    shutil.copy2(zipout,dest)
    shutil.copy2(pngout,dest)
    shutil.copy2(pngout.replace('.png','.pgw'),dest)
    PrintMsg('zip coppied',Heading=True)

    #copy file to drive
    shutil.copy2(lasout,drive)

    #cleanup
    os.remove(zipout)
    os.remove(zipin)
    os.remove(lasin)
    os.remove(lasout)
    os.remove(pngout)
    os.remove(pngout.replace('.png','.pgw'))
if __name__ == "__main__":
    main(sys.argv[1:])            