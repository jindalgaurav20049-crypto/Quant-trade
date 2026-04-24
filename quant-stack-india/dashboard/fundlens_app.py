"""FundLens prototype application surface in Streamlit."""

import streamlit as st

from fundlens.modes import EntitlementService, Mode


st.set_page_config(page_title="FundLens", page_icon="🔎", layout="wide")


def _init_state() -> None:
    if "fundlens_mode" not in st.session_state:
        st.session_state["fundlens_mode"] = Mode.BEGINNER.value
    if "fundlens_premium" not in st.session_state:
        st.session_state["fundlens_premium"] = False


def _selected_mode() -> Mode:
    return Mode(st.session_state["fundlens_mode"])


def _header(entitlement: EntitlementService, mode: Mode) -> None:
    st.title("FundLens")
    st.caption("See through the noise.")
    if not entitlement.can_use_mode(mode):
        st.warning("Advanced mode requires premium subscription.")


def _home_tab(mode: Mode) -> None:
    st.subheader("Home")
    if mode == Mode.BEGINNER:
        st.info("Default: SIP calculator and 5-metric quick card.")
        st.metric("Fund Health Score", "74", "+2")
        st.metric("Risk Level", "Moderate")
        st.metric("Cost (Expense Ratio)", "1.28%")
    else:
        st.info("Advanced dashboard: multi-factor summary and heatmap entry points.")
        st.metric("Composite Score", "78.4")
        st.metric("Sharpe", "1.12")
        st.metric("Sortino", "1.54")


def _compare_tab(mode: Mode, entitlement: EntitlementService) -> None:
    st.subheader("Compare")
    max_funds = entitlement.max_compare_funds(mode)
    fund_count = st.slider("Funds to compare", min_value=2, max_value=max_funds, value=2)
    st.caption(f"Mode limit applied: up to {max_funds} funds.")
    st.write(f"Comparing {fund_count} fund(s) in {mode.value} mode.")


def _screener_tab(entitlement: EntitlementService, mode: Mode) -> None:
    st.subheader("Screener")
    if entitlement.can_use_feature("custom_screener", mode):
        st.success("Custom screener available.")
    else:
        st.info("Upgrade to premium for custom screener.")


def main() -> None:
    _init_state()

    st.sidebar.header("Mode")
    st.sidebar.selectbox(
        "Experience",
        options=[Mode.BEGINNER.value, Mode.ADVANCED.value],
        key="fundlens_mode",
    )
    st.sidebar.toggle("Premium Subscription", key="fundlens_premium")

    mode = _selected_mode()
    entitlement = EntitlementService(has_premium=st.session_state["fundlens_premium"])

    _header(entitlement, mode)

    tabs = st.tabs(["Home", "Explore", "Compare", "Portfolio Insights", "Screener", "Profile"])

    with tabs[0]:
        _home_tab(mode)
    with tabs[1]:
        st.subheader("Explore")
        st.write("Universal search, category ranking, and benchmark-relative drill-down.")
    with tabs[2]:
        _compare_tab(mode, entitlement)
    with tabs[3]:
        st.subheader("Portfolio Insights")
        st.write("Overlap, concentration risk, and tax-aware scenario summaries.")
    with tabs[4]:
        _screener_tab(entitlement, mode)
    with tabs[5]:
        st.subheader("Profile")
        st.write("Subscription, exports, and personalization settings.")


if __name__ == "__main__":
    main()
