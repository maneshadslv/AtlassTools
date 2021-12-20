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
@Gooey(program_name="Make Products for new control", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=2)
def param_parser():
    main_parser=GooeyParser(description="Shift Products")
    main_parser.add_argument("inputgeojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default='')
    main_parser.add_argument("zshift", metavar="Z shift", help="Z shif to be applied on all products")
    main_parser.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default='')
    main_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default='') 
    main_parser.add_argument("cores", metavar="Cores", default=8) 
    product_group = main_parser.add_argument_group("Products", "Select Output Products", gooey_options={'show_border': True,'columns': 3})
    product_group.add_argument("-las", "--shiftLAS", metavar="LAS", action='store_true')
    product_group.add_argument("-lasfiletype", metavar="LAS/LAZ", default = "laz")
    product_group.add_argument("-lasinpath", metavar="LAS Directory",widget="DirChooser", default = "")
    product_group.add_argument("-mkp", "--shiftMKP", metavar="MKP", action='store_true')
    product_group.add_argument("-mkpfiletype", metavar="LAS/LAZ", default = "laz")
    product_group.add_argument("-mkpinpath", metavar="MKP Directory",widget="DirChooser", default = "")
    product_group.add_argument("-dem", "--shiftDEM", metavar="DEM", action='store_true')
    product_group.add_argument("-demstep", metavar="DEM step", default = 1.0, type=float)
    product_group.add_argument("-deminpath", metavar="DEM Directory",widget="DirChooser", default = "")
    product_group.add_argument("-dsm", "--shiftDSM", metavar="DSM", action='store_true')
    product_group.add_argument("-dsmstep", metavar="DSM step", default = 1.0, type=float)
    product_group.add_argument("-dsminpath", metavar="DSM Directory",widget="DirChooser", default = "")
    product_group.add_argument("-chm", "--shiftCHM", metavar="CHM", action='store_true')
    product_group.add_argument("-chmstep", metavar="CHM step", default = 1.0, type=float)
    product_group.add_argument("-chminpath", metavar="CHM Directory",widget="DirChooser", default = "")

    return main_parser.parse_args()


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


            #inputasc,filename,xmin,ymin, inputdir,workingdir,outputdir, zshift, step, int(tilesize)
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



def shiftProductsperTile(tl_in,xmin,ymin,xmax,ymax,tilename,tilesize,productlist,zshift,workingdir,outputdir):

    print('\n\n Starting to Shift TILE : {0}'.format(tilename))

    for product in productlist:

 
        proddir = AtlassGen.makedir(os.path.join(workingdir, product[0])).replace('\\','/')
        proddir_out = AtlassGen.makedir(os.path.join(outputdir, product[0])).replace('\\','/')


        print('Shifting {0}'.format(product))
                            
        if product[0] =='LAS':
            #files
            inputlas = os.path.join(product[1],'{0}.{1}'.format(tilename,product[2])).replace('\\','/')
            if not os.path.isfile(inputlas):
                print("{0} not in input dir {1}".format(tilename,product[1]))
            
            else:
                outputlas = os.path.join(proddir_out,'{0}.{1}'.format(tilename,product[2])).replace('\\','/')
                result = shiftlas(inputlas, outputlas,zshift)

        if product[0] =='MKP':
            if product[2]=='laz' or product[2]=='las':
                #files
                inputlas = os.path.join(product[1],'{0}.{1}'.format(tilename,product[2])).replace('\\','/')
                if not os.path.isfile(inputlas):
                    print("{0} not in input dir {1}".format(tilename,product[1]))

                else:
                    outputlas = os.path.join(proddir_out,'{0}.{1}'.format(tilename,product[2])).replace('\\','/')
                    result = shiftlas(inputlas, outputlas,zshift)

            elif product[2] =='txt':
                #files
                inputtxt = os.path.join(product[1],'{0}.{1}'.format(tilename,product[2])).replace('\\','/')
                if not os.path.isfile(inputtxt):
                    print("{0} not in input dir {1}".format(tilename,product[1]))

                else:
                    inputlas = os.path.join(proddir,'{0}.laz'.format(tilename)).replace('\\','/')
                    txttolas(inputtxt,inputlas)
                    outputlas = os.path.join(proddir_out,'{0}.{1}'.format(tilename,product[2])).replace('\\','/')
                    result = shiftlas(inputlas, outputlas,zshift)


            
        if product[0] =='DEM' or product[0]=='DSM' or product[0]=='CHM':
            step = int(product[2])
            gsd = ''
            if step < 1:
                gsd = '0_{0}'.format(int(step*100))
            elif step < 10:
                gsd = '00{0}'.format(str(int(step)))
            elif step > 10:
                gsd = '0{0}'.format(str(int(step)))

            
            files = AtlassGen.FILELIST(['*{0}*.asc'.format(tilename)], product[1])

            if len(files) > 0:
                path,filename,ext = AtlassGen.FILESPEC(files[0])
                print(filename)
                result = shiftasc(tilename,filename,xmin,ymin, product[1],proddir, proddir_out, zshift, step, int(tilesize))
            
            else:
                print("{0} not in input dir {1}".format(tilename,product[1]))


 

    return(True,tilename,result[2])                
    

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    freeze_support() 
    args = param_parser()


    #create variables from gui
    outputpath = args.outputpath.replace('\\','/')
    workingpath = args.workpath.replace('\\','/')
    zshift = args.zshift

    shiftMKP=args.shiftMKP
    shiftLAS=args.shiftLAS
    shiftDSM=args.shiftDSM
    shiftCHM=args.shiftCHM
    shiftDEM=args.shiftDEM
    lasinpath = args.lasinpath
    mkpinpath = args.mkpinpath
    deminpath = args.deminpath
    dsminpath = args.dsminpath
    chminpath = args.chminpath    
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
    if shiftLAS:
        productlist.append(['LAS',lasinpath, lasfiletype])
    if shiftMKP:
        productlist.append(['MKP', mkpinpath, mkpfiletype])
    if shiftDEM:
        productlist.append(['DEM', deminpath, demstep])
    if shiftDSM:
        productlist.append(['DSM', dsminpath, dsmstep])   
    if shiftCHM:
        productlist.append(['CHM', chminpath, chmstep])

    
    #read tilelayout into library
    tl_in = AtlassTileLayout()
    tl_in.fromjson(ingeojsonfile)

    print("No of Tiles in Input Tilelayout : {0}".format(len(tl_in)))

    dt = strftime("%y%m%d_%H%M")
    dt=''

    outputdir = AtlassGen.makedir(os.path.join(outputpath, '{0}ShiftingProducts'.format(dt))).replace('\\','/')
    workingdir = AtlassGen.makedir(os.path.join(workingpath, '{0}ShiftingProducts_working'.format(dt))).replace('\\','/')


    shift_products = {}
    shift_products_results = []
    
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

        shift_products[tilename] = AtlassTask(tilename, shiftProductsperTile,tl_in,xmin,ymin,xmax,ymax,tilename,tilesize,productlist,zshift,workingdir,outputdir)
   

    p=Pool(processes=cores)        
    shift_products_results=p.map(AtlassTaskRunner.taskmanager,shift_products.values())   

    ########################################################################################################################
    ## Merge files
    #######################################################################################################################

    for result in shift_products_results:
        log.write(result.log)

    print("------------- Finished shifting products --------------------------")
    

    return()
    
if __name__ == "__main__":
    main(sys.argv[1:]) 

