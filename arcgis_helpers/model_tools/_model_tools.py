import arcpy
import os
import datetime
import sys

from arcgis_helpers.__logger import _logger


def import_model_shapefile(shapefile, output_geodatabase):
    """
    Import a model result shapefile into a geodatabase
    :param shapefile:
    :type shapefile:
    :param output_geodatabase:
    :type output_geodatabase:
    :return:
    :rtype:
    """
    try:
        _logger.info("asserting values")
        assert shapefile is not None
        assert output_geodatabase is not None

        arcpy.env.overwriteOutput = True
        shape = shapefile
        output_geodatabase = output_geodatabase

        _logger.info("Adding {} to {}".format(shape,output_geodatabase))
        shapefile_name = str(shape).split("\\")
        out_feature = "{}\\{}".format(output_geodatabase,shapefile_name[len(shapefile_name)-1].replace(".shp",""))
        _logger.debug(out_feature)
        if (arcpy.Exists(out_feature)):
            _logger.info("feature exists - deleting old feature")
            arcpy.Delete_management(out_feature)
        x = arcpy.FeatureClassToGeodatabase_conversion(shape,output_geodatabase)[0]
        return out_feature

    except Exception, e:
        _logger.error(e.message)


def create_query_table(input_feature, input_tables, geodatabase):
    """
    Generate query table from an input feature and tables
    Input should be the feature without the path.
    Path should be the supplied geodatabase
    :param input_feature:
    :type input_feature:
    :param input_tables: str
    :type input_tables: list or str
    :param geodatabase:
    :type geodatabase: str
    :return:
    :rtype:
    """
    try:
        _logger.info("asserting values")
        assert input_feature is not None
        assert input_tables is not None

        arcpy.env.overwriteOutput = True

        input_feature_type = _feature_type(input_feature)
        results = []
        for table in list(input_tables):
            # table_full = os.path.join(geodatabase, table)
            # feature_full = os.path.join(geodatabase, input_feature)
            # Check to ensure that tables are for the feature type
            # IE: Processing only for Junctions
            if input_feature_type.upper() not in str(table).upper():
                # warn
                _logger.warning("Skipping {}\n"
                                 "Table is not for {} Feature Type".format(table, input_feature))
            else:
                _logger.info("Working on {}".format(table))
                result = _create_query_table(input_feature, table, input_feature_type, geodatabase)
                results.append(result)

        return results
    except Exception, e:
        _logger.error(e.message)


def _feature_type(feature):
    _logger.info("Validating feature type")
    f_type = ""
    base_list = ["Junction","Pipe","Pump","Reservoir","Valve","Tank"]
    for i in base_list:
        if i.upper() in str(feature).upper():
            _logger.info("Feature type {} found".format(i))
            return i


def _create_query_table(feature, table, input_type, geodatabase):
    workspace_path = _get_workspace(geodatabase)

    _logger.info("Building Query Table parameters")
    qf_parameters = _build_qf(feature, table, workspace_path, input_type)

    _logger.info("Generating Query Table")
    QT = arcpy.MakeQueryTable_management(qf_parameters[0],
                                         qf_parameters[1],
                                         "USE_KEY_FIELDS",
                                         qf_parameters[2],
                                         qf_parameters[3],
                                         qf_parameters[4])[0]

    _logger.info("Copying final Query Table to\n"
                     "{}".format(qf_parameters[5]))
    _logger.info("feature count: {}".format(arcpy.GetCount_management(QT)[0]))

    out__q_t = os.path.join(workspace_path,qf_parameters[5])
    out_feature = arcpy.CopyFeatures_management(QT, out__q_t)[0]
    _logger.info("OUT: {}".format(out__q_t))
    return out_feature


