#!/usr/bin/env python

import sqlite3
import sys
import cgi
import cgitb
import datetime
from collections import OrderedDict
import numpy as np
import os

# global variables
dbname='/opt/db/inverter/inverter.db'
tzOffset = ''

# print the HTTP header
def printHTTPheader():
	print "Content-type: text/html\n\n"

def cgiFieldStorageToDict( fieldStorage ):
	params = {}
	for key in fieldStorage.keys():
		params[ key ] = fieldStorage[ key ].value
	return params

def getTZOffsetFromParams(_params):
	return _params['tz_offset']
		

# print the HTML head section
# arguments are the page title and the table for the chart
def printHTMLHead(title):
	print "<head>"
	print "  <title>"
	print title
	print "</title>"
	print """<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>"""

	return

def stripParamHdr(_dict, _RemoveSerial = False):
	if isinstance(_dict, tuple) or isinstance(_dict, dict):
		return_dict = []
		for item in _dict:
			if item[:6] == "total_":
				if _RemoveSerial:
					return_dict.append(item[6:])
				else:
					return_dict.append(item[6:], 'Total')
			if item[:5] == "INV__":
					tmpPos = item[5:].find("__")
					inverter_serial = item[:tmpPos + 5]
					if _RemoveSerial:
						return_dict.append(item[tmpPos+7:])
					else:
						return_dict.append((item[tmpPos+7:], inverter_serial))
					
		return return_dict

	if _dict[:6] == "total_":
		if _RemoveSerial:
			return (_dict[6:])
		else:
			return (_dict[6:], 'Total')
	if _dict[:5] == "INV__":
		tmpPos = _dict[5:].find("__")
		inverter_serial = _dict[:tmpPos + 5]

		if _RemoveSerial:
			return (_dict[tmpPos + 7:])
		else:
			return (_dict[tmpPos + 7:], inverter_serial)
	
def get_axis_units(_dict):
	
	dict = stripParamHdr(_dict, True)
	ret_value = []
	if "load_W" in dict:
		ret_value.append("load_W")
	if "load_perc" in dict:
		ret_value.append("load_perc")
	if "bat_V" in dict:
		ret_value.append("voltage")
	if "bat_in_A" in dict:
		ret_value.append("current")
	if "bat_out_A" in dict:
		ret_value.append("current")
	if "pv_in_V" in dict:
		ret_value.append("voltage")
	if "pv_in_A" in dict:
		ret_value.append("current")	
		
		
	return ret_value

def get_select_cols_pretty(dict):
	
	#strip header
	tmpDict = stripParamHdr(dict, True)
	ret_value = []
	if "load_W" in tmpDict:
		ret_value.append("Load (W)")
	if "load_perc" in tmpDict:
		ret_value.append("Load (%%)")
	if "bat_V" in tmpDict:
		ret_value.append("Battery (V)")
	if "bat_in_A" in tmpDict:
		ret_value.append("Battery in (A)")
	if "bat_out_A" in tmpDict:
		ret_value.append("Battery out (A)")
	if "pv_in_V" in tmpDict:
		ret_value.append("PV in (V)")
	if "pv_in_A" in tmpDict:
		ret_value.append("PV in (A)")
	
	return ret_value

def get_select_cols_units_pretty(invalue):
	#invalue = stripParamHdr(_invalue, True)
	if invalue == "load_W":
		return "Power (W)"
	if invalue == "load_perc":
		return "Load (%%)"
	if invalue == "voltage":
		return "Voltage (V)"
	if invalue == "current":
		return "Current (A)"
 
	return ""

def get_select_cols_units_short(invalue):
	if invalue == "load_W":
		return "W"
	if invalue == "load_perc":
		return "%"
	if invalue == "voltage":
		return "V"
	if invalue == "current":
		return "A"
	if invalue == "bat_V":
		return "V"
	if invalue == "bat_in_A":
		return "A"
	if invalue == "bat_out_A":
		return "A"
	if invalue == "pv_in_A":
		return "A"
	if invalue == "pv_in_V":
		return "V"
 
	return ""

