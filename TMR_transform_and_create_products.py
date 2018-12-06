#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import math
import shutil
import subprocess
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser

from Atlass import *


#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make Grid", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="Make Grid")
    main_parser.add_argument("inputpath", metavar="Input Folder", widget="DirChooser", help="Select input las/laz file", default="D:\\Python\\Gui\\input\\Contours")
    main_parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    #main_parser.add_argument("geojsonfile", metavar="GoeJson file", widget="FileChooser", help="Select geojson file", default='D:\\Python\\Gui\\input\\TileLayout.json')
    main_parser.add_argument("poly", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.shp or .json)", default='D:\\Python\\Gui\\input\\Contours\\tilelayout\\tile_layout_shapefile.shp')
    main_parser.add_argument('name', metavar="AreaName", help="Project Area Name eg : MR101502 ", default="MR22353")
    main_parser.add_argument("epsg", metavar="EPSG", type=int, default=28356)
    main_parser.add_argument("dx", metavar="dx", type=float, default=0.001)
    main_parser.add_argument("dy", metavar="dy", type=float, default=0.0100)
    main_parser.add_argument("dz", metavar="dz", type=float, default=-0.0353)
    main_parser.add_argument("intensity_min", metavar="Intensity min", type=float, default=0.01)
    main_parser.add_argument("intensity_max", metavar="Intensity max", type=float, default=0.1)    
    main_parser.add_argument("-tile_size", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    main_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    main_parser.add_argument("-cs", "--chmstep",metavar="CHM step", help="Provide chmstep", type=float, default=2.0)
    main_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    main_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    main_parser.add_argument("-k", "--kill",metavar="Kill", help="Kill after (s)", type=int, default=250)
    main_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    
    return main_parser.parse_args()


#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def MakeDEM(TILE, workdir, dem1esridir, dem1dir, lasfiles, buffer, kill, step, chmstep, gndclasses, chmclasses, nongndclasses, hydrogridclasses, hydropoints, filetype, poly,areaname):
#need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
#use this file for MKP, just remember to remove buffer
#This will need clipping to AOI
    workdemdir = os.path.join(workdir,"dem")


    #Prep RAW DTM
    print('Setting up folders :','Prepare Raw DTM')
    AtlassGen.makedir(workdemdir)


    #files
    dtmfile=os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, TILE.xmin, TILE.ymin)).replace('\\','/')
    dtmlazfile=os.path.join(workdemdir,'{0}_dem.{1}'.format(TILE.name, filetype)).replace('\\','/')
    dtmlazclipped = os.path.join(workdemdir,'{0}_dem_clipped.{1}'.format(TILE.name, filetype)).replace('\\','/')
    gndfile=os.path.join(workdemdir,'{0}_dem_merged.{1}'.format(TILE.name, filetype)).replace('\\','/')
    clipped_dtmascfile = os.path.join(dem1esridir,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, TILE.xmin, TILE.ymin)).replace('\\','/')
    
    #set up clipping    
    keep='-keep_xy {0} {1} {2} {3}'.format(TILE.xmin-buffer,TILE.ymin-buffer,TILE.xmax+buffer,TILE.ymax+buffer)
    keep=keep.split()

    
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + lasfiles + ['-olas','-o', gndfile,'-merged','-keep_class'] + gndclasses  + keep 
        subprocessargs=list(map(str,subprocessargs))
        subprocess.call(subprocessargs)         
        
        #make dem -- simple tin to DEM process made with buffer and clipped  back to the tile boundary
        if not hydropoints==None:
            gndfile2=os.path.join(workdemdir,'{0}_dem_hydro.{1}'.format(TILE.name, filetype)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i', gndfile,'-merged','-olas','-o',gndfile2] + keep 
            subprocessargs=list(map(str,subprocessargs))
            subprocess.call(subprocessargs)    
            print("added Hydro points")
        
        print("DEM starting")
        subprocessargs=['C:/LAStools/bin/blast2dem.exe','-i',gndfile,'-oasc','-o', dtmfile,'-nbits',32,'-kill',kill,'-step',step] 
        subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/step), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/step)]    
        #ensures the tile is not buffered by setting lower left coordinate and num rows and num cols in output grid.
        subprocessargs=list(map(str,subprocessargs))  
        subprocess.call(subprocessargs) 


        #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', dtmfile, '-olas', '-o', dtmlazfile, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs) 

        #lasindex of dtmlazfile
        index(dtmlazfile)

        #lasclip dtmlazfile
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' , dtmlazfile, '-merged', '-poly', poly, '-o', dtmlazclipped, '-olas']
        subprocessargs=list(map(str,subprocessargs))    
        print(subprocessargs)
        subprocess.call(subprocessargs)


        #lasgrid clipped dtmlazfile test if file exists because files outside of poly will not exist
        if dtmlazclipped.exists():
            
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i',dtmlazclipped,'-oasc','-o', clipped_dtmascfile,'-nbits',32,'-step',step] 
            subprocessargs=subprocessargs+['-ll',TILE.xmin,TILE.ymin,'-ncols',math.ceil((TILE.xmax-TILE.xmin)/step), '-nrows',math.ceil((TILE.ymax-TILE.ymin)/step)]    
            subprocess.call(subprocessargs)

            print(TILE.name+': DEM output.')
            result = {"file":TILE.name, "state" :"Success", "output":clipped_dtmascfile }
        else:
            result = {"file":TILE.name, "state" :"Success", "output":"not within boundry" }

    except:
        print(TILE.name+': DEM output FAILED.')
        result = {"file":TILE.name, "state" :"Error", "output":clipped_dtmascfile }
    
    return result

