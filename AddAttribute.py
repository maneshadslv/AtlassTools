import sys
import shutil
import os, glob
import json
from gooey import Gooey, GooeyParser
from multiprocessing import Pool,freeze_support
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
#-----------------------------------------------------------------------------------------------------------------
#Development Notes
#-----------------------------------------------------------------------------------------------------------------
# 29/03/2018 -Alex Rixon - Original development Alex Rixon
#

#-----------------------------------------------------------------------------------------------------------------
#Notes
#-----------------------------------------------------------------------------------------------------------------
#This tool is used to tile data and run lastools ground clasification.

#-----------------------------------------------------------------------------------------------------------------
#Global variables and constants
#-----------------------------------------------------------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------
#Multithread Function definitions
#-----------------------------------------------------------------------------------------------------------------
# Function used to calculate result

@Gooey(program_name="Add attributes to a TileLayout", use_legacy_titles=True, required_cols=1, optional_cols=3, advance=True, default_size=(1000,500))
def param_parser():
    parser=GooeyParser(description="Add attributes to a Tile Layout")
    parser.add_argument("inputfile", metavar="Input Tilelayout File", widget="FileChooser", help="Select Tilelayout json file")
    parser.add_argument("output_dir", metavar="Output Directory",widget="DirChooser", help="Output directory", default="")
    attr_group = parser.add_argument_group("Attribute", gooey_options={'show_border': True,'columns': 3})
    attr_group.add_argument("attrname",metavar="Attribute Name", help="Attribute Name\n\n")
    attr_group.add_argument("attrval", metavar="Attribute Value", help="if Naming convention for files used, \nreplace x,y with %X% and %Y%.\nex: dem_%X%m_%Y%m.asc")
    attr_group.add_argument("--division", metavar="Shorten X, Y", help="Reduce the X and Y values to the nearest 100,1000. \nleave blank for None\n", type=int)

    args = parser.parse_args()
    return args

#-----------------------------------------------------------------------------------------------------------------
#Function definitions
#-----------------------------------------------------------------------------------------------------------------


   
#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():
    
    args = param_parser()
    jsonfile = args.inputfile
    outputpath = args.output_dir
    attrname = args.attrname
    attrval = args.attrval
    division = args.division
   

    tilelayout = AtlassTileLayout()


    tilelayout.fromjson(jsonfile)
    outputfile =  os.path.join(outputpath, 'TileLayout.json')

    print(len(tilelayout.tiles))
    for tiledata in tilelayout.tiles.items():
        tilename, tile = tiledata
        atrrstr = attrval
        if not division ==None:

            xmin = int(tile.xmin/division)
            ymin = int(tile.ymin/division)

        else:
            xmin = int(tile.xmin)
            ymin = int(tile.ymin)

        print(xmin)
        atrrstr = atrrstr.replace("%X%", str(xmin))
        atrrstr = atrrstr.replace("%Y%", str(ymin))

        tile.addparams(**{attrname: atrrstr})
        print(tile)

    
    tilelayout.createGeojsonFile(outputfile)
    if os.path.isfile(outputfile):
        print("\n\nProcess Complete\nTileLayout output to {0}".format(outputfile))
    else:
        print("Output File could not be created")

    return

if __name__ == "__main__":
    main()         


