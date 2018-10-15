import pandas as __pd
import numpy as __np

import arcpy as __arcpy
from arcgis_helpers.__logger import _logger


def __convert_dataframe_to_np(data_frame_):
    ar = []
    fld_var = []
    for col, type_v in zip(data_frame_.columns, data_frame_.dtypes):
        var_vals = data_frame_[col].values
        if type_v == 'datetime64[ns]':
            ar.append(tuple(var_vals.astype("M8[us]")))
            fld_var.append((str(col.replace(" ", "")), "M8[us]"))
        elif type_v == 'object':
            mx_len = max(__np.vectorize(len)(data_frame_[col]))
            if mx_len > 255:
                mx_len = 255
            tp = "|S{}".format(mx_len)
            ar.append(tuple(var_vals.astype(tp)))
            fld_var.append((str(col.replace(" ", "")), tp))
        else:
            ar.append(tuple(var_vals))
            fld_var.append((str(col.replace(" ", "")), type_v))

    values = zip(*ar)
    fields = fld_var

    # print(values)
    # print(fields)

    return __np.array(values, dtype=fields)


def dataframe_to_arctable(data_frame_obj, output_location):
    np_data = __convert_dataframe_to_np(data_frame_obj)
    __arcpy.da.NumPyArrayToTable(np_data, output_location)


def arctable_to_dataframe(feature_path, fields=None, where_clause="",
                          skip_nulls=False, null_value=None):
    if fields is None:
        fields = ["*"]
    x = __arcpy.da.TableToNumPyArray(feature_path, fields, where_clause,
                                   skip_nulls, null_value)
    x = __drop_shape_field(x)
    df = __pd.DataFrame(x)
    return df


def arcfeature_to_dataframe(feature_path, field_names=None, where_clause="",
                            spatial_reference=None, explode_to_points=False,
                            skip_nulls=False, null_value=None):
    if field_names is None:
        field_names = ["*"]
    x = __arcpy.da.FeatureClassToNumPyArray(in_table=feature_path,
                                          field_names=field_names,
                                          where_clause=where_clause,
                                          spatial_reference=spatial_reference,
                                          explode_to_points=explode_to_points,
                                          skip_nulls=skip_nulls,
                                          null_value=null_value)
    x = __drop_shape_field(x)
    df = __pd.DataFrame(x)
    return df


def __drop_shape_field(numpy_array):
    shape_index = None
    for x in enumerate(numpy_array.dtype.names):
        if x[1].upper() == "SHAPE":
            shape_index = x[0]

    out_numpy_array = numpy_array
    if shape_index is not None:
        names = list(numpy_array.dtype.names)
        out_names = names[:shape_index] + names[shape_index + 1:]
        out_numpy_array = __pd.DataFrame(numpy_array[out_names])

    return out_numpy_array
