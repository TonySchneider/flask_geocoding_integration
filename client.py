#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__licence__ = 'GPL'
__version__ = '0.0.1'
__author__ = 'Tony Schneider'
__email__ = 'tonysch05@gmail.com'

import os
import sys
import time
import json
import logging
import hashlib
import requests
import threading
from typing import Union
from datetime import datetime, timedelta
from flask import Flask, request
from wrappers.db_wrapper import DBWrapper
from wrappers.requets_wrapper import RequestWrapper

"""
Please fill the MySQL credentials!
MySQL tables:
1. admins
2. deliveries
3. deliveries_by_day
4. timeslots

Please run the db script (that provided with the project files) to create all tables correctly.
"""

try:
    MYSQL_IP = os.environ["MYSQL_IP"]
    MYSQL_USER = os.environ["MYSQL_USER"]
    MYSQL_PASS = os.environ["MYSQL_PASS"]
    GEOCODING_API_KEY = os.environ["GEOCODING_API_KEY"]
    HOLIDAY_API_KEY = os.environ["HOLIDAY_API_KEY"]
except KeyError:
    logging.error("Please set the environment variables. Aborting...")
    sys.exit(1)

MYSQL_SCHEMA = 'dropit_exercise'

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-10s | %(message)s', stream=sys.stdout)
app = Flask(__name__)
db_obj = DBWrapper(host=MYSQL_IP, mysql_user=MYSQL_USER, mysql_pass=MYSQL_PASS, database=MYSQL_SCHEMA)
threadLock = threading.Lock()

##### Admin Endpoints #####


def verify_admin(username: str, password: str) -> bool:
    """
    This method verifies the provided user's password.
    :return: True | False
    """
    hashed_password = hashlib.sha1(password.encode('utf8'))
    users_hashed_password = db_obj.get_all_values_by_field(table_name='admins', condition_field='username', condition_value=username, field='password', first_item=True)

    if users_hashed_password == hashed_password.hexdigest():
        return True
    return False


@app.route('/upload-new-timeslots', methods=['POST'])
def upload_new_timeslots():
    """
    ** Admin Endpoint **

    This method responsible on the uploading of newest timeslots.

    # payload example:
    {
        "username": <username>,
        "password": <password>,
        "timeslots: "[
            {
                "start_time": <YYYY-MM-DD hh:mm:ss>,
                "end_time": <YYYY-MM-DD hh:mm:ss>,
                "supported_city": <city>
            }
        ]
    {
    """
    payload = verify_json_structure(['username', 'password', 'timeslots'])
    if isinstance(payload, tuple):
        return payload

    valid = verify_admin(username=payload['username'], password=payload['password'])

    if valid:
        timeslots = payload['timeslots']
        insert_statuses = []
        bad_timeslots = []

        for timeslot in timeslots:
            if any(key not in timeslot.keys() for key in ['start_time', 'end_time', 'city']):
                insert_statuses.append(False)
                bad_timeslots.append(f"'{timeslot}' - one of the keys doesn't exist or written incorrectly.\n")
                continue

            current_row = {
                'start_time': timeslot['start_time'],
                'end_time': timeslot['end_time'],
                'city': timeslot['city']
            }

            start_time_dt = datetime.strptime(timeslot['start_time'], "%Y-%m-%d %H:%M:%S")
            end_time_dt = datetime.strptime(timeslot['end_time'], "%Y-%m-%d %H:%M:%S")
            if end_time_dt <= start_time_dt:
                insert_statuses.append(False)
                bad_timeslots.append(f"'{timeslot}' - The end time is before the start time.\n")
                continue

            holidays = get_holidays()
            for holiday in holidays:
                if start_time_dt.strftime("%Y-%m-%d") == holiday['date']:
                    insert_statuses.append(False)
                    bad_timeslots.append(f"'{timeslot}' - This timeslot is fall on a holiday.\n")
                    continue

            current_insert_status = db_obj.insert_row(table_name='timeslots', keys_values=current_row)
            if not current_insert_status:
                bad_timeslots.append(f"'{timeslot}' - Syntax Issue.\n")

            insert_statuses.append(current_insert_status)

        if all(insert_statuses):
            return "All slots were inserted successfully.", 200
        else:
            return f"One or more timeslots wasn't inserted:\n{''.join([bad_timeslot for bad_timeslot in bad_timeslots])}"
    else:
        return "The provided user admin is invalid.", 400


