#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime
import time
import logging

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sabit değerler
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
BASE_URL = "https://www.canlitv.me/hd1"
OUTPUT_FILE = "kanallar.m3u"
METADATA_FILE = "metadata.json"

# Bilinen m3u linkleri - bu liste periyodik olarak güncellenebilir
KNOWN_CHANNELS = [
    {"name": "TRT 1", "url": "https://www.canlitv.me/canli-izle/trt-1", "m3u_url": "https://tv-trt1.medya.trt.com.tr/master.m3u8"},
    {"name": "TRT 2", "url": "https://www.canlitv.me/canli-izle/trt-2", "m3u_url": "https://tv-trt2.medya.trt.com.tr/master.m3u8"},
    {"name": "TRT Spor", "url": "https://www.canlitv.me/canli-izle/trt-spor", "m3u_url": "https://tv-trtspor1.medya.trt.com.tr/master.m3u8"},
    {"name": "TRT Haber", "url": "https://www.canlitv.me/canli-izle/trt-haber", "m3u_url": "https://tv-trthaber.medya.trt.com.tr/master.m3u8"},
    {"name": "ATV", "url": "https://www.canlitv.me/canli-izle/atv", "m3u_url": "https://trkvz-live.ercdn.net/atvhd/atvhd.m3u8"},
    {"name": "Star TV", "url": "https://www.canlitv.me/canli-izle/star-tv", "m3u_url": "https://tv.ensonhaber.com/tv/tr/startv/index.m3u8"},
    {"name": "Show TV", "url": "https://www.canlitv.me/canli-izle/show-tv", "m3u_url": "https://tv.ensonhaber.com/tv/tr/showtv/index.m3u8"},
    {"name": "Kanal D", "url": "https://www.canlitv.me/canli-izle/kanal-d", "m3u_url": "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3"},
    {"name": "FOX TV", "url": "https://www.canlitv.me/canli-izle/fox-tv", "m3u_url": "https://foxtv.blutv.com/blutv_foxtv_live/live.m3u8"},
    {"name": "TV8", "url": "https://www.canlitv.me/canli-izle/tv8", "m3u_url": "https://tv8-live.daioncdn.net/tv8/tv8.m3u8"},
    {"name": "CNN Türk", "url": "https://www.canlitv.me/canli-izle/cnn-turk", "m3u_url": "https://live.duhnet.tv/S2/HLS_LIVE/cnnturknp/playlist.m3u8"},
    {"name": "Habertürk", "url": "https://www.canlitv.me/canli-izle/haberturk", "m3u_url": "https://tv.ensonhaber.com/tv/tr/haberturk/index.m3u8"},
    {"name": "A Haber", "url": "https://www.canlitv.me/canli-izle/a-haber", "m3u_url": "https://trkvz-live.ercdn.net/ahaberhd/ahaberhd.m3u8"},
    {"name": "NTV", "url": "https://www.canlitv.me/canli-izle/ntv", "m3u_url": "https://tv.ensonhaber.com/tv/tr/ntv/index.m3u8"},
    {"name": "TRT Belgesel", "url": "https://www.canlitv.me/canli-izle/trt-belgesel", "m3u_url": "https://tv-trtbelgesel.medya.trt.com.tr/master.m3u8"},
    {"name": "TRT Çocuk", "url": "https://www.canlitv.me/canli-izle/trt-cocuk", "m3u_url": "https://tv-trtcocuk.medya.trt.com.tr/master.m3u8"},
    {"name": "TRT Müzik", "url": "https://www.canlitv.me/canli-izle/trt-muzik", "m3u_url": "https://tv-trtmuzik.medya.trt.com.tr/master.m3u8"},
    {"name": "Kanal 7", "url": "https://www.canlitv.me/canli-izle/kanal-7", "m3u_url": "https://live.kanal7.com/live/kanal7LiveDesktop/index.m3u8"},
    {"name": "TGRT Haber", "url": "https://www.canlitv.me/canli-izle/tgrt-haber", "m3u_url": "https://tv.ensonhaber.com/tv/tr/tgrthaber/index.m3u8"},
    {"name": "A2", "url": "https://www.canlitv.me/canli-izle/a2", "m3u_url": "https://trkvz-live.ercdn.net/a2hd/a2hd.m3u8"},
    {"name": "TRT Avaz", "url": "https://www.canlitv.me/canli-izle/trt-avaz", "m3u_url": "https://tv-trtavaz.medya.trt.com.tr/master.m3u8"},
    {"name": "TRT Kurdî", "url": "https://www.canlitv.me/canli-izle/trt-kurdi", "m3u_url": "https://tv-trtkurdi.medya.trt.com.tr/master.m3u8"},
    {"name": "Beyaz TV", "url": "https://www.canlitv.me/canli-izle/beyaz-tv", "m3u_url": "https://tv.ensonhaber.com/tv/tr/beyaztv/index.m3u8"},
    # Azerbaycan kanalları
    {"name": "ATV Azerbaycan", "url": "https://www.canlitv.me/canli-izle/atv-azerbaycan", "m3u_url": "http://85.132.81.184:8080/atv/index.m3u8"},
    {"name": "İctimai TV", "url": "https://www.canlitv.me/canli-izle/ictimai-tv", "m3u_url": "https://insanhaqtv.livebox.co.in/manastvindia/livehls/channel3.m3u8"},
    {"name": "CBC Sport", "url": "https://www.canlitv.me/canli-izle/cbc-sport", "m3u_url": "https://59c7ea6bec1c6.streamlock.net/live/cbcsport.stream/playlist.m3u8"},
    {"name": "ARB TV", "url": "https://www.canlitv.me/canli-izle/arb-tv", "m3u_url": "http://85.132.81.184:8080/arb/live/index.m3u8"},
    {"name": "Space TV", "url": "https://www.canlitv.me/canli-izle/space-tv-azerbaycan", "m3u_url": "http://150.253.219.25:8888/live/Feed222/index.m3u8"}
]

