import streamlit as st
import pandas as pd
import numpy as np

# --- 1. 頁面基礎設定 ---
st.set_page_config(
    page_title="IAT2 策略全能計算機",
    page_icon="🏦",
    layout="wide"
)

# --- 1.5 密碼驗證模組 ---
def check_password():
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
        --brand-color: #003a8c;
        --brand-bg: #f0f5ff;
        --text-main: #262626;
        --pay-text: #389e0d;
        --receive-text: #c41d7f;
        --debt-color: #cf1322;
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
    </style>
""", unsafe_allow_html=True)

# --- 3. IAT2 資料與核心函式 ---
IAT2_BASE_PREMIUM = 120918
# 根據 PDF 試算表匯入數據 
IAT2_CV_DATA = [
    0, 57241, 161215, 280011, 414148, 563983, 722004, 745788, 762729, 780050, 797711, 
    815762, 834207, 853051, 872256, 892170, 912497, 933250, 954474, 976139, 998284, 
    1020880, 1043933, 1067496, 1091523, 1116366, 1141780, 1167738, 1194193, 1221201, 1248731, 
    1276880, 1305516, 1334739, 1364433, 1395712, 1427683, 1460369, 1493739, 1527863, 1562718, 
    1598291, 1634634, 1671738, 1709575, 1748178, 1787558, 1827752, 1868643, 1910310, 1952764, 
    1995964, 2039829, 2084438, 2129682, 2175900, 2222877, 2270575, 2319052, 2368279, 2418279, 
    2468979, 2520481, 2572804, 2625837, 2679680, 2734352, 2789925, 2846357, 2903802, 2962153, 
    3021701, 3082687, 3146580, 3200603
]

IAT2_DEATH_DATA = [
    0, 126468, 321248, 525515, 734419, 829592, 1020884, 1042505, 1064500, 1087000, 1109882,
    1133237, 1157070, 1181428, 1206147, 1061997, 1085248, 1108966, 1133198, 1157911, 1183148,
    1208876, 1235103, 1261924, 1289210, 1216901, 1244068, 1271740, 1299990, 1328795, 1358120,
    1388107, 1418622, 1449725, 1481299, 1419520, 1451866, 1484970, 1518800, 1553341, 1588614,
    1624646, 1661449, 1699012, 1737309, 1776371, 1816211, 1856864, 1898257, 1940424, 1983338,
    2027039, 2071405, 2116516, 2162260, 2192816, 2239250, 2286321, 2334047, 2382480, 2431561,
    2481342, 2531842, 2583120, 2635109, 2687867, 2741411, 2795815, 2850993, 2907018, 2963907,
    3021743, 3082687, 3146580, 3200603
]

# --- 核心更新：根據附件圖表修正借款成數 ---
def get_loan_limit_rate(year):
    if year >= 4: return 0.90  # 4年(含)以上為 90%
    if year == 3: return 0.85  # 第3年為 85%
    if year == 2: return 0.80  # 第2年為 80%
    if year == 1: return 0.75  # 第1年為 75%
    return 0

def get_iat2_cv(year, annual_deposit):
    if year <= 0: return 0
    idx = year if year < len(IAT2_CV_DATA) else len(IAT2_CV_DATA) - 1
    return IAT2_CV_DATA[idx] * (annual_deposit / IAT2_BASE_PREMIUM)

def get_iat2_death(year, annual_deposit):
    if year <= 0: return 0
    idx = year if year < len(IAT2_DEATH_DATA) else len(IAT2_DEATH_DATA) - 1
    return IAT2_DEATH_DATA[idx] * (annual_deposit / IAT2_BASE_PREMIUM)

def format_money(val, is_receive_column=False):
    if val == 0: return "-"
    abs_val = abs(val)
    money_str = f"${abs_val:,.0f}"
    if is_receive_column and val < 0: return f"領 {money_str}"
    elif val < 0: return f"-{money_str}"
    return money_str

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("⚙️ IAT2 參數設定")
    start_age = st.number_input("🧑‍💼 投保年齡", value=37, min_value=0, max_value=80)
    monthly_deposit = st.number_input("💵 月存金額", value=10076, step=1000)
    st.divider()
    mode = st.radio("🔄 選擇策略模式", ["🛡️ 以息養險 (折抵保費)", "🚀 階梯槓桿 (複利滾存)"])
    st.info("💡 借款成數已更新：\n1年:75% / 2年:80% / 3年:85% / 4年+:90%")

# --- 5. 主畫面與計算 ---
st.title("📊 IAT2 策略全能計算機 (精準借款版)")

annual_deposit = monthly_deposit * 12
deposit_years = 6
fee_rate = 0.05
MIN_LOAN_THRESHOLD = 300000 
LOAN_INTERVAL_YEARS = 3 

data_rows, raw_data_rows = [], []
current_loan, current_fund, accum_cash_out, accum_net_wealth, accum_real_cost, last_borrow_year = 0, 0, 0, 0, 0, 0

for age in range(start_age + 1, start_age + 51):
    policy_year = age - start_age
    cv = get_iat2_cv(policy_year, annual_deposit)
    limit_rate = get_loan_limit_rate(policy_year) # 調用更新後的成數
    
    loan_tag, is_borrowing_year = "", False
    if age <= 65:
        max_loan = cv * limit_rate
        new_borrow = max_loan - current_loan
        if new_borrow >= MIN_LOAN_THRESHOLD and (last_borrow_year == 0 or (policy_year - last_borrow_year) >= LOAN_INTERVAL_YEARS):
            current_loan += new_borrow
            current_fund += new_borrow * (1 - fee_rate)
            last_borrow_year = policy_year
            loan_tag = "⚡"
            is_borrowing_year = True

    net_income = current_fund * 0.07
    nominal_premium = annual_deposit if policy_year <= deposit_years else 0
    death_benefit_base = get_iat2_death(policy_year, annual_deposit)
    
    row_display = {"保單年度": policy_year, "年齡": f"{age} {loan_tag}"}
    
    if "以息養險" in mode:
        actual_pay_yearly = nominal_premium - net_income
        if actual_pay_yearly > 0: accum_real_cost += actual_pay_yearly
        else: accum_cash_out += abs(actual_pay_yearly)
        total_net_asset = cv + current_fund + accum_cash_out - current_loan
        total_death_benefit = death_benefit_base + current_fund - current_loan
        row_display.update({
            "①應繳年保費": format_money(nominal_premium),
            "②配息抵扣": format_money(net_income),
            "③實繳金額": format_money(actual_pay_yearly, is_receive_column=True),
            "④累積實繳": format_money(accum_real_cost),
            "⑤IAT2解約金": format_money(cv),
            "⑥保單借款": f"{format_money(-current_loan)} ({int(limit_rate*100)}%)",
            "⑦基金本金": format_money(current_fund),
            "⑧總淨資產": format_money(total_net_asset),
            "⑨身故金": format_money(total_death_benefit)
        })
    else:
        accum_net_wealth = (accum_net_wealth * 1.07) + net_income
        total_net_asset = cv + current_fund + accum_net_wealth - current_loan
        total_death_benefit = death_benefit_base + current_fund + accum_net_wealth - current_loan
        row_display.update({
            "①當年存入": format_money(nominal_premium),
            "②累積本金": format_money(annual_deposit * min(policy_year, 6)),
            "③IAT2解約金": format_money(cv),
            "④保單借款": f"{format_money(-current_loan)} ({int(limit_rate*100)}%)",
            "⑤基金本金": format_money(current_fund),
            "⑥年度淨配息": format_money(net_income),
            "⑦累積配息(複利)": format_money(accum_net_wealth),
            "⑧總淨資產": format_money(total_net_asset),
            "⑨身故金": format_money(total_death_benefit)
        })
    data_rows.append(row_display)

# --- 6. 顯示表格 ---
st.dataframe(pd.DataFrame(data_rows), use_container_width=True, height=600, hide_index=True)
st.caption("註：借款成數參考富邦人壽最新公佈之借款上限表修正。")
