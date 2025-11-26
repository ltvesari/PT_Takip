import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
st.set_page_config(page_title="PT Levent Hoca", layout="wide", page_icon="💪")

# --- TASARIM (MAVİ PASTEL & OKUNAKLI) ---
st.markdown("""
<style>
    /* GENEL */
    .stApp { background-color: #F4F7F6; }
    [data-testid="stSidebar"] { background-color: #2C3E50; }
    [data-testid="stSidebar"] * { color: #ecf0f1 !important; }

    /* KART YAPISI */
    div[data-testid="column"] { padding: 5px !important; }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background-color: white;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        padding: 0px !important;
        overflow: hidden;
    }

    /* KART BAŞLIĞI */
    .card-header {
        background-color: #3498DB;
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 14px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
    }
    
    /* BAKİYE */
    .stat-box { padding: 15px 10px 5px 10px; text-align: center; }
    .stat-number { font-size: 32px; font-weight: 800; color: #2C3E50; line-height: 1; }
    .stat-label { font-size: 12px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; }

    /* PROGRESS BAR */
    .progress-container {
        width: 80%;
        background-color: #e0e0e0;
        border-radius: 10px;
        margin: 10px auto; 
        height: 8px;
    }
    .progress-fill { height: 100%; border-radius: 10px; transition: width 0.5s; }

    /* ALT BİLGİLER */
    .info-row {
        font-size: 11px;
        color: #95a5a6;
        text-align: center;
        margin-bottom: 5px;
    }

    /* BUTONLAR */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        font-size: 12px;
        padding: 0.5rem 1rem;
        border: none;
    }
    button[kind="primary"] { background-color: #E74C3C !important; color: white !important; }
    button[kind="secondary"] { background-color: #BDC3C7 !important; color: #2C3E50 !important; }
    
    /* DOĞUM GÜNÜ UYARISI */
    .birthday-alert {
        background-color: #FFD700;
        color: #d35400;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 20px;
        border: 2px solid #f39c12;
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

# --- YARDIMCI FONKSİYONLAR ---
def tarihleri_zorla_cevir(df, kolon_adi):
    df[kolon_adi] = df[kolon_adi].astype(str).str.strip()
    df["tarih_dt"] = pd.to_datetime(df[kolon_adi], dayfirst=True, format="mixed", errors='coerce')
    if df["tarih_dt"].isnull().all():
         df["tarih_dt"] = pd.to_datetime(df[kolon_adi], errors='coerce')
    return df

def progress_bar_yap(bakiye):
    yuzde = min(bakiye * 5, 100) 
    if bakiye <= 3: renk = "#E74C3C" 
    elif bakiye <= 7: renk = "#F39C12" 
    else: renk = "#2ECC71" 
    return f"""<div class="progress-container"><div class="progress-fill" style="width: {yuzde}%; background-color: {renk};"></div></div>"""

# --- VERİ ÇEKME ---
def veri_getir():
    try:
        sh = baglanti_kur()
        try: ws_ogrenci = sh.worksheet("Ogrenciler")
        except: ws_ogrenci = sh.add_worksheet(title="Ogrenciler", rows="100", cols="6")
        
        try: ws_log = sh.worksheet("Loglar")
        except: ws_log = sh.add_worksheet(title="Loglar", rows="1000", cols="4")
        
        try: ws_olcum = sh.worksheet("Olcumler")
        except: ws_olcum = sh.add_worksheet(title="Olcumler", rows="1000", cols="5")

        df_students = pd.DataFrame(ws_ogrenci.get_all_records()).astype(str)
        df_logs = pd.DataFrame(ws_log.get_all_records()).astype(str)
        df_measure = pd.DataFrame(ws_olcum.get_all_records())
        df_students["bakiye"] = pd.to_numeric(df_students["bakiye"], errors='coerce').fillna(0).astype(int)

        # Doğum tarihi kolonu yoksa hata vermesin diye kontrol
        if "dogum_tarihi" not in df_students.columns:
            df_students["dogum_tarihi"] = ""

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
        
        # --- DOĞUM GÜNÜ KONTROLÜ ---
        bugun = datetime.now()
        dogum_gunu_cocuklari = []
        if not df_ogrenci.empty and "dogum_tarihi" in df_ogrenci.columns:
            for _, row in df_ogrenci.iterrows():
                dt_str = str(row["dogum_tarihi"]).strip()
                if dt_str and dt_str != "nan":
                    try:
                        # Tarih formatını algıla (YYYY-MM-DD veya DD.MM.YYYY)
                        dt = pd.to_datetime(dt_str, dayfirst=True)
                        if dt.month == bugun.month and dt.day == bugun.day:
                            dogum_gunu_cocuklari.append(row["isim"])
                    except:
                        pass
        
        if dogum_gunu_cocuklari:
            st.balloons()
            isimler = ", ".join(dogum_gunu_cocuklari)
            st.markdown(f"""
            <div class='birthday-alert'>
                🎂 İYİ Kİ DOĞDUN! <br>
                Bugün {isimler} kullanıcısının doğum günü! 🥳
            </div>
            """, unsafe_allow_html=True)
        # ---------------------------

        st.markdown("### 📋 Öğrenci Listesi")
        
        c1, c2 = st.columns([3, 1])
        arama = c1.text_input("🔍 İsim Ara...")
        filtre = c2.selectbox("Filtre", ["Aktif", "Pasif", "Tümü"])
        
        # Son Dersler
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
            
            cols = st.columns(4)
            for idx, row in filtrelenmis.iterrows():
                col = cols[idx % 4]
                with col:
                    with st.container(border=True):
                        isim = row["isim"]
                        bakiye = row["bakiye"]
                        son_tarih = son_dersler.get(isim, "-")
                        
                        st.markdown(f"<div class='card-header'>{isim}</div>", unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class='stat-box'>
                            <div class='stat-label'>KALAN DERS</div>
                            <div class='stat-number'>{bakiye}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(progress_bar_yap(bakiye), unsafe_allow_html=True)
                        
                        # Notlar
                        if row["notlar"] and row["notlar"] != "nan":
                            st.markdown(f"<div class='info-row' style='color:#e67e22'>⚠️ {row['notlar']}</div>", unsafe_allow_html=True)

                        # Son Ders
                        st.markdown(f"<div class='info-row'>📅 Son: {son_tarih}</div>", unsafe_allow_html=True)
                        
                        # Doğum Günü Göstergesi (Varsa)
                        dt_str = str(row.get("dogum_tarihi", "")).strip()
                        if dt_str and dt_str != "nan":
                             st.markdown(f"<div class='info-row'>🎂 {dt_str}</div>", unsafe_allow_html=True)

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

    # === 2. ÖĞRENCİ YÖNETİMİ (GÜNCELLENDİ) ===
    elif menu == "Öğrenci Ekle/Düzenle":
        st.header("⚙️ Öğrenci Yönetimi")
        t1, t2 = st.tabs(["Yeni Kayıt", "Düzenle / Paket Yükle"])
        
        # --- YENİ KAYIT ---
        with t1:
            with st.form("ekle"):
                ad = st.text_input("Ad Soyad")
                bas = st.number_input("Paket Başlangıç", value=10)
                nt = st.text_area("Notlar (Sakatlık vb.)")
                # Doğum Tarihi Ekleme
                dt_input = st.date_input("Doğum Tarihi (İsteğe Bağlı)", value=None, min_value=datetime(1950,1,1))
                
                if st.form_submit_button("Kaydet"):
                    zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                    dt_str = dt_input.strftime("%Y-%m-%d") if dt_input else ""
                    
                    # Sütun sırası: isim, bakiye, notlar, durum, son_guncelleme, dogum_tarihi
                    sh.worksheet("Ogrenciler").append_row([ad, bas, nt, "active", zaman, dt_str])
                    st.success(f"{ad} sisteme eklendi!")
                    time.sleep(1)
                    st.rerun()
        
        # --- DÜZENLEME ---
        with t2:
            if not df_ogrenci.empty:
                sec = st.selectbox("Öğrenci Seç", df_ogrenci["isim"].tolist())
                # Veriyi al
                sec_veri = df_ogrenci[df_ogrenci["isim"] == sec].iloc[0]
                
                c1, c2 = st.columns(2)
                
                with c1:
                    st.subheader("📦 Paket & Durum")
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
                    # Durum Değiştirme
                    mevcut_durum = sec_veri.get("durum", "active")
                    yeni_durum = st.radio("Öğrenci Durumu", ["active", "passive"], index=0 if mevcut_durum=="active" else 1)
                    if st.button("Durumu Güncelle"):
                        ws = sh.worksheet("Ogrenciler")
                        cell = ws.find(sec)
                        # Durum 4. sütunda
                        ws.update_cell(cell.row, 4, yeni_durum)
                        st.success("Durum güncellendi.")
                        st.rerun()

                with c2:
                    st.subheader("📝 Bilgiler")
                    # Notları güncelle
                    mevcut_not = sec_veri.get("notlar", "")
                    if mevcut_not == "nan": mevcut_not = ""
                    yeni_not = st.text_area("Notlar", value=mevcut_not)
                    
                    # Doğum Tarihi Güncelleme
                    mevcut_dt = sec_veri.get("dogum_tarihi", "")
                    dt_value = None
                    if mevcut_dt and mevcut_dt != "nan":
                        try:
                            dt_value = pd.to_datetime(mevcut_dt).date()
                        except:
                            pass
                    
                    yeni_dt = st.date_input("Doğum Tarihi", value=dt_value, min_value=datetime(1950,1,1))
                    
                    if st.button("Bilgileri Kaydet"):
                        ws = sh.worksheet("Ogrenciler")
                        cell = ws.find(sec)
                        # Notlar 3. sütun
                        ws.update_cell(cell.row, 3, yeni_not)
                        
                        # Doğum Tarihi 6. sütun (F sütunu)
                        dt_str = yeni_dt.strftime("%Y-%m-%d") if yeni_dt else ""
                        ws.update_cell(cell.row, 6, dt_str)
                        
                        st.success("Bilgiler kaydedildi.")
                        st.rerun()

                st.divider()
                st.subheader(f"📜 Ders Geçmişi")
                if not df_log.empty:
                    df_log = tarihleri_zorla_cevir(df_log, "tarih")
                    kisi_log = df_log[df_log["ogrenci"] == sec].copy()
                    if not kisi_log.empty:
                        kisi_log = kisi_log.sort_values(by="tarih_dt", ascending=False)
                        st.dataframe(kisi_log[["tarih", "islem", "detay"]], use_container_width=True)
                    else:
                        st.info("Kayıt yok.")

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
            df_sirali = df_log.sort_values("tarih_dt", ascending=False)
            st.dataframe(df_sirali[["tarih", "ogrenci", "islem"]], use_container_width=True)
