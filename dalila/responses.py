"""Human-readable safe demo replies; labels are proposals, not verified AFI facts."""
TOPICS={
'aeb':['المقاسم الموجودة','السوم','الأوراق اللازمة','الإجراءات','المساحة','آخر أجل','الامتيازات','توضيح الطلب'],
'ar':['توفر المقاسم','السعر','الوثائق المطلوبة','الإجراءات','المساحة','الموعد النهائي','الحوافز','توضيح الطلب'],
'fr':['la disponibilité des parcelles','le prix','les pièces justificatives','les démarches','la superficie','la date limite','les aides et avantages','une clarification'],
'en':['plot availability','the price','required documents','the procedure','the surface area','the deadline','incentives','a clarification'],
'arq':['المقاسم المتوفرة','السعر','الوثائق اللازمة','الإجراءات','المساحة','آخر أجل','الامتيازات','توضيح الطلب'],
'ayl':['الأراضي المتوفرة','السعر','الأوراق المطلوبة','الإجراءات','المساحة','آخر موعد','الحوافز','توضيح الطلب'],
'de':['die Verfügbarkeit von Grundstücken','den Preis','die erforderlichen Unterlagen','das Verfahren','die Grundstücksfläche','die Frist','Fördermöglichkeiten','eine Klarstellung'],
'tr':['arsa mevcudiyeti','fiyat','gerekli belgeler','başvuru süreci','arsa alanı','son başvuru tarihi','teşvikler','bir açıklama'],
'arabizi':['el ma9asem elli mawjoudin','es-soum','el awra9 elli lezmou','les démarches','el masa7a','e5er délai','les avantages','tawdhih et-taleb']}
ORDER=['availability','price','documents','procedure','surface','deadline','incentives','clarify']
# Render only the controlled topic label and a clear knowledge-unavailable message.
PATTERNS={
'aeb':'تقصد تسأل على {topic}؟ توّا معطيات AFI المثبّتة موش مربوطة. ما نجمش نعطيك جواب دقيق قبل ما نتثبّت.',
'ar':'هل تقصد الاستفسار عن {topic}؟ لم تُربط بيانات AFI المعتمدة بعد، لذلك لا أستطيع تقديم إجابة مؤكدة.',
'fr':'Votre demande concerne {topic}, c’est bien cela ? Les données AFI validées ne sont pas encore connectées ; je ne peux pas donner de réponse confirmée.',
'en':'Are you asking about {topic}? Verified AFI data is not connected yet, so I cannot provide a confirmed answer.',
'arq':'راك تسقسي على {topic}؟ معلومات AFI المؤكدة مازال ما ربطناهاش، ما نقدرش نعطيك جواب مؤكد.',
'ayl':'تقصد تسأل على {topic}؟ بيانات AFI المؤكدة مش مربوطة توا، ما نقدرش نعطيك جواب مؤكد.',
'de':'Geht es um {topic}? Geprüfte AFI-Daten sind noch nicht verbunden; eine bestätigte Antwort ist daher nicht möglich.',
 'tr':'Sorunuz {topic} ile mi ilgili? Doğrulanmış AFI verileri henüz bağlı değil; bu nedenle kesin bir yanıt veremiyorum.',
 'arabizi':'Ta9sed tes2el 3la {topic}? Taw les données AFI mthabtin mazelou moch marboutin, ma najjemch n3tik ijeba mthabta.'}

def reply(language,style,intent):
    if language not in TOPICS or intent not in ORDER:return None
    key='arabizi' if language=='aeb' and style=='arabizi' else language
    return PATTERNS[key].format(topic=TOPICS[key][ORDER.index(intent)])
