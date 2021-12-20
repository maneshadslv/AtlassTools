#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
from __future__ import print_function
import itertools
import time
import random
import sys
import math
import statistics
import shutil
import subprocess
import os, glob
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from gooey import Gooey, GooeyParser
import time
import datetime
from time import strftime
from multiprocessing import Pool,freeze_support
import pandas as pd
sys.path.append('C:/Program Files/GTK2-Runtime Win64/bin/'.replace('\\', '/'))
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader

from multiprocessing import Process, Queue, current_process, freeze_support
from datetime import datetime, timedelta
from collections import defaultdict 
from collections import OrderedDict 

sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\', '/'))
from Atlass_beta1 import *
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
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Generate GCP report", advanced=True, default_size=(1100,1000), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Generate GCP report")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("-genreport", metavar="Generate Only Report", help=" **You can select this if you allready have the 'CGP_<tilename>_result.txt' files generated\n  Please select the appropriate 'method used' and the 'GCP Control File Has index ?' option\n used to generate the files", action="store_true")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz', 'txt'], default='laz') 
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    main_parser.add_argument("tilelayoutfile", metavar="TileLayout file", widget="FileChooser", help="Select TileLayout file (.json)", default='')
    main_parser.add_argument("--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("control", metavar="Control file", widget="FileChooser", help="Select the GCP height control file")

    main_parser.add_argument("projname", metavar="Project Name", default='')
    main_parser.add_argument('areaname', metavar="Area Name", default='')
    main_parser.add_argument('deltax', metavar="x shift", default=0, type=float)
    main_parser.add_argument('deltay', metavar="y shift", default=0, type=float)
    main_parser.add_argument("armse", metavar="Standard Deviation for filtering", help="The report status will be Not Accepted if value greater than the value provided", type=float)

    technique = main_parser.add_mutually_exclusive_group("Select method to use")
    technique.add_argument('-tin', '--tinmethod', dest='PointTin',
                           action="store_true", help="Use Point to Tin method (Must have ground classfication done before running this method)")
    technique.add_argument('-p', '--pointstat', dest='PatchStats',
                           action="store_true", help="Use Statistical/average elevation Method")
    main_parser.add_argument("--radius", metavar="Radius for Surface avarage", default=2.0, type=float)
    main_parser.add_argument("--hasindex", metavar="GCP Control file Has Index?", action= "store_true")
    main_parser.add_argument("--gndclass", metavar="Ground Classes", default='2 8')
    main_parser.add_argument("--cores", metavar="General", help="Number of cores to be used for tiling process", type=int, default=4)
    return main_parser.parse_args()
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def GenSurfaceStats(tilelayout,buffer,laspath, outpath, filetype,tile,points,radius,pointstatdir,user_std):
    log = ''
    tile = tilelayout.gettile(tile)
    outfile=os.path.join(outpath,'CGP_{0}_result.txt'.format(tile.name)).replace('\\','/')
    outsqfile=os.path.join(pointstatdir,'CGP_{0}_sq.laz'.format(tile.name)).replace('\\','/')
    neighbourlasfiles = []
    tiledir = AtlassGen.makedir(os.path.join(pointstatdir, tile.name))
    outputfiles = []
    otf = open(outfile, 'w')
    print(tile.name)

    try:
        if not buffer ==0:  
            try:
                neighbours = tile.getneighbours(buffer)
                print(neighbours)
            except:
                print("tile: {0} does not exist in Tilelayout file".format(tile.name))

            for neighbour in neighbours:
                neighbour = os.path.join(laspath,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')
                #print("Indexing Started")
                if os.path.isfile(neighbour):
                    neighbourlasfiles.append(neighbour) 
                    subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', neighbour, '-cores', 5]
                    subprocessargs=list(map(str,subprocessargs)) 
                    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            
                #print("Indexing finished")
        else:
            neighbourlasfiles = [os.path.join(laspath, '{0}.{1}'.format(tile.name, filetype))]
                
        surfacepatch ={}


        for point in points:
            index,x,y,z=point
            pxmin = float(float(x)-float(radius))
            pymin = float(float(y)-float(radius))
            pxmax = float(float(x)+float(radius))
            pymax = float(float(y)+float(radius))

            start = time.process_time()

            print('\n\nWorking with point -----> {0}'.format(index))
            outtxt = os.path.join(tiledir, 'GCP_{0}.txt'.format(index))
            outputfiles.append(outtxt)
            print('generating patch')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', '-use_lax'] + neighbourlasfiles +['-inside', pxmin,pymin,pxmax,pymax, '-o',  outsqfile,'-merged','-last_only', '-olaz']
            subprocessargs=list(map(str,subprocessargs))  
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', outsqfile, '-inside_circle', x,y,radius, '-o',  outtxt, '-otxt', '-rescale', 0.001, 0.001, 0.001,'-oparse', 'xyz']
            subprocessargs=list(map(str,subprocessargs))  
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)


            #lines = [line.rstrip('\n')for line in open(outtxt)]
            
            i =0
            print('reading patch file')

            surfacepatch = SurfacePatch()
            f = open(outtxt)
            for line in f.readlines():

                line = line.rstrip("\n")
                ln = line.split(' ')
                i +=1
                if ln[0] == '':
                    print('No Surface points found in file {0}'.format(outtxt))
                else:
                    #print(i,ln[0],ln[1],ln[2])
                    dz = round(float(z)- float(ln[2]),3)
                    if ( -1.0 < dz < 1.0 ):
                        surfacepatch.addSurfacePoint(i,float(ln[0]),float(ln[1]),float(ln[2]),dz, True)
                    else:
                        surfacepatch.addSurfacePoint(i,float(ln[0]),float(ln[1]),float(ln[2]),dz, False)
            
            
            #Calculate initial statistics
            if len(surfacepatch) >=2:
                average1 = surfacepatch.calc_average('z')
                print('Initial average : {0}'.format(average1))
                stddev1= surfacepatch.calc_stdev('z')
                print('Initial Std Deviation : {0}'.format(stddev1))
                
                filter_val = min(stddev1, 0.05)
                print('Filtering patch data by 3*{0} ==>>>> '.format(filter_val))

                accepted, rejected = surfacepatch.filter_data(filter_val*3, average1)
                total = accepted+rejected
                print('Total of points in patch {0}'.format(total))
                print('No of accepted points in patch : {0}'.format(accepted))
                print('No of rejected points in patch : {0}'.format(rejected))

                #Point List statistics
                
                if not rejected ==0:
                    fav = float(surfacepatch.finalaverage)
                    fstddev = surfacepatch.finalstddev

                else:
                    fav = average1
                    fstddev = stddev1

                if fstddev <= 0.1:
                    diff = round((fav-z), 4)
                    print(fav, fstddev)
                    wrl = '{0} {1} {2} {3} {4} {5} {6}\n'.format(str(diff),fav,x,y,z,index, fstddev)
                    otf.writelines(wrl)


                else:
                    print("Rejecting patch {0} as final std dev is greater than 0.05".format(index))
            else:
                print("Not enough patch points to calculate average")

            end = time.process_time()
            timetaken = end -start   
            print('Finished with point -----> {0}\ntime taken - {1}\n\n'.format(index, timetaken))
    
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        print('CGP output Failed for {0} at Subprocess - {1}.'.format(tile.name, e))
        log = 'CGP output Failed for {0} at Subprocess - {1}.'.format(tile.name, e)
        return(False, None, log)

    finally:
       
        otf.close()
        if os.path.isfile(outfile):
            log = 'Per Tile GCP Statistics Success for: {0}.'.format(tile.name)
            return(True, outfile, log)

        else:
            log = 'Per Tile CGP Statistics Failed for: {0}.'.format(tile.name)
            print(log)
            return(False, None, log)
    
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

def PointTin(tilelayout,buffer,laspath, outpath, filetype,tile,points,gndclasses):
    log = ''
    tile = tilelayout.gettile(tile)
    outfile=os.path.join(outpath,'CGP_{0}_result.txt'.format(tile.name)).replace('\\','/')
    gcpfile=os.path.join(outpath,'CGP_{0}.txt'.format(tile.name)).replace('\\','/')
    neighbourlasfiles = []
 
    try:
        if not buffer == 0:    
            try:
                neighbours = tile.getneighbours(buffer)
    
            except:
                print("tile: {0} does not exist in Tilelayout file".format(tile.name))

            for neighbour in neighbours:
                neighbour = os.path.join(laspath,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

                if os.path.isfile(neighbour):
                    neighbourlasfiles.append(neighbour) 
        else:
            neighbourlasfiles = [os.path.join(laspath, '{0}.{1}'.format(tile.name, filetype))]

        f = open(gcpfile,'w')
        for point in points:
            index,x,y,z=point
            f.write('{0} {1} {2} {3}\n'.format(x,y,z, index))
        f.close()
        classes=['-keep_class']+gndclasses
        '''
        check optional input classify ground  == True
            lasground_new -i neighbourlasfiles -o <name>_gnd.laz -step 10 -spike 0.5 -down_spike 1.0 -bulge 2.5 -offset 0.1 -fine
            lascontrol

        else
        '''
        subprocessargs=['C:/LAStools/bin/lascontrol.exe','-i'] + neighbourlasfiles +['-merged','-cp', gcpfile ,'-cp_out',outfile] + classes
        subprocessargs=list(map(str,subprocessargs))  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        print('CGP output Failed for {0} at Subprocess.'.format(tile.name))
        log = 'CGP output Failed for {0} at Subprocess.'.format(tile.name)
        return(False, None, log)

    finally:
        if os.path.isfile(outfile):
            
            log = 'CGP output Success for: {0}.'.format(tile.name)
            return(True, outfile, log)
        else:
            log = 'CGP output Failed for: {0}.'.format(tile.name)
            return(False, None, log)



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():


    freeze_support() 
    args = param_parser()

    inputfolder = args.inputfolder
    outputfolder = args.outputpath
    cores=args.cores
    deltax = args.deltax
    deltay = args.deltay
    user_std = args.armse
    dt = strftime("%y%m%d_%H%M")
    outputpath = AtlassGen.makedir(os.path.join(outputfolder, '{0}_GCP_Report_{2}_{3}_stdDev_{1}'.format(dt,user_std,args.projname, args.areaname)))
    pointstat = args.PatchStats
    control=args.control
    genreport = args.genreport

    hasindex = args.hasindex
    radius = args.radius
    if radius==None or radius ==0:
        radius = 2
    if not genreport:

        filetype=args.filetype

        filepattern = args.filepattern
        print("Reading {0} files \n".format(filetype))

        filepattern = args.filepattern.split(';')

        lasfiles=AtlassGen.FILELIST(filepattern, inputfolder)
        
        if pointstat:

            pointstatdir = AtlassGen.makedir(os.path.join(outputpath, 'Point_Stats'))

        if len(lasfiles) ==0:
            print("Exiting as no las files found, please check file type & filter pattern")
            exit()
        
        tilelayoutfile=args.tilelayoutfile
        buffer=args.buffer

        tilelayout = AtlassTileLayout()
        tilelayout.fromjson(tilelayoutfile)
        gndclasses=args.gndclass.split()

    logpath = os.path.join(outputpath,'log_report.txt').replace('\\','/')
    log = open(logpath, 'w')

    lines = [line.rstrip('\n')for line in open(control)]


    if not genreport:

        
        # Read the GCP files to get the GCP points
        #######################################################################################################################
        INDEX_TASK={}
        GCPTile={}
        results = []
        originalpoints=OrderedDict()
        PATCH_GEN_TASK = {}
        index=0
        for line in lines:

            line=line.split()

            if hasindex:
                if len(line) <=4:

                    index=str(line[0])
                    x,y,z=float(line[1]),float(line[2]),float(line[3])
                    originalpoints[index]=[round(x,3),round(y,3),round(z,3)]
                else:
                    print("GCP file not accepted, check if index has spaces")
                    exit()
            else:
                index+=1
                x,y,z=float(line[0]),float(line[1]),float(line[2])
                originalpoints[str(index)]=[round(x,3),round(y,3),round(z,3)]


            for file in lasfiles:
                path, filename, ext = AtlassGen.FILESPEC(file)
           		#print(filename)
                tile = tilelayout.gettile(filename)
                if tile==None:
                    pass
                elif tile.xmin<x<tile.xmax and  tile.ymin<y<tile.ymax:
                    if tile.name in GCPTile.keys():
                        GCPTile[tile.name].append([index,x,y,z])
                    else:
                        GCPTile[tile.name]=[[index,x,y,z]]



        print('GCP Points found in {0} files'.format(len(GCPTile)))
        
        #Classify and Generate the results files for tiles that has GCP
        ##############################################################################################################################
        GEN_CONTROL_TASKS={}      
        SURFCE_AVG_TASK={}

        for tile in GCPTile.keys():

            points=GCPTile[tile]

            if pointstat:
                
                SURFCE_AVG_TASK[tile] =  AtlassTask(tile, GenSurfaceStats,tilelayout,buffer,inputfolder,outputpath,filetype,tile,points,radius,pointstatdir,user_std)
                #GenSurfaceStats(tilelayout,buffer,inputfolder,outputpath,filetype,tile,points,radius,pointstatdir,user_std)  
            else:
                GEN_CONTROL_TASKS[tile]= AtlassTask(tile, PointTin,tilelayout,buffer,inputfolder,outputpath,filetype,tile,points,gndclasses)
                #CGPCheck(tilelayout,buffer,outputpath,filetype,tile,points,gndclasses)
        
        if pointstat:
            print("Starting Point Surface Average method")
            p=Pool(processes=cores)  
            results=p.map(AtlassTaskRunner.taskmanager,SURFCE_AVG_TASK.values())

        else:
            print("Starting Point to Tin method")
            p=Pool(processes=cores)      
            results=p.map(AtlassTaskRunner.taskmanager,GEN_CONTROL_TASKS.values())
        
        pointlist = PointList()
        
        if len(results) ==0:
            print("Exiting as no data caluclated")
            exit()

        for result in results:
            #log.write(result.log)
            f = open(result.result)

            for line in f.readlines():
                line = line.rstrip("\n")
                z = line.split(' ')
                if z[0] == '-' or z[1] == '-':
                    print('Lascontrol - None of the points cover any control point. all filtered or too far.')
                else:
                    diff = round(float(z[0]), 3)
                    if pointstat:
                        pointlist.addPoint(z[5],z[2],z[3],z[1],z[4],diff,z[6])
                    else:
                        pointlist.addPoint(z[5],z[2],z[3],z[1],z[4],diff,0.0)
            f.close()

    else:
        index=0
        originalpoints=OrderedDict()
        for line in lines:
            line=line.split()

            if hasindex:
                if len(line) <=4:

                    index=str(line[0])
                    x,y,z=float(line[1]),float(line[2]),float(line[3])
                    originalpoints[index]=[round(x,3),round(y,3),round(z,3)]
                else:
                    print("GCP file not accepted, check if index has spaces")
                    exit()
            else:
                index+=1
                x,y,z=float(line[0]),float(line[1]),float(line[2])
                originalpoints[str(index)]=[round(x,3),round(y,3),round(z,3)]

        result_files = glob.glob(inputfolder+'/*_result.txt')
        pointlist = PointList()

        for file in result_files:
            f = open(file)
            for line in f.readlines():
                line = line.rstrip("\n")
                z = line.split(' ')
                if z[0] == '-' or z[1] == '-':
                    print('Lascontrol - None of the points cover any control point. all filtered or too far.')
                else:
                    diff = round(float(z[0]), 3)
                    if len(z) ==7:
                        patchstddev = z[6]
                    else:
                        patchstddev = 0.0
                    pointlist.addPoint(z[5],z[2],z[3],z[1],z[4],diff,patchstddev)

            f.close()
     
    # Generate the statistical report
    ##############################################################################################################################
    
    report_hist = os.path.join(outputpath,'points_dist.png').replace('\\', '/')
    report_pdf = os.path.join(outputpath,'Statistical_Report_3Sigma_{0}_{1}.pdf'.format(args.projname, args.areaname)).replace('\\', '/')
    
    total_gcp_points = len(lines)
    print('\nNo of GCP points in control: {0}'.format(total_gcp_points))

    print('\nNo of GCP points used for Analysis : {0}'.format(len(pointlist.points)))
    #Calculate initial statistics
    average1 = pointlist.calc_average('dz')
    stddev1 = pointlist.calc_stdev('dz')
    print('\n\n-------------Initial Stats :--------------\n Average : {0} \n Standard Deviation : {1}'.format(average1, stddev1))
    print('\nUser input Standard Deviation : {0}'.format(user_std))
    # Filter data
    filter_val = min(stddev1, user_std)
    print('\n\nFiltering Data by 3*{0} ==>>>> '.format(filter_val))
    
    accepted, rejected = pointlist.filter_data(filter_val*3)
    total = accepted+rejected
    print('Total number of data sampled {0}'.format(total))
    print('No of accepted data : {0}'.format(accepted))
    print('No of rejected data : {0}'.format(rejected))

    #Point List statistics
    
    fav = pointlist.finalaverage
    fstddev = pointlist.finalstddev
    rmse = pointlist.rmse
    ci95 = pointlist.ci95

    if not (fav or fstddev or rmse or ci95):
        print('Some stats were not calculated')
        exit()
    
    
    shift = round((0-(pointlist.finalaverage)), 4)

    print('\n\n------------------Final Stats :--------------------\nAverage: {0} \nStandard Deviation: {1}\n RMSE : {2}\n CI95 : {3}\n Z shift : {4}'.format(fav, fstddev, rmse, ci95, shift))
    
    #generate  histogram
    dataset = []
    
    for key, point in pointlist.points.items():
        originalpoints[key].append('yes')         
        if point.accepted:
            #print(point.dzshifted)
            dataset.append(point.dzshifted)
    if len(dataset)==0:
        print('all points rejected')
    print('dataset:',len(dataset))
    print([min(dataset), max(dataset)])
    bins = 'auto'
    plt.xlim([min(dataset), max(dataset)])
    plt.hist(dataset, bins=bins, alpha=0.5,color = "#ed6363")
    plt.title('Histogram of height difference')
    plt.xlabel('Height differences after a shift of {0}m'.format(shift))
    plt.ylabel('count')
    plt.savefig(report_hist)
    
     
    #Generate data table
    data_all = []
    outside = 0
    data_txt = ''
    outside_txt = ''
    data_acp_txt = ''

    for key, gcp in originalpoints.items():

      
        if key in pointlist.points.keys():
            point=pointlist.points[key]
            found=True
        else:
            found=False
            outside+=1

        if pointstat:
            if not found:
                #did not return
                data_all.append({'index':key, 'x':originalpoints[key][0], 'y':originalpoints[key][1], 'lidarz':'None','dz':'None', 'controlz':originalpoints[key][2], 'patch stddev':'None', 'dz after shift':'Patch Rejected'})
                outside_txt = outside_txt + '{0} {1} {2} {3}\n'.format(key,originalpoints[key][0], originalpoints[key][1], originalpoints[key][2])
            else:
                data_all.append({'index':point.index, 'x':point.x, 'y':point.y, 'lidarz':point.lidarz,'dz':point.dz, 'controlz':point.controlz, 'patch stddev':point.patchstddev, 'dz after shift':point.dzshifted})
                data_acp_txt = data_acp_txt + '{0} {1} {2} {3} {4} {5}\n'.format(point.dz, point.lidarz, point.x, point.y, point.controlz, point.index)


            df = pd.DataFrame(data_all)
            #Order columns
            df = df[['index','x', 'y','controlz', 'lidarz', 'patch stddev','dz', 'dz after shift']]
            df.sort_values(by=['index'])
        
            
        else:
            if not found:
                #did not return
                data_all.append({'index':key, 'x':originalpoints[key][0], 'y':originalpoints[key][1], 'lidarz':'None','dz':'None', 'controlz':originalpoints[key][2], 'dz after shift':'Outside'})
                outside_txt = outside_txt + '{0} {1} {2} {3}\n'.format(key,originalpoints[key][0], originalpoints[key][1], originalpoints[key][2])
            else:
                data_all.append({'index':point.index, 'x':point.x, 'y':point.y, 'lidarz':point.lidarz,'dz':point.dz, 'controlz':point.controlz, 'dz after shift':point.dzshifted})
                data_acp_txt = data_acp_txt + '{0} {1} {2} {3} {4} {5}\n'.format(point.dz, point.lidarz, point.x, point.y, point.controlz, point.index)
            df = pd.DataFrame(data_all)

            #Order columns
            df = df[['index','x', 'y','controlz', 'lidarz','dz', 'dz after shift']]
            df.sort_values(by=['index'])


    #Write the results txt file for all the accepted points/patches
    
    txtfile = os.path.join(outputpath,'GCP_Result_ALL.txt').replace('\\','/')
    with open(txtfile, 'w') as txtf:
        txtf.write(data_acp_txt)

       
    outsidetxtfile = os.path.join(outputpath,'GCP_outside.txt').replace('\\','/')
    with open(outsidetxtfile, 'w') as outf:
        outf.write(outside_txt)

    pointlist.createOutputFiles(outputpath)


    gcp_outof_range = outside

    path, control_file, ext = AtlassGen.FILESPEC(control)
    control_file = '{0}.{1}'.format(control_file,ext)
    #Create PDF report
    points = total_gcp_points
    points_accept = accepted
    points_accept_perc = round((accepted/points*100), 1)
    points_rej = rejected
    points_rej_perc = round(((rejected)/points*100), 1)


    #Check Report Quality
    quality = ''
    note = ''
    if points_rej_perc<5:
        quality = 'Accepted'
        if rmse<3*user_std and rmse>-3*user_std:
            quality = 'Accepted'
            note = ''
        else:
            quality = 'Not Accepted'
            note = "The RMSE is more than the {0}".format(rmse)
    else:
        quality = 'Not Accepted'
        note = " (More than 5% of the points rejected)"

    if pointstat:
        outcome = 'Patches Rejected'
        method_head = "Statistical/average elevation"
        method = "This report was generated by comparing supplied ground control points (GCPs) to the average elevation of unclassified last/only return LiDAR points within a {0}m radius of each GCP point. Surfaces with vertical deviation of greater than 1.0m have been rejected in a first pass. After comparison, deviations of greater than 0.05m from the average vertical difference have been rejected from analysis. The shift values and statistics shown in this report are for preliminary validation of LiDAR point cloud, and assessment of supplied ground control only. A final report and final shift values will be calculated from classified LiDAR data once it is available.".format(radius)
        print('\nNo of Patches Rejected: {0}'.format(gcp_outof_range))
    else:
        outcome = 'Out of Range'
        method_head = "Point to Tin"
        method = "This report was generated by comparing supplied ground control points (GCPs) to a Triangulated Irregular Network (TIN) generated from LiDAR points classified as ground. Points with vertical Standard Deviation of greater than or less than {0}m from the Average Vertical Difference have been rejected from analysis. The shifts values and statistics shown in this report are suitable for adjusting the LiDAR point cloud. RMSE and CI95 values shown are calculated after average shifts were applied.".format(user_std)
        print('\nNo of GCPs out of range: {0}'.format(gcp_outof_range))
    
    gcp_outof_range_perc = round(gcp_outof_range/points*100,1)
    dt = strftime("%d/%m/%y")
    logo = 	"\\\\10.10.10.142\\projects\\PythonScripts\\icons\\logo.png"
    env = Environment(loader=FileSystemLoader("\\\\10.10.10.142\\projects\\PythonScripts\\templates"))
    template = env.get_template("template.html")
    template_vars = {"project" : args.projname,
                    "area" : args.areaname,
                    "points": points,
                    "points_accept": points_accept,
                    "points_accept_perc": points_accept_perc,
                    "points_rej": points_rej,
                    "points_rej_perc": points_rej_perc,
                    "points_outof_range": gcp_outof_range,
                    "points_outof_range_perc": gcp_outof_range_perc,
                    "report": report_hist,
                    "mean": pointlist.finalaverage,
                    "tsigma": pointlist.finalstddev,
                    "data": df.to_html(),
                    "deltax" : deltax,
                    "deltay" : deltay,
                    "deltaz" : shift,
                    "date" : dt,
                    "rmse" : rmse,
                    "ci95" : ci95,
                    "control_file" : control_file,
                    "logo" : logo,
                    "quality": quality,
                    "method": method,
                    "method_head": method_head,
                    "outcome" : outcome,
                    "note" : note}
    # Render our file and create the PDF using our css style file
    html_out = template.render(template_vars)
    stylesheet = os.path.join('\\\\10.10.10.142\\projects\\PythonScripts\\templates','style.css').replace('\\', '/')
    HTML(string=html_out).write_pdf(report_pdf, stylesheets=[stylesheet])

    print("Report Located in : {0}".format(report_pdf))
    print('Process complete')
        
    return
        
if __name__ == "__main__":
    main()            
