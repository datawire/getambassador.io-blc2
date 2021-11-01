#!/usr/bin/env node

const fs = require('fs/promises');
const http = require('http');
const path = require('path');
const url = require('url');

const mime = require('mime');
const redirectParser = require('netlify-redirect-parser');
const {
  parseHeadersFile,
  headersForPath
} = require('netlify-cli/src/utils/headers');
const {fdir} = require('fdir');

let host = 'localhost';
let port = 9000;
let dir = path.resolve('public');
let cfg = path.resolve('netlify.toml');

// getambassador.io migration sources
const datawireDomains = {
  'http://www.datawire.io/': true,
  'https://www.datawire.io/': true,
  'http://datawire.io/': true,
  'https://datawire.io/': true
};
// getambassador.io migration link
const migrationRedirect = 'https://www.getambassador.io/?utm_source=https://www.datawire.io/';

const server = http.createServer();

async function exists(filepath) {
  try {
    await fs.stat(filepath);
    return true;
  } catch {
    return false;
  }
}

function matchesRedirect(forcefulOnly, requestURL, redirect) {
  if (forcefulOnly && !redirect.force) {
    return false;
  }
  // keep getambassador.io on localhost, due to migrations from datawire.io to getambassador.io
  if (requestURL.pathname === '/' && requestURL.path === '/' && requestURL.href === '/' &&
    datawireDomains[redirect.origin] && migrationRedirect === redirect.to) {
    return false;
  }
  if (redirect.path !== requestURL.pathname && redirect.path !== requestURL.pathname+'/') {
    return false;
  }
  const requestQuery = new URLSearchParams(requestURL.query);
  for (const key in redirect.query) {
    if (requestQuery.get(key) !== redirect.query[key]) {
      return false;
    }
  }
  return true;
}

function doRedirect(requestURL, response, redirect) {
  let location = redirect.to;
  if (!url.parse(location).search) {
    location += (requestURL.search || '');
  }
  response.writeHead(redirect.status, {
    'Location': location,
    'Content-Type': 'text/plain',
  });
  response.end(`Redirecting to ${location}`);
}

const filesOnMemory = {};
const errorLoadingFile = 'There was reading the file';

function loadSiteOnMemory(dir) {
  const api = new fdir().withFullPaths().crawl(dir);
  const files = api.sync();
  for (const file of files) {
    fs.readFile(file).then(content => {
      filesOnMemory[file] = content;
    }).catch(() => filesOnMemory[file] = errorLoadingFile);
  }
}

loadSiteOnMemory(dir);

const headersFiles = [path.resolve('_headers'), path.resolve(dir, '_headers')];
const headerRules = headersFiles.reduce((headerRules, headersFile) => Object.assign(headerRules, parseHeadersFile(headersFile)), {});

let redirects;

try {
  redirects = redirectParser.parseAllRedirects({
    redirectsFiles: [path.resolve(dir, '_redirects')],
    netlifyConfigPath: cfg,
  });
} catch (err) {
  process.abort();
}

server.on('request', async (request, response) => {
  console.log('srv', request.method, request.url);
  const requestURL = url.parse(url.resolve('/', request.url));
  if (requestURL.protocol || requestURL.slashes || requestURL.host) {
    response.writeHead(400);
    response.end('Bad request URL');
  }

  let redirect = (await redirects).find((redirect) => (matchesRedirect(true, requestURL, redirect)));
  if (redirect) {
    doRedirect(requestURL, response, redirect);
    return;
  }

  const filepath = path.join(dir, requestURL.pathname).replace(/\/$/, '/index.html');
  let content;
  try {
    if (filesOnMemory[filepath] && filesOnMemory[filepath] !== errorLoadingFile) {
      content = filesOnMemory[filepath];
    } else {
      content = await fs.readFile(filepath);
    }
  } catch (err) {
    if (err.code === 'EISDIR' && !requestURL.pathname.endsWith('/')) {
      // All sane webservers should do this.  `netlify dev` doesn't.
      const location = requestURL.pathname + '/' + (requestURL.search || '');
      response.writeHead(302, {
        'Location': location,
        'Content-Type': 'text/plain',
      });
      response.end(`Redirecting to ${location}`);
    } else if (requestURL.pathname.endsWith('.html') && await exists(filepath.replace(/\.html$/, ''))) {
      // This is a weird thing that Netlify does (even if you
      // turn off pretty URLs).
      const location = requestURL.pathname.replace(/\.html$/, '') + (requestURL.search || '');
      response.writeHead(302, {
        'Location': location,
        'Content-Type': 'text/plain',
      });
      response.end(`Redirecting to ${location}`);
    } else if ((redirect = (await redirects).find((redirect) => (matchesRedirect(false, requestURL, redirect))))) {
      doRedirect(requestURL, response, redirect);
    } else {
      response.writeHead(404, {
        'Content-Type': 'text/html',
      });
      response.end(await fs.readFile(path.resolve(dir, '404.html')));
    }
    return;
  }

  const pathHeaderRules = headersForPath(headerRules, requestURL.pathname);
  Object.entries(pathHeaderRules).forEach(([key, val]) => {
    response.setHeader(key, val);
  });

  response.writeHead(200, {
    'Content-Type': mime.getType(filepath),
  });
  response.end(content);
});

server.listen(port, host, () => {
  const addr = url.format({
    protocol: 'http',
    hostname: host,
    port: port,
    pathname: '/',
  });
  console.log(`----

  Serving
    directory ${dir}
    with config ${cfg}
    at address ${addr}

----`);
});
