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

class ContourClass:
    def makecontourprocess(tilename,inputfolder,gms_path,bufferedout_path,bufferremoved_path,clippedout_path, buffer,contourinterval,zone,aois,index,hydropointsfiles,gmexe,intilelayoutfile,outtilelayoutfile,prjfile,proj_name,datum,projection,kill):

 
        tl_in = AtlassTileLayout()
        tl_in.fromjson(intilelayoutfile)

        tl_out = AtlassTileLayout()
        tl_out.fromjson(outtilelayoutfile)
        tile = tl_out.gettile(tilename)

        buff_output = os.path.join(bufferedout_path,'{0}.{1}'.format(tilename,'shp')).replace('\\','/')
        neighbours =  tl_in.gettilesfrombounds(tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)    
        #file
       
        output = {}
        neighbourfiles = []


        for neighbour in neighbours:
            neighbourfiles.append(os.path.join(inputfolder,'{0}.{1}'.format(neighbour,'laz')).replace('\\','/'))
        if not (hydropointsfiles == None or hydropointsfiles==''):
             
            hydfile=os.path.join(bufferedout_path,'{0}_hydro.laz'.format(tilename)).replace('\\','/')           
            keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin-buffer,tile.ymin-buffer,tile.xmax+buffer,tile.ymax+buffer)
            keep=keep.split()
            subprocessargs=['C:/LAStools/bin/las2las.exe','-i',hydropointsfiles,'-olaz','-o', hydfile] + keep 
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 
            print("clipped Hydro points")
            if os.path.isfile(hydfile):
                neighbourfiles.append(hydfile)   

        print(neighbourfiles)
        try:
            #Make Contour Files
            ContourClass.makecontours(tilename,neighbourfiles, buff_output, tile,  int(buffer), contourinterval,kill)    

            for aoi in aois:    
                pathb, aoiname,ext = AtlassGen.FILESPEC(aoi)
                aoiname=aoiname.replace(" ","_")
                aoipath = os.path.join(clippedout_path,aoiname).replace('\\','/')
                #Make GMS files    
                gmscript = os.path.join(gms_path,'{0}_{1}.{2}'.format(tilename,aoiname,'gms')).replace('\\','/')
                ContourClass.makegmsfiles(tilename,bufferedout_path,gms_path,bufferremoved_path,aoipath,tile, str(zone), aoi, index,outtilelayoutfile,gmscript,proj_name,datum,projection)

                #Run GMS files

                ContourClass.rungmsfiles(gmexe, gmscript)
                
        
        except:
            log = 'Could not make countours {0}, Failed at Subprocess'.format(tilename)  
            return (False,None, log)

        finally:
            for aoi in aois:
                pathb, aoiname,ext = AtlassGen.FILESPEC(aoi)
                aoiname=aoiname.replace(" ","_")
                aoipath = os.path.join(clippedout_path,aoiname).replace('\\','/')
                output = os.path.join(aoipath,'{0}.{1}'.format(tilename,'shp')).replace('\\','/')
                prjfile_tile = os.path.join(aoipath,'{0}.prj'.format(tilename)).replace('\\','/')
                print(prjfile_tile)
                if os.path.isfile(output):
                    log = 'Making countours for {0} Success'.format(tilename)  
                    shutil.copyfile(prjfile, prjfile_tile) 
                    return (True,output, log)

                else:
                    log = 'Could not make contours for {0}, Outside AOI'.format(tilename)   
                    return (False,None, log)
                

    def makegmsfiles(filename,inpath,outpath,buffoutpath,clipoutpath,tile,zone, AOI_clip, index,tilelayoutfile,dstfile,proj_name,datum,projection):
        scriptpath = os.path.dirname(os.path.realpath(__file__))
        print(scriptpath)
        template = "{0}\\templates\\Template.gms".format(scriptpath)
        
        outputpath = outpath+"\\"
        buffout = buffoutpath+"\\"
        inpath = inpath+"\\"
        clipout = clipoutpath+"\\"
        shutil.copyfile(template, dstfile)
        log = ''

        print(filename,inpath,outpath,buffoutpath,clipoutpath,tile,zone, AOI_clip, index,tilelayoutfile)
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
                while '<datum>' in data:
                    data = data.replace('<datum>', datum)
                while '<projection>' in data:
                    data = data.replace('<projection>', projection)
                while '<proj_name>' in data:
                    data = data.replace('<proj_name>', proj_name)
                while '<zone>' in data:
                    data = data.replace('<zone>', zone)
                while '<AOI_clip>' in data:
                    data = data.replace('<AOI_clip>', AOI_clip)
                while '<xmin>' in data:
                    data = data.replace('<xmin>', str(tile.xmin))
                while '<ymin>' in data:
                    data = data.replace('<ymin>', str(tile.ymin))
                while '<xmax>' in data:
                    data = data.replace('<xmax>', str(tile.xmax))
                while '<ymax>' in data:
                    data = data.replace('<ymax>', str(tile.ymax))
                while '<index>' in data:
                    data = data.replace('<index>', str(index))
                while '<tilelayoutfile>' in data:
                    data = data.replace('<tilelayoutfile>', str(tilelayoutfile))   

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
            #print(subprocessargs)
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


    def makecontours(filename,neighbourfiles, output, tile,buffer, contourinterval,kill):

        log = ''
        #set up clipping
        keep='-keep_xy {0} {1} {2} {3}'.format(tile.xmin-buffer, tile.ymin-buffer, tile.xmax+buffer, tile.ymax+buffer)
        keep=keep.split()
        print(neighbourfiles)

        try:
            ####MANESHA - CHANGED from blas2iso.exe to last2iso64.exe - 02/09/20 ####
            # blas2iso does not do a good job in steaper areas. Gab found issue that had bow ties and touching contours
            ############################################################################################################################
            print("USING LAS2ISO")
            subprocessargs=['C:/LAStools/bin/las2iso64.exe','-i'] + neighbourfiles + ['-merged','-oshp', '-iso_every', contourinterval,'-clean',4,'-o',output,'-kill', kill] + keep 
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

