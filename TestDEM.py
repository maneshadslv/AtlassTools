import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import json
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeDEMLib import *


@Gooey(program_name="Make DEM", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():

    stored_args = {}
    # get the script name without the extension & use it to build up
    # the json filename
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    congifg_folder = AtlassGen.makedir("C:\\pythontools")
    args_file = os.path.join(congifg_folder,"{}-args.json".format(script_name))
    # Read in the prior arguments as a dictionary
    if os.path.isfile(args_file):
        with open(args_file) as data_file:
            stored_args = json.load(data_file)

    main_parser=GooeyParser(description="Make DEM")
    main_parser.add_argument("inputpath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default=stored_args.get('inputpath'))
    main_parser.add_argument("filetype",metavar="Input File type", help="laz or las", default='laz')
    main_parser.add_argument("inputgeojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default=stored_args.get('inputgeojsonfile'))
    main_parser.add_argument("outputgeojsonfile", metavar="Output TileLayout file", widget="FileChooser", help="Select .json file", default=stored_args.get('outputgeojsonfile'))
    main_parser.add_argument("--outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default=stored_args.get('outputpath'))
    main_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default=stored_args.get('workpath'))    
    main_parser.add_argument("epsg", metavar="EPSG",default=stored_args.get('epsg'))
    main_parser.add_argument("--projectname", metavar="Project Name and Year", help="ProjectNameYYYY",default=stored_args.get('projectname'))
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("-chmc", "--chmclasses", metavar = "CHM Classes", default="3 4 5")
    main_parser.add_argument("-gc", "--gndclasses", metavar = "Ground Classes", default="2 8")
    main_parser.add_argument("-ngc", "--nongndclasses", metavar = "Non Ground Classes", default="1 3 4 5 6 10 13 14 15")
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    main_parser.add_argument("-k", "--kill",metavar="Kill", help="Maximum triagulation length", type=int, default=250)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    product_group = main_parser.add_argument_group("Products", "Select Output Products", gooey_options={'show_border': True,'columns': 5})
    product_group.add_argument("-dem", "--makeDEM", metavar="DEM", action='store_true', default=True)
    product_group.add_argument("-dsm", "--makeDSM", metavar="DSM", action='store_true')
    product_group.add_argument("-chm", "--makeCHM", metavar="CHM", action='store_true')
    
    args = main_parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args


def main():

    args = param_parser()
    step = float(args.step)
    kill = args.kill
    gndclasses = args.gndclasses
    nongndclasses = args.nongndclasses
    buffer = args.buffer
    epsg = args.epsg
    inputdir = args.inputpath
    workpath = args.workpath
    outputpath = args.outputpath
    inputgeojsonfile = args.inputgeojsonfile
    outputgeojsonfile = args.outputgeojsonfile
    hydropointsfiles=None
    if not args.hydropointsfiles==None:
        hydropointsfiles=args.hydropointsfiles
        hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')

    cores = args.cores
    dt = strftime("%y%m%d_%H%M")

    outputdir = AtlassGen.makedir(os.path.join(outputpath, '{0}_makeGrid'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workpath, '{0}_makeGrid_Working'.format(dt))).replace('\\','/')


    make_DEM = {}
    make_DEM_results = []
    make_DSM = {}
    make_DSM_results = []

    filetype = args.filetype 

    tl_out = AtlassTileLayout()
    tl_out.fromjson(outputgeojsonfile)
    
    for tile in tl_out: 

        tilename = tile.name
        outputfilename = tilename

        make_DEM[tilename] = AtlassTask(tilename,DEMClass.makeDEMperTile,tilename,inputdir,outputdir,workingdir,hydropointsfiles,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,gndclasses,buffer,kill,step)
        make_DSM[tilename] = AtlassTask(tilename,DSMClass.makeDSMperTile,tilename,inputdir,outputdir,workingdir,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,nongndclasses,buffer,kill,step)


    p=Pool(processes=cores)        
    make_DEM_results=p.map(AtlassTaskRunner.taskmanager,make_DEM.values())       
     
    make_DSM_results=p.map(AtlassTaskRunner.taskmanager,make_DSM.values())      

    return()
    
if __name__ == "__main__":
    main() 



