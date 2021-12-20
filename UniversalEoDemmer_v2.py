# Universal EO Demmer
# TOPPIT REQUIREMENTS
# Mandatory global values
inpho_folder = "C:\\atlass\\bin\\Inpho8"   # See email about this folder
harrier_calib_ini = "H68_038-009"       # See email about this file
# Should probably add support for multiple ini input there, but H68 is unlikely to move.
# INPHO/TOPPIT DESTINATION CODES - MGA
# See Inpho projection table for how to manipulate or add to the below
sbet_projections = []
sbet_proj_dictionary = {'Ellipsoidal': 0,
                        'MGA/GDA Zone 47': 36,
                        'MGA/GDA Zone 48': 37,
                        'MGA/GDA Zone 49': 38,
                        'MGA/GDA Zone 50': 39,
                        'MGA/GDA Zone 51': 40,
                        'MGA/GDA Zone 52': 41,
                        'MGA/GDA Zone 53': 42,
                        'MGA/GDA Zone 54': 43,
                        'MGA/GDA Zone 55': 44,
                        'MGA/GDA Zone 56': 45,
                        'MGA/GDA Zone 57': 46,
                        'MGA/GDA Zone 58': 47
                        }
for k in sbet_proj_dictionary.keys():
    sbet_projections.append(k)
seconds_in_day = 86400

# Imports
import os
import csv
try:
    from gooey import GooeyParser, Gooey
except ImportError:
    print('About to try installing Gooey. Please rerun the script afterwards.')
    os.system('start /wait cmd /k pip install gooey')
    from gooey import Gooey, GooeyParser
from datetime import datetime
import subprocess
from decimal import Decimal
import pandas as pd

# Global Mapper projections
gm_projection_dict = {'Ellipsoidal': 4326,
                      'MGA/GDA Zone 47': 28347,
                      'MGA/GDA Zone 48': 28348,
                      'MGA/GDA Zone 49': 28349,
                      'MGA/GDA Zone 50': 28350,
                      'MGA/GDA Zone 51': 28351,
                      'MGA/GDA Zone 52': 28352,
                      'MGA/GDA Zone 53': 28353,
                      'MGA/GDA Zone 54': 28354,
                      'MGA/GDA Zone 55': 28355,
                      'MGA/GDA Zone 56': 28356,
                      'MGA/GDA Zone 57': 28357,
                      'MGA/GDA Zone 58': 28358}


# Class Main Arg Handler - works out params etc
class main_arg_handler:
    def __init__(self):
        noot = goo()
        if 'global' and 'exe' not in noot.gm_exe:
            print("Error: that doesn't look like a Global Mapper exe...")
            exit()
        elif 'VQ_Prepper' in noot.command:
            print("VQ780i selected...")
            vq_system_run(noot)
        elif 'Harrier_Prepper' in noot.command:
            print("Harrier system selected...")
            harrier_system_run(noot)
        elif 'U' in noot.command:
            print("Ultracam detected...")
            ucep_run(noot)
        else:
            print("Sorry, system not recognised somehow. Please try again or report issue to IT")
        print('Complete!')


