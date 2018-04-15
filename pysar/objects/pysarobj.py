############################################################
# Program is part of PySAR v2.0                            #
# Copyright(c) 2018, Zhang Yunjun, Heresh Fattahi          #
# Author:  Zhang Yunjun, Heresh Fattahi, 2018              #
############################################################
# class used for file operation within PySAR
# Recommended usage:
#     from pysar.objects import timeseries, ifgramStack, geometry

import os, sys, glob
import time
from datetime import datetime as dt
import h5py
import numpy as np

BOOL_ZERO = np.bool_(0)
INT_ZERO = np.int16(0)
FLOAT_ZERO = np.float32(0.0)
CPX_ZERO = np.complex64(0.0)

dataType = np.float32

dataTypeDict = {'bool':np.bool_,'byte':np.bool_,'flag':np.bool_,
                'int':np.int16,'int16':np.int16,'short':np.int16,'int32':np.int32,
                'int64':np.int64,'long':np.int64,
                'float':np.float32,'float32':np.float32,
                'float_':np.float64,'float64':np.float64,
                'complex':np.complex64,'complex64':np.complex64,'cpx_float32':np.complex64,
                'cfloat':np.complex64,'cfloat32':np.complex64,
                'complex128':np.complex128,'complex_':np.complex128,'cpx_float64':np.complex128
               }

##------------------ Variables ---------------------##
timeseriesKeyNames = ['timeseries','HDFEOS','GIANT_TS']

timeseriesDatasetNames = ['raw',
                          'troposphericDelay',
                          'topographicResidual',
                          'ramp',
                          'displacement']

geometryDatasetNames = ['height',
                        'latitude',
                        'longitude',
                        'rangeCoord',
                        'azimuthCoord',
                        'incidenceAngle',
                        'headingAngle',
                        'slantRangeDistance',
                        'shadowMask',
                        'waterMask',
                        'commonMask',
                        'bperp']

ifgramDatasetNames = ['unwrapPhase',
                      'coherence',
                      'connectComponent',
                      'wrapPhase',
                      'iono',
                      'rangeOffset',
                      'azimuthOffset']

datasetUnitDict = {'unwrapPhase'        :'radian',
                   'coherence'          :'1',
                   'connectComponent'   :'1',
                   'wrapPhase'          :'radian',
                   'iono'               :'radian',  #not sure
                   'rangeOffset'        :'1',
                   'azimuthOffset'      :'1',

                   'height'             :'m',
                   'latitude'           :'degree',
                   'longitude'          :'degree',
                   'rangeCoord'         :'1',
                   'azimuthCoord'       :'1',
                   'incidenceAngle'     :'degree',
                   'headingAngle'       :'degree',
                   'slantRangeDistance' :'m',
                   'shadowMask'         :'1',
                   'waterMask'          :'1',
                   'commonMask'         :'1',
                   'bperp'              :'m',

                   'raw'                :'m',
                   'troposphericDelay'  :'m',
                   'topographicResidual':'m',
                   'ramp'               :'m',
                   'displacement'       :'m',

                   'velocity'           :'m/year',
                   'acceleration'       :'m/year^2',
                   'mask'               :'1',

                   '.unw'               :'radian',
                   '.int'               :'radian',
                   '.flat'              :'radian',
                   '.cor'               :'1',
                   '.dem'               :'m',
                   '.hgt'               :'m',
                   '.hgt_sim'           :'m',
                  }