######################


def verify_json_structure(keys: list = None) -> Union[dict, tuple]:
    try:
        data = request.get_data().decode('utf8').replace('\'', '"')
        payload = json.loads(data)
    except Exception as e:
        logging.error(f"There was an issue with the provided data. Reason - '{e}'")
        return "Bad request. please check the sent data.", 400

    try:
        assert isinstance(payload, dict)
        assert all(key in payload.keys() for key in keys)
    except AssertionError:
        return "Bad request. please check the sent data.", 400

    return payload


def get_geocoding_object(address: str) -> Union[dict, None]:
    parsed_response = None
    defined_url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GEOCODING_API_KEY}"

    try:
        response = requests.get(url=defined_url)
        response.raise_for_status()
        content = response.content.decode('utf8')
        parsed_response = json.loads(content) if content else {}
    except Exception as e:
        logging.error(f"There was an issue with sending GET GeoCoding request by the address - '{address}' | Error -'{e}'")

    return parsed_response


def get_holidays() -> Union[dict, None]:
    defined_url = f"https://holidayapi.com/v1/holidays"
    # Free accounts are limited to last year's historical data only, so i wrote "-1" to the year key but for payed account we should remove it.
    params = {
        'country': 'IL',
        'year': datetime.now().year - 1,
        'key': HOLIDAY_API_KEY
    }

    rw_obj = RequestWrapper()
    response = rw_obj.perform_request(method='GET', url=defined_url, params=params)

    if hasattr(response, 'parsed_response'):
        parsed_response = response.parsed_response
        if parsed_response['status'] == 200:
            holidays = parsed_response['holidays']
            return holidays

    return None


@app.route('/resolve-address', methods=['POST'])
def resolve_address():
    payload = verify_json_structure(['searchTerm'])
    if isinstance(payload, tuple):
        return payload

    geocoding_details = get_geocoding_object(payload['searchTerm'])
    if not geocoding_details:
        return "Internal Error", 500

    print(geocoding_details)
    if 'results' in geocoding_details.keys() and geocoding_details['results'] and 'formatted_address' in geocoding_details['results'][0].keys():
        return geocoding_details['results'][0]['formatted_address'], 200
    else:
        return 'No Formatted Address. Check the provided address.', 404


@app.route('/timeslots', methods=['POST'])
def get_timeslots():
    payload = verify_json_structure(['address'])
    if isinstance(payload, tuple):
        return payload

    matched_timeslots = []

    datetime_now = datetime.now()
    all_timeslots = db_obj.get_all_values_by_field(table_name='timeslots')
    if not all_timeslots:
        return "Internal DB issue, ask devs.", 500

    for timeslot in all_timeslots:
        if timeslot['start_time'] > datetime_now and timeslot['city'].lower() in payload['address'].lower():
            matched_timeslots.append(timeslot)

    if matched_timeslots:
        return "\n".join(json.dumps(item, indent=4, sort_keys=True, default=str) for item in matched_timeslots), 302
    else:
        return "No available timeslots by the provided address.", 404


@app.route('/deliveries', methods=['POST'])
def book_a_delivery():
    payload = verify_json_structure(['timeslotId', 'user'])
    if isinstance(payload, tuple):
        return payload

    timeslot_details = db_obj.get_all_values_by_field(table_name='timeslots', condition_field='id', condition_value=payload['timeslotId'], first_item=True)
    if timeslot_details is None:
        return "The provided timeslot id is incorrect.", 400

    current_date = timeslot_details['start_time'].date()

    if timeslot_details['times_used'] >= 2:
        return f"This timeslot (ID - '{payload['timeslotId']}') was reached the 2 maximum used times, choose other timeslot.", 400

    number_of_delivery_by_day = db_obj.get_all_values_by_field(table_name='deliveries_by_day', condition_field='date', condition_value=timeslot_details['start_time'].date(), field='num_of_deliveries', first_item=True)

    if number_of_delivery_by_day is None:
        status = db_obj.insert_row(table_name='deliveries_by_day', keys_values={'date': current_date})
        if not status:
            return "Didn't manage to book new delivery, INTERNAL ERROR. ask devs.", 500
        number_of_delivery_by_day = 1

    if number_of_delivery_by_day >= 10:
        return f"The number of the deliveries at this date ({current_date}) reached the maximum (10 deliveries).", 500

    # The threadLock handles the concurrent requests.
    threadLock.acquire()
    insert_new_delivery_status = db_obj.insert_row(table_name='deliveries', keys_values={'user': payload['user'], 'timeslot_id': payload['timeslotId']})
    threadLock.release()

    if not insert_new_delivery_status:
        return "Didn't manage to book new delivery, INTERNAL ERROR. ask devs.", 500

    db_obj.increment_field(table_name='timeslots', condition_field='id', condition_value=payload['timeslotId'], field='times_used')
    db_obj.increment_field(table_name='deliveries_by_day', condition_field='date', condition_value=current_date, field='num_of_deliveries')
    return "The delivery was booked successfully.", 200


