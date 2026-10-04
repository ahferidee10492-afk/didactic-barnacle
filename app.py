"""
BIST Sinyal Paneli
------------------
Siteyi açtığında seçtiğin hisselerin verisini çeker; destek/direnç,
hacim, RSI ve mum yapısına bakarak AL/SAT sinyallerini gösterir.
Site açık kaldıkça her 5 dakikada bir kendini yeniler.

Yatırım tavsiyesi değildir.
"""

import datetime as dt
import html
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from plotly.subplots import make_subplots

st.set_page_config(page_title="BIST Sinyal", page_icon="📈", layout="wide")

# ======================= AYARLAR =======================
VARSAYILAN_HISSELER = "THYAO, ASELS, GARAN, AKBNK, EREGL, SISE, KCHOL, TUPRS, BIMAS, FROTO"
PERIYOTLAR = {  # görünen ad: (mum periyodu, geriye bakılacak süre)
    "15 dk": ("15m", "30d"),
    "5 dk": ("5m", "10d"),
    "30 dk": ("30m", "45d"),
    "1 saat": ("1h", "90d"),
}
PIVOT_PENCERE = 5          # tepe/dip tespiti için sağ-sol mum sayısı
SEVIYE_TOLERANS = 0.006    # %0.6 seviyelere yakınlık toleransı
HACIM_CARPANI = 1.5        # kırılım için hacim, 20 mum ortalamasının kaç katı
DONUS_HACIM_CARPANI = 1.2  # destekten/dirençten dönüş için hacim şartı
GERIYE_BAK_MUM = 8         # son kaç kapanmış mumdaki sinyaller gösterilsin
YENILEME = dt.timedelta(minutes=5)
TZ = ZoneInfo("Europe/Istanbul")
# =======================================================


# ---------- Veri ----------
@st.cache_data(ttl=120, show_spinner=False)
def veri_cek(hisse: str, periyot: str, gecmis: str) -> pd.DataFrame:
    df = yf.Ticker(f"{hisse}.IS").history(period=gecmis, interval=periyot, auto_adjust=False)
    if df.empty:
        return df
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = df.index.tz_convert(TZ)
    return df


