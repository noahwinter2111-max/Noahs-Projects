from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
from urllib.parse import urlparse, parse_qs

VALID_PERIODS = {'1d','5d','1mo','3mo','6mo','ytd','1y','2y','5y','10y','max'}
VALID_INTERVALS = {'1m','2m','5m','15m','30m','60m','90m','1h','1d','5d','1wk','1mo','3mo'}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        sym = params.get('sym', ['AAPL'])[0].upper()
        period = params.get('period', ['1mo'])[0]
        interval = params.get('interval', ['1d'])[0]

        if not re.match(r'^[A-Z]{1,5}$', sym):
            self._json({'error': 'Invalid symbol'}, 400)
            return
        if period not in VALID_PERIODS:
            period = '1mo'
        if interval not in VALID_INTERVALS:
            interval = '1d'

        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={period}&interval={interval}&includePrePost=false'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                d = json.loads(resp.read())
            r = d['chart']['result'][0]
            q = r['indicators']['quote'][0]

            # Build OHLCV arrays, skipping None entries
            ohlcv = []
            timestamps = r.get('timestamp', [])
            for i in range(len(timestamps)):
                c = q['close'][i] if i < len(q['close']) else None
                if c is None:
                    continue
                o = q['open'][i] if i < len(q.get('open', [])) else c
                h = q['high'][i] if i < len(q.get('high', [])) else c
                l = q['low'][i] if i < len(q.get('low', [])) else c
                v = q['volume'][i] if i < len(q.get('volume', [])) else 0
                ohlcv.append({
                    't': timestamps[i],
                    'o': round(o, 2) if o else round(c, 2),
                    'h': round(h, 2) if h else round(c, 2),
                    'l': round(l, 2) if l else round(c, 2),
                    'c': round(c, 2),
                    'v': v or 0
                })

            closes = [p['c'] for p in ohlcv]
            self._json({
                'symbol': sym,
                'closes': closes,
                'ohlcv': ohlcv,
                'timestamps': [p['t'] for p in ohlcv]
            })
        except Exception as e:
            self._json({'error': str(e)}, 502)

    def _json(self, obj, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 's-maxage=60, stale-while-revalidate=120')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