# Class VQ780i - runs old EIF to DEM workflow, with new adjustments in place
class vq_system_run:
    def __init__(self, noot):
        # paths, stripping noot
        self.eif_folder = noot.eif_folder
        self.gm_exe = noot.gm_exe
        self.first_time = None
        self.camera = noot.camera
        self.lat_long_id_secs = os.path.join(self.eif_folder, "demming.csv")
        self.lat_long_id_secs_height = os.path.join(self.eif_folder, "demming_with_h_temp.csv")
        self.cleaned_output = os.path.join(self.eif_folder, "cleaned_output.txt")
        # values
        self.sbet_proj = 'Ellipsoidal'
        self.epsg_code = gm_projection_dict[self.sbet_proj]
        self.demmed_dic = {}
        self.times_list = []
        self.sow_times_list = []
        # processes
        self.gms_script = os.path.join(self.eif_folder, "demming_script.gms")
        self.eif_filterer(self.eif_folder)
        self.gms_make()
        self.run_gms()
        self.gm_output_cleaner(self.lat_long_id_secs_height, self.cleaned_output)
        print("All done!")

    def eif_checker(self, eif_list):
        for e in eif_list:
            eif_path = (os.path.join(self.eif_folder, e)).replace("\\", "\\\\")
            reader = open(eif_path, 'r')
            b_name = os.path.basename(e)
            with reader as fr:
                line = fr.readlines()
                for n, entry in enumerate(line):
                    if n < 3:
                        if '#' not in entry[0]:
                            print("File " + str(b_name) + " looks invalid. Removing.")
                            eif_list.remove(e)
                    if n >= 4:
                        if not entry[0].isdigit():
                            print(entry[0], n)
                            print("You may wish to verify entries in file " + str(b_name) +
                                  " - I picked up something odd. Note there may be nothing wrong.")
                fr.close()
        if not len(eif_list):
            print("Uh oh! No valid EIF here!")
            exit()

    def eif_filterer(self, eif_folder):
        # get eif paths
        eif_list = []
        frame_entries_time_unfixed = {}
        frame_entries_fixed = {}
        for file in os.listdir(eif_folder):
            file_cased = file.lower()
            if file_cased.endswith(".eif"):
                eif_list.append(file)
        eif_list.sort()
        dof_from_bname = ((eif_list[0]).split('_'))[0]
        self.first_time = ((eif_list[0]).split('_'))[1]
        print(dof_from_bname)
        # loop through eif list
        print("Checking eifs...")
        self.eif_checker(eif_list)
        print("Filtering eifs...")
        for e in eif_list:
            eif_path = (os.path.join(eif_folder, e)).replace("\\", "\\\\")
            reader = open(eif_path, 'r')
            with reader as fr:
                line = fr.readlines()
                for l in line:
                    if l[0].isdigit():
                        ref_line = l.split(";")
                        # get the raw time - it is in seconds of day here
                        time_of_day = ref_line[0]
                        # get frame path
                        frame_path = ref_line[1]
                        # get name of frame from the path
                        frame_name = (os.path.basename(frame_path)).strip('.iiq"')
                        # get lat and long
                        lat, long = ref_line[9], ref_line[10]
                        frame_information = (frame_name, lat, long)
                        frame_entries_time_unfixed[time_of_day] = frame_information
                        self.times_list.append(time_of_day)
                fr.close()
        # time correction
        print("Correcting times...")
        # first up, find earliest time
        self.times_list.sort()
        earliest = self.times_list[0]
        # find which frame that refers to, and extract date and day of start of flight
        # gps_day_of_flight = frame_entries_time_unfixed[earliest]
        # date_of_flight = ((gps_day_of_flight[0]).split("_"))[0]
        print("Date of Flight set to: ", dof_from_bname)
        day_of_flight = datetime.strptime(dof_from_bname, '%y%m%d')
        # calculate conversion value
        day_before = day_of_flight.isoweekday()
        print("day_before is: ", day_before)
        # there is a more intelligent way to do the following but I will deal with it later
        if day_before == 7:
            print("Possible week overrun detected...")
            seconds_already = day_before * seconds_in_day - 604800
        else:
            seconds_already = day_before * seconds_in_day
        # correct times in dictionary to reflect seconds of week
        for tk in frame_entries_time_unfixed.keys():
            # if frame name starts with next day, add 604800
            get_frame_time_bit_1 = frame_entries_time_unfixed[tk]
            frame_time = ((get_frame_time_bit_1[0]).split('_'))[1]
            if day_before == 7 and (str(frame_time)).startswith('0'):
                sow_time = Decimal(tk) + Decimal(seconds_already)
            else:
                if (str(frame_time)).startswith('0'):
                    # needs line here to check if first one doesn't start with 0
                    if str(self.first_time).startswith('0'):
                        # if first line ever starts with 0:
                        if 'MM010014' or 'YC030228' in self.camera:
                            seconds_already_ent = seconds_already  # + seconds_in_day
                        else:
                            seconds_already_ent = seconds_already
                    else:
                        # seconds_already_ent = seconds_already + seconds_in_day
                        seconds_already_ent = seconds_already + seconds_in_day
                else:
                    seconds_already_ent = seconds_already
                sow_time = Decimal(tk) + Decimal(seconds_already_ent)
            self.sow_times_list.append(sow_time)
            frame_entries_fixed[sow_time] = frame_entries_time_unfixed[tk]
        # write that result to a CSV for the GMS script to read
        print("Writing temp file for Global Mapper...")
        with open(self.lat_long_id_secs, 'w', newline='') as f:
            writer = csv.writer(f)
            for ctime in frame_entries_fixed.keys():
                frame, lat, long = frame_entries_fixed[ctime]
                llis_line = lat, long, str(frame), str(ctime)
                writer.writerow(llis_line)
        f.close()
        # now on to gms running!

    def gms_make(self):
        llis = self.lat_long_id_secs
        script = self.gms_script
        llish = self.lat_long_id_secs_height
        print("Constructing Global Mapper script...")
        def_proj_text = 'DEFINE_PROJ PROJ_NAME="GEO_WGS84"\n' \
                        'Projection     GEOGRAPHIC\n' \
                        'Datum          WGS84\n' \
                        'Zunits         NO\n' \
                        'Units          DD\n' \
                        'Xshift         0.000000\n' \
                        'Yshift         0.000000\n' \
                        'Parameters\n' \
                        '0 0 0.00000 /* longitude of center of projection\n' \
                        'END_DEFINE_PROJ\n'
        contents_of_gms_header = "GLOBAL_MAPPER_SCRIPT VERSION=1.00 ENABLE_PROGRESS=YES LOG_TO_COMMAND_PROMPT=YES " \
                                 "SHOW_WARNINGS=YES \n"
        import_statement = 'IMPORT_ASCII FILENAME="%s" TYPE=POINT_ONLY COORD_ORDER=Y_FIRST INC_COORD_LINE_ATTRS=YES ' \
                           'INC_ELEV_COORDS=NO PROJ_NAME="GEO_WGS84"\n' % llis.replace('/', '\\')
        osm_statement = 'IMPORT_OSM_TILE OSM_BASE_URL="http://data.bluemarblegeo.com/datasets/ASTER_GDEM_V2_TILES/" ' \
                        'OSM_DESC="ASTER GDEM v2 Worldwide Elevation Data (1 arc-second Resolution)" ' \
                        'OSM_FILE_EXT="gmg" OSM_NUM_ZOOM_LEVELS="12" TILE_SIZE="512" LAYER_BOUNDS=%s ' \
                        'LAYER_BOUNDS_EXPAND="5" LABEL_FIELD_FORCE_OVERWRITE="NO" SAMPLING_METHOD="BICUBIC" ' \
                        'CLIP_COLLAR="NONE" ELEV_UNITS="METERS"\n' % llis.replace('/', '\\')
        # apply_elev_statement = "EDIT_VECTOR FILENAME='%s' APPLY_ELEVS=YES REPLACE_EXISTING=YES" % llis
        export_statement = 'EXPORT_VECTOR EXPORT_LAYER="%s" FILENAME="%s" TYPE=CSV OVERWRITE_EXISTING=YES ' \
                           'COORD_DELIM=COMMA COORD_ORDER=X_FIRST PRECISION=9 EXPORT_ELEV=YES EXPORT_ATTRS=YES\n' \
                           % (llis.replace('/', '\\'), llish.replace('/', '\\'))
        with open(script, 'w') as g:
            gms_string = contents_of_gms_header + def_proj_text + import_statement + osm_statement + export_statement
            g.write(gms_string)
            g.close()

    def run_gms(self):
        print("Running Global Mapper script...")
        # Just runs GMS script
        subprocess.call([self.gm_exe, self.gms_script])

    def gm_output_cleaner(self, llish, output):
        # Cleans output of GMS for insertion into Pospac (i.e. converts to 'SoW ID Height')
        print("Cleaning Global Mapper output...")
        if os.path.exists(output):
            os.remove(output)
        # NOTE: need to resort the times out
        # get all data into a dic (again):
        test = []
        for a in self.sow_times_list:
            test.append(a)
        test.sort()
        time_h_dic = {}
        # it didn't like sorting the original for whatever reason...
        with open(llish, 'r') as g_file:
            g_reader = g_file.readlines()
            for n, g_line in enumerate(g_reader):
                if n > 0:
                    gls = g_line.split(',')
                    t, id, h = (gls[4]).rstrip('\r\n'), gls[3], gls[2]
                    time_h_dic[t] = (id, h)
            g_file.close()
        with open(output, 'w') as o_file:
            for time in test:
                p_id, dheight = time_h_dic[str(time)]
                new_line = str(time) + " " + p_id + " " + str(dheight) + "\n"
                o_file.write(new_line)
            o_file.close()