if __name__ == '__main__':

    #python "\\10.10.10.142\projects\PythonScripts\lib\atlass\MakeContoursLib.py" #tilename# inputfolder outputfolder buffer contourinterval index zone aoi hydropointsfiles gmexe tilelayoutfile.json
    #python "\\10.10.10.142\projects\PythonScripts\lib\atlass\MakeContoursLib.py" #name# "D:\temp\Test_TL" "D:\temp\Test_TL" 200 0.5 5 55 "D:\temp\test_aois\aoi2.shp" "" "C:\Program Files\GlobalMapper21.0_64bit\global_mapper.exe" "D:\temp\Test_TL\TileLayout_18.json"
    print('Number of variables provided : {0}'.format(len(sys.argv)))
    print(sys.argv[1:12])
    tilename,inputfolder, outputfolder, buffer, contourinterval,index,zone,aoi,hydropointsfiles,gmexe,tilelayoutfile = sys.argv[1:12]
    print(tilelayoutfile)

    dt = strftime("%y%m%d_%H%M")

    contour_buffered_out_path = AtlassGen.makedir(os.path.join(outputfolder, ('{0}_makeContour_{1}'.format(dt,contourinterval))))
    gms_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'scripts'))
    bufferedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, ('buffered_{0}m_contours'.format(buffer))))
    bufferremoved_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'buffer_removed'))
    clippedout_path = AtlassGen.makedir(os.path.join(contour_buffered_out_path, 'clipped_shp'))

    ContourClass.makecontourprocess(tilename,inputfolder,gms_path,bufferedout_path,bufferremoved_path,clippedout_path, int(buffer),float(contourinterval),int(zone),aoi,index,hydropointsfiles,gmexe,tilelayoutfile)