def _build_qf(feature, table, geodatabase, input_type):
    _logger.info("building query feature")
    output_feature = _create_output_table(table, geodatabase)

    _logger.debug("building table list")
    table_list = [
        str(os.path.join(geodatabase, feature)),
        str(os.path.join(geodatabase, table))
    ]

    _logger.debug("setting key field")
    key_field = "{}.ID".format(feature)
    _logger.debug("key field {}".format(key_field))

    _logger.debug("Building SQL query")
    sql = "{}.ID = {}.ID".format(feature, table)
    _logger.debug("SQL Query - {}".format(sql))

    _logger.info("building feature fields")
    feature_dct = {
        'Junction': ["ID","ELEVATION","ZONE","FILTER_TYP","Shape"],
        'Pipe': ["ID","ZONE","FROM_","TO","Shape"]
    }
    ls = feature_dct.get(input_type, ["ID", "ZONE", "Shape"])

    _logger.debug("{} fields {}".format(input_type, ls))
    feature_field = ["{}.{}".format(feature, fl) for fl in ls]

    _logger.debug("building table fields")
    table_field = [
        "{}.{}".format(table, item.name)
        for item in arcpy.ListFields(os.path.join(geodatabase, table))
        if item.name not in ["TIME_STEP","OBJECTID"]
    ]

    _logger.debug("combining feature and table fields")
    combined_fields = feature_field + table_field

    return [table_list,"QueryTable",key_field,combined_fields,sql,output_feature]


def _get_workspace(item):
    _logger.debug("setting arcgis workspace")
    arcpy.env.workspace = item
    return item


def _create_output_table(table, geodatabase):
    _logger.info("generating output table")
    out_file = ''

    _logger.debug("building output based on feature")
    base_list = ["Junction","Pipe","Pump","Reservoir","Valve","Tank"]
    for i in base_list:
        if i.upper() in table.upper():
            out_file = table.replace("_OUT","_QT")
            out_file = out_file.replace("_AVG", "_AVG_QT")
            break

    _logger.debug("checking if fireflow table (FF)")
    if "FF" in table.upper():
        out_file += "_QT"

    _logger.debug("output file - {}".format(out_file))
    return os.path.join(geodatabase, out_file)


def import_model_results(model_mxd, scenario, features, output_geodatabase):
    """
    Used for importing model results into GIS
    features can be a single item, or a list of items, but they must match
    the names in the folder, ie: JunctOut.dbf
    :param model_mxd:
    :type model_mxd:
    :param scenario:
    :type scenario:
    :param features:
    :type features:
    :param output_geodatabase:
    :type output_geodatabase:
    :return:
    :rtype:
    """
    _logger.info("Starting Importing Model Results")
    out_tables = []
    try:
        _logger.debug("build scenario information")
        model_scenario_folder = model_mxd.replace(".mxd",os.path.join(".OUT","Scenario"))
        source_folder = os.path.join(model_scenario_folder, scenario)
        source_file = features
        result = _read_file(output_geodatabase, source_folder, source_file, scenario, model_mxd)
        return result

    except Exception, e:
        # arcpy.AddError(e.message)
        print("ERROR")
        _logger.error(e.message)
        _logger.error(sys.exc_info()[-1].tb_lineno)


def _table_fields(base_record):
    fld_name = base_record.name
    fld_type = base_record.type
    fld_length = base_record.length
    fld_decimals = base_record.scale
    fld_precision = base_record.precision
    if fld_name == "TIME":
        return [fld_name,"DATE","","",""]
    if fld_type == "OID":
        return None
    else:
        return [fld_name,fld_type,fld_precision,fld_decimals,fld_length]


def _create_model_output_table(output_gdb, table_name, fields):
    counter = 1
    core_table = table_name
    while arcpy.Exists(os.path.join(output_gdb, core_table)):
        core_table = "{}_{}".format(table_name, counter)
        counter += 1
    _logger.info("Creating Table: {}".format(os.path.join(output_gdb, core_table)))
    new_table = arcpy.CreateTable_management(output_gdb, core_table)[0]
    for field in fields:
        fld_settings = _table_fields(field)
        if fld_settings is not None:
            _logger.debug("Adding Field: {}".format(fld_settings[0]))
            arcpy.AddField_management(new_table,fld_settings[0],fld_settings[1],fld_settings[2],fld_settings[3],fld_settings[4])
    print("")
    return new_table