# Class Harrier - uses TopPit EO gen system
class harrier_system_run:
    def __init__(self, noot):
        # paths, stripping noot
        self.tac_files = noot.tac_files
        self.sbet_files = noot.sbet_files
        self.sbet_zone = noot.sbet_zone
        self.gms_exe = noot.gm_exe
        # translating zone into TopPit-speak
        self.destination = sbet_proj_dictionary[self.sbet_zone]
        # running
        self.handle_harrier_input(self.tac_files)

    def handle_harrier_input(self, tac_files):
        # there will always be one sbet, but there could be multiple tac.
        # If there is more than one tac, we will need to merge them sensibly (in the right order).
        # Test tac count:
        tac_list = tac_files.split(';')
        if len(tac_list) > 1:
            print(str(len(tac_list)) + " TAC detected...")
            self.tac_merger(tac_list)
        else:
            print("Single tac detected...")
            self.eo_bat_make(tac_list[0], self.sbet_files, self.destination)

    def tac_merger(self, tac_list):
        print("Merging tac files sensibly...")
        working_dir = os.path.dirname(tac_list[0])
        merged_tac = os.path.join(working_dir, "merged_tac.txt")
        tac_dic = {}
        tac_t_list = []
        # Get first entry of each tac
        for t in tac_list:
            with open(t, 'r') as tac_r:
                first_line = tac_r.readline()
                get_first_time = first_line.split("	")
                tac_t_list.append(Decimal(get_first_time[0]))
                tac_dic[Decimal(get_first_time[0])] = t
                tac_r.close()
        # If the tacs aren't merged chronologically, PosPac won't handle them correctly.
        tac_t_list.sort()
        # Let's merge!
        with open(merged_tac, 'a') as merging_file:
            for tac in tac_t_list:
                with open(tac_dic[tac], 'r') as current_tac:
                    current_read = current_tac.readlines()
                    for line in current_read:
                        merging_file.write(line)
                    current_tac.close()
            merging_file.close()
        self.eo_bat_make(merged_tac, self.sbet_files, self.destination)

    def eo_bat_make(self, tac_input, sbet, destination):
        print("Constructing bat file for eogen...")
        # Time to construct the bat as a string.
        # Make the necessary paths:
        working_dir = os.path.dirname(tac_input)  # I know we have defined this before, but it got messy...
        out_eo = os.path.join(working_dir, "working_file_for_gms")
        working_bat = os.path.join(working_dir, "running_eogen.bat")
        # Make the strings:
        setter_toppath = "set TOP_HOME=%s" % inpho_folder
        setter_eo_line = '%s/bin/eopro.exe "[dest %s geoid 3 system *%s* event **]" %s, %s - %s' \
                         % (inpho_folder, destination, harrier_calib_ini, tac_input, sbet, out_eo)
        fixed_sel = setter_eo_line.replace('/', '\\')
        # Write the bat:
        with open(working_bat, 'a') as bat:
            bat_string = setter_toppath + "\n" + fixed_sel
            bat.write(bat_string)
            bat.close()
        # Run the bat
        print("Running the eogen bat...")
        subprocess.run(working_bat)
        self.prep_for_gm(out_eo, working_dir)

    def prep_for_gm(self, raw_eo, working_dir):
        print("Making Global Mapper script...")
        # define some paths to files...
        gms_file = os.path.join(working_dir, "demming.gms")
        out_csv = os.path.join(working_dir, "demming_with_h_temp.csv")
        output = os.path.join(working_dir, "cleaned_output.txt")
        def_proj_text = 'DEFINE_PROJ PROJ_NAME="GEO_WGS84"\n' \
                        'Projection     GEOGRAPHIC\n' \
                        'Datum          WGS84\n' \
                        'Zunits         NO\n' \
                        'Units          DD\n' \
                        'Xshift         0.000000\n' \
                        'Yshift         0.000000\n' \
                        'Parameters\n' \
                        '0 0 0.00000 /* longitude of center of projection\n' \
                        'END_DEFINE_PROJ\n'
        contents_of_gms_header = "GLOBAL_MAPPER_SCRIPT VERSION=1.00 ENABLE_PROGRESS=YES LOG_TO_COMMAND_PROMPT=YES " \
                                 "SHOW_WARNINGS=YES \n"
        # note x first for harrier input! Plus different skip values...
        import_statement = 'IMPORT_ASCII FILENAME="%s.txt" TYPE=POINT_ONLY COORD_ORDER=X_FIRST ' \
                           'INC_COORD_LINE_ATTRS=YES INC_ELEV_COORDS=NO PROJ_NAME="GEO_WGS84" ' \
                           'SKIP_COLUMNS=3 SKIP_ROWS=17\n' % raw_eo.replace('/', '\\')
        osm_statement = 'IMPORT_OSM_TILE OSM_BASE_URL="http://data.bluemarblegeo.com/datasets/ASTER_GDEM_V2_TILES/" ' \
                        'OSM_DESC="ASTER GDEM v2 Worldwide Elevation Data (1 arc-second Resolution)" ' \
                        'OSM_FILE_EXT="gmg" OSM_NUM_ZOOM_LEVELS="12" TILE_SIZE="512" LAYER_BOUNDS=%s.txt ' \
                        'LAYER_BOUNDS_EXPAND="5" LABEL_FIELD_FORCE_OVERWRITE="NO" SAMPLING_METHOD="BICUBIC" ' \
                        'CLIP_COLLAR="NONE" ELEV_UNITS="METERS"\n' % raw_eo.replace('/', '\\')
        # apply_elev_statement = "EDIT_VECTOR FILENAME='%s' APPLY_ELEVS=YES REPLACE_EXISTING=YES" % llis
        export_statement = 'EXPORT_VECTOR EXPORT_LAYER="%s.txt" FILENAME="%s" TYPE=CSV OVERWRITE_EXISTING=YES ' \
                           'COORD_DELIM=COMMA COORD_ORDER=X_FIRST PRECISION=9 EXPORT_ELEV=YES EXPORT_ATTRS=YES\n' \
                           % (raw_eo.replace('/', '\\'), out_csv.replace('/', '\\'))
        with open(gms_file, 'w') as g:
            gms_string = contents_of_gms_header + def_proj_text + import_statement + osm_statement + export_statement
            g.write(gms_string)
            g.close()
        self.run_gms(gms_file, self.gms_exe)
        self.gm_output_cleaner(out_csv, output)

    def run_gms(self, gms_script, gms_location):
        print("Running Global Mapper script...")
        # Just runs GMS script
        subprocess.call([gms_location, gms_script])

    def gm_output_cleaner(self, llish, output):
        # Cleans output of GMS for insertion into Pospac (i.e. converts to 'SoW ID Height')
        print("Cleaning Global Mapper output...")
        with open(llish, 'r') as g_file:
            with open(output, 'w') as o_file:
                g_reader = g_file.readlines()
                for n, g_line in enumerate(g_reader):
                    if n > 0:
                        gls = g_line.split(',')
                        t, id, h = Decimal((gls[5]).rstrip('\r\n')), gls[3], gls[2]
                        clean_line = str(t) + " " + id + " " + h + "\n"
                        o_file.write(clean_line)
            o_file.close()
        g_file.close()
        print("All done!")


