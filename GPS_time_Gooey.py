from datetime import datetime, timedelta
import math
import os
import sys
from gooey import Gooey, GooeyParser
import pandas as pd
import xlsxwriter
import subprocess
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *


@Gooey(program_name="GPS Time converter", advanced=True, default_size=(800,600), use_legacy_titles=True, required_cols=2, optional_cols=2,advance=True, navigation='TABBED',)
def param_parser():

    parser=GooeyParser(description="GPS Time converter")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    step0_parser = sub_pars.add_parser('Calculate_LocalTime_Folder')
    step0_parser.add_argument("inputfolder",widget="DirChooser", metavar="Folder with LAS/LAZ files")
    step0_parser.add_argument("filetype", metavar="File Type LAS/LAZ ", default = "laz")
    step0_parser.add_argument("utctimeoffset_hrs",metavar="UTC time offset (hrs)", default=10.0)
    step4_parser = sub_pars.add_parser('Calculate_LocalTime_Folder_multiple_AOI')
    step4_parser.add_argument("inputfolder",widget="DirChooser", metavar="Folder with LAS/LAZ files")
    step4_parser.add_argument("filetype", metavar="File Type LAS/LAZ ", default = "laz")
    step4_parser.add_argument("utctimeoffset_hrs",metavar="UTC time offset (hrs)", default=10.0)
    step1_parser = sub_pars.add_parser('Calculate_LocalTime')
    step1_parser.add_argument("gpsstandardtime", metavar="GPS adjusted standard time")
    step1_parser.add_argument("utctimeoffset_hrs",metavar="UTC time offset (hrs)",default=10.0)
    step2_parser = sub_pars.add_parser('Seconds_Of_the_Week')
    step2_parser.add_argument("secondsofweek", metavar="GPS seconds of the week time")
    step2_parser.add_argument("utctimeoffset_hrs",metavar="UTC time offset (hrs)")
    step2_parser.add_argument("gpsweek",metavar="GPS Week")
    step3_parser = sub_pars.add_parser('Show_UTC_Time_Now')
    step3_parser.add_argument("utctimeoffset_hrs",metavar="UTC time offset (hrs)")
    args = parser.parse_args()

    return(args)

def StandardTime2LocalTime(gpstime, utctimeoffset_hrs):
    GPSOrigin= datetime.datetime(1980, 1, 6,0,0,0)
    gpstime_days_part=math.floor(gpstime/60/60/24)
    gpstime_seconds_part=gpstime-(math.floor(gpstime/60/60/24)*60*60*24)
    
    return GPSOrigin+timedelta(11574,6399)+timedelta(0,utctimeoffset_hrs*60*60)+timedelta(gpstime_days_part,gpstime_seconds_part)
    
def SecondsOfWeek2StandardTime(secondsofweek,surveydate):
    date_format = "%d/%m/%Y"
    a = datetime.datetime.strptime('06/01/1980', date_format)
    b = datetime.datetime.strptime(surveydate, date_format)
    return secondsofweek+math.floor((b - a).days/7)*604800-1000000000

def SecondsOfWeek2StandardTimeGPSWeek(secondsofweek,gpsweek):
    date_format = "%d/%m/%Y"
    a = datetime.datetime.strptime('06/01/1980', date_format)
    b = a+timedelta(days=gpsweek*7)
    return secondsofweek+math.floor((b - a).days/7)*604800-1000000000
    
def StandardTime2SecondsOfWeek(standardtime):
    return standardtime-(math.floor((standardtime+1000000000)/604800)*604800-1000000000)    

def GPSWeekFromDate(surveydate):
    date_format = "%d/%m/%Y"
    a = datetime.datetime.strptime('06/01/1980', date_format)
    b = datetime.datetime.strptime(surveydate, date_format)
    return math.floor((b-a).days/7)

def LocalTime2StandardTime(localtime):
    GPSOrigin= datetime.datetime(1980, 1, 6,0,0,0)
    deltatime = (localtime - GPSOrigin)
    return  float(deltatime.days*24*60*60 + deltatime.seconds -1000000000)

