from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------
# Konfigurasi aplikasi
# ---------------------------------------------------------
st.set_page_config(
    page_title="E-Commerce Analytics",
    page_icon="🛒",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

START_DATE = pd.Timestamp("2017-01-01")
END_DATE_EXCLUSIVE = pd.Timestamp("2018-09-01")
SNAPSHOT_DATE = END_DATE_EXCLUSIVE

REQUIRED_FILES = [
    "orders_dataset.csv",
    "order_items_dataset.csv",
    "products_dataset.csv",
    "product_category_name_translation.csv",
    "order_reviews_dataset.csv",
    "customers_dataset.csv",
]


# ---------------------------------------------------------
# Fungsi pemuatan dan pengolahan data
# ---------------------------------------------------------
@st.cache_data
def load_data(data_dir: str):
    data_path = Path(data_dir)
    missing_files = [name for name in REQUIRED_FILES if not (data_path / name).exists()]
    if missing_files:
        raise FileNotFoundError(
            "File berikut belum ditemukan di folder data/: "
            + ", ".join(missing_files)
        )

    orders = pd.read_csv(data_path / "orders_dataset.csv")
    items = pd.read_csv(data_path / "order_items_dataset.csv")
    products = pd.read_csv(data_path / "products_dataset.csv")
    translation = pd.read_csv(data_path / "product_category_name_translation.csv")
    reviews = pd.read_csv(data_path / "order_reviews_dataset.csv")
    customers = pd.read_csv(data_path / "customers_dataset.csv")

    date_cols = [
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")

    items["shipping_limit_date"] = pd.to_datetime(
        items["shipping_limit_date"], errors="coerce"
    )

    return orders, items, products, translation, reviews, customers


def build_analysis(orders, items, products, translation, reviews, customers):
    # Analisis dibatasi pada pesanan delivered dalam periode proyek.
    period_orders = orders[
        (orders["order_status"] == "delivered")
        & (orders["order_purchase_timestamp"] >= START_DATE)
        & (orders["order_purchase_timestamp"] < END_DATE_EXCLUSIVE)
    ].copy()

    # -----------------------------------------------------
    # Penjualan per kategori
    # -----------------------------------------------------
    sales = (
        items.merge(
            period_orders[["order_id", "order_purchase_timestamp"]],
            on="order_id",
            how="inner",
        )
        .merge(
            products[["product_id", "product_category_name"]],
            on="product_id",
            how="left",
        )
        .merge(translation, on="product_category_name", how="left")
    )

    sales["product_category_name_english"] = (
        sales["product_category_name_english"].fillna("Unknown")
    )

    category_summary = (
        sales.groupby("product_category_name_english", as_index=False)
        .agg(
            total_items=("order_item_id", "count"),
            total_revenue=("price", "sum"),
        )
        .sort_values("total_revenue", ascending=False)
    )

    sales["month"] = (
        sales["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp()
    )
    monthly_sales = (
        sales.groupby(
            ["month", "product_category_name_english"], as_index=False
        )["price"]
        .sum()
        .rename(columns={"price": "revenue"})
    )

    # -----------------------------------------------------
    # Pengiriman dan ulasan
    # -----------------------------------------------------
    delivery = period_orders.dropna(
        subset=[
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ]
    ).copy()

    delivery["delivery_status"] = np.where(
        delivery["order_delivered_customer_date"]
        > delivery["order_estimated_delivery_date"],
        "Late",
        "On Time",
    )

    delivery_summary = (
        delivery["delivery_status"]
        .value_counts()
        .rename_axis("delivery_status")
        .reset_index(name="total_orders")
    )
    delivery_summary["percentage"] = (
        delivery_summary["total_orders"]
        / delivery_summary["total_orders"].sum()
        * 100
    )

    reviews_per_order = (
        reviews.groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"))
    )
    delivery_reviews = delivery.merge(
        reviews_per_order, on="order_id", how="inner"
    )
    review_summary = (
        delivery_reviews.groupby("delivery_status", as_index=False)
        .agg(
            total_reviewed_orders=("order_id", "nunique"),
            average_review=("review_score", "mean"),
        )
    )

    # -----------------------------------------------------
    # RFM: sesuai definisi dan periode notebook
    # -----------------------------------------------------
    rfm_orders = period_orders.merge(
        customers[["customer_id", "customer_unique_id"]],
        on="customer_id",
        how="left",
    )

    order_revenue = (
        items.groupby("order_id", as_index=False)
        .agg(order_monetary=("price", "sum"))
    )
    rfm_orders = rfm_orders.merge(
        order_revenue, on="order_id", how="inner"
    )

    rfm = (
        rfm_orders.groupby("customer_unique_id", as_index=False)
        .agg(
            last_purchase=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            monetary=("order_monetary", "sum"),
        )
    )
    rfm["recency"] = (SNAPSHOT_DATE - rfm["last_purchase"]).dt.days

    # Mengikuti scoring notebook agar hasil dashboard konsisten.
    # Catatan: rank(method="first") dapat membedakan nilai yang sama.
    rfm["R_score"] = pd.qcut(
        rfm["recency"].rank(method="first"),
        5,
        labels=[5, 4, 3, 2, 1],
    ).astype(int)

    rfm["M_score"] = pd.qcut(
        rfm["monetary"].rank(method="first"),
        5,
        labels=[1, 2, 3, 4, 5],
    ).astype(int)

    def frequency_score(value):
        if value == 1:
            return 1
        elif value == 2:
            return 2
        elif value == 3:
            return 3
        elif value <= 5:
            return 4
        return 5

    rfm["F_score"] = rfm["frequency"].apply(frequency_score)
    rfm["RFM_score"] = (
        rfm["R_score"].astype(str)
        + rfm["F_score"].astype(str)
        + rfm["M_score"].astype(str)
    )

    def segment_customer(row):
        if (
            row["R_score"] >= 4
            and row["F_score"] >= 3
            and row["M_score"] >= 3
        ):
            return "Best Customers"
        elif row["F_score"] >= 2 and row["R_score"] >= 3:
            return "Loyal Customers"
        elif (
            row["R_score"] >= 4
            and row["F_score"] == 1
            and row["M_score"] >= 3
        ):
            return "Potential Customers"
        elif row["R_score"] <= 2 and row["F_score"] >= 2:
            return "At Risk Customers"
        return "Others"

    rfm["customer_segment"] = rfm.apply(segment_customer, axis=1)

    segment_summary = (
        rfm.groupby("customer_segment", as_index=False)
        .agg(
            total_customers=("customer_unique_id", "count"),
            total_revenue=("monetary", "sum"),
            average_monetary=("monetary", "mean"),
        )
    )
    segment_summary["customer_percentage"] = (
        segment_summary["total_customers"]
        / segment_summary["total_customers"].sum()
        * 100
    )
    segment_summary = segment_summary.sort_values(
        "total_customers", ascending=False
    )

    return (
        sales,
        category_summary,
        monthly_sales,
        delivery,
        delivery_summary,
        review_summary,
        rfm,
        segment_summary,
    )


# ---------------------------------------------------------
# Tampilan dashboard
# ---------------------------------------------------------
st.title("🛒 E-Commerce Analytics")
st.caption(
    "Analisis transaksi Olist | Periode Januari 2017–Agustus 2018 "
    "| Pesanan delivered"
)

with st.sidebar:
    st.header("Tentang Dashboard")
    st.write(
        "Dashboard ini menyajikan performa penjualan, ketepatan pengiriman, "
        "ulasan pelanggan, dan segmentasi RFM."
    )
    st.markdown("**Periode analisis**")
    st.write("1 Januari 2017 – 31 Agustus 2018")
    st.markdown("**Definisi revenue**")
    st.write("Total `price` produk; tidak termasuk ongkos kirim.")
    st.markdown("**Sumber data**")
    st.write("Olist Brazilian E-Commerce Public Dataset")

try:
    data = load_data(str(DATA_DIR))
    (
        sales,
        category_summary,
        monthly_sales,
        delivery,
        delivery_summary,
        review_summary,
        rfm,
        segment_summary,
    ) = build_analysis(*data)
except Exception as error:
    st.error(f"Data belum dapat dimuat: {error}")
    st.info(
        "Pastikan enam file CSV yang dibutuhkan sudah diletakkan di folder "
        "`data/` yang sejajar dengan file `app.py`. Lihat README.txt."
    )
    st.stop()

# KPI utama
total_revenue = category_summary["total_revenue"].sum()
total_items = category_summary["total_items"].sum()
on_time_pct = (
    delivery["delivery_status"].eq("On Time").mean() * 100
    if len(delivery) else 0
)
late_pct = (
    delivery["delivery_status"].eq("Late").mean() * 100
    if len(delivery) else 0
)
repeat_pct = (rfm["frequency"].gt(1).mean() * 100) if len(rfm) else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"R$ {total_revenue:,.2f}")
k2.metric("Item Terjual", f"{total_items:,.0f}")
k3.metric("Pesanan Tepat Waktu", f"{on_time_pct:.2f}%")
k4.metric("Pelanggan Repeat", f"{repeat_pct:.2f}%")

tab_sales, tab_delivery, tab_rfm = st.tabs(
    ["📈 Penjualan", "🚚 Pengiriman & Ulasan", "👥 RFM Pelanggan"]
)

# ---------------------------------------------------------
# Tab 1: Penjualan
# ---------------------------------------------------------
with tab_sales:
    st.subheader("Performa Penjualan per Kategori")

    categories = category_summary["product_category_name_english"].tolist()
    default_categories = categories[:5]
    selected_categories = st.multiselect(
        "Pilih kategori untuk melihat tren revenue bulanan",
        options=categories,
        default=default_categories,
    )

    if selected_categories:
        monthly_filtered = monthly_sales[
            monthly_sales["product_category_name_english"].isin(
                selected_categories
            )
        ]
        fig_monthly = px.line(
            monthly_filtered,
            x="month",
            y="revenue",
            color="product_category_name_english",
            markers=True,
            title="Tren Revenue Bulanan",
            labels={
                "month": "Bulan",
                "revenue": "Revenue (R$)",
                "product_category_name_english": "Kategori",
            },
        )
        fig_monthly.update_layout(legend_title_text="Kategori")
        st.plotly_chart(fig_monthly, use_container_width=True)
    else:
        st.info("Pilih minimal satu kategori untuk menampilkan tren.")

    top_n = st.slider("Jumlah kategori yang ditampilkan", 5, 15, 10)
    top_categories = category_summary.head(top_n).sort_values("total_revenue")
    fig_category = px.bar(
        top_categories,
        x="total_revenue",
        y="product_category_name_english",
        orientation="h",
        text_auto=",.0f",
        title=f"{top_n} Kategori dengan Revenue Tertinggi",
        labels={
            "total_revenue": "Revenue (R$)",
            "product_category_name_english": "Kategori",
        },
    )
    st.plotly_chart(fig_category, use_container_width=True)

    st.markdown("**Ringkasan kategori produk**")
    display_category = category_summary.copy()
    display_category["total_revenue"] = display_category[
        "total_revenue"
    ].map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(display_category, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# Tab 2: Pengiriman dan ulasan
# ---------------------------------------------------------
with tab_delivery:
    st.subheader("Ketepatan Pengiriman")

    d1, d2 = st.columns(2)
    with d1:
        fig_delivery = px.pie(
            delivery_summary,
            names="delivery_status",
            values="total_orders",
            hole=0.45,
            title="Proporsi Pesanan Tepat Waktu dan Terlambat",
        )
        st.plotly_chart(fig_delivery, use_container_width=True)

    with d2:
        fig_review = px.bar(
            review_summary,
            x="delivery_status",
            y="average_review",
            text_auto=".2f",
            title="Rata-rata Skor Ulasan berdasarkan Status Pengiriman",
            labels={
                "delivery_status": "Status Pengiriman",
                "average_review": "Rata-rata Skor Ulasan",
            },
        )
        fig_review.update_yaxes(range=[0, 5])
        st.plotly_chart(fig_review, use_container_width=True)

    st.markdown("**Ringkasan pengiriman**")
    st.dataframe(
        delivery_summary.round(2), use_container_width=True, hide_index=True
    )
    st.markdown("**Ringkasan ulasan**")
    st.dataframe(
        review_summary.round(2), use_container_width=True, hide_index=True
    )
    st.caption(
        "Perbandingan skor ulasan hanya mencakup pesanan yang memiliki ulasan. "
        "Hubungan antara keterlambatan dan skor ulasan tidak membuktikan sebab-akibat."
    )

# ---------------------------------------------------------
# Tab 3: RFM
# ---------------------------------------------------------
with tab_rfm:
    st.subheader("Segmentasi Pelanggan berdasarkan RFM")
    st.caption(
        "Recency dihitung terhadap 1 September 2018. Frequency dan Monetary "
        "dihitung dari pesanan delivered pada periode analisis."
    )

    r1, r2, r3 = st.columns(3)
    r1.metric("Pelanggan Dianalisis", f"{len(rfm):,}")
    r2.metric("Pelanggan Repeat", f"{(rfm['frequency'] > 1).sum():,}")
    r3.metric("Persentase Repeat", f"{repeat_pct:.2f}%")

    fig_segment = px.bar(
        segment_summary.sort_values("total_customers"),
        x="total_customers",
        y="customer_segment",
        orientation="h",
        text="total_customers",
        title="Jumlah Pelanggan per Segmen",
        labels={
            "total_customers": "Jumlah Pelanggan",
            "customer_segment": "Segmen Pelanggan",
        },
    )
    st.plotly_chart(fig_segment, use_container_width=True)

    fig_monetary = px.bar(
        segment_summary.sort_values("average_monetary"),
        x="average_monetary",
        y="customer_segment",
        orientation="h",
        text_auto=",.2f",
        title="Rata-rata Monetary per Segmen",
        labels={
            "average_monetary": "Rata-rata Monetary (R$)",
            "customer_segment": "Segmen Pelanggan",
        },
    )
    st.plotly_chart(fig_monetary, use_container_width=True)

    st.markdown("**Ringkasan segmen pelanggan**")
    st.dataframe(
        segment_summary.round(2), use_container_width=True, hide_index=True
    )

    st.markdown("**Cari pelanggan berdasarkan segmen (opsional)**")
    segment_options = ["Semua"] + sorted(rfm["customer_segment"].unique().tolist())
    chosen_segment = st.selectbox("Segmen", segment_options)
    customer_view = rfm.copy()
    if chosen_segment != "Semua":
        customer_view = customer_view[
            customer_view["customer_segment"] == chosen_segment
        ]
    customer_view = customer_view[
        [
            "customer_unique_id",
            "recency",
            "frequency",
            "monetary",
            "RFM_score",
            "customer_segment",
        ]
    ].sort_values(["monetary", "recency"], ascending=[False, True])
    st.dataframe(
        customer_view.head(500),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Tabel pelanggan dibatasi hingga 500 baris pertama untuk menjaga "
        "performa tampilan. Identitas pelanggan ditampilkan sebagai ID dataset."
    )

st.divider()
st.caption(
    "Catatan: Revenue menggunakan nilai price tanpa freight_value. "
    "RFM adalah analisis historis dalam periode yang ditentukan, bukan "
    "prediksi perilaku pelanggan."
)
