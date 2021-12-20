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
#Tool is designed to copy data to local drive, process products and prepare delivery and achive datasets for interpine


#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings


defaults={}
defaults['tile']=None
defaults['xmin']=None 
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None
defaults['RGB']=None

defaults['laspath']=None
defaults['extn']=None
defaults['tilelayout']=None
defaults['storagepath']=None
defaults['workingpath']=None
defaults['deliverypath']=None

defaults['__keepfiles']=None

defaults['buffer']=50

        
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
def cleanup(cleanupfolders,cleanupfiles):
    # clean up workspace
    for folder in cleanupfolders:
        files=AtlassGen.FILELIST('*.*',folder)
        for file in files:
            cleanupfiles.append(file)

    PrintMsg('Cleanup',Heading=True)
    for file in cleanupfiles:
        if os.path.isfile(file):
            os.remove(file)
            PrintMsg('file: {0} removed.'.format(file))
            pass
        else:
            PrintMsg('file: {0} not found.'.format(file))

    for folder in cleanupfolders:
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)    
            PrintMsg('folder: {0} removed.'.format(folder))
    return
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------
    
    #python Z:\PythonScripts\MakeHQ_Plantations.py --tile=#name# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --laspath=F:\Processing\BR01266_HQ_Plantations\Tranche01\laz --extn=laz --tilelayout="F:\Processing\BR01266_HQ_Plantations\Tranche01\laz\TileLayout.json" --workingpath=F:\Processing\BR01266_HQ_Plantations\Tranche01\delivery\working --deliverypath=F:\Processing\BR01266_HQ_Plantations\Tranche01\delivery\output


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

    buffer=float(settings['buffer'])


    laspath=settings['laspath']
    if not laspath==None:
        laspath=laspath.replace('\\','/')
    else: 
        PrintMsg('laspath not set')
        return

    extn=settings['extn']
    if not laspath==None:
        pass
    else: 
        PrintMsg('extn not set')
        return

    RGB=settings['RGB']
    if not RGB==None:
        RGB=RGB.replace('\\','/')
    else: 
        PrintMsg('RGB not set continuing...')
        

    tilelayout=settings['tilelayout']
    if not tilelayout==None:
        tilelayout=AtlassTileLayout()
        tilelayout.fromjson(settings['tilelayout'].replace('\\','/'))
    else: 
        PrintMsg('tilelayout not set')
        return    
    '''
    storagepath=settings['storagepath']
    if not storagepath==None:
        storagepath=AtlassGen.makedir(storagepath.replace('\\','/'))
    else: 
        PrintMsg('storagepath not set')
        return                 
    '''
    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
        workingpath=AtlassGen.makedir(os.path.join(workingpath,'{0}'.format(tile)))
        originaltiles=AtlassGen.makedir(os.path.join(workingpath,'Original_LAS_tiles'))
    else: 
        PrintMsg('workingpath not set')
        return     

    deliverypath=settings['deliverypath']
    if not deliverypath==None:
        deliverypath=AtlassGen.makedir(deliverypath.replace('\\','/'))
    else: 
        PrintMsg('deliverypath not set')
        return     

    __keepfiles=settings['__keepfiles']
    cleanupfiles=[]
    cleanupfolders=[]


    #set up workspace
    PrintMsg('Settin up workspace',Heading=True)

    cleanupfolders.append(workingpath)
    cleanupfolders.append(originaltiles)

    # Get overlapping tiles in buffer
    PrintMsg(Message="Getting Neighbours",Heading=True)
    neighbours=tilelayout.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    PrintMsg('{0} Neighbours detected'.format(len(neighbours)))
    PrintMsg('Copying to workspace')

    # Copy to workspace
    test=False
    for neighbour in neighbours:
        source =  os.path.join(laspath,'{0}.{1}'.format(neighbour,extn))
        dest =  originaltiles
        shutil.copy2(source,dest)
        if os.path.isfile(os.path.join(dest,'{0}.{1}'.format(neighbour,extn))):
            PrintMsg('{0}.{1} copied.'.format(neighbour,extn))
            cleanupfiles.append(os.path.join(dest,'{0}.{1}'.format(neighbour,extn)))   
            test=True    
        else:
            PrintMsg('{0}.{1} file not copied.'.format(neighbour,extn))

    if not test:
        cleanup(cleanupfolders,cleanupfiles)
        return

    # Create merged
    lasmerged=os.path.join( workingpath,'{0}.laz'.format(tile))
    cleanupfiles.append(lasmerged)
    PrintMsg(Message="Making buffered las file",Heading=True)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(originaltiles,extn),'-merged','-olaz','-o',lasmerged]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=subprocessargs+['-epsg',28356]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)     
    print('merged')

    # add RGB 
    if not RGB==None:
        lasmergedrgb=os.path.join( workingpath,'{0}_rgb.laz'.format(tile))
        cleanupfiles.append(lasmergedrgb)
        PrintMsg(Message="Making buffered las file",Heading=True)
        subprocessargs=['C:/LAStools/bin/lascolor.exe','-i',lasmerged,'-olaz','-o',lasmergedrgb]
        subprocessargs=subprocessargs+['-image',RGB]
        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)     
        print('rgb')
        if os.path.isfile(lasmergedrgb):
            lasmerged=lasmergedrgb

    lasnonground=os.path.join( workingpath,'{0}_above_ground.laz'.format(tile))
    cleanupfiles.append(lasnonground)

    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',lasmerged,'-merged','-olaz','-o',lasnonground,'-keep_class'] + [1,3,4,5,6,7,10,13,14,15,16,17,18,19,20]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=subprocessargs+['-epsg',28356]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)     
    print('epsg - non ground')
    lasground=os.path.join( workingpath,'{0}_ground.laz'.format(tile))
    cleanupfiles.append(lasground)

    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',lasmerged,'-merged','-olaz','-o',lasground,'-keep_class'] + [2,8]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=subprocessargs+['-epsg',28356]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    print('epsg - ground')
    
    lasgroundmkp=os.path.join( workingpath,'{0}_ground_mkp.laz'.format(tile))
    cleanupfiles.append(lasgroundmkp)

    subprocessargs=['C:/LAStools/bin/lasthin64.exe','-i',lasground,'-olaz','-o',lasgroundmkp,'-adaptive',0.1,20,'-classify_as', 8]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    print('mkp')

    final=os.path.join(deliverypath,'HQP_2019_C2_{0}.laz'.format(tile))
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',lasnonground,lasgroundmkp,'-merged','-olaz','-set_version',1.4,'-o',final]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=subprocessargs+['-reoffset',xmin,ymin,0]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    print('final')

    if os.path.isfile(final):
        PrintMsg('output file created')
        cleanup(cleanupfolders,cleanupfiles)


if __name__ == "__main__":
    main(sys.argv[1:])            