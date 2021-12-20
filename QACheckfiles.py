#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import os
from gooey import Gooey, GooeyParser
import subprocess
import datetime
from time import strftime, sleep
from shutil import copyfile
import glob
from multiprocessing import Pool,freeze_support
import urllib
import shutil
import json
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
import fnmatch
from collections import defaultdict , OrderedDict
import numpy as np
import pandas as pd
from laspy.file import File
import xlsxwriter

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Make QA", use_legacy_titles=True, required_cols=2, default_size=(1120,920))
def param_parser():
    stored_args = {}
    # get the script name without the extension & use it to build up
    # the json filename
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    congifg_folder = "C:\\pythontools"
    if not os.path.exists(congifg_folder):
        os.mkdir(congifg_folder)
    args_file = os.path.join(congifg_folder,"{}-args.json".format(script_name))

    

    #print(globalmapperexe)
    # Read in the prior arguments as a dictionary
    if os.path.isfile(args_file):
        with open(args_file) as data_file:
            stored_args = json.load(data_file)
    
    main_parser=GooeyParser(description="Make QA workspace")
    sub_pars = main_parser.add_subparsers(help='commands', dest='command')
    parser2 = sub_pars.add_parser('CHECKFILES', help='Check files for corruption')
    parser2.add_argument("ori_path", metavar="LAS file Folder with original files(unclassified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('ori_path'))
    parser2.add_argument("rec_path", metavar="LAS file Folder with recieved files(classified)", widget="DirChooser", help="Select las file folder", default=stored_args.get('rec_path'))
    parser2.add_argument("outputpath", metavar="Output Directory",widget="DirChooser", help="Output directory", default=stored_args.get('outputpath'))
    parser2.add_argument("filetype", metavar="File Type",help="input filetype (laz/las)", default='laz')
    parser2.add_argument("-validClasses", metavar="Valid Classes",help="input valid classes", default='1,2,3,4,5,6,7,9,10,13')
    parser2.add_argument("-c", "--cores",metavar="Cores", help="No of cores to run", type=int, default=stored_args.get('cores'))



    args = main_parser.parse_args()

    # Store the values of the arguments so we have them next time we run
    with open(args_file, 'w') as data_file:
        # Using vars(args) returns the data as a dictionary
        json.dump(vars(args), data_file)

    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------
def geninfo(tilename,ori,rec,validClasses):

    tdata=OrderedDict()
    tilecheckPassed = 'Passed'
    print(tilename)
    if os.path.isfile(ori) and os.path.isfile(rec):
        '''
        read data from file
        '''  

        try:
            oriFile = File(ori, mode='r')
            recFile = File(rec, mode='r')
        except:
            print(f'File Corrupted : {tilename}')
            tdata={"Classification" : "None","Classification_Test" : "None","Critical Failure - Unable to read file" : "None","Version Test" : "None", "PDRF" : "None","PDRF Test":"None", "GlobalEncoding":"None","GlobalEncoding Test":"None","Number of points": "None", "Number of points Tetst": "None","Points Test": "None","GPS times":"None","GPS Test":"None","Returns":"None","Returns Test":"None","Intensity":"None","Intensity Test":"None","Scale":"None","Scale Test":"None","Status":"Failed","Boundaries":"None","Boundary Test":"None"}
            return(True,tdata,'None')
           
   

        '''
        create dataframe ori file
        '''

        #tic = time.perf_counter()
        dataori={}
        dataori["points"] = pd.DataFrame(oriFile.points["point"])
        dataori["points"].columns = (x.lower() for x in dataori["points"].columns)
        dataori["points"].loc[:, ["x", "y", "z"]] *= oriFile.header.scale 
        dataori["points"].loc[:, ["x", "y", "z"]] += oriFile.header.offset
        dataori["header"] = oriFile.header

        '''
        create dataframe rec file
        '''

        datarec={}
        datarec["points"] = pd.DataFrame(recFile.points["point"])
        datarec["points"].columns = (x.lower() for x in datarec["points"].columns)
        # rescale and offset
        datarec["points"].loc[:, ["x", "y", "z"]] *= recFile.header.scale 
        datarec["points"].loc[:, ["x", "y", "z"]] += recFile.header.offset
        datarec["header"] = recFile.header
        #toc = time.perf_counter()
        #print(f"data frame created in {toc - tic:0.4f} seconds")

        # Header Information
        ############################################################
        # version test
        ############################################################
        o_version=oriFile.header.version
        r_version=recFile.header.version

        if o_version != r_version:
            version_test='Failed'
            tdata['Version'] = f'Ori - {o_version} Rec - {r_version}'
            tdata['Version Test'] = 'Warning'
            #print(f"Version test Failed for {tilename}")
            tilecheckPassed = 'Warning'
        else:
            version_test='Passed'
            tdata['Version'] = f'{o_version}'
            tdata['Version Test'] = 'Passed'
            #print(f"Version test Passed for {tilename}")
    
        ###########################################################
        # Data Format ID testt (PDRF)
        ############################################################
        o_pdrf = oriFile.header.data_format_id
        r_pdrf = recFile.header.data_format_id

        if o_pdrf != r_pdrf:
            tdata['PDRF'] = f'Ori-{o_pdrf} Rec - {r_pdrf}'
            tdata['PDRF Test'] = 'Failed'
            tilecheckPassed = 'Warning'

        else:
            tdata['PDRF'] = f'{o_pdrf}'
            tdata['PDRF Test'] = 'Passed'
        ###########################################################
        # Global Engoding test
        ###########################################################
        o_ge = oriFile.header.global_encoding
        r_ge = recFile.header.global_encoding

        if o_ge != r_ge:
            tdata['GlobalEncoding'] = f'Ori-{o_ge} Rec - {r_ge}'
            tdata['GlobalEncoding Test'] = 'Failed'
            tilecheckPassed = 'Warning'
        else:
            tdata['GlobalEncoding'] = f'{o_ge}'
            tdata['GlobalEncoding Test'] = 'Passed'


        ##########################################################
        # Bounding Box Test
        #########################################################
        #check Min Max
        recxmin = round(min(datarec["points"]["x"]),3)
        recymin = round(min(datarec["points"]["y"]),3)
        reczmin = round(min(datarec["points"]["z"]),3)
        recxmax = round(max(datarec["points"]["x"]),3)
        recymax = round(max(datarec["points"]["y"]),3)
        reczmax = round(max(datarec["points"]["z"]),3)     
        #print(recxmin,recymin)
        
        r_xmin = round(recFile.header.min[0],3)
        r_ymin = round(recFile.header.min[1],3)
        r_zmin = round(recFile.header.min[2],3)
        r_xmax = round(recFile.header.max[0],3)
        r_ymax = round(recFile.header.max[1],3)
        r_zmax = round(recFile.header.max[2],3)

        #print(r_xmin,r_ymin)

        if recxmin != r_xmin or recymin != r_ymin:
            tdata['Boundaries'] = f'Ori - min[{recxmin},{recymin},{reczmin}],max[{recxmax},{recymax},{reczmax}] Rec - min[{r_xmin},{r_ymin},{r_zmin}],max[{r_xmax},{r_ymax},{r_zmax}]'
            tdata['Boundary Test'] = 'Failed'
            tilecheckPassed = 'Warning'
        else:
            tdata['Boundaries'] = f'min[{recxmin},{recymin}],max[{recxmax},{recymax}]'
            tdata['Boundary Test'] = 'Passed'

        #########################################################
        # Classification Test
        #########################################################
        #get classification
        all_classes = set(list(range(0,256)))
        valid_classes = set(validClasses)
        invalid_classes = all_classes-valid_classes
        #print(invalid_classes)

        #o_class = oriFile.get_classification()
        r_class = recFile.get_classification()

        check =  list(invalid_classes.intersection(r_class))

        if len(check) >0:
            tdata['Classification'] = check
            tdata['Classification Test'] = 'Failed'
            #print(f"Version test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else :
            tdata['Classification'] = None
            tdata['Classification Test'] = 'Passed'

        ###########################################################
        # Number of points Test
        ##########################################################
        o_len = len(dataori['points'])
        r_len = len(datarec['points'])
        if o_len != r_len:
            tdata['Number of points'] = f'Ori - {o_len} Rec - {r_len}'
            tdata['Number of Points Test'] = 'Failed'
            print(f"Number of points test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            len_test='Passed'
            tdata['Number of points'] = len(datarec['points'])
            tdata['Number of Points Test'] = 'Passed'
            #print(f"Number of points test Passed for {tilename}")

        ###########################################################
        # Points Test
        ###########################################################

        tic = time.perf_counter()

        x0=dataori['points']['x']
        x1=datarec['points']['x']

        y0=dataori['points']['y']
        y1=datarec['points']['y']

        z0=dataori['points']['z']
        z1=datarec['points']['z']

        #print(x0.all()!=x1.all())
        #print(y0.all()!=y1.all())
        #print(z0.all()!=z1.all())
        if x0.all()!=x1.all() or y0.all()!=y1.all() or z0.all()!=z1.all():
            tdata['Points Test'] = 'Failed'
            toc = time.perf_counter()
            print(f"Points test Failed - {toc - tic:0.4f} seconds")
            tilecheckPassed = 'Failed'
        else:
            #print(f'{tilename} XYZ matched')
            tdata['Points Test'] = 'Passed'
            toc = time.perf_counter()
            #print(f"Points test Passed - {toc - tic:0.4f} seconds")

        #############################################################
        # GPS time test
        ##############################################################
        r_gps = [min(datarec['points']['gps_time']),max(datarec['points']['gps_time'])]
        o_gps = [min(dataori['points']['gps_time']),max(dataori['points']['gps_time'])]

        if o_gps != r_gps:
            gps_test='Failed'
            tdata['GPS times'] = f'Ori - {o_gps} Rec - {r_gps}'
            tdata['GPS Test'] = 'Failed'
            print(f"GPS Times test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            gps_test='Passed'
            tdata['GPS times'] = r_gps
            tdata['GPS Test'] = 'Passed'
            #print(f"GPS Times test Passed for {tilename}")
        
        ###############################################################
        # Intensity test
        ###############################################################

        r_intensity=[min(datarec['points']['intensity']),max(datarec['points']['intensity'])]
        o_intensity=[min(dataori['points']['intensity']),max(dataori['points']['intensity'])]
        
        if o_intensity != r_intensity:
            intensity_test='Failed'
            tdata['Intensity'] = f'Ori - {o_intensity} Rec - {r_intensity}'
            tdata['Intensity Test'] = 'Failed'
            print(f"Intensity test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            intensity_test='Passed'
            tdata['Intensity'] = f'{o_intensity}'
            tdata['Intensity Test'] = 'Passed'
            #print(f"Intensity test Passed for {tilename}")

        ###############################################################
        # Scale test
        ################################################################

        o_scale=oriFile.header.scale
        r_scale=recFile.header.scale
        #print(o_offscale,r_offscale)
        if o_scale != r_scale:
            tdata['Scale']=f'Ori-{o_scale} Rec - {r_scale}'
            tdata['Scale Test'] = 'Failed'
            print(f"Scale test Failed for {tilename}")
            tilecheckPassed = 'Failed'
        else:
            tdata['Scale']=f'{o_scale}'
            tdata['Scale Test'] = 'Passed'
            #print(f"Offset_Scale test Passed for {tilename}")

        ##############################################################
        # Returns test
        #############################################################

        o_returns=oriFile.get_return_num()
        r_returns=recFile.get_return_num()

        #nr0=oriFile.get_num_returns()
        #nr1=recFile.get_num_returns()    


        #nr1=datarec['points']['number of returns']

        if o_returns.all() != r_returns.all():
            returns_test='Failed'
            returns=[i for i, j in zip(o_returns, r_returns) if i != j]
            tdata['Returns'] = f'Returns not matching {returns}'
            tdata['Returns Test'] = 'Failed'
            tilecheckPassed = 'Failed'
            #print(f"Point Returns test Failed for {tilename}")
        else:
            returns_test='Passed'
            tdata['Returns'] = f'{min(o_returns),max(o_returns)}'
            tdata['Returns Test'] = 'Passed'        
            #print(f"Point Returns test Passed for {tilename}")
            ##returns=[i for i, j in zip(o_returns, r_returns) if i != j]
            #print(returns)

        tdata['Status']=tilecheckPassed
        return(True,tdata,'None')
    else:
        print(f'One of the files could not be found for Tile {tilename}')
        tdata={"Classification" : "None","Classification_Test" : "None","Version" : "None","Version Test" : "None", "PDRF" : "None","PDRF Test":"None", "GlobalEncoding":"None","GlobalEncoding Test":"None","Number of points": "None", "Number of points Tetst": "None","Points Test": "None","GPS times":"None","GPS Test":"None","Returns":"None","Returns Test":"None","Intensity":"None","Intensity Test":"None","Scale":"None","Scale Test":"None","Status":"None","Boundaries":"None","Boundary Test":"None"}
        return(True,tdata,'None')

   
def checkfiles(tilename,orifile,recfile,outputdir, filetype):

    print('Working with {0}'.format(tilename))

    orilasinfofile = genLasinfo(orifile,tilename,outputdir,filetype,'ori')
    reclasinfofile = genLasinfo(recfile,tilename,outputdir,filetype,'rec')
    report=os.path.join(outputdir,'{0}_report.txt'.format(tilename)).replace("\\","/")


    #constants
    attribs=OrderedDict()
    attribs['num_points']='  number of point records:    '
    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    attribs['scale']='  scale factor x y z:         '
    attribs['gps_time']='  gps_time '
    attribs['point_source_ID']='  point_source_ID   '
    attribs['intensity']='  intensity         '
    attribs['first']='number of first returns:        '
    attribs['intermediate']='number of intermediate returns: '
    attribs['last']='number of last returns:         '
    attribs['single']='number of single returns:       '
    attribs['pdrf']='  point data format:          '
    attribs['version']='  version major.minor:        '


    #file1
    lines1=[line.rstrip('\n')for line in open(orilasinfofile)]
    lines2=[line.rstrip('\n')for line in open(reclasinfofile)]


    filedict1=OrderedDict()
    for line in lines1:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict1[attrib]=line.replace(attribs[attrib],'')

    filedict2=OrderedDict()
    for line in lines2:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict2[attrib]=line.replace(attribs[attrib],'')

            

    reptstring=''
    test=True

    try:
        for attrib in attribs.keys():
            
            if not attrib in filedict1.keys():
                reptstring='{0} not foud in file 1\n'.format(attrib)
                test=False
            if not attrib in filedict2.keys():
                reptstring=reptstring+'{0} not foud in file 2\n'.format(attrib)
                test=False
            if not filedict1[attrib]==filedict2[attrib]:
                test=False
                reptstring=reptstring+'File1:{0}\n'.format(filedict1[attrib])
                reptstring=reptstring+'File2:{0}\n'.format(filedict2[attrib])
                #return(False,None,"not sure")

        if test:
            os.remove(orilasinfofile)
            os.remove(reclasinfofile)
            if os.path.isfile(report):
                os.remove(report)
        else:
            f=open(report,'w')
            f.write('Mismatch detected:\nfile1:{0}\nfile2:{1}\n'.format(orilasinfofile,reclasinfofile)+reptstring)
            f.close()

    except:
        log = 'Could not compare ATTRIBUTE : {0}, For file {1}'.format(attrib,tilename)  
        print(log)
        return (True,None, log)

    finally:

        if not test:
            log = 'Mismatch detected:\nfile1:{0}\nfile2:{1}\n'.format(orilasinfofile,reclasinfofile)+reptstring
            return(test,[tilename,filedict1,filedict2],log)
        else:
            return(test,[tilename,filedict1,filedict2],'Test Failed')



def genLasinfo(lazfile,tilename,outputdir,filetype,key):
  
    #genLasinfo(lazfile)
    lasinfofile = os.path.join(outputdir,'{0}{1}.txt'.format(tilename,key)).replace("\\","/")

    subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', lazfile,'-otxt','-o',lasinfofile]
    subprocessargs=list(map(str,subprocessargs))
    p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

 
    if os.path.exists(lasinfofile):
        return (lasinfofile)
    

    else:
        return(None)

def FILELIST (filepattern, inputfolder):
    filelist = []
    if len(filepattern) >=2:
        #print('Number of patterns found : {0}'.format(len(filepattern)))
        pass
    for pattern in filepattern:
        pattern = pattern.strip()
        #print ('Selecting files with pattern {0}'.format(pattern))
        files = glob.glob(inputfolder+"\\"+pattern)
        for file in files:
            filelist.append(file)
    #print('Number of Files founds : {0} '.format(len(filelist)))
    return filelist

def DIRLIST (inputfolder):
    dirlist = []

    folders = glob.glob(inputfolder+"\\*\\")
    for folder in folders:
        dirlist.append(folder)
    print('Number of Folders founds : {0} '.format(len(dirlist)))
    return dirlist

def FILESPEC(filename):
    # splits file into components
    path,name=os.path.split(filename)
    pattern=name.split(".")
    if len(pattern) == 2:
        name = pattern[0]
        ext = pattern[1]
    else:
        name = pattern[0]
        ext = pattern[len(pattern)-1]

    return path, name, ext    


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()

      
    if args.command == 'CHECKFILES':

        orifolder = args.ori_path
        recfolder = args.rec_path
        outputfolder = args.outputpath
        filetype = args.filetype
        validClasses = args.validClasses
        cores = args.cores

        validClasses = validClasses.split(',')
        validClasses = [int(i) for i in validClasses] 
        print('Valid Classes : {0}'.format(validClasses))

        rec_filelist = FILELIST([f'*.{filetype}'],recfolder)
        ori_filelist = FILELIST([f'*.{filetype}'],orifolder)
        
        print('Program Starting')
        print(f'\nNumber of files in the original dataset : {len(ori_filelist)}')
        print(f'\nNumber of files in the recieved dataset : {len(rec_filelist)}')

        dt = strftime("%y%m%d_%H%M")

        outputfile = os.path.join(outputfolder,f'FileCheckReport_{dt}.xlsx')


        tasks = {}
        for file in rec_filelist:
            path,tilename,ext = FILESPEC(file)
         

            ori = os.path.join(orifolder,f'{tilename}.{filetype}').replace("\\","/")
            rec = os.path.join(recfolder,f'{tilename}.{filetype}').replace("\\","/")
            tasks[tilename]= AtlassTask(tilename, geninfo, tilename,ori,rec,validClasses)

        p=Pool(processes=cores)        
        task_results=p.map(AtlassTaskRunner.taskmanager,tasks.values())
        
        resultt = OrderedDict()

        print(f'\nOriginal laz file locaiton : {orifolder}')
        print(f'Recieved laz file location : {recfolder}')
        for result in task_results:

            resultt[result.name] = result.result
            

        #print(resultt)
        df = pd.DataFrame(data=resultt).T
        df = df[['Version','Version Test','PDRF','PDRF Test','GlobalEncoding','GlobalEncoding Test','Boundaries','Boundary Test','Classification','Classification Test','Number of points','Number of Points Test','Points Test','GPS times', 'GPS Test', 'Intensity','Intensity Test','Scale','Scale Test','Returns','Returns Test','Status']]
        # Convert the dataframe to an XlsxWriter Excel object.
        ##df.to_excel(outputfile)
        print(f'\nFile Check Completed\n\nReport location : {outputfile}')
        
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(outputfile, engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='Sheet1')

        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        # Green fill with dark green text for passed.
        format1 = workbook.add_format({'bg_color':   '#C6EFCE', 'font_color': '#006100'})
        # Red fill with dark red text for failed.
        format2 = workbook.add_format({'bg_color':   '#FFC7CE', 'font_color': '#9C0006'})
        # Red fill with dark red text for failed.
        format5 = workbook.add_format({'bg_color':   '#F0B87D', 'font_color': '#946738'})
        # Heading yellow fill with black text.
        format3 = workbook.add_format({'bg_color':   '#FAFF00', 'font_color': '#000000', 'text_wrap': True})
        # Heading red fill with black text.
        format4 = workbook.add_format({'bg_color':   '#FF0000', 'font_color': '#000000', 'text_wrap': True})

        worksheet.conditional_format(0,0,len(df),22, {'type': 'text',
                                        'criteria': 'containing',
                                        'value':    'Passed',
                                        'format':   format1})
        worksheet.conditional_format(0,0,len(df),22, {'type': 'text',
                                        'criteria': 'containing',
                                        'value':    'Failed',
                                        'format':   format2})
        worksheet.conditional_format(0,0,len(df),22, {'type': 'text',
                                        'criteria': 'containing',
                                        'value':    'Warning',
                                        'format':   format5})

        worksheet.conditional_format('B1:I1', {'type': 'unique', 'format':   format3})
        worksheet.conditional_format('J1:V1', {'type': 'unique', 'format':   format4})
        worksheet.set_column(1,23,12)
        worksheet.set_column(0,0,15)
        workbook.close()
    return

if __name__ == "__main__":
    main()       

