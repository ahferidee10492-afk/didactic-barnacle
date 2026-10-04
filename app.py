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
Canlı bot: sanal bütçeyle gerçek seansta sinyallere otomatik girer/çıkar, tutarlılığını ölçer.

Yatırım tavsiyesi değildir.
"""

import bisect
import datetime as dt
import json
import os
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
MODLAR = ("1", "5", "g", "w")  # 1 dk, 5 dk, 15 dk, günlük
DILIM_ADI = {"1": "1 dk", "5": "5 dk", "g": "15 dk", "w": "Günlük"}
VADE = {  # zaman dilimine göre işlemin beklenen tutma süresi
    "1": dict(ad="Scalp", sure="15–60 dakika", aciklama="Çok kısa vadeli; hızlı gir, hızlı çık. 15 dk gecikmeli veriyle risklidir, fiyatı mutlaka Midas'tan teyit et."),
    "5": dict(ad="Gün içi kısa", sure="1–3 saat", aciklama="Gün içinde kapatılacak kısa işlem."),
    "g": dict(ad="Gün içi / kısa vade", sure="3 saat – 2 gün", aciklama="Gün içi ya da ertesi güne taşınabilecek işlem."),
    "w": dict(ad="Swing", sure="1–4 hafta", aciklama="Günlük grafiğe dayalı, birkaç hafta tutulabilecek işlem."),
}
HIZLI_EVREN = 60            # 1 ve 5 dakikalık analiz için en likit hisse sayısı
MIN_LIKIDITE = 20            # milyon TL; daha sığ hisseler hiç taranmaz (ayar uygulamada ayrıca filtrelenir)
AGIRLIK = {"1": {}, "5": {}, "g": {}, "w": {}}  # kurulum karnesine göre otomatik güven düzeltmesi (arka planda güncellenir)
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


def _gun_ici(semboller: list[str], period: str = "30d", interval: str = "15m") -> dict:
    v = _toplu([f"{h}.IS" for h in semboller], period, interval)
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

    if mod != "w":   # her gün için önceki günlerin hacim profili (1 dk: 3, 5 dk: 6, 15 dk: 10 gün)
        tarih = np.array(df.index.date)
        gun_no = np.searchsorted(np.array(sorted(set(tarih))), tarih)
        pencere, en_az = {"1": 3, "5": 6}.get(mod, 10), 64
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
    if mod != "w" and gunluk is not None and len(gunluk) > 60:
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
        geri = {"1": 390, "5": 160, "g": 160, "w": 20}[mod]
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
        puan += 8; arti.append(DILIM_ADI[ctx["mod"]] + " trend " + ("yukarı" if yukari else "aşağı"))
    elif yonlu(ema50 - ema200) < 0:
        puan -= 6; eksi.append(DILIM_ADI[ctx["mod"]] + " trende karşı")
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
        puan += 15; arti.append(f"Hacim patlaması ({sayi(rv, 1)}x)")
    elif rv >= 2:
        puan += 11; arti.append(f"Çok yüksek hacim ({sayi(rv, 1)}x)")
    elif rv >= 1.5:
        puan += 7; arti.append(f"Yüksek hacim ({sayi(rv, 1)}x)")
    elif rv >= 1.2:
        puan += 3; arti.append(f"Hacim normal üstü ({sayi(rv, 1)}x)")
    elif rv < 0.8:
        puan -= 10; eksi.append(f"Hacim zayıf ({sayi(rv, 1)}x)")

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
        puan += 5; arti.append(f"Endeksten {'güçlü' if yukari else 'zayıf'} (%{'+' if rs >= 0 else '−'}{sayi(abs(rs), 1)})")
    elif yonlu(rs) < -2:
        puan -= 5; eksi.append(f"Endeksten {'zayıf' if yukari else 'güçlü'} (%{'+' if rs >= 0 else '−'}{sayi(abs(rs), 1)})")

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
        puan += 5; arti.append(f"Risk/kazanç {sayi(rk, 1)}")
    elif rk < 1.5:
        puan -= 8; eksi.append(f"Risk/kazanç düşük ({sayi(rk, 1)})")

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

    guven = int(round(100 / (1 + np.exp(-(puan - 58) / 11))))  # ham puan 58 -> 50, 80 -> 88, 95 -> 97
    return dict(tur="AL" if yukari else "SAT", yon=yon, guven=guven, guclu=bool(guclu),
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
    if ctx["mod"] != "w":
        cumle.append(f"Günlük trend {trend_metin[int(htf)]}; {DILIM_ADI[ctx['mod']]} grafikte {yapi_metin[yapi]}.")
    else:
        e50, e200 = A["EMA50"][i], A["EMA200"][i]
        cumle.append(f"Günlük grafikte {yapi_metin[yapi]}; fiyat 50 günlük ortalamanın {'üstünde' if c > e50 else 'altında'}"
                     + (f", ana trend {'yukarı' if e50 > e200 else 'aşağı'} (EMA50/200)." if not np.isnan(e200) else "."))
    vw = A["VWAP"][i]
    if not np.isnan(vw):
        fark = (c / vw - 1) * 100
        kim = "alıcılar kârda, gün içi kontrol alıcılarda" if fark > 0 else "gün içi alanlar zararda, kontrol satıcılarda"
        cumle.append(f"Fiyat gün içi ortalama maliyetin (VWAP {sayi(vw)}) %{sayi(abs(fark), 1)} {'üstünde' if fark > 0 else 'altında'}: {kim}.")
    ab, rv = nanv(A["AB"][i]), nanv(A["RVOL"][i])
    if ab > 0.15:
        cumle.append(f"Son 20 mumda hacmin belirgin kısmı alıcı yönlü (alıcı baskısı %{ab * 100:.0f}).")
    elif ab < -0.15:
        cumle.append(f"Son 20 mumda satıcılar baskın (satıcı baskısı %{-ab * 100:.0f}).")
    else:
        cumle.append("Alıcı ve satıcı dengede, hacim akışında net taraf yok.")
    if rv >= 1.5:
        cumle.append(f"Hacim {'bu saat için' if ctx['mod'] != 'w' else 'son 10 güne göre'} normalin {sayi(rv, 1)} katı — hissede ilgi var.")
    elif rv < 0.7:
        cumle.append("Hacim normalin altında; kırılımlar güvenilir olmayabilir.")
    p = ctx["prof_guncel"]
    if p:
        cumle.append(f"{({'1': 'Son 3 günde', '5': 'Son 6 günde', 'g': 'Son 10 günde'}).get(ctx['mod'], 'Son 12 haftada')} en çok işlem {sayi(p['poc'])} seviyesinde (POC); değer bölgesi {sayi(p['val'])}–{sayi(p['vah'])}.")
    destek = max([x for x in sev if x < c], default=None)
    direnc = min([x for x in sev if x > c], default=None)
    if destek and direnc:
        cumle.append(f"En yakın destek {sayi(destek)} (%{sayi((c / destek - 1) * 100, 1)} aşağıda), direnç {sayi(direnc)} (%{sayi((direnc / c - 1) * 100, 1)} yukarıda).")
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
    if tam_test:
        bas = 60 if mod in ("g", "w") else max(60, n - 450)  # 1/5 dk: son ~450 mumda test
    else:
        bas = n - TEST_UFKU - 1
    sinyaller = sinyalleri_tara(ctx, bas)
    _, formlar = sinyal_bul(ctx, n - 1)
    sev = seviyeler_bul(ctx["pv"])
    i = n - 1
    fiyat = float(df["Close"].iloc[-1])
    if mod != "w":
        dun = df[df.index.date < df.index[-1].date()]["Close"]
        degisim = (fiyat / dun.iloc[-1] - 1) * 100 if len(dun) else 0.0
    else:
        degisim = (fiyat / df["Close"].iloc[-2] - 1) * 100
    son2 = df.iloc[max(0, n - ({"1": 120, "5": 80}.get(mod, 64) if mod != "w" else 15)):n]
    birikim = 0.0
    if len(son2) >= 10:
        genislik = (son2["High"].max() - son2["Low"].min()) / max(nanv(A["ATR"][i]), 1e-9)
        cvd_egim = (son2["CVD"].iloc[-1] - son2["CVD"].iloc[0]) / max(son2["Volume"].sum(), 1)
        sinir = 10 if mod != "w" else 6
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
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#060912;--card:rgba(255,255,255,.04);--card2:rgba(255,255,255,.07);--cardS:#0d1322;--ln:rgba(255,255,255,.08);--ln2:rgba(255,255,255,.05);
--tx:#eef1f8;--mu:#8b93a7;--mu2:#5b6378;--ac:#7c6cff;--ac2:#22d3ee;--acT:#a99bff;--grad:linear-gradient(135deg,#7c6cff 0%,#22d3ee 100%);--acs:rgba(124,108,255,.16);
--up:#2fe0a0;--ups:rgba(47,224,160,.13);--dn:#ff5c7c;--dns:rgba(255,92,124,.13);--wa:#ffb547;--was:rgba(255,181,71,.15);
--r:22px;--sh:0 14px 34px -16px rgba(0,0,0,.7);--nav:rgba(13,18,32,.8)}
html.acik{--bg:#f1f3f9;--card:#ffffff;--card2:#eef1f8;--cardS:#ffffff;--ln:rgba(15,23,42,.08);--ln2:rgba(15,23,42,.05);--tx:#0f1729;--mu:#5d6779;--mu2:#9aa3b5;
--acT:#6252f5;--up:#0fae78;--ups:rgba(15,174,120,.11);--dn:#e8395e;--dns:rgba(232,57,94,.1);--wa:#d98a0b;--sh:0 12px 30px -18px rgba(30,41,80,.35);--nav:rgba(255,255,255,.86)}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--tx);font:14px/1.45 Manrope,system-ui,sans-serif;-webkit-font-smoothing:antialiased}
body{overflow:hidden}button,input,select{font-family:inherit;color:inherit}button{cursor:pointer;border:0;background:none;padding:0}
.n{font-variant-numeric:tabular-nums}
.up{color:var(--up)}.dn{color:var(--dn)}.mu{color:var(--mu)}.wa{color:var(--wa)}.act{color:var(--acT)}
.lbl{font-size:11.5px;font-weight:700;color:var(--mu)}
.aurora{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:0}
.aurora i{position:absolute;border-radius:50%;filter:blur(80px)}
.aurora i:nth-child(1){width:360px;height:360px;background:#5b47ff;opacity:.38;top:-170px;left:-120px;animation:y1 18s ease-in-out infinite alternate}
.aurora i:nth-child(2){width:300px;height:300px;background:#0ea5c6;opacity:.26;top:-110px;right:-150px;animation:y2 22s ease-in-out infinite alternate}
.aurora i:nth-child(3){width:320px;height:320px;background:#2fe0a0;opacity:.08;bottom:-180px;left:15%;animation:y1 26s ease-in-out infinite alternate-reverse}
html.acik .aurora i{opacity:.13}
@keyframes y1{to{transform:translate(70px,50px) scale(1.15)}}@keyframes y2{to{transform:translate(-60px,70px) scale(.9)}}
#app{position:relative;z-index:1;display:flex;flex-direction:column;height:100%}
/* üst */
.ust{flex:none;padding:12px 16px 6px}
.ust1{display:flex;align-items:center;gap:8px}
.logo{display:flex;align-items:center;gap:10px;margin-right:auto}
.logo svg{width:38px;height:38px;filter:drop-shadow(0 8px 16px rgba(124,108,255,.45))}
.logo b{display:block;font-size:18px;font-weight:800;letter-spacing:-.03em;line-height:1.05}
.logo b span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.logo small{display:block;white-space:nowrap;font-size:10.5px;color:var(--mu);font-weight:700;letter-spacing:.03em}
.sweep{transform-origin:20px 21px;animation:don 4s linear infinite}@keyframes don{to{transform:rotate(360deg)}}
.ikon{width:38px;height:38px;border-radius:13px;background:var(--card);border:1px solid var(--ln);display:grid;place-items:center;position:relative;transition:transform .15s;flex:none;color:var(--tx);text-decoration:none}
.ikon:active{transform:scale(.9)}.ikon svg{width:18px;height:18px}
.rz{position:absolute;top:-5px;right:-5px;background:var(--dn);color:#fff;font-size:9.5px;font-weight:800;border-radius:9px;padding:1px 5px;min-width:17px;text-align:center;box-shadow:0 0 0 2px var(--bg);animation:pop .4s cubic-bezier(.3,1.6,.5,1)}
@keyframes pop{from{transform:scale(0)}}
.canli{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:800;color:var(--mu);background:var(--card);border:1px solid var(--ln);padding:6px 10px;border-radius:99px;white-space:nowrap}
.nokta{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--mu2);flex:none}
.nokta.on{background:var(--up);animation:nabiz 1.8s infinite}.nokta.wa{background:var(--wa)}
@keyframes nabiz{0%{box-shadow:0 0 0 0 rgba(47,224,160,.6)}70%{box-shadow:0 0 0 8px rgba(47,224,160,0)}100%{box-shadow:0 0 0 0 rgba(47,224,160,0)}}
.dilim{position:relative;display:flex;margin-top:12px;background:var(--card);border:1px solid var(--ln);border-radius:15px;padding:4px}
.dilim .ind{position:absolute;top:4px;bottom:4px;left:0;border-radius:11px;background:var(--grad);box-shadow:0 8px 18px -8px rgba(124,108,255,.9);transition:transform .45s cubic-bezier(.3,1.25,.5,1),width .3s}
.dilim button{position:relative;flex:1;font-weight:800;font-size:12.5px;color:var(--mu);padding:8px 0;transition:color .3s;z-index:1}
.dilim button.on{color:#fff}
.vade-bant{display:flex;justify-content:space-between;font-size:11.5px;color:var(--mu);padding:8px 3px 2px;font-weight:600}.vade-bant b{color:var(--tx)}
main{flex:1;overflow-y:auto;padding:6px 16px 120px;-webkit-overflow-scrolling:touch;scrollbar-width:none}main::-webkit-scrollbar{display:none}
/* genel */
.kart{background:var(--card);border:1px solid var(--ln);border-radius:var(--r);box-shadow:var(--sh);position:relative;overflow:hidden}
.pad{padding:16px}
.bolum{display:flex;align-items:center;justify-content:space-between;margin:26px 2px 11px}
.bolum h3{margin:0;font-size:16px;font-weight:800;letter-spacing:-.02em}
.bolum a,.link{font-size:12.5px;font-weight:800;color:var(--acT);cursor:pointer}
.anim>*{animation:yuksel .6s cubic-bezier(.2,.8,.2,1) both}
.anim>*:nth-child(2){animation-delay:.05s}.anim>*:nth-child(3){animation-delay:.1s}.anim>*:nth-child(4){animation-delay:.15s}.anim>*:nth-child(5){animation-delay:.2s}
.anim>*:nth-child(6){animation-delay:.25s}.anim>*:nth-child(7){animation-delay:.3s}.anim>*:nth-child(8){animation-delay:.35s}.anim>*:nth-child(n+9){animation-delay:.4s}
@keyframes yuksel{from{opacity:0;transform:translateY(16px)}}
.rozet{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:800;padding:4px 10px;border-radius:99px;background:var(--card2);color:var(--mu);white-space:nowrap}
.rozet.up{background:var(--ups);color:var(--up)}.rozet.dn{background:var(--dns);color:var(--dn)}.rozet.ac{background:var(--acs);color:var(--acT)}.rozet.wa{background:var(--was);color:var(--wa)}
.yon{display:inline-block;font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:7px;letter-spacing:.03em;vertical-align:1px}
.yon.al{background:var(--ups);color:var(--up)}.yon.sat{background:var(--dns);color:var(--dn)}
.kal{display:inline-block;font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:7px;background:var(--card2);color:var(--mu);vertical-align:1px}
.kal.Ap{background:linear-gradient(135deg,#ffcf6b,#ff9f43);color:#2a1700}.kal.A{background:var(--acs);color:var(--acT)}
.dl{display:inline-block;font-size:10.5px;font-weight:700;color:var(--mu);background:var(--card2);padding:2px 7px;border-radius:7px}
.avatar{display:grid;place-items:center;border-radius:13px;font-weight:800;font-size:11.5px;color:#fff;flex:none;letter-spacing:.02em;box-shadow:inset 0 1px 0 rgba(255,255,255,.25)}
.alan{display:block;width:100%;animation:ac 1.4s cubic-bezier(.4,0,.2,1) both}
@keyframes ac{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
.buyuk{font-size:34px;font-weight:800;letter-spacing:-.035em;line-height:1.1}
.satir{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sat1{display:flex;align-items:center;justify-content:space-between;gap:10px}
.btn{flex:1;border-radius:15px;padding:13px;font-weight:800;font-size:13.5px;background:var(--card2);border:1px solid var(--ln);transition:transform .15s;display:inline-flex;align-items:center;justify-content:center;gap:7px}
.btn:active{transform:scale(.96)}.btn.ana{background:var(--grad);border:0;color:#fff;box-shadow:0 12px 24px -12px rgba(124,108,255,.95)}.btn.kir{color:var(--dn)}
.btn svg{width:16px;height:16px}
.dugmeler{display:flex;gap:8px;padding:14px 16px 16px}
.seg{display:flex;gap:4px;background:var(--card);border:1px solid var(--ln);border-radius:15px;padding:4px;margin-bottom:12px;overflow-x:auto;scrollbar-width:none}.seg::-webkit-scrollbar{display:none}
.seg button{flex:1;padding:9px 6px;font-size:12.5px;font-weight:800;color:var(--mu);border-radius:11px;transition:all .25s;white-space:nowrap}
.seg button.on{background:var(--card2);color:var(--tx);box-shadow:0 4px 12px -4px rgba(0,0,0,.4)}
.chips{display:flex;gap:7px;overflow-x:auto;margin:0 -16px 12px;padding:0 16px;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}
.chip{flex:none;color:var(--mu);background:var(--card);border:1px solid var(--ln);border-radius:99px;padding:7px 13px;font-size:12.5px;font-weight:700;transition:all .2s}
.chip.on{color:#fff;background:var(--grad);border-color:transparent;box-shadow:0 6px 14px -8px rgba(124,108,255,.9)}.chip:disabled{opacity:.35}
.bos{border:1.5px dashed var(--ln);border-radius:var(--r);padding:26px 18px;text-align:center;color:var(--mu);line-height:1.55;font-size:13px}.bos b{display:block;color:var(--tx);margin-bottom:4px;font-size:14px}
.not{color:var(--mu);font-size:12px;line-height:1.6;margin:12px 2px 0}
.acik-not{color:var(--mu);font-size:12.5px;line-height:1.55;margin:0 2px 12px}
.uyari{color:var(--mu2);font-size:10.5px;text-align:center;margin:26px 0 4px;font-weight:700;letter-spacing:.05em}
/* panel */
.hero{padding:18px 18px 0}
.hero .alan{height:96px;margin:6px -18px 0;width:calc(100% + 36px)}
.genislik{display:flex;height:8px;border-radius:99px;overflow:hidden;gap:3px;margin-top:14px}
.genislik i{display:block;border-radius:99px;transform-origin:left;animation:uza 1.1s cubic-bezier(.2,.8,.2,1) both}
@keyframes uza{from{transform:scaleX(0)}}
.gy{display:flex;justify-content:space-between;font-size:12px;color:var(--mu);padding:8px 0 16px;font-weight:600}
.kpi{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
.tile{padding:14px;border-radius:19px;background:var(--card);border:1px solid var(--ln);display:flex;gap:11px;align-items:center;cursor:pointer;transition:transform .15s}
.tile:active{transform:scale(.97)}
.tile .ik{width:40px;height:40px;border-radius:13px;display:grid;place-items:center;flex:none}.tile .ik svg{width:20px;height:20px}
.tile b{display:block;font-size:19px;font-weight:800;letter-spacing:-.02em;line-height:1.2}.tile small{font-size:11.5px;color:var(--mu);font-weight:700}
.yatay{display:flex;gap:12px;overflow-x:auto;margin:0 -16px;padding:2px 16px 8px;scroll-snap-type:x mandatory;scrollbar-width:none}.yatay::-webkit-scrollbar{display:none}
.skart{flex:none;width:236px;scroll-snap-align:start;padding:15px;cursor:pointer;transition:transform .2s}.skart:active{transform:scale(.97)}
.skart::before{content:"";position:absolute;inset:0 0 auto 0;height:3px;background:var(--up)}.skart.sat::before{background:var(--dn)}
.skart .neden{font-size:12.5px;color:var(--mu);margin:10px 0 12px;height:36px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;font-weight:600}
.uc{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.uc div{background:var(--card2);border-radius:11px;padding:7px 8px}.uc small{display:block;font-size:10px;color:var(--mu);font-weight:700}.uc b{font-size:12.5px;font-weight:800}
.halka{position:relative;width:46px;height:46px;flex:none}
.halka svg{width:100%;height:100%;transform:rotate(-90deg)}.halka circle{fill:none;stroke-width:4;stroke-linecap:round}
.halka .hz{stroke:var(--card2)}.halka .hd{stroke-dasharray:var(--v) 100;animation:hk 1.2s cubic-bezier(.2,.8,.2,1) both}
@keyframes hk{from{stroke-dasharray:0 100}}
.halka b{position:absolute;inset:0;display:grid;place-items:center;font-size:13px;font-weight:800}
.botmini{cursor:pointer;margin-top:12px;background:linear-gradient(135deg,rgba(124,108,255,.18),rgba(34,211,238,.07));border-color:rgba(124,108,255,.3)}
.botbas{display:flex;align-items:center;gap:11px}.botbas b{display:block;font-size:15px;font-weight:800}.botbas small{display:block;font-size:11.5px;color:var(--mu);font-weight:600}
.botik{width:42px;height:42px;border-radius:14px;background:var(--grad);display:grid;place-items:center;flex:none;box-shadow:0 10px 20px -10px rgba(124,108,255,.9)}
.botik svg{width:22px;height:22px;color:#fff}
.goz{animation:goz 4s infinite}@keyframes goz{0%,92%,100%{transform:scaleY(1)}95%{transform:scaleY(.1)}}
.liste>div{display:flex;align-items:center;gap:12px;padding:12px 14px;border-bottom:1px solid var(--ln2);cursor:pointer;transition:background .2s}
.liste>div:last-child{border-bottom:0}.liste>div:active{background:var(--card2)}
.ad{flex:1;min-width:0}.ad b{display:block;font-size:14px;font-weight:800}.ad small{display:block;color:var(--mu);font-size:11.5px;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.sag{text-align:right;flex:none}.sag b{display:block;font-size:14px;font-weight:800}.sag small{display:block;font-size:11.5px;font-weight:800;margin-top:2px}
.spk{flex:none;animation:ac 1.2s cubic-bezier(.4,0,.2,1) both}
.akis>div{display:flex;gap:12px;padding:13px 14px;border-bottom:1px solid var(--ln2);cursor:pointer;position:relative}
.akis>div:last-child{border-bottom:0}
.akis .ai{width:36px;height:36px;border-radius:12px;display:grid;place-items:center;flex:none;font-size:15px}
.akis .ic{flex:1;min-width:0}.akis .ic .bas{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.akis .ic .bas b{font-size:14px;font-weight:800}
.akis .ic p{margin:3px 0 0;font-size:12.5px;font-weight:600}.akis .ic small{display:block;color:var(--mu);font-size:11.5px;margin-top:3px;font-weight:600}
.akis .zaman{font-size:11.5px;color:var(--mu);font-weight:700;flex:none}
.akis .yeni{position:absolute;right:14px;bottom:13px;font-size:9.5px;font-weight:800;color:var(--acT);display:flex;align-items:center;gap:4px}
.akis .yeni::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--acT);animation:yan 1.2s infinite}
@keyframes yan{50%{opacity:.25}}
.akisbar{position:relative;height:8px;background:var(--card2);border-radius:99px;margin-top:7px;overflow:hidden}.akisbar i{position:absolute;top:0;height:100%;border-radius:99px;animation:uza 1s cubic-bezier(.2,.8,.2,1) both}
.akisbar i.sol{transform-origin:right}
.harita{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.harita div{padding:10px 2px;text-align:center;cursor:pointer;border-radius:12px;transition:transform .15s;animation:yuksel .5s both}
.harita div:active{transform:scale(.93)}.harita b{display:block;font-size:11px;font-weight:800}.harita span{font-size:10.5px;font-weight:700;opacity:.9}
/* fiş */
.fis{margin-bottom:12px}
.fis::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--up)}.fis.fsat::before{background:var(--dn)}
.fbas{display:flex;align-items:center;gap:11px;padding:15px 16px 0}
.fkur{padding:12px 16px 0;font-size:12.5px;color:var(--mu);font-weight:600;line-height:1.5}.fkur b{color:var(--tx)}
.merdiven{position:relative;height:54px;margin:14px 22px 2px}
.merdiven .hat{position:absolute;left:0;right:0;top:22px;height:6px;border-radius:9px;background:linear-gradient(90deg,var(--dn),var(--card2) 35%,var(--card2) 55%,var(--up))}
.merdiven .bolge{position:absolute;top:18px;height:14px;background:var(--acs);border:1.5px solid var(--acT);border-radius:6px}
.merdiven .im{position:absolute;top:0;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;font-size:9.5px;font-weight:800}
.merdiven .im i{display:block;width:2px;height:10px;margin-top:2px;border-radius:2px}
.merdiven .im.s{color:var(--dn)}.merdiven .im.s i{background:var(--dn)}.merdiven .im.h{color:var(--up)}.merdiven .im.h i{background:var(--up)}
.merdiven .simdi{position:absolute;top:16px;width:18px;height:18px;margin-left:-9px;border-radius:50%;background:var(--tx);border:4px solid var(--bg);box-shadow:0 0 0 2px var(--tx);animation:simdi 2s infinite}
@keyframes simdi{50%{box-shadow:0 0 0 6px rgba(124,108,255,.25)}}
.merdiven .alt{position:absolute;top:40px;font-size:10px;color:var(--mu);font-weight:700;transform:translateX(-50%);white-space:nowrap}
.ig{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;padding:10px 16px 0}
.ig>div{background:var(--card2);border-radius:13px;padding:9px 10px}
.ig small{display:block;font-size:10.5px;font-weight:700;color:var(--mu);margin-bottom:2px}.ig b{font-size:13.5px;font-weight:800}.ig em{display:block;font-size:11px;font-style:normal;font-weight:800;margin-top:1px}
.ig .genis{grid-column:span 3;display:flex;justify-content:space-between;align-items:center}
.drm{display:flex;gap:9px;margin:10px 16px 14px;padding:10px 12px;border-radius:13px;font-size:12.5px;align-items:center;color:var(--mu);font-weight:700;background:var(--card2)}
.drm i{flex:none;width:8px;height:8px;border-radius:50%}
.drm.bolgede{color:var(--up);background:var(--ups)}.drm.bolgede i{background:var(--up);animation:nabiz 1.8s infinite}.drm.kacti{color:var(--wa);background:var(--was)}.drm.kacti i{background:var(--wa)}.drm.dikkat{color:var(--dn);background:var(--dns)}.drm.dikkat i{background:var(--dn)}
.karplan{width:calc(100% - 32px);margin:0 16px;border-collapse:collapse}
.karplan td{padding:10px 2px;border-top:1px solid var(--ln2);font-size:12.5px;font-weight:600}.karplan td:nth-child(2),.karplan td:nth-child(3){text-align:right;white-space:nowrap;font-weight:800}
.lot{display:flex;justify-content:space-between;align-items:center;margin:12px 16px 0;padding:13px 14px;border-radius:15px;background:var(--acs)}
.lot b{font-size:19px;font-weight:800;color:var(--acT)}
/* tablolar */
.tbl{width:100%;border-collapse:collapse}
.tbl th{font-size:10.5px;font-weight:800;color:var(--mu2);text-align:right;padding:10px;border-bottom:1px solid var(--ln);letter-spacing:.03em}
.tbl th:first-child,.tbl td:first-child{text-align:left}
.tbl td{padding:11px 10px;border-bottom:1px solid var(--ln2);text-align:right;font-size:12.5px;white-space:nowrap;font-weight:700}
.tbl tr:last-child td{border-bottom:0}.tbl tr[data-h]{cursor:pointer}
/* bot */
.bothero{background:linear-gradient(160deg,rgba(124,108,255,.2),rgba(34,211,238,.05) 55%,var(--card));border-color:rgba(124,108,255,.32)}
.bothero::after{content:"";position:absolute;width:220px;height:220px;border-radius:50%;right:-80px;top:-90px;background:radial-gradient(circle,rgba(124,108,255,.35),transparent 70%);pointer-events:none}
#botGrafik{height:170px;margin-top:6px;position:relative}
.botalt{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 16px 0}
.botalt div{background:var(--card2);border-radius:14px;padding:10px 11px}.botalt b{display:block;font-size:16px;font-weight:800;margin-top:1px}.botalt small{font-size:10.5px;color:var(--mu);font-weight:700}
.istat{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.istat div{background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:12px}.istat b{display:block;font-size:17px;font-weight:800;margin-top:2px;letter-spacing:-.02em}
.gauge{position:relative;width:220px;max-width:100%;margin:6px auto 0}
.gauge svg{width:100%;display:block}.gauge .gd{animation:gd 1.6s cubic-bezier(.2,.8,.2,1) both}@keyframes gd{from{stroke-dasharray:0 100}}
.gauge .gv{position:absolute;left:0;right:0;bottom:2px;text-align:center}.gauge .gv b{display:block;font-size:38px;font-weight:800;letter-spacing:-.04em;line-height:1}.gauge .gv span{font-size:12.5px;font-weight:800}
.bilesen>div{margin-top:12px}.bilesen .ust3{display:flex;justify-content:space-between;font-size:12.5px;font-weight:700}
.bar{height:8px;border-radius:99px;background:var(--card2);margin-top:6px;overflow:hidden}.bar i{display:block;height:100%;border-radius:99px;background:var(--grad);transform-origin:left;animation:uza 1.2s cubic-bezier(.2,.8,.2,1) both}
.donut{display:flex;align-items:center;gap:16px}.donut svg{width:96px;height:96px;transform:rotate(-90deg);flex:none}
.donut circle{fill:none;stroke-width:12}.donut .dk{animation:hk 1.3s cubic-bezier(.2,.8,.2,1) both}
.leg{flex:1}.leg div{display:flex;justify-content:space-between;align-items:center;padding:5px 0;font-size:12.5px;font-weight:700}.leg i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:7px}
.pozkart{margin-bottom:12px}.pozkart .ilerle{position:relative;height:8px;border-radius:99px;background:var(--card2);margin:16px 16px 4px}
.pozkart .ilerle i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:linear-gradient(90deg,var(--dn),var(--wa),var(--up));transform-origin:left;animation:uza 1.2s both}
.pozkart .ilerle span{position:absolute;top:-4px;width:2px;height:16px;background:var(--mu2);border-radius:2px}
.pozkart .etk{display:flex;justify-content:space-between;font-size:10px;color:var(--mu);font-weight:800;padding:0 16px}
.gunbar{display:flex;justify-content:center;align-items:flex-end;gap:4px;height:120px;padding:10px 4px 0;position:relative}
.gunbar::after{content:"";position:absolute;left:0;right:0;top:calc(10px + var(--sifir));height:1px;background:var(--ln)}
.gunbar div{flex:1;max-width:28px;position:relative;height:100%}
.gunbar i{position:absolute;left:0;right:0;border-radius:5px;animation:boy .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes boy{from{transform:scaleY(0)}}
.log>div{display:flex;gap:11px;padding:11px 14px;border-bottom:1px solid var(--ln2)}.log>div:last-child{border-bottom:0}
.log .li{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;flex:none;font-size:13px}
.log p{margin:0;font-size:12.5px;font-weight:600;line-height:1.45}.log small{display:block;color:var(--mu);font-size:11px;font-weight:700;margin-top:2px}
.stepper{display:flex;align-items:center;justify-content:space-between;background:var(--card2);border-radius:15px;padding:6px}
.stepper button{width:40px;height:40px;border-radius:12px;background:var(--card);font-size:20px;font-weight:700;border:1px solid var(--ln)}
.stepper b{font-size:20px;font-weight:800}
.alanf{display:block;margin-bottom:14px}.alanf>.lbl{display:block;margin-bottom:7px}
.giris{width:100%;background:var(--card2);border:1px solid var(--ln);border-radius:15px;outline:0;font-size:18px;font-weight:800;padding:12px 14px}
.form-ayar{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.form-ayar label{background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:11px 12px;display:block}
.form-ayar input,.form-ayar select{width:100%;background:none;border:0;outline:0;font-size:16px;font-weight:800;padding:4px 0 0}
.form-ayar select option{background:var(--cardS)}.form-ayar .genis{grid-column:1/-1}
input[type=range]{width:100%;accent-color:#7c6cff}
select{background:var(--card);border:1px solid var(--ln);border-radius:11px;padding:7px 9px;font-size:12.5px;font-weight:700}
.ara{display:flex;align-items:center;gap:9px;background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:0 14px;margin-bottom:12px}
.ara svg{width:18px;height:18px;color:var(--mu);flex:none}
.ara input{flex:1;background:none;border:0;outline:0;font-size:15px;font-weight:800;padding:13px 0;text-transform:uppercase}
.ara input::placeholder{text-transform:none;color:var(--mu2);font-weight:600}
.sirala{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;color:var(--mu);font-size:12.5px;font-weight:700}
.yorum{padding:2px 16px 8px}.yorum div{padding:10px 0;border-bottom:1px solid var(--ln2);font-size:13px;line-height:1.55;font-weight:500}.yorum div:last-child{border-bottom:0}
.neden2{padding:4px 16px 10px}.neden2 div{padding:6px 0;font-size:13px;display:flex;gap:9px;font-weight:600}
.neden2 .p::before{content:"+";color:var(--up);font-weight:800}.neden2 .x::before{content:"−";color:var(--dn);font-weight:800}
.profil div{display:flex;align-items:center;gap:8px;font-size:10.5px;color:var(--mu2);height:13px;font-weight:700}
.profil span{width:58px;text-align:right;flex:none}.profil i{display:block;height:8px;background:var(--card2);border-radius:4px;animation:uza .9s both}
.profil .va i{background:rgba(124,108,255,.55)}.profil .poc i{background:var(--wa)}.profil .poc span{color:var(--wa)}
.profil .simdi span{color:var(--tx)}.profil .simdi::after{content:"◂";color:var(--tx)}
/* alt menü */
nav.alt{position:fixed;left:12px;right:12px;bottom:calc(10px + env(safe-area-inset-bottom));display:flex;align-items:center;background:var(--nav);backdrop-filter:blur(22px);-webkit-backdrop-filter:blur(22px);border:1px solid var(--ln);border-radius:26px;padding:6px;box-shadow:0 22px 44px -14px rgba(0,0,0,.75);z-index:10}
nav.alt button{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:7px 0;color:var(--mu2);font-size:10.5px;font-weight:800;position:relative;transition:color .3s;z-index:1}
nav.alt button svg{width:21px;height:21px;transition:transform .35s cubic-bezier(.3,1.5,.5,1)}
nav.alt button.on{color:var(--tx)}nav.alt button.on svg{transform:translateY(-1px) scale(1.1);color:var(--acT)}
.nav-ind{position:absolute;top:6px;bottom:6px;left:0;border-radius:20px;background:var(--card2);transition:transform .45s cubic-bezier(.3,1.25,.5,1),width .3s,opacity .3s}
.nav-bot .bd{width:52px;height:52px;margin-top:-28px;border-radius:19px;background:var(--grad);display:grid;place-items:center;box-shadow:0 12px 26px -8px rgba(124,108,255,.9),0 0 0 5px var(--bg);transition:transform .35s cubic-bezier(.3,1.5,.5,1)}
.nav-bot .bd svg{color:#fff!important;width:24px;height:24px}.nav-bot.on .bd{transform:translateY(-3px) rotate(-8deg)}
nav.alt .rz{top:0;right:calc(50% - 22px)}
/* detay ve sayfa altı kartlar */
#detay{position:fixed;inset:0;background:var(--bg);display:flex;flex-direction:column;transform:translateY(102%);transition:transform .5s cubic-bezier(.2,.9,.2,1);z-index:20}
#detay.ac{transform:none}
.dust{display:flex;align-items:center;gap:10px;padding:12px 16px}
.dust b{display:block;font-size:17px;font-weight:800}.dust small{display:block;color:var(--mu);font-size:11.5px;font-weight:600}
#dicerik{flex:1;overflow-y:auto;padding-bottom:30px;scrollbar-width:none}#dicerik::-webkit-scrollbar{display:none}
.dfiyat{display:flex;align-items:baseline;gap:10px;padding:4px 16px}.dfiyat b{font-size:34px;font-weight:800;letter-spacing:-.035em}
.distat{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:10px 16px 0}
.distat div{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:9px}.distat b{display:block;font-size:13.5px;font-weight:800;margin-top:2px}
.karar{margin:12px 16px 0;padding:13px 14px;border-radius:16px;background:var(--card);border:1px solid var(--ln);font-size:13px;line-height:1.55;font-weight:600;position:relative;overflow:hidden}
.karar::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--mu2)}
.karar.AL::before{background:var(--up)}.karar.SAT::before{background:var(--dn)}.karar b{font-weight:800;margin-right:6px}
.dtf{display:flex;gap:6px;padding:14px 16px 0}.dtf .chip{flex:1}
.legend{padding:10px 16px 0;height:28px;font-size:11px;color:var(--mu);white-space:nowrap;overflow:hidden;font-weight:600}.legend b{color:var(--tx)}
#grafik{height:310px}
.gsec{display:flex;gap:6px;padding:8px 16px 0;overflow-x:auto;scrollbar-width:none}.gsec::-webkit-scrollbar{display:none}.gsec .chip{padding:6px 10px;font-size:11.5px}
.ayr{width:1px;background:var(--ln);flex:none;margin:4px 2px}
.dp{padding:0 16px}
#perde{position:fixed;inset:0;background:rgba(3,6,14,.55);backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:opacity .35s;z-index:29}#perde.ac{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;max-height:90%;overflow-y:auto;background:var(--cardS);border-radius:28px 28px 0 0;border-top:1px solid var(--ln);padding:10px 18px calc(22px + env(safe-area-inset-bottom));transform:translateY(105%);transition:transform .45s cubic-bezier(.2,.9,.2,1);z-index:30}
.sheet.ac{transform:none}.tutamak{width:42px;height:5px;border-radius:9px;background:var(--ln);margin:0 auto 16px}
.sheet h2{margin:0 0 4px;font-size:20px;font-weight:800;letter-spacing:-.02em}
.toast{position:fixed;left:50%;top:16px;transform:translate(-50%,-30px);background:var(--tx);color:var(--bg);font-weight:800;font-size:13px;padding:11px 16px;border-radius:14px;opacity:0;transition:all .35s cubic-bezier(.3,1.4,.5,1);z-index:40;pointer-events:none;box-shadow:0 14px 30px -10px rgba(0,0,0,.5);max-width:90%;text-align:center}
.toast.ac{opacity:1;transform:translate(-50%,0)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs>
<linearGradient id="gLogo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c6cff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>
<linearGradient id="gSweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".55"/></linearGradient>
<linearGradient id="gGauge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff5c7c"/><stop offset=".5" stop-color="#ffb547"/><stop offset="1" stop-color="#2fe0a0"/></linearGradient>
</defs></svg>
<div class="aurora"><i></i><i></i><i></i></div>
<div id="app">
  <header class="ust" id="ust"></header>
  <main id="ekran"></main>
  <nav class="alt" id="nav"><span class="nav-ind" id="navInd"></span>
    <button data-e="panel"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z"/></svg>Panel</button>
    <button data-e="piyasa"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg>Piyasa</button>
    <button data-e="bot" class="nav-bot"><span class="bd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="8" width="16" height="12" rx="4"/><path d="M12 8V4.5"/><circle cx="12" cy="3.5" r="1.3" fill="currentColor"/><g class="goz" style="transform-origin:12px 14px"><circle cx="9" cy="14" r="1.4" fill="currentColor"/><circle cx="15" cy="14" r="1.4" fill="currentColor"/></g></svg></span>Bot</button>
    <button data-e="plan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/></svg>Planlar<b class="rz" id="rz" hidden></b></button>
    <button data-e="portfoy"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><rect x="3" y="7" width="18" height="13" rx="3"/><path d="M8 7V5.5A2.5 2.5 0 0110.5 3h3A2.5 2.5 0 0116 5.5V7"/><path d="M3 12h18"/></svg>Portföy</button>
  </nav>
</div>
<div id="detay">
  <div class="dust"><button class="ikon" id="geri"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M15 6l-6 6 6 6"/></svg></button>
    <div style="flex:1;min-width:0;display:flex;align-items:center;gap:10px" id="dad"></div>
    <button class="ikon" id="dyildiz">☆</button><a class="ikon" id="tv" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M7 17L17 7M9 7h8v8"/></svg></a></div>
  <div id="dicerik">
    <div class="dfiyat" id="dfiyat"></div>
    <div class="distat" id="distat"></div>
    <div id="dkarar"></div>
    <div class="dtf" id="dtf"></div>
    <div class="legend" id="legend"></div>
    <div id="grafik"></div>
    <div class="gsec" id="gsec"></div>
    <div class="dp">
      <div id="dplan"></div>
      <div class="seg" id="sekmeler" style="margin-top:18px"><button data-s="analiz">Analiz</button><button data-s="hacim">Hacim</button><button data-s="teknik">Teknik</button><button data-s="gecmis">Geçmiş</button></div>
      <div id="sekme"></div>
      <div class="uyari">VERİ ~15 DK GECİKMELİ · YATIRIM TAVSİYESİ DEĞİLDİR</div>
    </div>
  </div>
</div>
<div id="perde"></div>
<div id="form" class="sheet"></div>
<div class="toast" id="toast"></div>
<script type="application/json" id="veri">__VERI__</script>
<script type="application/json" id="botv">__BOT__</script>
<script type="application/json" id="mesaj">__MESAJ__</script>
<script>
const V=JSON.parse(document.getElementById('veri').textContent);
const B=JSON.parse(document.getElementById('botv').textContent);
const MESAJ=JSON.parse(document.getElementById('mesaj').textContent);
const ANIM=!(window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches);
const MODLAR=['1','5','g','w'],GOSTER={'1':'1 dk','5':'5 dk','g':'15 dk','w':'Günlük'};
const iki=v=>String(v).padStart(2,'0');
const tarihYaz=(t,g)=>{const d=new Date(t*1000);return g?`${iki(d.getUTCDate())}.${iki(d.getUTCMonth()+1)} ${iki(d.getUTCHours())}:${iki(d.getUTCMinutes())}`:`${iki(d.getUTCDate())}.${iki(d.getUTCMonth()+1)}.${d.getUTCFullYear()}`};
const saatYaz=(t,m)=>{const d=new Date(t*1000);return m==='w'?`${iki(d.getUTCDate())}.${iki(d.getUTCMonth()+1)}`:`${iki(d.getUTCHours())}:${iki(d.getUTCMinutes())}`};
const coz=(o,g)=>{if(!o)return;let t=o.m.t0;o.m=o.m.d.map(x=>{t+=x[0]*60;return[t,x[1]/100,x[2]/100,x[3]/100,x[4]/100,x[5]]});
  o.sin=o.sin.map(a=>({t:a[0],yon:a[1],tur:a[1]>0?'AL':'SAT',guven:a[2],guclu:!!a[3],fiyat:a[4],sonuc:a[5],getiri:a[6],saat:tarihYaz(a[0],g)}))};
V.hisseler.forEach(h=>MODLAR.forEach(m=>coz(h[m],m!=='w')));
const H=Object.fromEntries(V.hisseler.map(h=>[h.s,h]));
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tl=(x,d=2)=>x==null||isNaN(x)?'—':Number(x).toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d});
const yz=(x,d=2)=>x==null||isNaN(x)?'—':(x>=0?'+':'−')+tl(Math.abs(x),d)+'%';
const tlk=(x,d=0)=>x==null||isNaN(x)?'—':(x>=0?'+':'−')+tl(Math.abs(x),d)+' ₺';
const yon=x=>x>=0?'up':'dn';
const D={get(k,d){try{const v=localStorage.getItem('rt_'+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem('rt_'+k,JSON.stringify(v))}catch(e){}}};
let fav=new Set(D.get('fav',[]));
const ayar=Object.assign({sermaye:100000,risk:1,guven:65,lik:30,tema:'koyu'},D.get('ayar',{}));
function temaUygula(){document.documentElement.classList.toggle('acik',ayar.tema==='acik')}temaUygula();
const TAZE={'1':30,'5':12,'g':12,'w':5},KS={'A+':0,'A':1,'B':2,'C':3},kalCls=k=>k==='A+'?'Ap':k;
let M=D.get('mod','g');if(!MODLAR.includes(M))M='g';
const birim=m=>m==='w'?'gün':'mum';
const sureYaz=(k,m)=>m==='w'?`${k} gün`:m==='g'?`${k} mum ≈ ${tl(k/4,0)} saat`:m==='5'?`${k} mum ≈ ${tl(k*5,0)} dk`:`${k} dk`;
const ne=(s,m)=>s.once===0?(m==='w'?'bugün':'son mum'):s.once+' '+birim(m)+' önce';
let tz_;function toast(x){const t=$('#toast');t.textContent=x;t.classList.add('ac');clearTimeout(tz_);tz_=setTimeout(()=>t.classList.remove('ac'),2400)}
/* logo ve ikonlar */
const LOGO=`<svg viewBox="0 0 40 40"><rect width="40" height="40" rx="12" fill="url(#gLogo)"/><circle cx="20" cy="21" r="12" fill="none" stroke="rgba(255,255,255,.28)" stroke-width="1.4"/><circle cx="20" cy="21" r="6.5" fill="none" stroke="rgba(255,255,255,.38)" stroke-width="1.4"/>
 <g class="sweep"><path d="M20 21L20 9A12 12 0 0 1 30.4 15Z" fill="url(#gSweep)"/></g><path d="M8.5 27l6.5-6.5 4 3 9.5-10" fill="none" stroke="#fff" stroke-width="2.7" stroke-linecap="round" stroke-linejoin="round"/><circle cx="28.5" cy="13.5" r="2.7" fill="#fff"/></svg>`;
const BOTIK=`<span class="botik"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="4" y="8" width="16" height="12" rx="4"/><path d="M12 8V4.5"/><circle cx="12" cy="3.5" r="1.3" fill="currentColor"/><g class="goz" style="transform-origin:12px 14px"><circle cx="9" cy="14" r="1.4" fill="currentColor"/><circle cx="15" cy="14" r="1.4" fill="currentColor"/></g></svg></span>`;
const IK={
 hedef:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/></svg>',
 yildiz:'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.5l2.9 6 6.6.8-4.9 4.6 1.3 6.6L12 17.3l-5.9 3.2 1.3-6.6L2.5 9.3l6.6-.8z"/></svg>',
 kupa:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 01-10 0z"/><path d="M17 5h3v2a3 3 0 01-3 3M7 5H4v2a3 3 0 003 3"/></svg>',
 grafik:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/></svg>',
 zil:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 003.4 0"/></svg>',
 ayar:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><path d="M4 7h10M18 7h2M4 12h4M12 12h8M4 17h12M20 17h0"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="17" r="2"/></svg>',
 ara:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>',
 dur:'<svg viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="5" width="4" height="14" rx="1.5"/><rect x="14" y="5" width="4" height="14" rx="1.5"/></svg>',
 bas:'<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5v15a1 1 0 001.5.9l12-7.5a1 1 0 000-1.8l-12-7.5A1 1 0 007 4.5z"/></svg>'};
/* görsel yardımcılar */
function av(s,k=40){let h=7;for(const c of s)h=(h*31+c.charCodeAt(0))%360;return `<span class="avatar" style="width:${k}px;height:${k}px;font-size:${k<36?10:11.5}px;background:linear-gradient(135deg,hsl(${h} 72% 58%),hsl(${(h+45)%360} 78% 42%))">${esc(s.slice(0,3))}</span>`}
function say(v,d=0,pre='',suf=''){return `<span data-say="${v}" data-d="${d}" data-pre="${esc(pre)}" data-suf="${esc(suf)}">${pre}${tl(v,d)}${suf}</span>`}
function sayAnim(kok){if(!ANIM||!kok)return;kok.querySelectorAll('[data-say]').forEach(el=>{const v=+el.dataset.say;if(isNaN(v))return;const d=+el.dataset.d,pre=el.dataset.pre,suf=el.dataset.suf,t0=performance.now(),T=1000;
  const f=t=>{const k=Math.min((t-t0)/T,1),e=1-Math.pow(1-k,3);el.textContent=pre+tl(v*e,d)+suf;if(k<1)requestAnimationFrame(f)};requestAnimationFrame(f)})}
function yol(d,w,h,p=6){const mn=Math.min(...d),mx=Math.max(...d),k=mx-mn||1,P=d.map((v,i)=>[i/(d.length-1)*w,h-p-(v-mn)/k*(h-2*p)]);
  let s=`M${P[0][0].toFixed(1)},${P[0][1].toFixed(1)}`;for(let i=1;i<P.length;i++){const a=P[i-1],b=P[i],cx=(a[0]+b[0])/2;s+=` C${cx.toFixed(1)},${a[1].toFixed(1)} ${cx.toFixed(1)},${b[1].toFixed(1)} ${b[0].toFixed(1)},${b[1].toFixed(1)}`}return s}
let gid=0;
function alan(d,{h=96,renk}={}){if(!d||d.length<2)return'';const w=320,c=renk||(d[d.length-1]>=d[0]?'var(--up)':'var(--dn)'),y=yol(d,w,h),i='al'+(gid++);
  return `<svg class="alan" style="height:${h}px" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><defs><linearGradient id="${i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:${c};stop-opacity:.32"/><stop offset="1" style="stop-color:${c};stop-opacity:0"/></linearGradient></defs>
   <path d="${y} L${w},${h} L0,${h} Z" style="fill:url(#${i})"/><path d="${y}" style="fill:none;stroke:${c};stroke-width:2.2" vector-effect="non-scaling-stroke" stroke-linecap="round"/></svg>`}
function spark(d,w=64,h=26,r){if(!d||d.length<2)return'';const c=r||(d[d.length-1]>=d[0]?'var(--up)':'var(--dn)');
  return `<svg class="spk" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}"><path d="${yol(d,w,h,3)}" style="fill:none;stroke:${c};stroke-width:1.8" stroke-linecap="round"/></svg>`}
function halka(g,al){return `<div class="halka"><svg viewBox="0 0 44 44"><circle class="hz" cx="22" cy="22" r="18"/><circle class="hd" cx="22" cy="22" r="18" pathLength="100" style="--v:${g};stroke:${al?'var(--up)':'var(--dn)'}"/></svg><b>${g}</b></div>`}
const kap=o=>o.m.slice(-40).map(m=>m[4]);
function isi(d){const a=Math.min(Math.abs(d||0)/4,1)*.55+.1;return d>=0?`rgba(47,224,160,${a})`:`rgba(255,92,124,${a})`}
/* Streamlit sayfasına komut gönder: adres satırına ?bot=... yazar, sunucu işler */
function ustCalis(kod){try{const d=window.parent.document,s=d.createElement('script');s.textContent=kod;d.body.appendChild(s);return true}catch(e){return false}}
function ustGit(qs){toast('Gönderiliyor…');D.set('ekran','bot');if(!ustCalis('window.location.search='+JSON.stringify(qs))){try{window.top.location.search=qs}catch(e){toast('Tarayıcı izin vermedi')}}}
function yenile(){toast('Yenileniyor…');if(!ustCalis('window.location.reload()'))location.reload()}

let liste_,aktifler;
function modHazirla(m){V.hisseler.forEach(h=>{const o=h[m];if(!o)return;
  const a=o.akl.filter(s=>s.guven>=ayar.guven&&s.once<=TAZE[m]);o.akt=a.length?a[a.length-1]:null;o.sinF=o.sin.filter(s=>s.guven>=ayar.guven)})}
function hazirla(){MODLAR.forEach(modHazirla);
  liste_=V.hisseler.filter(h=>h[M]&&(h.lik||0)>=ayar.lik);
  aktifler=liste_.filter(h=>h[M].akt).sort((a,b)=>(KS[a[M].akt.kalite]-KS[b[M].akt.kalite])||(b[M].akt.guven-a[M].akt.guven)||(a[M].akt.once-b[M].akt.once));
  $('#rz').hidden=!aktifler.length;$('#rz').textContent=aktifler.length}
function yeniAkis(){const g=new Set(D.get('gorulen',[]));return V.akis.filter(o=>!g.has(o.id)).length}
function gorus(h,m){const o=h[m],s=o.akt;
  if(s){let x=s.yon>0?`${GOSTER[m]} grafiğe göre · vade ${s.vade} (${s.vade_sure}). Giriş ${tl(s.giris_alt)}–${tl(s.giris_ust)}, ilk kâr al ${tl(s.hedef)} (+%${tl(s.pot[0])}), stop ${tl(s.stop)} (−%${tl(s.risk)}).`:`${GOSTER[m]} grafiğe göre zayıflama · elinde varsa çık ya da azalt. Beklenen geri çekilme ${tl(s.hedef)} (−%${tl(s.pot[0])}); ${tl(s.stop)} üstü kapanış sinyali bozar.`;
    if(s.guclu)x+=s.yon>0?' Hacimli bölgede alıcılar aktif; bot bu sinyalde ısrarcı.':' Hacimli bölgede satıcılar baskın.';return{tur:s.tur,metin:x}}
  const p=[];if(o.tetik.ust)p.push(`${tl(o.tetik.ust)} üstünde hacimli kapanış AL tetikler`);if(o.tetik.alt)p.push(`${tl(o.tetik.alt)} altı SAT/çıkış`);
  return{tur:'BEKLE',metin:'Açık plan yok. '+(p.length?p.join('; ')+'.':'')}}

/* üst bölüm */
let indX=null;
function ustCiz(){const vd=V.vade[M],gizle=['bot','portfoy','akis'].includes(ekran),yeni=yeniAkis();
  $('#ust').innerHTML=`<div class="ust1"><div class="logo">${LOGO}<div><b>Borsa <span>Radar</span></b><small>BIST · SİNYAL BOTU</small></div></div>
   <span class="canli"><i class="nokta ${V.seans?'on':''}"></i>${V.guncelleme}</span>
   <button class="ikon" data-git="akis" title="Canlı akış">${IK.zil}${yeni?`<b class="rz">${yeni>99?'99+':yeni}</b>`:''}</button>
   <button class="ikon" data-git="profil" title="Ayarlar">${IK.ayar}</button></div>
   ${gizle?'':`<div class="dilim" id="dilim"><span class="ind" id="dind"></span>${MODLAR.map(m=>`<button data-mod="${m}" class="${M===m?'on':''}">${GOSTER[m]}</button>`).join('')}</div>
   <div class="vade-bant"><span>Vade <b>${vd.ad}</b> · ${vd.sure}</span><span>${V.likit} likit hisse</span></div>`}`;
  const on=$('#dilim button.on'),ind=$('#dind');if(on&&ind){const x=on.offsetLeft;ind.style.width=on.offsetWidth+'px';
    if(indX!=null&&ANIM){ind.style.transition='none';ind.style.transform=`translateX(${indX}px)`;ind.offsetWidth;ind.style.transition=''}ind.style.transform=`translateX(${x}px)`;indX=x}}
function navCiz(){const bs=[...document.querySelectorAll('#nav button')];bs.forEach(b=>b.classList.toggle('on',b.dataset.e===ekran));
  const on=bs.find(b=>b.dataset.e===ekran&&!b.classList.contains('nav-bot')),ind=$('#navInd');
  if(on){ind.style.width=on.offsetWidth+'px';ind.style.transform=`translateX(${on.offsetLeft}px)`;ind.style.opacity=1}else ind.style.opacity=0}

/* işlem fişi */
function merdiven(s,p){const v=[s.stop,s.giris_alt,s.giris_ust,p,s.hedef,s.hedef2,s.hedef3].filter(x=>x!=null);
  const lo=Math.min(...v),hi=Math.max(...v),k=(hi-lo)||1,x=f=>((f-lo)/k*100).toFixed(2)+'%';
  const ga=Math.min(s.giris_alt,s.giris_ust),gu=Math.max(s.giris_alt,s.giris_ust);
  return `<div class="merdiven"><div class="hat"></div><div class="bolge" style="left:${x(ga)};width:calc(${x(gu)} - ${x(ga)})"></div>
   <div class="im s" style="left:${x(s.stop)}">SL<i></i></div>${[s.hedef,s.hedef2,s.hedef3].map((h,i)=>`<div class="im h" style="left:${x(h)}">H${i+1}<i></i></div>`).join('')}
   <div class="simdi" style="left:${x(p)}"></div><div class="alt" style="left:${x(p)}">şimdi ${tl(p)}</div></div>`}
function lotHesap(s){const g=(s.giris_alt+s.giris_ust)/2,r=Math.abs(g-s.stop);if(!r)return null;
  let lot=Math.floor(ayar.sermaye*ayar.risk/100/r);lot=Math.min(lot,Math.floor(ayar.sermaye/g));return{lot,tutar:lot*g,zarar:lot*r}}
function fis(h,m,tam){const o=h[m],s=o.akt,al=s.yon>0;
  let x=`<div class="kart fis ${al?'':'fsat'}" ${tam?'':`data-h="${h.s}" data-m="${m}" style="cursor:pointer"`}>
   <div class="fbas">${av(h.s)}<div class="ad"><b>${h.s} <span class="yon ${al?'al':'sat'}">${s.tur}</span> <span class="kal ${kalCls(s.kalite)}">${s.kalite}</span></b><small>${GOSTER[m]} · ${s.vade} · ${ne(s,m)}</small></div>${halka(s.guven,al)}</div>
   <div class="fkur">${s.guclu?'<span class="rozet wa" style="margin-right:6px">🔥 Güçlü iz</span>':''}<b>${esc(s.sebepler[0])}</b>${s.sebepler.length>1?' · '+s.sebepler.slice(1).map(esc).join(' · '):''}</div>
   ${merdiven(s,o.p)}
   <div class="ig"><div class="genis"><div><small>Giriş aralığı</small><b class="act">${tl(s.giris_alt)} – ${tl(s.giris_ust)}</b></div><div style="text-align:right"><small>Risk : kazanç</small><b>1 : ${tl(s.rk,1)}</b></div></div>
    <div><small>Stop</small><b class="dn">${tl(s.stop)}</b><em class="dn">−${tl(s.risk)}%</em></div>
    <div><small>Hedef 1</small><b class="up">${tl(s.hedef)}</b><em class="up">+${tl(s.pot[0])}%</em></div>
    <div><small>Hedef 2</small><b class="up">${tl(s.hedef2)}</b><em class="up">+${tl(s.pot[1])}%</em></div></div>
   <div class="drm ${s.durum.kod}"><i></i><span>${esc(s.durum.metin)}${s.en_iyi>0?` · en iyi ${yz(s.en_iyi)}`:''}</span></div>`;
  if(tam)x+=karPlani(h,m);
  return x+'</div>'}
function karPlani(h,m){const s=h[m].akt,al=s.yon>0,L=lotHesap(s),kapanis={'1':'1 dakikalık','5':'5 dakikalık','g':'15 dakikalık','w':'günlük'}[m];
  if(!al)return `<table class="karplan"><tr><td colspan="3" class="lbl">Satış planı</td></tr>
    <tr><td>Elindeyse çık / azalt</td><td>${tl(s.giris_alt)}–${tl(s.giris_ust)}</td><td></td></tr>
    <tr><td>Geçersiz: üstünde ${kapanis} kapanış</td><td class="dn">${tl(s.stop)}</td><td class="dn">+${tl(s.risk)}%</td></tr>
    <tr><td>Beklenen düşüş (H1 / H2)</td><td>${tl(s.hedef)} / ${tl(s.hedef2)}</td><td class="dn">−${tl(s.pot[0])}%</td></tr>
    <tr><td colspan="3" class="mu" style="font-size:11.5px">Midas'ta açığa satış olmadığı için SAT, elindeki pozisyondan çıkış sinyalidir.</td></tr></table><div style="height:14px"></div>`;
  return `<table class="karplan"><tr><td colspan="3" class="lbl">Kâr al planı</td></tr>
    <tr><td>Giriş: aralıkta kademeli al</td><td class="act">${tl(s.giris_alt)}–${tl(s.giris_ust)}</td><td></td></tr>
    <tr><td>H1 → %50 sat, stopu girişe çek</td><td>${tl(s.hedef)}</td><td class="up">+${tl(s.pot[0])}%</td></tr>
    <tr><td>H2 → %30 daha sat, stop H1'e</td><td>${tl(s.hedef2)}</td><td class="up">+${tl(s.pot[1])}%</td></tr>
    <tr><td>H3 → kalan %20'yi sat</td><td>${tl(s.hedef3)}</td><td class="up">+${tl(s.pot[2])}%</td></tr>
    <tr><td>Zarar kes: ${kapanis} kapanış altı</td><td class="dn">${tl(s.stop)}</td><td class="dn">−${tl(s.risk)}%</td></tr>
    <tr><td>${sureYaz(s.kalan,m)} içinde H1 yoksa küçült</td><td colspan="2" class="mu">${s.vade}</td></tr></table>`+
   (L&&L.lot>0?`<div class="lot"><div><span class="lbl">Pozisyon · ${tl(ayar.sermaye,0)} ₺ · risk %${tl(ayar.risk,1)}</span><div class="mu" style="font-size:11.5px;margin-top:3px;font-weight:600">≈ ${tl(L.tutar,0)} ₺ · stop olursa ≈ −${tl(L.zarar,0)} ₺</div></div><b>${tl(L.lot,0)} lot</b></div>`:'')+
   `<div class="dugmeler"><button class="btn ana" data-gir="gercek">İşleme girdim</button><button class="btn" data-gir="kagit">Kağıt üstünde al</button></div>`+
   (m==='1'?`<div class="drm dikkat"><i></i>1 dk sinyalleri ~15 dk gecikmeli veriye dayanır; fiyatı Midas'tan mutlaka kontrol et.</div>`:'')}
function satirH(h,alt,m=M){const o=h[m];return `<div data-h="${h.s}" data-m="${m}">${av(h.s)}<div class="ad"><b>${h.s}${o.akt?` <span class="yon ${o.akt.yon>0?'al':'sat'}">${o.akt.tur}</span> <span class="kal ${kalCls(o.akt.kalite)}">${o.akt.kalite}</span>`:''}</b><small>${alt||h.sek}</small></div>
  ${spark(kap(o))}<div class="sag"><b class="n">${tl(o.p)}</b><small class="${yon(o.d)}">${yz(o.d)}</small></div></div>`}
function akisSatir(e,gorulen){const R={AL:['var(--ups)','var(--up)','▲'],SAT:['var(--dns)','var(--dn)','▼'],'HACİM':['var(--was)','var(--wa)','⚡'],'DÜŞÜŞ':['var(--dns)','var(--dn)','↘'],'YÜKSELİŞ':['var(--ups)','var(--up)','↗']}[e.tip]||['var(--card2)','var(--mu)','•'];
  const tipEt=e.tip==='AL'||e.tip==='SAT'?`<span class="yon ${e.tip==='AL'?'al':'sat'}">${e.tip}</span>${e.kalite?`<span class="kal ${kalCls(e.kalite)}">${e.kalite}</span>`:''}`:`<span class="rozet ${e.tip==='HACİM'?'wa':e.tip==='DÜŞÜŞ'?'dn':'up'}" style="padding:2px 8px;font-size:10.5px">${e.tip}</span>`;
  return `<div data-h="${e.s}" data-m="${e.mod}"><span class="ai" style="background:${R[0]};color:${R[1]}">${R[2]}</span>
   <div class="ic"><div class="bas"><b>${e.s}</b>${tipEt}<span class="dl">${GOSTER[e.mod]}</span></div><p>${esc(e.metin)}</p><small>${tl(e.fiyat)} · ${esc(e.alt||'')}</small></div>
   <span class="zaman">${saatYaz(e.t,e.mod)}</span>${gorulen&&!gorulen.has(e.id)?'<span class="yeni">YENİ</span>':''}</div>`}

/* PANEL */
function botMini(){const kz=B.kz||0,eg=(B.egri||[]).map(x=>x[1]);
  return `<div class="kart pad botmini" data-git="bot"><div class="sat1"><div class="botbas">${BOTIK}<div><b>Canlı Bot</b><small>${!B.aktif?'Duraklatıldı':V.seans?'Seansta işlem yapıyor':'Seans kapalı · bekliyor'} · bugün ${B.bugun.islem}/${B.ayar.gunluk}</small></div></div>
   <div style="text-align:right"><b class="n" style="font-size:16px;font-weight:800;display:block">${tl(B.ozk,0)} ₺</b><span class="rozet ${yon(kz)}" style="margin-top:3px">${yz(B.kz_yuzde)}</span></div></div>
   ${eg.length>2?`<div style="margin:10px -16px -16px">${alan(eg,{h:56})}</div>`:''}</div>`}
function ekranPanel(){const b=V.bist,yuk=liste_.filter(h=>h[M].d>0).length,dus=liste_.filter(h=>h[M].d<0).length,top=yuk+dus||1,BT=V.bot[M]||{};
  const ap=aktifler.filter(h=>KS[h[M].akt.kalite]<=1).length;
  let x=`<div class="kart hero"><div class="sat1" style="align-items:flex-start"><div><span class="lbl">BIST 100 endeksi</span><div class="buyuk n">${b?say(b.p,0):'—'}</div>
      ${b?`<div class="satir" style="margin-top:6px"><span class="rozet ${yon(b.d)}">${b.d>=0?'▲':'▼'} ${yz(b.d)}</span><span class="rozet ${b.rejim==='Boğa'?'up':b.rejim==='Ayı'?'dn':''}">${b.rejim==='Boğa'?'🐂':b.rejim==='Ayı'?'🐻':'↔'} ${b.rejim} piyasası</span></div>`:''}</div></div>
    ${b?alan(M==='w'?b.spark_w:b.spark):''}
    <div class="genislik"><i style="flex:${yuk};background:var(--up)"></i><i style="flex:${dus};background:var(--dn);transform-origin:right"></i></div>
    <div class="gy"><span><b class="up">${yuk}</b> yükselen</span><span>piyasa genişliği</span><span><b class="dn">${dus}</b> düşen</span></div></div>`;
  x+=botMini();
  x+=`<div class="kpi"><div class="tile" data-git="plan"><span class="ik" style="background:var(--acs);color:var(--acT)">${IK.hedef}</span><div><b>${say(aktifler.length)}</b><small>Taze plan</small></div></div>
    <div class="tile" data-git="plan"><span class="ik" style="background:var(--was);color:var(--wa)">${IK.yildiz}</span><div><b>${say(ap)}</b><small>A+ / A kalite</small></div></div>
    <div class="tile" data-git="bot"><span class="ik" style="background:var(--ups);color:var(--up)">${IK.kupa}</span><div><b>${BT.n?say(BT.kazanma,0,'%'):'—'}</b><small>Test kazanma</small></div></div>
    <div class="tile" data-git="bot"><span class="ik" style="background:${(BT.getiri||0)>=0?'var(--ups)':'var(--dns)'};color:${(BT.getiri||0)>=0?'var(--up)':'var(--dn)'}">${IK.grafik}</span><div><b class="${yon(BT.getiri||0)}">${BT.n?yz(BT.getiri,1):'—'}</b><small>Test getirisi</small></div></div></div>`;
  const en=aktifler.slice(0,10);
  x+=`<div class="bolum"><h3>En iyi kurulumlar</h3><a data-git="plan">Tümü →</a></div>`;
  x+=en.length?`<div class="yatay">${en.map(h=>{const s=h[M].akt,al=s.yon>0;return `<div class="kart skart ${al?'':'sat'}" data-h="${h.s}" data-m="${M}">
      <div class="sat1"><div class="satir" style="gap:10px;flex-wrap:nowrap">${av(h.s,38)}<div><b style="font-size:15px;font-weight:800">${h.s}</b><div style="margin-top:2px"><span class="yon ${al?'al':'sat'}">${s.tur}</span> <span class="kal ${kalCls(s.kalite)}">${s.kalite}</span></div></div></div>${halka(s.guven,al)}</div>
      <div class="neden">${esc(s.sebepler[0])}</div>
      <div class="uc"><div><small>Giriş</small><b>${tl(s.giris_ust)}</b></div><div><small>H1</small><b class="up">+${tl(s.pot[0],1)}%</b></div><div><small>Stop</small><b class="dn">−${tl(s.risk,1)}%</b></div></div></div>`}).join('')}</div>`
    :`<div class="bos"><b>Bu dilimde taze plan yok</b>Diğer zaman dilimlerine bak ya da güven eşiğini düşür.</div>`;
  const g=new Set(D.get('gorulen',[]));const ak=V.akis.filter(e=>!(e.tip==='AL'||e.tip==='SAT')||e.guven>=ayar.guven).slice(0,5);
  x+=`<div class="bolum"><h3>Canlı akış</h3><a data-git="akis">Tümü →</a></div>`+(ak.length?`<div class="kart akis">${ak.map(e=>akisSatir(e,g)).join('')}</div>`:`<div class="bos">Henüz olay yok</div>`);
  if(V.sektorler.length){const s=V.sektorler.filter(k=>k.ad!=='Diğer');
    x+=`<div class="bolum"><h3>Sektör para akışı</h3><a data-git="sektor">Detay →</a></div><div class="kart pad">${s.slice(0,6).map(k=>`<div style="padding:6px 0;cursor:pointer" data-sek="${esc(k.ad)}"><div class="sat1" style="font-size:13px;font-weight:700"><span>${esc(k.ad)}</span><span class="${yon(k.akis)}" style="font-weight:800">${k.akis>=0?'+':'−'}${tl(Math.abs(k.akis*100),0)}%</span></div>
      <div class="akisbar"><i class="${k.akis>=0?'':'sol'}" style="${k.akis>=0?`left:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--up)`:`right:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--dn)`}"></i></div></div>`).join('')}</div>`}
  const ls=[...liste_].sort((a,b)=>(b.lik||0)-(a.lik||0)).slice(0,30);
  x+=`<div class="bolum"><h3>Isı haritası</h3><span class="lbl">en likit 30</span></div><div class="harita">${ls.map((h,i)=>`<div data-h="${h.s}" data-m="${M}" style="background:${isi(h[M].d)};animation-delay:${i*15}ms"><b>${h.s}</b><span>${yz(h[M].d,1)}</span></div>`).join('')}</div>`;
  return x}

/* AKIŞ */
let af=D.get('af','tumu'),adl=D.get('adl','tumu');
function ekranAkis(){const g=new Set(D.get('gorulen',[]));
  let l=V.akis.filter(e=>(adl==='tumu'||e.mod===adl)&&(af==='tumu'||(af==='sinyal'&&(e.tip==='AL'||e.tip==='SAT'))||(af==='hacim'&&e.tip==='HACİM')||(af==='hareket'&&(e.tip==='DÜŞÜŞ'||e.tip==='YÜKSELİŞ'))));
  l=l.filter(e=>!(e.tip==='AL'||e.tip==='SAT')||e.guven>=ayar.guven);
  const c=(k,a,v,x)=>`<button class="chip${v===k?' on':''}" data-${x}="${k}">${a}</button>`;
  const x=`<div class="bolum" style="margin-top:8px"><h3>Canlı akış</h3><span class="lbl">${l.length} olay</span></div>
   <div class="chips">${c('tumu','Tümü',af,'af')}${c('sinyal','Sinyaller',af,'af')}${c('hacim','⚡ Hacim patlaması',af,'af')}${c('hareket','Sert hareket',af,'af')}</div>
   <div class="chips">${c('tumu','Tüm dilimler',adl,'adl')}${MODLAR.map(m=>c(m,GOSTER[m],adl,'adl')).join('')}</div>`+
   (l.length?`<div class="kart akis">${l.map(e=>akisSatir(e,g)).join('')}</div>`:`<div class="bos">Bu filtrede olay yok</div>`);
  setTimeout(()=>{V.akis.forEach(e=>g.add(e.id));D.set('gorulen',[...g].slice(-1500))},2500);
  return x}

/* PLANLAR */
let pf=D.get('pf','ust');
function ekranPlan(){let l=[...aktifler];
  if(pf==='ust')l=l.filter(h=>KS[h[M].akt.kalite]<=1);if(pf==='al')l=l.filter(h=>h[M].akt.yon>0);if(pf==='sat')l=l.filter(h=>h[M].akt.yon<0);if(pf==='bolgede')l=l.filter(h=>h[M].akt.durum.kod==='bolgede');
  const b=(k,a)=>`<button data-pf="${k}" class="${pf===k?'on':''}">${a}</button>`;
  return `<div class="seg">${b('ust','A+ / A')}${b('tumu','Tümü')}${b('bolgede','Girişte')}${b('al','AL')}${b('sat','SAT')}</div>
   <p class="acik-not">${GOSTER[M]} grafikteki taze planlar (son ${TAZE[M]} ${birim(M)}). ${V.vade[M].aciklama}</p>`+
   (l.length?l.map(h=>fis(h,M,false)).join(''):`<div class="bos"><b>Bu filtrede plan yok</b>Güven eşiği ${ayar.guven} · ayarlardan değiştirebilirsin.</div>`)}

/* PİYASA */
let pg=D.get('pg','liste'),mf=D.get('mf','tumu'),ms=D.get('ms','degisim'),q='',sekSec=null;
function piyasaListe(){let l=liste_.filter(h=>!q||h.s.includes(q));if(sekSec)l=l.filter(h=>h.sek===sekSec);
  if(mf==='plan')l=l.filter(h=>h[M].akt);if(mf==='hacim')l=l.filter(h=>(h[M].rv||0)>=1.5);if(mf==='alici')l=l.filter(h=>(h[M].ab||0)>.15);
  if(mf==='form')l=l.filter(h=>h[M].form.some(f=>f.durum==='oluşuyor'));if(mf==='fav')l=l.filter(h=>fav.has(h.s));
  const k={degisim:h=>h[M].d||0,hacim:h=>h[M].rv||0,alici:h=>h[M].ab||0,likidite:h=>h.lik||0}[ms];
  if(k)l.sort((a,b)=>k(b)-k(a));else l.sort((a,b)=>a.s.localeCompare(b.s));return l}
function piyasaIcerik(){const l=piyasaListe();if(!l.length)return `<div class="bos">Sonuç yok</div>`;
  if(pg==='harita')return `<div class="harita">${l.map((h,i)=>`<div data-h="${h.s}" data-m="${M}" style="background:${isi(h[M].d)};animation-delay:${Math.min(i,60)*10}ms"><b>${h.s}</b><span>${yz(h[M].d,1)}</span></div>`).join('')}</div>`;
  return `<div class="kart liste">${l.slice(0,300).map(h=>satirH(h,`${h.sek} · hacim ${tl(h[M].rv,1)}x · alıcı %${tl((1+(h[M].ab||0))*50,0)}`)).join('')}</div>`}
function ekranPiyasa(){const b=(k,a)=>`<button data-pg="${k}" class="${pg===k?'on':''}">${a}</button>`;
  let x=`<div class="seg">${b('liste','Liste')}${b('sektor','Sektörler')}${b('harita','Isı haritası')}</div>`;
  if(pg==='sektor')return x+`<p class="acik-not">Bugün sektörlerde işlem hacminin alıcı yönlü payı (15 dk verisiyle).</p>`+V.sektorler.map(k=>`<div class="kart pad" style="margin-bottom:10px">
    <div class="sat1"><b style="font-size:14.5px;font-weight:800">${esc(k.ad)}</b><span class="rozet ${yon(k.akis)}">${k.akis>=0?'Giriş':'Çıkış'} %${tl(Math.abs(k.akis*100),0)}</span></div>
    <div class="mu" style="font-size:12px;margin-top:3px;font-weight:600">${k.n} hisse · ort. ${yz(k.d)} · ${tl(Math.abs(k.tl),0)} mn ₺ net</div>
    <div class="akisbar"><i class="${k.akis>=0?'':'sol'}" style="${k.akis>=0?`left:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--up)`:`right:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--dn)`}"></i></div>
    <div class="chips" style="margin:12px -16px 0;padding:0 16px">${k.hisseler.map(s=>H[s]&&H[s].g?`<button class="chip" data-h="${s}" data-m="g">${s} <span class="${yon(H[s].g.d)}">${yz(H[s].g.d,1)}</span></button>`:'').join('')}</div></div>`).join('');
  const c=(k,a)=>`<button class="chip${mf===k?' on':''}" data-mf="${k}">${a}</button>`,o=(k,a)=>`<option value="${k}"${ms===k?' selected':''}>${a}</option>`;
  return x+`<div class="ara">${IK.ara}<input id="q" placeholder="Hisse ara (THYAO, ASELS…)" value="${esc(q)}" autocomplete="off"></div>
   ${sekSec?`<div class="chips"><button class="chip on" data-sektemizle="1">${esc(sekSec)} ✕</button></div>`:''}
   <div class="chips">${c('tumu','Tümü')}${c('plan','Planı olan')}${c('hacim','Hacimli')}${c('alici','Alıcılı')}${c('form','Formasyon')}${c('fav','★ Favori')}</div>
   <div class="sirala"><span>${liste_.length} hisse${M==='1'||M==='5'?' · en likitler':''}</span><select id="ms">${o('degisim','Değişim')}${o('hacim','Göreli hacim')}${o('alici','Alıcı baskısı')}${o('likidite','İşlem hacmi')}${o('ad','A-Z')}</select></div>
   <div id="pliste">${piyasaIcerik()}</div>`}

/* CANLI BOT */
let bt=D.get('bt','ozet'),botChart=null;
const SEBEP_R={H1:'up',H2:'up',H3:'up','Stop':'dn','Başabaş stop':'','İz süren stop':'up','Süre doldu':'wa','SAT sinyali':'wa','Gün sonu':'wa','Elle kapatıldı':''};
function ekranBot(){const a=B.ayar,kz=B.kz||0;
  const durum=!B.aktif?['wa','wa','Duraklatıldı']:V.seans?['up','on','Canlı işlemde']:['','','Seans kapalı · bekliyor'];
  let x=`<div class="kart bothero"><div class="pad" style="padding-bottom:0;position:relative;z-index:1">
    <div class="sat1"><div class="botbas">${BOTIK}<div><b>Canlı Bot</b><small>${GOSTER[a.dilim]} · ${V.vade[a.dilim].ad} · ${B.baslangic}'ten beri</small></div></div><span class="rozet ${durum[0]}"><i class="nokta ${durum[1]}"></i>${durum[2]}</span></div>
    <div class="lbl" style="margin-top:18px">Toplam değer · ${tl(a.butce,0)} ₺ sanal bütçe</div>
    <div class="buyuk n">${say(B.ozk,0,'','')} <span style="font-size:22px;color:var(--mu)">₺</span></div>
    <div class="satir" style="margin-top:6px"><span class="rozet ${yon(kz)}">${kz>=0?'▲':'▼'} ${tlk(kz)} · ${yz(B.kz_yuzde)}</span>${B.bist!=null?`<span class="rozet">BIST100 aynı dönem ${yz(B.bist)}</span>`:''}</div></div>
   <div id="botGrafik"></div>
   <div class="botalt"><div><small>Bugün</small><b>${B.bugun.islem}<span class="mu" style="font-size:12px">/${a.gunluk}</span></b><small>işlem</small></div><div><small>Açık</small><b>${B.poz.length}<span class="mu" style="font-size:12px">/${a.acik}</span></b><small>pozisyon</small></div><div><small>Nakit</small><b>${tl(B.nakit,0)}</b><small>₺</small></div></div>
   <div class="dugmeler"><button class="btn" data-bot="${B.aktif?'durdur':'baslat'}">${B.aktif?IK.dur+' Duraklat':IK.bas+' Başlat'}</button><button class="btn ana" data-botayar="1">${IK.ayar} Bot ayarları</button></div></div>`;
  const b=(k,t)=>`<button data-bt="${k}" class="${bt===k?'on':''}">${t}</button>`;
  x+=`<div class="seg" style="margin-top:16px">${b('ozet','Özet')}${b('poz','Pozisyon'+(B.poz.length?' · '+B.poz.length:''))}${b('islem','İşlemler')}${b('gun','Günlük')}${b('log','Kayıt')}</div><div>${({ozet:botOzet,poz:botPoz,islem:botIslem,gun:botGun,log:botLog}[bt]||botOzet)()}</div>`;
  return x}
function botOzet(){const s=B.st||{},az=s.n<5;
  const sk=s.skor??0,renk=sk>=60?'up':sk>=45?'wa':'dn';
  const bil=[['Kazanma oranı',s.kazanma,s.kazanma==null?'—':'%'+tl(s.kazanma,0)],['Kâr faktörü',s.pf==null?null:Math.min(s.pf/2,1)*100,s.pf==null?'—':tl(s.pf,2)],
    ['Kârlı gün oranı',s.karli_gun,s.karli_gun==null?'—':'%'+tl(s.karli_gun,0)],['Düşüş kontrolü',Math.max(0,1-Math.abs(s.dd||0)/10)*100,yz(s.dd,1)]];
  let x=`<div class="kart pad"><div class="sat1"><div><b style="font-size:15px;font-weight:800">Tutarlılık skoru</b><div class="mu" style="font-size:12px;font-weight:600">Bot ne kadar istikrarlı kâr üretiyor</div></div><span class="rozet ${az?'':renk}">${esc(s.etiket)}</span></div>
    <div class="gauge"><svg viewBox="0 0 200 112"><path d="M18 102A82 82 0 0 1 182 102" fill="none" style="stroke:var(--card2)" stroke-width="16" stroke-linecap="round"/>
     <path class="gd" d="M18 102A82 82 0 0 1 182 102" fill="none" stroke="url(#gGauge)" stroke-width="16" stroke-linecap="round" pathLength="100" stroke-dasharray="${az?0:sk} 100"/></svg>
     <div class="gv"><b class="${az?'mu':renk}">${az?'—':say(sk)}</b><span class="mu">${az?`en az 5 işlem gerekli · şu an ${s.n}`:'100 üzerinden'}</span></div></div>
    <div class="bilesen">${bil.map(([ad,v,yazi])=>`<div><div class="ust3"><span class="mu">${ad}</span><span>${yazi}</span></div><div class="bar"><i style="width:${Math.max(0,Math.min(v||0,100))}%"></i></div></div>`).join('')}</div></div>`;
  x+=`<div class="istat" style="margin-top:12px"><div><span class="lbl">İşlem</span><b>${say(s.n)}</b></div><div><span class="lbl">Kazanma</span><b>${s.kazanma==null?'—':'%'+tl(s.kazanma,0)}</b></div><div><span class="lbl">Kâr faktörü</span><b class="${(s.pf||0)>=1?'up':'dn'}">${s.pf==null?'—':tl(s.pf,2)}</b></div>
    <div><span class="lbl">Ort. R</span><b class="${yon(s.ortR||0)}">${s.ortR==null?'—':(s.ortR>=0?'+':'')+tl(s.ortR,2)}</b></div><div><span class="lbl">İşlem başı</span><b class="${yon(s.beklenti||0)}">${s.beklenti==null?'—':tlk(s.beklenti)}</b></div><div><span class="lbl">Maks. düşüş</span><b class="dn">${yz(s.dd,1)}</b></div></div>`;
  const kaz=s.kazanan||0,kay=s.kaybeden||0,t=kaz+kay||1;
  x+=`<div class="kart pad" style="margin-top:12px"><div class="donut"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="48" style="stroke:var(--dns)"/>${kaz?`<circle class="dk" cx="60" cy="60" r="48" pathLength="100" style="stroke:var(--up);stroke-dasharray:${kaz/t*100} 100;--v:${kaz/t*100}"/>`:''}</svg>
    <div class="leg"><div><span><i style="background:var(--up)"></i>Kazanan</span><b>${kaz}</b></div><div><span><i style="background:var(--dn)"></i>Kaybeden</span><b>${kay}</b></div>
     <div><span class="mu">Ort. kazanç / kayıp</span><b><span class="up">${s.ort_kaz==null?'—':tl(s.ort_kaz,0)}</span> / <span class="dn">${s.ort_kay==null?'—':tl(Math.abs(s.ort_kay),0)}</span></b></div>
     <div><span class="mu">En uzun seri</span><b><span class="up">${s.seri_k||0}K</span> · <span class="dn">${s.seri_z||0}Z</span></b></div></div></div></div>`;
  const BT=V.bot[B.ayar.dilim]||{};
  x+=`<div class="bolum"><h3>Geçmiş test</h3><span class="lbl">${GOSTER[B.ayar.dilim]} · simülasyon</span></div>`+(BT.n?`<div class="kart pad"><div class="sat1"><div><span class="lbl">Bot bu kurallarla geçmişte</span><div class="buyuk ${yon(BT.getiri)}" style="font-size:28px">${yz(BT.getiri,1)}</div></div>
     <div style="text-align:right" class="mu"><b style="color:var(--tx);font-size:15px">${BT.n}</b> işlem<br>%${tl(BT.kazanma,0)} kazanma<br>${yz(BT.dd,1)} maks. düşüş</div></div>
     <div style="margin:8px -16px -16px">${alan(BT.egri,{h:64})}</div></div><p class="not">Her gün en güçlü 3 sinyal, işlem başı %1 risk. Gerçek bot sonuçlarıyla karşılaştırarak modelin canlıda tutarlı olup olmadığını görebilirsin.</p>`
     :`<div class="bos"><b>Geçmiş test hazırlanıyor</b>Derin tarama arka planda yapılıyor.</div>`);
  return x}
function botPoz(){if(!B.poz.length)return `<div class="bos"><b>Açık pozisyon yok</b>${B.aktif?(V.seans?'Bot uygun sinyal bekliyor. Taze ve kaliteli bir AL sinyali fiyat giriş aralığındayken otomatik girer.':'Seans açılınca bot sinyalleri izlemeye başlar.'):'Bot duraklatıldı.'}</div>`;
  return B.poz.map(p=>{const lo=p.stop0,hi=p.h[2],k=(hi-lo)||1,x=v=>Math.max(0,Math.min(100,(v-lo)/k*100));
    return `<div class="kart pozkart"><div class="fbas">${av(p.s)}<div class="ad"><b>${p.s} <span class="dl">${GOSTER[p.mod]}</span> <span class="kal ${kalCls(p.kalite)}">${p.kalite}</span></b><small>${p.saat} · ${esc(p.sebep)}</small></div>
      <div class="sag"><b class="${yon(p.kz)}">${tlk(p.kz)}</b><small class="${yon(p.yuzde)}">${yz(p.yuzde)}</small></div></div>
     <div class="ilerle"><i style="width:${x(p.fiyat)}%"></i><span style="left:${x(p.giris)}%"></span><span style="left:${x(p.h[0])}%"></span><span style="left:${x(p.h[1])}%"></span></div>
     <div class="etk"><span class="dn">SL ${tl(p.stop0)}</span><span>giriş · H1 · H2</span><span class="up">H3 ${tl(p.h[2])}</span></div>
     <div class="ig"><div><small>Giriş</small><b>${tl(p.giris)}</b></div><div><small>Şimdi</small><b class="${yon(p.fiyat-p.giris)}">${tl(p.fiyat)}</b></div><div><small>Lot</small><b>${p.kalan}<span class="mu">/${p.lot}</span></b></div>
      <div><small>Stop</small><b class="dn">${tl(p.stop)}</b><em class="mu">${p.kademe?'kâr korumalı':'ilk stop'}</em></div><div><small>Sıradaki hedef</small><b class="up">${p.kademe<3?tl(p.h[p.kademe]):'—'}</b><em class="mu">H${p.kademe+1}</em></div><div><small>Geçen</small><b>${p.bar}</b><em class="mu">${birim(p.mod)}</em></div></div>
     <div class="dugmeler"><button class="btn" data-h="${p.s}" data-m="${p.mod}">${IK.grafik} Grafik</button><button class="btn kir" data-botkapat="${p.id}">Kapat</button></div></div>`}).join('')+
   (B.poz.length>1?`<button class="btn kir" style="width:100%" data-bothepsi="1">Tüm pozisyonları kapat</button>`:'')}
function botIslem(){if(!B.islem.length)return `<div class="bos"><b>Henüz kapanan işlem yok</b>Bot ilk işlemlerini kapattıkça burada sonuçlar ve R katları listelenir.</div>`;
  return `<div class="kart liste">${B.islem.map(t=>`<div data-h="${t.s}" data-m="${t.mod}">${av(t.s,36)}<div class="ad"><b>${t.s} <span class="rozet ${SEBEP_R[t.sebep]||''}" style="padding:2px 8px;font-size:10.5px">${esc(t.sebep)}</span></b><small>${t.g} → ${t.c} · ${t.lot} lot · ${tl(t.giris)} → ${tl(t.cikis)}</small></div>
    <div class="sag"><b class="${yon(t.kz)}">${tlk(t.kz)}</b><small class="${yon(t.R)}">${yz(t.yuzde,1)} · ${t.R>=0?'+':''}${tl(t.R,1)}R</small></div></div>`).join('')}</div>`}
function botGun(){const g=B.gunler||[];if(!g.length)return `<div class="bos"><b>Günlük veri yok</b>Bot seansta çalıştıkça her günün sonucu burada çubuk grafik olarak birikir.</div>`;
  const son=g.slice(-20),mx=Math.max(...son.map(x=>Math.abs(x.kz)),1),pos=Math.max(...son.map(x=>x.kz),0),neg=Math.min(...son.map(x=>x.kz),0),aralik=(pos-neg)||1,h=110,sifir=pos/aralik*h;
  const s=B.st||{};
  return `<div class="kart pad"><div class="sat1"><b style="font-weight:800">Günlük kâr / zarar</b><span class="lbl">son ${son.length} gün</span></div>
    <div class="gunbar" style="--sifir:${sifir}px;height:${h+10}px">${son.map((x,i)=>{const b=Math.abs(x.kz)/aralik*h;return `<div title="${x.g}"><i style="height:${Math.max(b,2)}px;top:${x.kz>=0?sifir-b:sifir}px;background:${x.kz>=0?'var(--up)':'var(--dn)'};transform-origin:${x.kz>=0?'bottom':'top'};animation-delay:${i*40}ms"></i></div>`}).join('')}</div>
    <div class="satir" style="justify-content:space-between;margin-top:10px"><span class="rozet up">Kârlı gün %${s.karli_gun??'—'}</span><span class="rozet">Günlük oynaklık ${s.std==null?'—':'%'+tl(s.std,2)}</span></div></div>
   <div class="kart" style="margin-top:12px"><table class="tbl"><tr><th>Gün</th><th>İşlem</th><th>K/Z</th><th>Getiri</th></tr>${[...g].reverse().map(x=>`<tr><td>${x.g}</td><td>${x.islem}</td><td class="${yon(x.kz)}">${tlk(x.kz)}</td><td class="${yon(x.ret)}">${yz(x.ret)}</td></tr>`).join('')}</table></div>`}
function botLog(){const R={al:['var(--acs)','var(--acT)','＋'],kar:['var(--ups)','var(--up)','◐'],kazanc:['var(--ups)','var(--up)','✓'],zarar:['var(--dns)','var(--dn)','✕'],bilgi:['var(--card2)','var(--mu)','i']};
  return B.log.length?`<div class="kart log">${B.log.map(l=>{const r=R[l[1]]||R.bilgi;return `<div ${l[3]?`data-h="${l[3]}" style="cursor:pointer"`:''}><span class="li" style="background:${r[0]};color:${r[1]}">${r[2]}</span><div><p>${l[3]?`<b>${l[3]}</b> · `:''}${esc(l[2])}</p><small>${l[0]}</small></div></div>`}).join('')}</div>`:`<div class="bos">Kayıt yok</div>`}
function botGrafikKur(){if(botChart){botChart.remove();botChart=null}const el=$('#botGrafik');if(!el)return;
  const eg=(B.egri||[]).filter((x,i,a)=>!i||x[0]>a[i-1][0]);
  if(eg.length<2||!window.LightweightCharts){el.innerHTML=`<div style="height:100%;display:grid;place-items:center;color:var(--mu);font-size:12.5px;font-weight:700">Grafik bot işlem yaptıkça çizilecek</div>`;return}
  const css=getComputedStyle(document.documentElement),cv=k=>css.getPropertyValue(k).trim(),up=(B.ozk>=B.ayar.butce),c=up?'#2fe0a0':'#ff5c7c';
  botChart=LightweightCharts.createChart(el,{width:el.clientWidth,height:170,layout:{background:{type:'solid',color:'transparent'},textColor:cv('--mu'),fontFamily:'Manrope',fontSize:10},
    grid:{vertLines:{visible:false},horzLines:{color:cv('--ln2')}},rightPriceScale:{borderVisible:false,scaleMargins:{top:.15,bottom:.08}},timeScale:{borderVisible:false,timeVisible:true,secondsVisible:false},
    crosshair:{mode:0,vertLine:{color:cv('--mu2'),labelBackgroundColor:'#7c6cff'},horzLine:{color:cv('--mu2'),labelBackgroundColor:'#7c6cff'}},handleScroll:false,handleScale:false,localization:{locale:'tr-TR',priceFormatter:p=>tl(p,0)}});
  const s=botChart.addAreaSeries({lineColor:c,topColor:up?'rgba(47,224,160,.35)':'rgba(255,92,124,.35)',bottomColor:'rgba(0,0,0,0)',lineWidth:2.5,priceLineVisible:false});
  s.setData(eg.map(x=>({time:x[0]+10800,value:x[1]})));s.createPriceLine({price:B.ayar.butce,color:cv('--mu2'),lineStyle:2,lineWidth:1,axisLabelVisible:true,title:'bütçe'});
  botChart.timeScale().fitContent();new ResizeObserver(()=>botChart&&botChart.applyOptions({width:el.clientWidth})).observe(el)}
function botAyarAc(){const a=Object.assign({},B.ayar);
  const sec=(ad,liste,v,yazi)=>`<div class="chips" style="margin:0 0 4px;padding:0;flex-wrap:wrap">${liste.map(k=>`<button class="chip${String(v)===String(k)?' on':''}" data-sec="${ad}" data-v="${k}">${yazi?yazi(k):k}</button>`).join('')}</div>`;
  const ciz=()=>{$('#form').innerHTML=`<div class="tutamak"></div><h2>Bot ayarları</h2><p class="acik-not">Bot sanal bütçeyle gerçek seans verisinde işlem yapar; parana dokunmaz. Sonuçlar modelin canlıda ne kadar tutarlı olduğunu gösterir.</p>
    <label class="alanf"><span class="lbl">Sanal bütçe (₺)</span><input class="giris" id="b_butce" inputmode="numeric" value="${tl(a.butce,0)}"></label>
    <div class="form-ayar" style="margin-bottom:14px"><div><span class="lbl" style="display:block;margin-bottom:7px">Günlük işlem sayısı</span><div class="stepper"><button data-adim="gunluk:-1">−</button><b>${a.gunluk}</b><button data-adim="gunluk:1">+</button></div></div>
     <div><span class="lbl" style="display:block;margin-bottom:7px">Aynı anda pozisyon</span><div class="stepper"><button data-adim="acik:-1">−</button><b>${a.acik}</b><button data-adim="acik:1">+</button></div></div></div>
    <div class="alanf"><span class="lbl">Zaman dilimi (vade)</span>${sec('dilim',MODLAR,a.dilim,k=>GOSTER[k])}<div class="mu" style="font-size:12px;font-weight:600;margin-top:4px">${V.vade[a.dilim].ad} · ${V.vade[a.dilim].sure}</div></div>
    <div class="alanf"><span class="lbl">İşlem başı risk</span>${sec('risk',[0.5,1,1.5,2,3],a.risk,k=>'%'+tl(k,1))}</div>
    <div class="alanf"><span class="lbl">En düşük sinyal kalitesi</span>${sec('kalite',['A+','A','B'],a.kalite,k=>k+(k==='B'?' ve üstü':k==='A'?' ve üstü':' sadece'))}</div>
    <label class="alanf"><span class="lbl">En düşük güven: <b class="act" id="b_gv">${a.guven}</b></span><input type="range" id="b_guven" min="50" max="90" step="5" value="${a.guven}"></label>
    <div class="dugmeler" style="padding:6px 0 0"><button class="btn ana" id="b_kaydet">Kaydet</button></div>
    <button class="btn kir" style="width:100%;margin-top:10px" id="b_sifirla">Sıfırla ve yeni bütçeyle başlat</button>
    <p class="not">Bütçe değişikliği, bot henüz işlem yapmadıysa hemen uygulanır; yaptıysa sıfırlama gerekir. Giriş/çıkışta %0,05 kayma hesaba katılır. 1 ve 5 dk işlemleri gün sonunda kapatılır.</p>`};
  ciz();sheetAc();
  $('#form').onclick=e=>{const t=e.target.closest('[data-sec],[data-adim],#b_kaydet,#b_sifirla');if(!t)return;
    a.butce=parseFloat(String($('#b_butce').value).replace(/\./g,'').replace(',','.'))||a.butce;a.guven=+$('#b_guven').value;
    if(t.dataset.sec){a[t.dataset.sec]=t.dataset.sec==='risk'?+t.dataset.v:t.dataset.v;ciz();baglaGv()}
    else if(t.dataset.adim){const[k,d]=t.dataset.adim.split(':');a[k]=Math.max(1,Math.min(k==='gunluk'?50:20,a[k]+ +d));ciz();baglaGv()}
    else{const qs=new URLSearchParams({bot:t.id==='b_sifirla'?'sifirla':'ayar',butce:Math.round(a.butce),gunluk:a.gunluk,acik:a.acik,risk:a.risk,guven:a.guven,dilim:a.dilim,kalite:a.kalite});
      if(t.id==='b_sifirla'&&!confirm('Bot tüm geçmişiyle sıfırlanacak. Emin misin?'))return;sheetKapat();ustGit('?'+qs.toString())}};
  const baglaGv=()=>{const g=$('#b_guven');g.oninput=e=>$('#b_gv').textContent=e.target.value};baglaGv()}
function sheetAc(){$('#form').classList.add('ac');$('#perde').classList.add('ac')}
function sheetKapat(){$('#form').classList.remove('ac');$('#perde').classList.remove('ac')}
$('#perde').onclick=sheetKapat;

/* PORTFÖY (elle girilen) */
let poz=D.get('poz',[]),pt=D.get('pt','gercek');if(pt==='bot')pt='gercek';
function degerlendir(p){const h=H[p.s],o=h&&h[p.mod];const r={durum:'açık',fiyat:o?o.p:p.giris,realize:0,kalanLot:p.lot,h1:false};
  if(p.kap){r.durum='kapandı';r.fiyat=p.kap.fiyat;r.kalanLot=0;r.realize=(p.kap.fiyat-p.giris)*p.lot+(p.kap.realize||0);return r}
  if(!o)return r;let stop=p.stop,h1=false,realize=0,lot=p.lot;
  for(const m of o.m){if(m[0]<=p.t)continue;
    if(m[3]<=stop){realize+=(stop-p.giris)*lot;lot=0;r.durum=h1?'H1 + başabaş':'stop';r.fiyat=stop;break}
    if(!h1&&m[2]>=p.h[0]){h1=true;const y=Math.floor(lot/2);realize+=(p.h[0]-p.giris)*y;lot-=y;stop=p.giris}
    if(h1&&m[2]>=p.h[1]){realize+=(p.h[1]-p.giris)*lot;lot=0;r.durum='H2';r.fiyat=p.h[1];break}}
  r.h1=h1;r.realize=realize;r.kalanLot=lot;return r}
const kz=(p,d)=>d.realize+(d.kalanLot?(d.fiyat-p.giris)*d.kalanLot:0);
function ekranPortfoy(){const b=(k,a)=>`<button data-pt="${k}" class="${pt===k?'on':''}">${a}</button>`;
  let x=`<div class="seg">${b('gercek','Gerçek işlemlerim')}${b('kagit','Kağıt üstü')}</div>`;
  const l=poz.filter(p=>p.tip===pt).map(p=>({p,d:degerlendir(p)})),acik=l.filter(x=>x.d.durum==='açık'),kapali=l.filter(x=>x.d.durum!=='açık');
  const top=l.reduce((a,x)=>a+kz(x.p,x.d),0),kaz=kapali.filter(x=>kz(x.p,x.d)>0).length;
  x+=`<div class="istat"><div><span class="lbl">Toplam K/Z</span><b class="${yon(top)}">${tlk(top)}</b></div><div><span class="lbl">Açık</span><b>${acik.length}</b></div><div><span class="lbl">Kazanma</span><b>${kapali.length?'%'+tl(kaz/kapali.length*100,0):'—'}</b></div></div>`;
  if(!l.length)return x+`<div class="bos" style="margin-top:12px"><b>Kayıt yok</b>Bir planın detayında “${pt==='gercek'?'İşleme girdim':'Kağıt üstünde al'}” ile ekle. Stop ve hedefler senin yerine takip edilir; kayıtlar bu cihazda saklanır. Otomatik işlem yapan bot için alttaki <b style="display:inline">Bot</b> sekmesine geç.</div>`;
  const kart=({p,d})=>{const k=kz(p,d),yu=k/(p.giris*p.lot)*100;return `<div class="kart pozkart"><div class="fbas">${av(p.s)}<div class="ad"><b>${p.s} <span class="dl">${GOSTER[p.mod]}</span> <span class="rozet ${p.tip==='kagit'?'':'ac'}" style="padding:2px 8px;font-size:10.5px">${p.tip==='kagit'?'Kağıt':'Gerçek'}</span></b><small>${d.durum==='açık'?(d.h1?'H1 alındı':'Açık'):d.durum}</small></div>
    <div class="sag"><b class="${yon(k)}">${tlk(k)}</b><small class="${yon(yu)}">${yz(yu)}</small></div></div>
    <div class="ig"><div><small>Giriş</small><b>${tl(p.giris)}</b></div><div><small>Lot</small><b>${tl(p.lot,0)}</b></div><div><small>${d.durum==='açık'?'Şimdi':'Çıkış'}</small><b>${tl(d.fiyat)}</b></div>
    <div><small>Stop</small><b class="dn">${tl(d.h1?p.giris:p.stop)}</b></div><div><small>H1</small><b class="up">${tl(p.h[0])}</b></div><div><small>H2</small><b class="up">${tl(p.h[1])}</b></div></div>
    <div class="dugmeler">${d.durum==='açık'?`<button class="btn" data-kapat="${p.id}">Kapat</button>`:''}<button class="btn kir" data-sil="${p.id}">Sil</button><button class="btn" data-h="${p.s}" data-m="${p.mod}">Grafik</button></div></div>`};
  return x+(acik.length?`<div class="bolum"><h3>Açık pozisyonlar</h3></div>${acik.map(kart).join('')}`:'')+(kapali.length?`<div class="bolum"><h3>Kapananlar</h3></div>${kapali.map(kart).join('')}`:'')}

/* AYARLAR */
function ekranProfil(){const K=V.karne[M]||[];const l=liste_.filter(h=>fav.has(h.s));
  return `<div class="bolum" style="margin-top:8px"><h3>Ayarlar</h3></div><div class="form-ayar">
   <label><span class="lbl">Sermaye (₺)</span><input id="a_sermaye" inputmode="numeric" value="${ayar.sermaye}"></label>
   <label><span class="lbl">İşlem başı risk %</span><input id="a_risk" inputmode="decimal" value="${ayar.risk}"></label>
   <label class="genis"><span class="lbl">Minimum güven: <b id="gv" class="act">${ayar.guven}</b></span><input type="range" id="a_guven" min="45" max="90" step="5" value="${ayar.guven}"></label>
   <label><span class="lbl">Min. günlük işlem</span><select id="a_lik">${[20,30,100,300].map(v=>`<option value="${v}"${ayar.lik==v?' selected':''}>${v} mn ₺</option>`).join('')}</select></label>
   <label><span class="lbl">Tema</span><select id="a_tema"><option value="koyu"${ayar.tema==='koyu'?' selected':''}>Koyu</option><option value="acik"${ayar.tema==='acik'?' selected':''}>Açık</option></select></label></div>
  <div class="bolum"><h3>Favoriler</h3><span class="lbl">${l.length}</span></div>`+(l.length?`<div class="kart liste">${l.map(h=>satirH(h,'Bot: '+gorus(h,M).tur)).join('')}</div>`:`<div class="bos">Hisse detayında ☆ ile ekle</div>`)+
  `<div class="bolum"><h3>Kurulum karnesi · ${GOSTER[M]}</h3></div><p class="acik-not">Sinyal türlerinin geçmiş testte tutma oranı. En az 15 örneği olan türlerde güven puanı otomatik ayarlanır.</p>`+
  (K.length?`<div class="kart"><table class="tbl"><tr><th>Kurulum</th><th>Adet</th><th>İsabet</th><th>Ayar</th></tr>${K.map(k=>`<tr><td>${esc(k.ad)}</td><td>${k.n}</td><td class="${(k.isabet||0)>=45?'up':'dn'}">${k.isabet==null?'—':'%'+k.isabet}</td><td class="${k.bonus>0?'up':k.bonus<0?'dn':'mu'}">${k.bonus>0?'+':''}${k.bonus}</td></tr>`).join('')}</table></div>`:`<div class="bos">Karne hazırlanıyor</div>`)+
  `<div class="bolum"><h3>Zaman dilimleri ve vade</h3></div><div class="kart"><table class="tbl"><tr><th>Grafik</th><th>Vade</th><th>Süre</th></tr>${MODLAR.map(m=>`<tr><td>${GOSTER[m]}</td><td>${V.vade[m].ad}</td><td>${V.vade[m].sure}</td></tr>`).join('')}</table></div>
  <p class="not">1 ve 5 dk analizleri en likit ${V.hisseler.filter(h=>h.hizli).length} hissede yapılır. Veriler Yahoo Finance'tan ~15 dk gecikmeli gelir. Son tarama ${V.guncelleme}${V.derin?', son derin test '+V.derin:''}. Yatırım tavsiyesi değildir.</p>`}

/* çizim */
let ekran=D.get('ekran','panel');if(ekran==='bot'&&!B)ekran='panel';
function ciz(yeniEkran){hazirla();ustCiz();navCiz();
  const el=$('#ekran');el.classList.toggle('anim',!!yeniEkran&&ANIM);
  el.innerHTML=({panel:ekranPanel,akis:ekranAkis,plan:ekranPlan,piyasa:ekranPiyasa,bot:ekranBot,portfoy:ekranPortfoy,profil:ekranProfil}[ekran]||ekranPanel)()+`<div class="uyari">VERİ ~15 DK GECİKMELİ · YATIRIM TAVSİYESİ DEĞİLDİR</div>`;
  if(yeniEkran)el.scrollTop=0;
  if(yeniEkran)sayAnim(el);
  if(ekran==='bot')setTimeout(botGrafikKur,30);else if(botChart){botChart.remove();botChart=null}
  const qi=$('#q');if(qi)qi.oninput=e=>{q=e.target.value.toUpperCase().trim();$('#pliste').innerHTML=piyasaIcerik()};
  const si=$('#ms');if(si)si.onchange=e=>{ms=e.target.value;D.set('ms',ms);$('#pliste').innerHTML=piyasaIcerik()};
  ['sermaye','risk'].forEach(k=>{const i=$('#a_'+k);if(i)i.onchange=e=>{const v=parseFloat(String(e.target.value).replace(/\./g,'').replace(',','.'));if(v>0){ayar[k]=v;D.set('ayar',ayar);toast('Kaydedildi')}}});
  const g=$('#a_guven');if(g){g.oninput=e=>$('#gv').textContent=e.target.value;g.onchange=e=>{ayar.guven=+e.target.value;D.set('ayar',ayar);ciz()}}
  const lk=$('#a_lik');if(lk)lk.onchange=e=>{ayar.lik=+e.target.value;D.set('ayar',ayar);ciz()};
  const tm=$('#a_tema');if(tm)tm.onchange=e=>{ayar.tema=e.target.value;D.set('ayar',ayar);temaUygula();ciz()}}
function git(e){ekran=e;D.set('ekran',ekran);ciz(true)}
const ACILIS=Date.now();if(V.seans)setTimeout(()=>{if(!document.hidden&&!$('#form').classList.contains('ac'))yenile()},4*60*1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-ACILIS>4*60*1000)yenile()});
$('#nav').onclick=e=>{const b=e.target.closest('button');if(b)git(b.dataset.e)};
$('#ust').onclick=e=>{const t=e.target.closest('[data-mod],[data-git]');if(!t)return;const d=t.dataset;
  if(d.mod){M=d.mod;D.set('mod',M);ciz()}else if(d.git)git(d.git)};
$('#ekran').onclick=e=>{const t=e.target.closest('[data-pf],[data-pg],[data-mf],[data-pt],[data-af],[data-adl],[data-bt],[data-bot],[data-botayar],[data-botkapat],[data-bothepsi],[data-git],[data-sek],[data-sektemizle],[data-kapat],[data-sil],[data-h]');if(!t)return;const d=t.dataset;
  if(d.pf){pf=d.pf;D.set('pf',pf);ciz()}else if(d.pg){pg=d.pg;D.set('pg',pg);ciz()}else if(d.mf){mf=d.mf;D.set('mf',mf);ciz()}else if(d.pt){pt=d.pt;D.set('pt',pt);ciz()}
  else if(d.af){af=d.af;D.set('af',af);ciz()}else if(d.adl){adl=d.adl;D.set('adl',adl);ciz()}
  else if(d.bt){bt=d.bt;D.set('bt',bt);ciz();sayAnim($('#ekran'))}
  else if(d.bot)ustGit('?bot='+d.bot)
  else if(d.botayar)botAyarAc()
  else if(d.botkapat){if(confirm('Bu pozisyon anlık fiyattan kapatılsın mı?'))ustGit('?bot=kapat&id='+encodeURIComponent(d.botkapat))}
  else if(d.bothepsi){if(confirm('Botun tüm açık pozisyonları kapatılsın mı?'))ustGit('?bot=hepsi')}
  else if(d.git){if(d.git==='sektor'){ekran='piyasa';pg='sektor';D.set('ekran',ekran);ciz(true)}else git(d.git)}
  else if(d.sek){sekSec=d.sek;ekran='piyasa';pg='liste';ciz(true)}else if(d.sektemizle){sekSec=null;ciz()}
  else if(d.kapat){const p=poz.find(x=>x.id==d.kapat),o=p&&H[p.s]&&H[p.s][p.mod];if(p&&o){const dv=degerlendir(p);p.kap={fiyat:o.p,realize:dv.realize-(o.p-p.giris)*(p.lot-dv.kalanLot)};D.set('poz',poz);toast('Pozisyon kapatıldı');ciz()}}
  else if(d.sil){poz=poz.filter(x=>x.id!=d.sil);D.set('poz',poz);ciz()}
  else detayAc(d.h,d.m)};

/* hisse detayı */
let chart=null,ro=null,secili=null,DM='g',sekme=D.get('sekme','analiz');
const gor=Object.assign({plan:true,vwap:true,ema:true,prof:true,sev:false,form:true},D.get('gor',{}));
function ema(d,n){const k=2/(n+1);let e=d[0];return d.map(v=>e=v*k+e*(1-k))}
function vwapHesap(m){let gun=-1,pv=0,vv=0;return m.map(x=>{const g=Math.floor(x[0]/86400);if(g!==gun){gun=g;pv=0;vv=0}pv+=(x[2]+x[3]+x[4])/3*x[5];vv+=x[5];return vv?pv/vv:x[4]})}
function delta(m){return m.map(x=>{const r=x[2]-x[3];return r>0?x[5]*((x[4]-x[3])-(x[2]-x[4]))/r:0})}
function detayAc(s,m){const h=H[s];if(!h)return;m=m&&h[m]?m:(h[M]?M:MODLAR.find(k=>h[k]));if(!m)return;secili=s;DM=m;D.set('detay',[s,m]);hazirla();detayCiz();
  $('#detay').classList.add('ac');$('#dicerik').scrollTop=0}
function detayCiz(){const h=H[secili],o=h[DM];
  $('#tv').href='https://tr.tradingview.com/chart/?symbol=BIST%3A'+encodeURIComponent(secili);yildizCiz();
  $('#dad').innerHTML=`${av(secili,40)}<div style="min-width:0"><b>${secili}</b><small>${esc(h.sek)} · ${tl(h.lik,0)} mn ₺/gün</small></div>`;
  $('#dfiyat').innerHTML=`<b class="n">${tl(o.p)}</b><span class="rozet ${yon(o.d)}">${o.d>=0?'▲':'▼'} ${yz(o.d)}</span><span class="mu" style="margin-left:auto;font-size:12px;font-weight:700">${GOSTER[DM]}</span>`;
  const vwF=o.vw?(o.p/o.vw-1)*100:null;
  $('#distat').innerHTML=`<div><span class="lbl">Hacim</span><b>${tl(o.rv,1)}x</b></div><div><span class="lbl">Alıcı</span><b class="${yon(o.ab||0)}">%${tl((1+(o.ab||0))*50,0)}</b></div>
    <div><span class="lbl">${DM==='w'?'RS 20G':'VWAP'}</span><b class="${yon(DM==='w'?(o.rs||0):(vwF||0))}">${DM==='w'?yz(o.rs,1):(vwF==null?'—':yz(vwF,1))}</b></div><div><span class="lbl">RSI</span><b>${tl(o.rsi,0)}</b></div>`;
  const g=gorus(h,DM);$('#dkarar').innerHTML=`<div class="karar ${g.tur}"><b class="${g.tur==='AL'?'up':g.tur==='SAT'?'dn':'mu'}">${g.tur}</b>${esc(g.metin)}</div>`;
  $('#dtf').innerHTML=MODLAR.map(m=>`<button class="chip${m===DM?' on':''}" data-dm="${m}" ${h[m]?'':'disabled'}>${GOSTER[m]}${h[m]&&h[m].akt?` <span style="color:${m===DM?'#fff':h[m].akt.yon>0?'var(--up)':'var(--dn)'}">●</span>`:''}</button>`).join('');
  $('#dplan').innerHTML=o.akt?`<div class="bolum"><h3>İşlem fişi</h3></div>${fis(h,DM,true)}`
   :`<div class="bolum"><h3>Tetik seviyeleri</h3><span class="lbl">${GOSTER[DM]}</span></div><div class="kart" style="padding-bottom:12px"><div class="ig"><div><small>AL tetiği</small><b class="up">${tl(o.tetik.ust)}</b><em class="mu">üstünde kapanış</em></div>
     <div><small>Çıkış tetiği</small><b class="dn">${tl(o.tetik.alt)}</b><em class="mu">altında kapanış</em></div><div><small>Vade</small><b style="font-size:12.5px">${V.vade[DM].ad}</b><em class="mu">${V.vade[DM].sure}</em></div></div></div>`;
  setTimeout(()=>grafikKur(h,DM),60);sekmeCiz()}
$('#dtf').onclick=e=>{const b=e.target.closest('[data-dm]');if(!b||b.disabled)return;DM=b.dataset.dm;D.set('detay',[secili,DM]);detayCiz()};
function kapat(){$('#detay').classList.remove('ac');sheetKapat();D.set('detay',null);setTimeout(()=>{if(chart){chart.remove();chart=null}},400)}
$('#geri').onclick=kapat;
function yildizCiz(){const b=$('#dyildiz'),on=fav.has(secili);b.textContent=on?'★':'☆';b.style.color=on?'var(--wa)':''}
$('#dyildiz').onclick=()=>{fav.has(secili)?fav.delete(secili):fav.add(secili);D.set('fav',[...fav]);yildizCiz();toast(fav.has(secili)?'Favorilere eklendi':'Favorilerden çıkarıldı')};
$('#dplan').onclick=e=>{const b=e.target.closest('[data-gir]');if(b)formAc(b.dataset.gir)};
function formAc(tip){const h=H[secili],o=h[DM],s=o.akt,L=lotHesap(s)||{lot:0};$('#form').onclick=null;
  $('#form').innerHTML=`<div class="tutamak"></div><h2>${tip==='gercek'?'İşleme girdim':'Kağıt üstünde al'}</h2><p class="acik-not">${secili} · ${GOSTER[DM]} · ${s.vade}</p>
   <div class="form-ayar"><label><span class="lbl">Alış fiyatı</span><input id="f_fiyat" inputmode="decimal" value="${tl(Math.min(o.p,s.giris_ust))}"></label><label><span class="lbl">Lot</span><input id="f_lot" inputmode="numeric" value="${L.lot||1}"></label></div>
   <p class="not">Stop ${tl(s.stop)} · H1 ${tl(s.hedef)} · H2 ${tl(s.hedef2)}. Pozisyon bu plana göre takip edilir.</p>
   <div class="dugmeler" style="padding:14px 0 0"><button class="btn" id="f_iptal">Vazgeç</button><button class="btn ana" id="f_kaydet">Kaydet</button></div>`;
  sheetAc();$('#f_iptal').onclick=sheetKapat;
  $('#f_kaydet').onclick=()=>{const num=v=>parseFloat(String(v).replace(/\./g,'').replace(',','.'));const f=num($('#f_fiyat').value),l=Math.floor(num($('#f_lot').value));
    if(!(f>0&&l>0)){toast('Fiyat ve lot gir');return}
    poz.unshift({id:Date.now(),s:secili,mod:DM,tip,yon:s.yon,giris:f,lot:l,stop:s.stop,h:[s.hedef,s.hedef2,s.hedef3],t:o.m[o.m.length-1][0],kap:null});
    D.set('poz',poz);sheetKapat();toast('Portföye eklendi')}}

function grafikKur(h,m){if(chart){chart.remove();chart=null}const el=$('#grafik'),o=h[m];
  if(!window.LightweightCharts){el.innerHTML='<div class="bos" style="margin:0 16px">Grafik yüklenemedi. Sayfayı yenile.</div>';return}
  const css=getComputedStyle(document.documentElement),cv=k=>css.getPropertyValue(k).trim(),UP='#2fe0a0',DN='#ff5c7c';
  chart=LightweightCharts.createChart(el,{width:el.clientWidth,height:310,layout:{background:{type:'solid',color:'transparent'},textColor:cv('--mu'),fontFamily:'Manrope',fontSize:10},
    grid:{vertLines:{color:cv('--ln2')},horzLines:{color:cv('--ln2')}},rightPriceScale:{borderColor:cv('--ln'),scaleMargins:{top:.06,bottom:.2}},
    timeScale:{borderColor:cv('--ln'),timeVisible:m!=='w',secondsVisible:false,rightOffset:5,barSpacing:m==='1'?5:7},
    crosshair:{mode:0,vertLine:{color:cv('--mu2'),labelBackgroundColor:'#7c6cff'},horzLine:{color:cv('--mu2'),labelBackgroundColor:'#7c6cff'}},localization:{locale:'tr-TR',priceFormatter:p=>tl(p)}});
  const md=o.m,n=md.length,zam=md.map(x=>x[0]);
  const mum=chart.addCandlestickSeries({upColor:UP,downColor:DN,borderVisible:false,wickUpColor:UP,wickDownColor:DN,priceLineColor:'#7c6cff',priceLineStyle:2});
  mum.setData(md.map(x=>({time:x[0],open:x[1],high:x[2],low:x[3],close:x[4]})));
  const hac=chart.addHistogramSeries({priceScaleId:'h',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false});chart.priceScale('h').applyOptions({scaleMargins:{top:.84,bottom:0}});
  const dl=delta(md);hac.setData(md.map((x,i)=>({time:x[0],value:x[5],color:dl[i]>=0?'rgba(47,224,160,.35)':'rgba(255,92,124,.35)'})));
  const cz=(r,w=1,st=0)=>chart.addLineSeries({color:r,lineWidth:w,lineStyle:st,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
  const kp=md.map(x=>x[4]);const e20=cz('#22d3ee'),e50=cz('#a99bff');e20.setData(ema(kp,20).map((v,i)=>({time:zam[i],value:v})));e50.setData(ema(kp,50).map((v,i)=>({time:zam[i],value:v})));
  const vw=cz('#ffb547',1.5,2);if(m!=='w')vw.setData(vwapHesap(md).map((v,i)=>({time:zam[i],value:v})));
  const fs=[];o.form.forEach(f=>f.cizgiler.forEach(c=>{const s=cz(f.yon<0?'#ff8aa0':'#a99bff',2);s.setData([{time:c[0],value:c[1]},{time:c[2],value:c[3]}]);fs.push(s)}));
  let cl=[];const lo=Math.min(...md.map(x=>x[3]))*.97,hi=Math.max(...md.map(x=>x[2]))*1.03;
  function uyg(){[e20,e50].forEach(s=>s.applyOptions({visible:gor.ema}));vw.applyOptions({visible:gor.vwap&&m!=='w'});fs.forEach(s=>s.applyOptions({visible:gor.form}));
    cl.forEach(p=>mum.removePriceLine(p));cl=[];const ek=x=>cl.push(mum.createPriceLine(Object.assign({lineWidth:1,axisLabelVisible:false},x)));
    if(gor.sev)o.sev.filter(s=>s[0]>lo&&s[0]<hi).forEach(s=>ek({price:s[0],color:(s[1]==='D'?'rgba(47,224,160,':'rgba(255,92,124,')+(0.3+0.45*(s[2]||0)).toFixed(2)+')',lineStyle:2}));
    if(gor.prof&&o.prof){ek({price:o.prof.poc,color:'#ffb547',lineStyle:0,title:'POC',axisLabelVisible:true});ek({price:o.prof.vah,color:'rgba(139,147,167,.5)',lineStyle:1,title:'VAH'});ek({price:o.prof.val,color:'rgba(139,147,167,.5)',lineStyle:1,title:'VAL'})}
    const s=o.akt;if(gor.plan&&s){ek({price:s.stop,color:DN,lineStyle:0,title:'SL',axisLabelVisible:true});ek({price:s.giris_ust,color:'#7c6cff',lineStyle:2,title:'GİRİŞ'});ek({price:s.giris_alt,color:'#7c6cff',lineStyle:2});
      [s.hedef,s.hedef2,s.hedef3].forEach((p,i)=>ek({price:p,color:`rgba(47,224,160,${1-i*.25})`,lineStyle:0,title:'H'+(i+1),axisLabelVisible:i===0}))}
    const bp=(B.poz||[]).find(p=>p.s===secili&&p.mod===m);if(bp){ek({price:bp.giris,color:'#22d3ee',lineStyle:0,lineWidth:2,title:'BOT',axisLabelVisible:true})}
    mum.setMarkers(gor.plan?o.sinF.filter(s=>s.t>=zam[0]&&s.t<=zam[n-1]).map(s=>({time:s.t,position:s.yon>0?'belowBar':'aboveBar',color:s.yon>0?UP:DN,shape:s.yon>0?'arrowUp':'arrowDown',text:s.tur})):[])}
  uyg();
  const ar=m==='w'?{'1A':22,'3A':66,'Tümü':n}:m==='1'?{'30dk':30,'1S':60,'3S':180,'Tümü':n}:m==='5'?{'2S':24,'1G':o.gun_bar,'Tümü':n}:{'1G':o.gun_bar,'2G':o.gun_bar*2,'Tümü':n};
  let sec=D.get('ar_'+m,Object.keys(ar)[1]);if(!ar[sec])sec=Object.keys(ar)[1];
  const arU=()=>{const k=Math.min(ar[sec],n);chart.timeScale().setVisibleLogicalRange({from:n-k-.5,to:n+4})};arU();
  const gs=$('#gsec'),t=(k,a,on)=>`<button class="chip${on?' on':''}" data-k="${k}">${a}</button>`;
  const gsc=()=>{gs.innerHTML=Object.keys(ar).map(k=>t('a:'+k,k,sec===k)).join('')+'<span class="ayr"></span>'+t('g:plan','Plan',gor.plan)+(m!=='w'?t('g:vwap','VWAP',gor.vwap):'')+t('g:ema','EMA',gor.ema)+t('g:prof','Profil',gor.prof)+t('g:form','Formasyon',gor.form)+t('g:sev','S/R',gor.sev)};gsc();
  gs.onclick=e=>{const b=e.target.closest('[data-k]');if(!b)return;const[tp,k]=b.dataset.k.split(':');if(tp==='a'){sec=k;D.set('ar_'+m,k);arU()}else{gor[k]=!gor[k];D.set('gor',gor);uyg()}gsc()};
  const ix=Object.fromEntries(md.map((x,i)=>[x[0],i]));
  const lg=i=>{const x=md[i];if(!x)return'';const d=dl[i];return `A <b>${tl(x[1])}</b> Y <b>${tl(x[2])}</b> D <b>${tl(x[3])}</b> K <b class="${x[4]>=x[1]?'up':'dn'}">${tl(x[4])}</b> · Hac <b>${tl(x[5],0)}</b> · <span class="${d>=0?'up':'dn'}">alıcı %${tl((1+d/(x[5]||1))*50,0)}</span>`};
  $('#legend').innerHTML=lg(n-1);chart.subscribeCrosshairMove(p=>{$('#legend').innerHTML=lg(p&&p.time!=null&&ix[p.time]!=null?ix[p.time]:n-1)});
  if(ro)ro.disconnect();ro=new ResizeObserver(()=>chart&&chart.applyOptions({width:el.clientWidth}));ro.observe(el)}

function sekmeCiz(){document.querySelectorAll('#sekmeler button').forEach(b=>b.classList.toggle('on',b.dataset.s===sekme));const o=H[secili][DM],m=DM;let x='';
  if(sekme==='analiz'){const s=o.akt;
    if(s)x+=`<div class="kart" style="margin-bottom:12px"><div class="lbl" style="padding:14px 16px 0">Sinyalin gerekçeleri</div><div class="neden2">${s.arti.map(a=>`<div class="p">${esc(a)}</div>`).join('')}${s.eksi.map(a=>`<div class="x">${esc(a)}</div>`).join('')}</div></div>`;
    x+=`<div class="kart"><div class="satir" style="padding:14px 16px 0">${BOTIK.replace('botik','botik" style="width:30px;height:30px;border-radius:10px')}<b style="font-weight:800">Bot ne görüyor</b></div><div class="yorum">${o.yorum.map(c=>`<div>${esc(c)}</div>`).join('')}</div></div>`}
  else if(sekme==='hacim'){const ab=o.ab||0;const dl=delta(o.m);let c=0;const cvd=dl.map(v=>c+=v).slice(-120);
    x+=`<div class="istat"><div><span class="lbl">Alıcı/satıcı</span><b class="${yon(ab)}">${ab>=0?'+':'−'}${tl(Math.abs(ab)*100,0)}%</b></div><div><span class="lbl">Göreli hacim</span><b>${tl(o.rv,1)}x</b></div><div><span class="lbl">Birikim</span><b>${(o.birikim||0)>0?'Var':'—'}</b></div></div>
      <div class="bolum"><h3>Kümülatif hacim akışı</h3><span class="lbl">son ${cvd.length} ${birim(m)}</span></div><div class="kart" style="padding:12px 0 0">${alan(cvd,{h:90})}
      <p class="not" style="padding:0 16px 14px">Yükselen çizgi alıcı hacminin biriktiğini gösterir; fiyat düşerken yükseliyorsa gizli alım olabilir.</p></div>`;
    if(o.prof){const b=[...o.prof.bins].reverse(),mx=Math.max(...b.map(x=>x[1]));const si=b.reduce((e,x,i)=>Math.abs(x[0]-o.p)<Math.abs(b[e][0]-o.p)?i:e,0),pi=b.reduce((e,x,i)=>x[1]>b[e][1]?i:e,0);
      x+=`<div class="bolum"><h3>Hacim profili</h3><span class="lbl">POC ${tl(o.prof.poc)}</span></div><div class="kart pad profil">${b.map((r,i)=>`<div class="${i===pi?'poc':(r[0]>=o.prof.val&&r[0]<=o.prof.vah?'va':'')}${i===si?' simdi':''}"><span>${tl(r[0])}</span><i style="width:${(r[1]/mx*70).toFixed(1)}%;animation-delay:${i*12}ms"></i></div>`).join('')}</div>`}}
  else if(sekme==='teknik'){const tr={1:'Yukarı',0:'Yatay','-1':'Aşağı'},yp={1:'Yükselen',0:'Kararsız','-1':'Alçalan'};
    x+=`<div class="kart"><table class="tbl"><tr><th>Gösterge</th><th>Değer</th><th>Yorum</th></tr>
      ${m!=='w'?`<tr><td>Günlük trend</td><td class="${o.htf>0?'up':o.htf<0?'dn':''}">${tr[o.htf]}</td><td class="mu">EMA20/50</td></tr>`:''}
      <tr><td>Yapı (${GOSTER[m]})</td><td class="${o.yapi>0?'up':o.yapi<0?'dn':''}">${yp[o.yapi]}</td><td class="mu">tepe-dip</td></tr>
      <tr><td>RSI 14</td><td>${tl(o.rsi,0)}</td><td class="mu">${o.rsi>70?'aşırı alım':o.rsi<30?'aşırı satım':'nötr'}</td></tr>
      <tr><td>MACD</td><td class="${yon(o.macd||0)}">${(o.macd||0)>=0?'Pozitif':'Negatif'}</td><td class="mu">momentum</td></tr>
      <tr><td>Endekse göre</td><td class="${yon(o.rs||0)}">${yz(o.rs,1)}</td><td class="mu">göreli güç</td></tr>
      <tr><td>ATR</td><td>%${tl(o.atr)}</td><td class="mu">mum oynaklığı</td></tr></table></div>`;
    x+=`<div class="bolum"><h3>Formasyonlar</h3></div>`+(o.form.length?`<div class="kart"><table class="tbl"><tr><th>Formasyon</th><th>Kritik</th><th>Durum</th></tr>${o.form.map(f=>`<tr><td>${esc(f.ad)}</td><td>${tl(f.ref)}</td><td class="${f.durum==='kırıldı'?(f.yon>0?'up':'dn'):'mu'}">${f.durum}</td></tr>`).join('')}</table></div>`:`<div class="bos">Formasyon yok</div>`);
    const sv=[...o.sev].sort((a,b)=>Math.abs(a[0]-o.p)-Math.abs(b[0]-o.p)).slice(0,8).sort((a,b)=>b[0]-a[0]);
    x+=`<div class="bolum"><h3>Destek / direnç</h3></div><div class="kart"><table class="tbl"><tr><th>Seviye</th><th>Tür</th><th>Uzaklık</th><th>Hacim</th></tr>${sv.map(s=>`<tr><td>${tl(s[0])}</td><td class="${s[1]==='D'?'up':'dn'}">${s[1]==='D'?'Destek':'Direnç'}</td><td>${yz((s[0]/o.p-1)*100,1)}</td><td><span style="display:inline-block;height:6px;border-radius:9px;background:var(--grad);width:${Math.max(8,Math.round((s[2]||0)*50))}px"></span></td></tr>`).join('')}</table></div>`}
  else{const l=[...o.sinF].reverse(),bit=l.filter(s=>s.sonuc!=='açık'),hd=bit.filter(s=>s.sonuc==='hedef').length,st=bit.filter(s=>s.sonuc==='stop').length;
    x+=`<div class="istat"><div><span class="lbl">Sinyal</span><b>${l.length}</b></div><div><span class="lbl">Hedef / stop</span><b><span class="up">${hd}</span> / <span class="dn">${st}</span></b></div><div><span class="lbl">İsabet</span><b>${hd+st?'%'+tl(hd/(hd+st)*100,0):'—'}</b></div></div>`;
    x+=l.length?`<div class="kart" style="margin-top:12px"><table class="tbl"><tr><th>Zaman</th><th>Yön</th><th>Gv</th><th>Sonuç</th></tr>${l.slice(0,20).map(s=>`<tr><td>${s.saat}</td><td><span class="yon ${s.yon>0?'al':'sat'}">${s.tur}</span></td><td>${s.guven}</td>
      <td class="${s.sonuc==='hedef'?'up':s.sonuc==='stop'?'dn':'mu'}">${esc(s.sonuc)} ${yz(s.getiri,1)}</td></tr>`).join('')}</table></div>`:`<div class="bos" style="margin-top:12px">Sinyal yok</div>`;
    x+=`<p class="not">Her sinyalden sonra ${V.ufuk} ${birim(m)} içinde önce H1'e mi stopa mı gidildiğine bakıldı. Hedefler riskin en az 1,5 katı olduğu için ~%40 üstü isabet kârlı sayılır.</p>`}
  $('#sekme').innerHTML=x}
$('#sekmeler').onclick=e=>{const b=e.target.closest('button');if(!b)return;sekme=b.dataset.s;D.set('sekme',sekme);sekmeCiz()};

if(MESAJ){ekran='bot';D.set('ekran','bot');setTimeout(()=>toast(MESAJ),400)}
ciz(true);window.addEventListener('resize',()=>{navCiz();indX=null;ustCiz()});
const ds=D.get('detay',null);if(!MESAJ&&Array.isArray(ds)&&H[ds[0]])detayAc(ds[0],ds[1]);
</script></body></html>
"""


