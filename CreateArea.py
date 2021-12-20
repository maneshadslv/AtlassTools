import sys
import shutil
import os, glob
import subprocess
import math
import time
from datetime import datetime
from gooey import Gooey, GooeyParser
from geojson import Point, Feature, FeatureCollection, Polygon,dump
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

@Gooey(program_name="Tile migrater", use_legacy_titles=True, required_cols=1, default_size=(1000,820))
def param_parser():
    parser=GooeyParser(description="Moves/Copies specified tiles to a new folder")
    parser.add_argument("input_folder", metavar="Input Directory ", widget="DirChooser", help="Select folder with input files")
    parser.add_argument("output_dir", metavar="Output Directory", widget="DirChooser", help="Output directory")
    parser.add_argument("-file",metavar="Tilelayout File", widget="FileChooser")
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz','zip','rar','txt','asc','shp','shx','dbf','prj','tab','dat','id','map'], default='laz')
    parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)
    parser.add_argument("-copy", metavar="Copy Files to output folder",  action='store_true', default=False)
    parser.add_argument("-move", metavar="Move Files to output folder",  action='store_true', default=False)
    txtf_group = parser.add_argument_group("Use Text file", gooey_options={'show_border': True,'columns': 3})
    txtf_group.add_argument("-usetxtfile", action="store_true", help="Use Txt file as input")
    txtf_group.add_argument("-txtfile",metavar="Input Text file", widget="FileChooser")
    txtf_group.add_argument("-tilesize",metavar="Input file tile size", default=500, type = int)
    batch_group = parser.add_argument_group("create batches", gooey_options={'show_border': True,'columns': 3})
    batch_group.add_argument("-ba", "--batches",metavar="Batches", help="No of batches to split to", type=int, default=1,gooey_options={
            'validator': {
                'test': '1 <= int(user_input) <= 250',
                'message': 'Must be between 1 and 250'
            }})
    block_group = parser.add_argument_group("Blocking Settings", "Required when breaking a tilelayout into desired block sizes. \n**Do not use with the 'Batches' setting above", gooey_options={'show_border': True,'columns': 2})
    block_group.add_argument("-gen_block",metavar="Generate Blocks", help="Divide to blocks",action='store_true', default=False)
    block_group.add_argument("-block_size",metavar="Block size", help="Block size", type = int ,default=10000)

    return parser.parse_args()

