# -*- coding: utf-8 -*-

import base64
import io
import os
import tempfile

import django
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import TestCase, LiveServerTestCase
import numpy as np
from obspy import read, UTCDateTime, Trace, Stream
from obspy.clients.fdsn import Client as FDSNClient
from obspy.clients.fdsn.header import FDSNException
from psycopg2._range import DateTimeTZRange

from jane.waveforms.models import Restriction, Mapping, ContinuousTrace
from jane.waveforms.process_waveforms import process_file


django.setup()


PATH = os.path.join(os.path.dirname(__file__), 'data')
FILES = [
    os.path.join(PATH, 'RJOB_061005_072159.ehz.new.mseed'),
    os.path.join(PATH, 'TA.A25A.mseed')
]


class DataSelect1TestCase(TestCase):

    def setUp(self):
        # index waveform files
        [process_file(f) for f in FILES]
        User.objects.get_or_create(username='random',
                                   password=make_password('random'))

        credentials = base64.b64encode(b'random:random')
        self.valid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

        credentials = base64.b64encode(b'random:random2')
        self.invalid_auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }

    def test_version(self):
        # 1 - HTTP OK
        response = self.client.get('/fdsnws/dataselect/1/version')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertEqual(response.content, b'1.1.1')
        # 2 - incorrect trailing slash will work too
        response = self.client.get('/fdsnws/dataselect/1/version/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/plain')
        self.assertEqual(response.content, b'1.1.1')

    def test_wadl(self):
        # 1 - HTTP OK
        response = self.client.get('/fdsnws/dataselect/1/application.wadl')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'],
                         'application/xml; charset=utf-8')
        self.assertTrue(response.content.startswith(b'<?xml'))
        # 2 - incorrect trailing slash will work too
        response = self.client.get('/fdsnws/dataselect/1/application.wadl/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'],
                         'application/xml; charset=utf-8')
        self.assertTrue(response.content.startswith(b'<?xml'))

    def test_index(self):
        # 1 - redirect if APPEND_SLASH = True
        response = self.client.get('/fdsnws/dataselect/1')
        self.assertEqual(response.status_code, 301)
        # 2 - HTTP OK
        response = self.client.get('/fdsnws/dataselect/1/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'text/html; charset=utf-8')

    def test_query(self):
        # 1 - start time must be specified
        param = '?'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('Start time must be specifi' in response.reason_phrase)
        # 2 - start time must be parseable
        param = '?start=0'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('Error parsing starttime' in response.reason_phrase)
        # 3 - end time must be specified
        param = '?start=2012-01-01'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('End time must be specified' in response.reason_phrase)
        # 4 - end time must be parseable
        param = '?start=2012-01-01&end=0'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('Error parsing endtime' in response.reason_phrase)
        # 5 - start time must before endtime
        param = '?start=2012-01-01&end=2012-01-01'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('Start time must be before end time' in
                        response.reason_phrase)
        param = '?start=2012-01-02&end=2012-01-01'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 400)
        self.assertTrue('Start time must be before end time' in
                        response.reason_phrase)

    def test_query_nodata(self):
        # not existing - error 204
        param = '?start=2012-01-01&end=2012-01-02&net=GE&sta=APE&cha=EHE'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 204)
        self.assertTrue('Not Found: No data' in response.reason_phrase)
        # not existing - error 404
        param += '&nodata=404'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 404)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

    def test_query_data(self):
        expected = read(FILES[0])[0]
        params = {
            'station': expected.meta.station,
            'cha': expected.meta.channel,
            'start': expected.meta.starttime,
            'end': expected.meta.endtime
        }
        # 1 - query using HTTP GET
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        # compare streams
        got = read(io.BytesIO(response.getvalue()))[0]
        np.testing.assert_equal(got.data, expected.data)
        self.assertEqual(got, expected)
        # 2 - query using HTTP POST
        response = self.client.post('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        # compare streams
        got = read(io.BytesIO(response.getvalue()))[0]
        np.testing.assert_equal(got.data, expected.data)
        self.assertEqual(got, expected)

    def test_queryauth_nodata(self):
        param = '?start=2012-01-01&end=2012-01-02&net=GE&sta=APE&cha=EHE'

        # 1 - no credentials - error 401
        response = self.client.get('/fdsnws/dataselect/1/queryauth' + param)
        self.assertEqual(response.status_code, 401)

        # 2 - invalid credentials - error 401
        response = self.client.get('/fdsnws/dataselect/1/queryauth' + param,
                                   **self.invalid_auth_headers)
        self.assertEqual(response.status_code, 401)

        # 3 - valid credentials - not existing - error 204
        response = self.client.get('/fdsnws/dataselect/1/queryauth' + param,
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 204)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

        # 4 - valid credentials - not existing - error 404
        param += '&nodata=404'
        response = self.client.get('/fdsnws/dataselect/1/queryauth' + param,
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 404)
        self.assertTrue('Not Found: No data' in response.reason_phrase)

    def test_queryauth_data(self):
        expected = read(FILES[0])[0]
        params = {
            'station': expected.meta.station,
            'cha': expected.meta.channel,
            'start': expected.meta.starttime,
            'end': expected.meta.endtime,
        }

        # 1 - no credentials GET - error 401
        response = self.client.get('/fdsnws/dataselect/1/queryauth', params)
        self.assertEqual(response.status_code, 401)

        # 2 - invalid credentials GET - error 401
        response = self.client.get('/fdsnws/dataselect/1/queryauth', params,
                                   **self.invalid_auth_headers)
        self.assertEqual(response.status_code, 401)

        # 3 - no credentials POST - error 401
        response = self.client.post('/fdsnws/dataselect/1/queryauth', params)
        self.assertEqual(response.status_code, 401)

        # 4 - invalid credentials POST - error 401
        response = self.client.post('/fdsnws/dataselect/1/queryauth', params,
                                    **self.invalid_auth_headers)
        self.assertEqual(response.status_code, 401)

        # 5 - query using HTTP GET
        response = self.client.get('/fdsnws/dataselect/1/queryauth', params,
                                   **self.valid_auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)

        # compare streams
        got = read(io.BytesIO(response.getvalue()))[0]
        np.testing.assert_equal(got.data, expected.data)
        self.assertEqual(got, expected)

        # 6 - query using HTTP POST
        response = self.client.post('/fdsnws/dataselect/1/queryauth', params,
                                    **self.valid_auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)

        # compare streams
        got = read(io.BytesIO(response.getvalue()))[0]
        np.testing.assert_equal(got.data, expected.data)
        self.assertEqual(got, expected)

    def test_query_data_wildcards(self):
        # query using wildcards
        param = '?endtime=2010-03-25T00:00:30&network=TA&channel=BH%2A' + \
            '&starttime=2010-03-25&station=A25A'
        response = self.client.get('/fdsnws/dataselect/1/query' + param)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)

    def test_restrictions(self):
        """
        Tests if the waveform restrictions actually work as expected.
        """
        params = {
            'station': 'A25A',
            'cha': 'BHE',
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00'
        }

        # No restrictions currently apply - we should get something.
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        st = read(io.BytesIO(response.getvalue()))
        self.assertEqual(len(st), 1)
        self.assertEqual(st[0].id, "TA.A25A..BHE")

        # Now add restrictions to this one station.
        # create anonymous user
        r = Restriction.objects.get_or_create(network="TA", station="A25A")[0]
        r.users.add(User.objects.filter(username='random')[0])
        r.save()

        # Now the same query should no longer return something as the
        # station has been restricted.
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 204)

        # RJOB data can still be retrieved.
        params["station"] = "RJOB"
        params["cha"] = "Z"
        params["start"] = "2005-01-01T00:00:00"
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        st = read(io.BytesIO(response.getvalue()))
        self.assertEqual(len(st), 1)
        self.assertEqual(st[0].id, ".RJOB..Z")

        # The correct user can still everything
        params = {
            'station': 'A25A',
            'cha': 'BHE',
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00'
        }

        p = {}
        p.update(params)
        p.update(self.valid_auth_headers)
        response = self.client.get('/fdsnws/dataselect/1/queryauth', **p)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        st = read(io.BytesIO(response.getvalue()))
        self.assertEqual(len(st), 1)
        self.assertEqual(st[0].id, "TA.A25A..BHE")

        # Make another user that has not been added to this restriction - he
        # should not be able to retrieve it.
        self.client.logout()
        User.objects.get_or_create(
            username='some_dude', password=make_password('some_dude'))[0]
        credentials = base64.b64encode(b'some_dude:some_dude')
        auth_headers = {
            'HTTP_AUTHORIZATION': 'Basic ' + credentials.decode("ISO-8859-1")
        }
        p = {}
        p.update(params)
        p.update(auth_headers)
        response = self.client.get('/fdsnws/dataselect/1/queryauth', **p)
        self.assertEqual(response.status_code, 204)

    def test_empty_string_identifiers(self):
        """
        A query with only empty strings as NSC identifer is invalid.

        Empty strings are only allowed for stations - otherwise it should
        raise an error - this follows what IRIS does.
        """
        params = {
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00'
        }

        # Not giving NSLC identifiers will result in returning everything.
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('OK' in response.reason_phrase)
        st = read(io.BytesIO(response.getvalue()))
        self.assertEqual(len(st), 19)

        # Explicitly passing either network/station/channel as an empty
        # string should result in an error.
        params = {
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00',
            'net': ''}
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase,
                         "Network must not be an empty string.")

        params = {
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00',
            'station': '  '}
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase,
                         "Station must not be an empty string.")

        params = {
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00',
            'cha': ' '}
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase,
                         "Channel must not be an empty string.")

        params = {
            'start': '2010-03-25T00:00:00',
            'end': '2010-03-26T00:00:00',
            'net': '',
            'sta': ' ',
            'cha': '  '}
        response = self.client.get('/fdsnws/dataselect/1/query', params)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.reason_phrase,
                         "Network must not be an empty string.")

    def test_dataselect_query_for_slightly_messed_up_files(self):
        # Create a file with interleaved traces and some noise traces
        # in-between
        traces = [
            Trace(data=np.ones(10), header={"starttime": UTCDateTime(0)}),
            Trace(data=np.ones(10), header={"starttime": UTCDateTime(5)}),
            Trace(data=np.ones(10), header={"starttime": UTCDateTime(10)}),
            Trace(data=np.ones(10), header={"starttime": UTCDateTime(-5)}),
            Trace(data=np.ones(8), header={"starttime": UTCDateTime(2)}),
            Trace(data=np.ones(12), header={"starttime": UTCDateTime(0)}),
            Trace(data=np.ones(10), header={"starttime": UTCDateTime(1)})
        ]
        for tr in traces:
            tr.stats.network = "XX"
            tr.stats.station = "YY"
            tr.stats.channel = "EHZ"

        # Add a couple more random traces in between. These should just be
        # ignored for the query.
        traces.insert(0, Trace(
            data=np.ones(5),
            header={"starttime": UTCDateTime(2), "network": "DD",
                    "station": "BLA", "channel": "BHZ", "location": "10"}))
        traces.insert(4, Trace(
            data=np.ones(17),
            header={"starttime": UTCDateTime(-2), "network": "DD",
                    "station": "BLA", "channel": "BHZ", "location": "10"}))
        traces.append(Trace(
            data=np.ones(2),
            header={"starttime": UTCDateTime(5), "network": "AB",
                    "station": "CD", "channel": "XYZ", "location": ""}))

        # Write to a temporary file.
        filename = tempfile.mkstemp()[1]
        try:
            Stream(traces=traces).write(filename, format="mseed")
            process_file(filename)

            params = {
                "network": "XX",
                "station": "YY",
                "location": "",
                "channel": "EHZ"}

            def _test_number_of_returned_traces(start, end, expected):
                params["start"] = str(UTCDateTime(start))
                params["end"] = str(UTCDateTime(end))
                response = self.client.get('/fdsnws/dataselect/1/query',
                                           params)
                if expected == 0:
                    self.assertEqual(response.status_code, 204)
                    return

                self.assertEqual(response.status_code, 200)
                self.assertTrue('OK' in response.reason_phrase)
                st = read(io.BytesIO(response.getvalue()))
                self.assertEqual(len(st), expected)

            _test_number_of_returned_traces(1, 10, 7)
            _test_number_of_returned_traces(1, 9, 6)
            _test_number_of_returned_traces(-10, 0, 3)
            _test_number_of_returned_traces(-10, -1, 1)
            _test_number_of_returned_traces(-10, -4, 1)
            _test_number_of_returned_traces(-10, -5, 1)
            _test_number_of_returned_traces(-10, -5.5, 0)
            _test_number_of_returned_traces(10, 15, 4)
            _test_number_of_returned_traces(4, 5, 6)
            _test_number_of_returned_traces(-6, -5, 1)
            _test_number_of_returned_traces(-6, -1, 1)
            _test_number_of_returned_traces(-6, 0, 3)
            _test_number_of_returned_traces(10, 15, 4)
            _test_number_of_returned_traces(11, 15, 3)
            _test_number_of_returned_traces(12, 15, 2)
            _test_number_of_returned_traces(14, 17, 2)
            _test_number_of_returned_traces(15, 17, 1)
            _test_number_of_returned_traces(18, 20, 1)
            _test_number_of_returned_traces(19, 20, 1)
            _test_number_of_returned_traces(19.5, 20, 0)

        finally:
            os.remove(filename)


