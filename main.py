import sys
import os
import argparse
import feedparser
from feedgen.feed import FeedGenerator
import urllib.parse
from datetime import datetime, timezone

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def fetch_and_generate_rss(debug=False):
    fg = FeedGenerator()
    fg.id('https://mycustomnews.local/rss')
    fg.title('Günlük Özel Haber Özeti')
    fg.author({'name': 'Haber Botu', 'email': 'bot@example.com'})
    fg.link(href='https://mycustomnews.local', rel='alternate')
    fg.subtitle('Belirlenen konulara göre otomatik derlenen haber akışı.')
    fg.language('tr')

    # İlgilendiğiniz konuları bu listeye ekleyebilirsiniz — Türkçe ve İngilizce çevre/ekoloji odaklı anahtar kelimeler
    keywords = [
        # Turkish
        "İklim", "İklim Değişikliği", "Yenilenebilir Enerji", "Biyoçeşitlilik", "Sürdürülebilirlik",
        "Doğa", "Toprak", "Koruma", "Atık Yönetimi", "Hava Kirliliği", "Su Kirliliği",
        # English
        "climate change", "biodiversity", "renewable energy", "conservation", "sustainability",
        "pollution", "ecosystem", "wildlife", "environmental policy", "waste management"
    ]
    
    seen_links = set()

    for keyword in keywords:
        encoded_keyword = urllib.parse.quote(keyword)
        google_news_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=tr&gl=TR&ceid=TR:tr"
        if debug:
            print(f"DEBUG: keyword={keyword!r}, encoded={encoded_keyword!r}")
            print(f"DEBUG: fetching URL: {google_news_url}")
        feed = feedparser.parse(google_news_url)
        if debug:
            print(f"DEBUG: feed.bozo={getattr(feed,'bozo',None)}, entries={len(getattr(feed,'entries',[]))}")
        
        for entry in feed.entries[:3]:

            if entry.link in seen_links:
                continue
            seen_links.add(entry.link)

            fe = fg.add_entry()
            fe.id(entry.link)
            fe.title(f"[{keyword}] {entry.title}")
            fe.link(href=entry.link)
            fe.description(getattr(entry, 'summary', 'Açıklama bulunamadı.'))
            
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                fe.published(pub_date)

    fg.rss_file('gunluk_haberler.xml', pretty=True)
    print("RSS akışı oluşturuldu.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a daily RSS feed')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    debug = args.debug or os.getenv('RSS_DEBUG', '').lower() in ('1', 'true', 'yes', 'on')
    fetch_and_generate_rss(debug=debug)
