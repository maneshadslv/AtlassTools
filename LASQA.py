

import time
import numpy as np
import pandas as pd
from laspy.file import File
import math
from scipy import spatial
import random

import itertools
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from matplotlib.colors import LightSource


def poly_matrix(x, y, order=2):
    """ generate Matrix use with lstsq """
    ncols = (order + 1)**2
    G = np.zeros((x.size, ncols))
    ij = itertools.product(range(order+1), range(order+1))
    for k, (i, j) in enumerate(ij):
        G[:, k] = x**i * y**j
    return G
    
    
def CalculateLeastSquares(xyz,polyorder):
    
    #polyorder = 2  # order of polynomial
    x, y, z = xyz.T
    #print '===before==='
    #print ('\tmin x:{0} max x:{1}'.format(min(x),max(x)))
    #print ('\tmin y:{0} max y:{1}'.format(min(y),max(y)))
    #print ('\tmin z:{0} max z:{1}'.format(min(z),max(z)))
    #print ('\tcalculating {0} points'.format(len(z)))
    #Save offsets
    x0=float(math.floor(np.mean(x)))
    y0=float(math.floor(np.mean(y)))

    
    x, y, z = x - x0, y - y0 , z  # this improves accuracy
  
    # make Matrix:
    G = poly_matrix(x, y, polyorder)
    # Solve for np.dot(G, m) = z:
    m = np.linalg.lstsq(G, z)[0]
            
    r=np.reshape(np.dot(G, m), x.shape)
    #print '\tsolution found for {0} order polynomial'.format(polyorder)

    dz=np.subtract(z, r)

    x, y, r = x + x0, y + y0 , r
        
    #print '===after==='
    #print ('\tmin x:{0} max x:{1}'.format(min(x),max(x)))
    #print ('\tmin y:{0} max y:{1}'.format(min(y),max(y)))
    #print ('\tmin z:{0} max z:{1}'.format(min(r),max(r)))
    #print ('\tmin dz:{0} max dz:{1}'.format(round(min(dz),4),round(max(dz),4)))
    return(x, y, r)

def leastsquaresgrid(xyz,step,polyorder,origin):  
    x0, y0, z0 = xyz.T

    x0, y0, z0 = x0 - np.mean(x0), y0 - np.mean(y0), z0 - np.mean(z0)  # this improves accuracy
    
    x=[]
    y=[]
    z=[]
    '''
    for i,zval in enumerate (z0):
        if -0.8<=zval<=0.8:
            x.append(x0[i])
            y.append(y0[i])
            z.append(z0[i])
    '''
    x=np.array(x0)
    y=np.array(y0)
    z=np.array(z0)
    
    # make Matrix without noise points
    G = poly_matrix(x, y, polyorder)

    # Solve for np.dot(G, m) = z:
    m = np.linalg.lstsq(G, z,rcond=None)[0]

    cols=int((math.ceil(max(x))-math.floor(min(x)))/step)
    rows=int((math.ceil(max(y))-math.floor(min(y)))/step)
    nx, ny = cols,rows
    
    xx, yy = np.meshgrid(np.linspace(x.min(), x.max(), nx),
                         np.linspace(y.min(), y.max(), ny))
    GG = poly_matrix(xx.ravel(), yy.ravel(), polyorder)
    zz = np.reshape(np.dot(GG, m), xx.shape)    
    

    # Plotting (see http://matplotlib.org/examples/mplot3d/custom_shaded_3d_surface.html):
    fg, ax = plt.subplots(subplot_kw=dict(projection='3d'))
    ls = LightSource(270, 45)
    rgb = ls.shade(zz, cmap=cm.gist_earth, vert_exag=0.5, blend_mode='soft')
    surf = ax.plot_surface(xx, yy, zz, rstride=1, cstride=1, facecolors=rgb,linewidth=0, antialiased=False, shade=False)
    ax.plot3D(x, y, z, "o")

    fg.canvas.draw()
    plt.show()
    
    
    #Make dz plot
    r = np.reshape(np.dot(G, m), x.shape) 
    dz=z-r
    
    fg, ax = plt.subplots(subplot_kw=dict(projection='3d'))
    ax.plot3D(x, y, dz, "x")
    fg.canvas.draw()
    plt.show()
    
    # make Matrix  with noise points and output original point list unfiltered
    x0, y0, z0 = xyz.T

    x, y, z = x0 - np.mean(x0), y0 - np.mean(y0), z0 - np.mean(z0)  
    
    G = poly_matrix(x, y, polyorder)
    r = np.reshape(np.dot(G, m), x.shape) 
    dz=z-r
    
    x, y, z = xyz.T
    
    return (x,y,z,r,dz)


'''
read data from file
'''
radius=0.25
tic = time.perf_counter()
filename="D:/ground_class/3D_Sunshine_Coast_LASx64Tiles/re-tiled/200218_1519_GDA94_MGA-56_100m_tiles/513600_7035400.laz"

tilex=513600
tiley=7035400

GSD=10

inFile = File(filename, mode='r')
toc = time.perf_counter()
print(f"{len(inFile.points):d} records read from file in {toc - tic:0.4f} seconds")

'''
create dataframe
'''
tic = time.perf_counter()
data={}
data["points"] = pd.DataFrame(inFile.points["point"])
data["points"].columns = (x.lower() for x in data["points"].columns)
# rescale and offset
data["points"].loc[:, ["x", "y", "z"]] *= inFile.header.scale
data["points"].loc[:, ["x", "y", "z"]] += inFile.header.offset
data["las_header"] = inFile.header

toc = time.perf_counter()
print(f"data frame created in {toc - tic:0.4f} seconds")

'''
create arrays for kd tree
'''
tic = time.perf_counter()
xvalues=inFile.get_x_scaled()
yvalues=inFile.get_y_scaled()
zvalues=inFile.get_z_scaled()
classvalues=inFile.get_classification()

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