class DataSelect1LiveServerTestCase(LiveServerTestCase):
    """
    Launches a live Django server in the background on setup, and shuts it down
    on teardown. This allows the use of automated test clients other than the
    Django dummy client such as obspy.clients.fdsn.Client.
    """

    def setUp(self):
        # index waveform files
        [process_file(f) for f in FILES]

    def test_query_data(self):
        # query using ObsPy
        t1 = UTCDateTime("2005-10-06T07:21:59.850000")
        t2 = UTCDateTime("2005-10-06T07:24:59.845000")
        client = FDSNClient(self.live_server_url)
        got = client.get_waveforms("", "RJOB", "", "Z", t1, t2)[0]
        expected = read(FILES[0])[0]
        np.testing.assert_equal(got.data, expected.data)
        self.assertEqual(got, expected)

    def test_query_data_wildcards(self):
        # query using wildcards
        t = UTCDateTime(2010, 3, 25, 0, 0)
        client = FDSNClient(self.live_server_url)
        # 1
        st = client.get_waveforms("TA", "A25A", "", "BHZ", t, t + 30)
        self.assertEqual(len(st), 1)
        self.assertEqual(len(st[0].data), 1201)
        self.assertEqual(st[0].id, 'TA.A25A..BHZ')
        # 2
        st = client.get_waveforms("TA", "A25A", "", "BHZ,BHN,BHE", t, t + 30)
        self.assertEqual(len(st), 3)
        # 3
        st = client.get_waveforms("TA", "A25A", "", "BH*", t, t + 30)
        self.assertEqual(len(st), 3)
        # 4
        st = client.get_waveforms("TA", "A25A", "", "BH?", t, t + 30)
        self.assertEqual(len(st), 3)
        # 5
        st = client.get_waveforms("TA", "A25A", "", "BH?,VCO", t, t + 30)
        self.assertEqual(len(st), 4)
        # 6
        st = client.get_waveforms("TA", "A25A", "", "BH?,-BHZ", t, t + 30)
        self.assertEqual(len(st), 2)
        # 7
        st = client.get_waveforms("TA", "A25A", "", "*", t, t + 30)
        self.assertEqual(len(st), 19)
        # 8
        st = client.get_waveforms("TA", "A25A", "", "*,-BHZ", t, t + 30)
        self.assertEqual(len(st), 18)
        # 9
        st = client.get_waveforms("*", "*", "*", "*", t, t + 30)
        self.assertEqual(len(st), 19)
        # 10
        st = client.get_waveforms("??", "????", "*", "???", t, t + 30)
        self.assertEqual(len(st), 19)
        # 11
        st = client.get_waveforms("?*", "?*?", "*", "?HZ", t, t + 30)
        self.assertEqual(len(st), 3)

    def test_no_wildcards(self):
        t1 = UTCDateTime(2010, 3, 25, 0, 0)
        t2 = t1 + 30
        client = FDSNClient(self.live_server_url)

        # network
        st = client.get_waveforms("TA", "*", "*", "*", t1, t2)
        self.assertEqual(len(st), 19)
        for id_ in ["T", "A", "X"]:
            self.assertRaises(FDSNException,
                              client.get_waveforms, id_, "*", "*", "*", t1, t2)
        # station
        st = client.get_waveforms("*", "A25A", "*", "*", t1, t2)
        self.assertEqual(len(st), 19)
        for id_ in ["A2", "25", "5A"]:
            self.assertRaises(FDSNException,
                              client.get_waveforms, "*", id_, "*", "*", t1, t2)
        # location
        st = client.get_waveforms("*", "*", "", "*", t1, t2)
        self.assertEqual(len(st), 19)
        # Jane does not distinguish between location ids with an empty
        # string or one or more spaces.
        # This is according to
        # http://www.fdsn.org/message-center/thread/108/
        st = client.get_waveforms("*", "*", "  ", "*", t1, t2)
        self.assertEqual(len(st), 19)
        st = client.get_waveforms("*", "*", " ", "*", t1, t2)
        self.assertEqual(len(st), 19)
        st = client.get_waveforms("*", "*", "--", "*", t1, t2)
        self.assertEqual(len(st), 19)
        for id_ in ["00", "XX", "X"]:
            self.assertRaises(FDSNException,
                              client.get_waveforms, "*", "*", id_, "*", t1, t2)
        # channel
        st = client.get_waveforms("*", "*", "*", "BHZ", t1, t2)
        self.assertEqual(len(st), 1)
        for id_ in ["B", "Z", "H"]:
            self.assertRaises(FDSNException,
                              client.get_waveforms, "*", "*", "*", id_, t1, t2)


