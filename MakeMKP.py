#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess 
from subprocess import PIPE, Popen
import os, glob
import numpy as np
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from gooey import Gooey, GooeyParser

#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 25/10/2018
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make MKP", use_legacy_titles=True, required_cols=1, default_size=(1000,700))
def param_parser():
    parser=GooeyParser(description="Make MKP")
    parser.add_argument("inputfolder", metavar="Las files Folder", widget="DirChooser", help="Select input files (.las/.laz)")
    parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.laz')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)")
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory")
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument("buffer", metavar="Buffer", help="Provide buffer", default=200, type=int)
    parser.add_argument("hz", metavar="hz", help="Provide hz", default=30, type=int)
    parser.add_argument("vt", metavar="vt", help="Provide vt", default=0.15, type=float) 
    parser.add_argument("--clipshape", metavar="Clip shape", help="Clip Shape", action='store_true')
    parser.add_argument("--aoifile", metavar="AOI shp file", widget="FileChooser", help="Select aoi shape file for clipping", default='')
    parser.add_argument("--cores", metavar="Cores", help="Number of Cores", default=4, type=int)
   
    return parser.parse_args()

def makeMKP(tile, lasfiles, outpath, workingdir, gndclasses,vt, hz, buffer, filetype):
    cleanup=[]
    outfile=os.path.join(outpath,'{0}.{1}'.format(tile.name, filetype)).replace('\\','/')
    tempfile=os.path.join(workingdir,'{0}_temp.{1}'.format(tile.name, filetype)).replace('\\','/')
    tempfile2=os.path.join(workingdir,'{0}_temp2.{1}'.format(tile.name, filetype)).replace('\\','/')
    cleanup.append(tempfile)
    cleanup.append(tempfile2)

    log = ''
    print(lasfiles)

    if isinstance(lasfiles, str):
        lasfiles = [lasfiles]
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+lasfiles+['-merged','-o{0}'.format(filetype),'-o',tempfile,'-keep_class'] + gndclasses
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]    #adds buffer
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    
        subprocessargs=['C:/LAStools/bin/lasthin.exe','-i',tempfile,'-o{0}'.format(filetype),'-o',tempfile2,'-adaptive',vt,hz,'-set_classification',8]
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,'-o{0}'.format(filetype),'-o',outfile]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin,tile.ymin,tile.xmax,tile.ymax]    #removes buffer
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Making MKP Failed at exception for : {0}'.format(tile.name)
        return (False, None, log)
    finally:
        if os.path.isfile(outfile):
            log ='Making MKPsuccess for : {0}'.format(tile.name)
            for file in cleanup:
                try:
                    if os.path.isfile(file):
                        os.remove(file)   
                except:
                    print('cleanup FAILED.') 
                print('Cleaning Process complete')
            return (True, outfile, log)
        else:
            log ='Making MKP Failed for {0}'.format(tile.name)
            return (False, None, log)
    

def index(input):
   
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        return(True, input, "Success")

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
#c:\python35-64\python.exe \\10.10.10.100\temp\Alex\Python\scripts\MakeMKP.py --lasfile=#file# --outpath=F:\Newlands\Z_adjusted\Wollombi\edited\tiles_1000m\mkp --hz=30 --vt=0.15 --tileshape="F:\Newlands\Z_adjusted\Wollombi\edited\tiles_1000m\tile_layout_shapefile.shp"

#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support()
    args = param_parser()

    inputfolder=args.inputfolder
    filetype = args.filetype
    tilelayoutfile=args.layoutfile
    outputpath=args.outputpath
    buffer=args.buffer
    hz=args.hz
    vt=args.vt
    gndclasses='2 8'
    cores = int(args.cores)
    aoifile = args.aoifile
    clipshape = args.clipshape

    outpath=args.outputpath
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')
    log = open(logpath, 'w')

    lasfiles = []
    filepattern = args.filepattern.split(';')

    if len(filepattern) >=2:
        print('Number of patterns found : {0}'.format(len(filepattern)))
    for pattern in filepattern:
        pattern = pattern.strip()
        print ('Selecting files with pattern {0}'.format(pattern))
        filelist = glob.glob(inputfolder+"\\"+pattern)
        for file in filelist:
            lasfiles.append(file)
    print('Number of Files founds : {0} '.format(len(lasfiles)))

    
    tilelayoutfile=tilelayoutfile.replace('\\','/')
    #path,name,ext=AtlassGen.FILESPEC(lasfile)


    gndclasses=gndclasses.split()    
    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)

    dt = strftime("%y%m%d_%H%M")

    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_makeMKP'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(outputpath, 'working')).replace('\\','/')
    make_mkp_tasks = {}

    for file in lasfiles:
        file=file.replace('\\','/')
        path, filename, ext = AtlassGen.FILESPEC(file)
        tile = tilelayout.gettile(filename)
    
        neighbourfiles = []
        neighbours = tile.getneighbours(buffer)
        for neighbour in neighbours:
            neighbourfiles.append(os.path.join(path,'{0}.{1}'.format(neighbour,ext)).replace('\\','/'))

        print('Neighbourhood of {0} las files detected in overlapping {1}m buffer of :{2}\n Neighbourhood :'.format(len(neighbours),buffer,file))
        print(tile.name)
        make_mkp_tasks[tile.name] = AtlassTask(tile.name, makeMKP, tile, neighbourfiles, outputpath,workingdir, gndclasses,vt, hz, buffer, filetype)

        #makeMKP(tile, neighbourfiles, outpath, gndclasses,vt, hz, buffer, filetype)
    p=Pool(processes=cores)    
    make_mkp_results=p.map(AtlassTaskRunner.taskmanager,make_mkp_tasks.values())

    for result in make_mkp_results:
        print(result.success, result.log)

    if clipshape:
        prodclippeddir = AtlassGen.makedir(os.path.join(outputpath, 'clipped')).replace('\\','/')

        ###########################################################################################################################
        #Index the product laz files
        #index(demlazfile)

        print('Indexing files')
        index_tasks={}
        for result in make_mkp_results:
            log.write(result.log)  
            if result.success:
                tilename = result.name
                x,y=tilename.split('_') 
                file = result.result
                print(file)
                index_tasks[tilename] = AtlassTask(tilename, index, file)
        
    
        index_results=p.map(AtlassTaskRunner.taskmanager,index_tasks.values())



        ###########################################################################################################################
        #Clipping the product las files to the AOI
        #lasclip demlazfile

        print('Clipping the las files to AOI')
        clip_tasks = {}

        for result in index_results:
            log.write(result.log)  
            if result.success:
                print(tilename)
                tilename=result.name

                #files 
                input=result.result
                output = os.path.join(prodclippeddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')

                clip_tasks[tilename] = AtlassTask(tilename, clip, input, output, aoifile, filetype)

        clip_results=p.map(AtlassTaskRunner.taskmanager,clip_tasks.values())   
        
    return
        
if __name__ == "__main__":
    main(sys.argv[1:])            
