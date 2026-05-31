import http.server
import json
import os
import threading
import time
import yfinance as yf

PORT = int(os.environ.get('PORT', 8877))
DIR = os.path.dirname(os.path.abspath(__file__))

WATCHLIST = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'JPM', 'V', 'XOM',
             'AMD', 'NFLX', 'DIS', 'BA', 'COIN', 'PLTR', 'SOFI', 'UBER', 'SQ', 'SHOP']

quote_cache = {}
cache_lock = threading.Lock()
last_fetch = 0


def fetch_quotes():
    global last_fetch
    try:
        tickers = yf.Tickers(' '.join(WATCHLIST))
        data = {}
        for sym in WATCHLIST:
            try:
                t = tickers.tickers[sym]
                info = t.fast_info
                h = t.history(period='5d')
                if h.empty:
                    continue
                prev_close = float(info.previous_close) if hasattr(info, 'previous_close') else float(h['Close'].iloc[-2]) if len(h) > 1 else 0
                price = float(h['Close'].iloc[-1])
                change = price - prev_close
                change_pct = (change / prev_close * 100) if prev_close else 0
                data[sym] = {
                    'symbol': sym,
                    'name': t.info.get('shortName', sym) if hasattr(t, 'info') else sym,
                    'price': round(price, 2),
                    'change': round(change, 2),
                    'changePct': round(change_pct, 2),
                    'open': round(float(h['Open'].iloc[-1]), 2),
                    'high': round(float(h['High'].iloc[-1]), 2),
                    'low': round(float(h['Low'].iloc[-1]), 2),
                    'prevClose': round(prev_close, 2),
                    'volume': int(h['Volume'].iloc[-1]),
                }
            except Exception:
                pass
        with cache_lock:
            quote_cache.update(data)
            last_fetch = time.time()
    except Exception as e:
        print(f'Quote fetch error: {e}')


def bg_fetcher():
    while True:
        fetch_quotes()
        time.sleep(15)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)

    def do_GET(self):
        if self.path == '/api/quotes':
            self._json(quote_cache)
        elif self.path.startswith('/api/chart/'):
            parts = self.path.split('/')
            sym = parts[3].split('?')[0].upper()
            query = self.path.split('?')[1] if '?' in self.path else ''
            params = dict(p.split('=') for p in query.split('&') if '=' in p)
            period = params.get('period', '1mo')
            interval = params.get('interval', '1d')
            self._chart(sym, period, interval)
        elif self.path.startswith('/api/info/'):
            sym = self.path.split('/api/info/')[1].split('?')[0].upper()
            self._info(sym)
        else:
            if self.path == '/':
                self.path = '/index.html'
            super().do_GET()

    def _chart(self, sym, period, interval):
        try:
            t = yf.Ticker(sym)
            h = t.history(period=period, interval=interval)
            if h.empty:
                self._json({'error': 'no data'}, 404)
                return
            closes = [round(float(v), 2) for v in h['Close'].tolist() if v == v]
            timestamps = [int(ts.timestamp()) for ts in h.index]
            self._json({'symbol': sym, 'closes': closes, 'timestamps': timestamps})
        except Exception as e:
            self._json({'error': str(e)}, 502)

    def _info(self, sym):
        try:
            t = yf.Ticker(sym)
            info = t.info
            keys = ['shortName', 'longName', 'marketCap', 'trailingPE', 'forwardPE',
                    'epsTrailingTwelveMonths', 'epsForward', 'dividendYield',
                    'trailingAnnualDividendYield', 'beta', 'fiftyTwoWeekHigh',
                    'fiftyTwoWeekLow', 'fiftyDayAverage', 'twoHundredDayAverage',
                    'averageDailyVolume10Day', 'bookValue', 'priceToBook',
                    'exchange', 'currency', 'sector', 'industry']
            result = {k: info.get(k) for k in keys if info.get(k) is not None}
            result['symbol'] = sym
            self._json(result)
        except Exception as e:
            self._json({'error': str(e)}, 502)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    print('Fetching initial quotes...')
    fetch_quotes()
    t = threading.Thread(target=bg_fetcher, daemon=True)
    t.start()
    print(f'Stock server running on port {PORT}')
    with http.server.HTTPServer(('0.0.0.0', PORT), Handler) as httpd:
        httpd.serve_forever()
