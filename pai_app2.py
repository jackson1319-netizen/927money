import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="PAI 策略全能計算機 (修正版)",
    page_icon="📊",
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

# --- 3. 核心資料與函式 (含折扣與紅利) ---

@st.cache_data
def load_policy_data(uploaded_file):
    """
    從上傳的 PDATA.csv 解析費率、身故金與解約金表
    """
    if uploaded_file is None:
        return None

    df = pd.read_csv(uploaded_file, header=None)
    
    data = {
        "premium_rate": {},  # { "gender_age": rate_per_10k }
        "death_benefit": {}, # { "gender_age": [year1, year2...] per 10k SA }
        "cash_value": {}     # { "gender_age": [year1, year2...] per 10k SA }
    }
    
    # --- 1. 解析保費 (Premium) ---
    try:
        die_start_indices = df[df[129] == 'DIE'].index
        die_start_idx = die_start_indices[0] if not die_start_indices.empty else 444
    except:
        die_start_idx = 444
        
    premium_df = df.iloc[1:die_start_idx]
    for _, row in premium_df.iterrows():
        try:
            sex = int(row[5]) # 1=男, 2=女
            age = int(row[7])
            rate = float(row[10])
            key = f"{sex}_{age}"
            data["premium_rate"][key] = rate
        except:
            continue

    # --- 2. 解析身故金 (DIE) ---
    try:
        pv_start_indices = df[df[129] == 'PV0'].index 
        if pv_start_indices.empty:
            pv_start_indices = df[df[129] == 'PV'].index
        pv_start_idx = pv_start_indices[0] if not pv_start_indices.empty else 867
    except:
        pv_start_idx = 867

    die_df = df.iloc[die_start_idx+2 : pv_start_idx]
    for _, row in die_df.iterrows():
        try:
            sex = int(row[131])
            age = int(row[132])
            values = row[134:].dropna().astype(str).str.replace(',', '').astype(float).tolist()
            key = f"{sex}_{age}"
            data["death_benefit"][key] = values
        except:
            continue

    # --- 3. 解析解約金 (PV) ---
    try:
        real_pv_indices = df[df[129] == 'PV'].index
        real_pv_start = real_pv_indices[0] if not real_pv_indices.empty else 1737
    except:
        real_pv_start = 1737
    
    pv_df = df.iloc[real_pv_start+2 :]
    for _, row in pv_df.iterrows():
        try:
            sex = int(row[131])
            age = int(row[132])
            values = row[134:].dropna().astype(str).str.replace(',', '').astype(float).tolist()
            key = f"{sex}_{age}"
            data["cash_value"][key] = values
        except:
            continue
            
    return data

def calculate_discount_rate(face_amount_wan):
    """
    計算高保額折扣率
    規則假設：
    < 100萬: 0%
    100萬 ~ 200萬(不含): 1.0%
    >= 200萬: 1.5%
    """
    if face_amount_wan >= 200:
        return 0.015
    elif face_amount_wan >= 100:
        return 0.01
    else:
        return 0.0

def calculate_dividends(guaranteed_cv_list, annual_premium_discounted, declared_rate=0.0175, assumed_rate=0.01):
    """
    計算累積年度紅利 (Accumulated Annual Dividends)
    公式近似：(前一年末保價 + 當年度實繳保費) * (宣告 - 預定)
    """
    accumulated_dividends = []
    current_acc_div = 0
    
    # 假設繳費年期 20 年 (影響分紅本金)
    payment_years = 20 
    
    for t in range(len(guaranteed_cv_list)):
        # 前一年末保價 (第1年是0)
        prev_pv = guaranteed_cv_list[t-1] if t > 0 else 0
        
        # 當年度實繳保費 (繳費期內才算)
        curr_prem = annual_premium_discounted if t < payment_years else 0
        
        # 利差分紅 (Interest Spread Dividend)
        # 這裡用 (期初準備金 + 保費) * 利差 來估算
        # 期初準備金近似於 前一年末保價 + 累積紅利
        base_for_interest = prev_pv + current_acc_div + curr_prem
        
        dividend = base_for_interest * (declared_rate - assumed_rate)
        
        if dividend < 0: dividend = 0
        
        # 累積紅利滾存 (本金+新紅利)
        # 注意：通常累積紅利本身也會以宣告利率滾存
        current_acc_div = current_acc_div * (1 + declared_rate) + dividend
        
        accumulated_dividends.append(current_acc_div)
        
    return accumulated_dividends

