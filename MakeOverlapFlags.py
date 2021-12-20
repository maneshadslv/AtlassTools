#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import math
import shutil
import subprocess
import os, glob
import numpy as np
import urllib
from gooey import Gooey, GooeyParser
import time
import datetime
from time import strftime
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Overlap Flags", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Overlap Flags")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("outputtype",metavar="Output File Type", help="las or laz\n", default='laz')
    main_parser.add_argument("tilelayoutfile", metavar="TileLayout file", widget="FileChooser", help="Select TileLayout file (.json)", default='')
    main_parser.add_argument("--attrval", metavar="Attribute Value", help="if Naming convention for files used, \nreplace x,y with %X% and %Y%.\nex: dem_%X%m_%Y%m.asc")
    main_parser.add_argument("--division", metavar="Division for X, Y", help="Reduce the X and Y values to the nearest 100,1000. \nleave blank for None\n", type=int)
    main_parser.add_argument("--cores", metavar="Cores", help="Number of cores to be used\n", type=int)
    
    return main_parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------



def index(input):
   
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        return(True, None, "Success")

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        return(False, None, "Error")


def clip(input, output, poly, filetype):

    if isinstance(input,str):
        input = [input]
    log=''
    try:
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' ] + input + [ '-merged', '-poly', poly, '-o', output, '-o{0}'.format(filetype)]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(output):
            log = "Clipping {0} output : {1}".format(str(input), str(output)) 
            return (True,output, log)

        else:
            log = "Clipping failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Clipping failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()

    inputfolder = args.inputfolder
    poly = args.poly.split(';')
    cores = args.cores
  
    outputpath=args.outputpath.replace('\\','/')
    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_OverlapFlags'.format(strftime("%y%m%d_%H%M"))))
    outputtype = args.outputtype
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')
    attrval = args.attrval
    division = args.division
    log = open(logpath, 'w')
    
    filepattern = args.filepattern.split(';')
    print("Reading {0} files \n".format(filepattern))
    files = AtlassGen.FILELIST(filepattern, inputfolder)
  

    ###########################################################################################################################
    #Index the files

 
    tasks={}
    for file in files:
        path, filename, ext = AtlassGen.FILESPEC(file)
        tilename = filename
        indexfile = os.path.join(path, '{0}.{1}'.format(filename, 'lax'))
        #print(indexfile)

        if not os.path.isfile(indexfile):
            tasks[tilename] = AtlassTask(tilename, index, file)
    if len(index_tasks) == 0:
        print('Skipping indexing as files are already indexed')
    else:
        print('Indexing files')
        p=Pool(processes=cores)  
        index_results=p.map(AtlassTaskRunner.taskmanager,index_tasks.values())

    ###########################################################################################################################
    #Clipping the filesto the AOI
    
    for aoi in poly:
        cliping_tasks = {}
        path, aoiname, ext = AtlassGen.FILESPEC(aoi)
        print('Clipping files to the AOI : {0}'.format(aoi))
        aoidir = AtlassGen.makedir(os.path.join(outputpath,aoiname))
        for file in files:

            path, filename, ext = AtlassGen.FILESPEC(file)
            tilename = filename

            input = file
            output = os.path.join(aoidir, '{0}.{1}'.format(filename, outputtype)).replace("\\", "/")
        
            cliping_tasks[tilename] = AtlassTask(tilename, clip, input, output, aoi, outputtype)


        p=Pool(processes=cores) 
        clipping_results=p.map(AtlassTaskRunner.taskmanager,cliping_tasks.values()) 

        ###########################################################################################################################


        for result in clipping_results:
            log.write(result.log)        


    print("Process Complete")
    return


if __name__ == "__main__":
    main()         