def get_select_cols_units(_dict):
	ret_value = []

	dict = stripParamHdr(_dict, True)
	for item in dict:
		if "load_W" in item:
			ret_value.append("load_W")
		if "load_perc" in item:
			ret_value.append("load_perc")
		if "bat_V" in item:
			ret_value.append("voltage")
		if "bat_in_A" in item:
			ret_value.append("current")
		if "bat_out_A" in item:
			ret_value.append("current")
		if "pv_in_A" in item:
			ret_value.append("current")
		if "pv_in_V" in item:
			ret_value.append("voltage")

	#return list(OrderedDict.fromkeys(stripParamHdr(dict, True)))
	return ret_value


# get data from the database
# return a list of records from the database
def get_data(interval, dict, inverter_list):
  
	if not dict:
		return ""

	from_clause_template = " LEFT OUTER JOIN inverter_data {0} ON a.observe_datetime = {0}.observe_datetime and {0}.serial_no = '{1}'" 
	from_clause = ""
	select_cols = ""

	#inverter specific cols
	for inverter_serial, inverter_alias in inverter_list.iteritems():
		from_clause += from_clause_template.format(inverter_alias, inverter_serial[0][5:]) #ignore the INV__ part in SQL

		for sel_item in dict:
			if sel_item[:5] == "INV__":
				colData = stripParamHdr(sel_item)
				col_inverter_serial = colData[1]
				if col_inverter_serial == inverter_serial[0]:
					select_col = colData[0]
					select_cols += ", "+ inverter_alias + "." + select_col + " as " + sel_item

	#total cols
	for sel_item in dict:
		if sel_item[:6] == "total_":
			select_cols += ", a." + stripParamHdr(sel_item, True) + " as " + sel_item
				
					

	sqlstr = ("SELECT datetime(a.observe_datetime,'" + tzOffset + " minute') " + select_cols + " FROM total_data a " + from_clause + " WHERE a.observe_datetime > datetime('now','-%s hours') ORDER BY a.observe_datetime" % interval)
	conn=sqlite3.connect(dbname)
	curs=conn.cursor()
	curs.execute(sqlstr)
	rows=curs.fetchall()
	conn.close()

	return rows


# convert rows from database into a javascript table
def create_table(rows, dict):
	chart_table=""
	mask_begin = "[new Date('{0}', '{1}', '{2}', '{3}', '{4}', '{5}')"
	mask_middle = ", {0}"
	mask_end = "]"
	new_row = ",\n"

	for row in rows[:-1]:
		observe_datetime = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
		rowstr = mask_begin.format(observe_datetime.year, observe_datetime.month - 1, observe_datetime.day, observe_datetime.hour, observe_datetime.minute, observe_datetime.second)
		for i in range(1, len(dict) + 1):
			rowstr += mask_middle.format(str(row[i]))
		chart_table += rowstr + mask_end + new_row

	row=rows[-1]
	observe_datetime = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
	rowstr = mask_begin.format(observe_datetime.year, observe_datetime.month - 1, observe_datetime.day, observe_datetime.hour, observe_datetime.minute, observe_datetime.second)
	for i in range(1, len(dict)+1):
		rowstr += mask_middle.format(str(row[i]))
	chart_table += rowstr + mask_end

	return chart_table


