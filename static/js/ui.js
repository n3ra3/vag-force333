// small UI helpers used by pages
(function(){
  function getCart(){
    try{ return JSON.parse(localStorage.getItem('cart')||'[]') }catch(e){ return [] }
  }

  function updateCartCount(){
    const el = document.getElementById('cartCount')
    if (!el) return
    const cart = getCart()
    const count = cart.reduce((s,it)=> s + (parseInt(it.quantity||0)||0), 0)
    el.textContent = count
    // bump animation
    try{
      el.classList.remove('bump')
      // force reflow to restart animation
      void el.offsetWidth
      el.classList.add('bump')
    }catch(e){/* ignore */}
  }

  function toast(msg, timeout=1800){
    let t = document.getElementById('__vf_toast')
    if (!t){ t = document.createElement('div'); t.id='__vf_toast'; t.className='toast'; document.body.appendChild(t) }
    t.textContent = msg
    t.classList.add('show')
    clearTimeout(t._h)
    t._h = setTimeout(()=> t.classList.remove('show'), timeout)
  }

  function getToken(){ return localStorage.getItem('vf_token') }
  function clearToken(){ localStorage.removeItem('vf_token') }

  function updateAuthUI(){
    const el = document.getElementById('authLink')
    if (!el) return
    const token = getToken()
    // remove any previous handler
    el.onclick = null
    if (token){
      el.textContent = 'Выйти'
      el.href = '#'
      el.addEventListener('click', function onLogout(e){
        e.preventDefault()
        clearToken()
        // update UI immediately
        try{ updateCartCount() }catch(e){}
        toast('Вы вышли из аккаунта')
        // reload to reflect logged-out state
        setTimeout(()=> location.href = '/', 250)
      })
    } else {
      el.textContent = 'Войти'
      el.href = '/login'
    }
  }

  // expose helpers globally
  window.vfUI = { updateCartCount, toast, updateAuthUI, getToken, clearToken }
  // auto-run on load
  function _onReady(){ updateCartCount(); updateAuthUI() }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', _onReady)
  else _onReady()

})();
