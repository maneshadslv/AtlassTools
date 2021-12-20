import sys
import shutil
import time
import os, glob
import subprocess 
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeDEMLib_Valeria import *



@Gooey(program_name="Valeria prod Generator", use_legacy_titles=True, required_cols=1, default_size=(1000,820))
def param_parser():
    parser=GooeyParser(description="Valeria Prod Gen tool")
    parser.add_argument("input_folder", metavar="Input Directory ", widget="DirChooser", help="Select folder with input files")
    parser.add_argument("output_dir", metavar="Output Directory", widget="DirChooser", help="Output directory")
    parser.add_argument("workingpath", metavar="working Directory", widget="DirChooser", help="working directory")
    parser.add_argument("inputtilelayoutfile", metavar="Input TileLayout file", widget="FileChooser", help="TileLayout file(.json)")
    parser.add_argument("-hydropoints", metavar="Hydropoints file", widget="FileChooser", help=".laz file")
    parser.add_argument("aoi", metavar="AOI file", widget="FileChooser", help=".shp file")
    parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)

    return parser.parse_args()
def clip(input, output, poly, filetype):

    if isinstance(input,str):
        input = [input]
    log=''
    try:
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' ] + input + [ '-merged', '-poly', poly, '-o', output, '-o{0}'.format(filetype)]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        if os.path.isfile(output):
            log = "Clipping {0} output : {1}".format(str(input), str(output)) 
            return (True,output, log)

        else:
            log = "Clipping failed for {0}. ".format(str(input)) 
            return (False,None,log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Clipping failed for {0}. Failed at Subprocess ".format(str(input)) 
        return(False, None, log)

def ApplyVLR(lazfile,inputdir,vlrdir):
    os.chdir(inputdir)
    log = ''
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-odir',vlrdir,'-load_vlrs' ,'-olaz'] 
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

def MakeProducts(tile, inputfile, inputfolder,outputdir,workingdir,aoi,inputtilelayoutfile, outputtilelayoutfile,hydropoints):

    tilename = tile.name

    nongroundclasses = [1,3,4,5,6,9,10,11,12,13,14,15,16,17,18,19,20]
    #print(inputfile)
    clipped_dir = os.path.join(workingdir,'clipped').replace('\\','/')
    clipped_laz = os.path.join(clipped_dir,'{0}.laz'.format(tilename))
    lasdir = AtlassGen.makedir(os.path.join(outputdir,'LAS_1.2\\Clipped_1000m').replace('\\','/'))
    LASfile = os.path.join(lasdir,'{0}.las'.format(tilename))

    vlr_applied_dir = AtlassGen.makedir(os.path.join(workingdir,'vlr_applied').replace('\\','/'))
    vlr_applied_file = os.path.join(vlr_applied_dir,'{0}.laz'.format(tilename))
    gnd_dir = AtlassGen.makedir(os.path.join(outputdir,'GROUND_XYZ\\Clipped_1000m').replace('\\','/'))
    grndfile = os.path.join(gnd_dir,'{0}.xyz'.format(tilename))
    nongrnd_dir = AtlassGen.makedir(os.path.join(outputdir,'NON_GROUND_XYZ\\Clipped_1000m').replace('\\','/'))
    nongrndfile = os.path.join(nongrnd_dir,'{0}.xyz'.format(tilename))
    DEMdir = outputdir
    demfilename = tilename
    DEMworkdir = workingdir
    DSMdir = outputdir
    dsmfilename = tilename
    DSMworkdir = workingdir

    cleanup = [clipped_laz,vlr_applied_file]


    try:
        clip(inputfile,clipped_laz,aoi,'laz')

        if os.path.exists(clipped_laz):
            ApplyVLR(clipped_laz,clipped_dir,vlr_applied_dir)    
            
            #Apply global length value#
            '''
            print('Generating LAS 1.2')
            subprocessargs=['C:/LAStools/bin/lasinfo', '-i',vlr_applied_file,'-set_global_encoding', 1, '-set_version', 1.2,'-o',LASfile ,'-olas']
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            '''

            
            print('Generating LAS 1.2')
            subprocessargs=['C:/LAStools/bin/las2las', '-i',vlr_applied_file,'-set_version', 1.2,'-o',LASfile ,'-olas']
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            
            
            #generate Ground only#
            print('Generating GND file')
            subprocessargs=['C:/LAStools/bin/las2las', '-i',clipped_laz, '-o',grndfile ,'-oparse', 'xyz','-keep_class',2, '-otxt']
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            #generate Ground only#
            print('Generating Non GND file')
            subprocessargs=['C:/LAStools/bin/las2las', '-i',clipped_laz, '-o',nongrndfile, '-oparse', 'xyz', '-otxt','-keep_class'] + nongroundclasses
            subprocessargs=subprocessargs
            subprocessargs=list(map(str,subprocessargs))    
            #print(subprocessargs)
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            #Making DEM
            print('Making DEM')
            DEMClass.makeDEMperTile(tilename,inputfolder,DEMdir,DEMworkdir,[hydropoints],inputtilelayoutfile,outputtilelayoutfile,'laz',demfilename,[2,8],250,200,1.0,True,[aoi])
                                    #tilename,inputdir,outputdir,workingdir,hydropoints,inputgeojsonfile,outputgeojsonfile,filetype,outputfilename,gndclass,buffer,kill,step,clipp,aois

            #Make DSM
            print('Making DSM')
            res = DSMClass.makeDSMperTile(tilename,inputfolder,DSMdir,DSMworkdir,inputtilelayoutfile,outputtilelayoutfile,'laz',dsmfilename,nongroundclasses,250,200,1.0,True,[aoi])
            return (res[0],res[1],res[2])

        else:
            return (True,None,'Outside AOI : {0}'.format(tilename))


    except subprocess.CalledProcessError as suberror:
        log='\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)
    
    finally:

        if os.path.isfile(nongrndfile):
            for cleanfile in cleanup:
                os.remove(cleanfile)
            return (True,nongrndfile,'true')


        else:
            return(False,None,"Failed to gen products for {0}".format(tilename))
    

def main():

    freeze_support()

    args = param_parser()

    print("Program Starting \n")
    intputfolder = args.input_folder.replace('\\','/')
    outputfolder = args.output_dir.replace('\\','/')
    workingpath = args.workingpath.replace('\\','/')
    inputtilelayoutfile = args.inputtilelayoutfile.replace('\\','/')
    if not args.hydropoints == None:
        hydropoints = args.hydropoints.replace('\\','/')
    else:
        hydropoints = None
    aoi = args.aoi.replace('\\','/')
    cores = args.cores



    lasfilepattern = '*.{0}'.format('laz')
    lasfilepattern = lasfilepattern.split(';')
    files = AtlassGen.FILELIST(lasfilepattern, intputfolder)

    tilelayout_in = AtlassTileLayout()
    tilelayout_in.fromjson(inputtilelayoutfile)

    dt = strftime("%y%m%d_%H%M")




    outputdir = AtlassGen.makedir(os.path.join(outputfolder, 'Valeria_prods_{0}'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, 'Valeria_prods_working_{0}'.format(dt))).replace('\\','/')


        
    clipped_dir = AtlassGen.makedir(os.path.join(workingdir,'clipped').replace('\\','/'))
    vlrsource = "Z:/PythonScripts/VLR_Headers/GDA2020/55/AHD/GDA2020_55_AHD.vlr"
    vlrtarget = os.path.join(clipped_dir,'vlrs.vlr')
    copyfile(vlrsource, vlrtarget)

    makeproducts_tasks = {}

    print('No of Tiles in the input folder : {0}'.format(len(files)))
    print('No of Tile in the Tilelayout : {0}'.format(len(tilelayout_in)))

    for tile in tilelayout_in: 
        tilename = tile.name
        inputfile = os.path.join(intputfolder,'{0}.{1}'.format(tilename,'laz'))
        
        makeproducts_tasks[tilename] = AtlassTask(tilename, MakeProducts, tile, inputfile, intputfolder,outputdir,workingdir,aoi,inputtilelayoutfile, inputtilelayoutfile,hydropoints)


    p=Pool(processes=cores)      
    results=p.map(AtlassTaskRunner.taskmanager,makeproducts_tasks.values())

   

    print("\n\nProgram finished")

if __name__ == "__main__":
    main()         
