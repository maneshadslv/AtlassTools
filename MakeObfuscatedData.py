import time
import numpy as np
import pandas as pd
from laspy.tools import lasverify
from laspy.file import File
import sys
import os
import math
from multiprocessing import Pool,freeze_support
import subprocess
from random import randrange
from random import randint
from gooey import Gooey,GooeyParser
import random, string
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *



@Gooey(program_name="Make Data Obfuscated", use_legacy_titles=True, required_cols=2, optional_cols=3, advance=True, default_size=(1000,810))
def param_parser():
    parser=GooeyParser(description="Make Data Obfuscated")
    subs = parser.add_subparsers(help='commands', dest='command')
    part1_parser = subs.add_parser('Part_1', help='Create comfuscated Tile layout ')
    part1_parser.add_argument("intilelayout", metavar="Input Tilelayout", widget="FileChooser", help=".json files")
    part1_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    part2_parser = subs.add_parser('Part_2', help='Apply obfuscation to tiles')
    part2_parser.add_argument("input_dir", metavar="Input Directory",widget="DirChooser", help="Input directory wih laz files", default="")
    part2_parser.add_argument('filetype',metavar="Input File Type", help="Select input file type", default='laz')
    part2_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    part2_parser.add_argument("jsonfile", metavar="Tilelayout",widget="FileChooser", help="Tilelayout with the obfuscated data (.json)", default="")
    part2_parser.add_argument("--cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)
    part2_parser.add_argument("--buffer", metavar="Buffer", help="Buffer Size", type=int, default=200)
    part3_parser = subs.add_parser('Part_3', help='Create a Tile layout with last Edited tiles ')
    part3_parser.add_argument('obfuscated_data',metavar="Obfuscated Data", widget="DirChooser", help="Select folder with obfuscated files")
    part3_parser.add_argument('original_data',metavar="Original Data", widget="DirChooser", help="Select folder with original UNBUFFERED files")
    part3_parser.add_argument("jsonfile", metavar="Tilelayout", widget="FileChooser",help="Provide the tilelayout with the obfuscated info")
    part3_parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    part3_parser.add_argument('filetype',metavar="Input File Type", help="Select input file type", default='laz')
    part3_parser.add_argument("--cores", metavar="Number of Cores", help="Number of cores", type=int, default=8)


    args = parser.parse_args()
    return args

def rotate_about_origin(x,y, radians, originx, originy):
    """Rotate a point around a given point.
    x and y are numpy lists
    """

    offset_x, offset_y = originx, originy
    adjusted_x = (x - offset_x)
    adjusted_y = (y - offset_y)
    cos_rad = math.cos(radians)
    sin_rad = math.sin(radians)
    qx = offset_x + cos_rad * adjusted_x + sin_rad * adjusted_y
    qy = offset_y + -sin_rad * adjusted_x + cos_rad * adjusted_y
    return qx, qy

def obfuscate_data(tile, inputfolder, originx, originy,rotation,xoffset,yoffset,zoffset,toffset,outputfolder,filetype,outtilename,buffer):
    """Rotate a point around a given point.
    x and y are numpy lists
    """
    tilename = tile.name
    input_file=os.path.join(outputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    buffered_file=os.path.join(outputfolder, '{0}_buff.laz'.format(tilename)).replace('\\','/')
    temp_outputfile = os.path.join(outputfolder, '{0}.{1}'.format(outtilename,'las')).replace('\\','/')
    outputfile = os.path.join(outputfolder, '{0}.{1}'.format(outtilename,filetype)).replace('\\','/')
    log=''
    try:
        neighbours = tile.getneighbours(buffer)
        neighbourfiles = []
        for fi in neighbours:
            nfi = os.path.join(inputfolder, '{0}.{1}'.format(fi,filetype)).replace('\\','/')
            if os.path.isfile(nfi):
                neighbourfiles.append(nfi)

        keep='-keep_xy {0} {1} {2} {3}'.format(str(tile.xmin-buffer), str(tile.ymin-buffer), str(tile.xmax+buffer), str(tile.ymax+buffer))
        keep=keep.split()

        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i']+neighbourfiles+['-olaz', '-o', buffered_file, '-merged']+keep
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        infile = File(buffered_file, mode='r')

        xvalues=infile.get_x_scaled()
        yvalues=infile.get_y_scaled()
        zvalues=infile.get_z_scaled()
        tvalues=infile.get_gps_time()

        
        print(f"\ntilename={tilename:s} xoffset={xoffset:0.4f} yoffset={yoffset:0.4f} zoffset={zoffset:0.4f} rotation={rotation:0.4f}  toffset={toffset:0.4f}")
       
        #rotate points
        xvalues,yvalues=rotate_about_origin(xvalues,yvalues, math.radians(rotation), originx, originy)
        #print(tilename,xvalues[0],yvalues[0],zvalues[0])
        #offset points 
        newxvals=xvalues+xoffset
        newyvals=yvalues+yoffset
        newzvals=zvalues+zoffset
        newtvals=tvalues+toffset

        #print(tilename,newxvals[0],newyvals[0],newzvals[0])
        outfile = File(temp_outputfile, mode="w", header=infile.header)
        outfile.points=infile.points
        outfile.set_x_scaled(newxvals)
        outfile.set_y_scaled(newyvals)
        outfile.set_z_scaled(newzvals)
        outfile.set_gps_time(newtvals)
        

        outfile.close()
        infile.close()

        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', temp_outputfile, '-olaz', '-o', outputfile]
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        if os.path.isfile(outputfile):
            log = f'Succesfully Obfuscated {tilename}'
            os.remove(temp_outputfile)
            os.remove(buffered_file)

            return(True,outputfile,log)

    
    except:

        log =f"{tilename} : Obfuscation Failed"
        print(log)
        #outfile.close()
        #infile.close()
        return(False,tilename,log)
    

def random_name():
    x = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return x

def obfuscate_tilelayout(ingeojsonfile,outgeojsonfile,outobsuredgeojsonfile):
    tl_in = AtlassTileLayout()
    tl_in.fromjson(ingeojsonfile)
    tl_out = AtlassTileLayout()
    tl_out = tl_in
    tl_obsout = AtlassTileLayout()

    names=[]

    #loop tiles and calc offsets
    for tile in tl_in:
        #make random new name string
        newname=''
        while newname=='' or newname in names:
            newname=random_name()

        tileout={}
        tileout['obfsname']=newname
        tileout['originx']=(tile.xmax+tile.xmin)/2
        tileout['originy']=(tile.ymax+tile.ymin)/2
        tileout['xoffset']=randint(-500,500)*1000
        tileout['yoffset']=randint(0,700)*1000
        tileout['zoffset']=randint(-200,200)
        tileout['rotation']=randint(0,3)*90
        tileout['toffset']=randint(-25,25)*86400

        outtile = tl_out.gettile(tile.name)
        outtile.addparams(**tileout)

        
        tileobfsout={}
        tileobfsout['name']=newname
        tileobfsout['xmin']=tile.xmin+tileout['xoffset']
        tileobfsout['ymin']=tile.ymin+tileout['yoffset']
        tileobfsout['xmax']=tile.xmax+tileout['xoffset']
        tileobfsout['ymax']=tile.ymax+tileout['yoffset']
        mtime = time.time()
        modificationTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(mtime))
        tileobfsout['modtime']=modificationTime

        tl_obsout.addtile(**tileobfsout)
        
    tl_out.createGeojsonFile(outgeojsonfile)
    tl_obsout.createGeojsonFile(outobsuredgeojsonfile)



    return outgeojsonfile, outobsuredgeojsonfile

def clarifydata(tile, obfuscated_data,original_data,filetype,outputfolder):

    tilename = tile.name
    obfuscated_name = tile.params['obfsname']
    toffset = tile.params['toffset']

    obfuscated_tile = os.path.join(obfuscated_data, '{0}.{1}'.format(obfuscated_name,filetype)).replace('\\','/')
    ori_tile = os.path.join(original_data, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    temp_outputfile = os.path.join(outputfolder, '{0}.{1}'.format(tilename,'las')).replace('\\','/')
    outputfile = os.path.join(outputfolder, '{0}.{1}'.format(tilename,filetype)).replace('\\','/')
    
    #read the obfuscated tile
    infile = File(obfuscated_tile, mode='r')

    #get the gps times
    tvalues=infile.get_gps_time()
    #reset to original times
    newtvals = tvalues-toffset

    outfile = File(temp_outputfile, mode="w", header=infile.header)
    outfile.points=infile.points
    outfile.set_gps_time(newtvals)

    outfile.close()
    infile.close()


    #lascopy all x,y,z,classification based on the corrected gps time
    subprocessargs=['C:/LAStools/bin/lascopy.exe', '-i', temp_outputfile, '-i', ori_tile, '-olaz', '-o', outputfile]
    subprocessargs=list(map(str,subprocessargs))    
    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    if os.path.isfile(outputfile):
        #read the obfuscated tile
        nfile = File(outputfile, mode='r')
        classification = nfile.classification
        #print(classification)

        #get the class 0
        if not 0 in classification:

            log = f'Succesfully coverted {obfuscated_name} -> {tilename}'
            os.remove(temp_outputfile)
            print(log)

            ofile = File(ori_tile, mode='r')

            return(True,outputfile,log)

        else:

            log = f'Failed coverting {obfuscated_name} -> {tilename}- class 0 points in tile'
            #os.remove(temp_outputfile)
            print(log)

            return(False,outputfile,log)

    else:

        log = f'Failed coverting {obfuscated_name} -> {tilename}'
        #os.remove(temp_outputfile)
        print(log)

        return(False,outputfile,log)
def main():
 
    args = param_parser()

    if args.command=='Part_1':

        ingeojsonfile = args.intilelayout
        outgeojsonfile = "{0}/Origial_TileLayout.json".format(args.output_dir)
        outobsuredgeojsonfile = "{0}/Obfuscated_TileLayout.json".format(args.output_dir)

        obfuscate_tilelayout(ingeojsonfile,outgeojsonfile,outobsuredgeojsonfile)


    if args.command=='Part_2':
        inputfolder = args.input_dir
        outputfolder = args.output_dir
        filetype = args.filetype
        obfuscated_tl = args.jsonfile
        cores = args.cores
        buffer = args.buffer
        obfuscated_Tilelayout = AtlassTileLayout()
        obfuscated_Tilelayout.fromjson(obfuscated_tl)
        outputfolder = AtlassGen.makedir(os.path.join(outputfolder, 'ObfuscatedData')).replace('\\','/')
        tasks={}
        for tile in obfuscated_Tilelayout:
            tilename = tile.name
            outtilename = tile.params['obfsname']


            print(outtilename)
       
              
            tasks[tilename]=AtlassTask(tilename,obfuscate_data,tile, inputfolder, tile.params['originx'], tile.params['originy'],tile.params['rotation'],tile.params['xoffset'],tile.params['yoffset'],tile.params['zoffset'],tile.params['toffset'],outputfolder,filetype,outtilename,buffer)


        p=Pool(processes=cores)    
        results=p.map(AtlassTaskRunner.taskmanager,tasks.values())

        log=os.path.join(outputfolder,'log_Obfuscation_step2.txt').replace("\\","/")
        f=open(log,'w')
        for result in results:
            #print(result.success, result.log)

            if result.success:
                f.write(result.log)

    if args.command=='Part_3':
        obfuscated_data = args.obfuscated_data
        original_data = args.original_data

        outputfolder = args.output_dir
        filetype = args.filetype
        ori_tl = args.jsonfile
        cores = args.cores

        outputfolder = AtlassGen.makedir(os.path.join(outputfolder, 'ClarifiedData')).replace('\\','/')
        ori_Tilelayout = AtlassTileLayout()
        ori_Tilelayout.fromjson(ori_tl)

        obfs_filelist = AtlassGen.FILELIST([f'*.{filetype}'],obfuscated_data)
        ori_filelist = AtlassGen.FILELIST([f'*.{filetype}'],original_data)

        print(f'\nNumber of files in the original dataset : {len(ori_filelist)}')
        print(f'\nNumber of files in the obfuscated dataset :{len(obfs_filelist)}')

        tasks = {}

        for tile in ori_Tilelayout:
            tilename = tile.name
            if tile.params['obfsname'] == None:
                print("Input Tilelayout does not have the obfuscted tile information")
            tasks[tilename] = AtlassTask(tilename,clarifydata,tile, obfuscated_data,original_data,filetype,outputfolder)

        p=Pool(processes=cores)    
        results=p.map(AtlassTaskRunner.taskmanager,tasks.values())
    

        log=os.path.join(outputfolder,'log_Obfuscation_step3.txt').replace("\\","/")
        f=open(log,'w')
        for result in results:
            #print(result.success, result.log)

            if result.success:
                f.write(result.log)

    return()
if __name__ == "__main__":
    main() 

