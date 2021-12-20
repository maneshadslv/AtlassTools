import os
import sys
import subprocess

# INPUT: Tilenum, xmin, ymin, xmax, ymax, image path, working_dir, zone, datum
# OUTPUT: Colourised LAZ

gm_exe = r"C:\Program Files\GlobalMapper21.0_64bit\global_mapper.exe"

r'''tile_num = '314000_5816500'
xmin = '314000'
xmax = '314500'
ymin = '5816500'
ymax = '5817000'
image_path = r"Y:\ECW_Testing\RGB\A6414_Melbourne_MetroMap_75mm_RGB_MGA94z55_09-Apr-2020.ecw"
working_dir = r"Y:\ECW_Testing\LAZ"
zone = 55
datum = 'GDA2020'''''

tile_num = sys.argv[1]
xmin = sys.argv[2]
xmax = sys.argv[3]
ymin = sys.argv[4]
ymax = sys.argv[5]
image_path = sys.argv[6]
working_dir = sys.argv[7]
zone = sys.argv[8]
datum = sys.argv[9]

# Step one: set file names.
print('Step one: set file names.')
working_laz = os.path.join(working_dir, "%s.laz" % tile_num)
output_folder = os.path.join(working_dir, 'colourised')
if not os.path.isdir(output_folder):
    os.mkdir(output_folder)
output_laz = os.path.join(output_folder, os.path.basename(working_laz))
gms_path = os.path.join(working_dir, "%s.gms" % tile_num)
tif_path = os.path.join(working_dir, "%s.tif" % tile_num)

# Step two: set projection text/name
print('Step two: set projection text/name')


def projection_definer():
    if 'AGD66' in datum:
        proj_name = "AMG_ZONE%s_AUSTRALIAN_GEODETIC_1966" % zone
        proj_text = 'DEFINE_PROJ PROJ_NAME="AMG_ZONE%s_AUSTRALIAN_GEODETIC_1966"\n' \
                    'Projection     AMG (Australian Map Grid)\n' \
                    'Datum          D_AUSTRALIAN_1966\n' \
                    'Zunits         NO\n' \
                    'Units          METERS\n' \
                    'Zone           %s\n' \
                    'Xshift         0.000000\n' \
                    'Yshift         0.000000\n' \
                    'Parameters\n' \
                    'END_DEFINE_PROJ' % (zone, zone)
    elif 'AGD84' in datum:
        proj_name = "AMG_ZONE%s_AUSTRALIAN_GEODETIC_1984" % zone
        proj_text = 'DEFINE_PROJ PROJ_NAME="AMG_ZONE%s_AUSTRALIAN_GEODETIC_1984"\n' \
                    'Projection     AMG (Australian Map Grid)\n' \
                    'Datum          D_AUSTRALIAN_1984\n' \
                    'Zunits         NO\n' \
                    'Units          METERS\n' \
                    'Zone           %s\n' \
                    'Xshift         0.000000\n' \
                    'Yshift         0.000000\n' \
                    'Parameters\n' \
                    'END_DEFINE_PROJ' % (zone, zone)
    elif 'GDA2020' in datum:
        proj_name = "MGA_ZONE%s_GDA_2020_AUSTRALIAN_GEODETIC_2020" % zone
        proj_text = 'DEFINE_PROJ PROJ_NAME="MGA_ZONE%s_GDA_2020_AUSTRALIAN_GEODETIC_2020"\n' \
                    'Projection     MGA (Map Grid of Australia)\n' \
                    'Datum          GDA2020\n' \
                    'Zunits         NO\n' \
                    'Units          METERS\n' \
                    'Zone           %s\n' \
                    'Xshift         0.000000\n' \
                    'Yshift         0.000000\n' \
                    'Parameters\n' \
                    'END_DEFINE_PROJ' % (zone, zone)
    elif 'GDA94' in datum:
        proj_name = "MGA_ZONE%s_GDA_94_AUSTRALIAN_GEODETIC_1994" % zone
        proj_text = 'DEFINE_PROJ PROJ_NAME="MGA_ZONE%s_GDA_94_AUSTRALIAN_GEODETIC_1994"\n' \
                    'Projection     MGA (Map Grid of Australia)\n' \
                    'Datum          GDA94\n' \
                    'Zunits         NO\n' \
                    'Units          METERS\n' \
                    'Zone           %s\n' \
                    'Xshift         0.000000\n' \
                    'Yshift         0.000000\n' \
                    'Parameters\n' \
                    'END_DEFINE_PROJ' % (zone, zone)
    else:
        print("Sorry, I don't do that yet...")
        proj_name = None
        proj_text = None
    return proj_text, proj_name


proj_text, proj_name = projection_definer()


# Step three: make a GMS.
print('Step three: make a GMS.')


def make_GMS():
    gms_str = 'GLOBAL_MAPPER_SCRIPT VERSION=1.00 SHOW_WARNINGS=NO\n' \
              'UNLOAD_ALL\n' \
              '%s\n' % proj_text
    gms_str = gms_str + 'IMPORT FILENAME="%s" TYPE=AUTO\n' % image_path
    gms_str = gms_str + 'EXPORT_RASTER FILENAME="%s" TYPE=GEOTIFF SPATIAL_RES_METERS="0.25" GEN_WORLD_FILE=YES ' \
                        'GLOBAL_BOUNDS=%s,%s,%s,%s LAYER_BOUNDS_EXPAND=5 USE_EXACT_BOUNDS=YES\n' \
                        'UNLOAD_ALL' % (tif_path, xmin, ymin, xmax, ymax)
    with open(gms_path, 'w') as g:
        g.write(gms_str)


make_GMS()


# step 4: Run GMS.
print('step 4: Run GMS.')
command_str = [gm_exe, gms_path]
subprocess.call(command_str)

# step 5: lascolour
print('step 5: lascolour')
command_str_lc = ['lascolor', '-i', str(working_laz), '-image', str(tif_path), '-o', str(output_laz)]
subprocess.call(command_str_lc)





