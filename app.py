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
Kalıcı kayıt: Streamlit Secrets'a GITHUB_TOKEN ve GITHUB_REPO eklenirse bot geçmişi GitHub'da 'bot-veri' dalında saklanır.

Yatırım tavsiyesi değildir.
"""

import bisect
import datetime as dt
import base64
import gc
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import email.utils
import xml.etree.ElementTree as ET
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
               "sweep": "Stop avı + dönüş", "emilim": "Emilim", "yapi": "Yapı kırılımı / CHoCH",
               "uyum": "RSI uyumsuzluğu + onay mumu"}
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
    # ADX / DI: trendin gücü ve yönü
    yuk, asg = h.diff(), -l.diff()
    pdm = pd.Series(np.where((yuk > asg) & (yuk > 0), yuk, 0.0), index=df.index)
    ndm = pd.Series(np.where((asg > yuk) & (asg > 0), asg, 0.0), index=df.index)
    df["PDI"] = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / df["ATR"].replace(0, np.nan)
    df["NDI"] = 100 * ndm.ewm(alpha=1 / 14, adjust=False).mean() / df["ATR"].replace(0, np.nan)
    dx = 100 * (df["PDI"] - df["NDI"]).abs() / (df["PDI"] + df["NDI"]).replace(0, np.nan)
    df["ADX"] = dx.ewm(alpha=1 / 14, adjust=False).mean()
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
def pivot_bul(df: pd.DataFrame, P: int | None = None) -> list[tuple]:
    """Belirgin tepe/dipler: sağ-sol PIVOT_PENCERE mumun en yükseği/düşüğü VE en az ~0,8 ATR'lik salınım.
    Küçük titreşimler seviye sayılmaz (eski sürümde her minik dalga seviye oluyordu)."""
    P = P or PIVOT_PENCERE
    w = 2 * P + 1
    hm = df["High"].rolling(w, center=True).max().values
    lm = df["Low"].rolling(w, center=True).min().values
    H, L = df["High"].values, df["Low"].values
    atr = df["ATR"].values if "ATR" in df else (df["High"] - df["Low"]).rolling(14).mean().values
    pv = []
    for j in range(len(df)):
        a = atr[j] if not np.isnan(atr[j]) else (H[j] - L[j])
        if not np.isnan(hm[j]) and H[j] == hm[j]:
            sol, sag = L[max(0, j - 3 * P):j + 1].min(), L[j:j + P + 1].min()
            if H[j] - max(sol, sag) >= 0.8 * a:
                pv.append((j, float(H[j]), "H"))
        if not np.isnan(lm[j]) and L[j] == lm[j]:
            sol, sag = H[max(0, j - 3 * P):j + 1].max(), H[j:j + P + 1].max()
            if min(sol, sag) - L[j] >= 0.8 * a:
                pv.append((j, float(L[j]), "L"))
    return pv


def seviye_kumeleri(pv: list[tuple], son_j: int, tol: float, kaynak: str = "tepe-dip", ufuk: int = 400) -> list[dict]:
    """Tepe/dipleri fiyat yakınlığına göre kümeler ve her seviyeye 0-1 güç puanı verir.
    Güç: temas sayısı + tazelik + rol değişimi (eski direncin desteğe dönmesi ya da tersi)."""
    if not pv:
        return []
    sirali = sorted(pv, key=lambda p: p[1])
    gruplar = [[sirali[0]]]
    for p in sirali[1:]:
        m = sum(x[1] for x in gruplar[-1]) / len(gruplar[-1])
        if abs(p[1] - m) / m <= tol:
            gruplar[-1].append(p)
        else:
            gruplar.append([p])
    out = []
    for g in gruplar:
        temas = len(g)
        son = max(x[0] for x in g)
        tazelik = max(0.0, 1 - (son_j - son) / ufuk)
        rol = len({x[2] for x in g}) == 2
        guc = min(1.0, 0.2 * min(temas, 4) + 0.3 * tazelik + (0.15 if rol else 0))
        out.append(dict(p=float(sum(x[1] for x in g) / temas), temas=temas, son=son, guc=round(guc, 3), rol=rol, kaynak=kaynak))
    return out


def seviyeler_bul(pv: list[tuple], tol: float = SEVIYE_TOLERANS) -> list[float]:
    """Geriye uyumluluk: sadece güçlü seviyelerin fiyatları."""
    if not pv:
        return []
    son_j = max(p[0] for p in pv)
    return [d["p"] for d in seviye_kumeleri(pv, son_j, tol) if d["temas"] >= 2 or d["guc"] >= 0.5]


def _olay_say(idx: np.ndarray, ara: int = 3) -> list[int]:
    """Art arda gelen mumları tek tepki say (aynı test birden çok mum sürebilir)."""
    out, son = [], -99
    for j in idx:
        if j - son > ara:
            out.append(int(j))
        son = j
    return out


def bolgeler(A: dict, pv: list[tuple], i: int, pencere: int, ek: list[dict] | None = None) -> list[dict]:
    """Destek/direnç BÖLGELERİ. Tepe-dip kümelerinden aday bölge çıkarılır, sonra pencere içindeki her mumda
    fiyatın o bölgeye fitille girip geri döndüğü (reddedildiği) anlar sayılır. Gerçek tepki görmeyen bölge elenir."""
    atr = nanv(A["ATR"][i], A["Close"][i] * 0.01)
    bas = max(0, i - pencere)
    H, L, C = A["High"][bas:i + 1], A["Low"][bas:i + 1], A["Close"][bas:i + 1]
    pvw = sorted([p for p in pv if bas <= p[0] <= i], key=lambda p: p[1])
    gruplar = []
    for p in pvw:                                        # fiyatı birbirine 0,6 ATR'den yakın tepe-dipler aynı bölge
        if gruplar and p[1] - np.mean([x[1] for x in gruplar[-1]]) <= 0.6 * atr:
            gruplar[-1].append(p)
        else:
            gruplar.append([p])
    adaylar = []
    for g in gruplar:
        fl = [x[1] for x in g]
        lo, hi = min(fl) - 0.12 * atr, max(fl) + 0.12 * atr
        if hi - lo > 0.9 * atr:
            m = float(np.median(fl))
            lo, hi = m - 0.45 * atr, m + 0.45 * atr
        adaylar.append(dict(lo=lo, hi=hi, kaynak="tepe-dip", pv=len(g)))
    for d in ek or []:                                   # günlük grafik seviyeleri
        adaylar.append(dict(lo=d["p"] - 0.3 * atr, hi=d["p"] + 0.3 * atr, kaynak="günlük", pv=d.get("temas", 1), gbonus=0.12))
    out = []
    for z in adaylar:
        lo, hi = z["lo"], z["hi"]
        # Tepki = bölgeye fitille girip dışında kapanan, yerel tepe/dip olan VE sonraki 8 mumda bölgeden en az 1,5 ATR uzaklaşan mum
        ust_aday = np.where((H >= lo) & (H <= hi + 0.3 * atr) & (C < lo))[0]
        alt_aday = np.where((L <= hi) & (L >= lo - 0.3 * atr) & (C > hi))[0]
        ust = [j for j in ust_aday if H[j] >= H[max(0, j - 3):j + 4].max() and L[j:j + 9].min() <= lo - 1.5 * atr]
        alt = [j for j in alt_aday if L[j] <= L[max(0, j - 3):j + 4].min() and H[j:j + 9].max() >= hi + 1.5 * atr]
        ue, ae = _olay_say(ust, 6), _olay_say(alt, 6)
        test = len(ue) + len(ae)
        if test == 0 and z["kaynak"] != "günlük":
            continue
        tum = sorted(ue + ae)
        son = (tum[-1] + bas) if tum else bas
        tazelik = max(0.0, 1 - (i - son) / pencere)
        rol = bool(ue and ae)
        guc = min(1.0, 0.16 * min(test, 5) + 0.2 * tazelik + (0.12 if rol else 0) + z.get("gbonus", 0))
        dokunus = [(int(j + bas), float(H[j]) if j in set(ue) else float(L[j])) for j in tum][-8:]
        out.append(dict(lo=float(lo), hi=float(hi), p=float((lo + hi) / 2), temas=test, ust_n=len(ue), alt_n=len(ae), guc=round(guc, 3),
                        rol=rol, kaynak=z["kaynak"], ilk=int(tum[0] + bas) if tum else bas, son=int(son), dokunus=dokunus))
    out.sort(key=lambda d: d["p"])
    birlesik = []
    for d in out:                                        # üst üste binen bölgeleri birleştir
        if birlesik and d["lo"] <= birlesik[-1]["hi"]:
            e = birlesik[-1]
            ana, yan = (e, d) if e["guc"] >= d["guc"] else (d, e)
            y = dict(ana)
            y["lo"], y["hi"] = min(e["lo"], d["lo"]), max(e["hi"], d["hi"])
            if y["hi"] - y["lo"] > 1.1 * atr:
                y["lo"], y["hi"] = ana["lo"], ana["hi"]
            y["p"] = (y["lo"] + y["hi"]) / 2
            y["temas"] = max(e["temas"], d["temas"])
            y["guc"] = round(min(1.0, ana["guc"] + 0.06), 3)
            y["rol"] = e["rol"] or d["rol"]
            y["kaynak"] = ana["kaynak"] if e["kaynak"] == d["kaynak"] else "tepe-dip + günlük"
            y["dokunus"] = sorted(e["dokunus"] + d["dokunus"])[-8:]
            y["ilk"], y["son"] = min(e["ilk"], d["ilk"]), max(e["son"], d["son"])
            birlesik[-1] = y
        else:
            birlesik.append(d)
    secilen = []                                         # birbirine 1 ATR'den yakın bölgelerden sadece güçlüsü kalır
    for d in sorted(birlesik, key=lambda d: -d["guc"]):
        if all(abs(d["p"] - e["p"]) > 1.0 * atr for e in secilen):
            secilen.append(d)
    return sorted(secilen, key=lambda d: d["p"])


def seviye_listesi(ctx: dict, i: int, pv: list[tuple]) -> list[dict]:
    """i. mumda geçerli destek/direnç bölgeleri (sadece i'ye kadar bilinen veriyle)."""
    anahtar = (len(pv), int(ctx["gun_no"][i]))
    onb = ctx.setdefault("sev_onbellek", {})
    if anahtar in onb:
        return onb[anahtar]
    pencere = {"1": 300, "5": 300, "g": 360, "w": 250}.get(ctx["mod"], 300)
    z = [d for d in bolgeler(ctx["A"], pv, i, pencere, ctx["gun_sev"](i)) if d["temas"] >= 2 or d["guc"] >= 0.5]
    onb[anahtar] = z
    return z


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


# ---------- Mum formasyonları ve uyumsuzluk ----------
def mum_formasyon(A: dict, i: int) -> list[tuple]:
    """Son mumdaki mum formasyonları: (ad, yön, puan). Yön 0 = kararsızlık."""
    if i < 5:
        return []
    O, Hh, Ll, C = A["Open"], A["High"], A["Low"], A["Close"]
    o, h, l, c = O[i], Hh[i], Ll[i], C[i]
    o1, h1, l1, c1 = O[i - 1], Hh[i - 1], Ll[i - 1], C[i - 1]
    atr = nanv(A["ATR"][i], c * 0.01)
    govde, aralik = abs(c - o), max(h - l, 1e-9)
    ust, alt = h - max(o, c), min(o, c) - l
    g1 = abs(c1 - o1)
    dusus, yukselis = C[i - 1] < C[i - 5], C[i - 1] > C[i - 5]
    out = []
    if c > o and c1 < o1 and c >= o1 and o <= c1 and govde > g1 and govde >= 0.3 * atr:
        out.append(("Yutan boğa", 1, 10))
    if c < o and c1 > o1 and c <= o1 and o >= c1 and govde > g1 and govde >= 0.3 * atr:
        out.append(("Yutan ayı", -1, 10))
    if alt >= 2 * govde and ust <= 0.25 * aralik and aralik >= 0.6 * atr and dusus:
        out.append(("Çekiç", 1, 8))
    if ust >= 2 * govde and alt <= 0.25 * aralik and aralik >= 0.6 * atr and yukselis:
        out.append(("Kayan yıldız", -1, 8))
    if ust >= 2 * govde and alt <= 0.25 * aralik and aralik >= 0.6 * atr and dusus:
        out.append(("Ters çekiç", 1, 4))
    if alt >= 2 * govde and ust <= 0.25 * aralik and aralik >= 0.6 * atr and yukselis:
        out.append(("Asılı adam", -1, 4))
    o2, c2 = O[i - 2], C[i - 2]
    g2 = abs(c2 - o2)
    if c2 < o2 and g2 >= 0.6 * atr and g1 <= 0.35 * g2 and c > o and c > (o2 + c2) / 2:
        out.append(("Sabah yıldızı", 1, 10))
    if c2 > o2 and g2 >= 0.6 * atr and g1 <= 0.35 * g2 and c < o and c < (o2 + c2) / 2:
        out.append(("Akşam yıldızı", -1, 10))
    son3 = range(i - 2, i + 1)
    if all(C[k] > O[k] and abs(C[k] - O[k]) >= 0.5 * atr and Hh[k] - C[k] <= 0.3 * (Hh[k] - Ll[k]) for k in son3) and C[i] > C[i - 1] > C[i - 2]:
        out.append(("Üç beyaz asker", 1, 8))
    if all(C[k] < O[k] and abs(C[k] - O[k]) >= 0.5 * atr and C[k] - Ll[k] <= 0.3 * (Hh[k] - Ll[k]) for k in son3) and C[i] < C[i - 1] < C[i - 2]:
        out.append(("Üç kara karga", -1, 8))
    if g1 >= 0.8 * atr and govde <= 0.4 * g1 and max(o, c) <= max(o1, c1) and min(o, c) >= min(o1, c1):
        if c1 < o1 and c > o:
            out.append(("Boğa harami", 1, 5))
        elif c1 > o1 and c < o:
            out.append(("Ayı harami", -1, 5))
    if govde <= 0.1 * aralik and aralik >= 0.5 * atr:
        out.append(("Doji (kararsızlık)", 0, 0))
    if h <= h1 and l >= l1:
        out.append(("İçeri mum (sıkışma)", 0, 0))
    return out


def uyumsuzluk(A: dict, pv: list[tuple], i: int) -> int:
    """RSI uyumsuzluğu: fiyat daha düşük dip yaparken RSI daha yüksek dip (+1) ya da tersi (-1)."""
    r = A["RSI"]
    L = [p for p in pv if p[2] == "L" and p[0] >= i - 70][-2:]
    H = [p for p in pv if p[2] == "H" and p[0] >= i - 70][-2:]
    if len(L) == 2 and i - L[1][0] <= 14 and L[1][1] < L[0][1] and nanv(r[L[1][0]], 50) > nanv(r[L[0][0]], 50) + 3 and nanv(r[L[0][0]], 50) < 45:
        return 1
    if len(H) == 2 and i - H[1][0] <= 14 and H[1][1] > H[0][1] and nanv(r[H[1][0]], 50) < nanv(r[H[0][0]], 50) - 3 and nanv(r[H[0][0]], 50) > 55:
        return -1
    return 0


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
    ftol = min(0.015, max(0.004, 1.0 * atr / c))   # "aynı seviye" sayılacak fark: hissenin oynaklığına göre

    def ekle(ad, yon, durum, cizgiler, hedef, ref):
        sonuc.append(dict(ad=ad, yon=yon, durum=durum, cizgiler=cizgiler, hedef=hedef, ref=ref))

    if len(L) >= 2:
        (j1, p1, _), (j2, p2, _) = L[-2], L[-1]
        if j2 - j1 >= 8 and abs(p1 - p2) / p1 <= ftol and i - j2 <= 40:
            jm = j1 + int(np.argmax(Hh[j1:j2 + 1]))
            boyun, dip = float(Hh[jm]), min(p1, p2)
            if boyun / max(p1, p2) - 1 >= 0.02 and np.min(Ll[j2 + 1:i], initial=np.inf) >= dip * 0.99:
                durum = "kırıldı" if c > boyun >= cp else ("oluşuyor" if c <= boyun else None)
                if durum:
                    ekle("İkili dip", 1, durum, [(j1, p1, jm, boyun), (jm, boyun, j2, p2), (j1, boyun, i, boyun)],
                         boyun + (boyun - dip), boyun)
    if len(H) >= 2:
        (j1, p1, _), (j2, p2, _) = H[-2], H[-1]
        if j2 - j1 >= 8 and abs(p1 - p2) / p1 <= ftol and i - j2 <= 40:
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
        j0 = int(min(hx[0], lx[0]))
        ust = lambda j: sh * j + bh  # noqa: E731
        alt = lambda j: sl * j + bl  # noqa: E731
        gen0, gen = ust(j0) - alt(j0), ust(i) - alt(i)
        daralan = 0 < gen < gen0 * 0.85
        paralel = gen0 > 0 and abs(gen - gen0) <= 0.25 * gen0
        tip = None
        if daralan and abs(nh) < F and nl > F:
            tip = ("Yükselen üçgen", 1)
        elif daralan and abs(nl) < F and nh < -F:
            tip = ("Alçalan üçgen", -1)
        elif daralan and nh < -F and nl > F:
            tip = ("Simetrik üçgen", 0)
        elif daralan and nh > F and nl > nh * 1.15:
            tip = ("Yükselen kama", -1)
        elif daralan and nl < -F and nh < nl * 1.15:
            tip = ("Düşen kama", 1)
        elif paralel and nh > F and nl > F:
            tip = ("Yükselen kanal", 0)
        elif paralel and nh < -F and nl < -F:
            tip = ("Düşen kanal", 0)
        elif paralel and abs(nh) < F and abs(nl) < F and gen <= 8 * atr:
            tip = ("Dikdörtgen (yatay bant)", 0)
        if not tip:
            continue
        if gen > 0 and alt(i - 1) * 0.997 <= cp <= ust(i - 1) * 1.003:
            if c > ust(i) * 1.002:
                durum, yon, hedef, ref = "kırıldı", 1, c + gen0, ust(i)
            elif c < alt(i) * 0.998:
                durum, yon, hedef, ref = "kırıldı", -1, c - gen0, alt(i)
            else:
                durum, yon, hedef, ref = "oluşuyor", tip[1], None, ust(i) if tip[1] >= 0 else alt(i)
            ekle(tip[0], yon, durum, [(j0, ust(j0), i, ust(i)), (j0, alt(j0), i, alt(i))], hedef, ref)
            break
    if len(L) >= 3:   # üçlü dip
        (a, la, _), (b, lb, _), (d, ld, _) = L[-3:]
        dipler = (la, lb, ld)
        if max(dipler) / min(dipler) - 1 <= ftol and b - a >= 6 and d - b >= 6 and i - d <= 40:
            boyun = float(Hh[a:d + 1].max())
            if boyun / max(dipler) - 1 >= 0.02:
                durum = "kırıldı" if c > boyun >= cp else ("oluşuyor" if c <= boyun else None)
                if durum:
                    ekle("Üçlü dip", 1, durum, [(a, la, b, lb), (b, lb, d, ld), (a, boyun, i, boyun)], boyun + (boyun - min(dipler)), boyun)
    if len(H) >= 3:   # üçlü tepe
        (a, ha, _), (b, hb, _), (d, hd, _) = H[-3:]
        tepeler = (ha, hb, hd)
        if max(tepeler) / min(tepeler) - 1 <= ftol and b - a >= 6 and d - b >= 6 and i - d <= 40:
            boyun = float(Ll[a:d + 1].min())
            if 1 - boyun / min(tepeler) >= 0.02:
                durum = "kırıldı" if c < boyun <= cp else ("oluşuyor" if c >= boyun else None)
                if durum:
                    ekle("Üçlü tepe", -1, durum, [(a, ha, b, hb), (b, hb, d, hd), (a, boyun, i, boyun)], boyun - (max(tepeler) - boyun), boyun)
    if i >= 60:       # fincan-kulp
        bas = max(0, i - 120)
        jl = bas + int(np.argmax(Hh[bas:i - 30]))
        kenar_sol = float(Hh[jl])
        if i - 5 > jl + 10:
            jb = jl + int(np.argmin(Ll[jl:i - 5]))
            dip = float(Ll[jb])
            derinlik = kenar_sol - dip
            if derinlik >= 5 * atr and derinlik / kenar_sol <= 0.35 and jb - jl >= 10 and i - 3 > jb + 5:
                jr = jb + int(np.argmax(Hh[jb:i - 2]))
                kenar_sag = float(Hh[jr])
                kulp_dip = float(Ll[jr:i].min()) if i > jr else kenar_sag
                if (kenar_sag >= kenar_sol * 0.97 and jr - jb >= 0.5 * (jb - jl) and 3 <= i - jr <= 30
                        and kulp_dip >= dip + 0.6 * derinlik):
                    kenar = max(kenar_sol, kenar_sag)
                    durum = "kırıldı" if c > kenar >= cp else ("oluşuyor" if c <= kenar else None)
                    if durum:
                        ekle("Fincan-kulp", 1, durum, [(jl, kenar_sol, jb, dip), (jb, dip, jr, kenar_sag), (jr, kenar_sag, i, kulp_dip), (jl, kenar, i, kenar)],
                             kenar + derinlik, kenar)
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


# ---------- Piyasa rejimi ve üst zaman dilimi ----------
REJIM_ADI = {1: "Yükselen trend", -1: "Düşen trend", 0: "Yatay piyasa"}


def rejim_serisi(kapanis: pd.Series) -> pd.Series:
    """Günlük kapanışlardan piyasa rejimi: verimlilik oranı (son 10 gün net hareket / toplam hareket) yüksekse trend,
    düşükse yatay. Yön EMA20/EMA50'den. Bir gün kaydırılır (o gün bilinen bilgi)."""
    g = kapanis.dropna()
    er = (g - g.shift(10)).abs() / g.diff().abs().rolling(10).sum().replace(0, np.nan)
    e20, e50 = g.ewm(span=20, adjust=False).mean(), g.ewm(span=50, adjust=False).mean()
    r = np.where(er >= 0.3, np.sign(e20 - e50), 0)
    return pd.Series(r, index=g.index).shift(1).fillna(0)


def _gunluge(seri: pd.Series) -> pd.Series:
    idx = seri.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    return pd.Series(seri.values, index=pd.DatetimeIndex(idx).normalize())


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

    # Üst zaman dilimi trendi (sadece TAMAMLANMIŞ üst mumlar kullanılır)
    ust = np.zeros(len(df))
    ust_ad = {"1": "5 dk", "5": "15 dk", "g": "1 saatlik", "w": "Haftalık"}[mod]
    try:
        if mod != "w":
            kural = {"1": "5min", "5": "15min", "g": "60min"}[mod]
            uc = df["Close"].resample(kural, label="left", closed="left").last().dropna()
            ue20, ue50 = uc.ewm(span=20, adjust=False).mean(), uc.ewm(span=50, adjust=False).mean()
            utr = pd.Series(np.where((uc > ue20) & (ue20 > ue50), 1, np.where((uc < ue20) & (ue20 < ue50), -1, 0)), index=uc.index).shift(1)
            ust = utr.reindex(df.index, method="ffill").fillna(0).values
        else:
            c_, e50_, e100_ = df["Close"], df["Close"].ewm(span=50, adjust=False).mean(), df["Close"].ewm(span=100, adjust=False).mean()
            egim = e50_ - e50_.shift(10)
            ust = np.where((c_ > e100_) & (egim > 0), 1, np.where((c_ < e100_) & (egim < 0), -1, 0)).astype(float)
    except Exception:  # noqa: BLE001
        pass
    # Piyasa rejimi (BIST100 günlük kapanışlarından)
    rejim = np.zeros(len(df))
    try:
        if xu15 is not None and len(xu15) > 40:
            xg = xu15["Close"] if mod == "w" else xu15["Close"].resample("1D").last().dropna()
            rs_ = _gunluge(rejim_serisi(_gunluge(xg)))
            rejim = rs_.reindex(pd.to_datetime(pd.Series(np.array(df.index.date))), method="ffill").fillna(0).values
    except Exception:  # noqa: BLE001
        pass

    # Seviye toleransı: hissenin oynaklığına göre (sakin hissede dar, oynakta geniş)
    atr_oran = np.nanmedian(A["ATR"][max(0, n - 300):n] / A["Close"][max(0, n - 300):n]) if n > 20 else 0.01
    tol = float(np.clip(0.6 * atr_oran, 0.003, 0.02))

    # Günlük grafiğin ana tepe/dipleri (gün içi modlarda üst zaman dilimi seviyesi); sadece o güne kadar bilinenler
    gun_pv = []
    if mod != "w" and gunluk is not None and len(gunluk) > 40:
        g = gunluk.copy()
        g["ATR"] = (pd.concat([g["High"] - g["Low"], (g["High"] - g["Close"].shift()).abs(), (g["Low"] - g["Close"].shift()).abs()], axis=1)
                    .max(axis=1).ewm(alpha=1 / 14, adjust=False).mean())
        P0 = 3
        gp = pivot_bul(g, P0)
        gidx = g.index
        gun_pv = [(gidx[min(j + P0, len(gidx) - 1)].date(), j, f, t) for j, f, t in gp if j + P0 < len(gidx)]
    tarih_dizi = np.array(df.index.date)
    gun_onb = {}

    def gun_sev(i):
        if not gun_pv:
            return []
        t = tarih_dizi[i]
        if t not in gun_onb:
            bilinen = [(j, f, tp) for (onay, j, f, tp) in gun_pv if onay < t][-60:]
            out = []
            if bilinen:
                son_j = bilinen[-1][0] + 3
                for d in seviye_kumeleri(bilinen, son_j, max(tol, 0.006), "günlük", ufuk=120):
                    d = dict(d)
                    d["guc"] = round(min(1.0, d["guc"] + 0.1), 3)
                    d["son"] = 0
                    out.append(d)
            gun_onb[t] = [d for d in out if d["temas"] >= 2 or d["guc"] >= 0.55]
        return gun_onb[t]

    return dict(df=df, A=A, n=n, pv=pv, pv_j=[p[0] for p in pv], gun_no=gun_no, prof=prof,
                prof_guncel=prof_guncel, htf=htf, py=py, rs=rs, mod=mod, tol=tol, gun_sev=gun_sev,
                ust=ust, ust_ad=ust_ad, rejim=rejim)


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
OZ_ADI = ["Olay gücü", "Trend uyumu", "Günlük trend", "VWAP tarafı", "Alıcı/satıcı baskısı", "Göreli hacim", "Hacimli bölge",
          "CVD uyumsuzluğu", "MACD", "RSI konumu", "Sıkışmadan çıkış", "BIST100 yönü", "Endekse göre güç", "Risk/kazanç",
          "Ortalamadan uzaklık", "Önündeki engel mesafesi", "ADX trend gücü", "Mum formasyonu", "RSI uyumsuzluğu", "Seviye gücü",
          "Israrcı alıcı/satıcı", "Kırılım türü", "Üst zaman dilimi uyumu", "Piyasa rejimi uyumu"]


def puanla(ctx, i, yon, olay, sebepler, ref, hedef_ozel, stop_ozel, sev, prof, pv, ex=None) -> dict:
    ex = ex or {}
    A = ctx["A"]
    ad_ = ADAPT.get(ctx["mod"]) or ADAPT_VARSAYILAN
    c, atr = A["Close"][i], nanv(A["ATR"][i], A["Close"][i] * 0.01)
    puan, arti, eksi = olay, [], []
    yukari = yon > 0
    yonlu = lambda x: x * yon  # noqa: E731
    f = {}

    # Trend ve günlük trend
    ema50, ema200 = A["EMA50"][i], A["EMA200"][i]
    f["trend"] = 0
    if yonlu(ema50 - ema200) > 0 and yonlu(c - ema50) > 0:
        puan += 8; arti.append(DILIM_ADI[ctx["mod"]] + " trend " + ("yukarı" if yukari else "aşağı")); f["trend"] = 1
    elif yonlu(ema50 - ema200) < 0:
        puan -= 6; eksi.append(DILIM_ADI[ctx["mod"]] + " trende karşı"); f["trend"] = -1
    htf = ctx["htf"][i]
    if htf * yon > 0:
        puan += 10; arti.append("Günlük trend onaylıyor")
    elif htf * yon < 0:
        puan -= 14; eksi.append("Günlük trende karşı")

    # VWAP
    vw = A["VWAP"][i]
    f["vwap"] = 0
    if not np.isnan(vw):
        if yonlu(c - vw) > 0:
            puan += 7; arti.append("Fiyat VWAP'ın " + ("üstünde" if yukari else "altında")); f["vwap"] = 1
        else:
            puan -= 5; eksi.append("Fiyat VWAP'ın " + ("altında" if yukari else "üstünde")); f["vwap"] = -1

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
        puan -= int(ad_["hacim_ceza"]); eksi.append(f"Hacim zayıf ({sayi(rv, 1)}x)")

    # Hacimli bölge
    yogun = max(bolge_gucu(prof, ref), bolge_gucu(prof, c))
    hacimli_bolge = yogun >= 0.6
    if hacimli_bolge:
        puan += 8; arti.append("Yüksek hacimli fiyat bölgesi")

    # CVD uyumsuzluğu
    f["cvd"] = 0
    if i >= 40:
        C, cvd = A["Close"], A["CVD"]
        a1, a2 = slice(i - 40, i - 20), slice(i - 20, i + 1)
        if yukari and C[a2].min() < C[a1].min() and cvd[a2].min() > cvd[a1].min():
            puan += 8; arti.append("Gizli alım (CVD uyumsuzluğu)"); f["cvd"] = 1
        if not yukari and C[a2].max() > C[a1].max() and cvd[a2].max() < cvd[a1].max():
            puan += 8; arti.append("Gizli satış (CVD uyumsuzluğu)"); f["cvd"] = 1

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
    f["sikisma"] = 0
    bw1, bwmin = A["BBw"][i - 1], A["BBwMin"][i - 1]
    if not np.isnan(bw1) and not np.isnan(bwmin) and bw1 <= bwmin * 1.1:
        if (yukari and c > A["BBu"][i]) or (not yukari and c < A["BBa"][i]):
            puan += 5; arti.append("Sıkışmadan çıkış"); f["sikisma"] = 1

    # Piyasa ve göreli güç
    if ctx["py"][i] * yon > 0:
        puan += 4; arti.append("BIST100 aynı yönde")
    elif ctx["py"][i] * yon < 0:
        puan -= int(ad_["piyasa_ceza"]); eksi.append("BIST100 ters yönde")
    rs = ctx["rs"][i]
    if yonlu(rs) > 2:
        puan += 5; arti.append(f"Endeksten {'güçlü' if yukari else 'zayıf'} (%{'+' if rs >= 0 else '−'}{sayi(abs(rs), 1)})")
    elif yonlu(rs) < -2:
        puan -= 5; eksi.append(f"Endeksten {'zayıf' if yukari else 'güçlü'} (%{'+' if rs >= 0 else '−'}{sayi(abs(rs), 1)})")

    guclu = hacimli_bolge and rv >= 1.5 and yonlu(ab) > 0.2
    if guclu:
        puan += 10

    # ADX: trend gücü
    adx = nanv(A["ADX"][i], 20)
    trend_yon = 1 if nanv(A["PDI"][i]) >= nanv(A["NDI"][i]) else -1
    kirilim = ex.get("kirilim", True)
    if kirilim:
        if adx >= 25 and trend_yon == yon:
            puan += 6; arti.append(f"Güçlü trend (ADX {adx:.0f})")
        elif adx < 18:
            puan -= 4; eksi.append(f"Trend zayıf (ADX {adx:.0f}), kırılım sönebilir")
    elif adx >= 35 and trend_yon == -yon:
        puan -= 10; eksi.append(f"Güçlü trende karşı dönüş denemesi (ADX {adx:.0f})")

    # Çoklu zaman onayı: bir üst zaman diliminin trendi
    ust_ = int(ctx["ust"][i]) if "ust" in ctx else 0
    if ust_ * yon > 0:
        puan += 6; arti.append(f"{ctx['ust_ad']} grafik de aynı yönde")
    elif ust_ * yon < 0:
        puan -= 10; eksi.append(f"{ctx['ust_ad']} grafiğin trendine karşı")
    # Piyasa rejimi: trend gününde kırılım, yatay günde dönüş sinyalleri daha iyi çalışır
    rj = int(ctx["rejim"][i]) if "rejim" in ctx else 0
    rejim_uyum = 0
    if rj != 0:
        if kirilim and rj * yon > 0:
            puan += 5; arti.append("Piyasa trendde, kırılım sinyali uygun"); rejim_uyum = 1
        elif rj * yon < 0:
            puan -= 6; eksi.append("Piyasa (BIST100) ters yönde trendde"); rejim_uyum = -1
    else:
        if not kirilim:
            puan += 5; arti.append("Piyasa yatay, dönüş sinyali uygun"); rejim_uyum = 1
        else:
            puan -= 5; eksi.append("Piyasa yatay; kırılımlar sık sönüyor"); rejim_uyum = -1

    # Kovalama: fiyat ortalamadan çok uzaklaşmışsa girmek risklidir
    uzak = yonlu(c - nanv(A["EMA20"][i], c)) / atr
    if uzak > 2.8:
        puan -= 14; eksi.append(f"Fiyat ortalamadan çok uzak ({sayi(uzak, 1)} ATR) — kovalama riski")
    elif uzak > 2:
        puan -= 6; eksi.append(f"Fiyat ortalamadan uzaklaşmış ({sayi(uzak, 1)} ATR)")

    # Mum formasyonu ve RSI uyumsuzluğu
    mum_skor = 0
    for ad, y, g in ex.get("mum", []):
        if y == yon:
            puan += g; mum_skor += g; arti.append(f"Mum: {ad}")
        elif y == -yon and g:
            puan -= int(g * 0.8); mum_skor -= g; eksi.append(f"Ters mum: {ad}")
    uyum = ex.get("uyum", 0)
    if uyum == yon:
        puan += 10; arti.append("RSI " + ("pozitif" if yukari else "negatif") + " uyumsuzluk")
    elif uyum == -yon:
        puan -= 8; eksi.append("RSI " + ("negatif" if yukari else "pozitif") + " uyumsuzluk (ters)")

    # Seviyenin gücü
    ref_guc = ex.get("ref_guc", 0.5)
    if ref_guc >= 0.75:
        puan += 6; arti.append(f"Güçlü seviye ({ex.get('ref_aciklama', '')})")
    elif ref_guc < 0.35:
        puan -= 6; eksi.append("Zayıf seviye")

    # Stop ve hedefler: güçlü seviyelere göre
    sev_d = ex.get("sev_d") or [dict(p=x, guc=0.5) for x in sev]
    guclu_sev = sorted({round(d["p"], 4) for d in sev_d if d["guc"] >= 0.45})
    dipler = [p[1] for p in pv[-12:] if p[2] == "L" and p[1] < c]
    tepeler = [p[1] for p in pv[-12:] if p[2] == "H" and p[1] > c]
    tum_sev = sorted(set(guclu_sev + ([prof["poc"], prof["vah"], prof["val"]] + prof["hvn"] if prof else [])))
    if yukari:
        aday = ref - 0.5 * atr
        if dipler:
            aday = min(aday, max(dipler) - 0.2 * atr)
        stop = stop_ozel if stop_ozel else max(aday, c - 3 * atr)
        if stop >= c - 0.4 * atr:
            stop = c - 1.2 * atr
        stop -= ad_["stop_ek"] * atr                      # hatalardan öğrenilen ek stop payı
        R = c - stop
        ustler = [x for x in tum_sev if x > c + 1.5 * R]
        hedef = ustler[0] if ustler else c + 2 * R
        if hedef_ozel and hedef_ozel > c + 1.5 * R:
            hedef = min(hedef, hedef_ozel) if ustler else hedef_ozel
        sonra = [x for x in tum_sev if x > hedef * 1.003]
        hedef2 = sonra[0] if sonra else hedef + R
        engel = next((d["p"] for d in sorted(sev_d, key=lambda d: d["p"]) if d["guc"] >= 0.5 and c + 0.3 * atr < d["p"] < hedef), None)
    else:
        aday = ref + 0.5 * atr
        if tepeler:
            aday = max(aday, min(tepeler) + 0.2 * atr)
        stop = stop_ozel if stop_ozel else min(aday, c + 3 * atr)
        if stop <= c + 0.4 * atr:
            stop = c + 1.2 * atr
        stop += ad_["stop_ek"] * atr
        R = stop - c
        altlar = [x for x in tum_sev if x < c - 1.5 * R]
        hedef = altlar[-1] if altlar else c - 2 * R
        if hedef_ozel and hedef_ozel < c - 1.5 * R:
            hedef = max(hedef, hedef_ozel) if altlar else hedef_ozel
        sonra = [x for x in tum_sev if x < hedef * 0.997]
        hedef2 = sonra[-1] if sonra else hedef - R
        engel = next((d["p"] for d in sorted(sev_d, key=lambda d: -d["p"]) if d["guc"] >= 0.5 and hedef < d["p"] < c - 0.3 * atr), None)
    engel_oran = 3.0
    if engel is not None and R > 0:
        engel_oran = abs(engel - c) / R
        if engel_oran < ad_["engel_esik"]:
            puan -= 14; eksi.append(f"Hemen {'üstte güçlü direnç' if yukari else 'altta güçlü destek'} ({sayi(engel)}) — yer dar")
        elif engel_oran < 1.5:
            puan -= 5; eksi.append(f"Yakında {'direnç' if yukari else 'destek'} var ({sayi(engel)})")
    rk = abs(hedef - c) / R if R > 0 else 0
    if rk >= 2.5:
        puan += 5; arti.append(f"Risk/kazanç {sayi(rk, 1)}")
    elif rk < 1.5:
        puan -= 8; eksi.append(f"Risk/kazanç düşük ({sayi(rk, 1)})")

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

    oz = [round(float(v), 4) for v in (
        olay / 40, f["trend"], htf * yon, f["vwap"], ab * yon, min(rv, 4) / 4, int(hacimli_bolge), f["cvd"],
        np.sign(mh) * yon, (r - 50) / 50 * yon, f["sikisma"], ctx["py"][i] * yon, float(np.clip(rs * yon, -10, 10)) / 10,
        min(rk, 5) / 5, float(np.clip(uzak, -4, 6)) / 4, min(engel_oran, 3) / 3, adx / 50 * (1 if trend_yon == yon else -1),
        float(np.clip(mum_skor, -10, 10)) / 10, uyum * yon, ref_guc, int(guclu), int(kirilim), ust_ * yon, rejim_uyum)]
    guven = int(round(100 / (1 + np.exp(-(puan - 58) / 11))))
    return dict(tur="AL" if yukari else "SAT", yon=yon, guven=guven, guclu=bool(guclu),
                sebepler=sebepler, arti=arti, eksi=eksi, fiyat=float(c), stop=float(stop),
                hedef=float(hedef), hedef2=float(hedef2), hedef3=float(hedef3), rk=float(rk),
                giris_alt=float(giris_alt), giris_ust=float(giris_ust), oz=oz, ref=float(ref),
                engel=float(engel) if engel is not None else None, mtf=ust_ * yon, htf_yon=int(htf * yon), rejim=rj)


def sinyal_bul(ctx, i):
    """i. mum kapanışında sinyal var mı? Sadece i'ye kadarki veri kullanılır.
    Sinyal sadece GÜÇLÜ seviyelerde, onaylı kırılım ya da onay mumlu dönüşte üretilir."""
    A = ctx["A"]
    pv = ctx["pv"][:bisect.bisect_right(ctx["pv_j"], i - PIVOT_PENCERE - 1)]
    if len(pv) < 4:
        return None, []
    sev_d = seviye_listesi(ctx, i, pv)
    sev = [d["p"] for d in sev_d]
    prof = ctx["prof"].get(ctx["gun_no"][i])
    c, o, h, l, cp = A["Close"][i], A["Open"][i], A["High"][i], A["Low"][i], A["Close"][i - 1]
    atr = nanv(A["ATR"][i], c * 0.01)
    rv = nanv(A["RVOL"][i])
    tol = ctx["tol"]
    yesil, kirmizi = c > o, c < o
    aralik = max(h - l, 1e-9)
    govde_orani = abs(c - o) / aralik
    mum = mum_formasyon(A, i)
    mum_al = any(y > 0 for _, y, _ in mum)
    mum_sat = any(y < 0 for _, y, _ in mum)
    olaylar = {}
    ad_ = ADAPT.get(ctx["mod"]) or ADAPT_VARSAYILAN
    kmin, krv = ad_["kirilim_min"], ad_["kirilim_rv"]

    def olay(anahtar, yon, puan, metin, seviye, hedef=None, stop=None, guc=0.5, aciklama="", kirilim=True):
        eski = olaylar.get(anahtar)
        if eski is None or abs(seviye - c) < abs(eski[3] - c):
            olaylar[anahtar] = (yon, puan, metin, seviye, hedef, stop, anahtar, guc, aciklama, kirilim)

    for d in sev_d:
        lo_, hi_, g = d["lo"], d["hi"], d["guc"]
        if g < 0.4:
            continue
        ac = f"{d['temas']} test" + (", rol değişimi" if d.get("rol") else "") + (f" · {d['kaynak']}" if d["kaynak"] != "tepe-dip" else "")
        bolge = f"{sayi(lo_)}–{sayi(hi_)}"
        k = int(round((0.6 + 0.6 * g) * 22))
        # Kırılım: kapanış bölgenin belirgin dışında, gövdesi dolu, hacimli
        if cp <= hi_ and c > hi_ and c - hi_ >= kmin * atr and yesil and govde_orani >= 0.45 and rv >= krv:
            olay("dk", 1, k, f"Direnç bölgesi yukarı kırıldı ({bolge}, {d['temas']} test)", hi_, guc=g, aciklama=ac)
        elif cp >= lo_ and c < lo_ and lo_ - c >= kmin * atr and kirmizi and govde_orani >= 0.45 and rv >= krv:
            olay("dsk", -1, k, f"Destek bölgesi aşağı kırıldı ({bolge}, {d['temas']} test)", lo_, guc=g, aciklama=ac)
        # Dönüş: bölgeye fitille girip dışında kapanan, onay mumu ya da hacmi olan mum
        elif l <= hi_ and c > hi_ and cp >= lo_ and yesil and c >= l + 0.6 * aralik and (mum_al or rv >= 1.3):
            olay("dd", 1, int(round((0.6 + 0.6 * g) * 18)), f"Destek bölgesinden dönüş ({bolge}, {d['temas']} test)", lo_, guc=g, aciklama=ac, kirilim=False)
        elif h >= lo_ and c < lo_ and cp <= hi_ and kirmizi and c <= h - 0.6 * aralik and (mum_sat or rv >= 1.3):
            olay("rd", -1, int(round((0.6 + 0.6 * g) * 18)), f"Direnç bölgesinden dönüş ({bolge}, {d['temas']} test)", hi_, guc=g, aciklama=ac, kirilim=False)

    # Stop avı (likidite süpürme)
    son_dipler = [p for p in pv if p[2] == "L" and p[0] >= i - 60]
    son_tepeler = [p for p in pv if p[2] == "H" and p[0] >= i - 60]
    for p in son_dipler[-3:]:
        if l < p[1] * 0.9995 and c > p[1] and (min(o, c) - l) >= 0.5 * aralik and rv >= 1.2:
            olay("sweep", 1, 26, f"Stop avı + dönüş ({sayi(p[1])} altı süpürüldü)", p[1], stop=l - 0.3 * atr, guc=0.6, aciklama="önceki dip", kirilim=False)
    for p in son_tepeler[-3:]:
        if h > p[1] * 1.0005 and c < p[1] and (h - max(o, c)) >= 0.5 * aralik and rv >= 1.2:
            olay("sweep", -1, 26, f"Stop avı + dönüş ({sayi(p[1])} üstü süpürüldü)", p[1], stop=h + 0.3 * atr, guc=0.6, aciklama="önceki tepe", kirilim=False)

    # Emilim
    if rv >= 1.8 and (h - l) <= 0.7 * atr:
        for d in sev_d:
            L_ = d["p"]
            if d["guc"] < 0.4:
                continue
            if abs(l - L_) / L_ <= tol and c >= l + 0.5 * aralik:
                olay("emilim", 1, 20, f"Emilim: {sayi(L_)} desteğinde satışlar karşılandı", L_, guc=d["guc"], kirilim=False)
            if abs(h - L_) / L_ <= tol and c <= h - 0.5 * aralik:
                olay("emilim", -1, 20, f"Emilim: {sayi(L_)} direncinde alımlar karşılandı", L_, guc=d["guc"], kirilim=False)

    # Piyasa yapısı: BOS / CHoCH
    yapi, sH, sL = yapi_bul(pv)
    if sH and cp <= sH[-1][1] < c and yesil and rv >= 1.0 and govde_orani >= 0.4:
        if yapi == 1:
            olay("yapi", 1, 18, f"Yapı kırılımı / BOS ({sayi(sH[-1][1])})", sH[-1][1], guc=0.55, aciklama="son tepe")
        elif yapi == -1:
            olay("yapi", 1, 22, f"Trend dönüşü / CHoCH ({sayi(sH[-1][1])})", sH[-1][1], guc=0.6, aciklama="son tepe")
    if sL and cp >= sL[-1][1] > c and kirmizi and rv >= 1.0 and govde_orani >= 0.4:
        if yapi == -1:
            olay("yapi", -1, 18, f"Yapı kırılımı / BOS ({sayi(sL[-1][1])})", sL[-1][1], guc=0.55, aciklama="son dip")
        elif yapi == 1:
            olay("yapi", -1, 22, f"Trend dönüşü / CHoCH ({sayi(sL[-1][1])})", sL[-1][1], guc=0.6, aciklama="son dip")

    # RSI uyumsuzluğu + onay mumu = dönüş olayı
    uyum = uyumsuzluk(A, pv, i)
    if uyum > 0 and yesil and c > A["High"][i - 1] and (mum_al or rv >= 1.2):
        olay("uyum", 1, 18, "Pozitif RSI uyumsuzluğu + onay mumu", l, guc=0.55, kirilim=False)
    if uyum < 0 and kirmizi and c < A["Low"][i - 1] and (mum_sat or rv >= 1.2):
        olay("uyum", -1, 18, "Negatif RSI uyumsuzluğu + onay mumu", h, guc=0.55, kirilim=False)

    formlar = formasyonlar(A, pv, i)
    for f in formlar:
        if f["durum"] == "kırıldı" and f["yon"] != 0 and rv >= 1.0:
            yon_adi = "yukarı" if f["yon"] > 0 else "aşağı"
            olay("f-" + f["ad"], f["yon"], 26, f"{f['ad']} {yon_adi} kırılımı", f["ref"], f["hedef"], guc=0.65, aciklama="formasyon")

    en_iyi = None
    for yon in (1, -1):
        grup = sorted([v for v in olaylar.values() if v[0] == yon], key=lambda v: -v[1])
        if not grup:
            continue
        toplam = min(sum(v[1] for v in grup), 40)
        hedef_ozel = next((v[4] for v in grup if v[4]), None)
        stop_ozel = next((v[5] for v in grup if v[5]), None)
        ex = dict(mum=mum, uyum=uyum, ref_guc=grup[0][7], ref_aciklama=grup[0][8], kirilim=grup[0][9], sev_d=sev_d)
        s = puanla(ctx, i, yon, toplam, [v[2] for v in grup], grup[0][3], hedef_ozel, stop_ozel, sev, prof, pv, ex)
        anahtar = grup[0][6]
        s["kurulum"] = anahtar
        s["guven"] = model_uygula(ctx["mod"], s)
        ag = AGIRLIK.get(ctx["mod"], {}).get(anahtar)
        if ag and ag["bonus"]:
            s["guven"] = int(max(0, min(100, s["guven"] + ag["bonus"])))
            (s["arti"] if ag["bonus"] > 0 else s["eksi"]).append(f"Karne: bu kurulum BIST'te %{ag['isabet']:.0f} isabetli")
        if en_iyi is None or s["guven"] > en_iyi["guven"]:
            en_iyi = s
    return en_iyi, formlar


# ---------- Hatalardan öğrenme: tutmayan sinyallerin nedenine göre kuralları kendiliğinden sıkılaştırır ----------
ADAPT_VARSAYILAN = dict(stop_ek=0.0, kirilim_min=0.15, kirilim_rv=1.1, piyasa_ceza=8, engel_esik=1.2, hacim_ceza=10)
ADAPT = {m: dict(ADAPT_VARSAYILAN, notlar=[], dagilim=[], n=0) for m in ("1", "5", "g", "w")}
NEDEN_ADI = {"av": "Stop avlandı, sonra hedefe gitti (stop dar)", "sahte": "Sahte kırılım (fiyat seviyenin gerisine döndü)",
             "engel": "Önündeki güçlü seviyeden döndü", "piyasa": "Piyasa (BIST100) ters döndü",
             "hacim": "Hacim devam etmedi, fiyat hiç ilerlemedi", "gap": "Boşlukla (gap) stop oldu", "gurultu": "Normal dalgalanma"}
KIRILIM_KURULUM = ("dk", "dsk", "yapi")


def otopsi(ctx: dict, s: dict, n: int) -> str:
    """Stop olan sinyalin neden tutmadığını bulur."""
    A, i, yon, j = ctx["A"], s["i"], s["yon"], s.get("_j", s["i"] + 1)
    f, stop, hedef = s["fiyat"], s["stop"], s["hedef"]
    R = abs(f - stop) or 1e-9
    if (yon > 0 and A["Open"][j] < stop) or (yon < 0 and A["Open"][j] > stop):
        return "gap"
    son = min(j + 1 + TEST_UFKU, n)
    if son > j + 1 and ((yon > 0 and A["High"][j + 1:son].max() >= hedef) or (yon < 0 and A["Low"][j + 1:son].min() <= hedef)):
        return "av"
    ref = s.get("ref")
    kirilim = s.get("kurulum", "") in KIRILIM_KURULUM or s.get("kurulum", "").startswith("f-")
    if kirilim and ref and any((A["Close"][k] - ref) * yon < 0 for k in range(i + 1, min(i + 4, j + 1))):
        return "sahte"
    en_iyi = A["High"][i + 1:j + 1].max() if yon > 0 else A["Low"][i + 1:j + 1].min()
    engel = s.get("engel")
    if engel and abs(en_iyi - engel) / engel <= ctx["tol"] * 1.5:
        return "engel"
    if ctx["py"][i] * yon >= 0 and ctx["py"][j] * yon < 0:
        return "piyasa"
    if (en_iyi - f) * yon < 0.3 * R and np.nanmean(A["RVOL"][i + 1:j + 1]) < 1.0:
        return "hacim"
    return "gurultu"


def hatalardan_ogren(sinyaller: list[dict], mod: str):
    """Tutmayan sinyallerin nedenlerini sayar; sık görülen hataya göre ilgili kuralı sıkılaştırır (yumuşak geçişle)."""
    stoplar = [s for s in sinyaller if s["sonuc"] == "stop" and s.get("neden")]
    eski = ADAPT.get(mod) or dict(ADAPT_VARSAYILAN)
    if len(stoplar) < 30:
        ADAPT[mod] = dict(eski, n=len(stoplar), notlar=["Henüz yeterli hata örneği yok (en az 30 stop gerekli)."], dagilim=[])
        return
    say = {}
    for s in stoplar:
        say[s["neden"]] = say.get(s["neden"], 0) + 1
    pay = {k: v / len(stoplar) for k, v in say.items()}
    hedef = dict(ADAPT_VARSAYILAN)
    notlar = []
    if pay.get("av", 0) > 0.25:
        hedef["stop_ek"] = min(0.8, (pay["av"] - 0.15) * 2)
    if pay.get("sahte", 0) > 0.25:
        hedef["kirilim_min"] = 0.15 + min(0.3, pay["sahte"] - 0.15)
        hedef["kirilim_rv"] = 1.3
    if pay.get("piyasa", 0) > 0.2:
        hedef["piyasa_ceza"] = 16
    if pay.get("engel", 0) > 0.2:
        hedef["engel_esik"] = 1.6
    if pay.get("hacim", 0) > 0.25:
        hedef["hacim_ceza"] = 18
    yeni = {k: round(0.5 * eski.get(k, v) + 0.5 * hedef[k], 3) for k, v in ADAPT_VARSAYILAN.items()}   # ani sıçrama yok
    yuz = lambda k: f"%{pay.get(k, 0) * 100:.0f}"  # noqa: E731
    if yeni["stop_ek"] >= 0.05:
        notlar.append(f"Stop avı payı {yuz('av')}: stop olup sonra hedefe giden çok → stoplar {sayi(yeni['stop_ek'], 2)} ATR geriye alındı.")
    if yeni["kirilim_min"] > 0.17:
        notlar.append(f"Sahte kırılım payı {yuz('sahte')} → kırılım için kapanış en az {sayi(yeni['kirilim_min'], 2)} ATR ötede ve hacim {sayi(yeni['kirilim_rv'], 1)}x şartı.")
    if yeni["piyasa_ceza"] > 9:
        notlar.append(f"Piyasa dönüşü payı {yuz('piyasa')} → BIST100 ters yöndeyken ceza {yeni['piyasa_ceza']:.0f} puana çıkarıldı.")
    if yeni["engel_esik"] > 1.25:
        notlar.append(f"Önündeki seviyeden dönüş payı {yuz('engel')} → hedefe kadar en az {sayi(yeni['engel_esik'], 1)}R boş alan aranıyor.")
    if yeni["hacim_ceza"] > 11:
        notlar.append(f"Hacimsiz sinyal payı {yuz('hacim')} → zayıf hacme ceza {yeni['hacim_ceza']:.0f} puana çıkarıldı.")
    if not notlar:
        notlar.append("Hatalar dağınık, belirgin bir zayıf nokta yok; kurallar aynen korunuyor.")
    yeni.update(n=len(stoplar), notlar=notlar,
                dagilim=[[NEDEN_ADI[k], round(v * 100)] for k, v in sorted(pay.items(), key=lambda x: -x[1])])
    ADAPT[mod] = yeni


# ---------- Öğrenen model: geçmiş sinyallerden hangi koşulların işe yaradığını öğrenir ----------
MODEL = {"1": None, "5": None, "g": None, "w": None}


def _sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))


def _lojistik(X, y, l2=0.02, adim=500, oran=0.3):
    w, b = np.zeros(X.shape[1]), 0.0
    for _ in range(adim):
        p = _sigmoid(X @ w + b)
        hata = p - y
        w -= oran * (X.T @ hata / len(y) + l2 * w)
        b -= oran * hata.mean()
    return w, b


def _auc(y, p):
    sira = np.argsort(np.argsort(p)) + 1
    poz = y == 1
    n1, n0 = poz.sum(), (~poz).sum()
    if n1 == 0 or n0 == 0:
        return 0.5
    return float((sira[poz].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def model_egit(sinyaller: list[dict]) -> dict | None:
    """Bitmiş sinyallerden lojistik model eğitir. Zamana göre son %25'lik dilimde test eder;
    tahmin gücü (AUC) yetersizse model kullanılmaz."""
    veri = sorted([s for s in sinyaller if s["sonuc"] != "açık" and s.get("oz") and len(s["oz"]) == len(OZ_ADI)],
                  key=lambda s: pd.Timestamp(s["zaman"]).value)
    if len(veri) < 200:
        return dict(aktif=False, n=len(veri), auc=None, neden="yetersiz örnek (en az 200 bitmiş sinyal)")
    X = np.array([s["oz"] for s in veri], dtype=float)
    y = np.array([1.0 if s["sonuc"] == "hedef" or (s["sonuc"] == "süre doldu" and s["getiri"] > 0) else 0.0 for s in veri])
    k = int(len(y) * 0.75)
    mu, sd = X[:k].mean(0), X[:k].std(0) + 1e-6
    w, b = _lojistik((X[:k] - mu) / sd, y[:k])
    yt = y[k:]
    if min(yt.sum(), len(yt) - yt.sum()) < 30:
        return dict(aktif=False, n=len(veri), auc=None, neden="test dönemi için yeterli örnek yok")
    auc = _auc(yt, _sigmoid(((X[k:] - mu) / sd) @ w + b))
    mu, sd = X.mean(0), X.std(0) + 1e-6
    w, b = _lojistik((X - mu) / sd, y)
    p = _sigmoid(((X - mu) / sd) @ w + b)
    aktif = auc >= 0.54
    onemli = sorted(zip(OZ_ADI, w.tolist()), key=lambda x: -abs(x[1]))[:6]
    return dict(aktif=aktif, n=len(y), auc=round(auc, 3), oran=round(float(y.mean()) * 100, 1), mu=mu, sd=sd, w=w, b=b,
                dagilim=np.sort(p), onemli=[[a, round(v, 2)] for a, v in onemli],
                neden=None if aktif else "tahmin gücü düşük, kural puanı kullanılıyor")


def model_uygula(mod: str, s: dict) -> int:
    m = MODEL.get(mod)
    if not m or not m.get("aktif") or not s.get("oz"):
        return s["guven"]
    p = float(_sigmoid(((np.array(s["oz"]) - m["mu"]) / m["sd"]) @ m["w"] + m["b"]))
    yuzdelik = float(np.searchsorted(m["dagilim"], p)) / len(m["dagilim"]) * 100
    guven = int(round(0.5 * s["guven"] + 0.5 * yuzdelik))
    metin = f"Öğrenen model: benzer kurulumların %{p * 100:.0f}'i hedefe ulaştı (ortalama %{m['oran']:.0f})"
    (s["arti"] if p * 100 >= m["oran"] else s["eksi"]).append(metin)
    s["olasilik"] = round(p * 100, 1)
    return max(0, min(100, guven))


def sonuc_hesapla(A, s, n):
    i, yon, f = s["i"], s["yon"], s["fiyat"]
    for j in range(i + 1, min(i + 1 + TEST_UFKU, n)):
        if yon > 0:
            if A["Low"][j] <= s["stop"]:
                s["_j"] = j
                return "stop", s["stop"] / f - 1
            if A["High"][j] >= s["hedef"]:
                return "hedef", s["hedef"] / f - 1
        else:
            if A["High"][j] >= s["stop"]:
                s["_j"] = j
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
            if s["sonuc"] == "stop":
                try:
                    s["neden"] = otopsi(ctx, s, n)
                except Exception:  # noqa: BLE001
                    s["neden"] = "gurultu"
            out.append(s)
    return out


# ---------- Bot yorumu ----------
def _sec(secenek: list[str], tohum: int) -> str:
    return secenek[tohum % len(secenek)]


def _zaman_yaz(df, j: int, mod: str) -> str:
    t = df.index[j]
    if mod == "w":
        return f"{t:%d.%m}"
    return f"{t:%H:%M}" if t.date() == df.index[-1].date() else f"{t:%d.%m %H:%M}"


def bot_yorumu(ctx, sev_d, formlar, gunluk=None, sym="") -> tuple[list[str], dict]:
    """Hissenin o anki durumunu gerçek verilerle anlatan cümleler. En dikkat çekici olgular öne alınır;
    her hisse ve gün için farklı ifade kalıpları seçilir."""
    A, n, df, mod = ctx["A"], ctx["n"], ctx["df"], ctx["mod"]
    i = n - 1
    c, o = float(df["Close"].iloc[-1]), float(A["Open"][i])     # anlatımda ekrandaki son fiyat kullanılır
    atr = nanv(A["ATR"][i], c * 0.01)
    tohum = sum(ord(x) for x in sym) + int(df.index[-1].day)
    dil = DILIM_ADI[mod]
    olg = []                                             # (önem, cümle)

    # Günün hareketi ve fiyatın gün içi konumu
    if mod != "w":
        dfi = df
        gun_ = dfi.index[-1].date()
        bugun = dfi[dfi.index.date == gun_]
        onceki = dfi[dfi.index.date < gun_]["Close"]
        if len(bugun) and len(onceki):
            dk, gy, gd, ac = float(onceki.iloc[-1]), float(bugun["High"].max()), float(bugun["Low"].min()), float(bugun["Open"].iloc[0])
            deg, gap = (c / dk - 1) * 100, (ac / dk - 1) * 100
            konum = (c - gd) / (gy - gd) if gy > gd else 0.5
            yer = "en yükseğine yakın" if konum >= 0.8 else "en düşüğüne yakın" if konum <= 0.2 else "aralığın ortasında"
            olg.append((abs(deg) * 1.5 + 2, _sec([
                f"Gün içi aralık {sayi(gd)}–{sayi(gy)}; fiyat {sayi(c)} ile günün {yer} (dünkü kapanışa göre {'+' if deg >= 0 else '−'}%{sayi(abs(deg), 1)}).",
                f"Bugün {sayi(dk)} kapanışına göre {'+' if deg >= 0 else '−'}%{sayi(abs(deg), 1)}; gün içinde {sayi(gd)} ile {sayi(gy)} arasında gidip geldi, şu an {yer}.",
            ], tohum)))
            if abs(gap) >= 1:
                olg.append((abs(gap) * 2, f"Güne {'+' if gap >= 0 else '−'}%{sayi(abs(gap), 1)} boşlukla ({'yukarı' if gap > 0 else 'aşağı'} gap) {sayi(ac)}'dan açtı"
                                          + (", boşluk henüz kapanmadı." if (gap > 0 and gd > dk) or (gap < 0 and gy < dk) else ", boşluk gün içinde kapandı.")))
    else:
        C = A["Close"]
        if i >= 20:
            h5, h20 = (c / C[i - 5] - 1) * 100, (c / C[i - 20] - 1) * 100
            olg.append((abs(h20) / 2 + 2, f"Son 5 günde {'+' if h5 >= 0 else '−'}%{sayi(abs(h5), 1)}, son 20 günde {'+' if h20 >= 0 else '−'}%{sayi(abs(h20), 1)}."))

    # 52 hafta zirve/dip (günlük veriden)
    if gunluk is not None and len(gunluk) > 120:
        yy, yd = float(gunluk["High"].tail(250).max()), float(gunluk["Low"].tail(250).min())
        uz_y, uz_d = (yy / c - 1) * 100, (c / yd - 1) * 100
        if uz_y <= 3:
            olg.append((9 - uz_y, f"52 haftanın zirvesine ({sayi(yy)}) sadece %{sayi(uz_y, 1)} uzaklıkta; zirve bölgelerinde kâr satışı da kırılım da sert olur."))
        elif uz_d <= 5:
            olg.append((8 - uz_d, f"52 haftanın dibine ({sayi(yd)}) %{sayi(uz_d, 1)} yakın; burası uzun vadeli alıcıların izlediği bölge."))

    # Trend ve yapı
    htf = int(ctx["htf"][i])
    yapi, _, _ = yapi_bul(ctx["pv"])
    e20, e50 = nanv(A["EMA20"][i], c), nanv(A["EMA50"][i], c)
    tr_m = {1: "yukarı", -1: "aşağı", 0: "kararsız"}
    yp_m = {1: "yükselen tepe ve dipler", -1: "alçalan tepe ve dipler", 0: "belirgin bir yön olmadan"}
    if mod != "w":
        olg.append((3, _sec([f"Günlük trend {tr_m[htf]}; {dil} grafikte {yp_m[yapi]} var.",
                             f"{dil} grafikte {yp_m[yapi]} görülüyor, üst zaman dilimi (günlük) {tr_m[htf]}."], tohum + 1)))
    else:
        olg.append((3, f"Günlük grafikte {yp_m[yapi]}; fiyat 50 günlük ortalamanın %{sayi(abs(c / e50 - 1) * 100, 1)} {'üstünde' if c > e50 else 'altında'}."))
    # Ortalama kesişimi (yakın zamanda)
    E20, E50 = A["EMA20"], A["EMA50"]
    for k in range(1, min(30, i)):
        if (E20[i - k] - E50[i - k]) * (E20[i - k + 1] - E50[i - k + 1]) < 0:
            yukari = E20[i - k + 1] > E50[i - k + 1]
            olg.append((7 - k * 0.2, f"20'lik ortalama {k} {'gün' if mod == 'w' else 'mum'} önce 50'liği {'yukarı' if yukari else 'aşağı'} kesti ({'olumlu' if yukari else 'olumsuz'} kesişim)."))
            break
    # MACD kesişimi
    Mh = A["MACDh"]
    for k in range(0, min(15, i)):
        if nanv(Mh[i - k]) * nanv(Mh[i - k - 1]) < 0:
            yk = nanv(Mh[i - k]) > 0
            olg.append((6 - k * 0.3, f"MACD {('bu mumda' if k == 0 else f'{k} mum önce')} sinyal çizgisini {'yukarı' if yk else 'aşağı'} kesti; momentum {'güçleniyor' if yk else 'zayıflıyor'}."))
            break
    # RSI
    r, r3 = nanv(A["RSI"][i], 50), nanv(A["RSI"][i - 3], 50)
    if r >= 70 or r <= 30:
        olg.append((7, f"RSI {r:.0f} ile {'aşırı alım' if r >= 70 else 'aşırı satım'} bölgesinde; {'yeni alım için geç, kâr satışı gelebilir' if r >= 70 else 'satış yorulmuş olabilir, tepki alımı gelebilir'}."))
    elif abs(r - r3) >= 8:
        olg.append((4, f"RSI son 3 mumda {r3:.0f}'dan {r:.0f}'a {'çıktı' if r > r3 else 'indi'}."))
    # Mum serisi ve mum formasyonu
    seri = 0
    yesil = c >= o
    for k in range(i, max(i - 12, 0), -1):
        if (A["Close"][k] >= A["Open"][k]) == yesil:
            seri += 1
        else:
            break
    if seri >= 4:
        olg.append((seri, f"Art arda {seri} {'yeşil' if yesil else 'kırmızı'} mum; {'alıcılar acele ediyor ama uzayan seriler genelde dinlenmeyle biter' if yesil else 'satış baskısı sürüyor, tepki için bir dönüş mumu beklenmeli'}."))
    mm = mum_formasyon(A, i)
    if mm:
        olg.append((6, "Son mum: " + ", ".join(m_[0] for m_ in mm) + "."))
    # Hacim
    v, v20 = float(A["Volume"][i]), float(np.nanmean(A["Volume"][max(0, i - 20):i])) if i > 1 else 0
    rv, ab = nanv(A["RVOL"][i]), nanv(A["AB"][i])
    if v20 > 0 and v / v20 >= 1.8:
        olg.append((5 + v / v20, f"Son mumun hacmi 20 mumluk ortalamanın {sayi(v / v20, 1)} katı; {'alıcı' if yesil else 'satıcı'} tarafta belirgin bir istek var."))
    elif rv < 0.6:
        olg.append((3, f"Hacim bu saat için normalin ancak %{rv * 100:.0f}'i kadar; sessiz piyasada kırılımlara temkinli yaklaş."))
    if abs(ab) >= 0.2:
        olg.append((4 + abs(ab) * 5, f"Son 20 mumun hacminin %{abs(ab) * 100:.0f} kadarı {'alıcı' if ab > 0 else 'satıcı'} yönlü işlemlerden geldi."))
    # VWAP
    vw = A["VWAP"][i]
    if not np.isnan(vw):
        f_ = (c / vw - 1) * 100
        olg.append((abs(f_) * 2 + 1, _sec([
            f"Gün içi ortalama maliyet (VWAP) {sayi(vw)}; fiyat bunun %{sayi(abs(f_), 1)} {'üstünde, bugün alanlar kârda' if f_ > 0 else 'altında, bugün alanlar zararda'}.",
            f"Fiyat VWAP'ın ({sayi(vw)}) {'üstünde, gün içi kontrol alıcılarda' if f_ > 0 else 'altında, gün içi kontrol satıcılarda'}."], tohum + 2)))
    # ADX, uyumsuzluk
    adx = nanv(A["ADX"][i], 0)
    if adx >= 30:
        olg.append((5, f"ADX {adx:.0f}: güçlü trend var, trend yönündeki kırılımlar daha güvenilir."))
    elif 0 < adx < 16:
        olg.append((4, f"ADX {adx:.0f}: piyasa yatay; bant içinde destekten al, dirençten çık mantığı daha iyi çalışır."))
    um = uyumsuzluk(A, ctx["pv"], i)
    if um:
        olg.append((8, "RSI " + ("pozitif uyumsuzluk veriyor: fiyat daha düşük dip yaptı ama momentum daha güçlü." if um > 0
                                 else "negatif uyumsuzluk veriyor: fiyat daha yüksek tepe yaptı ama momentum zayıf.")))
    # En yakın bölgeler: test sayısı ve son test zamanı
    ust = sorted([d for d in sev_d if d["lo"] > c], key=lambda d: d["lo"])
    alt = sorted([d for d in sev_d if d["hi"] < c], key=lambda d: -d["hi"])
    icinde = [d for d in sev_d if d["lo"] <= c <= d["hi"]]
    if icinde:
        d = icinde[0]
        olg.append((9, f"Fiyat şu an {sayi(d['lo'])}–{sayi(d['hi'])} bölgesinin içinde; bu bölge {d['temas']} kez tepki gördü, buradan çıkış yönü önemli."))
    if ust:
        d = ust[0]
        uz = (d["lo"] / c - 1) * 100
        olg.append((7 - min(uz, 5), _sec([
            f"Yukarıdaki ilk direnç {sayi(d['lo'])}–{sayi(d['hi'])} (%{sayi(uz, 1)} yukarıda): {d['ust_n']} kez satış gördü, en son {_zaman_yaz(df, d['son'], mod)}.",
            f"{sayi(d['lo'])}–{sayi(d['hi'])} arası direnç; fiyat buradan {d['ust_n']} kez geri döndü (son test {_zaman_yaz(df, d['son'], mod)}). Mesafe %{sayi(uz, 1)}."], tohum + 3)))
    if alt:
        d = alt[0]
        uz = (c / d["hi"] - 1) * 100
        olg.append((7 - min(uz, 5), _sec([
            f"Aşağıdaki ilk destek {sayi(d['lo'])}–{sayi(d['hi'])} (%{sayi(uz, 1)} aşağıda): {d['alt_n']} kez alıcı geldi, en son {_zaman_yaz(df, d['son'], mod)}.",
            f"Destek {sayi(d['lo'])}–{sayi(d['hi'])}; burada {d['alt_n']} kez alım tepkisi oldu (son {_zaman_yaz(df, d['son'], mod)})" + (", eski direnç desteğe dönmüş." if d.get("rol") else ".")], tohum + 4)))
    if not ust and len(sev_d):
        olg.append((6, "Fiyat görünen tüm direnç bölgelerinin üstünde; yukarıda referans seviye yok, hedefler oynaklığa göre hesaplanır."))
    # Profil
    p = ctx["prof_guncel"]
    if p:
        olg.append((2, f"{({'1': 'Son 3 günde', '5': 'Son 6 günde', 'g': 'Son 10 günde'}).get(mod, 'Son 12 haftada')} en çok işlem {sayi(p['poc'])} fiyatında yapıldı; değer bölgesi {sayi(p['val'])}–{sayi(p['vah'])}."))
    # Endekse göre güç
    rs = float(ctx["rs"][i])
    if abs(rs) >= 2:
        olg.append((3 + abs(rs) / 2, f"BIST100'e göre %{sayi(abs(rs), 1)} {'daha güçlü' if rs > 0 else 'daha zayıf'} gidiyor."))
    # Oynaklık
    olg.append((1.5, f"Bir {('günlük' if mod == 'w' else dil)} mumun ortalama oynaklığı %{sayi(atr / c * 100, 2)} ({sayi(atr)} TL)."))
    # Oluşan formasyonlar
    for f in formlar:
        if f["durum"] == "oluşuyor":
            yon = "yukarı" if f["yon"] > 0 else ("aşağı" if f["yon"] < 0 else "iki yöne de")
            olg.append((7, f"{f['ad']} oluşuyor; {yon} kırılım izlenmeli" + (f", kritik seviye {sayi(f['ref'])}." if f["ref"] else ".")))

    olg.sort(key=lambda x: -x[0])
    cumle = [m for _, m in olg[:8]]
    direnc = min([d["lo"] for d in ust], default=None)
    destek = max([d["hi"] for d in alt], default=None)
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
    sev_d = [d for d in seviye_listesi(ctx, n - 1, ctx["pv"]) if d["guc"] >= 0.4]
    sev = [d["p"] for d in sev_d]
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
    yorum, tetik = bot_yorumu(ctx, sev_d, formlar, gunluk, sym)
    return dict(sym=sym, ctx=ctx, sinyaller=sinyaller, formlar=formlar, sev=sev, fiyat=fiyat, degisim=degisim, yorum=yorum, tetik=tetik,
                rv=nanv(A["RVOL"][i]), ab=nanv(A["AB"][i]), vwap=nanv(A["VWAP"][i], None), rsi=nanv(A["RSI"][i], 50),
                macd=nanv(A["MACDh"][i]), atr=nanv(A["ATR"][i]) / fiyat * 100, yapi=yapi_bul(ctx["pv"])[0],
                htf=int(ctx["htf"][i]), rs=float(ctx["rs"][i]), birikim=birikim, likidite=gunluk_tl,
                yesil_mum=bool(A["Close"][i] >= A["Open"][i]), mod=mod, sev_d=sev_d,
                mum=[m_[0] for m_ in mum_formasyon(A, i)], uyum=uyumsuzluk(A, ctx["pv"], i), adx=nanv(A["ADX"][i], 0))





# ---------- Arayüz (HTML + JS) ----------
ARAYUZ = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700;800;900&family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=Figtree:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,600;9..144,800&family=Public+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&family=Unbounded:wght@500;600;700;800&family=Onest:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{--bg:#f3f5f9;--card:#ffffff;--card2:#eef2f7;--cardS:#ffffff;--ln:#e2e7ef;--ln2:#edf0f5;--tx:#0b1322;--mu:#5c687c;--mu2:#9aa5b6;
--ac:#2743f0;--acT:#2743f0;--acInk:#ffffff;--acs:rgba(39,67,240,.09);--grad:linear-gradient(#2743f0,#2743f0);
--up:#0c9466;--ups:rgba(12,148,102,.1);--dn:#d93c45;--dns:rgba(217,60,69,.09);--wa:#c26a05;--was:rgba(217,119,6,.12);
--r:18px;--sh:0 1px 2px rgba(16,24,40,.05);--nav:#ffffff;--disp:'Schibsted Grotesk',system-ui,sans-serif;--govde:'Schibsted Grotesk',system-ui,sans-serif}
html.koyu{--bg:#0b1220;--card:#121b2d;--card2:#18243a;--cardS:#121b2d;--ln:#223050;--ln2:#1a2740;--tx:#eaf0fa;--mu:#8e9bb3;--mu2:#5b6a86;
--ac:#6c84ff;--acT:#8fa1ff;--acInk:#0b1220;--acs:rgba(108,132,255,.14);--up:#34d399;--ups:rgba(52,211,153,.13);--dn:#ff6b72;--dns:rgba(255,107,114,.12);
--wa:#fbbf24;--was:rgba(251,191,36,.14);--nav:#121b2d}
/* --- TEMALAR --- */
html[data-tema=iznik]{--bg:#edf1f4;--card:#ffffff;--card2:#e5ebef;--cardS:#ffffff;--ln:#d5dee5;--ln2:#e6ebef;--tx:#0e1c2c;--mu:#516173;--mu2:#8e9cab;
--ac:#1f3fae;--acT:#1f3fae;--acInk:#ffffff;--acs:rgba(31,63,174,.09);--up:#08907f;--ups:rgba(8,144,127,.11);--dn:#cf3f2b;--dns:rgba(207,63,43,.1);
--wa:#b57808;--was:rgba(200,137,14,.13);--r:20px;--sh:0 1px 0 rgba(14,28,44,.04);--nav:#0e1c2c;--disp:Unbounded,'Schibsted Grotesk',sans-serif;--govde:Onest,'Schibsted Grotesk',system-ui,sans-serif;--cini:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='48' height='48' viewBox='0 0 48 48'%3E%3Cg fill='none' stroke='white' stroke-width='1.1' stroke-opacity='.55'%3E%3Cpath d='M24 8l4.7 11.3L40 24l-11.3 4.7L24 40l-4.7-11.3L8 24l11.3-4.7z'/%3E%3Crect x='14' y='14' width='20' height='20' transform='rotate(45 24 24)' stroke-opacity='.25'/%3E%3Ccircle cx='24' cy='24' r='3'/%3E%3Cpath d='M0 0l6 6M48 0l-6 6M0 48l6-6M48 48l-6-6' stroke-opacity='.35'/%3E%3C/g%3E%3C/svg%3E")}
html[data-tema=iznik] .logo b,html[data-tema=iznik] .bolum h3{font-weight:700!important;letter-spacing:-.01em}
html[data-tema=iznik] .bolum h3{font-size:15px}
html[data-tema=iznik] .buyuk,html[data-tema=iznik] .dfiyat b{font-weight:700;letter-spacing:-.02em}
html[data-tema=iznik] .tile b,html[data-tema=iznik] .mini b,html[data-tema=iznik] .botalt b,html[data-tema=iznik] .halka b{font-weight:700;letter-spacing:-.01em}
html[data-tema=iznik] nav.alt{left:10px;right:10px;bottom:calc(10px + env(safe-area-inset-bottom));padding:6px;border:0;border-radius:24px;box-shadow:0 18px 40px -16px rgba(14,28,44,.55)}
html[data-tema=iznik] nav.alt button{color:#7f8fa1}html[data-tema=iznik] nav.alt button.on,html[data-tema=iznik] nav.alt button.on svg{color:#fff}
html[data-tema=iznik] .nav-ind{top:auto;bottom:4px;height:3px;border-radius:3px;background:#3fd1bd}
html[data-tema=iznik] .nav-bot .bd{background:#1f3fae;box-shadow:0 0 0 5px var(--nav),0 10px 22px -8px rgba(31,63,174,.8)}
html[data-tema=iznik] .seg button.on{background:var(--tx);color:#fff;box-shadow:none}
html[data-tema=iznik] .chip.on{background:var(--tx);border-color:var(--tx);color:#fff}
html[data-tema=iznik] .dilim{background:var(--card2);border-color:transparent}html[data-tema=iznik] .dilim .ind{background:var(--tx)}
html[data-tema=iznik] .kart{border-color:#dde4ea}
html[data-tema=iznik] .bothero{background:var(--ac);color:#fff;border:0}
html[data-tema=iznik] .bothero .buyuk>span[style]{color:rgba(255,255,255,.6)!important}
html[data-tema=iznik] .bothero .kart{color:var(--tx)}html[data-tema=iznik] .bothero .kart :is(.lbl,small,.mu,.not){color:var(--mu)!important}
html[data-tema=iznik] .bothero .kart .btn.ana{background:var(--ac);color:#fff}
html[data-tema=iznik] .bothero :is(.lbl,small,.mu){color:rgba(255,255,255,.72)!important}
html[data-tema=iznik] .bothero .botik{background:#fff}html[data-tema=iznik] .bothero .botik svg{color:var(--ac)}
html[data-tema=iznik] .bothero .botalt div{background:rgba(255,255,255,.12)}
html[data-tema=iznik] .bothero .rozet{background:rgba(255,255,255,.14);color:#fff}
html[data-tema=iznik] .bothero .rozet.up{background:#3fd1bd;color:#05302a}html[data-tema=iznik] .bothero .rozet.dn{background:#ff9a8a;color:#3d0d06}
html[data-tema=iznik] .bothero .btn{background:rgba(255,255,255,.12);border-color:transparent;color:#fff}html[data-tema=iznik] .bothero .btn.ana{background:#fff;color:var(--ac)}

html[data-tema=gece]{--bg:#0d1726;--card:#132136;--card2:#1a2b44;--cardS:#132136;--ln:#22344f;--ln2:#1b2b42;--tx:#e9eff7;--mu:#8fa0b8;--mu2:#5d7090;
--ac:#f5b83d;--acT:#f5b83d;--acInk:#1d1404;--acs:rgba(245,184,61,.14);--up:#3ddc97;--ups:rgba(61,220,151,.13);--dn:#ff6b6b;--dns:rgba(255,107,107,.13);
--wa:#f5b83d;--was:rgba(245,184,61,.15);--r:20px;--sh:none;--nav:#132136;--disp:'Bricolage Grotesque',Figtree,sans-serif;--govde:Figtree,system-ui,sans-serif}
html[data-tema=terminal]{--bg:#06080a;--card:#0d1115;--card2:#141a20;--cardS:#0d1115;--ln:#212a33;--ln2:#171e25;--tx:#d6e1ea;--mu:#7d8a97;--mu2:#4c5864;
--ac:#38d68c;--acT:#38d68c;--acInk:#03140b;--acs:rgba(56,214,140,.12);--up:#38d68c;--ups:rgba(56,214,140,.12);--dn:#ff5f5f;--dns:rgba(255,95,95,.12);
--wa:#ffc53d;--was:rgba(255,197,61,.13);--r:4px;--sh:none;--nav:#0d1115;--disp:'IBM Plex Mono',monospace;--govde:'IBM Plex Mono',monospace}
html[data-tema=terminal] body{font-size:13px}
html[data-tema=terminal] .ozet h1{font-size:18px;font-weight:600;line-height:1.45}html[data-tema=terminal] .vade-bant{font-size:10.5px}
html[data-tema=terminal] :is(.kart,.btn,.seg,.seg button,.chip,.ikon,.tile,.giris,.stepper,.stepper button,.dilim,.dilim .ind,.dilim button,.rozet,.yon,.kal,.dl,.avatar,.ig>div,.uc div,.botalt div,.istat div,.drm,.lot,.anahtar,.sheet,.nav-bot .bd,.bar,.bar i,.genislik,.genislik i,.harita div,.akisbar,.halka){border-radius:3px!important}
html[data-tema=gazete]{--bg:#f4efe4;--card:#fffdf7;--card2:#eee6d6;--cardS:#fffdf7;--ln:#d9cfbd;--ln2:#e8e0d0;--tx:#1c1915;--mu:#6a6156;--mu2:#a0968a;
--ac:#8b1e2d;--acT:#8b1e2d;--acInk:#fffdf7;--acs:rgba(139,30,45,.08);--up:#1d6e46;--ups:rgba(29,110,70,.09);--dn:#b4231c;--dns:rgba(180,35,28,.08);
--wa:#9a5b00;--was:rgba(154,91,0,.1);--r:3px;--sh:none;--nav:#fffdf7;--disp:Fraunces,Georgia,serif;--govde:'Public Sans',system-ui,sans-serif}
html[data-tema=gazete] :is(.kart,.btn,.seg,.seg button,.chip,.ikon,.tile,.giris,.stepper,.stepper button,.dilim,.dilim .ind,.dilim button,.rozet,.yon,.kal,.dl,.avatar,.ig>div,.uc div,.botalt div,.istat div,.drm,.lot,.anahtar,.nav-bot .bd,.harita div){border-radius:2px!important}
html[data-tema=gazete] .ozet h1{font-weight:600;font-size:27px}html[data-tema=gazete] .bolum h3{font-weight:600;font-size:19px}
html[data-tema=gazete] .kart{border-color:var(--tx);border-width:1px 0 0;box-shadow:none;background:transparent}
html[data-tema=neon]{--bg:#070914;--card:rgba(255,255,255,.045);--card2:rgba(255,255,255,.075);--cardS:#11142a;--ln:rgba(255,255,255,.09);--ln2:rgba(255,255,255,.05);--tx:#eef0fb;--mu:#9097b8;--mu2:#5b6182;
--ac:#8b7bff;--acT:#a99cff;--acInk:#ffffff;--acs:rgba(139,123,255,.16);--up:#2fe0a0;--ups:rgba(47,224,160,.13);--dn:#ff5c86;--dns:rgba(255,92,134,.13);
--wa:#ffb547;--was:rgba(255,181,71,.15);--r:22px;--sh:0 14px 34px -18px rgba(0,0,0,.8);--nav:#10132a;--disp:Manrope,sans-serif;--govde:Manrope,sans-serif}
html[data-tema=neon] body{background:radial-gradient(ellipse 80% 50% at 0% 0%,rgba(110,90,255,.28),transparent 60%),radial-gradient(ellipse 70% 45% at 100% 0%,rgba(20,190,230,.18),transparent 60%),var(--bg)}
html[data-tema=neon] .btn.ana,html[data-tema=neon] .chip.on,html[data-tema=neon] .dilim .ind,html[data-tema=neon] .nav-bot .bd{background:linear-gradient(135deg,#7c6cff,#22c4e8)}
.temalar{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.tema{border-radius:16px;overflow:hidden;cursor:pointer;border:2px solid transparent;transition:transform .15s}.tema:active{transform:scale(.97)}
.tema.on{border-color:var(--ac)}.tema .onz{height:96px;padding:10px;display:flex;flex-direction:column;gap:6px}
.tema .onz i{display:block;border-radius:4px;height:8px}.tema .onz .bas{height:14px;width:70%}
.tema .ad2{padding:8px 10px;font-size:12.5px;font-weight:700;background:var(--card);border-top:1px solid var(--ln)}
.tema .ad2 small{display:block;color:var(--mu);font-weight:600;font-size:11px}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;height:100%;background:var(--bg);color:var(--tx);font:14px/1.45 var(--govde);-webkit-font-smoothing:antialiased}
body{overflow:hidden}button,input,select{font-family:inherit;color:inherit}button{cursor:pointer;border:0;background:none;padding:0}
.n{font-variant-numeric:tabular-nums}
.up{color:var(--up)}.dn{color:var(--dn)}.mu{color:var(--mu)}.wa{color:var(--wa)}.act{color:var(--acT)}
.lbl{font-size:11.5px;font-weight:700;color:var(--mu)}
#app{position:relative;z-index:1;display:flex;flex-direction:column;height:100%}
/* üst */
.ust{flex:none;padding:12px 16px 6px}
.ust1{display:flex;align-items:center;gap:8px}
.logo{display:flex;align-items:center;gap:10px;margin-right:auto}
.logo svg{width:38px;height:38px}
.logo b{display:block;font:800 19px/1.05 var(--disp);letter-spacing:-.02em}
.logo b span{color:var(--ac)}
.logo b{font-weight:900!important}
.logo small{display:block;white-space:nowrap;font-size:11px;color:var(--mu);font-weight:600}
.sweep{transform-origin:20px 20px;animation:don 4s linear infinite}@keyframes don{to{transform:rotate(360deg)}}
.ikon{width:38px;height:38px;border-radius:13px;background:var(--card);border:1px solid var(--ln);display:grid;place-items:center;position:relative;transition:transform .15s;flex:none;color:var(--tx);text-decoration:none}
.ikon:active{transform:scale(.9)}.ikon svg{width:18px;height:18px}
.rz{position:absolute;top:-5px;right:-5px;background:var(--dn);color:#fff;font-size:9.5px;font-weight:800;border-radius:9px;padding:1px 5px;min-width:17px;text-align:center;box-shadow:0 0 0 2px var(--bg);animation:pop .4s cubic-bezier(.3,1.6,.5,1)}
@keyframes pop{from{transform:scale(0)}}
.canli{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:800;color:var(--mu);background:var(--card);border:1px solid var(--ln);padding:6px 10px;border-radius:99px;white-space:nowrap}
.nokta{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--mu2);flex:none}
.nokta.on{background:var(--up);animation:nabiz 1.8s infinite}.nokta.wa{background:var(--wa)}
@keyframes nabiz{0%{box-shadow:0 0 0 0 rgba(61,220,151,.6)}70%{box-shadow:0 0 0 8px rgba(61,220,151,0)}100%{box-shadow:0 0 0 0 rgba(61,220,151,0)}}
.dilim{position:relative;display:flex;margin-top:12px;background:var(--card);border:1px solid var(--ln);border-radius:15px;padding:4px}
.dilim .ind{position:absolute;top:4px;bottom:4px;left:0;border-radius:11px;background:var(--ac);transition:transform .45s cubic-bezier(.3,1.25,.5,1),width .3s}
.dilim button{position:relative;flex:1;font-weight:800;font-size:12.5px;color:var(--mu);padding:8px 0;transition:color .3s;z-index:1}
.dilim button.on{color:var(--acInk)}
.vade-bant{display:flex;justify-content:space-between;font-size:11.5px;color:var(--mu);padding:8px 3px 2px;font-weight:600}.vade-bant b{color:var(--tx)}
main{flex:1;overflow-y:auto;padding:6px 16px 110px;-webkit-overflow-scrolling:touch;scrollbar-width:none}main::-webkit-scrollbar{display:none}
/* genel */
.kart{background:var(--card);border:1px solid var(--ln);border-radius:var(--r);position:relative;overflow:hidden;box-shadow:var(--sh)}
.pad{padding:16px}
.bolum{display:flex;align-items:center;justify-content:space-between;margin:26px 2px 11px}
.bolum h3{margin:0;font:700 17px/1.2 var(--disp);letter-spacing:-.01em}
.bolum a,.link{font-size:12.5px;font-weight:800;color:var(--acT);cursor:pointer}
.anim{animation:gecis .28s ease-out both}
@keyframes gecis{from{opacity:0;transform:translateY(6px)}}
@keyframes yuksel{from{opacity:0;transform:translateY(16px)}}
.rozet{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:800;padding:4px 10px;border-radius:99px;background:var(--card2);color:var(--mu);white-space:nowrap}
.rozet.up{background:var(--ups);color:var(--up)}.rozet.dn{background:var(--dns);color:var(--dn)}.rozet.ac{background:var(--acs);color:var(--acT)}.rozet.wa{background:var(--was);color:var(--wa)}
.yon{display:inline-block;font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:7px;letter-spacing:.03em;vertical-align:1px}
.yon.al{background:var(--ups);color:var(--up)}.yon.sat{background:var(--dns);color:var(--dn)}
.kal{display:inline-block;font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:7px;background:var(--card2);color:var(--mu);vertical-align:1px}
.kal.Ap{background:var(--ac);color:var(--acInk)}.kal.A{background:var(--acs);color:var(--acT)}
.dl{display:inline-block;font-size:10.5px;font-weight:700;color:var(--mu);background:var(--card2);padding:2px 7px;border-radius:7px}
.avatar{display:grid;place-items:center;border-radius:13px;font-weight:800;font-size:11.5px;color:#fff;flex:none;letter-spacing:.02em;box-shadow:inset 0 1px 0 rgba(255,255,255,.25)}
.alan{display:block;width:100%;animation:ac 1.4s cubic-bezier(.4,0,.2,1) both}
@keyframes ac{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}
.buyuk{font:800 36px/1.05 var(--disp);letter-spacing:-.03em}
.satir{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sat1{display:flex;align-items:center;justify-content:space-between;gap:10px}
.btn{flex:1;border-radius:15px;padding:13px;font-weight:800;font-size:13.5px;background:var(--card2);border:1px solid var(--ln);transition:transform .15s;display:inline-flex;align-items:center;justify-content:center;gap:7px}
.btn:active{transform:scale(.96)}.btn.ana{background:var(--ac);border:0;color:var(--acInk)}.btn.kir{color:var(--dn)}
.btn svg{width:16px;height:16px}
.dugmeler{display:flex;gap:8px;padding:14px 16px 16px}
.seg{display:flex;gap:4px;background:var(--card);border:1px solid var(--ln);border-radius:15px;padding:4px;margin-bottom:12px;overflow-x:auto;scrollbar-width:none}.seg::-webkit-scrollbar{display:none}
.seg button{flex:1;padding:9px 6px;font-size:12.5px;font-weight:800;color:var(--mu);border-radius:11px;transition:all .25s;white-space:nowrap}
.seg button.on{background:var(--card2);color:var(--tx);box-shadow:0 4px 12px -4px rgba(0,0,0,.4)}
.chips{display:flex;gap:7px;overflow-x:auto;margin:0 -16px 12px;padding:0 16px;scrollbar-width:none}.chips::-webkit-scrollbar{display:none}
.chip{flex:none;color:var(--mu);background:var(--card);border:1px solid var(--ln);border-radius:99px;padding:7px 13px;font-size:12.5px;font-weight:700;transition:all .2s}
.chip.on{color:var(--acInk);background:var(--ac);border-color:var(--ac)}.chip:disabled{opacity:.35}
.bos{border:1.5px dashed var(--ln);border-radius:var(--r);padding:26px 18px;text-align:center;color:var(--mu);line-height:1.55;font-size:13px}.bos b{display:block;color:var(--tx);margin-bottom:4px;font-size:14px}
.not{color:var(--mu);font-size:12px;line-height:1.6;margin:12px 2px 0}
.acik-not{color:var(--mu);font-size:12.5px;line-height:1.55;margin:0 2px 12px}
.uyari{color:var(--mu2);font-size:10.5px;text-align:center;margin:26px 0 4px;font-weight:700;letter-spacing:.05em}

/* çini piyasa kartı (panelin başı) */
.cini{background:var(--ac);color:#fff;border:0;margin-top:4px;border-radius:calc(var(--r) + 4px)}
.cini .desen{position:absolute;inset:0;background:var(--cini,none);background-size:48px;pointer-events:none;-webkit-mask-image:radial-gradient(circle 340px at 100% 0%,#000 0,rgba(0,0,0,.55) 45%,transparent 100%);mask-image:radial-gradient(circle 340px at 100% 0%,#000 0,rgba(0,0,0,.55) 45%,transparent 100%)}
.cini .ic{position:relative;padding:16px 18px 0}
.cini .ust2{display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:12.5px;font-weight:600;color:rgba(255,255,255,.78)}
.cini .ust2 b{color:#fff;font-weight:700}
.cini .deg{display:inline-flex;align-items:center;gap:5px;font-weight:800;font-size:13px;padding:5px 10px;border-radius:99px;background:rgba(255,255,255,.14);color:#fff}
.cini .deg.up{background:#3fd1bd;color:#04302a}.cini .deg.dn{background:#ff9a8a;color:#3d0d06}
.cini .endeks{font:700 44px/1 var(--disp);letter-spacing:-.03em;margin:12px 0 2px;font-variant-numeric:tabular-nums}
.cini .alt2{font-size:12.5px;color:rgba(255,255,255,.75);font-weight:600}
.cini svg.ccz{display:block;width:100%;height:92px;margin-top:6px}
.cini .ccz path.c{fill:none;stroke:#fff;stroke-width:2.2;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:0}
.cini .ccz path.f{fill:url(#cGrad)}
.cini .cumle{position:relative;background:rgba(5,14,40,.22);padding:13px 18px 15px;font-size:14px;line-height:1.5;font-weight:500}
.cini .cumle b{font-weight:800}.cini .cumle a{color:#fff;font-weight:800;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.cini .cumle .up{color:#7ff0de}.cini .cumle .dn{color:#ffb4a8}
.cini .gd{display:flex;height:5px;gap:3px;margin:12px 0 0}.cini .gd i{display:block;border-radius:3px}
.ilk .cini .desen{animation:desen 1.6s cubic-bezier(.2,.7,.2,1) both}
@keyframes desen{from{opacity:0;transform:scale(1.15) rotate(-4deg);transform-origin:100% 0}}
.ilk .cini .ccz path.c{animation:ciz 1.5s .25s cubic-bezier(.4,0,.2,1) both}
.ilk .cini .ccz path.f{animation:belir .8s 1.1s both}
@keyframes ciz{from{stroke-dashoffset:1}}@keyframes belir{from{opacity:0}}
/* kayan fiyat bandı */
.bant2{position:relative;overflow:hidden;margin:8px -16px 0;padding:7px 0;border-block:1px solid var(--ln);background:var(--card);-webkit-mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);mask-image:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent)}
.bant2 .yol2{display:flex;width:max-content;animation:kay var(--sure,60s) linear infinite}
.bant2:active .yol2{animation-play-state:paused}
.bant2 span{display:inline-flex;gap:6px;align-items:baseline;padding:0 14px;font-size:12px;font-weight:700;white-space:nowrap;cursor:pointer;border-right:1px solid var(--ln2)}
.bant2 span b{font-weight:800}.bant2 span em{font-style:normal;font-weight:800}
@keyframes kay{to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.bant2 .yol2{animation:none}.ilk .cini *{animation:none!important}}
#grafik.acil{animation:grafikAc .9s cubic-bezier(.3,.7,.2,1) both}
@keyframes grafikAc{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}

/* öğrenen beyin */
.beyin{padding:16px}
.beyin .sev{display:flex;align-items:center;gap:12px}
.beyin .rozet2{width:52px;height:52px;border-radius:16px;background:var(--ac);color:var(--acInk);display:grid;place-items:center;font:800 20px var(--disp);flex:none;position:relative}
.beyin .rozet2 small{position:absolute;bottom:-6px;right:-6px;background:var(--tx);color:var(--bg);font:800 10px var(--govde);padding:2px 6px;border-radius:8px}
.beyin .sev b{display:block;font:700 17px var(--disp)}.beyin .sev .alt3{font-size:12.5px;color:var(--mu);font-weight:600}
.beyin .ilerle2{height:8px;border-radius:5px;background:var(--card2);margin:14px 0 6px;overflow:hidden}
.beyin .ilerle2 i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,var(--ac),var(--up));transform-origin:left;animation:uza 1.2s cubic-bezier(.2,.8,.2,1) both}
.beyin .dort{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:12px}
.beyin .dort div{background:var(--card2);border-radius:12px;padding:8px 9px}.beyin .dort b{display:block;font-size:15px;font-weight:800}.beyin .dort small{font-size:10.5px;color:var(--mu);font-weight:700;line-height:1.25;display:block}
.kars{display:grid;gap:9px;margin-top:4px}
.kars>div{display:grid;grid-template-columns:118px 1fr 62px;align-items:center;gap:8px;font-size:12.5px;font-weight:700}
.kars .cb{position:relative;height:16px;background:var(--card2);border-radius:5px}
.kars .cb i{position:absolute;top:0;bottom:0;border-radius:5px;transform-origin:left;animation:uza 1s both}
.kars .cb::after{content:"";position:absolute;left:50%;top:-3px;bottom:-3px;width:1.5px;background:var(--mu2)}
.ders{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--ln2);align-items:flex-start}.ders:last-child{border-bottom:0}
.ders .di{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;flex:none;font-size:14px;font-weight:900}
.ders .di.up{background:var(--ups);color:var(--up)}.ders .di.dn{background:var(--dns);color:var(--dn)}
.ders b{display:block;font-size:13.5px;font-weight:700;line-height:1.35}.ders small{display:block;font-size:12px;color:var(--mu);font-weight:600;margin-top:2px}
.hafta{display:flex;align-items:flex-end;gap:5px;height:90px;margin-top:10px;position:relative}
.hafta>div{flex:1;display:flex;gap:2px;align-items:flex-end;height:100%;position:relative}
.hafta i{flex:1;border-radius:3px 3px 0 0;transform-origin:bottom;animation:yuksel2 .9s both}
@keyframes yuksel2{from{transform:scaleY(0)}}
.hafta span{position:absolute;bottom:-17px;left:0;right:0;text-align:center;font-size:9.5px;color:var(--mu2);font-weight:700}
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
.tile b{display:block;font:800 21px/1.15 var(--disp);letter-spacing:-.01em}.tile small{font-size:11.5px;color:var(--mu);font-weight:700}
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
.halka b{position:absolute;inset:0;display:grid;place-items:center;font:800 14px var(--disp)}
.botmini{cursor:pointer;margin-top:12px}
.botbas{display:flex;align-items:center;gap:11px}.botbas b{display:block;font-size:15px;font-weight:800}.botbas small{display:block;font-size:11.5px;color:var(--mu);font-weight:600}
.botik{width:42px;height:42px;border-radius:14px;background:var(--ac);display:grid;place-items:center;flex:none}
.botik svg{width:22px;height:22px;color:var(--acInk)}
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
.radarkart{border-radius:28px;padding:18px 16px 16px}
.radar{position:relative;width:min(100%,330px);aspect-ratio:1;margin:4px auto 0}
.radar svg.iz{position:absolute;inset:0;width:100%;height:100%}
.radar .tarama{position:absolute;inset:4%;border-radius:50%;background:conic-gradient(from 0deg,transparent 0deg,transparent 290deg,color-mix(in srgb,var(--ac) 22%,transparent) 350deg,color-mix(in srgb,var(--ac) 55%,transparent) 360deg);animation:don 6s linear infinite}
.radar .tarama::after{content:"";position:absolute;left:50%;top:0;width:2px;height:50%;margin-left:-1px;background:linear-gradient(var(--ac),transparent);border-radius:2px}
.radar .nok{position:absolute;width:10px;height:10px;margin:-5px 0 0 -5px;cursor:pointer}
.radar .nok::before{content:"";position:absolute;inset:0;border-radius:50%;background:var(--c);opacity:.4;animation:blip 6s linear infinite both;animation-delay:var(--d)}
.radar .nok.b{width:14px;height:14px;margin:-7px 0 0 -7px}
.radar .nok i{position:absolute;left:14px;top:50%;transform:translateY(-50%);font:700 11px var(--disp);color:var(--tx);white-space:nowrap;font-style:normal;text-shadow:0 1px 3px var(--bg)}
.radar .nok.sol i{left:auto;right:14px}
@keyframes blip{0%{opacity:1;transform:scale(1.7);box-shadow:0 0 0 6px rgba(255,255,255,.12)}6%{opacity:1;transform:scale(1)}55%{opacity:.4}100%{opacity:.4}}
.radar .merkez{position:absolute;left:50%;top:50%;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;background:var(--ac);box-shadow:0 0 0 4px var(--acs)}
.radar-alt{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;margin-top:12px}
.radar-alt b{display:block;font:800 30px/1 var(--disp);letter-spacing:-.02em}
.radar-alt small{font-size:12.5px;color:var(--mu);font-weight:600}
.radar-alt .sag2{text-align:right;font-size:12.5px;font-weight:700;line-height:1.7}
.bistsat{display:flex;align-items:center;gap:14px;padding:14px 16px;margin-top:12px}
.bistsat .alan{height:48px;width:120px;flex:none}
.hb{display:flex;gap:11px;padding:12px 14px;border-bottom:1px solid var(--ln2);text-decoration:none;color:inherit}
.hb:last-child{border-bottom:0}
.hb .hp{width:8px;border-radius:4px;flex:none;align-self:stretch}
.hb p{margin:0;font-size:13.5px;font-weight:600;line-height:1.45}
.hb small{display:block;color:var(--mu);font-size:11.5px;font-weight:600;margin-top:4px}
.durumlar{display:flex;gap:6px;flex-wrap:wrap;padding:12px 16px 0}
.anahtar{display:flex;align-items:center;justify-content:space-between;background:var(--card2);border-radius:15px;padding:12px 14px;cursor:pointer}
.anahtar .tg{width:46px;height:28px;border-radius:99px;background:var(--ln);position:relative;transition:background .2s;flex:none}
.anahtar .tg::after{content:"";position:absolute;left:3px;top:3px;width:22px;height:22px;border-radius:50%;background:#fff;transition:transform .2s}
.anahtar.on .tg{background:var(--ac)}.anahtar.on .tg::after{transform:translateX(18px)}
.ozet{padding:10px 2px 6px}
.ozet .tarih{font-size:13px;font-weight:600;color:var(--mu);margin:0 0 6px}
.ozet h1{margin:0;font:700 23px/1.32 var(--disp);letter-spacing:-.02em;color:var(--tx)}
.ozet h1 span{animation:kelime .6s cubic-bezier(.2,.8,.2,1) both;animation-delay:calc(var(--i) * 90ms)}
.ozet h1 b{font-weight:900}.ozet h1 a{color:var(--ac);text-decoration:none;font-weight:900;cursor:pointer;border-bottom:2px solid var(--acs)}
@keyframes kelime{from{opacity:0;filter:blur(4px)}}
.ikili{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
.mini{padding:13px 14px;cursor:pointer}.mini .alan{height:34px;margin:6px -14px -13px;width:calc(100% + 28px)}
.mini b{display:block;font:800 21px/1.15 var(--disp);margin-top:2px}
.yaris-satir{display:grid;grid-template-columns:22px 1fr auto;gap:10px;align-items:center;padding:12px 14px;border-bottom:1px solid var(--ln2)}
.yaris-satir:last-child{border-bottom:0}.yaris-satir .sira{font:800 15px var(--disp);color:var(--mu2)}
.yaris-satir.bir .sira{color:var(--ac)}
.kayip-tbl td:first-child{white-space:normal}
.alarm{display:flex;align-items:center;gap:11px;padding:12px 14px;border-bottom:1px solid var(--ln2)}.alarm:last-child{border-bottom:0}
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
.bothero{border-radius:24px}
#botGrafik{height:170px;margin-top:6px;position:relative}
.botalt{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 16px 0}
.botalt div{background:var(--card2);border-radius:14px;padding:10px 11px}.botalt b{display:block;font:800 18px/1.2 var(--disp);margin-top:1px}.botalt small{font-size:10.5px;color:var(--mu);font-weight:700}
.istat{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.istat div{background:var(--card);border:1px solid var(--ln);border-radius:16px;padding:12px}.istat b{display:block;font:800 19px/1.2 var(--disp);margin-top:2px}
.gauge{position:relative;width:220px;max-width:100%;margin:6px auto 0}
.gauge svg{width:100%;display:block}.gauge .gd{animation:gd 1.6s cubic-bezier(.2,.8,.2,1) both}@keyframes gd{from{stroke-dasharray:0 100}}
.gauge .gv{position:absolute;left:0;right:0;bottom:14px;text-align:center}.gauge .gv b{display:block;font:800 40px/1 var(--disp);letter-spacing:-.03em}.gauge .gv span{font-size:12.5px;font-weight:800}
.bilesen>div{margin-top:12px}.bilesen .ust3{display:flex;justify-content:space-between;font-size:12.5px;font-weight:700}
.bar{height:8px;border-radius:99px;background:var(--card2);margin-top:6px;overflow:hidden}.bar i{display:block;height:100%;border-radius:99px;background:var(--ac);transform-origin:left;animation:uza 1.2s cubic-bezier(.2,.8,.2,1) both}
.donut{display:flex;align-items:center;gap:16px}.donut svg{width:96px;height:96px;transform:rotate(-90deg);flex:none}
.donut circle{fill:none;stroke-width:12}.donut .dk{animation:hk 1.3s cubic-bezier(.2,.8,.2,1) both}
.leg{flex:1}.leg div{display:flex;justify-content:space-between;align-items:center;padding:5px 0;font-size:12.5px;font-weight:700}.leg i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:7px}
.term{padding:0;overflow:hidden;margin-bottom:12px}
.termust{display:grid;grid-template-columns:repeat(auto-fit,minmax(96px,1fr));border-bottom:1px solid var(--ln)}
.termust>div{padding:11px 12px;border-right:1px solid var(--ln);border-bottom:1px solid var(--ln);margin-bottom:-1px}
.term small,.tbaslik .lbl{font-size:10px;color:var(--mu2);font-weight:800;letter-spacing:.05em;text-transform:uppercase;display:block}
.termust b{font-size:15px;font-weight:800;display:block;margin-top:3px}
.tbaslik{display:flex;justify-content:space-between;align-items:center;padding:12px 14px 8px;border-bottom:1px solid var(--ln)}
.tbaslik b{font:800 13px var(--disp);letter-spacing:.02em}
.trow{padding:12px 14px;border-bottom:1px solid var(--ln)}.trow:last-child{border-bottom:0}
.trow .tu{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.trow .tu b.sym{font:800 15px var(--disp);cursor:pointer}.trow .tu .dl{font-size:10.5px;font-weight:800;color:var(--mu2);margin-left:6px}
.trow .tk{text-align:right;white-space:nowrap}.trow .tk small{text-transform:none;letter-spacing:0;font-size:11.5px;color:inherit}.trow .tk b{font-size:15px;font-weight:800;display:block}.trow .tk small{font-size:11.5px;font-weight:700}
.trow .ts{font-size:12.5px;color:var(--mu);font-weight:600;margin-top:2px}
.tbar{position:relative;height:6px;border-radius:3px;background:var(--card2);margin:10px 0 4px}
.tbar i{position:absolute;top:0;bottom:0;border-radius:3px}.tbar span{position:absolute;top:-3px;width:2px;height:12px;background:var(--mu2);border-radius:1px}
.tbar em{position:absolute;top:-4px;width:10px;height:14px;margin-left:-5px;border-radius:3px;background:var(--tx);box-shadow:0 0 0 2px var(--card)}
.tetk{display:flex;justify-content:space-between;font-size:10.5px;font-weight:800;color:var(--mu2)}
.tnot{margin-top:8px;padding:8px 10px;border-radius:10px;background:var(--card2);font-size:12.5px;font-weight:600;line-height:1.45;display:flex;gap:8px;align-items:flex-start}
.tnot i{font-style:normal}
.tbayrak{display:inline-block;font-size:10px;font-weight:800;padding:2px 6px;border-radius:5px;margin-left:5px;vertical-align:2px;background:var(--card2);color:var(--mu)}
.tbayrak.up{background:var(--ups);color:var(--up)}.tbayrak.wa{background:var(--was);color:var(--wa)}
.ttus{display:flex;gap:8px;margin-top:8px}.ttus button{flex:1;padding:7px;font-size:12px}
.ed{display:grid;grid-template-columns:40px 48px 1fr;gap:4px 8px;padding:9px 14px;border-bottom:1px solid var(--ln);font-size:12.5px;align-items:start}.ed:last-child{border-bottom:0}
.ed .z{color:var(--mu2);font-weight:700;font-variant-numeric:tabular-nums}.ed p{margin:0;font-weight:600;line-height:1.4}.ed p b{font-weight:800}
.etk2{font-size:10px;font-weight:900;letter-spacing:.04em;text-align:center;padding:3px 0;border-radius:5px}
.etk2.al{background:var(--ups);color:var(--up)}.etk2.sat{background:var(--dns);color:var(--dn)}.etk2.emir{background:var(--acs);color:var(--acT)}
.pozkart{margin-bottom:12px}.pozkart .ilerle{position:relative;height:8px;border-radius:99px;background:var(--card2);margin:16px 16px 4px}
.pozkart .ilerle i{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:linear-gradient(90deg,var(--dn),var(--wa),var(--up));transform-origin:left;animation:uza 1.2s both}
.pozkart .ilerle span{position:absolute;top:-4px;width:2px;height:16px;background:var(--mu2);border-radius:2px}
.pozkart .etk{display:flex;justify-content:space-between;font-size:10px;color:var(--mu);font-weight:800;padding:0 16px}
.gunbar{display:flex;justify-content:center;align-items:flex-end;gap:4px;height:120px;padding:10px 4px 0;position:relative}
.gunbar::after{content:"";position:absolute;left:0;right:0;top:calc(10px + var(--sifir));height:1px;background:var(--ln)}
.gunbar div{flex:1;max-width:28px;position:relative;height:100%}
.gunbar i{position:absolute;left:0;right:0;border-radius:5px;animation:boy .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes boy{from{transform:scaleY(0)}}
.kayit{display:flex;align-items:center;gap:10px;margin-top:12px;padding:11px 14px;border-radius:16px;font-size:12.5px;font-weight:700;cursor:pointer;border:1px solid var(--ln);background:var(--card)}
.kayit .ki{width:30px;height:30px;border-radius:10px;display:grid;place-items:center;flex:none;font-size:14px}
.kayit.ok .ki{background:var(--ups);color:var(--up)}.kayit.uyar{border-color:rgba(255,181,71,.35);background:var(--was)}.kayit.uyar .ki{background:rgba(255,181,71,.25);color:var(--wa)}
.kayit.hata{border-color:rgba(217,60,69,.3);background:var(--dns)}.kayit.hata .ki{background:rgba(255,107,107,.22);color:var(--dn)}
.kayit small{display:block;color:var(--mu);font-weight:600;font-size:11.5px;margin-top:1px}
.adimlar{counter-reset:a;margin:0;padding:0;list-style:none}.adimlar li{counter-increment:a;position:relative;padding:0 0 14px 40px;font-size:13px;line-height:1.55;font-weight:600}
.adimlar li::before{content:counter(a);position:absolute;left:0;top:-2px;width:28px;height:28px;border-radius:50%;background:var(--ac);color:var(--acInk);display:grid;place-items:center;font-weight:800;font-size:13px}
.kod{display:block;background:var(--card2);border:1px solid var(--ln);border-radius:12px;padding:10px 12px;font:600 12px ui-monospace,Menlo,monospace;white-space:pre-wrap;word-break:break-all;margin-top:6px;user-select:all}
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
input[type=range]{width:100%;accent-color:#f5b83d}
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
nav.alt{position:fixed;left:0;right:0;bottom:0;display:flex;align-items:center;background:var(--nav);border-top:1px solid var(--ln);padding:6px 6px calc(8px + env(safe-area-inset-bottom));z-index:10}
nav.alt button{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:7px 0;color:var(--mu2);font-size:10.5px;font-weight:800;position:relative;transition:color .3s;z-index:1}
nav.alt button svg{width:21px;height:21px;transition:transform .35s cubic-bezier(.3,1.5,.5,1)}
nav.alt button.on{color:var(--ac)}nav.alt button.on svg{transform:translateY(-1px);color:var(--ac)}
.nav-ind{position:absolute;top:0;height:3px;left:0;border-radius:0 0 3px 3px;background:var(--ac);transition:transform .45s cubic-bezier(.3,1.25,.5,1),width .3s,opacity .3s}
.nav-bot .bd{width:52px;height:52px;margin-top:-26px;border-radius:16px;background:var(--ac);display:grid;place-items:center;box-shadow:0 0 0 5px var(--nav),0 8px 20px -8px rgba(39,67,240,.6);transition:transform .35s cubic-bezier(.3,1.5,.5,1)}
.nav-bot .bd svg{color:var(--acInk)!important;width:25px;height:25px}.nav-bot.on .bd{transform:translateY(-3px) rotate(-8deg)}
nav.alt .rz{top:0;right:calc(50% - 22px)}
/* detay ve sayfa altı kartlar */
#detay{position:fixed;inset:0;background:var(--bg);display:flex;flex-direction:column;transform:translateY(102%);transition:transform .5s cubic-bezier(.2,.9,.2,1);z-index:20}
#detay.ac{transform:none}
.dust{display:flex;align-items:center;gap:10px;padding:12px 16px}
.dust b{display:block;font-size:17px;font-weight:800}.dust small{display:block;color:var(--mu);font-size:11.5px;font-weight:600}
#dicerik{flex:1;overflow-y:auto;padding-bottom:30px;scrollbar-width:none}#dicerik::-webkit-scrollbar{display:none}
.dfiyat{display:flex;align-items:baseline;gap:10px;padding:4px 16px}.dfiyat b{font:800 36px/1.05 var(--disp);letter-spacing:-.03em}
.distat{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:10px 16px 0}
.distat div{background:var(--card);border:1px solid var(--ln);border-radius:14px;padding:9px}.distat b{display:block;font-size:13.5px;font-weight:800;margin-top:2px}
.karar{margin:12px 16px 0;padding:13px 14px;border-radius:16px;background:var(--card);border:1px solid var(--ln);font-size:13px;line-height:1.55;font-weight:600;position:relative;overflow:hidden}
.karar::before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--mu2)}
.karar.AL::before{background:var(--up)}.karar.SAT::before{background:var(--dn)}.karar b{font-weight:800;margin-right:6px}
.dtf{display:flex;gap:6px;padding:14px 16px 0}.dtf .chip{flex:1}
.legend{padding:10px 16px 0;height:28px;font-size:11px;color:var(--mu);white-space:nowrap;overflow:hidden;font-weight:600}.legend b{color:var(--tx)}
#grafik{height:310px}
.bantkat{position:absolute;inset:0;pointer-events:none;z-index:3;overflow:hidden}
.bant{position:absolute;border-left:2px solid;border-top:0;border-bottom:0;border-radius:2px;will-change:top,height}
.dok{position:absolute;width:7px;height:7px;margin:-3.5px 0 0 -3.5px;border-radius:50%;box-shadow:0 0 0 2px var(--bg)}
.bant span{position:absolute;right:4px;top:50%;transform:translateY(-50%);font-size:9.5px;font-weight:800;color:#06121a;padding:1px 6px;border-radius:6px;white-space:nowrap;letter-spacing:.02em}
.gsec{display:flex;gap:6px;padding:8px 16px 0;overflow-x:auto;scrollbar-width:none}.gsec::-webkit-scrollbar{display:none}.gsec .chip{padding:6px 10px;font-size:11.5px}
.ayr{width:1px;background:var(--ln);flex:none;margin:4px 2px}
.dp{padding:0 16px}
#perde{position:fixed;inset:0;background:rgba(3,6,14,.55);backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:opacity .35s;z-index:29}#perde.ac{opacity:1;pointer-events:auto}
.sheet{position:fixed;left:0;right:0;bottom:0;max-height:90%;overflow-y:auto;background:var(--cardS);border-radius:28px 28px 0 0;border-top:1px solid var(--ln);padding:10px 18px calc(22px + env(safe-area-inset-bottom));transform:translateY(105%);transition:transform .45s cubic-bezier(.2,.9,.2,1);z-index:30}
.sheet.ac{transform:none}.tutamak{width:42px;height:5px;border-radius:9px;background:var(--ln);margin:0 auto 16px}
.sheet h2{margin:0 0 4px;font:800 22px/1.15 var(--disp);letter-spacing:-.02em}
.toast{position:fixed;left:50%;top:16px;transform:translate(-50%,-30px);background:var(--tx);color:var(--bg);font-weight:800;font-size:13px;padding:11px 16px;border-radius:14px;opacity:0;transition:all .35s cubic-bezier(.3,1.4,.5,1);z-index:40;pointer-events:none;box-shadow:0 14px 30px -10px rgba(0,0,0,.5);max-width:90%;text-align:center}
.toast.ac{opacity:1;transform:translate(-50%,0)}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}

/* ===== SOHBET: ana ekran ===== */
#sohbet{position:fixed;inset:0;display:flex;flex-direction:column;background:var(--bg);z-index:2}
.sbas{flex:none;display:flex;align-items:center;gap:10px;padding:12px 14px 10px;background:var(--card);border-bottom:1px solid var(--ln)}
.sbas .sav{width:40px;height:40px;flex:none;position:relative}.sbas .sav svg{width:40px;height:40px}
.sbas .sav::after{content:"";position:absolute;right:-1px;bottom:-1px;width:11px;height:11px;border-radius:50%;background:var(--mu2);box-shadow:0 0 0 2.5px var(--card)}
.sbas .sav.on::after{background:var(--up)}
.sbas .sad{flex:1;min-width:0}.sbas .sad b{display:block;font:700 16.5px/1.15 var(--disp)}
.sbas .sad small{display:block;font-size:11.5px;color:var(--mu);font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.spill{display:flex;flex-direction:column;align-items:flex-end;padding:5px 10px;border-radius:12px;background:var(--card2);font-size:11px;font-weight:700;color:var(--mu);line-height:1.2}
.spill b{font-size:13px;color:var(--tx);font-variant-numeric:tabular-nums}
#sohbet .bant2{margin:0;flex:none}
#slog{flex:1;overflow-y:auto;padding:8px 12px 16px;scrollbar-width:none;-webkit-overflow-scrolling:touch}#slog::-webkit-scrollbar{display:none}
.sgun{text-align:center;margin:16px 0 6px}.sgun span{font-size:11px;font-weight:700;color:var(--mu);background:var(--card2);padding:4px 10px;border-radius:99px}
.sb{display:flex;gap:8px;margin:6px 0;align-items:flex-end}
.sb .av2{width:28px;height:28px;flex:none;visibility:hidden}.sb .av2 svg{width:28px;height:28px}
.sb.ilk2 .av2{visibility:visible}
.sb .bal{max-width:84%;background:var(--card);border:1px solid var(--ln);border-radius:18px 18px 18px 6px;padding:10px 13px;font-size:14.5px;line-height:1.5;position:relative;min-width:0}
.sb .bal b{font-weight:800}.sb .bal a.sl{color:var(--acT);font-weight:800;cursor:pointer;text-decoration:none}
.sb.ben{justify-content:flex-end}.sb.ben .bal{background:var(--ac);color:var(--acInk);border:0;border-radius:18px 18px 6px 18px;font-weight:600}
.sb .bal.kartli{padding:0;overflow:hidden;width:84%}
.sb .zm{display:block;font-size:10.5px;color:var(--mu2);font-weight:600;margin-top:4px}
.sb.ben .zm{color:rgba(255,255,255,.7);text-align:right}
.sb.yeni2 .bal{animation:balon .38s cubic-bezier(.2,.9,.3,1.2) both}
.sb.ben.yeni2 .bal{transform-origin:100% 100%}.sb.yeni2 .bal{transform-origin:0 100%}
@keyframes balon{from{opacity:0;transform:scale(.85) translateY(8px)}}
.yaz{display:inline-flex;gap:4px;padding:4px 2px}.yaz i{width:7px;height:7px;border-radius:50%;background:var(--mu2);animation:zipla 1s infinite}
.yaz i:nth-child(2){animation-delay:.15s}.yaz i:nth-child(3){animation-delay:.3s}
@keyframes zipla{0%,60%,100%{transform:none;opacity:.5}30%{transform:translateY(-4px);opacity:1}}
/* kart parçaları (balon içinde) */
.kc{padding:12px 13px}.kc+.kc{border-top:1px solid var(--ln2)}
.kc .kb{display:flex;align-items:center;justify-content:space-between;gap:8px}
.kc .kb .baslik2{font:700 13px var(--disp);color:var(--mu)}
.kc .dev{font:700 30px/1.05 var(--disp);letter-spacing:-.02em;margin:4px 0 2px;font-variant-numeric:tabular-nums}
.kc .alan{height:58px;margin:6px -13px -12px;width:calc(100% + 26px)}
.kbtn{display:flex;gap:6px;padding:10px 12px 12px;flex-wrap:wrap;border-top:1px solid var(--ln2)}
.kbtn button{flex:1 1 auto;padding:8px 10px;border-radius:11px;background:var(--card2);font-size:12.5px;font-weight:800;color:var(--tx);white-space:nowrap}
.kbtn button.ana{background:var(--ac);color:var(--acInk)}
.ssin{display:flex;gap:10px;align-items:center;padding:11px 13px;cursor:pointer}
.ssin+.ssin{border-top:1px solid var(--ln2)}
.ssin .ad b{font-size:14.5px}.ssin .ad small{white-space:normal;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ssin .halka{width:40px;height:40px}.ssin .halka b{font-size:12.5px}
.srow{display:flex;align-items:center;gap:10px;padding:9px 13px;cursor:pointer}.srow+.srow{border-top:1px solid var(--ln2)}
.srow .ad b{font-size:14px}.srow .sag{text-align:right}.srow .sag b{display:block;font-size:13.5px;font-weight:800;font-variant-numeric:tabular-nums}.srow .sag small{font-size:12px;font-weight:800}
.ymad{margin:0;padding:0 0 0 2px;list-style:none}.ymad li{position:relative;padding:5px 0 5px 16px;font-size:13.5px;line-height:1.45}
.ymad li::before{content:"";position:absolute;left:2px;top:12px;width:6px;height:6px;border-radius:2px;background:var(--ac)}
.sdz{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}
.sdz div{background:var(--card2);border-radius:11px;padding:7px 9px}.sdz small{display:block;font-size:10.5px;color:var(--mu);font-weight:700}.sdz b{font-size:13.5px;font-weight:800}
.kc .harita{grid-template-columns:repeat(4,1fr)}
/* yazma alanı */
.salt{flex:none;background:var(--card);border-top:1px solid var(--ln);padding:8px 0 calc(10px + env(safe-area-inset-bottom))}
.soneri{display:flex;gap:7px;overflow-x:auto;padding:2px 12px 8px;scrollbar-width:none}.soneri::-webkit-scrollbar{display:none}
.soneri button{flex:none;padding:7px 12px;border-radius:99px;border:1px solid var(--ln);background:var(--bg);font-size:12.5px;font-weight:700;color:var(--tx);white-space:nowrap}
.soneri button.hs{border-color:var(--ac);color:var(--acT);background:var(--acs)}
.sgiris{display:flex;gap:8px;padding:0 12px}
.sgiris input{flex:1;min-width:0;border:1px solid var(--ln);background:var(--bg);border-radius:22px;padding:11px 16px;font-size:15px;outline:none;color:var(--tx)}
.sgiris input:focus{border-color:var(--ac)}
.sgiris button{width:44px;height:44px;border-radius:50%;background:var(--ac);color:var(--acInk);display:grid;place-items:center;flex:none;transition:transform .15s}
.sgiris button:active{transform:scale(.9)}.sgiris button svg{width:20px;height:20px}
.smenu button{display:flex;align-items:center;gap:12px;width:100%;padding:13px 4px;border-bottom:1px solid var(--ln2);font-size:15px;font-weight:700;text-align:left}
.smenu button span{width:36px;height:36px;border-radius:11px;background:var(--card2);display:grid;place-items:center;font-size:17px;flex:none}
.smenu button small{display:block;font-size:12px;color:var(--mu);font-weight:600}
/* sayfalar sohbetin üstünde açılır */
#app{position:fixed;inset:0;z-index:12;background:var(--bg);transform:translateX(104%);transition:transform .42s cubic-bezier(.2,.9,.2,1);box-shadow:-20px 0 40px -20px rgba(0,0,0,.35)}
#app.ac{transform:none}
@media (prefers-reduced-motion:reduce){.sb.yeni2 .bal,.yaz i{animation:none}#app{transition:none}}
</style></head><body>
<svg width="0" height="0" style="position:absolute"><defs>
<linearGradient id="gLogo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f7c55a"/><stop offset="1" stop-color="#e9a21f"/></linearGradient>
<linearGradient id="gSweep" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#f5b83d" stop-opacity="0"/><stop offset="1" stop-color="#f5b83d" stop-opacity=".55"/></linearGradient>
<linearGradient id="gGauge" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff6b6b"/><stop offset=".5" stop-color="#f5b83d"/><stop offset="1" stop-color="#3ddc97"/></linearGradient>
</defs></svg>
<div id="sohbet"><header class="sbas" id="sbas"></header><div id="sbant"></div><div id="slog" aria-live="polite"></div>
  <div class="salt"><div class="soneri" id="soneri"></div><div class="sgiris"><input id="sq" placeholder="Hisse kodu ya da soru yaz…" autocomplete="off" autocapitalize="characters" enterkeyhint="send">
  <button id="sgonder" aria-label="Gönder"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button></div></div></div>
<div id="app">
  <header class="ust" id="ust"></header>
  <main id="ekran"></main>
  <nav class="alt" id="nav"><span class="nav-ind" id="navInd"></span>
    <button data-e="panel"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z"/></svg>Panel</button>
    <button data-e="piyasa"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/></svg>Piyasa</button>
    <button data-e="bot" class="nav-bot"><span class="bd"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="8" width="16" height="12" rx="4"/><path d="M12 8V4.5"/><circle cx="12" cy="3.5" r="1.3" fill="currentColor"/><g class="goz" style="transform-origin:12px 14px"><circle cx="9" cy="14" r="1.4" fill="currentColor"/><circle cx="15" cy="14" r="1.4" fill="currentColor"/></g></svg></span>Bot</button>
    <button data-e="plan"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/></svg>Planlar<b class="rz" id="rz" hidden></b></button>
    <button data-e="portfoy"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5l2.6 5.3 5.9.9-4.2 4.1 1 5.8L12 16.9l-5.3 2.7 1-5.8-4.2-4.1 5.9-.9z"/></svg>Listem</button>
  </nav>
</div>
<div id="detay">
  <div class="dust"><button class="ikon" id="geri"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M15 6l-6 6 6 6"/></svg></button>
    <div style="flex:1;min-width:0;display:flex;align-items:center;gap:10px" id="dad"></div>
    <button class="ikon" id="dalarm" title="Fiyat alarmı"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 003.4 0"/></svg></button><button class="ikon" id="dyildiz">☆</button><a class="ikon" id="tv" target="_blank" rel="noopener"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M7 17L17 7M9 7h8v8"/></svg></a></div>
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
      <div class="seg" id="sekmeler" style="margin-top:18px"><button data-s="analiz">Analiz</button><button data-s="hacim">Hacim</button><button data-s="teknik">Teknik</button><button data-s="gecmis">Geçmiş</button><button data-s="haber">Haber</button></div>
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
  o.sin=o.sin.map(a=>({t:a[0],yon:a[1],tur:a[1]>0?'AL':'SAT',guven:a[2],guclu:!!a[3],fiyat:a[4],sonuc:a[5],getiri:a[6],neden:a[7]||null,saat:tarihYaz(a[0],g)}))};
V.hisseler.forEach(h=>MODLAR.forEach(m=>coz(h[m],m!=='w')));
const H=Object.fromEntries(V.hisseler.map(h=>[h.s,h]));
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tl=(x,d=2)=>x==null||isNaN(x)?'—':Number(x).toLocaleString('tr-TR',{minimumFractionDigits:d,maximumFractionDigits:d});
const yz=(x,d=2)=>x==null||isNaN(x)?'—':(x>=0?'+':'−')+tl(Math.abs(x),d)+'%';
const tlk=(x,d=0)=>x==null||isNaN(x)?'—':(x>=0?'+':'−')+tl(Math.abs(x),d)+' TL';
const yon=x=>x>=0?'up':'dn';
const D={get(k,d){try{const v=localStorage.getItem('rt_'+k);return v==null?d:JSON.parse(v)}catch(e){return d}},set(k,v){try{localStorage.setItem('rt_'+k,JSON.stringify(v))}catch(e){}}};
let fav=new Set(D.get('fav',[]));
const ayar=Object.assign({sermaye:100000,risk:1,guven:65,lik:30},D.get('ayar',{}));ayar.tema=D.get('tema4','iznik');
function temaUygula(){document.documentElement.dataset.tema=ayar.tema}temaUygula();
const TAZE={'1':30,'5':12,'g':12,'w':5},KS={'A+':0,'A':1,'B':2,'C':3},kalCls=k=>k==='A+'?'Ap':k;
let M=D.get('mod','g');if(!MODLAR.includes(M))M='g';
const birim=m=>m==='w'?'gün':'mum';
const sureYaz=(k,m)=>m==='w'?`${k} gün`:m==='g'?`${k} mum ≈ ${tl(k/4,0)} saat`:m==='5'?`${k} mum ≈ ${tl(k*5,0)} dk`:`${k} dk`;
const ne=(s,m)=>s.once===0?(m==='w'?'bugün':'son mum'):s.once+' '+birim(m)+' önce';
let tz_;function toast(x){const t=$('#toast');t.textContent=x;t.classList.add('ac');clearTimeout(tz_);tz_=setTimeout(()=>t.classList.remove('ac'),2400)}
/* logo ve ikonlar */
const LOGO=`<svg viewBox="0 0 40 40"><rect width="40" height="40" rx="11" fill="var(--ac)"/><path d="M11 28V19M17.5 28V14M24 28V21" stroke="#fff" stroke-width="3.2" stroke-linecap="round"/><path d="M27 15.5l3.5-3.5M30.5 12h-4M30.5 12v4" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
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
function isi(d){const a=Math.round((Math.min(Math.abs(d||0)/4,1)*.55+.12)*100);return `color-mix(in srgb,var(${d>=0?'--up':'--dn'}) ${a}%,transparent)`}
/* Streamlit sayfasına komut gönder: adres satırına ?bot=... yazar, sunucu işler */
function ustCalis(kod){try{const d=window.parent.document,s=d.createElement('script');s.textContent=kod;d.body.appendChild(s);return true}catch(e){return false}}
function ustGit(qs,ek){toast('Gönderiliyor…');D.set('ekran',ek||(qs.indexOf('alarm=')>=0?'portfoy':qs.indexOf('bildirim=')>=0?'profil':'bot'));if(!ustCalis('window.location.search='+JSON.stringify(qs))){try{window.top.location.search=qs}catch(e){toast('Tarayıcı izin vermedi')}}}
function yenile(){toast('Yenileniyor…');if(!ustCalis('window.location.reload()'))location.reload()}

let liste_,aktifler;
function modHazirla(m){V.hisseler.forEach(h=>{const o=h[m];if(!o)return;
  const a=o.akl.filter(s=>s.guven>=ayar.guven&&s.once<=TAZE[m]);o.akt=a.length?a[a.length-1]:null;o.sinF=o.sin.filter(s=>s.guven>=ayar.guven)})}
function hazirla(){MODLAR.forEach(modHazirla);
  liste_=V.hisseler.filter(h=>h[M]&&(h.lik||0)>=ayar.lik);
  aktifler=liste_.filter(h=>h[M].akt).sort((a,b)=>(KS[a[M].akt.kalite]-KS[b[M].akt.kalite])||(b[M].akt.guven-a[M].akt.guven)||(a[M].akt.once-b[M].akt.once));
  $('#rz').hidden=!aktifler.length;$('#rz').textContent=aktifler.length}
function yeniAkis(){const g=new Set(D.get('gorulen',[]));return V.akis.filter(o=>!g.has(o.id)).length}
function gorus(h,m){const o=h[m],s=o.akt;let th=0;for(const c of h.s)th+=c.charCodeAt(0);th+=new Date().getDate();
  const sec=a=>a[th%a.length],kucuk=x=>x?x.charAt(0).toLocaleLowerCase('tr-TR')+x.slice(1):'',temiz=x=>!/^Karne|^Öğrenen/.test(x);
  if(s){const al=s.yon>0,olay=s.sebepler[0],ek=s.sebepler.slice(1,2);
    const ger=s.arti.filter(temiz).slice(0,3),risk=s.eksi.filter(temiz)[0];
    const ga=Math.min(s.giris_alt,s.giris_ust),gu=Math.max(s.giris_alt,s.giris_ust);
    const p1=sec([`${olay}${ek.length?', ayrıca '+kucuk(ek[0]):''}.`,`${GOSTER[m]} grafikte ${kucuk(olay)}${ek.length?' ve '+kucuk(ek[0]):''}.`]);
    const p2=ger.length?sec(['Lehine olanlar: ','Sinyali destekleyen: ','Arkasında: '])+ger.map(kucuk).join(', ')+'.':'';
    const gecti=al?o.p>=s.hedef:o.p<=s.hedef;
    if(gecti){const tam=[p1,`Fiyat ${tl(o.p)} ile ilk hedefin (${tl(s.hedef)}) ${al?'üstüne çıktı':'altına indi'}; sinyalin büyük kısmı gerçekleşti, buradan yeni ${al?'alım':'satış'} için geç.`,
      al?`Elinde varsa stopu ${tl(Math.max(s.giris_alt,s.stop))} üstüne çekip ikinci hedef ${tl(s.hedef2)} için taşıyabilirsin.`:'',p2].filter(Boolean).join(' ');return{tur:s.tur,metin:tam}}
    const p3=s.durum.kod==='bolgede'?`Fiyat ${tl(o.p)} ile giriş aralığında (${tl(ga)}–${tl(gu)}).`
      :s.durum.kod==='kacti'?sec([`Fiyat ${tl(o.p)} ile giriş aralığını geçti; kovalamak yerine ${tl(gu)} civarına geri çekilme beklemek daha sağlıklı.`,`Giriş aralığı (${tl(ga)}–${tl(gu)}) kaçtı, fiyat ${tl(o.p)}; geri çekilme gelmezse bu fırsatı pas geçmek de bir seçenek.`])
      :`Fiyat ${tl(o.p)} ile ${al?'stopa':'geçersizlik seviyesine'} yaklaşıyor; ${tl(s.stop)} ${al?'altında':'üstünde'} kapanış senaryoyu bozar.`;
    const p4=al?sec([`İlk hedef ${tl(s.hedef)} (+%${tl(s.pot[0],1)}), zarar kes ${tl(s.stop)} (−%${tl(s.risk,1)}); olası kazanç riskin ${tl(s.rk,1)} katı.`,
                     `Plan: ${tl(s.hedef)}'de (+%${tl(s.pot[0],1)}) yarısını sat, ${tl(s.stop)} altında (−%${tl(s.risk,1)}) çık. Vade ${s.vade.toLocaleLowerCase('tr-TR')}, ${s.vade_sure}.`])
      :`Elinde varsa çık ya da azalt. ${tl(s.hedef)} civarına (−%${tl(s.pot[0],1)}) geri çekilme beklenir; ${tl(s.stop)} üstünde kapanış bu görüşü bozar.`;
    const p5=risk?`Dikkat: ${kucuk(risk)}.`:'';
    const p6=s.olasilik!=null?`Geçmişte benzer kurulumların %${tl(s.olasilik,0)} kadarı hedefe ulaştı.`:'';
    const p7=s.guclu?(al?' Hacimli bölgede alıcılar gerçekten iş başında.':' Hacimli bölgede satıcılar baskın.'):'';
    return{tur:s.tur,metin:[p1+p7,p2,p3,p4,p5,p6].filter(Boolean).join(' ')}}
  const Rz=o.sev.filter(x=>x[1]==='R').sort((a,b)=>a[6]-b[6])[0],Dz=o.sev.filter(x=>x[1]==='D').sort((a,b)=>b[7]-a[7])[0],Iz=o.sev.find(x=>x[1]==='I');
  const bz=z=>`${tl(z[6])}–${tl(z[7])}`;let t;
  if(Iz)t=`Fiyat ${bz(Iz)} bölgesinin içinde; bu bölge ${Iz[3]} kez tepki gördü. Bölgenin üstünde hacimli kapanış AL, altında kapanış çıkış sinyali olur.`;
  else if(Rz&&Dz){const uR=(Rz[6]/o.p-1)*100,uD=(o.p/Dz[7]-1)*100;
    if(uR<uD*0.5)t=sec([`Fiyat ${bz(Rz)} direncine %${tl(uR,1)} yaklaştı; bu bölge ${Rz[10]||Rz[3]} kez satış gördü. Hacimli kırılım gelmeden almak için erken.`,`Üstte ${bz(Rz)} direnci var (%${tl(uR,1)} yukarıda, ${Rz[3]} tepki). Burayı hacimle aşarsa AL sinyali gelir, aşamazsa geri çekilme olası.`]);
    else if(uD<uR*0.5)t=sec([`Fiyat ${bz(Dz)} desteğine %${tl(uD,1)} mesafede; burada ${Dz[11]||Dz[3]} kez alıcı çıktı. Dönüş mumu gelirse tepki alımı düşünülebilir.`,`Altta ${bz(Dz)} desteği yakın (%${tl(uD,1)}). Bu bölgeden ${Dz[3]} kez dönüş olmuş; kırılırsa satış hızlanabilir.`]);
    else t=`Fiyat iki bölge arasında: altta ${bz(Dz)} desteği (%${tl(uD,1)} aşağıda), üstte ${bz(Rz)} direnci (%${tl(uR,1)} yukarıda). Ortada net bir avantaj yok; kenarlardan birine gelince değerlendirmek daha iyi.`}
  else if(Dz)t=`Fiyat görünen tüm dirençlerin üstünde, yukarıda referans yok. En yakın destek ${bz(Dz)}; trend sürdükçe taşımak, bu bölgenin altına inişte çıkmak mantıklı.`;
  else if(Rz)t=`Fiyat görünen tüm desteklerin altında; en yakın direnç ${bz(Rz)}. Dip arayışında acele etme, önce bir dönüş yapısı oluşmalı.`;
  else t='Yakında tepki görmüş bir destek ya da direnç bölgesi yok; net sinyal için fiyatın bir yapı oluşturmasını bekle.';
  return{tur:'BEKLE',metin:t}}
/* üst bölüm */
let indX=null;
function ustCiz(){const vd=V.vade[M],gizle=['bot','portfoy','akis'].includes(ekran),yeni=yeniAkis();
  $('#ust').innerHTML=`<div class="ust1"><button class="ikon" data-geri="1" title="Sohbete dön"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M15 6l-6 6 6 6"/></svg></button><div class="logo">${LOGO}<div><b>Borsa <span>Radar</span></b><small><i class="nokta ${V.seans?'on':''}" style="margin-right:5px;vertical-align:0"></i>${V.seans?'Seans açık':'Seans kapalı'}, ${V.guncelleme} itibarıyla</small></div></div>

   <button class="ikon" data-git="akis" title="Canlı akış">${IK.zil}${yeni?`<b class="rz">${yeni>99?'99+':yeni}</b>`:''}</button>
   <button class="ikon" data-git="profil" title="Ayarlar">${IK.ayar}</button></div>
   ${gizle?'':`<div class="dilim" id="dilim"><span class="ind" id="dind"></span>${MODLAR.map(m=>`<button data-mod="${m}" class="${M===m?'on':''}">${GOSTER[m]}</button>`).join('')}</div>
   <div class="vade-bant"><span>Vade <b>${vd.ad}</b> · ${vd.sure}</span><span>${V.likit} likit hisse</span></div>`}${ekran==='panel'||ekran==='piyasa'?kayanBant():''}`;
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
   ${s.olasilik!=null?`<div class="drm" style="margin-bottom:0"><i style="background:var(--acT)"></i><span>Öğrenen model: benzer kurulumların <b style="color:var(--tx)">%${tl(s.olasilik,0)}</b>'i hedefe ulaştı</span></div>`:''}
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
   (L&&L.lot>0?`<div class="lot"><div><span class="lbl">Pozisyon · ${tl(ayar.sermaye,0)} TL · risk %${tl(ayar.risk,1)}</span><div class="mu" style="font-size:11.5px;margin-top:3px;font-weight:600">≈ ${tl(L.tutar,0)} TL · stop olursa ≈ −${tl(L.zarar,0)} TL</div></div><b>${tl(L.lot,0)} lot</b></div>`:'')+
   `<div class="dugmeler"><button class="btn ana" data-gir="gercek">İşleme girdim</button><button class="btn" data-gir="kagit">Kağıt üstünde al</button></div>`+
   (m==='1'?`<div class="drm dikkat"><i></i>1 dk sinyalleri ~15 dk gecikmeli veriye dayanır; fiyatı Midas'tan mutlaka kontrol et.</div>`:'')}
function satirH(h,alt,m=M){const o=h[m];return `<div data-h="${h.s}" data-m="${m}">${av(h.s)}<div class="ad"><b>${h.s}${o.akt?` <span class="yon ${o.akt.yon>0?'al':'sat'}">${o.akt.tur}</span> <span class="kal ${kalCls(o.akt.kalite)}">${o.akt.kalite}</span>`:''}</b><small>${alt||h.sek}</small></div>
  ${spark(kap(o))}<div class="sag"><b class="n">${tl(o.p)}</b><small class="${yon(o.d)}">${yz(o.d)}</small></div></div>`}
function zamanFark(t){const d=(Date.now()/1000-t)/60;return d<60?Math.max(1,Math.round(d))+' dk önce':d<1440?Math.round(d/60)+' sa önce':Math.round(d/1440)+' gün önce'}
function haberSatir(e){const p=e.p||0,r=p>0?'var(--up)':p<0?'var(--dn)':'var(--mu2)';
  return `<a class="hb" href="${esc(e.u||'#')}" target="_blank" rel="noopener"><span class="hp" style="background:${r}"></span><div style="min-width:0"><p>${e.s?`<b style="font-family:var(--disp)">${e.s}</b> `:''}${esc(e.metin||e.b)}</p>
   <small>${p>0?'Olumlu':p<0?'Olumsuz':'Nötr'}${e.k||e.alt?' · '+esc(e.k||String(e.alt).replace(/^Olu\w+ haber · ?/,'')):''} · ${zamanFark(e.t-(e.tip==='HABER'?10800:0))}</small></div></a>`}
function akisSatir(e,gorulen){if(e.tip==='HABER')return haberSatir(e);const R={AL:['var(--ups)','var(--up)','▲'],SAT:['var(--dns)','var(--dn)','▼'],'HACİM':['var(--was)','var(--wa)','⚡'],'DÜŞÜŞ':['var(--dns)','var(--dn)','↘'],'YÜKSELİŞ':['var(--ups)','var(--up)','↗']}[e.tip]||['var(--card2)','var(--mu)','•'];
  const tipEt=e.tip==='AL'||e.tip==='SAT'?`<span class="yon ${e.tip==='AL'?'al':'sat'}">${e.tip}</span>${e.kalite?`<span class="kal ${kalCls(e.kalite)}">${e.kalite}</span>`:''}`:`<span class="rozet ${e.tip==='HACİM'?'wa':e.tip==='DÜŞÜŞ'?'dn':'up'}" style="padding:2px 8px;font-size:10.5px">${e.tip}</span>`;
  return `<div data-h="${e.s}" data-m="${e.mod}"><span class="ai" style="background:${R[0]};color:${R[1]}">${R[2]}</span>
   <div class="ic"><div class="bas"><b>${e.s}</b>${tipEt}<span class="dl">${GOSTER[e.mod]}</span></div><p>${esc(e.metin)}</p><small>${tl(e.fiyat)} · ${esc(e.alt||'')}</small></div>
   <span class="zaman">${saatYaz(e.t,e.mod)}</span>${gorulen&&!gorulen.has(e.id)?'<span class="yeni">YENİ</span>':''}</div>`}

function ciniKart(){const b=V.bist,saat=new Date().getHours(),selam=saat<12?'Günaydın.':saat<18?'İyi günler.':'İyi akşamlar.';
  const nal=aktifler.filter(h=>h[M].akt.yon>0).length,nsat=aktifler.length-nal,en=aktifler[0];
  const yuk=liste_.filter(h=>h[M].d>0).length,dus=liste_.filter(h=>h[M].d<0).length;
  const c=[selam];
  c.push(aktifler.length?`${GOSTER[M]} grafikte <b>${aktifler.length}</b> taze sinyal var: ${nal} al, ${nsat} sat.`:`${GOSTER[M]} grafikte şu an taze sinyal yok.`);
  if(en){const s=en[M].akt;c.push(`En güçlüsü <a data-h="${en.s}" data-m="${M}">${en.s}</a> (${s.tur}, güven ${s.guven}).`)}
  if(B&&B.ayar)c.push(!B.aktif?'Bot duraklatıldı.':`Bot ${B.poz.length?B.poz.length+' pozisyonda':'pozisyonsuz'}, toplamda <b class="${yon(B.kz_yuzde||0)}">${yz(B.kz_yuzde)}</b>.`);
  const tarih=new Date().toLocaleDateString('tr-TR',{weekday:'long',day:'numeric',month:'long'});
  const d=b?(M==='w'?b.spark_w:b.spark):null,w=340,h=92;
  let cz='';if(d&&d.length>2){const y=yol(d,w,h,8);cz=`<svg class="ccz" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><defs><linearGradient id="cGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".28"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs><path class="f" d="${y} L${w},${h} L0,${h} Z"/><path class="c" pathLength="1" vector-effect="non-scaling-stroke" d="${y}"/></svg>`}
  return `<section class="kart cini" data-git="piyasa"><div class="desen"></div><div class="ic">
     <div class="ust2"><span><b>BIST 100</b> · ${tarih}</span>${b?`<span class="deg ${yon(b.d)}">${b.d>=0?'▲':'▼'} ${yz(b.d)}</span>`:''}</div>
     <div class="endeks">${b?say(b.p,0):'—'}</div>
     <div class="alt2">${V.rejim?esc(V.rejim)+' · ':''}${yuk} hisse yükseliyor, ${dus} düşüyor</div>
     <div class="gd"><i style="flex:${yuk||1};background:#3fd1bd"></i><i style="flex:${dus||1};background:#ff9a8a"></i></div></div>
    ${cz}<div class="cumle">${c.join(' ')}</div></section>`}
function kayanBant(){const l=[...liste_].sort((a,b)=>(b.lik||0)-(a.lik||0)).slice(0,24).filter(h=>h[M]&&h[M].p!=null);if(l.length<4)return'';
  const ic=l.map(h=>`<span data-h="${h.s}" data-m="${M}"><b>${h.s}</b>${tl(h[M].p)}<em class="${yon(h[M].d)}">${h[M].d>=0?'▲':'▼'}${tl(Math.abs(h[M].d),2)}%</em></span>`).join('');
  return `<div class="bant2" style="--sure:${l.length*3}s"><div class="yol2">${ic}${ic}</div></div>`}
function gunOzeti(){const b=V.bist,saat=new Date().getHours(),selam=saat<12?'Günaydın.':saat<18?'İyi günler.':'İyi akşamlar.';
  const nal=aktifler.filter(h=>h[M].akt.yon>0).length,nsat=aktifler.length-nal,en=aktifler[0];
  const c=[selam];
  if(b)c.push(`BIST 100 <b class="${yon(b.d)}">${yz(b.d)}</b> ile ${b.d>=0?'yükselişte':'düşüşte'}${V.rejim?`, piyasa ${V.rejim.toLocaleLowerCase('tr-TR')} modunda`:''}.`);
  c.push(aktifler.length?`${GOSTER[M]} grafikte <b>${aktifler.length}</b> taze sinyal var: ${nal} al, ${nsat} sat.`:`${GOSTER[M]} grafikte şu an taze sinyal yok.`);
  if(en){const s=en[M].akt;c.push(`En güçlüsü <a data-h="${en.s}" data-m="${M}">${en.s}</a> (${s.tur}, güven ${s.guven}).`)}
  if(B&&B.ayar)c.push(!B.aktif?'Bot duraklatıldı.':`Bot ${B.poz.length?B.poz.length+' pozisyonda':'pozisyonsuz'} ve toplamda <b class="${yon(B.kz_yuzde||0)}">${yz(B.kz_yuzde)}</b>.`);
  const tarih=new Date().toLocaleDateString('tr-TR',{weekday:'long',day:'numeric',month:'long'});
  return `<section class="ozet"><p class="tarih">${tarih}</p><h1>${c.map((x,i)=>`<span style="--i:${i}">${x} </span>`).join('')}</h1></section>`}
function kucukHarf(x){return x?x.charAt(0).toLocaleLowerCase('tr-TR')+x.slice(1):''}
/* RADAR: aktif sinyaller; merkeze yakın = güçlü, tarama geçince yanıp söner */
function radar(){const T=6,l=aktifler.slice(0,24),nal=l.filter(h=>h[M].akt.yon>0).length;
  const etiket=new Set(l.slice(0,6).map(h=>h.s));
  const nok=l.map(h=>{const s=h[M].akt;let a=7;for(const c of h.s)a=(a*31+c.charCodeAt(0))%360;
    const r=Math.min(44,6+(100-s.guven)*0.85),x=50+r*Math.sin(a*Math.PI/180),y=50-r*Math.cos(a*Math.PI/180),renk=s.yon>0?'var(--up)':'var(--dn)';
    return `<span class="nok${KS[s.kalite]<=1?' b':''}${x>62?' sol':''}" data-h="${h.s}" data-m="${M}" style="left:${x}%;top:${y}%;--c:${renk};--d:${(a/360*T).toFixed(2)}s">${etiket.has(h.s)?`<i>${h.s}</i>`:''}</span>`}).join('');
  return `<div class="kart radarkart"><div class="sat1"><h3 style="margin:0;font:700 17px var(--disp)">Sinyal radarı</h3><span class="lbl">${GOSTER[M]} grafik</span></div>
   <div class="radar"><svg class="iz" viewBox="0 0 100 100"><g fill="none" style="stroke:var(--ln)" stroke-width=".35">
     <circle cx="50" cy="50" r="46"/><circle cx="50" cy="50" r="31"/><circle cx="50" cy="50" r="16"/><path d="M50 4V96M4 50H96"/></g>
     <circle cx="50" cy="50" r="46" fill="none" style="stroke:var(--ac);opacity:.5" stroke-width=".5"/></svg>
    <div class="tarama"></div>${nok}<span class="merkez"></span></div>
   <div class="radar-alt"><div><b>${say(l.length)}</b><small>taze sinyal${aktifler.length>l.length?' (en güçlü 24 gösteriliyor)':''}</small></div>
    <div class="sag2"><span class="up">● ${nal} al</span><br><span class="dn">● ${l.length-nal} sat</span></div></div>
   <p class="not" style="margin:8px 0 0">Merkeze yakın nokta daha yüksek güven demek. Büyük noktalar A+ ve A kalite. Bir noktaya dokunursan hissenin grafiği açılır.</p></div>`}
/* PANEL */
function botMini(){const kz=B.kz||0,eg=(B.egri||[]).map(x=>x[1]);
  return `<div class="kart pad botmini" data-git="bot"><div class="sat1"><div class="botbas">${BOTIK}<div><b>Canlı Bot</b><small>${!B.aktif?'Duraklatıldı':V.seans?'Seansta işlem yapıyor':'Seans kapalı · bekliyor'} · bugün ${B.bugun.islem}/${B.ayar.gunluk}</small></div></div>
   <div style="text-align:right"><b class="n" style="font:800 18px var(--disp);display:block;white-space:nowrap">${tl(B.ozk,0)} TL</b><span class="rozet ${yon(kz)}" style="margin-top:3px">${yz(B.kz_yuzde)}</span></div></div>
   ${eg.length>2?`<div style="margin:10px -16px -16px">${alan(eg,{h:56})}</div>`:''}</div>`}
function ekranPanel(){const b=V.bist,yuk=liste_.filter(h=>h[M].d>0).length,dus=liste_.filter(h=>h[M].d<0).length,top=yuk+dus||1,BT=V.bot[M]||{};
  const ap=aktifler.filter(h=>KS[h[M].akt.kalite]<=1).length;
  let x=(ayar.tema==='gece'||ayar.tema==='neon')?radar():ciniKart();
  const BTk=(B&&B.egri||[]).map(e=>e[1]);
  const ciniVar=!(ayar.tema==='gece'||ayar.tema==='neon');
  if(ciniVar)x+=(B&&B.ayar)?botMini():'';else x+=`<div class="ikili"><div class="kart mini" data-git="piyasa"><span class="lbl">BIST 100</span><b>${b?tl(b.p,0):'—'}</b><span class="${yon(b?b.d:0)}" style="font-weight:800;font-size:12.5px">${b?yz(b.d):''}</span>${b?alan(M==='w'?b.spark_w:b.spark,{h:34}):''}</div>
    <div class="kart mini" data-git="bot"><span class="lbl">Canlı bot</span><b>${B&&B.ozk!=null?tl(B.ozk,0)+' TL':'—'}</b><span class="${yon(B&&B.kz_yuzde||0)}" style="font-weight:800;font-size:12.5px">${B?yz(B.kz_yuzde):''}</span>${BTk.length>2?alan(BTk,{h:34}):''}</div></div>
   <div class="kart pad" style="margin-top:10px;padding:13px 14px"><div class="genislik" style="margin-top:0"><i style="flex:${yuk};background:var(--up)"></i><i style="flex:${dus};background:var(--dn);transform-origin:right"></i></div>
    <div class="gy" style="padding:8px 0 0"><span><b class="up">${yuk}</b> hisse yükseliyor</span><span><b class="dn">${dus}</b> düşüyor</span></div></div>`;
  x+=`<div class="kpi"><div class="tile" data-git="plan"><span class="ik" style="background:var(--acs);color:var(--acT)">${IK.hedef}</span><div><b>${say(aktifler.length)}</b><small>Taze plan</small></div></div>
    <div class="tile" data-git="plan"><span class="ik" style="background:var(--was);color:var(--wa)">${IK.yildiz}</span><div><b>${say(ap)}</b><small>A+ / A kalite</small></div></div>
    <div class="tile" data-git="bot"><span class="ik" style="background:var(--ups);color:var(--up)">${IK.kupa}</span><div><b>${BT.n?say(BT.kazanma,0,'%'):'—'}</b><small>Test kazanma</small></div></div>
    <div class="tile" data-git="bot"><span class="ik" style="background:${(BT.getiri||0)>=0?'var(--ups)':'var(--dns)'};color:${(BT.getiri||0)>=0?'var(--up)':'var(--dn)'}">${IK.grafik}</span><div><b class="${yon(BT.getiri||0)}">${BT.n?yz(BT.getiri,1):'—'}</b><small>Test getirisi</small></div></div></div>`;
  const en=aktifler.slice(0,10);
  x+=`<div class="bolum"><h3>En iyi kurulumlar</h3><a data-git="plan">Tümünü gör</a></div>`;
  x+=en.length?`<div class="yatay">${en.map(h=>{const s=h[M].akt,al=s.yon>0;return `<div class="kart skart ${al?'':'sat'}" data-h="${h.s}" data-m="${M}">
      <div class="sat1"><div class="satir" style="gap:10px;flex-wrap:nowrap">${av(h.s,38)}<div><b style="font-size:15px;font-weight:800">${h.s}</b><div style="margin-top:2px"><span class="yon ${al?'al':'sat'}">${s.tur}</span> <span class="kal ${kalCls(s.kalite)}">${s.kalite}</span></div></div></div>${halka(s.guven,al)}</div>
      <div class="neden">${esc(s.sebepler[0])}</div>
      <div class="uc"><div><small>Giriş</small><b>${tl(s.giris_ust)}</b></div><div><small>H1</small><b class="up">+${tl(s.pot[0],1)}%</b></div><div><small>Stop</small><b class="dn">−${tl(s.risk,1)}%</b></div></div></div>`}).join('')}</div>`
    :`<div class="bos"><b>Bu dilimde taze plan yok</b>Diğer zaman dilimlerine bak ya da güven eşiğini düşür.</div>`;
  const hbl=V.akis.filter(e=>e.tip==='HABER').slice(0,4);
  if(hbl.length)x+=`<div class="bolum"><h3>Önemli haberler</h3><a data-git="akis" data-afh="1">Tümü</a></div><div class="kart">${hbl.map(haberSatir).join('')}</div>`;
  const g=new Set(D.get('gorulen',[]));const ak=V.akis.filter(e=>e.tip!=='HABER'&&(!(e.tip==='AL'||e.tip==='SAT')||e.guven>=ayar.guven)).slice(0,5);
  x+=`<div class="bolum"><h3>Canlı akış</h3><a data-git="akis">Tümü</a></div>`+(ak.length?`<div class="kart akis">${ak.map(e=>akisSatir(e,g)).join('')}</div>`:`<div class="bos">Henüz olay yok</div>`);
  if(V.sektorler.length){const s=V.sektorler.filter(k=>k.ad!=='Diğer');
    x+=`<div class="bolum"><h3>Sektör para akışı</h3><a data-git="sektor">Detay</a></div><div class="kart pad">${s.slice(0,6).map(k=>`<div style="padding:6px 0;cursor:pointer" data-sek="${esc(k.ad)}"><div class="sat1" style="font-size:13px;font-weight:700"><span>${esc(k.ad)}</span><span class="${yon(k.akis)}" style="font-weight:800">${k.akis>=0?'+':'−'}${tl(Math.abs(k.akis*100),0)}%</span></div>
      <div class="akisbar"><i class="${k.akis>=0?'':'sol'}" style="${k.akis>=0?`left:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--up)`:`right:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--dn)`}"></i></div></div>`).join('')}</div>`}
  const ls=[...liste_].sort((a,b)=>(b.lik||0)-(a.lik||0)).slice(0,30);
  x+=`<div class="bolum"><h3>Isı haritası</h3><span class="lbl">en likit 30</span></div><div class="harita">${ls.map((h,i)=>`<div data-h="${h.s}" data-m="${M}" style="background:${isi(h[M].d)};animation-delay:${i*15}ms"><b>${h.s}</b><span>${yz(h[M].d,1)}</span></div>`).join('')}</div>`;
  return x}

/* AKIŞ */
let af=D.get('af','tumu'),adl=D.get('adl','tumu');
function ekranAkis(){const g=new Set(D.get('gorulen',[]));
  let l=V.akis.filter(e=>(adl==='tumu'||e.mod===adl)&&(af==='tumu'||(af==='sinyal'&&(e.tip==='AL'||e.tip==='SAT'))||(af==='hacim'&&e.tip==='HACİM')||(af==='hareket'&&(e.tip==='DÜŞÜŞ'||e.tip==='YÜKSELİŞ'))||(af==='haber'&&e.tip==='HABER')));
  l=l.filter(e=>!(e.tip==='AL'||e.tip==='SAT')||e.guven>=ayar.guven);
  const c=(k,a,v,x)=>`<button class="chip${v===k?' on':''}" data-${x}="${k}">${a}</button>`;
  const x=`<div class="bolum" style="margin-top:8px"><h3>Canlı akış</h3><span class="lbl">${l.length} olay</span></div>
   <div class="chips">${c('tumu','Tümü',af,'af')}${c('sinyal','Sinyaller',af,'af')}${c('hacim','⚡ Hacim patlaması',af,'af')}${c('hareket','Sert hareket',af,'af')}${c('haber','Haberler',af,'af')}</div>
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
    <div class="mu" style="font-size:12px;margin-top:3px;font-weight:600">${k.n} hisse · ort. ${yz(k.d)} · ${tl(Math.abs(k.tl),0)} mn TL net</div>
    <div class="akisbar"><i class="${k.akis>=0?'':'sol'}" style="${k.akis>=0?`left:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--up)`:`right:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--dn)`}"></i></div>
    <div class="chips" style="margin:12px -16px 0;padding:0 16px">${k.hisseler.map(s=>H[s]&&H[s].g?`<button class="chip" data-h="${s}" data-m="g">${s} <span class="${yon(H[s].g.d)}">${yz(H[s].g.d,1)}</span></button>`:'').join('')}</div></div>`).join('');
  const c=(k,a)=>`<button class="chip${mf===k?' on':''}" data-mf="${k}">${a}</button>`,o=(k,a)=>`<option value="${k}"${ms===k?' selected':''}>${a}</option>`;
  return x+`<div class="ara">${IK.ara}<input id="q" placeholder="Hisse ara (THYAO, ASELS…)" value="${esc(q)}" autocomplete="off"></div>
   ${sekSec?`<div class="chips"><button class="chip on" data-sektemizle="1">${esc(sekSec)} ✕</button></div>`:''}
   <div class="chips">${c('tumu','Tümü')}${c('plan','Planı olan')}${c('hacim','Hacimli')}${c('alici','Alıcılı')}${c('form','Formasyon')}${c('fav','★ Favori')}</div>
   <div class="sirala"><span>${liste_.length} hisse${M==='1'||M==='5'?' · en likitler':''}</span><select id="ms">${o('degisim','Değişim')}${o('hacim','Göreli hacim')}${o('alici','Alıcı baskısı')}${o('likidite','İşlem hacmi')}${o('ad','A-Z')}</select></div>
   <div id="pliste">${piyasaIcerik()}</div>`}

/* CANLI BOT */
let bt=D.get('bt2','term'),botChart=null;
const SEBEP_R={'Momentum kayboldu':'wa','Olumsuz haber':'wa','Piyasa sert düştü':'wa','Kâr koruma stopu':'up','İz süren stop (kârda)':'up',H1:'up',H2:'up',H3:'up','Stop':'dn','Başabaş stop':'','İz süren stop':'up','Süre doldu':'wa','SAT sinyali':'wa','Gün sonu':'wa','Elle kapatıldı':''};
function ekranBot(){const a=B.ayar,kz=B.kz||0;
  const durum=!B.aktif?['wa','wa','Duraklatıldı']:V.seans?['up','on','Canlı işlemde']:['','','Seans kapalı · bekliyor'];
  let x=`<div class="kart bothero"><div class="pad" style="padding-bottom:0;position:relative;z-index:1">
    <div class="sat1"><div class="botbas">${BOTIK}<div><b>Canlı Bot</b><small>${GOSTER[a.dilim]}${a.hizli&&a.dilim==='g'?' + 5 dk':''} · ${V.vade[a.dilim].ad} · ${B.baslangic}'ten beri</small></div></div><span class="rozet ${durum[0]}"><i class="nokta ${durum[1]}"></i>${durum[2]}</span></div>
    <div class="lbl" style="margin-top:18px">Toplam değer · ${tl(a.butce,0)} TL sanal bütçe</div>
    <div class="buyuk n">${say(B.ozk,0,'','')} <span style="font-size:22px;color:var(--mu)">TL</span></div>
    <div class="satir" style="margin-top:6px"><span class="rozet ${yon(kz)}">${kz>=0?'▲':'▼'} ${tlk(kz)} · ${yz(B.kz_yuzde)}</span>${B.bist!=null?`<span class="rozet">BIST100 aynı dönem ${yz(B.bist)}</span>`:''}${B.ogren?`<span class="rozet" data-bt="analiz" style="cursor:pointer">🧠 ${B.ogren.seviye.ad} · ${tl(B.ogren.n,0)} ders</span>`:''}</div></div>
   <div id="botGrafik"></div>
   ${botDurum()}
   <div class="botalt"><div><small>Bugün</small><b>${B.bugun.islem}<span class="mu" style="font-size:12px">/${a.gunluk}</span></b><small>işlem</small></div><div><small>Açık</small><b>${B.poz.length}<span class="mu" style="font-size:12px">/${a.acik}</span></b><small>pozisyon</small></div><div><small>Nakit</small><b>${tl(B.nakit,0)}</b><small>TL</small></div></div>
   <div class="dugmeler"><button class="btn" data-bot="${B.aktif?'durdur':'baslat'}">${B.aktif?IK.dur+' Duraklat':IK.bas+' Başlat'}</button><button class="btn ana" data-botayar="1">${IK.ayar} Bot ayarları</button></div>${B.ayar&&(B.ayar.risk>1.5||B.ayar.guven<65||!B.ayar.piyasa_filtre||B.ayar.kalite==='B'||B.ayar.kalite==='C'||!B.ayar.coklu_onay)?`<div class="kart pad" style="margin:12px 0 0;border-color:var(--wa)"><b style="font:700 14px var(--disp)">Ayarların çok agresif</b><p class="not" style="margin:6px 0 10px">Risk %${tl(B.ayar.risk,1)}, güven ${B.ayar.guven}+, kalite ${B.ayar.kalite}+${B.ayar.piyasa_filtre?'':', piyasa filtresi kapalı'}. Bu ayarlarla bot zayıf sinyallere de girer, kayıplar büyür. Önerilen: risk %1, güven 65+, kalite A+, filtreler açık.</p><button class="btn ana" data-bot="onerilen">Önerilen ayarlara geç</button></div>`:''}</div>`;
  x+=taniKart()+kayitSerit();
  const b=(k,t)=>`<button data-bt="${k}" class="${bt===k?'on':''}">${t}</button>`;
  x+=`<div class="seg" style="margin-top:16px">${b('term','Terminal')}${b('ozet','Özet')}${b('poz','Pozisyon'+(B.poz.length?' · '+B.poz.length:''))}${b('islem','İşlemler')}${b('yaris','Yarış')}${b('analiz','Analiz')}${b('gun','Günlük')}${b('log','Kayıt')}</div><div>${({term:botTerminal,ozet:botOzet,poz:botPoz,islem:botIslem,yaris:botYaris,analiz:botAnaliz,gun:botGun,log:botLog}[bt]||botOzet)()}</div>`;
  return x}
function kayitSerit(){const k=B.kayit||{tip:'yerel'};
  if(k.tip==='github'&&k.hazir&&!k.hata)return `<div class="kayit ok" data-kayitbilgi="1"><span class="ki">☁</span><div style="flex:1">Kalıcı kayıt açık<small>GitHub · ${esc(k.dal)} dalı · ${k.son?'son kayıt '+k.son:'ilk kayıt bekleniyor'}</small></div><span class="mu">›</span></div>`;
  if(k.tip==='github')return `<div class="kayit hata" data-kayitbilgi="1"><span class="ki">!</span><div style="flex:1">GitHub'a kaydedilemiyor<small>${esc(k.hata||'Bağlantı bekleniyor')}</small></div><span class="mu">›</span></div>`;
  return `<div class="kayit uyar" data-kayitbilgi="1"><span class="ki">⚠</span><div style="flex:1">Kalıcı kayıt kapalı<small>Uygulama yeniden başlarsa bot geçmişi silinir · kurmak için dokun</small></div><span class="mu">›</span></div>`}
function kayitBilgi(){const k=B.kayit||{tip:'yerel'};$('#form').onclick=null;
  const durum=k.tip==='github'?(k.hazir&&!k.hata?`<div class="kayit ok" style="cursor:default"><span class="ki">☁</span><div>Bağlı: ${esc(k.repo)}<small>${esc(k.dal)} dalındaki bot_canli.json · ${k.son?'son kayıt '+k.son:'ilk kayıt bekleniyor'}</small></div></div>`
    :`<div class="kayit hata" style="cursor:default"><span class="ki">!</span><div>Hata<small>${esc(k.hata||'Bağlantı bekleniyor')}</small></div></div>`):'';
  $('#form').innerHTML=`<div class="tutamak"></div><h2>Kalıcı kayıt</h2><p class="acik-not">Bot geçmişi GitHub deponda ayrı bir <b>bot-veri</b> dalında saklanır. Ayrı dal olduğu için site yeniden başlamaz; app.py güncellesen bile geçmiş kaybolmaz.</p>${durum}
   <div class="bolum" style="margin-top:18px"><h3>${k.tip==='github'?'Kurulum adımları':'Telefondan 3 adımda kur'}</h3></div>
   <ol class="adimlar">
    <li>GitHub'da <b>Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token</b>. Repository access: <b>Only select repositories</b> → bu sitenin deposu. Permissions → <b>Contents: Read and write</b>. Oluştur ve token'ı kopyala.</li>
    <li>Streamlit'te uygulamanın <b>⋮ → Settings → Secrets</b> bölümüne şunu yapıştır (kendi bilgilerinle):<span class="kod">GITHUB_TOKEN = "github_pat_..."
GITHUB_REPO = "kullanici-adin/didactic-barnacle"</span></li>
    <li><b>Save</b>'e bas. Uygulama kendini yeniden başlatır; Bot ekranında yeşil “Kalıcı kayıt açık” yazısını görürsün.</li></ol>
   <p class="not">Token sadece bu depoya ve sadece dosya yazma iznine sahip olur. Bot verisi her işlemde ve seans boyunca 10 dakikada bir kaydedilir. Şu anki geçmiş, kurulumdan sonra ilk kayıtta GitHub'a taşınır (uygulama araya yeniden başlamazsa).</p>
   <div class="dugmeler" style="padding:8px 0 0"><button class="btn" id="kb_kapat">Tamam</button></div>`;
  sheetAc();$('#kb_kapat').onclick=sheetKapat}
function taniKart(){const t=B.tani;if(!t)return `<div class="kart pad" style="margin-top:12px"><b style="font:700 15px var(--disp)">Bot ne yapıyor?</b><p class="not" style="margin:6px 0 0">İlk tarama sürüyor. Tam tarama birkaç dakika alır; bot ilk taramadan sonra karar vermeye başlar.</p></div>`;
  const ad={guven:'güven eşiğinin altında',kalite:'kalite yetersiz',haber:'olumsuz haber',gorulen:'zaten değerlendirildi',aralik:'fiyat giriş aralığı dışında',limit:'günlük işlem ya da pozisyon limiti dolu',elde:'hisse zaten elde',lot:'bütçe/lot yetmedi',mtf:'üst zaman dilimi ya da günlük trend onaylamadı',bekleyen:'fiyat kaçtı, limit emir bırakıldı',adim:'kuruşluk hisse (fiyat adımı stopa göre çok büyük)',ogrenme:'botun kendi geçmişinde kaybettiren kurulum/hisse'};
  const nl=Object.entries(t.neden||{}).sort((a,b)=>b[1]-a[1]);
  let ana;if(t.mesaj)ana=t.mesaj;
  else if(t.giris)ana=`Son taramada ${t.giris} yeni işleme girdi.`;
  else if(!t.sinyal)ana=`${B.ayar?GOSTER[B.ayar.dilim]:''} grafikte şu an taze AL sinyali yok. Bot her ~2 dakikada bir tarıyor; bir mum kapanıp sinyal oluşunca girecek.`;
  else ana=`${t.sinyal} taze AL sinyali bulundu ama hiçbiri şartları sağlamadı.`;
  return `<div class="kart pad" style="margin-top:12px"><div class="sat1"><b style="font:700 15px var(--disp)">Bot ne yapıyor?</b><span class="lbl">son tarama ${B.son_tik?B.son_tik.split(' ')[1]:'—'}</span></div>
   <p style="margin:8px 0 0;font-size:13.5px;font-weight:600;line-height:1.5">${esc(ana)}</p>
   <div class="satir" style="margin-top:10px"><span class="rozet">${t.taranan} hisse tarandı</span><span class="rozet">${t.bugun} hissede bugünün verisi var</span>${t.son_mum?`<span class="rozet">son mum ${t.son_mum}</span>`:''}</div>
   ${nl.length?`<div class="bilesen" style="margin-top:4px">${nl.map(([k,v])=>`<div><div class="ust3"><span class="mu">${ad[k]||k}</span><span>${v}</span></div></div>`).join('')}</div>`:''}
   <p class="not" style="margin-top:10px">Eşikleri gevşetmek için Bot ayarlarından en düşük güveni ya da kaliteyi düşürebilirsin. Daha seyrek ama daha seçici işlem, uzun vadede daha tutarlı sonuç verir.</p></div>`}
function botDurum(){const a=B.ayar,d=B.durum||{},c=[];
  const gd=d.gun_degisim;
  if(a.gunluk_zarar>0)c.push(d.zarar_kilit?`<span class="rozet dn">Zarar limiti doldu, bugün yeni işlem yok</span>`:`<span class="rozet ${gd!=null&&gd<0?'wa':''}">Bugün ${gd==null?'—':yz(gd,1)} · limit −%${tl(a.gunluk_zarar,1)}</span>`);
  else c.push(`<span class="rozet">Günlük zarar limiti kapalı</span>`);
  if(a.piyasa_filtre)c.push(d.piyasa_kilit?`<span class="rozet dn">Piyasa düşüyor (${yz(d.bist_d,1)}), AL beklemede</span>`:`<span class="rozet up">Piyasa filtresi açık</span>`);
  return `<div class="durumlar">${c.join('')}</div>`}
function botOzet(){const s=B.st||{},az=s.n<5;
  const sk=s.skor??0,renk=sk>=60?'up':sk>=45?'wa':'dn';
  const bil=[['Kazanma oranı',s.kazanma,s.kazanma==null?'—':'%'+tl(s.kazanma,0)],['Kâr faktörü',s.pf==null?null:Math.min(s.pf/2,1)*100,s.pf==null?'—':tl(s.pf,2)],
    ['Kârlı gün oranı',s.karli_gun,s.karli_gun==null?'—':'%'+tl(s.karli_gun,0)],['Düşüş kontrolü',Math.max(0,1-Math.abs(s.dd||0)/10)*100,yz(s.dd,1)]];
  let x=`<div class="kart pad"><div class="sat1"><div><b style="font-size:15px;font-weight:800">Tutarlılık skoru</b><div class="mu" style="font-size:12px;font-weight:600">Bot ne kadar istikrarlı kâr üretiyor</div></div><span class="rozet ${az?'':renk}">${esc(s.etiket)}</span></div>
    <div class="gauge"><svg viewBox="0 0 200 112"><path d="M18 102A82 82 0 0 1 182 102" fill="none" style="stroke:var(--card2)" stroke-width="16" stroke-linecap="round"/>
     ${az?'':`<path class="gd" d="M18 102A82 82 0 0 1 182 102" fill="none" stroke="url(#gGauge)" stroke-width="16" stroke-linecap="round" pathLength="100" stroke-dasharray="${Math.max(sk,1)} 100"/>`}</svg>
     <div class="gv"><b class="${az?'mu':renk}">${az?'—':say(sk)}</b></div></div>
    <div class="mu" style="text-align:center;font-size:12.5px;font-weight:700;margin-top:6px">${az?`Skor için en az 5 kapanmış işlem gerekli · şu an ${s.n}`:'100 üzerinden'}</div>
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
function botYaris(){const y=[...(B.yaris||[])].sort((a,b)=>(b.getiri||0)-(a.getiri||0));
  if(!y.length)return `<div class="bos">Yarış verisi yok</div>`;
  let x=`<p class="acik-not">Aynı anda 4 bot çalışıyor: senin ayarlarınla çalışan ana bot ve ayarları sabit 3 rakip. Hepsi aynı bütçe ve aynı veriyle; hangi tarzın daha tutarlı kazandığını haftalar içinde görürsün.</p>
   <div class="kart">${y.map((r,i)=>`<div class="yaris-satir${i===0?' bir':''}"><span class="sira">${i+1}</span><div style="min-width:0"><b style="font-size:14.5px">${esc(r.ad)}${r.anahtar==='ana'?' <span class="rozet ac" style="padding:1px 7px;font-size:10.5px">sen</span>':''}</b>
     <div class="mu" style="font-size:11.5px;font-weight:600;margin-top:2px">${esc(r.aciklama)}</div>
     <div class="mu" style="font-size:11.5px;font-weight:600;margin-top:2px">${r.n} işlem${r.kazanma!=null?', %'+tl(r.kazanma,0)+' kazanma':''}${r.skor!=null?', tutarlılık '+r.skor:''}${r.poz?', '+r.poz+' açık':''}</div></div>
     <div style="text-align:right"><b class="${yon(r.getiri||0)}" style="font:800 17px var(--disp)">${yz(r.getiri)}</b><div class="mu" style="font-size:11px;font-weight:700">maks. düşüş ${yz(r.dd,1)}</div></div></div>`).join('')}</div>
   <div class="kart" style="margin-top:12px;padding:12px 0 4px"><div class="lbl" style="padding:0 14px">Getiri eğrileri (%)</div><div id="yarisGrafik" style="height:180px"></div>
    <div class="satir" style="padding:4px 14px 10px">${y.map((r,i)=>`<span class="rozet" style="padding:3px 8px"><i class="nokta" style="background:${YRENK[(B.yaris||[]).indexOf(r)]}"></i>${esc(r.ad)}</span>`).join('')}</div></div>
   <button class="btn kir" style="width:100%;margin-top:12px" data-yarissifirla="1">Rakip botları sıfırla</button>`;
  setTimeout(yarisGrafikKur,40);return x}
const YRENK=['#2743f0','#0c9466','#d97706','#9333ea'];let yarisChart=null;
function yarisGrafikKur(){if(yarisChart){yarisChart.remove();yarisChart=null}const el=$('#yarisGrafik');if(!el||!window.LightweightCharts)return;
  const css=getComputedStyle(document.documentElement),cv=k=>css.getPropertyValue(k).trim();
  yarisChart=LightweightCharts.createChart(el,{width:el.clientWidth,height:180,layout:{background:{type:'solid',color:'transparent'},textColor:cv('--mu'),fontFamily:cv('--govde')||'sans-serif',fontSize:10},
    grid:{vertLines:{visible:false},horzLines:{color:cv('--ln2')}},rightPriceScale:{borderVisible:false},timeScale:{borderVisible:false,timeVisible:true},handleScroll:false,handleScale:false,
    localization:{locale:'tr-TR',priceFormatter:p=>tl(p,1)+'%'}});
  (B.yaris||[]).forEach((r,i)=>{const d=(r.egri||[]).filter((x,k,a)=>!k||x[0]>a[k-1][0]);if(d.length<2)return;
    const s=yarisChart.addLineSeries({color:YRENK[i],lineWidth:i===0?3:2,priceLineVisible:false,lastValueVisible:false});s.setData(d.map(x=>({time:x[0]+10800,value:x[1]})))});
  yarisChart.timeScale().fitContent()}
function beyinKart(){const O=B.ogren;if(!O)return '';const S=O.seviye,Rf=v=>v==null?'—':(v>=0?'+':'−')+tl(Math.abs(v),2)+'R';
  let x=`<div class="bolum" style="margin-top:4px"><h3>Botun beyni</h3><span class="lbl">her sinyalden ders çıkarır</span></div><div class="kart beyin">
   <div class="sev"><span class="rozet2">${S.no}<small>sv</small></span><div><b>${esc(S.ad)}</b><span class="alt3">${tl(O.n,0)} ders${S.sonraki?` · ${esc(SEV_AD[S.no]||'')} için ${tl(S.sonraki-O.n,0)} ders daha`:' · en üst seviye'}</span></div></div>
   <div class="ilerle2"><i style="width:${Math.round(S.oran*100)}%"></i></div>
   <div class="dort"><div><b>${tl(O.n-O.canli,0)}</b><small>gölge işlem dersi</small></div><div><b>${tl(O.canli,0)}</b><small>gerçek işlem (2× ağırlık)</small></div><div><b>${tl(O.acik,0)}</b><small>şu an takipte</small></div><div><b>${tl(O.test,0)}</b><small>geçmiş test ön bilgisi</small></div></div>
   <p class="not" style="margin:12px 0 0">Bot gördüğü her AL sinyalini, girsin girmesin, gölgede takip eder: hedef mi önce geldi, stop mu? Her sonuç bir ders. Kazandıran koşullarda güveni ve lotu artırır, kaybettirenlerde azaltır, açıkça kaybettiren koşula hiç girmez.</p></div>`;
  const kb=(ad,v,n,renk)=>{const w=v==null?0:Math.min(Math.abs(v)/1*50,50);return `<div><span>${ad}<br><small class="mu" style="font-weight:600">${n} işlem</small></span><span class="cb"><i style="${v>=0?`left:50%;width:${w}%`:`right:50%;width:${w}%`};background:${v==null?'transparent':v>=0?'var(--up)':'var(--dn)'}"></i></span><b class="n ${v==null?'mu':yon(v)}" style="text-align:right">${Rf(v)}</b></div>`};
  x+=`<div class="kart pad" style="margin-top:12px"><b style="font:700 14.5px var(--disp)">Öğrenme işe yarıyor mu?</b><p class="not" style="margin:4px 0 12px">Gölge işlem açılırken botun o anki kararı yazılır, sonuç sonra gelir. Yani bu karşılaştırma geriye dönük ayarlanmış değil, dürüst.</p>
    <div class="kars">${kb('Bütün sinyaller',O.hep,O.n-O.canli)}${kb('Botun gireceği',O.sec,O.sec_n)}${kb('Güçlü bulduğu',O.guclu,O.guclu_n)}</div>
    ${O.sec_n>=O.n-O.canli?`<p class="not" style="margin-top:12px">Bot henüz hiçbir sinyali elemedi. Bir koşulda yeterince ders birikince ayırt etmeye başlayacak; fark o zaman burada görünür.</p>`:O.sec_n<30?`<p class="not" style="margin-top:12px">Anlamlı bir fark için en az 30 seçilmiş işlem gerekiyor; şimdilik ${O.sec_n}.</p>`:O.sec!=null&&O.hep!=null?`<p style="margin:12px 0 0;font-size:13px;font-weight:700" class="${O.sec>O.hep?'up':'dn'}">${O.sec>O.hep?`Seçtikleri, hepsine göre işlem başı ${tl(O.sec-O.hep,2)}R daha iyi.`:'Seçtikleri şimdilik hepsinden iyi değil; bot daha fazla veri topluyor.'}</p>`:''}</div>`;
  const G=O.gelisim||[];if(G.length>=2){const mx=Math.max(...G.flatMap(g=>[Math.abs(g.hep||0),Math.abs(g.sec||0)]),.2);
    x+=`<div class="kart pad" style="margin-top:12px;padding-bottom:26px"><div class="sat1"><b style="font:700 14.5px var(--disp)">Haftalık gelişim</b><span class="lbl"><span style="color:var(--mu2)">■</span> hepsi <span class="act">■</span> seçtikleri</span></div>
     <div class="hafta">${G.map((g,i)=>`<div><i style="height:${Math.max(3,Math.abs(g.hep)/mx*80)}%;background:${g.hep>=0?'var(--mu2)':'var(--dns)'};animation-delay:${i*50}ms"></i><i style="height:${g.sec==null?0:Math.max(3,Math.abs(g.sec)/mx*80)}%;background:${(g.sec||0)>=0?'var(--ac)':'var(--dn)'};animation-delay:${i*50+25}ms"></i><span>${g.et}</span></div>`).join('')}</div></div>`}
  const D_=[...(O.dersler||[]).filter(d=>d.iyi).slice(0,5),...(O.dersler||[]).filter(d=>!d.iyi).slice(0,5)];
  x+=`<div class="kart pad" style="margin-top:12px"><b style="font:700 14.5px var(--disp)">Çıkardığı dersler</b>`+(D_.length?D_.map(d=>`<div class="ders"><span class="di ${d.iyi?'up':'dn'}">${d.iyi?'↑':'↓'}</span><div><b>${esc(d.metin.charAt(0).toLocaleUpperCase('tr-TR')+d.metin.slice(1))} ${d.engel?'<span class="rozet dn" style="padding:1px 7px;font-size:10px;vertical-align:1px">artık girmiyor</span>':d.iyi?'<span class="rozet up" style="padding:1px 7px;font-size:10px;vertical-align:1px">lotu büyütüyor</span>':'<span class="rozet wa" style="padding:1px 7px;font-size:10px;vertical-align:1px">temkinli</span>'}</b><small>${esc(d.boyut)} · ${d.adet} deneme · %${d.kaz} kazanma · ort. ${Rf(d.E)}</small></div></div>`).join('')
     :`<p class="not" style="margin:8px 0 0">Henüz belirgin bir ders yok. Bir koşulda en az 8 deneme birikip sonuç ortalamadan belirgin ayrışınca burada görünür.</p>`)+`</div>`;
  return x}
const SEV_AD=['Çaylak','Öğrenci','Deneyimli','Usta','Uzman','Efsane'];
function botAnaliz(){const kb=B.kayip||[],kg=(V.kayip||{})[B.ayar.dilim]||[];
  const tablo=(liste,genelAd)=>liste.slice(0,5).map(bl=>`<div class="kart" style="margin-bottom:10px"><div class="sat1" style="padding:12px 14px 4px"><b style="font:700 14.5px var(--disp)">${esc(bl.boyut)}</b><span class="lbl">${genelAd} %${bl.genel}</span></div>
    <table class="tbl kayip-tbl"><tr><th>Grup</th><th>Adet</th><th>Kazanma</th><th>Ort. R</th></tr>${bl.satirlar.map((r,i)=>`<tr><td>${esc(r.ad)}${i===0?' <span class="rozet dn" style="padding:1px 7px;font-size:10px">en zayıf</span>':i===bl.satirlar.length-1?' <span class="rozet up" style="padding:1px 7px;font-size:10px">en iyi</span>':''}</td><td>${r.n}</td>
      <td class="${r.kazanma>=bl.genel?'up':'dn'}">%${r.kazanma}</td><td class="${yon(r.ortR||0)}">${r.ortR>=0?'+':''}${tl(r.ortR,2)}</td></tr>`).join('')}</table></div>`).join('');
  const og=B.ogrenme;let x=beyinKart();
  if(og){const yas=og.boyut.flatMap(b=>b.satir.filter(r=>r.yasak).map(r=>b.baslik+': '+r.ad));
    x+=`<div class="bolum" style="margin-top:4px"><h3>Gerçek işlemlerin dökümü</h3><span class="lbl">4 botun ${og.n} işlemi</span></div>
    <div class="kart pad" style="margin-bottom:12px"><p style="margin:0 0 10px;font-size:13.5px;font-weight:600;line-height:1.5">${og.n<5?'Henüz çok az işlem var. Bir koşulu kara listeye almak için en az 5 işlem görmesi gerekiyor.':yas.length?`Şu koşullarda artık işleme girmiyor: <b class="dn">${esc(yas.join(', '))}</b>. Bu gruplarda kazanma %30'un altında ve ortalama sonuç zararda.`:'Şimdilik kara listeye aldığı bir koşul yok. Bir grup en az 5 işlemde %30\'un altında kazanırsa o koşula girmeyi bırakacak.'}</p>
    ${og.boyut.map(b=>b.satir.length?`<div style="margin-top:10px"><div class="lbl" style="margin-bottom:4px">${esc(b.baslik)}</div>${b.satir.map(r=>`<div class="sat1" style="font-size:13px;padding:5px 0;border-bottom:1px solid var(--ln2)"><span style="font-weight:700">${esc(r.ad)}${r.yasak?' <span class="rozet dn" style="padding:1px 7px;font-size:10px">girmiyor</span>':''}</span><span class="n"><span class="mu">${r.n} işlem · </span><b class="${r.kaz>=50?'up':r.kaz<30?'dn':''}">%${r.kaz}</b><span class="${yon(r.R)}"> · ${r.R>=0?'+':''}${tl(r.R,2)}R</span></span></div>`).join('')}</div>`:'').join('')}</div>`}
  x+=`<p class="acik-not">Kaybeden işlemler hangi koşullarda yoğunlaşıyor? Gruplar arasında farkın en büyük olduğu boyutlar en üstte. "En zayıf" grubu kaçınmak, botu güçlendirmenin en hızlı yolu.</p>`;
  x+=`<div class="bolum" style="margin-top:6px"><h3>Botun kendi işlemleri</h3><span class="lbl">${(B.islem||[]).length} işlem</span></div>`+(kb.length?tablo(kb,'genel'):`<div class="bos">En az 8 kapanmış işlem gerekiyor. Şimdilik aşağıda geçmiş testteki sinyallere bakabilirsin.</div>`);
  x+=`<div class="bolum"><h3>Geçmiş test sinyalleri</h3><span class="lbl">${GOSTER[B.ayar.dilim]}</span></div>`+(kg.length?tablo(kg,'genel'):`<div class="bos">Derin test sonrası hazırlanır.</div>`);
  return x}
function pozNot(p){const r0=(p.giris0-p.stop0)||1e-9,koru=p.giris0+0.8*r0;
  if(p.kademe>=1)return ['🎯',`H1 alındı, kalan ${p.kalan} lot iz süren stopla taşınıyor. Stop ${tl(p.stop)}; H${p.kademe+1} hedefi ${tl(p.h[Math.min(p.kademe,2)])}.`];
  if(p.ek)return ['➕',`Kazanana ekleme yapıldı (+${p.ek[2]} lot @ ${tl(p.ek[1])}). Stop ortalama maliyette, artık risk yok. H1 (${tl(p.h[0])}) gelince yarısını satacağım.`];
  if(p.koru)return ['🛡️',`0,8R geçildi, stop kâra çekildi (${tl(p.stop)}). Trend 15 dk EMA20 üstünde kalırsa yarım lot ekleyeceğim.`];
  if(p.R!=null&&p.R<=-0.3)return ['⚠️',`Zararda (${tl(p.R,1)}R). Mum EMA20 ve VWAP altında kapanırsa stopu beklemeden çıkacağım. Son çare stop ${tl(p.stop)}.`];
  return ['📋',`Plan: fiyat ${tl(koru)} seviyesini geçerse stopu kâra çek ve yarım lot ekle; H1 (${tl(p.h[0])}) gelince yarısını sat. Stop ${tl(p.stop)}.`]}
function botTerminal(){const a=B.ayar,g=B.bugun||{},bek=B.bekleyen||[],top=(g.kz||0)+(g.acik_kz||0);
  const h=(l,v,c='')=>`<div><small>${l}</small><b class="n ${c}">${v}</b></div>`;
  let x=`<div class="kart term"><div class="termust">${h('Gün K/Z',tlk(top),yon(top))}${h('Gerçekleşen',tlk(g.kz||0),yon(g.kz||0))}${h('Açık K/Z',tlk(g.acik_kz||0),yon(g.acik_kz||0))}${h('Maruziyet','%'+tl(B.maruziyet||0,0))}${h('Bugün isabet',g.kapanan?g.kazanan+'/'+g.kapanan:'—')}${h('Bugün giriş',(g.islem||0)+'/'+a.gunluk)}</div>
   <div class="tbaslik"><b>Açık pozisyonlar</b><span class="lbl">${B.poz.length}/${a.acik} · ${a.hizli&&a.dilim==='g'?'15 dk + 5 dk':GOSTER[a.dilim]}</span></div>`;
  if(!B.poz.length)x+=`<div class="trow ts">${B.aktif?(V.seans?'Pozisyon yok. Bot taze sinyal ya da limit emirlerinin dolmasını bekliyor.':'Seans kapalı.'):'Bot duraklatıldı.'}</div>`;
  x+=B.poz.map(p=>{const lo=Math.min(p.stop0,p.stop,p.fiyat),hi=Math.max(p.h[1],p.fiyat),k=(hi-lo)||1,X=v=>Math.max(0,Math.min(100,(v-lo)/k*100)),n=pozNot(p),ust=p.fiyat>=p.giris;
    return `<div class="trow"><div class="tu"><div><b class="sym" data-h="${p.s}" data-m="${p.mod}">${p.s}</b><span class="dl">${GOSTER[p.mod]}</span><span class="kal ${kalCls(p.kalite)}" style="margin-left:6px">${p.kalite}</span>${p.ek?'<span class="tbayrak up">EKLENDİ</span>':''}${p.koru||p.kademe?'<span class="tbayrak up">KÂR KORUMALI</span>':''}${p.pk?'<span class="tbayrak wa">YARIYA İNDİ</span>':''}
       <div class="ts n">${p.kalan} lot · ort. ${tl(p.giris)} → <b class="${yon(p.fiyat-p.giris)}">${tl(p.fiyat)}</b> · ${tl(p.deger,0)} TL</div></div>
      <div class="tk"><b class="n ${yon(p.kz)}">${tlk(p.kz)}</b><small class="n ${yon(p.yuzde)}">${yz(p.yuzde)}${p.R!=null?' · '+(p.R>=0?'+':'')+tl(p.R,1)+'R':''}</small></div></div>
     <div class="tbar"><i style="left:${Math.min(X(p.giris),X(p.fiyat))}%;width:${Math.abs(X(p.fiyat)-X(p.giris))}%;background:var(--${ust?'up':'dn'})"></i><span style="left:${X(p.stop)}%;background:var(--dn)"></span><span style="left:${X(p.giris)}%"></span><span style="left:${X(p.h[0])}%;background:var(--up)"></span><span style="left:${X(p.h[1])}%;background:var(--up)"></span><em style="left:${X(p.fiyat)}%"></em></div>
     <div class="tetk n"><span class="dn">stop ${tl(p.stop)}</span><span>${p.saat.split(' ')[1]||p.saat} · ${p.bar} ${birim(p.mod)}</span><span class="up">H1 ${tl(p.h[0])} · H2 ${tl(p.h[1])}</span></div>
     <div class="tnot"><i>${n[0]}</i><span>${esc(n[1])}</span></div>
     <div class="ttus"><button class="btn" data-h="${p.s}" data-m="${p.mod}">${IK.grafik} Grafik</button><button class="btn kir" data-botkapat="${p.id}">Piyasadan kapat</button></div></div>`}).join('');
  x+=`</div>`;
  x+=`<div class="kart term"><div class="tbaslik"><b>Bekleyen limit emirler</b><span class="lbl">${bek.length}</span></div>`+(bek.length?bek.map(b=>`<div class="trow"><div class="tu"><div><b class="sym" data-h="${b.s}" data-m="${b.mod}">${b.s}</b><span class="dl">${GOSTER[b.mod]}</span><span class="kal ${kalCls(b.kalite)}" style="margin-left:6px">${b.kalite}</span>
       <div class="ts n">LİMİT AL ${tl(b.alt)}–${tl(b.ust)} · stop ${tl(b.stop)} · H1 ${tl(b.hedef)}</div><div class="ts">${esc(b.sebep)}</div></div><div class="tk"><small class="mu">${b.kalan_dk} dk</small><small class="mu">güven ${b.guven}</small></div></div></div>`).join(''):`<div class="trow ts">Bekleyen emir yok. Sinyal geldiğinde fiyat kaçmışsa bot kovalamaz; aralığa geri çekilmesini bekleyen limit emir bırakır.</div>`)+`</div>`;
  const ed=(B.log||[]).filter(l=>l[3]&&['al','kar','kazanc','zarar','bilgi'].includes(l[1])).slice(0,25);
  const tip=l=>l[1]==='al'?['al','AL']:['kar','kazanc','zarar'].includes(l[1])?['sat','SAT']:['emir','EMİR'];
  x+=`<div class="kart term"><div class="tbaslik"><b>Emir defteri</b><span class="lbl">son ${ed.length}</span></div>`+(ed.length?ed.map(l=>{const t=tip(l);return `<div class="ed" data-h="${l[3]}" style="cursor:pointer"><span class="z">${(l[0].split(' ')[1]||l[0])}</span><span class="etk2 ${t[0]}">${t[1]}</span><p><b>${l[3]}</b> ${esc(l[2])}</p></div>`}).join(''):`<div class="trow ts">Henüz emir yok.</div>`)+`</div>`;
  return x+(B.poz.length>1?`<button class="btn kir" style="width:100%" data-bothepsi="1">Tüm pozisyonları kapat</button>`:'')}
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
function botLog(){const R={zarar:['var(--dns)','var(--dn)','⛔'],al:['var(--acs)','var(--acT)','＋'],kar:['var(--ups)','var(--up)','◐'],kazanc:['var(--ups)','var(--up)','✓'],zarar:['var(--dns)','var(--dn)','✕'],bilgi:['var(--card2)','var(--mu)','i']};
  return B.log.length?`<div class="kart log">${B.log.map(l=>{const r=R[l[1]]||R.bilgi;return `<div ${l[3]?`data-h="${l[3]}" style="cursor:pointer"`:''}><span class="li" style="background:${r[0]};color:${r[1]}">${r[2]}</span><div><p>${l[3]?`<b>${l[3]}</b> · `:''}${esc(l[2])}</p><small>${l[0]}</small></div></div>`}).join('')}</div>`:`<div class="bos">Kayıt yok</div>`}
function botGrafikKur(){if(botChart){botChart.remove();botChart=null}const el=$('#botGrafik');if(!el)return;
  const eg=(B.egri||[]).filter((x,i,a)=>!i||x[0]>a[i-1][0]);
  if(eg.length<2||!window.LightweightCharts){el.innerHTML=`<div style="height:100%;display:grid;place-items:center;color:var(--mu);font-size:12.5px;font-weight:700">Grafik bot işlem yaptıkça çizilecek</div>`;return}
  const css=getComputedStyle(document.documentElement),cv=k=>css.getPropertyValue(k).trim(),up=(B.ozk>=B.ayar.butce),iz=document.documentElement.dataset.tema==='iznik',c=iz?'#ffffff':up?'#3ddc97':'#ff6b6b';
  botChart=LightweightCharts.createChart(el,{width:el.clientWidth,height:170,layout:{background:{type:'solid',color:'transparent'},textColor:cv('--mu'),fontFamily:cv('--govde')||'sans-serif',fontSize:10},
    grid:{vertLines:{visible:false},horzLines:{color:cv('--ln2')}},rightPriceScale:{borderVisible:false,scaleMargins:{top:.15,bottom:.08}},timeScale:{borderVisible:false,timeVisible:true,secondsVisible:false},
    crosshair:{mode:0,vertLine:{color:cv('--mu2'),labelBackgroundColor:'#3b5bff'},horzLine:{color:cv('--mu2'),labelBackgroundColor:'#3b5bff'}},handleScroll:false,handleScale:false,localization:{locale:'tr-TR',priceFormatter:p=>tl(p,0)}});
  const s=botChart.addAreaSeries({lineColor:c,topColor:iz?'rgba(255,255,255,.22)':up?'rgba(12,148,102,.3)':'rgba(217,60,69,.3)',bottomColor:'rgba(0,0,0,0)',lineWidth:2.5,priceLineVisible:false});
  s.setData(eg.map(x=>({time:x[0]+10800,value:x[1]})));s.createPriceLine({price:B.ayar.butce,color:cv('--mu2'),lineStyle:2,lineWidth:1,axisLabelVisible:true,title:'bütçe'});
  botChart.timeScale().fitContent();new ResizeObserver(()=>botChart&&botChart.applyOptions({width:el.clientWidth})).observe(el)}
function botAyarAc(){const a=Object.assign({},B.ayar);
  const sec=(ad,liste,v,yazi)=>`<div class="chips" style="margin:0 0 4px;padding:0;flex-wrap:wrap">${liste.map(k=>`<button class="chip${String(v)===String(k)?' on':''}" data-sec="${ad}" data-v="${k}">${yazi?yazi(k):k}</button>`).join('')}</div>`;
  const ciz=()=>{$('#form').innerHTML=`<div class="tutamak"></div><h2>Bot ayarları</h2><p class="acik-not">Bot sanal bütçeyle gerçek seans verisinde işlem yapar; parana dokunmaz. Sonuçlar modelin canlıda ne kadar tutarlı olduğunu gösterir.</p>
    <label class="alanf"><span class="lbl">Sanal bütçe (TL)</span><input class="giris" id="b_butce" inputmode="numeric" value="${tl(a.butce,0)}"></label>
    <div class="form-ayar" style="margin-bottom:14px"><div><span class="lbl" style="display:block;margin-bottom:7px">Günlük işlem sayısı</span><div class="stepper"><button data-adim="gunluk:-1">−</button><b>${a.gunluk}</b><button data-adim="gunluk:1">+</button></div></div>
     <div><span class="lbl" style="display:block;margin-bottom:7px">Aynı anda pozisyon</span><div class="stepper"><button data-adim="acik:-1">−</button><b>${a.acik}</b><button data-adim="acik:1">+</button></div></div></div>
    <div class="alanf"><span class="lbl">Zaman dilimi (vade)</span>${sec('dilim',MODLAR,a.dilim,k=>GOSTER[k])}<div class="mu" style="font-size:12px;font-weight:600;margin-top:4px">${V.vade[a.dilim].ad} · ${V.vade[a.dilim].sure}</div></div>
    <div class="alanf"><span class="lbl">İşlem başı risk</span>${sec('risk',[0.5,1,1.5,2,3],a.risk,k=>'%'+tl(k,1))}</div>
    <div class="alanf"><span class="lbl">En düşük sinyal kalitesi</span>${sec('kalite',['A+','A','B'],a.kalite,k=>k+(k==='B'?' ve üstü':k==='A'?' ve üstü':' sadece'))}</div>
    <label class="alanf"><span class="lbl">En düşük güven: <b class="act" id="b_gv">${a.guven}</b></span><input type="range" id="b_guven" min="50" max="90" step="5" value="${a.guven}"></label>
    <div class="alanf"><span class="lbl">Günlük zarar limiti</span>${sec('gunluk_zarar',[0,2,3,5],a.gunluk_zarar,k=>+k?'%'+k:'Kapalı')}<div class="mu" style="font-size:12px;font-weight:600;margin-top:4px">Gün içinde bu kadar kayıpta bot o gün yeni işlem açmaz; açık pozisyonları takip etmeye devam eder.</div></div>
    ${[['hizli','15 dk + 5 dk birlikte tara','15 dk grafiğe ek olarak en likit 60 hissede 5 dk sinyallerine de girer (daha çok işlem; 5 dk işlemleri gün sonunda kapanır)'],['aktif_yonetim','Aktif işlem yönetimi','Kazanana ekleme, momentum kaybolunca erken çıkış, olumsuz haberde çıkış, piyasa sert düşünce yarıya indirme'],['coklu_onay','Çoklu zaman onayı','Sinyal ancak üst zaman dilimi ve günlük trend de aynı yöndeyse alınır'],['iz_stop','İz süren stop','Fiyat 1R yol alınca stop en yüksek fiyatın 2,5 ATR altını takip eder, kârı korur'],['guven_lot','Güvene göre pozisyon','Güveni yüksek sinyalde daha büyük, düşükte daha küçük pozisyon (0,5x–1,5x)']].map(([k,ad,ac])=>`<div class="alanf"><div class="anahtar ${a[k]?'on':''}" data-sec="${k}" data-v="${a[k]?0:1}"><div><b style="font-size:14px">${ad}</b><div class="mu" style="font-size:12px;font-weight:600">${ac}</div></div><span class="tg"></span></div></div>`).join('')}
    <div class="alanf"><div class="anahtar ${a.piyasa_filtre?'on':''}" data-sec="piyasa_filtre" data-v="${a.piyasa_filtre?0:1}"><div><b style="font-size:14px">Piyasa filtresi</b><div class="mu" style="font-size:12px;font-weight:600">BIST100 sert düşerken AL sinyallerine girme</div></div><span class="tg"></span></div>
     ${a.piyasa_filtre?`<div style="margin-top:8px">${sec('piyasa_esik',[-1,-1.5,-2,-3],a.piyasa_esik,k=>'BIST100 '+tl(k,1)+'%')}</div>`:''}</div>
    <div class="dugmeler" style="padding:6px 0 0"><button class="btn ana" id="b_kaydet">Kaydet</button></div>
    <button class="btn kir" style="width:100%;margin-top:10px" id="b_sifirla">Sıfırla ve yeni bütçeyle başlat</button>
    <p class="not">Bütçe değişikliği, bot henüz işlem yapmadıysa hemen uygulanır; yaptıysa sıfırlama gerekir. Giriş/çıkışta %0,05 kayma hesaba katılır. 1 ve 5 dk işlemleri gün sonunda kapatılır.</p>`};
  ciz();sheetAc();
  $('#form').onclick=e=>{const t=e.target.closest('[data-sec],[data-adim],#b_kaydet,#b_sifirla');if(!t)return;
    a.butce=parseFloat(String($('#b_butce').value).replace(/\./g,'').replace(',','.'))||a.butce;a.guven=+$('#b_guven').value;
    if(t.dataset.sec){const k=t.dataset.sec,v=t.dataset.v;a[k]=['piyasa_filtre','iz_stop','guven_lot','coklu_onay','hizli','aktif_yonetim'].includes(k)?v==='1':['risk','gunluk_zarar','piyasa_esik'].includes(k)?+v:v;ciz();baglaGv()}
    else if(t.dataset.adim){const[k,d]=t.dataset.adim.split(':');a[k]=Math.max(1,Math.min(k==='gunluk'?50:20,a[k]+ +d));ciz();baglaGv()}
    else{const qs=new URLSearchParams({bot:t.id==='b_sifirla'?'sifirla':'ayar',butce:Math.round(a.butce),gunluk:a.gunluk,acik:a.acik,risk:a.risk,guven:a.guven,dilim:a.dilim,kalite:a.kalite,
      gunluk_zarar:a.gunluk_zarar,piyasa_filtre:a.piyasa_filtre?1:0,piyasa_esik:a.piyasa_esik,iz_stop:a.iz_stop?1:0,guven_lot:a.guven_lot?1:0,coklu_onay:a.coklu_onay?1:0,hizli:a.hizli?1:0,aktif_yonetim:a.aktif_yonetim?1:0});
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
let ls=D.get('ls','izle');
function ekranListe(){const b=(k,a)=>`<button data-ls="${k}" class="${ls===k?'on':''}">${a}</button>`;
  let x=`<div class="seg">${b('izle','İzleme listem')}${b('alarm','Alarmlar'+((B.ortak&&B.ortak.alarmlar.filter(a=>!a.tetik).length)?' · '+B.ortak.alarmlar.filter(a=>!a.tetik).length:''))}${b('portfoy','Portföyüm')}</div>`;
  if(ls==='alarm')return x+alarmListe();
  if(ls==='portfoy')return x+ekranPortfoy();
  const l=V.hisseler.filter(h=>fav.has(h.s));
  if(!l.length)return x+`<div class="bos"><b>İzleme listen boş</b>Bir hissenin detayında yıldıza dokunarak listene ekle. Listendeki hisselerin sinyalleri ve alarmları burada toplanır.</div>`;
  return x+`<div class="kart liste">${l.map(h=>{const o=h[M]||h.g||h.w,g=o?gorus(h,h[M]?M:'g'):{tur:'—'};return o?satirH(h,`Bot: ${g.tur}${h.hb?` · haber ${h.hb.skor>=2?'olumlu':h.hb.skor<=-2?'olumsuz':'nötr'}`:''}`,h[M]?M:(h.g?'g':'w')):''}).join('')}</div>`}
function alarmListe(){const al=(B.ortak&&B.ortak.alarmlar)||[];
  const bekl=al.filter(a=>!a.tetik),tet=al.filter(a=>a.tetik).reverse();
  let x=`<p class="acik-not">Alarmlar sunucuda çalışır; site kapalıyken de fiyat seviyeye gelince telefonuna bildirim gelir (bildirimleri Ayarlar'dan aç). Alarm kurmak için hisse detayındaki zile dokun.</p>`;
  const sat=a=>`<div class="alarm">${av(a.s,36)}<div class="ad"><b>${a.s} <span class="mu" style="font-weight:700;font-size:12.5px">${a.tip==='ust'?'üstüne çıkınca':'altına inince'}</span></b><small>${tl(a.fiyat)}${a.not_?' · '+esc(a.not_):''}${a.tetik?` · tetiklendi ${tl(a.tetik_fiyat)}`:''}</small></div>
    <button class="ikon" data-alarmsil="${a.id}" title="Sil"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg></button></div>`;
  x+=bekl.length?`<div class="kart">${bekl.map(sat).join('')}</div>`:`<div class="bos"><b>Bekleyen alarm yok</b>Hisse detayında zil simgesine dokunup bir fiyat seviyesi seç.</div>`;
  if(tet.length)x+=`<div class="bolum"><h3>Tetiklenenler</h3></div><div class="kart">${tet.slice(0,15).map(sat).join('')}</div>`;
  return x}
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
  return temaSecici()+`<div class="bolum"><h3>Ayarlar</h3></div><div class="form-ayar">
   <label><span class="lbl">Sermaye (TL)</span><input id="a_sermaye" inputmode="numeric" value="${ayar.sermaye}"></label>
   <label><span class="lbl">İşlem başı risk %</span><input id="a_risk" inputmode="decimal" value="${ayar.risk}"></label>
   <label class="genis"><span class="lbl">Minimum güven: <b id="gv" class="act">${ayar.guven}</b></span><input type="range" id="a_guven" min="45" max="90" step="5" value="${ayar.guven}"></label>
   <label><span class="lbl">Min. günlük işlem</span><select id="a_lik">${[20,30,100,300].map(v=>`<option value="${v}"${ayar.lik==v?' selected':''}>${v} mn TL</option>`).join('')}</select></label>
   </div>
  <div class="bolum"><h3>Favoriler</h3><span class="lbl">${l.length}</span></div>`+(l.length?`<div class="kart liste">${l.map(h=>satirH(h,'Bot: '+gorus(h,M).tur)).join('')}</div>`:`<div class="bos">Hisse detayında ☆ ile ekle</div>`)+
  bildirimKart()+ogrenKart()+modelKart()+`<div class="bolum"><h3>Kurulum karnesi · ${GOSTER[M]}</h3></div><p class="acik-not">Sinyal türlerinin geçmiş testte tutma oranı. En az 15 örneği olan türlerde güven puanı otomatik ayarlanır.</p>`+
  (K.length?`<div class="kart"><table class="tbl"><tr><th>Kurulum</th><th>Adet</th><th>İsabet</th><th>Ayar</th></tr>${K.map(k=>`<tr><td>${esc(k.ad)}</td><td>${k.n}</td><td class="${(k.isabet||0)>=40?'up':'dn'}">${k.isabet==null?'—':'%'+k.isabet}</td><td class="${k.bonus>0?'up':k.bonus<0?'dn':'mu'}">${k.bonus>0?'+':''}${k.bonus}</td></tr>`).join('')}</table></div>`:`<div class="bos">Karne hazırlanıyor</div>`)+
  `<div class="bolum"><h3>Zaman dilimleri ve vade</h3></div><div class="kart"><table class="tbl"><tr><th>Grafik</th><th>Vade</th><th>Süre</th></tr>${MODLAR.map(m=>`<tr><td>${GOSTER[m]}</td><td>${V.vade[m].ad}</td><td>${V.vade[m].sure}</td></tr>`).join('')}</table></div>
  <p class="not">1 ve 5 dk analizleri en likit ${V.hisseler.filter(h=>h.hizli).length} hissede yapılır. Veriler Yahoo Finance'tan ~15 dk gecikmeli gelir. Son tarama ${V.guncelleme}${V.derin?', son derin test '+V.derin:''}. Yatırım tavsiyesi değildir.</p>`}

const TEMALAR=[['iznik','İznik','çini mavisi, turkuaz, yeni',['#edf1f4','#ffffff','#1f3fae','#08907f','#cf3f2b','#0e1c2c']],
  ['ferah','Ferah','açık, kobalt mavi',['#f3f5f9','#ffffff','#2743f0','#0c9466','#d93c45','#0b1322']],
  ['gece','Gece radarı','lacivert, kehribar, radar',['#0d1726','#132136','#f5b83d','#3ddc97','#ff6b6b','#e9eff7']],
  ['terminal','Terminal','siyah, yeşil, yoğun veri',['#06080a','#0d1115','#38d68c','#38d68c','#ff5f5f','#d6e1ea']],
  ['gazete','Gazete','kâğıt, bordo, klasik',['#f4efe4','#fffdf7','#8b1e2d','#1d6e46','#b4231c','#1c1915']],
  ['neon','Neon','mor ışıltı, cam kartlar',['#0b0d1e','#171a35','#8b7bff','#2fe0a0','#ff5c86','#eef0fb']]];
function temaSecici(){return `<div class="bolum" style="margin-top:8px"><h3>Görünüm</h3><span class="lbl">dokun, anında değişir</span></div><div class="temalar">${TEMALAR.map(([k,ad,ac,c])=>`<div class="tema${ayar.tema===k?' on':''}" data-temasec="${k}">
   <div class="onz" style="background:${c[0]}"><i class="bas" style="background:${c[5]};opacity:.85"></i><div style="display:flex;gap:6px;flex:1"><div style="flex:1;background:${c[1]};border-radius:${k==='terminal'||k==='gazete'?2:8}px;padding:7px;display:flex;flex-direction:column;gap:5px">
   <i style="background:${c[2]};width:55%"></i><i style="background:${c[3]};width:80%;opacity:.8"></i><i style="background:${c[4]};width:40%;opacity:.8"></i></div>
   <div style="width:34%;background:${c[1]};border-radius:${k==='terminal'||k==='gazete'?2:8}px;display:grid;place-items:center"><span style="width:18px;height:18px;border-radius:50%;background:${c[2]}"></span></div></div></div>
   <div class="ad2">${ad}<small>${ac}</small></div></div>`).join('')}</div>`}
function bildirimKart(){const o=B.ortak;if(!o)return'';const bl=o.bildirim||{};
  const tg=(k,ad)=>`<div class="anahtar ${bl[k]?'on':''}" data-bildirim="${k}=${bl[k]?0:1}" style="margin-top:8px"><b style="font-size:14px">${ad}</b><span class="tg"></span></div>`;
  return `<div class="bolum"><h3>Telefona bildirim</h3>${o.hata?'<span class="rozet dn">gönderilemedi</span>':''}</div><div class="kart pad">
   <ol class="adimlar" style="margin-bottom:4px"><li>Telefonuna ücretsiz <b>ntfy</b> uygulamasını kur (App Store / Google Play).</li>
    <li>Uygulamada <b>+</b> ile şu konuya abone ol:<span class="kod">${esc(o.ntfy)}</span></li><li>Aşağıdan test bildirimi gönder.</li></ol>
   ${tg('bot','Bot işlem açınca / kapatınca')}${tg('sinyal','A+ kalite yeni sinyal')}${tg('alarm','Fiyat alarmı tetiklenince')}
   <button class="btn ana" style="width:100%;margin-top:12px" data-bildirim="test">Test bildirimi gönder</button>
   ${o.gecmis&&o.gecmis.length?`<div class="lbl" style="margin:14px 0 4px">Son bildirimler</div>${o.gecmis.slice(0,5).map(g=>`<div style="font-size:12.5px;font-weight:600;padding:4px 0"><span class="mu">${g[0]}</span> ${esc(g[1])}</div>`).join('')}`:''}
   <p class="not">Konu adını bilen herkes bildirimlerini görebilir; kimseyle paylaşma.</p></div>`}
function ogrenKart(){const a=(V.adapt||{})[M];
  let x=`<div class="bolum"><h3>Hatalarından öğrendikleri · ${GOSTER[M]}</h3>${a&&a.n?`<span class="lbl">${a.n} stop incelendi</span>`:''}</div>`;
  if(!a)return x+`<div class="bos">İlk derin taramadan sonra hazırlanır.</div>`;
  x+=`<div class="kart pad"><p class="acik-not" style="margin:0 0 6px">Tutmayan her sinyal incelenir: sahte kırılım mı, stop mu dardı, piyasa mı döndü, dirence mi çarptı? En sık hataya göre ilgili kural otomatik sıkılaştırılır.</p>`;
  if(a.dagilim&&a.dagilim.length)x+=`<div class="bilesen">${a.dagilim.map(([ad,p])=>`<div><div class="ust3"><span class="mu">${esc(ad)}</span><span>%${p}</span></div><div class="bar"><i style="width:${p}%;background:linear-gradient(90deg,var(--wa),var(--dn))"></i></div></div>`).join('')}</div>`;
  x+=`<div class="lbl" style="margin:16px 0 6px">Yapılan ayarlar</div>${(a.notlar||[]).map(n=>`<div class="satir" style="align-items:flex-start;padding:5px 0;font-size:13px;font-weight:600;flex-wrap:nowrap"><span style="color:var(--acT);font-weight:800">✦</span><span>${esc(n)}</span></div>`).join('')}`;
  return x+`</div>`}
function modelKart(){const m=(V.model||{})[M];
  let x=`<div class="bolum"><h3>Öğrenen model · ${GOSTER[M]}</h3>${m&&m.aktif?'<span class="rozet up">Aktif</span>':'<span class="rozet">Beklemede</span>'}</div>`;
  if(!m)return x+`<div class="bos">Model ilk derin taramadan sonra eğitilir.</div>`;
  x+=`<div class="kart pad"><p class="acik-not" style="margin:0 0 12px">Bot geçmişteki ${m.n} sinyalin hangisinin hedefe ulaştığına bakarak hangi koşulların gerçekten işe yaradığını öğrenir ve güven puanını buna göre ayarlar.${m.neden?' <b style="color:var(--wa)">'+esc(m.neden)+'</b>':''}</p>
   <div class="istat"><div><span class="lbl">Örnek</span><b>${m.n}</b></div><div><span class="lbl">Tahmin gücü</span><b class="${(m.auc||0)>=0.58?'up':(m.auc||0)>=0.54?'wa':'dn'}">${m.auc==null?'—':tl(m.auc*100,0)}</b></div><div><span class="lbl">Genel isabet</span><b>${m.oran==null?'—':'%'+tl(m.oran,0)}</b></div></div>`;
  if(m.onemli&&m.onemli.length)x+=`<div class="lbl" style="margin:14px 0 4px">En etkili koşullar</div>${m.onemli.map(([a,w])=>`<div class="sat1" style="padding:6px 0;font-size:13px;font-weight:700"><span>${esc(a)}</span><span class="${w>=0?'up':'dn'}">${w>=0?'işe yarıyor ▲':'zarar veriyor ▼'}</span></div>`).join('')}`;
  return x+`<p class="not" style="margin-top:10px">Tahmin gücü 50 = yazı tura, 54 altı kullanılmaz, 60 üstü iyi. Model her 30 dakikada bir yeniden eğitilir ve sadece daha önce görmediği dönemde test edilerek değerlendirilir.</p></div>`}
/* çizim */
let ekran=D.get('ekran','panel');if(ekran==='bot'&&!B)ekran='panel';
function ciz(yeniEkran){hazirla();ustCiz();navCiz();
  const el=$('#ekran');el.classList.toggle('anim',!!yeniEkran&&ANIM);
  el.innerHTML=({panel:ekranPanel,akis:ekranAkis,plan:ekranPlan,piyasa:ekranPiyasa,bot:ekranBot,portfoy:ekranListe,profil:ekranProfil}[ekran]||ekranPanel)()+`<div class="uyari">VERİ ~15 DK GECİKMELİ · YATIRIM TAVSİYESİ DEĞİLDİR</div>`;
  if(yeniEkran)el.scrollTop=0;
  if(yeniEkran)sayAnim(el);
  if(!window._ilk&&ANIM){window._ilk=1;el.classList.add('ilk');setTimeout(()=>el.classList.remove('ilk'),2600)}
  if(ekran==='bot')setTimeout(botGrafikKur,30);else{if(botChart){botChart.remove();botChart=null}if(yarisChart){yarisChart.remove();yarisChart=null}}
  const qi=$('#q');if(qi)qi.oninput=e=>{q=e.target.value.toUpperCase().trim();$('#pliste').innerHTML=piyasaIcerik()};
  const si=$('#ms');if(si)si.onchange=e=>{ms=e.target.value;D.set('ms',ms);$('#pliste').innerHTML=piyasaIcerik()};
  ['sermaye','risk'].forEach(k=>{const i=$('#a_'+k);if(i)i.onchange=e=>{const v=parseFloat(String(e.target.value).replace(/\./g,'').replace(',','.'));if(v>0){ayar[k]=v;D.set('ayar',ayar);toast('Kaydedildi')}}});
  const g=$('#a_guven');if(g){g.oninput=e=>$('#gv').textContent=e.target.value;g.onchange=e=>{ayar.guven=+e.target.value;D.set('ayar',ayar);ciz()}}
  const lk=$('#a_lik');if(lk)lk.onchange=e=>{ayar.lik=+e.target.value;D.set('ayar',ayar);ciz()};
  const tm=$('#a_tema');if(tm)tm.onchange=e=>{ayar.tema=e.target.value;D.set('tema4',ayar.tema);temaUygula();ciz()}}
function git(e){ekran=e;D.set('ekran',ekran);ciz(true);sayfaAc()}
const ACILIS=Date.now();if(V.seans)setTimeout(()=>{if(!document.hidden&&!$('#form').classList.contains('ac'))yenile()},4*60*1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-ACILIS>4*60*1000)yenile()});
$('#nav').onclick=e=>{const b=e.target.closest('button');if(b)git(b.dataset.e)};
$('#ust').onclick=e=>{const t=e.target.closest('[data-geri],[data-mod],[data-git],[data-h]');if(!t)return;const d=t.dataset;
  if(d.geri)sayfaKapat();else if(d.mod){M=d.mod;D.set('mod',M);ciz()}else if(d.git)git(d.git);else if(d.h)detayAc(d.h,d.m)};
$('#ekran').onclick=e=>{const t=e.target.closest('a.hb')?null:e.target.closest('[data-temasec],[data-ls],[data-alarmsil],[data-yarissifirla],[data-bildirim],[data-pf],[data-pg],[data-mf],[data-pt],[data-af],[data-adl],[data-bt],[data-bot],[data-botayar],[data-kayitbilgi],[data-botkapat],[data-bothepsi],[data-git],[data-sek],[data-sektemizle],[data-kapat],[data-sil],[data-h]');if(!t)return;const d=t.dataset;
  if(d.temasec){ayar.tema=d.temasec;D.set('tema4',d.temasec);temaUygula();ciz();toast('Görünüm değişti')}
  else if(d.ls){ls=d.ls;D.set('ls',ls);ciz()}
  else if(d.alarmsil){if(confirm('Alarm silinsin mi?'))ustGit('?alarm=sil&id='+encodeURIComponent(d.alarmsil))}
  else if(d.bildirim){const q=d.bildirim==='test'?'?bildirim=test':'?bildirim=ayar&'+d.bildirim;ustGit(q)}
  else if(d.pf){pf=d.pf;D.set('pf',pf);ciz()}else if(d.pg){pg=d.pg;D.set('pg',pg);ciz()}else if(d.mf){mf=d.mf;D.set('mf',mf);ciz()}else if(d.pt){pt=d.pt;D.set('pt',pt);ciz()}
  else if(d.af){af=d.af;D.set('af',af);ciz()}else if(d.adl){adl=d.adl;D.set('adl',adl);ciz()}
  else if(d.bt){bt=d.bt;D.set('bt2',bt);ciz();sayAnim($('#ekran'))}
  else if(d.yarissifirla){if(confirm('Rakip botlar sıfırlansın mı? Senin botun etkilenmez.'))ustGit('?bot=yaris_sifirla')}
  else if(d.bot)ustGit('?bot='+d.bot)
  else if(d.botayar)botAyarAc()
  else if(d.kayitbilgi)kayitBilgi()
  else if(d.botkapat){if(confirm('Bu pozisyon anlık fiyattan kapatılsın mı?'))ustGit('?bot=kapat&id='+encodeURIComponent(d.botkapat))}
  else if(d.bothepsi){if(confirm('Botun tüm açık pozisyonları kapatılsın mı?'))ustGit('?bot=hepsi')}
  else if(d.git){if(d.afh){af='haber';D.set('af',af)}if(d.git==='sektor'){ekran='piyasa';pg='sektor';D.set('ekran',ekran);ciz(true)}else git(d.git)}
  else if(d.sek){sekSec=d.sek;ekran='piyasa';pg='liste';ciz(true)}else if(d.sektemizle){sekSec=null;ciz()}
  else if(d.kapat){const p=poz.find(x=>x.id==d.kapat),o=p&&H[p.s]&&H[p.s][p.mod];if(p&&o){const dv=degerlendir(p);p.kap={fiyat:o.p,realize:dv.realize-(o.p-p.giris)*(p.lot-dv.kalanLot)};D.set('poz',poz);toast('Pozisyon kapatıldı');ciz()}}
  else if(d.sil){poz=poz.filter(x=>x.id!=d.sil);D.set('poz',poz);ciz()}
  else detayAc(d.h,d.m)};

/* hisse detayı */
let chart=null,ro=null,secili=null,DM='g',sekme=D.get('sekme','analiz');
const gor=Object.assign({plan:true,vwap:true,ema:true,prof:false,sev:true,form:true},D.get('gor2',{}));
function ema(d,n){const k=2/(n+1);let e=d[0];return d.map(v=>e=v*k+e*(1-k))}
function vwapHesap(m){let gun=-1,pv=0,vv=0;return m.map(x=>{const g=Math.floor(x[0]/86400);if(g!==gun){gun=g;pv=0;vv=0}pv+=(x[2]+x[3]+x[4])/3*x[5];vv+=x[5];return vv?pv/vv:x[4]})}
function delta(m){return m.map(x=>{const r=x[2]-x[3];return r>0?x[5]*((x[4]-x[3])-(x[2]-x[4]))/r:0})}
function detayAc(s,m){const h=H[s];if(!h)return;m=m&&h[m]?m:(h[M]?M:MODLAR.find(k=>h[k]));if(!m)return;secili=s;DM=m;D.set('detay',[s,m]);hazirla();detayCiz();
  $('#detay').classList.add('ac');$('#dicerik').scrollTop=0}
function detayCiz(){const h=H[secili],o=h[DM];
  $('#tv').href='https://tr.tradingview.com/chart/?symbol=BIST%3A'+encodeURIComponent(secili);yildizCiz();
  $('#dad').innerHTML=`${av(secili,40)}<div style="min-width:0"><b>${secili}</b><small>${esc(h.sek)} · ${tl(h.lik,0)} mn TL/gün</small></div>`;
  $('#dfiyat').innerHTML=`<b class="n">${tl(o.p)}</b><span class="rozet ${yon(o.d)}">${o.d>=0?'▲':'▼'} ${yz(o.d)}</span><span class="mu" style="margin-left:auto;font-size:12px;font-weight:700">${GOSTER[DM]}</span>`;
  const vwF=o.vw?(o.p/o.vw-1)*100:null;
  $('#distat').innerHTML=`<div><span class="lbl">Hacim</span><b>${tl(o.rv,1)}x</b></div><div><span class="lbl">Alıcı</span><b class="${yon(o.ab||0)}">%${tl((1+(o.ab||0))*50,0)}</b></div>
    <div><span class="lbl">${DM==='w'?'RS 20G':'VWAP'}</span><b class="${yon(DM==='w'?(o.rs||0):(vwF||0))}">${DM==='w'?yz(o.rs,1):(vwF==null?'—':yz(vwF,1))}</b></div><div><span class="lbl">RSI</span><b>${tl(o.rsi,0)}</b></div>`;
  const g=gorus(h,DM);$('#dkarar').innerHTML=`<div class="karar ${g.tur}"><b class="${g.tur==='AL'?'up':g.tur==='SAT'?'dn':'mu'}">${g.tur}</b>${esc(g.metin)}</div>`;
  $('#dtf').innerHTML=MODLAR.map(m=>`<button class="chip${m===DM?' on':''}" data-dm="${m}" ${h[m]?'':'disabled'}>${GOSTER[m]}${h[m]&&h[m].akt?` <span style="color:${m===DM?'#fff':h[m].akt.yon>0?'var(--up)':'var(--dn)'}">●</span>`:''}</button>`).join('');
  $('#dplan').innerHTML=o.akt?`<div class="bolum"><h3>İşlem fişi</h3></div>${fis(h,DM,true)}`
   :`<div class="bolum"><h3>Tetik seviyeleri</h3><span class="lbl">${GOSTER[DM]}</span></div><div class="kart" style="padding-bottom:12px"><div class="ig"><div><small>AL tetiği</small><b class="up">${o.tetik.ust?tl(o.tetik.ust):'Yok'}</b><em class="mu">${o.tetik.ust?'üstünde kapanış':'üstte direnç yok'}</em></div>
     <div><small>Çıkış tetiği</small><b class="dn">${o.tetik.alt?tl(o.tetik.alt):'Yok'}</b><em class="mu">${o.tetik.alt?'altında kapanış':'altta destek yok'}</em></div><div><small>Vade</small><b style="font-size:12.5px">${V.vade[DM].ad}</b><em class="mu">${V.vade[DM].sure}</em></div></div></div>`;
  setTimeout(()=>grafikKur(h,DM),60);sekmeCiz()}
$('#dtf').onclick=e=>{const b=e.target.closest('[data-dm]');if(!b||b.disabled)return;DM=b.dataset.dm;D.set('detay',[secili,DM]);detayCiz()};
function kapat(){$('#detay').classList.remove('ac');sheetKapat();D.set('detay',null);setTimeout(()=>{if(chart){chart.remove();chart=null}},400)}
$('#geri').onclick=kapat;
function yildizCiz(){const b=$('#dyildiz'),on=fav.has(secili);b.textContent=on?'★':'☆';b.style.color=on?'var(--wa)':''}
$('#dyildiz').onclick=()=>{fav.has(secili)?fav.delete(secili):fav.add(secili);D.set('fav',[...fav]);yildizCiz();toast(fav.has(secili)?'Favorilere eklendi':'Favorilerden çıkarıldı')};
$('#dalarm').onclick=()=>alarmAc();
function alarmAc(){const h=H[secili],o=h[DM],p=o.p;let tip='ust',fiyat=null;
  const oner=[...o.sev.filter(s=>s[1]==='R').sort((a,b)=>a[6]-b[6]).slice(0,2).map(s=>['ust',s[6],'direnç '+tl(s[6])]),...o.sev.filter(s=>s[1]==='D').sort((a,b)=>b[7]-a[7]).slice(0,2).map(s=>['alt',s[7],'destek '+tl(s[7])])];
  if(o.akt){oner.unshift(['alt',o.akt.stop,'stop '+tl(o.akt.stop)]);oner.unshift(['ust',o.akt.hedef,'hedef '+tl(o.akt.hedef)])}
  const ciz_=()=>{$('#form').innerHTML=`<div class="tutamak"></div><h2>${secili} için alarm</h2><p class="acik-not">Şu an ${tl(p)}. Fiyat seçtiğin seviyeye gelince telefonuna bildirim gelir (Ayarlar'dan bildirimleri aç).</p>
    <div class="chips" style="margin:0 0 12px;padding:0;flex-wrap:wrap">${oner.map(([t,f,a],i)=>`<button class="chip" data-oner="${i}">${a}</button>`).join('')}</div>
    <div class="seg"><button data-atip="ust" class="${tip==='ust'?'on':''}">Üstüne çıkınca</button><button data-atip="alt" class="${tip==='alt'?'on':''}">Altına inince</button></div>
    <label class="alanf"><span class="lbl">Fiyat</span><input class="giris" id="al_fiyat" inputmode="decimal" value="${fiyat!=null?tl(fiyat):''}" placeholder="${tl(p)}"></label>
    <label class="alanf"><span class="lbl">Not (isteğe bağlı)</span><input class="giris" id="al_not" style="font-size:15px" maxlength="60" placeholder="ör. kırılırsa al"></label>
    <div class="dugmeler" style="padding:4px 0 0"><button class="btn" id="al_iptal">Vazgeç</button><button class="btn ana" id="al_kur">Alarmı kur</button></div>`;
    $('#al_iptal').onclick=sheetKapat;
    $('#al_kur').onclick=()=>{const f=parseFloat(String($('#al_fiyat').value).replace(/\./g,'').replace(',','.'));if(!(f>0)){toast('Fiyat gir');return}
      sheetKapat();ustGit('?'+new URLSearchParams({alarm:'ekle',s:secili,tip,fiyat:f,not:$('#al_not').value}).toString(),'portfoy')}};
  ciz_();sheetAc();
  $('#form').onclick=e=>{const t=e.target.closest('[data-oner],[data-atip]');if(!t)return;
    if(t.dataset.oner){const o_=oner[+t.dataset.oner];tip=o_[0];fiyat=o_[1]}else{tip=t.dataset.atip;fiyat=parseFloat(String($('#al_fiyat').value).replace(/\./g,'').replace(',','.'))||null}ciz_()}}
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
  const css=getComputedStyle(document.documentElement),cv=k=>css.getPropertyValue(k).trim(),UP=cv('--up'),DN=cv('--dn'),AC=cv('--ac');
  const hexA=(c,a)=>{const m=/^#([0-9a-f]{6})$/i.exec(c);if(!m)return c;const n=parseInt(m[1],16);return `rgba(${n>>16&255},${n>>8&255},${n&255},${a})`};
  if(ANIM){el.classList.remove('acil');void el.offsetWidth;el.classList.add('acil')}
  chart=LightweightCharts.createChart(el,{width:el.clientWidth,height:340,watermark:{visible:true,text:h.s,fontSize:54,fontFamily:cv('--disp')||'sans-serif',fontStyle:'700',color:hexA(cv('--tx'),.05),horzAlign:'center',vertAlign:'center'},handleScroll:{mouseWheel:true,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:false},layout:{background:{type:'solid',color:'transparent'},textColor:cv('--mu'),fontFamily:cv('--govde')||'sans-serif',fontSize:10},
    grid:{vertLines:{color:cv('--ln2')},horzLines:{color:cv('--ln2')}},rightPriceScale:{borderColor:cv('--ln'),scaleMargins:{top:.06,bottom:.2}},
    timeScale:{borderColor:cv('--ln'),timeVisible:m!=='w',secondsVisible:false,rightOffset:5,barSpacing:m==='1'?5:7},
    crosshair:{mode:0,vertLine:{color:cv('--mu2'),width:1,style:2,labelBackgroundColor:cv('--tx')},horzLine:{color:cv('--mu2'),width:1,style:2,labelBackgroundColor:cv('--tx')}},localization:{locale:'tr-TR',priceFormatter:p=>tl(p)}});
  const md=o.m,n=md.length,zam=md.map(x=>x[0]);
  const mum=chart.addCandlestickSeries({upColor:UP,downColor:DN,borderVisible:true,borderUpColor:UP,borderDownColor:DN,wickUpColor:hexA(UP,.75),wickDownColor:hexA(DN,.75),priceLineColor:AC,priceLineStyle:2,priceLineWidth:1});
  mum.setData(md.map(x=>({time:x[0],open:x[1],high:x[2],low:x[3],close:x[4]})));
  const hac=chart.addHistogramSeries({priceScaleId:'h',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false});chart.priceScale('h').applyOptions({scaleMargins:{top:.84,bottom:0}});
  const dl=delta(md);hac.setData(md.map((x,i)=>({time:x[0],value:x[5],color:dl[i]>=0?hexA(UP,.28):hexA(DN,.28)})));
  const cz=(r,w=1,st=0)=>chart.addLineSeries({color:r,lineWidth:w,lineStyle:st,lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false});
  const kp=md.map(x=>x[4]);const e20=cz(hexA(AC,.55),1.5),e50=cz(hexA(cv('--wa'),.6),1.5);e20.setData(ema(kp,20).map((v,i)=>({time:zam[i],value:v})));e50.setData(ema(kp,50).map((v,i)=>({time:zam[i],value:v})));
  const vw=cz(AC,1.5,2);if(m!=='w')vw.setData(vwapHesap(md).map((v,i)=>({time:zam[i],value:v})));
  const fs=[];o.form.forEach(f=>f.cizgiler.forEach(c=>{const s=cz(f.yon<0?'#ff8aa0':'#a99bff',2);s.setData([{time:c[0],value:c[1]},{time:c[2],value:c[3]}]);fs.push(s)}));
  let cl=[],bantlar=[];const lo=Math.min(...md.map(x=>x[3]))*.97,hi=Math.max(...md.map(x=>x[2]))*1.03;
  el.style.position='relative';const kat=document.createElement('div');kat.className='bantkat';el.appendChild(kat);
  const yari=Math.max(0.0015,(o.atr||0.6)/100*0.22);   // bant yarı kalınlığı: hissenin oynaklığına göre
  // Bantlar: yapı bir kez kurulur, konumları her karede grafiğin o anki fiyat/zaman eksenine göre güncellenir
  // (kaydırma, yakınlaştırma, fiyat ekseni sürükleme dahil her durumda grafikle birlikte hareket eder)
  let bantEl=[];
  function bantCiz(){if(typeof mum.priceToCoordinate!=='function'){kat.innerHTML='';bantEl=[];return}
    kat.innerHTML=bantlar.map(s=>{const g=s[2]||0,tip=s[1],r=tip==='D'?'12,148,102':tip==='R'?'217,60,69':'217,119,6';
      const ad=tip==='D'?'Destek':tip==='R'?'Direnç':'Fiyat bölgede';
      return `<div class="bant" style="background:rgba(${r},${(0.07+0.13*g).toFixed(2)});border-color:rgba(${r},${(0.45+0.45*g).toFixed(2)})"><span style="background:rgb(${r})">${ad} ${s[3]} tepki</span></div>`+
        (s[12]||[]).map(()=>`<i class="dok" style="background:rgb(${r})"></i>`).join('')}).join('');
    const bl=[...kat.querySelectorAll('.bant')],dl=[...kat.querySelectorAll('.dok')];let k=0;
    bantEl=bantlar.map((s,i)=>{const n=(s[12]||[]).length,o_={b:bl[i],d:dl.slice(k,k+n),s};k+=n;return o_});bantKonum()}
  function bantKonum(){if(!chart||!bantEl.length)return;
    const sag=(chart.priceScale('right').width&&chart.priceScale('right').width())||56,W=el.clientWidth-sag,H=el.clientHeight-26,ts=chart.timeScale();
    const xz=t=>{const x=ts.timeToCoordinate?ts.timeToCoordinate(t):null;return x==null?(t<zam[0]?-9999:null):x};
    bantEl.forEach(({b,d,s})=>{const y1=mum.priceToCoordinate(s[7]),y2=mum.priceToCoordinate(s[6]);
      if(y1==null||y2==null){b.style.display='none';d.forEach(e=>e.style.display='none');return}
      const ust=Math.min(y1,y2),boy=Math.max(5,Math.abs(y2-y1));
      if(ust>H||ust+boy<0){b.style.display='none'}else{let x0=xz(s[8]);if(x0==null)x0=0;x0=Math.max(0,Math.min(x0,W-70));
        b.style.display='';b.style.top=ust+'px';b.style.height=boy+'px';b.style.left=x0+'px';b.style.width=(W-x0)+'px'}
      (s[12]||[]).forEach(([t,pz],i)=>{const e=d[i];if(!e)return;const x=xz(t),y=mum.priceToCoordinate(pz);
        if(x==null||y==null||x<2||x>W||y<0||y>H){e.style.display='none';return}e.style.display='';e.style.left=x+'px';e.style.top=y+'px'})})}
  let bantDongu=0;const dongu=()=>{if(!chart||!el.isConnected)return;bantKonum();bantDongu=requestAnimationFrame(dongu)};bantDongu=requestAnimationFrame(dongu);
  function uyg(){[e20,e50].forEach(s=>s.applyOptions({visible:gor.ema}));vw.applyOptions({visible:gor.vwap&&m!=='w'});fs.forEach(s=>s.applyOptions({visible:gor.form}));
    cl.forEach(p=>mum.removePriceLine(p));cl=[];const ek=x=>cl.push(mum.createPriceLine(Object.assign({lineWidth:1,axisLabelVisible:false},x)));
    bantlar=[];if(gor.sev){const p=o.p,us=o.sev.filter(s=>s[1]==='R').sort((a,b)=>a[6]-b[6]).slice(0,2),al=o.sev.filter(s=>s[1]==='D').sort((a,b)=>b[7]-a[7]).slice(0,2),ic=o.sev.filter(s=>s[1]==='I').slice(0,1);
      bantlar=[...us,...ic,...al];bantlar.forEach(s=>{const c=s[1]==='D'?UP:s[1]==='R'?DN:'#d97706';
        ek({price:s[7],color:c,lineStyle:1,lineWidth:1,axisLabelVisible:s[1]!=='D'});ek({price:s[6],color:c,lineStyle:1,lineWidth:1,axisLabelVisible:s[1]==='D'})})}
    bantCiz();
    if(gor.prof&&o.prof){ek({price:o.prof.poc,color:'#ffb547',lineStyle:0,title:'POC',axisLabelVisible:true});ek({price:o.prof.vah,color:'rgba(139,147,167,.5)',lineStyle:1,title:'VAH'});ek({price:o.prof.val,color:'rgba(139,147,167,.5)',lineStyle:1,title:'VAL'})}
    const s=o.akt;if(gor.plan&&s){ek({price:s.stop,color:DN,lineStyle:0,title:'SL',axisLabelVisible:true});ek({price:s.giris_ust,color:AC,lineStyle:2,title:'GİRİŞ'});ek({price:s.giris_alt,color:AC,lineStyle:2});
      [s.hedef,s.hedef2,s.hedef3].forEach((p,i)=>ek({price:p,color:hexA(UP,1-i*.25),lineStyle:0,title:'H'+(i+1),axisLabelVisible:i===0}))}
    const bp=(B.poz||[]).find(p=>p.s===secili&&p.mod===m);if(bp){ek({price:bp.giris,color:'#22d3ee',lineStyle:0,lineWidth:2,title:'BOT',axisLabelVisible:true})}
    mum.setMarkers(gor.plan?o.sinF.filter(s=>s.t>=zam[0]&&s.t<=zam[n-1]).map(s=>({time:s.t,position:s.yon>0?'belowBar':'aboveBar',color:s.yon>0?UP:DN,shape:s.yon>0?'arrowUp':'arrowDown',text:s.tur})):[])}
  uyg();
  const ar=m==='w'?{'1A':22,'3A':66,'Tümü':n}:m==='1'?{'30dk':30,'1S':60,'3S':180,'Tümü':n}:m==='5'?{'2S':24,'1G':o.gun_bar,'Tümü':n}:{'1G':o.gun_bar,'2G':o.gun_bar*2,'Tümü':n};
  let sec=D.get('ar_'+m,Object.keys(ar)[1]);if(!ar[sec])sec=Object.keys(ar)[1];
  const arU=()=>{const k=Math.min(ar[sec],n);chart.timeScale().setVisibleLogicalRange({from:n-k-.5,to:n+4})};arU();
  const gs=$('#gsec'),t=(k,a,on)=>`<button class="chip${on?' on':''}" data-k="${k}">${a}</button>`;
  const gsc=()=>{gs.innerHTML=Object.keys(ar).map(k=>t('a:'+k,k,sec===k)).join('')+'<span class="ayr"></span>'+t('g:plan','Plan',gor.plan)+(m!=='w'?t('g:vwap','VWAP',gor.vwap):'')+t('g:ema','EMA',gor.ema)+t('g:sev','Destek / direnç',gor.sev)+t('g:form','Formasyon',gor.form)+t('g:prof','Hacim profili',gor.prof)};gsc();
  gs.onclick=e=>{const b=e.target.closest('[data-k]');if(!b)return;const[tp,k]=b.dataset.k.split(':');if(tp==='a'){sec=k;D.set('ar_'+m,k);arU()}else{gor[k]=!gor[k];D.set('gor2',gor);uyg()}gsc()};
  const ix=Object.fromEntries(md.map((x,i)=>[x[0],i]));
  const lg=i=>{const x=md[i];if(!x)return'';const d=dl[i];return `A <b>${tl(x[1])}</b> Y <b>${tl(x[2])}</b> D <b>${tl(x[3])}</b> K <b class="${x[4]>=x[1]?'up':'dn'}">${tl(x[4])}</b> · Hac <b>${tl(x[5],0)}</b> · <span class="${d>=0?'up':'dn'}">alıcı %${tl((1+d/(x[5]||1))*50,0)}</span>`};
  $('#legend').innerHTML=lg(n-1);chart.subscribeCrosshairMove(p=>{$('#legend').innerHTML=lg(p&&p.time!=null&&ix[p.time]!=null?ix[p.time]:n-1)});
  if(ro)ro.disconnect();ro=new ResizeObserver(()=>{if(chart)chart.applyOptions({width:el.clientWidth})});ro.observe(el)}

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
      <tr><td>ATR</td><td>%${tl(o.atr)}</td><td class="mu">mum oynaklığı</td></tr>
      <tr><td>ADX</td><td>${tl(o.adx,0)}</td><td class="mu">${o.adx>=25?'güçlü trend':o.adx<18?'yatay piyasa':'orta trend'}</td></tr>
      <tr><td>RSI uyumsuzluk</td><td class="${o.uyum>0?'up':o.uyum<0?'dn':''}">${o.uyum>0?'Pozitif':o.uyum<0?'Negatif':'Yok'}</td><td class="mu">${o.uyum?'dönüş habercisi':'—'}</td></tr>
      <tr><td>Son mum</td><td colspan="2" style="white-space:normal">${(o.mum||[]).length?o.mum.map(esc).join(', '):'<span class="mu">belirgin formasyon yok</span>'}</td></tr></table></div>`;
    x+=`<div class="bolum"><h3>Formasyonlar</h3></div>`+(o.form.length?`<div class="kart"><table class="tbl"><tr><th>Formasyon</th><th>Kritik</th><th>Durum</th></tr>${o.form.map(f=>`<tr><td>${esc(f.ad)}</td><td>${tl(f.ref)}</td><td class="${f.durum==='kırıldı'?(f.yon>0?'up':'dn'):'mu'}">${f.durum}</td></tr>`).join('')}</table></div>`:`<div class="bos">Formasyon yok</div>`);
    const sv=[...o.sev].sort((a,b)=>Math.abs(a[0]-o.p)-Math.abs(b[0]-o.p)).slice(0,10).sort((a,b)=>b[0]-a[0]);
    x+=`<div class="bolum"><h3>Destek ve direnç bölgeleri</h3><span class="lbl">fiyata yakınlığa göre</span></div>`+(sv.length?`<div class="kart liste">${sv.map(s=>{const g=s[2]||0,tip=s[1];
      const rk=tip==='D'?['var(--ups)','var(--up)','D']:tip==='R'?['var(--dns)','var(--dn)','R']:['var(--was)','var(--wa)','◆'];
      const uz=tip==='R'?(s[6]/o.p-1)*100:tip==='D'?(s[7]/o.p-1)*100:0;
      const det=[s[10]?s[10]+' kez satış':'',s[11]?s[11]+' kez alım':''].filter(Boolean).join(', ');
      return `<div style="cursor:default"><span class="avatar" style="width:38px;height:38px;background:${rk[0]};color:${rk[1]};box-shadow:none">${rk[2]}</span>
      <div class="ad"><b>${tl(s[6])} – ${tl(s[7])} <span class="mu" style="font-weight:700;font-size:12px">${tip==='I'?'fiyat içinde':yz(uz,1)}</span></b><small>${det||s[3]+' tepki'}${s[9]?', son tepki '+saatYaz(s[9],DM):''}${s[5]?', rol değiştirdi':''}${s[4]!=='tepe-dip'?', '+esc(s[4]):''}</small></div>
      <div class="sag" style="width:70px"><small class="${g>=0.7?'up':g>=0.5?'wa':'mu'}">${g>=0.7?'Güçlü':g>=0.5?'Orta':'Zayıf'}</small><div class="bar" style="margin-top:5px"><i style="width:${Math.round(g*100)}%"></i></div></div></div>`}).join('')}</div>`:`<div class="bos">Yakında tepki görmüş bir bölge yok</div>`)+
     `<p class="not"><b style="color:var(--tx)">Seviyeler nasıl bulunuyor?</b> Önce belirgin tepe ve diplerden aday bölgeler çıkarılır. Sonra son ~300 mumun her biri kontrol edilir: fiyat bölgeye fitille girip dışında kapandıysa, o mum yerel bir tepe ya da dipse ve fiyat ardından bölgeden en az 1,5 ATR (ortalama mum boyunun 1,5 katı) uzaklaştıysa bu bir tepki sayılır. Hiç tepki görmeyen bölge çizilmez. Tepki sayısı, son tepkinin ne kadar yakın olduğu ve bölgenin hem destek hem direnç olarak çalışması (rol değişimi) gücü belirler. Grafikte bölge ilk tepkiden bugüne çizilir, noktalar tepki anlarıdır.</p>`}
  else if(sekme==='haber'){const hb=H[secili].hb;
    if(!hb||!hb.l.length)x+=`<div class="bos"><b>Son 7 günde haber bulunamadı</b>${V.haber_durum&&V.haber_durum.hata?'Haber kaynağına ulaşılamadı: '+esc(V.haber_durum.hata):'Haberler sinyali olan ve en likit hisseler için ~30 dakikada bir güncellenir.'}</div>`;
    else{const sk=hb.skor;x+=`<div class="kart pad" style="margin-bottom:12px"><div class="sat1"><div><span class="lbl">Son 48 saatin haber havası</span><div style="font:800 24px var(--disp);margin-top:2px" class="${sk>=2?'up':sk<=-2?'dn':''}">${sk>=2?'Olumlu':sk<=-2?'Olumsuz':'Nötr'}</div></div><span class="rozet ${sk>=2?'up':sk<=-2?'dn':''}">puan ${sk>0?'+':''}${tl(sk,1)}</span></div>
      <p class="not" style="margin:8px 0 0">Başlıklardaki kelimelere göre puanlanır (temettü, rekor kâr, ihale kazandı olumlu; zarar, soruşturma, ceza olumsuz). Olumlu akış AL sinyalinin güvenini artırır, olumsuz akış düşürür; bot olumsuz haberli hisseye girmez.</p></div>
      <div class="kart">${hb.l.map(h=>haberSatir({b:h.b,k:h.k,u:h.u,p:h.p,t:h.t})).join('')}</div>`}}
  else{const l=[...o.sinF].reverse(),bit=l.filter(s=>s.sonuc!=='açık'),hd=bit.filter(s=>s.sonuc==='hedef').length,st=bit.filter(s=>s.sonuc==='stop').length;
    x+=`<div class="istat"><div><span class="lbl">Sinyal</span><b>${l.length}</b></div><div><span class="lbl">Hedef / stop</span><b><span class="up">${hd}</span> / <span class="dn">${st}</span></b></div><div><span class="lbl">İsabet</span><b>${hd+st?'%'+tl(hd/(hd+st)*100,0):'—'}</b></div></div>`;
    x+=l.length?`<div class="kart" style="margin-top:12px"><table class="tbl"><tr><th>Zaman</th><th>Yön</th><th>Gv</th><th>Sonuç</th></tr>${l.slice(0,20).map(s=>`<tr><td>${s.saat}</td><td><span class="yon ${s.yon>0?'al':'sat'}">${s.tur}</span></td><td>${s.guven}</td>
      <td class="${s.sonuc==='hedef'?'up':s.sonuc==='stop'?'dn':'mu'}">${esc(s.sonuc)} ${yz(s.getiri,1)}</td></tr>${s.neden&&V.neden_adi?`<tr><td colspan="4" style="padding-top:0;white-space:normal;text-align:left;font-size:11.5px;color:var(--mu)">↳ Neden tutmadı: <b style="color:var(--wa)">${esc(V.neden_adi[s.neden]||s.neden)}</b></td></tr>`:''}`).join('')}</table></div>`:`<div class="bos" style="margin-top:12px">Sinyal yok</div>`;
    const nd={};bit.filter(s=>s.neden).forEach(s=>nd[s.neden]=(nd[s.neden]||0)+1);const ndl=Object.entries(nd).sort((a,b)=>b[1]-a[1]);
    if(ndl.length&&V.neden_adi)x+=`<div class="bolum"><h3>Bu hissede neden tutmadı?</h3></div><div class="kart pad bilesen" style="padding-top:4px">${ndl.map(([k,v])=>`<div><div class="ust3"><span class="mu">${esc(V.neden_adi[k]||k)}</span><span>${v}</span></div><div class="bar"><i style="width:${v/st*100}%;background:linear-gradient(90deg,var(--wa),var(--dn))"></i></div></div>`).join('')}</div>`;
    x+=`<p class="not">Her sinyalden sonra ${V.ufuk} ${birim(m)} içinde önce H1'e mi stopa mı gidildiğine bakıldı. Hedefler riskin en az 1,5 katı olduğu için ~%40 isabet başabaştır; %40'ın üstü kârlı demektir. Yani %45 isabet düşük değil, kazandıran bir orandır.</p>`}
  $('#sekme').innerHTML=x}
$('#sekmeler').onclick=e=>{const b=e.target.closest('button');if(!b)return;sekme=b.dataset.s;D.set('sekme',sekme);sekmeCiz()};


/* ===================== SOHBET ASİSTANI ===================== */
const SBK='sohbet1';let SB=D.get(SBK,[]);if(!Array.isArray(SB))SB=[];
const zamanS=t=>new Date(t).toLocaleTimeString('tr-TR',{hour:'2-digit',minute:'2-digit'});
const gunS=t=>{const d=new Date(t),b=new Date();const f=Math.round((new Date(b.toDateString())-new Date(d.toDateString()))/864e5);return f===0?'Bugün':f===1?'Dün':d.toLocaleDateString('tr-TR',{day:'numeric',month:'long',weekday:'long'})};
const sl=(s,m)=>`<a class="sl" data-h="${s}" data-m="${m||M}">${s}</a>`;
const btn=(et,ad,ana)=>`<button ${et}${ana?' class="ana"':''}>${ad}</button>`;
function sbKaydet(){SB=SB.slice(-90);D.set(SBK,SB)}
function sbCiz(){const el=$('#slog');let x='',onGun='',onK='';
  SB.forEach((m,i)=>{const g=gunS(m.t);if(g!==onGun){x+=`<div class="sgun"><span>${g}</span></div>`;onGun=g;onK=''}
    const ilk=m.k!==onK;onK=m.k;x+=balon(m,ilk,false)});
  el.innerHTML=x;el.scrollTop=el.scrollHeight}
function balon(m,ilk,yeni){return `<div class="sb ${m.k==='ben'?'ben':''}${ilk?' ilk2':''}${yeni?' yeni2':''}">${m.k==='bot'?`<span class="av2">${LOGO}</span>`:''}
  <div class="bal${m.kart?' kartli':''}">${m.h}${m.kart?'':`<span class="zm">${zamanS(m.t)}</span>`}</div></div>`}
function sbEkle(k,h,kart){const m={k,h,t:Date.now(),kart:!!kart};const son=SB[SB.length-1];SB.push(m);sbKaydet();
  const el=$('#slog');if(!son||gunS(son.t)!==gunS(m.t))el.insertAdjacentHTML('beforeend',`<div class="sgun"><span>${gunS(m.t)}</span></div>`);
  el.insertAdjacentHTML('beforeend',balon(m,!son||son.k!==k||gunS(son.t)!==gunS(m.t),ANIM));sayAnim(el.lastElementChild);
  requestAnimationFrame(()=>el.scrollTo({top:el.scrollHeight,behavior:ANIM?'smooth':'auto'}))}
/* bot yazıyor… sırası */
let sira=[],yaziyor=false;
function botYaz(...parcalar){parcalar.forEach(p=>sira.push(p));if(!yaziyor)sirayiIsle()}
function sirayiIsle(){const p=sira.shift();if(!p){yaziyor=false;oneriCiz();return}yaziyor=true;const el=$('#slog');
  if(!ANIM){(Array.isArray(p)?sbEkle('bot',p[0],true):sbEkle('bot',p));sirayiIsle();return}
  el.insertAdjacentHTML('beforeend',`<div class="sb ilk2" id="yazan"><span class="av2">${LOGO}</span><div class="bal"><span class="yaz"><i></i><i></i><i></i></span></div></div>`);el.scrollTop=el.scrollHeight;
  const uz=Array.isArray(p)?650:Math.min(1200,350+String(p).replace(/<[^>]+>/g,'').length*9);
  setTimeout(()=>{const y=$('#yazan');if(y)y.remove();Array.isArray(p)?sbEkle('bot',p[0],true):sbEkle('bot',p);setTimeout(sirayiIsle,160)},uz)}
const kartP=h=>[h];   // bir parçayı kart olarak işaretle
/* ---------- kartlar ---------- */
function kPiyasa(){const b=V.bist;if(!b)return kartP(`<div class="kc">BIST 100 verisi henüz gelmedi.</div>`);
  const yuk=liste_.filter(h=>h[M].d>0).length,dus=liste_.filter(h=>h[M].d<0).length;
  const sr=[...liste_].sort((a,b)=>b[M].d-a[M].d),en=sr.slice(0,3),kot=sr.slice(-3).reverse();
  return kartP(`<div class="kc"><div class="kb"><span class="baslik2">BIST 100${V.rejim?' · '+esc(V.rejim):''}</span><span class="rozet ${yon(b.d)}">${b.d>=0?'▲':'▼'} ${yz(b.d)}</span></div>
    <div class="dev">${say(b.p,0)}</div>${alan(M==='w'?b.spark_w:b.spark,{h:58})}</div>
   <div class="kc"><div class="genislik" style="margin-top:0"><i style="flex:${yuk||1};background:var(--up)"></i><i style="flex:${dus||1};background:var(--dn)"></i></div>
    <div class="gy" style="padding:7px 0 2px"><span><b class="up">${yuk}</b> yükseliyor</span><span><b class="dn">${dus}</b> düşüyor</span></div>
    <div class="sdz"><div><small>En çok yükselen</small><b>${en.map(h=>sl(h.s)+` <span class="up">${yz(h[M].d,1)}</span>`).join('<br>')}</b></div><div><small>En çok düşen</small><b>${kot.map(h=>sl(h.s)+` <span class="dn">${yz(h[M].d,1)}</span>`).join('<br>')}</b></div></div></div>
   <div class="kbtn">${btn('data-sor="Isı haritası"','Isı haritası')}${btn('data-sor="Sektörler"','Sektörler')}${btn('data-git="piyasa"','Tüm hisseler',1)}</div>`)}
function sinSatir(h,m=M){const s=h[m].akt,al=s.yon>0;
  return `<div class="ssin" data-h="${h.s}" data-m="${m}">${av(h.s,38)}<div class="ad"><b>${h.s} <span class="yon ${al?'al':'sat'}">${s.tur}</span> <span class="kal ${kalCls(s.kalite)}">${s.kalite}</span></b>
   <small>${esc(s.sebepler[0])}</small><small class="n" style="margin-top:3px">giriş ${tl(s.giris_alt)}–${tl(s.giris_ust)} · <span class="up">H1 +${tl(s.pot[0],1)}%</span> · <span class="dn">stop −${tl(s.risk,1)}%</span></small></div>${halka(s.guven,al)}</div>`}
function kSinyaller(f){let l=aktifler;if(f==='al')l=l.filter(h=>h[M].akt.yon>0);if(f==='sat')l=l.filter(h=>h[M].akt.yon<0);if(f==='a')l=l.filter(h=>KS[h[M].akt.kalite]<=1);
  if(!l.length)return [`${GOSTER[M]} grafikte şu an ${f==='sat'?'taze SAT':f==='a'?'A+ ya da A kalite':'taze AL'} sinyali yok. İstersen başka zaman dilimine bakabilirim: ${MODLAR.filter(m=>m!==M).map(m=>`<a class="sl" data-sor="${GOSTER[m]} grafiğe geç">${GOSTER[m]}</a>`).join(', ')}.`];
  return [`${GOSTER[M]} grafikte <b>${l.length}</b> taze sinyal var. En güçlü ${Math.min(3,l.length)} tanesi:`,
    kartP(l.slice(0,3).map(h=>sinSatir(h)).join('')+`<div class="kbtn">${l.length>3?btn('data-git="plan"',`Hepsini gör (${l.length})`,1):''}${btn(`data-sor="${l[0].s} neden"`,`${l[0].s} neden?`)}</div>`)]}
function kHisse(s){const h=H[s];const m=h[M]?M:MODLAR.find(k=>h[k]);if(!m)return [`${s} için veri yok.`];const o=h[m],kp=kap(o);
  const R=o.sev.filter(z=>z[6]>o.p).sort((a,b)=>a[6]-b[6])[0],Dz=o.sev.filter(z=>z[7]<o.p).sort((a,b)=>b[7]-a[7])[0];
  let x=`<div class="kc"><div class="kb"><div class="satir" style="gap:10px;flex-wrap:nowrap">${av(s,36)}<div><b style="font:700 16px var(--disp)">${s}</b><div class="mu" style="font-size:12px;font-weight:600">${esc(h.sek)} · ${GOSTER[m]}</div></div></div><span class="rozet ${yon(o.d)}">${yz(o.d)}</span></div>
    <div class="dev">${tl(o.p)}</div>${alan(kp,{h:58})}</div>`;
  if(o.akt)x+=sinSatir(h,m);
  if(o.yorum&&o.yorum.length)x+=`<div class="kc"><ul class="ymad">${o.yorum.slice(0,3).map(c=>`<li>${esc(c)}</li>`).join('')}</ul></div>`;
  x+=`<div class="kc"><div class="sdz"><div><small>Yakın direnç</small><b class="dn">${R?tl(R[6])+' <span class="mu" style="font-size:11px">'+yz((R[6]/o.p-1)*100,1)+'</span>':'—'}</b></div><div><small>Yakın destek</small><b class="up">${Dz?tl(Dz[7])+' <span class="mu" style="font-size:11px">'+yz((Dz[7]/o.p-1)*100,1)+'</span>':'—'}</b></div>
    <div><small>RSI · ADX</small><b>${tl(o.rsi,0)} · ${tl(o.adx,0)}</b></div><div><small>Haber havası</small><b class="${h.hb&&h.hb.skor>=2?'up':h.hb&&h.hb.skor<=-2?'dn':''}">${h.hb&&h.hb.l.length?(h.hb.skor>=2?'Olumlu':h.hb.skor<=-2?'Olumsuz':'Nötr'):'Haber yok'}</b></div></div></div>`;
  x+=`<div class="kbtn">${btn(`data-h="${s}" data-m="${m}"`,'Grafiği aç',1)}${btn(`data-fav="${s}"`,fav.has(s)?'Listemden çıkar':'Listeme ekle')}${btn(`data-alarm="${s}"`,'Alarm kur')}</div>`;
  const b=(B&&B.poz||[]).find(p=>p.s===s);
  return [b?`Bot şu an ${s}'de pozisyonda: ${b.kalan} lot, ${tlk(b.kz)} (${yz(b.yuzde)}).`:o.akt?`${s} için taze bir ${o.akt.tur} sinyali var.`:`${s} için şu an taze sinyal yok. Teknik durum şöyle:`,kartP(x)]}
function kBot(){if(!B||!B.ayar)return ['Bot verisi henüz yok.'];const g=B.bugun||{},top=(g.kz||0)+(g.acik_kz||0);
  let x=`<div class="kc"><div class="kb"><span class="baslik2">Canlı bot · ${B.aktif?(V.seans?'seansta':'seans kapalı'):'duraklatıldı'}</span><span class="rozet ${yon(B.kz||0)}">${yz(B.kz_yuzde)}</span></div>
   <div class="dev">${say(B.ozk,0)} <span style="font-size:16px;color:var(--mu)">TL</span></div><div class="mu" style="font-size:12.5px;font-weight:600">Bugün ${tlk(top)} · ${g.islem||0} giriş · ${B.poz.length} açık pozisyon</div></div>`;
  if(B.poz.length)x+=B.poz.map(p=>`<div class="srow" data-h="${p.s}" data-m="${p.mod}">${av(p.s,32)}<div class="ad"><b>${p.s} <span class="dl">${GOSTER[p.mod]}</span></b><small>${p.kalan} lot · ort. ${tl(p.giris)} · stop ${tl(p.stop)}</small></div><div class="sag"><b class="${yon(p.kz)}">${tlk(p.kz)}</b><small class="${yon(p.yuzde)}">${yz(p.yuzde)}</small></div></div>`).join('');
  const bk=B.bekleyen||[];if(bk.length)x+=`<div class="kc mu" style="font-size:12.5px;font-weight:600">Bekleyen limit emir: ${bk.map(b=>`<b style="color:var(--tx)">${b.s}</b> ${tl(b.alt)}–${tl(b.ust)}`).join(', ')}</div>`;
  x+=`<div class="kbtn">${btn('data-git="bot"','Terminali aç',1)}${btn('data-botayar="1"','Ayarlar')}${btn('data-sor="Ne öğrendin?"','Ne öğrendin?')}</div>`;
  const t=B.tani;const not=t&&(t.mesaj||(t.giris?`Son taramada ${t.giris} yeni işleme girdim.`:t.sinyal?`${t.sinyal} taze sinyal gördüm ama hiçbiri şartlarımı sağlamadı.`:'Şu an taze sinyal beklemedeyim.'));
  return [not||'Botun durumu:',kartP(x)]}
function kDers(){const O=B&&B.ogren;if(!O)return ['Öğrenme verisi henüz yok.'];const S=O.seviye,Rf=v=>v==null?'—':(v>=0?'+':'−')+tl(Math.abs(v),2)+'R';
  const iyi=(O.dersler||[]).filter(d=>d.iyi).slice(0,3),kot=(O.dersler||[]).filter(d=>!d.iyi).slice(0,3);
  let x=`<div class="kc"><div class="kb"><span class="baslik2">Seviye ${S.no} · ${esc(S.ad)}</span><span class="rozet ac">${tl(O.n,0)} ders</span></div>
   <div class="beyin" style="padding:0"><div class="ilerle2" style="margin:10px 0 4px"><i style="width:${Math.round(S.oran*100)}%"></i></div></div>
   <div class="mu" style="font-size:12px;font-weight:600">${S.sonraki?`${esc(SEV_AD[S.no]||'')} seviyesine ${tl(S.sonraki-O.n,0)} ders kaldı`:'En üst seviyedeyim'} · ${O.acik} sinyal takipte</div></div>`;
  const sat=d=>`<div class="ders" style="padding:9px 13px"><span class="di ${d.iyi?'up':'dn'}">${d.iyi?'↑':'↓'}</span><div><b>${esc(d.metin.charAt(0).toLocaleUpperCase('tr-TR')+d.metin.slice(1))}</b><small>${d.adet} deneme · %${d.kaz} kazanma · ort. ${Rf(d.E)}${d.engel?' · artık girmiyorum':''}</small></div></div>`;
  if(iyi.length||kot.length)x+=iyi.map(sat).join('')+kot.map(sat).join('');
  x+=`<div class="kbtn">${btn('data-git="bot" data-bt2="analiz"','Botun beyni',1)}</div>`;
  const ac=!iyi.length&&!kot.length?`Şu ana kadar ${tl(O.n,0)} ders topladım ama henüz belirgin bir kalıp çıkmadı. Bir koşulda en az 8 deneme birikince ayırt etmeye başlayacağım.`
    :`${tl(O.n,0)} dersten çıkardıklarım: ${iyi.length?`en iyi çalışan koşul <b>${esc(iyi[0].metin)}</b>`:''}${iyi.length&&kot.length?', ':''}${kot.length?`en zayıfı <b>${esc(kot[0].metin)}</b>`:''}.`+(O.sec!=null&&O.hep!=null&&O.sec_n>=30&&O.sec_n<O.n-O.canli?` Seçtiğim sinyaller ortalama ${Rf(O.sec)}, hepsi ${Rf(O.hep)}.`:'');
  return [ac,kartP(x)]}
function kHaber(){const l=V.akis.filter(e=>e.tip==='HABER').slice(0,5);if(!l.length)return ['Son saatlerde önemli bir haber yakalamadım.'];
  return ['Hisselerle ilgili son önemli haberler:',kartP(`<div class="kart" style="border:0;border-radius:0;box-shadow:none">${l.map(haberSatir).join('')}</div>`)]}
function kSektor(){const s=(V.sektorler||[]).filter(k=>k.ad!=='Diğer').slice(0,7);if(!s.length)return ['Sektör verisi henüz hazır değil.'];
  return [`Para en çok <b>${esc(s[0].ad)}</b> sektörüne ${s[0].akis>=0?'giriyor':'çıkıyor'}.`,kartP(`<div class="kc">${s.map(k=>`<div style="padding:5px 0;cursor:pointer" data-git="piyasa"><div class="sat1" style="font-size:13px;font-weight:700"><span>${esc(k.ad)}</span><span class="${yon(k.akis)}" style="font-weight:800">${k.akis>=0?'+':'−'}${tl(Math.abs(k.akis*100),0)}%</span></div>
    <div class="akisbar"><i style="${k.akis>=0?`left:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--up)`:`right:50%;width:${Math.min(Math.abs(k.akis),1)*50}%;background:var(--dn)`}"></i></div></div>`).join('')}</div>`)]}
function kIsi(){const ls=[...liste_].sort((a,b)=>(b.lik||0)-(a.lik||0)).slice(0,24);
  return ['En likit 24 hissenin haritası (renk ne kadar koyuysa hareket o kadar büyük):',kartP(`<div class="kc"><div class="harita">${ls.map((h,i)=>`<div data-h="${h.s}" data-m="${M}" style="background:${isi(h[M].d)};animation-delay:${i*15}ms"><b>${h.s}</b><span>${yz(h[M].d,1)}</span></div>`).join('')}</div></div>`)]}
function kHareket(y){const l=[...liste_].sort((a,b)=>y*(b[M].d-a[M].d)).slice(0,6);
  return [y>0?'Bugün en çok yükselenler:':'Bugün en çok düşenler:',kartP(l.map(h=>`<div class="srow" data-h="${h.s}" data-m="${M}">${av(h.s,32)}<div class="ad"><b>${h.s}</b><small>${esc(h.sek)}</small></div><div class="sag"><b>${tl(h[M].p)}</b><small class="${yon(h[M].d)}">${yz(h[M].d)}</small></div></div>`).join(''))]}
function kListe(){const l=liste_.filter(h=>fav.has(h.s));if(!l.length)return ['Listen boş. Bir hisse kartında "Listeme ekle"ye basarsan burada takip ederim.'];
  return ['Takip listen:',kartP(l.map(h=>`<div class="srow" data-h="${h.s}" data-m="${M}">${av(h.s,32)}<div class="ad"><b>${h.s} ${h[M].akt?`<span class="yon ${h[M].akt.yon>0?'al':'sat'}">${h[M].akt.tur}</span>`:''}</b><small>${esc(h.sek)}</small></div><div class="sag"><b>${tl(h[M].p)}</b><small class="${yon(h[M].d)}">${yz(h[M].d)}</small></div></div>`).join('')+`<div class="kbtn">${btn('data-git="portfoy"','Listemi aç',1)}</div>`)]}
const YARDIM=['Piyasa nasıl?','En iyi sinyaller','Bot ne yaptı?','Ne öğrendin?','Haberler','Yükselenler','Düşenler','Sektörler','Listem'];
function kYardim(){return [`Bana bir hisse kodu yazabilirsin (örneğin <a class="sl" data-sor="THYAO">THYAO</a>), ya da şunları sorabilirsin: ${YARDIM.map(y=>`<a class="sl" data-sor="${y}">${y.toLocaleLowerCase('tr-TR')}</a>`).join(', ')}. "5 dk grafiğe geç", "botu durdur", "ayarlar" gibi komutları da anlarım.`]}
function selam(){const sa=new Date().getHours();return sa<6?'İyi geceler.':sa<12?'Günaydın.':sa<18?'İyi günler.':'İyi akşamlar.'}
function brif(){const b=V.bist,nal=aktifler.filter(h=>h[M].akt.yon>0).length;const p=[];
  p.push(`${selam()} ${b?`BIST 100 ${b.d>=0?'yükselişte':'düşüşte'}, <b class="${yon(b.d)}">${yz(b.d)}</b>.`:''} ${V.seans?'Seans açık.':'Seans kapalı, son veriler '+esc(V.guncelleme)+' itibarıyla.'}`);
  p.push(kPiyasa());
  if(aktifler.length){const en=aktifler[0],s=en[M].akt;p.push(`${GOSTER[M]} grafikte ${aktifler.length} taze sinyal var (${nal} AL). En güçlüsü ${sl(en.s)}: ${esc(s.sebepler[0].charAt(0).toLocaleLowerCase('tr-TR')+s.sebepler[0].slice(1))}, güven ${s.guven}.`)}
  if(B&&B.ayar)p.push(`Bot ${B.poz.length?B.poz.length+' pozisyonda':'şu an pozisyonsuz'}, başlangıçtan beri <b class="${yon(B.kz||0)}">${yz(B.kz_yuzde)}</b>${B.ogren?`. ${tl(B.ogren.n,0)} ders topladım, seviyem ${esc(B.ogren.seviye.ad)}`:''}.`);
  return p}
/* ---------- anlama ---------- */
const trk=t=>t.toLocaleLowerCase('tr-TR');
function anla(q){const t=trk(q).trim(),ust=q.toLocaleUpperCase('tr-TR');
  const kod=(ust.match(/[A-ZÇĞİÖŞÜ0-9]{3,6}/g)||[]).map(k=>k.replace(/İ/g,'I')).find(k=>H[k]);
  const dil=[['1 dk','1'],['5 dk','5'],['15 dk','g'],['günlük','w'],['1dk','1'],['5dk','5'],['15dk','g']].find(([k])=>t.includes(k));
  if(dil&&/geç|bak|değiştir|grafik/.test(t)&&!kod){M=dil[1];D.set('mod',M);hazirla();sbBas();return [`Tamam, artık ${GOSTER[M]} grafiğe bakıyorum.`,...kSinyaller('al').slice(0,2)]}
  if(kod){if(/grafi|aç|chart/.test(t)){setTimeout(()=>detayAc(kod),500);return [`${kod} grafiğini açıyorum.`]}
    if(/alarm/.test(t)){setTimeout(()=>{detayAc(kod);setTimeout(alarmAc,450)},400);return [`${kod} için alarm ekranını açıyorum.`]}
    if(/haber/.test(t)){const h=H[kod];return h.hb&&h.hb.l.length?[`${kod} haberleri:`,kartP(`<div class="kart" style="border:0;border-radius:0;box-shadow:none">${h.hb.l.slice(0,5).map(x=>haberSatir({b:x.b,k:x.k,u:x.u,p:x.p,t:x.t})).join('')}</div>`)]:[`${kod} için son 7 günde haber bulamadım.`]}
    if(/neden|niye|yorum|ne düşün/.test(t)){const h=H[kod],o=h[M]||h[MODLAR.find(k=>h[k])];if(o&&o.akt){const s=o.akt;return [`${kod} ${s.tur} sinyalinin gerekçeleri:`,kartP(`<div class="kc"><ul class="ymad">${s.sebepler.map(c=>`<li>${esc(c)}</li>`).join('')}${(s.eksi||[]).map(c=>`<li style="color:var(--dn)">${esc(c)}</li>`).join('')}</ul></div><div class="kbtn">${btn(`data-h="${kod}"`,'Grafiği aç',1)}</div>`)]}}
    if(/sat(\b|ış)|çık/.test(t)){const b=(B&&B.poz||[]).find(p=>p.s===kod);if(b)return [`Bot ${kod}'de ${b.kalan} lot taşıyor. Kapatmak istersen:`,kartP(`<div class="kbtn">${btn(`data-botkapat2="${b.id}"`,`${kod} pozisyonunu kapat`,1)}</div>`)]}
    return kHisse(kod)}
  if(/^(merhaba|selam|sa\b|günaydın|iyi akşam|iyi gün|hey)/.test(t))return brif();
  if(/yardım|ne yapabilir|neler sor|nasıl kullan/.test(t))return kYardim();
  if(/durdur|duraklat/.test(t)&&/bot/.test(t)){setTimeout(()=>{if(confirm('Bot duraklatılsın mı? Açık pozisyonlar takip edilmeye devam eder.'))ustGit('?bot=durdur')},300);return ['Botu duraklatmak için onayını bekliyorum.']}
  if(/başlat|çalıştır/.test(t)&&/bot/.test(t)){ustGit('?bot=baslat');return ['Botu başlatıyorum.']}
  if(/ayar|tema|görünüm/.test(t)&&!/bot/.test(t)){setTimeout(()=>git('profil'),400);return ['Ayarları açıyorum.']}
  if(/bot.*ayar|ayar.*bot/.test(t)){setTimeout(botAyarAc,300);return ['Bot ayarlarını açıyorum.']}
  if(/öğren|ders|beyin|seviye|tecrübe/.test(t))return kDers();
  if(/pozisyon|bot|işlem|portföy|kâr|kar\b|zarar|ne yaptı|bakiye|para/.test(t))return kBot();
  if(/haber/.test(t))return kHaber();
  if(/sektör/.test(t))return kSektor();
  if(/ısı|harita/.test(t))return kIsi();
  if(/düşen|kaybettir|en kötü/.test(t))return kHareket(-1);
  if(/yükselen|kazandır|artan|en iyi hisse/.test(t))return kHareket(1);
  if(/liste|favori|takip/.test(t))return kListe();
  if(/sat sinyal|ne satay|short/.test(t))return kSinyaller('sat');
  if(/a\+|kaliteli/.test(t))return kSinyaller('a');
  if(/sinyal|fırsat|ne alay|ne alın|öneri|tavsiye|en iyi|güçlü|al\b/.test(t))return kSinyaller('al');
  if(/piyasa|bist|endeks|borsa|genel|nasıl gidiyor|durum/.test(t))return [V.bist?`BIST 100 şu an ${tl(V.bist.p,0)}, gün içinde ${yz(V.bist.d)}.`:'Piyasa özeti:',kPiyasa()];
  const yakin=Object.keys(H).filter(k=>k.startsWith(ust.replace(/[^A-ZÇĞİÖŞÜ0-9]/g,'').slice(0,3))).slice(0,5);
  return [`Bunu tam anlayamadım.${yakin.length&&ust.trim().length<=6?` Şunlardan birini mi kastettin: ${yakin.map(k=>`<a class="sl" data-sor="${k}">${k}</a>`).join(', ')}?`:''}`,...kYardim()]}
function sor(q){q=String(q||'').trim();if(!q)return;sbEkle('ben',esc(q));$('#sq').value='';otoCiz();
  let c;try{c=anla(q)}catch(e){c=['Bir şeyler ters gitti, tekrar dener misin?']}botYaz(...c)}
/* ---------- öneriler, otomatik tamamlama, başlık ---------- */
function oneriCiz(){const son=SB.slice(-6).map(m=>m.h).join(' ');const kl=[...son.matchAll(/data-h="([A-Z0-9]+)"/g)],kod=kl.length?kl[kl.length-1][1]:null;
  const l=[...(kod?[`${kod} neden`,`${kod} haberleri`]:[]),'Piyasa nasıl?','En iyi sinyaller','Bot ne yaptı?','Ne öğrendin?','Haberler','Yükselenler','Isı haritası','Yardım'];
  $('#soneri').innerHTML=l.slice(0,8).map(x=>`<button data-sor="${esc(x)}">${esc(x)}</button>`).join('')}
function otoCiz(){const v=$('#sq').value.toLocaleUpperCase('tr-TR').replace(/İ/g,'I').trim();if(v.length<2||/\s/.test(v)){oneriCiz();return}
  const l=Object.keys(H).filter(k=>k.startsWith(v)).slice(0,8);if(!l.length){oneriCiz();return}
  $('#soneri').innerHTML=l.map(k=>`<button class="hs" data-sor="${k}">${k} <span class="${yon((H[k][M]||{}).d||0)}">${H[k][M]?yz(H[k][M].d,1):''}</span></button>`).join('')}
function sbBas(){const b=V.bist;$('#sbas').innerHTML=`<span class="sav ${V.seans?'on':''}">${LOGO}</span><div class="sad"><b>Radar</b><small>${V.seans?'Seans açık':'Seans kapalı'} · ${esc(V.guncelleme)} verisi · ${GOSTER[M]}</small></div>
  ${b?`<button class="spill" data-sor="Piyasa nasıl?"><b>${tl(b.p,0)}</b><span class="${yon(b.d)}">${yz(b.d)}</span></button>`:''}${B&&B.ayar?`<button class="spill" data-sor="Bot ne yaptı?"><b>Bot</b><span class="${yon(B.kz||0)}">${yz(B.kz_yuzde)}</span></button>`:''}
  <button class="ikon" data-menu="1" title="Menü">${IK.ayar}</button>`;
  const bt_=$('#sbant');if(bt_)bt_.innerHTML=kayanBant()}
function menuAc(){$('#form').onclick=null;
  const s=(e,i,a,k)=>`<button ${e}><span>${i}</span><div>${a}<small>${k}</small></div></button>`;
  $('#form').innerHTML=`<div class="tutamak"></div><h2>Menü</h2><div class="smenu">
   ${s('data-git="plan"','🎯','Sinyaller ve planlar',`${aktifler.length} taze plan`)}${s('data-git="piyasa"','📈','Piyasa','tüm hisseler, sektörler')}${s('data-git="bot"','🤖','Bot terminali','pozisyonlar, emirler, yarış')}
   ${s('data-git="akis"','⚡','Canlı akış','sinyaller ve haberler sırayla')}${s('data-git="portfoy"','⭐','Listem','takip listesi ve alarmlar')}${s('data-git="panel"','🧭','Pano','klasik genel görünüm')}${s('data-git="profil"','⚙️','Ayarlar','görünüm, bildirimler, eşikler')}
   ${s('data-temizle="1"','🧹','Sohbeti temizle','geçmiş mesajları sil')}</div>`;
  sheetAc();$('#form').onclick=e=>{const t=e.target.closest('[data-git],[data-temizle]');if(!t)return;sheetKapat();
    if(t.dataset.temizle){SB=[];sbKaydet();sbCiz();botYaz(...brif())}else git(t.dataset.git)}}
function sayfaAc(){$('#app').classList.add('ac');D.set('sayfa',1)}
function sayfaKapat(){$('#app').classList.remove('ac');D.set('sayfa',0);if(chart&&!$('#detay').classList.contains('ac')){}sbBas()}
/* ---------- olaylar ---------- */
$('#sohbet').addEventListener('click',e=>{const t=e.target.closest('a.hb')?null:e.target.closest('[data-sor],[data-h],[data-git],[data-fav],[data-alarm],[data-botayar],[data-menu],[data-botkapat2]');if(!t)return;const d=t.dataset;
  if(d.sor)sor(d.sor);
  else if(d.menu)menuAc();
  else if(d.git){if(d.bt2){bt=d.bt2;D.set('bt2',bt)}git(d.git)}
  else if(d.fav){fav.has(d.fav)?fav.delete(d.fav):fav.add(d.fav);D.set('fav',[...fav]);t.textContent=fav.has(d.fav)?'Listemden çıkar':'Listeme ekle';toast(fav.has(d.fav)?`${d.fav} listene eklendi`:`${d.fav} listenden çıkarıldı`)}
  else if(d.alarm){detayAc(d.alarm);setTimeout(alarmAc,450)}
  else if(d.botayar)botAyarAc();
  else if(d.botkapat2){if(confirm('Pozisyon anlık fiyattan kapatılsın mı?'))ustGit('?bot=kapat&id='+encodeURIComponent(d.botkapat2))}
  else if(d.h)detayAc(d.h,d.m)});
$('#sq').addEventListener('input',otoCiz);
$('#sq').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();sor($('#sq').value)}});
$('#sgonder').onclick=()=>sor($('#sq').value);
/* ---------- açılışta: brif ve kaçırılanlar ---------- */
function acilisSohbet(){sbBas();sbCiz();const p=[],son=D.get('sb_son',0),simdi=Date.now();
  const yeniGun=!SB.length||gunS(SB[SB.length-1].t)!=='Bugün';
  if(MESAJ)p.push(`✓ ${esc(MESAJ)}`);
  if(yeniGun)p.push(...brif());
  if(B&&B.log&&son){const ol=B.log.filter(l=>l[4]&&l[4]*1000>son&&l[3]&&['al','kar','kazanc','zarar'].includes(l[1])).reverse();
    if(ol.length===1){const l=ol[0];p.push(`${l[1]==='al'?'🟢':l[1]==='zarar'?'🔴':'✅'} ${sl(l[3])}: ${esc(l[2])}`)}
    else if(ol.length>1)p.push(`Sen yokken ${ol.length} işlem hareketi oldu:`,kartP(ol.slice(-8).map(l=>`<div class="srow" data-h="${l[3]}"><span class="etk2 ${l[1]==='al'?'al':'sat'}" style="width:40px;flex:none">${l[1]==='al'?'AL':'SAT'}</span><div class="ad"><b>${l[3]}</b><small style="white-space:normal">${esc(l[2])}</small></div><span class="mu" style="font-size:11.5px;font-weight:700">${(l[0].split(' ')[1]||'')}</span></div>`).join('')+`<div class="kbtn">${btn('data-git="bot"','Terminali aç',1)}</div>`))}
  if(B&&B.ogren){const sv=D.get('sb_sev',0);if(sv&&B.ogren.seviye.no>sv)p.push(`🎉 Seviye atladım: artık <b>${esc(B.ogren.seviye.ad)}</b>yim. ${tl(B.ogren.n,0)} dersten öğrendiklerimi işlemlerimde kullanıyorum.`);D.set('sb_sev',B.ogren.seviye.no)}
  const gor=new Set(D.get('sb_sin',[]));const yeniA=aktifler.filter(h=>h[M].akt.kalite==='A+'&&!gor.has(h.s+h[M].akt.t)).slice(0,2);
  if(!yeniGun&&yeniA.length)p.push(`Yeni ${yeniA.length>1?'A+ fırsatlar':'bir A+ fırsat'} çıktı:`,kartP(yeniA.map(h=>sinSatir(h)).join('')));
  yeniA.forEach(h=>gor.add(h.s+h[M].akt.t));D.set('sb_sin',[...gor].slice(-200));
  D.set('sb_son',simdi);if(p.length)botYaz(...p);else oneriCiz()}

if(MESAJ)setTimeout(()=>toast(MESAJ),400);
ciz(true);window.addEventListener('resize',()=>{navCiz();indX=null;ustCiz()});
if(D.get('sayfa',0))sayfaAc();
acilisSohbet();
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
        sonuc=s["sonuc"], getiri=_r(s["getiri"] * 100, 2), neden=s.get("neden"), ilerleme=_r(min(max(ilerleme, 0), 1), 3), durum=durum,
        risk=_r(abs(s["fiyat"] - s["stop"]) / s["fiyat"] * 100, 2),
        pot=[yuzde(s["hedef"]), yuzde(s["hedef2"]), yuzde(s["hedef3"])],
        en_iyi=yuzde(en_iyi), kalan=max(TEST_UFKU - (n - 1 - s["i"]), 0),
        vade=VADE[mod]["ad"], vade_sure=VADE[mod]["sure"], olasilik=s.get("olasilik"), mtf=s.get("mtf", 0), htf_yon=s.get("htf_yon", 0),
        kalite=("A+" if s["guven"] >= 80 and s["guclu"] and s["rk"] >= 2 else
                "A" if s["guven"] >= 70 and s["rk"] >= 1.5 else "B" if s["guven"] >= 60 else "C"),
    )


def kompakt(x: dict) -> list:
    """Geçmiş sinyaller için sıkıştırılmış satır: [zaman, yön, güven, güçlü, fiyat, sonuç, getiri%, tutmama nedeni]"""
    return [x["t"], x["yon"], x["guven"], int(x["guclu"]), x["fiyat"], x["sonuc"], x["getiri"], x.get("neden")]


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
    yorum, tetik = a["yorum"], a["tetik"]
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
        sev=[[_r(d["p"], 4), "D" if d["hi"] < fiyat else ("R" if d["lo"] > fiyat else "I"), _r(d["guc"], 2), d["temas"], d["kaynak"],
              int(bool(d.get("rol"))), _r(d["lo"], 4), _r(d["hi"], 4), _ts(df.index[min(d["ilk"], len(df) - 1)], mod),
              _ts(df.index[min(d["son"], len(df) - 1)], mod), d.get("ust_n", 0), d.get("alt_n", 0),
              [[_ts(df.index[min(j, len(df) - 1)], mod), _r(pz, 4)] for j, pz in d.get("dokunus", [])]]
             for d in a["sev_d"] if abs(d["p"] / fiyat - 1) <= 0.25],
        mum=a.get("mum", []), uyum=a.get("uyum", 0), adx=_r(a.get("adx"), 0),
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
            if len(l) >= 25 and isabet < 33:      # sürekli tutmayan kurulum pratikte kapatılır
                bonus = -25
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
BOT_VARSAYILAN = dict(butce=100000.0, gunluk=8, hizli=True, aktif_yonetim=True, acik=3, risk=1.0, guven=65, dilim="g", kalite="A",
                      gunluk_zarar=3.0, piyasa_filtre=True, piyasa_esik=-1.5, iz_stop=True, guven_lot=True, coklu_onay=True)
# Bot yarışı: aynı anda farklı tarzda çalışan rakip botlar (ayarları sabit, karşılaştırma için)
RAKIPLER = {
    "secici": dict(ad="Seçici", aciklama="Sadece A+ kalite, güven 75+, en fazla 2 pozisyon",
                   ayar=dict(BOT_VARSAYILAN, kalite="A+", guven=75, acik=2, gunluk=3, coklu_onay=True, hizli=False)),
    "atak": dict(ad="Atak", aciklama="B ve üstü, güven 55+, 5 pozisyon, çoklu zaman onayı yok",
                 ayar=dict(BOT_VARSAYILAN, kalite="B", guven=55, acik=5, gunluk=10, coklu_onay=False, guven_lot=False)),
    "swing": dict(ad="Swing", aciklama="Günlük grafik, haftalarca taşıyan işlemler",
                  ayar=dict(BOT_VARSAYILAN, dilim="w", kalite="A", guven=65, acik=4, gunluk=3, risk=1.5)),
}


def fiyat_adimi(f: float) -> float:
    """Borsa İstanbul pay piyasası fiyat adımı (kademe)."""
    for sinir, adim in ((20, 0.01), (50, 0.02), (100, 0.05), (250, 0.10), (500, 0.25), (1000, 0.50), (2500, 1.0)):
        if f < sinir:
            return adim
    return 2.5


def kurulum_karnesi(islemler: list[dict]) -> dict:
    """Botun KENDİ işlemlerinden kurulum türü başına kazanma oranı ve ortalama R."""
    g = {}
    for x in islemler[-300:]:
        g.setdefault(x.get("kurulum") or "?", []).append(x)
    return {k: dict(n=len(l), kaz=sum(1 for x in l if x["kz"] > 0) / len(l), R=float(np.mean([x.get("R", 0) for x in l])))
            for k, l in g.items()}


TUM_BOTLAR: list = []          # ana bot + rakipler: öğrenme hepsinin işlemlerinden yapılır


def _saat_grubu(h) -> str:
    if h is None:
        return "Saat kaydı yok"
    return "10–11" if h < 11 else "11–13" if h < 13 else "13–15" if h < 15 else "15–18"


OGRENME_BOYUT = {
    "kurulum": ("Sinyal türü", lambda x: x.get("kurulum") or "?"),
    "rejim": ("Hissenin trendi", lambda x: str(int(x.get("rejim") or 0))),
    "saat": ("Giriş saati", lambda x: _saat_grubu(x.get("saat"))),
    "kalite": ("Kalite", lambda x: x.get("kalite") or "?"),
}


def ortak_ogrenme() -> dict:
    """Bütün botların kapanan işlemlerinden: hangi koşulda kaybediliyor? (boyut → grup → istatistik + yasak mı)"""
    islemler, gor = [], set()
    son = {}
    for b in TUM_BOTLAR:                       # uygulama yeniden kurulduysa aynı adlı eski bot yerine en yenisi
        son[b.ad] = b
    for b in son.values():
        for x in b.d.get("islem", [])[-400:]:
            k = (x["id"], x.get("giris"))
            if k not in gor:
                gor.add(k)
                islemler.append(x)
    out = {}
    for anahtar, (_, f) in OGRENME_BOYUT.items():
        g = {}
        for x in islemler:
            g.setdefault(f(x), []).append(x)
        out[anahtar] = {k: dict(n=len(l), kaz=sum(1 for x in l if x["kz"] > 0) / len(l), R=float(np.mean([x.get("R", 0) for x in l])),
                                yasak=len(l) >= 5 and sum(1 for x in l if x["kz"] > 0) / len(l) < 0.3 and float(np.mean([x.get("R", 0) for x in l])) < -0.15)
                        for k, l in g.items()}
    out["_n"] = len(islemler)
    return out


def _ep_dizi(df) -> np.ndarray:
    """Mum zamanlarını saniye cinsinden epoch olarak döndürür."""
    return pd.DatetimeIndex(df.index).as_unit("ns").asi8 // 10 ** 9


class GitDepo:
    """Bot verisini GitHub deposunda ayrı bir dalda saklar. Ayrı dal olduğu için Streamlit uygulamayı yeniden başlatmaz."""
    API = "https://api.github.com"

    def __init__(self, token: str, repo: str, dal: str = "bot-veri", yol: str = "bot_canli.json"):
        self.token, self.repo, self.dal, self.yol = token, repo, dal, yol
        self.sha = None
        self.hazir = False        # uzaktaki veri başarıyla okunmadan asla yazılmaz (eski geçmişin üstüne yazmamak için)
        self.son = None           # son başarılı kayıt zamanı
        self.hata = None
        self.son_deneme = 0.0

    def _istek(self, yontem: str, yol: str, govde=None):
        veri = json.dumps(govde).encode() if govde is not None else None
        req = urllib.request.Request(self.API + yol, data=veri, method=yontem, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "borsa-radar-bot"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                icerik = r.read()
                return r.status, (json.loads(icerik) if icerik else None)
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read() or b"null")
            except Exception:  # noqa: BLE001
                return e.code, None

    @staticmethod
    def _mesaj(g) -> str:
        return (g or {}).get("message", "") if isinstance(g, dict) else ""

    def _dal_hazirla(self):
        k, g = self._istek("GET", f"/repos/{self.repo}/branches/{self.dal}")
        if k == 200:
            return
        k, r = self._istek("GET", f"/repos/{self.repo}")
        if k != 200:
            raise RuntimeError(f"Depoya erişilemedi ({k} {self._mesaj(r)}) — GITHUB_REPO ve token izinlerini kontrol et")
        k, ref = self._istek("GET", f"/repos/{self.repo}/git/ref/heads/{r['default_branch']}")
        if k != 200:
            raise RuntimeError(f"Ana dal okunamadı ({k} {self._mesaj(ref)})")
        k, g = self._istek("POST", f"/repos/{self.repo}/git/refs",
                           {"ref": f"refs/heads/{self.dal}", "sha": ref["object"]["sha"]})
        if k not in (201, 422):
            raise RuntimeError(f"'{self.dal}' dalı açılamadı ({k} {self._mesaj(g)}) — token'a Contents: yazma izni ver")

    def oku(self):
        """Uzaktaki veriyi döndürür; dosya henüz yoksa None. Hata olursa istisna fırlatır."""
        self.son_deneme = time.time()
        k, g = self._istek("GET", f"/repos/{self.repo}/contents/{self.yol}?ref={self.dal}")
        if k == 200:
            self.sha = g["sha"]
            ham = base64.b64decode(g.get("content") or "") if g.get("encoding") == "base64" else b""
            if not ham:   # 1 MB üstü dosyalarda içerik ayrıca okunur
                k2, b = self._istek("GET", f"/repos/{self.repo}/git/blobs/{self.sha}")
                if k2 != 200:
                    raise RuntimeError(f"Kayıt okunamadı ({k2})")
                ham = base64.b64decode(b["content"])
            self.hazir, self.hata = True, None
            return json.loads(ham.decode("utf-8"))
        if k == 404:
            self._dal_hazirla()
            self.sha, self.hazir, self.hata = None, True, None
            return None
        raise RuntimeError(f"GitHub okuma hatası ({k} {self._mesaj(g)})")

    def yaz(self, veri: dict) -> bool:
        if not self.hazir:
            return False
        ham = json.dumps(veri, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        govde = {"message": f"Bot verisi · {dt.datetime.now(TZ):%d.%m %H:%M}", "branch": self.dal,
                 "content": base64.b64encode(ham).decode()}
        k = None
        for _ in range(2):
            if self.sha:
                govde["sha"] = self.sha
            else:
                govde.pop("sha", None)
            k, g = self._istek("PUT", f"/repos/{self.repo}/contents/{self.yol}", govde)
            if k in (200, 201):
                self.sha, self.son, self.hata = g["content"]["sha"], time.time(), None
                return True
            if k in (409, 422):    # sha eskimiş: güncelini alıp bir kez daha dene
                k2, g2 = self._istek("GET", f"/repos/{self.repo}/contents/{self.yol}?ref={self.dal}")
                self.sha = g2["sha"] if k2 == 200 else None
                continue
            self.hata = f"GitHub kayıt hatası ({k} {self._mesaj(g)})"
            return False
        self.hata = f"GitHub kayıt hatası ({k})"
        return False


def depo_kur(yol: str = "bot_canli.json") -> GitDepo | None:
    """Streamlit 'Secrets' içinde GITHUB_TOKEN ve GITHUB_REPO varsa kalıcı kaydı açar."""
    try:
        tok, repo = st.secrets.get("GITHUB_TOKEN"), st.secrets.get("GITHUB_REPO")
        dal = st.secrets.get("GITHUB_DAL", "bot-veri")
    except Exception:  # noqa: BLE001  (secrets hiç tanımlı değil)
        return None
    if not tok or not repo:
        return None
    repo = str(repo).strip().replace("https://github.com/", "").replace(".git", "").strip("/")
    return GitDepo(str(tok).strip(), repo, str(dal).strip() or "bot-veri", yol)


class CanliBot:
    def __init__(self, depo: GitDepo | None = None, dosya: str | None = None, ad: str = "Ana bot",
                 sabit: dict | None = None, bildir=None):
        self.kilit = threading.RLock()
        self.depo = depo
        self.dosya = dosya or BOT_DOSYA
        self.ad, self.sabit, self.bildir = ad, sabit, bildir
        self._push_log, self._push_egri = -1, -1
        self.d = self._yukle()
        TUM_BOTLAR.append(self)

    # --- kayıt ---
    def _yeni(self, ayar: dict) -> dict:
        t = int(time.time())
        return dict(surum=1, ayar=ayar, aktif=True, baslangic=t, nakit=float(ayar["butce"]), poz=[], islem=[],
                    egri=[[t, float(ayar["butce"])]], gunler={}, gorulen=[], log=[], xu0=None, son_tik=None)

    @staticmethod
    def _gecerli(d) -> bool:
        return isinstance(d, dict) and d.get("surum") == 1

    def _duzelt(self, d: dict) -> dict:
        d["ayar"] = dict(self.sabit) if self.sabit else {**BOT_VARSAYILAN, **d.get("ayar", {})}
        return d

    def _yukle(self) -> dict:
        yerel = None
        try:
            with open(self.dosya, encoding="utf-8") as f:
                yerel = json.load(f)
        except Exception:  # noqa: BLE001
            pass
        yerel = self._duzelt(yerel) if self._gecerli(yerel) else None
        if self.depo:
            try:
                uzak = self.depo.oku()
                if self._gecerli(uzak):
                    return self._sec(self._duzelt(uzak), yerel)
                if yerel:                        # uzakta henüz kayıt yok: mevcut geçmişi GitHub'a taşı
                    self._push_log = -2
                    return yerel
            except Exception as e:  # noqa: BLE001
                self.depo.hata = str(e)
        if yerel:
            return yerel
        d = self._yeni(dict(self.sabit or BOT_VARSAYILAN))
        d["log"].append([int(time.time()), "bilgi", f"Bot {sayi(d['ayar']['butce'], 0)} TL sanal bütçeyle hazır", None])
        return d

    @staticmethod
    def _sec(uzak: dict, yerel: dict | None) -> dict:
        """Aynı botun devamı olan ve daha yeni olan kaydı seçer."""
        if (yerel and yerel.get("baslangic") == uzak.get("baslangic")
                and (yerel.get("egri") or [[0]])[-1][0] > (uzak.get("egri") or [[0]])[-1][0]):
            return yerel
        return uzak

    def _kucult(self, d: dict) -> dict:
        """GitHub'a giden kaydı makul boyutta tutar."""
        if len(d["islem"]) > 1000:
            d["islem"] = d["islem"][-1000:]
        if len(d["egri"]) > 3000:
            d["egri"] = d["egri"][:1] + d["egri"][1::2]
        d["log"] = d["log"][-150:]
        return d

    def _yerel_yaz(self):
        try:
            gecici = self.dosya + ".tmp"
            with open(gecici, "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(gecici, self.dosya)
        except Exception:  # noqa: BLE001
            pass

    def _kaydet(self, zorla: bool = False):
        self._yerel_yaz()
        if not self.depo:
            return
        if not self.depo.hazir:
            if time.time() - self.depo.son_deneme < 120:
                return
            try:                                  # açılışta GitHub'a ulaşılamadıysa tekrar dene
                uzak = self.depo.oku()
                if self._gecerli(uzak):
                    self.d = self._sec(self._duzelt(uzak), self.d)
                    if self.d is not uzak:
                        zorla = True
                    else:
                        self._yerel_yaz()
                else:
                    zorla = True
            except Exception as e:  # noqa: BLE001
                self.depo.hata = str(e)
                return
        log_n, eg_n = len(self.d["log"]), (self.d["egri"][-1][0] if self.d["egri"] else 0)
        yeni_olay = log_n != self._push_log or (self.d["log"] and self.d["log"][-1][0] > (self.depo.son or 0))
        sure_doldu = eg_n != self._push_egri and time.time() - (self.depo.son or 0) > 600
        if zorla or yeni_olay or sure_doldu or self._push_log == -2:
            self._kucult(self.d)
            if self.depo.yaz(self.d):
                self._push_log, self._push_egri = len(self.d["log"]), eg_n

    def _haber_ver(self, baslik: str, metin: str, etiket: str = "chart_with_upwards_trend"):
        if self.bildir:
            try:
                self.bildir(baslik, metin, etiket)
            except Exception:  # noqa: BLE001
                pass

    def _log(self, tip: str, metin: str, s: str | None = None):
        self.d["log"].append([int(time.time()), tip, metin, s])
        self.d["log"] = self.d["log"][-200:]

    def _ozkaynak(self) -> float:
        return self.d["nakit"] + sum(p["kalan"] * p["fiyat"] for p in self.d["poz"])

    def _onceki_gun_oz(self, bugun: str):
        onceki = [v.get("oz") for g, v in sorted(self.d["gunler"].items()) if g < bugun and v.get("oz")]
        return onceki[-1] if onceki else None

    @staticmethod
    def _gun(t: int) -> str:
        return dt.datetime.fromtimestamp(t, TZ).strftime("%Y-%m-%d")

    # --- işlem mekaniği ---
    def _al(self, h, mod, s, j, an, t, karar: dict | None = None) -> bool:
        d, a = self.d, self.d["ayar"]
        fiyat = float(an["fiyat"])
        giris = fiyat * (1 + KAYMA)
        stop = float(s["stop"])
        rb = giris - stop
        if rb <= giris * 0.001:
            return False
        oz = self._ozkaynak()
        carpan = 1.0
        if a.get("guven_lot"):                                        # güvene göre pozisyon: 50→0,6x, 75→1x, 95→1,4x
            carpan = float(np.clip(0.6 + (s["guven"] - 50) / 25 * 0.4, 0.5, 1.5)) * (1.15 if j["kalite"] == "A+" else 1.0)
        if karar and a.get("ogrenen", True):
            carpan *= karar.get("carpan", 1.0)                           # öğrenilmiş: iyi çalışan koşulda büyük, zayıfta küçük lot
        lot = int(oz * a["risk"] * carpan / 100 / rb)                 # risk bazlı lot
        lot = min(lot, int(min(d["nakit"], oz / a["acik"]) / giris))  # tek hisseye en fazla özkaynak / pozisyon sayısı
        if lot < 1:
            return False
        d["nakit"] -= lot * giris
        ep = _ep_dizi(an["ctx"]["df"])
        d["poz"].append(dict(
            id=f"{h}-{t}", s=h, mod=mod, giris=round(giris, 4), lot=lot, kalan=lot, stop=round(stop, 4), stop0=round(stop, 4),
            h=[round(float(s["hedef"]), 4), round(float(s["hedef2"]), 4), round(float(s["hedef3"]), 4)], kademe=0,
            giris_ts=t, son_ts=int(ep[-1]), sinyal_ts=int(s["_ts"]) if "_ts" in s else int(ep[s["i"]]), bar=0, giris0=round(giris, 4), realize=0.0, risk_tl=round(rb * lot, 2),
            fiyat=fiyat, guven=int(s["guven"]), kalite=j["kalite"], kurulum=s.get("kurulum", ""), sebep=s["sebepler"][0], parca=[],
            atr=round(nanv(an["ctx"]["A"]["ATR"][an["ctx"]["n"] - 1], fiyat * 0.01), 4), tepe=fiyat, carpan=round(carpan, 2),
            saat=dt.datetime.fromtimestamp(t, TZ).hour, sektor=sektor_bul(h), rejim=int(s.get("rejim", 0)), mtf=int(s.get("mtf", 0))))
        self._log("al", f"{lot} lot alındı @ {sayi(giris)} · {j['kalite']} · güven {s['guven']} — {s['sebepler'][0]}"
                         + (" (limit emir doldu)" if "_ts" in s else "")
                         + (f". Öğrenme: {karar['neden']}, lot ×{sayi(karar['carpan'], 2)}" if karar and karar.get("neden") else "") + f". Plan: stop {sayi(stop)}, H1 ({sayi(float(s['hedef']))}) gelince yarısını sat", h)
        self._haber_ver(f"{self.ad}: {h} alındı", f"{lot} lot @ {sayi(giris)} · stop {sayi(stop)} · H1 {sayi(float(s['hedef']))}\n{s['sebepler'][0]}", "green_circle")
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
            self._log("kar", f"{sebep}: {lot} lot satıldı @ {sayi(net)} · {'+' if kz >= 0 else '−'}{sayi(abs(kz), 0)} TL", p["s"])

    def _kapat(self, p, t, sebep):
        d = self.d
        d["poz"].remove(p)
        satilan = sum(x[2] for x in p["parca"]) or 1
        ort = sum(x[1] * x[2] for x in p["parca"]) / satilan
        kz = p["realize"]
        R = kz / p["risk_tl"] if p["risk_tl"] else 0
        d["islem"].append(dict(id=p["id"], s=p["s"], mod=p["mod"], lot=p["lot"], giris=p["giris"], cikis=round(ort, 4),
                               giris_ts=p["giris_ts"], cikis_ts=t, kz=round(kz, 2), yuzde=round(kz / (p["giris"] * p["lot"]) * 100, 2),
                               R=round(R, 2), sebep=sebep, guven=p["guven"], kalite=p["kalite"], kurulum=p["kurulum"],
                               saat=p.get("saat"), sektor=p.get("sektor", sektor_bul(p["s"])), rejim=p.get("rejim", 0), mtf=p.get("mtf", 0)))
        d["islem"] = d["islem"][-1500:]
        if OGRENCI is not None:
            try:
                OGRENCI.canli_ekle(d["islem"][-1])
            except Exception:  # noqa: BLE001
                pass
        self._log("kazanc" if kz > 0 else "zarar",
                  f"Pozisyon kapandı ({sebep}) · {'+' if kz >= 0 else '−'}{sayi(abs(kz), 0)} TL · {'+' if R >= 0 else ''}{sayi(R, 1)}R", p["s"])
        self._haber_ver(f"{self.ad}: {p['s']} kapandı ({sebep})", f"{'+' if kz >= 0 else '−'}{sayi(abs(kz), 0)} TL · {'+' if R >= 0 else ''}{sayi(R, 1)}R",
                        "white_check_mark" if kz > 0 else "x")

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
        if p["stop"] > p["giris"] * 1.001:
            return "Kâr koruma stopu" if p.get("koru") and p["kademe"] == 0 and p["stop"] <= p["giris"] + 0.15 * self._r0(p) else "İz süren stop (kârda)"
        return "Başabaş stop" if p["stop"] >= p["giris"] * 0.999 else "Stop"

    def _iz(self, p, tepe):
        """İz süren stop: fiyat 1R yol aldıktan sonra stop, en yüksek fiyatın 2,5 ATR altını takip eder (sadece yukarı)."""
        p["tepe"] = max(p.get("tepe", p["giris"]), tepe)
        g0 = p.get("giris0", p["giris"])
        r0 = g0 - p["stop0"]
        # Kâr koruma: fiyat 0,8R yol aldıysa stop girişin biraz üstüne çekilir, kazanan işlem zarara dönmez
        if p["kademe"] == 0 and p["tepe"] >= g0 + 0.8 * r0:
            koru = round(max(g0 + 0.1 * r0, p["giris"] * 1.001 if p.get("ek") else 0), 4)
            if koru > p["stop"]:
                p["stop"], p["koru"] = koru, True
        if not self.d["ayar"].get("iz_stop") or not p.get("atr"):
            return
        if p["tepe"] >= g0 + r0:
            yeni = max(p["giris"], p["tepe"] - 2.5 * p["atr"])
            if yeni > p["stop"]:
                p["stop"] = round(yeni, 4)

    def _bar(self, p, o, h, l, t):
        if l <= p["stop"]:                                     # temkinli: aynı mumda önce stop kontrol edilir
            self._sat(p, p["kalan"], min(o, p["stop"]), t, self._stop_sebep(p))
            return
        self._hedefler(p, h, t)
        if p in self.d["poz"]:
            self._iz(p, h)

    # --- aktif işlem yönetimi (trader gibi) ---
    def _r0(self, p) -> float:
        return max(p.get("giris0", p["giris"]) - p["stop0"], 1e-9)

    def _yonet_bar(self, p, A, j, tj):
        """Kapanmış her mumda: momentum kaybolduysa stopu beklemeden erken çık."""
        if p["kademe"] != 0 or p["bar"] < 4:
            return
        g0, r0 = p.get("giris0", p["giris"]), self._r0(p)
        c = float(A["Close"][j])
        e20 = nanv(A["EMA20"][j], c)
        vw = A["VWAP"][j] if "VWAP" in A else np.nan
        if c < g0 - 0.35 * r0 and c < e20 and (np.isnan(vw) or c < vw):
            self._log("zarar", f"Momentum kayboldu: fiyat {sayi(c)}, EMA20 ({sayi(e20)}) ve VWAP altında. Stopu beklemeden çıkıyorum", p["s"])
            self._sat(p, p["kalan"], c, tj, "Momentum kayboldu")

    def _ekle(self, p, A, n, fiyat, t) -> bool:
        """Kazanana bir kez ekleme: fiyat 0,8R yol aldı, trend sağlam → ilk lotun yarısı kadar ekle, stop ortalama maliyete."""
        if p.get("ek") or p["kademe"] != 0:
            return False
        g0, r0 = p.get("giris0", p["giris"]), self._r0(p)
        c = float(A["Close"][n - 1])
        if fiyat < g0 + 0.8 * r0 or c <= nanv(A["EMA20"][n - 1], c) or fiyat >= p["h"][0]:
            return False
        ek = int(p["lot"] * 0.5)
        al = fiyat * (1 + KAYMA)
        if ek < 1 or ek * al > self.d["nakit"]:
            return False
        self.d["nakit"] -= ek * al
        p["giris"] = round((p["giris"] * p["kalan"] + al * ek) / (p["kalan"] + ek), 4)
        p["lot"] += ek
        p["kalan"] += ek
        p["ek"] = [t, round(al, 4), ek]
        p["stop"] = max(p["stop"], round(p["giris"] * 1.001, 4))
        self._log("al", f"Kazanana ekleme: +{ek} lot @ {sayi(al)}. Fiyat 0,8R yol aldı, trend sağlam. Ortalama {sayi(p['giris'])}, stop ortalamaya çekildi (risk sıfır)", p["s"])
        self._haber_ver(f"{self.ad}: {p['s']} pozisyonuna ekleme", f"+{ek} lot @ {sayi(al)} · stop {sayi(p['stop'])}", "heavy_plus_sign")
        return True

    def _al_hazirla(self, s, h, mod, an, j):
        """Sinyalden bekleyen emir kaydı (fiyat aralığa gelince girilecek)."""
        ep = _ep_dizi(an["ctx"]["df"])
        return dict(s=h, mod=mod, alt=float(s["giris_alt"]), ust=float(s["giris_ust"]), stop=float(s["stop"]),
                    hedef=float(s["hedef"]), hedef2=float(s["hedef2"]), hedef3=float(s["hedef3"]), guven=int(s["guven"]),
                    kalite=j["kalite"], sebepler=[s["sebepler"][0]], kurulum=s.get("kurulum", ""), rejim=int(s.get("rejim", 0)),
                    mtf=int(s.get("mtf", 0)), _ts=int(ep[s["i"]]), anahtar=f"{h}-{mod}-{j['t']}", olusma=int(time.time()),
                    bitis=int(time.time()) + {"5": 30, "1": 15}.get(mod, 75) * 60)

    # --- her taramada çağrılır ---
    def tik(self, analiz: dict, acik: bool, bist_p: float | None, bist_d: float | None = None, haber_ozet: dict | None = None):
        with self.kilit:
            d, a = self.d, self.d["ayar"]
            simdi = dt.datetime.now(TZ)
            t = int(simdi.timestamp())
            bugun = simdi.strftime("%Y-%m-%d")
            yonet = a.get("aktif_yonetim", True)
            haber_ozet = haber_ozet or {}
            if d.get("xu0") is None and bist_p:
                d["xu0"] = bist_p

            # 1) Açık pozisyonlar: kapanmış mumlarda stop/hedef/momentum, sonra anlık fiyatla yönetim
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
                    if yonet:
                        self._yonet_bar(p, A, j, tj)
                        if p not in d["poz"]:
                            break
                    if p["bar"] >= TEST_UFKU and p["kademe"] == 0:     # H1 alındıysa kâr iz süren stopla taşınır
                        self._sat(p, p["kalan"], float(A["Close"][j]), tj, "Süre doldu")
                        break
                if p not in d["poz"]:
                    continue
                fiyat = float(an["fiyat"])
                p["fiyat"] = fiyat
                if acik:
                    if fiyat <= p["stop"]:
                        o_son = float(ctx["df"]["Open"].iloc[-1])           # son (açık) mumun açılışı: boşluk varsa oradan dolar
                        self._sat(p, p["kalan"], min(p["stop"], o_son) if o_son > fiyat else fiyat, t, self._stop_sebep(p))
                    else:
                        self._hedefler(p, fiyat, t)
                        if p in d["poz"]:
                            self._iz(p, fiyat)
                        if p in d["poz"] and yonet:
                            self._ekle(p, A, n, fiyat, t)
                if p not in d["poz"]:
                    continue
                if yonet:
                    oz = haber_ozet.get(p["s"])
                    kotu = oz.get("olumsuz") if oz else None
                    if kotu and oz["skor"] <= -3 and kotu["t"] > p["giris_ts"]:
                        self._log("zarar", f"Olumsuz haber geldi: “{kotu['b'][:90]}”. Riski taşımıyorum, çıkıyorum", p["s"])
                        self._sat(p, p["kalan"], fiyat, t, "Olumsuz haber")
                        continue
                    if acik and bist_d is not None and bist_d <= -2.0 and not p.get("pk") and p["kalan"] >= 2:
                        p["pk"] = True
                        self._log("bilgi", f"BIST100 {sayi(bist_d, 1)}% sert düşüyor: pozisyonu yarıya indiriyorum", p["s"])
                        self._sat(p, p["kalan"] // 2, fiyat, t, "Piyasa sert düştü")
                        if p in d["poz"]:
                            p["stop"] = max(p["stop"], round(fiyat - 1.0 * p.get("atr", fiyat * 0.01), 4))
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
            ana_mod = a["dilim"]
            modlar = [ana_mod] + (["5"] if a.get("hizli") and ana_mod == "g" else [])
            gec_mod = lambda m: m in ("1", "5") and simdi.time() >= dt.time(17, 40)  # noqa: E731
            gec = gec_mod(ana_mod)
            # Günlük zarar limiti: gün başındaki değere göre kayıp sınırı aşılınca o gün yeni işlem yok
            oz_simdi = self._ozkaynak()
            if gun.get("oz0") is None:
                gun["oz0"] = round(onceki_oz if (onceki_oz := self._onceki_gun_oz(bugun)) else oz_simdi, 2)
            gun_degisim = (oz_simdi / gun["oz0"] - 1) * 100 if gun["oz0"] else 0.0
            zarar_kilit = a.get("gunluk_zarar", 0) > 0 and gun_degisim <= -a["gunluk_zarar"]
            if zarar_kilit and not gun.get("zk"):
                gun["zk"] = True
                self._log("zarar", f"Günlük zarar limiti doldu ({sayi(gun_degisim, 1)}%), bugün yeni işlem açılmayacak")
                self._haber_ver(f"{self.ad}: günlük zarar limiti doldu", f"Bugün {sayi(gun_degisim, 1)}%. Bot bugün yeni işlem açmayacak.", "warning")
            # Piyasa filtresi: BIST100 sert düşüyorsa yeni AL yok
            piyasa_kilit = bool(a.get("piyasa_filtre")) and bist_d is not None and bist_d <= a.get("piyasa_esik", -1.5)
            if piyasa_kilit and not gun.get("pk"):
                gun["pk"] = True
                self._log("bilgi", f"Piyasa filtresi devrede: BIST100 {sayi(bist_d, 1)}%, piyasa toparlanana kadar yeni AL yok")
            if not piyasa_kilit and gun.get("pk") and acik and bist_d is not None:
                gun["pk"] = False
                self._log("bilgi", "Piyasa toparlandı, piyasa filtresi kalktı")
            d["durum"] = dict(gun_degisim=round(gun_degisim, 2), zarar_kilit=bool(zarar_kilit), piyasa_kilit=bool(piyasa_kilit),
                              bist_d=bist_d)
            tani = dict(t=t, taranan=len(analiz.get(ana_mod, {})) + (len(analiz.get("5", {})) if len(modlar) > 1 else 0),
                        bugun=0, son_mum=None, sinyal=0, giris=0, neden={}, mesaj=None, modlar=modlar)
            neden = tani["neden"]
            ekle = lambda k: neden.__setitem__(k, neden.get(k, 0) + 1)  # noqa: E731
            if not acik:
                tani["mesaj"] = "Seans kapalı; bot 10:00'da açılışla birlikte sinyal aramaya başlar."
            elif not d["aktif"]:
                tani["mesaj"] = "Bot duraklatılmış; yeni işleme girmiyor."
            elif gec:
                tani["mesaj"] = "1 ve 5 dk işlemleri için gün sonu yaklaştı (17:40 sonrası yeni işlem yok)."
            elif zarar_kilit:
                tani["mesaj"] = "Günlük zarar limiti doldu; bugün yeni işlem yok."
            elif piyasa_kilit:
                tani["mesaj"] = f"Piyasa filtresi devrede (BIST100 {sayi(bist_d, 1)}%); AL sinyallerine girilmiyor."
            bekleyen = [b for b in d.get("bekleyen", []) if b["bitis"] > t and acik]
            if d["aktif"] and acik and not gec and not zarar_kilit and not piyasa_kilit:
                gorulen = set(d["gorulen"])
                eldeki = {p["s"] for p in d["poz"]}
                karne = kurulum_karnesi(d["islem"])
                son_zarar = {}
                for x in d["islem"][-60:]:                         # hisse başına art arda zarar sayısı
                    son_zarar[x["s"]] = son_zarar.get(x["s"], 0) + 1 if x["kz"] <= 0 else 0
                adaylar = []
                bek_anahtar = {b["anahtar"] for b in bekleyen}
                for mod in modlar:
                    if gec_mod(mod):
                        continue
                    for h, an in analiz.get(mod, {}).items():
                        ctx = an["ctx"]
                        df, n = ctx["df"], ctx["n"]
                        son_t = pd.Timestamp(df.index[-1])
                        if mod == ana_mod and (tani["son_mum"] is None or son_t > tani["son_mum"]):
                            tani["son_mum"] = son_t
                        if son_t.date() != simdi.date():
                            continue                                  # bugünün verisi yoksa işlem yok
                        if mod == ana_mod:
                            tani["bugun"] += 1
                        for s in filtrele(an["sinyaller"], ESIK)[-2:]:
                            if s["yon"] <= 0 or s["sonuc"] != "açık":
                                continue
                            if n - 1 - s["i"] > {"1": 6, "5": 2}.get(mod, 1):
                                continue                              # eski sinyal (1 dk: son 7, 5 dk: son 3, diğer: son 2 mum)
                            tani["sinyal"] += 1
                            j = sinyal_json(s, df, n, an["fiyat"], mod)
                            # Öğrenen beyin: önce bu sinyali gölgede takibe al (girsek de girmesek de ders olur), sonra
                            # geçmiş derslere göre güveni/lotu ayarla ya da engelle
                            karar = dict(delta=0, carpan=1.0, engel=None, neden=None)
                            if OGRENCI is not None:
                                karar = OGRENCI.degerlendir(mod, s, j["kalite"], sektor_bul(h))
                                OGRENCI.golge_ekle(h, mod, s, j, float(an["fiyat"]), int(_ep_dizi(df)[s["i"]]), karar)
                            if s["guven"] + max(karar["delta"], -20) < a["guven"]:
                                ekle("guven"); continue
                            if KALITE_SIRA[j["kalite"]] > KALITE_SIRA[a["kalite"]]:
                                ekle("kalite"); continue
                            if a.get("coklu_onay") and (s.get("mtf", 0) <= 0 or s.get("htf_yon", 0) < 0):
                                ekle("mtf"); continue                 # üst zaman dilimi ve günlük trend onaylamıyor
                            if s.get("haber_skor", 0) <= -2:
                                ekle("haber"); continue               # olumsuz haber akışı olan hisseye girilmez
                            anahtar = f"{h}-{mod}-{j['t']}"
                            f = float(an["fiyat"])
                            if anahtar in gorulen or anahtar in bek_anahtar:
                                ekle("gorulen"); continue
                            atr_i = nanv(ctx["A"]["ATR"][n - 1], f * 0.01)
                            adim = fiyat_adimi(f)
                            if adim / f > 0.004 or adim > 0.35 * atr_i or (f - s["stop"]) < 3 * adim:
                                ekle("adim"); continue                # kuruşluk hisse: bir kademe bile stopu yer, gürültü çok
                            kk = karne.get(s.get("kurulum") or "?")
                            if karar["engel"]:
                                if anahtar not in gorulen:
                                    d["gorulen"].append(anahtar)
                                    self._log("bilgi", f"Ders aldım, girmiyorum: {karar['engel']}", h)
                                ekle("ogrenme"); continue
                            if (kk and kk["n"] >= 4 and kk["kaz"] < 0.3 and kk["R"] < 0) or son_zarar.get(h, 0) >= 2:
                                ekle("ogrenme"); continue             # botun kendi geçmişinde kaybettiren kurulum / hisse
                            # Gecikmeli veri yüzünden fiyat biraz kaçmış olabilir: 0,35 ATR'ye kadar tolerans, ama H1'e kalan
                            # kazanç kalan riskten az olmamalı
                            kalan_kz = (s["hedef"] - f) / max(f - s["stop"], 1e-9)
                            if f > s["giris_ust"] + 0.35 * atr_i or (kalan_kz < 1.0 and f > s["giris_ust"]):
                                # Fiyat kaçtı: kovalamak yerine aralığa geri çekilmeyi bekleyen limit emir bırak
                                if h not in eldeki:
                                    bekleyen = [x for x in bekleyen if x["s"] != h]     # hisse başına tek (en yeni) emir
                                    bekleyen.append(dict(self._al_hazirla(s, h, mod, an, j), _ek=karar["carpan"], _not=karar["neden"]))
                                    bek_anahtar.add(anahtar)
                                    d["gorulen"].append(anahtar)
                                    self._log("bilgi", f"Fiyat kaçtı ({sayi(f)}), kovalamıyorum. {sayi(s['giris_alt'])}–{sayi(s['giris_ust'])} aralığına limit AL emri bıraktım", h)
                                ekle("bekleyen"); continue
                            if f <= s["stop"] or f < s["giris_alt"] - 0.1 * atr_i or kalan_kz < 1.0:
                                ekle("aralik"); continue
                            adaylar.append((KALITE_SIRA[j["kalite"]], -(s["guven"] + karar["delta"]), h, s, j, anahtar, an, mod, karar))
                # Bekleyen limit emirler: fiyat aralığa geri geldiyse gir; stop kırıldıysa iptal
                kalanlar = []
                for b in bekleyen:
                    an = analiz.get(b["mod"], {}).get(b["s"])
                    if not an:
                        kalanlar.append(b); continue
                    f = float(an["fiyat"])
                    if f <= b["stop"]:
                        self._log("bilgi", f"Limit emir iptal: fiyat stop seviyesinin ({sayi(b['stop'])}) altına indi, kurulum bozuldu", b["s"])
                        continue
                    if b["alt"] - 0.05 * (b["ust"] - b["stop"]) <= f <= b["ust"] and (b["hedef"] - f) / max(f - b["stop"], 1e-9) >= 1.2:
                        j = dict(kalite=b["kalite"], t=0)
                        adaylar.append((KALITE_SIRA[b["kalite"]] - 0.5, -b["guven"], b["s"], b, j, b["anahtar"], an, b["mod"],
                                        dict(delta=0, carpan=b.get("_ek", 1.0), engel=None, neden=b.get("_not"))))
                        continue
                    kalanlar.append(b)
                bekleyen = kalanlar
                adaylar.sort(key=lambda x: (x[0], x[1]))
                for _, _, h, s, j, anahtar, an, mod, karar in adaylar:
                    if gun["al"] >= a["gunluk"] or len(d["poz"]) >= a["acik"]:
                        ekle("limit")
                        if "_ts" in s:
                            bekleyen.append(s)
                        continue
                    if h in eldeki:
                        ekle("elde"); continue
                    if self._al(h, mod, s, j, an, t, karar):
                        gun["al"] += 1
                        tani["giris"] += 1
                        eldeki.add(h)
                        if anahtar not in d["gorulen"]:
                            d["gorulen"].append(anahtar)
                    else:
                        ekle("lot")
                d["gorulen"] = d["gorulen"][-600:]
                if tani["bugun"] == 0:
                    tani["mesaj"] = "Yahoo'dan henüz bugüne ait veri gelmedi (veri ~15 dk gecikmeli; ilk mumlar 10:15–10:30 arası düşer)."
            d["bekleyen"] = bekleyen[-10:]
            if tani["son_mum"] is not None:
                tani["son_mum"] = f"{tani['son_mum']:%H:%M}" if ana_mod != "w" else f"{tani['son_mum']:%d.%m}"
            d["tani"] = tani

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
                                    ("risk", float, 0.1, 10), ("guven", int, 40, 95), ("gunluk_zarar", float, 0, 20),
                                    ("piyasa_esik", float, -10, 0)):
                if ad in q:
                    try:
                        yeni[ad] = min(max(tip(float(str(q[ad]).replace(",", "."))), lo), hi)
                    except ValueError:
                        pass
            if q.get("dilim") in MODLAR:
                yeni["dilim"] = q["dilim"]
            for anahtar in ("piyasa_filtre", "iz_stop", "guven_lot", "coklu_onay", "hizli", "aktif_yonetim"):
                if q.get(anahtar) in ("0", "1"):
                    yeni[anahtar] = q[anahtar] == "1"
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
                                   f"risk %{sayi(yeni['risk'], 1)}, güven {yeni['guven']}+, kalite {yeni['kalite']}+, "
                                   f"günlük zarar limiti {'%' + sayi(yeni['gunluk_zarar'], 1) if yeni['gunluk_zarar'] else 'kapalı'}, "
                                   f"piyasa filtresi {'açık (' + sayi(yeni['piyasa_esik'], 1) + '%)' if yeni['piyasa_filtre'] else 'kapalı'}")
                mesaj = mesaj or "Ayarlar kaydedildi"
            elif k == "onerilen":
                d["ayar"] = dict(d["ayar"], risk=1.0, guven=65, kalite="A", piyasa_filtre=True, piyasa_esik=-1.5,
                                 gunluk_zarar=3.0, iz_stop=True, guven_lot=True, coklu_onay=True, hizli=True, aktif_yonetim=True,
                                 gunluk=min(max(d["ayar"]["gunluk"], 8), 12))
                self._log("bilgi", "Önerilen ayarlara geçildi: risk %1, güven 65+, kalite A+, piyasa filtresi ve çoklu zaman onayı açık")
                mesaj = "Önerilen (daha seçici) ayarlar uygulandı"
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
            self._kaydet(zorla=True)
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

    def kisa_ozet(self) -> dict:
        with self.kilit:
            d, a = self.d, self.d["ayar"]
            oz = self._ozkaynak()
            eg = d["egri"]
            adim = max(1, len(eg) // 120)
            st_ = self._istatistik()
            return dict(ad=self.ad, getiri=_r((oz / a["butce"] - 1) * 100, 2), ozk=_r(oz, 0), n=st_["n"], kazanma=st_["kazanma"],
                        pf=st_["pf"], dd=st_["dd"], skor=st_["skor"], poz=len(d["poz"]), dilim=a["dilim"],
                        egri=[[x[0], round(x[1] / a["butce"] * 100 - 100, 2)] for x in eg[::adim]])

    def _ogrenme_ui(self) -> dict:
        og = ortak_ogrenme()
        ad = {"rejim": {"1": "Yükselen trend", "-1": "Düşen trend", "0": "Yatay"}}
        kur = lambda k: KURULUM_ADI.get(k, (k[2:] + " kırılımı") if str(k).startswith("f-") else k)  # noqa: E731
        boyutlar = []
        for b, (baslik, _) in OGRENME_BOYUT.items():
            sat = [dict(ad=(kur(k) if b == "kurulum" else ad.get(b, {}).get(k, k)), n=v["n"], kaz=round(v["kaz"] * 100), R=_r(v["R"], 2), yasak=v["yasak"])
                   for k, v in og[b].items()]
            sat.sort(key=lambda x: (x["kaz"], x["R"]))
            boyutlar.append(dict(baslik=baslik, satir=sat))
        return dict(n=og["_n"], boyut=boyutlar)

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
                                bar=p["bar"], guven=p["guven"], kalite=p["kalite"], sebep=p["sebep"],
                                giris0=p.get("giris0", p["giris"]), ek=p.get("ek"), koru=bool(p.get("koru")), pk=bool(p.get("pk")),
                                R=_r(pk / p["risk_tl"], 2) if p.get("risk_tl") else None, deger=_r(p["fiyat"] * p["kalan"], 0),
                                tepe=_r(p.get("tepe", p["giris"]), 4), atr=p.get("atr")))
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
            bugun_k = dt.datetime.now(TZ).strftime("%Y-%m-%d")
            bugun = d["gunler"].get(bugun_k, {})
            bugun_islem = [x for x in d["islem"] if self._gun(x["cikis_ts"]) == bugun_k]
            acik_kz = sum(x["kz"] for x in poz)
            bekleyen = [dict(s=b["s"], mod=b["mod"], alt=_r(b["alt"], 4), ust=_r(b["ust"], 4), stop=_r(b["stop"], 4), hedef=_r(b["hedef"], 4),
                             guven=b["guven"], kalite=b["kalite"], sebep=b["sebepler"][0], kalan_dk=max(0, round((b["bitis"] - time.time()) / 60)))
                        for b in d.get("bekleyen", [])]
            return dict(aktif=d["aktif"], ayar=a, baslangic=saat(d["baslangic"]), nakit=_r(d["nakit"], 0), ozk=_r(oz, 0),
                        kz=_r(kz, 0), kz_yuzde=_r(kz / a["butce"] * 100, 2),
                        realize=_r(sum(x["kz"] for x in d["islem"]), 0),
                        bist=_r((bist_p / d["xu0"] - 1) * 100, 2) if bist_p and d.get("xu0") else None,
                        poz=poz, islem=islem, egri=egri, gunler=gunler[-30:],
                        log=[[saat(x[0]), x[1], x[2], x[3], x[0]] for x in reversed(d["log"][-80:])],
                        st=self._istatistik(), bugun=dict(islem=bugun.get("al", 0), kz=_r(bugun.get("kz", 0), 0), acik_kz=_r(acik_kz, 0),
                                                         kapanan=len(bugun_islem), kazanan=sum(1 for x in bugun_islem if x["kz"] > 0)),
                        ogrenme=self._ogrenme_ui(),
                        maruziyet=_r(sum(x["deger"] for x in poz) / oz * 100 if oz else 0, 1), bekleyen=bekleyen, durum=d.get("durum") or {}, tani=d.get("tani"),
                        son_tik=saat(d["son_tik"]) if d.get("son_tik") else None, ad=self.ad,
                        kayip=kayip_analizi([dict(kazandi=x["kz"] > 0, R=x["R"], saat=x.get("saat"), kurulum=x.get("kurulum"),
                                                  sektor=x.get("sektor"), kalite=x.get("kalite"), rejim=x.get("rejim", 0), mtf=x.get("mtf", 0))
                                             for x in d["islem"]]),
                        kayit=(dict(tip="github", hazir=self.depo.hazir, hata=self.depo.hata, repo=self.depo.repo, dal=self.depo.dal,
                                    son=saat(int(self.depo.son)) if self.depo.son else None)
                               if self.depo else dict(tip="yerel")))

# ---------- Öğrenen beyin: her sinyali gölgede takip eder, gerçek işlemlerle birleştirir, zamanla güçlenir ----------
OGREN_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ogrenme.json")
OGREN_ALAN = ["mod", "kurulum", "rejim", "mtf", "saat", "kalite", "guv", "sektor"]       # kayıt sırası
OGREN_BOYUT = {                                                                      # öğrenilen boyutlar (ve ikili kombinasyonlar)
    "kurulum": "Sinyal türü", "rejim": "Hissenin trendi", "mtf": "Üst zaman dilimi", "saat": "Giriş saati",
    "kalite": "Kalite", "guv": "Güven aralığı", "mod": "Zaman dilimi", "sektor": "Sektör",
    "kurulum|rejim": "Sinyal türü × trend", "kurulum|mod": "Sinyal türü × zaman dilimi", "saat|mod": "Saat × zaman dilimi",
}
SEVIYELER = [(0, "Çaylak"), (60, "Öğrenci"), (250, "Deneyimli"), (700, "Usta"), (1600, "Uzman"), (4000, "Efsane")]
_SAAT = lambda h: "?" if h is None else ("10–11" if h < 11 else "11–13" if h < 13 else "13–15" if h < 15 else "15–18")  # noqa: E731
_GUV = lambda g: "50–59" if g < 60 else "60–69" if g < 70 else "70–79" if g < 80 else "80+"  # noqa: E731


def ozellik(mod, kurulum, rejim, mtf, saat, kalite, guven, sektor) -> dict:
    return dict(mod=str(mod), kurulum=str(kurulum or "?"), rejim=str(int(rejim or 0)), mtf=str(int(mtf or 0)),
                saat=saat if isinstance(saat, str) else _SAAT(saat), kalite=str(kalite or "?"), guv=_GUV(int(guven or 0)),
                sektor=str(sektor or "Diğer"))


def _grup_anahtar(f: dict) -> list[tuple[str, str]]:
    return [(b, "|".join(f[p] for p in b.split("|"))) for b in OGREN_BOYUT]


class Ogrenci:
    """Botun hafızası.
    - Gölge işlemler: botun gördüğü HER taze AL sinyali (girsin girmesin) sanal olarak takip edilir; hedef mi stop mu
      önce geldi kaydedilir. Böylece günde 3–5 gerçek işlem yerine onlarca ders birikir.
    - Gerçek işlemler 2 kat ağırlıkla, geçmiş test sonuçları zayıf ön bilgi (0,25 ağırlık) olarak eklenir.
    - Her koşul (sinyal türü, trend, saat, kalite… ve ikili kombinasyonları) için beklenen getiri, az veriyle aşırı
      tepki vermesin diye genel ortalamaya doğru büzülerek (Bayes) hesaplanır.
    - Karar: güven puanını yukarı/aşağı çeker, lotu büyütür/küçültür, açıkça kaybettiren koşulu engeller.
    - Dürüst ölçüm: her gölge işlem açılırken botun o anki kararı (girerdi/girmezdi) yazılır; sonradan 'öğrenmenin
      seçtikleri' ile 'hepsi' karşılaştırılır (geriye dönük hile yok)."""

    A = 12.0            # büzülme gücü: bir grubun kendi verisi bu kadar ağırlığa ulaşınca yarı yarıya kendi sonucuna güvenilir

    def __init__(self, depo: GitDepo | None = None):
        self.kilit = threading.RLock()
        self.depo = depo
        self.d = self._yukle()
        self._ist = None
        self._son_kayit = 0.0

    # --- kayıt ---
    def _bos(self) -> dict:
        return dict(surum=1, baslangic=int(time.time()), golge=[], kayit=[], test={}, gorulen=[], egri=[])

    def _yukle(self) -> dict:
        d = None
        try:
            with open(OGREN_DOSYA, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:  # noqa: BLE001
            pass
        if self.depo:
            try:
                u = self.depo.oku()
                if isinstance(u, dict) and u.get("surum") == 1 and len(u.get("kayit", [])) >= len((d or {}).get("kayit", [])):
                    d = u
            except Exception as e:  # noqa: BLE001
                self.depo.hata = str(e)
        if not (isinstance(d, dict) and d.get("surum") == 1):
            d = self._bos()
        return {**self._bos(), **d}

    def kaydet(self, zorla: bool = False):
        if not zorla and time.time() - self._son_kayit < 600:
            return
        self._son_kayit = time.time()
        with self.kilit:
            veri = json.loads(json.dumps(self.d))
        try:
            with open(OGREN_DOSYA + ".tmp", "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(OGREN_DOSYA + ".tmp", OGREN_DOSYA)
        except Exception:  # noqa: BLE001
            pass
        if self.depo and self.depo.hazir:
            threading.Thread(target=lambda: self.depo.yaz(veri), daemon=True).start()

    # --- veri ekleme ---
    def golge_ekle(self, h: str, mod: str, s: dict, j: dict, fiyat: float, ep_sinyal: int, karar: dict):
        """Taze AL sinyalini gölge işlem olarak açar (aynı sinyal bir kez)."""
        anahtar = f"{h}-{mod}-{ep_sinyal}"
        with self.kilit:
            if anahtar in self._gorulen_set():
                return
            stop, hedef = float(s["stop"]), float(s["hedef"])
            if not (stop < fiyat < hedef):
                return
            f = ozellik(mod, s.get("kurulum"), s.get("rejim", 0), s.get("mtf", 0), dt.datetime.now(TZ).hour, j["kalite"], s["guven"], sektor_bul(h))
            self.d["golge"].append(dict(s=h, mod=mod, g=round(fiyat, 4), st=round(stop, 4), hd=round(hedef, 4), ts=ep_sinyal,
                                        son=ep_sinyal, bar=0, t=int(time.time()), f=[f[k] for k in OGREN_ALAN],
                                        karar=0 if karar.get("engel") else (2 if karar.get("delta", 0) >= 3 else 1)))
            self.d["golge"] = self.d["golge"][-400:]
            self.d["gorulen"] = (self.d["gorulen"] + [anahtar])[-3000:]
            self._gs = None

    def _gorulen_set(self):
        if getattr(self, "_gs", None) is None:
            self._gs = set(self.d["gorulen"])
        return self._gs

    def _kapat(self, g: dict, R: float, t: int, kaynak: str = "g"):
        R = float(max(min(R, 6.0), -1.5))
        self.d["kayit"].append([t, round(R, 3), kaynak, g.get("karar", 1)] + list(g["f"]))
        self.d["kayit"] = self.d["kayit"][-3500:]
        self._ist = None

    def canli_ekle(self, x: dict):
        """Botun gerçek (sanal bütçeli) işlemi kapandığında: 2 kat ağırlıklı ders."""
        f = ozellik(x.get("mod", "g"), x.get("kurulum"), x.get("rejim", 0), x.get("mtf", 0), x.get("saat"), x.get("kalite"),
                    x.get("guven", 60), x.get("sektor"))
        with self.kilit:
            self._kapat(dict(f=[f[k] for k in OGREN_ALAN], karar=1), x.get("R", 0), int(x.get("cikis_ts") or time.time()), "c")

    def test_yukle(self, mod: str, tum: list[dict]):
        """Derin geçmiş testin sonuçlarını ön bilgi olarak özetler (ham veri saklanmaz)."""
        ozet = {}
        for s in tum:
            if s.get("yon", 1) <= 0 or s.get("sonuc") not in ("hedef", "stop"):
                continue
            risk = abs(s["fiyat"] - s["stop"]) / s["fiyat"] if s.get("fiyat") else 0
            R = max(min(s["getiri"] / risk if risk else 0, 6), -1.5)
            kal = ("A+" if s["guven"] >= 80 and s.get("guclu") and s.get("rk", 0) >= 2 else
                   "A" if s["guven"] >= 70 and s.get("rk", 0) >= 1.5 else "B" if s["guven"] >= 60 else "C")
            saat = pd.Timestamp(s["zaman"]).hour if s.get("zaman") is not None and mod != "w" else None
            f = ozellik(mod, s.get("kurulum"), s.get("rejim", 0), s.get("mtf", 0), saat, kal, s["guven"], sektor_bul(s.get("sym", "")))
            for b, k in _grup_anahtar(f) + [("_", "_")]:
                o = ozet.setdefault(f"{b}={k}", [0, 0, 0.0])
                o[0] += 1
                o[1] += R > 0
                o[2] = round(o[2] + R, 3)
        with self.kilit:
            self.d["test"][mod] = ozet
            self._ist = None

    # --- her taramada: gölge işlemleri ilerlet ---
    def guncelle(self, analiz: dict):
        simdi = int(time.time())
        with self.kilit:
            kalan = []
            for g in self.d["golge"]:
                an = analiz.get(g["mod"], {}).get(g["s"])
                if not an:
                    if simdi - g["t"] > 4 * 86400:
                        continue                                  # uzun süre veri yoksa bırak
                    kalan.append(g)
                    continue
                ctx = an["ctx"]
                A, n, ep = ctx["A"], ctx["n"], _ep_dizi(ctx["df"])
                r0 = g["g"] - g["st"]
                bitti = False
                for i in range(min(n, len(ep))):
                    ti = int(ep[i])
                    if ti <= g["son"]:
                        continue
                    g["son"], g["bar"] = ti, g["bar"] + 1
                    lo, hi = float(A["Low"][i]), float(A["High"][i])
                    if lo <= g["st"]:                              # temkinli: aynı mumda ikisi de olduysa stop sayılır
                        self._kapat(g, -1.0, ti); bitti = True; break
                    if hi >= g["hd"]:
                        self._kapat(g, (g["hd"] - g["g"]) / r0, ti); bitti = True; break
                    if g["bar"] >= TEST_UFKU:
                        self._kapat(g, (float(A["Close"][i]) - g["g"]) / r0, ti); bitti = True; break
                if not bitti:
                    kalan.append(g)
            self.d["golge"] = kalan
            # Günlük gelişim kaydı
            bugun = dt.datetime.now(TZ).strftime("%Y-%m-%d")
            if not self.d["egri"] or self.d["egri"][-1][0] != bugun:
                ist = self._istatistik()
                self.d["egri"].append([bugun, ist["n"], round(ist["E0"], 3)])
                self.d["egri"] = self.d["egri"][-180:]
        self.kaydet()

    # --- istatistik ---
    def _istatistik(self) -> dict:
        if self._ist is not None:
            return self._ist
        W = {"g": 1.0, "c": 2.0}
        gr = {}
        topn = topw = topR = 0.0
        for r in self.d["kayit"]:
            w = W.get(r[2], 1.0)
            R = r[1]
            f = dict(zip(OGREN_ALAN, r[4:]))
            topn += w; topw += w * (R > 0); topR += w * R
            for b, k in _grup_anahtar(f):
                o = gr.setdefault((b, k), [0.0, 0.0, 0.0, 0])
                o[0] += w; o[1] += w * (R > 0); o[2] += w * R; o[3] += 1
        tw = 0.25                                                  # geçmiş test ön bilgisi zayıf ağırlıkla
        for oz in self.d["test"].values():
            for key, v in oz.items():
                b, k = key.split("=", 1)
                if b == "_":
                    topn += tw * v[0]; topw += tw * v[1]; topR += tw * v[2]
                    continue
                o = gr.setdefault((b, k), [0.0, 0.0, 0.0, 0])
                o[0] += tw * v[0]; o[1] += tw * v[1]; o[2] += tw * v[2]
        E0 = topR / topn if topn else 0.0
        P0 = topw / topn if topn else 0.5
        A = self.A
        grup = {}
        for (b, k), (n, w, R, adet) in gr.items():
            grup[(b, k)] = dict(n=n, adet=adet, E=(R + A * E0) / (n + A), P=(w + A * P0) / (n + A), ham=R / n if n else 0.0)
        self._ist = dict(n=len(self.d["kayit"]), E0=E0, P0=P0, grup=grup)
        return self._ist

    def degerlendir(self, mod, s: dict, kalite: str, sektor: str, saat=None) -> dict:
        """Sinyal için öğrenilmiş düzeltme: güven farkı, lot çarpanı, engel (varsa nedeni)."""
        with self.kilit:
            ist = self._istatistik()
        if ist["n"] < 20:
            return dict(delta=0, carpan=1.0, engel=None, neden=None)
        f = ozellik(mod, s.get("kurulum"), s.get("rejim", 0), s.get("mtf", 0), dt.datetime.now(TZ).hour if saat is None else saat,
                    kalite, s.get("guven", 60), sektor)
        toplam = agirlik = 0.0
        en_kotu = en_iyi = None
        for b, k in _grup_anahtar(f):
            g = ist["grup"].get((b, k))
            if not g or g["adet"] < 6:
                continue
            fark = g["E"] - ist["E0"]
            a = 1.6 if "|" in b else 1.0
            toplam += a * fark; agirlik += a
            if en_kotu is None or fark < en_kotu[0]:
                en_kotu = (fark, b, k, g)
            if en_iyi is None or fark > en_iyi[0]:
                en_iyi = (fark, b, k, g)
            if g["adet"] >= 8 and g["E"] <= -0.3 and g["P"] < 0.33:
                return dict(delta=-99, carpan=0.0, engel=f"{self.grup_adi(b, k)}: {g['adet']} denemede %{round(g['P'] * 100)} kazanma, ort. {sayi(g['E'], 2)}R", neden=None)
        if not agirlik:
            return dict(delta=0, carpan=1.0, engel=None, neden=None)
        skor = toplam / agirlik
        delta = int(round(float(np.clip(skor * 40, -15, 10))))
        carpan = float(np.clip(1 + skor * 1.2, 0.6, 1.4))
        neden = None
        if delta >= 3 and en_iyi:
            neden = f"{self.grup_adi(en_iyi[1], en_iyi[2])} iyi çalışıyor (ort. {sayi(en_iyi[3]['E'], 2)}R)"
        elif delta <= -3 and en_kotu:
            neden = f"{self.grup_adi(en_kotu[1], en_kotu[2])} zayıf (ort. {sayi(en_kotu[3]['E'], 2)}R)"
        return dict(delta=delta, carpan=round(carpan, 2), engel=None, neden=neden)

    @staticmethod
    def grup_adi(b: str, k: str) -> str:
        def tek(bb, kk):
            if bb == "kurulum":
                return KURULUM_ADI.get(kk, (kk[2:] + " kırılımı") if kk.startswith("f-") else kk)
            if bb == "rejim":
                return {"1": "yükselen trendde", "-1": "düşen trendde", "0": "yatay piyasada"}.get(kk, kk)
            if bb == "mtf":
                return {"1": "üst dilim onaylı", "-1": "üst dilim ters", "0": "üst dilim kararsız"}.get(kk, kk)
            if bb == "mod":
                return DILIM_ADI.get(kk, kk)
            if bb == "saat":
                return f"saat {kk}"
            if bb == "kalite":
                return f"{kk} kalite"
            if bb == "guv":
                return f"güven {kk}"
            return kk
        bs, ks = b.split("|"), k.split("|")
        return " · ".join(tek(x, y) for x, y in zip(bs, ks))

    def seviye(self) -> dict:
        n = len(self.d["kayit"])
        i = max(k for k, (esik, _) in enumerate(SEVIYELER) if n >= esik)
        sonraki = SEVIYELER[i + 1][0] if i + 1 < len(SEVIYELER) else None
        return dict(ad=SEVIYELER[i][1], no=i + 1, n=n, sonraki=sonraki,
                    oran=1.0 if not sonraki else (n - SEVIYELER[i][0]) / (sonraki - SEVIYELER[i][0]))

    def ui(self) -> dict:
        with self.kilit:
            ist = self._istatistik()
            kayit = list(self.d["kayit"])
            acik = len(self.d["golge"])
            egri = list(self.d["egri"])
        # Dürüst karşılaştırma: gölge işlemler açılırken verilen karara göre (sonradan bakma yok)
        hafta = {}
        for r in kayit:
            if r[2] != "g":
                continue
            k = dt.datetime.fromtimestamp(r[0], TZ).strftime("%d.%m")
            hf = hafta.setdefault(dt.datetime.fromtimestamp(r[0], TZ).isocalendar()[1], dict(et=k, hep=[], sec=[]))
            hf["hep"].append(r[1])
            if r[3] >= 1:
                hf["sec"].append(r[1])
        gelisim = [dict(et=v["et"], hep=_r(float(np.mean(v["hep"])), 3), sec=_r(float(np.mean(v["sec"])), 3) if v["sec"] else None,
                        n=len(v["hep"])) for _, v in sorted(hafta.items())][-12:]
        tum_g = [r for r in kayit if r[2] == "g"]
        secilen = [r[1] for r in tum_g if r[3] >= 1]
        guclu = [r[1] for r in tum_g if r[3] == 2]
        # Dersler: verisi yeterli ve ortalamadan belirgin ayrışan gruplar
        dersler = []
        for (b, k), g in ist["grup"].items():
            if g["adet"] < 8 or b == "sektor" and g["adet"] < 15:
                continue
            fark = g["E"] - ist["E0"]
            if abs(fark) < 0.12:
                continue
            dersler.append(dict(metin=self.grup_adi(b, k), boyut=OGREN_BOYUT[b], adet=g["adet"], kaz=round(g["P"] * 100), E=_r(g["E"], 2),
                                iyi=fark > 0, engel=g["adet"] >= 8 and g["E"] <= -0.3 and g["P"] < 0.33, fark=_r(fark, 2)))
        dersler.sort(key=lambda x: -abs(x["fark"]))
        return dict(seviye=self.seviye(), acik=acik, n=len(kayit), canli=sum(1 for r in kayit if r[2] == "c"),
                    test=sum((oz.get("_=_") or [0])[0] for oz in self.d["test"].values()),
                    E0=_r(ist["E0"], 3), P0=round(ist["P0"] * 100),
                    hep=_r(float(np.mean([r[1] for r in tum_g])), 3) if tum_g else None,
                    sec=_r(float(np.mean(secilen)), 3) if secilen else None, sec_n=len(secilen),
                    guclu=_r(float(np.mean(guclu)), 3) if guclu else None, guclu_n=len(guclu),
                    gelisim=gelisim, dersler=dersler[:14], egri=egri[-60:],
                    kayit=(dict(hazir=self.depo.hazir, hata=self.depo.hata) if self.depo else None))


OGRENCI: Ogrenci | None = None

# ---------- Haberler: Google Haberler'den hisse haberleri, Türkçe olumlu/olumsuz puanlama ----------
HABER_OLUMLU = {
    "rekor": 2, "kâr artış": 2, "kar artış": 2, "net kâr": 1, "net kar": 1, "kârını artırdı": 2, "karını artırdı": 2,
    "temettü": 2, "kâr payı": 2, "kar payı": 2, "bedelsiz": 2, "geri alım": 2, "pay geri al": 2, "anlaşma imzala": 2,
    "sözleşme imzala": 2, "ihale kazan": 2, "ihaleyi kazan": 2, "sipariş": 1, "yeni yatırım": 1, "yatırım kararı": 1,
    "kapasite artır": 1, "ihracat": 1, "büyüme": 1, "hedef fiyat yükselt": 2, "hedef fiyatını yükselt": 2, "al tavsiyesi": 2,
    "endeks dahil": 1, "endekse dahil": 1, "onay aldı": 1, "lisans aldı": 1, "satın aldı": 1, "ortaklık": 1, "işbirliği": 1,
    "yükseliş": 1, "tavan": 2, "güçlü bilanço": 2, "beklentileri aştı": 2, "beklenti üstü": 2, "rating yükselt": 2, "not artır": 2,
}
HABER_OLUMSUZ = {
    "zarar": -2, "net zarar": -2, "kârı düştü": -2, "karı düştü": -2, "dava": -1, "ceza": -2, "soruşturma": -2,
    "iflas": -3, "konkordato": -3, "temerrüt": -3, "haciz": -2, "işlem yasağı": -3, "tedbir": -2, "spk tedbir": -3,
    "hedef fiyat düşür": -2, "hedef fiyatını düşür": -2, "sat tavsiyesi": -2, "bedelli": -1, "sermaye kaybı": -2,
    "borç": -1, "yangın": -2, "grev": -2, "üretime ara": -2, "faaliyet durdur": -3, "iptal": -1, "geriledi": -1,
    "düşüş": -1, "taban": -2, "beklentilerin altında": -2, "beklenti altı": -2, "not düşür": -2, "rating düşür": -2,
    "istifa": -1, "manipülasyon": -3, "gözaltı": -3, "kayyum": -3, "satış baskısı": -1,
}


def _tr_kucuk(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def haber_puani(baslik: str) -> int:
    t = _tr_kucuk(baslik)
    puan = 0
    for k, v in HABER_OLUMLU.items():
        if k in t:
            puan += v
    for k, v in HABER_OLUMSUZ.items():
        if k in t:
            puan += v
    if "zarar" in t and ("azalt" in t or "kâra geçti" in t or "kara geçti" in t):
        puan += 3          # "zararı azalttı", "kâra geçti" olumlu
    return int(max(-3, min(3, puan)))


class HaberServis:
    """Arka planda öncelikli hisselerin haberlerini çeker (her hisse ~30 dakikada bir)."""

    def __init__(self):
        self.kilit = threading.Lock()
        self.veri: dict[str, list[dict]] = {}
        self.zaman: dict[str, float] = {}
        self.hedefler: list[str] = []
        self.hata = None
        self.son_basari = None
        threading.Thread(target=self._dongu, daemon=True).start()

    def hedef_ayarla(self, semboller: list[str]):
        gor, sira = set(), []
        for s in semboller:
            if s not in gor:
                gor.add(s)
                sira.append(s)
        self.hedefler = sira[:120]

    def _getir(self, sym: str) -> list[dict]:
        sorgu = urllib.parse.quote(f'"{sym}" hisse')
        url = f"https://news.google.com/rss/search?q={sorgu}&hl=tr&gl=TR&ceid=TR:tr"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (borsa-radar)"})
        with urllib.request.urlopen(req, timeout=15) as r:
            kok = ET.fromstring(r.read())
        simdi = time.time()
        out = []
        for it in kok.iter("item"):
            baslik = (it.findtext("title") or "").strip()
            if not baslik or sym.lower() not in baslik.lower():
                continue                                    # sadece başlığında hisse kodu geçen haberler
            try:
                t = email.utils.parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
            except Exception:  # noqa: BLE001
                continue
            if simdi - t > 7 * 86400:
                continue
            kaynak = (it.findtext("source") or "").strip()
            if kaynak and baslik.endswith(" - " + kaynak):
                baslik = baslik[: -len(kaynak) - 3]
            out.append(dict(b=baslik[:180], k=kaynak[:40], u=(it.findtext("link") or "")[:400], t=int(t), p=haber_puani(baslik)))
        out.sort(key=lambda x: -x["t"])
        tekil, gor = [], set()
        for h in out:
            anahtar = _tr_kucuk(h["b"])[:60]
            if anahtar not in gor:
                gor.add(anahtar)
                tekil.append(h)
        return tekil[:8]

    def _dongu(self):
        time.sleep(20)
        while True:
            try:
                bekleyen = [s for s in list(self.hedefler) if time.time() - self.zaman.get(s, 0) > 1800]
                for s in bekleyen[:40]:
                    try:
                        l = self._getir(s)
                        with self.kilit:
                            self.veri[s] = l
                        self.son_basari, self.hata = time.time(), None
                    except Exception as e:  # noqa: BLE001
                        self.hata = f"{type(e).__name__}: {e}"
                    self.zaman[s] = time.time()
                    time.sleep(1.5)
            except Exception as e:  # noqa: BLE001
                self.hata = str(e)
            time.sleep(45)

    def ozet(self, sym: str) -> dict | None:
        """Son 48 saatin haber puanı (yeni haber daha ağır)."""
        with self.kilit:
            l = list(self.veri.get(sym, []))
        if not l:
            return None
        simdi = time.time()
        skor = 0.0
        for h in l:
            yas = (simdi - h["t"]) / 3600
            if yas <= 48:
                skor += h["p"] * (1.0 if yas <= 24 else 0.5)
        olumsuz = next((h for h in l if h["p"] <= -2 and simdi - h["t"] <= 48 * 3600), None)
        olumlu = next((h for h in l if h["p"] >= 2 and simdi - h["t"] <= 48 * 3600), None)
        return dict(skor=round(skor, 1), liste=l, olumsuz=olumsuz, olumlu=olumlu)


def haber_uygula(analiz: dict, haber: HaberServis | None) -> dict:
    """Taze sinyallerin güvenini haber akışına göre ayarlar. Döndürdüğü sözlük: hisse → haber özeti."""
    ozetler = {}
    if not haber:
        return ozetler
    taze = {"1": 30, "5": 12, "g": 12, "w": 5}
    for mod, liste in analiz.items():
        for h, a in liste.items():
            if h not in ozetler:
                ozetler[h] = haber.ozet(h)
            oz = ozetler[h]
            if not oz:
                continue
            n = a["ctx"]["n"]
            for s in a["sinyaller"]:
                if s["sonuc"] != "açık" or n - 1 - s["i"] > taze[mod] or s.get("_haber"):
                    continue
                s["_haber"] = True
                etki = oz["skor"] * s["yon"]
                if etki >= 2:
                    s["guven"] = min(100, s["guven"] + 5)
                    s["arti"].append("Haber akışı destekliyor" + (f": {oz['olumlu']['b'][:70]}" if oz.get("olumlu") and s["yon"] > 0 else ""))
                elif etki <= -2:
                    s["guven"] = max(0, s["guven"] - 12)
                    kotu = oz["olumsuz"] if s["yon"] > 0 else oz.get("olumlu")
                    s["eksi"].append("Haber akışı ters" + (f": {kotu['b'][:70]}" if kotu else ""))
                s["haber_skor"] = oz["skor"]
    return ozetler

# ---------- Bildirimler (ntfy.sh) ve fiyat alarmları ----------
ORTAK_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ortak.json")


class Ortak:
    """Telefona bildirim (ntfy uygulaması) ve sunucu tarafında çalışan fiyat alarmları.
    Ayarlar ve alarmlar kalıcı kayıt açıksa GitHub'da 'ortak.json' olarak saklanır."""

    def __init__(self, depo: GitDepo | None = None):
        self.kilit = threading.RLock()
        self.depo = depo
        self.kuyruk: list[dict] = []
        self.son_hata = None
        self.d = self._yukle()
        self._kaydet()
        threading.Thread(target=self._gonderici, daemon=True).start()

    def _bos(self) -> dict:
        konu = "borsaradar-" + "".join(np.random.choice(list("abcdefghjkmnpqrstuvwxyz23456789"), 10))
        return dict(surum=1, ntfy=konu, bildirim=dict(bot=True, sinyal=True, alarm=True), alarmlar=[], gonderilen=[], gecmis=[])

    def _yukle(self) -> dict:
        d = None
        try:
            with open(ORTAK_DOSYA, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:  # noqa: BLE001
            pass
        if self.depo:
            try:
                u = self.depo.oku()
                if isinstance(u, dict) and u.get("surum") == 1:
                    d = u
            except Exception as e:  # noqa: BLE001
                self.depo.hata = str(e)
        if not (isinstance(d, dict) and d.get("surum") == 1):
            d = self._bos()
        return {**self._bos(), **d}

    def _kaydet(self):
        try:
            with open(ORTAK_DOSYA + ".tmp", "w", encoding="utf-8") as f:
                json.dump(self.d, f, ensure_ascii=False, separators=(",", ":"))
            os.replace(ORTAK_DOSYA + ".tmp", ORTAK_DOSYA)
        except Exception:  # noqa: BLE001
            pass
        if self.depo and self.depo.hazir:
            threading.Thread(target=lambda: self.depo.yaz(dict(self.d)), daemon=True).start()

    # --- bildirim gönderimi ---
    def gonder(self, baslik: str, metin: str, etiket: str = "bell", tur: str = "bot", oncelik: int = 4):
        if not self.d["bildirim"].get(tur, True) or not self.d.get("ntfy"):
            return
        with self.kilit:
            self.kuyruk.append(dict(topic=self.d["ntfy"], title=baslik[:120], message=metin[:500], tags=[etiket], priority=oncelik))
            self.d["gecmis"] = (self.d.get("gecmis", []) + [[int(time.time()), baslik[:120], tur]])[-40:]

    def _gonderici(self):
        while True:
            is_ = None
            with self.kilit:
                if self.kuyruk:
                    is_ = self.kuyruk.pop(0)
            if not is_:
                time.sleep(2)
                continue
            try:
                req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(is_).encode("utf-8"),
                                             headers={"Content-Type": "application/json"}, method="POST")
                urllib.request.urlopen(req, timeout=15).read()
                self.son_hata = None
            except Exception as e:  # noqa: BLE001
                self.son_hata = f"{type(e).__name__}: {e}"
            time.sleep(1)

    # --- siteden gelen komutlar ---
    def komut(self, q: dict) -> str | None:
        with self.kilit:
            if q.get("alarm") == "ekle":
                try:
                    fiyat = float(str(q.get("fiyat")).replace(",", "."))
                except (TypeError, ValueError):
                    return "Alarm fiyatı geçersiz"
                s = str(q.get("s", "")).upper()[:10]
                tip = "ust" if q.get("tip") == "ust" else "alt"
                self.d["alarmlar"].append(dict(id=f"{s}-{int(time.time())}", s=s, tip=tip, fiyat=fiyat, not_=str(q.get("not", ""))[:80],
                                               olusma=int(time.time()), tetik=None))
                self.d["alarmlar"] = self.d["alarmlar"][-60:]
                self._kaydet()
                return f"Alarm kuruldu: {s} {sayi(fiyat)} {'üstüne çıkınca' if tip == 'ust' else 'altına inince'}"
            if q.get("alarm") == "sil":
                self.d["alarmlar"] = [a for a in self.d["alarmlar"] if a["id"] != q.get("id")]
                self._kaydet()
                return "Alarm silindi"
            if q.get("bildirim") == "test":
                self.gonder("Borsa Radar test bildirimi", "Bildirimler çalışıyor. Bot işlem açınca, kapatınca ve alarmların tetiklenince buraya mesaj gelecek.",
                            "tada", tur="bot")
                return "Test bildirimi gönderildi"
            if q.get("bildirim") == "ayar":
                for k in ("bot", "sinyal", "alarm"):
                    if q.get(k) in ("0", "1"):
                        self.d["bildirim"][k] = q[k] == "1"
                if q.get("ntfy"):
                    konu = "".join(ch for ch in str(q["ntfy"]) if ch.isalnum() or ch in "-_")[:60]
                    if len(konu) >= 6:
                        self.d["ntfy"] = konu
                self._kaydet()
                return "Bildirim ayarları kaydedildi"
        return None

    # --- her taramada ---
    def kontrol(self, fiyatlar: dict):
        """Fiyat alarmlarını kontrol eder (tetiklenen alarm bir kez bildirilir)."""
        degisti = False
        with self.kilit:
            for a in self.d["alarmlar"]:
                if a.get("tetik"):
                    continue
                p = fiyatlar.get(a["s"])
                if p is None:
                    continue
                if (a["tip"] == "ust" and p >= a["fiyat"]) or (a["tip"] == "alt" and p <= a["fiyat"]):
                    a["tetik"], a["tetik_fiyat"] = int(time.time()), round(float(p), 4)
                    degisti = True
                    self.gonder(f"Alarm: {a['s']} {sayi(p)}", f"{a['s']} {sayi(a['fiyat'])} {'üstüne çıktı' if a['tip'] == 'ust' else 'altına indi'}."
                                + (f"\n{a['not_']}" if a.get("not_") else ""), "rotating_light", tur="alarm", oncelik=5)
        if degisti:
            self._kaydet()

    def sinyal_bildir(self, analiz: dict, haber_ozet: dict | None = None):
        """Taze A+ kalite AL sinyallerini (15 dk ve günlük) bir kez bildirir."""
        gon = set(self.d.get("gonderilen", []))
        yeni = []
        for mod in ("g", "w"):
            for h, a in analiz.get(mod, {}).items():
                df, n = a["ctx"]["df"], a["ctx"]["n"]
                for s in filtrele(a["sinyaller"], ESIK)[-1:]:
                    if s["yon"] <= 0 or s["sonuc"] != "açık" or n - 1 - s["i"] > 1:
                        continue
                    j = sinyal_json(s, df, n, a["fiyat"], mod)
                    if j["kalite"] != "A+":
                        continue
                    k = f"{h}-{mod}-{j['t']}"
                    if k in gon:
                        continue
                    gon.add(k)
                    yeni.append(k)
                    self.gonder(f"A+ sinyal: {h} AL ({DILIM_ADI[mod]})",
                                f"{s['sebepler'][0]}\nGiriş {sayi(j['giris_alt'])}–{sayi(j['giris_ust'])} · H1 {sayi(j['hedef'])} · stop {sayi(j['stop'])} · güven {j['guven']}",
                                "star", tur="sinyal")
        if yeni:
            self.d["gonderilen"] = (self.d.get("gonderilen", []) + yeni)[-400:]

    def ui(self) -> dict:
        with self.kilit:
            return dict(ntfy=self.d["ntfy"], bildirim=self.d["bildirim"], alarmlar=self.d["alarmlar"][-60:],
                        gecmis=[[dt.datetime.fromtimestamp(x[0], TZ).strftime("%d.%m %H:%M"), x[1], x[2]] for x in reversed(self.d.get("gecmis", [])[-15:])],
                        hata=self.son_hata)


# ---------- Kayıp analizi: hangi koşullarda kaybediliyor? ----------
def _saat_dilimi(saat) -> str:
    if saat is None:
        return "?"
    return "10–11" if saat < 11 else "11–13" if saat < 13 else "13–15" if saat < 15 else "15–18"


def kayip_analizi(kayitlar: list[dict]) -> list[dict]:
    """Her kayıt: kazandi (bool), R, saat, kurulum, sektor, kalite, rejim, mtf. Boyutlara göre gruplar;
    en kötü grupları öne çıkarır."""
    if len(kayitlar) < 8:
        return []
    boyutlar = [
        ("Giriş saati", lambda k: _saat_dilimi(k.get("saat"))),
        ("Sinyal türü", lambda k: KURULUM_ADI.get(k.get("kurulum", ""), (k.get("kurulum", "")[2:] + " kırılımı") if str(k.get("kurulum", "")).startswith("f-") else k.get("kurulum") or "?")),
        ("Sektör", lambda k: k.get("sektor") or "?"),
        ("Kalite", lambda k: k.get("kalite") or "?"),
        ("Piyasa rejimi", lambda k: REJIM_ADI.get(int(k.get("rejim") or 0), "?")),
        ("Üst zaman dilimi", lambda k: {1: "Aynı yönde", -1: "Ters yönde", 0: "Kararsız"}.get(int(k.get("mtf") or 0), "?")),
    ]
    genel = sum(1 for k in kayitlar if k["kazandi"]) / len(kayitlar) * 100
    out = []
    for ad, f in boyutlar:
        gr = {}
        for k in kayitlar:
            gr.setdefault(f(k), []).append(k)
        satir = []
        for anahtar, l in gr.items():
            if len(l) < 3:
                continue
            kaz = sum(1 for k in l if k["kazandi"]) / len(l) * 100
            satir.append(dict(ad=str(anahtar), n=len(l), kazanma=round(kaz), ortR=_r(float(np.mean([k["R"] for k in l])), 2)))
        if len(satir) >= 2:
            satir.sort(key=lambda x: x["kazanma"])
            out.append(dict(boyut=ad, satirlar=satir, fark=satir[-1]["kazanma"] - satir[0]["kazanma"]))
    out.sort(key=lambda x: -x["fark"])
    for b in out:
        b["genel"] = round(genel)
    return out


def sinyal_kayitlari(tum: list[dict], ctxler: dict) -> list[dict]:
    """Geçmiş testteki bitmiş sinyalleri kayıp analizine uygun biçime çevirir."""
    out = []
    for s in tum:
        if s["sonuc"] not in ("hedef", "stop"):
            continue
        risk = abs(s["fiyat"] - s["stop"]) / s["fiyat"] if s["fiyat"] else 0
        R = max(min(s["getiri"] / risk if risk else 0, 6), -1.5)
        kal = ("A+" if s["guven"] >= 80 and s["guclu"] and s["rk"] >= 2 else
               "A" if s["guven"] >= 70 and s["rk"] >= 1.5 else "B" if s["guven"] >= 60 else "C")
        out.append(dict(kazandi=s["sonuc"] == "hedef", R=R, saat=pd.Timestamp(s["zaman"]).hour if s.get("zaman") is not None else None,
                        kurulum=s.get("kurulum", ""), sektor=sektor_bul(s.get("sym", "")), kalite=kal, rejim=s.get("rejim", 0), mtf=s.get("mtf", 0)))
    return out


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
        self.ortak = Ortak(depo_kur("ortak.json"))
        global OGRENCI
        self.ogrenci = OGRENCI = Ogrenci(depo_kur("ogrenme.json"))
        self.canli = CanliBot(depo_kur(), bildir=lambda b_, m_, e_: self.ortak.gonder(b_, m_, e_, tur="bot"))
        klasor = os.path.dirname(os.path.abspath(__file__))
        self.rakipler = {k: CanliBot(depo_kur(f"bot_{k}.json"), os.path.join(klasor, f"bot_{k}.json"), v["ad"], v["ayar"])
                         for k, v in RAKIPLER.items()}
        self.kayip = {m: [] for m in MODLAR}
        self.haber = HaberServis()
        threading.Thread(target=self._dongu, daemon=True).start()

    def sayfa(self, mesaj: str | None = None) -> str:
        b = self.canli.ui(self.bist_p)
        b["yaris"] = [dict(self.canli.kisa_ozet(), anahtar="ana", aciklama="Senin ayarların")] + [
            dict(r.kisa_ozet(), anahtar=k, aciklama=RAKIPLER[k]["aciklama"]) for k, r in self.rakipler.items()]
        b["ortak"] = self.ortak.ui()
        b["ogren"] = self.ogrenci.ui()
        bot = json.dumps(b, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        return (ARAYUZ.replace("__BOT__", bot).replace("__MESAJ__", json.dumps(mesaj, ensure_ascii=False))
                .replace("__VERI__", self.veri))

    def _dongu(self):
        """Hızlı tarama + bot sürekli döner. Derin geçmiş testi sadece seans KAPALIYKEN ve sırayla çalışır
        (bellek sınırını aşmamak ve seans içinde botu bekletmemek için)."""
        while True:
            try:
                self._tur(derin=False)
                self.hata = None
            except Exception as e:  # noqa: BLE001
                self.hata = f"{type(e).__name__}: {e}"
            gc.collect()
            acik = seans_acik_mi()
            if not acik and time.time() - self.derin_zaman > 3 * 3600:
                try:
                    self._derin()
                except Exception as e:  # noqa: BLE001
                    self.hata = f"Derin test: {type(e).__name__}: {e}"
                gc.collect()
            time.sleep(45 if acik else 600)

    def _derin(self):
        """Geçmiş test, karne, öğrenen model ve hata analizi. Her zaman dilimi ayrı ayrı ve hisse hisse işlenir;
        analiz biter bitmez büyük veri bellekten atılır, sadece sinyal sonuçları kalır."""
        gunluk = self.gunluk or gunluk_veri()
        self.gunluk = gunluk
        likitler = [h for h in TUM_HISSELER if h in gunluk and len(gunluk[h]) >= 20
                    and (gunluk[h]["Close"] * gunluk[h]["Volume"]).tail(20).mean() / 1e6 >= MIN_LIKIDITE]
        hizli = sorted(likitler, key=lambda h: -(gunluk[h]["Close"] * gunluk[h]["Volume"]).tail(20).mean())[:HIZLI_EVREN]
        xug = gunluk.get("XU100")
        xu = _gun_ici(["XU100"]).get("XU100")
        if (xu is None or len(xu) <= 40) and xug is not None and len(xug) > 60:
            xu = pd.DataFrame({"Close": xug["Close"].shift(1)}).dropna()
            xu.index = xu.index.tz_localize(TZ) + pd.Timedelta(hours=9)
        acik = seans_acik_mi()
        for mod in ("w", "g", "5", "1"):
            semb = hizli if mod in ("1", "5") else likitler
            if mod == "w":
                kaynak = gunluk
            else:
                kaynak = _gun_ici(semb, *({"g": ("30d", "15m"), "5": ("20d", "5m"), "1": ("5d", "1m")}[mod]))
            tum = []
            for h in semb:
                try:
                    a = hisse_analiz(h, kaynak.get(h), gunluk.get(h), xug if mod == "w" else xu, not acik, tam_test=True, mod=mod)
                except Exception:  # noqa: BLE001
                    a = None
                if not a:
                    continue
                f = filtrele(a["sinyaller"], ESIK)
                df, n = a["ctx"]["df"], a["ctx"]["n"]
                for s_ in f:
                    s_["sym"] = h
                self.derin_sin[mod][h] = [kompakt(sinyal_json(s_, df, n, a["fiyat"], mod)) for s_ in f]
                for s_ in f:                              # sinyal kayıtlarında büyük nesne tutma
                    s_.pop("_j", None)
                tum += f
                del a
            del kaynak
            self.karne[mod], AGIRLIK[mod] = karne_hesapla(tum)
            self.bot[mod] = bot_portfoyu(tum)
            hatalardan_ogren(tum, mod)
            try:
                self.ogrenci.test_yukle(mod, tum)
            except Exception:  # noqa: BLE001
                pass
            try:
                self.kayip[mod] = kayip_analizi(sinyal_kayitlari(tum, None))
            except Exception:  # noqa: BLE001
                self.kayip[mod] = []
            try:
                MODEL[mod] = model_egit(tum)
            except Exception as e:  # noqa: BLE001
                MODEL[mod] = dict(aktif=False, n=0, auc=None, neden=f"eğitim hatası: {e}")
            del tum
            gc.collect()
        self.derin_zaman = time.time()

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
                hatalardan_ogren(tum, mod)
                try:
                    self.kayip[mod] = kayip_analizi(sinyal_kayitlari(tum, None))
                except Exception:  # noqa: BLE001
                    self.kayip[mod] = []
                try:
                    MODEL[mod] = model_egit(tum)
                except Exception as e:  # noqa: BLE001
                    MODEL[mod] = dict(aktif=False, n=0, auc=None, neden=f"eğitim hatası: {e}")
            self.derin_zaman = time.time()
            return                                   # derin test sadece karne/model/öğrenmeyi günceller; botu ve sayfayı hızlı tarama besler

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

        # Haberler: sinyali olan, botun elindeki ve en likit hisseler öncelikli
        oncelik = [p["s"] for p in self.canli.d.get("poz", [])]
        for mod in ("g", "5", "1", "w"):
            for h, a in analiz[mod].items():
                if any(s["sonuc"] == "açık" and a["ctx"]["n"] - 1 - s["i"] <= 12 for s in a["sinyaller"][-3:]):
                    oncelik.append(h)
        oncelik += hizli
        self.haber.hedef_ayarla(oncelik)
        haber_ozet = haber_uygula(analiz, self.haber)

        # Öğrenen beyin: gölge işlemleri yeni mumlarla ilerlet (hedef mi stop mu önce geldi)
        try:
            self.ogrenci.guncelle(analiz)
        except Exception as e:  # noqa: BLE001
            self.hata = f"Öğrenme: {type(e).__name__}: {e}"
        # Canlı bot: yeni sinyallere gir, açık pozisyonları yönet
        self.durum = "Canlı bot pozisyonları güncelliyor"
        try:
            self.canli.tik(analiz, acik, self.bist_p, bist["d"] if bist else None, haber_ozet)
        except Exception as e:  # noqa: BLE001
            self.hata = f"Bot: {type(e).__name__}: {e}"
        for r in self.rakipler.values():
            try:
                r.tik(analiz, acik, self.bist_p, bist["d"] if bist else None, haber_ozet)
            except Exception as e:  # noqa: BLE001
                self.hata = f"Rakip bot: {type(e).__name__}: {e}"
        try:                                     # fiyat alarmları ve A+ sinyal bildirimleri
            fiyatlar = {h: a["fiyat"] for m in ("w", "g", "5", "1") for h, a in analiz[m].items()}
            self.ortak.kontrol(fiyatlar)
            if acik:
                self.ortak.sinyal_bildir(analiz)
        except Exception as e:  # noqa: BLE001
            self.hata = f"Bildirim: {type(e).__name__}: {e}"

        hisseler = []
        for h in likitler:
            if not any(h in analiz[m] for m in MODLAR):
                continue
            ana = next(analiz[m][h] for m in ("g", "w", "5", "1") if h in analiz[m])
            kayit = dict(s=h, sek=sektor_bul(h), lik=_r(ana["likidite"], 1), hizli=h in hizli)
            oz = haber_ozet.get(h)
            if oz:
                kayit["hb"] = dict(skor=oz["skor"], l=oz["liste"][:6])
            for mod in MODLAR:
                a = analiz[mod].get(h)
                kayit[mod] = mod_json(a, self.derin_sin[mod].get(h)) if a else None
            hisseler.append(kayit)
        akis = akis_olaylari(analiz)
        simdi_t = time.time()
        for h, oz in haber_ozet.items():          # önemli haberler canlı akışa
            for hb in (oz or {}).get("liste", [])[:3]:
                if abs(hb["p"]) >= 2 and simdi_t - hb["t"] <= 24 * 3600:
                    akis.append(dict(t=hb["t"] + 3 * 3600, s=h, mod="g", tip="HABER", metin=hb["b"], fiyat=analiz["g"][h]["fiyat"] if h in analiz["g"] else None,
                                     alt=("Olumlu haber" if hb["p"] > 0 else "Olumsuz haber") + (f" · {hb['k']}" if hb["k"] else ""), p=hb["p"],
                                     u=hb["u"], id=f"{h}-hb-{hb['t']}"))
        akis.sort(key=lambda x: -x["t"])
        paket = dict(hisseler=hisseler, akis=akis, vade=VADE, dilim=DILIM_ADI, bist=bist, sektorler=sektor_ozeti(analiz["g"]), karne=self.karne, bot=self.bot,
                     haber_durum=dict(son=f"{dt.datetime.fromtimestamp(self.haber.son_basari, TZ):%H:%M}" if self.haber.son_basari else None,
                                      hata=self.haber.hata, adet=sum(1 for v in haber_ozet.values() if v)),
                     kayip=self.kayip, rejim=REJIM_ADI.get(int(rejim_serisi(xug["Close"]).iloc[-1]) if xug is not None and len(xug) > 60 else 0),
                     adapt={m: {k: ADAPT[m].get(k) for k in ("n", "notlar", "dagilim", "stop_ek", "kirilim_min")} for m in MODLAR}, neden_adi=NEDEN_ADI,
                     model={m: (None if not MODEL[m] else {k: MODEL[m].get(k) for k in ("aktif", "n", "auc", "oran", "onemli", "neden")}) for m in MODLAR},
                     seans=acik, guncelleme=f"{dt.datetime.now(TZ):%H:%M}", taranan=len(TUM_HISSELER),
                     likit=len(likitler), ufuk=TEST_UFKU, esik=ESIK,
                     derin=f"{dt.datetime.fromtimestamp(self.derin_zaman, TZ):%H:%M}" if self.derin_zaman else None)
        self.veri = json.dumps(paket, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        self.surum += 1
        self.durum, self.ilerleme = "Hazır", 1.0


@st.cache_resource
def servis_al_v6(surum: str = "guclu-1") -> Servis:
    # Ad ve sürüm değişince Streamlit önceki app.py'den kalan eski servisi kullanmaz
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

servis = servis_al_v6()
if not hasattr(servis, "canli") or not hasattr(servis.canli, "depo") or not hasattr(servis, "haber") or not hasattr(servis, "rakipler") or not hasattr(servis, "ogrenci"):   # önbellekte eski sürüm kalmışsa yeniden kur
    st.cache_resource.clear()
    servis = servis_al_v6()

mesaj = None
try:
    sorgu = st.query_params.to_dict()
except Exception:  # noqa: BLE001
    sorgu = {}
if sorgu.get("bot") == "yaris_sifirla":
    for r_ in servis.rakipler.values():
        r_.komut({"bot": "sifirla", "butce": str(servis.canli.d["ayar"]["butce"])})
    mesaj = "Yarıştaki rakip botlar sıfırlandı"
    st.query_params.clear()
elif sorgu.get("bot"):          # sitedeki bot ayarları / komutları adres satırıyla gelir
    mesaj = servis.canli.komut(sorgu)
    st.query_params.clear()
elif sorgu.get("alarm") or sorgu.get("bildirim"):
    mesaj = servis.ortak.komut(sorgu)
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
