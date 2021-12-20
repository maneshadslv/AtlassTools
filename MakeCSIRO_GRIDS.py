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
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

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
#Global variables and constants
__keepfiles=None #can be overritten by settings


defaults={}
defaults['tile']=None
defaults['xmin']=None 
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None

defaults['areaname']=None
defaults['yyyy']=None #year eg.2019
defaults['zone']=None #year eg.55
defaults['laspath']=None # storage folder can be on the server
defaults['extn']=None
defaults['tilelayout']=None
defaults['aoi']=None
defaults['storagepath']=None # server location to store final results.
defaults['workingpath']=None # local ssd
defaults['deliverypath']=None # can be usb HDD #Delivery\National_Datasets\Queensland\<areaname>
defaults['geoid']=None #geoid to convert from AHD to ELL using lastools

defaults['__keepfiles']=None

# stuff for DEM
defaults['hydropoints']=None
defaults['buffer']=500
defaults['kill']=450
        
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

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------
    
    #python \\10.10.10.142\projects\PythonScripts\MakeCSIRO_GRIDS.py --tile=#name# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --areaname=Bishopbourne --yyyy=2019 --zone=55 --laspath=F:\Processing\Area01_Mary_GDA94MGA56\origtiles --tilelayout=F:\Processing\Area01_Mary_GDA94MGA56\origtiles\TileLayout.json --storagepath=W:\temp2\working\storage\NorthMidlands --workingpath=W:\temp2\working\working --deliverypath=W:\temp2\working\delivery\NorthMidlands --extn=laz --geoid="\\10.10.10.142\projects\Projects\BR01325_CSIRO_Reef_Catchments-CSIRO\GEOID\AG09_From_AHD_To_ELL_Lastools.laz" --aoi="<file>?"


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
            #raise Exception('Unknown input type')

    #create variables from settings
    tile=settings['tile']
    if not tile==None:
        pass
    else:
        PrintMsg('tile not set')
        return

    xmin=settings['xmin']
    if not xmin==None:
        xmin=float(xmin)
    else:
        PrintMsg('xmin not set')
        return

    ymin=settings['ymin']
    if not ymin==None:
        ymin=float(ymin)
    else:
        PrintMsg('ymin not set')
        return

    xmax=settings['xmax']
    if not xmax==None:
        xmax=float(xmax)
    else:
        PrintMsg('xmax not set')
        return

    ymax=settings['ymax']
    if not ymax==None:
        ymax=float(ymax)
    else:
        PrintMsg('ymax not set')
        return
    kill=float(settings['kill'])
    
    buffer=float(settings['buffer'])

    areaname=settings['areaname']
    if areaname==None:
        PrintMsg('areaname not set')
        return    

    yyyy=settings['yyyy']
    if yyyy==None:
        PrintMsg('yyyy not set')
        return    
    zone=settings['zone']
    if zone==None:
        PrintMsg('zone not set')
        return          

    laspath=settings['laspath']
    if not laspath==None:
        laspath=laspath.replace('\\','/')
    else: 
        PrintMsg('laspath not set')
        return

    geoid=settings['geoid']
    if not geoid==None:
        geoid=geoid.replace('\\','/')
    else: 
        PrintMsg('geoid not set')
        return

    extn=settings['extn']
    if not laspath==None:
        pass
    else: 
        PrintMsg('extn not set')
        return

    tilelayout=settings['tilelayout']
    if not tilelayout==None:
        tilelayout=AtlassTileLayout()
        tilelayout.fromjson(settings['tilelayout'].replace('\\','/'))
    else: 
        PrintMsg('tilelayout not set')
        return    

    aoi=settings['aoi']
    if not aoi==None:
        aoi=aoi.replace('\\','/')
    else: 
        PrintMsg('aoi not set')
        return              


    storagepath=settings['storagepath']
    if not storagepath==None:
        storagepath=AtlassGen.makedir(storagepath.replace('\\','/'))
    else: 
        PrintMsg('storagepath not set')
        return
            
    workingpath=settings['workingpath']
    if not workingpath==None:
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
    else: 
        PrintMsg('workingpath not set')
        return     

    deliverypath=settings['deliverypath']
    if not deliverypath==None:
        deliverypath=AtlassGen.makedir(deliverypath.replace('\\','/'))
    else: 
        PrintMsg('deliverypath not set')
        return     

    hydropoints=settings['hydropoints']
    if not hydropoints==None:
        hydropoints=hydropoints.replace('\\','/')
    else: 
        pass 

    __keepfiles=settings['__keepfiles']
    cleanupfiles=[]
    cleanupfolders=[]


    #set up workspace
    PrintMsg('Setting up workspace',Heading=True)
    workspace={}
    workspace['DEM']={}
    workspace['DEM']['relpath']='{0}/Zone{1}/{2}/DEM/ArcASCII/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['DEM']['nameconv']='{0}{1}-DEM-GRID-0_5_{2}{3}_{4}_0001_0001.asc'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['DEM']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['DEM']['relpath']))
    workspace['DEM']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['DEM']['relpath']))
    workspace['DEM']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/DEM_50cm'.format(areaname,tile)))
    cleanupfolders.append(workspace['DEM']['workingpath'])

    workspace['DSM']={}
    workspace['DSM']['relpath']='{0}/Zone{1}/{2}/DSM/ArcASCII/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['DSM']['nameconv']='{0}{1}-DSM-GRID-001_{2}{3}_{4}_0001_0001.asc'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['DSM']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['DSM']['relpath']))
    workspace['DSM']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['DSM']['relpath']))
    workspace['DSM']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/DSM_1m'.format(areaname,tile)))
    cleanupfolders.append(workspace['DSM']['workingpath'])

    workspace['INT']={}
    workspace['INT']['relpath']='{0}/Zone{1}/{2}/Intensity_tiles/ECW/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['INT']['nameconv']='{0}{1}-INT-001_{2}{3}_{4}_0001_0001.tif'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['INT']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['INT']['relpath']))
    workspace['INT']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['INT']['relpath']))
    workspace['INT']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/INT_1m'.format(areaname,tile)))
    cleanupfolders.append(workspace['INT']['workingpath'])    

    workspace['C3_LAS_ELL']={}
    workspace['C3_LAS_ELL']['relpath']='{0}/Zone{1}/{2}/Classified_LAS/LAS_Ellipsoid/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['C3_LAS_ELL']['nameconv']='{0}{1}-C3-ELL_{2}{3}_{4}_0001_0001.las'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['C3_LAS_ELL']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['C3_LAS_ELL']['relpath']))
    workspace['C3_LAS_ELL']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['C3_LAS_ELL']['relpath']))
    workspace['C3_LAS_ELL']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/C3_LAS_ELL'.format(areaname,tile)))
    cleanupfolders.append(workspace['C3_LAS_ELL']['workingpath'])

    workspace['MKP_LAS_ELL']={}
    workspace['MKP_LAS_ELL']['relpath']='{0}/Zone{1}/{2}/MKP/LAS_Ellipsoid/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['MKP_LAS_ELL']['nameconv']='{0}{1}-C3-MKP-ELL_{2}{3}_{4}_0001_0001.las'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['MKP_LAS_ELL']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['MKP_LAS_ELL']['relpath']))
    workspace['MKP_LAS_ELL']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['MKP_LAS_ELL']['relpath']))
    workspace['MKP_LAS_ELL']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/MKP_LAS_ELL'.format(areaname,tile)))
    cleanupfolders.append(workspace['MKP_LAS_ELL']['workingpath'])

    '''
    not active this should actually be swaths
    workspace['UNC_LAS_ELL']={}
    workspace['UNC_LAS_ELL']['relpath']='{0}/Zone{1}/{2}/Classified_LAS/LAS_Ellipsoid/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['UNC_LAS_ELL']['nameconv']='{0}{1}-C0-ELL_{2}{3}_{4}_0001_0001.las'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['UNC_LAS_ELL']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['UNC_LAS_ELL']['relpath']))
    workspace['UNC_LAS_ELL']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['UNC_LAS_ELL']['relpath']))
    workspace['UNC_LAS_ELL']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/UNC_LAS_ELL'.format(areaname,tile)))
    cleanupfolders.append(workspace['UNC_LAS_ELL']['workingpath'])
    '''
    workspace['C3_LAS_AHD']={}
    workspace['C3_LAS_AHD']['relpath']='{0}/Zone{1}/{2}/Classified_LAS/LAS_AHD/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['C3_LAS_AHD']['nameconv']='{0}{1}-C3-AHD_{2}{3}_{4}_0001_0001.las'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['C3_LAS_AHD']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['C3_LAS_AHD']['relpath']))
    workspace['C3_LAS_AHD']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['C3_LAS_AHD']['relpath']))
    workspace['C3_LAS_AHD']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/C3_LAS_AHD'.format(areaname,tile)))
    cleanupfolders.append(workspace['C3_LAS_AHD']['workingpath'])

    workspace['MKP_LAS_AHD']={}
    workspace['MKP_LAS_AHD']['relpath']='{0}/Zone{1}/{2}/MKP/LAS_AHD/1000m_Tiles'.format(areaname,zone,yyyy)
    workspace['MKP_LAS_AHD']['nameconv']='{0}{1}-C3-MKP-AHD_{2}{3}_{4}_0001_0001.las'.format(areaname,yyyy,int(round(xmin/1000,0)),int(round(ymin/1000,0)),zone)
    workspace['MKP_LAS_AHD']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['MKP_LAS_AHD']['relpath']))
    workspace['MKP_LAS_AHD']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['MKP_LAS_AHD']['relpath']))
    workspace['MKP_LAS_AHD']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/MKP_LAS_AHD'.format(areaname,tile)))
    cleanupfolders.append(workspace['MKP_LAS_AHD']['workingpath'])

    #create other folders
    for fp in [deliverypath,storagepath]:
        AtlassGen.makedir(os.path.join(fp,os.path.join('{0}/Zone{1}/{2}/Flightlines/SHP'.format(areaname,zone,yyyy))))
        AtlassGen.makedir(os.path.join(fp,os.path.join('{0}/Zone{1}/{2}/Intensity_mosaic'.format(areaname,zone,yyyy))))
        AtlassGen.makedir(os.path.join(fp,os.path.join('{0}/Zone{1}/{2}/Metadata'.format(areaname,zone,yyyy))))
        AtlassGen.makedir(os.path.join(fp,os.path.join('{0}/Zone{1}/{2}/Tile_layout'.format(areaname,zone,yyyy))))

    originaltiles=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/Original_LAS_tiles'.format(areaname,tile)))
    cleanupfolders.append(originaltiles)
    cleanupfolders.append(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)))

    # Get overlapping tiles in buffer
    PrintMsg(Message="Getting Neighbours",Heading=True)
    neighbours=tilelayout.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    PrintMsg('{0} Neighbours detected'.format(len(neighbours)))
    PrintMsg('Copying to workspace')

    # Copy to workspace
    for neighbour in neighbours:
        source =  os.path.join(laspath,'{0}.{1}'.format(neighbour,extn))
        dest =  originaltiles
        shutil.copy2(source,dest)
        if os.path.isfile(os.path.join(dest,'{0}.{1}'.format(neighbour,extn))):
            PrintMsg('{0}.{1} copied.'.format(neighbour,extn))
            cleanupfiles.append(os.path.join(dest,'{0}.{1}'.format(neighbour,extn)))       
        else:
            PrintMsg('{0}.{1} file not copied.'.format(neighbour,extn))

    # Create merged
    PrintMsg(Message="Making buffered las file",Heading=True)
    mergedlas=os.path.join( os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),'{0}.laz'.format(tile))
    cleanupfiles.append(mergedlas)

    #merged AHD z adjusted to control source data.
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(originaltiles,extn),'-merged','-olaz','-o',mergedlas]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    
    if os.path.isfile(mergedlas):
        PrintMsg('buffered file created')
    else:
        PrintMsg('buffered file not created')
        return

    # clipping and make AHD version clipped to tile bounds.
    C3_LAS_AHD_T=mergedlas.replace('.laz','_clip.laz')
    cleanupfiles.append(C3_LAS_AHD_T)
    subprocessargs=['C:/LAStools/bin/lasclip.exe','-i',mergedlas,'-poly',aoi,'-o',C3_LAS_AHD_T]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    C3_LAS_AHD=os.path.join(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),workspace['C3_LAS_AHD']['nameconv'])
    cleanupfiles.append(C3_LAS_AHD)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',C3_LAS_AHD_T,'-olas','-set_version','1.2','-epsg','283{0}'.format(zone),'-o',C3_LAS_AHD]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs)
    print(str(subprocessargs))
    subprocess.call(subprocessargs)

    shutil.copy2(C3_LAS_AHD,workspace['C3_LAS_AHD']['storagepath'])
    shutil.copy2(C3_LAS_AHD,workspace['C3_LAS_AHD']['deliverypath'])

    # make ellipsoidal version clipped to tile bounds.
    C3_LAS_ELL=os.path.join(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),workspace['C3_LAS_ELL']['nameconv'])
    cleanupfiles.append(C3_LAS_ELL)
    subprocessargs=['C:/LAStools/bin/lasheight.exe','-i',C3_LAS_AHD,'-o',C3_LAS_ELL,'-ground_points',geoid,'-all_ground_points','-replace_z']
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    shutil.copy2(C3_LAS_ELL,workspace['C3_LAS_ELL']['storagepath'])
    shutil.copy2(C3_LAS_ELL,workspace['C3_LAS_ELL']['deliverypath'])

    # make ellipsoidal unclassified version.
    # not active - this should actually be swaths.

    # make intensity.
    INT=os.path.join(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),workspace['INT']['nameconv'])
    cleanupfiles.append(INT)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-intensity','-average','-first_only','-otif','-nbits','8','-o',INT,'-step',1,'-set_min_max',500,1800]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',1000,'-ncols',1000]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    shutil.copy2(INT,workspace['INT']['storagepath'])
    shutil.copy2(INT,workspace['INT']['deliverypath'])

    # create a buffered ground file (+ hydro) for DEM & mkp creation
    demground=mergedlas.replace('.laz','_GND.laz')
    cleanupfiles.append(demground)    

    PrintMsg(Message="Making DEM ground file",Heading=True)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',mergedlas,'-merged','-olaz','-o',demground]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer,'-keep_class',2,8]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)     

    # make mkp AHD.
    mkpT1=mergedlas.replace('.laz','_mkp.laz')
    cleanupfiles.append(mkpT1)
    subprocessargs=['C:/LAStools/bin/lasthin64.exe','-i',demground,'-olaz','-o',mkpT1,'-adaptive',0.1,10,'-classify_as', 8]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    mkpT2=mergedlas.replace('.laz','_clip.laz')
    cleanupfiles.append(mkpT2)
    subprocessargs=['C:/LAStools/bin/lasclip.exe','-i',mkpT1,'-poly',aoi,'-o',mkpT2,'-keep_class',8]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    MKP_LAS_AHD=os.path.join(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),workspace['MKP_LAS_AHD']['nameconv'])
    cleanupfiles.append(MKP_LAS_AHD)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',mkpT2,'-olas','-set_version','1.2','-epsg','283{0}'.format(zone),'-o',MKP_LAS_AHD]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    shutil.copy2(MKP_LAS_AHD,workspace['MKP_LAS_AHD']['storagepath'])
    shutil.copy2(MKP_LAS_AHD,workspace['MKP_LAS_AHD']['deliverypath'])

    # make mkp ELL from MKP AHD.
    MKP_LAS_ELL=os.path.join(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),workspace['MKP_LAS_ELL']['nameconv'])
    cleanupfiles.append(MKP_LAS_ELL)
    subprocessargs=['C:/LAStools/bin/lasheight.exe','-i',MKP_LAS_AHD,'-o',MKP_LAS_ELL,'-ground_points',geoid,'-all_ground_points','-replace_z']
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    shutil.copy2(MKP_LAS_ELL,workspace['MKP_LAS_ELL']['storagepath'])
    shutil.copy2(MKP_LAS_ELL,workspace['MKP_LAS_ELL']['deliverypath'])


    # make a dsm grid with no fill.
    step=1.0
    PrintMsg(Message="Making DSM")
    dsmtempfile1=mergedlas.replace('.laz','_DSM.asc')
    cleanupfiles.append(dsmtempfile1)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-oasc','-o',dsmtempfile1,'-nbits',32,'-elevation_highest','-step',step,'-keep_class'] + [1,2,3,4,5,6,8,10,13,14,15,16,17,18,19,20]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    

    dsmtempfile2=mergedlas.replace('.laz','_DSM.laz')
    cleanupfiles.append(dsmtempfile2)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',dsmtempfile1,'-olaz','-o',dsmtempfile2,'-rescale',0.001,0.001,0.001]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)        

    dsmtempfile3=mergedlas.replace('.laz','_DSM_clipped.laz')
    cleanupfiles.append(dsmtempfile3)
    subprocessargs=['C:/LAStools/bin/lasclip.exe','-i',dsmtempfile2,'-olaz','-o',dsmtempfile3,'-poly',aoi]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)      


    print('dem ground prep file created')  
    if not hydropoints==None:
        tempfile2=demground
        demground=tempfile2.replace('.laz','_HYDRO.laz')
        cleanupfiles.append(demground)    

        PrintMsg(Message="Making DEM hydro+ground file")
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,hydropoints,'-merged','-olaz','-o',demground]
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)    
        PrintMsg('DEM hydro+ground file created')    

    #make a dem 0.5m with hydro
    step=0.5
    PrintMsg(Message="Making DEM")

    demtempfile1=mergedlas.replace('.laz','_DEM.asc')
    cleanupfiles.append(demtempfile1)
    subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',demground,'-oasc','-o',demtempfile1,'-nbits',32,'-kill',kill,'-step',step]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    

    demtempfile2=mergedlas.replace('.laz','_DEM.laz')
    cleanupfiles.append(demtempfile2)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',demtempfile1,'-olaz','-o',demtempfile2,'-rescale',0.001,0.001,0.001]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)        

    demtempfile3=mergedlas.replace('.laz','_DEM_clipped.laz')
    cleanupfiles.append(demtempfile3)
    subprocessargs=['C:/LAStools/bin/lasclip.exe','-i',demtempfile2,'-olaz','-o',demtempfile3,'-poly',aoi]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)        

    demfile=os.path.join( workspace['DEM']['workingpath'],workspace['DEM']['nameconv'])
    cleanupfiles.append(demfile)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',demtempfile3,'-oasc','-o',demfile,'-nbits',32,'-elevation_highest','-step',step]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    

    if os.path.isfile(demfile):
        PrintMsg('Dem file created')
        
        shutil.copy2(demfile,workspace['DEM']['deliverypath'])
        PrintMsg('copied to delivery')
        cleanupfiles.append(demfile)  

        #zip
        zipfile=demfile.replace('.asc','.zip')
        subprocessargs=['C:/Program Files/WinRAR/RAR.exe','a','-m5',zipfile,demfile,'-ep','-o+']
        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)
        cleanupfiles.append(zipfile)       
        PrintMsg('zipped for strorage')        

        #copy to storage
        shutil.copy2(zipfile,workspace['DEM']['storagepath'])      
        PrintMsg('coppied to storage')

    #make merged DEM DSM, grid. 
    step=1.0
    PrintMsg(Message="Making DSM")
    dsmfile=os.path.join( workspace['DSM']['workingpath'],workspace['DSM']['nameconv'])
    cleanupfiles.append(dsmtempfile1)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',dsmtempfile3,demtempfile3,'-merged','-oasc','-o',dsmfile,'-nbits',32,'-elevation_highest','-step',step]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    

    if os.path.isfile(dsmfile):
            PrintMsg('Dsm file created')
            
            shutil.copy2(dsmfile,workspace['DSM']['deliverypath'])
            PrintMsg('copied to delivery')
            cleanupfiles.append(dsmfile)  

            #zip
            zipfile=dsmfile.replace('.asc','.zip')
            subprocessargs=['C:/Program Files/WinRAR/RAR.exe','a','-m5',zipfile,dsmfile,'-ep','-o+']
            subprocessargs=map(str,subprocessargs)
            subprocess.call(subprocessargs)
            cleanupfiles.append(zipfile)       
            PrintMsg('zipped for strorage')        

            #copy to storage
            shutil.copy2(zipfile,workspace['DSM']['storagepath'])      
            PrintMsg('coppied to storage')

    # clean up workspace
    if __keepfiles==None:
        PrintMsg('Cleanup',Heading=True)
        for file in cleanupfiles:
            if os.path.isfile(file):
                os.remove(file)
                PrintMsg('file: {0} removed.'.format(file))
                pass
            else:
                PrintMsg('file: {0} not found.'.format(file))

        for folder in cleanupfolders:
            if os.path.isdir(folder):
                shutil.rmtree(folder, ignore_errors=True)

if __name__ == "__main__":
    main(sys.argv[1:])