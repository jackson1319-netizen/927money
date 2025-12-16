import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="PAI 策略全能計算機 (分紅旗艦版)",
    page_icon="💎",
    layout="wide"
)

# --- 1.5 密碼驗證模組 ---
def check_password():
    """Returns `True` if the user had a correct password."""
    ACTUAL_PASSWORD = "TP927" 

    def password_entered():
        if st.session_state["password"] == ACTUAL_PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 請輸入訪問密碼", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 請輸入訪問密碼", type="password", on_change=password_entered, key="password")
        st.error("❌ 密碼錯誤")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- 2. CSS 樣式注入 ---
st.markdown("""
    <style>
    :root {
        --brand-color: #006d75;
        --brand-bg: #e6fffb;
        --text-main: #262626;
        --pay-text: #389e0d;
        --receive-text: #c41d7f;
        --debt-color: #cf1322;
        --asset-bg: #e6f7ff;
        --asset-text: #096dd9;
    }
    h1, h2, h3 { color: var(--brand-color) !important; font-family: -apple-system, sans-serif; }
    .verify-box {
        background-color: #262626;
        color: white;
        padding: 24px;
        border-radius: 10px;
        margin-top: 24px;
        font-family: monospace;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .verify-title { color: #faad14; font-weight: bold; margin-bottom: 15px; border-bottom: 1px solid #434343; padding-bottom: 10px; font-size: 16px; }
    .verify-row { display: flex; justify-content: space-between; margin-bottom: 8px; align-items: center; }
    .verify-total { font-size: 20px; font-weight: bold; color: #52c41a; margin-top: 15px; border-top: 1px solid #555; padding-top: 15px; display: flex; justify-content: space-between; }
    .verify-note { font-size: 13px; color: #8c8c8c; margin-top: 15px; border-top: 1px dashed #434343; padding-top: 10px; }
    .disclaimer-box { margin-top: 40px; padding: 15px; background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 5px; color: #6c757d; font-size: 12px; line-height: 1.5; }
    .disclaimer-title { font-weight: bold; margin-bottom: 5px; display: flex; align-items: center; }
    </style>
""", unsafe_allow_html=True)

# --- 3. 核心資料與函式 (分紅引擎升級) ---

@st.cache_data
def load_policy_data(uploaded_file):
    if uploaded_file is None: return None
    df = pd.read_csv(uploaded_file, header=None)
    data = {"premium_rate": {}, "death_benefit": {}, "cash_value": {}}
    
    # 解析保費
    try:
        die_start = df[df[129] == 'DIE'].index[0] if not df[df[129] == 'DIE'].empty else 444
        premium_df = df.iloc[1:die_start]
        for _, row in premium_df.iterrows():
            try:
                data["premium_rate"][f"{int(row[5])}_{int(row[7])}"] = float(row[10])
            except: continue
    except: pass

    # 解析 DIE & CV
    try:
        die_start = df[df[129] == 'DIE'].index[0]
        pv_start = df[df[129] == 'PV0'].index[0]
        real_pv_start = df[df[129] == 'PV'].index[0]
    except:
        die_start, pv_start, real_pv_start = 444, 867, 1737

    # DIE Table
    die_df = df.iloc[die_start+2 : pv_start]
    for _, row in die_df.iterrows():
        try:
            vals = row[134:].dropna().astype(str).str.replace(',', '').astype(float).tolist()
            data["death_benefit"][f"{int(row[131])}_{int(row[132])}"] = vals
        except: continue

    # PV Table
    pv_df = df.iloc[real_pv_start+2 :]
    for _, row in pv_df.iterrows():
        try:
            vals = row[134:].dropna().astype(str).str.replace(',', '').astype(float).tolist()
            data["cash_value"][f"{int(row[131])}_{int(row[132])}"] = vals
        except: continue
            
    return data

def calculate_discount_rate(face_amount_wan):
    if face_amount_wan >= 200: return 0.015
    elif face_amount_wan >= 100: return 0.01
    else: return 0.0

