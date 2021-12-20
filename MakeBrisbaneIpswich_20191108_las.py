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
    class_tiles=AtlassGen.makedir(os.path.join(tempworkspace,'originalclassifed'))
    copyneighbourtiles(xmin,ymin,xmax,ymax,buffer,tilelayout_500m_tl,[lazpath],class_tiles,prefix='',extn='.laz')
    #add files to cleanup
    cleanupfolders.append(class_tiles)


    #CONVERT TO las1.4
    class_tiles_14=AtlassGen.makedir(os.path.join(tempworkspace,'LAS14'))

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles),'-olaz','-odir',class_tiles_14,'-set_version','1.4','-epsg',28356]
    subprocessargs=subprocessargs+['-reoffset',xorigin,yorigin,0]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_14)

    #CONVERT TO PDRF6
    class_tiles_PDRF6=AtlassGen.makedir(os.path.join(tempworkspace,'PDRF6'))

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_14),'-olaz','-odir',class_tiles_PDRF6,'-set_point_type','6']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_PDRF6)

    #LASthin
    class_tiles_MKP=AtlassGen.makedir(os.path.join(tempworkspace,'MKP'))

    subprocessargs=['C:/LAStools/bin/lasthin64.exe','-i','{0}/*.laz'.format(class_tiles_PDRF6),'-olaz','-odir',class_tiles_MKP,'-flag_as_keypoint','-adaptive', 0.1,5.0,'-ignore_class',0,1,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_MKP)

    pdrf6files=AtlassGen.FILELIST('*.laz',class_tiles_PDRF6)
    for file in pdrf6files:
        
        path,name,ext=AtlassGen.FILESPEC(file)
        if ext=='laz':
            mkpfile=os.path.join(class_tiles_MKP,'{0}.laz'.format(name))
            if not os.path.isfile(mkpfile):
                shutil.copy2(file,class_tiles_MKP)
                print('copied {0} as no mkp file exists'.format(name))

    #merge classified tiles with buffer 
    mergedoriginal=os.path.join(tempworkspace,'02_mergedoriginal.laz')
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_MKP),'-merged','-olaz','-o',mergedoriginal,'-set_version','1.4','-epsg',28356]
    subprocessargs=subprocessargs+['-reoffset',xorigin,yorigin,0]
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
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',mergedoriginal,'-olas','-o',las_ahd,'-change_classification_from_to',10,17,'-change_classification_from_to',13,19,'-epsg',28356,'-set_point_type', 6]
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
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',geoid,'-olaz','-o',tilegeoid,'-set_version','1.4','-set_classification',0,'-epsg',28356]
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