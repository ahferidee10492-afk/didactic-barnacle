"""
BIST Sinyal Paneli
------------------
Siteyi açtığında seçtiğin hisselerin verisini çeker ve şunlara bakar:
  - Destek / direnç seviyeleri (en az iki kez test edilmiş tepe ve dipler)
  - Formasyonlar: ikili dip/tepe, OBO/TOBO, yükselen/alçalan/simetrik üçgen, bayrak
  - Göstergeler: EMA20/50/200, RSI, MACD, Bollinger sıkışması, ATR, hacim
  - BIST100'ün yönü
Her sinyale 0-100 arası bir güven puanı verir, gerekçelerini yazar ve
aynı kuralların son 30 günde o hissede ne kadar tuttuğunu gösterir.

Yatırım tavsiyesi değildir.
"""

import bisect
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
PIVOT_PENCERE = 5        # tepe/dip tespiti için sağ-sol mum sayısı
SEVIYE_TOLERANS = 0.006  # %0.6 seviyelere yakınlık toleransı
GERIYE_BAK_MUM = 8       # "güncel sinyal" sayılacak son mum sayısı
VARSAYILAN_MIN_GUVEN = 45
TEST_UFKU = 26           # geçmiş testte sinyalden sonra kaç mum içinde hedef/stop aranır
YENILEME = dt.timedelta(minutes=5)
TZ = ZoneInfo("Europe/Istanbul")
# =======================================================


