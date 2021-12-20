#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import shutil
import subprocess
import os
import random
import argparse
import math
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
import glob
from collections import defaultdict 
from collections import OrderedDict 
from gooey import Gooey, GooeyParser
from geojson import Point, Feature, FeatureCollection, Polygon,dump
sys.path.append('{0}/lib/shapefile_original/'.format(sys.path[0]).replace('\\','/'))
import shapefile_original 
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

@Gooey(program_name="Make TileLayout", use_legacy_titles=True, required_cols=2, optional_cols=3, advance=True, navigation='TABBED', default_size=(1000,810))
def param_parser():
    parser=GooeyParser(description="Make Tile Layout")
    subs = parser.add_subparsers(help='commands', dest='command')
    main_parser = subs.add_parser('main', help='Create Tile layout using files')
    main_parser.add_argument("input_folder", metavar="Input Folder", widget="DirChooser", help="Select folder with las/laz files")
    main_parser.add_argument("filepattern",metavar="Input filter Pattern", help="Provide a file pattern seperated by ';' for multiple patterns\n(*.laz or 123*_456*.laz;345*_789* )", default='*.laz')
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz','zip','rar','txt','asc'], default='laz')
    main_parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", default=500, type=int)
    main_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    main_parser.add_argument("--cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)
    main_parser.add_argument("--jsonfile", metavar="Output File Name", help="Provide name for outputfile (.json)", default="TileLayout")
    main_parser.add_argument("--prjfile", metavar="Output Prj file name",help="Provide name for prj file (.prj)", default="tile_layout.prj")
    attr_group = main_parser.add_argument_group("Attribute settings", "Required for spec jobs", gooey_options={'show_border': True,'columns': 3})
    attr_group.add_argument("-dt", metavar="Date", widget="DateChooser")
    attr_group.add_argument("-brnumber", metavar="BR Number")
    attr_group.add_argument("-projection", metavar="Projection", help="GDAXXXX_MGAXX")
    attr_group.add_argument("-vertD", metavar="Vertical Datum", choices=['AHD', 'ELL','AWS'])
    attr_group.add_argument("-rgb", metavar="RGB", choices=['Yes', 'No'])
    attr_group.add_argument("-cls", metavar="Classification", choices=['C1', 'C2','C3'])
    attr_group.add_argument("-xadj", metavar="X adjustment", type=float)
    attr_group.add_argument("-yadj", metavar="Y adjustment", type=float)
    attr_group.add_argument("-zadj", metavar="Z adjustment", type=float)
    attr_group.add_argument("-spath", metavar="Storage Location")
    name_group = main_parser.add_argument_group("File name settings", "Required when files have different naming conventions", gooey_options={'show_border': True,'columns': 3})
    name_group.add_argument("-hfn", "--hasfilename", metavar="Has filename pattern", action='store_true', default=False)
    name_group.add_argument("-addzero", metavar="Zeros to add", help="Multiplication to be used at the end of X and Y\n1 = None, 100, 1000 etc..", type=int)
    name_group.add_argument("--namepattern", metavar="Input File Name Convention", help="Ex: MGA55_dem_Mo%X%_%Y%_1.laz\n ")

    product_group = main_parser.add_argument_group("Other outputs", "Select Other outputs", gooey_options={'show_border': True,'columns': 5})
    product_group.add_argument("-shp", "--makeshp", metavar="shp", action='store_true', default=False)
    product_group.add_argument("-prj", "--makeprj", metavar="prj", action='store_true', default=False)
    boundingbox_parser = subs.add_parser('boundingbox', help='Create a Tile layout using a box boundingbox ')
    boundingbox_parser.add_argument('xmin',type=int)
    boundingbox_parser.add_argument('ymin',type = int)
    boundingbox_parser.add_argument('xmax',type = int)
    boundingbox_parser.add_argument('ymax',type = int)
    boundingbox_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    boundingbox_parser.add_argument("--tilesize", metavar="Tile size", help="Select Size of Tile in meters [size x size]", default=1000, type=int)
    boundingbox_parser.add_argument("--jsonfile", metavar="Output File Name", help="Provide name for outputfile (.json)", default="TileLayout")
    boundingbox_parser.add_argument("--shpfile", metavar="Output shape file name",help="Provide name for shape file (.shp)", default="tile_layout_shapefile.shp")  
    output_group = main_parser.add_argument_group("Output tilename settings", "Required when client requires different tilename on tilelayout file", gooey_options={'show_border': True,'columns': 3})
    output_group.add_argument("-ohtn", "--ohastilename", metavar="Has filename pattern", action='store_true', default=False)
    output_group.add_argument("--tilename", metavar="Output tilename File Name Convention", help="MR12345_SW_%X%_%Y%_1k\n ")
    lastedit_parser = subs.add_parser('lastedit', help='Create a Tile layout with last Edited tiles ')
    lastedit_parser.add_argument('inputdir',metavar="Input Folder", widget="DirChooser", help="Select folder with las/laz files")
    lastedit_parser.add_argument("outputdir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    lastedit_parser.add_argument('datefilter',metavar="Date Filter",widget="DateChooser", help="Filter files with modified date after", default="")
    lastedit_parser.add_argument("timefilter", metavar="Time Filter", help="Time filter (HH:MM:SS)", default="00:00:00")
    lastedit_parser.add_argument("tilesize", metavar="Tile size", help="Select Size of Tile in meters [size x size]", default=500, type=int)   
    lastedit_parser.add_argument('filetype',metavar="Input File Type", help="Select input file type", choices=['las', 'laz','zip','rar','txt'], default='laz')
    lastedit_parser.add_argument("--cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)
    lastedit_parser.add_argument("--jsonfile", metavar="Output File Name", help="Provide name for outputfile (.json)", default="TileLayout")

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

    if args.command=='main':
        tilesize=int(args.tile_size)
        inputfolder=args.input_folder
        filetype = args.filetype
        
        filepattern = args.filepattern.split(';')

        files = AtlassGen.FILELIST(filepattern, inputfolder)

        cores=int(args.cores)
        outlasdir=args.output_dir

        prjfile = os.path.join(outlasdir, args.prjfile).replace("\\", "/")

        makeshp = args.makeshp
        makeprj = args.makeprj
        tilenameconv = args.tilename

        #attribute_Values
        dt = args.dt
        brnumber = args.brnumber
        projection = args.projection
        vertd = args.vertD
        rgb = args.rgb
        cl = args.cls 
        xadj = args.xadj
        yadj = args.yadj
        zadj = args.zadj
        storage_path = args.spath

        print("Total number of las files found : {0}\n".format(len(files)))
        tilelayout = AtlassTileLayout()

        if args.hasfilename:
            namepattern = args.namepattern
            searchpattern=namepattern.replace("%X%","*")
            searchpattern=searchpattern.replace("%Y%","*")
            searchpattern=searchpattern.replace("%BLAH%","*")
            print(searchpattern)
            patternsplit=searchpattern.split("*")
        
            print(patternsplit)
            addzero = args.addzero


        prjfilespec=AtlassGen.FILESPEC(prjfile)
        if not os.path.exists(prjfilespec[0]):
            os.makedirs(prjfilespec[0])
        
        w = shapefile_original.Writer(shapefile_original.POLYGON)
        w.autoBalance = 1
        w.field('TILE_NAME','C','255')
        w.field('XMIN','N',12,3)
        w.field('YMIN','N',12,3)
        w.field('XMAX','N',12,3)
        w.field('YMAX','N',12,3)
        w.field('TILENUM','C','16')

        features = []
        print("Making geojson file : Started \n")
        #make a tile layout index
        for file in files:
            if not args.hasfilename:
                path, tilename, ext = AtlassGen.FILESPEC(file)
                print(tilename)
                x,y = tilename.split('_')
                if not args.ohastilename:
                    tilename = '{0}_{1}'.format(x,y)
                else:
                    tilename = tilenameconv.replace('%X%',x)
                    tilename = tilename.replace('%Y%',y)

    
            else:
                filespec=AtlassGen.FILESPEC(file)
                X_Y ='{0}'.format(filespec[1])
                for rep in patternsplit:
                    if rep!='':
                        #print(rep)
                        X_Y = X_Y.replace(rep,"_")

                X_Y = X_Y.replace("_"," ")
                X_Y = X_Y.strip()
 
                coords=X_Y.split()
                #print(coords)
                if len(coords) == 1:
                    x=int(coords[0][0:3])*addzero
                    y=int(coords[0][3:8])*addzero
                    if not args.ohastilename:
                        tilename = '{0}_{1}'.format(x,y)
                    else:
                            tilename = tilenameconv.replace('%X%',x)
                            tilename = tilename.replace('%Y%',y)
                
                else:
                    if namepattern.find("%X%")>namepattern.find("%Y%"):
                        coords.reverse()
                    x=int(float(coords[0]))
                    y=int(float(coords[1]))
                    if not args.ohastilename:
                        tilename = '{0}_{1}'.format(x,y)
                    else:
                            tilename = tilenameconv.replace('%X%',str(x))
                            tilename = tilename.replace('%Y%',str(y))


            mtime = os.path.getmtime(file)
            modificationTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(mtime))

            #print(x,y)
            #print(tilesize)
            boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
            poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
            xmax = str(int(x)+tilesize)
            ymax = str(int(y)+tilesize)
            #adding records for json file
            features.append(Feature(geometry=poly, properties={"name": tilename, "xmin": x, "ymin":y, "xmax":xmax, "ymax":ymax, "tilenum":tilename,"modifiedTime":modificationTime,"Date":dt,"BR_Number":brnumber,"Projection":projection,"Vertical_Datum":vertd,"RGB":rgb,"Classification":cl,"X_adj":xadj,"Y_adj":yadj,"Z_adj":zadj,"Storage_Location":storage_path}))
            tilelayout.addtile(name=tilename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize, modtime=modificationTime, Date=dt,BR_Number=brnumber, Projection=projection, Vertical_Datum=vertd, RGB=rgb, Classification=cl, X_adj=xadj, Y_adj=yadj, Z_adj=zadj, Storage_Location=storage_path)
            
        #Creating Json file
        print('No of tiles in tilelayout : {0}'.format(len(features)))

        jsonfile = os.path.join(outlasdir,'{0}_{1}.json'.format(args.jsonfile,len(features)))

        if os.path.isfile(jsonfile):
            mtime = os.path.getmtime(jsonfile)
            modificationTime = time.strftime('%Y%m%d_%H%M%S',time.localtime(mtime))

            path,jname,ext = AtlassGen.FILESPEC(jsonfile)
            oldjsonfile = os.path.join(outlasdir, '{0}_{1}.{2}'.format(jname,modificationTime,ext)).replace("\\", "/")
            print('********* File {0} EXISTS, renaming this to {1} *************\n\n'.format(jsonfile,oldjsonfile))
            os.rename(jsonfile,oldjsonfile)


        feature_collection = FeatureCollection(features)

        with open(jsonfile, 'w') as f:
            dump(feature_collection, f)

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
                        if not args.ohastilename:
                            tilename = '{0}_{1}'.format(x,y)
                        else:
                            tilename = tilenameconv.replace('%X%',str(x))
                            tilename = tilename.replace('%Y%',str(y))
                            print(tilename)
            
                    else:
                        filespec=AtlassGen.FILESPEC(file)
                        X_Y ='{0}'.format(filespec[1])
                        ext = filespec[0]
                        for rep in patternsplit:
                            if rep!='':
                                #print(rep)
                                X_Y = X_Y.replace(rep,"_")

                        X_Y = X_Y.replace("_"," ")
                        X_Y = X_Y.strip()
                        coords=X_Y.split()

                        if len(coords) == 1:
                            x=int(coords[0][0:3])*addzero
                            y=int(coords[0][3:8])*addzero
                            if not args.ohastilename:
                                tilename = '{0}_{1}'.format(x,y)
                            else:
                                    tilename = tilenameconv.replace('%X%',str(x))
                                    tilename = tilename.replace('%Y%',str(y))
                        
                        else:
                            if namepattern.find("%X%")>namepattern.find("%Y%"):
                                coords.reverse()
                            x=int(float(coords[0]))
                            y=int(float(coords[1]))
                            if not args.ohastilename:
                                tilename = '{0}_{1}'.format(x,y)
                            else:
                                    tilename = tilenameconv.replace('%X%',str(x))
                                    tilename = tilename.replace('%Y%',str(y))


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
                    if not args.ohastilename:
                        tilename = '{0}_{1}'.format(x,y)
                    else:
                        tilename = tilenameconv.replace('%X%',x)
                        tilename = tilename.replace('%Y%',y)

        
                else:
                    filespec=AtlassGen.FILESPEC(file)
                    X_Y ='{0}'.format(filespec[1])
                    for rep in patternsplit:
                        if rep!='':
                            #print(rep)
                            X_Y = X_Y.replace(rep,"_")

                    X_Y = X_Y.replace("_"," ")
                    X_Y = X_Y.strip()
                    coords=X_Y.split()

                    if len(coords) == 1:
                        x=int(coords[0][0:3])*addzero
                        y=int(coords[0][3:8])*addzero
                        if not args.ohastilename:
                            tilename = '{0}_{1}'.format(x,y)
                        else:
                                tilename = tilenameconv.replace('%X%',x)
                                tilename = tilename.replace('%Y%',y)
                    
                    else:
                        if namepattern.find("%X%")>namepattern.find("%Y%"):
                            coords.reverse()
                        x=int(float(coords[0]))
                        y=int(float(coords[1]))
                        if not args.ohastilename:
                            tilename = '{0}_{1}'.format(x,y)
                        else:
                                tilename = tilenameconv.replace('%X%',str(x))
                                tilename = tilename.replace('%Y%',str(y))


                boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
                #print(boxcoords[0][0],boxcoords[0][1])
                w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                w.record(TILE_NAME='{0}'.format(tilename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='{0}_{1}'.format(int(boxcoords[0][0]),int(boxcoords[0][1])))
                
            w.save(prjfile.replace('.prj','_shapefile'))           
            print("Making shp file : Completed\n")
    elif args.command=='boundingbox':

        boundingbox_xmin = args.xmin
        boundingbox_ymin = args.ymin
        boundingbox_xmax = args.xmax
        boundingbox_ymax = args.ymax
        tilesize = int(args.tilesize)
        outdir=args.output_dir
        shpfile = os.path.join(outdir, args.shpfile).replace("\\", "/")
        makeshp = True

        print('Making tilelayout for area;\n xmin = {0}\n ymin = {1}\n xmax = {2}\n ymax = {3}'.format(boundingbox_xmin,boundingbox_ymin,boundingbox_xmax,boundingbox_ymax))
     
        w = shapefile_original.Writer(shapefile_original.POLYGON)
        w.autoBalance = 1
        w.field('TILE_NAME','C','255')
        w.field('XMIN','N',12,3)
        w.field('YMIN','N',12,3)
        w.field('XMAX','N',12,3)
        w.field('YMAX','N',12,3)
        w.field('TILENUM','C','16')

        features = []

        #make a tile layout index
        for x in range(boundingbox_xmin-int(tilesize),boundingbox_xmax+int(tilesize),int(tilesize)):
            x=math.ceil(x/tilesize)*tilesize
            for y in range(boundingbox_ymin-int(tilesize),boundingbox_ymax+int(tilesize),int(tilesize)):
                y=math.ceil(y/tilesize)*tilesize
                boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
                poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                tilename = '{0}_{1}'.format(x,y)
                xmax=x+int(tilesize)
                ymax=y+int(tilesize)

                #adding records for json file
                features.append(Feature(geometry=poly, properties={"name": tilename, "xmin": x, "ymin":y, "xmax":xmax, "ymax":ymax, "tilenum":tilename,"modtime":"0000-00-00 00:00:00"}))

                #adding records for shp file
                w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                w.record(TILE_NAME='{0}'.format(tilename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='{0}_{1}'.format(int(boxcoords[0][0]),int(boxcoords[0][1])))
                
    
        #Creating Json file
        print('No of tiles in tilelayout : {0}'.format(len(features)))

        print("Making geojson file : Started \n")

        feature_collection = FeatureCollection(features)

        jsonfile = os.path.join(outdir,'{0}_{1}.json'.format(args.jsonfile,len(features)))

        if os.path.isfile(jsonfile):
            mtime = os.path.getmtime(jsonfile)
            modificationTime = time.strftime('%Y%m%d_%H%M%S',time.localtime(mtime))

            path,jname,ext = AtlassGen.FILESPEC(jsonfile)
            oldjsonfile = os.path.join(outdir, '{0}_{1}.{2}'.format(jname,modificationTime,ext)).replace("\\", "/")
            print('********* File {0} EXISTS, renaming this to {1} *************\n\n'.format(jsonfile,oldjsonfile))
            os.rename(jsonfile,oldjsonfile)

        with open(jsonfile, 'w') as f:
            dump(feature_collection, f)

        print("Making geojson file : Completed\n File : {0}\n".format(jsonfile))


        #Creating shp file
        print("Making shp file : Started\n")
        w.save(shpfile)           
        print("Making shp file : Completed\n File : {0}\n".format(shpfile))


    elif args.command=='lastedit':
        datefilter = args.datefilter
        timefilter = args.timefilter
        inputfolder = args.inputdir
        tilesize = args.tilesize
        outputfolder = args.outputdir
        filetype = args.filetype
        jsonfile = os.path.join(outputfolder,args.jsonfile)
        print('Filter files with modified date after : {0}'.format(datefilter))


        filepattern = ['*.{0}'.format(filetype)]
        files = AtlassGen.FILELIST(filepattern, inputfolder)
    
        max_mtime = '{0} {1}'.format(datefilter, timefilter)
        pattern = '%Y-%m-%d %H:%M:%S'
        epoch = float(time.mktime(time.strptime(max_mtime, pattern)))
        nfile = 0

        features = []
        for file in files:
            mtime = os.path.getmtime(file)

            if mtime > epoch:
                nfile += 1
                modificationTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(mtime))
                print('File {0} modified date : {1}'.format(file,modificationTime))
                path, tilename, ext = AtlassGen.FILESPEC(file)
                x,y = tilename.split('_')

                tilename = '{0}_{1}'.format(x,y)
                mtime = os.path.getmtime(file)
                modificationTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(mtime))

                boxcoords=AtlassGen.GETCOORDS([x,y],tilesize)
                poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                xmax = str(int(x)+tilesize)
                ymax = str(int(y)+tilesize)
                #adding records for json file
                features.append(Feature(geometry=poly, properties={"name": tilename, "xmin": x, "ymin":y, "xmax":xmax, "ymax":ymax, "tilenum":tilename,"modifiedTime":modificationTime}))
               


        print("No of files edited after {0}  :   {1}".format( max_mtime,nfile))
        #Creating Json file
        print('No of tiles in tilelayout : {0}'.format(len(features)))

        jsonfile = os.path.join(outputfolder,'{0}_{1}.json'.format(args.jsonfile,len(features)))

        if os.path.isfile(jsonfile):
            mtime = os.path.getmtime(jsonfile)
            modificationTime = time.strftime('%Y%m%d_%H%M%S',time.localtime(mtime))

            path,jname,ext = AtlassGen.FILESPEC(jsonfile)
            oldjsonfile = os.path.join(outputfolder, '{0}_{1}.{2}'.format(jname,modificationTime,ext)).replace("\\", "/")
            print('********* File {0} EXISTS, renaming this to {1} *************\n\n'.format(jsonfile,oldjsonfile))
            os.rename(jsonfile,oldjsonfile)


        feature_collection = FeatureCollection(features)

        with open(jsonfile, 'w') as f:
            dump(feature_collection, f)

        print("Making geojson file : Completed\n File : {0}\n".format(jsonfile))
    return

if __name__ == "__main__":
    main()         