def get_policy_values_with_dividends(age, gender_code, face_amount, data_dict, declared_rate, assumed_rate):
    """
    整合計算：保費(含折扣) + 保證值 + 紅利
    """
    if data_dict is None:
        return 0, 0, 0, [], []
        
    key = f"{gender_code}_{age}"
    
    # 1. 取得基本費率
    rate_per_10k = data_dict["premium_rate"].get(key, 0)
    if rate_per_10k == 0: return 0, 0, 0, [], []
    
    # 2. 計算原始保費
    face_amount_wan = face_amount / 10000
    units = face_amount_wan # 單位數
    original_premium = rate_per_10k * units
    
    # 3. 計算折扣
    discount_rate = calculate_discount_rate(face_amount_wan)
    discounted_premium = original_premium * (1 - discount_rate)
    
    # 4. 取得查表保證值
    raw_cv = data_dict["cash_value"].get(key, [])
    raw_die = data_dict["death_benefit"].get(key, [])
    
    guaranteed_cv = [val * units for val in raw_cv]
    guaranteed_die = [val * units for val in raw_die]
    
    # 5. 計算紅利 (使用折扣後的實繳保費來算貢獻度嗎？通常是用表定保費算準備金，但利差是用資產份額。
    # 為求保守與精確，我們用 "保證解約金" 代表 "資產份額" 的底，加上 "折扣後保費" 的利差)
    acc_div_list = calculate_dividends(guaranteed_cv, discounted_premium, declared_rate, assumed_rate)
    
    # 6. 合併總值
    total_cv = [g + d for g, d in zip(guaranteed_cv, acc_div_list)]
    total_die = [g + d for g, d in zip(guaranteed_die, acc_div_list)]
    
    return original_premium, discounted_premium, discount_rate, total_cv, total_die

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
    
    st.markdown("### 1. 資料庫載入")
    uploaded_file = st.file_uploader("請上傳 PDATA.csv", type=['csv'])
    if uploaded_file:
        st.success("✅ 資料已讀取")
    else:
        st.warning("⚠️ 請上傳檔案以啟動計算")
        
    st.divider()
    
    st.markdown("### 2. 投保條件")
    start_age = st.number_input("🧑‍💼 投保年齡", value=25, min_value=0, max_value=80)
    gender = st.radio("性別", ["男性", "女性"], horizontal=True)
    gender_code = 1 if gender == "男性" else 2
    
    face_amount_wan = st.number_input("🛡️ 投保保額 (萬元)", value=100, step=10, help="輸入 200 萬以上自動適用 1.5% 折扣")
    face_amount = face_amount_wan * 10000
    
    st.divider()
    
    st.markdown("### 3. 紅利參數")
    declared_rate = st.number_input("📈 宣告利率 (%)", value=1.75, step=0.05) / 100
    assumed_rate = 0.01 # 預定利率固定 1%
    
    st.divider()
    
    mode = st.radio("🔄 選擇策略模式", ["🛡️ 以息養險 (折抵保費)", "🚀 階梯槓桿 (複利滾存)"])
    st.info("💡 說明：\n\n**以息養險**：配息優先折抵保費，多餘領現。\n\n**階梯槓桿**：配息全數再投入，追求資產最大化。\n\n**⚡ 借款規則**：\n1. 可貸額度需滿 30 萬。\n2. 之後每滿 3 年且額度足夠才借。")

# --- 5. 主畫面 ---
st.title("📊 PAI 策略全能計算機 (修正版)")

IMG_OFFSET = "https://i.postimg.cc/9Mwkq4c1/Gemini-Generated-Image-57o51457o51457o5.png"
IMG_COMPOUND = "https://i.postimg.cc/SxKDMXr6/Gemini-Generated-Image-p41a4fp41a4fp41a.png"

if "以息養險" in mode:
    st.image(IMG_OFFSET, use_container_width=True)
    current_mode = "offset"
else:
    st.image(IMG_COMPOUND, use_container_width=True)
    current_mode = "compound"

# --- 6. 計算邏輯 ---

policy_data = load_policy_data(uploaded_file)

if policy_data is None:
    st.warning("👈 請先在左側上傳 PDATA.csv 檔案才能開始計算！")
    st.stop()

# [修正點] 呼叫含紅利與折扣的計算函式
orig_prem, annual_premium, disc_rate, cv_list, die_list = get_policy_values_with_dividends(
    start_age, gender_code, face_amount, policy_data, declared_rate, assumed_rate
)

if not cv_list:
    st.error(f"❌ 找不到 {start_age} 歲 {gender} 的費率資料，請確認 CSV 內容。")
    st.stop()

