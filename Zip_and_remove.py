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

import zipfile

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

cleanupfolders=[]

defaults={}
defaults['filetozip']=None #file to zip and remove
defaults['moveto']=None #move final zip to location
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


def FILESPEC(filename):
    """
    FILESPEC(filename)
        returns (path, name, ext)

    example:
        FILESPEC('c:/temp/myfile.txt')
        returns ('c:/temp', 'myfile', 'txt')
    """
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
    #outpath=W:/processing/BR02692_Axedale/test

    #python \\10.10.10.142\projects\PythonScripts\Zip_and_remove.py --filetozip=#outpath#\#name#.las 
    '''
    alex wants.
    python \\10.10.10.142\projects\PythonScripts\Zip_and_remove.py --filetozip=#outpath#\#name#*.* -r
    '''


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
    filetozip=settings['filetozip']
    if not filetozip==None:
        filetozip=filetozip.replace('\\','/')
    else:
        PrintMsg('filetozip not set')
        return


    moveto=settings['moveto']
    if not moveto==None:
        moveto=moveto.replace('\\','/')
        AtlassGen.makedir(moveto)
    else:
        #PrintMsg('moveto not set')
        pass


    __keepfiles=settings['__keepfiles']


    #zip the file
    path,name,ext=FILESPEC(filetozip)
    zfile=filetozip.replace('.{0}'.format(ext),'.zip')
    zfile_z=zipfile.ZipFile(zfile, mode='w', compression=zipfile.ZIP_DEFLATED)
    zfile_z.write(filetozip,os.path.basename(filetozip))
    zfile_z.close()
    PrintMsg('file: {0} zipped'.format(filetozip),Heading=True)

    #remove file
    if __keepfiles==None and os.path.isfile(zfile):
        os.remove(filetozip)
        PrintMsg('file: {0} removed.'.format(filetozip))
        pass
    
    if not moveto==None:
        shutil.copy2(zfile,moveto)
        if os.path.isfile(os.path.join(moveto,os.path.basename(zfile))):
            os.remove(zfile)


    #---------------------------------------------------------------------------------------

    

if __name__ == "__main__":
    main(sys.argv[1:])            