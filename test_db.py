from backend.database import (
    init_db, upsert_product, add_price, get_last_price, list_products,
)

init_db()

# 1. Insert a product
pid = upsert_product("https://example.com/product/1", "Test Product")
print(f"1. Inserted product id={pid}")

# 2. Insert the same URL again — should return the SAME id
pid2 = upsert_product("https://example.com/product/1", "Test Product v2")
print(f"2. Second upsert id={pid2} (should equal {pid})")
assert pid == pid2, "upsert returned a different id!"

# 3. Add two price records
add_price(pid, 19.99, "$", True)
add_price(pid, 17.99, "$", True)
print("3. Added two price records")

# 4. Last price should be 17.99 (the newer one)
last = get_last_price(pid)
print(f"4. Last price: {last['price']} (expected 17.99)")
assert last["price"] == 17.99

# 5. List products
products = list_products()
print(f"5. Products in DB: {len(products)}")
for p in products:
    print(f"   - {p['id']}: {p['name']} ({p['url']})")

print("\n✅ All checks passed")