#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess 
from subprocess import PIPE, Popen
import os, glob
import numpy as np
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeMKPLib import *
from gooey import Gooey, GooeyParser

#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 25/10/2018
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make MKP", use_legacy_titles=True, required_cols=2,optional_cols=2, default_size=(1000,700))
def param_parser():
    parser=GooeyParser(description="Make MKP - thins ground points to vertical accuracy and maximum horizontal distance.")
    parser.add_argument("inputfolder", metavar="Las files Folder", widget="DirChooser", help="Select input files (.las/.laz)")
    parser.add_argument("inlayoutfile", metavar="Input TileLayout file", widget="FileChooser", help="TileLayout file(.json)")
    parser.add_argument("outlayoutfile", metavar="Output TileLayout file", widget="FileChooser", help="TileLayout file(.json)")
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory")
    parser.add_argument("workingdir", metavar="Working Directory",widget="DirChooser", help="Working directory")
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", default='laz')
    parser.add_argument("hz", metavar="hz", help="Provide maximum horizontal distance", default=30, type=int)
    parser.add_argument("vt", metavar="vt", help="Provide vertical accuracy requirement", default=0.15, type=float) 
    parser.add_argument("buffer", metavar="Buffer", help="Provide buffer", default=200, type=int)
    parser.add_argument("--clipshape", metavar="Clip shape", help="Clip Shape", action='store_true')
    parser.add_argument("--poly", metavar="AOI folder", widget="DirChooser", help="Folder with Polygons(Script will take all .shp files)", default='')
    parser.add_argument("--makeascii", metavar="Create ASCII files",help=".txt files", action='store_true')
    parser.add_argument("--cores", metavar="Cores", help="Number of Cores", default=8, type=int)
   
    return parser.parse_args()

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
##python C:\AtlassTools\MakeMKPLib.py #tilename# D:\Processing_Data\inputfolder D:\Processing_Data\outputfolder D:\Processing_Data\workingfolder 2;8 0.15 30 200 D:\Processing_Data\inputfolder\TileLayout.json laz True D:\Processing_Data\aoi\Area_MR1_mga56.shp;D:\Processing_Data\aoi\Area_MR2_mga56.shp

#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support()
    args = param_parser()

    inputfolder=args.inputfolder
    filetype = args.filetype
    outtilelayoutfile=args.outlayoutfile
    intilelayoutfile=args.inlayoutfile
    outputpath=args.outputpath
    workingpath = args.workingdir
    buffer=args.buffer
    hz=args.hz
    vt=args.vt
    gndclasses='2 8'
    cores = int(args.cores)
    aoifolder = args.poly
    poly = AtlassGen.FILELIST(['*.shp'],aoifolder)
    print('\nNumber of AOIS found: {1}\n\n AOIS : {0}'.format(poly, len(poly)))
    clipshape = args.clipshape
    makeASCII = args.makeascii

    outpath=args.outputpath
    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')
    log = open(logpath, 'w')

    lasfiles = glob.glob(inputfolder + "/*.{0}".format(filetype))
    
    print('####################################################\n\nNumber of Files found : {0} '.format(len(lasfiles)))

    outtilelayoutfile=outtilelayoutfile.replace('\\','/')
    intilelayoutfile=intilelayoutfile.replace('\\','/')
    #path,name,ext=AtlassGen.FILESPEC(lasfile)

    gndclasses=gndclasses.split()    
    outtilelayout = AtlassTileLayout()
    outtilelayout.fromjson(outtilelayoutfile)

    intilelayout = AtlassTileLayout()
    intilelayout.fromjson(intilelayoutfile)         

    dt = strftime("%y%m%d_%H%M")
    vtcm =int(float(vt)*100)
 
    outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_makeMKP_hz_{1}_vt_{2}cm'.format(dt,hz,vtcm))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, '{0}_makeMKP_Working_hz_{1}_vt_{2}cm'.format(dt,hz,vtcm))).replace('\\','/')
    make_mkp_tasks = {}


 
    print("No of Tiles in the Input Tilelayout : {0}".format(len(intilelayout)))
    print("No of Tiles in the Output Tilelayout : {0}\n\n#####################################################".format(len(outtilelayout)))
    
    for tile in outtilelayout: 

        tilename = tile.name
        make_mkp_tasks[tilename] = AtlassTask(tilename, MKPClass.makeMKP, tilename, inputfolder, outputpath,workingdir, gndclasses,vt, hz, buffer, intilelayoutfile,filetype,clipshape,poly,makeASCII)


    p=Pool(processes=cores)    
    make_mkp_results=p.map(AtlassTaskRunner.taskmanager,make_mkp_tasks.values())


    return
        
if __name__ == "__main__":
    main(sys.argv[1:])            
