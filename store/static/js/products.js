// products.js — fixed version with Cloudinary image support
console.log("[products.js] loaded (Cloudinary fixed)");

/* ---------- Helpers ---------- */
function dlog(...args){ console.log("[PDBG]", ...args); }
function escapeHtml(s){ if(!s && s !== 0) return ''; return String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;'); }
function renderStars(r){
  const full = Math.floor(r||0);
  let s = '';
  for(let i=0;i<5;i++) s += i<full ? '★' : '☆';
  return s;
}

/* Simple toast using Bootstrap toast classes */
function toast(msg = '', timeout = 1200, isError = false){
  let container = document.querySelector('.toast-container');
  if(!container){
    container = document.createElement('div');
    container.className = 'toast-container';
    container.style.position = 'fixed';
    container.style.top = '1rem';
    container.style.right = '1rem';
    container.style.zIndex = 1200;
    document.body.appendChild(container);
  }

  const t = document.createElement('div');
  t.className = 'toast align-items-center shadow-sm';
  t.setAttribute('role','alert');
  t.setAttribute('aria-live','assertive');
  t.setAttribute('aria-atomic','true');
  t.style.minWidth = '170px';
  t.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${escapeHtml(msg)}</div>
      <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>`;
  if(isError) t.querySelector('.toast-body').style.color = '#b02a37';
  container.appendChild(t);
  const bs = bootstrap.Toast.getOrCreateInstance(t);
  bs.show();
  setTimeout(()=> { bs.hide(); setTimeout(()=> t.remove(), 300); }, timeout);
}

/* ---------- Cart API helpers ---------- */
async function fetchCartAPI(){
  try{
    const res = await fetch('/api/cart', { credentials: 'same-origin' });
    if(!res.ok) { dlog('/api/cart not ok', res.status); return null; }
    return await res.json();
  } catch(e){
    dlog('fetchCartAPI error', e);
    return null;
  }
}

function renderCartInDrawer(cartJson){
  const container = document.getElementById('cartItems');
  const totalEl = document.getElementById('cartTotal');
  if(!container || !totalEl) return;

  if(!cartJson || !cartJson.items || cartJson.items.length === 0){
    container.innerHTML = '<p class="text-muted">Giỏ hàng trống.</p>';
    totalEl.innerText = '$0.00';
    const cc = document.getElementById('cartCount'); if(cc) cc.innerText = '0';
    return;
  }

  container.innerHTML = '';
  cartJson.items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'd-flex align-items-center mb-3';
    const imgsrc = item.image && item.image.startsWith('http') ? item.image : '/static/images/' + (item.image || 'a1.jpg');
    row.innerHTML = `
      <img src="${imgsrc}" style="width:64px;height:64px;object-fit:cover;border-radius:6px;margin-right:10px;">
      <div style="flex:1">
        <div class="small fw-semibold">${escapeHtml(item.title)}</div>
        <div class="small text-muted">$${item.price.toFixed(2)} x ${item.qty} = <strong>$${item.subtotal.toFixed(2)}</strong></div>
      </div>
      <div>
        <button class="btn btn-sm btn-outline-danger drawer-remove" data-id="${item.id}">Xóa</button>
      </div>`;
    container.appendChild(row);
  });

  totalEl.innerText = '$' + (cartJson.total || 0).toFixed(2);
  const cc = document.getElementById('cartCount'); if(cc) cc.innerText = String(cartJson.count || 0);

  container.querySelectorAll('.drawer-remove').forEach(b => {
    b.addEventListener('click', (e) => {
      const pid = e.currentTarget.dataset.id;
      const fd = new URLSearchParams();
      fd.append('product_id', pid);
      fd.append('qty', 0);
      fetch('/cart/update', { method: 'POST', body: fd, credentials: 'same-origin' })
        .then(r=> r.ok ? r.json() : Promise.reject('update failed'))
        .then(()=> { refreshCart(false); toast('Đã xóa', 900); })
        .catch(err => { dlog('drawer remove error', err); toast('Lỗi khi xóa', 1200, true); });
    });
  });
}

async function refreshCart(openDrawer = false){
  const cart = await fetchCartAPI();
  renderCartInDrawer(cart);
  if(openDrawer){
    const el = document.getElementById('cartDrawer');
    if(el){
      const oc = new bootstrap.Offcanvas(el);
      oc.show();
    }
  }
}

/* ---------- Products / Grid ---------- */
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('productGrid');
  const searchInput = document.getElementById('searchInput');
  const categoryBtns = document.getElementsByClassName('category-btn');
  const priceMin = document.getElementById('priceMin');
  const priceMax = document.getElementById('priceMax');
  const applyPriceBtn = document.getElementById('applyPriceBtn');
  const sortSelect = document.getElementById('sortSelect');
  const resultInfo = document.getElementById('resultInfo');
  const pagination = document.getElementById('pagination');
  const cartCount = document.getElementById('cartCount');
  const openCartBtn = document.getElementById('openCartBtn');

  if(!grid){ dlog('productGrid not found'); return; }

  let state = { q:'', category:'', price_min:null, price_max:null, page:1, per_page:9, sort:'' };
  const debounce = (fn, wait=300) => { let t; return (...a)=>{ clearTimeout(t); t = setTimeout(()=>fn(...a), wait); }; };

  async function fetchProducts(){
    try{
      const params = new URLSearchParams();
      if(state.q) params.append('q', state.q);
      if(state.category) params.append('category', state.category);
      if(state.price_min != null) params.append('price_min', state.price_min);
      if(state.price_max != null) params.append('price_max', state.price_max);
      params.append('page', state.page);
      params.append('per_page', state.per_page);

      const res = await fetch('/api/products?' + params.toString(), { credentials: 'same-origin' });
      if(!res.ok) throw new Error('API ' + res.status);
      const data = await res.json();
      renderProducts(data.products || []);
      renderPagination(data.page, data.pages);
      if(resultInfo) resultInfo.textContent = `Hiển thị ${data.products.length} / ${data.total || data.products.length}`;
    } catch(err){
      dlog('fetchProducts error', err);
      grid.innerHTML = '<div class="col-12"><p class="text-muted">Không tải được sản phẩm.</p></div>';
    }
  }

  function renderProducts(products){
    grid.innerHTML = '';
    if(!products.length){
      grid.innerHTML = '<div class="col-12"><p class="text-muted">Không tìm thấy sản phẩm.</p></div>';
      return;
    }
    products.forEach(p => {
      let imgsrc = p.image || '/static/images/a1.jpg';
      // ✅ Fix: support Cloudinary or local images
      if (!imgsrc.startsWith('http') && !imgsrc.startsWith('/static/')) {
        imgsrc = '/static/images/' + imgsrc;
      }

      const col = document.createElement('div');
      col.className = 'col-md-4';
      col.innerHTML = `
        <div class="card product-card h-100">
          <img data-src="${imgsrc}" loading="lazy" class="card-img-top lazy-img" alt="${escapeHtml(p.title)}">
          <div class="card-body d-flex flex-column">
            <div class="mb-2">
              <div class="product-title">${escapeHtml(p.title)}</div>
              <div class="product-meta">${escapeHtml(p.category || '')}</div>
            </div>
            <p class="small text-muted mb-3">${escapeHtml((p.description||'').slice(0,100))}${p.description && p.description.length>100 ? '...' : ''}</p>
            <div class="mt-auto d-flex justify-content-between align-items-center">
              <div>
                <div class="price">$${(p.price||0).toFixed(2)}</div>
                <div class="small text-muted">${renderStars(p.rating)} <span class="ms-1">(${p.rating})</span></div>
              </div>
              <div>
                <button class="btn btn-sm btn-outline-secondary me-2 view-detail" data-id="${p.id}">View</button>
                <button class="btn btn-sm btn-dark add-to-cart" data-id="${p.id}">Add to Cart</button>
              </div>
            </div>
          </div>
        </div>`;
      grid.appendChild(col);
    });

    // lazy-load images
    const lazyImgs = document.querySelectorAll('.lazy-img');
    if('IntersectionObserver' in window){
      const obs = new IntersectionObserver((entries, ob)=>{
        entries.forEach(entry=>{
          if(entry.isIntersecting){
            const img = entry.target;
            const src = img.dataset.src;
            if(src){ img.src = src; img.removeAttribute('data-src'); }
            ob.unobserve(img);
          }
        });
      }, { rootMargin: '200px' });
      lazyImgs.forEach(i => obs.observe(i));
    } else {
      lazyImgs.forEach(i => { i.src = i.dataset.src; i.removeAttribute('data-src'); });
    }

    attachCardHandlers();
  }

  function renderPagination(page, pages){
    if(!pagination) return;
    pagination.innerHTML = '';
    if(!pages || pages <= 1) return;
    for(let i=1;i<=pages;i++){
      const li = document.createElement('li');
      li.className = 'page-item' + (i===page ? ' active' : '');
      li.innerHTML = `<a class="page-link" href="#" data-page="${i}">${i}</a>`;
      pagination.appendChild(li);
    }
    pagination.querySelectorAll('.page-link').forEach(link=>{
      link.addEventListener('click', e=>{
        e.preventDefault();
        state.page = parseInt(e.target.dataset.page);
        fetchProducts();
      });
    });
  }

  function attachCardHandlers(){
    document.querySelectorAll('.add-to-cart').forEach(btn=>{
      btn.onclick = async () => {
        const id = btn.dataset.id;
        const fd = new URLSearchParams();
        fd.append('product_id', id);
        fd.append('qty', 1);
        try{
          const res = await fetch('/cart/add', { method:'POST', body: fd, credentials: 'same-origin' });
          if(!res.ok) throw new Error('add failed');
          const j = await res.json();
          if(j.success){ toast('Đã thêm vào giỏ'); updateCartCount(); refreshCart(false); }
          else toast('Lỗi khi thêm', 1400, true);
        } catch(e){ dlog('add-to-cart error', e); toast('Lỗi mạng', 1400, true); }
      };
    });

    document.querySelectorAll('.view-detail').forEach(b=>{
      b.onclick = () => {
        const id = b.dataset.id;
        fetch(`/api/products/${id}`, { credentials: 'same-origin' })
          .then(r=>r.json())
          .then(showModal)
          .catch(e=>{ dlog('showModal err', e); });
      };
    });
  }

  function showModal(p){
    const body = document.getElementById('productModalBody');
    if(!body) return;
    const imgsrc = p.image && p.image.startsWith('http')
      ? p.image
      : '/static/images/' + (p.image || 'a1.jpg');

    body.innerHTML = `
      <div class="row">
        <div class="col-md-6"><img src="${imgsrc}" class="img-fluid" alt="${escapeHtml(p.title)}" /></div>
        <div class="col-md-6">
          <h4>${escapeHtml(p.title)}</h4>
          <p class="text-muted">${escapeHtml(p.category || '')}</p>
          <h3>$${(p.price||0).toFixed(2)}</h3>
          <p>${escapeHtml(p.description || '')}</p>
          <div class="mb-2">${renderStars(p.rating)} <span class="ms-2">(${p.rating})</span></div>
          <button class="btn btn-dark" id="modalAddCart" data-id="${p.id}">Add to Cart</button>
        </div>
      </div>`;
    const modal = new bootstrap.Modal(document.getElementById('productModal'));
    modal.show();
    document.getElementById('modalAddCart').onclick = async (e) => {
      const id = e.target.dataset.id;
      const fd = new URLSearchParams();
      fd.append('product_id', id);
      fd.append('qty', 1);
      try{
        const res = await fetch('/api/cart/add', { method:'POST', body: fd, credentials: 'same-origin' });
        if(!res.ok) throw new Error('add failed');
        const j = await res.json();
        if(j.success){ toast('Đã thêm vào giỏ'); updateCartCount(); setTimeout(()=> modal.hide(), 600); }
        else toast('Lỗi', 1000, true);
      } catch(err){ toast('Lỗi mạng', 1200, true); }
    };
  }

  async function updateCartCount(){
    try{
      const res = await fetch('/api/cart', { credentials: 'same-origin' });
      if(!res.ok) return;
      const j = await res.json();
      if(cartCount) cartCount.innerText = String(j.count || 0);
    } catch(e){ dlog('updateCartCount err', e); }
  }

  if(openCartBtn){
    openCartBtn.addEventListener('click', ()=> { refreshCart(true); });
  }

  Array.from(categoryBtns).forEach(b=>{
    b.addEventListener('click', ()=> {
      Array.from(categoryBtns).forEach(x=>x.classList.remove('active'));
      b.classList.add('active');
      state.category = b.dataset.cat || '';
      state.page = 1;
      fetchProducts();
    });
  });

  applyPriceBtn && applyPriceBtn.addEventListener('click', ()=> {
    state.price_min = priceMin.value ? parseFloat(priceMin.value) : null;
    state.price_max = priceMax.value ? parseFloat(priceMax.value) : null;
    state.page = 1;
    fetchProducts();
  });

  sortSelect && sortSelect.addEventListener('change', ()=> {
    state.sort = sortSelect.value;
    fetchProducts();
  });

  if(searchInput){
    searchInput.addEventListener('input', debounce((e)=>{
      state.q = e.target.value.trim();
      state.page = 1;
      fetchProducts();
    }, 350));
  }

  fetchProducts();
  updateCartCount();
});
