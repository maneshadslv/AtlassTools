import itertools
import time
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import json
import os, glob
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
from MakeHydroLib import *
from shapely.geometry import Polygon, Point, LinearRing
import os
import shapefile_old as shp 
from collections import defaultdict , OrderedDict

@Gooey(program_name="Make Hydro Grids", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=2, optional_cols=3,advance=True, navigation='SIDEBAR',)
def param_parser():

    stored_args = {}
    # get the script name without the extension & use it to build up
    # the json filename
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    congifg_folder = AtlassGen.makedir("C:\\pythontools")
    args_file = os.path.join(congifg_folder,"{}-args.json".format(script_name))
    # Read in the prior arguments as a dictionary
    if os.path.isfile(args_file):
        with open(args_file) as data_file:
            stored_args = json.load(data_file)

    parser=GooeyParser(description="Make Hydro Grids")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    step1_parser = sub_pars.add_parser('Step_1', help='Preparation of Hydro voids as individual shp files')
    step1_parser.add_argument("laspath", metavar="LAS files", widget="DirChooser", help="Select input las/laz file", default=stored_args.get('laspath'))
    step1_parser.add_argument("filetype",metavar="Input File type", help="laz or las", default='laz')
    step1_parser.add_argument("geojsonfile", metavar="Input TileLayout file", widget="FileChooser", help="Select .json file", default=stored_args.get('geojsonfile'))
    step1_parser.add_argument("deliverypath", metavar="Output Directory",widget="DirChooser", help="Output directory(Storage Path)", default=stored_args.get('deliverypath'))
    step1_parser.add_argument("workpath", metavar="Working Directory",widget="DirChooser", help="Working directory", default=stored_args.get('workpath'))    
    step1_parser.add_argument("aoi", metavar="Aoi Shp file",widget="FileChooser",default=stored_args.get('aoi'))
    step1_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    step1_parser.add_argument("-b", "--buffer",metavar="Buffer", help="Provide buffer", type=int, default=200)
    step1_parser.add_argument("-f", "--fill",metavar="Fill", help="Fills voids in the grid with a square search radius of the fill value ", type=int, default=100)
    step1_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    step1_parser.add_argument("-hpfiles", "--hydropointsfiles", widget="MultiFileChooser", metavar = "Hydro Points Files", help="Select files with Hydro points")
    output_group = step1_parser.add_argument_group("Create the merge files only", "Run this only if the merge files does not get created in this step", gooey_options={'show_border': True,'columns': 3})
    output_group.add_argument("--createmerge", metavar="Create Merge", action='store_true', default=False)
    output_group.add_argument("--lazpath", metavar="LAZ File Path", widget="DirChooser", help="Select folder of the laz files generated in step 1", default=stored_args.get('lazfiles'))
    step2_parser = sub_pars.add_parser('Step_2', help='Calculation of Elevation for each void- Run after global mapper step')
    step2_parser.add_argument("lazfile", metavar="Hydro points Laz Files", widget="MultiFileChooser", help="This should be small water bodies only", default=stored_args.get('lazfile'))
    step2_parser.add_argument("outputfolder", metavar="Output folder", widget="DirChooser", help="Output folder for Hydro Laz file", default=stored_args.get('outputfolder'))
    step2_parser.add_argument("-s", "--step", metavar="Step", help="Provide step", type=float, default = 1.0)
    step2_parser.add_argument("epsg", metavar="EPSG",help="GDA2020 = 78**, GDA94 = 283**, AGD84 = 203**, AGD66 = 202**\n ** = zone", default=stored_args.get('epsg'))
    step2_parser.add_argument("area_limit", metavar="Polygon Size",help="Size of the polygons to exlcude from the process(m2) \ndefault=100", default=stored_args.get('area_limit'))
    step2_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    step3_parser = sub_pars.add_parser('Step_3', help='Calculation of Elevation for each void- Run after global mapper step')
    step3_parser.add_argument("lazpath", metavar="LAZ Path", widget="DirChooser", help="Select folder with Laz poly", default=stored_args.get('lazpath'))
    step3_parser.add_argument("outputfolder", metavar="Output folder", widget="DirChooser", help="Output folder for Hydro Laz file", default=stored_args.get('outputdir'))
    step3_parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=8)
    
    args = parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

