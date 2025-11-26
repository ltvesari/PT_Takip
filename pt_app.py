import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
st.set_page_config(page_title="PT Levent Hoca", layout="wide", page_icon="💪")

# --- CSS TASARIM (FİŞ EKLENDİ) ---
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
    .stat-box { padding: 10px 10px 0px 10px; text-align: center; }
    .stat-number { font-size: 28px; font-weight: 800; color: #2C3E50; line-height: 1; }
    .stat-label { font-size: 10px; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; }

    /* PROGRESS BAR */
    .progress-container { width: 80%; background-color: #e0e0e0; border-radius: 10px; margin: 8px auto; height: 6px; }
    .progress-fill { height: 100%; border-radius: 10px; transition: width 0.5s; }

    /* DERS FİŞİ (TICKET) TASARIMI 🎫 */
    .ticket-wrapper {
        background: linear-gradient(135deg, #ffffff 0%, #f9f9f9 100%);
        border: 2px dashed #3498DB;
        border-radius: 15px;
        padding: 20px;
        width: 100%;
        max-width: 350px;
        margin: 0 auto 20px auto;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        position: relative;
    }
    .ticket-title { font-size: 12px; letter-spacing: 2px; color: #95a5a6; text-transform: uppercase; margin-bottom: 10px; }
    .ticket-name { font-size: 24px; font-weight: 900; color: #2C3E50; margin-bottom: 5px; }
    .ticket-date { font-size: 14px; color: #7f8c8d; margin-bottom: 20px; font-style: italic; }
    .ticket-balance-box { 
        background-color: #3498DB; 
        color: white; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 15px; 
    }
    .ticket-balance-num { font-size: 42px; font-weight: 800; line-height: 1; }
    .ticket-balance-lbl { font-size: 12px; opacity: 0.9; }
    .ticket-footer { font-size: 10px; color: #bdc3c7; margin-top: 10px; }
    
    /* BUTONLAR */
    .stButton button {
        width: 100%;
        border-radius: 6px;
        font-weight: 600;
        font-size: 11px;
        padding: 0.4rem 0.1rem;
        border: none;
    }
    /* Renkler */
    button[kind="primary"] { background-color: #E74C3C !important; color: white !important; } /* Düş - Kırmızı */
    button[kind="secondary"] { background-color: #BDC3C7 !important; color: #2C3E50 !important; } /* İptal - Gri */
    /* Fiş Butonu İçin Özel Stil (Normal buton gibi davranır ama biz ona mavi dedik) */
    
    /* NOTLAR */
    .notes { font-size: 10px; color: #e67e22; text-align: center; margin-bottom: 5px; font-style: italic; }
    .last-date { font-size: 10px; color: #95a5a6; text-align: center; margin-bottom: 10px; }

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
        if "dogum_tarihi" not in df_students.columns: df_students["dogum_tarihi"] = ""

        return sh, df_students, df_logs, df_measure
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None, None, None, None

# --- ANA PROGRAM ---
sh, df_ogrenci, df_log, df_olcum = veri_getir()

if "fis_goster" not in st.session_state:
    st.session_state["fis_goster"] = None

if sh:
    with st.sidebar:
        st.markdown("### 💪 PT KONTROL")
        menu = st.radio("Menü", ["Ana Ekran", "Öğrenci Ekle/Düzenle", "Vücut Ölçümleri", "Raporlar"])
        if st.button("🔄 Yenile"):
            st.cache_data.clear()
            st.rerun()

    # === 1. ANA EKRAN ===
    if menu == "Ana Ekran":
        
        # --- FİŞ GÖSTERİM ALANI (SCREENSHOT MODU) ---
        if st.session_state["fis_goster"]:
            kisi = st.session_state["fis_goster"]
            # Kişinin bilgilerini bul
            kisi_row = df_ogrenci[df_ogrenci["isim"] == kisi["isim"]].iloc[0]
            
            st.markdown("---")
            c_fis, c_kapat = st.columns([4, 1])
            c_kapat.button("X Kapat", on_click=lambda: st.session_state.update({"fis_goster": None}))
            
            bugun_tarih = datetime.now().strftime("%d.%m.%Y")
            
            # ŞIK FİŞ HTML
            st.markdown(f"""
            <div class="ticket-wrapper">
                <div class="ticket-title">PT LEVENT HOCA • DERS DURUMU</div>
                <div class="ticket-name">{kisi['isim']}</div>
                <div class="ticket-date">📅 {bugun_tarih}</div>
                <div class="ticket-balance-box">
                    <div class="ticket-balance-num">{kisi_row['bakiye']}</div>
                    <div class="ticket-balance-lbl">KALAN DERS HAKKI</div>
                </div>
                <div class="ticket-footer">Spor, sağlık ve disiplin.<br>İyi antrenmanlar! 💪</div>
            </div>
            """, unsafe_allow_html=True)
            st.info("👆 Bu alanı ekran görüntüsü alıp gönderebilirsin.")
            st.markdown("---")
        # --------------------------------------------

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
                            <div class='stat-label'>KALAN</div>
                            <div class='stat-number'>{bakiye}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(progress_bar_yap(bakiye), unsafe_allow_html=True)
                        
                        if row["notlar"] and row["notlar"] != "nan":
                            st.markdown(f"<div class='notes'>⚠️ {row['notlar']}</div>", unsafe_allow_html=True)

                        st.markdown(f"<div class='last-date'>📅 Son: {son_tarih}</div>", unsafe_allow_html=True)
                        
                        # 3'LÜ BUTON GRUBU (DÜŞ | FİŞ | İPTAL)
                        b1, b2, b3 = st.columns([1, 1, 1])
                        
                        # DÜŞ
                        if b1.button("DÜŞ", key=f"d_{idx}", type="primary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim)
                            ws.update_cell(cell.row, 2, int(bakiye - 1))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, isim, "Ders Yapıldı", ""])
                            st.toast(f"{isim}: Ders düşüldü!")
                            time.sleep(0.5)
                            st.rerun()
                        
                        # FİŞ (DURUM) - Mavi renkte olsun diye secondary kullanıp CSS ile halledebilirdik ama karışmasın diye şimdilik secondary
                        if b2.button("🎫", key=f"f_{idx}", help="Durum Fişi Oluştur"):
                            st.session_state["fis_goster"] = {"isim": isim}
                            st.rerun()

                        # İPTAL
                        if b3.button("İPTAL", key=f"i_{idx}", type="secondary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim)
                            ws.update_cell(cell.row, 2, int(bakiye + 1))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, isim, "Ders İptal/İade", "Düzeltme"])
                            st.toast("Geri alındı.")
                            time.sleep(0.5)
                            st.rerun()

    # === 2. ÖĞRENCİ YÖNETİMİ ===
    elif menu == "Öğrenci Ekle/Düzenle":
        st.header("⚙️ Yönetim")
        t1, t2 = st.tabs(["Yeni Kayıt", "Düzenle"])
        with t1:
            with st.form("ekle"):
                ad = st.text_input("Ad Soyad")
                bas = st.number_input("Paket", value=10)
                nt = st.text_area("Notlar")
                dt_input = st.date_input("Doğum Tarihi", value=None, min_value=datetime(1950,1,1))
                if st.form_submit_button("Kaydet"):
                    zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                    dt_str = dt_input.strftime("%Y-%m-%d") if dt_input else ""
                    sh.worksheet("Ogrenciler").append_row([ad, bas, nt, "active", zaman, dt_str])
                    st.success("Kaydedildi")
                    st.rerun()
        with t2:
            if not df_ogrenci.empty:
                sec = st.selectbox("Seç", df_ogrenci["isim"].tolist())
                sec_veri = df_ogrenci[df_ogrenci["isim"] == sec].iloc[0]
                c1, c2 = st.columns(2)
                with c1:
                    ek = st.number_input("Ekle", value=10)
                    if st.button("Yükle"):
                        ws = sh.worksheet("Ogrenciler")
                        cell = ws.find(sec)
                        ws.update_cell(cell.row, 2, int(sec_veri["bakiye"] + ek))
                        zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                        sh.worksheet("Loglar").append_row([zaman, sec, "Paket Yüklendi", f"{ek} ders"])
                        st.success("Yüklendi")
                        st.rerun()
                with c2:
                    yeni_not = st.text_area("Not", value=sec_veri.get("notlar", ""))
                    if st.button("Güncelle"):
                        ws = sh.worksheet("Ogrenciler")
                        cell = ws.find(sec)
                        ws.update_cell(cell.row, 3, yeni_not)
                        st.success("Güncellendi")
                        st.rerun()

    # === 3. ÖLÇÜMLER ===
    elif menu == "Vücut Ölçümleri":
        st.header("📏 Ölçümler")
        o_sec = None
        if not df_ogrenci.empty:
            o_sec = st.selectbox("Öğrenci", df_ogrenci["isim"].tolist())
            with st.form("olcum"):
                c1, c2 = st.columns(2)
                kg = c1.number_input("Kilo")
                yg = c2.number_input("Yağ")
                bl = st.number_input("Bel")
                if st.form_submit_button("Kaydet"):
                    trh_str = datetime.now().strftime("%Y-%m-%d")
                    sh.worksheet("Olcumler").append_row([o_sec, trh_str, kg, yg, bl])
                    st.success("Kaydedildi")
                    st.rerun()
            if o_sec and not df_olcum.empty:
                kisi_olcum = df_olcum[df_olcum["ogrenci"] == o_sec].copy()
                if not kisi_olcum.empty:
                    kisi_olcum["kilo"] = pd.to_numeric(kisi_olcum["kilo"], errors='coerce')
                    st.line_chart(kisi_olcum, x="tarih", y="kilo")

    # === 4. RAPORLAR ===
    elif menu == "Raporlar":
        st.header("📊 Raporlar")
        if not df_log.empty:
            df_log = tarihleri_zorla_cevir(df_log, "tarih")
            df_sirali = df_log.sort_values("tarih_dt", ascending=False)
            st.dataframe(df_sirali[["tarih", "ogrenci", "islem"]], use_container_width=True)
