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
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]))
from Atlass_beta1 import *


#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 01/10/2016 -Alex Rixon - Added functionality to create hydro flattening points. 
# 01/10/2016 -Alex Rixon - Added functionality to create CHM  
# 30/09/2016 -Alex Rixon - Added functionality to create DHM 
# 20/09/2016 -Alex Rixon - Original development Alex Rixon
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

#-----------------------------------------------------------------------------------------------------------------
#grid class
#-----------------------------------------------------------------------------------------------------------------
      
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
@Gooey(program_name="Make Grid", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Make Grid")
    main_parser.add_argument("inputpath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default='D:\\Python\\test')
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    main_parser.add_argument("geojsonfile", metavar="TileLayout file", widget="FileChooser", help="Select .json file", default='D:\\Python\\test\\TileLayout.json')
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='D:\\Python\\test\\out')
    main_parser.add_argument("-tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    main_parser.add_argument("aoifile", metavar="AOI shp file", widget="FileChooser", help="Select aoi shape file for clipping", default='D:\\Python\\test\\aoi.shp')
    product_group = main_parser.add_argument_group("Products", "Select Output Products", gooey_options={'show_border': True,'columns': 5})
    product_group.add_argument("-dem", "--makeDEM", metavar="DEM", action='store_true', default=True)
    product_group.add_argument("-dsm", "--makeDSM", metavar="DSM", action='store_true')
    product_group.add_argument("-chm", "--makeCHM", metavar="CHM", action='store_true')
    product_group.add_argument("-hydro", "--makeHYDRO", metavar="Hydro", action='store_true')
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-cs", "--chmstep",metavar="CHM step", help="Provide chmstep", type=float, default=2.0)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("--clipshape", metavar="Clip shape", help="Clip Shape", action='store_true')
    main_parser.add_argument("-c", "--classes",metavar="classes", help="Provide classes", default="2;8")
    main_parser.add_argument("-ngc", "--nongndclasses", metavar = "Non Ground Classes", default="1 3 4 5 6 10 13 14 15")
    main_parser.add_argument("-chmc", "--chmclasses", metavar = "CHM Classes", default="3 4 5")
    main_parser.add_argument("-gc", "--gndclasses", metavar = "Ground Classes", default="2 8")
    main_parser.add_argument("-hc", "--hydrogridclasses", metavar = "Hydro Grid Classes", default="2 4 5 6 8 10 13")
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    main_parser.add_argument("-k", "--kill",metavar="Kill", help="Kill after (s)", type=int, default=250)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    
    return main_parser.parse_args()

def makeBufferedFiles(input, outputpath, x, y, filename,tilesize, buffer, nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeHYDRO, makeCHM, filetype, step, chmstep):

    if isinstance(input, str):
        input = [input]

    output = []
    bufflasfile = os.path.join(outputpath,'{0}.{1}'.format(filename, filetype)).replace('\\','/') 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(x-buffer), y-buffer, x+tilesize+buffer, y+tilesize+buffer)
    keep=keep.split()
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + input + ['-olaz','-o', bufflasfile,'-merged','-keep_class'] + gndclasses + keep #'-rescale',0.001,0.001,0.001,
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)      

        if makeDSM:
            dsmgridfile = os.path.join(outputpath,'{0}_dsm_grid.asc'.format(filename)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + input + ['-merged','-oasc','-o',dsmgridfile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-highest','-first_only','-subcircle',step/4]
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)] + ['-keep_class']+ nongndclasses
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if makeCHM:
            chmgridfile = os.path.join(outputpath,'{0}_chm_grid.asc'.format(filename)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + input + ['-merged','-oasc','-o',chmgridfile,'-nbits',32,'-fill',0,'-step',chmstep,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/chmstep), '-nrows',math.ceil((tilesize)/chmstep)] + ['-keep_class']+ chmclasses
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if makeHYDRO:
            hydrofile = os.path.join(outputpath,'{0}_hydro_input.asc'.format(filename)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + input + ['-merged','-oasc','-o',hydrofile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-lowest','-subcircle',step]
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)] + ['-keep_class']+ hydrogridclasses
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)     
            
    
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making MKP for {0} /nException {1}".format(bufflasfile, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufflasfile):
            log = "Making MKP for {0} Success".format(bufflasfile)
            for file in bufflasfile:
                if os.path.isfile(file):
                    os.remove(file)
                    pass
            return (True,bufflasfile, log)

        else: 
            log = "Making MKP for {0} Failed".format(bufflasfile)
            return (False,None, log)
   
