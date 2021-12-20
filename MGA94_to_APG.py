

import time

from laspy.file import File
import math
import sys
import os
from gooey import Gooey, GooeyParser
import subprocess
import datetime
from shutil import copyfile
import glob
from multiprocessing import Pool,freeze_support
import json
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

#-----------------------------------------------------------------------------------------------------------------
#Globals
#-----------------------------------------------------------------------------------------------------------------
a=1.000384332000
b=-0.000005743600
c=-8095163.209000000000
d=-403129.888000000000
f=8152070.637000000000
g=435422.127000000000



#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------




@Gooey(program_name="Trans GDA94 to ArgyleGrid", use_legacy_titles=True, required_cols=2, default_size=(1120,920))
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

    namestr=" E = b (Y - f) + a (X - g) + d + g \n N = a (Y - f) - b (X - g) + c + f "
    namestr=namestr+'\na='+str(a)+ ' b= ' +str(b) + ' c= ' +str(c)
    namestr=namestr+'\nd='+str(d) + ' f= '+str(f) + ' g= '+str(g)

    parser=GooeyParser(description=namestr)
    parser.add_argument("inputfolder", metavar="LAS file Folder", widget="DirChooser", help="Select las file folder", default=stored_args.get('inputfolder'))
    parser.add_argument("filetype",metavar="Input File Pattern", default='laz')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default=stored_args.get('layoutfile'))
    parser.add_argument("outputfolder", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputfolder'))
    parser.add_argument("-cores",metavar="Cores", type=int, default=12)

    args = parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

#-----------------------------------------------------------------------------------------------------------------
# Functions
#-----------------------------------------------------------------------------------------------------------------
def transGDA94_to_ArgyleGrid(X,Y):
    E = b *(Y - f) + a *(X - g) + d + g
    N = a *(Y - f) - b *(X - g) + c + f
    return E,N

def Rotate(X,Y,sintheta=0,costheta=1):
    """
    Rotates data using rotation formula
    x'=X*costheta - Y*sintheta
    y'=X*sintheta + Y*costheta
    """
    X1 = costheta *(X) - sintheta *(Y)
    Y1 = sintheta *(X) + costheta *(Y)
    return X1,Y1

def Translate(X,Y,Xoffset=0,Yoffset=0):
    """
    Translates X and Y by Xoffset & Yoffset
    """
    X1 = X + Xoffset
    Y1 = Y + Yoffset
    return X1,Y1

def convertFile(tilename,inputfolder,outputfolder,filetype):
    
    inputfile=os.path.join(inputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    temp_outputfile = os.path.join(outputfolder, '{0}.{1}'.format(tilename,'las')).replace('\\','/')
    outputfile = os.path.join(outputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')

    try:
        inFile = File(inputfile, mode='r')

        header =  inFile.header
        
        outfile = File(temp_outputfile, mode="w", header=header,)
        
        outfile.header.offset=[0.0, 0.0, 0.0]
    
        tic = time.perf_counter()
        X=inFile.get_x_scaled()
        Y=inFile.get_y_scaled()
        Z=inFile.get_z_scaled()
        E,N=transGDA94_to_ArgyleGrid(X,Y)
    
        outfile.points = inFile.points
        outfile.set_x_scaled(E)
        outfile.set_y_scaled(N)
        
        print(E,N,Z)
        
        toc = time.perf_counter()

        outfile.close()

        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', temp_outputfile, '-olaz', '-o', outputfile]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        log =f"{tilename} : Convertion completed in {toc - tic:0.4f}s"
        print(log)

        if os.path.isfile(outputfile):
            os.remove(temp_outputfile)

        return(True,outputfile,log)

    except:

        log =f"{tilename} : Convertion Failed"
        print(log)
        outfile.close()
        return(False,tilename,log)


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------


def main():
    #Set Arguments
    args = param_parser()

    inputfolder = args.inputfolder
    filetype = args.filetype
    tilelayoutfile = args.layoutfile
    outputdir = args.outputfolder
    cores=args.cores

    tl_out = AtlassTileLayout()
    tl_out.fromjson(tilelayoutfile)
    
    dt = strftime("%y%m%d_%H%M")
        
    outputfolder = AtlassGen.makedir(os.path.join(outputdir, (dt+'_ScaledData')).replace('\\','/'))
    
    tasks = {}
    print("Programming Starting")
    print("No of tiles in the tilelayout : {0}\n".format(len(tl_out)))
    for tile in tl_out: 
        tilename = tile.name

        tasks[tilename]= AtlassTask(tilename,convertFile,tilename,inputfolder,outputfolder,filetype)
    
    p=Pool(processes=cores)    
    results=p.map(AtlassTaskRunner.taskmanager,tasks.values())


    return()

if __name__ == "__main__":
    main() 

 