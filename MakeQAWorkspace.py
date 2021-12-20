#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import os
from gooey import Gooey, GooeyParser
import subprocess
import datetime
from time import strftime
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
    parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )",default='*.laz')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default=stored_args.get('layoutfile'))
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputpath'))
    cls_type = parser.add_mutually_exclusive_group(required=True,gooey_options={'initial_selection': 0})
    cls_type.add_argument("--type1", metavar="Type 1  [classes- DEM, 3,4,9]", action='store_true')
    cls_type.add_argument("--type2", metavar="Type 2 [classes- DEM, 3,4,5,6,1,9,10,13]", action='store_true')
    cls_type.add_argument("--type3", metavar="Type 3 [classes- DEM, 3,4,5,6,1,9,10,13]", action='store_true')
    parser.add_argument("--diff", metavar="Diff - Make Tiffs to check coverage", action='store_true',default=True)
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
    parser2.add_argument("filetype", metavar="File Type",help="input filetype (laz/las)", default='laz')
    parser2.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=stored_args.get('cores'))

    args = main_parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

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


def maketiffile(tilename, input, output, classN, step, prjfile,classdir):
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-o' , output, '-otif', '-nbits', 32, '-elevation_highest', '-step', step, '-keep_class', classN] 
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
            '''
            #removed as 1kb files are not the cause of GM crash.
            #print(os.path.getsize(output)) 
            if os.path.getsize(output) <= 500:
                os.remove(output)
                print('Deleted {0} : less the 500B'.format(output))
                log ='Deleted {0} : less the 500B'.format(output)
            else:
                log = 'Making tif file was successful for {0}'.format(input)
            return (True,output, log)
            '''
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

def checkfiles(tilename,orifile,recfile,outputdir, filetype):

    print('Working with {0}'.format(tilename))

    orilasinfofile = genLasinfo(orifile,tilename,outputdir,filetype,'ori')
    reclasinfofile = genLasinfo(recfile,tilename,outputdir,filetype,'rec')
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


    #file1
    lines1=[line.rstrip('\n')for line in open(orilasinfofile)]
    lines2=[line.rstrip('\n')for line in open(reclasinfofile)]

    filedict1=OrderedDict()
    for line in lines1:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict1[attrib]=line

    filedict2=OrderedDict()
    for line in lines2:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict2[attrib]=line

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
            return(True,report,log)
        else:
            return(False,None,'No issue')