# print the javascript to generate the chart
# pass the table generated from the database info
def print_graph_script(table, dict, documentid):

	# google chart snippet
	chart_code="""
    <script type="text/javascript">
      google.charts.load('current', {'packages':['line']});
      google.charts.setOnLoadCallback(drawChart);
      function drawChart() {
        var data = new google.visualization.DataTable(); 
"""

	chart_code += "data.addColumn('datetime', 'Time');\n"

	#for colname in get_select_cols_pretty(dict):
	for colname in dict:
		if colname[:5] == 'INV__': #do inverter cols
			tmpColData = stripParamHdr(colname)
			chart_code += "data.addColumn('number', '" + get_pretty_inv_name(tmpColData[1]) + " " + get_select_cols_pretty(colname)[0] + "');\n"


	for colname in dict:
		if colname[:6] == 'total_': #do total cols
			tmpColData = stripParamHdr(colname)
			chart_code += "data.addColumn('number', '" + get_pretty_inv_name(tmpColData[1]) + " " + get_select_cols_pretty(colname)[0] + "');\n"

	chart_code += """ data.addRows([
%s
        ]);

        var options = {
          chart: {title: 'Inverter data'},
	  curveType: 'function',
	  width:900,
	  height:500,
        series: {
          // Gives each series an axis name that matches the Y-axis below.  
		  """
		  
	i = 0
	for colname in get_select_cols_units(dict):
		chart_code += str(i) + ": {axis: '" + colname + "'},\n"
		i += 1
		
	chart_code += """    },
        axes: {
          // Adds labels to each axis; they don't have to match the axis names.
          y: {   
		  """

	for colname in list(set(get_axis_units(dict))):
		chart_code += colname + ": {label: '" + get_select_cols_units_pretty(colname) + "'},\n"

	chart_code += """          }
        }

	  
        };

        var chart = new google.charts.Line(document.getElementById('""" + documentid + """'));
        chart.draw(data, options);
      }
    </script>
	"""

	print chart_code % (table)




# print the div that contains the graph
def show_graph(documentid):
	print """<div id="%s" style="width: 900px; height: 500px;"></div>""" % documentid



def show_stats_totals(option, current_item):

	conn=sqlite3.connect(dbname)
	curs=conn.cursor()

	select_col = stripParamHdr(current_item, True)

	curs.execute("SELECT datetime(observe_datetime,'" + tzOffset + " minute'), max(" + select_col + ") FROM total_data WHERE observe_datetime > datetime('now','-%s hour') AND observe_datetime <= datetime('now')" % option)
	rowmax=curs.fetchone()
	rowstrmax="<td style=""padding: 5px;"">{0}</td><td align=""right""  style=""padding: 5px;"">{1}&nbsp{2}</td>".format(str(rowmax[0]), str(rowmax[1]), get_select_cols_units_short(select_col))

	curs.execute("SELECT datetime(observe_datetime,'" + tzOffset + " minute'), min(" + select_col + ") FROM total_data WHERE observe_datetime > datetime('now','-%s hour') AND observe_datetime <= datetime('now')" % option)
	rowmin=curs.fetchone()
	rowstrmin="<td style=""padding: 5px;"">{0}</td><td align=""right"" style=""padding: 5px;"">{1}&nbsp{2}</td>".format(str(rowmin[0]), str(rowmin[1]), get_select_cols_units_short(select_col))

	curs.execute("SELECT avg(" + select_col + ") FROM total_data WHERE observe_datetime > datetime('now','-%s hour') AND observe_datetime <= datetime('now')" % option)
	rowavg=curs.fetchone()
	rowstravg="<td align=""right"" style=""padding: 5px;"">{0:>.2f}&nbsp{1}</td>".format(rowavg[0], get_select_cols_units_short(select_col))

	curs.execute("SELECT datetime(observe_datetime,'" + tzOffset + " minute'), " + select_col + " FROM total_data WHERE observe_datetime = (select max(observe_datetime) from total_data)")
	rowcurr=curs.fetchone()
	rowstrcurr="<td style=""padding: 5px;"">{0}</td><td align=""right"" style=""padding: 5px;"">{1}&nbsp{2}</td>".format(str(rowcurr[0]), str(rowcurr[1]), get_select_cols_units_short(select_col))

	conn.close()

	print "<tr>"
	print "<td>Total</td>"
	print "<td>" + get_select_cols_pretty(current_item)[0] + "</td>"
	print rowstrmin
	print "<td>&nbsp&nbsp</td>"
	print rowstrmax
	print "<td>&nbsp&nbsp</td>"
	print rowstravg
	print "<td>&nbsp&nbsp</td>"
	print rowstrcurr
	print "<td>&nbsp&nbsp</td>"
	print "</tr>"



