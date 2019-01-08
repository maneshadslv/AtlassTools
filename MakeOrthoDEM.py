#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import shutil
import subprocess
import os
import random
import argparse
import math
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
from collections import defaultdict 
from collections import OrderedDict 
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=1, default_size=(1000,900))
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    parser.add_argument("input_folder", metavar="Input Directory", widget="DirChooser", help="Select input las/laz files", default='')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    parser.add_argument("filepattern",metavar="Input File Filter Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.las')
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    gnd_group = parser.add_argument_group("Ground Settings", gooey_options={'show_border': True,'columns': 5})
    gnd_group.add_argument("--gndstep", metavar="Step", default=10, type=float)
    gnd_group.add_argument("--spike", metavar="Spike", default=0.5, type=float)
    gnd_group.add_argument("--downspike", metavar="Down Spike", default=1, type=float)
    gnd_group.add_argument("--bulge", metavar="Bulge", default=2.5, type=float)
    gnd_group.add_argument("--offset", metavar="Offset", default=1.0, type=float)
    noise_group = parser.add_argument_group("Noise Settings", gooey_options={'show_border': True,'columns': 2})
    noise_group.add_argument("--noisestep", metavar="Step",default=3.0, type=float)
    noise_group.add_argument("--isopoints", metavar="Isolated points", default=10, type=int)
    dem_group = parser.add_argument_group('DEM settings',gooey_options={'show_border': True,'columns': 3})
    dem_group.add_argument("--demstep", metavar="Step - DEM", default=1.0, type=float)
    cores_group = parser.add_argument_group("Cores Settings", gooey_options={'show_border': True,'columns': 3} )
    cores_group.add_argument("--noisecores", metavar="Noise", help="Number of Cores to be used for noise removal process (Should be a small number)", type=int, default=4, gooey_options={
        'validator': {
            'test': '2 <= int(user_input) <= 14',
            'message': 'Must be between 2 and 14'
        }})
    cores_group.add_argument("--tilingcores", metavar="Tiling", help="Number of cores to be used for tiling process", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 14',
                'message': 'Must be between 2 and 14'
            }})

    cores_group.add_argument("--cores", metavar="General", help="Number of Cores to be used for normal operations", type=int, default=4, gooey_options={
    'validator': {
        'test': '2 <= int(user_input) <= 14',
        'message': 'Must be between 2 and 14'
    }})
    parser.add_argument("buffer", metavar="Buffer", help="Buffer to generate the neighbourhood", default=200, type=int)


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
        outputfiles = glob.glob(outputpath+"/*."+filetype)
        log = '\nTiling completed for {0}, generated {1}\n{2}'.format(input, len(outputfiles), list(outputfiles))
        return (True, outputfiles, log)

def MergeTiles(input, output, filetype):    
    log = ''

    if isinstance(input, str):
        input = [input]
    print(list(input))

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+input+['-o{0}'.format(filetype),'-o',output,'-merged'] 
        subprocessargs=list(map(str,subprocessargs))
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
            log = '\nMerging completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nMerging {0} Failed'.format(output)
            return (False, None, log)

