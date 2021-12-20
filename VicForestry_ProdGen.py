import sys
import shutil
import time
import os, glob
import subprocess 
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *



@Gooey(program_name="Vicforestry prod Generator", use_legacy_titles=True, required_cols=1, default_size=(1000,820))
def param_parser():
    parser=GooeyParser(description="Vicforestry prod Generator")
    parser.add_argument("input_folder", metavar="Input Directory ", widget="DirChooser", help="Select folder with input files")
    parser.add_argument("tilelayoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)")
    parser.add_argument("output_dir", metavar="Output Directory", widget="DirChooser", help="Output directory")
    parser.add_argument("workingpath", metavar="working Directory", widget="DirChooser", help="working directory")
    parser.add_argument("geoid", metavar="GEOID", widget="FileChooser", help="laz file")
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument('--name', metavar="AreaName", help="Project Area Name Used for Naming Convention,  \neg : AreaName2020_C2_xxxxxx_yyyyyyy.las ", default="")
    parser.add_argument('--year', metavar="Year of Survey", help="Year of Survey  Naming Convention,  \neg : AreaName2020_C2_xxxxxx_yyyyyyy.las ", default="")
    parser.add_argument("epsg", metavar="EPSG", type=int, default=7855)
    parser.add_argument("hz", metavar="hz", help="Provide maximum horizontal distance", default=20, type=int)
    parser.add_argument("vt", metavar="vt", help="Provide vertical accuracy requirement", default=0.10, type=float) 
    parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)

    return parser.parse_args()

def copyfile(input, output):

    try:
        shutil.copyfile(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            log = "Copying file for {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Copying file for {} Failed".format(input)
            return (False,output, log)
       
def shiftlas(inputf, outputf,dz):

    log = ''

    try:
        #Las2las -i *.laz -olaz -odir xyz_adjusted -translate_xyz 1.50 2.80 0.00
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',inputf,'-olaz','-o',outputf,'-translate_xyz', 0.0, 0.0, dz ] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nShifting {0} \n Exception {1}".format(inputf, e)
        return(False,None, log)

    finally:
        if os.path.isfile(outputf):
            log = '\nShifting completed for {0}'.format(outputf)
            return (True, outputf, log)
        else:
            log ='\nShifting {} Failed'.format(outputf)
            return (False, None, log)

def MakeMKPnflagoverlap(tile, inputfile, intputfolder,outputdir,workingdir,vt,hz,filetype,areaname,year,epsg,geoid):

    tilename = tile.name

    print(inputfile)
    geoidappfile = os.path.join(workingdir,'{0}_geoapp.laz'.format(tilename))
    mkpfile = os.path.join(workingdir,'{0}_MKP.las'.format(tilename))
    temp1 = os.path.join(workingdir,'{0}_temp1.las'.format(tilename))
    temp = os.path.join(workingdir,'{0}_temp.las'.format(tilename))
    pt1 = os.path.join(workingdir,'{0}_pt1.las'.format(tilename))
    pt2 = os.path.join(workingdir,'{0}_pt2.las'.format(tilename))
    pt3 = os.path.join(workingdir,'{0}_pt3.las'.format(tilename))
    cleanup = [geoidappfile,mkpfile,temp1,temp,pt1,pt2,pt3]
    outputfile = os.path.join(workingdir,'{0}.las'.format(tilename))

    try:
        subprocessargs=['C:/LAStools/bin/lasheight.exe','-i',inputfile,'-o',geoidappfile,'-olaz','-ground_points',geoid,'-all_ground_points','-replace_z']
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/lasthin64.exe','-i',geoidappfile,'-olas','-adaptive',vt,hz,'-classify_as', 8,'-o',mkpfile,'-ignore_class', 0 ,1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
    
    except subprocess.CalledProcessError as suberror:
        log='\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)
    
    finally:

        if os.path.isfile(mkpfile):

            subprocessargs=['C:/LAStools/bin/las2las', '-i',mkpfile, '-set_point_type', 6, '-o',temp1 , '-olas']
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        
        else:
            print('here')
            subprocessargs=['C:/LAStools/bin/las2las', '-i',geoidappfile, '-set_point_type', 6, '-o',temp1 , '-olas']
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)


        subprocessargs=['C:/LAStools/bin/las2las', '-i', temp1, '-set_version', 1.4, '-o', temp, '-olas']
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i',temp, '-keep_scan_angle', -15, 15, '-o', pt1, '-set_version', 1.4, '-set_point_type', 6, '-olas']
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/las2las', '-i', temp, '-keep_scan_angle', -65, -16, '-o', pt2, '-set_overlap_flag', 1, '-set_version', 1.4, '-set_point_type', 6, '-olas']
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/las2las', '-i', temp, '-keep_scan_angle', 16, 65, '-o', pt3, '-set_overlap_flag', 1, '-set_version', 1.4, '-set_point_type', 6, '-olas']
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))  
        print(subprocessargs)  
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        subprocessargs=['C:/LAStools/bin/las2las', '-i', pt1, pt2, pt3, '-merged', '-o', outputfile, '-set_version', 1.4, '-set_point_type', 6, '-olas']
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin,tile.ymin,tile.xmax,tile.ymax)
        keep=keep.split()


        cleanup.append(outputfile)
        subprocessargs=['C:/LAStools/bin/laszip', '-i',outputfile , '-odir', outputdir,'-olaz'] + keep
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        if os.path.exists(outputfile):
            for ifile in cleanup:
                if os.path.isfile(ifile):
                    os.remove(ifile)
            return(True,outputfile,'MKP and Flag Complete for {0}'.format(tilename))
        
        else:
            return(False,None,"Failed {0}".format(tilename))
    

def main():

    freeze_support()

    args = param_parser()

    print("Program Starting \n")
    intputfolder = args.input_folder.replace('\\','/')
    outputfolder = args.output_dir.replace('\\','/')
    workingpath = args.workingpath.replace('\\','/')
    filetype = args.file_type
    areaname = args.name
    year = args.year
    epsg = args.epsg
    cores = args.cores
    tilelayoutfile = args.tilelayoutfile
    hz=args.hz
    vt=args.vt
    geoid = args.geoid

    lasfilepattern = '*.{0}'.format(filetype)
    lasfilepattern = lasfilepattern.split(';')
    files = AtlassGen.FILELIST(lasfilepattern, intputfolder)

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)

    dt = strftime("%y%m%d_%H%M")

 
    outputdir = AtlassGen.makedir(os.path.join(outputfolder, 'prods_{0}'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, 'prods_working_{0}'.format(dt))).replace('\\','/')
    make_mkp_tasks = {}

    print('No of Tiles in the input folder : {0}'.format(len(files)))
    print('No of Tile in the Tilelayout : {0}'.format(len(tilelayout)))

    for tile in tilelayout: 
        tilename = tile.name
        inputfile = os.path.join(intputfolder,'{0}.{1}'.format(tilename,filetype))
        
        make_mkp_tasks[tilename] = AtlassTask(tilename, MakeMKPnflagoverlap, tile, inputfile,intputfolder, outputdir,workingdir,vt,hz,filetype,areaname,year,epsg,geoid)


    p=Pool(processes=cores)      
    results=p.map(AtlassTaskRunner.taskmanager,make_mkp_tasks.values())

    failed = 0

    for result in results:
        if not result.success:
            failed +=1
            print('File {0} could not be copied'.format(result.name))

    print("\n\nProgram finished with {0} failures".format(failed))

if __name__ == "__main__":
    main()         