def get_channels():
    """Ana sayfadan tüm kanal bağlantılarını alır."""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        response = requests.get(BASE_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info(f"HTML içeriği alındı: {len(response.text)} byte")
        
        # Sayfadan tüm linkleri al
        all_links = soup.find_all('a', href=True)
        
        # Debug için bazı bilgileri kaydet
        logger.info(f"Toplam link sayısı: {len(all_links)}")
        channel_candidates = [l['href'] for l in all_links if '/izle/' in l['href'] or '/canli/' in l['href']]
        logger.info(f"Potansiyel kanal linkleri: {len(channel_candidates)}")
        logger.info(f"Örnek linkler: {channel_candidates[:5] if channel_candidates else 'Yok'}")
        
        # Bilinen kanalları döndür
        logger.info(f"Bilinen {len(KNOWN_CHANNELS)} kanal kullanılıyor")
        return KNOWN_CHANNELS
        
    except Exception as e:
        logger.error(f"Kanal listesi alınırken hata oluştu: {e}")
        # Hata durumunda yine bilinen kanalları döndür
        return KNOWN_CHANNELS

def extract_m3u_url(channel_info):
    """Channel için m3u URL döndürür"""
    # Kanal zaten m3u_url içeriyorsa onu kullan
    if channel_info.get('m3u_url'):
        logger.info(f"Bilinen M3U URL kullanılıyor: {channel_info['name']}")
        return channel_info['m3u_url']
    
    # Aksi halde web sayfasından çekmeye çalış
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': BASE_URL,
        }
        
        logger.info(f"İşleniyor: {channel_info['name']} - {channel_info['url']}")
        response = requests.get(channel_info['url'], headers=headers)
        response.raise_for_status()
        html_content = response.text
        
        # m3u/m3u8 URL'leri için regex pattern'leri
        patterns = [
            r'source:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'file:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'src=[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'(https?://[^\'"\s]+\.m3u[8]?[^\'"\s]*)',
            r'hls:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        ]
        
        # Tüm pattern'leri dene
        for pattern in patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                # İlk eşleşmeyi kullan
                m3u_url = matches[0]
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
                })
                iframe_content = iframe_response.text
                
                for pattern in patterns:
                    matches = re.findall(pattern, iframe_content)
                    if matches:
                        m3u_url = matches[0]
                        logger.info(f"İframe içinde M3U URL bulundu: {m3u_url}")
                        return m3u_url
            except Exception as e:
                logger.warning(f"İframe içeriği alınırken hata: {e}")
        
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
            
            for channel in channels:
                if channel.get('m3u_url'):
                    f.write(f"#EXTINF:-1,{channel['name']}\n")
                    f.write(f"{channel['m3u_url']}\n")
            
        logger.info(f"M3U dosyası oluşturuldu: {OUTPUT_FILE}")
        return True
    except Exception as e:
        logger.error(f"M3U dosyası oluşturulurken hata: {e}")
        return False

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