def calculate_dividends(guaranteed_cv_list, annual_premium, declared_rate, assumed_rate, bonus_loading, terminal_rate):
    """
    分紅計算核心：
    1. 累積年度紅利 (Accumulated Annual Dividend)
       - 基礎：(前一年末保價 + 當年度保費)
       - 利率：(宣告 - 預定 + 額外加成)
    2. 終期紅利 (Terminal Dividend)
       - 估算：保單價值 * 終期紅利係數 (通常在第10年後開始顯著)
    """
    accumulated_dividends = []
    terminal_dividends = []
    
    current_acc_div = 0
    payment_years = 20
    
    # 模擬保單價值 (用於計算分紅基數，這裡用累積保費與保證價值的混合估算，以接近真實貢獻度)
    # PAI 的保證價值很低，如果用保證價值算分紅會太少。
    # 通常分紅基數 (Asset Share) 會接近累積保費扣除費用。
    # 我們這裡用 "累積實繳保費" 作為分紅基數的權重參考。
    
    cum_premium = 0
    
    for t in range(len(guaranteed_cv_list)):
        curr_prem = annual_premium if t < payment_years else 0
        cum_premium += curr_prem
        
        # 1. 年度紅利計算
        # 簡易公式：(分紅基數) * 利差
        # 假設分紅基數隨著累積保費成長 (比純保價金更接近資產份額)
        dividend_base = cum_premium * 0.9 # 假設扣除10%費用作為基數
        
        spread = max(0, declared_rate - assumed_rate + bonus_loading)
        annual_div = dividend_base * spread
        
        # 累積紅利滾存 (以宣告利率複利)
        current_acc_div = current_acc_div * (1 + declared_rate) + annual_div
        accumulated_dividends.append(current_acc_div)
        
        # 2. 終期紅利計算
        # 假設第 6 年起開始累積，第 20 年達到高峰
        # 終期紅利通常是 Asset Share 與 Guaranteed CV 的差額的一定比例
        # 我們用 "累積紅利" 的倍數來模擬，或者直接用 Total Value 的比例
        
        term_factor = 0
        if t >= 10:
            # 隨年期增加係數 (模擬長期持有獎勵)
            term_factor = terminal_rate * ((t - 5) / 15) 
            
        term_div = (guaranteed_cv_list[t] + current_acc_div) * term_factor
        terminal_dividends.append(term_div)
        
    return accumulated_dividends, terminal_dividends

def get_full_policy_values(age, gender_code, face_amount_wan, data, declared_rate, bonus_loading, terminal_rate):
    key = f"{gender_code}_{age}"
    
    # 費率
    rate = data["premium_rate"].get(key, 0)
    if rate == 0: return None
    
    # 單位換算 (PDATA 基準可能是 1萬元保額)
    units = face_amount_wan # e.g. 210
    
    # 1. 保費計算
    original_prem = rate * units
    disc_rate = calculate_discount_rate(face_amount_wan)
    final_prem = original_prem * (1 - disc_rate)
    
    # 2. 查表 (保證值)
    raw_cv = data["cash_value"].get(key, [])
    raw_die = data["death_benefit"].get(key, [])
    
    # PAI 特殊處理：PDATA 的 CV/DIE 數值需要乘上單位數
    # 根據驗證，PDATA 的數值 (如 4308) 乘上單位數 (210) 得到的只是保證值，遠小於總值。
    guaranteed_cv = [v * units for v in raw_cv]
    guaranteed_die = [v * units for v in raw_die]
    
    # 3. 分紅計算
    assumed_rate = 0.01 # PAI 預定利率
    acc_divs, term_divs = calculate_dividends(
        guaranteed_cv, final_prem, declared_rate, assumed_rate, bonus_loading, terminal_rate
    )
    
    # 4. 總值合併
    total_cv = []
    total_die = []
    
    for i in range(len(guaranteed_cv)):
        # 解約金 = 保證 + 累積紅利 + 終期紅利
        t_cv = guaranteed_cv[i] + acc_divs[i] + term_divs[i]
        total_cv.append(t_cv)
        
        # 身故金 = 保證 + 累積紅利 + 終期紅利 (PAI 通常身故也有終期紅利)
        t_die = guaranteed_die[i] + acc_divs[i] + term_divs[i]
        total_die.append(t_die)
        
    return final_prem, disc_rate, total_cv, total_die, guaranteed_cv, acc_divs, term_divs

