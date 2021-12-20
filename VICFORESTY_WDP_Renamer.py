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
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  
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


def rename_swath(swathlazfile,wdpfile,outputpath,lasinfopath,basename):
    ############################################################################
    attribs={}


    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    
    outputpathtxt = os.path.join(outputpath,'lasinfofiles').replace('\\','/')
    if not os.path.exists(outputpathtxt):
        AtlassGen.makedir(outputpathtxt)


    lasinfofiles = glob.glob('{0}\*{1}*.txt'.format(lasinfopath,basename))

    if len(lasinfofiles) > 0:
        lasinfofile = lasinfofiles[0]
    else:
        lasinfofile = None

    if lasinfofile == None:

        genLasinfo(swathlazfile,outputpathtxt)
        lasinfofile = os.path.join(outputpathtxt,'{0}.txt'.format(basename)).replace('\\','/')

    else:
        print('lasinfo file found for {0}'.format(basename))

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
    minx = int(str(minx)[:4])
    miny = round(float(attribs['min_xyz'].split(' ')[1]),0)
    miny = int(str(miny)[:5])

    maxx = round(float(attribs['max_xyz'].split(' ')[0]),0)
    maxy = round(float(attribs['max_xyz'].split(' ')[1]),0)

   

    print(minx,miny,maxx,maxy)

    basefile = os.path.join(outputpathtxt,f'{basename}.txt').replace('\\','/')
    wdfile = os.path.join(outputpath,wdpfile).replace('\\','/')
    wfile = os.path.join(outputpath,'e{0}n{1}_EasternVictoria_2019_mpts-unc_v10cm_ell-mga55.wdp'.format(int(minx),int(miny))).replace('\\','/')
    
    lasfile = os.path.join(outputpath,swathlazfile).replace('\\','/')    
    lfile = os.path.join(outputpath,'e{0}n{1}_EasternVictoria_2019_mpts-unc_v10cm_ell-mga55.las'.format(int(minx),int(miny))).replace('\\','/')



    try:
        os.rename(wdfile,wfile)
        os.rename(lasfile,lfile)    
        with open(basefile,"a") as fw:
            fw.write("\n{1} -> {0}".format(wfile,wdfile))
    except:
        print('Could not rename {0}'.format(wdfile))
        with open(basefile,"a") as fw:
            fw.write("\n Falied to rename {1} -> {0}".format(wfile,wdfile))

    print('Renaming {0} to {1}'.format(wdfile,wfile))
    

    return (True,wfile, wfile)


       
   
    
if __name__ == "__main__":
   
    lazfile,wdpfile,outputpath,lasinfopath,basename = sys.argv[1:6]

    lazfile = lazfile.replace('\\','/')
    wdpfile = wdpfile.replace('\\','/')
    outputpath = outputpath.replace('\\','/')
    lasinfopath = lasinfopath.replace('\\','/')
    print(outputpath)

    rename_swath(lazfile,wdpfile,outputpath,lasinfopath,basename)
     



