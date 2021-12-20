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
from os.path import basename
import numpy as np
import io
import datetime
import time
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

import zipfile

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

cleanupfolders=[]

defaults={}
defaults['tile']=None #(delivery tile name)
defaults['tilelayout_1km']="//10.10.10.142/processed_data/BR02096_Canberra_and_ACT_Tender-ACT_Government/01_LiDAR/05_Product_generation/1km_delivery_tilelayout.json" #delivery tilelayout 
defaults['tilelayout_500m']="//10.10.10.142/processed_data/BR02096_Canberra_and_ACT_Tender-ACT_Government/01_LiDAR/05_Product_generation/500m_storage_tilelayout.json" #storage tilelayout
defaults['workingpath']=None #location to process and store results
defaults['products']='//10.10.10.142/processed_data/BR02096_Canberra_and_ACT_Tender-ACT_Government/01_LiDAR/05_Product_generation/GDA_2020_Z55_Canberra_2020_Submission'
defaults['lazpath']="//10.10.10.142/processed_data/BR02096_Canberra_and_ACT_Tender-ACT_Government/01_LiDAR/04_Final_transformed_and_XYZ_adjusted/GDA2020_Z55_Canberra_ACT_AHD_xyz_adj" #location to process and store results
defaults['ELL_GEOID']="//10.10.10.142/Projects/Projects/BR02096_Canberra_and_ACT_Tender-ACT_Government/GEOIDS/AHD_to_ELL.laz" #geoid from AHD to ELL
defaults['AVWS_GEOID']="//10.10.10.142/Projects/Projects/BR02096_Canberra_and_ACT_Tender-ACT_Government/GEOIDS/AHD_to_AVWS.laz"
defaults['zshift']=0
defaults['buffer']=0
defaults['__keepfiles']=None

