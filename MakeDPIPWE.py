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
__DebugMode=False #can be overritten by settings



defaults={}
defaults['tile']=None
defaults['xmin']=None 
defaults['ymin']=None
defaults['xmax']=None
defaults['ymax']=None

defaults['areaname']=None
defaults['laspath']=None
defaults['extn']=None
defaults['geoidlaz']=None
defaults['tilelayout']=None
defaults['storagepath']=None
defaults['workingpath']=None
defaults['deliverypath']=None

defaults['__keepfiles']=None

# stuff for DEM
defaults['hydropoints']=None
defaults['step']=None
defaults['buffer']=300
defaults['kill']=350
        
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
    
    #c:\python35-64\python \\10.10.10.142\projects\PythonScripts\MakeDPIPWE.py --tile=461000_7170000 --xmin=461000 --ymin=7170000 --xmax=462000 --ymax=7171000 --areaname=Bishopbourne --laspath=F:\Processing\Area01_Mary_GDA94MGA56\origtiles --tilelayout=F:\Processing\Area01_Mary_GDA94MGA56\origtiles\TileLayout.json --storagepath=W:\temp2\working\storage\NorthMidlands --workingpath=W:\temp2\working\working --deliverypath=W:\temp2\working\delivery\NorthMidlands --step=1.0 --extn=laz --geoidlaz=F:\Processing\Area01_Mary_GDA94MGA56\CSIROArea1.laz --buffer=250
    #c:\python35-64\python \\10.10.10.142\projects\PythonScripts\MakeDPIPWE.py --tile=#tile# --xmin=#xmin# --ymin=#ymin# --xmax=#xmax# --ymax=#ymax# --areaname=#areaname# --laspath=#laspath# --tilelayout=#tilelayout# --storagepath=#storagepath# --workingpath=#workingpath# --deliverypath=#deliverypath# --step=1.0 --extn=laz --geoidlaz="W:\DPIPWE\working\MGA55_Geoid_100m_ell_to_AHD.laz" --buffer=250 --hydropoints="W:\DPIPWE\Hydro_all_final_ahd03.laz" 

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

    geoidlaz=settings['geoidlaz']
    if not geoidlaz==None:
        geoidlaz=geoidlaz.replace('\\','/')
    else: 
        PrintMsg('geoidlaz not set')
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
    PrintMsg('Settin up workspace',Heading=True)
    workspace={}
    workspace['DEM']={}
    workspace['DEM']['relpath']='{0}/AHD_GDA2020/DEM_1m'.format(areaname)
    workspace['DEM']['nameconv']='{0}2019-DEM-1m_{1}{2}_GDA2020_55.tif'.format(areaname,int(round(xmin/1000,0)),int(round(ymin/1000,0)))
    workspace['DEM']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['DEM']['relpath']))
    workspace['DEM']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['DEM']['relpath']))
    workspace['DEM']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/AHD_GDA2020/DEM_1m'.format(areaname,tile)))
    cleanupfolders.append(workspace['DEM']['workingpath'])

    workspace['LAS_AHD']={}
    workspace['LAS_AHD']['relpath']='{0}/AHD_GDA2020/LAS_tiles_C2'.format(areaname)
    workspace['LAS_AHD']['nameconv']='{0}2019-C2-AHD_{1}{2}_GDA2020_55.las'.format(areaname,int(round(xmin/1000,0)),int(round(ymin/1000,0)))   
    workspace['LAS_AHD']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['LAS_AHD']['relpath']))
    workspace['LAS_AHD']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['LAS_AHD']['relpath']))
    workspace['LAS_AHD']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/AHD_GDA2020/LAS_tiles_C2'.format(areaname,tile)))
    cleanupfolders.append(workspace['LAS_AHD']['workingpath'])


    workspace['LAS_ELL']={}
    workspace['LAS_ELL']['relpath']='{0}/ELL_GDA2020/LAS_tiles_C2'.format(areaname)
    workspace['LAS_ELL']['nameconv']='{0}2019-C2-ELL_{1}{2}_GDA2020_55.las'.format(areaname,int(round(xmin/1000,0)),int(round(ymin/1000,0)))
    workspace['LAS_ELL']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['LAS_ELL']['relpath']))
    workspace['LAS_ELL']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['LAS_ELL']['relpath']))
    workspace['LAS_ELL']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/ELL_GDA2020/LAS_tiles_C2'.format(areaname,tile)))
    cleanupfolders.append(workspace['LAS_ELL']['workingpath'])

    workspace['LAS_ELL_UNC']={}
    workspace['LAS_ELL_UNC']['relpath']='{0}/ELL_GDA2020/LAS_tiles_UNC'.format(areaname)
    workspace['LAS_ELL_UNC']['nameconv']='{0}2019-UNC-ELL_{1}{2}_GDA2020_55.las'.format(areaname,int(round(xmin/1000,0)),int(round(ymin/1000,0)))    
    #workspace['LAS_ELL_UNC']['storagepath']=AtlassGen.makedir(os.path.join(storagepath,workspace['LAS_ELL_UNC']['relpath']))
    workspace['LAS_ELL_UNC']['deliverypath']=AtlassGen.makedir(os.path.join(deliverypath,workspace['LAS_ELL_UNC']['relpath']))
    workspace['LAS_ELL_UNC']['workingpath']=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/ELL_GDA2020/LAS_tiles_UNC'.format(areaname,tile)))
    cleanupfolders.append(workspace['LAS_ELL_UNC']['workingpath'])

    originaltiles=AtlassGen.makedir(os.path.join(workingpath,'{0}/{1}/ELL_GDA2020/Original_LAS_tiles'.format(areaname,tile)))
    cleanupfolders.append(originaltiles)
    cleanupfolders.append(os.path.join(workingpath,'{0}/{1}/ELL_GDA2020'.format(areaname,tile)))
    cleanupfolders.append(os.path.join(workingpath,'{0}/{1}/AHD_GDA2020'.format(areaname,tile)))
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


    # Create merged clipped ELL LAS1.2
    PrintMsg(Message="Making buffered las file",Heading=True)
    tempfile=os.path.join( workspace['LAS_ELL']['workingpath'],'{0}.las'.format(tile))
    cleanupfiles.append(tempfile)

    las_ell_file=os.path.join( workspace['LAS_ELL']['workingpath'],workspace['LAS_ELL']['nameconv'])
    cleanupfiles.append(las_ell_file)

    las_ell_unc_file=os.path.join( workspace['LAS_ELL_UNC']['workingpath'],workspace['LAS_ELL_UNC']['nameconv'])
    cleanupfiles.append(las_ell_unc_file)

    las_ahd_file=os.path.join( workspace['LAS_AHD']['workingpath'],workspace['LAS_AHD']['nameconv'])
    cleanupfiles.append(las_ahd_file)

    subprocessargs=['C:/LAStools/bin/las2las.exe','-i','{0}/*.{1}'.format(originaltiles,extn),'-merged','-olas','-o',tempfile,'-set_version','1.2']
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
    if __DebugMode:
        debugmessage=" ".join(str(x) for x in subprocessargs) 
        print(debugmessage)    

    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)  
    
    if os.path.isfile(tempfile):
        PrintMsg('buffered file created')

    PrintMsg(Message="Making ellipsoidal las file",Heading=True)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile,'-merged','-olas','-o',las_ell_file]
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    
    if __DebugMode:
        debugmessage=" ".join(str(x) for x in subprocessargs) 
        print(debugmessage)          
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    if os.path.isfile(las_ell_file):
        PrintMsg('ellipsoidal las file created')


        #zip
        subprocessargs=['C:/Program Files/WinRAR/RAR.exe','a','-m5',las_ell_file.replace('.las','.zip'),las_ell_file,'-ep','-o+']
        if __DebugMode:
            debugmessage=" ".join(str(x) for x in subprocessargs) 
            print(debugmessage)
        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)
             
          
        cleanupfiles.append(las_ell_file.replace('.las','.zip'))          
        PrintMsg('zipped for strorage')

        shutil.copy2(las_ell_file.replace('.las','.zip'),workspace['LAS_ELL']['deliverypath'])
        PrintMsg('copied to delivery')

        #copy to storage
        shutil.copy2(las_ell_file.replace('.las','.zip'),workspace['LAS_ELL']['storagepath'])      
        PrintMsg('coppied to storage')
        
        
    
    # Adjust to AHD
    PrintMsg(Message="Making AHD las file",Heading=True)
    subprocessargs=['C:/LAStools/bin/lasheight.exe','-i',las_ell_file,'-merged','-olas','-o',las_ahd_file]
    subprocessargs=subprocessargs+['-ground_points',geoidlaz,'-all_ground_points','-replace_z']
    
    if __DebugMode:
        debugmessage=" ".join(str(x) for x in subprocessargs) 
        print(debugmessage)
    
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)             
    
    if os.path.isfile(las_ahd_file):
        PrintMsg('AHD las file created')

        #zip
        subprocessargs=['C:/Program Files/WinRAR/RAR.exe','a','-m5',las_ahd_file.replace('.las','.zip'),las_ahd_file,'-ep','-o+']
        
        if __DebugMode:
            debugmessage=" ".join(str(x) for x in subprocessargs) 
            print(debugmessage)    

        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)

        cleanupfiles.append(las_ahd_file.replace('.las','.zip'))       
        PrintMsg('zipped for strorage')        

        shutil.copy2(las_ahd_file.replace('.las','.zip'),workspace['LAS_AHD']['deliverypath'])      
        PrintMsg('copied to delivery')

        #copy to storage
        shutil.copy2(las_ahd_file.replace('.las','.zip'),workspace['LAS_AHD']['storagepath'])      
        PrintMsg('coppied to storage')


    # Create unclassified ELL file
    PrintMsg(Message="Making ellipsoidal unclassified las file",Heading=True)
    subprocessargs=['C:/LAStools/bin/las2las.exe','-i',las_ell_file,'-merged','-olas','-o',las_ell_unc_file,'-set_classification','0']
    subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]
    
    if __DebugMode:
        debugmessage=" ".join(str(x) for x in subprocessargs) 
        print(debugmessage)

    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    if os.path.isfile(las_ell_unc_file):
        PrintMsg('ellipsoidal unclassified las file created')

        subprocessargs=['C:/Program Files/WinRAR/RAR.exe','a','-m5',las_ell_unc_file.replace('.las','.zip'),las_ell_unc_file,'-ep','-o+']
        
        if __DebugMode:
            debugmessage=" ".join(str(x) for x in subprocessargs) 
            print(debugmessage)

        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)

        PrintMsg('zipped for strorage') 

        shutil.copy2(las_ell_unc_file.replace('.las','.zip'),workspace['LAS_ELL_UNC']['deliverypath'])
        PrintMsg('copied to delivery')
        #not coppied to storage    

    # create a buffered ground file (+ hydro) for DEM creation

    tempfile2=tempfile
    tempfile=os.path.join( workspace['LAS_ELL']['workingpath'],'{0}_gnd.las'.format(tile))
    cleanupfiles.append(tempfile)    


    PrintMsg(Message="Making DEM ground file",Heading=True)
    subprocessargs=['C:/LAStools/bin/lasheight.exe','-i',tempfile2,'-olas','-o',tempfile]
    subprocessargs=subprocessargs+['-ground_points',geoidlaz,'-all_ground_points','-replace_z']
    subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer,'-keep_class',2,8]
     
    if __DebugMode:
        debugmessage=" ".join(str(x) for x in subprocessargs) 
        print(debugmessage)
    
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    print('dem ground prep file created')  

    if not hydropoints==None:
        tempfile2=tempfile
        tempfile=os.path.join( workspace['LAS_ELL']['workingpath'],'{0}_hydro.las'.format(tile))
        cleanupfiles.append(tempfile)    

        PrintMsg(Message="Making DEM hydro+ground file")
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydropoints,'-olas','-o',tempfile]
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
          
        if __DebugMode:
            debugmessage=" ".join(str(x) for x in subprocessargs) 
            print(debugmessage)

        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)     

        hydropoints=tempfile
        tempfile=os.path.join( workspace['LAS_ELL']['workingpath'],'{0}_hydro_gnd.las'.format(tile))
        cleanupfiles.append(hydropoints)    

        PrintMsg(Message="Making DEM hydro+ground file")
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,hydropoints,'-merged','-olas','-o',tempfile]
        subprocessargs=subprocessargs+['-keep_xy',xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer]
             
        if __DebugMode:
            debugmessage=" ".join(str(x) for x in subprocessargs) 
            print(debugmessage)

        subprocessargs=map(str,subprocessargs)
        subprocess.call(subprocessargs)

        PrintMsg('DEM hydro+ground file created')     

        if not os.path.isfile(tempfile):
            tempfile=tempfile2
          
    # create 1m DEM
    PrintMsg(Message="Making DEM")
    demfile=os.path.join( workspace['DEM']['workingpath'],workspace['DEM']['nameconv'])
    subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',tempfile,'-otif','-o',demfile,'-nbits',32,'-kill',kill,'-step',step]
    subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((xmax-xmin)/step), '-nrows',math.ceil((ymax-ymin)/step)]
    
    if __DebugMode:
        debugmessage=" ".join(str(x) for x in subprocessargs) 
        print(debugmessage)
        
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)    

    if os.path.isfile(demfile):
        PrintMsg('Dem file created')
        
        shutil.copy2(demfile,workspace['DEM']['deliverypath'])
        tempfile=demfile.replace('.tif','.tfw')
        shutil.copy2(tempfile,workspace['DEM']['deliverypath'])
        PrintMsg('copied to delivery')
        cleanupfiles.append(demfile)  
        cleanupfiles.append(tempfile)  

        #copy to storage
        shutil.copy2(demfile,workspace['DEM']['storagepath'])
        tempfile=demfile.replace('.tif','.tfw')
        shutil.copy2(tempfile,workspace['DEM']['storagepath'])
        PrintMsg('copied to storage')        

    # clean up workspace
    PrintMsg('Cleanup',Heading=True)
    if __keepfiles==None:
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
                pass

if __name__ == "__main__":
    main(sys.argv[1:])            