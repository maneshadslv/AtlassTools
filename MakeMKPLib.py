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


class MKPClass():

    def makeMKP(tilename, inputfolder, outpath, workingdir, gndclasses,vt, hz, buffer,tilelayoutfile, filetype,clipshape,poly,makeASCII):
        
        tl_in = AtlassTileLayout()
        tl_in.fromjson(tilelayoutfile)

        tile = tl_in.gettile(tilename)
        
        neighbourfiles = []
        neighbours = tile.getneighbours(buffer)
        for neighbour in neighbours:
            neighbourfiles.append(os.path.join(inputfolder,'{0}.{1}'.format(neighbour,filetype)).replace('\\','/'))

        print('Neighbourhood of {0} las files detected in overlapping {1}m buffer of :{2}\n Neighbourhood :'.format(len(neighbours),buffer,tilename))
        
        cleanup=[]
        outfile=os.path.join(outpath,'{0}.{1}'.format(tile.name, filetype)).replace('\\','/')
        tempfile=os.path.join(workingdir,'{0}_temp.{1}'.format(tile.name, filetype)).replace('\\','/')
        tempfile2=os.path.join(workingdir,'{0}_temp2.{1}'.format(tile.name, filetype)).replace('\\','/')
        cleanup.append(tempfile)
        cleanup.append(tempfile2)

        log = ''
        print(neighbourfiles)

        if isinstance(neighbourfiles, str):
            neighbourfiles = [neighbourfiles]
        try:
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+neighbourfiles+['-merged','-o{0}'.format(filetype),'-o',tempfile,'-keep_class'] + gndclasses
            subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]    #adds buffer
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        
            subprocessargs=['C:/LAStools/bin/lasthin64.exe','-i',tempfile,'-o{0}'.format(filetype),'-o',tempfile2,'-adaptive',vt,hz,'-set_classification',8]
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,'-o{0}'.format(filetype),'-o',outfile]
            subprocessargs=subprocessargs+['-keep_xy',tile.xmin,tile.ymin,tile.xmax,tile.ymax]    #removes buffer
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)


            if makeASCII:
                
                outfiletxt = outfile.replace('.{0}'.format(filetype), '.txt')
                subprocessargs=['C:/LAStools/bin/las2txt.exe','-i', outfile, '-rescale', 0.001, 0.001, 0.001,'-o', outfiletxt]
                subprocessargs=list(map(str,subprocessargs))       
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)


            if clipshape:
                prodclippeddir = AtlassGen.makedir(os.path.join(outpath, 'clipped')).replace('\\','/')

                ###########################################################################################################################
                #Index the product laz files

                print('Indexing files')
                AtlassGen.index(outfile)
                indexfile = outfile.replace('.laz','.lax')
                cleanup.append(indexfile)
                

                ###########################################################################################################################
                #Clipping the product las files to the AOI


                for aoi in poly:
                    aoipath,aoiname,shpext = AtlassGen.FILESPEC(aoi)
                    print('Clipping the las files to {0}'.format(aoiname))
                    aoidir = AtlassGen.makedir(os.path.join(prodclippeddir, aoiname)).replace('\\','/')
                    clippedoutput = os.path.join(aoidir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')


                    AtlassGen.clip(outfile, clippedoutput, aoi, filetype)

                    if makeASCII and os.path.exists(clippedoutput):
                        try:
                            clippedoutputtxt = os.path.join(aoidir,'{0}.txt'.format(tilename)).replace('\\','/')
                            subprocessargs=['C:/LAStools/bin/las2txt.exe','-i', clippedoutput, '-rescale', 0.001, 0.001, 0.001,'-o', clippedoutputtxt]
                            subprocessargs=list(map(str,subprocessargs))       
                            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

                        except subprocess.CalledProcessError as suberror:
                            log=log +'\n'+ "{0}\n".format(suberror.stdout)
                            print(log)



        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log ='Making MKP Failed at exception for : {0}'.format(tile.name)
            return (False, None, log)
        finally:
            if os.path.isfile(outfile):
                log ='Making MKPsuccess for : {0}'.format(tile.name)
                for file in cleanup:
                    try:
                        if os.path.isfile(file):
                            os.remove(file)   
                    except:
                        print('cleanup FAILED.') 
                    print('Cleaning Process complete')
                return (True, outfile, log)
            else:
                log ='Making MKP Failed for {0}'.format(tile.name)
                return (False, None, log)


if __name__ == '__main__':
    print('Number of variables provided : {0}'.format(print(len(sys.argv))))

    #python C:\AtlassTools\MakeMKPLib.py #tilename# D:\Processing_Data\inputfolder D:\Processing_Data\outputfolder D:\Processing_Data\workingfolder 2;8 0.15 30 200 D:\Processing_Data\inputfolder\TileLayout.json laz True D:\Processing_Data\aoi\Area_MR1_mga56.shp;D:\Processing_Data\aoi\Area_MR2_mga56.shp
    if len(sys.argv) == 13:

        print(sys.argv[1:13])
        tilename, inputfolder, outpath, workingdir, gndcls,vt, hz, buffer,tilelayoutfile, filetype,clipshape,poly = sys.argv[1:13]

    if len(sys.argv) == 11:

        print(sys.argv[1:11])
        tilename, inputfolder, outpath, workingdir, gndcls,vt, hz, buffer,tilelayoutfile, filetype = sys.argv[1:11]
        clipshape=False
        poly=""

    else:
        print("Invalid number of variables provided.")

    gndcls=gndcls.split(';')    
    poly = poly.split(';')
    vtcm =int(float(vt)*100)

    if clipshape == 'True':
        clipshape = True
    else:
        clipshape = False

    gndclasses=[]
    
    for cl in gndcls:
        gndclasses.append(int(cl))

    print(gndclasses,poly)

    outputpath = AtlassGen.makedir(os.path.join(outpath, 'makeMKP_hz_{0}_vt_{1}cm'.format(hz,vtcm))).replace('\\','/')
    workingpath = AtlassGen.makedir(os.path.join(workingdir, 'makeMKP_Working_hz_{0}_vt_{1}cm'.format(hz,vtcm))).replace('\\','/')

    MKPClass.makeMKP(tilename, inputfolder, outputpath, workingpath, gndclasses,float(vt), int(hz), int(buffer), tilelayoutfile,filetype,clipshape,poly)


