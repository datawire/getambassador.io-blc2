selectors = {
    '*': {'itemtype'},
    'a': {'href', 'ping'},
    'applet': {'archive', 'code', 'codebase', 'object', 'src'},
    'area': {'href', 'ping'},
    'audio': {'src'},
    'blockquote': {'cite'},
    'body': {'background'},
    'button': {'formaction'},
    'del': {'cite'},
    'embed': {'src'},
    'form': {'action'},
    'frame': {'longdesc', 'src'},
    'head': {'profile'},
    'html': {'manifest'},
    'iframe': {'longdesc', 'src'},
    'img': {'longdesc', 'src', 'srcset'},
    'input': {'formaction', 'src'},
    'ins': {'cite'},
    'link': {'href'},
    'menuitem': {'icon'},
    'meta': {'content'},
    'object': {'codebase', 'data'},
    'q': {'cite'},
    'script': {'src'},
    'source': {'src', 'srcset'},
    'table': {'background'},
    'tbody': {'background'},
    'td': {'background'},
    'tfoot': {'background'},
    'th': {'background'},
    'thead': {'background'},
    'tr': {'background'},
    'track': {'src'},
    'video': {'poster', 'src'},
}

def get_links(baseurl: str, soup: BeautifulSoup):
    basetags = soup.select('base[href]')
    if basetags:
        baseurl = urldefrag(basetags[0]['href']).url
    for tagname, attrs in selectors:
        for attr in attrs:
            for element in soup.select(f"{tagname}[{attr}]"):
                tagurl = urljoin(baseurl, element[attr])
