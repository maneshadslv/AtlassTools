import json
from pprint import pprint
import os
from collections import OrderedDict

class CoveragePlots():
    pass
    def __init__(self,data):
        self.data=data

class TileData():
    pass
    def __init__(self,data):
        self.data=data    

class TileLayout():
    pass
    def __init__(self,data):
        self.data=data

class Project():
    def __init__(self,file):
        self.file=file
        if os.path.isfile(file):
            self.load()
        else:
            self.newproject()
            self.save()

    def __str_(self):
        return '{0}'.format(self.data)

    def newproject(self):
        '''
        creates empty ordered dict and runs project setup form
        '''

        self.data=OrderedDict()
        self.data['project']=OrderedDict()
        self.data['project']['meta']=OrderedDict()
        self.data['project']['meta']['name']=input('Enter project name:')
        self.data['project']['meta']['location']=input('Enter project location:')
        self.data['project']['meta']['bounds']=[float(input('xmin:')),float(input('ymin:')),float(input('xmax:')),float(input('ymax:'))]
        
        self.data['project']['meta']['tilelayout']=OrderedDict()
        self.data['project']['meta']['tilelayout']['classname']='TileLayout'
        self.data['project']['meta']['tilelayout']['data']=OrderedDict()

        self.data['project']['process']=OrderedDict()
        #Process ID should be in yymmdd_HHMMSS_Name
        self.data['project']['process']['00001']=OrderedDict()
        self.data['project']['process']['00001']['classname']='TileData'
        self.data['project']['process']['00001']['data']=OrderedDict()

        self.data['project']['process']['00002']=OrderedDict()
        self.data['project']['process']['00002']['classname']='CoveragePlots'
        self.data['project']['process']['00002']['data']=OrderedDict()


    def save(self):
        with open(self.file, 'w') as outfile:
            json.dump(self.data, outfile)

    def load(self):
        self.instances=[]
        with open(self.file) as infile:
            self.data = json.load(infile,object_pairs_hook=OrderedDict)
        self._data=self.data
        for processid in self._data['project']['process']:
            clsname=self._data['project']['process'][processid]['classname']
            data=self._data['project']['process'][processid]['data']
            instance=globals()[clsname](data)
            print(type(instance))
            self.instances.append(instance)



project =globals()['Project']('F:/project.json')

  
print(str(project.data))

