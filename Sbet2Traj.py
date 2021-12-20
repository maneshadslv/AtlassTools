#!/usr/bin/python

import sys, getopt
import math
import shutil
import subprocess
import os
import random
import struct
import binascii
from datetime import datetime, timedelta

sys.path.append('{0}/Lib/utm-0.4.0/'.format(sys.path[0]))
import utm

sys.path.append('{0}/Lib/sbet_handler'.format(sys.path[0]))
import sbet_handler

sys.path.append('{0}/lib/shapefile_original'.format(sys.path[0]))
import shapefile_original

# terra scan trj format
TrajHdr=struct.Struct('< 8s i i i i 78s B B d d i i 400s d d 400s d d 400s 16s')
TrajPos=struct.Struct('< d d d d d d d B B B B h h')

def PrintHelp():
    print('help')
    return
    
def FILESPEC(filename):
    path,name=os.path.split(filename)
    name,ext=name.split(".")
    return [path, name, ext]

def Rad2Deg(rad):
    return rad * 180 / math.pi
    
def Deg2Rad(deg):
    return deg / 180 * math.pi    
    
def HeadingConvergenceCorrection(lat,lon,UTM_Zone):
    cm=(UTM_Zone-0.5)*6-180
    #print 'cm={0}'.format(cm)
    #print 'HeadingConvergenceCorrection={0}'.format(Rad2Deg(math.atan(math.tan(Deg2Rad(lon-cm))*math.sin(Deg2Rad(lat)))))
    return math.atan(math.tan(Deg2Rad(lon-cm))*math.sin(Deg2Rad(lat)))
    
def StandardTime2LocalTime(gpstime, utctimeoffset_hrs):
    gpstime_days_part=math.floor(gpstime/60/60/24)
    gpstime_seconds_part=gpstime-(math.floor(gpstime/60/60/24)*60*60*24)
    
    GPSOrigin= datetime(1980, 1, 6,0,0,0)
    return GPSOrigin+timedelta(11574,6399)+timedelta(0,utctimeoffset_hrs*60*60)+timedelta(gpstime_days_part,gpstime_seconds_part)
    
def SecondsOfWeek2StandardTime(sow,SurveyDate):
    date_format = "%d/%m/%Y"
    a = datetime.strptime('06/01/1980', date_format)
    b = datetime.strptime(SurveyDate, date_format)
    return sow+math.floor((b - a).days/7)*604800-1000000000
    
def StandardTime2SecondsOfWeek(st):
    return st-(math.floor((st+1000000000)/604800)*604800-1000000000)    
    
