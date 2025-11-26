import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

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
        try: ws_ogrenci = sh.worksheet("Ogrenciler")
        except: ws_ogrenci = sh.add_worksheet(title="Ogrenciler", rows="100", cols="5"); ws_ogrenci.append_row(["isim", "bakiye", "notlar", "durum", "son_guncelleme"])

        try: ws_log = sh.worksheet("Loglar")
        except: ws_log = sh.add_worksheet(title="Loglar", rows="1000", cols="4"); ws_log.append_row(["tarih", "ogrenci", "islem", "detay"])

        try: ws_olcum = sh.worksheet("Olcumler")
        except: ws_olcum = sh.add_worksheet(title="Olcumler", rows="1000", cols="5"); ws_olcum.append_row(["ogrenci", "tarih", "kilo", "yag", "bel"])

        # Verileri String (Yazı) olarak al
        df_students = pd.DataFrame(ws_ogrenci.get_all_records()).astype(str)
        df_logs = pd.DataFrame(ws_log.get_all_records()).astype(str)
        df_measure = pd.DataFrame(ws_olcum.get_all_records())

        # Bakiyeyi sayıya çevir
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
        
        # --- SON DERS TARİHLERİ (AKILLI MOD) ---
        son_dersler = {}
        if not df_log.empty:
            # İşlem adını temizle
            df_log["islem"] = df_log["islem"].str.strip()
            
            # 1. Pandas'ın otomatik tarih algılayıcısını kullan (mixed=True karışık formatları çözer)
            # errors='coerce' demek: Anlayamadığın saçma bir şey varsa hata verme, boş geç (NaT).
            df_log["tarih_dt"] = pd.to_datetime(df_log["tarih"], errors='coerce')
            
            # 2. Tarihi anlaşılamayan satırları yoksay
            df_log = df_log.dropna(subset=["tarih_dt"])

            # 3. Sadece 'Ders Yapıldı' olanları al
            sadece_dersler = df_log[df_log["islem"] == "Ders Yapıldı"].copy()
            
            # 4. En yeniden en eskiye sırala
            sadece_dersler = sadece_dersler.sort_values("tarih_dt", ascending=False)
            
            # 5. Her öğrencinin en üstteki (en yeni) dersini kaydet
            for _, row_log in sadece_dersler.iterrows():
                ogr_adi = row_log["ogrenci"]
                if ogr_adi not in son_dersler:
                    # Ekranda Gün.Ay.Yıl olarak göster
                    son_dersler[ogr_adi] = row_log["tarih_dt"].strftime("%d.%m.%Y")
        # ---------------------------------------------

        if not df_ogrenci.empty:
            mask = pd.Series([True] * len(df_ogrenci))
            if filtre == "Aktif": mask = mask & (df_ogrenci["durum"] == "active")
            if filtre == "Pasif": mask = mask & (df_ogrenci["durum"] == "passive")
            if arama: mask = mask & (df_ogrenci["isim"].str.contains(arama, case=False))
            
            filtrelenmis = df_ogrenci[mask]
            
            cols = st.columns(4)
            for idx, row in filtrelenmis.iterrows():
                col = cols[idx % 4]
                with col:
                    with st.container(border=True):
                        bakiye = row["bakiye"]
                        isim = row["isim"]
                        renk = "🟢" if bakiye >= 5 else "🟠" if bakiye > 0 else "🔴"
                        st.markdown(f"### {renk} {isim}")
                        st.metric("Kalan", bakiye)
                        
                        not_goster = row["notlar"] if row["notlar"] and row["notlar"] != "nan" else "Normal"
                        st.caption(f"📝 {not_goster}")

                        son_tarih = son_dersler.get(isim, "-")
                        st.caption(f"📅 **Son:** {son_tarih}")
                        
                        b1, b2 = st.columns(2)
                        # DÜŞ
                        if b1.button("DÜŞ 📉", key=f"d_{idx}", type="primary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim)
                            if cell:
                                ws.update_cell(cell.row, 2, int(bakiye - 1))
                                # YENİ KAYITLAR HER ZAMAN SAATLİ VE DÜZGÜN OLSUN
                                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                                sh.worksheet("Loglar").append_row([zaman, isim, "Ders Yapıldı", ""])
                                st.toast(f"{isim}: Ders düşüldü!")
                                time.sleep(1)
                                st.rerun()
                        
                        # İPTAL
                        if b2.button("İPTAL ↩️", key=f"i_{idx}"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim)
                            if cell:
                                ws.update_cell(cell.row, 2, int(bakiye + 1))
                                zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                                sh.worksheet("Loglar").append_row([zaman, isim, "Ders İptal/İade", "Düzeltme"])
                                st.toast("Geri alındı.")
                                time.sleep(1)
                                st.rerun()

    # === 2. ÖĞRENCİ YÖNETİMİ ===
    elif menu == "Öğrenci Ekle/Düzenle":
        st.header("⚙️ Yönetim")
        t1, t2 = st.tabs(["Yeni Kayıt", "Düzenle"])
        
        with t1:
            with st.form("ekle"):
                ad = st.text_input("Ad Soyad")
                bas = st.number_input("Paket", value=10)
                nt = st.text_area("Not")
                if st.form_submit_button("Kaydet"):
                    zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                    sh.worksheet("Ogrenciler").append_row([ad, bas, nt, "active", zaman])
                    st.success("Eklendi!")
                    time.sleep(1)
                    st.rerun()
                    
        with t2:
            if not df_ogrenci.empty:
                sec = st.selectbox("Seç", df_ogrenci["isim"].tolist())
                sec_veri = df_ogrenci[df_ogrenci["isim"] == sec].iloc[0]
                
                c1, c2 = st.columns(2)
                with c1:
                    ek = st.number_input("Ders Ekle", value=10)
                    if st.button("Yükle"):
                        ws = sh.worksheet("Ogrenciler")
                        cell = ws.find(sec)
                        if cell:
                            ws.update_cell(cell.row, 2, int(sec_veri["bakiye"] + ek))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, sec, "Paket Yüklendi", f"{ek} ders"])
                            st.success("Yüklendi!")
                            st.rerun()
                
                st.divider()
                st.write("📜 **Ders Geçmişi**")
                if not df_log.empty:
                    # Burada da akıllı tarih çevirici kullanıyoruz
                    df_log["tarih_dt"] = pd.to_datetime(df_log["tarih"], errors='coerce')
                    kisi_log = df_log[df_log["ogrenci"] == sec].copy()
                    
                    if not kisi_log.empty:
                        # Tarihe göre sırala (NaT olanlar en sona gider)
                        kisi_log = kisi_log.sort_values(by="tarih_dt", ascending=False)
                        st.dataframe(kisi_log[["tarih", "islem", "detay"]], use_container_width=True)
                    else:
                        st.info("Kayıt yok.")

    # === 3. ÖLÇÜMLER ===
    elif menu == "Vücut Ölçümleri":
        st.header("📏 Ölçümler")
        o_sec = None
        if df_ogrenci.empty:
            st.warning("Önce öğrenci ekleyin.")
        else:
            c1, c2 = st.columns([1, 2])
            with c1:
                o_sec = st.selectbox("Öğrenci", df_ogrenci["isim"].tolist())
                with st.form("olcum"):
                    trh = st.date_input("Tarih")
                    kg = st.number_input("Kilo")
                    yg = st.number_input("Yağ")
                    bl = st.number_input("Bel")
                    if st.form_submit_button("Kaydet"):
                        sh.worksheet("Olcumler").append_row([o_sec, str(trh), kg, yg, bl])
                        st.success("Kaydedildi")
                        time.sleep(1)
                        st.rerun()
            with c2:
                if o_sec and not df_olcum.empty:
                    kisi_olcum = df_olcum[df_olcum["ogrenci"] == o_sec].copy()
                    if not kisi_olcum.empty:
                        kisi_olcum["kilo"] = pd.to_numeric(kisi_olcum["kilo"], errors='coerce')
                        st.line_chart(kisi_olcum, x="tarih", y="kilo")
                        st.dataframe(kisi_olcum, use_container_width=True)
                    else:
                        st.info("Veri yok.")

    # === 4. RAPORLAR ===
    elif menu == "Raporlar":
        st.header("📊 Raporlar")
        if not df_log.empty:
            # Akıllı tarih çevirici raporlarda da devrede
            df_log["tarih_dt"] = pd.to_datetime(df_log["tarih"], errors='coerce')
            df_log = df_log.dropna(subset=["tarih_dt"])
            df_log["Ay"] = df_log["tarih_dt"].dt.strftime("%Y-%m")
            
            dersler = df_log[df_log["islem"].str.strip() == "Ders Yapıldı"]
            
            st.bar_chart(dersler["Ay"].value_counts())
            st.dataframe(df_log[["tarih", "ogrenci", "islem"]].sort_values("tarih", ascending=False), use_container_width=True)
