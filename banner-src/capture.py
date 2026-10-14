import sys, base64, io, time, urllib.parse, json
from playwright.sync_api import sync_playwright
from PIL import Image

FRAMES = int(sys.argv[1]); SUB = 2
params = dict(a.split('=') for a in sys.argv[2:])
q = urllib.parse.urlencode(params)
out = []
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width':960,'height':250})
    pg.goto(f'file://./index.html?{q}')
    pg.wait_for_function('window.__ready===true')
    # overlay: text + shade + border only, transparent elsewhere
    pg.add_style_tag(content='#veil{visibility:hidden}#banner{background:transparent!important;box-shadow:none!important}')
    pg.evaluate("()=>{window.requestAnimationFrame=window.__origRaf}")
    pg.screenshot(path='./overlay.png', omit_background=True)
    pg.evaluate("()=>{window.requestAnimationFrame=function(cb){window.__cbs.push(cb);return window.__cbs.length;}}")
    ts = 1000.0; t0 = time.time()
    for f in range(FRAMES):
        data = None
        for s in range(SUB):
            last = (s == SUB-1)
            js = f"window.__step({ts});const c=document.querySelector('canvas');" + ("c.toDataURL('image/png')" if last else "c.getContext('webgl2').finish()")
            data = pg.evaluate(js); ts += 1000/30
        out.append(Image.open(io.BytesIO(base64.b64decode(data.split(',')[1]))).convert('RGBA'))
        if f % 15 == 0: print('frame', f, round(time.time()-t0,1), 's', flush=True)
    b.close()
import pickle
pickle.dump([im.tobytes() for im in out], open('./frames.pkl','wb'))
print('size', out[0].size, 'frames', len(out))
