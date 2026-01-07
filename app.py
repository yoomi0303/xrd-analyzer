import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
import io

# =============================================================================
# 1. 광물 DB (업데이트됨: Quartz/SO3 추가, Friedel 수정, C-S-H 제외)
# =============================================================================
MINERAL_DB = {
    # --- 1. 실리카 및 황산염 ---
    "Quartz (SiO2)": { "peaks": [26.6, 20.8, 50.1], "marker": "x", "color": "purple" },
    "Gypsum (CaSO4.2H2O)": { "peaks": [11.6, 20.7, 23.4], "marker": "1", "color": "cyan" },
    "Bassanite (Hemihydrate)": { "peaks": [14.7, 29.7, 31.9], "marker": "B", "color": "navy" },
    "Anhydrite (CaSO4)": { "peaks": [25.4, 38.6], "marker": "A", "color": "blue" },

    # --- 2. 주요 수화물 ---
    "Portlandite (CH)": { "peaks": [18.0, 34.1, 47.1], "marker": "v", "color": "blue" },
    "Ettringite (AFt)": { "peaks": [9.1, 15.8, 22.9], "marker": "*", "color": "red" },
    "Monosulfate (AFm)": { "peaks": [9.9, 11.7], "marker": "s", "color": "orange" },
    "Hemicarbonate (Hc)": { "peaks": [10.5, 10.8], "marker": "H", "color": "teal" },
    "Monocarbonate (Mc)": { "peaks": [11.6, 11.7], "marker": "M", "color": "magenta" },
    
    # --- 3. 슬래그/염해 관련 ---
    "Hydrotalcite (Ht)": { "peaks": [11.3, 22.8], "marker": "h", "color": "olive" },
    "Stratlingite (C2ASH8)": { "peaks": [7.2, 14.3], "marker": "8", "color": "pink" },
    "Friedel's Salt (Fs)": { "peaks": [11.2, 22.5], "marker": "p", "color": "navy" },
    "Thaumasite": { "peaks": [9.1, 16.0], "marker": "+", "color": "cyan" },
    
    # --- 4. 클링커 및 원재료 ---
    "Alite (C3S)": { "peaks": [29.4, 32.2, 34.3, 41.3, 51.7], "marker": "o", "color": "black" },
    "Belite (C2S)": { "peaks": [32.1, 32.5, 34.4], "marker": "d", "color": "gray" },
    "Aluminate (C3A)": { "peaks": [33.2, 47.6], "marker": "^", "color": "brown" },
    "Ferrite (C4AF)": { "peaks": [33.5, 47.7], "marker": "v", "color": "brown" },
    "Calcite": { "peaks": [29.4, 39.4, 47.5, 48.5], "marker": "D", "color": "green" },
    "Dolomite": { "peaks": [30.9, 41.1, 50.5], "marker": "D", "color": "lime" },
    "Feldspar": { "peaks": [27.5, 21.0, 23.6], "marker": "4", "color": "violet" },
    "Hematite (Fe2O3)": { "peaks": [33.1, 35.6, 54.0], "marker": "P", "color": "darkred" },
}

# 2. 웹 앱 설정
st.set_page_config(page_title="Team XRD Analyzer", layout="wide")
st.title("🧪 엑셀 파일 XRD 분석기")
st.markdown("엑셀/TXT 파일을 업로드하면 **Top 5 성분 비율**과 **누적 그래프**를 자동으로 그려줍니다.")

# 3. 파일 업로드
uploaded_file = st.file_uploader("파일 업로드 (.xlsx, .csv, .txt)", type=["xlsx", "xls", "csv", "txt"])

