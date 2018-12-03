#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import os
from gooey import Gooey, GooeyParser
import subprocess
from Atlass import *
import datetime
from time import strftime
from shutil import copyfile
import glob

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make Contour", use_legacy_titles=True, required_cols=1, default_size=(1000,800))
def param_parser():
    parser=GooeyParser(description="Make Contour")
    parser.add_argument("inputfolder", metavar="Contour Points Folder", widget="DirChooser", help="Select input files (.las/.laz)", default='')
    parser.add_argument("filetype",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='las')
    parser.add_argument("layoutfile", metavar="TileLayout file", widget="FileChooser", help="TileLayout file(.json)", default='')
    #parser.add_argument("hydrofiles", metavar="Hydro LAS files", widget="MultiFileChooser", help="Select Hydro files (las/laz )", default='')
    parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default='')
    parser.add_argument("aoi", metavar="AOI", widget="FileChooser", help="Area of interest(.shp file)", default="")
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

def makegmsfiles(filename,inpath,gms,buffout,clipout,xmin,ymin,xmax,ymax, zone, AOI_clip, index):

    template = "\\\\10.10.10.100\\projects\\PythonScripts\\templates\\Template.gms"
    dstfile = os.path.join(gms,'{0}.{1}'.format(filename,'gms')).replace('\\','/')
    gms = gms+"\\"
    buffout = buffout+"\\"
    inpath = inpath+"\\"
    clipout = clipout+"\\"
    copyfile(template, dstfile)
    result = {}

    try:
        with open(dstfile, 'r') as g:
            data = g.read()

            while '<Filename>' in data:
                data = data.replace('<Filename>', filename)
            while '<Outpath>' in data:
                data = data.replace('<Outpath>', gms)
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
                data = data.replace('<xmin>', xmin)
            while '<ymin>' in data:
                data = data.replace('<ymin>', ymin)
            while '<xmax>' in data:
                data = data.replace('<xmax>', xmax)
            while '<ymax>' in data:
                data = data.replace('<ymax>', ymax)
            while '<index>' in data:
                data = data.replace('<index>', index)

        with open(dstfile, 'w') as f:
                f.write(data)
        if os.path.exists(dstfile):
            result = {"file":filename, "state" :"Success", "output":dstfile }
        else:
            result = {"file":filename, "state" :"Error", "output":"Could not generate GMS for : {0}".format(filename) }
    except:
        result = {"file":filename, "state" :"Error", "output":"Could not generate GMS for : {0}".format(filename) }



    return(result)


def rungmsfiles(gmpath, gmsfile):
    results = {}

    try:
        subprocessargs=[gmpath, gmsfile]
        subprocessargs=map(str,subprocessargs) 
        subprocess.call(subprocessargs)
        result = {"file":gmsfile, "state":"Success", "output" : "" }
    except:
        result = {"file":gmsfile, "state":"Error", "output": "Could not run gms file"}

    return(result)


def makecontours(tile, buffer, neighbourfiles, contourinterval, outpath):
    result = {}
    #set up clipping
    keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
    keep=keep.split()

    outfile = os.path.join(outpath,'{0}.{1}'.format(tile.name,'shp')).replace('\\','/')
    try:
        subprocessargs=['C:/LAStools/bin/blast2iso.exe','-i'] + neighbourfiles + ['-merged','-oshp', '-iso_every', contourinterval,'-clean',2,'-o',outfile] + keep 
        subprocessargs=map(str,subprocessargs) 
        subprocess.call(subprocessargs)

        result = {"file":tile.name, "state":"Success", "output" : outfile }
    except:
        result = {"file":tile.name, "state":"Error", "output": "Could not make contour"}

    return(result)


   
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
    gmexe = args.gmexe
    buffer = args.buffer
    cores = args.cores
    contourinterval = args.contourinterval
    index = float(contourinterval)*(float(args.indexinterval))

    al = Atlasslogger(outpath)

    tilelayout = AtlassTileLayout()
    tilelayout.fromjson(tilelayoutfile)

    if not contourfiles:
        al.PrintMsg ("Please select the correct file type", "No Selected files")
        quit

    dt = strftime("%y%m%d_%H%M")

    contour_buffered_out = AtlassGen.makedir(os.path.join(outpath, (dt+'_contour_buffered')))
    gms = AtlassGen.makedir(os.path.join(contour_buffered_out, 'scripts'))
    bufferedout = AtlassGen.makedir(os.path.join(contour_buffered_out, ('buffered_{0}m_contours'.format(buffer))))
    clippedout = AtlassGen.makedir(os.path.join(contour_buffered_out, ('clipped'.format(buffer))))

    MAKE_CONTOUR_TASKS=[]
    MAKE_GMSFILE_TASKS=[]
    RUN_GMSFILE_TASKS=[]

    for contourfile in contourfiles:
        path, filename, ext = AtlassGen.FILESPEC(contourfile)
        tile = tilelayout.gettile(filename)
        
        neighbourfiles = []
        neighbours = tile.getneighbours(buffer)
        for neighbour in neighbours:
            neighbourfiles.append(os.path.join(path,'{0}.{1}'.format(neighbour,ext)).replace('\\','/'))
        
        MAKE_CONTOUR_TASKS.append((makecontours,(tile, buffer, neighbourfiles, contourinterval, contour_buffered_out)))
        MAKE_GMSFILE_TASKS.append((makegmsfiles,(filename,contour_buffered_out,gms,bufferedout,clippedout,str(tile.xmin),str(tile.ymin),str(tile.xmax),str(tile.ymax), zone, aoi, str(index))))
        gmscript = os.path.join(gms,'{0}.{1}'.format(filename,'gms')).replace('\\','/')
        RUN_GMSFILE_TASKS.append((rungmsfiles,(gmexe,gmscript)))
    
    #Multiprocess the tasks   
    atr1 = AtlassTaskRunner(cores,MAKE_CONTOUR_TASKS,'Making Contours', al, str(args))

    if not atr1.failedscript:
        atr2 = AtlassTaskRunner(cores,MAKE_GMSFILE_TASKS,'Making Global Mapper Scripts', al, str(args))
    else:
        al.PrintMsg("Making Countours Failed. Aborting Program", "ERROR")
        al.DumpLog();
        exit
    
    if not atr2.failedscript:
        atr3 = AtlassTaskRunner(cores,RUN_GMSFILE_TASKS,'Running Global Mapper Scripts', al, str(args))
        
    else:
        al.PrintMsg("Running GMS Failed. Aborting Program", "ERROR")
        al.DumpLog();
        exit

    al.DumpLog();

    return

if __name__ == "__main__":
    main()       

