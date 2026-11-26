"""Conservative local semantic adapter. No AFI factual generation, no automatic cloud calls."""
import json, os, re, time, unicodedata
from collections import Counter
from .core import LANGS, INTENTS, classify, normalize, script, numbers, MESSAGES
from .responses import reply

# Explicit surface patterns. These are engineering heuristics, not linguistic gold data.
INTENT_WORDS={
'availability': 'شاغر|شاغرة|فارغ|فارغة|متوفر|متوفرة|متاح|متاحة|موجود|موجودة|disponib|vacant|available|free plot|verfügbar|frei|müsait|boş|faragh|feragh|feregh|fama blasa|famma blasa|dispo',
'price': 'سوم|ثمن|سعر|قداش|بقداش|تكلفة|prix|coût|tarif|price|cost|preis|kosten|fiyat|ücret|b9addech|9addech|9adech|9addesh|9adeh|sou[mn]',
'documents': 'وثائق|وثيقة|أوراق|الوراق|اوراق|مستند|ملف|pièces|justificatif|papiers|documents?|paperwork|unterlagen|dokument|belge|evrak|awra9|wra9|wara9',
'procedure': 'إجراءات|اجراءات|إجراء|خطوات|كيفاش|كيف يمكن|كيفية|procédure|démarche|comment|étapes|steps|procedure|how (?:do|can|to)|verfahren|ablauf|wie (?:kann|beantrage)|başvuru|nasıl|kifech|kifesh|kifach|kifeh',
'surface': r'مساحة|متر مربع|هكتار|surface|superficie|area|square met|hectare|fläche|quadratmeter|metrekare|alan|m[²2](?!\w)|\bm²|\bha\b|masa7a|mesa7a',
'deadline': 'آخر أجل|اخر اجل|آجال|اجال|موعد|تاريخ|نهار|délai|date limite|échéance|deadline|due date|closing date|frist|termin|son tarih|süre|wa9tech|wa9t|imta',
'incentives': 'امتياز|حوافز|منح|إعفاء|اعفاء|aides|incitation|avantage|subvention|incentive|grant|tax relief|förder|anreiz|teşvik|destek|muafiyet|imtiyaz',
'clarify': 'وضّح|وضح|توضيح|clarif|précis|que veut dire|what do you mean|was bedeutet|erklär|ne demek|açıkla|fassar|fasser',
}
# Stronger multiword terms first, preserve ambiguity for overlapping dialects.
LID_WORDS={
'aeb':r'(?<!\w)(?:شنوة|شنوا|شنية|شنوّة|شنيا|نحب|يلزمني|يلزمك|برشة|باهي|توّا|توا|موش|بالله|عسلامة|بقداش|قداش|متاع|famma|fama|chnowa|chneya|chnoua|chnia|n7eb|na7eb|tnajjem|tnajem|barcha|barsha|bech|bch|moch|mouch|tawwa|3aslema|9addech|9adech|kifech|mte3|mta3)(?!\w)',
'arq':r'(?<!\w)(?:واش|بزاف|درك|دروك|راني|نقدر|شحال|راك|راكي|wach|wesh|bzzaf|bezaf|ch7al|dorka|rani)(?!\w)',
'ayl':r'(?<!\w)(?:نبي|نبو|هلبا|واجد|شنو|شن|توا|نقدر|بالله|نبيك|nbi|nbee|halba|shn|shin|tawa)(?!\w)',
'ar':r'(?<!\w)(?:أريد|اريد|أرغب|هل|يرجى|يرجى|يمكنني|ما هي|الرجاء|لدي|أحتاج|احتاج|كيفية|المتاحة|المطلوبة|اللازمة)(?!\w)',
'fr':r'(?<!\w)(?:je|vous|nous|quel|quelle|quels|quelles|comment|est-ce|où|combien|souhaite|voudrais|disponible|pour|dans|les|des|une|un|du|le|la|prix)(?!\w)',
'en':r'(?<!\w)(?:what|where|when|which|how|can|could|would|please|the|is|are|there|i|need|want|does|for|of|in|available)(?!\w)',
'de':r'(?<!\w)(?:ich|möchte|welche|welcher|wie|wo|wann|gibt|sind|ist|der|die|das|ein|eine|für|bitte|kosten|antrag|grundstück)(?!\w)',
 'tr':r'(?<!\w)(?:bir|hangi|nasıl|nerede|ne|kadar|için|istiyorum|var|mı|mi|başvuru|belgeler|sanayi|arsa|lütfen|gerekiyor)(?!\w)'}