def NoiseRemove(input, output, noisestep, isopoints, filetype):
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/lasnoise.exe','-i',input,'-o{0}'.format(filetype),'-o',output,'-step',noisestep, '-isolated', isopoints] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except:
        log = "\n Noise removal failed for {0} \n Exception {1}".format(input, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nNoise removal completed for {0}'.format(input)
            return (True, output, log)
        else:
            log ='\nNoise removal for {0} Failed'.format(input)
            return (False, None, log)

def ClassifyGround(input, output, tile, buffer, step, spike, downspike, bulge, offset):
    log = ''
 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(tile.xmin-buffer), tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
    keep=keep.split()

    try:
        #lasground_new -i neighbourlasfiles -o <name>_gnd.laz -step 10 -spike 0.5 -down_spike 1.0 -bulge 2.5 -offset 0.1 -fine
        subprocessargs=['C:/LAStools/bin/lasground_new.exe','-i']+input+['-o',output,'-merged','-step',step, '-spike', spike, '-down_spike', downspike, '-bulge', bulge, '-offset', offset, '-fine'] + keep
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "\nClassifying ground failed for {0} \n at Exception {1}".format(output, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nClassifying ground completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nClassifying ground  for {0} Failed'.format(output)
            print(log)
            return (False, None, log)

def MakeDEM(x, y, tilename, gndfile, output, buffer, step,tilesize):

    log = ''

    try:        
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o', output,'-nbits',32,'-kill',200,'-step',step,'-keep_class', 2] 
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]    
        #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}: DEM output FAILED at Subprocess.'.format(tilename))
        log = 'DEM creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(output):
            
            log = 'DEM output Success for: {0}.'.format(tilename)
            return(True, output, log)
        else:
            log = 'DEM creation Failed for: {0}.'.format(tilename)
            return(False, None, log)

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    freeze_support()

    args = param_parser()

    tilesize=int(args.tile_size)
    filetype=args.file_type
    inputfolder=args.input_folder
    #geojsonfile = args.geojsonfile.replace('\\','/')
    files = []
    filepattern = args.filepattern.split(';')

    if len(filepattern) >=2:
        print('\n\nNumber of patterns found : {0}'.format(len(filepattern)))
    for pattern in filepattern:
        pattern = pattern.strip()
        print ('\n\n*********************************************************************************************\nSelecting files with pattern {0}'.format(pattern))
        filelist = glob.glob(inputfolder+"\\"+pattern)
        for file in filelist:
            files.append(file)
    print('Number of Files founds : {0} '.format(len(files)))

    tilelayout = AtlassTileLayout()
    outlasdir=args.output_dir

    logpath = os.path.join(outlasdir,'log_MakeDem.txt').replace('\\','/')
    log = open(logpath, 'w')

    dt = strftime("%y%m%d_%H%M")
    workingdir = AtlassGen.makedir(os.path.join(outlasdir, '{0}_OrthoDem'.format(dt))).replace('\\','/')
    tileddir = AtlassGen.makedir(os.path.join(workingdir, '1_Tiled')).replace('\\','/')
    noiseremoveddir = AtlassGen.makedir(os.path.join(workingdir, '2_Noise_removed')).replace('\\','/')
    lasground = AtlassGen.makedir(os.path.join(workingdir, '3_Ground')).replace('\\','/')
    demdir = AtlassGen.makedir(os.path.join(workingdir, '4_DEM')).replace('\\','/')

    buffer = args.buffer

    print('\n\nTiling : Started')
    TILE_TASKS={}
    for file in files:
    
        path, filename, ext = AtlassGen.FILESPEC(file)

        #files
        input = file
        outputpath=AtlassGen.makedir(os.path.join(tileddir,filename)).replace('\\','/')
        TILE_TASKS[filename] = AtlassTask(filename,TileStrip,input,outputpath,tilesize,filetype)

    p=Pool(processes=int(args.tilingcores))      
    TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())


    #Merge tiles with the same tile name
    ######################################################################################################################
    MERGE_TASKS={}
    resultsdic=defaultdict(list)

    MERGE_TASKS={}


    for result in TILE_RESULTS:
        log.write(result.log)  
        if result.success:
            for file in result.result:
                path,filename,ext = AtlassGen.FILESPEC(file)
                resultsdic[filename].append(file)

    
    for key, value in list(resultsdic.items()): 
        input = resultsdic[key]
        output = os.path.join(tileddir, '{0}.{1}'.format(key,filetype))
        MERGE_TASKS[key]= AtlassTask(key, MergeTiles, input, output, filetype)
    
    MERGE_RESULTS=p.map(AtlassTaskRunner.taskmanager,MERGE_TASKS.values())
    print('\nTiling : Completed')
    #Making tilelayout file
    ######################################################################################################################
    print("\n\nMaking tilelayout file : Started \n")

    jsonfile = os.path.join(tileddir,'TileLayout.json')

    lasfiles = glob.glob(tileddir+"/*."+filetype)

    for file in lasfiles:
        print(file)
        path,filename,ext = AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilelayout.addtile(name=filename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)
         
    geojsonfile = tilelayout.createGeojsonFile(jsonfile)

    print("\nMaking tilelayout file : Completed\n")

    #remove noise
    ######################################################################################################################

    NOISE_TASK={}

    print('\n\nRemoving Noise : Started')
    for result in MERGE_RESULTS:
        log.write(result.log)  
        if result.success:
            tilename = result.name
            input = result.result
            output = os.path.join(noiseremoveddir, '{0}.{1}'.format(tilename,filetype))
            NOISE_TASK[tilename] = AtlassTask(tilename, NoiseRemove, input, output, args.noisestep, args.isopoints, filetype)

    p=Pool(processes=int(args.noisecores))       
    NOISE_RESULTS=p.map(AtlassTaskRunner.taskmanager,NOISE_TASK.values())
    print('\nRemoving Noise : Completed')

    #Classify ground
    #######################################################################################################################

    MAKE_GROUND_TASKS = {}

    print('\n\nAdding buffer')
    for result in NOISE_RESULTS:
        log.write(result.log)

        if result.success:
            tilename = result.name

            #Get Neigbouring las files
            print('Creating tile neighbourhood for : {0}'.format(tilename))
            tile = tilelayout.gettile(tilename)
            neighbourlasfiles = []

            try:
                neighbours = tile.getneighbours(buffer)
            except:
                print("tile: {0} does not exist in geojson file".format(tilename))

            #print('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,tilename))

            for neighbour in neighbours:
                neighbour = os.path.join(noiseremoveddir,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

                if os.path.isfile(neighbour):
                    neighbourlasfiles.append(neighbour)

            input = neighbourlasfiles
            output = os.path.join(lasground,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            MAKE_GROUND_TASKS[tilename] = AtlassTask(tilename, ClassifyGround, input, output, tile, buffer, args.gndstep, args.spike, args.downspike, args.bulge, args.offset)
            #ClassifyGround(input, output, tile, buffer, demstep, spike, downspike, bulge, offset)
    print('\n\nGround classification : Started')

    p=Pool(processes=int(args.cores))       
    MAKE_GROUND_RESULTS=p.map(AtlassTaskRunner.taskmanager,MAKE_GROUND_TASKS.values())

    print('\nGround classification : Completed')

    #Make DEM
    #######################################################################################################################
    print('\n\nMaking DEM : Started')

    MakeDEM_TASKS = {}
    for result in MAKE_GROUND_RESULTS:
        log.write(result.log)     
        print(result.name)
        if result.success:
            tilename = result.name
            x,y = tilename.split('_')
            input = os.path.join(lasground,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            output = os.path.join(demdir,'{0}.asc'.format(tilename)).replace('\\','/')
            MakeDEM_TASKS[tilename] = AtlassTask(tilename, MakeDEM, int(x), int(y), tilename, input, output, buffer, float(args.demstep), tilesize)
            #MakeDEM(int(x), int(y), tilename, input, output, buffer, args.demstep, tilesize)
    Pool(processes=int(args.cores))       
    MAKEDEM_RESULTS=p.map(AtlassTaskRunner.taskmanager,MakeDEM_TASKS.values())

    
    print('\nMaking DEM : Completed')

    for result in MAKEDEM_RESULTS:
        log.write(result.log)     

    return

if __name__ == "__main__":
    main()         

