import streamlit as st
import pandas as pd
import stripe
import streamlit.components.v1 as components
from datetime import datetime, timedelta, timezone

st.set_page_config(
    page_title="Resumatic Subscription Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; }
[data-testid="stMetricLabel"] { font-size: 0.85rem; color: #888; }
</style>
""", unsafe_allow_html=True)

st.title("Resumatic Subscription Dashboard")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input(
        "Stripe Secret Key",
        type="password",
        placeholder="sk_live_...",
        help="Never saved to disk — lives only in this browser session.",
    )
    st.caption("dashboard.stripe.com → Developers → API keys")
    load_clicked = st.button("Load Data", type="primary", use_container_width=True)

    st.divider()
    st.subheader("Date Range")
    days_back = st.selectbox("Look-back window", [30, 60, 90, 180, 365], index=2)
    since_dt = datetime.now(timezone.utc) - timedelta(days=days_back)
    since_ts = int(since_dt.timestamp())

    if "loaded_at" in st.session_state:
        st.divider()
        st.caption(f"Last loaded: {st.session_state['loaded_at']}")
        if st.button("Refresh Data", use_container_width=True):
            st.session_state.pop("stripe_data", None)
            st.session_state.pop("loaded_at", None)
            st.rerun()

# ── Helpers ───────────────────────────────────────────────────────────────────

def stripe_list_all(method, **kwargs):
    items, has_more, starting_after = [], True, None
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
    return (amount or 0) / 100


def fmt_usd(val):
    return f"${val:,.2f}"


def filter_df(df, search_key):
    query = st.text_input("Search", placeholder="Filter by name, email, plan…", key=search_key, label_visibility="collapsed")
    if query:
        mask = df.apply(lambda col: col.astype(str).str.contains(query, case=False, na=False)).any(axis=1)
        return df[mask].reset_index(drop=True), list(df[mask].index)
    return df, list(range(len(df)))


# ── Customer detail panel ─────────────────────────────────────────────────────

def show_customer_details(cust_id, label, anchor_id):
    components.html(
        f"<script>var el=window.parent.document.getElementById('{anchor_id}');"
        "if(el)el.scrollIntoView({{behavior:'smooth',block:'start'}});</script>",
        height=0,
    )
    st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader(f"Customer Details — {label}")

        # Basic info
        try:
            stripe.api_key = api_key
            cust = stripe.Customer.retrieve(cust_id)
            d = cust.to_dict()

            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.markdown("**Contact**")
                st.markdown(f"Name: **{d.get('name') or '—'}**")
                st.markdown(f"Email: **{d.get('email') or '—'}**")
                st.markdown(f"Phone: **{d.get('phone') or '—'}**")

            with col_b:
                st.markdown("**Account**")
                st.markdown(f"Customer ID: `{d.get('id', cust_id)}`")
                created_ts = d.get("created")
                if created_ts:
                    st.markdown(f"Since: **{datetime.fromtimestamp(int(created_ts), tz=timezone.utc).strftime('%b %d, %Y')}**")
                raw_balance = int(d.get("balance") or 0)
                balance_label = "Credit" if raw_balance < 0 else "Balance Owed"
                bal_color = "green" if raw_balance <= 0 else "red"
                st.markdown(f"{balance_label}: <span style='color:{bal_color};font-weight:700'>{fmt_usd(cents_to_dollars(abs(raw_balance)))}</span>", unsafe_allow_html=True)

            with col_c:
                addr = d.get("address") or {}
                if isinstance(addr, dict):
                    parts = [v for v in [addr.get("line1"), addr.get("line2"), addr.get("city"), addr.get("state"), addr.get("postal_code"), addr.get("country")] if v]
                else:
                    parts = []
                st.markdown("**Address**")
                st.markdown(", ".join(parts) if parts else "—")
                meta = d.get("metadata") or {}
                if isinstance(meta, dict) and meta:
                    st.markdown("**Metadata**")
                    for k, v in meta.items():
                        st.markdown(f"`{k}`: {v}")
        except Exception as e:
            st.error(f"Could not load customer info: {e}")
            return

        st.divider()
        left, right = st.columns(2)

        # Cards on file
        with left:
            try:
                payment_methods = stripe_list_all(stripe.PaymentMethod.list, customer=cust_id, type="card")
                st.markdown("**Cards on File**")
                if payment_methods:
                    default_pm_id = (d.get("invoice_settings") or {}).get("default_payment_method")
                    card_rows = []
                    for pm in payment_methods:
                        try:
                            pmd = pm.to_dict()
                            card = pmd.get("card") or {}
                            card_rows.append({
                                "Brand": (card.get("brand") or "—").title(),
                                "Last 4": f"•••• {card.get('last4', '—')}",
                                "Expires": f"{int(card.get('exp_month', 0)):02d}/{int(card.get('exp_year', 0))}",
                                "Default": "✓" if pmd.get("id") == default_pm_id else "",
                            })
                        except Exception:
                            pass
                    if card_rows:
                        st.dataframe(pd.DataFrame(card_rows), use_container_width=True, hide_index=True)
                else:
                    st.caption("No cards on file.")
            except Exception as e:
                st.warning(f"Could not load cards: {e}")

        # Recent invoices
        with right:
            try:
                invoices = stripe_list_all(stripe.Invoice.list, customer=cust_id)[:10]
                st.markdown("**Recent Invoices**")
                if invoices:
                    inv_rows = []
                    for inv in invoices:
                        try:
                            id_ = inv.to_dict()
                            amount = int(id_.get("amount_paid") or id_.get("amount_due") or 0)
                            status = id_.get("status") or "—"
                            inv_rows.append({
                                "Date": datetime.fromtimestamp(int(id_.get("created", 0)), tz=timezone.utc).strftime("%b %d, %Y"),
                                "Amount": fmt_usd(cents_to_dollars(amount, id_.get("currency", "usd"))),
                                "Status": status.title(),
                                "Invoice #": id_.get("number") or id_.get("id", "—"),
                            })
                        except Exception:
                            pass
                    if inv_rows:
                        st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)
                else:
                    st.caption("No invoices found.")
            except Exception as e:
                st.warning(f"Could not load invoices: {e}")


# ── Landing page ──────────────────────────────────────────────────────────────

if not api_key:
    st.markdown("---")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("### Welcome")
        st.markdown(
            "Enter your **Stripe Secret Key** in the sidebar and click **Load Data** to view your subscription metrics.\n\n"
            "Your key is **never saved** — it lives only in this browser session.\n\n"
            "You'll get access to:\n"
            "- Active subscribers & MRR\n"
            "- New subscriber growth chart\n"
            "- Cancellations with reason\n"
            "- Unpaid invoices\n"
            "- Failed / declined charges"
        )
    st.stop()

if load_clicked:
    stripe.api_key = api_key
    with st.spinner("Fetching data from Stripe…"):
        try:
            active_subs = stripe_list_all(stripe.Subscription.list, status="active", expand=["data.customer"])
            canceled_subs = stripe_list_all(stripe.Subscription.list, status="canceled", created={"gte": since_ts}, expand=["data.customer"])
            open_invoices = stripe_list_all(stripe.Invoice.list, status="open")
            past_due_subs = stripe_list_all(stripe.Subscription.list, status="past_due", expand=["data.customer"])
            all_charges = stripe_list_all(stripe.Charge.list, created={"gte": since_ts})
            failed_charges = [c for c in all_charges if c.status == "failed"]

            st.session_state["stripe_data"] = {
                "active_subs": active_subs,
                "canceled_subs": canceled_subs,
                "open_invoices": open_invoices,
                "past_due_subs": past_due_subs,
                "failed_charges": failed_charges,
            }
            st.session_state["loaded_at"] = datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC")
        except stripe.error.AuthenticationError:
            st.error("Invalid API key. Please check the key in the sidebar.")
            st.stop()
        except Exception as e:
            st.error(f"Stripe error: {e}")
            st.stop()

if "stripe_data" not in st.session_state:
    st.info("Enter your Stripe Secret Key in the sidebar, then click **Load Data**.")
    st.stop()

active_subs    = st.session_state["stripe_data"]["active_subs"]
canceled_subs  = st.session_state["stripe_data"]["canceled_subs"]
open_invoices  = st.session_state["stripe_data"]["open_invoices"]
past_due_subs  = st.session_state["stripe_data"]["past_due_subs"]
failed_charges = st.session_state["stripe_data"]["failed_charges"]

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

unpaid_total = sum(cents_to_dollars(inv.amount_due, inv.currency) for inv in open_invoices)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Active Subscribers", f"{len(active_subs):,}")
k2.metric("Est. MRR", fmt_usd(mrr))
k3.metric(f"Cancellations ({days_back}d)", len(canceled_subs))
k4.metric("Unpaid Balance", fmt_usd(unpaid_total), delta=f"{len(open_invoices)} open invoices", delta_color="inverse")
k5.metric(f"Failed Charges ({days_back}d)", len(failed_charges), delta_color="inverse")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Active Subscriptions",
    "New Subscribers",
    "Cancellations",
    "Unpaid Balances",
    "Failed Charges",
])

# ── Tab 1: Active Subscriptions ───────────────────────────────────────────────
with tab1:
    st.subheader(f"Active Subscriptions ({len(active_subs):,})")
    if active_subs:
        now_ts = datetime.now(timezone.utc).timestamp()
        rows, customer_ids = [], []
        for s in active_subs:
            cust = s.customer
            email = cust.email if hasattr(cust, "email") else "—"
            name  = (cust.name if hasattr(cust, "name") and cust.name else None) or email or "—"
            try:
                item      = s.items.data[0]
                price_obj = item.price
                plan      = price_obj.nickname or price_obj.id
                amount    = cents_to_dollars(price_obj.unit_amount or 0, s.currency)
                interval  = price_obj.recurring.interval if price_obj.recurring else "—"
                period_end = getattr(item, "current_period_end", None) or getattr(s, "current_period_end", None)
            except (IndexError, AttributeError):
                plan, amount, interval, period_end = "—", 0, "—", None

            days_until = int((period_end - now_ts) / 86400) if period_end else None
            billing_str = (
                f"{days_until}d" if days_until is not None and days_until <= 7
                else datetime.fromtimestamp(period_end, tz=timezone.utc).strftime("%Y-%m-%d") if period_end
                else "—"
            )

            rows.append({
                "Customer": name,
                "Email": email,
                "Plan": plan,
                "Amount": fmt_usd(amount),
                "Billing": interval.title() if interval != "—" else "—",
                "Started": datetime.fromtimestamp(getattr(s, "start_date", None) or s.created, tz=timezone.utc).strftime("%Y-%m-%d"),
                "Next Billing": billing_str,
            })
            customer_ids.append(cust.id if hasattr(cust, "id") else None)

        df_full = pd.DataFrame(rows)
        df_filtered, original_indices = filter_df(df_full, "search_tab1")

        st.caption(f"Showing {len(df_filtered)} of {len(df_full)} subscribers · Click a row for details")
        selection = st.dataframe(df_filtered, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

        selected_rows = selection.selection.rows
        if selected_rows:
            orig_idx = original_indices[selected_rows[0]]
            cust_id = customer_ids[orig_idx]
            st.divider()
            if cust_id:
                show_customer_details(cust_id, rows[orig_idx]["Customer"], "details-tab1")
            else:
                st.warning("Customer ID not available for this row.")
    else:
        st.info("No active subscriptions found.")

# ── Tab 2: New Subscribers ────────────────────────────────────────────────────
with tab2:
    st.subheader(f"New Subscribers — Last {days_back} Days")

    def get_start_date(s):
        return getattr(s, "start_date", None) or getattr(s, "created", None)

    new_subs = [s for s in active_subs   if (get_start_date(s) or 0) >= since_ts]
    new_subs += [s for s in canceled_subs if (get_start_date(s) or 0) >= since_ts]

    if new_subs:
        dates = [datetime.fromtimestamp(get_start_date(s), tz=timezone.utc).date() for s in new_subs if get_start_date(s)]
        df_chart = pd.DataFrame({"date": dates})
        df_chart = df_chart.groupby("date").size().reset_index(name="New Subscribers")
        df_chart["date"] = pd.to_datetime(df_chart["date"])
        df_chart = df_chart.set_index("date").resample("D").sum().reset_index()
        st.line_chart(df_chart.set_index("date"), use_container_width=True)

        m1, m2 = st.columns(2)
        m1.metric("Total Sign-ups", len(new_subs))
        avg = len(new_subs) / max(days_back, 1)
        m2.metric("Daily Average", f"{avg:.1f}")

        st.divider()
        ns_rows, ns_cust_ids, ns_labels = [], [], []
        for s in new_subs:
            sd = s.to_dict()
            cust_obj  = sd.get("customer") or {}
            cust_id_v = cust_obj.get("id") if isinstance(cust_obj, dict) else (cust_obj if isinstance(cust_obj, str) else None)
            email     = cust_obj.get("email", "—") if isinstance(cust_obj, dict) else "—"
            name      = (cust_obj.get("name") if isinstance(cust_obj, dict) else None) or email or "—"
            items_list = sd.get("items", {}).get("data", [])
            plan = (items_list[0].get("price", {}).get("nickname") or items_list[0].get("price", {}).get("id", "—")) if items_list else "—"
            start_ts = get_start_date(s)
            ns_rows.append({"Customer": name, "Email": email, "Plan": plan,
                            "Signed Up": datetime.fromtimestamp(int(start_ts), tz=timezone.utc).strftime("%Y-%m-%d") if start_ts else "—"})
            ns_cust_ids.append(cust_id_v)
            ns_labels.append(name)

        df_ns_full = pd.DataFrame(ns_rows)
        df_ns_filtered, ns_orig_idx = filter_df(df_ns_full, "search_tab2")
        st.caption(f"Showing {len(df_ns_filtered)} of {len(df_ns_full)} · Click a row for details")
        ns_sel = st.dataframe(df_ns_filtered, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if ns_sel.selection.rows:
            orig_idx = ns_orig_idx[ns_sel.selection.rows[0]]
            cust_id = ns_cust_ids[orig_idx]
            st.divider()
            if cust_id:
                show_customer_details(cust_id, ns_labels[orig_idx], "details-tab2")
            else:
                st.warning("Customer ID not available for this row.")
    else:
        st.info("No new subscribers in this date range.")

# ── Tab 3: Cancellations ──────────────────────────────────────────────────────
with tab3:
    st.subheader(f"Cancellations — Last {days_back} Days ({len(canceled_subs):,})")
    if canceled_subs:
        reason_map = {
            "cancellation_requested":       "Manual",
            "payment_failed":               "Non-payment",
            "payment_disputed":             "Disputed",
            "canceled_by_retention_policy": "Retention Policy",
        }
        rows, cancel_cust_ids, cancel_labels = [], [], []
        for s in canceled_subs:
            sd        = s.to_dict()
            cust_obj  = sd.get("customer") or {}
            cust_id_v = cust_obj.get("id") if isinstance(cust_obj, dict) else (cust_obj if isinstance(cust_obj, str) else None)
            email     = cust_obj.get("email", "—") if isinstance(cust_obj, dict) else "—"
            name      = (cust_obj.get("name") if isinstance(cust_obj, dict) else None) or email or "—"
            items_list = sd.get("items", {}).get("data", [])
            plan = (items_list[0].get("price", {}).get("nickname") or items_list[0].get("price", {}).get("id", "—")) if items_list else "—"
            canceled_at  = sd.get("canceled_at") or sd.get("ended_at")
            raw_reason   = (sd.get("cancellation_details") or {}).get("reason")
            rows.append({
                "Customer":            name,
                "Email":               email,
                "Plan":                plan,
                "Cancellation Reason": reason_map.get(raw_reason, "—"),
                "Started":             datetime.fromtimestamp(int(sd.get("start_date") or sd.get("created", 0)), tz=timezone.utc).strftime("%Y-%m-%d"),
                "Cancelled":           datetime.fromtimestamp(int(canceled_at), tz=timezone.utc).strftime("%Y-%m-%d") if canceled_at else "—",
            })
            cancel_cust_ids.append(cust_id_v)
            cancel_labels.append(name)

        df_c_full = pd.DataFrame(rows)
        df_c_filtered, c_orig_idx = filter_df(df_c_full, "search_tab3")
        st.caption(f"Showing {len(df_c_filtered)} of {len(df_c_full)} · Click a row for details")
        c_sel = st.dataframe(df_c_filtered, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if c_sel.selection.rows:
            orig_idx = c_orig_idx[c_sel.selection.rows[0]]
            cust_id = cancel_cust_ids[orig_idx]
            st.divider()
            if cust_id:
                show_customer_details(cust_id, cancel_labels[orig_idx], "details-tab3")
            else:
                st.warning("Customer ID not available for this row.")
    else:
        st.success(f"No cancellations in the last {days_back} days.")

# ── Tab 4: Unpaid Balances ────────────────────────────────────────────────────
with tab4:
    st.subheader(f"Unpaid / Open Invoices ({len(open_invoices):,})")
    if open_invoices:
        rows, unpaid_cust_ids, unpaid_labels = [], [], []
        for inv in open_invoices:
            inv_d = inv.to_dict()
            rows.append({
                "Customer Email": inv_d.get("customer_email") or "—",
                "Amount Due":     fmt_usd(cents_to_dollars(inv_d.get("amount_due", 0), inv_d.get("currency", "usd"))),
                "Currency":       (inv_d.get("currency") or "usd").upper(),
                "Due Date":       datetime.fromtimestamp(inv_d["due_date"], tz=timezone.utc).strftime("%Y-%m-%d") if inv_d.get("due_date") else "—",
                "Created":        datetime.fromtimestamp(inv_d["created"], tz=timezone.utc).strftime("%Y-%m-%d"),
                "Invoice ID":     inv_d.get("id", "—"),
            })
            unpaid_cust_ids.append(inv_d.get("customer"))
            unpaid_labels.append(inv_d.get("customer_email") or inv_d.get("customer") or "—")

        st.metric("Total Unpaid", fmt_usd(unpaid_total))
        df_u_full = pd.DataFrame(rows)
        df_u_filtered, u_orig_idx = filter_df(df_u_full, "search_tab4")
        st.caption(f"Showing {len(df_u_filtered)} of {len(df_u_full)} · Click a row for details")
        u_sel = st.dataframe(df_u_filtered, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if u_sel.selection.rows:
            orig_idx = u_orig_idx[u_sel.selection.rows[0]]
            cust_id = unpaid_cust_ids[orig_idx]
            st.divider()
            if cust_id:
                show_customer_details(cust_id, unpaid_labels[orig_idx], "details-tab4")
            else:
                st.warning("Customer ID not available for this invoice.")
    else:
        st.success("No open invoices — all caught up!")

# ── Tab 5: Failed Charges ─────────────────────────────────────────────────────
with tab5:
    st.subheader(f"Failed / Declined Charges — Last {days_back} Days ({len(failed_charges):,})")
    if failed_charges:
        rows, fc_cust_ids, fc_labels = [], [], []
        for c in failed_charges:
            cd      = c.to_dict()
            billing = cd.get("billing_details") or {}
            email   = billing.get("email") or "—" if isinstance(billing, dict) else "—"
            rows.append({
                "Customer Email":  email,
                "Amount":          fmt_usd(cents_to_dollars(cd.get("amount", 0), cd.get("currency", "usd"))),
                "Failure Reason":  cd.get("failure_message") or "—",
                "Failure Code":    cd.get("failure_code") or "—",
                "Date":            datetime.fromtimestamp(int(cd.get("created", 0)), tz=timezone.utc).strftime("%Y-%m-%d %H:%M"),
            })
            fc_cust_ids.append(cd.get("customer"))
            fc_labels.append(email)

        df_f_full = pd.DataFrame(rows)
        df_f_filtered, f_orig_idx = filter_df(df_f_full, "search_tab5")
        st.caption(f"Showing {len(df_f_filtered)} of {len(df_f_full)} · Click a row for details")
        f_sel = st.dataframe(df_f_filtered, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        if f_sel.selection.rows:
            orig_idx = f_orig_idx[f_sel.selection.rows[0]]
            cust_id = fc_cust_ids[orig_idx]
            st.divider()
            if cust_id:
                show_customer_details(cust_id, fc_labels[orig_idx], "details-tab5")
            else:
                st.warning("No linked customer found for this charge.")
    else:
        st.success(f"No failed charges in the last {days_back} days.")
