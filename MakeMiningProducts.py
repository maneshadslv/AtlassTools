#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import os
from gooey import Gooey, GooeyParser
import subprocess
import datetime
from time import strftime
import shutil 
import math
import glob
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeContoursLib import *
#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make Mining Products", use_legacy_titles=True, required_cols=1, default_size=(1000,800))
def param_parser():

    
    globalmapperexe = glob.glob('C:\\Program Files\\'+'GlobalMapper2*')
    globalmapperexe = '{0}\\global_mapper.exe'.format(globalmapperexe[0])
    print(globalmapperexe)

    parser=GooeyParser(description="Make standard products for mine sites.\nThis tool will make MKP text files, embossed image for multiple clipping boundaries for mining clients.")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    filter_parser = sub_pars.add_parser('Filter_LAZ_Files', help='Prepares the las files for contours by filtering')
    filter_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input fodler containing (.las/.laz)", default='')
    filter_parser.add_argument("filepattern",metavar="Input File Pattern", help="Provide a file pattern seperated by ';' for multiple patterns (*.laz or 123*_456*.laz;345*_789* )", default='*.laz')
    filter_parser.add_argument("inputshpfolder", metavar="Input clipping shapefile folder", widget="DirChooser", help="Select input fodler containing (.shp)", default='')
    filter_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    filter_parser.add_argument("TL", metavar="Tilelayout", widget="FileChooser", help="tilelayout.json", default="")
    filter_parser.add_argument("MKP_vt", metavar="vertical thinning tol", help="Provide vt thinning param", default='0.1')
    filter_parser.add_argument("MKP_hz", metavar="horizontal thinning tol", help="Provide hz thinning param", default='20')
    filter_parser.add_argument("emboss_step", metavar="emboss step size", help="Provide pixel size of emboss image", default='1.0')
    
    filter_parser.add_argument("-cores",metavar="Cores", help="No of cores to run", type=int, default=8)


    return parser.parse_args()

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


def convert2TXT(inputlas,tilename,output):
    log =''

    try:
        subprocessargs=['C:/LAStools/bin/las2txt64.exe','-i',inputlas,'-keep_class',2,'-rescale',0.001,0.001,0.001,'-o',output]
        subprocessargs=list(map(str,subprocessargs))
        #print(list(subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except:
        log = 'Could not make countours {0}, Failed at Subprocess'.format(tilename)  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'Making Contours was successful for {0}'.format(tilename)
            return (True,output, log)

        else:
            log = 'Could not make contours for {0}'.format(tilename)   
            return (False,None, log)

def txt2las(input,tilename,output):
    print(input)
    log =''

    try:
        subprocessargs=['C:/LAStools/bin/las2las64.exe','-i',input,'-olaz','-o',output]
        subprocessargs=list(map(str,subprocessargs))
        #print(list(subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except:
        log = 'Could not make countours {0}, Failed at Subprocess'.format(tilename)  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'Making Contours was successful for {0}'.format(tilename)
            return (True,output, log)

        else:
            log = 'Could not make contours for {0}'.format(tilename)   
            return (False,None, log)

def filterFile(input,output,interval,buff,flatten):

    #myfile="W:/processing/test/756000_7462000.txt"  ## ground only laz converted to xyz - input
    #myfile2="W:/processing/test/756000_7462000_filter_15cm.txt" #-output
    #interval=0.5 #-contour_interval
    #buff=0.15 #-filtervalue (must not be more than 30% of interval)
    #flatten=True #-flatten user input to flatten points between intervals's

    count=0 
    with open(output,'w') as f:

        lines = [line.rstrip('\n')for line in open(input)]
        #print(len(lines))
        for line in lines:
            count=count+1
            #if count%100000==0:
                #print(count)
            x,y,z=line.split()
            x,y,z=float(x),float(y),float(z)
            b=z%interval
            if buff<=b<=(interval-buff):
                if flatten:
                    z=math.floor(z/interval)*interval+interval/2

                f.write('{0} {1} {2}\n'.format(x,y,z))
        f.close()

