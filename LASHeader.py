import sys
import shutil
import time
import os, glob
import subprocess 
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
from liblas import file
from liblas import vlr
from liblas import header as lasheader


f = liblas.File("D:\\temp\\test_vic_foresty\\604000_5812500.laz", None,'rb')
h = f.header
print(h)
v = vlr.VLR()

v.userid = 'Manesha'
v.recordid = 12344
v.data = 'TestData'

h.add_vlr(v)

f2 = lasfile.File('D:\\temp\\test_vic_foresty\\604000_5812500_edited.laz', header=h,mode='w')
for p in f:
    f2.write(p)
f2.close