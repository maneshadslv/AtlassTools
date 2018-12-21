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
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]))
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
    main_parser.add_argument("geojsonfile", metavar="GoeJson file", widget="FileChooser", help="Select geojson file", default='D:\\Python\\Gui\\input\\TileLayout.json')
    main_parser.add_argument("poly", metavar="AOI file", widget="FileChooser", help="polygon shapefile (.shp)", default='D:\\Python\\Gui\\input\\aoi.shp')
    main_parser.add_argument('name', metavar="AreaName", help="Project Area Name eg : MR101502 ", default="MR22353")
    main_parser.add_argument("epsg", metavar="EPSG", type=int, default=28356)
    main_parser.add_argument("dx", metavar="dx", type=float, default=0.001)
    main_parser.add_argument("dy", metavar="dy", type=float, default=0.0100)
    main_parser.add_argument("dz", metavar="dz", type=float, default=-0.0353)
    main_parser.add_argument("intensity_min", metavar="Intensity min", type=float, default=100)
    main_parser.add_argument("intensity_max", metavar="Intensity max", type=float, default=2500)    
    main_parser.add_argument("-tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    main_parser.add_argument("-k", "--kill",metavar="Kill", help="Large triangle size (m)", type=int, default=250)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    
    return main_parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def asciigridtolas(input, output , filetype, nofiles, i):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''

    print('\nConverting ASCI to {0} : {1}/{2}'.format(filetype, i, nofiles))
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
        log ='Converting {} file  to {} Failed at exception'.format(input, filetype)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {} file  to {} success'.format(input, filetype)
            return (True, output, log)
        else:
            log ='Converting {} file  to {} Failed'.format(input, filetype)
            return (False, output, log)

def clipandmergelas(filelist,clipshape,lasfile,outformat='las'):
    '''
    clips and merges several lasfiles usinf an ESRI shapefile.
    '''
    try:
        subprocessargs=['C:/LAStools/bin/clip.exe','-i'] +filelist + ['-o{0}'.format(outformat),'-merged', '-o', lasfile, '-poly',clipshape] 
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs) 
    except:
        pass
    finally:
        if os.path.isfile(lasfile):
            return lasfile
        else:
            return None

def transformlas(infile,outfile,x=0,y=0,z=0,outformat='las'):
    #
    #clips and merges several lasfiles usinf an ESRI shapefile.
    #

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] +filelist + ['-o{0}'.format(outformat),'-merged', '-o', lasfile, '-poly',clipshape] 
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs) 
    except:
        pass
    finally:
        if os.path.isfile(lasfile):
            return lasfile
        else:
            return None

