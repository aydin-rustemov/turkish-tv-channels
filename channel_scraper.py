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
    """canlitv.vin sitesindeki tüm kanal URL'lerini toplar."""
    try:
        logger.info("Tüm kanal URL'leri toplanıyor...")
        
        # Bilinen kanal URL'leri (direkt çalışan örnekler)
        known_channel_urls = [
            "https://www.canlitv.vin/trt1-canliyayin",
            "https://www.canlitv.vin/trt2-canli-izle",
            "https://www.canlitv.vin/trt-haber",
            "https://www.canlitv.vin/kanal-d-canli-yayin",
            "https://www.canlitv.vin/star-tv-canli",
            "https://www.canlitv.vin/show-tv-hd-canli",
            "https://www.canlitv.vin/atv-canli-yayin-hd-izle",
            "https://www.canlitv.vin/fox-tv-canli-yayin",
            "https://www.canlitv.vin/tv8-hd-canli-yayin",
            "https://www.canlitv.vin/tv8-5-canli-izle",
            "https://www.canlitv.vin/kanal-7-hd-canli-yayin",
            # Haber kanalları - düzeltilmiş formatlar
            "https://www.canlitv.vin/cnn-turk-canli-yayin", # cnn-turk-izle -> cnn-turk-canli-yayin
            "https://www.canlitv.vin/ntv-canli-yayin",     # ntv-izle -> ntv-canli-yayin
            "https://www.canlitv.vin/haberturk-canli-yayin", # haberturk-izle -> haberturk-canli-yayin
            "https://www.canlitv.vin/tgrt-haber-canli-yayin",
            "https://www.canlitv.vin/tv100-canli-yayin",
            "https://www.canlitv.vin/haber-global-canli-yayin",
            # Müzik ve eğlence
            "https://www.canlitv.vin/trt-muzik-canli",
            "https://www.canlitv.vin/power-turk-tv-canli-hd-izle",
            "https://www.canlitv.vin/dream-turk-canli-yayin",
            "https://www.canlitv.vin/kral-tv-hd-canli-izle",
            "https://www.canlitv.vin/kral-pop-tv-canli-hd-izle",
            # Çocuk kanalları
            "https://www.canlitv.vin/trt-cocuk-canli",
            "https://www.canlitv.vin/minika-cocuk-canli-yayin",
            "https://www.canlitv.vin/minika-go-canli-yayin"
        ]
        
        # Bilinen URL'lerin formatlarını kullanarak daha fazla URL oluştur
        channel_urls = set(known_channel_urls)  # Tekrarları önlemek için set kullanıyoruz
        
        # Ana sayfadan kanal linklerini analiz et ve topla
        try:
            # Ana sayfa
            response = requests.get(BASE_URL, headers={"User-Agent": USER_AGENT}, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tüm linkleri bul
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                
                # Kanal linki olabilecek URL'leri filtrele
                # Kanal linkleri genelde -canli, -izle, -yayin gibi kelimeler içerir
                if (href.startswith('/') or href.startswith(BASE_URL)) and any(keyword in href.lower() for keyword in ['canli', 'izle', 'yayin']):
                    if href.startswith('/'):
                        full_url = BASE_URL + href
                    else:
                        full_url = href
                        
                    # URL'yi temizle ve normalize et
                    if not full_url.startswith('http'):
                        full_url = 'https://' + full_url.lstrip('/')
                        
                    channel_urls.add(full_url)
            
            logger.info(f"Ana sayfadan {len(channel_urls) - len(known_channel_urls)} yeni kanal URL'si bulundu")
            
            # Otomatik keşfedilen URL'leri düzelt
            corrected_urls = set()
            for url in channel_urls:
                # URL üzerinde düzeltmeler yap
                if "cnn-turk-izle" in url:
                    corrected_urls.add(url.replace("cnn-turk-izle", "cnn-turk-canli-yayin"))
                elif "ntv-izle" in url:
                    corrected_urls.add(url.replace("ntv-izle", "ntv-canli-yayin"))
                elif "haberturk-izle" in url:
                    corrected_urls.add(url.replace("haberturk-izle", "haberturk-canli-yayin"))
                else:
                    corrected_urls.add(url)
            
            channel_urls = corrected_urls
            
            # Kategori sayfalarını da tara
            category_paths = [
                "/tv-kanallari",
                "/haber-kanallari",
                "/spor-kanallari", 
                "/muzik-kanallari",
                "/sinema-kanallari",
                "/belgesel-kanallari",
                "/cocuk-kanallari",
                "/dini-kanallar",
                "/azerbaycan-kanallari"
            ]
            
            for category_path in category_paths:
                try:
                    category_url = BASE_URL + category_path
                    logger.info(f"Kategori sayfası taranıyor: {category_url}")
                    
                    response = requests.get(category_url, headers={"User-Agent": USER_AGENT}, timeout=15)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    category_links = soup.find_all('a', href=True)
                    for link in category_links:
                        href = link['href']
                        if (href.startswith('/') or href.startswith(BASE_URL)) and any(keyword in href.lower() for keyword in ['canli', 'izle', 'yayin']):
                            if href.startswith('/'):
                                full_url = BASE_URL + href
                            else:
                                full_url = href
                                
                            # URL'yi temizle ve normalize et
                            if not full_url.startswith('http'):
                                full_url = 'https://' + full_url.lstrip('/')
                                
                            channel_urls.add(full_url)
                            
                except Exception as category_error:
                    logger.warning(f"Kategori sayfası tarama hatası: {category_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"Ana sayfa tarama hatası: {e}")
            
        logger.info(f"Toplam {len(channel_urls)} kanal URL'si bulundu")
        return list(channel_urls)
        
    except Exception as e:
        logger.error(f"Kanal URL'leri toplanırken hata: {e}")
        return []

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
        
        # ÖZEL İŞLEME: canlitv.vin için geolive.php iframeler (yüksek öncelik)
        geolive_iframe = None
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            iframe_src = iframe.get('src', '')
            if 'geolive.php' in iframe_src and 'kanal=' in iframe_src:
                geolive_iframe = iframe_src
                logger.info(f"GeoLive iframe bulundu: {geolive_iframe}")
                break
        
        if geolive_iframe:
            geolive_m3u = process_geolive_iframe(geolive_iframe, channel_info['url'])
            if geolive_m3u:
                return geolive_m3u
        
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
                        nested_content = iframe_response.text
                        
                        # Debug için kaydet
                        nested_debug_file = f"debug_nested_iframe_{full_iframe_src.split('/')[-1].split('?')[0]}.html"
                        with open(nested_debug_file, 'w', encoding='utf-8') as f:
                            f.write(nested_content)
                        
                        # İçerikten m3u URL'sini ara
                        m3u_url = find_m3u_in_content(nested_content)
                        if m3u_url:
                            logger.info(f"Nested iframe içinden m3u URL bulundu: {m3u_url}")
                            return m3u_url
                except Exception as nested_error:
                    logger.warning(f"Nested iframe hatası: {nested_error}")
        
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

def process_geolive_iframe(iframe_url, referer_url):
    """canlitv.vin sitesinin geolive.php iframe'ini özel olarak işler"""
    try:
        logger.info(f"GeoLive iframe işleniyor: {iframe_url}")
        
        # URL'yi normalize et
        if not iframe_url.startswith('http'):
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            else:
                iframe_url = urllib.parse.urljoin(BASE_URL, iframe_url)
        
        # YENİ: Rekaptcha algılama ve atlatma
        logger.info("Anti-bot korumalarını atlatma denemesi yapılıyor...")
        
        # Geolive sayfasını önce Selenium ile deneyelim
        m3u_url = extract_geolive_with_selenium(iframe_url, referer_url)
        if m3u_url:
            logger.info(f"Selenium ile GeoLive'dan m3u URL başarıyla çıkarıldı: {m3u_url}")
            return m3u_url
        
        # Geolive sayfasını getir
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': referer_url,
            'Origin': BASE_URL,
            'Cookie': 'geolivevisit=1; watched=true; tvpage=active',  # CAPTCHA bypass için cookie eklendi
        }
        
        # Farklı User-Agent'lar ile dene
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0'
        ]
        
        response = None
        for ua in user_agents:
            try:
                headers['User-Agent'] = ua
                response = requests.get(iframe_url, headers=headers, timeout=15)
                
                if response.status_code == 200 and not ('captcha' in response.text.lower() or 'g-recaptcha' in response.text.lower()):
                    logger.info(f"Başarılı GeoLive erişimi (User-Agent: {ua[:20]}...)")
                    break
                else:
                    logger.warning(f"Bu User-Agent ile erişim başarısız: {ua[:20]}...")
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"HTTP isteği hatası: {str(e)}")
        
        if not response or response.status_code != 200:
            logger.warning(f"GeoLive iframe alınamadı: HTTP {response.status_code if response else 'None'}")
            return None
        
        # Debug için sayfayı kaydet
        debug_file = f"debug_geolive_{iframe_url.split('kanal=')[1].split('&')[0]}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
            logger.info(f"GeoLive iframe içeriği kaydedildi: {debug_file}")
        
        # İçerikten m3u bağlantısını ara
        iframe_content = response.text
        
        # Captcha kontrolü
        if 'captcha' in iframe_content.lower() or 'g-recaptcha' in iframe_content.lower():
            logger.warning("CAPTCHA algılandı. Selenium ile otomatik bypass denemesi yapılacak...")
            m3u_url = extract_geolive_with_selenium(iframe_url, referer_url)
            if m3u_url:
                return m3u_url
            
            # Kanal adını al
            channel_name = iframe_url.split('kanal=')[1].split('&')[0] if 'kanal=' in iframe_url else 'unknown'
            
            # Direk bilinen URL'leri dene
            logger.info(f"Bilinen M3U patternleri deneniyor: {channel_name}")
            known_patterns = [
                f"https://canlitv.center/stream/{channel_name}.m3u8",
                f"https://cdn.yayin.com.tr/tv/{channel_name}/playlist.m3u8",
                f"https://tv-{channel_name}.live.trt.com.tr/master.m3u8",
                f"https://stream.canlitv.com/{channel_name}/tracks-v1/index.m3u8",
                f"https://canlitv-pull.ercdn.net/{channel_name}/playlist.m3u8"
            ]
            
            for pattern in known_patterns:
                try:
                    head_response = requests.head(pattern, timeout=5)
                    if head_response.status_code < 400:
                        logger.info(f"Bilinen pattern çalışıyor: {pattern}")
                        return pattern
                except:
                    continue
            
            logger.warning(f"CAPTCHA nedeniyle işlem başarısız: {iframe_url}")
            return None
        
        # YENİ: JavaScript değişken tanımlarını analiz et
        # Genellikle gizlenmiş videoları ayıklamak için
        var_declarations = re.findall(r'var\s+([a-zA-Z0-9_$]+)\s*=\s*[\'"](.*?)[\'"];', iframe_content)
        var_dict = {k: v for k, v in var_declarations}
        
        # Değişkenleri birleştiren ifadeleri bul
        combined_vars = re.findall(r'([a-zA-Z0-9_$]+\s*\+\s*[a-zA-Z0-9_$]+(?:\s*\+\s*[a-zA-Z0-9_$]+)*)', iframe_content)
        
        # Değişken birleştirmeleri deneyip m3u ara
        for combined in combined_vars:
            try:
                parts = re.split(r'\s*\+\s*', combined)
                combined_value = ""
                for part in parts:
                    if part in var_dict:
                        combined_value += var_dict[part]
                
                if '.m3u' in combined_value:
                    logger.info(f"Değişken birleştirme ile m3u URL bulundu: {combined_value}")
                    return combined_value
            except Exception as var_error:
                logger.warning(f"Değişken birleştirme analiz hatası: {var_error}")
        
        # YENİ: kaynak etiketi içindeki gizli içerikleri analiz et
        source_with_vars = re.findall(r'source\s*:\s*([a-zA-Z0-9_$]+\s*\+\s*[a-zA-Z0-9_$]+(?:\s*\+\s*[a-zA-Z0-9_$]+)*)', iframe_content)
        for source_expr in source_with_vars:
            try:
                parts = re.split(r'\s*\+\s*', source_expr)
                combined_value = ""
                for part in parts:
                    part = part.strip()
                    if part in var_dict:
                        combined_value += var_dict[part]
                    elif part.startswith('"') or part.startswith("'"):
                        # Stringse tırnak işaretlerini kaldır
                        combined_value += part.strip('"\'')
                
                if '.m3u' in combined_value:
                    logger.info(f"Source değişken birleştirme ile m3u URL bulundu: {combined_value}")
                    return combined_value
            except Exception as source_error:
                logger.warning(f"Source değişken birleştirme analiz hatası: {source_error}")
        
        # YENİ: Obfuscated stringleri analiz et - HLS.js ve benzeri kütüphanelerde
        hls_patterns = [
            r'([a-zA-Z0-9_$]+)\.src\s*=\s*\{[^}]*?\bsrc\s*:\s*([a-zA-Z0-9_$]+\s*\+\s*[a-zA-Z0-9_$]+(?:\s*\+\s*[a-zA-Z0-9_$]+)*)',
            r'(?:Hls|hls)\.loadSource\(([a-zA-Z0-9_$]+\s*\+\s*[a-zA-Z0-9_$]+(?:\s*\+\s*[a-zA-Z0-9_$]+)*)\)',
            r'videojs\([^)]+\)\.src\(\{\s*src\s*:\s*([a-zA-Z0-9_$]+\s*\+\s*[a-zA-Z0-9_$]+(?:\s*\+\s*[a-zA-Z0-9_$]+)*)',
        ]
        
        for pattern in hls_patterns:
            matches = re.findall(pattern, iframe_content)
            for match in matches:
                try:
                    expr = match
                    if isinstance(match, tuple):
                        expr = match[1] if len(match) > 1 else match[0]
                        
                    parts = re.split(r'\s*\+\s*', expr)
                    combined_value = ""
                    for part in parts:
                        part = part.strip()
                        if part in var_dict:
                            combined_value += var_dict[part]
                        elif part.startswith('"') or part.startswith("'"):
                            combined_value += part.strip('"\'')
                    
                    if '.m3u' in combined_value:
                        logger.info(f"HLS pattern ile m3u URL bulundu: {combined_value}")
                        return combined_value
                except Exception as hls_error:
                    logger.warning(f"HLS pattern analiz hatası: {hls_error}")
        
        # YENİ: Özel canlitv.vin desen analizi
        m3u8_regex_pattern = r'function\s+getURL\(\)\s*{[^}]*\breturn\s+[\'"]([^\'"]*)[\'"]\s*\+\s*[\'"]([^\'"]*)[\'"]\s*;?\s*}'
        m3u8_matches = re.findall(m3u8_regex_pattern, iframe_content)
        if m3u8_matches:
            try:
                parts = m3u8_matches[0]
                if len(parts) >= 2:
                    combined_url = parts[0] + parts[1]
                    if '.m3u' in combined_url:
                        logger.info(f"getURL fonksiyonundan m3u URL bulundu: {combined_url}")
                        return combined_url
            except Exception as url_func_error:
                logger.warning(f"getURL fonksiyonu analiz hatası: {url_func_error}")
        
        # YENİ: JavaScript fonksiyonlarını bul
        js_functions = {}
        function_pattern = r'function\s+([a-zA-Z0-9_$]+)\s*\([^)]*\)\s*{([^}]*)}'
        func_matches = re.findall(function_pattern, iframe_content)
        
        for func_name, func_body in func_matches:
            js_functions[func_name] = func_body
            
            # Eğer fonksiyonda return ve m3u ifadesi varsa analiz et
            if 'return' in func_body and ('.m3u' in func_body or '.m3u8' in func_body):
                # Basit return ifadelerini bul
                return_pattern = r'return\s+[\'"]([^\'"]*\.m3u[^\'"]*)[\'"]'
                return_matches = re.findall(return_pattern, func_body)
                
                if return_matches:
                    logger.info(f"JavaScript fonksiyonundan m3u URL bulundu: {return_matches[0]}")
                    return return_matches[0]
                
                # String birleştirme return'leri
                return_concat_pattern = r'return\s+[\'"]([^\'"]*)[\'"](?:\s*\+\s*[\'"]([^\'"]*)[\'"])+\s*;'
                return_concat_matches = re.findall(return_concat_pattern, func_body)
                
                if return_concat_matches:
                    concat_strings = re.findall(r'[\'"]([^\'"]*)[\'"]', func_body[func_body.find('return'):])
                    combined = ''.join(concat_strings)
                    
                    if '.m3u' in combined:
                        logger.info(f"JavaScript fonksiyonu string birleştirmesiyle m3u URL bulundu: {combined}")
                        return combined
        
        # YENİ: JSON yapılandırma objelerini ara
        json_pattern = r'(?:var|const|let)\s+([a-zA-Z0-9_$]+)\s*=\s*({[^;]*?(?:src|source|file|url)\s*:\s*[\'"][^\'";]*?\.m3u[^\'"]*[\'"][^;]*})'
        json_matches = re.findall(json_pattern, iframe_content)
        
        for var_name, json_str in json_matches:
            try:
                # {} içindeki içeriği tam bir JSON'a çevir
                cleaned_json = '{' + re.sub(r'([{,])\s*([a-zA-Z0-9_$]+)\s*:', r'\1"\2":', json_str.strip('{} ')) + '}'
                
                # Tırnak işaretlerini normalleştir
                cleaned_json = re.sub(r':\s*\'([^\']*?)\'', r':"\1"', cleaned_json)
                
                # Temiz bir JSON mu kontrol et
                if cleaned_json.count('{') == cleaned_json.count('}'):
                    # m3u URL'sini bul
                    url_pattern = r'["\'](https?://[^"\']*\.m3u[8]?[^"\']*)["\']'
                    url_match = re.search(url_pattern, cleaned_json)
                    
                    if url_match:
                        logger.info(f"JSON yapılandırmasından m3u URL bulundu: {url_match.group(1)}")
                        return url_match.group(1)
            except Exception as json_error:
                logger.warning(f"JSON analiz hatası: {json_error}")
        
        # 1. Doğrudan embedDecode fonksiyonunu ara
        embed_decode_pattern = r'embedDecode\("([^"]+)"\)'
        embed_matches = re.findall(embed_decode_pattern, iframe_content)
        
        if embed_matches:
            encoded_content = embed_matches[0]
            try:
                # Base64 kodlu içeriği çöz
                import base64
                decoded_content = base64.b64decode(encoded_content).decode('utf-8')
                logger.info(f"Çözülen embedDecode içeriği: {decoded_content}")
                
                # Çözülen içerikten m3u URL'sini çıkar
                m3u_url = find_m3u_in_content(decoded_content)
                if m3u_url:
                    logger.info(f"embedDecode içinden m3u URL bulundu: {m3u_url}")
                    return m3u_url
            except Exception as decode_error:
                logger.warning(f"embedDecode çözme hatası: {decode_error}")
        
        # 2. Vidogevideo değişkenini ara
        vidogevideo_pattern = r'var vidogevideo\s*=\s*[\'"]([^\'"]*)[\'"]'
        vidogevideo_matches = re.findall(vidogevideo_pattern, iframe_content)
        
        if vidogevideo_matches:
            video_url = vidogevideo_matches[0]
            if '.m3u' in video_url:
                logger.info(f"vidogevideo değişkeninden m3u URL bulundu: {video_url}")
                return video_url
        
        # 3. Diğer Player URL'lerini ara (script içinde)
        player_url_patterns = [
            r'player\.src\(\{\s*src:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'player\.src\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'file:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'source:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'src=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
            r'source\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        ]
        
        for pattern in player_url_patterns:
            matches = re.findall(pattern, iframe_content)
            if matches:
                for match in matches:
                    if '.m3u' in match:
                        logger.info(f"Player URL patterninden m3u URL bulundu: {match}")
                        return match
        
        # 4. JSON içindeki URL'leri ara
        json_url_pattern = r'[{,]\s*["\'](?:file|src|source|url|stream|hlsUrl)["\']:\s*["\']([^"\']*\.m3u[^"\']*)["\']'
        json_matches = re.findall(json_url_pattern, iframe_content)
        
        if json_matches:
            for match in json_matches:
                if '.m3u' in match:
                    logger.info(f"JSON içinden m3u URL bulundu: {match}")
                    return match
        
        # 5. Sayfayı daha derin analiz et ve iframe'leri kontrol et
        soup = BeautifulSoup(iframe_content, 'html.parser')
        
        # Nested iframe'leri kontrol et
        nested_iframes = soup.find_all('iframe')
        for nested_iframe in nested_iframes:
            nested_src = nested_iframe.get('src')
            if nested_src and nested_src != 'about:blank':
                logger.info(f"GeoLive içinde nested iframe bulundu: {nested_src}")
                
                # Normalize URL
                if not nested_src.startswith('http'):
                    if nested_src.startswith('//'):
                        nested_src = 'https:' + nested_src
                    else:
                        nested_src = urllib.parse.urljoin(iframe_url, nested_src)
                
                try:
                    nested_headers = headers.copy()
                    nested_headers['Referer'] = iframe_url
                    
                    nested_response = requests.get(nested_src, headers=nested_headers, timeout=10)
                    if nested_response.status_code == 200:
                        nested_content = nested_response.text
                        
                        # Debug için kaydet
                        nested_debug_file = f"debug_nested_iframe_{nested_src.split('/')[-1].split('?')[0]}.html"
                        with open(nested_debug_file, 'w', encoding='utf-8') as f:
                            f.write(nested_content)
                        
                        # İçerikten m3u URL'sini ara
                        m3u_url = find_m3u_in_content(nested_content)
                        if m3u_url:
                            logger.info(f"Nested iframe içinden m3u URL bulundu: {m3u_url}")
                            return m3u_url
                except Exception as nested_error:
                    logger.warning(f"Nested iframe hatası: {nested_error}")
        
        # 6. Sayfa içindeki tüm videoları kontrol et
        video_tags = soup.find_all('video')
        for video in video_tags:
            video_src = video.get('src')
            if video_src and ('.m3u' in video_src or '.m3u8' in video_src):
                logger.info(f"Video tag'inden m3u URL bulundu: {video_src}")
                return video_src
            
            # Video source'larını kontrol et
            sources = video.find_all('source')
            for source in sources:
                source_src = source.get('src')
                if source_src and ('.m3u' in source_src or '.m3u8' in source_src):
                    logger.info(f"Video source tag'inden m3u URL bulundu: {source_src}")
                    return source_src
        
        # 7. Script taglerindeki evalatob kodunu çözmeyi dene
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_content = script.string
            if script_content and 'atob(' in script_content:
                try:
                    # Atob fonksiyonlarını bul
                    atob_pattern = r'atob\([\'"]([^\'"]+)[\'"]\)'
                    atob_matches = re.findall(atob_pattern, script_content)
                    
                    for encoded in atob_matches:
                        try:
                            import base64
                            decoded = base64.b64decode(encoded).decode('utf-8')
                            logger.info(f"Atob çözüldü: {decoded}")
                            
                            # Çözülen içerikten m3u URL'sini ara
                            m3u_url = find_m3u_in_content(decoded)
                            if m3u_url:
                                logger.info(f"Atob çözümünden m3u URL bulundu: {m3u_url}")
                                return m3u_url
                        except Exception as decode_error:
                            logger.warning(f"Atob çözme hatası: {decode_error}")
                except Exception as script_error:
                    logger.warning(f"Script çözme hatası: {script_error}")
        
        # 8. Son çare: tüm içerikte m3u ara
        m3u_url = find_m3u_in_content(iframe_content)
        if m3u_url:
            logger.info(f"Genel içerik taramasından m3u URL bulundu: {m3u_url}")
            return m3u_url
        
        # 9. YENİ: URL parçalarını birleştirerek arama
        url_part_pattern = r'/([^/]*\.m3u[^/\'"]*)'
        url_parts = re.findall(url_part_pattern, iframe_content)
        
        if url_parts:
            for part in url_parts:
                # Olası sunucu domainlerini kontrol et
                possible_domains = [
                    'https://cdn.canlitv.vin',
                    'https://stream.canlitv.vin',
                    'https://live.canlitv.vin',
                    'https://player.canlitv.vin',
                    'https://tv.canlitv.vin',
                    'https://media.canlitv.vin',
                    'https://cdn.canlitv.com',
                    'https://stream.canlitv.com'
                ]
                
                for domain in possible_domains:
                    potential_url = f"{domain}/{part}"
                    logger.info(f"Parçalardan oluşturulan potansiyel m3u URL: {potential_url}")
                    
                    # Bu URL'yi kontrol et (başlık kontrolü yeterli)
                    try:
                        head_response = requests.head(potential_url, timeout=5)
                        if head_response.status_code < 400:
                            logger.info(f"Geçerli parçalanmış m3u URL bulundu: {potential_url}")
                            return potential_url
                    except:
                        continue
        
        logger.warning(f"GeoLive iframe'inde m3u URL bulunamadı")
        return None
        
    except Exception as e:
        logger.error(f"GeoLive iframe işleme hatası: {str(e)}")
        return None

def extract_geolive_with_selenium(iframe_url, referer_url):
    """Selenium ve Chrome Stealth ile GeoLive iframe'den m3u URL çıkarma"""
    try:
        logger.info(f"Selenium ile GeoLive iframe işleniyor: {iframe_url}")
        
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
            packages = ["selenium", "webdriver-manager", "selenium-stealth"]
            for package in packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package], 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            logger.info("Selenium paketleri başarıyla kuruldu")
            
            try:
                import selenium_stealth
            except ImportError:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium-stealth"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                import selenium_stealth
                logger.info("Selenium Stealth başarıyla kuruldu")
        
        # WebDriver Manager ile Chrome Driver'ı otomatik kur
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            chromedriver_path = ChromeDriverManager().install()
        except Exception as e:
            logger.warning(f"Chrome Driver otomatik kurulumu hatası: {e}")
            # Sistem PATH'inde ChromeDriver'ı aramaya çalış
            chromedriver_path = "chromedriver"
        
        # Chrome Options ayarlamaları - CI/CD ortamları için özel ayarlar
        chrome_options = Options()
        
        # Github Actions ve CI ortamları için gerekli ayarlar
        chrome_options.add_argument("--headless=new")  # Yeni headless modu kullan
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Stealth mode tespiti zorlaştıracak ayarlar
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Farklı bir user-data-dir belirt (Github Actions için kritik)
        import tempfile
        import os
        import random
        import string
        
        # Rastgele bir kullanıcı profili oluştur
        random_dir = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
        temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{random_dir}")
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        
        # Diğer ayarlar
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument(f"--user-agent={USER_AGENT}")
        chrome_options.add_argument(f"--referer={referer_url}")
        
        # CI/CD ortamlar için ek ayarlar
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-infobars")
        
        # WebDriver'ı başlat
        driver = None
        try:
            service = Service(chromedriver_path)
            logger.info("Chrome Driver başlatılıyor...")
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome Driver başarıyla başlatıldı")
            
            # Selenium Stealth uygulaması - otomatik tarayıcı tespitini zorlaştırır
            try:
                import selenium_stealth
                selenium_stealth.stealth(driver,
                    languages=["tr-TR", "tr", "en-US", "en"],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                )
                logger.info("Selenium Stealth modu aktif edildi")
            except Exception as e:
                logger.warning(f"Selenium Stealth uygulanamadı: {e}")
                
        except Exception as e:
            logger.error(f"Chrome Driver başlatma hatası: {e}")
            
            # Alternatif yöntem: Farklı ayarlarla yeniden dene
            try:
                logger.info("Alternatif ayarlarla Chrome Driver başlatma deneniyor...")
                chrome_options = Options()
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                
                # Rastgele bir başka user-data-dir dene
                random_dir = ''.join(random.choice(string.ascii_lowercase) for i in range(10))
                temp_dir = os.path.join(tempfile.gettempdir(), f"chrome_profile_{random_dir}")
                chrome_options.add_argument(f"--user-data-dir={temp_dir}")
                
                driver = webdriver.Chrome(options=chrome_options)
                logger.info("Chrome Driver alternatif ayarlarla başlatıldı")
            except Exception as alt_error:
                logger.error(f"Alternatif Chrome Driver başlatma hatası: {alt_error}")
                
                # Doğrudan kanal URL'inden m3u adresi çıkarmaya çalış
                logger.warning("Selenium başlatılamadı. Direk URL desenleri deneniyor...")
                try:
                    # Kanal adını al ve bilinen URL desenlerini dene
                    channel_name = iframe_url.split('kanal=')[1].split('&')[0] if 'kanal=' in iframe_url else None
                    if channel_name:
                        logger.info(f"Bilinen M3U patternleri deneniyor: {channel_name}")
                        known_patterns = [
                            f"https://canlitv.center/stream/{channel_name}.m3u8",
                            f"https://cdn.yayin.com.tr/tv/{channel_name}/playlist.m3u8",
                            f"https://tv-{channel_name}.live.trt.com.tr/master.m3u8",
                            f"https://stream.canlitv.com/{channel_name}/tracks-v1/index.m3u8",
                            f"https://canlitv-pull.ercdn.net/{channel_name}/playlist.m3u8",
                            # Bayrak TV gibi özel kanallar için pattern
                            f"https://stream.tvcdn.biz/{channel_name}/tracks-v1/index.m3u8",
                            f"https://live.artidijitalmedya.com/{channel_name}/index.m3u8",
                            # TRT kanalları için özel patternler
                            f"https://tv-{channel_name.replace('-canli-yayin', '')}.medya.trt.com.tr/master.m3u8",
                            # Özel TV kanalları için patternler
                            f"https://{channel_name.split('-')[0]}.blutv.com/blutv_{channel_name.split('-')[0]}/live.m3u8",
                        ]
                        
                        # Eurostar ve diğer tematik kanallar için özel patternler
                        if "eurostar" in channel_name:
                            eurostar_patterns = [
                                "https://stream.eurostar.com.tr/eurostar/smil:eurostar.smil/playlist.m3u8",
                                "https://mn-nl.mncdn.com/eurostar/eurostar/chunklist.m3u8",
                                "https://xrklj56s.rocketcdn.com/eurostar.stream_720p/chunklist.m3u8",
                                "https://streaming.eurostar.com.tr/eurostar/eurostar/playlist.m3u8",
                                # Bilinen diğer CDN'ler için
                                "https://cdn-eurostar.yayin.com.tr/eurostar/eurostar/playlist.m3u8",
                                "https://live.duhnet.tv/S2/HLS_LIVE/eurostar/playlist.m3u8"
                            ]
                            known_patterns.extend(eurostar_patterns)
                            logger.info(f"Eurostar için {len(eurostar_patterns)} özel pattern eklendi")
                        
                        # Sinema kanalları için özel patternler
                        elif "sinema" in channel_name:
                            sinema_patterns = [
                                f"https://sinema-{channel_name.split('-')[-1]}.blutv.com/live/playlist.m3u8",
                                f"https://cdn-sinema.yayin.com.tr/{channel_name}/playlist.m3u8"
                            ]
                            known_patterns.extend(sinema_patterns)
                        
                        # Spor kanalları için özel patternler
                        elif "spor" in channel_name or "sport" in channel_name:
                            sport_patterns = [
                                f"https://live.sportstv.com.tr/{channel_name}/playlist.m3u8",
                                f"https://spor.blutv.com/{channel_name}/live.m3u8"
                            ]
                            known_patterns.extend(sport_patterns)
                        
                        # Belgesel kanalları için özel patternler
                        elif "belgesel" in channel_name or "discovery" in channel_name or "national" in channel_name:
                            documentary_patterns = [
                                f"https://d-{channel_name}.blutv.com/live/playlist.m3u8",
                                f"https://belgesel.duhnet.tv/{channel_name}/playlist.m3u8"
                            ]
                            known_patterns.extend(documentary_patterns)
                        
                        # Çocuk kanalları için özel patternler
                        elif "cocuk" in channel_name or "kids" in channel_name or "cartoon" in channel_name:
                            kids_patterns = [
                                f"https://cdn-cocuk.yayin.com.tr/{channel_name}/playlist.m3u8",
                                f"https://kids.blutv.com/{channel_name}/playlist.m3u8"
                            ]
                            known_patterns.extend(kids_patterns)
                        
                        for pattern in known_patterns:
                            try:
                                head_response = requests.head(pattern, timeout=5)
                                if head_response.status_code < 400:
                                    logger.info(f"Bilinen pattern çalışıyor: {pattern}")
                                    return pattern
                            except:
                                continue
                except Exception as pattern_error:
                    logger.error(f"URL pattern denemesi hatası: {pattern_error}")
                
                return None
        
        if not driver:
            logger.error("Driver oluşturulamadı")
            return None
        
        try:
            # Zaman aşımı ayarları
            driver.set_page_load_timeout(30)
            
            # Önce cookieleri ayarla
            try:
                logger.info("Cookies ayarlanıyor...")
                driver.get(BASE_URL)
                driver.add_cookie({"name": "geolivevisit", "value": "1"})
                driver.add_cookie({"name": "watched", "value": "true"})
                driver.add_cookie({"name": "tvpage", "value": "active"})
                logger.info("Cookies başarıyla ayarlandı")
            except Exception as cookie_error:
                logger.warning(f"Cookie ayarlama hatası: {cookie_error}")
            
            # Sayfayı yükle
            logger.info(f"GeoLive iframe yükleniyor: {iframe_url}")
            driver.get(iframe_url)
            
            # Sayfanın yüklenmesini bekle
            logger.info("Sayfa yüklenmesi bekleniyor...")
            time.sleep(5)  # Sayfanın tamamen yüklenmesi için biraz bekle
            
            # Debug için ekran görüntüsü al
            try:
                screenshot_path = f"debug_geolive_screenshot_{iframe_url.split('kanal=')[1].split('&')[0] if 'kanal=' in iframe_url else 'unknown'}.png"
                driver.save_screenshot(screenshot_path)
                logger.info(f"Ekran görüntüsü alındı: {screenshot_path}")
            except Exception as ss_error:
                logger.warning(f"Ekran görüntüsü alma hatası: {ss_error}")
            
            # CAPTCHA kontrolü
            if "captcha" in driver.page_source.lower() or "g-recaptcha" in driver.page_source.lower():
                logger.warning("Selenium'da CAPTCHA algılandı")
                # CI/CD ortamında CAPTCHA çözümü beklemek anlamsız, atlayalım
                logger.warning("CI/CD ortamında CAPTCHA çözümü atlanıyor")
            
            # Sayfa kaynak kodunu al ve m3u URL'lerini bul
            page_source = driver.page_source
            
            # Debug amaçlı kaydet
            debug_file = f"selenium_geolive_{iframe_url.split('kanal=')[1].split('&')[0] if 'kanal=' in iframe_url else 'unknown'}.html"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                logger.info(f"Selenium sayfa kaynağı kaydedildi: {debug_file}")
            except Exception as save_error:
                logger.warning(f"Sayfa kaynağı kaydetme hatası: {save_error}")
            
            # İçerikteki m3u URL'lerini bul
            m3u_url = find_m3u_in_content(page_source)
            if m3u_url:
                logger.info(f"Selenium ile GeoLive sayfasında m3u URL bulundu: {m3u_url}")
                driver.quit()
                return m3u_url
            
            # JavaScript ile veri topla
            try:
                # JavaScript çalıştırarak daha derin analiz yap
                logger.info("JavaScript analizi yapılıyor...")
                js_result = driver.execute_script("""
                function extractM3uUrls() {
                    var results = [];
                    
                    // 1. Video elementlerini kontrol et
                    var videos = document.querySelectorAll('video');
                    for (var i = 0; i < videos.length; i++) {
                        if (videos[i].src && videos[i].src.includes('.m3u')) {
                            results.push({type: 'video.src', url: videos[i].src});
                        }
                        
                        var sources = videos[i].querySelectorAll('source');
                        for (var j = 0; j < sources.length; j++) {
                            if (sources[j].src && sources[j].src.includes('.m3u')) {
                                results.push({type: 'source.src', url: sources[j].src});
                            }
                        }
                    }
                    
                    // 2. JavaScript değişkenleri ara
                    var pageSource = document.documentElement.outerHTML;
                    
                    // Common patterns
                    var patterns = [
                        /var\\s+([a-zA-Z0-9_$]+)\\s*=\\s*['"]([^'"]*\\.m3u[^'"]*)['"]/g,
                        /source\\s*:\\s*['"]([^'"]*\\.m3u[^'"]*)['"]/g,
                        /file\\s*:\\s*['"]([^'"]*\\.m3u[^'"]*)['"]/g,
                        /url\\s*:\\s*['"]([^'"]*\\.m3u[^'"]*)['"]/g,
                        /src\\s*=\\s*['"]([^'"]*\\.m3u[^'"]*)['"]/g,
                        /(https?:\\/\\/[^'"\s]+\\.m3u[8]?[^'"\s]*)/g
                    ];
                    
                    for (var i = 0; i < patterns.length; i++) {
                        var regex = patterns[i];
                        var match;
                        
                        while ((match = regex.exec(pageSource)) !== null) {
                            var url = match[1].includes('http') ? match[1] : match[2];
                            if (url && url.includes('.m3u')) {
                                results.push({type: 'regex', url: url});
                            }
                        }
                    }
                    
                    // 3. Network kayıtlarındaki m3u isteklerini kontrol et
                    if (window.performance && window.performance.getEntries) {
                        var entries = window.performance.getEntries();
                        for (var i = 0; i < entries.length; i++) {
                            if (entries[i].name && entries[i].name.includes('.m3u')) {
                                results.push({type: 'network', url: entries[i].name});
                            }
                        }
                    }
                    
                    return results;
                }
                
                return extractM3uUrls();
                """)
                
                logger.info(f"JavaScript sonucu: {js_result}")
                
                if js_result and len(js_result) > 0:
                    for result in js_result:
                        if result.get('url') and '.m3u' in result.get('url'):
                            logger.info(f"JavaScript analizi ile m3u URL bulundu: {result.get('url')}")
                            driver.quit()
                            return result.get('url')
                
            except Exception as js_error:
                logger.warning(f"JavaScript analizi hatası: {js_error}")
            
            # HAR dosyası oluştur ve içinden m3u8 URL'leri ara
            try:
                # Performance loglarını al
                logger.info("Performance logları alınıyor...")
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
            
            # İframe içeriğini kontrol et
            try:
                logger.info("iframe'ler aranıyor...")
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                
                for i, iframe in enumerate(iframes):
                    try:
                        iframe_src = iframe.get_attribute("src")
                        logger.info(f"iframe {i} bulundu: {iframe_src}")
                        
                        # iframe'e geç
                        driver.switch_to.frame(iframe)
                        iframe_content = driver.page_source
                        
                        # Bu içerikte m3u URL'si ara
                        m3u_url = find_m3u_in_content(iframe_content)
                        if m3u_url:
                            logger.info(f"iframe {i} içinde m3u URL bulundu: {m3u_url}")
                            driver.quit()
                            return m3u_url
                        
                        # Ana içeriğe geri dön
                        driver.switch_to.default_content()
                    except Exception as iframe_error:
                        logger.warning(f"iframe {i} işleme hatası: {iframe_error}")
                        driver.switch_to.default_content()
            except Exception as iframes_error:
                logger.warning(f"iframe'leri bulma hatası: {iframes_error}")
            
            # Hiçbir şey bulunamadı
            logger.warning(f"Selenium ile GeoLive iframe içinde m3u URL bulunamadı")
            driver.quit()
            
            # Son çare: Bilinen URL desenlerini dene
            channel_name = iframe_url.split('kanal=')[1].split('&')[0] if 'kanal=' in iframe_url else None
            if channel_name:
                logger.info(f"Bilinen M3U patternleri deneniyor: {channel_name}")
                known_patterns = [
                    f"https://canlitv.center/stream/{channel_name}.m3u8",
                    f"https://cdn.yayin.com.tr/tv/{channel_name}/playlist.m3u8",
                    f"https://tv-{channel_name}.live.trt.com.tr/master.m3u8",
                    f"https://stream.canlitv.com/{channel_name}/tracks-v1/index.m3u8",
                    f"https://canlitv-pull.ercdn.net/{channel_name}/playlist.m3u8",
                    # Bayrak TV gibi özel kanallar için pattern
                    f"https://stream.tvcdn.biz/{channel_name}/tracks-v1/index.m3u8",
                    f"https://live.artidijitalmedya.com/{channel_name}/index.m3u8",
                    # TRT kanalları için özel patternler
                    f"https://tv-{channel_name.replace('-canli-yayin', '')}.medya.trt.com.tr/master.m3u8",
                    # Özel TV kanalları için patternler
                    f"https://{channel_name.split('-')[0]}.blutv.com/blutv_{channel_name.split('-')[0]}/live.m3u8",
                ]
                
                # Eurostar ve diğer tematik kanallar için özel patternler
                if "eurostar" in channel_name:
                    eurostar_patterns = [
                        "https://stream.eurostar.com.tr/eurostar/smil:eurostar.smil/playlist.m3u8",
                        "https://mn-nl.mncdn.com/eurostar/eurostar/chunklist.m3u8",
                        "https://xrklj56s.rocketcdn.com/eurostar.stream_720p/chunklist.m3u8",
                        "https://streaming.eurostar.com.tr/eurostar/eurostar/playlist.m3u8",
                        # Bilinen diğer CDN'ler için
                        "https://cdn-eurostar.yayin.com.tr/eurostar/eurostar/playlist.m3u8",
                        "https://live.duhnet.tv/S2/HLS_LIVE/eurostar/playlist.m3u8"
                    ]
                    known_patterns.extend(eurostar_patterns)
                    logger.info(f"Eurostar için {len(eurostar_patterns)} özel pattern eklendi")
                
                # Sinema kanalları için özel patternler
                elif "sinema" in channel_name:
                    sinema_patterns = [
                        f"https://sinema-{channel_name.split('-')[-1]}.blutv.com/live/playlist.m3u8",
                        f"https://cdn-sinema.yayin.com.tr/{channel_name}/playlist.m3u8"
                    ]
                    known_patterns.extend(sinema_patterns)
                
                # Spor kanalları için özel patternler
                elif "spor" in channel_name or "sport" in channel_name:
                    sport_patterns = [
                        f"https://live.sportstv.com.tr/{channel_name}/playlist.m3u8",
                        f"https://spor.blutv.com/{channel_name}/live.m3u8"
                    ]
                    known_patterns.extend(sport_patterns)
                
                # Belgesel kanalları için özel patternler
                elif "belgesel" in channel_name or "discovery" in channel_name or "national" in channel_name:
                    documentary_patterns = [
                        f"https://d-{channel_name}.blutv.com/live/playlist.m3u8",
                        f"https://belgesel.duhnet.tv/{channel_name}/playlist.m3u8"
                    ]
                    known_patterns.extend(documentary_patterns)
                
                # Çocuk kanalları için özel patternler
                elif "cocuk" in channel_name or "kids" in channel_name or "cartoon" in channel_name:
                    kids_patterns = [
                        f"https://cdn-cocuk.yayin.com.tr/{channel_name}/playlist.m3u8",
                        f"https://kids.blutv.com/{channel_name}/playlist.m3u8"
                    ]
                    known_patterns.extend(kids_patterns)
                
                for pattern in known_patterns:
                    try:
                        head_response = requests.head(pattern, timeout=5)
                        if head_response.status_code < 400:
                            logger.info(f"Bilinen pattern çalışıyor: {pattern}")
                            return pattern
                    except:
                        continue
            
            return None
            
        except Exception as browse_error:
            logger.error(f"GeoLive sayfası Selenium ile erişim hatası: {browse_error}")
            try:
                if driver:
                    driver.quit()
            except:
                pass
            return None
            
    except Exception as e:
        logger.error(f"Selenium ile GeoLive iframe işleme hatası: {str(e)}")
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
        
        # canlitv.vin özel desenleri
        r'var\s+vidogevideo\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'var\s+kaynakurl\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'var\s+url\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'var\s+videolink\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'var\s+m3ulink\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'var\s+str\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'videojs\([^\)]+\)\.src\(\{\s*src:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'if\s*\((\s*a\s*\+\s*b\s*\+\s*c\s*\+\s*d\s*\+\s*e\s*\+\s*f\s*)\)',
        r'player\.src\(\{\s*src:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'player\.src\s*=\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        r'jwplayer\([^\)]+\)\.setup\(\{\s*[^\{\}]*file:\s*[\'"]([^\'"]*.m3u[8]?[^\'"]*)[\'"]',
        
        # Obfuscated JavaScript için
        r'\\x68\\x74\\x74\\x70([^\'"]*.m3u[8]?[^\'"]*)',
        r'\\u0068\\u0074\\u0074\\u0070([^\'"]*.m3u[8]?[^\'"]*)',
    ]
    
    # Önce sayfada görülen string birleştirme işlemlerini tespit etmeye çalış
    # Bu tür JavaScript kod obfuscation tekniklerini çözmeye çalışır
    js_concat_patterns = [
        r'((?:[a-zA-Z0-9_$]+\s*\+\s*){2,}[a-zA-Z0-9_$]+)',  # a + b + c formatı
        r'(\[[^\[\]]+\]\.join\(\s*[\'"][\'"]?\s*\))',  # ["h","t","t","p"].join("") formatı
        r'String\.fromCharCode\(([^\)]+)\)',  # String.fromCharCode(104,116,116,112) formatı
    ]
    
    for concat_pattern in js_concat_patterns:
        concat_matches = re.findall(concat_pattern, content)
        for concat_expr in concat_matches:
            # Eğer bu bir join ifadesi ise
            if '.join(' in concat_expr:
                try:
                    # ["h","t","t","p"].join("")
                    array_str = concat_expr.split('.join(')[0].strip()
                    # Basit bir JavaScript array parsing
                    if array_str.startswith('[') and array_str.endswith(']'):
                        array_items = re.findall(r'[\'"]([^\'"]*)[\'"]', array_str)
                        combined = ''.join(array_items)
                        if '.m3u' in combined:
                            return combined
                except Exception as e:
                    logger.warning(f"Join ifadesi çözülemedi: {e}")
            
            # String.fromCharCode işlemi ise
            elif 'String.fromCharCode' in concat_expr:
                try:
                    # String.fromCharCode(104,116,116,112)
                    char_codes = re.findall(r'(\d+)', concat_expr)
                    if char_codes:
                        chars = [chr(int(code)) for code in char_codes]
                        combined = ''.join(chars)
                        if '.m3u' in combined:
                            return combined
                except Exception as e:
                    logger.warning(f"fromCharCode ifadesi çözülemedi: {e}")
            
            # Basit string birleştirme ise (a + b + c)
            else:
                # JavaScript değişken birleştirme işlemleri için daha derin analiz gerekebilir
                # Bu örnek için sadece sayfada gördüğümüz içeriği analiz ediyoruz
                # Gerçek bir çözüm için JavaScript parsing/execution gerekebilir
                pass
    
    # canlitv.vin'de özel olarak kullanılan string birleştirme yöntemini tespit et
    concat_str_pattern = r'([\'"](https?:)?/?/?[^\'"]*[\'"])\s*\+\s*([\'"](/[^\'"]*\.m3u[8]?[^\'"]*)[\'"])'
    concat_matches = re.findall(concat_str_pattern, content)
    for match in concat_matches:
        try:
            part1 = match[0].strip('\'"')
            part2 = match[3].strip('\'"')
            combined = part1 + part2
            if '.m3u' in combined:
                logger.info(f"String birleştirme tespit edildi: {combined}")
                return combined
        except Exception as e:
            logger.warning(f"String birleştirme çözülemedi: {e}")
    
    # Base64 kodlu içerik arama
    base64_pattern = r'atob\([\'"]([^\'"]+)[\'"]\)'
    base64_matches = re.findall(base64_pattern, content)
    for encoded in base64_matches:
        try:
            import base64
            decoded = base64.b64decode(encoded).decode('utf-8')
            logger.info(f"Base64 çözüldü: {decoded[:50]}...")
            
            # Çözülen içerikte m3u arama
            m3u_in_decoded = find_m3u_in_content(decoded)
            if m3u_in_decoded:
                return m3u_in_decoded
        except Exception as e:
            logger.warning(f"Base64 çözme hatası: {e}")
    
    # Tüm pattern'leri dene
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            for match in matches:
                # m3u ya da m3u8 uzantılı dosyaya denk gelmişsek kullan
                if isinstance(match, tuple):  # Eğer pattern gruplar içeriyorsa
                    for group in match:
                        if group and '.m3u' in group:
                            logger.info(f"M3U URL bulundu (grup): {group}")
                            return group
                elif match and '.m3u' in match:
                    logger.info(f"M3U URL bulundu: {match}")
                    return match
    
    # Son çare olarak .m3u veya .m3u8 içeren herhangi bir URL'yi bul
    all_urls = re.findall(r'[\'"\(]((https?:)?//[^\'"\s\)]+)[\'"\)]', content)
    for url in all_urls:
        if isinstance(url, tuple):
            url = url[0]
        if '.m3u' in url:
            logger.info(f"Genel URL aramasında m3u bulundu: {url}")
            return url
    
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
    """Tüm kanal sayfalarını kaydeder - debug için kullanılır"""
    logger.info("Tüm kanal sayfaları indiriliyor ve kaydediliyor...")
    
    # Debug klasörü oluştur
    debug_dir = "debug_channels"
    os.makedirs(debug_dir, exist_ok=True)
    
    # Tüm URL'leri topla
    channel_urls = get_all_channel_urls()
    
    # Hatalı URL'ler için düzeltmeler
    url_corrections = {
        "cnn-turk-izle": "cnn-turk-canli-yayin",
        "ntv-izle": "ntv-canli-yayin",
        "haberturk-izle": "haberturk-canli-yayin"
    }
    
    processed_count = 0
    for url in channel_urls:
        # Kanal adını URL'den çıkar
        channel_slug = url.rstrip('/').split('/')[-1]
        
        # Hatalı URL formatlarını düzelt
        for wrong_format, correct_format in url_corrections.items():
            if wrong_format in url:
                url = url.replace(wrong_format, correct_format)
                channel_slug = correct_format
                logger.info(f"URL düzeltildi: {wrong_format} -> {correct_format}")
        
        logger.info(f"Kanal sayfası indiriliyor: {channel_slug}")
        
        try:
            # Sayfayı indir
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
            
            if response.status_code != 200:
                logger.error(f"Kanal sayfası yüklenemedi: HTTP {response.status_code}")
                continue
                
            # Sayfayı kaydet
            with open(f"{debug_dir}/{channel_slug}.html", "w", encoding="utf-8") as f:
                f.write(response.text)
                
            logger.info(f"Kanal HTML içeriği kaydedildi: {debug_dir}/{channel_slug}.html")
            
            # Sayfadaki iframe'leri bul ve içeriklerini kaydet
            soup = BeautifulSoup(response.text, 'html.parser')
            iframes = soup.find_all('iframe')
            
            for i, iframe in enumerate(iframes):
                iframe_src = iframe.get('src', '')
                
                # iframe src'yi normalize et
                if iframe_src:
                    if iframe_src.startswith('//'):
                        iframe_src = 'https:' + iframe_src
                    elif not iframe_src.startswith('http'):
                        iframe_src = urllib.parse.urljoin(url, iframe_src)
                        
                    try:
                        # iframe içeriğini indir
                        iframe_response = requests.get(iframe_src, headers={
                            "User-Agent": USER_AGENT,
                            "Referer": url
                        }, timeout=15)
                        
                        if iframe_response.status_code == 200:
                            # iframe içeriğini kaydet
                            with open(f"{debug_dir}/{channel_slug}_iframe_{i}.html", "w", encoding="utf-8") as f:
                                f.write(iframe_response.text)
                                
                            logger.info(f"İframe içeriği kaydedildi: {debug_dir}/{channel_slug}_iframe_{i}.html")
                    except Exception as iframe_error:
                        logger.warning(f"İframe indirilirken hata: {iframe_error}")
            
            processed_count += 1
            
            # Her 10 sayfada bir 2 saniye bekle - rate limiting'i önlemek için
            if processed_count % 10 == 0:
                time.sleep(2)
            else:
                time.sleep(1)  # Her sayfa arasında 1 saniye bekle
                
        except Exception as e:
            logger.error(f"Kanal sayfası kaydedilirken hata: {e}")
            
        # Her sayfa arasında 2 saniye bekle - rate limiting
        time.sleep(2)
    
    logger.info(f"Toplam {processed_count} kanal sayfası başarıyla kaydedildi.")

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