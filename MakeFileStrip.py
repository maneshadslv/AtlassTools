#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import shutil
import subprocess
import os
import random
import argparse
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=1, default_size=(800, 500))
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    parser.add_argument("input_folder", metavar="Files", widget="DirChooser", help="Select input las/laz files", default=' ')
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='2000')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default=" ")
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 14',
                'message': 'Must be between 2 and 14'
            }})
    parser.add_argument("output_file", metavar="Output File Name", help="Provide name for outputfile", default="TileLayout.json")
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    args = parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


def TileStrip(file,outpath,tilesize,filetype):    
    filepath,filename,extn=AtlassGen.FILESPEC(file)  
    tilepath=AtlassGen.makedir(os.path.join(outpath,filename))

    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i',file] 
        subprocessargs=map(str,subprocessargs)    
        subprocess.call(subprocessargs) 
        subprocessargs=['C:/LAStools/bin/lastile.exe','-i',file,'-o{0}'.format(filetype),'-odir',tilepath,'-tile_size',tilesize] 
        subprocessargs=map(str,subprocessargs)    
        subprocess.call(subprocessargs)    
        files=AtlassGen.FILELIST(os.path.join(tilepath,'*.{0}'.format(filetype)))
        print('Tile strip completed')
        result = {"file":filename, "state" :"Success", "output":"Tile Striped" }

    except:
        result = {"file":filename, "state" :"Fail", "output":"Tile Could not be striped" }

    return result
    
def MergeTiles(file,files,filetype):    

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+files+['-o{0}'.format(filetype),'-o',file,'-merged'] 
        subprocessargs=map(str,subprocessargs)    
        subprocess.call(subprocessargs) 
        if os.path.isfile(file):
            for infile in files:
                os.remove(infile)

        result = {"file":file, "state" :"Success", "output":"Tiles Merged" }

    except:
        result = {"file":file, "state" :"Fail", "output":"Tiles could not be merged" }


    return(result)
   
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    
    args = param_parser()

    tilesize=int(args.tile_size)
    filetype=args.file_type
    inputfolder=args.input_folder
    
    files = []
    files = glob.glob(inputfolder+"\\*."+filetype)
    cores=int(args.cores)
    outlasdir=args.output_dir
    outputfile = os.path.join(outlasdir, args.output_file)
    logger = Atlasslogger(outlasdir)

    '''
    al = AtlassTileLayout()
    data = al.fromjson("D:\\Python\\Gui\\output\\test.json")
    print(data)
    '''

    TILETASK=[]
    for file in files:
        TILETASK.append((TileStrip,(file,outlasdir,tilesize,filetype)))
        
    results=AtlassTaskRunner(cores,TILETASK,'Tiling', logger, str(args)).results
    resultsdic=defaultdict(list)
    print(results)

    #merge tiles with the same tile name
    MERGETASK=[]
    for result in results:
        for key, value in result.items():
            if key =='Tile':
                print(value)
                filepath,filename,extn=AtlassGen.FILESPEC(file)
                resultsdic[value].append(file)
    for key in list(resultsdic.keys()): 
        print(key)
        outfile=os.path.join(outlasdir,'{0}.{1}'.format(key,filetype)).replace('\\','/')
        MERGETASK.append((MergeTiles,(outfile,resultsdic[key],filetype)))  
    
    results=AtlassTaskRunner(cores,MERGETASK,'Merging', logger, str(args)).results
    
    tilelayout = AtlassTileLayout()

    print("Making initial geojson file from dictionary \n")
    #make a tile layout index
    for file in results:
        for key, value in result.items():
            if key =='file':
                print(value)
                x,y=value.split('_')
            tilelayout.addtile(name=value, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize, task1='done', task1_val='val')
        '''
        #Format for dictionary input
        tiles[filename] = {'name':filename,'xmin':float(x), 'ymin':float(y), 'xmax':float(x)+tilesize,'ymax':float(y)+tilesize, 'key1':'shsfhsfh', 'key2':'dfhdhd'}

        tilelayout.fromdict(tiles)
        '''

    
    outputfile = tilelayout.createGeojsonFile(outputfile)
    print("Creating geojson file : Completed\n")
    print("output file : {}/{}".format(os.path.dirname(os.path.realpath(__file__)), outputfile))
    
    #Take a tile layout and add new params

    tl2 = AtlassTileLayout()
    tl2.fromjson(outputfile)
    for tile in tl2:
        tile.addparams(task2= "done", task2_val= "yahooo" )
        print('getting neighbours')
        neighbours = tile.getneighbours(50)
        print(len(neighbours))


    outputfile = tl2.createGeojsonFile(outputfile)
    print("Reading from geojson file : Completed\n")
    print("output file : {}".format(outputfile))

    return

if __name__ == "__main__":
    main(sys.argv[1:])         

