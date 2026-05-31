from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import xml.etree.ElementTree as ET
import re
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed

FEEDS = [
    ('https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,GOOGL,AMZN,NVDA,TSLA,META&region=US&lang=en-US', 'Yahoo Finance'),
    ('https://feeds.finance.yahoo.com/rss/2.0/headline?region=US&lang=en-US', 'Yahoo Finance'),
    ('https://rss.nytimes.com/services/xml/rss/nyt/Business.xml', 'NY Times'),
    ('https://feeds.bbci.co.uk/news/business/rss.xml', 'BBC Business'),
    ('https://www.cnbc.com/id/100003114/device/rss/rss.html', 'CNBC'),
    ('https://feeds.marketwatch.com/marketwatch/topstories/', 'MarketWatch'),
]

def strip_html(text):
    if not text:
        return ''
    text = unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:200]

def parse_rss(xml_text, source_name):
    items = []
    try:
        root = ET.fromstring(xml_text)
        # Handle both RSS and Atom
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'media': 'http://search.yahoo.com/mrss/'}

        # RSS format
        for item in root.findall('.//item'):
            title = item.findtext('title', '').strip()
            desc = strip_html(item.findtext('description', ''))
            link = item.findtext('link', '')
            pub = item.findtext('pubDate', '')

            # Try to get image
            img = ''
            media = item.find('media:content', ns)
            if media is not None:
                img = media.get('url', '')
            enclosure = item.find('enclosure')
            if not img and enclosure is not None:
                img = enclosure.get('url', '')

            if title:
                items.append({
                    'title': title[:120],
                    'description': desc,
                    'source': source_name,
                    'link': link,
                    'pubDate': pub,
                    'image': img,
                })

        # Atom format
        if not items:
            for entry in root.findall('.//atom:entry', ns):
                title = entry.findtext('atom:title', '', ns).strip()
                desc = strip_html(entry.findtext('atom:summary', '', ns) or entry.findtext('atom:content', '', ns))
                link_el = entry.find('atom:link', ns)
                link = link_el.get('href', '') if link_el is not None else ''
                pub = entry.findtext('atom:published', '', ns) or entry.findtext('atom:updated', '', ns)
                if title:
                    items.append({
                        'title': title[:120],
                        'description': desc,
                        'source': source_name,
                        'link': link,
                        'pubDate': pub,
                        'image': '',
                    })
    except Exception:
        pass
    return items

def fetch_feed(url, source):
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=6) as resp:
            xml_text = resp.read().decode('utf-8', errors='replace')
        return parse_rss(xml_text, source)
    except Exception:
        return []

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        sym = params.get('sym', [None])[0]

        all_items = []

        if sym:
            # Stock-specific news
            sym = sym.upper()
            if not re.match(r'^[A-Z]{1,5}$', sym):
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Invalid symbol'}).encode())
                return
            ticker_feed = f'https://feeds.finance.yahoo.com/rss/2.0/headline?s={sym}&region=US&lang=en-US'
            items = fetch_feed(ticker_feed, 'Yahoo Finance')
            all_items.extend(items[:15])
        else:
            # General market news — fetch all feeds in parallel
            with ThreadPoolExecutor(max_workers=6) as pool:
                futures = {pool.submit(fetch_feed, url, source): source for url, source in FEEDS}
                for f in as_completed(futures):
                    items = f.result()
                    all_items.extend(items[:8])

        # Deduplicate by title similarity
        seen = set()
        unique = []
        for item in all_items:
            key = item['title'][:50].lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)

        # Limit to 30 articles
        unique = unique[:30]

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 's-maxage=120, stale-while-revalidate=300')
        self.end_headers()
        self.wfile.write(json.dumps(unique).encode())
