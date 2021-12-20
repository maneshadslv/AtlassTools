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
defaults['workingpath']=None #location to find laz and output results
defaults['missinglazpath']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/04_Final_transformed_and_XYZ_adjusted/Current_merged_500m_delivery_ready_dataset_missing_data/Z_adjusted" #location to process and store results


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
    #python \\10.10.10.142\projects\PythonScripts\MakeBrisbaneIpswich_merge_missing_data.py --tile=#name# --workingpath=W:\temp2\working\working


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

    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
        outlazpath=AtlassGen.makedir(os.path.join(workingpath,'Corrected_missing_data'))
        pass
    else:
        PrintMsg('workingpath not set')
        return

    missinglazpath=settings['missinglazpath']
    if not missinglazpath==None:
        missinglazpath=missinglazpath.replace('\\','/')
        pass
    else:
        PrintMsg('missinglazpath not set')
        return
    


    '''
    ---------------------------------------------------------------------------------------------------------------------------------------
    copy classifed points to all points tile
    ---------------------------------------------------------------------------------------------------------------------------------------
    '''


    #correct edited classification might be missing points
    infile=os.path.join(workingpath,'{0}.laz'.format(tile)).replace('\\','/')
    
    #has all points but auto classification
    sourcefile=os.path.join(missinglazpath,'{0}.laz'.format(tile)).replace('\\','/')

    #has all points with classification ported from the edited tile
    fixedfile=os.path.join(outlazpath,'{0}.laz'.format(tile)).replace('\\','/')

    if not os.path.isfile(infile):
        print('no in file')
        return

    if not os.path.isfile(sourcefile):
        print('no missing data file\n{}\ncopying original'.format(sourcefile))
        shutil.copy2(infile,outlazpath)
        return


    #merge orginal tiles with buffer +50 

    subprocessargs=['C:/LAStools/bin/lascopy.exe','-i',infile,'-i',sourcefile,'-olaz','-o',fixedfile]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    PrintMsg('classified corrected file created -- {0}'.format(os.path.isfile(fixedfile)),Heading=True)


if __name__ == "__main__":
    main(sys.argv[1:])            