def createBoundries(mergedRawHydroFile,mergedHydroShp,step):

    concavity = round(float(math.sqrt((step**2.0)*2.0))+0.1,2)
    print('Concavity = {0}'.format(concavity))

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasboundary.exe', '-i', mergedRawHydroFile ,'-oshp','-o',mergedHydroShp , '-concavity', concavity ,'-holes','-disjoint' ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  


    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Making merged file for {0} Exception - {1}".format(mergedHydroShp, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(mergedHydroShp):
            log = "Making merged for {0} Success".format(mergedHydroShp)
            print(log)
            return (True,mergedHydroShp, log)

        else: 
            log = "Making merged for {0} Failed".format(mergedHydroShp)
            print(log)
            return (False,None, log)


def ascTolaz(ascfile,lazfile):

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', ascfile ,'-olaz', '-rescale', 0.001,0.001,0.001 ,'-o',lazfile ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  



    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Converting asc to Laz failed at Exception for : {0} - {1}".format(lazfile, e)
        print(log)
        return(False,None, log)

    finally:
        if os.path.isfile(lazfile):
            subprocessargs=['C:/LAStools/bin/lasindex.exe','-i', lazfile]
            subprocessargs=list(map(str,subprocessargs)) 
            p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            log = "Converting asc to Laz {0} Success".format(lazfile)
            print(log)
            return (True,lazfile, log)

        else: 
            log = "Converting asc to Laz {0} Failed".format(ascfile)
            print(log)
            return (False,None, log)

def genLasinfo(lazfile):
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lazfile,'-otxt' ]
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  
        return(True,None,log)


    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "generating lasinfo for {0} Exception - {1}".format(lazfile, e)
        print(log)
        return(False,None, log)

def movefile(inputfile,outputfile):
        try:
            shutil.move(inputfile, outputfile)

        except subprocess.CalledProcessError as suberror:
            log=log +'\n'+ "{0}\n".format(suberror.stdout)
            return (False,None,log)

        finally:
            if os.path.isfile(outputfile):
                log = "\nMoving file {0} Success".format(inputfile)
                print(log)
                return (True,outputfile, log)

            else: 
                log = "\n **** Moving file {0} Failed ****".format(inputfile)
                return (False,outputfile, log)

        #clipIslandsOut(lazfiles,IslandLakeshpfiles,outputfile)
def clipIslandsOut(lazfile,shpfile,outputfile):
    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/lasclip.exe', '-i', lazfile, '-merged', '-poly', shpfile, '-o', outputfile,'-interior']
        subprocessargs=list(map(str,subprocessargs))    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except:
        log = "Clipping failed for {0}. Failed at Subprocess ".format(str(shpfile)) 
        print(log)
        return(False, None, log)  
    

def zadjust(inputlaz,outputlaz,clamp_val):

    log = ''
    try:
        subprocessargs=['C:/LAStools/bin/las2las.exe', '-i', inputlaz,'-o', outputlaz, '-clamp_z',clamp_val, clamp_val,'-olaz' ]
        subprocessargs=list(map(str,subprocessargs))
        print(subprocessargs)
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  
        #return(True,None,log)

    
    except subprocess.CalledProcessError as suberror:
        log=log +"{0}\n".format(suberror.stdout)
        print(log)
        return (False,None,log)

    except Exception as e:
        log = "Clamping for {0} Exception - {1}".format(inputlaz, e)
        print(log)
        return(False,None, log)
    
    finally:
        if os.path.isfile(outputlaz):
            log = "Clamping for {0} Successfull".format(outputlaz)
            print(log)
            return (True,outputlaz, log)

        else: 
            log = "Clamping for {0} Failed".format(outputlaz)
            print(log)
            return (False,None, log)
    
