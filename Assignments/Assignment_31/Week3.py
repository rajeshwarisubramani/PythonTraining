import streamlit as st
import requests
import numpy as np

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FakeStore Product Explorer",
    page_icon="🛍️",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

  /* Background */
  .stApp { background: #0d0f14; color: #e8e6e0; }

  /* Header strip */
  .header-strip {
    background: linear-gradient(135deg, #1a1d26 0%, #12151e 100%);
    border: 1px solid #2a2d3a;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 32px;
    display: flex;
    align-items: center;
    gap: 18px;
  }
  .header-strip h1 { font-size: 2.1rem; font-weight: 800; color: #f0ece4; margin: 0; letter-spacing: -1px; }
  .header-strip p  { color: #7a7e8e; margin: 0; font-size: 0.9rem; font-family: 'DM Mono', monospace; }

  /* Search card */
  .search-card {
    background: #13161f;
    border: 1px solid #22263a;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 28px;
  }

  /* Metric pill */
  .metric-pill {
    background: #1a1d2a;
    border: 1px solid #2a2f45;
    border-radius: 10px;
    padding: 14px 20px;
    text-align: center;
  }
  .metric-pill .label { font-size: 0.72rem; color: #5a6080; text-transform: uppercase; letter-spacing: 1.5px; font-family: 'DM Mono', monospace; }
  .metric-pill .value { font-size: 1.55rem; font-weight: 800; color: #c8f080; margin-top: 4px; }

  /* Product card */
  .product-card {
    background: #13161f;
    border: 1px solid #22263a;
    border-radius: 16px;
    padding: 30px;
    margin-top: 24px;
    position: relative;
    overflow: hidden;
  }
  .product-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #c8f080, #60c0f0, #c060f0);
  }
  .product-title  { font-size: 1.4rem; font-weight: 800; color: #f0ece4; line-height: 1.3; margin-bottom: 12px; }
  .product-cat    { display: inline-block; background: #1e2438; border: 1px solid #3a3f58; border-radius: 6px;
                    padding: 3px 12px; font-size: 0.75rem; font-family: 'DM Mono', monospace;
                    color: #8090c0; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 16px; }
  .product-price  { font-size: 2.2rem; font-weight: 800; color: #c8f080; letter-spacing: -1px; }
  .product-desc   { color: #8a8e9e; font-size: 0.88rem; line-height: 1.65; margin-top: 14px; border-top: 1px solid #1e2232; padding-top: 14px; }
  .rating-row     { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
  .stars          { color: #f0c040; font-size: 1rem; }
  .rating-num     { font-family: 'DM Mono', monospace; font-size: 0.85rem; color: #7080a0; }

  /* Results table */
  .result-row {
    background: #13161f;
    border: 1px solid #1e2232;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 10px;
    cursor: pointer;
    transition: border-color 0.2s;
  }
  .result-row:hover { border-color: #c8f080; }
  .result-id   { font-family: 'DM Mono', monospace; font-size: 0.75rem; color: #5a6080; }
  .result-name { font-weight: 600; color: #d0ccc4; font-size: 0.9rem; }

  /* Inputs override */
  .stTextInput > div > div > input,
  .stNumberInput > div > div > input {
    background: #0e111a !important;
    border: 1px solid #2a2f45 !important;
    color: #e8e6e0 !important;
    border-radius: 10px !important;
    font-family: 'DM Mono', monospace !important;
  }
  div[data-testid="stTabs"] button { font-family: 'Syne', sans-serif !important; font-weight: 600 !important; }

  /* Divider */
  hr { border-color: #1e2232; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #0b0d12; border-right: 1px solid #1a1d2a; }
</style>
""", unsafe_allow_html=True)


# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_all_products():
    url = "https://fakestoreapi.com/products"
    response = requests.request("GET", url, headers={}, data={})
    response.raise_for_status()
    return response.json()


def render_stars(rating: float) -> str:
    filled  = int(round(rating))
    return "★" * filled + "☆" * (5 - filled)


def numpy_stats(products: list) -> dict:
    """Use numpy to derive price statistics across all products."""
    prices  = np.array([p["price"] for p in products], dtype=np.float64)
    ratings = np.array([p["rating"]["rate"] for p in products], dtype=np.float64)
    counts  = np.array([p["rating"]["count"] for p in products], dtype=np.int64)
    return {
        "total"       : len(prices),
        "avg_price"   : float(np.mean(prices)),
        "min_price"   : float(np.min(prices)),
        "max_price"   : float(np.max(prices)),
        "std_price"   : float(np.std(prices)),
        "avg_rating"  : float(np.mean(ratings)),
        "max_count"   : int(np.max(counts)),
        "median_price": float(np.median(prices)),
    }


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-strip">
  <div>
    <h1>🛍️ FakeStore Explorer</h1>
    <p>fakestoreapi.com &nbsp;·&nbsp; search by ID or title &nbsp;·&nbsp; powered by numpy</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching products…"):
    try:
        all_products = fetch_all_products()
    except Exception as e:
        st.error(f"Could not reach FakeStore API: {e}")
        st.stop()

stats = numpy_stats(all_products)

# ── Metric pills ──────────────────────────────────────────────────────────────
cols = st.columns(5)
metrics = [
    ("TOTAL PRODUCTS",  stats["total"],                    ""),
    ("AVG PRICE",       f"${stats['avg_price']:.2f}",      ""),
    ("MEDIAN PRICE",    f"${stats['median_price']:.2f}",   ""),
    ("PRICE STD DEV",   f"${stats['std_price']:.2f}",      ""),
    ("AVG RATING",      f"{stats['avg_rating']:.2f} ★",    ""),
]
for col, (label, value, _) in zip(cols, metrics):
    with col:
        st.markdown(f"""
        <div class="metric-pill">
          <div class="label">{label}</div>
          <div class="value">{value}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Search tabs ───────────────────────────────────────────────────────────────
tab_id, tab_title = st.tabs(["🔢  Search by ID", "🔤  Search by Title"])

# ─ Tab 1 : by ID ──────────────────────────────────────────────────────────────
with tab_id:
    st.markdown('<div class="search-card">', unsafe_allow_html=True)
    product_id = st.number_input(
        "Enter Product ID",
        min_value=1, max_value=len(all_products),
        value=1, step=1,
        help=f"Valid IDs: 1 – {len(all_products)}"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Use numpy to find by id
    ids    = np.array([p["id"] for p in all_products])
    idx    = np.where(ids == int(product_id))[0]

    if idx.size > 0:
        product = all_products[int(idx[0])]
        _show   = True
    else:
        st.warning("No product found for that ID.")
        _show = False

    if _show:
        c1, c2 = st.columns([1, 2], gap="large")
        with c1:
            try:
                st.image(product["image"], width=230)
            except Exception:
                st.markdown("*(image unavailable)*")
        with c2:
            st.markdown(f"""
            <div class="product-card">
              <div class="product-cat">{product['category']}</div>
              <div class="product-title">{product['title']}</div>
              <div class="product-price">${product['price']}</div>
              <div class="rating-row">
                <span class="stars">{render_stars(product['rating']['rate'])}</span>
                <span class="rating-num">{product['rating']['rate']} / 5 &nbsp;({product['rating']['count']} reviews)</span>
              </div>
              <div class="product-desc">{product['description']}</div>
            </div>
            """, unsafe_allow_html=True)

# ─ Tab 2 : by Title ───────────────────────────────────────────────────────────
with tab_title:
    st.markdown('<div class="search-card">', unsafe_allow_html=True)
    query = st.text_input("Enter product title (partial match OK)", placeholder="e.g. jacket, ring, laptop …")
    st.markdown('</div>', unsafe_allow_html=True)

    if query.strip():
        titles  = np.array([p["title"].lower() for p in all_products])
        matches = np.where(np.char.find(titles, query.strip().lower()) >= 0)[0]

        if matches.size == 0:
            st.warning("No products matched your query.")
        else:
            st.markdown(f"**{matches.size} result(s) found:**")

            for i in matches:
                p = all_products[int(i)]
                with st.expander(f"#{p['id']} — {p['title'][:70]}{'…' if len(p['title'])>70 else ''}"):
                    ec1, ec2 = st.columns([1, 3], gap="medium")
                    with ec1:
                        try:
                            st.image(p["image"], width=140)
                        except Exception:
                            pass
                    with ec2:
                        st.markdown(f"""
                        <div class="product-card">
                          <div class="product-cat">{p['category']}</div>
                          <div class="product-title" style="font-size:1.1rem">{p['title']}</div>
                          <div class="product-price" style="font-size:1.6rem">${p['price']}</div>
                          <div class="rating-row">
                            <span class="stars">{render_stars(p['rating']['rate'])}</span>
                            <span class="rating-num">{p['rating']['rate']} / 5 ({p['rating']['count']} reviews)</span>
                          </div>
                          <div class="product-desc">{p['description']}</div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("Type a title keyword above to search across all products.")

# ── Sidebar : category filter ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📂 Browse by Category")
    categories = sorted(set(p["category"] for p in all_products))
    selected_cat = st.radio("Category", ["All"] + categories)

    if selected_cat != "All":
        cat_products = [p for p in all_products if p["category"] == selected_cat]
        # numpy: price range for this category
        cat_prices = np.array([p["price"] for p in cat_products])
        st.markdown(f"""
        **{len(cat_products)} products**  
        💰 `${cat_prices.min():.2f}` – `${cat_prices.max():.2f}`  
        avg `${cat_prices.mean():.2f}`
        """)
        for p in cat_products:
            st.markdown(f"""
            <div class="result-row">
              <div class="result-id">ID {p['id']}</div>
              <div class="result-name">{p['title'][:50]}{'…' if len(p['title'])>50 else ''}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Data: [fakestoreapi.com](https://fakestoreapi.com)")
    st.caption("Stats computed with **numpy**")