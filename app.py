import streamlit as st
import pandas as pd
import stripe
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="ResumaticAI — Stripe Dashboard", layout="wide")

st.title("ResumaticAI — Stripe Subscription Monitor")

# ── Sidebar: API Key ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input(
        "Stripe Secret Key",
        type="password",
        placeholder="sk_live_...",
        help="Your key is never saved to disk — it lives only in this browser session.",
    )
    st.caption("Find it at dashboard.stripe.com → Developers → API keys")

    if api_key:
        stripe.api_key = api_key
        st.success("Key loaded")
    else:
        st.info("Enter your Stripe Secret Key to load data.")

    st.divider()
    st.subheader("Date Range")
    days_back = st.selectbox("Look-back window", [30, 60, 90, 180, 365], index=2)
    since_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
    since_ts = int(since_dt.timestamp())

# ── Helpers ───────────────────────────────────────────────────────────────────

def stripe_list_all(method, **kwargs):
    """Auto-paginate any stripe list endpoint."""
    items = []
    has_more = True
    starting_after = None
    while has_more:
        params = dict(limit=100, **kwargs)
        if starting_after:
            params["starting_after"] = starting_after
        resp = method(**params)
        items.extend(resp.data)
        has_more = resp.has_more
        if has_more:
            starting_after = resp.data[-1].id
    return items


def cents_to_dollars(amount, currency="usd"):
    if currency and currency.lower() in ("jpy", "krw", "clp"):
        return amount
    return amount / 100


def fmt_usd(val):
    return f"${val:,.2f}"


# ── Main content ──────────────────────────────────────────────────────────────

if not api_key:
    st.info("Enter your Stripe Secret Key in the sidebar to get started.")
    st.stop()

with st.spinner("Fetching data from Stripe…"):
    try:
        # Active subscriptions
        active_subs = stripe_list_all(
            stripe.Subscription.list, status="active", expand=["data.customer"]
        )

        # Cancelled subscriptions in window
        canceled_subs = stripe_list_all(
            stripe.Subscription.list,
            status="canceled",
            created={"gte": since_ts},
            expand=["data.customer"],
        )

        # Open (unpaid) invoices
        open_invoices = stripe_list_all(stripe.Invoice.list, status="open")

        # Past-due subscriptions
        past_due_subs = stripe_list_all(
            stripe.Subscription.list, status="past_due", expand=["data.customer"]
        )

        # Failed charges in window (declined cards)
        all_charges = stripe_list_all(
            stripe.Charge.list,
            created={"gte": since_ts},
        )
        failed_charges = [c for c in all_charges if c.status == "failed"]

    except stripe.error.AuthenticationError:
        st.error("Invalid API key. Please check the key in the sidebar and try again.")
        st.stop()
    except Exception as e:
        st.error(f"Stripe error: {e}")
        st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────────────

mrr = 0
for s in active_subs:
    try:
        item = s.items.data[0]
        price = item.price
        if price and price.unit_amount and price.recurring:
            amt = cents_to_dollars(price.unit_amount, s.currency)
            if price.recurring.interval == "year":
                amt = amt / 12
            mrr += amt
    except (IndexError, AttributeError):
        pass

unpaid_total = sum(
    cents_to_dollars(inv.amount_due, inv.currency) for inv in open_invoices
)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Active Subscribers", len(active_subs))
col2.metric("Est. MRR", fmt_usd(mrr))
col3.metric(f"Cancellations (last {days_back}d)", len(canceled_subs))
col4.metric(
    "Unpaid Balances",
    fmt_usd(unpaid_total),
    delta=f"{len(open_invoices)} open invoices",
    delta_color="inverse",
)
col5.metric(
    f"Failed Charges (last {days_back}d)",
    len(failed_charges),
    delta_color="inverse",
)

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Active Subscriptions",
        "New Subscribers",
        "Cancellations",
        "Unpaid Balances",
        "Failed Charges",
    ]
)

