#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
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
from gooey import Gooey, GooeyParser
import riegl.rdb 

from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/utm-0.4.0/'.format(sys.path[0]).replace('\\','/'))
import utm
sys.path.append('{0}/lib/shapefile_original/'.format(sys.path[0]).replace('\\','/'))
import shapefile_original
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 18/01/2019 - Manesha De Silva - reading pof files, converting to shp files abstracted from Sbet2Traj.py - Alex Rixon
#


#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#
#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
__keepfiles=None #can be overritten by settings

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Insert PSID", use_legacy_titles=True, required_cols=1, default_size=(1000,830))
def param_parser():
    parser=GooeyParser(description="Converts POS files to SHP files and Inserts the PSID to corresponding LAS file")
    parser.add_argument("input_folder", metavar="POF Directory ", widget="DirChooser", help="Select folder with pof files")
    parser.add_argument("output_dir", metavar="Output Directory", widget="DirChooser", help="Output directory")
    parser.add_argument("poffiletype",metavar="POF type", choices=['pof', 'pofx'], default='pof')
    parser.add_argument("poffilepattern",metavar="POF File name Pattern", help=" 190112_223007_Scanner_1.pof -> %D%_Scanner_1.pof", default='%D%_Channel_1.pof')
    parser.add_argument("psid", metavar="Enter the first swath/PSID number", type=int)
    parser.add_argument("flight", metavar="Flight No", type=int, default=1)
    parser.add_argument("zone", metavar="Zone", type=int)
    parser.add_argument("utctimeoffset", metavar="UTC time offset", type=float, default=10)
    parser.add_argument('everynth', metavar="Point thinning (every nth point)", type=int, default=20)
    parser.add_argument("--insert", metavar="Insert PSID to LAS", help="Tick if You need to insert PSID to corresponding LAS files", action= "store_false")
    parser.add_argument("--lasinput_dir", metavar="LAS Directory", widget="DirChooser", help="Input directory")
    parser.add_argument("--file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument("--out_file_type",metavar="Output File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument("--file_version",metavar="Las File Version", help="Enter las file version(Ex: 1.4)", default=1.4, type=float)  
    parser.add_argument("--cores", metavar="Number of Cores", help="Number of cores", type=int, default=10, gooey_options={
        'validator': {
            'test': '2 <= int(user_input) <= 20',
            'message': 'Must be between 2 and 20'
        }})


    return parser.parse_args()

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

def insertPSID(input, outlas, filetype, psid, channel, version):    
    log = ''

    try:

        subprocessargs=['c:\\lastools\\bin\\las2las.exe', '-i', input ,'-o{0}'.format(filetype), '-o', outlas,'-set_point_source', '{0}'.format(psid),'-target_precision','0.001','-target_elevation_precision','0.001']
        subprocessargs=list(map(str,subprocessargs))
        p = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True) 

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    except Exception as e:
        log = "\n insertPSID {0} \n Exception {1}".format(input, e)
        return(False,None, log)
    
    finally:
        if os.path.isfile(outlas):
            log = log +'\nInserting PSID completed for {0}'.format(outlas)
            print(log)
            return (True, outlas, log)
        else:
            print(log)
            log = log + '\nPSID could not be inserted to {0}'.format(input)
            return (False, None, log)



