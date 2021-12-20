import xlrd
import os
import glob
import sys
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
import xlwt 
from xlwt import Workbook 

loc = "D:\\Processing_Data\\Vic_Foresty\\Control\\GCP_extraction"

txt_files = AtlassGen.FILELIST(['*.xlsx'],loc)

wbw = Workbook() 
sheetw = wbw.add_sheet('Sheet1') 

w_row = 1

for file in excel_files:
  
    wbr = xlrd.open_workbook(file) 
    sheetr = wbr.sheet_by_index(0) 
    
    sheetr.cell_value(0,0) 
    
    rows = range(12,sheetr.nrows)
    print(len(rows))
    for r in rows: 
        if sheetr.cell_value(r,3) == 'h':
            print('false')

        if sheetr.cell_value(r,3) == 'v':
            print('false')

        else:
            print(w_row, sheetr.cell_value(r,4))

            index = sheetr.cell_value(r,4)

            if isinstance(index,str):
                index = str(index)
            elif isinstance(index,float):
                index = int(index)

            sheetw.write(w_row,0,index)
            sheetw.write(w_row,1,sheetr.cell_value(r,5))
            sheetw.write(w_row,2,sheetr.cell_value(r,6))
            sheetw.write(w_row,3,sheetr.cell_value(r,7))
            sheetw.write(w_row,4,sheetr.cell_value(r,2))
            w_row +=1


wbw.save('D:\\Processing_Data\\Vic_Foresty\\Control\\GCP_extraction\\All_unspec.xls') 
