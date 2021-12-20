import os
from gooey import Gooey, GooeyParser
import requests
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer import pdfparser
import io


class the_tool:
    def __init__(self, goo):
        self.folder_in = goo.dir_in
        self.file_format = goo.ff
        if not os.path.isdir(self.folder_in):
            print('Error: folder does not exist')
            exit()
        self.rinex_base_codes = []
        self.reg_13_folder = os.path.join(self.folder_in, 'REG13')
        if '21o' in self.file_format:
            self.rinex_file_bn_list = [a for a in os.listdir(self.folder_in) if a.endswith('o')]
        elif '.rnx.zip' in self.file_format:
            self.rinex_file_bn_list = [a for a in os.listdir(self.folder_in) if a.endswith('.rnx.zip')]
        else:
            print('Error - invalid extension selected')
            exit()
        if len(self.rinex_file_bn_list) == 0:
            print('Error: No rinex found in %s' % self.folder_in)
            exit()
        else:
            if not os.path.isdir(self.reg_13_folder):
                os.mkdir(self.reg_13_folder)
            # base code shound be first four letters
            self.rinex_base_codes = [a[:4].upper() for a in self.rinex_file_bn_list]
            print('%s bases detected - %s' % (len(self.rinex_base_codes), ', '.join(self.rinex_base_codes)))
            self.reg_info = {}
            for b in self.rinex_base_codes:
                info = self.fetch_reg13(b)
                self.reg_info[b] = info
            print('#########################################')
            print('#################RESULTS#################')
            print('#########################################')
            for b in self.rinex_base_codes:
                print('%s: %s' % (b, self.reg_info[b]))
            print('#########################################')
            print('REG certs have been saved in the below path for your convenience:')
            print(str(self.reg_13_folder))
            print('#########################################')

    def fetch_reg13(self, base_code):
        if 'RTX' not in base_code:
            print('Collecting info for %s...' % base_code)
            save_path = os.path.join(self.reg_13_folder, "REG13_%s.pdf" % base_code.upper())
            pdf_address = r"http://sbc.smartnetaus.com/Reg13/GDA2020/%s.pdf" % base_code.upper()
            get_pdf = requests.get(pdf_address)
            with open(save_path, 'wb') as f:
                f.write(get_pdf.content)
            with open(save_path, 'rb') as f:
                resource_manager = PDFResourceManager()
                fake_file_handle = io.StringIO()
                converter = TextConverter(resource_manager, fake_file_handle)
                page_interpreter = PDFPageInterpreter(resource_manager, converter)
                kosher = True
                try:
                    for page in PDFPage.get_pages(f, caching=True, check_extractable=True):
                        page_interpreter.process_page(page)
                except pdfparser.PDFSyntaxError:
                    print('error on', save_path)
                    kosher = False
                if kosher:
                    text = fake_file_handle.getvalue()
                    converter.close()
                    fake_file_handle.close()
            if 'inconvenience' in text:
                reg_text = "REG13 not available"
            else:
                text_page_split = text.split('Page1of2')[1]
                south_lat = 'S ' + text_page_split[
                                   text_page_split.find('SouthLatitudeanditsuncertaintyofvalue:'):text_page_split.rfind(
                                       'EastLongitudeanditsuncertaintyofvalue:')].strip(
                    'SouthLatitudeanditsuncertaintyofvalue:').split('±')[0].replace('°', 'deg')
                east_long = 'E ' + text_page_split[
                                   text_page_split.find('EastLongitudeanditsuncertaintyofvalue:'):text_page_split.rfind(
                                       'ElevationaboveEllipsoidanditsuncertaintyofvalue:')].strip(
                    'EastLongitudeanditsuncertaintyofvalue:').split('±')[0].replace('°', 'deg')
                elev = text_page_split[
                       text_page_split.find('ElevationaboveEllipsoidanditsuncertaintyofvalue:'):text_page_split.rfind(
                           'mGeocentricDatumofAustralia')].strip(
                    'ElevationaboveEllipsoidanditsuncertaintyofvalue:').split('±')[0] + 'm'
                reg_text = ', '.join([south_lat, east_long, elev])
            return reg_text


@Gooey(program_name="Reg13 Checker", use_legacy_titles=True, required_cols=1, default_size=(750, 500))
def goo():
    parser = GooeyParser(description='Reg13 Assistant for SmartNet+SmartBase')
    parser.add_argument('-dir_in', metavar='Folder holding only files to be scanned', widget='DirChooser')
    parser.add_argument('-ff', metavar="File format", choices=['Rinex unzipped (*.21o, *.20o etc)',
                                                               'Zipped files (*.rnx.zip)'])
    return parser.parse_args()


the_tool(goo())
