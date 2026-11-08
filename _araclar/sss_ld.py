"""sss.html'deki görünen soru-cevaplardan FAQPage (JSON-LD) etiketini üretir ve sayfaya yazar.
SSS'ye soru eklenir/değişirse: python3 _araclar/sss_ld.py   (test, ikisinin uyumlu olduğunu kontrol eder)"""
import html, json, os, re, sys
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YOL = os.path.join(KOK, 'sss.html')
BAS, SON = '<!-- SSS-LD:BAS -->', '<!-- SSS-LD:SON -->'

def duz(s):
    s = re.sub(r'<br\s*/?>', ' ', s); s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()

def sorular(t):
    return [(duz(q), duz(a)) for q, a in re.findall(r'<span class="sss-q-text">(.*?)</span>.*?<div class="sss-a">(.*?)</div></div>', t, re.S)]

def ld(t):
    return {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in sorular(t)]}

if __name__ == '__main__':
    t = open(YOL, encoding='utf-8').read()
    blok = BAS + '\n<script type="application/ld+json">' + json.dumps(ld(t), ensure_ascii=False) + '</script>\n' + SON
    if BAS in t: t = re.sub(re.escape(BAS) + '.*?' + re.escape(SON), lambda m: blok, t, flags=re.S)
    else: t = t.replace('</head>', blok + '\n</head>', 1)
    open(YOL, 'w', encoding='utf-8').write(t)
    print(len(sorular(t)), 'soru yazıldı')
