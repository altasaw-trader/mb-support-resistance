import json, math, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd
import yfinance as yf

PAIRS='AUDCAD AUDCHF AUDJPY AUDNZD AUDUSD CADCHF CADJPY CHFJPY EURAUD EURCAD EURCHF EURGBP EURJPY EURNZD EURUSD GBPAUD GBPCAD GBPCHF GBPJPY GBPNZD GBPUSD NZDCAD NZDCHF NZDJPY NZDUSD USDCAD USDCHF USDJPY'.split()
CONFIG={'M30':('30m','59d',timedelta(minutes=30)), 'H1':('60m','700d',timedelta(hours=1)), 'D1':('1d','3y',timedelta(days=1))}
NOW=datetime.now(timezone.utc)
OUTPUT=Path(__file__).resolve().parent/'data.json'

def fetch(pair, interval, period, duration):
    df=yf.download(pair+'=X',period=period,interval=interval,progress=False,auto_adjust=False,threads=False,timeout=25)
    if df is None or df.empty:return None
    if isinstance(df.columns,pd.MultiIndex):df.columns=df.columns.get_level_values(0)
    df=df[['High','Low','Close']].apply(pd.to_numeric,errors='coerce').dropna()
    if df.empty:return None
    idx=pd.to_datetime(df.index,utc=True)
    df=df.loc[(idx+duration)<=pd.Timestamp(NOW)]
    return df if len(df)>=12 else None

def levels(df,price,point,pair):
    highs=df['High'].to_numpy();lows=df['Low'].to_numpy();n=len(df)
    left=3;right=3
    resistance=[];support=[]
    for i in range(left,n-right):
        if highs[i]>max(highs[i-left:i]) and highs[i]>=max(highs[i+1:i+right+1]): resistance.append(float(highs[i]))
        if lows[i]<min(lows[i-left:i]) and lows[i]<=min(lows[i+1:i+right+1]): support.append(float(lows[i]))
    # Cluster near-duplicate swing levels; avoid displaying effectively identical prices.
    spread=float((df['High']-df['Low']).tail(min(n,50)).median())
    tolerance=max(point*10,spread*0.12)
    def unique(values,reverse=False):
        result=[]
        for value in sorted(values,reverse=reverse):
            if all(abs(value-v)>tolerance for v in result):result.append(value)
            if len(result)==6:break
        return result
    r=unique([v for v in resistance if v>price]);s=unique([v for v in support if v<price],True)
    decimals=3 if pair.endswith('JPY') else 5
    return {'R':[round(x,decimals) for x in r], 'S':[round(x,decimals) for x in s], 'bars':n, 'asof':str(df.index[-1]),'price':round(price,decimals)}

def main():
    old={}
    if OUTPUT.exists():
        try:old=json.loads(OUTPUT.read_text()).get('pairs',{})
        except Exception:pass
    result={};failures=[]
    for pair in PAIRS:
        entry={}; point=.001 if pair.endswith('JPY') else .00001
        raw={}
        for tf,(interval,period,duration) in CONFIG.items():
            try:raw[tf]=fetch(pair,interval,period,duration)
            except Exception as exc:
                raw[tf]=None;failures.append(f'{pair} {tf}: {type(exc).__name__}: {str(exc)[:160]}')
            time.sleep(.15)
        # H4 synthesized from H1, aligned to UTC 00/04/08/12/16/20.
        if raw.get('H1') is not None:
            h=raw['H1']; h4=h.resample('4h',origin='start_day',label='left',closed='left').agg({'High':'max','Low':'min','Close':'last'})
            counts=h['Close'].resample('4h',origin='start_day',label='left',closed='left').count()
            raw['H4']=h4[counts>=4].dropna()
        else:raw['H4']=None
        for tf in ['M30','H1','H4','D1']:
            df=raw.get(tf)
            if df is not None and len(df)>=12:
                try:entry[tf]={'status':'ok',**levels(df,float(df['Close'].iloc[-1]),point,pair)}
                except Exception as exc:failures.append(f'{pair} {tf}: {type(exc).__name__}: {str(exc)[:160]}')
            if tf not in entry:
                previous=old.get(pair,{}).get(tf)
                if previous and previous.get('status') in ('ok','stale') and previous.get('bars',0)>=12:
                    entry[tf]={**previous,'status':'stale'}
                else:entry[tf]={'status':'unavailable','R':[],'S':[]}
        result[pair]=entry
    payload={'updated_utc':NOW.isoformat(timespec='seconds'),'source':'Yahoo Finance (unofficial)','method':'3-left/3-right confirmed swing extrema, nearby levels clustered; H4 derived from H1 using UTC 4h bins','windows':{'M30':'up to 59 days','H1':'up to 700 days','H4':'up to 700 days','D1':'3 years'},'pairs':result,'warnings':failures[:50]}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print('Updated',len(result),'pairs; missing',sum(1 for p in result.values() for v in p.values() if v['status']=='unavailable'))

if __name__=='__main__':main()
