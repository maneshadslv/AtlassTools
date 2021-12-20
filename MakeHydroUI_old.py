import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import json
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeHydroLib import *

@Gooey(program_name="Make Hydro Grids", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=3,advance=True, navigation='SIDEBAR',)
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

    parser=GooeyParser(description="Make Hydro Grids")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    step1_parser = sub_pars.add_parser('Step_1', help='Preparation of Hydro voids as individual shp files')
    step1_parser.add_argument("laspath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default=stored_args.get('laspath'))
    step1_parser.add_argument("filetype",metavar="Input File type", help="laz or las", default='laz')
    step1_parser.add_argument("geojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default=stored_args.get('geojsonfile'))
    step1_parser.add_argument("deliverypath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default=stored_args.get('deliverypath'))
    step1_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default=stored_args.get('workpath'))    
    step1_parser.add_argument("areaname", metavar="AreaName",default=stored_args.get('areaname'))
    step1_parser.add_argument("aoi", metavar="Aoi Shp file",widget="FileChooser",default=stored_args.get('aoi'))
    step1_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    step1_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    step1_parser.add_argument("-k", "--kill",metavar="Kill", help="Maximum triagulation length", type=int, default=250)
    step1_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    step1_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    output_group = step1_parser.add_argument_group("Create the merge files only", "Run this only if the merge files does not get created in this step", gooey_options={'show_border': True,'columns': 3})
    output_group.add_argument("--createmerge", metavar="Create Merge", action='store_true', default=False)
    output_group.add_argument("--lazfiles", metavar="LAZ File Path", widget="DirChooser", help="Select folder of the laz files generated in step 1", default=stored_args.get('lazfiles'))
    step2_parser = sub_pars.add_parser('Step_2', help='Calculation of Elevation for each void- Run after global mapper step')
    step2_parser.add_argument("shpfilepath", metavar="SHP File Path", widget="DirChooser", help="Select folder of the shp files generated from Global Mapper", default=stored_args.get('shpfilepath'))
    step2_parser.add_argument("demfolder", metavar="DEM files", widget="DirChooser", help="Select the folder with the DEM files", default=stored_args.get('demfolder'))
    step2_parser.add_argument("outputfolder", metavar="Output folder", widget="DirChooser", help="Output folder for Hydro Laz file", default=stored_args.get('outputdir'))
    step2_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    step3_parser = sub_pars.add_parser('Step_3', help='Calculation of Elevation for each void- Run after global mapper step')
    step3_parser.add_argument("lazpath", metavar="LAZ Path", widget="DirChooser", help="Select folder with Laz poly", default=stored_args.get('lazpath'))
    step3_parser.add_argument("outputfolder", metavar="Output folder", widget="DirChooser", help="Output folder for Hydro Laz file", default=stored_args.get('outputdir'))
    step3_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    
    args = parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

def createBoundries(mergedRawHydroFile,mergedHydroShp,step):

    concavity = round(float(math.sqrt((step**2.0)*2.0))+0.1,2)
    print('Concavity = {0}'.format(concavity))

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasboundary.exe', '-i', mergedRawHydroFile ,'-oshp', '-concavity', concavity ,'-holes','-disjoint' ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  


    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making merged file for {0} Exception - {1}".format(mergedHydroShp, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(mergedHydroShp):
            log = "Making merged for {0} Success".format(mergedHydroShp)
            print(log)
            return (True,mergedHydroShp, log)

        else: 
            log = "Making merged for {0} Failed".format(mergedHydroShp)
            print(log)
            return (False,None, log)

def ascTolaz(ascfile,lazfile):

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', ascfile ,'-olaz', '-rescale', 0.001,0.001,0.001 ,'-o',lazfile ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  



    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Converting asc to Laz failed at Exception for : {0} - {1}".format(lazfile, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(lazfile):
            subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', lazfile]
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            log = "Converting asc to Laz {0} Success".format(lazfile)
            print(log)
            return (True,lazfile, log)

        else: 
            log = "Converting asc to Laz {0} Failed".format(ascfile)
            print(log)
            return (False,None, log)

def genLasinfo(lazfile):
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lazfile,'-otxt' ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  
        return(True,None,log)


    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "generating lasinfo for {0} Exception - {1}".format(lazfile, e)
        print(log)
        return(False,None, log)

def movefile(inputfile,outputfile):
        try:
            shutil.move(inputfile, outputfile)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            return (False,None,log)

        finally:
            if os.path.isfile(outputfile):
                log = "\nMoving file {0} Success".format(inputfile)
                print(log)
                return (True,outputfile, log)

            else: 
                log = "\n **** Moving file {0} Failed ****".format(inputfile)
                return (False,outputfile, log)

def clipLaz(lazpath,shpfile,hydrolaz):


    lazfiles = '{0}/*.laz'.format(lazpath).replace('\\','/')
    log=''
    try:
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' , lazfiles, '-merged', '-poly', shpfile, '-o',hydrolaz]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(hydrolaz):
            log = "Clipping {0} output : {1}".format(str(shpfile), str(hydrolaz)) 
            return (True,output, log)

        else:
            log = "Clipping failed for {0}. ".format(str(shpfile)) 
            print(log)
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Clipping failed for {0}. Failed at Subprocess ".format(str(shpfile)) 
        print(log)
        return(False, None, log)  


def zadjust(input,output,clamp_val):

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', input,'-o', output, '-clamp_z',clamp_val, clamp_val,'-olaz' ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  
        return(True,None,log)


    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Clamping for {0} Exception - {1}".format(input, e)
        print(log)
        return(False,None, log)
    
    finally:
        if os.path.isfile(output):
            log = "Clamping for {0} Successfull".format(output)
            print(log)
            return (True,output, log)

        else: 
            log = "Clamping for {0} Failed".format(output)
            print(log)
            return (False,None, log)

def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()

    if args.command == 'Step_1':


        areaname = args.areaname 
        laspath = args.laspath
        filetype = args.filetype 
        workpath = args.workpath.replace('\\','/')
        deliverypath = args.deliverypath.replace('\\','/')
        tilelayout = args.geojsonfile.replace('\\','/')
        step = float(args.step)
        buffer = args.buffer
        aoi = args.aoi
        kill = args.kill
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles
            hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')


        cores = args.cores
        dt = strftime("%y%m%d_%H%M")

        deliverypath = AtlassGen.makedir(os.path.join(deliverypath, '{0}_makeHydro'.format(dt)).replace('\\','/'))
        deliverypath = AtlassGen.makedir(os.path.join(deliverypath, areaname).replace('\\','/'))
        workingdir = AtlassGen.makedir(os.path.join(workpath, '{0}_makeHydro_Working'.format(dt)).replace('\\','/'))


        make_Hydro = {}
        make_Hydro_results = []

        tl = AtlassTileLayout()
        tl.fromjson(tilelayout)

        if not args.createmerge:
            
            for tile in tl: 

                tilename = tile.name
                make_Hydro[tilename] = AtlassTask(tilename,Hydro.newmakeHydroperTile,tilename,laspath,deliverypath,workingdir,tilelayout,areaname,aoi,filetype,buffer,step,kill,hydropointsfiles)

            p=Pool(processes=cores)   
            make_Hydro_results=p.map(AtlassTaskRunner.taskmanager,make_Hydro.values())      

            merged_dir = AtlassGen.makedir(os.path.join(deliverypath,'merged').replace('\\','/'))
            mergedRawHydroFile = '{0}/merged_Hydro_voids_raw.laz'.format(merged_dir)
            AtlassGen.mergeFiles(deliverypath,mergedRawHydroFile,'laz')

            mergedHydroShp = mergedRawHydroFile.replace('.laz','.shp')
            createBoundries(mergedRawHydroFile,mergedHydroShp,step)

        else:
            lazfiles = args.lazfiles
            merged_dir = AtlassGen.makedir(os.path.join(lazfiles,'merged').replace('\\','/'))
            mergedRawHydroFile = '{0}/merged_Hydro_voids_raw.laz'.format(merged_dir)
            AtlassGen.mergeFiles(lazfiles,mergedRawHydroFile,'laz')

            mergedHydroShp = mergedRawHydroFile.replace('.laz','.shp')
            createBoundries(mergedRawHydroFile,mergedHydroShp,step)


    if args.command == 'Step_2':
        print(args.shpfilepath)

        shpfilepath = args.shpfilepath
        demfolder = args.demfolder
        outputfolder = args.outputfolder
        shpfiles = AtlassGen.FILELIST(["*.shp"], shpfilepath)
        demfiles = AtlassGen.FILELIST(["*.asc"], demfolder)

        lazpolypath = AtlassGen.makedir(os.path.join(outputfolder, 'Laz_Poly').replace('\\','/'))
        lazpath = AtlassGen.makedir(os.path.join(outputfolder, 'DEM_LAZ').replace('\\','/'))
        hydrofolder = AtlassGen.makedir(os.path.join(outputfolder,'Zadjusted_hydro_files'))

        convert_tolaz = {}
        convert_tolaz_results = []
        cores = args.cores
        print('Converting DEM.asc to LAZ files')
        for demfile in demfiles:

            #convert to laz file and index
            path,tilename,ext = AtlassGen.FILESPEC(demfile)
            lazfile = os.path.join(lazpath,'{0}.laz'.format(tilename))
            convert_tolaz[tilename] = AtlassTask(tilename,ascTolaz,demfile,lazfile)

        p=Pool(processes=cores)   
        convert_tolaz_results=p.map(AtlassTaskRunner.taskmanager,convert_tolaz.values()) 

        #merge the laz files
        print("Merging Laz files")
        mergedlaz = os.path.join(lazpath,'merged.laz').replace('\\','/')
        AtlassGen.mergeFiles(lazpath,mergedlaz,'laz')

        print("Indexing merged file")
        AtlassGen.index(mergedlaz)

        clip_task = {}
        clip_task_results = []

        genlazinfo_task = {}
        genlazinfo_task_resilts = []
        for shpfile in shpfiles:
            path,id,ext = AtlassGen.FILESPEC(shpfile)
            
            hydrolaz = os.path.join(lazpolypath,'{0}.laz'.format(id))
            #Cut the hydro polygons in to seperate laz files
            clip_task[id] = AtlassTask(id,AtlassGen.clip,mergedlaz,hydrolaz,shpfile,'laz')

            #Generate lasinfo for each laz file
            genlazinfo_task[id] = AtlassTask(id,genLasinfo,hydrolaz)
    
        print('Clipping to polys started')
        clip_task_results=p.map(AtlassTaskRunner.taskmanager,clip_task.values()) 
        print('Generating Lazinfo for polys started')
        genlazinfo_task_resilts=p.map(AtlassTaskRunner.taskmanager,genlazinfo_task.values()) 


        ############################################################################
        attribs={}
        attribs['num_points']='  number of point records:    '
        attribs['min_xyz']='  min x y z:                  '
        attribs['max_xyz']='  max x y z:                  '

        txtfiles = AtlassGen.FILELIST(['*.txt'],lazpolypath)

        filedict1 = {}

        for file in txtfiles:
            path,name,extn=AtlassGen.FILESPEC(file)
            lazfile = os.path.join(path,'{0}.laz'.format(name)).replace('\\','/')
            filedict1[name]={}
            filedict1[name]['file']=file.replace('\\','/')
            filedict1[name]['lazfile']=lazfile  
            filedict1[name]['attribs']={}
            for attrib in attribs.keys():
                filedict1[name]['attribs'][attrib]=''
        
        ##############################################################################

        #loop through tiles and summarise key attribs
        for name in filedict1.keys():

            lines = [line.rstrip('\n')for line in open(filedict1[name]['file'])]

            for line in lines:
                for attrib in attribs.keys():
                    if attribs[attrib] in line:
                        line=line.replace(attribs[attrib] ,'')
                        line=line.strip(' ')
                        filedict1[name]['attribs'][attrib]=line
            
            minz = round(float(filedict1[name]['attribs']['min_xyz'].split(' ')[2]),3)
            maxz = round(float(filedict1[name]['attribs']['max_xyz'].split(' ')[2]),3)
            diff  = round(maxz - minz,3)

            filedict1[name]['attribs']['minz'] = minz
            filedict1[name]['attribs']['maxz'] = maxz
            filedict1[name]['attribs']['diff'] = diff

            #Move file to a different location if diff is greater than 1m for manual check
            if diff < 1.0:
                if (minz%0.50)== 0:
                    new_minz = minz-0.250
                    print('\nMin z of {0} adjusted to {1}'.format(name,new_minz))
                    filedict1[name]['attribs']['minz'] = new_minz

                lazfile = filedict1[name]['lazfile']
                print('\nClamping Polygon : {0}'.format(name))
                outputfile = os.path.join(hydrofolder,'{0}.laz'.format(name).replace('\\','/'))
                zadjust(lazfile,outputfile,minz)
            
            else:
                inputfile = filedict1[name]['lazfile']
                txtf = filedict1[name]['file']
                path,filename,ext = AtlassGen.FILESPEC(inputfile)
                manualCheckdir = AtlassGen.makedir(os.path.join(outputfolder,'ManualCheck').replace('\\','/'))
                lazfile =  os.path.join(manualCheckdir,'{0}.laz'.format(filename)).replace('\\','/')
                otxtfile = os.path.join(manualCheckdir,'{0}.txt'.format(filename)).replace('\\','/')
                filedict1[name]['lazfile']=lazfile  

                movefile(inputfile,lazfile)
                movefile(txtf,otxtfile )

                    
            print(name,filedict1[name]['attribs'])


        attribute_file = os.path.join(outputfolder,'Ploy_Summary.json')
        with open(attribute_file, 'w') as f:
            # Using vars(args) returns the data as a dictionary
            json.dump(filedict1, f)


        #Merge the hydro files to one file
        mergedfile = os.path.join(hydrofolder,'Merged_Hydro_Output.laz').replace('\\','/')
        AtlassGen.mergeFiles(hydrofolder,mergedfile,'laz')


    if args.command == 'Step_3':
        print("Clamping the polygons in Manual Check Folder after visual check.\nNOTE: minz will be used")

        lazpath = args.lazpath
        outputfolder = args.outputfolder

        hydrofolder = AtlassGen.makedir(os.path.join(outputfolder,'Zclamped_hydro_files'))

        ############################################################################
        attribs={}
        attribs['num_points']='  number of point records:    '
        attribs['min_xyz']='  min x y z:                  '
        attribs['max_xyz']='  max x y z:                  '

        txtfiles = AtlassGen.FILELIST(['*.txt'],lazpath)

        filedict1 = {}

        for file in txtfiles:
            path,name,extn=AtlassGen.FILESPEC(file)
            lazfile = os.path.join(path,'{0}.laz'.format(name)).replace('\\','/')
            filedict1[name]={}
            filedict1[name]['file']=file.replace('\\','/')
            filedict1[name]['lazfile']=lazfile  
            filedict1[name]['attribs']={}
            for attrib in attribs.keys():
                filedict1[name]['attribs'][attrib]=''
        
        ##############################################################################

        #loop through tiles and summarise key attribs
        for name in filedict1.keys():

            lines = [line.rstrip('\n')for line in open(filedict1[name]['file'])]

            for line in lines:
                for attrib in attribs.keys():
                    if attribs[attrib] in line:
                        line=line.replace(attribs[attrib] ,'')
                        line=line.strip(' ')
                        filedict1[name]['attribs'][attrib]=line
            
            minz = round(float(filedict1[name]['attribs']['min_xyz'].split(' ')[2]),3)
            maxz = round(float(filedict1[name]['attribs']['max_xyz'].split(' ')[2]),3)
            diff  = round(maxz - minz,3)

            filedict1[name]['attribs']['minz'] = minz
            filedict1[name]['attribs']['maxz'] = maxz
            filedict1[name]['attribs']['diff'] = diff

            if (minz%0.50)== 0:
                new_minz = minz-0.250
                print('\nMin z of {0} adjusted to {1}'.format(name,new_minz))
                filedict1[name]['attribs']['minz'] = new_minz

            lazfile = filedict1[name]['lazfile']
            print('\nClamping Polygon : {0}'.format(name))
            outputfile = os.path.join(hydrofolder,'{0}.laz'.format(name).replace('\\','/'))
            zadjust(lazfile,outputfile,minz)
        
        print("\nMerging Files\n")
        mergedfile = os.path.join(hydrofolder,'Merged_Hydro_Output2.laz').replace('\\','/')
        AtlassGen.mergeFiles(hydrofolder,mergedfile,'laz')



    return
    
if __name__ == "__main__":
    main() 



