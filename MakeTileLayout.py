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
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]))
import shapefile
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]))
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

@Gooey(program_name="Make TileLayout", use_legacy_titles=True, required_cols=1, default_size=(800,600))
def param_parser():
    parser=GooeyParser(description="Make Tile Layout")
    parser.add_argument("input_folder", metavar="Input Folder", widget="DirChooser", help="Select folder with las/laz files")
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 20',
                'message': 'Must be between 2 and 20'
            }})
    parser.add_argument("jsonfile", metavar="Output File Name", help="Provide name for outputfile (.json)", default="TileLayout.json")
    parser.add_argument("prjfile", metavar="Output Prj file name",help="Provide name for prj file (.prj)", default="tile_layout.prj")
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    product_group = parser.add_argument_group("Other outputs", "Select Other outputs", gooey_options={'show_border': True,'columns': 5})
    product_group.add_argument("-shp", "--makeshp", metavar="shp", action='store_true', default=False)
    product_group.add_argument("-prj", "--makeprj", metavar="prj", action='store_true', default=False)
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
    jsonfile = os.path.join(outlasdir, args.jsonfile).replace("\\", "/")
    prjfile = os.path.join(outlasdir, args.prjfile).replace("\\", "/")
    logger = Atlasslogger(outlasdir)
    makeshp = args.makeshp
    makeprj = args.makeprj

    print("Total number of las files found : {0}\n".format(len(files)))
    tilelayout = AtlassTileLayout()
    
    prjfilespec=AtlassGen.FILESPEC(prjfile)
    if not os.path.exists(prjfilespec[0]):
        os.makedirs(prjfilespec[0])
    
    w = shapefile.Writer(shapefile.POLYGON)
    w.autoBalance = 1
    w.field('TILE_NAME','C','255')
    w.field('XMIN','N',12,3)
    w.field('YMIN','N',12,3)
    w.field('XMAX','N',12,3)
    w.field('YMAX','N',12,3)
    w.field('TILENUM','C','8')


    print("Making geojson file : Started \n")
    #make a tile layout index
    for file in files:
        filepath,filename,extn=AtlassGen.FILESPEC(file)
        x,y=filename.split('_')
        tilelayout.addtile(name=filename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)
         
    jsonfile = tilelayout.createGeojsonFile(jsonfile)

    print("Making geojson file : Completed\n")


    if makeprj:
        print("Making prj file : Started\n")
        with open(prjfile,"w") as f:

            
            #write the header to the file.
            filespec=AtlassGen.FILESPEC(files[0])
            f.write('[TerraScan project]\n')
            f.write('Scanner=Airborne\n')
            f.write('Storage={0}1.2\n'.format(filespec[2]))
            f.write('StoreTime=2\n')
            f.write('StoreColor=0\n')
            f.write('RequireLock=0\n')
            f.write('Description=Created using Compass\n')
            f.write('FirstPointId=1\n')
            f.write('Directory={0}\n'.format(inputfolder))
            f.write('PointClasses=\n')
            f.write('Trajectories=\n')
            f.write('BlockSize={0}\n'.format(str(tilesize)))
            f.write('BlockNaming=0\n')
            f.write('BlockPrefix=\n')   
            
            
            #make a prj fille

            for file in files:
                filepath,filename,extn=AtlassGen.FILESPEC(file)
                x,y=filename.split('_')
                boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
                f.write( '\nBlock {0}.{1}\n'.format(filename,extn))
                for i in boxcoords:
                    f.write(  ' {0} {1}\n'.format(i[0],i[1]))

            f.close
            print("Making prj file : Completed\n")
        
    if makeshp:
        print("Making shp file : Started\n")
        filespec=AtlassGen.FILESPEC(files[0])
        for file in files:
            filepath,filename,extn=AtlassGen.FILESPEC(file)
            x,y=filename.split('_')
            boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
            w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
            w.record(TILE_NAME='{0}'.format(filespec[1]), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='t{0}{1}'.format(int(boxcoords[0][0]/1000),int(boxcoords[0][1]/1000)))
        
        w.save(prjfile.replace('.prj','_shapefile'))           
        print("Making shp file : Completed\n")
  
    return

if __name__ == "__main__":
    main()         


