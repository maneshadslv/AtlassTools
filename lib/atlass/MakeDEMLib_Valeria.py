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
from MakeDEMLib_Valeria import *


class DEMClass():
        

    def makeDEMperTile(tilename,inputdir,outputdir,workingdir,hydropoints,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,gndclass,buffer,kill,step,clipp,aois):

        #workingdir = AtlassGen.makedir(os.path.join(workingdir, 'makeGRID_working')).replace('\\','/')

        #read tilelayout into library
        tl_in = AtlassTileLayout()
        tl_in.fromjson(inputgeojsonfile)

        tl_out = AtlassTileLayout()
        tl_out.fromjson(outputgeojsonfile)
        
        cleanup = []

        buff_dir = AtlassGen.makedir(os.path.join(workingdir, 'buffered')).replace('\\','/')
        workingdir = AtlassGen.makedir(os.path.join(workingdir, 'DEM_{0}'.format(step))).replace('\\','/')
        buffFile = os.path.join(buff_dir,'{0}.{1}'.format(tilename,filetype)).replace('\\','/')

        DEMoutputdir =  AtlassGen.makedir(os.path.join(outputdir, 'DEM_{0}'.format(step))).replace('\\','/')
        outputfile = os.path.join(DEMoutputdir,'{0}.asc'.format(outputfilename)).replace('\\','/')

        tile = tl_out.gettile(tilename)
  
        tilesize = int(int(tile.xmax) - int(tile.xmin))

        inputfile = AtlassGen.bufferTile(tile,tl_in,buffFile,buffer,[2,8],inputdir,filetype)[1]
    
        keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
        keep=keep.split()
        print('Making DEM for : {0}'.format(tilename))
        log = ''
        print(hydropoints)

        
        try:
            #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
            print("Checking for Hydro files")
            if not hydropoints==None:
                hydfile=os.path.join(workingdir,'{0}_hydro.laz'.format(tilename)).replace('\\','/')
                cleanup.append(hydfile)
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + hydropoints + ['-merged','-olaz','-o', hydfile] + keep 
                subprocessargs=list(map(str,subprocessargs))
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
                print("clipped Hydro points")

                tempinput = inputfile
                inputfile=os.path.join(workingdir,'{0}_dem_hydro.laz'.format(tilename)).replace('\\','/')
                cleanup.append(inputfile)
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i', tempinput, hydfile,'-merged','-olaz','-o',inputfile] + keep 
                subprocessargs=list(map(str,subprocessargs))
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
                print("added Hydro points")

            else:
                print("No Hydro files")
            

            print(inputfile)
            print("DEM starting")
            subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',inputfile,'-oasc','-o', outputfile,'-nbits',32,'-kill',kill,'-step',step,'-keep_class']+ gndclass
            subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]    
            #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
            subprocessargs=list(map(str,subprocessargs))  
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            if clipp:
                cleanup.append(outputfile)
                asclaz = os.path.join(workingdir,'{0}.laz'.format(outputfilename)).replace('\\','/')
                asclax = asclaz.replace('.laz','.lax')
                AtlassGen.asciigridtolas(outputfile, asclaz , 'laz')
                cleanup.append(asclaz)
                cleanup.append(asclax)

                AtlassGen.index(asclaz)

                for aoi in aois:
                    pathn, aoiname,ext = AtlassGen.FILESPEC(aoi)
                    print(aoiname)
                    aoidir = AtlassGen.makedir(os.path.join(workingdir, 'Clipped_1000m').replace('\\','/'))
                    aoioutdir = AtlassGen.makedir(os.path.join(DEMoutputdir, 'Clipped_1000m').replace('\\','/'))
                    clippedlaz = os.path.join(aoidir,'{0}_clipped.laz'.format(outputfilename)).replace('\\','/')

                    cleanup.append(clippedlaz)
                    
                    AtlassGen.clip(asclaz, clippedlaz, aoi, 'laz')

                    finalasc = os.path.join(aoioutdir,'{0}.asc'.format(outputfilename))
                    AtlassGen.lastoasciigrid(tile.xmin,tile.ymin,clippedlaz, finalasc, tilesize, step)
        


        except subprocess.CalledProcessError as suberror:

            log="{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)
    
    
        except:
            print('{0}: DEM output FAILED.'.format(tilename))
            print(log)
            log = 'DEM creation Failed for {0} at Subprocess.'.format(tilename)+log
            return(False, None, log)
    
    
        finally:
            if os.path.isfile(outputfile):               
                log = 'DEM output Success for: {0}'.format(tilename)+log
                for file in cleanup:
                    try:
                        if os.path.isfile(file):
                            os.remove(file)   
                    except:
                        print('cleanup FAILED.') 
                    print('Cleaning Process complete')
                return(True, outputfile, log)
            else:
                log = 'DEM creation Failed for: {0}'.format(tilename)+log
                return(False, None, log)

