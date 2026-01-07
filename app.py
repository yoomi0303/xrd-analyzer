import streamlit as st

import pandas as pd

import matplotlib.pyplot as plt

import numpy as np

from scipy.signal import find_peaks

import io



# 1. 광물 DB 설정

MINERAL_DB = {

    # --- 주요 수화물 (Main Hydrates) ---

    "Portlandite (CH)": { "peaks": [18.0, 34.1, 47.1, 50.8], "marker": "v", "color": "blue" },

    "Ettringite (AFt)": { "peaks": [9.1, 15.8, 22.9, 35.0], "marker": "*", "color": "red" },

    "Monosulfate (AFm)": { "peaks": [9.9, 11.7, 22.7], "marker": "s", "color": "orange" },

    "Hemicarbonate (Hc)": { "peaks": [10.5, 10.8, 21.3], "marker": "H", "color": "teal" },

    "Monocarbonate (Mc)": { "peaks": [11.6, 11.7, 23.5], "marker": "M", "color": "magenta" },

    

    # --- 추가된 수화물 (유효한 마커로 변경됨) ---

    "Hydrotalcite (Ht)": { "peaks": [11.3, 22.8, 34.6, 38.9, 46.4, 60.5, 61.9], "marker": "h", "color": "olive" }, # h: 육각형

    "Stratlingite (C2ASH8)": { "peaks": [7.2, 14.3, 21.5, 28.7], "marker": "8", "color": "pink" },    # 8: 팔각형

    "Friedel's Salt (Fs)": { "peaks": [11.2, 22.5, 33.9, 39.5, 47.1], "marker": "p", "color": "navy" },    # p: 오각형

    "Thaumasite": { "peaks": [9.1, 16.0, 19.1, 22.5], "marker": "+", "color": "cyan" },             # +: 플러스 기호

    "C-S-H Gel (Hump)": { "peaks": [29.4, 32.0, 50.0], "marker": ".", "color": "gray" },



    # --- 클링커 및 원재료 ---

    "Alite (C3S)": { "peaks": [29.4, 32.2, 32.6, 34.3, 41.3, 51.7], "marker": "o", "color": "black" },

    "Belite (C2S)": { "peaks": [32.1, 32.5, 34.4, 38.7, 41.2], "marker": "d", "color": "gray" },

    "Aluminate (C3A)": { "peaks": [33.2, 47.6, 59.3], "marker": "^", "color": "brown" },

    "Ferrite (C4AF)": { "peaks": [33.5, 47.7], "marker": "v", "color": "brown" },

    "Quartz (SiO2)": { "peaks": [20.8, 26.6, 36.5, 39.5, 40.3, 42.4, 45.8, 50.1, 54.9, 60.0], "marker": "x", "color": "purple" },

    "Gypsum": { "peaks": [11.6, 20.7, 23.4, 29.1], "marker": "1", "color": "cyan" },

    "Calcite": { "peaks": [29.4, 39.4, 43.1, 47.5, 48.5], "marker": "D", "color": "green" },

    "Dolomite": { "peaks": [30.9, 41.1, 50.5, 51.1], "marker": "D", "color": "lime" },

    "Feldspar": { "peaks": [27.5, 21.0, 23.6, 25.6], "marker": "4", "color": "violet" }, # 4: 오른쪽 삼각형

    "Hematite (Fe2O3)": { "peaks": [33.1, 35.6, 24.1, 40.8, 49.4, 54.0], "marker": "P", "color": "darkred" }, # P: 굵은 플러스

}





# 2. 웹 앱 설정

st.set_page_config(page_title="Team XRD Analyzer", layout="wide")

st.title("🧪 엑셀 파일 XRD 분석기")

st.markdown("엑셀 파일을 업로드하면 **Top 5 성분 비율**과 **누적 그래프**를 자동으로 그려줍니다.")



# 3. 파일 업로드

uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx, .csv)", type=["xlsx", "xls", "csv"])



