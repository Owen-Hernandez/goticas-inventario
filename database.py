import sqlite3
import os

DB_PATH = 'inventario.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    
    # ── Crear tablas ──
    db.executescript('''
        CREATE TABLE IF NOT EXISTS productos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            referencia TEXT UNIQUE NOT NULL,
            nombre    TEXT NOT NULL,
            costo     REAL NOT NULL DEFAULT 0,
            stock     REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id    INTEGER NOT NULL,
            tipo           TEXT NOT NULL CHECK(tipo IN ('entrada','salida','ajuste')),
            cantidad       REAL NOT NULL,
            costo_unitario REAL NOT NULL DEFAULT 0,
            fecha          TEXT NOT NULL,
            observacion    TEXT DEFAULT '',
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        );
    ''')

    # ── Verificar si ya hay datos (para no duplicar) ──
    ya_tiene_datos = db.execute('SELECT COUNT(*) FROM productos').fetchone()[0]
    if ya_tiene_datos > 0:
        db.close()
        return

    # ── Inventario inicial ──
    productos_iniciales = [
        ('ACE_PAL_NAL_001', 'Aceite de Palma Balde 5L',          13500, 500),
        ('MAR_SUA_ESP_001', 'Caja Margarina Suave Especial 15 KG', 87500, 1200),
        ('SEB_NAL_001',     'Sebo refinado Balde 3 KG',            27500, 800),
        ('EST_HDR_IMP_001', 'Estearina Hidrogenada bolsa 1 KG',     8500, 3000),
    ]

    for ref, nombre, costo, stock in productos_iniciales:
        db.execute(
            'INSERT INTO productos (referencia, nombre, costo, stock) VALUES (?, ?, ?, ?)',
            (ref, nombre, costo, stock)
        )
        pid = db.execute('SELECT id FROM productos WHERE referencia = ?', (ref,)).fetchone()[0]
        # Registrar saldo inicial como entrada
        db.execute(
            '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
               VALUES (?, 'entrada', ?, ?, '2024-12-31', 'Saldo inicial')''',
            (pid, stock, costo)
        )

    db.commit()

    # ── Movimientos precargados de la prueba ──
    def get_pid(ref):
        return db.execute('SELECT id FROM productos WHERE referencia = ?', (ref,)).fetchone()[0]

    movimientos_prueba = [
        # (referencia, tipo, cantidad, fecha, observacion)
        ('ACE_PAL_NAL_001', 'entrada', 50,  '2025-01-01', 'Ingreso registrado'),
        ('SEB_NAL_001',     'salida',  20,  '2025-01-08', 'Salida registrada'),
        ('MAR_SUA_ESP_001', 'entrada', 150, '2025-02-13', 'Ingreso registrado'),
    ]

    for ref, tipo, cantidad, fecha, obs in movimientos_prueba:
        pid = get_pid(ref)
        producto = db.execute('SELECT costo, stock FROM productos WHERE id = ?', (pid,)).fetchone()
        costo = producto['costo']

        db.execute(
            '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (pid, tipo, cantidad, costo, fecha, obs)
        )
        if tipo == 'entrada':
            db.execute('UPDATE productos SET stock = stock + ? WHERE id = ?', (cantidad, pid))
        elif tipo == 'salida':
            db.execute('UPDATE productos SET stock = stock - ? WHERE id = ?', (cantidad, pid))

    # ── Producto nuevo del 08/03/2025 ──
    db.execute(
        'INSERT INTO productos (referencia, nombre, costo, stock) VALUES (?, ?, ?, ?)',
        ('OLE_PAL_BID_001', 'Oleína de Palma Bidón 20 L', 0, 0)
    )
    pid_oleina = db.execute("SELECT id FROM productos WHERE referencia = 'OLE_PAL_BID_001'").fetchone()[0]
    db.execute(
        '''INSERT INTO movimientos (producto_id, tipo, cantidad, costo_unitario, fecha, observacion)
           VALUES (?, 'entrada', 0, 0, '2025-03-08', 'Producto nuevo creado en sistema')''',
        (pid_oleina,)
    )

    db.commit()
    db.close()
    print("✅ Base de datos inicializada con datos de prueba.")
