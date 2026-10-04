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
import json
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

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


# ---------- Siteye gidecek veri ----------
def _ts(t) -> int:
    """Grafik ekseninde İstanbul saati görünsün diye UTC damgasına +3 saat eklenir."""
    return int(t.timestamp()) + 3 * 3600


def _r(x, n=4):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def sinyal_ozet(s: dict, df: pd.DataFrame, n: int) -> dict:
    return dict(
        t=_ts(df.index[s["i"]]), saat=f"{df.index[s['i']]:%d.%m %H:%M}", once=n - 1 - s["i"],
        tur=s["tur"], yon=s["yon"], guven=s["guven"], sebepler=s["sebepler"], arti=s["arti"], eksi=s["eksi"],
        fiyat=_r(s["fiyat"]), stop=_r(s["stop"]), hedef=_r(s["hedef"]), rk=_r(s["rk"], 2),
        sonuc=s["sonuc"], getiri=_r(s["getiri"] * 100, 2),
    )


def hisse_paketi(a: dict, sinyaller: list[dict], guncel) -> dict:
    df, n = a["df"], a["n"]
    bas = max(0, len(df) - 300)
    w = df.iloc[bas:]
    zaman = [_ts(t) for t in w.index]

    def seri(kol):
        return [[t, _r(v)] for t, v in zip(zaman, w[kol].values) if not np.isnan(v)]

    formlar = []
    for f in a["formlar"]:
        cizgiler = []
        for j0, y0, j1, y1 in f["cizgiler"]:
            j0, j1 = int(j0), int(j1)
            if j1 < bas or j1 >= len(df):
                continue
            if j0 < bas:
                y0 = y0 + (y1 - y0) * (bas - j0) / (j1 - j0)
                j0 = bas
            if j1 > j0:
                cizgiler.append([_ts(df.index[j0]), _r(y0), _ts(df.index[j1]), _r(y1)])
        formlar.append(dict(ad=f["ad"], yon=f["yon"], durum=f["durum"], ref=_r(f["ref"]),
                            hedef=_r(f["hedef"]), cizgiler=cizgiler))

    ist = istatistik(sinyaller)
    gunluk = df[df.index.date == df.index[-1].date()]
    bar_gun = max(len(gunluk), 1)
    return dict(
        hisse=a["hisse"], fiyat=_r(a["fiyat"]), degisim=_r(a["degisim"], 2),
        mumlar=[[t, _r(o), _r(h), _r(l), _r(c), _r(v, 0)] for t, o, h, l, c, v in
                zip(zaman, w["Open"].values, w["High"].values, w["Low"].values, w["Close"].values, w["Volume"].values)],
        ema20=seri("EMA20"), ema50=seri("EMA50"), ema200=seri("EMA200"),
        seviyeler=[_r(s) for s in a["seviyeler"]],
        destek=_r(a["destek"]), direnc=_r(a["direnc"]),
        formlar=formlar,
        sinyaller=[sinyal_ozet(s, df, n) for s in sinyaller if s["i"] >= bas],
        guncel=sinyal_ozet(guncel, df, n) if guncel else None,
        son_sinyal=sinyal_ozet(sinyaller[-1], df, n) if sinyaller else None,
        rsi=_r(a["rsi"], 1), macd=_r(a["macd"]), atr=_r(a["atr_yuzde"], 2), trend=a["trend"],
        ist=dict(toplam=ist["toplam"], hedef=ist["hedef"], stop=ist["stop"],
                 isabet=_r(ist["isabet"], 0), ort=_r(ist["ort"], 2)),
        bar_gun=bar_gun,
    )


