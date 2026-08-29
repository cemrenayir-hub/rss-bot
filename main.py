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
    fg.title('Ekoloji Haber Servisi')
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
    search_both = False
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as cf:
                cfg = json.load(cf)
                cats = cfg.get('rss_filter_config', {}).get('categories')
                if isinstance(cats, list) and cats:
                    loaded = []
                    for c in cats:
                        name = str(c.get('name', '')).strip() or 'Category'
                        kws = c.get('keywords', []) if isinstance(c.get('keywords', []), list) else []
                        kws_norm = [unicodedata.normalize('NFC', str(k).strip()) for k in kws if str(k).strip()]
                        if kws_norm:
                            loaded.append({'name': name, 'keywords': kws_norm})
                    if loaded:
                        categories = loaded
                # load follow_urls (optional)
                follow_urls = cfg.get('rss_filter_config', {}).get('follow_urls', [])
                if not isinstance(follow_urls, list):
                    follow_urls = []
        except Exception as e:
            print('Failed to load rss_filter_config.json:', e)
            follow_urls = []
    else:
        follow_urls = []
        search_both = False

    # Collect candidate entries first so we can deduplicate similar items across sources
    seen_links = set()
    candidates = []

    # Iterate categories and their keywords; label entries by category name
    for cat in categories:
        cat_name = cat.get('name', 'Category')
        for keyword in cat.get('keywords', []):
            # restrict results to the past 7 days
            search_query = f"{keyword} when:7d"
            encoded_keyword = urllib.parse.quote(search_query)
            # Query Google News RSS without language-specific parameters
            google_news_url = f"https://news.google.com/rss/search?q={encoded_keyword}"
            feed = feedparser.parse(google_news_url)

                # Apply per-keyword cap if configured
                cap = None
                try:
                    with open(config_path, 'r', encoding='utf-8') as cf_cap:
                        cap = int(json.load(cf_cap).get('rss_filter_config', {}).get('per_keyword_cap', 0))
                except Exception:
                    cap = 0

                entries_to_iterate = feed.entries if not cap or cap <= 0 else feed.entries[:cap]

                # Fetch capped articles returned by the search
                for entry in entries_to_iterate:
                    link = getattr(entry, 'link', None)
                    if not link or link in seen_links:
                        continue
                    seen_links.add(link)

                    title = unicodedata.normalize('NFC', getattr(entry, 'title', '') or '')
                    desc = unicodedata.normalize('NFC', getattr(entry, 'summary', '') or 'Açıklama bulunamadı.')
                    pub_date = None
                    if hasattr(entry, 'published_parsed'):
                        try:
                            pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        except Exception:
                            pub_date = None
                    candidates.append({
                        'link': link,
                        'title': title,
                        'desc': desc,
                        'pub_date': pub_date,
                        'category': cat_name
                    })

    # Process follow_urls (optional) — accept list of strings or objects {url, category}
    for fu in (follow_urls or []):
        if isinstance(fu, dict):
            url = str(fu.get('url', '')).strip()
            cat_name = str(fu.get('category', '')).strip() or 'Followed'
        else:
            url = str(fu).strip()
            cat_name = 'Followed'
        if not url:
            continue
        try:
            feed = feedparser.parse(url)
        except Exception:
            feed = None
        if feed and getattr(feed, 'entries', None):
            for entry in feed.entries:
                link = getattr(entry, 'link', None)
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                title = unicodedata.normalize('NFC', getattr(entry, 'title', '') or '')
                desc = unicodedata.normalize('NFC', getattr(entry, 'summary', '') or '')
                pub_date = None
                if hasattr(entry, 'published_parsed'):
                    try:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    except Exception:
                        pub_date = None
                candidates.append({
                    'link': link,
                    'title': title,
                    'desc': desc,
                    'pub_date': pub_date,
                    'category': cat_name
                })
        else:
            # fallback: include the URL as a single entry
            if url in seen_links:
                continue
            seen_links.add(url)
            candidates.append({
                'link': url,
                'title': url,
                'desc': 'Followed URL (no feed entries).',
                'pub_date': None,
                'category': cat_name
            })

    # Deduplicate similar items server-side using title+description similarity
    try:
        import difflib, re

        def normalize_for_compare(s):
            s = unicodedata.normalize('NFD', s or '')
            # remove diacritics
            s = ''.join(ch for ch in s if not unicodedata.combining(ch))
            s = s.lower()
            # remove punctuation
            s = re.sub(r"[^\w\s]", ' ', s)
            s = re.sub(r"\s+", ' ', s).strip()
            return s

        threshold = 0.85
        dedupe_keep = 'earliest'
        try:
            with open(config_path, 'r', encoding='utf-8') as cf:
                cfg = json.load(cf)
                threshold = float(cfg.get('rss_filter_config', {}).get('dedupe_threshold', threshold))
                dedupe_keep = str(cfg.get('rss_filter_config', {}).get('dedupe_keep', dedupe_keep))
        except Exception:
            pass

        # prepare normalized text
        for c in candidates:
            c['cmp_text'] = normalize_for_compare((c.get('title','') + ' ' + c.get('desc','')))

        # sort to prefer earliest when keeping earliest
        if dedupe_keep == 'earliest':
            candidates.sort(key=lambda x: x['pub_date'] if x['pub_date'] is not None else datetime.max)
        else:
            candidates.sort(key=lambda x: x['pub_date'] if x['pub_date'] is not None else datetime.min, reverse=True)

        keep = []
        skipped = [False]*len(candidates)
        for i in range(len(candidates)):
            if skipped[i]:
                continue
            a = candidates[i]
            keep.append(a)
            for j in range(i+1, len(candidates)):
                if skipped[j]:
                    continue
                b = candidates[j]
                ratio = difflib.SequenceMatcher(None, a['cmp_text'], b['cmp_text']).ratio()
                if ratio >= threshold:
                    skipped[j] = True
        unique_entries = keep
    except Exception as e:
        print('Deduplication failed, falling back to raw candidates:', e)
        unique_entries = candidates

    # Order entries newest first
    try:
        # treat missing pub_date as very old so they appear last
        epoch = datetime(1970,1,1, tzinfo=timezone.utc)
        unique_entries.sort(key=lambda x: x.get('pub_date') or epoch, reverse=True)
    except Exception:
        pass

    # Build feed from unique entries (newest to oldest)
    for e in unique_entries:
        fe = fg.add_entry()
        fe.id(e.get('link',''))
        fe.title(f"[{e.get('category','')}] {e.get('title','')}")
        fe.link(href=e.get('link',''))
        fe.description(e.get('desc',''))
        if e.get('pub_date'):
            fe.published(e.get('pub_date'))

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
