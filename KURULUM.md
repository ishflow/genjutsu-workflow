# Bu kopya

`sirioberati/Genjustsu-Open-Source-Workflow` deposunun (MIT) değiştirilmiş kopyası. Kaynak depo `upstream` adıyla bağlı.
Üstüne eklenenler:

| Ek | Ne yapar | Belge |
|---|---|---|
| Magnific sağlayıcısı | Üretim Enhancor yerine Magnific'in Seedance 2.5 Pro ucuna gider | `docs/MAGNIFIC-API.md` |
| Yerel hazırlık | Ses ayrıştırma, derinlik ve maske Replicate yerine bu makinede çalışır | `docs/LOCAL-MODELS.md` |
| Kırpma | Arayüzde ve komut satırında videonun 4–30 saniyelik bir kısmını seçme | `trim.py` |
| Hata mesajları | Yüz izleme boşlukları ve 30 saniye sınırı için anlaşılır açıklama | `face_mesh.py`, `pipeline.py` |

## Yeni makinede kurulum

```sh
brew install rubberband ffmpeg            # cloudflared yalnız Enhancor için gerekir
PYTHON=python3.14 bash setup.sh           # ana ortam (.venv)
uv venv --python 3.12 .venv-face && uv pip install --python .venv-face/bin/python mediapipe==1.1.0 av==19.0.1 pillow==12.3.0 numpy==2.5.3
bash setup-local-models.sh                # yerel modeller (.venv-local + models/, yaklaşık 2 GB)
```

`.env` (git'e girmez; içinde gizli değer yok, anahtar başka dosyadan okunur):

```
LOCAL_PREPARATION=1
SEEDANCE_PROVIDER=magnific
MAGNIFIC_KEY_FILE=<anahtarların durduğu KEY=değer dosyasının yolu>
MAGNIFIC_KEY_NAME=<o dosyadaki satırın adı>
MAGNIFIC_DRAFT_RESOLUTION=720p
```

## Çalıştırma ve kontrol

```sh
bash start.command                                   # http://127.0.0.1:8770
.venv/bin/python doctor.py --require-keys --mesh     # kurulum kontrolü
.venv/bin/python -m unittest discover -s tests       # 37 test
.venv/bin/python workflow.py prepare video.mp4 --mode depth --from 2 --to 8
```

## Bilinen sınırlar (2026-10-12)

- Hazırlık ücretsiz ve yerel; üretim ücretli. Kaynak videolu istek çıktı + kaynak süresi kadar faturalanır (30 sn tavan).
- 1080p, taslağın yükseltmesi değil, aynı istekle yeni bir üretimdir; henüz denenmedi.
- 6 saniyelik kesitte iki kişi de değişti; 30 saniyelik çok sahneli videoda ikinci kişi değişmedi. Uzun videoyu sahnelere bölmek daha güvenli görünüyor.
- Yerel maske 30 saniyelik klipte 15–20 dakika sürer (M5).
- `runs/` (yüklenen videolar, referans görseller, sonuçlar) ve `models/` git'e girmez.
