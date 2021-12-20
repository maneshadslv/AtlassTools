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
import scipy
from scipy import misc
from scipy.interpolate import griddata
from scipy.ndimage import morphology
from scipy.ndimage import filters
from gooey import Gooey, GooeyParser
import datetime
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile
#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 08/05/2019 -Alex Rixon - Original development Alex Rixon
# 
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#Tool is designed to copy data to local drive, process products and prepare delivery and achive datasets for DPIPWE
#-----------------------------------------------------------------------------------------------------------------

        
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


class Hydro():
    def newmakeHydroperTile(tilename,laspath,deliverypath,workingpath,tilelayout,areaname,aoi,filetype,buffer,step,kill,hydropoints):

        cleanupfiles=[]
        cleanupfolders=[]

        dempath = AtlassGen.makedir(os.path.join(deliverypath, 'DEM').replace('\\','/'))

        tly =  AtlassTileLayout()
        tly.fromjson(tilelayout)

        tile = tly.gettile(tilename)

        #set up workspace
        print('Settin up workspace')
        originaltiles=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/Original_LAS_tiles'.format(areaname,tile.name)))
        cleanupfolders.append(originaltiles)
        cleanupfolders.append(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile.name)))
    

        # Get overlapping tiles in buffer
        print("Getting Neighbours")
        neighbours=tile.getneighbours(buffer)

        print('{0} Neighbours detected'.format(len(neighbours)))
        print('Copying to workspace')


        mergedlas=os.path.join( os.path.join(workingpath,'{0}/{1}'.format(areaname,tile.name)),'{0}.laz'.format(tile.name))
        #if os.path.isdir(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile))):
        #    return
        cleanupfiles.append(mergedlas)

        # Copy to workspace
        for neighbour in neighbours:
            source =  os.path.join(laspath,'{0}.{1}'.format(neighbour,filetype))
            dest =  originaltiles
            shutil.copy2(source,dest)
            if os.path.isfile(os.path.join(dest,'{0}.{1}'.format(neighbour,filetype))):
                print('{0}.{1} copied.'.format(neighbour,filetype))
                cleanupfiles.append(os.path.join(dest,'{0}.{1}'.format(neighbour,filetype)))       
            else:
                print('{0}.{1} file not copied.'.format(neighbour,filetype))
        # Create merged
        print("Making buffered las file")


        #excluding water, noise and low veg
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(originaltiles,filetype),'-merged','-olaz','-o',mergedlas,'-keep_class'] + [0,1,2,4,5,6,8,10,13,14,15]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)     
        
        if os.path.isfile(mergedlas):
            print('buffered file created')
            cleanupfiles.append(mergedlas)
        else:
            print('buffered file not created')
            return


        #make a dsm grid for lowest elevation using subcircle and fill - clip to tile
        print("Making hydro grid1")
        dsmtempfile1=mergedlas.replace('.laz','_HYDRO.asc')
        cleanupfiles.append(dsmtempfile1)
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-oasc','-o',dsmtempfile1,'-nbits',32,'-elevation_lowest','-step',step,'-subcircle',step,'-fill',1]
        subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tile.xmax-tile.xmin)/step), '-nrows',math.ceil((tile.ymax-tile.ymin)/step)]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)    

        deminput=[mergedlas]

        print(hydropoints, mergedlas)
        if not hydropoints==None:
            hydro=dsmtempfile3=mergedlas.replace('.laz','_hydro.laz').replace('\\','/')
            try:
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydropoints,'-olaz','-o',hydro,'-set_classification'] + [2]
                subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer*3,tile.ymin-buffer*3,tile.xmax+buffer*3,tile.ymax+buffer*3]
                subprocessargs=map(str,subprocessargs)     
                print(list(subprocessargs))   
                subprocess.call(subprocessargs)     
                deminput.append(hydro)
            except subprocess.CalledProcessError as suberror:
                log="{0}\n".format(suberror.stdout)
                print(log)

            except:
                log ='Making hydro Failed at exception for : {0}'.format(tile.name)
                print(log)

            finally:
                if not os.path.isfile(hydro):
                    print('{0} not generated'.format(hydro))

        #make a dsm grid for triangulated elevation - clip to tile
        print("Making DEM grid")
        dsmtempfile3=mergedlas.replace('.laz','_DEM.asc')
        cleanupfiles.append(dsmtempfile3)
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i']+deminput+['-merged','-oasc','-o',dsmtempfile3,'-nbits',32,'-step',step,'-kill',kill,'-keep_class'] + [2]
        subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tile.xmax-tile.xmin)/step), '-nrows',math.ceil((tile.ymax-tile.ymin)/step)]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)   

        #test if dem tile contains no data.
        if os.path.isfile(dsmtempfile3):
            a=AsciiGrid()
            a.readfromfile(dsmtempfile3)     

            ones=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)
            zeros=np.array(np.zeros((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)    
            nodata=np.array(np.ones((a.grid.shape[0],a.grid.shape[1])), ndmin=2, dtype=int)*a.nodata_value   

            demvoids=ones*(a.grid==a.nodata_value) #return a grid of ones and zeros
            if True: #not demvoids.all()==zeros.all() and not not demvoids.all()==zeros.all():
                #contains some nodata pixels

                #NEW addition - Fill function
                print("Fill function")
                dsmtempfile4=mergedlas.replace('.laz','_DEM_filled.asc')
                #cleanupfiles.append(dsmtempfile4)
                subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',dsmtempfile3,'-step', step, '-elevation_lowest', '-fill', 2, '-o', dsmtempfile4]           
                subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tile.xmax-tile.xmin)/step), '-nrows',math.ceil((tile.ymax-tile.ymin)/step)]
                subprocessargs=map(str,subprocessargs)        
                subprocess.call(subprocessargs)   
                if os.path.isfile(dsmtempfile4):
                    dsmtempfile3=dsmtempfile4

            #extract dem heights
            a=AsciiGrid()
            b=AsciiGrid()   

            #Void File
            a.readfromfile(dsmtempfile1) 
            #DEM file    
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
            hydrovoidfile=mergedlas.replace('.laz','_HYDRO_Voids.asc')
            hydrovoids_dem.savetofile(hydrovoidfile)     
            cleanupfiles.append(hydrovoidfile)

            #outputting voids with dem heights
            hydrovoids_dem.grid=np.where(hydrovoids==1,b.grid,nodata)
            hydrovoidfile=mergedlas.replace('.laz','_HYDRO_Voids_Height.asc')
            hydrovoids_dem.savetofile(hydrovoidfile)         
            cleanupfiles.append(hydrovoidfile)
            
            hydrovoidfilelaz=mergedlas.replace('.laz','_HYDRO_Voids_Height.laz')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydrovoidfile,'-olaz','-o',hydrovoidfilelaz,'-rescale',0.001,0.001,0.001]
            subprocessargs=map(str,subprocessargs)        
            subprocess.call(subprocessargs)    
            cleanupfiles.append(hydrovoidfilelaz)
            log =''
            
            try:
                hydrovoidfilelazClipped=os.path.join(deliverypath,'{0}_HYDRO_Voids_Height_Clipped.laz'.format(tile.name)).replace('\\','/')
                print(hydrovoidfilelazClipped)
                subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i',hydrovoidfilelaz,'-merged', '-poly', aoi, '-o', hydrovoidfilelazClipped, '-olaz']
                subprocessargs=list(map(str,subprocessargs))    
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            
            except subprocess.CalledProcessError as suberror:
                log=log +'\n'+ "{0}\n".format(suberror.stdout)
                print(log)
                pass

            except:
                log = 'Could not make grid {0}, Failed at Subprocess'.format(str(tilename))  
                pass
                    
        #Copy dem for later use.
        destdem =  os.path.join(dempath,'{0}.asc'.format(tile.name))
        shutil.copy2(dsmtempfile3,destdem)


        # clean up workspace
        print("Cleaning")
        for file in cleanupfiles:
            if os.path.isfile(file):
                os.remove(file)
                print('file: {0} removed.'.format(file))
                pass
            else:
                print('file: {0} not found.'.format(file))
        
        for folder in cleanupfolders:
            if os.path.isdir(folder):
                shutil.rmtree(folder, ignore_errors=True)
                pass
        
        return(True,tilename,"Complete")

    def makeHydroperTile(tilename,laspath,deliverypath,workingpath,tilelayout,areaname,aoi,filetype,buffer,step,kill,hydropoints):

        cleanupfiles=[]
        cleanupfolders=[]

        tly =  AtlassTileLayout()
        tly.fromjson(tilelayout)

        tile = tly.gettile(tilename)

        #set up workspace
        print('Settin up workspace')
        originaltiles=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/Original_LAS_tiles'.format(areaname,tile.name)))
        cleanupfolders.append(originaltiles)
        cleanupfolders.append(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile.name)))
    

        # Get overlapping tiles in buffer
        print("Getting Neighbours")
        neighbours=tile.getneighbours(buffer)

        print('{0} Neighbours detected'.format(len(neighbours)))
        print('Copying to workspace')


        mergedlas=os.path.join( os.path.join(workingpath,'{0}/{1}'.format(areaname,tile.name)),'{0}.laz'.format(tile.name))
        #if os.path.isdir(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile))):
        #    return
        cleanupfiles.append(mergedlas)

        # Copy to workspace
        for neighbour in neighbours:
            source =  os.path.join(laspath,'{0}.{1}'.format(neighbour,filetype))
            dest =  originaltiles
            shutil.copy2(source,dest)
            if os.path.isfile(os.path.join(dest,'{0}.{1}'.format(neighbour,filetype))):
                print('{0}.{1} copied.'.format(neighbour,filetype))
                cleanupfiles.append(os.path.join(dest,'{0}.{1}'.format(neighbour,filetype)))       
            else:
                print('{0}.{1} file not copied.'.format(neighbour,filetype))
        # Create merged
        print("Making buffered las file")


        #excluding water, noise and low veg
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(originaltiles,filetype),'-merged','-olaz','-o',mergedlas,'-keep_class'] + [0,1,2,4,5,6,8,10,13,14,15]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)     
        
        if os.path.isfile(mergedlas):
            print('buffered file created')
            cleanupfiles.append(mergedlas)
        else:
            print('buffered file not created')
            return


        #make a dsm grid for lowest elevation using subcircle and fill - clip to tile
        print("Making hydro grid1")
        dsmtempfile1=mergedlas.replace('.laz','_HYDRO.asc')
        cleanupfiles.append(dsmtempfile1)
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-oasc','-o',dsmtempfile1,'-nbits',32,'-elevation_lowest','-step',step,'-subcircle',step,'-fill',1]
        subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tile.xmax-tile.xmin)/step), '-nrows',math.ceil((tile.ymax-tile.ymin)/step)]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)    

        deminput=[mergedlas]

        print(hydropoints, mergedlas)
        if not hydropoints==None:
            hydro=dsmtempfile3=mergedlas.replace('.laz','_hydro.laz').replace('\\','/')
            try:
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydropoints,'-olaz','-o',hydro,'-set_classification'] + [2]
                subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer*3,tile.ymin-buffer*3,tile.xmax+buffer*3,tile.ymax+buffer*3]
                subprocessargs=map(str,subprocessargs)     
                print(list(subprocessargs))   
                subprocess.call(subprocessargs)     
                deminput.append(hydro)
            except subprocess.CalledProcessError as suberror:
                log="{0}\n".format(suberror.stdout)
                print(log)
                

            except:
                log ='Making MKP Failed at exception for : {0}'.format(tile.name)
                print(log)

            finally:
                if not os.path.isfile(hydro):
                    print('{0} not generated'.format(hydro))

        #make a dsm grid for triangulated elevation - clip to tile
        print("Making DEM grid")
        dsmtempfile3=mergedlas.replace('.laz','_DEM.asc')
        cleanupfiles.append(dsmtempfile3)
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i']+deminput+['-merged','-oasc','-o',dsmtempfile3,'-nbits',32,'-step',step,'-kill',kill,'-keep_class'] + [2]
        subprocessargs=subprocessargs+['-ll',tile.xmin,tile.ymin,'-ncols',math.ceil((tile.xmax-tile.xmin)/step), '-nrows',math.ceil((tile.ymax-tile.ymin)/step)]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)   

 
        a=AsciiGrid()
        b=AsciiGrid()   

        #Void File
        a.readfromfile(dsmtempfile1) 
        #DEM file    
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
        hydrovoidfile=mergedlas.replace('.laz','_HYDRO_Voids.asc')
        hydrovoids_dem.savetofile(hydrovoidfile)     
        cleanupfiles.append(hydrovoidfile)

        #outputting voids with dem heights
        hydrovoids_dem.grid=np.where(hydrovoids==1,b.grid,nodata)
        hydrovoidfile=mergedlas.replace('.laz','_HYDRO_Voids_Height.asc')
        hydrovoids_dem.savetofile(hydrovoidfile)         
        cleanupfiles.append(hydrovoidfile)
        
        hydrovoidfilelaz=mergedlas.replace('.laz','_HYDRO_Voids_Height.laz')
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydrovoidfile,'-olaz','-o',hydrovoidfilelaz,'-rescale',0.001,0.001,0.001]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)    
        cleanupfiles.append(hydrovoidfilelaz)
        log =''
        try:
            hydrovoidfilelazClipped=os.path.join(deliverypath,'{0}_HYDRO_Voids_Height_Clipped.laz'.format(tile.name)).replace('\\','/')
            print(hydrovoidfilelazClipped)
            subprocessargs=['C:/LAStools/bin/lasclip64.exe', '-i',hydrovoidfilelaz,'-merged', '-poly', aoi, '-o', hydrovoidfilelazClipped, '-olaz']
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        
        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            pass

        except:
            log = 'Could not make grid {0}, Failed at Subprocess'.format(str(tilename))  
            pass

        
        # clean up workspace
        print("Cleaning")
        for file in cleanupfiles:
            if os.path.isfile(file):
                os.remove(file)
                print('file: {0} removed.'.format(file))
                pass
            else:
                print('file: {0} not found.'.format(file))

        for folder in cleanupfolders:
            if os.path.isdir(folder):
                shutil.rmtree(folder, ignore_errors=True)
                pass
    
        return(True,tilename,"Complete")


    #python C:\AtlassTools\MakeHYDRO_GRIDS.py --tile=#name# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --areaname=Bishopbourne --laspath=F:\Processing\Area01_Mary_GDA94MGA56\origtiles --tilelayout=F:\Processing\Area01_Mary_GDA94MGA56\origtiles\TileLayout.json --storagepath=W:\temp2\working\storage\NorthMidlands --workingpath=W:\temp2\working\working --deliverypath=W:\temp2\working\delivery\NorthMidlands --step=1.0 --extn=laz --buffer=250




