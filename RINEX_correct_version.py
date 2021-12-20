import os
import subprocess
from gooey import Gooey, GooeyParser
from multiprocessing import Pool, Manager, freeze_support
import zipfile
import rarfile
import shutil
from itertools import repeat

gfzrnx_path = r"\\10.10.10.142\projects\Reporting_Templates\RINEX\gfzrnx_win64.exe"


class FilesNotPresent(Exception):
    pass


class FileSizeError(Exception):
    pass


class FileTimeError(Exception):
    pass


error_list = []


class unzip_and_convert:
    def __init__(self, input_f, output_folder):
        """Main handler class for the tool.
        Requires from the Gooey input an input zip, rar, or .??o file path and the output folder."""
        self.input_file = input_f
        self.output_dir = output_folder
        self.input_dir = os.path.dirname(self.input_file)
        self.input_file_bn, self.input_ext = os.path.splitext(os.path.basename(self.input_file))
        self.input_file_bn = self.input_file_bn.replace('.rnx', '')
        try:
            self.extracted_rinex_file = [os.path.join(self.input_dir, a) for a in os.listdir(self.input_dir) if a.endswith('o') and a.startswith(self.input_file_bn)][0]  # only used for checks just in case it breaks
        except IndexError:
            self.extracted_rinex_file = None

        self.new_file_path = os.path.join(self.output_dir, '%s_v2.21o' % self.input_file_bn)

    def unzipper(self):
        """
        Simple unzipping function for input rar or zip files. Detects which strategy is appropriate.
        Outputs result into input_folder.

        Arguments:
        self.input_ext - file extension of the archive
        self.input_file - full path to input archive
        self.input_dir - location of input archive

        :returns:
        Does not return any values. Result is archive is unpacked.

        Usage:
        unzip_and_convert(self.input_file, self.output_dir).unzipper()
        """
        if self.input_ext in '.rar':
            rarfile.RarFile(self.input_file).extractall(self.input_dir)
        elif self.input_ext in '.zip':
            zipfile.ZipFile(self.input_file).extractall(self.input_dir)

    def run_gf_command(self):
        """
        Runs the conversion using the gfzrnx_win64.exe tool.

        Arguments:
        gfzrnx_path - location of gfzrnx exe
        self.input_file - location of input .??o file
        self.new_file_path - location of output .21o file

        :returns:
        Does not return any values. Result is converted end files in output folder.

        Usage:
        unzip_and_convert(self.input_file, self.output_dir).run_gf_command()
        """

        command_in = [str(gfzrnx_path), '-finp', str(self.extracted_rinex_file), '-fout', str(self.new_file_path), '-vo', '2', '-d', '9999999\n']
        subprocess.call(command_in)

    def copy_eph(self):
        """
        Copies over relevant ephemeris for easy loading in Pospac.

        Arguments:
        self.input_dir - location of input file
        self.output_dir - save location
        self.input_file_bn - basename of input file

        :return:
        Does not return anything, just copies.

        Usage:
        unzip_and_convert(self.input_file, self.output_dir).copy_eph()
        """
        copy_file_list = [os.path.join(self.input_dir, f) for f in os.listdir(self.input_dir) if
                          f.startswith(self.input_file_bn) and not f.endswith('o')
                          and not f.endswith('zip') and not f.endswith('rar')]
        for f in copy_file_list:
            dest = os.path.join(self.output_dir, os.path.basename(f))
            shutil.copy2(f, dest)

    def check_file(self):
        """
        Checks conversion was successful, using some very basic checks.
        :return:
        Returns any error messages into error message list.
        Usage:
        unzip_and_convert(self.input_file, self.output_dir).check_file()
        """
        ts_input = os.path.getmtime(self.input_file)
        ts_output = os.path.getmtime(self.new_file_path)
        # File size should be greater
        try:
            fs_input = os.path.getsize(self.input_file)
            fs_output = os.path.getsize(self.new_file_path)
            ex_input = os.path.getsize(self.extracted_rinex_file)
            if not fs_input < ex_input < fs_output:
                raise FileSizeError
            # Files should be present
            if not os.path.exists(self.new_file_path):
                raise FilesNotPresent
            # Timestamp should be later
            if not ts_input < ts_output:
                raise FileTimeError
        except FileSizeError:
            error_list.append((self.input_file_bn, 'Output file is suspiciously small'))
        except FilesNotPresent:
            error_list.append((self.input_file_bn, 'Output RINEX was not present'))
        except FileTimeError:
            error_list.append((self.input_file_bn, 'Output file has inappropriate timestamp.'))


def poolboy(list_in, cores, output_dir):
    """
    Multithreader handler for the process.
    :param list_in: List of files to be processed.
    :param cores: Number of cores to use
    :param output_dir: Desired output directory.
    :return:

    Usage:
    poolboy(list_in, cores, output_dir)
    """
    print('Running pool...')
    if __name__ == '__main__':
        freeze_support()
        manager = Manager()
        pool = Pool(processes=int(cores))
        pool.starmap(workflow, zip(list_in, repeat(output_dir)))
        pool.close()
        pool.join()
    print('Pool complete...')


def workflow(file_in, output_folder):
    """
    Workflow handler for each file.
    :param file_in: Full file path to input archive file
    :param output_folder: Full file path to desired output folder
    :return:
    Usage:
    from pool.starmap(workflow, zip(list_in, repeat(output_dir)))

    """
    print('Running %s...' % os.path.basename(file_in))
    unzip_and_convert(file_in, output_folder).unzipper()
    unzip_and_convert(file_in, output_folder).run_gf_command()
    unzip_and_convert(file_in, output_folder).copy_eph()
    unzip_and_convert(file_in, output_folder).check_file()
    print('Processing on %s complete!' % os.path.basename(file_in))


def main(g):
    """Main process. Takes GUI input, threads it, and manages it."""
    input_dir = g.input_dir
    output_dir = g.output_dir
    cores = g.cores
    try:
        unz_all = g.unzip_all
    except AttributeError:
        unz_all = False
    arc_list = [os.path.join(input_dir, a) for a in os.listdir(input_dir) if a.endswith('.rnx.zip')]
    all_list = [os.path.join(input_dir, a) for a in os.listdir(input_dir) if a.endswith('.rar') or a.endswith('.zip')]
    if unz_all:
        print('Working on ALL archives (%d files)...' % len(all_list))
        poolboy(all_list, cores, output_dir)
    else:
        print('Working on .rnx.zip archives only (%d files)...' % len(arc_list))
        poolboy(arc_list, cores, output_dir)
    print('Errors:')
    if len(error_list) > 0:
        for a in error_list:
            print('%s had error %s' % a)
    else:
        print('No errors detected!')
    print('Done!')


@Gooey(program_name="Rinex Converter", use_legacy_titles=True, required_cols=2, default_size=(750, 550))
def goo():
    parser = GooeyParser(description="Rinex convertor, release 1")
    parser.add_argument('input_dir', metavar='Input folder', widget='DirChooser')
    parser.add_argument('output_dir', metavar='Output folder', widget='DirChooser')
    parser.add_argument('cores', metavar='Cores to use')
    parser.add_argument('-unzip_all', metavar="Unzip files that don't end in '.rnx.zip'?", action='store_true')
    return parser.parse_args()


if __name__ == "__main__":
    main(goo())