########################################################################################
class timeseries:
    '''
    Time-series object for displacement of a set of SAR images from the same platform and track.
    It contains a "timeseries" group and three datasets: date, bperp and timeseries.

    /                Root level
    Attributes       Dictionary for metadata
    /timeseries      3D array of float32 in size of (n, l, w) in meter.
    /date            1D array of string  in size of (n,     ) in YYYYMMDD format
    /bperp           1D array of float32 in size of (n,     ) in meter. (optional)
    '''
    def __init__(self, file=None):
        self.file = file
        self.name = 'timeseries'

    def close(self, printMsg=True):
        try:
            self.f.close()
            if printMsg:
                print('close timeseries file: {}'.format(os.path.basename(self.file)))
        except:
            pass

    def open(self, printMsg=True):
        if printMsg:
            print('open {} file: {}'.format(self.name, os.path.basename(self.file)))
        self.get_metadata()
        self.get_size()
        self.numPixel = self.length * self.width

        with h5py.File(self.file, 'r') as f:
            dates = f['date'][:]
            try:
                self.pbase = f['bperp'][:]
                self.pbase -= self.pbase[self.refIndex]
            except:
                self.pbase = None
        self.times = np.array([dt(*time.strptime(i.decode('utf8'),"%Y%m%d")[0:5]) for i in dates])
        self.tbase = np.array([i.days for i in self.times - self.times[self.refIndex]], dtype=np.int16)
        self.dateList = [i.decode('utf8') for i in dates]
        self.yearList = [i.year + (i.timetuple().tm_yday-1)/365.25 for i in self.times]  #list of float for year, 2014.95
        self.datasetList = list(self.dateList)

    def get_metadata(self):
        with h5py.File(self.file, 'r') as f:
            self.metadata = dict(f.attrs)
            dates = f['date'][:]
        for key, value in self.metadata.items():
            try:     self.metadata[key] = value.decode('utf8')
            except:  self.metadata[key] = value
        ## ref_date/index
        dateList = [i.decode('utf8') for i in dates]
        if 'REF_DATE' not in self.metadata.keys():
            self.metadata['REF_DATE'] = dateList[0]
        self.refIndex = dateList.index(self.metadata['REF_DATE'])
        return self.metadata

    def get_size(self):
        with h5py.File(self.file, 'r') as f:
            self.numDate, self.length, self.width = f[self.name].shape
        return self.numDate, self.length, self.width

    def read(self, datasetName=None, box=None, printMsg=True):
        '''Read dataset from timeseries file
        Parameters: self : timeseries object
                    datasetName : (list of) string in YYYYMMDD format
                    box : tuple of 4 int, indicating x0,y0,x1,y1 of range
        Returns:    data : 2D or 3D dataset
        Examples:   from pysar.objects import timeseries
                    tsobj = timeseries('timeseries_ECMWF_demErr.h5')
                    data = tsobj.read(datasetName='20161020')
                    data = tsobj.read(datasetName='20161020', box=(100,300,500,800))
                    data = tsobj.read(datasetName=['20161020','20161026','20161101'])
                    data = tsobj.read(box=(100,300,500,800))
        '''
        if printMsg:
            print('reading {} data from file: {} ...'.format(self.name, self.file))
        self.open(printMsg=False)

        with h5py.File(self.file, 'r') as f:
            ds = f[self.name]
            if isinstance(ds, h5py.Group):    #support for old pysar files
                ds = ds[self.name]

            ##Get dateFlag - mark in time/1st dimension
            dateFlag = np.zeros((self.numDate), dtype=np.bool_)
            if not datasetName:
                dateFlag[:] = True
            elif isinstance(datasetName, str):
                dateFlag[self.dateList.index(datasetName)] = True
            elif isinstance(datasetName, list):
                for e in datasetName:
                    dateFlag[self.dateList.index(e)] = True

            ##Get Index in space/2_3 dimension
            if box is None:
                box = [0,0,self.width,self.length]
            data = ds[dateFlag, box[1]:box[3], box[0]:box[2]]
        data = np.squeeze(data)
        return data

    def write2hdf5(self, data, outFile=None, dates=None, bperp=None, metadata=None, refFile=None):
        '''
        Parameters: data  : 3D array of float32
                    dates : 1D array/list of string in YYYYMMDD format
                    bperp : 1D array/list of float32 (optional)
                    metadata : dict
                    outFile : string
                    refFile : string
        Returns: outFile : string
        Examples:
            from pysar.objects import timeseries

            ##Generate a new timeseries file
            tsobj = timeseries('timeseries.h5')
            timeseries.write(data, dates=dateList, bperp=bperp, metadata=atr)

            ##Generate a timeseries with same attributes and same date/bperp info
            tsobj = timeseries('timeseries_demErr.h5')
            timeseries.write(data, refFile='timeseries.h5')
        '''
        if not outFile:
            outFile = self.file
        if refFile:
            refobj = timeseries(refFile)
            refobj.open(printMsg=False)
            if metadata is None:
                metadata = refobj.metadata
            if dates is None:
                dates = refobj.dateList
            if bperp is None:
                bperp = refobj.pbase
            refobj.close(printMsg=False)
        data = np.array(data, dtype=np.float32)
        dates = np.array(dates, dtype=np.string_)
        bperp = np.array(bperp, dtype=np.float32)
        metadata['FILE_TYPE'] = self.name

        ##### 3D dataset - timeseries
        print('create timeseries HDF5 file: {} with w mode'.format(outFile))
        f = h5py.File(outFile,'w')
        print('create dataset /timeseries of {:<10} in size of {}'.format(str(data.dtype), data.shape))
        dset = f.create_dataset('timeseries', data=data, chunks=True)

        dset.attrs['Title'] = 'timeseries'
        dset.attrs['MissingValue'] = FLOAT_ZERO
        dset.attrs['Units'] = 'm'
        dset.attrs['_FillValue'] = FLOAT_ZERO
        dset.attrs['MaxValue'] = np.nanmax(data)  #facilitate disp_min/max for mutiple subplots in view.py
        dset.attrs['MinValue'] = np.nanmin(data)  #facilitate disp_min/max for mutiple subplots in view.py

        ##### 3D dataset - date / bperp
        print('create dataset /dates      of {:<10} in size of {}'.format(str(dates.dtype), dates.shape))
        dset = f.create_dataset('date', data=dates, chunks=True)

        if bperp.shape != ():
            print('create dataset /bperp      of {:<10} in size of {}'.format(str(bperp.dtype), bperp.shape))
            dset = f.create_dataset('bperp', data=bperp, chunks=True)

        #### Attributes
        for key, value in metadata.items():
            f.attrs[key] = str(value)

        f.close()
        print('finished writing to {}'.format(outFile))
        return outFile

    def timeseries_std(self, maskFile=None, outFile=None):
        '''Calculate the standard deviation (STD) for each epoch,
           output result to a text file.
        '''
        #Calculate STD
        data = self.read()
        if maskFile:
            mask = singleDataset(maskFile).read()
            print('read mask from file: '+maskFile)
            data[:,mask==0] = np.nan
        self.std = np.nanstd(data, axis=(1,2))

        #Write text file
        header  = 'Standard Deviation in space for each epoch of timeseries\n'
        header += 'Timeseries file: {}\n'.format(self.file)
        header += 'Mask file: {}\n'.format(maskFile)
        header += 'Date\t\tSTD (m)'
        if not outFile:
            outFile = os.path.join(os.path.dirname(os.path.abspath(self.file)),\
                                   'std_{}.txt'.format(os.path.splitext(os.path.basename(self.file))[0]))
        np.savetxt(outFile, np.hstack((np.array(self.dateList).reshape(-1,1), self.std.reshape(-1,1))),\
                   fmt='%s', delimiter='\t', header=header)
        print('save timeseries STD to text file: {}'.format(outFile))
        return outFile

    def timeseries_rms(self, maskFile=None, outFile=None):
        '''Calculate the Root Mean Square for each epoch of input timeseries file
            and output result to a text file.
        '''
        #Calculate RMS
        data = self.read()
        if maskFile and os.path.isfile(maskFile):
            print('read mask from file: '+maskFile)
            mask = singleDataset(maskFile).read()
            data[:,mask==0] = np.nan
        self.rms = np.sqrt(np.nanmean(np.square(data), axis=(1,2)))

        #Write text file
        header  = 'Root Mean Square in space for each epoch of timeseries\n'
        header += 'Timeseries file: {}\n'.format(self.file)
        header += 'Mask file: {}\n'.format(maskFile)
        header += 'Date\t\tRMS (m)'
        if not outFile:
            outFile = os.path.join(os.path.dirname(os.path.abspath(self.file)),\
                                   'rms_{}.txt'.format(os.path.splitext(os.path.basename(self.file))[0]))
        np.savetxt(outFile, np.hstack((np.array(self.dateList).reshape(-1,1), self.rms.reshape(-1,1))),\
                   fmt='%s', delimiter='\t', header=header)
        print('save timeseries RMS to text file: {}'.format(outFile))
        return outFile

    def spatial_average(self, maskFile=None, box=None):
        self.open(printMsg=False)
        data = self.read(box=box)
        if maskFile and os.path.isfile(maskFile):
            print('read mask from file: '+maskFile)
            mask = singleDataset(maskFile).read(box=box)
            data[:,mask==0] = np.nan
        dmean = np.nanmean(data, axis=(1,2))
        return dmean, self.dateList

    def temporal_average(self):
        print('calculating the temporal average of timeseries file: {}'.format(self.file))
        self.open(printMsg=False)
        data = self.read()
        dmean = np.nanmean(data, axis=0)
        return dmean