def show_stats_inverter(option, current_item):

	tmpData = stripParamHdr(current_item)
	inverter_serial = tmpData[1]
	
	inverter_serial_SQL = tmpData[1][5:] #ignore INV__ part from serial
	select_col = tmpData[0]

	conn=sqlite3.connect(dbname)
	curs=conn.cursor()

	curs.execute("SELECT datetime(observe_datetime,'" + tzOffset + " minute'), max(" + select_col + ") FROM inverter_data WHERE observe_datetime > datetime('now','-%s hour') AND observe_datetime <= datetime('now') and serial_no = '%s'" % (option, inverter_serial_SQL))
	rowmax=curs.fetchone()
	rowstrmax="<td style=""padding: 5px;"">{0}</td><td align=""right""  style=""padding: 5px;"">{1}&nbsp{2}</td>".format(str(rowmax[0]), str(rowmax[1]), get_select_cols_units_short(select_col))

	curs.execute("SELECT datetime(observe_datetime,'" + tzOffset + " minute'), min(" + select_col + ") FROM inverter_data WHERE observe_datetime > datetime('now','-%s hour') AND observe_datetime <= datetime('now') and serial_no = '%s'" % (option, inverter_serial_SQL))
	rowmin=curs.fetchone()
	rowstrmin="<td style=""padding: 5px;"">{0}</td><td align=""right"" style=""padding: 5px;"">{1}&nbsp{2}</td>".format(str(rowmin[0]), str(rowmin[1]), get_select_cols_units_short(select_col))

	curs.execute("SELECT avg(" + select_col + ") FROM inverter_data WHERE observe_datetime > datetime('now','-%s hour') AND observe_datetime <= datetime('now') and serial_no = '%s'" % (option, inverter_serial_SQL))
	rowavg=curs.fetchone()
	rowstravg="<td align=""right"" style=""padding: 5px;"">{0:>.2f}&nbsp{1}</td>".format(rowavg[0], get_select_cols_units_short(select_col))

	curs.execute("SELECT datetime(observe_datetime,'" + tzOffset + " minute'), " + select_col + " FROM inverter_data a WHERE observe_datetime = (select max(observe_datetime) from inverter_data b where a.serial_no = b.serial_no) and a.serial_no = '%s'" % inverter_serial_SQL)
	rowcurr=curs.fetchone()
	rowstrcurr="<td style=""padding: 5px;"">{0}</td><td align=""right"" style=""padding: 5px;"">{1}&nbsp{2}</td>".format(str(rowcurr[0]), str(rowcurr[1]), get_select_cols_units_short(select_col))

	conn.close()

	print "<tr>"
	print "<td>" + get_pretty_inv_name(inverter_serial) + "</td>"
	print "<td>" + get_select_cols_pretty(current_item)[0] + "</td>"
	print rowstrmin
	print "<td>&nbsp&nbsp</td>"
	print rowstrmax
	print "<td>&nbsp&nbsp</td>"
	print rowstravg
	print "<td>&nbsp&nbsp</td>"
	print rowstrcurr
	print "<td>&nbsp&nbsp</td>"
	print "</tr>"



# connect to the db and show some stats
# argument option is the number of hours
def show_stats(option, selected_legend):

	print "<hr />"
	print """<table>
	<tr>
	<th colspan="2"></th>
	<th colspan="3" style="padding: 5px;">Minimum</th>
	<th colspan="3" style="padding: 5px;">Maximum</th>
	<th colspan="2" style="padding: 5px;">Average</th>
	<th colspan="3" style="padding: 5px;">Last</th>
	</tr>
	"""

	if option is None:
		option = str(24)
		
	for item in selected_legend:


		if item[:6] == "total_":
			show_stats_totals(option, item)

		if item[:5] == "INV__":
			show_stats_inverter(option, item)		

	print "</table>"





