import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="PAI 策略全能計算機",
    page_icon="📊",
    layout="wide"
)

# --- 1.5 密碼驗證模組 ---
def check_password():
    """Returns `True` if the user had a correct password."""
    ACTUAL_PASSWORD = "TP927" # <--- 密碼設定

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

# --- 3. 核心資料與函式 (全新改寫) ---

@st.cache_data
def load_policy_data(uploaded_file):
    """
    從上傳的 PDATA.csv 解析費率、身故金與解約金表
    """
    if uploaded_file is None:
        return None

    # 讀取 CSV，header=None 因為格式混亂
    df = pd.read_csv(uploaded_file, header=None)
    
    data = {
        "premium_rate": {},  # { "gender_age": rate }
        "death_benefit": {}, # { "gender_age": [year1, year2...] }
        "cash_value": {}     # { "gender_age": [year1, year2...] }
    }
    
    # --- 1. 解析保費 (Premium) ---
    # 假設保費在最上方，直到 'DIE' 出現
    # 根據您的檔案結構：性別=col 5, 年齡=col 7, 保費=col 10
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
            rate = float(row[10]) # 單位保費
            key = f"{sex}_{age}"
            data["premium_rate"][key] = rate
        except:
            continue

    # --- 2. 解析身故金 (DIE) ---
    # 從 DIE 標籤後 2 行開始讀數據
    # 格式：性別=col 131, 年齡=col 132, 數值從 col 134 開始
    try:
        pv_start_indices = df[df[129] == 'PV0'].index # 找下一個區塊
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
            # 取出歷年數值，去除逗號轉 float
            values = row[134:].dropna().astype(str).str.replace(',', '').astype(float).tolist()
            key = f"{sex}_{age}"
            data["death_benefit"][key] = values
        except:
            continue

    # --- 3. 解析解約金 (PV) ---
    # 找 PV 標籤 (通常在下方)
    try:
        real_pv_indices = df[df[129] == 'PV'].index
        # 這裡要小心，有時候會有 PV0 和 PV，我們要找年度末保價金通常是 PV
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

def get_policy_values(age, gender_code, annual_premium, data_dict):
    """
    根據年齡、性別、保費，回傳該保單的歷年解約金與身故金陣列
    gender_code: 1=男, 2=女
    """
    if data_dict is None:
        return [], []
        
    key = f"{gender_code}_{age}"
    
    # 1. 取得費率 (每單位保額的保費)
    rate = data_dict["premium_rate"].get(key)
    
    if not rate or rate == 0:
        return [], [] # 查無資料
        
    # 2. 反推投保單位數 (Multiplier)
    # 公式：總保費 = (投保單位 / 單位基準) * 費率
    # 所以：投保單位 / 單位基準 = 總保費 / 費率
    # 而表上的解約金也是每單位的數值，所以直接乘上這個倍數即可
    # 假設表定費率是每萬元保額，或者是每百元，這裡直接用比例法最準：
    multiplier = annual_premium / rate
    
    # 3. 計算歷年數值
    raw_cv = data_dict["cash_value"].get(key, [])
    raw_die = data_dict["death_benefit"].get(key, [])
    
    # 乘上倍數
    final_cv = [val * multiplier for val in raw_cv]
    final_die = [val * multiplier for val in raw_die]
    
    return final_cv, final_die

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
    
    # 檔案上傳區
    st.markdown("### 1. 資料庫載入")
    uploaded_file = st.file_uploader("請上傳 PDATA.csv", type=['csv'])
    if uploaded_file:
        st.success("✅ 資料已讀取")
    else:
        st.warning("⚠️ 請上傳檔案以啟動計算")
        
    st.divider()
    
    # 輸入參數
    st.markdown("### 2. 投保條件")
    start_age = st.number_input("🧑‍💼 投保年齡", value=25, min_value=0, max_value=80)
    gender = st.radio("性別", ["男性", "女性"], horizontal=True)
    gender_code = 1 if gender == "男性" else 2
    
    monthly_deposit = st.number_input("💵 月存金額", value=10000, step=1000)
    st.divider()
    
    mode = st.radio("🔄 選擇策略模式", ["🛡️ 以息養險 (折抵保費)", "🚀 階梯槓桿 (複利滾存)"])
    st.info("💡 說明：\n\n**以息養險**：配息優先折抵保費，多餘領現。\n\n**階梯槓桿**：配息全數再投入，追求資產最大化。\n\n**⚡ 借款規則**：\n1. 可貸額度需滿 30 萬。\n2. 之後每滿 3 年且額度足夠才借。")

# --- 5. 主畫面 ---
st.title("📊 PAI 策略全能計算機")

IMG_OFFSET = "https://i.postimg.cc/9Mwkq4c1/Gemini-Generated-Image-57o51457o51457o5.png"
IMG_COMPOUND = "https://i.postimg.cc/SxKDMXr6/Gemini-Generated-Image-p41a4fp41a4fp41a.png"

if "以息養險" in mode:
    st.image(IMG_OFFSET, use_container_width=True)
    current_mode = "offset"
else:
    st.image(IMG_COMPOUND, use_container_width=True)
    current_mode = "compound"

# --- 6. 計算邏輯 ---

# 載入資料
policy_data = load_policy_data(uploaded_file)

if policy_data is None:
    st.warning("👈 請先在左側上傳 PDATA.csv 檔案才能開始計算！")
    st.stop()

annual_deposit = monthly_deposit * 12
deposit_years = 20
fee_rate = 0.05
MIN_LOAN_THRESHOLD = 300000  # 最低借款門檻
LOAN_INTERVAL_YEARS = 3      # 借款間隔年數

