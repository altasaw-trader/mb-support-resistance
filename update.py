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

def levels(df, price, point, pair, tf='H1'):
    """Confirmed 3/3 swings; rank by proximity after volatility-based filtering."""
    highs=df['High'].to_numpy(); lows=df['Low'].to_numpy(); n=len(df)
    pivots_r=[]; pivots_s=[]
    for i in range(3,n-3):
        if highs[i]>max(highs[i-3:i]) and highs[i]>=max(highs[i+1:i+4]):
            pivots_r.append(float(highs[i]))
        if lows[i]<min(lows[i-3:i]) and lows[i]<=min(lows[i+1:i+4]):
            pivots_s.append(float(lows[i]))
    median_range=float((df['High']-df['Low']).tail(min(n,50)).median())
    if not math.isfinite(median_range) or median_range<=0: median_range=point*20
    tolerance=max(point*10,median_range*.12)
    # Exclude micro-levels: 25% of recent median candle range, minimum 10 points.
    min_distance=max(point*10,median_range*.25)
    decimals=3 if pair.endswith('JPY') else 5
    def select(values,above):
        eligible=[v for v in values if (v-price>=min_distance if above else price-v>=min_distance)]
        eligible.sort(reverse=not above)
        chosen=[]
        for value in eligible:
            if any(abs(value-v['raw'])<=tolerance for v in chosen): continue
            touches=sum(abs(x-value)<=tolerance for x in values)
            strength='strong' if touches>=3 else ('medium' if touches==2 else 'normal')
            chosen.append({'raw':value,'price':round(value,decimals),
                           'points':round(abs(value-price)/point,1),
                           'touches':touches,'strength':strength})
            if len(chosen)==6:break
        return chosen
    rr=select(pivots_r,True); ss=select(pivots_s,False)
    for items in (rr,ss):
        for item in items:item.pop('raw')
    return {'R':[v['price'] for v in rr], 'S':[v['price'] for v in ss],
            'R_info':rr,'S_info':ss,'min_distance_points':round(min_distance/point,1),
            'bars':n,'asof':str(df.index[-1]),'price':round(price,decimals)}

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
                try:entry[tf]={'status':'ok',**levels(df,float(df['Close'].iloc[-1]),point,pair,tf)}
                except Exception as exc:failures.append(f'{pair} {tf}: {type(exc).__name__}: {str(exc)[:160]}')
            if tf not in entry:
                previous=old.get(pair,{}).get(tf)
                if previous and previous.get('status') in ('ok','stale') and previous.get('bars',0)>=12:
                    entry[tf]={**previous,'status':'stale'}
                else:entry[tf]={'status':'unavailable','R':[],'S':[]}
        result[pair]=entry
    payload={'updated_utc':NOW.isoformat(timespec='seconds'),'version':'V2','source':'Yahoo Finance (unofficial)','method':'V2: 3-left/3-right confirmed swing extrema, volatility-based minimum distance, pivot touch strength; H4 UTC 4h bins','windows':{'M30':'up to 59 days','H1':'up to 700 days','H4':'up to 700 days','D1':'3 years'},'pairs':result,'warnings':failures[:50]}
    OUTPUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print('Updated',len(result),'pairs; missing',sum(1 for p in result.values() for v in p.values() if v['status']=='unavailable'))

if __name__=='__main__':main()