def _table_type(input_file, scenario, model):
    _logger.debug("determining table type")
    out_name = ""
    if "Junct" in input_file:
        out_name = "Junction"
    elif "Pipe" in input_file:
        out_name = "Pipe"
    elif "Pump" in input_file:
        out_name = "Pump"
    elif "Res" in input_file:
        out_name = "Reservoir"
    elif "Tank" in input_file:
        out_name = "Tank"
    elif "Valve" in input_file:
        out_name = "Valve"
    else:
        _logger.warning("could not determine type of {}".format(input_file))
        return False

    # if include_model_name:
    #     model = model.split("\\")
    #     final_name = "{}_{}_{}_{}".format(model[len(model)-1].replace(".mxd",""),scenario,out_name,"OUT")
    # else:
    final_name = "{}_{}_{}".format(scenario,out_name,"OUT")
    _logger.debug("output name - {}".format(final_name))
    return final_name


def _read_file(output_gdb, source_folder, source_file, scenario, model_file):
    try:
        column_names = {}
        cursor_fields = []
        out_name = _table_type(source_file, scenario, model_file)
        _logger.info("Starting processing of {}".format(os.path.join(source_folder, source_file)))
        if not out_name:
            _logger.error("Problem with input file name\n"
                           "Please ensure it is unchanged from original name"
                           "Ex: JunctOut.dbf")
            return False

        # For the datetime formatting
        _logger.debug("setting base time")
        base_time = datetime.datetime(int(datetime.datetime.now().year),01,01,00,00)

        # Open Table
        _logger.debug("loading dbf table to memory")
        dbf_table = arcpy.CopyRows_management(os.path.join(source_folder, source_file), "in_memory\\ResTable")[0]

        _logger.debug("building table fields excluding OID")
        fld_names = arcpy.ListFields(dbf_table)
        for x in range(0,len(fld_names)):
            if fld_names[x].type <> "OID":
                cursor_fields.append(fld_names[x].name)
                column_names[x] = fld_names[x].name

        output_table = _create_model_output_table(output_gdb, out_name, fld_names)

        row_count = int(arcpy.GetCount_management(dbf_table)[0])
        _logger.info("Total Rows to process: {}".format(row_count))

        current_row = 0

        _logger.info("Starting row iteration")

        with arcpy.da.InsertCursor(output_table,cursor_fields) as ic:
            with arcpy.da.SearchCursor(dbf_table,cursor_fields) as sc:
                for line in sc:
                    current_row += 1
                    if ((current_row % 20) == 0) or ((current_row + 1) > row_count):
                        _logger.info("{} of {}".format(current_row, row_count))
                    out_values = []
                    for i in range(0,len(cursor_fields),1):
                        var = line[i]
                        if type(var) is unicode:
                            if cursor_fields[i] == "TIME":
                                var = var.replace("hrs","")
                                var = var.replace(" ","")
                                var = var.split(":")
                                #takes a base time of Jan 1 and adds the hours or minutes depending on the value in the time field
                                #new code, works better then looking at the time and trying to estimate based on the hour
                                #doesn't need to be sequential, simply based on the total amount of time within the field thats being examined
                                var = base_time + datetime.timedelta(hours=int(var[0]),minutes=int(var[1]))
                                var = var.strftime("%x %X")
                        out_values.append(var)
                    ic.insertRow(out_values)
        _logger.debug("Deleting temporary dbf table")
        arcpy.Delete_management(dbf_table)
        return output_table
    except Exception, e:
        try:
            arcpy.Delete_management(dbf_table)
        finally:
            _logger.error(e.message)
            return False


def list_model_scenarios(model_file):
    output_path = "{}.OUT".format(model_file.split(".")[0])
    _logger.debug("output path {}".format(output_path))
    scenario_path = os.path.join(output_path, "SCENARIO")
    _logger.debug(scenario_path)
    if not os.path.isdir(scenario_path):
        _logger.error("No scenario path found")
        return

    _logger.debug(os.listdir(scenario_path))

    scenarios = [
        item for item in os.listdir(scenario_path)
        if os.path.isdir(os.path.join(scenario_path, item))
    ]

    _logger.info("\n".join(scenarios))

    return scenarios
