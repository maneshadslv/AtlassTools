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
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile
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

@Gooey(program_name="Make TileLayout", use_legacy_titles=True, required_cols=1, optional_cols=3, default_size=(1000,810))
def param_parser():
    parser=GooeyParser(description="Make Tile Layout")
    parser.add_argument("input_folder", metavar="Input Folder", widget="DirChooser", help="Select folder with las/laz files")
    parser.add_argument("filepattern",metavar="Input filter Pattern", help="Provide a file pattern seperated by ';' for multiple patterns\n(*.laz or 123*_456*.laz;345*_789* )", default='*.laz')
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 20',
                'message': 'Must be between 2 and 20'
            }})
    parser.add_argument("jsonfile", metavar="Output File Name", help="Provide name for outputfile (.json)", default="TileLayout.json")
    parser.add_argument("prjfile", metavar="Output Prj file name",help="Provide name for prj file (.prj)", default="tile_layout.prj")
    name_group = parser.add_argument_group("File name settings", "Required when files have different naming conventions", gooey_options={'show_border': True,'columns': 3})
    name_group.add_argument("-hfn", "--hasfilename", metavar="Has filename pattern", action='store_true', default=False)
    name_group.add_argument("-addzero", metavar="Zeros to add", help="Number of zeros to add at the end of X and Y\n1 = None, 100 = 2 zeros , etc..", type=int)
    name_group.add_argument("--namepattern", metavar="Input File Name Convention", help="Ex: MGA55_dem_Mo%X%_%Y%_1.laz\n ")
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
    inputfolder=args.input_folder
    filetype = args.filetype
      
    filepattern = args.filepattern.split(';')

    files = AtlassGen.FILELIST(filepattern, inputfolder)

    cores=int(args.cores)
    outlasdir=args.output_dir
    jsonfile = os.path.join(outlasdir, args.jsonfile).replace("\\", "/")
    prjfile = os.path.join(outlasdir, args.prjfile).replace("\\", "/")

    makeshp = args.makeshp
    makeprj = args.makeprj

    print("Total number of las files found : {0}\n".format(len(files)))
    tilelayout = AtlassTileLayout()

    if args.hasfilename:
        namepattern = args.namepattern
        searchpattern=namepattern.replace("%X%","*")
        searchpattern=searchpattern.replace("%Y%","*")
        print(searchpattern)
        patternsplit=searchpattern.split("*")
    
        print(patternsplit)
        addzero = args.addzero
    
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
    w.field('TILENUM','C','16')


    print("Making geojson file : Started \n")
    #make a tile layout index
    for file in files:
        if not args.hasfilename:
            path, tilename, ext = AtlassGen.FILESPEC(file)
            x,y = tilename.split('_')
        
        else:
            filespec=AtlassGen.FILESPEC(file)
            X_Y ='{0}.{1}'.format(filespec[1],filespec[2])
            for rep in patternsplit:
                if rep!='':
                    #print(rep)
                    X_Y = X_Y.replace(rep,"_")
            #print(X_Y)
            X_Y = X_Y.replace("_"," ")
            X_Y = X_Y.strip()
            coords=X_Y.split()

            if namepattern.find("%X%")>namepattern.find("%Y%"):
                coords.reverse()
            x=int(float(coords[0])*addzero)
            y=int(float(coords[1])*addzero)
            tilename = '{0}_{1}'.format(x,y)

        tilelayout.addtile(name=tilename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)
         
    jsonfile = tilelayout.createGeojsonFile(jsonfile)

    print("Making geojson file : Completed\n File : {0}\n".format(jsonfile))

    if makeprj:
        print("Making prj file : Started\n")
        with open(prjfile,"w") as f:

            
            #write the header to the file.
            f.write('[TerraScan project]\n')
            f.write('Scanner=Airborne\n')
            f.write('Storage={0}1.2\n'.format(filetype))
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
                if not args.hasfilename:
                    path, tilename, ext = AtlassGen.FILESPEC(file)
                    x,y = tilename.split('_')
        
                else:
                    path, filename, ext=AtlassGen.FILESPEC(file)
                    X_Y ='{0}.{1}'.format(filename, ext)
                    for rep in patternsplit:
                        if rep!='':
                            #print(rep)
                            X_Y = X_Y.replace(rep,"_")
                    #print(X_Y)
                    X_Y = X_Y.replace("_"," ")
                    X_Y = X_Y.strip()
                    coords=X_Y.split()

                    if namepattern.find("%X%")>namepattern.find("%Y%"):
                        coords.reverse()
                    x=int(float(coords[0])*addzero)
                    y=int(float(coords[1])*addzero)
                    tilename = '{0}_{1}'.format(x,y)

                boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
                f.write( '\nBlock {0}.{1}\n'.format(tilename,ext))
                for i in boxcoords:
                    f.write(  ' {0} {1}\n'.format(i[0],i[1]))

            f.close
            print("Making prj file : Completed\n")
        
    if makeshp:
        print("Making shp file : Started\n")

        for file in files:

            if not args.hasfilename:
                path, tilename, ext = AtlassGen.FILESPEC(file)
                x,y = tilename.split('_')
    
            else:
                path, filename, ext=AtlassGen.FILESPEC(file)
                X_Y ='{0}.{1}'.format(filename, ext)
                for rep in patternsplit:
                    if rep!='':
                        #print(rep)
                        X_Y = X_Y.replace(rep,"_")
                #print(X_Y)
                X_Y = X_Y.replace("_"," ")
                X_Y = X_Y.strip()
                coords=X_Y.split()

                if namepattern.find("%X%")>namepattern.find("%Y%"):
                    coords.reverse()
                x=int(float(coords[0])*addzero)
                y=int(float(coords[1])*addzero)
                tilename = '{0}_{1}'.format(x,y)

            boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
            w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
            w.record(TILE_NAME='{0}'.format(tilename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='t{0}{1}'.format(int(boxcoords[0][0]/1000),int(boxcoords[0][1]/1000)))
            
        w.save(prjfile.replace('.prj','_shapefile'))           
        print("Making shp file : Completed\n")
  
    return

if __name__ == "__main__":
    main()         


