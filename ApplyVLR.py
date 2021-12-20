#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import shutil
import subprocess
import os
import random
import argparse
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
from collections import defaultdict 
from collections import OrderedDict 
from gooey import Gooey, GooeyParser
from geojson import Point, Feature, FeatureCollection, Polygon,dump
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile_original'.format(sys.path[0]).replace('\\','/'))
import shapefile_original
#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 29/03/2018 -Alex Rixon - Original development Alex Rixon
#

#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#This tool is used to tile data and run lastools ground clasification.

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
#-----------------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------
#Multithread Function definitions
#-----------------------------------------------------------------------------------------------------------------
# Function used to calculate result

@Gooey(program_name="Apply VLR", use_legacy_titles=True, required_cols=2, default_size=(950, 700),monospace_display=False)
def param_parser():
    vlr_apply_parser=GooeyParser(description="Apply VLR")
    vlr_apply_parser.add_argument("inputdir", metavar="Input Directory", widget="DirChooser", help="Directory with the inorrect header files", default='')
    vlr_apply_parser.add_argument("outdir", metavar="Output Directory", widget="DirChooser", help="Output location", default='')
    vlr_apply_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    vlr_apply_parser.add_argument("gda",metavar="Geocentric Datum", choices=['GDA94', 'GDA2020'], default='GDA94')
    vlr_apply_parser.add_argument("zone",metavar="Zone",choices=['47', '48','49','50','51','52','53','54','55','56','57'])
    vlr_apply_parser.add_argument("height",metavar="AHD or ELL", choices=['AHD', 'ELL'])
    vlr_apply_parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)
    args = vlr_apply_parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def ApplyVLR(lazfile,inputdir,vlrdir,filetype):
    os.chdir(inputdir)
    log = ''
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-odir',vlrdir,'-load_vlrs' ,'-o{0}'.format(filetype)] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

        log = 'Success'
        return(True,lazfile, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nFixing header failed at exception for :{0}".format(e)
        return(False,None, log)
    


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()


    inputdir = args.inputdir
    filetype = args.filetype
    outputdir = args.outdir
    cores = args.cores
    gda = args.gda
    zone = args.zone
    height = args.height

    if gda == 'GDA94':
        gda = 'GDA94'
    if gda == 'GDA2020':
        gda == 'GDA2020'

    if height == 'ELL':
        height = 'ellipsoidal'
    
    vlrfile = "\\\\10.10.10.142\\projects\\PythonScripts\\VLR_Headers\\{0}\\{1}\\{2}\\{0}_{1}_{2}.vlr".format(gda,zone,height)
    

    print('VLR file used : {0}'.format(vlrfile))
    if not os.path.isfile(vlrfile):
        print("Could not fine the VLR file for {0} {1} {2}".format(gda,zone,height))

    print(vlrfile)

    dt = strftime("%y%m%d_%H%M")

    outputdir = AtlassGen.makedir(os.path.join(outputdir,'Fixed_Header_{0}'.format(dt)).replace('\\','/'))
    #Copying file to projects folder.
    
    destinationfile = os.path.join(inputdir,'vlrs.vlr').replace('\\','/')

    #if not os.path.isfile(destinationfile):
    shutil.copyfile(vlrfile, destinationfile)


    listOfFiles = AtlassGen.FILELIST(['*.{0}'.format(filetype)], inputdir)
    TILE_TASKS = {}
    TILE_RESULTS=[]

    for ifile in listOfFiles:
 
        dirpath, filename,ext = AtlassGen.FILESPEC(ifile)
  
        print(filename)
        TILE_TASKS[filename] = AtlassTask(filename,ApplyVLR,ifile,inputdir,outputdir,filetype)

    p=Pool(processes=cores)      
    TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())

    for result in TILE_RESULTS:
        print(result.result, result.success)

    print("Process Complete")
    return

if __name__ == "__main__":
    main()         