# 顯示保費與折扣資訊區塊
st.markdown(f"""
<div style="padding: 15px; background-color: #f6ffed; border: 1px solid #b7eb8f; border-radius: 5px; margin-bottom: 20px;">
    <h3 style="margin:0; color: #389e0d;">💰 保費與折扣試算</h3>
    <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-top: 10px; font-size: 16px;">
        <div><b>投保保額：</b> {face_amount_wan} 萬元</div>
        <div><b>原始保費：</b> ${orig_prem:,.0f}</div>
        <div><b>適用折扣：</b> <span style="color: #d46b08; font-weight:bold;">{disc_rate*100}%</span></div>
        <div><b>實繳年繳：</b> <span style="color: #cf1322; font-weight:bold; font-size: 18px;">${annual_premium:,.0f}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

annual_deposit = annual_premium
deposit_years = 20
fee_rate = 0.05
MIN_LOAN_THRESHOLD = 300000  
LOAN_INTERVAL_YEARS = 3      

data_rows = []
raw_data_rows = [] 
current_loan = 0
current_fund = 0
accum_cash_out = 0  
accum_net_wealth = 0 
accum_real_cost = 0 
last_borrow_year = 0 

is_monthly_pay = False
if current_mode == "offset":
    col_toggle, _ = st.columns([0.3, 0.7])
    with col_toggle:
        is_monthly_pay = st.toggle("切換為「月繳」顯示", value=False)

max_years = min(len(cv_list), 100 - start_age)

for t in range(max_years):
    policy_year = t + 1
    current_age = start_age + policy_year
    
    cv = cv_list[t]
    death_benefit_base = die_list[t]
    
    limit_rate = get_loan_limit_rate(policy_year)
      
    # --- 借款邏輯 ---
    loan_tag = ""
    is_borrowing_year = False 

    if current_age <= 65:
        max_loan = cv * limit_rate
        new_borrow = max_loan - current_loan
        
        is_amount_ok = new_borrow >= MIN_LOAN_THRESHOLD
        is_time_ok = (last_borrow_year == 0) or ((policy_year - last_borrow_year) >= LOAN_INTERVAL_YEARS)
        
        if is_amount_ok and is_time_ok:
            current_loan += new_borrow
            current_fund += new_borrow * (1 - fee_rate)
            last_borrow_year = policy_year 
            loan_tag = "⚡"
            is_borrowing_year = True

    net_income = current_fund * 0.07
    nominal_premium = annual_deposit if policy_year <= deposit_years else 0
    total_net_asset = 0

    row_display = {}
    row_raw = {} 

    loan_display_str = format_money(-current_loan)
    if is_borrowing_year:
        loan_display_str += f" ({int(limit_rate*100)}%)"

    row_display["保單年度"] = policy_year

    if current_mode == "offset":
        actual_pay_yearly = nominal_premium - net_income
        if actual_pay_yearly > 0: accum_real_cost += actual_pay_yearly
        else: accum_cash_out += abs(actual_pay_yearly)

        total_net_asset = cv + current_fund + accum_cash_out - current_loan
        display_val = actual_pay_yearly / 12 if is_monthly_pay else actual_pay_yearly
        
        total_death_benefit = death_benefit_base + current_fund - current_loan
        
        row_display["年齡"] = f"{current_age} {loan_tag}"
        row_display["①應繳年保費"] = format_money(nominal_premium)
        row_display["②配息抵扣"] = format_money(net_income)
        row_display["③實繳金額"] = format_money(display_val, is_receive_column=True)
        row_display["④累積實繳"] = format_money(accum_real_cost)
        row_display["⑤PAI解約金(含紅利)"] = format_money(cv)
        row_display["⑥保單借款"] = loan_display_str 
        row_display["⑦基金本金"] = format_money(current_fund)
        row_display["⑧總淨資產"] = format_money(total_net_asset)
        row_display["⑨身故金(含紅利)"] = format_money(total_death_benefit)

        row_raw = {"loan_year": loan_tag == "⚡", "real_pay_val": display_val, "net_asset": total_net_asset}

    else:
        actual_deposit = nominal_premium
        acc_deposit = annual_deposit * policy_year if policy_year <= deposit_years else annual_deposit * deposit_years
        accum_net_wealth = (accum_net_wealth * 1.07) + net_income
        total_net_asset = cv + current_fund + accum_net_wealth - current_loan

        total_death_benefit = death_benefit_base + current_fund + accum_net_wealth - current_loan
        
        row_display["年齡"] = f"{current_age} {loan_tag}"
        row_display["①當年存入"] = format_money(actual_deposit)
        row_display["②累積本金"] = format_money(acc_deposit)
        row_display["③PAI解約金(含紅利)"] = format_money(cv)
        row_display["④保單借款"] = loan_display_str 
        row_display["⑤基金本金"] = format_money(current_fund)
        row_display["⑥年度淨配息"] = format_money(net_income)
        row_display["⑦累積配息(複利)"] = format_money(accum_net_wealth)
        row_display["⑧總淨資產"] = format_money(total_net_asset)
        row_display["⑨身故金(含紅利)"] = format_money(total_death_benefit)

        row_raw = {"loan_year": loan_tag == "⚡", "net_asset": total_net_asset}

    data_rows.append(row_display)
    raw_data_rows.append(row_raw)
    
    if current_age == 65:
        verify_snapshot = {
            "cv": cv, "loan": current_loan, "fund": current_fund,
            "cash_out": accum_cash_out, "accum_wealth": accum_net_wealth,
            "total": total_net_asset
        }

# --- 7. 表格樣式化 ---
df = pd.DataFrame(data_rows)

def style_dataframe(df_input, raw_data):
    df_style = pd.DataFrame('', index=df_input.index, columns=df_input.columns)
    for i, raw in enumerate(raw_data):
        if raw["loan_year"]:
            df_style.iloc[i, :] = 'background-color: #fffbe6;'
        
        df_style.iloc[i, df_input.columns.get_loc("⑧總淨資產")] += 'background-color: #e6f7ff; color: #096dd9; font-weight: bold;'
        df_style.iloc[i, df_input.columns.get_loc(f"⑨身故金(含紅利)")] += 'background-color: #fff7e6; color: #d46b08; font-weight: bold;'
        
        if current_mode == "offset":
            val = raw["real_pay_val"]
            if val < 0: df_style.iloc[i, df_input.columns.get_loc("③實繳金額")] += 'color: #c41d7f; font-weight: bold;'
            elif val > 0: df_style.iloc[i, df_input.columns.get_loc("③實繳金額")] += 'color: #389e0d;'
            
            df_style.iloc[i, df_input.columns.get_loc("②配息抵扣")] += 'color: #c41d7f;'
            df_style.iloc[i, df_input.columns.get_loc("⑥保單借款")] += 'color: #cf1322;'
        else:
            df_style.iloc[i, df_input.columns.get_loc("⑥年度淨配息")] += 'color: #c41d7f;'
            df_style.iloc[i, df_input.columns.get_loc("⑦累積配息(複利)")] += 'color: #722ed1;'
            
    return df_style

styler = df.style.apply(lambda x: style_dataframe(df, raw_data_rows), axis=None)

st.dataframe(styler, use_container_width=True, height=600, hide_index=True)

# --- 8. 驗證區 (如有資料才顯示) ---
if 'verify_snapshot' in locals():
    v = verify_snapshot
    v_cv = f"${v['cv']:,.0f}"
    v_fund = f"${v['fund']:,.0f}"
    v_loan = f"-${v['loan']:,.0f}"
    v_total = f"${v['total']:,.0f}"

    if current_mode == "offset":
        v_cash = f"${v['cash_out']:,.0f}"
        html_content = f"""
        <div class="verify-box">
            <div class="verify-title">🔍 65 歲資產結算驗證</div>
            <div class="verify-row"><span>[+] PAI 保單現金價值(含紅利)</span> <span>{v_cv}</span></div>
            <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund}</span></div>
            <div class="verify-row" style="color: #c41d7f;"><span>[+] 累積已領回現金 (Cash Out)</span> <span>{v_cash}</span></div>
            <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan}</span></div>
            <div class="verify-total">
                <span>[=] 總淨資產 (Net Worth)</span> <span>{v_total}</span>
            </div>
        </div>
        """
    else:
        v_accum = f"${v['accum_wealth']:,.0f}"
        html_content = f"""
        <div class="verify-box">
            <div class="verify-title">🔍 65 歲資產結算驗證</div>
            <div class="verify-row"><span>[+] PAI 保單現金價值(含紅利)</span> <span>{v_cv}</span></div>
            <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund}</span></div>
            <div class="verify-row" style="color: #722ed1;"><span>[+] 累積配息滾存 (複利)</span> <span>{v_accum}</span></div>
            <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan}</span></div>
            <div class="verify-total">
                <span>[=] 總淨資產 (Net Worth)</span> <span>{v_total}</span>
            </div>
        </div>
        """
    st.markdown(html_content, unsafe_allow_html=True)

# --- 9. 免責聲明 ---
st.markdown("""
<div class="disclaimer-box">
    <div class="disclaimer-title">⚠️ 免責聲明：</div>
    本計算機僅供內部教育訓練與模擬試算使用，並非正式保單條款或銷售文件。<br>
    1. 所有試算數據（如宣告利率、投資報酬率 7% 等）均為<strong>假設值</strong>，僅供參考，不代表未來實際績效，亦不保證最低收益。<br>
    2. 實際保單權利義務請以保險公司正式條款為準。<br>
    3. 投資一定有風險，基金投資有賺有賠，申購前應詳閱公開說明書。<br>
    4. 使用者應自行評估風險，本工具開發者不對任何引用本工具所做出之投資決策負責。
</div>
""", unsafe_allow_html=True)
