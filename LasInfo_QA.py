#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import itertools
import random
import sys, getopt
import math
import shutil
import subprocess
import urllib
import os, glob
import numpy as np
import io
import datetime
import time
from collections import OrderedDict

sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

defaults={}
defaults['file1']=None
defaults['file2']=None
defaults['outpath']=None
defaults['__keepfiles']=None

#constants
attribs=OrderedDict()
attribs['num_points']='  number of point records:    '
attribs['min_xyz']='  min x y z:                  '
attribs['max_xyz']='  max x y z:                  '
attribs['scale']='  scale factor x y z:         '
#attribs['offset']='  offset x y z:               '
attribs['gps_time']='  gps_time '
attribs['point_source_ID']='  point_source_ID   '
attribs['intensity']='  intensity         '
attribs['first']='number of first returns:        '
attribs['intermediate']='number of intermediate returns: '
attribs['last']='number of last returns:         '
attribs['single']='number of single returns:       '



#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def FILELIST (Pattern):
    filedetails = []
    for infile in glob.glob( Pattern ):
        filedetails.append(infile.replace("\\","/"))
    return filedetails
    
def FILESPEC(filename):
    # splits file into components
    path,name=os.path.split(filename)
    name,ext=name.split(".")
    
    return path, name, ext
       
def makedir(path):
    if not os.path.exists('{0}'.format(path)):
        try:
            os.makedirs('{0}'.format(path))
        except:
            pass
    return path
    

def PrintMsg(Message,Heading=False):
    if not Heading:
        msgstring='\t{0}'.format(Message)
        print(msgstring)
    else:
        msgstring='\n'
        msgstring=msgstring+'----------------------------------------------------------------------------\n'
        msgstring=msgstring+'{0}: {1}\n'.format(time.ctime(time.time()),Message)
        msgstring=msgstring+'----------------------------------------------------------------------------\n'
        print(msgstring)
        
    return msgstring + '\n'

def PrintHelp(defaults):
    PrintMsg('Below is an example of acceptable options and arguments:','Print help.')
    for arg in list(defaults.keys()):
        PrintMsg('\t--{0}={1}'.format(arg,defaults[arg]))
    print('----------------------------------------------------------------------------')


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    #-----------------------------------------------------------------------------------------------------------------
    #data1 data received from India
    #data2 tiles stored on server (sent to India)
    #------------------------------------------------
    #Intructions:
    #load the tilelayout of data received in batch from India into the onetool
    #set data1 variable to the path of the laz data received
    #set data2 varaible to the path of the laz data sent to India
    #use the command below to report the differences.
    #------------------------------------------------
    #
    #global variables
    #data1=d:\myproject\newbatchfromIndia
    #data2=L:\myproject\originaltilestoindia
    #
    #command pattern
    #python \\10.10.10.142\projects\PythonScripts\LasInfo_QA.py --file1=#data1#\#name#.laz --file2=#data2#\#name#.laz --outpath=#data1#\checks

    try:
        longargs=list('{0}='.format(key) for key in list(defaults.keys()))
        settings=defaults
        opts, args = getopt.getopt(argv,"h",["help"] + longargs)
    except getopt.GetoptError as err:
        # print help information and exit:
        PrintMsg(str(err),Heading=True)
        PrintHelp(defaults)
        sys.exit(2)
        
    PrintMsg('Setting arguments:',Heading=True)

    #Get options
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintHelp(longargs,defaults)
            sys.exit()
        elif opt.replace('-','') in list(defaults.keys()):
            PrintMsg('{0}={1}'.format(opt, arg))
            settings[opt.replace('-','')]=arg
        else:
            PrintHelp(defaults)
            sys.exit()

    #create variables from settings
    file1=settings['file1']
    if not file1==None:
        file1=file1.replace("\\","/")
        pass
    else:
        PrintMsg('file1 not set')
        exit(0)

    file2=settings['file2']
    if not file2==None:
        file2=file2.replace("\\","/")
        pass
    else:
        PrintMsg('file2 not set')
        exit(0)

    outpath=settings['outpath']
    if not outpath==None:
        outpath=makedir(outpath.replace("\\","/"))
        path,name,ext=FILESPEC(file1)
        file1_txt=os.path.join(outpath,'{0}_1.txt'.format(name)).replace("\\","/")
        file2_txt=os.path.join(outpath,'{0}_2.txt'.format(name)).replace("\\","/")
        report=os.path.join(outpath,'{0}_report.txt'.format(name)).replace("\\","/")
        pass
    else:
        PrintMsg('outpath not set')
        exit(0)
        
    subprocessargs=['C:/LAStools/bin/lasinfo.exe','-i',file1,'-otxt','-o',file1_txt]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs) 

    subprocessargs=['C:/LAStools/bin/lasinfo.exe','-i',file2,'-otxt','-o',file2_txt]
    subprocessargs=map(str,subprocessargs)        
    subprocess.call(subprocessargs) 

    #file1
    lines1=[line.rstrip('\n')for line in open(file1_txt)]
    lines2=[line.rstrip('\n')for line in open(file2_txt)]

    filedict1=OrderedDict()
    for line in lines1:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict1[attrib]=line

    filedict2=OrderedDict()
    for line in lines2:
        for attrib in attribs.keys():
            if attribs[attrib] in line:
                filedict2[attrib]=line

    reptstring=''
    test=True
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

    if test:
        os.remove(file1_txt)
        os.remove(file2_txt)
        if os.path.isfile(report):
            os.remove(report)
    else:
        f=open(report,'w')
        f.write('Mismatch detected:\nfile1:{0}\nfile2:{1}\n'.format(file1,file2)+reptstring)
        f.close()
    '''
    for attrib in attribs.keys():





    #make filelist1 "before"
    filelist1=FILELIST (inputdir,'*.txt')
    print(len(filelist1))
    filedict1={}
    for file in filelist1:
        path,name,extn=FILESPEC(file)
        filedict1[name]={}
        filedict1[name]['file']=file
        filedict1[name]['attribs']={}
        for attrib in attribs.keys():
            filedict1[name]['attribs'][attrib]=''
        
    #loop through tiles and summarise key attribs
    for name in filedict1.keys():
        lines = [line.rstrip('\n')for line in open(filedict1[name]['file'])]
        for line in lines:
            for attrib in attribs.keys():
                if attribs[attrib] in line:
                    line=line.replace(attribs[attrib] ,'')
                    line=line.strip(' ')
                    filedict1[name]['attribs'][attrib]=line
            
    
    '''
if __name__ == "__main__":
    main(sys.argv[1:])            