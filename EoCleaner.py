import csv
import os.path as op
import os
from gooey import Gooey, GooeyParser
from tkinter import messagebox


class eoCSVcleaner:
    def __init__(self):
        indetect = goo()

        # check if empty return
        if indetect:
            print(os.listdir(indetect))
            self.csvHere = False
            for a in os.listdir(indetect):
                if a.endswith('.csv'):
                    self.csvHere = True
            if not self.csvHere:
                messagebox.showerror("Error", "Invalid input selected, or none at all")
                print("Error - No or invalid input selected")
            for file in os.listdir(indetect):
                filename = op.join(op.normpath(indetect), file)
                if file.endswith(".csv") or file.endswith(".CSV"):
                    if not file.endswith('cleaned.csv'):
                        print("I choose " + file)
                        self.cleaner(filename)
                    else:
                        continue
                else:
                    continue
        else:
            messagebox.showerror("Error", "No or invalid input selected")
            print("Error - No or invalid input selected")

    def cleaner(self, infile):
        print("Process now running; be patient")
        opener = open(infile, newline='')
        with opener as csvfile:
            base = op.basename(infile)
            bname = op.splitext(base)[0]
            output_name = bname + "_cleaned.txt"
            output_path = op.join(op.dirname(infile), output_name)
            dirtyread = csv.reader(csvfile)
            with open(output_path, 'w') as headertime:
                wh = csv.DictWriter(headertime, fieldnames=["ID " "Time " "Easting " "Northing " "Height " "Roll " 
                                                            "Pitch " "Yaw "])
                wh.writeheader()
            next(dirtyread)
            for row in dirtyread:
                ID = row[2]
                sow = row[3]
                easting = row[4]
                northing = row[5]
                height = row[6]
                roll = row[7]
                pitch = row[8]
                yaw = row[9]

                # fix ID
                newid = (ID[:ID.index('\t')]).strip('"')

                line_dict = {"ID": newid, "Time": sow, "Easting": easting, "Northing": northing, "Height": height,
                             "Roll": roll, "Pitch": pitch, "Yaw": yaw}
                # print(line_dict.keys())
                with open(output_path, 'a', newline='') as csvfile2:
                    fieldnames = ["ID", "Time", "Easting", "Northing", "Height", "Roll", "Pitch", "Yaw"]
                    w = csv.DictWriter(csvfile2, fieldnames=fieldnames, delimiter=' ')
                    w.writerow(line_dict)

# GUI handling
@Gooey(program_name="EO Reformatter and Editor", use_legacy_titles=True, required_cols=1, default_size=(600, 600))
def goo():
    parser = GooeyParser(description="Reformat EO CSVs")
    parser.add_argument("inputfolder", metavar="Folder containing EO CSVs", widget="DirChooser",
                        help="Select input folder")
    noot = (parser.parse_args())
    return noot.inputfolder


eoCSVcleaner()
