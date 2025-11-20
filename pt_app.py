import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time
import json

# --- AYARLAR ---
st.set_page_config(page_title="PT Levent Hoca", layout="wide", page_icon="💪")

# --- CSS TASARIM ---
st.markdown("""
<style>
    .stButton button {width: 100%; border-radius: 8px; font-weight: bold;}
    div[data-testid="stMetricValue"] {font-size: 36px;}
</style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS BAĞLANTISI ---
def baglanti_kur():
    # Streamlit Secrets'tan anahtarı al
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("PT_Takip_Sistemi")
    return sheet

# --- VERİ ÇEKME ---
def veri_getir():
    try:
        sh = baglanti_kur()
        
        try:
            ws_ogrenci = sh.worksheet("Ogrenciler")
        except:
            ws_ogrenci = sh.add_worksheet(title="Ogrenciler", rows="100", cols="5")
            ws_ogrenci.append_row(["isim", "bakiye", "notlar", "durum", "son_guncelleme"])

        try:
            ws_log = sh.worksheet("Loglar")
        except:
            ws_log = sh.add_worksheet(title="Loglar", rows="1000", cols="4")
            ws_log.append_row(["tarih", "ogrenci", "islem", "detay"])

        try:
            ws_olcum = sh.worksheet("Olcumler")
        except:
            ws_olcum = sh.add_worksheet(title="Olcumler", rows="1000", cols="5")
            ws_olcum.append_row(["ogrenci", "tarih", "kilo", "yag", "bel"])

        # Verileri oku ve DataFrame'e çevir
        df_students = pd.DataFrame(ws_ogrenci.get_all_records())
        df_logs = pd.DataFrame(ws_log.get_all_records())
        df_measure = pd.DataFrame(ws_olcum.get_all_records())
        
        return sh, df_students, df_logs, df_measure
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, None, None

# --- ANA PROGRAM ---
# Değişken isimlerini burada eşitliyoruz
sh, df_ogrenci, df_log, df_olcum = veri_getir()

if sh:
    # YAN MENÜ
    with st.sidebar:
        st.title("💪 PT KONTROL")
        st.write("👤 **Levent Hoca**")
        st.success("🟢 Bulut Bağlantısı Aktif")
        st.divider()
        menu = st.radio("Menü", ["Ana Ekran", "Öğrenci Ekle/Düzenle", "Vücut Ölçümleri", "Raporlar"])
        if st.button("🔄 Verileri Yenile"):
            st.cache_data.clear()
            st.rerun()

    # === 1. ANA EKRAN ===
    if menu == "Ana Ekran":
        st.header("📋 Öğrenci Listesi")
        c1, c2 = st.columns([3, 1])
        arama = c1.text_input("🔍 Ara...")
        filtre = c2.selectbox("Filtre", ["Aktif", "Pasif", "Tümü"])
        
        if not df_ogrenci.empty:
            mask = pd.Series([True] * len(df_ogrenci))
            if filtre == "Aktif": mask = mask & (df_ogrenci["durum"] == "active")
            if filtre == "Pasif": mask = mask & (df_ogrenci["durum"] == "passive")
            if arama: mask = mask & (df_ogrenci["isim"].str.contains(
