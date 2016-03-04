import csv
from biases.utils.mysql import cursor_iterator
from itertools import groupby
import mwclient

LANGLINK_QUERY = """SELECT p.page_title, ll.ll_title, ll.ll_lang FROM
({from_lang}wiki.langlinks AS ll JOIN {from_lang}wiki.page AS p ON
(p.page_id = ll.ll_from)) WHERE ll.ll_lang IN ({to_langs}) AND
ll_title != '' ORDER BY ll.ll_from;"""

def read_langlinks_from_db(from_lang, to_langs, db_cursor):
    """Given a MySQL database cursor, and assuming that databases are named
    as they are in Wikipedia (ex. enwiki, eswiki, ruwiki...), generates
    interlanguage links as tuples of titles, where the first element is the
    title in the from_lang language and the remaining elements are the titles
    in the to_langs languages. If no langlink is present for a particular
    language, it will be represented as None."""
    
    to_langs_str = ','.join('\'{}\''.format(to_lang) for to_lang in to_langs)
    query = LANGLINK_QUERY.format(from_lang = from_lang,
                                  to_langs = to_langs_str)
    db_cursor.execute(query)
    
    # group resulting rows by the first column (the from_lang article title)
    for from_title, rows in groupby(cursor_iterator(db_cursor),
                                    key = lambda r: r[0]):
        
        try:
            rows = list(rows)
            from_title = from_title.decode('utf-8')
            to_titles = {to_lang.decode('utf-8'): to_title.decode('utf-8')
                         for _, to_title, to_lang in rows}
        except UnicodeDecodeError:
            print('UnicodeDecodeError: rows = {}'.format(rows))
        
        result = [from_title]
        for to_lang in to_langs:
            result.append(to_titles.get(to_lang, None))
            
        yield tuple(result)

def write_langlinks_file(langs, langlinks, filename):
    """Given a list of langs (as two-letter codes) [lang1, lang2...] and an
    iterable of langlinks as tuples (lang1_title, lang2_title...), writes them
    to a CSV file."""
    
    with open(filename, 'w') as outfile:
        writer = csv.writer(outfile)
        
        writer.writerow(langs)
        for langlink in langlinks:
            writer.writerow(langlink)

MWCLIENT_SITES = {}

def mwclient_site(lang):
    """Given a language code, get the mwclient Site object for that language
    edition of Wikipedia. Caches Site objects to avoid making them over and
    over."""
    
    if lang not in MWCLIENT_SITES:
        MWCLIENT_SITES[lang] = mwclient.Site('{}.wikipedia.org'.format(lang))
        
    return MWCLIENT_SITES[lang]

def get_article_versions(seed, langs):
    """Given a seed article and a set of languages, finds other versions of
    the article in the given languages by following interlanguage links.
    Articles are given and returned in the form (lang, article_title). Works by
    performing a graph search over the network of interlanguage links until
    no new article versions can been found."""
    
    explored = set()
    frontier = {seed}
    
    while frontier:
        article = frontier.pop()
        explored.add(article)
        lang, title = article
        page = mwclient_site(lang).pages[title]
        for langlink in page.langlinks():
            if langlink[0] in langs and langlink not in explored:
                frontier.add(langlink)
    
    return explored
