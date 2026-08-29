import feedparser
from feedgen.feed import FeedGenerator
import urllib.parse
from datetime import datetime, timezone
import json
import os
import unicodedata


def fetch_and_generate_rss():
    fg = FeedGenerator()
    fg.id('https://cemrenayir-hub.github.io/rss-bot/gunluk_haberler.xml')
    fg.title('Günlük Özel Haber Özeti')
    fg.author({'name': 'Haber Botu', 'email': 'bot@example.com'})
    fg.link(href='https://cemrenayir-hub.github.io/rss-bot/', rel='alternate')
    fg.subtitle('Belirlenen konularda en güncel haber akışı.')
    fg.language('tr')

    # Load categories from config if available; fallback to a single default category
    config_path = os.path.join(os.path.dirname(__file__), 'rss_filter_config.json')
    categories = [
        {
            'name': 'Default',
            'hl': 'tr',
            'gl': 'TR',
            'ceid': 'TR:tr',
            'keywords': ["Yapay Zeka", "Yazılım Geliştirme", "Ekonomi", "Teknoloji"]
        }
    ]
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as cf:
                cfg = json.load(cf)
                cats = cfg.get('rss_filter_config', {}).get('categories')
                if isinstance(cats, list) and cats:
                    # normalize keywords in each category
                    loaded = []
                    for c in cats:
                        name = str(c.get('name', '')).strip() or 'Category'
                        hl = str(c.get('hl', 'en'))
                        gl = str(c.get('gl', 'US'))
                        ceid = str(c.get('ceid', f'{gl}:{hl}'))
                        kws = c.get('keywords', []) if isinstance(c.get('keywords', []), list) else []
                        kws_norm = [unicodedata.normalize('NFC', str(k).strip()) for k in kws if str(k).strip()]
                        if kws_norm:
                            loaded.append({'name': name, 'hl': hl, 'gl': gl, 'ceid': ceid, 'keywords': kws_norm})
                    if loaded:
                        categories = loaded
        except Exception as e:
            print('Failed to load rss_filter_config.json:', e)

    seen_links = set()

    # Iterate categories and their keywords; label entries by category name
    for cat in categories:
        cat_name = cat.get('name', 'Category')
        hl = cat.get('hl', 'en')
        gl = cat.get('gl', 'US')
        ceid = cat.get('ceid', f'{gl}:{hl}')
        for keyword in cat.get('keywords', []):
            # restrict results to the past 7 days
            search_query = f"{keyword} when:7d"
            encoded_keyword = urllib.parse.quote(search_query)
            google_news_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl={hl}&gl={gl}&ceid={ceid}"
            feed = feedparser.parse(google_news_url)

            # Fetch all available articles returned by the search (no hard limit)
            for entry in feed.entries:
                link = getattr(entry, 'link', None)
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                fe = fg.add_entry()
                fe.id(link)
                title = unicodedata.normalize('NFC', getattr(entry, 'title', '') or '')
                fe.title(f"[{cat_name}] {title}")
                fe.link(href=link)
                desc = unicodedata.normalize('NFC', getattr(entry, 'summary', '') or 'Açıklama bulunamadı.')
                fe.description(desc)

                if hasattr(entry, 'published_parsed'):
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    fe.published(pub_date)

    # Save the output file explicitly as UTF-8 to avoid encoding issues
    rss_bytes = fg.rss_str(pretty=True)
    try:
        with open('gunluk_haberler.xml', 'wb') as out:
            if isinstance(rss_bytes, bytes):
                out.write(rss_bytes)
            else:
                out.write(rss_bytes.encode('utf-8'))
    except Exception as e:
        print('Failed to write feed file:', e)
        return

    print("Son 7 günün güncel haber akışı oluşturuldu.")


if __name__ == '__main__':
    fetch_and_generate_rss()
