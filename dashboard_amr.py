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

# Validasi kolom wajib
required_cols = ['LOCATION_CODE', 'LOCATION_TYPE']
missing_cols = [col for col in required_cols if col not in df.columns]
if missing_cols:
    st.error(f"❌ Kolom berikut wajib ada: {', '.join(missing_cols)}")
    st.stop()

# Filter hanya LOCATION_TYPE = CUSTOMER
df = df[df['LOCATION_TYPE'] == 'CUSTOMER']

# Hitung Jumlah Kemunculan per LOCATION_CODE
df['Jumlah Kemunculan'] = df.groupby('LOCATION_CODE')['LOCATION_CODE'].transform('count')

# -------------------- Tambahkan Indikator Teknis -------------------- #
def hitung_indikator_teknis(row):
    indikator = {}
    indikator['unbalance_arus'] = abs(row['CURRENT_L1'] - row['CURRENT_L2']) > 10 or abs(row['CURRENT_L2'] - row['CURRENT_L3']) > 10
    indikator['arus_netral_lebih_besar'] = row.get('CURRENT_NEUTRAL', 0) > max(row['CURRENT_L1'], row['CURRENT_L2'], row['CURRENT_L3'])
    indikator['urutan_fasa_terbalik'] = row.get('PHASE_SEQUENCE', '') == 'K-L'
    indikator['kwh_import_lebih_besar_export'] = row.get('KWH_IMPORT', 0) > row.get('KWH_EXPORT', 0)
    indikator['tegangan_hilang_ada_arus'] = any(row[f'VOLTAGE_L{i}'] == 0 and row[f'CURRENT_L{i}'] > 0 for i in range(1, 4))
    return indikator

indikator_result = df.apply(hitung_indikator_teknis, axis=1, result_type='expand')
df[indikator_result.columns] = indikator_result

# -------------------- FILTER INDIKATOR -------------------- #
indikator_kolom = [
    'unbalance_arus', 'arus_netral_lebih_besar', 'urutan_fasa_terbalik',
    'kwh_import_lebih_besar_export', 'tegangan_hilang_ada_arus'
]

st.sidebar.header("🧮 Filter Indikator")
selected_indikator = st.sidebar.multiselect("Pilih indikator untuk analisa:", indikator_kolom, default=indikator_kolom)

# Filter data berdasarkan indikator
if selected_indikator:
    df['Jumlah Indikator Aktif'] = df[selected_indikator].sum(axis=1)
    df = df[df['Jumlah Indikator Aktif'] > 0]

    # Gabungkan berdasarkan LOCATION_CODE agar unik
    agg_dict = {col: 'max' for col in selected_indikator}
    agg_dict['Jumlah Indikator Aktif'] = 'sum'
    agg_dict['Jumlah Kemunculan'] = 'max'
    df_grouped = df.groupby('LOCATION_CODE').agg(agg_dict).sort_values("Jumlah Indikator Aktif", ascending=False).reset_index()

    # -------------------- TAMPILKAN -------------------- #
    st.subheader("Top Rekomendasi Target Operasi")
    st.dataframe(df_grouped.head(50), use_container_width=True)

    # Visualisasi indikator terbanyak
    st.subheader("📈 Visualisasi Indikator Terbanyak")
    indikator_count = df[selected_indikator].sum().sort_values(ascending=False)
    fig = px.bar(indikator_count, x=indikator_count.index, y=indikator_count.values,
                 labels={'x': 'Indikator', 'y': 'Jumlah'}, title="Jumlah Pemenuhan Indikator")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Pilih minimal satu indikator untuk ditampilkan.")