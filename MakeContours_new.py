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
import math
import glob
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeContoursLib import *
#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make Contour", use_legacy_titles=True, required_cols=1, default_size=(1000,800))
def param_parser():

    
    globalmapperexe = glob.glob('C:\\Program Files\\'+'GlobalMapper2*')
    globalmapperexe = '{0}\\global_mapper.exe'.format(globalmapperexe[0])
    print(globalmapperexe)

    parser=GooeyParser(description="Make Contour")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    cart_filter_parser = sub_pars.add_parser('Cartographic_Filter', help='Prepares the las files for contours by filtering')
    cart_filter_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    cart_filter_parser.add_argument("filetype",metavar="Input File type", default='laz')
    cart_filter_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    cart_filter_parser.add_argument("TL", metavar="Tilelayout", widget="FileChooser", help="tilelayout.json", default="")
    cart_filter_parser.add_argument("contourinterval", metavar="Contour interval", help="Provide contour interval", default='0.5')
    cart_filter_parser.add_argument("-flatten", metavar="Flatten", help="Flatten points between intervals", action='store_true',default=False)
    cart_filter_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    cart_filter_parser.add_argument("-cores",metavar="Cores", help="No of cores to run", type=int, default=8)
    eng_filter_parser = sub_pars.add_parser('Engineering_Filter', help='Prepares the las files for contours by filtering')
    eng_filter_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    eng_filter_parser.add_argument("filetype",metavar="Input File type", default='laz')
    eng_filter_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    eng_filter_parser.add_argument("TL", metavar="Tilelayout", widget="FileChooser", help="tilelayout.json", default="")
    eng_filter_parser.add_argument("contourinterval", metavar="Contour interval", help="Provide contour interval", default='0.5')
    eng_filter_parser.add_argument("-flatten", metavar="Flatten", help="Flatten points between intervals", action='store_true',default=False)
    eng_filter_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    eng_filter_parser.add_argument("-cores",metavar="Cores", help="No of cores to run", type=int, default=8)
    smooth_filter_parser = sub_pars.add_parser('Smooth_Raw_Filter', help='Prepares the las files for contours by filtering')
    smooth_filter_parser.add_argument("inputfolder", metavar="Input Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    smooth_filter_parser.add_argument("filetype",metavar="Input File type", default='laz')
    smooth_filter_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    smooth_filter_parser.add_argument("TL", metavar="Tilelayout", widget="FileChooser", help="tilelayout.json", default="")
    smooth_filter_parser.add_argument("contourinterval", metavar="Contour interval", help="Provide contour interval", default='0.5')
    smooth_filter_parser.add_argument("filterval",metavar="Filter Value", help="Must not be more than 30% of contour interval", type=float, default=0.15)
    smooth_filter_parser.add_argument("-flatten", metavar="Flatten", help="Flatten points between intervals", action='store_true',default=False)
    smooth_filter_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    smooth_filter_parser.add_argument("-cores",metavar="Cores", help="No of cores to run", type=int, default=8)
    main_parser = sub_pars.add_parser('Make_Contours', help='Creates the contours')
    main_parser.add_argument("inputfolder", metavar="Contour Points Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    main_parser.add_argument("filetype",metavar="Input File type", default='laz')
    main_parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default='')
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    main_parser.add_argument("aoi", metavar="AOI", widget="FileChooser", help="Area of interest(.shp file)", default="")
    main_parser.add_argument("zone", metavar="UTM Zone", choices=['49','50','51','52','53','54','55','56'],default='55')
    main_parser.add_argument("contourinterval", metavar="Contour interval", help="Provide contour interval", default='0.5')
    main_parser.add_argument("indexinterval", metavar="Index Interval", help="Provide interval for contour index", default='5')
    main_parser.add_argument("gmexe", metavar="Global Mapper EXE", widget="FileChooser", help="Location of Global Mapper exe", default=globalmapperexe)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=8)
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")

    return parser.parse_args()

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


def convert2TXT(inputlas,tilename,output):
    log =''

    try:
        subprocessargs=['C:/LAStools/bin/las2txt.exe','-i',inputlas,'-rescale',0.001,0.001,0.001,'-o',output]
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
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',input,'-olaz','-o',output]
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


