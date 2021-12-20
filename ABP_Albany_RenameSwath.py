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

@Gooey(program_name="ABP", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3,advance=True, navigation='SIDEBAR',)
def param_parser():

    stored_args = {}
    # get the script name without the extension & use it to build up
    # the json filename
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    congifg_folder = AtlassGen.makedir("C:\\pythontools")
    args_file = os.path.join(congifg_folder,"{}-args.json".format(script_name))
    # Read in the prior arguments as a dictionary
    if os.path.isfile(args_file):
        with open(args_file) as data_file:
            stored_args = json.load(data_file)

    parser=GooeyParser(description="ABP swaths")
    parser.add_argument("laspath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default=stored_args.get('laspath'))
    parser.add_argument("filetype",metavar="Input File type", help="laz or las", default='laz')
    parser.add_argument("outputfolder", metavar="output Directory",widget="DirChooser", help="output directory", default=stored_args.get('outputfolder'))    
    parser.add_argument("areaname", metavar="AreaName",default=stored_args.get('areaname'))
    parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
        
    args = parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args


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


def rename(inputlaz,outputlas):
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i' , inputlaz ,'-o', outputlas,'-olaz','-set_version', 1.4, '-set_point_type', 6 ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(outputlas):
            log = "Renaming Success output : {1}".format(str(outputlas))
            return (True,outputlas, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Could not rename {0}. Failed at Subprocess".format(str(inputlaz))
        return (False,None,log)

def rename_swath(swathfile,sid,swathname,filetype,lazpath,outputpath,areaname):
    ############################################################################
    attribs={}


    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    
    outputpathtxt = os.path.join(lazpath,'lasinfofiles').replace('\\','/')
    if not os.path.exists(outputpathtxt):
        AtlassGen.makedir(outputpathtxt)

    genLasinfo(swathfile,outputpathtxt)
    txtfile = os.path.join(outputpathtxt,'{0}.txt'.format(swathname))


    lines = [line.rstrip('\n')for line in open(txtfile)]

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

   

    print(minx,miny,maxx,maxy)
    width = abs(maxx-minx)
    height = abs(maxy-miny)

    width = (str(width).zfill(4))
    height = (str(height).zfill(4))

    print(swathfile)
    print(width,height)

    sfile = os.path.join(outputpath,'ABPWA2020_UNC_{0}_{1}.laz'.format(int(minx),int(miny)))
 
    rename(swathfile,sfile)
    

    return (True,sfile, 'log')

def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()

    lazpath = args.laspath
    filetype = args.filetype
    outputpath = args.outputfolder
    areaname = args.areaname
    cores = args.cores
    swaths = AtlassGen.FILELIST(['*.laz'], lazpath)
    #outputpath = AtlassGen.makedir(os.path.join(outputpath,areaname).replace('\\','/'))
    
    genrawfiles_task = {}
    for swathfile in swaths:
            path,swathname,ext = AtlassGen.FILESPEC(swathfile)
            
            print(swathname)
            sid = swathname.split('_')[2]
            print(sid)

            genrawfiles_task[swathname] = AtlassTask(swathname, rename_swath,swathfile,sid,swathname,filetype,lazpath,outputpath,areaname)
    
    p=Pool(processes=cores) 
    genlazinfo_task_resilts=p.map(AtlassTaskRunner.taskmanager,genrawfiles_task.values()) 

       
    return
    
if __name__ == "__main__":
    main() 



