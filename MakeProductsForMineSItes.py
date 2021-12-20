#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *


#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 01/10/2016 -Alex Rixon - Added functionality to create hydro flattening points. 
# 01/10/2016 -Alex Rixon - Added functionality to create CHM  
# 30/09/2016 -Alex Rixon - Added functionality to create DHM 
# 20/09/2016 -Alex Rixon - Original development Alex Rixon
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

#-----------------------------------------------------------------------------------------------------------------
#grid class
#-----------------------------------------------------------------------------------------------------------------
      
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
@Gooey(program_name="Make Products for mine sites", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=2)
def param_parser():
    main_parser=GooeyParser(description="Make Products for mine sites")
    main_parser.add_argument("projname", metavar="Project Name",default='')
    main_parser.add_argument("inputpath", metavar="Output Directory",widget="DirChooser", help="Input Directory", default='')
    main_parser.add_argument("filetype", metavar="Input filetype", default='laz')
    main_parser.add_argument("inputgeojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default='')
    main_parser.add_argument("aoi", metavar="AOI", widget="FileChooser", default ='')
    main_parser.add_argument("zshift", metavar="Z shift", help="Z shif to be applied on all products")
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default='')
    main_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default='') 
    main_parser.add_argument("cores", metavar="Cores", default=8) 
    product_group = main_parser.add_argument_group("Products", "Select Output Products", gooey_options={'show_border': True,'columns': 2})
    product_group.add_argument("-las", "--genLAS", metavar="LAS", action='store_true')
    product_group.add_argument("-lasfiletype", metavar="Output file format LAS/LAZ", default = "laz")
    product_group.add_argument("-mkp", "--genMKP", metavar="MKP", action='store_true')
    product_group.add_argument("-mkpfiletype", metavar="Output File format LAS/LAZ/TXT", default = "laz")
    product_group.add_argument("-dem", "--genDEM", metavar="DEM", action='store_true')
    product_group.add_argument("-demstep", metavar="DEM step", default = 1.0, type=float)
    product_group.add_argument("-dsm", "--genDSM", metavar="DSM", action='store_true')
    product_group.add_argument("-dsmstep", metavar="DSM step", default = 1.0, type=float)
    product_group.add_argument("-chm", "--genCHM", metavar="CHM", action='store_true')
    product_group.add_argument("-chmstep", metavar="CHM step", default = 1.0, type=float)

    return main_parser.parse_args()


def makeBufferedFiles(input, outputpath, x, y, filename,tilesize, buffer, nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeCHM, filetype, step, chmstep):

    if isinstance(input, str):
        input = [input]

    output = []
    bufflasfile = os.path.join(outputpath,'{0}.{1}'.format(filename, filetype)).replace('\\','/') 
    keep='-keep_xy {0} {1} {2} {3}'.format(str(x-buffer), y-buffer, x+tilesize+buffer, y+tilesize+buffer)
    keep=keep.split()
    log = ''

    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i'] + input + ['-olaz','-o', bufflasfile,'-merged','-keep_class'] + gndclasses + keep #'-rescale',0.001,0.001,0.001,
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)      
        

        if makeDSM:
            dsmgridfile = os.path.join(outputpath,'{0}_dsm_grid.asc'.format(filename)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + input + ['-merged','-oasc','-o',dsmgridfile,'-nbits',32,'-fill',0,'-step',step,'-elevation','-highest','-first_only','-subcircle',step/4]
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)] + ['-keep_class']+ nongndclasses
            subprocessargs=list(map(str,subprocessargs))
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        if makeCHM:
            chmgridfile = os.path.join(outputpath,'{0}_chm_grid.asc'.format(filename)).replace('\\','/')
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i'] + input + ['-merged','-oasc','-o',chmgridfile,'-nbits',32,'-fill',0,'-step',chmstep,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/chmstep), '-nrows',math.ceil((tilesize)/chmstep)] + ['-keep_class']+ chmclasses
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)


    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making Buffered for {0} /nException {1}".format(bufflasfile, e)
        return(False,None, log)

    finally:
        if os.path.isfile(bufflasfile):
            log = "Making Buffered for {0} Success".format(bufflasfile)
            return (True,bufflasfile, log)

        else: 
            log = "Making Buffered for {0} Failed".format(bufflasfile)
            return (False,None, log)

def asciigridtolas(input, output , filetype):
    '''
    Converts an ascii file to a las/laz file and retains the milimetre precision.
    '''

    log = ''
    if os.path.isfile(input):
        print('Converting {0} to las'.format(input))
    try:
       #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', input, '-o{0}'.format(filetype), '-o', output, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting {0} file  to {1} Failed at exception'.format(input, filetype)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {0} file  to {1} success'.format(input, filetype)
            return (True, output, log)
        else:
            log ='Converting {0} file  to {1} Failed'.format(input, filetype)
            return (False, output, log)

