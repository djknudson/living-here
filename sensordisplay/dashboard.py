#!/usr/bin/env python3
import sys, time, json, urllib.request
sys.path.insert(0, '/home/sensordisplay/display')
from PIL import Image, ImageDraw, ImageFont

DIR='/home/sensordisplay/display'; DEJA='/usr/share/fonts/truetype/dejavu'
MDI=f'{DIR}/materialdesignicons-webfont.ttf'
HA='http://10.0.10.90:8123'
def F(p,s): return ImageFont.truetype(p,s)
BOLD=f'{DEJA}/DejaVuSans-Bold.ttf'; REG=f'{DEJA}/DejaVuSans.ttf'
f_title=F(BOLD,14); f_unit=F(REG,10); f_cap=F(REG,10); f_foot=F(REG,11)
VAL_SIZES=[20,19,18]; _valf={s:F(BOLD,s) for s in VAL_SIZES}
i_icon=F(MDI,32); i_small=F(MDI,16); i_foot=F(MDI,13)
IC_WTEMP=chr(0xF1A80); IC_TDS=chr(0xF058E); IC_ATEMP=chr(0xF050F); IC_PRESS=chr(0xF029A)
IC_FISH=chr(0xF023A); IC_UPD=chr(0xF06B0); IC_WIFI=chr(0xF05A9)

def _fit(d,value,unit,maxw):
    uw=d.textlength(unit,font=f_unit)
    for s in VAL_SIZES:
        vf=_valf[s]; vw=d.textlength(value,font=vf)
        if vw+3+uw<=maxw: return vf,vw
    vf=_valf[VAL_SIZES[-1]]; return vf,d.textlength(value,font=vf)

def tile(d,x,y,icon,value,unit,label):
    d.text((x+4,y+3),icon,font=i_icon,fill=0)
    vf,vw=_fit(d,value,unit,78)          # 78px cap -> stays clear of the panel's right edge
    d.text((x+40,y+2),value,font=vf,fill=0)
    d.text((x+42+vw,y+10),unit,font=f_unit,fill=0)
    d.text((x+40,y+26),label,font=f_cap,fill=0)

def render(v):
    img=Image.new('1',(250,122),255); d=ImageDraw.Draw(img)
    d.rectangle((0,0,249,19),fill=0)
    d.text((5,1),IC_FISH,font=i_small,fill=255); d.text((26,2),'FISHBUCKET',font=f_title,fill=255)
    d.line((125,24,125,104),fill=0); d.line((6,63,244,63),fill=0)
    tile(d,0,22,IC_WTEMP,v['wtemp'],'°F','WATER TEMP')
    tile(d,125,22,IC_TDS,v['tds'],'ppm','TDS')
    tile(d,0,66,IC_ATEMP,v['atemp'],'°F','AIR TEMP')
    tile(d,125,66,IC_PRESS,v['press'],'inHg','PRESSURE')
    d.text((3,106),IC_UPD,font=i_foot,fill=0); d.text((19,107),v['time'],font=f_foot,fill=0)
    d.text((228,106),IC_WIFI,font=i_foot,fill=0)
    return img

def _state(entity,tok):
    try:
        req=urllib.request.Request(f'{HA}/api/states/{entity}',headers={'Authorization':f'Bearer {tok}'})
        with urllib.request.urlopen(req,timeout=8) as r: return json.load(r)['state']
    except Exception: return None
def _fmt(s,dec):
    try: return f'{float(s):.{dec}f}'
    except (TypeError,ValueError): return '--'
def fetch():
    tok=open(f'{DIR}/ha_token').read().strip(); g=lambda e:_state(e,tok)
    return {'wtemp':_fmt(g('sensor.fishbucket_sensors_water_temperature'),1),
            'tds':_fmt(g('sensor.fishbucket_sensors_water_tds'),0),
            'atemp':_fmt(g('sensor.fishbucket_sensors_air_temperature'),1),
            'press':_fmt(g('sensor.fishbucket_sensors_air_pressure'),2),
            'time':time.strftime('%b %d  %H:%M')}

SAMPLE={'wtemp':'77.5','tds':'58','atemp':'75.4','press':'29.86','time':time.strftime('%b %d  %H:%M')}
def main():
    from waveshare_epd import epd2in13_V4
    v=SAMPLE if (len(sys.argv)>1 and sys.argv[1]=='sample') else fetch()
    epd=epd2in13_V4.EPD(); epd.init(); epd.display(epd.getbuffer(render(v))); epd.sleep()
if __name__=='__main__': main()
