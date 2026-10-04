"""
BORSA RADAR — BIST sinyal botu
------------------------------
Borsa İstanbul'daki tüm likit hisseleri tarar. 15 dakikalık grafikte:
  - Destek/direnç (tepe-dip kümeleri) ve hacim profili (POC, değer bölgesi, yüksek hacimli düğümler)
  - VWAP, alıcı/satıcı baskısı (mum içi hacim dağılımı), saate göre göreli hacim (RVOL)
  - Stop avı (likidite süpürme), emilim, piyasa yapısı (BOS / CHoCH)
  - Formasyonlar: ikili dip/tepe, OBO/TOBO, üçgenler, bayraklar
  - Günlük trend onayı, BIST100 yönü ve göreli güç
Her sinyale 0-100 güven puanı verir; alıcıların gerçekten olduğu hacimli bölgelerde ekstra puan verir.
Sinyaller hedef ya da stop gelene kadar aktif olarak takip edilir.

Yatırım tavsiyesi değildir.
"""

import bisect
import datetime as dt
import json
import threading
import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

st.set_page_config(page_title="Borsa Radar", page_icon="📡", layout="wide")

# ======================= AYARLAR =======================
TUM_HISSELER = """
ACSEL ADEL ADESE ADGYO AEFES AFYON AGESA AGHOL AGROT AHGAZ AKBNK AKCNS AKENR AKFGY AKFYE AKGRT AKMGY AKSA AKSEN
AKSGY AKSUE AKYHO ALARK ALBRK ALCTL ALFAS ALGYO ALKA ALKIM ALMAD ALTNY ANELE ANGEN ANHYT ANSGR ARASE ARCLK ARDYZ
ARENA ARSAN ARZUM ASELS ASGYO ASTOR ASUZU ATAGY ATAKP ATATP ATEKS ATLAS ATSYH AVGYO AVHOL AVOD AVPGY AVTUR AYCES
AYDEM AYEN AYES AYGAZ AZTEK BAGFS BAKAB BALAT BANVT BARMA BASCM BASGZ BAYRK BEGYO BERA BEYAZ BFREN BIENY BIGCH
BIMAS BINHO BIOEN BIZIM BJKAS BLCYT BMSCH BMSTL BNTAS BOBET BORLS BORSK BOSSA BRISA BRKO BRKSN BRKVY BRLSM BRMEN
BRSAN BRYAT BSOKE BTCIM BUCIM BURCE BURVA BVSAN BYDNR CANTE CATES CCOLA CELHA CEMAS CEMTS CEOEM CIMSA CLEBI
CMBTN CMENT CONSE COSMO CRDFA CRFSA CUSAN CVKMD CWENE DAGHL DAGI DAPGM DARDL DENGE DERHL DERIM DESA DESPC DEVA
DGATE DGGYO DGNMO DITAS DMRGD DMSAS DNISI DOAS DOBUR DOCO DOFER DOGUB DOHOL DOKTA DURDO DYOBY DZGYO EBEBK ECILC
ECZYT EDATA EDIP EGEEN EGEPO EGGUB EGPRO EGSER EKGYO EKIZ EKOS EKSUN ELITE EMKEL EMNIS ENERY ENJSA ENKAI ENSRI
ENTRA EPLAS ERBOS ERCB EREGL ERSU ESCAR ESCOM ESEN ETILR ETYAT EUHOL EUKYO EUPWR EUREN EUYO EYGYO FADE FENER
FLAP FMIZP FONET FORMT FORTE FRIGO FROTO FZLGY GARAN GARFA GEDIK GEDZA GENIL GENTS GEREL GESAN GIPTA GLBMD GLCVY
GLRYH GLYHO GMTAS GOKNR GOLTS GOODY GOZDE GRNYO GRSEL GRTHO GSDDE GSDHO GSRAY GUBRF GWIND GZNMI HALKB HATEK
HATSN HDFGS HEDEF HEKTS HKTM HLGYO HOROZ HRKET HTTBT HUBVC HUNER HURGZ ICBCT ICUGS IDGYO IEYHO IHAAS IHEVA IHGZT
IHLAS IHLGM IHYAY IMASM INDES INFO INGRM INTEM INVEO INVES IPEKE ISATR ISBIR ISBTR ISCTR ISDMR ISFIN ISGSY ISGYO
ISKPL ISMEN ISSEN IZENR IZFAS IZINV IZMDC JANTS KAPLM KAREL KARSN KARTN KARYE KATMR KAYSE KBORU KCAER KCHOL
KENT KERVN KERVT KFEIN KGYO KIMMR KLGYO KLKIM KLMSN KLNMA KLRHO KLSER KLSYN KMPUR KNFRT KOCMT KONKA KONTR KONYA
KOPOL KORDS KOTON KOZAA KOZAL KRDMA KRDMB KRDMD KRGYO KRONT KRPLS KRSTL KRTEK KRVGD KSTUR KTLEV KTSKR KUTPO
KUVVA KUYAS KZBGY KZGYO LIDER LIDFA LILAK LINK LKMNH LMKDC LOGO LRSHO LUKSK MAALT MACKO MAGEN MAKIM MAKTK MANAS
MARBL MARKA MARTI MAVI MEDTR MEGAP MEGMT MEKAG MEPET MERCN MERIT MERKO METRO METUR MGROS MHRGY MIATK MIPAZ MMCAS
MNDRS MNDTR MOBTL MOGAN MPARK MRGYO MRSHL MSGYO MTRKS MTRYO MZHLD NATEN NETAS NIBAS NTGAZ NTHOL NUGYO NUHCM
OBAMS OBASE ODAS ODINE OFSYM ONCSM ONRYT ORCAY ORGE ORMA OSMEN OSTIM OTKAR OTTO OYAKC OYAYO OYLUM OYYAT OZATD
OZGYO OZKGY OZRDN OZSUB OZYSR PAGYO PAMEL PAPIL PARSN PASEU PATEK PCILT PEKGY PENGD PENTA PETKM PETUN PGSUS
PINSU PKART PKENT PLTUR PNLSN PNSUT POLHO POLTK PRDGS PRKAB PRKME PRZMA PSDTC PSGYO QNBFK QNBTR QUAGR RALYH
RAYSG REEDR RGYAS RNPOL RODRG RTALB RUBNS RYGYO RYSAS SAFKR SAHOL SAMAT SANEL SANFM SANKO SARKY SASA SAYAS
SDTTR SEGMN SEGYO SEKFK SEKUR SELEC SELGD SELVA SEYKM SILVR SISE SKBNK SKTAS SKYLP SKYMD SMART SMRTG SMRVA SNGYO
SNICA SNKRN SNPAM SODSN SOKE SOKM SONME SRVGY SUMAS SUNTK SURGY SUWEN TABGD TARKM TATEN TATGD TAVHL TBORG TCELL
TCKRC TDGYO TEKTU TERA TETMT TEZOL TGSAS THYAO TKFEN TKNSA TLMAN TMPOL TMSN TNZTP TOASO TRCAS TRGYO TRILC TSGYO
TSKB TSPOR TTKOM TTRAK TUCLK TUKAS TUPRS TUREX TURGG TURSG UFUK ULAS ULKER ULUFA ULUSE ULUUN UMPAS UNLU USAK
VAKBN VAKFN VAKKO VANGD VBTYZ VERTU VERUS VESBE VESTL VKFYO VKGYO VKING VRGYO YAPRK YATAS YAYLA YBTAS YEOTK
YESIL YGGYO YGYO YKBNK YKSLN YONGA YUNSA YYAPI YYLGD ZEDUR ZOREN ZRGYO
""".split()

PIVOT_PENCERE = 5           # tepe/dip tespiti için sağ-sol mum sayısı
SEVIYE_TOLERANS = 0.006     # %0.6 seviyelere yakınlık toleransı
TEST_UFKU = 26              # sinyal kaç mum boyunca takip edilir (≈ 1 işlem günü)
YENI_MUM = 2                # bu kadar mum içindeki sinyaller "yeni" sayılır
ONE_CIKAN_ESIK = 45         # tam geçmiş testi yapılacak sinyallerin alt güven sınırı
GRAFIK_MUM = 130            # her hisse için grafiğe gönderilen mum sayısı
YENILEME = dt.timedelta(minutes=5)
TZ = ZoneInfo("Europe/Istanbul")
MIN_LIKIDITE = 20            # milyon TL; daha sığ hisseler hiç taranmaz (ayar uygulamada ayrıca filtrelenir)
AGIRLIK = {"g": {}, "w": {}}  # kurulum karnesine göre otomatik güven düzeltmesi (arka planda güncellenir)
KURULUM_ADI = {"dk": "Direnç kırılımı", "dsk": "Destek kırılımı", "dd": "Destekten dönüş", "rd": "Dirençten dönüş",
               "sweep": "Stop avı + dönüş", "emilim": "Emilim", "yapi": "Yapı kırılımı / CHoCH"}
SEKTOR_LISTE = {
    "Banka": "AKBNK GARAN ISCTR YKBNK VAKBN HALKB TSKB SKBNK ALBRK QNBTR ICBCT KLNMA",
    "Sigorta & Finans": "AKGRT ANSGR TURSG AGESA ANHYT RAYSG GEDIK ISMEN INFO OSMEN ISFIN GARFA VAKFN SEKFK CRDFA LIDFA ULUFA",
    "Holding": "KCHOL SAHOL DOHOL AGHOL ALARK TKFEN GLYHO NTHOL POLHO ECZYT GSDHO IHLAS BERA METRO NETAS",
    "Enerji": "AKSEN ENJSA ZOREN AYDEM ODAS AYEN CWENE EUPWR GWIND NATEN SMRTG ESEN CANTE BIOEN MAGEN AKFYE ALFAS ENERY ENTRA IZENR YEOTK AHGAZ AKENR CONSE",
    "Demir-çelik & Metal": "EREGL KRDMD KRDMA KRDMB ISDMR BRSAN CEMTS KCAER BURCE BURVA SARKY ASUZU TUCLK ERBOS",
    "Havacılık & Ulaşım": "THYAO PGSUS TAVHL CLEBI DOCO RYSAS PASEU",
    "Otomotiv": "FROTO TOASO DOAS OTKAR KARSN TTRAK BRISA GOODY FMIZP EGEEN JANTS",
    "Perakende & Gıda": "BIMAS MGROS SOKM MAVI ULKER CCOLA AEFES TATGD TUKAS PNSUT BANVT KNFRT EBEBK BIZIM ULUUN TBORG KRVGD OBAMS",
    "Savunma & Teknoloji": "ASELS KONTR LOGO KAREL ARDYZ INDES ESCOM SDTTR PAPIL MIATK OBASE FONET LINK ALCTL ASTOR REEDR",
    "Kimya & Petrol": "TUPRS PETKM SASA AKSA AYGAZ GUBRF HEKTS ALKIM KMPUR BAGFS EGGUB",
    "Cam, Çimento & İnşaat": "SISE CIMSA AKCNS OYAKC NUHCM BTCIM BUCIM GOLTS ENKAI KONYA",
    "Telekom": "TCELL TTKOM",
    "Beyaz eşya & Elektronik": "ARCLK VESTL VESBE",
    "Madencilik": "KOZAL KOZAA IPEKE",
    "Tekstil": "KORDS YUNSA ATEKS",
}
SEKTOR = {h: ad for ad, liste in SEKTOR_LISTE.items() for h in liste.split()}


def sektor_bul(h: str) -> str:
    if h in SEKTOR:
        return SEKTOR[h]
    return "GYO" if h.endswith("GYO") else "Diğer"
# =======================================================


