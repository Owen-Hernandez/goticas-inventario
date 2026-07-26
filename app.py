from flask import Flask, render_template, request, jsonify
from database import init_db, get_db
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
init_db()

# ── PÁGINAS ──────────────────────────────────────────────────────────────────
@app.route('/')
def dashboard(): return render_template('dashboard.html', active='dashboard')

@app.route('/entradas')
def entradas(): return render_template('entradas.html', active='entradas')

@app.route('/salidas')
def salidas(): return render_template('salidas.html', active='salidas')

@app.route('/ajustes')
def ajustes(): return render_template('ajustes.html', active='ajustes')

@app.route('/productos')
def productos(): return render_template('productos.html', active='productos')

@app.route('/costos')
def costos(): return render_template('costos.html', active='costos')

@app.route('/ia')
def ia(): return render_template('ia.html', active='ia')

# ── API PRODUCTOS ─────────────────────────────────────────────────────────────
@app.route('/api/productos', methods=['GET'])
def api_get_productos():
    db = get_db()
    rows = db.execute('SELECT * FROM productos ORDER BY nombre').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/productos', methods=['POST'])
def api_crear_producto():
    d = request.get_json()
    ref = d.get('referencia','').strip()
    nombre = d.get('nombre','').strip()
    costo = float(d.get('costo', 0))
    saldo = float(d.get('saldo_inicial', 0))
    if not ref or not nombre:
        return jsonify({'error': 'Referencia y nombre son requeridos'}), 400
    db = get_db()
    if db.execute('SELECT id FROM productos WHERE referencia=?',(ref,)).fetchone():
        return jsonify({'error': 'La referencia ya existe'}), 400
    db.execute('INSERT INTO productos (referencia,nombre,costo,stock) VALUES (?,?,?,?)',(ref,nombre,costo,saldo))
    db.commit()
    if saldo > 0:
        pid = db.execute('SELECT id FROM productos WHERE referencia=?',(ref,)).fetchone()[0]
        db.execute("INSERT INTO movimientos (producto_id,tipo,cantidad,costo_unitario,fecha,observacion) VALUES (?,'entrada',?,?,date('now'),'Saldo inicial')",(pid,saldo,costo))
        db.commit()
    return jsonify({'mensaje': 'Producto creado exitosamente'})

@app.route('/api/productos/<int:pid>', methods=['PUT'])
def api_editar_producto(pid):
    d = request.get_json()
    nombre = d.get('nombre','').strip()
    costo = float(d.get('costo', 0))
    if not nombre: return jsonify({'error': 'Nombre requerido'}), 400
    db = get_db()
    db.execute("UPDATE productos SET nombre=?,costo=?,updated_at=datetime('now') WHERE id=?",(nombre,costo,pid))
    db.commit()
    return jsonify({'mensaje': 'Producto actualizado'})

# ── API ENTRADAS ──────────────────────────────────────────────────────────────
@app.route('/api/entradas', methods=['POST'])
def api_entrada():
    d = request.get_json()
    pid = d.get('producto_id')
    cantidad = float(d.get('cantidad', 0))
    costo = float(d.get('costo_unitario', 0))
    fecha = d.get('fecha')
    obs = d.get('observacion','')
    if not pid or cantidad <= 0: return jsonify({'error': 'Datos inválidos'}), 400
    db = get_db()
    db.execute("INSERT INTO movimientos (producto_id,tipo,cantidad,costo_unitario,fecha,observacion) VALUES (?,'entrada',?,?,?,?)",(pid,cantidad,costo,fecha,obs))
    db.execute('UPDATE productos SET stock=stock+?,updated_at=datetime("now") WHERE id=?',(cantidad,pid))
    if costo > 0:
        p = db.execute('SELECT costo FROM productos WHERE id=?',(pid,)).fetchone()
        if p and p['costo'] == 0:
            db.execute('UPDATE productos SET costo=? WHERE id=?',(costo,pid))
    db.commit()
    return jsonify({'mensaje': 'Entrada registrada exitosamente'})

