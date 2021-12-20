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

@Gooey(program_name="TMR change GE and GeRef", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3,navigation='TABBED')
def param_parser():
    main_parser=GooeyParser(description="TMR change GE and GeRef")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("vlrindex", metavar="VLR index number", type=int, help="Starts from 0, so if you want vlr 4 removed you need to enter 3")
    main_parser.add_argument("globalencoding", metavar="Global encoding to use", type=int,default =1)
    main_parser.add_argument("outputtype",metavar="Output File Type", help="las or laz\n", default='laz')
    main_parser.add_argument("cores", metavar="Cores", help="Number of cores to be used\n", type=int)
    return main_parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------



def geotag(input,outputpath,outfiletype,globalencoding,vlrindex):
   
    log = ''
    try:

        path,filename,ext = AtlassGen.FILESPEC(input)

        subprocessargs=['C:/LAStools/bin/lasinfo.exe','-i', input, '-set_global_encoding', globalencoding]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input,'-odir',outputpath, '-o{0}'.format(outfiletype),'-remove_vlr',vlrindex]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        if os.path.isfile(input):
            return(True, input, "Success")

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


    inputfolder = args.inputfolder
    cores = args.cores

    outputpath=args.outputpath.replace('\\','/')
    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_Output'.format(strftime("%y%m%d_%H%M"))))
    outfiletype = args.outputtype
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')
    globalencoding = args.globalencoding
    vlrindex = args.vlrindex
    log = open(logpath, 'w')
    
    filepattern = args.filepattern.split(';')
    print("Reading {0} files \n".format(filepattern))
    files = AtlassGen.FILELIST(filepattern, inputfolder)

    print("Number of files found : {0}".format(len(files)))

    index_tasks={}

    for file in files:
        print(file)
        path, filename, ext = AtlassGen.FILESPEC(file)
        tilename = filename
        index_tasks[tilename] = AtlassTask(tilename, geotag, file,outputpath,outfiletype,globalencoding,vlrindex)


    print('Editing Header files')
    p=Pool(processes=cores)  
    index_results=p.map(AtlassTaskRunner.taskmanager,index_tasks.values())

    
    for result in index_results:
        log.write(result.log)        




    print("Process Complete")
    return


if __name__ == "__main__":
    main()         

