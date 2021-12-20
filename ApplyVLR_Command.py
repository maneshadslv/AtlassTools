#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys, getopt
import shutil
import subprocess
import os
import random
import argparse
from datetime import datetime, timedelta
import time



#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

def ApplyVLR(lazfile,inputdir,vlrdir,filetype):
    os.chdir(inputdir)
    log = ''
    try:
        
        subprocessargs=['C:/LAStools/bin/las2las', '-i', lazfile, '-odir',vlrdir,'-load_vlrs' ,'-o{0}'.format(filetype)] 
        subprocessargs=map(str,subprocessargs)    
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)  

        log = 'Success'
        return(True,lazfile, log)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\nFixing header failed at exception for :{0}".format(e)
        return(False,None, log)
    


if __name__ == '__main__':
    #print('Number of variables provided : {0}'.format(print(len(sys.argv))))

    #python C:\AtlassTools\ApplyVLR_Command.py inputfile outpath vlrfile outputfiletype

    print(sys.argv[1:5])
    inputfile, outpath, vlrfile,outputfiletype = sys.argv[1:5]
    inputdir,filename=os.path.split(inputfile)
    
    #copy vlrfile to ouput dir
    if not os.path.isfile(os.path.join(inputdir,'vlrs.vlr').replace('\\','/')):
        destinationfile = os.path.join(inputdir,'vlrs.vlr').replace('\\','/')
        #if not os.path.isfile(destinationfile):
        shutil.copyfile(vlrfile, destinationfile)

    ApplyVLR(inputfile,inputdir,outpath,outputfiletype)