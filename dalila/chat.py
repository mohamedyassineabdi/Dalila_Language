"""Safe chat orchestration; domain responses remain controlled pending AFI retrieval."""
import re
from .semantic import understand
from .responses import reply
from .llm import conversational_reply

GREETINGS = {
    'ahla bik': ('aeb','arabizi','Ahla bik! Labes? Kifech najjem n3awnek?'),
    'ahla': ('aeb','arabizi','Ahla! Kifech najjem n3awnek?'),
    '3aslema': ('aeb','arabizi','3aslema! Kifech najjem n3awnek?'),
    'aslema': ('aeb','arabizi','3aslema! Kifech najjem n3awnek?'),
    'عسلامة': ('aeb','arabic','عسلامة! لاباس؟ كيفاش نجم نعاونك؟'),
    'أهلا بيك': ('aeb','arabic','أهلا بيك! كيفاش نجم نعاونك؟'),
    'اهلا بيك': ('aeb','arabic','أهلا بيك! كيفاش نجم نعاونك؟'),
    'bonjour': ('fr','arabic','Bonjour ! Comment puis-je vous aider ?'),
    'hello': ('en','arabic','Hello! How can I help?'),
    'hi': ('en','arabic','Hi! How can I help?'),
    'hallo': ('de','arabic','Hallo! Wie kann ich Ihnen helfen?'),
    'merhaba': ('tr','arabic','Merhaba! Size nasıl yardımcı olabilirim?'),
}
def chat_turn(text, language='auto', history=None, backend='baseline', style='auto'):
    result = understand(text, language, history, 'baseline', style)
    greeting = GREETINGS.get(re.sub(r'[!?.؟،]+$', '', text.strip().casefold()).strip())
    chosen = result['language'] or result['language_detection']['best_guess'] or 'aeb'
    response_style = result['response_style']
    if chosen == 'aeb' and result['script'] == 'latin' and style == 'auto':
        response_style = 'arabizi'
    model = None
    failure = None
    if greeting and (language == 'auto' or language == greeting[0]):
        chosen, response_style, answer = greeting
        used = 'greeting'
    else:
        # Do not let a free-form LLM answer domain questions without verified sources.
        domain = any(result['intent']['matches'].get(k) for k in ('availability','price','documents','procedure','surface','deadline','incentives'))
        answer = reply(chosen, response_style, result['intent']['label'])
        used = 'baseline'
        if backend != 'baseline':
            if domain or backend != 'ollama':
                result = understand(text, language, history, backend, style)
                chosen = result['language'] or chosen
                response_style = result['response_style'] if result['language'] else response_style
                answer = reply(chosen, response_style, result['intent']['label'])
                used = result['semantic_backend']
                failure = result.get('fallback_reason')
            else:
                try:
                    answer, model = conversational_reply(text, history or [], chosen, response_style)
                    used = 'ollama'
                except Exception as exc:
                    failure = type(exc).__name__ + ': local conversational model unavailable'
    return {'user_text':text,'assistant_text':answer,'language':chosen,
            'detected_language': greeting[0] if greeting and used=='greeting' else result['language'],
            'needs_language_confirmation':False if used=='greeting' else result['needs_language_confirmation'],
            'response_style':response_style,'intent':result['intent'],'semantic_backend':used,
            'model':model,'fallback_reason':failure,'technical':result}
