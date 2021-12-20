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
import os, glob, re
import numpy as np
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *


#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Copying Files", advanced=True, default_size=(1000,800), use_legacy_titles=True, required_cols=1, optional_cols=3)
def param_parser():
    main_parser=GooeyParser(description="")
    main_parser.add_argument("newLoc", metavar="New location", widget="DirChooser")
    main_parser.add_argument("oldLoc", metavar="Old location", widget="DirChooser")

    return main_parser.parse_args()


    
#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    print("Starting Program \n\n")
    freeze_support() 
    
    #Set Arguments
    args = param_parser()

    new_path = args.newLoc
    old_path = args.oldLoc

    #logpath = os.path.join(new_path,'log.txt').replace('\\','/')
    #log = open(logpath, 'w')

    d = new_path
    new_subdirs = [os.path.join(d, o) for o in os.listdir(d) if os.path.isdir(os.path.join(d,o))]

    for proj_dir in new_subdirs:
        proj = proj_dir.replace("\\\\10.10.10.142\\Archived\\Projects\\","")
        BR = proj.split("_")[0]

        print(BR)       

        for foundProjectPath in glob.glob("{0}\\{1}*".format(old_path,BR)):
            print('-------------------------{0}------------------'.format(BR))
            #log.write('-------------------------{0}------------------\n'.format(BR))
            subfolders = [['Current AOI','AOI'],['Proposals & Costs','Proposals_Costs'],['Submitted to Client','Submitted_Quote'],['Supplied from Client','ClientData']]

            for source, target in subfolders:
                sourcedir = os.path.join(foundProjectPath,source)
                targetdir = os.path.join(proj_dir,target)
                print('{0} ---> {1}\n'.format(sourcedir, targetdir))
                #log.write('{0} ---> {1}\n'.format(sourcedir, targetdir))      

                for cur, dirs, files in os.walk(sourcedir):
                    if not len(dirs) == 0:
                        print('--------{0}--------'.format(dirs))
                        print(dirs)
                    elif not len(files) == 0:
                        print(files)

                '''
                if os.path.isdir(sourcedir):

                    
                    items = os.listdir(sourcedir)
                    for item in items:
                        s = os.path.join(sourcedir,item)
                        t = os.path.join(targetdir,item)

                        if os.path.isdir(s):
                            if not os.path.exists(t):
                                os.makedirs(t)
                                shutil.copytree(s,t)
                                print('{0} ---> {1}\n'.format(s, t))
                                log.write('{0} ---> {1}\n'.format(s, t))
                            else:
                                subitems = os.listdir(s)

                                print('ignored {0}'.format(t))
                                log.write('ignored {0}'.format(t))

                        else:
                            if  not os.path.exists(t):
                                shutil.copy2(s,t)
                                print('{0} ---> {1}'.format(s, t))
                                log.write('{0} ---> {1}\n'.format(s, t))
                            else:
                                print('ignored {0}'.format(s))
                                log.write('ignored {0}'.format(s))
                '''

      



    return


if __name__ == "__main__":
    main()         

