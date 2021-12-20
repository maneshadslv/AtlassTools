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
    dirs=['W:/Brisbane/deliveryinfocheck/Class_0']
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_1')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_2')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_3')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_4')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_5')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_6')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_7')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_8')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_9')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_10')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_11')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_12')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_13')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_14')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_15')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_16')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_17')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_18')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_19')
    dirs.append('W:/Brisbane/deliveryinfocheck/Class_20')

    for d in dirs:
        outfile='{0}.csv'.format(d)

        filelist1=FILELIST (d,'*.txt')
        with open(outfile,'w') as f:
            for file in filelist1:
                path,name,extn=FILESPEC(file)
                lines = [line.rstrip('\n')for line in open(file)]
                for line in lines:

                    if '  min x y z:' in line:
                        line=line.replace('  min x y z:' ,'')
                        line=line.strip(' ')
                        while not line.replace('  ' ,' ')==line:
                            line=line.replace('  ' ,' ')
                        line=line.replace(' ' ,',')
                        bbmin=line
                    if '  max x y z:' in line:
                        line=line.replace('  max x y z:' ,'')
                        line=line.strip(' ')
                        while not line.replace('  ' ,' ')==line:
                            line=line.replace('  ' ,' ')
                        line=line.replace(' ' ,',')
                        bbmax=line

                f.write('{0},{1},{2}\n'.format(name[:30],bbmin,bbmax))
            f.close

if __name__ == "__main__":
    main(sys.argv[1:])         