def makeDEM(xmin, ymin, xmax, ymax, gndfile, workdir, dtmfile, buffer, kill, step, gndclasses, hydropoints, filetype, poly,areaname, nofiles, i):
    #need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
    #use this file for MKP, just remember to remove buffer
    #This will need clipping to AOI
    log = ''
    print('\nMaking DEM for : {0}/{1}'.format(i, nofiles))
    #Prep RAW DTM
    
    #set up clipping    
    keep='-keep_xy {0} {1} {2} {3}'.format(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)
    keep=keep.split()

    
    try:
        #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
        print("Checking for Hydro files")
        if not hydropoints==None:
            gndfile2 = gndfile
            gndfile=os.path.join(workdir,'{0}_{}_dem_hydro.{1}'.format(xmin, ymin,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile2,'-merged','-o{0}'.format(filetype),'-o',gndfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("added Hydro points")

        else:
            print("No Hydro files")
        
        print("DEM starting")
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o', dtmfile,'-nbits',32,'-kill',kill,'-step',step] 
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]    
        #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}_{1}: DEM output FAILED.'.format(xmin, ymin))
        log = 'DEM creation Failed for {0}_{1} at Subprocess.'.format(xmin, ymin)
        return(False, None, log)


    finally:
        if os.path.isfile(dtmfile):
            
            log = 'DEM output Success for: {0}_{1}.'.format(xmin, ymin)
            return(True, dtmfile, log)
        else:
            log = 'DEM creation Failed for: {0}_{1}.'.format(xmin, ymin)
            return(False, None, log)

def adjust(input, output, dx, dy, dz, epsg, filetype, nofiles, i):
    #las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las
    log=''
 
    print('\nAdjusting : {0}/{1}'.format(i,nofiles))
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i' , input ,'-o{0}'.format(filetype), '-translate_xyz', dx, dy, dz, '-epsg', epsg ,'-set_version', 1.2,  '-o', output]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(output):
            log = "Adjusting {0} output : {1}".format(str(input), str(output))
            return (True,output, log)

        else:
            log = "Could not adjust : {0}".format(str(input))
            return (False,None,log)
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Could not adjust {0}. Failed at Subprocess".format(str(input))
        return (False,None,log)

def makeXYZ(input, output, filetype, nofiles, i):
    #las2las -i <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc -otxt -o <inputpath>/Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz -rescale 0.001 0.001 0.001

    #Prep RAW DTM
    print('\nMaking XYZ for :  {0}/{1}'.format(i, nofiles))

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-otxt','-o', output, '-rescale', 0.001, 0.001, 0.001]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make xyz {0}. Failed at Subprocess'.format(str(input))
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'xyz file created for {0}'.format(str(input))
            return (True,output, log)

        else:
            log = 'Could not make xyz {0}'.format(str(input))           
            return (False,None, log)

def index(input, nofiles, i):
    print('\nIndexing  {0}/{1}'.format(i, nofiles))
   
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

def makeMKP(input, tempfile, tempfile2, output, filetype, gndclasses, hz, vt, buffer, tile, nofiles, i):
    log=''
    cleanup=[tempfile2]


    if isinstance(input,str):
        input = [input]
    
    print('\nMaking MKP for  {0}/{1}'.format(i, nofiles))
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+input+['-merged','-o{0}'.format(filetype),'-o',tempfile,'-keep_class'] + gndclasses
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    

        subprocessargs=['C:/LAStools/bin/lasthin.exe','-i',tempfile,'-o{0}'.format(filetype),'-o',tempfile2,'-adaptive',vt,hz,'-set_classification',8]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,'-o{0}'.format(filetype),'-o',output]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin,tile.ymin,tile.xmax,tile.ymax]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making MKP for {0} /nException {1}".format(tile.name, e)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = "Making MKP for {0} Success".format(tile.name)
            for file in cleanup:
                if os.path.isfile(file):
                    os.remove(file)
                    pass
            return (True,output, log)

        else: 
            log = "Making MKP for {} Failed".format(tile.name)
            return (False,None, log)

def clip(input, output, poly, filetype , nofiles, i):
    print('\nClipping : {0}/{1}'.format(i, nofiles))
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

