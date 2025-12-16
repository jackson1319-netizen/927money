import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="PAI 策略全能計算機 (完美校正版)",
    page_icon="💎",
    layout="wide"
)

# --- 1.5 密碼驗證模組 ---
def check_password():
    ACTUAL_PASSWORD = "TP927" 
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    def password_entered():
        if st.session_state["password"] == ACTUAL_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("🔒 請輸入訪問密碼", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password(): st.stop()

# --- 2. CSS ---
st.markdown("""
    <style>
    :root { --brand: #006d75; --text: #262626; --pos: #389e0d; --neg: #cf1322; }
    .metric-card { background:#f6ffed; border:1px solid #b7eb8f; padding:15px; border-radius:5px; margin-bottom:20px; }
    .verify-box { background:#262626; color:white; padding:20px; border-radius:10px; margin-top:20px; font-family:monospace; }
    .verify-row { display:flex; justify-content:space-between; margin-bottom:5px; }
    .verify-total { border-top:1px solid #555; padding-top:10px; margin-top:10px; font-weight:bold; color:#52c41a; font-size:18px; display:flex; justify-content:space-between; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心邏輯 (參數已校正) ---

@st.cache_data
def load_data(file):
    if file is None: return None
    df = pd.read_csv(file, header=None)
    data = {"prem": {}, "cv": {}, "db": {}}
    
    # Premium
    try:
        die_idx = df[df[129]=='DIE'].index[0]
        for _, r in df.iloc[1:die_idx].iterrows():
            data["prem"][f"{int(r[5])}_{int(r[7])}"] = float(r[10])
    except: pass
    
    # Values
    try:
        die_idx = df[df[129]=='DIE'].index[0]
        pv0_idx = df[df[129]=='PV0'].index[0]
        pv_idx = df[df[129]=='PV'].index[0]
        
        # DB Table
        for _, r in df.iloc[die_idx+2 : pv0_idx].iterrows():
            data["db"][f"{int(r[131])}_{int(r[132])}"] = r[134:].dropna().astype(str).str.replace(',','').astype(float).tolist()
            
        # CV Table
        for _, r in df.iloc[pv_idx+2 :].iterrows():
            data["cv"][f"{int(r[131])}_{int(r[132])}"] = r[134:].dropna().astype(str).str.replace(',','').astype(float).tolist()
    except: pass
    return data

def calc_policy(age, gender, face_wan, data, declared, loading, term_rate_cv, term_rate_db):
    key = f"{gender}_{age}"
    if key not in data["prem"]: return None
    
    units = face_wan # 萬元單位
    rate = data["prem"][key]
    
    # 1. 保費與折扣
    orig_prem = rate * units
    disc = 0.015 if face_wan >= 200 else (0.01 if face_wan >= 100 else 0)
    real_prem = orig_prem * (1 - disc)
    
    # 2. 基礎保證值
    raw_cv = data["cv"].get(key, [])
    raw_db = data["db"].get(key, [])
    
    g_cv = [v * units for v in raw_cv]
    g_db_table = [v * units for v in raw_db] # 查表身故
    
    # 3. 分紅計算
    assumed = 0.01
    spread = max(0, declared - assumed + loading)
    
    acc_div = 0
    res_cv = []
    res_db = []
    
    cum_prem = 0
    
    for t in range(len(g_cv)):
        cum_prem += (real_prem if t < 20 else 0)
        
        # 身故保證：取 Max(查表, 累積保費)
        # 這是關鍵！修正了身故金過低的問題
        g_db_actual = max(g_db_table[t], cum_prem)
        
        # 年度紅利：(前一年CV + 累積紅利 + 當年保費) * 利差
        prev_cv = g_cv[t-1] if t > 0 else 0
        base = prev_cv + acc_div + (real_prem if t < 20 else 0)
        div = base * spread
        
        acc_div = acc_div * (1 + declared) + div
        
        # 終期紅利
        # 係數隨年期成長 (模擬)
        tf_cv = 0
        tf_db = 0
        if t >= 10:
            # 簡單模擬：第10年開始，第20年達標
            ratio = min(1.0, (t - 5) / 15)
            tf_cv = (g_cv[t] + acc_div) * (term_rate_cv * ratio)
            tf_db = (g_cv[t] + acc_div) * (term_rate_db * ratio)
            
        total_cv = g_cv[t] + acc_div + tf_cv
        total_db = g_db_actual + acc_div + tf_db
        
        res_cv.append(total_cv)
        res_db.append(total_db)
        
    return real_prem, disc, res_cv, res_db, g_cv, acc_div

def get_loan_limit(y):
    if y>=12: return 0.9
    if y>=10: return 0.85
    if y>=8: return 0.8
    if y>=6: return 0.75
    return 0.7

# --- 4. 介面 ---
with st.sidebar:
    st.header("⚙️ 設定")
    f = st.file_uploader("上傳 PDATA.csv", type='csv')
    
    st.divider()
    age = st.number_input("年齡", 36)
    sex = st.radio("性別", ["男", "女"], 0)
    sex_code = 1 if sex=="男" else 2
    face = st.number_input("保額 (萬)", 210, step=10)
    
    st.divider()
    st.markdown("### 🔧 參數微調 (已校正)")
    dec_rate = st.number_input("宣告利率", 1.75, step=0.05) / 100
    
    # 預設值已改為 2.0% 和 46%/80%
    loading = st.slider("額外分紅加成 (Loading)", 0.0, 3.0, 1.98, 0.01) / 100
    term_cv = st.slider("終期紅利 (解約)", 0.0, 1.0, 0.46, 0.01)
    term_db = st.slider("終期紅利 (身故)", 0.0, 1.0, 0.80, 0.01)
    
    st.divider()
    mode = st.radio("模式", ["以息養險", "階梯槓桿"])

# --- 5. 執行 ---
st.title("💎 PAI 策略全能計算機")

if f:
    data = load_data(f)
    res = calc_policy(age, sex_code, face, data, dec_rate, loading, term_cv, term_db)
    
    if res:
        prem, disc, cvs, dbs, g_cvs, final_acc = res
        
        st.markdown(f"""
        <div class="metric-card">
            <h3>💰 試算結果 (保額 {face} 萬)</h3>
            實繳年繳：<b style="color:#cf1322">${prem:,.0f}</b> (折扣 {disc*100}%)<br>
            20年總繳：${prem*20:,.0f}
        </div>
        """, unsafe_allow_html=True)
        
        # 表格與策略
        rows = []
        raws = []
        loan = 0
        fund = 0
        cash_out = 0
        wealth = 0
        last_loan_y = 0
        
        max_y = min(len(cvs), 100-age)
        
        for t in range(max_y):
            py = t + 1
            curr_age = age + py
            
            c_cv = cvs[t]
            c_db = dbs[t]
            
            # 借款
            limit = get_loan_limit(py)
            do_loan = False
            if curr_age <= 65:
                can_loan = c_cv * limit
                new = can_loan - loan
                if new >= 300000 and ((last_loan_y==0) or (py-last_loan_y>=3)):
                    loan += new
                    fund += new * 0.95
                    last_loan_y = py
                    do_loan = True
            
            income = fund * 0.07
            pay_nom = prem if py <= 20 else 0
            
            r = {"年度": py, "年齡": f"{curr_age} {'⚡' if do_loan else ''}"}
            l_str = f"-${loan:,.0f}" + (f" ({int(limit*100)}%)" if do_loan else "")
            
            if "以息" in mode:
                real_pay = pay_nom - income
                if real_pay > 0: cash_out = cash_out
                else: cash_out += abs(real_pay)
                
                net = c_cv + fund + cash_out - loan
                d_total = c_db + fund - loan
                
                r["應繳"] = f"${pay_nom:,.0f}"
                r["抵扣"] = f"${income:,.0f}"
                r["實繳"] = f"${real_pay:,.0f}" if real_pay>0 else f"領 ${abs(real_pay):,.0f}"
                r["解約金"] = f"${c_cv:,.0f}"
                r["借款"] = l_str
                r["淨資產"] = f"${net:,.0f}"
                r["身故金"] = f"${d_total:,.0f}"
                
                raws.append({"loan": do_loan, "pay": real_pay, "net": net, "db": d_total})
                
            else:
                wealth = (wealth * 1.07) + income
                net = c_cv + fund + wealth - loan
                d_total = c_db + fund + wealth - loan
                
                r["存入"] = f"${pay_nom:,.0f}"
                r["累積存入"] = f"${(prem*py if py<=20 else prem*20):,.0f}"
                r["解約金"] = f"${c_cv:,.0f}"
                r["借款"] = l_str
                r["基金"] = f"${fund:,.0f}"
                r["累積配息"] = f"${wealth:,.0f}"
                r["淨資產"] = f"${net:,.0f}"
                r["身故金"] = f"${d_total:,.0f}"
                
                raws.append({"loan": do_loan, "net": net, "db": d_total})
            
            rows.append(r)
            
            if curr_age == 65:
                v_snap = {"cv": c_cv, "loan": loan, "fund": fund, "total": net}

        # 顯示
        df_show = pd.DataFrame(rows)
        st.dataframe(df_show, use_container_width=True, height=600, hide_index=True)
        
        # 驗證
        if 'v_snap' in locals():
            v = v_snap
            st.markdown(f"""
            <div class="verify-box">
                <div class="verify-row"><span>65歲 解約金</span> <span>${v['cv']:,.0f}</span></div>
                <div class="verify-row"><span>基金本金</span> <span>${v['fund']:,.0f}</span></div>
                <div class="verify-row" style="color:#cf1322"><span>保單借款</span> <span>-${v['loan']:,.0f}</span></div>
                <div class="verify-total"><span>總淨資產</span> <span>${v['total']:,.0f}</span></div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.error("查無資料")
else:
    st.info("請上傳檔案")
