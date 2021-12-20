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

locations=[]

defaults={}
defaults['tile']=None #(delivery tile name)
defaults['tilelayout_1km']=None #delivery tilelayout 
defaults['tilelayout']=None #storage tilelayout
defaults['workingpath']=None #location to process and store results
defaults['lazpath']=None #location to process and store results
defaults['avggnd_lazpath']=None #location to process and store result
defaults['__keepfiles']=None

#constants
buffer=250
kill=500
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
    #python "\\10.10.10.142\projects\PythonScripts\MakeBrisbaneIpswich_QA.py" --tile=#name# --workingpath=F:\Processing\BR01280_Brisbane_to_Ipswich\Merged_classified_current_version_20191022_QA --tilelayout='F:\Processing\BR01280_Brisbane_to_Ipswich\Merged_classified_current_version_20191022\TileLayout.json' --avggnd_lazpath=


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
        #workspace for storing outputs
        workingpath=AtlassGen.makedir(workingpath.replace('\\','/'))
        temppath=AtlassGen.makedir(os.path.join(workingpath,'temp'))

        #temp workspace for tile processing
        tempworkspace=AtlassGen.makedir(os.path.join(temppath,'{0}'.format(tile)))

    else:
        PrintMsg('workingpath not set')
        return

    tilelayout=settings['tilelayout']
    if not tilelayout==None:
        tilelayout=tilelayout.replace('\\','/')
        tilelayout_tl = AtlassTileLayout()
        tilelayout_tl.fromjson(tilelayout)
        pass
    else:
        PrintMsg('tilelayout not set')
        return

    lazpath=settings['lazpath']
    if not lazpath==None:
        lazpath=lazpath.replace('\\','/')
        pass
    else:
        PrintMsg('lazpath not set')
        return

    avggnd_lazpath=settings['avggnd_lazpath']
    if not avggnd_lazpath==None:
        avggnd_lazpath=avggnd_lazpath.replace('\\','/')
        pass
    else:
        PrintMsg('avggnd_lazpath not set')
        return

    

    '''
    ----------------------------------------------------------------------------------------------
    preparation
    ----------------------------------------------------------------------------------------------
    copy tiles within buffer
    ----------------------------------------------------------------------------------------------
    '''
    tileinfo=tilelayout_tl.tiles[tile]
    xmin=tileinfo.xmin
    xmax=tileinfo.xmax
    ymin=tileinfo.ymin
    ymax=tileinfo.ymax

    '''
    ---------------------------------------------------------------------------------------------------------------------------------------
    original tiles
    ---------------------------------------------------------------------------------------------------------------------------------------
    '''
    cleanupfolders.append(tempworkspace)
    originallaz=os.path.join(lazpath,'{0}.laz'.format(tile))
    heightlaz=os.path.join(avggnd_lazpath,'{0}.laz'.format(tile))
    heightlazinv=os.path.join(tempworkspace,'{0}_hgt_inv.laz'.format(tile))
    normlaz=os.path.join(workingpath,'{0}_norm.laz'.format(tile))
    finallaz=os.path.join(workingpath,'{0}.laz'.format(tile))

    #normalize the laz tile
    mergedoriginal=os.path.join(tempworkspace,'mergedoriginal.laz')
    subprocessargs=['C:/LAStools/bin/lasheight64.exe','-i',originallaz,'-olaz','-o',normlaz,'-ground_points',heightlaz,'-all_ground_points','-replace_z']
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    PrintMsg('normalised-- {0}'.format(os.path.isfile(normlaz)),Heading=True)

    subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',heightlaz,'-olaz','-o',heightlazinv,'-scale_z',-1]
    subprocessargs=map(str,subprocessargs) 
    subprocess.call(subprocessargs)  

    PrintMsg('heightlazinv-- {0}'.format(os.path.isfile(heightlazinv)),Heading=True)


    laztests=[]
    #laztests.append(['_very_low',-999,-10.0001,[0,1,2,3,4,5,6,8,10,11,12,13,14,15,16,17,18,19,20],7])
    #laztests.append(['_very_high',150,9999,[0,1,2,3,4,5,6,8,10,11,12,13,14,15,16,17,18,19,20],7])
    #laztests.append(['_high',50,149.999,[0,1,2,3,4,5,6,8,10,11,12,13,14,15,16,17,18,19,20],None])
    #laztests.append(['_med_non_bldveg',2,49.999,[0,1,2,7,8,10,11,12,13,14,15,16,17,18,19,20],None])
    #laztests.append(['_med_veg',2,49.999,[3,4,5],None])
    #laztests.append(['_med_bld',2,49.999,[6],None])
    #laztests.append(['_unk_near',-0.5,2,[0,1],None])
    #laztests.append(['_high_ground',1,10,[2],None])
    #laztests.append(['_low_ground_noise',-10,-2,[2],7])
    #laztests.append(['_low_ground_check',-2,-1,[2],None])
    laztests.append(['_-62_-50',-62,-50,[2],None])
    laztests.append(['_-50_0',-50,0,[2],None])
    laztests.append(['_0_4',0,4,[2],None])
    laztests.append(['_4_100',4,100,[2],None])
    for test in laztests:
        ofilenorm=os.path.join(workingpath,'{0}{1}.laz'.format(tile,test[0]))
        ofile=os.path.join(workingpath,'{0}{1}.laz'.format(tile,test[0]))
        low=test[1]
        high=test[2]
        classes=test[3]
        
        subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',normlaz,'-olaz','-o',ofilenorm,'-keep_z',low,high,'-keep_class']+classes
        if not test[4]==None:
            subprocessargs=subprocessargs+['-set_classification',test[4]]  
        subprocessargs=map(str,subprocessargs) 
        subprocess.call(subprocessargs)  
        PrintMsg('{0}-- {1}'.format(ofilenorm,os.path.isfile(ofilenorm)),Heading=True)        

        #subprocessargs=['C:/LAStools/bin/lasheight64.exe','-i',ofilenorm,'-olaz','-o',ofile,'-ground_points',heightlazinv,'-all_ground_points','-replace_z']
        #subprocessargs=map(str,subprocessargs) 
        #subprocess.call(subprocessargs)  
        #PrintMsg('{0}-- {1}'.format(ofile,os.path.isfile(ofile)),Heading=True)        

    '''
    ---------------------------------------------------------------------------------------------------------------------------------------
    cleanup workspace
    ---------------------------------------------------------------------------------------------------------------------------------------
    '''
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