# ---------- Siteye gidecek veri ----------
ESIK = 40   # bu güvenin altındaki sinyaller hiç gönderilmez; kullanıcı eşiği uygulamada ayrıca uygulanır


def _ts(t, mod) -> int:
    """Gün içi grafikte İstanbul saati görünsün diye UTC damgasına +3 saat eklenir."""
    return int(pd.Timestamp(t).timestamp()) + (3 * 3600 if mod != "w" else 0)


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
        t=_ts(zaman, mod), saat=f"{zaman:%d.%m %H:%M}" if mod != "w" else f"{zaman:%d.%m.%Y}", once=n - 1 - s["i"],
        tur=s["tur"], yon=s["yon"], guven=s["guven"], guclu=s["guclu"], kurulum=s.get("kurulum", ""),
        sebepler=s["sebepler"], arti=s["arti"], eksi=s["eksi"],
        fiyat=_r(s["fiyat"], 4), stop=_r(s["stop"], 4), hedef=_r(s["hedef"], 4), hedef2=_r(s["hedef2"], 4),
        hedef3=_r(s["hedef3"], 4), giris_alt=_r(ga, 4), giris_ust=_r(gu, 4), rk=_r(s["rk"], 1),
        sonuc=s["sonuc"], getiri=_r(s["getiri"] * 100, 2), ilerleme=_r(min(max(ilerleme, 0), 1), 3), durum=durum,
        risk=_r(abs(s["fiyat"] - s["stop"]) / s["fiyat"] * 100, 2),
        pot=[yuzde(s["hedef"]), yuzde(s["hedef2"]), yuzde(s["hedef3"])],
        en_iyi=yuzde(en_iyi), kalan=max(TEST_UFKU - (n - 1 - s["i"]), 0),
        vade=VADE[mod]["ad"], vade_sure=VADE[mod]["sure"],
        kalite=("A+" if s["guven"] >= 80 and s["guclu"] and s["rk"] >= 2 else
                "A" if s["guven"] >= 70 and s["rk"] >= 1.5 else "B" if s["guven"] >= 60 else "C"),
    )


