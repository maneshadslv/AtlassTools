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
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile
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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=1, default_size=(950, 700),monospace_display=False)
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    parser.add_argument("input_folder", metavar="Input Directory", widget="DirChooser", help="Select input las/laz files", default='')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.las')
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000','5000','10000'], default='500')
    parser.add_argument("datum", metavar="Datum",choices=['AMG84','AMG66','MGA94','MGA2020'], default='MGA94')
    parser.add_argument("zone", metavar="UTM Zone", choices=['50','51','52','53','54','55','56'])
    shift_group = parser.add_argument_group("Shift values", "* Keep blank if shifting is NOT required", gooey_options={'show_border': True,'columns': 3})
    shift_group.add_argument("--dx",  metavar="x shift", type=float, default=0.00)
    shift_group.add_argument("--dy",  metavar="y shift", type=float, default=0.00)
    shift_group.add_argument("--dz",  metavar="z shift", type=float, default=0.00)
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4)
    parser.add_argument("file_type",metavar="Output File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
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

def MakeTileLayout(files, tilesize, inputfolder, tldir, filetype):

    print("Total number of las files found : {0}\n".format(len(files)))
    tilelayout = AtlassTileLayout()
    jsonfile = os.path.join(tldir, 'TileLayout.json').replace('\\','/')
    prjfile = os.path.join(tldir, 'tile_layout.prj').replace('\\','/')
    shpfile = prjfile.replace('.prj','_shapefile').replace('\\','/')

    w = shapefile.Writer(shapefile.POLYGON)
    w.autoBalance = 1
    w.field('TILE_NAME','C','255')
    w.field('XMIN','N',12,3)
    w.field('YMIN','N',12,3)
    w.field('XMAX','N',12,3)
    w.field('YMAX','N',12,3)
    w.field('TILENUM','C','16')

    for file in files:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilelayout.addtile(name=filename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)
         
    jsonfile = tilelayout.createGeojsonFile(jsonfile)

    print("Making geojson file : Completed\n")


 
    print("Making prj file : Started\n")
    with open(prjfile,"w") as f:

        
        #write the header to the file.
        f.write('[TerraScan project]\n')
        f.write('Scanner=Airborne\n')
        f.write('Storage={0}1.2\n'.format(filetype))
        f.write('StoreTime=2\n')
        f.write('StoreColor=0\n')
        f.write('RequireLock=0\n')
        f.write('Description=Created using Compass\n')
        f.write('FirstPointId=1\n')
        f.write('Directory={0}\n'.format(inputfolder))
        f.write('PointClasses=\n')
        f.write('Trajectories=\n')
        f.write('BlockSize={0}\n'.format(str(tilesize)))
        f.write('BlockNaming=0\n')
        f.write('BlockPrefix=\n')   
        
        
        #make a prj fille

        for file in files:
            filepath,filename,extn=AtlassGen.FILESPEC(file)
            x,y=filename.split('_')
            boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
            f.write( '\nBlock {0}.{1}\n'.format(filename,extn))
            for i in boxcoords:
                f.write(  ' {0} {1}\n'.format(i[0],i[1]))

        f.close
        print("Making prj file : Completed\n")
        
    print("Making shp file : Started\n")

    for file in files:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
        w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
        w.record(TILE_NAME='{0}'.format(filename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='t{0}{1}'.format(int(boxcoords[0][0]/1000),int(boxcoords[0][1]/1000)))
    
    w.save(shpfile)           
    print("Making shp file : Completed\n")
  
def shiftlas(input, output, filetype, dx, dy, dz):

    log = ''

    try:
        #Las2las -i *.laz -olaz -odir xyz_adjusted -translate_xyz 1.50 2.80 0.00
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',input,'-o{0}'.format(filetype),'-o',output,'-translate_xyz', dx, dy, dz ] 
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


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()

    tilesize=int(args.tile_size)
    filetype=args.file_type
    inputfolder=args.input_folder
    datum = args.datum
    zone = args.zone
    dx = float(args.dx)
    dy = float(args.dy)
    dz = float(args.dz)
    shift = False
    
    files = []
    filepattern = args.filepattern.split(';')

    if len(filepattern) >=2:
        print('Number of patterns found : {0}'.format(len(filepattern)))
    for pattern in filepattern:
        pattern = pattern.strip()
        print ('Selecting files with pattern {0}'.format(pattern))
        filelist = glob.glob(inputfolder+"\\"+pattern)
        for file in filelist:
            files.append(file)
    print('Number of Files founds : {0} '.format(len(files)))

    cores=int(args.cores)
    outlasdir=args.output_dir

    
    if dx==0.0 and dy==0.0 and dz==0.0:
        shift = False
    
    else:
        shift = True
        xzy_string = ''
        if not dx==0:
            xzy_string = xzy_string + 'x'
        if not dy==0:
            xzy_string = xzy_string + 'y'
        if not dz==0:
            xzy_string = xzy_string + 'z'


    print('Shifting required : {0}'.format(shift))
    logw = 'Shift values used : \ndx={0} \ndy={1} \ndz={2}'.format(dx, dy, dz)
    print(logw)

    dt = strftime("%y%m%d_%H%M")
    maindir = AtlassGen.makedir(os.path.join(outlasdir, '{0}_{1}-{2}_{3}m_tiles'.format(dt, datum,zone,tilesize))).replace('\\','/')
    tldir = AtlassGen.makedir(os.path.join(maindir, 'tilelayout')).replace('\\','/')
    if shift:

        adjusteddir = AtlassGen.makedir(os.path.join(maindir, '{0}_adjusted_input'.format(xzy_string))).replace('\\','/')
        xyz_file = os.path.join(adjusteddir, 'xyz_adjustment.txt').replace('\\','/')
        f= open(xyz_file,"w+")
        f.write('dx={0} \ndy={1} \ndz={2}'.format(dx, dy, dz))
        f.close()
    
    workingdir =  maindir
  

    

    logpath = os.path.join(maindir,'log_TileStrip.txt').replace('\\','/')
    log = open(logpath, 'w')
    log.write(logw)



    TILE_TASKS={}
    SHIFT_TASKS={}
    folders = []
    for file in files:
    
        path, filename, ext = AtlassGen.FILESPEC(file)
        folders.append(filename)
        if shift:
            #files
            input = file
            output = os.path.join(adjusteddir, '{0}.{1}'.format(filename, filetype)).replace('\\','/')
            SHIFT_TASKS[filename]= AtlassTask(filename,shiftlas,input,output, filetype, dx, dy, dz)
        else:
            #files
            input = file
            outputpath=AtlassGen.makedir(os.path.join(workingdir,filename)).replace('\\','/')
            TILE_TASKS[filename] = AtlassTask(filename,TileStrip,input,outputpath,tilesize,filetype)

    if shift:
        print('\n\nShifting Started')
        p=Pool(processes=cores)      
        SHIFT_RESULTS=p.map(AtlassTaskRunner.taskmanager,SHIFT_TASKS.values()) 

        for result in SHIFT_RESULTS:
            if result.success:
                filename = result.name      
                #files
                input = result.result
                print(input)
                outputpath=AtlassGen.makedir(os.path.join(workingdir,filename)).replace('\\','/')
                TILE_TASKS[filename] = AtlassTask(filename,TileStrip,input,outputpath,tilesize,filetype)
        if len(SHIFT_TASKS) == 0:
            print('Unable to shift the las files.. Exiting Program...')
            exit()
        else:
            print('\n\nTiling started')
            p=Pool(processes=cores)      
            TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())
            resultsdic=defaultdict(list)

    else:
        print('\n\nTiling started')
        p=Pool(processes=cores)      
        TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())
        resultsdic=defaultdict(list)

    #merge tiles with the same tile name
    MERGE_TASKS={}

    print('\n\nMerging started')
    for result in TILE_RESULTS:
        log.write(result.log)  
        if result.success:
            for file in result.result:
                path,filename,ext = AtlassGen.FILESPEC(file)
                resultsdic[filename].append(file)


    for key, value in list(resultsdic.items()): 
        input = resultsdic[key]
        output = os.path.join(workingdir, '{0}.{1}'.format(key,filetype)).replace('\\','/')
        MERGE_TASKS[key]= AtlassTask(key, MergeTiles, input, output, filetype)
    
    MERGE_RESULTS=p.map(AtlassTaskRunner.taskmanager,MERGE_TASKS.values())
   
    #make a tile layout index
    for result in MERGE_RESULTS:
        log.write(result.log)  
    
    for folder in folders:

        rmfolder = (os.path.join(workingdir, folder).replace('\\','/'))
        if [f for f in os.listdir(rmfolder) if not f.startswith('.')] == []:
            os.rmdir(rmfolder)
        else: 
            print ('Files exist in {0} , Merging Not Successfule for {1}'.format(rmfolder, result.name))

    tiledlas = glob.glob(workingdir+'/*.{0}'.format(filetype))
    MakeTileLayout(tiledlas, tilesize, workingdir, tldir, filetype)

    return

if __name__ == "__main__":
    main()         

