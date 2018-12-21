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
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]))
from Atlass_beta1 import *

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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=1, default_size=(800, 500))
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    parser.add_argument("input_folder", metavar="Files", widget="DirChooser", help="Select input las/laz files", default='D:\\Python\\Gui\\input')
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="D:\\Python\\Gui\\output")
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 14',
                'message': 'Must be between 2 and 14'
            }})
    parser.add_argument("output_file", metavar="Output File Name", help="Provide name for outputfile", default="TileLayout.json")
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    args = parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


def TileStrip(input, outputpath, tilesize,filetype):    
    log = ''

    try:

        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i',input] 
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 


        subprocessargs=['C:/LAStools/bin/lastile.exe','-i',input,'-o{0}'.format(filetype),'-odir',outputpath,'-tile_size',tilesize] 
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\n TileStrip {0} \n Exception {1}".format(input, e)
        return(False,None, log)
    
    finally:
        outputfiles = glob.glob(outputpath+"\\*."+filetype)
        print('\nTiling completed for {0}, generated {1}\n{2}'.format(input, len(outputfiles), list(outputfiles)))
        log = '\nTiling completed for {0}, generated {1}\n{2}'.format(input, len(outputfiles), list(outputfiles))
        return (True, outputfiles, log)

        

    
def MergeTiles(input, output, filetype):    
    log = ''

    if isinstance(input, str):
        input = [input]
    print(list(input))

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+input+['-o{0}'.format(filetype),'-o',output,'-merged'] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except:
        log = "\n Merging {0} \n Exception {1}".format(output, e)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            for infile in input:
                os.remove(infile)
            log = '/Merging completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='/Merging {} Failed'.format(output)
            return (False, None, log)

  
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()

    tilesize=int(args.tile_size)
    filetype=args.file_type
    inputfolder=args.input_folder
    
    files = []
    files = glob.glob(inputfolder+"\\*."+filetype)
    cores=int(args.cores)
    outlasdir=args.output_dir



    print('Tiling started')
    TILE_TASKS={}
    for file in files:
    
        path, filename, ext = AtlassGen.FILESPEC(file)
        x,y=filename.split('_')  

        #files
        input = file
        outputpath=AtlassGen.makedir(os.path.join(outlasdir,filename))
        TILE_TASKS[filename] = AtlassTask(filename,TileStrip,input,outputpath,tilesize,filetype)

    p=Pool(processes=cores)      
    TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())
    resultsdic=defaultdict(list)

    #merge tiles with the same tile name
    MERGE_TASKS={}

    print('Merging started')
    for result in TILE_RESULTS:
        print(result.name, result.log)
        if result.success:
            for resultfile in result.result:
                resultsdic[result.name].append(resultfile)
    
    for key, value in list(resultsdic.items()): 
        print(key, value)
        input = resultsdic[key]
        output = os.path.join(outlasdir, '{0}.{1}'.format(key,filetype))
        MERGE_TASKS[key]= AtlassTask(key, MergeTiles, input, output, filetype)
    
    MERGE_RESULTS=p.map(AtlassTaskRunner.taskmanager,MERGE_TASKS.values())
    
 
    print("Making initial geojson file from dictionary \n")
    #make a tile layout index
    for result in MERGE_RESULTS:

        print(result.result, result.log)


    return

if __name__ == "__main__":
    main()         