if uploaded_file is not None:
    # 데이터 읽기
    try:
        if uploaded_file.name.lower().endswith(('.csv', '.txt')):
            df = pd.read_csv(uploaded_file, sep=None, engine='python', header=None)
        else:
            try:
                df = pd.read_excel(uploaded_file, sheet_name='data', header=None)
            except:
                df = pd.read_excel(uploaded_file, header=None)
        
        st.success("✅ 파일 로드 성공!")
    except Exception as e:
        st.error(f"파일을 읽을 수 없습니다: {e}")
        st.stop()

    # 샘플 목록 추출
    sample_names = []
    try:
        float(df.iloc[0, 0]) 
        is_header_row = False
    except:
        is_header_row = True

    if not is_header_row and df.shape[1] == 2:
        sample_names = [uploaded_file.name]
    else:
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
            # 그래프 생성
            fig, ax = plt.subplots(figsize=(10, 5 + len(selected_samples) * 1.5))
            
            current_offset = 0
            all_x = []
            used_minerals_for_legend = {}

            for sample_name in selected_samples:
                # 데이터 찾기 및 추출
                two_theta, intensity = [], []
                
                # Case A: 단일 샘플
                if len(sample_names) == 1 and sample_names[0] == uploaded_file.name:
                    x_raw = pd.to_numeric(df.iloc[:, 0], errors='coerce')
                    y_raw = pd.to_numeric(df.iloc[:, 1], errors='coerce')
                # Case B: 다중 샘플 엑셀
                else:
                    found_col_idx = -1
                    for i in range(0, df.shape[1], 2):
                        if str(df.iloc[0, i]).strip() == sample_name:
                            found_col_idx = i
                            break
                    if found_col_idx == -1: continue
                    x_raw = pd.to_numeric(df.iloc[2:, found_col_idx], errors='coerce')
                    y_raw = pd.to_numeric(df.iloc[2:, found_col_idx+1], errors='coerce')

                # 유효 데이터 필터링
                valid = x_raw.notna() & y_raw.notna()
                two_theta = x_raw[valid].values
                intensity = y_raw[valid].values # 그대로 사용
                
                if len(two_theta) == 0: continue
                all_x.extend(two_theta)

                max_int = np.max(intensity)
                y_shifted = intensity + current_offset
                
                # 그래프 그리기
                ax.plot(two_theta, y_shifted, color='black', linewidth=1)
                ax.text(two_theta[-1] + 1, y_shifted[-1], f" {sample_name}", 
                        fontweight='bold', fontsize=10, va='center', ha='left')

                # 피크 찾기
                peaks, _ = find_peaks(intensity, height=max_int*0.03, distance=10)
                stats = []
                total_int = 0
                
                # [분석 로직 개선] Top 2 피크 합산 방식
                for m, info in MINERAL_DB.items():
                    matched_indices = [p for p in peaks if any(abs(two_theta[p]-ref) <= tolerance for ref in info['peaks'])]
                    
                    if matched_indices:
                        matched_intensities = [intensity[p] for p in matched_indices]
                        matched_intensities.sort(reverse=True)
                        
                        # 상위 2개 피크의 합만 점수로 사용
                        s = sum(matched_intensities[:2])
                        
                        peaks_matched = [(two_theta[p], intensity[p]) for p in matched_indices]
                        stats.append({'name':m, 'sum':s, 'peaks':peaks_matched, 'info':info})
                        total_int += s
                
                # Top 5 선정
                stats.sort(key=lambda x:x['sum'], reverse=True)
                top5 = stats[:5]
                
                lines = []
                for item in top5:
                    item['peaks'].sort(key=lambda x:x[1], reverse=True)
                    # 마커는 상위 3개까지 표시
                    for px, py in item['peaks'][:3]:
                        ax.scatter(px, py+current_offset+max_int*0.03, marker=item['info']['marker'], color=item['info']['color'], s=40, zorder=5, edgecolors='black', linewidth=0.5)
                    
                    if item['name'] not in used_minerals_for_legend:
                        used_minerals_for_legend[item['name']] = item['info']
                    
                    pct = (item['sum']/total_int*100) if total_int>0 else 0
                    simple_name = item['name'].split('(')[0].strip()
                    lines.append(f"{simple_name}: {pct:.1f}%")

                full_label = "\n".join(lines)
                ax.text(max(two_theta)-1, current_offset+max_int, full_label, 
                        ha='right', va='top', fontsize=8, 
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray', boxstyle='round,pad=0.3'))

                current_offset += (max_int + max_int*0.4)

            # 스타일링
            ax.set_xlabel('2-Theta (deg)', fontsize=12, fontweight='bold')
            ax.set_ylabel('Intensity (a.u.)', fontsize=12, fontweight='bold')
            ax.set_yticks([])
            if all_x: ax.set_xlim(min(all_x), max(all_x))
            
            # 범례
            handles, labels = [], []
            for m in sorted(used_minerals_for_legend.keys()):
                info = used_minerals_for_legend[m]
                h = ax.scatter([],[], marker=info['marker'], color=info['color'], s=40, edgecolors='black', linewidth=0.5)
                handles.append(h)
                labels.append(m)
            
            if handles:
                ax.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc='upper left', title="Identified Phases", fontsize=10)

            st.pyplot(fig)

            # 다운로드
            fn = "xrd_analysis_result.png"
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight')
            st.download_button(label="📷 그래프 이미지 다운로드", data=img, file_name=fn, mime="image/png")
