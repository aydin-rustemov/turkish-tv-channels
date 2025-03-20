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
    """Site'deki tüm kanal URL'lerini toplar."""
    all_channel_urls = []
    
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
    }
    
    try:
        # Doğrudan bilinen URL formatlarını ekle
        known_channel_urls = [
            # Doğrudan URL örnekleri
            "https://www.canlitv.vin/now-tv-canli", 
            "https://www.canlitv.vin/showtvcanli", 
            "https://www.canlitv.vin/kanal-d-canli-yayin",
            "https://www.canlitv.vin/trt1-canli",
            "https://www.canlitv.vin/atv-canli",
            "https://www.canlitv.vin/fox-tv-canli",
            "https://www.canlitv.vin/star-tv-canli",
            "https://www.canlitv.vin/tv8-canli",
            "https://www.canlitv.vin/trt-haber-canli",
            "https://www.canlitv.vin/haberturk-canli",
            "https://www.canlitv.vin/cnn-turk-canli",
            "https://www.canlitv.vin/trt-spor-canli",
            "https://www.canlitv.vin/a-spor-canli",
            "https://www.canlitv.vin/aspor-canli",
            "https://www.canlitv.vin/trt-belgesel-canli",
            "https://www.canlitv.vin/trt-cocuk-canli",
            "https://www.canlitv.vin/kanal-7-canli",
            "https://www.canlitv.vin/tv8-5-canli",
            "https://www.canlitv.vin/trt-muzik-canli",
            "https://www.canlitv.vin/idman-tv-canli",
            "https://www.canlitv.vin/az-tv-canli",
            "https://www.canlitv.vin/xezer-tv-canli",
            "https://www.canlitv.vin/ictimai-tv-canli",
            "https://www.canlitv.vin/trt-avaz-canli",
            "https://www.canlitv.vin/trt-kurdi-canli"
        ]
        all_channel_urls.extend(known_channel_urls)
        logger.info(f"Bilinen kanal URL'leri eklendi: {len(known_channel_urls)}")
        
        # Ana sayfayı incele
        logger.info(f"Ana sayfa inceleniyor")
        response = requests.get(BASE_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Ana sayfa yüklenirken hata: HTTP {response.status_code}")
            return all_channel_urls if all_channel_urls else use_fallback_method()
        
        # HTML içeriğini kaydet
        with open('ana_sayfa.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
            logger.info("Ana sayfa HTML içeriği kaydedildi")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Sayfadaki bütün kanal linklerini bul 
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href')
            # Kanal linki olabilecek formatları kontrol et
            if href and (('canli' in href) or ('izle' in href) or ('yayin' in href)):
                # Çeşitli formatları deniyoruz
                if href.startswith('/'):
                    href = BASE_URL + href[1:]
                elif not href.startswith('http'):
                    href = urllib.parse.urljoin(BASE_URL, href)
                
                all_channel_urls.append(href)
                logger.info(f"Ana sayfadan kanal bulundu: {href}")
        
        # Yan menüdeki kanal listesini özel olarak kontrol et (kanal listesi sayfada yan tarafta listelenmiş)
        channel_list_elem = soup.select_one('div.kanallar-listesi') or soup.select_one('ul.kanallar') or soup.select_one('ul.menu')
        
        if channel_list_elem:
            channel_links = channel_list_elem.find_all('a', href=True)
            logger.info(f"Kanal listesinde {len(channel_links)} link bulundu")
            
            for link in channel_links:
                href = link.get('href')
                
                if href:
                    # Tam URL oluştur
                    if not href.startswith('http'):
                        href = urllib.parse.urljoin(BASE_URL, href)
                    
                    # Kanal URL'si mi kontrol et
                    if 'canli' in href.lower() or 'izle' in href.lower() or 'yayin' in href.lower():
                        all_channel_urls.append(href)
                        logger.info(f"Kanal menüsünden URL bulundu: {href}")
        
        # URL'leri benzersiz hale getir
        all_channel_urls = list(set(all_channel_urls))
        logger.info(f"Toplam {len(all_channel_urls)} benzersiz kanal URL'si bulundu")
        
        # Eğer hiç URL bulunamadıysa, alternatif metod kullanılacak
        if not all_channel_urls:
            logger.warning("Hiç kanal URL'si bulunamadı, alternatif metoda geçiliyor...")
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
    """Kanal sayfasından m3u/m3u8 URL'sini dinamik olarak çıkarır"""
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': BASE_URL,
        }
        
        logger.info(f"İşleniyor: {channel_info['name']} - {channel_info['url']}")
        
        try:
            response = requests.get(channel_info['url'], headers=headers, timeout=15)
            response.raise_for_status()
            html_content = response.text
            
            # Debug: Kanal HTML içeriğini kaydet
            debug_file = f"debug_channel_{channel_info['name'].replace(' ', '_')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                logger.info(f"Kanal HTML içeriği kaydedildi: {debug_file}")
                
        except Exception as e:
            logger.error(f"Sayfa alınırken hata: {channel_info['url']} - {str(e)}")
            return None
        
        # HTML içeriğini analiz et
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. kanallar.php iframe'ini bul - canlitv.vin'in özel formatı
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            iframe_src = iframe.get('src')
            if not iframe_src:
                continue
                
            # kanallar.php iframe'i önemli bir ipucu
            if 'kanallar.php' in iframe_src:
                logger.info(f"kanallar.php iframe bulundu: {iframe_src}")
                
                # kanallar.php parametrelerini çıkar
                kanal_param = None
                if '?' in iframe_src:
                    query_part = iframe_src.split('?')[1]
                    params = query_part.split('&')
                    for param in params:
                        if param.startswith('kanal='):
                            kanal_param = param.split('=')[1]
                            break
                
                if kanal_param:
                    logger.info(f"Kanal parametresi bulundu: {kanal_param}")
                    
                    # iframe URL'sini normalize et
                    iframe_url = iframe_src
                    if not iframe_url.startswith('http'):
                        if iframe_url.startswith('//'):
                            iframe_url = 'https:' + iframe_url
                        else:
                            iframe_url = urllib.parse.urljoin(BASE_URL, iframe_url)
                    
                    # iframe içeriğini getir
                    try:
                        iframe_headers = headers.copy()
                        iframe_headers['Referer'] = channel_info['url']
                        
                        iframe_response = requests.get(iframe_url, headers=iframe_headers, timeout=10)
                        iframe_content = iframe_response.text
                        
                        # iframe içeriğini debug için kaydet
                        iframe_debug_file = f"debug_iframe_{kanal_param}.html"
                        with open(iframe_debug_file, 'w', encoding='utf-8') as f:
                            f.write(iframe_content)
                            logger.info(f"iframe içeriği kaydedildi: {iframe_debug_file}")
                        
                        # iframe içinde m3u URL'lerini ara
                        iframe_soup = BeautifulSoup(iframe_content, 'html.parser')
                        
                        # Video elementleri kontrol et
                        video_tags = iframe_soup.find_all('video')
                        for video in video_tags:
                            # video src attribute
                            video_src = video.get('src')
                            if video_src and ('.m3u' in video_src or '.m3u8' in video_src):
                                if not video_src.startswith('http'):
                                    video_src = urllib.parse.urljoin(iframe_url, video_src)
                                logger.info(f"Video tag'i içinde m3u bulundu: {video_src}")
                                return video_src
                            
                            # source elementleri kontrol et
                            source_tags = video.find_all('source')
                            for source in source_tags:
                                source_src = source.get('src')
                                if source_src and ('.m3u' in source_src or '.m3u8' in source_src):
                                    if not source_src.startswith('http'):
                                        source_src = urllib.parse.urljoin(iframe_url, source_src)
                                    logger.info(f"Source tag'i içinde m3u bulundu: {source_src}")
                                    return source_src
                        
                        # Scriptlerde değişkenler ara
                        script_tags = iframe_soup.find_all('script')
                        for script in script_tags:
                            script_content = script.string
                            if script_content:
                                m3u_url = find_m3u_in_content(script_content)
                                if m3u_url:
                                    # URL'yi normalize et
                                    if not m3u_url.startswith('http'):
                                        if m3u_url.startswith('//'):
                                            m3u_url = 'https:' + m3u_url
                                        else:
                                            m3u_url = urllib.parse.urljoin(iframe_url, m3u_url)
                                    logger.info(f"iframe script içinde m3u bulundu: {m3u_url}")
                                    return m3u_url
                        
                        # iframe içeriğinde m3u URL'leri ara
                        m3u_url = find_m3u_in_content(iframe_content)
                        if m3u_url:
                            # URL'yi normalize et
                            if not m3u_url.startswith('http'):
                                if m3u_url.startswith('//'):
                                    m3u_url = 'https:' + m3u_url
                                else:
                                    m3u_url = urllib.parse.urljoin(iframe_url, m3u_url)
                            logger.info(f"iframe içeriğinde m3u bulundu: {m3u_url}")
                            return m3u_url
                    
                    except Exception as iframe_error:
                        logger.warning(f"iframe içeriği incelenirken hata: {iframe_error}")
            
            # İframe içeriği direk m3u formatındaysa
            elif iframe_src.endswith('.m3u') or iframe_src.endswith('.m3u8') or '.m3u8' in iframe_src:
                # URL'yi normalize et
                if not iframe_src.startswith('http'):
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    else:
                        iframe_src = urllib.parse.urljoin(channel_info['url'], iframe_src)
                logger.info(f"İframe src içinde doğrudan m3u URL'si bulundu: {iframe_src}")
                return iframe_src
            
            # Diğer tüm iframe'leri de kontrol edelim
            else:
                # iframe URL'sini normalize et
                full_iframe_src = iframe_src
                if not full_iframe_src.startswith('http'):
                    if full_iframe_src.startswith('//'):
                        full_iframe_src = 'https:' + full_iframe_src
                    else:
                        full_iframe_src = urllib.parse.urljoin(channel_info['url'], full_iframe_src)
                
                try:
                    # iframe içeriğini al
                    iframe_headers = headers.copy()
                    iframe_headers['Referer'] = channel_info['url']
                    
                    iframe_response = requests.get(full_iframe_src, headers=iframe_headers, timeout=10)
                    if iframe_response.status_code == 200:
                        iframe_content = iframe_response.text
                        
                        # iframe içinde m3u URL'leri ara
                        m3u_url = find_m3u_in_content(iframe_content)
                        if m3u_url:
                            # URL'yi normalize et
                            if not m3u_url.startswith('http'):
                                if m3u_url.startswith('//'):
                                    m3u_url = 'https:' + m3u_url
                                else:
                                    m3u_url = urllib.parse.urljoin(full_iframe_src, m3u_url)
                            logger.info(f"Normal iframe içinde m3u bulundu: {m3u_url}")
                            return m3u_url
                except Exception as normal_iframe_error:
                    logger.warning(f"Normal iframe işlenirken hata: {normal_iframe_error}")
        
        # 2. Video player elementlerini bul
        player_selectors = [
            '#video-player', '#player', '.video-player', '.player', '#tv-player', 
            '.tv-player', '#videoContainer', '.videoContainer', '#playerContainer', 
            '.playerContainer', '#livePlayer', '.livePlayer', '#video', '.video',
            '#player_div', '.player_div', '#playerElement', '.playerElement',
            '#jwplayer', '.jwplayer', '.flowplayer', '#flowplayer'
        ]
        
        for selector in player_selectors:
            player_element = soup.select_one(selector)
            if player_element:
                logger.info(f"Player elementi bulundu: {selector}")
                
                # Player içinde iframe var mı?
                player_iframe = player_element.find('iframe')
                if player_iframe and player_iframe.get('src'):
                    iframe_src = player_iframe.get('src')
                    # URL'yi normalize et
                    if not iframe_src.startswith('http'):
                        if iframe_src.startswith('//'):
                            iframe_src = 'https:' + iframe_src
                        else:
                            iframe_src = urllib.parse.urljoin(channel_info['url'], iframe_src)
                    
                    logger.info(f"Player içinde iframe bulundu: {iframe_src}")
                    
                    # m3u8 linki içeriyor mu kontrol et
                    if '.m3u' in iframe_src or '.m3u8' in iframe_src:
                        logger.info(f"Player iframe src içinde m3u linki bulundu: {iframe_src}")
                        return iframe_src
                    
                    # iframe içeriğini al
                    try:
                        iframe_headers = headers.copy()
                        iframe_headers['Referer'] = channel_info['url']
                        
                        iframe_response = requests.get(iframe_src, headers=iframe_headers, timeout=10)
                        if iframe_response.status_code == 200:
                            iframe_content = iframe_response.text
                            
                            # iframe içinde m3u URL'leri ara
                            m3u_url = find_m3u_in_content(iframe_content)
                            if m3u_url:
                                # URL'yi normalize et
                                if not m3u_url.startswith('http'):
                                    if m3u_url.startswith('//'):
                                        m3u_url = 'https:' + m3u_url
                                    else:
                                        m3u_url = urllib.parse.urljoin(iframe_src, m3u_url)
                                logger.info(f"Player iframe içinde m3u bulundu: {m3u_url}")
                                return m3u_url
                    except Exception as player_iframe_error:
                        logger.warning(f"Player iframe işlenirken hata: {player_iframe_error}")
                
                # Player içinde video veya source elementleri var mı?
                video_tag = player_element.find('video')
                if video_tag:
                    # Video src attribute
                    video_src = video_tag.get('src')
                    if video_src and ('.m3u' in video_src or '.m3u8' in video_src):
                        if not video_src.startswith('http'):
                            video_src = urllib.parse.urljoin(channel_info['url'], video_src)
                        logger.info(f"Player içindeki video tag'i içinde m3u bulundu: {video_src}")
                        return video_src
                    
                    # Source elementleri kontrol et
                    source_tags = video_tag.find_all('source')
                    for source in source_tags:
                        source_src = source.get('src')
                        if source_src and ('.m3u' in source_src or '.m3u8' in source_src):
                            if not source_src.startswith('http'):
                                source_src = urllib.parse.urljoin(channel_info['url'], source_src)
                            logger.info(f"Player içindeki source tag'i içinde m3u bulundu: {source_src}")
                            return source_src
                
                # Data attribute'ları kontrol et
                for data_attr in ['data-source', 'data-url', 'data-stream', 'data-hls', 'data-src']:
                    attr_value = player_element.get(data_attr)
                    if attr_value and ('.m3u' in attr_value or '.m3u8' in attr_value):
                        if not attr_value.startswith('http'):
                            attr_value = urllib.parse.urljoin(channel_info['url'], attr_value)
                        logger.info(f"Player data attribute içinde m3u bulundu: {attr_value}")
                        return attr_value
        
        # 3. Sayfa içindeki tüm video elementlerini kontrol et
        video_tags = soup.find_all('video')
        for video in video_tags:
            # Video src attribute
            video_src = video.get('src')
            if video_src and ('.m3u' in video_src or '.m3u8' in video_src):
                if not video_src.startswith('http'):
                    video_src = urllib.parse.urljoin(channel_info['url'], video_src)
                logger.info(f"Video tag'i içinde m3u bulundu: {video_src}")
                return video_src
            
            # Source elementleri kontrol et
            source_tags = video.find_all('source')
            for source in source_tags:
                source_src = source.get('src')
                if source_src and ('.m3u' in source_src or '.m3u8' in source_src):
                    if not source_src.startswith('http'):
                        source_src = urllib.parse.urljoin(channel_info['url'], source_src)
                    logger.info(f"Source tag'i içinde m3u bulundu: {source_src}")
                    return source_src
        
        # 4. Sayfa içindeki script elementlerini kontrol et
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_content = script.string
            if script_content:
                m3u_url = find_m3u_in_content(script_content)
                if m3u_url:
                    # URL'yi normalize et
                    if not m3u_url.startswith('http'):
                        if m3u_url.startswith('//'):
                            m3u_url = 'https:' + m3u_url
                        else:
                            m3u_url = urllib.parse.urljoin(channel_info['url'], m3u_url)
                    logger.info(f"Script içinde m3u bulundu: {m3u_url}")
                    return m3u_url
        
        # 5. Sayfa içinde m3u URL'leri ara
        m3u_url = find_m3u_in_content(html_content)
        if m3u_url:
            # URL'yi normalize et
            if not m3u_url.startswith('http'):
                if m3u_url.startswith('//'):
                    m3u_url = 'https:' + m3u_url
                else:
                    m3u_url = urllib.parse.urljoin(channel_info['url'], m3u_url)
            logger.info(f"Sayfa içeriğinde m3u bulundu: {m3u_url}")
            return m3u_url
        
        # 6. Son çare: yt-dlp veya selenium kullan
        try:
            yt_dlp_url = extract_with_ytdlp(channel_info['url'])
            if yt_dlp_url:
                logger.info(f"yt-dlp ile m3u bulundu: {yt_dlp_url}")
                return yt_dlp_url
        except Exception as yt_dlp_error:
            logger.warning(f"yt-dlp ile çıkarma hatası: {str(yt_dlp_error)}")
        
        try:
            selenium_url = extract_with_selenium(channel_info['url'])
            if selenium_url:
                logger.info(f"Selenium ile m3u bulundu: {selenium_url}")
                return selenium_url
        except Exception as selenium_error:
            logger.warning(f"Selenium ile çıkarma hatası: {str(selenium_error)}")
        
        # M3U bulunamadı
        logger.warning(f"M3U URL bulunamadı: {channel_info['name']}")
        return None
        
    except Exception as e:
        logger.error(f"M3U URL çıkarılırken genel hata: {str(e)}")
        return None

def extract_with_ytdlp(url):
    """yt-dlp kullanarak m3u8 linkini çıkarır"""
    try:
        # yt-dlp'nin kurulu olup olmadığını kontrol et
        try:
            import yt_dlp
        except ImportError:
            logger.warning("yt-dlp paketi bulunamadı, otomatik kurmayı deniyorum...")
            import subprocess
            import sys
            
            # pip kullanarak yt-dlp'yi yüklemeyi dene
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            import yt_dlp
            logger.info("yt-dlp paketi başarıyla kuruldu")
        
        logger.info(f"yt-dlp ile çıkarma deneniyor: {url}")
        
        # yt-dlp options
        ydl_opts = {
            'format': 'best',
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'skip_download': True,
            'external_downloader_args': ['--inet4-only'],
            'socket_timeout': 10,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get('url') and ('.m3u' in info.get('url') or '.m3u8' in info.get('url')):
                return info.get('url')
            elif info.get('formats'):
                for fmt in info.get('formats'):
                    if fmt.get('url') and ('.m3u' in fmt.get('url') or '.m3u8' in fmt.get('url')):
                        return fmt.get('url')
            
            # En iyi formatı seçerek dön
            if info.get('formats'):
                best_format = None
                for fmt in info.get('formats'):
                    # HLS veya DASH formatlarını tercih et
                    if fmt.get('protocol') in ['m3u8', 'm3u8_native', 'http_dash_segments']:
                        if not best_format or fmt.get('quality', 0) > best_format.get('quality', 0):
                            best_format = fmt
                
                if best_format and best_format.get('url'):
                    return best_format.get('url')
        
        logger.warning(f"yt-dlp ile URL bulunamadı: {url}")
        return None
        
    except Exception as e:
        logger.error(f"yt-dlp ile çıkarma hatası: {str(e)}")
        return None

def find_m3u_in_content(content):
    """HTML veya JavaScript içeriğinden m3u URL'lerini çıkarır"""
    if not content:
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
        r'stream_url[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
        r'streamUrl[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
        r'mediaUrl[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
        r'playURL[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
        r'hls_url[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
        r'hlsURL[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
        r'videoURL[\'"\s:=]+([^\'"\s]+\.m3u[8]?[^\'"\s]*)',
    ]
    
    # Tüm pattern'leri dene
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            for match in matches:
                # m3u ya da m3u8 uzantılı dosyaya denk gelmişsek kullan
                if '.m3u' in match:
                    m3u_url = match
                    logger.info(f"M3U URL bulundu: {m3u_url}")
                    return m3u_url
    
    return None

def extract_with_selenium(url):
    """Selenium ile JavaScript çalıştırarak m3u8 linkini çıkarır"""
    try:
        # Selenium'un kurulu olup olmadığını kontrol et
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            logger.warning("Selenium paketleri bulunamadı, otomatik kurmayı deniyorum...")
            import subprocess
            import sys
            
            # Pip ile gerekli paketleri yükle
            packages = ["selenium", "webdriver-manager"]
            for package in packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from webdriver_manager.chrome import ChromeDriverManager
            logger.info("Selenium paketleri başarıyla kuruldu")
        
        # WebDriver Manager ile Chrome Driver'ı otomatik kur
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            chromedriver_path = ChromeDriverManager().install()
        except Exception as e:
            logger.warning(f"Chrome Driver otomatik kurulumu hatası: {e}")
            # Sistem PATH'inde ChromeDriver'ı aramaya çalış
            chromedriver_path = "chromedriver"
        
        logger.info(f"Selenium ile çıkarma deneniyor: {url}")
        
        # Chrome Options ayarlamaları
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Başsız modda çalıştır
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument(f"user-agent={USER_AGENT}")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        # WebDriver'ı başlat
        try:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"Chrome Driver başlatma hatası: {e}")
            return None
        
        try:
            # Zaman aşımı ayarları
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(5)
            
            # Sayfayı yükle
            driver.get(url)
            logger.info(f"Sayfa yüklendi: {url}")
            
            # Sayfa yüklendikten sonra biraz bekle - JavaScript yüklensin
            time.sleep(5)
            
            # Network trafiğini analiz etmek için JavaScript çalıştır
            script = """
            var videoSources = [];
            
            // Video etiketlerindeki src'leri al
            var videoElements = document.querySelectorAll('video');
            for(var i=0; i<videoElements.length; i++) {
                var src = videoElements[i].src;
                if(src && (src.includes('.m3u') || src.includes('.m3u8'))) {
                    videoSources.push(src);
                }
                
                // Video içindeki source etiketlerini kontrol et
                var sources = videoElements[i].querySelectorAll('source');
                for(var j=0; j<sources.length; j++) {
                    src = sources[j].src;
                    if(src && (src.includes('.m3u') || src.includes('.m3u8'))) {
                        videoSources.push(src);
                    }
                }
            }
            
            // iframe'leri kontrol et
            var iframes = document.querySelectorAll('iframe');
            var iframeSrcs = [];
            for(var i=0; i<iframes.length; i++) {
                iframeSrcs.push(iframes[i].src);
            }
            
            // HLS.js veya video.js tanımlarını arat
            var hlsJsUrls = [];
            var scripts = document.querySelectorAll('script');
            for(var i=0; i<scripts.length; i++) {
                var scriptContent = scripts[i].innerText;
                if(scriptContent) {
                    // Yaygın HLS/DASH URL formatlarını kontrol et
                    var m3u8Regex = /(["'])(https?:\\/\\/[^"']+\\.m3u8[^"']*)(\\1)/g;
                    var match;
                    while((match = m3u8Regex.exec(scriptContent)) !== null) {
                        hlsJsUrls.push(match[2]);
                    }
                }
            }
            
            return {
                videoSources: videoSources,
                iframeSrcs: iframeSrcs,
                hlsJsUrls: hlsJsUrls
            };
            """
            
            result = driver.execute_script(script)
            
            # Sonuçları analiz et
            if result:
                # 1. Önce doğrudan video kaynaklarını kontrol et
                if result.get('videoSources') and len(result.get('videoSources')) > 0:
                    for src in result.get('videoSources'):
                        if '.m3u' in src:
                            logger.info(f"Video kaynağından m3u bulundu: {src}")
                            driver.quit()
                            return src
                
                # 2. HLS.js veya video.js URL'lerini kontrol et
                if result.get('hlsJsUrls') and len(result.get('hlsJsUrls')) > 0:
                    for src in result.get('hlsJsUrls'):
                        if '.m3u' in src:
                            logger.info(f"Script içeriğinden m3u bulundu: {src}")
                            driver.quit()
                            return src
                
                # 3. iframe'leri kontrol et
                if result.get('iframeSrcs') and len(result.get('iframeSrcs')) > 0:
                    logger.info(f"Toplam {len(result.get('iframeSrcs'))} iframe bulundu")
                    iframe_sources = result.get('iframeSrcs')
                    
                    for iframe_src in iframe_sources:
                        if iframe_src and iframe_src.strip():
                            try:
                                # iframe'e git
                                driver.get(iframe_src)
                                logger.info(f"iframe yüklendi: {iframe_src}")
                                time.sleep(3)  # iframe yüklensin
                                
                                # iframe içinde m3u8 ara
                                iframe_result = driver.execute_script(script)
                                
                                if iframe_result:
                                    # iframe içindeki video kaynaklarını kontrol et
                                    if iframe_result.get('videoSources') and len(iframe_result.get('videoSources')) > 0:
                                        for src in iframe_result.get('videoSources'):
                                            if '.m3u' in src:
                                                logger.info(f"iframe video kaynağından m3u bulundu: {src}")
                                                driver.quit()
                                                return src
                                    
                                    # iframe içindeki HLS.js URL'lerini kontrol et
                                    if iframe_result.get('hlsJsUrls') and len(iframe_result.get('hlsJsUrls')) > 0:
                                        for src in iframe_result.get('hlsJsUrls'):
                                            if '.m3u' in src:
                                                logger.info(f"iframe script içeriğinden m3u bulundu: {src}")
                                                driver.quit()
                                                return src
                            except Exception as iframe_error:
                                logger.warning(f"iframe işlenirken hata: {iframe_error}")
            
            # HAR dosyası oluştur ve içinden m3u8 URL'leri ara
            try:
                # Performance loglarını al
                logs = driver.execute_script("""
                    var performance = window.performance || window.mozPerformance || window.msPerformance || window.webkitPerformance || {};
                    var network = performance.getEntries() || [];
                    return network;
                """)
                
                # Network trafiğinde m3u8 URL'lerini ara
                if logs:
                    for entry in logs:
                        name = entry.get('name', '')
                        if name and ('.m3u8' in name or '.m3u' in name):
                            logger.info(f"Performance loglarından m3u bulundu: {name}")
                            driver.quit()
                            return name
            except Exception as perf_error:
                logger.warning(f"Performance logları alınırken hata: {perf_error}")
            
            # Hiçbir şey bulunamadı
            logger.warning(f"Selenium ile m3u URL bulunamadı: {url}")
            driver.quit()
            return None
            
        except Exception as browse_error:
            logger.error(f"Sayfa gezinme hatası: {browse_error}")
            driver.quit()
            return None
            
    except Exception as e:
        logger.error(f"Selenium ile çıkarma hatası: {str(e)}")
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