def check_m3u_urls():
    """Listelenen m3u URL'lerinin geçerliliğini kontrol eder"""
    valid_channels = []
    invalid_channels = []
    
    for channel in KNOWN_CHANNELS:
        if not channel.get('m3u_url'):
            continue
            
        try:
            response = requests.head(channel['m3u_url'], timeout=5)
            if response.status_code < 400:
                valid_channels.append(channel)
                logger.info(f"Geçerli M3U URL: {channel['name']} - {channel['m3u_url']}")
            else:
                invalid_channels.append(channel)
                logger.warning(f"Geçersiz M3U URL (HTTP {response.status_code}): {channel['name']} - {channel['m3u_url']}")
        except Exception as e:
            invalid_channels.append(channel)
            logger.warning(f"M3U URL kontrolü hatası: {channel['name']} - {channel['m3u_url']} - {e}")
    
    logger.info(f"Geçerli M3U URL sayısı: {len(valid_channels)}/{len(KNOWN_CHANNELS)}")
    return valid_channels

def main():
    logger.info("Kanal çekme işlemi başlıyor...")
    
    # Hata ayıklama için sayfayı kaydet
    save_debug_html()
    
    # Önce bilinen kanalları kontrol et
    valid_known_channels = check_m3u_urls()
    
    if valid_known_channels:
        logger.info(f"{len(valid_known_channels)} geçerli kanal bulundu, web sitesinden ek kanal aranmayacak")
        # M3U dosyasını oluştur
        create_m3u_file(valid_known_channels)
        # Metadata dosyasını oluştur
        create_metadata(valid_known_channels, len(valid_known_channels))
        logger.info("İşlem tamamlandı!")
        return True
    
    # Geçerli bilinen kanal yoksa web sitesinden kanalları al
    channels = get_channels()
    
    if not channels:
        logger.error("Hiç kanal bulunamadı!")
        return False
    
    # Her kanal için m3u URL'sini çıkar
    for i, channel in enumerate(channels):
        if not channel.get('m3u_url'):  # Zaten m3u_url yoksa ekle
            channel['m3u_url'] = extract_m3u_url(channel)
        
        # Her 3 kanalda bir 2 saniye bekle (site koruması için)
        if (i + 1) % 3 == 0:
            logger.info(f"Rate limiting: 2 saniye bekleniyor...")
            time.sleep(2)
    
    # Geçerli m3u URL'si olan kanalları say
    valid_channels = [c for c in channels if c.get('m3u_url')]
    valid_count = len(valid_channels)
    
    logger.info(f"Toplam {len(channels)} kanal işlendi")
    logger.info(f"M3U URL'si bulunan kanal sayısı: {valid_count}")
    
    if valid_count == 0:
        logger.error("Hiç geçerli M3U URL'si bulunamadı!")
        return False
    
    # M3U dosyasını oluştur
    create_m3u_file(valid_channels)
    
    # Metadata dosyasını oluştur
    create_metadata(channels, valid_count)
    
    logger.info("İşlem tamamlandı!")
    return True

if __name__ == "__main__":
    main() 