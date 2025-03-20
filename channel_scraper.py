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

def get_channels():
    """Ana sayfadan tüm kanal bağlantılarını alır."""
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        response = requests.get(BASE_URL, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info(f"HTML içeriği alındı: {len(response.text)} byte")
        
        # Tüm kanal linklerini bul
        all_links = soup.find_all('a', href=True)
        channel_links = []
        
        # Azerbaycan ve Türk kanallarını belirlemek için aranacak kelimeler
        tr_az_keywords = ['trt', 'a haber', 'atv', 'kanal d', 'show tv', 'star tv', 'fox', 'tv8', 
                       'ntv', 'cnn türk', 'haberturk', 'kanal 7', 'beyaz tv', 'tv 100',
                       'azerbaycan', 'azad', 'ictimai', 'idman', 'azərbaycan', 'aztv', 'cbc sport']
        
        for link in all_links:
            href = link.get('href')
            if not href:
                continue
                
            # Kanal linklerini filtrele
            if '/izle/' in href or '/canli/' in href:
                if not href.startswith('http'):
                    href = f"https://www.canlitv.me{href}" if href.startswith('/') else f"https://www.canlitv.me/{href}"
                
                # Kanal ismini al
                channel_name = href.split('/')[-1].replace('-', ' ').title()
                
                # Türk ve Azerbaycan kanallarını filtrele
                is_tr_az_channel = False
                for keyword in tr_az_keywords:
                    if keyword.lower() in channel_name.lower():
                        is_tr_az_channel = True
                        break
                
                # Doğrudan azeri ve türk kanal linkleri zaten eklenebilir
                if 'azeri' in href.lower() or 'turk' in href.lower() or is_tr_az_channel:
                    channel_links.append({'name': channel_name, 'url': href})
                    logger.info(f"Kanal bulundu: {channel_name} - {href}")
                    
        # Hiç kanal bulunamadıysa tüm linkleri kullan
        if not channel_links:
            logger.warning("Filtreleme sonrası kanal bulunamadı, tüm kanal linklerini kullanıyoruz.")
            for link in all_links:
                href = link.get('href')
                if href and ('/izle/' in href or '/canli/' in href):
                    if not href.startswith('http'):
                        href = f"https://www.canlitv.me{href}" if href.startswith('/') else f"https://www.canlitv.me/{href}"
                    channel_name = href.split('/')[-1].replace('-', ' ').title()
                    channel_links.append({'name': channel_name, 'url': href})
        
        logger.info(f"Toplam {len(channel_links)} kanal bulundu")
        return channel_links
    
    except Exception as e:
        logger.error(f"Kanal listesi alınırken hata oluştu: {e}")
        return []

def extract_m3u_url(channel_info):
    """Kanal sayfasından m3u URL'sini çıkarır."""
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': BASE_URL,
    }
    
    try:
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
        
        # Direkt olarak video kaynaklarını ara
        video_tags = soup.find_all('video')
        for video in video_tags:
            src = video.get('src')
            if src and ('.m3u' in src or '.m3u8' in src):
                logger.info(f"Video tag içinde M3U URL bulundu: {src}")
                return src
                
            # Video içindeki source etiketlerini kontrol et
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src')
                if src and ('.m3u' in src or '.m3u8' in src):
                    logger.info(f"Video source tag içinde M3U URL bulundu: {src}")
                    return src
        
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

def main():
    logger.info("Kanal çekme işlemi başlıyor...")
    
    # Hata ayıklama için sayfayı kaydet
    save_debug_html()
    
    # Kanalları al
    channels = get_channels()
    
    if not channels:
        logger.error("Hiç kanal bulunamadı!")
        return False
    
    # Her kanal için m3u URL'sini çıkar
    for i, channel in enumerate(channels):
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
        # Debugging için tüm kanalları listele
        for channel in channels:
            logger.info(f"Kanal: {channel['name']} - {channel['url']}")
        return False
    
    # M3U dosyasını oluştur
    create_m3u_file(valid_channels)
    
    # Metadata dosyasını oluştur
    create_metadata(channels, valid_count)
    
    logger.info("İşlem tamamlandı!")
    return True

if __name__ == "__main__":
    main() 