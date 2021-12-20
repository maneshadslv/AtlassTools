
import os, sys
import time
import numpy as np
import pandas as pd
from laspy.file import File
import math
from scipy import spatial
import random
from collections import defaultdict , OrderedDict
import itertools
import json
from gooey import Gooey,GooeyParser
from multiprocessing import Pool,freeze_support
import random, string
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *



@Gooey(program_name="QA File Check", use_legacy_titles=True, required_cols=2, optional_cols=3, advance=True, default_size=(1000,810))
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

    parser=GooeyParser(description="QA Check Files")
    subs = parser.add_subparsers(help='commands', dest='command')
    parser2 = subs.add_parser('CHECKFILES', help='Check files for corruption')
    parser2.add_argument("ori_path", metavar="LAS file Folder with original files(unclassified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('ori_path'))
    parser2.add_argument("rec_path", metavar="LAS file Folder with recieved files(classified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('rec_path'))
    parser2.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default=stored_args.get('layoutfile'))
    parser2.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputpath'))
    parser2.add_argument("filetype", metavar="File Type",help="input filetype (laz/las)", default='laz')
    parser2.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=stored_args.get('cores'))

    args = parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def geninfo(tilename,ori,rec):



    '''
    read data from file
    '''
    
    
    
    oriFile = File(ori, mode='r')
    recFile = File(rec, mode='r')

    '''
    create dataframe ori file
    '''

    tic = time.perf_counter()
    dataori={}
    dataori["points"] = pd.DataFrame(oriFile.points["point"])
    dataori["points"].columns = (x.lower() for x in dataori["points"].columns)
    dataori["points"].loc[:, ["x", "y", "z"]] *= oriFile.header.scale 
    dataori["points"].loc[:, ["x", "y", "z"]] += oriFile.header.offset
    dataori["header"] = oriFile.header

    '''
    create dataframe rec file
    '''

    datarec={}
    datarec["points"] = pd.DataFrame(recFile.points["point"])
    datarec["points"].columns = (x.lower() for x in datarec["points"].columns)
    # rescale and offset
    datarec["points"].loc[:, ["x", "y", "z"]] *= recFile.header.scale 
    datarec["points"].loc[:, ["x", "y", "z"]] += recFile.header.offset
    datarec["header"] = recFile.header
    toc = time.perf_counter()
    print(f"data frame created in {toc - tic:0.4f} seconds")

   

    tdata=OrderedDict()

    # Header Information
    # version test
    o_version=oriFile.header.version
    r_version=recFile.header.version

    if o_version != r_version:
        version_test='Failed'
        tdata['Version'] = f'Ori - {o_version} Rec - {r_version}'
        tdata['Version Test'] = 'Failed'
        print(f"Version test Failed for {tilename}")
    else:
        version_test='Passed'
        tdata['Version'] = f'{o_version}'
        tdata['Version Test'] = 'Passed'
        print(f"Version test Passed for {tilename}")
    
    # Data Format ID testt
    o_pdrf = oriFile.header.data_format_id
    r_pdrf = recFile.header.data_format_id

    if o_pdrf != r_pdrf:
        tdata['PDRF'] = f'Ori-{o_pdrf} Rec - {r_pdrf}'
        tdata['PDRF Test'] = 'Failed'

    else:
        tdata['PDRF'] = f'{o_pdrf}'
        tdata['PDRF Test'] = 'Passed'


    # Global Engoding testt
    o_ge = oriFile.header.global_encoding
    r_ge = recFile.header.global_encoding

    if o_ge != r_ge:
        tdata['GlobalEncoding'] = f'Ori-{o_ge} Rec - {r_ge}'
        tdata['GlobalEncoding Test'] = 'Failed'

    else:
        tdata['GlobalEncoding'] = f'{o_ge}'
        tdata['GlobalEncoding Test'] = 'Passed'


    #test number of points
    o_len = len(dataori['points'])
    r_len = len(datarec['points'])
    if o_len != r_len:
        tdata['Number of points'] = f'Ori - {o_len} Rec - {r_len}'
        tdata['Number of Points Test'] = 'Failed'
        print(f"Number of points test Failed for {tilename}")
    else:
        len_test='Passed'
        tdata['Number of points'] = len(datarec['points'])
        tdata['Number of Points Test'] = 'Passed'
        #print(f"Number of points test Passed for {tilename}")

    
    #test points

    tic = time.perf_counter()

    x0=dataori['points']['x']
    x1=datarec['points']['x']

    y0=dataori['points']['y']
    y1=datarec['points']['y']

    z0=dataori['points']['z']
    z1=datarec['points']['z']



    #print(x0==x1)
    #print(y0==y1)
    #print(z0==z1)
    if x0.all()!=x1.all() and y0.all()!=y1.all() and z0.all()!=z1.all():
        tdata['Points Test'] = 'Failed'
        toc = time.perf_counter()
        print(f"Points test Failed - {toc - tic:0.4f} seconds")
    else:
        print(f'{tilename} XYZ matched')
        tdata['Points Test'] = 'Passed'
        toc = time.perf_counter()
        print(f"Points test Passed - {toc - tic:0.4f} seconds")


    #test gpstime
    r_gps = [min(datarec['points']['gps_time']),max(datarec['points']['gps_time'])]
    o_gps = [min(dataori['points']['gps_time']),max(dataori['points']['gps_time'])]

    if o_gps != r_gps:
        gps_test='Failed'
        tdata['GPS times'] = f'Ori - {o_gps} Rec - {r_gps}'
        tdata['GPS Test'] = 'Failed'
        print(f"GPS Times test Failed for {tilename}")
    else:
        gps_test='Passed'
        tdata['GPS times'] = r_gps
        tdata['GPS Test'] = 'Passed'
        #print(f"GPS Times test Passed for {tilename}")

    # returns test
    o_returns=oriFile.get_return_num()
    r_returns=recFile.get_return_num()

    nr0=oriFile.get_num_returns()
    nr1=recFile.get_num_returns()    


    #nr1=datarec['points']['number of returns']

    if o_returns.all() != r_returns.all():
        returns_test='Failed'
        tdata['Returns'] = f'Ori - {o_returns} Rec - {r_returns}'
        tdata['Returns Test'] = 'Failed'
        print(f"Point Returns test Failed for {tilename}")
    else:
        returns_test='Passed'
        tdata['Returns'] = f'{o_returns[1],nr0[1]}'
        tdata['Returns Test'] = 'Passed'        
        print(f"Point Returns test Passed for {tilename}")
        ##returns=[i for i, j in zip(o_returns, r_returns) if i != j]
        #print(returns)
    
    # Intensity test
    r_intensity=[min(datarec['points']['intensity']),max(datarec['points']['intensity'])]
    o_intensity=[min(dataori['points']['intensity']),max(dataori['points']['intensity'])]
    
    if o_intensity != r_intensity:
        intensity_test='Failed'
        tdata['Intensity'] = f'Ori - {o_intensity} Rec - {r_intensity}'
        tdata['Intensity Test'] = 'Failed'
        print(f"Intensity test Failed for {tilename}")
    else:
        intensity_test='Passed'
        tdata['Intensity'] = f'{o_intensity}'
        tdata['Intensity Test'] = 'Passed'
        #print(f"Intensity test Passed for {tilename}")

    # Scale test
    o_scale=oriFile.header.scale
    r_scale=recFile.header.scale
    #print(o_offscale,r_offscale)
    if o_scale != r_scale:
        tdata['Scale']=f'Ori-{o_scale} Rec - {r_scale}'
        tdata['Scale Test'] = 'Failed'
        print(f"Scale test Failed for {tilename}")
    else:
        tdata['Scale']=f'{o_scale}'
        tdata['Scale Test'] = 'Passed'
        #print(f"Offset_Scale test Passed for {tilename}")
 
    return(True,tdata,'None')
   
