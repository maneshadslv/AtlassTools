import os
import shutil
import subprocess
import sys

# input_laz = r"Y:\BR02364_eat_grandma\script_testing\200905_223237_75.laz"
init_swaths = sys.argv[1]
# input_laz_bname = '201101_033449_1.laz'
input_laz_bname = sys.argv[2]
input_laz = os.path.join(init_swaths, input_laz_bname)
tile_size = sys.argv[3]
per_swath_cores = '2'
lasindex_req = True

base_name = os.path.basename(input_laz).replace('.laz', '').replace('.las', '')
base_name_w_ext = os.path.basename(input_laz)
root_dir = os.path.dirname(input_laz)
working_root = os.path.join(root_dir, base_name)
merge_root = os.path.join(root_dir, 'merged_classed_go_hard_2')
if not os.path.isdir(working_root):
    os.mkdir(working_root)
if not os.path.isdir(merge_root):
    os.mkdir(merge_root)
settings_file = os.path.join(merge_root, 'settings.txt')
buff_tiles_folder = os.path.join(working_root, '01_buffered_unclass')
class_tiles_folder = os.path.join(working_root, '02_buffered_class')
cut_tiles_folder = os.path.join(working_root, '03_unbuffered_class')
for a in [buff_tiles_folder, class_tiles_folder, cut_tiles_folder]:
    if not os.path.isdir(a):
        os.mkdir(a)

if lasindex_req:
    # lasindex swath
    print('Making lasindex...')
    lasindex_cmd = ['lasindex', '-i', str(input_laz)]
    subprocess.call(lasindex_cmd)

# tile with buffer
print('Making buffered tiles...')
lastile_command = ['lastile', '-i', str(input_laz), '-odir', str(buff_tiles_folder), '-olaz',
                   '-tile_size', str(tile_size), '-cores', str(per_swath_cores),
                   '-buffer', '25', '-flag_as_synthetic', '-extra_pass']
subprocess.call(lastile_command)

# classify
print('Classifying...')
tiles_str = str(buff_tiles_folder) + r'\*.laz'
lasground_command = ['lasground_new', '-i', tiles_str, '-cores', per_swath_cores, '-hyper_fine',
                     '-spike', '0.1', '-spike_down', '1.5', '-offset', '0.03', '-bulge',
                     '0.5', '-olaz', '-odir', str(class_tiles_folder)]
try:
    with open(settings_file, 'w') as s:
        s.write(' '.join(lasground_command))
        s.close()
    subprocess.call(lasground_command)
except IOError:
    pass

# clip to bb
print('Clipping to bb...')

tiles_str_2 = str(class_tiles_folder) + r'\*.laz'
clip_command = ['las2las', '-i', tiles_str_2, '-cores', per_swath_cores, '-olaz',
                '-odir', str(cut_tiles_folder), '-drop_synthetic']
subprocess.call(clip_command)

# re-merge
print('Merging...')
output_swath = os.path.join(merge_root, "%s" % base_name_w_ext)
tiles_str_3 = str(cut_tiles_folder) + r'\*.laz'
merge_command = ['las2las', '-i', tiles_str_3, '-merged', '-o', str(output_swath)]
subprocess.call(merge_command)

# to clean up after
if os.path.isfile(output_swath) and os.path.getsize(output_swath) > 0:
    shutil.rmtree(working_root)




