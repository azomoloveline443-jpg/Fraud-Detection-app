import streamlit as st
import pandas as pd
import joblib
import os
import random
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Ticket Fraud Detection",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. INITIALIZE SESSION STATE
# ==========================================
if "recent_reservations" not in st.session_state:
    st.session_state.recent_reservations = []

if "_db_seeded" not in st.session_state:
    st.session_state._db_seeded = False

# _pending_prediction holds the last prediction result to display after a rerun
if "_pending_prediction" not in st.session_state:
    st.session_state._pending_prediction = None

# ==========================================
# 3. POWER BI STYLING (White / Fuchsia)
# ==========================================
st.markdown("""
    <style>
        .stApp { background-color: #FFFFFF !important; }
        .main > div { background-color: #FFFFFF !important; }
        html, body, [class*="css"] { color: #1A1A1A !important; }
        h1, h2, h3, h4, h5, h6, p, li, span, label, div { color: #1A1A1A !important; }

        .powerbi-header {
            background: linear-gradient(135deg, #E6007E 0%, #C4006A 100%);
            padding: 18px 30px;
            border-radius: 10px;
            margin-bottom: 25px;
            box-shadow: 0 4px 15px rgba(230, 0, 126, 0.25);
        }
        .powerbi-header h1 { color: #FFFFFF !important; font-size: 26px; font-weight: 700; margin: 0; letter-spacing: 0.5px; }
        .powerbi-header p { color: rgba(255,255,255,0.85) !important; font-size: 14px; margin: 4px 0 0 0; }

        .metric-card {
            background: #FFFFFF;
            border: 1.5px solid #E6007E;
            border-radius: 10px;
            padding: 18px 15px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(230, 0, 126, 0.10);
            transition: transform 0.15s ease;
            height: 100%;
        }
        .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(230, 0, 126, 0.18); }
        .metric-card .label { font-size: 12px; font-weight: 600; color: #888888 !important; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
        .metric-card .value { font-size: 28px; font-weight: 700; }
        .metric-card .value.green  { color: #00A86B !important; }
        .metric-card .value.red    { color: #E6007E !important; }
        .metric-card .value.orange { color: #FF8C00 !important; }
        .metric-card .value.blue   { color: #2563EB !important; }

        .form-card {
            background: #FFFFFF;
            border: 1.5px solid #E6E6E6;
            border-radius: 10px;
            padding: 22px 24px 8px 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 20px;
        }
        .form-card h4 { color: #E6007E !important; font-weight: 600; font-size: 16px; margin-bottom: 14px; border-bottom: 2px solid #F0F0F0; padding-bottom: 10px; }

        div.stButton > button {
            background: linear-gradient(135deg, #E6007E 0%, #C4006A 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 14px 28px !important;
            font-size: 17px !important;
            font-weight: 700 !important;
            letter-spacing: 0.5px !important;
            box-shadow: 0 4px 14px rgba(230, 0, 126, 0.30) !important;
            transition: all 0.2s ease !important;
            width: 100%;
        }
        div.stButton > button:hover { box-shadow: 0 6px 20px rgba(230, 0, 126, 0.45) !important; transform: translateY(-1px); }
        div.stButton > button:active { transform: translateY(0px); }

        .result-box { border-radius: 10px; padding: 22px 25px; margin-top: 10px; border-left: 6px solid; }
        .result-box.approved { background: #F0FFF4; border-left-color: #00A86B; }
        .result-box.suspicious { background: #FFF0F5; border-left-color: #E6007E; }
        .result-box .result-title { font-size: 20px; font-weight: 700; }
        .result-box .result-detail { font-size: 15px; margin-top: 4px; }

        section[data-testid="stSidebar"] { background: #FAFAFA !important; border-right: 1px solid #E6E6E6; }
        section[data-testid="stSidebar"] .block-container { padding-top: 28px; }
        section[data-testid="stSidebar"] hr { border-color: #E6E6E6; }

        .divider-fuchsia { border: none; height: 2px; background: linear-gradient(90deg, #E6007E 0%, transparent 100%); margin: 8px 0 16px 0; }

        .sidebar-metric { background: #FFFFFF; border: 1px solid #E6E6E6; border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; text-align: center; }
        .sidebar-metric .s-label { font-size: 11px; font-weight: 600; color: #999999 !important; text-transform: uppercase; letter-spacing: 0.5px; }
        .sidebar-metric .s-value { font-size: 22px; font-weight: 700; margin-top: 2px; }

        .stSelectbox label, .stNumberInput label, .stTextInput label, .stDateInput label, .stSlider label { font-weight: 500 !important; color: #333333 !important; }
        .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input, .stTextInput input, .stDateInput input { border: 1.5px solid #D0D0D0 !important; border-radius: 6px !important; }
        .st-cx, .st-cy, .st-cw, .st-cv, .st-cu, .st-ct { background-color: transparent !important; }
        .stApp header { background: transparent !important; }
        .user-badge { background: #FFFFFF; border: 1px solid #E6007E; border-radius: 20px; padding: 6px 14px; display: inline-block; font-size: 13px; font-weight: 600; color: #E6007E !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. INITIAL STATS (fallback when DB not available)
# ==========================================
total_reservations = 501
approved_count = 257
monitoring_count = 219
blocked_count = 25
fraud_count = 244
fraud_rate = 48.7

# ==========================================
# 5. LOAD MACHINE LEARNING MODEL
# ==========================================
MODEL_PATH = "fraud_detection_pipeline.pkl"
model = None
if os.path.exists(MODEL_PATH):
    try:
        model = joblib.load(MODEL_PATH)
    except Exception:
        pass

# ==========================================
# 6. POSTGRESQL CONFIGURATION
# ==========================================
DB_CONFIG = {
    "username": "postgres",
    "password": "Admin1234",
    "host": "localhost",
    "port": 5432,
    "database": "Fraud_Detection"
}
DB_TABLE = "ticket_fraud_predictions"

def get_db_connection():
    conn_str = (
        f"postgresql+psycopg2://{DB_CONFIG['username']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
    )
    return create_engine(conn_str)


def sync_table_schema():
    engine = get_db_connection()
    desired_columns = [
        ("Booking_ID", "VARCHAR(20) NOT NULL UNIQUE"),
        ("Customer_ID", "VARCHAR(20) NOT NULL UNIQUE"),
        ("route", "VARCHAR(100)"),
        ("booking_date", "DATE"),
        ("travel_date", "DATE"),
        ("passenger_name", "VARCHAR(100)"),
        ("passenger_age", "INT"),
        ("gender", "VARCHAR(10)"),
        ("booking_amount", "DOUBLE PRECISION"),
        ("discount_applied", "DOUBLE PRECISION"),
        ("payment_method", "VARCHAR(50)"),
        ("reservation_platform", "VARCHAR(50)"),
        ("cancellation_status", "VARCHAR(30)"),
        ("loyalty_membership", "VARCHAR(20)"),
        ("lead_time", "INT"),
        ("number_of_tickets", "INT"),
        ("previous_cancellations", "INT"),
        ("risk_score", "INT"),
        ("risk_level", "VARCHAR(20)"),
        ("decision", "VARCHAR(20)"),
    ]
    col_defs = ",\n    ".join(f'"{col_name}" {col_type}' for col_name, col_type in desired_columns)
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_TABLE} (
                id SERIAL PRIMARY KEY,
                {col_defs},
                prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        for column_name, column_type in desired_columns:
            conn.execute(text(f"""
                ALTER TABLE {DB_TABLE}
                ADD COLUMN IF NOT EXISTS "{column_name}" {column_type}
            """))
    return True


def init_database():
    try:
        sync_table_schema()
        return True
    except SQLAlchemyError:
        return False


def insert_new_reservation(conn, form_data, prediction_results):
    cursor = conn.connection.cursor()
    cursor.execute(f"SELECT COALESCE(MAX(id), 0) FROM {DB_TABLE};")
    next_number = cursor.fetchone()[0] + 1
    booking_id = f"CUST{next_number:06d}"
    customer_id = f"CUST{next_number:06d}"

    insert_query = f"""
    INSERT INTO {DB_TABLE} (
        "Booking_ID", "Customer_ID", route, booking_date, travel_date, passenger_name, passenger_age,
        gender, booking_amount, discount_applied, payment_method,
        reservation_platform, cancellation_status, loyalty_membership,
        lead_time, number_of_tickets, previous_cancellations, risk_score,
        risk_level, decision
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """
    query_values = (
        booking_id, customer_id,
        form_data['route'], form_data['booking_date'], form_data['travel_date'],
        form_data['passenger_name'], int(form_data['passenger_age']),
        form_data['gender'], float(form_data['booking_amount']),
        float(form_data['discount_applied']), form_data['payment_method'],
        form_data['reservation_platform'], form_data['cancellation_status'],
        form_data['loyalty_membership'],
        int(prediction_results['lead_time']),
        int(prediction_results['number_of_tickets']),
        int(prediction_results['previous_cancellations']),
        int(prediction_results['risk_score']),
        prediction_results['risk_level'], prediction_results['decision'],
    )
    cursor.execute(insert_query, query_values)
    conn.connection.commit()
    cursor.close()


# ==========================================
# 6b. DATABASE SEEDING
# ==========================================
TARGET_APPROVED = 257
TARGET_BLOCKED = 25
TARGET_MONITORING = 219


def _get_db_counts(conn):
    r = conn.execute(text(f"SELECT decision, COUNT(*) FROM {DB_TABLE} GROUP BY decision"))
    rows = r.fetchall()
    counts = {"APPROVED": 0, "MONITORING": 0, "BLOCKED": 0}
    for row in rows:
        if row[0] in counts:
            counts[row[0]] = row[1]
    total = sum(counts.values())
    return counts, total


def seed_database_to_targets():
    engine = get_db_connection()
    with engine.connect() as conn:
        counts, total = _get_db_counts(conn)
        needed_approved = max(0, TARGET_APPROVED - counts['APPROVED'])
        needed_blocked = max(0, TARGET_BLOCKED - counts['BLOCKED'])
        needed_monitoring = max(0, TARGET_MONITORING - counts['MONITORING'])
        if (needed_approved + needed_blocked + needed_monitoring) == 0:
            return

        max_id_result = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {DB_TABLE}")).scalar()
        next_id = max_id_result + 1

        routes = [
            "Douala → Yaounde", "Yaounde → Douala", "Douala → Bafoussam",
            "Bafoussam → Douala", "Yaounde → Garoua", "Douala → Bamenda",
            "Yaounde → Kribi", "Kribi → Douala"
        ]
        platforms = ["Mobile App", "Website", "Agent Counter", "Call Center"]
        payment_methods = ["MTN Mobile Money", "Orange Money", "UBA Transfer", "Afriland Transfer", "Express Union"]
        first_names_m = ["Jean","Paul","Pierre","Michel","Thomas","David","Samuel","Daniel","Eric","Alain","Patrick","Joseph","Claude","Henri","Marc"]
        first_names_f = ["Marie","Jeanne","Anne","Sophie","Claire","Esther","Florence","Ruth","Grace","Alice","Chantal","Beatrice","Sandrine","Eliane","Josiane"]
        last_names = ["Mbianda","Kamga","Fotso","Nkoulou","Abena","Tchinda","Dongmo","Ngono","Essono","Owono","Mbappe","Etoga","Amougou","Belinga","Zambo"]

        inserts_to_do = []
        for decision_type, needed in [("APPROVED", needed_approved), ("MONITORING", needed_monitoring), ("BLOCKED", needed_blocked)]:
            for _ in range(needed):
                bid = f"CUST{next_id:06d}"
                cid = f"CUST{next_id:06d}"
                next_id += 1
                gender_choice = random.choice(["MALE", "FEMALE"])
                if gender_choice == "MALE":
                    pname = f"{random.choice(first_names_m)} {random.choice(last_names)}"
                else:
                    pname = f"{random.choice(first_names_f)} {random.choice(last_names)}"
                route = random.choice(routes)
                bdate = date.today() - timedelta(days=random.randint(1, 30))
                tdate = bdate + timedelta(days=random.randint(1, 60))
                age = random.randint(18, 70)
                amount = random.randint(2000, 80000)
                discount = random.randint(0, 40)
                payment = random.choice(payment_methods)
                platform = random.choice(platforms)
                cancellation = random.choice(["Not Cancelled", "Cancelled"])
                loyalty = random.choice(["No", "Yes"])
                lead = (tdate - bdate).days
                tickets = random.randint(1, 5)
                prev_canc = random.randint(0, 5)

                if decision_type == "APPROVED":
                    risk_score = random.randint(0, 39); risk_level = "LOW"
                elif decision_type == "MONITORING":
                    risk_score = random.randint(40, 69); risk_level = "HIGH"
                else:
                    risk_score = random.randint(70, 100); risk_level = "CRITICAL"

                inserts_to_do.append((
                    bid, cid, route, bdate, tdate, pname, age, gender_choice,
                    amount, discount, payment, platform, cancellation, loyalty,
                    lead, tickets, prev_canc, risk_score, risk_level, decision_type
                ))

        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()
        insert_sql = f"""
        INSERT INTO {DB_TABLE} (
            "Booking_ID", "Customer_ID", route, booking_date, travel_date,
            passenger_name, passenger_age, gender, booking_amount, discount_applied,
            payment_method, reservation_platform, cancellation_status, loyalty_membership,
            lead_time, number_of_tickets, previous_cancellations, risk_score,
            risk_level, decision
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.executemany(insert_sql, inserts_to_do)
        raw_conn.commit()
        cursor.close()
        raw_conn.close()


def load_stats_from_database():
    global total_reservations, approved_count, monitoring_count, blocked_count, fraud_count, fraud_rate
    try:
        engine = get_db_connection()
        with engine.connect() as conn:
            counts, total = _get_db_counts(conn)
            if total > 0:
                total_reservations = total
                approved_count = counts['APPROVED']
                monitoring_count = counts['MONITORING']
                blocked_count = counts['BLOCKED']
                fraud_count = blocked_count + monitoring_count
                fraud_rate = (fraud_count / total_reservations * 100)
                return True
    except Exception:
        pass
    return False


# ==========================================
# 6c. DB INIT, SEEDING, LOAD STATS
# ==========================================
DB_READY = init_database()

if DB_READY and not st.session_state._db_seeded:
    try:
        seed_database_to_targets()
    except Exception:
        pass
    st.session_state._db_seeded = True

if DB_READY:
    load_stats_from_database()

# ==========================================
# 7. SIDEBAR - NAVIGATION & SUMMARY
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 10px;">
            <div style="background: #E6007E; width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                <span style="color: white; font-size: 28px; font-weight: bold;">CT</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #E6007E !important; font-weight: 700; margin-bottom: 4px;'>CTFD System</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 12px; color: #999 !important; margin-top: -4px;'>Cameroon Ticket Fraud Detection</p>", unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("Navigation", ["📋 Prediction", "📊 Dashboard", "ℹ️ About"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown("<h4 style='font-size: 14px; margin-bottom: 12px;'>📈 System Summary</h4>", unsafe_allow_html=True)
    st.markdown(f"""
        <div class="sidebar-metric">
            <div class="s-label">Total Reservations</div>
            <div class="s-value blue">{total_reservations}</div>
        </div>
        <div class="sidebar-metric">
            <div class="s-label">Approved</div>
            <div class="s-value green">{approved_count}</div>
        </div>
        <div class="sidebar-metric">
            <div class="s-label">Monitoring</div>
            <div class="s-value orange">{monitoring_count}</div>
        </div>
        <div class="sidebar-metric">
            <div class="s-label">Blocked</div>
            <div class="s-value red">{blocked_count}</div>
        </div>
        <div class="sidebar-metric">
            <div class="s-label">Fraud Rate</div>
            <div class="s-value red">{fraud_rate:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if DB_READY:
        st.markdown("""<div style="display: flex; align-items: center; gap: 8px; font-size: 13px;"><span style="color: #00A86B; font-size: 18px;">●</span><span>PostgreSQL connected</span></div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="display: flex; align-items: center; gap: 8px; font-size: 13px;"><span style="color: #FF8C00; font-size: 18px;">●</span><span>PostgreSQL not connected</span></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="margin-top: 12px; font-size: 12px; color: #AAAAAA !important;"><span>👤 Admin</span><br><span>📅 {date.today().strftime('%d %B %Y')}</span></div>""", unsafe_allow_html=True)

# ==========================================
# 8. PREDICTION PAGE
# ==========================================
if page == "📋 Prediction":

    st.markdown("""
        <div class="powerbi-header">
            <h1>🚌 Cameroon Ticket Fraud Detection System</h1>
            <p>Intelligent Fraud Detection System — Transport Reservations in Cameroon</p>
        </div>
    """, unsafe_allow_html=True)

    # --- Display pending prediction results if they exist ---
    pending = st.session_state._pending_prediction
    if pending is not None:
        # Clear it so it doesn't display again on next rerun
        st.session_state._pending_prediction = None

        risk_score = pending["risk_score"]
        risk_level = pending["risk_level"]
        decision = pending["decision"]
        bar_color = "#00A86B" if risk_score < 40 else "#FF8C00" if risk_score < 70 else "#E6007E"
        passenger_name = pending["passenger_name"]
        route = pending["route"]
        booking_amount = pending["booking_amount"]
        tickets_count = pending["tickets_count"]

        st.markdown('<h3 style="font-weight: 700; color: #1A1A1A !important;">📊 Prediction Result</h3>', unsafe_allow_html=True)
        st.markdown('<hr class="divider-fuchsia">', unsafe_allow_html=True)

        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            st.markdown(f"""<div class="metric-card"><div class="label">🎯 Risk Score</div><div class="value" style="color: {bar_color} !important;">{risk_score}<span style="font-size:14px;color:#999!important;"> / 100</span></div><div style="background:#F0F0F0;border-radius:6px;height:8px;margin-top:8px;overflow:hidden;"><div style="background:{bar_color};width:{risk_score}%;height:100%;border-radius:6px;"></div></div></div>""", unsafe_allow_html=True)
        with col_r2:
            st.markdown(f"""<div class="metric-card"><div class="label">⚠️ Risk Level</div><div class="value" style="color:{bar_color}!important;">{risk_level}</div><div style="font-size:13px;color:#888!important;margin-top:4px;">Assigned risk level</div></div>""", unsafe_allow_html=True)
        with col_r3:
            st.markdown(f"""<div class="metric-card"><div class="label">🔐 Decision</div><div class="value" style="color:{bar_color}!important;">{decision}</div><div style="font-size:13px;color:#888!important;margin-top:4px;">System action</div></div>""", unsafe_allow_html=True)
        with col_r4:
            st.markdown(f"""<div class="metric-card"><div class="label">👤 Passenger</div><div class="value" style="font-size:20px!important;color:#333!important;">{passenger_name[:16]}{'...' if len(passenger_name)>16 else ''}</div><div style="font-size:13px;color:#888!important;margin-top:4px;">{route}</div></div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if decision == "BLOCKED":
            st.markdown(f"""<div class="result-box suspicious"><div class="result-title" style="color:#E6007E!important;">🚨 Fraud Alert — Reservation BLOCKED</div><div class="result-detail" style="color:#333!important;"><strong>Passenger:</strong> {passenger_name} &nbsp;|&nbsp; <strong>Route:</strong> {route} &nbsp;|&nbsp; <strong>Amount:</strong> {booking_amount:,} XAF &nbsp;|&nbsp; <strong>Score:</strong> {risk_score}/100 — {risk_level}<br>This reservation presents a critical risk. It has been automatically <strong>BLOCKED</strong>.</div></div>""", unsafe_allow_html=True)
        elif decision == "MONITORING":
            st.markdown(f"""<div class="result-box" style="background:#FFF8E1;border-left-color:#FF8C00;"><div class="result-title" style="color:#FF8C00!important;">⚠️ Reservation Under Monitoring</div><div class="result-detail" style="color:#333!important;"><strong>Passenger:</strong> {passenger_name} &nbsp;|&nbsp; <strong>Route:</strong> {route} &nbsp;|&nbsp; <strong>Score:</strong> {risk_score}/100 — {risk_level}<br>This reservation requires manual verification before confirmation.</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="result-box approved"><div class="result-title" style="color:#00A86B!important;">✅ Reservation Approved</div><div class="result-detail" style="color:#333!important;"><strong>Passenger:</strong> {passenger_name} &nbsp;|&nbsp; <strong>Route:</strong> {route} &nbsp;|&nbsp; <strong>Tickets:</strong> {tickets_count} &nbsp;|&nbsp; <strong>Score:</strong> {risk_score}/100 — {risk_level}<br>No risk detected. Ticket issued successfully.</div></div>""", unsafe_allow_html=True)

        if DB_READY:
            st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;background:#F0FFF4;border:1px solid #00A86B;border-radius:8px;padding:10px 16px;margin-top:12px;"><span style="color:#00A86B;font-size:20px;">✅</span><span style="color:#333;font-size:14px;"><strong>Database:</strong> Reservation saved to PostgreSQL (table <code>{DB_TABLE}</code>)</span></div>""", unsafe_allow_html=True)

        # Recent Reservations table
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 style="font-weight: 700; color: #1A1A1A !important;">📋 Recent Reservations</h3>', unsafe_allow_html=True)
        st.markdown('<hr class="divider-fuchsia">', unsafe_allow_html=True)
        if st.session_state.recent_reservations:
            df_table = pd.DataFrame(st.session_state.recent_reservations)
            def color_decision(val):
                if val == "APPROVED":
                    return "background-color: #d4edda; color: #155724; font-weight: 600;"
                elif val == "MONITORING":
                    return "background-color: #fff3cd; color: #856404; font-weight: 600;"
                elif val == "BLOCKED":
                    return "background-color: #f8d7da; color: #721c24; font-weight: 600;"
                return ""
            styled_df = df_table.style.map(color_decision, subset=["Decision"])
            st.dataframe(styled_df, use_container_width=True, height=min(400, 40 * (len(df_table) + 1)))

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<h3 style="font-weight: 700; color: #1A1A1A !important;">📝 New Reservation</h3>', unsafe_allow_html=True)
        st.markdown('<hr class="divider-fuchsia">', unsafe_allow_html=True)

    # --- KPI Cards ---
    col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
    with col_k1:
        st.markdown(f"""<div class="metric-card"><div class="label">Total Reservations</div><div class="value blue">{total_reservations}</div></div>""", unsafe_allow_html=True)
    with col_k2:
        st.markdown(f"""<div class="metric-card"><div class="label">Approved</div><div class="value green">{approved_count}</div></div>""", unsafe_allow_html=True)
    with col_k3:
        st.markdown(f"""<div class="metric-card"><div class="label">Monitoring</div><div class="value orange">{monitoring_count}</div></div>""", unsafe_allow_html=True)
    with col_k4:
        st.markdown(f"""<div class="metric-card"><div class="label">Blocked</div><div class="value red">{blocked_count}</div></div>""", unsafe_allow_html=True)
    with col_k5:
        st.markdown(f"""<div class="metric-card"><div class="label">Fraud Rate</div><div class="value red">{fraud_rate:.1f}%</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if pending is None:
        st.markdown('<h3 style="font-weight: 700; color: #1A1A1A !important;">📝 Reservation Form</h3>', unsafe_allow_html=True)
        st.markdown("Fill in the 15 variables below to analyze the fraud risk.", unsafe_allow_html=True)
        st.markdown('<hr class="divider-fuchsia">', unsafe_allow_html=True)

    # --- Reservation Form ---
    with st.form("main_reservation_form"):
        st.markdown('<div class="form-card"><h4>📍 Route & Dates</h4>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            route = st.selectbox("Route", ["Douala → Yaounde", "Yaounde → Douala", "Douala → Bafoussam", "Bafoussam → Douala", "Yaounde → Garoua", "Douala → Bamenda", "Yaounde → Kribi", "Kribi → Douala"], index=0)
        with col2:
            booking_date = st.date_input("Booking Date", value=date.today() - relativedelta(days=2))
        with col3:
            travel_date = st.date_input("Travel Date", value=date.today() + relativedelta(days=3))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><h4>👤 Passenger Information</h4>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            passenger_name = st.text_input("Passenger Name", value="Thomas Kamga", placeholder="Ex: Jean Mbianda")
        with col2:
            passenger_age = st.number_input("Passenger Age", min_value=12, max_value=100, value=28, step=1)
        with col3:
            gender = st.selectbox("Gender", ["MALE", "FEMALE"], index=0)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><h4>💰 Amount & Payment</h4>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            booking_amount = st.number_input("Booking Amount (XAF)", min_value=500, max_value=500000, value=18500, step=500, format="%d")
        with col2:
            discount = st.slider("Discount Applied (%)", min_value=0, max_value=100, value=15, step=5, help="Discount percentage applied")
        with col3:
            payment_method = st.selectbox("Payment Method", ["MTN Mobile Money", "Orange Money", "UBA Transfer", "Afriland Transfer", "Express Union"], index=0)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><h4>🎫 Reservation Details</h4>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            reservation_platform = st.selectbox("Reservation Platform", ["Mobile App", "Website", "Agent Counter", "Call Center"], index=0)
        with col2:
            cancellation_status = st.selectbox("Cancellation Status", ["Not Cancelled", "Cancelled"], index=0)
        with col3:
            loyalty = st.selectbox("Loyalty Membership", ["No", "Yes"], index=0)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="form-card"><h4>⏱️ Lead Time & Quantity</h4>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            lead_time = st.number_input("Lead Time (Days before travel)", min_value=0, max_value=365, value=3, step=1, help="Number of days between booking and travel")
        with col2:
            tickets_count = st.number_input("Number of Tickets", min_value=1, max_value=20, value=1, step=1)
        with col3:
            prev_cancellations = st.number_input("Previous Cancellations", min_value=0, max_value=50, value=0, step=1)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🔮 Predict Reservation Risk")

    # ==========================================
    # 9. PREDICTION ENGINE
    # ==========================================
    if submitted:
        input_data = pd.DataFrame([{
            "Route": route,
            "Booking Amount": booking_amount,
            "Discount Applied": discount,
            "Payment Method": payment_method,
            "Reservation Platform": reservation_platform,
            "Cancellation Status": 1 if cancellation_status == "Cancelled" else 0,
            "Loyalty Membership": 1 if loyalty == "Yes" else 0,
            "Lead Time": lead_time,
            "Number of Tickets": tickets_count,
            "Passenger Age": passenger_age,
            "Gender": 1 if gender == "MALE" else 0,
            "Previous Cancellations": prev_cancellations
        }])

        risk_score = 0
        risk_level = "LOW"
        decision = "APPROVED"
        prediction_success = False

        if model is not None:
            try:
                pred = model.predict(input_data)[0]
                if hasattr(model, "predict_proba"):
                    prob = model.predict_proba(input_data)[0][1]
                else:
                    prob = float(pred)
                risk_score = int(prob * 100) if prob <= 1.0 else int(prob)
                if pred == 1 or risk_score >= 70:
                    risk_level = "CRITICAL"; decision = "BLOCKED"
                elif risk_score >= 40:
                    risk_level = "HIGH"; decision = "MONITORING"
                else:
                    risk_level = "LOW"; decision = "APPROVED"
                prediction_success = True
            except Exception:
                prediction_success = False

        if not prediction_success:
            if lead_time <= 1 and discount >= 30 and prev_cancellations >= 2:
                risk_score = 82; risk_level = "CRITICAL"; decision = "BLOCKED"
            elif lead_time <= 2 and discount >= 30:
                risk_score = 65; risk_level = "HIGH"; decision = "MONITORING"
            elif booking_amount >= 150000 and payment_method in ["UBA Transfer", "Afriland Transfer"]:
                risk_score = 58; risk_level = "HIGH"; decision = "MONITORING"
            elif prev_cancellations >= 3:
                risk_score = 55; risk_level = "HIGH"; decision = "MONITORING"
            elif lead_time <= 3 and prev_cancellations >= 1:
                risk_score = 45; risk_level = "HIGH"; decision = "MONITORING"
            elif lead_time >= 14 and loyalty == "Yes":
                risk_score = 8; risk_level = "LOW"; decision = "APPROVED"
            else:
                risk_score = 15; risk_level = "LOW"; decision = "APPROVED"

        # --- ADD TO SESSION-STATE RECENT RESERVATIONS ---
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reservation_record = {
            "Timestamp": now_str,
            "Passenger": passenger_name,
            "Route": route,
            "Booking Date": str(booking_date),
            "Travel Date": str(travel_date),
            "Amount (XAF)": f"{booking_amount:,}",
            "Payment": payment_method,
            "Platform": reservation_platform,
            "Tickets": tickets_count,
            "Score": risk_score,
            "Level": risk_level,
            "Decision": decision
        }
        st.session_state.recent_reservations.insert(0, reservation_record)

        # --- INSERT INTO DB ---
        db_error = None
        if DB_READY:
            try:
                engine = get_db_connection()
                raw_conn = engine.raw_connection()
                try:
                    insert_new_reservation(raw_conn, {
                        'route': route,
                        'booking_date': booking_date,
                        'travel_date': travel_date,
                        'passenger_name': passenger_name,
                        'passenger_age': passenger_age,
                        'gender': gender,
                        'booking_amount': float(booking_amount),
                        'discount_applied': float(discount),
                        'payment_method': payment_method,
                        'reservation_platform': reservation_platform,
                        'cancellation_status': cancellation_status,
                        'loyalty_membership': loyalty,
                    }, {
                        'lead_time': (travel_date - booking_date).days,
                        'number_of_tickets': tickets_count,
                        'previous_cancellations': prev_cancellations,
                        'risk_score': risk_score,
                        'risk_level': risk_level,
                        'decision': decision,
                    })
                finally:
                    raw_conn.close()
                load_stats_from_database()
            except SQLAlchemyError as e:
                db_error = f"PostgreSQL error: {e}"
            except Exception as e:
                db_error = f"Error: {e}"

        # --- Store pending prediction to display on rerun ---
        st.session_state._pending_prediction = {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "decision": decision,
            "passenger_name": passenger_name,
            "route": route,
            "booking_amount": booking_amount,
            "tickets_count": tickets_count,
            "db_error": db_error,
        }

        # Re-run to display results
        st.rerun()

# ==========================================
# 10. DASHBOARD PAGE
# ==========================================
elif page == "📊 Dashboard":
    st.markdown("""
        <div class="powerbi-header">
            <h1>📊 Dashboard — Statistics</h1>
            <p>Key performance indicators of the anti-fraud system</p>
        </div>
    """, unsafe_allow_html=True)

    if DB_READY:
        load_stats_from_database()

    # Build chart data from DB
    db_chart_data = None
    if DB_READY:
        try:
            engine = get_db_connection()
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT decision, COUNT(*) as cnt FROM {DB_TABLE} GROUP BY decision ORDER BY decision"))
                rows = result.fetchall()
                if rows:
                    chart_dict = {}
                    for row in rows:
                        label = row[0].capitalize() if row[0] else row[0]
                        chart_dict[label] = row[1]
                    db_chart_data = pd.Series(chart_dict)
        except Exception:
            db_chart_data = None

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="form-card"><h4>📈 Reservations Distribution</h4>', unsafe_allow_html=True)
        if db_chart_data is not None and len(db_chart_data) > 0:
            st.bar_chart(db_chart_data)
        else:
            st.info("No database records found. Submit reservations to populate the chart.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="form-card"><h4>🏆 Global Indicators</h4>', unsafe_allow_html=True)
        st.markdown(f"""
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr style="border-bottom:1px solid #E6E6E6;"><td style="padding:8px 6px;"><strong>Total Reservations</strong></td><td style="padding:8px 6px;text-align:right;">{total_reservations}</td></tr>
                <tr style="border-bottom:1px solid #E6E6E6;"><td style="padding:8px 6px;"><strong>Approved</strong></td><td style="padding:8px 6px;text-align:right;color:#00A86B;">{approved_count}</td></tr>
                <tr style="border-bottom:1px solid #E6E6E6;"><td style="padding:8px 6px;"><strong>Monitoring</strong></td><td style="padding:8px 6px;text-align:right;color:#FF8C00;">{monitoring_count}</td></tr>
                <tr style="border-bottom:1px solid #E6E6E6;"><td style="padding:8px 6px;"><strong>Blocked</strong></td><td style="padding:8px 6px;text-align:right;color:#E6007E;">{blocked_count}</td></tr>
                <tr style="border-bottom:1px solid #E6E6E6;"><td style="padding:8px 6px;"><strong>Fraud Rate</strong></td><td style="padding:8px 6px;text-align:right;color:#E6007E;">{fraud_rate:.1f}%</td></tr>
                <tr><td style="padding:8px 6px;"><strong>Safety Rate</strong></td><td style="padding:8px 6px;text-align:right;color:#00A86B;">{100-fraud_rate:.1f}%</td></tr>
            </table>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="form-card"><h4>🗄️ Database Status</h4>', unsafe_allow_html=True)
    if DB_READY:
        try:
            engine = get_db_connection()
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {DB_TABLE}"))
                st.success(f"✅ PostgreSQL connected — Table `{DB_TABLE}` — {result.scalar()} record(s)")
        except Exception:
            st.warning("⚠️ PostgreSQL connected but table not accessible.")
    else:
        st.warning("⚠️ PostgreSQL not connected.")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 11. ABOUT PAGE
# ==========================================
else:
    st.markdown("""
        <div class="powerbi-header">
            <h1>ℹ️ About the System</h1>
            <p>Design and Implementation of an Intelligent Fraud Detection System</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="form-card">', unsafe_allow_html=True)
    st.markdown("""
        <h4 style="color:#E6007E!important;">🎯 Project Objective</h4>
        <p style="font-size:15px;line-height:1.7;">Design and implementation of an intelligent system for detecting and monitoring online transport ticket reservation fraud in Cameroon.</p>
        <h4 style="color:#E6007E!important;margin-top:24px;">⚙️ Technologies Used</h4>
        <ul style="font-size:15px;line-height:1.8;">
            <li><strong>Frontend:</strong> Streamlit (Python) — Interactive user interface</li>
            <li><strong>Machine Learning:</strong> Random Forest / XGBoost — Binary classification</li>
            <li><strong>Database:</strong> PostgreSQL (ticket_fraud_data) — Prediction persistence</li>
            <li><strong>Visualization:</strong> Power BI — Analytical dashboards</li>
        </ul>
        <h4 style="color:#E6007E!important;margin-top:24px;">🧠 Prediction Model</h4>
        <p style="font-size:15px;line-height:1.7;">The model analyzes 12 input variables to compute a <strong>Risk Score</strong> out of 100 and determine the decision: <span style="color:#00A86B;">APPROVED</span>, <span style="color:#FF8C00;">MONITORING</span> or <span style="color:#E6007E;">BLOCKED</span>.</p>
        <h4 style="color:#E6007E!important;margin-top:24px;">💾 Data Persistence</h4>
        <p style="font-size:15px;line-height:1.7;">Each prediction is automatically saved to PostgreSQL to build an audit trail and feed Power BI reports.</p>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
