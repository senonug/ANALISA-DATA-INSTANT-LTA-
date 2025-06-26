import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# -------------------- AUTH -------------------- #
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    with st.form("login"):
        st.title("🔐 Login Pegawai")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username == "admin" and password == "pln123":
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Login gagal. Periksa kembali username dan password Anda.")
    st.stop()

# -------------------- DASHBOARD -------------------- #
st.set_page_config(page_title="Dashboard Target Operasi AMR", layout="wide")
st.title("📊 Dashboard Target Operasi P2TL AMR")

# Upload data
st.sidebar.header("📤 Upload Data Instant")
uploaded_file = st.sidebar.file_uploader("Unggah file Excel data instant", type=["xlsx"])

data_folder = "data_history"
os.makedirs(data_folder, exist_ok=True)

if uploaded_file is not None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(data_folder, f"instant_{timestamp}.xlsx")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"✅ File disimpan: {file_path}")

# Baca seluruh file historis
def read_all_excels(folder):
    dfs = []
    for file in os.listdir(folder):
        if file.endswith(".xlsx"):
            df = pd.read_excel(os.path.join(folder, file))
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

df = read_all_excels(data_folder)

if df.empty:
    st.warning("Belum ada data diunggah.")
    st.stop()

# -------------------- FILTER INDIKATOR -------------------- #
st.sidebar.header("🧮 Filter Indikator")
indikator_kolom = [
    'v_lost', 'cos_phi_kecil', 'arus_hilang', 'In_more_Imax', 'over_current', 'over_voltage',
    'active_power_negative', 'active_power_negative_siang', 'active_power_negative_malam',
    'unbalance_I', 'active_p_lost', 'arus_kecil_teg_kecil', 'current_loop', 'freeze',
    'v_drop', 'unbalance_arus', 'arus_netral_lebih_besar',
    'urutan_fasa_terbalik', 'kwh_import_lebih_besar_export', 'tegangan_hilang_ada_arus'
]

selected_indikator = st.sidebar.multiselect("Pilih indikator untuk analisa:", indikator_kolom, default=indikator_kolom)

# Filter data berdasarkan indikator
df_filtered = df[df[selected_indikator].sum(axis=1) > 0]

# Hapus duplikat IDPEL dan hitung jumlah indikator aktif
df_filtered['Jumlah Indikator Aktif'] = df_filtered[selected_indikator].sum(axis=1)
df_grouped = df_filtered.groupby('IDPEL').agg({col: 'max' for col in selected_indikator})
df_grouped['Jumlah Indikator Aktif'] = df_filtered.groupby('IDPEL')['Jumlah Indikator Aktif'].max()
df_grouped = df_grouped.sort_values("Jumlah Indikator Aktif", ascending=False).reset_index()

# -------------------- TAMPILKAN -------------------- #
st.subheader("Top Rekomendasi Target Operasi")
st.dataframe(df_grouped.head(50), use_container_width=True)

# Visualisasi indikator terbanyak
st.subheader("📈 Visualisasi Indikator Terbanyak")
indikator_count = df_filtered[selected_indikator].sum().sort_values(ascending=False)
fig = px.bar(indikator_count, x=indikator_count.index, y=indikator_count.values,
             labels={'x': 'Indikator', 'y': 'Jumlah'}, title="Jumlah Pemenuhan Indikator")
st.plotly_chart(fig, use_container_width=True)