def CartographicPrep(tilename,inputfolder,outputfolder,buffer,hydropointsfiles,tl_out,tile,filetype):

    step =1
    #Create buffer of tile containing class 2
    gndclasses=[2]
    bufferfolder = AtlassGen.makedir(os.path.join(outputfolder,'buffer').replace('\\','/'))
    bufferedlas = os.path.join(bufferfolder, '{0}.laz'.format(tilename)).replace('\\','/')

    AtlassGen.bufferTile(tile,tl_out,bufferedlas,buffer,gndclasses,inputfolder,filetype)

    bufferedinputs = [bufferedlas]
    print(hydropointsfiles)

    if not hydropointsfiles == None:
        bufferedhydrofile = bufferhydro(tile, buffer,bufferfolder,hydropointsfiles)
        bufferedinputs.append(bufferedhydrofile)

    if not len(bufferedinputs) == 0:

        mergedfile = os.path.join(bufferfolder, '{0}_merged.laz'.format(tilename)).replace('\\','/')
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+bufferedinputs+['-merged','-olaz','-o',mergedfile]
        subprocessargs=list(map(str,subprocessargs))
        #print(list(subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    outputfile = os.path.join(outputfolder, '{0}_temp.laz'.format(tilename)).replace('\\','/')
    #Lasgrid -i mergedfile -step 1 -subcircle 0.5 -elevation_average
    try:
        subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',mergedfile,'-step',step,'-o',outputfile,'-subcircle',0.5,'-elevation_average']
        subprocessargs=list(map(str,subprocessargs))
        #print(list(subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except:
        log = 'Could not make grid for (catagraphic) {0}, Failed at Subprocess'.format(tile.name)  
        return (None)

    finally:
        if os.path.isfile(outputfile):
            log = 'Making grid(catagraphic) was successful for {0}'.format(tile.name)
            return (outputfile)

        else:
            log = 'Could not make grid(catagraphic) for {0}'.format(tile.name)   
            return (None)

    

def bufferhydro(tile,buffer,outputfolder,hydropointsfiles):

    outputfile = os.path.join(outputfolder,'{0}_hydro.laz'.format(tile.name)).replace('\\','/')
    keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin-buffer, tile.ymin-buffer, tile.xmax+buffer, tile.ymax+buffer)
    keep=keep.split()

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+hydropointsfiles+['-olaz','-o',outputfile] + keep
        subprocessargs=list(map(str,subprocessargs))
        #print(list(subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except:
        log = 'Could not make buffered hydro tile for {0}, Failed at Subprocess'.format(tile.name)  
        return (None)

    finally:
        if os.path.isfile(outputfile):
            log = 'Making Contours was successful for {0}'.format(tile.name)
            return (outputfile)

        else:
            log = 'Could not make contours for {0}'.format(tile.name)   
            return (None)


def Cartographicfilterprocess(tilename,tl_out,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval,flatten,tile,hydropointsfiles,temp_folder,filetype):

    txtfile = os.path.join(txtfolder,'{0}.txt'.format(tilename)).replace('\\','/')
    filteredtxtfile = os.path.join(filteredfolder,'{0}.txt'.format(tilename)).replace('\\','/')
    filteredlas = os.path.join(filteredfolder,'{0}_buff.laz'.format(tilename)).replace('\\','/')
    unbufferedfile = os.path.join(lazfolder,'{0}.laz'.format(tilename)).replace('\\','/')
    cleanup = [txtfile,filteredtxtfile,filteredlas]


    try:
        gridfile = CartographicPrep(tilename,inputfolder,temp_folder,200,hydropointsfiles,tl_out,tile,filetype)
        convert2TXT(gridfile,tilename,txtfile)
        filterFile(txtfile,filteredtxtfile,contourinterval,filterval,flatten)
        txt2las(filteredtxtfile,tilename,filteredlas)
        AtlassGen.unbufferTile(tile,tl_out,unbufferedfile,200,filteredlas)


    except:
        log = 'Could not make countours {0}, Failed at Subprocess'.format(tilename)
        return (False,None, log)

    finally:
        if os.path.isfile(unbufferedfile):
            log = 'Making Contours was successful for {0}'.format(tilename)
            for fe in cleanup:
                try:
                    if os.path.isfile(fe):
                        os.remove(fe)   
                except:
                    print('cleanup FAILED.') 
                print('Cleaning Process complete')
            return (True,unbufferedfile, log)

        else:
            log = 'Could not make contours for {0}'.format(tilename)
            return (False,None, log)

def Engineeringfilterprocess(tilename,tl_out,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval,flatten,tile,hydropointsfiles,temp_folder,filetype):

    inputfile = os.path.join(inputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
  
    try:
        if not hydropointsfiles == None:
            
            tiledhydropointsfile = os.path.join(temp_folder,'{0}_hydro.laz'.format(tilename)).replace('\\','/')
            keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin, tile.ymin, tile.xmax, tile.ymax)
            keep=keep.split()

            inputfile_justlaz = inputfile

            subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+ hydropointsfiles +['-olaz','-o',tiledhydropointsfile,'-merged'] + keep
            subprocessargs=list(map(str,subprocessargs))
            #print(list(subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            if os.path.isfile(tiledhydropointsfile):
                inputfile = os.path.join(temp_folder,'{0}.laz'.format(tilename))
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i',inputfile_justlaz,tiledhydropointsfile ,'-merged','-olaz','-o',inputfile]
                subprocessargs=list(map(str,subprocessargs))
                #print(list(subprocessargs))
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        
        txtfile = os.path.join(txtfolder,'{0}.txt'.format(tilename)).replace('\\','/')
        filteredtxtfile = os.path.join(filteredfolder,'{0}.txt'.format(tilename)).replace('\\','/')
        filteredlas = os.path.join(lazfolder,'{0}.laz'.format(tilename)).replace('\\','/')
        cleanup = [txtfile,filteredtxtfile,tiledhydropointsfile]

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

