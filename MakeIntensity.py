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

@Gooey(program_name="Make Intensity Files", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=2)
def param_parser():
    main_parser=GooeyParser(description="Make Intensity files")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputfolder", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filetype",metavar="Input File Type", default='laz')
    main_parser.add_argument("geojsonfile", metavar="TileLayout file", widget="FileChooser", help="Select TileLayout file (.json)", default='')
    main_parser.add_argument("step", metavar="Step", default=0.5,type=float)
    main_parser.add_argument("intensity_min", metavar="Intensity min", type=float, default=100)
    main_parser.add_argument("intensity_max", metavar="Intensity max", type=float, default=2500)    
    main_parser.add_argument("cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    
    return main_parser.parse_args()
    


def makeIntensityGrids(input, output, intensityMin,intensityMax, xmin, ymin,step,tilesize):

    
    log = ''

    try:
        '''
        This function needs -ll <xmin> <ymin>
        '''
        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-step', step, '-fill' ,2 ,'-keep_first', '-intensity_average', '-otif', '-nbits', 8 ,'-set_min_max', intensityMin , intensityMax, '-o', output, '-ll', xmin , ymin, '-nrows', math.ceil((tilesize)/step), '-ncols', math.ceil((tilesize)/step)]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make grid {0}, Failed at Subprocess'.format(str(input))  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'Make Grid successful for {0}'.format(str(input))
            return (True,output, log)

        else:
            log = 'Could not make grid {0}'.format(str(input))           
            return (False,None, log)



   
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support() 
    args = param_parser()

    #create variables from gui
    inputfolder = args.inputfolder
    outputfolder = args.outputfolder
    #aoifiles = args.poly
    filetype = args.filetype
    geojsonfile = args.geojsonfile
    intensity_min = args.intensity_min
    intensity_max = args.intensity_max
    step=float(args.step)
    cores = args.cores

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(geojsonfile)
    
    outputfolder=args.outputfolder.replace('\\','/')
    outputfolder = AtlassGen.makedir(os.path.join(outputfolder, '{0}_MakeIntensityFiles'.format(strftime("%y%m%d_%H%M")))).replace('\\','/')
    
    print('Making Intensity Image')
    grid_tasks = {}
    grid_results = []
    for tile in tilelayout:
        
        tilename = tile.name
        xmin = tile.xmin
        ymin =  tile.ymin
        tilesize= int(tile.xmax - tile.xmin)

        #files 
        input = os.path.join(inputfolder, '{0}.{1}'.format(tilename,filetype)).replace("\\", "/") 
        output = os.path.join(outputfolder,'{0}.tif'.format(tilename)).replace("\\", "/")   

        grid_tasks[tilename] = AtlassTask(tilename, makeIntensityGrids, input, output, intensity_min,intensity_max, int(xmin), int(ymin),step, tilesize)

    p=Pool(processes=cores)      
    grid_results=p.map(AtlassTaskRunner.taskmanager,grid_tasks.values())   

    for result in grid_results:
        print(result.log)

    return()
    
if __name__ == "__main__":
    main(sys.argv[1:]) 

