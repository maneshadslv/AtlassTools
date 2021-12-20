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

@Gooey(program_name="Make ortho DEM", use_legacy_titles=True, default_size=(1000,900), required_cols=1, optional_cols=3,advance=True, navigation='SIDEBAR')
def param_parser():
    main_parser=GooeyParser(description="Tile Strip")
    subs = main_parser.add_subparsers(help='commands', dest='command')
    parser = subs.add_parser('swaths', help='Used when input files are swaths')
    parser.add_argument("input_folder", metavar="Input Directory", widget="DirChooser", help="Select input las/laz files", default='')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='500')
    parser.add_argument("filepattern",metavar="Input File Filter Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.las')
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    parser.add_argument("--metro", metavar="Metro", action= "store_true")
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
            'test': '2 <= int(user_input) <= 20',
            'message': 'Must be between 2 and 20'
        }})
    cores_group.add_argument("--tilingcores", metavar="Tiling", help="Number of cores to be used for tiling process", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 20',
                'message': 'Must be between 2 and 20'
            }})

    cores_group.add_argument("--cores", metavar="General", help="Number of Cores to be used for normal operations", type=int, default=4, gooey_options={
    'validator': {
        'test': '2 <= int(user_input) <= 20',
        'message': 'Must be between 2 and 20'
    }})
    parser.add_argument("buffer", metavar="Buffer", help="Buffer to generate the neighbourhood", default=200, type=int)
    parser.add_argument("-classify", metavar="Tile & Classify", help="Tick if Tiling and ground classification is required", action= "store_true")
    parser.add_argument("-geojsonfile", metavar="TileLayout file", widget="FileChooser", help="TL - if using tiled data", default='')

    tiled_parser = subs.add_parser('tiled', help='Used when input files are tiled')
    tiled_parser.add_argument("inputfolder",metavar="Input Directory", widget="DirChooser", help="Select the folder with the TILED las/laz files", default='')
    tiled_parser.add_argument("outputfolder",metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    tiled_parser.add_argument("inputgeojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="TL with all the tiles - uses to find neighboures", default='')
    tiled_parser.add_argument("outputgeojsonfile", metavar="Output TileLayout file", widget="FileChooser", help="TL with the selected tiles - few tiles", default='')
    tiled_parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    tiled_parser.add_argument("--metro", metavar="Metro", action= "store_true")
    gnd_group = tiled_parser.add_argument_group("Ground Settings", gooey_options={'show_border': True,'columns': 5})
    gnd_group.add_argument("--gndstep", metavar="Step", default=10, type=float)
    gnd_group.add_argument("--spike", metavar="Spike", default=0.5, type=float)
    gnd_group.add_argument("--downspike", metavar="Down Spike", default=1, type=float)
    gnd_group.add_argument("--bulge", metavar="Bulge", default=2.5, type=float)
    gnd_group.add_argument("--offset", metavar="Offset", default=1.0, type=float)
    noise_group = tiled_parser.add_argument_group("Noise Settings", gooey_options={'show_border': True,'columns': 2})
    noise_group.add_argument("--noisestep", metavar="Step",default=3.0, type=float)
    noise_group.add_argument("--isopoints", metavar="Isolated points", default=10, type=int)
    dem_group = tiled_parser.add_argument_group('DEM settings',gooey_options={'show_border': True,'columns': 3})
    dem_group.add_argument("--demstep", metavar="Step - DEM", default=1.0, type=float)
    cores_group = tiled_parser.add_argument_group("Cores Settings", gooey_options={'show_border': True,'columns': 3} )
    cores_group.add_argument("--noisecores", metavar="Noise", help="Number of Cores to be used for noise removal process (Should be a small number)", type=int, default=4, gooey_options={
        'validator': {
            'test': '2 <= int(user_input) <= 20',
            'message': 'Must be between 2 and 20'
        }})
    cores_group.add_argument("--tilingcores", metavar="Tiling", help="Number of cores to be used for tiling process", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 20',
                'message': 'Must be between 2 and 20'
            }})

    cores_group.add_argument("--cores", metavar="General", help="Number of Cores to be used for normal operations", type=int, default=4, gooey_options={
    'validator': {
        'test': '2 <= int(user_input) <= 20',
        'message': 'Must be between 2 and 20'
    }})
    tiled_parser.add_argument("buffer", metavar="Buffer", help="Buffer to generate the neighbourhood", default=200, type=int)
    tiled_parser.add_argument("-classify", metavar="Tile & Classify", help="Tick if Tiling and ground classification is required", action= "store_true")

    args = main_parser.parse_args()
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

    except Exception as e:
        log = "\n Noise removal failed for {0} \n Exception {1}".format(input,e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nNoise removal completed for {0}'.format(input)
            return (True, output, log)
        else:
            log ='\nNoise removal for {0} Failed'.format(input)
            return (False, None, log)

def ClassifyGround(input, output, tile, buffer, step, spike, downspike, bulge, offset, metro):
    log = ''
    if isinstance(input, str):
        input = [input]
 

    keep='-keep_xy {0} {1} {2} {3}'.format(str(tile.xmin-buffer), tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
    keep=keep.split()

    try:
        #lasground_new -i neighbourlasfiles -o <name>_gnd.laz -step 10 -spike 0.5 -down_spike 1.0 -bulge 2.5 -offset 0.1 -fine
        if metro:
            subprocessargs=['C:/LAStools/bin/lasground_new.exe','-i']+input+['-o',output,'-merged','-step',step, '-spike', spike, '-down_spike', downspike, '-bulge', bulge, '-offset', offset, '-fine', '-metro'] + keep
        else:
            subprocessargs=['C:/LAStools/bin/lasground_new.exe','-i']+input+['-o',output,'-merged','-step',step, '-spike', spike, '-down_spike', downspike, '-bulge', bulge, '-offset', offset, '-fine',] + keep
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
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

    if isinstance(gndfile,str):
        gndfile = [gndfile]

    log = ''

    try:    
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i']+gndfile+['-oasc','-o', output,'-nbits',32,'-kill',200,'-step',step,'-keep_class', 2] 
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]   # - requested by Eleanor to leave the buffer 
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except Exception as e:
        print('{0}: DEM output FAILED at Subprocess. {1}'.format(tilename,e))
        log = 'DEM creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(output):
            
            log = 'DEM output Success for: {0}.'.format(tilename)
            return(True, output, log)
        else:
            log = 'DEM creation Failed for: {0}.'.format(tilename)
            return(False, None, log)
   
def makeBufferedFiles(input, bufflasfile, x, y, filename,tilesize, buffer, filetype):

    if isinstance(input, str):
        input = [input]

    keep='-keep_xy {0} {1} {2} {3}'.format(str(x-buffer), y-buffer, x+tilesize+buffer, y+tilesize+buffer)
    keep=keep.split()
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + input + ['-olaz','-o', bufflasfile,'-merged'] + keep #'-rescale',0.001,0.001,0.001,
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)      
        
          

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making Buffered for {0} /nException {1}".format(bufflasfile, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufflasfile):
            log = "Making Buffered for {0} Success".format(bufflasfile)
            return (True,bufflasfile, log)

        else: 
            log = "Making Buffered for {0} Failed".format(bufflasfile)
            return (False,None, log)