def main():

    #Set Arguments
    args = param_parser()

    if args.command=="Calculate_LocalTime_Folder":

        inputfolder = args.inputfolder
        filetype = args.filetype
        #lasinfofile = AtlassGen.makedir(os.path.join)

        
       

        data = {}


        print("Running Lasinfo merged .......")
        inputf = os.path.join(inputfolder, '*.{0}'.format(filetype))
        subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', inputf, '-merged']
        subprocessargs=list(map(str,subprocessargs))    
        proc = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

        print("Lasinfo merge completed")
        output = proc.stdout
        output = output.split('\n')
        #print(output)
        attrib = '  gps_time '

        for line in output:
            if attrib in line:
                line=line.replace(attrib ,'')
                line=line.split(' ')
                gpsstandardtime_Start=line[0]
                gpsstandardtime_End=line[1]

        utctimeoffset_hrs=float(args.utctimeoffset_hrs)
        print('\tUTC time offset (hrs): {0}'.format(utctimeoffset_hrs))

    
        gpsstandardtime_Start=float(gpsstandardtime_Start)
        print('\tGPS adjusted standard START time: {0}'.format(gpsstandardtime_Start))

        secondsofweek=StandardTime2SecondsOfWeek(gpsstandardtime_Start)
        localtime=StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")  
        flying_date_start = StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%d/%m/%Y")
        flying_time_start = StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%H:%M")
        gpsweek=GPSWeekFromDate(StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%d/%m/%Y"))
        path=os.path.dirname(inputfolder)
        areaname = os.path.basename(path)
        print('\n--------------------------------------------------------------------------------------')
        print('\n{0}'.format(areaname))
        print('\n--------------------------------------------------------------------------------------')
        print('\n-------------------------------- START -----------------------------------------------')
        print('\t\tGPS standard time: {0}'.format(gpsstandardtime_Start))
        print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
        print('\t\tGPS week: {0}'.format(gpsweek))
        print('\t\tLocal time based on UTC offset {0}hrs: {1}'.format(utctimeoffset_hrs,localtime))
        print('-------------------------------------------------------------------------------------\n\n')

        gpsstandardtime_End=float(gpsstandardtime_End)
        print('\tGPS adjusted standard END time: {0}'.format(gpsstandardtime_End))

        secondsofweek=StandardTime2SecondsOfWeek(gpsstandardtime_End)
        localtime=StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")  
        gpsweek=GPSWeekFromDate(StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%d/%m/%Y"))
        flying_date_end = StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%d/%m/%Y")
        flying_time_end = StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%H:%M")



        print('\n-------------------------------- END -----------------------------------------------')
        print('\t\tGPS standard time: {0}'.format(gpsstandardtime_End))
        print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
        print('\t\tGPS week: {0}'.format(gpsweek))
        print('\t\tLocal time based on UTC offset {0}hrs: {1}'.format(utctimeoffset_hrs,localtime))
        print('-------------------------------------------------------------------------------------\n\n')
        
        if not flying_date_start == flying_date_end:
            flying_date_start = '{0} - {1}'.format(flying_date_start, flying_date_end)

        data[areaname] = {'Date of Flight' : flying_date_start, 'Time of Flight(GMT + {0})'.format(utctimeoffset_hrs): '{0} - {1}'.format(flying_time_start,flying_time_end)}

        
        outputfile = os.path.join(inputfolder,'GPStimes.xlsx')

  
        df = pd.DataFrame(data=data).T
        #df = df[['Area Name','Date of Flight']]
        # Convert the dataframe to an XlsxWriter Excel object.
        ##df.to_excel(outputfile)
        print(f'\nReport location : {outputfile}')
        
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(outputfile, engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        workbook.close()

    if args.command=="Calculate_LocalTime_Folder_multiple_AOI":

        inputfolder = args.inputfolder
        filetype = args.filetype
        #lasinfofile = AtlassGen.makedir(os.path.join)

        
        dirlist = AtlassGen.DIRLIST(inputfolder)
        #dirlist = list(os.walk(inputfolder))
        #print(dirlist)

        if len(dirlist) <= 1:
            dirlist = [inputfolder]
            print(dirlist)

        data = {}
        for folder in dirlist:

            print("Running Lasinfo merged .......")
            inputf = os.path.join(folder, '*.{0}'.format(filetype))
            subprocessargs=['C:/LAStools/bin/lasinfo.exe', '-i', inputf, '-merged']
            subprocessargs=list(map(str,subprocessargs))    
            proc = subprocess.run(subprocessargs,stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, check=True, universal_newlines=True)

            print("Lasinfo merge completed")
            output = proc.stdout
            output = output.split('\n')
            #print(output)
            attrib = '  gps_time '

            for line in output:
                if attrib in line:
                    line=line.replace(attrib ,'')
                    line=line.split(' ')
                    gpsstandardtime_Start=line[0]
                    gpsstandardtime_End=line[1]

            utctimeoffset_hrs=float(args.utctimeoffset_hrs)
            print('\tUTC time offset (hrs): {0}'.format(utctimeoffset_hrs))

        
            gpsstandardtime_Start=float(gpsstandardtime_Start)
            print('\tGPS adjusted standard START time: {0}'.format(gpsstandardtime_Start))

            secondsofweek=StandardTime2SecondsOfWeek(gpsstandardtime_Start)
            localtime=StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")  
            flying_date_start = StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%d/%m/%Y")
            flying_time_start = StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%H:%M")
            gpsweek=GPSWeekFromDate(StandardTime2LocalTime(gpsstandardtime_Start, utctimeoffset_hrs).strftime("%d/%m/%Y"))
            path=os.path.dirname(folder)
            areaname = os.path.basename(path)
            print('\n--------------------------------------------------------------------------------------')
            print('\n{0}'.format(areaname))
            print('\n--------------------------------------------------------------------------------------')
            print('\n-------------------------------- START -----------------------------------------------')
            print('\t\tGPS standard time: {0}'.format(gpsstandardtime_Start))
            print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
            print('\t\tGPS week: {0}'.format(gpsweek))
            print('\t\tLocal time based on UTC offset {0}hrs: {1}'.format(utctimeoffset_hrs,localtime))
            print('-------------------------------------------------------------------------------------\n\n')

            gpsstandardtime_End=float(gpsstandardtime_End)
            print('\tGPS adjusted standard END time: {0}'.format(gpsstandardtime_End))

            secondsofweek=StandardTime2SecondsOfWeek(gpsstandardtime_End)
            localtime=StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")  
            gpsweek=GPSWeekFromDate(StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%d/%m/%Y"))
            flying_date_end = StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%d/%m/%Y")
            flying_time_end = StandardTime2LocalTime(gpsstandardtime_End, utctimeoffset_hrs).strftime("%H:%M")



            print('\n-------------------------------- END -----------------------------------------------')
            print('\t\tGPS standard time: {0}'.format(gpsstandardtime_End))
            print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
            print('\t\tGPS week: {0}'.format(gpsweek))
            print('\t\tLocal time based on UTC offset {0}hrs: {1}'.format(utctimeoffset_hrs,localtime))
            print('-------------------------------------------------------------------------------------\n\n')
            
            if not flying_date_start == flying_date_end:
                flying_date_start = '{0} - {1}'.format(flying_date_start, flying_date_end)

            data[areaname] = {'Date of Flight' : flying_date_start, 'Time of Flight(GMT + {0})'.format(utctimeoffset_hrs): '{0} - {1}'.format(flying_time_start,flying_time_end)}

        
        outputfile = os.path.join(inputfolder,'GPStimes.xlsx')

        
        df = pd.DataFrame(data=data).T
        #df = df[['Area Name','Date of Flight']]
        # Convert the dataframe to an XlsxWriter Excel object.
        ##df.to_excel(outputfile)
        print(f'\nReport location : {outputfile}')
        
        # Create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(outputfile, engine='xlsxwriter')

        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        workbook.close()


    if args.command=="Calculate_LocalTime":

        gpsstandardtime=float(args.gpsstandardtime)
        print('\tGPS adjusted standard time: {0}'.format(gpsstandardtime))
        utctimeoffset_hrs=float(args.utctimeoffset_hrs)
        print('\tUTC time offset (hrs): {0}'.format(utctimeoffset_hrs))

        secondsofweek=StandardTime2SecondsOfWeek(gpsstandardtime)
        localtime=StandardTime2LocalTime(gpsstandardtime, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S")  
        gpsweek=GPSWeekFromDate(StandardTime2LocalTime(gpsstandardtime, utctimeoffset_hrs).strftime("%d/%m/%Y"))

        print('\n-------------------------------------------------------------------------------------')
        print('\t\tGPS standard time: {0}'.format(gpsstandardtime))
        print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
        print('\t\tGPS week: {0}'.format(gpsweek))
        print('\t\tLocal time based on UTC offset {0}hrs: {1}'.format(utctimeoffset_hrs,localtime))
        print('-------------------------------------------------------------------------------------\n\n')


    if args.command=="Seconds_Of_the_Week":

        secondsofweek=float(args.secondsofweek)
        print('\tGPS seconds of the week time: {0}'.format(secondsofweek))
        utctimeoffset_hrs=float(args.utctimeoffset_hrs)
        print('\tUTC time offset (hrs): {0}'.format(utctimeoffset_hrs))
        gpsweek = float(args.gpsweek)
        print('\tGPS week: {0}'.format(gpsweek))

         
        gpsstandardtime=SecondsOfWeek2StandardTimeGPSWeek(secondsofweek,gpsweek)
        localtime=StandardTime2LocalTime(gpsstandardtime, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S") 
        
        print('\n-------------------------------------------------------------------------------------')
        print('\t\tGPS standard time: {0}'.format(gpsstandardtime))
        print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
        print('\t\tGPS week: {0}'.format(gpsweek))
        print('\t\tLocal time based on UTC offset {0}hrs: {1}'.format(utctimeoffset_hrs,localtime))
        print('-------------------------------------------------------------------------------------\n\n')

    if args.command=="Show_UTC_Time_Now":

        utctimeoffset_hrs=float(args.utctimeoffset_hrs)
        print('\tUTC time offset (hrs): {0}'.format(utctimeoffset_hrs))

        timenow=datetime.datetime.now()-datetime.timedelta(0,utctimeoffset_hrs*60*60)
        gpsstandardtime=LocalTime2StandardTime(timenow)
        secondsofweek=StandardTime2SecondsOfWeek(gpsstandardtime)
        gpsweek=GPSWeekFromDate(StandardTime2LocalTime(gpsstandardtime, 0).strftime("%d/%m/%Y"))
        localtime=StandardTime2LocalTime(gpsstandardtime, utctimeoffset_hrs).strftime("%d/%m/%Y %H:%M:%S") 

        print('\n\tNote:')
        print('\t\tThe UTC time now is: {0}'.format(timenow.strftime("%d/%m/%Y %H:%M:%S")))
        print('\t\tGPS standard time: {0}'.format(gpsstandardtime))
        print('\t\tGPS seconds of week: {0}'.format(secondsofweek))
        print('\t\tGPS week: {0}'.format(gpsweek))
        print('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n')
     

    else:
        return
    
           




if __name__ == "__main__":
    main()         
