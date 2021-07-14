# Flask & Geocoding Integration

## Requirements

* Python Version >= 3.7.4
* MySQL Server
* MySQL Workbench
* Please see requirements.txt file that includes all necessary pip installations!

## How to run? + install

* Import the mysql_structure.sql to the workbench
* Python3 -m pip install -r requirement.txt
* Fill the following variables at the client.py file:
  * MYSQL_IP
  * MYSQL_USER
  * MYSQL_PASS
  * MYSQL_SCHEMA
* Run python3 client.py

# Project Organization

    ├── requirements.txt         <- Requirements file (pip installations).
    ├── mysql_structure.sql      <- All necessary SQL tables and schemas.
    ├── client.py                <- Main file. This file executes the project.
    |── wrappers           
       '── db_wrapper.py         <- wraps all DB (MySQL) functionality.

## Authors

* **Tony Schneider** - *Programming* - [TonySchneider](https://github.com/tonySchneider)