def makeshapefile(input, lasfile, pointsfile, linesfile, trajfile, jsonfile, psid, flight, utm_zone, utctimeoffset_hrs, everynth):
    log = ''

    if not lasfile == None:
        path, lasfilename, ext = AtlassGen.FILESPEC(lasfile)
        lasfile = '{0}.{1}'.format(lasfilename,ext)
    else:
        lasfile = 'None'

    print(input)
    try:
        with open(input, mode='rb') as file:

            fileContent = file.read()

            majmin = struct.unpack('HH',fileContent[27:31])
            dataoffset = struct.unpack('L',fileContent[31:35])[0]
            date = struct.unpack('HHH', fileContent[35:41])
            entries = struct.unpack('N', fileContent[41:49])[0]
            minlon = struct.unpack('d', fileContent[49:57])[0]
            maxlon = struct.unpack('d', fileContent[57:65])[0]
            minlat = struct.unpack('d', fileContent[65:73])[0]
            maxlat = struct.unpack('d', fileContent[73:81])[0]
            timeunit = int(struct.unpack('B', fileContent[121:122])[0])
            file.seek(123)
            timezone = file.read(9)
            timezone = timezone.decode('ascii').split('+')[1]
        

            SurveyDate = '{0}/{1}/{2}'.format(date[2],date[1],date[0])
            prnt = '----------------------Header INFO------------------------\nmajmin: {0}, \ndataoffset: {1}, \nsurvey date: {2}, \nentries: {3}, \nminlon: {4}, \nmaxlon: {5}, \nminlat: {6}, \nmaxlat: {7}, \ntimeitype: {8}, \ntimezone: {9}\n---------------------------------------------------------'.format(majmin,dataoffset, SurveyDate, entries, minlon, maxlon, minlat, maxlat, timeunit, timezone)
            print(prnt)

            shapefilecoords = []
            shapefilecoordstimes = []
            trajrecords = []

            #loop through the data set starting from the dataoffset position,  64 bytes per dataset 
            for i in range(entries):
                seekpos = (dataoffset+(i*64))
                file.seek(seekpos)
                fileContent = file.read(65)
                #print('starting data at byte position : {0}'.format(seekpos))
                time = struct.unpack('d',fileContent[:8])[0]

                lon = struct.unpack('d',fileContent[8:16])[0]

                lat = struct.unpack('d',fileContent[16:24])[0]

                alt = struct.unpack('d', fileContent[24:32])[0]

                roll = struct.unpack('d', fileContent[32:40])[0]
            
                pitch = struct.unpack('d', fileContent[40:48])[0]

                head = struct.unpack('d', fileContent[48:56])[0]

                easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon, utm_zone) 

                #From RIWORLD.pdf - Appendix 35 
                #Time stamps are stored as normseconds [normsecs] within the file. This time format is equivalent to GPS week
                #seconds with only one exception: The first day is the date specified in the header (fields YEAR, MONTH and DAY)
                #whereas GPS week seconds always start on Sunday.
                days = math.floor(time/86400.0)

                secs = time - (days*86400.0)
                #Adding +1 as weekday () function of datetime module returns the day-of-week as an integer from 0 to 6 representing Monday to Sunday. But GPS week seconds starts on Sunday
                dayofweek = datetime.date(date[0],date[1],date[2]).weekday()+1
                weeksecs = round(secs + ((dayofweek+days)%7)*86400.0, 3)
                
                stdtime = SecondsOfWeek2StandardTime(weeksecs, SurveyDate)
                localtime = StandardTime2LocalTime(stdtime,utctimeoffset_hrs)

                shapefilecoords.append([easting,northing,alt])
                shapefilecoordstimes.append(SecondsOfWeek2StandardTime(weeksecs,SurveyDate))
                trajrecords.append([SecondsOfWeek2StandardTime(weeksecs,SurveyDate),easting,northing,alt,head,roll,pitch])
            
      
                #if (i%10000)==0:
                    #print( weeksecs, stdtime, localtime)
                    #print(lat, lon, easting, northing,zone_number, zone_letter)
                    #print('\n\n{0}  -   time: {1}, easting : {2}, northing: {3}, zone {4}, alt {5}, weeksecs : {6}'.format(i, time, easting, northing, utm_zone, alt, weeksecs))
                #i +=1
            
    
            
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
            
            '''
            #Point based Geojson
            with open(jsonfile, 'a') as geoj:
                geostr = '{ "type": "FeatureCollection", "features": [{"type" : "Feature", "geometry" : { "type": "LineString", "coordinates": ['      
                
                for i, point in enumerate(shapefilecoords):      
                    pointfeature = '[{0}, {1}],'.format(str(point[0]), str(point[1]))
                    geostr = geostr + pointfeature
                geostr = geostr + ']},"properties": { "PSID":' + str(psid) + ',"FLIGHT":'+str(flight)+',"START_TIME":"'+StandardTime2LocalTime(LasStartTime_st, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")+'","END_TIME":"'+StandardTime2LocalTime(LasEndTime_st, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")+'","LAS_FILE": "'+lasfile+'"} } ] }'
            
                geoj.write(geostr)
            geoj.close()
            '''
            for i,point in enumerate(shapefilecoords):
                wp.point(point[0],point[1],point[2])
                wp.record(FLIGHT=flight,PSID=psid,GPS=(shapefilecoordstimes_new[i]),TIME=StandardTime2LocalTime(shapefilecoordstimes_new[i],utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset_hrs,LAS_FILE=lasfile)

            wp.save(pointsfile)
        
            w = shapefile_original.Writer(shapefile_original.POLYLINEZ)
            w.autoBalance = 1
            w.field('FLIGHT','N',5,0)
            w.field('PSID','N',10,0)
            w.field('MIN_GPS','N',24,3)
            w.field('MAX_GPS','N',24,3)
            w.field('MIN_TIME','C',40)
            w.field('MAX_TIME','C',40)
            w.field('UTC_OFFSET','N',4,2)
            w.field('LAS_FILE','C',80)
            #create line shapefile
            w.line(parts=[shapefilecoords[0::everynth*1]])
            w.record(FLIGHT=flight,PSID=psid,MIN_GPS=(LasStartTime_st),MAX_GPS=(LasEndTime_st),MIN_TIME=StandardTime2LocalTime(LasStartTime_st,utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),MAX_TIME=StandardTime2LocalTime(LasEndTime_st,utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset_hrs,LAS_FILE=lasfile)
            
            w.save(linesfile)

            
            #create trj file
            # terra scan trj format

            TrajHdr=struct.Struct('< 8s i i i i 78s B B d d i i 400s d d 400s d d 400s 16s')
            TrajPos=struct.Struct('< d d d d d d d B B B B h h')

            TrajHdrValues=('TSCANTRJ'.encode('utf-8'),20010715,1376,entries,64,input.encode('utf-8'),0,3,shapefilecoordstimes[0],shapefilecoordstimes[entries-1],psid,psid,''.encode('utf-8'),0.0,0.0,''.encode('utf-8'),0.0,0.0,''.encode('utf-8'),'flight_{0}'.format(flight).encode('utf-8'))


            with open(trajfile, "wb") as f:

                #write header
                print(TrajHdrValues)
                TrajHdrPacked_data = TrajHdr.pack(*TrajHdrValues)
                f.write(TrajHdrPacked_data) 
                print('written header')

                for i,point in enumerate(trajrecords):

                    TrajPosValues=(point[0],point[1],point[2],point[3],point[4],point[5],point[6],0,0,0,0,0,0)
                    TrajPosPacked_data=TrajPos.pack(*TrajPosValues)
                    f.write(TrajPosPacked_data)

                f.close
            
    except Exception as e:
        log = log +'\nMaking SHP Failed at exception for : {0}'.format(input)
        print('Exception : {0}'.format(e))
        file.close
        return (False, None, log)

    finally:
        if os.path.isfile(pointsfile+'.shp') and os.path.isfile(linesfile+'.shp'):
            log = log +'\nSHP files created for  : {0}'.format(input)
            print(log)
            file.close
            return (True, [pointsfile, linesfile], log)
        else:
            print(log)
            log = log + '\nSHP file could NOT be created for {0}'.format(input)
            file.close
            return (False, None, log)


def makeshapefilepofx(input, lasfile, pointsfile, linesfile, trajfile, jsonfile, psid, flight, utm_zone, utctimeoffset_hrs, everynth,dtime):
    log = ''

    if not lasfile == None:
        path, lasfilename, ext = AtlassGen.FILESPEC(lasfile)
        lasfile = '{0}.{1}'.format(lasfilename,ext)
    else:
        lasfile = 'None'

    print(input)

    shapefilecoords = []
    shapefilecoordstimes = []
    trajrecords = []

    dt = datetime.datetime.strptime(dtime, "%y%m%d_%H%M%S")
    print(dt)
    tt=dt.timetuple()
    SurveyDate = '{0}/{1}/{2}'.format(tt[2],tt[1],tt[0])
    print(SurveyDate)
    #Adding +1 as weekday () function of datetime module returns the day-of-week as an integer from 0 to 6 representing Monday to Sunday. But GPS week seconds starts on Sunday
    dayofweek = dt.weekday()+1
    print(dayofweek)
    entries=0

    try:
        with riegl.rdb.rdb_open(input) as rdb:
        
            for point in rdb.points(None,["riegl.id" ,"riegl.pof_timestamp", "riegl.pof_latitude","riegl.pof_longitude","riegl.pof_height","riegl.pof_roll","riegl.pof_pitch","riegl.pof_yaw","riegl.pof_path_length"]):
                #print(point["riegl.id"] ,point["riegl.pof_timestamp"], point["riegl.pof_latitude"],point["riegl.pof_longitude"],point["riegl.pof_height"],point["riegl.pof_roll"],point["riegl.pof_pitch"],point["riegl.pof_yaw"],point["riegl.pof_path_length"])
                entries+=1
                time = point["riegl.pof_timestamp"]
                lon = point["riegl.pof_longitude"]

                lat = point["riegl.pof_latitude"]

                alt = point["riegl.pof_height"]

                roll = point["riegl.pof_roll"]
            
                pitch = point["riegl.pof_pitch"]

                head = point["riegl.pof_yaw"]

                easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon, utm_zone) 

                days = math.floor(time/86400.0)

                secs = time - (days*86400.0)
                
                weeksecs = round(secs + ((dayofweek+days)%7)*86400.0, 3)
                
                stdtime = SecondsOfWeek2StandardTime(weeksecs, SurveyDate)
                localtime = StandardTime2LocalTime(stdtime,utctimeoffset_hrs)
                

                shapefilecoords.append([easting,northing,alt])
                shapefilecoordstimes.append(SecondsOfWeek2StandardTime(weeksecs,SurveyDate))
                trajrecords.append([SecondsOfWeek2StandardTime(weeksecs,SurveyDate),easting,northing,alt,head,roll,pitch])
                
                #if (i%10000)==0:
                    #print( weeksecs, stdtime, localtime)
                    #print(lat, lon, easting, northing,zone_number, zone_letter)
                    #print('\n\n{0}  -   time: {1}, easting : {2}, northing: {3}, zone {4}, alt {5}, weeksecs : {6}'.format(i, time, easting, northing, utm_zone, alt, weeksecs))
                #i +=1
            

            
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
            
            '''
            #Point based Geojson
            with open(jsonfile, 'a') as geoj:
                geostr = '{ "type": "FeatureCollection", "features": [{"type" : "Feature", "geometry" : { "type": "LineString", "coordinates": ['      
                
                for i, point in enumerate(shapefilecoords):      
                    pointfeature = '[{0}, {1}],'.format(str(point[0]), str(point[1]))
                    geostr = geostr + pointfeature
                geostr = geostr + ']},"properties": { "PSID":' + str(psid) + ',"FLIGHT":'+str(flight)+',"START_TIME":"'+StandardTime2LocalTime(LasStartTime_st, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")+'","END_TIME":"'+StandardTime2LocalTime(LasEndTime_st, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")+'","LAS_FILE": "'+lasfile+'"} } ] }'
            
                geoj.write(geostr)
            geoj.close()
            '''
            for i,point in enumerate(shapefilecoords):
                wp.point(point[0],point[1],point[2])
                wp.record(FLIGHT=flight,PSID=psid,GPS=(shapefilecoordstimes_new[i]),TIME=StandardTime2LocalTime(shapefilecoordstimes_new[i],utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset_hrs,LAS_FILE=lasfile)

            wp.save(pointsfile)
        
            w = shapefile_original.Writer(shapefile_original.POLYLINEZ)
            w.autoBalance = 1
            w.field('FLIGHT','N',5,0)
            w.field('PSID','N',10,0)
            w.field('MIN_GPS','N',24,3)
            w.field('MAX_GPS','N',24,3)
            w.field('MIN_TIME','C',40)
            w.field('MAX_TIME','C',40)
            w.field('UTC_OFFSET','N',4,2)
            w.field('LAS_FILE','C',80)
            #create line shapefile
            w.line(parts=[shapefilecoords[0::everynth*1]])
            w.record(FLIGHT=flight,PSID=psid,MIN_GPS=(LasStartTime_st),MAX_GPS=(LasEndTime_st),MIN_TIME=StandardTime2LocalTime(LasStartTime_st,utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),MAX_TIME=StandardTime2LocalTime(LasEndTime_st,utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset_hrs,LAS_FILE=lasfile)
            
            w.save(linesfile)

            
            #create trj file
            # terra scan trj format

            TrajHdr=struct.Struct('< 8s i i i i 78s B B d d i i 400s d d 400s d d 400s 16s')
            TrajPos=struct.Struct('< d d d d d d d B B B B h h')

            TrajHdrValues=('TSCANTRJ'.encode('utf-8'),20010715,1376,entries,64,input.encode('utf-8'),0,3,shapefilecoordstimes[0],shapefilecoordstimes[entries-1],psid,psid,''.encode('utf-8'),0.0,0.0,''.encode('utf-8'),0.0,0.0,''.encode('utf-8'),'flight_{0}'.format(flight).encode('utf-8'))


            with open(trajfile, "wb") as f:

                #write header
                print(TrajHdrValues)
                TrajHdrPacked_data = TrajHdr.pack(*TrajHdrValues)
                f.write(TrajHdrPacked_data) 
                print('written header')

                for i,point in enumerate(trajrecords):

                    TrajPosValues=(point[0],point[1],point[2],point[3],point[4],point[5],point[6],0,0,0,0,0,0)
                    TrajPosPacked_data=TrajPos.pack(*TrajPosValues)
                    f.write(TrajPosPacked_data)

                f.close
  
      
    except Exception as e:
        log = log +'\nMaking SHP Failed at exception for : {0}'.format(input)
        print('Exception : {0}'.format(e))
       
        return (False, None, log)

    finally:
        if os.path.isfile(pointsfile+'.shp') and os.path.isfile(linesfile+'.shp'):
            log = log +'\nSHP files created for  : {0}'.format(input)
            print(log)
           
            return (True, [pointsfile, linesfile], log)
        else:
            print(log)
            log = log + '\nSHP file could NOT be created for {0}'.format(input)
            
            return (False, None, log)
    
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    freeze_support()
    args = param_parser()

    #This is added because check box does not work with a default =True, as it always returns true if checked or not. Therefore using store_false and inverting the results
    if args.insert== False:
        args.insert = True
    else:   
        args.insert = False


    intputfolder = args.input_folder
    outputpath = args.output_dir
    lasfolder = args.lasinput_dir
    filetype = args.file_type  
    poffiletype=args.poffiletype
    filepattern = '*.{0}'.format(poffiletype)
    if args.insert ==True and args.lasinput_dir ==None:
        print("insert PSID to LAS is ticked but LAS folder is not selected, Please select the LAS folder and rerun")
        exit()

    if not lasfolder == None:
        args.insert = True
    poffilepattern = args.poffilepattern
    poffilepattern = poffilepattern.replace('.{0}'.format(poffiletype), '')
    lasfilepattern = '*.{0}'.format(filetype)
    filepattern = filepattern.split(';')
    lasfilepattern = lasfilepattern.split(';')
    files = AtlassGen.FILELIST(filepattern, intputfolder)
    print(args.insert)
    if args.insert:
        lasfiles = AtlassGen.FILELIST(lasfilepattern, lasfolder)
    psid = int(args.psid)
    everynth =int(args.everynth)
    flight = int(args.flight)    
    zone = int(args.zone)
    utctimeoffset_hrs = float(args.utctimeoffset)
    cores = int(args.cores)
    dt = strftime("%y%m%d_%H%M")
    version = args.file_version
  

    if len(files)==0 :
        print('POF files not found : Exiting ....')
        exit()
    if args.insert and len(lasfiles)==0:

        print('LAS files not found : Exiting ....')
        exit()

        if len(files) != len(lasfiles):
            print('Number of LAS files are not equal to the number of POF files')
            exit()
    
    workingdir = AtlassGen.makedir(os.path.join(outputpath, '{0}_PSID_Applied'.format(dt))).replace('\\','/')
    pointsdir = AtlassGen.makedir(os.path.join(workingdir, 'trj_points')).replace('\\','/')
    linedir = AtlassGen.makedir(os.path.join(workingdir, 'trj_centerLines')).replace('\\','/')
    trajdir = AtlassGen.makedir(os.path.join(workingdir, 'trj_terrascan')).replace('\\','/')
    lasdir = os.path.join(workingdir, 'lasfiles').replace('\\','/')
    jsondir = AtlassGen.makedir(os.path.join(workingdir, 'json_files')).replace('\\','/')


    logpath = os.path.join(workingdir,'log_POFtoSHP.txt').replace('\\','/')
    log = open(logpath, 'w')
    

    filesdict = collections.OrderedDict()

    for file in files:
        path, filename, ext = AtlassGen.FILESPEC(file)
        if not args.insert:
            poffilename = filename
            patternsplit = poffilepattern.split("%D%")
            #print(list(patternsplit))
 
            for i in range(len(patternsplit)):
                poffilename = poffilename.replace(patternsplit[i], '')
            
            pofdatetime = poffilename
            print('pof ID : {0}'.format(pofdatetime))
            filesdict[pofdatetime] = {'poffile': file, 'lasfile': None}

        else:
            poffilename = filename

            patternsplit = poffilepattern.split("%D%")
            #print(list(patternsplit))
 
            for i in range(len(patternsplit)):
                poffilename = poffilename.replace(patternsplit[i], '')
            
            pofdatetime = poffilename
            print('pof ID : {0}'.format(pofdatetime))


            lasfile = glob.glob('{0}/*{1}*.{2}'.format(lasfolder, pofdatetime, filetype))
            print(lasfile)
            if  not len(lasfile) == 0:
                filesdict[pofdatetime] = {'poffile': file, 'lasfile': lasfile[0]}
            else:
                filesdict[pofdatetime] = {'poffile': file, 'lasfile': None}
                logw = "Matching LAS file not found for {0} in directory {1}".format(file, lasfolder)
                print(log)
                log.write(logw)


    orderedfiles = collections.OrderedDict(sorted(filesdict.items()))
   

    make_shpfiles = {}
    add_psid2las = {}

    for key, values in orderedfiles.items():

        input = values['poffile']
        lasfile = values['lasfile']
        points = os.path.join(pointsdir,'{0}_points_{1}'.format(key, psid)).replace('\\','/')
        lines =  os.path.join(linedir,'{0}_lines_{1}'.format(key, psid)).replace('\\','/')
        trajfile = os.path.join(trajdir,'{0}_{1}.trj'.format(key, psid)).replace('\\','/')
        jsonfile = os.path.join(jsondir,'{0}_{1}.json'.format(key, psid)).replace('\\','/')
        lasoutput = os.path.join(lasdir, '{0}_{1}.{2}'.format(key,psid, args.out_file_type)).replace('\\','/')
        
        if poffiletype=='pofx':
            print(key)
            make_shpfiles[key] = AtlassTask(input, makeshapefilepofx, input, lasfile, points, lines, trajfile, jsonfile, psid, flight, zone, utctimeoffset_hrs, everynth,key)
        
        else:
            make_shpfiles[key] = AtlassTask(input, makeshapefile, input, lasfile, points, lines, trajfile, jsonfile, psid, flight, zone, utctimeoffset_hrs, everynth)

        add_psid2las[key] = AtlassTask(input, insertPSID, lasfile, lasoutput, args.out_file_type, psid, flight, version)
        #makeshapefile(input, points, lines, psid, flight, zone, utctimeoffset_hrs, everynth)   

        psid +=1
    
    p=Pool(processes=cores)    
    make_shpfiles_results=p.map(AtlassTaskRunner.taskmanager,make_shpfiles.values())


    for result in make_shpfiles_results:
        print('SHP file output for : {1},\t\t Status : {0}'.format(result.success, result.name))
        log.write(result.log)


    if args.insert:
        AtlassGen.makedir(lasdir)
        print('Inserting the PSID to LAS files')
        p=Pool(processes=cores)      
        add_psid2las_results=p.map(AtlassTaskRunner.taskmanager, add_psid2las.values())
        for result in add_psid2las_results:
            log.write(result.log)
            print('Output LAS file : {1},\t\t Status : {0}'.format(result.success, result.name))
    return

if __name__ == "__main__":
    main()         