def makeOthoDEMtiled(tile,tl_in,tl_out,buffer,args,inputfolder,workingdir,filetype,classify,metro):
    
    #Make buffered file
    bufferdir = AtlassGen.makedir(os.path.join(workingdir, '0_buffered')).replace('\\','/')
    tilesize = int(tile.xmax - tile.xmin)

    print(tile.name)
    neighbourlasfiles = []
    try:
        neighbours = tl_in.gettilesfrombounds(tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
    except:
        print("tile: {0} does not exist in geojson file".format(tile.name))

    print('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,tile.name))

    for neighbour in neighbours:
        neighbour = os.path.join(inputfolder,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

        if os.path.isfile(neighbour):
            neighbourlasfiles.append(neighbour)

    print("Only {0} found in input folder".format(len(neighbourlasfiles)))

    input = neighbourlasfiles
    print(neighbourlasfiles)
    bufferedlas = os.path.join(bufferdir, '{0}.{1}'.format(tile.name,filetype))

    makeBufferedFiles(input, bufferedlas, int(tile.xmin), int(tile.ymin), tile.name,tilesize, buffer, filetype)

    if classify:
            #remove noise
            ######################################################################################################################

            noiseremoveddir = AtlassGen.makedir(os.path.join(workingdir, '1_Noise_removed')).replace('\\','/')

            noiseremovedlas = os.path.join(noiseremoveddir, '{0}.{1}'.format(tile.name,filetype))

            NoiseRemove(bufferedlas, noiseremovedlas, args.noisestep, args.isopoints, filetype)

            #Classify ground
            #######################################################################################################################
            lasground = AtlassGen.makedir(os.path.join(workingdir, '2_Ground')).replace('\\','/')

            classifiedlas = os.path.join(lasground,'{0}.{1}'.format(tile.name, filetype)).replace('\\','/')
            ClassifyGround(noiseremovedlas, classifiedlas, tile, buffer, args.gndstep, args.spike, args.downspike, args.bulge, args.offset, metro)
            #ClassifyGround(input, output, tile, buffer, demstep, spike, downspike, bulge, offset)
        

    #Make DEM
    #######################################################################################################################

    print('\n\nMaking DEM : Started')

    demdir = AtlassGen.makedir(os.path.join(workingdir, '3_DEM')).replace('\\','/')

    if classify:
        input = classifiedlas
    else:
        input = neighbourlasfiles
    output = os.path.join(demdir,'{0}.asc'.format(tile.name)).replace('\\','/')

    MakeDEM(int(tile.xmin), int(tile.ymin), tile.name, input, output, buffer, float(args.demstep), tilesize)


    if os.path.exists(output):
        return(True,output,"DEM file created")
    
    else:
        return(False,None,"DEM file could not be created for {0}".format(tile.name))
           

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    freeze_support()

    args = param_parser()

    if args.command == 'swaths':
        tilesize=int(args.tile_size)
        filetype=args.file_type
        inputfolder=args.input_folder

        #geojsonfile = args.geojsonfile.replace('\\','/')
        files = []
        filepattern = args.filepattern.split(';')

        files=AtlassGen.FILELIST(filepattern, inputfolder)

        tilelayout = AtlassTileLayout()
        outlasdir=args.output_dir
        classify = args.classify
        metro = args.metro
        logpath = os.path.join(outlasdir,'log_MakeDem.txt').replace('\\','/')
        log = open(logpath, 'w')

        dt = strftime("%y%m%d_%H%M")
        workingdir = AtlassGen.makedir(os.path.join(outlasdir, '{0}_OrthoDem'.format(dt))).replace('\\','/')

 
        buffer = args.buffer
        print('\n\nWorking on files in  : {0}'.format(inputfolder))

        if classify:
            #Tiling
            ######################################################################################################################
            tileddir = AtlassGen.makedir(os.path.join(workingdir, '1_Tiled')).replace('\\','/')
            
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
            print('\n\nWorking on files in  : {0}'.format(inputfolder))
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

            noiseremoveddir = AtlassGen.makedir(os.path.join(workingdir, '2_Noise_removed')).replace('\\','/')
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
            lasground = AtlassGen.makedir(os.path.join(workingdir, '3_Ground')).replace('\\','/')

            MAKE_GROUND_TASKS = {}
            print('\n\nWorking on files in  : {0}'.format(inputfolder))
            print('\n\nAdding buffer')
            for result in NOISE_RESULTS:
                log.write(result.log)

                if result.success:
                    tilename = result.name

                    #Get Neigbouring las files
                    print('Creating tile neighbourhood for : {0}'.format(tilename))
                    tile = tilelayout.gettile(tilename)

                    input = os.path.join(noiseremoveddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')

                    output = os.path.join(lasground,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
                    MAKE_GROUND_TASKS[tilename] = AtlassTask(tilename, ClassifyGround, input, output, tile, buffer, args.gndstep, args.spike, args.downspike, args.bulge, args.offset, metro)
                    #ClassifyGround(input, output, tile, buffer, demstep, spike, downspike, bulge, offset)
            print('\n\nGround classification : Started')

            p=Pool(processes=int(args.cores))       
            MAKE_GROUND_RESULTS=p.map(AtlassTaskRunner.taskmanager,MAKE_GROUND_TASKS.values())
            files = glob.glob("{0}\\*.{1}".format(lasground, filetype))
            print('\nGround classification : Completed')

        else:
            geojsonfile = args.geojsonfile
            tilelayout = AtlassTileLayout()
            tilelayout.fromjson(geojsonfile)
            lasground = args.input_folder

        #Make DEM
        #######################################################################################################################
        print('\n\nWorking on files in  : {0}'.format(inputfolder))
        print('\n\nMaking DEM : Started')

        demdir = AtlassGen.makedir(os.path.join(workingdir, '4_DEM')).replace('\\','/')
        gndfiles = glob.glob("{0}\\*.{1}".format(lasground, filetype))
        print(len(gndfiles))
        MakeDEM_TASKS = {}
        for file in gndfiles:
            file = file.replace('\\', '/')
            path, filename, ext = AtlassGen.FILESPEC(file)
            tilename = filename
            x,y = tilename.split('_')
            tile = tilelayout.gettile(tilename)
            print(tile.name)
            neighbourlasfiles = []
            tilesize = int(tile.xmax - tile.xmin)

            try:
                neighbours = tile.getneighbours(buffer)
            except:
                print("tile: {0} does not exist in geojson file".format(tilename))

           # print('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,tilename))

            for neighbour in neighbours:
                neighbour = os.path.join(lasground,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

                if os.path.isfile(neighbour):
                    neighbourlasfiles.append(neighbour)

            input = neighbourlasfiles
            print(input)
            output = os.path.join(demdir,'{0}.asc'.format(tilename)).replace('\\','/')
            MakeDEM_TASKS[tilename] = AtlassTask(tilename, MakeDEM, int(x), int(y), tilename, input, output, buffer, float(args.demstep), tilesize)
            #MakeDEM(int(x), int(y), tilename, input, output, buffer, float(args.demstep), tilesize)

        p=Pool(processes=int(args.cores))       
        MAKEDEM_RESULTS=p.map(AtlassTaskRunner.taskmanager,MakeDEM_TASKS.values())

        
        print('\nMaking DEM : Completed')

        for result in MAKEDEM_RESULTS:
            log.write(result.log)     


    if args.command == 'tiled':
        print(args)


        inputfolder=args.inputfolder
        outlasdir=args.outputfolder
        classify = args.classify
        metro = args.metro
        inputgeojsonfile = args.inputgeojsonfile
        outputgeojsonfile = args.outputgeojsonfile

        filetype=args.file_type
        logpath = os.path.join(outlasdir,'log_MakeDem.txt').replace('\\','/')
        log = open(logpath, 'w')

        dt = strftime("%y%m%d_%H%M")
        workingdir = AtlassGen.makedir(os.path.join(outlasdir, '{0}_OrthoDem'.format(dt))).replace('\\','/')
        
        tl_in = AtlassTileLayout()
        tl_in.fromjson(inputgeojsonfile)

        tl_out = AtlassTileLayout()
        tl_out.fromjson(outputgeojsonfile)
        
        buffer = args.buffer
        print('\n\nWorking on files in  : {0}'.format(inputfolder))
        
        makeOrthoDEM_task = {}
        results = []


        for tile in tl_out:
            print(tile.name)
            makeOrthoDEM_task[tile.name] = AtlassTask(tile.name,makeOthoDEMtiled,tile,tl_in,tl_out,buffer,args,inputfolder,workingdir,filetype,classify,metro)

            #makeOthoDEMtiled(tile,tl_in,tl_out,buffer,args,inputfolder,workingdir,filetype,classify,metro)
        p=Pool(processes=int(args.cores))       
        results=p.map(AtlassTaskRunner.taskmanager,makeOrthoDEM_task.values())

    return

if __name__ == "__main__":
    main()         