def MakeDEM(x, y, tilename, gndfile, workdir, dtmfile, buffer, kill, step, gndclasses, hydropoints, tilesize, filetype):
    #need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
    #use this file for MKP, just remember to remove buffer
    #This will need clipping to AOI
    log = ''
    #Prep RAW DTM
    
    #set up clipping    
    keep='-keep_xy {0} {1} {2} {3}'.format(x-buffer,y-buffer,x+tilesize+buffer,y+tilesize+buffer)
    keep=keep.split()
    print('Making DEM for : {0}'.format(gndfile))
    
    try:
        #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
        print("Checking for Hydro files")
        if not hydropoints==None:
            gndfile2 = gndfile
            gndfile=os.path.join(workdir,'{0}_dem_hydro.{1}'.format(tilename,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile2,'-merged','-o{0}'.format(filetype),'-o',gndfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("added Hydro points")

        else:
            print("No Hydro files")
        
        print("DEM starting")
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o', dtmfile,'-nbits',32,'-kill',kill,'-step',step] 
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]    
        #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}: DEM output FAILED.'.format(tilename))
        log = 'DEM creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(dtmfile):
            
            log = 'DEM output Success for: {0}.'.format(tilename)
            return(True, dtmfile, log)
        else:
            log = 'DEM creation Failed for: {0}.'.format(tilename)
            return(False, None, log)

def MakeDSM(demfile,dsmgridfile, outfile, step, tilename, x, y, nongndclasses, tilesize, buffer): 
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #DSM
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #make dsm grid with no interpolation
    print('DSM Starting')
    cleanup=[]

    cleanup.append(dsmgridfile)
   
    try:

        #Merge dsm grid and dem grid
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + [dsmgridfile,demfile] + ['-merged','-oasc','-o',outfile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
        subprocessargs=list(map(str,subprocessargs))       
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}}: DSM output FAILED.'.format(tilename))
        log = 'DSM creation Failed for {0}_{1} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(outfile):
            
            log = 'DSM output Success for: {0}.'.format(tilename)
            for file in cleanup:
                try:
                    if os.path.isfile(file):
                        os.remove(file)   
                except:
                    print('cleanup FAILED.') 
                print('Cleaning Process complete')
            return(True, outfile, log)
        else:
            log = 'DSM creation Failed for: {0}.'.format(tilename)
            return(False, None, log)

def MakeCHM (x, y, gndfile, chmgridfile, chmfile, chmdemgridfile, tilename, buffer, kill, step, chmstep, tilesize, filetype): 
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #CHM
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Make veg grid with no interpolation
    log = ''
    cleanup = []
    cleanup.append(chmgridfile)

    print('CHM Starting')
    try:
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o',chmdemgridfile,'-nbits',32,'-kill',kill,'-step',chmstep] 
        subprocessargs=subprocessargs+['-ll',x, y,'-ncols',math.ceil((tilesize)/chmstep), '-nrows',math.ceil((tilesize)/chmstep)]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)   
        if os.path.isfile(chmdemgridfile):
            print('CHM dem grid File Created {}'.format(chmdemgridfile))
            cleanup.append(chmdemgridfile)
        else:
            exit()

        a=AsciiGrid()    
        a.readfromfile(chmgridfile)     
        
        b=AsciiGrid()    
        b.readfromfile(chmdemgridfile) 
        

        ones=np.array(np.ones((b.grid.shape[0],b.grid.shape[1])), ndmin=2, dtype=int)
        zeros=np.array(np.zeros((b.grid.shape[0],b.grid.shape[1])), ndmin=2, dtype=int)    
        
        c=AsciiGrid()  
        c.header=a.header
        c.grid=np.subtract(a.grid,b.grid)

        c.grid=np.where(c.grid>=0,c.grid,zeros)
        c.savetofile(chmfile) 


    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}: CHM output FAILED.'.format(tilename))
        log = '\nCHM creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(chmfile):
            print('Success')
            log = 'CHM output Success for: {0}.'.format(tilename)
            for file in cleanup:
                try:
                    if os.path.isfile(file):
                        os.remove(file)  
                except:
                    print('cleanup FAILED.') 
            print('Cleaning Process complete')
            return(True, chmfile, log)
        else:
            print('Failed to find output CHM file for : {0}'.format(tilename))
            log = 'CHM creation Failed for: {0}.'.format(tilename)
            return(False, None, log)