def filterprocess(tilename,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval,flatten):

    txtfile = os.path.join(txtfolder,'{0}.txt'.format(tilename))
    inputfile = os.path.join(inputfolder,'{0}.{1}'.format(tilename,'laz'))
    filteredtxtfile = os.path.join(filteredfolder,'{0}.txt'.format(tilename))
    filteredlas = os.path.join(lazfolder,'{0}.laz'.format(tilename))
    cleanup = [txtfile,filteredtxtfile]
    try:
        convert2TXT(inputfile,tilename,txtfile)
        filterFile(txtfile,filteredtxtfile,contourinterval,filterval,flatten)
        txt2las(filteredtxtfile,tilename,filteredlas)

    except:
        log = 'Could not make countours {0}, Failed at Subprocess'.format(tilename)
        return (False,None, log)

    finally:
        if os.path.isfile(filteredlas):
            log = 'Making Contours was successful for {0}'.format(tilename)
            for fe in cleanup:
                try:
                    if os.path.isfile(fe):
                        os.remove(fe)   
                except:
                    print('cleanup FAILED.') 
                print('Cleaning Process complete')
            return (True,filteredlas, log)

        else:
            log = 'Could not make contours for {0}'.format(tilename)
            return (False,None, log)



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()

    if args.command == "Make_Contours":
        inputfolder=args.inputfolder
        filepattern = args.filepattern.split(';')

        contourfiles = []
        if len(filepattern) >=2:
            print('Number of patterns found : {0}'.format(len(filepattern)))
        for pattern in filepattern:
            pattern = pattern.strip()
            print ('Selecting files with pattern {0}'.format(pattern))
            filelist = glob.glob(inputfolder+"\\"+pattern)
            for file in filelist:
                contourfiles.append(file)
        print('Number of Files found : {0} '.format(len(contourfiles)))

        tilelayoutfile = args.layoutfile
        outpath = args.outputpath
        #hydrofiles = args.hydrofiles
        aoi = args.aoi
        epsg = args.epsg
        zone = str(epsg)[-2:]
        print("Zone number : {0}".format(zone))
        gmexe = args.gmexe.replace('\\','/')
        buffer = args.buffer
        cores = args.cores
        contourinterval = args.contourinterval
        index = float(contourinterval)*(float(args.indexinterval))
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles.replace('\\','/')

        print(hydropointsfiles)


        tilelayout = AtlassTileLayout()
        tilelayout.fromjson(tilelayoutfile)

        if not contourfiles:
            print("No LAS files in the given folder to generate contours")
            quit

        dt = strftime("%y%m%d_%H%M")

        contour_buffered_out_path = AtlassGen.makedir(os.path.join(outpath, ('{0}_makeContour_{1}'.format(dt,contourinterval))))
        gms_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'scripts'))
        bufferedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, ('buffered_{0}m_contours'.format(buffer))))
        bufferremoved_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'buffer_removed'))
        clippedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'clipped_shp'))

        if not epsg == None:

            prjfile2 = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
            prjfile = os.path.join(gms_path,'{0}.prj'.format(epsg)).replace('\\','/')

        if os.path.isfile(prjfile2):
            shutil.copy(prjfile2,prjfile)
        else:
            print("PRJ file for {1} is not available in 10.10.10.142".format(epsg))

        mk_contour_tasks = {}
        for tile in tilelayout:
                                                                                                 
            mk_contour_tasks[tile.name] = AtlassTask(tile.name,ContourClass.makecontourprocess, tile.name,inputfolder,gms_path,bufferedout_path,bufferremoved_path,clippedout_path,int(buffer),contourinterval,zone,aoi,index,hydropointsfiles,gmexe,tilelayoutfile,prjfile)        

        p=Pool(processes=cores)      
        mk_contour_results=p.map(AtlassTaskRunner.taskmanager,mk_contour_tasks.values())


        #Verify final results
        for result in mk_contour_results:
            print(result.result, result.log)
        
    if args.command == "Filter_LAZ_Files":


        inputfolder = args.inputfolder
        outputfolder = args.outputpath
        contourinterval = float(args.contourinterval)
        filepattern = args.filepattern.split(';')
        filterval = float(args.filterval)
        flatten = args.flatten
        tilelayoutfile = args.TL
        cores = args.cores

        files=AtlassGen.FILELIST(filepattern, inputfolder)
        print("\nNo of laz files found : {0}".format(len(files)))

        filterval_val = min([filterval,0.3])

        print("\nFiltering Value used : {0}".format(filterval_val))

        outputfolder = AtlassGen.makedir(os.path.join(outputfolder,'Filteringfor_{0}m_Contours_{1}_filtering'.format(contourinterval,filterval_val)).replace('\\','/'))
        txtfolder = AtlassGen.makedir(os.path.join(outputfolder,'txt_files').replace('\\','/'))
        filteredfolder = AtlassGen.makedir(os.path.join(txtfolder,'filtered_txtfiles').replace('\\','/'))
        lazfolder = AtlassGen.makedir(os.path.join(outputfolder,'filtered_laz').replace('\\','/'))

        
        tl_out = AtlassTileLayout()
        tl_out.fromjson(tilelayoutfile)

        filter_task = {}
        filter_results = []

        for tile in tl_out:

            tilename = tile.name
            filter_task[tilename] = AtlassTask(tilename, filterprocess, tilename,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval_val,flatten)     

        p=Pool(processes=cores)      
        filter_results=p.map(AtlassTaskRunner.taskmanager,filter_task.values())
        
        for result in filter_results:
            print(result.log)
    return

if __name__ == "__main__":
    main()       

