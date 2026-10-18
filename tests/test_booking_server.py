"""All deliveries are fake. These tests never contact Telegram."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from booking_server import ASTANA, BookingError, BookingService, TelegramSender, configured, make_server, message_for, validate, package_estimate


def payload(request_id='a' * 32):
    start = datetime.now(ASTANA) + timedelta(days=2)
    return {'requestId': request_id, 'contact': {'name': 'Тестовый гость', 'phone': '+7 (700) 000-00-00'},
            'plan': {'room': 'standard', 'guests': '2', 'duration': '2', 'date': start.strftime('%Y-%m-%d'),
                     'time': '23:00', 'mode': 'hourly', 'nearby': True, 'seat': 'pc-01', 'game': 'cs2', 'packages': []}}


class FakeSender:
    def __init__(self, error=None):
        self.messages, self.error = [], error

    def send(self, text):
        self.messages.append(text)
        if self.error:
            raise self.error


class BookingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'requests.sqlite3'
        self.settings = {'TELEGRAM_BOT_TOKEN': '123456:' + 'x' * 30, 'TELEGRAM_CHAT_ID': '-100123456',
                         'TELEGRAM_MESSAGE_THREAD_ID': '', 'PUBLIC_ORIGIN': 'http://127.0.0.1:8897'}

    def tearDown(self):
        self.temp.cleanup()

    def service(self, sender=None, dry_run=False):
        return BookingService(self.path, self.settings, dry_run, sender or FakeSender())

    def test_contacts_and_server_price(self):
        data = payload()
        data['plan']['total'] = 1
        booking = validate(data)
        text = message_for(booking, 'AAAAAAAA')
        self.assertIn('Телефон: +77000000000', text)
        self.assertIn('3 600 ₸', text)
        self.assertIn('01:00', text)
        self.assertIn('Counter-Strike 2', text)

    def test_required_contacts_and_invalid_control_characters(self):
        for contact in ({'name': '', 'phone': ''}, {'name': 'A\nB', 'phone': '+7 700 000 00 00'}, {'name': 'Гость', 'phone': '123'}):
            with self.subTest(contact=contact), self.assertRaises(BookingError) as error:
                data = payload()
                data['contact'] = contact
                validate(data)
            self.assertEqual(error.exception.status, 422)

    def test_capacity_past_duration_seat_and_game(self):
        for changes in ({'room': 'duo', 'guests': '3'}, {'date': '2020-01-01'}, {'duration': '1.5'},
                        {'duration': '13'}, {'seat': 'vip-01'}, {'game': 'unknown'}, {'date': '2026-02-30'}):
            with self.subTest(changes=changes), self.assertRaises(BookingError):
                data = payload()
                data['plan'].update(changes)
                validate(data)

    def test_legacy_packages_require_explicit_pricing_policy(self):
        data = payload()
        data['plan']['mode'] = 'packages'
        for selected in ([], [{'id': 'standard-3-hours', 'quantity': 1}],
                         [{'id': 'standard-5-hours', 'quantity': 2, 'price': 1}],
                         [{'id': 'standard-night', 'quantity': 1}],
                         [{'id': 'vip-night', 'quantity': 1}], [{'id': 'standard-day', 'quantity': 100}]):
            with self.subTest(selected=selected), self.assertRaises(BookingError):
                data['plan']['packages'] = selected
                validate(data)

    def test_package_model_scenarios_match_browser(self):
        cases = json.loads((Path(__file__).parent / 'package_quote_cases.json').read_text(encoding='utf-8'))
        for case in cases:
            with self.subTest(case=case['name']):
                if 'code' in case['expected']:
                    with self.assertRaises(BookingError) as error:
                        package_estimate(case['plan'])
                    self.assertEqual(error.exception.code, case['expected']['code'])
                else:
                    quote = package_estimate(case['plan'])
                    for key, value in case['expected'].items():
                        self.assertEqual(quote[key], value, key)

    def test_package_request_uses_server_total_and_labels_assumptions(self):
        data = payload()
        data['plan'].update(mode='packages', packageId='standard-3-hours', pricingPolicy='package-estimate-v1',
                            duration='4', packages=[{'id':'standard-3-hours','quantity':2,'price':1}], estimate={'total':1})
        booking = validate(data)
        self.assertEqual(booking['plan']['estimate']['total'], 6000)
        text = message_for(booking, 'AAAAAAAA')
        self.assertIn('Предварительно за весь визит: 6 000 ₸', text)
        self.assertIn('МОДЕЛЬ САЙТА', text)
        data['plan']['packages'][0]['quantity'] = 1
        with self.assertRaises(BookingError):
            validate(data)

    def test_success_and_duplicate_do_not_send_twice_or_store_contacts(self):
        sender = FakeSender()
        service = self.service(sender)
        first = service.submit(payload(), 'local')
        second = service.submit(payload(), 'local')
        self.assertEqual(first, second)
        self.assertEqual(first['status'], 'sent')
        self.assertEqual(len(sender.messages), 1)
        with service.connect() as db:
            rows = json.dumps(db.execute('SELECT * FROM requests').fetchall(), ensure_ascii=False)
        self.assertNotIn('Тестовый гость', rows)
        self.assertNotIn('77000000000', rows)

    def test_simultaneous_double_submit_calls_sender_once(self):
        entered, release = threading.Event(), threading.Event()
        sender = FakeSender()
        original = sender.send

        def slow(text):
            entered.set()
            release.wait(3)
            original(text)

        sender.send = slow
        service = self.service(sender)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.submit, payload(), 'local')
            self.assertTrue(entered.wait(2))
            with self.assertRaises(BookingError):
                service.submit(payload(), 'local')
            release.set()
            self.assertEqual(first.result()['status'], 'sent')
        self.assertEqual(len(sender.messages), 1)

    def test_rejected_delivery_can_retry_and_never_claims_success(self):
        sender = FakeSender(BookingError(502, 'delivery_failed', 'failed'))
        service = self.service(sender)
        with self.assertRaises(BookingError):
            service.submit(payload(), 'local')
        sender.error = None
        self.assertEqual(service.submit(payload(), 'local')['status'], 'sent')

    def test_uncertain_delivery_is_never_sent_twice(self):
        sender = FakeSender(BookingError(409, 'uncertain', 'unknown'))
        service = self.service(sender)
        for _ in range(2):
            with self.assertRaises(BookingError) as error:
                service.submit(payload(), 'local')
            self.assertEqual(error.exception.code, 'uncertain')
        self.assertEqual(len(sender.messages), 1)

    def test_id_reuse_with_different_data_is_rejected(self):
        service = self.service()
        service.submit(payload(), 'local')
        data = payload()
        data['contact']['name'] = 'Другой гость'
        with self.assertRaises(BookingError) as error:
            service.submit(data, 'local')
        self.assertEqual(error.exception.code, 'conflict')

    def test_dry_run_never_calls_sender(self):
        sender = FakeSender()
        self.assertEqual(self.service(sender, True).submit(payload(), 'local')['status'], 'test')
        self.assertEqual(sender.messages, [])

    def test_unconfigured_and_rate_limit(self):
        service = self.service()
        service.settings['TELEGRAM_BOT_TOKEN'] = ''
        self.assertFalse(configured(service.settings))
        with self.assertRaises(BookingError) as error:
            service.submit(payload(), 'local')
        self.assertEqual(error.exception.status, 503)
        service.dry_run = True
        for i in range(8):
            service.submit(payload(f'{i:032x}'), 'local')
        with self.assertRaises(BookingError) as error:
            service.submit(payload('f' * 32), 'local')
        self.assertEqual(error.exception.status, 429)

    def test_telegram_adapter_uses_server_credentials_without_markup(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return b'{"ok":true,"result":{"message_id":1}}'
        with patch('booking_server.urlopen', return_value=Response()) as mocked:
            TelegramSender(self.settings).send('Тест <без разметки>')
        request = mocked.call_args.args[0]
        body = json.loads(request.data)
        self.assertEqual(body['chat_id'], '-100123456')
        self.assertEqual(body['text'], 'Тест <без разметки>')
        self.assertNotIn('parse_mode', body)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.sender = FakeSender()
        settings = {'TELEGRAM_BOT_TOKEN': '123456:' + 'x' * 30, 'TELEGRAM_CHAT_ID': '-100123456',
                    'TELEGRAM_MESSAGE_THREAD_ID': '', 'PUBLIC_ORIGIN': 'http://127.0.0.1:8897'}
        self.server = make_server('127.0.0.1', 0, settings, db_path=Path(self.temp.name) / 'requests.sqlite3', sender=self.sender)
        self.origin = f'http://127.0.0.1:{self.server.server_port}'
        self.server.origin = self.origin
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def request(self, path, data=None, origin=None, content_type='application/json'):
        headers = {'Origin': origin or self.origin, 'Content-Type': content_type}
        request = Request(self.origin + path, data=data, headers=headers)
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, response.read()
        except HTTPError as response:
            return response.code, response.read()

    def test_http_send_and_repeat_with_fake_telegram(self):
        body = json.dumps(payload()).encode()
        status, first = self.request('/api/bookings', body)
        status2, second = self.request('/api/bookings', body)
        self.assertEqual((status, status2), (200, 200))
        self.assertEqual(first, second)
        self.assertEqual(len(self.sender.messages), 1)

    def test_cross_origin_rejected(self):
        status, _ = self.request('/api/bookings', json.dumps(payload()).encode(), origin='https://other.example')
        self.assertEqual(status, 403)
        self.assertEqual(self.sender.messages, [])

    def test_unconfigured_fails_closed_without_secrets(self):
        self.server.service.settings['TELEGRAM_BOT_TOKEN'] = ''
        status, config = self.request('/api/booking-config')
        self.assertEqual(status, 200)
        self.assertFalse(json.loads(config)['available'])
        self.assertNotIn('TELEGRAM', config.decode())
        status, _ = self.request('/api/bookings', json.dumps(payload()).encode())
        self.assertEqual(status, 503)
        self.assertEqual(self.sender.messages, [])

    def test_env_and_directory_listing_not_served(self):
        for path in ('/env/.env', '/.env', '/%2e%2e/env/.env', '/assets/'):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request('/booking.html')[0], 200)

    def test_malformed_and_windows_secret_paths_fail_closed(self):
        paths = ('/env%00', '/var%00', '/%ff', '/%ed%a0%80', '/env%5c%2eenv',
                 '/%2e%2e%5cenv%5c%2eenv', '/%252e%252e/env/%252eenv',
                 '/%252e%252e%5c%252e%252e%5cbooking_server.py',
                 '/%252e%252e\\%252e%252e\\var\\booking.sqlite3',
                 '/env/.env::$DATA', '/index.html::$DATA', '/C:/env/.env',
                 '/.git/config', '/booking_server.py', '/var/booking.sqlite3')
        for path in paths:
            for method in ('GET', 'HEAD'):
                with self.subTest(path=path, method=method):
                    connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
                    try:
                        connection.request(method, path)
                        response = connection.getresponse()
                        self.assertEqual(response.status, 404)
                        self.assertNotIn(b'TELEGRAM_BOT_TOKEN', response.read())
                    finally:
                        connection.close()
        self.assertEqual(self.request('/')[0], 200)

    def test_root_index_target_must_stay_inside_public_directory(self):
        # Model a resolved index link without requiring Windows symlink privileges.
        # Both the direct file and the implicit home page must check that target.
        public = Path(__file__).resolve().parents[1] / 'demofinal'
        outside = Path(self.temp.name) / 'private.txt'
        outside.write_text('AUDIT_PRIVATE_MARKER', encoding='utf-8')
        original_resolve = Path.resolve

        def resolve(path, *args, **kwargs):
            if path == public / 'index.html':
                return outside
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, 'resolve', resolve):
            for path in ('/', '/index.html'):
                with self.subTest(path=path):
                    status, body = self.request(path)
                    self.assertEqual(status, 404)
                    self.assertNotIn(b'AUDIT_PRIVATE_MARKER', body)

    def test_internal_exception_and_config_do_not_expose_credentials(self):
        marker = 'AUDIT_PRIVATE_MARKER'
        with patch.object(self.server.service, 'submit', side_effect=RuntimeError(marker)):
            status, body = self.request('/api/bookings', b'{}')
            self.assertEqual(status, 500)
            self.assertNotIn(marker.encode(), body)
            self.assertNotIn(b'Traceback', body)
        status, body = self.request('/api/booking-config?file=env/.env')
        self.assertEqual(status, 200)
        self.assertEqual(set(json.loads(body)), {'mode', 'available'})

    def test_bad_json_content_type_and_size(self):
        self.assertEqual(self.request('/api/bookings', b'{')[0], 400)
        self.assertEqual(self.request('/api/bookings', b'{}', content_type='text/plain')[0], 415)
        self.assertEqual(self.request('/api/bookings', b'x' * 17000)[0], 413)
        self.assertEqual(self.sender.messages, [])


if __name__ == '__main__':
    unittest.main()
