from http.cookiejar import CookieJar
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, Request

from oneagent.travel.domain import CATALOG, TravelMessageStore, travel_tools
from oneagent.travel.server import Hub, WebServer


class TravelDomainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tools = travel_tools()

    def test_catalog_tools_are_read_only_and_no_trip_actions_exist(self):
        self.assertEqual({tool['name'] for tool in self.tools.descriptions()},
                         {f'{site}.{action}' for site in ('flights', 'hotels', 'activities') for action in ('search', 'get')})
        self.assertTrue(all(not tool['mutating'] for tool in self.tools.descriptions()))
        hotel = self.tools.invoke('hotels.get', {'id':'kumo-house'}, owner='alice', request_id='lookup')
        self.assertEqual(hotel['nightly_cents'], 16000)
        for name in ('trip.get', 'trip.update_brief', 'trip.save_flight', 'trip.save_hotel', 'trip.save_activity'):
            with self.assertRaises(KeyError):
                self.tools.invoke(name, {}, owner='alice', request_id='removed')
        with self.assertRaises(ValueError):
            self.tools.invoke('hotels.get', {'id':'invented'}, owner='alice', request_id='bad')

    def test_app_enriches_selection_with_authoritative_catalog(self):
        store = TravelMessageStore(self.root / 'flight.sqlite', 'flights')
        session = store.session('alice')['session_id']
        event = store.message('alice', {'id':'m', 'session_id':session, 'text':'This?', 'context': {'selected_id':'pacific-101','price_cents':1}})
        self.assertEqual(event['context']['selected_object']['price_cents'], 72000)
        self.assertNotIn('price_cents', event['context'])
        with self.assertRaises(ValueError):
            store.message('alice', {'id':'bad','session_id':session,'text':'This?','context':{'selected_id':'bad'}})


class TravelHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.seen = []
        def factory(owner):
            def respond(payload, key):
                self.seen.append((owner, key, payload))
                current = payload['current']['context'].get('selected_object', {})
                return {'text': f"[Fixture] {current.get('name', 'Your trip')}; previous turns: {len(payload['history'])}"}
            return respond
        self.hub = Hub(self.root, responder_factory=factory)
        self.addCleanup(self.hub.close)
        self.web = WebServer(('127.0.0.1', 0), self.hub, self.root)
        threading.Thread(target=self.web.serve_forever, daemon=True).start()
        self.addCleanup(self.web.server_close)
        self.addCleanup(self.web.shutdown)
        self.origin = self.web.public_origin
        self.browser = build_opener(HTTPCookieProcessor(CookieJar()))
        self.boot = self.request('session')

    def request(self, route, body=None, browser=None, csrf=None):
        headers = {'Content-Type': 'application/json'}
        if body is not None:
            headers.update({'Origin':self.origin, 'X-CSRF-Token':csrf or self.boot['csrf']})
        req = Request(self.origin + '/api/' + route, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with (browser or self.browser).open(req, timeout=5) as response:
            return json.load(response)

    def wait_reply(self, app, session):
        for _ in range(100):
            value = self.request(f'transcript?app_id={app}&session_id={session}')
            if value['outputs']:
                return value
            if value['error']:
                self.fail(value['error'])
            time.sleep(.03)
        self.fail('No reply')

    def test_two_app_flow_keeps_choices_in_private_agent_history(self):
        a = self.request('sessions', {'app_id':'flights'})['session_id']
        self.request('messages', {'app_id':'flights','id':'a','session_id':a,'text':'I prefer quiet places. What about this flight?','context':{'selected_id':'pacific-101'}})
        first = self.wait_reply('flights', a)
        self.assertIn('Pacific Air', first['outputs'][0]['text'])
        b = self.request('sessions', {'app_id':'hotels'})['session_id']
        self.request('messages', {'app_id':'hotels','id':'b','session_id':b,'text':'Does this work with my flight?','context':{'selected_id':'kumo-house'}})
        second = self.wait_reply('hotels', b)
        self.assertIn('previous turns: 1', second['outputs'][0]['text'])
        self.assertEqual(self.seen[0][1], self.seen[1][1])
        self.assertIn('quiet', self.seen[1][2]['history'][0]['event']['message']['text'])

    def test_owner_binding_and_csrf(self):
        session = self.request('sessions', {'app_id':'home'})['session_id']
        other = build_opener(HTTPCookieProcessor(CookieJar()))
        boot = self.request('session', browser=other)
        self.assertNotEqual(boot['visitor'], self.boot['visitor'])
        with self.assertRaises(HTTPError) as denied:
            self.request(f'transcript?app_id=home&session_id={session}', browser=other)
        self.assertEqual(denied.exception.code,403)
        with self.assertRaises(HTTPError) as denied:
            self.request('preferences', {'id':'x','budget_cents':123000,'preferences':'x'}, csrf='invalid')
        self.assertEqual(denied.exception.code,403)
        self.assertEqual(self.request('session')['visitor'], self.boot['visitor'])

    def test_new_visitor_has_new_identity_and_empty_chat(self):
        self.request('new-trip', {})
        new = self.request('session')
        self.assertNotEqual(new['visitor'], self.boot['visitor'])
        self.assertEqual(self.request('conversation')['messages'], [])

    def test_reopening_a_pending_session_resumes_processing(self):
        session = self.request('sessions', {'app_id':'home'})['session_id']
        self.hub.stores['home'].message(self.boot['visitor'], {'id':'queued','session_id':session,'text':'Hello','context':{}})
        result = self.wait_reply('home', session)
        self.assertEqual(result['outputs'][0]['in_reply_to'], 'queued')

    def test_invalid_selection_never_enters_agent_history(self):
        session = self.request('sessions', {'app_id':'flights'})['session_id']
        with self.assertRaises(HTTPError):
            self.request('messages', {'app_id':'flights','id':'bad','session_id':session,'text':'hello','context':{'selected_id':'invented'}})
        self.assertEqual(self.seen, [])

class TravelReasoningTests(unittest.TestCase):
    def test_stale_action_request_cannot_mutate_state_and_answer_has_no_proposal(self):
        from oneagent.travel.agent import TravelResponder
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            class Runtime:
                def __init__(self):
                    self.turn = 0
                def respond(self, identity, message, **kwargs):
                    self.turn += 1
                    payload = json.loads(message.rsplit('\n', 1)[1])
                    self_test.assertNotIn('trip', payload)
                    if self.turn == 1:
                        return json.dumps({'tool': {'name':'trip.save_hotel','arguments':{'id':'kumo-house'}}})
                    self_test.assertIn('error', payload['tool_results'][0]['result'])
                    return json.dumps({'text':"I'll remember Kumo House.",
                                       'proposal':{'name':'trip.save_hotel','arguments':{'id':'kumo-house'}},
                                       'shared_context':{'budget_cents':150000}})
            self_test = self
            respond = TravelResponder('alice', root / 'runtime', travel_tools(), runtime=Runtime())
            output = respond({'current':{'app_id':'hotels','event_id':'m1','context':{},'share':[]},'history':[]}, 'alice')
            self.assertEqual(output, {'text':"I'll remember Kumo House.", 'shared_context':{}})
            self.assertFalse((root / 'trips.sqlite').exists())


if __name__ == '__main__':
    unittest.main()