def lastoasciigrid(x,y,inputF, output, tilesize, step):
    '''
    Converts a las/laz file to ascii and retains the milimetre precision.
    '''

    if os.path.isfile(inputF):
        log = ''
        try:
        #las2las -i <dtmfile> -olas -o <dtmlazfile>
            subprocessargs=['C:/LAStools/bin/lasgrid.exe','-i', inputF,'-oasc','-o', output, '-nbits',32,'-fill',0,'-step',step,'-elevation','-highest']
            subprocessargs=subprocessargs+['-ll',x,y,'-ncols',math.ceil((tilesize)/step), '-nrows',math.ceil((tilesize)/step)]
            subprocessargs=list(map(str,subprocessargs))       
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            print(log)
            return (False,None,log)

        except:
            log ='Converting las to asc Failed at exception for : {0}'.format(inputF)
            return (False, output, log)
        finally:
            if os.path.isfile(output):
                log ='Converting las to asc success for : {0}'.format(inputF)
                return (True, output, log)
            else:
                log ='Converting las to asc Failed for {0}'.format(inputF)
                return (False, output, log)
    else:
        return(True,None,'Not input File')



def txttolas(inputtxt,output):
    '''
    Converts a txt to laz file .
    '''
    log = ''
    if os.path.isfile(inputtxt):
        print('Converting {0} to las'.format(inputtxt))
    try:
    #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', inputtxt, '-olaz', '-o', output] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting {0} file  to laz Failed at exception'.format(inputtxt)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {0} file  to laz success'.format(inputtxt)
            return (True, output, log)
        else:
            log ='Converting {0} file  to laz Failed'.format(inputtxt)
            return (False, output, log)


def lastotxt(inputlas,output):
    '''
    Converts a laz to txt file .
    '''
    log = ''
    if os.path.isfile(inputlas):
        print('Converting {0} to las'.format(inputlas))
    try:
    #las2las -i <dtmfile> -olas -o <dtmlazfile>
        subprocessargs=['C:/LAStools/bin/las2las.exe','-i', inputtxt, '-olaz', '-o', output, '-rescale', 0.001, 0.001, 0.001] 
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log ='Converting {0} file  to laz Failed at exception'.format(inputlas)
        return (False, output, log)
    finally:
        if os.path.isfile(output):
            log ='Converting {0} file  to laz success'.format(inputlas)
            return (True, output, log)
        else:
            log ='Converting {0} file  to laz Failed'.format(inputlas)
            return (False, output, log)

def index(input):
   
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', input]
        subprocessargs=list(map(str,subprocessargs)) 
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)
        return(True, None, "Success")

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        return(False, None, "Error")


         
def shiftasc(tilename,filename,xmin,ymin, inputdir,proddir, proddir_out, zshift, step, tilesize):

    print('shifting')
    

    #convert to laz
    inputasc = os.path.join(inputdir,'{0}.asc'.format(filename)).replace('\\','/')
    inputlaz = os.path.join(proddir,'{0}.laz'.format(filename)).replace('\\','/')
    asciigridtolas(inputasc, inputlaz , 'laz')

    #shift laz
    outputlaz = os.path.join(proddir,'{0}_shifted.laz'.format(filename)).replace('\\','/')
    shiftlas(inputlaz, outputlaz,zshift)

    #shift laz to asc again
    outputasc = os.path.join(proddir_out,'{0}.asc'.format(filename)).replace('\\','/')
    lastoasciigrid(int(xmin),int(ymin), outputlaz, outputasc, tilesize, step)

    if os.path.isfile(outputasc):
        log = '\nShifting completed for {0}'.format(outputasc)
        return (True, outputasc, log)
    else:
        log ='\nShifting {} Failed'.format(outputasc)
        return (False, None, log)
        
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

