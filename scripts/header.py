import base64, os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(root, "assets")
def b64(p): return base64.b64encode(open(os.path.join(root, p), "rb").read()).decode()
FONTS = ("<style>"
 + "".join(f"@font-face{{font-family:'{n}';src:url(data:font/woff2;base64,{b64('assets/fonts/'+f)}) format('woff2');}}"
           for n, f in [("Sync", "Syncopate-Bold.woff2"), ("In", "Inter-400.woff2"), ("InS", "Inter-600.woff2"), ("Mono", "JBM-500.woff2")])
 + ".d{font-family:'Sync',Arial Black,sans-serif;font-weight:700}.i{font-family:'In',Helvetica,Arial,sans-serif}"
 + ".s{font-family:'InS',Helvetica,Arial,sans-serif;font-weight:600}.m{font-family:'Mono',Menlo,Consolas,monospace}"
 + "</style>")
THEMES = {
  "dark":  dict(bg="#020204", panel="#0b0b12", line="#1e293b", grid="#ffffff", gridop="0.035", fg="#f8fafc", sub="#94a3b8", mute="#64748b", chip="#0f172a", photo="#0f172a", ring="#ffffff1a", outer="#ffffff14"),
  "light": dict(bg="#f8fafc", panel="#ffffff", line="#e2e8f0", grid="#0f172a", gridop="0.05", fg="#0f172a", sub="#475569", mute="#64748b", chip="#f1f5f9", photo="#e2e8f0", ring="#ffffff99", outer="#0ea5e933"),
}
SKY, VIO = "#0ea5e9", "#8b5cf6"
def top_round(x, y, w, h, r):
    return f'M{x} {y+h}V{y+r}a{r} {r} 0 0 1 {r} -{r}H{x+w-r}a{r} {r} 0 0 1 {r} {r}V{y+h}Z'
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def head(W, H): return [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', FONTS]

def hero(t):
    W, H = 1000, 330
    photo = b64("assets/source/photo.jpg")
    o = head(W, H)
    o.append('<defs>'
      f'<linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
      f'<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{t["grid"]}" stroke-opacity="{t["gridop"]}"/></pattern>'
      f'<radialGradient id="g1" cx="0.85" cy="0.1" r="0.6"><stop offset="0" stop-color="{SKY}" stop-opacity="0.16"/><stop offset="1" stop-color="{SKY}" stop-opacity="0"/></radialGradient>'
      f'<radialGradient id="g2" cx="0.05" cy="1" r="0.6"><stop offset="0" stop-color="{VIO}" stop-opacity="0.12"/><stop offset="1" stop-color="{VIO}" stop-opacity="0"/></radialGradient>'
      f'<linearGradient id="fadeR" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
      f'<mask id="gm"><rect width="{W}" height="{H}" fill="url(#fadeR)"/></mask>'
      '<clipPath id="pc"><circle cx="846" cy="186" r="96"/></clipPath>'
      f'<filter id="halo" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="22"/></filter>'
      f'<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
      '</defs>')
    o.append(f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>')
    o.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#grid)" mask="url(#gm)"/>')
    o.append(f'<rect width="{W}" height="{H}" rx="18" fill="url(#g1)"/><rect width="{W}" height="{H}" rx="18" fill="url(#g2)"/>')
    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{t["line"]}"/>')
    logo = b64("assets/source/rvh-logo.png")
    o.append(f'<mask id="rvh" maskUnits="userSpaceOnUse" x="50" y="22" width="80" height="34">'
             f'<image href="data:image/png;base64,{logo}" xlink:href="data:image/png;base64,{logo}" x="50" y="23" width="80" height="30.5"/></mask>'
             f'<rect x="50" y="22" width="80" height="34" fill="{t["fg"]}" mask="url(#rvh)"/>')
    o.append(f'<linearGradient id="acw" gradientUnits="userSpaceOnUse" x1="790" y1="0" x2="905" y2="0">'
             f'<stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
             f'<text x="846" y="45" class="s" font-size="14" fill="{t["fg"]}" text-anchor="middle">'
             f'www.<tspan fill="url(#acw)">rafvanhooijdonk</tspan>.nl</text>')
    o.append('<linearGradient id="sweepW" gradientUnits="userSpaceOnUse" x1="700" y1="0" x2="760" y2="0">'
             '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.9"/>'
             '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
             '<animateTransform attributeName="gradientTransform" type="translate" values="0 0;260 0;260 0" keyTimes="0;0.25;1" '
             'begin="5s" dur="6s" repeatCount="indefinite"/></linearGradient>'
             '<text x="846" y="45" class="s" font-size="14" fill="url(#sweepW)" text-anchor="middle">www.rafvanhooijdonk.nl</text>')
    o.append(f'<text x="52" y="98.5" class="m" font-size="12.5" fill="{SKY}" letter-spacing="2.2">FULL-STACK SOFTWARE &amp; AI ENGINEER</text>')
    o.append(f'<text x="50" y="177.5" class="d" font-size="50" fill="{t["fg"]}" letter-spacing="1">RAF VAN</text>')
    o.append(f'<text x="50" y="235.5" class="d" font-size="50" fill="url(#ac)" letter-spacing="1">HOOIJDONK</text>')
    o.append('<linearGradient id="sweepN" gradientUnits="userSpaceOnUse" x1="-130" y1="0" x2="-40" y2="0">'
             '<stop offset="0" stop-color="#ffffff" stop-opacity="0"/><stop offset="0.5" stop-color="#ffffff" stop-opacity="0.85"/>'
             '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/>'
             '<animateTransform attributeName="gradientTransform" type="translate" values="0 0;640 0;640 0" keyTimes="0;0.35;1" '
             'begin="3s" dur="6s" repeatCount="indefinite"/></linearGradient>')
    o.append('<text x="50" y="177.5" class="d" font-size="50" fill="url(#sweepN)" letter-spacing="1">RAF VAN</text>'
             '<text x="50" y="235.5" class="d" font-size="50" fill="url(#sweepN)" letter-spacing="1">HOOIJDONK</text>')
    o.append(f'<clipPath id="bar0"><rect x="52" y="118" width="64" height="3" rx="1.5"/></clipPath>'
             f'<g><rect x="52" y="118" width="64" height="3" rx="1.5" fill="url(#ac)"/>'
             f'<rect x="28" y="118" width="24" height="3" fill="url(#shine)" opacity="0.8" clip-path="url(#bar0)">'
             f'<animate attributeName="x" values="28;116;116" keyTimes="0;0.5;1" dur="5s" repeatCount="indefinite"/></rect></g>')
    o.append(f'<clipPath id="bar"><rect x="52" y="256" width="64" height="3" rx="1.5"/></clipPath>'
             f'<g><rect x="52" y="256" width="64" height="3" rx="1.5" fill="url(#ac)"/>'
             f'<rect x="28" y="256" width="24" height="3" fill="url(#shine)" opacity="0.8" clip-path="url(#bar)">'
             f'<animate attributeName="x" values="28;116;116" keyTimes="0;0.5;1" dur="5s" repeatCount="indefinite"/></rect></g>')
    ends = [0, 11.13, 17.70, 21.81, 32.22, 42.66, 46.77, 56.81, 67.23, 72.02, 80.98, 91.19, 96.89, 102.70,
            116.61, 126.16, 132.28, 142.19, 147.09, 151.88, 161.92, 171.47, 177.59, 188.00, 201.91, 211.45,
            217.58, 227.48, 232.27, 243.22, 248.00, 259.72, 264.28, 269.19]
    begin, per = 0.6, 0.065
    typing = round(per * (len(ends) - 1), 3)
    widths = ";".join(f"{w + 1:.2f}" for w in ends)
    cursor_x = ";".join(f"{52 + w + 2:.2f}" for w in ends)
    o.append(f'<clipPath id="typed"><rect x="50" y="270.5" width="0" height="28">'
             f'<animate attributeName="width" values="{widths}" calcMode="discrete" begin="{begin}s" dur="{typing}s" fill="freeze"/></rect></clipPath>')
    o.append(f'<text x="52" y="290.5" class="i" font-size="17" fill="{t["sub"]}" clip-path="url(#typed)">Bridging software, hardware &amp; AI.</text>')
    o.append(f'<rect x="54" y="275.5" width="2" height="19" rx="1" fill="{SKY}">'
             f'<animate attributeName="x" values="{cursor_x}" calcMode="discrete" begin="{begin}s" dur="{typing}s" fill="freeze"/>'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" begin="{begin + typing}s" dur="1.1s" repeatCount="indefinite"/></rect>')
    o.append(f'<circle cx="846" cy="186" r="106" fill="{SKY}" fill-opacity="0.2" filter="url(#halo)"/>')
    o.append(f'<circle cx="846" cy="186" r="96" fill="{t["photo"]}"/>')
    o.append(f'<image href="data:image/jpeg;base64,{photo}" xlink:href="data:image/jpeg;base64,{photo}" x="750" y="90" width="192" height="192" clip-path="url(#pc)" preserveAspectRatio="xMidYMid slice"/>')
    o.append(f'<circle cx="846" cy="186" r="95" fill="none" stroke="{t["ring"]}" stroke-width="2"/>')
    o.append(f'<circle cx="846" cy="186" r="112" fill="none" stroke="{SKY}" stroke-opacity="0.3" stroke-dasharray="4 4">'
             '<animateTransform attributeName="transform" type="rotate" from="0 846 186" to="360 846 186" dur="12s" repeatCount="indefinite"/></circle>')
    o.append(f'<circle cx="846" cy="186" r="128" fill="none" stroke="{t["outer"]}"/>')
    o.append('</svg>')
    return "\n".join(o)

def divider(t):
    W, H = 1000, 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><defs>'
            f'<linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}" stop-opacity="0"/><stop offset="0.5" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect y="3.5" width="{W}" height="1" fill="{t["line"]}"/>'
            f'<rect x="-200" y="3.5" width="200" height="1" fill="url(#g)"><animate attributeName="x" values="-200;{W}" dur="7s" repeatCount="indefinite"/></rect></svg>')

for tn, t in THEMES.items():
    open(f"{out}/hero-{tn}.svg", "w").write(hero(t))
    open(f"{out}/divider-{tn}.svg", "w").write(divider(t))


def contact_tile(t, num, kind, label, value, sub):
    W, H = 320, 150
    li = base64.b64encode(open(os.path.join(root, "assets/source/linkedin.svg"), "rb").read()).decode()
    icons = {
        "web": f'<circle cx="48" cy="72" r="15" fill="none" stroke="{SKY}" stroke-width="2"/>'
               f'<ellipse cx="48" cy="72" rx="6.5" ry="15" fill="none" stroke="{SKY}" stroke-width="2"/>'
               f'<line x1="33" y1="72" x2="63" y2="72" stroke="{SKY}" stroke-width="2"/>',
        "linkedin": f'<image href="data:image/svg+xml;base64,{li}" x="33" y="57" width="30" height="30"/>',
        "mail": f'<rect x="33" y="61" width="30" height="22" rx="3" fill="none" stroke="{VIO}" stroke-width="2"/>'
                f'<path d="M34 63 L48 74 L62 63" fill="none" stroke="{VIO}" stroke-width="2" stroke-linejoin="round"/>',
    }
    o = head(W, H)
    o.append(f'<defs><linearGradient id="ac" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{SKY}"/><stop offset="1" stop-color="{VIO}"/></linearGradient>'
             '<linearGradient id="shine" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.5" stop-color="#fff" stop-opacity="0.9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
             '<clipPath id="tb"><rect x="24" y="0.5" width="48" height="3" rx="1.5"/></clipPath></defs>')
    o.append(f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    o.append('<rect x="24" y="0.5" width="48" height="3" rx="1.5" fill="url(#ac)"/>'
             '<rect x="12" y="0.5" width="18" height="3" fill="url(#shine)" opacity="0.8" clip-path="url(#tb)">'
             '<animate attributeName="x" values="12;72;72" keyTimes="0;0.5;1" dur="5s" repeatCount="indefinite"/></rect>')
    o.append(f'<text x="24" y="34" class="m" font-size="10" fill="{SKY}" letter-spacing="1.6">{num} // {label.upper()}</text>')
    o.append(f'<rect x="24" y="48" width="48" height="48" rx="12" fill="{t["chip"]}" stroke="{t["line"]}"/>' + icons[kind])
    o.append(f'<text x="86" y="69" class="s" font-size="{15 if len(value) < 22 else 13}" fill="{t["fg"]}">{esc(value)}</text>'
             f'<text x="86" y="88" class="i" font-size="12" fill="{t["sub"]}">{esc(sub)}</text>')
    o.append(f'<line x1="24" y1="114" x2="{W-24}" y2="114" stroke="{t["line"]}"/>'
             f'<text x="24" y="134" class="m" font-size="10.5" fill="{t["mute"]}">Open &#8599;</text>')
    o.append('</svg>')
    return "\n".join(o)


for tn, t in THEMES.items():
    for slug, kind, label, value, sub in (
            ("website", "web", "Website", "rafvanhooijdonk.nl", "Portfolio and projects"),
            ("linkedin", "linkedin", "LinkedIn", "Raf van Hooijdonk", "Experience and education"),
            ("mail", "mail", "Email", "contact@rafvanhooijdonk.nl", "Questions or a project")):
        n = {"website": "01", "linkedin": "02", "mail": "03"}[slug]
        open(f"{out}/contact-{slug}-{tn}.svg", "w").write(contact_tile(t, n, kind, label, value, sub))
