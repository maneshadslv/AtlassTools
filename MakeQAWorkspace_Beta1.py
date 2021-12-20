#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import os
from gooey import Gooey, GooeyParser
import subprocess
import datetime
from time import strftime, sleep
from shutil import copyfile
import glob
from multiprocessing import Pool,freeze_support
import urllib
import shutil
import json
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeDEMLib import *
import fnmatch
from collections import defaultdict , OrderedDict
import numpy as np
import pandas as pd
from laspy.file import File
import xlsxwriter

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make QA", use_legacy_titles=True, required_cols=2, default_size=(1120,920))
def param_parser():
    stored_args = {}
    # get the script name without the extension & use it to build up
    # the json filename
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    congifg_folder = AtlassGen.makedir("C:\\pythontools")
    args_file = os.path.join(congifg_folder,"{}-args.json".format(script_name))

    
    globalmapperversions = glob.glob('C:\\Program Files\\'+'GlobalMapper*')

    if len(globalmapperversions) >= 2:
        for vers in globalmapperversions:
            if fnmatch.fnmatch(vers, '*GlobalMapper2*'):
                globalmapperexe = '{0}\\global_mapper.exe'.format(vers)
            elif fnmatch.fnmatch(vers, '*GlobalMapper18*'):
                globalmapperexe = '{0}\\global_mapper.exe'.format(vers)
        
    else:  
        globalmapperexe = '{0}\\global_mapper.exe'.format(globalmapperversions[0])

    #print(globalmapperexe)
    # Read in the prior arguments as a dictionary
    if os.path.isfile(args_file):
        with open(args_file) as data_file:
            stored_args = json.load(data_file)
    
    main_parser=GooeyParser(description="Make QA workspace")
    sub_pars = main_parser.add_subparsers(help='commands', dest='command')
    parser = sub_pars.add_parser('GMQA', help='Preparation QA workspace in GM')
    parser.add_argument("inputfolder", metavar="LAS file Folder", widget="DirChooser", help="Select las file folder", default=stored_args.get('inputfolder'))
    parser.add_argument("filetype",metavar="Input File Type",default='laz')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default=stored_args.get('layoutfile'))
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputpath'))
    cls_type = parser.add_mutually_exclusive_group(required=True,gooey_options={'initial_selection': 0})
    cls_type.add_argument("--type1", metavar="Type 1  [classes- DEM, 3,4,5,9]", action='store_true')
    cls_type.add_argument("--type1TMR", metavar="Type 1 w/ 17 & 19  [classes- DEM, 3,4,5,9,17,19]", action='store_true')
    cls_type.add_argument("--type2", metavar="Type 2 [classes- DEM, 3,4,5,6,1,9,10,13]", action='store_true')
    cls_type.add_argument("--type3", metavar="Type 3 [classes- DEM, 3,4,5,6,1,9,10,11,12,13,14,15,16]", action='store_true')
    parser.add_argument("--diff", metavar="Diff - Make Tiffs to check coverage", action='store_true')
    parser.add_argument("projection", metavar="Projection", choices=['AMG (Australian Map Grid)','MGA (Map Grid of Australia)'], default=stored_args.get('projection'))
    parser.add_argument("datum", metavar="Datum",choices=['D_AUSTRALIAN_1984','D_AUSTRALIAN_1966','GDA94', 'GDA2020'], default=stored_args.get('datum'))
    parser.add_argument("zone", metavar="UTM Zone", choices=['50','51','52','53','54','55','56'],default=stored_args.get('zone'))
    parser.add_argument("step", metavar="Step for lasgrid", type=float, default=stored_args.get('step'))
    parser.add_argument("gmexe", metavar="Global Mapper EXE", widget="FileChooser", help="Location of Global Mapper exe",default=globalmapperexe)
    parser.add_argument("-workspace", metavar="Create Global Mapper workspace", action='store_true')
    parser.add_argument("-onlymapC", metavar="Create only the map catalogs(TIFs must be available", action='store_true')
    parser.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=stored_args.get('cores'))
    parser2 = sub_pars.add_parser('CHECKFILES', help='Check files for corruption')
    parser2.add_argument("ori_path", metavar="LAS file Folder with original files(unclassified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('ori_path'))
    parser2.add_argument("rec_path", metavar="LAS file Folder with recieved files(classified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('rec_path'))
    parser2.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default=stored_args.get('layoutfile'))
    parser2.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputpath'))
    parser2.add_argument("orifiletype", metavar="Ori File Type",help="Ori input filetype (laz/las)", default='laz')
    parser2.add_argument("recfiletype", metavar="Rec File Type",help="Rec input filetype (laz/las)", default='laz')
    parser2.add_argument("-validClasses", metavar="Valid Classes",help="input valid classes", default='1,2,3,4,5,6,7,9,10,13')
    parser2.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=stored_args.get('cores'))
    parser2.add_argument("-correctbbt", metavar="Correct Bounding Box", action='store_true')
    parser3 = sub_pars.add_parser('SUMMARIZE', help='Check files for corruption')
    parser3.add_argument("ori_path", metavar="LAS file Folder with original files(unclassified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('ori_path'))
    parser3.add_argument("rec_path", metavar="LAS file Folder with recieved files(classified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('rec_path'))
    parser3.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default=stored_args.get('layoutfile'))
    parser3.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputpath'))
    parser3.add_argument("filetype", metavar="File Type",help="input filetype (laz/las)", default='laz')
    parser3.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=stored_args.get('cores'))

    args = main_parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def geninfo(tilename,ori,rec,validClasses):

    tdata=OrderedDict()
    tilecheckPassed = 'Passed'
    print(tilename)
    if os.path.isfile(ori) and os.path.isfile(rec):
        '''
        read data from file
        '''
    


        try:
            oriFile = File(ori, mode='r')
            recFile = File(rec, mode='r')
        except:
            print(f'File Corrupted : {tilename}')
            tdata={"Classification" : "None","Classification Test" : "None","Version" : "None","Version Test" : "None", "PDRF" : "None","PDRF Test":"None", "GlobalEncoding":"None","GlobalEncoding Test":"None","Number of points": "None", "Number of Points Test": "None","Points Test": "None","GPS times":"None","GPS Test":"None","Returns":"None","Returns Test":"None","Intensity":"None","Intensity Test":"None","Scale":"None","Scale Test":"None","Status":"Failed","Boundaries":"None","Boundary Test":"None"}
            return(True,tdata,'None')
           
   

        '''
        create dataframe ori file
        '''

        #tic = time.perf_counter()
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
        #toc = time.perf_counter()
        #print(f"data frame created in {toc - tic:0.4f} seconds")

        # Header Information
        ############################################################
        # version test
        ############################################################
        o_version=oriFile.header.version
        r_version=recFile.header.version

        if o_version != r_version:
            version_test='Failed'
            tdata['Version'] = f'Ori - {o_version} Rec - {r_version}'
            tdata['Version Test'] = 'Warning'
            #print(f"Version test Failed for {tilename}")
            tilecheckPassed = 'Warning'
        else:
            version_test='Passed'
            tdata['Version'] = f'{o_version}'
            tdata['Version Test'] = 'Passed'
            #print(f"Version test Passed for {tilename}")
    
        ###########################################################
        # Data Format ID testt (PDRF)
        ############################################################
        o_pdrf = oriFile.header.data_format_id
        r_pdrf = recFile.header.data_format_id

        if o_pdrf != r_pdrf:
            tdata['PDRF'] = f'Ori-{o_pdrf} Rec - {r_pdrf}'
            tdata['PDRF Test'] = 'Failed'
            tilecheckPassed = 'Warning'

        else:
            tdata['PDRF'] = f'{o_pdrf}'
            tdata['PDRF Test'] = 'Passed'
        ###########################################################
        # Global Engoding test
        ###########################################################
        o_ge = oriFile.header.global_encoding
        r_ge = recFile.header.global_encoding

        if o_ge != r_ge:
            tdata['GlobalEncoding'] = f'Ori-{o_ge} Rec - {r_ge}'
            tdata['GlobalEncoding Test'] = 'Failed'
            tilecheckPassed = 'Warning'
        else:
            tdata['GlobalEncoding'] = f'{o_ge}'
            tdata['GlobalEncoding Test'] = 'Passed'


        ##########################################################
        # Bounding Box Test
        #########################################################
        #check Min Max
        recxmin = round(min(datarec["points"]["x"]),3)
        recymin = round(min(datarec["points"]["y"]),3)
        reczmin = round(min(datarec["points"]["z"]),3)
        recxmax = round(max(datarec["points"]["x"]),3)
        recymax = round(max(datarec["points"]["y"]),3)
        reczmax = round(max(datarec["points"]["z"]),3)     
        #print(recxmin,recymin)
        
        r_xmin = round(recFile.header.min[0],3)
        r_ymin = round(recFile.header.min[1],3)
        r_zmin = round(recFile.header.min[2],3)
        r_xmax = round(recFile.header.max[0],3)
        r_ymax = round(recFile.header.max[1],3)
        r_zmax = round(recFile.header.max[2],3)

        #print(r_xmin,r_ymin)

        if recxmin != r_xmin or recymin != r_ymin:
            tdata['Boundaries'] = f'Rec File - min[{recxmin},{recymin},{reczmin}],max[{recxmax},{recymax},{reczmax}] Rec Header - min[{r_xmin},{r_ymin},{r_zmin}],max[{r_xmax},{r_ymax},{r_zmax}]'
            tdata['Boundary Test'] = 'Failed'
            tilecheckPassed = 'Warning'
        else:
            tdata['Boundaries'] = f'min[{recxmin},{recymin}],max[{recxmax},{recymax}]'
            tdata['Boundary Test'] = 'Passed'
 
        #########################################################
        # Classification Test
        #########################################################
        #get classification
        all_classes = set(list(range(0,256)))
        valid_classes = set(validClasses)
        invalid_classes = all_classes-valid_classes
        #print(invalid_classes)

        #o_class = oriFile.get_classification()
        r_class = recFile.get_classification()

        check =  list(invalid_classes.intersection(r_class))

        if len(check) >0:
            tdata['Classification'] = check
            tdata['Classification Test'] = 'Failed'
            #print(f"Version test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else :
            tdata['Classification'] = None
            tdata['Classification Test'] = 'Passed'

        ###########################################################
        # Number of points Test
        ##########################################################
        o_len = len(dataori['points'])
        r_len = len(datarec['points'])
        if o_len != r_len:
            tdata['Number of points'] = f'Ori - {o_len} Rec - {r_len}'
            tdata['Number of Points Test'] = 'Failed'
            print(f"Number of points test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            len_test='Passed'
            tdata['Number of points'] = len(datarec['points'])
            tdata['Number of Points Test'] = 'Passed'
            #print(f"Number of points test Passed for {tilename}")

        ###########################################################
        # Points Test
        ###########################################################

        tic = time.perf_counter()

        x0=dataori['points']['x']
        x1=datarec['points']['x']

        y0=dataori['points']['y']
        y1=datarec['points']['y']

        z0=dataori['points']['z']
        z1=datarec['points']['z']

        #print(x0.all()!=x1.all())
        #print(y0.all()!=y1.all())
        #print(z0.all()!=z1.all())
        if x0.all()!=x1.all() or y0.all()!=y1.all() or z0.all()!=z1.all():
            tdata['Points Test'] = 'Failed'
            toc = time.perf_counter()
            print(f"Points test Failed - {toc - tic:0.4f} seconds")
            tilecheckPassed = 'Failed'
        else:
            #print(f'{tilename} XYZ matched')
            tdata['Points Test'] = 'Passed'
            toc = time.perf_counter()
            #print(f"Points test Passed - {toc - tic:0.4f} seconds")

        #############################################################
        # GPS time test
        ##############################################################
        r_gps = [min(datarec['points']['gps_time']),max(datarec['points']['gps_time'])]
        o_gps = [min(dataori['points']['gps_time']),max(dataori['points']['gps_time'])]

        if o_gps != r_gps:
            gps_test='Failed'
            tdata['GPS times'] = f'Ori - {o_gps} Rec - {r_gps}'
            tdata['GPS Test'] = 'Failed'
            print(f"GPS Times test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            gps_test='Passed'
            tdata['GPS times'] = r_gps
            tdata['GPS Test'] = 'Passed'
            #print(f"GPS Times test Passed for {tilename}")
        
        ###############################################################
        # Intensity test
        ###############################################################

        r_intensity=[min(datarec['points']['intensity']),max(datarec['points']['intensity'])]
        o_intensity=[min(dataori['points']['intensity']),max(dataori['points']['intensity'])]
        
        if o_intensity != r_intensity:
            intensity_test='Failed'
            tdata['Intensity'] = f'Ori - {o_intensity} Rec - {r_intensity}'
            tdata['Intensity Test'] = 'Failed'
            print(f"Intensity test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            intensity_test='Passed'
            tdata['Intensity'] = f'{o_intensity}'
            tdata['Intensity Test'] = 'Passed'
            #print(f"Intensity test Passed for {tilename}")

        ###############################################################
        # Scale test
        ################################################################

        o_scale=oriFile.header.scale
        r_scale=recFile.header.scale
        #print(o_offscale,r_offscale)
        if o_scale != r_scale:
            tdata['Scale']=f'Ori-{o_scale} Rec - {r_scale}'
            tdata['Scale Test'] = 'Failed'
            print(f"Scale test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            tdata['Scale']=f'{o_scale}'
            tdata['Scale Test'] = 'Passed'
            #print(f"Offset_Scale test Passed for {tilename}")

        ##############################################################
        # Returns test
        #############################################################

        o_returns=oriFile.get_return_num()
        r_returns=recFile.get_return_num()

        #nr0=oriFile.get_num_returns()
        #nr1=recFile.get_num_returns()    


        #nr1=datarec['points']['number of returns']

        if o_returns.all() != r_returns.all():
            returns_test='Failed'
            returns=[i for i, j in zip(o_returns, r_returns) if i != j]
            tdata['Returns'] = f'Returns not matching {returns}'
            tdata['Returns Test'] = 'Failed'
            tilecheckPassed = 'Failed'
            #print(f"Point Returns test Failed for {tilename}")
        else:
            returns_test='Passed'
            tdata['Returns'] = f'{min(o_returns),max(o_returns)}'
            tdata['Returns Test'] = 'Passed'        
            #print(f"Point Returns test Passed for {tilename}")
            ##returns=[i for i, j in zip(o_returns, r_returns) if i != j]
            #print(returns)

        tdata['Status']=tilecheckPassed
        return(True,tdata,'None')
    else:
        print(f'One of the files could not be found for Tile {tilename}')
        tdata={"Classification" : "None","Classification_Test" : "None","Version" : "None","Version Test" : "None", "PDRF" : "None","PDRF Test":"None", "GlobalEncoding":"None","GlobalEncoding Test":"None","Number of points": "None", "Number of points Tetst": "None","Points Test": "None","GPS times":"None","GPS Test":"None","Returns":"None","Returns Test":"None","Intensity":"None","Intensity Test":"None","Scale":"None","Scale Test":"None","Status":"None","Boundaries":"None","Boundary Test":"None"}
        return(True,tdata,'None')

def makegmsfiles(input_dir,gmcfile,gmsfiles, zone, datum, projection,filetype):

    if datum == 'D_AUSTRALIAN_1984':
        proj_name = "AMG_ZONE{0}_AUSTRALIAN_GEODETIC_1984".format(zone)

    if datum == 'D_AUSTRALIAN_1966':
        proj_name = "AMG_ZONE{0}_AUSTRALIAN_GEODETIC_1966".format(zone)

    if datum == 'GDA94':
        proj_name = "MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994".format(zone)

    if datum == 'GDA2020':
        proj_name = "MGA_ZONE{0}_GDA_2020_AUSTRALIAN_GEODETIC_2020".format(zone)

    template = '''GLOBAL_MAPPER_SCRIPT VERSION="1.00" FILENAME="{5}" 
UNLOAD_ALL 
DEFINE_PROJ PROJ_NAME="{0}" 
Projection     MGA (Map Grid of Australia) 
Datum          {2} 
Zunits         NO 
Units          METERS 
Zone           {1} 
Xshift         0.000000 
Yshift         0.000000 
Parameters 
END_DEFINE_PROJ 
EDIT_MAP_CATALOG FILENAME="{3}" CREATE_IF_EMPTY=YES \
ADD_FILE="{4}\*.{6}" \
ZOOM_DISPLAY="PERCENT,0.90,0"
// Load the map catalog
IMPORT FILENAME="{3}"
'''.format(proj_name, zone, datum, gmcfile, input_dir, gmsfiles,filetype)

    dstfile = gmsfiles

    log = ''

    try:
            
        with open(dstfile, 'w') as f:
                f.write(template)

        if os.path.exists(dstfile):
            log = 'Successfully created GMS file for :{0}'.format(gmsfiles)
            return(True,dstfile,log)
        else:
            log = 'Could not create GMS file for :{0}'.format(gmsfiles)
            return(False,None,log)
    except:
        log = 'Could not create GMS file for :{0}, Failed at exception'.format(gmsfiles)
        return(False,None,log)


def rungmsfiles(gmpath, gmsfile, cl):
    log = ''

    try:
        subprocessargs=[gmpath, gmsfile]
        subprocessargs=list(map(str,subprocessargs))
        print(subprocessargs)
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        log = 'Creating Map Catalog for class {0} was successful'.format(cl)
        return (True,None, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (True,None,log)

    except:
        log = 'Could not run GMS file for class {0}, Failed at Subprocess'.format(cl)  
        return (False,None, log)


def maketiffile(tile, input, output, classN, step, prjfile,classdir): #parse in xmin ymin nrows ncols
    log = ''
    tilename = tile.name
    xmin = tile.xmin
    ymin = tile.ymin
    xmax = tile.xmax
    tilesize = int(xmax-xmin)
    try:
        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-o' , output, '-otif', '-nbits', 32, '-elevation_highest', '-step', step, '-keep_class', classN] #-ll xmin ymin -nrows -ncols
        subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        prjfile2 = os.path.join(classdir,'{0}_{1}.prj'.format(tilename,classN)).replace('\\','/')
        shutil.copyfile(prjfile, prjfile2) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make tif for {0}, Failed at Subprocess'.format(input)  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            
            #removed as 1kb files are not the cause of GM crash.
            #print(os.path.getsize(output)) 
            if os.path.getsize(output) <= 1000:
                os.remove(output)
                print('Deleted {0} : less the 1kB'.format(output))
                log ='Deleted {0} : less the 1kB'.format(output)
                return (True,output, log)
            else:
                log = 'Making tif file was successful for {0}'.format(input)
                return (True,output, log)

        else:
            log = 'Could not make tif file for {0}'.format(input)   
            return (False,None, log)

def makedifftiffile(inputfile, outputfile, outputdir):

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasoverlap.exe', '-i', inputfile, '-odir',outputdir, '-otif', '-keep_class', 2, '-step', 1.0 ,'-min_diff', 0.15, '-max_diff', 0.35,  '-no_over'] 
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

       
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make tif for {0}, Failed at Subprocess'.format(inputfile)  
        print(log)
        return (False,None, log)

    finally:
        if os.path.isfile(outputfile):
            log = 'Making tif file was successful for {0}'.format(inputfile)
            return (True,outputfile, log)

        else:
            log = 'Could not make tif file for {0}'.format(inputfile)   
            return (False,None, log)


def correctbb(lasfile):
    try:
        subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lasfile, '-repair'] 
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

       
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not correct BB for {0}, Failed at Subprocess'.format(lasfile)  
        print(log)
        return (False,None, log)

    finally:
        if os.path.isfile(lasfile):
            log = 'Correcting BB was successful for {0}'.format(lasfile)
            return (True,lasfile, log)

        else:
            log = 'Could not correct file {0}'.format(lasfile)   
            return (False,None, log)


def makedemascfiles(tile, inputfile, outputfile,outputdir,prjfile,step,kill):
    log = ''
    tilename = tile.name
    xmin = tile.xmin
    ymin = tile.ymin
    xmax = tile.xmax
    tilesize = int(xmax-xmin)
    print(tilename,inputfile, outputfile,outputdir,prjfile,step,kill)
    try:
        subprocessargs=['C:/LAStools/bin/blast2dem.exe', '-i', inputfile, '-odir',outputdir, '-oasc','-nbits',32, '-keep_class', 2, '-step', float(step),'-kill',kill] 
        #subprocessargs=subprocessargs+['-ll',xmin,ymin,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        prjfile2 = os.path.join(outputdir,'{0}.prj'.format(tilename)).replace('\\','/')
        shutil.copyfile(prjfile, prjfile2) 

  
    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make DEM for {0}, Failed at Subprocess'.format(inputfile)  
        print(log)
        return (False,None, log)

    finally:
        if os.path.isfile(outputfile):
            log = 'Making DEM file was successful for {0}'.format(inputfile)
            return (True,outputfile, log)

        else:
            log = 'Could not make DEM file for {0}'.format(inputfile)   
            return (False,None, log)
   
def checkfiles(tilename,orifile,recfile,outputdir, orifiletype,recfiletype):

    print('Working with {0}'.format(tilename))

    orilasinfofile = genLasinfo(orifile,tilename,outputdir,orifiletype,'ori')
    reclasinfofile = genLasinfo(recfile,tilename,outputdir,recfiletype,'rec')
    report=os.path.join(outputdir,'{0}_report.txt'.format(tilename)).replace("\\","/")


    #constants
    attribs=OrderedDict()
    attribs['num_points']='  number of point records:    '
    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    attribs['scale']='  scale factor x y z:         '
    attribs['gps_time']='  gps_time '
    attribs['point_source_ID']='  point_source_ID   '
    attribs['intensity']='  intensity         '
    attribs['first']='number of first returns:        '
    attribs['intermediate']='number of intermediate returns: '
    attribs['last']='number of last returns:         '
    attribs['single']='number of single returns:       '
    attribs['pdrf']='  point data format:          '
    attribs['version']='  version major.minor:        '


    #file1
    lines1=[line.rstrip('\n')for line in open(orilasinfofile)]
    lines2=[line.rstrip('\n')for line in open(reclasinfofile)]


    filedict1=OrderedDict()
    for line in lines1:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict1[attrib]=line.replace(attribs[attrib],'')

    filedict2=OrderedDict()
    for line in lines2:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict2[attrib]=line.replace(attribs[attrib],'')

            

    reptstring=''
    test=True

    try:
        for attrib in attribs.keys():
            
            if not attrib in filedict1.keys():
                reptstring='{0} not foud in file 1\n'.format(attrib)
                test=False
            if not attrib in filedict2.keys():
                reptstring=reptstring+'{0} not foud in file 2\n'.format(attrib)
                test=False
            if not filedict1[attrib]==filedict2[attrib]:
                test=False
                reptstring=reptstring+'File1:{0}\n'.format(filedict1[attrib])
                reptstring=reptstring+'File2:{0}\n'.format(filedict2[attrib])
                #return(False,None,"not sure")

        if test:
            os.remove(orilasinfofile)
            os.remove(reclasinfofile)
            if os.path.isfile(report):
                os.remove(report)
        else:
            f=open(report,'w')
            f.write('Mismatch detected:\nfile1:{0}\nfile2:{1}\n'.format(orilasinfofile,reclasinfofile)+reptstring)
            f.close()

    except:
        log = 'Could not compare ATTRIBUTE : {0}, For file {1}'.format(attrib,tilename)  
        print(log)
        return (True,None, log)

    finally:

        if not test:
            log = 'Mismatch detected:\nfile1:{0}\nfile2:{1}\n'.format(orilasinfofile,reclasinfofile)+reptstring
            return(test,[tilename,filedict1,filedict2],log)
        else:
            return(test,[tilename,filedict1,filedict2],'Test Failed')


def SummarizeFiles(tilename,orifile,outputdir, filetype):

    print('Working with {0}'.format(tilename))

    orilasinfofile = genLasinfo(orifile,tilename,outputdir,filetype,'')
    report=os.path.join(outputdir,'{0}_report.txt'.format(tilename)).replace("\\","/")


    #constants
    attribs=OrderedDict()
    attribs['num_points']='  number of point records:    '
    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    attribs['scale']='  scale factor x y z:         '
    attribs['gps_time']='  gps_time '
    attribs['point_source_ID']='  point_source_ID   '
    attribs['intensity']='  intensity         '
    attribs['first']='number of first returns:        '
    #attribs['intermediate']='number of intermediate returns: '
    attribs['last']='number of last returns:         '
    attribs['single']='number of single returns:       '
    attribs['pdrf']='  point data format:          '
    attribs['version']='  version major.minor:        '


    #file1
    lines1=[line.rstrip('\n')for line in open(orilasinfofile)]


    filedict1=OrderedDict()
    for line in lines1:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict1[attrib]=line.replace(attribs[attrib],'')


    reptstring=''
    test=True

    try:
        for attrib in attribs.keys():
            
            if not attrib in filedict1.keys():
                reptstring='{0} not found in file 1\n'.format(attrib)
                test=False
                filedict1[attrib] = 'Couldnt find attribute'


                f.write('No infomation for attrin : {0} in file {1}'.format(attrib ,tilename))
                f.close()

    except:
        log = 'Could not compare ATTRIBUTE : {0}, For file {1}'.format(attrib,tilename)  
        print(log)
        return (True,None, log)

    finally:

        if not test:
            log = 'Could not compare ATTRIBUTE : {0}, For file {1}'.format(attrib,tilename) 
            return(test,[tilename,filedict1],log)
        else:
            return(test,[tilename,filedict1],'Test Failed')


def makeecwfile(tilename, qadir, ecwoutputdir, classes, step, prjfile,rgb_color,gmpath):
 
    log = ''

    gmsfile = os.path.join(ecwoutputdir,"{0}.gms".format(tilename)).replace('\\','/')
    prjfile=prjfile.replace('/','\\')
    ecwoutput=os.path.join(ecwoutputdir,'{0}.ecw'.format(tilename)).replace('/','\\')

    print(gmsfile,prjfile, ecwoutput)

    try:
    
        gms = '''GLOBAL_MAPPER_SCRIPT VERSION="1.00"
SET_BG_COLOR COLOR="RGB(255,255,255)"
UNLOAD_ALL 
LOAD_PROJECTION FILENAME="{0}"'''.format(prjfile)
        for cl in classes:
            rgb=rgb_color[cl]
            classdir = os.path.join(qadir,"class_{0}".format(cl)).replace('/','\\')
            tifinput = os.path.join(classdir,'{0}_{1}.tif'.format(tilename,cl)).replace('/','\\')
            
            gms = gms + '''\nDEFINE_SHADER SHADER_NAME="class{0}" BLEND_COLORS="YES" STRETCH_TO_RANGE="NO" SHADE_SLOPES="NO" \\
	 SLOPES_PERCENT="NO" OVERWRITE_EXISTING="NO" SAVE_SHADER="YES"
	0,RGB({1})
END_DEFINE_SHADER
IMPORT FILENAME="{2}" \\
	 TYPE="GEOTIFF" LABEL_FIELD_FORCE_OVERWRITE="NO" LABEL_FORMAT_NUMBERS="YES" LABEL_PRECISION="-1" \\
	 LABEL_REMOVE_TRAILING_ZEROS="YES" LABEL_USE_SCIENTIFIC_NOTATION="NO" LOAD_FLAGS="0~0~0~3~0~0" \\
	 RASTER_TYPE="GRID" BAND_RANGE="282.540008545,333.002014160,NO_DATA,1,-9999.00000000000000000" \\
	 CLIP_COLLAR="NONE" SAMPLING_METHOD="NEAREST_NEIGHBOR" ELEV_UNITS="METERS" SHADER_NAME="class{0}"'''.format(cl,rgb,tifinput)

        gms = gms+'''
EXPORT_RASTER FILENAME="{0}"\\
TYPE="ECW" GEN_WORLD_FILE=YES GEN_PRJ_FILE="YES"
UNLOAD_ALL'''.format(ecwoutput)


        f = open(gmsfile, 'w')
        f.write(gms)  
        f.close()    

        rungmsfiles(gmpath, gmsfile,'ecw')


    
    except:
        log = 'Could not make tif for {0}, Failed at Subprocess'.format(tifinput)  
        return (False,None, log)

    finally:
        if os.path.isfile(ecwoutput):
            
            #removed as 1kb files are not the cause of GM crash.
            #print(os.path.getsize(output)) 
            if os.path.getsize(ecwoutput) == 0:
                sleep(20)
                os.remove(gmsfile)
                print('done')

            else:
                os.remove(gmsfile)
                log = 'Making ecw file was successful for {0}'.format(tifinput)
            return (True,ecwoutput, log)
            
            log = 'Making ecw file was successful for {0}'.format(tifinput) 
            return (True,ecwoutput, log)

        else:
            log = 'Could not make tif file for {0}'.format(tifinput)   
            return (False,None, log)
    


def genLasinfo(lazfile,tilename,outputdir,filetype,key):
  
    #genLasinfo(lazfile)
    lasinfofile = os.path.join(outputdir,'{0}{1}.txt'.format(tilename,key)).replace("\\","/")

    subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lazfile,'-otxt','-o',lasinfofile]
    subprocessargs=list(map(str,subprocessargs))
    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

 
    if os.path.exists(lasinfofile):
        return (lasinfofile)
    

    else:
        return(None)


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()
    #print(args)

    if args.command == 'GMQA':
        inputfolder=args.inputfolder
        filetype = args.filetype
        zone = args.zone
        lasfiles = AtlassGen.FILELIST(['*.{0}'.format(filetype)], inputfolder)

        tilelayoutfile = args.layoutfile
        outpath = args.outputpath.replace('\\','/')
        #hydrofiles = args.hydrofiles
        #aoi = args.aoi
        step = args.step
        makediff = args.diff
        print(makediff)

        scriptpath = os.path.dirname(os.path.realpath(__file__))
        print(scriptpath)
    
        gmexe = args.gmexe.replace('\\','/')
        classes = []
        rgb_colors = {}
        rgb_colors[1] = '128,128,128'
        rgb_colors[2] = '242,121,0'
        rgb_colors[3] = '0,128,64'
        rgb_colors[4] = '0,157,157'
        rgb_colors[5] = '121,242,0'
        rgb_colors[6] = '255,0,0'
        rgb_colors[7] = '0,0,225'
        rgb_colors[9] = '0,125,255'
        rgb_colors[10] = '128,255,255'
        rgb_colors[11] = '0,255,255'
        rgb_colors[12] = '192,192,192'
        rgb_colors[13] = '255,192,0'
        rgb_colors[14] = '128,0,128'
        rgb_colors[15] = '255,255,0'
        rgb_colors[16] = '128,64,64'
        rgb_colors[17] = '255,255,0'
        rgb_colors[19] = '128,64,64'

        if args.type1:
            classes = [2,3,4,5,9]
        
        if args.type1TMR:
            classes = [2,3,4,5,9,17,19]

        if args.type2:
            classes = [2,3,4,5,6,1,9,10,13]

        if args.type3:
            classes = [2,3,4,5,6,1,9,10,11,12,13,14,15,16]

        cores = args.cores

        print(tilelayoutfile)
        print('Classes selected for QA {0}: '.format(classes))

        if not args.onlymapC:
            if not lasfiles:
                print("Please select the correct file type", "No Selected files")
                exit()

            dt = strftime("%y%m%d_%H%M")
        
            workingdir = AtlassGen.makedir(os.path.join(outpath, (dt+'_QAWorkspace')).replace('\\','/'))
            qatifdir = AtlassGen.makedir(os.path.join(workingdir, 'qa').replace('\\','/'))
            DEMdir = AtlassGen.makedir(os.path.join(qatifdir, 'DEM').replace('\\','/'))
            ECWdir = AtlassGen.makedir(os.path.join(qatifdir, 'ECW').replace('\\','/'))

        if args.onlymapC:
            qatifdir = inputfolder
            workingdir = inputfolder.replace('qa','')

        if args.datum == 'D_AUSTRALIAN_1984':
            proj_name = "AMG_ZONE{0}_AUSTRALIAN_GEODETIC_1984".format(zone)
            epsg = 20300 + int(zone)
            prjfile = "{1}\\EPSG\\{0}.prj".format(epsg,scriptpath)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))

        if args.datum == 'D_AUSTRALIAN_1966':
            proj_name = "AMG_ZONE{0}_AUSTRALIAN_GEODETIC_1966".format(zone)
            epsg = 20200 + int(zone)
            prjfile = "{1}\\EPSG\\{0}.prj".format(epsg,scriptpath)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))

        if args.datum == 'GDA94':
            proj_name = "MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994".format(zone)
            epsg = 28300 + int(zone)
            prjfile = "{1}\\EPSG\\{0}.prj".format(epsg,scriptpath)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))


        if args.datum == 'GDA2020':
            proj_name = "MGA_ZONE{0}_GDA_2020_AUSTRALIAN_GEODETIC_2020".format(zone)
            epsg = 7800 + int(zone)
            prjfile = "{1}\\EPSG\\{0}.prj".format(epsg,scriptpath)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))


        print('EPSG : {0}'.format(epsg))
        print(proj_name)
        
        projfile = os.path.join(workingdir, 'workspace.prj').replace("\\", "/")
        shutil.copy(prjfile,projfile)

        tl_in = AtlassTileLayout()
        tl_in.fromjson(tilelayoutfile)
        

        mk_tif_tasks = {}
        mk_diff_tasks = {}
        mk_dem_tasks = {}
        mk_ecw_tasks = {}


        if not args.onlymapC:

            correctbb_tasks = {}
            #Correct Bounding box
            print('Correcting Bounding box')
            for tile in tl_in:
                filename = tile.name
                lasfile = os.path.join(inputfolder, '{0}.{1}'.format(filename,filetype)).replace('\\','/')
               
                                                                                #tile,inputfile, outputfile,outputdir,prjfile,step,kill
                correctbb_tasks[filename] = AtlassTask(filename, correctbb,lasfile)

            p=Pool(processes=cores)      
            correctbb_results=p.map(AtlassTaskRunner.taskmanager,correctbb_tasks.values())

            
            #Make TIF Files for each class
            for cl in classes:
                classdir = AtlassGen.makedir(os.path.join(qatifdir, 'Class_{0}'.format(str(cl))).replace('\\','/'))
                print('Making tifs for class {0}'.format(str(cl)))
                for tile in tl_in:
                    filename = tile.name
                    lasfile = os.path.join(inputfolder, '{0}.{1}'.format(filename, filetype)).replace('\\','/')
            
                    #file
                    input = lasfile
                    output = os.path.join(classdir,'{0}_{2}.{1}'.format(filename,'tif',cl)).replace('\\','/')
                    ecwinput = output
                    ecwoutput = output.replace('.tif','.ecw')
                    projfiletif = output.replace('.tif','.prj')

                    path, filename, ext = AtlassGen.FILESPEC(lasfile)
                    tiffile = '{0}_{1}'.format(filename,cl)
                    mk_tif_tasks[tiffile] = AtlassTask(filename, maketiffile, tile, input, output, cl, step, projfile, classdir)    
                     
                    
            
            p=Pool(processes=cores)      
            mk_tif_results=p.map(AtlassTaskRunner.taskmanager,mk_tif_tasks.values())
        

            #make ecw files
            for tile in tl_in:
                filename = tile.name                                         
                                                                                      #tilename, qadir, ecwoutputdir, classes, step, prjfile,rgb_color,gmpath
                mk_ecw_tasks[filename] = AtlassTask(filename, makeecwfile, filename, qatifdir, ECWdir, classes, step, projfile, rgb_colors,gmexe)   
               
            p=Pool(processes=cores)      
            mk_ecw_results=p.map(AtlassTaskRunner.taskmanager,mk_ecw_tasks.values())
            
   

            #make dem files
            for tile in tl_in:
                filename = tile.name
                lasfile = os.path.join(inputfolder, '{0}.{1}'.format(filename,filetype)).replace('\\','/')
                outputfile = os.path.join(DEMdir, '{0}.asc'.format(filename)).replace('\\','/')
                                                                                #tile,inputfile, outputfile,outputdir,prjfile,step,kill
                mk_dem_tasks[filename] = AtlassTask(filename, makedemascfiles, tile, lasfile,outputfile, DEMdir, projfile,step, 250)

            p=Pool(processes=cores)      
            mk_dem_results=p.map(AtlassTaskRunner.taskmanager,mk_dem_tasks.values())

            #make diff files
            if makediff:
                print('Making tifs for diff')
                diff_path = AtlassGen.makedir(os.path.join(qatifdir,"diff").replace('\\','/'))
                for tile in tl_in:
                    filename = tile.name
                    lasfile = os.path.join(inputfolder, '{0}.{1}'.format(filename,filetype)).replace('\\','/') 
                    input = lasfile
                    outputdir = diff_path
                    output = os.path.join(diff_path,'{0}.tif'.format(filename)).replace('\\','/')
                    prjfile2 = os.path.join(diff_path,'{0}_diff.prj'.format(filename)).replace('\\','/')
                    shutil.copyfile(projfile, prjfile2) 
                    mk_diff_tasks[filename] = AtlassTask(filename, makedifftiffile, input,output, outputdir)
                
                p=Pool(processes=cores)           
                mk_diff_results=p.map(AtlassTaskRunner.taskmanager,mk_diff_tasks.values())

        if args.onlymapC:
            workingdir = workingdir.replace('\qa','')
            
        if args.workspace:

            #Make GMS files for Map Catalog for 
            
            DEMdir = AtlassGen.makedir(os.path.join(qatifdir, 'DEM').replace('\\','/'))

            gms_path = AtlassGen.makedir(os.path.join(workingdir, 'gm_scripts').replace('\\','/'))
            mk_gmsfiles_tasks = {}
            

            #DEMdir = os.path.join(DEMdir, 'makeGRID_output/DEM').replace('/','\\')
            gmcfile = os.path.join(DEMdir, 'dem.gmc').replace('/','\\')
            gmsfile = os.path.join(gms_path,'dem.gms').replace('\\','/')
            mk_gmsfiles_tasks['dem'] = AtlassTask('dem', makegmsfiles,DEMdir,gmcfile,gmsfile, args.zone, args.datum, args.projection,'asc')

            ECWdir = AtlassGen.makedir(os.path.join(qatifdir, 'ECW').replace('\\','/'))
            gmcfile = os.path.join(ECWdir, 'ecw.gmc').replace('/','\\')
            gmsfile = os.path.join(gms_path,'ecw.gms').replace('\\','/')
            mk_gmsfiles_tasks['ecw'] = AtlassTask('ecw', makegmsfiles,ECWdir,gmcfile,gmsfile, args.zone, args.datum, args.projection,'ecw')

            for cl in classes:
                cl = str(cl)
                input_dir = os.path.join(qatifdir, 'Class_{0}'.format(cl)).replace('/','\\')
                gmcfile = os.path.join(input_dir, 'Class_{0}.gmc'.format(cl)).replace('/','\\')
                gmsfile = os.path.join(gms_path,'Class_{0}.gms'.format(cl)).replace('\\','/')
                print(gmcfile, gmsfile, input_dir)
                mk_gmsfiles_tasks[cl] = AtlassTask(cl, makegmsfiles,input_dir,gmcfile,gmsfile, args.zone, args.datum, args.projection,'tif')

            if makediff:
                diff_path = os.path.join(qatifdir,"diff").replace('/','\\')
                gmcfile = os.path.join(diff_path, 'diff.gmc').replace('/','\\')
                gmsfile = os.path.join(gms_path,'dif.gms').replace('\\','/')
                print(gmcfile, gmsfile, diff_path)
                mk_gmsfiles_tasks['diff'] = AtlassTask('diff', makegmsfiles,diff_path,gmcfile,gmsfile, args.zone, args.datum, args.projection,'tif')         
            
            p=Pool(processes=cores)        
            mk_gmsfiles_results=p.map(AtlassTaskRunner.taskmanager,mk_gmsfiles_tasks.values())


            #Run GMS files
            ###########################################################################################################################################
            run_gmsfiles_tasks = {}
            for result in mk_gmsfiles_results:
                print(result.success, result.log)
                if result.success:
                    cl = result.name     
                    path, filename, ext = AtlassGen.FILESPEC(result.result)
                    #files
                    gmscript = os.path.join(gms_path,'{0}.{1}'.format(filename,'gms')).replace('\\','/')

                    run_gmsfiles_tasks[cl] = AtlassTask(cl, rungmsfiles, gmexe, gmscript, cl)

            run_gmsfiles_results=p.map(AtlassTaskRunner.taskmanager,run_gmsfiles_tasks.values())


        
            #Generate the gm workspace
            ############################################################################################################################################
    
            gmwfile = os.path.join(workingdir, 'workspace.gmw').replace("\\", "/")
            
    
            workspc = 'GLOBAL_MAPPER_SCRIPT VERSION="1.00" \nSET_BG_COLOR COLOR="RGB(255,255,255)" \nUNLOAD_ALL'

            for i in range(len(classes)):
                classno = classes[i]
                workspc = workspc+'\nDEFINE_SHADER SHADER_NAME="class{0}" BLEND_COLORS="YES" STRETCH_TO_RANGE="NO" SHADE_SLOPES="NO" SLOPES_PERCENT="NO" OVERWRITE_EXISTING="NO" \n0,RGB({1})\nEND_DEFINE_SHADER'.format(classno,rgb_colors[classno] )
            workspc = workspc+'\nDEFINE_SHADER SHADER_NAME="Emboss" BLEND_COLORS="YES" STRETCH_TO_RANGE="YES" SHADE_SLOPES="NO" SLOPES_PERCENT="NO" OVERWRITE_EXISTING="NO" SAVE_SHADER="YES" \n0,RGB(255,255,255)\nEND_DEFINE_SHADER'

            workspc = workspc + '\nIMPORT FILENAME="qa/DEM/dem.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,25000.000,0.0000000000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="Emboss"'
           
            for i in range(len(classes)):
                classno = classes[i]
                if os.path.exists(os.path.join(qatifdir,'Class_{0}/Class_{0}.gmc'.format(classno))):
                    workspc = workspc + '\nIMPORT FILENAME="qa/Class_{0}/Class_{0}.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,250000.000,0.0000000000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="class{0}"'.format(classno)
            
            if makediff:
                diff_path = os.path.join(qatifdir,"diff").replace('/','\\')
                workspc = workspc + '\nIMPORT FILENAME="qa/diff/diff.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,250000.000,10000.0000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="Atlas Shader"'
            
            workspc = workspc + '\nIMPORT FILENAME="qa/ECW/ecw.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,2500000.000,0.0000000000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE"'
            
            workspc = workspc + '''\nDEFINE_PROJ PROJ_NAME="{2}"
            Projection     {3}
            Datum          {4}
            Zunits         NO
            Units          METERS
            Zone           {0}
            Xshift         0.000000
            Yshift         0.000000
            Parameters
            END_DEFINE_PROJ
            IMPORT FILENAME="{1}" TYPE="GEOJSON" PROJ_NAME="{2}" \
                LABEL_FIELD_FORCE_OVERWRITE="NO" LOAD_FLAGS="0"
            LOAD_PROJECTION PROJ_NAME="{2}"
            SET_VIEW GLOBAL_BOUNDS="691759.460,7443162.180,710831.253,7452051.069"
            SET_VERT_DISP_OPTS SHADER_NAME="Emboss" AMBIENT_LIGHT_LEVEL="0.10000000" VERT_EXAG="1.0000000" \
                LIGHT_ALTITUDE="51.000000" LIGHT_AZIMUTH="45.000000" LIGHT_NUM_SOURCES="1" LIGHT_BLENDING_ALGORITHM="0" \
                ENABLE_HILL_SHADING="YES" SHADE_DARKNESS="0" SHADE_HIGHLIGHT="0" ENABLE_WATER="NO" \
                WATER_ALPHA="128" WATER_LEVEL="0.0000000000" WATER_COLOR="RGB(0,0,255)"

            /************ DEFINE MAP LAYOUT *************/
            MAP_LAYOUT
            ElevLegendBgColor=16777215
            ElevLegendTranslucency=384
            ElevLegendFont=~0~534799372~0.000~0~0~16777215
            ElevLegendVisible=0
            ElevLegendDisplayType=1
            ElevLegendDisplayUnits=1
            ElevLegendDisplayUnitsStr=
            ElevLegendCustomRangeMin=0
            ElevLegendCustomRangeMax=0
            ElevLegendRangeType=0
            ElevLegendTitle=
            ElevLegendSlopePercent=0

            END_MAP_LAYOUT'''.format(zone, tilelayoutfile, proj_name, args.projection, args.datum )

            f = open(gmwfile, 'w')
            f.write(workspc)  
            f.close()    

    if args.command == 'SUMMARIZE':

        originalpath = args.ori_path
        recievedpath = args.rec_path
        outputpath = args.outputpath
        tilelayoutfile = args.layoutfile
        cores = args.cores
        filetype = args.filetype

        orilasfiles = AtlassGen.FILELIST(['*.{0}'.format(filetype)], originalpath)

        checkfiles_tasks = {}
        summary=os.path.join(outputpath,'Summary_Rec.csv').replace("\\","/")

        tilelayout = AtlassTileLayout()
        tilelayout.fromjson(tilelayoutfile)
        rec_filelist = AtlassGen.FILELIST([f'*.{filetype}'],recievedpath)
        ori_filelist = AtlassGen.FILELIST([f'*.{filetype}'],originalpath)

        print('Program Starting')
        print(f'\nNumber of files in the original dataset : {len(ori_filelist)}')
        print(f'\nNumber of files in the recieved dataset : {len(rec_filelist)}')
        print(f'\nNumber of files in the TL : {len(tilelayout)}')

        for tile in tilelayout:
            
            filename = tile.name
            of = os.path.join(originalpath,'{0}.{1}'.format(filename,filetype))
            rf = os.path.join(recievedpath,'{0}.{1}'.format(filename,filetype))
            if os.path.exists(rf):
 
                #print(of, rf)
                checkfiles_tasks[filename] = AtlassTask(filename, checkfiles, filename,of,rf,outputpath,filetype)         

            else:
                print('File {0} does not exists in the Recieved Files'.format(rf))
        
        p=Pool(processes=cores)        
        mk_gmsfiles_results=p.map(AtlassTaskRunner.taskmanager,checkfiles_tasks.values())

        report=os.path.join(outputpath,'Final_report.txt').replace("\\","/")
        f=open(report,'w')
        sf=open(summary,'w')
        attribshead = mk_gmsfiles_results[0].result[1]

        #header of CSV
        sf.write('Tilename,')
        for k,v in attribshead.items():
            sf.write('O_{0},'.format(k))
            sf.write('R_{0},'.format(k))

        sf.write('Status\n')


        for result in mk_gmsfiles_results:
            #print(result.success, result.log)
            tilename = result.result[0]
            atribs1 = result.result[1]
            atribs2 = result.result[2]     
            sf.write('{0}, '.format(tilename))
            for k,v in atribs2.items():
                sf.write('{0},'.format(atribs1[k]))
                sf.write('{0}, '.format(v))

            if result.success:
                sf.write('Success')


            else:
                sf.write('Failed')
                f.write(result.log)
            sf.write('\n')

        f.close()       
        sf.close()

        print('Summerize Check Completed')
    
    if args.command == 'CHECKFILES':

        jsonfile = args.layoutfile
        tilelayout = AtlassTileLayout()
        tilelayout.fromjson(jsonfile)
        orifolder = args.ori_path
        recfolder = args.rec_path
        outputfolder = args.outputpath
        orifiletype = args.orifiletype
        recfiletype = args.recfiletype
        correctbbt = args.correctbbt
        validClasses = args.validClasses
        cores = args.cores

        validClasses = validClasses.split(',')
        validClasses = [int(i) for i in validClasses] 
        print('Valid Classes : {0}'.format(validClasses))

        rec_filelist = AtlassGen.FILELIST([f'*.{recfiletype}'],recfolder)
        ori_filelist = AtlassGen.FILELIST([f'*.{orifiletype}'],orifolder)
        
        print('Program Starting')
        print(f'\nNumber of files in the original dataset : {len(ori_filelist)}')
        print(f'\nNumber of files in the recieved dataset : {len(rec_filelist)}')
        print(f'\nNumber of files in the TL : {len(tilelayout)}')

        dt = strftime("%y%m%d_%H%M")

        outputfile = os.path.join(outputfolder,f'FileCheckReport_{dt}.xlsx')

        if correctbbt:
            correctbb_tasks = {}
            #Correct Bounding box
            print('Correcting Bounding box')
            for tile in tilelayout:
                filename = tile.name
                lasfile = os.path.join(recfolder, '{0}.{1}'.format(filename,recfiletype)).replace('\\','/')
                                                                                        
                correctbb_tasks[filename] = AtlassTask(filename, correctbb,lasfile)

            p=Pool(processes=cores)      
            correctbb_results=p.map(AtlassTaskRunner.taskmanager,correctbb_tasks.values())

        tasks = {}
        for tile in tilelayout:
            tilename = tile.name

            ori = os.path.join(orifolder,f'{tilename}.{orifiletype}').replace("\\","/")
            rec = os.path.join(recfolder,f'{tilename}.{recfiletype}').replace("\\","/")
            tasks[tilename]= AtlassTask(tilename, geninfo, tilename,ori,rec,validClasses)

        p=Pool(processes=cores)        
        task_results=p.map(AtlassTaskRunner.taskmanager,tasks.values())
        
        resultt = OrderedDict()

        print(f'\nOriginal laz file locaiton : {orifolder}')
        print(f'Recieved laz file location : {recfolder}')
        for result in task_results:

            resultt[result.name] = result.result
            

        #print(resultt)
        df = pd.DataFrame(data=resultt).T
        df = df[['Version','Version Test','PDRF','PDRF Test','GlobalEncoding','GlobalEncoding Test','Boundaries','Boundary Test','Classification','Classification Test','Number of points','Number of Points Test','Points Test','GPS times', 'GPS Test', 'Intensity','Intensity Test','Scale','Scale Test','Returns','Returns Test','Status']]
        # Convert the dataframe to an XlsxWriter Excel object.
        ##df.to_excel(outputfile)
        print(f'\nFile Check Completed\n\nReport location : {outputfile}')
        
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(outputfile, engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='Sheet1')

        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        # Green fill with dark green text for passed.
        format1 = workbook.add_format({'bg_color':   '#C6EFCE', 'font_color': '#006100'})
        # Red fill with dark red text for failed.
        format2 = workbook.add_format({'bg_color':   '#FFC7CE', 'font_color': '#9C0006'})
        # Red fill with dark red text for failed.
        format5 = workbook.add_format({'bg_color':   '#F0B87D', 'font_color': '#946738'})
        # Heading yellow fill with black text.
        format3 = workbook.add_format({'bg_color':   '#FAFF00', 'font_color': '#000000', 'text_wrap': True})
        # Heading red fill with black text.
        format4 = workbook.add_format({'bg_color':   '#FF0000', 'font_color': '#000000', 'text_wrap': True})

        worksheet.conditional_format(0,0,len(df),22, {'type': 'text',
                                        'criteria': 'containing',
                                        'value':    'Passed',
                                        'format':   format1})
        worksheet.conditional_format(0,0,len(df),22, {'type': 'text',
                                        'criteria': 'containing',
                                        'value':    'Failed',
                                        'format':   format2})
        worksheet.conditional_format(0,0,len(df),22, {'type': 'text',
                                        'criteria': 'containing',
                                        'value':    'Warning',
                                        'format':   format5})

        worksheet.conditional_format('B1:I1', {'type': 'unique', 'format':   format3})
        worksheet.conditional_format('J1:V1', {'type': 'unique', 'format':   format4})
        worksheet.set_column(1,23,12)
        worksheet.set_column(0,0,15)
        workbook.close()
    return

if __name__ == "__main__":
    main()       

