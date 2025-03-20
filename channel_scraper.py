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
        # Site yapısını direk incelemek için ana sayfayı çekelim
        logger.info(f"Ana sayfa inceleniyor")
        response = requests.get(BASE_URL, headers=headers, timeout=15)
        
        if response.status_code != 200:
            logger.error(f"Ana sayfa yüklenirken hata: HTTP {response.status_code}")
            return use_fallback_method()
        
        # Debug: HTML içeriğini kaydet
        with open('ana_sayfa.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
            logger.info("Ana sayfa HTML içeriği kaydedildi")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Ana menüden kanal kategorilerini bul
        menu_items = soup.select('ul.menu > li > a')
        category_urls = []
        
        for item in menu_items:
            href = item.get('href')
            if href and ('kategori' in href or 'canli-' in href or 'kanallar' in href):
                if not href.startswith('http'):
                    href = urllib.parse.urljoin(BASE_URL, href)
                category_urls.append(href)
                logger.info(f"Kategori bulundu: {href}")
        
        # 2. Ana sayfadaki popüler/öne çıkan kanal kartlarını bul
        card_links = soup.select('div.card a')
        for link in card_links:
            href = link.get('href')
            if href and ('-izle' in href or 'canli-' in href):
                if not href.startswith('http'):
                    href = urllib.parse.urljoin(BASE_URL, href)
                all_channel_urls.append(href)
                logger.info(f"Ana sayfada kanal bulundu: {href}")
        
        # 3. Özel olarak direk kanal listesi sayfalarını kontrol et
        kanallar_url = urllib.parse.urljoin(BASE_URL, "kanallar")
        logger.info(f"Tüm kanallar sayfası inceleniyor: {kanallar_url}")
        
        try:
            kanallar_response = requests.get(kanallar_url, headers=headers, timeout=15)
            if kanallar_response.status_code == 200:
                kanallar_soup = BeautifulSoup(kanallar_response.text, 'html.parser')
                
                # Kanal liste sayfasını debug için kaydet
                with open('kanallar_sayfasi.html', 'w', encoding='utf-8') as f:
                    f.write(kanallar_response.text)
                
                # Kanal kartlarını bul - farklı sınıf/id'ler deneyerek
                card_patterns = [
                    'div.card a', 'div.channels a', 'div.tv-card a', 'div.kanal a',
                    'li.channel a', 'div.card-body a', 'div.card-title a',
                    'a.tv-link', 'a.channel-link', 'a.kanal-link'
                ]
                
                for pattern in card_patterns:
                    links = kanallar_soup.select(pattern)
                    if links:
                        logger.info(f"'{pattern}' seçicisiyle {len(links)} kanal bulundu")
                        
                        for link in links:
                            href = link.get('href')
                            if href and ('-izle' in href or 'canli-' in href or 'tv-' in href):
                                if not href.startswith('http'):
                                    href = urllib.parse.urljoin(BASE_URL, href)
                                all_channel_urls.append(href)
                                logger.info(f"Kanal URL bulundu: {href}")
                
                # Herhangi bir şekilde link bulunamadıysa tüm a etiketlerini tara
                if not all_channel_urls:
                    logger.info("Özel seçicilerle kanal bulunamadı, tüm linkler taranıyor")
                    all_links = kanallar_soup.find_all('a', href=True)
                    
                    for link in all_links:
                        href = link.get('href')
                        # Kanal URL'si olabilecek linkleri filtrele
                        if href and ('-izle' in href or 'canli-' in href or 'tv-' in href) and not '#' in href and not 'javascript:' in href:
                            if not href.startswith('http'):
                                href = urllib.parse.urljoin(BASE_URL, href)
                            all_channel_urls.append(href)
                            logger.info(f"Genel tarama ile kanal URL bulundu: {href}")
            else:
                logger.warning(f"Kanallar sayfası alınamadı: HTTP {kanallar_response.status_code}")
                
        except Exception as e:
            logger.error(f"Kanallar sayfası işlenirken hata: {str(e)}")
        
        # 4. Her kategori sayfasını ziyaret et ve kanal linklerini topla
        for category_url in category_urls:
            try:
                logger.info(f"Kategori inceleniyor: {category_url}")
                cat_response = requests.get(category_url, headers=headers, timeout=15)
                
                if cat_response.status_code != 200:
                    logger.warning(f"Kategori sayfası alınamadı: {category_url}")
                    continue
                
                cat_soup = BeautifulSoup(cat_response.text, 'html.parser')
                
                # Tüm muhtemel kanal kartı içeren etiketleri dene
                for selector in card_patterns:
                    cat_links = cat_soup.select(selector)
                    for link in cat_links:
                        href = link.get('href')
                        if href and ('-izle' in href or 'canli-' in href or 'tv-' in href):
                            if not href.startswith('http'):
                                href = urllib.parse.urljoin(BASE_URL, href)
                            all_channel_urls.append(href)
                            logger.info(f"Kategori sayfasında kanal bulundu: {href}")
                
                # Herhangi bir şekilde link bulunamadıysa tüm a etiketlerini tara
                if not all_channel_urls:
                    all_links = cat_soup.find_all('a', href=True)
                    for link in all_links:
                        href = link.get('href')
                        # Kanal URL'si olabilecek linkleri filtrele
                        if href and ('-izle' in href or 'canli-' in href or 'tv-' in href) and not '#' in href and not 'javascript:' in href:
                            if not href.startswith('http'):
                                href = urllib.parse.urljoin(BASE_URL, href)
                            all_channel_urls.append(href)
                            logger.info(f"Kategori genel taramayla kanal bulundu: {href}")
                            
            except Exception as e:
                logger.error(f"Kategori sayfası işlenirken hata: {category_url} - {str(e)}")
        
        # Eğer hiç URL bulunamadıysa, alternatif metod kullanılacak
        if not all_channel_urls:
            logger.warning("Hiç kanal URL'si bulunamadı, alternatif metoda geçiliyor...")
            return use_fallback_method()
        
        # URL'leri benzersiz hale getir
        all_channel_urls = list(set(all_channel_urls))
        logger.info(f"Toplam {len(all_channel_urls)} benzersiz kanal URL'si bulundu")
        
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
    channel_name_lower = channel_info['name'].lower()
    
    # ------------------- BİLİNEN KANALLAR LİSTESİ -------------------
    # Bu listeyi güncelleyerek tüm kanalların doğrudan m3u linklerini ekleyebilirsiniz
    known_channels = {
        # TRT Kanalları
        'trt 1': "https://tv-trt1.medya.trt.com.tr/master.m3u8",
        'trt1': "https://tv-trt1.medya.trt.com.tr/master.m3u8",
        'trt 2': "https://tv-trt2.medya.trt.com.tr/master.m3u8",
        'trt2': "https://tv-trt2.medya.trt.com.tr/master.m3u8",
        'trt spor': "https://tv-trtspor1.medya.trt.com.tr/master.m3u8",
        'trt haber': "https://tv-trthaber.medya.trt.com.tr/master.m3u8",
        'trt belgesel': "https://tv-trtbelgesel.medya.trt.com.tr/master.m3u8",
        'trt çocuk': "https://tv-trtcocuk.medya.trt.com.tr/master.m3u8",
        'trt müzik': "https://tv-trtmuzik.medya.trt.com.tr/master.m3u8",
        'trt avaz': "https://tv-trtavaz.medya.trt.com.tr/master.m3u8",
        'trt kurdî': "https://tv-trtkurdi.medya.trt.com.tr/master.m3u8",
        'trt kurdi': "https://tv-trtkurdi.medya.trt.com.tr/master.m3u8",
        'trt kurd': "https://tv-trtkurdi.medya.trt.com.tr/master.m3u8",
        'trt türk': "https://tv-trtturk.medya.trt.com.tr/master.m3u8",
        'trt turk': "https://tv-trtturk.medya.trt.com.tr/master.m3u8",
        'trt arabi': "https://tv-trtarabi.medya.trt.com.tr/master.m3u8",
        'trt world': "https://tv-trtworld.medya.trt.com.tr/master.m3u8",
        'trt spor yıldız': "https://tv-trtspor2.medya.trt.com.tr/master.m3u8",
        'trt spor yildiz': "https://tv-trtspor2.medya.trt.com.tr/master.m3u8",
        'trt eba ilkokul': "https://tv-e-okul00.medya.trt.com.tr/master.m3u8",
        'trt eba ortaokul': "https://tv-e-okul01.medya.trt.com.tr/master.m3u8",
        'trt eba lise': "https://tv-e-okul02.medya.trt.com.tr/master.m3u8",
        
        # Diğer Bilinen Türk Kanalları
        'kanal d': "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3",
        'kanald': "https://demiroren.daioncdn.net/kanald/kanald.m3u8?app=kanald_web&ce=3",
        'atv': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/8/index.m3u8",
        'show tv': "https://ciner-live.daioncdn.net/showtv/showtv.m3u8",
        'showtv': "https://ciner-live.daioncdn.net/showtv/showtv.m3u8",
        'star tv': "https://dogus-live.daioncdn.net/startv/startv.m3u8",
        'startv': "https://dogus-live.daioncdn.net/startv/startv.m3u8",
        'tv8': "https://tv8-live.daioncdn.net/tv8/tv8.m3u8",
        'tv 8': "https://tv8-live.daioncdn.net/tv8/tv8.m3u8",
        'fox tv': "https://foxtv.blutv.com/blutv_foxtv_live/live.m3u8",
        'foxtv': "https://foxtv.blutv.com/blutv_foxtv_live/live.m3u8",
        'fox': "https://foxtv.blutv.com/blutv_foxtv_live/live.m3u8",
        'kanal 7': "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
        'kanal7': "https://kanal7-live.daioncdn.net/kanal7/kanal7.m3u8",
        'teve2': "https://demiroren.daioncdn.net/teve2/teve2.m3u8?app=teve2_web&ce=3",
        'teve 2': "https://demiroren.daioncdn.net/teve2/teve2.m3u8?app=teve2_web&ce=3",
        'beyaz tv': "https://beyaztv-live.daioncdn.net/beyaztv/beyaztv.m3u8",
        'beyaztv': "https://beyaztv-live.daioncdn.net/beyaztv/beyaztv.m3u8",
        'a2': "https://stream2.filbox.com.tr/live/7d6b0f92687fa8e886368f640271243b/10/index.m3u8",
        
        # Spor Kanalları
        'tv8.5': "https://tv85-live.daioncdn.net/tv85/tv85.m3u8",
        'tv 8.5': "https://tv85-live.daioncdn.net/tv85/tv85.m3u8",
        'gs tv': "https://owifavo5.rocketcdn.com/gstv/gstv.smil/master.m3u8",
        'gstv': "https://owifavo5.rocketcdn.com/gstv/gstv.smil/master.m3u8",
        'fb tv': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/66/index.m3u8",
        'fbtv': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/66/index.m3u8",
        'bjk tv': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/5/index.m3u8",
        'bjktv': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/5/index.m3u8",
        'a spor': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/95/index.m3u8",
        'aspor': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/95/index.m3u8",
        'sports tv': "https://live.sportstv.com.tr/hls/low/sportstv.m3u8",
        'sportstv': "https://live.sportstv.com.tr/hls/low/sportstv.m3u8",
        'tivibu spor': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/67/index.m3u8",
        
        # Haber Kanalları
        'ntv': "https://dogus-live.daioncdn.net/ntv/ntv.m3u8",
        'cnn türk': "https://live.duhnet.tv/S2/HLS_LIVE/cnnturknp/playlist.m3u8",
        'cnn turk': "https://live.duhnet.tv/S2/HLS_LIVE/cnnturknp/playlist.m3u8",
        'cnnturk': "https://live.duhnet.tv/S2/HLS_LIVE/cnnturknp/playlist.m3u8",
        'haber türk': "https://ciner-live.daioncdn.net/haberturktv/haberturktv.m3u8",
        'haberturk': "https://ciner-live.daioncdn.net/haberturktv/haberturktv.m3u8",
        'haberturk tv': "https://ciner-live.daioncdn.net/haberturktv/haberturktv.m3u8",
        'halk tv': "https://halktv.daioncdn.net/halktv/halktv.m3u8?app=halktv_web&ce=3",
        'halktv': "https://halktv.daioncdn.net/halktv/halktv.m3u8?app=halktv_web&ce=3",
        'tgrt haber': "https://tgrt-live.daioncdn.net/tgrthaber/tgrthaber.m3u8",
        'tgrthaber': "https://tgrt-live.daioncdn.net/tgrthaber/tgrthaber.m3u8",
        'bloomberg ht': "https://bloomberght-live.daioncdn.net/bloomberght/bloomberght.m3u8",
        'bloomberght': "https://bloomberght-live.daioncdn.net/bloomberght/bloomberght.m3u8",
        'tv 100': "https://tv100.blutv.com/blutv_tv100_live/live.m3u8",
        'tv100': "https://tv100.blutv.com/blutv_tv100_live/live.m3u8",
        '24 tv': "https://turkmedya-live.ercdn.net/tv24/tv24.m3u8",
        '24tv': "https://turkmedya-live.ercdn.net/tv24/tv24.m3u8",
        'ulusal kanal': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/77/index.m3u8",
        'a haber': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/27/index.m3u8",
        'ahaber': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/27/index.m3u8",
        
        # Azerbaycan Kanalları
        'aztv': "http://az.digicom.az:8080/play/a01v/index.m3u8",
        'az tv': "http://az.digicom.az:8080/play/a01v/index.m3u8",
        'idman tv': "http://az.digicom.az:8080/play/a01q/index.m3u8",
        'space tv': "http://az.digicom.az:8080/play/a01o/index.m3u8",
        'cbc az': "http://az.digicom.az:8080/play/a01k/index.m3u8",
        'cbc az tv': "http://az.digicom.az:8080/play/a01k/index.m3u8",
        'xezer tv': "http://az.digicom.az:8080/play/a01y/index.m3u8",
        'ictimai tv': "http://az.digicom.az:8080/play/a025/index.m3u8",
        'atv azad': "http://az.digicom.az:8080/play/a01p/index.m3u8",
        'atv azad tv': "http://az.digicom.az:8080/play/a01p/index.m3u8",
        'arb tv': "http://az.digicom.az:8080/play/a01v/index.m3u8",
        'arb 24 tv': "http://85.132.81.184:8080/arb24/live1/index.m3u8",
        
        # Müzik Kanalları
        'kral tv': "https://dogus-live.daioncdn.net/kraltv/kraltv.m3u8",
        'kraltv': "https://dogus-live.daioncdn.net/kraltv/kraltv.m3u8",
        'kral pop': "https://dogus-live.daioncdn.net/kralpoptv/kralpoptv.m3u8",
        'kralpop': "https://dogus-live.daioncdn.net/kralpoptv/kralpoptv.m3u8",
        'power türk': "https://livetv.powerapp.com.tr/powerturkTV/powerturkhd.smil/playlist.m3u8",
        'power turk': "https://livetv.powerapp.com.tr/powerturkTV/powerturkhd.smil/playlist.m3u8",
        'powerturk': "https://livetv.powerapp.com.tr/powerturkTV/powerturkhd.smil/playlist.m3u8",
        'power tv': "https://livetv.powerapp.com.tr/powerTV/powerhd.smil/playlist.m3u8",
        'powertv': "https://livetv.powerapp.com.tr/powerTV/powerhd.smil/playlist.m3u8",
        'number one': "https://b01c02nl.mediatriple.net/videoonlylive/mtkgeuihrlfwlive/u_stream_5c9e17cd6360b_1/playlist.m3u8",
        'numberone': "https://b01c02nl.mediatriple.net/videoonlylive/mtkgeuihrlfwlive/u_stream_5c9e17cd6360b_1/playlist.m3u8",
        'number one türk': "https://b01c02nl.mediatriple.net/videoonlylive/mtkgeuihrlfwlive/u_stream_5c9e198784bdc_1/playlist.m3u8",
        'numberone türk': "https://b01c02nl.mediatriple.net/videoonlylive/mtkgeuihrlfwlive/u_stream_5c9e198784bdc_1/playlist.m3u8",
        'dream türk': "https://live.duhnet.tv/S2/HLS_LIVE/dreamturknp/playlist.m3u8",
        'dream turk': "https://live.duhnet.tv/S2/HLS_LIVE/dreamturknp/playlist.m3u8",
        'dreamturk': "https://live.duhnet.tv/S2/HLS_LIVE/dreamturknp/playlist.m3u8",
        'tatlıses tv': "https://live.artidijitalmedya.com/artidijital_tatlisestv/tatlisestv/playlist.m3u8",
        'tatlises tv': "https://live.artidijitalmedya.com/artidijital_tatlisestv/tatlisestv/playlist.m3u8",
        
        # Çocuk Kanalları
        'minika go': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/51/index.m3u8",
        'minikago': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/51/index.m3u8",
        'minika çocuk': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/52/index.m3u8",
        'minika cocuk': "https://stream2.filbox.com.tr/live/08d07e8f6f186381322a5fd7c8941558/52/index.m3u8",
        'cartoon network': "https://cartoonnetwork.blutv.com/blutv_cartoonnetwork/live.m3u8",
    }
    
    # Kanal ismi bilinen listede mi kontrol et
    if channel_name_lower in known_channels:
        m3u_url = known_channels[channel_name_lower]
        logger.info(f"Bilinen kanal URL'si kullanılıyor: {channel_info['name']} -> {m3u_url}")
        return m3u_url
    
    # Benzer adlarda arama yap
    for key, value in known_channels.items():
        # Kanal ismi içeriyorsa
        if key in channel_name_lower or channel_name_lower in key:
            logger.info(f"Benzer isimli bilinen kanal URL'si kullanılıyor: {channel_info['name']} -> {value}")
            return value
    
    # Web sayfasından çekmeye çalış - Eğer bu noktada hala bir URL bulunmadıysa
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
            
            # Debug: Kanal HTML içeriğini kaydet
            debug_file = f"debug_channel_{channel_info['name'].replace(' ', '_')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
                logger.info(f"Kanal HTML içeriği kaydedildi: {debug_file}")
                
        except Exception as e:
            logger.error(f"Sayfa alınırken hata: {channel_info['url']} - {str(e)}")
            return None
        
        # HTML içeriğinden URL bulma kodunu çalıştır
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Video player container'ını bul
        player_selectors = [
            '#video-player', '#player', '.video-player', '.player', '#tv-player', 
            '.tv-player', '#videoContainer', '.videoContainer', '#playerContainer', 
            '.playerContainer', '#livePlayer', '.livePlayer', '#video', '.video'
        ]
        
        player_element = None
        for selector in player_selectors:
            found = soup.select_one(selector)
            if found:
                player_element = found
                logger.info(f"Player elementi bulundu: {selector}")
                break
                
        # İframe'leri kontrol et
        if player_element:
            iframe = player_element.find('iframe')
            if iframe and iframe.get('src'):
                iframe_src = iframe.get('src')
                if not iframe_src.startswith('http'):
                    iframe_src = f"https:{iframe_src}" if iframe_src.startswith('//') else f"https://{iframe_src}"
                
                logger.info(f"İframe URL bulundu: {iframe_src}")
                
                try:
                    iframe_response = requests.get(iframe_src, headers=headers, timeout=10)
                    if iframe_response.status_code == 200:
                        m3u_url = find_m3u_in_content(iframe_response.text)
                        if m3u_url:
                            return m3u_url
                except Exception as e:
                    logger.warning(f"İframe içeriği alınırken hata: {e}")
        
        # Son çare olarak m3u URL'si ara
        m3u_url = find_m3u_in_content(html_content)
        if m3u_url:
            return m3u_url
        
        # M3U bulunamadı, null dön
        logger.warning(f"M3U URL bulunamadı: {channel_info['name']}")
        return None
        
    except Exception as e:
        logger.error(f"M3U URL çıkarılırken hata oluştu ({channel_info['url']}): {e}")
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