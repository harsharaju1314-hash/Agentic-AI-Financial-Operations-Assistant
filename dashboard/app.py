import datetime
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import Customer, Merchant, Transaction, FraudAlert, AgentExecutionLog
from database.queries import (
    get_financial_summary_metrics,
    get_top_merchants_by_volume,
    get_customer_spending_summary,
)
from agents.orchestrator import FinancialOperationsOrchestrator
from ml.fraud_detector import FraudDetector

# Streamlit Page Setup
st.set_page_config(
    page_title="FinOps AI | Multi-Agent Operations & Fraud Analytics",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F8FAFC;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .agent-pill {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.4rem;
        background-color: #E0E7FF;
        color: #3730A3;
    }
    .alert-high {
        color: #DC2626;
        font-weight: bold;
    }
    .alert-medium {
        color: #D97706;
        font-weight: bold;
    }
    .alert-low {
        color: #16A34A;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_orchestrator():
    return FinancialOperationsOrchestrator()


@st.cache_resource
def get_fraud_detector():
    detector = FraudDetector()
    detector.load()
    return detector


def main():
    # Sidebar
    st.sidebar.image("https://img.icons8.com/fluency/96/bank-building.png", width=64)
    st.sidebar.title("FinOps AI Assistant")
    st.sidebar.caption("Enterprise Risk & Agentic Operations")

    nav_selection = st.sidebar.radio(
        "Navigation",
        [
            "📊 Executive Dashboard",
            "🤖 Multi-Agent AI Console",
            "🚨 Fraud Alerts & Human Approval",
            "🔍 Customer & Merchant Drilldown",
            "🛡️ Ad-Hoc Fraud Detection",
            "📋 Agent Audit Logs",
        ],
    )

    db: Session = SessionLocal()

    try:
        if nav_selection == "📊 Executive Dashboard":
            render_executive_dashboard(db)
        elif nav_selection == "🤖 Multi-Agent AI Console":
            render_agent_console(db)
        elif nav_selection == "🚨 Fraud Alerts & Human Approval":
            render_fraud_alerts(db)
        elif nav_selection == "🔍 Customer & Merchant Drilldown":
            render_drilldown(db)
        elif nav_selection == "🛡️ Ad-Hoc Fraud Detection":
            render_adhoc_fraud(db)
        elif nav_selection == "📋 Agent Audit Logs":
            render_audit_logs(db)
    finally:
        db.close()


def render_executive_dashboard(db: Session):
    st.markdown('<div class="main-header">💳 Financial Operations & Risk Overview</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time transaction volume, anomaly detection KPIs, and operational health metrics.</div>', unsafe_allow_html=True)

    metrics = get_financial_summary_metrics(db)

    # Metric Cards Row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Total Transactions", f"{metrics['total_transactions']:,}")
    with c2:
        st.metric("Total Volume", f"${metrics['total_volume_usd']:,.2f}")
    with c3:
        st.metric("Avg Transaction", f"${metrics['average_transaction_usd']:,.2f}")
    with c4:
        st.metric("High-Risk Txns", f"{metrics['high_risk_transactions']:,}", delta=f"{metrics['flagged_ratio_pct']}% of total", delta_color="inverse")
    with c5:
        st.metric("Pending Alerts", f"{metrics['pending_fraud_alerts']:,}", delta="Requires Review", delta_color="off")

    st.markdown("---")

    # Filters Row
    st.subheader("Filter Transactions")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        selected_category = st.selectbox(
            "Category Filter",
            ["All"] + [c[0] for c in db.query(Transaction.category).distinct().all()],
        )
    with fc2:
        selected_risk = st.selectbox("Risk Level Filter", ["All", "HIGH", "MEDIUM", "LOW"])
    with fc3:
        limit_rows = st.slider("Display Limit", min_value=100, max_value=2000, value=500, step=100)

    # Query filtered transactions
    query = db.query(Transaction)
    if selected_category != "All":
        query = query.filter(Transaction.category == selected_category)
    if selected_risk != "All":
        query = query.filter(Transaction.risk_level == selected_risk)

    records = query.order_by(Transaction.timestamp.desc()).limit(limit_rows).all()
    df_txns = pd.DataFrame([
        {
            "transaction_id": t.transaction_id,
            "customer_id": t.customer_id,
            "merchant_id": t.merchant_id,
            "amount": t.amount,
            "category": t.category,
            "payment_method": t.payment_method,
            "status": t.status,
            "risk_level": t.risk_level,
            "anomaly_score": t.anomaly_score,
            "timestamp": t.timestamp,
        }
        for t in records
    ])

    if df_txns.empty:
        st.warning("No transactions match the selected filters.")
        return

    # Visualizations Row
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("📅 Daily Transaction Volume & Value")
        df_txns["date"] = pd.to_datetime(df_txns["timestamp"]).dt.date
        df_daily = df_txns.groupby("date").agg({"amount": "sum", "transaction_id": "count"}).reset_index()
        fig_daily = px.line(
            df_daily,
            x="date",
            y="amount",
            title="Daily Total Transaction Volume (USD)",
            markers=True,
            line_shape="spline",
            labels={"amount": "Volume (USD)", "date": "Date"},
        )
        fig_daily.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_daily, use_container_width=True)

    with col_chart2:
        st.subheader("📊 Category Distribution by Dollar Volume")
        df_cat = df_txns.groupby("category")["amount"].sum().reset_index()
        fig_cat = px.pie(
            df_cat,
            values="amount",
            names="category",
            title="Total Spend Share by Category",
            hole=0.4,
        )
        fig_cat.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_cat, use_container_width=True)

    # Secondary Charts Row
    col_chart3, col_chart4 = st.columns(2)

    with col_chart3:
        st.subheader("🎯 Isolation Forest Anomaly Score Distribution")
        fig_hist = px.histogram(
            df_txns,
            x="anomaly_score",
            color="risk_level",
            nbins=30,
            title="ML Anomaly Score Spread (Higher = More Anomalous)",
            color_discrete_map={"LOW": "#10B981", "MEDIUM": "#F59E0B", "HIGH": "#EF4444"},
        )
        fig_hist.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_chart4:
        st.subheader("🏆 Top Merchants by Transaction Volume")
        top_merchants = get_top_merchants_by_volume(db, limit=5)
        df_top_m = pd.DataFrame(top_merchants)
        if not df_top_m.empty:
            fig_merch = px.bar(
                df_top_m,
                x="merchant_name",
                y="total_volume_usd",
                color="category",
                title="Top 5 Volume Generating Merchants",
                labels={"total_volume_usd": "Volume (USD)", "merchant_name": "Merchant"},
            )
            fig_merch.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_merch, use_container_width=True)

    # Data Table
    st.subheader("Recent Transactions")
    st.dataframe(
        df_txns.head(50),
        use_container_width=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f"),
            "anomaly_score": st.column_config.ProgressColumn("Anomaly Score", min_value=0.0, max_value=1.0, format="%.3f"),
        },
    )


