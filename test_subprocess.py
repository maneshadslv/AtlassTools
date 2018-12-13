

#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import math
import shutil
import subprocess
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
import time
import datetime
from time import strftime
from multiprocessing import Pool,freeze_support
from Atlass_beta1 import *


#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------
@Gooey(program_name="Make TMR products", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Make TMR products")
    main_parser.add_argument("inputpath", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="D:\\Python\\Gui\\input")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="D:\\Python\\Gui\\input")
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')

    
    return main_parser.parse_args()

def adjust(input, output, dx, dy, dz, epsg, filetype):
    #las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las
    log=''
 
    print('\nAdjusting : {0}'.format(input))
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i' , input ,'-o{0}'.format(filetype), '-translate_xyz', dx, dy, dz, '-epsg', epsg ,'-set_version', 1.2,  '-o', output]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        log=log +'\n'+p.stderr
        log=log +'Sucess: {0}\n'.format(time.ctime(time.time()))

        if os.path.isfile(output):

            log = "Adjusting {0} output : {1}".format(str(input), str(output))
            return (True,output, log)

        else:
            log = "Could not adjust : {0}".format(str(input))
            return (False,None,log)
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except:
        log = "Could not adjust {0}. Failed at Subprocess".format(str(input))
        return (False,None,log)


def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()
    filetype=args.filetype
    dx = 0.001
    dy = 0.002
    dz = -0.002
    epsg = 50
    areaname = 'M36464'

    outputpath=args.outputpath.replace('\\','/')
    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_{1}'.format(areaname,strftime("%y%m%d_%H%M"))))
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')
    print("Reading {0} files \n".format(filetype))
    files = []
    files = glob.glob(args.inputpath+"\\*."+filetype)
    print("{0} files found \n".format(len(files)))
    adjdir = AtlassGen.makedir(os.path.join(outputpath, 'Adjusted')).replace('\\','/')

    adj_tasks = {}
    for file in files:

        path, filename, ext = AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        #finalnames[filename]={}
        #finalnames[filename]['CLIPPED_LAS']='{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.las'.format()
        #finalnames[filename]['ESRI_GRID']='{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.las'.format()
        
        output = os.path.join(adjdir, '{0}.{1}'.format(filename, ext)).replace("\\", "/")
         
        adj_tasks[filename] = AtlassTask(filename, adjust, file, output, dx, dy, dz, epsg, filetype)



    p=Pool(processes=4)      
    adjust_results=p.map(AtlassTaskRunner.taskmanager,adj_tasks.values())



    for result in adjust_results:
        log.write(result.log)


if __name__ == "__main__":
    main()         
