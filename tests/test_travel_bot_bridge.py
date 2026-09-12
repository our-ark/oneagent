import json
import sqlite3
import sys
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from oneagent.app.core import OneAgentApplication
from oneagent.app.notifications import notification_records
from oneagent.collaboration.handoff import digest
from oneagent.identity import load_identity
from oneagent.providers.runtime import FunctionAgentRuntime
from oneagent.providers.contracts import ChatEvent
from oneagent.travel.demo import ControlServer, launch_bot
from oneagent.travel.server import Hub, SITES
from oneagent.travel.telegram import TelegramDemo, existing_bot_reply
from tests.test_oneagent_telegram import FakeTelegramClient


class ExistingConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.memory, self.calls = {}, []
        self.active, self.max_active = 0, 0
        self.guard = threading.Lock()
        def respond(identity, prompt, **kwargs):
            key = kwargs['session_key']
            with self.guard:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                time.sleep(.04)
                self.calls.append((identity, kwargs['cwd'], key, prompt))
                if 'available_tools' in prompt:
                    payload = json.loads(prompt.rsplit('\n', 1)[1])
                    self.assertNotIn('quiet', payload['trip']['preferences'])
                    answer = 'Choose the quiet option.' if self.memory.get(key) == 'quiet' else 'Choose the busiest option.'
                    if payload['current']['message']['text'] == 'Save this hotel':
                        return json.dumps({'text':'Confirm Kumo House.', 'proposal':{'name':'trip.save_hotel','arguments':{'id':'kumo-house'}}})
                    return json.dumps({'text': answer, 'shared_context': {}})
                if 'quiet neighborhoods' in prompt:
                    self.memory[key] = 'quiet'
                return 'I will remember your preferences.'
            finally:
                with self.guard:
                    self.active -= 1
        runtime = FunctionAgentRuntime(respond, respond, lambda *_: '', lambda: (), lambda: None)
        bot_root = self.root / 'bot'
        bot_root.mkdir()
        self.bot = OneAgentApplication(load_identity(), bot_root, FakeTelegramClient(allowed_chat_id=42), runtime=runtime)
        self.addCleanup(lambda: self.bot.stop_workers())
        self.hub = Hub(self.root / 'travel', mirror_worker=False)
        self.addCleanup(lambda: self.hub.close())
        self.hub.origins = {site: f'http://127.0.0.1:{8080 + i}' for i, site in enumerate(SITES)}
        self.controller = TelegramDemo(self.hub)
        self.control = ControlServer(self.controller)
        threading.Thread(target=self.control.serve_forever, daemon=True).start()
        self.addCleanup(self.control.server_close)
        self.addCleanup(self.control.shutdown)
        self.config = self.root / 'control.json'
        self.config.write_text(json.dumps({'url': f'http://127.0.0.1:{self.control.server_port}/telegram', 'token': self.control.token, 'root': str(self.hub.root)}))
        env = patch.dict('os.environ', {'ONEAGENT_TRAVEL_CONTROL_FILE': str(self.config)})
        env.start()
        self.addCleanup(env.stop)

    def event(self, text, message_id=1):
        return SimpleNamespace(text=text, message_id=message_id, raw={'message': {'chat': {'id':42, 'type':'private'}, 'from': {'id':42}}})

    def start_travel(self):
        reply = existing_bot_reply(self.event('/traveldemo'), self.bot.root, application=self.bot)
        self.assertIn('Airside', reply)
        return self.hub.handoffs.account('telegram:42:42')

    def turn(self, owner, app, event):
        session = self.hub.channel(owner, app)
        self.hub.submit(owner, app, {'id': event, 'session_id': session, 'text': 'What would you recommend?', 'context': {}})
        for _ in range(150):
            transcript = self.hub.transcript(owner, app, session)
            output = next((output for output in transcript['outputs'] if output['in_reply_to'] == event), None)
            if output:
                return output
            if transcript['error']:
                self.fail(transcript['error'])
            time.sleep(.02)
        self.fail('No response')

    def test_pre_travel_preference_uses_actual_bot_runtime_identity_and_session_in_every_site(self):
        self.bot._natural(42, 'I always prefer quiet neighborhoods.')
        # Existing itinerary and handoffs must survive attachment to the bot.
        self.controller.handle(42, 42, 101, '/traveldemo')
        original_owner = self.hub.handoffs.account('telegram:42:42')
        old_link = self.hub.handoffs.issue(original_owner, 'flights')
        old_session = self.hub.channel(original_owner, 'flights')
        self.hub.trips.update(original_owner, {'flight_id':'pacific-101'}, 'saved-before-attach')
        owner = self.start_travel()
        self.assertEqual(owner, original_owner)
        self.assertEqual(self.hub.channel(owner, 'flights'), old_session)
        self.assertEqual(self.hub.handoffs.redeem(old_link, 'flights')[0], owner)
        for site in SITES:
            self.assertIn('quiet', self.turn(owner, site, site)['text'])
            self.assertEqual([m['source_app'] for m in self.hub.conversation(owner, site)['messages']], [site])
        self.assertEqual(self.hub.trips.get(owner)['flight_id'], 'pacific-101')
        self.assertTrue(all(identity is self.bot.identity and cwd == self.bot.root and key == 'telegram:42' for identity, cwd, key, _ in self.calls))
        self.assertEqual(len(self.calls), 4)
        # Retrying a persisted website output never re-runs reasoning.
        self.hub.worker(owner)['service'].process_once()
        self.assertEqual(len(self.calls), 4)

    def test_ordinary_telegram_and_website_turns_use_one_conversation_lock(self):
        owner = self.start_travel()
        threads = [threading.Thread(target=self.turn, args=(owner, 'hotels', 'website')), threading.Thread(target=self.bot._natural, args=(42, 'I prefer quiet neighborhoods.'))]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertEqual(self.max_active, 1)
        self.assertEqual({call[2] for call in self.calls}, {'telegram:42'})
        bridge = self.bot._travel_bridge
        with self.assertRaises(PermissionError):
            bridge.respond(owner, 99, {'current': {'app_id':'hotels', 'event_id':'intruder'}})

    def test_website_exchange_mirrors_once_with_source_and_selection_and_no_telegram_echo(self):
        self.bot._natural(42, 'I prefer quiet neighborhoods.')
        owner = self.start_travel()
        session = self.hub.channel(owner, 'hotels')
        self.hub.submit(owner, 'hotels', {'id':'hotel-question', 'session_id':session, 'text':'Does this fit?', 'context':{'selected_id':'kumo-house'}})
        for _ in range(150):
            transcript = self.hub.transcript(owner, 'hotels', session)
            if transcript['outputs']:
                break
            time.sleep(.02)
        self.assertIn('quiet', transcript['outputs'][0]['text'])
        with self.hub.worker(owner)['service'].state.lock:
            pass
        before_calls = len(self.calls)
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 1)
        mirrored = self.bot.client.sent[0][1]
        self.assertIn('Staywell · Kumo House', mirrored)
        self.assertIn('You: Does this fit?', mirrored)
        self.assertIn('OneAgent: Choose the quiet option.', mirrored)
        self.hub.deliver_mirrors()
        self.hub.worker(owner)['service'].process_once()
        self.assertEqual(len(self.bot.client.sent), 1)
        self.assertEqual(len(self.calls), before_calls)
        event = ChatEvent(cursor=20, conversation_id=42, message_id=20, text='Continue here', raw={'message':{'chat':{'id':42,'type':'private'},'from':{'id':42}}})
        self.bot.handle_event(event)
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 2)
        records = notification_records('telegram', self.bot.root)
        self.assertEqual(len([r for r in records if r.idempotency_key.startswith('travel-mirror:')]), 1)
        self.assertEqual([m['message']['text'] for m in self.hub.conversation(owner, 'hotels')['messages']], ['Does this fit?'])
        for site in ('flights', 'activities'):
            self.assertEqual(self.hub.conversation(owner, site)['messages'], [])

    def test_explicit_telegram_website_reply_uses_normal_delivery_without_mirror_echo(self):
        owner = self.start_travel()
        event = ChatEvent(cursor=21, conversation_id=42, message_id=21,
            text='/traveldemo reply hotels Compare the quiet stays',
            raw={'message':{'chat':{'id':42,'type':'private'},'from':{'id':42}}})
        self.bot.handle_event(event)
        with self.hub.worker(owner)['service'].state.lock:
            pass
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 1)
        self.assertIn('Sent to Staywell', self.bot.client.sent[0][1])
        chat = self.hub.conversation(owner, 'hotels')
        self.assertEqual(chat['messages'][0]['origin'], 'telegram')
        self.assertEqual(chat['messages'][0]['message']['text'], 'Compare the quiet stays')
        self.assertEqual(len(chat['outputs']), 1)
        self.assertEqual(self.hub.conversation(owner, 'flights')['messages'], [])
        self.assertEqual(self.hub.conversation(owner, 'activities')['messages'], [])
        self.assertFalse(any(r.idempotency_key.startswith('travel-mirror:') for r in notification_records('telegram', self.bot.root)))
        before = len(self.calls)
        existing_bot_reply(self.event(event.text, 21), self.bot.root, application=self.bot)
        self.assertEqual(len(self.calls), before)

    def test_mirrored_proposal_can_be_confirmed_privately_in_telegram(self):
        owner = self.start_travel()
        reply = self.controller.reply(owner, 'hotels', 'hotel-proposal', 'Save this hotel')
        self.assertIn('/travelconfirm hotels hotel-proposal', reply)
        with self.hub.worker(owner)['service'].state.lock:
            pass
        # An exchange already delivered by the previous version keeps its
        # original payload and ID; the new confirmation arrives separately.
        self.bot.notifications.send(42, 'Staywell\n\nYou: Save this hotel\n\nOneAgent: Confirm Kumo House.',
            idempotency_key='travel-mirror:' + digest(f'{owner}:hotels:hotel-proposal') + ':0')
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 2)
        self.assertIn('/travelconfirm hotels hotel-proposal', self.bot.client.sent[1][1])
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 2)
        self.assertIsNone(self.hub.trips.get(owner)['hotel_id'])
        reply = existing_bot_reply(self.event('/travelconfirm hotels hotel-proposal', 22), self.bot.root, application=self.bot)
        self.assertIn('Confirmed', reply)
        self.assertEqual(self.hub.trips.get(owner)['hotel_id'], 'kumo-house')
        self.assertTrue(self.hub.conversation(owner, 'hotels')['outputs'][0]['confirmed'])
        self.assertEqual(self.hub.conversation(owner, 'flights')['outputs'], [])

    def test_bot_restart_clears_web_chats_but_keeps_agent_memory_and_pending_mirrors(self):
        self.bot._natural(42, 'I prefer quiet neighborhoods.')
        owner = self.start_travel()
        self.turn(owner, 'hotels', 'before-bot-restart')
        self.hub.trips.update(owner, {'hotel_id':'kumo-house'}, 'saved-hotel')
        with self.hub.worker(owner)['service'].state.lock:
            pass
        old_bot = self.bot
        self.bot.stop_workers()
        self.bot = OneAgentApplication(old_bot.identity, old_bot.root, old_bot.client, runtime=old_bot.runtime)
        self.start_travel()
        for site in SITES:
            self.assertEqual(self.hub.conversation(owner, site)['messages'], [])
            self.assertEqual(self.hub.conversation(owner, site)['outputs'], [])
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 1)
        self.assertIn('Choose the quiet option.', self.bot.client.sent[0][1])
        self.assertEqual(self.hub.trips.get(owner)['hotel_id'], 'kumo-house')
        self.assertIn('quiet', self.turn(owner, 'hotels', 'after-bot-restart')['text'])
        self.assertEqual([m['event_id'] for m in self.hub.conversation(owner, 'hotels')['messages']], ['after-bot-restart'])
        # Reattaching the same running bot is not a restart.
        self.start_travel()
        self.assertEqual(len(self.hub.conversation(owner, 'hotels')['messages']), 1)

    def test_failed_mirror_recovers_after_bot_and_backend_restart_without_reasoning_again(self):
        owner = self.start_travel()
        output = self.turn(owner, 'activities', 'activity-question')
        with self.hub.worker(owner)['service'].state.lock:
            pass
        count = len(self.calls)
        with patch.object(self.bot.client, 'send_message', side_effect=OSError('temporary outage')):
            self.hub.deliver_mirrors()
        records = notification_records('telegram', self.bot.root)
        mirror = next(r for r in records if r.idempotency_key.startswith('travel-mirror:'))
        self.assertEqual(mirror.status, 'retryable_failure')
        self.assertEqual(len(self.bot.client.sent), 0)
        old_bot = self.bot
        self.bot.stop_workers()
        self.hub.close()
        self.hub = Hub(self.root / 'travel', mirror_worker=False)
        self.controller = TelegramDemo(self.hub)
        self.control.controller = self.controller
        self.bot = OneAgentApplication(old_bot.identity, old_bot.root, old_bot.client, runtime=old_bot.runtime)
        self.bot.start()
        for _ in range(100):
            if self.hub.bot_route(owner)[2] == self.bot._travel_bridge.token:
                break
            time.sleep(.03)
        with sqlite3.connect(self.hub.db_path) as db:
            db.execute('UPDATE mirror_outbox SET next_attempt=0')
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 1)
        self.assertIn(output['text'], self.bot.client.sent[0][1])
        self.assertEqual(len(self.calls), count)
        recovered = next(r for r in notification_records('telegram', self.bot.root) if r.idempotency_key == mirror.idempotency_key)
        self.assertEqual(recovered.status, 'delivered')
        with sqlite3.connect(self.hub.db_path) as db:
            self.assertEqual(db.execute('SELECT status FROM mirror_outbox').fetchone()[0], 'delivered')

    def test_restart_recovers_saved_browser_reply_before_mirror_was_queued(self):
        owner = self.start_travel()
        with patch.object(self.hub, 'queue_mirror', side_effect=OSError('crash before queue')):
            with self.assertLogs('oneagent.travel.server', level='ERROR'):
                self.turn(owner, 'flights', 'saved-before-crash')
                with self.hub.worker(owner)['service'].state.lock:
                    pass
        count = len(self.calls)
        self.hub.close()
        self.hub = Hub(self.root / 'travel', mirror_worker=False)
        self.control.controller = TelegramDemo(self.hub)
        config = json.loads(self.config.read_text())
        self.bot._travel_bridge.attach(config, 42)
        for _ in range(100):
            with sqlite3.connect(self.hub.db_path) as db:
                queued = db.execute('SELECT 1 FROM mirror_outbox').fetchone()
            if queued:
                break
            time.sleep(.03)
        self.assertIsNotNone(queued)
        self.hub.deliver_mirrors()
        self.assertEqual(len(self.bot.client.sent), 1)
        self.assertEqual(len(self.calls), count)

    def test_stopped_travel_does_not_intercept_ordinary_chat_with_backend_down(self):
        self.start_travel()
        existing_bot_reply(self.event('/traveldemo stop', 2), self.bot.root, application=self.bot)
        with patch('oneagent.travel.bot_bridge.local_request', side_effect=RuntimeError('backend down')):
            self.assertIsNone(existing_bot_reply(self.event('Ordinary conversation', 3), self.bot.root, application=self.bot))
            self.assertIn('unavailable', existing_bot_reply(self.event('/traveldemo', 4), self.bot.root, application=self.bot))


class TravelLauncherTests(unittest.TestCase):
    def test_launcher_uses_normal_bot_and_absolute_control_file(self):
        with patch('oneagent.travel.demo.subprocess.Popen') as launch:
            launch_bot(Path('control.json'))
        args, kwargs = launch.call_args
        self.assertEqual(args[0], [sys.executable, '-c', "from oneagent.app.core import main; main('telegram')"])
        self.assertEqual(kwargs['env']['ONEAGENT_TRAVEL_CONTROL_FILE'], str(Path('control.json').resolve()))
        self.assertTrue(kwargs['start_new_session'])


if __name__ == '__main__':
    unittest.main()