def render_agent_console(db: Session):
    st.markdown('<div class="main-header">🤖 Multi-Agent AI Operations Console</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">LangGraph orchestrated agents: SQL Retrieval, Transaction Analytics, Isolation Forest Fraud Investigation, and Executive Reporting.</div>', unsafe_allow_html=True)

    orch = get_orchestrator()

    # Pre-built Prompt Suggestions
    st.write("**Quick Prompt Templates:**")
    qc1, qc2, qc3 = st.columns(3)
    prompt_input = ""
    with qc1:
        if st.button("🔎 Investigate unusual transactions for C1002"):
            prompt_input = "Find unusual transactions for customer C1002."
    with qc2:
        if st.button("📊 Summarize top five merchants by volume"):
            prompt_input = "Summarize the top five merchants by transaction volume."
    with qc3:
        if st.button("🚨 Investigate high risk transactions"):
            prompt_input = "Show high risk fraud transactions with high anomaly score."

    user_query = st.text_input("Enter natural language request for AI agents:", value=prompt_input, placeholder="e.g. Find unusual transactions for customer C1002.")

    if st.button("🚀 Dispatch to Agent Swarm", type="primary"):
        if not user_query.strip():
            st.warning("Please enter a question or query.")
            return

        with st.spinner("Multi-Agent Orchestration in progress..."):
            result = orch.execute_query(user_query=user_query)

        # Execution Trail Header
        st.success(f"**Orchestrator Intent:** `{result.get('intent')}`")

        # Routed Agents Pills
        st.write("**Specialized Agents Executed:**")
        routed_html = "".join([f'<span class="agent-pill">🤖 {agent}</span>' for agent in result.get("routed_agents", [])])
        st.markdown(routed_html, unsafe_allow_html=True)

        st.markdown("---")

        # Response
        st.markdown(result.get("final_response", ""))

        # Technical Provenance Collapsible
        with st.expander("🛠️ Inspect Agent Execution Trail & SQL Telemetry"):
            st.write(f"**Generated SQL Query:**")
            st.code(result.get("sql_query") or "No direct SQL query executed", language="sql")

            st.write("**Supporting Transaction Identifiers:**")
            st.write(result.get("supporting_transactions") or "None")

            st.write("**Detailed Agent Step Execution Logs:**")
            st.json(result.get("agent_logs", []))