def Adjust(input, output, dx, dy, dz, epsg):
    #las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las
    result = None
    print(output)
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i' , input ,'-olas', '-translate_xyz', dx, dy, dz, '-epsg', epsg ,'-set_version', 1.2,  '-o', output]
        subprocessargs=list(map(str,subprocessargs))
        print(subprocessargs)    
        subprocess.call(subprocessargs) 
        if os.path.isfile(ouput):
            result = {"file":input, "state":"Success", "output" : output }
        else:
            result = {"file":input, "state":"Error", "output" : "Could Not make adjusted file" }
        index(output)
    except:
        print("Could not adjust Tile {0}".format(input))
        result = {"file":input, "state":"Error", "output" : "Could Not make adjusted file" }
    
    print(result)
    return result

def MakeXYZ(TILE, outpath, dem1dir,areaname):
    #las2las -i <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc -otxt -o <inputpath>/Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz -rescale 0.001 0.001 0.001

    #Prep RAW DTM
    print('Making 1m')

    #files
    dtmfile=os.path.join(outpath,'{0}_2018_SW_{1}_{2}_1k_1m_esri.asc'.format(areaname, TILE.xmin, TILE.ymin)).replace('\\','/')
    xyzfile = os.path.join(dem1dir,'{0}_2018_SW_{1}_{2}_1k_1m.xyz'.format(areaname, TILE.xmin, TILE.ymin)).replace('\\','/')


    
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', dtmfile, '-otxt','-o', xyzfile, '-rescale', 0.001, 0.001, 0.001]
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs)
        if xyzfile.exists():
            result = {"file":TILE.name, "state" :"Success", "output":xyzfile }
        else:
            result = {"file":TILE.name, "state" :"Error", "output":xyzfile }

    except:
        print(TILE.name+': DEM output FAILED.')
        result = {"file":TILE.name, "state" :"Error", "output":xyzfile }
    print(result)
    return result

def index(input):
    print("Indexing")
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs)
        result = {"file":input, "state" :"Success", "output":"Indexing Complete" }
    except:
        result = {"file":input, "state" :"Error", "output":"Indexing Failed" }

    return result

