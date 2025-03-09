from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import json,cloudscraper,time,csv
from dateutil import parser
import statistics as st

chrome_options = Options()
chrome_options.add_argument('--window-size=1200,900')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--no-sandbox')
drA = webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options) #initiate webdriver

scraper = cloudscraper.create_scraper()
mainUrl = "https://www.dcard.tw/service/api/v2"

def reopen(url):
    global drA
    drA.quit()
    drA = webdriver.Chrome(ChromeDriverManager().install(),options=chrome_options)
    drA.get(url)
    time.sleep(1)

def acs(url):
    drA.get(url)
    ob = None
    time.sleep(1)
    while(not ob):
        try:
            a = drA.find_element_by_xpath('//pre').get_attribute('innerText')
            ob = json.loads(a)
        except Exception as e:
            print('.',end='')
        time.sleep(1)
    return ob

class post:
    def __init__(sf,**kwargs):
        sf.stat = True
        if kwargs.get('id'):
            sf.id = kwargs['id']
        if kwargs.get('url'):
            url = kwargs['url']
            sf.id = url[url.index('/p/')+len('/p/'):]
            if '?cid=' in sf.id:
                sf.id = sf.id[:sf.id.index('?cid=')]
        sf.dData = acs(mainUrl+'/posts/'+sf.id)
        if sf.dData.get('error'):
            sf.stat = False
        sf.dt = list()

    def getTrainData(sf):
        lcmt = list()
        llike = list()
        tdt = {
            'like' : sf.dData['likeCount'],
            'cmt' : sf.dData['commentCount'],
            'lcRatio': 0,
            'pVis' : (1 if sf.dData['anonymousSchool'] else 0) + (1 if sf.dData['anonymousDepartment'] else 0),
            'tCreated' : parser.parse(sf.dData['createdAt']).hour,
            'pGender' : 1 if sf.dData['gender'] == 'M' else 0,
            'collection' : sf.dData['collectionCount'],
            'wordCount' : len(sf.dData['content']),
            'B0mentionCnt' : 0,
            'B0mentionAvgLike' :0,
            'B0mentionAvgCmt' :0,
            'anonRate' :0,
            'B0cmtCnt':0,
            'B0cmtAvgLikeCnt' :0,
            'B0cmtAvgCmtCnt' :0,
        }
        cmtCnt = tdt['cmt']
        url0 = mainUrl+'/posts/'+sf.id+'/comments?limit=100&popular=false&after='
        for i in range(1+tdt['cmt']//100):
            cmts = acs(url0+ str(i*100))
            for cmt in cmts:
                if cmt['hidden']: continue
                llike.append(cmt['likeCount'])
                lcmt.append(cmt['subCommentCount'])
                if cmt.get('subCommentCount'):
                    tdt['cmt'] += cmt['subCommentCount']
                if cmt['anonymous']: tdt['anonRate'] += 1
                if cmt['host']:
                    tdt['B0cmtCnt'] += 1
                    tdt['B0cmtAvgLikeCnt'] += cmt['likeCount']
                    if cmt.get('subCommentCount'):
                        tdt['B0cmtAvgCmtCnt'] += cmt['subCommentCount']
                elif 'B0' in cmt['content']:
                    tdt['B0mentionCnt'] += 1
                    tdt['B0mentionAvgLike'] += cmt['likeCount']
                    if cmt.get('subCommentCount'):
                        tdt['B0mentionAvgCmt'] += cmt['subCommentCount']    
            print('*',end='')
            # time.sleep(8)
        tdt['lcRatio'] = int((tdt['cmt'] / tdt['like'])*1000)
        tdt['anonRate'] = int(1000*tdt['anonRate']/cmtCnt)
        if tdt['B0mentionCnt'] > 0:
            tdt['B0mentionAvgLike'] = int(1000*tdt['B0mentionAvgLike']/tdt['B0mentionCnt'])
            tdt['B0mentionAvgCmt'] = int(1000*tdt['B0mentionAvgCmt']/tdt['B0mentionCnt'])
        if tdt['B0cmtCnt'] > 0:
            tdt['B0cmtAvgLikeCnt'] = int(1000*tdt['B0cmtAvgLikeCnt']/tdt['B0cmtCnt'])
            tdt['B0cmtAvgCmtCnt'] = int(1000*tdt['B0cmtAvgCmtCnt']/tdt['B0cmtCnt'])
        tdt.update({
            'stLike' : int(st.stdev(llike)*100),
            'stCmt' : int(st.stdev(lcmt)*100)
        })
        # sf.dt = tdt
        print(sf.dData['title'],tdt)
        return tdt

if __name__ == '__main__':
    lraw = list()
    lRes = list()
    with open('AI/file032.csv', newline='') as f:
        ob = csv.reader(f)
        lraw = list(ob)

    for cpost in lraw:
        ob = post(url = cpost[0])
        if not ob.stat :
            print('fail')
            continue 
        data = ob.getTrainData()
        if not ob.stat:
            continue
        data.update({'isCondemn':int(cpost[1])})
        lRes.append(data)

    keys = lRes[0].keys()
    with open('AI/DcaTrainData.csv', 'a', newline='') as f:
        dict_writer = csv.DictWriter(f, keys)
        # dict_writer.writeheader()
        dict_writer.writerows(lRes)