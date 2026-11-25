"""Texte des statistiques sous l'aperçu, comme la page web (renderStats) : avertissements d'abord (texte du
caisson, QR code, sujet, IA…), puis les chiffres du résultat selon son type (gravure, trame / lignes, pochoir).
Sans Qt : `tr(texte, **valeurs)` traduit avec le catalogue de la page.

    warnings, parts = stats_message(stats, state, subject_box, box_messages, tr, version)
"""


def stats_message(s, state, subject_box, box_messages, tr, version=""):
    """(avertissements, chiffres) : deux listes de textes déjà traduits."""
    infos, extras = [], []
    box = s.get("box")
    if s.get("eng_px"):
        infos.append(tr("Engraving: {w} x {h} px at {dpi} DPI, {c} % burned, about {m} min", w=s["eng_px"][0],
                        h=s["eng_px"][1], dpi=round(s.get("eng_dpi") or 0), c=s.get("eng_cover"),
                        m=s.get("eng_minutes")))
    if box and box.get("style") == "fingers":
        infos.append(tr("Box with finger joints: {n} wall pieces, total depth {d} mm, cutting sheet {w} x {h} mm",
                        n=(box.get("counts") or {}).get("wall", 0), d=box.get("depth_total"),
                        w=round(box["sheet"][0]), h=round(box["sheet"][1])))
    elif box:
        infos.append(tr("Box: {f} frames, stack {d} mm, cutting sheet {w} x {h} mm", f=box.get("frames"),
                        d=box.get("depth_total"), w=round(box["sheet"][0]), h=round(box["sheet"][1])))
    notes = (box or {}).get("notes") or []
    if box and "depth_low" in notes and box.get("style") != "fingers":
        extras.append(tr("Depth under 15 mm: the LEDs may show as bright spots through the front."))
    for key in ("sharp_corners", "radius_small", "ring_thin", "key_no_room", "foot_shape"):
        if key in notes and key in box_messages:
            extras.append(tr(box_messages[key]))
    if "wall_thin" in notes:
        extras.append(tr("The wall is too narrow for the screws: widen it or reduce the screw diameter."))
    if s.get("text_ignored"):
        extras.append(tr("The text is ignored: it works on circle, oval, rectangle and rounded rectangle shapes."))
    if s.get("text_scaled"):
        extras.append(tr("The text was too long for the ring: it was reduced."))
    if s.get("ml_pin_skip"):
        extras.append(tr("The border is too narrow for alignment holes: widen it (diameter + 2 mm) or untick them."))
    if s.get("qr_error"):
        extras.append(tr("QR code error: {e}", e=s["qr_error"]))
    elif s.get("qr_scan") == "fail":
        extras.append(tr("WARNING: the generated QR code could not be read back. Enlarge it, raise the error "
                         "correction or shorten the text."))
    elif s.get("qr_scan") == "inverted":
        extras.append(tr("The QR code reads inverted (light on dark): most phones read it anyway."))
    if s.get("qr_small"):
        action = tr("cut") if state.get("qr_mode") == "cut" else tr("engrave")
        extras.append(tr("WARNING: modules are only {m} mm: too small to {a} reliably. Enlarge the code or shorten "
                         "the text.", m=s.get("qr_module_mm"), a=action))
    if s.get("qr_clamped"):
        extras.append(tr("The code was reduced to fit the plate."))
    if s.get("ai_missing"):
        extras.append(tr("AI detection unavailable ({e}): classic method used. Install it with: {cmd}",
                         e=str(s["ai_missing"])[:80], cmd=s.get("ai_install") or "pip install onnxruntime"))
    if s.get("subject_failed"):
        extras.append(tr("WARNING: subject detection failed, mask ignored. Draw a Subject box or untick the "
                         "isolation."))
    elif s.get("subject_pct") is not None and s["subject_pct"] < 35 and not subject_box:
        extras.append(tr("The mask covers only {p} % of the frame: check the Original view (dark areas = rejected) "
                         "or draw a Subject box.", p=s["subject_pct"]))
    size = tr("Size: {w} x {h} mm", w=f"{s.get('w_mm', 0):.1f}", h=f"{s.get('h_mm', 0):.1f}")
    length = tr("Cut length: {mm} mm", mm=round(s.get("length_mm") or 0))
    subject = [tr("Subject: {p} %", p=s["subject_pct"])] if s.get("subject_pct") is not None else []
    if s.get("eng_px"):
        parts = [length, size, tr("{s} s", s=s.get("seconds"))]
    elif "holes" in s:
        parts = [tr("Holes: {n}", n=s["holes"])]
        if s.get("dots_across"):
            parts.append(tr("Grid: {n} dots across", n=s["dots_across"]))
        if s.get("lines_across"):
            parts.append(tr("Lines: {n} across", n=s["lines_across"]))
        parts += subject + [length, size]
    else:
        parts = [tr("Contours: {n}", n=s.get("contours")), length, tr("Bridges: {n}", n=s.get("linked")),
                 tr("Removed pieces: {n}", n=s.get("dropped")), size,
                 tr("Threshold: {t}", t=round(s.get("threshold") or 0))] + subject
        if s.get("px"):
            parts.append(tr("Computed at {px} px", px=max(s["px"][0], s["px"][1])))
        parts.append(tr("{s} s", s=s.get("seconds")))
    parts = infos + parts + ([f"v{version}"] if version else [])
    return extras, parts