def get_loan_limit_rate(year):
    if year >= 12: return 0.90
    if year >= 10: return 0.85
    if year >= 8: return 0.80
    if year >= 6: return 0.75
    return 0.70

def format_money(val, is_receive_column=False):
    if val == 0: return "-"
    abs_val = abs(val)
    money_str = f"${abs_val:,.0f}"
    if is_receive_column and val < 0: return f"領 {money_str}"
    elif val < 0: return f"-{money_str}"
    return money_str

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ 參數設定")
    
    uploaded_file = st.file_uploader("請上傳 PDATA.csv", type=['csv'])
    if uploaded_file: st.success("✅ 資料已讀取")
    else: st.warning("⚠️ 請上傳檔案")
        
    st.divider()
    
    st.markdown("### 1. 投保條件")
    start_age = st.number_input("🧑‍💼 投保年齡", value=36, min_value=0, max_value=80)
    gender = st.radio("性別", ["男性", "女性"], horizontal=True)
    gender_code = 1 if gender == "男性" else 2
    face_amount_wan = st.number_input("🛡️ 投保保額 (萬元)", value=210, step=10, help="輸入 200 萬以上自動適用 1.5% 折扣")
    
    st.divider()
    
    st.markdown("### 2. 紅利校正 (重要!)")
    st.caption("請調整下方滑桿，使第20年的數值與您的試算表相符。")
    declared_rate = st.number_input("📈 宣告利率 (%)", value=1.75, step=0.05) / 100
    
    # 校正滑桿
    bonus_loading = st.slider("✨ 額外分紅加成 (死差/費差)", 0.0, 2.0, 0.8, 0.1, help="調整年度紅利的累積速度") / 100
    terminal_rate = st.slider("🎁 終期紅利預估 (%)", 0.0, 100.0, 35.0, 5.0, help="解約時額外給付的比例") / 100
    
    st.divider()
    mode = st.radio("🔄 策略模式", ["🛡️ 以息養險", "🚀 階梯槓桿"])

# --- 5. 主畫面 ---
st.title("💎 PAI 策略全能計算機 (分紅旗艦版)")

policy_data = load_policy_data(uploaded_file)
if policy_data is None: st.stop()

# 計算
result = get_full_policy_values(
    start_age, gender_code, face_amount_wan, policy_data, declared_rate, bonus_loading, terminal_rate
)

if result is None:
    st.error("查無費率資料")
    st.stop()
    
annual_prem, disc_rate, cv_list, die_list, g_cv_list, acc_div_list, term_div_list = result

