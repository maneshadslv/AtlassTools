'''Takes a csv as output by the CRM and builds a Trello card.
   Stores Trello card ID and other info in a db on Projects.'''
import io
import sqlite3
import uuid
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfpage import PDFPage
from collections import OrderedDict
import os
import re
import pandas as pd
import shapefile_old as shapefile
import requests
import datetime
try:
    from gooey import GooeyParser, Gooey
except ImportError:
    os.system('start /wait cmd /k pip install gooey')
    from gooey import Gooey, GooeyParser

# timezone
tz_offset = datetime.timezone(datetime.timedelta(hours=10))

numbers = re.compile('\d+(?:\.\d+)?')

csv_folder = r'C:\Trello'

logo = "\\\\10.10.10.142\\projects\\PythonScripts\\icons\\logo.png"
global_db = r'G:\global_db'

# Trello stuff
# logins
trello_card_links = "https://trello.com/1/cards"
apikey = '2e4a6967dcc93370d2582847d6a45726'
atoken = 'a0f7750db6dce905e830089813cb8f7c4611695c8264ba325b1266cb156e4274'
params_presented = {'key': apikey, 'token': atoken}
# PHASE ONE BOARD
po_static_idb = '5c6ba2fc2b495b8e447e2bd8'
po_to_capture_list_id = "5c73757fd870658419b26cf8"
po_not_captured_label = "5c6ba2fc91d0c2ddc5361a4c"
po_in_progress_label = "5c6ba2fc91d0c2ddc5361a4e"
po_calibration_label = "5d3f89e4e88dff49ff475f8a"
po_mine_site_label = '5d2bc842bbeedd120de5d60f'
# BUDERIM BOARD
bud_static_idb = '5d4b5c81f14f58321c53da34'
bud_to_capture_list_id = '5d776925e96d9682c79c8f87'
bud_not_captured_label = '5d776a05fc8c6b5f5776f765'
bud_mine_site_label = '5d776a12a829c70384f1ee21'
# EMAILS
# person to email
trello_gmail = "etesting.aerotrello@gmail.com"
trello_contact = ["eleanor.chandlertemple@aerometrex.com.au"]  # here for ease of testing
'''
trello_contact = ["eleanor.chandlertemple@aerometrex.com.au",
                  "stuart.wileman@aerometrex.com.au",
                  "mahdi.ghafourian@aerometrex.com.au",
                  "Margi.McFadyen@aerometrex.com.au",
                  "LIDAR@aerometrex.com.au"]
'''
# constant sites with shifts
shifting_list = ['callide', 'curragh', 'dawson']


