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

@Gooey(program_name="Generate GCP report", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Generate GCP report")
    main_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input las/laz folder", default="")
    main_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns \nex: (*.laz) or (123*_456*.laz; 345*_789*.laz )", default='*.las')
    main_parser.add_argument("tilelayoutfile", metavar="TileLayout file", widget="FileChooser", help="Select TileLayout file (.json)", default='')
    main_parser.add_argument("control", metavar="Control file", widget="FileChooser", help="Select the GCP height control file")
    main_parser.add_argument("projname", metavar="Project Name", default='Dawson')
    main_parser.add_argument('areaname', metavar="Area Name", default='South')
    main_parser.add_argument('deltax', metavar="x shift", default=0, type=float)
    main_parser.add_argument('deltay', metavar="y shift", default=0, type=float)
    main_parser.add_argument("--gndclass", metavar="Ground Classes", default='2 8')
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    
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
            f.write('{0} {1} {2}\n'.format(x,y,z))
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

def calc_stats(data):
    dmean = round(statistics.mean(data), 2)
   
    variance = statistics.pvariance(data, dmean)
    sigma = math.sqrt(variance)
    tsigma = round(sigma*3, 2)

    return (dmean, tsigma)

def filter_data(data_all, tsigma):

    data_new = []
    data_all_new = []
    data_rej = []

    for x in data_all:
        if ( (-tsigma) < x.get('diff') < tsigma):
            data_all_new.append(x)
            data_new.append(x.get('diff'))
        else:
            data_rej.append(x)

    return(data_all_new, data_rej, data_new)
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):

    freeze_support() 
    args = param_parser()

    filepattern = args.filepattern
    inputfolder = args.inputfolder
    outputpath = AtlassGen.makedir(os.path.join(inputfolder, 'Report'))
    filetype=args.filetype


    print("Reading {0} files \n".format(filetype))

    filepattern = args.filepattern.split(';')

    lasfiles=AtlassGen.FILELIST (filepattern, inputfolder)

    
    control=args.control
    tilelayoutfile=args.tilelayoutfile
    buffer=args.buffer
    gndclasses=args.gndclass.split()
    cores=args.cores
    deltax = args.deltax
    deltay = args.deltay

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)

    lines = [line.rstrip('\n')for line in open(control)]
    index=0

    GCPTile={}
    
    results = []
    for line in lines:
        line=line.split()
        index=index+1
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


    data = []
    data_all = []
    report_hist = os.path.join(outputpath,'points_dist.png').replace('\\', '/')
    report_pdf = os.path.join(outputpath,'Statistical_Report_3Sigma_{0}_{1}.pdf'.format(args.projname, args.areaname)).replace('\\', '/')
    i=1
    for result in results:
        f = open(result.result)
        for line in f.readlines():
            line = line.rstrip("\n")
            z = line.split(' ')
            diff = round(float(z[0]), 4)
            data.append(diff)
            data_all.append({'index':i,'east':z[2], 'north':z[3],'control':z[4], 'lidar':z[1], 'diff':diff})
            i+=1
        
    gcp_outof_range = total_gcp_points-len(data)

    print('\nNo of GCPs out of range: {0}'.format(gcp_outof_range))
    #Calculate initial statistics
    dmean, tsigma = calc_stats(data)
    print('\n\ninitial sigma {0}'.format(tsigma))
    
    # Filter data
    print('-----------------Filtering Data by zigma -----------------------')
    data_all_new, data_rej, data_new = filter_data(data_all, tsigma)

    print('Total number of data sampled {0}'.format(len(data_all)))
    print('No of filtered data : {0}'.format(len(data_all_new)))
    print('No of rejected data : {0}'.format(len(data_rej)))



    #generate  histogram
    bins = 'auto'
    plt.xlim([min(data)-5, max(data)+5])
    plt.hist(data, bins=bins, alpha=0.5)
    plt.title('Histogram of height difference')
    plt.xlabel('Height difference')
    plt.ylabel('count')
    plt.savefig(report_hist)
    
     
    #Generate data table
    df = pd.DataFrame(data_all_new)
    #Order columns
    df = df[['index','east', 'north','control', 'lidar', 'diff']]
    df.style.applymap(color_negative_red, subset=['diff'])

    #Re-Calculate statistics
    dmean, tsigma = calc_stats(data_new)
    print('final sigma {0}'.format(tsigma))
    print('final mean {0}'.format(dmean))

    #Check Report Quality
    if dmean>5 and dmean<-5:
        quality = 'Accepted'
    else:
        quality = 'Not Accepted'

    #Create PDF report
    points = total_gcp_points
    points_accept = len(data_new)
    points_accept_perc = round((len(data_new)/len(data)*100), 0)
    points_rej = (points-len(data_new))
    points_rej_perc = round((points_rej/points_accept*100), 0)
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
                    "GCP_not_found" : gcp_outof_range,
                    "report": report_hist,
                    "mean": dmean,
                    "tsigma": tsigma,
                    "data": df.to_html(),
                    "deltax" : deltax,
                    "deltay" : deltay,
                    "date" : dt,
                    "logo" : logo,
                    "quality": quality}
    # Render our file and create the PDF using our css style file
    html_out = template.render(template_vars)
    stylesheet = os.path.join('\\\\10.10.10.100\\projects\\PythonScripts\\templates','style.css').replace('\\', '/')
    HTML(string=html_out).write_pdf(report_pdf, stylesheets=[stylesheet])

    print('Process complete')
        
    return
        
if __name__ == "__main__":
    main(sys.argv[1:])            