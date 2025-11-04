def bag_svg_with_distribution(blood_type: str, total: int, dist: dict) -> str:
    """
    ถุงเลือดสไตล์การ์ตูนสมจริง (flat + gloss) พร้อมกราฟในถุง
    กราฟ/ชื่อชนิดเลือดจะแสดงเมื่อ hover เท่านั้น
    """
    status, label, pct = compute_bag(total)
    fill = bag_color(status)

    # ----- พื้นที่ด้านในของถุง (สำหรับน้ำ/กราฟ) -----
    INNER_LEFT, INNER_RIGHT = 36.0, 114.0
    INNER_TOP, INNER_BOTTOM = 30.0, 186.0
    INNER_W = INNER_RIGHT - INNER_LEFT          # 78
    INNER_H = INNER_BOTTOM - INNER_TOP          # 156

    # ระดับผิวน้ำ (อิง 0..20) -> 0..INNER_H
    water_h = INNER_H * max(0, min(20, min(total, BAG_MAX))) / BAG_MAX
    water_y = INNER_BOTTOM - water_h

    # ----- กราฟย่อยในถุง -----
    ORDER = ["PRC", "Platelets", "Plasma", "Cryo"]
    COLORS = {
        "PRC": "#1f77b4",       # ฟ้า
        "Platelets": "#ff7f0e", # ส้ม
        "Plasma": "#2ca02c",    # เขียว
        "Cryo": "#d62728",      # แดง
    }
    vals = [max(0, int(dist.get(k, 0))) for k in ORDER]
    bar_heights = [(min(v, BAG_MAX) / BAG_MAX) * water_h for v in vals]

    gap = 6.0
    bar_w = (INNER_W - gap * 3) / 4.0
    bars, labels = [], []
    for i, (k, h) in enumerate(zip(ORDER, bar_heights)):
        x = INNER_LEFT + i * (bar_w + gap)
        y = water_y + (water_h - h)  # ดันจากก้นน้ำขึ้นมา
        color = COLORS[k]
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
            f'rx="4" fill="{color}"></rect>'
        )
        # ป้ายชื่อชนิดเลือด บนแท่ง (อ่านง่ายเวลา hover)
        ty = max(y + 12, water_y + 12)
        labels.append(
            f'<text x="{x + bar_w/2:.1f}" y="{ty:.1f}" text-anchor="middle" '
            f'font-size="9" font-weight="600" fill="white">{k}</text>'
        )

    gid = f"g_{blood_type}"

    # ----- SVG + CSS (isolated ใน component) -----
    return f"""
<div>
  <style>
    .bag-wrap{{display:flex;flex-direction:column;align-items:center;gap:8px;
               font-family:ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial}}
    .bag{{transition:transform .18s ease, filter .18s ease}}
    .bag:hover{{transform:translateY(-2px); filter:drop-shadow(0 8px 24px rgba(0,0,0,.12));}}
    .dist-group{{opacity:0; transition:opacity .2s ease;}}
    .bag:hover .dist-group{{opacity:1;}}
    .bag-caption{{text-align:center; line-height:1.2}}
    .bag-caption .total{{font-weight:700}}
    .bag-caption .tip{{font-size:10px;color:#6b7280}}
  </style>

  <div class="bag-wrap">
    <svg class="bag" width="170" height="220" viewBox="0 0 150 200" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="shadow_{gid}" x="-20%" y="-20%" width="160%" height="160%">
          <feDropShadow dx="0" dy="6" stdDeviation="7" flood-opacity="0.18"/>
        </filter>
        <clipPath id="clip_{gid}">
          <!-- โครงด้านในของถุง (พื้นที่น้ำ/กราฟ) -->
          <path d="M35,25 C35,13 45,7 57,7 L93,7 C105,7 115,13 115,25 L115,160
                   C115,176 104,186 88,188 L62,188 C46,186 35,176 35,160 Z"/>
        </clipPath>
        <linearGradient id="liquid_{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stop-color="{fill}" stop-opacity=".96"/>
          <stop offset="100%" stop-color="{fill}" stop-opacity=".86"/>
        </linearGradient>
        <linearGradient id="gloss_{gid}" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="rgba(255,255,255,.65)"/>
          <stop offset="100%" stop-color="rgba(255,255,255,0)"/>
        </linearGradient>
      </defs>

      <!-- หูถุง/คอท่อ -->
      <rect x="70" y="0" width="10" height="10" rx="5" fill="#9ca3af"/>
      <rect x="68" y="10" width="14" height="6" rx="3" fill="#cbd5e1"/>
      <path d="M75,16 C75,22 75,22 75,22" stroke="#cbd5e1" stroke-width="4" stroke-linecap="round"/>

      <!-- สเกลด้านซ้ายให้สมจริง -->
      <g opacity=".35">
        <line x1="28" x2="28" y1="28" y2="184" stroke="#9ca3af" stroke-width="1"/>
        {"".join([f'<line x1="26" x2="30" y1="{{y}}" y2="{{y}}" stroke="#9ca3af" stroke-width="{{2 if i%5==0 else 1}}"/>'
                 for i,y in enumerate(range(184, 27, -8))])}
      </g>

      <!-- ตัวถุง -->
      <g filter="url(#shadow_{gid})">
        <path d="M35,25 C35,13 45,7 57,7 L93,7 C105,7 115,13 115,25 L115,160
                 C115,176 104,186 88,188 L62,188 C46,186 35,176 35,160 Z"
              fill="#ffffff" stroke="#e5e7eb" stroke-width="3"/>

        <!-- ของเหลวในถุง -->
        <rect x="{INNER_LEFT:.1f}" y="{water_y:.1f}" width="{INNER_W:.1f}" height="{water_h:.1f}"
              fill="url(#liquid_{gid})" clip-path="url(#clip_{gid})"/>

        <!-- กราฟย่อย + ป้ายชื่อ (แสดงเฉพาะตอน hover) -->
        <g class="dist-group" clip-path="url(#clip_{gid})">
          {"".join(bars)}
          {"".join(labels)}
        </g>

        <!-- ผิวน้ำโค้ง + ไฮไลต์ -->
        <path d="M{INNER_LEFT:.1f},160 Q75,174 {INNER_RIGHT:.1f},160" fill="none" stroke="rgba(0,0,0,0.10)"/>
        <rect x="{INNER_LEFT+5:.1f}" y="21" width="9" height="165" fill="url(#gloss_{gid})" opacity=".55" clip-path="url(#clip_{gid})"/>
      </g>

      <!-- ป้าย 20 max -->
      <g>
        <rect x="82" y="17" rx="10" ry="10" width="52" height="22" fill="#ffffff" stroke="#e5e7eb"/>
        <text x="108" y="32" text-anchor="middle" font-size="12" fill="#374151">{BAG_MAX} max</text>
      </g>

      <!-- ตัวอักษรกรุ๊ป -->
      <text x="75" y="125" text-anchor="middle" font-weight="bold" font-size="28" fill="#ffffff">{blood_type}</text>
    </svg>

    <div class="bag-caption">
      <div class="total">{min(total, BAG_MAX)} / {BAG_MAX} unit</div>
      <div style="font-size:12px">{label}</div>
      <div class="tip">เอาเมาส์วางบนถุงเพื่อดูสัดส่วน PRC / Platelets / Plasma / Cryo</div>
    </div>
  </div>
</div>
"""