def kompakt(x: dict) -> list:
    """Geçmiş sinyaller için sıkıştırılmış satır: [zaman, yön, güven, güçlü, fiyat, sonuç, getiri%]"""
    return [x["t"], x["yon"], x["guven"], int(x["guclu"]), x["fiyat"], x["sonuc"], x["getiri"]]


def mod_json(a: dict, eski_sin: list | None) -> dict:
    """Bir hissenin bir moddaki (gün içi / swing) tüm verisi."""
    ctx, mod = a["ctx"], a["mod"]
    df, n = ctx["df"], ctx["n"]
    bas = max(0, len(df) - {"1": 180, "5": 160, "g": GRAFIK_MUM, "w": 90}[mod])
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
    gun_bar = int((df.index.date == df.index[-1].date()).sum()) if mod != "w" else 1
    return dict(
        p=_r(fiyat, 4), d=_r(a["degisim"], 2), m=mumlar, rv=_r(a["rv"], 2), ab=_r(a["ab"], 3), vw=_r(a["vwap"], 4),
        rsi=_r(a["rsi"], 1), macd=_r(a["macd"], 4), atr=_r(a["atr"], 2), yapi=a["yapi"], htf=a["htf"], rs=_r(a["rs"], 2),
        sev=[[_r(x, 4), "D" if x < fiyat else "R", _r(bolge_gucu(prof, x), 2)] for x in a["sev"]],
        form=formlar, yorum=yorum, tetik=tetik, gun_bar=max(gun_bar, {"1": 300, "5": 60, "g": 26}.get(mod, 1)) if mod != "w" else 1,
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


def bot_portfoyu(sinyaller: list[dict], esik: int = 65, gunluk_en_fazla: int = 3) -> dict:
    """Bot her gün en güçlü 3 sinyale, her birinde sermayenin %1'ini riske ederek girseydi (bileşik değil)."""
    adaylar = [s for s in sinyaller if s["guven"] >= esik and s["sonuc"] != "açık"]
    gunler = {}
    for s in adaylar:
        gunler.setdefault(pd.Timestamp(s["zaman"]).date(), []).append(s)
    islemler = []
    for g in sorted(gunler):
        islemler += sorted(gunler[g], key=lambda s: -s["guven"])[:gunluk_en_fazla]
    if not islemler:
        return dict(n=0)
    toplam, tepe, dd, egri, rler = 0.0, 0.0, 0.0, [0.0], []
    for s in islemler:
        risk = abs(s["fiyat"] - s["stop"]) / s["fiyat"]
        R = max(min(s["getiri"] / risk if risk > 0 else 0, 6), -1.5)
        rler.append((R, s))
        toplam += R  # her işlem %1 risk -> R kadar % getiri
        tepe = max(tepe, toplam)
        dd = min(dd, toplam - tepe)
        egri.append(toplam)
    adim = max(1, len(egri) // 60)
    kazanan = sum(1 for R, _ in rler if R > 0)
    sirali = sorted(rler, key=lambda x: -x[0])
    ozet = lambda R, s: dict(s=s["sym"], tur=s["tur"], saat=f"{s['zaman']:%d.%m %H:%M}", R=_r(R, 2))  # noqa: E731
    return dict(n=len(islemler), kazanma=_r(kazanan / len(islemler) * 100, 0), getiri=_r(toplam, 1),
                dd=_r(dd, 1), egri=[_r(x, 2) for x in egri[::adim]] + [_r(egri[-1], 2)],
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


def akis_olaylari(analiz: dict) -> list[dict]:
    """Canlı akış: taze sinyaller + son mumdaki hacim patlaması / sert hareket uyarıları, en yeni üstte."""
    taze = {"1": 30, "5": 12, "g": 8, "w": 2}
    olaylar = []
    for mod, liste in analiz.items():
        for h, a in liste.items():
            ctx = a["ctx"]
            df, n, A = ctx["df"], ctx["n"], ctx["A"]
            for s_ in filtrele(a["sinyaller"], ESIK):
                if n - 1 - s_["i"] <= taze[mod]:
                    j = sinyal_json(s_, df, n, a["fiyat"], mod)
                    if j["kalite"] == "C" or j["durum"] == "bitti":
                        continue
                    olaylar.append(dict(t=j["t"], s=h, mod=mod, tip=j["tur"], guven=j["guven"], kalite=j["kalite"],
                                        guclu=j["guclu"], metin=j["sebepler"][0], fiyat=j["fiyat"],
                                        alt=(f"Giriş {sayi(j['giris_alt'])}–{sayi(j['giris_ust'])} · H1 +%{sayi(j['pot'][0])} · stop −%{sayi(j['risk'])} · {j['vade']}"
                                             if j["yon"] > 0 else f"Elindeyse çık/azalt · beklenen −%{sayi(j['pot'][0])} · {sayi(j['stop'])} üstü bozar")))
            if mod == "w" or n < 25:
                continue
            i = n - 1
            c, atr = A["Close"][i], nanv(A["ATR"][i], A["Close"][i] * 0.01)
            rv = nanv(A["RVOL"][i])
            t = _ts(df.index[i], mod)
            if rv >= 3 and A["Close"][i] > A["Open"][i] * 1.002:
                olaylar.append(dict(t=t, s=h, mod=mod, tip="HACİM", metin=f"Hacim patlaması: normalin {sayi(rv, 1)} katı",
                                    fiyat=_r(c, 4), alt=f"Mum +%{sayi((c / A['Open'][i] - 1) * 100)} · alıcı payı %{(1 + nanv(A['AB'][i])) * 50:.0f}"))
            hareket = c / A["Close"][i - 3] - 1
            if abs(hareket) * c >= 2.5 * atr and abs(hareket) >= {"1": 0.008, "5": 0.012, "g": 0.02}[mod]:
                olaylar.append(dict(t=t, s=h, mod=mod, tip="DÜŞÜŞ" if hareket < 0 else "YÜKSELİŞ",
                                    metin=("Sert düşüş" if hareket < 0 else "Sert yükseliş") + f" %{sayi(abs(hareket) * 100, 1)} (son 3 mum)",
                                    fiyat=_r(c, 4), alt=f"Hacim {sayi(rv, 1)}x · RSI {nanv(A['RSI'][i], 50):.0f}"))
    olaylar.sort(key=lambda x: -x["t"])
    for o in olaylar:
        o["id"] = f"{o['s']}-{o['mod']}-{o['t']}-{o['tip']}"
    return olaylar[:150]


# ---------- Canlı bot: sanal bütçeyle gerçek seansta otomatik işlem (kağıt üstünde) ----------
BOT_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_canli.json")
KAYMA = 0.0005          # her alış ve satışta %0,05 kayma (gerçekçi dolum için)
KALITE_SIRA = {"A+": 0, "A": 1, "B": 2, "C": 3}
BOT_VARSAYILAN = dict(butce=100000.0, gunluk=5, acik=3, risk=1.0, guven=65, dilim="g", kalite="A")


def _ep_dizi(df) -> np.ndarray:
    """Mum zamanlarını saniye cinsinden epoch olarak döndürür."""
    return pd.DatetimeIndex(df.index).as_unit("ns").asi8 // 10 ** 9


class CanliBot:
    def __init__(self):
        self.kilit = threading.RLock()
        self.d = self._yukle()

    # --- kayıt ---
    def _yeni(self, ayar: dict) -> dict:
        t = int(time.time())
        return dict(surum=1, ayar=ayar, aktif=True, baslangic=t, nakit=float(ayar["butce"]), poz=[], islem=[],
                    egri=[[t, float(ayar["butce"])]], gunler={}, gorulen=[], log=[], xu0=None, son_tik=None)

    def _yukle(self) -> dict:
        try:
            with open(BOT_DOSYA, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("surum") == 1:
                d["ayar"] = {**BOT_VARSAYILAN, **d.get("ayar", {})}
                return d
        except Exception:  # noqa: BLE001
            pass
        d = self._yeni(dict(BOT_VARSAYILAN))
        d["log"].append([int(time.time()), "bilgi", f"Bot {sayi(d['ayar']['butce'], 0)} TL sanal bütçeyle hazır", None])
        return d

    def _kaydet(self):
        try:
            gecici = BOT_DOSYA + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(gecici, BOT_DOSYA)
        except Exception:  # noqa: BLE001
            pass

    def _log(self, tip: str, metin: str, s: str | None = None):
        self.d["log"].append([int(time.time()), tip, metin, s])
        self.d["log"] = self.d["log"][-200:]

    def _ozkaynak(self) -> float:
        return self.d["nakit"] + sum(p["kalan"] * p["fiyat"] for p in self.d["poz"])

    @staticmethod
    def _gun(t: int) -> str:
        return dt.datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d")

    # --- işlem mekaniği ---
    def _al(self, h, mod, s, j, an, t) -> bool:
        d, a = self.d, self.d["ayar"]
        fiyat = float(an["fiyat"])
        giris = fiyat * (1 + KAYMA)
        stop = float(s["stop"])
        rb = giris - stop
        if rb <= giris * 0.001:
            return False
        oz = self._ozkaynak()
        lot = int(oz * a["risk"] / 100 / rb)                          # risk bazlı lot
        lot = min(lot, int(min(d["nakit"], oz / a["acik"]) / giris))  # tek hisseye en fazla özkaynak / pozisyon sayısı
        if lot < 1:
            return False
        d["nakit"] -= lot * giris
        ep = _ep_dizi(an["ctx"]["df"])
        d["poz"].append(dict(
            id=f"{h}-{t}", s=h, mod=mod, giris=round(giris, 4), lot=lot, kalan=lot, stop=round(stop, 4), stop0=round(stop, 4),
            h=[round(float(s["hedef"]), 4), round(float(s["hedef2"]), 4), round(float(s["hedef3"]), 4)], kademe=0,
            giris_ts=t, son_ts=int(ep[-1]), sinyal_ts=int(ep[s["i"]]), bar=0, realize=0.0, risk_tl=round(rb * lot, 2),
            fiyat=fiyat, guven=int(s["guven"]), kalite=j["kalite"], kurulum=s.get("kurulum", ""), sebep=s["sebepler"][0], parca=[]))
        self._log("al", f"{lot} lot alındı @ {sayi(giris)} · {j['kalite']} · güven {s['guven']} — {s['sebepler'][0]}", h)
        return True

    def _sat(self, p, lot, fiyat, t, sebep):
        if p not in self.d["poz"] or lot <= 0:
            return
        lot = min(int(lot), p["kalan"])
        net = fiyat * (1 - KAYMA)
        kz = (net - p["giris"]) * lot
        self.d["nakit"] += net * lot
        p["kalan"] -= lot
        p["realize"] += kz
        p["parca"].append([t, round(net, 4), lot, sebep])
        g = self.d["gunler"].setdefault(self._gun(t), dict(kz=0.0, al=0, oz=None))
        g["kz"] = g.get("kz", 0.0) + kz
        if p["kalan"] <= 0:
            self._kapat(p, t, sebep)
        else:
            self._log("kar", f"{sebep}: {lot} lot satıldı @ {sayi(net)} · {'+' if kz >= 0 else '−'}{sayi(abs(kz), 0)} ₺", p["s"])

    def _kapat(self, p, t, sebep):
        d = self.d
        d["poz"].remove(p)
        satilan = sum(x[2] for x in p["parca"]) or 1
        ort = sum(x[1] * x[2] for x in p["parca"]) / satilan
        kz = p["realize"]
        R = kz / p["risk_tl"] if p["risk_tl"] else 0
        d["islem"].append(dict(id=p["id"], s=p["s"], mod=p["mod"], lot=p["lot"], giris=p["giris"], cikis=round(ort, 4),
                               giris_ts=p["giris_ts"], cikis_ts=t, kz=round(kz, 2), yuzde=round(kz / (p["giris"] * p["lot"]) * 100, 2),
                               R=round(R, 2), sebep=sebep, guven=p["guven"], kalite=p["kalite"], kurulum=p["kurulum"]))
        d["islem"] = d["islem"][-1500:]
        self._log("kazanc" if kz > 0 else "zarar",
                  f"Pozisyon kapandı ({sebep}) · {'+' if kz >= 0 else '−'}{sayi(abs(kz), 0)} ₺ · {'+' if R >= 0 else ''}{sayi(R, 1)}R", p["s"])

    def _hedefler(self, p, tepe, t):
        if p in self.d["poz"] and p["kademe"] == 0 and tepe >= p["h"][0]:
            self._sat(p, max(1, p["lot"] // 2), p["h"][0], t, "H1")
            p["kademe"], p["stop"] = 1, p["giris"]              # kalan için stop başabaşa
        if p in self.d["poz"] and p["kademe"] == 1 and tepe >= p["h"][1]:
            self._sat(p, max(1, round(p["lot"] * 0.3)), p["h"][1], t, "H2")
            p["kademe"], p["stop"] = 2, p["h"][0]               # stop H1'e
        if p in self.d["poz"] and p["kademe"] == 2 and tepe >= p["h"][2]:
            self._sat(p, p["kalan"], p["h"][2], t, "H3")

    def _stop_sebep(self, p):
        return "Stop" if p["kademe"] == 0 else ("Başabaş stop" if p["kademe"] == 1 else "İz süren stop")

    def _bar(self, p, o, h, l, t):
        if l <= p["stop"]:                                     # temkinli: aynı mumda önce stop kontrol edilir
            self._sat(p, p["kalan"], min(o, p["stop"]), t, self._stop_sebep(p))
            return
        self._hedefler(p, h, t)

    # --- her taramada çağrılır ---
    def tik(self, analiz: dict, acik: bool, bist_p: float | None):
        with self.kilit:
            d, a = self.d, self.d["ayar"]
            simdi = dt.datetime.now(TZ)
            t = int(simdi.timestamp())
            bugun = simdi.strftime("%Y-%m-%d")
            if d.get("xu0") is None and bist_p:
                d["xu0"] = bist_p

            # 1) Açık pozisyonlar: kapanmış mumlarda stop/hedef, sonra anlık fiyat kontrolü
            for p in list(d["poz"]):
                an = analiz.get(p["mod"], {}).get(p["s"])
                if not an:
                    continue
                ctx = an["ctx"]
                A, n, ep = ctx["A"], ctx["n"], _ep_dizi(ctx["df"])
                for j in range(min(n, len(ep))):
                    tj = int(ep[j])
                    if tj <= p["son_ts"]:
                        continue
                    p["son_ts"], p["bar"] = tj, p["bar"] + 1
                    self._bar(p, float(A["Open"][j]), float(A["High"][j]), float(A["Low"][j]), tj)
                    if p not in d["poz"]:
                        break
                    if p["bar"] >= TEST_UFKU:
                        self._sat(p, p["kalan"], float(A["Close"][j]), tj, "Süre doldu")
                        break
                if p not in d["poz"]:
                    continue
                fiyat = float(an["fiyat"])
                p["fiyat"] = fiyat
                if acik:
                    if fiyat <= p["stop"]:
                        self._sat(p, p["kalan"], fiyat, t, self._stop_sebep(p))
                    else:
                        self._hedefler(p, fiyat, t)
                if p not in d["poz"]:
                    continue
                for s in filtrele(an["sinyaller"], ESIK)[-3:]:   # aynı hissede taze SAT sinyali → çık
                    if (s["yon"] < 0 and n - 1 - s["i"] <= 1 and s["guven"] >= a["guven"]
                            and int(ep[s["i"]]) > p["sinyal_ts"]):
                        self._sat(p, p["kalan"], fiyat, t, "SAT sinyali")
                        break
                if p in d["poz"] and p["mod"] in ("1", "5") and (
                        simdi.time() >= dt.time(17, 55) or self._gun(p["giris_ts"]) != bugun):
                    self._sat(p, p["kalan"], fiyat, t, "Gün sonu")

            # 2) Yeni girişler: sadece seans açıkken, taze AL sinyali, fiyat giriş aralığındaysa
            gun = d["gunler"].setdefault(bugun, dict(kz=0.0, al=0, oz=None))
            mod = a["dilim"]
            gec = mod in ("1", "5") and simdi.time() >= dt.time(17, 40)
            if d["aktif"] and acik and not gec:
                liste = analiz.get(mod, {})
                gorulen = set(d["gorulen"])
                eldeki = {p["s"] for p in d["poz"]}
                adaylar = []
                for h, an in liste.items():
                    ctx = an["ctx"]
                    df, n = ctx["df"], ctx["n"]
                    if pd.Timestamp(df.index[-1]).date() != simdi.date():
                        continue                                  # bugünün verisi yoksa işlem yok
                    for s in filtrele(an["sinyaller"], ESIK)[-2:]:
                        if s["yon"] <= 0 or n - 1 - s["i"] > 1 or s["sonuc"] != "açık" or s["guven"] < a["guven"]:
                            continue
                        j = sinyal_json(s, df, n, an["fiyat"], mod)
                        if KALITE_SIRA[j["kalite"]] > KALITE_SIRA[a["kalite"]]:
                            continue
                        anahtar = f"{h}-{mod}-{j['t']}"
                        f = float(an["fiyat"])
                        if anahtar in gorulen or f <= s["stop"] or not (s["giris_alt"] * 0.998 <= f <= s["giris_ust"] * 1.003):
                            continue
                        adaylar.append((KALITE_SIRA[j["kalite"]], -s["guven"], h, s, j, anahtar, an))
                adaylar.sort(key=lambda x: (x[0], x[1]))
                for _, _, h, s, j, anahtar, an in adaylar:
                    if gun["al"] >= a["gunluk"] or len(d["poz"]) >= a["acik"]:
                        break
                    if h in eldeki:
                        continue
                    if self._al(h, mod, s, j, an, t):
                        gun["al"] += 1
                        eldeki.add(h)
                        d["gorulen"].append(anahtar)
                d["gorulen"] = d["gorulen"][-600:]

            oz = self._ozkaynak()
            gun["oz"] = round(oz, 2)
            if acik or abs(d["egri"][-1][1] - oz) > 0.5:
                d["egri"].append([t, round(oz, 2)])
                if len(d["egri"]) > 4000:
                    d["egri"] = d["egri"][:1] + d["egri"][1::2]
            d["son_tik"] = t
            self._kaydet()

    # --- siteden gelen komutlar (?bot=...) ---
    def komut(self, q: dict) -> str | None:
        k = q.get("bot")
        if not k:
            return None
        with self.kilit:
            d = self.d
            yeni = dict(d["ayar"])
            for ad, tip, lo, hi in (("butce", float, 1000, 1e9), ("gunluk", int, 1, 50), ("acik", int, 1, 20),
                                    ("risk", float, 0.1, 10), ("guven", int, 40, 95)):
                if ad in q:
                    try:
                        yeni[ad] = min(max(tip(float(str(q[ad]).replace(",", "."))), lo), hi)
                    except ValueError:
                        pass
            if q.get("dilim") in MODLAR:
                yeni["dilim"] = q["dilim"]
            if q.get("kalite") in KALITE_SIRA:
                yeni["kalite"] = q["kalite"]
            t = int(time.time())
            mesaj = None
            if k == "sifirla":
                self.d = self._yeni(yeni)
                self._log("bilgi", f"Bot {sayi(yeni['butce'], 0)} TL sanal bütçeyle sıfırdan başladı")
                mesaj = "Bot yeni bütçeyle sıfırlandı"
            elif k == "ayar":
                if yeni["butce"] != d["ayar"]["butce"]:
                    if not d["poz"] and not d["islem"]:
                        d["nakit"] = yeni["butce"]
                        d["egri"] = [[t, yeni["butce"]]]
                        mesaj = "Ayarlar ve bütçe kaydedildi"
                    else:
                        yeni["butce"] = d["ayar"]["butce"]
                        mesaj = "Ayarlar kaydedildi · bütçe için 'Sıfırla' gerekir"
                d["ayar"] = yeni
                self._log("bilgi", f"Ayarlar: {DILIM_ADI[yeni['dilim']]}, günde {yeni['gunluk']} işlem, en fazla {yeni['acik']} pozisyon, "
                                   f"risk %{sayi(yeni['risk'], 1)}, güven {yeni['guven']}+, kalite {yeni['kalite']}+")
                mesaj = mesaj or "Ayarlar kaydedildi"
            elif k == "baslat":
                d["aktif"] = True
                self._log("bilgi", "Bot başlatıldı")
                mesaj = "Bot çalışıyor"
            elif k == "durdur":
                d["aktif"] = False
                self._log("bilgi", "Bot duraklatıldı (açık pozisyonlar takip edilmeye devam eder)")
                mesaj = "Bot duraklatıldı"
            elif k in ("kapat", "hepsi"):
                for p in list(d["poz"]):
                    if k == "hepsi" or p["id"] == q.get("id"):
                        self._sat(p, p["kalan"], p["fiyat"], t, "Elle kapatıldı")
                mesaj = "Pozisyon kapatıldı" if k == "kapat" else "Tüm pozisyonlar kapatıldı"
            self._kaydet()
            return mesaj

    # --- istatistik ve site verisi ---
    def _istatistik(self) -> dict:
        d = self.d
        isl = d["islem"]
        n = len(isl)
        kaz = [x["kz"] for x in isl if x["kz"] > 0]
        kay = [x["kz"] for x in isl if x["kz"] <= 0]
        brut_k, brut_z = sum(kaz), -sum(kay)
        pf = (brut_k / brut_z if brut_z > 0 else (9.99 if brut_k > 0 else None))
        tepe, dd = 0.0, 0.0
        for _, v in d["egri"]:
            tepe = max(tepe, v)
            dd = min(dd, (v / tepe - 1) * 100 if tepe else 0)
        seri_k = seri_z = sk = sz = 0
        for x in isl:
            if x["kz"] > 0:
                sk, sz = sk + 1, 0
            else:
                sz, sk = sz + 1, 0
            seri_k, seri_z = max(seri_k, sk), max(seri_z, sz)
        gunler = sorted((g, v) for g, v in d["gunler"].items() if v.get("al") or abs(v.get("kz", 0)) > 0.01)
        karli = sum(1 for _, v in gunler if v.get("kz", 0) > 0)
        onceki, getiriler = d["ayar"]["butce"], []
        for g, v in sorted(d["gunler"].items()):
            if v.get("oz"):
                getiriler.append((v["oz"] / onceki - 1) * 100 if onceki else 0)
                onceki = v["oz"]
        kazanma = len(kaz) / n * 100 if n else None
        karli_gun = karli / len(gunler) * 100 if gunler else None
        skor, etiket = None, "Veri birikiyor"
        if n >= 5:
            parca = dict(pf=min((pf or 0) / 2, 1) * 100, kazanma=kazanma or 0,
                         gun=karli_gun if karli_gun is not None else (kazanma or 0), dd=max(0.0, 1 - abs(dd) / 10) * 100)
            skor = round(0.3 * parca["pf"] + 0.25 * parca["kazanma"] + 0.25 * parca["gun"] + 0.2 * parca["dd"])
            etiket = "Çok tutarlı" if skor >= 75 else "Tutarlı" if skor >= 60 else "Kararsız" if skor >= 45 else "Tutarsız"
        return dict(n=n, kazanan=len(kaz), kaybeden=len(kay), kazanma=_r(kazanma, 1), pf=_r(pf, 2),
                    ortR=_r(np.mean([x["R"] for x in isl]), 2) if n else None,
                    beklenti=_r(np.mean([x["kz"] for x in isl]), 0) if n else None,
                    ort_kaz=_r(np.mean(kaz), 0) if kaz else None, ort_kay=_r(np.mean(kay), 0) if kay else None,
                    dd=_r(dd, 2), seri_k=seri_k, seri_z=seri_z, karli_gun=_r(karli_gun, 0), gun_sayisi=len(gunler),
                    std=_r(float(np.std(getiriler)), 2) if len(getiriler) >= 2 else None, skor=skor, etiket=etiket)

    def ui(self, bist_p: float | None) -> dict:
        with self.kilit:
            d, a = self.d, self.d["ayar"]
            oz = self._ozkaynak()
            kz = oz - a["butce"]
            saat = lambda t: dt.datetime.fromtimestamp(t, TZ).strftime("%d.%m %H:%M")  # noqa: E731
            poz = []
            for p in d["poz"]:
                pk = p["realize"] + (p["fiyat"] * (1 - KAYMA) - p["giris"]) * p["kalan"]
                poz.append(dict(id=p["id"], s=p["s"], mod=p["mod"], lot=p["lot"], kalan=p["kalan"], giris=p["giris"],
                                fiyat=_r(p["fiyat"], 4), stop=p["stop"], stop0=p["stop0"], h=p["h"], kademe=p["kademe"],
                                kz=_r(pk, 0), yuzde=_r(pk / (p["giris"] * p["lot"]) * 100, 2), saat=saat(p["giris_ts"]),
                                bar=p["bar"], guven=p["guven"], kalite=p["kalite"], sebep=p["sebep"]))
            islem = [dict(s=x["s"], mod=x["mod"], lot=x["lot"], giris=x["giris"], cikis=x["cikis"], kz=x["kz"], yuzde=x["yuzde"],
                          R=x["R"], sebep=x["sebep"], g=saat(x["giris_ts"]), c=saat(x["cikis_ts"]), kalite=x["kalite"],
                          sure=round((x["cikis_ts"] - x["giris_ts"]) / 60)) for x in reversed(d["islem"][-150:])]
            eg = d["egri"]
            adim = max(1, len(eg) // 400)
            egri = eg[::adim] + ([eg[-1]] if (len(eg) - 1) % adim else [])
            gunler, onceki = [], a["butce"]
            for g, v in sorted(d["gunler"].items()):
                if v.get("oz") is None and not v.get("al"):
                    continue
                o = v.get("oz") or onceki
                gunler.append(dict(g=f"{g[8:10]}.{g[5:7]}", kz=_r(v.get("kz", 0), 0), islem=v.get("al", 0),
                                   ret=_r((o / onceki - 1) * 100 if onceki else 0, 2)))
                onceki = o
            bugun = d["gunler"].get(dt.datetime.now(TZ).strftime("%Y-%m-%d"), {})
            return dict(aktif=d["aktif"], ayar=a, baslangic=saat(d["baslangic"]), nakit=_r(d["nakit"], 0), ozk=_r(oz, 0),
                        kz=_r(kz, 0), kz_yuzde=_r(kz / a["butce"] * 100, 2),
                        realize=_r(sum(x["kz"] for x in d["islem"]), 0),
                        bist=_r((bist_p / d["xu0"] - 1) * 100, 2) if bist_p and d.get("xu0") else None,
                        poz=poz, islem=islem, egri=egri, gunler=gunler[-30:],
                        log=[[saat(x[0]), x[1], x[2], x[3]] for x in reversed(d["log"][-80:])],
                        st=self._istatistik(), bugun=dict(islem=bugun.get("al", 0)),
                        son_tik=saat(d["son_tik"]) if d.get("son_tik") else None)


# ---------- Arka plan servisi: sürekli tarar, botu çalıştırır, site açılınca hazır sonuç verir ----------
class Servis:
    def __init__(self):
        self.veri = None
        self.bist_p = None
        self.surum = 0
        self.durum = "Motor başlatılıyor"
        self.ilerleme = 0.0
        self.hata = None
        self.gunluk, self.gunluk_zaman = None, 0
        self.derin_zaman = 0
        self.derin_sin = {m: {} for m in MODLAR}
        self.karne = {m: [] for m in MODLAR}
        self.bot = {m: dict(n=0) for m in MODLAR}
        self.canli = CanliBot()
        threading.Thread(target=self._dongu, daemon=True).start()

    def sayfa(self, mesaj: str | None = None) -> str:
        bot = json.dumps(self.canli.ui(self.bist_p), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return (ARAYUZ.replace("__BOT__", bot).replace("__MESAJ__", json.dumps(mesaj, ensure_ascii=False))
                .replace("__VERI__", self.veri))

    def _dongu(self):
        while True:
            try:
                self._tur(derin=False)
                if time.time() - self.derin_zaman > 1800:
                    self._tur(derin=True)
                self.hata = None
            except Exception as e:  # noqa: BLE001
                self.hata = f"{type(e).__name__}: {e}"
            time.sleep(120 if seans_acik_mi() else 900)

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
        xu15_gercek = xu15 is not None and len(xu15) > 40
        if not xu15_gercek and xug is not None and len(xug) > 60:
            # Yahoo endeksin 15 dk verisini vermezse: bir önceki günün kapanışı gün içine yayılır (ileriye bakmaz)
            xu15 = pd.DataFrame({"Close": xug["Close"].shift(1)}).dropna()
            xu15.index = xu15.index.tz_localize(TZ) + pd.Timedelta(hours=9)
        # 1 ve 5 dakikalık veri sadece en likit hisselerde (scalp ancak derin tahtada mantıklı)
        hizli = sorted(likitler, key=lambda h: -(gunluk[h]["Close"] * gunluk[h]["Volume"]).tail(20).mean())[:HIZLI_EVREN]
        self.durum, self.ilerleme = "En likit hisselerin 5 ve 1 dakikalık verisi indiriliyor", 0.18
        g5 = _gun_ici(hizli, "20d", "5m")
        g1 = _gun_ici(hizli, "5d", "1m")
        kaynak = {"1": g1, "5": g5, "g": gi}
        analiz = {m: {} for m in MODLAR}
        for k, h in enumerate(likitler):
            self.durum = ("Derin geçmiş test ve kurulum karnesi" if derin else "Hisseler analiz ediliyor") + f" · {h}"
            self.ilerleme = 0.2 + 0.75 * k / max(len(likitler), 1)
            for mod in MODLAR:
                if mod in ("1", "5") and h not in hizli:
                    continue
                try:
                    if mod == "w":
                        a = hisse_analiz(h, gunluk.get(h), gunluk.get(h), xug, not acik, tam_test=derin, mod="w")
                    else:
                        a = hisse_analiz(h, kaynak[mod].get(h), gunluk.get(h), xu15, not acik, tam_test=derin, mod=mod)
                    if a:
                        analiz[mod][h] = a
                except Exception:  # noqa: BLE001
                    pass

        if derin:
            for mod in MODLAR:
                tum = []
                for h, a in analiz[mod].items():
                    f = filtrele(a["sinyaller"], ESIK)
                    for s_ in f:
                        s_["sym"] = h
                    tum += f
                    df, n = a["ctx"]["df"], a["ctx"]["n"]
                    self.derin_sin[mod][h] = [kompakt(sinyal_json(s_, df, n, a["fiyat"], mod)) for s_ in f]
                self.karne[mod], AGIRLIK[mod] = karne_hesapla(tum)
                self.bot[mod] = bot_portfoyu(tum)
            self.derin_zaman = time.time()

        bist = None
        rejim = "Yatay"
        if xug is not None and len(xug) > 60:
            e50 = xug["Close"].ewm(span=50, adjust=False).mean().iloc[-1]
            e20 = xug["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
            son = xug["Close"].iloc[-1]
            rejim = "Boğa" if son > e20 > e50 else ("Ayı" if son < e20 < e50 else "Yatay")
        if xu15_gercek:
            xc = gi["XU100"]["Close"]
            dun = xc[xc.index.date < xc.index[-1].date()]
            bist = dict(p=_r(xc.iloc[-1], 2), d=_r((xc.iloc[-1] / dun.iloc[-1] - 1) * 100 if len(dun) else 0, 2),
                        spark=[_r(x, 2) for x in xc.tail(64).values])
        elif xug is not None and len(xug) > 2:
            bist = dict(p=_r(xug["Close"].iloc[-1], 2), d=_r((xug["Close"].iloc[-1] / xug["Close"].iloc[-2] - 1) * 100, 2),
                        spark=[_r(x, 2) for x in xug["Close"].tail(30).values])
        if bist:
            bist["rejim"] = rejim
            bist["spark_w"] = [_r(x, 2) for x in xug["Close"].tail(60).values] if xug is not None else bist["spark"]
        self.bist_p = bist["p"] if bist else None

        # Canlı bot: yeni sinyallere gir, açık pozisyonları yönet
        self.durum = "Canlı bot pozisyonları güncelliyor"
        try:
            self.canli.tik(analiz, acik, self.bist_p)
        except Exception as e:  # noqa: BLE001
            self.hata = f"Bot: {type(e).__name__}: {e}"

        hisseler = []
        for h in likitler:
            if not any(h in analiz[m] for m in MODLAR):
                continue
            ana = next(analiz[m][h] for m in ("g", "w", "5", "1") if h in analiz[m])
            kayit = dict(s=h, sek=sektor_bul(h), lik=_r(ana["likidite"], 1), hizli=h in hizli)
            for mod in MODLAR:
                a = analiz[mod].get(h)
                kayit[mod] = mod_json(a, self.derin_sin[mod].get(h)) if a else None
            hisseler.append(kayit)
        akis = akis_olaylari(analiz)
        paket = dict(hisseler=hisseler, akis=akis, vade=VADE, dilim=DILIM_ADI, bist=bist, sektorler=sektor_ozeti(analiz["g"]), karne=self.karne, bot=self.bot,
                     seans=acik, guncelleme=f"{dt.datetime.now(TZ):%H:%M}", taranan=len(TUM_HISSELER),
                     likit=len(likitler), ufuk=TEST_UFKU, esik=ESIK,
                     derin=f"{dt.datetime.fromtimestamp(self.derin_zaman, TZ):%H:%M}" if self.derin_zaman else None)
        self.veri = json.dumps(paket, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        self.surum += 1
        self.durum, self.ilerleme = "Hazır", 1.0


@st.cache_resource
def servis_al_v2(surum: str = "bot-1") -> Servis:
    # Ad ve sürüm değişince Streamlit eski (önceki app.py'den kalan) servisi kullanmaz
    return Servis()


YUKLEME = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap" rel="stylesheet">
<style>html,body{margin:0;height:100%;background:#060912;color:#eef1f8;font-family:Manrope,system-ui,sans-serif;overflow:hidden}
.a{position:fixed;inset:0;pointer-events:none}.a i{position:absolute;border-radius:50%;filter:blur(70px)}
.a i:nth-child(1){width:360px;height:360px;background:#5b47ff;opacity:.45;top:-140px;left:-120px;animation:y 9s ease-in-out infinite alternate}
.a i:nth-child(2){width:300px;height:300px;background:#0ea5c6;opacity:.3;bottom:-120px;right:-120px;animation:y 11s ease-in-out infinite alternate-reverse}
@keyframes y{to{transform:translate(60px,50px) scale(1.15)}}
.k{position:relative;height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;text-align:center;padding:24px}
.r{position:relative;width:132px;height:132px}
.r .h{position:absolute;inset:0;border-radius:50%;border:1px solid rgba(124,108,255,.35)}
.r .h:nth-child(2){inset:22px;border-color:rgba(34,211,238,.3)}.r .h:nth-child(3){inset:44px;border-color:rgba(255,255,255,.18)}
.r .s{position:absolute;inset:0;border-radius:50%;background:conic-gradient(from 0deg,rgba(124,108,255,0) 0deg,rgba(124,108,255,0) 280deg,rgba(124,108,255,.55) 340deg,rgba(34,211,238,.9) 360deg);animation:d 2.2s linear infinite;-webkit-mask:radial-gradient(circle,transparent 0,#000 1px)}
.r .p{position:absolute;width:8px;height:8px;border-radius:50%;background:#2fe0a0;box-shadow:0 0 12px #2fe0a0;animation:b 2.2s infinite}
.r .p:nth-of-type(5){top:30px;left:84px}.r .p:nth-of-type(6){top:86px;left:30px;animation-delay:.9s;background:#22d3ee;box-shadow:0 0 12px #22d3ee}
.r svg{position:absolute;inset:40px;width:52px;height:52px}
@keyframes d{to{transform:rotate(360deg)}}@keyframes b{0%,100%{opacity:.15;transform:scale(.6)}40%{opacity:1;transform:scale(1)}}
h1{margin:0;font-size:26px;font-weight:800;letter-spacing:-.03em}h1 span{background:linear-gradient(135deg,#a99bff,#22d3ee);-webkit-background-clip:text;background-clip:text;color:transparent}
p{color:#8b93a7;font-size:13px;margin:0;line-height:1.5;max-width:300px}
.b{width:240px;height:6px;border-radius:9px;background:rgba(255,255,255,.07);overflow:hidden}.b i{display:block;height:100%;border-radius:9px;background:linear-gradient(90deg,#7c6cff,#22d3ee);width:__Y__%;transition:width .6s}
small{color:#5b6378;font-size:11.5px;max-width:280px;line-height:1.5}</style></head><body><div class="a"><i></i><i></i></div><div class="k">
<div class="r"><div class="h"></div><div class="h"></div><div class="h"></div><div class="s"></div><i class="p"></i><i class="p"></i>
<svg viewBox="0 0 40 40"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#7c6cff"/><stop offset="1" stop-color="#22d3ee"/></linearGradient></defs><rect width="40" height="40" rx="12" fill="url(#g)"/><path d="M9 27l6-6 4 3 9-10" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="28" cy="14" r="2.8" fill="#fff"/></svg></div>
<h1>Borsa <span>Radar</span></h1><div class="b"><i></i></div><p>__D__</p>
<small>İlk açılışta bütün borsa 1 dk, 5 dk, 15 dk ve günlük grafiklerde taranıyor. Sonraki açılışlarda sonuçlar hazır gelir.</small>__H__</div></body></html>"""


# ---------- Sayfa ----------
st.markdown("""
<style>
#MainMenu, footer, header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"] {display:none !important}
.stApp {background:#060912}
.block-container {padding:0 !important; max-width:100% !important}
iframe {height:100dvh !important; display:block; border:0}
div[data-testid="stVerticalBlock"] {gap:0 !important}
</style>""", unsafe_allow_html=True)

servis = servis_al_v2()
if not hasattr(servis, "canli"):   # önbellekte eski sürüm kalmışsa temizle ve yeniden kur
    st.cache_resource.clear()
    servis = servis_al_v2()

mesaj = None
try:
    sorgu = st.query_params.to_dict()
except Exception:  # noqa: BLE001
    sorgu = {}
if sorgu.get("bot"):          # sitedeki bot ayarları / komutları adres satırıyla gelir
    mesaj = servis.canli.komut(sorgu)
    st.query_params.clear()

if servis.veri is None:
    # İlk açılış: motor ilk taramayı bitirene kadar yükleme ekranı, birkaç saniyede bir yenilenir
    hata = f'<p style="color:#ff5c7c">{servis.hata}</p>' if servis.hata else ""
    components.html(YUKLEME.replace("__D__", servis.durum).replace("__Y__", f"{servis.ilerleme * 100:.0f}")
                    .replace("__H__", hata), height=760)
    time.sleep(3)
    st.rerun()
else:
    components.html(servis.sayfa(mesaj), height=760, scrolling=False)