def render_fraud_alerts(db: Session):
    st.markdown('<div class="main-header">🚨 Fraud Alert Queue & Human-in-the-Loop Review</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Review transactions flagged by Scikit-learn Isolation Forest. Apply human analyst approvals before account freezes or reversals.</div>', unsafe_allow_html=True)

    status_filter = st.selectbox("Alert Status", ["PENDING_REVIEW", "APPROVED_ACTION", "DISMISSED", "ALL"])

    query = db.query(FraudAlert)
    if status_filter != "ALL":
        query = query.filter(FraudAlert.status == status_filter)

    alerts = query.order_by(FraudAlert.created_at.desc()).limit(20).all()

    if not alerts:
        st.info(f"No fraud alerts found for status '{status_filter}'.")
        return

    st.write(f"Showing **{len(alerts)}** alerts:")

    for alert in alerts:
        with st.container():
            st.markdown(f"#### ⚠️ Alert `{alert.alert_id}` | Transaction: `{alert.transaction_id}`")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**Customer:** `{alert.customer_id}`")
            with col2:
                st.write(f"**Risk Level:** `{alert.risk_level}`")
            with col3:
                st.write(f"**Anomaly Score:** `{alert.anomaly_score:.4f}`")
            with col4:
                st.write(f"**Current Status:** `{alert.status}`")

            st.info(f"**Flag Reason:** {alert.reason}")

            if alert.status == "PENDING_REVIEW":
                ac1, ac2, ac3 = st.columns([1, 1, 2])
                with ac1:
                    if st.button("❄️ Freeze Account", key=f"freeze_{alert.alert_id}"):
                        alert.status = "APPROVED_ACTION"
                        alert.action_taken = "ACCOUNT_FROZEN"
                        alert.reviewed_by = "Lead_Risk_Analyst"
                        alert.resolution_notes = "Customer account frozen following high anomaly score detection."
                        cust = db.query(Customer).filter(Customer.customer_id == alert.customer_id).first()
                        if cust:
                            cust.account_status = "FROZEN"
                        db.commit()
                        st.success(f"Customer `{alert.customer_id}` account frozen.")
                        st.rerun()

                with ac2:
                    if st.button("↩️ Reverse Charge", key=f"refund_{alert.alert_id}"):
                        alert.status = "APPROVED_ACTION"
                        alert.action_taken = "TRANSACTION_REVERSED"
                        alert.reviewed_by = "Lead_Risk_Analyst"
                        alert.resolution_notes = "Transaction reversed and refunded."
                        txn = db.query(Transaction).filter(Transaction.transaction_id == alert.transaction_id).first()
                        if txn:
                            txn.status = "REFUNDED"
                        db.commit()
                        st.success(f"Transaction `{alert.transaction_id}` refunded.")
                        st.rerun()

                with ac3:
                    if st.button("✅ Dismiss (False Positive)", key=f"dismiss_{alert.alert_id}"):
                        alert.status = "DISMISSED"
                        alert.action_taken = "FALSE_POSITIVE"
                        alert.reviewed_by = "Lead_Risk_Analyst"
                        alert.resolution_notes = "Customer confirmed transaction was legitimate."
                        db.commit()
                        st.info(f"Alert `{alert.alert_id}` marked as false positive.")
                        st.rerun()
            else:
                st.write(f"**Resolution:** Action `{alert.action_taken}` applied by `{alert.reviewed_by}`. Notes: {alert.resolution_notes}")

            st.markdown("---")


