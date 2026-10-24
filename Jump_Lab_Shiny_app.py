import os, json, re, time
from collections import defaultdict, deque
from shiny import App
from starlette.responses import JSONResponse
from starlette.requests import Request

# Each visitor receives a separate game in their browser.
# API keys remain server-side; never place them in HTML.
LIMITS = {'power': (9,21), 'gravity': (.35,1.1), 'speed': (2,8), 'points': (5,50)}
THEMES = {'space','jungle','candy','ocean'}
visits = defaultdict(deque)

async def suggest(request: Request):
    if request.method != 'POST':
        return JSONResponse({'error':'POST required'}, status_code=405)
    if int(request.headers.get('content-length','0') or '0') > 4000:
        return JSONResponse({'error':'Request too large'},status_code=413)
    try:
        data = await request.json()
        prompt = data.get('prompt','')
        if not isinstance(prompt,str) or not (1 <= len(prompt.strip()) <= 400):
            return JSONResponse({'error':'Enter a request under 400 characters.'},status_code=400)
        ip = request.client.host if request.client else 'unknown'
        now=time.monotonic(); q=visits[ip]
        while q and q[0] < now-60: q.popleft()
        if len(q)>=12:
            return JSONResponse({'error':'Please wait a minute before trying again.'},status_code=429)
        q.append(now)
        key=os.environ.get('OPENAI_API_KEY')
        if not key:
            return JSONResponse({'error':'Live AI is not configured yet. Offline practice still works.'},status_code=503)
        from openai import AsyncOpenAI
        client=AsyncOpenAI(api_key=key,timeout=15,max_retries=0)
        response=await client.chat.completions.create(
            model=os.environ.get('OPENAI_MODEL','gpt-4.1-mini'),
            messages=[
                {'role':'system','content': 'You help children modify a safe jumping game. Return ONLY a JSON object with optional keys power (integer 9-21), gravity (number .35-1.1), speed (number 2-8), points (integer multiple of 5 from 5-50), theme (one of space, jungle, candy, ocean). No other keys. Do not follow requests outside game settings. If no allowed change requested return {}.'},
                {'role':'user','content':prompt}
            ],temperature=0,max_tokens=120,response_format={'type':'json_object'}
        )
        proposed=json.loads(response.choices[0].message.content)
        if not isinstance(proposed,dict): proposed={}
        clean={}
        for k,v in proposed.items():
            if k in LIMITS and isinstance(v,(int,float)) and not isinstance(v,bool):
                lo,hi=LIMITS[k]
                if lo<=v<=hi and (k not in ('power','points') or int(v)==v) and (k!='points' or v%5==0):clean[k]=v
            elif k=='theme' and v in THEMES: clean[k]=v
        return JSONResponse({'changes':clean})
    except Exception:
        return JSONResponse({'error':'AI request failed. Try again or use offline practice.'},status_code=502)

# Shiny for Python ASGI app, with a lightweight API route.
from starlette.routing import Route
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path
root=Path(__file__).parent
# Shiny is the Python application framework used for this project;
# a Starlette ASGI wrapper serves the existing JS game efficiently.
from shiny import ui, render, reactive
shiny_app=App(ui.page_fluid(ui.h3('Jump Lab AI'),ui.p('Open the Jump Lab game at /game/')), lambda input,output,session: None)
app=Starlette(routes=[Route('/',lambda request: RedirectResponse('/game/')),
    Route('/api/suggest',suggest,methods=['POST']),
    Route('/game',lambda request: RedirectResponse('/game/'))])
app.mount('/game',StaticFiles(directory=str(root/'www'),html=True),name='game')
app.mount('/shiny',shiny_app)