# ---------- Göstergeler ----------
def rsi(seri: pd.Series, n: int = 14) -> pd.Series:
    fark = seri.diff()
    kazanc = fark.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    kayip = (-fark.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = kazanc / kayip.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def gostergeler(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["RSI"] = rsi(df["Close"])
    df["EMA50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["HacimOrt"] = df["Volume"].rolling(20).mean().shift(1)
    return df


def destek_direnc_bul(df: pd.DataFrame) -> list[float]:
    """Pivot tepe/dipleri bulur, birbirine yakın olanları tek seviyede birleştirir."""
    k = PIVOT_PENCERE
    noktalar = []
    yuksek, dusuk = df["High"].values, df["Low"].values
    for i in range(k, len(df) - k):
        if yuksek[i] == yuksek[i - k:i + k + 1].max():
            noktalar.append(yuksek[i])
        if dusuk[i] == dusuk[i - k:i + k + 1].min():
            noktalar.append(dusuk[i])
    if not noktalar:
        return []
    noktalar.sort()
    gruplar = [[noktalar[0]]]
    for p in noktalar[1:]:
        if abs(p - np.mean(gruplar[-1])) / np.mean(gruplar[-1]) <= SEVIYE_TOLERANS:
            gruplar[-1].append(p)
        else:
            gruplar.append([p])
    guclu = [float(np.mean(g)) for g in gruplar if len(g) >= 2]  # en az 2 kez test edilmiş
    return guclu if guclu else [float(np.mean(g)) for g in gruplar]


# ---------- Sinyal mantığı ----------
def mum_sinyali(df: pd.DataFrame, i: int, seviyeler: list[float]):
    """df.iloc[i] mumunda sinyal var mı? (seviyeler o mumdan önceki veriden)"""
    c, p = df.iloc[i], df.iloc[i - 1]
    if not c["HacimOrt"] or np.isnan(c["HacimOrt"]):
        return None
    fiyat = c["Close"]
    hacim_oran = c["Volume"] / c["HacimOrt"]
    yesil, kirmizi = c["Close"] > c["Open"], c["Close"] < c["Open"]
    tol = SEVIYE_TOLERANS
    ustte = sorted([s for s in seviyeler if s > fiyat])
    altta = sorted([s for s in seviyeler if s < fiyat], reverse=True)

    def al(sebep, L):
        return dict(tur="AL", sebep=sebep, seviye=L, stop=L * (1 - tol),
                    hedef=ustte[0] if ustte else fiyat * 1.03, fiyat=fiyat, hacim_oran=hacim_oran)

    def sat(sebep, L):
        return dict(tur="SAT", sebep=sebep, seviye=L, stop=L * (1 + tol),
                    hedef=altta[0] if altta else fiyat * 0.97, fiyat=fiyat, hacim_oran=hacim_oran)

    for L in seviyeler:
        if p["Close"] < L and c["Close"] > L * (1 + tol / 2) and yesil and hacim_oran >= HACIM_CARPANI:
            return al("Direnç hacimli kırıldı", L)
        if p["Close"] > L and c["Close"] < L * (1 - tol / 2) and kirmizi and hacim_oran >= HACIM_CARPANI:
            return sat("Destek hacimli kırıldı", L)
        if (c["Low"] <= L * (1 + tol) and c["Close"] > L and yesil
                and hacim_oran >= DONUS_HACIM_CARPANI and c["RSI"] < 60):
            return al("Destekten hacimli dönüş", L)
        if (c["High"] >= L * (1 - tol) and c["Close"] < L and kirmizi
                and hacim_oran >= DONUS_HACIM_CARPANI and c["RSI"] > 40):
            return sat("Dirençten hacimli dönüş", L)
    return None


def analiz_et(hisse: str, ham: pd.DataFrame) -> dict:
    df = gostergeler(ham)
    kapali = df.iloc[:-1]  # son mum seans içinde henüz kapanmamış olabilir

    # Son kapanmış mumlardan geriye doğru en yeni sinyali ara
    son_sinyal = None
    for i in range(len(kapali) - 1, max(len(kapali) - 1 - GERIYE_BAK_MUM, 30), -1):
        s = mum_sinyali(kapali, i, destek_direnc_bul(kapali.iloc[:i]))
        if s:
            s["zaman"] = kapali.index[i]
            s["kac_mum_once"] = len(kapali) - 1 - i
            son_sinyal = s
            break

    seviyeler = destek_direnc_bul(kapali)
    son = df.iloc[-1]
    fiyat = float(son["Close"])
    destek = max([s for s in seviyeler if s < fiyat], default=None)
    direnc = min([s for s in seviyeler if s > fiyat], default=None)

    bugun = df[df.index.date == df.index[-1].date()]
    degisim = (fiyat / bugun["Open"].iloc[0] - 1) * 100 if len(bugun) else 0.0

    if direnc and (direnc - fiyat) / fiyat < 0.01:
        durum = "Dirence yakın"
    elif destek and (fiyat - destek) / fiyat < 0.01:
        durum = "Desteğe yakın"
    else:
        durum = "Arada"

    return dict(hisse=hisse, df=df, fiyat=fiyat, degisim=degisim, rsi=float(son["RSI"]),
                trend="Yukarı" if fiyat > son["EMA50"] else "Aşağı",
                seviyeler=seviyeler, destek=destek, direnc=direnc, durum=durum,
                sinyal=son_sinyal, guncel=df.index[-1])


# ---------- Görünüm ----------
RENK = dict(zemin="#0b0f14", kart="#121821", cizgi="#1f2a37", yazi="#e6edf3",
            soluk="#8b98a5", yesil="#22c55e", kirmizi="#ef4444", vurgu="#f5a524")

STIL = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'IBM Plex Sans', sans-serif; }}
.stApp {{ background: {RENK['zemin']}; color: {RENK['yazi']}; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
.block-container {{ padding: 1rem 0.9rem 3rem; max-width: 900px; }}
.mono {{ font-family: 'JetBrains Mono', monospace; }}

.ust {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:.4rem; }}
.logo {{ font-weight:700; font-size:1.35rem; letter-spacing:-.02em; }}
.logo span {{ color:{RENK['vurgu']}; }}
.seans {{ font-size:.75rem; padding:.25rem .6rem; border-radius:999px; border:1px solid {RENK['cizgi']}; }}
.seans.acik {{ color:{RENK['yesil']}; border-color:{RENK['yesil']}55; }}
.seans.kapali {{ color:{RENK['soluk']}; }}
.altbilgi {{ color:{RENK['soluk']}; font-size:.72rem; margin-bottom:1rem; }}

.ozet {{ display:grid; grid-template-columns:repeat(3,1fr); gap:.5rem; margin-bottom:1.2rem; }}
.ozet div {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:12px; padding:.6rem .7rem; }}
.ozet b {{ display:block; font-family:'JetBrains Mono',monospace; font-size:1.3rem; }}
.ozet small {{ color:{RENK['soluk']}; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; }}

.baslik {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:{RENK['soluk']};
          margin:1.2rem 0 .5rem; font-weight:600; }}

