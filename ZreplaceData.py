import time
import numpy as np
import pandas as pd
from laspy.tools import lasverify
from laspy.file import File
import sys
import os
import math
from multiprocessing import Pool,freeze_support
import subprocess
from random import randrange
from random import randint
from gooey import Gooey,GooeyParser
import random, string
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *



@Gooey(program_name="Make Data Obfuscated", use_legacy_titles=True, required_cols=2, optional_cols=3, advance=True, default_size=(1000,810))
def param_parser():
    parser=GooeyParser(description="Make Data Obfuscated")
    subs = parser.add_subparsers(help='commands', dest='command')
    part3_parser = subs.add_parser('Replace_Z', help='Create a Tile layout with last Edited tiles ')
    part3_parser.add_argument('source_data',metavar="Source Data", widget="DirChooser", help="Correct z")
    part3_parser.add_argument('target_data',metavar="Target Data", widget="DirChooser", help="incorrect z")
    part3_parser.add_argument("jsonfile", metavar="Tilelayout", widget="FileChooser",help="Provide the tilelayout")
    part3_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    part3_parser.add_argument('filetype',metavar="Input File Type", help="Select input file type", default='laz')
    part3_parser.add_argument("--cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)


    args = parser.parse_args()
    return args


def z_adjustData(tile, source_data,target_data,filetype,outputfolder):

    tilename = tile.name

    source_tile = os.path.join(source_data, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    target_tile = os.path.join(target_data, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    temp_outputfile = os.path.join(outputfolder, '{0}.{1}'.format(tilename,'las')).replace('\\','/')
    outputfile = os.path.join(outputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    
    #read the obfuscated tile
    sourcefile = File(source_tile, mode='r')
    targetfile = File(target_tile, mode='r')


    #get z values from source
    z_values=sourcefile.get_z_scaled()
    outfile = File(temp_outputfile, mode="w", header=targetfile.header)
    outfile.points=targetfile.points

    
    #Replace the z values from source file
    outfile.set_z_scaled(z_values)

    outfile.close()
    sourcefile.close()
    targetfile.close()


    #lascopy all x,y,z,classification based on the corrected gps time
    subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', temp_outputfile, '-olaz', '-o', outputfile]
    subprocessargs=list(map(str,subprocessargs))    
    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    if os.path.isfile(outputfile):
        #read the obfuscated tile
        log = f'Z replaced from {source_tile} -> {target_tile}'
        os.remove(temp_outputfile)
        print(log)

   
        return(True,outputfile,log)


    else:

        log = f'Failed replacing Z from {source_tile} -> {target_tile}'
        #os.remove(temp_outputfile)
        print(log)

        return(False,None,log)

def main():
 
    args = param_parser()

    
    

    if args.command=='Replace_Z':
        source_data = args.source_data
        target_data = args.target_data

        outputfolder = args.output_dir
        filetype = args.filetype
        ori_tl = args.jsonfile
        cores = args.cores

        outputfolder = AtlassGen.makedir(os.path.join(outputfolder, 'z_replacedData')).replace('\\','/')
        ori_Tilelayout = AtlassTileLayout()
        ori_Tilelayout.fromjson(ori_tl)

        source_filelist = AtlassGen.FILELIST([f'*.{filetype}'],source_data)
        target_filelist = AtlassGen.FILELIST([f'*.{filetype}'],target_data)

        print(f'\nNumber of files in the source dataset : {len(source_filelist)}')
        print(f'\nNumber of files in the target dataset :{len(target_filelist)}')

        tasks = {}

        for tile in ori_Tilelayout:
            tilename = tile.name
  
            tasks[tilename] = AtlassTask(tilename,z_adjustData,tile, source_data,target_data,filetype,outputfolder)

        p=Pool(processes=cores)    
        results=p.map(AtlassTaskRunner.taskmanager,tasks.values())
    

        log=os.path.join(outputfolder,'log.txt').replace("\\","/")
        f=open(log,'w')
        for result in results:
            #print(result.success, result.log)

            if result.success:
                f.write(result.log)

    return()
if __name__ == "__main__":
    main() 