if uploaded_file is not None:

    # 데이터 읽기

    try:

        if uploaded_file.name.endswith('.csv'):

            df = pd.read_csv(uploaded_file, header=None)

        else:

            df = pd.read_excel(uploaded_file, sheet_name='data', header=None)

    except:

        df = pd.read_excel(uploaded_file, header=None)

        

    st.success("✅ 파일 로드 성공!")



    # 샘플 목록 추출

    sample_names = []

    num_cols = df.shape[1]

    for i in range(0, num_cols, 2):

        if i+1 < num_cols:

            col_name = str(df.iloc[0, i]).strip()

            if col_name and col_name != 'nan':

                sample_names.append(col_name)



    # 샘플 선택

    selected_samples = st.multiselect("비교 분석할 샘플을 선택하세요:", sample_names, default=sample_names[:2] if len(sample_names)>=2 else sample_names)



    if selected_samples:

        tolerance = st.slider("오차 범위 (Tolerance)", 0.1, 0.5, 0.3, 0.05)

        

        if st.button("분석 실행 🚀"):

            # ---------------------------------------------------------

            # [수정됨] 그래프 크기 축소 (가로 14->10, 세로 10->5)

            # ---------------------------------------------------------

            fig, ax = plt.subplots(figsize=(10, 5 + len(selected_samples) * 1.5))

            

            current_offset = 0

            all_x = []

            used_minerals_for_legend = {}



            for sample_name in selected_samples:

                # 데이터 찾기

                found_col_idx = -1

                for i in range(0, num_cols, 2):

                    if str(df.iloc[0, i]).strip() == sample_name:

                        found_col_idx = i

                        break

                if found_col_idx == -1: continue



                # XY 데이터 추출

                x_raw = pd.to_numeric(df.iloc[2:, found_col_idx], errors='coerce')

                y_raw = pd.to_numeric(df.iloc[2:, found_col_idx+1], errors='coerce')

                valid = x_raw.notna() & y_raw.notna()

                two_theta = x_raw[valid].values

                intensity = y_raw[valid].values

                

                if len(two_theta) == 0: continue

                all_x.extend(two_theta)



                max_int = np.max(intensity)

                y_shifted = intensity + current_offset

                

                # 그래프 그리기 (검은 실선)

                ax.plot(two_theta, y_shifted, color='black', linewidth=1)

                

                # [샘플 이름] -> 그래프 오른쪽 끝

                ax.text(two_theta[-1] + 1, y_shifted[-1], f" {sample_name}", 

                        fontweight='bold', fontsize=10, va='center', ha='left')



                # 피크 찾기 및 분석

                peaks, _ = find_peaks(intensity, height=max_int*0.03, distance=10)

                stats = []

                total_int = 0

                

                for m, info in MINERAL_DB.items():

                    matched = [intensity[p] for p in peaks if any(abs(two_theta[p]-ref) <= tolerance for ref in info['peaks'])]

                    s = sum(matched)

                    if s > 0:

                        peaks_matched = [(two_theta[p], intensity[p]) for p in peaks if any(abs(two_theta[p]-ref) <= tolerance for ref in info['peaks'])]

                        stats.append({'name':m, 'sum':s, 'peaks':peaks_matched, 'info':info})

                        total_int += s

                

                # Top 5 선정

                stats.sort(key=lambda x:x['sum'], reverse=True)

                top5 = stats[:5]

                

                lines = []

                for item in top5:

                    # 마커 찍기 (Top 3 피크만)

                    item['peaks'].sort(key=lambda x:x[1], reverse=True)

                    for px, py in item['peaks'][:3]:

                        ax.scatter(px, py+current_offset+max_int*0.03, marker=item['info']['marker'], color=item['info']['color'], s=40, zorder=5, edgecolors='black', linewidth=0.5)

                    

                    # 범례용 수집

                    if item['name'] not in used_minerals_for_legend:

                        used_minerals_for_legend[item['name']] = item['info']

                    

                    # 비율 계산

                    pct = (item['sum']/total_int*100) if total_int>0 else 0

                    simple_name = item['name'].split('(')[0].strip()

                    lines.append(f"{simple_name}: {pct:.1f}%")



                # [비율 박스] -> 그래프 내부 우상단

                full_label = "\n".join(lines)

                ax.text(max(two_theta)-1, current_offset+max_int, full_label, 

                        ha='right', va='top', fontsize=8, 

                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray', boxstyle='round,pad=0.3'))



                current_offset += (max_int + max_int*0.4)



            # 스타일링

            ax.set_xlabel('2-Theta (deg)', fontsize=12, fontweight='bold')

            ax.set_ylabel('Intensity (Stacked)', fontsize=12, fontweight='bold')

            ax.set_yticks([])

            if all_x: ax.set_xlim(min(all_x), max(all_x))

            

            # [범례] -> 그래프 바깥 우측 상단

            handles, labels = [], []

            for m in sorted(used_minerals_for_legend.keys()):

                info = used_minerals_for_legend[m]

                h = ax.scatter([],[], marker=info['marker'], color=info['color'], s=40, edgecolors='black', linewidth=0.5)

                handles.append(h)

                labels.append(m)

            

            if handles:

                ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left', title="Identified Phases", fontsize=10)



            st.pyplot(fig)



            # 다운로드 버튼

            fn = "xrd_analysis_result.png"

            img = io.BytesIO()

            plt.savefig(img, format='png', bbox_inches='tight')

            st.download_button(label="📷 그래프 이미지 다운로드", data=img, file_name=fn, mime="image/png")