.kart {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-left:4px solid;
        border-radius:12px; padding:.75rem .85rem; margin-bottom:.6rem; }}
.kart.al {{ border-left-color:{RENK['yesil']}; }}
.kart.sat {{ border-left-color:{RENK['kirmizi']}; }}
.kart-ust {{ display:flex; align-items:center; gap:.55rem; }}
.rozet {{ font-weight:700; font-size:.75rem; padding:.15rem .5rem; border-radius:6px; color:#0b0f14; }}
.rozet.al {{ background:{RENK['yesil']}; }}
.rozet.sat {{ background:{RENK['kirmizi']}; }}
.kod {{ font-weight:700; font-size:1.05rem; }}
.fiyat {{ margin-left:auto; font-family:'JetBrains Mono',monospace; font-size:1.05rem; }}
.sebep {{ color:{RENK['yazi']}; font-size:.85rem; margin:.35rem 0 .5rem; }}
.cipler {{ display:flex; flex-wrap:wrap; gap:.35rem; }}
.cipler span {{ font-size:.72rem; color:{RENK['soluk']}; background:{RENK['zemin']};
               border:1px solid {RENK['cizgi']}; border-radius:6px; padding:.15rem .45rem; }}
.cipler .stop {{ color:{RENK['kirmizi']}; }}
.cipler .hedef {{ color:{RENK['yesil']}; }}
.bos {{ background:{RENK['kart']}; border:1px dashed {RENK['cizgi']}; border-radius:12px;
       padding:.9rem; color:{RENK['soluk']}; font-size:.85rem; text-align:center; }}

.liste {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:12px; overflow:hidden; }}
.satir {{ display:grid; grid-template-columns:1.1fr 1fr .8fr 1.1fr; align-items:center;
         padding:.55rem .8rem; border-bottom:1px solid {RENK['cizgi']}; font-size:.85rem; }}
.satir:last-child {{ border-bottom:none; }}
.satir.bas {{ color:{RENK['soluk']}; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; }}
.satir .sag {{ text-align:right; font-family:'JetBrains Mono',monospace; }}
.arti {{ color:{RENK['yesil']}; }} .eksi {{ color:{RENK['kirmizi']}; }}
.hap {{ justify-self:end; font-size:.68rem; padding:.12rem .45rem; border-radius:999px;
       border:1px solid {RENK['cizgi']}; color:{RENK['soluk']}; white-space:nowrap; }}
.hap.al {{ color:{RENK['yesil']}; border-color:{RENK['yesil']}66; }}
.hap.sat {{ color:{RENK['kirmizi']}; border-color:{RENK['kirmizi']}66; }}
.hap.yakin {{ color:{RENK['vurgu']}; border-color:{RENK['vurgu']}66; }}

.bilgi {{ display:grid; grid-template-columns:repeat(4,1fr); gap:.4rem; margin-top:.3rem; }}
.bilgi div {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:10px;
             padding:.45rem .55rem; font-size:.7rem; color:{RENK['soluk']}; }}
.bilgi b {{ display:block; color:{RENK['yazi']}; font-family:'JetBrains Mono',monospace; font-size:.9rem; }}

.uyari {{ color:{RENK['soluk']}; font-size:.7rem; text-align:center; margin-top:1.5rem; }}
div[data-testid="stProgress"] > div > div > div {{ background:{RENK['vurgu']}; }}
</style>
"""


def seans_acik_mi() -> bool:
    simdi = dt.datetime.now(TZ)
    return simdi.weekday() < 5 and dt.time(10, 0) <= simdi.time() <= dt.time(18, 10)


def sayi(x, ondalik=2):
    return "—" if x is None else f"{x:,.{ondalik}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def sinyal_karti(a: dict) -> str:
    s = a["sinyal"]
    tur = s["tur"].lower()
    ne_zaman = "son mumda" if s["kac_mum_once"] == 0 else f"{s['kac_mum_once']} mum önce"
    if s["tur"] == "AL":
        risk, kazanc = s["fiyat"] - s["stop"], s["hedef"] - s["fiyat"]
    else:
        risk, kazanc = s["stop"] - s["fiyat"], s["fiyat"] - s["hedef"]
    rk = f"R/K {kazanc / risk:.1f}" if risk > 0 and kazanc > 0 else ""
    return f"""
