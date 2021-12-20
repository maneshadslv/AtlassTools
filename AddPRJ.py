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

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Add PRJ files", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Add PRJ files")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filetype", metavar="extension of the files(asc, tif, txt etc.)", default='asc')
    main_parser.add_argument("epsg", metavar="EPSG value", help="EPSG value to use")
    main_parser.add_argument("cores", metavar="Cores", help="Number of cores to be used\n", type=int)
    return main_parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def copyprj(filename,proj,output):
    log = ''
    try:
        shutil.copy(proj,output)
        return(True,output,"Successful")

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        return(False, None, "Error")




#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()

    inputpath = args.inputfolder
    outputpath = args.outputpath
    cores = args.cores
    epsg = args.epsg
    filetype = args.filetype


    files = AtlassGen.FILELIST(['*.{0}'.format(filetype)], inputpath)

    scriptpath = os.path.dirname(os.path.realpath(__file__))
    print(scriptpath)

    prjfile2 = "{1}\\EPSG\\{0}.prj".format(epsg,scriptpath)
    prjfile = os.path.join(outputpath,'{0}.prj'.format(epsg)).replace('\\','/')

    tasks = {}
    results = []

    if os.path.isfile(prjfile2):
        shutil.copy(prjfile2,prjfile)
    else:
        print("PRJ file for {1} is not available in {0}".format(scriptpath,epsg))

    print(outputpath)

    for item in files:

        path, filename, ext = AtlassGen.FILESPEC(item)
        print(filename)
        outputprj = os.path.join(outputpath,'{0}.prj'.format(filename)).replace('\\','/')
        tasks[filename] = AtlassTask(filename, copyprj, filename, prjfile, outputprj)


    p=Pool(processes=cores) 
    results=p.map(AtlassTaskRunner.taskmanager, tasks.values())



    print("Process Complete")
    return


if __name__ == "__main__":
    main()         