class DSMClass():

    def makeDSMperTile(tilename,inputdir,outputdir,workingdir,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,nongndclasses,buffer,kill,step,clipp,aois):

        #read tilelayout into library
        tl_in = AtlassTileLayout()
        tl_in.fromjson(inputgeojsonfile)

        tl_out = AtlassTileLayout()
        tl_out.fromjson(outputgeojsonfile)
        
        tile = tl_out.gettile(tilename)
        tilesize = int(tile.xmax - tile.xmin)

        print(nongndclasses)
        
        #workingdir = AtlassGen.makedir(os.path.join(workingdir, 'makeGRID_working')).replace('\\','/')
        buffered_dir = os.path.join(workingdir, 'buffered').replace('\\','/')
        buffered_inputfile = os.path.join(buffered_dir, '{0}_dsm.{1}'.format(tilename,filetype)).replace('\\','/')
        demfile = os.path.join(outputdir, 'DEM_{1}/Clipped_1000m/{0}.asc'.format(outputfilename,step)).replace('\\','/')
        print(demfile)


        inputfile = AtlassGen.bufferTile(tile,tl_in,buffered_inputfile,buffer,nongndclasses,inputdir,filetype)[1]


        DSMoutputdir =  AtlassGen.makedir(os.path.join(outputdir, 'DSM_{0}'.format(step))).replace('\\','/')
        DSMworkdir = AtlassGen.makedir(os.path.join(workingdir, 'DSM_{0}'.format(step))).replace('\\','/')
        outputfile = os.path.join(DSMoutputdir,'{0}.asc'.format(outputfilename)).replace('\\','/')



        print('DSM Starting')
        cleanup=[]
        log = ''
        
        print(inputfile)
  
        
        try:

            #Makes the dsm grid
            dsmgridfile = os.path.join(DSMworkdir,'{0}_dsm_grid.asc'.format(tilename)).replace('\\','/')
            cleanup.append(dsmgridfile)
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', inputfile,'-oasc','-o',dsmgridfile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-highest','-first_only','-subcircle',step/4]
            subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step),'-keep_class']+ nongndclasses
            subprocessargs=list(map(str,subprocessargs))
            #print(list(subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            cleanup.append(dsmgridfile)
            #Merge dsm grid and dem grid 


            if os.path.exists(demfile):
                dem=AsciiGrid()
                dem.readfromfile(demfile)
        
            else:
                print("DSM : could not find the DEM file for {0}".format(demfile))
            dsm=AsciiGrid()
            dsm.readfromfile(dsmgridfile)
        
            # creates grids containing ones, zeros or no data.
            ones=np.array(np.ones((dem.grid.shape[0],dem.grid.shape[1])), ndmin=2, dtype=int)
            zeros=np.array(np.zeros((dem.grid.shape[0],dem.grid.shape[1])), ndmin=2, dtype=int)    
            nodata=np.array(np.ones((dem.grid.shape[0],dem.grid.shape[1])), ndmin=2, dtype=int)*dem.nodata_value   
        
            # extract dsm nodata areas
            dsm_nodata=ones*(dsm.grid==dsm.nodata_value)
        
            #create new output dsm grid
            dsm_output=AsciiGrid() 
            dsm_output.header=dsm.header
        
            #outputting voids as value 1
            dsm_output.grid=np.where(dsm_nodata==1,dem.grid,dsm.grid)
        
            dsm_output.savetofile(outputfile)

            if clipp:
                cleanup.append(outputfile)
                asclaz = os.path.join(DSMworkdir,'{0}.laz'.format(outputfilename)).replace('\\','/')
                asclax = asclaz.replace('.laz','.lax')
                AtlassGen.asciigridtolas(outputfile, asclaz , 'laz')
                cleanup.append(asclaz)
                cleanup.append(asclax)

                AtlassGen.index(asclaz)

                for aoi in aois:
                    pathn, aoiname,ext = AtlassGen.FILESPEC(aoi)
                    print(aoiname)
                    aoidir = AtlassGen.makedir(os.path.join(DSMworkdir, 'Clipped_1000m').replace('\\','/'))
                    aoioutdir = AtlassGen.makedir(os.path.join(DSMoutputdir, 'Clipped_1000m').replace('\\','/'))
                    clippedlaz = os.path.join(aoidir,'{0}_clipped.laz'.format(outputfilename)).replace('\\','/')

                    cleanup.append(clippedlaz)
                    
                    AtlassGen.clip(asclaz, clippedlaz, aoi, 'laz')

                    finalasc = os.path.join(aoioutdir,'{0}.asc'.format(outputfilename))
                    AtlassGen.lastoasciigrid(tile.xmin,tile.ymin,clippedlaz, finalasc, tilesize, step)
        
        except subprocess.CalledProcessError as suberror:
            log=log + "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)


        except:
            print('{0}: DSM output FAILED.'.format(tilename))
            log = 'DSM creation Failed for {0} at Subprocess.'.format(tilename)
            return(False, None, log)


        finally:
            if os.path.isfile(finalasc):
                
                log = 'DSM output Success for: {0}.'.format(tilename)
                for file in cleanup:
                    try:
                        if os.path.isfile(file):
                            os.remove(file)   
                    except:
                        print('cleanup FAILED.') 
                    print('Cleaning Process complete')
                return(True, outputfile, log)
            else:
                log = 'DSM creation Failed for: {0}.'.format(tilename)
                return(False, None, log)
        