def main():
    
    #Set Arguments
    args = param_parser()


    jsonfile = args.layoutfile
    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(jsonfile)
    orifolder = args.ori_path
    recfolder = args.rec_path
    outputfolder = args.outputpath
    filetype = args.filetype
    cores = args.cores
    dt = strftime("%y%m%d_%H%M")

    outputfile = os.path.join(outputfolder,f'FileCheckReport_{dt}.xlsx')

    tasks = {}
    for tile in tilelayout:
        tilename = tile.name

        ori = os.path.join(orifolder,f'{tilename}.{filetype}').replace("\\","/")
        rec = os.path.join(recfolder,f'{tilename}.{filetype}').replace("\\","/")
        tasks[tilename]= AtlassTask(tilename, geninfo, tilename,ori,rec)

    p=Pool(processes=cores)        
    task_results=p.map(AtlassTaskRunner.taskmanager,tasks.values())
    
    resultt = OrderedDict()
    print('Program Starting')

    for result in task_results:

        resultt[result.name] = result.result
         

    #print(resultt)
    df = pd.DataFrame(data=resultt).T
    df = df[['Version','Version Test','PDRF','PDRF Test','GlobalEncoding','GlobalEncoding Test','Number of points','Number of Points Test','Points Test','GPS times', 'GPS Test', 'Intensity','Intensity Test','Scale','Scale Test','Returns','Returns Test']]
    # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(outputfile)

    return()

if __name__ == "__main__":
    main() 

 