import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Deal Structure What-If Builder", layout="wide")
st.title("Deal Structure & Commercial What-If Builder")
st.caption("B2B IT Services | Hours-based | Multi-year + Outcome models included")

# ====================== SIDEBAR INPUTS ======================
st.sidebar.header("Deal Inputs")

deal_name = st.sidebar.text_input("Deal Name", "Project Phoenix")

effort_hours = st.sidebar.number_input("Estimated Effort (Hours)", min_value=100, value=3200, step=50)
bill_rate = st.sidebar.number_input("Bill Rate ($/hour)", min_value=20.0, value=85.0, step=1.0)
cost_rate = st.sidebar.number_input("Internal Cost Rate ($/hour)", min_value=10.0, value=48.0, step=1.0)

desired_margin = st.sidebar.slider("Desired Margin %", 15, 45, 30)
contract_months = st.sidebar.number_input("Contract Length (Months)", min_value=3, value=24, step=1)
risk_buffer = st.sidebar.slider("Risk Buffer % (for Fixed Price)", 5, 25, 12)
discount = st.sidebar.slider("Discount %", 0, 25, 0)

st.sidebar.markdown("---")
st.sidebar.subheader("Hybrid & Outcome Settings")
hybrid_fixed_pct = st.sidebar.slider("Hybrid: % Fixed Price", 0, 100, 60)
gain_share_pct = st.sidebar.slider("Gain-share % of Value Pool", 0, 25, 10)
value_pool = st.sidebar.number_input("Estimated Client Value / Savings Pool ($)", min_value=0, value=450000, step=10000)

st.sidebar.markdown("---")
revenue_profile = st.sidebar.radio(
    "Revenue Timing Profile",
    ["Year-1 Heavy", "Ramp"],
    index=0
)

# ====================== CORE CALCULATIONS ======================

total_cost = effort_hours * cost_rate
base_revenue = effort_hours * bill_rate
discounted_bill_rate = bill_rate * (1 - discount / 100)
discounted_base_revenue = effort_hours * discounted_bill_rate

# ----- Fixed Price -----
fixed_price = discounted_base_revenue * (1 + risk_buffer / 100)
fixed_margin_abs = fixed_price - total_cost
fixed_margin_pct = (fixed_margin_abs / fixed_price * 100) if fixed_price > 0 else 0

# ----- T&M -----
tm_revenue = discounted_base_revenue
tm_margin_abs = tm_revenue - total_cost
tm_margin_pct = (tm_margin_abs / tm_revenue * 100) if tm_revenue > 0 else 0

# ----- Hybrid -----
fixed_portion = hybrid_fixed_pct / 100
tm_portion = 1 - fixed_portion
hybrid_revenue = (fixed_portion * fixed_price) + (tm_portion * tm_revenue)
hybrid_margin_abs = hybrid_revenue - total_cost
hybrid_margin_pct = (hybrid_margin_abs / hybrid_revenue * 100) if hybrid_revenue > 0 else 0

# ----- Outcome / Gain-share -----
# Base fee = 70% of discounted T&M revenue (you can change this logic)
base_fee = discounted_base_revenue * 0.70
gain_share_amount = value_pool * (gain_share_pct / 100)
outcome_revenue = base_fee + gain_share_amount
outcome_margin_abs = outcome_revenue - total_cost
outcome_margin_pct = (outcome_margin_abs / outcome_revenue * 100) if outcome_revenue > 0 else 0

# ====================== MULTI-YEAR CASH DISTRIBUTION ======================

def distribute_revenue(total_rev, months, profile):
    years = int(np.ceil(months / 12))
    yearly = [0.0] * years

    if profile == "Year-1 Heavy":
        if years == 1:
            yearly[0] = total_rev
        else:
            yearly[0] = total_rev * 0.58
            remaining = total_rev * 0.42
            for i in range(1, years):
                yearly[i] = remaining / (years - 1)
    else:  # Ramp
        if years == 1:
            yearly[0] = total_rev
        elif years == 2:
            yearly[0] = total_rev * 0.35
            yearly[1] = total_rev * 0.65
        else:
            # Simple progressive ramp
            weights = np.linspace(0.2, 0.45, years)
            weights = weights / weights.sum()
            yearly = (total_rev * weights).tolist()

    return [round(y, 0) for y in yearly]

fixed_yearly = distribute_revenue(fixed_price, contract_months, revenue_profile)
tm_yearly = distribute_revenue(tm_revenue, contract_months, revenue_profile)
hybrid_yearly = distribute_revenue(hybrid_revenue, contract_months, revenue_profile)
outcome_yearly = distribute_revenue(outcome_revenue, contract_months, revenue_profile)

