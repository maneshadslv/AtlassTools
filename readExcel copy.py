import xlrd
import os
import glob
import sys
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
import xlwt 
from xlwt import Workbook 

loc = "D:\Processing_Data\VictorianForestry\lasinfofiles"

txt_files = AtlassGen.FILELIST(['*.txt'],loc)

search_pattern = 'Interpine2018_UNC_'

renamedlistfile = "D:\Processing_Data\VictorianForestry\lasinfofiles\\renamed_list.csv"
renamedlist = []
with open(renamedlistfile,'w') as da:
    for txtfile in txt_files:
        searchfile = open(txtfile, "r")
        for line in searchfile: 
            if search_pattern in line:
                #print(txtfile,line)
                f = txtfile.split('\\')
                flaz = f[-1].replace('.txt','.laz')
                fst = f[-1].replace('.txt','')
                psid = fst.split('_')[-1]
                renamedfile = line.split('/')[-1]
                print(f'{flaz}->{renamedfile}')
                renamedlist=f'{flaz},{psid},{renamedfile}\n'
                da.write(renamedlist)
