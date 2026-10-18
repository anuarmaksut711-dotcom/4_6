"""PIXEL: static frontend and server-side Telegram booking requests (Python 3.10+)."""
from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
ASTANA = timezone(timedelta(hours=5))
ROOMS = {'standard': ('Standard', 20, 900), 'duo': ('Duo', 2, 1000), 'vip': ('VIP', 5, 1500)}
GAMES = dict(zip(
    'cs2 fortnite minecraft dota2 valorant gtav gtaonline pubg apex lol rust roblox fc cod r6 overwatch2 rocketleague warthunder ets2 chrome'.split(),
    ['Counter-Strike 2', 'Fortnite', 'Minecraft', 'Dota 2', 'Valorant', 'GTA V', 'GTA Online', 'PUBG', 'Apex Legends', 'League of Legends', 'Rust', 'Roblox', 'EA Sports FC', 'Call of Duty', 'Rainbow Six Siege', 'Overwatch 2', 'Rocket League', 'War Thunder', 'Euro Truck Simulator 2', 'Google Chrome']))
PRICING = json.loads((ROOT / 'demofinal' / 'assets' / 'club-pricing.json').read_text(encoding='utf-8'))
PACKAGES = {item['id']: item for item in PRICING['packages']}
PACKAGE_POLICY = 'package-estimate-v1'


class BookingError(Exception):
    def __init__(self, status, code, message, fields=None):
        self.status, self.code, self.message, self.fields = status, code, message, fields or {}


def package_estimate(plan):
    """Site estimate: one package per PC; extra time billed by whole hours.

    These coverage rules are explicit assumptions, never a confirmed club quote.
    """
    def reject(code, message):
        raise BookingError(422, code, 'Проверьте пакет.', {'package': message})
    pid = plan.get('packageId')
    item = PACKAGES.get(pid) if isinstance(pid, str) else None
    if not item or item['room'] != plan['room'] or item['kind'] == 'hourly':
        reject('package', 'Выберите пакет выбранного зала.')
    if item.get('manualOnly'):
        reject('manual', 'Студенческий тариф согласуется по телефону.')
    guests, duration = int(plan['guests']), int(plan['duration'])
    if not 1 <= guests <= ROOMS[plan['room']][1] or not 1 <= duration <= 12:
        reject('inputs', 'Проверьте число игроков и длительность.')
    if item['kind'] == 'hours':
        covered = min(duration, item['hours']) * 60
        unused = max(0, item['hours'] - duration) * 60
    else:
        try:
            day = datetime.strptime(plan['date'], '%Y-%m-%d')
            clock = datetime.strptime(plan['time'], '%H:%M')
        except (ValueError, TypeError, KeyError):
            reject('date-time', 'Укажите дату и время для проверки интервала пакета.')
        start = clock.hour * 60 + clock.minute
        weekday = (day.weekday() + 1) % 7
        if item['end'] > 1440 and start < item['end'] - 1440:
            start += 1440
            weekday = (weekday + 6) % 7
        if weekday not in item['weekdays']:
            reject('weekday', 'Этот пакет действует только по будням. Выберите другую дату или тариф.')
        covered = max(0, min(start + duration * 60, item['end']) - max(start, item['start']))
        if not covered:
            reject('window', 'Визит не пересекается с интервалом пакета. Измените время или тариф.')
        unused = item['end'] - item['start'] - covered
    extra = (duration * 60 - covered + 59) // 60
    package_total = item['price'] * guests
    extra_total = extra * ROOMS[plan['room']][2] * guests
    return {'ok': True, 'policy': PACKAGE_POLICY, 'packageId': item['id'], 'quantity': guests,
            'unitPrice': item['price'], 'coveredMinutes': covered, 'unusedMinutes': unused,
            'extraHours': extra, 'packageTotal': package_total, 'extraTotal': extra_total,
            'total': package_total + extra_total, 'hourlyTotal': ROOMS[plan['room']][2] * guests * duration,
            'assumedWindow': bool(item.get('assumedWindow'))}


