#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import shutil
import subprocess
import os
import random
import argparse
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
import glob
from collections import defaultdict 
from collections import OrderedDict 
from gooey import Gooey, GooeyParser
from Atlass import *

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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=1, default_size=(800,600))
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    parser.add_argument("input_folder", metavar="Input Folder", widget="DirChooser", help="Select folder with las/laz files")
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='2000')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 20',
                'message': 'Must be between 2 and 20'
            }})
    parser.add_argument("output_file", metavar="Output File Name", help="Provide name for outputfile (.json)", default="TileLayout.json")
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    args = parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


   
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()

    tilesize=int(args.tile_size)
    filetype=args.file_type
    inputfolder=args.input_folder
    
    files = []
    files = glob.glob(inputfolder+"\\*."+filetype)
    cores=int(args.cores)
    outlasdir=args.output_dir
    outputfile = outlasdir+'\\'+args.output_file
    logger = Atlasslogger(outlasdir)

    print(len(files))
    tilelayout = AtlassTileLayout()

    print("Making initial geojson file from las files \n")
    #make a tile layout index
    for file in files:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilelayout.addtile(name=filename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)
        '''
        #Format for dictionary input
        tiles[filename] = {'name':filename,'xmin':float(x), 'ymin':float(y), 'xmax':float(x)+tilesize,'ymax':float(y)+tilesize, 'key1':'shsfhsfh', 'key2':'dfhdhd'}

        tilelayout.fromdict(tiles)
        '''

    
    outputfile = tilelayout.createGeojsonFile(outputfile)
    print("Creating geojson file : Completed\n")
    print("output file : {}/{}".format(os.path.dirname(os.path.realpath(__file__)), outputfile))
    
  
    return

if __name__ == "__main__":
    main()         