def sayi(x, ondalik=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{ondalik}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def nanv(x, varsayilan=0.0):
    return varsayilan if x is None or np.isnan(x) else float(x)


def seans_acik_mi() -> bool:
    simdi = dt.datetime.now(TZ)
    return simdi.weekday() < 5 and dt.time(10, 0) <= simdi.time() <= dt.time(18, 10)


# ---------- Veri ----------
@st.cache_data(ttl=120, show_spinner=False)
def veri_cek(sembol: str, periyot: str, gecmis: str) -> pd.DataFrame:
    df = yf.Ticker(sembol).history(period=gecmis, interval=periyot, auto_adjust=False)
    if df.empty:
        return df
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    df.index = df.index.tz_convert(TZ)
    return df


def piyasa_yonu(periyot: str, gecmis: str) -> pd.Series:
    """BIST100 fiyatı EMA50'nin üstündeyse +1, altındaysa -1."""
    try:
        x = veri_cek("XU100.IS", periyot, gecmis)
        if len(x) < 60:
            return pd.Series(dtype=float)
        return np.sign(x["Close"] - x["Close"].ewm(span=50, adjust=False).mean())
    except Exception:
        return pd.Series(dtype=float)


# ---------- Göstergeler ----------
def rsi(seri: pd.Series, n: int = 14) -> pd.Series:
    fark = seri.diff()
    kazanc = fark.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    kayip = (-fark.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + kazanc / kayip.replace(0, np.nan))


def gostergeler(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c = df["Close"]
    for n in (20, 50, 200):
        df[f"EMA{n}"] = c.ewm(span=n, adjust=False).mean()
    df["RSI"] = rsi(c)
    df["MACD"] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["MACDs"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACDh"] = df["MACD"] - df["MACDs"]
    onceki = c.shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - onceki).abs(), (df["Low"] - onceki).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    orta, sd = c.rolling(20).mean(), c.rolling(20).std()
    df["BBu"], df["BBa"] = orta + 2 * sd, orta - 2 * sd
    df["BBw"] = (df["BBu"] - df["BBa"]) / orta
    df["BBwMin"] = df["BBw"].rolling(60, min_periods=20).min()
    df["HacimOrt"] = df["Volume"].rolling(20).mean().shift(1)
    df["HacimOran"] = df["Volume"] / df["HacimOrt"].replace(0, np.nan)
    return df


# ---------- Tepe / dip ve seviyeler ----------
def pivot_bul(df: pd.DataFrame) -> list[tuple]:
    """(mum no, fiyat, 'H' tepe / 'L' dip) listesi, zamana göre sıralı."""
    w = 2 * PIVOT_PENCERE + 1
    hm = df["High"].rolling(w, center=True).max().values
    lm = df["Low"].rolling(w, center=True).min().values
    H, L = df["High"].values, df["Low"].values
    pv = []
    for j in range(len(df)):
        if not np.isnan(hm[j]) and H[j] == hm[j]:
            pv.append((j, float(H[j]), "H"))
        if not np.isnan(lm[j]) and L[j] == lm[j]:
            pv.append((j, float(L[j]), "L"))
    return pv


def seviyeler_bul(pv: list[tuple]) -> list[float]:
    if not pv:
        return []
    fiyatlar = sorted(p[1] for p in pv)
    gruplar = [[fiyatlar[0]]]
    for f in fiyatlar[1:]:
        m = np.mean(gruplar[-1])
        if abs(f - m) / m <= SEVIYE_TOLERANS:
            gruplar[-1].append(f)
        else:
            gruplar.append([f])
    guclu = [float(np.mean(g)) for g in gruplar if len(g) >= 2]
    return guclu if guclu else [float(np.mean(g)) for g in gruplar]


# ---------- Formasyonlar ----------
def _dogru(p1, p2, j):
    (j1, y1), (j2, y2) = p1, p2
    return y1 if j2 == j1 else y1 + (y2 - y1) * (j - j1) / (j2 - j1)


def formasyonlar(A: dict, pv: list[tuple], i: int) -> list[dict]:
    """Formasyon yapısı i'den önceki veriyle kurulur, i. mumda kırılım olup olmadığına bakılır.
    durum: 'kırıldı' (bu mumda) veya 'oluşuyor'."""
    C, Hh, Ll = A["Close"], A["High"], A["Low"]
    c, cp, atr = C[i], C[i - 1], nanv(A["ATR"][i], C[i] * 0.01)
    H = [p for p in pv if p[2] == "H" and p[0] >= i - 120]
    L = [p for p in pv if p[2] == "L" and p[0] >= i - 120]
    sonuc = []

    def ekle(ad, yon, durum, cizgiler, hedef, ref):
        sonuc.append(dict(ad=ad, yon=yon, durum=durum, cizgiler=cizgiler, hedef=hedef, ref=ref))

    # İkili dip
    if len(L) >= 2:
        (j1, p1, _), (j2, p2, _) = L[-2], L[-1]
        if j2 - j1 >= 8 and abs(p1 - p2) / p1 <= 0.015 and i - j2 <= 40:
            jm = j1 + int(np.argmax(Hh[j1:j2 + 1]))
            boyun, dip = float(Hh[jm]), min(p1, p2)
            sonra_min = np.min(Ll[j2 + 1:i], initial=np.inf)
            if boyun / max(p1, p2) - 1 >= 0.02 and sonra_min >= dip * 0.99:
                durum = "kırıldı" if c > boyun >= cp else ("oluşuyor" if c <= boyun else None)
                if durum:
                    ekle("İkili dip", 1, durum, [(j1, p1, jm, boyun), (jm, boyun, j2, p2), (j1, boyun, i, boyun)],
                         boyun + (boyun - dip), boyun)
    # İkili tepe
    if len(H) >= 2:
        (j1, p1, _), (j2, p2, _) = H[-2], H[-1]
        if j2 - j1 >= 8 and abs(p1 - p2) / p1 <= 0.015 and i - j2 <= 40:
            jm = j1 + int(np.argmin(Ll[j1:j2 + 1]))
            boyun, tepe = float(Ll[jm]), max(p1, p2)
            sonra_max = np.max(Hh[j2 + 1:i], initial=-np.inf)
            if 1 - boyun / min(p1, p2) >= 0.02 and sonra_max <= tepe * 1.01:
                durum = "kırıldı" if c < boyun <= cp else ("oluşuyor" if c >= boyun else None)
                if durum:
                    ekle("İkili tepe", -1, durum, [(j1, p1, jm, boyun), (jm, boyun, j2, p2), (j1, boyun, i, boyun)],
                         boyun - (tepe - boyun), boyun)
    # OBO (omuz-baş-omuz)
    if len(H) >= 3:
        (a, ha, _), (b, hb, _), (d, hd, _) = H[-3:]
        if hb > ha * 1.015 and hb > hd * 1.015 and abs(ha - hd) / ha <= 0.02 and i - d <= 40 and d - a >= 12:
            n1j = a + int(np.argmin(Ll[a:b + 1]))
            n2j = b + int(np.argmin(Ll[b:d + 1]))
            n1, n2 = (n1j, float(Ll[n1j])), (n2j, float(Ll[n2j]))
            bi, bo = _dogru(n1, n2, i), _dogru(n1, n2, i - 1)
            durum = "kırıldı" if c < bi and cp >= bo else ("oluşuyor" if c >= bi else None)
            if durum:
                boy = hb - _dogru(n1, n2, b)
                ekle("OBO", -1, durum, [(a, ha, n1j, n1[1]), (n1j, n1[1], b, hb), (b, hb, n2j, n2[1]),
                                        (n2j, n2[1], d, hd), (n1j, n1[1], i, bi)], bi - boy, bi)
    # TOBO (ters omuz-baş-omuz)
    if len(L) >= 3:
        (a, la, _), (b, lb, _), (d, ld, _) = L[-3:]
        if lb < la * 0.985 and lb < ld * 0.985 and abs(la - ld) / la <= 0.02 and i - d <= 40 and d - a >= 12:
            n1j = a + int(np.argmax(Hh[a:b + 1]))
            n2j = b + int(np.argmax(Hh[b:d + 1]))
            n1, n2 = (n1j, float(Hh[n1j])), (n2j, float(Hh[n2j]))
            bi, bo = _dogru(n1, n2, i), _dogru(n1, n2, i - 1)
            durum = "kırıldı" if c > bi and cp <= bo else ("oluşuyor" if c <= bi else None)
            if durum:
                boy = _dogru(n1, n2, b) - lb
                ekle("TOBO", 1, durum, [(a, la, n1j, n1[1]), (n1j, n1[1], b, lb), (b, lb, n2j, n2[1]),
                                        (n2j, n2[1], d, ld), (n1j, n1[1], i, bi)], bi + boy, bi)
    # Üçgenler (son 3 ya da son 2 tepe/dip ile denenir; formasyon öncesi tepeler karışmasın)
    H80 = [p for p in H if p[0] >= i - 80]
    L80 = [p for p in L if p[0] >= i - 80]
    for nh_, nl_ in ((3, 3), (2, 3), (3, 2), (2, 2)):
        Hs, Ls = H80[-nh_:], L80[-nl_:]
        if not (len(Hs) >= 2 and len(Ls) >= 2 and Hs[-1][0] - Hs[0][0] >= 10 and Ls[-1][0] - Ls[0][0] >= 10):
            continue
        hx, hy = np.array([p[0] for p in Hs]), np.array([p[1] for p in Hs])
        lx, ly = np.array([p[0] for p in Ls]), np.array([p[1] for p in Ls])
        sh, bh = np.polyfit(hx, hy, 1)
        sl, bl = np.polyfit(lx, ly, 1)
        ort = (hy.mean() + ly.mean()) / 2
        nh, nl, F = sh / ort, sl / ort, 0.0004
        tip = None
        if abs(nh) < F and nl > F:
            tip = ("Yükselen üçgen", 1)
        elif abs(nl) < F and nh < -F:
            tip = ("Alçalan üçgen", -1)
        elif nh < -F and nl > F:
            tip = ("Simetrik üçgen", 0)
        if not tip:
            continue
        if tip:
            j0 = int(min(hx[0], lx[0]))
            ust = lambda j: sh * j + bh  # noqa: E731
            alt = lambda j: sl * j + bl  # noqa: E731
            gen0, gen = ust(j0) - alt(j0), ust(i) - alt(i)
            if 0 < gen < gen0 and alt(i - 1) * 0.997 <= cp <= ust(i - 1) * 1.003:
                if c > ust(i) * 1.002:
                    durum, yon, hedef, ref = "kırıldı", 1, c + gen0, ust(i)
                elif c < alt(i) * 0.998:
                    durum, yon, hedef, ref = "kırıldı", -1, c - gen0, alt(i)
                else:
                    durum, yon, hedef, ref = "oluşuyor", tip[1], None, ust(i) if tip[1] >= 0 else alt(i)
                ekle(tip[0], yon, durum, [(j0, ust(j0), i, ust(i)), (j0, alt(j0), i, alt(i))], hedef, ref)
                break
    # Bayrak (sert hareket + dar yatay bölge)
    esik = max(0.03, 4 * atr / c)
    for m in range(5, 16):
        s, p0 = i - m, i - m - 10
        if p0 < 1:
            break
        direk = C[s - 1] / C[p0] - 1
        ust_b, alt_b = float(Hh[s:i].max()), float(Ll[s:i].min())
        aralik = (ust_b - alt_b) / C[s - 1]
        if direk >= esik and aralik <= 0.5 * direk and alt_b > C[p0] + 0.5 * (C[s - 1] - C[p0]):
            durum = "kırıldı" if c > ust_b else ("oluşuyor" if c >= alt_b else None)
            if durum:
                ekle("Boğa bayrağı", 1, durum, [(p0, C[p0], s - 1, C[s - 1]), (s, ust_b, i, ust_b), (s, alt_b, i, alt_b)],
                     c + (C[s - 1] - C[p0]), ust_b)
            break
        if direk <= -esik and aralik <= 0.5 * -direk and ust_b < C[p0] + 0.5 * (C[s - 1] - C[p0]):
            durum = "kırıldı" if c < alt_b else ("oluşuyor" if c <= ust_b else None)
            if durum:
                ekle("Ayı bayrağı", -1, durum, [(p0, C[p0], s - 1, C[s - 1]), (s, ust_b, i, ust_b), (s, alt_b, i, alt_b)],
                     c - (C[p0] - C[s - 1]), alt_b)
            break
    return sonuc


# ---------- Puanlama ----------
def puanla(A, i, yon, olay, sebepler, ref, hedef_ozel, sev, piyasa) -> dict:
    c, atr = A["Close"][i], nanv(A["ATR"][i], A["Close"][i] * 0.01)
    puan, arti, eksi = olay, [], []
    yukari = yon > 0

    ema50, ema200 = A["EMA50"][i], A["EMA200"][i]
    if (c - ema50) * yon > 0:
        puan += 10; arti.append("Fiyat EMA50'nin " + ("üstünde" if yukari else "altında"))
    else:
        puan -= 5; eksi.append("Fiyat EMA50'nin " + ("altında" if yukari else "üstünde"))
    if (ema50 - ema200) * yon > 0:
        puan += 10; arti.append("Ana trend " + ("yukarı" if yukari else "aşağı"))
    else:
        puan -= 10; eksi.append("Ana trende karşı")

    mh, mh1 = nanv(A["MACDh"][i]), nanv(A["MACDh"][i - 1])
    if mh * yon > 0:
        puan += 10; arti.append("MACD onaylıyor")
    elif (mh - mh1) * yon > 0:
        puan += 5; arti.append("MACD dönüyor")
    else:
        puan -= 5; eksi.append("MACD ters yönde")

    r = nanv(A["RSI"][i], 50)
    if yukari:
        if r > 72:
            puan -= 15; eksi.append(f"RSI aşırı alımda ({r:.0f})")
        elif r < 35:
            puan += 5; arti.append(f"RSI dipten ({r:.0f})")
        elif 45 <= r <= 68:
            puan += 5; arti.append(f"RSI sağlıklı ({r:.0f})")
    else:
        if r < 28:
            puan -= 15; eksi.append(f"RSI aşırı satımda ({r:.0f})")
        elif r > 65:
            puan += 5; arti.append(f"RSI tepeden ({r:.0f})")
        elif 32 <= r <= 55:
            puan += 5; arti.append(f"RSI zayıf ({r:.0f})")

    hv = nanv(A["HacimOran"][i])
    if hv >= 2:
        puan += 15; arti.append(f"Güçlü hacim ({hv:.1f}x)")
    elif hv >= 1.5:
        puan += 10; arti.append(f"Yüksek hacim ({hv:.1f}x)")
    elif hv >= 1.2:
        puan += 5; arti.append(f"Hacim ortalama üstü ({hv:.1f}x)")
    elif hv < 1:
        puan -= 10; eksi.append(f"Hacim zayıf ({hv:.1f}x)")

    bw1, bwmin = A["BBw"][i - 1], A["BBwMin"][i - 1]
    if not np.isnan(bw1) and not np.isnan(bwmin) and bw1 <= bwmin * 1.1:
        if (yukari and c > A["BBu"][i]) or (not yukari and c < A["BBa"][i]):
            puan += 10; arti.append("Bollinger sıkışmasından çıkış")

    if piyasa * yon > 0:
        puan += 5; arti.append("BIST100 aynı yönde")
    elif piyasa * yon < 0:
        puan -= 10; eksi.append("BIST100 ters yönde")

    if yukari:
        stop = ref - 0.5 * atr
        if stop >= c:
            stop = c - 1.5 * atr
        ustler = [s for s in sev if s > c * 1.003]
        hedef = hedef_ozel or (min(ustler) if ustler else c + 2 * (c - stop))
        if hedef <= c:
            hedef = c + 2 * (c - stop)
    else:
        stop = ref + 0.5 * atr
        if stop <= c:
            stop = c + 1.5 * atr
        altlar = [s for s in sev if s < c * 0.997]
        hedef = hedef_ozel or (max(altlar) if altlar else c - 2 * (stop - c))
        if hedef >= c:
            hedef = c - 2 * (stop - c)
    risk, kazanc = abs(c - stop), abs(hedef - c)
    rk = kazanc / risk if risk > 0 else 0.0
    if rk >= 2:
        puan += 5; arti.append(f"Risk/kazanç iyi ({rk:.1f})")
    elif rk < 1:
        puan -= 10; eksi.append(f"Risk/kazanç düşük ({rk:.1f})")

    return dict(tur="AL" if yukari else "SAT", yon=yon, guven=int(max(0, min(100, puan))),
                sebepler=sebepler, arti=arti, eksi=eksi, fiyat=float(c), stop=float(stop),
                hedef=float(hedef), rk=rk, hacim_oran=hv)


def sinyal_bul(A, pv_tum, pv_j, i, piyasa):
    """i. mum kapanışında sinyal var mı? Sadece i'ye kadarki veri kullanılır."""
    pv = pv_tum[:bisect.bisect_right(pv_j, i - PIVOT_PENCERE - 1)]
    if len(pv) < 4:
        return None, []
    sev = seviyeler_bul(pv)
    c, o, h, l, cp = A["Close"][i], A["Open"][i], A["High"][i], A["Low"][i], A["Close"][i - 1]
    hv = nanv(A["HacimOran"][i])
    tol = SEVIYE_TOLERANS
    yesil, kirmizi = c > o, c < o

    olaylar = {}  # tür -> (yön, puan, metin, seviye, hedef)

    def olay_ekle(anahtar, yon, puan, metin, seviye, hedef=None):
        eski = olaylar.get(anahtar)
        if eski is None or abs(seviye - c) < abs(eski[3] - c):
            olaylar[anahtar] = (yon, puan, metin, seviye, hedef)

    for L_ in sev:
        if cp < L_ and c > L_ * (1 + tol / 2) and yesil and hv >= 1.0:
            olay_ekle("dk", 1, 25, f"Direnç kırıldı ({sayi(L_)})", L_)
        elif cp > L_ and c < L_ * (1 - tol / 2) and kirmizi and hv >= 1.0:
            olay_ekle("dsk", -1, 25, f"Destek kırıldı ({sayi(L_)})", L_)
        elif l <= L_ * (1 + tol) and c > L_ and cp >= L_ * (1 - tol) and yesil and hv >= 1.0:
            olay_ekle("dd", 1, 20, f"Destekten dönüş ({sayi(L_)})", L_)
        elif h >= L_ * (1 - tol) and c < L_ and cp <= L_ * (1 + tol) and kirmizi and hv >= 1.0:
            olay_ekle("rd", -1, 20, f"Dirençten dönüş ({sayi(L_)})", L_)

    formlar = formasyonlar(A, pv, i)
    for f in formlar:
        if f["durum"] == "kırıldı" and f["yon"] != 0:
            yon_adi = "yukarı" if f["yon"] > 0 else "aşağı"
            olay_ekle("f-" + f["ad"], f["yon"], 30, f"{f['ad']} {yon_adi} kırılımı", f["ref"], f["hedef"])

    en_iyi = None
    for yon in (1, -1):
        grup = sorted([v for v in olaylar.values() if v[0] == yon], key=lambda v: -v[1])
        if not grup:
            continue
        olay = min(sum(v[1] for v in grup), 45)
        hedef_ozel = next((v[4] for v in grup if v[4]), None)
        s = puanla(A, i, yon, olay, [v[2] for v in grup], grup[0][3], hedef_ozel, sev, piyasa)
        if en_iyi is None or s["guven"] > en_iyi["guven"]:
            en_iyi = s
    return en_iyi, formlar


def sonuc_hesapla(A, s, n):
    """Sinyalden sonra önce stop mu hedef mi geldi? (aynı mumda ikisi de varsa stop sayılır)"""
    i, yon, f = s["i"], s["yon"], s["fiyat"]
    for j in range(i + 1, min(i + 1 + TEST_UFKU, n)):
        if yon > 0:
            if A["Low"][j] <= s["stop"]:
                return "stop", s["stop"] / f - 1
            if A["High"][j] >= s["hedef"]:
                return "hedef", s["hedef"] / f - 1
        else:
            if A["High"][j] >= s["stop"]:
                return "stop", (f - s["stop"]) / f
            if A["Low"][j] <= s["hedef"]:
                return "hedef", (f - s["hedef"]) / f
    son = min(i + TEST_UFKU, n - 1)
    getiri = (A["Close"][son] / f - 1) * yon
    return ("süre doldu" if i + TEST_UFKU < n else "açık"), getiri


@st.cache_data(ttl=600, show_spinner=False, max_entries=60)
def analiz(hisse: str, ham: pd.DataFrame, piyasa: pd.Series, son_mum_kapali: bool) -> dict:
    df = gostergeler(ham)
    n = len(df) if son_mum_kapali else len(df) - 1  # seans içinde son mum henüz kapanmadı
    A = {k: df[k].values for k in df.columns}
    pv = pivot_bul(df.iloc[:n])
    pv_j = [p[0] for p in pv]
    py = (piyasa.reindex(df.index, method="ffill").fillna(0).values
          if len(piyasa) else np.zeros(len(df)))

    sinyaller = []
    for i in range(60, n):
        s, _ = sinyal_bul(A, pv, pv_j, i, py[i])
        if s:
            s["i"], s["zaman"] = i, df.index[i]
            s["sonuc"], s["getiri"] = sonuc_hesapla(A, s, n)
            sinyaller.append(s)

    _, formlar = sinyal_bul(A, pv, pv_j, n - 1, py[n - 1])
    sev = seviyeler_bul(pv)
    fiyat = float(df["Close"].iloc[-1])
    bugun = df[df.index.date == df.index[-1].date()]
    son = df.iloc[n - 1]
    return dict(
        hisse=hisse, df=df, n=n, sinyaller=sinyaller, formlar=formlar, seviyeler=sev,
        fiyat=fiyat,
        degisim=(fiyat / bugun["Open"].iloc[0] - 1) * 100 if len(bugun) else 0.0,
        destek=max([s for s in sev if s < fiyat], default=None),
        direnc=min([s for s in sev if s > fiyat], default=None),
        rsi=nanv(son["RSI"], 50), macd=nanv(son["MACDh"]), atr_yuzde=nanv(son["ATR"]) / fiyat * 100,
        trend=("Yukarı" if son["EMA50"] > son["EMA200"] else "Aşağı"),
    )


def filtrele(sinyaller: list[dict], min_guven: int) -> list[dict]:
    """Güven eşiğinin altındakileri ve aynı yönde art arda gelen tekrarları ele."""
    kalan, son = [], {1: -99, -1: -99}
    for s in sinyaller:
        if s["guven"] >= min_guven and s["i"] - son[s["yon"]] > 4:
            kalan.append(s)
            son[s["yon"]] = s["i"]
    return kalan


def istatistik(sinyaller: list[dict]) -> dict:
    hedef = sum(s["sonuc"] == "hedef" for s in sinyaller)
    stop = sum(s["sonuc"] == "stop" for s in sinyaller)
    biten = [s for s in sinyaller if s["sonuc"] != "açık"]
    return dict(toplam=len(sinyaller), hedef=hedef, stop=stop,
                isabet=hedef / (hedef + stop) * 100 if hedef + stop else None,
                ort=np.mean([s["getiri"] for s in biten]) * 100 if biten else None)


# ---------- Görünüm ----------
RENK = dict(zemin="#0b0f14", kart="#121821", cizgi="#1f2a37", yazi="#e6edf3",
            soluk="#8b98a5", yesil="#22c55e", kirmizi="#ef4444", vurgu="#f5a524", mor="#a78bfa")

STIL = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');
html, body, [class*="css"], .stApp {{ font-family: 'IBM Plex Sans', sans-serif; }}
.stApp {{ background: {RENK['zemin']}; color: {RENK['yazi']}; }}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
.block-container {{ padding: 1rem 0.9rem 3rem; max-width: 900px; }}

.ust {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:.4rem; }}
.logo {{ font-weight:700; font-size:1.35rem; letter-spacing:-.02em; }}
.logo span {{ color:{RENK['vurgu']}; }}
.seans {{ font-size:.75rem; padding:.25rem .6rem; border-radius:999px; border:1px solid {RENK['cizgi']}; }}
.seans.acik {{ color:{RENK['yesil']}; border-color:{RENK['yesil']}55; }}
.seans.kapali {{ color:{RENK['soluk']}; }}
.altbilgi {{ color:{RENK['soluk']}; font-size:.72rem; margin-bottom:1rem; }}

.ozet {{ display:grid; grid-template-columns:repeat(4,1fr); gap:.45rem; margin-bottom:1.1rem; }}
.ozet div {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:12px; padding:.55rem .6rem; }}
.ozet b {{ display:block; font-family:'JetBrains Mono',monospace; font-size:1.15rem; }}
.ozet small {{ color:{RENK['soluk']}; font-size:.62rem; text-transform:uppercase; letter-spacing:.05em; }}

