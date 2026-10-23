from twin.audit import auditar


def _d(pid, ts, decision, label):
    return {"pieza_id": pid, "timestamp": ts, "decision": decision, "label": label}


def test_cuenta_aciertos_rechazos_falsos_y_defectos_no_detectados():
    verdad = [
        {"pieza_id": 0, "verdad": "ok", "timestamp": 100.0},
        {"pieza_id": 1, "verdad": "mancha", "timestamp": 101.0},
        {"pieza_id": 2, "verdad": "corte", "timestamp": 102.0},
        {"pieza_id": 3, "verdad": "ok", "timestamp": 103.0},
    ]
    decisiones = [
        _d(0, 100.1, "OK", "ok"),
        _d(1, 101.1, "RECHAZO", "mancha"),
        _d(2, 102.1, "OK", "ok"),  # defect missed
        _d(3, 103.1, "RECHAZO", "pegado"),  # false rejection
    ]
    r = auditar(verdad, decisiones)
    assert r["piezas"] == 4 and r["sin_decision"] == 0
    assert r["defectos_no_detectados"] == 1
    assert r["rechazos_falsos"] == 1
    assert r["tipo_correcto"] == 1  # mancha
    assert r["no_detectados"] == [{"pieza_id": 2, "verdad": "corte"}]


def test_empareja_con_la_decision_de_la_misma_corrida():
    verdad = [{"pieza_id": 0, "verdad": "mancha", "timestamp": 500.0}]
    decisiones = [
        _d(0, 100.1, "OK", "ok"),  # previous run, same id
        _d(0, 500.2, "RECHAZO", "mancha"),
    ]
    r = auditar(verdad, decisiones)
    assert r["defectos_no_detectados"] == 0
    assert r["tipo_correcto"] == 1


def test_una_pieza_sin_decision_se_reporta_aparte():
    verdad = [{"pieza_id": 7, "verdad": "ok", "timestamp": 10.0}]
    r = auditar(verdad, [])
    assert r["sin_decision"] == 1 and r["piezas"] == 1
    assert r["rechazos_falsos"] == 0
