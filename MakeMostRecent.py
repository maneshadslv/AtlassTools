#-----------------------------------------------------------------------------------------------------------------
#Include libraries
#-----------------------------------------------------------------------------------------------------------------

import os, glob, sys
import io
import datetime
import time



#these locations will be tested for the most current file version
filelocations=[]
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/ClassifiedData_Anditi_20191014')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/GroundClassifiedData_Anditi_20190929')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/ground_citytile')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/ground_QA')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/ground_QA_missing2tiles')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/nonground_pt1_reissue')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/data_from_Anditi/nonground_pt2')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/Terra_classified_outside_tiles')
filelocations.append('K:/BR01280_Brisbane_to_Ipswich-Department_of_Natural_Resources_and_Mines/test')

def getmostrecent(checkfolders,pattern):

    '''
    Searches through folders and creates a list of files patching a search pattern.
    File names are addded to a dictionary and tested for the most recent instance of each file.
    '''

    #dict to store name, size and date modified 
    #once processed will contain path to most recent
    filedict={}
    for folder in checkfolders:
        #make a list of files that match pattern

        files = glob.glob(os.path.join(folder,pattern))
        for filename in files:
            path,name=os.path.split(filename)
            mtime = os.path.getmtime(filename)
            if name in filedict.keys():
                #file already found
                filedict[name]['files'].append({'file':filename,'datemodified':mtime})
            else:
                #addfile
                filedict[name]={}
                filedict[name]['files']=[]
                filedict[name]['current']=''           
                filedict[name]['datemodified']=''   
                filedict[name]['files']=[{'file':filename,'datemodified':mtime}]

    for name,files in filedict.items():
        mostrectime=None
        for filerecord in files['files']:
            if mostrectime==None:
                mostrectime=filerecord['datemodified']
                mostrecfile=filerecord['file']
            else:
                if filerecord['datemodified']>mostrectime:
                    mostrectime=filerecord['datemodified']
                    mostrecfile=filerecord['file']

        return mostrecfile

#-----------------------------------------------------------------------------------------------------------------
#Main entry point
#-----------------------------------------------------------------------------------------------------------------
def main(argv):
    
    print(getmostrecent(filelocations,argv[0]).replace('/','\\'))
if __name__ == "__main__":
    main(sys.argv[1:])            