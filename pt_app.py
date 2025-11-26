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
