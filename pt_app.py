import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
st.set_page_config(page_title="PT Levent Hoca", layout="wide", page_icon="💪")

# --- MODERN PASTEL MAVİ TASARIM (CSS) ---
st.markdown("""
<style>
    /* GENEL SAYFA ARKAPLANI */
    .stApp {
        background-color: #F4F7F6; /* Çok açık gri-mavi */
    }

    /* SIDEBAR (YAN MENÜ) */
    [data-testid="stSidebar"] {
        background-color: #2C3E50; /* Koyu Lacivert */
    }
    [data-testid="stSidebar"] * {
        color: #ecf0f1 !important; /* Sidebar yazıları açık renk */
    }

    /* KART YAPISI */
    div[data-testid="column"] {
        padding: 5px !important;
    }
    
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: white;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); /* Hafif gölge */
        padding: 0px !important; /* İç boşluğu sıfırla (Header için) */
        overflow: hidden;
    }

    /* KART BAŞLIĞI (İSİM ALANI) */
    .card-header {
        background-color: #3498DB; /* Pastel Mavi */
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 14px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
    }
    
    /* BAKİYE ALANI */
    .stat-box {
        padding: 15px 10px 5px 10px;
        text-align: center;
    }
    .stat-number {
        font-size: 32px;
        font-weight: 800;
        color: #2C3E50;
        line-height: 1;
    }
    .stat-label {
        font-size: 12px;
        color: #7f8c8d;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* SON DERS TARİHİ */
    .last-date {
        font-size: 11px;
        color: #95a5a6;
        text-align: center;
        margin-bottom: 15px;
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 5px;
    }

    /* BUTONLAR */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
        padding: 0.5rem 1rem;
        border: none;
        transition: all 0.2s;
    }

    /* DÜŞ BUTONU (KIRMIZI) */
    button[kind="primary"] {
        background-color: #E74C3C !important; /* Pastel Kırmızı */
        color: white !important;
    }
    button[kind="primary"]:hover {
        background-color: #c0392b !important;
    }

    /* İPTAL BUTONU (GRİ) */
    button[kind="secondary"] {
        background-color: #BDC3C7 !important; /* Pastel Gri */
        color: #2C3E50 !important;
    }
    button[kind="secondary"]:hover {
        background-color: #95a5a6 !important;
    }
    
    /* NOTLAR */
    .notes {
        font-size: 11px;
        color: #e67e22; /* Turuncu uyarı */
        text-align: center;
        margin-top: -10px;
        margin-bottom: 10px;
        font-style: italic;
    }

</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS BAĞLANTISI ---
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("PT_Takip_Sistemi")
    return sheet

# --- TARİH DÜZELTİCİ ---
def tarihleri_zorla_cevir(df, kolon_adi):
    df[kolon_adi] = df[kolon_adi].astype(str).str.strip()
    df["tarih_dt"] = pd.to_datetime(df[kolon_adi], dayfirst=True, format="mixed", errors='coerce')
    if df["tarih_dt"].isnull().all():
         df["tarih_dt"] = pd.to_datetime(df[kolon_adi], errors='coerce')
    return df

# --- VERİ ÇEKME ---
def veri_getir():
    try:
        sh = baglanti_kur()
        try: ws_ogrenci = sh.worksheet("Ogrenciler")
        except: ws_ogrenci = sh.add_worksheet(title="Ogrenciler", rows="100", cols="5"); ws_ogrenci.append_row(["isim", "bakiye", "notlar", "durum", "son_guncelleme"])
        try: ws_log = sh.worksheet("Loglar")
        except: ws_log = sh.add_worksheet(title="Loglar", rows="1000", cols="4"); ws_log.append_row(["tarih", "ogrenci", "islem", "detay"])
        try: ws_olcum = sh.worksheet("Olcumler")
        except: ws_olcum = sh.add_worksheet(title="Olcumler", rows="1000", cols="5"); ws_olcum.append_row(["ogrenci", "tarih", "kilo", "yag", "bel"])

        df_students = pd.DataFrame(ws_ogrenci.get_all_records()).astype(str)
        df_logs = pd.DataFrame(ws_log.get_all_records()).astype(str)
        df_measure = pd.DataFrame(ws_olcum.get_all_records())
        df_students["bakiye"] = pd.to_numeric(df_students["bakiye"], errors='coerce').fillna(0).astype(int)

        return sh, df_students, df_logs, df_measure
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, None, None

# --- ANA PROGRAM ---
sh, df_ogrenci, df_log, df_olcum = veri_getir()

if sh:
    # YAN MENÜ
    with st.sidebar:
        st.markdown("### 💪 PT KONTROL")
        menu = st.radio("Menü", ["Ana Ekran", "Öğrenci Ekle/Düzenle", "Vücut Ölçümleri", "Raporlar"])
        if st.button("🔄 Verileri Yenile"):
            st.cache_data.clear()
            st.rerun()

    # === 1. ANA EKRAN ===
    if menu == "Ana Ekran":
        st.markdown("### 📋 Öğrenci Listesi")
        
        c1, c2 = st.columns([3, 1])
        arama = c1.text_input("🔍 İsim Ara...")
        filtre = c2.selectbox("Filtre", ["Aktif", "Pasif", "Tümü"])
        
        # Son Dersleri Hesapla
        son_dersler = {}
        if not df_log.empty:
            df_log = tarihleri_zorla_cevir(df_log, "tarih")
            sadece_dersler = df_log[df_log["islem"].str.strip() == "Ders Yapıldı"].dropna(subset=["tarih_dt"])
            sadece_dersler = sadece_dersler.sort_values(by="tarih_dt", ascending=False)
            for _, row_log in sadece_dersler.iterrows():
                if row_log["ogrenci"] not in son_dersler:
                    son_dersler[row_log["ogrenci"]] = row_log["tarih_dt"].strftime("%d.%m.%Y")

        if not df_ogrenci.empty:
            mask = pd.Series([True] * len(df_ogrenci))
            if filtre == "Aktif": mask = mask & (df_ogrenci["durum"] == "active")
            if filtre == "Pasif": mask = mask & (df_ogrenci["durum"] == "passive")
            if arama: mask = mask & (df_ogrenci["isim"].str.contains(arama, case=False))
            
            filtrelenmis = df_ogrenci[mask]
            
            # 4 SÜTUNLU TASARIM
            cols = st.columns(4)
            
            for idx, row in filtrelenmis.iterrows():
                col = cols[idx % 4]
                with col:
                    with st.container(border=True):
                        # --- ÖZEL HTML KART TASARIMI ---
                        isim = row["isim"]
                        bakiye = row["bakiye"]
                        son_tarih = son_dersler.get(isim, "-")
                        
                        # 1. MAVİ BAŞLIK
                        st.markdown(f"<div class='card-header'>{isim}</div>", unsafe_allow_html=True)
                        
                        # 2. BAKİYE
                        st.markdown(f"""
                        <div class='stat-box'>
                            <div class='stat-label'>KALAN DERS</div>
                            <div class='stat-number'>{bakiye}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 3. NOTLAR (Varsa)
                        if row["notlar"] and row["notlar"] != "nan":
                            st.markdown(f"<div class='notes'>⚠️ {row['notlar']}</div>", unsafe_allow_html=True)

                        # 4. SON DERS
                        st.markdown(f"<div class='last-date'>📅 Son: {son_tarih}</div>", unsafe_allow_html=True)
                        
                        # 5. BUTONLAR
                        b1, b2 = st.columns(2)
                        
                        if b1.button("DÜŞ 📉", key=f"d_{idx}", type="primary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim)
                            ws.update_cell(cell.row, 2, int(bakiye - 1))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, isim, "Ders Yapıldı", ""])
                            st.toast(f"{isim}: Ders düşüldü!")
                            time.sleep(0.5)
                            st.rerun()
                        
                        if b2.button("İPTAL ↩️", key=f"i_{idx}", type="secondary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim)
                            ws.update_cell(cell.row, 2, int(bakiye + 1))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, isim, "Ders İptal/İade", "Düzeltme"])
                            st.toast("İşlem geri alındı.")
                            time.sleep(0.5)
                            st.rerun()

    # === 2. ÖĞRENCİ YÖNETİMİ ===
    elif menu == "Öğrenci Ekle/Düzenle":
        st.header("⚙️ Öğrenci Yönetimi")
        t1, t2 = st.tabs(["Yeni Kayıt", "Düzenle / Paket Yükle"])
        
        with t1:
            with st.form("ekle"):
                ad = st.text_input("Ad Soyad")
                bas = st.number_input("Paket Başlangıç", value=10)
                nt = st.text_area("Notlar")
                if st.form_submit_button("Kaydet"):
                    zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                    sh.worksheet("Ogrenciler").append_row([ad, bas, nt, "active", zaman])
                    st.success("Öğrenci Eklendi!")
                    time.sleep(1)
                    st.rerun()
                    
        with t2:
            if not df_ogrenci.empty:
                sec = st.selectbox("Öğrenci Seç", df_ogrenci["isim"].tolist())
                sec_veri = df_ogrenci[df_ogrenci["isim"] == sec].iloc[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Paket Yükle")
                    ek = st.number_input("Eklenecek Ders Sayısı", value=10)
                    if st.button("Paketi Tanımla"):
                        ws = sh.worksheet("Ogrenciler")
                        cell = ws.find(sec)
                        ws.update_cell(cell.row, 2, int(sec_veri["bakiye"] + ek))
                        zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                        sh.worksheet("Loglar").append_row([zaman, sec, "Paket Yüklendi", f"{ek} ders"])
                        st.success("Paket Yüklendi!")
                        st.rerun()
                
                st.divider()
                st.subheader(f"📜 {sec} - Ders Geçmişi")
                if not df_log.empty:
                    df_log = tarihleri_zorla_cevir(df_log, "tarih")
                    kisi_log = df_log[df_log["ogrenci"] == sec].copy()
                    
                    if not kisi_log.empty:
                        kisi_log = kisi_log.sort_values(by="tarih_dt", ascending=False)
                        st.dataframe(kisi_log[["tarih", "islem", "detay"]], use_container_width=True)
                    else:
                        st.info("Bu öğrenciye ait geçmiş kayıt bulunamadı.")

    # === 3. ÖLÇÜMLER ===
    elif menu == "Vücut Ölçümleri":
        st.header("📏 Vücut Ölçümleri")
        o_sec = None
        if df_ogrenci.empty:
            st.warning("Henüz öğrenci listeniz boş.")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                o_sec = st.selectbox("Öğrenci Seçiniz", df_ogrenci["isim"].tolist())
                with st.form("olcum"):
                    st.write("Yeni Ölçüm Gir")
                    trh = st.date_input("Tarih")
                    kg = st.number_input("Kilo (kg)")
                    yg = st.number_input("Yağ Oranı (%)")
                    bl = st.number_input("Bel (cm)")
                    if st.form_submit_button("Kaydet"):
                        trh_str = trh.strftime("%Y-%m-%d")
                        sh.worksheet("Olcumler").append_row([o_sec, trh_str, kg, yg, bl])
                        st.success("Ölçüm Kaydedildi!")
                        time.sleep(1)
                        st.rerun()
            
            with c2:
                if o_sec and not df_olcum.empty:
                    kisi_olcum = df_olcum[df_olcum["ogrenci"] == o_sec].copy()
                    if not kisi_olcum.empty:
                        st.write(f"📈 **{o_sec} - Gelişim Grafiği**")
                        kisi_olcum["kilo"] = pd.to_numeric(kisi_olcum["kilo"], errors='coerce')
                        st.line_chart(kisi_olcum, x="tarih", y="kilo")
                        st.dataframe(kisi_olcum, use_container_width=True)
                    else:
                        st.info("Henüz veri yok.")

    # === 4. RAPORLAR ===
    elif menu == "Raporlar":
        st.header("📊 Genel Raporlar")
        if not df_log.empty:
            df_log = tarihleri_zorla_cevir(df_log, "tarih")
            df_log = df_log.dropna(subset=["tarih_dt"])
            df_log["Ay"] = df_log["tarih_dt"].dt.strftime("%Y-%m")
            
            dersler = df_log[df_log["islem"].str.strip() == "Ders Yapıldı"]
            
            st.subheader("Aylık Ders Yoğunluğu")
            st.bar_chart(dersler["Ay"].value_counts())
            
            st.divider()
            st.subheader("Tüm İşlem Geçmişi")
            st.dataframe(df_log[["tarih", "ogrenci", "islem"]].sort_values("tarih_dt", ascending=False), use_container_width=True)
