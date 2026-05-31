from http.server import BaseHTTPRequestHandler
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SYMS = 'AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META,JPM,V,XOM,AMD,NFLX,DIS,BA,COIN,PLTR,SOFI,UBER,SHOP'

def get_quote(sym):
    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=5d&interval=1d&includePrePost=false'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=5) as resp:
        d = json.loads(resp.read())
    r = d['chart']['result'][0]
    meta = r['meta']
    quotes = r['indicators']['quote'][0]
    closes = quotes['close']
    opens = quotes['open']
    highs = quotes['high']
    lows = quotes['low']
    vols = quotes['volume']

    valid_closes = [c for c in closes if c is not None]
    if len(valid_closes) < 2:
        return None

    price = valid_closes[-1]
    prev = valid_closes[-2]
    change = round(price - prev, 2)
    pct = round((change / prev) * 100, 2) if prev else 0

    last_open = opens[-1] if opens[-1] is not None else 0
    last_high = highs[-1] if highs[-1] is not None else 0
    last_low = lows[-1] if lows[-1] is not None else 0
    last_vol = vols[-1] if vols[-1] is not None else 0

    return {
        'symbol': sym,
        'name': meta.get('shortName', meta.get('longName', sym)),
        'price': round(price, 2),
        'change': change,
        'changePct': pct,
        'open': round(last_open, 2),
        'high': round(last_high, 2),
        'low': round(last_low, 2),
        'prevClose': round(prev, 2),
        'volume': last_vol or 0,
    }

def fetch_one(sym):
    try:
        return sym, get_quote(sym)
    except Exception:
        return sym, None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        data = {}
        syms = SYMS.split(',')

        # Fetch all 19 stocks in parallel (~1-2s instead of ~15-19s)
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {pool.submit(fetch_one, s): s for s in syms}
            for f in as_completed(futures):
                sym, result = f.result()
                if result:
                    data[sym] = result

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 's-maxage=30, stale-while-revalidate=60')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