class csv_grabber:
    # grabs and scans the csv file
    def __init__(self):
        self.csv_list = [os.path.join(csv_folder, a) for a in os.listdir(csv_folder) if a.endswith('.csv')]
        # find which has latest creation date, check if within 5 mins
        self.input_csv = None
        self.values_dict = {}
        if len(self.csv_list) == 0:
            print('error - no csv found')
            exit()
        else:
            self.input_csv = self.find_newest_csv()
        if self.input_csv:
            self.values_dict = self.make_values_dict()
        else:
            print('error - csv not valid')
            exit()
        if len(self.values_dict.keys()) == 2:
            print('error - csv not valid')
            exit()
        self.projects_folder_link = r"\\10.10.10.142\projects\Projects\%s" % self.values_dict['Data Location'][3:]
        self.values_dict['Projects folder'] = self.projects_folder_link
        self.br_code = self.values_dict['Job No.'].strip(' ')
        self.project_name = self.values_dict['Data Location'][3:].split('-')[0].split('_', 1)[1]
        self.area_name = self.values_dict['Schedule Name'].replace(' ', '')
        if 'Whole of Site' in self.area_name:
            self.area_name = 'Whole'
        self.client_name = self.values_dict['Data Location'][3:].split('-')[1]
        self.flightplans_folder = os.path.join(self.projects_folder_link, 'FlightPlans')
        self.flight_plan_dic = {}
        self.aoi_folder = os.path.join(self.projects_folder_link, 'AOI')
        self.sh_lines = []
        self.quotes_folder = os.path.join(self.projects_folder_link, 'Submitted_Quote')
        self.lidar_times = []
        self.image_times = []
        self.general_pandas_input = None
        self.area_dependent_pandas = pd.DataFrame()
        self.reconstructed_dic = {}
        self.reconstructed_pandas = pd.DataFrame()
        self.aois_df = pd.DataFrame()
        self.flight_plan_df = pd.DataFrame()
        self.mine_yn = False
        self.project_uuid = None
        self.quote_file = None
        print(self.values_dict)

        # Now, look in Projects folder to see if there is already a DB there
        db_list = [os.path.join(self.projects_folder_link, a) for a in os.listdir(self.projects_folder_link)
                   if a.endswith('.db')]
        self.database_file = None
        self.general_pandas_dic = self.make_general_dic_from_vals_dic()
        self.products_pandas_dic = self.make_product_dic_from_vals_dic()

        if len(db_list) == 1:
            self.database_file = db_list[0]
            self.from_existing_db()
        elif len(db_list) == 0:
            self.from_scratch_mode()
        else:
            print('error: too many databases')
            exit()

    def replace_all_tables(self):
        print('Updating database')
        s_f = self.flight_plan_df.astype(str)
        self.flight_plan_df = s_f
        a_f = self.area_dependent_pandas.astype('str')
        self.area_dependent_pandas = a_f

        conn = self.create_connection()
        if 'level_0' in self.general_pandas_input.columns:
            self.general_pandas_input.drop('level_0', axis=1, inplace=True)
        if 'index' in self.general_pandas_input.columns:
            self.general_pandas_input.drop('index', axis=1, inplace=True)
        if 'index' in self.area_dependent_pandas.columns:
            self.area_dependent_pandas.drop('index', axis=1, inplace=True)
            self.area_dependent_pandas.set_index('area')
        for i, row in self.general_pandas_input.iterrows():
            if row['BR Code'] is None:
                self.general_pandas_input.drop([i], inplace=True)
            elif str(row['BR Code']) is 'NaN':
                self.general_pandas_input.drop([i], inplace=True)
            elif pd.isna(row['BR Code']):
                self.general_pandas_input.drop([i], inplace=True)

        if conn is not None:
            self.general_pandas_input.to_sql("general_info", conn, if_exists="replace", dtype='string')
            self.aois_df.to_sql("aois", conn, if_exists="replace", dtype='string')
            self.flight_plan_df.to_sql('flight_plans', conn, if_exists="replace", dtype='string')
            self.area_dependent_pandas.to_sql('card_ids', conn, if_exists="replace", dtype='string')

    def make_general_dic_from_vals_dic(self):
        # effectively reorders and renames the keys in the dic to make the new one.
        # in some cases also constructs new values to match old method.
        if self.project_uuid is None:
            self.project_uuid = str(uuid.uuid4())
        # print('db file', self.database_file)
        if self.database_file is None:
            self.database_file = os.path.join(self.projects_folder_link, "%s_%s.db" % (self.br_code, self.project_name))
        new_general_dic = {'Project Name': self.project_name,
                           'BR Code': self.br_code,
                           'Client': self.client_name,
                           'PC Code': self.br_code.replace('BR0', 'PC'),
                           'Project Notes': None,
                           'Database name': os.path.splitext(os.path.basename(self.database_file))[0],
                           'Mine site': self.mine_yn,
                           'Database file': self.database_file,
                           'Project UUID': self.project_uuid,
                           'Quote': self.quote_file,
                           'Capture date type': self.values_dict['Date type']}
        return new_general_dic

    def make_product_dic_from_vals_dic(self):
        cut_type = 'Tiles'
        if 'Image as merged mosaic output' in self.values_dict['Format']:
            cut_type = 'Areas'
        shift_req = False
        for site in shifting_list:
            if site in self.project_name.lower():
                shift_req = True
        products_dic = {'File format': self.values_dict['Output'],
                        'Cut to': cut_type,
                        'Projection': self.values_dict['Projection'],
                        'Processing type': self.values_dict['Classify'],
                        'Client Manager': self.values_dict['Client Manager'],
                        'Pixel Size': self.values_dict['Pixel Size'],
                        'Data location': self.values_dict['Data Location'],
                        'Block shift requirement': shift_req,
                        'area': self.area_name,
                        'Project Name': self.project_name}

        return products_dic

    def make_trello_description(self):
        card_header = "%s_%s_%s_%s" % (self.br_code, self.project_name, self.area_name,
                                       self.br_code.replace('BR0', 'PC').replace(' ', ''))
        plan_to_frames = []
        if self.flight_plan_df.empty:
            plan_to_frames.append('Issue importing flightplan - please update manually')
        else:
            for key in self.flight_plan_dic.keys():
                frame_count = self.flight_plan_dic[key]['Total photos']
                lat_overlap = self.flight_plan_dic[key]['Lateral overlap']
                forward_overlap = self.flight_plan_dic[key]['Forward overlap']
                plan_system = self.flight_plan_dic[key]['System']
                plan_str = "%s - frame count: %s, overlaps f/s: %s/%s, planned system: %s\n" \
                           % (key, frame_count, forward_overlap, lat_overlap, plan_system)
                plan_to_frames.append(plan_str)
        if len(self.lidar_times) > 1:
            self.lidar_times.sort()
        if len(self.image_times) > 1:
            self.image_times.sort()
        if len(self.lidar_times) == 0 or len(self.image_times) == 0:
            self.image_times.append('Due dates could not be automatically extracted')
            self.lidar_times.append('Due dates could not be automatically extracted')

        # make the string
        desc_string = "CARD NAME: %s" \
                      "\n DATE:" \
                      "\n - Fixed: %s" \
                      "\n Due days past capture: %s" \
                      "\n" \
                      "\n"\
                      "\nFLIGHTPLANS AVAILABLE:" \
                      "\n%s" \
                      "\n" \
                      "\nNAV:" \
                      "\nTBA" \
                      "\n" \
                      "\nSURFACE:" \
                      "\nTBA" \
                      "\n" \
                      "\nPRODUCTS:" \
                      "\n%s %s cut to %s" \
                      "\n" \
                      "\nPROCESSING LEVEL:" \
                      "\n%s" \
                      "\n" \
                      "\nPROJECTION:" \
                      "\n%s" \
                      "\n" \
                      "\nCLIENT MANAGER:" \
                      "\n%s" \
                      "\n" \
                      "\nDATA LOCATION:" \
                      "\n%s" \
                      "\n" \
                      "\nBLOCK SHIFT REQUIRED:" \
                      "\n%s" \
                      "\n" \
                      "\nOPC:" % (card_header, self.values_dict['Date type'], str(self.image_times),
                                  '\n'.join(plan_to_frames), self.products_pandas_dic['Pixel Size'],
                                  self.products_pandas_dic['File format'], self.products_pandas_dic['Cut to'],
                                  self.products_pandas_dic['Processing type'], self.products_pandas_dic['Projection'],
                                  self.products_pandas_dic['Client Manager'], self.products_pandas_dic['Data location'],
                                  self.products_pandas_dic['Block shift requirement'])
        return desc_string

    def update_exisiting_trello_card(self, id_number):
        print('Updating card %s...' % id_number)
        idLabels = bud_not_captured_label
        card_header = "%s_%s_%s_%s" % (self.br_code, self.project_name, self.area_name,
                                       self.br_code.replace('BR0', 'PC').replace(' ', ''))
        link_to_card = trello_card_links + "/%s/" % id_number
        print(link_to_card)
        print(card_header)
        new_params_presented = {"name": card_header.strip(' '),
                                "idLabels": idLabels,
                                "desc": self.make_trello_description()}
        for a in params_presented:
            new_params_presented[a] = params_presented[a]
        go = requests.request("PUT", link_to_card, params=new_params_presented)
        print(new_params_presented)
        return go

    def make_new_trello_card(self):
        idLabels = po_not_captured_label
        card_header = "%s_%s_%s_%s" % (self.br_code, self.project_name, self.area_name,
                                       self.br_code.replace('BR0', 'PC'))
        new_params_presented = {"name": card_header,
                                "pos": "top",
                                "idList": po_to_capture_list_id,
                                "idLabels": idLabels,
                                "desc": self.make_trello_description()}
        for a in params_presented:
            new_params_presented[a] = params_presented[a]
        go = requests.request("POST", trello_card_links, params=new_params_presented)
        return go

    def get_newest_card_id(self):
        board_url = "https://trello.com/1/lists/%s/cards" % po_to_capture_list_id
        new_params_presented = {'cards': 'open'}
        for k in params_presented.keys():
            new_params_presented[k] = params_presented[k]
        card_list_init = requests.get(board_url, params=params_presented).json()
        card_id = None
        for count, b in enumerate(card_list_init):
            if count == 0:
                card_id = b['id']
        return card_id

    def from_scratch_mode(self):
        print('scratch')
        # make tables
        general_dic = self.make_general_dic_from_vals_dic()
        self.project_uuid = str(uuid.uuid4())
        general_series = pd.Series(general_dic, name=self.project_name)
        g_frame = pd.DataFrame(general_series)
        self.general_pandas_input = g_frame.T
        self.flight_plan_finder()
        self.flight_plan_reader()
        self.quote_worker()
        self.flight_plan_df = pd.DataFrame.from_dict(self.flight_plan_dic, orient='index')

        # make card
        self.make_new_trello_card()
        new_card_id = self.get_newest_card_id()
        products_dic = self.make_product_dic_from_vals_dic()
        products_dic['buderim'] = new_card_id

        products_dic_series = pd.Series(products_dic, name=products_dic['area'])

        self.area_dependent_pandas = pd.DataFrame(products_dic_series).T

        # make db
        self.replace_all_tables()

    def from_existing_db(self):
        self.general_pandas_input = self.general_pandas_get()
        print('existing')
        self.flight_plan_finder()
        self.flight_plan_reader()
        self.quote_worker()
        self.flight_plan_df = pd.DataFrame.from_dict(self.flight_plan_dic, orient='index')
        # we need to have two separate workflows: one for the "old" dbs, which
        # have the IDs in the General table, and one for the "new" ones, which will
        # have a new table called "card_ids".
        # DETECT OLDER DB:
        card_ids = {}
        new_db_type = True
        if 'Buderim card ID' in self.general_pandas_input.columns.to_list():
            card_ids['buderim'] = [self.general_pandas_input['Buderim card ID'].to_list()[0]]
            card_ids['phaseone'] = [self.general_pandas_input['PhaseOne card ID'].to_list()[0]]
            card_ids['area'] = [self.area_name]
            new_db_type = False
            product_dic = self.make_product_dic_from_vals_dic()
            card_ids = {**card_ids, **product_dic}
            self.area_dependent_pandas = pd.DataFrame.from_dict(card_ids, orient='columns')
        else:
            # it's a "newer" card
            self.area_dependent_pandas = self.get_other_table('card_ids')

        self.general_pandas_input.drop(columns=['index'])
        # we need to check this is a new area area or not too - this will alter if we update a
        # trello card or make a new one.
        # this will also need to implement product types.
        # also needs to possibly update self.project uuid. and quote file.
        self.project_uuid = self.general_pandas_input['Project UUID']

        # Need to set up flight plan stuff before this point!
        if not new_db_type:
            self.update_exisiting_trello_card(card_ids['phaseone'][0])
            self.replace_all_tables()
        else:
            # make series for areas pandas
            prod_dict = self.make_product_dic_from_vals_dic()
            area_flag = False
            line_index = None
            print(self.area_dependent_pandas.columns)
            for i, item in enumerate(self.area_dependent_pandas['area'].tolist()):
                if self.area_name.lower() in item.lower():
                    area_flag = True
                    line_index = i
            if not area_flag:
                self.make_new_trello_card()
                card_id = self.get_newest_card_id()
                prod_dict['phaseone'] = card_id
            else:
                card_id = self.area_dependent_pandas['phaseone'].tolist()[line_index]
                self.update_exisiting_trello_card(card_id)
            area_series = pd.Series(data=prod_dict, name=self.area_name)
            t = self.area_dependent_pandas.join(area_series, how='left')
            p_series = pd.Series(self.products_pandas_dic, name=self.area_name)
            p_t = pd.DataFrame(p_series)
            t_p = p_t.T
            t.set_index('index', inplace=True)
            merged_pd_1 = pd.concat([t, t_p], sort=False)
            if 'Whole' in merged_pd_1.columns.tolist():
                merged_pd_2 = merged_pd_1.drop(columns=['Whole'])
            else:
                merged_pd_2 = merged_pd_1
            self.area_dependent_pandas = merged_pd_2

            self.replace_all_tables()

    def make_values_dict(self):
        with open(self.input_csv, 'r') as iv:
            temp_contents = {}
            ivr = iv.readlines()
            date_type = 'Fixed'
            captured = False
            for line in ivr:
                line = line.replace('\n', '')
                if ':' in line:
                    line_spl = line.replace('\n', '').split(':', 1)
                    key = line_spl[0]
                    val = line_spl[1]
                    if 'Data Location' in line:
                        val = val[1:].replace(' ', '_')
                    if 'Classify' in line:
                        val = val.replace(' classify', '')
                    if key in temp_contents.keys():
                        temp_list = [val]
                        for item in temp_contents[key]:
                            temp_list.append(item)
                        temp_contents[key] = temp_list
                    else:
                        temp_contents[key] = val
                elif 'Client Manager' in line:
                    cm = line.replace('Client Manager ', '')
                    temp_contents['Client Manager'] = cm
                elif 'Flexible Flying Date' in line:
                    date_type = 'Flexible'
                elif 'Capture Complete' in line:
                    captured = True
                else:
                    print(line)
            temp_contents['Date type'] = date_type
            temp_contents['Capture_status'] = captured
        return temp_contents

    def find_newest_csv(self):
        newest = None
        dm = None
        dm_diff = None
        now_utc = datetime.datetime.now(tz_offset)
        now_here = now_utc.astimezone()
        for file in self.csv_list:
            date_modified = datetime.datetime.fromtimestamp(os.path.getmtime(file), tz=tz_offset)
            time_since_creation = now_here - date_modified
            if dm_diff is None:
                dm = date_modified
                dm_diff = time_since_creation
                newest = file
            elif time_since_creation < dm_diff:
                dm = date_modified
                dm_diff = time_since_creation
                newest = file
            else:
                pass
        return newest

    def get_general_table(self):
        conn = self.create_connection()
        select_string = "SELECT * FROM general_info"
        pd_fetch = pd.read_sql(select_string, conn)
        return pd_fetch

    def general_pandas_get(self):
        g_pd = self.get_general_table()
        return g_pd

    def flight_plan_finder(self):
        for r, d, f in os.walk(self.flightplans_folder, topdown=True):
            for file in f:
                # make actual path of file
                if 'pdf' in file:
                    file_direct = os.path.join(r, file)
                    if 'pdf' in os.path.splitext(file)[1]:
                        # a valid flightplan will have KML and ZIP of same name, in theory
                        kml_file = str(os.path.splitext(file_direct)[0]) + ".kml"
                        zip_file = str(os.path.splitext(file_direct)[0]) + '.zip'
                        if os.path.exists(kml_file) and os.path.exists(zip_file):
                            system_name = os.path.dirname(file_direct)
                            file_path = os.path.normpath(file_direct)
                            self.flight_plan_dic[file] = (system_name, file_path)

    def flight_plan_reader(self):
        plan_headers = ['Strip width', 'Lateral overlap', 'Run spacing', 'Forward overlap', 'Photo base',
                        'Total length', 'Total lines', 'Total photos', 'Planned By', 'Survey Time']
        for key in self.flight_plan_dic.keys():
            flight_plan_name = key
            file_path = self.flight_plan_dic[key][-1]
            resource_manager = PDFResourceManager()
            fake_file_handle = io.StringIO()
            converter = TextConverter(resource_manager, fake_file_handle)
            page_interpreter = PDFPageInterpreter(resource_manager, converter)
            with open(file_path, 'rb') as file:
                for page in PDFPage.get_pages(file, caching=True, check_extractable=True):
                    page_interpreter.process_page(page)
                text = fake_file_handle.getvalue()
            converter.close()
            fake_file_handle.close()
            page_split_output = text.split(' UNCONTROLLED DOCUMENT WHEN PRINTED ')
            first_page = page_split_output[0]
            script = None
            params_index = OrderedDict()
            param_values = {}
            backup_sys = None
            if 'VQ' in self.flight_plan_dic[key][0]:
                param_values['System'] = 'VQ'
                backup_sys = 'VQ'
                script = first_page[first_page.find('LiDAR'):first_page.rfind('LiDAR')]
                if len(script) == 0:
                    # print(first_page)
                    try:
                        script = first_page[first_page.find('Lidar:'):first_page.rfind('Images:Collect images')].split(':')[1]
                    except IndexError:
                        script = None
            elif 'H68' in self.flight_plan_dic[key][0]:
                script = 'H68 Standard'
                param_values['System'] = 'Harrier'
                backup_sys = 'H68'
            if script is None:
                print("You will need to enter flight plan info manually; non-standard setup found.")
            else:
                last_page = page_split_output[-1]
                for param in plan_headers:
                    params_index[param] = last_page.find(param)
                    """
                    if last_page.find(param) == -1:
                        params_index[param] = None"""
                for i, param in enumerate(plan_headers):
                    param_value = None
                    if i < (len(plan_headers)-1):
                        # print(param, "has i", i, "and next param is", plan_headers[i+1])
                        next_param = plan_headers[i+1]
                        index_current = params_index[param]
                        index_next = params_index[next_param]
                        cut_up_string = last_page[index_current:index_next]
                        param_value = cut_up_string.split(':')[-1].strip(' ')
                        # print(param_value)
                    elif i == (len(plan_headers)-1):
                        # print("Final param is", param)
                        index_current = params_index[param]
                        end = last_page.find('[')
                        cut_up_string = last_page[index_current:end]
                        param_value = cut_up_string.split(':')[-1].strip(' ')
                        # print(param_value)
                    param_values[param] = param_value
                    param_values['script'] = script
                    param_values['initial_vals'] = self.flight_plan_dic[flight_plan_name]
                param_values['System'] = backup_sys
                self.flight_plan_dic[flight_plan_name] = param_values

    def create_connection(self):
        conn = None
        full_db_path = self.database_file
        try:
            conn = sqlite3.connect(full_db_path)
        except sqlite3.Error as e:
            print("Connection error:")
            print(e)
        return conn

    def aoi_worker(self):
        aoi_listing = []
        try:
            aoi_listing = os.listdir(self.aoi_folder)
        except OSError as e:
            print("When trying to access the Cut AOI folder, I encountered:", e)
            exit()
        shp_list = []
        if len(aoi_listing) == 0:
            print('Oops, no shp in AOI folder!')
            print("I looked in", self.aoi_folder)
            exit()
        for f in aoi_listing:
            if f.endswith('.shp'):
                shp_list.append(f)
        for s in shp_list:
            area_information = {}
            s_path = os.path.join(self.aoi_folder, s)
            with shapefile.Reader(s_path) as area:
                for internal_shape in area:
                    is_uuid = uuid.uuid1()
                    area_information['shape_uuid'] = is_uuid
                    area_information['Filename'] = s
                    area_information['File path'] = s_path
                    geoj = internal_shape.__geo_interface__
                    area_information['GEOJSON'] = geoj
                    base_name = os.path.splitext(s)[0]
                    area_information['cutting_name'] = base_name
            self.sh_lines.append(area_information)

    def quote_worker(self):
        quote_list = []
        quote_name = "%s %s.pdf" % (self.br_code, self.project_name)
        theoretical_quote_name = os.path.join(self.quotes_folder, quote_name)
        theoretical_quote_name_underscores = os.path.join(self.quotes_folder,
                                                          "%s_%s.pdf" % (self.br_code, self.project_name))
        theoretical_quote_name_all_spaces = os.path.join(self.quotes_folder, quote_name.replace('_', ' '))
        # print(theoretical_quote_name_all_spaces, theoretical_quote_name, theoretical_quote_name_underscores)
        if os.path.isfile(theoretical_quote_name):
            quote_list.append(theoretical_quote_name)
        elif os.path.isfile(theoretical_quote_name_underscores):
            quote_list.append(theoretical_quote_name_underscores)
        elif os.path.isfile(theoretical_quote_name_all_spaces):
            quote_list.append(theoretical_quote_name_all_spaces)
        if len(quote_list) == 0:
            print('Yikes! I could not find a quote. Help!')
            exit()
        quote_list = str(quote_list)
        if 'Quote' in self.general_pandas_input.columns:
            self.general_pandas_input.at[0, 'Quote'] = quote_list
        else:
            self.general_pandas_input['Quote'] = quote_list
        self.quote_pdf_reader()

    def quote_pdf_reader(self):
        for file_path in self.general_pandas_input['Quote'].tolist():
            if file_path is not None:
                file_path = ''.join(file_path.strip('[]').strip("'"))
                # print('Accessing', file_path)
                resource_manager = PDFResourceManager()
                fake_file_handle = io.StringIO()
                converter = TextConverter(resource_manager, fake_file_handle)
                page_interpreter = PDFPageInterpreter(resource_manager, converter)
                with open(file_path[2:], 'rb') as file:
                    for page in PDFPage.get_pages(file, caching=True, check_extractable=True):
                        page_interpreter.process_page(page)
                    text = fake_file_handle.getvalue()
                # print('got past rb')
                converter.close()
                fake_file_handle.close()
                #print(text)

                worked = False
                for a in text.split('$'):
                    #print(a)
                    if 'Days' in a[-8:-1] or 'days' in a[-8:-1]:
                        days = int(numbers.findall(a[a.find('Days'):])[0])
                        #print(days)
                        if days > 1:
                            if 'image' in a.lower() and 'intensity' not in a.lower() and 'embossed' not in a.lower():
                                self.image_times.append(days)
                                worked = True
                            else:
                                self.lidar_times.append(days)
                                worked = True
                if worked is False:
                    for a in text.split('days'):
                        print("")
                        #print(a + "days")
                        print("Issue automatically extracting due dates. You will need to add these manually")

    def get_other_table(self, table):
        conn = self.create_connection()
        select_string = "SELECT * FROM %s" % table
        pd_fetch = pd.read_sql(select_string, conn)
        return pd_fetch

    # mod db
    def update_db_old(self):
        print('Updating database...')
        conn = self.create_connection()
        if 'level_0' in self.general_pandas_input.columns:
            self.general_pandas_input.drop('level_0', axis=1, inplace=True)
        if conn is not None:
            with conn:
                self.general_pandas_input.to_sql("general_info", conn, if_exists="replace", dtype='string')
                self.aois_df.to_sql("aois", conn, if_exists="replace", dtype='string')
                self.flight_plan_df.to_sql('flight_plans', conn, if_exists="replace", dtype='string')


csv_grabber()

