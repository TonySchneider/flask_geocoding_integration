import os
import sys
import requests
import unittest
from datetime import datetime, timedelta
from wrappers.requets_wrapper import RequestWrapper


class PositiveTests(unittest.TestCase):
    delivery_id = None

    def setUp(self):
        self.request_obj = RequestWrapper()
        self.host = 'http://127.0.0.1'
        self.headers = {'Content-Type': 'application/json'}
        try:
            self.test_user_password = os.environ["test_user_password"]
        except KeyError:
            sys.exit(1)

    # End Point Test
    def test1_upload_new_timeslots(self):
        endpoint = '/upload-new-timeslots'
        data = {
            'username': 'test_user',
            'password': self.test_user_password,
            'timeslots': [{
                'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'end_time': (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
                'city': 'Tel Aviv'
            }]
        }
        print(data)
        response = self.request_obj.perform_request(method='POST', url=f'{self.host}{endpoint}', data=data, headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 200)

    # End Point Test
    def test2_resolve_address(self):
        endpoint = '/resolve-address'
        data = {'searchTerm': 'menchem begin 140 tel aviv israel'}

        response = self.request_obj.perform_request(method='POST', url=f'{self.host}{endpoint}', data=data,
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.text)

    # End Point Test
    def test3_timeslots(self):
        endpoint = '/timeslots'

        data = {'address': 'menchem begin 140 tel aviv israel'}

        response = self.request_obj.perform_request(method='POST', url=f'{self.host}{endpoint}', data=data,
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 302)

    # End Point Test
    def test4_deliveries(self):
        endpoint = '/deliveries'

        data = {'user': 'tony', 'timeslotId': 4}

        response = self.request_obj.perform_request(method='POST', url=f'{self.host}{endpoint}', data=data,
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 200)

    # End Point Test
    def test5_daily(self):
        endpoint = '/deliveries/daily'

        response = self.request_obj.perform_request(method='GET', url=f'{self.host}{endpoint}',
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 302)
        if hasattr(response, 'parsed_response'):
            self.assertIsNotNone(response.parsed_response)
            self.assertIsInstance(response.parsed_response, list)
            self.assertTrue(len(response.parsed_response))
            PositiveTests.delivery_id = response.parsed_response[0]['id']

    # End Point Test
    def test6_weekly(self):
        endpoint = '/deliveries/weekly'

        response = self.request_obj.perform_request(method='GET', url=f'{self.host}{endpoint}',
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 302)

    # End Point Test
    def test7_mark_delivery_as_complete(self):
        endpoint = f'/deliveries/{PositiveTests.delivery_id}/complete'

        response = self.request_obj.perform_request(method='POST', url=f'{self.host}{endpoint}',
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 200)

    # End Point Test
    def test8_cancel_delivery(self):
        endpoint = f'/deliveries/{PositiveTests.delivery_id}'

        response = self.request_obj.perform_request(method='DELETE', url=f'{self.host}{endpoint}',
                                                    headers=self.headers)

        self.assertIsNotNone(response)
        self.assertIsInstance(response, requests.Response)
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
