# Brazilian E-Commerce Data Analysis (Olist)

Proyek ini berisi notebook analisis data dan dashboard interaktif menggunakan Streamlit berdasarkan Brazilian E-Commerce Public Dataset (Olist).

## Struktur Folder

Pastikan struktur folder proyek kurang lebih seperti berikut:

```text
submission/
│
├── .venv/
│
├── dashboard/
│   └── dashboard.py
│
├── data/
│   ├── customers_dataset.csv
│   ├── geolocation_dataset.csv
│   ├── order_items_dataset.csv
│   ├── order_payments_dataset.csv
│   ├── order_reviews_dataset.csv
│   ├── orders_dataset.csv
│   ├── product_category_name_translation.csv
│   ├── products_dataset.csv
│   └── sellers_dataset.csv
│
├── notebook.ipynb
├── README.md
├── requirements.txt
└── url.txt
```

Dashboard versi ini membutuhkan enam file CSV: `orders_dataset.csv`, `order_items_dataset.csv`, `products_dataset.csv`, `product_category_name_translation.csv`, `order_reviews_dataset.csv`, dan `customers_dataset.csv`. File `sellers_dataset.csv` dapat tetap disimpan untuk kebutuhan analisis notebook, tetapi tidak digunakan oleh dashboard saat ini.

## Persiapan Dataset

1. Unduh dan ekstrak E-Commerce Public Dataset.
2. Buat folder bernama `data` di dalam folder proyek.
3. Letakkan file CSV dataset ke dalam folder `data`.
4. Pastikan nama file dan struktur folder sesuai dengan contoh di atas.

## Setup Environment - Anaconda

Buka Anaconda Prompt atau terminal, lalu jalankan:

```bash
conda create --name olist-analysis python=3.11
conda activate olist-analysis
pip install -r requirements.txt
```

## Setup Environment - Shell/Terminal (venv)

Jalankan perintah berikut dari folder utama proyek.

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Setup Environment - Pipenv (Opsional)

Jika menggunakan Pipenv, jalankan:

```bash
pip install pipenv
pipenv --python 3.11
pipenv install -r requirements.txt
pipenv shell
```

## Menjalankan Notebook

Pastikan environment sudah aktif, kemudian jalankan:

```bash
jupyter notebook
```

Buka file `Proyek_Analisis_Data.ipynb` melalui browser/Jupyter. Jika notebook menggunakan path relatif, pastikan notebook dijalankan dari folder utama proyek dan data berada di folder `data`.

## Menjalankan Dashboard Streamlit

Pastikan environment sudah aktif dan file CSV dashboard sudah tersedia di folder `data/`. Dari folder utama proyek, jalankan:

```bash
streamlit run app.py
```

Dashboard akan terbuka secara lokal di browser. Alamat default Streamlit adalah:

```text
http://localhost:8501
```

Untuk menghentikan dashboard, tekan `Ctrl + C` pada terminal.

## Fitur Dashboard

Dashboard terdiri dari tiga bagian:

1. **Penjualan**: tren revenue bulanan dan perbandingan revenue kategori produk.
2. **Pengiriman & Ulasan**: proporsi pesanan tepat waktu/terlambat serta rata-rata skor ulasan berdasarkan status pengiriman.
3. **RFM Pelanggan**: ringkasan segmentasi pelanggan berdasarkan Recency, Frequency, dan Monetary.

## Catatan Analisis

- Periode analisis transaksi: 1 Januari 2017 sampai 31 Agustus 2018.
- Analisis penjualan dan RFM menggunakan pesanan dengan status `delivered`.
- Revenue dihitung berdasarkan kolom `price` dan tidak memasukkan `freight_value`.
- Tanggal acuan RFM adalah 1 September 2018.
- Perbandingan skor ulasan hanya menggunakan pesanan yang memiliki data ulasan. Hubungan antara keterlambatan pengiriman dan skor ulasan tidak dapat langsung diartikan sebagai hubungan sebab-akibat.