class ucep_run:
    def __init__(self, noot):
        self.cos_log = noot.cos_log
        self.ead_folder = noot.ead_folder
        self.gm_exe = noot.gm_exe

        self.cos_string = (os.path.basename(self.cos_log)).replace('COS', '')

        self.cos_dir = os.path.dirname(self.cos_log)
        self.frame_list = [int(a.split('-')[1]) for a in os.listdir(self.ead_folder) if a.endswith('.xml')]
        if len(self.frame_list) == 0:
            print('No EAD files detected...')
            exit()
        self.ll_dic = {}
        self.times_dic = {}

        self.times_panda = self.extract_values()
        self.gm_input = os.path.join(self.cos_dir, 'lat_long_id_secs.csv')
        self.gm_output = os.path.join(self.cos_dir, 'lat_long_height_sec_id.csv')
        self.gm_script = os.path.join(self.cos_dir, 'run_dem_heights.gms')
        for file in [self.gm_input, self.gm_output, self.gm_script]:
            if os.path.isfile(file):
                os.remove(file)
        self.times_panda.to_csv(self.gm_input, index=False, header=False)
        self.gms_make()
        self.run_gms()
        self.heighted_panda = self.gm_output_cleaner()
        self.tac_name_str = 'tac_id_file_%s.txt' % self.cos_string
        self.final_output = os.path.join(self.cos_dir, self.tac_name_str)
        self.heighted_panda.to_csv(self.final_output, sep=' ', index=False, header=False)

    def extract_values(self):
        with open(self.cos_log, 'r') as log_r:
            lines = log_r.readlines()
            for i, line in enumerate(lines):
                if 'Timestamp [s]' in line:
                    if 'PosData Event' in lines[i - 2]:
                        image_number = str(lines[i - 4].split(' ............... ')[-1].strip('\n\r'))
                        timestamp = line.split('............ ')[-1].strip('\n\r')
                        self.times_dic[i] = [timestamp, image_number]
                elif 'Latitude ................' in line:
                    lat = '-' + line.split(' ................ ')[-1].strip('\n\rS').replace('[WGS84]', '').replace(' ',
                                                                                                                   '')
                    long = lines[i + 1].split(' ............... ')[-1].strip('\n\rE').replace('[WGS84]', '').replace(
                        ' ', '')
                    frame = str(lines[i - 9].split(' ......... ')[-1].strip('\n\r'))
                    self.ll_dic[frame] = [lat, long]
        for key in self.times_dic.keys():
            for frame in self.ll_dic.keys():
                if frame in self.times_dic[key]:
                    self.times_dic[key] = self.ll_dic[frame] + self.times_dic[key]
        times_panda = pd.DataFrame.from_dict(self.times_dic, dtype='str', orient='index')
        return times_panda

    def gms_make(self):
        llis = self.gm_input
        script = self.gm_script
        llish = self.gm_output
        print("Constructing Global Mapper script...")
        def_proj_text = 'DEFINE_PROJ PROJ_NAME="GEO_WGS84"\n' \
                        'Projection     GEOGRAPHIC\n' \
                        'Datum          WGS84\n' \
                        'Zunits         NO\n' \
                        'Units          DD\n' \
                        'Xshift         0.000000\n' \
                        'Yshift         0.000000\n' \
                        'Parameters\n' \
                        '0 0 0.00000 /* longitude of center of projection\n' \
                        'END_DEFINE_PROJ\n'
        contents_of_gms_header = "GLOBAL_MAPPER_SCRIPT VERSION=1.00 ENABLE_PROGRESS=YES LOG_TO_COMMAND_PROMPT=YES " \
                                 "SHOW_WARNINGS=YES \n"
        import_statement = 'IMPORT_ASCII FILENAME="%s" TYPE=POINT_ONLY COORD_ORDER=Y_FIRST INC_COORD_LINE_ATTRS=YES ' \
                           'INC_ELEV_COORDS=NO PROJ_NAME="GEO_WGS84"\n' % llis.replace('/', '\\')
        osm_statement = 'IMPORT_OSM_TILE OSM_BASE_URL="http://data.bluemarblegeo.com/datasets/ASTER_GDEM_V2_TILES/" ' \
                        'OSM_DESC="ASTER GDEM v2 Worldwide Elevation Data (1 arc-second Resolution)" ' \
                        'OSM_FILE_EXT="gmg" OSM_NUM_ZOOM_LEVELS="12" TILE_SIZE="512" LAYER_BOUNDS=%s ' \
                        'LAYER_BOUNDS_EXPAND="5" LABEL_FIELD_FORCE_OVERWRITE="NO" SAMPLING_METHOD="BICUBIC" ' \
                        'CLIP_COLLAR="NONE" ELEV_UNITS="METERS"\n' % llis.replace('/', '\\')
        # apply_elev_statement = "EDIT_VECTOR FILENAME='%s' APPLY_ELEVS=YES REPLACE_EXISTING=YES" % llis
        export_statement = 'EXPORT_VECTOR EXPORT_LAYER="%s" FILENAME="%s" TYPE=CSV OVERWRITE_EXISTING=YES ' \
                           'COORD_DELIM=COMMA COORD_ORDER=X_FIRST PRECISION=9 EXPORT_ELEV=YES EXPORT_ATTRS=YES\n' \
                           % (llis.replace('/', '\\'), llish.replace('/', '\\'))
        with open(script, 'w') as g:
            gms_string = contents_of_gms_header + def_proj_text + import_statement + osm_statement + export_statement
            g.write(gms_string)
            g.close()

    def run_gms(self):
        print("Running Global Mapper script...")
        # Just runs GMS script
        subprocess.call([self.gm_exe, self.gm_script])

    def gm_output_cleaner(self):
        # Cleans output of GMS for insertion into Pospac (i.e. converts to 'SoW ID Height')
        print("Cleaning Global Mapper output...")
        # NOTE: need to resort the times out
        # get all data into a pd (again):
        temp_pd = pd.read_csv(self.gm_output, skip_blank_lines=True, skipinitialspace=True, dtype={'ATTR_2': 'str'})
        temp_pd.rename(columns={'ATTR_1': 'time', 'ATTR_2': 'frame'}, inplace=True)
        temp_pd.sort_values(by=['time'], inplace=True)
        temp_pd.drop(['LATITUDE', 'LONGITUDE'], axis=1)
        temp_pd_reordered = temp_pd[['time', 'frame', 'ELEV']]
        return temp_pd_reordered

