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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=2, default_size=(950, 700),monospace_display=False)
def param_parser():
    vlr_apply_parser=GooeyParser(description="Tile Strip")
    vlr_apply_parser.add_argument("inputdir", metavar="Input Directory", widget="DirChooser", help="Directory with the Correct Laz header files", default='')
    vlr_apply_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    vlr_apply_parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)
    args = vlr_apply_parser.parse_args()
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
        print('\nTiling completed for {0}, generated {1}'.format(input, len(outputfiles)))
        log = '\nTiling completed for {0}, generated {1}'.format(input, len(outputfiles))
        return (True, outputfiles, log)

 
def MergeTiles(input, output, filetype):    
    log = ''

    if isinstance(input, str):
        input = [input]
    

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+input+['-o{0}'.format(filetype),'-o',output,'-merged'] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\n Merging {0} \n Exception {1}".format(output, e)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            for infile in input:
                os.remove(infile)
            log = '\nMerging completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nMerging {} Failed'.format(output)
            return (False, None, log)


  
def shiftlas(input, output, filetype, dx, dy, dz, epsg):

    log = ''

    try:
        #Las2las -i *.laz -olaz -odir xyz_adjusted -translate_xyz 1.50 2.80 0.00
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',input, '-epsg',epsg,'-o{0}'.format(filetype),'-o',output,'-translate_xyz', dx, dy, dz ] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nShifting {0} \n Exception {1}".format(input, e)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nShifting completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nShifting {} Failed'.format(output)
            return (False, None, log)

def movefiles(input, output):

    try:
        shutil.move(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            log = "Moving file {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Moving file {0} Failed".format(input)
            return (False,output, log)

def MakeVLR(lazfile, outputdir):
    
  
    log = ''

    os.chdir(outputdir)
    dir_path = os.getcwd()

    vlr = os.path.join(outputdir,'vlrs.vlr')
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-save_vlrs', '-nil'] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

  
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nMaking VLR Failed at exception :{0}".format(e)
        return(False,None, log)

    finally:
        if os.path.isfile(vlr):
            log = '\nVLR created Successfully : {0}'.format(vlr)
            path, filename,ext = AtlassGen.FILESPEC(lazfile)
            vlrname = '{0}.vlr'.format(filename)
            newvlrfile = os.path.join(outputdir,vlrname)
            print('renaming vlr')
            os.rename(vlr,newvlrfile)
            if os.path.isfile(newvlrfile):
                os.remove(lazfile)
            return (True, newvlrfile, log)
        else:
            log ='\nVLR creation Failed'
            return (False, None, log)

def CorrectVLR(lazfile,inputdir,vlrdir,filetype):
    os.chdir(inputdir)
    log = ''
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-odir',vlrdir,'-load_vlrs' ,'-o{0}'.format(filetype)] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

        log = 'Success'
        return(True,lazfile, log)

    except subprocess.CalledProcessError as suberror:
     
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
    cores = args.cores
    
    listOfFiles = list()
    TILE_TASKS = {}
    TILE_RESULTS=[]

    for (dirpath, dirnames, filenames) in os.walk(inputdir):
        listOfFiles += [os.path.join(dirpath, file) for file in filenames]

    print(listOfFiles)

    for ifile in listOfFiles:
 
        dirpath, filename,ext = AtlassGen.FILESPEC(ifile)

     
        #newname = dirpath.replace('\\', '_')
        #newname = '{0}.{1}'.format(newname.replace('D:_VLR_Headers_', ''),filetype)
       
       # print(newname)
        
        
        if ext == filetype:
            lazfile = ifile
            print(lazfile, dirpath)
            #newlazfile = os.path.join(dirpath,newname)
            #os.rename(lazfile,newlazfile)

            TILE_TASKS[filename] = AtlassTask(filename,MakeVLR,lazfile, dirpath)

    p=Pool(processes=cores)      
    TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())

    for result in TILE_RESULTS:
        print(result)
    return

if __name__ == "__main__":
    main()         

