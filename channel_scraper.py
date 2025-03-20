#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime
import time
import logging
import urllib.parse

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sabit değerler
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
BASE_URL = "https://www.canlitv.vin/"
OUTPUT_FILE = "kanallar.m3u"
METADATA_FILE = "metadata.json"

def get_all_channel_urls():
    """Pagination ile tüm sayfaları gezerek tüm kanal URL'lerini toplar."""
    all_channel_urls = []
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
    }
    
    try:
        # Daha verimli yöntem: Kanal sayfasını kullan
        # Bu sayfa tüm kanal listesini içeriyor
        main_channel_page = BASE_URL + "trt1-canliyayin"
        
        logger.info(f"Ana kanal sayfası yükleniyor: {main_channel_page}")
        response = requests.get(main_channel_page, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Ana kanal sayfası yüklenirken hata: HTTP {response.status_code}")
            # Eski yönteme geri dön
            return use_fallback_method()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Debug: HTML içeriğini kaydet
        with open('kanal_sayfasi.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
            logger.info("Ana kanal sayfası HTML içeriği kaydedildi")
        
        # Sayfanın sol tarafında tüm kanalların listesi var
        # Tüm linkleri bul
        all_links = soup.find_all('a', href=True)
        logger.info(f"Sayfada toplam {len(all_links)} link bulundu")
        
        # Kanal linklerini ayıkla
        for link in all_links:
            href = link.get('href')
            
            # Link içerik kontrolü
            if not href:
                continue
                
            # Resimli kanal kartlarını kontrol et - Genellikle bunlar gerçek kanal linkleridir
            has_image = link.find('img')
            
            # Kanal URL'lerini kontrol et
            # 1. ya doğrudan canli-izle içermeli
            # 2. ya /izle/ içermeli
            # 3. ya -izle ile bitmeli
            # 4. ya açıkça belli olan kanal formatında olmalı
            if (('/canli-izle/' in href or 
                 '/izle/' in href or 
                 href.endswith('-izle') or 
                 href.endswith('-izle/')) or
                (has_image and not href.startswith('#') and not 'javascript:' in href and
                 not '/kategori/' in href and not '/etiket/' in href and not '/blog/' in href)):
                
                # URL'i normalleştir
                if not href.startswith('http'):
                    href = urllib.parse.urljoin(BASE_URL, href)
                
                all_channel_urls.append(href)
                logger.info(f"Kanal URL'si bulundu: {href}")
        
        # URL'leri benzersiz hale getir
        all_channel_urls = list(set(all_channel_urls))
        logger.info(f"Toplam {len(all_channel_urls)} benzersiz kanal URL'si bulundu")
        
        # Eğer hiç URL bulunamadıysa, alternatif metod kullanılacak
        if not all_channel_urls:
            logger.warning("Kanal sayfasından URL bulunamadı, alternatif metoda geçiliyor...")
            return use_fallback_method()
        
        return all_channel_urls
    
    except Exception as e:
        logger.error(f"Kanal URL'leri alınırken hata: {str(e)}")
        logger.warning("Alternatif metod kullanılacak")
        return use_fallback_method()

def use_fallback_method():
    """Alternatif URL çıkarma metodu - önceki değişiklikler başarısız olursa"""
    all_channel_urls = []
    
    try:
        logger.info("Alternatif kanal toplama metodu kullanılıyor...")
        
        # Bilinen kanalların listesi
        static_channels = [
            BASE_URL + "canli-izle/trt-1",
            BASE_URL + "canli-izle/show-tv",
            BASE_URL + "canli-izle/atv",
            BASE_URL + "canli-izle/fox-tv",
            BASE_URL + "canli-izle/star-tv",
            BASE_URL + "canli-izle/kanal-d",
            BASE_URL + "canli-izle/tv8",
            BASE_URL + "canli-izle/trt-haber",
            BASE_URL + "canli-izle/cnn-turk",
            BASE_URL + "canli-izle/haberturk",
            BASE_URL + "canli-izle/ntv",
            BASE_URL + "canli-izle/trt-spor",
            BASE_URL + "canli-izle/trt-belgesel",
            BASE_URL + "canli-izle/trt-muzik",
            BASE_URL + "canli-izle/trt-cocuk",
            BASE_URL + "canli-izle/trt-avaz",
            BASE_URL + "canli-izle/a-haber",
            BASE_URL + "canli-izle/a-spor",
            # Azerbaycan kanalları
            BASE_URL + "canli-izle/idman-tv",
            BASE_URL + "canli-izle/az-tv",
            BASE_URL + "canli-izle/xezer-tv",
            BASE_URL + "canli-izle/atv-azad",
            BASE_URL + "canli-izle/ictimai-tv",
            BASE_URL + "canli-izle/muz-tv",
            BASE_URL + "canli-izle/medeniyet-tv",
            BASE_URL + "canli-izle/space-tv",
            BASE_URL + "canli-izle/cbc-az-tv",
            BASE_URL + "canli-izle/real-tv",
            BASE_URL + "canli-izle/dunya-tv",
            BASE_URL + "canli-izle/arb-tv",
            BASE_URL + "canli-izle/arb-24-tv",
            BASE_URL + "canli-izle/sehiyye-tv",
            BASE_URL + "canli-izle/aznews-tv",
            BASE_URL + "canli-izle/gunaz-tv",
            BASE_URL + "canli-izle/baku-tv",
        ]
        
        # Kategori URL'leri
        category_urls = [
            BASE_URL + "kanallar/ulusal",
            BASE_URL + "kanallar/haber",
            BASE_URL + "kanallar/spor",
            BASE_URL + "kanallar/muzik",
            BASE_URL + "kanallar/cocuk",
            BASE_URL + "kanallar/dini",
            BASE_URL + "kanallar/belgesel",
            BASE_URL + "kanallar/yerel",
            BASE_URL + "kanallar/yabanci",
            BASE_URL + "kanallar/azerbaycan",
        ]
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        # Kategorilerden kanal URL'lerini topla
        for category_url in category_urls:
            try:
                logger.info(f"Kategori sayfası yükleniyor: {category_url}")
                response = requests.get(category_url, headers=headers, timeout=10)
                
                if response.status_code != 200:
                    logger.warning(f"Kategori sayfası yüklenemedi: {category_url}")
                    continue
                
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href')
                    if href and ('/izle/' in href or '/canli-' in href):
                        if not href.startswith('http'):
                            href = urllib.parse.urljoin(BASE_URL, href)
                        all_channel_urls.append(href)
                        logger.info(f"Kategori sayfasından kanal URL'si eklendi: {href}")
            
            except Exception as e:
                logger.error(f"Kategori sayfası işlenirken hata: {category_url} - {str(e)}")
        
        # Statik kanalları ekle
        all_channel_urls.extend(static_channels)
        
        # URL'leri benzersiz hale getir
        all_channel_urls = list(set(all_channel_urls))
        logger.info(f"Toplam {len(all_channel_urls)} benzersiz kanal URL'si bulundu")
        
        if not all_channel_urls:
            logger.warning("Hiç kanal URL'si bulunamadı, sadece statik liste kullanılacak")
            return static_channels
            
        return all_channel_urls
        
    except Exception as e:
        logger.error(f"Alternatif kanal toplama yöntemi hata: {str(e)}")
        # En azından statik listeyi döndür
        logger.warning("Statik kanal listesi kullanılıyor...")
        return static_channels

def get_channels():
    """Tüm kanal URL'lerinden kanal bilgilerini oluşturur."""
    try:
        # Tüm kanal URL'lerini al
        channel_urls = get_all_channel_urls()
        
        if not channel_urls:
            logger.error("Hiç kanal URL'si bulunamadı!")
            return []
        
        # URL'lerden kanal bilgilerini oluştur
        channels = []
        for url in channel_urls:
            # Kanal adını URL'den çıkar ve düzelt
            try:
                # URL'den kanal adını çıkar
                channel_name = url.split('/')[-1].replace('-', ' ').strip()
                
                # "canli" ve "izle" gibi gereksiz kelimeleri kaldır
                for word in ['canli', 'izle', 'live', 'watch', 'tv', 'online', 'hd']:
                    channel_name = channel_name.replace(word, '').strip()
                
                # Fazladan boşlukları temizle
                channel_name = ' '.join(channel_name.split())
                
                # Azerbaycan kanalları için özel işleme
                if 'azerbaycan' in url.lower() or 'azeri' in url.lower():
                    if 'azerbaycan' not in channel_name.lower() and 'azeri' not in channel_name.lower():
                        channel_name = f"{channel_name} (Azerbaycan)"
                
                # İlk harfleri büyük yap, ancak yaygın kısaltmalara dikkat et
                words = channel_name.split()
                capitalized_words = []
                
                for word in words:
                    # TRT, CNN, NTV gibi kısaltmalar büyük harfle yazılır
                    if len(word) <= 3 and word.lower() not in ['ve', 'ile', 'bir', 'the', 'and']:
                        capitalized_words.append(word.upper())
                    else:
                        capitalized_words.append(word.capitalize())
                
                channel_name = ' '.join(capitalized_words)
                
                # Kanal D, Show TV gibi özel formatları düzelt
                for special_name in ['Kanal D', 'Show TV', 'Fox TV', 'Star TV', 'TV 8', 'TRT 1', 'TRT 2']:
                    lower_name = channel_name.lower()
                    lower_special = special_name.lower()
                    if lower_special.replace(' ', '') in lower_name.replace(' ', ''):
                        channel_name = special_name
                        break
                
                # "TV" formatını normalize et
                channel_name = channel_name.replace('Tv', 'TV')
                
            except:
                # Hata durumunda basit isimlendirme kullan
                channel_name = url.split('/')[-1].replace('-', ' ').title()
            
            channels.append({
                'name': channel_name,
                'url': url,
                'm3u_url': None  # İlk aşamada boş, sonra doldurulacak
            })
        
        logger.info(f"Toplam {len(channels)} kanal bilgisi oluşturuldu")
        return channels
        
    except Exception as e:
        logger.error(f"Kanal bilgileri oluşturulurken hata: {str(e)}")
        return []

def extract_m3u_url(channel_info):
    """Channel için m3u veya m3u8 URL döndürür"""
    # Web sayfasından çekmeye çalış
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': BASE_URL,
        }
        
        logger.info(f"İşleniyor: {channel_info['name']} - {channel_info['url']}")
        
        try:
            response = requests.get(channel_info['url'], headers=headers, timeout=10)
            response.raise_for_status()
            html_content = response.text
        except Exception as e:
            logger.error(f"Sayfa alınırken hata: {channel_info['url']} - {str(e)}")
            return None
        
        # m3u/m3u8 URL'leri için regex pattern'leri - daha kapsamlı
        patterns = [
            r'source:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'file:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'src=[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'(https?://[^\'"\s]+\.m3u[8]?[^\'"\s]*)',
            r'hls:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'videoSrc\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'video\s*src\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'url:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'playlist:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'hlsUrl\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'streamURL\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'["\'](https?://[^\'"\s]+/playlist\.m3u[8]?)[\'"]',
            r'["\'](https?://[^\'"\s]+/manifest\.m3u[8]?)[\'"]',
            r'["\'](https?://[^\'"\s]+/live\.m3u[8]?)[\'"]',
            r'["\'](https?://[^\'"\s]+/index\.m3u[8]?)[\'"]',
            r'["\'](https?://[^\'"\s]+/master\.m3u[8]?)[\'"]',
            r'["\'](https?://[^\'"\s]+/stream\.m3u[8]?)[\'"]',
            r'source\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'data-source=[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'data-url=[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'data-stream=[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        ]
        
        # Bilinen özel kanalları kontrol et
        channel_name_lower = channel_info['name'].lower()
        
        # TRT kanalları için bilinen URL'leri kontrol et
        if 'trt' in channel_name_lower:
            if 'trt 1' in channel_name_lower or 'trt1' in channel_name_lower:
                logger.info(f"TRT 1 için bilinen URL kullanılıyor")
                return "https://tv-trt1.medya.trt.com.tr/master.m3u8"
            elif 'trt 2' in channel_name_lower or 'trt2' in channel_name_lower:
                logger.info(f"TRT 2 için bilinen URL kullanılıyor")
                return "https://tv-trt2.medya.trt.com.tr/master.m3u8"
            elif 'trt spor' in channel_name_lower:
                logger.info(f"TRT Spor için bilinen URL kullanılıyor")
                return "https://tv-trtspor1.medya.trt.com.tr/master.m3u8"
            elif 'trt haber' in channel_name_lower:
                logger.info(f"TRT Haber için bilinen URL kullanılıyor")
                return "https://tv-trthaber.medya.trt.com.tr/master.m3u8"
            elif 'trt belgesel' in channel_name_lower:
                logger.info(f"TRT Belgesel için bilinen URL kullanılıyor")
                return "https://tv-trtbelgesel.medya.trt.com.tr/master.m3u8"
            elif 'trt çocuk' in channel_name_lower:
                logger.info(f"TRT Çocuk için bilinen URL kullanılıyor")
                return "https://tv-trtcocuk.medya.trt.com.tr/master.m3u8"
            elif 'trt müzik' in channel_name_lower:
                logger.info(f"TRT Müzik için bilinen URL kullanılıyor")
                return "https://tv-trtmuzik.medya.trt.com.tr/master.m3u8"
            elif 'trt avaz' in channel_name_lower:
                logger.info(f"TRT Avaz için bilinen URL kullanılıyor")
                return "https://tv-trtavaz.medya.trt.com.tr/master.m3u8"
            elif 'trt kurd' in channel_name_lower:
                logger.info(f"TRT Kurdî için bilinen URL kullanılıyor")
                return "https://tv-trtkurdi.medya.trt.com.tr/master.m3u8"
        
        # Diğer bilinen kanallar
        elif 'kanal d' in channel_name_lower:
            logger.info(f"Kanal D için bilinen URL kullanılıyor")
            return "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3"
        elif 'tv8' in channel_name_lower.replace(' ', ''):
            logger.info(f"TV8 için bilinen URL kullanılıyor")
            return "https://tv8-live.daioncdn.net/tv8/tv8.m3u8"
        
        # Tüm pattern'leri dene
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                for match in matches:
                    # m3u ya da m3u8 uzantılı dosyaya denk gelmişsek kullan
                    if '.m3u' in match:
                        m3u_url = match
                        logger.info(f"M3U URL bulundu: {m3u_url}")
                        return m3u_url
        
        # İframe kontrol et
        soup = BeautifulSoup(html_content, 'html.parser')
        iframes = soup.find_all('iframe')
        
        for iframe in iframes:
            iframe_src = iframe.get('src')
            if not iframe_src:
                continue
                
            if not iframe_src.startswith('http'):
                iframe_src = f"https:{iframe_src}" if iframe_src.startswith('//') else f"https://{iframe_src}"
            
            try:
                iframe_response = requests.get(iframe_src, headers={
                    'User-Agent': USER_AGENT,
                    'Referer': channel_info['url']
                }, timeout=8)
                iframe_content = iframe_response.text
                
                for pattern in patterns:
                    matches = re.findall(pattern, iframe_content)
                    if matches:
                        for match in matches:
                            if '.m3u' in match:
                                m3u_url = match
                                logger.info(f"İframe içinde M3U URL bulundu: {m3u_url}")
                                return m3u_url
            except Exception as e:
                logger.warning(f"İframe içeriği alınırken hata: {e}")
        
        # Video etiketleri içinde src veya data-src attribute'larını kontrol et
        video_tags = soup.find_all('video')
        for video in video_tags:
            src = video.get('src') or video.get('data-src')
            if src and ('.m3u' in src or '.m3u8' in src):
                if not src.startswith('http'):
                    src = urllib.parse.urljoin(BASE_URL, src)
                logger.info(f"Video tag'i içinde M3U URL bulundu: {src}")
                return src
                
            # Video içindeki source etiketlerini kontrol et
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src') or source.get('data-src')
                if src and ('.m3u' in src or '.m3u8' in src):
                    if not src.startswith('http'):
                        src = urllib.parse.urljoin(BASE_URL, src)
                    logger.info(f"Source tag'i içinde M3U URL bulundu: {src}")
                    return src
        
        # M3U bulunamadı, null dön
        logger.warning(f"M3U URL bulunamadı: {channel_info['name']}")
        return None
        
    except Exception as e:
        logger.error(f"M3U URL çıkarılırken hata oluştu ({channel_info['url']}): {e}")
        return None

def create_m3u_file(channels):
    """Toplanan kanal bilgilerinden m3u dosyası oluşturur."""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            
            # Önce Türk, sonra Azerbaycan kanallarını sırala
            sorted_channels = sorted(channels, key=lambda c: determine_channel_priority(c))
            
            for channel in sorted_channels:
                if channel.get('m3u_url'):
                    # URL'lerde http yoksa ekleyelim
                    m3u_url = channel['m3u_url']
                    if not m3u_url.startswith('http'):
                        m3u_url = urllib.parse.urljoin(BASE_URL, m3u_url)
                    
                    f.write(f"#EXTINF:-1,{channel['name']}\n")
                    f.write(f"{m3u_url}\n")
            
        logger.info(f"M3U dosyası oluşturuldu: {OUTPUT_FILE}")
        return True
    except Exception as e:
        logger.error(f"M3U dosyası oluşturulurken hata: {e}")
        return False

def determine_channel_priority(channel):
    """Kanal sıralama önceliğini belirler. 
    Türk kanalları önce, Azerbaycan kanalları sonra, diğerleri en sonda."""
    name = channel['name'].lower()
    
    # Ulusal Türk kanalları önce
    national_turkish = ['trt 1', 'trt1', 'atv', 'show tv', 'showtv', 'star tv', 'startv', 'kanal d', 'kanald', 'fox tv', 'foxtv', 'tv8', 'tv 8']
    for prefix in national_turkish:
        if name.startswith(prefix) or name.replace(' ', '') == prefix.replace(' ', ''):
            return 0
            
    # TRT kanalları grubu
    if 'trt' in name:
        return 1
    
    # Haber kanalları grubu
    news_channels = ['haber', 'cnn', 'ntv', 'haberturk', 'haber türk', 'a haber', 'tgrt']
    for news in news_channels:
        if news in name:
            return 2
    
    # Spor kanalları grubu
    sports_channels = ['spor', 'sport', 'sports', 'futbol', 'gol', 'goal']
    for sport in sports_channels:
        if sport in name:
            return 3
    
    # Müzik kanalları grubu
    music_channels = ['müzik', 'muzik', 'music', 'number one', 'numberone', 'powertürk', 'powerturk', 'kral']
    for music in music_channels:
        if music in name:
            return 4
    
    # Diğer Türk kanalları
    if 'türk' in name or 'turk' in name:
        return 5
        
    # Azerbaycan kanalları
    if 'azerbaycan' in name or 'azeri' in name or 'aztv' in name or 'az tv' in name or '(azerbaycan)' in name:
        return 6
            
    # Diğer tüm kanallar
    return 7

def create_metadata(channels, valid_count):
    """Güncel metadata bilgisini JSON dosyasına yazar."""
    try:
        metadata = {
            'last_updated': datetime.now().isoformat(),
            'channel_count': len(channels),
            'valid_channels': valid_count,
            'channels': [{'name': c['name'], 'url': c['url']} for c in channels if c.get('m3u_url')]
        }
        
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Metadata dosyası oluşturuldu: {METADATA_FILE}")
        return True
    except Exception as e:
        logger.error(f"Metadata dosyası oluşturulurken hata: {e}")
        return False

def save_debug_html():
    """Hata ayıklama için web sayfasını kaydeder."""
    try:
        response = requests.get(BASE_URL, headers={'User-Agent': USER_AGENT})
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info("Hata ayıklama için HTML sayfası kaydedildi: debug_page.html")
    except Exception as e:
        logger.error(f"HTML sayfası kaydedilirken hata: {e}")

def check_m3u_urls(channels):
    """Listelenen m3u URL'lerinin geçerliliğini kontrol eder"""
    valid_channels = []
    invalid_channels = []
    
    logger.info(f"Toplam {len([c for c in channels if c.get('m3u_url')])} m3u URL'si kontrol edilecek")
    
    # İki denemede kontrol et - ilk denemede başarısız olanları ikinci denemede tekrar dene
    for attempt in range(2):
        channels_to_check = channels if attempt == 0 else invalid_channels
        invalid_channels = []
        
        for channel in channels_to_check:
            if not channel.get('m3u_url'):
                continue
                
            try:
                m3u_url = channel['m3u_url']
                if not m3u_url.startswith('http'):
                    m3u_url = urllib.parse.urljoin(BASE_URL, m3u_url)
                
                # HEAD isteği ile kontrol et
                try:
                    head_response = requests.head(m3u_url, timeout=8, allow_redirects=True)
                    
                    # Bazı sunucular HEAD isteklerini desteklemez, bu durumda GET kullanmayı dene
                    if head_response.status_code >= 400:
                        logger.info(f"HEAD isteği başarısız, GET deneniyor: {channel['name']}")
                        get_response = requests.get(m3u_url, timeout=8, stream=True)
                        
                        # İlk birkaç baytı oku ve bağlantıyı kapat
                        if get_response.status_code < 400:
                            for chunk in get_response.iter_content(chunk_size=1024):
                                if chunk:
                                    break
                            get_response.close()
                            
                            channel['m3u_url'] = m3u_url  # Tam URL'yi güncelle
                            valid_channels.append(channel)
                            logger.info(f"Geçerli M3U URL (GET): {channel['name']} - {m3u_url}")
                            continue
                    
                    # HEAD isteği başarılıysa
                    if head_response.status_code < 400:
                        channel['m3u_url'] = m3u_url  # Tam URL'yi güncelle
                        valid_channels.append(channel)
                        logger.info(f"Geçerli M3U URL (HEAD): {channel['name']} - {m3u_url}")
                    else:
                        invalid_channels.append(channel)
                        logger.warning(f"Geçersiz M3U URL (HTTP {head_response.status_code}): {channel['name']} - {m3u_url}")
                
                except Exception as e:
                    # Bağlantı hatası, ikinci denemede farklı yöntem kullanacağız
                    invalid_channels.append(channel)
                    logger.warning(f"M3U URL kontrolü hatası: {channel['name']} - {e}")
            
            except Exception as e:
                logger.error(f"Genel hata: {channel['name']} - {str(e)}")
                
        logger.info(f"Deneme {attempt+1} - Geçerli URL: {len(valid_channels)}, Geçersiz URL: {len(invalid_channels)}")
        
        # Bir sonraki tur için geçersizleri tekrar kontrol et
        if attempt == 0 and invalid_channels:
            logger.info(f"Geçersiz {len(invalid_channels)} URL ikinci kez kontrol edilecek")
            time.sleep(2)  # İkinci deneme öncesi bekle
    
    # Duplikasyonları temizle
    unique_valid_channels = []
    seen_urls = set()
    
    for channel in valid_channels:
        if channel['m3u_url'] not in seen_urls:
            seen_urls.add(channel['m3u_url'])
            unique_valid_channels.append(channel)
    
    logger.info(f"Geçerli benzersiz M3U URL sayısı: {len(unique_valid_channels)}/{len([c for c in channels if c.get('m3u_url')])}")
    return unique_valid_channels

def main():
    logger.info("Kanal çekme işlemi başlıyor...")
    
    # Hata ayıklama için sayfayı kaydet
    save_debug_html()
    
    # Tüm kanalları al
    channels = get_channels()
    
    if not channels:
        logger.error("Hiç kanal bulunamadı!")
        return False
    
    # Tüm kanalları işlemek için maksimum sayıyı artır
    max_channels = 1000  # İşlenecek maksimum kanal sayısını artırıyoruz
    channels_to_process = channels[:max_channels]
    logger.info(f"İşlenecek kanal sayısı: {len(channels_to_process)}/{len(channels)}")
    
    # Kanal listesini karıştır, popüler kanalları önceliklendirmeye çalışalım
    def prioritize_channels(channel):
        # TRT, ATV, gibi ana kanalları önceliklendir
        name = channel['name'].lower()
        for prefix in ['trt', 'atv', 'show', 'star', 'kanal d', 'fox', 'tv8']:
            if prefix in name:
                return 0
        return 1
        
    # Kanalları önceliklendir
    channels_to_process.sort(key=prioritize_channels)
    
    # Her kanal için m3u URL'sini çıkar
    for i, channel in enumerate(channels_to_process):
        if not channel.get('m3u_url'):  # Zaten m3u_url yoksa ekle
            channel['m3u_url'] = extract_m3u_url(channel)
        
        # Rate limiting - her 5 kanalda bir 2 saniye bekle
        if (i + 1) % 5 == 0:
            logger.info(f"İşlenen: {i+1}/{len(channels_to_process)} - Rate limiting: 2 saniye bekleniyor...")
            time.sleep(2)
    
    # İşlenen kanalları ana listeye ekle
    for i, channel in enumerate(channels_to_process):
        if i < len(channels):
            channels[i] = channel
    
    # Geçerli M3U URL'leri olan kanalları kontrol et
    valid_channels = check_m3u_urls([c for c in channels if c.get('m3u_url')])
    
    # M3U dosyasını oluştur
    create_m3u_file(valid_channels)
    
    # Metadata dosyasını oluştur
    create_metadata(channels, len(valid_channels))
    
    logger.info(f"İşlem tamamlandı! {len(valid_channels)} geçerli kanal m3u dosyasına eklendi.")
    return True

if __name__ == "__main__":
    main() 