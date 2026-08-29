import feedparser
from feedgen.feed import FeedGenerator
import urllib.parse
from datetime import datetime, timezone

def fetch_and_generate_rss():
    fg = FeedGenerator()
    fg.id('https://cemrenayir-hub.github.io/rss-bot/gunluk_haberler.xml')
    fg.title('Günlük Özel Haber Özeti')
    fg.author({'name': 'Haber Botu', 'email': 'bot@example.com'})
    fg.link(href='https://cemrenayir-hub.github.io/rss-bot/', rel='alternate')
    fg.subtitle('Belirlenen konularda en güncel haber akışı.')
    fg.language('tr')

    keywords = ["Yapay Zeka", "Yazılım Geliştirme", "Ekonomi", "Teknoloji"]
    seen_links = set()

    for keyword in keywords:
        # restrict results to the past 24 hours
        search_query = f"{keyword} when:1d"
        encoded_keyword = urllib.parse.quote(search_query)
        google_news_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=tr&gl=TR&ceid=TR:tr"
        feed = feedparser.parse(google_news_url)

        # Fetch up to 5 articles per keyword
        for entry in feed.entries[:5]:
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

    # Save the output file
    fg.rss_file('gunluk_haberler.xml', pretty=True)
    print("Son 24 saatin güncel haber akışı oluşturuldu.")

if __name__ == '__main__':
    fetch_and_generate_rss()