def main(argv):

    sbet=''
    trajdir=''
    starttime=0.0
    endtime=0.0
    everynth=1
    buffer=0.01
    psid=0
    flight=1
    channel=1
    version=1.2
    UTM_Zone=-99
    extn='laz'
    SurveyDate=''
    utctimeoffset=10
    sbet_rec_format=sbet_handler.get_sbet_rec_format()
    outlas='F:/temp'
    # c:\python27\python.exe \\10.10.10.100\temp\Alex\Python\scripts\Sbet2Traj.py --lasstrip=c:\my_laz.laz --psid=1000 --sbet=c:\my_sbet.out --UTM_Zone=56 --outlas=c:\psid\my_laz.laz --extn=laz --flight=1 --trajout=c:\psid\traj\my_laz.trj
    try:
        opts, args = getopt.getopt(argv,"h",["help","sbet=","trajout=","starttime=","endtime=","everynth=","psid=","channel=","version=","utctimeoffset=","UTM_Zone=","lasstrip=","outlas=","crosstie=","extn=","SurveyDate=","flight="] )
    except getopt.GetoptError as err:
        # print help information and exit:
        print (str(err)) # will print something like "option -a not recognized"
        PrintHelp()
        sys.exit(2)
        
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            PrintHelp()
            sys.exit(0)
        elif opt == '--sbet':
            sbet='{0}'.format(arg)
        elif opt == '--starttime':
            starttime=StandardTime2SecondsOfWeek(float(arg)-1.0)
        elif opt == '--endtime':
            endtime=StandardTime2SecondsOfWeek(float(arg)+1.0)
        elif opt == '--trajout':
            trajout='{0}'.format(arg)
            trajout=trajout.replace("\\","/")
        elif opt == '--everynth':
            everynth=int(arg)
        elif opt == '--psid':
            psid=int(arg)
        elif opt == '--flight':
            flight=int(arg)
        elif opt == '--channel':
            channel=int(channel)
        elif opt == '--version':
            version=float(version)
        elif opt == '--utctimeoffset':
            utctimeoffset=float(arg)
        elif opt == '--UTM_Zone':
            UTM_Zone=int(arg)
        elif opt == '--lasstrip':
            lasstrip='{0}'.format(arg)
            lasstrip=lasstrip.replace("\\","/")
            print(lasstrip)
        elif opt == '--outlas':
            outlas='{0}'.format(arg)
            outlas=outlas.replace("\\","/")
        elif opt == '--SurveyDate':
            SurveyDate='{0}'.format(arg)   
        elif opt == '--crosstie':
            crosstie='{0}'.format(arg) 
        elif opt == '--extn':
            extn='{0}'.format(arg)             
        else:
            sys.exit(1)
            
    lasstripspec=FILESPEC(lasstrip)
    print('-o{0}'.format(lasstripspec[2]))
    if not version==1.4:
        subprocessargs=['c:\\lastools\\bin\\las2las.exe', '-i', lasstrip ,'-o{0}'.format(extn), '-o', outlas,'-set_point_source', '{0}'.format(psid),'-set_user_data',channel,'-target_precision','0.001','-target_elevation_precision','0.001']
    else:
        subprocessargs=['c:\\lastools\\bin\\las2las.exe', '-i', lasstrip ,'-o{0}'.format(extn), '-o', outlas,'-set_point_source', '{0}'.format(psid),'-set_extended_scanner_channel',channel,'-target_precision','0.001','-target_elevation_precision','0.001']
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)
    
    subprocessargs=['c:\\lastools\\bin\\lasboundary.exe', '-i', lasstrip ,'-oshp', '-o', trajout.replace('.trj','_bdy.shp'),'-concavity',50,'-holes','-disjoint']
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)

    
    subprocessargs=['c:\\lastools\\bin\\lasindex.exe', '-i', outlas ]
    print(subprocessargs)
    subprocessargs=map(str,subprocessargs)
    subprocess.call(subprocessargs)    
    
    infofile=lasstripspec[0]+'/'+lasstripspec[1]+"_info.txt"
    subprocessargs =['c:\\lastools\\bin\\lasinfo.exe','-otxt','-no_check_outside','-keep_every_nth','100'] + ['-i', lasstrip,'-o',infofile]
    print(subprocessargs)
    subprocess.call(subprocessargs)    
    print('readind las header')
    for line in [line.rstrip('\n') for line in open(infofile)]:
        line=line.strip()
        if line[:len("gps_time")]=="gps_time":
            line=line.split()
            GpsStartTime=(float(line[1])-buffer)
            GpsEndTime=(float(line[2])+buffer)      
    os.remove(infofile)
    print('Gps time range',GpsStartTime,GpsEndTime)
    print('reading Sbet everynt {0}'.format(everynth))
    SbetInfo=sbet_handler.readSbet_packed(sbet,everynth)
    print('Sbet read ok')
    
    if not SurveyDate=='':
        print('survey date override')
        LasStartTime_sow=GpsStartTime
        LasEndTime_sow=GpsEndTime
        LasStartTime_st=SecondsOfWeek2StandardTime(GpsStartTime,SurveyDate)
        LasEndTime_st=SecondsOfWeek2StandardTime(GpsEndTime,SurveyDate)
    else:
        LasStartTime_st=GpsStartTime
        LasEndTime_st=GpsEndTime
        LasStartTime_sow=StandardTime2SecondsOfWeek(GpsStartTime)
        LasEndTime_sow=StandardTime2SecondsOfWeek(GpsEndTime)
    SbetStartTime_sow=struct.unpack(sbet_rec_format, SbetInfo[0])[0]
    SbetEndTime_sow=struct.unpack(sbet_rec_format, SbetInfo[len(SbetInfo)-1])[0]    
    SurveyDate=(StandardTime2LocalTime(LasStartTime_st,0)).strftime("%d/%m/%Y")    
    
    # las search time is buffered by 1 second in each direction
    print('LAS start time:{0}'.format(LasStartTime_st))
    print('LAS end time:{0}'.format(LasEndTime_st))
    print('LAS start time (sow):{0}'.format(LasStartTime_sow))
    print('LAS end time(sow):{0}'.format(LasEndTime_sow)) 
    
    print('Sbet start time (sow):{0}'.format(SbetStartTime_sow))
    print('Sbet end time (sow):{0}'.format(SbetEndTime_sow))
    print('Survey date based on start las time: {0}'.format(SurveyDate))
    
    
    if (LasStartTime_sow-SbetStartTime_sow) < -100:
        #Las time starts in the next gps week
        SearchStartTime_sow=LasStartTime_sow+604800
        print('Las starts in the next GPS week.')
        SurveyDate=(StandardTime2LocalTime(LasStartTime_st-(LasStartTime_sow-SbetStartTime_sow+604800),0)).strftime("%d/%m/%Y")
        print('Adjusting survey date based on start of SBET: {0}'.format(SurveyDate) )  
        print('Adjusting start (sow) search time to {0}'.format(SearchStartTime_sow))
    elif (LasStartTime_sow-SbetStartTime_sow) >=0 and (LasStartTime_sow-SbetStartTime_sow)<= 604800:
        #las starts after Sbet in the same GPS week
        SearchStartTime_sow=LasStartTime_sow
    else:
        pass
        
    if (SbetEndTime_sow-LasEndTime_sow) >=0 and (SbetEndTime_sow-LasEndTime_sow) <= 604800:
        #las ends in the same gps week as the sbet
        SearchEndTime_sow=LasEndTime_sow   
    elif (SbetEndTime_sow-LasEndTime_sow) > 604800:
        SearchEndTime_sow=LasEndTime_sow+604800
        print('Adjusting end (sow) search time to {0}'.format(SearchEndTime_sow))
    else:
        pass
    
    try:
        print(SearchStartTime_sow)
        StartRecID=sbet_handler.getPosition(SearchStartTime_sow,SbetInfo,True)
    except:
        print('Failed to find start record')
        
    try:
        print(SearchEndTime_sow)
        EndRecID=sbet_handler.getPosition(SearchEndTime_sow,SbetInfo,True)    
    except:
        print('Failed to find end record')
	

    print('Trj start time: {0}'.format(SecondsOfWeek2StandardTime(struct.unpack(sbet_rec_format, SbetInfo[StartRecID])[0],SurveyDate)))
    print('Trj end time: {0}'.format(SecondsOfWeek2StandardTime(struct.unpack(sbet_rec_format, SbetInfo[EndRecID])[0],SurveyDate)))
    
    #if zone not defined then set to zone of first sbet record.
    latitude=Rad2Deg(struct.unpack(sbet_rec_format, SbetInfo[0])[1])
    longitude=Rad2Deg(struct.unpack(sbet_rec_format, SbetInfo[0])[2])    
    if UTM_Zone==-99:
        UTM_Zone=math.floor((longitude + 180)/6) + 1  
    
    StartRec=struct.unpack(sbet_rec_format, SbetInfo[StartRecID])
    EndRec=struct.unpack(sbet_rec_format, SbetInfo[EndRecID])
    
    TrajHdrValues=('TSCANTRJ',20010715,1376,(EndRecID-StartRecID),64,sbet,0,3,SecondsOfWeek2StandardTime(StartRec[0],SurveyDate),SecondsOfWeek2StandardTime(EndRec[0],SurveyDate),psid,psid,'',0.0,0.0,'',0.0,0.0,'','flight_{0}'.format(flight))
    shapefile_original.coords=[]
    shapefile_original.coordstimes=[]
    
    with open (trajout, "wb") as f:
        #write header
        print(TrajHdrValues)
        TrajHdrPacked_data = TrajHdr.pack(*TrajHdrValues)
        f.write(TrajHdrPacked_data) 
        for rec in range(StartRecID,EndRecID,1):
            CurrentRec=struct.unpack(sbet_rec_format, SbetInfo[rec])
            latitude=Rad2Deg(CurrentRec[1])
            longitude=Rad2Deg(CurrentRec[2])

            easting, northing, zone_number, zone_letter = utm.from_latlon(latitude, longitude, UTM_Zone) 
            shapefile_original.coords.append([easting,northing,CurrentRec[3]])
            shapefile_original.coordstimes.append(SecondsOfWeek2StandardTime(CurrentRec[0],SurveyDate))
            
            TrajPosValues=(SecondsOfWeek2StandardTime(CurrentRec[0],SurveyDate),easting,northing,CurrentRec[3],Rad2Deg(CurrentRec[9]-CurrentRec[10])-Rad2Deg(HeadingConvergenceCorrection(latitude, longitude,UTM_Zone)),Rad2Deg(CurrentRec[7]),Rad2Deg(CurrentRec[8]),0,0,0,0,0,0)
            TrajPosPacked_data=TrajPos.pack(*TrajPosValues)
            f.write(TrajPosPacked_data)
            
        f.close
        
        w = shapefile_original.Writer(shapefile_original.POLYLINEZ)
        w.autoBalance = 1
        w.field('FLIGHT','N',12,0)
        w.field('PSID','N',5,0)
        w.field('MIN_GPS','N',24,3)
        w.field('MAX_GPS','N',24,3)
        w.field('MIN_TIME','C',40)
        w.field('MAX_TIME','C',40)
        w.field('UTC_OFFSET','N',4,2)
        
        #create line shapefile
        w.line(parts=[shapefile_original.coords[0::everynth*2]])
        w.record(FLIGHT=flight,PSID=psid,MIN_GPS=(LasStartTime_st),MAX_GPS=(LasEndTime_st),MIN_TIME=StandardTime2LocalTime(LasStartTime_st,utctimeoffset).strftime("%d/%m/%Y %H:%M:%S"),MAX_TIME=StandardTime2LocalTime(LasEndTime_st,utctimeoffset).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset)
        
        w.save(trajout.replace('.trj','_lines'))
        
        wp = shapefile_original.Writer(shapefile_original.POINTZ)
        wp.autoBalance = 1
        wp.field('FLIGHT','N',12,0)
        wp.field('PSID','N',5,0)
        wp.field('GPS','N',24,3)
        wp.field('TIME','C',40)
        wp.field('UTC_OFFSET','N',4,2)
        shapefile_original.coords=shapefile_original.coords[0::everynth*20]
        shapefile_original.coordstimes=shapefile_original.coordstimes[0::everynth*20]
        
        for i,point in enumerate(shapefile_original.coords):
            wp.point(point[0],point[1],point[2])
            wp.record(FLIGHT=flight,PSID=psid,GPS=(shapefile_original.coordstimes[i]),TIME=StandardTime2LocalTime(shapefile_original.coordstimes[i],utctimeoffset).strftime("%d/%m/%Y %H:%M:%S"),UTC_OFFSET=utctimeoffset)
            
        wp.save(trajout.replace('.trj','_points'))
        
    print("completed ok.")
    
if __name__ == "__main__":
    main(sys.argv[1:])
