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

    # Load keywords from config if available; fallback to a short default
    config_path = os.path.join(os.path.dirname(__file__), 'rss_filter_config.json')
    default_keywords = ["Yapay Zeka", "Yazılım Geliştirme", "Ekonomi", "Teknoloji"]
    keywords = default_keywords
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as cf:
                cfg = json.load(cf)
                kws = cfg.get('rss_filter_config', {}).get('keywords')
                if isinstance(kws, list) and kws:
                    # normalize unicode and strip whitespace
                    keywords = [unicodedata.normalize('NFC', str(k).strip()) for k in kws]
        except Exception as e:
            print('Failed to load rss_filter_config.json:', e)

    seen_links = set()

    for keyword in keywords:
        # restrict results to the past 7 days
        search_query = f"{keyword} when:7d"
        encoded_keyword = urllib.parse.quote(search_query)
        google_news_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(google_news_url)

        # Fetch all available articles returned by the search (no hard limit)
        for entry in feed.entries:
            if getattr(entry, 'link', None) in seen_links:
                continue
            seen_links.add(getattr(entry, 'link', None))

            fe = fg.add_entry()
            fe.id(getattr(entry, 'link', ''))
            title = unicodedata.normalize('NFC', getattr(entry, 'title', '') or '')
            fe.title(f"[{keyword}] {title}")
            fe.link(href=getattr(entry, 'link', ''))
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
