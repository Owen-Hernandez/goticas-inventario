from flask import Flask, render_template, request, jsonify
from database import init_db, get_db

app = Flask(__name__)

# ──────────────────────────────────────────────
# INICIALIZACIÓN
# ──────────────────────────────────────────────
@app.before_request
def setup():
    pass  # La BD se inicializa al importar database

# ──────────────────────────────────────────────
# PÁGINAS
# ──────────────────────────────────────────────
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/productos')
def productos():
    return render_template('productos.html')

@app.route('/entradas')
def entradas():
    return render_template('entradas.html')

@app.route('/salidas')
def salidas():
    return render_template('salidas.html')

@app.route('/ajustes')
def ajustes():
    return render_template('ajustes.html')

@app.route('/costos')
def costos():
    return render_template('costos.html')

# ──────────────────────────────────────────────
# API - PRODUCTOS
# ──────────────────────────────────────────────
@app.route('/api/productos', methods=['GET'])
def api_get_productos():
    db = get_db()
    productos = db.execute(
        'SELECT * FROM productos ORDER BY nombre'
    ).fetchall()
    return jsonify([dict(p) for p in productos])

@app.route('/api/productos', methods=['POST'])
def api_crear_producto():
    data = request.get_json()
    referencia = data.get('referencia', '').strip()
    nombre = data.get('nombre', '').strip()
    costo = data.get('costo', 0)
    saldo_inicial = data.get('saldo_inicial', 0)

    if not referencia or not nombre:
        return jsonify({'error': 'Referencia y nombre son requeridos'}), 400

    db = get_db()
    # Verificar si ya existe
    existe = db.execute('SELECT id FROM productos WHERE referencia = ?', (referencia,)).fetchone()
    if existe:
        return jsonify({'error': 'La referencia ya existe'}), 400

    db.execute(
        'INSERT INTO productos (referencia, nombre, costo, stock) VALUES (?, ?, ?, ?)',
        (referencia, nombre, costo, saldo_inicial)
    )
    # Registrar como movimiento de saldo inicial si hay stock
    if saldo_inicial > 0:
        producto_id = db.execute('SELECT id FROM productos WHERE referencia = ?', (referencia,)).fetchone()['id']
        db.execute(
            '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
               VALUES (?, 'entrada', ?, ?, date('now'), 'Saldo inicial')''',
            (producto_id, saldo_inicial, costo)
        )
    db.commit()
    return jsonify({'mensaje': 'Producto creado exitosamente'})

@app.route('/api/productos/<int:pid>', methods=['PUT'])
def api_editar_producto(pid):
    data = request.get_json()
    nombre = data.get('nombre', '').strip()
    costo = data.get('costo', 0)

    if not nombre:
        return jsonify({'error': 'Nombre requerido'}), 400

    db = get_db()
    db.execute('UPDATE productos SET nombre = ?, costo = ? WHERE id = ?', (nombre, costo, pid))
    db.commit()
    return jsonify({'mensaje': 'Producto actualizado'})

# ──────────────────────────────────────────────
# API - ENTRADAS
# ──────────────────────────────────────────────
@app.route('/api/entradas', methods=['POST'])
def api_entrada():
    data = request.get_json()
    producto_id = data.get('producto_id')
    cantidad = data.get('cantidad', 0)
    costo_unitario = data.get('costo_unitario', 0)
    fecha = data.get('fecha')
    observacion = data.get('observacion', '')

    if not producto_id or cantidad <= 0:
        return jsonify({'error': 'Datos inválidos'}), 400

    db = get_db()
    db.execute(
        '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
           VALUES (?, 'entrada', ?, ?, ?, ?)''',
        (producto_id, cantidad, costo_unitario, fecha, observacion)
    )
    db.execute(
        'UPDATE productos SET stock = stock + ? WHERE id = ?',
        (cantidad, producto_id)
    )
    # Si el producto tenía costo $0 y ahora se registra con un costo, actualizarlo
    if costo_unitario > 0:
        producto = db.execute("SELECT costo FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if producto and producto["costo"] == 0:
            db.execute("UPDATE productos SET costo = ? WHERE id = ?", (costo_unitario, producto_id))
    db.commit()
    return jsonify({'mensaje': 'Entrada registrada exitosamente'})

@app.route('/api/entradas', methods=['GET'])
def api_get_entradas():
    db = get_db()
    movs = db.execute(
        '''SELECT m.*, p.nombre as producto_nombre, p.referencia
           FROM movimientos m
           JOIN productos p ON p.id = m.producto_id
           WHERE m.tipo = 'entrada'
           ORDER BY m.fecha DESC, m.id DESC'''
    ).fetchall()
    return jsonify([dict(m) for m in movs])

# ──────────────────────────────────────────────
# API - SALIDAS
# ──────────────────────────────────────────────
@app.route('/api/salidas', methods=['POST'])
def api_salida():
    data = request.get_json()
    producto_id = data.get('producto_id')
    cantidad = data.get('cantidad', 0)
    fecha = data.get('fecha')
    observacion = data.get('observacion', '')

    if not producto_id or cantidad <= 0:
        return jsonify({'error': 'Datos inválidos'}), 400

    db = get_db()
    producto = db.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404
    if producto['stock'] < cantidad:
        return jsonify({'error': f'Stock insuficiente. Disponible: {producto["stock"]} UND'}), 400

    db.execute(
        '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
           VALUES (?, 'salida', ?, ?, ?, ?)''',
        (producto_id, cantidad, producto['costo'], fecha, observacion)
    )
    db.execute(
        'UPDATE productos SET stock = stock - ? WHERE id = ?',
        (cantidad, producto_id)
    )
    db.commit()
    return jsonify({'mensaje': 'Salida registrada exitosamente'})

@app.route('/api/salidas', methods=['GET'])
def api_get_salidas():
    db = get_db()
    movs = db.execute(
        '''SELECT m.*, p.nombre as producto_nombre, p.referencia
           FROM movimientos m
           JOIN productos p ON p.id = m.producto_id
           WHERE m.tipo = 'salida'
           ORDER BY m.fecha DESC, m.id DESC'''
    ).fetchall()
    return jsonify([dict(m) for m in movs])

# ──────────────────────────────────────────────
# API - AJUSTES
# ──────────────────────────────────────────────
@app.route('/api/ajustes', methods=['POST'])
def api_ajuste():
    data = request.get_json()
    producto_id = data.get('producto_id')
    cantidad_nueva = data.get('cantidad_nueva', 0)
    fecha = data.get('fecha')
    observacion = data.get('observacion', '')

    if not producto_id or cantidad_nueva < 0:
        return jsonify({'error': 'Datos inválidos'}), 400

    db = get_db()
    producto = db.execute('SELECT * FROM productos WHERE id = ?', (producto_id,)).fetchone()
    if not producto:
        return jsonify({'error': 'Producto no encontrado'}), 404

    diferencia = cantidad_nueva - producto['stock']
    db.execute(
        '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
           VALUES (?, 'ajuste', ?, ?, ?, ?)''',
        (producto_id, diferencia, producto['costo'], fecha, observacion)
    )
    db.execute('UPDATE productos SET stock = ? WHERE id = ?', (cantidad_nueva, producto_id))
    db.commit()
    return jsonify({'mensaje': 'Ajuste registrado exitosamente'})

@app.route('/api/ajustes', methods=['GET'])
def api_get_ajustes():
    db = get_db()
    movs = db.execute(
        '''SELECT m.*, p.nombre as producto_nombre, p.referencia
           FROM movimientos m
           JOIN productos p ON p.id = m.producto_id
           WHERE m.tipo = 'ajuste'
           ORDER BY m.fecha DESC, m.id DESC'''
    ).fetchall()
    return jsonify([dict(m) for m in movs])

# ──────────────────────────────────────────────
# API - COSTOS
# ──────────────────────────────────────────────
@app.route('/api/costos', methods=['GET'])
def api_costos():
    db = get_db()
    productos = db.execute(
        '''SELECT p.*, 
                  p.stock * p.costo as valor_total
           FROM productos p
           ORDER BY p.nombre'''
    ).fetchall()
    return jsonify([dict(p) for p in productos])

@app.route('/api/costos/<int:pid>', methods=['PUT'])
def api_actualizar_costo(pid):
    data = request.get_json()
    nuevo_costo = data.get('costo', 0)
    if nuevo_costo < 0:
        return jsonify({'error': 'Costo inválido'}), 400
    db = get_db()
    db.execute('UPDATE productos SET costo = ? WHERE id = ?', (nuevo_costo, pid))
    db.commit()
    return jsonify({'mensaje': 'Costo actualizado'})

# ──────────────────────────────────────────────
# API - DASHBOARD
# ──────────────────────────────────────────────
@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    db = get_db()

    # Resumen general
    productos = db.execute('SELECT * FROM productos').fetchall()
    total_productos = len(productos)
    valor_total_inventario = sum(p['stock'] * p['costo'] for p in productos)
    total_unidades = sum(p['stock'] for p in productos)

    # Últimos movimientos
    ultimos_movimientos = db.execute(
        '''SELECT m.*, p.nombre as producto_nombre
           FROM movimientos m
           JOIN productos p ON p.id = m.producto_id
           ORDER BY m.fecha DESC, m.id DESC
           LIMIT 10'''
    ).fetchall()

    # Entradas y salidas del mes
    entradas_mes = db.execute(
        '''SELECT COALESCE(SUM(cantidad), 0) as total
           FROM movimientos
           WHERE tipo = 'entrada' AND strftime('%Y-%m', fecha) = strftime('%Y-%m', date('now'))'''
    ).fetchone()['total']

    salidas_mes = db.execute(
        '''SELECT COALESCE(SUM(cantidad), 0) as total
           FROM movimientos
           WHERE tipo = 'salida' AND strftime('%Y-%m', fecha) = strftime('%Y-%m', date('now'))'''
    ).fetchone()['total']

    # Productos con stock bajo (menos de 100)
    stock_bajo = db.execute(
        'SELECT * FROM productos WHERE stock < 100 ORDER BY stock ASC'
    ).fetchall()

    # Movimientos por mes (para gráfica)
    movimientos_mes = db.execute(
        '''SELECT strftime('%Y-%m', fecha) as mes,
                  SUM(CASE WHEN tipo='entrada' THEN cantidad ELSE 0 END) as entradas,
                  SUM(CASE WHEN tipo='salida' THEN cantidad ELSE 0 END) as salidas
           FROM movimientos
           GROUP BY mes
           ORDER BY mes DESC
           LIMIT 6'''
    ).fetchall()

    return jsonify({
        'total_productos': total_productos,
        'valor_total_inventario': valor_total_inventario,
        'total_unidades': total_unidades,
        'entradas_mes': entradas_mes,
        'salidas_mes': salidas_mes,
        'ultimos_movimientos': [dict(m) for m in ultimos_movimientos],
        'stock_bajo': [dict(p) for p in stock_bajo],
        'movimientos_mes': [dict(m) for m in movimientos_mes],
        'productos': [dict(p) for p in productos]
    })

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("✅ Sistema de Inventario - Goticas de Aceite")
    print("🌐 Abre tu navegador en: http://localhost:5000")
    app.run(debug=True, port=5000)
