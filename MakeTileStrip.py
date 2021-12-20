#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import shutil
import subprocess
import os
import random
import argparse
from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
import time
from collections import defaultdict 
from collections import OrderedDict 
from gooey import Gooey, GooeyParser
from geojson import Point, Feature, FeatureCollection, Polygon,dump
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
sys.path.append('{0}/lib/shapefile_original'.format(sys.path[0]).replace('\\','/'))
import shapefile_original
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

@Gooey(program_name="Tile Strip", use_legacy_titles=True, required_cols=2, default_size=(950, 700),monospace_display=False)
def param_parser():
    parser=GooeyParser(description="Tile Strip")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    main_parser = sub_pars.add_parser('Tilling', help='Tilling tool')
    main_parser.add_argument("input_folder", metavar="Input Directory", widget="DirChooser", help="Select input las/laz files", default='')
    main_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.las')
    main_parser.add_argument("tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000','5000','10000','20000'], default='500')
    main_parser.add_argument("datum", metavar="Datum",choices=['AGD84_AMG','AGD66_AMG','GDA94_MGA','GDA2020_MGA'], default='GDA94_MGA',help="NOTE: shifting function will not work for GDA2020")
    main_parser.add_argument("zone", metavar="UTM Zone", choices=['49','50','51','52','53','54','55','56'])
    main_parser.add_argument("-makeVLR", metavar="Create VLR for header",action='store_true', default=False)
    main_parser.add_argument("-VLRlocation",metavar="Output Directory for VLR",widget="DirChooser", help="Please select the Correct project from \\10.10.10.142\projects\Projects")
    shift_group = main_parser.add_argument_group("Shift values", "* Keep blank if shifting is NOT required", gooey_options={'show_border': True,'columns': 3})
    shift_group.add_argument("--dx",  metavar="x shift", type=float, default=0.00)
    shift_group.add_argument("--dy",  metavar="y shift", type=float, default=0.00)
    shift_group.add_argument("--dz",  metavar="z shift", type=float, default=0.00)
    main_parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=4)
    main_parser.add_argument("file_type",metavar="Output File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    main_parser.add_argument("-gen_block",metavar="Generate Blocks", help="Divide to blocks",action='store_true', default=False)
    main_parser.add_argument("-block_size",metavar="Block size", help="Block size", type = int ,default=10000)
    vlr_gen_parser = sub_pars.add_parser('vlr_gen', help='Generate VLR')
    vlr_gen_parser.add_argument("inputfile", metavar="LAS/Z file", widget="FileChooser", help="File with Correct Laz header", default='')
    vlr_gen_parser.add_argument("VLRlocation",metavar="Output Directory for VLR",widget="DirChooser", help="Please select the Correct project from \\10.10.10.142\projects\Projects")
    vlr_apply_parser = sub_pars.add_parser('vlr_apply', help='Apply VLR')
    vlr_apply_parser.add_argument("inputfolder", metavar="Input Directory", widget="DirChooser", help="Directory with the inorrect Laz header files", default='')
    vlr_apply_parser.add_argument("outputfolder", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    vlr_apply_parser.add_argument("filetype",metavar="Output File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    vlr_apply_parser.add_argument("VLRFile",metavar="Correct VLR File",widget="FileChooser", help="Please select the Correct VLR file")
    vlr_apply_parser.add_argument("cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)
    args = parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


def TileStrip(input, outputpath, tilesize,filetype):    
    log = ''

    try:
        laxfile = input.replace('laz', 'lax')
        
        if not os.path.exists(laxfile):

            subprocessargs=['C:/LAStools/bin/lasindex.exe','-i',input] 
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

  
        subprocessargs=['C:/LAStools/bin/lastile.exe','-i',input,'-o{0}'.format(filetype),'-odir',outputpath,'-tile_size',tilesize] 
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\n TileStrip {0} \n Exception {1}".format(input, e)
        return(False,None, log)
    
    finally:
        outputfiles = glob.glob(outputpath+"\\*."+filetype)
        print('\nTiling completed for {0}, generated {1}'.format(input, len(outputfiles)))
        log = '\nTiling completed for {0}, generated {1}'.format(input, len(outputfiles))
        return (True, outputfiles, log)

 
def MergeTiles(input, output, filetype):    
    log = ''

    if isinstance(input, str):
        input = [input]
    

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+input+['-o{0}'.format(filetype),'-o',output,'-merged'] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\n Merging {0} \n Exception {1}".format(output, e)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            for infile in input:
                os.remove(infile)
            log = '\nMerging completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nMerging {} Failed'.format(output)
            return (False, None, log)


  
def shiftlas(input, output, filetype, dx, dy, dz, epsg):

    log = ''

    try:
        #Las2las -i *.laz -olaz -odir xyz_adjusted -translate_xyz 1.50 2.80 0.00
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',input,'-o{0}'.format(filetype),'-o',output,'-translate_xyz', dx, dy, dz ] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nShifting {0} \n Exception {1}".format(input, e)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nShifting completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nShifting {} Failed'.format(output)
            return (False, None, log)

def movefiles(input, output):

    try:
        shutil.move(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            log = "Moving file {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Moving file {0} Failed".format(input)
            return (False,output, log)

def MakeVLR(lazfile, outputdir):
    
  
    log = ''

    os.chdir(outputdir)
    dir_path = os.getcwd()

    vlr = os.path.join(outputdir,'vlrs.vlr')
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-save_vlrs', '-nil'] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

  
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nMaking VLR Failed at exception :{0}".format(e)
        return(False,None, log)

    finally:
        if os.path.isfile(vlr):
            log = '\nVLR created Successfully : {0}'.format(vlr)
            return (True, vlr, log)
        else:
            log ='\nVLR creation Failed'
            return (False, None, log)

def CorrectVLR(lazfile,inputdir,vlrdir,filetype):
    os.chdir(inputdir)
    log = ''
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-odir',vlrdir,'-load_vlrs' ,'-o{0}'.format(filetype)] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

        log = 'Success'
        return(True,lazfile, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nFixing header failed at exception for :{0}".format(e)
        return(False,None, log)





#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()

    if args.command == "Tilling":
        tilesize=int(args.tile_size)
        filetype=args.file_type
        inputfolder=args.input_folder
        datum = args.datum
        zone = int(args.zone)
        dx = float(args.dx)
        dy = float(args.dy)
        dz = float(args.dz)
        shift = False
        gen_block = args.gen_block
        block_size = int(args.block_size)
        genVLR = args.makeVLR
        vlrpath = args.VLRlocation
        
        files = []
        filepattern = args.filepattern.split(';')
        cores=int(args.cores)
        outlasdir=args.output_dir
        epsg = 0

        if datum == "GDA94_MGA":
            epsg = 28300 + zone
        elif datum == "AGD84_AMG":
            epsg = 20300 + zone
        elif datum == "AGD66_AMG":
            epsg = 20200 + zone
        elif datum == "GDA2020_MGA":
            epsg = 7800 + zone
        else:
            print('Unable to find the EPSG for the given datum')
            return()

        print('EPSG used : {0}'.format(epsg))
        

        dt = strftime("%y%m%d_%H%M")
        maindir = AtlassGen.makedir(os.path.join(outlasdir, '{0}_{1}-{2}_{3}m_tiles'.format(dt, datum,zone,tilesize))).replace('\\','/')
        tldir = AtlassGen.makedir(os.path.join(maindir, 'tilelayout')).replace('\\','/')

        if len(filepattern) >=2:
            print('Number of patterns found : {0}'.format(len(filepattern)))
        for pattern in filepattern:
            pattern = pattern.strip()
            print ('Selecting files with pattern {0}'.format(pattern))
            filelist = glob.glob(inputfolder+"\\"+pattern)
            for file in filelist:
                files.append(file)
        print('Number of Files founds : {0} '.format(len(files)))



        shpfile = os.path.join(tldir, "tile_layout_shapefile_original.shp")
        w = shapefile_original.Writer(shapefile_original.POLYGON)
        w.autoBalance = 1
        w.field('TILE_NAME','C','255')
        w.field('XMIN','N',12,3)
        w.field('YMIN','N',12,3)
        w.field('XMAX','N',12,3)
        w.field('YMAX','N',12,3)
        w.field('TILENUM','C','16')



        prjfile = os.path.join(tldir, "tile_layout.prj")

            
        f = open(prjfile,"w")

                    
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
        
        if dx==0.0 and dy==0.0 and dz==0.0:
            shift = False
        
        else:
            shift = True
            xzy_string = ''
            if not dx==0:
                xzy_string = xzy_string + 'x'
            if not dy==0:
                xzy_string = xzy_string + 'y'
            if not dz==0:
                xzy_string = xzy_string + 'z'


        print('Shifting required : {0}'.format(shift))
        logw = 'Shift values used : \ndx={0}\ndy={1}\ndz={2}'.format(dx, dy, dz)
        print(logw)


        if shift:

            adjusteddir = AtlassGen.makedir(os.path.join(maindir, '{0}_adjusted_input'.format(xzy_string))).replace('\\','/')
            xyz_file = os.path.join(adjusteddir, 'xyz_adjustment.txt').replace('\\','/')
            fr= open(xyz_file,"w+")
            fr.write('dx={0} \ndy={1} \ndz={2}'.format(dx, dy, dz))
            fr.close()
        
        workingdir =  maindir
        


        logpath = os.path.join(maindir,'log_TileStrip.txt').replace('\\','/')
        log = open(logpath, 'w')
        log.write(logw)

        TILE_TASKS={}
        SHIFT_TASKS={}
        folders = []
        for file in files:
        
            path, filename, ext = AtlassGen.FILESPEC(file)
            folders.append(filename)
            if shift:
                #files
                input = file
                output = os.path.join(adjusteddir, '{0}.{1}'.format(filename, filetype)).replace('\\','/')
                SHIFT_TASKS[filename]= AtlassTask(filename,shiftlas,input,output, filetype, dx, dy, dz, epsg)
            else:
                #files
                input = file
                outputpath=AtlassGen.makedir(os.path.join(workingdir,filename)).replace('\\','/')
                TILE_TASKS[filename] = AtlassTask(filename,TileStrip,input,outputpath,tilesize,filetype)

        if shift:
            print('\n\nShifting Started')
            log.write('\n\nShifting Started')

            p=Pool(processes=cores)      
            SHIFT_RESULTS=p.map(AtlassTaskRunner.taskmanager,SHIFT_TASKS.values()) 

            if dx==0 and dy==0 and dz==0:
                print('\n\nZ shift completed. \nNo retiling as x=0 and y=0')

                log.write('\n\nZ shift completed. \nNo retiling as x=0 and y=0')
                

            else:
                for result in SHIFT_RESULTS:
                    log.write(result.log)
                    if result.success:
                        filename = result.name      
                        #files
                        input = result.result
                        print(input)
                        outputpath=AtlassGen.makedir(os.path.join(workingdir,filename)).replace('\\','/')
                        TILE_TASKS[filename] = AtlassTask(filename,TileStrip,input,outputpath,tilesize,filetype)
                
                print('\n\nTiling started')
                p=Pool(processes=cores)      
                TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())
                resultsdic=defaultdict(list)

                #merge tiles with the same tile name
                MERGE_TASKS={}

                print('\n\nMerging started')
                for result in TILE_RESULTS:
                    log.write(result.log)  
                    if result.success:
                        for file in result.result:
                            path,filename,ext = AtlassGen.FILESPEC(file)
                            resultsdic[filename].append(file)


                for key, value in list(resultsdic.items()): 
                    input = resultsdic[key]
                    output = os.path.join(workingdir, '{0}.{1}'.format(key,filetype)).replace('\\','/')
                    MERGE_TASKS[key]= AtlassTask(key, MergeTiles, input, output, filetype)
                
                MERGE_RESULTS=p.map(AtlassTaskRunner.taskmanager,MERGE_TASKS.values())
            
                #make a tile layout index
                for result in MERGE_RESULTS:
                    log.write(result.log)  

                for folder in folders:
    
                    rmfolder = (os.path.join(workingdir, folder).replace('\\','/'))
                    if [f for f in os.listdir(rmfolder) if not f.startswith('.')] == []:
                        try:
                            os.rmdir(rmfolder)
                        except:
                            print("could not delete {0} ".format(rmfolder))
                    else: 
                        print ('Files exist in {0} , Merging Not Successfule for {1}'.format(rmfolder, result.name))
                        log.write('Files exist in {0} , Merging Not Successfule for {1}'.format(rmfolder, result.name))

        else:
            print('\n\nTiling started')
            log.write('\n\nTiling started')
            p=Pool(processes=cores)      
            TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())
            resultsdic=defaultdict(list)

            #merge tiles with the same tile name
            MERGE_TASKS={}

            print('\n\nMerging started')
            log.write('\n\nMerging started')

            for result in TILE_RESULTS:
                log.write(result.log)  
                if result.success:
                    for file in result.result:
                        path,filename,ext = AtlassGen.FILESPEC(file)
                        resultsdic[filename].append(file)


            for key, value in list(resultsdic.items()): 
                input = resultsdic[key]
                output = os.path.join(workingdir, '{0}.{1}'.format(key,filetype)).replace('\\','/')
                MERGE_TASKS[key]= AtlassTask(key, MergeTiles, input, output, filetype)
            
            MERGE_RESULTS=p.map(AtlassTaskRunner.taskmanager,MERGE_TASKS.values())
        
            #make a tile layout index
            for result in MERGE_RESULTS:
                log.write(result.log)  

            #Delete folders 
            for folder in folders:
    
                rmfolder = (os.path.join(workingdir, folder).replace('\\','/'))
                if [f for f in os.listdir(rmfolder) if not f.startswith('.')] == []:
                    try:
                        os.rmdir(rmfolder)
                    except:
                        print("could not delete {0} ".format(rmfolder))
                else: 
                    print ('Files exist in {0} , Merging Not Successfule for {1}'.format(rmfolder, result.name))
                    log.write('Files exist in {0} , Merging Not Successfule for {1}'.format(rmfolder, result.name))



        block_task={}
        features = []
        blocks = []


        if gen_block:
            print('\n\nBlocking started')
            block_path = os.path.join(workingdir,'{0}_block'.format(block_size)).replace('\\','/')
            files = glob.glob(workingdir+'/*.{0}'.format(filetype))
            for file in files:
                path, filename,ext = AtlassGen.FILESPEC(file)
                x_y = filename.split('_')
                xmin = int(x_y[0])
                xmax = xmin+tilesize
                ymin = int(x_y[1])
                ymax = ymin+tilesize

                block_x = math.floor(xmin/block_size)*block_size
                block_y = math.floor(ymin/block_size)*block_size
                blockname = '{0}_{1}'.format(block_x,block_y)
                block_folder = os.path.join(block_path,blockname).replace('\\','/')

                if blockname not in blocks:
                    blocks.append(blockname)

                boxcoords=AtlassGen.GETCOORDS([xmin,ymin],tilesize)
                poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])

                #adding records to json file
                features.append(Feature(geometry=poly, properties={"name": filename, "xmin": xmin, "ymin":ymin, "xmax":xmax, "ymax":ymax, "tilenum":filename,"modtime":"0000-00-00 00:00:00","{0}_block".format(block_size):blockname}))


                #adding records for shp file
                w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                w.record(TILE_NAME='{0}'.format(filename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='{0}_{1}'.format(int(boxcoords[0][0]),int(boxcoords[0][1])))
                

                #adding records to prj file
                f.write( '\nBlock {0}.{1}\n'.format(filename,ext))
                for i in boxcoords:
                    f.write(  ' {0} {1}\n'.format(i[0],i[1]))


                if not os.path.exists(block_folder):
                    AtlassGen.makedir(block_folder)

                input = file
                output = os.path.join(block_folder,'{0}.{1}'.format(filename,ext)) 
                print(output)
                #block_task[blockname] = AtlassTask(blockname, movefiles, input, output)
                movefiles(input, output)

            #Make overall Tilelayout for blocks
            features2 = []
            print(list(blocks))
            for block in blocks:
                blockname = block
                b_xmin,b_ymin = blockname.split('_')
                b_xmin = int(b_xmin)
                b_ymin = int(b_ymin)
                b_xmax = int(b_xmin) + block_size
                b_ymax = int(b_ymin) + block_size
                print(blockname,b_xmin,b_ymin,b_xmax,b_ymax)
                boxcoords=AtlassGen.GETCOORDS([b_xmin,b_ymin],block_size)
                poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                features2.append(Feature(geometry=poly, properties={"name": blockname, "xmin": b_xmin, "ymin":b_ymin, "xmax":b_xmax, "ymax":b_ymax, "tilenum":blockname}))

            block_jsonfile = os.path.join(workingdir, "Tilelayout_{0}_block.json".format(block_size))
            feature_collection2 = FeatureCollection(features2)
            with open(block_jsonfile, 'w') as fs:
                dump(feature_collection2, fs)

        else:
            print(workingdir)
            #if dz is not  zero there will be a shiting but not a retiling hence the working directory should be the same as your shift directory
            if shift and not dz==0:
                tiledir=workingdir
            else:
                tiledir= workingdir
            print(tiledir)

            files = glob.glob(tiledir+'/*.{0}'.format(filetype))
            for file in files:
                path, filename,ext = AtlassGen.FILESPEC(file)
                x_y = filename.split('_')
                xmin = int(x_y[0])
                xmax = xmin+tilesize
                ymin = int(x_y[1])
                ymax = ymin+tilesize
                boxcoords=AtlassGen.GETCOORDS([xmin,ymin],tilesize)
                poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])

                #adding records to json file
                features.append(Feature(geometry=poly, properties={"name": filename, "xmin": xmin, "ymin":ymin, "xmax":xmax, "ymax":ymax, "tilenum":filename,"modtime":"0000-00-00 00:00:00"}))


                #adding records for shp file
                w.line(parts=[[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])
                w.record(TILE_NAME='{0}'.format(filename), XMIN='{0}'.format(boxcoords[0][0]),YMIN='{0}'.format(boxcoords[0][1]),XMAX='{0}'.format(boxcoords[2][0]),YMAX='{0}'.format(boxcoords[2][1]),TILENUM='{0}_{1}'.format(int(boxcoords[0][0]),int(boxcoords[0][1])))
                
                #adding records to prj file
                f.write( '\nBlock {0}.{1}\n'.format(filename,ext))
                for i in boxcoords:
                    f.write(  ' {0} {1}\n'.format(i[0],i[1]))

        #Creating Json file
        print('No of tiles in tilelayout : {0}'.format(len(features)))

        print("Making geojson file : Started \n")

        feature_collection = FeatureCollection(features)
        jsonfile = 'TileLayout'
        jsonfile = os.path.join(tldir,'{0}_{1}.json'.format(jsonfile,len(features)))

        with open(jsonfile, 'w') as fj:
            dump(feature_collection, fj)

        print("Making geojson file : Completed\n File : {0}\n".format(jsonfile))

        #Creating shp file
        print("Making shp file : Started\n")
        w.save(shpfile)           
        print("Making shp file : Completed\n File : {0}\n".format(shpfile))

        #Creating prj file
        f.close
        print("Making prj file : Completed\n")

        if genVLR:
            
            vlrdir = AtlassGen.makedir(os.path.join(vlrpath,'VLR_{0}'.format(dt)).replace('\\','/'))
            result = MakeVLR(files, tldir)
            print(result)

            #Copying file to projects folder.
            sourcefile = os.path.join(tldir,'vlrs.vlr').replace('\\','/')
            destinationfile = os.path.join(vlrdir,'vlrs.vlr').replace('\\','/')
            shutil.copyfile(sourcefile, destinationfile)
            if os.path.exists(destinationfile):
                print("VLR file copied to {0}".format(destinationfile))

    if args.command == "vlr_gen":
        inputfile = args.inputfile 
        vlrpath = args.VLRlocation

        dt = strftime("%y%m%d_%H%M")
        vlrdir = AtlassGen.makedir(os.path.join(vlrpath,'VLR_{0}'.format(dt)).replace('\\','/'))
        print("generating VLR")
        result = MakeVLR(inputfile, vlrdir)
        sourcefile = os.path.join(vlrdir,'vlrs.vlr').replace('\\','/')
        
        if os.path.exists(sourcefile):
            print("File located at : {0}".format(sourcefile))
        
        else:
            print("Could not generate VLR \n{0}".format(result))


    if args.command == "vlr_apply":
        inputdir = args.inputfolder
        outputdir = args.outputfolder
        filetype = args.filetype
        cores = args.cores
        files = AtlassGen.FILELIST(["*.{0}".format(filetype)], inputdir)
        vlrfile = args.VLRFile

        dt = strftime("%y%m%d_%H%M")

        vlrdir = AtlassGen.makedir(os.path.join(outputdir,'Fixed_Header_{0}'.format(dt)).replace('\\','/'))
        #Copying file to projects folder.
        destinationfile = os.path.join(inputdir,'vlrs.vlr').replace('\\','/')

        if not os.path.isfile(destinationfile):
            shutil.copyfile(vlrfile, destinationfile)

        TILE_TASKS = {}
        TILE_RESULTS=[]
        for ifile in files:
            path, filename,ext = AtlassGen.FILESPEC(ifile)
            
            TILE_TASKS[filename] = AtlassTask(filename,CorrectVLR,ifile,inputdir,vlrdir,filetype)



        p=Pool(processes=cores)      
        TILE_RESULTS=p.map(AtlassTaskRunner.taskmanager,TILE_TASKS.values())

    return

if __name__ == "__main__":
    main()         

