import riegl.rdb
import itertools
import time
import random
import sys
import math
import struct
import shutil
from datetime import datetime, timedelta, date
import os, glob
import collections
import subprocess
from collections import defaultdict , OrderedDict
import numpy as np
import pandas as pd
from riegl.rdb.pointattributes import PointAttributes
sys.path.append('{0}/lib/utm-0.4.0/'.format(sys.path[0]).replace('\\','/'))
import utm
from datetime import datetime, timedelta


def Rad2Deg(rad):
    return rad * 180 / math.pi

def SecondsOfWeek2StandardTime(sow,SurveyDate):
    date_format = "%d/%m/%Y"
    a = datetime.strptime('06/01/1980', date_format)
    b = datetime.strptime(SurveyDate, date_format)
    return sow+math.floor((b - a).days/7)*604800-1000000000

def StandardTime2LocalTime(gpstime, utctimeoffset_hrs):
    gpstime_days_part=math.floor(gpstime/60/60/24)
    gpstime_seconds_part=gpstime-(math.floor(gpstime/60/60/24)*60*60*24)
    
    GPSOrigin= datetime(1980,1,6,0,0,0)
    return GPSOrigin+timedelta(11574,6399)+timedelta(0,utctimeoffset_hrs*60*60)+timedelta(gpstime_days_part,gpstime_seconds_part)



def main():
    shapefilecoords = []
    shapefilecoordstimes = []
    trajrecords = []
    dtime = '210423_044814'
    dt = datetime.strptime(dtime, "%y%m%d_%H%M%S")
    print(dt)
    tt=dt.timetuple()
    SurveyDate = '{0}/{1}/{2}'.format(tt[2],tt[1],tt[0])
    print(SurveyDate)
    dayofweek = dt.weekday()
    print(dayofweek)

    lasfile="terst"
    utctimeoffset_hrs=10
    psid=1
    flight=1
    jsonfile="F:\\test\\{0}.json".format(dtime)
    entries=0
    
    with riegl.rdb.rdb_open("C:\\Users\\Manesha.Desilva\\Downloads\\210423_044814_Channel_1.pofx") as rdb:
    
        for point in rdb.points(None,["riegl.id" ,"riegl.pof_timestamp", "riegl.pof_latitude","riegl.pof_longitude","riegl.pof_height","riegl.pof_roll","riegl.pof_pitch","riegl.pof_yaw","riegl.pof_path_length"]):
            #print(point["riegl.id"] ,point["riegl.pof_timestamp"], point["riegl.pof_latitude"],point["riegl.pof_longitude"],point["riegl.pof_height"],point["riegl.pof_roll"],point["riegl.pof_pitch"],point["riegl.pof_yaw"],point["riegl.pof_path_length"])
            entries+=1
            time = point["riegl.pof_timestamp"]
            print(time)
            lon = point["riegl.pof_longitude"]

            lat = point["riegl.pof_latitude"]

            alt = point["riegl.pof_height"]

            roll = point["riegl.pof_roll"]
        
            pitch = point["riegl.pof_pitch"]

            head = point["riegl.pof_yaw"]

            easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon, 55) 


            #From RIWORLD.pdf - Appendix 35 
            #Time stamps are stored as normseconds [normsecs] within the file. This time format is equivalent to GPS week
            #seconds with only one exception: The first day is the date specified in the header (fields YEAR, MONTH and DAY)
            #whereas GPS week seconds always start on Sunday.
            days = math.floor(time/86400.0)

            secs = time - (days*86400.0)
            
            
            weeksecs = round(secs + ((dayofweek+days)%7)*86400.0, 3)
            
            stdtime = SecondsOfWeek2StandardTime(weeksecs, SurveyDate)
            localtime = StandardTime2LocalTime(stdtime,10)
            
            print(easting,northing,alt)
            shapefilecoords.append([easting,northing,alt])
            shapefilecoordstimes.append(SecondsOfWeek2StandardTime(weeksecs,SurveyDate))
            print(SecondsOfWeek2StandardTime(weeksecs,SurveyDate))
            trajrecords.append([SecondsOfWeek2StandardTime(weeksecs,SurveyDate),easting,northing,alt,head,roll,pitch])
    

        LasStartTime_st = round(shapefilecoordstimes[0],4)
        LasEndTime_st = round(shapefilecoordstimes[entries-1],4)

        firstpoint = shapefilecoords[0]
        lastpoint = shapefilecoords[entries-1]
        
        with open(jsonfile, 'a') as geo:
            geostr = '{ "type": "FeatureCollection", "features": [{"type" : "Feature", "geometry" : { "type": "LineString", "coordinates": ['            
            pointfeature = '[{0}, {1}],[{2}, {3}]'.format(str(firstpoint[0]), str(firstpoint[1]), str(lastpoint[0]), str(lastpoint[1]))
            geostr = geostr + pointfeature
            geostr = geostr + ']},"properties": { "PSID":' + str(psid) + ',"FLIGHT":'+str(flight)+',"START_TIME":"'+StandardTime2LocalTime(LasStartTime_st, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")+'","END_TIME":"'+StandardTime2LocalTime(LasEndTime_st, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")+'","LAS_FILE": "'+lasfile+'"} } ] }'
        
            geo.write(geostr)
        geo.close()

        print(LasStartTime_st,LasEndTime_st )
        wp = shapefile_original.Writer(shapefile_original.POINTZ)
        wp.autoBalance = 1
        wp.field('FLIGHT','N',5,0)
        wp.field('PSID','N',10,0)
        wp.field('GPS','N',24,3)
        wp.field('TIME','C',40)
        wp.field('UTC_OFFSET','N',4,2)
        wp.field('LAS_FILE','C',80)
        shapefilecoords=shapefilecoords[0::everynth*1]
        shapefilecoordstimes_new=shapefilecoordstimes[0::everynth*1]

    return

if __name__ == "__main__":
    main()       
