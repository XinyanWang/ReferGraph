import json
import re
import requests
import Queue
import threading
from time import sleep
import conf.py

HEADERS = \
    """Host: www.researchgate.net
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate, br
Referer: https://www.researchgate.net
Connection: keep-alive"""

APIHEADERS = \
    '''Host: www.researchgate.net
User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0
Accept: application/json
Accept-Language: zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3
Accept-Encoding: gzip, deflate, br
X-Requested-With: XMLHttpRequest
Referer: https://www.researchgate.net/publication/279807879_Energy_exchange_network_of_inter-residue_interactions_within_a_thermally_fluctuating_protein_molecule_A_computational_study
Connection: keep-alive'''

SESSION = None
QUEUE = Queue.Queue(maxsize=-1)
FINISHED = Queue.Queue(maxsize=1)
OBJECT = Queue.Queue(maxsize=-1)
END = False
FILENAME = 'graph.json'
MAXR = 2
MAXC = 2


def judge(r, c):
    if r > MAXR or c > MAXC:
        return False
    return True


class LinkError(BaseException):
    pass


def mkheaders(string):
    '''
    Make Headers For class::Session
    '''
    res = {}
    for key, val in [i.split(": ") for i in string.split("\n")]:
        res[key] = val
    return res


def initialize():
    '''
    Initialize global var SESSION
    '''
    global FILENAME
    FILENAME = raw_input("Filename : ")
    S = requests.Session()
    S.headers.update(mkheaders(HEADERS))
    res = S.get('https://www.researchgate.net/application.Login.html')
    request_token = re.findall(
        r'<input type="hidden" name="request_token" value="(.*)"/>', res.content)[0][:300]
    S.post('https://www.researchgate.net/application.Login.html', data={'invalidPasswordCount': '0',
                                                                        'login': conf.email,
                                                                        'password': conf.passwd,
                                                                        'request_token': request_token,
                                                                        'setLoginCookie': 'yes'})
    S.headers.update(mkheaders(APIHEADERS))
    if not S.cookies:
        raise LinkError("No Cookie")
    global SESSION
    SESSION = S
    return


def mkReferUrl(artid, refnum, offset=0):
    '''
    Make url for getting reference
    '''
    return "https://www.researchgate.net/publicliterature.PublicationCitationsList.html?" +\
        "publicationUid={artid}".format(artid=artid) +\
        "&usePlainButton=0" +\
        "&nextDetailPageExperimentViewId=VeQYww0qs2IddJIPTj4sZCzf5l0yZQiI3ktO" +\
        "&swapJournalAndAuthorPositions=1" +\
        "&showAbstract=1" +\
        "&showOpenReviewButton=0" +\
        "&showDownloadButton=0" +\
        "&showType=0" +\
        "&showPublicationPreview=0" +\
        "&showEnrichedPublicationItem=1" +\
        "&publicationUid={artid}".format(artid=artid) +\
        "&sort=normal" +\
        "&limit={refnum}".format(refnum=refnum) +\
        "&offset={offset}".format(offset=offset)


def getRefDict(artid, num, offset=0):
    '''
    Get reference data.
    Return a list of dicts.
    '''
    url = mkReferUrl(artid, num, offset=offset)
    res = SESSION.get(url)
    ans = json.loads(res.content)
    if ans["success"]:
        if 'citationItems' not in ans['result']['data']:
            print artid
            return []
        return [getNodeData(i) for i in ans['result']['data']['citationItems']]
    raise LinkError("What The Fuck! I Can't Get Data!")


def mkCiteUrl(artid, citenum, offset=0):
    return 'https://www.researchgate.net/publicliterature.PublicationIncomingCitationsList.html?' +\
        'publicationUid={artid}&'.format(artid=artid) +\
        'nextDetailPageExperimentViewId=3SNBWYmdzTTW6mmuBpjizVsOoE8peYw3fhmU&' +\
        'usePlainButton=0&' +\
        'useEnrichedContext=1&' +\
        'swapJournalAndAuthorPositions=1&' +\
        'showAbstract=1&' +\
        'showOpenReviewButton=0&' +\
        'showDownloadButton=0&' +\
        'showType=0&' +\
        'showPublicationPreview=0&' +\
        'showEnrichedPublicationItem=1&' +\
        'publicationUid={artid}&'.format(artid=artid) +\
        'limit={citenum}&'.format(citenum=citenum) +\
        'offset={offset}'.format(offset=offset)


