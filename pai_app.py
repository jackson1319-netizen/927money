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
    ACTUAL_PASSWORD = "Fubon" # <--- 密碼設定

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

# --- 3. 核心資料與函式 ---
# PAI 解約金數據
PAI_BASE_DATA = [
    0, 75568, 151906, 229013, 306899, 368190, 429482, 549969, 679495, 815609, 960677, 
    1112453, 1273472, 1441892, 1619008, 1804891, 1999194, 2170489, 2345219, 2525180, 2708683, 
    2796023, 2871780, 2949471, 3030006, 3111221, 3194976, 3280911, 3369035, 3459379, 3552969, 
    3646561, 3744237, 3843884, 3945018, 4049162, 4155962, 4264024, 4375249, 4489180, 4605868, 
    4722041, 4843080, 4964110, 5088924, 5215376, 5344037, 5473126, 5604778, 5738463, 5874202, 
    6011861, 6151926, 6292620, 6434379, 6578609, 6723359, 6870598, 7019910, 7168168, 7319472, 
    7472919, 7626897, 7781843, 7937799, 8096541, 8255893, 8418253, 8583316, 8749459, 8921196, 
    9097991, 9280402, 9471102, 9674587, 9895415, 10142999, 10414816, 10696778, 10992809, 11304075, 
    11632752, 11979388, 12355444, 12765735, 13233318, 13766422
]

# PAI 身故金數據 (年度末身故/完全失能時可領總金額) 
PAI_DEATH_DATA = [
    0, 170000, 340185, 510558, 681120, 858687, 6849302, 6807176, 6772672, 6745104, 6724209, 
    6710612, 6702492, 6701107, 6706363, 6718151, 6735241, 6760773, 6791657, 6828419, 6871177, 
    6915181, 6946482, 6977752, 7009859, 7042364, 7075362, 7109371, 7143494, 7178647, 7214892, 
    7250015, 7288018, 7324779, 7363849, 7402672, 7442997, 7483378, 7525738, 7567382, 7611693, 
    7655608, 7702077, 7747425, 7796685, 7845305, 7895147, 7947001, 8000527, 8055223, 8111151, 
    8168164, 8226834, 8286878, 8350332, 8414295, 8481377, 8549089, 8618573, 8691615, 8766065, 
    8842680, 8923339, 9005279, 9090404, 9178873, 9270456, 9365880, 9463047, 9566182, 9672209, 
    9782518, 9897691, 10018324, 10142410, 10271878, 10408931, 10597577, 10866775, 11149518, 
    11446957, 11761249, 12095401, 12455963, 12847598, 13280185, 13766422
]

BASE_PREMIUM = 120003

def get_pai_cv(year, annual_deposit):
    if year <= 0: return 0
    idx = year if year < len(PAI_BASE_DATA) else len(PAI_BASE_DATA) - 1
    base = PAI_BASE_DATA[idx]
    return base * (annual_deposit / BASE_PREMIUM)

def get_pai_death(year, annual_deposit):
    if year <= 0: return 0
    idx = year if year < len(PAI_DEATH_DATA) else len(PAI_DEATH_DATA) - 1
    base = PAI_DEATH_DATA[idx]
    return base * (annual_deposit / BASE_PREMIUM)

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
    start_age = st.number_input("🧑‍💼 目前年齡", value=25, min_value=0, max_value=80)
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
annual_deposit = monthly_deposit * 12
deposit_years = 20
fee_rate = 0.05
MIN_LOAN_THRESHOLD = 300000  # 最低借款門檻
LOAN_INTERVAL_YEARS = 3      # 借款間隔年數

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

# 迴圈計算
for age in range(start_age + 1, 86):
    policy_year = age - start_age
    cv = get_pai_cv(policy_year, annual_deposit)
    limit_rate = get_loan_limit_rate(policy_year)
     
    # --- 新版借款邏輯 ---
    loan_tag = ""
    is_borrowing_year = False # 標記今年是否有借款

    # 只有在 65 歲以前才執行借款策略
    if age <= 65:
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

    # 計算身故金 (保障 + 投資 - 負債)
    death_benefit_base = get_pai_death(policy_year, annual_deposit)

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
        
        row_display["年齡"] = f"{age} {loan_tag}"
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
        
        row_display["年齡"] = f"{age} {loan_tag}"
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
    
    if age == 65:
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

# --- 8. 驗證區 ---
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
