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
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]))
from Atlass_beta1 import *
#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make Contour", use_legacy_titles=True, required_cols=1, default_size=(1000,800))
def param_parser():
    parser=GooeyParser(description="Make Contour")
    parser.add_argument("inputfolder", metavar="Contour Points Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default='')
    #parser.add_argument("hydrofiles", metavar="Hydro LAS files", widget="MultiFileChooser", help="Select Hydro files (las/laz )", default='')
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    parser.add_argument("aoi", metavar="AOI", widget="FileChooser", help="Area of interest(.shp file)", default="")
    parser.add_argument("tilesize", metavar="Tile size", help="Select Size of Tile in meters [size x size]", choices=['100', '250', '500', '1000', '2000'], default='1000')
    parser.add_argument("contourinterval", metavar="Contour interval", help="Provide contour interval", default='0.5')
    parser.add_argument("indexinterval", metavar="Index Interval", help="Provide interval for contour index", default='5')
    parser.add_argument("zone", metavar="Zone", help="Provide Zone", default='')
    parser.add_argument("gmexe", metavar="Global Mapper EXE", widget="FileChooser", help="Location of Global Mapper exe", default="C:\\Program Files\\GlobalMapper16.0_64bit_crack\\global_mapper.exe")
    parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    parser.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=4)

    return parser.parse_args()

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def makegmsfiles(filename,inpath,outpath,buffoutpath,clipoutpath,xmin,ymin,zone, AOI_clip, index, tilesize):

    template = "\\\\10.10.10.100\\projects\\PythonScripts\\templates\\Template.gms"
    dstfile = os.path.join(outpath,'{0}.{1}'.format(filename,'gms')).replace('\\','/')
    outputpath = outpath+"\\"
    buffout = buffoutpath+"\\"
    inpath = inpath+"\\"
    clipout = clipoutpath+"\\"
    copyfile(template, dstfile)
    log = ''

    try:
        with open(dstfile, 'r') as g:
            data = g.read()

            while '<Filename>' in data:
                data = data.replace('<Filename>', filename)
            while '<Outpath>' in data:
                data = data.replace('<Outpath>', outpath)
            while '<InPath>' in data:
                data = data.replace('<InPath>', inpath)
            while '<BuffOutpath>' in data:
                data = data.replace('<BuffOutpath>', buffout)
            while '<ClipOutpath>' in data:
                data = data.replace('<ClipOutpath>', clipout)
            while '<zone>' in data:
                data = data.replace('<zone>', zone)
            while '<AOI_clip>' in data:
                data = data.replace('<AOI_clip>', AOI_clip)
            while '<xmin>' in data:
                data = data.replace('<xmin>', str(xmin))
            while '<ymin>' in data:
                data = data.replace('<ymin>', str(ymin))
            while '<xmax>' in data:
                data = data.replace('<xmax>', str(xmin+tilesize))
            while '<ymax>' in data:
                data = data.replace('<ymax>', str(ymin+tilesize))
            while '<index>' in data:
                data = data.replace('<index>', index)

        with open(dstfile, 'w') as f:
                f.write(data)
        if os.path.exists(dstfile):
            log = 'Successfully created GMS file for :{0}'.format(filename)
            return(True,dstfile,log)
        else:
            log = 'Could not create GMS file for :{0}'.format(filename)
            return(False,None,log)
    except:
        log = 'Could not create GMS file for :{0}, Failed at exception'.format(filename)
        return(False,None,log)






def rungmsfiles(gmpath, gmsfile):
    log = ''

    try:
        subprocessargs=[gmpath, gmsfile]
        subprocessargs=list(map(str,subprocessargs))
        print(subprocessargs)
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        log = 'Making Contours was successful for {0}'.format(gmsfile)
        return (True,None, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (True,None,log)

    except:
        log = 'Could not run GMS file for {0}, Failed at Subprocess'.format(gmsfile)  
        return (False,None, log)


def makecontours(neighbourfiles, output, x, y, filename, buffer, contourinterval, tilesize):
    log = ''
    #set up clipping
    keep='-keep_xy {0} {1} {2} {3}'.format(x-buffer, y-buffer, x+tilesize+buffer, y+tilesize+buffer)
    keep=keep.split()

    try:
        subprocessargs=['C:/LAStools/bin/blast2iso.exe','-i'] + neighbourfiles + ['-merged','-oshp', '-iso_every', contourinterval,'-clean',2,'-o',output] + keep 
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = 'Could not make countours {0}, Failed at Subprocess'.format(filename)  
        return (False,None, log)

    finally:
        if os.path.isfile(output):
            log = 'Making Contours was successful for {0}'.format(filename)
            return (True,output, log)

        else:
            log = 'Could not make contours for {0}'.format(filename)   
            return (False,None, log)



   
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()

    contourfiles = []
    contourfiles = glob.glob(args.inputfolder+"\\*."+args.filetype)
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
    tilesize = args.tilesize

    al = Atlasslogger(outpath)

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)

    if not contourfiles:
        al.PrintMsg ("Please select the correct file type", "No Selected files")
        quit

    dt = strftime("%y%m%d_%H%M")

    contour_buffered_out_path = AtlassGen.makedir(os.path.join(outpath, (dt+'_contour_buffered')))
    gms_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'scripts'))
    bufferedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, ('buffered_{0}m_contours'.format(buffer))))
    clippedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, ('clipped'.format(buffer))))

    #Make Contour Files
    mk_contour_tasks = {}
    for contourfile in contourfiles:
        path, filename, ext = AtlassGen.FILESPEC(contourfile)
        x,y=filename.split('_')
        tile = tilelayout.gettile(filename)
        #file
        output = os.path.join(contour_buffered_out_path,'{0}.{1}'.format(tile.name,'shp')).replace('\\','/')
        neighbourfiles = []
        neighbours = tile.getneighbours(buffer)
        for neighbour in neighbours:
            neighbourfiles.append(os.path.join(path,'{0}.{1}'.format(neighbour,ext)).replace('\\','/'))

        mk_contour_tasks[filename] = AtlassTask(filename, makecontours, neighbourfiles, output, int(x), int(y), filename, int(buffer), contourinterval, int(tilesize))        
        
    p=Pool(processes=cores)      
    mk_contour_results=p.map(AtlassTaskRunner.taskmanager,mk_contour_tasks.values())


    #Make GMS files
    mk_gmsfiles_tasks = {}
    for result in mk_contour_results:
        print(result.success, result.log)
        path, filename, ext = AtlassGen.FILESPEC(result.result)
        x,y=filename.split('_')

        mk_gmsfiles_tasks[filename] = AtlassTask(filename, makegmsfiles,filename,contour_buffered_out_path,gms_path,bufferedout_path,clippedout_path,int(x),int(y), zone, aoi, index, int(tilesize))
    
    
    mk_gmsfiles_results=p.map(AtlassTaskRunner.taskmanager,mk_gmsfiles_tasks.values())


    #Run GMS files
    run_gmsfiles_tasks = {}
    for result in mk_gmsfiles_results:
        print(result.result, result.log)
        path, filename, ext = AtlassGen.FILESPEC(result.result)
        #files
        gmscript = os.path.join(gms_path,'{0}.{1}'.format(filename,'gms')).replace('\\','/')

        run_gmsfiles_tasks[filename] = AtlassTask(filename, rungmsfiles, gmexe, gmscript)

    run_gmsfiles_results=p.map(AtlassTaskRunner.taskmanager,run_gmsfiles_tasks.values())

    #Verify final results
    for result in run_gmsfiles_results:
        print(result.result, result.log)
    
    return

if __name__ == "__main__":
    main()       