@app.route('/api/entradas', methods=['GET'])
def api_get_entradas():
    db = get_db()
    rows = db.execute("SELECT m.*,p.nombre as producto_nombre,p.referencia FROM movimientos m JOIN productos p ON p.id=m.producto_id WHERE m.tipo='entrada' ORDER BY m.fecha DESC,m.id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

# ── API SALIDAS ───────────────────────────────────────────────────────────────
@app.route('/api/salidas', methods=['POST'])
def api_salida():
    d = request.get_json()
    pid = d.get('producto_id')
    cantidad = float(d.get('cantidad', 0))
    fecha = d.get('fecha')
    obs = d.get('observacion','')
    if not pid or cantidad <= 0: return jsonify({'error': 'Datos inválidos'}), 400
    db = get_db()
    p = db.execute('SELECT * FROM productos WHERE id=?',(pid,)).fetchone()
    if not p: return jsonify({'error': 'Producto no encontrado'}), 404
    if p['stock'] < cantidad: return jsonify({'error': f'Stock insuficiente. Disponible: {p["stock"]} UND'}), 400
    db.execute("INSERT INTO movimientos (producto_id,tipo,cantidad,costo_unitario,fecha,observacion) VALUES (?,'salida',?,?,?,?)",(pid,cantidad,p['costo'],fecha,obs))
    db.execute('UPDATE productos SET stock=stock-?,updated_at=datetime("now") WHERE id=?',(cantidad,pid))
    db.commit()
    return jsonify({'mensaje': 'Salida registrada exitosamente'})

@app.route('/api/salidas', methods=['GET'])
def api_get_salidas():
    db = get_db()
    rows = db.execute("SELECT m.*,p.nombre as producto_nombre,p.referencia FROM movimientos m JOIN productos p ON p.id=m.producto_id WHERE m.tipo='salida' ORDER BY m.fecha DESC,m.id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

# ── API AJUSTES ───────────────────────────────────────────────────────────────
@app.route('/api/ajustes', methods=['POST'])
def api_ajuste():
    d = request.get_json()
    pid = d.get('producto_id')
    nueva = float(d.get('cantidad_nueva', 0))
    fecha = d.get('fecha')
    obs = d.get('observacion','')
    if not pid or nueva < 0: return jsonify({'error': 'Datos inválidos'}), 400
    db = get_db()
    p = db.execute('SELECT * FROM productos WHERE id=?',(pid,)).fetchone()
    if not p: return jsonify({'error': 'Producto no encontrado'}), 404
    dif = nueva - p['stock']
    db.execute("INSERT INTO movimientos (producto_id,tipo,cantidad,costo_unitario,fecha,observacion) VALUES (?,'ajuste',?,?,?,?)",(pid,dif,p['costo'],fecha,obs))
    db.execute('UPDATE productos SET stock=?,updated_at=datetime("now") WHERE id=?',(nueva,pid))
    db.commit()
    return jsonify({'mensaje': 'Ajuste registrado exitosamente'})

@app.route('/api/ajustes', methods=['GET'])
def api_get_ajustes():
    db = get_db()
    rows = db.execute("SELECT m.*,p.nombre as producto_nombre,p.referencia FROM movimientos m JOIN productos p ON p.id=m.producto_id WHERE m.tipo='ajuste' ORDER BY m.fecha DESC,m.id DESC").fetchall()
    return jsonify([dict(r) for r in rows])

# ── API COSTOS ────────────────────────────────────────────────────────────────
@app.route('/api/costos', methods=['GET'])
def api_costos():
    db = get_db()
    rows = db.execute('SELECT *,stock*costo as valor_total FROM productos ORDER BY nombre').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/costos/<int:pid>', methods=['PUT'])
def api_actualizar_costo(pid):
    d = request.get_json()
    costo = float(d.get('costo', 0))
    if costo < 0: return jsonify({'error': 'Costo inválido'}), 400
    db = get_db()
    db.execute('UPDATE productos SET costo=?,updated_at=datetime("now") WHERE id=?',(costo,pid))
    db.commit()
    return jsonify({'mensaje': 'Costo actualizado'})

# ── API DASHBOARD ─────────────────────────────────────────────────────────────
@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    db = get_db()
    productos = db.execute('SELECT * FROM productos').fetchall()
    valor_total = sum(p['stock']*p['costo'] for p in productos)
    total_unidades = sum(p['stock'] for p in productos)

    ultimos = db.execute("SELECT m.*,p.nombre as producto_nombre FROM movimientos m JOIN productos p ON p.id=m.producto_id ORDER BY m.fecha DESC,m.id DESC LIMIT 10").fetchall()

    entradas_mes = db.execute("SELECT COALESCE(SUM(cantidad),0) as t FROM movimientos WHERE tipo='entrada' AND strftime('%Y-%m',fecha)=strftime('%Y-%m',date('now'))").fetchone()['t']
    salidas_mes  = db.execute("SELECT COALESCE(SUM(cantidad),0) as t FROM movimientos WHERE tipo='salida'  AND strftime('%Y-%m',fecha)=strftime('%Y-%m',date('now'))").fetchone()['t']

    stock_bajo = db.execute('SELECT * FROM productos WHERE stock < 100 ORDER BY stock').fetchall()

    mov_por_mes = db.execute("""
        SELECT strftime('%Y-%m',fecha) as mes,
               SUM(CASE WHEN tipo='entrada' THEN cantidad ELSE 0 END) as entradas,
               SUM(CASE WHEN tipo='salida'  THEN cantidad ELSE 0 END) as salidas
        FROM movimientos GROUP BY mes ORDER BY mes DESC LIMIT 8
    """).fetchall()

    return jsonify({
        'total_productos': len(productos),
        'valor_total_inventario': valor_total,
        'total_unidades': total_unidades,
        'entradas_mes': entradas_mes,
        'salidas_mes': salidas_mes,
        'ultimos_movimientos': [dict(m) for m in ultimos],
        'stock_bajo': [dict(p) for p in stock_bajo],
        'mov_por_mes': [dict(m) for m in mov_por_mes],
        'productos': [dict(p) for p in productos],
    })

# ── API IA ────────────────────────────────────────────────────────────────────
@app.route('/api/ia/contexto', methods=['GET'])
def api_ia_contexto():
    db = get_db()
    productos = db.execute('SELECT *,stock*costo as valor_total FROM productos').fetchall()
    movimientos = db.execute("""
        SELECT m.tipo, m.cantidad, m.fecha, m.observacion, p.nombre as producto_nombre
        FROM movimientos m JOIN productos p ON p.id=m.producto_id
        ORDER BY m.fecha DESC LIMIT 50
    """).fetchall()
    valor_total = sum(p['stock']*p['costo'] for p in productos)
    return jsonify({
        'productos': [dict(p) for p in productos],
        'movimientos_recientes': [dict(m) for m in movimientos],
        'valor_total_inventario': valor_total,
        'total_productos': len(productos),
        'total_unidades': sum(p['stock'] for p in productos),
    })


# ── API IA PROXY (Groq) ──────────────────────────────────────────────────────
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

@app.route("/api/ia/chat", methods=["POST"])
def api_ia_chat():
    import urllib.request, json as _json
    d = request.get_json()
    sistema = d.get("system", "")
    mensajes = d.get("messages", [])
    max_tokens = d.get("max_tokens", 1000)

    payload = _json.dumps({
        "model": "llama-3.3-70b-versatile",
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "messages": [
            {"role": "system", "content": sistema},
        ] + mensajes
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + GROQ_API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = _json.loads(resp.read())
            text = data["choices"][0]["message"]["content"]
            return jsonify({"text": text})
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print("GROQ ERROR:", body)
        try:
            err = _json.loads(body)
            msg = err.get("error", {}).get("message", body)
        except:
            msg = body
        return jsonify({"error": msg}), 500
    except Exception as e:
        print("EXCEPTION:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("✅ NEXUS — Sistema Inteligente de Inventario")
    print("🌐 http://localhost:5000")
    app.run(debug=True, port=5000)