def load_settings(path=ROOT / 'env' / '.env'):
    """Only explicitly named settings; OS environment wins. Never expose values in logs."""
    values = {}
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('\"\'')
    return {key: os.environ.get(key, values.get(key, '')) for key in (
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_MESSAGE_THREAD_ID', 'PUBLIC_ORIGIN')}


def configured(settings):
    return bool(re.fullmatch(r'\d{5,}:[A-Za-z0-9_-]{20,}', settings['TELEGRAM_BOT_TOKEN'])
                and re.fullmatch(r'-?\d+|@[A-Za-z0-9_]{5,}', settings['TELEGRAM_CHAT_ID'])
                and (not settings['TELEGRAM_MESSAGE_THREAD_ID'] or re.fullmatch(r'[1-9]\d*', settings['TELEGRAM_MESSAGE_THREAD_ID'])))


def validate(payload, now=None):
    if not isinstance(payload, dict) or not isinstance(payload.get('plan'), dict) or not isinstance(payload.get('contact'), dict):
        raise BookingError(400, 'invalid', 'Проверьте данные заявки.')
    fields = {}
    contact, source = payload['contact'], payload['plan']
    name = contact.get('name', '')
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 80 or any(unicodedata.category(c).startswith('C') for c in name):
        fields['name'] = 'Укажите имя: от 2 до 80 символов.'
        name = ''
    phone = contact.get('phone', '')
    if not isinstance(phone, str) or len(phone) > 32 or not re.fullmatch(r'[+\d ()-]+', phone):
        phone = ''
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 11 and digits.startswith('8') and not phone.strip().startswith('+'):
        digits = '7' + digits[1:]
    if not 10 <= len(digits) <= 15 or digits.startswith('0'):
        fields['phone'] = 'Укажите телефон с кодом страны, например +7 700 000 00 00.'
    room = source.get('room')
    if not isinstance(room, str) or room not in ROOMS:
        fields['room'] = 'Выберите зал.'
        room = 'standard'

    def number(key, maximum):
        value = source.get(key)
        if isinstance(value, bool) or not re.fullmatch(r'\d{1,3}', str(value)) or not 1 <= int(value) <= maximum:
            fields[key] = f'Укажите целое число от 1 до {maximum}.'
            return 1
        return int(value)

    guests, duration = number('guests', ROOMS[room][1]), number('duration', 12)
    try:
        date, clock = source.get('date', ''), source.get('time', '')
        if not isinstance(date, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date):
            raise ValueError
        if not isinstance(clock, str) or not re.fullmatch(r'\d{2}:\d{2}', clock):
            raise ValueError
        start = datetime.fromisoformat(f'{date}T{clock}:00').replace(tzinfo=ASTANA)
        if start <= (now or datetime.now(ASTANA)):
            fields['date'] = 'Выберите будущие дату и время по Астане.'
    except ValueError:
        fields['date'] = 'Укажите существующие дату и время.'
        start = datetime.now(ASTANA)
    mode = source.get('mode')
    if mode not in ('hourly', 'packages'):
        fields['mode'] = 'Выберите почасовой тариф или пакеты.'
    seat, game = source.get('seat', ''), source.get('game', '')
    prefix = {'standard': 'pc', 'duo': 'duo', 'vip': 'vip'}[room]
    allowed_seats = {f'{prefix}-{i:02}' for i in range(1, ROOMS[room][1] + 1)}
    if not isinstance(seat, str) or (seat and seat not in allowed_seats):
        fields['seat'] = 'Выберите ПК в выбранном зале.'
    if not isinstance(game, str) or (game and game not in GAMES):
        fields['game'] = 'Выберите игру из списка.'
    selected = []
    estimate = None
    if mode == 'packages':
        if source.get('pricingPolicy') != PACKAGE_POLICY:
            fields['mode'] = 'Обновите страницу и проверьте предварительный расчёт пакетов.'
        elif not any(key in fields for key in ('room', 'guests', 'duration', 'date')):
            try:
                estimate = package_estimate({**source, 'room': room, 'guests': guests, 'duration': duration})
            except BookingError as error:
                fields.update(error.fields)
            if estimate:
                raw = source.get('packages')
                if not isinstance(raw, list) or len(raw) != 1 or not isinstance(raw[0], dict) or raw[0].get('id') != estimate['packageId'] or type(raw[0].get('quantity')) is not int or raw[0]['quantity'] != guests:
                    fields['package'] = 'Для каждого игрока нужен свой пакет. Проверьте число ПК.'
                else:
                    item = PACKAGES[estimate['packageId']]
                    selected = [{'id': item['id'], 'name': item['name'], 'room': room, 'price': item['price'], 'quantity': guests}]
    if source.get('nearby', False) not in (True, False):
        fields['nearby'] = 'Проверьте пожелание по посадке.'
    if fields:
        raise BookingError(422, 'validation', 'Проверьте отмеченные поля.', fields)
    return {'contact': {'name': name.strip(), 'phone': '+' + digits}, 'plan': {
        'room': room, 'guests': guests, 'duration': duration, 'date': date, 'time': clock,
        'mode': mode, 'seat': seat, 'game': game, 'nearby': source.get('nearby') is True and guests > 1,
        'packages': selected, **({'packageId': estimate['packageId'], 'pricingPolicy': PACKAGE_POLICY, 'estimate': estimate} if estimate else {})}, 'start': start}


def message_for(booking, reference):
    plan, contact, start = booking['plan'], booking['contact'], booking['start']
    room, _, hourly = ROOMS[plan['room']]
    amount = plan['estimate']['total'] if plan['mode'] == 'packages' else hourly * plan['guests'] * plan['duration']
    money = lambda n: f'{n:,}'.replace(',', ' ')
    lines = [f'Новая заявка PIXEL · {reference}', '', f'Имя: {contact["name"]}', f'Телефон: {contact["phone"]}',
             f'Зал: {room}', f'Игроки / ПК: {plan["guests"]}', f'Начало: {start:%d.%m.%Y, %H:%M} (Астана)',
             f'Длительность: {plan["duration"]} ч', f'Окончание: {start + timedelta(hours=plan["duration"]):%d.%m.%Y, %H:%M}']
    if plan['mode'] == 'packages':
        lines += ['Пакеты:'] + [f'• {p["name"]} × {p["quantity"]} — {money(p["price"] * p["quantity"])} ₸' for p in plan['packages']]
        quote = plan['estimate']
        lines += [f'Дополнительные часы: {quote["extraHours"]} ч/ПК — {money(quote["extraTotal"])} ₸.',
                  f'Предварительно за весь визит: {money(amount)} ₸.',
                  f'Пакет покрывает {quote["coveredMinutes"]} мин/ПК; неиспользовано {quote["unusedMinutes"]} мин/ПК.',
                  'МОДЕЛЬ САЙТА, НЕ ПОДТВЕРЖДЁННЫЕ УСЛОВИЯ КЛУБА: один пакет на ПК, доплата округляется вверх до часа; остаток не зачтён на будущие визиты. Подтвердите сумму с гостем.']
        if quote['assumedWindow']:
            lines.append('Интервал ночного Duo 22:00–08:00 принят как допущение модели; уточните его у гостя и клуба.')
    else:
        lines += [f'Почасовой расчёт: {money(hourly)} ₸ × {plan["guests"]} ПК × {plan["duration"]} ч = {money(amount)} ₸. Без скидок.']
    if plan['seat']:
        lines.append(f'Пожелание по месту: {room} · ПК {plan["seat"].split("-")[-1]}')
    if plan['nearby']:
        lines.append('Пожелание: сидеть рядом.')
    if plan['game']:
        lines.append(f'Игра: {GAMES[plan["game"]]}')
    lines += ['', 'Нужно связаться с гостем и подтвердить места. Это заявка, не подтверждённая бронь.']
    return '\n'.join(lines)


class TelegramSender:
    def __init__(self, settings):
        self.settings = settings

    def send(self, text):
        body = {'chat_id': self.settings['TELEGRAM_CHAT_ID'], 'text': text, 'link_preview_options': {'is_disabled': True}}
        if self.settings['TELEGRAM_MESSAGE_THREAD_ID']:
            body['message_thread_id'] = int(self.settings['TELEGRAM_MESSAGE_THREAD_ID'])
        request = Request(f'https://api.telegram.org/bot{self.settings["TELEGRAM_BOT_TOKEN"]}/sendMessage',
                          data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=12) as response:
                data = json.load(response)
            if not data.get('ok'):
                raise BookingError(502, 'delivery_failed', 'Не удалось отправить заявку. Проверьте связь или позвоните в клуб.')
        except HTTPError as error:
            # Telegram explicitly rejected the request: safe to retry the same ID later.
            if 400 <= error.code < 500:
                raise BookingError(502, 'delivery_failed', 'Не удалось отправить заявку. Попробуйте позже или позвоните в клуб.') from None
            raise BookingError(409, 'uncertain', 'Не удалось подтвердить отправку. Чтобы не создать повторную заявку, свяжитесь с клубом.') from None
        except (URLError, TimeoutError, OSError, ValueError):
            # A response may have been lost after Telegram accepted the message.
            raise BookingError(409, 'uncertain', 'Не удалось подтвердить отправку. Чтобы не создать повторную заявку, свяжитесь с клубом.') from None


class BookingService:
    def __init__(self, db_path, settings, dry_run=False, sender=None):
        self.settings, self.dry_run = settings, dry_run
        self.sender = sender or TelegramSender(settings)
        self.lock = threading.Lock()
        self.attempts = defaultdict(deque)
        self.db_path = str(db_path)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, digest TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL)')

    def connect(self):
        return sqlite3.connect(self.db_path, timeout=5)

    def submit(self, payload, client):
        if not self.dry_run and not configured(self.settings):
            raise BookingError(503, 'unavailable', 'Отправка заявок пока недоступна. Свяжитесь с клубом по телефону.')
        booking = validate(payload)
        request_id = payload.get('requestId', '')
        if not isinstance(request_id, str) or not re.fullmatch(r'[a-f0-9]{32}', request_id):
            raise BookingError(400, 'invalid', 'Не удалось подготовить заявку. Обновите страницу.')
        digest = hashlib.sha256(json.dumps({'contact': booking['contact'], 'plan': booking['plan']}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        reference = request_id[:8].upper()
        with self.lock:
            with self.connect() as db:
                # Metadata only: contacts and full requests are never written to disk.
                db.execute('DELETE FROM requests WHERE created < ?', (time.time() - 30 * 86400,))
                row = db.execute('SELECT digest, state FROM requests WHERE id=?', (request_id,)).fetchone()
                if row:
                    if row[0] != digest:
                        raise BookingError(409, 'conflict', 'Параметры заявки изменились. Проверьте план перед отправкой.')
                    if row[1] in ('sent', 'test'):
                        return {'status': row[1], 'reference': reference}
                    raise BookingError(409, 'uncertain', 'Эта заявка уже отправляется или её отправка требует проверки. Свяжитесь с клубом перед повтором.')
                now = time.monotonic()
                for key in list(self.attempts):
                    while self.attempts[key] and now - self.attempts[key][0] > 600:
                        self.attempts[key].popleft()
                    if not self.attempts[key]:
                        del self.attempts[key]
                attempts = self.attempts[client]
                if len(attempts) >= 8:
                    raise BookingError(429, 'rate_limit', 'Слишком много заявок. Подождите несколько минут или позвоните в клуб.')
                attempts.append(now)
                db.execute('INSERT INTO requests VALUES (?, ?, ?, ?)', (request_id, digest, 'sending', time.time()))
        try:
            if not self.dry_run:
                self.sender.send(message_for(booking, reference))
        except BookingError as error:
            with self.connect() as db:
                if error.code == 'delivery_failed':
                    db.execute('DELETE FROM requests WHERE id=?', (request_id,))
                else:
                    db.execute('UPDATE requests SET state=? WHERE id=?', ('uncertain', request_id))
            raise
        state = 'test' if self.dry_run else 'sent'
        with self.connect() as db:
            db.execute('UPDATE requests SET state=? WHERE id=?', (state, request_id))
        return {'status': state, 'reference': reference}


class Handler(SimpleHTTPRequestHandler):
    server_version = 'Pixel'

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cache-Control', 'no-store' if urlsplit(self.path).path.startswith('/api/') else 'no-cache')
        super().end_headers()

    def log_message(self, format, *args):
        # Do not log URL query strings, phone numbers, request bodies or tokens.
        pass

    def json_response(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def translate_path(self, path):
        translated = super().translate_path(path)
        # Validate the actual index file instead of letting send_head select it
        # after the containment check (it could be a link outside the public root).
        if Path(translated) == Path(self.directory) and urlsplit(path).path in ('/', ''):
            return str(Path(translated) / 'index.html')
        return translated

    def allowed_static(self):
        try:
            path = unquote(urlsplit(self.path).path, errors='strict').replace('\\', '/')
            # Reject controls, hidden paths, Windows drive paths and data streams.
            if any(ord(char) < 32 or ord(char) == 127 or char == ':' for char in path):
                return False
            if any(part.startswith('.') for part in path.split('/') if part):
                return False
            target = Path(self.translate_path(self.path)).resolve()
            root = Path(self.directory).resolve()
            return target.is_relative_to(root) and target.is_file()
        except (OSError, RuntimeError, ValueError):
            # Malformed encodings, invalid OS paths and link loops fail closed.
            return False

    def do_GET(self):
        if urlsplit(self.path).path == '/api/booking-config':
            service = self.server.service
            if hasattr(self.server, 'refresh_settings'):
                service.settings.update(self.server.refresh_settings())
            self.json_response(200, {'mode': 'test' if service.dry_run else 'live', 'available': service.dry_run or configured(service.settings)})
        elif self.allowed_static():
            super().do_GET()
        else:
            self.send_error(404)

    def do_HEAD(self):
        if self.allowed_static():
            super().do_HEAD()
        else:
            self.send_error(404)

    def do_POST(self):
        try:
            if urlsplit(self.path).path != '/api/bookings':
                raise BookingError(404, 'not_found', 'Страница не найдена.')
            if self.headers.get('Origin') != self.server.origin:
                raise BookingError(403, 'origin', 'Откройте форму на сайте клуба и повторите отправку.')
            if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                raise BookingError(415, 'content_type', 'Не удалось прочитать заявку.')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16384:
                raise BookingError(413, 'too_large', 'Не удалось прочитать заявку.')
            self.connection.settimeout(10)
            payload = json.loads(self.rfile.read(length))
            if hasattr(self.server, 'refresh_settings'):
                self.server.service.settings.update(self.server.refresh_settings())
            result = self.server.service.submit(payload, self.client_address[0])
            self.json_response(200, result)
        except BookingError as error:
            self.json_response(error.status, {'code': error.code, 'message': error.message, 'fields': error.fields})
        except (ValueError, UnicodeError, TimeoutError):
            self.json_response(400, {'code': 'invalid', 'message': 'Не удалось прочитать заявку. Проверьте поля.'})
        except Exception:
            # Fail closed, especially if delivery succeeded but receipt persistence failed.
            self.json_response(500, {'code': 'uncertain', 'message': 'Не удалось подтвердить отправку. Свяжитесь с клубом перед повтором.'})


def make_server(host, port, settings, dry_run=False, db_path=None, sender=None):
    origin = settings.get('PUBLIC_ORIGIN') or f'http://127.0.0.1:{port}'
    parsed = urlsplit(origin)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError('PUBLIC_ORIGIN must be the exact website origin without trailing slash.')
    if dry_run and host not in ('127.0.0.1', 'localhost', '::1'):
        raise ValueError('Dry-run is only available on loopback.')
    server = ThreadingHTTPServer((host, port), partial(Handler, directory=str(ROOT / 'demofinal')))
    server.origin = origin
    server.service = BookingService(db_path or ROOT / 'var' / ('booking-test.sqlite3' if dry_run else 'booking.sqlite3'), settings, dry_run, sender)
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8898)
    parser.add_argument('--dry-run', action='store_true', help='Local test only: no Telegram calls.')
    args = parser.parse_args()
    settings = load_settings()
    if args.dry_run:
        settings['PUBLIC_ORIGIN'] = f'http://{args.host}:{args.port}'
    server = make_server(args.host, args.port, settings, args.dry_run)
    if not args.dry_run:
        server.refresh_settings = load_settings
    print(f'PIXEL running at http://{args.host}:{args.port}; delivery={"TEST (no messages)" if args.dry_run else "configured" if configured(server.service.settings) else "not configured"}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
