#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import shutil
import subprocess
import os
import random
import argparse
import struct
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
from collections import defaultdict 
from collections import OrderedDict 
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 29/03/2018 -Alex Rixon - Original development Alex Rixon
#

#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#This tool is used to tile data and run lastools ground clasification.

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
#-----------------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------
#Multithread Function definitions
#-----------------------------------------------------------------------------------------------------------------
# Function used to calculate result

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=1, default_size=(800, 500))
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    parser.add_argument("input_folder", metavar="Input Directory", widget="DirChooser", help="Select input las/laz files", default='')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("start", metavar="Enter the first swath/PSID number", type=int)
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 14',
                'message': 'Must be between 2 and 14'
            }})
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument("file_version",metavar="Las File Version", help="Enter las file version(Ex: 1.6)", default=1.6, type=float)  
    args = parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


def insertPSID(input, outlas, filetype, psid, channel, version):    
    log = ''

    try:

        if not version==1.4:
            subprocessargs=['c:\\lastools\\bin\\las2las.exe', '-i', input ,'-o{0}'.format(filetype), '-o', outlas,'-set_point_source', '{0}'.format(psid),'-set_user_data',channel,'-target_precision','0.001','-target_elevation_precision','0.001']
        else:
            subprocessargs=['c:\\lastools\\bin\\las2las.exe', '-i', input ,'-o{0}'.format(filetype), '-o', outlas,'-set_point_source', '{0}'.format(psid),'-set_extended_scanner_channel',channel,'-target_precision','0.001','-target_elevation_precision','0.001']
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\n insertPSID {0} \n Exception {1}".format(input, e)
        return(False,None, log)
    
    finally:
        print('\nInserting PSID completed for {0}'.format(input))
        log = '\nInserting PSID completed for {0}'.format(input)
        return (True, outlas, log)

 

  
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()

    filetype=args.file_type
    inputfolder=args.input_folder
    channel = 1
    version = args.file_version
    files = []
    files = glob.glob(inputfolder+"\\*."+filetype)

    print('Number of Files founds : {0} '.format(len(files)))

    cores=int(args.cores)
    outlasdir=args.output_dir
    psid = args.start

    logpath = os.path.join(outlasdir,'log_insertPSIDtoLAS.txt').replace('\\','/')
    log = open(logpath, 'w')

    dt = strftime("%y%m%d_%H%M")
    workingdir = AtlassGen.makedir(os.path.join(outlasdir, '{0}_PSID'.format(dt))).replace('\\','/')


  
  
    PSID_TASKS={}

    for file in files:
    
        path, filename, ext = AtlassGen.FILESPEC(file)

        #files
        input = file
        output=AtlassGen.makedir(os.path.join(workingdir,filename))

        PSID_TASKS[filename] = AtlassTask(filename, insertPSID, input, output, filetype, psid, channel, version)
        psid +=1

    p=Pool(processes=cores)      
    PSID_RESULTS=p.map(AtlassTaskRunner.taskmanager,PSID_TASKS.values())


    #write log
    for result in PSID_RESULTS:
        log.write(result.log)  


    return

if __name__ == "__main__":
    main()         

