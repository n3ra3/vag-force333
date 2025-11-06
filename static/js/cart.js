// static/js/cart.js
// Ensure DOM is ready before querying elements — defensive to avoid
// cases where the script is executed before the template is fully parsed.
(function(){
  function init(){
    const btn = document.getElementById('checkoutBtn')
    const result = document.getElementById('result')
    if (!btn){
      console.warn('cart.js: checkoutBtn not found in DOM')
      return
    }
    console.debug('cart.js: init — checkout handler attached')

  function makeIdempotencyKey(){
    if (window.crypto && crypto.randomUUID){
      return crypto.randomUUID()
    }
    return 'idem-' + Math.random().toString(36).slice(2)
  }

  function loadCart(){
    try{ return JSON.parse(localStorage.getItem('cart')||'[]') }catch(e){ return [] }
  }

  function saveCart(cart){ localStorage.setItem('cart', JSON.stringify(cart)) }

  function renderCart(){
    const itemsEl = document.getElementById('items')
    const summaryEl = document.getElementById('summary')
    const emptyHint = document.getElementById('emptyHint')
    const cart = loadCart()
    if (!cart || cart.length===0){
      emptyHint.style.display = 'block'
      itemsEl.innerHTML = ''
      summaryEl.innerHTML = ''
      return
    }
    emptyHint.style.display = 'none'
    itemsEl.innerHTML = ''
    let total = 0
    cart.forEach((it, idx)=>{
      const row = document.createElement('div')
      row.style.display = 'flex'
      row.style.justifyContent = 'space-between'
      row.style.alignItems = 'center'
      row.style.padding = '8px 0'
      row.innerHTML = `<div><strong>${it.name||('product '+it.product_id)}</strong><div style="font-size:0.9em;color:#666">id: ${it.product_id}</div></div>`
      const controls = document.createElement('div')
      const qty = document.createElement('input')
      qty.type = 'number'
      qty.value = it.quantity
      qty.min = 1
      qty.style.width = '60px'
      qty.addEventListener('change', e=>{
        const v = Math.max(1, parseInt(e.target.value||1))
        cart[idx].quantity = v
        saveCart(cart)
        renderCart()
      })
      const rem = document.createElement('button')
      rem.textContent = 'Удалить'
      rem.style.marginLeft = '8px'
      rem.addEventListener('click', ()=>{
        cart.splice(idx,1)
        saveCart(cart)
        renderCart()
        if (window.vfUI && typeof window.vfUI.updateCartCount === 'function') window.vfUI.updateCartCount()
      })
      controls.appendChild(qty)
      controls.appendChild(rem)
      row.appendChild(controls)
      itemsEl.appendChild(row)
      total += (parseFloat(it.price)||0)*it.quantity
    })
    summaryEl.innerHTML = `<div>Всего: ${total.toFixed(2)} USD</div>`
  }

    btn.addEventListener('click', async ()=>{
        console.debug('cart.js: checkout button clicked')
        // store cart in sessionStorage and redirect to checkout page where user fills address/payment
    const cart = loadCart()
    if (!cart || cart.length===0){ result.textContent = 'Корзина пуста'; return }
    const amount = cart.reduce((s,c)=> s + ((parseFloat(c.price)||0) * c.quantity), 0)
    const checkout = { items: cart, amount: Number(amount.toFixed(2)), currency: 'USD' }
    try{
      sessionStorage.setItem('vf_checkout', JSON.stringify(checkout))
      console.debug('cart.js: vf_checkout saved to sessionStorage', checkout)
      // use assign to better reflect navigation intent and make it easier to debug
      location.assign('/checkout')
    }catch(e){
      result.textContent = 'Ошибка подготовки оформления: ' + String(e)
    }
    })

    // initial render
    renderCart()

    // ensure header counter initialized
    if (window.vfUI && typeof window.vfUI.updateCartCount === 'function') window.vfUI.updateCartCount()
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init)
  else init()

})()
