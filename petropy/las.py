# -*- coding: utf-8 -*-
"""
Las

The the purpose of this module is to provide methods for reading stand alone raw
las files. This is a subclass of Log, allowing for all calculations to be
performed after reading the raw data.

"""

import os
import sys
import numpy as np
import pandas as pd

from log import Log, Parameter

class Las(Log):
    """
    LAS class for working with stand alone las files

    The Las class is a subclass of Log and allows for reading of raw and/or
    stand alone las files.

    Parameters
    ----------
    las_file : file
        file path to .las file to read

    Raises
    ------
    ValueError
        If NULL not found in header

    ValueError
        If inconsistent number of columns in wrapped data between depth steps

    Examples
    --------
    >>> import os
    >>> import petro as ptr
    >>> file_dir = os.path.dirname(__file__)
    >>> read_path = os.path.join(file_dir, 'my_well.las')
    >>> las = ptr.Las(read_path)

    See Also
    --------
    Log
        Parent class of Las
    log_data
        Retrives Las object for specified source area

    """

    def __init__(self, las_file):
        """
        Reads las file from las_file path.

        Initializing checks for the las_file path. If found, it parses header
        data, storing correct values in the parent Log attributes.

        """

        if not os.path.isfile(las_file):
            raise ValueError('LAS file not found at path: %s' % las_file)

        with open(las_file, 'r') as f:
            lines = f.readlines()

        if sys.version_info[0] < 3:
            super(Las, self).__init__()
        else:
            super().__init__()

        VERSION = False
        WELL = False
        PARAMETER = False
        CURVE = False
        DATA = False
        for i, line in enumerate(lines):

            if line[0] == '#': continue

            ### check for change in data type @##
            if '~VERSION' in line.upper():
                VERSION = True
                WELL = False
                PARAMETER = False
                CURVE = False
                DATA = False
            elif '~WELL' in line.upper():
                VERSION = False
                WELL = True
                PARAMETER = False
                CURVE = False
                DATA = False
            elif '~PARAMETER' in line.upper():
                VERSION = False
                WELL = False
                PARAMETER = True
                CURVE = False
                DATA = False
            elif '~CURVE' in line.upper():
                VERSION = False
                WELL = False
                PARAMETER = False
                CURVE = True
                DATA = False
            elif '~A' in line.upper():
                VERSION = False
                WELL = False
                PARAMETER = False
                CURVE = False
                DATA = True

                ### check if curve names are on this row ###

            ### set las file properties ###
            elif VERSION:
                paramater = Parameter(line = line)
                self.version_parameters.append(paramater.name)
                self.version_values[paramater.name] = paramater

            elif WELL:
                paramater = Parameter(line = line)
                self.well_parameters.append(paramater.name)
                self.well_values[paramater.name] = paramater

            elif PARAMETER:
                paramater = Parameter(line = line)
                self.parameter_parameters.append(paramater.name)
                self.parameter_values[paramater.name] = paramater

            elif CURVE:
                paramater = Parameter(line = line)
                self.curve_parameters.append(paramater.name)
                self.curve_values[paramater.name] = paramater

            elif DATA:
                DATA = False
                data = lines[i:]
                break

        cleaned_data = []
        cleaned_rows_len = [] # for use if las data is wrapped
        for row in data:
            values = row.strip().split(' ')
            cleaned_row = list(filter(lambda x: x != '', values))
            cleaned_data.append(cleaned_row)
            cleaned_rows_len.append(len(cleaned_row))

        if 'WRAP' in self.version_values:
            if 'YES' in self.version_values['WRAP'].value:
                self.version_values['WRAP'].value = 'NO'
                wrapped = True
            elif 'YES' in self.version_values['WRAP'].right_value:
                self.version_values['WRAP'].right_value = 'NO'
                wrapped = True
            elif 'YES' in self.version_values['WRAP'].des:
                self.version_values['WRAP'].des = 'NO'
                wrapped = True
            else:
                wrapped = False

        if wrapped:
            data_arr = np.asarray(cleaned_data)
            rows_len_arr = np.asarray(cleaned_rows_len)
            data_df = pd.DataFrame(cleaned_data)

            unique_lengths = np.unique(np.asarray(rows_len_arr))
            if len(unique_lengths) == 3:
                depth_indexes = np.where(rows_len_arr == 1)[0]
                cleaned_data = np.vstack(np.take(data_arr, depth_indexes))
                for d in range(depth_indexes[0] + 1, depth_indexes[1]):
                    added_rows = data_df.iloc[depth_indexes + d].as_matrix()
                    cleaned_data = np.concatenate((cleaned_data, added_rows), axis = 1)

            elif len(unique_lengths) == 2:
                # use only even indexes as the odd single row values contain
                # wrapped data and are not depth values
                depth_indexes = np.where(rows_len_arr == 1)[0][::2]
                cleaned_data = np.vstack(np.take(data_arr, depth_indexes))
                for d in range(depth_indexes[0] + 1, depth_indexes[1]):
                    added_rows = data_df.iloc[depth_indexes + d].as_matrix()
                    cleaned_data = np.concatenate((cleaned_data, added_rows), axis = 1)

            else:
                raise ValueError('Inconsistent values for wrapped data.')

            deleted_columns = []
            for column, value in enumerate(cleaned_data[0]):
                if value is None:
                    deleted_columns.append(column)
            cleaned_data = np.delete(cleaned_data, deleted_columns, 1)

        self.curve_df = pd.DataFrame(cleaned_data, columns = self.curve_parameters)

        for column in self.curve_df.columns:
            self.curve_df[column] = self.curve_df[column].astype(float)

        ### get uwi from parameters if available ###
        if 'UWI' in self.well_parameters:
            uwi_param = self.well_values['UWI']
        elif 'uwi' in self.well_parameters:
            uwi_param = self.well_values['uwi']
        elif 'API' in self.well_parameters:
            uwi_param = self.well_values['API']
        elif 'api' in self.well_parameters:
            uwi_param = self.well_values['api']
        else:
            uwi_param = None

        if uwi_param is not None:
            if 'WELL' not in uwi_param.value.upper() and 'UNIQUE' not in uwi_param.value.upper() and len(uwi_param.value) > 0:
                self.uwi = uwi_param.value.replace('-', '')
            elif 'WELL' not in uwi_param.des.upper() and 'UNIQUE' not in uwi_param.des.upper() and len(uwi_param.des) > 0:
                self.uwi = uwi_param.des.replace('-', '')
            elif 'WELL' not in uwi_param.right_value.upper() and 'UNIQUE' not in uwi_param.right_value.upper() and len(uwi_param.right_value) > 0:
                self.uwi = uwi_param.right_value.replace('-', '')
            else:
                self.uwi = None
        else:
            self.uwi = None

        if 'NULL' in self.well_parameters:
            if len(self.well_values['NULL'].value) > 0:
                self.null = float(self.well_values['NULL'].value)
            elif len(self.well_values['NULL'].right_value) > 0:
                self.null = float(self.well_values['NULL'].right_value)
            else:
                raise ValueError('Null Value not found in Null Parameter:\n%s'\
                                 % self.well_values['NULL'].to_string())

        elif 'null' in self.well_parameters:
            if len(self.well_values['null'].value) > 0:
                self.null = float(self.well_values['null'].value)
            elif len(self.well_values['null'].right_value) > 0:
                self.null = float(self.well_values['null'].right_value)
            else:
                raise ValueError('Null Value not found in Null Parameter:\n%s'\
                                 % self.well_values['null'].to_string())

        else:
            print('Check las file at %s' % las_file)
            raise ValueError('Null Value not found in well header data.')

        self.precondition()