def genLasinfo(lazfile,tilename,outputdir,filetype,key):
  
    #genLasinfo(lazfile)
    lasinfofile = os.path.join(outputdir,'{0}_{1}.txt'.format(tilename,key)).replace("\\","/")

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

    if args.command == 'GMQA':
        inputfolder=args.inputfolder
        filepattern = args.filepattern.split(';')
        zone = args.zone
        lasfiles = AtlassGen.FILELIST(filepattern, inputfolder)

    
        tilelayoutfile = args.layoutfile
        outpath = args.outputpath.replace('\\','/')
        #hydrofiles = args.hydrofiles
        #aoi = args.aoi
        step = args.step
        makediff = args.diff
    
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
        rgb_colors[13] = '255,0,128'

        if args.type1:
            classes = [2,3,4,9]

        if args.type2:
            classes = [2,3,4,5,6,1,9,10,13]

        if args.type3:
            classes = [2,3,4,5,6,1,9,10,13]

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

        if args.onlymapC:
            qatifdir = inputfolder
            workingdir = inputfolder.replace('qa','')

        if args.datum == 'D_AUSTRALIAN_1984':
            proj_name = "AMG_ZONE{0}_AUSTRALIAN_GEODETIC_1984".format(zone)
            epsg = 20300 + int(zone)
            prjfile = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))

        if args.datum == 'D_AUSTRALIAN_1966':
            proj_name = "AMG_ZONE{0}_AUSTRALIAN_GEODETIC_1966".format(zone)
            epsg = 20200 + int(zone)
            prjfile = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))

        if args.datum == 'GDA94':
            proj_name = "MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994".format(zone)
            epsg = 28300 + int(zone)
            prjfile = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))


        if args.datum == 'GDA2020':
            proj_name = "MGA_ZONE{0}_GDA_2020_AUSTRALIAN_GEODETIC_2020".format(zone)
            epsg = 7800 + int(zone)
            prjfile = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            if not os.path.isfile(prjfile):
                prjfile = None
                print("PRJ file could not be found for EPSG : {0}".format(epsg))


        print('EPSG : {0}'.format(epsg))
        print(proj_name)
        
        projfile = os.path.join(workingdir, 'workspace.prj').replace("\\", "/")
        shutil.copy(prjfile,projfile)

        tl_in = AtlassTileLayout()
        tl_in.fromjson(tilelayoutfile)
        #Make TIF Files
        mk_tif_tasks = {}
        mk_diff_tasks = {}
        mk_dem_tasks = {}

        if not args.onlymapC:
                
            for cl in classes:
                classdir = AtlassGen.makedir(os.path.join(qatifdir, 'Class_{0}'.format(str(cl))).replace('\\','/'))
                print('Making tifs for class {0}'.format(str(cl)))
                for tile in tl_in:
                    filename = tile.name
                    lasfile = os.path.join(inputfolder, '{0}.laz'.format(filename)).replace('\\','/')
            
                    #file
                    input = lasfile
                    output = os.path.join(classdir,'{0}_{2}.{1}'.format(filename,'tif',cl)).replace('\\','/')

                    path, filename, ext = AtlassGen.FILESPEC(lasfile)
                    mk_tif_tasks[filename] = AtlassTask(filename, maketiffile, filename, input, output, cl, step, projfile, classdir)        
                    
                
                p=Pool(processes=cores)      
                mk_tif_results=p.map(AtlassTaskRunner.taskmanager,mk_tif_tasks.values())
            
            prjdir = AtlassGen.makedir(os.path.join(DEMdir,'makeGRID_output/DEM').replace('\\','/'))      

            for tile in tl_in:
                filename = tile.name
                lasfile = os.path.join(inputfolder, '{0}.laz'.format(filename)).replace('\\','/')
                outputfilename = filename                                               #tilename,inputdir,outputdir,workingdir,hydropoints,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,gndclass,buffer,kill,step,clipp,aois
                mk_dem_tasks[filename] = AtlassTask(filename, DEMClass.makeDEMperTile, filename,inputfolder,DEMdir,DEMdir,None,tilelayoutfile,tilelayoutfile,'laz',outputfilename,[2,8],250,200,step,False,'')

                prjfile2 = os.path.join(prjdir,'{0}.prj'.format(filename)).replace('\\','/')
                shutil.copyfile(projfile, prjfile2) 
            p=Pool(processes=cores)      
            mk_dem_results=p.map(AtlassTaskRunner.taskmanager,mk_dem_tasks.values())

            if makediff:
                print('Making tifs for diff')
                diff_path = AtlassGen.makedir(os.path.join(qatifdir,"diff").replace('\\','/'))
                for tile in tl_in:
                    filename = tile.name
                    lasfile = os.path.join(inputfolder, '{0}.laz'.format(filename)).replace('\\','/') 
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
            

            DEMdir = os.path.join(DEMdir, 'makeGRID_output/DEM').replace('/','\\')
            gmcfile = os.path.join(DEMdir, 'dem.gmc').replace('/','\\')
            gmsfile = os.path.join(gms_path,'dem.gms').replace('\\','/')
            mk_gmsfiles_tasks['dem'] = AtlassTask('dem', makegmsfiles,DEMdir,gmcfile,gmsfile, args.zone, args.datum, args.projection,'asc')

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




            #Verify final results
            #for result in run_gmsfiles_results:
                #print(result.result, result.log)
        
            #Generate the gm workspace
            
    
            gmwfile = os.path.join(workingdir, 'workspace.gmw').replace("\\", "/")
            
    
            workspc = 'GLOBAL_MAPPER_SCRIPT VERSION="1.00" \nSET_BG_COLOR COLOR="RGB(255,255,255)" \nUNLOAD_ALL'
            for i in range(len(classes)):
                classno = classes[i]
                workspc = workspc+'\nDEFINE_SHADER SHADER_NAME="class{0}" BLEND_COLORS="YES" STRETCH_TO_RANGE="NO" SHADE_SLOPES="NO" SLOPES_PERCENT="NO" OVERWRITE_EXISTING="NO" \n0,RGB({1})\nEND_DEFINE_SHADER'.format(classno,rgb_colors[classno] )


            workspc = workspc + '\nIMPORT FILENAME="qa/DEM/makeGRID_output/DEM/dem.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,25000.000,0.0000000000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="Atlas Shader"'.format(DEMdir)
            

            for i in range(len(classes)):
                classno = classes[i]
                workspc = workspc + '\nIMPORT FILENAME="qa/Class_{1}/Class_{1}.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,250000.000,0.0000000000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="class{1}"'.format(qatifdir,classno)
            
            if makediff:
                diff_path = os.path.join(qatifdir,"diff").replace('/','\\')
                workspc = workspc + '\nIMPORT FILENAME="qa/diff/diff.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="SCALE,250000.000,10000.0000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="Atlas Shader"'.format(diff_path)
            
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
            SET_VERT_DISP_OPTS SHADER_NAME="Atlas Shader" AMBIENT_LIGHT_LEVEL="0.0000000000" VERT_EXAG="3.0000000" \
                LIGHT_ALTITUDE="45.000000" LIGHT_AZIMUTH="45.000000" LIGHT_NUM_SOURCES="1" LIGHT_BLENDING_ALGORITHM="0" \
                ENABLE_HILL_SHADING="YES" SHADE_DARKNESS="0" SHADE_HIGHLIGHT="0" ENABLE_WATER="NO" \
                WATER_ALPHA="128" WATER_LEVEL="0.0000000000" WATER_COLOR="RGB(0,0,255)"

            /************ DEFINE MAP LAYOUT *************/
            MAP_LAYOUT
            ElevLegendBgColor=16777215
            ElevLegendTranslucency=384
            ElevLegendFont=~0~534799372~0.000~0~0~16777215
            ElevLegendVisible=1
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

    if args.command == 'CHECKFILES':

        originalpath = args.ori_path
        recievedpath = args.rec_path
        outputpath = args.outputpath
        tilelayoutfile = args.layoutfile
        cores = args.cores
        filetype = args.filetype

        orilasfiles = AtlassGen.FILELIST(['*.{0}'.format(filetype)], originalpath)

        checkfiles_tasks = {}
        
        for of in orilasfiles:
            
            path,filename,ext = AtlassGen.FILESPEC(of)
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
        for result in mk_gmsfiles_results:
            #print(result.success, result.log)

            if result.success:
                f.write(result.log)


        f.close()       

    return

if __name__ == "__main__":
    main()       