.baslik {{ font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; color:{RENK['soluk']};
          margin:1.3rem 0 .5rem; font-weight:600; }}

.kart {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-left:4px solid;
        border-radius:12px; padding:.75rem .85rem; margin-bottom:.6rem; }}
.kart.al {{ border-left-color:{RENK['yesil']}; }}
.kart.sat {{ border-left-color:{RENK['kirmizi']}; }}
.kart-ust {{ display:flex; align-items:center; gap:.5rem; }}
.rozet {{ font-weight:700; font-size:.75rem; padding:.15rem .5rem; border-radius:6px; color:#0b0f14; }}
.rozet.al {{ background:{RENK['yesil']}; }}
.rozet.sat {{ background:{RENK['kirmizi']}; }}
.kod {{ font-weight:700; font-size:1.05rem; }}
.fiyat {{ margin-left:auto; font-family:'JetBrains Mono',monospace; font-size:1.05rem; }}
.guven {{ display:flex; align-items:center; gap:.5rem; margin:.5rem 0 .2rem; font-size:.75rem; color:{RENK['soluk']}; }}
.guven .bar {{ flex:1; height:6px; background:{RENK['zemin']}; border-radius:99px; overflow:hidden; }}
.guven .bar i {{ display:block; height:100%; border-radius:99px; }}
.guven b {{ font-family:'JetBrains Mono',monospace; color:{RENK['yazi']}; }}
.sebep {{ color:{RENK['yazi']}; font-size:.88rem; font-weight:600; margin:.35rem 0 .4rem; }}
.nedenler {{ display:flex; flex-wrap:wrap; gap:.3rem; margin-bottom:.5rem; }}
.nedenler span {{ font-size:.7rem; border-radius:6px; padding:.12rem .4rem; }}
.nedenler .p {{ color:{RENK['yesil']}; background:{RENK['yesil']}14; }}
.nedenler .n {{ color:{RENK['kirmizi']}; background:{RENK['kirmizi']}14; }}
.cipler {{ display:flex; flex-wrap:wrap; gap:.35rem; }}
.cipler span {{ font-size:.72rem; color:{RENK['soluk']}; background:{RENK['zemin']};
               border:1px solid {RENK['cizgi']}; border-radius:6px; padding:.15rem .45rem; }}
.cipler .stop {{ color:{RENK['kirmizi']}; }}
.cipler .hedef {{ color:{RENK['yesil']}; }}
.bos {{ background:{RENK['kart']}; border:1px dashed {RENK['cizgi']}; border-radius:12px;
       padding:.9rem; color:{RENK['soluk']}; font-size:.85rem; text-align:center; }}

.liste {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:12px; overflow:hidden; }}
.satir {{ display:grid; grid-template-columns:1.1fr 1fr .8fr 1.2fr; align-items:center; gap:.3rem;
         padding:.55rem .8rem; border-bottom:1px solid {RENK['cizgi']}; font-size:.85rem; }}
.satir:last-child {{ border-bottom:none; }}
.satir.bas {{ color:{RENK['soluk']}; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; }}
.satir .sag {{ text-align:right; font-family:'JetBrains Mono',monospace; }}
.satir.f {{ grid-template-columns:1fr 1.6fr 1fr; }}
.arti {{ color:{RENK['yesil']}; }} .eksi {{ color:{RENK['kirmizi']}; }}
.hap {{ justify-self:end; font-size:.68rem; padding:.12rem .45rem; border-radius:999px;
       border:1px solid {RENK['cizgi']}; color:{RENK['soluk']}; white-space:nowrap; }}
.hap.al {{ color:{RENK['yesil']}; border-color:{RENK['yesil']}66; }}
.hap.sat {{ color:{RENK['kirmizi']}; border-color:{RENK['kirmizi']}66; }}
.hap.yakin {{ color:{RENK['vurgu']}; border-color:{RENK['vurgu']}66; }}
.hap.form {{ color:{RENK['mor']}; border-color:{RENK['mor']}66; }}

.bilgi {{ display:grid; grid-template-columns:repeat(4,1fr); gap:.4rem; margin-top:.3rem; }}
.bilgi div {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:10px;
             padding:.45rem .55rem; font-size:.66rem; color:{RENK['soluk']}; }}
