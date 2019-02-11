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
sys.path.append('C:/Program Files/GTK2-Runtime Win64/bin')
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

@Gooey(program_name="Generate GCP report", advanced=True, default_size=(1100,950), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Generate GCP report")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.laz')
    main_parser.add_argument("tilelayoutfile", metavar="TileLayout file", widget="FileChooser", help="Select TileLayout file (.json)", default='')
    main_parser.add_argument("control", metavar="Control file", widget="FileChooser", help="Select the GCP height control file")
    main_parser.add_argument("projname", metavar="Project Name", default='')
    main_parser.add_argument('areaname', metavar="Area Name", default='')
    main_parser.add_argument('deltax', metavar="x shift", default=0, type=float)
    main_parser.add_argument('deltay', metavar="y shift", default=0, type=float)
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("armse", metavar="Standard Deviation for filtering", help="The report status will be Not Accepted if value greater than the value provided", type=float)
    main_parser.add_argument("--hasindex", metavar="Has Index?", action= "store_true")
    main_parser.add_argument("--classify", metavar="Ground Classify", action= "store_true")
    main_parser.add_argument("--gndclass", metavar="Ground Classes", default='2 8')
    gnd_group = main_parser.add_argument_group("Ground Settings", gooey_options={'show_border': True,'columns': 5})
    gnd_group.add_argument("--gndstep", metavar="Step", default=10, type=float)
    gnd_group.add_argument("--spike", metavar="Spike", default=0.5, type=float)
    gnd_group.add_argument("--downspike", metavar="Down Spike", default=1, type=float)
    gnd_group.add_argument("--bulge", metavar="Bulge", default=2.5, type=float)
    gnd_group.add_argument("--offset", metavar="Offset", default=1.0, type=float)
    noise_group = main_parser.add_argument_group("Noise Settings", gooey_options={'show_border': True,'columns': 2})
    noise_group.add_argument("--noisestep", metavar="Step",default=3.0, type=float)
    noise_group.add_argument("--isopoints", metavar="Isolated points", default=10, type=int)
    cores_group = main_parser.add_argument_group("Cores Settings", gooey_options={'show_border': True,'columns': 3} )
    cores_group.add_argument("--noisecores", metavar="Classification", help="Number of Cores to be used for Classification process", type=int, default=4, gooey_options={
        'validator': {
            'test': '2 <= int(user_input) <= 14',
            'message': 'Must be between 2 and 14'
        }})
    cores_group.add_argument("--cores", metavar="General", help="Number of cores to be used for tiling process", type=int, default=4, gooey_options={
            'validator': {
                'test': '2 <= int(user_input) <= 14',
                'message': 'Must be between 2 and 14'
            }})
    return main_parser.parse_args()
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def CGPCheck(tilelayout,buffer,laspath, outpath, filetype,tile,points,gndclasses):
    log = ''
    tile = tilelayout.gettile(tile)
    outfile=os.path.join(outpath,'CGP_{0}_result.txt'.format(tile.name)).replace('\\','/')
    gcpfile=os.path.join(outpath,'CGP_{0}.txt'.format(tile.name)).replace('\\','/')
    neighbourlasfiles = []
 
    try:    
        try:
            neighbours = tile.getneighbours(buffer)
  
        except:
            print("tile: {0} does not exist in Tilelayout file".format(tile.name))

        for neighbour in neighbours:
            neighbour = os.path.join(laspath,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

            if os.path.isfile(neighbour):
                neighbourlasfiles.append(neighbour) 
        

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

def color_negative_red(value):
    """
    Colors elements in a dateframe
    green if positive and red if
    negative. Does not color NaN
    values.
    """

    if value < 0:
        color = 'red'
    elif value > 0:
        color = 'green'
    else:
        color = 'black'

    return 'color: %s' % color

def NoiseRemove(input, output, noisestep, isopoints, filetype):
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/lasnoise.exe','-i',input,'-o{0}'.format(filetype),'-o',output,'-step',noisestep, '-isolated', isopoints] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except:
        log = "\n Noise removal failed for {0} \n Exception {1}".format(input, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nNoise removal completed for {0}'.format(input)
            return (True, output, log)
        else:
            log ='\nNoise removal for {0} Failed'.format(input)
            return (False, None, log)

def ClassifyGround(input, output, tile, buffer, step, spike, downspike, bulge, offset):
    log = ''
 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(tile.xmin-buffer), tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
    keep=keep.split()

    try:
        #lasground_new -i neighbourlasfiles -o <name>_gnd.laz -step 10 -spike 0.5 -down_spike 1.0 -bulge 2.5 -offset 0.1 -fine
        subprocessargs=['C:/LAStools/bin/lasground_new.exe','-i']+input+['-o',output,'-merged','-step',step, '-spike', spike, '-down_spike', downspike, '-bulge', bulge, '-offset', offset, '-fine'] + keep
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "\nClassifying ground failed for {0} \n at Exception {1}".format(output, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(output):
            log = '\nClassifying ground completed for {0}'.format(output)
            return (True, output, log)
        else:
            log ='\nClassifying ground  for {0} Failed'.format(output)
            print(log)
            return (False, None, log)




#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):

    freeze_support() 
    args = param_parser()

    filepattern = args.filepattern
    inputfolder = args.inputfolder

    filetype=args.filetype
    dt = strftime("%y%m%d_%H%M")
    outputpath = AtlassGen.makedir(os.path.join(inputfolder, '{0}_GCP_Report'.format(dt)))


    print("Reading {0} files \n".format(filetype))

    filepattern = args.filepattern.split(';')
    user_std = args.armse
    lasfiles=AtlassGen.FILELIST(filepattern, inputfolder)

    if len(lasfiles) ==0:
        print("Exiting as no las files found, please check file type & filter pattern")
        exit()
    
    control=args.control
    tilelayoutfile=args.tilelayoutfile
    buffer=args.buffer
    gndclasses=args.gndclass.split()
    cores=args.cores
    deltax = args.deltax
    deltay = args.deltay
    hasindex = args.hasindex
    classify = args.classify
    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)

    logpath = os.path.join(outputpath,'log_report.txt').replace('\\','/')
    log = open(logpath, 'w')

    lines = [line.rstrip('\n')for line in open(control)]
    index=0

#Clssify
##############################################################################################################################
    if classify:

        noiseremoveddir = AtlassGen.makedir(os.path.join(outputpath, 'Noise_Removed'))
        grounddir = AtlassGen.makedir(os.path.join(outputpath, 'Ground'))
        NOISE_TASK={}

        #Remove noise
        #######################################################################################################################
        print('\n\nRemoving Noise : Started')
        for file in lasfiles:
            path,tilename,ext = AtlassGen.FILESPEC(file)
            input = file
            output = os.path.join(noiseremoveddir, '{0}.{1}'.format(tilename,filetype))
            NOISE_TASK[tilename] = AtlassTask(tilename, NoiseRemove, input, output, args.noisestep, args.isopoints, filetype)

        p=Pool(processes=int(args.noisecores))       
        NOISE_RESULTS=p.map(AtlassTaskRunner.taskmanager,NOISE_TASK.values())
        print('\nRemoving Noise : Completed')

        #Classify ground
        #######################################################################################################################

        MAKE_GROUND_TASKS = {}

        print('\n\nAdding buffer')
        for result in NOISE_RESULTS:
            log.write(result.log)

            if result.success:
                tilename = result.name

                #Get Neigbouring las files
                print('Creating tile neighbourhood for : {0}'.format(tilename))
                tile = tilelayout.gettile(tilename)
                neighbourlasfiles = []

                try:
                    neighbours = tile.getneighbours(buffer)
                except:
                    print("tile: {0} does not exist in geojson file".format(tilename))

                #print('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,tilename))

                for neighbour in neighbours:
                    neighbour = os.path.join(noiseremoveddir,'{0}.{1}'.format(neighbour, filetype)).replace('\\','/')

                    if os.path.isfile(neighbour):
                        neighbourlasfiles.append(neighbour)

                input = neighbourlasfiles
                output = os.path.join(grounddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
                MAKE_GROUND_TASKS[tilename] = AtlassTask(tilename, ClassifyGround, input, output, tile, buffer, args.gndstep, args.spike, args.downspike, args.bulge, args.offset)
                #ClassifyGround(input, output, tile, buffer, demstep, spike, downspike, bulge, offset)
        print('\n\nGround classification : Started')

        p=Pool(processes=int(args.cores))       
        MAKE_GROUND_RESULTS=p.map(AtlassTaskRunner.taskmanager,MAKE_GROUND_TASKS.values())

        for result in MAKE_GROUND_RESULTS:
            log.write(result.log)
        
        print('\nGround classification : Completed')
        
        lasfiles=AtlassGen.FILELIST (filepattern, grounddir)
    
 
    GCPTile={}
    results = []
    for line in lines:
        line=line.split()

        if hasindex:
            if len(line) <=4:

                index=str(line[0])
                x,y,z=float(line[1]),float(line[2]),float(line[3])
            else:
                print("GCP file not accepted, check if index has spaces")
                exit()
        else:
            index+=1
            x,y,z=float(line[0]),float(line[1]),float(line[2])

        for file in lasfiles:
            path, filename, ext = AtlassGen.FILESPEC(file)
            tile = tilelayout.gettile(filename)
            if tile.xmin<x<tile.xmax and  tile.ymin<y<tile.ymax:
                if tile.name in GCPTile.keys():
                    GCPTile[tile.name].append([index,x,y,z])
                else:
                    GCPTile[tile.name]=[[index,x,y,z]]
          

# Generate the results files for tiles that has GCP
##############################################################################################################################
    TASKS={}      
    for tile in GCPTile.keys():
        points=GCPTile[tile]
        TASKS[tile]= AtlassTask(tile, CGPCheck,tilelayout,buffer,inputfolder,outputpath,filetype,tile,points,gndclasses)
        #CGPCheck(tilelayout,buffer,outputpath,filetype,tile,points,gndclasses)
    
    p=Pool(processes=cores)      
    results=p.map(AtlassTaskRunner.taskmanager,TASKS.values())


# Generate the statistical report
##############################################################################################################################
    total_gcp_points = len(lines)
    print('\nNo of GCP points in control: {0}'.format(total_gcp_points))

    pointlist = PointList()
    report_hist = os.path.join(outputpath,'points_dist.png').replace('\\', '/')
    report_pdf = os.path.join(outputpath,'Statistical_Report_3Sigma_{0}_{1}.pdf'.format(args.projname, args.areaname)).replace('\\', '/')
   
    for result in results:
        f = open(result.result)
        for line in f.readlines():
            line = line.rstrip("\n")
            z = line.split(' ')
            diff = round(float(z[0]), 4)
            pointlist.addPoint(z[5],z[2],z[3],z[1],z[4],diff)
            
    gcp_outof_range = total_gcp_points-len(pointlist)
    print('\nNo of GCPs out of range: {0}'.format(gcp_outof_range))
    
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
        if point.accepted:
            dataset.append(point.dzshifted)

    bins = 'auto'
    plt.xlim([min(dataset), max(dataset)])
    plt.hist(dataset, bins=bins, alpha=0.5)
    plt.title('Histogram of height difference')
    plt.xlabel('Height differences after a shift of {0}m'.format(shift))
    plt.ylabel('count')
    plt.savefig(report_hist)
    
     
    #Generate data table
    data_all = []
    for key, point in pointlist.points.items():
        data_all.append({'index':point.index, 'x':point.x, 'y':point.y, 'lidarz':point.lidarz,'dz':point.dz, 'controlz':point.controlz, 'dz after shift':point.dzshifted})

    df = pd.DataFrame(data_all)
    #Order columns
    df = df[['index','x', 'y','controlz', 'lidarz', 'dz', 'dz after shift']]
    df.sort_values(by=['index'])
    df.style.applymap(color_negative_red, subset=['dz'])


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


    gcp_outof_range_perc = round(gcp_outof_range/points*100,1)
    dt = strftime("%d/%m/%y")
    logo = 	"\\\\10.10.10.100\\projects\\PythonScripts\\icons\\logo.png"
    env = Environment(loader=FileSystemLoader("\\\\10.10.10.100\\projects\\PythonScripts\\templates"))
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
                    "logo" : logo,
                    "quality": quality,
                    "note" : note}
    # Render our file and create the PDF using our css style file
    html_out = template.render(template_vars)
    stylesheet = os.path.join('\\\\10.10.10.100\\projects\\PythonScripts\\templates','style.css').replace('\\', '/')
    HTML(string=html_out).write_pdf(report_pdf, stylesheets=[stylesheet])

    print('Process complete')
        
    return
        
if __name__ == "__main__":
    main(sys.argv[1:])            