def render_drilldown(db: Session):
    st.markdown('<div class="main-header">🔍 Customer & Merchant Intelligence Drilldown</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Deep-dive analysis of historical spending baselines, velocity, and anomaly trends.</div>', unsafe_allow_html=True)

    tab_cust, tab_merch = st.tabs(["👤 Customer Intelligence", "🏪 Merchant Intelligence"])

    with tab_cust:
        cust_list = [c[0] for c in db.query(Customer.customer_id).limit(100).all()]
        selected_cid = st.selectbox("Select Customer ID", cust_list, index=0)

        summary = get_customer_spending_summary(db, selected_cid)
        if summary:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Total Spent", f"${summary['total_spent_usd']:,.2f}")
            with c2:
                st.metric("Total Transactions", summary["total_transactions"])
            with c3:
                st.metric("Average Ticket", f"${summary['average_transaction_usd']:,.2f}")
            with c4:
                st.metric("Flagged Count", summary["flagged_transactions_count"])

            st.write(f"**Customer Name:** {summary['name']} | **Status:** `{summary['account_status']}` | **Risk:** `{summary['risk_profile']}`")
            st.write(f"**Location:** {summary['home_city']}, {summary['home_country']}")

            st.subheader("Recent Customer Transactions")
            df_recent = pd.DataFrame(summary["recent_transactions"])
            if not df_recent.empty:
                st.dataframe(df_recent, use_container_width=True)

    with tab_merch:
        merch_list = [m[0] for m in db.query(Merchant.merchant_id).limit(100).all()]
        selected_mid = st.selectbox("Select Merchant ID", merch_list, index=0)
        merchant = db.query(Merchant).filter(Merchant.merchant_id == selected_mid).first()

        if merchant:
            st.write(f"### {merchant.name} (`{merchant.merchant_id}`)")
            st.write(f"**Category:** {merchant.category} | **Location:** {merchant.city}, {merchant.country} | **Risk Weight:** {merchant.base_risk_score}")

            txns = db.query(Transaction).filter(Transaction.merchant_id == selected_mid).all()
            if txns:
                df_m = pd.DataFrame([{"amount": t.amount, "status": t.status, "risk_level": t.risk_level, "timestamp": t.timestamp} for t in txns])
                m_vol = df_m["amount"].sum()
                st.metric("Total Merchant Volume", f"${m_vol:,.2f}", f"{len(df_m)} transactions")
                st.dataframe(df_m.head(20), use_container_width=True)


def render_adhoc_fraud(db: Session):
    st.markdown('<div class="main-header">🛡️ On-Demand ML Anomaly Scoring</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Score any arbitrary or simulated transaction directly against the trained Isolation Forest model.</div>', unsafe_allow_html=True)

    detector = get_fraud_detector()

    with st.form("adhoc_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            amount = st.number_input("Transaction Amount ($)", min_value=1.0, value=2500.0, step=50.0)
            hist_avg = st.number_input("Customer Historical Avg Spend ($)", min_value=5.0, value=65.0, step=10.0)
        with c2:
            category = st.selectbox("Merchant Category", ["Crypto Exchange", "Wire Transfer", "Luxury", "Electronics", "Travel", "Groceries", "Dining", "Retail"])
            payment_method = st.selectbox("Payment Rail", ["CREDIT_CARD", "DEBIT_CARD", "WIRE_TRANSFER", "CRYPTO", "ACH"])
        with c3:
            txn_hour = st.slider("Hour of Transaction (0 to 23)", min_value=0, max_value=23, value=3)
            location = st.text_input("Transaction Location", value="Lagos, NG")

        submitted = st.form_submit_button("⚡ Evaluate Anomaly Score", type="primary")

    if submitted:
        sample_txn = {
            "amount": amount,
            "historical_avg_spending": hist_avg,
            "category": category,
            "payment_method": payment_method,
            "timestamp": datetime.datetime(2026, 3, 15, txn_hour, 15, 0),
            "location": location,
        }
        res = detector.score_single(sample_txn)

        st.subheader("Evaluation Result")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.metric("Anomaly Score", f"{res['anomaly_score']:.4f}")
        with rc2:
            risk = res["risk_level"]
            color = "inverse" if risk == "HIGH" else "normal"
            st.metric("Risk Classification", risk, delta="Action Required" if risk == "HIGH" else "Safe", delta_color=color)
        with rc3:
            st.metric("Flagged Status", "YES" if res["is_flagged"] else "NO")

        st.warning(f"**Analytical Reasoning:** {res['flagged_reason']}")


def render_audit_logs(db: Session):
    st.markdown('<div class="main-header">📋 Agent Execution Audit Trail</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Immutable record of all agent queries, SQL executed, and execution latencies.</div>', unsafe_allow_html=True)

    logs = db.query(AgentExecutionLog).order_by(AgentExecutionLog.created_at.desc()).limit(100).all()
    if logs:
        df_logs = pd.DataFrame([
            {
                "log_id": l.log_id,
                "session_id": l.session_id,
                "agent_name": l.agent_name,
                "action_taken": l.action_taken,
                "execution_time_ms": l.execution_time_ms,
                "sql_query": l.sql_query,
                "details": l.details,
                "created_at": l.created_at,
            }
            for l in logs
        ])
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No agent logs recorded yet.")


if __name__ == "__main__":
    main()