.bilgi b {{ display:block; color:{RENK['yazi']}; font-family:'JetBrains Mono',monospace; font-size:.88rem; }}

.test {{ background:{RENK['kart']}; border:1px solid {RENK['cizgi']}; border-radius:12px; padding:.75rem .85rem; }}
.test .sayilar {{ display:grid; grid-template-columns:repeat(4,1fr); gap:.4rem; text-align:center; margin-bottom:.5rem; }}
.test .sayilar b {{ display:block; font-family:'JetBrains Mono',monospace; font-size:1.05rem; }}
.test .sayilar small {{ color:{RENK['soluk']}; font-size:.62rem; text-transform:uppercase; }}
.test .gecmis {{ font-size:.75rem; color:{RENK['soluk']}; border-top:1px solid {RENK['cizgi']}; padding-top:.45rem; }}
.test .gecmis div {{ display:flex; justify-content:space-between; padding:.12rem 0; }}
.not {{ color:{RENK['soluk']}; font-size:.68rem; margin-top:.4rem; }}

.uyari {{ color:{RENK['soluk']}; font-size:.7rem; text-align:center; margin-top:1.5rem; }}
div[data-testid="stProgress"] > div > div > div {{ background:{RENK['vurgu']}; }}
</style>
"""


def guven_rengi(g):
    return RENK["yesil"] if g >= 70 else (RENK["vurgu"] if g >= 50 else RENK["soluk"])


def guven_adi(g):
    return "Güçlü" if g >= 70 else ("Orta" if g >= 50 else "Zayıf")


def sinyal_karti(a: dict, s: dict) -> str:
    tur = s["tur"].lower()
    kac = a["n"] - 1 - s["i"]
    ne_zaman = "son mumda" if kac == 0 else f"{kac} mum önce"
    nedenler = "".join(f'<span class="p">✓ {html.escape(x)}</span>' for x in s["arti"])
    nedenler += "".join(f'<span class="n">✗ {html.escape(x)}</span>' for x in s["eksi"])
    g = s["guven"]
    return f"""