def MakeMKP(tile, lasfiles, outpath, gndclasses,vt, hz, buffer):
    cleanup=[]
    outfile=os.path.join(outpath,'{0}.las'.format(tile.name)).replace('\\','/')
    tempfile=os.path.join(outpath,'{0}_temp.las'.format(tile.name)).replace('\\','/')
    tempfile2=os.path.join(outpath,'{0}_temp2.las'.format(tile.name)).replace('\\','/')
    cleanup.append(tempfile)
    cleanup.append(tempfile2)
    
    print("Making MKP")
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i']+lasfiles+['-merged','-olas','-o',tempfile,'-keep_class'] + gndclasses
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer]
        subprocessargs=list(map(str,subprocessargs)) 
        subprocess.call(subprocessargs)
    
        subprocessargs=['C:/LAStools/bin/lasthin.exe','-i',tempfile,'-olas','-o',tempfile2,'-adaptive',vt,hz,'-set_classification',8]
        subprocessargs=subprocessargs
        subprocessargs=list(map(str,subprocessargs))    
        subprocess.call(subprocessargs)  

        subprocessargs=['C:/LAStools/bin/las2las.exe','-i',tempfile2,'-olas','-o',outfile]
        subprocessargs=subprocessargs+['-keep_xy',tile.xmin,tile.ymin,tile.xmax,tile.ymax]
        subprocessargs=list(map(str,subprocessargs))    
        subprocess.call(subprocessargs)  

        index(outfile)

        if os.path.isfile(outfile):
            result = {"file":tile.name, "state" :"Success", "output":outfile }
        else: 
            result = {"file":tile.name, "state" :"Error", "output":"Could not Make MKP for file : {0}".format(tile.name) }
    except:
        result = {"file":tile.name, "state" :"Error", "output":"Could not Make MKP : {0}".format(tile.name) }

    for file in cleanup:
        if os.path.isfile(file):
            os.remove(file)
            pass
    return result

