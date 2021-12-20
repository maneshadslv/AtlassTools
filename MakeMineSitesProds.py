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
import urllib
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
import fnmatch

#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 01/10/2016 -Alex Rixon - Added functionality to create hydro flattening points. 
# 01/10/2016 -Alex Rixon - Added functionality to create CHM  
# 30/09/2016 -Alex Rixon - Added functionality to create DHM 
# 20/09/2016 -Alex Rixon - Original development Alex Rixon
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

#-----------------------------------------------------------------------------------------------------------------
#grid class
#-----------------------------------------------------------------------------------------------------------------
      
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
@Gooey(program_name="Minning Sites Prod Gen", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=2)
def param_parser():

    globalmapperversions = glob.glob('C:\\Program Files\\'+'GlobalMapper*')

    if len(globalmapperversions) >= 2:
        for vers in globalmapperversions:
            if fnmatch.fnmatch(vers, '*GlobalMapper2*'):
                globalmapperexe = '{0}\\global_mapper.exe'.format(vers)
            elif fnmatch.fnmatch(vers, '*GlobalMapper18*'):
                globalmapperexe = '{0}\\global_mapper.exe'.format(vers)
        
    else:  
        globalmapperexe = '{0}\\global_mapper.exe'.format(globalmapperversions[0])


    main_parser=GooeyParser(description="Minning Sites Prod Gen")
    main_parser.add_argument("inputpath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default='')
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    main_parser.add_argument("inputgeojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default='')
    main_parser.add_argument("outputgeojsonfile", metavar="Output TileLayout file", widget="FileChooser", help="Select .json file", default='')
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default='')
    main_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default='') 
    main_parser.add_argument("aoifiles", metavar="AOI shp file", widget="MultiFileChooser", help="Select aoi shape file/s for clipping", default='')
    main_parser.add_argument("gndclasses", metavar = "Ground Classes", default="2 8")
    main_parser.add_argument("cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    main_parser.add_argument("gmexe", metavar="Global Mapper EXE", widget="FileChooser", help="Location of Global Mapper exe",default=globalmapperexe)
    Emboss_group = main_parser.add_argument_group("Emboss Images", "Emboss Image", gooey_options={'show_border': True,'columns': 4})
    Emboss_group.add_argument("-emb", "--makeEMB", metavar="Emboss Image", action='store_true')
    Emboss_group.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    Emboss_group.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    Emboss_group.add_argument("-k", "--kill",metavar="Kill", help="Maximum triagulation length", type=int, default=250)
    Emboss_group.add_argument("epsg", metavar="EPSG", help="GDA2020 = 78**, GDA94 = 283**, AGD84 = 203**, AGD66 = 202**\n ** = zone")
    Emboss_group.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    MKP_group = main_parser.add_argument_group("MKP", "MKP files", gooey_options={'show_border': True,'columns': 4})
    MKP_group.add_argument("-mkp", "--makeMKP", metavar="MKP", action='store_true')
    MKP_group.add_argument("-hz", metavar="hz", help="Provide maximum horizontal distance", default=20, type=int)
    MKP_group.add_argument("-vt", metavar="vt", help="Provide vertical accuracy requirement", default=0.10, type=float) 
    MKP_group.add_argument("-txt", "--makeTXT", metavar="Make Ascii files", action='store_true')


    return main_parser.parse_args()


def makeMKPperTile(tilename,xmin,ymin,xmax,ymax,tilesize, inputfolder,mkp_output, mkp_working, main_workingdir, gndclasses,vt, hz, buffer,tl_in, filetype,aois,makeEMB):

    deletefiles = []
    log = ''
   
    #Generate buffered file if not created in makeEMP route.
    if makeEMB == False:
        
        print('Creating tile neighbourhood for : {0}'.format(tilename))
        buffdir = AtlassGen.makedir(os.path.join(main_workingdir, 'buffered')).replace('\\','/')
        neighbourlasfiles = []
        neighbours = []
        makebuff_results = []

        try:
            neighbours =  tl_in.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

        except:
            log = "tile: {0} does not exist in geojson file".format(tilename)
            print(log)
            return(False,None,log)

        print('Neighbours : {0}'.format(neighbours))
        
        #files
        for neighbour in neighbours:
            neighbour = os.path.join(inputfolder, '{0}.{1}'.format(neighbour, filetype))
            if os.path.isfile(neighbour):
                print('\n{0}'.format(neighbour))
                neighbourlasfiles.append(neighbour)
            else:
                print('\nFile {0} could not be found in {1}'.format(neighbour, inputfolder))
                                            #input, outputpath, x, y, filename,tilesize, buffer, gndclasses, filetype, step 
        makebuff_results = makeBufferedFiles(neighbourlasfiles, buffdir, int(xmin), int(ymin), tilename, int(tilesize), int(buffer), gndclasses, filetype)

        bufferedfile = makebuff_results[1]
        

    else:
        buffered_dir= os.path.join(main_workingdir,'buffered')
        bufferedfile= os.path.join(buffered_dir,'{0}.laz'.format(tilename)).replace('\\','/')

    print(bufferedfile)
    if os.path.exists(bufferedfile):
        deletefiles.append(bufferedfile)
        tempfile = os.path.join(mkp_working,'{0}_temp.laz'.format(tilename)).replace('\\','/')
        outfile = os.path.join(mkp_output,'{0}.laz'.format(tilename)).replace('\\','/')
        deletefiles.append(tempfile)
        try:
        
            subprocessargs=['C:/LAStools/bin/lasthin64.exe','-i',bufferedfile,'-olaz','-o',tempfile,'-adaptive',vt,hz,'-set_classification',8]
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile,'-olaz','-o',outfile]
            subprocessargs=subprocessargs+['-keep_xy',xmin,ymin,xmax,ymax]    #removes buffer
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            ###################################################################################################################
            #Starting Clipping format
            prodclippeddir = AtlassGen.makedir(os.path.join(mkp_output, 'clipped')).replace('\\','/')
     

            ###########################################################################################################################
            #Index the product laz files

            print('Indexing files')
            AtlassGen.index(outfile)
            indexfile = outfile.replace('laz','lax')
            deletefiles.append(indexfile)
            

            ###########################################################################################################################
            #Clipping the product las files to the AOI


            for aoi in aois:
                aoipath,aoiname,shpext = AtlassGen.FILESPEC(aoi)
                print('Clipping the las files to {0}'.format(aoiname))
                aoidir = AtlassGen.makedir(os.path.join(prodclippeddir, aoiname)).replace('\\','/')
                clippedoutput = os.path.join(aoidir,'{0}.laz'.format(tilename)).replace('\\','/')
    
                AtlassGen.clip(outfile, clippedoutput, aoi, filetype)
      
    

        except subprocess.CalledProcessError as suberror:
            
            log = log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log ='Making MKP Failed at exception for : {0}'.format(tilename)
            return (False, None, log)
        finally:
            if os.path.isfile(outfile):
                log ='Making MKPsuccess for : {0}'.format(tilename)
                for file in deletefiles:
                    try:
                        if os.path.isfile(file):
                            os.remove(file)   
                    except:
                        print('cleanup FAILED.') 
                    print('Cleaning Process complete')
                return (True, outfile, log)
            else:
                log ='Making MKP Failed for {0}'.format(tilename)
                return (False, None, log)


    else:
        log = 'Unable to find the buffered file {0}'.format(bufferedfile)
        print(log)
        return(False,None,log)