<div class="kart {tur}">
  <div class="kart-ust"><span class="rozet {tur}">{s['tur']}</span>
    <span class="kod">{html.escape(a['hisse'])}</span>
    <span class="fiyat">{sayi(a['fiyat'])}</span></div>
  <div class="guven">Güven <div class="bar"><i style="width:{g}%;background:{guven_rengi(g)}"></i></div>
    <b>{g}</b> {guven_adi(g)}</div>
  <div class="sebep">{html.escape(' + '.join(s['sebepler']))}</div>
  <div class="nedenler">{nedenler}</div>
  <div class="cipler">
    <span>⏱ {s['zaman']:%H:%M} · {ne_zaman}</span>
    <span>Sinyal {sayi(s['fiyat'])}</span>
    <span class="stop">Stop {sayi(s['stop'])}</span>
    <span class="hedef">Hedef {sayi(s['hedef'])}</span>
    <span>R/K {s['rk']:.1f}</span>
  </div>
</div>"""


def form_listesi(kayitlar: list[tuple]) -> str:
    satirlar = []
    for hisse, f in kayitlar:
        yon = "al" if f["yon"] > 0 else ("sat" if f["yon"] < 0 else "form")
        beklenti = "yukarı" if f["yon"] > 0 else ("aşağı" if f["yon"] < 0 else "yön belirsiz")
        satirlar.append(
            f'<div class="satir f"><b>{html.escape(hisse)}</b><span>{f["ad"]}</span>'
            f'<span class="hap {yon}">{f["durum"]} · {beklenti}</span></div>')
    return '<div class="liste">' + "".join(satirlar) + "</div>"


def hisse_listesi(sonuclar: list[dict], guncel: dict) -> str:
    satirlar = ['<div class="satir bas"><span>Hisse</span><span class="sag">Fiyat</span>'
                '<span class="sag">Gün</span><span class="sag">Durum</span></div>']
    for a in sonuclar:
        s = guncel.get(a["hisse"])
        acik_form = [f for f in a["formlar"] if f["durum"] == "oluşuyor"]
        if s:
            hap = f'<span class="hap {s["tur"].lower()}">{s["tur"]} · {s["guven"]}</span>'
        elif acik_form:
            hap = f'<span class="hap form">{acik_form[0]["ad"]}</span>'
        elif a["direnc"] and (a["direnc"] - a["fiyat"]) / a["fiyat"] < 0.01:
            hap = '<span class="hap yakin">Dirence yakın</span>'
        elif a["destek"] and (a["fiyat"] - a["destek"]) / a["fiyat"] < 0.01:
            hap = '<span class="hap yakin">Desteğe yakın</span>'
        else:
            hap = f'<span class="hap">RSI {a["rsi"]:.0f}</span>'
        yon = "arti" if a["degisim"] >= 0 else "eksi"
        satirlar.append(
            f'<div class="satir"><b>{html.escape(a["hisse"])}</b>'
            f'<span class="sag">{sayi(a["fiyat"])}</span>'
            f'<span class="sag {yon}">{a["degisim"]:+.2f}%</span>{hap}</div>')
    return '<div class="liste">' + "".join(satirlar) + "</div>"


def test_kutusu(a: dict, sinyaller: list[dict]) -> str:
    ist = istatistik(sinyaller)
    isabet = f"%{ist['isabet']:.0f}" if ist["isabet"] is not None else "—"
    ort = f"{ist['ort']:+.2f}%" if ist["ort"] is not None else "—"
    son = []
    for s in sinyaller[-6:][::-1]:
        renk = "arti" if s["sonuc"] == "hedef" else ("eksi" if s["sonuc"] == "stop" else "")
        son.append(f'<div><span>{s["zaman"]:%d.%m %H:%M} · {s["tur"]} · güven {s["guven"]}</span>'
                   f'<span class="{renk}">{s["sonuc"]} {s["getiri"] * 100:+.1f}%</span></div>')
    gecmis = "".join(son) or "<div>Bu dönemde eşiği geçen sinyal yok</div>"
    return f"""
