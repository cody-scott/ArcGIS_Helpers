import arcview
import arcpy

import os
import logging
import contextlib

import pyperclip

from arcgis_helpers.__logger import _logger


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
        output_values_2.append("\t".join(str(x) for x in item))

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


def _set_logger_level(level):
    _logger.setLevel(level)