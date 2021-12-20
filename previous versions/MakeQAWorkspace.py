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
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make QA", use_legacy_titles=True, required_cols=1, default_size=(1120,920))
def param_parser():
    parser=GooeyParser(description="Make Contour")
    parser.add_argument("inputfolder", metavar="LAS file Folder", widget="DirChooser", help="Select las file folder", default='')
    parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.laz')
    load_group = parser.add_argument_group("Load files", "These files are loaded to the workspace if selected", gooey_options={'show_border': True,'columns': 2})
    load_group.add_argument("-layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default='')
    load_group.add_argument("-aoi", metavar="AOI", widget="FileChooser", help="Area of interest(.shp file)", default="")
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    classes_group = parser.add_argument_group("Classes", "Select the classes  required for QA", gooey_options={'show_border': True,'columns': 15})
    classes_group.add_argument("-c1", metavar="1", action='store_true')
    classes_group.add_argument("-c2", metavar="2", action='store_true')
    classes_group.add_argument("-c3", metavar="3", action='store_true')
    classes_group.add_argument("-c4", metavar="4", action='store_true')
    classes_group.add_argument("-c5", metavar="5", action='store_true')
    classes_group.add_argument("-c6", metavar="6", action='store_true')
    classes_group.add_argument("-c7", metavar="7", action='store_true')
    classes_group.add_argument("-c8", metavar="8", action='store_true')
    classes_group.add_argument("-c9", metavar="9", action='store_true')
    classes_group.add_argument("-c10", metavar="10", action='store_true')
    classes_group.add_argument("-c13", metavar="13", action='store_true')
    classes_group.add_argument("-mine", metavar="Mine Site", action='store_true')
    classes_group.add_argument("-all", metavar="All", action='store_true')
    parser.add_argument("datum", metavar="Datum",choices=['AMG84','AMG66','MGA94'], default='MGA94')
    parser.add_argument("zone", metavar="UTM Zone", choices=['50','51','52','53','54','55','56'])
    parser.add_argument("step", metavar="Step for lasgrid", type=float, default=0.5)
    parser.add_argument("gmexe", metavar="Global Mapper EXE", widget="FileChooser", help="Location of Global Mapper exe", default="C:\\Program Files\\GlobalMapper16.0_64bit_crack\\global_mapper.exe")
    parser.add_argument("-workspace", metavar="Create Global Mapper workspace", action='store_true')
    parser.add_argument("-onlymapC", metavar="Create only the map catalogs(TIFs must be available", action='store_true')
    parser.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=4)

    return parser.parse_args()

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def makegmsfiles(input_dir,gmcfile,gmsfiles, zone, datum):

    template = "\\\\10.10.10.100\\projects\\PythonScripts\\templates\\Template_MapCatalog.gms"
    dstfile = gmsfiles
    copyfile(template, dstfile)
    log = ''

    try:
        with open(dstfile, 'r') as g:
            data = g.read()

            while '<gmcfile>' in data:
                data = data.replace('<gmcfile>', gmcfile)
            while '<input_dir>' in data:
                data = data.replace('<input_dir>', input_dir)
            while '<gmsfiles>' in data:
                data = data.replace('<gmsfiles>', gmsfiles)
            while '<zone>' in data:
                data = data.replace('<zone>', zone)
            while '<datum>' in data:
                data = data.replace('<datum>', datum)    
            
        with open(dstfile, 'w') as f:
                f.write(data)
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


