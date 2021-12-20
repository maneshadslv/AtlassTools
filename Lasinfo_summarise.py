#!\\\\usr\\\\bin\\\\python

import sys, getopt
import math
import shutil
import subprocess
import os, glob

    
def FILESPEC(filename):
    # splits file into components
    path,name=os.path.split(filename)
    name,ext=name.split(".")
    return path, name, ext  
    
def FILELIST (Path,extn):
    filedetails = []
    for infile in glob.glob( os.path.join(Path, '{0}'.format(extn)) ):
        filedetails.append(infile.replace("\\","/"))
    return filedetails   


def main(argv):
    print(argv)
    inputdir = argv[0]
    #Key attribs
    attribs={}
    attribs['global_encoding']='  global_encoding:            '
    attribs['version']='  version major.minor:        '
    attribs['pdrf']='  point data format:          '
    attribs['num_points']='  number of point records:    '
    attribs['min_xyz']='  min x y z:                  '
    attribs['max_xyz']='  max x y z:                  '
    attribs['point_source_ID']='  point_source_ID   '
    attribs['gps_time']='  gps_time '
    ##
    '''
    attribs['Class_1']='  bin 1 has '
    attribs['Class_2']='  bin 2 has '
    attribs['Class_3']='  bin 3 has '
    attribs['Class_4']='  bin 4 has '
    attribs['Class_5']='  bin 5 has '
    attribs['Class_6']='  bin 6 has '
    attribs['Class_7']='  bin 7 has '
    attribs['Class_8']='  bin 8 has '
    attribs['Class_9']='  bin 9 has '
    attribs['Class_10']='  bin 10 has '
    attribs['Class_11']='  bin 11 has '
    attribs['Class_12']='  bin 12 has '
    attribs['Class_13']='  bin 13 has '
    attribs['Class_14']='  bin 14 has '
    attribs['Class_15']='  bin 15 has '
    attribs['Class_16']='  bin 16 has '
    attribs['Class_17']='  bin 17 has '
    attribs['Class_18']='  bin 18 has '
    attribs['Class_19']='  bin 19 has '
    attribs['Class_20']='  bin 20 has '
    attribs['Class_21']='  bin 21 has '
    attribs['Class_22']='  bin 22 has '
    attribs['Class_23']='  bin 23 has '
    attribs['Class_24']='  bin 24 has '
    attribs['Class_25']='  bin 25 has '
    attribs['Class_26']='  bin 26 has '
    attribs['Class_27']='  bin 27 has '

    '''

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
            
                
        print(name,filedict1[name]['attribs'])


if __name__ == "__main__":
    main(sys.argv[1:])         