def main():

    print("Starting Program \n\n")
    freeze_support() 
    #Set Arguments
    args = param_parser()

    if args.command == 'Step_1':


        laspath = args.laspath
        filetype = args.filetype 
        workpath = args.workpath.replace('\\','/')
        deliverypath = args.deliverypath.replace('\\','/')
        tilelayout = args.geojsonfile.replace('\\','/')
        step = float(args.step)
        buffer = args.buffer
        aoi = args.aoi
        fill = args.fill
        hydropointsfiles=None
        if not args.hydropointsfiles==None:
            hydropointsfiles=args.hydropointsfiles
            hydropointsfiles=args.hydropointsfiles.replace('\\','/').split(';')


        cores = args.cores
        dt = strftime("%y%m%d_%H%M")

        deliverypath = AtlassGen.makedir(os.path.join(deliverypath, '{0}_makeHydro'.format(dt)).replace('\\','/'))
        workingdir = AtlassGen.makedir(os.path.join(workpath, '{0}_makeHydro_Working'.format(dt)).replace('\\','/'))


        make_Hydro = {}
        make_Hydro_results = []

        tl = AtlassTileLayout()
        tl.fromjson(tilelayout)

        if not args.createmerge:
            
            for tile in tl: 

                tilename = tile.name                                                 #tile,laspath,deliverypath,workingpath,tilelayout,aoi,filetype,step,fill
                make_Hydro[tilename] = AtlassTask(tilename,Hydro.newmakeHydroperTile,tile,laspath,deliverypath,workingdir,tilelayout,aoi,filetype,step,fill)

            p=Pool(processes=cores)   
            make_Hydro_results=p.map(AtlassTaskRunner.taskmanager,make_Hydro.values())      

            merged_dir = AtlassGen.makedir(os.path.join(deliverypath,'output_Step_1_merged_laz').replace('\\','/'))
            mergedRawHydroFile = '{0}/merged_Hydro_voids_raw.laz'.format(merged_dir)
            hydrolazpath = os.path.join(workingdir,'04_heighted_voids_clipped')
            AtlassGen.mergeFiles(hydrolazpath,mergedRawHydroFile,'laz')


        else:
            lazpath = args.lazpath
            merged_dir = AtlassGen.makedir(os.path.join(lazpath,'output_Step_1_merged_laz').replace('\\','/'))
            mergedRawHydroFile = '{0}/merged_Hydro_voids_raw.laz'.format(merged_dir)
            AtlassGen.mergeFiles(lazfiles,mergedRawHydroFile,'laz')

            mergedHydroShp = mergedRawHydroFile.replace('.laz','.shp')





    if args.command == 'Step_2':


        lazfile = args.lazfile
        outputfolder = args.outputfolder

        shpfolder = AtlassGen.makedir(os.path.join(outputfolder,'SHP_Files'))
        step = args.step
        epsg = args.epsg
        area_s = int(args.area_limit)

        cores = args.cores
     
     
        print('Making SHP files from the input LAZ files')
    
        #convert laz TO shp files and index
        path,filename,ext = AtlassGen.FILESPEC(lazfile)
        hydroShpfile = os.path.join(outputfolder,'{0}.shp'.format(filename)).replace('\\','/')
        prjfile = os.path.join(outputfolder,'{0}.prj'.format(filename)).replace('\\','/')

        prjfile2 = "\\\\10.10.10.142\\projects\\PythonScripts\\EPSG\\{0}.prj".format(epsg)
           
        if os.path.isfile(prjfile2):
            shutil.copy(prjfile2,prjfile)
        else:
            print("PRJ file for {1} is not available in 10.10.10.142".format(epsg))


        createBoundries(lazfile, hydroShpfile, step)

   

        # Eleanor's breaking up the shp file to many shp files come here.
        #########################################################################################################
        maximum_indices = 9999999

        polygons_folder = AtlassGen.makedir(os.path.join(shpfolder,'polygons')).replace('\\','/')
        polygon_dic = OrderedDict()

        
        path,shpfilename,ext = AtlassGen.FILESPEC(hydroShpfile)
        # set up output folders


        # import the polygon. it should be a multipolygon.
        read_shp = shp.Reader(hydroShpfile)
        # import all its shaperecords
        shapes = read_shp.shapes()
        i=1
        deleted_polygons = []
        for i, record in enumerate(shapes):
            # make filled index number for naming. eg 00000002
            idx = str(i).zfill(len(str(maximum_indices)))
            #print('Running index %s of %s...' % (i, len(shapes) - 1))
            
            # extract coords
            coordinate_tups = record.points
            r = LinearRing(coordinate_tups)

            # convert that to shapely form
            polygon_in = Polygon(r)
   
            # get area
            area_m = polygon_in.area
            #print(area_m)
            if area_m < area_s:
                deleted_polygons.append(idx)
                #print('Skipped : Area smaller than 100m2 : {0}'.format(idx))
            else:
                file_name = "{0}_{1}.shp".format(shpfilename,idx)
                polygon_dic[idx] = {'area' : area_m, 'filename' : file_name, 'points':coordinate_tups,'status':None, 'parent':idx}

        print('\n################### Deleted {0} polygons less than {1}m2 ########################\n'.format(len(deleted_polygons), area_s))
        print('Total polygons to process : {0}'.format(len(polygon_dic)))
        sorted_list = list(OrderedDict(sorted(polygon_dic.items(), key=lambda x: x[1]['area'],reverse=True)))

        print(sorted_list)

        largest_poly_id = sorted_list[0]
        #set the largest polygon to be water
        polygon_dic[largest_poly_id]['status'] = 'Water'
      
        islandLakes = []

        for polyid in sorted_list:

            poly_main = Polygon(polygon_dic[polyid]['points'])
            
            print('\nWorking on Poly iD = {0}'.format(polyid))
            polys_inside = []
 
            
            for id in sorted_list:

                poly_sel = polygon_dic[id]

              
                if poly_sel['status'] == None or  poly_sel['status'] == 'Water':
                    for x in range(len(poly_sel['points'])):

                        pp = poly_sel['points'][x]
                        point_to_check = Point(pp)
                        
                                                    
                        if point_to_check.within(poly_main):
                            print("    Polygon {0} is inside {1}".format(id,polyid))
                            print("    setting {0} to Island".format(id))
                            poly_sel['status'] = 'Island'
                            poly_sel['parent'] = polyid
                            polys_inside.append(id)   
                            break

                        else:
                            poly_sel['status'] = 'Water'    
                           
          
            

            # if island run the loop to see whether there are any water bodies inside this 

            if not len(polys_inside)==0: 
                print('     Islands of polygon {0}   : {1}'.format(polyid, polys_inside))

                for j in polys_inside:
                    island = polygon_dic[j]
                    island_poly = Polygon(island['points'])

                    for k in polys_inside:

                        checkIsland = polygon_dic[k]
                    
                        for x in range(len(checkIsland['points'])):

                            pp = checkIsland['points'][x]
                            point_to_check = Point(pp)
                        
                                                    
                        if point_to_check.within(island_poly):
                            print("    Polygon {0} is a lake Inside {1}".format(k,j))
                            print("    setting {0} to IslandLake".format(k))
                            polygon_dic[k]['status'] = 'IslandLake'
                            islandLakes.append(k)

                            break
                



        for key, value in polygon_dic.items():
            print(key, value['status'], value['parent'])
            buffered_coordinates = []
            if value['status'] == 'Water':
                coordinate_list = value['points']
                # Buffer polygons 
                polygon_in = Polygon(coordinate_list)
                try:
                    buffered_poly = Polygon(polygon_in.buffer(0.1).exterior, [r])
                    buffered_coordinates = buffered_poly.exterior.coords
                except:
                    print('could not buffer {0}'.format(key))
                    pass
                finally:
                    #print(len(buffered_coordinates))
                    if len(buffered_coordinates) == 0:
                        buffered_coordinates = coordinate_list

                file_path = os.path.join(polygons_folder, 'Water_poly_{0}.shp'.format(key)).replace('\\','/')
                prjfile = os.path.join(polygons_folder,'Water_poly_{0}.prj'.format(key)).replace('\\','/')

                # write the shp. Type 5 is a single simple polygon without z values. Type 15 has z.
                sh = shp.Writer(file_path, shapeType=15)
                sh.field('Area', 'N', decimal=4)
                sh.field('Index', 'C')
                sh.field('Type', 'C')

                sh.polyz([buffered_coordinates])
                sh.record(Area=area_m, Index=str(key),Type='Water')
                sh.close()
                shutil.copy(prjfile2,prjfile)

            if value['status'] == 'Island':
                coordinate_list = value['points']
                islandsfolder = AtlassGen.makedir(os.path.join(polygons_folder,'Islands_shp').replace('\\','/'))
                file_path = os.path.join(islandsfolder, 'Island_poly_{0}.shp'.format(key)).replace('\\','/')
                prjfile = os.path.join(islandsfolder,'Island_poly_{0}.prj'.format(key)).replace('\\','/')
                # write the shp. Type 5 is a single simple polygon without z values. Type 15 has z.
                sh = shp.Writer(file_path, shapeType=15)
                sh.field('Area', 'N', decimal=4)
                sh.field('Index', 'C')
                sh.field('Type', 'C')

                sh.polyz([coordinate_list])
                sh.record(Area=area_m, Index=key,Type='Island')
                sh.close()
                shutil.copy(prjfile2,prjfile)
        
            if value['status'] == 'IslandLake':
                coordinate_list = value['points']
                buffered_coordinates = []
                # Buffer polygons 
                polygon_in = Polygon(coordinate_list)
                try:
                    buffered_poly = Polygon(polygon_in.buffer(0.1).exterior, [r])
                    buffered_coordinates = buffered_poly.exterior.coords
                except:
                    print('could not buffer {0}'.format(key))
                    pass
                finally:
                    if len(buffered_coordinates) == 0:
                        buffered_coordinates = coordinate_list
                file_path = os.path.join(polygons_folder, 'IslandLake_poly_{0}.shp'.format(key)).replace('\\','/')
                prjfile = os.path.join(polygons_folder,'IslandLake_poly_{0}.prj'.format(key)).replace('\\','/')
                # write the shp. Type 5 is a single simple polygon without z values. Type 15 has z.
                sh = shp.Writer(file_path, shapeType=15)
                sh.field('Area', 'N', decimal=4)
                sh.field('Index', 'C')
                sh.field('Type', 'C')

                sh.polyz([buffered_coordinates])
                sh.record(Area=area_m, Index=key,Type='Lake')
                sh.close()
                shutil.copy(prjfile2,prjfile)

        inputlazfile = os.path.join(outputfolder,'inputHydroLaz.laz')
        shutil.copy(lazfile,inputlazfile)

        #remove lakes from islands
        if not len(islandLakes) == 0:
            IslandLakeshpfiles = AtlassGen.FILELIST(['*IslandLake_*.shp'],polygons_folder)
            outputfile = os.path.join(outputfolder, 'InputIslandLakes_removed.laz').replace('\\','/')
            
            for poly in IslandLakeshpfiles:
                print(poly)
                path,polyname,ext = AtlassGen.FILESPEC(poly)
                polylaz = os.path.join(polygons_folder,'{0}.laz'.format(polyname)).replace('\\','/')
                
                #makes the indivisual island lake hydro  laz
                resul = AtlassGen.clip(lazfile,polylaz,poly,'laz')
                print(resul)
                

                #now clip it out of the main hydro laz before water bodies get individually clipped
                clipIslandsOut(inputlazfile,poly,outputfile)
                shutil.copy(outputfile,inputlazfile)

        
        
        shpfiles = AtlassGen.FILELIST(['*Water*.shp'],polygons_folder) # we have already clipped the Islandwater bodies in the earlier stage so no need to clip them again
        print(len(shpfiles))

        clip_task = {}
        clip_task_results = []

        genlazinfo_task = {}
        genlazinfo_task_resilts = []


        for shpfile in shpfiles:
            path,id,ext = AtlassGen.FILESPEC(shpfile)
            
            hydrolaz = os.path.join(polygons_folder,'{0}.laz'.format(id))
            #Cut the hydro polygons in to seperate laz files

            clip_task[id] = AtlassTask(id,AtlassGen.clip,inputlazfile,hydrolaz,shpfile,'laz')
        
        p=Pool(processes=cores)    
        print('Clipping to polys started')
        clip_task_results=p.map(AtlassTaskRunner.taskmanager,clip_task.values()) 

        hydrolazfiles = AtlassGen.FILELIST(['*.laz'],polygons_folder)

        for lfile in hydrolazfiles:
            path,id,ext = AtlassGen.FILESPEC(lfile)

            #Generate lasinfo for each laz file
            genlazinfo_task[id] = AtlassTask(id,genLasinfo,lfile)

        print('Generating Lazinfo for polys started')
        genlazinfo_task_resilts=p.map(AtlassTaskRunner.taskmanager,genlazinfo_task.values()) 

        
        ############################################################################
        attribs={}
        attribs['num_points']='  number of point records:    '
        attribs['min_xyz']='  min x y z:                  '
        attribs['max_xyz']='  max x y z:                  '

        txtfiles = AtlassGen.FILELIST(['*.txt'],polygons_folder)

        filedict1 = {}

        for file in txtfiles:
            path,name,extn=AtlassGen.FILESPEC(file)
            lazfile = os.path.join(path,'{0}.laz'.format(name)).replace('\\','/')
            filedict1[name]={}
            filedict1[name]['file']=file.replace('\\','/')
            filedict1[name]['lazfile']=lazfile  
            filedict1[name]['attribs']={}
            for attrib in attribs.keys():
                filedict1[name]['attribs'][attrib]=''
        
        ##############################################################################

        adjusted_laz = AtlassGen.makedir(os.path.join(outputfolder,'adjusted_hydro_polygons').replace('\\','/'))
        #loop through tiles and summarise key attribs
        for name in filedict1.keys():

            print("\nStarting to clamp {0}".format(name))
            lines = [line.rstrip('\n')for line in open(filedict1[name]['file'])]

            for line in lines:
                for attrib in attribs.keys():
                    if attribs[attrib] in line:
                        line=line.replace(attribs[attrib] ,'')
                        line=line.strip(' ')
                        filedict1[name]['attribs'][attrib]=line
            
            minz = round(float(filedict1[name]['attribs']['min_xyz'].split(' ')[2]),3)
            maxz = round(float(filedict1[name]['attribs']['max_xyz'].split(' ')[2]),3)
            diff  = round(maxz - minz,3)

            print('Polygon {0} minz : {1}'.format(name,minz))

            filedict1[name]['attribs']['minz'] = minz
            filedict1[name]['attribs']['maxz'] = maxz
            filedict1[name]['attribs']['diff'] = diff

            #Move file to a different location if diff is greater than 1m for manual check

            if diff < 1.0:
                if (minz%0.50)== 0:
                    new_minz = minz-0.250
                    print('\nMin z of {0} adjusted to {1}'.format(name,new_minz))
                    filedict1[name]['attribs']['minz'] = new_minz
                    minz = new_minz

                lazfile = filedict1[name]['lazfile']
                print('Clamping Polygon : {0}'.format(name))
                outputfile = os.path.join(adjusted_laz,'{0}.laz'.format(name).replace('\\','/'))
                zadjust(lazfile,outputfile,minz)
            
            else:
                inputfile = filedict1[name]['lazfile']
                txtf = filedict1[name]['file']
                path,filename,ext = AtlassGen.FILESPEC(inputfile)
                manualCheckdir = AtlassGen.makedir(os.path.join(outputfolder,'ManualCheck').replace('\\','/'))
                lazfile =  os.path.join(manualCheckdir,'{0}.laz'.format(filename)).replace('\\','/')
                otxtfile = os.path.join(manualCheckdir,'{0}.txt'.format(filename)).replace('\\','/')
                filedict1[name]['lazfile']=lazfile  

                movefile(inputfile,lazfile)
                movefile(txtf,otxtfile)
                    
            print(name,filedict1[name]['attribs'])


        attribute_file = os.path.join(outputfolder,'Ploy_Summary.json')
        with open(attribute_file, 'w') as f:
            # Using vars(args) returns the data as a dictionary
            json.dump(filedict1, f)

        #print('{0} polygons deleted due to zero area :\n{1}'.format(len(deleted_polygons),deleted_polygons))

        #Merge the hydro files to one file
        mergedfile = os.path.join(adjusted_laz,'Merged_Hydro_Output.laz').replace('\\','/')
        if os.path.isfile(mergedfile):
            os.remove(mergedfile)
        
        AtlassGen.mergeFiles(adjusted_laz,mergedfile,'laz')

    if args.command == 'Step_3':
        print("Clamping the polygons in Manual Check Folder after visual check.\nNOTE: minz will be used")

        lazpath = args.lazpath
        outputfolder = args.outputfolder

        hydrofolder = AtlassGen.makedir(os.path.join(outputfolder,'Zclamped_hydro_files'))

        ############################################################################
        attribs={}
        attribs['num_points']='  number of point records:    '
        attribs['min_xyz']='  min x y z:                  '
        attribs['max_xyz']='  max x y z:                  '

        txtfiles = AtlassGen.FILELIST(['*.txt'],lazpath)

        filedict1 = {}

        for file in txtfiles:
            path,name,extn=AtlassGen.FILESPEC(file)
            lazfile = os.path.join(path,'{0}.laz'.format(name)).replace('\\','/')
            filedict1[name]={}
            filedict1[name]['file']=file.replace('\\','/')
            filedict1[name]['lazfile']=lazfile  
            filedict1[name]['attribs']={}
            for attrib in attribs.keys():
                filedict1[name]['attribs'][attrib]=''
        
        ##############################################################################

        #loop through tiles and summarise key attribs
        for name in filedict1.keys():

            lines = [line.rstrip('\n')for line in open(filedict1[name]['file'])]

            for line in lines:
                for attrib in attribs.keys():
                    if attribs[attrib] in line:
                        line=line.replace(attribs[attrib] ,'')
                        line=line.strip(' ')
                        filedict1[name]['attribs'][attrib]=line
            
            
            minz = round(float(filedict1[name]['attribs']['min_xyz'].split(' ')[2]),3)
            maxz = round(float(filedict1[name]['attribs']['max_xyz'].split(' ')[2]),3)
            diff  = round(maxz - minz,3)

            print('Polygon {0} minz : {1}'.format(name,minz))

            filedict1[name]['attribs']['minz'] = minz
            filedict1[name]['attribs']['maxz'] = maxz
            filedict1[name]['attribs']['diff'] = diff

            if (minz%0.50)== 0:
                new_minz = minz-0.250
                print('\nMin z of {0} adjusted to {1}'.format(name,new_minz))
                filedict1[name]['attribs']['minz'] = new_minz

            lazfile = filedict1[name]['lazfile']
            print('\nClamping Polygon : {0}'.format(name))
            outputfile = os.path.join(hydrofolder,'{0}.laz'.format(name).replace('\\','/'))
            zadjust(lazfile,outputfile,minz)
                    
        print("\nMerging Files\n")
        mergedfile = os.path.join(hydrofolder,'Merged_Hydro_Output2.laz').replace('\\','/')
        AtlassGen.mergeFiles(hydrofolder,mergedfile,'laz')



    return
    
if __name__ == "__main__":
    main() 