def MakeHYDRO(hydrofile, hydrovoidfile, hydromanhattan, tilename): 
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Hydro-flattening
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Make hydro points grid with no interpolation
    print('Hydro starting')
    log = ''
    try:
    
        #merge hydro grid and dem grid
        
        a=AsciiGrid()    
        a.readfromfile(hydrofile)     

        ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
        zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
        nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

        # extract hydro void areas
        hydrovoids=ones*(a.grid==a.nodata_value)
        
        hydrovoids_dem=AsciiGrid() 
        hydrovoids_dem.header=a.header

        #currently just outputting voids as value 1
        hydrovoids_dem.grid=np.where(hydrovoids==1,ones,nodata)
        hydrovoids_dem.savetofile(hydrovoidfile) 

        #output manhattan distance grid 
        dist=morphology.distance_transform_cdt(hydrovoids,metric='taxicab').astype(hydrovoids.dtype)
        hydrovoids_dem.grid=np.where(dist>=1,dist,nodata)
        
        hydrovoids_dem.savetofile(hydromanhattan) 
        
        print('Hydro grid output Successfull.')

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}: Hydro output FAILED.'.format(tilename))
        log = '\Hydro creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(hydromanhattan):
            log = 'Hydro output Success for: {0}.'.format(tilename)
            return(True, hydromanhattan, log)
        else:
            print('Failed to find output CHM file for : {0}'.format(tilename))
            log = 'Hydro creation Failed for: {0}.'.format(tilename)
            return(False, None, log)
        
def asciigridtolas(input, output , filetype):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''

    log = ''
    try:
       #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-o{0}'.format(filetype), '-o', output, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting {0} file  to {1} Failed at exception'.format(input, filetype)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {0} file  to {1} success'.format(input, filetype)
            return (True, output, log)
        else:
            log ='Converting {0} file  to {1} Failed'.format(input, filetype)
            return (False, output, log)

def lastoasciigrid(x,y,input, output, tilesize, step):
    '''
    Converts a las/laz file to ascii and retains the milimetre precision.
    '''

    log = ''
    try:
       #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', input, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
        subprocessargs=list(map(str,subprocessargs))       
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting las to asc Failed at exception for : {0}'.format(input)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting las to asc success for : {0}'.format(input)
            return (True, output, log)
        else:
            log ='Converting las to asc Failed for {0}'.format(input)
            return (False, output, log)