<div class="test">
  <div class="sayilar">
    <div><small>Sinyal</small><b>{ist['toplam']}</b></div>
    <div><small>Hedef</small><b class="arti">{ist['hedef']}</b></div>
    <div><small>Stop</small><b class="eksi">{ist['stop']}</b></div>
    <div><small>İsabet</small><b>{isabet}</b></div>
  </div>
  <div class="gecmis">{gecmis}</div>
  <div class="not">Sinyal başına ort. sonuç {ort}. Aynı kurallar bu hissenin geçmiş verisine uygulandı;
  her sinyalden sonra {TEST_UFKU} mum içinde önce hedef mi stop mu geldiğine bakıldı.
  Geçmişte tutması gelecekte tutacağını garanti etmez.</div>
</div>"""


# ---------- Grafik ----------
def grafik(a: dict, sinyaller: list[dict], mum_sayisi: int = 120) -> go.Figure:
    df = a["df"]
    bas = max(0, len(df) - mum_sayisi)
    w = df.iloc[bas:]
    etiket = list(df.index.strftime("%d.%m %H:%M"))
    x = etiket[bas:]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.62, 0.17, 0.21], vertical_spacing=0.02)
    fig.add_trace(go.Candlestick(
        x=x, open=w["Open"], high=w["High"], low=w["Low"], close=w["Close"],
        increasing=dict(line=dict(color=RENK["yesil"]), fillcolor=RENK["yesil"]),
        decreasing=dict(line=dict(color=RENK["kirmizi"]), fillcolor=RENK["kirmizi"]),
        name="Fiyat"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=w["EMA20"], line=dict(color="#38bdf8", width=1), name="EMA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=w["EMA50"], line=dict(color=RENK["vurgu"], width=1.3), name="EMA50"), row=1, col=1)

    alt, ust = w["Low"].min() * 0.99, w["High"].max() * 1.01
    for s in a["seviyeler"]:
        if alt <= s <= ust:
            c = RENK["yesil"] if s < a["fiyat"] else RENK["kirmizi"]
            fig.add_hline(y=s, line_dash="dot", line_width=1, line_color=c, opacity=0.7,
                          annotation_text=sayi(s), annotation_position="top left",
                          annotation_font=dict(color=c, size=10), row=1, col=1)

    # Formasyon çizgileri
    for f in a["formlar"]:
        xs, ys = [], []
        for j0, y0, j1, y1 in f["cizgiler"]:
            if j1 < bas:
                continue
            if j0 < bas:
                y0 = y0 + (y1 - y0) * (bas - j0) / (j1 - j0)
                j0 = bas
            xs += [etiket[int(j0)], etiket[int(j1)], None]
            ys += [y0, y1, None]
        if xs:
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=RENK["mor"], width=1.6),
                                     name=f["ad"], hoverinfo="name"), row=1, col=1)

    # Sinyal okları
    for s in sinyaller:
        if s["i"] < bas:
            continue
        al_mi = s["yon"] > 0
        c = RENK["yesil"] if al_mi else RENK["kirmizi"]
        y = df["Low"].iloc[s["i"]] * 0.994 if al_mi else df["High"].iloc[s["i"]] * 1.006
        fig.add_trace(go.Scatter(
            x=[etiket[s["i"]]], y=[y], mode="markers+text", text=[s["tur"]],
            textfont=dict(color=c, size=10), textposition="bottom center" if al_mi else "top center",
            marker=dict(symbol="triangle-up" if al_mi else "triangle-down", size=12, color=c),
            hovertext=f"{s['tur']} · güven {s['guven']} · {s['sonuc']}", hoverinfo="text"), row=1, col=1)

    renk = np.where(w["Close"] >= w["Open"], RENK["yesil"], RENK["kirmizi"])
    fig.add_trace(go.Bar(x=x, y=w["Volume"], marker_color=renk, opacity=0.45, name="Hacim"), row=2, col=1)
    mrenk = np.where(w["MACDh"] >= 0, RENK["yesil"], RENK["kirmizi"])
    fig.add_trace(go.Bar(x=x, y=w["MACDh"], marker_color=mrenk, opacity=0.5, name="MACD hist"), row=3, col=1)
    fig.add_trace(go.Scatter(x=x, y=w["MACD"], line=dict(color="#38bdf8", width=1), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=x, y=w["MACDs"], line=dict(color=RENK["vurgu"], width=1), name="Sinyal"), row=3, col=1)

    fig.update_layout(
        height=580, margin=dict(l=4, r=4, t=6, b=4), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=RENK["zemin"],
        font=dict(family="IBM Plex Sans, sans-serif", color=RENK["soluk"], size=10),
        xaxis_rangeslider_visible=False, dragmode="pan", hovermode="x unified")
    fig.update_xaxes(type="category", nticks=5, gridcolor=RENK["cizgi"], showline=False)
    fig.update_yaxes(gridcolor=RENK["cizgi"], side="right", zeroline=False)
    return fig


TV_PERIYOT = {"5m": "5", "15m": "15", "30m": "30", "1h": "60"}


def tradingview(hisse: str, periyot: str, yukseklik: int = 620):
    """TradingView gelişmiş grafiği: tüm göstergeler, çizim araçları, zaman dilimleri, tam ekran."""
    ayar = {
        "autosize": True,
        "symbol": f"BIST:{hisse}",
        "interval": TV_PERIYOT.get(periyot, "15"),
        "timezone": "Europe/Istanbul",
        "theme": "dark",
        "style": "1",
        "locale": "tr",
        "backgroundColor": RENK["zemin"],
        "gridColor": RENK["cizgi"],
        "withdateranges": True,
        "allow_symbol_change": True,
        "hide_side_toolbar": False,
        "details": False,
        "calendar": False,
        "save_image": True,
        "studies": ["Volume@tv-basicstudies", "RSI@tv-basicstudies", "MACD@tv-basicstudies",
                    "MAExp@tv-basicstudies", "BB@tv-basicstudies"],
        "support_host": "https://www.tradingview.com",
    }
    import json
    import streamlit.components.v1 as components
    components.html(f"""
