import json, os, urllib.parse, feedparser
p=os.path.join(os.path.dirname(__file__),'rss_filter_config.json')
if not os.path.exists(p):
    print('config missing')
    raise SystemExit(1)
with open(p,'r',encoding='utf-8') as f:
    cfg=json.load(f)
cats=cfg.get('rss_filter_config',{}).get('categories', [])
search_both = cfg.get('rss_filter_config', {}).get('search_both_languages', False)
print('Categories:', [c.get('name') for c in cats])
for c in cats:
    name=c.get('name')
    kws=c.get('keywords', [])
    if not kws:
        continue
    kw=kws[0]
    print('\nCategory:',name,'sample keyword:',kw)
    langs=[(c.get('hl','en'),c.get('gl','US'),c.get('ceid', f"{c.get('gl','US')}:{c.get('hl','en')}"))]
    if search_both:
        langs=[('en','US','US:en'),('tr','TR','TR:tr')]
    for (hl,gl,ceid) in langs:
        q = urllib.parse.quote(f"{kw} when:7d")
        url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"
        print(' Fetching',url)
        try:
            feed=feedparser.parse(url)
            print('  entries:', len(getattr(feed,'entries',[])))
        except Exception as e:
            print('  error',e)