# ---------- Arayüz (HTML + JS) ----------
ARAYUZ = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#0b0d12;--s1:#14171f;--s2:#1b1f29;--s3:#252a36;--tx:#f3f5f8;--mu:#8b93a3;--mu2:#5d6575;
--up:#16c784;--dn:#ea3943;--ac:#6c8cff;--wa:#f5a524;--fo:#b48cff;--r:16px}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--tx);font-family:Inter,system-ui,sans-serif}
body{overflow:hidden}
.num{font-variant-numeric:tabular-nums}
#app{display:flex;flex-direction:column;height:100%}
header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px 10px}
.logo{font-weight:800;font-size:20px;letter-spacing:-.03em}.logo b{color:var(--ac)}
.piyasa{text-align:right;font-size:12px;color:var(--mu)}.piyasa div{font-weight:700;color:var(--tx);font-size:14px}
.seans{display:inline-flex;align-items:center;gap:5px;font-size:11px;color:var(--mu);margin-top:2px}
.seans i{width:6px;height:6px;border-radius:50%;background:var(--mu2)}.seans.acik i{background:var(--up);box-shadow:0 0 8px var(--up)}
main{flex:1;overflow-y:auto;padding:4px 16px 90px;-webkit-overflow-scrolling:touch}
h2{font-size:22px;font-weight:800;letter-spacing:-.02em;margin:8px 0 12px}
.alt-baslik{font-size:12px;color:var(--mu);font-weight:600;text-transform:uppercase;letter-spacing:.06em;margin:20px 0 10px}
nav.alt{position:fixed;left:0;right:0;bottom:0;display:flex;background:rgba(15,17,23,.92);backdrop-filter:blur(14px);
border-top:1px solid var(--s3);padding:8px 8px calc(8px + env(safe-area-inset-bottom))}
nav.alt button{flex:1;background:none;border:0;color:var(--mu);font:600 11px Inter;display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px 0;position:relative}
nav.alt button svg{width:22px;height:22px}
nav.alt button.on{color:var(--tx)}
nav.alt .rozet{position:absolute;top:2px;left:calc(50% + 6px);background:var(--dn);color:#fff;font-size:10px;border-radius:9px;padding:1px 5px}
.ozet{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:6px}
.ozet div{background:var(--s1);border-radius:14px;padding:12px}
.ozet small{display:block;color:var(--mu);font-size:11px;font-weight:600;margin-bottom:4px}
.ozet b{font-size:22px;font-weight:800}
.up{color:var(--up)}.dn{color:var(--dn)}
.kart{background:var(--s1);border-radius:var(--r);padding:14px;margin-bottom:10px;cursor:pointer;transition:transform .1s}
.kart:active{transform:scale(.985)}
.satir1{display:flex;align-items:center;gap:12px}
.av{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;font-weight:800;font-size:13px;flex:none;color:#fff}
.ad{flex:1;min-width:0}.ad b{display:block;font-size:16px;font-weight:700}.ad small{color:var(--mu);font-size:12px}
.sag{text-align:right}.sag b{display:block;font-size:16px;font-weight:700}
.pill{display:inline-block;font-size:12px;font-weight:700;border-radius:8px;padding:3px 8px;margin-top:3px}
.pill.up{background:rgba(22,199,132,.14)}.pill.dn{background:rgba(234,57,67,.14)}
.tur{font-weight:800;font-size:13px;border-radius:8px;padding:5px 10px;color:#fff}
.tur.al{background:var(--up)}.tur.sat{background:var(--dn)}
.guven{display:flex;align-items:center;gap:10px;margin:12px 0 8px;font-size:12px;color:var(--mu)}
.bar{flex:1;height:6px;background:var(--s3);border-radius:9px;overflow:hidden}.bar i{display:block;height:100%;border-radius:9px}
.guven b{color:var(--tx);font-size:14px}
.sebep{font-size:14px;font-weight:600;margin-bottom:10px}
.ucl{display:grid;grid-template-columns:repeat(3,1fr);background:var(--s2);border-radius:12px;padding:10px 4px;text-align:center}
.ucl small{display:block;color:var(--mu);font-size:11px;margin-bottom:2px}.ucl b{font-size:14px}
.bos{background:var(--s1);border-radius:var(--r);padding:28px 18px;text-align:center;color:var(--mu);font-size:14px;line-height:1.5}
.bos b{display:block;color:var(--tx);font-size:16px;margin-bottom:4px}
.liste{background:var(--s1);border-radius:var(--r);overflow:hidden}
.liste .satir1{padding:12px 14px;border-bottom:1px solid var(--s2);cursor:pointer}
.liste .satir1:last-child{border-bottom:0}.liste .satir1:active{background:var(--s2)}
.chips{display:flex;gap:8px;overflow-x:auto;margin-bottom:12px;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}
.chip{flex:none;background:var(--s1);color:var(--mu);border:0;border-radius:20px;padding:8px 14px;font:600 13px Inter}
.chip.on{background:var(--tx);color:var(--bg)}
.etiket{font-size:11px;font-weight:600;border-radius:6px;padding:2px 6px;margin-left:6px;vertical-align:2px}
.etiket.al{color:var(--up);background:rgba(22,199,132,.12)}.etiket.sat{color:var(--dn);background:rgba(234,57,67,.12)}
.etiket.fo{color:var(--fo);background:rgba(180,140,255,.12)}
/* detay */
#detay{position:fixed;inset:0;background:var(--bg);display:flex;flex-direction:column;transform:translateX(100%);transition:transform .25s ease;z-index:10}
#detay.ac{transform:none}
.dust{display:flex;align-items:center;gap:10px;padding:12px 12px 4px}
.geri{background:var(--s1);border:0;color:var(--tx);width:38px;height:38px;border-radius:50%;font-size:20px;display:grid;place-items:center}
.dust .ad b{font-size:18px}
.tv{margin-left:auto;background:var(--s1);color:var(--mu);border-radius:20px;padding:8px 12px;font-size:12px;font-weight:600;text-decoration:none}
#dicerik{flex:1;overflow-y:auto;padding:0 0 30px}
.fiyatbas{padding:8px 16px 4px}.fiyatbas .buyuk{font-size:34px;font-weight:800;letter-spacing:-.03em}
.fiyatbas .pill{font-size:13px;margin-left:8px;vertical-align:6px}
.legend{padding:0 16px;height:18px;font-size:11px;color:var(--mu)}
#grafik{height:360px;margin:4px 0 0}
.gsec{display:flex;gap:6px;padding:8px 16px;overflow-x:auto;scrollbar-width:none}.gsec::-webkit-scrollbar{display:none}
.gsec .chip{padding:6px 11px;font-size:12px}
.gsec .ayr{width:1px;background:var(--s3);flex:none;margin:4px 2px}
.dpad{padding:0 16px}
.sekmeler{display:flex;background:var(--s1);border-radius:12px;padding:4px;margin:14px 0 12px}
.sekmeler button{flex:1;border:0;background:none;color:var(--mu);font:600 13px Inter;padding:9px 0;border-radius:9px}
.sekmeler button.on{background:var(--s3);color:var(--tx)}
.neden{display:flex;flex-direction:column;gap:6px;margin:10px 0 12px}
.neden div{font-size:13px;display:flex;gap:8px;align-items:flex-start}
.neden .p::before{content:"✓";color:var(--up);font-weight:800}.neden .n::before{content:"✕";color:var(--dn);font-weight:800}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grid div{background:var(--s1);border-radius:12px;padding:12px}
.grid small{display:block;color:var(--mu);font-size:11px;margin-bottom:3px}.grid b{font-size:16px}
.sayilar{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;text-align:center;margin-bottom:12px}
.sayilar div{background:var(--s1);border-radius:12px;padding:10px 4px}.sayilar small{display:block;color:var(--mu);font-size:10px;margin-bottom:3px;font-weight:600}
.sayilar b{font-size:18px}
.gecmis .satir1{font-size:13px}
.not{color:var(--mu2);font-size:11px;line-height:1.5;margin-top:12px}
.uyari{color:var(--mu2);font-size:11px;text-align:center;margin:22px 0 4px}
</style></head><body>
<div id="app">
  <header>
    <div><div class="logo">BIST<b>·</b>Sinyal</div><div class="seans" id="seans"><i></i><span></span></div></div>
    <div class="piyasa" id="piyasa"></div>
  </header>
  <main id="ekran"></main>
  <nav class="alt">
    <button data-e="sinyal"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/></svg>Sinyaller<span class="rozet" id="rz" hidden></span></button>
    <button data-e="hisse"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h16"/></svg>Hisseler</button>
    <button data-e="izle"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>İzleme</button>
  </nav>
</div>
<div id="detay">
  <div class="dust"><button class="geri" id="geri">‹</button><div class="ad" id="dad"></div><a class="tv" id="tvlink" target="_blank" rel="noopener">TradingView ↗</a></div>
  <div id="dicerik">
    <div class="fiyatbas" id="dfiyat"></div>
    <div class="legend num" id="legend"></div>
    <div id="grafik"></div>
    <div class="gsec" id="gsec"></div>
    <div class="dpad">
      <div class="sekmeler" id="sekmeler"><button data-s="sinyal">Sinyal</button><button data-s="analiz">Analiz</button><button data-s="gecmis">Geçmiş</button></div>
      <div id="sekme"></div>
      <div class="uyari">Veri yaklaşık 15 dk gecikmeli · Yatırım tavsiyesi değildir</div>
    </div>
  </div>
</div>
<script type="application/json" id="veri">__VERI__</script>
<script>
const V=JSON.parse(document.getElementById('veri').textContent);
const H=Object.fromEntries(V.hisseler.map(h=>[h.hisse,h]));
const $=s=>document.querySelector(s);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tl=(x,d=2)=>x==null?'—':Number(x).toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d});
const yuzde=x=>x==null?'—':(x>=0?'+':'')+tl(x)+'%';
const sinif=x=>x>=0?'up':'dn';
const durum={get(k,d){try{return localStorage.getItem('bs_'+k)??d}catch(e){return d}},set(k,v){try{localStorage.setItem('bs_'+k,v)}catch(e){}}};
function renk(ad){let h=0;for(const c of ad)h=(h*31+c.charCodeAt(0))%360;return `hsl(${h} 55% 42%)`}
function av(ad){return `<div class="av" style="background:${renk(ad)}">${esc(ad.slice(0,2))}</div>`}
function guvenRenk(g){return g>=70?'var(--up)':g>=50?'var(--wa)':'var(--mu)'}
function guvenAd(g){return g>=70?'Güçlü':g>=50?'Orta':'Zayıf'}
function ne(s){return s.once===0?'son mumda':s.once+' mum önce'}

// üst bilgi
$('#seans').className='seans'+(V.seans?' acik':'');$('#seans span').textContent=(V.seans?'Seans açık':'Seans kapalı')+' · '+V.guncelleme;
$('#piyasa').innerHTML=V.bist100?`BIST 100<div class="num">${tl(V.bist100.fiyat,0)} <span class="${sinif(V.bist100.degisim)}">${yuzde(V.bist100.degisim)}</span></div>`:'';

const guncel=V.hisseler.filter(h=>h.guncel).sort((a,b)=>b.guncel.guven-a.guncel.guven||a.guncel.once-b.guncel.once);
if(guncel.length){$('#rz').hidden=false;$('#rz').textContent=guncel.length}

function sinyalKarti(h){const s=h.guncel,t=s.tur.toLowerCase();return `
<div class="kart" data-h="${h.hisse}">
 <div class="satir1">${av(h.hisse)}<div class="ad"><b>${h.hisse}</b><small>${s.saat} · ${ne(s)}</small></div>
  <div class="sag"><span class="tur ${t}">${s.tur}</span></div></div>
 <div class="guven">Güven<div class="bar"><i style="width:${s.guven}%;background:${guvenRenk(s.guven)}"></i></div><b>${s.guven}</b>${guvenAd(s.guven)}</div>
 <div class="sebep">${esc(s.sebepler.join(' + '))}</div>
 <div class="ucl num"><div><small>Fiyat</small><b>${tl(h.fiyat)}</b></div><div><small>Stop</small><b class="dn">${tl(s.stop)}</b></div><div><small>Hedef</small><b class="up">${tl(s.hedef)}</b></div></div>
</div>`}

function ekranSinyal(){
  const al=guncel.filter(h=>h.guncel.yon>0).length;
  let x=`<h2>Sinyaller</h2><div class="ozet num"><div><small>AL</small><b class="up">${al}</b></div><div><small>SAT</small><b class="dn">${guncel.length-al}</b></div>
   <div><small>Geçmiş isabet</small><b>${V.isabet==null?'—':'%'+V.isabet}</b></div></div>`;
  x+=guncel.length?`<div class="alt-baslik">Güncel · güven ${V.min_guven}+</div>`+guncel.map(sinyalKarti).join('')
   :`<div class="alt-baslik">Güncel</div><div class="bos"><b>Şu an sinyal yok</b>Son ${V.geriye} mumda güven puanı ${V.min_guven} üstü AL/SAT oluşmadı. Formasyonları İzleme sekmesinden takip edebilirsin.</div>`;
  return x}

let filtre=durum.get('filtre','tumu');
function hisseSatiri(h){
  let alt='';
  if(h.guncel)alt=`<span class="etiket ${h.guncel.tur.toLowerCase()}">${h.guncel.tur} ${h.guncel.guven}</span>`;
  else{const f=h.formlar.find(f=>f.durum==='oluşuyor');if(f)alt=`<span class="etiket fo">${esc(f.ad)}</span>`}
  return `<div class="satir1" data-h="${h.hisse}">${av(h.hisse)}<div class="ad"><b>${h.hisse}${alt}</b><small>RSI ${tl(h.rsi,0)} · Trend ${h.trend.toLowerCase()}</small></div>
   <div class="sag num"><b>${tl(h.fiyat)}</b><span class="pill ${sinif(h.degisim)}">${yuzde(h.degisim)}</span></div></div>`}
function ekranHisse(){
  let l=[...V.hisseler];
  if(filtre==='sinyal')l=l.filter(h=>h.guncel);
  if(filtre==='yukselen')l.sort((a,b)=>b.degisim-a.degisim);
  if(filtre==='dusen')l.sort((a,b)=>a.degisim-b.degisim);
  const c=(k,a)=>`<button class="chip${filtre===k?' on':''}" data-f="${k}">${a}</button>`;
  return `<h2>Hisseler</h2><div class="chips">${c('tumu','Tümü')}${c('sinyal','Sinyal verenler')}${c('yukselen','Yükselenler')}${c('dusen','Düşenler')}</div>`+
   (l.length?`<div class="liste">${l.map(hisseSatiri).join('')}</div>`:`<div class="bos">Bu filtrede hisse yok</div>`)}

function ekranIzle(){
  const k=[];V.hisseler.forEach(h=>h.formlar.filter(f=>f.durum==='oluşuyor').forEach(f=>k.push([h,f])));
  let x=`<h2>İzleme</h2><div class="not" style="margin:-4px 0 12px">Oluşmakta olan formasyonlar. Kırılım olursa güven puanıyla birlikte Sinyaller'e düşer.</div>`;
  if(!k.length)return x+`<div class="bos"><b>Oluşan formasyon yok</b>Takip listendeki hisselerde şu an tamamlanmamış formasyon görünmüyor.</div>`;
  return x+k.map(([h,f])=>{const yon=f.yon>0?'Yukarı kırılım beklenir':f.yon<0?'Aşağı kırılım beklenir':'Yön belirsiz';
   const ref=f.ref?` · kritik seviye ${tl(f.ref)}`:'';
   return `<div class="kart" data-h="${h.hisse}"><div class="satir1">${av(h.hisse)}<div class="ad"><b>${h.hisse}<span class="etiket fo">${esc(f.ad)}</span></b>
    <small>${yon}${ref}</small></div><div class="sag num"><b>${tl(h.fiyat)}</b><span class="pill ${sinif(h.degisim)}">${yuzde(h.degisim)}</span></div></div></div>`}).join('')}

let ekran=durum.get('ekran','sinyal');
function ciz(){
  document.querySelectorAll('nav.alt button').forEach(b=>b.classList.toggle('on',b.dataset.e===ekran));
  $('#ekran').innerHTML=(ekran==='hisse'?ekranHisse():ekran==='izle'?ekranIzle():ekranSinyal())+`<div class="uyari">Veri yaklaşık 15 dk gecikmeli · Yatırım tavsiyesi değildir</div>`;
}
document.querySelector('nav.alt').onclick=e=>{const b=e.target.closest('button');if(!b)return;ekran=b.dataset.e;durum.set('ekran',ekran);ciz();$('#ekran').scrollTop=0};
$('#ekran').onclick=e=>{const f=e.target.closest('[data-f]');if(f){filtre=f.dataset.f;durum.set('filtre',filtre);ciz();return}
  const h=e.target.closest('[data-h]');if(h)detayAc(h.dataset.h)};

// ---------- detay ----------
let chart=null,ro=null,secili=null,sekme=durum.get('sekme','sinyal');
const gor=JSON.parse(durum.get('gor','{"ema":true,"sev":true,"form":true,"sin":true}'));
function detayAc(ad){
  const h=H[ad];if(!h)return;secili=ad;durum.set('detay',ad);
  $('#dad').innerHTML=`<b>${ad}</b><small style="color:var(--mu);font-size:12px">${V.periyot} grafik</small>`;
  $('#tvlink').href='https://tr.tradingview.com/chart/?symbol=BIST%3A'+encodeURIComponent(ad);
  $('#dfiyat').innerHTML=`<span class="buyuk num">${tl(h.fiyat)}</span><span class="pill ${sinif(h.degisim)} num">${yuzde(h.degisim)}</span>`;
  $('#detay').classList.add('ac');$('#dicerik').scrollTop=0;
  setTimeout(()=>grafikKur(h),30);sekmeCiz();
}
$('#geri').onclick=()=>{$('#detay').classList.remove('ac');durum.set('detay','');if(chart){chart.remove();chart=null}};

function grafikKur(h){
  if(chart){chart.remove();chart=null}
  const el=$('#grafik');
  if(!window.LightweightCharts){el.innerHTML='<div class="bos" style="margin:0 16px">Grafik kütüphanesi yüklenemedi. Sayfayı yenile.</div>';return}
  chart=LightweightCharts.createChart(el,{width:el.clientWidth,height:360,
    layout:{background:{type:'solid',color:'transparent'},textColor:'#8b93a3',fontFamily:'Inter',fontSize:11},
    grid:{vertLines:{color:'rgba(255,255,255,.04)'},horzLines:{color:'rgba(255,255,255,.04)'}},
    rightPriceScale:{borderVisible:false,scaleMargins:{top:.08,bottom:.24}},
    timeScale:{borderVisible:false,timeVisible:true,secondsVisible:false,rightOffset:4,barSpacing:7},
    crosshair:{mode:0,vertLine:{color:'#5d6575',labelBackgroundColor:'#252a36'},horzLine:{color:'#5d6575',labelBackgroundColor:'#252a36'}},
    localization:{locale:'tr-TR',priceFormatter:p=>tl(p)}});
  const mum=chart.addCandlestickSeries({upColor:'#16c784',downColor:'#ea3943',borderVisible:false,wickUpColor:'#16c784',wickDownColor:'#ea3943',priceLineColor:'#6c8cff'});
  mum.setData(h.mumlar.map(m=>({time:m[0],open:m[1],high:m[2],low:m[3],close:m[4]})));
  const hacim=chart.addHistogramSeries({priceScaleId:'h',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false});
  chart.priceScale('h').applyOptions({scaleMargins:{top:.82,bottom:0}});
  hacim.setData(h.mumlar.map(m=>({time:m[0],value:m[5],color:m[4]>=m[1]?'rgba(22,199,132,.35)':'rgba(234,57,67,.35)'})));
  const cizgi=(renk,w=1)=>chart.addLineSeries({color:renk,lineWidth:w,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
  const emalar=[[h.ema20,'#38bdf8'],[h.ema50,'#f5a524'],[h.ema200,'#b48cff']].map(([d,r])=>{const s=cizgi(r);s.setData(d.map(p=>({time:p[0],value:p[1]})));return s});
  const formSeri=[];h.formlar.forEach(f=>f.cizgiler.forEach(c=>{const s=cizgi(f.yon<0?'#ff7a85':'#b48cff',2);s.setData([{time:c[0],value:c[1]},{time:c[2],value:c[3]}]);formSeri.push(s)}));
  let sevCizgi=[],slCizgi=[];
  const lo=Math.min(...h.mumlar.map(m=>m[3]))*.97,hi=Math.max(...h.mumlar.map(m=>m[2]))*1.03;
  function uygula(){
    emalar.forEach(s=>s.applyOptions({visible:gor.ema}));formSeri.forEach(s=>s.applyOptions({visible:gor.form}));
    sevCizgi.forEach(p=>mum.removePriceLine(p));sevCizgi=[];slCizgi.forEach(p=>mum.removePriceLine(p));slCizgi=[];
    if(gor.sev)h.seviyeler.filter(s=>s>lo&&s<hi).forEach(s=>sevCizgi.push(mum.createPriceLine({price:s,color:s<h.fiyat?'rgba(22,199,132,.55)':'rgba(234,57,67,.55)',lineWidth:1,lineStyle:2,axisLabelVisible:false})));
    const g=h.guncel;
    if(gor.sin&&g){slCizgi.push(mum.createPriceLine({price:g.stop,color:'#ea3943',lineWidth:1,lineStyle:0,title:'Stop'}));
      slCizgi.push(mum.createPriceLine({price:g.hedef,color:'#16c784',lineWidth:1,lineStyle:0,title:'Hedef'}))}
    mum.setMarkers(gor.sin?h.sinyaller.map(s=>({time:s.t,position:s.yon>0?'belowBar':'aboveBar',color:s.yon>0?'#16c784':'#ea3943',
      shape:s.yon>0?'arrowUp':'arrowDown',text:s.tur+' '+s.guven})):[]);
  }
  uygula();
  const n=h.mumlar.length,aralik={'1G':h.bar_gun,'3G':h.bar_gun*3,'1H':h.bar_gun*5,'Tümü':n};
  let sec=durum.get('aralik','3G');
  function aralikUygula(){const k=Math.min(aralik[sec]||n,n);chart.timeScale().setVisibleLogicalRange({from:n-k-.5,to:n+3})}
  aralikUygula();
  const gs=$('#gsec');
  const t=(k,a,on)=>`<button class="chip${on?' on':''}" data-k="${k}">${a}</button>`;
  function gsecCiz(){gs.innerHTML=Object.keys(aralik).map(k=>t('a:'+k,k,sec===k)).join('')+'<span class="ayr"></span>'+
    t('g:sin','AL/SAT',gor.sin)+t('g:sev','Seviyeler',gor.sev)+t('g:form','Formasyon',gor.form)+t('g:ema','EMA',gor.ema)}
  gsecCiz();
  gs.onclick=e=>{const b=e.target.closest('[data-k]');if(!b)return;const[tip,k]=b.dataset.k.split(':');
    if(tip==='a'){sec=k;durum.set('aralik',k);aralikUygula()}else{gor[k]=!gor[k];durum.set('gor',JSON.stringify(gor));uygula()}gsecCiz()};
  const son=h.mumlar[n-1];
  const lg=m=>m?`A <b>${tl(m[1])}</b> Y <b>${tl(m[2])}</b> D <b>${tl(m[3])}</b> K <b class="${m[4]>=m[1]?'up':'dn'}">${tl(m[4])}</b> · Hacim ${tl(m[5],0)}`:'';
  const idx=Object.fromEntries(h.mumlar.map(m=>[m[0],m]));
  $('#legend').innerHTML=lg(son);
  chart.subscribeCrosshairMove(p=>{$('#legend').innerHTML=lg(p&&p.time?idx[p.time]:son)});
  if(ro)ro.disconnect();ro=new ResizeObserver(()=>chart&&chart.applyOptions({width:el.clientWidth}));ro.observe(el);
}

function sekmeCiz(){
  document.querySelectorAll('#sekmeler button').forEach(b=>b.classList.toggle('on',b.dataset.s===sekme));
  const h=H[secili];let x='';
  if(sekme==='sinyal'){
    const s=h.guncel||null;
    if(s){x=`<div class="kart" style="cursor:default"><div class="satir1"><span class="tur ${s.tur.toLowerCase()}">${s.tur}</span>
      <div class="ad"><small>${s.saat} · ${ne(s)} · sinyal fiyatı ${tl(s.fiyat)}</small></div></div>
      <div class="guven">Güven<div class="bar"><i style="width:${s.guven}%;background:${guvenRenk(s.guven)}"></i></div><b>${s.guven}</b>${guvenAd(s.guven)}</div>
      <div class="sebep">${esc(s.sebepler.join(' + '))}</div>
      <div class="neden">${s.arti.map(a=>`<div class="p">${esc(a)}</div>`).join('')}${s.eksi.map(a=>`<div class="n">${esc(a)}</div>`).join('')}</div>
      <div class="ucl num"><div><small>Stop</small><b class="dn">${tl(s.stop)}</b></div><div><small>Hedef</small><b class="up">${tl(s.hedef)}</b></div><div><small>Risk/Kazanç</small><b>${tl(s.rk,1)}</b></div></div></div>`}
    else{const l=h.son_sinyal;x=`<div class="bos"><b>Şu an sinyal yok</b>${l?`Son sinyal: ${l.saat} · ${l.tur} (güven ${l.guven}) → ${esc(l.sonuc)}`:'Bu dönemde güven eşiğini geçen sinyal olmadı.'}</div>`}
  }else if(sekme==='analiz'){
    x=`<div class="grid num">
      <div><small>RSI</small><b class="${h.rsi>70?'dn':h.rsi<30?'up':''}">${tl(h.rsi,0)}</b></div>
      <div><small>MACD</small><b class="${sinif(h.macd)}">${h.macd>=0?'Pozitif':'Negatif'}</b></div>
      <div><small>Ana trend</small><b class="${h.trend==='Yukarı'?'up':'dn'}">${h.trend}</b></div>
      <div><small>Oynaklık (ATR)</small><b>%${tl(h.atr)}</b></div>
      <div><small>Yakın destek</small><b class="up">${tl(h.destek)}</b></div>
      <div><small>Yakın direnç</small><b class="dn">${tl(h.direnc)}</b></div></div>`;
    x+=`<div class="alt-baslik">Formasyonlar</div>`+(h.formlar.length?`<div class="liste">${h.formlar.map(f=>`<div class="satir1" style="cursor:default">
      <div class="ad"><b style="font-size:14px">${esc(f.ad)}</b><small>${f.yon>0?'Yukarı beklenti':f.yon<0?'Aşağı beklenti':'Yön belirsiz'}${f.ref?' · kritik '+tl(f.ref):''}${f.hedef?' · hedef '+tl(f.hedef):''}</small></div>
      <span class="etiket ${f.durum==='kırıldı'?(f.yon>0?'al':'sat'):'fo'}">${f.durum}</span></div>`).join('')}</div>`:`<div class="bos">Şu an formasyon yok</div>`);
  }else{
    const i=h.ist;
    x=`<div class="sayilar num"><div><small>SİNYAL</small><b>${i.toplam}</b></div><div><small>HEDEF</small><b class="up">${i.hedef}</b></div>
      <div><small>STOP</small><b class="dn">${i.stop}</b></div><div><small>İSABET</small><b>${i.isabet==null?'—':'%'+i.isabet}</b></div></div>`;
    const l=[...h.sinyaller].reverse().slice(0,12);
    x+=l.length?`<div class="liste gecmis">${l.map(s=>`<div class="satir1" style="cursor:default"><span class="etiket ${s.tur.toLowerCase()}" style="margin:0">${s.tur}</span>
      <div class="ad"><small style="color:var(--tx)">${s.saat}</small><small> · güven ${s.guven}</small></div>
      <div class="sag num"><b style="font-size:13px" class="${s.sonuc==='hedef'?'up':s.sonuc==='stop'?'dn':''}">${esc(s.sonuc)}</b><small style="color:var(--mu)">${yuzde(s.getiri)}</small></div></div>`).join('')}</div>`
      :`<div class="bos">Bu dönemde sinyal yok</div>`;
    x+=`<div class="not">Ortalama sonuç ${i.ort==null?'—':yuzde(i.ort)}. Aynı kurallar bu hissenin geçmiş verisine uygulandı; her sinyalden sonra ${V.ufuk} mum içinde önce hedefe mi stopa mı gittiğine bakıldı. Geçmişte tutması gelecekte tutacağını garanti etmez.</div>`;
  }
  $('#sekme').innerHTML=x;
}
$('#sekmeler').onclick=e=>{const b=e.target.closest('button');if(!b)return;sekme=b.dataset.s;durum.set('sekme',sekme);sekmeCiz()};

ciz();
const d=durum.get('detay','');if(d&&H[d])detayAc(d);
</script></body></html>"""


def arayuz_html(paket: dict) -> str:
    veri = json.dumps(paket, ensure_ascii=False).replace("</", "<\\/")
    return ARAYUZ.replace("__VERI__", veri)


# ---------- Sayfa ----------
st.markdown("""
<style>
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden;height:0}
.stApp {background:#0b0d12}
.block-container {padding:0 !important; max-width:100% !important}
div[data-testid="stExpander"] {margin:0 8px; border:0}
div[data-testid="stExpander"] details {border:0; background:#14171f; border-radius:12px}
div[data-testid="stExpander"] summary {font-size:13px; color:#8b93a3; padding:6px 12px}
iframe {height:calc(100dvh - 58px) !important; display:block}
div[data-testid="stProgress"] {padding:0 12px}
</style>""", unsafe_allow_html=True)

with st.expander("⚙️ Ayarlar · hisseler, periyot, güven"):
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
    acik = seans_acik_mi()
    sonuclar, hatalar = [], []
    ilerleme = st.progress(0.0, text="BIST 100 alınıyor...")
    piyasa = piyasa_yonu(periyot, gecmis)
    bist = None
    try:
        x = veri_cek("XU100.IS", periyot, gecmis)
        if len(x):
            bugun = x[x.index.date == x.index[-1].date()]
            bist = dict(fiyat=_r(x["Close"].iloc[-1], 2),
                        degisim=_r((x["Close"].iloc[-1] / bugun["Open"].iloc[0] - 1) * 100, 2))
    except Exception:
        pass
    for n, h in enumerate(hisseler, 1):
        ilerleme.progress(n / max(len(hisseler), 1), text=f"{h} inceleniyor...")
        try:
            ham = veri_cek(f"{h}.IS", periyot, gecmis)
            if len(ham) < 80:
                hatalar.append(h)
            else:
                sonuclar.append(analiz(h, ham, piyasa, not acik))
        except Exception:
            hatalar.append(h)
    ilerleme.empty()
    if hatalar:
        st.warning("Veri alınamadı: " + ", ".join(hatalar))
    if not sonuclar:
        st.error("Hiçbir hissenin verisi alınamadı. Biraz sonra tekrar dene.")
        return

    paketler, tum = [], []
    for a in sonuclar:
        f = filtrele(a["sinyaller"], min_guven)
        tum += f
        yeni = [s for s in f if s["i"] >= a["n"] - GERIYE_BAK_MUM]
        paketler.append(hisse_paketi(a, f, yeni[-1] if yeni else None))
    genel = istatistik(tum)
    paket = dict(hisseler=paketler, seans=acik, guncelleme=f"{dt.datetime.now(TZ):%H:%M}",
                 bist100=bist, isabet=_r(genel["isabet"], 0), min_guven=min_guven,
                 geriye=GERIYE_BAK_MUM, ufuk=TEST_UFKU, periyot=periyot_adi)
    components.html(arayuz_html(paket), height=760, scrolling=False)


panel()