# 取得該年齡對應的解約金與身故金表
cv_list, die_list = get_policy_values(start_age, gender_code, annual_deposit, policy_data)

if not cv_list:
    st.error(f"❌ 找不到 {start_age} 歲 {gender} 的費率資料，請確認 CSV 內容。")
    st.stop()

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

# 迴圈計算 (計算到 100 歲或資料結束)
max_years = min(len(cv_list), 100 - start_age)

for t in range(max_years):
    policy_year = t + 1
    current_age = start_age + policy_year
    
    # 從查表結果取得當年度數值
    cv = cv_list[t]
    death_benefit_base = die_list[t]
    
    limit_rate = get_loan_limit_rate(policy_year)
      
    # --- 新版借款邏輯 ---
    loan_tag = ""
    is_borrowing_year = False # 標記今年是否有借款

    # 只有在 65 歲以前才執行借款策略
    if current_age <= 65:
        max_loan = cv * limit_rate
        new_borrow = max_loan - current_loan
        
        # 條件 1: 可借金額大於 30 萬
        is_amount_ok = new_borrow >= MIN_LOAN_THRESHOLD
        
        # 條件 2: 從未借過款 OR 距離上次借款已滿 3 年
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

    # 處理借款顯示字串：如果有借款，加上成數
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
        
        # 以息養險模式下的總身故金：保單身故 + 基金本金 - 借款
        total_death_benefit = death_benefit_base + current_fund - current_loan
        
        row_display["年齡"] = f"{current_age} {loan_tag}"
        row_display["①應繳年保費"] = format_money(nominal_premium)
        row_display["②配息抵扣"] = format_money(net_income)
        row_display["③實繳金額"] = format_money(display_val, is_receive_column=True)
        row_display["④累積實繳"] = format_money(accum_real_cost)
        row_display["⑤PAI解約金"] = format_money(cv)
        row_display["⑥保單借款"] = loan_display_str 
        row_display["⑦基金本金"] = format_money(current_fund)
        row_display["⑧總淨資產"] = format_money(total_net_asset)
        row_display["⑨身故金"] = format_money(total_death_benefit) # 新增

        row_raw = {"loan_year": loan_tag == "⚡", "real_pay_val": display_val, "net_asset": total_net_asset}

    else:
        actual_deposit = nominal_premium
        acc_deposit = annual_deposit * policy_year if policy_year <= deposit_years else annual_deposit * deposit_years
        accum_net_wealth = (accum_net_wealth * 1.07) + net_income
        total_net_asset = cv + current_fund + accum_net_wealth - current_loan

        # 階梯槓桿模式下的總身故金：保單身故 + 基金本金 + 累積配息 - 借款
        total_death_benefit = death_benefit_base + current_fund + accum_net_wealth - current_loan
        
        row_display["年齡"] = f"{current_age} {loan_tag}"
        row_display["①當年存入"] = format_money(actual_deposit)
        row_display["②累積本金"] = format_money(acc_deposit)
        row_display["③PAI解約金"] = format_money(cv)
        row_display["④保單借款"] = loan_display_str 
        row_display["⑤基金本金"] = format_money(current_fund)
        row_display["⑥年度淨配息"] = format_money(net_income)
        row_display["⑦累積配息(複利)"] = format_money(accum_net_wealth)
        row_display["⑧總淨資產"] = format_money(total_net_asset)
        row_display["⑨身故金"] = format_money(total_death_benefit) # 新增

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
        
        # 總淨資產樣式
        df_style.iloc[i, df_input.columns.get_loc("⑧總淨資產")] += 'background-color: #e6f7ff; color: #096dd9; font-weight: bold;'
        
        # 身故金樣式：暖金背景，深橘金文字
        df_style.iloc[i, df_input.columns.get_loc("⑨身故金")] += 'background-color: #fff7e6; color: #d46b08; font-weight: bold;'
        
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
            <div class="verify-row"><span>[+] PAI 保單現金價值</span> <span>{v_cv}</span></div>
            <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund}</span></div>
            <div class="verify-row" style="color: #c41d7f;"><span>[+] 累積已領回現金 (Cash Out)</span> <span>{v_cash}</span></div>
            <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan}</span></div>
            <div class="verify-total">
                <span>[=] 總淨資產 (Net Worth)</span> <span>{v_total}</span>
            </div>
            <div class="verify-note">💡 說明：此模式配息優先抵扣保費，多餘的現金領回放口袋，適合重視現金流者。</div>
        </div>
        """
    else:
        v_accum = f"${v['accum_wealth']:,.0f}"
        html_content = f"""
        <div class="verify-box">
            <div class="verify-title">🔍 65 歲資產結算驗證</div>
            <div class="verify-row"><span>[+] PAI 保單現金價值</span> <span>{v_cv}</span></div>
            <div class="verify-row"><span>[+] 基金本金</span> <span>{v_fund}</span></div>
            <div class="verify-row" style="color: #722ed1;"><span>[+] 累積配息滾存 (複利)</span> <span>{v_accum}</span></div>
            <div class="verify-row" style="color: #cf1322;"><span>[-] 扣除保單借款</span> <span>{v_loan}</span></div>
            <div class="verify-total">
                <span>[=] 總淨資產 (Net Worth)</span> <span>{v_total}</span>
            </div>
            <div class="verify-note">💡 說明：此模式假設配息全部再投入 (7%複利)，適合追求資產最大化者。</div>
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
