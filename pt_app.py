import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import time

# --- AYARLAR ---
st.set_page_config(page_title="PT", layout="wide", page_icon="💪")

# --- CSS İLE TELEFONU ZORLAMA VE BUTON RENKLENDİRME ---
st.markdown("""
<style>
    /* 1. Sayfa Kenar Boşluklarını Yok Et */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0.1rem;
        padding-right: 0.1rem;
    }

    /* 2. TELEFON İÇİN ÖZEL KOD (Zorla Yan Yana) */
    @media (max-width: 800px) {
        div[data-testid="column"] {
            width: 12% !important;
            flex: 0 0 12% !important;
            min-width: 0px !important;
            padding: 0px 1px !important;
        }
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 1px !important;
        }
    }

    /* Masaüstü için de aynı ayar */
    div[data-testid="column"] {
        width: 12% !important;
        flex: 0 0 12% !important;
        min-width: 0px !important;
        padding: 0px 1px !important;
    }

    /* 3. Butonları Ayarla */
    .stButton button {
        width: 100%;
        padding: 0px !important;
        font-size: 9px !important; /* Yazılar sığsın diye minik font */
        font-weight: bold !important;
        line-height: 1 !important;
        height: 22px !important;
        min-height: 0px !important;
        margin-top: 2px !important;
    }
    
    /* İPTAL butonu (Secondary) Beyaz kalsın, kenarlığı ince olsun */
    button[kind="secondary"] {
        border: 1px solid #ccc !important;
        background-color: white !important;
        color: black !important;
    }

    /* DÜŞ butonu (Primary) Kırmızı olsun */
    button[kind="primary"] {
        background-color: #ff4b4b !important; /* Streamlit Kırmızısı */
        color: white !important;
        border: none !important;
    }
    
    /* 4. İsimleri Küçült */
    .ogrenci-isim {
        font-size: 9px;
        font-weight: bold;
        text-align: center;
        line-height: 1;
        white-space: normal; 
        height: 22px;
        overflow: hidden;
        margin-bottom: 0px;
    }
    
    /* 5. Bakiyeyi Küçült */
    .ogrenci-bakiye {
        font-size: 14px;
        font-weight: bold;
        text-align: center;
        margin: 0px;
        line-height: 1;
    }
    
    /* 6. Son Tarihi Küçült */
    .son-tarih {
        font-size: 7px;
        color: grey;
        text-align: center;
        margin-bottom: 1px;
    }

    /* 7. Kutunun Çerçevesi */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        padding: 1px !important;
        border: 1px solid #ddd;
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
        st.error(f"Hata: {e}")
        return None, None, None, None

# --- ANA PROGRAM ---
sh, df_ogrenci, df_log, df_olcum = veri_getir()

if sh:
    # YAN MENÜ (SOLDA)
    with st.sidebar:
        st.markdown("### 🏋️‍♂️ PT")
        menu = st.radio("", ["Liste", "Yönetim", "Ölçüm", "Rapor"])
        if st.button("🔄"):
            st.cache_data.clear()
            st.rerun()

    # === 1. LİSTE (MİKRO MOD - 8 SÜTUNLU) ===
    if menu == "Liste":
        arama = st.text_input("", placeholder="Ara...", label_visibility="collapsed")
        
        # Son Dersler
        son_dersler = {}
        if not df_log.empty:
            df_log = tarihleri_zorla_cevir(df_log, "tarih")
            sadece_dersler = df_log[df_log["islem"].str.strip() == "Ders Yapıldı"].dropna(subset=["tarih_dt"])
            sadece_dersler = sadece_dersler.sort_values(by="tarih_dt", ascending=False)
            for _, row_log in sadece_dersler.iterrows():
                if row_log["ogrenci"] not in son_dersler:
                    son_dersler[row_log["ogrenci"]] = row_log["tarih_dt"].strftime("%d.%m")

        if not df_ogrenci.empty:
            df_aktif = df_ogrenci[df_ogrenci["durum"] == "active"]
            if arama:
                df_aktif = df_aktif[df_aktif["isim"].str.contains(arama, case=False)]
            
            # --- 8 SÜTUNLU IZGARA ---
            SUTUN_SAYISI = 8 
            cols = st.columns(SUTUN_SAYISI)
            
            for idx, row in df_aktif.iterrows():
                col_index = idx % SUTUN_SAYISI
                
                with cols[col_index]:
                    with st.container(border=True):
                        isim_tam = row["isim"]
                        bakiye = row["bakiye"]
                        renk = "green" if bakiye >= 5 else "orange" if bakiye > 0 else "red"
                        
                        st.markdown(f"<div class='ogrenci-isim'>{isim_tam}</div>", unsafe_allow_html=True)
                        st.markdown(f"<div class='ogrenci-bakiye' style='color:{renk}'>{bakiye}</div>", unsafe_allow_html=True)
                        
                        son_tarih = son_dersler.get(isim_tam, "-")
                        st.markdown(f"<div class='son-tarih'>{son_tarih}</div>", unsafe_allow_html=True)
                        
                        # BUTONLAR: DÜŞ (Kırmızı) ve İPTAL (Beyaz)
                        # 'type="primary"' -> CSS ile Kırmızı yapıldı
                        # 'type="secondary"' (varsayılan) -> CSS ile Beyaz yapıldı
                        if st.button("DÜŞ", key=f"d_{idx}", type="primary"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim_tam)
                            ws.update_cell(cell.row, 2, int(bakiye - 1))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, isim_tam, "Ders Yapıldı", ""])
                            st.toast("Düşüldü")
                            time.sleep(0.1)
                            st.rerun()
                            
                        if st.button("İPTAL", key=f"i_{idx}"):
                            ws = sh.worksheet("Ogrenciler")
                            cell = ws.find(isim_tam)
                            ws.update_cell(cell.row, 2, int(bakiye + 1))
                            zaman = datetime.now().strftime("%Y-%m-%d %H:%M")
                            sh.worksheet("Loglar").append_row([zaman, isim_tam, "Ders İptal/İade", "Düzeltme"])
                            st.toast("İade")
                            time.sleep(0.1)
                            st.rerun()

    # === 2. YÖNETİM ===
    elif menu == "Yönetim":
        st.header("⚙️")
        t1, t2 = st.tabs(["Yeni", "Düzenle"])
        with t1:
            with st.form("ekle"):
                ad = st.text_input("Ad")
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
                        st.success("OK")
                        st.rerun()

    # === 3. ÖLÇÜMLER ===
    elif menu == "Ölçüm":
        st.subheader("📏")
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
