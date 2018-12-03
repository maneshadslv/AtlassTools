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
from Atlass import *
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

@Gooey(program_name="Make MKP", use_legacy_titles=True, required_cols=1, default_size=(1000,600))
def param_parser():
    parser=GooeyParser(description="Make MKP")
    parser.add_argument("inputfolder", metavar="Contour Points Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default='')
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    parser.add_argument("buffer", metavar="Buffer", help="Provide buffer", default=200, type=int)
    parser.add_argument("hz", metavar="hz", help="Provide hz", default=30, type=int)
    parser.add_argument("vt", metavar="vt", help="Provide vt", default=0.15, type=float) 
    parser.add_argument("cores", metavar="Cores", help="Number of Cores", default=4, type=int)   
    return parser.parse_args()

def makeMKP(tile, lasfiles, outpath, gndclasses,vt, hz, buffer):
    cleanup=[]
    outfile=os.path.join(outpath,'{0}.laz'.format(tile.name)).replace('\\','/')
    tempfile=os.path.join(outpath,'{0}_temp.laz'.format(tile.name)).replace('\\','/')
    tempfile2=os.path.join(outpath,'{0}_temp2.laz'.format(tile.name)).replace('\\','/')
    cleanup.append(tempfile)
    cleanup.append(tempfile2)
    
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+lasfiles+['-merged','-olaz','-o',tempfile,'-keep_class'] + gndclasses
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]
        subprocessargs=map(str,subprocessargs) 
        '''cmd =  " ".join(str(x) for x in subprocessargs)
        print(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE).wait()
        stdout, stderr = p.communicate()
        print(stderr)'''
        subprocess.call(subprocessargs)
    
        subprocessargs=['C:/LAStools/bin/lasthin.exe','-i',tempfile,'-olaz','-o',tempfile2,'-adaptive',vt,hz,'-set_classification',8]
        subprocessargs=subprocessargs
        subprocessargs=map(str,subprocessargs)    
        subprocess.call(subprocessargs)  

        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,'-olaz','-o',outfile]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin,tile.ymin,tile.xmax,tile.ymax]
        subprocessargs=map(str,subprocessargs)    
        subprocess.call(subprocessargs)  

        if os.path.isfile(outfile):
            result = {"file":tile.name, "state" :"Success", "output":outfile }
        else: 
            result = {"file":tile.name, "state" :"Error", "output":"Could not Make MKP for file : {0}".format(tile.name) }
    except:
        result = {"file":tile.name, "state" :"Error", "output":"Could not Make MKP : {0}".format(tile.name) }

    for file in cleanup:
        if os.path.isfile(file) and __keepfiles==None:
            os.remove(file)
            pass
    return result
    
def ShapeAttributes(shape,fields,NameField=None):
    Rec={}
    for i,field in enumerate(fields):
        if i>0:
            Rec[field[0]]=shape.record[i-1]
    XMIN=float(Rec['XMIN'])
    YMIN=float(Rec['YMIN'])
    XMAX=float(Rec['XMAX'])
    YMAX=float(Rec['YMAX'])
    if NameField==None:
        NameField='TILE_NAME'
    TILE=Rec[NameField].replace('/','_')

    return TILE,XMIN,YMIN,XMAX,YMAX



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#c:\python35-64\python.exe \\10.10.10.100\temp\Alex\Python\scripts\MakeMKP.py --lasfile=#file# --outpath=F:\Newlands\Z_adjusted\Wollombi\edited\tiles_1000m\mkp --hz=30 --vt=0.15 --tileshape="F:\Newlands\Z_adjusted\Wollombi\edited\tiles_1000m\tile_layout_shapefile.shp"

#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    args = param_parser()

    inputfolder=args.inputfolder
    filetype = args.filetype
    tilelayoutfile=args.layoutfile
    outpath=args.outputpath
    buffer=args.buffer
    hz=args.hz
    vt=args.vt
    gndclasses='2 8'
    cores = int(args.cores)

    #create variables from settings

    # __keepfiles=settings['__keepfiles']

    lasfiles = []
    lasfiles = glob.glob(args.inputfolder+"\\*."+args.filetype)

    
    tilelayoutfile=tilelayoutfile.replace('\\','/')
    #path,name,ext=AtlassGen.FILESPEC(lasfile)


    gndclasses=gndclasses.split()    
    al = Atlasslogger(outpath)
    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)
    MAKE_MKP_TASKS = []

    for file in lasfiles:
            file=file.replace('\\','/')
            path, filename, ext = AtlassGen.FILESPEC(file)
            tile = tilelayout.gettile(filename)
        
            neighbourfiles = []
            neighbours = tile.getneighbours(buffer)
            for neighbour in neighbours:
                neighbourfiles.append(os.path.join(path,'{0}.{1}'.format(neighbour,ext)).replace('\\','/'))
            
            al.PrintMsg('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of {2}'.format(len(neighbourfiles),buffer,file),'Neighbourhood:')
    
            al.PrintMsg('','Starting process')
            outpath=AtlassGen.makedir(outpath)
            MAKE_MKP_TASKS.append((makeMKP,(tile, neighbourfiles, outpath, gndclasses,vt, hz, buffer)))

            #makeMKP(tile, neighbourfiles, outpath, gndclasses,vt, hz, buffer)
    atr = AtlassTaskRunner(cores,MAKE_MKP_TASKS,'Making MKP', al, str(args))

    al.DumpLog()

    return
        
if __name__ == "__main__":
    main(sys.argv[1:])            