def index(input):
   
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        return(True, None, "Success")

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
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support() 
    args = param_parser()

    #create variables from gui
    outputpath=args.outputpath
    outputpath=outputpath.replace('\\','/')
    buffer=float(args.buffer)
    hydropointsfiles=None
    if not args.hydropointsfiles==None:
        hydropointsfiles=args.hydropointsfiles
        hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')
    clipshape=args.clipshape
    step=float(args.step)
    chmstep=float(args.chmstep)
    kill=float(args.kill)
    nongndclasses=args.nongndclasses.split()
    chmclasses=args.chmclasses.split()
    gndclasses=args.gndclasses.split()    
    hydrogridclasses=args.hydrogridclasses.split()
    makeHYDRO=args.makeHYDRO
    makeDSM=args.makeDSM
    makeCHM=args.makeCHM
    makeDEM=args.makeDEM
    cores = args.cores
    tilesize = args.tile_size
    filetype = args.filetype
    aoifile = args.aoifile
    tilelayout = AtlassTileLayout()
    lasfiles = []
    lasfiles = glob.glob(args.inputpath+"\\*."+filetype)

    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')

    if not args.geojsonfile == None:
        geojsonfile = args.geojsonfile

    print(len(lasfiles))

    productlist = []
    if makeDEM:
        productlist.append('DEM')
    if makeDSM:
        productlist.append('DSM')   
    if makeCHM:
        productlist.append('CHM')
    if makeHYDRO:
        productlist.append('HYDRO')
     
    #read tilelayout into library
    tl = AtlassTileLayout()
    tl.fromjson(geojsonfile)
    dt = strftime("%y%m%d_%H%M")

    workingdir = AtlassGen.makedir(os.path.join(outputpath, '{0}_makeGrid'.format(dt))).replace('\\','/')
    buffdir = AtlassGen.makedir(os.path.join(workingdir, 'buffered')).replace('\\','/')

   


    ###########################################################################################################################
    #Make buffered files

    print("Making buffered files")
    makebuff_tasks = {}
    makebuff_results = []
    for file in lasfiles: 

        print('Creating tile neighbourhood for : {0}'.format(file))
        path, filename, ext = AtlassGen.FILESPEC(file)
        x,y = filename.split('_')
        tile = tl.gettile(filename)
        neighbourlasfiles = []

        try:
            neighbours = tile.getneighbours(buffer)

        except:
            print("tile: {0} does not exist in geojson file".format(filename))

        print('Neighbourhood of {0} las files detected in overlapping {1}m buffer of :{2}\n Neighbourhood :'.format(len(neighbours),buffer,file))
        #files
        for neighbour in neighbours:
            neighbour = os.path.join(path, '{0}.{1}'.format(neighbour, filetype))
            if os.path.isfile(neighbour):
                print('\n{0}'.format(neighbour))
                neighbourlasfiles.append(neighbour)
        makebuff_tasks[filename] = AtlassTask(filename, makeBufferedFiles, neighbourlasfiles, buffdir, int(x), int(y), filename, int(tilesize), int(buffer),nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeHYDRO, makeCHM, filetype, step, chmstep)

    p=Pool(processes=cores)    
    makebuff_results=p.map(AtlassTaskRunner.taskmanager,makebuff_tasks.values())

    print(list(productlist))

    for product in productlist:
        ###########################################################################################################################
        #Make relavant product with the buffered las files
        #input buffered las file ?????
        proddir = AtlassGen.makedir(os.path.join(workingdir, product)).replace('\\','/')


        print('Making {0}'.format(product))
        tasks = {}
        results = []
        for result in makebuff_results:
            log.write(result.log)            
            if result.success:
                
                tilename=result.name
                x,y = tilename.split('_')


                if product =='DEM':
                    #files
                    input=os.path.join(buffdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                    output=os.path.join(proddir,'{0}_{1}.asc'.format(tilename, product)).replace('\\','/')
                    tasks[tilename] = AtlassTask(tilename, MakeDEM, int(x), int(y), tilename, input, proddir, output, buffer, kill, step, gndclasses, hydropointsfiles, int(tilesize), filetype)
                    #MakeDEM(int(x), int(y), tilename, input, proddir, output, buffer, kill, step, gndclasses, hydropointsfiles, int(tilesize), filetype)
                if product =='DSM':
                    #files
                    dsmgridfile = os.path.join(buffdir,'{0}_dsm_grid.asc'.format(tilename)).replace('\\','/')
                    demfile = os.path.join(workingdir,'DEM/{0}_DEM.asc'.format(tilename)).replace('\\','/')
                    output = os.path.join(proddir,'{0}_{1}.asc'.format(tilename, product)).replace('\\','/')
                    tasks[tilename] = AtlassTask(tilename, MakeDSM, demfile, dsmgridfile, output, step, tilename, int(x), int(y), nongndclasses, int(tilesize), buffer )               
                    #MakeDSM(demfile, dsmgridfile, outfile, step, tilename, int(x), int(y), nongndclasses, int(tilesize), buffer )  

                if product =='CHM':
                    #files
                    demfile = os.path.join(workingdir,'DEM/{0}_DEM.asc'.format(tilename)).replace('\\','/') 
                    chmgridfile = os.path.join(buffdir,'{0}_chm_grid.asc'.format(tilename)).replace('\\','/')
                    chmdemgridfile = os.path.join(buffdir,'{0}_CHM_DEM_grid.asc'.format(tilename)).replace('\\','/')
                    output=os.path.join(proddir,'{0}_{1}.asc'.format(tilename, product)).replace('\\','/')
                    tasks[tilename] = AtlassTask(tilename, MakeCHM, int(x), int(y), demfile, chmgridfile, output, chmdemgridfile, tilename, buffer, kill, step, chmstep, int(tilesize), filetype)
                    #MakeCHM(int(x), int(y), demfile, chmgridfile, output, chmdemgridfile, tilename, buffer, kill, step, chmstep, int(tilesize), filetype)
                
                if product =='HYDRO':
                    #files
                    hydrofile = os.path.join(buffdir,'{0}_hydro_input.asc'.format(tilename)).replace('\\','/')
                    hydrovoidfile=os.path.join(buffdir,'{0}_hydro_voids.asc'.format(tilename)).replace('\\','/')
                    output=os.path.join(proddir,'{0}_{1}.asc'.format(tilename, product)).replace('\\','/')
                    tasks[tilename] = AtlassTask(tilename, MakeHYDRO, hydrofile, hydrovoidfile, output, tilename)
        
        results=p.map(AtlassTaskRunner.taskmanager,tasks.values())


        # Run the following steps only if clip shape selected
        if clipshape:
            ###########################################################################################################################
            #Convert asci to laz
            #asciigridtolas(dtmlazfile)
            prodclippeddir = AtlassGen.makedir(os.path.join(proddir, 'clipped')).replace('\\','/')
            print('Converting ASC to LAZ')
            asciigridtolas_tasks={}
            for result in results:
                log.write(result.log)  
                if result.success:
                    tilename = result.name

                    x,y=tilename.split('_') 

                    #files
                    input=os.path.join(proddir,'{0}_{1}.asc'.format(tilename, product)).replace('\\','/')
                    output=os.path.join(proddir,'{0}_{1}.{2}'.format(tilename, product, filetype)).replace('\\','/')

                    asciigridtolas_tasks[tilename] = AtlassTask(tilename, asciigridtolas, input, output, filetype)
            

            asciigridtolas_results=p.map(AtlassTaskRunner.taskmanager,asciigridtolas_tasks.values())


            ###########################################################################################################################
            #Index the product laz files
            #index(demlazfile)

            print('Indexing files')
            index_tasks={}
            for result in asciigridtolas_results:
                log.write(result.log)  
                if result.success:
                    tilename = result.name
                    x,y=tilename.split('_') 

                    index_tasks[tilename] = AtlassTask(tilename, index, file)
            
        
            index_results=p.map(AtlassTaskRunner.taskmanager,index_tasks.values())



            ###########################################################################################################################
            #Clipping the product las files to the AOI
            #lasclip demlazfile

            print('Clipping the las files to AOI')
            clip_demlaz_tasks = {}

            for result in index_results:
                log.write(result.log)  
                if result.success:
                    print(tilename)
                    tilename=result.name

                    #files 
                    input=os.path.join(proddir,'{0}_{1}.{2}'.format(tilename, product, filetype)).replace('\\','/') #dtmlaz
                    output = os.path.join(prodclippeddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')

                    clip_demlaz_tasks[tilename] = AtlassTask(tilename, clip, input, output, aoifile, filetype)

            clip_demlaz_results=p.map(AtlassTaskRunner.taskmanager,clip_demlaz_tasks.values())   


            #############################################################################################################################
            #Convert the laz files to asci
            #lasgrid
            #TODo
            print('Converting Clipped {0} to asc'.format(filetype))
            lastoasciigrid_tasks={}
            for result in  clip_demlaz_results:
                log.write(result.log)  
                if result.success:
                    tilename = result.name

                    x,y=tilename.split('_') 

                    #files
                    input=os.path.join(prodclippeddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
                    output=os.path.join(prodclippeddir,'{0}_{1}_clipped.asc'.format(tilename, product)).replace('\\','/')

                    lastoasciigrid_tasks[tilename] = AtlassTask(tilename, lastoasciigrid,int(x), int(y), input, output, int(tilesize), step)
            

            lastoasciigrid_results=p.map(AtlassTaskRunner.taskmanager,lastoasciigrid_tasks.values())

        
if __name__ == "__main__":
    main(sys.argv[1:]) 