def getCiteDict(artid, num, offset=0):
    '''
    Get citation data.
    Return a list of dicts.
    '''
    url = mkCiteUrl(artid, num, offset=offset)
    res = SESSION.get(url)
    ans = json.loads(res.content)
    if ans["success"]:
        if 'citationItems' not in ans['result']['data']:
            print artid
            return []
        return [getNodeData(i) for i in ans['result']['data']['citationItems']]
    raise LinkError("What The Fuck! I Can't Get Data!")


def getNodeData(data):
    """
    Return a dict of artid, title, url and abstract.
    """
    ans = {}
    if 'url' in data['data']:
        ans['url'] = 'http://www.researchgate.net/' + data['data']['url']
        ans['artid'] = re.findall(r'publication/([0-9]*)_', ans['url'])[0]
        ans['citation'] = data['data']['citationCount']
    else:
        ans['url'] = None
        ans['artid'] = None
        ans['citation'] = None
    if 'abstract' in data['data']:
        ans['abstract'] = data['data']['abstract']
    else:
        ans['abstract'] = None
    if 'title' in data['data']:
        ans['title'] = data['data']['title']
    else:
        ans['title'] = None
    return ans


def first():
    item = {'artid': '255736230',
            'title': 'An automated approach to network features of protein structure ensembles',
            'abstract': '',
            'url': 'https://www.researchgate.net/publication/255736230_An_automated_approach_to_network_features_of_protein_structure_ensembles',
            'citation': 10,
            'refers': [],
            'cites': []}
    # get title and abstract
    QUEUE.put([item, 0, 0])
    FINISHED.put(set())


def worker(name=''):
    # Get object from QUEUE
    while 1:
        if END:
            break
        try:
            item, r, c = QUEUE.get(timeout=10)
        except Queue.Empty, e:
            break
        finished = FINISHED.get()
        finished.add(item['artid'])
        FINISHED.put(finished)
        if not item['url'] or not judge(r, c):
            OBJECT.put(item)
            continue
        # Get data from web
        refs = getRefDict(item['artid'], 9999)
        cites = getCiteDict(item['artid'], item['citation'])
        refids = [i['artid'] for i in refs]
        citeids = [i['artid'] for i in cites]
        finished = FINISHED.get()
        for i in refs:
            if i['artid'] not in finished:
                QUEUE.put([i, r + 1, c])
        for i in cites:
            if i['artid'] not in finished:
                QUEUE.put([i, r, c + 1])
        FINISHED.put(finished)
        item['refers'] = refids
        item['cites'] = citeids
        OBJECT.put(item)
        continue


class Worker(threading.Thread):

    def __init__(self, lock, threadName):
        super(Worker, self).__init__(name=threadName)
        self.lock = lock

    def run(self):
        try:
            worker(self.name)
        except LinkError, e:
            worker(self.name)


class Counter(threading.Thread):

    def __init__(self, lock, threadName):
        super(Counter, self).__init__(name=threadName)
        self.lock = lock

    def run(self):
        zero = 0
        string = ''
        while 1:
            sleep(0.25)
            string = str(QUEUE.qsize()) + ' items waiting.\t\t\r'
            print string,
            if QUEUE.qsize() == 0:
                zero += 1
            if zero > 50:
                print "Task Finished.\t\t\t"
                global END
                END = True
                break
        print "Writing..."
        total = OBJECT.qsize()
        i = 0.0
        with open(FILENAME, 'w') as f:
            f.write('[')
            while 1:
                try:
                    item = OBJECT.get(timeout=0.25)
                except Queue.Empty, e:
                    f.write(']')
                    break
                f.write(json.dumps(item))
                f.write(',')
                i += 1
                print str(i / total) + '% finished.\r',
        print 'FINISHED.\t\t\t'

if __name__ == '__main__':
    initialize()
    first()
    lock = threading.Lock()
    for i in range(5):
        Worker(lock, 'thread-' + str(i)).start()
    Counter(lock, 'thread-' + str(i + 1)).start()
    QUEUE.join()
