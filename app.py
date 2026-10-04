"""
BIST Sinyal Paneli
------------------
Siteyi açtığında seçtiğin hisselerin verisini çeker; destek/direnç,
hacim, RSI ve mum yapısına bakarak AL/SAT sinyallerini gösterir.
Site açık kaldıkça her 5 dakikada bir kendini yeniler.

Yatırım tavsiyesi değildir.
"""

import datetime as dt
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


# ---------- Grafik ----------
def grafik(a: dict, mum_sayisi: int = 120) -> go.Figure:
    df = a["df"].iloc[-mum_sayisi:]
    x = df.index.strftime("%d.%m %H:%M")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25], vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=x, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                                 increasing_line_color="#16a34a", decreasing_line_color="#dc2626",
                                 name="Fiyat"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=df["EMA50"], line=dict(color="#f59e0b", width=1.2), name="EMA50"),
                  row=1, col=1)
    renk = np.where(df["Close"] >= df["Open"], "#16a34a", "#dc2626")
    fig.add_trace(go.Bar(x=x, y=df["Volume"], marker_color=renk, opacity=0.6, name="Hacim"), row=2, col=1)

    alt, ust = df["Low"].min() * 0.99, df["High"].max() * 1.01
    for s in a["seviyeler"]:
        if alt <= s <= ust:
            fig.add_hline(y=s, line_dash="dash", line_width=1,
                          line_color="#16a34a" if s < a["fiyat"] else "#dc2626",
                          annotation_text=f"{s:.2f}", annotation_position="right", row=1, col=1)

    s = a["sinyal"]
    if s and s["zaman"] in df.index:
        satir = df.loc[s["zaman"]]
        al = s["tur"] == "AL"
        fig.add_trace(go.Scatter(
            x=[s["zaman"].strftime("%d.%m %H:%M")],
            y=[satir["Low"] * 0.995 if al else satir["High"] * 1.005],
            mode="markers+text", text=[s["tur"]],
            textposition="bottom center" if al else "top center",
            marker=dict(symbol="triangle-up" if al else "triangle-down", size=14,
                        color="#16a34a" if al else "#dc2626"),
            name="Sinyal"), row=1, col=1)

    fig.update_layout(height=520, margin=dict(l=8, r=8, t=8, b=8), showlegend=False,
                      xaxis_rangeslider_visible=False, dragmode="pan")
    fig.update_xaxes(type="category", nticks=6)
    return fig


# ---------- Sayfa ----------
st.title("📈 BIST Sinyal Paneli")

with st.expander("⚙️ Ayarlar"):
    hisse_metni = st.text_input("Hisseler (virgülle ayır)", VARSAYILAN_HISSELER)
    periyot_adi = st.selectbox("Mum periyodu", list(PERIYOTLAR))
hisseler = [h.strip().upper() for h in hisse_metni.split(",") if h.strip()]
periyot, gecmis = PERIYOTLAR[periyot_adi]

if st.button("🔄 Şimdi yenile", use_container_width=True):
    st.cache_data.clear()


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
        ilerleme.progress(n / len(hisseler), text=f"{h} inceleniyor...")
    ilerleme.empty()

    st.caption(f"Son güncelleme: {dt.datetime.now(TZ):%H:%M} · Veri yaklaşık 15 dk gecikmeli · "
               f"{YENILEME.seconds // 60} dk'da bir yenilenir · Yatırım tavsiyesi değildir")
    if hatalar:
        st.warning("Veri alınamadı: " + ", ".join(hatalar))

    # --- Sinyaller ---
    st.subheader("🔔 Sinyaller")
    sinyalliler = sorted([a for a in sonuclar if a["sinyal"]], key=lambda a: a["sinyal"]["zaman"], reverse=True)
    if not sinyalliler:
        st.info(f"Son {GERIYE_BAK_MUM} mumda sinyal yok.")
    for a in sinyalliler:
        s = a["sinyal"]
        ne_zaman = "son mumda" if s["kac_mum_once"] == 0 else f"{s['kac_mum_once']} mum önce"
        metin = (f"**{'🟢 AL' if s['tur'] == 'AL' else '🔴 SAT'} · {a['hisse']}** — {s['sebep']} "
                 f"({s['seviye']:.2f})  \n"
                 f"Sinyal fiyatı {s['fiyat']:.2f} · şimdi {a['fiyat']:.2f} · "
                 f"{s['zaman']:%H:%M} ({ne_zaman}) · hacim {s['hacim_oran']:.1f}x  \n"
                 f"Stop {s['stop']:.2f} · Hedef {s['hedef']:.2f}")
        (st.success if s["tur"] == "AL" else st.error)(metin)

    # --- Tablo ---
    st.subheader("📋 Tüm hisseler")
    if sonuclar:
        tablo = pd.DataFrame([{
            "Hisse": a["hisse"],
            "Fiyat": round(a["fiyat"], 2),
            "Gün %": round(a["degisim"], 2),
            "Sinyal": a["sinyal"]["tur"] if a["sinyal"] else "—",
            "Durum": a["durum"],
            "RSI": round(a["rsi"]),
            "Trend": a["trend"],
            "Destek": round(a["destek"], 2) if a["destek"] else None,
            "Direnç": round(a["direnc"], 2) if a["direnc"] else None,
        } for a in sonuclar])
        st.dataframe(tablo, hide_index=True, use_container_width=True)

    # --- Grafik ---
    st.subheader("📊 Grafik")
    if sonuclar:
        isimler = [a["hisse"] for a in sonuclar]
        varsayilan = isimler.index(sinyalliler[0]["hisse"]) if sinyalliler else 0
        secim = st.selectbox("Hisse seç", isimler, index=varsayilan)
        a = next(x for x in sonuclar if x["hisse"] == secim)
        st.plotly_chart(grafik(a), use_container_width=True, config={"displayModeBar": False})
        bilgi = [f"Fiyat **{a['fiyat']:.2f}**", f"RSI **{a['rsi']:.0f}**", f"Trend **{a['trend']}**"]
        if a["destek"]:
            bilgi.append(f"Destek **{a['destek']:.2f}**")
        if a["direnc"]:
            bilgi.append(f"Direnç **{a['direnc']:.2f}**")
        st.markdown(" · ".join(bilgi))


panel()