# Aliases are for recognizing mention strings, not a verified AFI zone catalogue.
PLACES={'Tunis':'تونس|tunis|tounes','Sfax':'صفاقس|sfax|sf9s|sfa9s','Bizerte':'بنزرت|bizerte|benzart|benzert','Zaghouan':'زغوان|zaghouan|zaghwen','Ben Arous':'بن عروس|ben arous|ben 3arous','Sousse':'سوسة|sousse|soussa','Gabès':'قابس|gab[eè]s|gabes|gabis','Nabeul':'نابل|nabeul|nebel','Kairouan':'القيروان|قيروان|kairouan|9ayrawen','Médenine':'مدنين|m[eé]denine','Monastir':'المنستير|منستير|monastir','Gafsa':'قفصة|gafsa|9afsa','Kasserine':'القصرين|قصرين|kasserine','Jendouba':'جندوبة|jendouba','Le Kef':'الكاف|kef','Siliana':'سليانة|siliana','Mahdia':'المهدية|مهدية|mahdia','Tozeur':'توزر|tozeur','Kébili':'قبلي|k[eé]bili','Tataouine':'تطاوين|tataouine','Béja':'باجة|b[eé]ja','Manouba':'منوبة|manouba','Ariana':'أريانة|اريانة|ariana','Sidi Bouzid':'سيدي بوزيد|sidi bouzid'}
NEG=r'(?<!\w)(?:موش|مش|ماشي|ليس|ليست|لا|لم|لن|غير|pas|not|never|no|nicht|kein(?:e[nrms]?)?|değil|yok|moch|mouch|mish|mach|ma\s+\w+ch|ما\s+\w+ش)(?!\w)'

def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))

def detect(text):
    raw=classify(text,'language'); t=normalize(text).casefold(); counts={k:len(set(re.findall(p,t,re.I))) for k,p in LID_WORDS.items()};
    # Score discriminative markers + weak statistical signal; not calibrated.
    ranked=sorted(LANGS,key=lambda k: -(counts[k]*0.32+next((x['score'] for x in raw['alternatives'] if x['label']==k),0)))
    a,b=ranked[:2]; mixed=script(text)=='mixed' or bool(counts['aeb'] and (counts['fr'] or counts['en']))
    # Shared Maghrebi markers alone should not force country-level classification.
    if counts[a]>=1 and counts[a]>counts[b] and (counts[a]>=2 or raw['label']==a): selected=a; reason='markers_and_baseline'
    elif raw['score']>=.45 and raw['score']-raw['alternatives'][1]['score']>=.15: selected=raw['label']; reason='statistical_baseline'
    else: selected=None; reason='ambiguous'
    if counts['aeb']>=2 and counts['aeb']>max(counts['arq'],counts['ayl']): selected='aeb'; reason='tunisian_markers'
    return {'label':selected,'best_guess':a,'baseline':raw,'markers':counts,'code_switch_candidate':mixed,'reason':reason}

def intent(text):
    t=normalize(text).casefold(); baseline=classify(text,'intent'); matches={k:sorted(set(re.findall(p,t,re.I))) for k,p in INTENT_WORDS.items()}; counts={k:len(v) for k,v in matches.items()};
    # A number followed by m² is a constraint, not necessarily the intent.
    if counts['surface'] and (counts['availability'] or counts['price']): counts['surface']=0
    if counts['procedure'] and (counts['documents'] or counts['price'] or counts['availability'] or counts['deadline']): counts['procedure']=0
    # '9addech' can mean how much area, time, or price.
    if counts['price'] and counts['surface'] and not re.search('prix|price|سوم|سعر|ثمن|fiyat|preis|tarif|cost',t): counts['price']=0
    candidates=sorted(INTENTS,key=lambda k:(-counts[k],-next((x['score'] for x in baseline['alternatives'] if x['label']==k),0),k)); top=candidates[0];
    if counts[top]>0: selected=top; reason='lexical'; needs=counts[top]==counts[candidates[1]]
    else: selected=baseline['label']; reason='statistical'; needs=baseline['score']<.45
    return {'label':selected,'needs_confirmation':needs,'reason':reason,'matches':matches,'baseline':baseline,'secondary':[k for k in candidates if counts[k]>0 and k!=selected]}

