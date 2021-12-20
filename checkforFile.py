import sys
import shutil
import os, glob


def main():

    filen = "E:\\part2\\Other_deliveries\\Flight_trajectories\\list.txt"
    dir1 = "E:\\BR01241_Victorian_Forestry_Part01_Delivery\\Other_Deliveries\\Flight_Trajectory"
    dir2 = "E:\\part2\\Other_deliveries\\Flight_trajectories"

    lines = [line.rstrip('\n')for line in open(filen)]

    i =0
    for line in lines:
        f1 = os.path.join(dir1,line).replace('\\','/')
        f2 = os.path.join(dir2,line).replace('\\','/')
        if os.path.isfile(f1):
            os.remove(f2)
            print('deleting {0}'.format(f2))
            i+=1
            

        else:
            print('not duplicated {0}'.format(f2))
            
    print('number of files duplicated {0}'.format(i))


if __name__ == "__main__":
    main()         
