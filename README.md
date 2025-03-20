# Türk ve Azerbaycan TV Kanalları M3U Listesi

Bu repo, [canlitv.me](https://www.canlitv.me/hd1) sitesinden Türk ve Azerbaycan TV kanallarının M3U linklerini otomatik olarak derleyen bir sistem içerir.

## Özellikler

- Her gün otomatik olarak güncellenen kanal listesi
- Türk ve Azerbaycan kanallarının m3u bağlantıları
- GitHub Actions ile tam otomatik işleyiş

## Kullanım

Kanalları IPTV uygulamanızda kullanmak için aşağıdaki bağlantıyı ekleyin:

```
https://raw.githubusercontent.com/KULLANICI_ADI/REPO_ADI/main/kanallar.m3u
```

*Not: Yukarıdaki bağlantıyı, kendi GitHub kullanıcı adınız ve repo adınız ile değiştirin.*

## Lokal Kullanım

Bu projeyi yerel bilgisayarınızda çalıştırmak için:

1. Repoyu klonlayın
2. Gereksinimleri yükleyin: `pip install -r requirements.txt`
3. Scripti çalıştırın: `python channel_scraper.py`

## Lisans

Bu proje açık kaynaklıdır ve özgürce kullanılabilir.

## Güncelleme Geçmişi

Güncellemeler hakkında detaylı bilgi için `metadata.json` dosyasına bakabilirsiniz. 