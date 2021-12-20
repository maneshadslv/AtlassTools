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
# 25/02/2020 -Alex Rixon - Original development Alex Rixon
# 
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#Tool is designed to identify void areas (no points or only water) in LiDAR tiles
#Void areas are returned with heights from a lowest point grid generated from ground and water points


#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings


defaults={}
defaults['tile']=None
defaults['aoi']=None
defaults['workingpath']=None
defaults['lazfile']=None
defaults['xmin']=None
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None
defaults['step']=1.0
defaults['fill']=25
defaults['__keepfiles']=None


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

def cleanfiles(cleanupfiles,cleanupfolders=None):
    # clean up workspace
    PrintMsg('Cleanup',Heading=True)
    for file in cleanupfiles:
        if os.path.isfile(file):
            os.remove(file)
            PrintMsg('file: {0} removed.'.format(file))
            pass
        else:
            PrintMsg('file: {0} not found.'.format(file))
    if not cleanupfolders==None:
        for folder in cleanupfolders:
            if os.path.isdir(folder):
                #shutil.rmtree(folder, ignore_errors=True)
                pass

    return

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------
    
    #python \\10.10.10.142\projects\PythonScripts\MakeHYDRO_GRIDS_New.py --tile=#name# --lazfile=W:\processing\BR01381_Burdekin_and_Haughton_Rivers-Burdekin_Shire_Council\GDA94_MGA_Z55_Burdekin_1911_xyz_adj_191204\#name#.laz --aoi="W:\processing\BR01381_Burdekin_and_Haughton_Rivers-Burdekin_Shire_Council\AOI\Cutting_aoi_new\buff.shp" --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --step=2 --fill=20 --workingpath=W:\processing\BR01381_Burdekin_and_Haughton_Rivers-Burdekin_Shire_Council\hydro_test2


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

    aoi=settings['aoi']
    if not aoi==None:
        aoi=aoi.replace('\\','/')
    else: 
        PrintMsg('aoi not set')
        #return

    lazfile=settings['lazfile']
    if not lazfile==None:
        lazfile=lazfile.replace('\\','/')
    else: 
        PrintMsg('lazfile not set')
        return


    xmin=settings['xmin']
    if not xmin==None:
        xmin=float(xmin)
        pass
    else:
        PrintMsg('xmin not set')
        return

    ymin=settings['ymin']
    if not ymin==None:
        ymin=float(ymin)
        pass
    else:
        PrintMsg('ymin not set')
        return

    xmax=settings['xmax']
    if not xmax==None:
        xmax=float(xmax)
        pass
    else:
        PrintMsg('xmax not set')
        return

    ymax=settings['ymax']
    if not ymax==None:
        ymax=float(ymax)
        pass
    else:
        PrintMsg('ymax not set')
        return

    step=settings['step']
    if not step==None:
        step=float(step)
        pass
    else:
        PrintMsg('step not set')
        return

    fill=settings['fill']
    if not fill==None:
        fill=int(fill)
        pass
    else:
        PrintMsg('fill not set')
        return

    workingpath=settings['workingpath']
    if not workingpath==None:
        cleanupfiles=[]

        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
    else: 
        PrintMsg('workingpath not set')
        return

    #make void
    #makes values where not water or voids
    voidfile=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'01_hydro_voids')),'{0}_void.asc'.format(tile)).replace('\\','/')
    cleanupfiles.append(voidfile)

    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',lazfile,'-oasc','-o',voidfile,'-step',step,'-elevation_highest','-nodata',-9999 ]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',int((ymax-ymin)/step),'-ncols',int((xmax-xmin)/step)]
    subprocessargs=subprocessargs+['-subcircle',step,'-fill',0]
    subprocessargs=subprocessargs+['-keep_class',0,1,2,3,4,5,6,8,10,11,13,14,15,16,17,18,19,20] #class 9 and 7 missing from here
    
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs) 

    #make water
    #makes values where water exists
    water=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'01_hydro_voids')),'{0}_water.asc'.format(tile)).replace('\\','/')
    cleanupfiles.append(water)

    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',lazfile,'-oasc','-o',water,'-step',step,'-elevation_lowest','-nodata',-9999 ]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',int((ymax-ymin)/step),'-ncols',int((xmax-xmin)/step)]
    subprocessargs=subprocessargs+['-keep_class',9]
    
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)     

    #make height source
    heightsource=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'02_height_source')),'{0}.asc'.format(tile)).replace('\\','/')
    cleanupfiles.append(heightsource)

    subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',lazfile,'-oasc','-o',heightsource,'-step',step,'-elevation_lowest','-nodata',-9999 ]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-nrows',int((ymax-ymin)/step),'-ncols',int((xmax-xmin)/step)]
    subprocessargs=subprocessargs+['-subcircle',step,'-fill',fill]
    subprocessargs=subprocessargs+['-keep_class',2,9]
    
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs)     

    
    
    


    #Void File
    hydrovoid_asc=AsciiGrid()
    hydrovoid_asc.readfromfile(voidfile)

    #water file
    water_asc=AsciiGrid()
    water_asc.readfromfile(water)

    #DEM file
    heightsource_asc=AsciiGrid()
    heightsource_asc.readfromfile(heightsource)

    ones=np.array(np.ones((heightsource_asc.grid.shape[0],heightsource_asc.grid.shape[1])), ndmin=2, dtype=int)
    zeros=ones*0
    nodata=ones*heightsource_asc.nodata_value

    # extract hydro void areas
    hydrovoids=ones*(hydrovoid_asc.grid==hydrovoid_asc.nodata_value)
    
    # extract cells that contain water
    watervoids=ones*(water_asc.grid!=water_asc.nodata_value)

    #extract height source in cells
    
    hydrovoids_dem_file=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'03_heighted_voids')),'{0}.asc'.format(tile)).replace('\\','/')
    cleanupfiles.append(heightsource)    

    hydrovoids_dem=AsciiGrid() 
    hydrovoids_dem.header=hydrovoid_asc.header
    hydrovoids_dem.grid=np.where((hydrovoids==1)|(watervoids==1),heightsource_asc.grid,nodata)   #if either void or water is true then retun dem
    hydrovoids_dem.savetofile(hydrovoids_dem_file)

    hydrovoidfilelaz=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'03_heighted_voids')),'{0}.laz'.format(tile)).replace('\\','/')
    cleanupfiles.append(hydrovoidfilelaz)  
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydrovoids_dem_file,'-olaz','-o',hydrovoidfilelaz,'-rescale',0.001,0.001,0.001]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    
    subprocessargs=['C:/LAStools/bin/lasindex.exe','-i',hydrovoidfilelaz]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    hydrovoidfilelaz_clipped=os.path.join(AtlassGen.makedir(os.path.join(workingpath,'04_heighted_voids_clipped')),'{0}.laz'.format(tile)).replace('\\','/')
    subprocessargs=['C:/LAStools/bin/lasclip.exe','-i',hydrovoidfilelaz,'-olaz','-o',hydrovoidfilelaz_clipped,'-poly',aoi]
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    #cleanfiles(cleanupfiles)

if __name__ == "__main__":
    main(sys.argv[1:])