class DataSelectMappingTestCase(LiveServerTestCase):
    """
    Launches a live Django server in the background on setup, and shuts it down
    on teardown. This allows the use of automated test clients other than the
    Django dummy client such as obspy.clients.fdsn.Client.
    """

    def setUp(self):
        # create mapping
        Mapping(
            timerange=DateTimeTZRange(
                UTCDateTime(2002, 1, 1).datetime,
                UTCDateTime(2016, 1, 2).datetime),
            network="TA", station="A25A", location="", channel="BHE",
            new_network="XX", new_station="YY", new_location="00",
            new_channel="ZZZ").save()
        ContinuousTrace.update_all_mappings()
        # index waveform files
        [process_file(f) for f in FILES]

    def tearDown(self):
        # remove mappings
        Mapping.objects.all().delete()
        ContinuousTrace.update_all_mappings()

    def test_query_mapping(self):
        t1 = UTCDateTime(2010, 3, 25, 0, 0)
        t2 = t1 + 30
        client = FDSNClient(self.live_server_url)
        # 1 - direct query fails
        self.assertRaises(FDSNException,
                          client.get_waveforms, "TA", "*", "*", "BHE", t1, t2)
        # 2 - query use mapping works
        st = client.get_waveforms("XX", "YY", "00", "ZZZ", t1, t2)
        self.assertEqual(len(st), 1)
        # 3 - TA.A25A..BHZ and TA.A25A..BHN shouldn't be affected at all
        st = client.get_waveforms("TA", "A25A", "", "BH?", t1, t2)
        self.assertEqual(len(st), 2)
