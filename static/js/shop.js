// static/js/shop.js
(async function(){
  const out = document.getElementById('products')

  function productsUrl(){
    const host = window.location.hostname
    return (host && host !== 'localhost') ? '/api/products' : 'http://localhost:8002/api/products'
  }

  async function fetchProducts(){
    try{
      const r = await fetch(productsUrl())
      if (!r.ok) throw new Error('failed')
      return await r.json()
    }catch(e){
      console.error(e)
      return []
    }
  }

  function loadCart(){
    try{ return JSON.parse(localStorage.getItem('cart')||'[]') }catch(e){ return [] }
  }

  function saveCart(cart){ localStorage.setItem('cart', JSON.stringify(cart)) }

  function addToCart(product){
    const cart = loadCart()
    const idx = cart.findIndex(c=>c.product_id===product.id)
    if (idx>=0) cart[idx].quantity += 1
    else cart.push({ product_id: product.id, quantity: 1, name: product.name, price: product.price })
    saveCart(cart)
    // update header counter and show a small toast
    if (window.vfUI && typeof window.vfUI.updateCartCount === 'function') window.vfUI.updateCartCount()
    if (window.vfUI && typeof window.vfUI.toast === 'function') window.vfUI.toast('Добавлено в корзину')
  }

  const products = await fetchProducts()
  if (!products || products.length===0){ out.textContent = 'Товары недоступны' ; return }

  out.innerHTML = ''
  const grid = document.createElement('div')
  grid.className = 'products-grid'

  products.forEach(p=>{
    const card = document.createElement('div')
    card.className = 'card product-card'
    const imgSrc = p.image || '/static/img/product-placeholder-1.svg'
    card.innerHTML = `
      <img class="product-thumb" src="${imgSrc}" alt="${p.name} thumbnail" />
      <h3 class="product-title">${p.name}</h3>
      <div class="product-desc">${(p.description||'').slice(0,160)}</div>
      <div class="product-price">Цена: ${Number(p.price).toFixed(2)} USD</div>
    `
    const btn = document.createElement('button')
    btn.className = 'btn primary'
    btn.textContent = 'Добавить в корзину'
    btn.addEventListener('click', ()=> addToCart(p))
    card.appendChild(btn)
    grid.appendChild(card)
  })

  out.appendChild(grid)
  // subtle fade-in
  grid.style.opacity = 0
  grid.style.transition = 'opacity .28s ease'
  requestAnimationFrame(()=> grid.style.opacity = 1)
  // after initial render update header count
  if (window.vfUI && typeof window.vfUI.updateCartCount === 'function') window.vfUI.updateCartCount()
})()