# ── Tab 1: Active Subscriptions ───────────────────────────────────────────────
with tab1:
    st.subheader(f"Active Subscriptions ({len(active_subs)})")
    if active_subs:
        rows = []
        for s in active_subs:
            cust = s.customer
            email = cust.email if hasattr(cust, "email") else "—"
            name = cust.name if hasattr(cust, "name") and cust.name else "—"
            try:
                item = s.items.data[0]
                price_obj = item.price
                plan = price_obj.nickname or price_obj.id
                amount = cents_to_dollars(price_obj.unit_amount or 0, s.currency)
                interval = price_obj.recurring.interval if price_obj.recurring else "—"
                # current_period_end moved to SubscriptionItem in newer API versions
                period_end = (
                    getattr(item, "current_period_end", None)
                    or getattr(s, "current_period_end", None)
                )
            except (IndexError, AttributeError):
                plan, amount, interval, period_end = "—", 0, "—", None
            rows.append(
                {
                    "Customer": name,
                    "Email": email,
                    "Plan": plan,
                    f"Amount ({(s.currency or 'usd').upper()})": fmt_usd(amount),
                    "Billing": interval,
                    "Status": s.status,
                    "Started": datetime.fromtimestamp(getattr(s, "start_date", None) or s.created, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "Next Billing": datetime.fromtimestamp(
                        period_end, tz=timezone.utc
                    ).strftime("%Y-%m-%d") if period_end else "—",
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No active subscriptions found.")

# ── Tab 2: New Subscribers Over Time ─────────────────────────────────────────
with tab2:
    st.subheader(f"New Subscribers — Last {days_back} Days")
    def get_start_date(s):
        return getattr(s, "start_date", None) or getattr(s, "created", None)

    new_subs = [s for s in active_subs if (get_start_date(s) or 0) >= since_ts]
    new_subs += [s for s in canceled_subs if (get_start_date(s) or 0) >= since_ts]

    if new_subs:
        dates = [
            datetime.fromtimestamp(get_start_date(s), tz=timezone.utc).date()
            for s in new_subs
            if get_start_date(s)
        ]
        df_new = pd.DataFrame({"date": dates})
        df_new = df_new.groupby("date").size().reset_index(name="New Subscribers")
        df_new["date"] = pd.to_datetime(df_new["date"])
        df_new = df_new.set_index("date").resample("D").sum().reset_index()
        st.line_chart(df_new.set_index("date"), use_container_width=True)
        st.caption(f"Total new sign-ups in this window: {len(new_subs)}")
    else:
        st.info("No new subscribers in this date range.")

# ── Tab 3: Cancellations ──────────────────────────────────────────────────────
with tab3:
    st.subheader(f"Cancellations — Last {days_back} Days ({len(canceled_subs)})")
    if canceled_subs:
        rows = []
        for s in canceled_subs:
            cust = s.customer
            email = cust.email if hasattr(cust, "email") else "—"
            name = cust.name if hasattr(cust, "name") and cust.name else "—"
            try:
                plan = s.items.data[0].price.nickname or s.items.data[0].price.id
            except (IndexError, AttributeError):
                plan = "—"
            canceled_at = s.canceled_at or s.ended_at
            rows.append(
                {
                    "Customer": name,
                    "Email": email,
                    "Plan": plan,
                    "Started": datetime.fromtimestamp(
                        getattr(s, "start_date", None) or s.created, tz=timezone.utc
                    ).strftime("%Y-%m-%d"),
                    "Cancelled": datetime.fromtimestamp(
                        canceled_at, tz=timezone.utc
                    ).strftime("%Y-%m-%d")
                    if canceled_at
                    else "—",
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(f"No cancellations in the last {days_back} days.")

# ── Tab 4: Unpaid Balances ────────────────────────────────────────────────────
with tab4:
    st.subheader(f"Unpaid / Open Invoices ({len(open_invoices)})")
    if open_invoices:
        rows = []
        for inv in open_invoices:
            rows.append(
                {
                    "Invoice ID": inv.id,
                    "Customer Email": inv.customer_email or "—",
                    "Amount Due": fmt_usd(
                        cents_to_dollars(inv.amount_due, inv.currency)
                    ),
                    "Currency": (inv.currency or "usd").upper(),
                    "Due Date": datetime.fromtimestamp(
                        inv.due_date, tz=timezone.utc
                    ).strftime("%Y-%m-%d")
                    if inv.due_date
                    else "—",
                    "Created": datetime.fromtimestamp(
                        inv.created, tz=timezone.utc
                    ).strftime("%Y-%m-%d"),
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Total Unpaid", fmt_usd(unpaid_total))
    else:
        st.success("No open invoices — you're all caught up!")

# ── Tab 5: Failed Charges ─────────────────────────────────────────────────────
with tab5:
    st.subheader(
        f"Failed / Declined Charges — Last {days_back} Days ({len(failed_charges)})"
    )
    if failed_charges:
        rows = []
        for c in failed_charges:
            rows.append(
                {
                    "Charge ID": c.id,
                    "Customer Email": c.billing_details.email
                    if c.billing_details and c.billing_details.email
                    else "—",
                    "Amount": fmt_usd(cents_to_dollars(c.amount, c.currency)),
                    "Failure Reason": c.failure_message or "—",
                    "Failure Code": c.failure_code or "—",
                    "Date": datetime.fromtimestamp(c.created, tz=timezone.utc).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                }
            )
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.success(f"No failed charges in the last {days_back} days.")