<div class="tradingview-widget-container" style="height:{yukseklik}px;width:100%">
  <div class="tradingview-widget-container__widget" style="height:100%;width:100%"></div>
  <script type="text/javascript" async
    src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js">
  {json.dumps(ayar)}
  </script>
</div>""", height=yukseklik + 10)
    st.caption("Sol menüden çizim araçları, üstten zaman dilimi ve gösterge ekleyebilirsin. "
               "Sağ üstteki simgeyle tam ekran açılır.")


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
    min_guven = st.slider("Minimum güven puanı", 20, 90, VARSAYILAN_MIN_GUVEN, 5,
                          help="Bu puanın altındaki sinyaller gösterilmez ve geçmiş teste katılmaz.")
    if st.button("🔄 Verileri şimdi yenile", use_container_width=True):
        st.cache_data.clear()
hisseler = [h.strip().upper() for h in hisse_metni.split(",") if h.strip()]
periyot, gecmis = PERIYOTLAR[periyot_adi]


@st.fragment(run_every=YENILEME)
def panel():
    son_mum_kapali = not seans_acik_mi()
    sonuclar, hatalar = [], []
    ilerleme = st.progress(0.0, text="BIST100 yönü alınıyor...")
    piyasa = piyasa_yonu(periyot, gecmis)
    for n, h in enumerate(hisseler, 1):
        ilerleme.progress(n / max(len(hisseler), 1), text=f"{h} inceleniyor...")
        try:
            ham = veri_cek(f"{h}.IS", periyot, gecmis)
            if len(ham) < 80:
                hatalar.append(h)
            else:
                sonuclar.append(analiz(h, ham, piyasa, son_mum_kapali))
        except Exception:
            hatalar.append(h)
    ilerleme.empty()

    st.markdown(f'<div class="altbilgi">Güncellendi {dt.datetime.now(TZ):%H:%M} · '
                f'{periyot_adi} mumlar · {YENILEME.seconds // 60} dk\'da bir yenilenir</div>',
                unsafe_allow_html=True)
    if hatalar:
        st.warning("Veri alınamadı: " + ", ".join(hatalar))
    if not sonuclar:
        return

    filtreli = {a["hisse"]: filtrele(a["sinyaller"], min_guven) for a in sonuclar}
    guncel = {}
    for a in sonuclar:
        yeni = [s for s in filtreli[a["hisse"]] if s["i"] >= a["n"] - GERIYE_BAK_MUM]
        if yeni:
            guncel[a["hisse"]] = yeni[-1]
    kartlar = sorted(((a, guncel[a["hisse"]]) for a in sonuclar if a["hisse"] in guncel),
                     key=lambda t: (-t[1]["guven"], -t[1]["i"]))

    genel = istatistik([s for v in filtreli.values() for s in v])
    piyasa_son = piyasa.iloc[-1] if len(piyasa) else 0
    al_say = sum(s["yon"] > 0 for s in guncel.values())
    st.markdown(
        f'<div class="ozet"><div><small>AL</small><b class="arti">{al_say}</b></div>'
        f'<div><small>SAT</small><b class="eksi">{len(guncel) - al_say}</b></div>'
        f'<div><small>İsabet</small><b>{"%" + format(genel["isabet"], ".0f") if genel["isabet"] is not None else "—"}</b></div>'
        f'<div><small>BIST100</small><b class="{"arti" if piyasa_son > 0 else "eksi"}">'
        f'{"↑" if piyasa_son > 0 else ("↓" if piyasa_son < 0 else "—")}</b></div></div>',
        unsafe_allow_html=True)

    st.markdown('<div class="baslik">Sinyaller</div>', unsafe_allow_html=True)
    if kartlar:
        st.markdown("".join(sinyal_karti(a, s) for a, s in kartlar), unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bos">Son {GERIYE_BAK_MUM} mumda güven puanı {min_guven} üstü sinyal yok</div>',
                    unsafe_allow_html=True)

    izlenen = [(a["hisse"], f) for a in sonuclar for f in a["formlar"] if f["durum"] == "oluşuyor"]
    if izlenen:
        st.markdown('<div class="baslik">İzlemede · oluşan formasyonlar</div>', unsafe_allow_html=True)
        st.markdown(form_listesi(izlenen), unsafe_allow_html=True)

    st.markdown('<div class="baslik">Grafik</div>', unsafe_allow_html=True)
    isimler = [a["hisse"] for a in sonuclar]
    onceki = st.session_state.get("secili")
    if onceki not in isimler:
        onceki = kartlar[0][0]["hisse"] if kartlar else isimler[0]
    secim = st.pills("Hisse", isimler, default=onceki, label_visibility="collapsed") or onceki
    st.session_state["secili"] = secim
    a = next(x for x in sonuclar if x["hisse"] == secim)
    sekme1, sekme2 = st.tabs(["📈 Gelişmiş grafik", "🎯 Sinyal grafiği"])
    with sekme1:
        tradingview(secim, periyot)
    with sekme2:
        st.plotly_chart(grafik(a, filtreli[secim]), use_container_width=True, config={"displayModeBar": False})
    st.markdown(
        f'<div class="bilgi">'
        f'<div>Fiyat<b>{sayi(a["fiyat"])}</b></div>'
        f'<div>Gün<b class="{"arti" if a["degisim"] >= 0 else "eksi"}">{a["degisim"]:+.2f}%</b></div>'
        f'<div>RSI<b>{a["rsi"]:.0f}</b></div>'
        f'<div>MACD<b class="{"arti" if a["macd"] >= 0 else "eksi"}">{"Pozitif" if a["macd"] >= 0 else "Negatif"}</b></div>'
        f'<div>Trend<b class="{"arti" if a["trend"] == "Yukarı" else "eksi"}">{a["trend"]}</b></div>'
        f'<div>Oynaklık<b>%{a["atr_yuzde"]:.1f}</b></div>'
        f'<div>Destek<b class="arti">{sayi(a["destek"])}</b></div>'
        f'<div>Direnç<b class="eksi">{sayi(a["direnc"])}</b></div></div>',
        unsafe_allow_html=True)
    if a["formlar"]:
        st.markdown('<div class="baslik">Formasyonlar</div>', unsafe_allow_html=True)
        st.markdown(form_listesi([(a["hisse"], f) for f in a["formlar"]]), unsafe_allow_html=True)
    st.markdown(f'<div class="baslik">Geçmiş test · {secim}</div>', unsafe_allow_html=True)
    st.markdown(test_kutusu(a, filtreli[secim]), unsafe_allow_html=True)

    st.markdown('<div class="baslik">Tüm hisseler</div>', unsafe_allow_html=True)
    st.markdown(hisse_listesi(sonuclar, guncel), unsafe_allow_html=True)

    st.markdown('<div class="uyari">Veri yaklaşık 15 dk gecikmelidir · Yatırım tavsiyesi değildir</div>',
                unsafe_allow_html=True)


panel()
