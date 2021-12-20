import time
import numpy as np
import pandas as pd
from laspy.file import File
import math
from random import randrange
from random import randint
import random, string
from Atlass_beta1 import *

def rotate_about_origin(x,y, radians, originx, originy):
    """Rotate a point around a given point.
    x and y are numpy lists
    """

    offset_x, offset_y = originx, originy
    adjusted_x = (x - offset_x)
    adjusted_y = (y - offset_y)
    cos_rad = math.cos(radians)
    sin_rad = math.sin(radians)
    qx = offset_x + cos_rad * adjusted_x + sin_rad * adjusted_y
    qy = offset_y + -sin_rad * adjusted_x + cos_rad * adjusted_y
    return qx, qy

def random_name():
    x = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return x

def obfuscate_tilelayout(ingeojsonfile,outgeojsonfile,outobsuredgeojsonfile):
    tl_in = AtlassTileLayout()
    tl_in.fromjson(ingeojsonfile)
    tl_out = AtlassTileLayout()
    tl_obsout = AtlassTileLayout()

    #list to store obfs names.
    names=[]

    #loop tiles and calc offsets
    for tile in tl_in.tiles.items():
        
        #make random new name string
        newname=''
        while newname=='' or newname in names:
            newname=random_name()
        names.append(newname)

        #add old and new params to the updated tile layout
        tileout=tile.params
        tileout['obfsname']=newname
        tileout['originx']=(tile.xmax+tile.xmin)/2
        tileout['originy']=(tile.ymax+tile.ymin)/2
        tileout['xoffset']=randint(-500,500)*1000
        tileout['yoffset']=randint(-200,700)*1000
        tileout['zoffset']=randint(-200,200)
        tileout['rotation']=randint(0,3)*90
        tileout['toffset']=randint(-25,25)*86400

        tl_out.fromdict(tileout)

        #add adjusted coords and obfs name to the obs tilelayout.
        tileobfsout={}
        tileobfsout['name']=newname
        tileobfsout['xmin']=tile.xmin+tileout['xoffset']
        tileobfsout['ymin']=tile.ymin+tileout['yoffset']
        tileobfsout['xmax']=tile.xmin+tileout['xoffset']
        tileobfsout['ymax']=tile.ymin+tileout['yoffset']

        tl_obsout.fromdict(tileobfsout)

        #['name','xmin','ymin','xmax','ymax']



    return updatedtilelayout, obfuscatedtilelayout


def main():
    '''
    read data from file
    '''
    print('Reading files')
    file1='F:/temp/Brisbane_2014_LGA_SW_502000_6965000_1K_Las.laz'

    tic = time.perf_counter()
    inFile1 = File(file1, mode='r')
    toc = time.perf_counter()
    print(f"{len(inFile1.points):d} records read from {file1:s} in {toc - tic:0.4f} seconds")

    print('permuting data')
    tic = time.perf_counter()

    xvalues=inFile1.get_x_scaled()
    yvalues=inFile1.get_y_scaled()
    zvalues=inFile1.get_z_scaled()
    tvalues=inFile1.get_gps_time()
    pointclasses=inFile1.get_classification()

    #tile lower left corner
    originx, originy=502000,6965000
    xoffset=randrange(-500000,500000)
    yoffset=randrange(-500000,500000)
    zoffset=randrange(-200,200)``
    rotation=randint(0,3)*90
    toffset=randint(-25,25)*86400

    print(f" xoffset={xoffset:0.4f} \n yoffset={yoffset:0.4f} \n zoffset={zoffset:0.4f} \n rotation={rotation:0.4f} \n toffset={toffset:0.4f}")

    #rotate points
    xvalues,yvalues=rotate_about_origin(xvalues,yvalues, math.radians(rotation), originx, originy)

    #offset points 
    xvalues=xvalues-xoffset
    yvalues=yvalues-yoffset
    zvalues=zvalues-zoffset
    tvalues=tvalues-toffset

    toc = time.perf_counter()
    print(f"{len(inFile1.points):d} records permuted in {toc - tic:0.4f} seconds")

if __name__ == "__main__":
    main(sys.argv[1:]) 

