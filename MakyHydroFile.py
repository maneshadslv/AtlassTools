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
import urllib
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
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
    main_parser.add_argument("inputpath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default='')
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.laz')
    main_parser.add_argument("inputgeojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default='')
    main_parser.add_argument("outputgeojsonfile", metavar="Output TileLayout file", widget="FileChooser", help="Select .json file", default='')
    main_parser.add_argument("--outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default='')
    main_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default='')    
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    main_parser.add_argument("--epsg", metavar="EPSG")
    main_parser.add_argument("--projectname", metavar="Project Name and Year", help="ProjectNameYYYY")
    product_group = main_parser.add_argument_group("Products", "Select Output Products", gooey_options={'show_border': True,'columns': 5})
    product_group.add_argument("-dem", "--makeDEM", metavar="DEM", action='store_true', default=True)
    product_group.add_argument("-dsm", "--makeDSM", metavar="DSM", action='store_true')
    product_group.add_argument("-chm", "--makeCHM", metavar="CHM", action='store_true')
    product_group.add_argument("-hydro", "--makeHYDRO", metavar="Hydro", action='store_true')
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-cs", "--chmstep",metavar="CHM step", help="Provide chmstep", type=float, default=2.0)
    main_parser.add_argument("--clipshape", metavar="Clip shape", help="Clip Shape", action='store_true')
    main_parser.add_argument("--aoifiles", metavar="AOI shp file", widget="MultiFileChooser", help="Select aoi shape file/s for clipping", default='')
    main_parser.add_argument("--merged", metavar="Merged", action='store_true')
    main_parser.add_argument("--makeFCM", metavar="Prepare DEM for Vegetation Model", action='store_true')
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
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
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + input + ['-olaz','-o', bufflasfile,'-merged','-keep_class'] +[0,1,2,4,5,6,8,10,13,14,15] + keep #'-rescale',0.001,0.001,0.001,
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
            hydfile=os.path.join(workdir,'{0}_{1}_hydro.{2}'.format(x, y,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + hydropoints + ['-merged','-o{0}'.format(filetype),'-o', hydfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("clipped Hydro points")

            gndfile2 = gndfile
            gndfile=os.path.join(workdir,'{0}_{1}_dem_hydro.{2}'.format(x,y,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile2, hydfile,'-merged','-o{0}'.format(filetype),'-o',gndfile] + keep 
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
    log = ''
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
        print('{0}: DSM output FAILED.'.format(tilename))
        log = 'DSM creation Failed for {0} at Subprocess.'.format(tilename)
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
    #cleanup.append(chmgridfile)

    print('CHM Starting')
    try:

        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o',chmdemgridfile,'-nbits',32,'-kill',kill,'-step',chmstep]
        subprocessargs=subprocessargs+['-ll',x, y,'-ncols',math.ceil((tilesize)/chmstep), '-nrows',math.ceil((tilesize)/chmstep)]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)   
        if os.path.isfile(chmdemgridfile):
            print('CHM dem grid File Created {}'.format(chmdemgridfile))
            #cleanup.append(chmdemgridfile)
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

def MakeHYDRO(buffered_las, proddir, output, xmin,ymin,xmax,ymax,tilename,tilesize,step, buffer,kill): 
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Hydro-flattening
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #Make hydro points grid with no interpolation
    print('Hydro starting')
    log = ''
    hydrovoidfilelaz=output.replace('.asc','.laz')


    mergedlas = buffered_las.replace('.laz', '_HYDRO.laz')
    #excluding water, noise and low veg
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',buffered_las,'-olaz','-o',mergedlas,'-keep_class'] + [0,1,2,4,5,6,8,10,13,14,15]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)     
    cleanupfiles=[]

    #make a dsm grid for lowest elevation using subcircle and fill - clip to tile
    print("Making hydro grid1")
    dsmtempfile1=mergedlas.replace('_HYDRO.laz','_HYDRO.asc')
    cleanupfiles.append(dsmtempfile1)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-oasc','-o',dsmtempfile1,'-nbits',32,'-elevation_lowest','-step',step,'-subcircle',step,'-fill',1]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    


    #make a dsm grid for lowest elevation using subcircle and fill - not clipped to tile
    print("Making hydro grid2")
    dsmtempfile2=mergedlas.replace('.laz','_low_elev.laz')
    cleanupfiles.append(dsmtempfile2)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-olaz','-o',dsmtempfile2,'-nbits',32,'-elevation_lowest','-step',step,'-subcircle',step,'-fill',1]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    

    #make a dsm grid for triangulated elevation - clip to tile
    print("Making DEM grid")
    dsmtempfile3=mergedlas.replace('.laz','_DEM.asc')
    cleanupfiles.append(dsmtempfile3)
    subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',mergedlas,'-oasc','-o',dsmtempfile3,'-nbits',32,'-step',step,'-kill',kill,'-keep_class'] + [2]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    


    #merge hydro grid and dem grid
    
    a=AsciiGrid()
    b=AsciiGrid()   
    a.readfromfile(dsmtempfile1)     
    b.readfromfile(dsmtempfile3)     

    ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
    zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
    nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

    # extract hydro void areas
    hydrovoids=ones*(a.grid==a.nodata_value)
    
    hydrovoids_dem=AsciiGrid() 
    hydrovoids_dem.header=a.header

    #outputting voids as value 1
    hydrovoids_dem.grid=np.where(hydrovoids==1,ones,nodata)
    hydrovoidfile=mergedlas.replace('_HYDRO.laz','_HYDRO_Voids.asc')
    hydrovoids_dem.savetofile(hydrovoidfile)     

    #outputting voids with dem heights
    hydrovoids_dem.grid=np.where(hydrovoids==1,b.grid,nodata)
    hydrovoidfile=mergedlas.replace('_HYDRO.laz','_HYDRO_Voids_Height.asc')
    hydrovoids_dem.savetofile(hydrovoidfile)         

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydrovoidfile,'-olaz','-o',hydrovoidfilelaz,'-rescale',0.001,0.001,0.001]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)    
        
        print('Hydro grid output Successfull.')

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}: Hydro output FAILED.'.format(tilename))
        log = 'Hydro creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(hydrovoidfilelaz):
            log = 'Hydro output Success for: {0}.'.format(tilename)
            return(True, hydrovoidfilelaz, log)
        else:
            print('Failed to find output file for : {0}'.format(tilename))
            log = 'Hydro creation Failed for: {0}.'.format(tilename)
            return(False, None, log)
        
def asciigridtolas(input, output , filetype):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''

    log = ''
    if os.path.isfile(input):
        print('Converting {0} to las'.format(input))
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

def lastoasciigrid(x,y,inputF, output, tilesize, step):
    '''
    Converts a las/laz file to ascii and retains the milimetre precision.
    '''

    if os.path.isfile(inputF):
        log = ''
        try:
        #las2las -i <dtmfile> -olas -o <dtmlazfile>
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', inputF, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
            subprocessargs=list(map(str,subprocessargs))       
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log ='Converting las to asc Failed at exception for : {0}'.format(inputF)
            return (False, output, log)
        finally:
            if os.path.isfile(output):
                log ='Converting las to asc success for : {0}'.format(inputF)
                return (True, output, log)
            else:
                log ='Converting las to asc Failed for {0}'.format(inputF)
                return (False, output, log)
    else:
        return(True,None,'Not input File')

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

def merge_product(inputdir, mergedlasfile, output, step, filetype):
   
    input = '{0}/*.{1}'.format(inputdir, filetype)
    log=''
    try:
        #las2las -i (asciigridtolas_results.path)\*.laz -merged -step step -oasc -o product\merged\merged_"product".asc

        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', input, '-merged', '-olas', '-o', mergedlasfile]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', mergedlasfile, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
        subprocessargs=list(map(str,subprocessargs))       
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        if os.path.isfile(output):
            log = "Merged input : {0} \nMerged output : {1}".format(str(input), str(output)) 
            return (True,output, log)

        else:
            log = "Merging failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Merging failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)

def makeProductsperTile(tl_in, tl_out,xmin,ymin,xmax,ymax,tilename,tilesize,productlist,inputfolder,workingdir,outputdir,filetype,hydropointsfiles,buffer,nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeHYDRO, makeCHM, step, chmstep,kill,clipshape,aoifiles,prjfile,merged,projname,makeFCM):
    
    if step == 1.0:
        gsd = '001'
    elif step == 2.0:
        gsd = '002'
    elif step == 0.5:
        gsd = '0_5'

    if not projname == None:
        proj = '{0}_'.format(projname)
    else:
        proj = ''

    ##########################################################################################################################
    #Making the neighbourhood files
    #


    print('Creating tile neighbourhood for : {0}'.format(tilename))
    buffdir = AtlassGen.makedir(os.path.join(workingdir, 'buffered')).replace('\\','/')
    neighbourlasfiles = []
    neighbours = []
    makebuff_results = []
    deletefiles = []
    try:
        neighbours =  tl_in.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    except:
        print("tile: {0} does not exist in geojson file".format(tilename))

    print('Neighbours : {0}'.format(neighbours))
    
    #files
    for neighbour in neighbours:
        neighbour = os.path.join(inputfolder, '{0}.{1}'.format(neighbour, filetype))
        if os.path.isfile(neighbour):
            print('\n{0}'.format(neighbour))
            neighbourlasfiles.append(neighbour)
        else:
            print('\nFile {0} could not be found in {1}'.format(neighbour, inputfolder))

    makebuff_results = makeBufferedFiles(neighbourlasfiles, buffdir, int(xmin), int(ymin), tilename, int(tilesize), int(buffer),nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeHYDRO, makeCHM, filetype, step, chmstep)

    deletefiles.append(makebuff_results[1])


    for product in productlist:
        ###########################################################################################################################
        #Make relavant product with the buffered las files
        #input buffered las file ?????
        proddir = AtlassGen.makedir(os.path.join(workingdir, product)).replace('\\','/')
        proddir_out = AtlassGen.makedir(os.path.join(outputdir, product)).replace('\\','/')
        product_files = []
        prjfile1 = os.path.join(proddir,'{0}{1}-GRID_{2}_{3}_{4}m.prj'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')
        output = os.path.join(proddir,'{0}{1}-GRID_{2}_{3}_{4}m.asc'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')

        product_files.append(output)
        product_files.append(prjfile1)

        print('Making {0}'.format(product))
                            
        if makebuff_results[0]:
                
            if product =='DEM':
                #files
                input=os.path.join(buffdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                MakeDEM(int(xmin), int(ymin), tilename, input, proddir, output, buffer, kill, step, gndclasses, hydropointsfiles, int(tilesize), filetype)


            if product =='DSM':
                #files
                dsmgridfile = os.path.join(buffdir,'{0}_dsm_grid.asc'.format(tilename)).replace('\\','/')
                demfile = os.path.join(workingdir,'DEM/{0}{1}-GRID_{2}_{3}_{4}m.asc'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')
                MakeDSM(demfile, dsmgridfile, output, step, tilename, int(xmin), int(ymin), nongndclasses, int(tilesize), buffer )               


            if product =='CHM':
                #files
                #demfile = os.path.join(workingdir,'DEM/{0}_DEM.asc'.format(tilename)).replace('\\','/') 
                input=os.path.join(buffdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                chmgridfile = os.path.join(buffdir,'{0}_chm_grid.asc'.format(tilename)).replace('\\','/')
                chmdemgridfile = os.path.join(buffdir,'{0}_CHM_DEM_grid.asc'.format(tilename)).replace('\\','/')
                MakeCHM(int(xmin), int(ymin), input, chmgridfile, output, chmdemgridfile, tilename, buffer, kill, step, chmstep, int(tilesize), filetype)

            if product =='HYDRO':
                #files
                buffered_laz = os.path.join(buffdir,'{0}.laz'.format(tilename)).replace('\\','/')
                MakeHYDRO(buffered_laz,proddir, output, xmin,ymin,xmax,ymax,tilename,tilesize,step,buffer,kill)


        if os.path.isfile(output):
            shutil.copyfile(prjfile, prjfile1) 

            # Run the following steps only if clip shape or merged or makeFCM selected
            if clipshape or merged or makeFCM:
                if not product == 'HYDRO':
                    ###########################################################################################################################
                    #Convert asci to laz
                    #asciigridtolas(dtmlazfile)

                    print('Converting ASC to LAZ')

                    #files
                    time.sleep(1)
                    asc=output
                    las=os.path.join(proddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')

                    asciigridtolas(asc, las, filetype)
                    deletefiles.append(las)
                    

                    ###########################################################################################################################
                    #Index the product laz files
                    #index(demlazfile)

                    index(las)
                    lax=os.path.join(proddir,'{0}.lax'.format(tilename)).replace('\\','/')
                    deletefiles.append(lax)

            ###########################################################################################################################
            #Clipping the product las files to the AOI
            #lasclip demlazfile
            if clipshape:
                prodclippeddir = AtlassGen.makedir(os.path.join(proddir, 'clipped')).replace('\\','/')
                print('Clipping the las files to AOI')

                for aoi in aoifiles:

                    path, aoiname, ext = AtlassGen.FILESPEC(aoi)
                    print('Clipping files to the AOI : {0}'.format(aoi))
                    aoidir = AtlassGen.makedir(os.path.join(prodclippeddir,aoiname))

                    print(tilename)


                    #files 
                    lasinput=os.path.join(proddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') #dtmlaz
                    lasoutput = os.path.join(aoidir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            
                    clip(lasinput, lasoutput, aoi, filetype)

                    if os.path.isfile(lasoutput):
                        deletefiles.append(lasoutput)
                        print('Converting Clipped {0} to asc'.format(filetype))
                    
                        #############################################################################################################################
                        #Convert the laz files to asci
                        #lasgrid
                        #TODo
                        #files

                        ascoutput=os.path.join(aoidir,'{0}{1}-GRID_{2}_{3}_{4}m.asc'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')
                        prjfile1 = os.path.join(aoidir,'{0}{1}-GRID_{2}_{3}_{4}m.prj'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')

                        lastoasciigrid(int(xmin), int(ymin), lasoutput, ascoutput, int(tilesize), step)
                        product_files.append(ascoutput)
                        product_files.append(prjfile1)
                        shutil.copyfile(prjfile, prjfile1) 
            

            else:
                print("Finished making products. No clipping selected")
    
        
        else:
            print("{0} file not created for {1}".format(product, tilename))
            return(True,tilename,"{0} file not created for {1}".format(product, tilename))


        print("-----------------Copying product files -----------------")
        for sourcef in product_files:

            destf = sourcef.replace(proddir, proddir_out)
            path,df,ext = AtlassGen.FILESPEC(destf)
            if not os.path.exists(path):
                AtlassGen.makedir(path)
            
            print("copying {0}\n".format(sourcef))
            try:
                shutil.copy(sourcef, destf)
            except Exception as e:
                print ("Unable to copy file.{0}".format(e))
            finally:
                print('deleting {0}'.format(sourcef))
                os.remove(sourcef)
                
    print("-------------------------------------------------------")
    if not (merged or makeFCM):         
        for deletef in deletefiles:
            print('Deleting {0}'.format(deletef))
            if os.path.isfile(deletef):
                os.remove(deletef)

    log = "Finished making products. No clipping selected"
    return(True,tilename,log)                
    
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support() 
    args = param_parser()

    #create variables from gui
    inputfolder = args.inputpath
    inputfolder = inputfolder.replace('\\','/')
    if not args.outputpath==None:
        outputpath=args.outputpath
        outputpath=outputpath.replace('\\','/')
    else:
        outputpath = args.workpath
    workingpath = args.workpath
    workingpath = workingpath.replace('\\','/')
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
    merged=args.merged
    cores = args.cores
    filetype = args.filetype
    aoifiles = args.aoifiles.split(';')
    epsg = args.epsg
    projname = args.projectname
    makeFCM = args.makeFCM

    tilelayout = AtlassTileLayout()
    lasfiles = []
    filepattern = args.filepattern.split(';')
    print(filepattern[0])
    

    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')

    if not args.inputgeojsonfile == None:
        ingeojsonfile = args.inputgeojsonfile

    if not args.outputgeojsonfile == None:
        outgeojsonfile = args.outputgeojsonfile

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
    tl_in = AtlassTileLayout()
    tl_in.fromjson(ingeojsonfile)

    tl_out = AtlassTileLayout()
    tl_out.fromjson(outgeojsonfile)

    print("Merging : {0}".format(merged))
    print("Making DEMs for FCM : {0}".format(makeFCM))
    print("No of Tiles in Input Tilelayout : {0}".format(len(tl_in)))
    print("No of Tiles in Output Tilelayout : {0}".format(len(tl_out)))
    dt = strftime("%y%m%d_%H%M")

    outputdir = AtlassGen.makedir(os.path.join(outputpath, '{0}_makeGrid'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, '{0}_makeGrid_Working'.format(dt))).replace('\\','/')


    if clip:
        epsg = args.epsg
        link = "http://spatialreference.org/ref/epsg/{0}/prj/".format(epsg)
        prjfile2 = os.path.join(workingdir, '{0}.prj'.format(epsg)).replace("\\", "/")
        prjfile = urllib.request.urlretrieve(link, prjfile2)


    make_products = {}
    make_products_results = []
    
    ########################################################################################################################
    ## Make Products for tiles in the output tilelayout
    #######################################################################################################################

    for tile in tl_out: 
        xmin = tile.xmin
        ymin = tile.ymin
        xmax = tile.xmax
        ymax = tile.ymax
        tilename = tile.name
        tilesize = int(tile.xmax - tile.xmin)

        make_products[tilename] = AtlassTask(tilename, makeProductsperTile, tl_in, tl_out, xmin,ymin,xmax,ymax,tilename,tilesize,productlist,inputfolder,workingdir,outputdir,filetype,hydropointsfiles,buffer,nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeHYDRO, makeCHM, step, chmstep,kill,clipshape,aoifiles,prjfile2,merged,projname,makeFCM)
        #makeProductsperTile(tl_in, tl_out, xmin,ymin,xmax,ymax,tilename,tilesize,productlist,inputfolder,workingdir,outputdir,filetype,hydropointsfiles,buffer,nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeHYDRO, makeCHM, step, chmstep,kill,clipshape,aoifiles,prjfile2)
    
    print(len(make_products))
    p=Pool(processes=cores)        
    make_products_results=p.map(AtlassTaskRunner.taskmanager,make_products.values())   

    ########################################################################################################################
    ## Merge files
    #######################################################################################################################

    for result in make_products_results:
        log.write(result.log)
    print("-------------Finished making DEMS, starting other functions--------------------------")
    if merged and not clipshape:

        print("Starting to Merge files without clipping")
        buffdir = os.path.join(workingdir, 'buffered').replace('\\','/')
        shutil.rmtree(buffdir)

        for product in productlist:
            proddir = os.path.join(workingdir, product).replace('\\','/')
            proddir_dest = os.path.join(outputdir,product).replace('\\','/')

            print('Merging {0} files'.format(product))

            mergeddir = AtlassGen.makedir(os.path.join(proddir, 'merged')).replace('\\','/')
            mergeddir_dest = AtlassGen.makedir(os.path.join(proddir_dest, 'merged')).replace('\\','/')
            mergedlasfile = os.path.join(mergeddir,"merged_{0}.{1}".format(product,filetype)).replace('\\','/')
            mergedascfile = os.path.join(mergeddir,"merged_{0}.asc".format(product)).replace('\\','/')
            copy_file = os.path.join(mergeddir_dest,"merged_{0}.asc".format(product)).replace('\\','/')
            
            merge_product(proddir,mergedlasfile,mergedascfile,step,filetype)

            if os.path.isfile(mergedascfile):
                shutil.copy(mergedascfile,copy_file)
                print('Merged File copied {0}'.format(mergedascfile))
            else:
                print('No merged .asc file to copy')

    if merged and clipshape: 

        print("Starting to Merge files")
        buffdir = os.path.join(workingdir, 'buffered').replace('\\','/')
        shutil.rmtree(buffdir)

        for product in productlist:
            proddir = os.path.join(workingdir, product).replace('\\','/')
            proddir_dest = os.path.join(outputdir,product).replace('\\','/')
            prodclippeddir = AtlassGen.makedir(os.path.join(proddir, 'clipped')).replace('\\','/')
            prodclippeddir_dest = AtlassGen.makedir(os.path.join(proddir_dest, 'clipped')).replace('\\','/')
			
            for aoi in aoifiles:

                path, aoiname, ext = AtlassGen.FILESPEC(aoi)
                print('Merging {0} files for AOI : {1}'.format(product,aoiname))
                aoidir = AtlassGen.makedir(os.path.join(prodclippeddir,aoiname)).replace('\\','/')
                aoidir_dest = AtlassGen.makedir(os.path.join(prodclippeddir_dest,aoiname)).replace('\\','/')
                mergeddir = AtlassGen.makedir(os.path.join(aoidir, 'merged')).replace('\\','/')
                mergeddir_dest = AtlassGen.makedir(os.path.join(aoidir_dest, 'merged')).replace('\\','/')
                mergedlasfile = os.path.join(mergeddir,"merged_{0}_{1}.{2}".format(product,aoiname,filetype)).replace('\\','/')
                mergedascfile = os.path.join(mergeddir,"merged_{0}_{1}.asc".format(product,aoiname)).replace('\\','/')
                copy_file = os.path.join(mergeddir_dest,"merged_{0}_{1}.asc".format(product,aoiname)).replace('\\','/')
       
                merge_product(aoidir,mergedlasfile,mergedascfile,step,filetype)
            
                if os.path.isfile(mergedascfile):
                    print('Copying {1} Merged file for AOI : {0}'.format(aoiname, product))
                    shutil.copy(mergedascfile,copy_file)
                    if os.path.isfile(copy_file):
                        print('Merged  {1} file copied for AOI : {0}\n\n'.format(aoiname, product))
                else:
                    print('No {1} merged file to copy for AOI : {0}\n\n'.format(aoiname, product))    

    return()
    
if __name__ == "__main__":
    main(sys.argv[1:]) 