<div class="kart {tur}">
  <div class="kart-ust"><span class="rozet {tur}">{s['tur']}</span>
    <span class="kod">{html.escape(a['hisse'])}</span>
    <span class="fiyat">{sayi(a['fiyat'])}</span></div>
  <div class="sebep">{s['sebep']} · seviye {sayi(s['seviye'])}</div>
  <div class="cipler">
    <span>⏱ {s['zaman']:%H:%M} · {ne_zaman}</span>
    <span>Sinyal {sayi(s['fiyat'])}</span>
    <span>Hacim {s['hacim_oran']:.1f}x</span>
    <span class="stop">Stop {sayi(s['stop'])}</span>
    <span class="hedef">Hedef {sayi(s['hedef'])}</span>
    {f'<span>{rk}</span>' if rk else ''}
  </div>
</div>"""


def hisse_listesi(sonuclar: list[dict]) -> str:
    satirlar = ['<div class="satir bas"><span>Hisse</span><span class="sag">Fiyat</span>'
                '<span class="sag">Gün</span><span class="sag">Durum</span></div>']
    for a in sonuclar:
        if a["sinyal"]:
            hap = f'<span class="hap {a["sinyal"]["tur"].lower()}">{a["sinyal"]["tur"]} sinyali</span>'
        elif a["durum"] != "Arada":
            hap = f'<span class="hap yakin">{a["durum"]}</span>'
        else:
            hap = f'<span class="hap">RSI {a["rsi"]:.0f}</span>'
        yon = "arti" if a["degisim"] >= 0 else "eksi"
        satirlar.append(
            f'<div class="satir"><b>{html.escape(a["hisse"])}</b>'
            f'<span class="sag">{sayi(a["fiyat"])}</span>'
            f'<span class="sag {yon}">{a["degisim"]:+.2f}%</span>{hap}</div>')
    return '<div class="liste">' + "".join(satirlar) + "</div>"


# ---------- Grafik ----------
def grafik(a: dict, mum_sayisi: int = 120) -> go.Figure:
    df = a["df"].iloc[-mum_sayisi:]
    x = df.index.strftime("%d.%m %H:%M")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.76, 0.24], vertical_spacing=0.02)
    fig.add_trace(go.Candlestick(
        x=x, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        increasing=dict(line=dict(color=RENK["yesil"]), fillcolor=RENK["yesil"]),
        decreasing=dict(line=dict(color=RENK["kirmizi"]), fillcolor=RENK["kirmizi"]),
        name="Fiyat"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=df["EMA50"], line=dict(color=RENK["vurgu"], width=1.3), name="EMA50"),
                  row=1, col=1)
    renk = np.where(df["Close"] >= df["Open"], RENK["yesil"], RENK["kirmizi"])
    fig.add_trace(go.Bar(x=x, y=df["Volume"], marker_color=renk, opacity=0.45, name="Hacim"), row=2, col=1)

    alt, ust = df["Low"].min() * 0.99, df["High"].max() * 1.01
    for s in a["seviyeler"]:
        if alt <= s <= ust:
            c = RENK["yesil"] if s < a["fiyat"] else RENK["kirmizi"]
            fig.add_hline(y=s, line_dash="dot", line_width=1, line_color=c, opacity=0.8,
                          annotation_text=sayi(s), annotation_position="top left",
                          annotation_font=dict(color=c, size=10), row=1, col=1)

    s = a["sinyal"]
    if s and s["zaman"] in df.index:
        satir = df.loc[s["zaman"]]
        al = s["tur"] == "AL"
        c = RENK["yesil"] if al else RENK["kirmizi"]
        fig.add_trace(go.Scatter(
            x=[s["zaman"].strftime("%d.%m %H:%M")],
            y=[satir["Low"] * 0.994 if al else satir["High"] * 1.006],
            mode="markers+text", text=[s["tur"]], textfont=dict(color=c, size=11),
            textposition="bottom center" if al else "top center",
            marker=dict(symbol="triangle-up" if al else "triangle-down", size=13, color=c),
            name="Sinyal"), row=1, col=1)

    fig.update_layout(
        height=480, margin=dict(l=4, r=4, t=6, b=4), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=RENK["zemin"],
        font=dict(family="IBM Plex Sans, sans-serif", color=RENK["soluk"], size=10),
        xaxis_rangeslider_visible=False, dragmode="pan", hovermode="x unified")
    fig.update_xaxes(type="category", nticks=5, gridcolor=RENK["cizgi"], showline=False)
    fig.update_yaxes(gridcolor=RENK["cizgi"], side="right", zeroline=False)
    return fig


# ---------- Sayfa ----------
st.markdown(STIL, unsafe_allow_html=True)

acik = seans_acik_mi()
st.markdown(
    f'<div class="ust"><div class="logo">BIST<span>·</span>Sinyal</div>'
    f'<div class="seans {"acik" if acik else "kapali"}">{"● Seans açık" if acik else "○ Seans kapalı"}</div></div>',
    unsafe_allow_html=True)

with st.expander("⚙️ Ayarlar"):
    hisse_metni = st.text_input("Hisseler (virgülle ayır)", VARSAYILAN_HISSELER)
    periyot_adi = st.selectbox("Mum periyodu", list(PERIYOTLAR))
    if st.button("🔄 Verileri şimdi yenile", use_container_width=True):
        st.cache_data.clear()
hisseler = [h.strip().upper() for h in hisse_metni.split(",") if h.strip()]
periyot, gecmis = PERIYOTLAR[periyot_adi]


@st.fragment(run_every=YENILEME)
def panel():
    sonuclar, hatalar = [], []
    ilerleme = st.progress(0.0, text="Veriler çekiliyor...")
    for n, h in enumerate(hisseler, 1):
        try:
            ham = veri_cek(h, periyot, gecmis)
            if len(ham) < 60:
                hatalar.append(h)
            else:
                sonuclar.append(analiz_et(h, ham))
        except Exception:
            hatalar.append(h)
        ilerleme.progress(n / max(len(hisseler), 1), text=f"{h} inceleniyor...")
    ilerleme.empty()

    st.markdown(f'<div class="altbilgi">Güncellendi {dt.datetime.now(TZ):%H:%M} · '
                f'{periyot_adi} mumlar · {YENILEME.seconds // 60} dk\'da bir yenilenir</div>',
                unsafe_allow_html=True)
    if hatalar:
        st.warning("Veri alınamadı: " + ", ".join(hatalar))

    sinyalliler = sorted([a for a in sonuclar if a["sinyal"]], key=lambda a: a["sinyal"]["zaman"], reverse=True)
    al_say = sum(a["sinyal"]["tur"] == "AL" for a in sinyalliler)
    sat_say = len(sinyalliler) - al_say
    st.markdown(
        f'<div class="ozet"><div><small>AL</small><b class="arti">{al_say}</b></div>'
        f'<div><small>SAT</small><b class="eksi">{sat_say}</b></div>'
        f'<div><small>Takip</small><b>{len(sonuclar)}</b></div></div>',
        unsafe_allow_html=True)

    st.markdown('<div class="baslik">Sinyaller</div>', unsafe_allow_html=True)
    if sinyalliler:
        st.markdown("".join(sinyal_karti(a) for a in sinyalliler), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bos">Son {GERIYE_BAK_MUM} mumda sinyal yok</div>', unsafe_allow_html=True)

    if not sonuclar:
        return

    st.markdown('<div class="baslik">Grafik</div>', unsafe_allow_html=True)
    isimler = [a["hisse"] for a in sonuclar]
    onceki = st.session_state.get("secili")
    if onceki not in isimler:
        onceki = sinyalliler[0]["hisse"] if sinyalliler else isimler[0]
    secim = st.pills("Hisse", isimler, default=onceki, label_visibility="collapsed") or onceki
    st.session_state["secili"] = secim
    a = next(x for x in sonuclar if x["hisse"] == secim)
    st.plotly_chart(grafik(a), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f'<div class="bilgi"><div>Fiyat<b>{sayi(a["fiyat"])}</b></div>'
        f'<div>RSI<b>{a["rsi"]:.0f}</b></div>'
        f'<div>Destek<b class="arti">{sayi(a["destek"])}</b></div>'
        f'<div>Direnç<b class="eksi">{sayi(a["direnc"])}</b></div></div>',
        unsafe_allow_html=True)

    st.markdown('<div class="baslik">Tüm hisseler</div>', unsafe_allow_html=True)
    st.markdown(hisse_listesi(sonuclar), unsafe_allow_html=True)

    st.markdown('<div class="uyari">Veri yaklaşık 15 dk gecikmelidir · Yatırım tavsiyesi değildir</div>',
                unsafe_allow_html=True)


panel()