def save_all_channel_pages():
    """Her kanalın HTML içeriğini debug_channels klasörüne kaydeder"""
    try:
        # Debug klasörünü oluştur
        os.makedirs('debug_channels', exist_ok=True)
        logger.info("debug_channels klasörü oluşturuldu")
        
        # Bazı bilinen kanalların listesi
        channels_to_check = [
            "trt1-izle",
            "atv-izle", 
            "fox-tv-izle",
            "show-tv-izle",
            "kanal-d-izle",
            "star-tv-izle",
            "tv8-izle",
            "cnn-turk-izle",
            "ntv-izle",
            "haberturk-izle"
        ]
        
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3',
        }
        
        # Her kanalı kaydet
        for channel in channels_to_check:
            try:
                channel_url = f"{BASE_URL}{channel}"
                logger.info(f"Kanal sayfası indiriliyor: {channel}")
                
                response = requests.get(channel_url, headers=headers, timeout=15)
                if response.status_code == 200:
                    # Dosya adını oluştur
                    filename = f"debug_channels/{channel}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    logger.info(f"Kanal HTML içeriği kaydedildi: {filename}")
                    
                    # İframe varsa onun içeriğini de kaydet
                    soup = BeautifulSoup(response.text, 'html.parser')
                    iframes = soup.find_all('iframe')
                    
                    for i, iframe in enumerate(iframes):
                        src = iframe.get('src')
                        if src:
                            if not src.startswith('http'):
                                src = urllib.parse.urljoin(BASE_URL, src)
                            
                            try:
                                iframe_response = requests.get(src, headers=headers, timeout=10)
                                if iframe_response.status_code == 200:
                                    iframe_filename = f"debug_channels/{channel}_iframe_{i}.html"
                                    with open(iframe_filename, 'w', encoding='utf-8') as f:
                                        f.write(iframe_response.text)
                                    logger.info(f"İframe içeriği kaydedildi: {iframe_filename}")
                            except Exception as e:
                                logger.error(f"İframe içeriği alınamadı: {src} - {e}")
                else:
                    logger.error(f"Kanal sayfası yüklenemedi: HTTP {response.status_code}")
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Kanal sayfası işlenirken hata: {channel} - {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Kanal sayfalarını kaydetme hatası: {e}")
        return False

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
    # Manuel analiz için tüm kanal sayfalarını indir
    save_all_channel_pages()
    
    # Ana işlemi çalıştır
    main() 