if __name__ == '__main__':
    #python C:/AtlassTools/lib/atlass/MakeDEMLib.py #name# D:\temp\Test_TL D:\temp\Test_TL D:\temp\Test_TL None "D:\temp\Test_TL\TileLayout_18.json" "D:\temp\Test_TL\TileLayout_18.json" "laz" #name# 200 200 1 'DEM'
    #python.exe C:/AtlassTools/lib/atlass/MakeDEMLib.py #name# D:/Processing_Data/TMR/MR102092/retiled/190613_1545_MGA94-56_1000m_tiles D:/Processing_Data/TMR/MR102092 D:/Processing_Data/TMR/MR102092 None D:/Processing_Data/TMR/MR102092/retiled/190613_1545_MGA94-56_1000m_tiles/tilelayout/TileLayout.json "D:/Processing_Data/TMR/MR102092/ouput - Copy.json" laz Test_#name# "200" "200" "1" DEM
    #python.exe C:/AtlassTools/lib/atlass/MakeDEMLib.py #name# D:/Processing_Data/TMR/MR102092/retiled/190613_1545_MGA94-56_1000m_tiles D:/Processing_Data/TMR/MR102092 D:/Processing_Data/TMR/MR102092 None D:/Processing_Data/TMR/MR102092/retiled/190613_1545_MGA94-56_1000m_tiles/tilelayout/TileLayout.json "D:/Processing_Data/TMR/MR102092/ouput - Copy.json" laz Test_#name# "200" "200" "1" DSM
    gndclass = [2,8]
    nongndclasses = "1 3 4 5 6 10 13 14 15"
    clip = True

    print(sys.argv[1:])

    print('Number of variables provided : {0}'.format(print(len(sys.argv))))
    if sys.argv[13] == "DEM":
        tilename,inputdir,outputdir,workingdir,hydropoints,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,buffer,kill,step = sys.argv[1:13]
        aois = sys.argv[14:]

        if len(aois) == 0:
            clip = False
        else:
            clip = True

        if hydropoints == "None":
            hydrofiles = None
        else:
            hydrofiles = hydropoints

        demresults = DEMClass.makeDEMperTile(tilename,inputdir,outputdir,workingdir,hydrofiles,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,gndclass,int(buffer),int(kill),int(step),clip,aois)


    if sys.argv[13] == "DSM":
        tilename,inputdir,outputdir,workingdir,hydropoints,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,buffer,kill,step = sys.argv[1:13]
        aois = sys.argv[14:]
   
        if len(aois) == 0:
            clip = False
        else:
            clip = True

        if hydropoints == "None":
            hydrofiles = None
        else:
            hydrofiles = hydropoints

        if sys.argv[13] == "DSM":
            demresults = DEMClass.makeDEMperTile(tilename,inputdir,outputdir,workingdir,hydrofiles,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,gndclass,int(buffer),int(kill),int(step),clip,aois)
            dsmresults = DSMClass.makeDSMperTile(tilename,inputdir,outputdir,workingdir,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,nongndclasses,int(buffer),int(kill),int(step),clip,aois)

    else:
        print("Please check command line arguments provided.")