masterVLR="//10.10.10.142/projects/PythonScripts/VLR_Headers/GDA2020/55/AHD/GDA2020_55_AHD.vlr"
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
    #load and run using 1km tilelayout in the one tool
    #python \\10.10.10.142\projects\PythonScripts\MakeCanberra_20200626_las.py --tile=#name# --workingpath=W:\temp2\working\working --zshift=-0.035


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
        folders.append('01_GDA2020_MGA55_AHD')
        folders.append('03_GDA2020_MGA55_AVWS')
        folders.append('02_GDA2020_MGA55_ELL')
        

        for folder in folders:
            AtlassGen.makedir(os.path.join(workingpath,folder))
        pass
    else:
        PrintMsg('workingpath not set')
        exit(1)

    products=settings['products']
    if not products==None:
        productspath=AtlassGen.makedir(products.replace('\\','/'))
        pass
    else:
        PrintMsg('products path not set')
        exit(1)

    tilelayout_1km=settings['tilelayout_1km']
    if not tilelayout_1km==None:
        tilelayout_1km=tilelayout_1km.replace('\\','/')
        tilelayout_1km_tl = AtlassTileLayout()
        tilelayout_1km_tl.fromjson(tilelayout_1km)
        pass
    else:
        PrintMsg('tilelayout_1km not set')
        exit(1)

    tilelayout_500m=settings['tilelayout_500m']
    if not tilelayout_500m==None:
        tilelayout_500m=tilelayout_500m.replace('\\','/')
        tilelayout_500m_tl = AtlassTileLayout()
        tilelayout_500m_tl.fromjson(tilelayout_500m)        
        pass
    else:
        PrintMsg('tilelayout_500m not set')
        exit(1)

    lazpath=settings['lazpath']
    if not lazpath==None:
        lazpath=lazpath.replace('\\','/')
        pass
    else:
        PrintMsg('lazpath not set')
        exit(1)

    ELL_GEOID=settings['ELL_GEOID']
    if not ELL_GEOID==None:
        ELL_GEOID=ELL_GEOID.replace('\\','/')
        pass
    else:
        PrintMsg('ELL_GEOID not set')
        exit(1)

    AVWS_GEOID=settings['AVWS_GEOID']
    if not AVWS_GEOID==None:
        AVWS_GEOID=AVWS_GEOID.replace('\\','/')
        pass
    else:
        PrintMsg('AVWS_GEOID not set')
        exit(1)

    zshift=settings['zshift']
    if not zshift==None:
        zshift=float(zshift)
        pass
    else:
        zshift=0

    buffer=settings['buffer']
    if not buffer==None:
        buffer=float(buffer)
        pass
    else:
        buffer=0

    __keepfiles=settings['__keepfiles']


    '''
    ----------------------------------------------------------------------------------------------
    preparation
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

    #prep geoid with 1000m tile buffer
    ELL_GEOID_tile=os.path.join(tempworkspace,'{0}_ELL_GEOID.laz'.format(tile))
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',ELL_GEOID,'-olaz','-o',ELL_GEOID_tile]
    subprocessargs=subprocessargs+['-keep_xy',xmin-10000,ymin-10000,xmax+10000,ymax+10000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)
    PrintMsg('ELL geoid created -- {0}'.format(os.path.isfile(ELL_GEOID_tile)),Heading=True)

    AVWS_GEOID_tile=os.path.join(tempworkspace,'{0}_AVWS_GEOID.laz'.format(tile))
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',AVWS_GEOID,'-olaz','-o',AVWS_GEOID_tile]
    subprocessargs=subprocessargs+['-keep_xy',xmin-10000,ymin-10000,xmax+10000,ymax+10000]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)
    PrintMsg('AVWS geoid created -- {0}'.format(os.path.isfile(AVWS_GEOID_tile)),Heading=True)


    #temp workspace for original tiles
    class_tiles=AtlassGen.makedir(os.path.join(tempworkspace,'01_500m_original'))
    copyneighbourtiles(xmin,ymin,xmax,ymax,buffer,tilelayout_500m_tl,[lazpath],class_tiles,prefix='',extn='.laz')
    #add files to cleanup
    cleanupfolders.append(class_tiles)

    #copy master VLR
    shutil.copyfile(masterVLR,os.path.join(class_tiles,'vlrs.vlr'))

    os.chdir(class_tiles)
    
    class_tiles_vlr=AtlassGen.makedir(os.path.join(tempworkspace,'02_500m_vlr'))
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.laz'.format(class_tiles), '-load_vlrs', '-odir',class_tiles_vlr,'-olaz','-translate_xyz',0,0,zshift,'-change_classification_from_to',10,17,'-change_classification_from_to',13,19]  
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    #CONVERT TO las1.4
    class_tiles_14=AtlassGen.makedir(os.path.join(tempworkspace,'03_500m_14'))

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_vlr),'-olaz','-odir',class_tiles_14,'-set_version','1.4']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_14)

    #CONVERT TO PDRF6
    class_tiles_PDRF6=AtlassGen.makedir(os.path.join(tempworkspace,'04_500m_PDRF6'))

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_14),'-olaz','-odir',class_tiles_PDRF6,'-set_point_type','6']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_PDRF6)

    #CONVERT TO ELL
    class_tiles_ELL=AtlassGen.makedir(os.path.join(tempworkspace,'05_500m_ELL'))

    subprocessargs=['C:/LAStools/bin/lasheight64.exe','-i','{0}/*.laz'.format(class_tiles_PDRF6),'-olaz','-ground_points',ELL_GEOID_tile, '-all_ground_points','-odir',class_tiles_ELL,'-replace_z']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_ELL)


    #CONVERT TO AVWS
    class_tiles_AVWS=AtlassGen.makedir(os.path.join(tempworkspace,'06_500m_AVWS'))

    subprocessargs=['C:/LAStools/bin/lasheight64.exe','-i','{0}/*.laz'.format(class_tiles_PDRF6),'-olaz','-ground_points',AVWS_GEOID_tile, '-all_ground_points','-odir',class_tiles_AVWS,'-replace_z']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    cleanupfolders.append(class_tiles_AVWS)

    PrintMsg('Original converted to LAS1.4-PDRF6 -- {0} - zshifted {1}m  -- merging...'.format(os.path.isfile(class_tiles_PDRF6),zshift),Heading=True)

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
    las_ahd='ACT-12ppm-2020-C3-AHD_{0}{1}_55_0001_0001.las'.format(int(math.floor(xmin/1000)),int(math.floor(ymin/1000)))
    las_ahd=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'01_GDA2020_MGA55_AHD')),las_ahd)
    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_PDRF6),'-olas','-merged','-o',las_ahd]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    PrintMsg('las_ahd created -- {0}'.format(os.path.isfile(las_ahd)),Heading=True)

    #---------------------------------------------------------------------------------------    
    # 02_LAS_Ellipsoid
    las_ell='ACT-12ppm-2020-C3-ELL_{0}{1}_55_0001_0001.las'.format(int(math.floor(xmin/1000)),int(math.floor(ymin/1000)))
    las_ell=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'02_GDA2020_MGA55_ELL')),las_ell)

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_ELL),'-olas','-merged','-o',las_ell]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    PrintMsg('las_ELL created -- {0}'.format(os.path.isfile(las_ell)),Heading=True)

    #---------------------------------------------------------------------------------------    
    # 03_LAS_AVWS
    las_avws='ACT-12ppm-2020-C3-AVWS_{0}{1}_55_0001_0001.las'.format(int(math.floor(xmin/1000)),int(math.floor(ymin/1000)))
    las_avws=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'03_GDA2020_MGA55_AVWS')),las_avws)

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i','{0}/*.laz'.format(class_tiles_AVWS),'-olas','-merged','-o',las_avws]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    PrintMsg('las_AVWS created -- {0}'.format(os.path.isfile(las_avws)),Heading=True)

    #---------------------------------------------------------------------------------------

    completed=os.path.isfile(las_avws) and  os.path.isfile(las_ell) and  os.path.isfile(las_ahd)



    #---------------------------------------------------------------------------------------
    # #copy las_ahd to drive 1
    #01_GDA2020_MGA55_AHD
    dest=AtlassGen.makedir(os.path.join('F:/ACT_LIDAR_2020/','01_GDA2020_MGA55_AHD'))
    #shutil.copy2(las_ahd,dest)
    #PrintMsg('las_ahd coppied',Heading=True)

    #zip las_ahd
    zfile=las_ahd.replace('.las','.zip')
    zfile_z=zipfile.ZipFile(zfile, mode='w', compression=zipfile.ZIP_DEFLATED)
    zfile_z.write(las_ahd,basename(las_ahd))
    zfile_z.close()

    PrintMsg('las_ahd zipped', Heading=True)

    dest=AtlassGen.makedir(os.path.join(productspath,'01_GDA2020_MGA55_AHD'))
    shutil.copy2(zfile,dest)
    os.remove(zfile)
    os.remove(las_ahd)
    PrintMsg('las_ahd zip coppied',Heading=True)

    #---------------------------------------------------------------------------------------
    #copy las_ell to drive 2
    #02_GDA2020_MGA55_ELL
    dest=AtlassGen.makedir(os.path.join('G:/ACT_LIDAR_2020/','02_GDA2020_MGA55_ELL'))
    #shutil.copy2(las_ell,dest)
    #PrintMsg('las_ell coppied',Heading=True)

    #zip las_ell
    
    zfile=las_ell.replace('.las','.zip')
    zfile_z=zipfile.ZipFile(zfile, mode='w', compression=zipfile.ZIP_DEFLATED)
    zfile_z.write(las_ell,basename(las_ell))
    zfile_z.close()

    PrintMsg('las_ell zipped',Heading=True)

    dest=AtlassGen.makedir(os.path.join(productspath,'02_GDA2020_MGA55_ELL'))
    shutil.copy2(zfile,dest)
    os.remove(zfile)
    os.remove(las_ell)
    PrintMsg('las_ell zip coppied',Heading=True)

    #---------------------------------------------------------------------------------------
    #copy las_avws to drive 3
    #03_GDA2020_MGA55_AVWS
    dest=AtlassGen.makedir(os.path.join('H:/ACT_LIDAR_2020/','03_GDA2020_MGA55_AVWS'))
    #shutil.copy2(las_avws,dest)
    #PrintMsg('las_avws coppied',Heading=True)

    #zip las_avws
    zfile=las_avws.replace('.las','.zip')
    zfile_z=zipfile.ZipFile(zfile, mode='w', compression=zipfile.ZIP_DEFLATED)
    zfile_z.write(las_avws,basename(las_avws))
    zfile_z.close()
    PrintMsg('las_avws zipped',Heading=True)

    dest=AtlassGen.makedir(os.path.join(productspath,'03_GDA2020_MGA55_AVWS'))
    shutil.copy2(zfile,dest)
    os.remove(zfile)
    os.remove(las_avws)
    PrintMsg('las_avws zip coppied',Heading=True)

    # clean up workspace
    if not completed:
        exit(1) 

    PrintMsg('Cleanup',Heading=True)
    if __keepfiles==None and completed:
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