########################################################################################
class geometry:
    ''' Geometry object.
    /                        Root level
    Attributes               Dictionary for metadata. 'X/Y_FIRST/STEP' attribute for geocoded.
    /height                  2D array of float32 in size of (l, w   ) in meter.
    /latitude (azimuthCoord) 2D array of float32 in size of (l, w   ) in degree.
    /longitude (rangeCoord)  2D array of float32 in size of (l, w   ) in degree.
    /incidenceAngle          2D array of float32 in size of (l, w   ) in degree.
    /slantRangeDistance      2D array of float32 in size of (l, w   ) in meter.
    /headingAngle            2D array of float32 in size of (l, w   ) in degree. (optional)
    /shadowMask              2D array of bool    in size of (l, w   ).           (optional)
    /waterMask               2D array of bool    in size of (l, w   ).           (optional)
    /bperp                   3D array of float32 in size of (n, l, w) in meter   (optional)
    /date                    1D array of string  in size of (n,     ) in YYYYMMDD(optional)
    ...
    '''
    def __init__(self, file=None):
        self.file = file
        self.name = 'geometry'

    def close(self, printMsg=True):
        try:
            self.f.close()
            if printMsg:
                print('close geometry file: {}'.format(os.path.basename(self.file)))
        except: 
            pass

    def open(self, printMsg=True):
        if printMsg:
            print('open {} file: {}'.format(self.name, os.path.basename(self.file)))
        self.get_metadata()
        self.get_size()
        self.numPixel = self.length * self.width
        self.geocoded = False
        if 'Y_FIRST' in self.metadata.keys():
            self.geocoded = True

        with h5py.File(self.file,'r') as f:
            self.datasetNames = list(set(f.keys()) & set(geometryDatasetNames))
            self.datasetList = list(self.datasetNames)
            if 'bperp' in f.keys():
                self.dateList = [i.decode('utf8') for i in f['date'][:]]
                self.numDate = len(self.dateList)
                ##Update bperp datasetNames
                try: self.datasetList.remove('bperp')
                except: pass
                self.datasetList += ['bperp-'+d for d in self.dateList]
            else:
                self.dateList = None

    def get_size(self):
        with h5py.File(self.file, 'r') as f:
            self.length, self.width = f[geometryDatasetNames[0]].shape
        return self.length, self.width

    def get_metadata(self):
        with h5py.File(self.file, 'r') as f:
            self.metadata = dict(f.attrs)
        for key, value in self.metadata.items():
            try:     self.metadata[key] = value.decode('utf8')
            except:  self.metadata[key] = value
        return self.metadata

    def read(self, datasetName=geometryDatasetNames[0], box=None, printMsg=True):
        '''Read 2D / 3D dataset with bounding box in space
        Parameters: datasetName : string, to point to specific 2D dataset, e.g.:
                        height
                        incidenceAngle
                        bperp
                        ...
                        bperp-20161020
                        bperp-20161026
                        bperp-...
                    box : tuple of 4 int, for (x0,y0,x1,y1)
                    printMsg : bool
        Returns: data : 2D or 3D array
        Example:
            obj = geometry('./INPUTS/geometryRadar.h5')
            obj.read(datasetName='height')
            obj.read(datasetName='incidenceAngle')
            obj.read(datasetName='bperp')
            obj.read(datasetName='bperp-20161020')
        '''
        self.open(printMsg=False)
        if box is None:
            box = (0,0,self.width,self.length)
        if datasetName is None:
            datasetName = geometryDatasetNames[0]
        datasetName = datasetName.split('-')
        if printMsg:
            print('reading {} data from file: {} ...'.format(datasetName[0], self.file))

        with h5py.File(self.file, 'r') as f:
            dset = f[datasetName[0]]
            if len(dset.shape) == 2:
                data = dset[box[1]:box[3], box[0]:box[2]]
            elif len(dset.shape) == 3:      ## bperp
                if len(datasetName) == 1:
                    data = dset[:, box[1]:box[3], box[0]:box[2]]
                else:
                    data = dset[self.dateList.index(datasetName[1]), box[1]:box[3], box[0]:box[2]]
                    data = np.squeeze(data)
        return data







