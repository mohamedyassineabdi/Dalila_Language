from pathlib import Path
import json,re,unicodedata,os
from functools import lru_cache
ROOT=Path(__file__).resolve().parents[1]
LANGS={'aeb':'Tunisian Arabic','ar':'Modern Standard Arabic','fr':'French','en':'English','arq':'Algerian Arabic','ayl':'Libyan Arabic','de':'German','tr':'Turkish'}
INTENTS={'availability','price','documents','procedure','surface','deadline','incentives','clarify'}

def normalize(text):
    # NFC and whitespace only: never replace digits, negations, or Arabizi characters.
    return ' '.join(unicodedata.normalize('NFC',text).split())

def script(text):
    a=bool(re.search(r'[\u0600-\u06ff]',text)); l=bool(re.search(r'[a-zA-ZÀ-ž]',text))
    return 'mixed' if a and l else 'arabic' if a else 'latin' if l else 'other'

def numbers(text):
    return re.findall(r'(?<!\w)\d+(?:[.,]\d+)*(?!\w)',text)

def rows():
    return [json.loads(x) for x in (ROOT/'data/text_cases.jsonl').read_text(encoding='utf-8').splitlines()]

@lru_cache(maxsize=4)
def classifier(target,kind='char'):
    from sklearn.pipeline import make_pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    if target not in ('language','intent') or kind not in ('word','char'): raise ValueError('Unknown classifier')
    train=[r for r in rows() if r['split']=='dev']
    model=make_pipeline(TfidfVectorizer(analyzer='char' if kind=='char' else 'word',ngram_range=(2,5) if kind=='char' else (1,2),sublinear_tf=True),LogisticRegression(max_iter=1000,C=5,class_weight='balanced',random_state=42))
    model.fit([normalize(r['text']) for r in train],[r[target] for r in train]); return model

def classify(text,target,kind='char'):
    m=classifier(target,kind); p=m.predict_proba([normalize(text)])[0]; ranked=sorted(zip(m.classes_,p),key=lambda x:-x[1]); return {'label':str(ranked[0][0]),'score':float(ranked[0][1]),'alternatives':[{'label':str(k),'score':float(v)} for k,v in ranked[:3]]}

# Safe demo only: acknowledge request, no retrieval or substantive AFI claim.
MESSAGES={'aeb':'فهمت سؤالك. توّا ما عنديش معطيات AFI مثبّتة باش نعطيك إجابة دقيقة. تنجّم توضّح طلبك؟','ar':'فهمت سؤالك. لا تتوفر لدي بيانات AFI معتمدة للإجابة الآن. هل يمكنك توضيح طلبك؟','fr':'Je comprends votre demande. Les données AFI validées ne sont pas encore connectées. Pouvez-vous préciser votre demande ?','en':'I understand your request. Verified AFI data is not connected yet. Could you clarify your request?','arq':'فهمت سؤالك. ما عنديش معلومات AFI مؤكدة دُرك. تقدر توضّح طلبك؟','ayl':'فهمت سؤالك. ما عنديش بيانات AFI مؤكدة توا. ممكن توضّح طلبك؟','de':'Ich verstehe Ihre Anfrage. Geprüfte AFI-Daten sind noch nicht verbunden. Können Sie Ihre Anfrage präzisieren?','tr':'Talebinizi anladım. Doğrulanmış AFI verileri henüz bağlı değil. Talebinizi açıklayabilir misiniz?'}

def analyze(text,language='auto'):
    if not text.strip() or len(text)>4000: raise ValueError('Text must contain 1–4000 characters')
    if language!='auto' and language not in LANGS: raise ValueError('Unsupported language')
    lid=classify(text,'language'); intent=classify(text,'intent'); chosen=language if language!='auto' else lid['label']
    # Raw classifier probability is not calibrated; abstain conservatively.
    uncertain=language=='auto' and (lid['score']<0.45 or lid['score']-lid['alternatives'][1]['score']<0.15)
    return {'original':text,'normalized':normalize(text),'script':script(text),'language':None if uncertain else chosen,'language_detection':lid,'intent':intent,'numbers':numbers(text),'needs_language_confirmation':uncertain,'response':None if uncertain else MESSAGES[chosen], 'knowledge_status':'not_connected'}