@app.route('/deliveries/<delivery_id>/complete', methods=['POST'])
def mark_delivery_complete(delivery_id):
    update_status = db_obj.update_field(table_name='deliveries', condition_field='id', condition_value=delivery_id, field='status', value='Delivered')
    if not update_status:
        return "Didn't manage to find delivery by the provided ID.", 400

    return "Marked the delivery as 'Delivered'", 200


@app.route('/deliveries/<delivery_id>', methods=['DELETE'])
def cancel_delivery(delivery_id):
    delete_status = db_obj.delete_by_field(table_name='deliveries', field_condition='id', value_condition=delivery_id)
    if not delete_status:
        return "Didn't manage to cancel the delivery by the provided ID.", 400

    # I didn't decrease the value of timeslot used times and the deliveries of the day since this delivery can be canceled while the courier already reached the location.

    return "The delivery was canceled successfully.", 200


@app.route('/deliveries/daily', methods=['GET'])
def get_daily():
    all_deliveries = db_obj.get_join_tables(first_table='deliveries', second_table='timeslots', first_field='timeslot_id', second_field='id')
    if not all_deliveries:
        return "There are no deliveries.", 404

    today_date = datetime.today().date()

    matched_deliveries = []
    for delivery in all_deliveries:
        if delivery['start_time'].date() == today_date:
            matched_deliveries.append(delivery)

    if matched_deliveries:
        return json.dumps(matched_deliveries, indent=4, sort_keys=True, default=str), 302

    return "There are not deliveries today yet.", 404


def get_dates_by_week_number() -> list:
    """
    This method calculates list of dates by today's date.
    First, it calculates the week number and after that by the week number it calculates the dates by asctime object and for loop range(1, 7)
    :return: list of dates by the week number
    """
    current_week_number = datetime.now().isocalendar()[1] - 1
    start_date = time.asctime(time.strptime('2021 %d 0' % current_week_number, '%Y %W %w'))
    start_date = datetime.strptime(start_date, '%a %b %d %H:%M:%S %Y')
    dates = [start_date.strftime('%Y-%m-%d')]
    for i in range(1, 7):
        day = start_date + timedelta(days=i)
        dates.append(day.strftime('%Y-%m-%d'))

    return dates


@app.route('/deliveries/weekly', methods=['GET'])
def get_weekly():
    all_deliveries = db_obj.get_join_tables(first_table='deliveries', second_table='timeslots', first_field='timeslot_id', second_field='id')
    if not all_deliveries:
        return "There are no deliveries.", 404

    all_week_dates = get_dates_by_week_number()

    matched_deliveries = []
    for date in all_week_dates:
        for delivery in all_deliveries:
            if delivery['start_time'].date() == datetime.strptime(date, "%Y-%m-%d").date():
                matched_deliveries.append(delivery)

    if matched_deliveries:
        return json.dumps(matched_deliveries, indent=4, sort_keys=True, default=str), 302

    return "There are not deliveries this week yet.", 404


def main(*args, **kwargs) -> int:
    try:
        logging.info('Starting app... Press CTRL+C to quit.')
        app.run(host="0.0.0.0", port=80)
    except KeyboardInterrupt:
        logging.info('Quitting... (CTRL+C pressed)')
        return 0
    except Exception:  # Catch-all for unexpected exceptions, with stack trace
        logging.exception(f'Unhandled exception occurred!')
        return 1


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
