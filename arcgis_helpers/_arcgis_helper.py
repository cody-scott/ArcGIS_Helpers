import arcview
import arcpy

import os
import logging
import contextlib
import re

import pyperclip

from arcgis_helpers.__logger import _logger
import sys

if not hasattr(sys, 'argv'):
    sys.argv  = ['']

def feature_to_tsv_clipboard(feature, field_name=None, show_headers=True,
                             where_clause=None):
    """Get Feature from FC and copy to clipboard
    Format is TSV
    :param feature: Feature Class or Table to search
    :type feature: Feature Class or Table
    :param field_name: Field Names to build list of
    :type field_name: List of Field Names
    :param show_headers: Show header row of feature
    :type show_headers: Boolean
    :param where_clause: Where clause to apply to selection
    :type where_clause: str
    :return: TSV list of features
    :rtype: str
    """
    output_text = feature_to_tsv(feature, field_name, show_headers,
                                 where_clause)
    pyperclip.copy(output_text)
    _logger.info("copied to clipboard")
    return output_text


def feature_to_tsv(feature, field_name=None, show_headers=True,
                   where_clause=None):
    """Get Features from FC as TSV
    :param feature: Feature Class or Table to search
    :type feature: Feature Class or Table
    :param field_name: Field Names to build list of
    :type field_name: List of Field Names
    :param show_headers: Show header row of feature
    :type show_headers: Boolean
    :param where_clause: Where clause to apply to selection
    :type where_clause: str
    :return: TSV list of features
    :rtype: str
    """
    _logger.debug("asserting is headers is boolean")
    assert type(show_headers) is bool

    _logger.debug("checking field names")
    if field_name is None:
        field_name = ["*"]
    if isinstance(field_name, str):
        field_name = [field_name]

    _logger.info("Getting features")
    output_values_1 = []
    with arcpy.da.SearchCursor(feature, field_name, where_clause) as sc:
        for row in sc:
            output_values_1.append(row)

    _logger.info("building data rows")
    output_values_2 = []
    for item in output_values_1:
        output_values_2.append("\t".join(__convert_value(x) for x in item))

    _logger.info("building header rows")
    if "*" in field_name:
        field_name = [field.name for field in arcpy.ListFields(feature)]

    output_text = ""
    if show_headers:
        _logger.info("adding headers")
        output_text += "{}\n".format("\t".join(x for x in field_name))

    _logger.info("adding data to output value")
    output_text += "\n".join(x for x in output_values_2)
    return output_text


def __convert_value(value):
    out_value = None
    try:
        out_value = str(value)
    except UnicodeEncodeError as UE:
        print("Error with {}".format(value.encode('utf-8')))
        # out_value = str(value.encode('utf8'))
        out_value = "ERROR VALUE"

    return out_value


def save_text_to_file(text, output_path, file_name="OutputFile",
                      overwrite_file=False):
    """
    Export string to a file\nTXT Format
    :param text: string of text to save
    :type text: string
    :param output_path: path to save the file
    :type output_path: path
    :param file_name: Name of File -> Defaults to "OutputFile" if nothing supplied
    :type file_name: string
    :param overwrite_file: Flag to overwrite any existing file
    :type overwrite_file: Bool
    :return: None
    :rtype: None
    """
    output_file = os.path.join(output_path, "{}.txt".format(file_name))
    _logger.info("output file {}".format(output_file))

    arcpy_overwrite = arcpy.env.overwriteOutput

    if os.path.isfile(output_file) and not (overwrite_file or arcpy_overwrite):
        _logger.info("File already exists\n"
              "Please set overwrite_File = True to overwrite\n"
              "or set arcpy.env.overwriteOutput = True")
        return

    _logger.info("writing to file")
    with open(output_file, "w") as file_writer:
        file_writer.write(text)

    return


def _extent_to_polygon(extent):
    extents = [
        [extent.XMin, extent.YMin],
        [extent.XMax, extent.YMin],
        [extent.XMax, extent.YMax],
        [extent.XMin, extent.YMax]
    ]
    extent_poly = arcpy.Polygon(
        arcpy.Array([arcpy.Point(*coords) for coords in extents])
    )
    return extent_poly


