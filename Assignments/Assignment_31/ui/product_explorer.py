import streamlit as st
import requests
import numpy as np

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FakeStore Explorer",
    page_icon="🛍️",
    layout="centered",
)

# ── Simple CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .main-title {
    font-size: 2rem;
    font-weight: bold;
    color: #2c3e50;
    text-align: center;
    margin-bottom: 5px;
  }
  .sub-title {
    text-align: center;
    color: #7f8c8d;
    font-size: 0.9rem;
    margin-bottom: 25px;
  }
  .stat-box {
    background-color: #f0f4f8;
    border-left: 4px solid #3498db;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 8px;
  }
  .stat-label { font-size: 0.75rem; color: #7f8c8d; text-transform: uppercase; }
  .stat-value { font-size: 1.3rem; font-weight: bold; color: #2c3e50; }
  .product-box {
    background-color: #f9f9f9;
    border: 1px solid #dde3ea;
    border-radius: 10px;
    padding: 20px 24px;
    margin-top: 20px;
  }
  .product-name  { font-size: 1.2rem; font-weight: bold; color: #2c3e50; margin-bottom: 6px; }
  .product-price { font-size: 1.6rem; font-weight: bold; color: #27ae60; }
  .product-cat   { display: inline-block; background: #eaf0fb; color: #2980b9;
                   border-radius: 4px; padding: 2px 10px; font-size: 0.78rem;
                   text-transform: uppercase; margin-bottom: 10px; }
  .product-desc  { font-size: 0.87rem; color: #555; line-height: 1.6;
                   border-top: 1px solid #dde3ea; padding-top: 10px; margin-top: 10px; }
  .stars         { color: #f39c12; font-size: 1rem; }
  .rating-text   { font-size: 0.82rem; color: #7f8c8d; margin-left: 6px; }
  .divider       { border: none; border-top: 1px solid #dde3ea; margin: 20px 0; }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_all_products():
    response = requests.get("https://fakestoreapi.com/products")
    response.raise_for_status()
    return response.json()

def render_stars(rating: float) -> str:
    filled = int(round(rating))
    return "★" * filled + "☆" * (5 - filled)

def numpy_stats(products: list) -> dict:
    prices  = np.array([p["price"]          for p in products], dtype=np.float64)
    ratings = np.array([p["rating"]["rate"] for p in products], dtype=np.float64)
    return {
        "total"        : len(prices),
        "avg_price"    : float(np.mean(prices)),
        "min_price"    : float(np.min(prices)),
        "max_price"    : float(np.max(prices)),
        "avg_rating"   : float(np.mean(ratings)),
        "median_price" : float(np.median(prices)),
    }


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🛍️ FakeStore Product Explorer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Search products by ID or Title · Stats powered by NumPy</div>', unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching products..."):
    try:
        all_products = fetch_all_products()
    except Exception as e:
        st.error(f"Could not reach API: {e}")
        st.stop()

stats = numpy_stats(all_products)

# ── Stats row ─────────────────────────────────────────────────────────────────
st.markdown("#### 📊 Store Summary")
total, avg_price, median_price, rating = st.columns(4)

with total:
    st.markdown(f"""<div class="stat-box">
        <div class="stat-label">Total Products</div>
        <div class="stat-value">{stats['total']}</div>
    </div>""", unsafe_allow_html=True)

with avg_price:
    st.markdown(f"""<div class="stat-box">
        <div class="stat-label">Avg Price</div>
        <div class="stat-value">${stats['avg_price']:.2f}</div>
    </div>""", unsafe_allow_html=True)

with median_price:
    st.markdown(f"""<div class="stat-box">
        <div class="stat-label">Median Price</div>
        <div class="stat-value">${stats['median_price']:.2f}</div>
    </div>""", unsafe_allow_html=True)

with rating:
    st.markdown(f"""<div class="stat-box">
        <div class="stat-label">Avg Rating</div>
        <div class="stat-value">{stats['avg_rating']:.2f} ★</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ── Search tabs ───────────────────────────────────────────────────────────────
tab_productId, tab_title = st.tabs(["🔢 Search by ID", "🔤 Search by Title"])

# ── Tab 1: Search by ID ───────────────────────────────────────────────────────
with tab_productId:
    product_id = st.number_input(
        "Enter Product ID",
        min_value=1,
        max_value=len(all_products),
        value=1,
        step=1,
        help=f"Valid range: 1 to {len(all_products)}"
    )

    # numpy lookup
    ids = np.array([p["id"] for p in all_products])
    idx = np.where(ids == int(product_id))[0]

    if idx.size > 0:
        p = all_products[int(idx[0])]

        col_img, col_info = st.columns([1, 2])

        with col_img:
            try:
                st.image(p["image"], width=200)
            except Exception:
                st.write("*(image unavailable)*")

        with col_info:
            st.markdown(f"""
            <div class="product-box">
              <div class="product-cat">{p['category']}</div>
              <div class="product-name">{p['title']}</div>
              <div class="product-price">${p['price']}</div>
              <div>
                <span class="stars">{render_stars(p['rating']['rate'])}</span>
                <span class="rating-text">{p['rating']['rate']} / 5 &nbsp;({p['rating']['count']} reviews)</span>
              </div>
              <div class="product-desc">{p['description']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("No product found for that ID.")

# ── Tab 2: Search by Title ────────────────────────────────────────────────────
with tab_title:
    query = st.text_input("Enter keyword to search titles", placeholder="e.g. jacket, gold, backpack ...")

    if query.strip():
        titles  = np.array([p["title"].lower() for p in all_products])
        matches = np.where(np.char.find(titles, query.strip().lower()) >= 0)[0]

        if matches.size == 0:
            st.warning("No products matched your search.")
        else:
            st.success(f"✅ {matches.size} product(s) found")

            for i in matches:
                p = all_products[int(i)]
                with st.expander(f"#{p['id']}  —  {p['title'][:65]}{'…' if len(p['title']) > 65 else ''}"):
                    img_col, info_col = st.columns([1, 2])

                    with img_col:
                        try:
                            st.image(p["image"], width=150)
                        except Exception:
                            pass

                    with info_col:
                        st.markdown(f"""
                        <div class="product-box">
                          <div class="product-cat">{p['category']}</div>
                          <div class="product-name">{p['title']}</div>
                          <div class="product-price">${p['price']}</div>
                          <div>
                            <span class="stars">{render_stars(p['rating']['rate'])}</span>
                            <span class="rating-text">{p['rating']['rate']} / 5 ({p['rating']['count']} reviews)</span>
                          </div>
                          <div class="product-desc">{p['description']}</div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("👆 Type a keyword above to search products by title.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('<hr class="divider">', unsafe_allow_html=True)
st.caption("Data: fakestoreapi.com  ·  Stats computed with NumPy")