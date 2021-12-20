import sys, getopt
import math
import shutil
import subprocess
import os, glob
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

@Gooey(program_name="Check LAS Header for attributes", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=2)
def param_parser():
    main_parser=GooeyParser(description="Check Header")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputfolder", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filetype",metavar="Input File Type", default='laz')
    main_parser.add_argument("attrib",metavar="Attribute To search", default='')
    main_parser.add_argument("cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    
    return main_parser.parse_args()
    
def FILESPEC(filename):
    # splits file into components
    path,name=os.path.split(filename)
    name,ext=name.split(".")
    return path, name, ext  
    
def FILELIST (Path,extn):
    filedetails = []
    for infile in glob.glob( os.path.join(Path, '{0}'.format(extn)) ):
        filedetails.append(infile.replace("\\","/"))
    return filedetails   

def genLasinfo(lazfile,tilename,outputdir,filetype,attrib):
  
    #genLasinfo(lazfile)
    lasinfofile = os.path.join(outputdir,'{0}.txt'.format(tilename)).replace("\\","/")

    subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lazfile,'-otxt','-o',lasinfofile]
    subprocessargs=list(map(str,subprocessargs))
    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  


    with open(lasinfofile) as f:

        if not attrib in f.read():
            return (True,'{0}.{1}'.format(tilename,filetype),"Found")
    

        else:
            return(False,'{0}.{1}'.format(tilename,filetype),"NotFound")

def main():
   
    print("\n\n\nStarting Program \n")
    freeze_support() 
    #Set Arguments
    args = param_parser()
    

    inputdir = args.inputfolder
    outputdir = args.outputfolder
    filetype = args.filetype
    attrib = args.attrib
    cores = args.cores
    listoffiles = os.path.join(outputdir,'OutputFileList_NotFound.txt').replace("\\","/")
    listoffiles_False = os.path.join(outputdir,'OutputFileList_Found.txt').replace("\\","/")

    checkedList = []



    files=FILELIST (inputdir,'*.{0}'.format(filetype))

    print("No of files found :  {0} ".format(len(files)))

  
    test_task={}
    for lazfile in files:
        path,tilename,extn=FILESPEC(lazfile)
        test_task[tilename] = AtlassTask(tilename,genLasinfo,lazfile,tilename,outputdir,filetype,attrib)



    p=Pool(processes=cores)   
    results=p.map(AtlassTaskRunner.taskmanager,test_task.values()) 


    false = []

    af = open(listoffiles,"w+")
    nf = open(listoffiles_False,"w+")
    for result in results:
        if result.success:
  
            af.write('{0}\n'.format(result.result))
            checkedList.append(result.result)    
            
        else:
            nf.write('{0}\n'.format(result.result))
            checkedList.append(result.result)            
            if result.log == 'NotFound':
                false.append()    

    af.close
    nf.close

    print("No of Files found without the attribute {0}:  {1}".format(attrib, len(false)))

    return
    
if __name__ == "__main__":
    main() 