def makegrid(input, output, intensityMin,intensityMax, nofiles, i):
 
    log = ''

    print('\nMaking Grid for  {0}/{1}'.format(i, nofiles))
    try:
        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-step', 0.5, '-fill' ,2 ,'-keep_first', '-intensity_average', '-otif', '-nbits', 8 ,'-set_min_max', intensityMin , intensityMax, '-o', output, '-nrows', 2000, '-ncols', 2000]
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
def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()
    filetype=args.filetype


    areaname = args.name

    buffer=float(args.buffer)
    tilesize=int(args.tile_size)
    dx = args.dx
    dy = args.dy
    dz = args.dz
    epsg = args.epsg
    zone = (int(epsg) - 28300)
    hydropointsfiles=None
    vt = 0.1 
    hz = 20
    poly = args.poly.replace('\\','/')
    geojsonfile = args.geojsonfile.replace('\\','/')
    intensityMin = args.intensity_min
    intensityMax = args.intensity_max
    

    if not args.hydropointsfiles==None:
        hydropointsfiles=args.hydropointsfiles
        hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')
    step=float(args.step)
    kill=float(args.kill)
    gndclasses=[2 ,8]    
    cores = args.cores
    
    tl = AtlassTileLayout()
    tl.fromjson(geojsonfile)
    
    outputpath=args.outputpath.replace('\\','/')
    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_{1}'.format(areaname,strftime("%y%m%d_%H%M"))))
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')

    adjdir = AtlassGen.makedir(os.path.join(outputpath, 'Adjusted')).replace('\\','/')
    adjclippeddir = AtlassGen.makedir(os.path.join(adjdir, 'Clipped')).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(adjdir, 'Working')).replace('\\','/')
    mkpdir = AtlassGen.makedir(os.path.join(adjdir, 'MKP')).replace('\\','/')
    adjdemclippeddir = AtlassGen.makedir(os.path.join(adjdir, 'DEM_Clipped')).replace('\\','/')
    prodsdir = AtlassGen.makedir(os.path.join(outputpath, 'Products')).replace('\\','/')

    dem1dir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_DEM_1m'.format(areaname))).replace('\\','/')
    dem1esridir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_DEM_1m_ESRI'.format(areaname))).replace('\\','/')
    intensitydir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_Intensity_50cm'.format(areaname))).replace('\\','/')
    lasahddir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_LAS_AHD'.format(areaname))).replace('\\','/')

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(geojsonfile)

 

    print("Reading {0} files \n".format(filetype))
    files = []
    files = glob.glob(args.inputpath+"\\*."+filetype)
    print("{0} files found \n".format(len(files)))
    nofiles = len(files)
    ###########################################################################################################################
    #Adjust las
    adj_tasks = {}
    i =0
    print("Applying x,y,z adjustments")
    for file in files:

        path, filename, ext = AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        #finalnames[filename]={}
        #finalnames[filename]['CLIPPED_LAS']='{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.las'.format()
        #finalnames[filename]['ESRI_GRID']='{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.las'.format()
        
        output = os.path.join(adjdir, '{0}.{1}'.format(filename, ext)).replace("\\", "/")
        i +=1      
        adj_tasks[filename] = AtlassTask(filename, adjust, file, output, dx, dy, dz, epsg, filetype, nofiles, i )



    p=Pool(processes=cores)      
    adjust_results=p.map(AtlassTaskRunner.taskmanager,adj_tasks.values())

    ###########################################################################################################################
    #las index
    i=0
    print("Starting Indexing the adjusted Files")
    index_tasks = {}
    for result in adjust_results:
        log.write(result.log)
        if result.success:
            file = result.result
            path, filename, ext = AtlassGen.FILESPEC(file)
            x,y=filename.split('_') 
            i+=1
            index_tasks[filename] = AtlassTask(filename, index, file, nofiles, i)
    

    index_results=p.map(AtlassTaskRunner.taskmanager,index_tasks.values())

    ###########################################################################################################################
    '''
    clip adjusted las into polygon
    lets say there are 1000 files in the input folder.
    The polygon only covers 100 of these. 
    We only need to make DEM and MKP for the 100.
    If we use the names of the 100 returned clipped las files to guide the task runner for these processes.
    We can save considerable tprocessinf time.
    '''
    print('Clipping adjusted files to the AOI')
    clip_task = {}
    i=0
    for result in adjust_results:
 
        if result.success:
            file = result.result
            path, filename, ext = AtlassGen.FILESPEC(file)
            x,y = filename.split('_')
            #files
            output = os.path.join(adjclippeddir, '{0}.{1}'.format(filename, filetype)).replace("\\", "/")
            input = os.path.join(adjdir, '{0}.{1}'.format(filename, filetype)).replace("\\", "/")
            i +=1
            clip_task[filename] = AtlassTask(filename, clip, input, output, poly, filetype, nofiles, i)
            #clip(input,output,poly,filetype)
            


    clip_results=p.map(AtlassTaskRunner.taskmanager,clip_task.values())

    ###########################################################################################################################
    #MKP process
    #use names from clipped las to decide which tiles to generate mkp from unclipped adjusted las.
    i=0
    print('\n\n Starting MKP')
    mkp_tasks = {}
    for result in clip_results:
        #tasklist={'ProcessName':'Run some tasks','fn'=func,'Tasks':{'tile/filename':{'args':args,'kwargs':kwargs,'status':False,'output':None,'log':'blah blah blah\n blah blah blah'}}}
        log.write(result.log)  
        if result.success:
            
            tilename=result.name
            
            #files
            input = os.path.join(adjdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')  #adjusted las
            output=os.path.join(mkpdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            bufferedfile=os.path.join(workingdir,'{0}_buff.{1}'.format(tilename, filetype)).replace('\\','/')
            tempfile2=os.path.join(mkpdir,'{0}_temp2.{1}'.format(tilename, filetype)).replace('\\','/')

            #Get Neigbouring las files
            print('Creating tile neighbourhood for : {0}'.format(tilename))
            tile = tl.gettile(tilename)
            neighbourlasfiles = []

            try:
                neighbours = tile.getneighbours(buffer)
            except:
                print("tile: {0} does not exist in geojson file".format(tilename))

            #print('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,tilename))

            for neighbour in neighbours:
                neighbour = os.path.join(adjdir,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

                if os.path.isfile(neighbour):
                    neighbourlasfiles.append(neighbour)
            i +=1
            mkp_tasks[tilename] = AtlassTask(tilename, makeMKP, neighbourlasfiles, bufferedfile, tempfile2, output, filetype, gndclasses, hz, vt, buffer, tile, nofiles, i)

    mkp_results=p.map(AtlassTaskRunner.taskmanager,mkp_tasks.values())

    ###########################################################################################################################
    #las index mkp las files
    i=0
    print("Starting MKP file Indexing")
    mkp_index_tasks = {}
    for result in mkp_results:
        log.write(result.log)
        if result.success:
            file = result.result
            path, filename, ext = AtlassGen.FILESPEC(file)
            x,y=filename.split('_') 
            i+=1
            mkp_index_tasks[filename] = AtlassTask(filename, index, file, nofiles, i)
    
   
    mkp_index_results=p.map(AtlassTaskRunner.taskmanager,mkp_index_tasks.values())

    

    ###########################################################################################################################
    #Clipping the MKP files and the adjusted files to the AOI
    #Making product ADH

    print('Clipping MKP files to the AOI')
    clip_mkp_tasks = {}
    i=0
    for result in mkp_index_results:
        log.write(result.log)        
        if result.success:
            
            tilename=result.name
            x,y = tilename.split('_')
            #files 
            input_adj = os.path.join(adjdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')  #adjusted las
            input_mkp = result.result # mkp
            output = os.path.join(lasahddir, '{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, x, y, zone, filetype)).replace("\\", "/") #<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las
            input=[input_adj, input_mkp] 
            i+=1
            clip_mkp_tasks[tilename] = AtlassTask(tilename, clip, input, output, poly, filetype, nofiles, i)


    clip_mkp_results=p.map(AtlassTaskRunner.taskmanager,clip_mkp_tasks.values())   
    
    ###########################################################################################################################
    #Make DEM with the adjusted las in the working directory
    #input buffered las file ?????
    i=0
    print('Making DEM')
    dem_tasks = {}
    dem_results = []
    for result in clip_mkp_results:
        log.write(result.log)
        if result.success:
            
            tilename=result.name
            x,y = tilename.split('_')
            #files
            input=os.path.join(workingdir,'{0}_buff.{1}'.format(tilename, filetype)).replace('\\','/') # adjusted buffered las files
            output=os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, x, y)).replace('\\','/')
            i+=1
            dem_tasks[tilename] = AtlassTask(tilename, makeDEM, int(x), int(y), int(x)+tilesize, int(y)+tilesize, input, workingdir, output, buffer, kill, step, gndclasses, hydropointsfiles, filetype, poly,areaname, nofiles, i)
            
    
            #dem_results.append(makeDEM(int(x), int(y), int(x)+tilesize, int(y)+tilesize, input, workingdir, output, buffer, kill, step, gndclasses, hydropointsfiles, filetype, poly,areaname))

    dem_results=p.map(AtlassTaskRunner.taskmanager,dem_tasks.values())

    ###########################################################################################################################
    #Convert asci to laz
    #asciigridtolas(dtmlazfile)
    i=0
    print('Converting ASC to LAZ')
    asciigridtolas_tasks={}
    for result in dem_results:
        log.write(result.log)
        if result.success:
            tilename = result.name

            x,y=tilename.split('_') 


            #files
            input=os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, x, y)).replace('\\','/')
            output=os.path.join(workingdir,'{0}_dem.{1}'.format(tilename, filetype)).replace('\\','/')
            i+=1
            asciigridtolas_tasks[tilename] = AtlassTask(tilename, asciigridtolas, input, output, filetype, nofiles, i)
    

    asciigridtolas_results=p.map(AtlassTaskRunner.taskmanager,asciigridtolas_tasks.values())



    ###########################################################################################################################
    #Index the DEM laz files
    #index(demlazfile)
    i=0
    print('Indexing DEM files')
    index_dem_tasks={}
    for result in asciigridtolas_results:
        log.write(result.log)
        if result.success:
            tilename = result.name
            x,y=tilename.split('_') 
            i+=1
            index_dem_tasks[tilename] = AtlassTask(tilename, index, file, nofiles, i)
    
 
    index_dem_results=p.map(AtlassTaskRunner.taskmanager,index_dem_tasks.values())



    ###########################################################################################################################
    #Clipping the DEM las files to the AOI
    #lasclip demlazfile
    i=0
    print('Clipping the DEM files to AOI')
    clip_demlaz_tasks = {}

    for result in index_dem_results:
        log.write(result.log)
        if result.success:
            
            tilename=result.name

            #files 
            input=os.path.join(workingdir,'{0}_dem.{1}'.format(tilename, filetype)).replace('\\','/') #dtmlaz
            output = os.path.join(adjdemclippeddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            i+=1
            clip_demlaz_tasks[tilename] = AtlassTask(tilename, clip, input, output, poly, filetype, nofiles, i)

    clip_demlaz_results=p.map(AtlassTaskRunner.taskmanager,clip_demlaz_tasks.values())   

    ###########################################################################################################################
    #MAKE XYZ from the dtm asci file, output xyz file in Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz
    #makexyz
    i=0
    print('Making XYZ files')
    xyz_tasks = {}
    for result in clip_demlaz_results:
        log.write(result.log)
        if result.success:
            
            tilename = result.name
            x,y=tilename.split('_') 

            #files 
            input=os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, x, y)).replace('\\','/') #dtm asci file
            output = os.path.join(dem1dir,'{0}_2018_SW_{1}_{2}_1k_1m.xyz'.format(areaname, x, y)).replace('\\','/')

            i+=1
            xyz_tasks[tilename] = AtlassTask(tilename, makeXYZ, input, output, filetype, nofiles, i)


    xyz_results=p.map(AtlassTaskRunner.taskmanager,xyz_tasks.values())   

    for result in xyz_results:
        print(result.name, result.success, result.result)


    ###########################################################################################################################
    #MAKE GRID from the AHD las files, output tif file
    #makexyz
    i=0
    print('Making Grid')
    grid_tasks = {}
    for result in clip_demlaz_results:
        log.write(result.log)
        if result.success:
            
            tilename = result.name
            x,y=tilename.split('_') 

            #files 
            input = os.path.join(lasahddir, '{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, x, y, zone, filetype)).replace("\\", "/") #<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las
            output = os.path.join(intensitydir,'{0}_2018_SW_{1}_{2}_1k_50cm_INT.tif'.format(areaname, x, y)).replace("\\", "/")   #<inputpath>/Products/<Area_Name>_Intensity_50cm/<Name>_2018_SW_<X>_<Y>_1k_50cm_INT.tif

            i+=1
            grid_tasks[tilename] = AtlassTask(tilename, makegrid, input, output, intensityMin,intensityMax, nofiles, i)


    grid_results=p.map(AtlassTaskRunner.taskmanager,grid_tasks.values())   
    
    for result in grid_results:
        log.write(result.log)
        print(result.name, result.success)

    log.close()
    return


if __name__ == "__main__":
    main()         

'''
Make def for each of the bolow functions;


kwargs;
    <input path>
    <input extn>
    <Area name> eg <MR101502>
    <poly>
    <dx>
    <dy>
    <dz>
    <epsg> or <Zone>   EPSG= 28300 + <Zone>
    <cores>
    <intensity Min>
    <intensity max>


1.
make output folder structure based on
<inputpath>/Adjusted/
<inputpath>/Adjusted/Working
<inputpath>/Adjusted/MKP

<inputpath>/Products/<Area_Name>_DEM_1m
<inputpath>/Products/<Area_Name>_DEM_1m_ESRI
<inputpath>/Products/<Area_Name>_Intensity_50cm
<inputpath>/Products/<Area_Name>_LAS_AHD

2. 
#las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las

3.
#need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
use this file for MKP, just remember to remove buffer
MakeGrids Just DEM in <inputpath>/Adjusted/<name>.las  ... to <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc    
This will need clipping to AOI

4. 
las2las -i <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc     -otxt -o <inputpath>/Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz -rescale 0.001 0.001 0.001

5.
lasindex <inputpath>/Adjusted/<name>.las

6.
Make MKP vt=0.1 hz=20 -input=<inputpath>/Adjusted/Working/<name>.las output=<inputpath>/Adjusted/MKP/<name>.las --set_classification 8  (remove buffer)

7.
lasindex <inputpath>/Adjusted/MKP/<name>.las


8.
lasclip -i -use_lax <inputpath>/Adjusted/<name>.las <inputpath>/Adjusted/MKP/<name>.las -merged -poly <poly> -o <inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las -olas


9.
lasgrid -i<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las -step 0.5 -fill 2 -keep_first -intensity_average -otif -nbits 8 -set_min_max <intensity Min> <intensity Max> -o <inputpath>/Products/<Area_Name>_Intensity_50cm/<Name>_2018_SW_<X>_<Y>_1k_50cm_INT.tif -nrows 2000 -ncols 2000



set up multi thread process for each
'''


#



#lasgrid -i W:\TMR_Mackaybeesck_VQ780_180923\20181012\dz\clipped\*.las -step 0.5 -fill 2 -keep_first -intensity_average -otif -nbits 8 -set_min_max 100 2500 -cores 18 -odir W:\TMR_Mackaybeesck_VQ780_180923\20181012\clipped_intensity -nrows 2000 -ncols 2000

#C:\LASTools\bin\lasgrid -i *.laz -cores 18 -keep_last -step 5 -point_density -otif -odir point_density

