#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime
import time

def get_channel_links(base_url):
    """Ana sayfadan kanal linklerini toplar."""
    response = requests.get(base_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    soup = BeautifulSoup(response.text, 'html.parser')
    
    channel_links = []
    # Kanal linklerini bul - Sitedeki gerçek yapıya göre ayarlanmalı
    # Örnek: tüm kanal kartları veya kanal linkleri için selector
    channel_elements = soup.select('.channel-card a, .kanal-kutu a, .tv-channel a')
    
    if not channel_elements:
        # Alternatif selector denemeleri
        channel_elements = soup.select('a[href*="/izle/"]')
    
    for element in channel_elements:
        href = element.get('href')
        if href and ('/izle/' in href or '/canli/' in href):
            # Turkçe ve Azerbaycan kanallarını filtrele (gerekirse)
            channel_links.append(href)
    
    # Hiç link bulunamadıysa, tüm link etiketlerini tara
    if not channel_links:
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if '/izle/' in href or '/canli/' in href:
                channel_links.append(href)
    
    return channel_links

def extract_m3u_url(channel_url):
    """Kanal sayfasından m3u URL'sini çıkarır."""
    try:
        response = requests.get(channel_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # JavaScript içinde gömülü olan m3u URL'sini bulmak için farklı regex pattern'leri dene
        patterns = [
            r'source:\s*[\'"]([^\'"]*.m3u[^\'"]*)[\'"]',
            r'file:\s*[\'"]([^\'"]*.m3u[^\'"]*)[\'"]',
            r'src=[\'"]([^\'"]*.m3u[^\'"]*)[\'"]',
            r'(https?://[^\'"\s]+\.m3u[^\'"\s]*)',
            r'(https?://[^\'"\s]+\.m3u8[^\'"\s]*)'
        ]
        
        for pattern in patterns:
            m3u_matches = re.search(pattern, response.text)
            if m3u_matches:
                return m3u_matches.group(1)
        
        # İframe içinde kaynak olabilir
        iframe_src = None
        soup = BeautifulSoup(response.text, 'html.parser')
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            iframe_src = iframe.get('src')
            if not iframe_src.startswith('http'):
                iframe_src = f"https:{iframe_src}" if iframe_src.startswith('//') else f"https://{iframe_src}"
            
            # iframe içeriğini al
            try:
                iframe_response = requests.get(iframe_src, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Referer': channel_url
                })
                
                # iframe içinde m3u arama
                for pattern in patterns:
                    m3u_matches = re.search(pattern, iframe_response.text)
                    if m3u_matches:
                        return m3u_matches.group(1)
            except Exception as iframe_error:
                print(f"iframe hatası ({iframe_src}): {iframe_error}")
        
        return None
    except Exception as e:
        print(f"Hata oluştu (URL: {channel_url}): {e}")
        return None

def create_m3u_file(channels_data, output_file):
    """Toplanan kanal bilgilerinden m3u dosyası oluşturur."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        
        for channel in channels_data:
            if channel['m3u_url']:
                f.write(f"#EXTINF:-1,{channel['name']}\n")
                f.write(f"{channel['m3u_url']}\n")

def main():
    base_url = "https://www.canlitv.me/hd1"
    output_file = "kanallar.m3u"
    
    print(f"Kanal listesi alınıyor: {base_url}")
    channel_links = get_channel_links(base_url)
    
    print(f"Toplam {len(channel_links)} kanal linki bulundu.")
    
    channels_data = []
    for i, link in enumerate(channel_links):
        if not link.startswith('http'):
            link = "https://www.canlitv.me" + link if not link.startswith('/') else "https://www.canlitv.me" + link
        
        channel_name = link.split('/')[-1].replace('-', ' ').title()
        print(f"[{i+1}/{len(channel_links)}] İşleniyor: {channel_name}")
        
        m3u_url = extract_m3u_url(link)
        channels_data.append({
            'name': channel_name,
            'url': link,
            'm3u_url': m3u_url
        })
        
        # Her 5 kanalda bir 3 saniye bekle (site koruması için)
        if (i + 1) % 5 == 0:
            time.sleep(3)
    
    print(f"Toplam {len(channels_data)} kanal işlendi.")
    print(f"M3U URL'si bulunan kanal sayısı: {sum(1 for c in channels_data if c['m3u_url'])}")
    
    # Sadece m3u_url'si olan kanalları kaydet
    valid_channels = [c for c in channels_data if c['m3u_url']]
    
    create_m3u_file(valid_channels, output_file)
    print(f"M3U dosyası oluşturuldu: {output_file}")
    
    # Güncellenme bilgisi için JSON dosyası
    metadata = {
        'last_updated': datetime.now().isoformat(),
        'channel_count': len(channels_data),
        'valid_channels': len(valid_channels),
        'channels': [{'name': c['name'], 'url': c['url']} for c in valid_channels]
    }
    
    with open('metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print("metadata.json dosyası oluşturuldu.")

if __name__ == "__main__":
    main() 