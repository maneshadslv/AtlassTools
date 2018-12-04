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

from Atlass import *


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
    main_parser.add_argument("lasfiles", metavar="LAS files", widget="MultiFileChooser", help="Select input las/laz file", default=" ")
    #main_parser.add_argument("geojsonfile", metavar="GoeJson file", widget="FileChooser", help="Select geojson file", default='D:\\Python\\Gui\\input\\TileLayout.json')
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=" ")
    product_group = main_parser.add_argument_group("Products", "Select Output Products", gooey_options={'show_border': True,'columns': 5})
    product_group.add_argument("-dtm", "--makeDTM", metavar="DTM", action='store_true', default=True)
    product_group.add_argument("-dem", "--makeDEM", metavar="DEM", action='store_true', default=True)
    product_group.add_argument("-dsm", "--makeDSM", metavar="DSM", action='store_true', default=True)
    product_group.add_argument("-hydro", "--makeHYDRO", metavar="Hydro", action='store_true')
    product_group.add_argument("-dhm", "--makeDHM", metavar="DHM", action='store_true')
    product_group.add_argument("-chm", "--makeCHM", metavar="CSM", action='store_true')
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-cs", "--chmstep",metavar="CHM step", help="Provide chmstep", type=float, default=2.0)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("--clipshape", metavar="Clip shape", help="Clip Shape", action='store_true', default=True)
    main_parser.add_argument("-c", "--classes",metavar="classes", help="Provide classes", default="2;8")
    main_parser.add_argument("-ngc", "--nongndclasses", metavar = "Non Ground Classes", default="1 3 4 5 6 10 13 14 15")
    main_parser.add_argument("-chmc", "--chmclasses", metavar = "CHM Classes", default="3 4 5")
    main_parser.add_argument("-gc", "--gndclasses", metavar = "Ground Classes", default="2 8")
    main_parser.add_argument("-hc", "--hydrogridclasses", metavar = "Hydro Grid Classes", default="2 4 5 6 8 10 13")
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    main_parser.add_argument("-k", "--kill",metavar="Kill", help="Kill after (s)", type=int, default=250)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    
    return main_parser.parse_args()

    