def sayi(x, ondalik=2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    return f"{x:,.{ondalik}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def nanv(x, varsayilan=0.0):
    try:
        return varsayilan if x is None or np.isnan(x) else float(x)
    except TypeError:
        return varsayilan


def _r(x, n=2):
    x = nanv(x, None) if x is not None else None
    return None if x is None else round(x, n)


def seans_acik_mi() -> bool:
    simdi = dt.datetime.now(TZ)
    return simdi.weekday() < 5 and dt.time(10, 0) <= simdi.time() <= dt.time(18, 10)


# ---------- Veri ----------
def _toplu(semboller: list[str], period: str, interval: str, parca: int = 80) -> dict:
    sonuc = {}
    for k in range(0, len(semboller), parca):
        grup = semboller[k:k + parca]
        try:
            ham = yf.download(grup, period=period, interval=interval, group_by="ticker",
                              auto_adjust=False, threads=True, progress=False)
        except Exception:
            continue
        if ham is None or ham.empty:
            continue
        for s in grup:
            try:
                df = ham[s] if isinstance(ham.columns, pd.MultiIndex) else ham
                df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                df = df[df["Volume"] > 0]
                if len(df):
                    sonuc[s] = df
            except Exception:
                pass
    return sonuc


def gunluk_veri() -> dict:
    """Tüm hisselerin 1 yıllık günlük verisi (likidite ve günlük trend için)."""
    v = _toplu([f"{h}.IS" for h in TUM_HISSELER] + ["XU100.IS"], "1y", "1d", parca=120)
    out = {}
    for s, df in v.items():
        df = df.copy()
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        out[s.replace(".IS", "")] = df
    return out


def _gun_ici(semboller: list[str], period: str = "30d") -> dict:
    v = _toplu([f"{h}.IS" for h in semboller], period, "15m")
    out = {}
    for s, df in v.items():
        df = df.copy()
        df.index = df.index.tz_convert(TZ)
        out[s.replace(".IS", "")] = df
    return out


# ---------- Göstergeler ----------
def rsi(seri: pd.Series, n: int = 14) -> pd.Series:
    fark = seri.diff()
    kazanc = fark.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    kayip = (-fark.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + kazanc / kayip.replace(0, np.nan))


def gostergeler(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    for n in (20, 50, 200):
        df[f"EMA{n}"] = c.ewm(span=n, adjust=False).mean()
    df["RSI"] = rsi(c)
    df["MACD"] = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    df["MACDs"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["MACDh"] = df["MACD"] - df["MACDs"]
    onceki = c.shift(1)
    tr = pd.concat([h - l, (h - onceki).abs(), (l - onceki).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    orta, sd = c.rolling(20).mean(), c.rolling(20).std()
    df["BBu"], df["BBa"] = orta + 2 * sd, orta - 2 * sd
    df["BBw"] = (df["BBu"] - df["BBa"]) / orta
    df["BBwMin"] = df["BBw"].rolling(60, min_periods=20).min()
    # Gün içi VWAP (her gün sıfırlanır)
    gun = df.index.date
    tp = (h + l + c) / 3
    df["VWAP"] = (tp * v).groupby(gun).cumsum() / v.groupby(gun).cumsum().replace(0, np.nan)
    # Mum içi alıcı/satıcı hacmi tahmini: kapanış mumun neresinde -> hacmin o kadarı alıcı
    aralik = (h - l).replace(0, np.nan)
    df["Delta"] = (v * ((c - l) - (h - c)) / aralik).fillna(0)
    df["AB"] = df["Delta"].rolling(20).sum() / v.rolling(20).sum().replace(0, np.nan)
    df["CVD"] = df["Delta"].cumsum()
    # Saate göre göreli hacim: aynı saat diliminin son 10 gün ortalamasına göre
    gun_k, gun_no = np.unique(np.array(gun), return_inverse=True)
    dilim = df.index.hour.values * 60 + df.index.minute.values
    dilim_k, dilim_no = np.unique(dilim, return_inverse=True)
    M = np.full((len(gun_k), len(dilim_k)), np.nan)
    M[gun_no, dilim_no] = v.values
    ort = pd.DataFrame(M).shift(1).rolling(10, min_periods=3).mean().values[gun_no, dilim_no]
    yedek = v.rolling(20).mean().shift(1).values
    payda = np.where(np.isnan(ort), yedek, ort)
    with np.errstate(divide="ignore", invalid="ignore"):
        df["RVOL"] = np.where(payda > 0, v.values / payda, np.nan)
    return df


# ---------- Tepe / dip, seviyeler, hacim profili ----------
def pivot_bul(df: pd.DataFrame) -> list[tuple]:
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
    gruplar = [[fiyatlar[0], 1]]  # [toplam, adet]
    for f in fiyatlar[1:]:
        m = gruplar[-1][0] / gruplar[-1][1]
        if abs(f - m) / m <= SEVIYE_TOLERANS:
            gruplar[-1][0] += f
            gruplar[-1][1] += 1
        else:
            gruplar.append([f, 1])
    guclu = [t / a for t, a in gruplar if a >= 2]
    return guclu if guclu else [t / a for t, a in gruplar]


def hacim_profili(H, L, V, bins: int = 40):
    lo, hi = float(np.min(L)), float(np.max(H))
    if hi <= lo or len(V) < 20:
        return None
    hist = np.zeros(bins)
    olcek = bins / (hi - lo)
    for h, l, v in zip(H, L, V):
        a = min(max(int((l - lo) * olcek), 0), bins - 1)
        b = min(max(int((h - lo) * olcek), 0), bins - 1)
        hist[a:b + 1] += v / (b - a + 1)
    kenar = np.linspace(lo, hi, bins + 1)
    merkez = (kenar[:-1] + kenar[1:]) / 2
    poc = int(np.argmax(hist))
    toplam, acc, a, b = hist.sum(), hist[poc], poc, poc
    while acc < 0.7 * toplam and (a > 0 or b < bins - 1):
        yukari = hist[b + 1] if b < bins - 1 else -1
        asagi = hist[a - 1] if a > 0 else -1
        if yukari >= asagi:
            b += 1; acc += yukari
        else:
            a -= 1; acc += asagi
    ort = hist.mean()
    hvn = [float(merkez[k]) for k in range(1, bins - 1)
           if hist[k] >= 1.25 * ort and hist[k] >= hist[k - 1] and hist[k] >= hist[k + 1]]
    return dict(poc=float(merkez[poc]), vah=float(kenar[b + 1]), val=float(kenar[a]), hvn=hvn,
                lo=lo, hi=hi, olcek=olcek, hist=hist / hist.max(), merkez=merkez)


def bolge_gucu(prof, fiyat) -> float:
    """Fiyatın bulunduğu bölgedeki hacim yoğunluğu (0-1)."""
    if not prof or not (prof["lo"] <= fiyat <= prof["hi"]):
        return 0.0
    k = min(int((fiyat - prof["lo"]) * prof["olcek"]), len(prof["hist"]) - 1)
    return float(prof["hist"][max(k - 1, 0):k + 2].max())


# ---------- Formasyonlar ----------
def _dogru(p1, p2, j):
    (j1, y1), (j2, y2) = p1, p2
    return y1 if j2 == j1 else y1 + (y2 - y1) * (j - j1) / (j2 - j1)


def formasyonlar(A: dict, pv: list[tuple], i: int) -> list[dict]:
    C, Hh, Ll = A["Close"], A["High"], A["Low"]
    c, cp, atr = C[i], C[i - 1], nanv(A["ATR"][i], C[i] * 0.01)
    H = [p for p in pv if p[2] == "H" and p[0] >= i - 120]
    L = [p for p in pv if p[2] == "L" and p[0] >= i - 120]
    sonuc = []

    def ekle(ad, yon, durum, cizgiler, hedef, ref):
        sonuc.append(dict(ad=ad, yon=yon, durum=durum, cizgiler=cizgiler, hedef=hedef, ref=ref))

    if len(L) >= 2:
        (j1, p1, _), (j2, p2, _) = L[-2], L[-1]
        if j2 - j1 >= 8 and abs(p1 - p2) / p1 <= 0.015 and i - j2 <= 40:
            jm = j1 + int(np.argmax(Hh[j1:j2 + 1]))
            boyun, dip = float(Hh[jm]), min(p1, p2)
            if boyun / max(p1, p2) - 1 >= 0.02 and np.min(Ll[j2 + 1:i], initial=np.inf) >= dip * 0.99:
                durum = "kırıldı" if c > boyun >= cp else ("oluşuyor" if c <= boyun else None)
                if durum:
                    ekle("İkili dip", 1, durum, [(j1, p1, jm, boyun), (jm, boyun, j2, p2), (j1, boyun, i, boyun)],
                         boyun + (boyun - dip), boyun)
    if len(H) >= 2:
        (j1, p1, _), (j2, p2, _) = H[-2], H[-1]
        if j2 - j1 >= 8 and abs(p1 - p2) / p1 <= 0.015 and i - j2 <= 40:
            jm = j1 + int(np.argmin(Ll[j1:j2 + 1]))
            boyun, tepe = float(Ll[jm]), max(p1, p2)
            if 1 - boyun / min(p1, p2) >= 0.02 and np.max(Hh[j2 + 1:i], initial=-np.inf) <= tepe * 1.01:
                durum = "kırıldı" if c < boyun <= cp else ("oluşuyor" if c >= boyun else None)
                if durum:
                    ekle("İkili tepe", -1, durum, [(j1, p1, jm, boyun), (jm, boyun, j2, p2), (j1, boyun, i, boyun)],
                         boyun - (tepe - boyun), boyun)
    if len(H) >= 3:
        (a, ha, _), (b, hb, _), (d, hd, _) = H[-3:]
        if hb > ha * 1.015 and hb > hd * 1.015 and abs(ha - hd) / ha <= 0.02 and i - d <= 40 and d - a >= 12:
            n1j, n2j = a + int(np.argmin(Ll[a:b + 1])), b + int(np.argmin(Ll[b:d + 1]))
            n1, n2 = (n1j, float(Ll[n1j])), (n2j, float(Ll[n2j]))
            bi, bo = _dogru(n1, n2, i), _dogru(n1, n2, i - 1)
            durum = "kırıldı" if c < bi and cp >= bo else ("oluşuyor" if c >= bi else None)
            if durum:
                ekle("OBO", -1, durum, [(a, ha, n1j, n1[1]), (n1j, n1[1], b, hb), (b, hb, n2j, n2[1]),
                                        (n2j, n2[1], d, hd), (n1j, n1[1], i, bi)], bi - (hb - _dogru(n1, n2, b)), bi)
    if len(L) >= 3:
        (a, la, _), (b, lb, _), (d, ld, _) = L[-3:]
        if lb < la * 0.985 and lb < ld * 0.985 and abs(la - ld) / la <= 0.02 and i - d <= 40 and d - a >= 12:
            n1j, n2j = a + int(np.argmax(Hh[a:b + 1])), b + int(np.argmax(Hh[b:d + 1]))
            n1, n2 = (n1j, float(Hh[n1j])), (n2j, float(Hh[n2j]))
            bi, bo = _dogru(n1, n2, i), _dogru(n1, n2, i - 1)
            durum = "kırıldı" if c > bi and cp <= bo else ("oluşuyor" if c <= bi else None)
            if durum:
                ekle("TOBO", 1, durum, [(a, la, n1j, n1[1]), (n1j, n1[1], b, lb), (b, lb, n2j, n2[1]),
                                        (n2j, n2[1], d, ld), (n1j, n1[1], i, bi)], bi + (_dogru(n1, n2, b) - lb), bi)
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


# ---------- Bağlam (bir hissenin tüm hazırlık hesapları) ----------
def baglam_kur(df15: pd.DataFrame, gunluk: pd.DataFrame | None, xu15: pd.DataFrame | None, son_kapali: bool,
               mod: str = "g") -> dict:
    """mod 'g': 15 dakikalık gün içi, mod 'w': günlük grafik (swing)."""
    df = gostergeler(df15)
    n = len(df) if son_kapali else len(df) - 1
    A = {k: df[k].values for k in df.columns}
    if mod == "w":
        A["VWAP"] = np.full(len(df), np.nan)  # günlük grafikte gün içi VWAP anlamsız
    pv = pivot_bul(df.iloc[:n])

    if mod == "g":   # her gün için önceki 10 günün hacim profili
        tarih = np.array(df.index.date)
        gun_no = np.searchsorted(np.array(sorted(set(tarih))), tarih)
        pencere, en_az = 10, 64
    else:            # haftalık gruplar, önceki 12 haftanın profili
        tarih = np.array(df.index.date)
        gun_no = np.arange(len(df)) // 5
        pencere, en_az = 12, 40

    class Profiller(dict):  # ihtiyaç duyulan grubun profili ilk istendiğinde hesaplanır
        def get(self, g, varsayilan=None):
            if g not in self:
                m = (gun_no >= g - pencere) & (gun_no < g)
                self[g] = hacim_profili(A["High"][m], A["Low"][m], A["Volume"][m]) if m.sum() >= en_az else None
            return self[g]
    prof = Profiller()
    m = gun_no >= gun_no[n - 1] - (pencere - 1)
    m[n:] = False
    prof_guncel = hacim_profili(A["High"][m], A["Low"][m], A["Volume"][m]) if m.sum() >= en_az else None

    # Günlük trend (bir önceki günün kapanışına göre) — sadece gün içi modda üst zaman dilimi onayı
    htf = np.zeros(len(df))
    if mod == "g" and gunluk is not None and len(gunluk) > 60:
        g = gunluk.copy()
        g["E20"] = g["Close"].ewm(span=20, adjust=False).mean()
        g["E50"] = g["Close"].ewm(span=50, adjust=False).mean()
        trend = np.where((g["Close"] > g["E20"]) & (g["E20"] > g["E50"]), 1,
                         np.where((g["Close"] < g["E20"]) & (g["E20"] < g["E50"]), -1, 0))
        tr = pd.Series(trend, index=g.index).shift(1)
        htf = tr.reindex(pd.to_datetime(pd.Series(tarih)), method="ffill").fillna(0).values

    # BIST100 yönü ve göreli güç
    py, rs = np.zeros(len(df)), np.zeros(len(df))
    if xu15 is not None and len(xu15) > 60:
        xc = xu15["Close"].reindex(df.index, method="ffill")
        ema = xu15["Close"].ewm(span=50, adjust=False).mean().reindex(df.index, method="ffill")
        py = np.sign(xc - ema).fillna(0).values
        geri = 160 if mod == "g" else 20  # ≈ 5 / 20 işlem günü
        rs = ((df["Close"] / df["Close"].shift(geri) - 1) - (xc / xc.shift(geri) - 1)).fillna(0).values * 100

    return dict(df=df, A=A, n=n, pv=pv, pv_j=[p[0] for p in pv], gun_no=gun_no, prof=prof,
                prof_guncel=prof_guncel, htf=htf, py=py, rs=rs, mod=mod)


def yapi_bul(pv):
    H = [p for p in pv if p[2] == "H"][-2:]
    L = [p for p in pv if p[2] == "L"][-2:]
    if len(H) < 2 or len(L) < 2:
        return 0, H, L
    if H[1][1] > H[0][1] and L[1][1] > L[0][1]:
        return 1, H, L
    if H[1][1] < H[0][1] and L[1][1] < L[0][1]:
        return -1, H, L
    return 0, H, L


# ---------- Puanlama ----------
def puanla(ctx, i, yon, olay, sebepler, ref, hedef_ozel, stop_ozel, sev, prof, pv) -> dict:
    A = ctx["A"]
    c, atr = A["Close"][i], nanv(A["ATR"][i], A["Close"][i] * 0.01)
    puan, arti, eksi = olay, [], []
    yukari = yon > 0
    yonlu = lambda x: x * yon  # noqa: E731

    # Trend (15 dk) ve günlük trend
    ema50, ema200 = A["EMA50"][i], A["EMA200"][i]
    if yonlu(ema50 - ema200) > 0 and yonlu(c - ema50) > 0:
        puan += 8; arti.append(("15 dk" if ctx["mod"] == "g" else "Günlük") + " trend " + ("yukarı" if yukari else "aşağı"))
    elif yonlu(ema50 - ema200) < 0:
        puan -= 6; eksi.append(("15 dk" if ctx["mod"] == "g" else "Günlük") + " trende karşı")
    htf = ctx["htf"][i]
    if htf * yon > 0:
        puan += 10; arti.append("Günlük trend onaylıyor")
    elif htf * yon < 0:
        puan -= 14; eksi.append("Günlük trende karşı")

    # VWAP
    vw = A["VWAP"][i]
    if not np.isnan(vw):
        if yonlu(c - vw) > 0:
            puan += 7; arti.append("Fiyat VWAP'ın " + ("üstünde" if yukari else "altında"))
        else:
            puan -= 5; eksi.append("Fiyat VWAP'ın " + ("altında" if yukari else "üstünde"))

    # Alıcı / satıcı baskısı
    ab = nanv(A["AB"][i])
    taraf = "Alıcılar" if yukari else "Satıcılar"
    if yonlu(ab) > 0.25:
        puan += 12; arti.append(f"{taraf} baskın (%{abs(ab) * 100:.0f})")
    elif yonlu(ab) > 0.08:
        puan += 6; arti.append(f"{taraf} önde (%{abs(ab) * 100:.0f})")
    elif yonlu(ab) < -0.1:
        puan -= 10; eksi.append(("Satıcılar" if yukari else "Alıcılar") + f" baskın (%{abs(ab) * 100:.0f})")

    # Göreli hacim
    rv = nanv(A["RVOL"][i])
    if rv >= 3:
        puan += 15; arti.append(f"Hacim patlaması ({rv:.1f}x)")
    elif rv >= 2:
        puan += 11; arti.append(f"Çok yüksek hacim ({rv:.1f}x)")
    elif rv >= 1.5:
        puan += 7; arti.append(f"Yüksek hacim ({rv:.1f}x)")
    elif rv >= 1.2:
        puan += 3; arti.append(f"Hacim normal üstü ({rv:.1f}x)")
    elif rv < 0.8:
        puan -= 10; eksi.append(f"Hacim zayıf ({rv:.1f}x)")

    # Hacimli bölge (gerçek alıcı/satıcı yığılması)
    yogun = max(bolge_gucu(prof, ref), bolge_gucu(prof, c))
    hacimli_bolge = yogun >= 0.6
    if hacimli_bolge:
        puan += 8; arti.append("Yüksek hacimli fiyat bölgesi")

    # CVD uyumsuzluğu (fiyat yeni dip/tepe yaparken hacim akışı tersini gösteriyor)
    if i >= 40:
        C, cvd = A["Close"], A["CVD"]
        a1, a2 = slice(i - 40, i - 20), slice(i - 20, i + 1)
        if yukari and C[a2].min() < C[a1].min() and cvd[a2].min() > cvd[a1].min():
            puan += 8; arti.append("Gizli alım (CVD uyumsuzluğu)")
        if not yukari and C[a2].max() > C[a1].max() and cvd[a2].max() < cvd[a1].max():
            puan += 8; arti.append("Gizli satış (CVD uyumsuzluğu)")

    # Momentum
    mh, mh1 = nanv(A["MACDh"][i]), nanv(A["MACDh"][i - 1])
    if yonlu(mh) > 0:
        puan += 5; arti.append("MACD onaylıyor")
    elif yonlu(mh - mh1) > 0:
        puan += 2
    else:
        puan -= 4; eksi.append("MACD ters yönde")
    r = nanv(A["RSI"][i], 50)
    if yukari and r > 74:
        puan -= 12; eksi.append(f"RSI aşırı alımda ({r:.0f})")
    elif not yukari and r < 26:
        puan -= 12; eksi.append(f"RSI aşırı satımda ({r:.0f})")
    bw1, bwmin = A["BBw"][i - 1], A["BBwMin"][i - 1]
    if not np.isnan(bw1) and not np.isnan(bwmin) and bw1 <= bwmin * 1.1:
        if (yukari and c > A["BBu"][i]) or (not yukari and c < A["BBa"][i]):
            puan += 5; arti.append("Sıkışmadan çıkış")

    # Piyasa ve göreli güç
    if ctx["py"][i] * yon > 0:
        puan += 4; arti.append("BIST100 aynı yönde")
    elif ctx["py"][i] * yon < 0:
        puan -= 8; eksi.append("BIST100 ters yönde")
    rs = ctx["rs"][i]
    if yonlu(rs) > 2:
        puan += 5; arti.append(f"Endeksten {'güçlü' if yukari else 'zayıf'} ({rs:+.1f}%)")
    elif yonlu(rs) < -2:
        puan -= 5; eksi.append(f"Endeksten {'zayıf' if yukari else 'güçlü'} ({rs:+.1f}%)")

    # "Israrcı" bonus: alıcılar hacimli bölgede gerçekten iş başında
    guclu = hacimli_bolge and rv >= 1.5 and yonlu(ab) > 0.2
    if guclu:
        puan += 10

    # Stop: yapının (son dip/tepe) arkası; hedef: sıradaki seviye, en az 1.5R
    dipler = [p[1] for p in pv[-12:] if p[2] == "L" and p[1] < c]
    tepeler = [p[1] for p in pv[-12:] if p[2] == "H" and p[1] > c]
    tum_sev = sorted(set([round(x, 4) for x in sev] + ([prof["poc"], prof["vah"], prof["val"]] + prof["hvn"] if prof else [])))
    if yukari:
        aday = ref - 0.5 * atr
        if dipler:
            aday = min(aday, max(dipler) - 0.2 * atr)
        stop = stop_ozel if stop_ozel else max(aday, c - 3 * atr)
        if stop >= c - 0.4 * atr:
            stop = c - 1.2 * atr
        R = c - stop
        ustler = [x for x in tum_sev if x > c + 1.5 * R]
        hedef = ustler[0] if ustler else c + 2 * R
        if hedef_ozel and hedef_ozel > c + 1.5 * R:
            hedef = min(hedef, hedef_ozel) if ustler else hedef_ozel
        sonra = [x for x in tum_sev if x > hedef * 1.003]
        hedef2 = sonra[0] if sonra else hedef + R
    else:
        aday = ref + 0.5 * atr
        if tepeler:
            aday = max(aday, min(tepeler) + 0.2 * atr)
        stop = stop_ozel if stop_ozel else min(aday, c + 3 * atr)
        if stop <= c + 0.4 * atr:
            stop = c + 1.2 * atr
        R = stop - c
        altlar = [x for x in tum_sev if x < c - 1.5 * R]
        hedef = altlar[-1] if altlar else c - 2 * R
        if hedef_ozel and hedef_ozel < c - 1.5 * R:
            hedef = max(hedef, hedef_ozel) if altlar else hedef_ozel
        sonra = [x for x in tum_sev if x < hedef * 0.997]
        hedef2 = sonra[-1] if sonra else hedef - R
    rk = abs(hedef - c) / R if R > 0 else 0
    if rk >= 2.5:
        puan += 5; arti.append(f"Risk/kazanç {rk:.1f}")
    elif rk < 1.5:
        puan -= 8; eksi.append(f"Risk/kazanç düşük ({rk:.1f})")

    # Giriş aralığı: kovalamadan, geri çekilmede kademeli giriş bölgesi
    if yukari:
        giris_ust = c + 0.15 * atr
        giris_alt = max(c - 0.5 * atr, (stop + c) / 2)
        sonra3 = [x for x in tum_sev if x > hedef2 * 1.003]
        hedef3 = sonra3[0] if sonra3 else hedef2 + R
    else:
        giris_alt = c - 0.15 * atr
        giris_ust = min(c + 0.5 * atr, (stop + c) / 2)
        sonra3 = [x for x in tum_sev if x < hedef2 * 0.997]
        hedef3 = sonra3[-1] if sonra3 else hedef2 - R

    return dict(tur="AL" if yukari else "SAT", yon=yon, guven=int(max(0, min(100, puan))), guclu=bool(guclu),
                sebepler=sebepler, arti=arti, eksi=eksi, fiyat=float(c), stop=float(stop),
                hedef=float(hedef), hedef2=float(hedef2), hedef3=float(hedef3), rk=float(rk),
                giris_alt=float(giris_alt), giris_ust=float(giris_ust))


def sinyal_bul(ctx, i):
    """i. mum kapanışında sinyal var mı? Sadece i'ye kadarki veri kullanılır."""
    A = ctx["A"]
    pv = ctx["pv"][:bisect.bisect_right(ctx["pv_j"], i - PIVOT_PENCERE - 1)]
    if len(pv) < 4:
        return None, []
    onbellek = ctx.setdefault("sev_onbellek", {})
    if len(pv) not in onbellek:
        onbellek[len(pv)] = seviyeler_bul(pv)
    sev = onbellek[len(pv)]
    prof = ctx["prof"].get(ctx["gun_no"][i])
    profil_sev = [prof["poc"], prof["vah"], prof["val"]] if prof else []
    c, o, h, l, cp = A["Close"][i], A["Open"][i], A["High"][i], A["Low"][i], A["Close"][i - 1]
    atr = nanv(A["ATR"][i], c * 0.01)
    rv = nanv(A["RVOL"][i])
    tol = SEVIYE_TOLERANS
    yesil, kirmizi = c > o, c < o
    olaylar = {}

    def olay(anahtar, yon, puan, metin, seviye, hedef=None, stop=None):
        eski = olaylar.get(anahtar)
        if eski is None or abs(seviye - c) < abs(eski[3] - c):
            olaylar[anahtar] = (yon, puan, metin, seviye, hedef, stop, anahtar)

    for L_ in sev + profil_sev:
        ad = "profil" if L_ in profil_sev else "seviye"
        if cp < L_ and c > L_ * (1 + tol / 2) and yesil and rv >= 1.0:
            olay("dk", 1, 22, f"Direnç kırıldı ({sayi(L_)})" if ad == "seviye" else f"Hacim bölgesi kırıldı ({sayi(L_)})", L_)
        elif cp > L_ and c < L_ * (1 - tol / 2) and kirmizi and rv >= 1.0:
            olay("dsk", -1, 22, f"Destek kırıldı ({sayi(L_)})" if ad == "seviye" else f"Hacim bölgesi kırıldı ({sayi(L_)})", L_)
        elif l <= L_ * (1 + tol) and c > L_ and cp >= L_ * (1 - tol) and yesil and rv >= 1.0:
            olay("dd", 1, 18, f"Destekten dönüş ({sayi(L_)})", L_)
        elif h >= L_ * (1 - tol) and c < L_ and cp <= L_ * (1 + tol) and kirmizi and rv >= 1.0:
            olay("rd", -1, 18, f"Dirençten dönüş ({sayi(L_)})", L_)

    # Stop avı (likidite süpürme): önceki dibin altına iğne, geri kapanış, hacim
    aralik = max(h - l, 1e-9)
    son_dipler = [p for p in pv if p[2] == "L" and p[0] >= i - 60]
    son_tepeler = [p for p in pv if p[2] == "H" and p[0] >= i - 60]
    for p in son_dipler[-3:]:
        if l < p[1] * 0.9995 and c > p[1] and (min(o, c) - l) >= 0.5 * aralik and rv >= 1.2:
            olay("sweep", 1, 26, f"Stop avı + dönüş ({sayi(p[1])} altı süpürüldü)", p[1], stop=l - 0.3 * atr)
    for p in son_tepeler[-3:]:
        if h > p[1] * 1.0005 and c < p[1] and (h - max(o, c)) >= 0.5 * aralik and rv >= 1.2:
            olay("sweep", -1, 26, f"Stop avı + dönüş ({sayi(p[1])} üstü süpürüldü)", p[1], stop=h + 0.3 * atr)

    # Emilim: destekte büyük hacim ama fiyat düşmüyor (alıcılar satışı karşılıyor)
    if rv >= 1.8 and (h - l) <= 0.7 * atr:
        for L_ in sev + profil_sev:
            if abs(l - L_) / L_ <= tol and c >= l + 0.5 * aralik:
                olay("emilim", 1, 20, f"Emilim: {sayi(L_)} desteğinde satışlar karşılandı", L_)
            if abs(h - L_) / L_ <= tol and c <= h - 0.5 * aralik:
                olay("emilim", -1, 20, f"Emilim: {sayi(L_)} direncinde alımlar karşılandı", L_)

    # Piyasa yapısı: BOS (trend devamı) / CHoCH (trend dönüşü)
    yapi, sH, sL = yapi_bul(pv)
    if sH and cp <= sH[-1][1] < c and yesil and rv >= 1.0:
        if yapi == 1:
            olay("yapi", 1, 18, f"Yapı kırılımı / BOS ({sayi(sH[-1][1])})", sH[-1][1])
        elif yapi == -1:
            olay("yapi", 1, 22, f"Trend dönüşü / CHoCH ({sayi(sH[-1][1])})", sH[-1][1])
    if sL and cp >= sL[-1][1] > c and kirmizi and rv >= 1.0:
        if yapi == -1:
            olay("yapi", -1, 18, f"Yapı kırılımı / BOS ({sayi(sL[-1][1])})", sL[-1][1])
        elif yapi == 1:
            olay("yapi", -1, 22, f"Trend dönüşü / CHoCH ({sayi(sL[-1][1])})", sL[-1][1])

    formlar = formasyonlar(A, pv, i)
    for f in formlar:
        if f["durum"] == "kırıldı" and f["yon"] != 0:
            yon_adi = "yukarı" if f["yon"] > 0 else "aşağı"
            olay("f-" + f["ad"], f["yon"], 26, f"{f['ad']} {yon_adi} kırılımı", f["ref"], f["hedef"])

    en_iyi = None
    for yon in (1, -1):
        grup = sorted([v for v in olaylar.values() if v[0] == yon], key=lambda v: -v[1])
        if not grup:
            continue
        toplam = min(sum(v[1] for v in grup), 40)
        hedef_ozel = next((v[4] for v in grup if v[4]), None)
        stop_ozel = next((v[5] for v in grup if v[5]), None)
        s = puanla(ctx, i, yon, toplam, [v[2] for v in grup], grup[0][3], hedef_ozel, stop_ozel, sev, prof, pv)
        anahtar = grup[0][6]
        s["kurulum"] = anahtar
        ag = AGIRLIK.get(ctx["mod"], {}).get(anahtar)
        if ag and ag["bonus"]:
            s["guven"] = int(max(0, min(100, s["guven"] + ag["bonus"])))
            (s["arti"] if ag["bonus"] > 0 else s["eksi"]).append(f"Karne: bu kurulum BIST'te %{ag['isabet']:.0f} isabetli")
        if en_iyi is None or s["guven"] > en_iyi["guven"]:
            en_iyi = s
    return en_iyi, formlar


def sonuc_hesapla(A, s, n):
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


def filtrele(sinyaller: list[dict], min_guven: int) -> list[dict]:
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
                ort=float(np.mean([s["getiri"] for s in biten]) * 100) if biten else None)


def sinyalleri_tara(ctx, bas: int) -> list[dict]:
    A, n, df = ctx["A"], ctx["n"], ctx["df"]
    out = []
    for i in range(max(bas, 60), n):
        s, _ = sinyal_bul(ctx, i)
        if s:
            s["i"], s["zaman"] = i, df.index[i]
            s["sonuc"], s["getiri"] = sonuc_hesapla(A, s, n)
            out.append(s)
    return out


# ---------- Bot yorumu ----------
def bot_yorumu(ctx, sev, formlar) -> tuple[list[str], dict]:
    A, n = ctx["A"], ctx["n"]
    i = n - 1
    c = A["Close"][i]
    cumle = []
    htf = ctx["htf"][i]
    yapi, _, _ = yapi_bul(ctx["pv"])
    trend_metin = {1: "yukarı", -1: "aşağı", 0: "yatay/kararsız"}
    yapi_metin = {1: "yükselen tepe-dipler (HH/HL)", -1: "alçalan tepe-dipler (LH/LL)", 0: "net yön yok"}
    if ctx["mod"] == "g":
        cumle.append(f"Günlük trend {trend_metin[int(htf)]}; 15 dakikalıkta {yapi_metin[yapi]}.")
    else:
        e50, e200 = A["EMA50"][i], A["EMA200"][i]
        cumle.append(f"Günlük grafikte {yapi_metin[yapi]}; fiyat 50 günlük ortalamanın {'üstünde' if c > e50 else 'altında'}"
                     + (f", ana trend {'yukarı' if e50 > e200 else 'aşağı'} (EMA50/200)." if not np.isnan(e200) else "."))
    vw = A["VWAP"][i]
    if not np.isnan(vw):
        fark = (c / vw - 1) * 100
        kim = "alıcılar kârda, gün içi kontrol alıcılarda" if fark > 0 else "gün içi alanlar zararda, kontrol satıcılarda"
        cumle.append(f"Fiyat gün içi ortalama maliyetin (VWAP {sayi(vw)}) %{abs(fark):.1f} {'üstünde' if fark > 0 else 'altında'}: {kim}.")
    ab, rv = nanv(A["AB"][i]), nanv(A["RVOL"][i])
    if ab > 0.15:
        cumle.append(f"Son 20 mumda hacmin belirgin kısmı alıcı yönlü (alıcı baskısı %{ab * 100:.0f}).")
    elif ab < -0.15:
        cumle.append(f"Son 20 mumda satıcılar baskın (satıcı baskısı %{-ab * 100:.0f}).")
    else:
        cumle.append("Alıcı ve satıcı dengede, hacim akışında net taraf yok.")
    if rv >= 1.5:
        cumle.append(f"Hacim {'bu saat için' if ctx['mod'] == 'g' else 'son 10 güne göre'} normalin {rv:.1f} katı — hissede ilgi var.")
    elif rv < 0.7:
        cumle.append("Hacim normalin altında; kırılımlar güvenilir olmayabilir.")
    p = ctx["prof_guncel"]
    if p:
        cumle.append(f"{'Son 10 günde' if ctx['mod'] == 'g' else 'Son 12 haftada'} en çok işlem {sayi(p['poc'])} seviyesinde (POC); değer bölgesi {sayi(p['val'])}–{sayi(p['vah'])}.")
    destek = max([x for x in sev if x < c], default=None)
    direnc = min([x for x in sev if x > c], default=None)
    if destek and direnc:
        cumle.append(f"En yakın destek {sayi(destek)} (%{(c / destek - 1) * 100:.1f} aşağıda), direnç {sayi(direnc)} (%{(direnc / c - 1) * 100:.1f} yukarıda).")
    for f in formlar:
        if f["durum"] == "oluşuyor":
            yon = "yukarı" if f["yon"] > 0 else ("aşağı" if f["yon"] < 0 else "iki yöne de")
            cumle.append(f"{f['ad']} oluşuyor; {yon} kırılım izlenmeli" + (f" (kritik {sayi(f['ref'])})." if f["ref"] else "."))

    return cumle, dict(ust=_r(direnc, 4), alt=_r(destek, 4))


def gorus_yap(aktif: dict | None, tetik: dict) -> dict:
    if aktif:
        tur = aktif["tur"]
        metin = f"{tur} — güven {aktif['guven']}. Stop {sayi(aktif['stop'])}, hedef {sayi(aktif['hedef'])}."
        if aktif.get("guclu"):
            metin += (" Hacimli bölgede alıcılar gerçekten iş başında; bot bu sinyalde ısrarcı."
                      if aktif["yon"] > 0 else " Hacimli bölgede satıcılar baskın; bot bu sinyalde ısrarcı.")
        return dict(tur=tur, metin=metin)
    parca = []
    if tetik.get("ust"):
        parca.append(f"{sayi(tetik['ust'])} üstünde hacimli kapanış AL sinyali verebilir")
    if tetik.get("alt"):
        parca.append(f"{sayi(tetik['alt'])} altına sarkma SAT/çıkış sinyali olur")
    return dict(tur="BEKLE", metin="Şu an net giriş yok. " + ("; ".join(parca) + "." if parca else ""))


# ---------- Tek hisse analizi ----------
def hisse_analiz(sym, df15, gunluk, xu15, son_kapali, tam_test=False, mod="g") -> dict | None:
    if df15 is None or len(df15) < 120:
        return None
    ctx = baglam_kur(df15, gunluk, xu15, son_kapali, mod)
    A, n, df = ctx["A"], ctx["n"], ctx["df"]
    bas = 60 if tam_test else n - TEST_UFKU - 1
    sinyaller = sinyalleri_tara(ctx, bas)
    _, formlar = sinyal_bul(ctx, n - 1)
    sev = seviyeler_bul(ctx["pv"])
    i = n - 1
    fiyat = float(df["Close"].iloc[-1])
    if mod == "g":
        dun = df[df.index.date < df.index[-1].date()]["Close"]
        degisim = (fiyat / dun.iloc[-1] - 1) * 100 if len(dun) else 0.0
    else:
        degisim = (fiyat / df["Close"].iloc[-2] - 1) * 100
    son2 = df.iloc[max(0, n - (64 if mod == "g" else 15)):n]
    birikim = 0.0
    if len(son2) >= 10:
        genislik = (son2["High"].max() - son2["Low"].min()) / max(nanv(A["ATR"][i]), 1e-9)
        cvd_egim = (son2["CVD"].iloc[-1] - son2["CVD"].iloc[0]) / max(son2["Volume"].sum(), 1)
        sinir = 10 if mod == "g" else 6
        if genislik < sinir and cvd_egim > 0.05:
            birikim = cvd_egim * (sinir - genislik)
    gunluk_tl = None
    if gunluk is not None and len(gunluk) >= 5:
        gunluk_tl = float((gunluk["Close"] * gunluk["Volume"]).tail(20).mean() / 1e6)
    return dict(sym=sym, ctx=ctx, sinyaller=sinyaller, formlar=formlar, sev=sev, fiyat=fiyat, degisim=degisim,
                rv=nanv(A["RVOL"][i]), ab=nanv(A["AB"][i]), vwap=nanv(A["VWAP"][i], None), rsi=nanv(A["RSI"][i], 50),
                macd=nanv(A["MACDh"][i]), atr=nanv(A["ATR"][i]) / fiyat * 100, yapi=yapi_bul(ctx["pv"])[0],
                htf=int(ctx["htf"][i]), rs=float(ctx["rs"][i]), birikim=birikim, likidite=gunluk_tl,
                yesil_mum=bool(A["Close"][i] >= A["Open"][i]), mod=mod)


# ---------- Arayüz (HTML + JS) ----------
ARAYUZ = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#0b0c10;--s1:#121419;--s2:#181b22;--s3:#22252e;--ln:rgba(217,178,111,.16);--ln2:#23262f;
--tx:#f4efe6;--mu:#9a958c;--mu2:#66625b;--au:#d9b26f;--au2:#f0d49a;--up:#3ccf91;--dn:#f0645f;--fo:#b39ddb;
--se:'Fraunces',Georgia,serif;--mo:'IBM Plex Mono',ui-monospace,monospace}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--tx);font-family:Inter,system-ui,sans-serif;font-size:14px}
body{overflow:hidden;background:radial-gradient(120% 55% at 50% -12%,rgba(217,178,111,.10),transparent 60%),var(--bg)}
button,input,select{font-family:inherit;color:inherit}button{cursor:pointer}
.n{font-family:var(--mo);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.se{font-family:var(--se)}.up{color:var(--up)}.dn{color:var(--dn)}.mu{color:var(--mu)}.au{color:var(--au)}
#app{display:flex;flex-direction:column;height:100%}
main{flex:1;overflow-y:auto;padding:0 18px 112px;-webkit-overflow-scrolling:touch}
.ekran{animation:gir .28s ease}@keyframes gir{from{opacity:0;transform:translateY(6px)}}
/* üst */
.bas{display:flex;justify-content:space-between;align-items:center;padding:16px 0 2px;gap:10px}
.bas small{display:block;color:var(--mu);font-size:12px}
.bas h1{margin:2px 0 0;font:600 26px var(--se);letter-spacing:-.01em}
.mod{display:flex;background:var(--s1);border:1px solid var(--ln);border-radius:20px;padding:3px;flex:none}
.mod button{border:0;background:none;color:var(--mu);font-size:12px;font-weight:600;padding:7px 11px;border-radius:16px}
.mod button.on{background:linear-gradient(135deg,#e8c88a,#b8914f);color:#1a1408}
.seans{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--mu);margin-top:6px}
.seans i{width:7px;height:7px;border-radius:50%;background:var(--mu2)}.seans.acik i{background:var(--up);box-shadow:0 0 10px var(--up)}
/* hikayeler */
.hikaye{display:flex;gap:14px;overflow-x:auto;margin:16px -18px 0;padding:2px 18px 4px;scrollbar-width:none}.hikaye::-webkit-scrollbar{display:none}
.hk{flex:none;width:64px;text-align:center;cursor:pointer}
.hk .halka2{width:62px;height:62px;border-radius:50%;padding:2.5px;background:var(--s3)}
.hk .halka2.al{background:conic-gradient(from 200deg,#3ccf91,#d9b26f,#3ccf91)}.hk .halka2.sat{background:conic-gradient(from 200deg,#f0645f,#d9b26f,#f0645f)}
.hk .ic{width:100%;height:100%;border-radius:50%;background:radial-gradient(circle at 30% 25%,#2a261d,#121317);border:2px solid var(--bg);display:grid;place-items:center;font:700 12px Inter;color:var(--au2)}
.hk b{display:block;font-size:11px;margin-top:6px}.hk small{display:block;font-size:10px;font-weight:700}
/* kayan bant */
.bant{margin:14px -18px 0;border-top:1px solid var(--ln2);border-bottom:1px solid var(--ln2);overflow:hidden;white-space:nowrap;padding:9px 0;mask-image:linear-gradient(90deg,transparent,#000 8%,#000 92%,transparent)}
.bant div{display:inline-block;animation:kay 100s linear infinite}
.bant span{margin-right:22px;font-size:12px;font-family:var(--mo)}.bant b{color:var(--tx);font-weight:600;margin-right:6px;font-family:Inter}
@keyframes kay{to{transform:translateX(-50%)}}
.bolum{display:flex;align-items:baseline;justify-content:space-between;margin:28px 0 12px}
.bolum h2{margin:0;font:600 20px var(--se)}.bolum small{color:var(--mu);font-size:12px}
.bolum a{color:var(--au);font-size:12px;font-weight:600;cursor:pointer}
.acik{color:var(--mu);font-size:12.5px;margin:-6px 0 12px;line-height:1.5}
.kart{background:linear-gradient(180deg,var(--s1),#0f1115);border:1px solid var(--ln2);border-radius:22px;padding:16px}
.altin{border-color:var(--ln);box-shadow:inset 0 1px 0 rgba(240,212,154,.06)}
.tik{cursor:pointer;transition:transform .15s}.tik:active{transform:scale(.985)}
.av{width:42px;height:42px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:11.5px;flex:none;letter-spacing:.04em;color:var(--au2);background:radial-gradient(circle at 30% 25%,#2a261d,#121317);border:1px solid var(--ln)}
.satir{display:flex;align-items:center;gap:12px}
.ad{flex:1;min-width:0}.ad b{display:block;font-size:15.5px;font-weight:700}.ad small{display:block;color:var(--mu);font-size:12px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sag{text-align:right;flex:none}.sag b{display:block;font-size:15px}
.dg{display:inline-block;font-size:12px;font-weight:600;border-radius:8px;padding:3px 7px;margin-top:3px;font-family:var(--mo)}
.dg.up{background:rgba(60,207,145,.12)}.dg.dn{background:rgba(240,100,95,.12)}
.rozet{font-weight:700;font-size:11.5px;border-radius:20px;padding:5px 11px;letter-spacing:.08em;flex:none}
.rozet.al{background:rgba(60,207,145,.14);color:var(--up);border:1px solid rgba(60,207,145,.35)}
.rozet.sat{background:rgba(240,100,95,.14);color:var(--dn);border:1px solid rgba(240,100,95,.35)}
.rozet.bekle{background:var(--s3);color:var(--mu);border:1px solid var(--ln2)}
.rozet.au{background:rgba(217,178,111,.12);color:var(--au2);border:1px solid var(--ln)}
.et{display:inline-block;font-size:10.5px;font-weight:700;border-radius:6px;padding:2px 6px;margin-left:6px;vertical-align:2px}
.et.al{color:var(--up);background:rgba(60,207,145,.1)}.et.sat{color:var(--dn);background:rgba(240,100,95,.1)}
.et.fo{color:var(--fo);background:rgba(179,157,219,.12)}.et.au{color:var(--au);background:rgba(217,178,111,.12)}
.spk{flex:none}
.endeks .ust{display:flex;justify-content:space-between;align-items:flex-start}
.endeks small{color:var(--mu);font-size:11.5px;letter-spacing:.08em}
.endeks .buyuk{font:600 34px var(--se);margin-top:4px}
.rejim{font-size:11.5px;font-weight:700;padding:6px 11px;border-radius:20px;border:1px solid var(--ln2);color:var(--mu)}
.rejim.Boğa{color:var(--up);border-color:rgba(60,207,145,.35)}.rejim.Ayı{color:var(--dn);border-color:rgba(240,100,95,.35)}
.genislik{display:flex;height:4px;border-radius:9px;overflow:hidden;margin:14px 0 7px;background:var(--s3)}.genislik i{display:block;height:100%}
.uc{display:grid;grid-template-columns:repeat(3,1fr);margin-top:14px;border-top:1px solid var(--ln2);padding-top:12px}
.uc div{text-align:center}.uc div+div{border-left:1px solid var(--ln2)}
.uc small{display:block;color:var(--mu);font-size:10.5px;letter-spacing:.08em;margin-bottom:4px}.uc b{font:600 19px var(--se)}
/* bilet */
.bilet{position:relative;padding:0;overflow:hidden}.bilet .ust{padding:16px 16px 12px}
.bilet .kurulum{font-size:13px;line-height:1.45;margin-top:12px}.bilet .kurulum b{color:var(--au2);font-weight:600}
.delik{position:relative;height:0;border-top:1px dashed rgba(217,178,111,.28);margin:0 16px}
.delik::before,.delik::after{content:"";position:absolute;top:-11px;width:22px;height:22px;border-radius:50%;background:var(--bg)}
.delik::before{left:-28px}.delik::after{right:-28px}
.bilet .alt{padding:14px 16px 16px}
.merdiven{position:relative;height:46px;margin:6px 4px 4px}
.merdiven .hat{position:absolute;left:0;right:0;top:22px;height:2px;background:var(--s3)}
.merdiven .bolge{position:absolute;top:16px;height:14px;border-radius:4px;background:rgba(217,178,111,.25);border:1px solid rgba(217,178,111,.6)}
.merdiven .im{position:absolute;top:0;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;font-size:9.5px;font-weight:700;letter-spacing:.04em}
.merdiven .im i{display:block;width:8px;height:8px;border-radius:50%;margin-top:9px}
.merdiven .im.s{color:var(--dn)}.merdiven .im.s i{background:var(--dn)}
.merdiven .im.h{color:var(--up)}.merdiven .im.h i{background:var(--up);transform:rotate(45deg);border-radius:1px}
.merdiven .simdi{position:absolute;top:10px;width:2px;height:26px;background:var(--tx);transform:translateX(-1px);box-shadow:0 0 0 3px var(--s1)}
.merdiven .simdi::after{content:"ŞİMDİ";position:absolute;top:28px;left:50%;transform:translateX(-50%);font-size:9px;font-weight:700;color:var(--mu)}
.tablo{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--ln2);border:1px solid var(--ln2);border-radius:14px;overflow:hidden;margin-top:16px}
.tablo div{background:var(--s1);padding:10px 12px}
.tablo small{display:block;color:var(--mu);font-size:10.5px;letter-spacing:.06em;margin-bottom:3px}
.tablo b{font-family:var(--mo);font-size:13.5px;font-weight:600}.tablo em{font-style:normal;font-size:11.5px;margin-left:5px;font-family:var(--mo)}
.tablo .genis{grid-column:1/-1}
.durum{display:flex;gap:9px;align-items:flex-start;margin-top:12px;font-size:12.5px;line-height:1.4;padding:10px 12px;border-radius:12px;background:var(--s2)}
.durum i{flex:none;width:8px;height:8px;border-radius:50%;margin-top:5px}
.durum.bolgede i{background:var(--up);box-shadow:0 0 8px var(--up)}.durum.kacti i{background:var(--au)}.durum.dikkat i{background:var(--dn)}
.halka{position:relative;width:48px;height:48px;flex:none}.halka b{position:absolute;inset:0;display:grid;place-items:center;font:600 15px var(--se)}
.guclu{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;color:var(--au2);margin-top:8px;padding:4px 9px;border-radius:20px;background:rgba(217,178,111,.1);border:1px solid var(--ln)}
.serit{display:flex;gap:10px;overflow-x:auto;margin:0 -18px;padding:0 18px 4px;scroll-snap-type:x mandatory;scrollbar-width:none}.serit::-webkit-scrollbar{display:none}
.mb{flex:none;width:210px;scroll-snap-align:start;padding:14px}
.mb .kurulum{font-size:12px;color:var(--mu);margin:10px 0;min-height:32px;line-height:1.35}
.mb .ikili{display:flex;justify-content:space-between;font-size:11px;color:var(--mu)}.mb .ikili b{display:block;color:var(--tx);font-family:var(--mo);font-size:12.5px}
.harita{display:grid;grid-template-columns:repeat(4,1fr);gap:5px}
.harita div{border-radius:12px;padding:10px 6px;text-align:center;cursor:pointer;border:1px solid rgba(255,255,255,.04)}
.harita b{display:block;font-size:12px;font-weight:700}.harita span{font-size:11px;font-family:var(--mo)}
.sektor{display:flex;gap:6px;overflow-x:auto;margin:0 -18px;padding:0 18px;scrollbar-width:none}.sektor::-webkit-scrollbar{display:none}
.sk{flex:none;padding:10px 13px;border-radius:16px;border:1px solid var(--ln2);background:var(--s1);cursor:pointer}
.sk b{display:block;font-size:12.5px}.sk span{font-size:11px;font-family:var(--mo)}
.seg{display:flex;background:var(--s1);border:1px solid var(--ln2);border-radius:14px;padding:4px;margin-bottom:12px}
.seg button{flex:1;border:0;background:none;color:var(--mu);font-size:12.5px;font-weight:600;padding:9px 0;border-radius:10px}
.seg button.on{background:var(--s3);color:var(--au2)}
.liste{background:var(--s1);border:1px solid var(--ln2);border-radius:22px;overflow:hidden}
.liste>.satir{padding:13px 15px;border-bottom:1px solid var(--ln2);cursor:pointer}
.liste>.satir:last-child{border-bottom:0}.liste>.satir:active{background:var(--s2)}
.ara{display:flex;align-items:center;gap:8px;background:var(--s1);border:1px solid var(--ln2);border-radius:16px;padding:0 14px;margin:0 0 12px}
.ara input{flex:1;background:none;border:0;outline:0;font:500 15px Inter;padding:13px 0;text-transform:uppercase}
.ara input::placeholder{text-transform:none;color:var(--mu2)}
.chips{display:flex;gap:6px;overflow-x:auto;margin:0 -18px 12px;padding:0 18px;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}
.chip{flex:none;background:var(--s1);color:var(--mu);border:1px solid var(--ln2);border-radius:20px;padding:7px 12px;font-size:12px;font-weight:600}
.chip.on{background:rgba(217,178,111,.12);color:var(--au2);border-color:var(--ln)}
.sirala{display:flex;align-items:center;justify-content:space-between;color:var(--mu);font-size:12px;margin:0 0 10px}
select{background:var(--s1);border:1px solid var(--ln2);border-radius:10px;padding:7px 9px;font:600 12px Inter}
.bos{border:1px dashed var(--ln2);border-radius:22px;padding:28px 18px;text-align:center;color:var(--mu);line-height:1.55}
.bos b{display:block;color:var(--tx);font:600 17px var(--se);margin-bottom:4px}
.sektor-kart{margin-bottom:10px}
.akis{position:relative;height:6px;background:var(--s3);border-radius:9px;margin:10px 0 8px}
.akis i{position:absolute;top:0;height:100%;border-radius:9px}.akis::after{content:"";position:absolute;left:50%;top:-3px;width:1px;height:12px;background:var(--mu2)}
/* portföy */
.ozet3{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.ozet3 div{background:var(--s1);border:1px solid var(--ln2);border-radius:16px;padding:12px}
.ozet3 small{display:block;color:var(--mu);font-size:10.5px;letter-spacing:.06em;margin-bottom:4px}.ozet3 b{font:600 18px var(--se)}
.poz{margin-bottom:10px}
.poz .bilgi{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:12px}
.poz .bilgi div{background:var(--s2);border-radius:12px;padding:8px 10px}.poz .bilgi small{display:block;color:var(--mu);font-size:10px}.poz .bilgi b{font-family:var(--mo);font-size:13px}
.dugmeler{display:flex;gap:8px;margin-top:12px}
.dugme{flex:1;border:1px solid var(--ln2);background:var(--s2);border-radius:14px;padding:11px;font-size:13px;font-weight:600}
.dugme.ana{background:linear-gradient(135deg,#e8c88a,#b8914f);color:#1a1408;border:0}
.dugme.kirmizi{color:var(--dn)}
/* nav */
nav.alt{position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));display:flex;background:rgba(18,20,25,.88);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid var(--ln);border-radius:24px;padding:5px;box-shadow:0 10px 30px rgba(0,0,0,.5)}
nav.alt button{flex:1;background:none;border:0;color:var(--mu2);font-size:10px;font-weight:600;display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px 0;border-radius:18px;position:relative}
nav.alt button svg{width:21px;height:21px}nav.alt button.on{color:var(--au2);background:rgba(217,178,111,.1)}
nav.alt .rz{position:absolute;top:4px;left:calc(50% + 6px);background:var(--au);color:#1a1408;font-size:9.5px;font-weight:700;border-radius:9px;padding:1px 5px}
/* alt sayfalar */
.perde{position:fixed;inset:0;background:rgba(0,0,0,.55);opacity:0;pointer-events:none;transition:opacity .25s;z-index:15}.perde.ac{opacity:1;pointer-events:auto}
#detay{position:fixed;left:0;right:0;bottom:0;top:18px;background:var(--bg);border-radius:26px 26px 0 0;border-top:1px solid var(--ln);display:flex;flex-direction:column;transform:translateY(105%);transition:transform .34s cubic-bezier(.2,.8,.2,1);z-index:20;overflow:hidden}
#detay.ac{transform:none}
.tutamak{width:42px;height:5px;border-radius:9px;background:var(--s3);margin:9px auto 0}
.dust{display:flex;align-items:center;gap:10px;padding:8px 16px 4px}
.yuv{background:var(--s1);border:1px solid var(--ln2);width:40px;height:40px;border-radius:50%;font-size:17px;display:grid;place-items:center;flex:none;text-decoration:none;color:var(--tx)}
.yuv.on{color:var(--au);border-color:var(--ln)}
#dicerik{flex:1;overflow-y:auto;padding-bottom:40px}
.dkah{padding:4px 18px 0}.dkah h1{margin:0;font:600 30px var(--se)}.dkah small{color:var(--mu);font-size:12px}
.dkah .fiyat{display:flex;align-items:baseline;gap:10px;margin-top:6px}.dkah .fiyat b{font:600 40px var(--se)}
.cipler{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.cipler span{font-size:11.5px;background:var(--s1);border:1px solid var(--ln2);border-radius:20px;padding:5px 10px;color:var(--mu)}.cipler span b{color:var(--tx);font-family:var(--mo);font-weight:600}
.karar{margin:16px 18px 0;border-radius:18px;padding:14px;display:flex;gap:12px;align-items:flex-start;border:1px solid var(--ln2);background:var(--s1)}
.karar.AL{border-color:rgba(60,207,145,.35);background:linear-gradient(120deg,rgba(60,207,145,.1),var(--s1) 65%)}
.karar.SAT{border-color:rgba(240,100,95,.35);background:linear-gradient(120deg,rgba(240,100,95,.1),var(--s1) 65%)}
.karar p{margin:0;font-size:13.5px;line-height:1.5}.karar small{display:block;color:var(--au);font-size:10.5px;font-weight:700;letter-spacing:.12em;margin-bottom:4px}
.legend{padding:14px 18px 0;height:30px;font-size:11px;color:var(--mu);white-space:nowrap;overflow:hidden}.legend b{color:var(--tx)}
#grafik{height:310px}
.gsec{display:flex;gap:6px;padding:8px 18px 0;overflow-x:auto;scrollbar-width:none}.gsec::-webkit-scrollbar{display:none}
.ayr{width:1px;background:var(--ln2);flex:none;margin:3px 2px}
.dp{padding:0 18px}
.adimlar{counter-reset:a;display:flex;flex-direction:column;gap:10px;margin-top:14px}
.adimlar div{display:flex;gap:11px;font-size:13px;line-height:1.5}
.adimlar div::before{counter-increment:a;content:counter(a);flex:none;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font:600 11px var(--mo);color:var(--au2);border:1px solid var(--ln);margin-top:1px}
.lot{display:flex;justify-content:space-between;align-items:center;margin-top:14px;padding:12px 14px;border-radius:14px;background:rgba(217,178,111,.07);border:1px solid var(--ln)}
.lot small{display:block;color:var(--mu);font-size:11px}.lot b{font:600 20px var(--se);color:var(--au2)}
.neden{display:flex;flex-direction:column;gap:8px}.neden div{font-size:13px;display:flex;gap:10px;line-height:1.4}
.neden .p::before{content:"✓";color:var(--up);font-weight:700}.neden .x::before{content:"✕";color:var(--dn);font-weight:700}
.yorum{display:flex;flex-direction:column;gap:12px}
.yorum div{display:flex;gap:11px;font-size:13.5px;line-height:1.55}.yorum div::before{content:"";flex:none;width:5px;height:5px;border-radius:50%;background:var(--au);margin-top:9px}
.izgara{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.izgara div{background:var(--s1);border:1px solid var(--ln2);border-radius:16px;padding:13px}
.izgara small{display:block;color:var(--mu);font-size:11px;margin-bottom:5px}.izgara b{font:600 19px var(--se)}
.izgara i{display:block;font-style:normal;color:var(--mu2);font-size:11px;margin-top:3px}
.profil{display:flex;flex-direction:column;gap:2px}
.profil div{display:flex;align-items:center;gap:8px;font-size:10.5px;font-family:var(--mo);color:var(--mu2)}
.profil span{width:60px;text-align:right;flex:none}.profil i{display:block;height:9px;border-radius:3px;background:var(--s3)}
.profil .va i{background:rgba(217,178,111,.35)}.profil .poc i{background:var(--au)}.profil .poc span{color:var(--au)}
.profil .simdi span{color:var(--tx);font-weight:600}.profil .simdi::after{content:"◂ fiyat";color:var(--tx);font-size:10px}
.say4{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;text-align:center;margin-bottom:12px}
.say4 div{background:var(--s1);border:1px solid var(--ln2);border-radius:16px;padding:11px 4px}
.say4 small{display:block;color:var(--mu);font-size:10px;letter-spacing:.06em;margin-bottom:3px}.say4 b{font:600 20px var(--se)}
.bar{flex:1;height:5px;background:var(--s3);border-radius:9px;overflow:hidden}.bar i{display:block;height:100%;border-radius:9px}
.form-ayar{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.form-ayar label{background:var(--s1);border:1px solid var(--ln2);border-radius:16px;padding:12px;display:block}
.form-ayar small{display:block;color:var(--mu);font-size:11px;margin-bottom:6px}
.form-ayar input,.form-ayar select{width:100%;background:none;border:0;outline:0;font:600 18px var(--se);padding:0}
.form-ayar .genis{grid-column:1/-1}
input[type=range]{width:100%;accent-color:#d9b26f}
.karne{display:grid;grid-template-columns:1.6fr .6fr .7fr .6fr;gap:0;font-size:12.5px}
.karne div{padding:10px 8px;border-bottom:1px solid var(--ln2)}.karne .bas2{color:var(--mu);font-size:10.5px;letter-spacing:.06em}
.not{color:var(--mu2);font-size:11.5px;line-height:1.55;margin-top:12px}
.uyari{color:var(--mu2);font-size:11px;text-align:center;margin:28px 0 6px}
#form{position:fixed;left:0;right:0;bottom:0;background:var(--s1);border-radius:26px 26px 0 0;border-top:1px solid var(--ln);padding:8px 18px calc(24px + env(safe-area-inset-bottom));transform:translateY(105%);transition:transform .3s cubic-bezier(.2,.8,.2,1);z-index:30}
#form.ac{transform:none}
.toast{position:fixed;left:50%;bottom:100px;transform:translate(-50%,20px);background:var(--au2);color:#1a1408;font-weight:600;font-size:13px;padding:10px 16px;border-radius:20px;opacity:0;transition:all .3s;z-index:40;pointer-events:none}
.toast.ac{opacity:1;transform:translate(-50%,0)}
</style></head><body>
<div id="app">
  <main id="ekran"></main>
  <nav class="alt">
    <button data-e="ana"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>Ana Sayfa</button>
    <button data-e="plan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M4 7h16v4a2 2 0 000 4v4H4v-4a2 2 0 000-4z"/><path d="M14 7v12" stroke-dasharray="2 2"/></svg>Planlar<span class="rz" id="rz" hidden></span></button>
    <button data-e="piyasa"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/></svg>Piyasa</button>
    <button data-e="portfoy"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8 7V5a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>Portföy</button>
    <button data-e="profil"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/></svg>Profil</button>
  </nav>
</div>
<div class="perde" id="perde"></div>
<div id="detay">
  <div class="tutamak"></div>
  <div class="dust"><button class="yuv" id="geri">⌄</button><div style="flex:1"></div>
    <button class="yuv" id="dyildiz">☆</button><a class="yuv" id="tv" target="_blank" rel="noopener" title="TradingView'de aç">↗</a></div>
  <div id="dicerik">
    <div class="dkah" id="dkah"></div>
    <div id="dkarar"></div>
    <div class="legend n" id="legend"></div>
    <div id="grafik"></div>
    <div class="gsec" id="gsec"></div>
    <div class="dp">
      <div id="dplan"></div>
      <div class="seg" id="sekmeler" style="margin-top:22px"><button data-s="analiz">Analiz</button><button data-s="hacim">Hacim</button><button data-s="teknik">Teknik</button><button data-s="gecmis">Geçmiş</button></div>
      <div id="sekme"></div>
      <div class="uyari">Veri yaklaşık 15 dk gecikmeli · Yatırım tavsiyesi değildir</div>
    </div>
  </div>
</div>
<div id="form"></div>
<div class="toast" id="toast"></div>
<script type="application/json" id="veri">__VERI__</script>
<script>
const V=JSON.parse(document.getElementById('veri').textContent);
const iki=v=>String(v).padStart(2,'0');
const tarihYaz=(t,g)=>{const d=new Date(t*1000);return g?`${iki(d.getUTCDate())}.${iki(d.getUTCMonth()+1)} ${iki(d.getUTCHours())}:${iki(d.getUTCMinutes())}`:`${iki(d.getUTCDate())}.${iki(d.getUTCMonth()+1)}.${d.getUTCFullYear()}`};
const coz=(o,g)=>{if(!o)return;let t=o.m.t0;o.m=o.m.d.map(x=>{t+=x[0]*60;return[t,x[1]/100,x[2]/100,x[3]/100,x[4]/100,x[5]]});
  o.sin=o.sin.map(a=>({t:a[0],yon:a[1],tur:a[1]>0?'AL':'SAT',guven:a[2],guclu:!!a[3],fiyat:a[4],sonuc:a[5],getiri:a[6],saat:tarihYaz(a[0],g)}))};
V.hisseler.forEach(h=>{coz(h.g,true);coz(h.w,false)});
const H=Object.fromEntries(V.hisseler.map(h=>[h.s,h]));
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tl=(x,d=2)=>x==null||isNaN(x)?'—':Number(x).toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d});
const yz=(x,d=2)=>x==null||isNaN(x)?'—':(x>=0?'+':'−')+tl(Math.abs(x),d)+'%';
const yon=x=>x>=0?'up':'dn';
const D={get(k,d){try{const v=localStorage.getItem('rv_'+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem('rv_'+k,JSON.stringify(v))}catch(e){}}};
let fav=new Set(D.get('fav',[]));
const ayar=Object.assign({sermaye:100000,risk:1,guven:55,lik:30},D.get('ayar',{}));
let M=D.get('mod','g');
const X=h=>h[M];
const birim=()=>M==='g'?'mum':'gün';
const av=a=>`<div class="av">${esc(a.slice(0,3))}</div>`;
const gRenk=g=>g>=70?'var(--up)':g>=55?'var(--au)':'var(--mu)';
const gAd=g=>g>=70?'Güçlü':g>=55?'Orta':'Zayıf';
const ne=s=>s.once===0?(M==='g'?'son mumda':'bugün'):s.once+' '+birim()+' önce';
function toast(m){const t=$('#toast');t.textContent=m;t.classList.add('ac');setTimeout(()=>t.classList.remove('ac'),2200)}
function spark(d,w=70,h=26,r){if(!d||d.length<2)return'';const mn=Math.min(...d),mx=Math.max(...d),k=mx-mn||1;
  const p=d.map((v,i)=>`${(i/(d.length-1)*w).toFixed(1)},${(h-2-(v-mn)/k*(h-4)).toFixed(1)}`).join(' ');
  const c=r||(d[d.length-1]>=d[0]?'var(--up)':'var(--dn)');
  return `<svg class="spk" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><polyline points="${p}" fill="none" stroke="${c}" stroke-width="1.5" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>`}
const genis=s=>s.replace('class="spk"','class="spk" style="width:100%"');
const kap=o=>o.m.slice(-32).map(m=>m[4]);
function halka(g){const r=20,c=2*Math.PI*r;return `<div class="halka"><svg width="48" height="48"><circle cx="24" cy="24" r="${r}" fill="none" stroke="var(--s3)" stroke-width="3"/><circle cx="24" cy="24" r="${r}" fill="none" stroke="${gRenk(g)}" stroke-width="3" stroke-linecap="round" stroke-dasharray="${c*g/100} ${c}" transform="rotate(-90 24 24)"/></svg><b>${g}</b></div>`}
function isi(d){const a=Math.min(Math.abs(d||0)/4,1)*.5+.08;return d>=0?`rgba(60,207,145,${a})`:`rgba(240,100,95,${a})`}

// ---------- veri görünümü (mod + ayarlar) ----------
let liste_,aktifler;
function hazirla(){
  liste_=V.hisseler.filter(h=>X(h)&&(h.lik||0)>=ayar.lik);
  liste_.forEach(h=>{const o=X(h);const a=o.akl.filter(s=>s.guven>=ayar.guven);o.akt=a.length?a[a.length-1]:null;o.sinF=o.sin.filter(s=>s.guven>=ayar.guven)});
  aktifler=liste_.filter(h=>X(h).akt).sort((a,b)=>(X(b).akt.guclu-X(a).akt.guclu)||(X(b).akt.guven-X(a).akt.guven)||(X(a).akt.once-X(b).akt.once));
  $('#rz').hidden=!aktifler.length;$('#rz').textContent=aktifler.length}
function gorus(h){const o=X(h),s=o.akt;
  if(s){let m=`${s.tur} — güven ${s.guven}. Giriş ${tl(s.giris_alt)}–${tl(s.giris_ust)}, stop ${tl(s.stop)}, ilk hedef ${tl(s.hedef)}.`;
    if(s.guclu)m+=s.yon>0?' Hacimli bölgede alıcılar gerçekten iş başında; bot bu sinyalde ısrarcı.':' Hacimli bölgede satıcılar baskın; bot bu sinyalde ısrarcı.';return{tur:s.tur,metin:m}}
  const p=[];if(o.tetik.ust)p.push(`${tl(o.tetik.ust)} üstünde hacimli kapanış AL sinyali verebilir`);if(o.tetik.alt)p.push(`${tl(o.tetik.alt)} altına sarkma SAT/çıkış sinyali olur`);
  return{tur:'BEKLE',metin:'Şu an net giriş yok. '+(p.length?p.join('; ')+'.':'')}}

// ---------- işlem planı bileti ----------
function merdiven(s,p){const v=[s.stop,s.giris_alt,s.giris_ust,p,s.hedef,s.hedef2,s.hedef3].filter(x=>x!=null);
  const lo=Math.min(...v),hi=Math.max(...v),k=(hi-lo)||1,x=f=>((f-lo)/k*92+4).toFixed(2)+'%';
  const ga=Math.min(s.giris_alt,s.giris_ust),gu=Math.max(s.giris_alt,s.giris_ust);
  return `<div class="merdiven"><div class="hat"></div><div class="bolge" style="left:${x(ga)};width:calc(${x(gu)} - ${x(ga)})"></div>
   <div class="im s" style="left:${x(s.stop)}">STOP<i></i></div>${[s.hedef,s.hedef2,s.hedef3].map((h,i)=>`<div class="im h" style="left:${x(h)}">H${i+1}<i></i></div>`).join('')}
   <div class="simdi" style="left:${x(p)}"></div></div>`}
function lotHesap(s){const g=(s.giris_alt+s.giris_ust)/2,r=Math.abs(g-s.stop);if(!r)return null;
  let lot=Math.floor(ayar.sermaye*ayar.risk/100/r);lot=Math.min(lot,Math.floor(ayar.sermaye/g));return{lot,tutar:lot*g,zarar:lot*r,giris:g}}
function bilet(h,tam){const o=X(h),s=o.akt,al=s.yon>0,sure=M==='g'?`≈ ${tl(s.kalan/4,0)} saat`:`≈ ${tl(s.kalan/5,0)} hafta`;
  const ust=`<div class="ust"><div class="satir">${av(h.s)}<div class="ad"><b class="se" style="font-size:19px">${h.s}</b><small>${s.saat} · ${ne(s)} · ${M==='g'?'gün içi':'swing'}</small></div>
    <span class="rozet ${al?'al':'sat'}">${s.tur}</span>${halka(s.guven)}</div>
    ${s.guclu?`<div class="guclu">◆ Güçlü ${al?'alıcı':'satıcı'} izi — bot ısrarcı</div>`:''}
    <div class="kurulum">${s.sebepler.map((x,i)=>i===0?`<b>${esc(x)}</b>`:esc(x)).join(' · ')}</div></div>`;
  const alt=`<div class="alt">${merdiven(s,o.p)}<div class="tablo">
      <div class="genis"><small>GİRİŞ ARALIĞI</small><b class="au">${tl(s.giris_alt)} – ${tl(s.giris_ust)}</b><em class="mu">şimdi ${tl(o.p)}</em></div>
      <div><small>STOP</small><b class="dn">${tl(s.stop)}</b><em class="dn">−${tl(s.risk)}%</em></div><div><small>RİSK / KAZANÇ</small><b>1 : ${tl(s.rk,1)}</b></div>
      <div><small>HEDEF 1</small><b class="up">${tl(s.hedef)}</b><em class="up">+${tl(s.pot[0])}%</em></div><div><small>HEDEF 2</small><b class="up">${tl(s.hedef2)}</b><em class="up">+${tl(s.pot[1])}%</em></div>
      <div><small>HEDEF 3</small><b class="up">${tl(s.hedef3)}</b><em class="up">+${tl(s.pot[2])}%</em></div><div><small>KALAN SÜRE</small><b>${s.kalan} ${birim()}</b><em class="mu">${sure}</em></div></div>
    <div class="durum ${s.durum.kod}"><i></i><span>${esc(s.durum.metin)}${s.en_iyi>0?` · sinyalden beri en iyi ${yz(s.en_iyi)}`:''}</span></div>${tam?planAdim(h):''}</div>`;
  return `<div class="kart bilet altin${tam?'':' tik'}" ${tam?'':`data-h="${h.s}"`}>${ust}<div class="delik"></div>${alt}</div>`}
function planAdim(h){const s=X(h).akt,al=s.yon>0,L=lotHesap(s),kap=M==='g'?'15 dakikalık mum':'günlük kapanış';
  const a=al?[`<b>${tl(s.giris_alt)} – ${tl(s.giris_ust)}</b> aralığında kademeli al. Fiyat aralığın üstündeyse kovalama, geri çekilmesini bekle.`,
    `Stop <b class="dn">${tl(s.stop)}</b>. ${kap} bu seviyenin altında kapanırsa plan geçersiz, çık.`,
    `<b class="up">${tl(s.hedef)}</b> (H1) gelince pozisyonun yarısını sat, stopu giriş fiyatına çek — artık risksiz.`,
    `Kalanı <b class="up">${tl(s.hedef2)}</b> (H2) ve <b class="up">${tl(s.hedef3)}</b> (H3) için tut; H2'de stopu H1'e taşı.`,
    `Plan ${s.kalan} ${birim()} içinde hedefe gitmezse pozisyonu küçült; zamanla zayıflayan sinyal güç kaybeder.`]
   :[`Elinde ${h.s} varsa <b>${tl(s.giris_alt)} – ${tl(s.giris_ust)}</b> aralığında satarak çık ya da azalt.`,`Fiyat <b class="dn">${tl(s.stop)}</b> üstünde kapanırsa satış sinyali geçersiz olur.`,
    `Düşüşün <b>${tl(s.hedef)}</b>, <b>${tl(s.hedef2)}</b> ve <b>${tl(s.hedef3)}</b> seviyelerine uzanması beklenir; buralar yeniden alım için izlenebilir.`,`Midas'ta açığa satış yapılamadığı için SAT, elindeki pozisyondan çıkış sinyalidir.`];
  return `<div class="adimlar">${a.map(x=>`<div><span>${x}</span></div>`).join('')}</div>`+
   (al&&L&&L.lot>0?`<div class="lot"><div><small>Sermaye ${tl(ayar.sermaye,0)} TL · risk %${tl(ayar.risk,1)}</small><b>${tl(L.lot,0)} lot</b></div><div style="text-align:right"><small>Tutar ≈ ${tl(L.tutar,0)} TL</small><small>Stop olursa ≈ −${tl(L.zarar,0)} TL</small></div></div>`:'')+
   (al?`<div class="dugmeler"><button class="dugme ana" data-gir="gercek">İşleme girdim</button><button class="dugme" data-gir="kagit">Kağıt üstünde al</button></div>`:'')}
function miniBilet(h){const o=X(h),s=o.akt;return `<div class="kart mb tik altin" data-h="${h.s}"><div class="satir">${av(h.s)}<div class="ad"><b>${h.s}</b><small>${ne(s)}</small></div><span class="rozet ${s.yon>0?'al':'sat'}">${s.tur}</span></div>
  <div class="kurulum">${s.guclu?'◆ ':''}${esc(s.sebepler[0])}</div>
  <div class="ikili"><div>Giriş<b class="au">${tl(s.giris_alt)}–${tl(s.giris_ust)}</b></div><div style="text-align:right">H1<b class="up">+${tl(s.pot[0])}%</b></div></div>
  <div class="ikili" style="margin-top:8px"><div>Stop<b class="dn">−${tl(s.risk)}%</b></div><div style="text-align:right">Güven<b>${s.guven}</b></div></div></div>`}
function etiket(h){const o=X(h);if(o.akt)return `<span class="et ${o.akt.yon>0?'al':'sat'}">${o.akt.tur} ${o.akt.guven}</span>`+(o.akt.guclu?'<span class="et au">◆</span>':'');
  const f=o.form.find(f=>f.durum==='oluşuyor');return f?`<span class="et fo">${esc(f.ad)}</span>`:''}
function satir(h,alt){const o=X(h);return `<div class="satir" data-h="${h.s}">${av(h.s)}<div class="ad"><b>${h.s}${etiket(h)}</b><small>${alt||h.sek}</small></div>
  ${spark(kap(o))}<div class="sag n"><b>${tl(o.p)}</b><span class="dg ${yon(o.d)}">${yz(o.d)}</span></div></div>`}

function yenile(){toast('Yenileniyor…');try{window.parent.location.reload()}catch(e){location.reload()}}
if(V.seans)setTimeout(()=>{if(!document.hidden)yenile()},5*60*1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-ACILIS>5*60*1000)yenile()});
const ACILIS=Date.now();
function baslik(alt,ust,mod=true){return `<div class="bas"><div><small>${alt}</small><h1>${ust}</h1></div>${mod?`<div class="mod"><button data-mod="g" class="${M==='g'?'on':''}">Gün içi</button><button data-mod="w" class="${M==='w'?'on':''}">Swing</button></div>`:''}</div>
  <div class="seans ${V.seans?'acik':''}"><i></i>${V.seans?'Seans açık':'Seans kapalı'} · ${V.guncelleme} · ${M==='g'?'15 dk grafik':'günlük grafik'}<span data-yenile="1" style="margin-left:auto;color:var(--au);font-weight:600;cursor:pointer">↻ Yenile</span></div>`}

// ---------- ANA SAYFA ----------
let liste=D.get('liste','hacim');
function ekranAna(){const sa=new Date().getHours(),sel=sa<12?'Günaydın':sa<18?'İyi günler':'İyi akşamlar';
  const b=V.bist,yuk=liste_.filter(h=>X(h).d>0).length,dus=liste_.filter(h=>X(h).d<0).length,top=yuk+dus||1;
  const yeni=aktifler.filter(h=>X(h).akt.once<=(M==='g'?3:1)).slice(0,14);
  let x=baslik(sel,'Radar');
  if(yeni.length)x+=`<div class="hikaye">${yeni.map(h=>{const s=X(h).akt;return `<div class="hk" data-h="${h.s}"><div class="halka2 ${s.yon>0?'al':'sat'}"><div class="ic">${h.s.slice(0,3)}</div></div><b>${h.s}</b><small class="${s.yon>0?'up':'dn'}">${s.tur} ${s.guven}</small></div>`}).join('')}</div>`;
  const ls=[...liste_].sort((a,b)=>(b.lik||0)-(a.lik||0));
  const bant=ls.slice(0,30).map(h=>`<span><b>${h.s}</b>${tl(X(h).p)} <span class="${yon(X(h).d)}">${yz(X(h).d)}</span></span>`).join('');
  x+=`<div class="bant"><div>${bant}${bant}</div></div>`;
  const sp=b?(M==='g'?b.spark:b.spark_w):null;
  x+=`<div class="kart endeks altin" style="margin-top:16px"><div class="ust"><div><small>BIST 100</small><div class="buyuk">${b?tl(b.p,0):'—'}</div>${b?`<span class="dg ${yon(b.d)}">${yz(b.d)}</span>`:''}</div><span class="rejim ${b?b.rejim:''}">${b?b.rejim+' piyasası':''}</span></div>
    <div style="margin-top:10px">${sp?genis(spark(sp,320,56,'var(--au)')):''}</div>
    <div class="genislik"><i style="width:${yuk/top*100}%;background:var(--up)"></i><i style="width:${dus/top*100}%;background:var(--dn)"></i></div>
    <div style="display:flex;justify-content:space-between;font-size:12px" class="mu"><span><b class="up">${yuk}</b> yükselen</span><span><b class="dn">${dus}</b> düşen</span></div>
    <div class="uc"><div><small>TARANAN</small><b>${liste_.length}</b></div><div><small>AÇIK PLAN</small><b class="au">${aktifler.length}</b></div><div><small>BOT 30G</small><b class="${yon(V.bot[M].getiri||0)}">${V.bot[M].n?yz(V.bot[M].getiri,1):'—'}</b></div></div></div>`;
  x+=`<div class="bolum"><h2>Günün işlem planı</h2><a data-git="plan">Tümü ›</a></div>`;
  x+=aktifler[0]?bilet(aktifler[0],false):`<div class="bos"><b>Şu an net plan yok</b>Bot güven ${ayar.guven} üstü bir kurulum bulamadı. Sabır da bir pozisyondur.</div>`;
  const dg=aktifler.slice(1,9);if(dg.length)x+=`<div class="bolum"><h2>Diğer fırsatlar</h2><small>${aktifler.length-1} plan</small></div><div class="serit">${dg.map(miniBilet).join('')}</div>`;
  if(M==='g'&&V.sektorler.length){const s=V.sektorler.filter(x=>x.ad!=='Diğer');x+=`<div class="bolum"><h2>Para nereye akıyor?</h2><a data-git="sektor">Sektörler ›</a></div>
    <div class="sektor">${s.map(k=>`<div class="sk" data-sek="${esc(k.ad)}"><b>${esc(k.ad)}</b><span class="${yon(k.akis)}">${k.akis>=0?'▲ giriş':'▼ çıkış'} %${tl(Math.abs(k.akis*100),0)}</span></div>`).join('')}</div>`}
  x+=`<div class="bolum"><h2>Piyasa ısısı</h2><small>en likit 24</small></div><div class="harita">${ls.slice(0,24).map(h=>`<div data-h="${h.s}" style="background:${isi(X(h).d)}"><b>${h.s}</b><span>${yz(X(h).d,1)}</span></div>`).join('')}</div>`;
  const L={hacim:['Hacim',`Normalin 2 katı üstü hacimle yükselenler.`,h=>(X(h).rv||0)>=2&&X(h).yesil,h=>X(h).rv,h=>`Hacim ${tl(X(h).rv,1)}x · alıcı %${tl((X(h).ab||0)*100,0)}`],
    alici:['Alıcı','Hacmin çoğu alıcı yönlü.',h=>(X(h).ab||0)>.2&&(M==='w'||(X(h).vw&&X(h).p>X(h).vw)),h=>X(h).ab,h=>`Alıcı baskısı %${tl(X(h).ab*100,0)}`],
    birikim:['Birikim','Fiyat sıkışırken alıcı hacmi birikiyor.',h=>(X(h).birikim||0)>0,h=>X(h).birikim,h=>`Sıkışma + alıcı akışı · RSI ${tl(X(h).rsi,0)}`],
    kirilim:['Kırılım','Direncin %1,5 yakınında, alıcılar önde.',h=>X(h).tetik.ust&&X(h).tetik.ust/X(h).p-1<.015&&(X(h).ab||0)>0,h=>-(X(h).tetik.ust/X(h).p),h=>`Direnç ${tl(X(h).tetik.ust)} · %${tl((X(h).tetik.ust/X(h).p-1)*100,1)} uzakta`]};
  const sec=L[liste],ll=liste_.filter(sec[2]).sort((a,b)=>sec[3](b)-sec[3](a)).slice(0,8);
  x+=`<div class="bolum"><h2>Akıllı listeler</h2></div><div class="seg">${Object.keys(L).map(k=>`<button data-l="${k}" class="${liste===k?'on':''}">${L[k][0]}</button>`).join('')}</div><div class="acik">${sec[1]}</div>`+
    (ll.length?`<div class="liste">${ll.map(h=>satir(h,sec[4](h))).join('')}</div>`:`<div class="bos">Şu an bu listede hisse yok</div>`);
  return x}

// ---------- PLANLAR ----------
let pf=D.get('pf','tumu');
function ekranPlan(){let l=[...aktifler];
  if(pf==='al')l=l.filter(h=>X(h).akt.yon>0);if(pf==='sat')l=l.filter(h=>X(h).akt.yon<0);if(pf==='guclu')l=l.filter(h=>X(h).akt.guclu);if(pf==='bolgede')l=l.filter(h=>X(h).akt.durum.kod==='bolgede');
  const b=(k,a)=>`<button data-pf="${k}" class="${pf===k?'on':''}">${a}</button>`;
  return baslik('Botun açık işlem planları','Planlar')+`<div class="seg" style="margin-top:16px">${b('tumu','Tümü')}${b('bolgede','Girişte')}${b('guclu','◆ Güçlü')}${b('al','AL')}${b('sat','SAT')}</div>
   <div class="acik">Her plan hedefe ya da stopa ulaşana kadar (en fazla ${V.ufuk} ${birim()}) açık kalır. Adım adım plan ve lot önerisi için karta dokun.</div>`+
   (l.length?l.map(h=>`<div style="margin-bottom:12px">${bilet(h,false)}</div>`).join(''):`<div class="bos"><b>Bu filtrede plan yok</b>Güven eşiği ${ayar.guven}; Profil'den değiştirebilirsin.</div>`)}

// ---------- PİYASA ----------
let pg=D.get('pg','hisse'),mf=D.get('mf','tumu'),ms=D.get('ms','degisim'),q='',sekSec=null;
function piyasaListe(){let l=liste_.filter(h=>!q||h.s.includes(q));if(sekSec)l=l.filter(h=>h.sek===sekSec);
  if(mf==='plan')l=l.filter(h=>X(h).akt);if(mf==='hacim')l=l.filter(h=>(X(h).rv||0)>=1.5);if(mf==='alici')l=l.filter(h=>(X(h).ab||0)>.15);
  if(mf==='form')l=l.filter(h=>X(h).form.some(f=>f.durum==='oluşuyor'));if(mf==='fav')l=l.filter(h=>fav.has(h.s));
  const k={degisim:h=>X(h).d||0,hacim:h=>X(h).rv||0,alici:h=>X(h).ab||0,guven:h=>X(h).akt?X(h).akt.guven:-1,likidite:h=>h.lik||0}[ms];
  if(k)l.sort((a,b)=>k(b)-k(a));else l.sort((a,b)=>a.s.localeCompare(b.s));return l}
function piyasaIcerik(){const l=piyasaListe();if(!l.length)return `<div class="bos">Sonuç yok</div>`;
  if(pg==='harita')return `<div class="harita">${l.map(h=>`<div data-h="${h.s}" style="background:${isi(X(h).d)}"><b>${h.s}</b><span>${yz(X(h).d,1)}</span></div>`).join('')}</div>`;
  return `<div class="liste">${l.slice(0,300).map(h=>satir(h,`${h.sek} · hacim ${tl(X(h).rv,1)}x · alıcı %${tl((X(h).ab||0)*100,0)}`)).join('')}</div>`}
function ekranPiyasa(){const b=(k,a)=>`<button data-pg="${k}" class="${pg===k?'on':''}">${a}</button>`;
  let x=baslik(`${liste_.length} likit hisse · ${V.taranan} hisse tarandı`,'Piyasa')+`<div class="seg" style="margin-top:16px">${b('hisse','Hisseler')}${b('sektor','Sektörler')}${b('harita','Isı haritası')}</div>`;
  if(pg==='sektor'){const s=V.sektorler;
    if(M==='w')x+=`<div class="acik">Sektör para akışı gün içi verilerle hesaplanır.</div>`;
    return x+`<div class="acik">Bugün hangi sektöre para giriyor? Akış: sektördeki hisselerde işlem hacminin alıcı yönlü payı.</div>`+s.map(k=>`<div class="kart sektor-kart"><div class="satir"><div class="ad"><b class="se" style="font-size:17px">${esc(k.ad)}</b><small>${k.n} hisse · ort. ${yz(k.d)}</small></div>
      <div class="sag"><b class="${yon(k.akis)}">${k.akis>=0?'Para girişi':'Para çıkışı'}</b><small class="mu n">%${tl(Math.abs(k.akis*100),0)} · ${tl(Math.abs(k.tl),0)} mn TL</small></div></div>
      <div class="akis"><i style="${k.akis>=0?`left:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--up)`:`right:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--dn)`}"></i></div>
      <div class="chips" style="margin:0 -16px;padding:0 16px">${k.hisseler.map(s=>H[s]&&X(H[s])?`<button class="chip" data-h="${s}">${s} <span class="${yon(X(H[s]).d)}">${yz(X(H[s]).d,1)}</span></button>`:'').join('')}</div></div>`).join('')}
  const c=(k,a)=>`<button class="chip${mf===k?' on':''}" data-mf="${k}">${a}</button>`,o=(k,a)=>`<option value="${k}"${ms===k?' selected':''}>${a}</option>`;
  return x+`<div class="ara"><span class="au">⌕</span><input id="q" placeholder="Hisse ara" value="${esc(q)}" autocomplete="off"></div>
   ${sekSec?`<div class="chips"><button class="chip on" data-sektemizle="1">${esc(sekSec)} ✕</button></div>`:''}
   <div class="chips">${c('tumu','Tümü')}${c('plan','Planı olan')}${c('hacim','Hacimli')}${c('alici','Alıcılı')}${c('form','Formasyon')}${c('fav','★ Favori')}</div>
   <div class="sirala"><span>${pg==='harita'?'Renk: günlük değişim':'Sırala'}</span><select id="ms">${o('degisim','Değişim')}${o('hacim','Hacim')}${o('alici','Alıcı baskısı')}${o('guven','Güven')}${o('likidite','İşlem hacmi')}${o('ad','A-Z')}</select></div>
   <div id="pliste">${piyasaIcerik()}</div>`}

// ---------- PORTFÖY (işlem günlüğü + kağıt işlem + bot) ----------
let poz=D.get('poz',[]),pt=D.get('pt','gercek');
function degerlendir(p){const h=H[p.s],o=h&&h[p.mod];const sonuc={durum:'açık',fiyat:o?o.p:p.giris,realize:0,kalanLot:p.lot,h1:false};
  if(p.kap){sonuc.durum='kapandı';sonuc.fiyat=p.kap.fiyat;sonuc.kalanLot=0;sonuc.realize=(p.kap.fiyat-p.giris)*p.lot+(p.kap.realize||0);return sonuc}
  if(!o)return sonuc;let stop=p.stop,h1=false,realize=0,lot=p.lot;
  for(const m of o.m){if(m[0]<=p.t)continue;
    if(m[3]<=stop){realize+=(stop-p.giris)*lot;lot=0;sonuc.durum=h1?'H1 + başabaş':'stop';sonuc.fiyat=stop;break}
    if(!h1&&m[2]>=p.h[0]){h1=true;const yari=Math.floor(lot/2);realize+=(p.h[0]-p.giris)*yari;lot-=yari;stop=p.giris}
    if(h1&&m[2]>=p.h[1]){realize+=(p.h[1]-p.giris)*lot;lot=0;sonuc.durum='H2 ✓';sonuc.fiyat=p.h[1];break}}
  sonuc.h1=h1;sonuc.realize=realize;sonuc.kalanLot=lot;return sonuc}
function kz(p,d){return d.realize+(d.kalanLot?(d.fiyat-p.giris)*d.kalanLot:0)}
function ekranPortfoy(){const b=(k,a)=>`<button data-pt="${k}" class="${pt===k?'on':''}">${a}</button>`;
  let x=baslik('İşlem günlüğün ve botun karnesi','Portföy',false)+`<div class="seg" style="margin-top:16px">${b('gercek','Gerçek')}${b('kagit','Kağıt üstünde')}${b('bot','Bot portföyü')}</div>`;
  if(pt==='bot'){const B=V.bot[M];if(!B||!B.n)return x+`<div class="bos"><b>Karne hazırlanıyor</b>Bot geçmiş testini arka planda yapıyor; birkaç dakika sonra burada olacak.</div>`;
    return x+`<div class="acik">Bot son 30 günde güven 55 üstü her ${M==='g'?'gün içi':'swing'} sinyaline sermayenin %1'ini riske ederek girseydi:</div>
     <div class="kart altin"><small class="mu" style="letter-spacing:.08em;font-size:11px">TOPLAM GETİRİ</small><div class="se ${yon(B.getiri)}" style="font-size:36px;font-weight:600">${yz(B.getiri)}</div>
     <div style="margin-top:10px">${genis(spark(B.egri,320,70,B.getiri>=0?'var(--up)':'var(--dn)'))}</div>
     <div class="uc"><div><small>İŞLEM</small><b>${B.n}</b></div><div><small>KAZANMA</small><b>%${tl(B.kazanma,0)}</b></div><div><small>MAKS. DÜŞÜŞ</small><b class="dn">${yz(B.dd,1)}</b></div></div></div>
     <div class="bolum"><h2>En iyi işlemler</h2></div><div class="liste">${B.en_iyi.map(t=>`<div class="satir" data-h="${t.s}">${av(t.s)}<div class="ad"><b>${t.s}</b><small>${t.tur} · ${t.saat}</small></div><div class="sag n"><b class="up">+${tl(t.R,1)}R</b></div></div>`).join('')}</div>
     <div class="bolum"><h2>En kötü işlemler</h2></div><div class="liste">${B.en_kotu.map(t=>`<div class="satir" data-h="${t.s}">${av(t.s)}<div class="ad"><b>${t.s}</b><small>${t.tur} · ${t.saat}</small></div><div class="sag n"><b class="dn">${tl(t.R,1)}R</b></div></div>`).join('')}</div>
     <div class="not">R: riske edilen miktarın katı (+2R = riskin 2 katı kazanç). Aynı anda açık işlemler ve kayma hesaba katılmamıştır. Son derin test: ${V.derin||'—'}.</div>`}
  const l=poz.filter(p=>p.tip===pt).map(p=>({p,d:degerlendir(p)}));
  const acik=l.filter(x=>x.d.durum==='açık'),kapali=l.filter(x=>x.d.durum!=='açık');
  const top=l.reduce((a,x)=>a+kz(x.p,x.d),0),kaz=kapali.filter(x=>kz(x.p,x.d)>0).length;
  x+=`<div class="ozet3"><div><small>TOPLAM K/Z</small><b class="${yon(top)}">${top>=0?'+':'−'}${tl(Math.abs(top),0)} ₺</b></div><div><small>AÇIK</small><b>${acik.length}</b></div><div><small>KAZANMA</small><b>${kapali.length?'%'+tl(kaz/kapali.length*100,0):'—'}</b></div></div>`;
  if(!l.length)return x+`<div class="bos" style="margin-top:12px"><b>Henüz işlem yok</b>Bir planın detayında “${pt==='gercek'?'İşleme girdim':'Kağıt üstünde al'}” butonuna dokun. Kayıtlar bu cihazda saklanır; bot stop ve hedefleri senin yerine takip eder.</div>`;
  const kart=({p,d})=>{const k=kz(p,d),yuz=k/(p.giris*p.lot)*100;return `<div class="kart poz"><div class="satir">${av(p.s)}<div class="ad"><b>${p.s} <span class="et ${p.tip==='kagit'?'fo':'au'}">${p.tip==='kagit'?'Kağıt':'Gerçek'}</span></b><small>${p.tarih} · ${p.mod==='g'?'gün içi':'swing'}</small></div>
    <div class="sag n"><b class="${yon(k)}">${k>=0?'+':'−'}${tl(Math.abs(k),0)} ₺</b><span class="dg ${yon(yuz)}">${yz(yuz)}</span></div></div>
    <div class="bilgi"><div><small>Giriş</small><b>${tl(p.giris)}</b></div><div><small>Lot</small><b>${tl(p.lot,0)}</b></div><div><small>${d.durum==='açık'?'Şimdi':'Çıkış'}</small><b>${tl(d.fiyat)}</b></div>
    <div><small>Stop</small><b class="dn">${tl(d.h1?p.giris:p.stop)}</b></div><div><small>H1</small><b class="up">${tl(p.h[0])}</b></div><div><small>Durum</small><b style="font-family:Inter;font-size:12px">${d.durum==='açık'?(d.h1?'H1 alındı':'Açık'):d.durum}</b></div></div>
    <div class="dugmeler">${d.durum==='açık'?`<button class="dugme" data-kapat="${p.id}">Şimdi kapat</button>`:''}<button class="dugme kirmizi" data-sil="${p.id}">Sil</button><button class="dugme" data-h="${p.s}">Grafik</button></div></div>`};
  return x+(acik.length?`<div class="bolum"><h2>Açık pozisyonlar</h2></div>${acik.map(kart).join('')}`:'')+(kapali.length?`<div class="bolum"><h2>Kapananlar</h2></div>${kapali.map(kart).join('')}`:'')+
   `<div class="not">Bot, açık pozisyonları plana göre takip eder: H1'de yarısını satar, stopu girişe çeker, kalanı H2'de kapatır. Kayıtlar yalnızca bu cihazda saklanır.</div>`}

// ---------- PROFİL ----------
function ekranProfil(){const K=V.karne[M]||[];const l=liste_.filter(h=>fav.has(h.s));
  return baslik('Ayarlar, favoriler ve botun karnesi','Profil')+
  `<div class="bolum"><h2>Favoriler</h2><small>${l.length}</small></div>`+(l.length?`<div class="liste">${l.map(h=>satir(h,'Bot: '+gorus(h).tur)).join('')}</div>`:`<div class="bos"><b>Henüz favori yok</b>Hisse detayında ☆ simgesine dokun.</div>`)+
  `<div class="bolum"><h2>Ayarlar</h2></div><div class="form-ayar">
   <label><small>Sermaye (TL)</small><input id="a_sermaye" inputmode="numeric" value="${ayar.sermaye}"></label>
   <label><small>İşlem başı risk (%)</small><input id="a_risk" inputmode="decimal" value="${ayar.risk}"></label>
   <label class="genis"><small>Minimum güven puanı: <b id="gv" class="au">${ayar.guven}</b></small><input type="range" id="a_guven" min="40" max="90" step="5" value="${ayar.guven}"></label>
   <label class="genis"><small>Günlük işlem hacmi en az</small><select id="a_lik">${[20,30,100,300].map(v=>`<option value="${v}"${ayar.lik==v?' selected':''}>${v} milyon TL</option>`).join('')}</select></label></div>
   <div class="acik" style="margin-top:8px">Lot önerisi: stop olursa sermayenin en fazla risk yüzdesi kadarını kaybedeceğin miktar.</div>
  <div class="bolum"><h2>Kurulum karnesi</h2><small>${M==='g'?'gün içi':'swing'} · son 30 ${M==='g'?'gün':'işlem'}</small></div>
   <div class="acik">Her sinyal türünün BIST'te ne kadar tuttuğu. Bot, en az 15 örneği olan türlerde güven puanını buna göre otomatik ayarlar.</div>`+
  (K.length?`<div class="kart" style="padding:4px 10px"><div class="karne"><div class="bas2">KURULUM</div><div class="bas2">ADET</div><div class="bas2">İSABET</div><div class="bas2">AYAR</div>
    ${K.map(k=>`<div>${esc(k.ad)}</div><div class="n">${k.n}</div><div class="n ${(k.isabet||0)>=45?'up':'dn'}">${k.isabet==null?'—':'%'+k.isabet}</div><div class="n ${k.bonus>0?'up':k.bonus<0?'dn':'mu'}">${k.bonus>0?'+':''}${k.bonus}</div>`).join('')}</div></div>`
   :`<div class="bos"><b>Karne hazırlanıyor</b>Arka planda tüm hisseler için geçmiş test yapılıyor.</div>`)+
  `<div class="bolum"><h2>Bot nasıl karar veriyor?</h2></div><div class="kart yorum">
   <div>Hacim profili (POC, değer bölgesi), VWAP ve her mumdaki alıcı/satıcı payıyla gerçek alıcının nerede olduğuna bakar.</div>
   <div>Kırılım, dönüş, stop avı, emilim, trend dönüşü (CHoCH) ve formasyon kırılımlarını yakalar.</div>
   <div>Günlük trend, BIST100 yönü ve endekse göre güçle onaylar; her sinyale 0-100 güven puanı verir, karnesine göre puanı düzeltir.</div>
   <div>Hacimli bölgede alıcılar gerçekten aktifse ◆ işareti koyar ve sinyalde ısrarcı olur.</div>
   <div>Giriş aralığı kovalamamak için verilir; stop yapının arkasına, hedefler sıradaki hacimli seviyelere konur.</div></div>
  <div class="bolum"><h2>Veri</h2></div><div class="kart yorum"><div>Son tarama ${V.guncelleme}${V.derin?', son derin test '+V.derin:''}. Bot arka planda seans içinde birkaç dakikada bir tarar.</div>
   <div>Veriler Yahoo Finance'tan yaklaşık 15 dk gecikmeli gelir; işleme girmeden önce fiyatı Midas'tan kontrol et.</div>
   <div>Henüz olmayanlar: anlık veri (Algolab hesabı gerekir), site kapalıyken bildirim (Telegram gerekir), KAP/bilanço takvimi.</div></div>`}

// ---------- gezinme ----------
let ekran=D.get('ekran','ana');
function ciz(kaydir){hazirla();document.querySelectorAll('nav.alt button').forEach(b=>b.classList.toggle('on',b.dataset.e===ekran));
  $('#ekran').innerHTML=`<div class="ekran">${({ana:ekranAna,plan:ekranPlan,piyasa:ekranPiyasa,portfoy:ekranPortfoy,profil:ekranProfil}[ekran]||ekranAna)()}<div class="uyari">Yatırım tavsiyesi değildir</div></div>`;
  if(kaydir)$('#ekran').scrollTop=0;
  const qi=$('#q');if(qi)qi.oninput=e=>{q=e.target.value.toUpperCase().trim();$('#pliste').innerHTML=piyasaIcerik()};
  const si=$('#ms');if(si)si.onchange=e=>{ms=e.target.value;D.set('ms',ms);$('#pliste').innerHTML=piyasaIcerik()};
  ['sermaye','risk'].forEach(k=>{const i=$('#a_'+k);if(i)i.onchange=e=>{const v=parseFloat(String(e.target.value).replace(/\./g,'').replace(',','.'));if(v>0){ayar[k]=v;D.set('ayar',ayar);toast('Kaydedildi')}}});
  const g=$('#a_guven');if(g){g.oninput=e=>$('#gv').textContent=e.target.value;g.onchange=e=>{ayar.guven=+e.target.value;D.set('ayar',ayar);ciz()}}
  const lk=$('#a_lik');if(lk)lk.onchange=e=>{ayar.lik=+e.target.value;D.set('ayar',ayar);ciz()}}
document.querySelector('nav.alt').onclick=e=>{const b=e.target.closest('button');if(!b)return;ekran=b.dataset.e;D.set('ekran',ekran);ciz(true)};
$('#ekran').onclick=e=>{const t=e.target.closest('[data-yenile],[data-mod],[data-l],[data-pf],[data-pg],[data-mf],[data-pt],[data-git],[data-sek],[data-sektemizle],[data-kapat],[data-sil],[data-h]');if(!t)return;const d=t.dataset;
  if(d.yenile){yenile();return}if(d.mod){M=d.mod;D.set('mod',M);ciz()}else if(d.l){liste=d.l;D.set('liste',liste);ciz()}else if(d.pf){pf=d.pf;D.set('pf',pf);ciz()}
  else if(d.pg){pg=d.pg;D.set('pg',pg);ciz()}else if(d.mf){mf=d.mf;D.set('mf',mf);ciz()}else if(d.pt){pt=d.pt;D.set('pt',pt);ciz()}
  else if(d.git){if(d.git==='sektor'){ekran='piyasa';pg='sektor'}else ekran=d.git;D.set('ekran',ekran);ciz(true)}
  else if(d.sek){sekSec=d.sek;ekran='piyasa';pg='hisse';ciz(true)}else if(d.sektemizle){sekSec=null;ciz()}
  else if(d.kapat){const p=poz.find(x=>x.id==d.kapat),o=H[p.s]&&H[p.s][p.mod];if(p&&o){const dv=degerlendir(p);p.kap={fiyat:o.p,realize:dv.realize-(o.p-p.giris)*(p.lot-dv.kalanLot)};D.set('poz',poz);toast('Pozisyon kapatıldı');ciz()}}
  else if(d.sil){poz=poz.filter(x=>x.id!=d.sil);D.set('poz',poz);ciz()}
  else detayAc(d.h)};

// ---------- DETAY (alttan açılan sayfa) ----------
let chart=null,ro=null,secili=null,sekme=D.get('sekme','analiz');
const gor=Object.assign({plan:true,vwap:true,ema:false,prof:true,sev:false,form:true},D.get('gor',{}));
function ema(d,n){const k=2/(n+1);let e=d[0];return d.map(v=>e=v*k+e*(1-k))}
function vwapHesap(m){let gun=-1,pv=0,vv=0;return m.map(x=>{const g=Math.floor(x[0]/86400);if(g!==gun){gun=g;pv=0;vv=0}pv+=(x[2]+x[3]+x[4])/3*x[5];vv+=x[5];return vv?pv/vv:x[4]})}
function delta(m){return m.map(x=>{const r=x[2]-x[3];return r>0?x[5]*((x[4]-x[3])-(x[2]-x[4]))/r:0})}
function detayAc(s){const h=H[s];if(!h||!X(h))return;secili=s;D.set('detay',s);hazirla();const o=X(h);
  $('#tv').href='https://tr.tradingview.com/chart/?symbol=BIST%3A'+encodeURIComponent(s);yildizCiz();
  const vwF=o.vw?(o.p/o.vw-1)*100:null;
  $('#dkah').innerHTML=`<small>${esc(h.sek)} · ${tl(h.lik,0)} mn TL günlük işlem · ${M==='g'?'15 dk':'günlük'}</small><h1>${s}</h1>
   <div class="fiyat"><b>${tl(o.p)}</b><span class="dg ${yon(o.d)}">${yz(o.d)}</span></div>
   <div class="cipler"><span>Hacim <b>${tl(o.rv,1)}x</b></span><span>${(o.ab||0)>=0?'Alıcı':'Satıcı'} <b>%${tl(Math.abs(o.ab||0)*100,0)}</b></span>${M==='g'?`<span>VWAP <b class="${yon(vwF||0)}">${vwF==null?'—':yz(vwF)}</b></span>`:''}<span>RSI <b>${tl(o.rsi,0)}</b></span></div>`;
  const g=gorus(h);$('#dkarar').innerHTML=`<div class="karar ${g.tur}"><span class="rozet ${g.tur==='AL'?'al':g.tur==='SAT'?'sat':'bekle'}">${g.tur}</span><div><small>BOT GÖRÜŞÜ</small><p>${esc(g.metin)}</p></div></div>`;
  $('#dplan').innerHTML=o.akt?`<div class="bolum"><h2>İşlem planı</h2><small>güven ${o.akt.guven} · ${gAd(o.akt.guven)}</small></div>${bilet(h,true)}`
   :`<div class="bolum"><h2>Tetik seviyeleri</h2></div><div class="kart"><div class="tablo" style="margin-top:0"><div><small>AL TETİĞİ</small><b class="up">${tl(o.tetik.ust)}</b><em class="mu">üstünde kapanış</em></div>
     <div><small>SAT / ÇIKIŞ</small><b class="dn">${tl(o.tetik.alt)}</b><em class="mu">altına sarkma</em></div></div><div class="not" style="margin-top:10px">Şu an açık plan yok. Bu seviyeler kırılırsa bot yeni plan üretir.</div></div>`;
  $('#perde').classList.add('ac');$('#detay').classList.add('ac');$('#dicerik').scrollTop=0;setTimeout(()=>grafikKur(h),80);sekmeCiz()}
function kapat(){$('#detay').classList.remove('ac');$('#perde').classList.remove('ac');formKapat();D.set('detay','');setTimeout(()=>{if(chart){chart.remove();chart=null}},350)}
$('#geri').onclick=kapat;$('#perde').onclick=kapat;
function yildizCiz(){const b=$('#dyildiz'),on=fav.has(secili);b.textContent=on?'★':'☆';b.classList.toggle('on',on)}
$('#dyildiz').onclick=()=>{fav.has(secili)?fav.delete(secili):fav.add(secili);D.set('fav',[...fav]);yildizCiz();toast(fav.has(secili)?'Favorilere eklendi':'Favorilerden çıkarıldı')};
$('#dplan').onclick=e=>{const b=e.target.closest('[data-gir]');if(b)formAc(b.dataset.gir)};
function formAc(tip){const h=H[secili],o=X(h),s=o.akt,L=lotHesap(s)||{lot:0};
  $('#form').innerHTML=`<div class="tutamak"></div><div class="bolum" style="margin-top:14px"><h2>${tip==='gercek'?'İşleme girdim':'Kağıt üstünde al'} · ${h.s}</h2></div>
   <div class="form-ayar"><label><small>Alış fiyatı</small><input id="f_fiyat" inputmode="decimal" value="${tl(Math.min(o.p,s.giris_ust))}"></label><label><small>Lot</small><input id="f_lot" inputmode="numeric" value="${L.lot||1}"></label></div>
   <div class="acik" style="margin-top:10px">Stop ${tl(s.stop)} · H1 ${tl(s.hedef)} · H2 ${tl(s.hedef2)}. Bot pozisyonu bu plana göre takip edecek.</div>
   <div class="dugmeler"><button class="dugme" id="f_iptal">Vazgeç</button><button class="dugme ana" id="f_kaydet">Kaydet</button></div>`;
  $('#form').classList.add('ac');
  $('#f_iptal').onclick=formKapat;
  $('#f_kaydet').onclick=()=>{const num=v=>parseFloat(String(v).replace(/\./g,'').replace(',','.'));const f=num($('#f_fiyat').value),l=Math.floor(num($('#f_lot').value));
    if(!(f>0&&l>0)){toast('Fiyat ve lot gir');return}
    const son=o.m[o.m.length-1][0];
    poz.unshift({id:Date.now(),s:h.s,mod:M,tip,yon:s.yon,giris:f,lot:l,stop:s.stop,h:[s.hedef,s.hedef2,s.hedef3],t:son,tarih:new Date().toLocaleDateString('tr-TR',{day:'2-digit',month:'2-digit'})+' '+new Date().toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'}),kap:null});
    D.set('poz',poz);formKapat();toast('Portföye eklendi');if(ekran==='portfoy')ciz()}}
function formKapat(){$('#form').classList.remove('ac')}

function grafikKur(h){if(chart){chart.remove();chart=null}const el=$('#grafik'),o=X(h);
  if(!window.LightweightCharts){el.innerHTML='<div class="bos" style="margin:0 18px">Grafik yüklenemedi. Sayfayı yenile.</div>';return}
  chart=LightweightCharts.createChart(el,{width:el.clientWidth,height:310,layout:{background:{type:'solid',color:'transparent'},textColor:'#8a857d',fontFamily:'IBM Plex Mono',fontSize:10},
    grid:{vertLines:{visible:false},horzLines:{color:'rgba(255,255,255,.04)'}},rightPriceScale:{borderVisible:false,scaleMargins:{top:.06,bottom:.2}},
    timeScale:{borderVisible:false,timeVisible:M==='g',secondsVisible:false,rightOffset:6,barSpacing:7},
    crosshair:{mode:0,vertLine:{color:'#66625b',labelBackgroundColor:'#22252e'},horzLine:{color:'#66625b',labelBackgroundColor:'#22252e'}},localization:{locale:'tr-TR',priceFormatter:p=>tl(p)}});
  const m=o.m,n=m.length,zam=m.map(x=>x[0]);
  const mum=chart.addCandlestickSeries({upColor:'#3ccf91',downColor:'#f0645f',borderVisible:false,wickUpColor:'#3ccf91',wickDownColor:'#f0645f',priceLineColor:'#d9b26f',priceLineStyle:2});
  mum.setData(m.map(x=>({time:x[0],open:x[1],high:x[2],low:x[3],close:x[4]})));
  const hac=chart.addHistogramSeries({priceScaleId:'h',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false});chart.priceScale('h').applyOptions({scaleMargins:{top:.84,bottom:0}});
  const dl=delta(m);hac.setData(m.map((x,i)=>({time:x[0],value:x[5],color:dl[i]>=0?'rgba(60,207,145,.32)':'rgba(240,100,95,.32)'})));
  const cz=(r,w=1,st=0)=>chart.addLineSeries({color:r,lineWidth:w,lineStyle:st,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
  const kp=m.map(x=>x[4]);const e20=cz('#7fb3d5'),e50=cz('#b39ddb');e20.setData(ema(kp,20).map((v,i)=>({time:zam[i],value:v})));e50.setData(ema(kp,50).map((v,i)=>({time:zam[i],value:v})));
  const vw=cz('#d9b26f',1.5,2);if(M==='g')vw.setData(vwapHesap(m).map((v,i)=>({time:zam[i],value:v})));
  const fs=[];o.form.forEach(f=>f.cizgiler.forEach(c=>{const s=cz(f.yon<0?'#f0948f':'#b39ddb',2);s.setData([{time:c[0],value:c[1]},{time:c[2],value:c[3]}]);fs.push(s)}));
  let cl=[];const lo=Math.min(...m.map(x=>x[3]))*.97,hi=Math.max(...m.map(x=>x[2]))*1.03;
  function uyg(){[e20,e50].forEach(s=>s.applyOptions({visible:gor.ema}));vw.applyOptions({visible:gor.vwap&&M==='g'});fs.forEach(s=>s.applyOptions({visible:gor.form}));
    cl.forEach(p=>mum.removePriceLine(p));cl=[];const ek=x=>cl.push(mum.createPriceLine(Object.assign({lineWidth:1,axisLabelVisible:false},x)));
    if(gor.sev)o.sev.filter(s=>s[0]>lo&&s[0]<hi).forEach(s=>ek({price:s[0],color:(s[1]==='D'?'rgba(60,207,145,':'rgba(240,100,95,')+(0.25+0.45*(s[2]||0)).toFixed(2)+')',lineStyle:2}));
    if(gor.prof&&o.prof){ek({price:o.prof.poc,color:'rgba(217,178,111,.9)',lineStyle:0,title:'POC',axisLabelVisible:true});ek({price:o.prof.vah,color:'rgba(244,239,230,.22)',lineStyle:1,title:'VAH'});ek({price:o.prof.val,color:'rgba(244,239,230,.22)',lineStyle:1,title:'VAL'})}
    const s=o.akt;if(gor.plan&&s){ek({price:s.stop,color:'#f0645f',lineStyle:0,title:'STOP',axisLabelVisible:true});ek({price:s.giris_ust,color:'#f0d49a',lineStyle:2,title:'GİRİŞ'});ek({price:s.giris_alt,color:'#f0d49a',lineStyle:2});
      [s.hedef,s.hedef2,s.hedef3].forEach((p,i)=>ek({price:p,color:`rgba(60,207,145,${1-i*.25})`,lineStyle:0,title:'H'+(i+1),axisLabelVisible:i===0}))}
    mum.setMarkers(gor.plan?o.sinF.filter(s=>s.t>=zam[0]&&s.t<=zam[n-1]).map(s=>({time:s.t,position:s.yon>0?'belowBar':'aboveBar',color:s.yon>0?'#3ccf91':'#f0645f',shape:s.yon>0?'arrowUp':'arrowDown',text:(s.guclu?'◆':'')+s.tur})):[])}
  uyg();
  const ar=M==='g'?{'1G':o.gun_bar,'2G':o.gun_bar*2,'5G':o.gun_bar*5,'Tümü':n}:{'1A':22,'3A':66,'Tümü':n};let sec=D.get('aralik_'+M,M==='g'?'2G':'3A');if(!ar[sec])sec=Object.keys(ar)[1];
  const arU=()=>{const k=Math.min(ar[sec],n);chart.timeScale().setVisibleLogicalRange({from:n-k-.5,to:n+5})};arU();
  const gs=$('#gsec'),t=(k,a,on)=>`<button class="chip${on?' on':''}" data-k="${k}">${a}</button>`;
  const gsc=()=>{gs.innerHTML=Object.keys(ar).map(k=>t('a:'+k,k,sec===k)).join('')+'<span class="ayr"></span>'+t('g:plan','Plan',gor.plan)+(M==='g'?t('g:vwap','VWAP',gor.vwap):'')+t('g:prof','Hacim profili',gor.prof)+t('g:form','Formasyon',gor.form)+t('g:sev','Seviyeler',gor.sev)+t('g:ema','EMA',gor.ema)};gsc();
  gs.onclick=e=>{const b=e.target.closest('[data-k]');if(!b)return;const[tp,k]=b.dataset.k.split(':');if(tp==='a'){sec=k;D.set('aralik_'+M,k);arU()}else{gor[k]=!gor[k];D.set('gor',gor);uyg()}gsc()};
  const ix=Object.fromEntries(m.map((x,i)=>[x[0],i]));
  const lg=i=>{const x=m[i];if(!x)return'';const d=dl[i];return `A <b>${tl(x[1])}</b> Y <b>${tl(x[2])}</b> D <b>${tl(x[3])}</b> K <b class="${x[4]>=x[1]?'up':'dn'}">${tl(x[4])}</b> · ${d>=0?'<span class="up">alıcı</span>':'<span class="dn">satıcı</span>'} %${tl(Math.abs(d)/(x[5]||1)*100,0)}`};
  $('#legend').innerHTML=lg(n-1);chart.subscribeCrosshairMove(p=>{$('#legend').innerHTML=lg(p&&p.time!=null&&ix[p.time]!=null?ix[p.time]:n-1)});
  if(ro)ro.disconnect();ro=new ResizeObserver(()=>chart&&chart.applyOptions({width:el.clientWidth}));ro.observe(el)}

function gosterge(ab){const a=Math.PI*(1-(ab+1)/2),x=60+48*Math.cos(a),y=58-48*Math.sin(a);
  return `<svg viewBox="0 0 120 66" width="100%" style="max-width:220px;display:block;margin:6px auto 0"><defs><linearGradient id="gg"><stop offset="0" stop-color="#f0645f"/><stop offset=".5" stop-color="#3a3d45"/><stop offset="1" stop-color="#3ccf91"/></linearGradient></defs>
   <path d="M12 58 A48 48 0 0 1 108 58" fill="none" stroke="url(#gg)" stroke-width="7" stroke-linecap="round"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="7" fill="#f4efe6" stroke="#0b0c10" stroke-width="3"/></svg>`}
function sekmeCiz(){document.querySelectorAll('#sekmeler button').forEach(b=>b.classList.toggle('on',b.dataset.s===sekme));const h=H[secili],o=X(h);let x='';
  if(sekme==='analiz'){const s=o.akt;
    if(s)x+=`<div class="kart"><small class="au" style="font-size:10.5px;font-weight:700;letter-spacing:.12em">SİNYALİN GEREKÇELERİ</small><div class="neden" style="margin-top:10px">${s.arti.map(a=>`<div class="p">${esc(a)}</div>`).join('')}${s.eksi.map(a=>`<div class="x">${esc(a)}</div>`).join('')}</div></div>`;
    x+=`<div class="bolum" style="margin-top:${s?22:4}px"><h2>Bot ne görüyor?</h2></div><div class="kart yorum">${o.yorum.map(c=>`<div>${esc(c)}</div>`).join('')}</div>`}
  else if(sekme==='hacim'){const ab=o.ab||0,vwF=o.vw?(o.p/o.vw-1)*100:null;
    x+=`<div class="kart" style="text-align:center"><small class="au" style="font-size:10.5px;font-weight:700;letter-spacing:.12em">ALICI / SATICI BASKISI · SON 20 ${M==='g'?'MUM':'GÜN'}</small>${gosterge(Math.max(-1,Math.min(1,ab*2)))}
      <div class="se ${yon(ab)}" style="font-size:22px;font-weight:600">${ab>=0?'Alıcılar':'Satıcılar'} %${tl(Math.abs(ab)*100,0)}</div><div class="mu" style="font-size:12px;margin-top:4px">Kapanışın mum içindeki konumuna göre hacmin alıcı/satıcı payı tahmin edilir.</div></div>
      <div class="izgara" style="margin-top:8px"><div><small>Göreli hacim</small><b>${tl(o.rv,1)}x</b><i>${M==='g'?'bu saatin normaline göre':'son 10 güne göre'}</i></div>
      ${M==='g'?`<div><small>VWAP farkı</small><b class="${yon(vwF||0)}">${vwF==null?'—':yz(vwF)}</b><i>ort. maliyet ${tl(o.vw)}</i></div>`:`<div><small>RSI</small><b>${tl(o.rsi,0)}</b><i>momentum</i></div>`}</div>`;
    const dl=delta(o.m);let c=0;const cv=dl.map(v=>c+=v).slice(-120);
    x+=`<div class="bolum"><h2>Hacim akışı</h2><small>son ${cv.length} ${birim()}</small></div><div class="kart">${genis(spark(cv,320,60,cv[cv.length-1]>=cv[0]?'var(--up)':'var(--dn)'))}<div class="mu" style="font-size:12px;margin-top:8px">Yükselen çizgi alıcı hacminin biriktiğini gösterir. Fiyat düşerken çizgi yükseliyorsa gizli alım olabilir.</div></div>`;
    if(o.prof){const b=[...o.prof.bins].reverse(),mx=Math.max(...b.map(x=>x[1]));const si=b.reduce((e,x,i)=>Math.abs(x[0]-o.p)<Math.abs(b[e][0]-o.p)?i:e,0),pi=b.reduce((e,x,i)=>x[1]>b[e][1]?i:e,0);
      x+=`<div class="bolum"><h2>Hacim profili</h2><small>${M==='g'?'son 10 gün':'son 12 hafta'}</small></div><div class="acik">Uzun çubuklar gerçek alıcı ve satıcıların biriktiği seviyeler. Altın çubuk POC, açık altın alan değer bölgesi (hacmin %70'i).</div>
      <div class="kart profil">${b.map((r,i)=>`<div class="${i===pi?'poc':(r[0]>=o.prof.val&&r[0]<=o.prof.vah?'va':'')}${i===si?' simdi':''}"><span>${tl(r[0])}</span><i style="width:${(r[1]/mx*68).toFixed(1)}%"></i></div>`).join('')}</div>`}}
  else if(sekme==='teknik'){const tr={1:'Yukarı',0:'Yatay','-1':'Aşağı'},yp={1:'Yükselen',0:'Kararsız','-1':'Alçalan'};
    x+=`<div class="izgara">${M==='g'?`<div><small>Günlük trend</small><b class="${o.htf>0?'up':o.htf<0?'dn':''}">${tr[o.htf]}</b><i>EMA20 / EMA50</i></div>`:''}
      <div><small>${M==='g'?'15 dk':'Günlük'} yapı</small><b class="${o.yapi>0?'up':o.yapi<0?'dn':''}">${yp[o.yapi]}</b><i>tepe-dip dizilimi</i></div>
      <div><small>RSI</small><b class="${o.rsi>70?'dn':o.rsi<30?'up':''}">${tl(o.rsi,0)}</b><i>${o.rsi>70?'aşırı alım':o.rsi<30?'aşırı satım':'normal bölge'}</i></div>
      <div><small>MACD</small><b class="${yon(o.macd||0)}">${(o.macd||0)>=0?'Pozitif':'Negatif'}</b><i>momentum</i></div>
      <div><small>Endekse göre</small><b class="${yon(o.rs||0)}">${yz(o.rs)}</b><i>son ${M==='g'?5:20} gün</i></div><div><small>Oynaklık</small><b>%${tl(o.atr)}</b><i>ortalama mum boyu</i></div></div>`;
    x+=`<div class="bolum"><h2>Formasyonlar</h2></div>`+(o.form.length?`<div class="liste">${o.form.map(f=>`<div class="satir" style="cursor:default"><div class="ad"><b style="font-size:14px">${esc(f.ad)}</b><small>${f.yon>0?'Yukarı beklenti':f.yon<0?'Aşağı beklenti':'Yön belirsiz'}${f.ref?' · kritik '+tl(f.ref):''}${f.hedef?' · hedef '+tl(f.hedef):''}</small></div><span class="et ${f.durum==='kırıldı'?(f.yon>0?'al':'sat'):'fo'}">${f.durum}</span></div>`).join('')}</div>`:`<div class="bos">Şu an formasyon yok</div>`);
    const sv=[...o.sev].sort((a,b)=>Math.abs(a[0]-o.p)-Math.abs(b[0]-o.p)).slice(0,8).sort((a,b)=>b[0]-a[0]);
    x+=`<div class="bolum"><h2>Destek / direnç</h2><small>hacim gücüyle</small></div><div class="liste">${sv.map(s=>`<div class="satir" style="cursor:default"><span class="et ${s[1]==='D'?'al':'sat'}" style="margin:0;width:58px;text-align:center">${s[1]==='D'?'Destek':'Direnç'}</span><div class="ad"><b class="n" style="font-size:14px">${tl(s[0])}</b><small>${yz((s[0]/o.p-1)*100,1)} uzakta</small></div><div style="width:70px"><div class="bar"><i style="width:${(s[2]||0)*100}%;background:var(--au)"></i></div></div></div>`).join('')}</div>`}
  else{const l=[...o.sinF].reverse(),bit=l.filter(s=>s.sonuc!=='açık'),hd=bit.filter(s=>s.sonuc==='hedef').length,st=bit.filter(s=>s.sonuc==='stop').length;
    x+=`<div class="say4"><div><small>SİNYAL</small><b>${l.length}</b></div><div><small>HEDEF</small><b class="up">${hd}</b></div><div><small>STOP</small><b class="dn">${st}</b></div><div><small>İSABET</small><b>${hd+st?'%'+tl(hd/(hd+st)*100,0):'—'}</b></div></div>`;
    x+=l.length?`<div class="liste">${l.slice(0,20).map(s=>`<div class="satir" style="cursor:default"><span class="rozet ${s.yon>0?'al':'sat'}" style="padding:3px 8px;font-size:10.5px">${s.tur}</span><div class="ad"><b class="n" style="font-size:13px">${s.saat}</b><small>güven ${s.guven}${s.guclu?' · ◆':''} · giriş ${tl(s.fiyat)}</small></div>
      <div class="sag"><b style="font-size:13px" class="${s.sonuc==='hedef'?'up':s.sonuc==='stop'?'dn':''}">${esc(s.sonuc)}</b><small class="mu n">${yz(s.getiri)}</small></div></div>`).join('')}</div>`:`<div class="bos">Bu dönemde sinyal yok</div>`;
    x+=`<div class="not">Aynı kurallar geçmiş veriye uygulandı; her sinyalden sonra ${V.ufuk} ${birim()} içinde önce H1'e mi stopa mı gidildiğine bakıldı. Hedefler riskin en az 1,5 katı olduğu için yaklaşık %40 üstü isabet kârlı sayılır.</div>`}
  $('#sekme').innerHTML=x}
$('#sekmeler').onclick=e=>{const b=e.target.closest('button');if(!b)return;sekme=b.dataset.s;D.set('sekme',sekme);sekmeCiz()};

ciz();const ds=D.get('detay','');if(ds&&H[ds]&&X(H[ds]))detayAc(ds);
</script></body></html>
"""


# ---------- Siteye gidecek veri ----------
ESIK = 40   # bu güvenin altındaki sinyaller hiç gönderilmez; kullanıcı eşiği uygulamada ayrıca uygulanır


def _ts(t, mod) -> int:
    """Gün içi grafikte İstanbul saati görünsün diye UTC damgasına +3 saat eklenir."""
    return int(pd.Timestamp(t).timestamp()) + (3 * 3600 if mod == "g" else 0)


def sinyal_json(s: dict, df: pd.DataFrame, n: int, fiyat: float, mod: str) -> dict:
    al = s["yon"] > 0
    ilerleme = ((fiyat - s["stop"]) / max(s["hedef"] - s["stop"], 1e-9) if al
                else (s["stop"] - fiyat) / max(s["stop"] - s["hedef"], 1e-9))
    ga, gu = s["giris_alt"], s["giris_ust"]
    if s["sonuc"] != "açık":
        durum = dict(kod="bitti", metin="Sonuçlandı")
    elif (al and fiyat > gu) or (not al and fiyat < ga):
        durum = dict(kod="kacti", metin="Fiyat giriş aralığını geçti — kovalama, geri çekilme bekle")
    elif ga <= fiyat <= gu:
        durum = dict(kod="bolgede", metin="Fiyat giriş aralığında — plan geçerli")
    else:
        durum = dict(kod="dikkat", metin="Fiyat girişin " + ("altında, stopa yaklaşıyor — dikkat" if al
                                                             else "üstünde, stopa yaklaşıyor — dikkat"))
    sonrasi = df.iloc[s["i"] + 1:n]
    en_iyi = (sonrasi["High"].max() if al else sonrasi["Low"].min()) if len(sonrasi) else s["fiyat"]
    yuzde = lambda x: _r((x / s["fiyat"] - 1) * 100 * (1 if al else -1), 2)  # noqa: E731
    zaman = df.index[s["i"]]
    return dict(
        t=_ts(zaman, mod), saat=f"{zaman:%d.%m %H:%M}" if mod == "g" else f"{zaman:%d.%m.%Y}", once=n - 1 - s["i"],
        tur=s["tur"], yon=s["yon"], guven=s["guven"], guclu=s["guclu"], kurulum=s.get("kurulum", ""),
        sebepler=s["sebepler"], arti=s["arti"], eksi=s["eksi"],
        fiyat=_r(s["fiyat"], 4), stop=_r(s["stop"], 4), hedef=_r(s["hedef"], 4), hedef2=_r(s["hedef2"], 4),
        hedef3=_r(s["hedef3"], 4), giris_alt=_r(ga, 4), giris_ust=_r(gu, 4), rk=_r(s["rk"], 1),
        sonuc=s["sonuc"], getiri=_r(s["getiri"] * 100, 2), ilerleme=_r(min(max(ilerleme, 0), 1), 3), durum=durum,
        risk=_r(abs(s["fiyat"] - s["stop"]) / s["fiyat"] * 100, 2),
        pot=[yuzde(s["hedef"]), yuzde(s["hedef2"]), yuzde(s["hedef3"])],
        en_iyi=yuzde(en_iyi), kalan=max(TEST_UFKU - (n - 1 - s["i"]), 0),
    )


def kompakt(x: dict) -> list:
    """Geçmiş sinyaller için sıkıştırılmış satır: [zaman, yön, güven, güçlü, fiyat, sonuç, getiri%]"""
    return [x["t"], x["yon"], x["guven"], int(x["guclu"]), x["fiyat"], x["sonuc"], x["getiri"]]


def mod_json(a: dict, eski_sin: list | None) -> dict:
    """Bir hissenin bir moddaki (gün içi / swing) tüm verisi."""
    ctx, mod = a["ctx"], a["mod"]
    df, n = ctx["df"], ctx["n"]
    bas = max(0, len(df) - (GRAFIK_MUM if mod == "g" else 90))
    w = df.iloc[bas:]
    zaman = [_ts(t, mod) for t in w.index]
    kurus = lambda x: int(round(float(x) * 100))  # noqa: E731
    mumlar = dict(t0=zaman[0], d=[[(zaman[k] - zaman[k - 1]) // 60 if k else 0, kurus(o), kurus(h), kurus(l), kurus(c), int(v)]
                                  for k, (o, h, l, c, v) in enumerate(zip(w["Open"].values, w["High"].values, w["Low"].values,
                                                                          w["Close"].values, w["Volume"].values))])
    prof, fiyat = ctx["prof_guncel"], a["fiyat"]
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
                cizgiler.append([_ts(df.index[j0], mod), _r(y0, 4), _ts(df.index[j1], mod), _r(y1, 4)])
        formlar.append(dict(ad=f["ad"], yon=f["yon"], durum=f["durum"], ref=_r(f["ref"], 4), hedef=_r(f["hedef"], 4), cizgiler=cizgiler))
    yorum, tetik = bot_yorumu(ctx, a["sev"], a["formlar"])
    sinyaller = filtrele(a["sinyaller"], ESIK)
    tam = [sinyal_json(s, df, n, fiyat, mod) for s in sinyaller]
    akl = [x for x in tam if x["sonuc"] == "açık"]
    kisa = [kompakt(x) for x in tam]
    if eski_sin:  # derin testten kalan daha eski sinyaller
        ilk = kisa[0][0] if kisa else 10 ** 12
        kisa = [x for x in eski_sin if x[0] < ilk] + kisa
    gun_bar = int((df.index.date == df.index[-1].date()).sum()) if mod == "g" else 1
    return dict(
        p=_r(fiyat, 4), d=_r(a["degisim"], 2), m=mumlar, rv=_r(a["rv"], 2), ab=_r(a["ab"], 3), vw=_r(a["vwap"], 4),
        rsi=_r(a["rsi"], 1), macd=_r(a["macd"], 4), atr=_r(a["atr"], 2), yapi=a["yapi"], htf=a["htf"], rs=_r(a["rs"], 2),
        sev=[[_r(x, 4), "D" if x < fiyat else "R", _r(bolge_gucu(prof, x), 2)] for x in a["sev"]],
        form=formlar, yorum=yorum, tetik=tetik, gun_bar=max(gun_bar, 26) if mod == "g" else 1,
        prof=None if not prof else dict(poc=_r(prof["poc"], 4), vah=_r(prof["vah"], 4), val=_r(prof["val"], 4),
                                        bins=[[_r(m_, 2), _r(h_, 2)] for m_, h_ in zip(prof["merkez"], prof["hist"])]),
        akl=akl, sin=kisa[-30:], birikim=_r(a["birikim"], 3), yesil=a["yesil_mum"],
    )


def karne_hesapla(sinyaller: list[dict]) -> tuple[list, dict]:
    gruplar = {}
    for s in sinyaller:
        if s["sonuc"] == "açık":
            continue
        gruplar.setdefault(s.get("kurulum", "?"), []).append(s)
    tablo, agirlik = [], {}
    for k, l in gruplar.items():
        hedef = sum(x["sonuc"] == "hedef" for x in l)
        stop = sum(x["sonuc"] == "stop" for x in l)
        isabet = hedef / (hedef + stop) * 100 if hedef + stop else None
        ort = float(np.mean([x["getiri"] for x in l])) * 100
        bonus = 0
        if isabet is not None and len(l) >= 15:
            bonus = int(max(-10, min(8, round((isabet - 45) / 2.5))))
        agirlik[k] = dict(bonus=bonus, isabet=isabet or 0)
        ad = KURULUM_ADI.get(k, k[2:] + " kırılımı" if k.startswith("f-") else k)
        tablo.append(dict(ad=ad, n=len(l), hedef=hedef, stop=stop, isabet=_r(isabet, 0), ort=_r(ort, 2), bonus=bonus))
    tablo.sort(key=lambda x: -(x["isabet"] or 0))
    return tablo, agirlik


def bot_portfoyu(sinyaller: list[dict], esik: int = 55) -> dict:
    """Bot her sinyale sermayenin %1'ini riske ederek girseydi (sırayla, basitleştirilmiş)."""
    islemler = sorted([s for s in sinyaller if s["guven"] >= esik and s["sonuc"] != "açık"], key=lambda s: s["zaman"])
    if not islemler:
        return dict(n=0)
    ozkaynak, tepe, en_dusuk_dd, egri, rler = 100.0, 100.0, 0.0, [100.0], []
    for s in islemler:
        risk = abs(s["fiyat"] - s["stop"]) / s["fiyat"]
        R = s["getiri"] / risk if risk > 0 else 0
        rler.append((R, s))
        ozkaynak *= 1 + 0.01 * R
        tepe = max(tepe, ozkaynak)
        en_dusuk_dd = min(en_dusuk_dd, ozkaynak / tepe - 1)
        egri.append(ozkaynak)
    adim = max(1, len(egri) // 60)
    kazanan = sum(1 for R, _ in rler if R > 0)
    sirali = sorted(rler, key=lambda x: -x[0])
    ozet = lambda R, s: dict(s=s["sym"], tur=s["tur"], saat=f"{s['zaman']:%d.%m %H:%M}", R=_r(R, 2))  # noqa: E731
    return dict(n=len(islemler), kazanma=_r(kazanan / len(islemler) * 100, 0), getiri=_r(ozkaynak - 100, 2),
                dd=_r(en_dusuk_dd * 100, 2), egri=[_r(x, 2) for x in egri[::adim]] + [_r(egri[-1], 2)],
                en_iyi=[ozet(*x) for x in sirali[:3]], en_kotu=[ozet(*x) for x in sirali[-3:][::-1]],
                ort_R=_r(np.mean([R for R, _ in rler]), 2))


def sektor_ozeti(analizler: dict) -> list[dict]:
    gruplar = {}
    for h, a in analizler.items():
        gruplar.setdefault(sektor_bul(h), []).append((h, a))
    out = []
    for ad, l in gruplar.items():
        akis_pay, akis_payda = 0.0, 0.0
        for h, a in l:
            df = a["ctx"]["df"]
            bugun = df[df.index.date == df.index[-1].date()]
            akis_pay += float((bugun["Delta"] * bugun["Close"]).sum())
            akis_payda += float((bugun["Volume"] * bugun["Close"]).sum())
        out.append(dict(ad=ad, n=len(l), d=_r(np.mean([a["degisim"] for _, a in l]), 2),
                        ab=_r(np.mean([a["ab"] for _, a in l]), 3), akis=_r(akis_pay / akis_payda if akis_payda else 0, 3),
                        tl=_r(akis_pay / 1e6, 1), hisseler=[h for h, _ in sorted(l, key=lambda x: -x[1]["degisim"])][:8]))
    return sorted(out, key=lambda x: -(x["akis"] or 0))


# ---------- Arka plan servisi: sürekli tarar, site açılınca hazır sonuç verir ----------
class Servis:
    def __init__(self):
        self.html = None
        self.surum = 0
        self.durum = "Motor başlatılıyor"
        self.ilerleme = 0.0
        self.hata = None
        self.gunluk, self.gunluk_zaman = None, 0
        self.derin_zaman = 0
        self.derin_sin = {"g": {}, "w": {}}
        self.karne = {"g": [], "w": []}
        self.bot = {"g": dict(n=0), "w": dict(n=0)}
        threading.Thread(target=self._dongu, daemon=True).start()

    def _dongu(self):
        while True:
            try:
                self._tur(derin=False)
                if time.time() - self.derin_zaman > 1800:
                    self._tur(derin=True)
                self.hata = None
            except Exception as e:  # noqa: BLE001
                self.hata = f"{type(e).__name__}: {e}"
            time.sleep(150 if seans_acik_mi() else 900)

    def _tur(self, derin: bool):
        acik = seans_acik_mi()
        if self.gunluk is None or time.time() - self.gunluk_zaman > (1200 if acik else 6 * 3600):
            self.durum, self.ilerleme = "Günlük veriler indiriliyor (tüm borsa)", 0.05
            self.gunluk, self.gunluk_zaman = gunluk_veri(), time.time()
        gunluk = self.gunluk
        likitler = [h for h in TUM_HISSELER if h in gunluk and len(gunluk[h]) >= 20
                    and (gunluk[h]["Close"] * gunluk[h]["Volume"]).tail(20).mean() / 1e6 >= MIN_LIKIDITE]
        self.durum, self.ilerleme = f"{len(likitler)} likit hissenin 15 dakikalık verisi indiriliyor", 0.15
        gi = _gun_ici(likitler + ["XU100"])
        xu15, xug = gi.get("XU100"), gunluk.get("XU100")
        analiz = {"g": {}, "w": {}}
        for k, h in enumerate(likitler):
            self.durum = ("Derin geçmiş test ve kurulum karnesi" if derin else "Hisseler analiz ediliyor") + f" · {h}"
            self.ilerleme = 0.2 + 0.75 * k / max(len(likitler), 1)
            try:
                a = hisse_analiz(h, gi.get(h), gunluk.get(h), xu15, not acik, tam_test=derin, mod="g")
                if a:
                    analiz["g"][h] = a
            except Exception:  # noqa: BLE001
                pass
            try:
                a = hisse_analiz(h, gunluk.get(h), gunluk.get(h), xug, not acik, tam_test=derin, mod="w")
                if a:
                    analiz["w"][h] = a
            except Exception:  # noqa: BLE001
                pass

        if derin:
            for mod in ("g", "w"):
                tum = []
                for h, a in analiz[mod].items():
                    f = filtrele(a["sinyaller"], ESIK)
                    for s in f:
                        s["sym"] = h
                    tum += f
                    df, n = a["ctx"]["df"], a["ctx"]["n"]
                    self.derin_sin[mod][h] = [kompakt(sinyal_json(s, df, n, a["fiyat"], mod)) for s in f]
                self.karne[mod], AGIRLIK[mod] = karne_hesapla(tum)
                self.bot[mod] = bot_portfoyu(tum)
            self.derin_zaman = time.time()

        hisseler = []
        for h in likitler:
            ag, aw = analiz["g"].get(h), analiz["w"].get(h)
            if not ag and not aw:
                continue
            ana = ag or aw
            hisseler.append(dict(
                s=h, sek=sektor_bul(h), lik=_r(ana["likidite"], 1),
                g=mod_json(ag, self.derin_sin["g"].get(h)) if ag else None,
                w=mod_json(aw, self.derin_sin["w"].get(h)) if aw else None))

        bist = None
        if xu15 is not None and len(xu15) > 40:
            xc = xu15["Close"]
            dun = xc[xc.index.date < xc.index[-1].date()]
            rejim = "Yatay"
            if xug is not None and len(xug) > 60:
                e50 = xug["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
                e20 = xug["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
                son = xug["Close"].iloc[-1]
                rejim = "Boğa" if son > e20 > e50 else ("Ayı" if son < e20 < e50 else "Yatay")
            bist = dict(p=_r(xc.iloc[-1], 2), d=_r((xc.iloc[-1] / dun.iloc[-1] - 1) * 100 if len(dun) else 0, 2),
                        spark=[_r(x, 2) for x in xc.tail(64).values],
                        spark_w=[_r(x, 2) for x in xug["Close"].tail(60).values] if xug is not None else [], rejim=rejim)
        paket = dict(hisseler=hisseler, bist=bist, sektorler=sektor_ozeti(analiz["g"]), karne=self.karne, bot=self.bot,
                     seans=acik, guncelleme=f"{dt.datetime.now(TZ):%H:%M}", taranan=len(TUM_HISSELER),
                     likit=len(likitler), ufuk=TEST_UFKU, esik=ESIK,
                     derin=f"{dt.datetime.fromtimestamp(self.derin_zaman, TZ):%H:%M}" if self.derin_zaman else None)
        veri = json.dumps(paket, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        self.html = ARAYUZ.replace("__VERI__", veri)
        self.surum += 1
        self.durum, self.ilerleme = "Hazır", 1.0


@st.cache_resource
def servis_al() -> Servis:
    return Servis()


YUKLEME = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>html,body{margin:0;height:100%;background:#0b0c10;color:#f4efe6;font-family:Inter,sans-serif}
.k{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:24px}
.l{width:74px;height:74px;border-radius:24px;border:1px solid rgba(217,178,111,.3);display:grid;place-items:center;
background:radial-gradient(circle at 30% 25%,#2a261d,#0f1013);animation:p 2s ease-in-out infinite}
@keyframes p{50%{box-shadow:0 0 0 12px rgba(217,178,111,0)}0%{box-shadow:0 0 0 0 rgba(217,178,111,.35)}}
h1{font:600 28px Fraunces,serif;margin:0}p{color:#9a958c;font-size:13px;margin:0;line-height:1.5;max-width:300px}
.b{width:220px;height:3px;background:#22252e;border-radius:9px;overflow:hidden}.b i{display:block;height:100%;background:#d9b26f;width:__Y__%}
small{color:#66625b;font-size:11.5px}</style></head><body><div class="k">
<div class="l"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#d9b26f" stroke-width="1.6" stroke-linecap="round"><path d="M3 17l5-5 4 3 8-9"/><path d="M15 6h5v5"/></svg></div>
<h1>Radar</h1><p>__D__</p><div class="b"><i></i></div>
<small>İlk açılışta bütün borsa taranıyor. Sonraki açılışlarda sonuçlar hazır gelir.</small>__H__</div></body></html>"""


# ---------- Sayfa ----------
st.markdown("""
<style>
#MainMenu, footer, header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"] {display:none !important}
.stApp {background:#0b0c10}
.block-container {padding:0 !important; max-width:100% !important}
iframe {height:100dvh !important; display:block; border:0}
div[data-testid="stVerticalBlock"] {gap:0 !important}
</style>""", unsafe_allow_html=True)

servis = servis_al()


if servis.html is None:
    # İlk açılış: motor ilk taramayı bitirene kadar yükleme ekranı, birkaç saniyede bir yenilenir
    hata = f'<p style="color:#f0645f">{servis.hata}</p>' if servis.hata else ""
    components.html(YUKLEME.replace("__D__", servis.durum).replace("__Y__", f"{servis.ilerleme * 100:.0f}")
                    .replace("__H__", hata), height=760)
    time.sleep(3)
    st.rerun()
else:
    components.html(servis.html, height=760, scrolling=False)