########################################################################################
class ifgramStack:
    ''' Interferograms Stack object.
    /                  Root level group name
    Attributes         Dictionary for metadata
    /date              2D array of string  in size of (m, 2   ) in YYYYMMDD format for master and slave date
    /bperp             1D array of float32 in size of (m,     ) in meter.
    /dropIfgram        1D array of bool    in size of (m,     ) with 0 for drop and 1 for keep
    /unwrapPhase       3D array of float32 in size of (m, l, w) in radian.
    /coherence         3D array of float32 in size of (m, l, w).
    /connectComponent  3D array of int16   in size of (m, l, w).           (optional)
    /wrapPhase         3D array of float32 in size of (m, l, w) in radian. (optional)
    /rangeOffset       3D array of float32 in size of (m, l, w).           (optional)
    /azimuthOffset     3D array of float32 in size of (m, l, w).           (optional)
    '''
    def __init__(self, file=None):
        self.file = file
        self.name = 'ifgramStack'

    def close(self, printMsg=True):
        try:
            self.f.close()
            if printMsg:
                print('close {} file: {}'.format(self.name, os.path.basename(self.file)))
        except:
            pass

    def open(self, printMsg=True):
        '''
        Time format/rules:
            All datetime.datetime objects named with time
            All string in YYYYMMDD        named with date (following roipac)
        '''
        if printMsg:
            print('open {} file: {}'.format(self.name, os.path.basename(self.file)))
        self.get_metadata()
        self.get_size()
        self.read_datetimes()
        self.numPixel = self.length * self.width

        with h5py.File(self.file, 'r') as f:
            self.dropIfgram = f['dropIfgram'][:]
            self.pbaseIfgram = f['bperp'][:]
            self.datasetNames = list(set(f.keys()) & set(ifgramDatasetNames))
        self.date12List = ['{}_{}'.format(i,j) for i,j in zip(self.mDates,self.sDates)]
        self.tbaseIfgram = np.array([i.days for i in self.sTimes - self.mTimes], dtype=np.int16)

        #Get datasetList for self.read()
        self.datasetList = []
        for dsName in self.datasetNames:
            self.datasetList += ['{}-{}'.format(dsName,i) for i in self.date12List]

        #Time in timeseries domain
        self.dateList = self.get_date_list(dropIfgram=False)
        self.numDate = len(self.dateList)

    def get_metadata(self):
        with h5py.File(self.file, 'r') as f:
            self.metadata = dict(f.attrs)
        for key, value in self.metadata.items():
            try:     self.metadata[key] = value.decode('utf8')
            except:  self.metadata[key] = value
        return self.metadata

    def get_size(self):
        with h5py.File(self.file, 'r') as f:
            self.numIfgram, self.length, self.width = f[ifgramDatasetNames[0]].shape
        return self.numIfgram, self.length, self.width

    def read_datetimes(self):
        '''Read master/slave dates into array of datetime.datetime objects'''
        with h5py.File(self.file, 'r') as f:
            dates = f['date'][:]
        self.mDates = np.array([i.decode('utf8') for i in dates[:,0]])
        self.sDates = np.array([i.decode('utf8') for i in dates[:,1]])
        self.mTimes = np.array([dt(*time.strptime(i,"%Y%m%d")[0:5]) for i in self.mDates])
        self.sTimes = np.array([dt(*time.strptime(i,"%Y%m%d")[0:5]) for i in self.sDates])

    def read(self, datasetName=ifgramDatasetNames[0], box=None, printMsg=True, dropIfgram=False):
        '''Read 3D dataset with bounding box in space
        Parameters: datasetName : string, to point to specific 2D dataset, e.g.:
                        unwrapPhase
                        coherence
                        connectComponent
                        ...
                        unwrapPhase-20161020_20161026
                        unwrapPhase-...
                        coherence-20161020_20161026
                        ...
                    box : tuple of 4 int, for (x0,y0,x1,y1)
                    printMsg : bool
        Returns: data : 2D or 3D array
        Example:
            obj = ifgramStack('./INPUTS/ifgramStack.h5')
            obj.read(datasetName='unwrapPhase')
            obj.read(datasetName='coherence')
            obj.read(datasetName='unwrapPhase-20161020_20161026')
        '''
        self.get_size()
        date12List = self.get_date12_list(dropIfgram=dropIfgram)
        if box is None:
            box = (0,0,self.width,self.length)
        if datasetName is None:
            datasetName = ifgramDatasetNames[0]

        datasetName = datasetName.split('-')
        with h5py.File(self.file, 'r') as f:
            dset = f[datasetName[0]]
            if len(datasetName) == 1:
                if dropIfgram:
                    data = dset[f['dropIfgram'][:], box[1]:box[3], box[0]:box[2]]
                else:
                    data = dset[:, box[1]:box[3], box[0]:box[2]]
            else:
                data = dset[date12List.index(datasetName[1]), box[1]:box[3], box[0]:box[2]]
                data = np.squeeze(data)
        return data

    def spatial_average(self, datasetName=ifgramDatasetNames[1], maskFile=None, box=None):
        if datasetName is None:
            datasetName = ifgramDatasetNames[1]
        print('calculating spatial average of {} in file {} ...'.format(datasetName, self.file))
        if maskFile and os.path.isfile(maskFile):
            print('read mask from file: '+maskFile)
            mask = singleDataset(maskFile).read(box=box)
        else:
            maskFile = None

        with h5py.File(self.file, 'r') as f:
            dset = f[datasetName]
            numIfgram = dset.shape[0]
            dmean = np.zeros((numIfgram), dtype=np.float32)
            for i in range(numIfgram):
                data = dset[i, box[1]:box[3], box[0]:box[2]]
                if maskFile:
                    data[mask==0] = np.nan
                dmean[i] = np.nanmean(data)
                sys.stdout.write('\rreading interferogram {}/{} ...'.format(i+1, numIfgram))
                sys.stdout.flush()
            print('')
        return dmean, self.date12List

    ##### Functions considering dropIfgram value
    def get_date12_list(self, dropIfgram=True):
        with h5py.File(self.file, 'r') as f:
            dates = f['date'][:]
            if dropIfgram:
                dates = dates[f['dropIfgram'][:],:]
        mDates = np.array([i.decode('utf8') for i in dates[:,0]])
        sDates = np.array([i.decode('utf8') for i in dates[:,1]])
        date12List = ['{}_{}'.format(i,j) for i,j in zip(mDates, sDates)]
        return date12List

    def get_date_list(self, dropIfgram=False):
        with h5py.File(self.file, 'r') as f:
            dates = f['date'][:]
            if dropIfgram:
                dates = dates[f['dropIfgram'][:],:]
        mDates = [i.decode('utf8') for i in dates[:,0]]
        sDates = [i.decode('utf8') for i in dates[:,1]]
        dateList = sorted(list(set(mDates + sDates)))
        return dateList

    def nonzero_mask(self, datasetName=None, printMsg=True, dropIfgram=True):
        '''Return the common mask of pixels with non-zero value in dataset of all ifgrams.
           Ignoring dropped ifgrams
        '''
        self.open(printMsg=False)
        with h5py.File(self.file, 'r') as f:
            if datasetName is None:
                datasetName = [i for i in ['connectComponent','unwrapPhase'] if i in f.keys()][0]
            print('calculate the common mask of pixels with non-zero {} value'.format(datasetName))

            dset = f[datasetName]
            mask = np.ones(dset.shape[1:3], dtype=np.bool_)
            dropIfgramFlag = np.ones(dset.shape[0], dtype=np.bool_)
            if dropIfgram:
                dropIfgramFlag = self.dropIfgram
            num2read = np.sum(dropIfgramFlag)
            idx2read = np.where(dropIfgramFlag)[0]
            for i in range(num2read):     #Loop to save memory usage
                data = dset[idx2read[i],:,:]
                mask[data==0.] = 0
                mask[np.isnan(data)] = 0
                sys.stdout.write('\rreading interferogram {}/{} ...'.format(i+1, num2read))
                sys.stdout.flush()
            print('')
        return mask

    def temporal_average(self, datasetName=ifgramDatasetNames[1], dropIfgram=True):
        self.open(printMsg=False)
        if datasetName is None:
            datasetName = ifgramDatasetNames[0]
        print('calculate the temporal average of {} in file {} ...'.format(datasetName, self.file))
        if datasetName == 'unwrapPhase':
            phase2range = -1 * float(self.metadata['WAVELENGTH']) / (4.0 * np.pi)
            tbaseIfgram = self.tbaseIfgram / 365.25

        with h5py.File(self.file, 'r') as f:
            dset = f[datasetName]
            dmean = np.zeros(dset.shape[1:3], dtype=np.float32)
            dropIfgramFlag = np.ones(dset.shape[0], dtype=np.bool_)
            if dropIfgram:
                dropIfgramFlag = self.dropIfgram
            num2read = np.sum(dropIfgramFlag)
            idx2read = np.where(dropIfgramFlag)[0]
            for i in range(num2read):
                data = dset[idx2read[i],:,:]
                if datasetName == 'unwrapPhase':
                    data *= (phase2range * (1./tbaseIfgram[idx2read[i]]))
                dmean += data
                sys.stdout.write('\rreading interferogram {}/{} ...'.format(i+1, num2read))
                sys.stdout.flush()
            print('')
        dmean /= np.sum(self.dropIfgram)
        return dmean

    ##### Functions for Network Inversion
    def get_design_matrix(self, refDate=None, dropIfgram=True):
        '''Return design matrix of the input ifgramStack, ignoring dropped ifgrams'''
        ## Date info
        date12List = self.get_date12_list(dropIfgram=dropIfgram)
        mDates = [i.split('_')[0] for i in date12List]
        sDates = [i.split('_')[1] for i in date12List]
        dateList = sorted(list(set(mDates + sDates)))
        dates = [dt(*time.strptime(i,"%Y%m%d")[0:5]) for i in dateList]
        tbase = np.array([(i - dates[0]).days for i in dates])
        numIfgram = len(date12List)
        numDate = len(dateList)

        ## calculate design matrix
        A = np.zeros((numIfgram, numDate))
        B = np.zeros(A.shape)
        for i in range(numIfgram):
            m_idx, s_idx = [dateList.index(j) for j in date12List[i].split('_')]
            A[i, m_idx] = -1
            A[i, s_idx] = 1
            B[i, m_idx:s_idx] = tbase[m_idx+1:s_idx+1] - tbase[m_idx:s_idx]

        ## Remove reference date as it can not be resolved
        if not refDate:
            refDate = dateList[0]
        refIndex = dateList.index(refDate)
        A = np.hstack((A[:,0:refIndex], A[:,(refIndex+1):]))
        B = B[:,:-1]
        return A, B

    def get_perp_baseline_timeseries(self, dropIfgram=True):
        '''Get spatial perpendicular baseline in timeseries from ifgramStack, ignoring dropped ifgrams'''
        ## Get tbaseDiff
        date12List = self.get_date12_list(dropIfgram=dropIfgram)
        mDates = [i.split('_')[0] for i in date12List]
        sDates = [i.split('_')[1] for i in date12List]
        dateList = sorted(list(set(mDates + sDates)))
        dates = [dt(*time.strptime(i,"%Y%m%d")[0:5]) for i in dateList]
        tbaseDiff = np.diff([(i - dates[0]).days for i in dates]).flatten()

        B = self.get_design_matrix(dropIfgram=dropIfgram)[1]
        B_inv = np.linalg.pinv(B)
        with h5py.File(self.file, 'r') as f:
            pbaseIfgram = f['bperp'][:]
            if dropIfgram:
                pbaseIfgram = pbaseIfgram[f['dropIfgram'][:]]
        pbaseRate = np.dot(B_inv, pbaseIfgram)
        pbaseTimeseries = np.concatenate((np.array([0.],dtype=np.float32), np.cumsum([pbaseRate * tbaseDiff])))
        return pbaseTimeseries

    def update_drop_ifgram(self, date12List_to_drop):
        '''Update dropIfgram dataset based on input date12List_to_drop'''
        if date12List_to_drop is None:
            return
        date12ListAll = self.get_date12_list(dropIfgram=False)
        with h5py.File(self.file, 'r+') as f:
            print('open file {} with r+ mode'.format(self.file))
            print('update HDF5 dataset "/dropIfgram".')
            f['dropIfgram'][:] = np.array([i not in date12List_to_drop for i in date12ListAll], dtype=np.bool_)