def MakeFiles(TILE,outpath, lasfiles, buffer, kill, step, chmstep, makeDTM, makeHYDRO, makeDSM, makeDEM, makeCHM, gndclasses, chmclasses, nongndclasses, hydrogridclasses, hydropoints):
    
    cleanup=[]
    outputtoqueue=[]

    #Prep RAW DTM
    print('Setting up folders :','Prepare Raw DTM')

    #files
    dtmfile=os.path.join(outpath,'{0}_dem.asc'.format(TILE.name)).replace('\\','/')
    print(dtmfile)
    gndfile=os.path.join(outpath,'{0}_dem.laz'.format(TILE.name)).replace('\\','/')
    cleanup.append(gndfile)
    
    dsmgridfile=os.path.join(outpath,'{0}_dsm_grid.asc'.format(TILE.name)).replace('\\','/')
    cleanup.append(dsmgridfile)
    
    dsmfile=os.path.join(outpath,'{0}_dsm.asc'.format(TILE.name)).replace('\\','/')
    
    dsmgridfile2=os.path.join(outpath,'{0}_dsm_grid2.asc'.format(TILE.name)).replace('\\','/')
    cleanup.append(dsmgridfile2)
    
    chmgridfile=os.path.join(outpath,'{0}_chm_grid.asc'.format(TILE.name)).replace('\\','/')
    cleanup.append(chmgridfile)
    
    chmdemgridfile=os.path.join(outpath,'{0}_chm_dem_grid.asc'.format(TILE.name)).replace('\\','/')
    cleanup.append(chmdemgridfile)
    
    chmfile=os.path.join(outpath,'{0}_chm.asc'.format(TILE.name)).replace('\\','/')

    #set up clipping
    keep='-keep_xy {0} {1} {2} {3}'.format(TILE.xmin-buffer,TILE.ymin-buffer,TILE.xmax+buffer,TILE.ymax+buffer)
    keep=keep.split()
    
    if not makeDTM==None:  
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #DEM
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        try:
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + lasfiles + ['-olaz','-o',gndfile,'-merged','-keep_class'] + gndclasses + keep #'-rescale',0.001,0.001,0.001,
            subprocessargs=list(map(str,subprocessargs))
            subprocess.call(subprocessargs)         
            
            #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
            if not hydropoints==None:
                gndfile2=gndfile
                gndfile=os.path.join(outpath,'{0}_dem_hydro.laz'.format(TILE.name)).replace('\\','/')
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile2, hydropoints,'-merged','-olaz','-o',gndfile] + keep 
                subprocessargs=list(map(str,subprocessargs))
                subprocess.call(subprocessargs)    
                print("added Hydro points")
            
            print("DEM starting")
            subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o',dtmfile,'-nbits',32,'-kill',kill,'-step',step] 
            subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/step), '-nrows',math.ceil((TILE.xmax-TILE.ymax)/step)]
            subprocessargs=map(str,subprocessargs)  
            subprocess.call(subprocessargs) 

            print(TILE.name+': DEM output.')
            outputtoqueue.append(TILE.name+': DEM output.')
            result = {"file":TILE.name, "state" :"Success", "output":list(outputtoqueue) }
            return 
        except:
            print(TILE.name+': DEM output FAILED.')
            outputtoqueue.append(TILE.name+': DEM output FAILED.')
            result = {"file":TILE.name, "state" :"Error", "output":list(outputtoqueue) }
        
    if not makeHYDRO==None: 
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #Hydro-flattening
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #Make hydro points grid with no interpolation
        try:
        
            hydrofile=os.path.join(outpath,'{0}_hydro_input.asc'.format(TILE.name)).replace('\\','/')
            hydrovoidfile=os.path.join(outpath,'{0}_hydro_voids.asc'.format(TILE.name)).replace('\\','/')
            hydromanhattan=os.path.join(outpath,'{0}_hydro_manhattan.asc'.format(TILE.name)).replace('\\','/')
            
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + lasfiles + ['-merged','-oasc','-o',hydrofile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-lowest','-subcircle',step]
            subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/step), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/step)] + ['-keep_class']+ hydrogridclasses
            subprocessargs=map(str,subprocessargs) 
            subprocess.call(subprocessargs)   
            
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
            
            print(TILE.name+': Hydro grid output.')
            outputtoqueue.append(TILE.name+': Hydro grid output.')
            result = {"file":TILE.name, "state" :"Success", "output":list(outputtoqueue) }
        except:
            print(TILE.name+': Hydro grid output FAILED.')
            outputtoqueue.append(TILE.name+': Hydro grid output FAILED.')
            result = {"file":TILE.name, "state" :"Error", "output":list(outputtoqueue) }
        
    if not makeDSM==None and not makeDEM==None: 
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #DSM
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #make dsm grid with no interpolation
        try:
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + lasfiles + ['-merged','-oasc','-o',dsmgridfile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-highest','-first_only','-subcircle',step/4]
            subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/step), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/step)] + ['-keep_class']+ nongndclasses
            subprocessargs=map(str,subprocessargs) 
            subprocess.call(subprocessargs)  


            #Merge dsm grid and dem grid
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + [dsmgridfile,dtmfile] + ['-merged','-oasc','-o',dsmfile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/step), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/step)]
            subprocessargs=map(str,subprocessargs)        
            subprocess.call(subprocessargs)  
           
            print(TILE.name+': DSM output.')
            outputtoqueue.append(TILE.name+': DSM output.')
            result = {"file":TILE.name, "state" :"Success", "output":list(outputtoqueue) }
        except:
            print(TILE.name+': DSM output FAILED.')
            outputtoqueue.append(TILE.name+': DSM output FAILED.')
            result = {"file":TILE.name, "state" :"Error", "output":list(outputtoqueue) }
            
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #DHM
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    #subtract dem from dsm grid height
    
    if not makeCHM==None and not makeDEM==None: 
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #CHM
        #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        #Make veg grid with no interpolation
        try:
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + lasfiles + ['-merged','-oasc','-o',chmgridfile,'-nbits',32,'-fill',0,'-step',chmstep,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/chmstep), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/chmstep)] + ['-keep_class']+ chmclasses
            subprocessargs=map(str,subprocessargs) 
            subprocess.call(subprocessargs)      
            
            subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o',chmdemgridfile,'-nbits',32,'-kill',kill,'-step',chmstep] 
            subprocessargs=subprocessargs+['-ll',TILE.xmin, TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/chmstep), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/chmstep)]
            subprocessargs=map(str,subprocessargs)    
            subprocess.call(subprocessargs)      

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
            
            print(TILE.name+': CHM output.')
            outputtoqueue.append(TILE.name+': CHM output.')
            result = {"file":TILE.name, "state" :"Success", "output":list(outputtoqueue) }
        except:
            print(TILE.name+': CHM output FAILED.')
            outputtoqueue.append(TILE.name+': CHM output FAILED.')
            result = {"file":TILE.name, "state" :"Error", "output":list(outputtoqueue) }
 
    
    
    #-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    try:
        for file in cleanup:
            if os.path.isfile(file):
                os.remove(file)
                pass
        print('cleanup complete.')        
    except:
        print('cleanup FAILED.') 
    #rescale','0.001','0.001','0.001'
    print('Cleaning Process complete')
    
    return (outputtoqueue)



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):

    args = param_parser()

    #create variables from gui
    outputpath=args.outputpath
    outoutpath=outputpath.replace('\\','/')
    buffer=float(args.buffer)
    lasfiles = []
    if not args.lasfiles==None:
        lasfiles=args.lasfiles
        lasfiles=args.lasfiles.replace('\\','/').split(';')
    hydropointsfiles=[]
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
    makeDTM=args.makeDTM
    makeHYDRO=args.makeHYDRO
    makeDSM=args.makeDSM
    makeDHM=args.makeDHM
    makeCHM=args.makeCHM
    makeDEM=args.makeDEM
    cores = args.cores
    geojsonfile = outoutpath + "/TileLayput.json"
    tilesize = 1000
    al = Atlasslogger(outoutpath)

    tilelayout = AtlassTileLayout()

    #make a tile layout index
    for file in lasfiles:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilelayout.addtile(name=filename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)
    
    outputfile = tilelayout.createGeojsonFile(geojsonfile)

    #read tilelayout into library
    tl = AtlassTileLayout()
    tl.fromjson(geojsonfile)

    TASKS = [] 
    for file in lasfiles: 

        al.PrintMsg('Creating tile neighbourhood for :'.format(file),'Reading tilelayout shapefile')
        path, filename, ext = AtlassGen.FILESPEC(file)
        tile = tl.gettile(filename)
        neighbourlasfiles = []

        try:
            neighbours = tile.getneighbours(buffer)

        except:
            al.PrintMsg("tile: {0} does not exist in geojson file".format(filename))

        al.PrintMsg('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,file),'Neighbourhood:')

        for neighbour in neighbours:
            neighbour = path +'/'+ neighbour + '.'+ ext
            if os.path.isfile(neighbour):
                al.PrintMsg(neighbour)
                neighbourlasfiles.append(neighbour)

        #MakeFiles(tile, outputpath, neighbourlasfiles, buffer, kill, step, chmstep, makeDTM, makeHYDRO, makeDSM, makeDEM, makeCHM, gndclasses, chmclasses, nongndclasses, hydrogridclasses, hydropointsfiles)
        TASKS.append((MakeFiles, (tile, outputpath, neighbourlasfiles, buffer, kill, step, chmstep, makeDTM, makeHYDRO, makeDSM, makeDEM, makeCHM, gndclasses, chmclasses, nongndclasses, hydrogridclasses, hydropointsfiles)))
    
    #Multithread runner task
    results=AtlassTaskRunner(cores,TASKS,'Making products', al, str(args)).results
    
    al.DumpLog()
        
    return
        
if __name__ == "__main__":
    main(sys.argv[1:]) 