# GUI
@Gooey(program_name="Universal Eo Prepper", use_legacy_titles=True, required_cols=1, default_size=(750, 500))
def goo():
    # For all systems, output will be EIF or TAC folder
    parser = GooeyParser(description="Universal EO Prepper")
    sub_pars = parser.add_subparsers(help='commands', dest='command')
    vq_parser = sub_pars.add_parser('VQ_Prepper', help='Run EO preparation on VQ780i systems')
    # VQ needs EIF folder, Global Mapper exe
    vq_parser.add_argument('eif_folder', metavar="EIF Folder", widget='DirChooser',
                           help='Select folder containing EIF files')
    vq_parser.add_argument('gm_exe', metavar='Global Mapper Location', widget='FileChooser',
                           help='Select your Global Mapper exe',
                           default=r"C:\Program Files\GlobalMapper21.0_64bit\global_mapper.exe")
    vq_parser.add_argument('camera', metavar="Which camera captured this? This has an impact on the calculations.",
                           choices=['MM010014', 'YC030345', 'YC030228', 'H68-IQ185'])
    harrier_parser = sub_pars.add_parser('Harrier_Prepper', help='Run EO preparation on VQ780i systems')
    # Harrier needs TAC_merged, sbet, zone , hardcoded calib_ini folder, gm exe location
    harrier_parser.add_argument('tac_files', metavar="Select your TAC files", widget='MultiFileChooser',
                                help="You can select more than one.")
    harrier_parser.add_argument('sbet_files', metavar="Select your sbet files", widget='FileChooser',
                                help="Just one this time.")
    harrier_parser.add_argument('sbet_zone', metavar="In what configuration is your sbet?", choices=sbet_projections,
                                help="Select the native projection of your input sbet file")
    harrier_parser.add_argument('gm_exe', metavar='Global Mapper Location', widget='FileChooser',
                                help='Select your Global Mapper exe',
                                default=r"C:\Program Files\GlobalMapper21.0_64bit\global_mapper.exe")
    uce_parser = sub_pars.add_parser('UCE_Prepper', help='Create ID file for the UCX')
    uce_parser.add_argument('cos_log', metavar='Please show me your COS log. \nYour output will also be placed here.',
                            widget='FileChooser')
    uce_parser.add_argument('ead_folder', metavar='Please show me your EAD_MM folder.', widget='DirChooser')
    uce_parser.add_argument('gm_exe', metavar='Please show me your Global Mapper exe', widget='FileChooser',
                            default=r"C:\Program Files\GlobalMapper21.1_64bit\global_mapper.exe")
    return parser.parse_args()


main_arg_handler()
