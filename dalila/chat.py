"""Local-first conversational orchestration, separate from AFI facts."""
import re, time
from .semantic import understand
from .responses import reply
from .llm import conversational_reply
from .core import LANGS, script

# Deterministic greetings keep short utterances usable even on a cold start.
GREETINGS = {
    'ahla bik': ('aeb','arabizi','Ahla bik! Labes? Kifech najjem n3awnek?','أهلا بيك! لاباس؟ كيفاش نجم نعاونك؟'),
    'ahla': ('aeb','arabizi','Ahla! Kifech najjem n3awnek?','أهلا! كيفاش نجم نعاونك؟'),
    '3aslema': ('aeb','arabizi','3aslema! Kifech najjem n3awnek?','عسلامة! كيفاش نجم نعاونك؟'),
    'aslema': ('aeb','arabizi','3aslema! Kifech najjem n3awnek?','عسلامة! كيفاش نجم نعاونك؟'),
    'عسلامة': ('aeb','arabic','عسلامة! لاباس؟ كيفاش نجم نعاونك؟','عسلامة! لاباس؟ كيفاش نجم نعاونك؟'),
    'أهلا بيك': ('aeb','arabic','أهلا بيك! كيفاش نجم نعاونك؟','أهلا بيك! كيفاش نجم نعاونك؟'),
    'اهلا بيك': ('aeb','arabic','أهلا بيك! كيفاش نجم نعاونك؟','أهلا بيك! كيفاش نجم نعاونك؟'),
    'تفهم فيا': ('aeb','arabic','إي، فهمتك. تنجم تحكي معايا بالتونسي.','إي، فهمتك. تنجم تحكي معايا بالتونسي.'),
    'bonjour': ('fr','arabic','Bonjour ! Comment puis-je vous aider ?',None),
    'salut': ('fr','arabic','Salut ! Comment puis-je vous aider ?',None),
    'hello': ('en','arabic','Hello! How can I help?',None),
    'hi': ('en','arabic','Hi! How can I help?',None),
    'hallo': ('de','arabic','Hallo! Wie kann ich Ihnen helfen?',None),
    'merhaba': ('tr','arabic','Merhaba! Size nasıl yardımcı olabilirim?',None),
    'السلام عليكم': ('ar','arabic','وعليكم السلام! كيف يمكنني مساعدتك؟',None),
}
CLARIFY = {
    'aeb':('تنجم توضّحلي شوية شنوّة تحب؟','Tnajem twadhahli chwaya chnowa t7eb?'),
    'ar':('هل يمكنك توضيح ما تقصده؟',),
    'arq':('تقدر توضّحلي واش تقصد؟',),
    'ayl':('ممكن توضّحلي شن تقصد؟',),
    'fr':('Pouvez-vous préciser ce que vous voulez dire ?',),
    'en':('Could you tell me a little more about what you mean?',),
    'de':('Können Sie genauer erklären, was Sie meinen?',),
    'tr':('Ne demek istediğinizi biraz daha açıklayabilir misiniz?',),
}
DOMAIN = re.compile(r'(?i)(?:\bafi\b|terrain|parcelle|foncier|industri|invest|march[ée]|dossier|document|proc[ée]dur|land|plot|price|deadline|tax|law|legal|قانون|استثمار|صناع|مقاسم|مقسم|أرض|ارض|أراضي|اراضي|رخص|سعر|سوم|وثائق|ملف|إجراءات|اجراءات|ma9sem|ma9asem|ardh|grundst|arsa|sanayi)')
def choose_style(text, language, style):
    if language == 'aeb':
        if style in ('arabic','arabizi'):
            return style
        return 'arabizi' if script(text)=='latin' else 'arabic'
    return 'arabic'

def chat_turn(text, language='auto', history=None, backend='baseline', style='auto'):
    started = time.perf_counter()
    timings = {}
    result = understand(text, language, history, 'baseline', style)
    timings['analysis_s'] = round(time.perf_counter()-started,3)
    norm = re.sub(r'[\s!?.؟،*]+$', '', text.strip().casefold()).strip()
    greeting = GREETINGS.get(norm)
    chosen = result['language'] or result['language_detection']['best_guess'] or 'aeb'
    response_style = choose_style(text, chosen, style)
    model = None
    failure = None
    used = 'baseline'
    speech_text = None
    domain = bool(DOMAIN.search(text)) or any(result['intent']['matches'].get(k) for k in ('availability','price','documents','procedure','surface','deadline','incentives'))
    # General project-start requests need a relevant follow-up, not ungrounded facts.
    project = bool(re.search(r'(?:مشروع|\bprojet\b|\bproject\b|machrou3|machroua|proje|projekt)',text,re.I))
    if greeting and (language == 'auto' or language == greeting[0]):
        chosen, response_style, answer, speech_text = greeting
        used = 'greeting'
    elif project and not domain and chosen == 'aeb':
        if response_style == 'arabizi':
            answer = 'Ey, najjem n3awnek. Chnowa naw3 el machrou3 elli t7eb ta3mlou?'
            speech_text = 'إي، نجم نعاونك. شنوة نوع المشروع اللي تحب تعملو؟'
        else:
            answer = speech_text = 'إي، نجم نعاونك. شنوة نوع المشروع اللي تحب تعملو؟'
        used = 'guided'
    else:
        if backend == 'ollama' and not domain:
            try:
                proposed, model = conversational_reply(text, history or [], chosen, response_style)
                timings.update(proposed.get('_timing', {}))
                if language == 'auto':
                    chosen = proposed['language']
                response_style = choose_style(text, chosen, style)
                if proposed['category'] == 'social' and (language == 'auto' or proposed['language'] == language):
                    answer = proposed['reply']
                    speech_text = proposed['speech_text'] or (answer if response_style != 'arabizi' else None)
                    if chosen in ('aeb','ar','arq','ayl'):
                        if response_style != 'arabizi' and script(answer) not in ('arabic','mixed'):
                            if speech_text and script(speech_text) in ('arabic','mixed'):
                                answer = speech_text
                            else:
                                raise ValueError('Model returned wrong script')
                        if speech_text and script(speech_text) not in ('arabic','mixed'):
                            speech_text = None
                    used = 'ollama'
                else:
                    domain = proposed['category'] == 'domain'
            except Exception as exc:
                failure = type(exc).__name__ + ': local conversational model unavailable'
        if used == 'baseline':
            if domain:
                if backend != 'baseline' and not model and (result['intent']['needs_confirmation'] or not result['language']):
                    result = understand(text, language, history, backend, style)
                    chosen = result['language'] or chosen
                    response_style = choose_style(text, chosen, style)
                    used = result['semantic_backend']
                    failure = result.get('fallback_reason') or failure
                answer = reply(chosen, response_style, result['intent']['label'])
                if chosen == 'aeb' and response_style == 'arabizi':
                    speech_text = reply(chosen,'arabic',result['intent']['label'])
            else:
                choices = CLARIFY[chosen]
                answer = choices[-1] if response_style == 'arabizi' else choices[0]
                speech_text = choices[0]
    timings['total_s'] = round(time.perf_counter()-started,3)
    return {'timing':timings,'user_text':text,'assistant_text':answer,'language':chosen,
            'detected_language': chosen if used in ('greeting','guided','ollama') else result['language'],
            'needs_language_confirmation':False if used in ('greeting','ollama') else result['needs_language_confirmation'],
            'response_style':response_style,'speech_text':speech_text or (answer if response_style != 'arabizi' else None),
            'intent':result['intent'],'semantic_backend':used,
            'model':model,'fallback_reason':failure,'technical':result}
