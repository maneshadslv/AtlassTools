
@Gooey(program_name="Make TileLayout", use_legacy_titles=True, required_cols=1, optional_cols=3, default_size=(1000,810))
def param_parser():
    parser=GooeyParser(description="Make Tile Layout")
    parser.add_argument("inputfile", metavar="Input Folder", widget="FileChooser", help="Select folder with las/laz files")
    parser.add_argument("gcpfile", metavar="GCP file", widget="FileChooser")
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

    f= open(args.inputfile, 'r')
    inputgcps = [i for line in f for i in line.split('')]

    print(inputgcps)
    return

if __name__ == "__main__":
    main()         
