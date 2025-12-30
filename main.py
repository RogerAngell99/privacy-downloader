import datetime
from time import sleep
import playwright.async_api as pw
from playwright.async_api import expect
# from playwright_stealth import stealth_async  # Desativado - causava problemas no carregamento
from config import settings
from sqlalchemy.engine.result import ScalarResult
import httpx
import os
import hashlib
import datetime as datetime
import metadata as meta
import asyncclick as click
import asyncio
import multiprocessing
from tqdm.asyncio import tqdm
import re
from dateutil.parser import parse
import time
from requests.models import Response
import platform
import sys

# Detecção de ambiente Android/Termux
is_android = hasattr(sys, 'getandroidapilevel') or 'ANDROID_ROOT' in os.environ or os.path.exists('/data/data/com.termux')
is_termux = 'com.termux' in os.environ.get('PREFIX', '') or os.path.exists('/data/data/com.termux')
is_windows = platform.system() == 'Windows'

def get_terminal_cols():
    """Obtém colunas do terminal de forma segura (funciona no Termux)."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        # Fallback para Termux/Android ou quando não há TTY
        try:
            import shutil
            return shutil.get_terminal_size().columns
        except:
            return 80  # Valor padrão seguro

url = "https://privacy.com.br/"
base_url = "https://privacy.com.br/profile/"
page_url = "https://privacy.com.br/Index?handler=PartialPosts&skip={0}&take={1}&nomePerfil={2}&agendado=false"
following_url = "https://privacy.com.br/Follow?Type=Following"
# Nova API de timeline (substituiu PartialPosts)
timeline_api_url = "https://service.privacy.com.br/timelinequeries/profile/{0}/{1}/{2}"
captured_timeline_data = []  # Armazena dados capturados da API
profile = ""
hdr = ""
filesTotal = 0
savedTotal = 0
postsTotal = 0
linksTotal = 0
metadata = ""
postContent = ''
prevPostId = ''
numPosts = 0
termCols = 0
responses = ''
postBar: tqdm
linkBar: tqdm
downloadBar: tqdm
global barFormat
barFormat = '{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}, {rate_fmt}]'


async def check_url(url, headers, cookies, timeout):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.head(url, headers=headers, cookies=cookies, timeout=timeout)
            return response
        except httpx.ReadTimeout as e:
            return f"ReadTimeout: {e}"
        except httpx.ConnectTimeout as e:
            return f"ConnectTimeout: {e}"
        except httpx.RequestError as e:
            return f"RequestError: {e}"

# Funcao para mostrar os nomes dos perfis e numeros
def display_profiles(profile_names):
    print("Perfis:")
    for i, profile_name in enumerate(profile_names):
        print(f"{i + 1}. {profile_name}")

async def fetch_profiles(page: pw.Page, profile, backlog):
    await page.goto(base_url + profile)
    #procura aba (link) de postagens
    print(f"Procurando página de postagens do perfil {profile}...")
    global numPosts
    # Busca mais robusta: procura por link que contém "postagen" (postagens/postagem)
    await page.wait_for_load_state('networkidle', timeout=30000)
    posts_locator = page.locator('a').filter(has_text=re.compile(r'\d+.*postagen', re.IGNORECASE))
    try:
        await expect(posts_locator.first).to_be_visible(timeout=15000)
        posts = await posts_locator.first.text_content()
    except AssertionError:
        # Fallback: tenta buscar qualquer elemento com texto de postagens
        posts_locator = page.get_by_text(re.compile(r'\d+\s*(k\s*)?postagen', re.IGNORECASE))
        posts = await posts_locator.first.text_content()

    numPosts = posts.strip().split(' ')[0].replace('.','')
    if 'k' in numPosts:
        numPosts = numPosts.replace('k','')
        numPosts = f"{numPosts}000" 
    numPosts = int(numPosts)

    js = await page.evaluate_handle('navigator')
    ua = await js.evaluate('navigator.userAgent')
    global hdr
    hdr = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
        'User-Agent': str(ua),
        'origin': 'https://privacy.com.br',
        'Referer': 'https://privacy.com.br'
    }

    jar = await refreshCookies(page)

    if not backlog:
        print("Buscando postagens com mídia...")
        await fetchLinks(page, jar, profile)
    else:
        print("Atenção: apenas baixando backlog do banco de dados! A página não vai ser varrida agora.")
    
    # Download usando método híbrido (Playwright + FFmpeg)
    global metadata
    if type(metadata) == str:
        openDatabase()
    if metadata.getMediaDownloadCount() > 0:
        await downloadHybrid(page, profile)
    else:
        print('Sem mídia para baixar.')


async def fetchLinks(page: pw.Page, jar, profile):
    """
    Busca links de mídia usando interceptação de rede.
    A nova API usa: https://service.privacy.com.br/timelinequeries/profile/{skip}/{take}/{profile}
    """
    global numPosts, postBar, linkBar, linksTotal, metadata, postsTotal, captured_timeline_data
    
    # Limpa dados capturados anteriores
    captured_timeline_data = []
    
    # Handler para interceptar respostas da API de timeline
    async def handle_response(response):
        if 'timelinequeries/profile' in response.url or 'mediavideotoken' in response.url:
            try:
                if response.status == 200:
                    json_data = await response.json()
                    captured_timeline_data.append({
                        'url': response.url,
                        'data': json_data
                    })
            except Exception as e:
                print(f"Erro ao processar resposta: {e}")
    
    # Registra o handler de resposta
    page.on('response', handle_response)
    
    linkBar = tqdm(total=linksTotal, colour='magenta', dynamic_ncols=True, position=1, desc='Mídia...', delay=5, bar_format=barFormat)
    postBar = tqdm(total=numPosts, colour='yellow', dynamic_ncols=True, position=0, desc='Postagem...', delay=5, bar_format=barFormat)
    
    # Navega para a página do perfil para disparar carregamento
    await page.goto(base_url + profile, timeout=90000)
    await page.wait_for_load_state('networkidle', timeout=30000)
    
    # Rola a página para carregar mais posts
    previous_count = 0
    max_scrolls = 50  # Limite de scrolls para evitar loop infinito
    scroll_count = 0
    
    print("Rolando página para carregar posts...")
    while scroll_count < max_scrolls:
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)  # Espera carregamento
        
        current_count = len(captured_timeline_data)
        if current_count == previous_count:
            # Se não houver novos dados após o scroll, para
            scroll_count += 1
            if scroll_count >= 3:  # 3 tentativas sem novos dados
                break
        else:
            scroll_count = 0  # Reset do contador
            previous_count = current_count
            postBar.update(len(captured_timeline_data))
    
    # Remove o handler para evitar duplicação
    page.remove_listener('response', handle_response)
    
    jar = await refreshCookies(page)
    
    # Processa os dados capturados
    print(f"Capturados {len(captured_timeline_data)} respostas da API. Processando...")
    
    # DEBUG: Mostra estrutura do primeiro JSON capturado
    if captured_timeline_data:
        import json
        print("\nDEBUG - URLs capturadas:")
        for i, resp in enumerate(captured_timeline_data):
            url = resp.get('url', 'N/A')
            data = resp.get('data', {})
            print(f"  [{i}] {url[:80]}...")
            
        # Procura especificamente por timelinequeries
        timeline_responses = [r for r in captured_timeline_data if 'timelinequeries' in r.get('url', '')]
        print(f"\nRespostas de timelinequeries: {len(timeline_responses)}")
        
        if timeline_responses:
            first_timeline = timeline_responses[0]
            print(f"URL Timeline: {first_timeline.get('url', 'N/A')}")
            data = first_timeline.get('data', {})
            if isinstance(data, list) and len(data) > 0:
                print(f"Tipo: Lista com {len(data)} itens")
                print(f"Primeiro item keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'não é dict'}")
                print(f"Amostra JSON: {json.dumps(data[0], indent=2, default=str)[:2000]}...")
            elif isinstance(data, dict):
                print(f"Tipo: Dict com keys: {list(data.keys())}")
                print(f"Amostra JSON: {json.dumps(data, indent=2, default=str)[:2000]}...")
        else:
            print("NENHUMA resposta de timelinequeries capturada!")
    
    await parseTimelineData(captured_timeline_data, profile)
    
    postBar.close()
    linkBar.close()
    
    openDatabase()
    print(f"{postsTotal} postagens com texto e mídia, {metadata.getMediaCount()} mídias encontradas. Baixando {metadata.getMediaDownloadCount()} mídias.")


async def parseTimelineData(timeline_data, profile):
    """
    Processa dados da timeline capturados da nova API.
    Extrai posts e mídias do JSON retornado.
    """
    openDatabase()
    global metadata, postsTotal, linksTotal, linkBar, prevPostId, termCols
    
    mediaCount = 0
    
    for response_data in timeline_data:
        if 'timelinequeries/profile' not in response_data.get('url', ''):
            continue
            
        data = response_data.get('data', {})
        
        # Os posts estão em data['items']
        if isinstance(data, dict):
            posts = data.get('items', [])
        elif isinstance(data, list):
            posts = data
        else:
            continue
        
        for post in posts:
            if not isinstance(post, dict):
                continue
                
            postId = post.get('id') or post.get('postId') or post.get('mediaId', '')
            if not postId:
                continue
                
            postId = str(postId)
            
            # Salva o post
            postContent = post.get('text') or post.get('description') or post.get('caption', '')
            if postId != prevPostId:
                postinfo = {
                    'post_id': postId,
                    'post_text': postContent.strip() if postContent else '',
                }
                metadata.savePost(postinfo)
                postsTotal += 1
                prevPostId = postId
                mediaCount = 1
            
            # Processa mídias do post
            medias = post.get('medias') or post.get('media') or post.get('files') or []
            if not isinstance(medias, list):
                medias = [medias]
            
            for media in medias:
                if not isinstance(media, dict):
                    continue
                    
                # Pula mídias bloqueadas
                if media.get('isLocked', False):
                    continue
                
                media_url = media.get('url') or media.get('src') or media.get('link', '')
                if not media_url:
                    continue
                
                media_type = media.get('type', 'image').lower()
                if 'video' in media_type or '.mp4' in media_url or '.m3u8' in media_url:
                    media_type = 'video'
                    extension = '.mp4'  # Salva como .mp4 mesmo sendo HLS
                else:
                    media_type = 'image'
                    extension = '.jpg'
                
                filename = f"{postId}-{str(mediaCount).rjust(3, '0')}{extension}"
                filepath = os.path.join(settings.downloaddir, profile, media_type)
                os.makedirs(name=filepath, exist_ok=True)
                
                imgHash = hashlib.md5(str(media_url).encode('utf-8')).hexdigest()
                
                mediainfo = {
                    'media_id': imgHash,
                    'post_id': postId,
                    'link': media_url,
                    'inner_link': media_url,
                    'directory': filepath,
                    'filename': filename,
                    'size': 0,
                    'media_type': media_type,
                    'downloaded': False,
                    'created_at': datetime.datetime.now()
                }
                
                if not metadata.checkSaved(mediainfo):
                    metadata.saveLinks(mediainfo)
                    linksTotal += 1
                    linkBar.total = linksTotal
                    
                if termCols < 80:
                    desc = f"M {truncate_middle(filename, 12)}"
                else:
                    desc = f"Mídia {filename}"
                linkBar.set_description(desc)
                linkBar.update()
                mediaCount += 1
                
                await asyncio.sleep(0)
    

async def parseLinks(divs, profile):
    openDatabase()
    mediaCount = 0
    for d in divs:
        privacy_web_mediahub_carousel = await d.locator('//privacy-web-mediahub-carousel').all()
        if privacy_web_mediahub_carousel:
            for carousel_element in privacy_web_mediahub_carousel:
                carousel = await carousel_element.evaluate('(element) => element.getAttribute("medias")')                                    
            postTag = d.get_by_role('paragraph')
            id_div = await d.locator('css=div.post-view-full').get_attribute('id')
            postId = id_div.replace('Postagem','')
            global prevPostId
            if prevPostId != postId: #postContent != postTag.text:
                global termCols
                if termCols < 80:
                    desc = f"P {truncate_middle(postId,12)}"
                else:
                    desc = f"Post  {postId}"
                postBar.set_description(desc)
                postBar.update()
                global postContent
                try:
                    await expect(postTag).to_have_count(count=1,timeout=2)
                    postContent = await postTag.text_content()
                    postContent = postContent.strip()
                    postinfo = {
                        'post_id': postId,
                        'post_text': postContent,
                    }
                    metadata.savePost(postinfo)
                    global numPosts
                    global postsTotal
                    postsTotal += 1
                except AssertionError:
                    pass
        
            global linkBar, linkBarD
            await asyncio.sleep(0)

            # Extraindo as midias do carrosel
            matches = re.findall(r'\{"isLocked":false,"mediaId":".*?","type":"(.*?)","url":"(.*?)".*?\}', carousel)

            # Construindo um dicionario para pegar o media_type de cada arquivo
            media_info = {media_link: media_type for media_type, media_link in matches if media_link and media_type}

            for media_link, media_type in media_info.items():            
                if prevPostId != postId:
                    mediaCount = 1
                    prevPostId = postId
                imgHash = hashlib.md5(str(media_link).encode('utf-8')).hexdigest()
                if "mp4" in media_link:
                    filename = postId + '-' + str(mediaCount).rjust(3,'0') + '.mp4'
                    media_type = 'video'
                else:
                    filename = postId + '-' + str(mediaCount).rjust(3,'0') + '.jpg'
                    media_type = 'image'
                filepath = os.path.join(settings.downloaddir, profile, media_type)
                os.makedirs(name=filepath, exist_ok=True)
                mediainfo = {
                    'media_id': imgHash,
                    'post_id': postId,
                    'link': media_link,
                    'inner_link': media_link,
                    'directory': filepath,
                    'filename': filename,
                    'size': 0,
                    'media_type': media_type,
                    'downloaded': False,
                    'created_at': datetime.datetime.now()
                }
                if not metadata.checkSaved(mediainfo):
                    metadata.saveLinks(mediainfo)
                # print(filename)
                if termCols < 80:
                    desc = f"M {truncate_middle(filename,12)}"
                else:
                    desc = f"Mídia {filename}"
                linkBar.set_description(desc)
                linkBar.update()
                mediaCount += 1
                await asyncio.sleep(0)
        
async def downloadLinks(drv, cookiejar, profile):
    profilePath = os.path.join(settings.downloaddir, profile)
    os.makedirs(name=profilePath, exist_ok=True)
    global metadata
    mediaCount = 0
    mediastoDownload = metadata.getMediaDownload()
    medias = asyncio.Queue()

    async with httpx.AsyncClient() as client:
        tasks = []
        for m in mediastoDownload:
            inner_link = m.inner_link
            if inner_link:
                timeout = httpx.Timeout(10.0, read=60.0)
                task = asyncio.create_task(check_url(inner_link, hdr, cookiejar, timeout))
                tasks.append(task)
        
        print("Verificando cabeçalhos de mídia...")
        global responses
        responses = await tqdm.gather(*tasks,colour='blue',dynamic_ncols=True,bar_format=barFormat)
        tasks.clear()
        
        async def check(media, response):
            # filepath = os.path.join(media.directory, media.filename)
            response_status = False
            if response.status_code == 200:
                response_status = True
                if response.headers.get('content-length'):
                    media.size = int(response.headers.get('content-length'))
            # if os.path.exists(filepath):
            #     if os.path.getsize(filepath) == response.headers.get('content-length'):
            #         media.downloaded = True
            #     else:
            #         return media
            # else:
                if response_status:
                    return media
                
        mediastoDownload = metadata.getMediaDownload()
        async def checkLink(m,r):
            while not m.empty():
                media = await m.get()
                temp_response = [
                    response
                    for response in r
                    if isinstance(response, Response) and response and str(response.url) == media.link
                    ]
                if temp_response:
                    temp_response = temp_response[0]
                    ret = await check(media, temp_response)
                    mdBar.update()
                    medias.task_done()
                    return ret

        print('Lendo metadados...')
        # for media in tqdm(mediastoDownload,colour='blue',dynamic_ncols=True,bar_format=barFormat):
        #     temp_response = [
        #         response
        #         for response in responses
        #         if response and str(response.url) == media.link
        #         ]
        #     if temp_response:
        #         temp_response = temp_response[0]
        #         task = check(media, temp_response)
        #         tasks.append(task)
        # results = await tqdm.gather(*tasks,colour='blue',dynamic_ncols=True,bar_format=barFormat)
        metadata.session.commit()
        # tasks.clear()
    
        global mdBar
        total = metadata.getMediaDownloadCount()
        with tqdm(total=total,colour='blue',dynamic_ncols=True,bar_format=barFormat) as mdBar:
            results = await asyncio.gather(*([retrieveLinks(mediastoDownload,medias)] + [checkLink(medias,responses) for _ in range(total)]))
            medialist = [x for x in results if x]
            mdBar.close()

    mediastoDownload = metadata.getMediaDownload()
    global downloadBar
    with tqdm(dynamic_ncols=True,colour='green',bar_format=barFormat,unit='B',unit_scale=True,miniters=1) as downloadBar:
        total = 0
        for x in medialist:
            total += int(x.size)
        downloadBar.total = int(total*1.00001)
        global savedTotal
        if (savedTotal>0 and savedTotal % 200 == 0) or len(medialist) > 1000:
            await drv.reload()
            cookiejar = await refreshCookies(drv)
        print(" Baixando mídia...")
        # m.filename == 'b3a4b631-ab8e-419a-b000-5e0d0c4e43a7-002.jpg'
        # perdendo o link de um arquivo, ficando com a url vazia mas no resto está vindo correto a url
        await asyncio.gather(*([retrieveLinks(mediastoDownload,medias)] + [requestLink(medias, cookiejar) for _ in range(4)]))

async def retrieveLinks(mediastoDownload, medias: asyncio.Queue()):
    for m in mediastoDownload:
        await medias.put(m)

async def requestLink(medias, cookiejar):
    while not medias.empty():
        media = await medias.get()
        global downloadBar
        global termCols
        if termCols < 80:
            desc = truncate_middle(media.filename,12)
        else:
            desc = media.filename
        downloadBar.set_description(f"{desc}")
        downloadBar.update()
        mediainfo = {}
        client = httpx.AsyncClient()
        timeout = httpx.Timeout(10.0, read=60.0)
        global responses
        temp_response = [
            response
            for response in responses
            if isinstance(response, Response) and response and str(response.url) == media.link
        ]
        url = media.link
        if temp_response:
            temp_response = temp_response[0]
            if temp_response.status_code == 413:
                url = media.inner_link

        async with client.stream('GET',url=url,headers=hdr,cookies=cookiejar,timeout=timeout) as req:
            if req.status_code == 200:
                saved = 0
                global filesTotal
                if int(req.headers['Content-Length']) < 10000000: #10MB
                    await req.aread()
                    with open(os.path.join(media.directory,media.filename), 'wb') as download:
                        saved = download.write(req.content)
                    filesTotal += saved
                    downloadBar.update(saved)
                else:
                    with open(os.path.join(media.directory,media.filename), 'wb') as download:
                        async for chunk in req.aiter_bytes():
                            f = download.write(chunk)
                            saved += f
                            downloadBar.update(f)
                        filesTotal += f

                if saved > 0:
                    date = parse(req.headers['last-modified'])
                    mtime = time.mktime(date.timetuple())
                    os.utime(os.path.join(media.directory,media.filename),(mtime,mtime))
                    mediainfo['media_id'] = media.media_id
                    mediainfo['size'] = os.path.getsize(os.path.join(media.directory,media.filename))
                    mediainfo['created_at'] = date
                    metadata.markDownloaded(mediainfo)
                    global savedTotal
                    savedTotal += 1
                    # print(f"{media.filename} {saved} bytes salvo.")
            else:
                tqdm.write(f"Download de {media.filename} falhou, HTTP erro {req.status_code}")
            # print(filesTotal)
            medias.task_done()

async def refreshCookies(driver: pw.Page):
    # reconstrói cookie do navegador para Requests
    jar = httpx.Cookies()
    # await driver.reload()
    for c in await driver.context.cookies():
        # print(type(c))
        # print(c['name'])
        jar.set(c['name'], c['value'], path=c['path'], domain=c['domain'])#, secure=c['secure']) #, httpOnly=c['httpOnly'], sameSite=c['sameSite'])
    return jar


async def downloadHybrid(page: pw.Page, profile):
    """
    Download híbrido: Playwright para imagens, FFmpeg para vídeos HLS.
    """
    profilePath = os.path.join(settings.downloaddir, profile)
    os.makedirs(name=profilePath, exist_ok=True)
    
    global metadata
    openDatabase()
    
    # Converte para lista para permitir múltiplas iterações
    mediastoDownload = list(metadata.getMediaDownload())
    total = len(mediastoDownload)
    
    if total == 0:
        print("Nenhuma mídia para baixar.")
        return
    
    print(f"\nBaixando {total} mídias usando método híbrido...")
    
    # DEBUG: Ver tipos de mídia no banco
    all_types = set(m.media_type for m in mediastoDownload)
    print(f"DEBUG - Tipos encontrados no banco: {all_types}")
    
    # Extrair tokens de vídeo capturados
    global captured_timeline_data
    video_tokens = {}
    
    import urllib.parse
    import json as json_module
    
    for resp in captured_timeline_data:
        if 'mediavideotoken' in resp.get('url', ''):
            try:
                content = resp.get('data', {}).get('content', '')
                if content:
                    # Decodifica o token URL-encoded
                    decoded = urllib.parse.unquote(content)
                    token_data = json_module.loads(decoded)
                    file_id = token_data.get('message', {}).get('file_id', '')
                    if file_id:
                        # Mapeia file_id -> token completo
                        video_tokens[file_id] = content
            except Exception as e:
                pass
    
    print(f"DEBUG - {len(video_tokens)} tokens de vídeo extraídos")
    
    # Separa por tipo (flexível para variações)
    images = [m for m in mediastoDownload if 'image' in str(m.media_type).lower() or '.jpg' in str(m.link).lower() or '.png' in str(m.link).lower()]
    videos = [m for m in mediastoDownload if 'video' in str(m.media_type).lower() or '.m3u8' in str(m.link).lower() or '.mp4' in str(m.link).lower()]
    
    print(f"  - {len(images)} imagens (Playwright)")
    print(f"  - {len(videos)} vídeos (FFmpeg)")
    
    # Obtém cookies para FFmpeg/yt-dlp
    cookies = await page.context.cookies()
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    
    # Cria arquivo de cookies no formato Netscape para yt-dlp
    cookies_file = os.path.join(profilePath, 'cookies.txt')
    with open(cookies_file, 'w') as f:
        f.write("# Netscape HTTP Cookie File\n")
        for c in cookies:
            domain = c.get('domain', '.privacy.com.br')
            flag = 'TRUE' if domain.startswith('.') else 'FALSE'
            path = c.get('path', '/')
            secure = 'TRUE' if c.get('secure', False) else 'FALSE'
            expires = str(int(c.get('expires', 0)))
            name = c.get('name', '')
            value = c.get('value', '')
            f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
    
    # Download de imagens com Playwright
    if images:
        print("\n📷 Baixando imagens...")
        for i, media in enumerate(tqdm(images, colour='cyan', bar_format=barFormat)):
            success = await downloadImageWithPlaywright(page, media)
            if success:
                markMediaDownloaded(media)
    
    # Download de vídeos
    if videos:
        print("\n🎬 Baixando vídeos HLS...")
        for i, media in enumerate(tqdm(videos, colour='magenta', bar_format=barFormat)):
            # Procura token correspondente ao vídeo
            video_url = media.link
            token = None
            for file_id, tok in video_tokens.items():
                if file_id in video_url:
                    token = tok
                    break
            
            success = await downloadVideoWithPlaywright(page, media, token)
            if success:
                markMediaDownloaded(media)
    
    print("\n✅ Download concluído!")


async def downloadImageWithPlaywright(page: pw.Page, media):
    """
    Baixa imagem usando o Playwright (mantém autenticação via cookies).
    Usa headers customizados (x-content-uri) para autenticação.
    """
    try:
        filepath = os.path.join(media.directory, media.filename)
        
        # Auto-skip se já existe
        if os.path.exists(filepath):
            return True
        
        # Headers para autenticação - CRUCIAL para Privacy.com.br
        headers = {
            'Origin': 'https://privacy.com.br',
            'Referer': 'https://privacy.com.br/',
            'x-content-uri': media.link.split('/')[-1],
        }
        
        # Tenta request direto pelo contexto (preserva cookies)
        try:
            response = await page.context.request.get(media.link, headers=headers)
            if response.status == 200:
                content = await response.body()
                with open(filepath, 'wb') as f:
                    f.write(content)
                return True
            else:
                tqdm.write(f"❌ Imagem {media.filename}: HTTP {response.status}")
        except Exception as e:
            tqdm.write(f"❌ Erro requisição imagem {media.filename}: {e}")

        # Fallback: Tenta sem x-content-uri se falhar (algumas imagens podem ser públicas/CDN diferente)
        try:
             # Remove header específico
            headers_simple = {
                'Origin': 'https://privacy.com.br',
                'Referer': 'https://privacy.com.br/',
            }
            response = await page.context.request.get(media.link, headers=headers_simple)
            if response.status == 200:
                content = await response.body()
                with open(filepath, 'wb') as f:
                    f.write(content)
                return True
        except Exception:
            pass

        return False
        
    except Exception as e:
        tqdm.write(f"❌ Erro ao baixar {media.filename}: {e}")
        return False


async def downloadVideoWithPlaywright(page: pw.Page, media, token=None):
    """
    Baixa vídeo HLS usando estratégia de "Local M3U8".
    BAIXA: Master m3u8 -> Variant m3u8 -> Keys (se houver) -> Segmentos.
    REESCREVE: Variant m3u8 para apontar para arquivos locais.
    FFMPEG: Processa o playlist local (que já aponta para keys e segments locais).
    """
    import subprocess
    import tempfile
    import shutil
    import uuid
    
    try:
        # Define caminhos
        filepath = os.path.join(media.directory, media.filename)
        abs_filepath = os.path.abspath(filepath)
        
        # Auto-skip se já existe
        if os.path.exists(filepath):
            return True
        video_url = media.link
        
        # Helper para criar headers com x-content-uri dinâmico
        def make_headers(url):
            h = {
                'Origin': 'https://privacy.com.br',
                'Referer': 'https://privacy.com.br/',
                'x-content-uri': url.split('/')[-1],
            }
            if token:
                h['content'] = token
            return h
        
        # 1. Baixa Master M3U8 (ou vídeo direto)
        response = await page.context.request.get(video_url, headers=make_headers(video_url))
        if response.status != 200:
            tqdm.write(f"❌ {media.filename}: HTTP {response.status}")
            return False
        
        # Verifica se é MP4 direto (não HLS)
        content_type = response.headers.get('content-type', '').lower()
        if 'video/mp4' in content_type:
            # É um vídeo direto, apenas salva
            with open(filepath, 'wb') as f:
                f.write(await response.body())
            return True

        try:
            master_content = (await response.body()).decode('utf-8')
        except UnicodeDecodeError:
            # Verifica se é MP4 pelos bytes (fallback se content-type falhar)
            raw_body = await response.body()
            if raw_body[:4] == b'\x00\x00\x00\x1c' and b'ftyp' in raw_body[:20]:
                with open(filepath, 'wb') as f:
                    f.write(raw_body)
                return True
            
            # Realmente um erro
            tqdm.write(f"❌ {media.filename}: decode error (master). Headers: {response.headers}")
            tqdm.write(f"Bytes iniciais: {raw_body[:20]}")
            return False
            
        # 2. Encontra Variante (High Quality)
        variant_url = None
        base_url = video_url.rsplit('/', 1)[0] + '/'
        
        for line in master_content.split('\n'):
            if line.strip() and not line.startswith('#'):
                variant_url = base_url + line.strip()
                break
        
        if not variant_url:
            tqdm.write(f"❌ {media.filename}: Sem variante")
            return False
            
        # 3. Baixa Variante M3U8
        v_resp = await page.context.request.get(variant_url, headers=make_headers(variant_url))
        if v_resp.status != 200:
            tqdm.write(f"❌ {media.filename}: Variante HTTP {v_resp.status}")
            return False
            
        try:
            variant_content = (await v_resp.body()).decode('utf-8')
        except UnicodeDecodeError:
             # Fallback ou Debug
            raw_body = await v_resp.body()
            tqdm.write(f"❌ {media.filename}: decode error (variant). Headers: {v_resp.headers}")
            tqdm.write(f"Bytes iniciais: {raw_body[:20]}")
            return False
        
        # Usa diretório temporário para tudo
        with tempfile.TemporaryDirectory() as tmpdir:
            # 4. Processa M3U8: Baixa Chaves e Segmentos, Reescreve Playlist
            local_lines = []
            segment_idx = 0
            base_variant = variant_url.rsplit('/', 1)[0] + '/'
            
            lines = variant_content.split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('#EXT-X-KEY'):
                    # Ex: #EXT-X-KEY:METHOD=AES-128,URI="key.php?id=...",IV=...
                    # Extrai URI
                    try:
                        start_uri = line.find('URI="') + 5
                        end_uri = line.find('"', start_uri)
                        key_uri = line[start_uri:end_uri]
                        
                        # Constrói URL completa da chave
                        if not key_uri.startswith('http'):
                            full_key_url = base_variant + key_uri
                        else:
                            full_key_url = key_uri
                            
                        # Baixa a chave
                        k_resp = await page.context.request.get(full_key_url, headers=make_headers(full_key_url))
                        if k_resp.status == 200:
                            key_filename = f"key_{segment_idx}.key"
                            key_path = os.path.join(tmpdir, key_filename)
                            with open(key_path, 'wb') as kf:
                                kf.write(await k_resp.body())
                            
                            # Reescreve linha para usar chave local (caminho absoluto forward slashed)
                            # FFmpeg precisa de caminho local
                            local_key_path = key_filename # Relativo ao playlist file
                            
                            # Reconstrói a linha substituindo a URI
                            new_line = line[:start_uri] + local_key_path + line[end_uri:]
                            local_lines.append(new_line)
                        else:
                            tqdm.write(f"⚠️ Falha chave {full_key_url}: {k_resp.status}")
                            local_lines.append(line) # Mantém original (vai falhar provavel)
                            
                    except Exception as e:
                        tqdm.write(f"⚠️ Erro parse chave: {e}")
                        local_lines.append(line)
                        
                elif line.startswith('#'):
                    local_lines.append(line)
                    
                else:
                    # É um segmento .ts
                    seg_url = line
                    if not seg_url.startswith('http'):
                        seg_url = base_variant + line
                    
                    # Baixa segmento
                    s_resp = await page.context.request.get(seg_url, headers=make_headers(seg_url))
                    if s_resp.status == 200:
                        seg_filename = f"seg_{segment_idx:04d}.ts"
                        seg_path = os.path.join(tmpdir, seg_filename)
                        with open(seg_path, 'wb') as sf:
                            sf.write(await s_resp.body())
                        
                        # Adiciona nome do arquivo local na playlist
                        local_lines.append(seg_filename)
                        segment_idx += 1
                    else:
                        tqdm.write(f"⚠️ Falha segmento {segment_idx}")
            
            # 5. Salva Playlist Reescrita Localmente
            local_m3u8_path = os.path.join(tmpdir, 'local.m3u8')
            with open(local_m3u8_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(local_lines))
            
            # 6. Chama FFmpeg para processar a playlist local
            # -allowed_extensions ALL permite usar keys locais .key kkkk
            # -protocol_whitelist file,http,https,tcp,tls,crypto
            
            # Paths seguros com /
            local_m3u8_safe = local_m3u8_path.replace('\\', '/')
            output_safe = abs_filepath.replace('\\', '/')
            
            cmd = [
                'ffmpeg', '-y', 
                '-allowed_extensions', 'ALL', 
                '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                '-i', local_m3u8_safe, 
                '-c', 'copy', '-bsf:a', 'aac_adtstoasc', 
                output_safe
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600) # Timeout maior
            
            if result.returncode == 0 and os.path.exists(abs_filepath):
                return True
            else:
                err = result.stderr[-300:] if result.stderr else "sem erro"
                tqdm.write(f"❌ {media.filename}: FFmpeg erro. {err[:200]}")
                return False
        
    except Exception as e:
        tqdm.write(f"❌ {media.filename}: {str(e)[:100]}")
        return False


async def downloadVideoWithFFmpeg(media, cookie_str, cookies_file=None, token=None):
    """
    Baixa vídeo HLS usando yt-dlp (melhor suporte a autenticação).
    Falls back to FFmpeg se yt-dlp falhar.
    Token é enviado via header 'content', não via URL.
    """
    import subprocess
    
    try:
        filepath = os.path.join(media.directory, media.filename)
        video_url = media.link
        
        # Extrai o nome do arquivo da URL para x-content-uri
        x_content_uri = video_url.split('/')[-1]  # Ex: 9b4f8b2c-...--Kauanny.m3u8
        
        # Método 1: yt-dlp com headers de autenticação
        cmd = [
            'yt-dlp',
            '--add-header', 'Origin: https://privacy.com.br',
            '--add-header', 'Referer: https://privacy.com.br/',
            '--add-header', f'x-content-uri: {x_content_uri}',
        ]
        
        # Adiciona token como header 'content' se disponível
        if token:
            cmd.extend(['--add-header', f'content: {token}'])
        
        cmd.extend([
            '--no-check-certificates',
            '-o', filepath,
            '--no-warnings',
            '-q',
            video_url
        ])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and os.path.exists(filepath):
            return True
        
        # Método 2: FFmpeg como fallback
        # Constrói headers para FFmpeg
        headers = f'Origin: https://privacy.com.br\r\nReferer: https://privacy.com.br/\r\nx-content-uri: {x_content_uri}\r\n'
        if token:
            headers += f'content: {token}\r\n'
        
        cmd = [
            'ffmpeg',
            '-y',
            '-headers', headers,
            '-i', video_url,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',
            filepath
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and os.path.exists(filepath):
            return True
        else:
            error_msg = result.stderr[-200:] if result.stderr else "Erro desconhecido"
            tqdm.write(f"❌ Vídeo {media.filename}: {error_msg[:100]}")
            return False
            
    except subprocess.TimeoutExpired:
        tqdm.write(f"❌ Vídeo {media.filename}: Timeout")
        return False
    except Exception as e:
        tqdm.write(f"❌ Erro ao baixar {media.filename}: {e}")
        return False


def markMediaDownloaded(media):
    """Marca mídia como baixada no banco de dados."""
    global metadata
    try:
        mediainfo = {
            'media_id': media.media_id,
            'size': os.path.getsize(os.path.join(media.directory, media.filename)),
            'created_at': datetime.datetime.now()
        }
        metadata.markDownloaded(mediainfo)
    except Exception:
        pass


#DISABLE IMAGES ON FIREFOX
# def disable_images(driver):
#     driver.get("about:config")
#     warningButton = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.ID,"warningButton"))
#     warningButton.click()
#     searchArea = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.ID,"about-config-search"))
#     searchArea.send_keys("permissions.default.image")
#     editButton = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.XPATH,"/html/body/table/tr[1]/td[2]/button"))
#     editButton.click()
#     editArea = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.XPATH,"/html/body/table/tr[1]/td[1]/form/input"))
#     editArea.send_keys("2")
#     saveButton = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.XPATH,"/html/body/table/tr[1]/td[2]/button"))
#     saveButton.click()

def openDatabase():
    profilePath = os.path.join(settings.downloaddir, profile)
    os.makedirs(name=profilePath, exist_ok=True)
    global metadata
    metadata = meta.metadata(profilePath)
    metadata.openDatabase()

def truncate_middle(s, n):
    if len(s) <= n:
        # string is already short-enough
        return s
    # half of the size, minus the 3 .'s
    n_2 = int(n / 2 - 3)
    # whatever's left
    n_1 = int(n - n_2 - 3)
    return '{0}...{1}'.format(s[:n_1], s[-n_2:])


@click.command()
@click.option(
    '--backlog',
    '-b',
    is_flag=True,
    default=False,
    help='Baixa apenas o "backlog" de mídias novas no DB, sem varrer a página'
    )
async def main(backlog):
    """Baixa toda a mídia seguida, aceita todos os perfis ou cada um individual."""
    global termCols
    termCols = get_terminal_cols()
    
    # Logs de ambiente para debug
    if is_termux:
        print("🤖 Detectado: Termux/Android")
    elif is_android:
        print("🤖 Detectado: Android")
    elif is_windows:
        print("💻 Detectado: Windows")
    else:
        print(f"💻 Detectado: {platform.system()}")
    
    async with pw.async_playwright() as p:
        global profile
        
        # Configurações específicas para Termux/Android
        browser_args = []
        if is_termux or is_android:
            # Flags necessárias para rodar Chromium no Termux
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process',
                '--no-zygote',
            ]
            print("⚙️ Usando configurações otimizadas para Termux...")
        
        browser = await p.chromium.launch(
            headless=True,
            args=browser_args if browser_args else None
        )
        print("Abrindo página de login...")
        page = await browser.new_page()
        await page.goto('about:blank')
        sleep(2)
        await page.goto(url)
        # await page.screenshot(path="ss.png")
        user = page.get_by_label('Email/CPF')
        await expect(user).to_be_editable(timeout=15000)
        await user.type(settings.user)
        sleep(1)
        pwd = page.get_by_label('Senha')
        await expect(pwd).to_be_editable(timeout=15000)
        await pwd.type(settings.pwd)
        sleep(1)
        btn = page.get_by_role('button', name=re.compile('entrar',re.IGNORECASE))
        await btn.click()
        # procura mudança de URL após login
        print("Aguardando autenticação...")
        await page.wait_for_url(lambda url: '/auth' not in url, timeout=90000)
        print("Login bem-sucedido!")
        
        #entrando na pagina do perfil para verificar os perfis seguidos
        await page.goto(following_url)
        sleep(5)

        profile_links = await page.locator('a[href^="https://privacy.com.br/profile/"]').evaluate_all('(links) => links.map(link => link.href)')
        
        # Extrai o nome dos perfis da pagina de seguindo do usuario
        profile_names_set = set(link.split('/')[-1] for link in profile_links)
        profile_names = list(profile_names_set)
        
        display_profiles(profile_names)

        # Pede para o utilizador escolher um perfil
        selection = input("Entre com o numero do perfil correspondente que queira baixar. (0 para todos os perfis): ")        
        
        if selection == "0":
            for profile in profile_names:
                await fetch_profiles(page, profile, backlog)
        elif selection.isdigit() and 0 < int(selection) <= len(profile_names):
            selected_profile = profile_names[int(selection) - 1]
            await fetch_profiles(page, selected_profile, backlog)
        
        await browser.close()
        print('Encerrado.')


if __name__ == "__main__":
    asyncio.run(main())
