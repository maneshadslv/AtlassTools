#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import itertools
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import os, glob
import numpy as np
import io
import datetime
import time
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *






#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

cleanupfolders=[]

defaults={}
defaults['tile']=None #(delivery tile name)
defaults['tilelayout_1km']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/05_Product_generation/1km_delivery_tilelayout.json" #delivery tilelayout 
defaults['tilelayout_500m']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/04_Final_transformed_and_XYZ_adjusted/Master_storage_tilelayout/TileLayout.json" #storage tilelayout
defaults['workingpath']=None #location to process and store results
defaults['lazpath']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/04_Final_transformed_and_XYZ_adjusted/Current_merged_500m_delivery_ready_dataset" #location to process and store results
defaults['hydropoints']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/05_Product_generation/BrisbaneIpswichLiDAR2019/Synthetic_Hydro_LAZ/*.laz" #hydro points file for hydro flattening
defaults['geoid']="//10.10.10.142/processed_data/BR01280_Brisbane_to_Ipswich-DNRME/01_LiDAR/05_Product_generation/BrisbaneIpswichLiDAR2019/geoid/BNE_AG09_lastools_AHD_to_ELL.laz" #geoid from AHD to ELL

defaults['__keepfiles']=None

#constants
buffer=499
kill=1000
xorigin=436000
yorigin=6914000


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def PrintMsg(Message,Heading=False):
    if not Heading:
        msgstring='\t{0}'.format(Message)
        print(msgstring)
    else:
        msgstring='\n'
        msgstring=msgstring+'----------------------------------------------------------------------------\n'
        msgstring=msgstring+'{0}: {1}\n'.format(time.ctime(time.time()),Message)
        msgstring=msgstring+'----------------------------------------------------------------------------\n'
        print(msgstring)
        
    return msgstring + '\n'

def PrintHelp(defaults):
    PrintMsg('Below is an example of acceptable options and arguments:','Print help.')
    for arg in list(defaults.keys()):
        PrintMsg('\t--{0}={1}'.format(arg,defaults[arg]))
    print('----------------------------------------------------------------------------')


def getmostrecent(checkfolders,pattern):

    '''
    Searches through folders and creates a list of files patching a search pattern.
    File names are addded to a dictionary and tested for the most recent instance of each file.
    '''

    #dict to store name, size and date modified 
    #once processed will contain path to most recent
    filedict={}
    for folder in checkfolders:
        #make a list of files that match pattern

        files = glob.glob(os.path.join(folder,pattern))
        for filename in files:
            path,name=os.path.split(filename)
            mtime = os.path.getmtime(filename)
            if name in filedict.keys():
                #file already found
                filedict[name]['files'].append({'file':filename,'datemodified':mtime})
            else:
                #addfile
                filedict[name]={}
                filedict[name]['files']=[]
                filedict[name]['current']=''           
                filedict[name]['datemodified']=''   
                filedict[name]['files']=[{'file':filename,'datemodified':mtime}]

    for name,files in filedict.items():
        mostrectime=None
        for filerecord in files['files']:
            if mostrectime==None:
                mostrectime=filerecord['datemodified']
                mostrecfile=filerecord['file']
            else:
                if filerecord['datemodified']>mostrectime:
                    mostrectime=filerecord['datemodified']
                    mostrecfile=filerecord['file']

        return mostrecfile

def copyneighbourtiles(xmin,ymin,xmax,ymax,buffer,tilelayout,locations,outputfolder,prefix='',extn='.laz'):
    # Get overlapping tiles in buffer
    PrintMsg(Message="Getting Neighbours",Heading=True)
    neighbours=tilelayout.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    PrintMsg('{0} Neighbours detected'.format(len(neighbours)))
    PrintMsg('Copying to workspace')

    # Copy to workspace
    for neighbour in neighbours:
        source =  getmostrecent(locations,'{0}{1}{2}'.format(prefix,neighbour,extn))
        if source==None: 
            #no file found
            return
        source=source.replace('\\','/')
        dest =  outputfolder
        
        shutil.copy2(source,dest)
        if os.path.isfile(os.path.join(dest,'{0}{1}{2}'.format(prefix,neighbour,extn))):
            PrintMsg('{0} copied.'.format(source))
        else:
            PrintMsg('{0} file not copied.'.format(source))
    return



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------
    #python \\10.10.10.142\projects\PythonScripts\MakeBrisbaneIpswich.py --tile=#name# --workingpath=W:\temp2\working\working --hydropoints= --tilelayout_1km= --tilelayout_500m= --geoid=


    try:
        longargs=list('{0}='.format(key) for key in list(defaults.keys()))
        settings=defaults
        opts, args = getopt.getopt(argv,"h",["help"] + longargs)
    except getopt.GetoptError as err:
        # print help information and exit:
        PrintMsg(str(err),Heading=True)
        PrintHelp(defaults)
        sys.exit(2)
        
    PrintMsg('Setting arguments:',Heading=True)

    #Get options
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintHelp(longargs,defaults)
            sys.exit()
        elif opt.replace('-','') in list(defaults.keys()):
            PrintMsg('{0}={1}'.format(opt, arg))
            settings[opt.replace('-','')]=arg
        else:
            PrintHelp(defaults)
            sys.exit()

    #create variables from settings
    tile=settings['tile']
    if not tile==None:
        pass
    else:
        PrintMsg('tile not set')
        return

    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
        workingtiles=AtlassGen.makedir(os.path.join(workingpath,'workingtiles'))

        folders=[]
        folders.append('01_LAS_AHD')
        folders.append('02_LAS_Ellipsoid')
        folders.append('27_DSM_1m_GeoTiff')
        folders.append('28_DSM_1m_ASCII_XYZ')
        folders.append('29_DSM_1m_ASCII_ESRI')
        folders.append('30a_Non_HydroDEM_1m_GeoTiff')
        folders.append('30a_Non_HydroDSM_1m_GeoTiff')
        folders.append('30b_Non_HydroDEM_1m_ASCII_XYZ')
        folders.append('30b_Non_HydroDSM_1m_ASCII_XYZ')
        folders.append('30c_Non_HydroDEM_1m_ASCII_ESRI')
        folders.append('30c_Non_HydroDSM_1m_ASCII_ESRI')
        folders.append('31_DEM_1m_ASCII_XYZ')
        folders.append('32_DEM_1m_ASCII_ESRI')
        folders.append('32_DEM_1m_GeoTiff')
        folders.append('33_Contours')
        folders.append('51a_Flight_Trajectory')
        folders.append('51b_QA_Control')
        folders.append('51c_System_Calibration')
        folders.append('51d_Intensity_Image')
        folders.append('51_Metadata_Reports')
        folders.append('52_Tile_Layout')
        folders.append('Synthetic_Hydro_LAZ')

        for folder in folders:
            AtlassGen.makedir(os.path.join(workingpath,folder))
        pass
    else:
        PrintMsg('workingpath not set')
        return

    tilelayout_1km=settings['tilelayout_1km']
    if not tilelayout_1km==None:
        tilelayout_1km=tilelayout_1km.replace('\\','/')
        tilelayout_1km_tl = AtlassTileLayout()
        tilelayout_1km_tl.fromjson(tilelayout_1km)
        pass
    else:
        PrintMsg('tilelayout_1km not set')
        return

    tilelayout_500m=settings['tilelayout_500m']
    if not tilelayout_500m==None:
        tilelayout_500m=tilelayout_500m.replace('\\','/')
        tilelayout_500m_tl = AtlassTileLayout()
        tilelayout_500m_tl.fromjson(tilelayout_500m)        
        pass
    else:
        PrintMsg('tilelayout_500m not set')
        return

    hydropoints=settings['hydropoints']
    if not hydropoints==None:
        hydropoints=hydropoints.replace('\\','/')
        pass
    else:
        PrintMsg('hydropoints not set')
        return

    lazpath=settings['lazpath']
    if not lazpath==None:
        lazpath=lazpath.replace('\\','/')
        pass
    else:
        PrintMsg('lazpath not set')
        return

    geoid=settings['geoid']
    if not geoid==None:
        geoid=geoid.replace('\\','/')
        pass
    else:
        PrintMsg('currengeoidtversion not set')
        return

    __keepfiles=settings['__keepfiles']


    '''
    ----------------------------------------------------------------------------------------------
    preparation
    ----------------------------------------------------------------------------------------------
    copy tiles within buffer
    A. raw data tiled z adjusted tiles data
    B. most recent classified file for each input tile.

    prep A. by merging and classifying all points to class 0 within buffer of the tile extent.
    prep B. by merging within 2xbuffer of the tile extent.

    copy classification
    lascopy -i source.laz -i target.laz -classification -o result.laz
    check for class code 0
    ----------------------------------------------------------------------------------------------
    '''

    tileinfo=tilelayout_1km_tl.tiles[tile]
    xmin=tileinfo.xmin
    xmax=tileinfo.xmax
    ymin=tileinfo.ymin
    ymax=tileinfo.ymax

    #temp workspace for tile processing
    tempworkspace=AtlassGen.makedir(os.path.join(workingtiles,tile))
    
    '''
    ---------------------------------------------------------------------------------------------------------------------------------------
    original tiles
    ---------------------------------------------------------------------------------------------------------------------------------------
    '''
    #temp workspace for original tiles
    temporiginaltiles=AtlassGen.makedir(os.path.join(tempworkspace,'original_unclassifed'))
    copyneighbourtiles(xmin,ymin,xmax,ymax,buffer,tilelayout_500m_tl,[lazpath],temporiginaltiles,prefix='',extn='.laz')
    #add files to cleanup
    cleanupfolders.append(temporiginaltiles)

    #merge classified tiles with buffer 
    mergedoriginal=os.path.join(tempworkspace,'02_mergedoriginal.laz')
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(temporiginaltiles),'-merged','-olaz','-o',mergedoriginal,'-set_version','1.2','-epsg',28356]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    PrintMsg('merged original created -- {0}'.format(os.path.isfile(mergedoriginal)),Heading=True)


    cleanupfolders.append(tempworkspace)

    '''
    ----------------------------------------------------------------------------------------------
    products
    ----------------------------------------------------------------------------------------------
    '''
    

    #---------------------------------------------------------------------------------------
    #las ahd
    #---------------------------------------------------------------------------------------
    # 01_LAS_AHD
    las_ahd='SW_{0}_{1}_1k_class_AHD.las'.format(int(xmin),int(ymin))
    las_ahd=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'01_LAS_AHD')),las_ahd)
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',mergedoriginal,'-olas','-o',las_ahd,'-change_classification_from_to',10,17,'-change_classification_from_to',13,19,'-epsg',28356]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    PrintMsg('las_ahd created -- {0}'.format(os.path.isfile(las_ahd)),Heading=True)

    #---------------------------------------------------------------------------------------    
    #las ell - adjust using geoid
    #---------------------------------------------------------------------------------------
    # 02_LAS_Ellipsoid

    #prep geoid with 1000m tile buffer
    tilegeoid=os.path.join(tempworkspace,'geoid.laz')
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',geoid,'-olaz','-o',tilegeoid,'-set_version','1.2','-set_classification',0,'-epsg',28356]
    subprocessargs=subprocessargs+['-reoffset',xorigin,yorigin,0]
    subprocessargs=subprocessargs+['-keep_xy',xmin-1000,ymin-1000,xmax+1000,ymax+1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)
    PrintMsg('geoid created -- {0}'.format(os.path.isfile(tilegeoid)),Heading=True)

    las_ell='SW_{0}_{1}_1k_class_Ellipsoid.las'.format(int(xmin),int(ymin))
    las_ell=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'02_LAS_Ellipsoid')),las_ell)

    subprocessargs=['C:/LAStools/bin/lasheight64.exe','-i',las_ahd,'-olas','-o',las_ell,'-ground_points',tilegeoid, '-all_ground_points','-epsg',28356]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)
    PrintMsg('las_ell created -- {0}'.format(os.path.isfile(las_ell)),Heading=True)
    
    
    #---------------------------------------------------------------------------------------
    #intensity 1m (create 8 bit tiff and convert to ecw)
    #---------------------------------------------------------------------------------------
    # 51d_Intensity_Image
    # Intensity=SW_500000_6981000_1k_1m_Intensity_Image.ecw
    Intensity='SW_{0}_{1}_1k_1m_Intensity_Image.tif'.format(int(xmin),int(ymin))
    Intensity=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'51d_Intensity_Image')),Intensity)

    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedoriginal,'-otif','-nbits',8,'-o',Intensity,'-step',1,'-intensity_average','-first_only']
    subprocessargs=subprocessargs+['-set_min_max', 150 ,1800]
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('intensity created  -- {0}'.format(os.path.isfile(Intensity)),Heading=True)
    

    #---------------------------------------------------------------------------------------
    #non_hydro_flattened 1m dem in ascii grid, xyz and 32bit geotiff
    #---------------------------------------------------------------------------------------
    # 30c_Non_HydroDEM_1m_ASCII_ESRI
    # DEM_esri=SW_500000_6981000_1k_1m_ESRI_DEM.asc
    deminput=[mergedoriginal]

    DEM_esri='SW_{0}_{1}_1k_1m_ESRI_DEM.asc'.format(int(xmin),int(ymin))
    DEM_esri=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'30c_Non_HydroDEM_1m_ASCII_ESRI')),DEM_esri)

    subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i']+deminput+['-merged','-oasc','-nbits',32,'-o',DEM_esri,'-step',1,'-keep_class',2,19,'-kill',kill]
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DEM_esri created (no hydro) -- {0}'.format(os.path.isfile(DEM_esri)),Heading=True)

    demlaz=os.path.join(tempworkspace,'dem.laz')
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',DEM_esri,'-olaz','-rescale',0.001,0.001,0.001,'-o',demlaz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('demlaz created (no hydro) -- {0}'.format(os.path.isfile(demlaz)),Heading=True) 

    
    # 30a_Non_HydroDEM_1m_GeoTiff
    # DEM_tif32=SW_500000_6981000_1k_1m_DEM.tif
    DEM_tif32='SW_{0}_{1}_1k_1m_DEM.tif'.format(int(xmin),int(ymin))
    DEM_tif32=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'30a_Non_HydroDEM_1m_GeoTiff')),DEM_tif32)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',DEM_esri,'-otif','-nbits',32,'-o',DEM_tif32,'-step',1,'-elevation_lowest']
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DEM_tif32 created (no hydro) -- {0}'.format(os.path.isfile(DEM_tif32)),Heading=True)
    
    # 30b_Non_HydroDEM_1m_ASCII_XYZ
    # DEM_xyz=SW_500000_6981000_1k_1m_DEM.xyz
    DEM_xyz='SW_{0}_{1}_1k_1m_DEM.xyz'.format(int(xmin),int(ymin))
    DEM_xyz=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'30b_Non_HydroDEM_1m_ASCII_XYZ')),DEM_xyz)
    demlaz=os.path.join(tempworkspace,'dem.laz')
    subprocessargs=['C:/LAStools/bin/las2txt.exe','-i',demlaz,'-otxt','-rescale',0.001,0.001,0.001,'-o',DEM_xyz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DEM_xyz created (no hydro) -- {0}'.format(os.path.isfile(DEM_xyz)),Heading=True)

    #---------------------------------------------------------------------------------------
    #non_hydro_flattened 1m dsm in ascii grid, xyz and 32bit geotiff
    #---------------------------------------------------------------------------------------
    # 30c_Non_HydroDSM_1m_ASCII_ESRI
    # DSM_esri=SW_500000_6981000_1k_1m_ESRI_DSM.asc
    dsm_raw=os.path.join(tempworkspace,'dsm.asc')
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedoriginal,'-oasc','-nbits',32,'-o',dsm_raw,'-step',1,'-elevation_highest','-keep_class',1,3,4,5,6,8,10,11,13,14,15,16,17,18,19]
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('dsm_raw created -- {0}'.format(os.path.isfile(dsm_raw)),Heading=True)

    asciigrid_dem=AsciiGrid()
    asciigrid_dem.readfromfile(DEM_esri)

    asciigrid_dsm=AsciiGrid()
    asciigrid_dsm.readfromfile(dsm_raw)

    ones=np.array(np.ones((asciigrid_dem.grid.shape[0],asciigrid_dem.grid.shape[1])), ndmin=2, dtype=int)
    zeros=np.array(np.zeros((asciigrid_dem.grid.shape[0],asciigrid_dem.grid.shape[1])), ndmin=2, dtype=int)    
    nodata=np.array(np.ones((asciigrid_dem.grid.shape[0],asciigrid_dem.grid.shape[1])), ndmin=2, dtype=int)*asciigrid_dem.nodata_value   

    # extract hydro void areas
    voids=ones*(asciigrid_dsm.grid==asciigrid_dsm.nodata_value)
    
    voids_dsm=AsciiGrid() 
    voids_dsm.header=asciigrid_dem.header

    #outputting voids with dem heights
    DSM_esri='SW_{0}_{1}_1k_1m_ESRI_DSM.asc'.format(int(xmin),int(ymin))
    DSM_esri=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'30c_Non_HydroDSM_1m_ASCII_ESRI')),DSM_esri)

    voids_dsm.grid=np.where(voids==1,asciigrid_dem.grid,asciigrid_dsm.grid)
    voids_dsm.savetofile(DSM_esri)  

    dsmlaz=os.path.join(tempworkspace,'dsm.laz')
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',DSM_esri,'-olaz','-rescale',0.001,0.001,0.001,'-o',dsmlaz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('dsmlaz created (no hydro) -- {0}'.format(os.path.isfile(dsmlaz)),Heading=True)    

    
    # 30a_Non_HydroDSM_1m_GeoTiff
    # DSM_tif32=SW_500000_6981000_1k_1m_DSM.tif
    DSM_tif32='SW_{0}_{1}_1k_1m_DSM.tif'.format(int(xmin),int(ymin))
    DSM_tif32=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'30a_Non_HydroDSM_1m_GeoTiff')),DSM_tif32)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',DSM_esri,'-otif','-nbits',32,'-o',DSM_tif32,'-step',1,'-elevation_lowest']
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DSM_tif32 created (no hydro) -- {0}'.format(os.path.isfile(DSM_tif32)),Heading=True)
    

    # 30b_Non_HydroDSM_1m_ASCII_XYZ
    # DSM_xyz=SW_500000_6981000_1k_1m_DSM.xyz
    DSM_xyz='SW_{0}_{1}_1k_1m_DSM.xyz'.format(int(xmin),int(ymin))
    DSM_xyz=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'30b_Non_HydroDSM_1m_ASCII_XYZ')),DSM_xyz)
    subprocessargs=['C:/LAStools/bin/las2txt.exe','-i',dsmlaz,'-otxt','-rescale',0.001,0.001,0.001,'-o',DSM_xyz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DSM_xyz created (no hydro) -- {0}'.format(os.path.isfile(DSM_xyz)),Heading=True)    


    #---------------------------------------------------------------------------------------
    #hydro_flattened 1m dem in ascii grid, xyz and 32bit geotiff
    #---------------------------------------------------------------------------------------
    deminput=[mergedoriginal]

    tilehydro=os.path.join(tempworkspace,'hydro.laz')
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',hydropoints,'-merged','-olaz','-o',tilehydro,'-set_version','1.2','-set_classification',2,'-epsg',28356]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('tilehydro created -- {0}'.format(os.path.isfile(tilehydro)),Heading=True)
    if os.path.isfile(tilehydro):
        deminput.append(tilehydro)
        
    laz4dem=os.path.join(tempworkspace,'laz4dem.laz')
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i']+deminput+['-merged','-olaz','-o',laz4dem,'-keep_class',2,19]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    
    # 32_DEM_1m_ASCII_ESRI
    # DEM_esri=SW_500000_6981000_1k_1m_ESRI_DEM.asc
    DEM_esri='SW_{0}_{1}_1k_1m_ESRI_DEM.asc'.format(int(xmin),int(ymin))
    DEM_esri=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'32_DEM_1m_ASCII_ESRI')),DEM_esri)

    subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',laz4dem,'-oasc','-nbits',32,'-o',DEM_esri,'-step',1,'-kill',kill]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DEM_esri created (hydro) -- {0}'.format(os.path.isfile(DEM_esri)),Heading=True)


    demlaz_hydro=os.path.join(tempworkspace,'dem_hydro.laz')
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',DEM_esri,'-olaz','-rescale',0.001,0.001,0.001,'-o',demlaz_hydro]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('demlaz created (hydro) -- {0}'.format(os.path.isfile(demlaz_hydro)),Heading=True)    
    
    # 32_DEM_1m_GeoTiff
    # DEM_tif32=SW_500000_6981000_1k_1m_DEM.tif
    DEM_tif32='SW_{0}_{1}_1k_1m_DEM.tif'.format(int(xmin),int(ymin))
    DEM_tif32=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'32_DEM_1m_GeoTiff')),DEM_tif32)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',DEM_esri,'-otif','-nbits',32,'-o',DEM_tif32,'-step',1,'-elevation_lowest']
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DEM_tif32 created (hydro) -- {0}'.format(os.path.isfile(DEM_tif32)),Heading=True)
    
    # 31_DEM_1m_ASCII_XYZ
    # DEM_xyz=SW_500000_6981000_1k_1m_DEM.xyz
    DEM_xyz='SW_{0}_{1}_1k_1m_DEM.xyz'.format(int(xmin),int(ymin))
    DEM_xyz=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'31_DEM_1m_ASCII_XYZ')),DEM_xyz)
    subprocessargs=['C:/LAStools/bin/las2txt.exe','-i',demlaz_hydro,'-otxt','-rescale',0.001,0.001,0.001,'-o',DEM_xyz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DEM_xyz created (hydro) -- {0}'.format(os.path.isfile(DEM_xyz)),Heading=True)    


    #---------------------------------------------------------------------------------------
    #hydro_flattened 1m dsm in ascii grid, xyz and 32bit geotiff
    #---------------------------------------------------------------------------------------
    # 29_DSM_1m_ASCII_ESRI
    # DSM_esri=SW_500000_6981000_1k_1m_ESRI_DSM.asc

    asciigrid_dem=AsciiGrid()
    asciigrid_dem.readfromfile(DEM_esri)

    asciigrid_dsm=AsciiGrid()
    asciigrid_dsm.readfromfile(dsm_raw)

    ones=np.array(np.ones((asciigrid_dem.grid.shape[0],asciigrid_dem.grid.shape[1])), ndmin=2, dtype=int)
    zeros=np.array(np.zeros((asciigrid_dem.grid.shape[0],asciigrid_dem.grid.shape[1])), ndmin=2, dtype=int)    
    nodata=np.array(np.ones((asciigrid_dem.grid.shape[0],asciigrid_dem.grid.shape[1])), ndmin=2, dtype=int)*asciigrid_dem.nodata_value   

    # extract hydro void areas
    voids=ones*(asciigrid_dsm.grid==asciigrid_dsm.nodata_value)
    
    voids_dsm=AsciiGrid() 
    voids_dsm.header=asciigrid_dem.header

    #outputting voids with dem heights
    DSM_esri='SW_{0}_{1}_1k_1m_ESRI_DSM.asc'.format(int(xmin),int(ymin))
    DSM_esri=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'29_DSM_1m_ASCII_ESRI')),DSM_esri)

    voids_dsm.grid=np.where(voids==1,asciigrid_dem.grid,asciigrid_dsm.grid)
    voids_dsm.savetofile(DSM_esri)      

    dsmlaz_hydro=os.path.join(tempworkspace,'dsm_hydro.laz')
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',DSM_esri,'-olaz','-rescale',0.001,0.001,0.001,'-o',dsmlaz_hydro]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('dsmlaz created (hydro) -- {0}'.format(os.path.isfile(dsmlaz_hydro)),Heading=True)    
    
    # 27_DSM_1m_GeoTiff
    # DSM_tif32=SW_500000_6981000_1k_1m_DSM.tif
    DSM_tif32='SW_{0}_{1}_1k_1m_DSM.tif'.format(int(xmin),int(ymin))
    DSM_tif32=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'27_DSM_1m_GeoTiff')),DSM_tif32)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',DSM_esri,'-otif','-nbits',32,'-o',DSM_tif32,'-step',1,'-elevation_lowest']
    subprocessargs=subprocessargs+['-ll',xmin+0.5,ymin+0.5,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DSM_tif32 created (hydro) -- {0}'.format(os.path.isfile(DSM_tif32)),Heading=True)
    
    # 28_DSM_1m_ASCII_XYZ
    # DSM_xyz=SW_500000_6981000_1k_1m_DSM.xyz
    DSM_xyz='SW_{0}_{1}_1k_1m_DSM.xyz'.format(int(xmin),int(ymin))
    DSM_xyz=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'28_DSM_1m_ASCII_XYZ')),DSM_xyz)
    subprocessargs=['C:/LAStools/bin/las2txt.exe','-i',dsmlaz_hydro,'-otxt','-rescale',0.001,0.001,0.001,'-o',DSM_xyz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('DSM_xyz created (hydro) -- {0}'.format(os.path.isfile(DSM_xyz)),Heading=True)    

    #---------------------------------------------------------------------------------------
    #contours_25cm
    # 33_Contours
    contourpointslaz=os.path.join(tempworkspace,'contourpoints01.laz') 
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedoriginal,'-olaz','-o',contourpointslaz,'-keep_class',2,19,'-step',1,'-subcircle',0.5,'-elevation_average']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('contourpointslaz created -- {0}'.format(os.path.isfile(contourpointslaz)),Heading=True)    

    contourpointsxyz=os.path.join(tempworkspace,'contourpoints02.xyz') 
    subprocessargs=['C:/LAStools/bin/las2txt.exe','-i',contourpointslaz,'-otxt','-rescale',0.001,0.001,0.001,'-o',contourpointsxyz]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('contourpointsxyz created -- {0}'.format(os.path.isfile(contourpointsxyz)),Heading=True)    


    interval=0.25 #-contour_interval
    buff=0.025
    flatten=False #-flatten user input to flatten points between intervals's

    count=0 
    contourpointsxyzout=os.path.join(tempworkspace,'contourpoints03.xyz') 
    with open(contourpointsxyzout,'w') as f:
        lines = [line.rstrip('\n')for line in open(contourpointsxyz)]
        print(len(lines))
        for line in lines:
            count=count+1
            x,y,z=line.split()
            x,y,z=float(x),float(y),float(z)
            b=z%interval
            if buff<=b<=(interval-buff):
                if flatten:
                    z=math.floor(z/interval)*interval+interval/2

                f.write('{0} {1} {2}\n'.format(x,y,z))
        f.close()
    contourpointslaz=os.path.join(tempworkspace,'contourpoints04.laz') 
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',contourpointsxyzout,'-olaz','-o',contourpointslaz,'-rescale',0.001,0.001,0.001]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('filtered contourpointslaz created -- {0}'.format(os.path.isfile(contourpointslaz)),Heading=True)    

    
    contourpointslazfinal='{0}_{1}.laz'.format(int(xmin),int(ymin))
    contourpointslazfinal=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'contour_points')),contourpointslazfinal)
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',contourpointslaz, tilehydro,'-merged','-olaz','-o',contourpointslazfinal,'-set_classification',2]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  
    PrintMsg('filetered contourpointslaz created (final -hydro points added) -- {0}'.format(os.path.isfile(contourpointslaz)),Heading=True)    



    #---------------------------------------------------------------------------------------


    # clean up workspace
    
    PrintMsg('Cleanup',Heading=True)
    if __keepfiles==None:
        for folder in cleanupfolders:
            if os.path.isdir(folder):
                cleanupfiles=AtlassGen.FILELIST('*.*',folder)
                for file in cleanupfiles:
                    if os.path.isfile(file):
                        os.remove(file)
                        PrintMsg('file: {0} removed.'.format(file))
                        pass
                    else:
                        PrintMsg('file: {0} not found.'.format(file))
                
                shutil.rmtree(folder, ignore_errors=True)
                pass
    

if __name__ == "__main__":
    main(sys.argv[1:])            