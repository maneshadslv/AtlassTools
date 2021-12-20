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
defaults['laspath']=None
defaults['extn']=None
defaults['tilelayout']=None
defaults['aoi']=None
defaults['storagepath']=None
defaults['workingpath']=None
defaults['deliverypath']=None

defaults['__keepfiles']=None

# stuff for DEM
defaults['hydropoints']=None
defaults['step']=None
defaults['buffer']=500
defaults['kill']=500
        
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
    
    #python C:\AtlassTools\MakeHYDRO_GRIDS.py --tile=#name# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --areaname=Bishopbourne --laspath=F:\Processing\Area01_Mary_GDA94MGA56\origtiles --tilelayout=F:\Processing\Area01_Mary_GDA94MGA56\origtiles\TileLayout.json --storagepath=W:\temp2\working\storage\NorthMidlands --workingpath=W:\temp2\working\working --deliverypath=W:\temp2\working\delivery\NorthMidlands --step=1.0 --extn=laz --buffer=250


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
    step=float(settings['step'])
    buffer=float(settings['buffer'])

    areaname=settings['areaname']

    laspath=settings['laspath']
    if not laspath==None:
        laspath=laspath.replace('\\','/')
    else: 
        PrintMsg('laspath not set')
        return

    extn=settings['extn']
    if not extn==None:
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
    if not workingpath==None:
        deliverypath=AtlassGen.makedir(deliverypath.replace('\\','/'))
    else: 
        PrintMsg('Delivery path path not set')
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
    PrintMsg('Settin up workspace',Heading=True)
    originaltiles=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/Original_LAS_tiles'.format(areaname,tile)))
    cleanupfolders.append(originaltiles)
    cleanupfolders.append(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)))
    
    # Get overlapping tiles in buffer
    PrintMsg(Message="Getting Neighbours",Heading=True)
    neighbours=tilelayout.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    PrintMsg('{0} Neighbours detected'.format(len(neighbours)))
    PrintMsg('Copying to workspace')


    mergedlas=os.path.join( os.path.join(workingpath,'{0}/{1}'.format(areaname,tile)),'{0}.laz'.format(tile))
    #if os.path.isdir(os.path.join(workingpath,'{0}/{1}'.format(areaname,tile))):
    #    return
    cleanupfiles.append(mergedlas)

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


    #excluding water, noise and low veg
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(originaltiles,extn),'-merged','-olaz','-o',mergedlas,'-keep_class'] + [0,1,2,4,5,6,8,10,13,14,15]
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)     
    
    if os.path.isfile(mergedlas):
        PrintMsg('buffered file created')
    else:
        PrintMsg('buffered file not created')
        return

    '''
    This bit Manesha
    ----------------------------------------------------------------------------------------------------
    '''
    #make a dsm grid for lowest elevation using subcircle and fill - clip to tile
    PrintMsg(Message="Making hydro grid1")
    dsmtempfile1=mergedlas.replace('.laz','_HYDRO.asc')
    cleanupfiles.append(dsmtempfile1)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-oasc','-o',dsmtempfile1,'-nbits',32,'-elevation_lowest','-step',step,'-subcircle',step,'-fill',1]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    

    '''
    to here
    -------------------------------------------------------------------------------------------------------
    '''

    '''
    #make a dsm grid for lowest elevation using subcircle and fill - not clipped to tile
    PrintMsg(Message="Making hydro grid2")
    dsmtempfile2=mergedlas.replace('.laz','_low_elev.laz')
    cleanupfiles.append(dsmtempfile2)
    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedlas,'-olaz','-o',dsmtempfile2,'-nbits',32,'-elevation_lowest','-step',step,'-subcircle',step,'-fill',1]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    
    '''
    deminput=[mergedlas]

    if not hydropoints==None:
        hydro=dsmtempfile3=mergedlas.replace('.laz','_hydro.laz')
        
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydropoints,'-olaz','-o',hydro,'-set_classification'] + [2]
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer*3,ymin-buffer*3,xmax+buffer*3,ymax+buffer*3]
        subprocessargs=map(str,subprocessargs)        
        subprocess.call(subprocessargs)     
        deminput.append(hydro)

    #make a dsm grid for triangulated elevation - clip to tile
    PrintMsg(Message="Making DEM grid")
    dsmtempfile3=mergedlas.replace('.laz','_DEM.asc')
    cleanupfiles.append(dsmtempfile3)
    subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i']+deminput+['-merged','-oasc','-o',dsmtempfile3,'-nbits',32,'-step',step,'-kill',kill,'-keep_class'] + [2]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    


    '''
    This bit Manesha
    ----------------------------------------------------------------------------------------------------
    '''
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

    #outputting voids with dem heights
    hydrovoids_dem.grid=np.where(hydrovoids==1,b.grid,nodata)
    hydrovoidfile=mergedlas.replace('.laz','_HYDRO_Voids_Height.asc')
    hydrovoids_dem.savetofile(hydrovoidfile)         

    hydrovoidfilelaz=mergedlas.replace('.laz','_HYDRO_Voids_Height.laz')
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydrovoidfile,'-olaz','-o',hydrovoidfilelaz,'-rescale',0.001,0.001,0.001]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)    


    '''
    ##### add this bit 
    #### lasclip -i hydro_raw.laz -poly aoi.shp -o hydro_raw_clipped.laz -olaz 
    to here
    -------------------------------------------------------------------------------------------------------
    '''
    hydrovoidfilelazClipped=os.path.join(deliverypath,'{0}_HYDRO_Voids_Height_Clipped.laz'.format(tile)).replace('\\','/')
    print(hydrovoidfilelazClipped)
    subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i',hydrovoidfilelaz,'-merged', '-poly', aoi, '-o', hydrovoidfilelazClipped, '-olaz']
    subprocessargs=list(map(str,subprocessargs))    
    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)



    # clean up workspace
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
            #shutil.rmtree(folder, ignore_errors=True)
            pass

if __name__ == "__main__":
    main(sys.argv[1:])            