def Cliping(TILE, adjdir, mkpdir, lasahddir, filetype, poly, zone,areaname):

    #files
    clipedfile = os.path.join(lasahddir, '{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, int(TILE.xmin), int(TILE.ymin), zone, filetype)).replace("\\", "/") #<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las
    adjfile = os.path.join(adjdir, '{0}.{1}'.format(TILE.name, filetype)).replace("\\", "/")
    mkpfile = os.path.join(mkpdir, '{0}.{1}'.format(TILE.name, filetype)).replace("\\", "/")
    print("Clipping")
    try:
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i','-use_lax' , adjfile, mkpfile, '-merged', '-poly', poly, '-o', clipedfile, '-olas']
        subprocessargs=list(map(str,subprocessargs))    
        subprocess.call(subprocessargs)  
        result = {"file":TILE.name, "state" :"Fail", "output": clipedfile}
    except:
        result = {"file":TILE.name, "state" :"Fail", "output":"Fail to Make Clip files" }

    return result


def MakeGrid(TILE, lasahddir,intensitydir, zone, intensityMin,intensityMax, filetype,areaname):
    inputfile = os.path.join(lasahddir, '{0}_2018_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, int(TILE.xmin), int(TILE.ymin), zone, filetype)).replace("\\", "/") #<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las
    outputfile = os.path.join(intensitydir,'{0}_2018_2_AHD_SW_{1}_{2}_1k_50cm_INT.tif'.format(areaname, int(TILE.xmin), int(TILE.ymin))).replace("\\", "/")   #<inputpath>/Products/<Area_Name>_Intensity_50cm/<Name>_2018_SW_<X>_<Y>_1k_50cm_INT.tif
    
    if os.path.exists(inputfile):
        print("Making Grid")
        try:
            subprocessargs=['C:/LAStools/bin/lasgrid.exe', '-i', inputfile, '-step', 0.5, '-fill' ,2 ,'-keep_first', '-intensity_average', '-otif', '-nbits', 8 ,'-set_min_max', intensityMin , intensityMax, '-o', outputfile, '-nrows', 2000, '-ncols', 2000]
            subprocessargs=list(map(str,subprocessargs)) 
            print(subprocessargs)   
            subprocess.call(subprocessargs)  
            result = {"file":TILE.name, "state" :"Success", "output":outputfile }
        except:
            result = {"file":TILE.name, "state" :"Fail", "output":"Fail to Make Clip files" }
    else:
        print ("{0} Not within boundry".format(TILE.name))
        result = {"file":TILE.name, "state" :"Fail", "output":"Not within boundry" }


    return result


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()
    filetype=args.filetype
    files = []
    files = glob.glob(args.inputpath+"\\*."+filetype)
    areaname = args.name
    outputpath=args.inputpath
    outputpath=outputpath.replace('\\','/')
    buffer=float(args.buffer)
    tilesize=int(args.tile_size)
    dx = args.dx
    dy = args.dy
    dz = args.dz
    epsg = args.epsg
    zone = (int(epsg) - 28300)
    hydropointsfiles=[]
    vt = 0.1 
    hz = 20
    poly = args.poly.replace('\\','/')
    intensityMin = args.intensity_min
    intensityMax = args.intensity_max
    

    if not args.hydropointsfiles==None:
        hydropointsfiles=args.hydropointsfiles
        hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')
    step=float(args.step)
    chmstep=float(args.chmstep)
    kill=float(args.kill)
    nongndclasses="1 3 4 5 6 10 13 14 15"
    chmclasses="3 4 5"
    gndclasses=[2 ,8]    
    hydrogridclasses="2 4 5 6 8 10 13"
    cores = args.cores
    geojsonfile = outputpath + "/TileLayput.json"

    al = Atlasslogger(outputpath)

    print(outputpath)
    adjdir = AtlassGen.makedir(os.path.join(outputpath, 'Adjusted'))
    workingdir = AtlassGen.makedir(os.path.join(adjdir, 'Working'))
    mkpdir = AtlassGen.makedir(os.path.join(adjdir, 'MKP'))
    prodsdir = AtlassGen.makedir(os.path.join(outputpath, 'Products'))

    dem1dir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_DEM_1m'.format(areaname)))
    dem1esridir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_DEM_1m_ESRI'.format(areaname)))
    intensitydir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_Intensity_50cm'.format(areaname)))
    lasahddir = AtlassGen.makedir(os.path.join(prodsdir, '{0}_LAS_AHD'.format(areaname)))

    tilelayout = AtlassTileLayout()

    #Populate Tasks
    ADJUST_TASK=[]
    INDEX_TASK = []


    for file in files:
        path, filename, ext = AtlassGen.FILESPEC(file)
        path = path.replace("\\", "/")
        output = os.path.join(adjdir, '{0}.{1}'.format(filename, ext)).replace("\\", "/")

        x,y=filename.split('_')
        tilelayout.addtile(name=filename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize)

        ADJUST_TASK.append((Adjust,(file, output, dx, dy, dz, epsg)))
        #Adjust(file, output, dx, dy, dz, epsg)

    jsonfile = tilelayout.createGeojsonFile(geojsonfile)

    #read tilelayout into library
    tl = AtlassTileLayout()
    tl.fromjson(geojsonfile)
    MAKEGRID_TASKS = [] 
    MAKEXYZ_TASKS = []
    MAKEMKP_TASKS = []
    CLIP_TASK = []
    GRID_TASK = []

    for file in files: 

        al.PrintMsg('Creating tile neighbourhood for : {0}'.format(file),'Reading tilelayout shapefile')
        path, filename, ext = AtlassGen.FILESPEC(file)
        path = path.replace("\\", "/")
        tile = tl.gettile(filename)
        neighbourlasfiles = []

        try:
            neighbours = tile.getneighbours(buffer)

        except:
            al.PrintMsg("tile: {0} does not exist in geojson file".format(filename))

        al.PrintMsg('Neighbourhood of {0} las files detected in/overlapping {1}m buffer of :{2}\n'.format(len(neighbours),buffer,file),'Neighbourhood:')

        for neighbour in neighbours:
            neighbour = path +'/'+ neighbour + '.'+ ext

            if os.path.isfile(neighbour):
                al.PrintMsg(neighbour)
                neighbourlasfiles.append(neighbour)


        MAKEGRID_TASKS.append((MakeDEM, (tile, workingdir, dem1esridir, dem1dir, neighbourlasfiles, buffer, kill, step, chmstep, gndclasses, chmclasses, nongndclasses, hydrogridclasses, hydropointsfiles, filetype ,poly,areaname)))
        #MakeDEM(tile, workingdir, dem1esridir, dem1dir, neighbourlasfiles, buffer, kill, step, chmstep, gndclasses, chmclasses, nongndclasses, hydrogridclasses, hydropointsfiles, filetype ,poly,areaname)
        
        MAKEXYZ_TASKS.append((MakeXYZ, (tile, dem1esridir, dem1dir, areaname)))
        #MakeXYZ(tile, dem1esridir, dem1dir, areaname)
        
        MAKEMKP_TASKS.append((MakeMKP,(tile, neighbourlasfiles, mkpdir, gndclasses,vt, hz, buffer)))
        #MakeMKP(tile, neighbourlasfiles, mkpdir, gndclasses,vt, hz, buffer)
        
        CLIP_TASK.append((Cliping,(tile,adjdir, mkpdir,lasahddir, filetype, poly, zone,areaname)))
        #Cliping(tile,adjdir, mkpdir,lasahddir, filetype, poly, zone,areaname)
        
        GRID_TASK.append((MakeGrid,(tile, lasahddir,intensitydir, zone, intensityMin, intensityMax, filetype,areaname)))
        #MakeGrid(tile, lasahddir,intensitydir, zone, intensityMin, intensityMax, filetype,areaname)

    #Multiprocess the tasks    
    results=AtlassTaskRunner(cores,ADJUST_TASK,'Adjusting', al, str(args))

    results2 = AtlassTaskRunner(cores,MAKEGRID_TASKS,'Making Dem and Clipping', al, str(args))

    results3 = AtlassTaskRunner(cores,MAKEXYZ_TASKS,'Making Dem 1 xyz', al, str(args))

    results5 = AtlassTaskRunner(cores,MAKEMKP_TASKS,'Marking MKP', al, str(args))

    results7 = AtlassTaskRunner(cores, CLIP_TASK, 'Clipping', al, str(args))

    results8 = AtlassTaskRunner(cores, GRID_TASK, 'Making Grid with tif', al, str(args))


    return



if __name__ == "__main__":
    main()         

'''
Make def for each of the bolow functions;


kwargs;
    <input path>
    <input extn>
    <Area name> eg <MR101502>
    <poly>
    <dx>
    <dy>
    <dz>
    <epsg> or <Zone>   EPSG= 28300 + <Zone>
    <cores>
    <intensity Min>
    <intensity max>


1.
make output folder structure based on
<inputpath>/Adjusted/
<inputpath>/Adjusted/Working
<inputpath>/Adjusted/MKP

<inputpath>/Products/<Area_Name>_DEM_1m
<inputpath>/Products/<Area_Name>_DEM_1m_ESRI
<inputpath>/Products/<Area_Name>_Intensity_50cm
<inputpath>/Products/<Area_Name>_LAS_AHD

2. 
#las2las -i <inputpath>/<name>.laz -olas -translate_xyz <dx> <dy> <dz> -epsg <epsg> -olas -set_version 1.2 -point_type 1 -o <inputpath>/Adjusted/<name>.las

3.
#need tilelayout to get 200m of neighbours Save the merged buffered las file to <inputpath>/Adjusted/Working
use this file for MKP, just remember to remove buffer
MakeGrids Just DEM in <inputpath>/Adjusted/<name>.las  ... to <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc    
This will need clipping to AOI

4. 
las2las -i <inputpath>/Products/<Area_Name>_DEM_1m_ESRI/<Name>_2018_SW_<X>_<Y>_1k_1m_esri.asc     -otxt -o <inputpath>/Products/<Area_Name>_DEM_1m/<Name>_2018_SW_<X>_<Y>_1k_1m.xyz -rescale 0.001 0.001 0.001

5.
lasindex <inputpath>/Adjusted/<name>.las

6.
Make MKP vt=0.1 hz=20 -input=<inputpath>/Adjusted/Working/<name>.las output=<inputpath>/Adjusted/MKP/<name>.las --set_classification 8  (remove buffer)

7.
lasindex <inputpath>/Adjusted/MKP/<name>.las


8.
lasclip -i -use_lax <inputpath>/Adjusted/<name>.las <inputpath>/Adjusted/MKP/<name>.las -merged -poly <poly> -o <inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las -olas


9.
lasgrid -i<inputpath>/Products/<Area_Name>_LAS_AHD/<Name>_2018_2_AHD_SW_<X>m_<Y>m_<Zone>_1k.las -step 0.5 -fill 2 -keep_first -intensity_average -otif -nbits 8 -set_min_max <intensity Min> <intensity Max> -o <inputpath>/Products/<Area_Name>_Intensity_50cm/<Name>_2018_SW_<X>_<Y>_1k_50cm_INT.tif -nrows 2000 -ncols 2000



set up multi thread process for each
'''


#



#lasgrid -i W:\TMR_Mackaybeesck_VQ780_180923\20181012\dz\clipped\*.las -step 0.5 -fill 2 -keep_first -intensity_average -otif -nbits 8 -set_min_max 100 2500 -cores 18 -odir W:\TMR_Mackaybeesck_VQ780_180923\20181012\clipped_intensity -nrows 2000 -ncols 2000

#C:\LASTools\bin\lasgrid -i *.laz -cores 18 -keep_last -step 5 -point_density -otif -odir point_density

