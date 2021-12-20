#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import math
import shutil
import subprocess
import os, glob
import numpy as np
import urllib
from gooey import Gooey, GooeyParser
import time
import datetime
from time import strftime
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Clip to AOIs", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3,navigation='TABBED')
def param_parser():
    parser=GooeyParser(description="Clip to AOIs")
    subs = parser.add_subparsers(help='commands', dest='command')
    main_parser = subs.add_parser('laz', help='Create Tile layout using files')
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("outputtype",metavar="Output File Type", help="las or laz\n", default='laz')
    main_parser.add_argument("poly", metavar="AOI folder", widget="DirChooser", help="Folder with Polygons(Script will take all .shp files)", default='')
    main_parser.add_argument("cores", metavar="Cores", help="Number of cores to be used\n", type=int)
    epsg_group = main_parser.add_argument_group("EPSG Settings", "Optional", gooey_options={'show_border': True,'columns': 3})
    epsg_group.add_argument("--hasepsg", metavar="Insert EPSG", action='store_true', default=False)
    epsg_group.add_argument("--epsg", metavar="EPSG value", help="EPSG value to use")
    asc_parser = subs.add_parser('asc', help='Create Tile layout using files')
    asc_parser.add_argument("inputpath", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    asc_parser.add_argument("outputpath", metavar="Output Folder", widget="DirChooser", help="Select output folder", default="")
    asc_parser.add_argument("poly", metavar="AOI folder", widget="DirChooser", help="Folder with Polygons(Script will take all .shp files)", default='')
    asc_parser.add_argument("epsg", metavar="EPSG value", help="EPSG value to use")
    asc_parser.add_argument("step", metavar="Step value", type = float)
    asc_parser.add_argument("tilesize", metavar="Tile size", help="Select Size of Tile in meters [size x size]", default=500, type=int)
    name_group = asc_parser.add_argument_group("File name settings", "Required when files have different naming conventions", gooey_options={'show_border': True,'columns': 3})
    name_group.add_argument("-hfn", "--hasfilename", metavar="Has filename pattern", action='store_true', default=False)
    name_group.add_argument("-addzero", metavar="Zeros to add", help="Multiplication to be used at the end of X and Y\n1 = None, 100, 1000 etc..", type=int)
    name_group.add_argument("--namepattern", metavar="Input File Name Convention", help="Ex: MGA55_dem_Mo%X%_%Y%_1.laz\n ", default = 'DEM-GRID_001_%X%_%Y%_500m.asc')
    asc_parser.add_argument("cores", metavar="Cores", help="Number of cores to be used\n", type=int)
    return parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------



def index(input,hasepsg, epsg,outputpath):
   
    log = ''
    try:
        if hasepsg:
            epsginput = input
            path,filename,ext = AtlassGen.FILESPEC(input)
            epsgpath = AtlassGen.makedir(os.path.join(outputpath,'epsg_added'))
            input = os.path.join(epsgpath,'{0}.{1}'.format(filename,ext))

            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', epsginput, '-epsg',epsg, '-olaz','-o',input ]
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        if os.path.isfile(input):
            return(True, input, "Success")

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        return(False, None, "Error")


def clip(input, output, poly, filetype):

    if isinstance(input,str):
        input = [input]
    log=''
    try:
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' ] + input + [ '-merged', '-poly', poly, '-o', output, '-o{0}'.format(filetype)]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(output):
            log = "Clipping {0} output : {1}".format(str(input), str(output)) 
            return (True,output, log)

        else:
            log = "Clipping failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Clipping failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)


def clipasc(tilename, ascfile, inputdir, outputdir,tempdir, aoifiles,prjfile,x,y, tilesize,step):

    path,ascfilename,ext = AtlassGen.FILESPEC(ascfile)
    deletefiles = []
    print(tilename)

    ###########################################################################################################################
    #Convert asci to laz
    #asciigridtolas(dtmlazfile)

    print('Converting ASC to LAZ')

    #files
    lasfile=os.path.join(tempdir,'{0}.laz'.format(ascfilename)).replace('\\','/')

    AtlassGen.asciigridtolas(ascfile, lasfile, 'laz')
    deletefiles.append(lasfile)
    

    ###########################################################################################################################
    #Index the product laz files
    #index(demlazfile)

    AtlassGen.index(lasfile)
    lax=os.path.join(tempdir,'{0}.lax'.format(ascfilename)).replace('\\','/')
    deletefiles.append(lax)

    ###########################################################################################################################
    #Clipping the product las files to the AOI
    #lasclip demlazfile

    prodclippeddir = AtlassGen.makedir(os.path.join(outputdir, 'clipped')).replace('\\','/')
    print('Clipping the las files to AOI')

    for aoi in aoifiles:

        path, aoiname, ext = AtlassGen.FILESPEC(aoi)
        print('Clipping files to the AOI : {0}'.format(aoi))
        aoidir = AtlassGen.makedir(os.path.join(prodclippeddir,aoiname))


        #files 

        lasoutput = os.path.join(aoidir,'{0}.laz'.format(ascfilename)).replace('\\','/')

        clip(lasfile, lasoutput, aoi, 'laz')

        if os.path.isfile(lasoutput):
            deletefiles.append(lasoutput)
            print('Converting Clipped laz to asc')
        
            #############################################################################################################################
            #Convert the laz files to asci


            ascoutput=os.path.join(aoidir,'{0}.asc'.format(ascfilename)).replace('\\','/')
            prjfile1 = os.path.join(aoidir,'{0}.prj'.format(ascfilename)).replace('\\','/')

        
            AtlassGen.lastoasciigrid(int(x), int(y), lasoutput, ascoutput, int(tilesize), step)
     
            shutil.copyfile(prjfile, prjfile1) 

    for delfile in deletefiles:
        os.remove(delfile)

    return(True,ascfile,"NONE")
    



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()

    if args.command == 'laz':
        inputfolder = args.inputfolder
        aoifolder = args.poly
        poly = AtlassGen.FILELIST(['*.shp'],aoifolder)
        print('\nNumber of AOIS found: {1}\n\n AOIS : {0}'.format(poly, len(poly)))
        cores = args.cores
        hasepsg = args.hasepsg
        epsg = args.epsg
    
        outputpath=args.outputpath.replace('\\','/')
        outputpath = AtlassGen.makedir(os.path.join(outputpath, '{0}_Clipped'.format(strftime("%y%m%d_%H%M"))))
        outputtype = args.outputtype
        logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

        log = open(logpath, 'w')
        
        filepattern = args.filepattern.split(';')
        print("Reading {0} files \n".format(filepattern))
        files = AtlassGen.FILELIST(filepattern, inputfolder)
    

        ###########################################################################################################################
        #Index the files

    
        index_tasks={}
        for file in files:
            path, filename, ext = AtlassGen.FILESPEC(file)
            tilename = filename
            indexfile = os.path.join(path, '{0}.{1}'.format(filename, 'lax'))

            if not os.path.isfile(indexfile):
                index_tasks[tilename] = AtlassTask(tilename, index, file,hasepsg,epsg,outputpath)

        if len(index_tasks) == 0:
            print('################## Skipping Indexing ####################')

        else:
            print('Indexing files')
            p=Pool(processes=cores)  
            index_results=p.map(AtlassTaskRunner.taskmanager,index_tasks.values())

        ###########################################################################################################################
        #Clipping the filesto the AOI
        cliping_tasks = {}   
        areanumber =0
        for aoi in poly:

            path, aoiname, ext = AtlassGen.FILESPEC(aoi)
            print('Clipping files to the AOI : {0}'.format(aoi))
            aoidir = AtlassGen.makedir(os.path.join(outputpath,aoiname))

            
            for file in files:

                path, filename, ext = AtlassGen.FILESPEC(file)
                tilename = filename


                input = file
                if hasepsg:
                    epsgpath = os.path.join(outputpath,'epsg_added')
                    input = os.path.join(epsgpath,'{0}.{1}'.format(filename,ext))

                output = os.path.join(aoidir, '{0}.{1}'.format(filename, outputtype)).replace("\\", "/")
                tareaname = '{0}_{1}'.format(tilename,areanumber)
                cliping_tasks[tareaname] = AtlassTask(tareaname, clip, input, output, aoi, outputtype)
            areanumber+=1

        p=Pool(processes=cores) 
        clipping_results=p.map(AtlassTaskRunner.taskmanager,cliping_tasks.values()) 

        ###########################################################################################################################
    
        for result in clipping_results:
            log.write(result.log)        


    if args.command == 'asc':

        inputpath = args.inputpath
        outputpath = args.outputpath
        aoifolder = args.poly
        poly = AtlassGen.FILELIST(['*.shp'],aoifolder)
        print('\nNumber of AOIS found: {1}\n\n AOIS : {0}'.format(poly, len(poly)))
        cores = args.cores
        epsg = args.epsg
        tilesize = args.tilesize
        step = args.step


        outputpath = AtlassGen.makedir(os.path.join(outputpath,'Clipping_asc').replace('\\','/'))
        tempdir = AtlassGen.makedir(os.path.join(outputpath,'temp').replace('\\','/'))
        if not epsg == None:
  
            prjfile2 = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            prjfile = os.path.join(outputpath,'{0}.prj'.format(epsg)).replace('\\','/')

            if os.path.isfile(prjfile2):
                shutil.copy(prjfile2,prjfile)
            else:
                print("PRJ file for {1} is not available in 10.10.10.142".format(epsg))

        if args.hasfilename:
            namepattern = args.namepattern
            searchpattern=namepattern.replace("%X%","*")
            searchpattern=searchpattern.replace("%Y%","*")
            print(searchpattern)
            patternsplit=searchpattern.split("*")
        
            print(patternsplit)
            addzero = args.addzero

        files = AtlassGen.FILELIST(['*.asc'], inputpath)
        tasks = {}

        for item in files:

            if not args.hasfilename:
                path, tilename, ext = AtlassGen.FILESPEC(item)
                x,y = tilename.split('_')

                tilename = '{0}_{1}'.format(x,y)

        
            else:
                filespec=AtlassGen.FILESPEC(item)
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
                    tilename = '{0}_{1}'.format(x,y)
        
                else:
                    if namepattern.find("%X%")>namepattern.find("%Y%"):
                        coords.reverse()
                    x=int(float(coords[0]))
                    y=int(float(coords[1]))
                    tilename = '{0}_{1}'.format(x,y)

            print(tilename)
            tasks[tilename] = AtlassTask(tilename, clipasc, tilename, item, inputpath, outputpath, tempdir,aois, prjfile, x,y, tilesize,step)


        p=Pool(processes=cores) 
        clipping_results=p.map(AtlassTaskRunner.taskmanager, tasks.values())




    print("Process Complete")
    return


if __name__ == "__main__":
    main()         