# 資訊卡
st.markdown(f"""
<div style="padding: 15px; background-color: #f6ffed; border: 1px solid #b7eb8f; border-radius: 5px; margin-bottom: 20px;">
    <h3 style="margin:0; color: #389e0d;">💰 保費與紅利試算結果</h3>
    <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-top: 10px; font-size: 16px;">
        <div><b>投保保額：</b> {face_amount_wan} 萬元</div>
        <div><b>實繳年繳：</b> <span style="color: #cf1322; font-weight:bold;">${annual_prem:,.0f}</span></div>
        <div><b>折扣率：</b> {disc_rate*100}%</div>
        <div><b>分紅加成：</b> {bonus_loading*100:.1f}%</div>
        <div><b>終期係數：</b> {terminal_rate*100:.0f}%</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 試算表邏輯
annual_deposit = annual_prem
deposit_years = 20
fee_rate = 0.05
MIN_LOAN = 300000
LOAN_INTERVAL = 3

data_rows = []
raw_data = []
curr_loan = 0
curr_fund = 0
acc_cash_out = 0
acc_wealth = 0
last_borrow = 0

max_years = min(len(cv_list), 100 - start_age)

for t in range(max_years):
    py = t + 1
    age = start_age + py
    
    cv = cv_list[t]
    db = die_list[t]
    
    # 借款邏輯
    limit = get_loan_limit_rate(py)
    loan_tag = ""
    is_borrow = False
    
    if age <= 65:
        max_loan = cv * limit
        new_borrow = max_loan - curr_loan
        if new_borrow >= MIN_LOAN and ((last_borrow==0) or (py - last_borrow >= LOAN_INTERVAL)):
            curr_loan += new_borrow
            curr_fund += new_borrow * (1 - fee_rate)
            last_borrow = py
            loan_tag = "⚡"
            is_borrow = True
            
    net_income = curr_fund * 0.07
    nominal_prem = annual_deposit if py <= deposit_years else 0
    
    row = {"保單年度": py, "年齡": f"{age} {loan_tag}"}
    
    loan_str = format_money(-curr_loan)
    if is_borrow: loan_str += f" ({int(limit*100)}%)"
    
    if "以息養險" in mode:
        actual_pay = nominal_prem - net_income
        if actual_pay > 0: acc_cash_out = acc_cash_out # No change (cost)
        else: acc_cash_out += abs(actual_pay)
        
        total_asset = cv + curr_fund + acc_cash_out - curr_loan
        total_db = db + curr_fund - curr_loan
        
        row["①應繳保費"] = format_money(nominal_prem)
        row["②配息抵扣"] = format_money(net_income)
        row["③實繳金額"] = format_money(actual_pay, True)
        row["④解約金(含紅利)"] = format_money(cv)
        row["⑤保單借款"] = loan_str
        row["⑥總淨資產"] = format_money(total_asset)
        row["⑦身故金(含紅利)"] = format_money(total_db)
        
        raw_data.append({"loan": is_borrow, "pay": actual_pay, "net": total_asset})
    else:
        acc_wealth = (acc_wealth * 1.07) + net_income
        total_asset = cv + curr_fund + acc_wealth - curr_loan
        total_db = db + curr_fund + acc_wealth - curr_loan
        
        row["①當年存入"] = format_money(nominal_prem)
        row["②累積存入"] = format_money(nominal_prem * py if py<=20 else nominal_prem*20)
        row["③解約金(含紅利)"] = format_money(cv)
        row["④保單借款"] = loan_str
        row["⑤基金本金"] = format_money(curr_fund)
        row["⑥累積配息(複利)"] = format_money(acc_wealth)
        row["⑦總淨資產"] = format_money(total_asset)
        row["⑧身故金(含紅利)"] = format_money(total_db)
        
        raw_data.append({"loan": is_borrow, "net": total_asset})
        
    data_rows.append(row)
    
    if age == 65:
        verify_snapshot = {"cv": cv, "loan": curr_loan, "fund": curr_fund, "total": total_asset}

# 表格顯示
df_res = pd.DataFrame(data_rows)
st.dataframe(df_res, use_container_width=True, height=600, hide_index=True)

# 驗證區
if 'verify_snapshot' in locals():
    v = verify_snapshot
    st.markdown(f"""
    <div class="verify-box">
        <div class="verify-title">🔍 65 歲資產結算驗證</div>
        <div class="verify-row"><span>[+] 解約金(含紅利)</span> <span>${v['cv']:,.0f}</span></div>
        <div class="verify-row"><span>[+] 基金本金</span> <span>${v['fund']:,.0f}</span></div>
        <div class="verify-row" style="color: #cf1322;"><span>[-] 保單借款</span> <span>-${v['loan']:,.0f}</span></div>
        <div class="verify-total"><span>[=] 總淨資產</span> <span>${v['total']:,.0f}</span></div>
    </div>
    """, unsafe_allow_html=True)