def print_time_selector(option):

	print """Show the inverter logs for <select name="timeinterval">"""


	if option is not None:

		if option == "6":
			print "<option value=\"6\" selected=\"selected\">the last 6 hours</option>"
		else:
			print "<option value=\"6\">the last 6 hours</option>"

		if option == "12":
			print "<option value=\"12\" selected=\"selected\">the last 12 hours</option>"
		else:
			print "<option value=\"12\">the last 12 hours</option>"

		if option == "24":
			print "<option value=\"24\" selected=\"selected\">the last 24 hours</option>"
		else:
			print "<option value=\"24\">the last 24 hours</option>"

	else:
		print """<option value="6">the last 6 hours</option>
			<option value="12">the last 12 hours</option>
			<option value="24" selected="selected">the last 24 hours</option>"""

	print "</select> <br />"


def print_form_start():
	print """<form id="inverter_params" action="/cgi-bin/%s" method="POST">
			<input type="hidden" name="tz_offset" value="" />
			<script type="text/javascript"> 
				var tz_offset_value = -(new Date().getTimezoneOffset());

				var formInfo = document.forms['inverter_params'];
				formInfo.elements["tz_offset"].value = tz_offset_value;				
				
			</script>
			""" % os.path.basename(sys.argv[0])

def print_form_total(dict):

	print """<strong>Aggregate</strong> <br />"""
	#Totals

	#BatV
	print_checkbox("total_bat_V", dict, "Battery (V)")

	#LoadW
	print_checkbox("total_load_W", dict, "Load (W)")

	#Load%
	print_checkbox("total_load_perc", dict, "Load (%)")

	#Bat in A
	print_checkbox("total_bat_in_A", dict, "Battery in (A)")

	#Bat out A
	print_checkbox("total_bat_out_A", dict, "Battery out (A)")

def get_inv_list():
	conn=sqlite3.connect(dbname)
	curs=conn.cursor()

	curs.execute("SELECT DISTINCT 'INV__' || serial_no FROM inverter_data ORDER BY serial_no")

	rows=curs.fetchall()
	
	conn.close()

	return rows

def get_pretty_inv_name(_inv_serial):
	conn=sqlite3.connect(dbname)
	curs=conn.cursor()
	curs.execute("SELECT pretty_name FROM inverter_pretty_names WHERE serial_no = '" + _inv_serial + "'")

	rows=curs.fetchone()
	
	conn.close()

	if rows:
		return rows[0]

	return _inv_serial
	
	
def print_checkbox(checkbox_name, param_dict, descr):
	
	checked_str = ''
	if checkbox_name in param_dict:
		checked_str = 'checked'
	print """      <input type="checkbox" name="%s" value="on" %s>%s<br />""" % (checkbox_name, checked_str, descr)
#	if checkbox_name in param_dict:
#		print " checked"
#	print ">%s<br>" % descr

def print_form_inv_select(inverter_serial, dict):
	print """<strong>%s</strong><br />""" % get_pretty_inv_name(inverter_serial)
	#PVinV
	print_checkbox("%s__pv_in_V" % inverter_serial, dict, "PV in (V)")
	#PVinA
	print_checkbox("%s__pv_in_A" % inverter_serial, dict, "PV in (A)")
	#BatinA
	print_checkbox("%s__bat_in_A" % inverter_serial, dict, "Battery in (A)")
	#BatoutA
	print_checkbox("%s__bat_out_A" % inverter_serial, dict, "Battery out (A)")
	#LoadW
	print_checkbox("%s__load_W" % inverter_serial, dict, "Load (W)")
	#Load%
	print_checkbox("%s__load_perc" % inverter_serial, dict, "Load (%)")

