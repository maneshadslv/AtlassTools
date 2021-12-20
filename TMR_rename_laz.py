import sys
import shutil
import os, glob
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *

@Gooey(program_name="TMR renamer", use_legacy_titles=True, required_cols=1, default_size=(1000,820))
def param_parser():
    parser=GooeyParser(description="TMR renamer")
    parser.add_argument("input_folder", metavar="Input Directory ", widget="DirChooser", help="Select folder with input files")
    parser.add_argument("output_dir", metavar="Output Directory", widget="DirChooser", help="Output directory")
    parser.add_argument("file_type",metavar="Input File Type", help="Select input file type", choices=['las', 'laz'], default='laz')
    parser.add_argument('name', metavar="AreaName", help="Project Area Name eg : MR101502 ", default="")
    parser.add_argument("zone", metavar="zone", type=int)
    parser.add_argument("year", metavar="year", type=int)
    parser.add_argument("-co", "--cores",metavar="Cores", help="No of cores to run in", type=int, default=4)

    return parser.parse_args()

def copyfile(input, output):

    try:
        shutil.copyfile(input, output)

    except subprocess.CalledProcessError as suberror:
        log=log +'\n'+ "{0}\n".format(suberror.stdout)
        return (False,None,log)

    finally:
        if os.path.isfile(output):
            log = "Copying file for {0} Success".format(input)
            return (True,output, log)

        else: 
            log = "Copying file for {} Failed".format(input)
            return (False,output, log)


def main():

    freeze_support()

    args = param_parser()

    intputfolder = args.input_folder.replace('\\','/')
    outputfolder = args.output_dir.replace('\\','/')
    filetype = args.file_type
    areaname = args.name
    zone = args.zone
    cores = args.cores
    year = args.year

    lasfilepattern = '*.{0}'.format(filetype)
    lasfilepattern = lasfilepattern.split(';')
    files = AtlassGen.FILELIST(lasfilepattern, intputfolder)

    outputfolder = AtlassGen.makedir(os.path.join(outputfolder, '{0}_LAS_AHD_unclipped'.format(areaname)).replace('\\', '/'))

    copy_tasks = {}

    for file in files:
        path, filename , ext = AtlassGen.FILESPEC(file)
        x, y = filename.split('_')
        input = file
        output =  os.path.join(outputfolder, '{0}_{5}_2_AHD_SW_{1}m_{2}m_{3}_1k.{4}'.format(areaname, x, y, zone, filetype, year)).replace("\\", "/")
        
        copy_tasks[filename] = AtlassTask(filename, copyfile, input, output)


    p=Pool(processes=cores)      
    copy_results=p.map(AtlassTaskRunner.taskmanager,copy_tasks.values())

    for result in copy_results:
        if not result.success:
            print('File {0} could not be copied'.format(result.name))

if __name__ == "__main__":
    main()         
