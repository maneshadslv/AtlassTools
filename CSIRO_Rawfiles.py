#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import math
import shutil
import subprocess
import os, glob
import numpy as np
import urllib
from gooey import Gooey, GooeyParser
import time
import datetime
from time import strftime
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make TMR products", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Make TMR products")
    main_parser.add_argument("inputpath", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("processpath", metavar="Processing Folder",widget="DirChooser")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("deliverypath", metavar="Delivery Folder", widget="DirChooser")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("groundfile", metavar="ground file for ELL gen", widget="FileChooser", default='')
    main_parser.add_argument("epsg", metavar="EPSG", type=int)
    main_parser.add_argument("dz", metavar="dz", type=float)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)

    return main_parser.parse_args()
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def copyfile(input, output):
    log = ''
    try:
        shutil.copyfile(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            log = "Copying file for {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Copying file for {} Failed".format(input)
            return (False,output, log)

def adjust(input, output, dx, dy, dz, epsg, filetype):
    #las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i' , input ,'-o{0}'.format(filetype), '-translate_xyz', dx, dy, dz, '-epsg', epsg ,'-set_version', 1.2,  '-o', output]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(output):
            log = "Adjusting {0} output : {1}".format(str(input), str(output))
            return (True,output, log)

        else:
            log = "Could not adjust : {0}".format(str(input))
            return (False,None,log)
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Could not adjust {0}. Failed at Subprocess".format(str(input))
        return (False,None,log)

def copytree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copyfile(s, d)
            if os.path.isfile(d):
                return(True,None,d)

            else:
                return(False,None,"Could not copy {0}".format(dst))
    return (True,None,"Copied")

def genell(inputfile, outputfile,groundfile):
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasheight.exe', '-i' , inputfile ,'-o', outputfile,'-ground_points', groundfile, '-all_ground_points', '-replace_z']
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(outputfile):
            log = "ELL for {0} output : {1}".format(str(input), str(outputfile))
            return (True,outputfile, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Could not adjust {0}. Failed at Subprocess".format(str(inputfile))
        return (False,None,log)


def dostuff( filename, inputfolder, workingdir,outputfolder, deliveryfolder,dz,epsg,groundfile):
    adjfolder = AtlassGen.makedir(os.path.join(workingdir,"Z_adjusted"))
    ahdfolder = AtlassGen.makedir(os.path.join(adjfolder, "LAS_AHD"))
    ellfolder = AtlassGen.makedir(os.path.join(adjfolder, 'LAS_ELL'))


    inputfile = os.path.join(inputfolder, '{0}.laz'.format(filename)).replace('\\','/')
    workingfile = os.path.join(workingdir,'{0}.laz'.format(filename)).replace('\\','/')
    adjahdfile = os.path.join(ahdfolder,'{0}.las'.format(filename)).replace('\\','/')
    ellfilename = filename.replace("-AHD-","-ELL-")
    adjellfile = os.path.join(ellfolder, '{0}.las'.format(ellfilename)).replace('\\','/')

    print("Working with {0}".format(filename))
    
    copy_result=copyfile(inputfile,workingfile)
    log = ''
  
    if copy_result[0]:
        print("Adjusting {0}".format(filename))
        adj_result = adjust(workingfile,adjahdfile,0.0,0.0,dz,epsg,'las')
    
    log = copy_result[2]

    if adj_result[0]:
        print("Creating ELL for {0}".format(filename))
        genell_result = genell(adjahdfile,adjellfile,groundfile)
    
    log = log + adj_result[2]
    
    if genell_result[0]:
        log = log + genell_result[2]
  
        print("Copying File {0} to Delivery Drive".format(filename))
        copy_path_AHD = AtlassGen.makedir(os.path.join(deliveryfolder, "LAS_AHD").replace('\\','/'))
        copy_path_ELL = AtlassGen.makedir(os.path.join(deliveryfolder, "LAS_ELL").replace('\\','/'))
        delivery_AHD_FILE = os.path.join(copy_path_AHD,'{0}.las'.format(filename)).replace('\\','/')
        delivery_ELL_FILE = os.path.join(copy_path_ELL,'{0}.las'.format(ellfilename)).replace('\\','/')

        copy_result_AHD=copyfile(adjahdfile,delivery_AHD_FILE)
        copy_result_ELL=copyfile(adjellfile,delivery_ELL_FILE)

        log = ''
    
    if copy_result_AHD[0] and copy_result_ELL[0] :
        print("Copying files Successful ! \nDeleteing files on the processing location")
        os.remove(workingfile)
        os.remove(adjahdfile)
        os.remove(adjellfile)
        print("Deleting workspace for file {0} Successful !".format(filename))
        return(True,None,log)
    
    else:
        return(False,None,log)

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    print("Starting Program \n\n")

    freeze_support() 

    #Set Arguments
    args = param_parser()

    inputfolder = args.inputpath
    processfolder = args.processpath
    groundfile = args.groundfile
    cores = args.cores
    filepattern = args.filepattern.split(';')
    outputfolder = args.outputpath
    deliveryfolder = args.deliverypath
    epsg = args.epsg
    dz = args.dz


    print("Reading {0} files \n".format(filepattern))
    files = AtlassGen.FILELIST(filepattern, inputfolder)

    workingdir = os.path.join(processfolder,"working").replace('\\','/')

    DOSTUFF_TASK = {}
    
    for file in files:
        path, filename, ext = AtlassGen.FILESPEC(file)

        
        DOSTUFF_TASK[file] = AtlassTask(filename, dostuff,  filename, inputfolder, workingdir,outputfolder, deliveryfolder,dz,epsg,groundfile)

    p=Pool(processes=cores)      
    dostuff_results=p.map(AtlassTaskRunner.taskmanager,DOSTUFF_TASK.values())
    

    for result in dostuff_results:
        if not result.success:
            print(result.log)


    print("Process Complete")
    return


if __name__ == "__main__":
    main()         
