import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
st.set_page_config(page_title="PT", layout="wide", page_icon="💪")

# --- MOBİL DOSTU CSS TASARIM ---
st.markdown("""
<style>
    /* Genel sayfa kenar boşluklarını azalt */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }
    
    /* Butonları küçült ve incelt */
    .stButton button {
        width: 100%;
        border-radius: 5px;
        font-weight: bold;
        font-size: 14px !important;
        padding: 0.2rem 0.5rem !important;
        height: auto !important;
        min-height: 0px !important;
    }
    
    /* Kartların içindeki boşlukları al */
    div[data-testid="column"] {
        padding: 0px !important;
    }
    
    /* İsim ve Rakamların boyutunu ayarla */
    h3 {
        font-size: 18px !important;
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }
    
    /* Metrik (Kalan Ders) yazısını küçült */
    div[data-testid="stMetricValue"] {
        font-size: 24px !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 12px !important;
    }
    
    /* Kartın kendisi */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        padding: 10px !important;
        margin-bottom: 5px !important;
    }
    
    /* Küçük notlar */
    .small-text {
        font-size: 12px;
        color: gray;
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

# --- ÖZEL TARİH ÇEVİRİCİ ---
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
        st.error(f"Hata: {e}")
        return None, None, None, None

# --- ANA PROGRAM ---
sh, df_ogrenci, df_log, df_olcum = veri_getir()

if sh:
    # YAN MENÜ
    with st.sidebar:
        st.write("👤 **Levent Hoca**")
        menu = st.radio("Menü", ["Ana Ekran", "Yönetim", "Ölçümler", "Rapor"])
        if st.button("🔄 Yenile"):
            st.cache_data.clear()
            st.rerun()

    # === 1. ANA EKRAN (KOMPAKT) ===
    if menu == "Ana Ekran":
        # Arama ve Filtre yan yana ve sıkışık
        c1, c2 = st.columns([2, 1])
        arama = c1.text_input("🔍", placeholder="Öğrenci Ara")
        filtre = c2.selectbox("", ["Aktif", "Pasif", "Tümü"], label_visibility="collapsed")
        
        # Son Dersleri Bul
        son_dersler = {}
        if not df_log.empty:
            df_log = tarihleri_zorla_cevir(df_log, "tarih")
            sadece_dersler = df_log[df_log["islem"].str.strip() == "Ders Yapıldı"].dropna(subset=["tarih_dt"])
            sadece_dersler = sadece_dersler.sort_values(by="tarih_dt", ascending=False)
            for _, row_log in sadece_dersler.iterrows():
                if row_log["ogrenci"] not in son_dersler:
                    son_dersler[row_log["ogrenci"]] = row_log["tarih_dt"].strftime("%d.%m") # Sadece Gün.Ay

        if not df_ogrenci.empty:
            mask = pd.Series([True] * len(df_ogrenci))
            if filtre == "Aktif": mask = mask & (df_ogrenci["durum"] == "active")
            if filtre == "Pasif": mask = mask & (df_ogrenci["durum"] == "passive")
            if arama: mask = mask & (df_ogrenci["isim"].str.contains(arama, case=False))
            
            filtrelenmis = df_ogrenci[mask]
            
            # 2 Sütunlu Grid (Telefonda daha iyi görünür)
            cols = st.columns(2)
            
            for idx, row in filtrelenmis.iterrows():
                col = cols[idx % 2] # 2 Sütunlu döngü
                with col:
                    with st.container(border=True):
                        # İsim ve Bakiye Yan Yana
                        bakiye = row["bakiye"]
                        isim = row["isim"].split(" ")[0] + " " + (row["isim"].split(" ")[1][0] + "." if len(row["isim"].split(" ")) > 1 else "")
                        # Uzun isimleri kısalt: Levent Hoca -> Levent H.
                        
                        renk = "🟢" if bakiye >= 5 else "🟠" if bakiye > 0 else "🔴"
                        
                        # Üst Bilgi (İsim ve Kalan)
                        st.markdown(f"**{renk} {isim}**")
                        st.markdown(f"<h3 style='text-align:center; color:#333;'>{bakiye}</h3>", unsafe_allow_html=True)
                        
                        # Alt Bilgi (Son Ders)
                        son_tarih = son_dersler.get(row["isim"], "-")
                        st.markdown(f"<p class='small-text' style='text-align:center; margin:0;'>📅 {son_tarih}</p>", unsafe_allow_html=True)
                        
                        # Butonlar Yan Yana (Küçük)
                        b1, b2 = st.columns(2)
                        if b1.button("DÜŞ", key=f"d_{idx}", type="primary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(row["isim"])
                            if cell:
                                ws.update_cell(cell.row, 2, int(bakiye - 1))
                                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                                sh.worksheet("Loglar").append_row([zaman, row["isim"], "Ders Yapıldı", ""])
                                st.toast(f"Düşüldü: {isim}")
                                time.sleep(0.5)
                                st.rerun()
                        
                        if b2.button("İPTAL", key=f"i_{idx}"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(row["isim"])
                            if cell:
                                ws.update_cell(cell.row, 2, int(bakiye + 1))
                                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                                sh.worksheet("Loglar").append_row([zaman, row["isim"], "Ders İptal/İade", "Düzeltme"])
                                st.toast("Geri alındı.")
                                time.sleep(0.5)
                                st.rerun()

    # === 2. YÖNETİM ===
    elif menu == "Yönetim":
        st.header("⚙️ Yönetim")
        t1, t2 = st.tabs(["Yeni", "Düzenle"])
        with t1:
            with st.form("ekle"):
                ad = st.text_input("Ad Soyad")
                bas = st.number_input("Paket", value=10)
                if st.form_submit_button("Kaydet"):
                    zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                    sh.worksheet("Ogrenciler").append_row([ad, bas, "", "active", zaman])
                    st.success("OK")
                    st.rerun()
        with t2:
            if not df_ogrenci.empty:
                sec = st.selectbox("Seç", df_ogrenci["isim"].tolist())
                sec_veri = df_ogrenci[df_ogrenci["isim"] == sec].iloc[0]
                ek = st.number_input("Ekle", value=10)
                if st.button("Yükle"):
                    ws = sh.worksheet("Ogrenciler")
                    cell = ws.find(sec)
                    if cell:
                        ws.update_cell(cell.row, 2, int(sec_veri["bakiye"] + ek))
                        zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                        sh.worksheet("Loglar").append_row([zaman, sec, "Paket Yüklendi", f"{ek} ders"])
                        st.success("Yüklendi")
                        st.rerun()

    # === 3. ÖLÇÜMLER ===
    elif menu == "Ölçümler":
        st.subheader("📏 Ölçüm")
        o_sec = None
        if not df_ogrenci.empty:
            o_sec = st.selectbox("Öğrenci", df_ogrenci["isim"].tolist())
            with st.form("olcum"):
                c1, c2 = st.columns(2)
                kg = c1.number_input("Kilo")
                yg = c2.number_input("Yağ")
                bl = st.number_input("Bel")
                if st.form_submit_button("Kaydet"):
                    trh = datetime.now().strftime("%Y-%m-%d")
                    sh.worksheet("Olcumler").append_row([o_sec, trh, kg, yg, bl])
                    st.success("OK")
                    st.rerun()
            if o_sec and not df_olcum.empty:
                kisi_olcum = df_olcum[df_olcum["ogrenci"] == o_sec].copy()
                if not kisi_olcum.empty:
                    kisi_olcum["kilo"] = pd.to_numeric(kisi_olcum["kilo"], errors='coerce')
                    st.line_chart(kisi_olcum, x="tarih", y="kilo")

    # === 4. RAPOR ===
    elif menu == "Rapor":
        if not df_log.empty:
            df_log = tarihleri_zorla_cevir(df_log, "tarih")
            st.dataframe(df_log[["tarih", "ogrenci", "islem"]].sort_values("tarih_dt", ascending=False), use_container_width=True)
