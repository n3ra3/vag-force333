import httpx, uuid, time

def run():
    pid = 2
    print('reset ->', httpx.post('http://localhost:8008/api/inventory/reset', json={'items': {str(pid):2}}).text)
    print('before ->', httpx.get(f'http://localhost:8008/api/inventory/items/{pid}').text)
    payload={'user_id':99999,'items':[{'product_id':pid,'quantity':1}],'amount':1.0,'currency':'USD','payment_method':'fail','idempotency_key':str(uuid.uuid4())}
    r = httpx.post('http://localhost:8004/api/orders/checkout', json=payload)
    print('checkout ->', r.status_code, r.text)
    print('after ->', httpx.get(f'http://localhost:8008/api/inventory/items/{pid}').text)

if __name__=='__main__':
    run()
