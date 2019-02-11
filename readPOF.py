import sys
import shutil
import subprocess
import os, glob
import random, time
import argparse
import struct
import urllib
import math
from datetime import datetime, timedelta
from gooey import Gooey, GooeyParser
from subprocess import PIPE, Popen
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/utm-0.4.0/'.format(sys.path[0]).replace('\\','/'))
import utm
sys.path.append('{0}/lib/shapefile/'.format(sys.path[0]).replace('\\','/'))
import shapefile
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

def Rad2Deg(rad):
    return rad * 180 / math.pi

def SecondsOfWeek2StandardTime(sow,SurveyDate):
    date_format = "%d/%m/%Y"
    a = datetime.datetime.strptime('06/01/1980', date_format)
    b = datetime.datetime.strptime(SurveyDate, date_format)
    return sow+math.floor((b - a).days/7)*604800-1000000000

def StandardTime2LocalTime(gpstime, utctimeoffset_hrs):
    gpstime_days_part=math.floor(gpstime/60/60/24)
    gpstime_seconds_part=gpstime-(math.floor(gpstime/60/60/24)*60*60*24)
    
    GPSOrigin= datetime.datetime(1980,1,6,0,0,0)
    return GPSOrigin+timedelta(11574,6399)+timedelta(0,utctimeoffset_hrs*60*60)+timedelta(gpstime_days_part,gpstime_seconds_part)

def main():


    input = "D:\\Python\\Gui\\02_SDW\\190112_222648_Scanner_1.pof"
    psid = 17272
    everynth =1
    flight = 1
    zone = 50
    utctimeoffset_hrs = 10


    log = open('D:\\Python\\Gui\\log.txt', 'w')

    linefile = input.replace(".pof", "_lines")

    pointfile = input.replace(".pof", "_points")
    
    with open(input, mode='rb') as file:

        fileContent = file.read()

        majmin = struct.unpack('HH',fileContent[27:31])
        dataoffset = struct.unpack('L',fileContent[31:35])[0]
        date = struct.unpack('HHH', fileContent[35:41])
        entries = struct.unpack('N', fileContent[41:49])[0]
        minlon = Rad2Deg(struct.unpack('d', fileContent[49:57])[0])
        maxlon = Rad2Deg(struct.unpack('d', fileContent[57:65])[0])
        minlat = Rad2Deg(struct.unpack('d', fileContent[65:73])[0])
        maxlat = Rad2Deg(struct.unpack('d', fileContent[73:81])[0])
        timeunit = int(struct.unpack('B', fileContent[121:122])[0])
        file.seek(122)
        timezone = file.read(16)
    

        SurveyDate = '{0}/{1}/{2}'.format(date[2],date[1],date[0])
        prnt = '----------------------Header INFO------------------------\nmajmin: {0}, \ndataoffset: {1}, \nsurvey date: {2}, \nentries: {3}, \nminlon: {4}, \nmaxlon: {5}, \nminlat: {6}, \nmaxlat: {7}, \ntimeitype: {8}, \ntimezone: {9}\n---------------------------------------------------------'.format(majmin,dataoffset, SurveyDate, entries, minlon, maxlon, minlat, maxlat, timeunit, timezone)
        print(prnt)
        
        shapefilecoords = []
        shapefilecoordstimes = []


        #loop through the data set starting from the dataoffset position  56 bytes per dataset
        for i in range(entries):
            seekpos = (dataoffset+i*64)
            file.seek(seekpos)
            fileContent = file.read()
            print('starting data at byte position : {0}'.format(seekpos))
            time = struct.unpack('d',fileContent[:8])[0]

            lon = struct.unpack('d',fileContent[8:16])[0]

            lat = struct.unpack('d',fileContent[16:24])[0]

            alt = struct.unpack('d', fileContent[24:32])[0]
        
            easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon, zone) 
            alt = struct.unpack('d', fileContent[24:32])[0]

            days = math.floor(time/86400.0)
            
            if timeunit == 0:
                weeksecs = round(time + (5+days)* 86400.0,3)
            if timeunit == 2:
                weeksecs = round(time + (5+days)* 86400.0,3)

            shapefilecoords.append([easting,northing,alt])
            shapefilecoordstimes.append(SecondsOfWeek2StandardTime(weeksecs,SurveyDate))
            print(time, lon, lat, alt, weeksecs)
            
            log.write('\n\n{0}  -   time: {1}, easting : {2}, northing: {3}, zone {4}, alt {5}, weeksecs : {6}'.format(i, time, easting, northing, zone, alt, weeksecs))
            i +=1
        
        
        LasStartTime_sow = shapefilecoordstimes[0]
        LasEndTime_sow = shapefilecoordstimes[entries-1]
        LasStartTime_st=SecondsOfWeek2StandardTime(LasStartTime_sow,SurveyDate)
        LasEndTime_st=SecondsOfWeek2StandardTime(LasEndTime_sow,SurveyDate)

        print(LasStartTime_st,LasEndTime_st )
        wp = shapefile.Writer(shapefile.POINTZ)
        wp.autoBalance = 1
        wp.field('FLIGHT','N',5,0)
        wp.field('PSID','N',5,0)
        wp.field('GPS','N',24,3)
        wp.field('TIME','C',40)
        wp.field('UTC_OFFSET','N',4,2)
        shapefilecoords=shapefilecoords[0::everynth*20]
        shapefilecoordstimes=shapefilecoordstimes[0::everynth*20]
        
        for i,point in enumerate(shapefilecoords):
            wp.point(point[0],point[1],point[2])
            wp.record(FLIGHT=flight,PSID=10100,GPS=(shapefilecoordstimes[i]),TIME=StandardTime2LocalTime(shapefilecoordstimes[i],utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset_hrs)
            

        wp.save(pointfile)

    
        w = shapefile.Writer(shapefile.POLYLINEZ)
        w.autoBalance = 1
        w.field('FLIGHT','N',5,0)
        w.field('PSID','N',5,0)
        w.field('MIN_GPS','N',24,3)
        w.field('MAX_GPS','N',24,3)
        w.field('MIN_TIME','C',40)
        w.field('MAX_TIME','C',40)
        w.field('UTC_OFFSET','N',4,2)
        
        #create line shapefile
        w.line(parts=[shapefilecoords[0::everynth*2]])
        w.record(FLIGHT=flight,PSID=psid,MIN_GPS=(LasStartTime_sow),MAX_GPS=(LasEndTime_sow),MIN_TIME=StandardTime2LocalTime(LasStartTime_sow,utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),MAX_TIME=StandardTime2LocalTime(LasEndTime_sow,utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset_hrs)
        
        w.save(linefile)

    
    return

if __name__ == "__main__":
    main()      