def maketiffile(input, output, classN, step ):
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-o' , output, '-otif', '-nbits', 32, '-elevation_highest', '-step', step, '-keep_class', classN] 
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', input, '-o' , output.replace('.tif','_lowres.laz'), '-olaz', '-nbits', 32, '-elevation_highest', '-step', step*10, '-keep_class', classN] 
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)        

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make tif for {0}, Failed at Subprocess'.format(input)  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'Making tif file was successful for {0}'.format(input)
            return (True,output, log)

        else:
            log = 'Could not make tif file for {0}'.format(input)   
            return (False,None, log)



   
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()

    inputfolder=args.inputfolder
    filepattern = args.filepattern.split(';')
    zone = args.zone
    lasfiles = AtlassGen.FILELIST(filepattern, inputfolder)

 
    tilelayoutfile = args.layoutfile
    outpath = args.outputpath.replace('\\','/')
    #hydrofiles = args.hydrofiles
    aoi = args.aoi
    step = args.step

 
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

    if args.c1:
        classes.append(1)
    if args.c2:
        classes.append(2)
    if args.c3:
        classes.append(3)
    if args.c4:
        classes.append(4)
    if args.c5:
        classes.append(5)
    if args.c6:
        classes.append(6)
    if args.c7:
        classes.append(7)
    if args.c8:
        classes.append(8)
    if args.c9:
        classes.append(9)
    if args.c10:
        classes.append(10)
    if args.c13:
        classes.append(13)
    if args.all:
        classes = [1,2,3,4,5,6,9,10,13]
    if args.mine:
        classes = [1,2,7,9]
 
    cores = args.cores


    print(tilelayoutfile, aoi)
    print('Classes selected for QA {0}: '.format(classes))

    if not args.onlymapC:
        if not lasfiles:
            print("Please select the correct file type", "No Selected files")
            exit()

        dt = strftime("%y%m%d_%H%M")
    
        workingdir = AtlassGen.makedir(os.path.join(outpath, (dt+'_QAWorkspace')).replace('\\','/'))
        qatifdir = AtlassGen.makedir(os.path.join(workingdir, 'qa').replace('\\','/'))

    else:
        qatifdir = inputfolder
        workingdir = inputfolder

    #Make TIF Files
    mk_tif_tasks = {}
    
    if not args.onlymapC:
        for cl in classes:
            classdir = AtlassGen.makedir(os.path.join(qatifdir, 'Class_{0}'.format(str(cl))).replace('\\','/'))
            print('Making tifs for class {0}'.format(str(cl)))
            for lasfile in lasfiles:
                path, filename, ext = AtlassGen.FILESPEC(lasfile)
        
                #file
                input = lasfile
                output = os.path.join(classdir,'{0}.{1}'.format(filename,'tif')).replace('\\','/')

                mk_tif_tasks[filename] = AtlassTask(filename, maketiffile, input, output, cl, step)        
            
            p=Pool(processes=cores)      
            mk_tif_results=p.map(AtlassTaskRunner.taskmanager,mk_tif_tasks.values())

    if args.workspace:
        #Make GMS files for Map Catalog for 
        gms_path = AtlassGen.makedir(os.path.join(workingdir, 'gm_scripts').replace('\\','/'))
        mk_gmsfiles_tasks = {}
        for cl in classes:
            cl = str(cl)
            input_dir = os.path.join(qatifdir, 'Class_{0}'.format(cl)).replace('/','\\')
            gmcfile = os.path.join(input_dir, 'Class_{0}.gmc'.format(cl)).replace('/','\\')
            gmsfile = os.path.join(gms_path,'Class_{0}.gms'.format(cl)).replace('\\','/')
            print(gmcfile, gmsfile, input_dir)
            mk_gmsfiles_tasks[cl] = AtlassTask(cl, makegmsfiles,input_dir,gmcfile,gmsfile, args.zone, args.datum)
            
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

        gmwfile = os.path.join(workingdir, 'workspace.gmw')
        workspc = 'GLOBAL_MAPPER_SCRIPT VERSION="1.00" FILENAME="{0}" \nSET_BG_COLOR COLOR="RGB(255,255,255)" \nUNLOAD_ALL'.format(gmwfile)
        for i in range(len(classes)):
            classno = classes[i]
            workspc = workspc+'\nDEFINE_SHADER SHADER_NAME="class{0}" BLEND_COLORS="YES" STRETCH_TO_RANGE="NO" SHADE_SLOPES="NO" SLOPES_PERCENT="NO" OVERWRITE_EXISTING="NO" \n0,RGB({1})\nEND_DEFINE_SHADER'.format(classno,rgb_colors[classno] )


        for i in range(len(classes)):
            classno = classes[i]
            workspc = workspc + '\nIMPORT FILENAME="{0}\\Class_{1}\\Class_{1}.gmc" TYPE="GLOBAL_MAPPER_CATALOG" \\ \nLABEL_FIELD_FORCE_OVERWRITE="NO" ZOOM_DISPLAY="PERCENT,0.90000000,0.0000000000" \\ \nLIDAR_DRAW_MODE_GLOBAL="YES" LIDAR_DRAW_MODE="ELEV" LIDAR_POINT_SIZE="0" LIDAR_DRAW_QUALITY="50" \\ \nSAMPLING_METHOD="BILINEAR" CLIP_COLLAR="NONE" SHADER_NAME="class{1}"'.format(qatifdir,classno)
        
        workspc = workspc + '''\nDEFINE_PROJ PROJ_NAME="MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994"
Projection     MGA (Map Grid of Australia)
Datum          GDA94
Zunits         NO
Units          METERS
Zone           {0}
Xshift         0.000000
Yshift         0.000000
Parameters
END_DEFINE_PROJ
IMPORT FILENAME="{1}" TYPE="GEOJSON" PROJ_NAME="MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994" \
	 LABEL_FIELD_FORCE_OVERWRITE="NO" LOAD_FLAGS="0"
IMPORT FILENAME="{2}" TYPE="SHAPEFILE" PROJ_NAME="MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994" \
	 ELEV_UNITS="METERS" LABEL_FIELD_FORCE_OVERWRITE="YES" LABEL_FIELD_SEP="0x20" LABEL_FIELD="NAME" \
	 CODE_PAGE="65001"
LOAD_PROJECTION PROJ_NAME="MGA_ZONE{0}_GDA_94_AUSTRALIAN_GEODETIC_1994"
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

END_MAP_LAYOUT'''.format(zone, tilelayoutfile, aoi )




        f = open(gmwfile, 'w')
        f.write(workspc)  
        f.close()    

    return

if __name__ == "__main__":
    main()       