def Smoothfilterprocess(tilename,tl_out,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval,flatten,tile,hydropointsfiles,temp_folder,filetype):

    inputfile = os.path.join(inputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    txtfile = os.path.join(txtfolder,'{0}.txt'.format(tilename)).replace('\\','/')
    filteredtxtfile = os.path.join(filteredfolder,'{0}.txt'.format(tilename)).replace('\\','/')
    filteredlas = os.path.join(lazfolder,'{0}.laz'.format(tilename)).replace('\\','/')
    cleanup = [txtfile,filteredtxtfile]

    try:
        if not hydropointsfiles == None:
            
            tiledhydropointsfile = os.path.join(temp_folder,'{0}_hydro.laz'.format(tilename)).replace('\\','/')
            cleanup.append[tiledhydropointsfile]
            keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin, tile.ymin, tile.xmax, tile.ymax)
            keep=keep.split()

            inputfile_justlaz = inputfile

            subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+ hydropointsfiles +['-olaz','-o',tiledhydropointsfile,'-merged'] + keep
            subprocessargs=list(map(str,subprocessargs))
            #print(list(subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            if os.path.isfile(tiledhydropointsfile):
                inputfile = os.path.join(temp_folder,'{0}.laz'.format(tilename))
                subprocessargs=['C:/LAStools/bin/las2las.exe','-i',inputfile_justlaz,tiledhydropointsfile ,'-merged','-olaz','-o',inputfile]
                subprocessargs=list(map(str,subprocessargs))
                #print(list(subprocessargs))
                p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
            


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
        filetype = args.filetype
        tilelayoutfile = args.layoutfile
        outpath = args.outputpath
        #hydrofiles = args.hydrofiles
        aoi = args.aoi
        zone = args.zone
        gmexe = args.gmexe.replace('\\','/')
        buffer = args.buffer
        cores = args.cores
        contourinterval = args.contourinterval
        index = float(contourinterval)*(float(args.indexinterval))
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles.replace('\\','/')

        print(hydropointsfiles)

        contourfiles = AtlassGen.FILELIST(['*.{0}'.format(filetype)],inputfolder)

        tilelayout = AtlassTileLayout()
        tilelayout.fromjson(tilelayoutfile)

        if len(contourfiles) == 0:
            print("No LAS files in the given folder to generate contours")
            quit

        dt = strftime("%y%m%d_%H%M")

        contour_buffered_out_path = AtlassGen.makedir(os.path.join(outpath, ('{0}_makeContour_{1}'.format(dt,contourinterval))))
        gms_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'scripts'))
        bufferedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, ('buffered_{0}m_contours'.format(buffer))))
        bufferremoved_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'buffer_removed'))
        clippedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'clipped_shp'))

        print("\nNo of tiles in TL : {0}".format(len(tilelayout)))

        mk_contour_tasks = {}
        for tile in tilelayout:
                                                                                                 
            mk_contour_tasks[tile.name] = AtlassTask(tile.name,ContourClass.makecontourprocess, tile.name,inputfolder,gms_path,bufferedout_path,bufferremoved_path,clippedout_path,int(buffer),contourinterval,zone,aoi,index,hydropointsfiles,gmexe,tilelayoutfile)        

        p=Pool(processes=cores)      
        mk_contour_results=p.map(AtlassTaskRunner.taskmanager,mk_contour_tasks.values())


        #Verify final results
        for result in mk_contour_results:
            print(result.result, result.log)
        
    if args.command == "Cartographic_Filter":


        inputfolder = args.inputfolder
        outputfolder = args.outputpath
        contourinterval = float(args.contourinterval)
        filetype = args.filetype
        filterval = 0.1
        flatten = args.flatten
        tilelayoutfile = args.TL
        cores = args.cores
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles.replace('\\','/')
            hydropointsfiles = hydropointsfiles.split(';')

        filterval_val = min([filterval,0.3])

        print("\nFiltering Value used : {0}".format(filterval_val))

        outputfolder = AtlassGen.makedir(os.path.join(outputfolder,'CartographicFiltering_{1}_{0}m_Contours'.format(contourinterval,filterval_val)).replace('\\','/'))
        txtfolder = AtlassGen.makedir(os.path.join(outputfolder,'txt_files').replace('\\','/'))
        filteredfolder = AtlassGen.makedir(os.path.join(txtfolder,'filtered_txtfiles').replace('\\','/'))
        lazfolder = AtlassGen.makedir(os.path.join(outputfolder,'filtered_laz').replace('\\','/'))
        temp_folder = AtlassGen.makedir(os.path.join(outputfolder,'temp').replace('\\','/'))

        
        tl_out = AtlassTileLayout()
        tl_out.fromjson(tilelayoutfile)

        filter_task = {}
        filter_results = []

        print("\nNo of tiles in TL : {0}".format(len(tl_out)))

        for tile in tl_out:

            tilename = tile.name
            filter_task[tilename] = AtlassTask(tilename, Cartographicfilterprocess, tilename,tl_out,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval_val,flatten,tile,hydropointsfiles,temp_folder,filetype)     

        p=Pool(processes=cores)      
        filter_results=p.map(AtlassTaskRunner.taskmanager,filter_task.values())
        
        for result in filter_results:
            print(result.log)

    if args.command == "Engineering_Filter":


        inputfolder = args.inputfolder
        outputfolder = args.outputpath
        contourinterval = float(args.contourinterval)
        filetype = args.filetype
        filterval = 0.025
        flatten = args.flatten
        tilelayoutfile = args.TL
        cores = args.cores
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles.replace('\\','/')
            hydropointsfiles = hydropointsfiles.split(';')

        filetype = args.filetype
        filterval_val = min([filterval,0.3])

        print("\nFiltering Value used : {0}".format(filterval_val))

        outputfolder = AtlassGen.makedir(os.path.join(outputfolder,'EngineeringFiltering_{1}_{0}m_Contours'.format(contourinterval,filterval_val)).replace('\\','/'))
        txtfolder = AtlassGen.makedir(os.path.join(outputfolder,'txt_files').replace('\\','/'))
        filteredfolder = AtlassGen.makedir(os.path.join(txtfolder,'filtered_txtfiles').replace('\\','/'))
        lazfolder = AtlassGen.makedir(os.path.join(outputfolder,'filtered_laz').replace('\\','/'))
        temp_folder = AtlassGen.makedir(os.path.join(outputfolder,'temp').replace('\\','/'))

        
        tl_out = AtlassTileLayout()
        tl_out.fromjson(tilelayoutfile)

        filter_task = {}
        filter_results = []

        for tile in tl_out:

            tilename = tile.name
            filter_task[tilename] = AtlassTask(tilename, Engineeringfilterprocess, tilename,tl_out,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval_val,flatten,tile,hydropointsfiles,temp_folder,filetype)     

        p=Pool(processes=cores)      
        filter_results=p.map(AtlassTaskRunner.taskmanager,filter_task.values())
        
        for result in filter_results:
            print(result.log)

    if args.command == "Smooth_Raw_Filter":


        inputfolder = args.inputfolder
        outputfolder = args.outputpath
        contourinterval = float(args.contourinterval)
        filetype = args.filetype
        filterval = float(args.filterval)
        flatten = args.flatten
        tilelayoutfile = args.TL
        cores = args.cores
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles.replace('\\','/')
            hydropointsfiles = hydropointsfiles.split(';')

        filterval_val = min([filterval,0.3])

        print("\nFiltering Value used : {0}".format(filterval_val))

        outputfolder = AtlassGen.makedir(os.path.join(outputfolder,'SmoothFiltering_{1}_{0}m_Contours'.format(contourinterval,filterval_val)).replace('\\','/'))
        txtfolder = AtlassGen.makedir(os.path.join(outputfolder,'txt_files').replace('\\','/'))
        filteredfolder = AtlassGen.makedir(os.path.join(txtfolder,'filtered_txtfiles').replace('\\','/'))
        lazfolder = AtlassGen.makedir(os.path.join(outputfolder,'filtered_laz').replace('\\','/'))
        temp_folder = AtlassGen.makedir(os.path.join(outputfolder,'temp').replace('\\','/'))

        
        tl_out = AtlassTileLayout()
        tl_out.fromjson(tilelayoutfile)

        filter_task = {}
        filter_results = []

        for tile in tl_out:

            tilename = tile.name
            filter_task[tilename] = AtlassTask(tilename, Smoothfilterprocess, tilename,tl_out,inputfolder,txtfolder,filteredfolder,lazfolder,contourinterval,filterval_val,flatten,tile,hydropointsfiles,temp_folder,filetype)     

        p=Pool(processes=cores)      
        filter_results=p.map(AtlassTaskRunner.taskmanager,filter_task.values())
        
        for result in filter_results:
            print(result.log)
    return

if __name__ == "__main__":
    main()       