def extract(text):
    found=[]
    for canonical,aliases in PLACES.items():
        for m in re.finditer(r'(?<!\w)(?:'+aliases+r')(?!\w)',text,re.I): found.append({'type':'place_mention','value':m.group(),'canonical_hint':canonical,'start':m.start(),'end':m.end()})
    for m in re.finditer(r'(?<!\w)\d+(?:[.,]\d+)*(?:\s*(?:m²|m2|م²|متر مربع|هكتار|ha|TND|DT|دينار|د\.?ت\.?|€|EUR))?(?!\w)',text,re.I): found.append({'type':'numeric_mention','value':m.group(),'start':m.start(),'end':m.end()})
    for m in re.finditer(NEG,text,re.I): found.append({'type':'negation_marker','value':m.group(),'start':m.start(),'end':m.end()})
    return sorted(found,key=lambda x:x['start'])

ARABIZI_REPLY='Fhemt sou2elek. Taw ma 3andich ma3loumet AFI mthabtin bech n3tik ijeba d9i9a. Tnajem twadhdha7 talbek?'

def understand(text,language='auto',history=None,backend='baseline',style='auto'):
    if not isinstance(text,str) or not text.strip() or len(text)>4000: raise ValueError('Text must contain 1–4000 characters')
    if language!='auto' and language not in LANGS: raise ValueError('Unsupported language')
    if backend not in ('baseline','ollama','gemini','groq'): raise ValueError('Unknown semantic backend')
    if style not in ('auto','arabic','arabizi'): raise ValueError('Unknown writing style')
    start=time.perf_counter(); d=detect(text); i=intent(text); selected=d['label'] if language=='auto' else language; mentions=extract(text); context=[]; failure=None; used='baseline'
    # Explicit client-provided previous user messages only; do not merge numeric mentions into current query.
    for item in (history or [])[-6:]:
        if isinstance(item,str) and len(item)<=4000: context.append(item)
    if backend!='baseline':
        try:
            from .llm import semantic_json
            parsed=semantic_json(text,context,backend)
            if language=='auto' and parsed['language']!='unknown': selected=parsed['language']
            if parsed['intent']!='unknown': i={**i,'label':parsed['intent'],'needs_confirmation':parsed['needs_clarification'],'reason':'llm_proposal'}
            used=backend
        except Exception as exc: failure=type(exc).__name__+': semantic backend unavailable or refused; local baseline retained'
    if backend=='baseline' and context and len(normalize(text).split())<=8 and re.match(r'^(?:و|w\s|et\s|and\s|und\s|peki\s)',normalize(text),re.I) and not any(i['matches'].values()):
        prev=intent(context[-1])
        if not prev['needs_confirmation']:
            i={**i,'label':prev['label'],'needs_confirmation':True,'reason':'previous_intent_candidate'}
    chosen_style='arabizi' if selected=='aeb' and (style=='arabizi' or style=='auto' and script(text)=='latin' and re.search(r'[a-z]\d|\d[a-z]|chnowa|chnoua|nheb|n7eb|fama|bech|kifech',text,re.I)) else 'arabic'
    response=reply(selected,chosen_style,i['label']) if selected else None
    return {'original':text,'normalized':normalize(text),'script':script(text),'language':selected,'language_detection':d,'intent':i,'numbers':numbers(text),'mentions':mentions,'needs_language_confirmation':selected is None,'response':response,'response_style':chosen_style,'knowledge_status':'not_connected','semantic_backend':used,'fallback_reason':failure,'context_turns':len(context),'processing_s':round(time.perf_counter()-start,4)}