########################################################################################
class singleDataset:
    def __init__(self, file=None):
        self.file = file

    def close(self, printMsg=True):
        try:
            self.f.close()
            if printMsg:
                print('close file: {}'.format(os.path.basename(self.file)))
        except:
            pass

    def read(self, box=None):
        self.f = h5py.File(self.file, 'r')
        k = list(self.f.keys())[0]
        data = self.f[k][:]
        if box is not None:
            data = data[box[1]:box[3],box[0]:box[2]]
        return data



########################################################################################
class HDFEOS:
    '''
    Time-series object in HDF-EOS5 format for Univ of Miami's InSAR Time-series Web Viewer (http://insarmaps.miami.edu)
    It contains a "timeseries" group and three datasets: date, bperp and timeseries.

    /HDFEOS                           Root level group name
        /GRIDS                        2nd level group name for products in geo coordinates
            Attributes                metadata in dict.
            /timeseries               3rd level group name for time-series InSAR product
                /date                 1D array of string  in size of (n,     ) in YYYYMMDD format.
                /bperp                1D array of float32 in size of (n,     ) in meter
                /temporalCoherence    2D array of float32 in size of (   l, w).
                /mask                 2D array of bool_   in size of (   l, w).
                /raw                  3D array of float32 in size of (n, l, w) in meter
                /troposphericDelay    3D array of float32 in size of (n, l, w) in meter
                /topographicResidual  3D array of float32 in size of (n, l, w) in meter
                /ramp                 3D array of float32 in size of (n, l, w) in meter
                /displacement         3D array of float32 in size of (n, l, w) in meter
            /geometry                 3rd level group name for geometry data
                /height               2D array of float32 in size of (   l, w) in meter.
                /incidenceAngle       2D array of float32 in size of (   l, w) in degree.
                /slantRangeDistance   2D array of float32 in size of (   l, w) in meter.
                /azimuthCoord         2D array of float32 in size of (   l, w) in degree.
                /rangeCoord           2D array of float32 in size of (   l, w) in degree.
                /headingAngle         2D array of float32 in size of (   l, w) in degree. (optional)
                /shadowMask           2D array of bool    in size of (   l, w).           (optional)
                /waterMask            2D array of bool    in size of (   l, w).           (optional)
                /bperp                3D array of float32 in size of (n, l, w) in meter.  (optional)
        /SWATHS
            Attributes
            /ifgramStack
                ...
            /geometry
                ...
    '''
    def __init__(self, file=None):
        self.file = file
        self.name = 'HDFEOS'

    def close(self, printMsg=True):
        try:
            self.f.close()
            if printMsg:
                print('close timeseries file: {}'.format(os.path.basename(self.file)))
        except:
            pass









