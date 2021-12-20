#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------
import sys
import os
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]))
from Atlass_beta1 import *
from gooey import Gooey, GooeyParser

#-----------------------------------------------------------------------------------------------------------------
#Gooey input
#-----------------------------------------------------------------------------------------------------------------

@Gooey(program_name="Renamer", use_legacy_titles=True, show_sidebar=False, navigation=True, required_cols=0)
def param_parser():
    parser=GooeyParser(description="Renamer")
    parser.add_argument("input_files", metavar="Files", widget="MultiFileChooser", help="Select input files", default='C:\\Users\\Manesha\\OneDrive - atlass.com.au\\Python\\Gui\\input\\180228_041704.las')
    parser.add_argument("find1", metavar = "Find 1", default="export - Channel 1 - ")
    parser.add_argument("-replace1", metavar = "replace 1", default="")
    parser.add_argument("find2", metavar = "Find 2", default="_Channel_1 - originalpoints")
    parser.add_argument("-replace2", metavar = "replace 2", default="")
    args = parser.parse_args()
    return args



#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main():

    #Set Arguments
    args = param_parser()

    find1=args.find1
    find2=args.find2
    replace1=args.replace1
    if replace1==None: replace1=''
    replace2=args.replace2
    if replace2==None: replace2=''

    input_files=args.input_files.split(';')
    print(input_files)

    for file in input_files:
        
        path,name,extn=Atlass.AtlassGen.FILESPEC(file)
        name=name.replace(find1,replace1)
        name=name.replace(find2,replace2)

        name='{0}\{1}.{2}'.format(path,name,extn) 

        print('rename {0} to {1}'.format(file,name) )

        os.rename(file,name)

    return

if __name__ == "__main__":
    main()         

