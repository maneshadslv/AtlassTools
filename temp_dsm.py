import sys
sys.path.append('{0}/lib/atlass/'.format(sys.path[0]).replace('\\','/'))
from Atlass_beta1 import *
def fix_dsm(demfile,dsmfile,dsm_outputfile): 
    '''
    taking from final/clipped or unclipped, dem grid and dsm grid (no ground class no fill cells.)
    must has same bounding box and rows and colmuns 

    '''
    

    dem=AsciiGrid()
    dem.readfromfile(demfile)

    dsm=AsciiGrid()
    dsm.readfromfile(dsmfile)

    # creates grids containing ones, zeros or no data.
    ones=np.array(np.ones((dem.grid.shape[0],dem.grid.shape[1])), ndmin=2, dtype=int)
    zeros=np.array(np.zeros((dem.grid.shape[0],dem.grid.shape[1])), ndmin=2, dtype=int)    
    nodata=np.array(np.ones((dem.grid.shape[0],dem.grid.shape[1])), ndmin=2, dtype=int)*dem.nodata_value   

    # extract dsm nodata areas
    dsm_nodata=ones*(dsm.grid==dsm.nodata_value)

    #create new output dsm grid
    dsm_output=AsciiGrid() 
    dsm_output.header=dsm.header

    #outputting voids as value 1
    dsm_output.grid=np.where(dsm_nodata==1,dem.grid,dsm.grid)

    dsm_output.savetofile(dsm_outputfile)

    return dsm_outputfile

def main(argv):
    tiles=[]
    tiles.append('494000_6952000')
    tiles.append('494000_6953000')
    tiles.append('494000_6954000')
    tiles.append('494000_6955000')
    tiles.append('494000_6956000')
    tiles.append('494000_6957000')
    tiles.append('494000_6958000')
    tiles.append('494000_6959000')
    tiles.append('495000_6952000')
    tiles.append('495000_6953000')
    tiles.append('495000_6954000')
    tiles.append('495000_6955000')
    tiles.append('495000_6956000')
    tiles.append('495000_6957000')
    tiles.append('495000_6958000')
    tiles.append('495000_6959000')
    tiles.append('496000_6952000')
    tiles.append('496000_6953000')
    tiles.append('496000_6954000')
    tiles.append('496000_6955000')
    tiles.append('496000_6956000')
    tiles.append('496000_6957000')
    tiles.append('496000_6958000')
    tiles.append('496000_6959000')
    tiles.append('497000_6952000')
    tiles.append('497000_6953000')
    tiles.append('497000_6954000')
    tiles.append('497000_6955000')
    tiles.append('497000_6956000')
    tiles.append('497000_6957000')
    tiles.append('497000_6958000')
    tiles.append('497000_6959000')
    tiles.append('498000_6952000')
    tiles.append('498000_6953000')
    tiles.append('498000_6954000')
    tiles.append('498000_6955000')
    tiles.append('498000_6956000')
    tiles.append('498000_6957000')
    tiles.append('498000_6958000')
    tiles.append('498000_6959000')
    tiles.append('499000_6952000')
    tiles.append('499000_6953000')
    tiles.append('499000_6954000')
    tiles.append('499000_6955000')
    tiles.append('499000_6956000')
    tiles.append('499000_6957000')
    tiles.append('499000_6958000')
    tiles.append('499000_6959000')
    tiles.append('500000_6952000')
    tiles.append('500000_6953000')
    tiles.append('500000_6954000')
    tiles.append('500000_6955000')
    tiles.append('500000_6956000')
    tiles.append('500000_6957000')
    tiles.append('500000_6958000')
    tiles.append('500000_6959000')
    tiles.append('501000_6952000')
    tiles.append('501000_6953000')
    tiles.append('501000_6954000')
    tiles.append('501000_6955000')
    tiles.append('501000_6956000')
    tiles.append('501000_6957000')
    tiles.append('501000_6958000')
    tiles.append('501000_6959000')
    tiles.append('502000_6952000')
    tiles.append('502000_6953000')
    tiles.append('502000_6954000')
    tiles.append('502000_6955000')
    tiles.append('502000_6956000')
    tiles.append('502000_6957000')
    tiles.append('502000_6958000')
    tiles.append('502000_6959000')

    for tile in tiles:
        demfile='F:/BNE_TEST/final_GRIDS/190812_0947_makeGrid/DEM/DEM-GRID_001_{0}_1000m.asc'.format(tile)
        dsmfile='F:/BNE_TEST/final_GRIDS/190812_0947_makeGrid/DSM/DSM-GRID_001_{0}_1000m.asc'.format(tile)
        dsm_outputfile='F:/BNE_TEST/delivery/29_DSM_1m_ASCII_ESRI/SW_{0}_1k_1m_ESRI_DSM.asc'.format(tile)
        fix_dsm(demfile,dsmfile,dsm_outputfile)

if __name__ == "__main__":
    main(sys.argv[1:])            