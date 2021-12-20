

import time
import numpy as np
import pandas as pd
from laspy.file import File
import math

'''
read data from file
'''
voxelsize=1.0

print('Reading files')
file1='F:/temp/Brisbane_2014_LGA_SW_502000_6965000_1K_Las.laz'
file2='F:/temp/SW_502000_6965000_1k_class_AHD.laz'


tic = time.perf_counter()
inFile1 = File(file1, mode='r')
toc = time.perf_counter()
print(f"{len(inFile1.points):d} records read from {file1:s} in {toc - tic:0.4f} seconds")

tic = time.perf_counter()
inFile2 = File(file2, mode='r')
toc = time.perf_counter()
print(f"{len(inFile2.points):d} records read from {file2:s} in {toc - tic:0.4f} seconds")

print('Creating voxels')
tic = time.perf_counter()
xvalues1=inFile1.get_x_scaled()
yvalues1=inFile1.get_y_scaled()
zvalues1=inFile1.get_z_scaled()
classvalues1=inFile1.get_classification()

vox1={}
for i in range(0, len(xvalues1)):
    if i%10000==0:
        print(i)
    x=xvalues1[i]
    y=yvalues1[i]
    z=zvalues1[i]
    key=(math.floor(x/voxelsize)*voxelsize,math.floor(y/voxelsize)*voxelsize,math.floor(z/voxelsize)*voxelsize)
    
    if not key in vox1.keys():
        vox1[key]={}
        vox1[key]['x']=[]
        vox1[key]['y']=[]
        vox1[key]['z']=[]

    vox1[key][x].append(x)
    vox1[key][y].append(y)
    vox1[key][z].append(z)

xvox1=(xvalues1/voxelsize).astype('int')*voxelsize
yvox1=(yvalues1/voxelsize).astype('int')*voxelsize
zvox1=(zvalues1/voxelsize).astype('int')*voxelsize


xvalues2=inFile2.get_x_scaled()
yvalues2=inFile2.get_y_scaled()
zvalues2=inFile2.get_z_scaled()
classvalues2=inFile2.get_classification()

xvox2=(xvalues2/voxelsize).astype('int')*voxelsize
yvox2=(yvalues2/voxelsize).astype('int')*voxelsize
zvox2=(zvalues2/voxelsize).astype('int')*voxelsize

toc = time.perf_counter()
print(f"{toc - tic:0.4f} seconds")

print(len(zvalues),'min_z={0} max_z={1}'.format(min(zvalues),max(zvalues)))


indices = [i for i, x in enumerate(classvalues) if x == 2]
test=[zvalues[i] for i in indices]
print('ground points:',len(test),'min_z={0} max_z={1}'.format(min(test),max(test)))

toc = time.perf_counter()
print(f"data arrays created in {toc - tic:0.4f} seconds")

'''
create kd tree
'''
tic = time.perf_counter()
points=np.column_stack((xvalues,yvalues))
tree = spatial.cKDTree(points)
toc = time.perf_counter()
print(f"kd tree created in {toc - tic:0.4f} seconds")




'''
for i in range(tilex,tilex+101,GSD):
    for j in range(tiley,tiley+101,GSD):
        tic = time.perf_counter()
        point=[i,j]
        
        
        
        
        results_large=tree.query_ball_point(point, 10*GSD)
        x1=[xvalues[n] for n in results_large]
        y1=[yvalues[n] for n in results_large]
        z1=[zvalues[n] for n in results_large]
        points_large=np.column_stack((x1,y1,z1))
        
        results_small=tree.query_ball_point(point, GSD)
        x1=[xvalues[n] for n in results_small]
        y1=[yvalues[n] for n in results_small]
        z1=[zvalues[n] for n in results_small]
        points_small=np.column_stack((x1,y1,z1))

        toc = time.perf_counter()        
        print(f"cell [{i},{j}] processed in {toc - tic:0.4f} seconds")

        fg, ax = plt.subplots(subplot_kw=dict(projection='3d' ))

        ax.plot3D(x1, y1, z1, "o")
        
        ax.set_aspect(1)
        fg.canvas.draw()
        plt.show( )
                
'''


'''
i=random.randint(0,len(points))
i=2



point=points[i]


#print(' \n\ntesting point {0} class:{1} return:{2}/{3}'.format(point,classvalues[i],retvalues[i],retnumvalues[i]))

results_index1=tree.query_ball_point(point, 1)

results_index10=tree.query_ball_point(point, 10)

#results=data['points'].ix[results_index]
#print(results)

#for result in results:
#    print(points[result], inFile.points[result])

#print(f'intensity:{ivalues[i]:d} vs ')
Height1=zvalues[i]-np.mean([zvalues[i] for i in results_index1])
Height2=zvalues[i]-np.mean([zvalues[i] for i in results_index10])
percentile1=len([x for x in [zvalues[i] for i in results_index1] if zvalues[i] > x ])/len(results_index1)*100
percentile10=len([x for x in [zvalues[i] for i in results_index10] if zvalues[i] > x ])/len(results_index10)*100
Heightdiff_1_to_10=np.mean([zvalues[i] for i in results_index1])-np.mean([zvalues[i] for i in results_index10])
Roughness=np.max([zvalues[i] for i in results_index1])-np.min([zvalues[i] for i in results_index1])
stdelev=np.std([zvalues[i] for i in results_index10])



#set up 5m 3d serach
x1=[xvalues[i] for i in results_index10]
y1=[yvalues[i] for i in results_index10]
z1=[zvalues[i] for i in results_index10]

points2=np.column_stack((x1,y1,z1))
tree2=spatial.cKDTree(points2)
results_index10_3d=tree2.query_ball_point([xvalues[i],yvalues[i],zvalues[i]], 10)
count10m=len(results_index10_3d)
#print(f'dz from 1m average: {Height1:0.4f}')
#print(f'dz from 10m average: {Height2:0.4f}')
#print(f'percentile in 2d radius 1m: {percentile1:0.4f}')
#print(f'percentile in 2d radius 10m: {percentile10:0.4f}')
#print(f'average 1m - averag 10m: {Heightdiff_1_to_10:0.4f}')
#print(f'1m roughness: {Roughness:0.4f}')
#print(f'stdev 2d radius 10m: {stdelev:0.4f}')
#print(f'count in 2d radius 2m: {len(results_index1):0.4f}')
#print(f'count in 2d radius 10m: {len(results_index10):0.4f}')
#print(f'count in 3d ball 10m : {count10m:0.4f}')

average_10=np.mean(z1)
stdev_10=np.std(z1)


fg, ax = plt.subplots(subplot_kw=dict(projection='3d' ))

ax.set_autoscale_on(False)
ax.set_zlim(average_10-4*stdev_10,average_10+4*stdev_10)
ax.set_xlim(xvalues[i]-10,xvalues[i]+10)
ax.set_ylim(yvalues[i]-10,yvalues[i]+10)


ax.plot3D(x1, y1, z1, "o")
ax.plot3D([xvalues[i]],[yvalues[i]],[zvalues[i]], "x")
ax.set_aspect(1)
fg.canvas.draw()
plt.show( )
'''




'''
step=1.0
polyorder=1
resultslstq= leastsquaresgrid(points2,step,polyorder,[xvalues[i],yvalues[i],zvalues[i]])
x,y,z,r,dz=resultslstq
print(np.std(dz))
'''



        
    




'''
values=np.column_stack((zvalues,ivalues,retvalues,retnumvalues,classvalues))
#test(points,inFile.points,points,radius)

toc = time.perf_counter()
print(f"{toc - tic:0.4f} seconds")

'''