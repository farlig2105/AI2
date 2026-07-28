import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Cấu hình trang
st.set_page_config(
    page_title="FinFlow - Quản Lý Tài Chính Cá Nhân",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed"
)

# ----------------------------------------------------
# BỘ HÀM XỬ LÝ ĐỊNH DẠNG TIỀN TỆ THÔNG MINH
# ----------------------------------------------------
def parse_amount(val) -> float:
    """Chuyển đổi chuỗi nhập liệu thành số thực"""
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = "".join(c for c in str(val) if c.isdigit())
    return float(cleaned) if cleaned else 0.0

def format_money_callback(key_name):
    """Callback tự động thêm dấu phẩy hàng nghìn khi người dùng nhập số"""
    raw_val = st.session_state.get(key_name, "")
    digits = "".join(c for c in str(raw_val) if c.isdigit())
    if digits:
        st.session_state[key_name] = f"{int(digits):,}"
    else:
        st.session_state[key_name] = "0"

def num2vi_words(val) -> str:
    """Đọc số tiền dạng viết tắt trực quan (Nghìn / Triệu / Tỷ)"""
    n = int(parse_amount(val))
    if n <= 0:
        return "0 VNĐ"
    if n >= 1_000_000_000:
        ty = n // 1_000_000_000
        trieu = (n % 1_000_000_000) // 1_000_000
        return f"{ty:,} tỷ {trieu} triệu VNĐ" if trieu > 0 else f"{ty:,} tỷ VNĐ"
    elif n >= 1_000_000:
        trieu = n // 1_000_000
        nghin = (n % 1_000_000) // 1_000
        return f"{trieu} triệu {nghin} nghìn VNĐ" if nghin > 0 else f"{trieu} triệu VNĐ"
    elif n >= 1_000:
        nghin = n // 1_000
        dong = n % 1_000
        return f"{nghin} nghìn {dong} VNĐ" if dong > 0 else f"{nghin} nghìn VNĐ"
    else:
        return f"{n} VNĐ"