def get_selected_inverters(dict):
	
	params = {}
	table_alias = "a"
	
	for inverter_serial in get_inv_list():
		for selected_item in dict:
		
			if selected_item.find("%s__" % inverter_serial) > -1:
				table_alias = chr(ord(table_alias) + 1)
				params[inverter_serial] = table_alias 
				break
	
	return params

def print_form_checkbox(dict):
	print """<div style="width:100%;display:flex;">
         <div style="width:20%">"""

	#Aggregate selection
	print_form_total(dict)
	print """</div>"""

	for inverter_serial in get_inv_list():
	#Inverter i per inverter display
		print """<div style="width:20%">"""
		print_form_inv_select(inverter_serial[0], dict)
		print """</div>"""

	print """</div>    <div><br /></div>"""


def print_form_end(option):
	print """ <div> """ 
	print_time_selector(option)
	print """</div><div>  <input type="submit" value="Display"></div>

       </form>"""

# check that the option is valid
# and not an SQL injection
def validate_input(option_str):
	# check that the option string represents a number
	if option_str.isalnum():
		# check that the option is within a specific range
		if int(option_str) > 0 and int(option_str) <= 24:
			return option_str
		else:
			return None
	else: 
		return None


#return the option passed to the script
def get_option(dict):
	if "timeinterval" in dict:
		option = dict["timeinterval"]
		return validate_input (option)
	else:
		return None

def get_selected_cols(dict):
	params = {}
	if "total_load_W" in dict:
		params["total_load_W"] = "on"
	if "total_load_perc" in dict:
		params["total_load_perc"] = "on"
	if "total_bat_V" in dict:
		params["total_bat_V"] = "on"
	if "total_bat_in_A" in dict:
		params["total_bat_in_A"] = "on"
	if "total_bat_out_A" in dict:
		params["total_bat_out_A"] = "on"

	for inverter_serial in get_inv_list():
		if "%s__pv_in_V" % inverter_serial in dict:
			params["%s__pv_in_V" % inverter_serial] = "on" 
		if "%s__pv_in_A" % inverter_serial in dict: 
			params["%s__pv_in_A" % inverter_serial] = "on" 
		if "%s__bat_in_A" % inverter_serial in dict: 
			params["%s__bat_in_A" % inverter_serial] = "on" 
		if "%s__bat_out_A" % inverter_serial in dict: 
			params["%s__bat_out_A" % inverter_serial] = "on" 
		if "%s__load_W" % inverter_serial in dict: 
			params["%s__load_W" % inverter_serial] = "on" 
		if "%s__load_perc" % inverter_serial in dict: 
			params["%s__load_perc" % inverter_serial] = "on" 


	return params

# main function
# This is where the program starts 
def main():

	# print the HTTP header
	printHTTPheader()
	# start printing the page
	print "<html>"

	cgitb.enable()

	dict = cgiFieldStorageToDict( cgi.FieldStorage() )

	#add timezone offset
	global tzOffset
	tzOffset = str(getTZOffsetFromParams(dict))
		
	# get options that may have been passed to this script
	option=get_option(dict)


	#get selected options
	selected_legend = get_selected_cols(dict)

	#get inverter list
	inverter_list = get_selected_inverters(dict)


	if option is None:
		option = str(24)
	
	# print the head section including the table
	# used by the javascript for the chart
	printHTMLHead("Raspberry Pi Inverter Logger")

	# get data from the database
	records=get_data(option, selected_legend, inverter_list)
	
	table_total = None

	if len(records) != 0:
		 #convert the data into a table
		table_total = create_table(records, selected_legend)

	if table_total != None:
		print_graph_script(table_total, selected_legend, "chart_div")

	print "</head>"

	# print the page body
	print "<body>"

	print_form_start()
	print_form_checkbox(selected_legend)
	print_form_end(option)

	if table_total != None:
		show_graph("chart_div")
		show_stats(option, selected_legend)
	else:
		print "No data found"

   # print dict
	print "</body>"
	print "</html>"

	sys.stdout.flush()

if __name__=="__main__":
	main()



