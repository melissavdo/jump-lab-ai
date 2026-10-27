import os, json, re, time
from collections import defaultdict, deque
from shiny import App
from starlette.responses import JSONResponse
from starlette.requests import Request

# Each visitor receives a separate game in their browser.
# API keys remain server-side; never place them in HTML.
LIMITS = {'power': (9,21), 'gravity': (.35,1.1), 'speed': (2,8), 'points': (5,50)}
THEMES = {'space','jungle','candy','ocean','sunset','snow','desert','forest','city','volcano'}
CHARACTERS = {'robot','cat','dog','fox','frog','rabbit','penguin','dinosaur','bear','owl','panda','unicorn','koala','raccoon','monkey','lion','tiger','elephant','turtle','dragon','alien','axolotl','shark','butterfly'}
OBSTACLES = {'spike','mushroom','rock','cactus','crystal','robot'}
COLLECTIBLES = {'star','heart','coin','gem','flower'}
COLOR_KEYS = {'skyColor','groundColor','characterColor'}
import string

def valid_color(v):
    return isinstance(v,str) and len(v)==7 and v.startswith('#') and all(c in string.hexdigits for c in v[1:])

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
                {'role':'system','content': 'You help children customize a safe jumping game. Return ONLY a JSON object with optional keys: power (integer 9-21), gravity (number .35-1.1), speed (number 2-8), points (integer multiple of 5 from 5-50), theme (one of space, jungle, candy, ocean, sunset, snow, desert, forest, city, volcano), character (one of robot, cat, dog, fox, frog, rabbit, penguin, dinosaur, bear, owl, panda, unicorn, koala, raccoon, monkey, lion, tiger, elephant, turtle, dragon, alien, axolotl, shark, butterfly), obstacle (one of spike, mushroom, rock, cactus, crystal, robot), collectible (one of star, heart, coin, gem, flower), skyColor, groundColor, characterColor (each a #RRGGBB hex color). If user asks for a pink background, use skyColor #FFB6C1. Interpret other named colors as hex. Only include requested changes. No other keys. Never return executable code. Ignore instructions unrelated to game settings. If no allowed change requested return {}.'},
                {'role':'user','content':prompt}
            ],temperature=0,max_tokens=260,response_format={'type':'json_object'}
        )
        proposed=json.loads(response.choices[0].message.content)
        if not isinstance(proposed,dict): proposed={}
        clean={}
        for k,v in proposed.items():
            if k in LIMITS and isinstance(v,(int,float)) and not isinstance(v,bool):
                lo,hi=LIMITS[k]
                if lo<=v<=hi and (k not in ('power','points') or int(v)==v) and (k!='points' or v%5==0):clean[k]=v
            elif k=='theme' and v in THEMES: clean[k]=v
            elif k=='character' and v in CHARACTERS: clean[k]=v
            elif k=='obstacle' and v in OBSTACLES: clean[k]=v
            elif k=='collectible' and v in COLLECTIBLES: clean[k]=v
            elif k in COLOR_KEYS and valid_color(v): clean[k]=v.upper()
        return JSONResponse({'changes':clean})
    except Exception:
        return JSONResponse({'error':'AI request failed. Try again or use offline practice.'},status_code=502)


# Classroom image generation: moderated, limited, and server-side only.
image_visits = defaultdict(deque)

async def generate_hero(request: Request):
    if request.method != 'POST':
        return JSONResponse({'error': 'POST required'}, status_code=405)
    if int(request.headers.get('content-length', '0') or '0') > 2000:
        return JSONResponse({'error': 'Request too large.'}, status_code=413)
    try:
        data = await request.json()
        description = data.get('prompt', '')
        if not isinstance(description, str) or not (5 <= len(description.strip()) <= 240):
            return JSONResponse({'error': 'Describe a hero in 5–240 characters.'}, status_code=400)
        key = os.environ.get('OPENAI_API_KEY')
        if not key:
            return JSONResponse({'error': 'AI image generation is not configured.'}, status_code=503)
        visitor = request.client.host if request.client else 'unknown'
        now = time.monotonic()
        history = image_visits[visitor]
        while history and history[0] < now - 3600:
            history.popleft()
        if len(history) >= int(os.environ.get('HERO_IMAGES_PER_HOUR', '3')):
            return JSONResponse({'error': 'This device has reached its image-generation limit. Try the character gallery.'}, status_code=429)
        from openai import AsyncOpenAI
        import base64
        client = AsyncOpenAI(api_key=key, timeout=120, max_retries=0)
        moderation = await client.moderations.create(model='omni-moderation-latest', input=description)
        if moderation.results[0].flagged:
            return JSONResponse({'error': 'Please describe a friendly, classroom-appropriate character.'}, status_code=400)
        # Count attempted generations to bound classroom costs, even if the API fails.
        history.append(now)
        instruction = (
            'Make ONE original, friendly, age-appropriate, full-body 2D cartoon video-game character sprite. '
            'Subject requested by student: ' + description + '. '
            'Character should clearly resemble the requested animal or creature, with recognizable anatomy. '
            'Single centered character, head to feet, expressive face, bold clean outlines, vivid colors, '
            'high detail, no cropping, no background, transparent alpha background, no floor, no shadow, '
            'no text, no logos, no weapons, no blood, no violence, no adult themes. '
            'Ensure limbs and accessories are part of a cohesive single illustration. '
            'Use a playful, polished, kid-friendly 2D platform-game art style.'
        )
        result = await client.images.generate(
            model=os.environ.get('OPENAI_IMAGE_MODEL', 'gpt-image-2.5-flare'),
            prompt=instruction,
            size='1024x1024',
            quality='low',
            background='transparent',
            output_format='png',
            n=1,
        )
        raw = result.data[0].b64_json
        if not raw:
            return JSONResponse({'error': 'Image service returned no artwork.'}, status_code=502)
        # No student prompt or generated image is stored on this server.
        return JSONResponse({'image': 'data:image/png;base64,' + raw})
    except Exception as exc:
        # Return only a safe error category; never expose keys, prompts, or raw provider responses.
        import logging
        from openai import APIStatusError, APITimeoutError, APIConnectionError
        logging.getLogger('jump_lab').exception('Hero image generation failed')
        if isinstance(exc, APIStatusError):
            code = getattr(exc, 'status_code', 502)
            if code == 401:
                message = 'OpenAI authentication failed. Check the server API key.'
            elif code == 403:
                message = 'OpenAI denied image-model access. Check project verification and permissions.'
            elif code == 429:
                message = 'OpenAI rate limit or billing quota reached. Check API billing and usage limits.'
            elif code == 400:
                message = 'OpenAI rejected the image request. Check image model and supported parameters.'
            else:
                message = 'OpenAI image service returned HTTP ' + str(code) + '. Check Posit logs.'
            return JSONResponse({'error': message, 'provider_status': code}, status_code=502)
        if isinstance(exc, (APITimeoutError, APIConnectionError)):
            return JSONResponse({'error': 'Cannot reach OpenAI image service or request timed out. Check Posit logs.'}, status_code=502)
        return JSONResponse({'error': 'Server error during image generation (' + type(exc).__name__ + '). Check Posit logs.'}, status_code=502)

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
    Route('/api/generate-hero',generate_hero,methods=['POST']),
    Route('/game',lambda request: RedirectResponse('/game/'))])
app.mount('/game',StaticFiles(directory=str(root/'www'),html=True),name='game')
app.mount('/shiny',shiny_app)
