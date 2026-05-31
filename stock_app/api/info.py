from http.server import BaseHTTPRequestHandler
import json
import re
import urllib.request
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        sym = params.get('sym', ['AAPL'])[0].upper()

        if not re.match(r'^[A-Z]{1,5}$', sym):
            self._json({'error': 'Invalid symbol'}, 400)
            return

        try:
            url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1y&interval=1d&includePrePost=false'
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                d = json.loads(resp.read())

            r = d['chart']['result'][0]
            meta = r['meta']
            closes = [v for v in r['indicators']['quote'][0]['close'] if v is not None]
            vols = [v for v in r['indicators']['quote'][0]['volume'] if v is not None]

            result = {
                'symbol': sym,
                'shortName': meta.get('shortName', meta.get('longName', sym)),
                'longName': meta.get('longName', ''),
                'exchange': meta.get('fullExchangeName', meta.get('exchangeName', '')),
                'currency': meta.get('currency', 'USD'),
                'instrumentType': meta.get('instrumentType', ''),
                # 52-week from Yahoo meta (more accurate than our calculation)
                'fiftyTwoWeekHigh': meta.get('fiftyTwoWeekHigh'),
                'fiftyTwoWeekLow': meta.get('fiftyTwoWeekLow'),
                # Today's range from meta
                'dayHigh': meta.get('regularMarketDayHigh'),
                'dayLow': meta.get('regularMarketDayLow'),
            }

            # Moving averages from actual data
            if closes:
                if len(closes) >= 50:
                    result['fiftyDayAverage'] = round(sum(closes[-50:]) / 50, 2)
                if len(closes) >= 200:
                    result['twoHundredDayAverage'] = round(sum(closes[-200:]) / 200, 2)

                # Price vs 52w range percentage
                h = result.get('fiftyTwoWeekHigh')
                l = result.get('fiftyTwoWeekLow')
                price = closes[-1]
                if h and l and h != l:
                    result['fiftyTwoWeekPct'] = round((price - l) / (h - l) * 100, 1)

            # Average volume
            if vols:
                result['averageDailyVolume10Day'] = int(sum(vols[-10:]) / min(len(vols), 10))

            # Clean out None values
            result = {k: v for k, v in result.items() if v is not None}

            self._json(result)
        except Exception as e:
            self._json({'error': str(e)}, 502)

    def _json(self, obj, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 's-maxage=300, stale-while-revalidate=600')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())
