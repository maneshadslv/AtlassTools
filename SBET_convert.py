import struct
from collections import OrderedDict

radtodeg=57.2958

def convert(infile,outfile,everynth=100):
    recordlen=8*17
    count=0
    print(infile)
    with open(outfile,'w') as writer:
        with open(sbet, 'rb') as reader:
            fileContent = reader.read()
            records=int(len(fileContent)/recordlen)
            for i in range(records):
                if count % everynth ==0:
                    print('\t{0}'.format(count))
                    seekpos = i*recordlen
                    reader.seek(seekpos)
                    record = reader.read(recordlen)
                    #print('starting data at byte position : {0}'.format(seekpos))
                    time = struct.unpack('d',record[:8])[0]
                    lon = float(struct.unpack('d',record[8:16])[0]*radtodeg)
                    lat = float(struct.unpack('d',record[16:24])[0]*radtodeg)
                    alt = float(struct.unpack('d', record[24:32])[0])
                    writer.write('{0},{1},{2},{3}\n'.format(time,lon,lat,alt))

                count=count+1
            reader.close()
        writer.close()
    print('done')


sbets=[]
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Cen_Mid_South_East_VQ780H_19031301/VQH-19031301/Export/export_VQH-19031301_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Cen_Mid_VQ780_19031101/VQ780H-19031101/Export/export_VQ780H-19031101_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Cen_Mid_VQ780H_19030701/VQ780H-19030701/Export/export_VQ780H-19030701_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenHigh_CenMid_190219_VQ780/VQ780/Export/export_VQ780_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenHigh_VQ780_190203/VQ780_190203/Export/export_VQ780_190203_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenHigh_VQ780_190203-2/VQ780_190203-2/Export/export_VQ780_190203-2_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenHigh_VQ780_190215/VQ780_190215/Export/export_VQ780_190215_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenHigh_VQ780_190222_new/VQ780H_190222_GDA2020/Export/export_VQ780H_190222_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenHigh_VQ780_190223/VQ780_190223/Export/export_VQ780_190223_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenMid_VQ780_190224/VQ780H_190224_GDA2020/Export/export_VQ780H_190224_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenMid_VQ780_190224_2/VQ780H_19022402_GDA2020/Export/export_VQ780H_19022402_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_CenMid_VQ780_190225/VQ780H_190225_GDA2020/Export/export_VQ780H_190225_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_SthEast_VQ780_190323/VQ780H_190323_GDA2020/Export/export_VQ780H_190323_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_SthEast_VQ780_190324/VQ780H_190324_GDA2020/Export/export_VQ780H_190324_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_VQ780_190317/VQ780_190317_GDA2020/Export/export_VQ780_190317_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_VQ780H_19031401/VQ780H-19031401/Export/export_VQ780H-19031401_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_VQ780H_19031402/VQ780H-19031402/Export/export_VQ780H-19031402_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_VQ780H_19031501_new/VQ780H-19031501/Export/export_VQ780H-19031501_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Derwent_VQ780H_19031601/VQ780H-19031601/Export/export_VQ780H-19031601_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Mid_North__Timberlands_Part_14_15_VQH-19012601/VQH-19012601/Export/export_VQH-19012601_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Mid_North_VQ780_190124-2_VQ780i/VQ780_190124-2VQ780i/Export/export_VQ780_190124-2VQ780i.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Mid_North_VQ780_190131/VQ780_190131/Export/export_VQ780_190131_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_NthMid_VQ780_193001/VQ780_193001/Export/export_VQ780_193001_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Refly_VQ780_190508/VQ780_190508_GDA94/Export/export_VQ780_190508_GDA94.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_Refly_VQ780H_19050801/VQ780H-19050801/Export/export_VQ780H-19050801_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_South_East_Derwent_VQ780H_19031701/VQ780H-19031701/Export/export_VQ780H-19031701_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_South_East_VQ780_19031602/VQ780H-19031602/Export/export_VQ780H-19031602_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_South_East_VQ780H_19031102/VQ780H-19031102/Export/export_VQ780H-19031102_gda2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_SthEast_VQ780_190324/VQ780_190324_GDA2020/Export/export_VQ780H_190324_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_SthEast_VQ780_190327/VQ780S_190327_GDA2020/Export/export_VQ780S_190327_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/DPIPWE_SthEast_VQ780_190327-2/VQ780H_190327-2_GDA2020/Export/export_VQ780H_190327-2_GDA2020.out")
sbets.append("//Processor-b1/PPE_3/DPIPWE_Metadata/Pospac/Timberlands_Part_4_Part_5_DPIPWE_Mid_North_VQ780i_190124/190124_VQ780i/Export/export_190124_VQ780i.out")

converted={}
for sbet in sbets:
    outfile=sbet.replace('.out','.csv')
    converted[sbet]=convert(sbet,outfile,2000)
