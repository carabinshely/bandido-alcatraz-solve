/* Browser checks use only Node built-ins and an existing local Chrome. */
const fs = require('fs'), path = require('path'), http = require('http');
const { spawn } = require('child_process');
const base = __dirname, dist = path.join(base, 'dist'), qa = path.join(base, '.qa');
fs.mkdirSync(qa, { recursive: true });
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function main() {
  const server = http.createServer((request, response) => {
    const url = new URL(request.url, 'http://localhost');
    const relative = decodeURIComponent(url.pathname.replace(/^\/project\//, ''));
    const file = path.resolve(dist, relative || 'index.html');
    if (!file.startsWith(dist + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      response.writeHead(404); response.end('Not found'); return;
    }
    const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml' };
    response.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
    response.end(fs.readFileSync(file));
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}/project/`;
  const profile = path.join(qa, 'chrome-' + process.pid);
  fs.mkdirSync(profile);
  const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
  const browser = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', '--user-data-dir=' + profile], { stdio: 'ignore', windowsHide: true });
  let ws, send;
  try {
    let port;
    for (let i = 0; i < 100; i++) {
      const file = path.join(profile, 'DevToolsActivePort');
      if (fs.existsSync(file)) { port = +fs.readFileSync(file, 'utf8').split('\n')[0]; break; }
      await wait(100);
    }
    if (!port) throw Error('Chrome did not start');
    const tab = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json();
    ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let id = 0;
    const pending = new Map(), exceptions = [], networkFailures = [];
    ws.onmessage = event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const entry = pending.get(message.id);
        if (entry) {
          clearTimeout(entry.timer); pending.delete(message.id);
          message.error ? entry.reject(Error(JSON.stringify(message.error))) : entry.resolve(message.result);
        }
      } else if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params);
      else if (message.method === 'Network.responseReceived' && message.params.response.status >= 400) networkFailures.push(message.params.response.url);
    };
    send = (method, params = {}) => new Promise((resolve, reject) => {
      const next = ++id, timer = setTimeout(() => reject(Error('Timeout: ' + method)), 15000);
      pending.set(next, { resolve, reject, timer }); ws.send(JSON.stringify({ id: next, method, params }));
    });
    const evaluate = async expression => {
      const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
      if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    };
    const navigate = async suffix => {
      await send('Page.navigate', { url: origin + suffix });
      for (let i = 0; i < 100; i++) {
        if (await evaluate(`document.readyState==='complete' && !!document.getElementById('theme-toggle')`)) break;
        await wait(50);
      }
      await evaluate('document.fonts.ready');
    };
    const assert = (value, message) => { if (!value) throw Error(message); };
    await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
    await navigate('index.html');
    const results = [];
    for (const width of [320, 390, 1024, 1440]) {
      await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
      for (const theme of ['light', 'dark']) {
        await evaluate(`document.documentElement.dataset.theme='${theme}'`);
        for (const view of ['ideas', 'policies', 'journey']) {
          await evaluate(`document.getElementById('tab-${view}').click()`);
          const metrics = await evaluate(`({overflow:document.documentElement.scrollWidth>innerWidth,active:document.querySelector('[role=tab][aria-selected=true]').dataset.view,count:document.querySelectorAll('#panel-${view} a').length,smallButtons:[...document.querySelectorAll('button')].filter(b=>b.checkVisibility()&&b.getBoundingClientRect().height<44).length})`);
          assert(!metrics.overflow && metrics.active === view && !metrics.smallButtons, JSON.stringify({ width, theme, view, metrics }));
          results.push({ width, theme, view, ...metrics });
          if (theme === 'light' && (width === 390 || width === 1024)) {
            const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
            fs.writeFileSync(path.join(qa, `home-${view}-${width}.png`), Buffer.from(shot.data, 'base64'));
          }
        }
      }
    }
    await navigate('index.html?view=journey#catalog');
    await evaluate(`document.querySelector('#panel-journey a[href*="v4.html"]').click()`);
    for (let i=0; i<100; i++) { if (await evaluate(`location.pathname.endsWith('/strategies/v4.html') && document.readyState==='complete'`)) break; await wait(50); }
    assert(await evaluate(`new URL(document.querySelector('[data-return]').href).searchParams.get('view')==='journey'`), 'Return context lost');
    await send('Page.reload'); await wait(150);
    assert(await evaluate(`new URL(document.querySelector('[data-return]').href).searchParams.get('view')==='journey'`), 'Reload context lost');
    const files = fs.readdirSync(path.join(dist, 'strategies')).filter(f => f.endsWith('.html') && !f.startsWith('research-'));
    const researchFiles = fs.readdirSync(path.join(dist, 'strategies')).filter(f => f.startsWith('research-'));
    for (const file of files) {
      await navigate('strategies/' + file);
      assert(await evaluate(`document.querySelectorAll('#hand .hand-piece').length===6`), 'Hand missing: ' + file);
      for (const width of [320, 1024]) {
        await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
        for (const theme of ['light', 'dark']) {
          await evaluate(`document.documentElement.dataset.theme='${theme}';document.querySelector('[data-step=chosen]').click();document.getElementById('agent').open=true`);
          const metrics = await evaluate(`({overflow:document.documentElement.scrollWidth>innerWidth,selected:document.querySelector('[data-step=chosen]').getAttribute('aria-pressed'),cells:document.querySelectorAll('[data-board=lesson] [data-cell]').length,highlight:document.querySelectorAll('.hand-piece[data-active=true]').length})`);
          assert(!metrics.overflow && metrics.selected === 'true' && metrics.cells === 14 && metrics.highlight === 1, file + JSON.stringify({ width, theme, metrics }));
          results.push({ file, width, theme, ...metrics });
          if ((file === 'v4.html' || file === 'v6.html') && theme === 'light') {
            await evaluate(`document.getElementById('agent').open=false;new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
            const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
            fs.writeFileSync(path.join(qa, `${file.replace('.html', '')}-${width}.png`), Buffer.from(shot.data, 'base64'));
          }
        }
      }
    }
    for (const file of ['results.html', 'rules.html', 'method.html', ...fs.readdirSync(path.join(dist, 'families')).map(f => 'families/' + f)]) {
      await navigate(file); await send('Emulation.setDeviceMetricsOverride', { width: 320, height: 900, deviceScaleFactor: 1, mobile: true });
      assert(await evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Reference/family overflow: ' + file);
    }
    for (const locale of ['', 'en/']) {
      for (const file of researchFiles) {
        await navigate(locale + 'strategies/' + file);
        for (const width of [320, 1024]) {
          await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
          for (const theme of ['light', 'dark']) {
            await evaluate(`document.documentElement.dataset.theme='${theme}';document.getElementById('agent').open=true`);
            for (const step of ['before', 'catalog', 'chosen']) {
              const state = await evaluate(`(()=>{document.querySelector('[data-step=${step}]').click();const d=JSON.parse(document.getElementById('board-data').textContent);const o='${step}'==='before'?d.original:d['${step}'];return {overflow:document.documentElement.scrollWidth>innerWidth,cells:document.querySelectorAll('[data-board=lesson] [data-cell]').length,expected:o.board.cells.length,highlight:document.querySelectorAll('.hand-piece[data-active=true]').length,scroll:document.querySelector('[data-board=lesson]').scrollLeft}})()`);
              assert(!state.overflow && state.cells === state.expected && state.highlight === (step === 'before' ? 0 : 1), 'Research example invalid: '+file+locale+width+step+JSON.stringify(state));
              if (file === 'research-129.html' && step !== 'before' && width === 320) assert(state.scroll>0, 'Large board did not reveal selected move');
              results.push({language:locale?'en':'ru',file,width,theme,step,...state});
            }
            if (theme === 'light') {
              await evaluate(`document.getElementById('agent').open=false;new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
              const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
              fs.writeFileSync(path.join(qa, `${locale ? 'en-' : ''}${file.replace('.html','')}-${width}.png`),Buffer.from(shot.data,'base64'));
            }
          }
        }
      }
      await navigate(locale + 'results.html#recent-129');
      await evaluate(`document.querySelectorAll('.recent-study details').forEach(d=>d.open=true)`);
      for (const width of [320, 1024]) {
        await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
        assert(await evaluate(`document.documentElement.scrollWidth<=innerWidth && document.querySelectorAll('.recent-study').length===4`), 'Recent results overflow/missing: ' + locale + width);
        const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
        fs.writeFileSync(path.join(qa, `${locale ? 'en-' : ''}results-${width}.png`), Buffer.from(shot.data, 'base64'));
      }
    }
    await navigate('example.html');
    const ab = [];
    for (const step of ['before', 'a', 'b']) {
      ab.push(await evaluate(`(()=>{document.querySelector('[data-step=${step}]').click();return {step:'${step}',cells:document.querySelectorAll('[data-board=lesson] [data-cell]').length,open:document.querySelectorAll('[data-board=lesson] [data-open-end]').length,water:document.querySelectorAll('[data-board=lesson] [data-water]').length}})()`));
    }
    assert(ab[0].cells === 12 && ab[1].open === 5 && ab[2].open === 3 && ab[2].water === 3, 'AB example invalid');
    const blocked = await send('Page.addScriptToEvaluateOnNewDocument', { source: `Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage disabled','SecurityError')}});` });
    await navigate('index.html?view=policies');
    await evaluate(`document.getElementById('tab-journey').click();document.getElementById('theme-toggle').click()`);
    assert(await evaluate(`document.getElementById('tab-journey').getAttribute('aria-selected')==='true'`), 'Disabled storage breaks tabs');
    await send('Page.removeScriptToEvaluateOnNewDocument', { identifier: blocked.identifier });
    await navigate('index.html');
    await evaluate(`localStorage.setItem('bandido-theme','system')`);
    await navigate('index.html');
    for (const theme of ['light', 'dark', 'system']) {
      await evaluate(`document.getElementById('theme-toggle').click()`);
      assert(await evaluate(`(document.documentElement.dataset.theme||'system')==='${theme}'`), 'Theme toggle failed: ' + theme);
    }
    await navigate('strategies/v4.html#agent');
    assert(await evaluate(`document.getElementById('agent').open`), 'Agent deep link not expanded');
    await navigate('index.html?view=ideas');
    await evaluate(`document.getElementById('tab-ideas').focus()`);
    await send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight' });
    await send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'ArrowRight', code: 'ArrowRight' });
    assert(await evaluate(`document.activeElement.id==='tab-policies' && document.getElementById('tab-policies').getAttribute('aria-selected')==='true'`), 'Tab keyboard navigation failed');
    await evaluate('history.back()'); await wait(100);
    assert(await evaluate(`document.getElementById('tab-ideas').getAttribute('aria-selected')==='true'`), 'History back failed');
    await evaluate('history.forward()'); await wait(100);
    assert(await evaluate(`document.getElementById('tab-policies').getAttribute('aria-selected')==='true'`), 'History forward failed');
    await evaluate(`localStorage.setItem('bandido-view','journey')`);
    await navigate('index.html');
    assert(await evaluate(`document.getElementById('tab-journey').getAttribute('aria-selected')==='true'`), 'Initial remembered tab failed');
    await evaluate(`document.getElementById('tab-policies').click()`);
    assert(await evaluate(`new URL(document.getElementById('language-switch').href).searchParams.get('view')==='policies'`), 'Language link is stale after the first tab click');
    await evaluate('history.back()'); await wait(100);
    await evaluate(`document.getElementById('tab-policies').click();history.back()`);
    await wait(150);
    assert(await evaluate(`document.getElementById('tab-journey').getAttribute('aria-selected')==='true'`), 'Back lost the initially remembered tab');
    const englishPages = ['index.html', 'results.html', 'rules.html', 'method.html', 'example.html', ...files.map(file => 'strategies/' + file), ...fs.readdirSync(path.join(dist, 'families')).map(file => 'families/' + file)];
    for (const file of englishPages) {
      await navigate('en/' + file);
      for (const width of [320, 1024]) {
        await send('Emulation.setDeviceMetricsOverride', { width, height: 900, deviceScaleFactor: 1, mobile: width < 600 });
        for (const theme of ['light', 'dark']) {
          await evaluate(`document.documentElement.dataset.theme='${theme}';document.querySelectorAll('details').forEach(d=>d.open=true);document.querySelector('[data-step=chosen]')?.click();document.querySelector('[data-step=b]')?.click()`);
          const state = await evaluate(`({lang:document.documentElement.lang,overflow:document.documentElement.scrollWidth>innerWidth,russian:/[А-Яа-яЁё]/.test(document.body.innerText.replaceAll('Русский',''))})`);
          assert(state.lang === 'en' && !state.overflow && !state.russian, 'English page failed: ' + file + JSON.stringify({ width, theme, state }));
          results.push({ language: 'en', file, width, theme, ...state });
          if ((file === 'index.html' || file === 'strategies/v4.html') && theme === 'light' && width === 1024) {
            await evaluate(`document.querySelectorAll('details').forEach(d=>d.open=false);new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))`);
            const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
            fs.writeFileSync(path.join(qa, 'en-' + file.replaceAll('/', '-').replace('.html', '') + '.png'), Buffer.from(shot.data, 'base64'));
          }
        }
      }
    }
    await navigate('strategies/v6.html?view=journey#example');
    await evaluate(`document.getElementById('language-switch').click()`);
    for (let i=0;i<100;i++){if(await evaluate(`document.documentElement.lang==='en'&&document.readyState==='complete'`))break;await wait(50);}
    assert(await evaluate(`location.pathname.endsWith('/en/strategies/v6.html')&&location.search==='?view=journey'&&location.hash==='#example'`), 'English switch lost context');
    await evaluate(`document.getElementById('language-switch').click()`);
    for (let i=0;i<100;i++){if(await evaluate(`document.documentElement.lang==='ru'&&document.readyState==='complete'`))break;await wait(50);}
    assert(await evaluate(`location.pathname.endsWith('/strategies/v6.html')&&!location.pathname.includes('/en/')&&location.search==='?view=journey'&&location.hash==='#example'`), 'Russian switch lost context');
    const summary = { states: results.length, policyPages: files.length, researchPages: researchFiles.length, ab, exceptions, networkFailures, passed: exceptions.length === 0 && networkFailures.length === 0 };
    fs.writeFileSync(path.join(qa, 'browser-checks.json'), JSON.stringify({ summary, results }, null, 2));
    console.log(JSON.stringify(summary)); assert(summary.passed, 'Browser exceptions or failed resources');
  } finally {
    if (ws) { try { await send('Browser.close'); } catch {} ws.close(); }
    if (browser.exitCode === null) { await Promise.race([new Promise(resolve => browser.once('exit', resolve)), wait(3000)]); if (browser.exitCode === null) browser.kill(); }
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); process.exitCode = 1; });
