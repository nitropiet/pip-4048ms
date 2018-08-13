CREATE TABLE inverter_data (observe_datetime DATETIME, serial_no TEXT, pv_in_V NUMERIC, pv_in_A NUMERIC, bat_in_A NUMERIC, bat_out_A NUMERIC, load_W NUMERIC, load_perc NUMERIC, PRIMARY KEY(observe_datetime DESC, serial_no));

CREATE TABLE total_data (observe_datetime DATETIME, bat_V NUMERIC, bat_in_A NUMERIC, bat_out_A NUMERIC, load_W  NUMERIC, load_perc NUMERIC, PRIMARY KEY (observe_datetime DESC));

CREATE TABLE inverter_pretty_names (serial_no, pretty_name, primary key (serial_no));
