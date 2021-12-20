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
defaults['outfile']=None #file to save
defaults['workingpath']=None #place to work
defaults['tilelayout']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/05_Product_generation/1km_delivery_tilelayout.json" #tilelayout to read
defaults['lazpath']="W:/processing/BR02692_Axedale/GDA2020_MGA_Z55_Axedale_xyz Adjusted_500m_tiles_210118" #where is the tiled data
defaults['xmin']=None
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None
defaults['buffer']=0 #optional add a buffer to the bounding box
extn='laz'
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

def getmostrecent(checkfolders,pattern):

    '''
    Searches through folders and creates a list of files patching a search pattern.
    File names are addded to a dictionary and tested for the most recent instance of each file.
    '''

    #dict to store name, size and date modified 
    #once processed will contain path to most recent
    filedict={}
    for folder in checkfolders:
        #make a list of files that match pattern

        files = glob.glob(os.path.join(folder,pattern))
        for filename in files:
            path,name=os.path.split(filename)
            mtime = os.path.getmtime(filename)
            if name in filedict.keys():
                #file already found
                filedict[name]['files'].append({'file':filename,'datemodified':mtime})
            else:
                #addfile
                filedict[name]={}
                filedict[name]['files']=[]
                filedict[name]['current']=''           
                filedict[name]['datemodified']=''   
                filedict[name]['files']=[{'file':filename,'datemodified':mtime}]

    for name,files in filedict.items():
        mostrectime=None
        for filerecord in files['files']:
            if mostrectime==None:
                mostrectime=filerecord['datemodified']
                mostrecfile=filerecord['file']
            else:
                if filerecord['datemodified']>mostrectime:
                    mostrectime=filerecord['datemodified']
                    mostrecfile=filerecord['file']

        return mostrecfile

def copyneighbourtiles(xmin,ymin,xmax,ymax,buffer,tilelayout,locations,outputfolder,prefix='',extn='laz'):
    # Get overlapping tiles in buffer
    PrintMsg(Message="Getting Neighbours",Heading=True)
    neighbours=tilelayout.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    PrintMsg('{0} Neighbours detected'.format(len(neighbours)))
    PrintMsg('Copying to workspace')

    # Copy to workspace
    for neighbour in neighbours:
        source =  getmostrecent(locations,'{0}{1}.{2}'.format(prefix,neighbour,extn))
        if source==None: 
            #no file found
            return
        source=source.replace('\\','/')
        dest =  outputfolder
        
        shutil.copy2(source,dest)
        if os.path.isfile(os.path.join(dest,'{0}{1}.{2}'.format(prefix,neighbour,extn))):
            PrintMsg('{0} copied.'.format(source))
        else:
            PrintMsg('{0} file not copied.'.format(source))
    return

def FILESPEC(filename):
    # splits file into components
    path,name=os.path.split(filename)
    name,ext=name.split(".")
    
    return path, name, ext


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------

    #globals
    #tilelayout="X:/BR02692_Axedale_Moe_DELWP/Axedale/04_Final_transformed_and_XYZ_adjusted/GDA2020_MGA_Z55_Axedale_xyz Adjusted_500m_tiles_210118/TileLayout_14583.json"
    #lazpath="X:/BR02692_Axedale_Moe_DELWP/Axedale/04_Final_transformed_and_XYZ_adjusted/GDA2020_MGA_Z55_Axedale_xyz Adjusted_500m_tiles_210118"
    #outpath=W:/processing/BR02692_Axedale/test
    #workingpath=W:\processing\BR02692_Axedale\test

    #python \\10.10.10.142\projects\PythonScripts\Clip_LAZ_to_XY.py --outfile=#outpath#\#name#.laz --workingpath=#workingpath#\#name# --tilelayout=#tilelayout# --lazpath=#lazpath# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --buffer=0


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
    outfile=settings['outfile']
    if not outfile==None:
        outfile=outfile.replace('\\','/')
        path,name,ext=FILESPEC(outfile)
        path=AtlassGen.makedir(path)
        pass
    else:
        PrintMsg('outfile not set')
        return

    tilelayout=settings['tilelayout']
    if not tilelayout==None:
        tilelayout=tilelayout.replace('\\','/')
        tilelayout_tl = AtlassTileLayout()
        tilelayout_tl.fromjson(tilelayout)
    else:
        PrintMsg('tilelayout not set')
        return

    lazpath=settings['lazpath']
    if not lazpath==None:
        pass
    else:
        PrintMsg('lazpath not set')
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

    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
    else:
        PrintMsg('workingpath not set')
        return

    __keepfiles=settings['__keepfiles']




    '''
    ----------------------------------------------------------------------------------------------
    preparation
    ----------------------------------------------------------------------------------------------
    copy tiles within buffer
    A. raw data tiled z adjusted tiles data
    B. most recent classified file for each input tile.

    prep A. by merging and classifying all points to class 0 within buffer of the tile extent.
    prep B. by merging within 2xbuffer of the tile extent.

    copy classification
    lascopy -i source.laz -i target.laz -classification -o result.laz
    check for class code 0
    ----------------------------------------------------------------------------------------------
    '''
    
    '''
    ---------------------------------------------------------------------------------------------------------------------------------------
    original tiles
    ---------------------------------------------------------------------------------------------------------------------------------------
    '''
    #temp workspace for original tiles

    copyneighbourtiles(xmin,ymin,xmax,ymax,buffer,tilelayout_tl,[lazpath],workingpath,prefix='',extn=extn)
    #add files to cleanup
    cleanupfolders.append(workingpath)

    

    #merge classified tiles with buffer 
    
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.{1}'.format(workingpath,extn),'-merged','-o{0}'.format(ext),'-o',outfile]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    print(subprocessargs)
    subprocessargs=map(str,subprocessargs) 
    
    subprocess.call(subprocessargs)  

    PrintMsg('outfile created -- {0}'.format(os.path.isfile(outfile)),Heading=True)


    #---------------------------------------------------------------------------------------


    # clean up workspace
    
    PrintMsg('Cleanup',Heading=True)
    if __keepfiles==None:
        for folder in cleanupfolders:
            if os.path.isdir(folder):
                cleanupfiles=AtlassGen.FILELIST('*.*',folder)
                for file in cleanupfiles:
                    if os.path.isfile(file):
                        os.remove(file)
                        PrintMsg('file: {0} removed.'.format(file))
                        pass
                    else:
                        PrintMsg('file: {0} not found.'.format(file))
                
                shutil.rmtree(folder, ignore_errors=True)
                pass
    

if __name__ == "__main__":
    main(sys.argv[1:])            