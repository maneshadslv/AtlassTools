import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import json
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeHydroLib import *



def genLasinfo(lazfile,outputpathtxt):
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lazfile,'-otxt','-odir',outputpathtxt ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True,timeout=30)  
        return(True,None,log)


    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "generating lasinfo for {0} Exception - {1}".format(lazfile, e)
        print(log)
        return(False,None, log)

def movefile(inputfile,outputfile):
        try:
            shutil.move(inputfile, outputfile)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            return (False,None,log)

        finally:
            if os.path.isfile(outputfile):
                log = "\nMoving file {0} Success".format(inputfile)
                print(log)
                return (True,outputfile, log)

            else: 
                log = "\n **** Moving file {0} Failed ****".format(inputfile)
                return (False,outputfile, log)


def rename_swath(swathlazpath,wdpfilepath,outputpath,basename,psid):
    ############################################################################
    attribs={}
    
    try:
        swathlazfile = glob.glob(swathlazpath + "/**/*{0}_Channel_1 - originalpoints.las".format(basename), recursive = True)[0].replace('\\','/')
        print(swathlazfile)
        wdpfile = glob.glob(wdpfilepath + "//**/*{0}_Channel_1 - originalpoints.wdp".format(basename), recursive = True)[0].replace('\\','/')
        print(wdpfile)

    except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            return (False,None,log)


    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    
    outputpathtxt = os.path.join(outputpath,'lasinfofiles').replace('\\','/')
    if not os.path.exists(outputpathtxt):
        AtlassGen.makedir(outputpathtxt)


    genLasinfo(swathlazfile,outputpathtxt)
    lasinfofile = os.path.join(outputpathtxt,'export - Channel 1 - {0}_Channel_1 - originalpoints.txt'.format(basename)).replace('\\','/')


    lines = [line.rstrip('\n')for line in open(lasinfofile)]

    ##############################################################################

    #loop through tiles and summarise key attribs

    for line in lines:
        for attr in attribs.keys():
            #print(attr)
            if  attribs[attr] in line:
                line=line.replace(attribs[attr] ,'')
                line=line.strip(' ')
                attribs[attr]=line
    

    minx = round(float(attribs['min_xyz'].split(' ')[0]),0)
    miny = round(float(attribs['min_xyz'].split(' ')[1]),0)
    maxx = round(float(attribs['max_xyz'].split(' ')[0]),0)
    maxy = round(float(attribs['max_xyz'].split(' ')[1]),0)
    minx = int(str(minx)[:3])
    miny = int(str(miny)[:4])
    maxx = int(str(maxx)[:3])
    maxy = int(str(maxy)[:4])

   

    print(minx,miny,maxx,maxy)
    width = int(abs(maxx-minx))
    width = str(width)
    width = width.zfill(4)
    height = int(abs(maxy-miny))
    height = str(height)
    height = height.zfill(4)


    ####here################

    basefile = os.path.join(outputpath,'{0}_{1}.txt'.format(basename,psid)).replace('\\','/')

    wfile = wdpfile.replace('export - Channel 1 - {0}_Channel_1 - originalpoints.wdp'.format(basename),'MurrayRiver2021-UNC-ELL-{0}_{1}{2}_54_{3}_{4}.wdp'.format(psid,int(minx),int(miny),width,height))
    print(wfile)
    
    lasfile = wdpfile.replace('.wdp','.las')
 
    lfile = wfile.replace('.wdp','.las')
    print(lasfile,lfile)


    try:
        if os.path.isfile(wdpfile):
            print('wdp available to rename')
            os.rename(wdpfile,wfile)
        if os.path.isfile(lasfile):
            print('las available to rename')
            os.rename(lasfile,lfile)    
        with open(basefile,"a") as fw:
            fw.write("\n{0} -> {1}".format(wdpfile,wfile))
            fw.write("\n{0} -> {1}".format(lasfile,lfile))
            print('Renaming {0} to {1} Successfull'.format(wdpfile,wfile))
            print('Renaming {0} to {1} Successfull'.format(lasfile,lfile))
    except:
        print('Could not rename {0}'.format(wdpfile))
        with open(basefile,"a") as fw:
            fw.write("\n Falied to rename {0} -> {1}".format(wdpfile,wfile))


    

    return (True,wfile, wfile)


       
   
    
if __name__ == "__main__":

    #outputpath=F:\Manesha_work_MurrayRiver_WDP_renaming
    #python D:\AtlassTools\MurrayRiver21_WDP_Renamer.py #laspath# #wdppath# #outputpath# #basename# #psid#

    lazfilepath,wdpfilepath,outputpath,basename,psid = sys.argv[1:6]

    lazfilepath = lazfilepath.replace('\\','/')
    wdpfilepath = wdpfilepath.replace('\\','/')
    outputpath = outputpath.replace('\\','/')

    #print(outputpath)

    rename_swath(lazfilepath,wdpfilepath,outputpath,basename,psid)
     