# ====================== RISK SCORING ======================
def risk_level(model):
    if model == "Fixed Price":
        return "High"
    elif model == "Hybrid":
        return "Medium"
    elif model == "T&M":
        return "Low"
    else:
        return "Medium-High"

# ====================== COMPARISON TABLE ======================

data = {
    "Metric": [
        "Total Revenue",
        "Total Cost",
        "Gross Margin $",
        "Gross Margin %",
        "Year 1 Cash",
        "Risk Level",
        "Meets Desired Margin?"
    ],
    "Fixed Price": [
        f"${fixed_price:,.0f}",
        f"${total_cost:,.0f}",
        f"${fixed_margin_abs:,.0f}",
        f"{fixed_margin_pct:.1f}%",
        f"${fixed_yearly[0]:,.0f}",
        risk_level("Fixed Price"),
        "✅" if fixed_margin_pct >= desired_margin else "❌"
    ],
    "T&M": [
        f"${tm_revenue:,.0f}",
        f"${total_cost:,.0f}",
        f"${tm_margin_abs:,.0f}",
        f"{tm_margin_pct:.1f}%",
        f"${tm_yearly[0]:,.0f}",
        risk_level("T&M"),
        "✅" if tm_margin_pct >= desired_margin else "❌"
    ],
    "Hybrid": [
        f"${hybrid_revenue:,.0f}",
        f"${total_cost:,.0f}",
        f"${hybrid_margin_abs:,.0f}",
        f"{hybrid_margin_pct:.1f}%",
        f"${hybrid_yearly[0]:,.0f}",
        risk_level("Hybrid"),
        "✅" if hybrid_margin_pct >= desired_margin else "❌"
    ],
    "Outcome / Gain-share": [
        f"${outcome_revenue:,.0f}",
        f"${total_cost:,.0f}",
        f"${outcome_margin_abs:,.0f}",
        f"{outcome_margin_pct:.1f}%",
        f"${outcome_yearly[0]:,.0f}",
        risk_level("Outcome"),
        "✅" if outcome_margin_pct >= desired_margin else "❌"
    ]
}

df = pd.DataFrame(data)
st.subheader("Side-by-Side Comparison")
st.dataframe(df, use_container_width=True, hide_index=True)

# ====================== YEARLY BREAKDOWN ======================
st.subheader(f"Revenue by Year ({revenue_profile})")

yearly_df = pd.DataFrame({
    "Year": [f"Year {i+1}" for i in range(len(fixed_yearly))],
    "Fixed Price": fixed_yearly,
    "T&M": tm_yearly,
    "Hybrid": hybrid_yearly,
    "Outcome / Gain-share": outcome_yearly
})
st.dataframe(yearly_df.style.format("${:,.0f}"), use_container_width=True, hide_index=True)

# ====================== RECOMMENDATION ======================
st.markdown("---")
st.subheader("Recommendation")

scores = {
    "Fixed Price": fixed_margin_pct,
    "T&M": tm_margin_pct,
    "Hybrid": hybrid_margin_pct,
    "Outcome / Gain-share": outcome_margin_pct
}

# Simple recommendation logic
best = max(scores, key=scores.get)

if best == "Hybrid" and hybrid_margin_pct >= desired_margin:
    rec = f"**Hybrid** looks strongest. It balances margin protection with lower risk than pure Fixed Price."
elif best == "Fixed Price" and fixed_margin_pct >= desired_margin + 3:
    rec = f"**Fixed Price** delivers the highest margin. Use only if scope is well-defined and risk buffer is acceptable."
elif best == "T&M":
    rec = f"**T&M** is safest when scope is unclear. Margin is lower but risk is minimal."
else:
    rec = f"**Outcome / Gain-share** can unlock higher upside if the value pool is realistic and measurable."

st.success(f"Recommended structure: **{best}**")
st.write(rec)

st.info(f"**Current settings summary**: {effort_hours} hours | ${bill_rate}/hr bill rate | {contract_months} months | {discount}% discount | Risk buffer {risk_buffer}%")

# ====================== ASSUMPTIONS ======================
with st.expander("Key Assumptions & Notes"):
    st.markdown("""
    - **Fixed Price** = Discounted effort revenue × (1 + Risk Buffer)
    - **T&M** = Pure discounted effort revenue (no buffer)
    - **Hybrid** = Weighted combination of Fixed + T&M
    - **Outcome / Gain-share** = 70% of discounted effort as base fee + Gain-share % of the Value Pool
    - Year-1 Heavy ≈ 58% in Year 1, rest evenly spread
    - Ramp = Progressive increase across years
    - You can later connect this to Google Sheets to save deal scenarios
    """)