def copyfile(input, output):
    log = ''
    try:
        shutil.copyfile(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            #print('File {0} moved to {1}'.format(input,output))
            log = "Copying file for {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Copying file for {0} Failed".format(input)
            return (False,output, log)

def movefiles(input, output):
    log = ''
    try:
        shutil.move(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            #print('File {0} moved to {1}'.format(input,output))
            log = "Moving file {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Moving file {0} Failed".format(input)
            return (False,output, log)


def main():

    freeze_support()

    args = param_parser()

    intputfolder = args.input_folder.replace('\\','/')
    outputfolder = AtlassGen.makedir(args.output_dir.replace('\\','/'))
    tilelayoutfile = args.file
    filetype = args.filetype
    cores = args.cores
    copy = args.copy
    move = args.move
    batches = args.batches
    gen_block = args.gen_block
    block_size = int(args.block_size)
    ffile = args.txtfile
    usetxtfile = args.usetxtfile
    tilesize = args.tilesize
    tasks = {}
       


    tl_in = AtlassTileLayout()



    if usetxtfile:
        lines = [line.rstrip('\n')for line in open(ffile)]
        
  
        modificationTime = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
        for i,line in enumerate(lines):
            print(line)
            tilename = line

            x,y = tilename.split('_')

            tl_in.addtile(name=tilename, xmin=float(x), ymin=float(y), xmax=float(x)+tilesize, ymax=float(y)+tilesize, modtime=modificationTime)
    else:


        tl_in.fromjson(tilelayoutfile)
    
    no_of_tiles = len(tl_in)
    
    print('\nTotal Number of Files : {0}'.format(no_of_tiles))
    batchlen=math.ceil(no_of_tiles/batches)
    batch=0
    
    if gen_block:
        features = []
        blocks = []


        print('\nBlocking started.')
        block_path = os.path.join(outputfolder,'{0}m_blocks'.format(block_size)).replace('\\','/')


        for tile in tl_in:
            tilename = tile.name
            xmin = tile.xmin
            xmax = tile.xmax
            ymin = tile.ymin
            ymax = tile.ymax
            tilesize = int(int(xmax) - int(xmin))

            block_x = math.floor(xmin/block_size)*block_size
            block_y = math.floor(ymin/block_size)*block_size
            blockname = '{0}_{1}'.format(block_x,block_y)
            block_folder = os.path.join(block_path,blockname).replace('\\','/')

            if blockname not in blocks:
                blocks.append(blockname)

            boxcoords=AtlassGen.GETCOORDS([xmin,ymin],tilesize)
            poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])


            
            if not os.path.exists(block_folder):
                AtlassGen.makedir(block_folder)

            input = os.path.join(intputfolder,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            output = os.path.join(block_folder,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            #print(output)
            #block_task[blockname] = AtlassTask(blockname, movefiles, input, output)
            if copy:
                tasks[tilename] = AtlassTask(tilename, copyfile, input, output)
            elif move:
                tasks[tilename] = AtlassTask(tilename, movefiles, input, output)
            else:
                print("no command selected")
        p=Pool(processes=cores)      
        results=p.map(AtlassTaskRunner.taskmanager,tasks.values())

        success = 0
        for result in results:
            if not result.success:
                print('File {0} could Not be copied/moved'.format(result.name ))
            else:
                success +=1
        print('No of blocks : {0}'.format(len(blocks)))
        print('\nFiles copied/moved Successfully : {0}'.format(success))


        for block in blocks:
            blockname = block
            block_folder = os.path.join(block_path,blockname).replace('\\','/')
            lfiles = AtlassGen.FILELIST(['*.{0}'.format(filetype)],block_folder)
            tilelayout = AtlassTileLayout()
            features = []
            for lf in lfiles:
                path, tilename, ext = AtlassGen.FILESPEC(lf)
                xmin,ymin = tilename.split('_')
                xmax = str(int(xmin)+tilesize)
                ymax = str(int(ymin)+tilesize)

                boxcoords=AtlassGen.GETCOORDS([xmin,ymin],tilesize)
                poly = Polygon([[boxcoords[0],boxcoords[1],boxcoords[2],boxcoords[3],boxcoords[4]]])

                #adding records for json file
                features.append(Feature(geometry=poly, properties={"name": tilename, "xmin": xmin, "ymin":ymin, "xmax":xmax, "ymax":ymax, "tilenum":tilename}))
                tilelayout.addtile(name=tilename, xmin=float(xmin), ymin=float(ymin), xmax=float(xmax), ymax=float(ymax))
                
            jsonfile = 'TileLayout'
            jsonfile = os.path.join(block_folder,'{0}_{1}.json'.format(jsonfile,len(features)))



            feature_collection = FeatureCollection(features)

            with open(jsonfile, 'w') as f:
                dump(feature_collection, f)








    else:
        for i, tile in enumerate(tl_in): 
            
            tilename = '{0}.{1}'.format(tile.name,filetype)

            if i%batchlen==0:
                batch=batch+1
            batchstring='{0}'.format(batch)
            batchstring=batchstring.rjust(3, '0')
            if batches==1:
                output =  os.path.join(outputfolder, tilename).replace("\\", "/")
            else:
                output =  os.path.join(AtlassGen.makedir('{0}/Batch_{1}'.format(outputfolder,batchstring)), tilename).replace("\\", "/")

            input = os.path.join(intputfolder, tilename).replace("\\", "/")
            
            if copy:
                tasks[tilename] = AtlassTask(tilename, copyfile, input, output)
            elif move:
                tasks[tilename] = AtlassTask(tilename, movefiles, input, output)
            else:
                print("no command selected")


        p=Pool(processes=cores)      
        results=p.map(AtlassTaskRunner.taskmanager,tasks.values())

        success = 0
        for result in results:
            if not result.success:
                print('File {0} could Not be copied/moved'.format(result.name ))
            else:
                success +=1
        
        print('Files copied/moved Successfully : {0}'.format(success))

if __name__ == "__main__":
    main()         