def makeBufferedFiles(input, outputpath, x, y, filename,tilesize, buffer, gndclasses, filetype ):

    if isinstance(input, str):
        input = [input]

    bufflasfile = os.path.join(outputpath,'{0}.{1}'.format(filename, filetype)).replace('\\','/') 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(x-buffer), y-buffer, x+tilesize+buffer, y+tilesize+buffer)
    keep=keep.split()
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + input + ['-olaz','-o', bufflasfile,'-merged','-dont_remove_empty_files','-keep_class'] + gndclasses + keep #'-rescale',0.001,0.001,0.001,
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)      

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making Buffered for {0} /nException {1}".format(bufflasfile, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufflasfile):
            log = "Making Buffered for {0} Success".format(bufflasfile)
            return (True,bufflasfile, log)

        else: 
            log = "Making Buffered for {0} Failed".format(bufflasfile)
            return (False,None, log)


            #int(xmin), int(ymin), tilename, bufferedFile, proddir, output, buffer, kill, step, gndclasses, hydropointsfiles, int(tilesize), filetype
def MakeDEM(x, y, tilename, gndfile, workdir, dtmfile, buffer, kill, step, gndclasses, hydropoints, tilesize, filetype):
    #need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
    #use this file for MKP, just remember to remove buffer
    #This will need clipping to AOI
    log = ''
    #Prep RAW DTM
    
    #set up clipping    
    keep='-keep_xy {0} {1} {2} {3}'.format(x-buffer,y-buffer,x+tilesize+buffer,y+tilesize+buffer)
    keep=keep.split()
    print('Making DEM for : {0}'.format(gndfile))
    
    try:
        #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
        print("Checking for Hydro files")
        if not hydropoints==None:
            hydfile=os.path.join(workdir,'{0}_{1}_hydro.{2}'.format(x, y,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + hydropoints + ['-merged','-o{0}'.format(filetype),'-o', hydfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("clipped Hydro points")

            gndfile2 = gndfile
            gndfile=os.path.join(workdir,'{0}_{1}_dem_hydro.{2}'.format(x,y,filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile2, hydfile,'-merged','-o{0}'.format(filetype),'-o',gndfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("added Hydro points")

        else:
            print("No Hydro files")
        

        print("DEM starting")
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o', dtmfile,'-nbits',32,'-kill',kill,'-step',step] 
        subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]    
        #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    


    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)


    except:
        print('{0}: DEM output FAILED.'.format(tilename))
        log = 'DEM creation Failed for {0} at Subprocess.'.format(tilename)
        return(False, None, log)


    finally:
        if os.path.isfile(dtmfile):
            
            log = 'DEM output Success for: {0}.'.format(tilename)
            return(True, dtmfile, log)
        else:
            log = 'DEM creation Failed for: {0}.'.format(tilename)
            return(False, None, log)


def asciigridtolas(input, output , filetype):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''

    log = ''
    if os.path.isfile(input):
        print('Converting {0} to las'.format(input))
    try:
       #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-o{0}'.format(filetype), '-o', output, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting {0} file  to {1} Failed at exception'.format(input, filetype)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {0} file  to {1} success'.format(input, filetype)
            return (True, output, log)
        else:
            log ='Converting {0} file  to {1} Failed'.format(input, filetype)
            return (False, output, log)

def asciigridtoTIF(input,output,step):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''
    temp = input.replace('.asc','_temp.laz')
    
    log = ''
    if os.path.isfile(input):
        print('Converting {0} to TIF'.format(input))
    try:
       
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-olaz', '-o', temp, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', temp, '-otif','-o', output, '-step',step,'-elevation','-highest']
        subprocessargs=list(map(str,subprocessargs))       
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting {0} file  to {1} Failed at exception'.format(input,'TIF')
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {0} file  to {1} success'.format(input,'TIF')
            if os.path.isfile(temp):
                os.remove(temp)

            return (True, output, log)
        else:
            log ='Converting {0} file  to {1} Failed'.format(input,'TIF')
            return (False, output, log)

def lastoasciigrid(x,y,inputF, output, tilesize, step):
    '''
    Converts a las/laz file to ascii and retains the milimetre precision.
    '''

    if os.path.isfile(inputF):
        log = ''
        try:
        #las2las -i <dtmfile> -olas -o <dtmlazfile>
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', inputF, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
            subprocessargs=list(map(str,subprocessargs))       
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log ='Converting las to asc Failed at exception for : {0}'.format(inputF)
            return (False, output, log)
        finally:
            if os.path.isfile(output):
                log ='Converting las to asc success for : {0}'.format(inputF)
                return (True, output, log)
            else:
                log ='Converting las to asc Failed for {0}'.format(inputF)
                return (False, output, log)
    else:
        return(True,None,'Not input File')

def lastotif(inputF, output, tilesize, step):
    '''
    Converts a las/laz file to tiff and retains the milimetre precision.
    '''

    if os.path.isfile(inputF):
        log = ''
        try:
        #las2las -i <dtmfile> -olas -o <dtmlazfile>
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', inputF, '-merged','-otif','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
            #subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
            subprocessargs=list(map(str,subprocessargs))       
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log ='Converting las to TIF Failed at exception for : {0}'.format(inputF)
            return (False, output, log)
        finally:
            if os.path.isfile(output):
                log ='Converting las to TIF success for : {0}'.format(inputF)
                return (True, output, log)
            else:
                log ='Converting las to TIF Failed for {0}'.format(inputF)
                return (False, output, log)
    else:
        return(True,None,'Not input File')

def index(input):
   
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        return(True, None, "Success")

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
                
#aoidir,mergedlasfile,mergedascfile,step,filetype
def merge_product(inputdir, mergedlasfile, output, step, filetype):
   
    input = '{0}/*.{1}'.format(inputdir, filetype)
    log=''
    try:
        #las2las -i (asciigridtolas_results.path)\*.laz -merged -step step -oasc -o product\merged\merged_"product".asc

        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', input, '-merged', '-olas', '-o', mergedlasfile]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
   

        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', mergedlasfile, '-merged','-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
        subprocessargs=list(map(str,subprocessargs))       
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

      
        if os.path.isfile(output):
            log = "Merged input : {0} \nMerged output : {1}".format(str(input), str(output)) 
            return (True,output, log)

        else:
            log = "Merging failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Merging failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)

                    #aoidir,mergedlasfile,outfile,filetype
def merge_product_mkp(inputdir, mergedlasfile, mergedtxtfile, makeTXT):
   
    input = '{0}/*.laz'.format(inputdir)
    log=''
    try:
        #las2las -i (asciigridtolas_results.path)\*.laz -merged -step step -oasc -o product\merged\merged_"product".asc

        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', input, '-merged', '-olas', '-o', mergedlasfile]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
   
        if makeTXT:
            subprocessargs=['C:/LAStools/bin/las2txt.exe','-i', mergedlasfile, '-rescale', 0.001, 0.001, 0.001,'-o', mergedtxtfile]
            subprocessargs=list(map(str,subprocessargs))       
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

      
        if os.path.isfile(output):
            log = "Merged input : {0} \nMerged output : {1}".format(str(input), str(mergedtxtfile)) 
            return (True,mergedtxtfile, log)

        else:
            log = "Merging failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Merging failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)



def makeEmbossperTile(tl_in, tl_out,xmin,ymin,xmax,ymax,tilename,tilesize,inputfolder,workingdir,outputdir,filetype,hydropointsfiles,buffer,gndclasses, step, kill,aoifiles,prjfile,gsd):

    ##########################################################################################################################
    #Making the neighbourhood files
    #######################################################################################################################
    print('Creating tile neighbourhood for : {0}'.format(tilename))
    buffdir = AtlassGen.makedir(os.path.join(workingdir, 'buffered')).replace('\\','/')
    neighbourlasfiles = []
    neighbours = []
    makebuff_results = []
    deletefiles = []
    try:
        neighbours =  tl_in.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    except:
        print("tile: {0} does not exist in geojson file".format(tilename))

    print('Neighbours : {0}'.format(neighbours))
    
    #files
    for neighbour in neighbours:
        neighbour = os.path.join(inputfolder, '{0}.{1}'.format(neighbour, filetype))
        if os.path.isfile(neighbour):
            print('\n{0}'.format(neighbour))
            neighbourlasfiles.append(neighbour)
        else:
            print('\nFile {0} could not be found in {1}'.format(neighbour, inputfolder))
                                        #input, outputpath, x, y, filename,tilesize, buffer, gndclasses, filetype, step 
    makebuff_results = makeBufferedFiles(neighbourlasfiles, buffdir, int(xmin), int(ymin), tilename, int(tilesize), int(buffer), gndclasses, filetype)

    #deletefiles.append(makebuff_results[1])

    proddir = AtlassGen.makedir(os.path.join(workingdir, 'DEM_{0}m'.format(step))).replace('\\','/')
    proddir_out = AtlassGen.makedir(os.path.join(outputdir, 'DEM_{0}m'.format(step))).replace('\\','/')
    product_files = []



    prjfile1 = os.path.join(proddir,'{0}.prj'.format(tilename)).replace('\\','/')
    DEMfile = os.path.join(proddir,'{0}.asc'.format(tilename)).replace('\\','/')


    product_files.append(DEMfile)
    product_files.append(prjfile1)
   
                        
    if makebuff_results[0]:
            

        #files
        bufferedFile=os.path.join(buffdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
        MakeDEM(int(xmin), int(ymin), tilename, bufferedFile, proddir, DEMfile, buffer, kill, step, gndclasses, hydropointsfiles, int(tilesize), filetype)

    else:
        print('Unable to find buffered file for tile {0}'.format(tilename))


    if os.path.isfile(DEMfile):
        shutil.copyfile(prjfile, prjfile1) 


        ###########################################################################################################################
        #Convert asci to laz
        #asciigridtolas(dtmlazfile)

        print('Converting ASC to LAZ')

        #files
        time.sleep(1)
        asc=DEMfile
        las=os.path.join(proddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')

        asciigridtolas(asc, las, filetype)
        deletefiles.append(las)
        

        ###########################################################################################################################
        #Index the product laz files
        #index(demlazfile)

        index(las)
        lax=os.path.join(proddir,'{0}.lax'.format(tilename)).replace('\\','/')
        deletefiles.append(lax)

        ###########################################################################################################################
        #Clipping the product las files to the AOI
        #lasclip demlazfile

        prodclippeddir = AtlassGen.makedir(os.path.join(proddir, 'clipped')).replace('\\','/')
        print('Clipping the las files to AOI')

        for aoi in aoifiles:

            path, aoiname, ext = AtlassGen.FILESPEC(aoi)
            print('Clipping files to the AOI : {0}'.format(aoi))
            aoidir = AtlassGen.makedir(os.path.join(prodclippeddir,aoiname))

            print(tilename)


            #files 
            lasinput=os.path.join(proddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') #dtmlaz
            lasoutput = os.path.join(aoidir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
    
            clip(lasinput, lasoutput, aoi, filetype)

            if os.path.isfile(lasoutput):
                deletefiles.append(lasoutput)
                print('Converting Clipped {0} to asc'.format(filetype))
            
                #############################################################################################################################
                #Convert the laz files to asci
                #lasgrid
                #TODo
                #files
            
                ascoutput=os.path.join(aoidir,'{0}.asc'.format(tilename)).replace('\\','/')
                prjfile1 = os.path.join(aoidir,'{0}.prj'.format(tilename)).replace('\\','/')
                lastoasciigrid(int(xmin), int(ymin), lasoutput, ascoutput, int(tilesize), step)
                product_files.append(ascoutput)
                product_files.append(prjfile1)
                shutil.copyfile(prjfile, prjfile1) 
    
    else:
        print("DEM file not created for {0}".format(tilename))
        return(True,tilename,"{DEM file not created for {0}".format(tilename))


    print("-----------------Copying product files -----------------")
    for sourcef in product_files:

        destf = sourcef.replace(proddir, proddir_out)
        path,df,ext = AtlassGen.FILESPEC(destf)
        if not os.path.exists(path):
            AtlassGen.makedir(path)
        
        print("copying {0}\n".format(sourcef))
        try:
            shutil.copy(sourcef, destf)
        except Exception as e:
            print ("Unable to copy file.{0}".format(e))
        finally:
            print('deleting {0}'.format(sourcef))
            os.remove(sourcef)
            
    print("-------------------------------------------------------")
    '''
    if not merged:         
        for deletef in deletefiles:
            print('Deleting {0}'.format(deletef))
            if os.path.isfile(deletef):
                os.remove(deletef)
    '''
    log = "Finished making products. No clipping selected"
    return(True,tilename,log)                
    

#neighbourlasfiles, buffdir, int(xmin), int(ymin), tilename, int(tilesize), int(buffer),filetype, step
def makeBuffer(input, outputpath, x, y, filename,tilesize, buffer, filetype, step):

    if isinstance(input, str):
        input = [input]

    bufflasfile = os.path.join(outputpath,'{0}.{1}'.format(filename, filetype)).replace('\\','/') 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(x-buffer), y-buffer, x+tilesize+buffer, y+tilesize+buffer)
    keep=keep.split()
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + input + ['-olaz','-o', bufflasfile,'-merged'] + keep #'-rescale',0.001,0.001,0.001,
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)      
        

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making Buffered for {0} /nException {1}".format(bufflasfile, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufflasfile):
            log = "Making Buffered for {0} Success".format(bufflasfile)
            return (True,bufflasfile, log)

        else: 
            log = "Making Buffered for {0} Failed".format(bufflasfile)
            return (False,None, log)  

def makegmsfiles(filename,inpath,outpath,buffoutpath,clipoutpath,tile,zone, AOI_clip, index,tilelayoutfile,dstfile):

    template = "\\\\10.10.10.142\\projects\\PythonScripts\\templates\\Template_Minsite.gms"
    
    outputpath = outpath+"\\"
    buffout = buffoutpath+"\\"
    inpath = inpath+"\\"
    clipout = clipoutpath+"\\"
    shutil.copyfile(template, dstfile)
    log = ''

    print(filename,inpath,outpath,buffoutpath,clipoutpath,tile,zone, AOI_clip, index,tilelayoutfile)
    try:
        with open(dstfile, 'r') as g:
            data = g.read()

            while '<Filename>' in data:
                data = data.replace('<Filename>', filename)
            while '<Outpath>' in data:
                data = data.replace('<Outpath>', outpath)
            while '<InPath>' in data:
                data = data.replace('<InPath>', inpath)
            while '<BuffOutpath>' in data:
                data = data.replace('<BuffOutpath>', buffout)
            while '<ClipOutpath>' in data:
                data = data.replace('<ClipOutpath>', clipout)
            while '<zone>' in data:
                data = data.replace('<zone>', zone)
            while '<AOI_clip>' in data:
                data = data.replace('<AOI_clip>', AOI_clip)
            while '<xmin>' in data:
                data = data.replace('<xmin>', str(tile.xmin))
            while '<ymin>' in data:
                data = data.replace('<ymin>', str(tile.ymin))
            while '<xmax>' in data:
                data = data.replace('<xmax>', str(tile.xmax))
            while '<ymax>' in data:
                data = data.replace('<ymax>', str(tile.ymax))
            while '<index>' in data:
                data = data.replace('<index>', str(index))
            while '<tilelayoutfile>' in data:
                data = data.replace('<tilelayoutfile>', str(tilelayoutfile))   

        with open(dstfile, 'w') as f:
                f.write(data)
        if os.path.exists(dstfile):
            log = 'Successfully created GMS file for :{0}'.format(filename)
            return(True,dstfile,log)
        else:
            log = 'Could not create GMS file for :{0}'.format(filename)
            return(False,None,log)

    
    except:
        log = 'Could not create GMS file for :{0}, Failed at exception'.format(filename)
        return(False,None,log)
    

def rungmsfiles(gmpath, gmsfile):
    log = ''

    try:
        subprocessargs=[gmpath, gmsfile]
        subprocessargs=list(map(str,subprocessargs))
        #print(subprocessargs)
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        log = 'Making Contours was successful for {0}'.format(gmsfile)
        return (True,None, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (True,None,log)

    except:
        log = 'Could not run GMS file for {0}, Failed at Subprocess'.format(gmsfile)  
        return (False,None, log)


    
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support() 
    args = param_parser()

    #create variables from gui
    inputfolder = args.inputpath
    inputfolder = inputfolder.replace('\\','/')
    if not args.outputpath==None:
        outputpath=args.outputpath
        outputpath=outputpath.replace('\\','/')
    else:
        outputpath = args.workpath
    workingpath = args.workpath
    workingpath = workingpath.replace('\\','/')
    buffer=float(args.buffer)
    hydropointsfiles=None
    if not args.hydropointsfiles==None:
        hydropointsfiles=args.hydropointsfiles
        hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')

    step=float(args.step)
    kill=float(args.kill)
    gndclasses=args.gndclasses.split()    
    makeEMB=args.makeEMB
    makeMKP=args.makeMKP
    cores = args.cores
    filetype = args.filetype
    aoifiles = args.aoifiles.split(';')
    epsg = args.epsg

    hz=args.hz
    vt=args.vt
    makeTXT = args.makeTXT
    gmpath = args.gmexe
    print(makeEMB)


    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')

    if not args.inputgeojsonfile == None:
        ingeojsonfile = args.inputgeojsonfile

    if not args.outputgeojsonfile == None:
        outgeojsonfile = args.outputgeojsonfile

    
    #read tilelayout into library
    tl_in = AtlassTileLayout()
    tl_in.fromjson(ingeojsonfile)

    tl_out = AtlassTileLayout()
    tl_out.fromjson(outgeojsonfile)

    print("No of Tiles in Input Tilelayout : {0}".format(len(tl_in)))
    print("No of Tiles in Output Tilelayout : {0}".format(len(tl_out)))
    dt = strftime("%y%m%d_%H%M")

    outputdir = AtlassGen.makedir(os.path.join(outputpath, '{0}_minesiteProds'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, '{0}_minesite_Working'.format(dt))).replace('\\','/')



 
    if makeEMB==True:
        
        gsd = ''
        if step < 1:
            gsd = '0_{0}'.format(int(step*100))
        elif step < 10:
            gsd = '00{0}'.format(str(int(step)))
        elif step >=10:
            gsd = '0{0}'.format(str(int(step)))
        print('gsd : {0}'.format(gsd))

        if not args.epsg == None:
            epsg = args.epsg
            prjfile2 = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            prjfile = os.path.join(workingdir,'{0}.prj'.format(epsg)).replace('\\','/')

            if os.path.isfile(prjfile2):
                shutil.copy(prjfile2,prjfile)
            else:
                print("PRJ file for {1} is not available in 10.10.10.142".format(epsg))

        make_dems = {}
        make_dems_results = []
        
        ########################################################################################################################
        ## Make FCM for tiles in the output tilelayout
        #######################################################################################################################

        for tile in tl_out: 
            xmin = tile.xmin
            ymin = tile.ymin
            xmax = tile.xmax
            ymax = tile.ymax
            tilename = tile.name
            tilesize = int(tile.xmax - tile.xmin)

            make_dems[tilename] = AtlassTask(tilename, makeEmbossperTile, tl_in, tl_out, xmin,ymin,xmax,ymax,tilename,tilesize,inputfolder,workingdir,outputdir,filetype,hydropointsfiles,buffer, gndclasses, step, kill,aoifiles,prjfile,gsd)
                                                                                #tl_in, tl_out,xmin,ymin,xmax,ymax,tilename,tilesize,inputfolder,workingdir,outputdir,filetype,hydropointsfiles,buffer,gndclasses, step, kill,aoifiles,prjfile,gsd)
        
        print(len(make_dems))
        p=Pool(processes=cores)        
        make_dems_results=p.map(AtlassTaskRunner.taskmanager,make_dems.values())

        ########################################################################################################################
        ## Merge files
        #######################################################################################################################


        print("Starting to Merge files")




        proddir = os.path.join(workingdir, 'DEM_{0}m'.format(step)).replace('\\', '/')
        proddir_dest = os.path.join(outputdir,'DEM_{0}m'.format(step)).replace('\\','/')
        prodclippeddir = AtlassGen.makedir(os.path.join(proddir, 'clipped')).replace('\\','/')
        prodclippeddir_dest = AtlassGen.makedir(os.path.join(proddir_dest, 'clipped')).replace('\\','/')
        
        for aoi in aoifiles:

            path, aoiname, ext = AtlassGen.FILESPEC(aoi)
            print('Merging files for AOI : {0}'.format(aoiname))
            aoidir = AtlassGen.makedir(os.path.join(prodclippeddir,aoiname)).replace('\\','/')
            aoidir_dest = AtlassGen.makedir(os.path.join(prodclippeddir_dest,aoiname)).replace('\\','/')
            mergeddir = AtlassGen.makedir(os.path.join(aoidir, 'merged')).replace('\\','/')
            mergeddir_dest = AtlassGen.makedir(os.path.join(aoidir_dest, 'merged')).replace('\\','/')
            mergedlasfile = os.path.join(mergeddir,"{0}.{1}".format(aoiname,filetype)).replace('\\','/')
            mergedascfile = os.path.join(mergeddir,"{0}.asc".format(aoiname)).replace('\\','/')
            copy_file = os.path.join(mergeddir_dest,"{0}.asc".format(aoiname)).replace('\\','/')
            mergedpngfile = os.path.join(mergeddir_dest,"{0}.png".format(aoiname)).replace('\\','/')
            prj = os.path.join(mergeddir_dest,"{0}.prj".format(aoiname)).replace('\\','/')
            gmsfile = os.path.join(workingdir,"{0}.gms".format(aoiname)).replace('\\','/')

            merge_product(aoidir,mergedlasfile,mergedascfile,step,filetype)
        
            if os.path.isfile(mergedascfile):
                print('Copying Merged DEM file for AOI : {0}'.format(aoiname))
                shutil.copy(mergedascfile,copy_file)
                shutil.copy(prjfile,prj)
                if os.path.isfile(copy_file):
                    print('Merged DEM file copied for AOI : {0}\n\n'.format(aoiname))

                    gms = '''GLOBAL_MAPPER_SCRIPT VERSION="1.00"
UNLOAD_ALL 
LOAD_PROJECTION FILENAME="{0}" \\
DEFINE_SHADER SHADER_NAME="Emboss" BLEND_COLORS="YES" STRETCH_TO_RANGE="YES" SHADE_SLOPES="NO" \\
    SLOPES_PERCENT="NO" OVERWRITE_EXISTING="NO" SAVE_SHADER="YES" 
    0,RGB(255,255,255)
END_DEFINE_SHADER
SET_VERT_DISP_OPTS SHADER_NAME="Emboss" AMBIENT_LIGHT_LEVEL="0.10000000" VERT_EXAG="1.0000000" \\
    LIGHT_ALTITUDE="51.000000" LIGHT_AZIMUTH="45.000000" LIGHT_NUM_SOURCES="1" LIGHT_BLENDING_ALGORITHM="0" \\
    SLOPE_ALGORITHM="0" ENABLE_HILL_SHADING="YES" SHADE_DARKNESS="0" SHADE_HIGHLIGHT="0" \\
    ENABLE_WATER="NO" WATER_ALPHA="128" WATER_LEVEL="0.0000000000" WATER_COLOR="RGB(0,0,255)"
SET_SHADER_OPTS HSV="HSV=0.000000,1.000000,1.000000,360.000000"
IMPORT FILENAME="{1}" \\
    TYPE="ARCASCIIGRID" LABEL_FIELD_FORCE_OVERWRITE="NO" LABEL_FORMAT_NUMBERS="YES" \\
    LABEL_PRECISION="-1" LABEL_REMOVE_TRAILING_ZEROS="YES" LABEL_USE_SCIENTIFIC_NOTATION="NO" \\
    SAMPLING_METHOD="NEAREST_NEIGHBOR" ELEV_UNITS="METERS"
EXPORT_RASTER FILENAME="{2}"\\
TYPE=PNG GEN_WORLD_FILE=YES GEN_PRJ_FILE=YES
UNLOAD_ALL'''.format(prj,copy_file, mergedpngfile)

                    f = open(gmsfile, 'w')
                    f.write(gms)  
                    f.close()    

                    rungmsfiles(gmpath, gmsfile)

            else:
                print('No merged DEM file to copy for AOI : {0}\n\n'.format(aoiname))    


    if makeMKP == True:
        print('Starting MKP Process ')
        mkpdir_work = os.path.join(workingdir, 'MKP_{0}m'.format(vt)).replace('\\', '/')
        mkpdir_dest = os.path.join(outputdir,'MKP_{0}m'.format(vt)).replace('\\','/')
        prodclippeddir = AtlassGen.makedir(os.path.join(mkpdir_work, 'clipped')).replace('\\','/')
        prodclippeddir_dest = AtlassGen.makedir(os.path.join(mkpdir_dest, 'clipped')).replace('\\','/')

        make_mkp = {}
        make_mkp_results = []


        for tile in tl_out: 
            xmin = tile.xmin
            ymin = tile.ymin
            xmax = tile.xmax
            ymax = tile.ymax
            tilename = tile.name
            tilesize = int(tile.xmax - tile.xmin)

            make_mkp[tilename] = AtlassTask(tilename,makeMKPperTile, tilename,xmin,ymin,xmax,ymax,tilesize, inputfolder,mkpdir_dest, mkpdir_work, workingdir, gndclasses,vt, hz, buffer,tl_in, filetype,aoifiles,makeEMB)
                                           #tilename,xmin,ymin,tilesize, inputfolder,mkp_output, mkp_working, main_workingdir, gndclasses,vt, hz, buffer,tl_in, filetype,aois,makeEMB
        
        print(len(make_mkp))
      
        make_mkp_results=p.map(AtlassTaskRunner.taskmanager,make_mkp.values())



        
        for aoi in aoifiles:

            path, aoiname, ext = AtlassGen.FILESPEC(aoi)
            print('Merging MKP files for AOI : {0}\n\n'.format(aoiname))

            aoidir_dest = AtlassGen.makedir(os.path.join(prodclippeddir_dest,aoiname)).replace('\\','/')
            mergeddir_dest = AtlassGen.makedir(os.path.join(aoidir_dest, 'merged')).replace('\\','/')
            mergedlasfile = os.path.join(mergeddir_dest,"{0}.laz".format(aoiname)).replace('\\','/')
            mergedtxtfile = os.path.join(mergeddir_dest,"{0}.txt".format(aoiname)).replace('\\','/')
        
            print(aoidir_dest)
            merge_product_mkp(aoidir_dest, mergedlasfile, mergedtxtfile,makeTXT)

            if os.path.exists(mergedlasfile):
                print('Merged MKP file created for AOI : {0}\n'.format(aoiname))


    


    buffdir = os.path.join(workingdir, 'buffered').replace('\\','/')
    shutil.rmtree(buffdir)
 
    return()
    
if __name__ == "__main__":
    main(sys.argv[1:]) 

