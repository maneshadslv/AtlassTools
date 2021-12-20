import pandas as pd
import os
import geojson
from shapely.geometry import LineString, MultiLineString, Polygon, Point
from shapely.ops import linemerge, unary_union
from gooey import GooeyParser, Gooey
from multiprocessing import Pool, freeze_support, Manager
import math
import shapefile_old as shp
import sys


tile_in_go = sys.argv[1]
ctr_folder = sys.argv[2]


class tool:
    def __init__(self, tile_in):
        self.ctr_folder = ctr_folder
        self.output_folder = os.path.join(self.ctr_folder, 'output_contours')
        if not os.path.isdir(self.output_folder):
            os.mkdir(self.output_folder)
        self.cheat_file = os.path.join(self.ctr_folder, 'cheat_mode.csv')
        self.tl_relationshps = pd.read_csv(self.cheat_file)
        self.tl_relationshps['Relevant'] = self.tl_relationshps['Relevant'].str.split(', ')
        self.intermediate_elevs = []
        self.something_here = False
        self.load_lines_relevant(tile_in)

    def load_tile(self, path_in):
        shape_loaded = shp.Reader(path_in)
        linestring_list = []
        test_dic = {}
        for item in shape_loaded.iterShapeRecords():
            fields = [a for a in shape_loaded.fields if 'Deletion' not in a[0]]
            shape_coords_xy_tups = item.shape.__geo_interface__['coordinates']
            shape_coords_xy = [list(a) for a in shape_coords_xy_tups]
            record = list(item.record)
            try:
                elev_record_index = fields.index(['ELEVATION', 'F', 5, 3])
            except ValueError:
                elev_record_index = fields.index(['ELEVATION', 'N', 3, 0])
            try:
                type_record_index = fields.index(['TYPE', 'C', 12, 0])
            except ValueError:
                type_record_index = fields.index(['TYPE', 'C', 5, 0])
            elev_of_line = record[elev_record_index]
            shape_coords_xyz = [[round(a[0], 3), round(a[1], 3), elev_of_line] for a in shape_coords_xy]
            if 'Inter' in record[type_record_index]:
                self.intermediate_elevs.append(elev_of_line)
            linestring_out = LineString(shape_coords_xyz)
            linestring_list.append(linestring_out)
            if elev_of_line in test_dic.keys():
                t = test_dic[elev_of_line]
                t.append(linestring_out)
                test_dic[elev_of_line] = t
            else:
                test_dic[elev_of_line] = [linestring_out]
        return linestring_list, test_dic

    def write_output_file(self, line_list_in, major_tile):
        output_path = os.path.join(self.output_folder, "%s.shp" % major_tile)
        print('Saving %s...' % major_tile)
        m = shp.Writer(output_path, shapeType=13)
        m.field('ELEV', 'F', decimal=3)
        m.field('TYPE', 'C')
        for f in line_list_in.__geo_interface__['coordinates']:
            try:
                retype_coords = [list(a) for a in f]
            except TypeError:
                retype_coords = [list(f)]
            # print(retype_coords)
            try:

                elev = retype_coords[0][2]
                m.linez([retype_coords])
                if elev in self.intermediate_elevs:
                    line_type = 'Intermediate'
                else:
                    line_type = 'Major'
                m.record(ELEV=elev, TYPE=line_type)
            except Exception as e:
                print('error was', e)
                m.null()
        m.close()

    def examine_head_tail(self, elev, test_dic):
        relevant_lines = test_dic[elev]
        lines_info = []
        self.something_here = False
        print('Setting up match table for elev %s...' % elev)
        for i, line in enumerate(relevant_lines):
            first_point = line.coords[0]
            last_point = line.coords[-1]
            line_list = [i, line, first_point, last_point]
            lines_info.append(line_list)

        temp_pd = pd.DataFrame(columns=['Index number', 'Linestring', 'First point', 'Last point'],
                               data=lines_info)

        def find_matching_first_to_last(row):
            match_list = []
            first_tuple = row['First point']
            identit = row['Index number']
            for k, s in enumerate(temp_pd['Linestring'].tolist()):
                l_listed = list(s.coords)
                if first_tuple in l_listed and k != identit:
                    match_list.append(k)
                    self.something_here = True

            return match_list

        print('Finding matches for elev %s...' % elev)
        temp_pd.loc[:, 'Matches'] = temp_pd.apply(find_matching_first_to_last, axis=1)

        if self.something_here:
            print('Match or matches found...')
            for j, item in enumerate(temp_pd['Matches']):
                if len(item) > 0:
                    # find index in list
                    first = temp_pd.loc[j]['First point']
                    for match in item:
                        match_list = list(temp_pd.loc[match]['Linestring'].coords)
                        match_index = match_list.index(first)
                        if len(match_list) > 2:
                            new_line = LineString(match_list[:-1])
                        else:
                            new_line = LineString(match_list)
                        temp_pd.loc[j]['Linestring'] = new_line
        new_line_list = temp_pd['Linestring'].tolist()
        return new_line_list

    def load_lines_relevant(self, major_tile):
        print('Setting up %s...' % major_tile)

        relevant_pd = self.tl_relationshps[self.tl_relationshps['name'] == major_tile]
        relevant_list = []
        try:
            relevant_list = relevant_pd['Relevant'].to_list()[0]
        except IndexError:
            print('No tiles for %s...' % major_tile)
            exit()
        if 'list' not in str(type(relevant_list)) or len(relevant_list) == 0:
            print('No tiles for %s...' % major_tile)
        else:
            line_list = []
            for i, item in enumerate(relevant_list):
                path_to_minor = os.path.join(self.ctr_folder, "%s.shp" % item)
                linestring_list, test_dic = self.load_tile(path_to_minor)

                for elev in test_dic.keys():
                    new_linestring_list = self.examine_head_tail(elev, test_dic)
                    line_list = line_list + new_linestring_list
            merge_lines = linemerge(line_list)
            self.write_output_file(merge_lines, major_tile)


tool(tile_in_go)