# 2. Tiêm CSS Tùy Biến (Ultra-Modern Fintech UI)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Nền ứng dụng chính */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #1E1B4B 0%, #0F172A 50%, #020617 100%) !important;
        color: #F8FAFC;
    }

    /* Backdrop Blur cho Modal Dialog */
    div[data-testid="stDialog"] > div:first-child {
        backdrop-filter: blur(20px) !important;
        background-color: rgba(2, 6, 23, 0.8) !important;
    }

    div[role="dialog"] {
        border-radius: 24px !important;
        background: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.8) !important;
    }

    /* Dashboard Header */
    .dash-header {
        background: linear-gradient(135deg, #818CF8 0%, #C084FC 50%, #34D399 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.4rem;
        letter-spacing: -0.5px;
    }

    /* Glassmorphic Metric Cards */
    .metric-card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 22px;
        transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
    }
    .metric-card:hover {
        transform: translateY(-4px);
        background: rgba(30, 41, 59, 0.6);
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 20px 30px -10px rgba(99, 102, 241, 0.2);
    }
    .metric-title {
        color: #94A3B8;
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .metric-value {
        color: #FFFFFF;
        font-size: 1.75rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .metric-sub {
        font-size: 0.825rem;
        margin-top: 8px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .sub-green { color: #34D399; }
    .sub-red { color: #F87171; }

    /* Custom Tabs */
    div[data-testid="stTabs"] {
        margin-top: 10px;
    }
    
    div[data-baseweb="tab-list"] {
        background: rgba(15, 23, 42, 0.6) !important;
        backdrop-filter: blur(12px) !important;
        padding: 6px !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        gap: 8px !important;
        display: flex !important;
        width: 100% !important;
    }

    button[data-baseweb="tab"] {
        flex: 1 !important;
        height: 48px !important;
        border-radius: 12px !important;
        border: none !important;
        background: transparent !important;
        color: #94A3B8 !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    button[data-baseweb="tab"]:hover {
        color: #F8FAFC !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 8px 20px -4px rgba(99, 102, 241, 0.5) !important;
    }

    div[data-baseweb="tab-highlight"], div[data-baseweb="tab-border"] {
        display: none !important;
    }

    div[data-testid="stTabContent"] {
        animation: fadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Nút Bấm Gradient */
    .stButton > button {
        border-radius: 12px !important;
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: white !important;
        border: none !important;
        font-weight: 700 !important;
        padding: 0.6rem 1.25rem !important;
        transition: all 0.25s ease !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4) !important;
    }

    /* Custom Inputs */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border-radius: 12px !important;
        background-color: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #6366F1 !important;
    }

    /* Fix Avatar & Chat UI */
    div[data-testid="stChatMessage"] {
        background: rgba(30, 41, 59, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        backdrop-filter: blur(10px) !important;
    }

    div[data-testid="stChatMessageAvatar"] {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(79, 70, 229, 0.25) 100%) !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        border-radius: 12px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Khởi tạo Session State
if "configured" not in st.session_state:
    st.session_state.configured = False
if "modal_step" not in st.session_state:
    st.session_state.modal_step = 1
if "income" not in st.session_state:
    st.session_state.income = 15000000.0
if "fixed_expenses" not in st.session_state:
    st.session_state.fixed_expenses = {
        "Tiền nhà": 3500000.0,
        "Thực phẩm": 4000000.0,
        "Điện nước & Mạng": 1000000.0,
        "Giải trí": 1500000.0,
        "Đi lại": 800000.0,
        "Khác": 500000.0
    }
if "savings_goal" not in st.session_state:
    st.session_state.savings_goal = 2960000.0
if "daily_logs" not in st.session_state:
    st.session_state.daily_logs = pd.DataFrame(columns=["Ngày", "Danh mục", "Số tiền", "Ghi chú"])
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "👋 **Xin chào! Tôi là FinBot AI** - Trợ lý tài chính thông minh của bạn.\n\nHãy bấm vào các gợi ý nhanh bên dưới hoặc đặt câu hỏi để tôi phân tích dòng tiền giúp bạn nhé!"}
    ]

# Khởi tạo keys nhập liệu cho Modal
if "inp_income" not in st.session_state:
    st.session_state.inp_income = f"{int(st.session_state.income):,}"
if "inp_rent" not in st.session_state:
    st.session_state.inp_rent = f"{int(st.session_state.fixed_expenses['Tiền nhà']):,}"
if "inp_food" not in st.session_state:
    st.session_state.inp_food = f"{int(st.session_state.fixed_expenses['Thực phẩm']):,}"
if "inp_util" not in st.session_state:
    st.session_state.inp_util = f"{int(st.session_state.fixed_expenses['Điện nước & Mạng']):,}"
if "inp_ent" not in st.session_state:
    st.session_state.inp_ent = f"{int(st.session_state.fixed_expenses['Giải trí']):,}"
if "inp_trans" not in st.session_state:
    st.session_state.inp_trans = f"{int(st.session_state.fixed_expenses['Đi lại']):,}"
if "inp_other" not in st.session_state:
    st.session_state.inp_other = f"{int(st.session_state.fixed_expenses['Khác']):,}"
if "inp_log_amt" not in st.session_state:
    st.session_state.inp_log_amt = "500,000"

# 4. Pop-up Modal Thiết Lập
@st.dialog("⚙️ Thiết Lập Khai Báo Tài Chính", width="large")
def show_setup_modal():
    if st.session_state.modal_step == 1:
        st.caption("Bước 1/2: Khai báo Thu nhập & Các khoản chi phí cố định ước tính")
        
        st.text_input(
            "💵 Thu nhập cố định hàng tháng (VNĐ):", 
            key="inp_income",
            on_change=format_money_callback,
            args=("inp_income",)
        )
        inc_val = parse_amount(st.session_state.inp_income)
        st.caption(f"➔ Số tiền: **{inc_val:,.0f} VNĐ** *({num2vi_words(inc_val)})*")
        
        st.write("---")
        st.markdown("**📌 Chi tiêu dự kiến hàng tháng:**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.text_input("Tiền nhà / Thuê phòng:", key="inp_rent", on_change=format_money_callback, args=("inp_rent",))
            rent_val = parse_amount(st.session_state.inp_rent)
            st.caption(f"➔ Số tiền: **{rent_val:,.0f} VNĐ** *({num2vi_words(rent_val)})*")

            st.text_input("Thực phẩm / Ăn uống:", key="inp_food", on_change=format_money_callback, args=("inp_food",))
            food_val = parse_amount(st.session_state.inp_food)
            st.caption(f"➔ Số tiền: **{food_val:,.0f} VNĐ** *({num2vi_words(food_val)})*")

            st.text_input("Điện, nước, Internet:", key="inp_util", on_change=format_money_callback, args=("inp_util",))
            util_val = parse_amount(st.session_state.inp_util)
            st.caption(f"➔ Số tiền: **{util_val:,.0f} VNĐ** *({num2vi_words(util_val)})*")

        with col_b:
            st.text_input("Giải trí / Giao lưu:", key="inp_ent", on_change=format_money_callback, args=("inp_ent",))
            ent_val = parse_amount(st.session_state.inp_ent)
            st.caption(f"➔ Số tiền: **{ent_val:,.0f} VNĐ** *({num2vi_words(ent_val)})*")

            st.text_input("Đi lại / Xăng xe:", key="inp_trans", on_change=format_money_callback, args=("inp_trans",))
            trans_val = parse_amount(st.session_state.inp_trans)
            st.caption(f"➔ Số tiền: **{trans_val:,.0f} VNĐ** *({num2vi_words(trans_val)})*")

            st.text_input("Khoản khác:", key="inp_other", on_change=format_money_callback, args=("inp_other",))
            other_val = parse_amount(st.session_state.inp_other)
            st.caption(f"➔ Số tiền: **{other_val:,.0f} VNĐ** *({num2vi_words(other_val)})*")

        if st.button("Tiếp theo: Đặt mục tiêu tiết kiệm ➡️", use_container_width=True):
            st.session_state.income = inc_val
            st.session_state.fixed_expenses = {
                "Tiền nhà": rent_val,
                "Thực phẩm": food_val,
                "Điện nước & Mạng": util_val,
                "Giải trí": ent_val,
                "Đi lại": trans_val,
                "Khác": other_val
            }
            total_exp = sum(st.session_state.fixed_expenses.values())
            max_possible = max(0.0, st.session_state.income - total_exp)
            st.session_state.inp_goal = f"{int(max_possible * 0.8):,}"
            st.session_state.modal_step = 2
            st.rerun()

    elif st.session_state.modal_step == 2:
        st.caption("Bước 2/2: Đặt mục tiêu tích lũy tháng")
        total_exp = sum(st.session_state.fixed_expenses.values())
        max_possible = max(0.0, st.session_state.income - total_exp)

        st.info(f"💡 Dựa trên thu nhập ({st.session_state.income:,.0f} VNĐ) và tổng chi cố định ({total_exp:,.0f} VNĐ), khả năng tiết kiệm tối đa của bạn là **{max_possible:,.0f} VNĐ**.")

        if "inp_goal" not in st.session_state:
            st.session_state.inp_goal = f"{int(max_possible * 0.8):,}"

        st.text_input(
            "🎯 Mục tiêu tiết kiệm tháng này (VNĐ):", 
            key="inp_goal",
            on_change=format_money_callback,
            args=("inp_goal",)
        )
        goal_val = parse_amount(st.session_state.inp_goal)
        st.caption(f"➔ Số tiền: **{goal_val:,.0f} VNĐ** *({num2vi_words(goal_val)})*")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Quay lại", use_container_width=True):
                st.session_state.modal_step = 1
                st.rerun()
        with col2:
            if st.button("Hoàn thành & Vào Dashboard 🚀", use_container_width=True):
                st.session_state.savings_goal = goal_val
                st.session_state.configured = True
                st.session_state.modal_step = 1
                st.rerun()

if not st.session_state.configured:
    show_setup_modal()

# ----------------------------------------------------
# 5. HEADER & TOP METRICS CARDS
# ----------------------------------------------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown('<div class="dash-header">💎 FinFlow Dashboard</div>', unsafe_allow_html=True)
    st.caption("Hệ thống phân tích & Quản lý tài chính cá nhân thế hệ mới")
with head_col2:
    if st.button("⚙️ Cấu hình lại thông tin", use_container_width=True):
        st.session_state.configured = False
        st.rerun()

st.write("")

# Tính toán chỉ số tổng quát
fixed_exp_total = sum(st.session_state.fixed_expenses.values())
logged_exp_total = st.session_state.daily_logs["Số tiền"].sum() if not st.session_state.daily_logs.empty else 0.0
grand_total_exp = fixed_exp_total + logged_exp_total
remaining_balance = st.session_state.income - grand_total_exp
diff_goal = remaining_balance - st.session_state.savings_goal

# Thẻ Metric
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">TỔNG THU NHẬP</div>
        <div class="metric-value">{st.session_state.income:,.0f} <span style="font-size:1rem; color:#94A3B8;">đ</span></div>
        <div class="metric-sub sub-green">⚡ Cố định hàng tháng</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">TỔNG CHI TIÊU</div>
        <div class="metric-value">{grand_total_exp:,.0f} <span style="font-size:1rem; color:#94A3B8;">đ</span></div>
        <div class="metric-sub sub-red">📌 Cố định: {fixed_exp_total:,.0f} đ | Phát sinh: {logged_exp_total:,.0f} đ</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">SỐ DƯ CÒN LẠI</div>
        <div class="metric-value">{remaining_balance:,.0f} <span style="font-size:1rem; color:#94A3B8;">đ</span></div>
        <div class="metric-sub {'sub-green' if remaining_balance >= 0 else 'sub-red'}">
            {'✅ Khả dụng' if remaining_balance >= 0 else '⚠️ Cảnh báo thâm hụt'}
        </div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    diff_text = f"+{diff_goal:,.0f} đ so với mục tiêu" if diff_goal >= 0 else f"{diff_goal:,.0f} đ so với mục tiêu"
    diff_class = "sub-green" if diff_goal >= 0 else "sub-red"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">MỤC TIÊU TIẾT KIỆM</div>
        <div class="metric-value">{st.session_state.savings_goal:,.0f} <span style="font-size:1rem; color:#94A3B8;">đ</span></div>
        <div class="metric-sub {diff_class}">🎯 {diff_text}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# Progress Bar Tích Lũy
if st.session_state.savings_goal > 0:
    progress_ratio = min(max(remaining_balance / st.session_state.savings_goal, 0.0), 1.0)
    st.progress(progress_ratio)
    if remaining_balance >= st.session_state.savings_goal:
        st.success(f"🎉 Rất tốt! Số dư hiện tại ({remaining_balance:,.0f} VNĐ) đã đạt mục tiêu tích lũy tháng này.")
    else:
        st.warning(f"⚠️ Cần chú ý: Số dư còn lại ({remaining_balance:,.0f} VNĐ) chưa đạt mục tiêu tiết kiệm ({st.session_state.savings_goal:,.0f} VNĐ).")

st.write("")

# ----------------------------------------------------
# 6. THANH SUB-TABS
# ----------------------------------------------------
tab_stats, tab_ai = st.tabs(["📊  Thống kê & Quản lý Chi tiêu", "🤖  Trợ lý Tài chính AI (FinBot)"])

# ================= TAB 1: THỐNG KÊ & PHÂN BỔ =================
with tab_stats:
    st.write("")
    col_chart1, col_chart2, col_form = st.columns([1, 1, 0.95])

    # --- BIỂU ĐỒ 1: CẤU TRÚC NGÂN SÁCH CỐ ĐỊNH ---
    with col_chart1:
        st.markdown("##### 📊 Phân bổ ngân sách cố định")
        df_fixed = pd.DataFrame(list(st.session_state.fixed_expenses.items()), columns=["Danh mục", "Số tiền"])
        
        fig1 = px.pie(
            df_fixed, 
            values="Số tiền", 
            names="Danh mục", 
            hole=0.6,
            color_discrete_sequence=['#818CF8', '#34D399', '#FBBF24', '#F87171', '#A78BFA', '#F472B6']
        )
        fig1.update_traces(
            textposition='inside',
            textinfo='percent',
            hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} VNĐ<br>Tỷ lệ: %{percent}<extra></extra>'
        )

        fig1.add_annotation(
            text=f"<span style='font-size:11px; color:#94A3B8; font-weight:600;'>TỔNG CỐ ĐỊNH</span><br><b style='font-size:16px; color:#F8FAFC;'>{fixed_exp_total:,.0f} đ</b>",
            x=0.5, y=0.5,
            showarrow=False,
            align="center"
        )

        fig1.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#F8FAFC', family="Plus Jakarta Sans", size=12),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            ),
            margin=dict(t=10, b=50, l=10, r=10),
            height=350
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- BIỂU ĐỒ 2: THỰC TẾ CHI TIÊU & SỐ DƯ CÒN LẠI ---
    with col_chart2:
        st.markdown("##### 📈 Chi tiêu thực tế & Số dư còn lại")
        
        # Xây dựng danh sách các phần tử cho biểu đồ 2
        chart2_list = []
        
        # 1. Các khoản chi cố định
        for cat, amt in st.session_state.fixed_expenses.items():
            if amt > 0:
                chart2_list.append({"Danh mục": cat, "Số tiền": amt, "Loại": "Chi cố định"})
                
        # 2. Các khoản chi phát sinh thực tế nhập từ bảng
        if logged_exp_total > 0:
            chart2_list.append({"Danh mục": "Chi phát sinh thực tế", "Số tiền": logged_exp_total, "Loại": "Chi phát sinh"})
            
        # 3. Khoảng tiết kiệm / số dư còn lại sau chi tiêu
        if remaining_balance > 0:
            chart2_list.append({"Danh mục": "Số dư còn lại", "Số tiền": remaining_balance, "Loại": "Số dư"})

        df_chart2 = pd.DataFrame(chart2_list)

        # Định nghĩa màu sắc nổi bật cho từng mục
        color_map = {
            "Số dư còn lại": "#34D399",          # Xanh emerald rực rỡ cho số dư/tiết kiệm
            "Chi phát sinh thực tế": "#FB7185",  # Đỏ hồng phát sinh
        }

        fig2 = px.pie(
            df_chart2, 
            values="Số tiền", 
            names="Danh mục", 
            hole=0.6,
            color="Danh mục",
            color_discrete_map=color_map,
            color_discrete_sequence=['#818CF8', '#A78BFA', '#FBBF24', '#38BDF8', '#818CF8', '#C084FC']
        )
        fig2.update_traces(
            textposition='inside',
            textinfo='percent',
            hovertemplate='<b>%{label}</b><br>Số tiền: %{value:,.0f} VNĐ<br>Tỷ lệ: %{percent}<extra></extra>'
        )

        # Cấu hình hiển thị khoản tiết kiệm/số dư còn lại ở giữa hình tròn
        bal_color = "#34D399" if remaining_balance >= 0 else "#F87171"
        bal_label = "SỐ DƯ CÒN LẠI" if remaining_balance >= 0 else "THÂM HỤT"

        fig2.add_annotation(
            text=f"<span style='font-size:11px; color:#94A3B8; font-weight:600;'>{bal_label}</span><br><b style='font-size:16px; color:{bal_color};'>{remaining_balance:,.0f} đ</b>",
            x=0.5, y=0.5,
            showarrow=False,
            align="center"
        )

        fig2.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#F8FAFC', family="Plus Jakarta Sans", size=12),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.3,
                xanchor="center",
                x=0.5,
                font=dict(size=11)
            ),
            margin=dict(t=10, b=50, l=10, r=10),
            height=350
        )
        st.plotly_chart(fig2, use_container_width=True)

    # --- KHUNG NHẬP KHOẢN CHI THỰC TẾ ---
    with col_form:
        st.markdown("##### ✍️ Ghi nhận khoản chi thực tế")
        log_date = st.date_input("Ngày giao dịch")
        log_cat = st.selectbox("Danh mục", list(st.session_state.fixed_expenses.keys()))
        
        # Ô nhập số tiền động tự nhảy dấu phẩy và hiển thị chữ viết tắt bên dưới
        st.text_input(
            "Số tiền (VNĐ)",
            key="inp_log_amt",
            on_change=format_money_callback,
            args=("inp_log_amt",)
        )
        log_amt = parse_amount(st.session_state.inp_log_amt)
        st.caption(f"➔ Số tiền: **{log_amt:,.0f} VNĐ** *({num2vi_words(log_amt)})*")
        
        log_note = st.text_input("Ghi chú khoản chi", placeholder="VD: Mua thực phẩm siêu thị")
        
        if st.button("➕ Thêm khoản chi", use_container_width=True):
            if log_amt > 0:
                new_row = pd.DataFrame([{"Ngày": str(log_date), "Danh mục": log_cat, "Số tiền": log_amt, "Ghi chú": log_note}])
                st.session_state.daily_logs = pd.concat([st.session_state.daily_logs, new_row], ignore_index=True)
                st.toast("Đã ghi nhận chi tiêu thành công!", icon="✅")
                st.session_state.inp_log_amt = "0"
                st.rerun()

    st.divider()
    st.markdown("##### 📋 Nhật ký chi tiêu thực tế trong tháng")
    if not st.session_state.daily_logs.empty:
        st.dataframe(
            st.session_state.daily_logs, 
            use_container_width=True,
            column_config={
                "Số tiền": st.column_config.NumberColumn("Số tiền (VNĐ)", format="%d VNĐ")
            }
        )
    else:
        st.info("Chưa có phát sinh chi tiêu nào được ghi nhận trong tháng này.")

# ================= TAB 2: AI ASSISTANT (FINBOT) =================
with tab_ai:
    st.write("")
    st.markdown("##### 🤖 FinBot AI - Cố vấn tài chính cá nhân")
    st.caption("AI kết nối trực tiếp với dòng tiền của bạn để đưa ra phân tích chuyên sâu.")

    # Nút bấm hỏi nhanh
    q1, q2, q3 = st.columns(3)
    user_click_prompt = None
    with q1:
        if st.button("📊 Phân tích thu chi tháng này", use_container_width=True):
            user_click_prompt = "Phân tích thu chi tháng này"
    with q2:
        if st.button("💡 Tư vấn đạt mục tiêu tiết kiệm", use_container_width=True):
            user_click_prompt = "Tư vấn đạt mục tiêu tiết kiệm"
    with q3:
        if st.button("🛒 Cân nhắc hạn mức mua sắm", use_container_width=True):
            user_click_prompt = "Cân nhắc hạn mức mua sắm"

    st.write("")

    # Cửa sổ Chat
    chat_container = st.container(height=420)
    with chat_container:
        for message in st.session_state.chat_history:
            avatar_icon = "🤖" if message["role"] == "assistant" else "👤"
            with st.chat_message(message["role"], avatar=avatar_icon):
                st.markdown(message["content"])

    # Xử lý nhập liệu từ bàn phím hoặc nút bấm
    user_prompt = st.chat_input("Nhập câu hỏi cho AI...") or user_click_prompt

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        
        prompt_lower = user_prompt.lower()
        exp_ratio = (grand_total_exp / st.session_state.income * 100) if st.session_state.income > 0 else 0
        
        if "phân tích" in prompt_lower or "thu chi" in prompt_lower:
            ai_reply = f"""📊 **Báo cáo phân tích tài chính:**
- **Tổng thu nhập:** `{st.session_state.income:,.0f} VNĐ`
- **Tổng chi tiêu:** `{grand_total_exp:,.0f} VNĐ` (Chiếm **{exp_ratio:.1f}%** thu nhập)
- **Số dư khả dụng:** `{remaining_balance:,.0f} VNĐ`

💡 **Đánh giá:** {"⚠️ Tỷ lệ chi tiêu của bạn đang khá cao (>70%). Nên kiểm soát thêm các khoản phát sinh ngoài kế hoạch." if exp_ratio > 70 else "✅ Tỷ lệ chi tiêu của bạn rất lành mạnh và an toàn."}"""
        
        elif "tiết kiệm" in prompt_lower or "mục tiêu" in prompt_lower:
            ai_reply = f"""💡 **Chiến lược đạt mục tiêu tiết kiệm:**
- **Mục tiêu tháng:** `{st.session_state.savings_goal:,.0f} VNĐ`
- **Số dư hiện tại:** `{remaining_balance:,.0f} VNĐ`
- **Tình trạng:** {'🎉 Bạn đã xuất sắc hoàn thành mục tiêu tích lũy!' if diff_goal >= 0 else f'⚠️ Còn thiếu **{abs(diff_goal):,.0f} VNĐ**. Hãy ưu tiên trích ngay 20% thu nhập đầu tháng vào quỹ tiết kiệm!'}"""

        elif "mua" in prompt_lower or "hạn mức" in prompt_lower:
            ai_reply = f"""🛒 **Tư vấn hạn mức mua sắm:**
Số dư khả dụng của bạn là **{remaining_balance:,.0f} VNĐ**. 
- Khoản mua sắm **dưới {remaining_balance * 0.15:,.0f} VNĐ** (15% số dư) nằm trong hạn mức an toàn.
- Nếu lớn hơn, hãy áp dụng quy tắc **"Hoãn 48 tiếng"** để tránh mua sắm cảm xúc!"""

        else:
            ai_reply = f"""Tôi đã ghi nhận thắc mắc của bạn! Dựa trên ngân sách khả dụng **{remaining_balance:,.0f} VNĐ**, hãy thử chọn các gợi ý phía trên hoặc hỏi cụ thể hơn để tôi hỗ trợ nhé!"""

        st.session_state.chat_history.append({"role": "assistant", "content": ai_reply})
        st.rerun()