@contextlib.contextmanager
def map_document_cm(mxd_path):
    """
    Context manager map document
    activates arcpy.mapping.MapDocument but allows with block
    context mangement
    :param mxd_path: path to map document
    :type mxd_path: string
    :return: yields arcpy.mapping.MapDocument
    :rtype:
    """
    _logger.info("Context managed map document {}".format(mxd_path))
    _mxd = arcpy.mapping.MapDocument(mxd_path)
    yield _mxd
    del _mxd


def get_unique_values(feature, field):
    def search_unique(feat):
        with arcpy.da.SearchCursor(feat, field) as sc:
            return [row[0] for row in sc]

    if not type(field) in [str, unicode]:
        error_msg = "Field should be a string or unicode, not {}".format(
            type(field))
        _logger.error(error_msg)
        print(error_msg)
        return

    results = []
    if type(feature) is list:
        for item in feature:
            results += search_unique(item)
    else:
        results = search_unique(feature)

    return list(set(results))


def select_by_regex(feature, fields, expression,
                    selection_type="NEW_SELECTION",
                    pre_clear_selection=True
                    ):
    """
    Allow selection of featurse based on a regex command.
    Iterates using search cursor and attempts to find pattern specified
    Since it uses search cursors it will honour selection sets applied, and will only search that selection (if there is one)
    :param feature: feature to apply selection to
    :type feature: FeatureLayer
    :param fields: single field or list of fields
    :type fields: str or list
    :param expression: expression to be applied
    :type expression: str
    :param selection_type: selection to be applied to feature
    :type selection_type:
    :param pre_clear_selection: Clear any current selection set before applying search
    :return: bool
    :rtype: list
    """

    if pre_clear_selection:
        arcpy.SelectLayerByAttribute_management(feature, "CLEAR_SELECTION")

    oid_list = _get_OID_match(feature, fields, expression)
    sql = ""
    if len(oid_list) > 0:
        describe_feature = arcpy.Describe(feature)

        sql = "\"{}\" IN ({})".format(
            describe_feature.OIDFieldName,
            ",".join(["{}".format(oid) for oid in oid_list])
        )

        arcpy.SelectLayerByAttribute_management(
            feature,
            selection_type,
            sql
        )

    else:
        print("No features match pattern {}".format(expression))

    return oid_list


def _get_OID_match(feature, fields, expression):
    if type(fields) is list:
        fields = ["OID@"] + fields
    else:
        fields = ["OID@", "{}".format(fields)]

    matcher = re.compile(expression)

    oid_list = []
    with arcpy.da.SearchCursor(feature, fields) as sc:
        for row in sc:
            if _check_match(matcher, row):
                oid_list.append(row[0])

    return oid_list


def _check_match(matcher, row):
    for i in range(1, len(row)):
        field_value = row[i]
        if field_value is None:
            continue

        if matcher.match("{}".format(field_value)) is not None:
            return True
    return False


def _set_logger_level(level):
    _logger.setLevel(level)


if __name__ == '__main__':

    tmp_ft = arcpy.MakeFeatureLayer_management(r'',
                                      'ft')
    select_by_regex()

    # a = r'I:\DocsDraw\DocsDrawFCs.gdb\DocsDraw_Polygon'
    # a_r = get_unique_values(a, ["HARDCOPYLOCATION"])
    #
    # a_r = get_unique_values(a, "HARDCOPYLOCATION")
    #
    #
    # a = [r'I:\DocsDraw\DocsDrawFCs.gdb\DocsDraw_Polygon', r'I:\DocsDraw\DocsDrawFCs.gdb\DocsDraw_Point']
    # a_r = get_unique_values(a, "HARDCOPYLOCATION")

    # x = feature_to_tsv_clipboard('Database Connections\\Production.sde\\GIS.RMW.RegionalProperties',
    #                                         # [
    #                                         #     # "PropertyName",
    #                                         #     # "FullAddress",
    #                                         #     # "Settlement",
    #                                         #     # "Municipality",
    #                                         #     "ParentSite",
    #                                         # ]
    # )
    pass