def genProductsperTile(tl_in, tl_out,xmin,ymin,xmax,ymax,tilename,tilesize,productlist,inputfolder,workingdir,outputdir,infiletype,hydropointsfiles,buffer,nongndclasses, gndclasses, chmclasses, hydrogridclasses,makeMKP, makeDEM, makeDSM, makeCHM, step, chmstep,kill,clipshape,aoifiles,prjfile,merged,projname,gsd,outfiletype):



    if not projname == None:
        proj = '{0}_'.format(projname)
    else:
        proj = ''

    #########################################################################################################################
    #Making the neighbourhood files
    #


    print('Creating tile neighbourhood for : {0}'.format(tilename))
    buffdir = AtlassGen.makedir(os.path.join(workingdir, 'buffered')).replace('\\','/')
    neighbourlasfiles = []
    neighbours = []
    makebuff_results = []
    deletefiles = []
    try:
        neighbours =  tl_in.gettilesfrombounds(xmin-buffer,ymin-buffer,xmax+buffer,ymax+buffer)

    except:
        print("tile: {0} does not exist in geojson file".format(tilename))

    print('Neighbours : {0}'.format(neighbours))
    
    #files
    for neighbour in neighbours:
        neighbour = os.path.join(inputfolder, '{0}.{1}'.format(neighbour, filetype))
        if os.path.isfile(neighbour):
            print('\n{0}'.format(neighbour))
            neighbourlasfiles.append(neighbour)
        else:
            print('\nFile {0} could not be found in {1}'.format(neighbour, inputfolder))

    makebuff_results = makeBufferedFiles(neighbourlasfiles, buffdir, int(xmin), int(ymin), tilename, int(tilesize), int(buffer),nongndclasses, gndclasses, chmclasses, hydrogridclasses, makeDEM, makeDSM, makeCHM, filetype, step, chmstep)

    deletefiles.append(makebuff_results[1])


    for product in productlist:
        #######################################################################################################################
        #Make relavant product with the buffered las files
        #input buffered las file ?????
        proddir = AtlassGen.makedir(os.path.join(workingdir, product)).replace('\\','/')
        proddir_out = AtlassGen.makedir(os.path.join(outputdir, product)).replace('\\','/')
        product_files = []
        prjfile1 = os.path.join(proddir,'{0}{1}-GRID_{2}_{3}_{4}m.prj'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')
        output = os.path.join(proddir,'{0}{1}-GRID_{2}_{3}_{4}m.asc'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')


        product_files.append(output)
        product_files.append(prjfile1)

        print('Making {0}'.format(product))
                            
        if makebuff_results[0]:

            if product =='LAS':
                #files
                input=os.path.join(inputfolder,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                MakeLAS(tilename, input, proddir, output,outfiletype)

            if product =='MKP':
                #files
                input=os.path.join(inputfolder,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                MakeMKP(tilename, input, proddir, output, buffer,outfiletype)
                
            if product =='DEM':
                #files
                input=os.path.join(buffdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                MakeDEM(int(xmin), int(ymin), tilename, input, proddir, output, buffer, kill, step, gndclasses, hydropointsfiles, int(tilesize), filetype)


            if product =='DSM':
                #files
                dsmgridfile = os.path.join(buffdir,'{0}_dsm_grid.asc'.format(tilename)).replace('\\','/')
                demfile = os.path.join(outputdir,'DEM/{0}DEM-GRID_{1}_{2}_{3}m.asc'.format(proj,gsd,tilename,tilesize)).replace('\\','/')
                MakeDSM(demfile, dsmgridfile, output, step, tilename, int(xmin), int(ymin), nongndclasses, int(tilesize), buffer )               


            if product =='CHM':
                #files
                #demfile = os.path.join(workingdir,'DEM/{0}_DEM.asc'.format(tilename)).replace('\\','/') 
                input=os.path.join(buffdir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') 
                chmgridfile = os.path.join(buffdir,'{0}_chm_grid.asc'.format(tilename)).replace('\\','/')
                chmdemgridfile = os.path.join(buffdir,'{0}_CHM_DEM_grid.asc'.format(tilename)).replace('\\','/')
                MakeCHM(int(xmin), int(ymin), input, chmgridfile, output, chmdemgridfile, tilename, buffer, kill, step, chmstep, int(tilesize), filetype)



        if os.path.isfile(output):
            shutil.copyfile(prjfile, prjfile1) 

            # Run the following steps only if clip shape or merged or selected
            if clipshape or merged:
                #######################################################################################################################
                #Convert asci to laz
                #asciigridtolas(dtmlazfile)

                print('Converting ASC to LAZ')


                #files
                time.sleep(1)
                asc=output
                las=os.path.join(proddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')

                asciigridtolas(asc, las, filetype)
                deletefiles.append(las)
                

                #######################################################################################################################
                #Index the product laz files
                #index(demlazfile)

                index(las)
                lax=os.path.join(proddir,'{0}.lax'.format(tilename)).replace('\\','/')
                deletefiles.append(lax)

            ###########################################################################################################################
            #Clipping the product las files to the AOI
            #lasclip demlazfile
            if clipshape:
                prodclippeddir = AtlassGen.makedir(os.path.join(proddir, 'clipped')).replace('\\','/')
                print('Clipping the las files to AOI')

                for aoi in aoifiles:

                    path, aoiname, ext = AtlassGen.FILESPEC(aoi)
                    print('Clipping files to the AOI : {0}'.format(aoi))
                    aoidir = AtlassGen.makedir(os.path.join(prodclippeddir,aoiname))

                    print(tilename)


                    #files 
                    lasinput=os.path.join(proddir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/') #dtmlaz
                    lasoutput = os.path.join(aoidir,'{0}.{1}'.format(tilename, filetype)).replace('\\','/')
            
                    clip(lasinput, lasoutput, aoi, filetype)

                    if os.path.isfile(lasoutput):
                        deletefiles.append(lasoutput)
                        print('Converting Clipped {0} to asc'.format(filetype))
                    
                        #############################################################################################################################
                        #Convert the laz files to asci
                        #lasgrid
                        #TODo
                        #files

                        ascoutput=os.path.join(aoidir,'{0}{1}-GRID_{2}_{3}_{4}m.asc'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')
                        prjfile1 = os.path.join(aoidir,'{0}{1}-GRID_{2}_{3}_{4}m.prj'.format(proj,product,gsd,tilename,tilesize)).replace('\\','/')

                        if product == 'CHM':
                            step = chmstep

                        lastoasciigrid(int(xmin), int(ymin), lasoutput, ascoutput, int(tilesize), step)
                        product_files.append(ascoutput)
                        product_files.append(prjfile1)
                        shutil.copyfile(prjfile, prjfile1) 
            

            else:
                print("Finished making products. No clipping selected")
    
        
        else:
            print("{0} file not created for {1}".format(product, tilename))
            return(True,tilename,"{0} file not created for {1}".format(product, tilename))


        print("-----------------Copying product files -----------------")
        for sourcef in product_files:

            destf = sourcef.replace(proddir, proddir_out)
            path,df,ext = AtlassGen.FILESPEC(destf)
            if not os.path.exists(path):
                AtlassGen.makedir(path)
            
            print("copying {0}\n".format(sourcef))
            try:
                shutil.copy(sourcef, destf)
            except Exception as e:
                print ("Unable to copy file.{0}".format(e))
            finally:
                print('deleting {0}'.format(sourcef))
                os.remove(sourcef)
                
    print("-------------------------------------------------------")
    if not merged:         
        for deletef in deletefiles:
            print('Deleting {0}'.format(deletef))
            if os.path.isfile(deletef):
                os.remove(deletef)

    log = "Finished making products. No clipping selected"
    return(True,tilename,log)                
    

      
    

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support() 
    args = param_parser()

    #create variables from gui
    outputpath = args.outputpath.replace('\\','/')
    workingpath = args.workpath.replace('\\','/')
    projname = args.projname
    inputpath = args.inputpath.replace('\\','/')
    zshift = args.zshift
    aoi = args.aoi.replace('\\','/')
    filetype = args.filetype
    genMKP=args.genMKP
    genLAS=args.genLAS
    genDSM=args.genDSM
    genCHM=args.genCHM
    genDEM=args.genDEM
    lasfiletype = args.lasfiletype
    mkpfiletype = args.mkpfiletype
    demstep = float(args.demstep)
    dsmstep = float(args.dsmstep)
    chmstep = float(args.chmstep)
    cores = int(args.cores)


    logpath = os.path.join(outputpath,'log.txt').replace('\\','/')

    log = open(logpath, 'w')

    ingeojsonfile = args.inputgeojsonfile


    productlist = []
    if genLAS:
        productlist.append(['LAS', lasfiletype])
    if genMKP:
        productlist.append(['MKP', mkpfiletype])
    if genDEM:
        productlist.append(['DEM', demstep])
    if genDSM:
        productlist.append(['DSM', dsmstep])   
    if genCHM:
        productlist.append(['CHM', chmstep])

    
    #read tilelayout into library
    tl_in = AtlassTileLayout()
    tl_in.fromjson(ingeojsonfile)

    print("No of Tiles in Input Tilelayout : {0}".format(len(tl_in)))

    dt = strftime("%y%m%d_%H%M")
    dt = ''

    outputdir = AtlassGen.makedir(os.path.join(outputpath, '{0}_ProdGen'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, '{0}_ProdGen_working'.format(dt))).replace('\\','/')


    gen_products = {}
    gen_products_results = []
    
    ########################################################################################################################
    ## Make FCM for tiles in the output tilelayout
    #######################################################################################################################

    for tile in tl_in: 
        xmin = tile.xmin
        ymin = tile.ymin
        xmax = tile.xmax
        ymax = tile.ymax
        tilename = tile.name
        tilesize = int(tile.xmax - tile.xmin)


        gen_products[tilename] = AtlassTask(tilename, genProductsperTile,tl_in,xmin,ymin,xmax,ymax,tilename,tilesize,productlist,zshift,workingdir,outputdir,outfiletype)
   

    p=Pool(processes=cores)        
    gen_products_results=p.map(AtlassTaskRunner.taskmanager,gen_products.values())   

    ########################################################################################################################
    ## Merge files
    #######################################################################################################################

    for result in gen_products_results:
        log.write(result.log)

    print("------------- Finished shifting products --------------------------")
    

    return()
    
if __name__ == "__main__":
    main(sys.argv[1:]) 

